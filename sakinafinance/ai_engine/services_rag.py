"""
RAG Service — SakinaFinance
Retrieval-Augmented Generation avec :
  - Embeddings : sentence-transformers/all-MiniLM-L6-v2 (local, gratuit)
  - Vector Store : ChromaDB (persistant sur disque)
  - LLM Inference : Gemini API
"""
import os
import logging
from pathlib import Path
from time import sleep

import requests
from django.conf import settings
from django.core.cache import cache
from .models import KnowledgeDocument, KnowledgeChunk

# File extractors
from pypdf import PdfReader
import docx2txt

logger = logging.getLogger('sakinafinance')

# ---------------------------------------------------------------------------
# Lazy-loaded singletons (chargés une seule fois au premier appel)
# ---------------------------------------------------------------------------
_pinecone_client = None
_pinecone_index = None

def _get_pinecone_index():
    """Initialise le client Pinecone et retourne l'index."""
    global _pinecone_client, _pinecone_index
    if _pinecone_index is None:
        try:
            from pinecone import Pinecone
            api_key = getattr(settings, 'PINECONE_API_KEY', '')
            if not api_key:
                logger.error("PINECONE_API_KEY non défini.")
                return None
            _pinecone_client = Pinecone(api_key=api_key)
            index_name = getattr(settings, 'PINECONE_INDEX_NAME', 'sakina-vect')
            _pinecone_index = _pinecone_client.Index(index_name)
            logger.info(f"Pinecone initialisé sur l'index : {index_name}")
        except Exception as e:
            logger.error(f"Impossible d'initialiser Pinecone: {e}")
            _pinecone_index = None
    return _pinecone_index


# ---------------------------------------------------------------------------
# RAGService
# ---------------------------------------------------------------------------

class RAGService:
    """
    Service RAG complet :
      - Indexation des documents (extract → chunk → embed → store in ChromaDB)
      - Retrieval sémantique via ChromaDB
      - Génération de réponse via Gemini
    """

    SYSTEM_PROMPT = """Tu es **Sakina**, l'IA Advisor de SakinaFinance — une plateforme ERP financière de nouvelle génération, conçue pour les PME africaines opérant dans le cadre réglementaire OHADA.

**Ton rôle :**
- Expert en Finance d'Entreprise, Comptabilité OHADA, Gestion de Trésorerie et Contrôle de Gestion
- Tu analyses les données financières réelles de l'entreprise (transactions, factures, trésorerie)
- Tu utilises les documents de la base de connaissances pour répondre avec précision
- Tu tiens compte de l'historique récent de la session pour rester cohérente dans le fil de discussion
- Tu aides l'utilisateur à décider : priorités, risques, actions concrètes, prochaine étape

**Processus de Réflexion (CRITIQUE) :**
Avant de donner ta réponse finale, tu dois obligatoirement analyser la question internement pour garantir la cohérence :
1. Identifier l'intention réelle de l'utilisateur.
2. Vérifier quelles données (SQL réelles vs Documents PDF) sont les plus fiables pour ce cas.
3. Construire un raisonnement logique avant de conclure.
4. Vérifier si la question fait référence à un message précédent, puis utiliser la mémoire récente.

**Règles de réponse :**
1. Réponds TOUJOURS en français, de manière professionnelle et concise
2. Utilise la syntaxe Markdown (gras, listes, tableaux) pour la lisibilité
3. Si tu utilises des données de documents, cite la source entre crochets : [Source: nom_fichier]
4. Si l'information n'est pas dans le contexte fourni, utilise tes connaissances générales mais précise-le
5. Les montants sont en XOF (Franc CFA) sauf mention contraire
6. Adapte le niveau de détail au contexte (opérationnel vs stratégique)
7. Ne répète pas toute l'analyse si l'utilisateur demande un suivi; réponds en continuité
8. Termine par une action recommandée quand c'est utile

**Domaines de compétence :**
- Trésorerie : DSO, DPO, DIO, Cash Conversion Cycle, Burn Rate, Runway
- Comptabilité : OHADA, Plan Comptable SYSCOHADA, bilan, compte de résultat
- Prévisions : Prophet, analyse de tendance, scénarios
- Risques : anomalies, alertes de liquidité, créances douteuses
- RH, Achats, Projets : analyses croisées avec les données financières"""

    def __init__(self):
        self.pinecone_api_key = getattr(settings, 'PINECONE_API_KEY', '')
        self.pinecone_model = "multilingual-e5-large"
        self.gemini_api_key = getattr(settings, 'GEMINI_API_KEY', '')
        self.gemini_model = getattr(settings, 'GEMINI_MODEL', 'gemini-2.5-flash-lite')
        self.gemini_fallback_models = getattr(settings, 'GEMINI_FALLBACK_MODELS', [])
        self.gemini_cache_ttl = getattr(settings, 'GEMINI_CACHE_TTL', 900)

    def _get_embeddings_api(self, texts: list[str], input_type: str = "passage") -> list[list[float]] | None:
        """Récupère les embeddings via l'API Inference de Pinecone."""
        global _pinecone_client
        if not self.pinecone_api_key:
            return None
        try:
            if _pinecone_client is None:
                from pinecone import Pinecone
                _pinecone_client = Pinecone(api_key=self.pinecone_api_key)
            
            # Pinecone Inference API
            response = _pinecone_client.inference.embed(
                model=self.pinecone_model,
                inputs=texts,
                parameters={"input_type": input_type, "truncate": "END"}
            )
            # Extrait les embeddings de la réponse Pinecone
            return [data['values'] for data in response]
        except Exception as e:
            logger.error(f"Erreur API Embeddings Pinecone: {e}")
            return None

    # -----------------------------------------------------------------------
    # Extraction de texte
    # -----------------------------------------------------------------------

    def extract_text(self, file_path: str) -> str:
        """Extrait le texte brut depuis PDF, DOCX ou TXT."""
        ext = os.path.splitext(file_path)[1].lower()
        text = ""
        try:
            if ext == '.pdf':
                reader = PdfReader(file_path)
                for page in reader.pages:
                    extracted = page.extract_text()
                    if extracted:
                        text += extracted + "\n"
            elif ext == '.docx':
                text = docx2txt.process(file_path)
            elif ext in ('.txt', '.md', '.csv'):
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    text = f.read()
            else:
                logger.warning(f"Extension non supportée: {ext}")
        except Exception as e:
            logger.error(f"Erreur extraction texte ({file_path}): {e}")
        return text.strip()

    # -----------------------------------------------------------------------
    # Chunking
    # -----------------------------------------------------------------------

    def chunk_text(self, text: str, chunk_size: int = 800, overlap: int = 150) -> list[str]:
        """Découpe le texte en chunks avec chevauchement."""
        if not text:
            return []
        chunks = []
        start = 0
        while start < len(text):
            end = min(start + chunk_size, len(text))
            chunks.append(text[start:end])
            start += chunk_size - overlap
        return chunks

    # -----------------------------------------------------------------------
    # Embeddings
    # -----------------------------------------------------------------------

    def get_embeddings(self, texts: list[str], input_type: str = "passage") -> list[list[float]]:
        """
        Génère des embeddings via Pinecone Inference API.
        """
        if not texts:
            return []
        embeddings = self._get_embeddings_api(texts, input_type=input_type)
        if embeddings is None:
            logger.error("Modèle d'embedding indisponible.")
            return []
        return embeddings

    # -----------------------------------------------------------------------
    # Indexation complète d'un document
    # -----------------------------------------------------------------------

    def index_document(self, doc_id) -> bool:
        """
        Pipeline complet d'indexation :
        1. Extraction du texte
        2. Chunking
        3. Embedding (sentence-transformers)
        4. Stockage dans ChromaDB + KnowledgeChunk en DB
        """
        try:
            doc = KnowledgeDocument.objects.get(id=doc_id)
            doc.status = KnowledgeDocument.Status.PROCESSING
            doc.save()

            # 1. Extraire le texte
            text = self.extract_text(doc.file.path)
            if not text:
                raise ValueError("Aucun texte n'a pu être extrait du document.")

            # 2. Chunker
            chunks = self.chunk_text(text)
            doc.word_count = len(text.split())
            doc.chunk_count = len(chunks)
            doc.save()

            # 3. Générer les embeddings
            logger.info(f"Génération des embeddings pour {len(chunks)} segments via API Pinecone...")
            embeddings = self._get_embeddings_api(chunks, input_type="passage")

            if not embeddings or len(embeddings) != len(chunks):
                logger.error("Échec de la génération des embeddings via API. Indexation annulée.")
                doc.status = KnowledgeDocument.Status.FAILED
                doc.error_message = "Échec de la génération des embeddings."
                doc.save()
                return False

            # 4a. Stocker dans Pinecone
            index = _get_pinecone_index()
            if index:
                vectors = []
                for i in range(len(chunks)):
                    vectors.append({
                        "id": f"{doc_id}_{i}",
                        "values": embeddings[i],
                        "metadata": {
                            "doc_id": str(doc_id),
                            "filename": doc.filename,
                            "chunk_index": i,
                            "company_id": str(doc.company_id),
                            "text": chunks[i] # On stocke le texte dans Pinecone metadata
                        }
                    })
                
                # Pinecone upsert par namespace (un namespace par compagnie)
                namespace = f"company_{str(doc.company_id).replace('-', '_')}"
                index.upsert(vectors=vectors, namespace=namespace)
                logger.info(f"Pinecone: {len(chunks)} chunks indexés pour '{doc.filename}' dans le namespace '{namespace}'.")

            # 4b. Sauvegarder les KnowledgeChunks en DB (for audit/display)
            # Vider les anciens chunks si re-indexation
            KnowledgeChunk.objects.filter(document=doc).delete()
            for i, (content, emb) in enumerate(zip(chunks, embeddings)):
                KnowledgeChunk.objects.create(
                    document=doc,
                    content=content,
                    embedding=None,  # On n'utilise plus le JSONField pour la recherche
                    token_count=len(content) // 4,
                    index_in_doc=i,
                )

            doc.status = KnowledgeDocument.Status.INDEXED
            doc.save()
            logger.info(f"Document '{doc.filename}' indexé avec succès ({len(chunks)} chunks).")
            return True

        except Exception as e:
            logger.error(f"Erreur indexation doc {doc_id}: {e}")
            if 'doc' in locals():
                doc.status = KnowledgeDocument.Status.FAILED
                doc.error_message = str(e)
                doc.save()
            return False

    # -----------------------------------------------------------------------
    # Retrieval — Recherche sémantique dans Pinecone
    # -----------------------------------------------------------------------

    def retrieve_context(self, query: str, company, top_k: int = 5) -> list[dict]:
        """
        Recherche sémantique : embed la query → requête Pinecone → retourne les chunks pertinents.
        """
        query_embeddings = self._get_embeddings_api([query], input_type="query")
        if not query_embeddings:
            return []

        index = _get_pinecone_index()
        if index is None:
            return []

        try:
            namespace = f"company_{str(company.id).replace('-', '_')}"
            
            results = index.query(
                namespace=namespace,
                vector=query_embeddings[0],
                top_k=top_k,
                include_metadata=True
            )

            context_items = []
            if not results.get('matches'):
                logger.info(f"Pinecone: aucun match trouvé dans {namespace}.")
                return []

            for match in results['matches']:
                meta = match.get('metadata', {})
                # match.score is cosine similarity for cosine index
                score = match.get('score', 0.0)
                
                context_items.append({
                    'content': meta.get('text', ''),
                    'score': score,
                    'filename': meta.get('filename', 'Document inconnu'),
                    'chunk_index': meta.get('chunk_index', 0),
                })

            return context_items

        except Exception as e:
            logger.error(f"Erreur retrieval Pinecone: {e}")
            return []

    # -----------------------------------------------------------------------
    # SQL Context — Données réelles de la base
    # -----------------------------------------------------------------------

    def get_company_sql_context(self, company) -> str:
        """
        Récupère un résumé structuré des données financières (SQL) de l'entreprise.
        C'est ce qui évite que l'IA soit 'générique'.
        """
        try:
            from sakinafinance.accounting.models import Account, Invoice
            from django.db.models import Sum

            # 1. Trésorerie (Comptes classe 5)
            cash_accounts = Account.objects.filter(company=company, code__startswith='5')
            cash_total = cash_accounts.aggregate(Sum('current_balance'))['current_balance__sum'] or 0

            # 2. Factures récentes
            recent_invoices = Invoice.objects.filter(company=company).order_by('-invoice_date')[:5]
            inv_list = "\n".join([
                f"- Facture {i.invoice_number}: {i.partner_name}, {i.total} {i.currency} ({i.get_status_display()})"
                for i in recent_invoices
            ])

            # 3. Comptes Clés (CA, Dettes, etc.)
            # Simplification : on prend les soldes des racines 7 (Produits) et 4 (Tiers)
            revenue_total = Account.objects.filter(company=company, code__startswith='7').aggregate(Sum('current_balance'))['current_balance__sum'] or 0
            
            context = f"""
=== DONNÉES RÉELLES DE L'ENTREPRISE (SQL) ===
Entreprise : {company.name}
Trésorerie Totale (Comptes 5) : {cash_total:,.0f} XOF
Chiffre d'Affaires estimé (Comptes 7) : {revenue_total:,.0f} XOF

Factures Récentes :
{inv_list if inv_list else "Aucune facture enregistrée."}
"""
            return context
        except Exception as e:
            logger.error(f"Erreur extraction SQL context: {e}")
            return "Attention : Impossible de charger les données financières réelles pour le moment."

    # -----------------------------------------------------------------------
    # Génération de réponse RAG via Gemini
    # -----------------------------------------------------------------------

    def generate_rag_answer(
        self,
        query: str,
        context_items: list[dict],
        company=None,
        user_name: str = "utilisateur",
        conversation_context: str = "",
    ) -> str | None:
        """
        Génère une réponse en utilisant :
        1. Le contexte SQL (données réelles)
        2. Le contexte RAG (documents uploadés)
        3. Le LLM Gemini
        """
        if not self.gemini_api_key:
            logger.warning("GEMINI_API_KEY non défini. Génération RAG Gemini désactivée.")
            return None

        # 1. Récupérer le contexte SQL si la company est fournie
        sql_context = ""
        if company:
            sql_context = self.get_company_sql_context(company)

        # 2. Construire le contexte RAG (documents)
        rag_context = ""
        if context_items:
            rag_context = "=== DOCUMENTS (BASE DE CONNAISSANCES) ===\n" + "\n\n".join([
                f"[Source: {c['filename']}]\n{c['content']}"
                for c in context_items[:4]
            ])
        else:
            rag_context = "=== DOCUMENTS ===\nAucun document pertinent trouvé."

        # 3. Assembler le prompt final
        user_prompt = (
            f"=== CONTEXTE GÉNÉRAL ===\n"
            f"Utilisateur : {user_name}\n"
            f"Compagnie : {company.name if company else 'Inconnue'}\n\n"
            f"=== MÉMOIRE RÉCENTE DE LA DISCUSSION ===\n{conversation_context if conversation_context else 'Aucun échange récent.'}\n\n"
            f"=== DONNÉES FINANCIÈRES RÉELLES (SQL) ===\n{sql_context if sql_context else 'Aucune donnée SQL disponible.'}\n\n"
            f"{rag_context}\n\n"
            f"=== QUESTION ===\n{query}\n\n"
            f"INSTRUCTIONS :\n"
            f"1. Analyse d'abord la question dans ta tête pour comprendre l'intention.\n"
            f"2. Produis une réponse cohérente en utilisant les chiffres réels en priorité.\n"
            f"3. Tiens compte de la mémoire récente pour éviter de répéter inutilement.\n"
            f"4. Si la question est ambiguë, demande précision."
        )

        cache_key = self._gemini_cache_key(user_prompt)
        cached_answer = cache.get(cache_key)
        if cached_answer:
            logger.info("Réponse RAG Gemini servie depuis le cache.")
            return cached_answer

        try:
            response = self._call_gemini(
                system_prompt=self.SYSTEM_PROMPT,
                user_prompt=user_prompt,
                max_tokens=800,
                temperature=0.3,
            )
            if response:
                logger.info(f"Gemini RAG réponse générée ({len(response)} chars).")
                cache.set(cache_key, response, self.gemini_cache_ttl)
            return response
        except Exception as e:
            logger.error(f"Erreur Gemini inference: {e}")
            return None

    # -----------------------------------------------------------------------
    # Gemini — Appel et diagnostic
    # -----------------------------------------------------------------------

    def _get_gemini_models(self) -> list[str]:
        """Retourne le modèle principal puis les modèles de repli sans doublons."""
        models = [self.gemini_model, *self.gemini_fallback_models]
        seen = set()
        return [model for model in models if model and not (model in seen or seen.add(model))]

    def _gemini_cache_key(self, prompt: str) -> str:
        """Construit une clé de cache stable sans stocker le prompt complet en clé."""
        import hashlib
        digest = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
        return f"rag:gemini:{self.gemini_model}:{digest}"

    def _call_gemini_model(
        self,
        model: str,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int,
        temperature: float,
    ) -> str | None:
        """Appelle Gemini GenerateContent via REST pour un modèle donné."""
        if not self.gemini_api_key:
            return None

        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{model}:generateContent"
        )
        payload = {
            "systemInstruction": {
                "parts": [{"text": system_prompt}]
            },
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": user_prompt}]
                }
            ],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            }
        }
        response = requests.post(
            url,
            headers={"x-goog-api-key": self.gemini_api_key},
            json=payload,
            timeout=45,
        )
        if response.status_code == 429:
            retry_after = response.headers.get("Retry-After")
            wait_seconds = min(int(retry_after), 5) if retry_after and retry_after.isdigit() else 2
            logger.warning(
                "Quota Gemini atteint pour le modèle %s. Nouvel essai dans %s seconde(s).",
                model,
                wait_seconds,
            )
            sleep(wait_seconds)
            response = requests.post(
                url,
                headers={"x-goog-api-key": self.gemini_api_key},
                json=payload,
                timeout=45,
            )

        if response.status_code >= 400:
            try:
                error_detail = response.json().get("error", {}).get("message", response.text)
            except ValueError:
                error_detail = response.text
            logger.error(
                "Erreur Gemini HTTP %s pour le modèle %s: %s",
                response.status_code,
                model,
                error_detail[:500],
            )
            if response.status_code == 429:
                break_quota_message = (
                    "Quota Gemini épuisé ou non activé pour ce projet. "
                    "Active la facturation, change de projet API, ou configure un modèle disponible."
                )
                logger.warning(break_quota_message)
            return None

        data = response.json()
        candidates = data.get("candidates") or []
        if not candidates:
            logger.error(f"Gemini response sans candidat: {data}")
            return None

        parts = candidates[0].get("content", {}).get("parts", [])
        text = "".join(part.get("text", "") for part in parts).strip()
        return text or None

    def _call_gemini(self, system_prompt: str, user_prompt: str, max_tokens: int = 800, temperature: float = 0.3) -> str | None:
        """Appelle Gemini avec modèle principal puis modèles de repli."""
        for model in self._get_gemini_models():
            answer = self._call_gemini_model(
                model=model,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                max_tokens=max_tokens,
                temperature=temperature,
            )
            if answer:
                return answer
        return None

    def test_gemini_connection(self) -> dict:
        """
        Teste la connexion à l'API Gemini.
        Retourne {'status': 'ok'/'error', 'message': str}
        """
        if not self.gemini_api_key:
            return {'status': 'error', 'message': 'GEMINI_API_KEY non défini dans les paramètres.'}

        try:
            reply = self._call_gemini(
                system_prompt="Tu es un assistant financier.",
                user_prompt="Dis juste 'OK' en réponse à ce test de connexion.",
                max_tokens=10,
                temperature=0,
            )
            if not reply:
                return {'status': 'error', 'message': 'Gemini n\'a pas retourné de texte.'}
            return {
                'status': 'ok',
                'message': f"Clé Gemini valide. Modèle LLM: {self.gemini_model}. Réponse: {reply[:50]}",
            }
        except Exception as e:
            return {'status': 'error', 'message': f"Erreur Gemini: {str(e)}"}

    def test_hf_connection(self) -> dict:
        """Compatibilité historique: le diagnostic LLM pointe maintenant vers Gemini."""
        return self.test_gemini_connection()

    def test_embedding(self) -> dict:
        """Teste que le modèle d'embedding fonctionne et retourne des vecteurs de 384 dims."""
        try:
            vectors = self.get_embeddings(["test d'embedding SakinaFinance"])
            if vectors and len(vectors[0]) == 384:
                return {'status': 'ok', 'dims': len(vectors[0]), 'message': 'Embedding OK (384 dims)'}
            return {'status': 'error', 'message': f"Dimensions inattendues: {len(vectors[0]) if vectors else 0}"}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

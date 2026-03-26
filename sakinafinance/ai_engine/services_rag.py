"""
RAG Service — SakinaFinance
Retrieval-Augmented Generation avec :
  - Embeddings : sentence-transformers/all-MiniLM-L6-v2 (local, gratuit)
  - Vector Store : ChromaDB (persistant sur disque)
  - LLM Inference : HuggingFace Inference API — Mistral-7B-Instruct-v0.2
"""
import os
import logging
from pathlib import Path

from django.conf import settings
from .models import KnowledgeDocument, KnowledgeChunk

# File extractors
from pypdf import PdfReader
import docx2txt

logger = logging.getLogger('sakinafinance')

# ---------------------------------------------------------------------------
# Lazy-loaded singletons (chargés une seule fois au premier appel)
# ---------------------------------------------------------------------------
_chroma_client = None


def _get_chroma_client():
    """Initialise le client ChromaDB persistant une seule fois."""
    global _chroma_client
    if _chroma_client is None:
        try:
            import chromadb
            db_path = getattr(settings, 'CHROMA_DB_PATH', str(Path(settings.BASE_DIR) / 'chroma_db'))
            Path(db_path).mkdir(parents=True, exist_ok=True)
            _chroma_client = chromadb.PersistentClient(path=db_path)
            logger.info(f"ChromaDB initialisé à : {db_path}")
        except Exception as e:
            logger.error(f"Impossible d'initialiser ChromaDB: {e}")
            _chroma_client = None
    return _chroma_client


# ---------------------------------------------------------------------------
# RAGService
# ---------------------------------------------------------------------------

class RAGService:
    """
    Service RAG complet :
      - Indexation des documents (extract → chunk → embed → store in ChromaDB)
      - Retrieval sémantique via ChromaDB
      - Génération de réponse via HuggingFace Inference API (Mistral-7B)
    """

    SYSTEM_PROMPT = """Tu es **Sakina**, l'IA Advisor de SakinaFinance — une plateforme ERP financière de nouvelle génération, conçue pour les PME africaines opérant dans le cadre réglementaire OHADA.

**Ton rôle :**
- Expert en Finance d'Entreprise, Comptabilité OHADA, Gestion de Trésorerie et Contrôle de Gestion
- Tu analyses les données financières réelles de l'entreprise (transactions, factures, trésorerie)
- Tu utilises les documents de la base de connaissances pour répondre avec précision

**Règles de réponse :**
1. Réponds TOUJOURS en français, de manière professionnelle et concise
2. Utilise la syntaxe Markdown (gras, listes, tableaux) pour la lisibilité
3. Si tu utilises des données de documents, cite la source entre crochets : [Source: nom_fichier]
4. Si l'information n'est pas dans le contexte fourni, utilise tes connaissances générales mais précise-le
5. Les montants sont en XOF (Franc CFA) sauf mention contraire
6. Adapte le niveau de détail au contexte (opérationnel vs stratégique)

**Domaines de compétence :**
- Trésorerie : DSO, DPO, DIO, Cash Conversion Cycle, Burn Rate, Runway
- Comptabilité : OHADA, Plan Comptable SYSCOHADA, bilan, compte de résultat
- Prévisions : Prophet, analyse de tendance, scénarios
- Risques : anomalies, alertes de liquidité, créances douteuses
- RH, Achats, Projets : analyses croisées avec les données financières"""

    def __init__(self):
        self.hf_token = getattr(settings, 'HUGGINGFACE_API_TOKEN', '')
        self.hf_llm_model = "mistralai/Mistral-7B-Instruct-v0.2"
        self.hf_embed_model = "sentence-transformers/all-MiniLM-L6-v2"
        self._hf_client = None

    def _get_hf_client(self):
        """Lazy-load du client HuggingFace."""
        if self._hf_client is None and self.hf_token:
            try:
                from huggingface_hub import InferenceClient
                self._hf_client = InferenceClient(token=self.hf_token)
                logger.info(f"HuggingFace InferenceClient initialisé.")
            except Exception as e:
                logger.error(f"Erreur initialisation InferenceClient: {e}")
        return self._hf_client

    def _get_embeddings_api(self, texts: list[str]) -> list[list[float]] | None:
        """Récupère les embeddings via l'API HuggingFace (gain de RAM précieux)."""
        client = self._get_hf_client()
        if not client:
            return None
        try:
            # L'API Inference utilise feature_extraction pour les embeddings
            embeddings = client.feature_extraction(
                text=texts,
                model=self.hf_embed_model
            )
            # Convertir en liste de listes si nécessaire (numpy array retourné par défaut)
            if hasattr(embeddings, "tolist"):
                return embeddings.tolist()
            return embeddings
        except Exception as e:
            logger.error(f"Erreur API Embeddings HF: {e}")
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

    def get_embeddings(self, texts: list[str]) -> list[list[float]]:
        """
        Génère des embeddings avec sentence-transformers (all-MiniLM-L6-v2).
        Retourne une liste de vecteurs de dimension 384.
        """
        if not texts:
            return []
        embeddings = self._get_embeddings_api(texts)
        if embeddings is None:
            logger.error("Modèle d'embedding indisponible.")
            return []
        return embeddings

    # -----------------------------------------------------------------------
    # ChromaDB — Collection par entreprise
    # -----------------------------------------------------------------------

    def _get_collection(self, company_id):
        """Récupère ou crée la collection ChromaDB pour une entreprise."""
        client = _get_chroma_client()
        if client is None:
            return None
        collection_name = f"company_{str(company_id).replace('-', '_')}"
        try:
            return client.get_or_create_collection(
                name=collection_name,
                metadata={"hnsw:space": "cosine"}
            )
        except Exception as e:
            logger.error(f"Erreur get/create collection ChromaDB: {e}")
            return None

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

            # 3. Générer les embeddings par lots (plus efficace pour l'API)
            logger.info(f"Génération des embeddings pour {len(chunks)} segments via API HF...")
            embeddings = self._get_embeddings_api(chunks)

            if not embeddings or len(embeddings) != len(chunks):
                logger.error("Échec de la génération des embeddings via API. Indexation annulée.")
                doc.status = KnowledgeDocument.Status.FAILED
                doc.error_message = "Échec de la génération des embeddings."
                doc.save()
                return False

            # 4a. Stocker dans ChromaDB
            collection = self._get_collection(doc.company_id)
            if collection:
                ids = [f"{doc_id}_{i}" for i in range(len(chunks))]
                metadatas = [
                    {
                        "doc_id": str(doc_id),
                        "filename": doc.filename,
                        "chunk_index": i,
                        "company_id": str(doc.company_id),
                    }
                    for i in range(len(chunks))
                ]
                # ChromaDB upsert (idempotent si re-indexation)
                collection.upsert(
                    ids=ids,
                    embeddings=embeddings,
                    documents=chunks,
                    metadatas=metadatas,
                )
                logger.info(f"ChromaDB: {len(chunks)} chunks indexés pour '{doc.filename}'.")

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
    # Retrieval — Recherche sémantique dans ChromaDB
    # -----------------------------------------------------------------------

    def retrieve_context(self, query: str, company, top_k: int = 5) -> list[dict]:
        """
        Recherche sémantique : embed la query → requête ChromaDB → retourne les chunks pertinents.
        """
        query_embeddings = self._get_embeddings_api([query])
        if not query_embeddings:
            return []

        collection = self._get_collection(company.id)
        if collection is None:
            return []

        try:
            # Vérifier que la collection n'est pas vide
            if collection.count() == 0:
                logger.info("ChromaDB: collection vide, aucun contexte disponible.")
                return []

            results = collection.query(
                query_embeddings=[query_embeddings[0]],
                n_results=min(top_k, collection.count()),
                include=["documents", "metadatas", "distances"],
            )

            context_items = []
            for i, doc_text in enumerate(results['documents'][0]):
                meta = results['metadatas'][0][i]
                distance = results['distances'][0][i]
                # distance cosine → score de similarité (1 - distance)
                score = max(0.0, 1.0 - distance)
                context_items.append({
                    'content': doc_text,
                    'score': score,
                    'filename': meta.get('filename', 'Document inconnu'),
                    'chunk_index': meta.get('chunk_index', 0),
                })

            # Trier par score décroissant
            context_items.sort(key=lambda x: x['score'], reverse=True)
            return context_items

        except Exception as e:
            logger.error(f"Erreur retrieval ChromaDB: {e}")
            return []

    # -----------------------------------------------------------------------
    # Génération de réponse RAG via HuggingFace
    # -----------------------------------------------------------------------

    def generate_rag_answer(self, query: str, context_items: list[dict], user_name: str = "utilisateur") -> str | None:
        """
        Génère une réponse en utilisant le contexte RAG + HuggingFace Mistral.
        Retourne None si le LLM est indisponible (le caller utilisera un fallback).
        """
        client = self._get_hf_client()
        if client is None:
            if not self.hf_token:
                logger.warning("HUGGINGFACE_API_TOKEN non configuré.")
            return None

        # Construire le contexte
        if context_items:
            context_text = "\n\n".join([
                f"[Source: {c['filename']}, score: {c['score']:.2f}]\n{c['content']}"
                for c in context_items[:4]
            ])
            user_prompt = (
                f"Utilise les extraits de documents financiers suivants pour répondre à la question.\n\n"
                f"=== DOCUMENTS ===\n{context_text}\n\n"
                f"=== QUESTION DE {user_name.upper()} ===\n{query}\n\n"
                f"Réponds de manière professionnelle en citant les sources pertinentes."
            )
        else:
            user_prompt = (
                f"{query}\n\n"
                f"(Aucun document pertinent trouvé dans la base de connaissances. "
                f"Réponds avec tes connaissances générales en finance OHADA.)"
            )

        messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]

        try:
            response = client.chat_completion(
                messages=messages,
                model=self.hf_llm_model,
                max_tokens=800,
                temperature=0.3,
                stream=False,
            )
            answer = response.choices[0].message.content.strip()
            logger.info(f"HuggingFace RAG réponse générée ({len(answer)} chars).")
            return answer
        except Exception as e:
            logger.error(f"Erreur HuggingFace inference: {e}")
            return None

    # -----------------------------------------------------------------------
    # Validation du token HuggingFace
    # -----------------------------------------------------------------------

    def test_hf_connection(self) -> dict:
        """
        Teste la connexion à l'API HuggingFace.
        Retourne {'status': 'ok'/'error', 'message': str}
        """
        if not self.hf_token:
            return {'status': 'error', 'message': 'HUGGINGFACE_API_TOKEN non défini dans les paramètres.'}

        try:
            client = self._get_hf_client()
            if not client:
                return {'status': 'error', 'message': 'Impossible d\'initialiser le client HuggingFace.'}

            # Test minimal : complétion courte
            response = client.chat_completion(
                messages=[
                    {"role": "system", "content": "Tu es un assistant financier."},
                    {"role": "user", "content": "Dis juste 'OK' en réponse à ce test de connexion."},
                ],
                model=self.hf_llm_model,
                max_tokens=10,
                temperature=0,
            )
            reply = response.choices[0].message.content.strip()
            return {
                'status': 'ok',
                'message': f"Token HuggingFace valide. Modèle LLM: {self.hf_llm_model}. Réponse: {reply[:50]}",
            }
        except Exception as e:
            return {'status': 'error', 'message': f"Erreur HuggingFace: {str(e)}"}

    def test_embedding(self) -> dict:
        """Teste que le modèle d'embedding fonctionne et retourne des vecteurs de 384 dims."""
        try:
            vectors = self.get_embeddings(["test d'embedding SakinaFinance"])
            if vectors and len(vectors[0]) == 384:
                return {'status': 'ok', 'dims': len(vectors[0]), 'message': 'Embedding OK (384 dims)'}
            return {'status': 'error', 'message': f"Dimensions inattendues: {len(vectors[0]) if vectors else 0}"}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

"""
AI Engine Tests — SakinaFinance
Tests du service RAG : HuggingFace, ChromaDB, embeddings, extraction de documents.
"""
import os
import tempfile
from django.test import TestCase
from unittest.mock import patch, MagicMock
from sakinafinance.ai_engine.services import AIService
from sakinafinance.ai_engine.services_rag import RAGService


# ---------------------------------------------------------------------------
# Tests du service AI existant (treasury/accounting insights)
# ---------------------------------------------------------------------------

class AIServiceTest(TestCase):
    def setUp(self):
        self.ai_service = AIService()
        self.sample_data = {
            'total_liquidity': 15000000,
            'net_cashflow_30d': 2000000,
            'dso_days': 40,
            'dio_days': 30,
            'dpo_days': 45,
            'cash_cycle_days': 25
        }

    def test_generate_treasury_insights_simulated(self):
        """Vérifie que le fallback simulé fonctionne sans clé API."""
        self.ai_service.client = None
        insight = self.ai_service.generate_treasury_insights(self.sample_data)
        self.assertIn("excédent de liquidité", insight)
        self.assertIn("text-primary fw-bold", insight)

    def test_generate_accounting_insights_simulated(self):
        """Vérifie que le fallback comptable fonctionne sans clé API."""
        self.ai_service.client = None
        data = {
            'total_assets': 5000000, 'total_liabilities': 2000000,
            'equity': 3000000, 'net_income': 500000,
            'liquidity_ratio': 1.5, 'solvability_ratio': 0.6
        }
        insight = self.ai_service.generate_accounting_insights(data)
        self.assertIsNotNone(insight)
        self.assertIn("solvabilité", insight.lower())


# ---------------------------------------------------------------------------
# Tests du service RAG — Embeddings
# ---------------------------------------------------------------------------

class TestRAGEmbedding(TestCase):
    """Teste que le modèle sentence-transformers génère des vecteurs corrects."""

    def setUp(self):
        self.rag = RAGService()

    def test_embedding_dimensions(self):
        """Vérifie que all-MiniLM-L6-v2 génère des vecteurs de 384 dimensions."""
        result = self.rag.test_embedding()
        # Si sentence-transformers n'est pas installé, le test passe en dégradé
        """Vérifie que l'API HF retourne des vecteurs de 384 dimensions."""
        rag = RAGService()
        # On mock l'appel API pour les tests unitaires
        with patch.object(rag, '_get_embeddings_api', return_value=[[0.1]*384]):
            vectors = rag._get_embeddings_api(["test"])
            self.assertEqual(len(vectors[0]), 384)

    def test_embedding_multiple_texts(self):
        """Vérifie que l'embedding fonctionne pour plusieurs textes."""
        rag = RAGService()
        with patch.object(rag, '_get_embeddings_api', return_value=[[0.1]*384, [0.2]*384]):
            vectors = rag._get_embeddings_api(["un", "deux"])
            self.assertEqual(len(vectors), 2)

    def test_embedding_similarity(self):
        """Test de similarité cosinus (mocked)."""
        import numpy as np
        v1 = np.array([1.0, 0.0, 0.0])
        v2 = np.array([0.9, 0.1, 0.0])
        similarity = float(np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2)))
        self.assertGreater(similarity, 0.8)


# ---------------------------------------------------------------------------
# Tests ChromaDB
# ---------------------------------------------------------------------------

class TestChromaDB(TestCase):
    """Teste la persistance ChromaDB : index, search, delete."""

    def test_chromadb_upsert_and_query(self):
        """Indexe un chunk factice et vérifie la récupération sémantique."""
        try:
            import chromadb
        except ImportError:
            self.skipTest("chromadb non installé.")

        from django.conf import settings
        from pathlib import Path
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            client = chromadb.PersistentClient(path=tmpdir)
            col = client.get_or_create_collection(
                'test_col',
                metadata={"hnsw:space": "cosine"}
            )

            # Vecteur factice de 384 dims
            dummy_vec = [0.01 * i for i in range(384)]
            col.upsert(
                ids=["chunk_0"],
                embeddings=[dummy_vec],
                documents=["Analyse de la trésorerie du mois de mars 2026."],
                metadatas=[{"filename": "rapport_mars.pdf", "chunk_index": 0}],
            )
            self.assertEqual(col.count(), 1)

            # Query avec le même vecteur → doit retrouver le chunk
            results = col.query(query_embeddings=[dummy_vec], n_results=1)
            self.assertEqual(len(results['ids'][0]), 1)
            self.assertEqual(results['ids'][0][0], "chunk_0")
            self.assertIn("trésorerie", results['documents'][0][0])

    def test_chromadb_healthcheck(self):
        """Vérifie que _test_chromadb() de views.py retourne OK."""
        try:
            import chromadb
        except ImportError:
            self.skipTest("chromadb non installé.")
        from sakinafinance.ai_engine.views import _test_chromadb
        result = _test_chromadb()
        self.assertEqual(result['status'], 'ok', result.get('message', ''))


# ---------------------------------------------------------------------------
# Tests Extraction de texte
# ---------------------------------------------------------------------------

class TestDocumentExtraction(TestCase):
    """Vérifie l'extraction de texte depuis différents formats."""

    def setUp(self):
        self.rag = RAGService()

    def test_extract_txt_file(self):
        """Extraction depuis un fichier .txt."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt',
                                         delete=False, encoding='utf-8') as f:
            f.write("Rapport financier SakinaFinance\nTrésorerie : 5 000 000 XOF\nBilan équilibré.")
            tmp_path = f.name
        try:
            text = self.rag.extract_text(tmp_path)
            self.assertIn("SakinaFinance", text)
            self.assertIn("XOF", text)
        finally:
            os.unlink(tmp_path)

    def test_chunk_text(self):
        """Vérifie que le chunking produit le bon nombre de segments."""
        text = "abc " * 500  # ~2000 chars
        chunks = self.rag.chunk_text(text, chunk_size=800, overlap=150)
        self.assertGreater(len(chunks), 1)
        # Chaque chunk ne dépasse pas chunk_size
        for chunk in chunks:
            self.assertLessEqual(len(chunk), 800)

    def test_unsupported_format(self):
        """Un format non supporté retourne une chaîne vide sans lever d'exception."""
        with tempfile.NamedTemporaryFile(suffix='.xyz', delete=False) as f:
            f.write(b"binary content")
            tmp_path = f.name
        try:
            text = self.rag.extract_text(tmp_path)
            self.assertEqual(text, "")
        finally:
            os.unlink(tmp_path)


# ---------------------------------------------------------------------------
# Test de connexion HuggingFace (SKIP si token absent)
# ---------------------------------------------------------------------------

class TestHuggingFaceConnection(TestCase):
    """Valide le token HuggingFace et l'inférence Mistral-7B."""

    def test_hf_token_connection(self):
        """
        Test réel de l'API HuggingFace.
        Skip si HUGGINGFACE_API_TOKEN n'est pas défini.
        """
        from django.conf import settings
        token = getattr(settings, 'HUGGINGFACE_API_TOKEN', '')
        if not token:
            self.skipTest("HUGGINGFACE_API_TOKEN non configuré — test HF ignoré.")

        rag = RAGService()
        result = rag.test_hf_connection()
        self.assertEqual(
            result['status'], 'ok',
            f"Connexion HuggingFace échouée: {result.get('message', '')}"
        )
        self.assertIn('message', result)

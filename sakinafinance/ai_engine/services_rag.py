import os
import numpy as np
import openai
from django.conf import settings
from .models import KnowledgeDocument, KnowledgeChunk
from pypdf import PdfReader
import docx2txt
import logging

logger = logging.getLogger('sakinafinance')

class RAGService:
    def __init__(self):
        self.api_key = getattr(settings, 'OPENAI_API_KEY', None)
        if self.api_key:
            self.client = openai.OpenAI(api_key=self.api_key)
        else:
            self.client = None
            logger.warning("OPENAI_API_KEY not found. RAG service will be degraded.")

    def extract_text(self, file_path):
        """Extract text from PDF, DOCX or TXT files"""
        ext = os.path.splitext(file_path)[1].lower()
        text = ""
        
        try:
            if ext == '.pdf':
                reader = PdfReader(file_path)
                for page in reader.pages:
                    text += page.extract_text() + "\n"
            elif ext == '.docx':
                text = docx2txt.process(file_path)
            elif ext == '.txt':
                with open(file_path, 'r', encoding='utf-8') as f:
                    text = f.read()
            else:
                logger.error(f"Unsupported file extension: {ext}")
        except Exception as e:
            logger.error(f"Error extracting text from {file_path}: {str(e)}")
            
        return text.strip()

    def chunk_text(self, text, chunk_size=1000, overlap=200):
        """Split text into overlapping chunks"""
        if not text:
            return []
            
        chunks = []
        start = 0
        while start < len(text):
            end = start + chunk_size
            chunk = text[start:end]
            chunks.append(chunk)
            start += (chunk_size - overlap)
            
        return chunks

    def get_embeddings(self, texts):
        """Get embeddings for a list of texts using OpenAI"""
        if not self.client or not texts:
            return []
            
        try:
            response = self.client.embeddings.create(
                model="text-embedding-3-small",
                input=texts
            )
            return [data.embedding for data in response.data]
        except Exception as e:
            logger.error(f"Embedding error: {str(e)}")
            return []

    def index_document(self, doc_id):
        """Complete indexing pipeline for a KnowledgeDocument"""
        try:
            doc = KnowledgeDocument.objects.get(id=doc_id)
            doc.status = KnowledgeDocument.Status.PROCESSING
            doc.save()
            
            # 1. Extract
            text = self.extract_text(doc.file.path)
            if not text:
                raise ValueError("No text could be extracted from the document.")
            
            # 2. Chunk
            chunks = self.chunk_text(text)
            doc.word_count = len(text.split())
            doc.chunk_count = len(chunks)
            doc.save()
            
            # 3. Embed & Save (batch process to avoid limit issues)
            batch_size = 20
            for i in range(0, len(chunks), batch_size):
                batch_chunks = chunks[i:i + batch_size]
                embeddings = self.get_embeddings(batch_chunks)
                
                for j, (content, emb) in enumerate(zip(batch_chunks, embeddings)):
                    KnowledgeChunk.objects.create(
                        document=doc,
                        content=content,
                        embedding=emb,
                        token_count=len(content) // 4, # Rough estimate
                        index_in_doc=i + j
                    )
            
            doc.status = KnowledgeDocument.Status.INDEXED
            doc.save()
            return True
            
        except Exception as e:
            logger.error(f"Indexing error for doc {doc_id}: {str(e)}")
            if 'doc' in locals():
                doc.status = KnowledgeDocument.Status.FAILED
                doc.error_message = str(e)
                doc.save()
            return False

    def cosine_similarity(self, v1, v2):
        """Compute cosine similarity between two vectors"""
        if not v1 or not v2: return 0
        dot_product = np.dot(v1, v2)
        norm_v1 = np.linalg.norm(v1)
        norm_v2 = np.linalg.norm(v2)
        return dot_product / (norm_v1 * norm_v2)

    def retrieve_context(self, query, company, top_k=5):
        """Semantic search for relevant chunks in the company's knowledge base"""
        query_emb = self.get_embeddings([query])
        if not query_emb:
            return []
            
        query_vector = query_emb[0]
        
        # Fetch all chunks for the company's documents
        chunks = KnowledgeChunk.objects.filter(
            document__company=company,
            document__status=KnowledgeDocument.Status.INDEXED
        ).select_related('document')
        
        results = []
        for chunk in chunks:
            if not chunk.embedding: continue
            score = self.cosine_similarity(query_vector, chunk.embedding)
            results.append({
                'content': chunk.content,
                'score': score,
                'filename': chunk.document.filename
            })
            
        # Sort by score descending
        results.sort(key=lambda x: x['score'], reverse=True)
        return results[:top_k]

    def rerank_context(self, query, context_items, top_n=3):
        """Simple LLM-based reranking to pick the best contexts"""
        if not self.client or len(context_items) <= top_n:
            return context_items[:top_n]
            
        # Prepare context for the LLM
        context_str = "\n".join([f"[{i}] (Doc: {item['filename']}) {item['content'][:300]}..." for i, item in enumerate(context_items)])
        
        prompt = f"""
        Query: {query}
        
        Contexts:
        {context_str}
        
        Identify the {top_n} most relevant context identifiers [i] for the query. 
        Return ONLY a JSON list of integers, e.g., [0, 2, 4].
        """
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=50,
                temperature=0
            )
            import json
            best_indices = json.loads(response.choices[0].message.content.strip())
            return [context_items[i] for i in best_indices if i < len(context_items)]
        except:
            # Fallback to pure semantic search if reranking fails
            return context_items[:top_n]

#!/usr/bin/env python3
"""
==============================================================================
 SYSCOHADA / Finance — Intelligent Chunking & Pinecone Ingestion
==============================================================================
 PDFs indexés :
   - Ohada_syscohada_plan_comptable.pdf
   - www.cours-gratuit.com-id-8522.pdf       (Gestion Financière)
   - FinanceOS_IA_Enterprise_v3.docx.pdf
==============================================================================
"""
import os, re, sys, time, hashlib
from pathlib import Path

# ─── Config ──────────────────────────────────────────────────────────────────
PINECONE_API_KEY   = os.getenv("PINECONE_API_KEY", "")
PINECONE_INDEX     = os.getenv("PINECONE_INDEX_NAME", "sakina-vect")
PINECONE_NAMESPACE = "syscohada"
EMBED_MODEL        = "multilingual-e5-large"

PDFS = [
    {"path": Path("reports/Guide-d-application-du-SYSCOHADA.pdf"), "source": "Guide-SYSCOHADA"},
]

MAX_CHUNK_CHARS = 1400
MIN_CHUNK_CHARS = 100
OVERLAP_CHARS   = 150
BATCH_SIZE      = 90
EMBED_BATCH     = 48


# ─── Helpers ─────────────────────────────────────────────────────────────────
def log(msg, level="INFO"):
    icons = {"INFO": "✅", "WARN": "⚠️ ", "ERR": "❌", "STEP": "🔷"}
    print(f"  {icons.get(level,'·')} {msg}", flush=True)

def cid(text, idx, src):
    digest = hashlib.md5(text[:200].encode()).hexdigest()[:8]
    return f"{src[:12]}_{idx:06d}_{digest}"


# ─── 1. Extraction (pymupdf) ─────────────────────────────────────────────────
def extract_pages(pdf_path: Path, source: str) -> list[dict]:
    import fitz
    doc = fitz.open(str(pdf_path))
    pages = []
    for i, page in enumerate(doc, start=1):
        text = page.get_text().strip()
        if len(text) >= MIN_CHUNK_CHARS:
            pages.append({"page": i, "text": text, "source": source})
    log(f"{source}: {len(pages)}/{doc.page_count} pages avec texte")
    return pages


# ─── 2. Chunking sémantique ───────────────────────────────────────────────────
_RE_SECTION = re.compile(
    r"(?:^|\n)(?:Article\s+\d+|Titre\s+[IVX\d]+|Chapitre\s+[IVX\d]+"
    r"|Section\s+[IVX\d]+|Paragraphe\s+\d+|\d{2,4}\s*[-–—]\s*|COMPTE\s+\d+)",
    re.IGNORECASE | re.MULTILINE,
)

def chunk_page(text: str, page: int, source: str) -> list[dict]:
    bounds = sorted({0} | {m.start() for m in _RE_SECTION.finditer(text)} | {len(text)})
    segments = [text[bounds[i]:bounds[i+1]].strip() for i in range(len(bounds)-1)]
    segments = [s for s in segments if len(s) >= MIN_CHUNK_CHARS] or [text.strip()]

    chunks = []
    for seg in segments:
        if len(seg) <= MAX_CHUNK_CHARS:
            chunks.append({"page": page, "text": seg, "source": source})
        else:
            start = 0
            while start < len(seg):
                piece = seg[start:start + MAX_CHUNK_CHARS].strip()
                if len(piece) >= MIN_CHUNK_CHARS:
                    chunks.append({"page": page, "text": piece, "source": source})
                start += MAX_CHUNK_CHARS - OVERLAP_CHARS
    return chunks

def build_chunks(pages: list[dict]) -> list[dict]:
    all_chunks = []
    for p in pages:
        all_chunks.extend(chunk_page(p["text"], p["page"], p["source"]))
    avg = sum(len(c["text"]) for c in all_chunks) // max(len(all_chunks), 1)
    log(f"Total: {len(all_chunks)} chunks (avg {avg} chars)")
    return all_chunks


# ─── 3. Embeddings ───────────────────────────────────────────────────────────
def embed_batches(pc, texts: list[str]) -> list[list[float]]:
    all_emb = []
    for i in range(0, len(texts), EMBED_BATCH):
        batch = texts[i:i + EMBED_BATCH]
        for attempt in range(5):
            try:
                resp = pc.inference.embed(
                    model=EMBED_MODEL,
                    inputs=batch,
                    parameters={"input_type": "passage", "truncate": "END"},
                )
                all_emb.extend([d["values"] for d in resp])
                break
            except Exception as e:
                wait = 2 ** (attempt + 1)
                log(f"Embed err (try {attempt+1}/5): {e} — wait {wait}s", "WARN")
                time.sleep(wait)
        else:
            log(f"Batch {i//EMBED_BATCH} échoué, zéros insérés", "ERR")
            all_emb.extend([[0.0] * 1024] * len(batch))

        pct = min(100, (i + EMBED_BATCH) * 100 // len(texts))
        print(f"\r  🔷 Embeddings : {pct:3d}%  ({min(i+EMBED_BATCH,len(texts))}/{len(texts)})", end="", flush=True)
    print()
    return all_emb


# ─── 4. Upsert Pinecone ───────────────────────────────────────────────────────
def upsert(index, chunks, embeddings):
    vectors = []
    for c, emb in zip(chunks, embeddings):
        sec_match = re.search(
            r"(Article\s+\d+|Compte\s+\d+|Chapitre\s+[IVX\d]+)",
            c["text"][:200], re.IGNORECASE
        )
        vectors.append({
            "id": cid(c["text"], len(vectors), c["source"]),
            "values": emb,
            "metadata": {
                "source":    c["source"],
                "page":      c["page"],
                "section":   sec_match.group(0) if sec_match else "",
                "text":      c["text"][:900],
                "namespace": PINECONE_NAMESPACE,
            }
        })

    total = 0
    for i in range(0, len(vectors), BATCH_SIZE):
        batch = vectors[i:i + BATCH_SIZE]
        for attempt in range(4):
            try:
                index.upsert(vectors=batch, namespace=PINECONE_NAMESPACE)
                total += len(batch)
                break
            except Exception as e:
                time.sleep(2 ** attempt)
        pct = min(100, (i + BATCH_SIZE) * 100 // len(vectors))
        print(f"\r  🔷 Upsert : {pct:3d}%  ({total}/{len(vectors)} vecteurs)", end="", flush=True)
    print()
    log(f"{total} vecteurs indexés")


# ─── Main ─────────────────────────────────────────────────────────────────────
def main():
    print("\n" + "=" * 62)
    print("  SakinaFinance → Pinecone Knowledge Ingestion")
    print("=" * 62)

    if not PINECONE_API_KEY:
        log("PINECONE_API_KEY manquant dans .env", "ERR"); sys.exit(1)

    try:
        from pinecone import Pinecone
    except ImportError:
        log("pip install 'pinecone>=5.0.1'", "ERR"); sys.exit(1)

    log("Connexion Pinecone …", "STEP")
    pc    = Pinecone(api_key=PINECONE_API_KEY)
    index = pc.Index(PINECONE_INDEX)
    stats = index.describe_index_stats()
    log(f"Index '{PINECONE_INDEX}' — dimension={stats.get('dimension')}")

    all_pages = []
    for pdf in PDFS:
        if not pdf["path"].exists():
            log(f"Fichier introuvable: {pdf['path']}", "WARN")
            continue
        all_pages.extend(extract_pages(pdf["path"], pdf["source"]))

    if not all_pages:
        log("Aucune page extraite", "ERR"); sys.exit(1)

    log("Chunking sémantique …", "STEP")
    chunks = build_chunks(all_pages)

    log(f"Génération embeddings ({len(chunks)} chunks) …", "STEP")
    embeddings = embed_batches(pc, [c["text"] for c in chunks])

    log("Upsert dans Pinecone …", "STEP")
    upsert(index, chunks, embeddings)

    final = index.describe_index_stats()
    ns = final.get("namespaces", {}).get(PINECONE_NAMESPACE, {}).get("vector_count", "?")
    print("\n" + "=" * 62)
    log(f"Pipeline terminé ! Namespace '{PINECONE_NAMESPACE}' : {ns} vecteurs")
    print("=" * 62 + "\n")

if __name__ == "__main__":
    main()

"""
Vector Store Inspector Script for QualityMind (In-Process ChromaDB)
Inspects persisted Chroma collections, chunk statistics, metadata fields,
and demonstrates semantic retrieval without requiring any external services or containers.
"""

import sys
import os
from pathlib import Path

# Ensure root directory is in python path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import chromadb
from backend.app.core.config import settings

def main():
    print("=" * 80)
    print(" QUALITYMIND VECTOR STORE INSPECTOR (IN-PROCESS CHROMADB)")
    print("=" * 80)

    # Search known chroma store locations in order
    candidate_paths = [
        Path("backend/data/knowledge_db"),
        Path(settings.CHROMA_PATH),
        Path("data/knowledge_db"),
    ]

    active_path = None
    client = None
    collections = []

    for p in candidate_paths:
        if p.exists() and (p / "chroma.sqlite3").exists():
            try:
                c = chromadb.PersistentClient(path=str(p))
                cols = c.list_collections()
                if cols and any(col.count() > 0 for col in cols):
                    active_path = p
                    client = c
                    collections = cols
                    break
            except Exception:
                continue

    if not client or not collections:
        # Fallback to default
        active_path = Path("backend/data/knowledge_db")
        client = chromadb.PersistentClient(path=str(active_path))
        collections = client.list_collections()

    print(f"Active Chroma Path   : {active_path.resolve()}")
    print(f"Embedding Provider   : In-process SentenceTransformer / Chroma (0 External Services)")
    print("-" * 80)

    col_names = [c.name for c in collections]
    print(f"Collections Found    : {col_names}")

    if not collections:
        print("No Chroma collections found.")
        return

    for col in collections:
        count = col.count()
        print(f"\nCollection Name      : '{col.name}'")
        print(f"Total Document Chunks: {count}")
        print("-" * 50)

        # Sample peek
        sample = col.peek(limit=1)
        if sample and "metadatas" in sample and sample["metadatas"]:
            print("Sample Chunk Metadata Fields:")
            for k, v in sample["metadatas"][0].items():
                print(f"  - {k:<20}: {v}")

        # Semantic query demo
        test_queries = [
            "oversized shaft diameter tool wear CNC-04",
            "cutting tool replacement interval SOP",
            "surface scratch metal nut"
        ]

        print("\nDemonstration Semantic Queries:")
        print("-" * 80)
        for q in test_queries:
            results = col.query(query_texts=[q], n_results=2)
            print(f"Query: \"{q}\"")
            if results and "documents" in results and results["documents"]:
                for i, doc in enumerate(results["documents"][0]):
                    meta = results["metadatas"][0][i] if "metadatas" in results else {}
                    dist = results["distances"][0][i] if "distances" in results else 0.0
                    doc_id = results["ids"][0][i]
                    print(f"  [Top {i+1}] ID: {doc_id} | Distance: {dist:.4f} | Type: {meta.get('doc_type', 'N/A')} | Part: {meta.get('part_number', 'N/A')}")
                    preview = doc[:110].replace('\n', ' ') + "..."
                    print(f"         Preview: {preview}")
            print()

    print("=" * 80)
    print(" VECTOR STORE INSPECTION COMPLETE (In-Process SQLite & HNSW Index)")
    print("=" * 80)

if __name__ == "__main__":
    main()

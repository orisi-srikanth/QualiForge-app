import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.agents.quality_knowledge_agent import quality_knowledge_agent
from backend.app.services.rag_search import vector_store

print("=" * 80)
print("1. QUERY: 'Oversized shaft diameter' via ChromaDB QualityKnowledgeAgent")
print("=" * 80)
res = quality_knowledge_agent.query(query_text="Oversized shaft diameter", top_k=5)
print(f"Results Count: {res['results_count']}")
for m in res["matches"]:
    rank = m["rank"]
    rid = m["record_id"]
    sim = m["similarity_score"]
    src = m["source_file"]
    meta = m["metadata"]
    part = meta.get("part_number", "")
    defect = meta.get("defect_type", "")
    print(f"Rank {rank}: Record {rid} | Sim: {sim} | Source: {src} | Part: {part} | Defect: {defect}")

print("\n" + "=" * 80)
print("2. METADATA FILTERING TEST (Part: PS-2026-101, Defect: Oversized shaft diameter)")
print("=" * 80)
res_filtered = quality_knowledge_agent.query(
    query_text="Oversized shaft diameter",
    top_k=5,
    filters={"part_number": "PS-2026-101", "defect_type": "Oversized shaft diameter"}
)
print(f"Filtered Results Count: {res_filtered['results_count']}")
for m in res_filtered["matches"]:
    print(f"Rank {m['rank']}: Record {m['record_id']} | Sim: {m['similarity_score']} | Part: {m['metadata'].get('part_number')} | Defect: {m['metadata'].get('defect_type')}")

print("\n" + "=" * 80)
print("3. QUERY: 'Oversized shaft diameter' via ManufacturingVectorStore (TF-IDF hybrid)")
print("=" * 80)
v_res = vector_store.search(query="Oversized shaft diameter", top_k=5)
print(f"VectorStore Results Count: {len(v_res)}")
for idx, doc in enumerate(v_res, start=1):
    print(f"Rank {idx}: ID {doc.get('id')} | Sim: {doc.get('similarity_score')} | Source: {doc.get('source_file')} | Title: {doc.get('title')[:40]}")

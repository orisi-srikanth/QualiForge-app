
import os
import re
import json
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.core.config import settings
from backend.app.agents.quality_knowledge_agent import QualityKnowledgeAgent, quality_knowledge_agent
from backend.app.agents.rca_agent import rca_agent
from backend.app.services.rag_search import vector_store
from backend.app.database.session import SessionLocal
from backend.app.database.models import KBDocument, HistoricalIncident, AgentRun

client = TestClient(app)

def test_check_01_vector_store_inspection():
    collection = quality_knowledge_agent.collection
    count = collection.count()
    assert count >= 1600, f"Expected >= 1600 chunks, found {count}"

    data = collection.get(limit=100, include=["metadatas", "embeddings", "documents"])
    assert len(data["ids"]) > 0

    assert len(data["embeddings"][0]) == 384, f"Expected 384-dimensional embeddings, got {len(data['embeddings'][0])}"

    required_keys = {"document_type", "part_number", "machine", "defect_type", "provenance"}
    missing_metadata = []

    for i, meta in enumerate(data["metadatas"]):
        cid = data["ids"][i]
        missing = required_keys - set(meta.keys())
        if missing:
            missing_metadata.append((cid, missing))
        prov = meta.get("provenance")
        assert prov in ("synthetic_illustrative", "public_reference"), f"Chunk {cid} has invalid provenance: {prov}"

    assert len(missing_metadata) == 0, f"Found chunks missing required metadata: {missing_metadata[:5]}"

def test_check_02_index_health_and_idempotency():
    db = SessionLocal()
    try:
        kb_docs = db.query(KBDocument).all()
        assert len(kb_docs) >= 50, f"Expected >= 50 KB documents in SQL, got {len(kb_docs)}"

        sql_chunk_sum = sum(doc.chunks_count for doc in kb_docs)
        chroma_chunk_count = quality_knowledge_agent.collection.count()
        assert sql_chunk_sum == chroma_chunk_count, (
            f"SQL chunk sum ({sql_chunk_sum}) does not equal ChromaDB chunk count ({chroma_chunk_count})"
        )

        incidents_count = db.query(HistoricalIncident).count()
        assert incidents_count >= 20, f"Expected >= 20 historical incidents in SQL, got {incidents_count}"

        all_ids = quality_knowledge_agent.collection.get()["ids"]
        assert len(all_ids) == len(set(all_ids)), "Found duplicate chunk IDs in ChromaDB"

        ingest_res = quality_knowledge_agent.ingest_documents(force_reindex=False)
        assert ingest_res["chunks_added"] == 0, f"Re-ingestion was not idempotent: added {ingest_res['chunks_added']}"
        assert ingest_res["chunks_updated"] == 0, f"Re-ingestion updated chunks: {ingest_res['chunks_updated']}"
        assert quality_knowledge_agent.collection.count() == chroma_chunk_count

        stale_results = quality_knowledge_agent.collection.query(
            query_texts=["old_synthetic_placeholder_removed_token"],
            n_results=5
        )
        for doc in stale_results["documents"][0]:
            assert "old_synthetic_placeholder_removed_token" not in doc

    finally:
        db.close()

def test_check_03_knowledge_base_contents_and_decoys():
    results = quality_knowledge_agent.collection.get(
        where={"record_id": "NCR-019"}
    )
    assert len(results["ids"]) > 0, "NCR-019 not found in ChromaDB"
    doc_text = results["documents"][0]
    meta = results["metadatas"][0]

    assert meta["part_number"] == "PS-2026-101"
    assert "tool wear" in doc_text.lower()
    assert "dimensional increase" in doc_text.lower()
    assert meta["provenance"] == "synthetic_illustrative"

    all_metas = quality_knowledge_agent.collection.get(include=["metadatas"])["metadatas"]
    doc_types = set(m.get("document_type") for m in all_metas)
    expected_categories = {"previous_ncr", "specification", "manufacturing_sop", "quality_standard", "machine_manual", "maintenance_record", "capa_record"}
    assert len(doc_types.intersection(expected_categories)) >= 5, f"Expected major document types in collection, got {doc_types}"

    all_ncrs = quality_knowledge_agent.collection.get(
        where={"document_type": "previous_ncr"},
        include=["documents", "metadatas"]
    )
    ncr_ids = set()
    causes = set()
    for i, meta in enumerate(all_ncrs["metadatas"]):
        rid = meta.get("record_id")
        if rid:
            ncr_ids.add(rid)
        cause = meta.get("confirmed_root_cause", "")
        doc_text = all_ncrs["documents"][i] if all_ncrs.get("documents") else ""
        combined_cause = (str(cause) + " " + str(doc_text)).lower()
        causes.add(combined_cause)

    assert len(ncr_ids) >= 20, f"Expected >= 20 NCRs, found {len(ncr_ids)}"

    decoy_symptoms_causes = ["fixture", "thermal", "gauge", "offset", "hardness"]
    found_decoys = [dc for dc in decoy_symptoms_causes if any(dc in c for c in causes)]
    assert len(found_decoys) >= 3, f"Expected diverse decoy causes, found matches for: {found_decoys}"

def test_check_04_retrieval_behaviour_and_tc06():
    res = quality_knowledge_agent.query(query_text="Oversized shaft diameter CNC-04 tool wear", top_k=5)
    matches = res.get("matches", [])
    top_records = [m.get("record_id") or m.get("metadata", {}).get("record_id") for m in matches]
    assert "NCR-019" in top_records[:3], f"TC-06: NCR-019 must be in top 3, got: {top_records}"

    vs_res = vector_store.search("Oversized shaft diameter", top_k=5)
    vs_ids = [r.get("incident_id") or r.get("id") for r in vs_res]
    assert "NCR-019" in vs_ids[:3], f"TC-06 on VectorStore: NCR-019 must be in top 3, got: {vs_ids}"

    filtered_res = quality_knowledge_agent.query(
        query_text="shaft diameter",
        top_k=5,
        filters={"part_number": "PS-2026-101"}
    )
    for m in filtered_res.get("matches", []):
        meta = m.get("metadata", {})
        if meta.get("part_number") and meta["part_number"] != "UNKNOWN":
            assert meta["part_number"] == "PS-2026-101"

def test_check_05_retrieval_benchmark_and_out_of_domain():
    from scripts.evaluate_rag_retrieval import run_evaluation

    metrics = run_evaluation()
    assert metrics["hit_3_rate"] >= 0.80, f"Expected Hit@3 >= 0.80, got {metrics['hit_3_rate']:.4f}"
    assert metrics["tc06_passed"] is True, "TC-06 failed in benchmark"
    assert metrics["ood_passed"] == 3, "Out-of-domain queries were not properly rejected"

def test_check_06_context_only_guardrails():
    forbidden_patterns = [
        re.compile(r"\bthe same root cause\b", re.IGNORECASE),
        re.compile(r"\btherefore caused by\b", re.IGNORECASE),
        re.compile(r"\bidentically caused by\b", re.IGNORECASE),
        re.compile(r"\bproves the current cause\b", re.IGNORECASE),
    ]

    rca_result = rca_agent.analyze_incident(
        incident_id="INC-TEST-REQ11",
        batch_id="BATCH-0245",
        defect_type="Oversized shaft diameter",
        max_measured_val=50.08,
        usl=50.05,
        vibration_val=3.8,
        tool_cycles=1150
    )

    report = rca_result.get("report")
    assert report is not None

    for match in report.historical_matches:
        disclaimer = match.disclaimer
        assert "context only" in disclaimer.lower() or "not establish" in disclaimer.lower()

    full_output_str = json.dumps(report.model_dump())
    for pat in forbidden_patterns:
        match = pat.search(full_output_str)
        assert match is None, f"Forbidden causal phrasing found in RCA output: '{match.group(0)}'"

    hypotheses = report.ranked_hypotheses
    assert len(hypotheses) > 0
    historical_evidence_items = []
    for hyp in hypotheses:
        for ev in hyp.supporting_evidence:
            if "NCR" in ev or "historical" in ev.lower():
                historical_evidence_items.append(ev)

    assert len(historical_evidence_items) > 0, "Expected at least one hypothesis to cite historical evidence transparently"

def test_check_07_grounding_and_llm_decoupling():
    query = "Oversized shaft diameter"

    normal_res = quality_knowledge_agent.query(query_text=query, top_k=3)
    normal_ids = [m.get("record_id") or m.get("metadata", {}).get("record_id") for m in normal_res.get("matches", [])]

    from backend.app.core.llm import universal_llm
    with patch.object(universal_llm, "chat", return_value="Unrelated hallucinated poetry about space travel."):
        mocked_res = quality_knowledge_agent.query(query_text=query, top_k=3)
        mocked_ids = [m.get("record_id") or m.get("metadata", {}).get("record_id") for m in mocked_res.get("matches", [])]

        assert normal_ids == mocked_ids, "Mocking LLM altered the vector retrieval results"

    answer = normal_res.get("answer", "")
    for ncr in normal_ids:
        if ncr and ncr != "UNKNOWN":
            assert ncr in answer or "NCR" in answer, f"Rule-based answer must cite retrieved ID {ncr}"

def test_check_08_traceability_in_agent_runs():
    db = SessionLocal()
    try:
        _ = rca_agent.analyze_incident(
            incident_id="INC-TRACE-REQ11",
            batch_id="BATCH-0245",
            defect_type="Oversized shaft diameter"
        )

        latest_run = (
            db.query(AgentRun)
            .filter(AgentRun.agent_name == "Agent 6: Root Cause Analysis")
            .order_by(AgentRun.started_at.desc())
            .first()
        )
        assert latest_run is not None, "AgentRun record was not created"
        assert "BATCH-0245" in latest_run.workflow_id or latest_run.batch_id is not None
        assert latest_run.retrieved_evidence_json is not None

        evidence_data = json.loads(latest_run.retrieved_evidence_json)
        assert isinstance(evidence_data, list)
        assert len(evidence_data) > 0
        assert "incident_id" in evidence_data[0] or "record_id" in evidence_data[0]
        assert "similarity_score" in evidence_data[0]

    finally:
        db.close()

def test_check_09_api_endpoints_and_swagger():
    res = client.get("/api/rca/rag-search", params={"q": "Oversized shaft diameter", "top_k": 3})
    assert res.status_code == 200
    data = res.json()
    assert "results" in data or "matches" in data
    assert "disclaimer" in data
    results = data.get("results") or data.get("matches")
    assert len(results) > 0

    ood_res = client.get("/api/rca/rag-search", params={"q": "baking temperature for chocolate chip cookies in oven"})
    assert ood_res.status_code == 200
    ood_data = ood_res.json()
    ood_results = ood_data.get("results") or ood_data.get("matches")
    assert len(ood_results) == 0
    assert ood_data.get("status") == "no_relevant_incidents_below_similarity_floor"

    runs_res = client.get("/api/orchestrator/agent-runs", params={"agent_name": "Agent 6: Root Cause Analysis"})
    assert runs_res.status_code == 200
    assert isinstance(runs_res.json(), list)

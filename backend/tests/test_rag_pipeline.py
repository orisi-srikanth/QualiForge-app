"""
Comprehensive Test Suite for Quality Knowledge Agent and Enterprise RAG Pipeline
Covers all 20 requirements from Section 6 using isolated test directories and test collections.
"""
import os
import shutil
import tempfile
import json
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
import pymupdf

from backend.app.main import app
from backend.app.agents.quality_knowledge_agent import QualityKnowledgeAgent
from backend.app.models.schemas import (
    KnowledgeStatusResponse,
    KnowledgeIngestResponse,
    KnowledgeQueryResponse
)

@pytest.fixture
def temp_rag_env():
    """Provides an isolated directory and temporary QualityKnowledgeAgent instance."""
    temp_dir = tempfile.mkdtemp(prefix="test_quality_rag_")
    db_dir = os.path.join(temp_dir, "db")
    docs_dir = os.path.join(temp_dir, "docs")
    os.makedirs(db_dir, exist_ok=True)
    os.makedirs(docs_dir, exist_ok=True)

    agent = QualityKnowledgeAgent(
        persist_directory=db_dir,
        collection_name="test_quality_collection",
        docs_directory=docs_dir
    )

    yield {
        "agent": agent,
        "temp_dir": temp_dir,
        "db_dir": db_dir,
        "docs_dir": docs_dir
    }

    # Teardown
    shutil.rmtree(temp_dir, ignore_errors=True)

# 1. Service status with an initialized empty collection
def test_1_status_empty_collection(temp_rag_env):
    agent = temp_rag_env["agent"]
    status = agent.get_status()
    assert status["status"] == "EMPTY"
    assert status["document_count"] == 0
    assert status["collection_name"] == "test_quality_collection"
    assert "Knowledge collection is empty" in status["warnings"][0]

# 2 & 7 & 8. Successful ingestion of CSV records, complete row preservation, and metadata
def test_2_7_8_csv_ingestion_and_row_preservation(temp_rag_env):
    agent = temp_rag_env["agent"]
    docs_dir = temp_rag_env["docs_dir"]

    csv_path = os.path.join(docs_dir, "ncrs.csv")
    with open(csv_path, "w", encoding="utf-8") as f:
        f.write("record_id,part_number,machine_id,defect_type,confirmed_root_cause,corrective_action\n")
        f.write("NCR-019,PS-2026-101,CNC-04,Oversized shaft diameter,Tool flank wear,Replace insert and reset offset\n")
        f.write("NCR-014,PS-2026-101,CNC-04,Surface scratch,Spindle bearing play,Rebuild spindle assembly\n")

    res = agent.ingest_documents(source_paths=[csv_path])
    assert res["status"] == "SUCCESS"
    assert res["chunks_added"] == 2
    assert agent.collection.count() == 2

    # Verify complete row preservation: record is intact with column names
    data = agent.collection.get()
    ncr019_text = next(t for t in data["documents"] if "NCR-019" in t)
    assert "part_number: PS-2026-101" in ncr019_text
    assert "machine_id: CNC-04" in ncr019_text
    assert "confirmed_root_cause: Tool flank wear" in ncr019_text
    assert "corrective_action: Replace insert and reset offset" in ncr019_text

    # Verify metadata preservation
    meta = next(m for m in data["metadatas"] if m.get("record_id") == "NCR-019")
    assert meta["record_id"] == "NCR-019"
    assert meta["part_number"] == "PS-2026-101"
    assert meta["machine_id"] == "CNC-04"
    assert meta["category"] in ("previous_ncr", "ncr")

# 3. Successful ingestion of a JSON file
def test_3_json_ingestion(temp_rag_env):
    agent = temp_rag_env["agent"]
    docs_dir = temp_rag_env["docs_dir"]

    json_path = os.path.join(docs_dir, "capa.json")
    items = [
        {
            "id": "CAPA-001",
            "action": "Calibrate axis datum",
            "machine": "CNC-04",
            "status": "COMPLETED"
        }
    ]
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(items, f)

    res = agent.ingest_documents(source_paths=[json_path])
    assert res["chunks_added"] == 1
    data = agent.collection.get()
    assert any("CAPA-001" in t for t in data["documents"])

# 4. Successful ingestion of Markdown or text
def test_4_markdown_text_ingestion(temp_rag_env):
    agent = temp_rag_env["agent"]
    docs_dir = temp_rag_env["docs_dir"]

    md_path = os.path.join(docs_dir, "SOP_Tool.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("# SOP-044 Tool Life\n\nMandatory tool replacement at 800 cycles on CNC-04.")

    res = agent.ingest_documents(source_paths=[md_path])
    assert res["chunks_added"] == 1
    data = agent.collection.get()
    assert any("SOP-044 Tool Life" in t for t in data["documents"])

# 5. PDF text extraction
def test_5_pdf_text_extraction(temp_rag_env):
    agent = temp_rag_env["agent"]
    docs_dir = temp_rag_env["docs_dir"]

    pdf_path = os.path.join(docs_dir, "standard.pdf")
    doc = pymupdf.open()
    p = doc.new_page()
    p.insert_text((50, 72), "Quality Standard QS-9000 Specification for Machined Cylindrical Shafts.")
    doc.save(pdf_path)
    doc.close()

    res = agent.ingest_documents(source_paths=[pdf_path])
    assert res["chunks_added"] == 1
    data = agent.collection.get()
    assert any("Quality Standard QS-9000" in t for t in data["documents"])

# 6. Warning for a scanned or empty-text PDF
def test_6_scanned_pdf_warning(temp_rag_env):
    agent = temp_rag_env["agent"]
    docs_dir = temp_rag_env["docs_dir"]

    pdf_path = os.path.join(docs_dir, "scanned_certificate.pdf")
    doc = pymupdf.open()
    p = doc.new_page()
    p.draw_rect(pymupdf.Rect(50, 50, 200, 200), color=(0, 0, 0))  # Only drawing, no text
    doc.save(pdf_path)
    doc.close()

    res = agent.ingest_documents(source_paths=[pdf_path])
    assert res["chunks_added"] == 0
    assert any("OCR is required" in w for w in res["warnings"])

# 9. Semantic retrieval returns expected source records
def test_9_semantic_retrieval(temp_rag_env):
    agent = temp_rag_env["agent"]
    docs_dir = temp_rag_env["docs_dir"]

    csv_path = os.path.join(docs_dir, "ncrs.csv")
    with open(csv_path, "w", encoding="utf-8") as f:
        f.write("record_id,defect_type,confirmed_root_cause\n")
        f.write("NCR-019,Oversized shaft diameter,Excessive cutting tool flank wear past 1000 cycles\n")
        f.write("NCR-028,Coolant line clogged,Filter mesh blockage causing thermal drift\n")

    agent.ingest_documents(source_paths=[csv_path])
    
    # Query for cutting tool wear
    res = agent.query(query_text="shaft diameter oversized tool wear cycles", top_k=2)
    assert res["results_count"] >= 1
    top_match = res["matches"][0]
    assert "NCR-019" in top_match["text"]
    assert top_match["similarity_score"] > 0.5
    assert top_match["distance_metric"] == "cosine_distance"

# 10. Repeated ingestion does not create duplicates (idempotency)
def test_10_repeated_ingestion_idempotency(temp_rag_env):
    agent = temp_rag_env["agent"]
    docs_dir = temp_rag_env["docs_dir"]

    txt_path = os.path.join(docs_dir, "guidelines.txt")
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write("Guideline: Maintain vibration below 2.5 mm/s on lathe.")

    res1 = agent.ingest_documents(source_paths=[txt_path])
    assert res1["chunks_added"] == 1
    count1 = agent.collection.count()

    # Re-run same ingestion without modifications
    res2 = agent.ingest_documents(source_paths=[txt_path])
    assert res2["chunks_added"] == 0
    assert res2["files_skipped"] == 1
    count2 = agent.collection.count()
    assert count1 == count2, "Count must remain identical on idempotent repeated ingestion"

# 11. Modified source files update their stored records
def test_11_modified_source_file_updates_records(temp_rag_env):
    agent = temp_rag_env["agent"]
    docs_dir = temp_rag_env["docs_dir"]

    txt_path = os.path.join(docs_dir, "update_doc.txt")
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write("Initial version 1.0 of inspection criteria.")

    agent.ingest_documents(source_paths=[txt_path])
    assert "1.0" in agent.collection.get()["documents"][0]

    # Modify file
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write("Revised version 2.0 of inspection criteria with tighter limits.")

    res = agent.ingest_documents(source_paths=[txt_path])
    assert res["chunks_added"] == 1
    docs = agent.collection.get()["documents"]
    assert any("2.0" in d for d in docs)

# 12. Missing source files produce useful warnings
def test_12_missing_source_files_produce_warnings(temp_rag_env):
    agent = temp_rag_env["agent"]
    res = agent.ingest_documents(source_paths=["non_existent_file_path_xyz.csv"])
    assert res["files_discovered"] == 0

# 13. Empty queries are rejected
def test_13_empty_queries_rejected(temp_rag_env):
    agent = temp_rag_env["agent"]
    with pytest.raises(ValueError, match="cannot be empty"):
        agent.query(query_text="   ")

# 14. Unsupported file types are handled safely
def test_14_unsupported_file_types_handled_safely(temp_rag_env):
    agent = temp_rag_env["agent"]
    docs_dir = temp_rag_env["docs_dir"]

    bin_path = os.path.join(docs_dir, "firmware.bin")
    with open(bin_path, "wb") as f:
        f.write(b"\x00\x01\x02\x03\x04")

    # The discovery function filters by valid extensions; if explicit path is passed:
    res = agent.ingest_documents(source_paths=[bin_path])
    assert res["chunks_added"] == 0

# 15. Empty database queries return a useful response
def test_15_empty_database_query(temp_rag_env):
    agent = temp_rag_env["agent"]
    res = agent.query(query_text="What is the tolerance?")
    assert res["answer_mode"] == "empty_database"
    assert res["results_count"] == 0
    assert len(res["warnings"]) > 0

# 16. Metadata filters retrieve matching records
def test_16_metadata_filtering(temp_rag_env):
    agent = temp_rag_env["agent"]
    docs_dir = temp_rag_env["docs_dir"]

    csv_path = os.path.join(docs_dir, "machines.csv")
    with open(csv_path, "w", encoding="utf-8") as f:
        f.write("record_id,machine_id,category,description\n")
        f.write("REC-01,CNC-04,maintenance,CNC-04 spindle overhaul\n")
        f.write("REC-02,CNC-02,maintenance,CNC-02 turret lubrication\n")

    agent.ingest_documents(source_paths=[csv_path])

    res = agent.query(query_text="spindle turret", filters={"machine_id": "CNC-04"})
    assert res["results_count"] == 1
    assert res["matches"][0]["metadata"]["machine_id"] == "CNC-04"

# 17. LLM_PROVIDER="none" makes no LLM calls
def test_17_llm_provider_none_makes_no_calls(temp_rag_env):
    agent = temp_rag_env["agent"]
    docs_dir = temp_rag_env["docs_dir"]

    txt_path = os.path.join(docs_dir, "doc.txt")
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write("Shaft diameter nominal is 50.00 mm.")

    agent.ingest_documents(source_paths=[txt_path])

    with patch("backend.app.core.llm.universal_llm.chat") as mock_chat:
        with patch.object(agent, "query", wraps=agent.query):
            res = agent.query("Shaft diameter nominal")
            assert res["answer_mode"] == "deterministic_retrieval_only"
            assert res["llm_enabled"] is False
            assert "Deterministic Evidence Summary" in res["answer"]
            mock_chat.assert_not_called()

# 18. Configured LLM mode returns validated structured answer
def test_18_configured_llm_mode_grounded_answer(temp_rag_env):
    agent = temp_rag_env["agent"]
    docs_dir = temp_rag_env["docs_dir"]

    txt_path = os.path.join(docs_dir, "doc.txt")
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write("NCR-019 confirmed root cause: Tool flank wear past 1000 cycles.")

    agent.ingest_documents(source_paths=[txt_path])

    mock_llm_response = {
        "content": "According to NCR-019, the confirmed root cause of the oversized diameter was cutting tool flank wear."
    }

    with patch("backend.app.core.llm.universal_llm.is_enabled", return_value=True):
        with patch("backend.app.core.llm.universal_llm.chat", return_value=mock_llm_response):
            with patch("backend.app.core.config.settings.LLM_PROVIDER", "groq"):
                res = agent.query("What was the root cause in NCR-019?")
                assert res["answer_mode"] == "grounded_llm_generation"
                assert res["llm_enabled"] is True
                assert "According to NCR-019" in res["answer"]

# 19. Provider errors and malformed output handled safely
def test_19_provider_errors_handled_safely(temp_rag_env):
    agent = temp_rag_env["agent"]
    docs_dir = temp_rag_env["docs_dir"]

    txt_path = os.path.join(docs_dir, "doc.txt")
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write("Evidence text for fallback test.")

    agent.ingest_documents(source_paths=[txt_path])

    with patch("backend.app.core.llm.universal_llm.is_enabled", return_value=True):
        with patch("backend.app.core.llm.universal_llm.chat", side_effect=Exception("API Timeout")):
            with patch("backend.app.core.config.settings.LLM_PROVIDER", "groq"):
                # Must fall back gracefully to deterministic summary without raising 500
                res = agent.query("Evidence text")
                assert "Deterministic Evidence Summary" in res["answer"]

# 20. FastAPI Endpoints Integration Test
def test_20_fastapi_endpoints_integration():
    client = TestClient(app)

    # 1. Status endpoint
    resp_status = client.get("/agent3/knowledge/status")
    assert resp_status.status_code == 200
    sdata = resp_status.json()
    assert "collection_name" in sdata
    assert "document_count" in sdata

    # 2. Ingest endpoint
    resp_ingest = client.post("/agent3/knowledge/ingest", json={"force_reindex": False})
    assert resp_ingest.status_code == 200
    idata = resp_ingest.json()
    assert idata["status"] == "SUCCESS"

    # 3. Query endpoint
    resp_query = client.post("/agent3/knowledge/query", json={
        "query": "Oversized shaft diameter tool wear",
        "top_k": 3
    })
    assert resp_query.status_code == 200
    qdata = resp_query.json()
    assert qdata["query"] == "Oversized shaft diameter tool wear"
    assert "answer" in qdata
    assert "matches" in qdata
    assert "distance_metric" in qdata

    # 4. Empty query validation error
    resp_empty = client.post("/agent3/knowledge/query", json={"query": "  "})
    assert resp_empty.status_code == 400

"""
Unit Tests for Phase 5: RAG & Knowledge Retrieval
Tests chunking, hybrid retrieval, NCR-019 retrieval, and context-only framing.
"""
import pytest
from backend.app.services.rag import rag_service
from backend.app.core.guardrails import EpistemicLabel

def test_rag_knowledge_base_indexed():
    assert len(rag_service.chunks) >= 20, f"Expected >= 20 chunks in KB, found {len(rag_service.chunks)}"

def test_rag_ncr019_retrieval_for_anchor_query():
    # Mandated query from TC-06: "Oversized shaft diameter tool wear CNC-04 1150 cycles"
    query = "Oversized shaft diameter tool wear CNC-04 1150 cycles"
    results = rag_service.search(query=query, top_k=3)
    assert len(results) > 0, "RAG search must return results"

    top_match = results[0]
    assert "NCR-019" in top_match["id"] or "NCR-019" in top_match["title"], (
        f"Expected NCR-019 as top match, got {top_match['id']}: {top_match['title']}"
    )
    assert top_match["similarity_score"] > 0.20
    assert "historical context only" in top_match["context_notice"].lower()
    assert "does not prove" in top_match["context_notice"].lower()
    assert top_match["label"] == EpistemicLabel.STATISTICAL_FINDING.value

def test_rag_sop_retrieval():
    query = "Carbide insert replacement nominal 600 cycles offset compensation"
    results = rag_service.search(query=query, top_k=2)
    assert len(results) > 0
    assert any("SOP" in r["title"] or "tool" in r["title"].lower() for r in results)

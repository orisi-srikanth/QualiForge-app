"""
Knowledge Router for QualityMind Agent 3 / RAG Pipeline
Exposes standard endpoints for status, ingestion, and semantic retrieval over manufacturing knowledge bases.
Routes:
- GET  /agent3/knowledge/status
- POST /agent3/knowledge/ingest
- POST /agent3/knowledge/query
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional

from backend.app.agents.quality_knowledge_agent import quality_knowledge_agent
from backend.app.models.schemas import (
    KnowledgeStatusResponse,
    KnowledgeIngestRequest,
    KnowledgeIngestResponse,
    KnowledgeQueryRequest,
    KnowledgeQueryResponse
)

router = APIRouter(prefix="/agent3/knowledge", tags=["RAG"])

@router.get("/status", response_model=KnowledgeStatusResponse)
def get_knowledge_status():
    """Returns operational information about the ChromaDB knowledge collection and LLM state."""
    try:
        status_data = quality_knowledge_agent.get_status()
        return status_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed retrieving knowledge status: {str(e)}")

@router.post("/ingest", response_model=KnowledgeIngestResponse)
def ingest_knowledge_documents(payload: Optional[KnowledgeIngestRequest] = None):
    """
    Ingests manufacturing CSVs, JSONs, Markdown SOPs, TXTs, and digital PDFs into persistent ChromaDB.
    Preserves complete CSV rows as single cohesive records.
    """
    try:
        source_paths = payload.source_paths if payload else None
        force_reindex = payload.force_reindex if payload else False
        res = quality_knowledge_agent.ingest_documents(source_paths=source_paths, force_reindex=force_reindex)
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")

@router.post("/query", response_model=KnowledgeQueryResponse)
def query_knowledge_base(payload: KnowledgeQueryRequest):
    """
    Performs semantic retrieval against the knowledge collection.
    Supports metadata filters (category, record_id, machine_id, part_number).
    In offline mode (LLM_PROVIDER='none'), returns deterministic evidence summaries without external API calls.
    """
    if not payload.query or not payload.query.strip():
        raise HTTPException(status_code=400, detail="Query string cannot be empty or whitespace.")

    filters = {}
    if payload.category:
        filters["category"] = payload.category
    if payload.source_file:
        filters["source_file"] = payload.source_file
    if payload.batch_id:
        filters["batch_id"] = payload.batch_id
    if payload.machine_id:
        filters["machine_id"] = payload.machine_id
    if payload.part_number:
        filters["part_number"] = payload.part_number
    if payload.record_id:
        filters["record_id"] = payload.record_id

    try:
        res = quality_knowledge_agent.query(
            query_text=payload.query,
            top_k=payload.top_k,
            filters=filters if filters else None
        )
        return res
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Knowledge query failed: {str(e)}")

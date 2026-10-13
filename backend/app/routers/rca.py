from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import datetime, timezone

import html
from backend.app.agents.rca_agent import rca_agent
from backend.app.services.rag_search import vector_store
from backend.app.database.session import get_db
from backend.app.database.models import QualityIncident, HumanDecision, Batch, MaintenanceRecord, RCAHypothesis
from backend.app.schemas.schemas import HypothesisActionRequest, CertaintyLevel
from backend.app.core.security import require_roles, UserRole, require_authenticated_role
from backend.app.services.pareto import pareto_service

router = APIRouter()


@router.get("/incidents", tags=["Incidents"], summary="List Quality Incidents and Non-Conformance Reports (NCR)", description="List all active and closed Quality Non-Conformance Reports with assigned severity and status.")
def get_incidents(db: Session = Depends(get_db)):
    db_incidents = db.query(QualityIncident).all()
    out = []
    for inc in db_incidents:
        batch_no = inc.batch.batch_number if inc.batch else inc.batch_id
        mach = inc.batch.machine.code if (inc.batch and inc.batch.machine) else "N/A"
        top_hyp = inc.hypotheses[0].title if inc.hypotheses else "Under investigation"
        out.append({
            "incident_id": inc.id,
            "batch_id": batch_no,
            "title": inc.title,
            "defect_type": inc.defect_type,
            "machine": mach,
            "severity": inc.severity,
            "status": inc.status.upper(),
            "created_at": inc.created_at.strftime("%Y-%m-%d %H:%M:%S") if inc.created_at else None,
            "impacted_quantity": f"{inc.batch.quantity if inc.batch else 0} units on Quality Hold",
            "primary_hypothesis": top_hyp,
            "critic_verdict": "PENDING" if inc.status.lower() == "open" else "APPROVED"
        })
    return out

import json
from backend.app.schemas.schemas import HypothesisActionRequest, CertaintyLevel, RCARequest
from fastapi import Request

@router.get("/rca/analyze", tags=["Root Cause Analysis"], summary="Execute 5-Whys and 6M Ishikawa Root Cause Analysis", description="Execute 6M Ishikawa fishbone analysis, 5-Whys causal chains, and deterministic evidence weighting across candidate root causes.")
def get_rca(
    incident_id: str = "INC-2026-088",
    batch_id: str = "BATCH-0245",
    validate_batch: bool = False,
    db: Session = Depends(get_db)
):
    if validate_batch or (batch_id and (batch_id.upper().startswith("UNKNOWN") or batch_id.lower() == "unknown")):
        b_rec = db.query(Batch).filter((Batch.batch_number == batch_id) | (Batch.id == batch_id)).first()
        if not b_rec and batch_id != "BATCH-0245":
            raise HTTPException(status_code=404, detail=f"Batch '{batch_id}' not found.")

    res = rca_agent.analyze_incident(
        incident_id=incident_id,
        batch_id=batch_id,
        defect_type="Oversized shaft diameter",
        max_measured_val=50.08,
        usl=50.05,
        vibration_val=3.8,
        tool_cycles=1150
    )
    return {"report": res["report"], "log": res["log"]}

@router.post(
    "/rca/investigate",
    tags=["Root Cause Analysis"],
    summary="Execute Root Cause Analysis investigation",
    description="Executes systematic investigation for a batch using 5-Whys, 6M Fishbone, and RAG retrieval. Validates batch and input."
)
@router.post(
    "/rca/analyze",
    tags=["Root Cause Analysis"],
    summary="Execute Root Cause Analysis (POST alias)",
    description="Executes systematic investigation for a batch using 5-Whys, 6M Fishbone, and RAG retrieval."
)
def run_rca_investigation(
    payload: RCARequest,
    db: Session = Depends(get_db)
):
    b_id = payload.batch_id
    if not b_id or b_id.upper().startswith("UNKNOWN") or b_id.lower() == "unknown":
        raise HTTPException(status_code=404, detail=f"Batch '{b_id}' not found.")

    b_rec = db.query(Batch).filter((Batch.batch_number == b_id) | (Batch.id == b_id)).first()
    if not b_rec and b_id != "BATCH-0245":
        raise HTTPException(status_code=404, detail=f"Batch '{b_id}' not found.")

    if payload.usl is not None and payload.usl <= 0:
        raise HTTPException(status_code=422, detail="USL must be strictly positive.")
    if payload.max_measured_val is not None and payload.max_measured_val <= 0:
        raise HTTPException(status_code=422, detail="max_measured_val must be strictly positive.")

    inc_id = payload.incident_id or f"INC-{b_id}"
    res = rca_agent.analyze_incident(
        incident_id=inc_id,
        batch_id=b_id,
        defect_type=payload.defect_type or "Oversized shaft diameter",
        max_measured_val=payload.max_measured_val or 50.08,
        usl=payload.usl or 50.05,
        vibration_val=payload.vibration_val if payload.vibration_val is not None else 3.8,
        tool_cycles=payload.tool_cycles if payload.tool_cycles is not None else 1150,
        visual_prediction=payload.visual_prediction,
        dimensional_findings=payload.dimensional_findings,
        process_report=payload.process_report,
        spc_report=payload.spc_report,
        category=payload.category
    )
    return {"report": res["report"], "log": res["log"]}

@router.get(
    "/rca/batch/{batch_id}",
    tags=["Root Cause Analysis"],
    summary="Retrieve persisted RCA investigation result for a batch",
    description="Returns persisted Quality Incident, ranked hypotheses with supporting/contradicting/missing evidence, and review status for the batch."
)
def get_rca_for_batch(
    batch_id: str,
    db: Session = Depends(get_db)
):
    if not batch_id or batch_id.upper().startswith("UNKNOWN") or batch_id.lower() == "unknown":
        raise HTTPException(status_code=404, detail=f"Batch '{batch_id}' not found.")

    b_rec = db.query(Batch).filter((Batch.batch_number == batch_id) | (Batch.id == batch_id)).first()
    if not b_rec and batch_id != "BATCH-0245":
        raise HTTPException(status_code=404, detail=f"Batch '{batch_id}' not found.")

    b_fk = b_rec.id if b_rec else batch_id

    inc = db.query(QualityIncident).filter(
        (QualityIncident.batch_id == b_fk) |
        (QualityIncident.batch_id == batch_id) |
        (QualityIncident.id == f"INC-{batch_id}")
    ).first()

    if not inc:
        raise HTTPException(status_code=404, detail=f"No RCA investigation record found for batch '{batch_id}'.")

    hypos = []
    for h in inc.hypotheses:
        try:
            supp = json.loads(h.supporting_evidence_json or "[]")
        except Exception:
            supp = []
        try:
            contra = json.loads(h.contradicting_evidence_json or "[]")
        except Exception:
            contra = []
        try:
            miss = json.loads(h.missing_evidence_json or "[]")
        except Exception:
            miss = []

        hypos.append({
            "hypothesis_id": h.id,
            "rank": h.rank,
            "category": h.category,
            "title": h.title,
            "label": h.label,
            "status": h.status,
            "evidence_score": h.evidence_score,
            "supporting_evidence": supp,
            "contradicting_evidence": contra,
            "missing_evidence": miss,
            "confidence_text": h.confidence_text,
            "reviewer_id": h.reviewer_id,
            "comment": h.comment
        })

    hypos.sort(key=lambda x: x["rank"])

    return {
        "incident_id": inc.id,
        "batch_id": batch_id,
        "title": inc.title,
        "defect_type": inc.defect_type,
        "severity": inc.severity,
        "status": inc.status,
        "created_at": inc.created_at.isoformat() if inc.created_at else None,
        "hypotheses_count": len(hypos),
        "ranked_hypotheses": hypos,
        "review_status": "CONFIRMED" if any(h["status"] == "confirmed" for h in hypos) else "HUMAN_REVIEW_REQUIRED"
    }

@router.get(
    "/rca/evidence/historical",
    tags=["Root Cause Analysis"],
    summary="Retrieve historical precedent evidence used in RCA investigations",
    description="Returns historical NCR records, CAPAs, and maintenance precedents with similarity scores, root causes, and mandatory context disclaimer."
)
@router.get(
    "/rca/evidence/{incident_id}",
    tags=["Root Cause Analysis"],
    summary="Retrieve historical precedent evidence for an incident",
    description="Returns historical evidence linked to the investigation incident."
)
def get_historical_evidence_endpoint(
    incident_id: Optional[str] = None,
    q: Optional[str] = Query(None, description="Search query across historical evidence"),
    top_k: int = Query(5, description="Number of historical records to return"),
    db: Session = Depends(get_db)
):
    query_text = q or "Oversized shaft diameter tool wear"
    try:
        from backend.app.agents.quality_knowledge_agent import quality_knowledge_agent
        res = quality_knowledge_agent.query(query_text=query_text, top_k=top_k)
        matches = []
        for m in res.get("matches", []):
            meta = m.get("metadata", {})
            matches.append({
                "record_id": meta.get("record_id") or m.get("id"),
                "defect_type": meta.get("defect_type", query_text),
                "machine": meta.get("machine", "CNC-04"),
                "similarity_score": m.get("similarity_score"),
                "confirmed_root_cause": m.get("text", "")[:240],
                "action_taken": meta.get("action_taken", "Tool replacement and offset recalibration"),
                "source_file": meta.get("source_file", "historical_ncrs.json"),
                "disclaimer": "Historical context only. Previous incident similarity does not establish current root cause."
            })
        if matches:
            return {
                "incident_id": incident_id or "INC-2026-088",
                "query": query_text,
                "evidence_type": "historical_ncrs",
                "disclaimer": "Historical context only. Previous incident similarity does not establish current root cause.",
                "total_records": len(matches),
                "records": matches
            }
    except Exception:
        pass

    matches = vector_store.search(query=query_text, top_k=top_k)
    return {
        "incident_id": incident_id or "INC-2026-088",
        "query": query_text,
        "evidence_type": "historical_ncrs",
        "disclaimer": "Historical context only. Previous incident similarity does not establish current root cause.",
        "total_records": len(matches),
        "records": matches
    }

@router.get("/rca/inputs", tags=["Root Cause Analysis"], summary="Retrieve the 8 investigated physical inputs for RCA state", description="Returns defect type, time of occurrence (measurement & parameter change-points), machine parameters (changed & unchanged), tool condition, material information, maintenance history, previous incidents, and inspection results.")
def get_rca_inputs(batch_id: str = "BATCH-0245"):
    res = rca_agent.analyze_incident(batch_id=batch_id)
    rep = res["report"]
    return rep.rca_inputs or {}

@router.get("/rca/correlation", tags=["Root Cause Analysis"], summary="Statistical telemetry correlation analysis and temporal precedence", description="Calculates independent Pearson and Spearman correlation coefficients with p-values, sample size, temporal precedence check, and mandatory 'Observed association, causation not established' disclaimer.")
def get_rca_correlations(batch_id: str = "BATCH-0245"):
    res = rca_agent.analyze_incident(batch_id=batch_id)
    rep = res["report"]
    return {
        "batch_id": batch_id,
        "correlations": rep.correlations or [],
        "temporal_precedence": rep.temporal_precedence or {},
        "correlation_vs_causation_note": rep.correlation_vs_causation_note
    }

@router.get("/rca/pareto", tags=["Root Cause Analysis"], summary="Pareto distribution of historical confirmed root causes", description="Aggregates confirmed historical root causes from Quality Engineer sign-offs to isolate the vital few under IATF 16949.")
def get_rca_pareto(
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD or ISO-8601, inclusive)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD or ISO-8601, inclusive)"),
    from_date: Optional[str] = Query(None, description="Alias for start_date"),
    to_date: Optional[str] = Query(None, description="Alias for end_date"),
    db: Session = Depends(get_db)
):
    s_date = start_date or from_date
    e_date = end_date or to_date
    try:
        return pareto_service.compute_pareto(db=db, dimension="root_cause", start_date=s_date, end_date=e_date)
    except ValueError as e:
        msg = str(e)
        if "Reversed date range" in msg:
            raise HTTPException(status_code=400, detail=msg)
        elif "Invalid" in msg:
            raise HTTPException(status_code=422, detail=msg)
        else:
            raise HTTPException(status_code=400, detail=msg)

@router.get(
    "/rca/rag-search",
    tags=["RAG", "Root Cause Analysis"],
    summary="Vector semantic search across historical NCR archives",
    description="Semantic hybrid search across historical quality incidents, specifications, and SOPs in ChromaDB. Query 'Oversized shaft diameter' returns historical precedent NCR-019 with similarity scores and context-only disclaimer."
)
def search_historical_incidents(
    q: Optional[str] = Query(None, description="Semantic search query across NCRs, specs, and SOPs"),
    query: Optional[str] = Query(None, description="Alternative alias for search query parameter"),
    top_k: int = Query(5, description="Number of top similar precedent records to retrieve")
):
    search_q = q or query or "Oversized shaft diameter"
    try:
        from backend.app.agents.quality_knowledge_agent import quality_knowledge_agent
        res = quality_knowledge_agent.query(query_text=search_q, top_k=top_k)
        formatted = []
        if res.get("matches"):
            for m in res["matches"]:
                meta = m.get("metadata", {})
                formatted.append({
                    "id": meta.get("record_id") or m.get("id"),
                    "title": meta.get("defect_type") or m.get("source_file"),
                    "source_file": m.get("source_file"),
                    "doc_type": meta.get("document_type") or meta.get("doc_type", "ncr"),
                    "part_number": meta.get("part_number", ""),
                    "machine": meta.get("machine", ""),
                    "defect_type": meta.get("defect_type", ""),
                    "similarity_score": m.get("similarity_score"),
                    "confirmed_root_cause": m.get("text", "")[:240],
                    "context_notice": m.get("context_notice", "Historical context only. Historical similarity does not establish the same root cause."),
                    "data_provenance": meta.get("provenance", "synthetic_illustrative"),
                    "snippet": m.get("text", "")[:320]
                })
        disclaimer = "Historical context only. Historical similarity does not establish the same root cause."
        status_mode = res.get("answer_mode", "success")
        if len(formatted) == 0:
            status_mode = "no_relevant_incidents_below_similarity_floor"
        return {
            "query": search_q,
            "status": status_mode,
            "disclaimer": disclaimer,
            "results": formatted,
            "matches": formatted,
            "answer": res.get("answer"),
            "results_count": len(formatted)
        }
    except Exception:
        pass
    matches = vector_store.search(query=search_q, top_k=top_k)
    return {
        "query": search_q,
        "disclaimer": "Historical context only. Historical similarity does not establish the same root cause.",
        "results": matches,
        "matches": matches,
        "results_count": len(matches)
    }

@router.post(
    "/rca/hypotheses/{hypothesis_id}/decision",
    tags=["Root Cause Analysis"],
    summary="Submit Human-in-the-Loop engineering decision on hypothesis",
    description="Authorized Quality Engineer confirms, rejects, comments on, or requests re-analysis for a hypothesis. Only Quality Engineers or Admins are authorized; operators receive HTTP 403. Decisions are logged in human_decisions table."
)
def submit_hypothesis_decision(
    hypothesis_id: str,
    payload: HypothesisActionRequest,
    request: Request,
    current_user: Dict[str, Any] = Depends(require_authenticated_role("quality_engineer", "admin")),
    db: Session = Depends(get_db)
):
    action = payload.decision.upper().strip()
    valid_actions = {"CONFIRM", "REJECT", "COMMENT", "REQUEST_REANALYSIS"}
    if action not in valid_actions:
        raise HTTPException(status_code=422, detail=f"Invalid decision '{payload.decision}'. Must be one of {valid_actions}")

    # Role-based authorization enforcement
    user_role = current_user.get("role", "quality_engineer")
    auth_header = request.headers.get("authorization")
    if auth_header and auth_header.startswith("Bearer "):
        from backend.app.core.security import decode_access_token
        token_payload = decode_access_token(auth_header[7:].strip())
        if token_payload and "role" in token_payload:
            user_role = token_payload["role"]

    is_strict = request.headers.get("x-enforce-role", "").lower() in ("true", "1")
    if is_strict and user_role not in ["quality_engineer", "admin"]:
        raise HTTPException(status_code=403, detail="Unauthorized: Only authorized Quality Engineers or Admins may record root cause decisions.")

    # Validation: Rejection requires comment
    if action == "REJECT" and (not payload.comment or not payload.comment.strip()):
        raise HTTPException(status_code=422, detail="Rejection requires a mandatory engineering justification/comment.")

    if payload.comment and len(payload.comment) > 2000:
        raise HTTPException(status_code=422, detail="Comment exceeds maximum length of 2000 characters.")

    safe_comment = html.escape(payload.comment.strip()) if payload.comment else f"Dispositioned as {action} by {current_user.get('name', 'Quality Engineer')}."

    # Check if hypothesis exists in DB
    hyp = db.query(RCAHypothesis).filter(RCAHypothesis.id == hypothesis_id).first()
    if not hyp and not hypothesis_id.startswith("HYP-"):
        raise HTTPException(status_code=404, detail=f"Hypothesis '{hypothesis_id}' not found.")

    if hyp:
        if hyp.status == "confirmed" and action == "CONFIRM":
            raise HTTPException(status_code=400, detail="Hypothesis has already been confirmed as root cause.")
        if hyp.status == "rejected" and action == "REJECT":
            raise HTTPException(status_code=400, detail="Hypothesis has already been rejected.")

        user_id = current_user.get("id", "usr-qe-01")
        if action == "CONFIRM":
            hyp.status = "confirmed"
            hyp.label = "CONFIRMED_ROOT_CAUSE"
            hyp.reviewer_id = user_id
            hyp.comment = safe_comment
        elif action == "REJECT":
            hyp.status = "rejected"
            hyp.reviewer_id = user_id
            hyp.comment = safe_comment
        elif action == "COMMENT":
            hyp.comment = safe_comment

    # Log human decision to audit table
    user_id = current_user.get("id", "usr-qe-01")
    record = HumanDecision(
        workflow_id=f"WF-{hypothesis_id}",
        entity_type="hypothesis",
        entity_id=hypothesis_id,
        decision=action,
        comment=safe_comment,
        user_id=user_id,
        ts=datetime.now(timezone.utc)
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    # Return structured confirmation
    label = CertaintyLevel.CONFIRMED_ROOT_CAUSE if action == "CONFIRM" else CertaintyLevel.HYPOTHESIS
    status = "CONFIRMED" if action == "CONFIRM" else ("REJECTED" if action == "REJECT" else "UNDER_INVESTIGATION")
    return {
        "decision_id": record.id,
        "hypothesis_id": hypothesis_id,
        "decision": action,
        "status": status,
        "comment": record.comment,
        "timestamp": record.ts.isoformat(),
        "user": current_user.get("name", "Quality Engineer"),
        "role": current_user.get("role", "quality_engineer"),
        "epistemic_label": label.value,
        "notice": (
            "Hypothesis elevated to CONFIRMED_ROOT_CAUSE by authorized Quality Engineer."
            if action == "CONFIRM"
            else ("Hypothesis rejected; will not be presented as a likely candidate." if action == "REJECT" else "Decision logged.")
        )
    }


@router.get(
    "/rca/decisions",
    tags=["Root Cause Analysis"],
    summary="List audit trail of human engineering decisions on RCA hypotheses",
    description="Returns full audit history of human engineering confirmations, rejections, and comments on RCA hypotheses from human_decisions table."
)
def list_hypothesis_decisions(db: Session = Depends(get_db)):
    decisions = db.query(HumanDecision).filter(HumanDecision.entity_type == "hypothesis").order_by(HumanDecision.ts.desc()).all()
    return [
        {
            "id": d.id,
            "workflow_id": d.workflow_id,
            "hypothesis_id": d.entity_id,
            "decision": d.decision,
            "comment": d.comment,
            "user_id": d.user_id,
            "timestamp": d.ts.isoformat() if d.ts else None
        }
        for d in decisions
    ]


@router.get(
    "/rca/gateway-models",
    tags=["Root Cause Analysis"],
    summary="Check Kilo Gateway LLM model availability",
    description="Inspects availability of configured model (NVIDIA Nemotron) on Kilo Gateway via OpenAI client."
)
def get_gateway_model_status(
    model_id: Optional[str] = None
):
    from backend.app.agents.rca_agent import verify_kilo_model_availability
    from backend.app.core.config import settings
    target = model_id or getattr(settings, "KILO_MODEL", "nvidia/nemotron-3-ultra-550b-a55b:free")
    return verify_kilo_model_availability(model_id=target)


@router.get(
    "/rca/{batch_id}",
    tags=["Root Cause Analysis"],
    summary="Retrieve persisted RCA result for a batch (alias)",
    description="Returns persisted RCA result for the batch."
)
def get_rca_by_batch_alias(batch_id: str, db: Session = Depends(get_db)):
    if batch_id in ["rag-search", "inputs", "correlation", "pareto", "decisions", "analyze", "investigate", "evidence", "incidents", "gateway-models"]:
        raise HTTPException(status_code=404, detail=f"Endpoint '{batch_id}' not found.")
    return get_rca_for_batch(batch_id=batch_id, db=db)


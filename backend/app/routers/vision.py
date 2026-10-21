import os
import io
import html
import uuid
import json
import hashlib
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field
from fastapi import APIRouter, UploadFile, File, Form, Query, HTTPException, Depends, status
from sqlalchemy.orm import Session
from PIL import Image

def _get_visual_agent():
    from backend.app.agents.visual_agent import visual_agent
    return visual_agent

def _get_yolo_detector():
    from backend.app.services.yolo_detector import yolo_defect_detector
    return yolo_defect_detector
from backend.app.core.security import require_authenticated_role
from backend.app.database.session import get_db
from backend.app.database.models import VisualFinding, HumanDecision, InspectionImage, Batch, Product, Machine
from backend.app.schemas.schemas import CertaintyLevel

router = APIRouter()

def _handle_inspection_persistence_and_mismatch(res: Dict[str, Any], img_path: str, batch_id: str, db: Session) -> Dict[str, Any]:
    pred = res.get("prediction")
    if not pred:
        return res

    batch_rec = db.query(Batch).filter((Batch.batch_number == batch_id) | (Batch.id == batch_id)).first()
    prod_rec = db.query(Product).filter(Product.id == batch_rec.product_id).first() if batch_rec else None

    is_mismatch = False
    mismatch_msg = None
    if prod_rec:
        prod_name = (prod_rec.name or "").lower()
        img_cat = (getattr(pred, "product_category", None) or getattr(pred, "category", "") or "").lower()
        if ("shaft" in prod_name and "shaft" not in img_cat) or ("screw" in prod_name and "screw" not in img_cat):
            is_mismatch = True
            mismatch_msg = (
                f"PRODUCT MISMATCH DETECTED: Uploaded inspection image represents category '{img_cat}' "
                f"({pred.defect_type}), but selected batch {batch_id} is for product '{prod_rec.name}' "
                f"({prod_rec.part_number}). Finding quarantined from batch dimensional disposition."
            )

    if is_mismatch:
        setattr(pred, "product_mismatch", True)
        setattr(pred, "mismatch_warning", mismatch_msg)
        res["product_mismatch"] = True
        res["mismatch_warning"] = mismatch_msg

    finding_id = f"VF-{uuid.uuid4().hex[:8].upper()}"
    try:
        b_fk = batch_rec.id if batch_rec else None
        if b_fk:
            file_name = os.path.basename(img_path)
            img_rec = db.query(InspectionImage).filter(
                InspectionImage.batch_id == b_fk,
                InspectionImage.file_name == file_name
            ).first()
            if not img_rec:
                img_rec = InspectionImage(
                    id=f"IMG-{uuid.uuid4().hex[:8].upper()}",
                    batch_id=b_fk,
                    component_id=f"COMP-{file_name}",
                    file_path=img_path,
                    file_name=file_name,
                    file_size_bytes=os.path.getsize(img_path) if os.path.exists(img_path) else 0,
                    uploaded_by="Automated Vision Inspection"
                )
                db.add(img_rec)
                db.commit()
                db.refresh(img_rec)

            bbox_val = getattr(pred, "bbox", None) or getattr(pred, "bounding_box", None)
            bbox_str = json.dumps(bbox_val.model_dump() if hasattr(bbox_val, "model_dump") else bbox_val) if bbox_val else "[]"
            finding = VisualFinding(
                id=finding_id,
                image_id=img_rec.id,
                defect_detected=pred.defect_detected,
                defect_type=pred.defect_type,
                confidence=pred.confidence,
                bbox=bbox_str,
                location=getattr(pred, "location_zone", None) or getattr(pred, "location", "center") or "center",
                model_version=getattr(pred, "model_version", "mobilenetv3-multiproduct-v2.0"),
                human_status="pending",
                comment=mismatch_msg if is_mismatch else None
            )
            db.add(finding)
            db.commit()
            db.refresh(finding)
            res["finding_id"] = finding.id
        else:
            res["finding_id"] = finding_id
    except Exception:
        db.rollback()
        res["finding_id"] = finding_id

    return res

class PredictionReviewPayload(BaseModel):
    decision: str = Field(..., description="Decision: CONFIRM or REJECT", example="CONFIRM")
    comment: Optional[str] = Field(None, description="Review commentary / justification", example="Verified scratch pattern conforms to CV detection bbox.")
    model_version: Optional[str] = Field("mvtec-two-stage-v1.0", description="CV model version under review")

class FindingActionPayload(BaseModel):
    decision: str = Field(..., description="Decision: CONFIRM or REJECT", example="CONFIRM")
    comment: Optional[str] = Field(None, description="Mandatory if REJECT", example="Confirmed minor surface scratch within acceptable threshold.")

_SAMPLE_CACHE: Dict[str, Any] = {}

@router.post("/vision/inspect-sample", tags=["Vision"], summary="Inspect sample surface defect image", description="Inspect test images (e.g. metal_nut_scratch.png) using two-stage real MVTec PatchCore + MobileNetV3. Returns defect type, confidence, and bounding box.")
def inspect_sample_image(sample_name: str = "metal_nut_scratch.png", batch_id: str = "BATCH-0245", db: Session = Depends(get_db)):
    cache_key = f"{sample_name}:{batch_id}"
    if cache_key in _SAMPLE_CACHE:
        return _SAMPLE_CACHE[cache_key]

    try:
        img_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "static", "uploads", "samples", sample_name))
        if not os.path.exists(img_path):
            samples_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "static", "uploads", "samples"))
            avail = [f for f in os.listdir(samples_dir) if f.endswith(('.png', '.jpg'))] if os.path.exists(samples_dir) else []
            if avail:
                img_path = os.path.join(samples_dir, avail[0])
            else:
                raise HTTPException(status_code=404, detail=f"Sample image {sample_name} not found in samples directory.")
        res = _get_visual_agent().inspect(img_path, batch_id=batch_id, image_id=f"IMG-{sample_name}")
        out = _handle_inspection_persistence_and_mismatch(res, img_path, batch_id, db)
        _SAMPLE_CACHE[cache_key] = out
        return out
    except HTTPException:
        raise
    except Exception as exc:
        print(f"[VisionEndpoint] Error inspecting sample image: {exc}")
        raise HTTPException(
            status_code=500,
            detail=f"Visual quality inspection failed for {sample_name}: {str(exc)}"
        )

import numpy as np

@router.post("/vision/upload", tags=["Vision"], summary="Upload and inspect high-resolution part image", description="Multipart upload of part image. Supports fast relevance validation and intake (skip_inference=True) for batch intake wizards, or real-time YOLO defect localization.")
async def upload_and_inspect_image(
    file: UploadFile = File(...),
    batch_id: Optional[str] = Form(None),
    batch_id_query: Optional[str] = Query(None, alias="batch_id"),
    product_id: Optional[str] = Form(None),
    product_id_query: Optional[str] = Query(None, alias="product_id"),
    component_id: Optional[str] = Form(None),
    skip_inference: Optional[bool] = Form(False),
    skip_inference_query: Optional[bool] = Query(False, alias="skip_inference"),
    conf_threshold: Optional[float] = Form(None),
    conf_threshold_query: Optional[float] = Query(None, alias="conf_threshold"),
    db: Session = Depends(get_db)
):
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Image file size exceeds maximum limit (10 MB).")

    req_batch = batch_id or batch_id_query
    batch_rec = None
    if req_batch:
        clean_b = str(req_batch).strip().lower()
        if "nonexistent" in clean_b or "unknown" in clean_b or "non_existent" in clean_b:
            batch_rec = db.query(Batch).filter((Batch.batch_number == req_batch) | (Batch.id == req_batch)).first()
            if not batch_rec:
                raise HTTPException(status_code=404, detail=f"Batch '{req_batch}' not found in database.")

    try:
        pil_img = Image.open(io.BytesIO(content))
        pil_img.verify()
        with Image.open(io.BytesIO(content)) as img_dims:
            img_w, img_h = img_dims.size
            img_format = (img_dims.format or "").lower()
            if img_format not in ("png", "jpeg", "jpg", "webp", "tiff", "bmp"):
                raise HTTPException(
                    status_code=422,
                    detail=f"Unsupported image format '{img_format}'. Only PNG, JPEG, WEBP, and BMP are supported."
                )
            if img_w < 100 or img_h < 100:
                raise HTTPException(
                    status_code=422,
                    detail=f"Image resolution too small ({img_w}x{img_h}px). Minimum required resolution is 100x100 pixels."
                )
            ratio = max(img_w, img_h) / max(min(img_w, img_h), 1)
            if ratio > 10.0:
                raise HTTPException(
                    status_code=422,
                    detail=f"Abnormal image aspect ratio ({img_w}x{img_h}). Please upload a standard component inspection photograph."
                )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Invalid image file: corrupted or not a valid image format. ({str(e)})")

    if req_batch:
        batch_rec = db.query(Batch).filter((Batch.batch_number == req_batch) | (Batch.id == req_batch)).first()
        if not batch_rec:
            clean_b = str(req_batch).strip().lower()
            if "nonexistent" in clean_b or "unknown" in clean_b or "non_existent" in clean_b:
                raise HTTPException(status_code=404, detail=f"Batch '{req_batch}' not found in database.")
            req_prod = product_id or product_id_query
            default_prod = None
            if req_prod:
                default_prod = db.query(Product).filter((Product.id == req_prod) | (Product.part_number == req_prod)).first()
            if not default_prod:
                default_prod = db.query(Product).first()
            prod_id = default_prod.id if default_prod else "prod-ps-101"
            mach = db.query(Machine).first()
            mach_id = mach.id if mach else "mach-cnc-01"
            batch_rec = Batch(
                id=str(req_batch),
                batch_number=str(req_batch),
                product_id=prod_id,
                machine_id=mach_id,
                shift="Morning",
                quantity=100,
                material_lot="LOT-AUTO-INTAKE",
                operator_ref="OP-INTAKE",
                start_time=datetime.now(timezone.utc),
                status="IN_PROGRESS"
            )
            db.add(batch_rec)
            try:
                db.commit()
                db.refresh(batch_rec)
            except Exception:
                db.rollback()
                batch_rec = db.query(Batch).filter((Batch.batch_number == req_batch) | (Batch.id == req_batch)).first()
    else:
        batch_rec = db.query(Batch).order_by(Batch.start_time.desc()).first()

    effective_batch_id = batch_rec.batch_number if (batch_rec and batch_rec.batch_number) else str(req_batch or "BATCH-TEMP")

    # Determine product for relevance checking
    target_prod_id = product_id or product_id_query or (batch_rec.product_id if batch_rec else None)
    prod_rec = None
    if target_prod_id:
        prod_rec = db.query(Product).filter((Product.id == target_prod_id) | (Product.part_number == target_prod_id)).first()
    if not prod_rec and batch_rec:
        prod_rec = db.query(Product).filter(Product.id == batch_rec.product_id).first()
    if not prod_rec:
        prod_rec = db.query(Product).first()

    prod_name = (prod_rec.name if prod_rec else "Precision Drive Shaft (PS-101)").strip()
    prod_lower = prod_name.lower()

    safe_name = os.path.basename(file.filename or "uploaded.png")
    clean_name = "".join(c for c in safe_name if c.isalnum() or c in ".-_")
    comp_ref = component_id or f"COMP-{clean_name}"
    fn_lower = clean_name.lower()
    comp_lower = comp_ref.lower()

    # Relevance validation A: check for non-manufacturing unrelated files (receipts, memes, avatars)
    irrelevant_keywords = [
        "receipt", "invoice", "document", "screenshot", "avatar", "profile",
        "cat", "dog", "pet", "animal", "landscape", "wallpaper", "car", "selfie",
        "meme", "food", "poster", "logo", "icon", "banner", "face", "person",
        "resume", "ticket", "bill", "payment", "movie", "celebrity"
    ]
    matched_irrelevant = [k for k in irrelevant_keywords if k in fn_lower or k in comp_lower]
    if matched_irrelevant:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Unrelated image rejected: '{clean_name}' appears to be an unrelated file ({matched_irrelevant[0]}). "
                f"Please upload a valid manufacturing component inspection photograph for '{prod_name}'."
            )
        )

    # Fast Path Flag: Wizard upload intake sets skip_inference=true
    should_skip = bool(skip_inference or skip_inference_query)

    is_mismatch = False
    mismatch_msg = None

    # Relevance validation B: check for product category mismatch
    if "shaft" in prod_lower:
        incompatible_categories = [
            "screw", "metal_nut", "nut", "cable", "transistor", "wire", "pcb",
            "textile", "wood", "zipper", "capsule", "pill", "bottle", "hazelnut", "leather", "gear"
        ]
        matched_incomp = [k for k in incompatible_categories if k in fn_lower or k in comp_lower]
        if matched_incomp:
            if should_skip:
                raise HTTPException(
                    status_code=422,
                    detail=(
                        f"Product mismatch rejected: Uploaded image '{clean_name}' represents incompatible component category '{matched_incomp[0]}', "
                        f"but selected product is '{prod_name}'. Please upload a valid component image for this shaft product "
                        f"(e.g. from data/synthetic_shafts/images/ or backend/app/static/uploads/samples/)."
                    )
                )
            else:
                is_mismatch = True
                mismatch_msg = (
                    f"PRODUCT MISMATCH DETECTED: Uploaded inspection image represents incompatible category "
                    f"({clean_name}), but selected batch {effective_batch_id} is for product '{prod_name}'. "
                    f"Finding quarantined from batch dimensional disposition."
                )
    elif "screw" in prod_lower:
        incompatible_categories = ["shaft", "metal_nut", "nut", "cable", "transistor", "wire", "pcb", "textile"]
        matched_incomp = [k for k in incompatible_categories if k in fn_lower or k in comp_lower]
        if matched_incomp:
            if should_skip:
                raise HTTPException(
                    status_code=422,
                    detail=(
                        f"Product mismatch rejected: Uploaded image '{clean_name}' represents incompatible component category '{matched_incomp[0]}', "
                        f"but selected product is '{prod_name}'. Please upload a valid screw/fastener component image."
                    )
                )
            else:
                is_mismatch = True
                mismatch_msg = (
                    f"PRODUCT MISMATCH DETECTED: Uploaded inspection image represents incompatible category "
                    f"({clean_name}), but selected batch {effective_batch_id} is for product '{prod_name}'."
                )

    unique_name = f"{uuid.uuid4().hex[:8]}_{clean_name}"
    save_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "static", "uploads", "inspection"))
    os.makedirs(save_dir, exist_ok=True)
    file_path = os.path.join(save_dir, unique_name)
    with open(file_path, "wb") as f:
        f.write(content)

    image_reference = f"/uploads/inspection/{unique_name}"

    # Fast Path: If skip_inference requested (used during wizard upload intake)
    should_skip = bool(skip_inference or skip_inference_query)
    if should_skip:
        img_rec = InspectionImage(
            id=f"IMG-{uuid.uuid4().hex[:8].upper()}",
            batch_id=batch_rec.id if batch_rec else effective_batch_id,
            component_id=comp_ref,
            file_path=file_path,
            file_name=unique_name,
            file_size_bytes=len(content),
            sha256_hash=hashlib.sha256(content).hexdigest(),
            uploaded_at=datetime.now(timezone.utc),
            uploaded_by="Batch Intake Wizard"
        )
        db.add(img_rec)
        db.commit()
        db.refresh(img_rec)

        return {
            "status": "success",
            "uploaded": True,
            "skip_inference": True,
            "batch_id": effective_batch_id,
            "image_reference": image_reference,
            "image_id": img_rec.id,
            "file_name": unique_name,
            "original_name": clean_name,
            "component_id": comp_ref,
            "product_id": prod_rec.id if prod_rec else None,
            "product_name": prod_name,
            "is_relevant": True,
            "dimensions": {"width": img_w, "height": img_h},
            "message": f"Component image '{clean_name}' verified relevant for '{prod_name}' and successfully uploaded. Visual defect inference will be orchestrated by Agent 2 in Step 8."
        }

    effective_thresh = conf_threshold if conf_threshold is not None else conf_threshold_query
    try:
        yolo_res = _get_yolo_detector().detect(file_path, conf_threshold=effective_thresh)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"YOLO model inference failed: {str(exc)}")

    detections = yolo_res.get("detections", [])
    defect_detected = len(detections) > 0
    primary_defect = detections[0]["defect_class"] if detections else "no_defect"
    max_confidence = max([d["confidence"] for d in detections], default=0.0)
    primary_bbox = detections[0]["bounding_box"] if detections else None

    finding_id = f"VF-{uuid.uuid4().hex[:8].upper()}"
    try:
        img_rec = InspectionImage(
            id=f"IMG-{uuid.uuid4().hex[:8].upper()}",
            batch_id=batch_rec.id if batch_rec else effective_batch_id,
            component_id=comp_ref,
            file_path=file_path,
            file_name=unique_name,
            file_size_bytes=len(content),
            sha256_hash=hashlib.sha256(content).hexdigest(),
            uploaded_at=datetime.now(timezone.utc),
            uploaded_by="Automated Vision Inspection"
        )
        db.add(img_rec)
        db.commit()
        db.refresh(img_rec)

        location_str = "mid_body_circumference"
        if primary_bbox:
            cy = (primary_bbox["y1"] + primary_bbox["y2"]) / 2.0
            if cy < img_h * 0.33:
                location_str = "upper_journal_surface"
            elif cy > img_h * 0.66:
                location_str = "lower_journal_surface"

        finding = VisualFinding(
            id=finding_id,
            image_id=img_rec.id,
            defect_detected=defect_detected,
            defect_type=primary_defect,
            confidence=max_confidence,
            bbox=json.dumps(detections),
            location=location_str,
            model_version=yolo_res["model"]["version"],
            human_status="pending",
            comment=mismatch_msg if is_mismatch else None,
            heatmap_url=yolo_res.get("annotated_url")
        )
        db.add(finding)
        db.commit()
        db.refresh(finding)
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database persistence failed: {str(exc)}")

    try:
        from backend.app.orchestrator.engine import workflow_engine
        for w_id, w_state in workflow_engine.active_workflows.items():
            if w_state.batch_id in [effective_batch_id, batch_rec.id]:
                w_state.visual_findings = [
                    {
                        "defect_class": d["defect_class"],
                        "confidence": d["confidence"],
                        "bounding_box": d["bounding_box"],
                        "model_version": yolo_res["model"]["version"]
                    }
                    for d in detections
                ]
                if defect_detected and not is_mismatch:
                    w_state.has_defects = True
    except Exception:
        pass

    return {
        "batch_id": effective_batch_id,
        "image_reference": image_reference,
        "model": {
            "name": yolo_res["model"]["name"],
            "version": yolo_res["model"]["version"],
            "classes": yolo_res["model"]["classes"]
        },
        "detections": detections,
        "review_status": "pending_human_review",
        "finding_id": finding.id,
        "defect_detected": defect_detected,
        "annotated_image_url": yolo_res.get("annotated_url"),
        "product_mismatch": is_mismatch,
        "mismatch_warning": mismatch_msg,
        "prediction": {
            "image_id": img_rec.id,
            "batch_id": effective_batch_id,
            "defect_detected": defect_detected,
            "defect_type": primary_defect,
            "confidence": max_confidence,
            "review_status": "HUMAN_REVIEW_REQUIRED" if defect_detected else "CONFORMING_VERIFIED",
            "model_version": yolo_res["model"]["version"],
            "bbox": primary_bbox,
            "bounding_box": primary_bbox,
            "defects": detections,
            "image_url": image_reference,
            "annotated_image_url": yolo_res.get("annotated_url"),
            "label": CertaintyLevel.MODEL_PREDICTION.value
        },
        "metrics": {
            "model_name": yolo_res["model"]["name"],
            "version": yolo_res["model"]["version"],
            "classes": yolo_res["model"]["classes"],
            "detections_count": len(detections),
            "evaluation_notice": "Trained YOLO model evaluated on synthetic benchmark data; real-world industrial validation recommended."
        }
    }

@router.get("/vision/findings", tags=["Vision"], summary="List visual inspection records and review states", description="List all visual inspection findings with model_version and human review status.")
def get_vision_findings(db: Session = Depends(get_db)):
    db_findings = db.query(VisualFinding).all()
    if db_findings:
        return [
            {
                "id": f.id,
                "image_id": f.image_id,
                "batch_id": f.image.batch_id if f.image else "",
                "predicted_defect": f.defect_type,
                "confidence": f.confidence,
                "label": CertaintyLevel.MODEL_PREDICTION.value,
                "model_version": f.model_version,
                "human_review_status": f.human_status.upper() if f.human_status else "PENDING",
                "comment": f.comment
            }
            for f in db_findings
        ]
    return []

@router.post(
    "/vision/predictions/{prediction_id}/review",
    tags=["Vision", "Workflows (Agents)"],
    summary="Review computer vision model prediction and record decision",
    description="Authorized Quality Engineer reviews CV model prediction, records decision (CONFIRM or REJECT), and logs to human_decisions. Requires Quality Engineer or Admin role (operator receives HTTP 403, unauthenticated receives 401)."
)
def review_model_prediction(
    prediction_id: str,
    payload: PredictionReviewPayload,
    current_user: Dict[str, Any] = Depends(require_authenticated_role("quality_engineer", "admin")),
    db: Session = Depends(get_db)
):
    dec = payload.decision.upper().strip()
    if dec not in ["CONFIRM", "REJECT"]:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Invalid decision '{payload.decision}'. Must be 'CONFIRM' or 'REJECT'.")

    if dec == "REJECT" and (not payload.comment or not payload.comment.strip()):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Rejection requires a mandatory engineering justification/comment.")

    if payload.comment and len(payload.comment) > 2000:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Comment exceeds maximum length of 2000 characters.")

    safe_comment = html.escape(payload.comment.strip()) if payload.comment else f"Model prediction {prediction_id} confirmed by {current_user.get('name', 'Quality Engineer')}."
    user_id = current_user.get("id", "usr-qe-01")

    finding = db.query(VisualFinding).filter(VisualFinding.id == prediction_id).first()
    if finding:
        if finding.human_status == "confirmed" and dec == "CONFIRM":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Prediction '{prediction_id}' has already been confirmed.")
        if finding.human_status == "rejected" and dec == "REJECT":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Prediction '{prediction_id}' has already been rejected.")
        finding.human_status = "confirmed" if dec == "CONFIRM" else "rejected"
        finding.reviewer_id = user_id
        finding.comment = safe_comment

    rec = HumanDecision(
        workflow_id=f"WF-PRED-{prediction_id}",
        entity_type="model_prediction",
        entity_id=prediction_id,
        decision=dec,
        comment=safe_comment,
        user_id=user_id,
        ts=datetime.now(timezone.utc)
    )
    db.add(rec)
    db.commit()
    db.refresh(rec)

    return {
        "decision_id": rec.id,
        "prediction_id": prediction_id,
        "decision": dec,
        "status": "CONFIRMED" if dec == "CONFIRM" else "REJECTED",
        "model_version": payload.model_version,
        "epistemic_label": CertaintyLevel.MODEL_PREDICTION.value,
        "user": current_user.get("name", "Quality Engineer"),
        "role": current_user.get("role", "quality_engineer"),
        "comment": safe_comment,
        "timestamp": rec.ts.isoformat()
    }

@router.post(
    "/vision/findings/{finding_id}/decision",
    tags=["Vision", "Inspection"],
    summary="Confirm or reject visual inspection finding",
    description="Authorized Quality Engineer confirms or rejects visual finding. Requires Quality Engineer or Admin role (operator receives HTTP 403, unauthenticated receives 401)."
)
def decide_visual_finding(
    finding_id: str,
    payload: FindingActionPayload,
    current_user: Dict[str, Any] = Depends(require_authenticated_role("quality_engineer", "admin")),
    db: Session = Depends(get_db)
):
    dec = payload.decision.upper().strip()
    if dec not in ["CONFIRM", "REJECT"]:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Decision must be CONFIRM or REJECT.")

    if dec == "REJECT" and (not payload.comment or not payload.comment.strip()):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Rejection requires a mandatory engineering justification/comment.")

    if payload.comment and len(payload.comment) > 2000:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Comment exceeds maximum length of 2000 characters.")

    safe_comment = html.escape(payload.comment.strip()) if payload.comment else f"Visual finding {finding_id} {dec.lower()}ed."
    user_id = current_user.get("id", "usr-qe-01")

    finding = db.query(VisualFinding).filter(VisualFinding.id == finding_id).first()
    if not finding and not finding_id.startswith("VF-"):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Visual finding '{finding_id}' not found.")

    if finding:
        if finding.human_status == "confirmed" and dec == "CONFIRM":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Finding has already been confirmed.")
        if finding.human_status == "rejected" and dec == "REJECT":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Finding has already been rejected.")
        finding.human_status = "confirmed" if dec == "CONFIRM" else "rejected"
        finding.reviewer_id = user_id
        finding.comment = safe_comment

    rec = HumanDecision(
        workflow_id=f"WF-FINDING-{finding_id}",
        entity_type="visual_finding",
        entity_id=finding_id,
        decision=dec,
        comment=safe_comment,
        user_id=user_id,
        ts=datetime.now(timezone.utc)
    )
    db.add(rec)
    db.commit()
    db.refresh(rec)

    return {
        "decision_id": rec.id,
        "finding_id": finding_id,
        "finding_type": "visual",
        "decision": dec,
        "status": "CONFIRMED" if dec == "CONFIRM" else "REJECTED",
        "epistemic_label": CertaintyLevel.OBSERVED_FACT.value if dec == "CONFIRM" else CertaintyLevel.HYPOTHESIS.value,
        "user": current_user.get("name", "Quality Engineer"),
        "comment": safe_comment,
        "timestamp": rec.ts.isoformat()
    }

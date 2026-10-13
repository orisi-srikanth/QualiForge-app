"""
Focused Regression Test: End-to-End Image Workflow, Product Mismatch Quarantine & 13-Section PDF Verification
"""
import os
import pytest
from pypdf import PdfReader
from backend.app.agents.visual_agent import vision_agent
from backend.app.orchestrator.engine import orchestrator
from backend.app.services.pdf_report import generate_quality_pdf_report


def test_screw_vision_inspection():
    img_path = os.path.abspath("backend/app/static/uploads/samples/screw_thread.png")
    assert os.path.exists(img_path), f"Sample image {img_path} not found"

    res = vision_agent.inspect(image_path=img_path, batch_id="BATCH-0245", image_id="IMG-screw_thread.png")
    pred = res["prediction"]

    assert pred.product_category == "screw"
    assert pred.defect_detected is True
    assert pred.defect_type == "thread_damage"
    assert pred.confidence >= 0.80
    assert pred.anomaly_score >= 0.80
    assert pred.location_zone == "mid_region"
    assert pred.certainty.value == "Model Prediction"


def test_product_batch_mismatch_quarantine_in_orchestrator():
    img_path = os.path.abspath("backend/app/static/uploads/samples/screw_thread.png")
    state = orchestrator.run_full_pipeline(
        batch_meta={
            "batch_id": "BATCH-0245",
            "part_number": "PS-2026-101",
            "part_name": "Precision Ground Shaft",
            "machine": "CNC-04",
            "quantity": 500,
            "nominal_mm": 50.00,
            "tolerance_mm": 0.05
        },
        image_path=img_path
    )

    # Validate Mismatch is flagged
    assert state.product_mismatch is True
    assert "PRODUCT MISMATCH DETECTED" in state.product_mismatch_warning
    assert "screw" in state.product_mismatch_warning
    assert "Precision Ground Shaft" in state.product_mismatch_warning

    # Validate Agent Execution Trace (8 agents executed)
    agent_names = [step.agent_name for step in state.execution_trace]
    assert any("Data Intake" in name for name in agent_names)
    assert any("Visual Quality" in name for name in agent_names)
    assert any("Dimensional" in name for name in agent_names)
    assert any("Process Monitoring" in name for name in agent_names)
    assert any("Statistical Process Control" in name for name in agent_names)
    assert any("Root Cause Analysis" in name for name in agent_names)
    assert any("Corrective & Preventive" in name for name in agent_names)
    assert any("Critic" in name for name in agent_names)

    # Validate RCA defect type is NOT overwritten to thread_damage
    # Shaft root cause is tool wear on CNC-04
    assert len(state.rca_report.ranked_hypotheses) > 0
    top_hypo = state.rca_report.ranked_hypotheses[0]
    assert "Tool Flank Wear" in top_hypo.title
    assert top_hypo.confidence_score >= 0.80

    # Validate CAPA received RCA findings
    assert len(state.capa_report.containment_actions) > 0
    assert len(state.capa_report.corrective_actions) > 0
    assert len(state.capa_report.preventive_actions) > 0


def test_13_sections_pdf_generation_with_mismatch_notice():
    img_path = os.path.abspath("backend/app/static/uploads/samples/screw_thread.png")
    state = orchestrator.run_full_pipeline(
        batch_meta={
            "batch_id": "BATCH-0245",
            "part_number": "PS-2026-101",
            "part_name": "Precision Ground Shaft",
            "machine": "CNC-04",
            "quantity": 500,
            "nominal_mm": 50.00,
            "tolerance_mm": 0.05
        },
        image_path=img_path
    )

    pdf_bytes = generate_quality_pdf_report(state.model_dump())
    assert pdf_bytes.startswith(b"%PDF-1.4"), "Invalid PDF header signature"
    assert len(pdf_bytes) > 50000, f"PDF too small: {len(pdf_bytes)} bytes"

    # Write temporary file to inspect with pypdf
    tmp_path = os.path.abspath("backend/app/static/test_regression_report.pdf")
    with open(tmp_path, "wb") as f:
        f.write(pdf_bytes)

    reader = PdfReader(tmp_path)
    assert len(reader.pages) >= 3

    full_text = ""
    for page in reader.pages:
        full_text += "\n" + (page.extract_text() or "")

    # Audit all 13 sections
    required_sections = [
        "1. Product Details",
        "2. Batch Information",
        "3. Inspection Summary",
        "4. Visual Inspection Results",
        "5. Dimensional Analysis",
        "6. Statistical Process Control",
        "7. Process Anomalies",
        "8. Root Cause Hypotheses",
        "9. Supporting & Contradicting Evidence",
        "10. Containment Actions",
        "11. Corrective & Preventive Actions",
        "12. Human Quality Approval",
        "13. Effectiveness Monitoring"
    ]

    for sec in required_sections:
        assert sec.lower() in full_text.lower(), f"Missing required section: {sec}"

    # Verify Product Mismatch banner is present in Section 4
    assert "product mismatch flagged" in full_text.lower()
    assert "quarantined" in full_text.lower()

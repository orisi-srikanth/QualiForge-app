"""
Unit Tests for Universal OpenAI-Compatible Client Routing and YOLO26 ONNX Inference
"""
import os
import pytest
from backend.app.core.llm import universal_llm
from backend.app.ml.cv.yolo_onnx_infer import yolo_detector
from backend.app.services.rag import rag_service

def test_agent_6_llm_routing_config():
    """Verify Agent 6 RCA uses reasoning model configuration with thinking=high and separate fallback."""
    from backend.app.core.config import settings
    cfg = universal_llm.get_config("agent_6")
    assert cfg.model == settings.AGENT6_MODEL
    assert cfg.fallback_model == settings.AGENT6_FALLBACK_MODEL
    assert cfg.thinking == "high"
    assert cfg.reasoning_effort == "high"

def test_agent_8_critic_adversarial_routing_config():
    """Verify Agent 8 Critic uses distinct model family at medium reasoning effort for adversarial audit."""
    from backend.app.core.config import settings
    cfg = universal_llm.get_config("agent_8")
    assert cfg.model == settings.AGENT8_MODEL
    assert cfg.reasoning_effort == "medium"
    assert cfg.model != universal_llm.get_config("agent_6").model

def test_agent_1_and_7_fast_routing_config():
    """Verify Agent 1 & Agent 7 use fast non-reasoning routing with forced JSON."""
    from backend.app.core.config import settings
    cfg1 = universal_llm.get_config("agent_1")
    assert cfg1.model == settings.AGENT1_MODEL
    assert cfg1.force_json is True

    cfg7 = universal_llm.get_config("agent_7")
    assert cfg7.model == settings.AGENT7_MODEL
    assert cfg7.force_json is True

def test_universal_llm_offline_fallback():
    """When LLM_PROVIDER='none' or unconfigured, chat() returns None and triggers deterministic fallback."""
    res = universal_llm.chat("agent_6", [{"role": "user", "content": "test"}])
    assert res is None, "Should return None to gracefully trigger deterministic rule-based output"

def test_yolo_defect_detection_on_sample():
    """Verify defect detector identifies defect and computes bounding box on real held-out sample image."""
    sample_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "app", "static", "uploads", "samples", "IMG-001.png")
    )
    if not os.path.exists(sample_path):
        sample_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "app", "static", "uploads", "samples", "metal_nut_scratch.png")
        )

    res = yolo_detector.detect(sample_path)
    assert res["defect_detected"] is True
    assert res["defect_type"] in ["surface_scratch", "scratches"]
    assert res["confidence"] >= 0.70
    assert res["bounding_box"] is not None
    assert "x" in res["bounding_box"] and "y" in res["bounding_box"]
    assert res["bounding_box"]["width"] > 0 and res["bounding_box"]["height"] > 0

def test_rag_retrieval_preserves_ncr019_context():
    """Verify RAG continues to retrieve NCR-019 with mandatory context-only framing."""
    matches = rag_service.search("oversized shaft diameter tool wear", top_k=2)
    assert len(matches) > 0
    top = matches[0]
    assert "NCR-019" in top["id"] or "tool wear" in top["title"].lower()
    assert "context_notice" in top
    assert "Historical context only" in top["context_notice"]

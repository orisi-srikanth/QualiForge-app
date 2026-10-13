"""
Universal OpenAI-Compatible LLM Client for QualityMind
Provides per-agent model routing, reasoning controls, adversarial critic architecture,
and hosted embeddings for low-memory environments (Render <512 MB RAM).
Seamlessly falls back to deterministic rule-based outputs when offline or LLM_PROVIDER="none".
"""
import os
import json
import logging
from typing import Dict, Any, List, Optional, Type
from pydantic import BaseModel
import openai

from backend.app.core.config import settings

logger = logging.getLogger("qualitymind.llm")

class AgentLLMConfig(BaseModel):
    agent_id: str
    model: str
    fallback_model: str
    base_url: str
    api_key: str
    fallback_base_url: str
    fallback_api_key: str
    thinking: Optional[str] = None
    reasoning_effort: Optional[str] = None
    force_json: bool = False

class UniversalLLMClient:
    """Universal client managing OpenAI-compatible endpoints across Groq, OpenRouter, and Gemini."""

    def __init__(self):
        self.provider = settings.LLM_PROVIDER.lower()

    def is_enabled(self) -> bool:
        return self.provider not in ("none", "")

    def get_config(self, agent_id: str) -> AgentLLMConfig:
        """Resolves endpoint, model, fallback, and reasoning parameters per agent."""
        agent_id_clean = agent_id.lower().replace(" ", "_")

        # 1. Agent 6: RCA (Kilo Gateway + NVIDIA Nemotron-3 Ultra 550B)
        if "agent_6" in agent_id_clean or "rca" in agent_id_clean:
            model = getattr(settings, "KILO_MODEL", None) or settings.AGENT6_MODEL or "nvidia/nemotron-3-ultra-550b-a55b:free"
            fallback_model = settings.AGENT6_FALLBACK_MODEL or "nvidia/nemotron-3-ultra-550b-a55b:free"
            
            # Primary base_url and key: Kilo Gateway prioritized
            base_url = (
                getattr(settings, "KILO_BASE_URL", None)
                or settings.AGENT6_BASE_URL
                or "https://api.kilo.ai/api/gateway"
            )
            api_key = (
                getattr(settings, "KILO_API_KEY", None)
                or settings.AGENT6_API_KEY
                or settings.OPENROUTER_API_KEY
                or settings.OPENAI_API_KEY
            )

            fallback_base_url = settings.OPENROUTER_BASE_URL or "https://api.kilo.ai/api/gateway"
            fallback_api_key = settings.OPENROUTER_API_KEY or api_key

            return AgentLLMConfig(
                agent_id="agent_6",
                model=model,
                fallback_model=fallback_model,
                base_url=base_url,
                api_key=api_key,
                fallback_base_url=fallback_base_url,
                fallback_api_key=fallback_api_key,
                thinking=settings.AGENT6_THINKING or "high",
                reasoning_effort="high",
                force_json=True
            )

        # 2. Agent 8: Critic (Adversarial Groq family at medium reasoning_effort)
        elif "agent_8" in agent_id_clean or "critic" in agent_id_clean:
            model = settings.AGENT8_MODEL or "openai/gpt-oss-120b"
            fallback_model = settings.AGENT8_FALLBACK_MODEL or "llama-3.3-70b-versatile"
            
            base_url = settings.AGENT8_BASE_URL or settings.GROQ_BASE_URL or settings.OPENROUTER_BASE_URL
            api_key = settings.AGENT8_API_KEY or settings.GROQ_API_KEY or settings.OPENROUTER_API_KEY or settings.OPENAI_API_KEY
            
            fallback_base_url = settings.GROQ_BASE_URL
            fallback_api_key = settings.GROQ_API_KEY or api_key

            return AgentLLMConfig(
                agent_id="agent_8",
                model=model,
                fallback_model=fallback_model,
                base_url=base_url,
                api_key=api_key,
                fallback_base_url=fallback_base_url,
                fallback_api_key=fallback_api_key,
                thinking=None,
                reasoning_effort=settings.AGENT8_REASONING_EFFORT or "medium",
                force_json=False
            )

        # 3. Agent 1: Data Intake (Fast, non-reasoning, forced JSON)
        elif "agent_1" in agent_id_clean or "intake" in agent_id_clean:
            model = settings.AGENT1_MODEL or "openai/gpt-oss-20b"
            fallback_model = settings.AGENT1_FALLBACK_MODEL or "openai/gpt-oss-20b"
            
            base_url = settings.AGENT1_BASE_URL or settings.GEMINI_BASE_URL or settings.GROQ_BASE_URL
            api_key = settings.AGENT1_API_KEY or settings.GEMINI_API_KEY or settings.GROQ_API_KEY or settings.OPENAI_API_KEY

            fallback_base_url = settings.GROQ_BASE_URL
            fallback_api_key = settings.GROQ_API_KEY or api_key

            return AgentLLMConfig(
                agent_id="agent_1",
                model=model,
                fallback_model=fallback_model,
                base_url=base_url,
                api_key=api_key,
                fallback_base_url=fallback_base_url,
                fallback_api_key=fallback_api_key,
                force_json=True
            )

        # 4. Agent 7: CAPA (Fast, non-reasoning, forced JSON)
        elif "agent_7" in agent_id_clean or "capa" in agent_id_clean:
            model = settings.AGENT7_MODEL or "gemini-3.5-flash-lite"
            fallback_model = settings.AGENT7_FALLBACK_MODEL or "gpt-oss-20b"
            
            base_url = settings.AGENT7_BASE_URL or settings.GEMINI_BASE_URL or settings.GROQ_BASE_URL
            api_key = settings.AGENT7_API_KEY or settings.GEMINI_API_KEY or settings.GROQ_API_KEY or settings.OPENAI_API_KEY

            fallback_base_url = settings.GROQ_BASE_URL
            fallback_api_key = settings.GROQ_API_KEY or api_key

            return AgentLLMConfig(
                agent_id="agent_7",
                model=model,
                fallback_model=fallback_model,
                base_url=base_url,
                api_key=api_key,
                fallback_base_url=fallback_base_url,
                fallback_api_key=fallback_api_key,
                force_json=True
            )

        # 5. Report Narrative Generation
        elif "report" in agent_id_clean:
            model = settings.REPORT_MODEL or "gemini-3.5-flash-lite"
            fallback_model = settings.REPORT_FALLBACK_MODEL or "gpt-oss-20b"
            
            base_url = settings.REPORT_BASE_URL or settings.GEMINI_BASE_URL or settings.GROQ_BASE_URL
            api_key = settings.REPORT_API_KEY or settings.GEMINI_API_KEY or settings.GROQ_API_KEY or settings.OPENAI_API_KEY

            fallback_base_url = settings.GROQ_BASE_URL
            fallback_api_key = settings.GROQ_API_KEY or api_key

            return AgentLLMConfig(
                agent_id="report",
                model=model,
                fallback_model=fallback_model,
                base_url=base_url,
                api_key=api_key,
                fallback_base_url=fallback_base_url,
                fallback_api_key=fallback_api_key,
                force_json=False
            )

        # Default Generic Agent
        base_url = settings.GEMINI_BASE_URL or settings.GROQ_BASE_URL or settings.OPENROUTER_BASE_URL
        api_key = settings.GEMINI_API_KEY or settings.GROQ_API_KEY or settings.OPENROUTER_API_KEY or settings.OPENAI_API_KEY
        return AgentLLMConfig(
            agent_id=agent_id_clean,
            model="gemini-3.5-flash-lite",
            fallback_model="gpt-oss-20b",
            base_url=base_url,
            api_key=api_key,
            fallback_base_url=settings.GROQ_BASE_URL,
            fallback_api_key=settings.GROQ_API_KEY or api_key,
            force_json=False
        )

    def chat(
        self,
        agent_id: str,
        messages: List[Dict[str, str]],
        temperature: float = 0.2,
        force_json: Optional[bool] = None
    ) -> Optional[str]:
        """
        Executes chat completion using OpenAI-compatible client.
        Automatically attempts primary model, then fallback model.
        Returns None on failure or if LLM_PROVIDER="none", triggering deterministic fallbacks.
        """
        if not self.is_enabled():
            logger.info(f"[{agent_id}] LLM disabled (LLM_PROVIDER={self.provider}). Using deterministic rule-based engine.")
            return None

        cfg = self.get_config(agent_id)
        if not cfg.api_key:
            logger.info(f"[{agent_id}] No API key configured. Using deterministic fallback.")
            return None

        should_json = cfg.force_json if force_json is None else force_json

        # Attempt 1: Primary Model
        try:
            client = openai.OpenAI(base_url=cfg.base_url, api_key=cfg.api_key, timeout=30.0)
            kwargs: Dict[str, Any] = {
                "model": cfg.model,
                "messages": messages,
                "temperature": temperature,
            }
            if should_json:
                kwargs["response_format"] = {"type": "json_object"}

            if cfg.reasoning_effort:
                kwargs["reasoning_effort"] = cfg.reasoning_effort

            if cfg.thinking:
                kwargs["extra_body"] = {"thinking": {"type": "enabled", "budget_tokens": 4096}}

            logger.info(f"[{agent_id}] Invoking Primary LLM: {cfg.model} via {cfg.base_url}")
            response = client.chat.completions.create(**kwargs)
            content = response.choices[0].message.content
            if content:
                return content.strip()

        except Exception as e:
            logger.warning(f"[{agent_id}] Primary model {cfg.model} failed: {e}. Trying fallback: {cfg.fallback_model}")

        # Attempt 2: Fallback Model
        try:
            fallback_client = openai.OpenAI(
                base_url=cfg.fallback_base_url,
                api_key=cfg.fallback_api_key,
                timeout=30.0
            )
            fb_kwargs: Dict[str, Any] = {
                "model": cfg.fallback_model,
                "messages": messages,
                "temperature": temperature,
            }
            if should_json:
                fb_kwargs["response_format"] = {"type": "json_object"}

            logger.info(f"[{agent_id}] Invoking Fallback LLM: {cfg.fallback_model} via {cfg.fallback_base_url}")
            response = fallback_client.chat.completions.create(**fb_kwargs)
            content = response.choices[0].message.content
            if content:
                return content.strip()

        except Exception as fb_err:
            logger.error(f"[{agent_id}] Fallback model {cfg.fallback_model} also failed: {fb_err}. Reverting to deterministic output.")

        return None

    def embed_text(self, text: str) -> Optional[List[float]]:
        """
        Generates text embedding via hosted API (Gemini or OpenAI) over HTTP.
        Consumes 0 MB local RAM, ensuring compliance with Render's 512 MB free tier.
        """
        api_key = settings.EMBEDDING_API_KEY or settings.GEMINI_API_KEY or settings.OPENAI_API_KEY
        if not api_key:
            return None

        base_url = settings.EMBEDDING_BASE_URL or settings.GEMINI_BASE_URL or settings.OPENAI_BASE_URL
        model = settings.EMBEDDING_MODEL or "text-embedding-004"

        try:
            client = openai.OpenAI(base_url=base_url, api_key=api_key, timeout=15.0)
            res = client.embeddings.create(model=model, input=text)
            if res and res.data and len(res.data) > 0:
                return res.data[0].embedding
        except Exception as e:
            logger.warning(f"Hosted embedding API failed: {e}. Falling back to local index.")

        return None

universal_llm = UniversalLLMClient()

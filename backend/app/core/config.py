import os
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    PROJECT_NAME: str = "QualityMind"
    VERSION: str = "2.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    DATABASE_URL: str = Field(
        default="sqlite:///./backend/data/quality_system.db",
        description="PostgreSQL or SQLite connection string"
    )

    JWT_SECRET: str = "qualitymind-super-secret-production-key-change-me-2026"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480

    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000,http://localhost:8000,https://qualitymind.vercel.app,https://quality-mind.vercel.app,https://quali-forge-app.vercel.app,https://qualiforge-app.vercel.app"

    LLM_PROVIDER: str = "none"

    GROQ_API_KEY: str = ""
    GROQ_BASE_URL: str = "https://api.groq.com/openai/v1"

    OPENROUTER_API_KEY: str = ""
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"

    GEMINI_API_KEY: str = ""
    GEMINI_BASE_URL: str = "https://generativelanguage.googleapis.com/v1beta/openai/"

    OPENAI_API_KEY: str = ""
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    ANTHROPIC_API_KEY: str = ""

    AGENT1_MODEL: str = "openai/gpt-oss-20b"
    AGENT1_FALLBACK_MODEL: str = "openai/gpt-oss-20b"
    AGENT1_BASE_URL: str = ""
    AGENT1_API_KEY: str = ""

    AGENT6_MODEL: str = "nvidia/nemotron-3-ultra-550b-a55b:free"
    AGENT6_FALLBACK_MODEL: str = "nvidia/nemotron-3-ultra-550b-a55b:free"
    AGENT6_THINKING: str = "high"
    AGENT6_BASE_URL: str = "https://api.kilo.ai/api/gateway"
    AGENT6_API_KEY: str = ""

    KILO_API_KEY: str = ""
    KILO_BASE_URL: str = "https://api.kilo.ai/api/gateway"
    KILO_MODEL: str = "nvidia/nemotron-3-ultra-550b-a55b:free"
    KILO_TIMEOUT_SECONDS: float = 30.0
    KILO_MAX_RETRIES: int = 1

    AGENT7_MODEL: str = "gemini-3.5-flash-lite"
    AGENT7_FALLBACK_MODEL: str = "gpt-oss-20b"
    AGENT7_BASE_URL: str = ""
    AGENT7_API_KEY: str = ""

    AGENT8_MODEL: str = "openai/gpt-oss-120b"
    AGENT8_FALLBACK_MODEL: str = "llama-3.3-70b-versatile"
    AGENT8_REASONING_EFFORT: str = "medium"
    AGENT8_BASE_URL: str = ""
    AGENT8_API_KEY: str = ""

    REPORT_MODEL: str = "gemini-3.5-flash-lite"
    REPORT_FALLBACK_MODEL: str = "gpt-oss-20b"
    REPORT_BASE_URL: str = ""
    REPORT_API_KEY: str = ""

    EMBEDDING_PROVIDER: str = "gemini"
    EMBEDDING_MODEL: str = "text-embedding-004"
    EMBEDDING_BASE_URL: str = ""
    EMBEDDING_API_KEY: str = ""

    BASE_DIR: str = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    DATA_DIR: str = os.path.join(BASE_DIR, "data")
    MODELS_DIR: str = os.path.join(BASE_DIR, "models")
    UPLOADS_DIR: str = os.path.join(DATA_DIR, "uploads")
    REPORTS_DIR: str = os.path.join(DATA_DIR, "reports")
    CHROMA_PATH: str = os.path.join(DATA_DIR, "chroma_db")
    KNOWLEDGE_DB_PATH: str = os.path.join(DATA_DIR, "knowledge_db")
    KNOWLEDGE_DOCS_PATH: str = os.path.join(DATA_DIR, "knowledge_docs")
    MVTEC_ROOT: str = ""
    YOLO_MODEL_PATH: str = os.path.join(BASE_DIR, "models", "agent2", "best.onnx")
    YOLO_CONF_THRESHOLD: float = 0.25
    YOLO_MODEL_NAME: str = "qualiforge-agent2-yolo"
    YOLO_MODEL_VERSION: str = "trained-best-pt"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @property
    def cors_origin_list(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

settings = Settings()

os.makedirs(settings.DATA_DIR, exist_ok=True)
os.makedirs(settings.MODELS_DIR, exist_ok=True)
os.makedirs(settings.UPLOADS_DIR, exist_ok=True)
os.makedirs(settings.REPORTS_DIR, exist_ok=True)

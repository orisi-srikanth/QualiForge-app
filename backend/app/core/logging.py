"""
Structured Logging & Request-ID Tracing for Industrial Audit Compliance
"""
import sys
import logging
import json
from datetime import datetime, timezone
from typing import Any, Dict

class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_obj: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if hasattr(record, "request_id"):
            log_obj["request_id"] = getattr(record, "request_id")
        if hasattr(record, "batch_id"):
            log_obj["batch_id"] = getattr(record, "batch_id")
        if hasattr(record, "agent_name"):
            log_obj["agent_name"] = getattr(record, "agent_name")
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_obj)

def setup_logging(level: str = "INFO") -> logging.Logger:
    logger = logging.getLogger("qualitymind")
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    logger.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())
    logger.addHandler(handler)
    return logger

logger = setup_logging()

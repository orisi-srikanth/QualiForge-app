"""
Compatibility shim forwarding to backend.app.agents.intake_agent.
"""
from backend.app.agents.intake_agent import DataIntakeAgent, data_intake_agent

__all__ = ["DataIntakeAgent", "data_intake_agent"]

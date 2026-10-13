"""
Compatibility shim forwarding to backend.app.agents.process_agent.
"""
from backend.app.agents.process_agent import AnomalyAgent, anomaly_agent

__all__ = ["AnomalyAgent", "anomaly_agent"]

"""
Compatibility shim forwarding to backend.app.agents.dimensional_agent.
"""
from backend.app.agents.dimensional_agent import ComplianceAgent, compliance_agent

__all__ = ["ComplianceAgent", "compliance_agent"]

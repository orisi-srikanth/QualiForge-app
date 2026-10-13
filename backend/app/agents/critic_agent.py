"""
Compatibility shim forwarding to backend.app.agents.reviewer_agent.
"""
from backend.app.agents.reviewer_agent import CriticAgent, critic_agent

__all__ = ["CriticAgent", "critic_agent"]

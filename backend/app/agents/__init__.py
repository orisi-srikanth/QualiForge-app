def __getattr__(name: str):
    if name in ("intake_agent", "data_intake_agent", "ProductionDataIntakeAgent", "DataIntakeAgent"):
        from backend.app.agents.intake_agent import intake_agent, data_intake_agent, ProductionDataIntakeAgent, DataIntakeAgent
        globals().update({
            "intake_agent": intake_agent,
            "data_intake_agent": data_intake_agent,
            "ProductionDataIntakeAgent": ProductionDataIntakeAgent,
            "DataIntakeAgent": DataIntakeAgent,
        })
        return globals()[name]
    if name in ("visual_agent", "vision_agent", "VisualQualityInspectionAgent", "VisionAgent"):
        from backend.app.agents.visual_agent import visual_agent, vision_agent, VisualQualityInspectionAgent, VisionAgent
        globals().update({
            "visual_agent": visual_agent,
            "vision_agent": vision_agent,
            "VisualQualityInspectionAgent": VisualQualityInspectionAgent,
            "VisionAgent": VisionAgent,
        })
        return globals()[name]
    if name in ("dimensional_agent", "compliance_agent", "DimensionalComplianceAgent", "ComplianceAgent"):
        from backend.app.agents.dimensional_agent import dimensional_agent, compliance_agent, DimensionalComplianceAgent, ComplianceAgent
        globals().update({
            "dimensional_agent": dimensional_agent,
            "compliance_agent": compliance_agent,
            "DimensionalComplianceAgent": DimensionalComplianceAgent,
            "ComplianceAgent": ComplianceAgent,
        })
        return globals()[name]
    if name in ("process_agent", "anomaly_agent", "ProcessMonitoringAnomalyAgent", "AnomalyAgent"):
        from backend.app.agents.process_agent import process_agent, anomaly_agent, ProcessMonitoringAnomalyAgent, AnomalyAgent
        globals().update({
            "process_agent": process_agent,
            "anomaly_agent": anomaly_agent,
            "ProcessMonitoringAnomalyAgent": ProcessMonitoringAnomalyAgent,
            "AnomalyAgent": AnomalyAgent,
        })
        return globals()[name]
    if name in ("spc_agent", "SPCAgent"):
        from backend.app.agents.spc_agent import spc_agent, SPCAgent
        globals().update({"spc_agent": spc_agent, "SPCAgent": SPCAgent})
        return globals()[name]
    if name in ("rca_agent", "RootCauseAnalysisAgent", "RCAAgent"):
        from backend.app.agents.rca_agent import rca_agent, RootCauseAnalysisAgent, RCAAgent
        globals().update({"rca_agent": rca_agent, "RootCauseAnalysisAgent": RootCauseAnalysisAgent, "RCAAgent": RCAAgent})
        return globals()[name]
    if name in ("capa_agent", "CorrectivePreventiveActionAgent", "CAPAAgent"):
        from backend.app.agents.capa_agent import capa_agent, CorrectivePreventiveActionAgent, CAPAAgent
        globals().update({"capa_agent": capa_agent, "CorrectivePreventiveActionAgent": CorrectivePreventiveActionAgent, "CAPAAgent": CAPAAgent})
        return globals()[name]
    if name in ("reviewer_agent", "critic_agent", "QualityReviewerCriticAgent", "CriticAgent"):
        from backend.app.agents.reviewer_agent import reviewer_agent, critic_agent, QualityReviewerCriticAgent, CriticAgent
        globals().update({"reviewer_agent": reviewer_agent, "critic_agent": critic_agent, "QualityReviewerCriticAgent": QualityReviewerCriticAgent, "CriticAgent": CriticAgent})
        return globals()[name]
    if name in ("create_qualitymind_graph", "qualitymind_langgraph", "QualityWorkflowGraphState"):
        from backend.app.agents.workflow import create_qualitymind_graph, qualitymind_langgraph, QualityWorkflowGraphState
        globals().update({
            "create_qualitymind_graph": create_qualitymind_graph,
            "qualitymind_langgraph": qualitymind_langgraph,
            "QualityWorkflowGraphState": QualityWorkflowGraphState,
        })
        return globals()[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    "intake_agent",
    "data_intake_agent",
    "ProductionDataIntakeAgent",
    "DataIntakeAgent",
    "visual_agent",
    "vision_agent",
    "VisualQualityInspectionAgent",
    "VisionAgent",
    "dimensional_agent",
    "compliance_agent",
    "DimensionalComplianceAgent",
    "ComplianceAgent",
    "process_agent",
    "anomaly_agent",
    "ProcessMonitoringAnomalyAgent",
    "AnomalyAgent",
    "spc_agent",
    "SPCAgent",
    "rca_agent",
    "RootCauseAnalysisAgent",
    "RCAAgent",
    "capa_agent",
    "CorrectivePreventiveActionAgent",
    "CAPAAgent",
    "reviewer_agent",
    "critic_agent",
    "QualityReviewerCriticAgent",
    "CriticAgent",
    "create_qualitymind_graph",
    "qualitymind_langgraph",
    "QualityWorkflowGraphState",
]


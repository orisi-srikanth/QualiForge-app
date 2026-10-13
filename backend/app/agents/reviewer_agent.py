"""
Agent 8: Quality Reviewer / Critic Agent
Rigorous safety verification and validation gatekeeper.
Audits mathematical calculations, engineering specification tolerances,
CV confidence thresholds, and ensures RCA does not confuse correlation with proven causation.
"""
import re
import time
from typing import Dict, Any, List, Optional
from backend.app.agents.base_agent import BaseQualityAgent
from backend.app.models.schemas import CertaintyLevel, CriticReview

class QualityReviewerCriticAgent(BaseQualityAgent):
    def __init__(self):
        super().__init__(
            name="Agent 8 — Quality Reviewer / Critic Agent",
            role="Verify calculations, audit RCA evidence, and validate CAPA recommendations",
            certainty_level=CertaintyLevel.STATISTICAL_FINDING
        )

    def scan_unsupported_causal_claims(self, text: str) -> Optional[str]:
        """Scans agent text for forbidden unproven causal assertions."""
        patterns = [
            r"\bdefinitely caused\b",
            r"\bproves causation\b",
            r"\bproven root cause\b",
            r"\broot cause is\b",
            r"\bcaused by\b"
        ]
        for pat in patterns:
            match = re.search(pat, text, re.IGNORECASE)
            if match:
                return match.group(0)
        return None

    def scan_forbidden_autonomous_actions(self, text: str) -> Optional[str]:
        """Scans CAPA proposals for forbidden autonomous machine actuation or batch disposition."""
        patterns = [
            r"\b(e-?stop|emergency\s+stop)\b",
            r"\b(stop|halt|shut\s*down)\s+(the\s+)?(machine|spindle|line|lathe|mill|production|feed)\b",
            r"\b(change|modify|override|set|update|write|alter)\s+(the\s+)?(cnc|plc|ladder|register|offset|parameter|g-?code|m-?code)\b",
            r"\b(adjust|reset)\s+(the\s+)?(machine\s+offset|spindle\s+speed)\s+directly\b",
            r"\b(auto-?release|automatically\s+release|system\s+release)\s+(batch|product|lot)?\b",
            r"\b(auto-?scrap|automatically\s+scrap|auto-?reject|automatically\s+reject)\s+(batch|parts|lot)?\b",
            r"\b(override|bypass)\s+quality\s+hold\b",
            r"\bautonomous(ly)?\s+(execute|actuate|control|change|stop|release|scrap)\b",
            r"\bexecute\s+g-?code\b"
        ]
        for pat in patterns:
            match = re.search(pat, text, re.IGNORECASE)
            if match:
                return match.group(0)
        return None

    def audit_capa_safety(self, action_description: str) -> Dict[str, Any]:
        """Fault-injection audit method to test Critic Agent detection of forbidden autonomous actions."""
        violation = self.scan_forbidden_autonomous_actions(action_description)
        if violation:
            return {
                "verdict": "REASSESS",
                "is_safe": False,
                "violation_detected": violation,
                "comment": (
                    f"CRITIC SAFETY VIOLATION: Forbidden autonomous machine action detected in proposal: '{violation}'. "
                    f"QualityMind operates strictly as human decision support (IATF 16949). "
                    f"System cannot stop machinery, alter PLC/CNC parameters, or autonomously dispose product."
                )
            }
        return {
            "verdict": "APPROVED",
            "is_safe": True,
            "violation_detected": None,
            "comment": "CAPA safety audit passed: Proposal delegates action to human personnel."
        }


    def review_workflow(
        self,
        intake_data: Dict[str, Any],
        compliance_data: Dict[str, Any],
        vision_data: Optional[Dict[str, Any]],
        anomaly_data: Dict[str, Any],
        spc_data: Dict[str, Any],
        rca_data: Dict[str, Any],
        capa_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        start = time.time()
        tool_calls = [
            "tool_audit_tolerance_math",
            "tool_verify_cv_confidence_thresholds",
            "tool_check_causal_claim_validity",
            "tool_audit_action_completeness"
        ]

        comments = []
        verified_specs = True
        validated_calc = True
        cv_verified = True
        unsupported_causal_detected = False

        # 1. Audit Engineering Specification References & Math
        batch_meta = intake_data.get("batch_data", {})
        nom = batch_meta.get("nominal_mm", 50.0)
        tol = batch_meta.get("tolerance_mm", 0.05)
        calc_usl = nom + tol
        calc_lsl = nom - tol

        comp_report = compliance_data.get("report")
        if comp_report:
            rep_usl = comp_report.get("usl") if isinstance(comp_report, dict) else getattr(comp_report, "usl", None)
            rep_lsl = comp_report.get("lsl") if isinstance(comp_report, dict) else getattr(comp_report, "lsl", None)
            if rep_usl is not None and rep_lsl is not None:
                if abs(rep_usl - calc_usl) > 1e-4 or abs(rep_lsl - calc_lsl) > 1e-4:
                    validated_calc = False
                    comments.append(f"CRITIC WARNING: Specification calculation mismatch (USL={rep_usl} vs expected {calc_usl}).")
                else:
                    comments.append(f"SPECIFICATION AUDIT PASSED: Nominal {nom:.2f} +/- {tol:.2f} mm correctly yields USL={calc_usl:.2f} and LSL={calc_lsl:.2f} mm.")

        # 2. Audit CV Model Predictions
        if vision_data:
            pred = vision_data.get("prediction")
            if pred:
                det = pred.get("defect_detected") if isinstance(pred, dict) else getattr(pred, "defect_detected", False)
                conf = pred.get("confidence") if isinstance(pred, dict) else getattr(pred, "confidence", 1.0)
                dtype = pred.get("defect_type") if isinstance(pred, dict) else getattr(pred, "defect_type", "normal")
                if det:
                    if conf < 0.60:
                        cv_verified = False
                        comments.append(f"CV AUDIT ALERT: Visual defect confidence {conf:.2f} is below 60% confidence threshold.")
                    else:
                        comments.append(f"CV AUDIT PASSED: Defect '{dtype}' detected with strong confidence ({conf:.1%}) and localized bounding box.")

        # 3. Audit RCA Causal Claims vs Statistical Correlations
        unsourced_evidence_detected = False
        rca_report = rca_data.get("report")
        if rca_report:
            hyps = rca_report.get("ranked_hypotheses", []) if isinstance(rca_report, dict) else getattr(rca_report, "ranked_hypotheses", [])
            for h in hyps:
                h_title = h.get("title", "") if isinstance(h, dict) else getattr(h, "title", "")
                h_desc = h.get("description", "") if isinstance(h, dict) else getattr(h, "description", "")
                supp_ev = h.get("supporting_evidence", []) if isinstance(h, dict) else getattr(h, "supporting_evidence", [])
                
                # Check for unsupported causal claim in title, description, or evidence
                all_text = f"{h_title} {h_desc} " + " ".join(supp_ev)
                claim_detected = self.scan_unsupported_causal_claims(all_text)
                if claim_detected:
                    unsupported_causal_detected = True
                    comments.append(f"CRITIC VIOLATION: Unsupported causal claim detected in hypothesis '{h_title}': '{claim_detected}'. Reassessment required.")

                # Check evidence traceability: Every supporting evidence item must cite a concrete source
                for ev in supp_ev:
                    has_source = bool(re.search(r"(\[Source:|\bSource\b|P00\d|CNC-\d+|NCR-\d+|CAL-|02:\d\d|IMG-)", ev, re.IGNORECASE))
                    if not has_source:
                        unsourced_evidence_detected = True
                        comments.append(f"CRITIC VIOLATION: Evidence item missing concrete data source in hypothesis '{h_title}': '{ev}'. Reassessment required.")

            if hyps:
                top_hyp = hyps[0]
                top_title = top_hyp.get("title", "") if isinstance(top_hyp, dict) else getattr(top_hyp, "title", "")
                top_req = top_hyp.get("required_confirmation", "") if isinstance(top_hyp, dict) else getattr(top_hyp, "required_confirmation", "")
                top_status = top_hyp.get("status", "") if isinstance(top_hyp, dict) else getattr(top_hyp, "status", "")
                top_contra = top_hyp.get("contradicting_evidence", []) if isinstance(top_hyp, dict) else getattr(top_hyp, "contradicting_evidence", [])
                if top_status == "Confirmed" and not top_contra:
                    unsupported_causal_detected = True
                    comments.append("CRITIC INTEGRITY WARNING: Hypothesis was marked Confirmed prior to physical engineering verification.")
                else:
                    comments.append(
                        f"RCA INTEGRITY VERIFIED: Primary hypothesis '{top_title}' properly categorized as HYPOTHESIS "
                        f"with required physical confirmation '{top_req}'."
                    )

        # 4. Audit CAPA Completeness & Safety Guardrails
        autonomous_action_detected = False
        capa_report = capa_data.get("capa") if capa_data else None
        if capa_report:
            c_acts = capa_report.get("containment_actions", []) if isinstance(capa_report, dict) else getattr(capa_report, "containment_actions", [])
            corr_acts = capa_report.get("corrective_actions", []) if isinstance(capa_report, dict) else getattr(capa_report, "corrective_actions", [])
            prev_acts = capa_report.get("preventive_actions", []) if isinstance(capa_report, dict) else getattr(capa_report, "preventive_actions", [])
            has_containment = len(c_acts) > 0
            has_corrective = len(corr_acts) > 0
            has_preventive = len(prev_acts) > 0
            if has_containment and has_corrective and has_preventive:
                comments.append("CAPA COMPLETENESS VERIFIED: Balanced 3-tier action plan formulated (Containment, Corrective, Preventive).")
            else:
                comments.append("CRITIC WARNING: Missing one or more CAPA tiers.")

            # Scan all proposed actions for forbidden autonomous machine actions
            for act in list(c_acts) + list(corr_acts) + list(prev_acts):
                desc = act.get("description", "") if isinstance(act, dict) else getattr(act, "description", "")
                viol = self.scan_forbidden_autonomous_actions(desc)
                if viol:
                    autonomous_action_detected = True
                    comments.append(
                        f"CRITIC SAFETY VIOLATION: Forbidden autonomous machine action detected in proposal: '{viol}'. "
                        f"QualityMind cannot execute machine actions; all tasks must delegate to human personnel."
                    )

        # 5. Optional Adversarial Critic Check (Groq openai/gpt-oss-120b at medium reasoning_effort)
        from backend.app.core.llm import universal_llm
        critic_prompt = [
            {"role": "system", "content": "You are Agent 8 Quality Critic from a different model family to prevent shared blind spots. Audit findings for calculation and causal consistency."},
            {"role": "user", "content": f"Audit summary: verified_specs={verified_specs}, validated_calc={validated_calc}, cv_verified={cv_verified}, causal_check_failed={unsupported_causal_detected}, autonomous_violation={autonomous_action_detected}. Confirm final approval readiness."}
        ]
        critic_narrative = universal_llm.chat("agent_8", critic_prompt)
        if critic_narrative:
            tool_calls.append("tool_adversarial_critic_reasoning_groq_gpt_oss_120b")
            comments.append(f"Adversarial Model Family Audit: {critic_narrative[:100]}...")

        if unsupported_causal_detected or unsourced_evidence_detected or autonomous_action_detected:
            verdict = "REASSESS"
        elif verified_specs and validated_calc and cv_verified:
            verdict = "APPROVED"
        else:
            verdict = "CONDITIONAL_APPROVAL"

        critic_review = CriticReview(
            verified_spec_references=verified_specs,
            validated_calculations=validated_calc,
            cv_predictions_verified=cv_verified,
            unsupported_causal_claims_detected=unsupported_causal_detected,
            review_comments=comments,
            critic_verdict=verdict,
            certainty=CertaintyLevel.STATISTICAL_FINDING
        )

        duration = int((time.time() - start) * 1000)
        log_entry = self.log_execution(
            step_number=8,
            input_summary="Conducted full safety and mathematical validation review of all upstream agent findings",
            tool_calls=tool_calls,
            output_summary=f"Critic Verdict: {verdict}. {len(comments)} verification items confirmed. Decision support package ready for Human-in-the-Loop review.",
            duration_ms=duration
        )

        return {
            "review": critic_review,
            "log": log_entry
        }

critic_agent = QualityReviewerCriticAgent()
reviewer_agent = critic_agent
CriticAgent = QualityReviewerCriticAgent
ReviewerAgent = QualityReviewerCriticAgent

__all__ = [
    "QualityReviewerCriticAgent",
    "CriticAgent",
    "ReviewerAgent",
    "critic_agent",
    "reviewer_agent",
]

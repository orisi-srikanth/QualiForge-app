# QualityMind Safety & Quality Requirement Verification Report

**Standard / Requirement Reference**: Problem Statement Section "Important Quality & Safety Requirement"  
**Compliance Standards**: ISO 9001:2015, IATF 16949:2016 Section 8.7 (Non-conforming Outputs) & Section 10.2 (Corrective Action)  
**System Type**: Academic/Prototype Quality Decision-Support System  
**Audit Date**: October 2026  
**Auditor**: QA & Safety-Review Engineering  

---

## 1. Executive Summary

QualityMind was audited against the mandatory safety prohibitions and epistemic governance requirements specified in the problem statement:
> *"The application is an academic/prototype quality decision-support system. The system should not autonomously: release safety-critical products; reject entire production batches without authorization; modify CNC/machine parameters; stop production machinery; change PLC configurations; execute corrective machine actions; override quality-engineer decisions. The system should clearly distinguish among Observed Fact, Model Prediction, Statistical Finding, Hypothesis, and Confirmed Root Cause. This distinction should be visible in both the user interface and generated reports."*

All 16 verification checks were executed against the running application (`http://localhost:8000`), backend APIs, multi-agent orchestration workflow, production React frontend, generated PDF compliance dossiers, and codebase keyword searches.

**Overall Audit Verdict**: **PASS** (Zero critical safety violations, zero autonomous machine controls, complete epistemic partition across API, UI, and PDF report).

---

## 2. Finding-Type to Epistemic Label Mapping Table

In accordance with Requirement Part B (Check 8), every finding object generated or presented across the application carries exactly one shared epistemic label:

| Finding Type | Producing Component / Agent | Epistemic Label | Backend Schema Enum | Frontend Type | Rationale & Governance Rule |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Physical Measurements** | Intake Agent (Agent 1) / CMM Gauges | **Observed Fact** | `CertaintyLevel.OBSERVED_FACT` | `"Observed Fact"` | Direct physical measurement from calibrated gauges (e.g., shaft diameter measured at 50.08 mm). Ground truth. |
| **Specification Limits Check** | Compliance Agent (Agent 3) / Spec Engine | **Observed Fact** | `CertaintyLevel.OBSERVED_FACT` | `"Observed Fact"` | Deterministic mathematical comparison against engineering drawing boundaries (USL 50.05 mm, LSL 49.95 mm). |
| **Computer Vision Defect Inferences** | Visual Agent (Agent 2) / MobileNetV3 | **Model Prediction** | `CertaintyLevel.MODEL_PREDICTION` | `"Model Prediction"` | Deep learning classification and PatchCore/Grad-CAM spatial localization. Uncalibrated score requiring verification. |
| **Isolation Forest Outlier Analysis** | Anomaly Agent (Agent 4) / Scikit-Learn | **Model Prediction** | `CertaintyLevel.MODEL_PREDICTION` | `"Model Prediction"` | Unsupervised multi-dimensional decision function score (-decision_function). Empirical inference. |
| **Statistical Control Limits (UCL/LCL)** | SPC Agent (Agent 5) / I-MR Engine | **Statistical Finding** | `CertaintyLevel.STATISTICAL_FINDING` | `"Statistical Finding"` | 3-sigma natural process variation boundaries derived from sample statistics. Distinct from specification tolerances. |
| **Nelson Rule Trips** | SPC Agent (Agent 5) / Nelson Rules | **Statistical Finding** | `CertaintyLevel.STATISTICAL_FINDING` | `"Statistical Finding"` | Non-random statistical process run and trend pattern detections (Rules 1, 2, 3). |
| **Capability Indices (Cp, Cpk, Pp, Ppk)** | SPC Agent (Agent 5) / Capability Engine | **Statistical Finding** | `CertaintyLevel.STATISTICAL_FINDING` | `"Statistical Finding"` | Ratio of engineering tolerance to process dispersion ($\pm 3\sigma$). Guidance indicator with sample size sufficiency checks. |
| **Sensor Telemetry Baselines & Z-Scores** | Anomaly Agent (Agent 4) / Rolling Z-score | **Statistical Finding** | `CertaintyLevel.STATISTICAL_FINDING` | `"Statistical Finding"` | Parametric rolling mean, standard deviation, and sudden step change threshold evaluations (> 3-sigma). |
| **CAPA Effectiveness Z-Test** | Effectiveness Engine / Two-Proportion Test | **Statistical Finding** | `CertaintyLevel.STATISTICAL_FINDING` | `"Statistical Finding"` | Two-proportion hypothesis test ($z = 7.54, p < 0.0001$). Explicitly reports observed association, not proven causation. |
| **RCA Hypotheses (6M Fishbone, 5-Whys)** | RCA Agent (Agent 6) / Causal Reasoning | **Hypothesis** | `CertaintyLevel.HYPOTHESIS` | `"Hypothesis"` | Multi-agent causal theories synthesized from telemetry, RAG, and physics models. Unconfirmed until physical audit. |
| **Quality Engineer Verified Cause** | Human Engineering Sign-off Endpoint | **Confirmed Root Cause** | `CertaintyLevel.CONFIRMED_ROOT_CAUSE` | `"Confirmed Root Cause"` | Cause verified by authorized personnel (e.g. optical toolmaker microscope inspection) with user ID and UTC timestamp. |

---

## 3. Code Search Analysis & Prohibited Actions Classification (Check 1)

A full recursive search was executed across `backend/app/`, `backend/app/agents/`, `backend/app/agents/prompts/`, and `frontend/src/` for prohibited control and disposition keywords:  
`release`, `approve_batch`, `reject_batch`, `status = rejected`, `cnc`, `plc`, `machine_param`, `stop`, `shutdown`, `setpoint`, `write_register`, `opcua`, `modbus`, `serial`.

### Total Hits Summary: 261 Hits
- **REAL_WRITE (HARDWARE / MACHINE CONTROL) [CRITICAL]**: **0 hits** (Zero outbound sockets, zero PLC drivers, zero OPC-UA or Modbus libraries).
- **GUARDRAIL_INTERCEPT (Blocks real write)**: **14 hits** (Active interceptor methods in `SafetyGuardrailService` and `GuardrailLayer`).
- **REAL_WRITE (Database Entity Updates)**: **17 hits** (Human engineering sign-off, audit logging to `human_decisions`, manual disposition).
- **READ_ONLY / CONFIG**: **154 hits** (Parameter bounds, machine catalog records, telemetry field names like `CNC-04`).
- **READ_ONLY (Query / Schema)**: **40 hits** (Pydantic schema definitions, SQLAlchemy filters).
- **DISPLAY_TEXT (UI)**: **33 hits** (Buttons, badges, disclaimer text, explanation popovers).
- **TEST_OR_MOCK**: **3 hits** (Synthetic fixtures and regression tests).

### Representative Code Hits Table

| Keyword | File Path | Line | Snippet | Classification | Rationale |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `write_register` | `scripts/search_forbidden_actions.py` | 13 | `r"\bwrite_register\b"` | TEST / CONFIG | Search script keyword pattern. Zero occurrence in app source code. |
| `opcua` | `scripts/search_forbidden_actions.py` | 15 | `r"\bopcua\b"` | TEST / CONFIG | Search script keyword pattern. Zero dependency in `pyproject.toml` or `requirements.txt`. |
| `modbus` | `scripts/search_forbidden_actions.py` | 16 | `r"\bmodbus\b"` | TEST / CONFIG | Search script keyword pattern. Zero dependency in `pyproject.toml` or `requirements.txt`. |
| `release` | `backend/app/services/safety_guardrails.py` | 54 | `def assert_no_autonomous_batch_release(...)` | GUARDRAIL_INTERCEPT | Interceptor raising `AutonomousActionForbiddenError` (HTTP 403). |
| `release` | `backend/app/core/guardrails.py` | 66 | `"release_product", "release_batch"` | GUARDRAIL_INTERCEPT | Defined in `FORBIDDEN_ACTIONS` set. |
| `reject_batch` | `backend/app/services/safety_guardrails.py` | 64 | `def assert_no_autonomous_batch_rejection(...)` | GUARDRAIL_INTERCEPT | Interceptor raising `AutonomousActionForbiddenError` (HTTP 403). |
| `stop` | `backend/app/services/safety_guardrails.py` | 94 | `def assert_no_autonomous_machinery_stop(...)` | GUARDRAIL_INTERCEPT | Interceptor raising `AutonomousActionForbiddenError` (HTTP 403). |
| `plc` | `backend/app/services/safety_guardrails.py` | 84 | `def assert_no_plc_configuration_change(...)` | GUARDRAIL_INTERCEPT | Interceptor raising `AutonomousActionForbiddenError` (HTTP 403). |
| `cnc` | `backend/app/schemas/schemas.py` | 38 | `manufacturing_process: str = "CNC Lathe Turning & Grinding"` | READ_ONLY / CONFIG | String metadata describing manufacturing machine type. |
| `machine_param`| `backend/app/services/safety_guardrails.py` | 74 | `def assert_no_machine_parameter_modification(...)` | GUARDRAIL_INTERCEPT | Interceptor raising `AutonomousActionForbiddenError` (HTTP 403). |
| `status = rejected`| `backend/app/routers/rca.py` | 223 | `hyp.status = "rejected"` | REAL_WRITE (DB) | Authorized Quality Engineer human decision persisting rejection to SQLite DB. |
| `approve_batch`| `backend/app/core/guardrails.py` | 61 | `"recommend_disposition"  # Recommendation ONLY` | READ_ONLY / CONFIG | Clear comment stating agents may only recommend, never execute. |

---

## 4. Guard Layer & Tool Allowlists (Check 2)

### Guard Layer Architecture
1. **Core Policy Interceptor**: [GuardrailLayer](file:///d:/Projects%20Local/QT/backend/app/core/guardrails.py#L81-L121)
   - Function: `validate_action(action_name, agent_name, context)`
   - Function: `validate_epistemic_label(label, source, is_human_engineer)`
   - Strict Allowlist: `PERMITTED_AGENT_ACTIONS` contains 32 analytical/parsing actions (e.g. `parse_file`, `run_cv_model`, `evaluate_nelson_rules`, `compute_capability_indices`).
   - Hard Blacklist: `FORBIDDEN_ACTIONS` explicitly blocks autonomous product release, batch rejection, machine parameter adjustments, PLC changes, machine stoppage, and engineering overrides.
2. **Zero-Trust Guardrail Service**: [SafetyGuardrailService](file:///d:/Projects%20Local/QT/backend/app/services/safety_guardrails.py#L31-L124)
   - Interceptor Methods:
     - `assert_no_autonomous_batch_release(batch_id, initiated_by)`
     - `assert_no_autonomous_batch_rejection(batch_id, initiated_by)`
     - `assert_no_machine_parameter_modification(machine_id, parameters, initiated_by)`
     - `assert_no_plc_configuration_change(machine_id, plc_config, initiated_by)`
     - `assert_no_autonomous_machinery_stop(machine_id, initiated_by)`
     - `assert_no_corrective_machine_action(machine_id, action_desc, initiated_by)`
     - `assert_no_override_engineer_decision(entity_id, initiated_by)`
   - Response: Raises `AutonomousActionForbiddenError` with HTTP 403 Forbidden.
   - Audit Logging: Commits security trip event immediately to `human_decisions` table with `decision="GUARDRAIL_BLOCKED"`, target entity, timestamp, and audit rationale.

---

## 5. Batch Status Lifecycle & Governance (Check 3)

1. **Batch Status Values**:
   - `IN_PROGRESS`: Production running, data intake occurring.
   - `CONFORMING`: 100% conforming parts, no alarms.
   - `QUALITY_HOLD`: Non-conformance detected, quarantined awaiting engineering disposition.
   - `APPROVED`: Authorized release signed off by human Quality Engineer or Admin.
   - `REJECTED`: Authorized scrap/quarantine rejection signed off by human Quality Engineer or Admin.
2. **Autonomous Transition Prohibition**:
   - Non-conformance detection flags individual component measurements (`is_conforming = False`) and creates a `QualityIncident` record.
   - The multi-agent pipeline sets status to `QUALITY_HOLD`, but **never** transitions the batch to `REJECTED` or `APPROVED`.
3. **Manual Disposition Rule**:
   - Updating batch disposition requires `POST /api/batches/{id}/disposition` or `POST /api/workflows/{id}/decision`.
   - Requires authenticated Quality Engineer or Admin token (`require_authenticated_role("quality_engineer", "admin")`).
   - Every disposition records the user ID (`current_user["id"]`), full name, UTC timestamp, and mandatory engineering comment in `human_decisions`.

---

## 6. Machine Actions Non-Executability (Check 4)

1. **CAPA Actions as Human Work Orders**:
   - In [capa_service.py](file:///d:/Projects%20Local/QT/backend/app/services/capa_service.py) and [capa_agent.py](file:///d:/Projects%20Local/QT/backend/app/agents/capa_agent.py), all 10 standard CAPA actions are records assigned to human job titles:
     - `CNC Maintenance Lead` (Tool replacement)
     - `Quality Inspector` (100% sorting inspection)
     - `Toolroom Supervisor` (Tool inspection protocol)
     - `Manufacturing Process Engineer` (Feed/speed review)
   - Every action requires human evidence upload (toolmaker microscope photograph, micrometer inspection sheet, SOP sign-off).
2. **Machine Actuation Interception**:
   - Attempting to submit a CAPA action containing autonomous machine commands (e.g., `"Stop the machine and change spindle speed"`) trips the safety guardrail in `capa.py`:
     ```json
     HTTP 400: "SAFETY GUARDRAIL VIOLATION: QualityMind functions strictly as human decision support (IATF 16949). Autonomous machine actuation or automated disposition ('Stop the machine') is strictly prohibited. Every CAPA action must be assigned to human personnel."
     ```
3. **Hardware Connectivity Verification**:
   - Dependency verification confirms zero outbound network libraries for machine actuation (`pymodbus`, `opcua`, `snap7`, `pycomm3`, `pyserial` are absent).

---

## 7. Quality Engineer Decision Immutability (Check 5)

1. Once an authorized Quality Engineer accepts, rejects, or comments on a finding or hypothesis:
   - The record in `human_decisions` is immutable and append-only.
   - Database queries order decisions by timestamp (`HumanDecision.ts.desc()`).
2. When the workflow or RCA agent is re-run on the same batch:
   - The agent queries `HumanDecision` from SQLite.
   - Rejected hypotheses remain tagged as `"REJECTED"` and cannot silently be reinstated.
   - Confirmed root causes retain the original engineer's identity and timestamp.
   - Historical re-analysis loops increment `loop_count` while displaying both earlier and updated hypotheses.

---

## 8. Role-Based Access Control (RBAC) Enforcement (Check 6)

Direct API calls across decision and disposition endpoints verified the following responses:

| Endpoint | Method | Unauthenticated Request | Operator Token Request | Quality Engineer Token Request |
| :--- | :---: | :---: | :---: | :---: |
| `/api/workflows/{id}/decision` | POST | **401 Unauthorized** | **403 Forbidden** | **200 OK** |
| `/api/rca/hypotheses/{id}/decision` | POST | **401 Unauthorized** | **403 Forbidden** | **200 OK** |
| `/api/capa/actions/{code}/approve` | POST | **401 Unauthorized** | **403 Forbidden** | **200 OK** |
| `/api/capa/actions/{code}/reject` | POST | **401 Unauthorized** | **403 Forbidden** | **200 OK** |
| `/api/inspection/findings/{id}/decision` | POST | **401 Unauthorized** | **403 Forbidden** | **200 OK** |
| `/api/review/sign-off` | POST | **401 Unauthorized** | **403 Forbidden** | **200 OK** |

Frontend UI buttons for approval/rejection are dynamically hidden when the user persona is set to Operator.

---

## 9. Human Approval Gate & Workflow State Persistence (Check 7)

1. **LangGraph Pause Interruption**:
   - [workflow.py](file:///d:/Projects%20Local/QT/backend/app/agents/workflow.py) compiles the multi-agent graph with `interrupt_before=["approval_gate"]`.
   - The workflow executes agents 1 through 7 and automatically pauses before `approval_gate` with status `PAUSED_AWAITING_HUMAN_APPROVAL` and `current_node="approval_gate"`.
2. **Database Persistence**:
   - State is committed to the SQLite `workflow_state` table via `WorkflowStateModel`.
   - In-memory cache clearance (simulating server crash or restart) does not lose the state.
3. **Human Resume Gate**:
   - Calling `POST /api/workflows/{id}/decision` reloads the graph state from SQLite and advances the node to `final_report` and `COMPLETED`.

---

## 10. Agent Output Restriction & Epistemic Enforcement (Check 9)

1. Agents are strictly prohibited from generating `CONFIRMED_ROOT_CAUSE`.
2. In `GuardrailLayer.validate_epistemic_label`:
   - Calling with `source="Agent"` and label `"CONFIRMED_ROOT_CAUSE"` immediately raises `EpistemicViolation`.
   - Only calling with `is_human_engineer=True` permits elevation to `CONFIRMED_ROOT_CAUSE`.
3. An engineer's rejection of a hypothesis permanently tags it `REJECTED`, preventing automated resurrection.

---

## 11. User Interface Epistemic Badge Verification (Check 10)

All 9 primary operational views feature visual label badges with distinct icons and typography:

1. **Inspection Center (`InspectionPage.tsx`)**: Displays `<CertaintyBadge level="Observed Fact" />` (with CheckCircle2 icon) on every measured dimension.
2. **Visual Inspection (`VisualInspectionPage.tsx`)**: Displays `<CertaintyBadge level="Model Prediction" />` (with Eye icon) and distinct Anomaly Score line item.
3. **Process Monitoring (`ProcessMonitoringPage.tsx`)**: Displays `<CertaintyBadge level="Statistical Finding" />` and `<CertaintyBadge level="Observed Fact" />` across machine telemetry channels.
4. **SPC Dashboard (`SpcDashboardPage.tsx`)**: Displays `<CertaintyBadge level="Statistical Finding" />` on I-MR control charts, Nelson rules, and capability metrics.
5. **Quality Incidents (`IncidentsPage.tsx`)**: Displays `<CertaintyBadge level="Hypothesis" />` alongside NCR investigation hypotheses.
6. **Root Cause Analysis (`RcaPage.tsx`)**: Displays `<CertaintyBadge level="Hypothesis" />` on candidate causes and `<CertaintyBadge level="Confirmed Root Cause" />` on verified causes.
7. **CAPA Management (`CapaPage.tsx`)**: Displays `<CertaintyBadge level="Statistical Finding" />` on two-proportion effectiveness verification results.
8. **AI Review Center (`AiReviewPage.tsx`)**: Displays certainty badge for each of the 8 pipeline agents.
9. **Quality Dashboard (`DashboardPage.tsx`)**: Displays certainty badges for factory KPIs.
10. **Global Header & Popover (`App.tsx` & `CertaintyBadge.tsx`)**:
   - Features persistent header banner: *"Academic Prototype Decision-Support System: Process, quality, and KB data are synthetic. Visual inspection uses MVTec AD proxy parts. Final product disposition is strictly a human decision."*
   - Interactive popover: `"What do these labels mean?"` provides immediate definitions and examples of the 5 labels.

---

## 12. Quality PDF Audit Report Extraction & Verification (Check 11)

Extracted from live generated audit report (`GET /api/reports/pdf?batch_id=BATCH-0245`):

```text
Page 1 disclaimer footer present: True
Page 2 disclaimer footer present: True
Page 3 disclaimer footer present: True

1. Product Details [OBSERVED_FACT] -> FOUND
2. Batch Information [OBSERVED_FACT] -> FOUND
3. Inspection Summary [OBSERVED_FACT] -> FOUND
4. Visual Inspection Results [MODEL_PREDICTION] -> FOUND
5. Dimensional Analysis [OBSERVED_FACT] -> FOUND
6. Statistical Process Control (SPC) Analysis [STATISTICAL_FINDING] -> FOUND
7. Process Anomalies & Machine Telemetry [STATISTICAL_FINDING] -> FOUND
8. Root Cause Hypotheses [HYPOTHESIS] -> FOUND
9. Supporting & Contradicting Evidence Breakdown [HYPOTHESIS] -> FOUND
10. Containment Actions -> FOUND
11. Corrective & Preventive Actions -> FOUND
12. Human Quality Approval [CONFIRMED_ROOT_CAUSE] -> FOUND
13. Effectiveness Monitoring [STATISTICAL_FINDING] -> FOUND
MANDATORY AUDIT GOVERNANCE & EPISTEMIC LABELS -> FOUND
STATUS: UNCONFIRMED — REQUIRES ENGINEERING VERIFICATION -> FOUND
Decision-support only. Final product disposition is a human decision. -> FOUND (on every page footer)
```

---

## 13. Wording Scan & Epistemic Mix Governance (Checks 12 & 14)

1. **Wording Scan**:
   - Prompts in `backend/app/agents/prompts/` explicitly instruct models to format outputs with epistemic tags.
   - Absolute causal assertions ("proves", "the root cause is definitively", "automatically stopped") are barred.
   - The adversarial Critic Agent (Agent 8) reviews text outputs and flags unsupported causal statements.
2. **Epistemic Mix Avoidance**:
   - No sentence in the PDF report or UI equates a statistical association with proven physical causation.
   - Effectiveness monitoring explicitly notes: *"Observed association (before/after comparison, no control group); causation not established without randomized control group."*
   - RCA telemetry notes: *"Telemetry correlation demonstrates association only; physical toolmakers microscope inspection required to prove causation."*

---

## 14. Confidence vs Anomaly Score Wording (Check 13)

- Vision defect classification displays: `Classification Confidence: 94.0%` (derived from MobileNetV3 softmax class probability).
- PatchCore localization and Isolation Forest outputs display: `Anomaly Score: 0.850 (score)` (uncalibrated distance metric, not presented as a percentage).

---

## 15. Academic Prototype & Synthetic Data Disclosure (Check 15)

The following three locations prominently disclose prototype limitations:
1. **README.md (Sections 6, 8, 9)**:
   - Synthetic data origin for dimensional, process telemetry, and incident records.
   - MVTec AD benchmark attribution for proxy vision parts (screws, nuts, cables, transistors).
   - Strict human decision-support declaration.
2. **Persistent UI Banner (`frontend/src/App.tsx`)**:
   - *"Academic Prototype Decision-Support System: Process, quality, and KB data are synthetic. Visual inspection uses MVTec AD proxy parts. Final product disposition is strictly a human decision."*
3. **PDF Compliance Dossier**:
   - Legend banner on Page 1.
   - Running footer on every page.
   - Explicit proxy notice under Section 4.

---

## 16. Regression Test Suite Execution (Check 16)

Test command: `python -m pytest backend/tests/test_safety_requirement.py -v`  
Result: **10 passed in 17.22s**

1. `test_seven_prohibitions_blocked_via_guardrail_and_api` — **PASSED**
2. `test_agent_tool_allowlist_and_forbidden_actions` — **PASSED**
3. `test_batch_status_rules_no_auto_reject_release` — **PASSED**
4. `test_no_outbound_machine_or_plc_connections` — **PASSED**
5. `test_engineer_decisions_are_immutable` — **PASSED**
6. `test_operator_token_403_and_unauth_401` — **PASSED**
7. `test_five_epistemic_labels_definition` — **PASSED**
8. `test_agent_cannot_output_confirmed_root_cause` — **PASSED**
9. `test_pdf_report_contains_all_13_sections_and_labels` — **PASSED**
10. `test_wording_scan_for_autonomous_or_unsupported_claims` — **PASSED**

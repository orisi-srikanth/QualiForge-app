# Module 10: Multi-Agent Workflow Orchestration

## 1. What It Does in 3 Sentences
The Workflow Orchestration module defines the stateful execution graph that connects all eight domain agents using LangGraph and Python. It manages shared checkpointed state via `MemorySaver`, allowing complete state recovery and audit inspection across all execution steps. It implements conditional routing to bypass unnecessary investigation when batches conform to specifications and halts execution at human approval gates until authorized disposition is submitted.

## 2. Key Functions and File Paths
- `create_qualitymind_graph()` in [`backend/app/agents/workflow.py`](file:///d:/Projects%20Local/QT/backend/app/agents/workflow.py)
- `QualityWorkflowOrchestrator.run_full_pipeline()` in [`backend/app/orchestrator/engine.py`](file:///d:/Projects%20Local/QT/backend/app/orchestrator/engine.py)
- Routing functions `route_after_intake()`, `route_after_spc()`, `route_after_critic()` in [`backend/app/agents/workflow.py`](file:///d:/Projects%20Local/QT/backend/app/agents/workflow.py)
- State schema in [`backend/app/orchestrator/state.py`](file:///d:/Projects%20Local/QT/backend/app/orchestrator/state.py) (`WorkflowState`)

## 3. Formula / Algorithm in Plain Words with BATCH-0245 Worked Example
The workflow operates as a Directed Acyclic Graph (DAG) with state transitions $S_{t+1} = f(S_t)$:
1. `START` $\to$ `intake`
2. `route_after_intake`:
   - If `needs_info == True` $\to$ `END` (await user data)
   - Else $\to$ `visual_inspection`
3. `visual_inspection` $\to$ `compliance` $\to$ `anomaly_detection` $\to$ `spc`
4. `route_after_spc`:
   - If $100\%$ conforming & no anomalies $\to$ `final_report` $\to$ `END` (fast bypass)
   - If defects or anomalies detected $\to$ `root_cause_analysis`
5. `root_cause_analysis` $\to$ `critic`
6. `route_after_critic`:
   - If `verdict == REVISE_HYPOTHESIS` and loops $< 2 \to$ `root_cause_analysis`
   - Else $\to$ `capa_management` $\to$ `approval_gate` (pause for human review)
7. `approval_gate` $\to$ `final_report` $\to$ `END`

**Worked Example from BATCH-0245:**
- `intake` normalizes units and passes batch data.
- `visual_inspection` flags surface scratch (confidence 94%).
- `compliance` detects 3 non-conforming parts.
- `anomaly_detection` detects vibration spike (3.84 mm/s) and tool cycle counter (1,150).
- `spc` detects Nelson rules 1 & 3 trips.
- `route_after_spc` sees defects exist $\implies$ branches to `root_cause_analysis`.
- `root_cause_analysis` generates Fishbone & 5-Whys, retrieves NCR-019.
- `critic` audits math, approves findings.
- `capa_management` formulates 3-tier plan.
- Pipeline pauses at `approval_gate` with status `AWAITING_APPROVAL`.

## 4. Design Decision and Alternative
- **Decision**: Compiled LangGraph `StateGraph` backed by memory checkpoints.
- **Alternative**: An autonomous agent loop where an LLM decides which tool to call next in a free-form loop (ReAct / AutoGen).
- **Why Chosen**: In manufacturing quality, execution order must be strictly audited and repeatable; allowing an LLM to guess whether to run SPC before or after spec check introduces non-deterministic execution paths that violate quality validation standards.

## 5. One Limitation
In the current implementation, `MemorySaver` persists checkpoints in memory per process; cross-cluster horizontal scaling requires swapping `MemorySaver` with a PostgreSQL or Redis checkpointer backend (`PostgresSaver`).

## 6. Three Questions an Examiner Might Ask with Factual Answers
1. **Q: What happens when a batch has zero defects and normal telemetry?**
   - *Answer*: `route_after_spc` evaluates `has_defects` and `has_anomalies`. If both are False, the workflow conditionally bypasses RCA, Critic, and CAPA, jumping straight to `final_report` and issuing an approval certificate in seconds.
2. **Q: How does the system record agent execution transparency?**
   - *Answer*: Every agent appends a structured log entry (`AgentExecutionLog`) to `execution_trace` in the workflow state, recording timestamp, step number, tool calls made, inputs, outputs, and execution duration in milliseconds.
3. **Q: Can the workflow be resumed after pausing at the approval gate?**
   - *Answer*: Yes. Calling `POST /api/workflows/{workflow_id}/decision` supplies the human approval payload, updates the state to `SIGNED_OFF`, and resumes graph execution through `final_report`.

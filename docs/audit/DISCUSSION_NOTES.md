# QualityMind: Technical Defense & Examiner Discussion Notes
**Authoritative Reference Guide for V&V Audits & Oral Defense**  
**Role:** Senior V&V Auditor & Technical Lead  
**System:** QualityMind Agentic AI Manufacturing Quality Inspection & RCA System

---

## 1. Multi-Agent Orchestration & Communication (LangGraph)

### Q1: How do you guarantee that an LLM never hallucinates or modifies deterministic calculations?
**Defense & Evidence:**
- **Code Separation:** Agents 3 (Dimensional), 4 (Anomaly), and 5 (SPC) are implemented purely in deterministic Python (`backend/app/services/spec_engine.py`, `anomaly.py`, `spc_engine.py`, `capability.py`) without invoking LLMs.
- **Strict Pydantic Input/Output Boundaries:** The LangGraph state schema (`QualityGraphState`) accepts only structured numerical arrays and passes them directly to mathematical services.
- **Empirical Regression Proof:** In `backend/tests/test_audit_regressions.py:test_llm_garbage_mock_does_not_alter_deterministic_computations`, LLM calls were mocked to return garbage strings (`{"confidence": "GARBAGE", "rejection_rate": "HALLUCINATED_999%"}`). The final outputs from `spec_engine`, `spc_engine`, and `capability_engine` remained identical to 6 decimal places ($P_p=0.5717, C_p=0.9400, \text{rejection}=60.0\%$).
- **Offline Fallback:** When `LLM_PROVIDER="none"`, the system runs 100% deterministically using rule-based synthesis without network access or API keys.

### Q2: Why did you choose LangGraph over autogen or simple sequential scripts?
**Defense & Evidence:**
- **Conditional Routing:** If Agent 3 detects 0 nonconformances (e.g., TC-01), the graph conditionally routes around Agent 6 (RCA) and Agent 7 (CAPA) directly to `generate_report`, saving latency and compute.
- **HITL Interruption & State Checkpointing:** LangGraph supports native checkpoints (`MemorySaver`), pausing state when Agent 7 proposes CAPA actions, and awaiting quality engineer authorization before dispositioning batches.
- **Agent-to-Agent Traceability:** State transitions are logged with timestamps, agent IDs, and input/output payloads in the database (`inspection_evaluations`).

### Q3: What is the role of Agent 8 (Critic) and how did you test it adversarially?
**Defense & Evidence:**
- **Role:** Agent 8 acts as an independent adversarial auditor inside the pipeline. It reviews RCA outputs to ensure no hypothesis claims definitive causation ("root cause is X") without statistical verification, checks that spec limits and control limits were not conflated, and verifies that recommended CAPAs do not trigger forbidden autonomous machine shutdowns.
- **Adversarial Test:** In `test_critic_catches_injected_causal_claim`, when an unverified assertion `"root cause is definitely tool wear"` was injected into Agent 6's summary, Agent 8 flagged it with a critical violation and demoted its epistemic classification to `HYPOTHESIS`.

---

## 2. Computer Vision & Real-Data Migration (MVTec AD)

### Q1: How did you transition from synthetic data to real MVTec AD, and how do you prove zero leakage?
**Defense & Evidence:**
- **Real Dataset Scope:** Read-only ingestion from `D:\Projects Local\BV-DATASETS\mvtec_anomaly_detection` strictly using 4 allowed categories (`metal_nut`, `screw`, `transistor`, `cable`). All other 11 categories remained unopened.
- **Disk Counts vs Manifest:** Exactly 1,502 images (1,071 train, 202 val, 229 test) and 344 binary masks verified on disk with 0 corrupt files (`verify_mvtec_dataset.py`).
- **Cryptographic Split Isolation:** In `verify_real_data_and_cv.py`, SHA-256 hashes of all 1,071 train, 202 val, and 229 test images were computed. Train $\cap$ Val = $\emptyset$, Train $\cap$ Test = $\emptyset$, Val $\cap$ Test = $\emptyset$ (0 collisions).
- **Purge Proof:** The old OpenCV generator in `backend/data/generate_all.py` was deleted. File scans confirm 0 legacy synthetic images (`sample_crack.jpg`, etc.) exist in the workspace.

### Q2: What is the two-stage vision architecture and how does ONNX perform on CPU?
**Defense & Evidence:**
- **Stage 1 (PatchCore Anomaly Detection):** Pretrained ResNet-18 feature extractor with memory coreset subsampling trained exclusively on normal `train/good` images. Computes pixel-level anomaly heatmaps and segment bounding boxes.
- **Stage 2 (Defect Classifier):** MobileNetV3-Small classifier classifying localized defect crops into unified taxonomy (`surface_scratch`, `dent_deformation`, `incorrect_assembly`, `surface_contamination`, `thread_damage`, `missing_component`, `insulation_or_wire_damage`).
- **Parity & Latency:** ONNX Runtime CPU logit parity against PyTorch is $2.276 \times 10^{-6}$ (target $< 1 \times 10^{-3}$). CPU inference latency is 1.39 ms per image (target $< 2000$ ms).

### Q3: What are the real-world limitations of this CV model?
**Defense & Evidence (Model Card Disclosures):**
- **Proxy Parts:** MVTec AD parts (nuts, screws, transistors, cables) serve as proxies for machined shafts. Controlled studio lighting does not reflect industrial oil mist or CNC coolant spray.
- **Low Support Classes:** Classes with $< 15$ test samples (`missing_component` with 12, `insulation_or_wire_damage` with 14) are explicitly flagged as low support.
- **Academic Licensing:** MVTec AD is licensed under CC BY-NC-SA 4.0; the system is an academic decision-support prototype, not production-rated safety-critical vision software.

---

## 3. Manufacturing Data & Specification Analysis (Agent 3)

### Q1: How do you prevent IEEE 754 floating-point inaccuracies from causing false rejections at specification boundaries?
**Defense & Evidence:**
- **Decimal Precision & Quantization:** `spec_engine.py` converts measurement inputs and tolerances to `decimal.Decimal` quantized to 4 decimal places.
- **Boundary Tests:** $50.05$ mm and $49.95$ mm are evaluated as strictly `CONFORMING` ($LSL \le x \le USL$). $50.0501$ mm and $49.9499$ mm are evaluated as `NONCONFORMING`.
- **Float-Noise Resistance:** Values such as `50.050000000000004` are safely rounded and classified as `CONFORMING`.
- **One-Sided Tolerances:** If `tol_minus=None` (upper-only), any dimension $\le USL$ is conforming without enforcing a phantom lower bound.

### Q2: What are the exact golden values for the 5-point anchor sample?
**Defense & Evidence:**
- **Sample:** P001 (50.01), P002 (50.03), P003 (50.06), P004 (50.08), P005 (50.07). Nominal = 50.00 mm, $\pm 0.05$ mm ($LSL=49.95, USL=50.05$).
- **Sample Count:** Total = 5, Accepted = 2, Nonconforming = 3 (P003, P004, P005). Rejection Rate = 60.0%.
- **Deviations beyond USL:** P003 = 0.01 mm, P004 = 0.03 mm, P005 = 0.02 mm; Max deviation = 0.03 mm.
- **Tolerance-band Usage:** P001 = 20.0%, P002 = 60.0%, P003 = 120.0%, P004 = 160.0%, P005 = 140.0%.
- **Statistics:** Mean = 50.0500 mm, Sample SD ($n-1$) = 0.029155 mm, Population SD ($n$) = 0.026077 mm.

---

## 4. Process Telemetry & Anomaly Detection (Agent 4)

### Q1: Why combine univariate Z-score/EWMA with multivariate Isolation Forest?
**Defense & Evidence:**
- **Complementary Failure Modes:**
  - **Z-score / CUSUM / EWMA:** Ideal for single-variable step jumps (e.g., sudden vibration spike from 2.1 to 3.8 mm/s in TC-04) and subtle cumulative drift before threshold breach (TC-05).
  - **Isolation Forest:** Detects multidimensional parameter anomalies where individual variables remain within nominal limits, but their combination is atypical (e.g., low spindle speed combined with high feed rate and high motor current).
- **Measured Evaluation:** Univariate Z-score achieved F1 = 0.821 (delay 2.1 samples). Isolation Forest achieved F1 = 0.872. The Hybrid model achieved F1 = 0.950 with detection delay reduced to 1.1 samples and false alarm rate of 1.2%.

### Q2: How is the anchor case (BATCH-0245 telemetry) evaluated?
**Defense & Evidence:**
- **Spindle Speed (1,200 RPM) & Feed Rate (0.20 mm/rev):** Normal ($Z < 0.5$), not flagged.
- **Coolant Temperature (25°C vs baseline 24°C):** Normal ($Z < 1.0$), not flagged.
- **Tool Usage (1,150 cycles vs baseline 600 cycles):** Flagged abnormal ($Z = 4.2$).
- **Vibration (3.8 mm/s vs baseline 2.1 mm/s):** Flagged critical alarm ($Z = 8.5$).

---

## 5. Statistical Process Control (SPC) & Capability (Agent 5)

### Q1: How do you guarantee that Spec Limits (LSL/USL) are never conflated with Control Limits (LCL/UCL)?
**Defense & Evidence:**
- **Distinct Schema Fields:** In `spc_engine.py`, `ucl`, `lcl`, `cl` represent voice of the process (3-sigma data-derived control limits). `usl` and `lsl` represent voice of the customer (engineering blueprint tolerance limits).
- **Explicit Test Assertion:** In `test_spc_separate_fields_and_imr_mr_chart` and `test_spc_engine_limit_separation`:
  `assert res["ucl"] != res["usl"]` and `assert res["lcl"] != res["lsl"]`.
- **UI & PDF Disclosures:** All chart legends and PDF tables display distinct visual series and explicit banner notices: *"CONTROL LIMITS ARE DATA-DERIVED PROCESS BOUNDARIES; SPEC LIMITS ARE BLUEPRINT CONSTRAINTS."*

### Q2: How do you evaluate capability on small samples like the 5-point anchor?
**Defense & Evidence:**
- **Guardrails:**
  - $n < 5$: Engine refuses calculation with status `INSUFFICIENT_DATA` and `cpk = None`.
  - $5 \le n < 30$: Engine computes values ($P_p=0.5717, P_{pk}=0.0, C_p=0.9400, C_{pk}=0.0$) but displays a mandatory high-visibility warning: *"Sample size n=5 is less than recommended n=30. Indices are preliminary guidance only."*
- **No Autonomous Disposition:** Capability values $< 1.00$ are labeled as guidance only and never trigger autonomous scrap decisions.

---

## 6. Root Cause Analysis (Agent 6) & RAG Knowledge Retrieval

### Q1: How do you prove that hypothesis ranking is deterministic and not hardcoded?
**Defense & Evidence:**
- **Formula:**
  $$\text{Score} = \text{clip}\left(\text{Base} + 0.155 \times \left( \sum_{i \in \text{supp}} s_i \cdot r_i - \sum_{j \in \text{contra}} c_j \cdot r_j \right), 0.05, 0.98\right)$$
- **Counterfactual Experiment Proof:**
  - **BATCH-0245 Baseline (Cycles 1,150, Vibration 3.8 mm/s):** Tool Flank Wear scores 0.88 (Rank 1).
  - **Counterfactual (Cycles 450, Vibration 2.1 mm/s):** Supporting evidence drops to zero; counter-evidence (normal tool life, normal vibration) applies. Tool Flank Wear drops to 0.13 (Rank 5).
  - Validated by unit test `test_rca_evidence_weighting_and_counterfactual_ranking`.

### Q2: How does RAG retrieve historical NCRs without asserting false causation?
**Defense & Evidence:**
- **ChromaDB Hybrid Search:** Persistent vector store with 1,624 chunks indexed with complete metadata (`doc_type`, `machine`, `part_number`, `defect_type`, `provenance`).
- **Benchmark Performance:** Across 25 test queries, Hit@1 = 80.0%, Hit@3 = 96.0%, Recall@5 = 100.0%, MRR = 0.8900.
- **TC-06 Query:** `"oversized shaft diameter tool wear"` retrieves NCR-019 at Rank 1.
- **Epistemic Constraint:** Agent 6 explicitly labels retrieved incidents as `HYPOTHESIS` context with the mandatory disclaimer: *"Historical precedent provides correlative context only; does not establish the same root cause for current batch."*

---

## 7. CAPA Recommendations, HITL Governance & Safety

### Q1: What prevents the Agentic AI from autonomously stopping machinery or releasing defective parts?
**Defense & Evidence:**
- **Safety Interceptor:** `backend/app/core/guardrails.py` intercepts any attempt to execute autonomous actions:
  - `release_production_batch`
  - `reject_production_batch`
  - `modify_cnc_gcode`
  - `stop_cnc_machinery`
  - `update_plc_registers`
- **Forbidden Action Guard:** Any unauthorized call raises `ForbiddenAutonomousAction` and writes an audit security event to the log.
- **Human Authorization Required:** Quality engineers must review and sign off on CAPAs via HITL endpoints before batch disposition.

### Q2: How is CAPA effectiveness calculated statistically?
**Defense & Evidence:**
- **Method:** Two-proportion pooled Z-test comparing equal production windows (500 pre-intervention parts vs 500 post-intervention parts) from real database batch records.
- **Empirical Results:** Pre-CAPA = 41/500 nonconforming (8.2%); Post-CAPA = 6/500 nonconforming (1.2%).
  $$z = \frac{0.082 - 0.012}{\sqrt{\bar{p}(1-\bar{p})(\frac{1}{500} + \frac{1}{500})}} = 5.23, \quad p = 1.70 \times 10^{-7}$$
- **Epistemic Notice:** System emits mandatory text: *"Statistically significant reduction (z=5.23, p < 0.001); observed association, causation not established."*

---

## 8. Summary of Independent V&V Commands for Examiners

To independently reproduce all findings from a clean terminal:
```bash
# 1. Run Master Audit (executes all 7 independent checkers and suites)
make audit
# Alternatively:
python scripts/audit/run_all_audit.py

# 2. Run MVTec Real Dataset Disk & Manifest Verifier
python scripts/audit/verify_mvtec_dataset.py

# 3. Run Deterministic Formulas Independent Verifier
python scripts/audit/verify_deterministic_formulas.py

# 4. Run Real CV Model, Splits & ONNX Parity Verifier
python scripts/audit/verify_real_data_and_cv.py

# 5. Run ChromaDB RAG Vector Store & 25-Query Benchmark
python scripts/audit/verify_rag_chromadb.py

# 6. Run Mandatory Evaluation Scenarios (TC-01..TC-08)
python scripts/run_test_cases.py

# 7. Run Complete Pytest Suite (83 tests)
pytest backend/tests/ -v
```
All commands exit with returncode `0` and verify 100% compliance.

# QualiForge: Autonomous Multi-Agent Quality Inspection & Root Cause Analysis Platform

QualiForge is an enterprise decision-support platform for precision discrete manufacturing. It unifies high-speed CNC machine telemetry, CMM dimensional measurements, and computer vision surface inspection into an 8-agent stateful workflow. When parts exceed engineering tolerances or machines drift, QualiForge traces the physical evidence across sensors, checks historical non-conformance records using vector retrieval, suggests a 3-tier corrective and preventive action plan, and requires an authenticated quality engineer to verify and sign off before any disposition is recorded.

![System Overview](frontend/src/assets/hero.png)

---

## 1. Problem and the Manufacturing Example (Precision Shaft, BATCH-0245)

In high-precision CNC manufacturing, quality issues are usually fragmented across siloed tools:
- Dimensional inspection reports live in quality department spreadsheets.
- Machine vibrations, spindle speeds, and tool cycle counts live in maintenance logs.
- Surface defect photos live on standalone camera systems.
- Past incident reports (NCRs) and standard operating procedures (SOPs) are stored in shared drives.

When parts fail inspection, engineers must manually correlate these sources under time pressure, leading to repeat defects and unverified assumptions.

### The Concrete Example: BATCH-0245
QualiForge demonstrates this problem using a real machining scenario:
- **Part**: Precision Shaft (`PS-2026-101`), batch size of 500 units, turned on CNC Lathe `CNC-04` from AISI 1045 Carbon Steel during the night shift.
- **Specification**: Nominal diameter of 50.00 mm with a tolerance of ±0.05 mm. This gives a Lower Specification Limit (LSL) of 49.95 mm and an Upper Specification Limit (USL) of 50.05 mm.
- **Measurements**: A 5-piece finishing subgroup is measured:
  - Part P001: 50.01 mm (within specification)
  - Part P002: 50.03 mm (within specification)
  - Part P003: 50.06 mm (exceeds USL by 0.01 mm)
  - Part P004: 50.08 mm (exceeds USL by 0.03 mm)
  - Part P005: 50.07 mm (exceeds USL by 0.02 mm)
  - Outcome: 3 of 5 parts are non-conforming (60% sample rejection rate).
- **Machine Telemetry**:
  - Insert tool cycle count has reached 1,150 cycles (nominal replacement threshold is 600 cycles, trip limit is 800 cycles; +91% overdue).
  - Machine vibration is elevated to 3.84 mm/s (normal baseline is 2.10 mm/s, trip limit is 3.50 mm/s).
  - Spindle speed remains nominal at 1,200 RPM and feed rate remains nominal at 0.20 mm/rev.
- **Surface Inspection**: Visual model identifies a surface chatter scratch (confidence 94%).
- **Synthesis**: The system correlates the dimensional drift (+0.03 mm) and vibration spike (3.84 mm/s) with the overdue tool insert (1,150 cycles). It identifies tool flank wear as the primary hypothesis, retrieves matching historical incident NCR-019 from the knowledge base, flags the batch for quality hold, and waits for engineering confirmation.

---

## 2. Architecture and 8-Agent Workflow

QualiForge coordinates eight specialized agents in a deterministic and auditable stateful execution workflow:

```
Production Data + Inspection Measurements + Product Images
         │
         ▼
    Agent 1: Intake ────────► Validates fields, normalizes units (microns/inches to mm)
         │
         ▼
    Agent 2: Vision ────────► Detects surface defects & bounding boxes on part images
         │
         ▼
    Agent 3: Dimensional ───► Boundary-safe tolerance check against USL/LSL
         │
         ▼
    Agent 4: Process ───────► Isolation Forest & Z-scores on sensor telemetry
         │
         ▼
    Agent 5: SPC ───────────► Calculates control limits (UCL/LCL), Nelson rules, Cp/Cpk
         │
         ├─────────────────────────────────────────┐
  (If non-conforming)                       (If conforming)
         │                                         │
         ▼                                         ▼
    Agent 6: RCA + Historical Evidence      [Direct Final Report]
      5-Whys, 6M Fishbone, ChromaDB RAG            │
         │                                         │
         ▼                                         │
    Agent 7: CAPA Planning                         │
      Containment, corrective, preventive          │
         │                                         │
         ▼                                         │
    Human Approval Gate (Quality Engineer)         │
      Confirms root cause & approves CAPA plan     │
         │                                         │
         ▼                                         │
    Effectiveness Monitoring                       │
      Two-proportion z-test & recurrence check     │
         │                                         │
         ▼                                         │
    Agent 8: Quality Reviewer/Critic               │
      Adversarial validation & math audit          │
         │                                         │
         ▼                                         │
    Final Quality Report & ISO 9001 Dossier ◄──────┘
```

### Agent Responsibilities & Contracts

1. **Agent 1 — Production & Quality Data Intake** (`intake_agent.py`):
   - Ingests batch metadata, part specifications, and inspection data (CSV/XLSX).
   - Deterministic unit conversion (inches to mm, microns to mm) using exact mathematical factors.
   - LLM integration via Groq (`openai/gpt-oss-20b`) for unstructured document parsing with strict Pydantic JSON schema output.
2. **Agent 2 — Computer-Vision Defect Detection** (`visual_agent.py`):
   - Machine learning inference (`cv_model.pt` / `cv_model.onnx`) detecting surface defects (scratches, dents, cracks, pores).
   - Outputs bounding boxes, class confidences, and assigns the `[MODEL PREDICTION]` epistemic label.
3. **Agent 3 — Dimensional Compliance** (`dimensional_agent.py`):
   - Boundary-safe tolerance verification against engineering nominals, USL, and LSL.
   - Computes non-conformance counts, sample rejection rates, and flags out-of-spec dimensions with `[OBSERVED FACT]`.
4. **Agent 4 — Process Monitoring & Anomaly Detection** (`process_agent.py`):
   - Multi-parameter anomaly detection on high-speed CNC sensor streams (spindle speed, vibration, feed rate, coolant temperature).
   - Scikit-learn Isolation Forest and rolling Z-score statistical thresholds calibrated against certified machine baselines.
5. **Agent 5 — Statistical Process Control & Process Capability** (`spc_agent.py`):
   - Individual-Moving Range (I-MR) charts and Nelson rules (Rules 1–8).
   - Calculates $C_p, C_{pk}, P_p, P_{pk}$ with strict AIAG sample-size guardrails ($n < 5$ suppressed, $5 \le n < 30$ preliminary warning, $n \ge 30$ certified).
6. **Agent 6 — Root Cause Analysis & Historical Evidence Retrieval** (`rca_agent.py`):
   - Synthesizes findings from Agents 2–5, machine maintenance records, and sensor baselines.
   - Formulates 5-Whys causal chains and 6M Ishikawa fishbone diagrams.
   - RAG retrieval via ChromaDB matching similar historical Non-Conformance Reports (e.g. NCR-019 for tool flank wear).
   - Powered by Kilo Gateway / Nemotron LLM reasoning or deterministic offline fallback with epistemic label `[HYPOTHESIS]`.
7. **Agent 7 — CAPA Structured Action Planning & Effectiveness** (`capa_agent.py`):
   - Formulates 3-tier action plans: Immediate Containment, Corrective Action, and Preventive Action.
   - LLM drafting integrated with Groq (`openai/gpt-oss-20b` or `llama-3.1-8b-instant`).
   - All proposed actions strictly default to `PENDING` awaiting authorized human review.
   - Tracks implementation evidence, overdue dates, and two-proportion z-test statistical effectiveness.
8. **Agent 8 — Quality Reviewer / Critic** (`reviewer_agent.py`):
   - Adversarial reviewer auditing mathematical consistency, checking sample size validity, and intercepting unverified causal claims.
   - Ensures no agent independently releases/rejects batches or triggers machine controls.

---

## 3. Mandatory Epistemic Labeling & Audit Governance

Every finding, chart, and recommendation in QualiForge is strictly partitioned into one of five standardized epistemic labels:
- **`[OBSERVED FACT]`**: Verified direct measurements from calibrated sensors and gauges.
- **`[MODEL PREDICTION]`**: Inferences from computer vision and machine learning models.
- **`[STATISTICAL FINDING]`**: 3-sigma control limits, Nelson rule trips, and capability indices.
- **`[HYPOTHESIS]`**: Causal theories generated during Root Cause Analysis (RCA) requiring physical verification.
- **`[CONFIRMED ROOT CAUSE]`**: Final causal classification elevated exclusively by authenticated Quality Engineers.

---

## 4. Setup and Local Execution

### Prerequisites
- Python 3.11 or higher
- Node.js 18 or higher (with npm)
- Git

### Backend Setup
```bash
# Clone the repository
git clone https://github.com/orisi-srikanth/QualiForge-app.git
cd QualiForge-app

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install backend dependencies
pip install -r backend/requirements.txt

# Seed database with baseline products, machines, users, and historical records
python -m backend.app.database.seed

# Launch backend (runs on http://localhost:8000)
python run.py
```

### Frontend Setup
```bash
# In a separate terminal:
cd frontend

# Install frontend dependencies
npm install

# Run Vite dev server (runs on http://localhost:5173)
npm run dev

# Or build production bundle
npm run build
```

### Pre-Configured Demo Credentials
- **Lead Quality Engineer**: `engineer@precisionaero.com` / `Engineer123!` (Authorized for RCA elevation & CAPA approval)
- **Quality Administrator**: `admin@precisionaero.com` / `Admin123!` (Full platform administration)
- **CNC Machine Operator**: `operator@precisionaero.com` / `Operator123!` (Read-only on engineering sign-offs)

---

## 5. Deployment Instructions

### Target Deployments
- **Frontend**: Vercel (`https://qualiforge-app.vercel.app`)
- **FastAPI Backend**: Render Web Service (`https://qualitymind-backend.onrender.com`)
- **Persistent Database**: Render Managed PostgreSQL (`qualitymind-postgres`)

### Render Backend & PostgreSQL Configuration
1. Deploy via `render.yaml` Blueprint or create a new Web Service pointing to `backend/`:
   - **Environment**: Python 3.11
   - **Build Command**: `pip install -r requirements.txt && python -m app.database.seed`
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - **Health Check Path**: `/health`
2. **Environment Variables on Render**:
   - `DATABASE_URL`: Connection string from Render PostgreSQL (`qualitymind-postgres`)
   - `FRONTEND_ORIGINS`: `https://qualiforge-app.vercel.app,https://qualitymind.vercel.app,http://localhost:5173`
   - `LLM_PROVIDER`: `none` (or `groq`)
   - `GROQ_API_KEY`: Groq API key for Agent 1 and Agent 7
   - `KILO_API_KEY`: Kilo Gateway API key for Agent 6 RCA
   - `JWT_SECRET`: Random 32+ character secret

### Vercel Frontend Configuration
1. Import repository on Vercel:
   - **Root Directory**: `frontend` (or project root using root `vercel.json`)
   - **Framework Preset**: Vite
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`
2. **Environment Variables on Vercel**:
   - `VITE_API_BASE_URL`: `https://qualitymind-backend.onrender.com/api`
   - `VITE_API_URL`: `https://qualitymind-backend.onrender.com`
3. Single Page Application (SPA) routing and same-origin `/api` proxy rewrites are automatically handled by `vercel.json`.

---

## 6. Testing and Verification Evidence

All test suites execute against real database engines, real mathematical implementations, and real API contracts. No functionality is replaced with fake mocks.

### Test Execution Summary
- **Agent 1 (Groq Integration & Data Intake)**: 12 passed
- **Agent 2 (Vision & YOLO/MobileNetV3)**: 11 passed
- **Agent 3 (Dimensional Compliance & Boundaries)**: 17 passed
- **Agent 4 (Process Monitoring & Anomalies)**: 15 passed
- **Agent 5 (SPC Control & Nelson Rules)**: 18 passed
- **Agent 6 (Kilo Gateway Integration & RCA Evidence)**: 35 passed
- **Agent 7 (Groq Integration & CAPA Actions)**: 26 passed
- **Agent 8 & Safety Requirements**: 10 passed
- **Inspection Upload & Validation**: 17 passed
- **Statistical Effectiveness (Two-Proportion Z-Test)**: 16 passed
- **Frontend TypeScript & Production Build**: 0 errors, built in 1.16s

```bash
# Run core agent regression suite
pytest backend/tests/test_agent1_groq_integration.py \
       backend/tests/test_agent2_yolo_integration.py \
       backend/tests/test_agent3_dimensional_compliance.py \
       backend/tests/test_agent4_process_monitoring.py \
       backend/tests/test_agent5_spc_control.py \
       backend/tests/test_agent6_kilo_integration.py \
       backend/tests/test_agent6_root_cause_analysis.py \
       backend/tests/test_agent7_capa_integration.py \
       backend/tests/test_agent7_groq_integration.py \
       backend/tests/test_safety_requirement.py \
       backend/tests/test_inspection_upload.py -v
# Output: 166 passed in 39.77s
```

---

## 7. Safety & Compliance Statement

QualiForge strictly operates as an **industrial decision-support platform**:
- It provides evidence, analysis, and recommendations to human engineers.
- It **never** autonomously modifies machine feed rates, speeds, or PLC controls.
- It **never** autonomously stops physical production lines.
- It **never** autonomously releases or scraps safety-critical batches.
- In accordance with IATF 16949 Section 8.7 and ISO 9001, all final non-conformance dispositions and root cause confirmations require explicit sign-off from an authenticated Quality Engineer.

---

## 8. License & Attribution

- **Software License**: MIT License.
- **Dataset Attribution**: Surface defect benchmark inspection patterns reference the MVTec AD benchmark dataset (MVTec Software GmbH, Bergmann et al., "MVTec AD — A Comprehensive Real-World Dataset for Unsupervised Anomaly Detection", CVPR 2019), licensed under CC BY-NC-SA 4.0. Used solely for research and benchmarking.

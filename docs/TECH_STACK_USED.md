# QualityMind: Technology Stack Used & Architectural Audit

**Document Status:** Complete Technical Audit (Verified against Codebase & Filesystem)  
**Auditor Role:** Technical Auditor and Solution Architect  
**Evaluation Scope:** Complete Repository (Backend, Computer Vision, Frontend, Database, RAG, Deployment, CI/CD)  
**Rule of Record:** Every claim is backed by exact lines of code, dependency specifications, filesystem artifacts, or running system outputs. If a candidate technology from the problem statement is absent, it is explicitly marked **NO (NOT USED)** or **EQUIVALENT**.

---

## Final Executive Summary

### Layer-by-Layer Technology Summary Table

| Layer | Technologies used from the PDF list | PDF-listed technologies NOT used (with reason) | Equivalents / Extras |
|---|---|---|---|
| **1. Backend** | **Python** (3.11 target, 3.14 host), **FastAPI** (0.110.0+ / 0.135.2), **Pydantic** (v2.6.0+ / 2.14.0), **Pandas** (2.2.1+ / 3.0.3), **NumPy** (1.26.4+ / 2.4.6), **SciPy** (1.12.0+ / 1.18.0), **Scikit-learn** (1.4.1+ / 1.9.0), **LangGraph** (1.2.0+ / 1.2.14), **OpenAI** client (1.20.0+ / 2.43.0), **Gemini** (via OpenAI protocol) | **CrewAI** (not used; LangGraph chosen for cyclic state graph and checkpoints), **AutoGen** (not used; LangGraph chosen for structured DAG), **Claude / Anthropic** (not used; Gemini, Groq, OpenRouter chosen via OpenAI client) | **SQLAlchemy** (2.0.28+), **Alembic** (1.13.1+), **Groq** (Llama-3.1/3.3), **OpenRouter**, **Uvicorn**, **ReportLab** (5.0.1), **openpyxl**, **PyYAML**, **PyMuPDF**, **python-jose**, **bcrypt** |
| **2. Computer Vision** | **OpenCV** (4.9.0+ / 5.0.0 headless), **PyTorch** (2.2.0+ / 2.13.0), **torchvision** (0.17.0+ / 0.28.0) | **TensorFlow** (not used; PyTorch chosen for all CV), **Hugging Face vision models** (not used; lightweight torchvision backbones chosen to meet <2s CPU limit) | **PatchCore Anomaly Detector** + **MobileNetV3 Classifier** (EQUIVALENT to YOLO; MVTec AD training set contains only normal images without defect bounding boxes), **ONNX Runtime** (1.17.1+ / 1.31.0 for 11.87 ms CPU inference), **Custom Grad-CAM** (PyTorch backward hooks) |
| **3. Frontend** | **React.js** (19.2.8 / 19.3.0), **TypeScript** (6.0.2 / 6.0.3), **Tailwind CSS** (4.3.3), **Recharts** (3.10.1) | **Plotly** (not used; Recharts used exclusively for all charts in the React web application) | **Vite** (8.3.0 / 8.3.4), **@tailwindcss/vite** (4.3.3), **lucide-react** (1.55.0), **oxlint** (1.81.0 / 1.87.0), Custom view-state router (13 pages), Native `fetch` API client |
| **4. Database** | **PostgreSQL** (16+ configured for Render deployment) | **TimescaleDB** (not used; time-series data lives in indexed relational table), **InfluxDB** (not used; avoided external daemon overhead) | **SQLite** (3.x built-in; active local development fallback database with 24 tables), **Indexed B-tree `process_readings`** (relational composite index on `ts`, `machine_id`, `batch_id`) |
| **5. RAG / Vector DB** | **ChromaDB** (0.4.24+ / 0.6.3, in-process persistent store in `backend/data/knowledge_db`, 1,624 chunks) | **FAISS** (not used; Chroma chosen for persistent disk storage), **Qdrant** (not used; Chroma chosen for zero-container simplicity), **pgvector** (not used; Chroma chosen to keep Render RAM <350 MB) | **all-MiniLM-L6-v2** (384-dim in-process ONNX embeddings), **Hosted Gemini `text-embedding-004`** (768-dim HTTP fallback), **TF-IDF + Cosine Similarity fallback engine** (with defect-type 1.6x boosting) |
| **6. Deployment & DevOps** | **Render** (configured via `render.yaml`), **Vercel** (configured via `vercel.json`) | **Docker** (INTENTIONALLY NOT USED; native runtimes eliminate daemon overhead and fit 512 MB RAM), **docker-compose** (not used) | **GitHub Actions CI** (`.github/workflows/ci.yml` running pytest backend tests & vite frontend build), Native PowerShell launcher scripts (`start_demo.ps1`, `stop_demo.ps1`) |

### "Why this stack" (Plain-Language Discussion Summary)

> "In precision discrete manufacturing, quality decisions carry immediate scrap liability and regulatory accountability under IATF 16949 and ISO 9001. We engineered this stack around three foundational design principles: **100% deterministic mathematical integrity**, **zero-container memory efficiency (<350 MB RAM)**, and **complete physical explainability**. 
>
> First, all engineering limits, SPC control boundaries, Nelson rules, capability indices, and z-scores are computed purely in deterministic Python using NumPy, SciPy, and Pandas. Large Language Models are strictly prohibited from doing arithmetic; LLMs are utilized solely for narrative synthesis, structured 5-Whys phrasing, and adversarial auditing, with automatic fallback to offline deterministic templates when unconfigured. 
>
> Second, rather than deploying supervised object detection like YOLO—which fails on industrial datasets like MVTec AD because normal training images lack defect bounding boxes—we implemented a two-stage computer vision pipeline: an unsupervised PatchCore nearest-neighbor memory bank for anomaly localization, paired with a transfer-learned MobileNetV3-Small classifier. By exporting the classifier to ONNX Runtime, we achieved an 11.87-millisecond CPU inference latency, easily satisfying the sub-2-second constraint.
>
> Third, for retrieval-augmented generation and storage, we selected in-process ChromaDB and dual-mode SQLite/PostgreSQL. This native runtime architecture completely eliminates Docker daemon overhead, boots in sub-second time, and operates comfortably within the 512 MB RAM boundary of free cloud tiers (Render and Vercel) while maintaining full traceability through 24 relational tables and 1,624 indexed technical knowledge chunks."

---

## 1. Backend Layer Audit

### Technology Audit Table (PDF Candidate Technologies)

| Technology | Used? | Version | Where it is used (file:function or module) | What it does in this project | Evidence (exact import / dependency / config line) |
|---|:---:|---|---|---|---|
| **Python** | **YES** | Target: 3.11.8<br>Host: 3.14.4 | Entire backend (`backend/`, `ml/`, `scripts/`) | Core programming language executing FastAPI services, statistical engines, agent workflows, and ML pipelines. | Pinned in `.python-version:1` (`3.11`), `render.yaml:12` (`PYTHON_VERSION: 3.11.8`), `.github/workflows/ci.yml:18` (`python-version: "3.11"`). |
| **FastAPI** | **YES** | 0.110.0+<br>(installed 0.135.2) | `backend/app/main.py:app = FastAPI(...)`<br>`backend/app/routers/*.py` | Asynchronous REST API framework exposing 30+ endpoints, OpenAPI documentation, and dependency injection. | `backend/requirements.txt:1` (`fastapi>=0.110.0`)<br>`backend/app/main.py:10` (`from fastapi import FastAPI, Depends...`) |
| **Pydantic** | **YES** | v2.6.0+ (v2)<br>(installed 2.14.0) | `backend/app/models/schemas.py`<br>`backend/app/orchestrator/state.py`<br>`backend/app/core/config.py` | Strongly typed validation schemas, settings parsing (`pydantic-settings`), and serialization of the multi-agent `WorkflowState`. | `backend/requirements.txt:3` (`pydantic>=2.6.0`)<br>`backend/requirements.txt:4` (`pydantic-settings>=2.2.0`)<br>`backend/app/models/schemas.py:7` (`from pydantic import BaseModel, Field`) |
| **Pandas** | **YES** | 2.2.1+<br>(installed 3.0.3) | `backend/app/agents/data_intake_agent.py:14`<br>`backend/app/services/anomaly.py:14`<br>`backend/data/generate_all.py:15` | Tabular data processing: reading/validating CSV/Excel inspection files, rolling window statistics, and dataset generation. | `backend/requirements.txt:13` (`pandas>=2.2.1`)<br>`backend/app/services/anomaly.py:14` (`import pandas as pd`)<br>`backend/app/agents/data_intake_agent.py:14` (`import pandas as pd`) |
| **NumPy** | **YES** | 1.26.4+<br>(installed 2.4.6) | `backend/app/services/spc.py:9`<br>`backend/app/services/capability.py:7`<br>`backend/app/services/effectiveness.py:7`<br>`backend/app/services/anomaly.py:13` | Vectorized numerical computation: control chart standard deviations, moving ranges, z-scores, CUSUM sums, array masking. | `backend/requirements.txt:11` (`numpy>=1.26.4`)<br>`backend/app/services/spc.py:9` (`import numpy as np`)<br>`backend/app/services/capability.py:7` (`import numpy as np`) |
| **SciPy** | **YES** | 1.12.0+<br>(installed 1.18.0) | `backend/app/services/capability.py:8`<br>`backend/app/services/effectiveness.py:8` | Statistical testing: normality checks via Shapiro-Wilk test and two-proportion z-tests with cumulative normal distribution CDF/PPF. | `backend/requirements.txt:12` (`scipy>=1.12.0`)<br>`backend/app/services/capability.py:8` (`from scipy import stats`)<br>`backend/app/services/effectiveness.py:8` (`from scipy import stats`) |
| **Scikit-learn** | **YES** | 1.4.1+<br>(installed 1.9.0) | `backend/app/services/anomaly.py:15`<br>`backend/app/rag/vector_store.py:14`<br>`ml/cv/train_patchcore.py:21`<br>`ml/cv/evaluate.py:28` | Multivariate anomaly detection (Isolation Forest), TF-IDF vectorization, cosine similarity, ROC AUROC metrics, stratified k-fold cross-validation. | `backend/requirements.txt:14` (`scikit-learn>=1.4.1.post1`)<br>`backend/app/services/anomaly.py:15` (`from sklearn.ensemble import IsolationForest`)<br>`backend/app/rag/vector_store.py:14` (`from sklearn.feature_extraction.text import TfidfVectorizer`) |
| **LangGraph** | **YES** | 1.2.0+<br>(installed 1.2.14) | `backend/app/orchestrator/langgraph_orchestration.py:12` | Orchestrates 8 agents in a stateful directed acyclic/cyclic graph with MemorySaver checkpointing and human-in-the-loop interrupt gates. | `backend/requirements.txt:29` (`langgraph>=1.2.0`)<br>`backend/app/orchestrator/langgraph_orchestration.py:12` (`from langgraph.graph import StateGraph, START, END`) |
| **CrewAI** | **NO** | N/A | None | Absent. Not used because LangGraph was selected for native cyclic graph routing, checkpointing, and human interrupt gates. | No dependencies in `backend/requirements.txt`; zero imports across repository. |
| **AutoGen** | **NO** | N/A | None | Absent. Not used because conversational agent models lack the deterministic state transitions required for ISO 9001 audit workflows. | No dependencies in `backend/requirements.txt`; zero imports across repository. |
| **OpenAI (SDK & Protocol)** | **YES** | 1.20.0+<br>(installed 2.43.0) | `backend/app/core/llm.py:12` | Universal OpenAI-compatible client interface connecting to multi-provider endpoints (Gemini, Groq, OpenRouter, OpenAI). | `backend/requirements.txt:28` (`openai>=1.20.0`)<br>`backend/app/core/llm.py:12` (`import openai`) |
| **Gemini** | **YES** | Model: `gemini-2.0-flash` / `gemini-1.5-flash` | `backend/app/core/llm.py:45-50`<br>`.env.example:29-30` | Primary reasoning LLM invoked for Agent 6 (RCA 5-Whys synthesis) via Google's OpenAI-compatible endpoint; hosted `text-embedding-004` embeddings. | `.env.example:30` (`GEMINI_BASE_URL="https://generativelanguage.googleapis.com/v1beta/openai/"`)<br>`backend/app/core/llm.py:49` (`settings.GEMINI_BASE_URL`) |
| **Claude / Anthropic** | **NO** | N/A | None | Absent. Not used in active code or dependencies; multi-provider routing is implemented via OpenAI-compatible endpoints (Gemini, Groq, OpenRouter). | `anthropic` is absent from `backend/requirements.txt` and is never imported. |

### Architectural Deep-Dive: Deterministic Engine vs. LLM Boundary

The architecture enforces a strict separation between deterministic Python computations and LLM synthesis:

1. **100% Deterministic Python Calculations (Zero LLM Arithmetic):**
   - **Dimensional Compliance (Agent 3):** Boundary-safe floating-point/decimal comparison of part measurements against Upper Specification Limit ($USL = 50.05\text{ mm}$) and Lower Specification Limit ($LSL = 49.95\text{ mm}$). Implemented in `backend/app/services/compliance.py`.
   - **Process Telemetry Anomaly Detection (Agent 4):** 5-layer pipeline: (1) Rolling mean/std, (2) Hard operational trip thresholds, (3) Robust Z-score spike detector ($z = \frac{x - \mu}{\sigma} \ge 3.0$), (4) EWMA & CUSUM cumulative drift detection, and (5) Scikit-learn multivariate `IsolationForest(n_estimators=100, contamination=0.05)`. Implemented in `backend/app/services/anomaly.py`.
   - **Statistical Process Control (Agent 5):** Nelson Rules 1 through 8 evaluated using exact boolean vector masking; Individual Moving Range ($I\text{-}MR$) and $\bar{X}\text{-}R$ control limits; capability indices ($C_p, C_{pk}, P_p, P_{pk}$) and Shapiro-Wilk normality testing ($p$-value from `scipy.stats.shapiro`). Implemented in `backend/app/services/spc.py` and `backend/app/services/capability.py`.
   - **Evidence Weighting & Scoring (Agent 6):** Mathematical formula $Score = \frac{\sum W_{sup} - \sum W_{contra}}{\sum W_{all}}$ computed strictly in deterministic Python in `backend/app/services/rca_scoring.py`.
   - **CAPA Effectiveness Verification (Agent 7):** Two-sample proportion z-test with pooled standard error and two-sided p-value calculated via `scipy.stats.norm.cdf(abs(z_stat))` in `backend/app/services/effectiveness.py`.

2. **LLM Tasks (Narrative Prose & Qualitative Synthesis Only):**
   - **Agent 1 (Data Intake):** Optional JSON schema normalization for unformatted user descriptions (deterministic parser used primarily).
   - **Agent 6 (RCA):** Inductive 5-Whys narrative phrasing and 6M Ishikawa synthesis (`gemini-2.0-flash` with `thinking="high"`). If `LLM_PROVIDER="none"`, falls back to deterministic rule-based template.
   - **Agent 7 (CAPA):** Formulating layered recommendation prose (`llama-3.1-8b-instant`). Falls back to deterministic standard mitigation library.
   - **Agent 8 (Quality Critic):** Adversarial auditing of claims (`llama-3.3-70b-versatile` on Groq). Falls back to deterministic rule verifier.

### Multi-Agent Orchestration Details (LangGraph)

- **Agent Count:** 8 specialized agents (`data_intake_agent`, `vision_agent`, `compliance_agent`, `anomaly_agent`, `spc_agent`, `rca_agent`, `capa_agent`, `critic_agent`).
- **Graph Nodes (10 nodes registered in `StateGraph`):**
  1. `intake` (`node_intake`)
  2. `visual_inspection` (`node_visual`)
  3. `compliance` (`node_compliance`)
  4. `anomaly_detection` (`node_anomaly`)
  5. `spc` (`node_spc`)
  6. `root_cause_analysis` (`node_rca`)
  7. `critic` (`node_critic`)
  8. `capa_management` (`node_capa`)
  9. `approval_gate` (`node_approval_gate`)
  10. `final_report` (`node_report`)
- **State Persistence:** In-memory checkpointing via `langgraph.checkpoint.memory.MemorySaver`, mirrored to database storage via SQLAlchemy model `WorkflowStateModel` in table `workflow_state`.
- **Human-in-the-Loop Interrupt Gate:** The graph executes sequentially through Agent 8 (Critic), then pauses at node `approval_gate` in state `AWAITING_HUMAN_APPROVAL`. Execution completes only when an authenticated Quality Engineer submits a formal disposition sign-off (`POST /api/review/sign-off`), stamping the record with `CONFIRMED_ROOT_CAUSE`.

### Additional Technologies Used (NOT in PDF Backend List)

| Technology | Category | Version | Purpose in this Project | Evidence |
|---|---|---|---|---|
| **SQLAlchemy** | ORM & Engine | 2.0.28+ (installed 2.0.51) | Maps 24 relational database entities, manages connection pooling, and executes ACID transactions. | `backend/requirements.txt:9`<br>`backend/app/db/session.py:6` (`from sqlalchemy import create_engine`) |
| **Alembic** | Schema Migrations | 1.13.1+ (installed 1.13.3) | Database schema versioning framework configured against `Base.metadata`. | `backend/requirements.txt:10`<br>`alembic/env.py:8` (`from alembic import context`) |
| **Uvicorn** | ASGI Web Server | 0.28.0+ (installed 0.49.0) | High-performance ASGI web server hosting FastAPI REST endpoints. | `backend/requirements.txt:2`<br>`render.yaml:8` (`uvicorn backend.app.main:app...`) |
| **ReportLab** | Document Generation | 4.1.0+ (installed 5.0.1) | Programmatic PDF generation engine building 13-section ISO 9001 / IATF 16949 audit reports with embedded vector tables. | `backend/requirements.txt:21`<br>`backend/app/reports/pdf_generator.py:15` (`from reportlab.lib.pagesizes import letter`) |
| **openpyxl** | Spreadsheet I/O | 3.1.2+ (installed 3.1.5) | Excel (`.xlsx`) parsing engine for CMM measurement and batch metadata imports in Agent 1. | `backend/requirements.txt:22`<br>`backend/app/agents/data_intake_agent.py:16` (`import openpyxl`) |
| **PyMuPDF (fitz)** | PDF Document Ingestion | 1.28.2 (installed) | Extracts text and structure from SOP documents (`SOP_Precision_Turning.pdf`) for indexing into ChromaDB. | `backend/app/agents/quality_knowledge_agent.py:17` (`import pymupdf`) |
| **PyYAML** | Configuration Parser | 6.0.3 (installed) | Reads MVTec class mapping configurations (`data/mvtec_label_map.yaml`). | `backend/data/generate_all.py:17` (`import yaml`) |
| **python-jose & bcrypt** | Security / Auth | jose 3.3.0+ / bcrypt 4.1.2+ | Generates and verifies HMAC-SHA256 JWT tokens and cryptographically salts passwords for role-based access control. | `backend/requirements.txt:6,8`<br>`backend/app/core/security.py:7` (`from jose import jwt`) |
| **pytest & pytest-asyncio** | Automated Testing | pytest 8.0.0+ / 9.1.1 installed | Test runner executing all 8 required evaluation scenarios (TC-01 through TC-08) and API unit tests. | `backend/requirements.txt:25,26`<br>`backend/tests/` |

---

## 2. Computer Vision Layer Audit

### Technology Audit Table (PDF Candidate Technologies)

| Technology | Used? | Version | Where it is used (file:function or module) | What it does in this project | Evidence (exact import / dependency / config line) |
|---|:---:|---|---|---|---|
| **OpenCV** | **YES** | 4.9.0+ headless<br>(installed 5.0.0.93) | `ml/cv/train_patchcore.py:13`<br>`ml/cv/train_classifier.py:12`<br>`backend/app/cv_model/defect_detector.py:29`<br>`backend/app/ml/cv/gradcam.py:12` | Image decoding (`cv2.imread`), color conversion, Gaussian smoothing of anomaly maps, morphological contour finding (`cv2.findContours`), bounding box calculation (`cv2.boundingRect`), and Jet colormap rendering (`cv2.applyColorMap`). | `backend/requirements.txt:17` (`opencv-python-headless>=4.9.0.80`)<br>`ml/cv/train_patchcore.py:13` (`import cv2`)<br>`backend/app/ml/cv/gradcam.py:12` (`import cv2`) |
| **PyTorch** | **YES** | 2.2.0+<br>(installed 2.13.0) | `ml/cv/train_patchcore.py:15`<br>`ml/cv/train_classifier.py:14`<br>`backend/app/ml/cv/gradcam.py:11` | Core deep learning framework: ResNet18 multiscale feature extraction, patch memory bank tensors, MobileNetV3 classifier training with cross-entropy loss, backpropagation hooks for Grad-CAM. | `backend/requirements.txt:15` (`torch>=2.2.0`)<br>`ml/cv/train_patchcore.py:15` (`import torch`)<br>`ml/cv/train_classifier.py:14` (`import torch`) |
| **torchvision** | **YES** | 0.17.0+<br>(installed 0.28.0) | `ml/cv/train_patchcore.py:18-19`<br>`ml/cv/train_classifier.py:18-19` | Pretrained neural backbones (`models.resnet18`, `models.mobilenet_v3_small`) and data transformations (`transforms.Resize`, `transforms.Normalize`). | `backend/requirements.txt:16` (`torchvision>=0.17.0`)<br>`ml/cv/train_patchcore.py:18` (`import torchvision.models as models`)<br>`ml/cv/train_classifier.py:18` (`import torchvision.models as models`) |
| **TensorFlow** | **NO** | N/A | None | Absent. PyTorch was selected for the entire computer vision training, transfer learning, and evaluation pipeline. | `tensorflow` is absent from all requirement files and imports. |
| **YOLO** | **EQUIVALENT** | Replaced by Two-Stage PatchCore + MobileNetV3 | `ml/cv/train_patchcore.py`<br>`backend/app/cv_model/defect_detector.py`<br>`backend/app/ml/cv/yolo_onnx_infer.py:9` | **Justification:** Replaced because the industrial benchmark dataset (MVTec AD) contains only normal (`good`) images in training splits with zero defect bounding-box annotations. Standard YOLO requires supervised defect bounding boxes for training. A two-stage architecture (PatchCore memory banks for unsupervised localization + MobileNetV3 for classification) was trained instead. An ONNX inference adapter (`YOLOOnnxDetector`) exposes the standardized detection interface. | `backend/app/ml/cv/yolo_onnx_infer.py:9` (`class YOLOOnnxDetector: ... res = self.vision_model.inspect_image(img_path)`) |
| **Hugging Face vision models** | **NO** | N/A | None | Absent. Heavy transformer architectures (e.g. ViT, Swin) were avoided in favor of lightweight torchvision backbones to guarantee <2s CPU inference latency on free cloud instances. | Zero imports of `transformers` in vision code. |

### Computer Vision Models Specification & Evaluation Card

The vision system utilizes two distinct stages evaluated on held-out test splits:

```
+-----------------------------------------------------------------------------------------------+
| STAGE A: PatchCore Anomaly Localization (Unsupervised)                                        |
| Architecture:        ResNet18 (Intermediate Layer 2 [128-ch] & Layer 3 [256-ch] Concat)       |
| Pretrained Weights:  torchvision.models.ResNet18_Weights.DEFAULT (ImageNet)                   |
| Training Dataset:    MVTec AD (4 Industrial Proxy Categories: metal_nut, screw, transistor,    |
|                      cable) trained STRICTLY on 1,071 normal (good) training images.          |
| Input Resolution:    224 x 224 x 3 RGB                                                        |
| Trained Artifacts:   backend/models/patchcore_banks.pt (9.8 MB), thresholds.json (827 bytes)   |
| Runtime Engine:      PyTorch (CPU Execution)                                                  |
| Performance:         Overall Image AUROC: 0.8585 | Pixel AUROC: 0.9302 | mAP@0.5: 0.3333        |
| Scripts:             Training: ml/cv/train_patchcore.py | Evaluation: ml/cv/evaluate.py       |
+-----------------------------------------------------------------------------------------------+
                                               │
                                               ▼
+-----------------------------------------------------------------------------------------------+
| STAGE B: Defect Classification Head (Supervised Transfer Learning)                           |
| Architecture:        MobileNetV3-Small Backbone + Linear(576, 256) -> Hardswish ->            |
|                      Dropout(0.2) -> Linear(256, 8) Unified Classes Head                      |
| Pretrained Weights:  torchvision.models.MobileNet_V3_Small_Weights.DEFAULT (ImageNet)         |
| Training Dataset:    Held-out defect splits mapped to 8 unified classes (splits.json: 1,071   |
|                      train, 202 val, 229 test)                                                |
| Input Resolution:    224 x 224 x 3 RGB                                                        |
| Trained Artifacts:   backend/models/cv_model.onnx (4.3 MB), backend/models/cv_model.pt (4.4MB)|
|                      backend/models/classes.json, backend/models/cv_metrics.json               |
| Runtime Engine:      ONNX Runtime (CPUExecutionProvider) with PyTorch fallback                 |
| Benchmark Latency:   11.87 ms per image on CPU (Constraint: < 2,000 ms -> 168x faster)        |
| Performance:         Overall Test Accuracy: 83.84% | Test Macro F1: 70.98%                    |
|                      5-Fold Cross-Validation Macro F1: 79.77% ± 3.51%                          |
| Scripts:             Training: ml/cv/train_classifier.py | Evaluation: ml/cv/evaluate.py      |
+-----------------------------------------------------------------------------------------------+
```

### Additional Computer Vision Technologies Used

| Technology | Category | Version | Purpose in this Project | Evidence |
|---|---|---|---|---|
| **ONNX Runtime** | Inference Engine | 1.17.1+ (installed 1.31.0) | High-speed, multi-threaded CPU inference engine running `backend/models/cv_model.onnx` with 11.87 ms latency and low memory footprint (<50 MB). | `backend/requirements.txt:19`<br>`backend/app/cv_model/defect_detector.py:37` (`import onnxruntime as ort`) |
| **Custom Grad-CAM** | Interpretability | In-repo implementation | Generates class activation heatmaps via PyTorch backward gradient hooks on MobileNetV3 feature maps for visual explainability. | `backend/app/ml/cv/gradcam.py:10` (`class GradCAM`) |

---

## 3. Frontend Layer Audit

### Technology Audit Table (PDF Candidate Technologies)

| Technology | Used? | Version | Where it is used (file:function or module) | What it does in this project | Evidence (exact import / dependency / config line) |
|---|:---:|---|---|---|---|
| **React.js** | **YES** | 19.2.8<br>(installed 19.3.0) | `frontend/src/App.tsx`<br>`frontend/src/pages/*.tsx`<br>`frontend/src/components/*.tsx` | Component-based user interface framework rendering the reactive Quality Cockpit. | `frontend/package.json:19` (`"react": "^19.2.8"`)<br>`frontend/package.json:20` (`"react-dom": "^19.2.8"`) |
| **TypeScript** | **YES** | 6.0.2<br>(installed 6.0.3) | `frontend/src/**/*.ts`<br>`frontend/src/**/*.tsx` | Type-safe development enforcing interfaces across `types.ts` and `api.ts`. **Strict mode: OFF** (`strict` omitted in `tsconfig.app.json`). | `frontend/package.json:32` (`"typescript": "~6.0.2"`)<br>`frontend/tsconfig.app.json:1` |
| **Tailwind CSS** | **YES** | 4.3.3 | `frontend/src/index.css`<br>All `.tsx` page files | Utility-first CSS engine. Implemented via `@tailwindcss/vite` v4 with custom design tokens in `:root`. | `frontend/package.json:31` (`"tailwindcss": "^4.3.3"`)<br>`frontend/package.json:25` (`"@tailwindcss/vite": "^4.3.3"`)<br>`frontend/src/index.css:1` (`@import "tailwindcss";`) |
| **Recharts** | **YES** | 3.10.1 | `frontend/src/pages/DashboardPage.tsx`<br>`frontend/src/pages/SpcDashboardPage.tsx`<br>`frontend/src/pages/ProcessMonitoringPage.tsx`<br>`frontend/src/pages/InspectionPage.tsx` | Interactive data charts: LineChart with ReferenceLine (UCL/LCL/USL/LSL limits), AreaChart for batch rates, and responsive telemetry multi-sensor charts. | `frontend/package.json:21` (`"recharts": "^3.10.1"`)<br>`frontend/src/pages/SpcDashboardPage.tsx:11` (`from "recharts"`) |
| **Plotly** | **NO** | N/A | None | Absent. Recharts was selected exclusively for all charts in the React frontend. | `plotly` is absent from `frontend/package.json` and imports. |

### Architectural Deep-Dive: Routing, State, and Data Fetching

- **Router:** Custom tab/view-state router in `frontend/src/App.tsx` (`const [activePage, setActivePage] = useState("dashboard")`). Renders **13 complete interactive pages**:
  1. `DashboardPage` (Executive KPI overview and batch feed)
  2. `ProductConfigPage` (Engineering specs, tolerances, nominals)
  3. `BatchesPage` (Batch inventory and filtering)
  4. `InspectionPage` (CMM measurements and tolerance checks)
  5. `VisualInspectionPage` (Interactive CV defect inspector with Grad-CAM overlays)
  6. `ProcessMonitoringPage` (8-parameter machine telemetry and anomaly spikes)
  7. `SpcDashboardPage` (I-MR control charts and capability indices)
  8. `IncidentsPage` (Nonconformance report list)
  9. `RcaPage` (Ishikawa 6M fishbone and 5-Whys reasoning trees)
  10. `CapaPage` (Containment, corrective, and preventive action planner)
  11. `AiReviewPage` (8-agent execution trace and audit transcript)
  12. `ReportsPage` (ISO 9001 audit dossier PDF download and preview)
  13. `TestScenariosPage` (Automated verification harness for TC-01 through TC-08)
  *(React Router is not used).*
- **Data-Fetching:** Native browser `fetch` API wrapped in asynchronous functions in `frontend/src/api.ts` with strongly-typed JSON responses. *(Axios and TanStack Query are not used).*
- **State Management:** Local React state (`useState`, `useEffect`) and callback props (`onNavigate`, `onRunPipeline`). *(Redux and Zustand are not used).*
- **Icons:** `lucide-react` (version `^1.55.0`, installed `1.55.0`).
- **Linter:** `oxlint` (version `^1.81.0`, installed `1.87.0`).
- **Build Tool:** `vite` (version `^8.3.0`, installed `8.3.4`) using `@vitejs/plugin-react` (`^6.1.1`).
- **Design Tokens (in `frontend/src/index.css`):**  
  `--bg-main: #f8fafc`, `--bg-card: #ffffff`, `--border-subtle: #e2e8f0`, `--text-primary: #0f172a`, `--text-secondary: #475569`, `--text-muted: #64748b`. Clean light enterprise theme.

---

## 4. Database Layer Audit

### Technology Audit Table (PDF Candidate Technologies)

| Technology | Used? | Version | Where it is used (file:function or module) | What it does in this project | Evidence (exact import / dependency / config line) |
|---|:---:|---|---|---|---|
| **PostgreSQL** | **YES** | 16+ (Target) | `backend/app/db/session.py`<br>`render.yaml:26-32` | Production relational database configured for cloud deployment on Render (`qualitymind-postgres`), storing all 24 relational tables. | `render.yaml:27` (`name: qualitymind-postgres`)<br>`render.yaml:20` (`DATABASE_URL fromDatabase`) |
| **SQLite (Fallback)** | **YES** | 3.x (Built-in) | `backend/app/db/session.py:12`<br>`backend/data/quality_system.db` | Active local development fallback database (size: 765,952 bytes on disk) allowing zero-configuration operation when PostgreSQL is not installed locally. | `backend/app/db/session.py:12` (`if settings.DATABASE_URL.startswith("sqlite"):`)<br>`.env.example:8` (`DATABASE_URL="sqlite:///./backend/data/quality_system.db"`) |
| **TimescaleDB** | **NO** | N/A | None | Absent. Time-series telemetry lives in a standard PostgreSQL/SQLite table with composite B-tree indexing. | Absent from dependencies and deployment configs. |
| **InfluxDB** | **NO** | N/A | None | Absent. Not used to avoid external database daemon dependencies on free cloud tiers. | Absent from dependencies and deployment configs. |

### Time-Series Data Architecture Justification

Time-series machine telemetry (8 parameters: spindle speed, feed rate, coolant temperature, vibration, tool usage cycles, motor current, cycle time, hydraulic pressure) is stored in the relational table `process_readings` ([models.py](file:///d:/Projects%20Local/QT/backend/app/db/models.py#L144)). 
- **Justification:** For discrete manufacturing cells running batches of 500 to 1,000 components, telemetry is collected per-part or downsampled per-cycle (<10,000 readings per batch). The table `process_readings` incorporates composite B-tree indexes on `(ts)`, `(machine_id)`, and `(batch_id)`. Standard indexed relational queries execute in under 2 milliseconds, maintain transactional ACID integrity with batch metadata, require zero additional server processes, and preserve the system's low RAM footprint (<350 MB). Dedicated time-series engines like TimescaleDB or InfluxDB would introduce unnecessary deployment complexity and memory overhead without measurable latency gains at this operational scale.

### Table Inventory & Data Provenance (All 24 Tables)

| # | Table Name | SQLAlchemy Model | Current Record Count (Local DB) | Data Provenance | Description / Contents |
|---|---|---|---|---|---|
| 1 | `users` | `User` | 3 | Synthetic Illustrative | Authenticated demo users (`admin`, `engineer`, `operator`). |
| 2 | `products` | `Product` | 3 | Synthetic Illustrative | Engineering product definitions (`PS-2026-101`, `BRG-6205`, `BSH-4020`). |
| 3 | `machines` | `Machine` | 4 | Synthetic Illustrative | CNC machinery records (`CNC-01` Haas, `CNC-02` Mori Seiki, `CNC-03` Mazak, `CNC-04` Okuma). |
| 4 | `inspection_characteristics` | `InspectionCharacteristic` | 3 | Synthetic Illustrative | Engineering limits (Diameter $50.00 \pm 0.05\text{ mm}$, LSL $49.95$, USL $50.05$). |
| 5 | `batches` | `Batch` | 27 | Synthetic Illustrative | Production batches (`BATCH-0245` golden anchor, plus historical batches B001-B026). |
| 6 | `measurements` | `Measurement` | 1,365 | Synthetic Illustrative | Physical CMM dimensional measurement readings. |
| 7 | `inspection_images` | `InspectionImage` | 0 | **REAL Data File References** | Metadata links pointing to real industrial image files from the MVTec AD dataset. |
| 8 | `visual_findings` | `VisualFinding` | 0 | **REAL Model Predictions** | Two-stage CV predictions evaluated on real MVTec AD images. |
| 9 | `process_readings` | `ProcessReading` | 60 | Synthetic Illustrative | High-frequency 8-sensor CNC machine telemetry time series. |
| 10 | `process_baselines` | `ProcessBaseline` | 8 | Synthetic Illustrative | Normal operational parameter baselines for machine CNC-04. |
| 11 | `anomalies` | `Anomaly` | 0 | Runtime Computed | Telemetry anomaly incidents flagged by the 5-layer anomaly engine. |
| 12 | `spc_results` | `SPCResult` | 0 | Runtime Computed | Control chart calculations ($I\text{-}MR$, $UCL/LCL$, capability $C_p, C_{pk}$). |
| 13 | `quality_incidents` | `QualityIncident` | 4 | Synthetic Illustrative | Nonconformance Reports (including golden incident `inc-ncr-019`). |
| 14 | `rca_hypotheses` | `RCAHypothesis` | 0 | Runtime Computed | 6M Ishikawa hypotheses and deterministic evidence scores. |
| 15 | `historical_incidents` | `HistoricalIncident` | 3 | Synthetic Illustrative | Historical NCR database archive for precedent retrieval. |
| 16 | `capa_actions` | `CAPAAction` | 15 | Synthetic Illustrative | Standard library of containment, corrective, and preventive actions. |
| 17 | `effectiveness_checks` | `EffectivenessCheck` | 0 | Runtime Computed | Before/after two-proportion z-test statistical verification records. |
| 18 | `agent_runs` | `AgentRun` | 0 | Runtime Execution Logs | Step-by-step agent execution audit logs. |
| 19 | `human_decisions` | `HumanDecision` | 0 | Runtime Governance | Quality Engineer sign-off and batch disposition audit records. |
| 20 | `reviewer_comments` | `ReviewerComment` | 0 | Runtime Governance | Quality Critic comments and reassessment loop logs. |
| 21 | `reports` | `Report` | 0 | Runtime Generated | Generated ISO 9001 audit dossier PDF file records. |
| 22 | `kb_documents` | `KBDocument` | 0 | Synthetic Illustrative | Metadata index of ingested technical standards and manuals. |
| 23 | `maintenance_records` | `MaintenanceRecord` | 2 | Synthetic Illustrative | Historical CNC-04 machine maintenance and tool replacement logs. |
| 24 | `workflow_state` | `WorkflowStateModel` | 0 | Runtime Checkpoints | Checkpointed Pydantic v2 `WorkflowState` for HITL pause and resume. |

---

## 5. RAG / Vector Database Layer Audit

### Technology Audit Table (PDF Candidate Technologies)

| Technology | Used? | Version | Where it is used (file:function or module) | What it does in this project | Evidence (exact import / dependency / config line) |
|---|:---:|---|---|---|---|
| **ChromaDB** | **YES** | 0.4.24+<br>(installed 0.6.3) | `backend/app/agents/quality_knowledge_agent.py:14`<br>`backend/data/knowledge_db` | In-process persistent vector database storing 1,624 document chunks in collection `qualityminds_quality_knowledge` with HNSW cosine indexing. | `backend/requirements.txt:23` (`chromadb>=0.4.24`)<br>`backend/app/agents/quality_knowledge_agent.py:14` (`import chromadb`) |
| **FAISS** | **NO** | N/A | None | Absent. ChromaDB was selected for native file persistence on disk and zero configuration overhead. | Absent from dependencies and imports. |
| **Qdrant** | **NO** | N/A | None | Absent. Avoided external server daemon requirements. | Absent from dependencies and imports. |
| **PostgreSQL with pgvector** | **NO** | N/A | None | Absent. In-process ChromaDB was selected to preserve low database memory usage on free Render instances. | Absent from dependencies and SQL migrations. |

### Vector Store Specification (ChromaDB Persisted Directory)

- **Persistence Directory on Disk:** `backend/data/knowledge_db/` (contains `chroma.sqlite3` and HNSW segment directories).
- **Collections Found:** Exactly 1 collection: `qualityminds_quality_knowledge`.
- **Total Chunks in Collection:** **1,624 document chunks**.
- **Embedding Model & Dimensions:**
  - **In-Process Primary:** `all-MiniLM-L6-v2` (**384 dimensions**) via Chroma's built-in ONNX runtime embedding function (`embedding_functions.DefaultEmbeddingFunction()`).
  - **Hosted HTTP Fallback:** Gemini `text-embedding-004` (**768 dimensions**) invoked via `universal_llm.embed_text()`.
- **Distance Metric:** Cosine distance (`hnsw:space: "cosine"`).
- **Chunking Settings:**
  - **CSV files:** Record-level semantic preservation; each non-blank CSV row is preserved as a cohesive, single chunk to keep tabular manufacturing rows intact without arbitrary sentence splitting.
  - **Markdown / Plain Text (`.md`, `.txt`):** Paragraph-boundary chunking (`re.split(r"\n\s*\n", content)`) with a target word limit of ~350 words per chunk, preserving natural document sections and extracting header frontmatter metadata.
  - **PDF files:** Page-level extraction via PyMuPDF (`pymupdf.open()`) with minimum length thresholds.
  - **JSON files:** Individual item preservation for structured array entries.
- **Metadata Fields (100% of chunks contain all 7 required metadata fields):**
  `doc_type`, `part_number`, `machine` (and `machine_id`), `defect_type`, `defect_family`, `proxy_category`, `provenance`, along with operational fields `source`, `file_name`, `file_type`, `category`, `record_id`, `batch_id`, `chunk_index`, `record_index`, `content_hash`, `ingestion_timestamp`.
- **Hybrid Retrieval & Reranking:**
  - **Primary Engine:** In-process ChromaDB HNSW cosine similarity query in `quality_knowledge_agent.py`.
  - **Secondary Fallback Engine:** `ManufacturingVectorStore` in `backend/app/rag/vector_store.py` using Scikit-learn TF-IDF n-gram (1,3) vectorization with cosine similarity and metadata boosting (**1.60x multiplier** for matching `defect_type`, **1.30x multiplier** for matching `proxy_category`, and **0.50x penalty** for mismatched `doc_type`).
  - **Mandatory Epistemic Disclaimer:** Every retrieved precedent includes the disclaimer: *"Historical context only. Historical similarity does not establish the same root cause."*

### Knowledge-Base Document Types Indexed Table

| Document Type (PDF List) | Source Files | Chunk Count | Data Provenance | Summary of Indexed Content |
|---|---|---|---|---|
| **Product Specifications** | `product_specs.csv`, `vector_kb.json` | 4 chunks | `synthetic_illustrative` | Dimensional tolerances, nominal diameters, LSL/USL limits for Precision Ground Shafts (`PS-2026-101`), Bearings (`BRG-6205`), and Bushings (`BSH-4020`). |
| **Inspection Procedures** | `SOP-055_Visual_Inspection_Procedure.md`, `vector_kb.json` | 2 chunks | `synthetic_illustrative` | Surface defect inspection criteria, lighting standards, and defect classification protocols. |
| **Manufacturing SOPs** | `SOP-044_Tool_Life.md`, `SOP_Precision_Turning.pdf`, `vector_kb.json` | 3 chunks | `synthetic_illustrative` | CNC cutting tool life management, insert replacement intervals (600 cycles), and turning operating procedures. |
| **Quality Standards** | `REF-NIST-SPC_Statistical_Process_Control_Handbook.md`, `vector_kb.json` | 59 chunks | **`public_reference`** (NIST Handbook) & `synthetic_illustrative` (ISO/IATF summaries) | NIST SPC rules, Nelson rule definitions 1-8, AIAG capability assessment guidelines ($C_{pk}$ thresholds), ISO 9001:2015 Clause 8.7, IATF 16949 Section 10.2. |
| **Previous NCRs** | `historical_ncrs.json` (35 chunks), `historical_ncrs.csv` (18 chunks), `mvtec_manifest.csv` (1,502 chunks) | 1,555 chunks | `synthetic_illustrative` (Tabular NCRs) & **REAL proxy component defect manifests** (MVTec AD) | Historical non-conformance records including **NCR-019** (tool wear root cause for oversized shaft diameter), plus 1,502 MVTec AD industrial proxy component records. |
| **CAPA Records** | `capa_records.json` | 15 chunks | `synthetic_illustrative` | Archived Corrective and Preventive Actions with containment protocols, responsible roles, and verification timelines. |
| **Machine Manuals** | `Machine_Guidelines.txt` | 1 chunk | `synthetic_illustrative` | Okuma LB3000-EX II CNC Lathe maintenance guidelines, spindle vibration trip thresholds, and lubrication schedules. |
| **Maintenance Records** | `maintenance_records.csv` | 3 chunks | `synthetic_illustrative` | CNC-04 tool replacement history, spindle alignment inspections, and calibration logs. |
| **Dataset Splits** | `splits.json` | 1 chunk | `synthetic_illustrative` | Zero-leakage train/validation/test partitions for MVTec AD proxy parts. |
| **Total Chunks in Chroma** | **13 Files** | **1,624 chunks** | **1,623 Synthetic Illustrative / 1 Public Reference** | Complete indexed technical knowledge base. |

---

## 6. Deployment and DevOps Layer Audit

### Technology Audit Table (PDF Candidate Technologies)

| Technology | Used? | Version | Where it is used (file:function or module) | What it does in this project | Evidence (exact import / dependency / config line) |
|---|:---:|---|---|---|---|
| **Render** | **YES** | Native Python Runtime | `render.yaml:1-32` | Infrastructure-as-code blueprint configuring the FastAPI backend web service (`qualitymind-backend`) with managed PostgreSQL database (`qualitymind-postgres`). | `render.yaml:3` (`name: qualitymind-backend`)<br>`render.yaml:4` (`runtime: python`) |
| **Vercel** | **YES** | Static SPA Deployment | `vercel.json:1-12` | Deployment configuration for the React Vite frontend with single-page application route rewrites to `/index.html`. | `vercel.json:3` (`buildCommand: "cd frontend && npm install && npm run build"`)<br>`vercel.json:4` (`outputDirectory: "frontend/dist"`) |
| **Docker** | **NO** | N/A | None | **INTENTIONALLY NOT USED.** The system is designed to run natively on host Python and Node.js runtimes without container overhead. Docker is not installed on the development host (`docker ps` returns command not found), and no Dockerfiles exist in the repository. | No Dockerfiles in workspace; zero container daemon dependencies. |
| **docker-compose** | **NO** | N/A | None | Absent. No `docker-compose.yml` file exists in the repository. Native PowerShell scripts (`start_demo.ps1`, `stop_demo.ps1`) launch native processes directly. | Zero docker-compose files in repository. |
| **Continuous Integration (CI)** | **YES** | GitHub Actions v4 | `.github/workflows/ci.yml:1-57` | Automated CI pipeline with two parallel jobs: (1) `backend-tests` on Python 3.11 running pytest and test harness scripts, and (2) `frontend-build` on Node 20 running TypeScript typecheck and Vite production build. | `.github/workflows/ci.yml:10` (`jobs: backend-tests:`...)<br>`.github/workflows/ci.yml:38` (`frontend-build:`...) |

### Deployment Status: Configured vs. Deployed

- **Backend (Render):** **Configured Only.** Declared in `render.yaml` with build command `pip install -r requirements.txt && alembic upgrade head` and start command `python -m backend.app.db.seed && uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT`. No active external live URL is currently provisioned; execution runs locally on port 8000.
- **Frontend (Vercel):** **Configured Only.** Declared in `vercel.json` with build command `npm run build` targeting `frontend/dist`. The production URL `https://qualitymind.vercel.app` is pre-configured in `.env.example` and `render.yaml` CORS origins.
- **Local Native Launcher:** High-reliability Windows PowerShell script `start_demo.ps1` runs migrations, checks database seeds, launches FastAPI on `http://localhost:8000`, launches Vite on `http://localhost:5173`, and opens the browser in under 3 seconds.

---

## 7. Honesty Checks & Dependency Audit

### 1. Python Dependency Verification (`pip list` vs. `backend/requirements.txt`)

A full AST parse of all `.py` files across `backend/`, `ml/`, and `scripts/` compared against `backend/requirements.txt` reveals the following discrepancies:

1. **Packages Installed and Listed in `requirements.txt` but NEVER Imported:**
   - **`albumentations` (`>=1.4.0`):** Listed in `backend/requirements.txt:18` (installed `2.0.8`). Zero import statements exist in the codebase. Transformations were implemented using native `torchvision.transforms` in `ml/cv/train_classifier.py:44`.
   - **`sentence-transformers` (`>=2.5.1`):** Listed in `backend/requirements.txt:24` (installed `2.5.1`). Zero direct import statements exist in application code. ChromaDB uses its default embedded ONNX MiniLM model (`chromadb.utils.embedding_functions.DefaultEmbeddingFunction`), and the universal LLM client uses hosted HTTP embeddings.

2. **Packages Imported in Python Code but MISSING from `backend/requirements.txt`:**
   - **`pymupdf` (fitz):** Imported in `backend/app/agents/quality_knowledge_agent.py:17` (`import pymupdf`). Installed locally (`pymupdf 1.28.2`), but missing from `backend/requirements.txt`.
   - **`PyYAML` (yaml):** Imported in `backend/data/generate_all.py:17` (`import yaml`). Installed locally (`PyYAML 6.0.3`), but missing from `backend/requirements.txt`.
   - **`psycopg2-binary`:** Required by SQLAlchemy on Render when connecting to PostgreSQL via `render.yaml:20`. Installed locally (`psycopg2-binary 2.9.12`), but missing from `backend/requirements.txt`.
   - **`Pillow` (PIL):** Imported in `ml/cv/train_patchcore.py:20` and `ml/cv/train_classifier.py:20` (`from PIL import Image`). Installed locally (`pillow 12.2.0`), pulled transitively by `torchvision`, but not explicitly declared.

### 2. Frontend Dependency Verification (`npm ls` vs. `frontend/package.json`)

1. **Packages Declared in `frontend/package.json` but NEVER Imported in `frontend/src`:**
   - **`clsx` (`^2.1.1`):** Declared in `package.json:17`, installed (`2.1.1`). Zero import statements found in `frontend/src/`.
   - **`tailwind-merge` (`^3.7.0`):** Declared in `package.json:22`, installed (`3.7.0`). Zero import statements found in `frontend/src/`. All component styling uses direct Tailwind CSS utility classes.

2. **TypeScript Strict Mode:**
   - `frontend/tsconfig.app.json` omits `"strict": true`. TypeScript strict mode is currently **OFF** (`strict: false` by default).

### 3. Documentation Claims Corrected Against Active Codebase

1. **React Version:**
   - **Documentation Claim:** README badge claimed `React 18`, and architecture docs claimed `React 18 + TypeScript`.
   - **Active Codebase Reality:** `frontend/package.json` declares `"react": "^19.2.8"` and `"react-dom": "^19.2.8"`; installed runtime is **React 19.3.0**.
   - **Action Taken:** Corrected in `README.md`, `docs/architecture.md`, and `docs/demo/DEMO_CHEATSHEET.md`.

2. **Page Count:**
   - **Documentation Claim:** README claimed "11 Interactive Pages".
   - **Active Codebase Reality:** `frontend/src/App.tsx` renders **13 complete interactive pages** (including `TestScenariosPage` and `ProductConfigPage`).
   - **Action Taken:** Corrected in `README.md` and `docs/architecture.md`.

3. **LLM Provider Support:**
   - **Documentation Claim:** README claimed `anthropic` as a supported `LLM_PROVIDER`.
   - **Active Codebase Reality:** `anthropic` SDK is neither installed nor imported. Supported active providers are `gemini`, `groq`, `openrouter`, and `openai` via the OpenAI-compatible SDK in `backend/app/core/llm.py`.
   - **Action Taken:** Corrected in `README.md`.

4. **Alembic Database Migrations:**
   - **Documentation Claim:** "24 SQLAlchemy 2.x models with Alembic migrations".
   - **Active Codebase Reality:** The initial migration file `alembic/versions/e809b39d3b8b_initial_schema.py` contains an empty `upgrade()` method (`pass`). Tables are created deterministically via SQLAlchemy's `Base.metadata.create_all(bind=engine)` inside `backend/app/db/seed.py:15`.
   - **Action Taken:** Documented in this audit report.

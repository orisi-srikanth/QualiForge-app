# QualityMind Live Technical Demo Cheat Sheet

---

## 1. Quick URLs & Port Allocation
| Service | URL / Location | Port | Role |
| :--- | :--- | :--- | :--- |
| **Frontend UI** | [http://localhost:5173](http://localhost:5173) | `5173` | React 19 + TypeScript Quality Cockpit |
| **Backend REST API** | [http://localhost:8000](http://localhost:8000) | `8000` | FastAPI Multi-Agent Engine |
| **Swagger UI Docs** | [http://localhost:8000/docs](http://localhost:8000/docs) | `8000` | Interactive OpenAPI Documentation |
| **ReDoc UI Docs** | [http://localhost:8000/redoc](http://localhost:8000/redoc) | `8000` | Formal API Specification |
| **Health Probe** | [http://localhost:8000/health](http://localhost:8000/health) | `8000` | Container-free Liveness Check |
| **Database** | `sqlite:///./backend/data/quality_system.db` | N/A (or `5432` Postgres) | 17 Relational Tables / 1,365 Measurements |
| **Vector Store** | `backend/data/knowledge_db` | In-process | ChromaDB (1,624 Chunks) |

---

## 2. Demo Personas & Credentials
| Role | Email | Password | Permissions |
| :--- | :--- | :--- | :--- |
| **Quality Engineer** *(Recommended)* | `engineer@precisionaero.com` | `Engineer123!` | Review findings, confirm root cause, approve CAPAs, sign off batches |
| **Admin** | `admin@precisionaero.com` | `Admin123!` | System configuration, database migrations, full administrative access |
| **Operator** | `operator@precisionaero.com` | `Operator123!` | Data intake, telemetry monitoring, view-only (RBAC blocks approvals with 403) |

---

## 3. Launch & Control Commands (PowerShell)
```powershell
# Start everything in one command (opens UI, Swagger, ReDoc):
.\start_demo.ps1

# Stop everything cleanly:
.\stop_demo.ps1

# Inspect Database without containers (tables, counts, anchor batch):
python scripts/show_db.py --summary

# Inspect ChromaDB Vector Knowledge Base & run test queries:
python scripts/show_vector_store.py --stats

# Run the 100% compliant master audit suite (7 verifiers, 83 tests):
python scripts/audit/run_all_audit.py
```

---

## 4. Recommended Demo Order of Screens
1. **Frontend App (`http://localhost:5173`)**:
   - Log in as `engineer@precisionaero.com`.
   - **Quality Dashboard**: Show overall health (87.4%), active incidents, and Pareto defect distribution.
   - **Dimensional Inspection**: Show `BATCH-0245` with 3 nonconforming parts (`P003`, `P004`, `P005`) exceeding USL (`50.05 mm`) with `[OBSERVED FACT]` labels.
   - **Computer Vision**: Show real MVTec `metal_nut` scratch detection with bounding box (`[MODEL PREDICTION]`, model version `mvtec-two-stage-v1.0`).
   - **Process Monitoring**: Point out CNC-04 vibration spike (3.84 mm/s) and tool cycle counter (1,150 cycles, +91% overdue) vs. normal spindle/feed rates.
   - **SPC & Capability**: Show I-MR chart, Nelson rule trips, and sample-size guardrail warning for $n=5 < 30$.
   - **Agent Orchestrator**: Run pipeline, watch it pause at the `PENDING_HUMAN_APPROVAL` gate.
   - **Engineering Sign-Off**: Submit human sign-off as Sarah Chen, elevating the hypothesis to `[CONFIRMED ROOT CAUSE]`.
   - **Download Audit PDF**: Download the 12-section IATF 16949 / ISO 9001 Audit Dossier.
2. **Swagger UI (`http://localhost:8000/docs`)**:
   - Demonstrate the 17 tag groups, click **Authorize** with JWT token, and show RBAC gate (operator gets 403 on `/api/review/sign-off`).
3. **Database Inspector**:
   - Run `python scripts/show_db.py --summary` in terminal (or DBeaver with `docs/demo/db_queries.sql`).
4. **Vector Store Inspector**:
   - Run `python scripts/show_vector_store.py --stats` to demonstrate in-process semantic search returning `NCR-019`.

---

## 5. Troubleshooting: "If Something Breaks"
| Issue | Immediate Fix Command |
| :--- | :--- |
| **Port 8000 or 5173 busy** | `.\stop_demo.ps1` (or `Get-NetTCPConnection -LocalPort 8000,5173 -State Listen \| Stop-Process -Id {$_.OwningProcess} -Force`) |
| **Backend not starting** | Verify Python path: `python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000` |
| **Database missing or empty** | `python -m alembic upgrade head` then `python -m backend.app.db.seed` |
| **Model loading error** | Ensure models directory exists: `python -c "from backend.app.agents.vision_agent import vision_agent"` |
| **CORS error on frontend** | Verify `.env` has `CORS_ORIGINS=["http://localhost:5173","http://127.0.0.1:5173"]` and restart backend |
| **Blank frontend screen** | Clear Vite cache and rebuild: `cd frontend; npm run build; npm run dev` |

---

## 6. The 5 Key Architectural Pillars to Emphasize
1. **Decision-Support Guarantee**: Compliant with ISO 9001 & IATF 16949; AI never executes autonomous physical actions or overrides certified engineers.
2. **100% Deterministic Math**: All tolerance checks, deviations, SPC limits, and z-scores run via deterministic Python engines. Zero LLM calculation hallucinations.
3. **5 Mandatory Epistemic Labels**: `[OBSERVED FACT]`, `[MODEL PREDICTION]`, `[STATISTICAL FINDING]`, `[HYPOTHESIS]`, and `[CONFIRMED ROOT CAUSE]` strictly prevent unfounded causal claims.
4. **Real MVTec AD Dataset**: Trained exclusively on real manufacturing anomaly benchmarks (`metal_nut`, `screw`, `transistor`, `cable`). Zero synthetic images.
5. **Native Zero-Container Simplicity**: Sub-second startup, in-process ChromaDB, ~337 MB RAM footprint, ready to deploy natively to Render and Vercel.

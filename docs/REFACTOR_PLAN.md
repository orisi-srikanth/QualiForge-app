# QualityMind Refactor & Hygiene Plan

This document details the refactoring, file renaming, and architectural hygiene plan for the QualityMind discrete manufacturing quality decision-support platform.

**Core Principles:**
1. **Zero Behavioral Change:** Public API contracts, database schemas, model outputs, and React UI workflows remain 100% identical.
2. **Obvious & Flat Naming:** Eliminate numeric prefixes (`a1_`, `a2_`), vague titles, and god files. File names reflect single, clear responsibilities.
3. **Preserved History:** All renames use `git mv`.
4. **Backward Compatibility:** Deprecated import paths are shimmed or cleanly updated across tests, scripts, and documentation.

---

## 1. File & Directory Renaming Map

| Current Path | Target Path | Rationale |
|---|---|---|
| `backend/app/core/config.py` | `backend/app/config.py` | Top-level application settings directly accessible per target structure (re-exported in `core/config.py` for compatibility). |
| `backend/app/db/` | `backend/app/database/` | Standard, intuitive noun naming for persistence tier (`connection.py`, `models.py`, `seed.py`). |
| `backend/app/models/schemas.py` | `backend/app/schemas/schemas.py` | Clean separation between Pydantic API schemas and database models; avoids naming confusion with `models/` directory. |
| `backend/app/agents/data_intake_agent.py` | `backend/app/agents/intake_agent.py` | Plain, concise purpose-driven name; removes redundant `data_` prefix. |
| `backend/app/agents/vision_agent.py` | `backend/app/agents/visual_agent.py` | Standardized agent naming aligning with visual inspection role. |
| `backend/app/agents/compliance_agent.py` | `backend/app/agents/dimensional_agent.py` | Clear domain role: evaluates physical dimensional measurements against USL/LSL. |
| `backend/app/agents/anomaly_agent.py` | `backend/app/agents/process_agent.py` | Aligns with process telemetry monitoring and machine sensor anomaly detection. |
| `backend/app/agents/critic_agent.py` | `backend/app/agents/reviewer_agent.py` | Clear role: quality review, mathematical verification, and adversarial audit. |
| `backend/app/orchestrator/langgraph_orchestration.py` | `backend/app/agents/workflow.py` | Houses the 8-agent LangGraph workflow graph definition within `agents/`. |
| `backend/app/agents/prompts/a1_intake.md` | `backend/app/agents/prompts/intake.md` | Eliminates numeric agent prefixes. |
| `backend/app/agents/prompts/a2_visual.md` | `backend/app/agents/prompts/visual.md` | Eliminates numeric agent prefixes. |
| `backend/app/agents/prompts/a3_dimensional.md` | `backend/app/agents/prompts/dimensional.md` | Eliminates numeric agent prefixes. |
| `backend/app/agents/prompts/a4_process_anomaly.md` | `backend/app/agents/prompts/process_anomaly.md` | Eliminates numeric agent prefixes. |
| `backend/app/agents/prompts/a5_spc.md` | `backend/app/agents/prompts/spc.md` | Eliminates numeric agent prefixes. |
| `backend/app/agents/prompts/a6_rca.md` | `backend/app/agents/prompts/rca.md` | Eliminates numeric agent prefixes. |
| `backend/app/agents/prompts/a7_capa.md` | `backend/app/agents/prompts/capa.md` | Eliminates numeric agent prefixes. |
| `backend/app/agents/prompts/a8_critic.md` | `backend/app/agents/prompts/reviewer.md` | Eliminates numeric agent prefixes. |
| `backend/app/services/spec_engine.py` | `backend/app/services/spec_check.py` | Descriptive action-focused name: specification limit and boundary checking. |
| `backend/app/services/spc_engine.py` | `backend/app/services/spc_charts.py` | Clear purpose: control chart limit calculation and Nelson rule verification. |
| `backend/app/services/anomaly.py` | `backend/app/services/anomaly_detection.py` | Unambiguous noun phrase: 5-layer telemetry anomaly detection service. |
| `backend/app/reports/pdf_generator.py` | `backend/app/services/pdf_report.py` | Consolidates report generation service under `services/`. |
| `backend/app/rag/vector_store.py` | `backend/app/services/rag_search.py` | Houses RAG semantic search and metadata retrieval logic under `services/`. |
| `backend/app/routers/api_router.py` | Modular domain routers in `backend/app/routers/` | Deconstructs 605-line god file into domain-specific modules (`batches.py`, `inspection.py`, `vision.py`, `process.py`, `spc.py`, `rca.py`, `capa.py`, `reports.py`, `orchestrator.py`, `auth.py`). |
| `powershell.exe` | `_archive_not_required/` | Clutter binary file not belonging in repository root. |

---

## 2. Target Directory Structure

```
quality-inspection-system/
├── README.md
├── alembic.ini
├── render.yaml
├── vercel.json
├── pyproject.toml
├── .gitignore
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── database/
│   │   │   ├── connection.py
│   │   │   ├── models.py
│   │   │   └── seed.py
│   │   ├── schemas/
│   │   │   ├── __init__.py
│   │   │   └── schemas.py
│   │   ├── routers/
│   │   │   ├── __init__.py
│   │   │   ├── auth.py
│   │   │   ├── batches.py
│   │   │   ├── capa.py
│   │   │   ├── dashboard.py
│   │   │   ├── inspection.py
│   │   │   ├── knowledge.py
│   │   │   ├── orchestrator.py
│   │   │   ├── process.py
│   │   │   ├── rca.py
│   │   │   ├── reports.py
│   │   │   ├── scenarios.py
│   │   │   ├── spc.py
│   │   │   └── vision.py
│   │   ├── agents/
│   │   │   ├── base_agent.py
│   │   │   ├── intake_agent.py
│   │   │   ├── visual_agent.py
│   │   │   ├── dimensional_agent.py
│   │   │   ├── process_agent.py
│   │   │   ├── spc_agent.py
│   │   │   ├── rca_agent.py
│   │   │   ├── capa_agent.py
│   │   │   ├── reviewer_agent.py
│   │   │   ├── quality_knowledge_agent.py
│   │   │   ├── workflow.py
│   │   │   └── prompts/
│   │   │       ├── intake.md
│   │   │       ├── visual.md
│   │   │       ├── dimensional.md
│   │   │       ├── process_anomaly.md
│   │   │       ├── spc.md
│   │   │       ├── rca.md
│   │   │       ├── capa.md
│   │   │       └── reviewer.md
│   │   ├── services/
│   │   │   ├── spec_check.py
│   │   │   ├── spc_charts.py
│   │   │   ├── capability.py
│   │   │   ├── anomaly_detection.py
│   │   │   ├── pareto.py
│   │   │   ├── effectiveness.py
│   │   │   ├── pdf_report.py
│   │   │   └── rag_search.py
│   │   ├── ml/
│   │   │   └── cv/
│   │   │       ├── infer.py
│   │   │       ├── gradcam.py
│   │   │       └── yolo_onnx_infer.py
│   │   └── core/
│   │       ├── config.py
│   │       ├── guardrails.py
│   │       ├── llm.py
│   │       ├── logging.py
│   │       └── security.py
│   ├── data/
│   │   ├── quality_system.db
│   │   ├── historical_ncrs.csv
│   │   ├── historical_ncrs.json
│   │   ├── product_specs.csv
│   │   ├── maintenance_records.csv
│   │   ├── mvtec_manifest.csv
│   │   ├── splits.json
│   │   ├── vector_kb.json
│   │   ├── knowledge_db/
│   │   └── knowledge_docs/
│   ├── models/
│   │   ├── cv_model.onnx
│   │   ├── cv_model.pt
│   │   ├── patchcore_banks.pt
│   │   ├── thresholds.json
│   │   ├── classes.json
│   │   └── cv_metrics.json
│   ├── tests/
│   │   └── (test suites)
│   └── requirements.txt
├── frontend/
│   ├── index.html
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   └── src/
│       ├── App.tsx
│       ├── main.tsx
│       ├── api.ts
│       ├── types.ts
│       ├── components/
│       │   ├── CertaintyBadge.tsx
│       │   ├── Header.tsx
│       │   └── Sidebar.tsx
│       └── pages/
│           ├── DashboardPage.tsx
│           ├── ProductConfigPage.tsx
│           ├── BatchesPage.tsx
│           ├── InspectionPage.tsx
│           ├── VisualInspectionPage.tsx
│           ├── ProcessMonitoringPage.tsx
│           ├── SpcDashboardPage.tsx
│           ├── IncidentsPage.tsx
│           ├── RcaPage.tsx
│           ├── CapaPage.tsx
│           ├── AiReviewPage.tsx
│           ├── ReportsPage.tsx
│           └── TestScenariosPage.tsx
├── docs/
│   ├── TECH_STACK_USED.md
│   ├── REFACTOR_PLAN.md
│   ├── architecture.md
│   ├── agents.md
│   ├── data_model.md
│   ├── api.md
│   ├── anomaly_methodology.md
│   ├── spc_methodology.md
│   ├── rca_methodology.md
│   ├── cv_model_card.md
│   ├── testing.md
│   ├── walkthrough/
│   │   ├── 01_intake.md
│   │   ├── 02_visual_inspection.md
│   │   ├── 03_dimensional_check.md
│   │   ├── 04_process_anomaly.md
│   │   ├── 05_spc_capability.md
│   │   ├── 06_root_cause_analysis.md
│   │   ├── 07_rag_knowledge.md
│   │   ├── 08_capa_human_approval.md
│   │   ├── 09_reviewer_critic.md
│   │   ├── 10_workflow_orchestration.md
│   │   ├── 11_frontend_architecture.md
│   │   └── 12_database_schema.md
│   └── demo/
└── scripts/
    ├── run_test_cases.py
    ├── show_db.py
    ├── show_vector_store.py
    └── train_cv.py
```

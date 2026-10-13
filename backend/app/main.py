"""
FastAPI Enterprise Application Entry Point
Agentic AI Manufacturing Quality Inspection & Root Cause Analysis System
Serves unified REST API, Static inspection media, and Production React Frontend.
"""
import os
import sys

# Constrain thread count for low-core cloud containers (Render 0.1 vCPU / 512MB RAM)
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["VECLIB_MAXIMUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"

try:
    import cv2
    cv2.setNumThreads(1)
except Exception:
    pass

try:
    import torch
    torch.set_num_threads(1)
except Exception:
    pass

# Ensure both repo root and backend directory are in sys.path
_current_dir = os.path.dirname(os.path.abspath(__file__))
_backend_dir = os.path.dirname(_current_dir)
_repo_dir = os.path.dirname(_backend_dir)
for _d in [_repo_dir, _backend_dir]:
    if _d not in sys.path:
        sys.path.insert(0, _d)

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, RedirectResponse, JSONResponse
from backend.app.routers.api_router import router as api_router
from backend.app.routers.knowledge_router import router as knowledge_router
from backend.app.database.session import Base, engine
import backend.app.database.models

tags_metadata = [
    {"name": "Products & Machines", "description": "Product catalogs, machine assets, and nominal specifications"},
    {"name": "Batches", "description": "Production batch management and anchor batch tracking"},
    {"name": "Inspection", "description": "Dimensional inspection intake and boundary-safe spec verification (Agent 1 & Agent 3)"},
    {"name": "Vision", "description": "Visual surface defect detection and proxy localization (Agent 2)"},
    {"name": "Process Monitoring", "description": "Real-time CNC telemetry, machine vibration, and anomaly detection (Agent 4)"},
    {"name": "SPC & Capability", "description": "Statistical Process Control, I-MR charts, Nelson rules, and Cp/Cpk indices (Agent 5)"},
    {"name": "Incidents", "description": "Quality incident records and Non-Conformance Reports (NCR)"},
    {"name": "Root Cause Analysis", "description": "5-Whys, 6M Ishikawa, and evidence-weighted causal reasoning (Agent 6)"},
    {"name": "RAG", "description": "In-process ChromaDB vector knowledge retrieval and SOP search"},
    {"name": "Pareto", "description": "Defect distribution and Vital Few analysis (IATF 16949)"},
    {"name": "CAPA", "description": "Corrective and Preventive Action planning and containment (Agent 7)"},
    {"name": "Workflows (Agents)", "description": "Stateful 8-Agent orchestration network and execution traces"},
    {"name": "Effectiveness", "description": "Two-proportion z-test statistical verification of CAPA efficacy"},
    {"name": "Dashboard", "description": "Aggregated factory floor metrics and real-time plant KPIs"},
    {"name": "Reports", "description": "ISO 9001 / IATF 16949 audit dossier PDF generation"},
    {"name": "System", "description": "Platform health, version telemetry, and runtime diagnostics"},
]

api_description = """
## QualityMind: Agentic Manufacturing Quality Decision-Support Platform

QualityMind is an enterprise industrial quality intelligence system engineered for high-precision CNC manufacturing cells. It orchestrates eight specialized AI agents with deterministic statistical process control, boundary-safe tolerance verification, computer vision defect localization, 8-parameter process anomaly detection, and human-in-the-loop engineering disposition.

### Mandatory Epistemic Labeling & Audit Governance
Every finding, chart, and recommendation is strictly partitioned into one of five epistemic labels:
- **`[OBSERVED FACT]`**: Verified direct measurements from calibrated sensors and gauges.
- **`[MODEL PREDICTION]`**: Inferences from computer vision and machine learning models.
- **`[STATISTICAL FINDING]`**: 3-sigma control limits, Nelson rule trips, and capability indices.
- **`[HYPOTHESIS]`**: Causal theories generated during Root Cause Analysis (RCA) requiring physical verification.
- **`[CONFIRMED ROOT CAUSE]`**: Final causal classification elevated exclusively by authenticated Quality Engineers.

### Human-in-the-Loop Decision Support
In compliance with IATF 16949 and ISO 9001, QualityMind functions exclusively as decision-support. It never autonomously releases batches, scraps parts, adjusts machine offsets, or stops production lines. All endpoints are open and accessible with zero authentication overhead.
"""

app = FastAPI(
    title="QualityMind API",
    description=api_description,
    version="2.0.0",
    openapi_tags=tags_metadata,
    contact={
        "name": "Quality Engineering Team",
        "email": "quality@precisionaero.com"
    },
    license_info={
        "name": "Proprietary / Precision Aerospace Manufacturing",
        "url": "https://precisionaero.com/license"
    }
)

from fastapi.openapi.utils import get_openapi

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
        tags=app.openapi_tags,
        contact=app.contact,
        license_info=app.license_info,
    )
    if "components" in openapi_schema and "securitySchemes" in openapi_schema["components"]:
        del openapi_schema["components"]["securitySchemes"]
    openapi_schema.pop("security", None)
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

# Support FRONTEND_ORIGINS environment variable as well as default approved origins
raw_frontend_origins = os.environ.get("FRONTEND_ORIGINS", "")
env_origins = [o.strip().rstrip("/") for o in raw_frontend_origins.split(",") if o.strip()]
default_origins = [
    "https://quality-mind.vercel.app",
    "https://qualitymind.vercel.app",
    "https://qualiforge-app.vercel.app",
    "http://localhost:5173",
    "http://localhost:3000",
    "http://localhost:8000",
]
origins = list(dict.fromkeys(env_origins + default_origins))

# Enable CORS with explicit origins, regex for all Vercel previews, and full method/header support
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=r"^https:\/\/.*\.vercel\.app$",
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept", "X-Requested-With", "*"],
    expose_headers=["*"],
)

from fastapi import HTTPException
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import logging

# Global exception handler ensuring CORS headers are preserved even on 500 crashes
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    origin = request.headers.get("origin")
    headers = {
        "Access-Control-Allow-Credentials": "true",
        "Access-Control-Allow-Methods": "*",
        "Access-Control-Allow-Headers": "*",
    }
    if origin:
        headers["Access-Control-Allow-Origin"] = origin
    else:
        headers["Access-Control-Allow-Origin"] = "*"

    if isinstance(exc, (HTTPException, StarletteHTTPException)):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
            headers=headers,
        )
    if isinstance(exc, RequestValidationError):
        return JSONResponse(
            status_code=422,
            content={"detail": exc.errors()},
            headers=headers,
        )

    logging.getLogger("uvicorn.error").error(f"Unhandled Server Error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal Server Error: {str(exc)}"},
        headers=headers,
    )

# Initialize Database and Sample Assets on Startup
@app.on_event("startup")
def startup_event():
    Base.metadata.create_all(bind=engine)

# Static files mount for uploaded/annotated inspection images
static_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "static"))
os.makedirs(os.path.join(static_dir, "uploads", "samples"), exist_ok=True)
os.makedirs(os.path.join(static_dir, "uploads", "annotated"), exist_ok=True)
app.mount("/uploads", StaticFiles(directory=os.path.join(static_dir, "uploads")), name="uploads")

# Include API and Knowledge routers exactly once
app.include_router(api_router)
app.include_router(knowledge_router)

@app.get("/health", tags=["System"], summary="System Health & Readiness Check", description="Returns operational health status, active agents count, and governance mode.")
def health_check():
    return {
        "status": "HEALTHY",
        "system": "Agentic AI Manufacturing Quality Inspection & RCA System",
        "version": "2.0.0",
        "agents_active": 8,
        "mode": "HUMAN_IN_THE_LOOP_DECISION_SUPPORT"
    }

# Mount React Frontend Production Build (if built)
dist_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "dist"))
if os.path.exists(dist_dir):
    assets_dir = os.path.join(dist_dir, "assets")
    if os.path.exists(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def serve_frontend(full_path: str):
        file_path = os.path.join(dist_dir, full_path)
        if full_path and os.path.exists(file_path) and os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(dist_dir, "index.html"))
else:
    @app.get("/", include_in_schema=False)
    def root_redirect():
        return RedirectResponse(url="/docs")

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=port, reload=False)

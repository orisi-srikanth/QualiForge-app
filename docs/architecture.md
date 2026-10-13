# QualityMind System Architecture

## Overview
QualityMind is an enterprise agentic manufacturing quality decision-support platform designed for high-precision discrete manufacturing (e.g. CNC machining, precision shafts, hydraulic components). It coordinates 8 specialized AI agents with deterministic engineering engines, computer vision defect inspection, Statistical Process Control (SPC), 8-parameter process anomaly detection, and human-in-the-loop governance.

---

## Architecture Diagram (Mermaid)

```mermaid
flowchart TD
    subgraph DataSources["Factory Floor Data Streams"]
        ProdBatch["Production Batches & Metadata (CSV/Excel)"]
        Sensors["Machine Telemetry (Spindle, Vibration, Tool Cycles, Temp, etc.)"]
        InspFiles["Coordinate Measuring & Gauge Measurements"]
        Images["High-Resolution Surface Images (512x512)"]
    end

    subgraph Agents["QualityMind 8-Agent Orchestration Network"]
        A1["Agent 1: Production & Quality Data Intake Agent\n(Schema Validation, Unit Normalization)"]
        A2["Agent 2: Visual Quality Inspection Agent\n(PyTorch MobileNetV3 + Morphological Localization)"]
        A3["Agent 3: Dimensional Compliance Agent\n(Deterministic USL/LSL Deviation Engine)"]
        A4["Agent 4: Process Anomaly Detection Agent\n(Isolation Forest + EWMA + CUSUM 5-Layer Engine)"]
        A5["Agent 5: Statistical Process Control Agent\n(I-MR, X-bar/R, Nelson Rules, Cp/Cpk)"]
        A6["Agent 6: Root Cause Analysis Agent\n(5-Whys, 6M Ishikawa, Vector RAG Retrieval)"]
        A7["Agent 7: CAPA Management Agent\n(Containment, Corrective, Preventive Action Planning)"]
        A8["Agent 8: Quality Critic Agent\n(Calculation Audit, Causal Interceptor, Reassessment Loop)"]
    end

    subgraph Engines["Deterministic Services & Machine Learning"]
        SpecEng["Deterministic Spec & Limit Engine\n(Boundary-Safe Decimal Arithmetic)"]
        SpcEng["SPC Engine\n(Nelson Rules 1-8, Separated UCL/LCL from USL/LSL)"]
        CapEng["Capability Engine\n(Cp, Cpk, Pp, Ppk with Guardrail Warnings)"]
        AnomEng["Hybrid Anomaly Engine\n(Isolation Forest, Robust Z-score, Drift Tests)"]
        RAGStore["Vector Store & Historical RAG\n(ChromaDB + All-MiniLM-L6-v2, 20+ NCRs)"]
        CVModel["PyTorch Vision Model\n(MobileNetV3 Transfer Learning, Grad-CAM Heatmaps)"]
    end

    subgraph Governance["Governance & Human-in-the-Loop Gate"]
        State["Checkpointed Shared WorkflowState\n(Pydantic v2 Models & Audit Tracing)"]
        HITL["Human-in-the-Loop Approval Gate\n(Authorized Quality Engineer Sign-Off)"]
        Guard["Guardrail Layer\n(Blocks Forbidden Autonomous Actions)"]
    end

    subgraph Output["Decision-Support Artifacts"]
        UI["React 19 + TypeScript + Tailwind UI\n(13 Interactive Pages + Execution Visibility)"]
        PDF["ISO 9001 / IATF 16949 Audit Report PDF\n(13 Sections, Embedded Charts, Epistemic Labels)"]
    end

    %% Data flow connections
    ProdBatch --> A1
    InspFiles --> A1
    A1 --> SpecEng
    A1 --> A3
    
    Images --> A2
    A2 --> CVModel
    
    A3 --> SpcEng
    A3 --> A5
    
    Sensors --> A4
    A4 --> AnomEng
    
    A3 --> A6
    A4 --> A6
    A5 --> A6
    A6 --> RAGStore
    
    A6 --> A7
    A7 --> A8
    A8 -- "Reassessment Loop (Max 2)" --> A6
    A8 --> HITL
    
    HITL --> State
    State --> UI
    State --> PDF
    Guard -.-> Agents
```

---

## Core System Subsystems

### 1. Deterministic Calculation Core
In strict adherence to manufacturing quality standards (AIAG, ISO 9001, IATF 16949), all arithmetic calculations are executed by verified Python libraries (`NumPy`, `SciPy`, `Pandas`, `Decimal`). An LLM is never permitted to perform arithmetic or evaluate part conformance.

### 2. Multi-Agent Orchestration & Shared WorkflowState
All 8 agents execute against a centralized, strongly-typed Pydantic v2 `WorkflowState`. State modifications are tracked with step execution records including elapsed time in milliseconds, input summaries, tool calls, and epistemic labeling.

### 3. Epistemic Labeling Taxonomy
Every finding across the API, frontend, and PDF export is tagged with exactly one label:
1. `OBSERVED_FACT`: Direct, verified physical measurements or batch properties.
2. `MODEL_PREDICTION`: Machine learning outputs (e.g. computer vision defect inference).
3. `STATISTICAL_FINDING`: 3-sigma statistical control limit evaluations, telemetry z-scores, and anomaly signals.
4. `HYPOTHESIS`: Root cause hypotheses generated through inductive reasoning and historical retrieval.
5. `CONFIRMED_ROOT_CAUSE`: Physical defect origin authorized and stamped by a certified Quality Engineer.

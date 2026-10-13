# Module 06: Root Cause Analysis (RCA)

## 1. What It Does in 3 Sentences
The Root Cause Analysis module investigates manufacturing non-conformances by structuring physical evidence across a 6M Ishikawa (Fishbone) diagram and a 5-Whys causal progression. It queries historical plant incident records using vector semantic retrieval to identify past verified failures with matching defect signatures. It synthesizes candidate root causes into ranked hypotheses with supporting and contradicting evidence, strictly labeled `[HYPOTHESIS]` pending physical engineering inspection.

## 2. Key Functions and File Paths
- `RootCauseAnalysisAgent.analyze_incident()` in [`backend/app/agents/rca_agent.py`](file:///d:/Projects%20Local/QT/backend/app/agents/rca_agent.py)
- Vector RAG search helper in [`backend/app/services/rag_search.py`](file:///d:/Projects%20Local/QT/backend/app/services/rag_search.py)
- Schema definitions in [`backend/app/schemas/schemas.py`](file:///d:/Projects%20Local/QT/backend/app/schemas/schemas.py) (`RCAReport`, `FishboneCategory`, `FiveWhysItem`, `HypothesisEvidence`)

## 3. Formula / Algorithm in Plain Words with BATCH-0245 Worked Example
The agent constructs an evidence-weighted confidence score $C_k$ for each candidate hypothesis $H_k$:
$$C_k = \frac{\sum w_{\text{support}} - \sum w_{\text{contradict}}}{\sum w_{\text{max}}} \times 100\%$$
Where evidence weights are assigned by modality:
- Direct physical telemetry trip (e.g. tool life $> 90\%$ overdue): weight = 0.40
- Sensor correlation (e.g. high vibration + high part diameter): weight = 0.30
- Historical incident match in vector store (e.g. NCR-019 match): weight = 0.20
- Conflicting parameters (e.g. nominal spindle speed / nominal feed rate): acts as negative weight (-0.25) against CNC speed programming error.

**Worked Example from BATCH-0245:**
Candidate Hypothesis 1: **Progressive Tool Flank Wear on CNC-04 Carbide Insert**.
- Supporting Evidence 1: Tool insert count at 1,150 cycles (+91% over 600 nominal threshold).
- Supporting Evidence 2: High spindle vibration at 3.84 mm/s (baseline 2.10 mm/s).
- Supporting Evidence 3: Historical match NCR-019 describes identical failure ("Tool wear flank VB > 0.35 mm on CNC-04 caused +0.03 mm shaft oversize").
- Contradicting Evidence: None.
- Result: **Rank 1 candidate (Confidence: 88.0%)**.

Candidate Hypothesis 2: **Spindle Speed / Feed Rate Programming Error**.
- Supporting Evidence: None.
- Contradicting Evidence: Spindle speed remained constant at 1,200 RPM and feed rate stayed at 0.20 mm/rev throughout the entire batch.
- Result: **Rejected candidate**.

## 4. Design Decision and Alternative
- **Decision**: Structuring causal findings across two standard automotive methodologies (6M Fishbone and 5-Whys) alongside ranked hypotheses.
- **Alternative**: Generating a single free-form narrative paragraph with an LLM.
- **Why Chosen**: IATF 16949 and ISO 9001 audits require structured categorization across Man, Machine, Material, Method, Measurement, and Milieu; free-form LLM text often omits categories and cannot be programmatically verified.

## 5. One Limitation
The RCA agent identifies statistical correlations and physical plausibility, but it cannot disassemble machine components or perform optical metallurgical inspections; human quality engineers must physically inspect the tool insert to elevate the hypothesis to a confirmed root cause.

## 6. Three Questions an Examiner Might Ask with Factual Answers
1. **Q: Why does the RCA report output `[HYPOTHESIS]` rather than `[CONFIRMED ROOT CAUSE]`?**
   - *Answer*: Under our epistemic safety rules, AI agents are prohibited from declaring proven causation autonomously. Only an authenticated human Quality Engineer using calibrated metrology tools can confirm root cause.
2. **Q: Which historical incident was retrieved from the vector database for BATCH-0245?**
   - *Answer*: Incident **NCR-019** ("Dimensional Non-Conformance on Precision Shaft PS-2026-101 due to Tool Flank Wear on CNC-04"), with a vector similarity score of 0.88.
3. **Q: What are the 6Ms in the Fishbone diagram?**
   - *Answer*: Machine, Method, Material, Manpower, Measurement, and Milieu (Environment). The agent populates every category with real parameters from the batch.

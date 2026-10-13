# Module 07: Vector Knowledge Retrieval (RAG Pipeline)

## 1. What It Does in 3 Sentences
The Vector Knowledge Retrieval module indexes historical Non-Conformance Reports (NCRs), Standard Operating Procedures (SOPs), machine manuals, and quality specifications into a local persistent ChromaDB collection. It uses record-aware chunking to preserve complete tabular CSV rows and PDF sections as cohesive semantic documents. When agents or engineers query the knowledge base, it returns ranked cosine-similarity matches with source citations and supports fully offline deterministic operation.

## 2. Key Functions and File Paths
- `QualityKnowledgeAgent.query()` in [`backend/app/agents/quality_knowledge_agent.py`](file:///d:/Projects%20Local/QT/backend/app/agents/quality_knowledge_agent.py)
- `QualityKnowledgeAgent.ingest_documents()` in [`backend/app/agents/quality_knowledge_agent.py`](file:///d:/Projects%20Local/QT/backend/app/agents/quality_knowledge_agent.py)
- Document parsers in [`backend/app/services/document_loader.py`](file:///d:/Projects%20Local/QT/backend/app/services/document_loader.py)
- Schema definitions in [`backend/app/schemas/schemas.py`](file:///d:/Projects%20Local/QT/backend/app/schemas/schemas.py) (`KnowledgeQueryResponse`, `KnowledgeMatchItem`)

## 3. Formula / Algorithm in Plain Words with BATCH-0245 Worked Example
Text chunks are embedded into dense 384-dimensional vectors $\vec{u}$ using the local ONNX embedding model `all-MiniLM-L6-v2`. The vector database computes cosine distance $d$ to query vector $\vec{v}$:
$$d(\vec{u}, \vec{v}) = 1 - \frac{\vec{u} \cdot \vec{v}}{\|\vec{u}\|_2 \|\vec{v}\|_2}$$
Reported similarity score:
$$\text{Similarity} = 1 - \frac{d}{2} \in [0, 1]$$

**Worked Example from BATCH-0245:**
Query string: `"Oversized shaft diameter CNC-04 tool wear vibration 1150 cycles"`
- ChromaDB embeds the query and searches the indexed NCR collection.
- Top-1 match retrieved is `NCR-019`:
  - Source file: `historical_ncrs.csv`
  - Record ID: `NCR-019`
  - Text excerpt: `"[NCR RECORD NCR-019] Part: PS-2026-101, Machine: CNC-04, Defect: Oversized shaft diameter (+0.03 mm). Root cause: Progressive tool flank wear on carbide insert exceeding 1,000 cycles without offset compensation. Corrective action: Replace carbide insert, recalibrate CMM offset."`
  - Cosine distance: $d = 0.24 \implies \text{Similarity Score} = 1 - \frac{0.24}{2} = 0.880$.

## 4. Design Decision and Alternative
- **Decision**: Ingesting CSV rows as complete single cohesive chunks with rich metadata fields (`machine`, `defect_type`, `record_id`).
- **Alternative**: Splitting CSV files by arbitrary character counts (e.g. 500 characters) like standard text.
- **Why Chosen**: Character-based chunking slices through table rows, splitting header names from numeric measurements and corrupting tabular records; preserving each row keeps the manufacturing incident intact.

## 5. One Limitation
The local ChromaDB embedding model (`all-MiniLM-L6-v2`) has an input context window of 256 word pieces; very long multi-page PDF maintenance manuals are chunked into 350-word paragraphs, which can split cross-page diagrams or long technical tables.

## 6. Three Questions an Examiner Might Ask with Factual Answers
1. **Q: Does the RAG pipeline require an external internet connection or cloud API key to function?**
   - *Answer*: No. The embedding model runs locally via Chroma's built-in ONNX runtime (`all-MiniLM-L6-v2`), and answer synthesis defaults to deterministic retrieval mode when `LLM_PROVIDER="none"`.
2. **Q: How does the pipeline ensure idempotency when ingesting documents repeatedly?**
   - *Answer*: Each record's text is hashed with SHA-256 (`content_hash`) and compared against existing metadata in the collection. If the hash matches, the record is skipped, preventing duplicate entries.
3. **Q: How does the system handle scanned PDF files with no text layer?**
   - *Answer*: In `document_loader.py`, PyMuPDF measures total extracted character count; if less than 20 characters are detected across all pages, it emits a warning: `"Warning: PDF contains little or no extractable text. OCR is required for scanned documents."`

# Module 01: Production & Quality Data Intake

## 1. What It Does in 3 Sentences
The Data Intake module ingests production batch metadata and raw CMM measurement files in CSV or tabular format. It checks required batch fields and immediately pauses execution if required information like batch ID or nominal tolerances is missing. Finally, it normalizes all incoming dimensional units into millimeters using deterministic conversion factors before passing data to downstream inspection agents.

## 2. Key Functions and File Paths
- `ProductionDataIntakeAgent.process_batch_and_measurements()` in [`backend/app/agents/intake_agent.py`](file:///d:/Projects%20Local/QT/backend/app/agents/intake_agent.py)
- `_normalize_units()` in [`backend/app/agents/intake_agent.py`](file:///d:/Projects%20Local/QT/backend/app/agents/intake_agent.py)
- Schema definitions in [`backend/app/schemas/schemas.py`](file:///d:/Projects%20Local/QT/backend/app/schemas/schemas.py) (`DataIntakeOutput`, `UnitConversionRecord`)

## 3. Formula / Algorithm in Plain Words with BATCH-0245 Worked Example
The unit normalization algorithm matches the unit column against a known lookup dictionary. If inches are supplied, it multiplies by 25.4. If micrometers (µm) are supplied, it divides by 1,000. If centimeters are supplied, it multiplies by 10. If millimeters are supplied, no multiplier is applied.

**Worked Example from BATCH-0245:**
Suppose sample P001 arrives as `1.968897 in`.
$$\text{Normalized Value} = 1.968897 \times 25.4 = 50.0100\,\text{mm}$$
Suppose sample P002 arrives as `50030.0 µm`.
$$\text{Normalized Value} = \frac{50030.0}{1000} = 50.0300\,\text{mm}$$
The normalized records are stored as `50.01 mm` and `50.03 mm`, tagged with epistemic label `[OBSERVED FACT]`.

## 4. Design Decision and Alternative
- **Decision**: Unit conversion and schema parsing use pure deterministic Python math without LLM calls.
- **Alternative**: Passing CSV text to an LLM to parse columns and convert units.
- **Why Chosen**: In manufacturing, unit errors cause catastrophic physical scrap; deterministic multiplication is 100% repeatable, runs in less than 2 milliseconds, and cannot hallucinate.

## 5. One Limitation
The intake agent currently requires measurement files to have tabular columnar formats (CSV/Excel) with recognizable column headers (`measured_value`, `sample_id`, `unit`). It does not automatically transcribe unstructured handwritten inspection sheets or scanned paper PDFs.

## 6. Three Questions an Examiner Might Ask with Factual Answers
1. **Q: How does the intake agent handle missing critical fields?**
   - *Answer*: If any required field (`batch_id`, `part_number`, `machine`, `quantity`, `nominal_mm`, `tolerance_mm`) is missing, the agent sets `needs_info=True` in `DataIntakeOutput` and records the missing field names. LangGraph routes this to `needs_info_gate`, halting the pipeline until human operators supply the missing data.
2. **Q: What happens if an unsupported unit like 'feet' is provided?**
   - *Answer*: If the unit string is not recognized in the deterministic normalization map, the agent flags an unrecognized unit warning and marks the record for operator verification rather than guessing a multiplier.
3. **Q: How is epistemic certainty labeled for intake data?**
   - *Answer*: The intake agent is initialized with `CertaintyLevel.OBSERVED_FACT` because calibrated measurement gauges and direct CMM readings represent ground-truth physical observations.

"""
Agent 1: Production & Quality Data Intake Agent (Requirement 3)
Fast, deterministic processing paired with forced Pydantic JSON schema validation
and Groq LLM (model: openai/gpt-oss-20b, reasoning_effort='low') interpretation.
Performs:
- Fuzzy column-name mapping (Diameter, Dia_mm, Shaft_OD, etc.)
- Deterministic engineering unit normalization (inches -> * 25.4, µm -> / 1000, cm -> * 10)
- Missing field identification and 'needs_info' gating
- Schema validation via DataIntakeOutput
- Interpretation of unstructured production/operator notes using Groq openai/gpt-oss-20b
- Safe fallback to deterministic logic when Groq is unavailable or offline
"""
import io
import json
import logging
import os
import re
import time
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv
import pandas as pd

from backend.app.agents.base_agent import BaseQualityAgent
from backend.app.models.schemas import CertaintyLevel, DataIntakeOutput, UnitConversionRecord
from backend.app.core.config import settings

logger = logging.getLogger("qualiforge.agent1")

# Module-level cached Groq client (avoids re-instantiating client per request)
_cached_groq_client: Optional[Any] = None

def get_groq_client(force_refresh: bool = False) -> Optional[Any]:
    """
    Returns a reusable Groq client initialized with GROQ_API_KEY from environment.
    Never exposes, logs, or returns the raw API key.
    Reuses existing client across requests to prevent redundant client instantiation.
    """
    global _cached_groq_client
    if _cached_groq_client is not None and not force_refresh:
        return _cached_groq_client

    try:
        from groq import Groq
    except ImportError:
        logger.warning("[Agent 1] 'groq' package not installed; falling back to deterministic processing.")
        return None

    load_dotenv()
    api_key = os.environ.get("GROQ_API_KEY")
    if api_key is None:
        from backend.app.core.config import settings
        api_key = getattr(settings, "GROQ_API_KEY", "")

    if not api_key:
        logger.info("[Agent 1] GROQ_API_KEY is not configured; deterministic fallback active.")
        return None

    try:
        groq_base = os.environ.get("GROQ_BASE_URL", "https://api.groq.com")
        if groq_base.endswith("/openai/v1"):
            groq_base = groq_base[:-10]
        elif groq_base.endswith("/openai/v1/"):
            groq_base = groq_base[:-11]

        client = Groq(
            api_key=api_key,
            base_url=groq_base,
            timeout=15.0,
            max_retries=1
        )
        _cached_groq_client = client
        return client
    except Exception as e:
        logger.warning(f"[Agent 1] Failed to initialize Groq client: {e}")
        return None

def set_groq_client(client: Optional[Any]) -> None:
    """Injects a mock or custom Groq client for unit testing."""
    global _cached_groq_client
    _cached_groq_client = client

def reset_groq_client() -> None:
    """Resets cached Groq client."""
    global _cached_groq_client
    _cached_groq_client = None


class ProductionDataIntakeAgent(BaseQualityAgent):
    def __init__(self):
        super().__init__(
            name="Agent 1 — Production & Quality Data Intake Agent",
            role="Collect, validate, normalize units, and structure manufacturing intake data",
            certainty_level=CertaintyLevel.OBSERVED_FACT
        )

    def interpret_production_notes(
        self,
        notes: str,
        batch_meta: Dict[str, Any],
        warnings: Optional[List[str]] = None,
        client: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        Uses Groq API with model 'openai/gpt-oss-20b' and reasoning_effort='low'
        to interpret unstructured production notes, operator observations, or intake warnings.

        Strict constraints:
        - Used only for non-authoritative interpretation and candidate observations.
        - Never fabricates missing measurements, tolerances, or machine baselines.
        - Cannot overwrite QE-approved specs or deterministic batch limits.
        - Distinguishes facts from inferences.
        - Returns structured dictionary with 'status', 'summary', 'extracted_facts', 'inferred_observations'.
        """
        active_client = client or get_groq_client()
        if not active_client:
            return {
                "status": "unavailable",
                "model": "openai/gpt-oss-20b",
                "reason": "GROQ_API_KEY not configured or client unavailable",
                "fallback_used": True,
                "summary": "Deterministic intake active; Groq LLM interpretation skipped (API key not active).",
                "extracted_facts": {},
                "inferred_observations": []
            }

        batch_id = str(batch_meta.get("batch_id", "UNKNOWN"))
        part_number = str(batch_meta.get("part_number", "UNKNOWN"))
        machine = str(batch_meta.get("machine", "UNKNOWN"))
        shift = str(batch_meta.get("shift", "UNKNOWN"))
        nominal_mm = batch_meta.get("nominal_mm", 50.0)
        tolerance_mm = batch_meta.get("tolerance_mm", 0.05)
        warning_list = warnings or []

        prompt_str = (
            "You are Agent 1 (Production & Quality Data Intake Agent) in the QualiForge quality intelligence system.\n"
            "Your role is strictly limited to interpreting unstructured operator/production notes and summarizing intake warnings.\n\n"
            "QUALITY & SAFETY RULES:\n"
            "1. Output MUST be a valid JSON object adhering to the schema below.\n"
            "2. NEVER invent or fabricate missing measurements, nominals, tolerances, or machine settings.\n"
            "3. Distinguish extracted facts from inferred observations.\n"
            "4. Retain source text quotes for any observation.\n"
            "5. You cannot override authoritative batch specifications or dimensions.\n\n"
            f"AUTHORITATIVE BATCH CONTEXT (DO NOT OVERWRITE):\n"
            f"- Batch ID: {batch_id}\n"
            f"- Part Number: {part_number}\n"
            f"- Machine: {machine}\n"
            f"- Shift: {shift}\n"
            f"- Nominal Dimension: {nominal_mm} mm (Tolerance: ±{tolerance_mm} mm)\n\n"
            f"INTAKE WARNINGS:\n"
            f"{json.dumps(warning_list)}\n\n"
            f"UNSTRUCTURED PRODUCTION NOTES:\n"
            f"\"\"\"{notes}\"\"\"\n\n"
            "Reply with a JSON object with this exact structure:\n"
            "{\n"
            '  "summary": "<Concise 1-2 sentence engineering summary of the notes and intake context>",\n'
            '  "extracted_facts": {\n'
            '    "operator_name": "<name if explicitly stated in notes, else null>",\n'
            '    "material_lot_ref": "<material/heat lot if explicitly stated, else null>",\n'
            '    "tooling_id": "<tool ID if explicitly stated, else null>"\n'
            "  },\n"
            '  "inferred_observations": [\n'
            '    {"category": "<tool_wear|thermal_drift|material_issue|process_speed|general>", "observation": "<description>", "source_text": "<quote from notes>", "certainty": "INFERRED"}\n'
            "  ],\n"
            '  "operator_concerns_flagged": false,\n'
            '  "model": "openai/gpt-oss-20b"\n'
            "}"
        )

        try:
            r = active_client.chat.completions.create(
                model="openai/gpt-oss-20b",
                reasoning_effort="low",
                messages=[
                    {
                        "role": "user",
                        "content": prompt_str
                    }
                ],
                response_format={"type": "json_object"},
            )

            raw_content = r.choices[0].message.content or "{}"
            parsed = json.loads(raw_content)

            return {
                "status": "success",
                "model": "openai/gpt-oss-20b",
                "reasoning_effort": "low",
                "fallback_used": False,
                "summary": parsed.get("summary", ""),
                "extracted_facts": parsed.get("extracted_facts", {}),
                "inferred_observations": parsed.get("inferred_observations", []),
                "operator_concerns_flagged": bool(parsed.get("operator_concerns_flagged", False)),
                "raw_response": parsed
            }
        except json.JSONDecodeError as jde:
            logger.warning(f"[Agent 1] Groq output was not valid JSON: {jde}")
            return {
                "status": "error",
                "model": "openai/gpt-oss-20b",
                "error_type": "json_decode_error",
                "fallback_used": True,
                "summary": "LLM output was malformed JSON; deterministic fallback preserved.",
                "details": str(jde)
            }
        except Exception as e:
            error_cls = type(e).__name__
            logger.warning(f"[Agent 1] Groq API call failed ({error_cls}): {str(e)[:120]}")
            return {
                "status": "error",
                "model": "openai/gpt-oss-20b",
                "error_type": error_cls,
                "fallback_used": True,
                "summary": f"Groq API unavailable ({error_cls}); deterministic fallback preserved.",
                "details": str(e)[:120]
            }

    def process_batch_and_measurements(
        self,
        batch_meta: Dict[str, Any],
        raw_measurements: Optional[List[Dict[str, Any]]] = None,
        csv_content: Optional[str] = None,
        production_notes: Optional[str] = None
    ) -> Dict[str, Any]:
        start = time.time()
        tool_calls = ["tool_validate_batch_schema", "tool_deterministic_unit_normalization"]

        # 1. Check Missing Critical Fields
        required_fields = ["batch_id", "part_number", "machine", "quantity", "nominal_mm", "tolerance_mm"]
        missing_fields = []
        for field in required_fields:
            if field not in batch_meta or batch_meta[field] is None:
                missing_fields.append(field)

        warnings = []
        needs_info = False
        if missing_fields:
            needs_info = True
            warnings.append(f"CRITICAL INTAKE ERROR: Missing required batch fields: {missing_fields}. Pipeline requires clarification.")

        # 2. Extract and sanitize batch attributes
        batch_id = str(batch_meta.get("batch_id", "BATCH-0245"))
        part_number = str(batch_meta.get("part_number", "PS-2026-101"))
        machine = str(batch_meta.get("machine", "CNC-04"))
        quantity = int(batch_meta.get("quantity", 500))
        material = str(batch_meta.get("material", "Carbon Steel"))
        shift = str(batch_meta.get("shift", "Night"))
        inspection_param = str(batch_meta.get("inspection_parameter", "shaft_diameter"))
        nominal_mm = float(batch_meta.get("nominal_mm", 50.00))
        tolerance_mm = float(batch_meta.get("tolerance_mm", 0.05))
        usl = round(nominal_mm + tolerance_mm, 4)
        lsl = round(nominal_mm - tolerance_mm, 4)

        # 3. Deterministic Measurement Extraction & Unit Normalization
        parsed_measurements = []
        unit_conversions = []

        if csv_content:
            tool_calls.append("tool_parse_csv_stream")
            df = pd.read_csv(io.StringIO(csv_content))
            
            # Fuzzy column header detection
            col_map = {}
            for col in df.columns:
                c_lower = col.lower().strip()
                if any(k in c_lower for k in ["sample", "id", "part_id", "piece"]):
                    col_map["sample_id"] = col
                elif any(k in c_lower for k in ["dia", "val", "measure", "od", "shaft"]):
                    col_map["value"] = col
                elif "unit" in c_lower:
                    col_map["unit"] = col

            val_col = col_map.get("value", df.columns[1] if len(df.columns) > 1 else df.columns[0])
            id_col = col_map.get("sample_id", df.columns[0])
            unit_col = col_map.get("unit")

            # Detect unit from column header
            header_unit = "mm"
            if "inch" in str(val_col).lower() or '"' in str(val_col):
                header_unit = "in"
            elif any(u in str(val_col).lower() for u in ["µm", "um", "micron"]):
                header_unit = "um"
            elif "cm" in str(val_col).lower():
                header_unit = "cm"

            for idx, row in df.iterrows():
                sid = str(row.get(id_col, f"P{idx+1:03d}"))
                raw_val = float(row.get(val_col, 50.00))
                row_unit = str(row.get(unit_col, header_unit)).lower().strip() if unit_col else header_unit

                # Deterministic unit normalization
                converted_val = raw_val
                if row_unit in ["in", "inch", '"']:
                    converted_val = round(raw_val * 25.4, 4)
                    unit_conversions.append({
                        "sample_id": sid, "original_value": raw_val,
                        "original_unit": "in", "converted_value_mm": converted_val
                    })
                elif row_unit in ["um", "µm", "micron"]:
                    converted_val = round(raw_val / 1000.0, 4)
                    unit_conversions.append({
                        "sample_id": sid, "original_value": raw_val,
                        "original_unit": "um", "converted_value_mm": converted_val
                    })
                elif row_unit in ["cm"]:
                    converted_val = round(raw_val * 10.0, 4)
                    unit_conversions.append({
                        "sample_id": sid, "original_value": raw_val,
                        "original_unit": "cm", "converted_value_mm": converted_val
                    })

                parsed_measurements.append({"sample_id": sid, "measured_value": converted_val})

        elif raw_measurements:
            tool_calls.append("tool_structure_raw_samples")
            for item in raw_measurements:
                sid = item.get("sample_id", "P-")
                raw_val = float(item.get("measured_value", 50.0))
                raw_u = str(item.get("unit", "mm")).lower().strip()
                converted_val = raw_val

                if raw_u in ["in", "inch", '"']:
                    converted_val = round(raw_val * 25.4, 4)
                    unit_conversions.append({
                        "sample_id": sid, "original_value": raw_val,
                        "original_unit": "in", "converted_value_mm": converted_val
                    })
                elif raw_u in ["um", "µm", "micron"]:
                    converted_val = round(raw_val / 1000.0, 4)
                    unit_conversions.append({
                        "sample_id": sid, "original_value": raw_val,
                        "original_unit": "um", "converted_value_mm": converted_val
                    })
                elif raw_u in ["cm"]:
                    converted_val = round(raw_val * 10.0, 4)
                    unit_conversions.append({
                        "sample_id": sid, "original_value": raw_val,
                        "original_unit": "cm", "converted_value_mm": converted_val
                    })

                parsed_measurements.append({"sample_id": sid, "measured_value": converted_val})

        else:
            parsed_measurements = []

        # 4. Interpret Unstructured Production Notes via Groq (openai/gpt-oss-20b)
        notes_str = (
            production_notes
            or batch_meta.get("notes")
            or batch_meta.get("production_notes")
            or batch_meta.get("operator_notes")
            or batch_meta.get("shift_notes")
        )

        llm_interpretation = None
        if notes_str or warnings:
            notes_payload = str(notes_str) if notes_str else "No free-text operator notes recorded."
            llm_interpretation = self.interpret_production_notes(
                notes=notes_payload,
                batch_meta=batch_meta,
                warnings=warnings
            )
            if llm_interpretation.get("status") == "success":
                tool_calls.append("tool_groq_production_notes_interpretation_gpt_oss_20b")
            else:
                tool_calls.append("tool_groq_intake_fallback")

        # 5. Enforce Pydantic DataIntakeOutput Contract
        intake_output = DataIntakeOutput(
            batch_id=batch_id,
            part_number=part_number,
            machine=machine,
            quantity=quantity,
            material=material,
            shift=shift,
            inspection_parameter=inspection_param,
            nominal_mm=nominal_mm,
            tolerance_mm=tolerance_mm,
            usl=usl,
            lsl=lsl,
            missing_fields=missing_fields,
            unit_conversions=unit_conversions,
            warnings=warnings,
            needs_info=needs_info,
            measurements=parsed_measurements,
            certainty=CertaintyLevel.OBSERVED_FACT,
            production_notes=str(notes_str) if notes_str else None,
            llm_interpretation=llm_interpretation,
            candidate_metadata=llm_interpretation.get("extracted_facts") if (llm_interpretation and isinstance(llm_interpretation, dict)) else None
        )

        duration = int((time.time() - start) * 1000)
        log_entry = self.log_execution(
            step_number=1,
            input_summary=f"Ingested batch {batch_id} metadata and {len(parsed_measurements)} measurement records",
            tool_calls=tool_calls,
            output_summary=(
                f"Successfully parsed and normalized batch {batch_id} ({part_number}). "
                f"Units: {len(unit_conversions)} converted to mm. Missing fields: {len(missing_fields)}. "
                f"Groq LLM interpretation: {llm_interpretation.get('status', 'skipped') if llm_interpretation else 'skipped'}."
            ),
            duration_ms=duration
        )

        return {
            "batch_data": intake_output.model_dump(),
            "intake_schema": intake_output,
            "log": log_entry
        }

data_intake_agent = ProductionDataIntakeAgent()
intake_agent = data_intake_agent
DataIntakeAgent = ProductionDataIntakeAgent
IntakeAgent = ProductionDataIntakeAgent

__all__ = [
    "ProductionDataIntakeAgent",
    "DataIntakeAgent",
    "IntakeAgent",
    "data_intake_agent",
    "intake_agent",
    "get_groq_client",
    "set_groq_client",
    "reset_groq_client",
]

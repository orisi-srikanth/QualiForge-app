"""
Knowledge Base Alignment & Enrichment Script for QualityMind
Aligns all visual defects to MVTec AD unified defect types (surface_scratch, dent_deformation,
incorrect_assembly, surface_contamination, thread_damage, missing_component, insulation_or_wire_damage).
Adds 14 new proxy-part visual NCRs with confirmed root causes and decoys.
Adds SOP-055 Visual Inspection Procedure and NIST/SEMATECH SPC public reference.
Enforces data_provenance ('synthetic_illustrative' vs 'public_reference') on all records.
"""
import os
import json
import csv
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
KB_DIR = PROJECT_ROOT / "backend" / "data" / "kb"
ROOT_DATA_DIR = PROJECT_ROOT / "data"
BACKEND_DATA_DIR = PROJECT_ROOT / "backend" / "data"

NEW_NCRS = [
    {
        "id": "NCR-140",
        "title": "Surface scratch defects on metal nut flange caused by abrasive unloader gripper wear",
        "defect_type": "surface_scratch",
        "defect_family": "surface_defect",
        "proxy_category": "metal_nut",
        "part_number": "NUT-HEX-M12",
        "machine": "CNC-02",
        "description": "Visual inspection flagged circumferential and longitudinal linear scratches along the bearing face of hexagonal flange metal nuts. Anomaly score 0.88, localized ROI on upper flange rim.",
        "confirmed_root_cause": "Hard carbide swarf embedded in the polyurethane lining of the automated unloader robot gripper fingers, creating repetitive scoring during part extraction.",
        "resolution": "Replaced polyurethane gripper pads with hardened brass jaws, installed automated high-pressure air blow-off nozzle to clear swarf prior to grip, and updated daily maintenance checklist.",
        "containment_action": "Quarantine 180 units from Lot L-2026-941; optical sorting station verified conforming units.",
        "date": "2026-08-10",
        "data_provenance": "synthetic_illustrative"
    },
    {
        "id": "NCR-141",
        "title": "Decoy: Surface scratches on metal nut from conveyor chute vibration friction",
        "defect_type": "surface_scratch",
        "defect_family": "surface_defect",
        "proxy_category": "metal_nut",
        "part_number": "NUT-HEX-M12",
        "machine": "CNC-03",
        "description": "Superficial scratches observed on outer hexagonal flats of metal nuts following gravity feed transition. Symptoms mimic unloader gripper abrasion.",
        "confirmed_root_cause": "Decoy investigation: Grippers inspected and verified clean. Root cause confirmed as excessive slope and lack of UHMW wear lining on the inter-stage gravity chute causing parts to tumble against sheet metal welds.",
        "resolution": "Installed smooth UHMW polyethylene chute liners and reduced slide inclination from 35 degrees to 18 degrees to eliminate tumbling impact.",
        "containment_action": "100% visual screening; polish rework acceptable for non-critical non-flange surfaces.",
        "date": "2026-08-14",
        "data_provenance": "synthetic_illustrative"
    },
    {
        "id": "NCR-142",
        "title": "Dent deformation on metal nut rim from vibratory bowl feeder drop height",
        "defect_type": "dent_deformation",
        "defect_family": "geometric_deformation",
        "proxy_category": "metal_nut",
        "part_number": "NUT-HEX-M12",
        "machine": "FEEDER-BOWL-01",
        "description": "Visual inspection identified localized edge dents and crater indentations on hexagonal flange corners. Average dent depth 0.25 mm exceeding visual aesthetic criteria.",
        "confirmed_root_cause": "Drop height from primary bulk hopper vibratory track to orientation spiral bowl was 450 mm without dampening baffle, causing metal-to-metal impact denting on case-hardened blanks.",
        "resolution": "Installed stepped urethane cascade baffles to limit free-fall distance to < 80 mm and adjusted vibratory hopper feed rate sensor.",
        "containment_action": "Quarantine 320 raw blanks; sort by optical profile projector.",
        "date": "2026-08-18",
        "data_provenance": "synthetic_illustrative"
    },
    {
        "id": "NCR-143",
        "title": "Decoy: Dent deformation on transistor heat sink case from pneumatic ejector over-pressure",
        "defect_type": "dent_deformation",
        "defect_family": "geometric_deformation",
        "proxy_category": "transistor",
        "part_number": "TR-TO220-40A",
        "machine": "FORMING-PRESS-02",
        "description": "Localized impact indentation observed on the copper mounting flange of TO-220 power transistor packages. Symptoms resemble hopper drop damage.",
        "confirmed_root_cause": "Decoy investigation: Bulk feeding chutes are foam-padded. Root cause confirmed as pneumatic parts-ejector cylinder air regulator failure, operating at 7.2 bar instead of specified 2.5 bar, driving parts against the metal catch bin.",
        "resolution": "Replaced failed pressure regulator with lockable precision regulator set to 2.2 bar and added low-bounce silicone catch tray.",
        "containment_action": "Quarantined 250 transistor units; 100% co-planarity gauge check of mounting tabs.",
        "date": "2026-08-22",
        "data_provenance": "synthetic_illustrative"
    },
    {
        "id": "NCR-144",
        "title": "Incorrect assembly: Inverted orientation of flange nuts in automated tapping fixture",
        "defect_type": "incorrect_assembly",
        "defect_family": "assembly_error",
        "proxy_category": "metal_nut",
        "part_number": "NUT-HEX-M12",
        "machine": "TAP-AUTO-01",
        "description": "Vision sensor detected inverted part orientation (flange facing downward rather than upward) entering the thread tapping spindle nest.",
        "confirmed_root_cause": "Optical orientation sensor reflector obscured by coolant mist deposits, failing to trigger the pneumatic rejection gate for upside-down parts.",
        "resolution": "Installed positive air-purge curtain over orientation sensor optic lens and added secondary mechanical mechanical poke-yoke orientation keyway.",
        "containment_action": "Machine immediately interlocked; automated station purged of 45 parts in buffer.",
        "date": "2026-08-28",
        "data_provenance": "synthetic_illustrative"
    },
    {
        "id": "NCR-145",
        "title": "Incorrect assembly: Pin terminal wire swap on multi-conductor cable harness",
        "defect_type": "incorrect_assembly",
        "defect_family": "assembly_error",
        "proxy_category": "cable",
        "part_number": "CAB-IND-HARN-04",
        "machine": "HARNESS-JIG-03",
        "description": "Visual inspection identified swapped colored wire conductors (blue pin 3 and green pin 4 reversed) in 6-pin connector housing.",
        "confirmed_root_cause": "Wire harness assembly board routing guide peg for pin 3 was bent, leading assembly operator to misroute conductor into adjacent terminal guide slot.",
        "resolution": "Replaced aluminum guide pegs with hardened steel keyed pins and implemented optical color-sequencing camera verification prior to connector latching.",
        "containment_action": "100% electrical continuity and pinout test on all 65 harnesses in active production lot.",
        "date": "2026-09-02",
        "data_provenance": "synthetic_illustrative"
    },
    {
        "id": "NCR-146",
        "title": "Surface contamination: Dark alkaline wash residue and blotches on metal nut finish",
        "defect_type": "surface_contamination",
        "defect_family": "surface_defect",
        "proxy_category": "metal_nut",
        "part_number": "NUT-HEX-M12",
        "machine": "WASH-LINE-01",
        "description": "Visual inspection detected irregular brown and amber surface discoloration staining across bearing faces of machined metal nuts.",
        "confirmed_root_cause": "Part-washing station rinse nozzle clogged with calcium scale, leaving concentrated alkaline cleaning detergent residue that baked onto parts during hot-air drying.",
        "resolution": "Descale wash and rinse manifolds, replace spray nozzles with quick-release stainless tips, and install automated pH rinse water conductivity monitor.",
        "containment_action": "Reworked 410 stained parts through ultra-pure ultrasonic DI water bath with zero dimensional change.",
        "date": "2026-09-06",
        "data_provenance": "synthetic_illustrative"
    },
    {
        "id": "NCR-147",
        "title": "Decoy: Surface contamination discoloration from oxidized rust preventive oil bath",
        "defect_type": "surface_contamination",
        "defect_family": "surface_defect",
        "proxy_category": "metal_nut",
        "part_number": "NUT-HEX-M12",
        "machine": "DIP-TANK-02",
        "description": "Mottled yellowish discoloration on parts exiting preservation line. Visual appearance resembles alkaline rinse burn.",
        "confirmed_root_cause": "Decoy investigation: Washer nozzles confirmed clear and rinse pH normal (7.1). Root cause identified as rust preventive oil tank temperature controller exceeding 65C (setpoint: 40C), causing thermal oil oxidation.",
        "resolution": "Replaced faulty RTD temperature thermocouple, flushed oil tank, and introduced dual-redundant thermal cut-off relay.",
        "containment_action": "Quarantine 150 packaged boxes; degrease and re-apply fresh corrosion inhibitor.",
        "date": "2026-09-11",
        "data_provenance": "synthetic_illustrative"
    },
    {
        "id": "NCR-148",
        "title": "Thread damage: Flattened thread crests and torn lead on precision fastener screws",
        "defect_type": "thread_damage",
        "defect_family": "machining_defect",
        "proxy_category": "screw",
        "part_number": "SCR-HEX-M8X40",
        "machine": "THREAD-ROLLER-01",
        "description": "Visual inspection identified flattened thread ridges and micro-tears along top 4 threads of M8 fastener screws. Pitch gauge indicated crest truncation.",
        "confirmed_root_cause": "Thread rolling die reached 82,000 cycles without scheduled regrind (limit: 75,000 cycles). Die profile wear caused insufficient penetration into blank root diameter.",
        "resolution": "Replaced cylindrical rolling dies with matched Kennametal carbide set, re-calibrated center distance gauge, and set PLC cycle counter alarm to 70,000 cycles.",
        "containment_action": "Scrapped 85 non-repairable threaded screws; quarantined lot for 100% Go/No-Go ring gauge testing.",
        "date": "2026-09-15",
        "data_provenance": "synthetic_illustrative"
    },
    {
        "id": "NCR-149",
        "title": "Decoy: Thread damage caused by undersized blank chamfer angle rather than die wear",
        "defect_type": "thread_damage",
        "defect_family": "machining_defect",
        "proxy_category": "screw",
        "part_number": "SCR-HEX-M8X40",
        "machine": "THREAD-ROLLER-02",
        "description": "Torn lead threads on screw tips following thread rolling. Die condition was suspected initially.",
        "confirmed_root_cause": "Decoy investigation: Thread rolling dies were new (< 5,000 cycles). Root cause traced upstream to CNC cold header blank cutting tool, which produced a 15-degree lead chamfer instead of the 45-degree specified chamfer.",
        "resolution": "Re-ground header chamfer tooling insert to 45 degrees +/- 1 degree and added optical shadowgraph inspection at blanking station.",
        "containment_action": "Quarantined 600 header blanks prior to rolling; sorted rolled parts.",
        "date": "2026-09-19",
        "data_provenance": "synthetic_illustrative"
    },
    {
        "id": "NCR-150",
        "title": "Missing component: Cut and missing gate lead pin on power transistor package",
        "defect_type": "missing_component",
        "defect_family": "component_integrity",
        "proxy_category": "transistor",
        "part_number": "TR-TO220-40A",
        "machine": "LEAD-TRIM-01",
        "description": "Visual inspection flagged missing gate pin (pin 1) on TO-220 transistor package. Anomaly score 0.94; lead completely absent from terminal body.",
        "confirmed_root_cause": "Shear blade edge chipped on lead forming die station 1, causing excessive tensile fracture that tore the lead flush with the molded epoxy casing.",
        "resolution": "Replaced shear blade punch assembly, reduced shear clearance to 0.02 mm, and added acoustic emission impact sensor to detect tooling notch chips.",
        "containment_action": "Quarantined 450 units from reel #R-8821; automated vision reel sorter rejected 12 defective components.",
        "date": "2026-09-24",
        "data_provenance": "synthetic_illustrative"
    },
    {
        "id": "NCR-151",
        "title": "Missing component: Missing conductor core wire in multi-strand industrial cable",
        "defect_type": "missing_component",
        "defect_family": "component_integrity",
        "proxy_category": "cable",
        "part_number": "CAB-IND-HARN-04",
        "machine": "AUTO-STRIP-02",
        "description": "Visual camera detected only 3 insulated conductors entering breakout gland instead of required 4-conductor specification.",
        "confirmed_root_cause": "Upstream cable reel splice joint had broken conductor wire that went undetected during outer jacket extruding.",
        "resolution": "Integrated high-frequency spark tester and magnetic inductive wire counter on jacket extrusion line.",
        "containment_action": "Quarantined reel batch; segmented and rejected 15 meters of defective cable run.",
        "date": "2026-09-28",
        "data_provenance": "synthetic_illustrative"
    },
    {
        "id": "NCR-152",
        "title": "Insulation damage: Punctured PVC outer insulation jacket on wiring harness",
        "defect_type": "insulation_or_wire_damage",
        "defect_family": "insulation_damage",
        "proxy_category": "cable",
        "part_number": "CAB-IND-HARN-04",
        "machine": "STRIP-CRIMP-01",
        "description": "Visual inspection identified puncture marks and jacket tears exposing internal copper braiding on multi-conductor harness. Anomaly score 0.91.",
        "confirmed_root_cause": "Automatic stripping blade depth micrometer zero-shift error (+0.35 mm depth excess) penetrating both outer sheath and primary conductor dielectric.",
        "resolution": "Calibrated stripping machine servo depth stop, implemented optical laser micrometer verification of stripped length and cut depth.",
        "containment_action": "Quarantine 120 assemblies; dielectric withstand test (Hi-Pot 1500V AC) applied to adjacent lots.",
        "date": "2026-10-02",
        "data_provenance": "synthetic_illustrative"
    },
    {
        "id": "NCR-153",
        "title": "Decoy: Wire insulation scoring from sharp grommet edge during bundle routing",
        "defect_type": "insulation_or_wire_damage",
        "defect_family": "insulation_damage",
        "proxy_category": "cable",
        "part_number": "CAB-IND-HARN-04",
        "machine": "ROUTING-BENCH-04",
        "description": "Surface scoring along outer cable jacket resembling automated stripper blade nicking.",
        "confirmed_root_cause": "Decoy investigation: Stripping machines verified calibrated. Root cause determined to be metal chassis passthrough grommet missing its nylon split-sleeve collar, scraping harness during manual bundle pull.",
        "resolution": "Installed captive snap-in protective nylon edge grommets on all assembly jigs and updated harness routing SOP.",
        "containment_action": "Inspected 50 completed harnesses; replaced damaged protective jackets.",
        "date": "2026-10-05",
        "data_provenance": "synthetic_illustrative"
    }
]

VISUAL_INSPECTION_PROCEDURE_MD = """# Standard Operating Procedure: Visual Inspection and AI Decision Review
- **Document ID:** SOP-055
- **Title:** Visual Defect Review, Model Confidence Thresholds, and Disposition Protocol
- **Version:** 2.0.0
- **Effective Date:** 2026-10-11
- **Data Provenance:** synthetic_illustrative

## 1. Purpose and Scope
This procedure specifies how automated computer vision inspection predictions (PatchCore Stage A anomaly localization and MobileNetV3 Stage B unified defect classification) are evaluated, confirmed, or escalated by Quality Engineers. Applies to proxy parts (screws, nuts, transistors, wiring harnesses) and machined shaft surface inspection.

## 2. Confidence Thresholds and Operational Routing
1. **Conforming Classification (no_defect):**
   - Anomaly score strictly below category threshold (e.g. < 0.65 for metal_nut).
   - Component automatically marked conforming for visual criteria and released to downstream operations.
2. **Confident Defect Identification (>= 0.70 Confidence):**
   - Model outputs defect classification, localized bounding box ROI, and heatmap overlay.
   - Component flagged for secondary visual engineering confirmation on the inspection console.
3. **Uncertain Prediction (< 0.70 Confidence):**
   - Model flags result as `uncertain`.
   - Automatic line stop or quarantine diverter routes component to the Human-in-the-Loop Quality Station.
4. **Out-of-Domain Classification (`out_of_domain`):**
   - If optical profile matches none of the recognized categories (metal_nut, screw, transistor, cable, precision_shaft), model outputs `out_of_domain`.
   - Requires manual metrology bench verification.

## 3. Human Quality Engineer Confirmation Protocol
Quality Engineers must review the multi-panel console display (Raw Surface, Model Overlay, PatchCore Heatmap):
- **Confirm Defect:** If physical inspection verifies visible discontinuity matching model ROI, engineer clicks `Confirm Defect`, generating an electronic Nonconformance Record (NCR).
- **Reject (False Positive):** If benign surface feature (e.g. washable lint, permissible reflection gradient) triggered false alarm, engineer records rejection rationale and releases component.

## 4. Disallowed Defect Classes
Cracks are explicitly unsupported in the proxy part dataset categories. All visual quality defects must conform strictly to the seven unified classes defined in `mvtec_label_map.yaml`.
"""

NIST_SPC_REF_MD = """# Reference Standard: Statistical Process Control & Capability Assessment
- **Document ID:** REF-NIST-SPC-01
- **Title:** NIST/SEMATECH e-Handbook of Statistical Methods - Control Charts and Process Capability
- **Source Citation:** NIST/SEMATECH e-Handbook of Statistical Methods, Section 6.3 (Statistical Process Control), https://www.itl.nist.gov/div898/handbook/pmc/section3/pmc3.htm
- **Data Provenance:** public_reference

## 1. Control Chart Methodology
Process stability is assessed using Shewhart variable control charts (X-bar and R / S charts):
- Upper Control Limit (UCL) = Mean + 3 * (sigma / sqrt(n))
- Lower Control Limit (LCL) = Mean - 3 * (sigma / sqrt(n))
A process is deemed statistically out of control if any observation violates the Western Electric Rules (e.g. 1 point beyond Zone A 3-sigma, or 9 consecutive points on one side of center line).

## 2. Process Capability Indices (Cp and Cpk)
- **Potential Capability (Cp):** Cp = (USL - LSL) / (6 * sigma)
- **Demonstrated Capability (Cpk):** Cpk = min((USL - Mean) / (3 * sigma), (Mean - LSL) / (3 * sigma))
For automotive and precision manufacturing (IATF 16949), processes must achieve Cpk >= 1.33 (capable) or Cpk >= 1.67 (critical characteristics).

## 3. Small-Sample Warning
When subgroup size or sample count is limited (N < 30), standard capability indices exhibit wide confidence intervals; calculated values must carry explicit small-sample uncertainty disclaimers.
"""

def update_kb():
    os.makedirs(KB_DIR, exist_ok=True)
    os.makedirs(BACKEND_DATA_DIR / "knowledge_docs", exist_ok=True)
    os.makedirs(ROOT_DATA_DIR / "knowledge_docs", exist_ok=True)

    # 1. Write SOP-055 and NIST Reference
    sop_path = KB_DIR / "SOP-055_Visual_Inspection_Procedure.md"
    with open(sop_path, "w", encoding="utf-8") as f:
        f.write(VISUAL_INSPECTION_PROCEDURE_MD.strip() + "\n")
    with open(BACKEND_DATA_DIR / "knowledge_docs" / "SOP-055_Visual_Inspection_Procedure.md", "w", encoding="utf-8") as f:
        f.write(VISUAL_INSPECTION_PROCEDURE_MD.strip() + "\n")

    nist_path = KB_DIR / "REF-NIST-SPC_Statistical_Process_Control_Handbook.md"
    with open(nist_path, "w", encoding="utf-8") as f:
        f.write(NIST_SPC_REF_MD.strip() + "\n")
    with open(BACKEND_DATA_DIR / "knowledge_docs" / "REF-NIST-SPC_Statistical_Process_Control_Handbook.md", "w", encoding="utf-8") as f:
        f.write(NIST_SPC_REF_MD.strip() + "\n")

    # 2. Write 14 new NCR Markdown files
    for ncr in NEW_NCRS:
        md_content = f"""# Nonconformance Report: {ncr['id']}
- **Title:** {ncr['title']}
- **Date:** {ncr['date']}
- **Part Number:** {ncr['part_number']}
- **Proxy Category:** {ncr['proxy_category']}
- **Machine:** {ncr['machine']}
- **Defect Classification:** {ncr['defect_type']}
- **Defect Family:** {ncr['defect_family']}
- **Data Provenance:** {ncr['data_provenance']}
- **Incident Description:** {ncr['description']}
- **Confirmed Root Cause:** {ncr['confirmed_root_cause']}
- **Corrective Resolution:** {ncr['resolution']}
- **Containment Action:** {ncr['containment_action']}
- **Epistemic Classification:** CONFIRMED_ROOT_CAUSE (Approved by Lead Quality Engineer)
"""
        with open(KB_DIR / f"{ncr['id']}.md", "w", encoding="utf-8") as f:
            f.write(md_content)

    # 3. Update existing KB files to add data_provenance if missing
    for fname in os.listdir(KB_DIR):
        if fname.endswith(".md"):
            fpath = KB_DIR / fname
            with open(fpath, "r", encoding="utf-8") as f:
                content = f.read()
            if "data_provenance" not in content.lower():
                # Add data_provenance after title or first header
                lines = content.split("\n")
                new_lines = []
                added = False
                for line in lines:
                    new_lines.append(line)
                    if line.startswith("# ") and not added:
                        new_lines.append("- **Data Provenance:** synthetic_illustrative")
                        added = True
                with open(fpath, "w", encoding="utf-8") as f:
                    f.write("\n".join(new_lines))

    # 4. Update historical_ncrs.json
    ncr_json_path = BACKEND_DATA_DIR / "historical_ncrs.json"
    ncrs = []
    if ncr_json_path.exists():
        with open(ncr_json_path, "r", encoding="utf-8") as f:
            ncrs = json.load(f)

    # Add data_provenance to existing records
    for item in ncrs:
        if "data_provenance" not in item:
            item["data_provenance"] = "synthetic_illustrative"
        if "proxy_category" not in item:
            item["proxy_category"] = "none"

    # Merge new NCRs if not already present
    existing_ids = {n["id"] for n in ncrs}
    for ncr in NEW_NCRS:
        if ncr["id"] not in existing_ids:
            ncrs.append({
                "id": ncr["id"],
                "title": ncr["title"],
                "defect_type": ncr["defect_type"],
                "defect_family": ncr["defect_family"],
                "proxy_category": ncr["proxy_category"],
                "part_number": ncr["part_number"],
                "machine": ncr["machine"],
                "description": ncr["description"],
                "confirmed_root_cause": ncr["confirmed_root_cause"],
                "resolution": ncr["resolution"],
                "date": ncr["date"],
                "data_provenance": ncr["data_provenance"]
            })

    with open(ncr_json_path, "w", encoding="utf-8") as f:
        json.dump(ncrs, f, indent=2)

    # Mirror to root data if needed
    with open(ROOT_DATA_DIR / "historical_ncrs.json", "w", encoding="utf-8") as f:
        json.dump(ncrs, f, indent=2)

    # 5. Update historical_ncrs.csv
    csv_path = BACKEND_DATA_DIR / "historical_ncrs.csv"
    existing_rows = []
    if csv_path.exists():
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            existing_rows = list(reader)

    csv_ids = {r["record_id"] for r in existing_rows}
    for ncr in NEW_NCRS:
        if ncr["id"] not in csv_ids:
            existing_rows.append({
                "record_id": ncr["id"],
                "date": ncr["date"],
                "part_number": ncr["part_number"],
                "machine_id": ncr["machine"],
                "batch_id": f"BATCH-{ncr['id'].replace('NCR-', 'V')}",
                "defect_type": ncr["defect_type"],
                "measured_dimension": "N/A (Visual)",
                "nominal_specification": "Visual Conformance (Zero Defect)",
                "description": ncr["description"],
                "root_cause_category": ncr["defect_family"],
                "confirmed_root_cause": ncr["confirmed_root_cause"],
                "containment_action": ncr["containment_action"],
                "corrective_action": ncr["resolution"],
                "preventive_action": "Inspection camera re-calibration; tooling wear limit lock.",
                "effectiveness_result": "Zero recurring defects observed in next 10 production lots.",
                "severity": "Medium",
                "status": "CLOSED"
            })

    if existing_rows:
        fieldnames = list(existing_rows[0].keys())
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(existing_rows)

        with open(ROOT_DATA_DIR / "historical_ncrs.csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(existing_rows)

    print(f"Updated KB in {KB_DIR} (Total files: {len(os.listdir(KB_DIR))}).")
    print(f"Updated historical_ncrs.json (Total records: {len(ncrs)}).")
    print(f"Updated historical_ncrs.csv (Total records: {len(existing_rows)}).")

if __name__ == "__main__":
    update_kb()

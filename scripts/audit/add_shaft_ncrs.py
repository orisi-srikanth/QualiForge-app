import json
import csv
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
BACKEND_KB_DIR = PROJECT_ROOT / "backend" / "data" / "kb"

NEW_SHAFT_NCRS = [
    {
        "id": "NCR-154",
        "title": "Surface impact dent on cylindrical shaft body during automated gantry transfer",
        "defect_type": "dent",
        "defect_family": "geometric_deformation",
        "proxy_category": "precision_shaft",
        "part_number": "PS-2026-101",
        "machine": "GANTRY-TRANSFER-01",
        "description": "Visual inspection identified localized impact crater and depression dent on outer diameter of AISI 1045 precision shaft. Depth measured at 0.18 mm exceeding visual cosmetic acceptance limit.",
        "confirmed_root_cause": "Robotic gantry pick-and-place gripper deceleration curve profile was misconfigured in servo drive, causing part to strike intermediate transfer V-block during high-speed cycle.",
        "resolution": "Updated servo motion deceleration profile with S-curve smoothing, installed urethane buffer padding on V-block staging nest, and added optical seating sensor.",
        "containment_action": "Quarantine 120 shafts from Batch BATCH-0245; 100% dial indicator inspection.",
        "date": "2026-10-01",
        "data_provenance": "synthetic_illustrative"
    },
    {
        "id": "NCR-155",
        "title": "Transverse hairline thermal crack on shaft step shoulder fillet from excessive plunge grinding infeed",
        "defect_type": "crack",
        "defect_family": "metallurgical_fracture",
        "proxy_category": "precision_shaft",
        "part_number": "PS-2026-101",
        "machine": "GRIND-01",
        "description": "Automated vision inspection flagged transverse hairline crack propagating across bearing transition fillet of precision ground shaft. Dye penetrant check confirmed stress micro-crack.",
        "confirmed_root_cause": "Cylindrical plunge grinder infeed rate was set to 0.045 mm/sec instead of specified 0.020 mm/sec, combined with glazed CBN wheel surface causing localized thermal temper burn and tensile residual stress cracking.",
        "resolution": "Dressed and balanced CBN grinding wheel, reduced rough infeed rate to 0.018 mm/sec, and increased high-pressure coolant flow directly onto grinding zone.",
        "containment_action": "100% eddy-current crack detection screening on all 85 pieces ground during shift.",
        "date": "2026-10-03",
        "data_provenance": "synthetic_illustrative"
    },
    {
        "id": "NCR-156",
        "title": "Missing milled keyway pocket on PS-2026-101 shaft due to CNC milling sub-routine call omission",
        "defect_type": "missing_feature",
        "defect_family": "machining_omission",
        "proxy_category": "precision_shaft",
        "part_number": "PS-2026-101",
        "machine": "CNC-02",
        "description": "Visual inspection detected complete absence of milled keyway slot on central body section of precision shaft. Surface remained unmachined cylindrical blank profile.",
        "confirmed_root_cause": "NC part program edit by night shift operator inadvertently commented out sub-program call M98 P2001 (keyway milling cycle) following tool offset adjustment.",
        "resolution": "Locked CNC controller program memory with supervisor password, installed macro verification interlock checking tool cycle completion before part unclamp, and restored validated NC code.",
        "containment_action": "Quarantined 42 parts; routed through secondary milling fixture to machine required keyway.",
        "date": "2026-10-05",
        "data_provenance": "synthetic_illustrative"
    },
    {
        "id": "NCR-157",
        "title": "Misplaced retaining collar assembled 55mm into shaft main body instead of shoulder datum",
        "defect_type": "incorrect_assembly",
        "defect_family": "assembly_error",
        "proxy_category": "precision_shaft",
        "part_number": "PS-2026-101",
        "machine": "ASSY-PRESS-01",
        "description": "Vision sensor detected retaining collar positioned 55 mm along the cylindrical body instead of flush seated against the left journal shoulder datum.",
        "confirmed_root_cause": "Assembly press axial stop cylinder linear scale feedback cable had loose connector, causing press ram to halt prematurely 55 mm short of mechanical positive stop.",
        "resolution": "Replaced linear encoder connector with IP67 sealed M12 connector, calibrated press stop distance with dial gauge, and added optical proximity sensor verifying collar seating.",
        "containment_action": "Disassembled 18 incorrectly positioned collars using hydraulic puller; inspected shaft journal for galling.",
        "date": "2026-10-08",
        "data_provenance": "synthetic_illustrative"
    },
    {
        "id": "NCR-158",
        "title": "Longitudinal surface scratches on precision shaft journal from swarf chips in coolant nozzle",
        "defect_type": "surface_scratch",
        "defect_family": "surface_defect",
        "proxy_category": "precision_shaft",
        "part_number": "PS-2026-101",
        "machine": "CNC-04",
        "description": "Visual inspection flagged longitudinal linear scratches along finish turned journal face. Average scratch depth 0.012 mm exceeding Ra 0.8 um surface finish specification.",
        "confirmed_root_cause": "Coolant filtration bag tore, allowing recirculating steel chips to lodge between wiping pad and rotating shaft workpiece during finish turning pass.",
        "resolution": "Installed 10-micron magnetic chip separator upstream of coolant tank, replaced torn filter bag, and upgraded wiper pads to wear-resistant polyurethane.",
        "containment_action": "Quarantine 60 units from lot; polish rework qualified on centerless polishing lathe.",
        "date": "2026-10-10",
        "data_provenance": "synthetic_illustrative"
    }
]

def update_ncrs():
    for base in [PROJECT_ROOT / "backend" / "data", PROJECT_ROOT / "data"]:
        ncr_json_path = base / "historical_ncrs.json"
        ncr_csv_path = base / "historical_ncrs.csv"

        with open(ncr_json_path, "r", encoding="utf-8") as f:
            existing_ncrs = json.load(f)

        existing_ids = {n["id"] for n in existing_ncrs}
        for new_ncr in NEW_SHAFT_NCRS:
            if new_ncr["id"] not in existing_ids:
                existing_ncrs.append(new_ncr)

        with open(ncr_json_path, "w", encoding="utf-8") as f:
            json.dump(existing_ncrs, f, indent=2)

        import pandas as pd
        df = pd.DataFrame(existing_ncrs)
        df.to_csv(ncr_csv_path, index=False)
        print(f"Updated {ncr_json_path} and {ncr_csv_path}: Total {len(existing_ncrs)} records.")

    # Write Markdown documents in backend/data/kb/
    for ncr in NEW_SHAFT_NCRS:
        md_path = BACKEND_KB_DIR / f"{ncr['id']}.md"
        content = f"""# Nonconformance Report: {ncr['id']}
- **Title:** {ncr['title']}
- **Defect Type:** {ncr['defect_type']}
- **Defect Family:** {ncr['defect_family']}
- **Part Number:** {ncr['part_number']}
- **Machine:** {ncr['machine']}
- **Date:** {ncr['date']}
- **Data Provenance:** {ncr['data_provenance']}

## Description
{ncr['description']}

## Confirmed Root Cause
{ncr['confirmed_root_cause']}

## Resolution & Corrective Action
{ncr['resolution']}

## Containment Action
{ncr['containment_action']}
"""
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Wrote KB doc: {md_path.name}")

if __name__ == "__main__":
    update_ncrs()

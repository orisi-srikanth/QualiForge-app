import sys
sys.path.insert(0, ".")
import json
import sqlite3
import pypdf
from backend.app.services.pdf_report import generate_quality_pdf_report

conn = sqlite3.connect('backend/data/quality_system.db')
c = conn.cursor()
c.execute("SELECT state_json FROM workflow_state WHERE workflow_id='WF-C038A990'")
row = c.fetchone()
if not row:
    print("Workflow WF-C038A990 not found!")
    exit(1)

state = json.loads(row[0])
print(f"Loaded workflow WF-C038A990. Has visual prediction: {state.get('visual_prediction') is not None}")

pdf_bytes = generate_quality_pdf_report(state)
out_path = "scripts/report_WF-C038A990.pdf"
with open(out_path, "wb") as f:
    f.write(pdf_bytes)

print(f"Generated PDF with {len(pdf_bytes)} bytes at {out_path}")

# Inspect with pypdf
reader = pypdf.PdfReader(out_path)
print(f"Total Pages: {len(reader.pages)}")

full_text = ""
for i, page in enumerate(reader.pages):
    page_text = page.extract_text() or ""
    print(f"\n--- PAGE {i+1} ({len(page_text)} chars) ---")
    full_text += f"\n[PAGE {i+1}]\n" + page_text

sections = [
    ("1. Product details", ["1. Product Details", "Part Number:", "Nominal Diameter:", "Tolerance Band:"]),
    ("2. Batch information", ["2. Batch Information", "Batch ID:", "Machine Assigned:", "Quantity Produced:"]),
    ("3. Inspection summary", ["3. Inspection Summary", "Total Sample Inspected:", "Conforming:", "Non-conforming:"]),
    ("4. Visual-inspection results", ["4. Visual Inspection Results", "Vision Architecture:", "surface_scratch", "Confidence:"]),
    ("5. Dimensional analysis", ["5. Dimensional Analysis", "Measured Diameter", "Conformance", "OBSERVED_FACT"]),
    ("6. SPC analysis", ["6. Statistical Process Control", "Process Mean", "Upper Control Limit", "Cp", "Cpk"]),
    ("7. Process anomalies", ["7. Process Anomalies", "Machine Vibration", "Tool Cycles", "Spindle Speed"]),
    ("8. Root-cause hypotheses", ["8. Root Cause Hypotheses", "Hypothesis Title", "6M Category", "Score"]),
    ("9. Supporting evidence", ["9. Supporting & Contradicting Evidence", "Primary Hypothesis", "Supporting Evidence:"]),
    ("10. Containment actions", ["10. Containment Actions", "Action ID", "Containment Action", "Responsible Role"]),
    ("11. Corrective/preventive actions", ["11. Corrective & Preventive Actions", "Action ID", "Type", "Due Date"]),
    ("12. Human approval", ["12. Human Quality Approval", "Critic Audit Status:", "Authorized Signoff:", "Batch Disposition:"]),
    ("13. Effectiveness monitoring", ["13. Effectiveness Monitoring", "Before Intervention", "After Intervention", "Two-Proportion Z-Test"])
]

all_passed = True
for name, keywords in sections:
    found = all(kw.lower() in full_text.lower() for kw in keywords)
    status = "PASS" if found else "FAIL"
    print(f"[{status}] Section: {name}")
    if not found:
        all_passed = False
        missing = [kw for kw in keywords if kw.lower() not in full_text.lower()]
        print(f"    Missing keywords: {missing}")

print("\nAll 13 sections passed:", all_passed)

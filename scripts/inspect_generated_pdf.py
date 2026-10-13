import urllib.request
import os
import pypdf

# 1. Download the PDF
url = "http://localhost:8000/api/reports/pdf?batch_id=BATCH-0245"
pdf_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "downloaded_report.pdf"))

print(f"Downloading PDF from {url}...")
with urllib.request.urlopen(url) as resp:
    data = resp.read()
    with open(pdf_path, "wb") as f:
        f.write(data)

print(f"Downloaded {len(data)} bytes to {pdf_path}")

# 2. Inspect with pypdf
reader = pypdf.PdfReader(pdf_path)
num_pages = len(reader.pages)
print(f"Total Pages: {num_pages}")

full_text = ""
for i, page in enumerate(reader.pages):
    page_text = page.extract_text() or ""
    print(f"\n--- PAGE {i+1} ({len(page_text)} chars) ---")
    print(page_text[:400] + ("..." if len(page_text) > 400 else ""))
    full_text += f"\n[PAGE {i+1}]\n" + page_text

print("\n" + "="*50)
print("=== VERIFYING THE 13 REQUIRED SECTIONS ===")
print("="*50)

sections = [
    ("1. Product details", ["1. Product Details", "Part Number:", "Nominal Diameter:", "Tolerance Band:"]),
    ("2. Batch information", ["2. Batch Information", "Batch ID:", "Machine Assigned:", "Quantity Produced:"]),
    ("3. Inspection summary", ["3. Inspection Summary", "Total Sample Inspected:", "Conforming:", "Non-conforming:"]),
    ("4. Visual-inspection results", ["4. Visual Inspection Results", "Vision Architecture:", "Defect"]),
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

for name, keywords in sections:
    found = all(kw.lower() in full_text.lower() for kw in keywords)
    status = "PASS" if found else "FAIL"
    print(f"[{status}] Section: {name}")
    if not found:
        missing = [kw for kw in keywords if kw.lower() not in full_text.lower()]
        print(f"    Missing keywords: {missing}")

import urllib.request
import io
from pypdf import PdfReader

def check_pdf():
    url = "http://localhost:8000/api/reports/pdf?batch_id=BATCH-0245"
    req = urllib.request.urlopen(url)
    pdf_bytes = req.read()
    reader = PdfReader(io.BytesIO(pdf_bytes))
    print(f"Total Pages: {len(reader.pages)}")
    
    pages_text = []
    for i, page in enumerate(reader.pages):
        txt = page.extract_text()
        pages_text.append(txt)
        has_footer = "Decision-support only. Final product disposition is a human decision." in txt
        print(f"Page {i+1} disclaimer footer present: {has_footer}")

    full_text = "\n".join(pages_text)

    checks = [
        "1. Product Details [OBSERVED_FACT]",
        "2. Batch Information [OBSERVED_FACT]",
        "3. Inspection Summary [OBSERVED_FACT]",
        "4. Visual Inspection Results [MODEL_PREDICTION]",
        "5. Dimensional Analysis [OBSERVED_FACT]",
        "6. Statistical Process Control (SPC) Analysis [STATISTICAL_FINDING]",
        "7. Process Anomalies & Machine Telemetry [STATISTICAL_FINDING]",
        "8. Root Cause Hypotheses [HYPOTHESIS]",
        "9. Supporting & Contradicting Evidence Breakdown [HYPOTHESIS]",
        "10. Containment Actions",
        "11. Corrective & Preventive Actions",
        "12. Human Quality Approval [CONFIRMED_ROOT_CAUSE]",
        "13. Effectiveness Monitoring [STATISTICAL_FINDING]",
        "MANDATORY AUDIT GOVERNANCE & EPISTEMIC LABELS",
        "REQUIRES ENGINEERING VERIFICATION",
        "Decision-support only. Final product disposition is a human decision."
    ]

    print("\nSection & Governance Verifications:")
    for c in checks:
        status = "FOUND" if c in full_text else "NOT FOUND"
        print(f"  {c} -> {status}")

if __name__ == "__main__":
    check_pdf()

"""
Independent V&V Master Audit Runner for QualityMind.
Runs all independent verifiers and regression test suites.
Exits with code 0 ONLY if 100% of all audit checks and tests pass.
Exits with non-zero code on any single failure.
"""

import sys
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent

CHECKS = [
    ("1. MVTec AD Real Dataset Disk & Manifest Integrity", [sys.executable, "scripts/audit/verify_mvtec_dataset.py"]),
    ("2. Deterministic Mathematical Formulas & Golden Values", [sys.executable, "scripts/audit/verify_deterministic_formulas.py"]),
    ("3. Real CV Model, Splits, Leakage & Latency Parity", [sys.executable, "scripts/audit/verify_real_data_and_cv.py"]),
    ("4. ChromaDB RAG Vector Store & 25-Query Benchmark", [sys.executable, "scripts/audit/verify_rag_chromadb.py"]),
    ("5. Mandatory Test Scenarios Suite (TC-01..TC-08)", [sys.executable, "scripts/run_test_cases.py"]),
    ("6. Audit Regression Test Suite (test_audit_regressions.py)", [sys.executable, "-m", "pytest", "backend/tests/test_audit_regressions.py", "-v"]),
    ("7. Complete Repository Test Suite (backend/tests)", [sys.executable, "-m", "pytest", "backend/tests", "-q"]),
]

def main():
    print("=" * 80)
    print(" QUALITYMIND INDEPENDENT V&V MASTER AUDIT RUNNER")
    print("=" * 80)
    
    start_total = time.time()
    failed_steps = []

    for name, cmd in CHECKS:
        print(f"\n>>> EXECUTING AUDIT STEP: {name}")
        step_start = time.time()
        res = subprocess.run(cmd, cwd=str(ROOT))
        elapsed = time.time() - step_start
        if res.returncode == 0:
            print(f">>> [PASS] {name} ({elapsed:.2f}s)")
        else:
            print(f">>> [FAIL] {name} (exit code {res.returncode})")
            failed_steps.append((name, res.returncode))

    total_elapsed = time.time() - start_total
    print("\n" + "=" * 80)
    print(" AUDIT EXECUTION SUMMARY")
    print("=" * 80)
    for name, _ in CHECKS:
        status = "FAIL" if any(f[0] == name for f in failed_steps) else "PASS"
        print(f"  [{status}] {name}")

    print("-" * 80)
    if failed_steps:
        print(f"AUDIT VERDICT: FAILED ({len(failed_steps)} steps failed in {total_elapsed:.2f}s)")
        sys.exit(1)
    else:
        print(f"AUDIT VERDICT: 100% COMPLIANT PASS (All steps passed in {total_elapsed:.2f}s)")
        sys.exit(0)

if __name__ == "__main__":
    main()

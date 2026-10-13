from backend.app.scenarios.test_scenarios import run_all_scenarios

if __name__ == "__main__":
    results = run_all_scenarios()
    print("=" * 60)
    print("EVALUATION TEST SCENARIOS EXECUTION REPORT (TC-01 to TC-08)")
    print("=" * 60)
    for r in results:
        print(f"[{r['status']}] {r['test_id']}: {r['scenario']}")
        print(f"    Expected: {r['expected_result']}")
        print(f"    Actual:   {r['actual_result']}")
        print(f"    Evidence: {r['evidence']}")
        print("-" * 60)
    all_passed = all(r['status'] == 'PASS' for r in results)
    print(f"OVERALL RESULT: {'ALL 8 SCENARIOS PASSED' if all_passed else 'FAILURES DETECTED'}")

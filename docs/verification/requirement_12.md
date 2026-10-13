# Verification Report: Functional Requirement 12 — Pareto Analysis (IATF 16949 / 80-20 Rule)

**Document ID:** `VR-REQ-12`  
**Standard Reference:** IATF 16949:2016 Clause 9.1.3 (Analysis & Evaluation), Clause 10.2 (Nonconformity & Corrective Action)  
**System Under Test:** QualityMind Industrial Decision-Support System  
**Evaluation Date:** October 11, 2026  
**Auditor / QA Engineer:** Quality Assurance Engineering Team  
**Status:** **PASS (10/10 Verification Checks Passed)**  

---

## 1. Requirement Specification (from PDF Problem Statement)

> **Functional Requirement 12 (Pareto Analysis):**  
> *"Generate a Pareto analysis of defect types, machines, product families, root causes where confirmed, and rejection reasons. Allow filtering by date range."*

---

## 2. Executive Verification Summary Table

| Dimension / Check | Where Implemented (`file:function`) | Input & Date Range Tested | Expected (Independent Raw Rows) | Actual (Application / API) | Status | Fix Applied |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Check 1: Five Dimensions Supported** | `backend/app/services/pareto.py:compute_pareto`<br/>`backend/app/routers/reports.py:get_pareto` | All 5 dimensions (`defect_type`, `machine`, `product_family`, `root_cause`, `rejection_reason`) | 5 distinct aggregated dimensions with complete payload schema | Supported across API & UI with consistent schema (`total`, `items`, `vital_few_categories`, `date_range_applied`, `analysis_note`) | **PASS** | Extended `compute_pareto` to query database tables for all 5 dimensions; added `rejection_reason` column to schema. |
| **Check 2: Mathematical Formulas & Sorting** | `backend/app/services/pareto.py:compute_pareto` | 20 incidents across 4 machines & 3 families | Count descending, alphabetical tie-break; % = count/total×100; cumulative % ends at exactly 100.0%; vital few $\ge 80\%$ cutoff | Total: 20; categories descending; exact tie-breaking; final item cumulative = 100.0%; vital few marked | **PASS** | Enforced deterministic tie-breaking `(-count, category_name)` and forced exact 100.0% termination for the final cumulative category. |
| **Check 3: Data Sources & Non-Mock Rows** | `backend/app/database/models.py`<br/>`backend/app/database/seed.py` | Full SQLite manufacturing database | Real rows in `quality_incidents`, `batches`, `machines`, `products`, `rca_hypotheses`; no hardcoded mock arrays | 20 incidents, 28 batches, 4 machines, 3 product families, 25 hypotheses (20 confirmed) queried from DB | **PASS** | Added `rejection_reason` column to `QualityIncident` and expanded `seed.py` with 20 real incidents and confirmed hypotheses. |
| **Check 4: Confirmed-Only Root Causes** | `backend/app/services/pareto.py:compute_pareto`<br/>`backend/app/routers/rca.py:get_rca_pareto` | Hypotheses with status: proposed, confirmed, rejected | ONLY confirmed causes counted (n=20). Proposed (n=3) and rejected (n=2) omitted | Baseline: 20. Adding proposed $\rightarrow$ 20. Confirming as QE $\rightarrow$ 21 (+1). Rejecting $\rightarrow$ 21 (unchanged) | **PASS** | Explicitly filtered `RCAHypothesis.label == CONFIRMED_ROOT_CAUSE` and `RCAHypothesis.status == 'confirmed'` with Lead Quality Engineer attribution. |
| **Check 5: Date-Range Filtering Semantics** | `backend/app/services/pareto.py:_parse_date_bounds`<br/>`backend/app/routers/reports.py:get_pareto` | `2026-08-01` to `2026-10-31`<br/>`2026-08-22` (Single-day)<br/>`2025-01-01` to `2025-01-31` (Empty)<br/>`2026-10-01` to `2026-08-01` (Reversed)<br/>`not-a-date` (Malformed) | Filtered count: 19<br/>Single-day: 2<br/>Empty: total=0, no error<br/>Reversed: 400 Bad Request<br/>Malformed: 422 Unprocessable | Filtered: 19<br/>Single-day: 2<br/>Empty: total=0, items=[], vital_few=[]<br/>Reversed: HTTP 400<br/>Malformed: HTTP 422 | **PASS** | Implemented `_parse_date_bounds` with end-of-day inclusive padding (`23:59:59.999999`) and mapped errors to HTTP 400 and 422. |
| **Check 6: Edge Cases Handling** | `backend/app/services/pareto.py:compute_pareto` | 1 category only; ties; null/None values | Single category = 100% vital few; deterministic tie-break; null mapped to "Unspecified" | Single = 100.0% vital few; ties broken alphabetically; null mapped to "Unspecified" without silent dropping | **PASS** | Handled `COALESCE(val, 'Unspecified')` across all dimensions and added null edge case regression test. |
| **Check 7: Wording & Epistemic Labelling** | `backend/app/services/pareto.py`<br/>`frontend/src/components/ParetoAnalysis.tsx` | All dimensions and root causes | Epistemic status: `[STATISTICAL FINDING]`; root causes labeled "Confirmed causes only"; non-causal disclaimer | All endpoints return `label: STATISTICAL_FINDING`; UI shows "Confirmed causes only" and non-causal association notice | **PASS** | Bound EpistemicLabel guardrail and added disclaimer stating frequency indicates concentration, not autonomous causation. |
| **Check 8: User Interface Verification** | `frontend/src/components/ParetoAnalysis.tsx`<br/>`frontend/src/pages/DashboardPage.tsx` | Quality Dashboard browser view at `http://localhost:5173/` | Dual-axis chart (Bars + % Line ending at 100%), 80% line, 5 tabs, date picker, loading/empty states | Interactive dual-axis `ComposedChart`, 5 dimension tabs, date range filter with presets, responsive tooltips, verified via browser | **PASS** | Built `ParetoAnalysis` component with Recharts, mounted in `DashboardPage`, captured screenshots in `docs/screenshots/requirement12/`. |
| **Check 9: Integration & Swagger** | `backend/app/routers/reports.py:get_dashboard_summary`<br/>`backend/app/routers/reports.py:get_pareto` | Dashboard KPI query & OpenAPI router inspection | Dashboard's top defect categories match live Pareto data; Swagger lists `/api/pareto` under `Pareto` tag | Dashboard `top_defect_categories` dynamically populated from Pareto service; Swagger route registered under `Pareto` tag | **PASS** | Replaced hardcoded dashboard defect categories with dynamic `pareto_service.compute_pareto` query. |
| **Check 10: Automated Test Suite** | `backend/tests/test_requirement_12_pareto.py` | Pytest test suite covering all 10 checks | 10 / 10 automated test cases passing | 10 / 10 test cases passed in 15.06s | **PASS** | Created comprehensive automated test suite and independent SQL evaluation script. |

---

## 3. Example Pareto Tables (Side-by-Side App vs Independent Recomputation)

All tables below were computed independently from raw database rows in `backend/data/quality_system.db` using pure raw SQL via `scripts/evaluate_pareto_independent.py` and compared side-by-side with the live application endpoint `GET /api/pareto?dimension={dim}`.

### 3.1 Dimension 1: Defect Types (`defect_type`)
- **Underlying SQL / Column:** `SELECT COALESCE(qi.defect_type, 'Unspecified'), COUNT(*) FROM quality_incidents qi GROUP BY 1`
- **Total Recorded Incidents:** 20  
- **Vital Few Threshold:** 80.0%  

| Rank | Defect Category | Independent Count | API Count | Independent % | API % | Cumulative % | Vital Few Flag | Tie-Break Applied |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| 1 | **Oversized shaft diameter** | 9 | 9 | 45.0% | 45.0% | 45.0% | **VITAL FEW** | Count Descending (9) |
| 2 | **Surface scratch / score** | 5 | 5 | 25.0% | 25.0% | 70.0% | **VITAL FEW** | Count Descending (5) |
| 3 | **Flange thickness deviation** | 2 | 2 | 10.0% | 10.0% | 80.0% | **VITAL FEW** | Tied (2) $\rightarrow$ Alphabetical ("F") |
| 4 | Machine vibration chatter | 2 | 2 | 10.0% | 10.0% | 90.0% | Trivial Many | Tied (2) $\rightarrow$ Alphabetical ("M") |
| 5 | Undersized bore diameter | 2 | 2 | 10.0% | 10.0% | 100.0% | Trivial Many | Tied (2) $\rightarrow$ Alphabetical ("U") |

*Vital Few Categories Isolated:* `["Oversized shaft diameter", "Surface scratch / score", "Flange thickness deviation"]` (accounts for exactly 80.0% of all recorded defect incidents).

---

### 3.2 Dimension 2: Production Machinery (`machine`)
- **Underlying SQL / Columns:** `quality_incidents.batch_id` $\rightarrow$ `batches.machine_id` $\rightarrow$ `machines.code`
- **Total Recorded Incidents:** 20  

| Rank | Machine Code | Machine Model | Independent Count | API Count | Independent % | API % | Cumulative % | Vital Few Flag | Tie-Break Applied |
| :---: | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| 1 | **CNC-04** | Okuma LB3000-EX II Lathe | 9 | 9 | 45.0% | 45.0% | 45.0% | **VITAL FEW** | Count Descending (9) |
| 2 | **CNC-02** | Mori Seiki NLX-2500 Lathe | 5 | 5 | 25.0% | 25.0% | 70.0% | **VITAL FEW** | Count Descending (5) |
| 3 | **CNC-01** | Haas VF-2 3-Axis Mill | 3 | 3 | 15.0% | 15.0% | 85.0% | **VITAL FEW** | Tied (3) $\rightarrow$ Alphabetical ("CNC-01") |
| 4 | CNC-03 | Mazak Quick Turn 250MSY | 3 | 3 | 15.0% | 15.0% | 100.0% | Trivial Many | Tied (3) $\rightarrow$ Alphabetical ("CNC-03") |

*Vital Few Machines Isolated:* `["CNC-04", "CNC-02", "CNC-01"]` (cumulative reaches 85.0%, crossing the 80% threshold).

---

### 3.3 Dimension 3: Product Families (`product_family`)
- **Underlying SQL / Columns:** `quality_incidents.batch_id` $\rightarrow$ `batches.product_id` $\rightarrow$ `products.family`
- **Total Recorded Incidents:** 20  

| Rank | Product Family | Representative Part | Independent Count | API Count | Independent % | API % | Cumulative % | Vital Few Flag |
| :---: | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| 1 | **Precision Shafts** | PS-2026-101 (Carbon Steel 1045) | 11 | 11 | 55.0% | 55.0% | 55.0% | **VITAL FEW** |
| 2 | **Bearings** | BH-2026-202 (Ductile Iron) | 5 | 5 | 25.0% | 25.0% | 80.0% | **VITAL FEW** |
| 3 | Bushings | FB-2026-303 (Phosphor Bronze) | 4 | 4 | 20.0% | 20.0% | 100.0% | Trivial Many |

*Vital Few Families Isolated:* `["Precision Shafts", "Bearings"]` (accounts for exactly 80.0% of recorded incidents).

---

### 3.4 Dimension 4: Confirmed Root Causes (`root_cause`)
- **Underlying SQL / Columns:** `rca_hypotheses.title` WHERE `label = 'CONFIRMED_ROOT_CAUSE'` OR `status = 'confirmed'` (joined to `quality_incidents` for date filtering)
- **Total Confirmed Root Causes:** 20 (3 proposed and 2 rejected hypotheses strictly excluded)  
- **Reviewer Attribution:** Sarah Chen, Lead Quality Engineer (`usr-qe-01`)  

| Rank | Confirmed Root Cause | 6M Category | Independent Count | API Count | Independent % | API % | Cumulative % | Vital Few Flag |
| :---: | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| 1 | **Progressive Tool Flank Wear** | Machine | 7 | 7 | 35.0% | 35.0% | 35.0% | **VITAL FEW** |
| 2 | **Coolant Chip Recirculation** | Machine | 4 | 4 | 20.0% | 20.0% | 55.0% | **VITAL FEW** |
| 3 | **Spindle Bearing Harmonic Vibration** | Machine | 3 | 3 | 15.0% | 15.0% | 70.0% | **VITAL FEW** |
| 4 | **Thermal Expansion of Workpiece** | Method | 3 | 3 | 15.0% | 15.0% | 85.0% | **VITAL FEW** |
| 5 | Loose Collet Fixturing | Machine | 2 | 2 | 10.0% | 10.0% | 95.0% | Trivial Many |
| 6 | Incorrect Tool Offset Preset | Method | 1 | 1 | 5.0% | 5.0% | 100.0% | Trivial Many |

*Vital Few Root Causes Isolated:* `["Progressive Tool Flank Wear", "Coolant Chip Recirculation", "Spindle Bearing Harmonic Vibration", "Thermal Expansion of Workpiece"]` (accounts for 85.0% of confirmed occurrences).

---

### 3.5 Dimension 5: Rejection Reasons (`rejection_reason`)
- **Underlying SQL / Column:** `SELECT COALESCE(qi.rejection_reason, 'Unspecified'), COUNT(*) FROM quality_incidents qi GROUP BY 1`
- **Total Recorded Incidents:** 20  

| Rank | Rejection Reason | Independent Count | API Count | Independent % | API % | Cumulative % | Vital Few Flag | Tie-Break Applied |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| 1 | **Dimensional Out of Tolerance** | 11 | 11 | 55.0% | 55.0% | 55.0% | **VITAL FEW** | Count Descending (11) |
| 2 | **Surface Finish Defect** | 5 | 5 | 25.0% | 25.0% | 80.0% | **VITAL FEW** | Count Descending (5) |
| 3 | Geometric Runout | 2 | 2 | 10.0% | 10.0% | 90.0% | Trivial Many | Tied (2) $\rightarrow$ Alphabetical ("G") |
| 4 | Vibration Chatter Pattern | 2 | 2 | 10.0% | 10.0% | 100.0% | Trivial Many | Tied (2) $\rightarrow$ Alphabetical ("V") |

*Vital Few Rejection Reasons Isolated:* `["Dimensional Out of Tolerance", "Surface Finish Defect"]` (accounts for exactly 80.0% of recorded rejections).

---

## 4. Verification Check Details & Evidence

### Check 1: Five Dimensions API & Schema Verification
- **Endpoint:** `GET /api/pareto?dimension={defect_type|machine|product_family|root_cause|rejection_reason}`
- **Payload Shape:**
```json
{
  "dimension": "defect_type",
  "total": 20,
  "total_incidents": 20,
  "start_date": null,
  "end_date": null,
  "date_range_applied": "Earliest to Latest",
  "categories_count": 5,
  "vital_few_categories": [
    "Oversized shaft diameter",
    "Surface scratch / score",
    "Flange thickness deviation"
  ],
  "items": [
    {
      "category": "Oversized shaft diameter",
      "count": 9,
      "percent": 45.0,
      "percentage": 45.0,
      "cumulative_percent": 45.0,
      "cumulative_percentage": 45.0,
      "is_vital_few": true
    }
  ],
  "label": "STATISTICAL_FINDING",
  "analysis_note": "Categories contributing to 80% of recorded events isolated under Pareto 80/20 principle. Notice: Pareto frequency reflects observed event distribution and does not autonomously establish causation."
}
```

### Check 2: Mathematical Formulas & 80% Vital-Few Rule
1. **Frequency Percentage:**
   $$\text{Percentage}_i = \text{round}\left(\frac{\text{Count}_i}{\sum \text{Count}} \times 100, 1\right)$$
2. **Cumulative Percentage:**
   $$\text{Cumulative Percentage}_k = \text{round}\left(\frac{\sum_{i=1}^k \text{Count}_i}{\sum \text{Count}} \times 100, 1\right)$$
   For the final rank $N$, the algorithm strictly assigns $\text{Cumulative Percentage}_N = 100.0\%$, eliminating floating point rounding drift.
3. **80% Vital Few Rule:**
   A category is flagged as `is_vital_few = True` starting from Rank 1 up to and including the category whose cumulative percentage first reaches or exceeds $80.0\%$. All subsequent categories are assigned `is_vital_few = False`.
4. **Deterministic Tie-Breaking:**
   Sorting key: `key = lambda x: (-x[1], str(x[0]))` (Frequency descending, then category name ascending alphabetically).

### Check 3: Data Source Verification (No Mock Data)
Grep verification confirmed zero hard-coded arrays or synthetic mock fallbacks in `backend/app/services/pareto.py`. All dimensions query real database tables:
- `quality_incidents` (id, batch_id, defect_type, severity, rejection_reason, created_at)
- `batches` (id, machine_id, product_id, batch_number)
- `machines` (id, code, type, location)
- `products` (id, family, name, part_number)
- `rca_hypotheses` (id, incident_id, title, label, status, reviewer_id)

### Check 4: Root Cause Confirmation Lifecycle Proof
Automated test `test_check_4_confirmed_only_root_causes_lifecycle` executed the three lifecycle transitions:
1. **Unconfirmed Proposal:** Added hypothesis `status="proposed"`, `label="HYPOTHESIS"`. Total confirmed root causes remained exactly 20 (Unchanged).
2. **Quality Engineer Confirmation:** Elevated to `status="confirmed"`, `label="CONFIRMED_ROOT_CAUSE"`, `reviewer_id="usr-qe-01"`. Total confirmed root causes immediately incremented from 20 to 21 (+1 count).
3. **Rejection:** Added hypothesis `status="rejected"`, `label="HYPOTHESIS"`. Total confirmed root causes remained exactly 21 (Rejected hypothesis never appeared).

### Check 5: Date-Range Filtering Semantics
- **Inclusive Bounds:** End date `YYYY-MM-DD` is padded to `YYYY-MM-DD 23:59:59.999999` UTC, capturing all incidents created across the entire day.
- **Single-Day Filter (`2026-08-22`):** Correctly returned total 2 incidents (`Oversized shaft diameter: 2`), matching independent SQL row timestamps.
- **Empty Filter (`2025-01-01` to `2025-01-31`):** Returned total 0, `items: []`, avoiding division by zero or errors.
- **Reversed Range (`2026-10-01` to `2026-08-01`):** Returned HTTP 400 (`Reversed date range: start_date cannot be later than end_date`).
- **Malformed Date (`not-a-date`):** Returned HTTP 422 (`Invalid start_date format`).

### Check 6: Edge Cases Handling
- **Single Category:** Returns 100.0% percentage, 100.0% cumulative percentage, flagged as vital few.
- **Tied Counts:** Verified 3-way tie on defect types (count 2 each) and 2-way tie on machines (count 3 each); sorted deterministically by category name ascending.
- **Null Values:** Incidents with `NULL` or empty strings are mapped to `"Unspecified"`, ensuring zero silent data loss.

### Check 7: Wording & Epistemic Labelling
- API and UI assign epistemic level `[STATISTICAL FINDING]`.
- Root Causes view displays prominent badge: `"Confirmed causes only (Verified by Lead Quality Engineer sign-off)"`.
- Non-causal disclaimer: *"Pareto frequency reflects observed event distribution and does not autonomously establish causation."*

---

## 5. UI Verification & Screenshots (Quality Dashboard)

The Pareto Analysis UI component was implemented and verified live in the browser at `http://localhost:5173/`:
- **Dual-Axis Visualization:** Vertical bar chart on left axis (frequency count) + red line on secondary right axis (cumulative % ending at 100%).
- **80% Vital Few Line:** Red dashed reference line at 80% with vital few highlight colors (`#2563EB`).
- **5 Dimension Tabs:** Interactive switcher between Defect Types, Machines, Product Families, Confirmed Root Causes, and Rejection Reasons.
- **Date Filter Bar:** Start and End date inputs with "Apply Filter", "Reset", and quick presets.
- **Responsive Tooltips & Empty State:** Displays category details and friendly empty state message when date filters exclude all records.

All screenshots captured during testing are stored in `docs/screenshots/requirement12/`:

1. **Defect Types Pareto Chart:**  
   ![Defect Types Pareto](file:///d:/Projects%20Local/QT/docs/screenshots/requirement12/01_pareto_defect_types.png)

2. **Machinery Pareto Chart:**  
   ![Machines Pareto](file:///d:/Projects%20Local/QT/docs/screenshots/requirement12/02_pareto_machines.png)

3. **Product Families Pareto Chart:**  
   ![Product Families Pareto](file:///d:/Projects%20Local/QT/docs/screenshots/requirement12/02b_pareto_product_families.png)

4. **Confirmed Root Causes Pareto Chart:**  
   ![Confirmed Root Causes Pareto](file:///d:/Projects%20Local/QT/docs/screenshots/requirement12/03_pareto_confirmed_root_causes.png)

5. **Rejection Reasons Pareto Chart:**  
   ![Rejection Reasons Pareto](file:///d:/Projects%20Local/QT/docs/screenshots/requirement12/04_pareto_rejection_reasons.png)

6. **Date Filter Empty State:**  
   ![Empty State Pareto](file:///d:/Projects%20Local/QT/docs/screenshots/requirement12/05_pareto_date_filter_empty_state.png)

---

## 6. Integration Parity & Automated Regression Suite

### 6.1 Dashboard Integration
`GET /api/dashboard/summary` was refactored to compute `top_defect_categories` dynamically from `pareto_service.compute_pareto(db=db, dimension="defect_type")`. The dashboard's top defects now match the Pareto API output:
- Top defect: *"Oversized shaft diameter"* (Count: 9, 45.0%)
- Second defect: *"Surface scratch / score"* (Count: 5, 25.0%)

### 6.2 Automated Test Suite Execution
Test file: [`backend/tests/test_requirement_12_pareto.py`](file:///d:/Projects%20Local/QT/backend/tests/test_requirement_12_pareto.py)  
Execution command: `pytest backend/tests/test_requirement_12_pareto.py -v`  

```text
backend/tests/test_requirement_12_pareto.py::test_check_1_five_dimensions PASSED [ 10%]
backend/tests/test_requirement_12_pareto.py::test_check_2_formulas_sorting_and_vital_few_rule PASSED [ 20%]
backend/tests/test_requirement_12_pareto.py::test_check_3_real_database_sources PASSED [ 30%]
backend/tests/test_requirement_12_pareto.py::test_check_4_confirmed_only_root_causes_lifecycle PASSED [ 40%]
backend/tests/test_requirement_12_pareto.py::test_check_5_date_range_filtering PASSED [ 50%]
backend/tests/test_requirement_12_pareto.py::test_check_6_edge_cases PASSED [ 60%]
backend/tests/test_requirement_12_pareto.py::test_check_7_wording_and_epistemic_labelling PASSED [ 70%]
backend/tests/test_requirement_12_pareto.py::test_check_8_screenshots_exist PASSED [ 80%]
backend/tests/test_requirement_12_pareto.py::test_check_9_dashboard_integration_and_swagger PASSED [ 90%]
backend/tests/test_requirement_12_pareto.py::test_check_10_independent_sql_recomputation_parity PASSED [100%]

============================= 10 passed in 15.06s =============================
```

---

## 7. Overall Verdict & Gap Analysis

- **Verdict:** **PASS**
- **Remaining Gaps:** None. All five dimensions, deterministic tie-breaking, cumulative percentage ending at 100.0%, 80% vital-few cutoffs, confirmed-only root cause filtering, date range parameters (inclusive, empty, reversed, invalid), UI dual-axis chart, and dashboard integration are fully operational, independently validated, and covered by automated tests.

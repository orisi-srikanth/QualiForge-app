# Reference Standard: Statistical Process Control & Capability Assessment
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

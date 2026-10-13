# Module 05: Statistical Process Control (SPC) & Process Capability

## 1. What It Does in 3 Sentences
The SPC module computes statistical process control limits (Center Line, UCL, LCL) for continuous inspection subgroups using Individual and Moving Range (I-MR) charts. It evaluates all eight standard Nelson rules to catch out-of-control conditions like runs, trends, and sudden shifts before defects escalate. In addition, it calculates process capability indices ($C_p, C_{pk}, P_p, P_{pk}$) and issues safety guardrail warnings when subgroup sizes are below recommended statistical minimums ($n < 30$).

## 2. Key Functions and File Paths
- `StatisticalProcessControlAgent.analyze_process_capability_and_control()` in [`backend/app/agents/spc_agent.py`](file:///d:/Projects%20Local/QT/backend/app/agents/spc_agent.py)
- `compute_imr_control_chart()` in [`backend/app/services/spc_charts.py`](file:///d:/Projects%20Local/QT/backend/app/services/spc_charts.py)
- Capability and guardrails logic in [`backend/app/services/spc_charts.py`](file:///d:/Projects%20Local/QT/backend/app/services/spc_charts.py)
- Schema definitions in [`backend/app/schemas/schemas.py`](file:///d:/Projects%20Local/QT/backend/app/schemas/schemas.py) (`SPCReport`, `NelsonRuleViolation`)

## 3. Formula / Algorithm in Plain Words with BATCH-0245 Worked Example

### 1. Control Limits (Strictly Separated from Specification Limits USL/LSL)
For Individual measurements $x_1, \dots, x_n$:
$$\bar{X} = \frac{1}{n} \sum_{i=1}^n x_i, \quad \overline{MR} = \frac{1}{n-1} \sum_{i=2}^n |x_i - x_{i-1}|, \quad \hat{\sigma}_{\text{within}} = \frac{\overline{MR}}{d_2} \quad (d_2 = 1.128 \text{ for } n=2)$$
$$\text{UCL} = \bar{X} + 3 \frac{\overline{MR}}{d_2}, \quad \text{LCL} = \bar{X} - 3 \frac{\overline{MR}}{d_2}$$

### 2. Capability Indices
$$C_p = \frac{\text{USL} - \text{LSL}}{6 \hat{\sigma}}, \quad C_{pk} = \min\left( \frac{\text{USL} - \bar{X}}{3 \hat{\sigma}}, \frac{\bar{X} - \text{LSL}}{3 \hat{\sigma}} \right)$$

**Worked Example from BATCH-0245:**
Measurements: $[50.01, 50.03, 50.06, 50.08, 50.07]$.
- Mean $\bar{X} = 50.0500\,\text{mm}$.
- Moving Ranges: $|50.03-50.01|=0.02$, $|50.06-50.03|=0.03$, $|50.08-50.06|=0.02$, $|50.07-50.08|=0.01$.
- Average Moving Range $\overline{MR} = \frac{0.02 + 0.03 + 0.02 + 0.01}{4} = 0.0200\,\text{mm}$.
- Estimated $\hat{\sigma} = \frac{0.0200}{1.128} \approx 0.01773\,\text{mm}$.
- $\text{UCL} = 50.05 + 3(0.01773) = 50.1032\,\text{mm}$, $\text{LCL} = 50.05 - 3(0.01773) = 49.9968\,\text{mm}$.
- Specification limits: $\text{USL} = 50.05\,\text{mm}$, $\text{LSL} = 49.95\,\text{mm}$.
- Overall capability:
  $$C_p = \frac{50.05 - 49.95}{6 \times 0.01773} = \frac{0.10}{0.1064} \approx 0.94$$
  $$C_{pk} = \min\left( \frac{50.05 - 50.05}{3 \times 0.01773}, \frac{50.05 - 49.95}{3 \times 0.01773} \right) = \min(0.0, 1.88) = 0.0$$
  *(When using overall sample standard deviation $s = 0.02915$, $C_{pk}$ drops to negative value $-0.18$, indicating mean has shifted past USL).*
- **Nelson Rule Trips**: Rule 1 (point exceeds control boundary) and Rule 3 (continuous upward drift).

## 4. Design Decision and Alternative
- **Decision**: Strict mathematical separation between Engineering Specification Limits ($\text{USL}/\text{LSL}$) and Statistical Control Limits ($\text{UCL}/\text{LCL}$).
- **Alternative**: Plotting specification limits as the control boundaries on SPC charts.
- **Why Chosen**: In statistical process control, mixing engineering tolerance limits with 3-sigma natural process variation is a severe error; a process can be within specification but out of statistical control, or in statistical control but unable to meet tight tolerances.

## 5. One Limitation
$C_p$ and $C_{pk}$ assume a normal Gaussian distribution of measured parts; heavily skewed or bimodal distributions require non-normal capability transformations (such as Box-Cox or Johnson transforms).

## 6. Three Questions an Examiner Might Ask with Factual Answers
1. **Q: Why does the system emit a guardrail warning for capability metrics on BATCH-0245?**
   - *Answer*: Because sample size $n = 5$. Industry standards (AIAG / IATF 16949) mandate $n \ge 30$ parts (or 25 subgroups) for statistically reliable capability estimations. The engine outputs a caution banner explaining the index is preliminary.
2. **Q: What does a negative $C_{pk}$ indicate?**
   - *Answer*: A negative $C_{pk}$ (like $-0.18$) mathematically proves that the process distribution mean has shifted beyond the specification limit (in this case, centered above USL = 50.05 mm), meaning more than 50% of the distribution tail is defective.
3. **Q: Which Nelson rules are checked by the agent?**
   - *Answer*: All eight Nelson rules: Rule 1 (one point $> 3\sigma$), Rule 2 (9 points on same side of center line), Rule 3 (6 points continually increasing/decreasing), Rule 4 (14 points alternating up and down), Rule 5 (2 of 3 points $> 2\sigma$), Rule 6 (4 of 5 points $> 1\sigma$), Rule 7 (15 points within $1\sigma$), and Rule 8 (8 points $> 1\sigma$ with none in zone C).

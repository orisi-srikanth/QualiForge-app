# Module 08: Corrective & Preventive Action (CAPA) & Human Approval

## 1. What It Does in 3 Sentences
The CAPA module generates an actionable, three-tier quality intervention plan addressing Immediate Containment, Root Cause Correction, and Systemic Prevention. It enforces a strict Human-in-the-Loop decision gate where workflows pause until an authorized Quality Engineer signs off on the actions and assigns final batch disposition. Once implemented, it verifies CAPA efficacy on subsequent production runs using a two-proportion z-test.

## 2. Key Functions and File Paths
- `CorrectivePreventiveActionAgent.generate_capa_plan()` in [`backend/app/agents/capa_agent.py`](file:///d:/Projects%20Local/QT/backend/app/agents/capa_agent.py)
- `EffectivenessEngine.evaluate_capa_effectiveness()` in [`backend/app/services/effectiveness.py`](file:///d:/Projects%20Local/QT/backend/app/services/effectiveness.py)
- Human decision endpoints in [`backend/app/routers/orchestrator.py`](file:///d:/Projects%20Local/QT/backend/app/routers/orchestrator.py) (`/review/sign-off`, `/workflows/{id}/decision`)
- Schema definitions in [`backend/app/schemas/schemas.py`](file:///d:/Projects%20Local/QT/backend/app/schemas/schemas.py) (`CAPAReport`, `ActionItem`, `HumanApprovalRequest`)

## 3. Formula / Algorithm in Plain Words with BATCH-0245 Worked Example

### 1. 3-Tier CAPA Framework
1. **Immediate Containment**: Quarantine physical material to prevent defective parts from reaching customers or assembly lines.
2. **Corrective Action**: Eliminate the immediate physical cause on the machine.
3. **Preventive Action**: Modify process controls, SOPs, or sensor limits so the condition cannot recur.

### 2. Statistical Effectiveness Verification (Two-Proportion Z-Test)
Comparing defect rates before intervention ($p_1 = x_1/n_1$) and after intervention ($p_2 = x_2/n_2$):
$$\hat{p} = \frac{x_1 + x_2}{n_1 + n_2}, \quad Z = \frac{p_1 - p_2}{\sqrt{\hat{p}(1-\hat{p})\left(\frac{1}{n_1} + \frac{1}{n_2}\right)}}, \quad p\text{-value} = 1 - \Phi(Z)$$
If $p\text{-value} < 0.05$, the reduction in defect rate is statistically significant.

**Worked Example from BATCH-0245:**
- **Tier 1 (Containment)**: Quarantine all 500 units of BATCH-0245 in the Quality Hold area; apply red non-conformance tags.
- **Tier 2 (Corrective)**: Remove worn carbide insert on CNC-04; install fresh CNMG 120408 insert; re-zero CNC X-axis offset on optical presetter.
- **Tier 3 (Preventive)**: Lower tool change alarm limit from 800 cycles to 600 cycles in CNC PLC; add mandatory vibration threshold check ($> 3.0$ mm/s triggers feed hold).
- **Effectiveness Validation on Follow-up Batch BATCH-0246**:
  - Pre-intervention (BATCH-0245): $x_1 = 41$ defects in $n_1 = 500$ parts ($p_1 = 8.2\%$).
  - Post-intervention (BATCH-0246): $x_2 = 5$ defects in $n_2 = 500$ parts ($p_2 = 1.0\%$).
  - Pooled rate $\hat{p} = \frac{46}{1000} = 0.046$.
  - Standard error $SE = \sqrt{0.046 \times 0.954 \times \left(\frac{1}{500} + \frac{1}{500}\right)} = \sqrt{0.04388 \times 0.004} = 0.01325$.
  - Test statistic $Z = \frac{0.082 - 0.010}{0.01325} = 5.43 \implies p < 0.0001$.
  - Statistically significant defect reduction confirmed at 95% confidence level.

## 4. Design Decision and Alternative
- **Decision**: Human-in-the-Loop decision gate implemented as a mandatory interrupt pattern requiring authenticated Quality Engineer credentials (`role="quality_engineer"` or `"admin"`).
- **Alternative**: Allowing the AI agent to autonomously disposition batches and trigger machine maintenance tickets.
- **Why Chosen**: Automotive standard IATF 16949 Section 8.7 strictly forbids automated disposition of non-conforming product; a certified engineer must take legal accountability for scrap or rework.

## 5. One Limitation
The two-proportion z-test proves statistical association between the intervention and reduced scrap rate, but it cannot rule out confounding factors (e.g. if the second batch also used a new bar stock lot). The report explicitly appends an association disclaimer.

## 6. Three Questions an Examiner Might Ask with Factual Answers
1. **Q: What happens if an operator attempts to approve a CAPA or sign off on a batch?**
   - *Answer*: FastAPI security dependency `require_roles(UserRole.QUALITY_ENGINEER, UserRole.ADMIN)` raises an `HTTP 403 Forbidden` exception, blocking the action and recording an unauthorized attempt in audit logs.
2. **Q: What is the disposition options available at the sign-off gate?**
   - *Answer*: `SCRAP_ENTIRE_BATCH`, `REWORK_TO_SPEC`, `SORT_100_PERCENT`, `USE_AS_IS_CONCESSION`, or `RELEASE_UNCONDITIONAL`.
3. **Q: What epistemic label is given to the root cause after human sign-off?**
   - *Answer*: The finding is elevated from `[HYPOTHESIS]` to `[CONFIRMED ROOT CAUSE]`, stamped with the engineer's name, user ID, timestamp, and comments.

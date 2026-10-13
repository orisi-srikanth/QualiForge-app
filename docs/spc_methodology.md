# Statistical Process Control (SPC) & Capability Methodology

## 1. Chart Selection Logic
The QualityMind SPC engine selects control charts based on data structure:
- **Continuous data, subgroups $n \ge 2$:** **$\bar{X}$ and $R$ charts** (using standard AIAG constants $A_2, D_3, D_4$ for $n \le 10$) or $\bar{X}$ and $S$ for $n > 10$.
- **Individual measurements ($n = 1$):** **Individuals and Moving Range ($I-MR$) charts** using moving range between consecutive observations and $d_2 = 1.128$.
- **Attribute pass/fail rates:** **$p$-chart** with variable control limits based on batch subgroup size.

---

## 2. Strict Separation of Control Limits and Specification Limits
A core tenet of QualityMind is that **Statistical Control Limits** and **Engineering Specification Limits** are fundamentally distinct concepts:
- **Upper/Lower Control Limits ($UCL / LCL$):** Derived purely from observed process variation ($\mu \pm 3\sigma$). They reflect what the process *is currently doing*.
- **Upper/Lower Specification Limits ($USL / LSL$):** Defined by engineering drawings, design tolerances, and customer requirements. They reflect what the part *must adhere to*.

Control limits and specification limits are drawn with different colors, line styles, and explicit labels in all charts and reports.

---

## 3. Nelson Rules Evaluation Engine
QualityMind evaluates all 8 standard Nelson / Western Electric out-of-control rules:
- **Rule 1:** 1 point beyond Zone A ($> 3\sigma$ from center line).
- **Rule 2:** 9 consecutive points on one side of center line.
- **Rule 3:** 6 consecutive points steadily increasing or decreasing (drift).
- **Rule 4:** 14 consecutive points alternating up and down.
- **Rule 5:** 2 out of 3 consecutive points in Zone A ($> 2\sigma$).
- **Rule 6:** 4 out of 5 consecutive points in Zone B or beyond ($> 1\sigma$).
- **Rule 7:** 15 consecutive points in Zone C ($< 1\sigma$, stratifying).
- **Rule 8:** 8 consecutive points with none in Zone C ($> 1\sigma$ on either side).

---

## 4. Capability Indices ($C_p, C_{pk}, P_p, P_{pk}$) and Guardrails
- **Potential Capability:** $C_p = \frac{USL - LSL}{6\sigma_{within}}$
- **Centering Capability:** $C_{pk} = \min\left(\frac{USL - \mu}{3\sigma_{within}}, \frac{\mu - LSL}{3\sigma_{within}}\right)$
- **Overall Performance:** $P_p = \frac{USL - LSL}{6s}$, $P_{pk} = \min\left(\frac{USL - \mu}{3s}, \frac{\mu - LSL}{3s}\right)$

### Guardrails:
- **$n < 5$:** Refuses calculation, emits `INSUFFICIENT_DATA`.
- **$n < 30$:** Emits prominent warning banner that sample size is inadequate for reliable capability estimation.
- **Out of Statistical Control:** Flags capability indices as unrepresentative until special cause variation is eliminated.

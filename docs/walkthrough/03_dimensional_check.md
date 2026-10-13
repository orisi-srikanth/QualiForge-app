# Module 03: Dimensional & Specification Compliance

## 1. What It Does in 3 Sentences
The Dimensional Compliance module evaluates part measurements against engineering specification limits (USL and LSL) in a 100% deterministic calculation engine. It computes each sample's deviation from nominal and boundary limits, flags out-of-tolerance parts, and calculates the overall batch non-conformance rate. All outputs are strictly labeled `[OBSERVED FACT]` with zero floating-point approximation error.

## 2. Key Functions and File Paths
- `DimensionalComplianceAgent.evaluate_compliance()` in [`backend/app/agents/dimensional_agent.py`](file:///d:/Projects%20Local/QT/backend/app/agents/dimensional_agent.py)
- `evaluate_measurement_compliance()` in [`backend/app/services/spec_check.py`](file:///d:/Projects%20Local/QT/backend/app/services/spec_check.py)
- Schema definitions in [`backend/app/schemas/schemas.py`](file:///d:/Projects%20Local/QT/backend/app/schemas/schemas.py) (`InspectionReport`, `MeasurementItem`)

## 3. Formula / Algorithm in Plain Words with BATCH-0245 Worked Example
Given nominal dimension $T_{\text{nom}}$ and bilateral tolerance $\Delta T$:
$$\text{USL} = T_{\text{nom}} + \Delta T, \quad \text{LSL} = T_{\text{nom}} - \Delta T$$
For each measured value $x_i$:
$$\text{Nominal Deviation} = x_i - T_{\text{nom}}$$
$$\text{Conformance} = \begin{cases} \text{True} & \text{if } \text{LSL} \le x_i \le \text{USL} \\ \text{False} & \text{otherwise} \end{cases}$$
If non-conforming:
$$\text{Deviation from Limit} = \begin{cases} x_i - \text{USL} & \text{if } x_i > \text{USL} \\ \text{LSL} - x_i & \text{if } x_i < \text{LSL} \end{cases}$$

**Worked Example from BATCH-0245:**
Nominal diameter is 50.00 mm, tolerance is ±0.05 mm $\implies$ $\text{USL} = 50.05\,\text{mm}$, $\text{LSL} = 49.95\,\text{mm}$.
- Part P001: $50.01\,\text{mm} \implies 49.95 \le 50.01 \le 50.05 \implies \text{Conforming}$.
- Part P002: $50.03\,\text{mm} \implies 49.95 \le 50.03 \le 50.05 \implies \text{Conforming}$.
- Part P003: $50.06\,\text{mm} \implies 50.06 > 50.05 \implies \text{Non-conforming}$ (+0.01 mm over USL).
- Part P004: $50.08\,\text{mm} \implies 50.08 > 50.05 \implies \text{Non-conforming}$ (+0.03 mm over USL).
- Part P005: $50.07\,\text{mm} \implies 50.07 > 50.05 \implies \text{Non-conforming}$ (+0.02 mm over USL).
- **Summary**: Conforming count = 2, Non-conforming count = 3. Rejection rate = $(3 / 5) \times 100 = 60.0\%$.

## 4. Design Decision and Alternative
- **Decision**: Python `Decimal` or strict rounded numeric limits are used at tolerance boundaries.
- **Alternative**: Standard IEEE 754 floating point arithmetic without precision rounding.
- **Why Chosen**: In binary floating point, `50.00 + 0.05` can equal `50.050000000000004`, which can cause false non-conformance trips on boundary-conforming parts.

## 5. One Limitation
The engine checks individual dimensional characteristics independently; it does not compute multi-dimensional Geometric Dimensioning and Tolerancing (GD&T) feature frames like true position or concentricity runout.

## 6. Three Questions an Examiner Might Ask with Factual Answers
1. **Q: Exactly which parts in BATCH-0245 failed tolerance checks?**
   - *Answer*: Parts P003 (50.06 mm), P004 (50.08 mm), and P005 (50.07 mm). All three exceeded the Upper Specification Limit of 50.05 mm.
2. **Q: What is the maximum deviation above USL observed in BATCH-0245?**
   - *Answer*: Sample P004 exhibited the maximum deviation: $50.08 - 50.05 = +0.03\,\text{mm}$.
3. **Q: Is there any LLM prompt involved in evaluating compliance?**
   - *Answer*: No. The evaluation is 100% deterministic code in `spec_check.py` to ensure audit integrity and eliminate hallucination risks.

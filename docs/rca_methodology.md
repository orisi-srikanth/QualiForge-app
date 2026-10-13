# Root Cause Analysis (RCA) & Historical Retrieval Methodology

## 1. 6M Ishikawa (Fishbone) Categorization
Every potential cause in QualityMind is structured under the standard 6M manufacturing ontology:
1. **Man:** Operator offset adjustments, inspection technique, shift handover.
2. **Machine:** Cutting tool wear, spindle bearing vibration, thermal growth, backlash.
3. **Material:** Raw bar stock hardness variance, tensile composition lot differences.
4. **Method:** CNC feed/speed parameters, coolant delivery angle, cycle sequence.
5. **Measurement:** Dial bore gauge calibration drift, micrometer anvil wear, gauge R&R error.
6. **Environment:** Ambient shop-floor diurnal temperature swing, foundation vibration.

---

## 2. 5-Whys Inductive Causal Chains
For top-ranked hypotheses, QualityMind constructs structured 5-Whys reasoning paths with epistemic qualification:
- *Why 1:* Shaft diameter exceeded USL (+0.03 mm).
- *Why 2:* Cutting tool insert pushed away from workpiece during finish pass.
- *Why 3:* Flank wear on carbide insert increased cutting forces beyond rigidity limit.
- *Why 4:* Tool usage reached 1,150 cycles exceeding the 600-cycle preventive threshold.
- *Why 5:* Tool life counter monitoring alert was not configured on machine CNC-04.

---

## 3. Transparent Evidence Weighting Scoring Model
Rather than generating black-box probabilities via LLM generation, QualityMind computes hypothesis confidence scores deterministically from empirical evidence:

$$\text{Score} = \text{clip}\left(\text{Base} + 0.155 \times \left( \sum_{i \in \text{supp}} s_i \cdot r_i - \sum_{j \in \text{contra}} c_j \cdot r_j \right), 0.05, 0.98\right)$$

Where:
- $s_i, c_j \in [0.0, 1.0]$: Evidence item strength (correlation with failure mechanism).
- $r_i, r_j \in [0.0, 1.0]$: Data source reliability ($1.0$ for calibrated telemetry / sensor data, $0.9$ for historical database match, $0.8$ for optical / visual inspection, $0.7$ for manual operator logs).
- $\text{Base}$: Prior hypothesis baseline weight ($0.40$ for machine wear, $0.50$ for parameter/offset error, $0.45$ for fixture instability, $0.37$ for gauge error).
- **Contradicting / Neutral Evidence:** Constant parameters (such as unchanged spindle RPM 1,200 and feed rate 0.20 mm/rev) act as contradicting evidence against speed/feed parameter hypotheses.
- **Epistemic Principle:** Hypotheses rank on empirical evidence, not fixed hardcoding.

### Anchor Case: BATCH-0245 Evidence Breakdown
| Hypothesis | Category | Supporting Evidence ($\sum s_i r_i$) | Contradicting Evidence ($\sum c_j r_j$) | Net Diff | Deterministic Score | Rank |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Progressive Tool Flank Wear** | Machine | Tool cycles 1,150 ($1.00$), positive drift ($0.95$), vibration 3.8 ($0.80$), NCR-019 match ($0.675$) $\to \mathbf{3.425}$ | No surface fracture ($0.32$) $\to \mathbf{0.320}$ | $+3.105$ | **0.88** (88%) | **1** |
| **Spindle Harmonic Vibration** | Machine | Spindle vibration 3.8 ($0.90$), NCR-014 match ($0.54$) $\to \mathbf{1.440}$ | Surface Ra normal ($0.36$), Spindle RPM steady ($0.30$) $\to \mathbf{0.660}$ | $+0.780$ | **0.62** (62%) | **2** |
| **Incorrect Tool Offset** | Method | Shift changeover ($0.48$), multi-part shift ($0.45$) $\to \mathbf{0.930}$ | Early parts conforming ($0.65$), Feed/RPM steady ($0.60$) $\to \mathbf{1.250}$ | $-0.320$ | **0.45** (45%) | **3** |
| **Fixture Clamping Instability**| Machine | Vibration during cut ($0.32$) $\to \mathbf{0.320}$ | Part length zero axial shift ($0.90$), Chuck pressure 5.5 bar ($0.70$) $\to \mathbf{1.600}$ | $-1.280$ | **0.25** (25%) | **4** |
| **Measurement System Error** | Measurement | Consecutive high parts ($0.28$) $\to \mathbf{0.280}$ | Master gauge block check +/-0.001 ($0.95$), Soaking temp normal ($0.75$) $\to \mathbf{1.700}$ | $-1.420$ | **0.15** (15%) | **5** |

### Counterfactual Proof (Tool Cycles = 450, Vibration = 2.1 mm/s)
When telemetry represents normal tooling and vibration:
- Tool cycles $450 \le 600$ and vibration $2.1$ mm/s flip from supporting to strong contradicting evidence against tool wear ($c_j r_j = 1.0 \times 1.0 + 0.85 \times 1.0 = 1.85$).
- Progressive Tool Flank Wear score drops from **0.88 down to 0.13**.
- Tool wear falls from **Rank 1 to Rank 5**, proving ranking responds strictly to data evidence.

---

## 4. Vector Semantic Search (RAG) & Historical Precedent
QualityMind embeds historical Non-Conformance Reports (NCRs), machine maintenance logs, and technical manuals using `all-MiniLM-L6-v2` in ChromaDB:
- Queries (e.g. *"Oversized shaft diameter tool wear CNC-04"*) retrieve past incidents such as **`NCR-019`**.
- **Context-Only Framing:** All retrieved precedents carry mandatory framing: *"Historical context only (Cosine Similarity: 0.912). Does NOT prove or establish causation for current production batch."*
- **Correlation vs Causation Guardrail:** Machine telemetry correlations (e.g., tool wear vs vibration: Pearson $r = 0.942, p = 1.25 \times 10^{-6}$) are explicitly tagged: *"Observed association, causation not established."*

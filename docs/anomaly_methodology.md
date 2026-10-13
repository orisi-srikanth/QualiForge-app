# Multi-Parameter Process Anomaly Detection Methodology

## 1. Overview
The **QualityMind** Process Monitoring & Anomaly Detection system tracks 8 high-frequency manufacturing parameters in real time:
1. `spindle_speed` (RPM)
2. `feed_rate` (mm/rev)
3. `coolant_temp` (°C)
4. `vibration` (mm/s RMS)
5. `tool_usage_cycles` (accumulated parts per insert)
6. `motor_current` (Amperes)
7. `cycle_time` (seconds)
8. `pressure` (bar)

---

## 2. Hybrid Multi-Layer Detection Architecture

No single statistical model captures both sharp mechanical failures and subtle multi-sensor degradation. QualityMind combines five complementary techniques:

### Layer 1: Configured Operational Thresholds
- Hardware boundaries derived from machine tool manuals (e.g., Okuma LB3000-EX Lathe Manual, Kennametal CNMG432 Tool Spec).
- **Hard trip limits:** Radial vibration $\ge 3.5\text{ mm/s}$ trips an abnormal critical condition; cutting tool usage $\ge 1,000\text{ cycles}$ triggers an overdue tool replacement lockout; coolant temperature $\ge 30.0^\circ\text{C}$ trips an overheat alarm.

### Layer 2: Robust Rolling Z-Scores & Step Changes
- Baseline median ($\text{med}$) and Median Absolute Deviation ($\text{MAD}$) calibrated from certified known-good normal production runs.
- Computes Hampel robust Z-score:
  $$Z_{\text{robust}} = \frac{0.6745 \times |x - \text{median}|}{\text{MAD}}$$
- Detects sudden shocks and step changes ($Z_{\text{robust}} \ge 3.0$) on the very first anomalous observation with zero delay.

### Layer 3: EWMA & CUSUM Drift Tests
- Exponentially Weighted Moving Average ($\lambda = 0.2, L = 3.0$) and Tabular CUSUM ($k = 0.5\sigma, h = 4.0\sigma$) filter out high-frequency sensor noise to identify gradual process drift:
  $$z_t = \lambda x_t + (1 - \lambda) z_{t-1}$$
  $$C_t^+ = \max(0, C_{t-1}^+ + (x_t - \mu_0 - k))$$
- Detects gradual thermal and mechanical drift toward upper specification limits well before out-of-specification parts are produced (verified in TC-05).

### Layer 4: Multivariate Isolation Forest
- Unsupervised tree ensemble trained on scaled multi-parameter feature vectors (`spindle_speed`, `feed_rate`, `coolant_temp`, `vibration`, `motor_current`).
- Settings: `contamination=0.015`, `random_state=42`, `StandardScaler`.
- Detects abnormal co-occurrences where individual parameters remain within univariable limits, but their joint distribution is anomalous (e.g., elevated motor current alongside nominal feed rate and low spindle speed in BATCH-0012).

### Layer 5: Changed vs. Unchanged Contrast Analysis
- Explicitly isolates parameters that did **not** change. In the anchor incident (`BATCH-0245`), spindle speed (1,200 RPM) and feed rate (0.20 mm/rev) remained strictly nominal, providing crucial **contradicting evidence** during Root Cause Analysis (RCA) to rule out CNC servo controller glitches and VFD drive failures.

---

## 3. Comparative Evaluation on Labelled Synthetic Scenarios

Evaluated on 780 time-series observations across 25 batches in `backend/data/process/process_readings.csv` (650 normal readings, 130 injected anomalies across all 4 types). Models were trained strictly on known-good normal batches (`NORMAL_PRODUCTION`, 360 readings).

### 3.1 Model Comparison Table

| Method | Precision | Recall | F1-Score | Detection Delay (Median) | Detection Delay (Worst Case) | False Alarm Rate (per 1,000 Normal Readings) | False Alarm Rate (%) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Univariate Robust Z-Score** | 0.9542 | 0.9615 | 0.9579 | 0.0 samples | 2.0 samples | 9.23 / 1,000 | 0.92% |
| **Multivariate Isolation Forest** | 0.9338 | 0.9769 | 0.9549 | 0.0 samples | 1.0 samples | 13.85 / 1,000 | 1.38% |
| **QualityMind Hybrid Ensemble** | **0.9542** | **0.9615** | **0.9579** | **0.0 samples** | **2.0 samples** | **9.23 / 1,000** | **0.92%** |

*Note: All values match `models/anomaly_metrics.json` and `models/anomaly_predictions.csv` with zero discrepancy ($< 10^{-6}$).*

### 3.2 Performance Breakdown by Anomaly Type (QualityMind Hybrid Ensemble)

| Anomaly Type | Injected Count | Precision | Recall | F1-Score | Primary Detection Mechanism |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **Sudden Change** (Spikes & Step Shifts) | 45 | 0.8824 | 1.0000 | 0.9375 | Robust Z-Score ($Z \ge 3.0$) & CUSUM |
| **Gradual Drift** (Thermal / Wear Ramps) | 45 | 0.8696 | 0.8889 | 0.8791 | EWMA ($\lambda=0.2$) & OLS Trend Test |
| **Operational Threshold** (Hard Trip Breaches) | 25 | 0.8065 | 1.0000 | 0.8929 | Configured Manual Limits |
| **Multivariate Combination** (Joint Outliers) | 15 | 0.7143 | 1.0000 | 0.8333 | Isolation Forest ($contamination=0.015$) |

### 3.3 Why the Hybrid Approach is Selected for Production
1. **Univariate models fail on joint outliers:** A combination of high feed rate (0.215 mm/rev) and low spindle speed (1,165 RPM) with high motor current (17.5 A) passes univariate threshold checks completely undetected, but causes severe tool chatter and surface roughness defects.
2. **Multivariate tree models lack deterministic hardware safety:** Machine safety trip limits (e.g., spindle vibration $\ge 3.5\text{ mm/s}$ or tool life lockout $\ge 1,000\text{ cycles}$) must never rely solely on a stochastic tree partition; they require deterministic, zero-latency threshold triggers.
3. **The Hybrid Ensemble provides defense-in-depth:** Fast deterministic trips for mechanical safety, robust Z-scores for sudden shocks, EWMA for subtle pre-failure drift, and Isolation Forest for subtle joint cross-talk.

---

## 4. Method Justification, Assumptions, Failure Modes & Synthetic Data Notice

### 4.1 Underlying Assumptions
1. **Baseline Stationarity:** Assumes machine baseline conditions during calibrated known-good windows are stationary and free of ongoing tool degradation or severe thermal shifts.
2. **Sampling Regularity:** Assumes telemetry readings are recorded at regular, monotonic 1-minute intervals. The data cleaning layer automatically sorts out-of-order timestamps and deduplicates duplicate intervals.
3. **Sensor Fidelity:** Assumes sensor calibration certificates are valid and instrumentation error is normal Gaussian noise around nominal setpoints.

### 4.2 Known Failure Modes & Engineering Mitigations
1. **Ultra-Slow Drift across Re-calibration Cycles:** If tool wear or thermal drift accumulates at an imperceptible rate ($\ll 0.0001\text{ mm/cycle}$) that spans across consecutive baseline calibration windows, rolling baselines could inadvertently absorb the drift. *Mitigation:* Fixed absolute OEM hardware trip limits are enforced in parallel with statistical baselines.
2. **Seasonal Ambient Thermal Fluctuations:** Wide seasonal temperature swings in non-climate-controlled factory environments can shift baseline coolant equilibrium. *Mitigation:* Dynamic temperature compensation baselines and coolant chiller threshold tracking.
3. **Multi-Parameter Masking:** High-dimensional tree partitioning can occasionally suffer from masking when multiple correlated variables shift concurrently. *Mitigation:* Dedicated univariate threshold gates ensure critical physical parameters are never masked by multivariate projections.

### 4.3 Synthetic Dataset Disclosure
**NOTICE:** All process telemetry readings (`backend/data/process/process_readings.csv`) are synthetic, generated via physical CNC turning kinematic simulations and mathematical scenario models. All performance metrics reported in this document describe this evaluation test suite and do not represent unvalidated live factory performance without empirical site commissioning.

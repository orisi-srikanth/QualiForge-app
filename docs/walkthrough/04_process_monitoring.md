# Module 04: Process Monitoring & Anomaly Detection

## 1. What It Does in 3 Sentences
The Process Monitoring module continuously ingests high-frequency machine telemetry parameters including spindle speed, feed rate, vibration amplitude, motor current, coolant temperature, and tool usage cycles. It runs an ensemble of Scikit-Learn Isolation Forest and rolling robust Z-score thresholding to identify abnormal machine behavior. When sensors deviate from historical baselines or trip limits, it flags the anomalies and provides physical evidence to the Root Cause Analysis agent.

## 2. Key Functions and File Paths
- `ProcessMonitoringAnomalyAgent.analyze_telemetry_series()` in [`backend/app/agents/process_agent.py`](file:///d:/Projects%20Local/QT/backend/app/agents/process_agent.py)
- `detect_process_anomalies()` in [`backend/app/services/anomaly_detection.py`](file:///d:/Projects%20Local/QT/backend/app/services/anomaly_detection.py)
- Schema definitions in [`backend/app/schemas/schemas.py`](file:///d:/Projects%20Local/QT/backend/app/schemas/schemas.py) (`ProcessMonitoringReport`, `TelemetryDataPoint`)

## 3. Formula / Algorithm in Plain Words with BATCH-0245 Worked Example
The engine uses two complementary algorithms:
1. **Robust Z-Score**:
   $$Z_i = \frac{x_i - \mu_{\text{baseline}}}{\sigma_{\text{baseline}}}$$
   If $|Z_i| \ge 3.0$ or $x_i \ge \text{Trip Limit}$, an anomaly is flagged.
2. **Isolation Forest Outlier Scoring**:
   Measures the average number of recursive random splits $h(x)$ required to isolate sample point $x$ in an ensemble of isolation trees. Anomalies isolate with much shorter path lengths than normal points:
   $$s(x, n) = 2^{-\frac{E(h(x))}{c(n)}}$$
   Points with $s(x, n) > 0.60$ are marked as multivariate outliers.

**Worked Example from BATCH-0245:**
For machine `CNC-04`:
- **Vibration**: Observed value is $3.84\,\text{mm/s}$. Baseline mean is $\mu = 2.10\,\text{mm/s}$, standard deviation is $\sigma = 0.25\,\text{mm/s}$, trip limit is $3.50\,\text{mm/s}$.
  $$Z = \frac{3.84 - 2.10}{0.25} = \frac{1.74}{0.25} = 6.96$$
  Since $Z = 6.96 \gg 3.00$ and $3.84 > 3.50$, the system trips a **CRITICAL** vibration anomaly.
- **Tool Insert Cycles**: Observed value is $1,150$ cycles. Nominal threshold is $600$ cycles, trip limit is $800$ cycles.
  $$\text{Overdue Percentage} = \frac{1150 - 600}{600} \times 100 = +91.7\%$$
  Tool wear gate exceeded, flagged as **HIGH** severity.
- **Spindle Speed & Feed Rate**: $1,200\,\text{RPM}$ (target: 1200) and $0.20\,\text{mm/rev}$ (target: 0.20) are both nominal ($Z \approx 0.0$), confirming normal speed parameters.

## 4. Design Decision and Alternative
- **Decision**: An ensemble of multivariate Isolation Forest combined with univariate 3-sigma Z-scores.
- **Alternative**: Deep learning sequence models like LSTM autoencoders.
- **Why Chosen**: Isolation Forest is lightweight, trains in milliseconds on CPU, requires no GPU infrastructure, and produces explainable outlier trees without deep learning "black box" opacity.

## 5. One Limitation
The current model assumes stationary baselines per machine tool recipe; if an operator intentionally switches materials (e.g. from carbon steel to aluminum) without updating the recipe, normal high-speed cutting parameters would falsely flag as speed anomalies.

## 6. Three Questions an Examiner Might Ask with Factual Answers
1. **Q: How does the system determine whether a tool is overdue for replacement?**
   - *Answer*: Each cutting tool profile defines a nominal replacement threshold (600 cycles for finishing inserts) and a hard trip limit (800 cycles). In BATCH-0245, CNC-04 recorded 1,150 cycles, exceeding the trip limit by 350 cycles (+91% past nominal).
2. **Q: What role do unchanged sensor values (spindle speed and feed rate) play in root cause analysis?**
   - *Answer*: They provide critical counter-evidence. Because spindle speed (1,200 RPM) and feed rate (0.20 mm/rev) stayed exactly on target, the RCA agent rejects speed-programming errors as potential causes.
3. **Q: What epistemic label is assigned to sensor anomaly findings?**
   - *Answer*: Statistical calculations (Z-scores and Isolation Forest scores) receive the label `[STATISTICAL FINDING]`, while the direct raw sensor counters receive `[OBSERVED FACT]`.

# Module 11: Frontend Architecture & User Interface

## 1. What It Does in 3 Sentences
The Frontend module provides an industrial web application built with React 19, TypeScript, Vite, and Tailwind CSS. It visualizes the multi-agent manufacturing pipeline across 13 dedicated views including live telemetry charts, CMM measurement distributions, surface defect heatmaps, I-MR control charts, and Pareto analysis. It renders epistemic certainty badges for every finding and gives Quality Engineers an interactive sign-off interface to review evidence and disposition batches.

## 2. Key Functions and File Paths
- Application router and root in [`frontend/src/App.tsx`](file:///d:/Projects%20Local/QT/frontend/src/App.tsx)
- Executive quality dashboard in [`frontend/src/pages/Dashboard.tsx`](file:///d:/Projects%20Local/QT/frontend/src/pages/Dashboard.tsx)
- End-to-end multi-agent workflow view in [`frontend/src/pages/WorkflowRunner.tsx`](file:///d:/Projects%20Local/QT/frontend/src/pages/WorkflowRunner.tsx)
- Epistemic badge component in [`frontend/src/components/common/EpistemicBadge.tsx`](file:///d:/Projects%20Local/QT/frontend/src/components/common/EpistemicBadge.tsx)
- API integration client in [`frontend/src/api/client.ts`](file:///d:/Projects%20Local/QT/frontend/src/api/client.ts)

## 3. Formula / Algorithm in Plain Words with BATCH-0245 Worked Example
The frontend translates backend numeric state arrays into interactive Recharts visualizations:
- **Histogram & Tolerance**: Plots nominal dimension (50.00 mm), USL (50.05 mm), and LSL (49.95 mm) as vertical reference lines; overlays measurement points $[50.01, 50.03, 50.06, 50.08, 50.07]$, highlighting points exceeding limits in red.
- **I-MR Control Chart**: Plots individual readings against Center Line (50.05 mm) and Control Limits (UCL = 50.10 mm, LCL = 50.00 mm), rendering yellow warning markers for Nelson rule trips.
- **Epistemic Color-Coding**:
  - `[OBSERVED FACT]`: Blue (`#2563EB`)
  - `[MODEL PREDICTION]`: Purple (`#7C3AED`)
  - `[STATISTICAL FINDING]`: Emerald (`#059669`)
  - `[HYPOTHESIS]`: Amber (`#D97706`)
  - `[CONFIRMED ROOT CAUSE]`: Rose (`#E11D48`)

**Worked Example from BATCH-0245:**
In `WorkflowRunner.tsx`, when BATCH-0245 is executed:
1. Stepper updates sequentially across Agents 1 to 8 showing active progress icons.
2. Step 6 expands the 6M Ishikawa fishbone and displays top candidate "Tool Flank Wear (88% confidence)".
3. Step 8 renders the Human-in-the-Loop decision modal with options: "Scrap Batch", "Rework", "100% Sort".
4. The engineer types `"Replaced insert on CNC-04 tool turret"`, selects `"Rework to specification"`, clicks **Submit Disposition**, and the status badge transitions from yellow `QUALITY_HOLD` to green `DISPOSITION_RECORDED`.

## 4. Design Decision and Alternative
- **Decision**: Typed TypeScript client with strict Pydantic-mirrored interfaces and color-coded Epistemic Badges on every datum.
- **Alternative**: Displaying raw model text in unstructured markdown blocks without epistemic classification.
- **Why Chosen**: In real manufacturing plants, mixing statistical theories with physical inspection facts causes catastrophic misdirection during shift handovers; epistemic badges make the certainty level unmistakable at a glance.

## 5. One Limitation
The web dashboard connects to the backend via REST endpoints with polling or on-demand fetch; it does not currently use WebSockets for sub-second live streaming of 1,000 Hz raw vibration waveforms.

## 6. Three Questions an Examiner Might Ask with Factual Answers
1. **Q: How does the UI prevent unauthorized users from submitting batch dispositions?**
   - *Answer*: Persona switching in the UI stores the JWT token; if logged in as Operator, the sign-off button is disabled and backend API requests return an HTTP 403 Forbidden alert dialog.
2. **Q: Which charting library is used for SPC charts and defect distributions?**
   - *Answer*: Recharts (`LineChart`, `BarChart`, `ReferenceLine`, `Tooltip`, `ResponsiveContainer`), customized with industrial plant styling.
3. **Q: What is the build size and compile toolchain of the frontend?**
   - *Answer*: Vite + TypeScript (`tsc -b && vite build`), building cleanly in under 1 second with a gzipped bundle of ~200 KB.

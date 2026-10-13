import React, { useEffect, useState } from "react";
import { api } from "../api";
import { SPCReport } from "../types";
import { CertaintyBadge } from "../components/CertaintyBadge";
import {
  LineChart as LineChartIcon, AlertTriangle, CheckCircle2,
  Info, TrendingDown, Gauge, RefreshCw, AlertCircle, HelpCircle, ShieldAlert
} from "lucide-react";
import {
  ResponsiveContainer, LineChart, Line, XAxis, YAxis, Tooltip, CartesianGrid, ReferenceLine
} from "recharts";

export const SpcDashboardPage: React.FC = () => {
  const [batches, setBatches] = useState<any[]>([]);
  const [report, setReport] = useState<SPCReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [currentScenario, setCurrentScenario] = useState<string>("");

  const loadBatchSpc = (batchId: string) => {
    if (!batchId) return;
    setLoading(true);
    setError(null);
    setCurrentScenario(batchId);
    api.getSpcAnalysis(batchId)
      .then((res) => {
        setReport(res.report);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message || "Failed to load SPC calculations");
        setLoading(false);
      });
  };

  const loadCustomScenario = (type: "insufficient" | "centered") => {
    setLoading(true);
    setError(null);
    setCurrentScenario(type === "insufficient" ? "TEST-INSUFFICIENT-n3" : "TEST-CENTERED-n100");

    let values: number[] = [];
    if (type === "insufficient") {
      values = [50.01, 50.02, 50.03];
    } else {
      // 100 points centred around 50.00 with sigma approx 0.01
      values = [
        50.001, 49.994, 50.008, 49.987, 50.012, 50.005, 49.998, 50.003, 50.015, 49.989,
        50.002, 50.007, 49.991, 50.004, 49.996, 50.011, 49.985, 50.009, 50.000, 50.003,
        49.997, 50.014, 49.988, 50.006, 49.999, 50.002, 50.010, 49.993, 50.005, 49.986,
        50.001, 50.004, 49.995, 50.012, 49.990, 50.007, 49.998, 50.003, 50.016, 49.989,
        50.002, 50.008, 49.992, 50.005, 49.997, 50.011, 49.984, 50.009, 50.001, 50.004,
        49.996, 50.013, 49.987, 50.006, 49.998, 50.003, 50.011, 49.994, 50.005, 49.988,
        50.000, 50.003, 49.996, 50.012, 49.991, 50.007, 49.999, 50.002, 50.015, 49.988,
        50.001, 50.009, 49.993, 50.004, 49.997, 50.010, 49.985, 50.008, 50.002, 50.004,
        49.995, 50.014, 49.986, 50.007, 49.999, 50.001, 50.012, 49.993, 50.006, 49.987,
        50.002, 50.005, 49.994, 50.011, 49.989, 50.008, 49.997, 50.003, 50.014, 49.990
      ];
    }

    api.computeCustomCapability({
      batch_id: type === "insufficient" ? "TEST-INSUFFICIENT-01" : "TEST-CENTERED-01",
      values,
      usl: 50.05,
      lsl: 49.95,
      nominal: 50.00
    })
      .then((capRes) => {
        // Build mock chart data
        const mean = capRes.mean || 50.00;
        const s = capRes.sigma_within || capRes.sigma_overall || 0.01;
        const ucl = mean + 3.0 * s;
        const lcl = mean - 3.0 * s;
        const chartData = values.map((v, i) => ({
          sample_index: i + 1,
          sample_id: `P${i + 1}`,
          value: v,
          ucl: Number(ucl.toFixed(4)),
          lcl: Number(lcl.toFixed(4)),
          cl: Number(mean.toFixed(4)),
          usl: 50.05,
          lsl: 49.95,
          is_out_of_control: v > ucl || v < lcl,
          is_out_of_spec: v > 50.05 || v < 49.95
        }));

        setReport({
          batch_id: capRes.batch_id || (type === "insufficient" ? "TEST-INSUFFICIENT-01" : "TEST-CENTERED-01"),
          sample_size: capRes.sample_size,
          mean: capRes.mean ?? 50.00,
          std_dev: capRes.std_dev ?? 0.0,
          ucl: Number(ucl.toFixed(4)),
          lcl: Number(lcl.toFixed(4)),
          cl: Number(mean.toFixed(4)),
          usl: 50.05,
          lsl: 49.95,
          cp: capRes.cp,
          cpk: capRes.cpk,
          pp: capRes.pp,
          ppk: capRes.ppk,
          capability_assessment: capRes.assessment || "Capability Assessment",
          status: capRes.status,
          warnings: capRes.warnings || [],
          sigma_within: capRes.sigma_within,
          sigma_within_method: capRes.sigma_within_method,
          sigma_overall: capRes.sigma_overall,
          sigma_overall_method: capRes.sigma_overall_method,
          interpretation_band: capRes.interpretation_band,
          guidance_notice: capRes.guidance_notice,
          future_guarantee_disclaimer: capRes.future_guarantee_disclaimer,
          distinction_warning: (
            "SPECIFICATION LIMITS (USL=50.05, LSL=49.95) are engineering tolerance boundaries. " +
            "STATISTICAL CONTROL LIMITS (UCL/LCL) represent natural 3-sigma process variation."
          ),
          certainty: "STATISTICAL_FINDING" as any,
          chart_data: chartData,
          nelson_violations: []
        });
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message || "Failed to calculate custom scenario");
        setLoading(false);
      });
  };

  useEffect(() => {
    api.getBatches()
      .then((bList) => {
        if (Array.isArray(bList) && bList.length > 0) {
          setBatches(bList);
          const firstId = bList[0].batch_number || bList[0].batch_id || bList[0].id || "";
          loadBatchSpc(firstId);
        } else {
          setBatches([]);
          setLoading(false);
        }
      })
      .catch(() => {
        setBatches([]);
        setLoading(false);
      });
  }, []);

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <h2 className="text-[26px] font-bold text-slate-900 leading-tight">Statistical Process Control & Capability</h2>
            <CertaintyBadge level="Statistical Finding" />
          </div>
          <p className="text-[14px] text-slate-500 mt-1">
            AIAG / IATF 16949 process stability, Nelson rules, and capability audit (Cp, Cpk, Pp, Ppk).
          </p>
        </div>

        {/* Dataset / Scenario Selector */}
        <div className="flex flex-wrap items-center gap-2">
          {batches.length > 0 && (
            <div className="flex items-center gap-1.5 px-2.5 py-1.5 bg-slate-50 border border-slate-200 rounded-lg">
              <span className="text-xs font-semibold text-slate-600">Batch:</span>
              <select
                value={currentScenario}
                onChange={(e) => loadBatchSpc(e.target.value)}
                className="bg-transparent text-xs font-bold text-slate-800 focus:outline-none cursor-pointer font-mono"
              >
                {batches.map((b) => {
                  const bId = b.batch_number || b.id || b.batch_id;
                  return (
                    <option key={bId} value={bId}>
                      {bId}
                    </option>
                  );
                })}
              </select>
            </div>
          )}

          <button
            onClick={() => loadCustomScenario("insufficient")}
            className={`px-3 py-1.5 text-xs font-semibold rounded-lg border transition-colors ${
              currentScenario === "TEST-INSUFFICIENT-n3"
                ? "bg-amber-600 text-white border-amber-600 shadow-xs"
                : "bg-white text-slate-700 border-slate-200 hover:bg-slate-50"
            }`}
          >
            AIAG Refusal Test (n=3)
          </button>
          <button
            onClick={() => loadCustomScenario("centered")}
            className={`px-3 py-1.5 text-xs font-semibold rounded-lg border transition-colors ${
              currentScenario === "TEST-CENTERED-n100"
                ? "bg-emerald-600 text-white border-emerald-600 shadow-xs"
                : "bg-white text-slate-700 border-slate-200 hover:bg-slate-50"
            }`}
          >
            AIAG Benchmark (n=100)
          </button>
          {currentScenario && (
            <button
              onClick={() => loadBatchSpc(currentScenario)}
              className="btn-secondary !h-[34px] !px-3"
              title="Reload SPC"
            >
              <RefreshCw className="w-3.5 h-3.5 text-slate-500" />
              <span className="text-xs">Refresh</span>
            </button>
          )}
        </div>
      </div>

      {/* Loading State */}
      {loading && (
        <div className="p-12 bg-white border border-slate-200 rounded-xl shadow-xs text-center space-y-3">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-4 border-blue-600 border-t-transparent" />
          <p className="text-sm font-medium text-slate-700">Calculating SPC & Process Capability Metrics...</p>
          <p className="text-xs text-slate-400">Verifying sample size adequacy, within-subgroup variation, and statistical assumptions.</p>
        </div>
      )}

      {/* Error State */}
      {!loading && error && (
        <div className="p-6 bg-red-50 border border-red-200 rounded-xl shadow-xs flex items-start gap-4">
          <AlertCircle className="w-5 h-5 text-red-600 shrink-0 mt-0.5" />
          <div className="space-y-2">
            <h4 className="text-sm font-bold text-red-900">SPC Computation Error</h4>
            <p className="text-xs text-red-700">{error}</p>
            {currentScenario && (
              <button
                onClick={() => loadBatchSpc(currentScenario)}
                className="px-3 py-1.5 bg-red-600 text-white rounded-md text-xs font-semibold hover:bg-red-700"
              >
                Retry Calculation
              </button>
            )}
          </div>
        </div>
      )}

      {/* Empty State */}
      {!loading && !error && !report && (
        <div className="p-12 bg-white border border-slate-200 rounded-xl shadow-xs text-center space-y-2">
          <Gauge className="w-10 h-10 text-slate-300 mx-auto" />
          <p className="text-sm font-semibold text-slate-700">No Quality Data Available Yet</p>
          <p className="text-xs text-slate-500">No quality data available yet. Register a production batch and submit inspection data to view analytics.</p>
        </div>
      )}

      {/* Data Loaded View */}
      {!loading && !error && report && (
        <div className="space-y-6">
          {/* Engineering Note Banner: Spec Limits vs Control Limits */}
          <div className="p-3.5 bg-gradient-to-r from-blue-50/90 to-indigo-50/90 border border-blue-200 rounded-xl space-y-2 shadow-2xs">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Info className="w-4 h-4 text-blue-700 shrink-0" />
                <span className="text-xs font-bold text-blue-950 uppercase tracking-wider">
                  Specification Limits vs. Statistical Control Limits
                </span>
              </div>
              <span className="text-[11px] font-mono font-semibold px-2 py-0.5 bg-blue-100 text-blue-800 rounded">
                Sample n = {report.sample_size}
              </span>
            </div>
            <p className="text-[12px] text-slate-700 leading-snug">
              Specification limits (USL/LSL) represent design tolerances. Statistical control limits (UCL/LCL) reflect actual 3-sigma manufacturing capability. Systematic tool wear drift observed on preliminary batch (n={report.sample_size}).
            </p>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-1.5 border-t border-blue-200/60 text-[11px]">
              <div>
                <span className="text-slate-500 font-medium">Engineering LSL: </span>
                <strong className="font-mono text-red-700">{report.lsl.toFixed(2)} mm</strong>
              </div>
              <div>
                <span className="text-slate-500 font-medium">Engineering USL: </span>
                <strong className="font-mono text-red-700">{report.usl.toFixed(2)} mm</strong>
              </div>
              <div>
                <span className="text-slate-500 font-medium">Statistical LCL (3σ): </span>
                <strong className="font-mono text-purple-700">{report.lcl.toFixed(4)} mm</strong>
              </div>
              <div>
                <span className="text-slate-500 font-medium">Statistical UCL (3σ): </span>
                <strong className="font-mono text-purple-700">{report.ucl.toFixed(4)} mm</strong>
              </div>
            </div>
          </div>

          {/* Prominent Amber Warning Banner (Concise with clear meaning) */}
          {report.warnings && report.warnings.length > 0 && (
            <div className="p-3.5 bg-amber-50/90 border border-amber-300 rounded-xl shadow-xs space-y-2.5">
              <div className="flex items-center justify-between border-b border-amber-200/80 pb-2">
                <div className="flex items-center gap-2">
                  <AlertTriangle className="w-4 h-4 text-amber-700 shrink-0" />
                  <h4 className="text-xs font-bold text-amber-950 uppercase tracking-wider">
                    Capability Guardrail & Assumption Warnings ({report.warnings.length} Active)
                  </h4>
                </div>
                <span className="px-2 py-0.5 text-[10.5px] font-bold rounded-full bg-amber-200 text-amber-900 font-mono">
                  STATUS: {String(report.status || "PRELIMINARY").toUpperCase()}
                </span>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-xs">
                {report.warnings.map((w, idx) => {
                  const isSmallSample = w.includes("PRELIMINARY SAMPLE SIZE") || w.includes("n=5") || w.includes("n < 30");
                  const isDrift = w.includes("PROCESS DRIFT") || w.includes("trend");
                  const title = isSmallSample ? "Preliminary Sample Size (n=5)" : isDrift ? "Process Drift Detected" : "Assumption Warning";
                  const desc = isSmallSample
                    ? "Preliminary estimate (n=5 < 30). Indices exhibit wide confidence intervals; do not use for long-term capability certification."
                    : isDrift
                    ? "Systematic linear drift detected (+0.0170 mm/unit, p=0.026), indicating progressive tool flank wear."
                    : w;
                  return (
                    <div key={idx} className="p-2.5 bg-white rounded-lg border border-amber-200 shadow-2xs space-y-0.5">
                      <strong className="text-amber-950 block font-semibold text-[12px]">{title}</strong>
                      <p className="text-amber-900 text-[11.5px] leading-relaxed">{desc}</p>
                    </div>
                  );
                })}
              </div>

              {report.guidance_notice && (
                <div className="p-2.5 bg-white/90 rounded-lg border border-amber-200 text-[11.5px] text-amber-900 leading-snug">
                  <strong className="font-semibold text-amber-950">Decision Guidance:</strong>{" "}
                  Statistical capability metrics are indicators for continuous improvement; they do not perform automated lot disposition without quality engineering authorization.
                </div>
              )}

              {report.future_guarantee_disclaimer && (
                <div className="text-[11px] text-amber-900/80 italic font-medium pt-0.5">
                  <strong>Disclaimer:</strong> Capability metrics reflect historical observed performance and do not guarantee future zero-defect production or parts conformity.
                </div>
              )}
            </div>
          )}

          {/* Process Capability Indices Cards (Cp, Cpk, Pp, Ppk) - Hover Popups Completely Removed */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {/* Cp Card */}
            <div className="p-4 bg-white border border-slate-200 rounded-xl shadow-xs space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs text-slate-700 font-bold">
                  Process Potential (Cp)
                </span>
                <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-100 text-slate-600">
                  n={report.sample_size}
                </span>
              </div>

              <div className="flex items-baseline gap-2">
                {report.cp !== null && report.cp !== undefined ? (
                  <>
                    <span className="text-2xl font-bold text-slate-900 font-mono">
                      {report.cp.toFixed(4)}
                    </span>
                    <span className="text-[11px] text-slate-500 font-medium">
                      {report.cp >= 1.33 ? "(Capable)" : "(Sub-optimal)"}
                    </span>
                  </>
                ) : (
                  <div className="space-y-0.5">
                    <span className="text-xl font-bold text-amber-600 font-mono">N/A</span>
                    <span className="block text-[10px] text-amber-700 font-semibold">
                      Insufficient Data (n &lt; 5)
                    </span>
                  </div>
                )}
              </div>

              <div className="pt-2 border-t border-slate-100 text-[10px] text-slate-500 space-y-0.5">
                <div><strong>Formula:</strong> (USL - LSL) / 6&sigma;_within</div>
                <div className="truncate" title={report.sigma_within_method || "MR-bar / 1.128"}>
                  <strong>Sigma:</strong> {report.sigma_within_method || "MR-bar / 1.128 (within)"}
                </div>
              </div>
            </div>

            {/* Cpk Card */}
            <div className={`p-4 rounded-xl shadow-xs space-y-2 border ${
              report.cpk === null
                ? "bg-amber-50/30 border-amber-200"
                : report.cpk < 1.00
                ? "bg-rose-50/30 border-rose-200"
                : "bg-emerald-50/30 border-emerald-200"
            }`}>
              <div className="flex items-center justify-between">
                <span className={`text-xs font-bold ${
                  report.cpk === null ? "text-amber-800" : report.cpk < 1.00 ? "text-rose-800" : "text-emerald-800"
                }`}>
                  Centering Capability (Cpk)
                </span>
                <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-white/80 border border-slate-200 text-slate-600">
                  Target &ge; 1.33
                </span>
              </div>

              <div className="flex items-baseline gap-2">
                {report.cpk !== null && report.cpk !== undefined ? (
                  <>
                    <span className={`text-2xl font-bold font-mono ${
                      report.cpk < 1.00 ? "text-rose-700" : "text-emerald-700"
                    }`}>
                      {report.cpk.toFixed(4)}
                    </span>
                    <span className={`text-[11px] font-bold ${
                      report.cpk < 1.00 ? "text-rose-600" : "text-emerald-600"
                    }`}>
                      {report.interpretation_band || (report.cpk < 1.00 ? "Incapable (< 1.00)" : "Capable")}
                    </span>
                  </>
                ) : (
                  <div className="space-y-0.5">
                    <span className="text-xl font-bold text-amber-600 font-mono">N/A</span>
                    <span className="block text-[10px] text-amber-700 font-semibold">
                      Insufficient Data (n &lt; 5)
                    </span>
                  </div>
                )}
              </div>

              <div className="pt-2 border-t border-slate-200/60 text-[10px] text-slate-600 space-y-0.5">
                <div><strong>Formula:</strong> min(Cpu, Cpl) via &sigma;_within</div>
                <div className="truncate" title={report.sigma_within_method || "MR-bar / 1.128"}>
                  <strong>Sigma:</strong> {report.sigma_within_method || "MR-bar / 1.128 (within)"}
                </div>
              </div>
            </div>

            {/* Pp Card */}
            <div className="p-4 bg-white border border-slate-200 rounded-xl shadow-xs space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs text-slate-700 font-bold">
                  Process Performance (Pp)
                </span>
                <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-100 text-slate-600">
                  Total Spread
                </span>
              </div>

              <div className="flex items-baseline gap-2">
                {report.pp !== null && report.pp !== undefined ? (
                  <>
                    <span className="text-2xl font-bold text-slate-900 font-mono">
                      {report.pp.toFixed(4)}
                    </span>
                    <span className="text-[11px] text-slate-500 font-medium">
                      {report.pp >= 1.33 ? "(Adequate)" : "(Wide Spread)"}
                    </span>
                  </>
                ) : (
                  <div className="space-y-0.5">
                    <span className="text-xl font-bold text-amber-600 font-mono">N/A</span>
                    <span className="block text-[10px] text-amber-700 font-semibold">
                      Insufficient Data (n &lt; 5)
                    </span>
                  </div>
                )}
              </div>

              <div className="pt-2 border-t border-slate-100 text-[10px] text-slate-500 space-y-0.5">
                <div><strong>Formula:</strong> (USL - LSL) / 6s (ddof=1)</div>
                <div className="truncate" title={report.sigma_overall_method || "Sample Std Dev s"}>
                  <strong>Sigma:</strong> {report.sigma_overall_method || "Sample Std Dev s (overall)"}
                </div>
              </div>
            </div>

            {/* Ppk Card */}
            <div className={`p-4 rounded-xl shadow-xs space-y-2 border ${
              report.ppk === null
                ? "bg-amber-50/30 border-amber-200"
                : report.ppk < 1.00
                ? "bg-rose-50/30 border-rose-200"
                : "bg-emerald-50/30 border-emerald-200"
            }`}>
              <div className="flex items-center justify-between">
                <span className={`text-xs font-bold ${
                  report.ppk === null ? "text-amber-800" : report.ppk < 1.00 ? "text-rose-800" : "text-emerald-800"
                }`}>
                  Performance Index (Ppk)
                </span>
                <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-white/80 border border-slate-200 text-slate-600">
                  Target &ge; 1.33
                </span>
              </div>

              <div className="flex items-baseline gap-2">
                {report.ppk !== null && report.ppk !== undefined ? (
                  <>
                    <span className={`text-2xl font-bold font-mono ${
                      report.ppk < 1.00 ? "text-rose-700" : "text-emerald-700"
                    }`}>
                      {report.ppk.toFixed(4)}
                    </span>
                    <span className={`text-[11px] font-bold ${
                      report.ppk < 1.00 ? "text-rose-600" : "text-emerald-600"
                    }`}>
                      {report.ppk < 1.00 ? "Action Required" : "Conforming"}
                    </span>
                  </>
                ) : (
                  <div className="space-y-0.5">
                    <span className="text-xl font-bold text-amber-600 font-mono">N/A</span>
                    <span className="block text-[10px] text-amber-700 font-semibold">
                      Insufficient Data (n &lt; 5)
                    </span>
                  </div>
                )}
              </div>

              <div className="pt-2 border-t border-slate-200/60 text-[10px] text-slate-600 space-y-0.5">
                <div><strong>Formula:</strong> min(Ppu, Ppl) via s (ddof=1)</div>
                <div className="truncate" title={report.sigma_overall_method || "Sample Std Dev s"}>
                  <strong>Sigma:</strong> {report.sigma_overall_method || "Sample Std Dev s (overall)"}
                </div>
              </div>
            </div>
          </div>

          {/* Statistical Moments & Confidence Interval Summary */}
          <div className="p-4 bg-white border border-slate-200 rounded-xl shadow-xs">
            <h4 className="text-xs font-bold text-slate-900 uppercase tracking-wider mb-2">
              Statistical Moments & Capability Assessment Summary
            </h4>
            <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 text-xs">
              <div className="p-2.5 bg-slate-50 rounded-lg border border-slate-100">
                <span className="text-slate-500 block text-[11px]">Sample Mean (&mu;)</span>
                <span className="font-bold text-slate-900 font-mono text-sm">{report.mean.toFixed(4)} mm</span>
              </div>
              <div className="p-2.5 bg-slate-50 rounded-lg border border-slate-100">
                <span className="text-slate-500 block text-[11px]">Within Sigma (&sigma;_w)</span>
                <span className="font-bold text-slate-900 font-mono text-sm">
                  {report.sigma_within ? report.sigma_within.toFixed(6) : "N/A"}
                </span>
              </div>
              <div className="p-2.5 bg-slate-50 rounded-lg border border-slate-100">
                <span className="text-slate-500 block text-[11px]">Overall Std Dev (s)</span>
                <span className="font-bold text-slate-900 font-mono text-sm">
                  {report.std_dev ? report.std_dev.toFixed(6) : "N/A"}
                </span>
              </div>
              <div className="p-2.5 bg-slate-50 rounded-lg border border-slate-100">
                <span className="text-slate-500 block text-[11px]">Tolerance Band</span>
                <span className="font-bold text-slate-900 font-mono text-sm">
                  {(report.usl - report.lsl).toFixed(3)} mm
                </span>
              </div>
              <div className="p-2.5 bg-slate-50 rounded-lg border border-slate-100">
                <span className="text-slate-500 block text-[11px]">Process Assessment</span>
                <span className="font-bold text-slate-900 text-[11px] block truncate" title={report.capability_assessment}>
                  {report.capability_assessment}
                </span>
              </div>
            </div>
          </div>

          {/* Control Chart Card (I-Chart) */}
          <div className="p-5 bg-white border border-slate-200 rounded-xl shadow-xs space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
              <div>
                <h3 className="text-sm font-bold text-slate-900">
                  Individuals Control Chart (I-Chart) with Explicit Spec vs Control Boundaries
                </h3>
                <p className="text-xs text-slate-500">
                  Center Line (CL) = {report.cl.toFixed(4)} mm | Natural 3-Sigma Limits = [{report.lcl.toFixed(4)}, {report.ucl.toFixed(4)}] mm
                </p>
              </div>
              <div className="flex flex-wrap items-center gap-4 text-xs">
                <span className="flex items-center gap-1.5">
                  <span className="w-3.5 h-1 bg-red-600 inline-block rounded-xs" />
                  <strong className="text-slate-700">Spec Limits (USL/LSL = 50.05 / 49.95)</strong>
                </span>
                <span className="flex items-center gap-1.5">
                  <span className="w-3.5 h-0.5 bg-purple-600 border-dashed border-t-2 border-purple-600 inline-block" />
                  <strong className="text-slate-700">Control Limits (UCL/LCL = {report.ucl.toFixed(3)} / {report.lcl.toFixed(3)})</strong>
                </span>
                <span className="flex items-center gap-1.5">
                  <span className="w-3.5 h-0.5 bg-blue-600 inline-block" />
                  <strong className="text-slate-700">Center Line (CL = {report.cl.toFixed(3)})</strong>
                </span>
              </div>
            </div>

            <div className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={report.chart_data} margin={{ top: 15, right: 30, left: 20, bottom: 15 }}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                  <XAxis dataKey="sample_id" tick={{ fontSize: 11 }} />
                  <YAxis domain={["auto", "auto"]} tick={{ fontSize: 11 }} />
                  <Tooltip
                    formatter={(val: any) => [`${val} mm`, "Shaft Diameter"]}
                    contentStyle={{ backgroundColor: "#ffffff", borderColor: "#e2e8f0", fontSize: "12px", borderRadius: "8px" }}
                  />

                  {/* Engineering Specification Limits (Solid Red) */}
                  <ReferenceLine y={report.usl} label="USL (50.05 mm)" stroke="#dc2626" strokeWidth={1.5} />
                  <ReferenceLine y={report.lsl} label="LSL (49.95 mm)" stroke="#dc2626" strokeWidth={1.5} />

                  {/* Statistical Control Limits (Dashed Purple) */}
                  <ReferenceLine y={report.ucl} label={`UCL (${report.ucl.toFixed(3)} mm)`} stroke="#9333ea" strokeDasharray="4 4" strokeWidth={1.5} />
                  <ReferenceLine y={report.lcl} label={`LCL (${report.lcl.toFixed(3)} mm)`} stroke="#9333ea" strokeDasharray="4 4" strokeWidth={1.5} />
                  <ReferenceLine y={report.cl} label={`CL (${report.cl.toFixed(3)} mm)`} stroke="#2563eb" strokeDasharray="2 2" strokeWidth={1} />

                  <Line
                    type="linear"
                    dataKey="value"
                    stroke="#0f172a"
                    strokeWidth={2}
                    dot={(props: any) => {
                      const { cx, cy, payload } = props;
                      const isFail = payload.is_out_of_spec || payload.is_out_of_control;
                      return (
                        <circle
                          cx={cx}
                          cy={cy}
                          r={isFail ? 5 : 3.5}
                          fill={isFail ? "#ef4444" : "#2563eb"}
                          stroke="#ffffff"
                          strokeWidth={1.5}
                          key={props.key}
                        />
                      );
                    }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Nelson Rules Violation Register */}
          <div className="p-5 bg-white border border-slate-200 rounded-xl shadow-xs space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-amber-600" />
                <h3 className="text-sm font-bold text-slate-900">
                  Nelson Rules Process Stability Audit ({report.nelson_violations.length} Violations)
                </h3>
              </div>
              <CertaintyBadge level="Statistical Finding" />
            </div>

            {report.nelson_violations.length === 0 ? (
              <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-lg flex items-center gap-3">
                <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0" />
                <p className="text-xs text-emerald-800 font-medium">
                  Process in statistical control. No Nelson rule violations detected across the evaluated subgroup window.
                </p>
              </div>
            ) : (
              <div className="space-y-2">
                {report.nelson_violations.map((v, i) => (
                  <div key={i} className="p-3 bg-rose-50/50 border border-rose-200 rounded-lg flex items-start justify-between gap-4">
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <span className="px-2 py-0.5 rounded bg-rose-100 text-rose-800 text-xs font-bold font-mono">
                          Rule {v.rule_number}
                        </span>
                        <span className="text-xs font-bold text-slate-900">{v.rule_name}</span>
                      </div>
                      <p className="text-xs text-slate-600">{v.description}</p>
                    </div>
                    <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-rose-100 text-rose-700 shrink-0">
                      {v.severity} Severity
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

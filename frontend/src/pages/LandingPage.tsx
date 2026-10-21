import React, { useState, useEffect } from "react";
import {
  ShieldCheck, ArrowRight, Eye, Ruler, Activity, BarChart2,
  GitFork, CheckCircle, FileText, ChevronRight, Lock,
  Cpu, Users, Layers, Award, Sparkles, AlertTriangle, Play, Pause,
  RefreshCw, Zap, Sliders, Database, FileCheck, CheckCircle2
} from "lucide-react";
import {
  ResponsiveContainer, LineChart, Line, XAxis, YAxis, Tooltip, ReferenceLine, CartesianGrid
} from "recharts";

interface Props {
  onNavigateToLogin: (defaultRole?: "quality_engineer" | "operator") => void;
  onExplore: () => void;
}

export const LandingPage: React.FC<Props> = ({ onNavigateToLogin, onExplore }) => {

  const [prefersReducedMotion, setPrefersReducedMotion] = useState<boolean>(() => {
    if (typeof window !== "undefined" && window.matchMedia) {
      return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    }
    return false;
  });

  const [telemetryData, setTelemetryData] = useState<any[]>([
    { sample: "101", diameter: 50.008, vibration: 2.12 },
    { sample: "102", diameter: 49.994, vibration: 2.08 },
    { sample: "103", diameter: 50.015, vibration: 2.18 },
    { sample: "104", diameter: 50.002, vibration: 2.11 },
    { sample: "105", diameter: 49.998, vibration: 2.14 },
    { sample: "106", diameter: 50.012, vibration: 2.20 },
    { sample: "107", diameter: 50.006, vibration: 2.09 },
    { sample: "108", diameter: 49.995, vibration: 2.15 },
    { sample: "109", diameter: 50.018, vibration: 2.22 },
    { sample: "110", diameter: 50.004, vibration: 2.10 },
  ]);
  const [liveSampleCount, setLiveSampleCount] = useState(110);
  const [liveDiameter, setLiveDiameter] = useState<number | null>(50.004);
  const [liveVibration, setLiveVibration] = useState<number | null>(2.10);
  const [liveCpk, setLiveCpk] = useState<number | null>(1.42);
  const [systemBatchesCount, setSystemBatchesCount] = useState(0);

  useEffect(() => {
    if (typeof window === "undefined" || !window.matchMedia) return;
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    const handler = (e: MediaQueryListEvent) => setPrefersReducedMotion(e.matches);
    mq.addEventListener("change", handler);
    return () => mq.removeEventListener("change", handler);
  }, []);

  useEffect(() => {
    import("../api").then(({ api }) => {
      api.getDashboardSummary().then((sum) => {
        if (sum) {
          if (sum.total_batches) setSystemBatchesCount(sum.total_batches);
          if (sum.total_inspected_parts) setLiveSampleCount(sum.total_inspected_parts);
          if (sum.process_control_status?.cpk !== null && sum.process_control_status?.cpk !== undefined) {
            setLiveCpk(sum.process_control_status.cpk);
          }
        }
      }).catch(() => {});
    });
  }, []);

  // Clean static baseline for landing view without continuous timer loops


  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 font-sans antialiased selection:bg-blue-500 selection:text-white">

      <header className="sticky top-0 z-50 bg-white/95 backdrop-blur-md border-b border-slate-200/80 shadow-xs">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-24 flex items-center justify-between">
          <div
            className="flex items-center cursor-pointer group"
            onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}
          >
            <img
              src="/logo.png"
              alt="QualiForge Logo"
              className="h-16 sm:h-18 md:h-20 w-auto object-contain drop-shadow-[0_2px_12px_rgba(37,99,235,0.24)] group-hover:drop-shadow-[0_4px_22px_rgba(37,99,235,0.36)] group-hover:scale-[1.03] transition-all duration-300"
            />
          </div>

          <nav className="hidden md:flex items-center gap-8 text-sm font-medium text-slate-600">
            <a href="#capabilities" className="hover:text-blue-600 transition-colors">Capabilities</a>
            <a href="#workflow" className="hover:text-blue-600 transition-colors">How It Works</a>
            <a href="#roles" className="hover:text-blue-600 transition-colors">Workspaces</a>
            <a href="#governance" className="hover:text-blue-600 transition-colors">Trust & Governance</a>
          </nav>

          <div className="flex items-center gap-3">
            <button
              onClick={() => onNavigateToLogin()}
              className="px-4 py-2.5 text-sm font-semibold text-slate-700 hover:text-slate-900 hover:bg-slate-100 rounded-lg transition-all cursor-pointer"
            >
              Sign In
            </button>
            <button
              onClick={onExplore}
              className="px-5 py-2.5 text-sm font-semibold text-white bg-blue-600 hover:bg-blue-700 active:bg-blue-800 rounded-lg shadow-xs hover:shadow transition-all flex items-center gap-1.5 cursor-pointer"
            >
              Get Started <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      </header>

      <section className="relative overflow-hidden pt-12 pb-20 lg:pt-16 lg:pb-24 bg-gradient-to-b from-white via-slate-50 to-slate-100 border-b border-slate-200/60">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-10 lg:gap-12 items-center">

            <div className="lg:col-span-6 flex flex-col items-start text-left">
              <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-blue-50 border border-blue-200 text-blue-700 text-xs font-semibold uppercase tracking-wider mb-6 shadow-2xs">
                <Sparkles className="w-3.5 h-3.5" />
                Agentic AI Decision-Support Platform
              </div>

              <h1 className="text-4xl sm:text-5xl lg:text-[52px] font-extrabold text-slate-900 tracking-tight leading-[1.12]">
                Manufacturing Quality Intelligence. <br />
                <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-600 via-indigo-600 to-blue-800">
                  From Detection to Root Cause.
                </span>
              </h1>

              <p className="mt-6 text-base sm:text-lg text-slate-600 leading-relaxed font-normal max-w-xl">
                Unify visual inspection, dimensional compliance, process monitoring, statistical analysis,
                and evidence-based root cause investigation in one AI-assisted quality platform.
              </p>

              <div className="mt-8 flex flex-col sm:flex-row items-stretch sm:items-center gap-4 w-full sm:w-auto">
                <button
                  onClick={onExplore}
                  className="px-7 py-3.5 text-base font-semibold text-white bg-blue-600 hover:bg-blue-700 active:bg-blue-800 rounded-xl shadow-md hover:shadow-lg transition-all flex items-center justify-center gap-2 cursor-pointer"
                >
                  Explore the Platform <ChevronRight className="w-5 h-5" />
                </button>
                <button
                  onClick={() => onNavigateToLogin()}
                  className="px-7 py-3.5 text-base font-semibold text-slate-700 bg-white hover:bg-slate-50 border border-slate-300 rounded-xl shadow-xs transition-all flex items-center justify-center gap-2 cursor-pointer"
                >
                  Sign In to Workspace
                </button>
              </div>

              <div className="mt-8 pt-6 border-t border-slate-200/80 w-full flex flex-wrap items-center gap-6 text-xs text-slate-500 font-medium">
                <div className="flex items-center gap-1.5">
                  <ShieldCheck className="w-4 h-4 text-emerald-600" />
                  <span>ISO 9001 / IATF 16949 Compliant</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <Cpu className="w-4 h-4 text-blue-600" />
                  <span>Human-in-the-Loop Gate</span>
                </div>
              </div>
            </div>

            <div className="lg:col-span-6 w-full">
              <div className="bg-slate-900 rounded-2xl shadow-xl border border-slate-800 p-5 sm:p-6 text-white relative overflow-hidden">

                <div className="absolute -top-24 -right-24 w-60 h-60 bg-blue-600/20 rounded-full blur-3xl pointer-events-none" />

                <div className="flex flex-wrap items-center justify-between gap-3 pb-4 border-b border-slate-800">
                  <div className="flex items-center gap-2.5">
                    <span className="relative flex h-3 w-3">
                      <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                      <span className="relative inline-flex rounded-full h-3 w-3 bg-emerald-500"></span>
                    </span>
                    <span className="text-xs font-mono font-bold tracking-wider text-emerald-400">
                      LIVE SHOP FLOOR STREAM
                    </span>
                  </div>
                  <div className="flex items-center gap-2 text-[11px] font-mono text-slate-400">
                    <span className="px-2 py-0.5 rounded bg-slate-800 border border-slate-700 text-blue-300">
                      Precision Quality Intelligence
                    </span>
                    <span className="px-2 py-0.5 rounded bg-slate-800 border border-slate-700 text-slate-300">
                      Standard PS-2026-101
                    </span>
                  </div>
                </div>

                <div className="mt-4 grid grid-cols-3 gap-3">
                  <div className="p-3 rounded-xl bg-slate-800/80 border border-slate-700/60 transition-all">
                    <div className="text-[11px] font-medium text-slate-400">Specification Nominal</div>
                    <div className="mt-1 text-lg sm:text-xl font-bold font-mono text-white tracking-tight">
                      {liveDiameter !== null ? liveDiameter.toFixed(3) : "50.000"} <span className="text-xs text-slate-400 font-sans">mm</span>
                    </div>
                    <div className="mt-1 text-[10px] text-emerald-400 font-medium flex items-center gap-1">
                      <CheckCircle className="w-3 h-3" /> Bilateral ±0.05 mm
                    </div>
                  </div>

                  <div className="p-3 rounded-xl bg-slate-800/80 border border-slate-700/60 transition-all">
                    <div className="text-[11px] font-medium text-slate-400">Machinery Baseline</div>
                    <div className="mt-1 text-lg sm:text-xl font-bold font-mono text-white tracking-tight">
                      {liveVibration !== null ? liveVibration.toFixed(2) : "2.10"} <span className="text-xs text-slate-400 font-sans">mm/s</span>
                    </div>
                    <div className="mt-1 text-[10px] text-blue-400 font-medium flex items-center gap-1">
                      <Activity className="w-3 h-3" /> Trip Limit 3.50 mm/s
                    </div>
                  </div>

                  <div className="p-3 rounded-xl bg-slate-800/80 border border-slate-700/60 transition-all">
                    <div className="text-[11px] font-medium text-slate-400">Quality Benchmark</div>
                    <div className="mt-1 text-lg sm:text-xl font-bold font-mono text-emerald-400 tracking-tight">
                      {liveCpk !== null ? liveCpk.toFixed(2) : "Cpk ≥ 1.33"}
                    </div>
                    <div className="mt-1 text-[10px] text-emerald-400 font-medium flex items-center gap-1">
                      <ShieldCheck className="w-3 h-3" /> AIAG Reference
                    </div>
                  </div>
                </div>

                <div className="mt-5 p-3.5 rounded-xl bg-slate-950/80 border border-slate-800">
                  <div className="flex items-center justify-between text-xs font-medium text-slate-400 mb-2">
                    <div className="flex items-center gap-2">
                      <BarChart2 className="w-3.5 h-3.5 text-blue-400" />
                      <span>Process Tolerance Envelope (I-MR Control Chart)</span>
                    </div>
                    <div className="flex items-center gap-3 text-[10px] font-mono">
                      <span className="flex items-center gap-1 text-rose-400">
                        <span className="w-2 h-0.5 bg-rose-500 inline-block" /> USL 50.05
                      </span>
                      <span className="flex items-center gap-1 text-emerald-400">
                        <span className="w-2 h-0.5 bg-emerald-500 inline-block" /> CL 50.00
                      </span>
                      <span className="flex items-center gap-1 text-rose-400">
                        <span className="w-2 h-0.5 bg-rose-500 inline-block" /> LSL 49.95
                      </span>
                    </div>
                  </div>

                  <div className="h-44 w-full flex items-center justify-center">
                    {telemetryData.length > 0 ? (
                      <ResponsiveContainer width="100%" height="100%">
                        <LineChart data={telemetryData} margin={{ top: 8, right: 10, left: -25, bottom: 0 }}>
                          <CartesianGrid strokeDasharray="3 3" stroke="#334155" opacity={0.5} />
                          <XAxis
                            dataKey="sample"
                            tick={{ fill: "#94a3b8", fontSize: 10 }}
                            tickLine={{ stroke: "#475467" }}
                          />
                          <YAxis
                            domain={[49.94, 50.06]}
                            tick={{ fill: "#94a3b8", fontSize: 10 }}
                            tickLine={{ stroke: "#475467" }}
                          />
                          <Tooltip
                            contentStyle={{
                              backgroundColor: "#0f172a",
                              borderColor: "#334155",
                              borderRadius: "8px",
                              fontSize: "11px",
                              color: "#fff"
                            }}
                            formatter={(value: any) => [`${Number(value).toFixed(3)} mm`, "Diameter"]}
                            labelFormatter={(label) => `Sample #${label}`}
                          />
                          <ReferenceLine y={50.05} stroke="#ef4444" strokeDasharray="3 3" />
                          <ReferenceLine y={50.00} stroke="#10b981" strokeDasharray="2 2" />
                          <ReferenceLine y={49.95} stroke="#ef4444" strokeDasharray="3 3" />
                          <Line
                            type="monotone"
                            dataKey="diameter"
                            stroke="#38bdf8"
                            strokeWidth={2.5}
                            dot={{ fill: "#38bdf8", r: 3, stroke: "#0284c7", strokeWidth: 1.5 }}
                            activeDot={{ r: 5, fill: "#38bdf8" }}
                            isAnimationActive={!prefersReducedMotion}
                            animationDuration={500}
                          />
                        </LineChart>
                      </ResponsiveContainer>
                    ) : (
                      <div className="text-center p-4">
                        <Activity className="w-8 h-8 text-blue-400/60 mx-auto mb-2" />
                        <p className="text-xs text-slate-300 font-medium">
                          Quality Engine Idle &bull; Ready for Batch Data Ingestion
                        </p>
                        <p className="text-[11px] text-slate-500 mt-1 max-w-sm">
                          Register a production batch and stream inspection measurements to activate live SPC charts.
                        </p>
                      </div>
                    )}
                  </div>
                </div>

                <div className="mt-4 pt-3 border-t border-slate-800 flex items-center justify-between text-[11px] font-mono text-slate-400">
                  <div className="flex items-center gap-1.5 text-emerald-400 font-semibold">
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    <span>Inspection Multi-Agent System: READY</span>
                  </div>
                  <div>
                    {systemBatchesCount > 0 ? (
                      <span>{systemBatchesCount} Active Batches &bull; {liveSampleCount} Inspected</span>
                    ) : (
                      <span>Clean State &bull; Awaiting Batch Registration</span>
                    )}
                  </div>
                </div>
              </div>
            </div>

          </div>
        </div>
      </section>

      <section id="capabilities" className="py-20 bg-white border-b border-slate-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center max-w-3xl mx-auto">
            <h2 className="text-xs font-bold text-blue-600 uppercase tracking-widest">Platform Capabilities</h2>
            <p className="mt-2 text-3xl sm:text-4xl font-extrabold text-slate-900 tracking-tight">
              Enterprise Quality Inspection Engine
            </p>
            <p className="mt-4 text-base text-slate-600">
              Eight autonomous micro-agents collaborating under deterministic engineering rules to deliver end-to-end quality assurance.
            </p>
          </div>

          <div className="mt-16 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            <div className="p-6 rounded-xl bg-slate-50 border border-slate-200/90 hover:border-blue-300 hover:shadow-md transition-all">
              <div className="w-11 h-11 rounded-lg bg-blue-100 text-blue-700 flex items-center justify-center mb-4">
                <Eye className="w-5 h-5" />
              </div>
              <h3 className="text-lg font-bold text-slate-900">AI Visual Inspection</h3>
              <p className="mt-2 text-sm text-slate-600 leading-relaxed">
                Automated surface defect localization and classification using YOLOv8 with millimeter bounding-box coordinates,
                confidence scoring, and explicit model prediction labeling.
              </p>
            </div>

            <div className="p-6 rounded-xl bg-slate-50 border border-slate-200/90 hover:border-blue-300 hover:shadow-md transition-all">
              <div className="w-11 h-11 rounded-lg bg-indigo-100 text-indigo-700 flex items-center justify-center mb-4">
                <Ruler className="w-5 h-5" />
              </div>
              <h3 className="text-lg font-bold text-slate-900">Dimensional Compliance</h3>
              <p className="mt-2 text-sm text-slate-600 leading-relaxed">
                Deterministic measurement verification against Upper (USL) and Lower (LSL) engineering specification limits.
                Boundary-safe delta calculations and conforming unit counts.
              </p>
            </div>

            <div className="p-6 rounded-xl bg-slate-50 border border-slate-200/90 hover:border-blue-300 hover:shadow-md transition-all">
              <div className="w-11 h-11 rounded-lg bg-amber-100 text-amber-700 flex items-center justify-center mb-4">
                <Activity className="w-5 h-5" />
              </div>
              <h3 className="text-lg font-bold text-slate-900">Process Monitoring</h3>
              <p className="mt-2 text-sm text-slate-600 leading-relaxed">
                Real-time ingestion of CNC telemetry, spindle vibration metrics, tool cycle counters, and thermal drift
                streams to detect physical abnormalities before tolerance breaches occur.
              </p>
            </div>

            <div className="p-6 rounded-xl bg-slate-50 border border-slate-200/90 hover:border-blue-300 hover:shadow-md transition-all">
              <div className="w-11 h-11 rounded-lg bg-emerald-100 text-emerald-700 flex items-center justify-center mb-4">
                <BarChart2 className="w-5 h-5" />
              </div>
              <h3 className="text-lg font-bold text-slate-900">Statistical Process Control</h3>
              <p className="mt-2 text-sm text-slate-600 leading-relaxed">
                I-MR individuals control charting, Nelson rule pattern trips, and sample-verified Cp/Cpk calculations
                distinguishing statistical control limits from product specifications.
              </p>
            </div>

            <div className="p-6 rounded-xl bg-slate-50 border border-slate-200/90 hover:border-blue-300 hover:shadow-md transition-all">
              <div className="w-11 h-11 rounded-lg bg-purple-100 text-purple-700 flex items-center justify-center mb-4">
                <GitFork className="w-5 h-5" />
              </div>
              <h3 className="text-lg font-bold text-slate-900">Root Cause Analysis</h3>
              <p className="mt-2 text-sm text-slate-600 leading-relaxed">
                Evidence-based causal investigation combining 6M Ishikawa categorization, 5-Whys deductive chains, and
                vector retrieval of historical non-conformance records (NCRs).
              </p>
            </div>

            <div className="p-6 rounded-xl bg-slate-50 border border-slate-200/90 hover:border-blue-300 hover:shadow-md transition-all">
              <div className="w-11 h-11 rounded-lg bg-teal-100 text-teal-700 flex items-center justify-center mb-4">
                <CheckCircle className="w-5 h-5" />
              </div>
              <h3 className="text-lg font-bold text-slate-900">Corrective Actions (CAPA)</h3>
              <p className="mt-2 text-sm text-slate-600 leading-relaxed">
                Structured 3-tier action plans covering immediate physical containment, process correction, and preventive
                mistake-proofing with two-proportion statistical effectiveness verification.
              </p>
            </div>

            <div className="p-6 rounded-xl bg-slate-50 border border-slate-200/90 hover:border-blue-300 hover:shadow-md transition-all">
              <div className="w-11 h-11 rounded-lg bg-rose-100 text-rose-700 flex items-center justify-center mb-4">
                <ShieldCheck className="w-5 h-5" />
              </div>
              <h3 className="text-lg font-bold text-slate-900">Human Quality Review</h3>
              <p className="mt-2 text-sm text-slate-600 leading-relaxed">
                Enforces Human-in-the-Loop decision governance. Machine disposition, root cause confirmation, and batch
                release require authorized engineer sign-off.
              </p>
            </div>

            <div className="p-6 rounded-xl bg-slate-50 border border-slate-200/90 hover:border-blue-300 hover:shadow-md transition-all">
              <div className="w-11 h-11 rounded-lg bg-slate-200 text-slate-800 flex items-center justify-center mb-4">
                <FileText className="w-5 h-5" />
              </div>
              <h3 className="text-lg font-bold text-slate-900">Quality Reporting</h3>
              <p className="mt-2 text-sm text-slate-600 leading-relaxed">
                Generates official ISO 9001 and IATF 16949 audit dossier PDF documentation streaming directly
                from backend evaluation services with immutable audit records.
              </p>
            </div>
          </div>
        </div>
      </section>

      <section id="workflow" className="py-20 bg-slate-900 text-white border-b border-slate-800">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center max-w-3xl mx-auto mb-14">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-blue-950 text-blue-400 border border-blue-800 text-xs font-mono uppercase tracking-widest mb-3">
              <Zap className="w-3.5 h-3.5 text-blue-400" /> Multi-Agent Quality Architecture
            </div>
            <h2 className="text-3xl sm:text-4xl font-extrabold text-white tracking-tight">
              8-Agent Autonomous Quality Pipeline
            </h2>
            <p className="mt-3 text-base text-slate-300">
              Deterministic specification verification, computer vision defect detection, statistical process control,
              and Bayesian causal diagnosis orchestrated with Human-in-the-Loop governance.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="p-5 rounded-xl bg-slate-800/80 border border-slate-700/80 hover:border-blue-500 transition-all">
              <div className="flex items-center justify-between mb-3">
                <span className="w-7 h-7 rounded-md font-mono text-xs font-bold bg-blue-600 text-white flex items-center justify-center">01</span>
                <span className="text-[10px] font-mono text-blue-400 uppercase tracking-wider font-semibold">Intake</span>
              </div>
              <h4 className="text-base font-bold text-white">Data Intake Agent</h4>
              <p className="mt-2 text-xs text-slate-400 leading-relaxed">
                Automated schema validation, unit standardization (inches to mm), and operator notes extraction.
              </p>
            </div>

            <div className="p-5 rounded-xl bg-slate-800/80 border border-slate-700/80 hover:border-blue-500 transition-all">
              <div className="flex items-center justify-between mb-3">
                <span className="w-7 h-7 rounded-md font-mono text-xs font-bold bg-indigo-600 text-white flex items-center justify-center">02</span>
                <span className="text-[10px] font-mono text-indigo-400 uppercase tracking-wider font-semibold">Vision</span>
              </div>
              <h4 className="text-base font-bold text-white">Computer Vision Agent</h4>
              <p className="mt-2 text-xs text-slate-400 leading-relaxed">
                YOLOv8 surface defect detection with bounding box localization, confidence scoring, and product mismatch guardrails.
              </p>
            </div>

            <div className="p-5 rounded-xl bg-slate-800/80 border border-slate-700/80 hover:border-blue-500 transition-all">
              <div className="flex items-center justify-between mb-3">
                <span className="w-7 h-7 rounded-md font-mono text-xs font-bold bg-emerald-600 text-white flex items-center justify-center">03</span>
                <span className="text-[10px] font-mono text-emerald-400 uppercase tracking-wider font-semibold">Compliance</span>
              </div>
              <h4 className="text-base font-bold text-white">Dimensional Agent</h4>
              <p className="mt-2 text-xs text-slate-400 leading-relaxed">
                Deterministic comparison of CMM measurements against nominal ± tolerance engineering limits (USL/LSL).
              </p>
            </div>

            <div className="p-5 rounded-xl bg-slate-800/80 border border-slate-700/80 hover:border-blue-500 transition-all">
              <div className="flex items-center justify-between mb-3">
                <span className="w-7 h-7 rounded-md font-mono text-xs font-bold bg-amber-600 text-white flex items-center justify-center">04</span>
                <span className="text-[10px] font-mono text-amber-400 uppercase tracking-wider font-semibold">Telemetry</span>
              </div>
              <h4 className="text-base font-bold text-white">Process Monitoring Agent</h4>
              <p className="mt-2 text-xs text-slate-400 leading-relaxed">
                Machine vibration spike detection, spindle RPM, feed rate drift, and Isolation Forest ML anomaly analysis.
              </p>
            </div>

            <div className="p-5 rounded-xl bg-slate-800/80 border border-slate-700/80 hover:border-blue-500 transition-all">
              <div className="flex items-center justify-between mb-3">
                <span className="w-7 h-7 rounded-md font-mono text-xs font-bold bg-cyan-600 text-white flex items-center justify-center">05</span>
                <span className="text-[10px] font-mono text-cyan-400 uppercase tracking-wider font-semibold">Capability</span>
              </div>
              <h4 className="text-base font-bold text-white">SPC Capability Agent</h4>
              <p className="mt-2 text-xs text-slate-400 leading-relaxed">
                I-MR individuals control charting, Nelson rule pattern trips, and statistical process capability (Cp / Cpk).
              </p>
            </div>

            <div className="p-5 rounded-xl bg-slate-800/80 border border-slate-700/80 hover:border-blue-500 transition-all">
              <div className="flex items-center justify-between mb-3">
                <span className="w-7 h-7 rounded-md font-mono text-xs font-bold bg-purple-600 text-white flex items-center justify-center">06</span>
                <span className="text-[10px] font-mono text-purple-400 uppercase tracking-wider font-semibold">Diagnosis</span>
              </div>
              <h4 className="text-base font-bold text-white">RCA Reasoning Agent</h4>
              <p className="mt-2 text-xs text-slate-400 leading-relaxed">
                6M Ishikawa categorization, 5-Whys causal synthesis, RAG historical NCR matching, and Bayesian probability updating.
              </p>
            </div>

            <div className="p-5 rounded-xl bg-slate-800/80 border border-slate-700/80 hover:border-blue-500 transition-all">
              <div className="flex items-center justify-between mb-3">
                <span className="w-7 h-7 rounded-md font-mono text-xs font-bold bg-rose-600 text-white flex items-center justify-center">07</span>
                <span className="text-[10px] font-mono text-rose-400 uppercase tracking-wider font-semibold">Governance</span>
              </div>
              <h4 className="text-base font-bold text-white">Critic Reviewer Agent</h4>
              <p className="mt-2 text-xs text-slate-400 leading-relaxed">
                Audits causal claims, checks calculation consistency, and enforces IATF safety guardrails against unauthorized machine overrides.
              </p>
            </div>

            <div className="p-5 rounded-xl bg-slate-800/80 border border-slate-700/80 hover:border-blue-500 transition-all">
              <div className="flex items-center justify-between mb-3">
                <span className="w-7 h-7 rounded-md font-mono text-xs font-bold bg-teal-600 text-white flex items-center justify-center">08</span>
                <span className="text-[10px] font-mono text-teal-400 uppercase tracking-wider font-semibold">Action</span>
              </div>
              <h4 className="text-base font-bold text-white">CAPA Formulation Agent</h4>
              <p className="mt-2 text-xs text-slate-400 leading-relaxed">
                Structured 8D action formulation: immediate physical containment, process correction, and preventive mistake-proofing.
              </p>
            </div>
          </div>
        </div>
      </section>

      <section id="roles" className="py-20 bg-white border-b border-slate-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center max-w-3xl mx-auto">
            <h2 className="text-xs font-bold text-blue-600 uppercase tracking-widest">Role-Based Workspaces</h2>
            <p className="mt-2 text-3xl sm:text-4xl font-extrabold text-slate-900 tracking-tight">
              Dedicated Views for Quality & Production Teams
            </p>
            <p className="mt-4 text-base text-slate-600">
              Each team member has access to the precise tools and permissions required for their manufacturing responsibilities.
            </p>
          </div>

          <div className="mt-14 grid grid-cols-1 md:grid-cols-2 gap-8 max-w-5xl mx-auto">

            <div className="rounded-2xl border-2 border-blue-600/60 bg-blue-50/20 p-8 shadow-sm flex flex-col justify-between">
              <div>
                <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-blue-100 text-blue-800 text-xs font-bold uppercase tracking-wider mb-4">
                  <Award className="w-3.5 h-3.5" /> Quality Engineering
                </div>
                <h3 className="text-2xl font-extrabold text-slate-900">Quality Engineer Workspace</h3>
                <p className="mt-2 text-sm text-slate-600 leading-relaxed">
                  Engineered for root cause analysis, statistical compliance, and final quality disposition sign-off.
                </p>

                <ul className="mt-6 space-y-2.5 text-sm text-slate-700">
                  <li className="flex items-center gap-2">
                    <CheckCircle className="w-4 h-4 text-blue-600 shrink-0" />
                    Configure products, machine cells, specifications, and tolerances
                  </li>
                  <li className="flex items-center gap-2">
                    <CheckCircle className="w-4 h-4 text-blue-600 shrink-0" />
                    Analyze real I-MR control charts, Nelson rules, and Cp/Cpk metrics
                  </li>
                  <li className="flex items-center gap-2">
                    <CheckCircle className="w-4 h-4 text-blue-600 shrink-0" />
                    Investigate 6M root causes with sensor telemetry correlation
                  </li>
                  <li className="flex items-center gap-2">
                    <CheckCircle className="w-4 h-4 text-blue-600 shrink-0" />
                    Approve or reject CAPA plans and verify statistical effectiveness
                  </li>
                  <li className="flex items-center gap-2">
                    <CheckCircle className="w-4 h-4 text-blue-600 shrink-0" />
                    Exclusive authorization: Human-in-the-Loop final batch disposition
                  </li>
                </ul>
              </div>

              <div className="mt-8 pt-6 border-t border-blue-200">
                <button
                  onClick={() => onNavigateToLogin("quality_engineer")}
                  className="w-full py-3 px-4 rounded-xl bg-blue-600 hover:bg-blue-700 text-white font-semibold text-sm shadow-xs transition-all flex items-center justify-center gap-2 cursor-pointer"
                >
                  Access Quality Engineer Workspace <ArrowRight className="w-4 h-4" />
                </button>
              </div>
            </div>

            <div className="rounded-2xl border-2 border-slate-300 bg-slate-50/50 p-8 shadow-sm flex flex-col justify-between">
              <div>
                <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-slate-200 text-slate-800 text-xs font-bold uppercase tracking-wider mb-4">
                  <Cpu className="w-3.5 h-3.5" /> Shop Floor Operations
                </div>
                <h3 className="text-2xl font-extrabold text-slate-900">Production Team Workspace</h3>
                <p className="mt-2 text-sm text-slate-600 leading-relaxed">
                  Action-oriented dashboard for machine operators, cell leads, and line supervisors.
                </p>

                <ul className="mt-6 space-y-2.5 text-sm text-slate-700">
                  <li className="flex items-center gap-2">
                    <CheckCircle className="w-4 h-4 text-slate-600 shrink-0" />
                    Register new production batches and associate machine/shift records
                  </li>
                  <li className="flex items-center gap-2">
                    <CheckCircle className="w-4 h-4 text-slate-600 shrink-0" />
                    Upload CMM dimensional measurement files (CSV, Excel) with instant validation
                  </li>
                  <li className="flex items-center gap-2">
                    <CheckCircle className="w-4 h-4 text-slate-600 shrink-0" />
                    Ingest high-frequency CNC machine telemetry and sensor data
                  </li>
                  <li className="flex items-center gap-2">
                    <CheckCircle className="w-4 h-4 text-slate-600 shrink-0" />
                    Submit component surface photos for rapid visual inspection
                  </li>
                  <li className="flex items-center gap-2">
                    <CheckCircle className="w-4 h-4 text-slate-600 shrink-0" />
                    Track batch processing progress and complete assigned containment tasks
                  </li>
                </ul>
              </div>

              <div className="mt-8 pt-6 border-t border-slate-200">
                <button
                  onClick={() => onNavigateToLogin("operator")}
                  className="w-full py-3 px-4 rounded-xl bg-slate-800 hover:bg-slate-900 text-white font-semibold text-sm shadow-xs transition-all flex items-center justify-center gap-2 cursor-pointer"
                >
                  Access Production Team Workspace <ArrowRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section id="governance" className="py-20 bg-slate-900 text-white border-b border-slate-800">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center max-w-3xl mx-auto">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-slate-800 border border-slate-700 text-blue-400 text-xs font-bold uppercase tracking-wider mb-4">
              <Lock className="w-3.5 h-3.5" /> Trust, Ethics & Governance
            </div>
            <h2 className="text-3xl sm:text-4xl font-extrabold text-white tracking-tight">
              Decision Support, Not Autonomous Authorization
            </h2>
            <p className="mt-4 text-base text-slate-300">
              QualiForge is engineered strictly as an engineering decision-support platform. In compliance with
              ISO 9001 and IATF 16949 Section 8.5.2, certified personnel retain sole authority over final product disposition.
            </p>
          </div>

          <div className="mt-14 max-w-4xl mx-auto grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="p-5 rounded-xl bg-slate-800/90 border border-slate-700/80">
              <span className="px-2.5 py-1 rounded text-xs font-mono font-bold bg-emerald-950 text-emerald-300 border border-emerald-700">
                [OBSERVED FACT]
              </span>
              <h4 className="mt-3 text-base font-bold text-white">Direct Sensor & Measurement Data</h4>
              <p className="mt-1 text-xs text-slate-400">
                Verified readings from calibrated physical sensors, CMM calipers, and direct dial indicators. 100% empirical evidence.
              </p>
            </div>

            <div className="p-5 rounded-xl bg-slate-800/90 border border-slate-700/80">
              <span className="px-2.5 py-1 rounded text-xs font-mono font-bold bg-blue-950 text-blue-300 border border-blue-700">
                [MODEL PREDICTION]
              </span>
              <h4 className="mt-3 text-base font-bold text-white">Computer Vision & ML Inferences</h4>
              <p className="mt-1 text-xs text-slate-400">
                Probabilistic inferences with exposed model versions, confidence percentages, and bounding boxes. Always subject to review.
              </p>
            </div>

            <div className="p-5 rounded-xl bg-slate-800/90 border border-slate-700/80">
              <span className="px-2.5 py-1 rounded text-xs font-mono font-bold bg-purple-950 text-purple-300 border border-purple-700">
                [STATISTICAL FINDING]
              </span>
              <h4 className="mt-3 text-base font-bold text-white">SPC Control Limits & Trends</h4>
              <p className="mt-1 text-xs text-slate-400">
                3-sigma statistical control limits, Nelson rule trips, and capability indices calculated deterministically from verified sample subgroups.
              </p>
            </div>

            <div className="p-5 rounded-xl bg-slate-800/90 border border-slate-700/80">
              <span className="px-2.5 py-1 rounded text-xs font-mono font-bold bg-amber-950 text-amber-300 border border-amber-700">
                [HYPOTHESIS]
              </span>
              <h4 className="mt-3 text-base font-bold text-white">6M Causal Candidate Theories</h4>
              <p className="mt-1 text-xs text-slate-400">
                Causal theories synthesized from shop telemetry and historical similarity. Clearly labeled as requiring physical verification before acceptance.
              </p>
            </div>

            <div className="md:col-span-2 p-5 rounded-xl bg-blue-950/40 border border-blue-700/60">
              <span className="px-2.5 py-1 rounded text-xs font-mono font-bold bg-blue-600 text-white">
                [CONFIRMED ROOT CAUSE]
              </span>
              <h4 className="mt-3 text-base font-bold text-white">Human Engineering Authorization</h4>
              <p className="mt-1 text-xs text-blue-200">
                Only authenticated Quality Engineers can elevate a candidate hypothesis to Confirmed Root Cause and approve batch release.
                Automated agents are strictly prohibited from releasing parts or adjusting machinery.
              </p>
            </div>
          </div>
        </div>
      </section>

      <footer className="bg-slate-950 text-slate-400 py-14 border-t border-slate-800 text-xs">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-6">

          <div className="flex items-center gap-4">
            <img
              src="/logo.png"
              alt="QualiForge Logo"
              className="h-12 sm:h-14 w-auto object-contain drop-shadow-[0_0_16px_rgba(59,130,246,0.35)]"
            />
            <div>
              <div className="text-sm font-bold text-white tracking-tight">AI Quality Intelligence</div>
              <div className="text-slate-400">From Production Data to Explainable Quality Decisions</div>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-6 text-slate-400">
            <a href="#capabilities" className="hover:text-white transition-colors">Capabilities</a>
            <a href="#workflow" className="hover:text-white transition-colors">How It Works</a>
            <a href="#governance" className="hover:text-white transition-colors">Governance</a>
            <button onClick={() => onNavigateToLogin()} className="hover:text-white transition-colors cursor-pointer">Sign In</button>
          </div>

          <div className="text-slate-500">
            &copy; 2026 QualiForge Inc. All rights reserved.
          </div>
        </div>
      </footer>
    </div>
  );
};

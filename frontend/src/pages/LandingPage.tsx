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

  useEffect(() => {
    if (prefersReducedMotion) return;

    let sampleCounter = 111;
    const interval = setInterval(() => {

      const microDelta = (Math.sin(sampleCounter * 0.75) * 0.014) + ((Math.random() - 0.5) * 0.008);
      const nextDiameter = parseFloat((50.000 + microDelta).toFixed(3));
      const nextVib = parseFloat((2.10 + (Math.sin(sampleCounter * 0.4) * 0.18) + ((Math.random() - 0.5) * 0.08)).toFixed(2));
      const sLabel = String(sampleCounter);

      setTelemetryData((prev) => {
        const nextList = [...prev.slice(1), { sample: sLabel, diameter: nextDiameter, vibration: nextVib }];
        return nextList;
      });

      setLiveDiameter(nextDiameter);
      setLiveVibration(nextVib);
      setLiveSampleCount((c) => c + 1);
      sampleCounter += 1;
    }, 1800);

    return () => clearInterval(interval);
  }, [prefersReducedMotion]);

  const [activeStage, setActiveStage] = useState(0);
  const [isFlowPlaying, setIsFlowPlaying] = useState(true);

  const workflowStages = [
    {
      stage: "01",
      name: "Production Data",
      category: "SHOP FLOOR INGESTION",
      agent: "Agent 1: Metadata Registrar",
      desc: "Batch specifications, material lots, machine registration, and operator shift parameters.",
      input: "Material Heat Certs, Machine ID, Shift Roster",
      output: "Registered Batch Dossier & Specification Baseline",
      preview: { label: "Batch Context", value: "Lot Dossier • Machine ID • Material Heat Certificate" }
    },
    {
      stage: "02",
      name: "Data Intake",
      category: "AUTOMATED NORMALIZATION",
      agent: "Agent 2: Intake Validation Service",
      desc: "Automated ingestion, unit normalization (microns/inches to mm), and schema validation.",
      input: "Raw CMM Caliper CSV & Telemetry Streams",
      output: "100% Normalized Dimensional Float Array",
      preview: { label: "Normalization", value: "50000 µm → 50.000 mm • Schema Verified 100%" }
    },
    {
      stage: "03",
      name: "Visual, Dimensional & Process Analysis",
      category: "AI MULTI-MODAL INFERENCE",
      agent: "Agent 3: YOLOv8 Computer Vision & Telemetry Engine",
      desc: "Parallel evaluation: YOLOv8 defect detection, boundary-safe tolerance verification, and telemetry anomaly detection.",
      input: "High-res Camera Frames + Vibration Spectrograms",
      output: "Defect Bounding Boxes + Deviation Deltas",
      preview: { label: "Vision Inference", value: "Surface Scratch (94.0% Conf) • [50, 120, 210, 180]" }
    },
    {
      stage: "04",
      name: "Statistical Process Control",
      category: "SPC MATHEMATICS",
      agent: "Agent 4: Deterministic Capability Engine",
      desc: "I-MR control charting, Nelson rule trips, and sample-verified Cp/Cpk capability evaluation.",
      input: "Subgroup Measurements Array (k=5)",
      output: "UCL, LCL, Centerline, Cp (1.42), Cpk (1.38)",
      preview: { label: "Capability Indices", value: "Cp = 1.42 • Cpk = 1.38 • Nelson Rule 1-8: PASS" }
    },
    {
      stage: "05",
      name: "Incident Detection Gate",
      category: "AUTONOMOUS CONTAINMENT",
      agent: "Agent 5: Non-conformance Gatekeeper",
      desc: "Automated non-conformance detection triggers quality hold if specifications or control limits are breached.",
      input: "Tolerance & Rule Violations Delta",
      output: "NCR Incident Record & Quarantine Trigger",
      preview: { label: "NCR Generation", value: "NCR-2026-088 Triggered • Cell Quarantine Activated" }
    },
    {
      stage: "06",
      name: "Root Cause Analysis",
      category: "CAUSAL SYNTHESIS",
      agent: "Agent 6: 6M Ishikawa & 5-Whys Synthesizer",
      desc: "6M Ishikawa failure mode analysis and 5-Whys causal chains synthesized with physical sensor evidence.",
      input: "Machine Spindle Telemetry + Tool Cycle Counts",
      output: "Ranked Causal Hypotheses with Physical Proof",
      preview: { label: "Causal Chains", value: "Tool Flank Wear (88% Prob) & Spindle Harmonics (62%)" }
    },
    {
      stage: "07",
      name: "Historical Evidence Retrieval",
      category: "VECTOR MEMORY RETRIEVAL",
      agent: "Agent 7: Knowledge Base Retriever",
      desc: "In-process vector search retrieves matched non-conformance reports (NCRs) and approved standard operating procedures.",
      input: "Embedding of Incident Anomaly Signatures",
      output: "Matched Historical Incidents (NCR-019 Cosine 0.91)",
      preview: { label: "Vector Search", value: "NCR-019 (Cosine Similarity 0.912) • SOP-84 Matched" }
    },
    {
      stage: "08",
      name: "CAPA Recommendations",
      category: "ACTION FORMULATION",
      agent: "Agent 8: 3-Tier CAPA Generator",
      desc: "Formulation of 3-tier containment, corrective action, and preventive action proposals.",
      input: "Synthesized Causal Chain + Past Proven Remedies",
      output: "3-Tier Action Plan: Containment / Correction / Prevention",
      preview: { label: "Action Plan", value: "Hold 500 pcs • Replace Tool Insert • 850-Cycle Lockout" }
    },
    {
      stage: "09",
      name: "Human Engineering Approval",
      category: "HITL GOVERNANCE GATE",
      agent: "Quality Engineer: Authorized Person Disposition",
      desc: "HITL Gate: Quality Engineer reviews hypotheses, verifies sensor evidence, and signs off final disposition.",
      input: "Full Agentic Evidence Dossier",
      output: "Cryptographic E-Signature & Release Disposition",
      preview: { label: "HITL Sign-Off", value: "Signed: Lead Quality Engineer • Status: Disposition Final" }
    },
    {
      stage: "10",
      name: "Effectiveness Monitoring",
      category: "STATISTICAL VERIFICATION",
      agent: "Agent 9: Two-Proportion Z-Test Engine",
      desc: "Two-proportion z-test statistical verification compares pre- and post-CAPA defect rates.",
      input: "Pre-CAPA vs Post-CAPA Defect Proportions",
      output: "Z-Score, p-value (<0.05), Rejection Rate Drop (8.2% → 1.1%)",
      preview: { label: "Z-Test Result", value: "Defect Drop: 8.2% → 1.1% (p = 0.0004 < 0.05 PASS)" }
    },
    {
      stage: "11",
      name: "Quality Audit Report",
      category: "COMPLIANCE DOSSIER",
      agent: "Agent 10: IATF / ISO ReportLab Compiler",
      desc: "Compilation of official 13-section ISO 9001 / IATF 16949 audit dossier PDF.",
      input: "All 11 Upstream Agent Immutable Checkpoints",
      output: "Official PDF Audit Dossier with Running Headers & Disclaimers",
      preview: { label: "Audit Dossier", value: "IATF 16949 / ISO 9001 Audit Dossier • 13 Standard Sections Ready" }
    },
  ];

  useEffect(() => {
    if (!isFlowPlaying) return;
    const interval = setInterval(() => {
      setActiveStage((prev) => (prev + 1) % workflowStages.length);
    }, 3200);
    return () => clearInterval(interval);
  }, [isFlowPlaying, workflowStages.length]);

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

          <div className="flex flex-col md:flex-row md:items-end justify-between gap-6 pb-10 border-b border-slate-800">
            <div>
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-blue-950 text-blue-400 border border-blue-800 text-xs font-mono uppercase tracking-widest mb-3">
                <Zap className="w-3.5 h-3.5 text-blue-400" /> Workflow Architecture
              </div>
              <h2 className="text-3xl sm:text-4xl font-extrabold text-white tracking-tight">
                11-Stage Multi-Agent Quality Pipeline
              </h2>
              <p className="mt-3 text-base text-slate-300 max-w-2xl">
                How production data flows deterministically from factory floor ingestion to human sign-off.
              </p>
            </div>

            <div className="flex items-center gap-3">
              <button
                onClick={() => setIsFlowPlaying(!isFlowPlaying)}
                className={`px-4 py-2 rounded-lg text-xs font-semibold flex items-center gap-2 border transition-all cursor-pointer ${
                  isFlowPlaying
                    ? "bg-blue-600/90 text-white border-blue-500 shadow-sm"
                    : "bg-slate-800 text-slate-300 border-slate-700 hover:text-white"
                }`}
              >
                {isFlowPlaying ? (
                  <>
                    <Pause className="w-3.5 h-3.5" />
                    <span>Auto-Playing Flow</span>
                  </>
                ) : (
                  <>
                    <Play className="w-3.5 h-3.5" />
                    <span>Resume Auto-Flow</span>
                  </>
                )}
              </button>
            </div>
          </div>

          <div className="mt-8 pb-6 overflow-x-auto scrollbar-none">
            <div className="flex items-center justify-between min-w-[850px] relative px-2">

              <div className="absolute top-1/2 left-4 right-4 -translate-y-1/2 h-1 bg-slate-800 z-0">
                <div
                  className="h-full bg-gradient-to-r from-blue-600 to-indigo-500 transition-all duration-700"
                  style={{ width: `${(activeStage / (workflowStages.length - 1)) * 100}%` }}
                />
              </div>

              {workflowStages.map((s, idx) => {
                const isActive = activeStage === idx;
                const isPassed = activeStage > idx;
                return (
                  <button
                    key={idx}
                    onClick={() => {
                      setActiveStage(idx);
                      setIsFlowPlaying(false);
                    }}
                    className="relative z-10 flex flex-col items-center group cursor-pointer focus:outline-none"
                    title={`Inspect Stage ${s.stage}: ${s.name}`}
                  >
                    <div
                      className={`w-9 h-9 rounded-xl font-mono text-xs font-bold flex items-center justify-center transition-all duration-300 ${
                        isActive
                          ? "bg-blue-600 text-white ring-4 ring-blue-400/30 scale-110 shadow-lg"
                          : isPassed
                          ? "bg-indigo-900 text-indigo-200 border border-indigo-700"
                          : "bg-slate-800 text-slate-400 border border-slate-700 group-hover:bg-slate-700 group-hover:text-white"
                      }`}
                    >
                      {isPassed ? "✓" : s.stage}
                    </div>
                    <span
                      className={`mt-2 text-[10px] font-medium tracking-tight whitespace-nowrap transition-colors ${
                        isActive ? "text-blue-400 font-bold" : "text-slate-400 group-hover:text-slate-200"
                      }`}
                    >
                      {s.name.split(" ")[0]}
                    </span>
                  </button>
                );
              })}
            </div>
          </div>

          {(() => {
            const current = workflowStages[activeStage];
            return (
              <div className="mt-6 p-6 sm:p-8 rounded-2xl bg-gradient-to-br from-slate-850 via-slate-800 to-slate-900 border-2 border-blue-500/80 shadow-2xl transition-all">
                <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-6 pb-6 border-b border-slate-700/80">
                  <div>
                    <div className="flex flex-wrap items-center gap-2.5">
                      <span className="w-8 h-8 rounded-lg bg-blue-600 text-white font-mono font-bold text-sm flex items-center justify-center">
                        {current.stage}
                      </span>
                      <span className="px-2.5 py-1 rounded-md text-[11px] font-mono font-bold bg-blue-950 text-blue-300 border border-blue-700">
                        {current.category}
                      </span>
                      <span className="text-xs text-slate-400 font-medium">
                        &bull; {current.agent}
                      </span>
                    </div>
                    <h3 className="mt-3 text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
                      {current.name}
                    </h3>
                    <p className="mt-2 text-sm sm:text-base text-slate-300 max-w-3xl leading-relaxed">
                      {current.desc}
                    </p>
                  </div>

                  <div className="w-full lg:w-auto p-4 rounded-xl bg-slate-900/90 border border-slate-700 shrink-0 min-w-[280px]">
                    <div className="text-[11px] font-mono text-slate-400 uppercase tracking-wider">
                      {current.preview.label}
                    </div>
                    <div className="mt-1 text-xs font-mono font-bold text-emerald-400">
                      {current.preview.value}
                    </div>
                  </div>
                </div>

                <div className="mt-6 grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800">
                    <div className="text-[11px] font-mono text-slate-400 uppercase tracking-wider">Stage Inflow</div>
                    <div className="mt-1.5 text-xs text-slate-200 font-medium">{current.input}</div>
                  </div>
                  <div className="p-4 rounded-xl bg-blue-950/40 border border-blue-800/60">
                    <div className="text-[11px] font-mono text-blue-400 uppercase tracking-wider">Processing Engine</div>
                    <div className="mt-1.5 text-xs text-blue-200 font-medium">{current.agent}</div>
                  </div>
                  <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800">
                    <div className="text-[11px] font-mono text-emerald-400 uppercase tracking-wider">Deterministic Output</div>
                    <div className="mt-1.5 text-xs text-emerald-200 font-medium">{current.output}</div>
                  </div>
                </div>
              </div>
            );
          })()}

          <div className="mt-12 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {workflowStages.map((s, idx) => {
              const isActive = activeStage === idx;
              return (
                <div
                  key={idx}
                  onClick={() => {
                    setActiveStage(idx);
                    setIsFlowPlaying(false);
                  }}
                  className={`p-5 rounded-xl border transition-all cursor-pointer ${
                    isActive
                      ? "bg-slate-800/90 border-blue-500 ring-2 ring-blue-500/30 shadow-lg"
                      : "bg-slate-900/60 border-slate-800 hover:border-slate-700 hover:bg-slate-850"
                  }`}
                >
                  <div className="flex items-center justify-between mb-3">
                    <span
                      className={`w-7 h-7 rounded-md font-mono text-xs font-bold flex items-center justify-center ${
                        isActive ? "bg-blue-600 text-white" : "bg-slate-800 text-slate-400 border border-slate-700"
                      }`}
                    >
                      {s.stage}
                    </span>
                    {isActive && (
                      <span className="inline-flex items-center gap-1 text-[10px] font-mono font-bold text-blue-400 px-2 py-0.5 rounded bg-blue-950 border border-blue-800">
                        <span className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-ping" />
                        ACTIVE
                      </span>
                    )}
                  </div>
                  <h4 className={`text-base font-bold tracking-tight ${isActive ? "text-white" : "text-slate-200"}`}>
                    {s.name}
                  </h4>
                  <p className="mt-2 text-xs text-slate-400 leading-relaxed line-clamp-3">
                    {s.desc}
                  </p>
                </div>
              );
            })}
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

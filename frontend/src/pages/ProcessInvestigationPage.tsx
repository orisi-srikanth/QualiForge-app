import React, { useState, useEffect } from "react";
import { api } from "../api";
import { ProcessInvestigationReport } from "../types";
import { CertaintyBadge } from "../components/CertaintyBadge";
import {
  GitFork, ShieldAlert, AlertTriangle, CheckCircle2, RefreshCw,
  Clock, ArrowRight, Layers, Cpu, Ruler, Eye, Activity, FileText,
  Search, ExternalLink, ChevronRight, Check, X, HelpCircle,
  TrendingUp, ShieldCheck
} from "lucide-react";

interface Props {
  initialBatchId?: string;
  onNavigate: (page: string, params?: any) => void;
  onSelectBatch?: (batchId: string) => void;
}

export const ProcessInvestigationPage: React.FC<Props> = ({
  initialBatchId = "BATCH-0245",
  onNavigate,
  onSelectBatch
}) => {
  const [batches, setBatches] = useState<any[]>([]);
  const [selectedBatchId, setSelectedBatchId] = useState<string>(initialBatchId);
  const [report, setReport] = useState<ProcessInvestigationReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    api.getBatches().then((bList) => {
      if (Array.isArray(bList) && bList.length > 0) {
        setBatches(bList);

        if (!selectedBatchId) {
          const firstId = bList[0].batch_number || bList[0].batch_id || "";
          setSelectedBatchId(firstId);
        }
      }
    }).catch(() => {});
  }, []);

  const fetchInvestigation = async (bId: string, force: boolean = false) => {
    if (!bId) return;
    setLoading(true);
    setError(null);
    try {
      if (force) {
        setRefreshing(true);
        const data = await api.runProcessInvestigation(bId, true);
        setReport(data);
      } else {
        const data = await api.getProcessInvestigation(bId);
        setReport(data);
      }
    } catch (err: any) {
      setError(err?.message || `Failed to load process investigation for batch ${bId}`);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    if (selectedBatchId) {
      fetchInvestigation(selectedBatchId);
      if (onSelectBatch) {
        onSelectBatch(selectedBatchId);
      }
    }
  }, [selectedBatchId]);

  const handleBatchSelect = (bId: string) => {
    setSelectedBatchId(bId);

    const url = new URL(window.location.href);
    url.searchParams.set("batch_id", bId);
    window.history.pushState(null, "", url.pathname + url.search);
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto font-sans antialiased text-slate-800">

      <div className="p-6 bg-gradient-to-r from-slate-900 via-indigo-950 to-slate-900 text-white rounded-2xl shadow-md border border-slate-800 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="px-2.5 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-blue-500/20 text-blue-300 border border-blue-500/40">
              Quality Engineering Intelligence
            </span>
            <span className="px-2.5 py-0.5 rounded text-[10px] font-mono font-bold bg-slate-800 text-slate-300 border border-slate-700">
              IATF 16949 / ISO 9001
            </span>
          </div>
          <h1 className="text-xl sm:text-2xl font-black text-white mt-2 tracking-tight flex items-center gap-2.5">
            <GitFork className="w-6 h-6 text-blue-400" />
            Manufacturing Process Investigation
          </h1>
          <p className="text-xs text-slate-300 mt-1 max-w-3xl leading-relaxed">
            Multi-factor defect-specific investigation correlating coordinate measurement inspection (CMM),
            high-frequency CNC telemetry, tool wear cycles, and operator setup records into evidence-ranked root causes.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3 shrink-0">
          <div className="relative">
            <select
              value={selectedBatchId}
              onChange={(e) => handleBatchSelect(e.target.value)}
              className="pl-3 pr-8 py-2 bg-slate-800 border border-slate-700 text-white rounded-xl text-xs font-mono font-bold focus:outline-none focus:ring-2 focus:ring-blue-500 cursor-pointer"
            >
              {batches.map((b) => {
                const bNum = b.batch_number || b.batch_id || b.id;
                return (
                  <option key={bNum} value={bNum}>
                    {bNum} ({b.part_number || b.product_id || "Part"})
                  </option>
                );
              })}
            </select>
          </div>

          <button
            onClick={() => fetchInvestigation(selectedBatchId, true)}
            disabled={refreshing}
            className="px-3.5 py-2 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white rounded-xl text-xs font-bold transition-all shadow-xs flex items-center gap-1.5 cursor-pointer"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${refreshing ? "animate-spin" : ""}`} />
            <span>Re-evaluate</span>
          </button>

          <button
            onClick={() => onNavigate("production-dashboard")}
            className="px-3 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-xl text-xs font-semibold border border-slate-700 transition-colors cursor-pointer"
          >
            &larr; PT Dashboard
          </button>
        </div>
      </div>

      {loading ? (
        <div className="p-16 text-center text-xs text-slate-500 bg-white rounded-2xl border border-slate-200 shadow-xs space-y-3">
          <RefreshCw className="w-8 h-8 animate-spin text-blue-600 mx-auto" />
          <div className="text-sm font-bold text-slate-800">Compiling Process Investigation...</div>
          <p className="text-slate-500 max-w-md mx-auto">
            Retrieving dimensional measurements, machine telemetry, tool wear history, and vector historical incident records.
          </p>
        </div>
      ) : error ? (
        <div className="p-8 bg-rose-50 border border-rose-200 rounded-2xl text-center space-y-3">
          <AlertTriangle className="w-8 h-8 text-rose-600 mx-auto" />
          <div className="text-sm font-bold text-rose-900">Investigation Error</div>
          <p className="text-xs text-rose-700 max-w-lg mx-auto">{error}</p>
          <button
            onClick={() => fetchInvestigation(selectedBatchId, true)}
            className="px-4 py-2 bg-rose-600 text-white rounded-lg text-xs font-semibold cursor-pointer"
          >
            Retry Investigation
          </button>
        </div>
      ) : !report ? (
        <div className="p-12 text-center text-xs text-slate-500 bg-white rounded-2xl border border-slate-200">
          No investigation data returned for this batch.
        </div>
      ) : (
        <>

          {report.investigation_status === "INSUFFICIENT_PROCESS_EVIDENCE" && (
            <div className="p-5 bg-amber-50 border-2 border-amber-300 rounded-2xl shadow-xs space-y-3">
              <div className="flex items-center gap-2.5 text-amber-900">
                <ShieldAlert className="w-5 h-5 text-amber-600 shrink-0" />
                <h3 className="text-sm font-extrabold uppercase tracking-wide">
                  Process Investigation Notice: INSUFFICIENT_PROCESS_EVIDENCE
                </h3>
              </div>
              <p className="text-xs text-amber-800 leading-relaxed">
                Nonconformance was detected in physical measurements or visual inspection, but required high-frequency machine telemetry,
                sensor logs, or tool maintenance records are currently missing from the system for batch <span className="font-mono font-bold">{report.batch_id}</span>.
                In compliance with quality governance, root causes cannot be fabricated without verifiable process evidence.
              </p>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2">
                <div className="p-3 bg-white/80 rounded-xl border border-amber-200 text-xs">
                  <div className="font-bold text-amber-900 mb-1.5 flex items-center gap-1.5">
                    <AlertTriangle className="w-3.5 h-3.5 text-amber-600" />
                    <span>Missing Data Sources:</span>
                  </div>
                  <ul className="list-disc list-inside space-y-1 text-slate-700 text-[11px]">
                    {report.missing_data_sources.map((s, idx) => (
                      <li key={idx}>{s}</li>
                    ))}
                  </ul>
                </div>
                <div className="p-3 bg-white/80 rounded-xl border border-amber-200 text-xs">
                  <div className="font-bold text-amber-900 mb-1.5 flex items-center gap-1.5">
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                    <span>Required Verification Steps:</span>
                  </div>
                  <ul className="list-disc list-inside space-y-1 text-slate-700 text-[11px]">
                    {report.verification_steps.map((v, idx) => (
                      <li key={idx}>{v}</li>
                    ))}
                  </ul>
                </div>
              </div>
            </div>
          )}

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">

            <div className="p-4 bg-white border border-slate-200 rounded-xl shadow-2xs">
              <div className="text-[11px] font-bold uppercase tracking-wider text-slate-400">Production Batch</div>
              <div className="mt-1 font-mono font-extrabold text-base text-slate-900">{report.batch_id}</div>
              <div className="text-xs text-slate-600 mt-1 font-medium">
                {report.product.part_number} &bull; {report.product.name}
              </div>
              <div className="mt-2 text-[10px] text-slate-500 font-mono">
                Material: {report.product.material}
              </div>
            </div>

            <div className="p-4 bg-white border border-slate-200 rounded-xl shadow-2xs">
              <div className="text-[11px] font-bold uppercase tracking-wider text-slate-400">Machine Cell</div>
              <div className="mt-1 font-mono font-extrabold text-base text-slate-900">{report.machine.code}</div>
              <div className="text-xs text-slate-600 mt-1 font-medium">
                {report.machine.type} &bull; Shift: <span className="font-semibold text-slate-800">{report.shift}</span>
              </div>
              <div className="mt-2 text-[10px] text-slate-500 font-mono">
                Location: {report.machine.location}
              </div>
            </div>

            <div className="p-4 bg-white border border-slate-200 rounded-xl shadow-2xs">
              <div className="text-[11px] font-bold uppercase tracking-wider text-slate-400">Specification Limits</div>
              <div className="mt-1 font-mono font-extrabold text-base text-slate-900">
                {report.specification.nominal.toFixed(3)} {report.specification.unit}
              </div>
              <div className="text-xs text-slate-600 mt-1 font-mono flex items-center gap-2">
                <span className="text-rose-600 font-semibold">LSL: {report.specification.lsl.toFixed(3)}</span>
                <span>&bull;</span>
                <span className="text-rose-600 font-semibold">USL: {report.specification.usl.toFixed(3)}</span>
              </div>
              <div className="mt-2 text-[10px] text-slate-500">
                Param: <span className="font-semibold">{report.specification.characteristic}</span>
              </div>
            </div>

            <div className="p-4 bg-white border border-slate-200 rounded-xl shadow-2xs">
              <div className="text-[11px] font-bold uppercase tracking-wider text-slate-400">Inspection Status</div>
              <div className="mt-1 flex items-center gap-2">
                <span className={`px-2.5 py-0.5 rounded text-xs font-bold uppercase ${
                  report.inspection_summary.conformance_verdict === "CONFORMING"
                    ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
                    : "bg-rose-50 text-rose-700 border border-rose-200"
                }`}>
                  {report.inspection_summary.conformance_verdict}
                </span>
                <span className="text-xs font-mono font-bold text-slate-700">
                  {report.batch_status}
                </span>
              </div>
              <div className="text-xs text-slate-600 mt-2 font-medium">
                Nonconforming: <span className="font-bold text-rose-600">{report.inspection_summary.nonconforming_count}</span> / {report.inspection_summary.total_inspected} parts
              </div>
              <div className="text-[10px] text-slate-500 font-mono mt-0.5">
                Rejection Rate: {report.inspection_summary.rejection_rate_percent}%
              </div>
            </div>
          </div>

          <div className="p-5 bg-white border border-slate-200 rounded-2xl shadow-xs space-y-2">
            <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 pb-3">
              <div>
                <span className="text-[10px] font-bold font-mono uppercase tracking-wider px-2 py-0.5 bg-blue-50 text-blue-700 border border-blue-200 rounded">
                  Investigation Strategy
                </span>
                <h3 className="text-base font-extrabold text-slate-900 mt-1">
                  {report.strategy.title}
                </h3>
              </div>
              <div className="text-right">
                <span className="text-[11px] font-mono font-bold text-slate-500">
                  {report.investigation_timestamp}
                </span>
              </div>
            </div>
            <p className="text-xs text-slate-600 leading-relaxed">
              {report.strategy.description}
            </p>
          </div>

          {report.nonconforming_samples.length > 0 && (
            <div className="p-5 bg-white border border-slate-200 rounded-2xl shadow-xs space-y-3">
              <div className="flex items-center justify-between border-b border-slate-100 pb-3">
                <div className="flex items-center gap-2">
                  <Ruler className="w-4 h-4 text-rose-600" />
                  <h3 className="text-sm font-bold text-slate-900">
                    Failed Characteristics & Out-of-Specification Measurements
                  </h3>
                </div>
                <span className="text-xs font-mono text-rose-600 font-semibold">
                  {report.nonconforming_samples.length} Out-of-Tolerance Part(s)
                </span>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-50 text-slate-600 font-semibold border-b border-slate-200">
                    <tr>
                      <th className="py-2.5 px-3">Sample Identifier</th>
                      <th className="py-2.5 px-3">Measured Value</th>
                      <th className="py-2.5 px-3">Specification Limits</th>
                      <th className="py-2.5 px-3">Deviation from Limit</th>
                      <th className="py-2.5 px-3">Intake Timestamp</th>
                      <th className="py-2.5 px-3">Measurement Source</th>
                      <th className="py-2.5 px-3">Classification</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {report.nonconforming_samples.map((s, idx) => (
                      <tr key={idx} className="hover:bg-rose-50/40">
                        <td className="py-2.5 px-3 font-mono font-bold text-slate-900">{s.sample_id}</td>
                        <td className="py-2.5 px-3 font-mono font-bold text-rose-600">
                          {s.measured_value.toFixed(4)} {s.unit}
                        </td>
                        <td className="py-2.5 px-3 font-mono text-slate-600">
                          [{report.specification.lsl.toFixed(3)}, {report.specification.usl.toFixed(3)}] {report.specification.unit}
                        </td>
                        <td className="py-2.5 px-3 font-mono font-semibold text-rose-600">
                          +{s.deviation_from_limit.toFixed(4)} {s.unit}
                        </td>
                        <td className="py-2.5 px-3 font-mono text-slate-500">{s.measured_at || "Shift Sample"}</td>
                        <td className="py-2.5 px-3 capitalize text-slate-600">{s.source || "Gauge"}</td>
                        <td className="py-2.5 px-3">
                          <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-rose-50 text-rose-700 border border-rose-200">
                            NONCONFORMING
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-base font-extrabold text-slate-900 flex items-center gap-2">
                  <Activity className="w-5 h-5 text-blue-600" />
                  Evidence-Backed Root Cause Hypotheses
                </h3>
                <p className="text-xs text-slate-500 mt-0.5">
                  Synthesized through physical telemetry correlation, tool cycles, and historical NCR vector retrieval.
                </p>
              </div>
              <span className="text-[11px] font-mono text-slate-400">
                Governance: Decision-Support Only
              </span>
            </div>

            <div className="grid grid-cols-1 gap-4">
              {report.hypotheses.map((h, idx) => (
                <div
                  key={h.hypothesis_id || idx}
                  className="p-5 bg-white border border-slate-200 rounded-2xl shadow-xs space-y-3 transition-all hover:border-blue-300"
                >
                  <div className="flex flex-wrap items-start justify-between gap-3 border-b border-slate-100 pb-3">
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-slate-900 text-white">
                          {h.hypothesis_id || `HYP-0${idx + 1}`}
                        </span>
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-blue-50 text-blue-700 border border-blue-200">
                          {h.category}
                        </span>
                        <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                          h.status === "SUPPORTED"
                            ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
                            : h.status === "CONTRADICTED"
                            ? "bg-rose-50 text-rose-700 border border-rose-200"
                            : "bg-amber-50 text-amber-700 border border-amber-200"
                        }`}>
                          {h.status.replace(/_/g, " ")}
                        </span>
                      </div>
                      <h4 className="text-base font-bold text-slate-900">{h.title}</h4>
                      <p className="text-xs text-slate-600 leading-relaxed max-w-4xl">{h.description}</p>
                    </div>

                    <div className="text-right shrink-0">
                      <div className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Evidence Score</div>
                      <div className="font-mono text-lg font-black text-blue-600">
                        {Math.round((h.confidence_score || h.evidence_score || 0) * 100)}%
                      </div>
                    </div>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-1">

                    <div className="p-3.5 bg-emerald-50/50 rounded-xl border border-emerald-200 space-y-2">
                      <div className="text-xs font-bold text-emerald-900 flex items-center gap-1.5">
                        <Check className="w-3.5 h-3.5 text-emerald-600" />
                        <span>Supporting Manufacturing Evidence:</span>
                      </div>
                      {h.supporting_evidence.length > 0 ? (
                        <ul className="list-disc list-inside space-y-1 text-slate-700 text-xs">
                          {h.supporting_evidence.map((ev, i) => (
                            <li key={i}>{ev}</li>
                          ))}
                        </ul>
                      ) : (
                        <div className="text-[11px] text-slate-500 italic">No supporting evidence identified.</div>
                      )}
                    </div>

                    <div className="p-3.5 bg-rose-50/50 rounded-xl border border-rose-200 space-y-2">
                      <div className="text-xs font-bold text-rose-900 flex items-center gap-1.5">
                        <X className="w-3.5 h-3.5 text-rose-600" />
                        <span>Contradicting / Counter Evidence:</span>
                      </div>
                      {h.contradicting_evidence.length > 0 ? (
                        <ul className="list-disc list-inside space-y-1 text-slate-700 text-xs">
                          {h.contradicting_evidence.map((ev, i) => (
                            <li key={i}>{ev}</li>
                          ))}
                        </ul>
                      ) : (
                        <div className="text-[11px] text-slate-500 italic">No contradictory evidence recorded.</div>
                      )}
                    </div>
                  </div>

                  <div className="p-3 bg-slate-50 rounded-xl border border-slate-200 text-xs space-y-1.5">
                    <div className="flex items-center gap-1.5 text-slate-700 font-bold">
                      <HelpCircle className="w-3.5 h-3.5 text-blue-600" />
                      <span>Required Physical Engineering Confirmation:</span>
                    </div>
                    <p className="text-slate-600 text-[11px] leading-relaxed">
                      {h.required_confirmation}
                    </p>
                    {h.missing_evidence && h.missing_evidence.length > 0 && (
                      <div className="text-[11px] text-slate-500 pt-1">
                        <span className="font-semibold text-slate-700">Missing Evidence Check:</span>{" "}
                        {h.missing_evidence.join("; ")}
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

            <div className="p-5 bg-white border border-slate-200 rounded-2xl shadow-xs space-y-3">
              <div className="flex items-center justify-between border-b border-slate-100 pb-3">
                <div className="flex items-center gap-2">
                  <ShieldCheck className="w-4 h-4 text-blue-600" />
                  <h3 className="text-sm font-bold text-slate-900">
                    Recommended Containment & Corrective Actions
                  </h3>
                </div>
                <span className="text-[11px] font-mono text-slate-400">3-Tier Hierarchy</span>
              </div>

              <div className="space-y-2.5">
                {report.recommended_actions.map((act, idx) => (
                  <div
                    key={idx}
                    className="p-3 rounded-xl border border-slate-200 bg-slate-50/70 text-xs space-y-1"
                  >
                    <div className="flex items-center justify-between">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                        act.type === "containment"
                          ? "bg-rose-100 text-rose-800"
                          : act.type === "corrective"
                          ? "bg-blue-100 text-blue-800"
                          : "bg-emerald-100 text-emerald-800"
                      }`}>
                        {act.type}
                      </span>
                      <span className="text-[10px] font-mono text-slate-500 font-semibold">
                        Urgency: {act.urgency}
                      </span>
                    </div>
                    <p className="text-slate-800 font-medium text-xs mt-1 leading-snug">{act.action}</p>
                    <div className="text-[10px] text-slate-500">
                      Responsible: <span className="font-semibold">{act.responsible}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="p-5 bg-white border border-slate-200 rounded-2xl shadow-xs space-y-3">
              <div className="flex items-center justify-between border-b border-slate-100 pb-3">
                <div className="flex items-center gap-2">
                  <FileText className="w-4 h-4 text-emerald-600" />
                  <h3 className="text-sm font-bold text-slate-900">
                    CAPA Workflow Integration
                  </h3>
                </div>
                <button
                  onClick={() => onNavigate("capa")}
                  className="text-xs font-semibold text-blue-600 hover:underline flex items-center gap-1 cursor-pointer"
                >
                  <span>Open CAPA Center</span>
                  <ArrowRight className="w-3 h-3" />
                </button>
              </div>

              {report.capa_actions.length > 0 ? (
                <div className="space-y-2">
                  {report.capa_actions.map((c) => (
                    <div
                      key={c.id}
                      className="p-3 rounded-xl border border-slate-200 hover:border-emerald-300 transition-colors bg-white text-xs space-y-1"
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-mono font-bold text-slate-900">{c.action_code}</span>
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
                          {c.status.toUpperCase()}
                        </span>
                      </div>
                      <p className="text-slate-700 text-xs">{c.description}</p>
                      <div className="flex items-center justify-between text-[10px] text-slate-500 pt-1">
                        <span>Role: {c.responsible_role || "QE Lead"}</span>
                        <span>Due: {c.due_date}</span>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="p-6 text-center text-xs text-slate-500 bg-slate-50 rounded-xl border border-dashed border-slate-200 space-y-2">
                  <div>No formal CAPA action plan committed for this incident yet.</div>
                  <button
                    onClick={() => onNavigate("capa")}
                    className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-xs font-semibold cursor-pointer"
                  >
                    Formulate CAPA in CAPA Center &rarr;
                  </button>
                </div>
              )}

              <div className="p-3 bg-slate-100 rounded-xl text-[11px] text-slate-600 leading-relaxed border border-slate-200">
                <span className="font-bold text-slate-800">Causation Audit Note:</span>{" "}
                {report.correlation_vs_causation_note}
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
};

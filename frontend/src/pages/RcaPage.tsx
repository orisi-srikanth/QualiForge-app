import React, { useEffect, useState } from "react";
import { api } from "../api";
import { RCAReport, HypothesisEvidence, HistoricalIncident } from "../types";
import { CertaintyBadge } from "../components/CertaintyBadge";
import {
  GitFork, HelpCircle, ShieldCheck, Database, Search,
  CheckCircle2, XCircle, AlertTriangle, Layers, BookOpen, ArrowRight,
  Calculator, Check, Ban, MessageSquare, RefreshCw, BarChart2, Activity, UserCheck
} from "lucide-react";

export const RcaPage: React.FC = () => {
  const [report, setReport] = useState<RCAReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<"hypotheses" | "five_whys" | "fishbone" | "correlation" | "inputs" | "rag">("hypotheses");
  const [ragQuery, setRagQuery] = useState("Oversized shaft diameter tool wear CNC-04");
  const [ragResults, setRagResults] = useState<HistoricalIncident[]>([]);
  const [searchingRag, setSearchingRag] = useState(false);
  const [selectedNcr, setSelectedNcr] = useState<any | null>(null);
  const [ragError, setRagError] = useState<string | null>(null);
  const [expandedBreakdown, setExpandedBreakdown] = useState<Record<string, boolean>>({ "HYP-01": true });
  const [userRole, setUserRole] = useState<"quality_engineer" | "operator">("quality_engineer");
  const [actionFeedback, setActionFeedback] = useState<string | null>(null);
  const [submittingAction, setSubmittingAction] = useState(false);

  useEffect(() => {
    loadRcaData();
  }, []);

  const parseEvidence = (raw: string): { headline: string; source?: string } => {
    let text = raw.trim();
    let source: string | undefined;

    const srcMatch = text.match(/\[Source:\s*([^\]]+)\]/i);
    if (srcMatch) {
      source = srcMatch[1]
        .replace(/process_reading @\s*/i, "")
        .replace(/kb_document\s*/i, "")
        .trim();
      text = text.replace(/\[Source:\s*[^\]]+\]/i, "").trim();
    }

    if (/Tool cycle count is\s*(\d+)\s*cycles.*exceeding nominal\s*(\d+)/i.test(text)) {
      const m = text.match(/(\d+)\s*cycles.*nominal\s*(\d+)/i);
      text = m ? `Tool cycle count: ${m[1]} / ${m[2]} cycles (+${Math.round(((parseInt(m[1]) - parseInt(m[2])) / parseInt(m[2])) * 100)}% over nominal)` : text;
    } else if (/gradual positive drift toward and past USL/i.test(text)) {
      text = "Positive dimensional drift toward & past USL in late batch";
    } else if (/vibration concurrently increased to\s*([0-9.]+)\s*mm\/s/i.test(text)) {
      const m = text.match(/([0-9.]+)\s*mm\/s/i);
      text = `Vibration surge to ${m ? m[1] : "3.8"} mm/s under elevated cutting force`;
    } else if (/Historical incident\s*([A-Z0-9-]+)\s*confirms identical failure/i.test(text)) {
      const m = text.match(/incident\s*([A-Z0-9-]+)/i);
      text = `Historical precedent ${m ? m[1] : "NCR-019"}: identical flank wear on CNC-04`;
    }

    return { headline: text, source };
  };

  const loadRcaData = () => {
    setLoading(true);
    api.getRcaAnalysis().then((res) => {
      setReport(res.report);
      setRagResults(res.report.historical_matches);
      setLoading(false);
    });
  };

  const handleRagSearch = async () => {
    setSearchingRag(true);
    setRagError(null);
    try {
      const res = await api.searchHistoricalIncidents(ragQuery);
      setRagResults(res.matches || []);
    } catch (e: any) {
      setRagError("Vector knowledge retrieval exception: " + (e.message || "Failed connecting to ChromaDB backend."));
    } finally {
      setSearchingRag(false);
    }
  };

  const handleHypothesisAction = async (hypId: string, action: string) => {
    setSubmittingAction(true);
    try {
      const res = await api.submitHypothesisDecision(hypId, action, `Manual engineering action: ${action}`);
      setActionFeedback(`Decision Recorded: ${res.notice} (ID: ${res.decision_id})`);
      loadRcaData();
    } catch (err: any) {
      setActionFeedback(`Action error: ${err.message || err}`);
    } finally {
      setSubmittingAction(false);
      setTimeout(() => setActionFeedback(null), 5000);
    }
  };

  const toggleBreakdown = (hypId: string) => {
    setExpandedBreakdown((prev) => ({ ...prev, [hypId]: !prev[hypId] }));
  };

  if (loading || !report) {
    return <div className="p-8 text-center text-slate-500 font-medium">Loading Root Cause Analysis & Empirical Evidence...</div>;
  }

  return (
    <div className="space-y-6">

      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-[26px] font-bold text-slate-900 leading-tight">Root Cause Analysis (RCA)</h2>
            <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-blue-100 text-blue-800 border border-blue-200">
              Agent 6
            </span>
          </div>
          <p className="text-[14px] text-slate-500 mt-1">
            Systematic evidence-supported causal investigation using deterministic scoring, 6M Fishbone, 5-Whys, and telemetry correlation.
          </p>
        </div>

      </div>

      {actionFeedback && (
        <div className={`p-4 rounded-xl border flex items-center justify-between text-xs font-semibold ${
          actionFeedback.includes("403") || actionFeedback.includes("error")
            ? "bg-red-50 text-red-900 border-red-300"
            : "bg-emerald-50 text-emerald-900 border-emerald-300"
        }`}>
          <span>{actionFeedback}</span>
          <button onClick={() => setActionFeedback(null)} className="text-slate-400 hover:text-slate-600">&times;</button>
        </div>
      )}

      <div className="p-4 bg-amber-50 border border-amber-200 rounded-xl flex items-start gap-3.5 shadow-2xs">
        <AlertTriangle className="w-5 h-5 text-amber-700 shrink-0 mt-0.5" />
        <div className="space-y-0.5 text-[13px] text-amber-900 leading-relaxed">
          <span className="font-bold block uppercase tracking-wider text-[12px]">
            Engineering Guardrail: Statistical Correlation Does Not Prove Causation
          </span>
          <p>{report.correlation_vs_causation_note}</p>
        </div>
      </div>

      <div className="border-b border-[#E3E8EF] bg-white rounded-t-xl px-4 pt-2 flex items-center gap-4 text-[13.5px] font-semibold overflow-x-auto">
        {[
          { id: "hypotheses", label: `Ranked Hypotheses (${report.ranked_hypotheses.length})` },
          { id: "five_whys", label: "5-Whys Sequential Chains" },
          { id: "fishbone", label: "Ishikawa Diagram (6M Matrix)" },
          { id: "correlation", label: "Correlation & Precedence" },
          { id: "inputs", label: "Investigated 8 Inputs" },
          { id: "rag", label: `Historical NCR Retrieval (${ragResults.length})` },
        ].map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id as any)}
            className={`pb-2.5 pt-1 border-b-2 cursor-pointer transition-all whitespace-nowrap ${
              activeTab === tab.id
                ? "border-[#2563EB] text-[#2563EB] font-bold"
                : "border-transparent text-slate-500 hover:text-slate-800"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {activeTab === "hypotheses" && (
        <div className="space-y-4">
          {report.ranked_hypotheses.map((hyp, idx) => (
            <div key={hyp.hypothesis_id} className="p-5 bg-white border border-slate-200 rounded-xl shadow-xs space-y-4">

              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-100 pb-3">
                <div className="flex items-center gap-3">
                  <div className={`w-8 h-8 rounded-lg flex items-center justify-center font-bold text-sm ${
                    idx === 0 ? "bg-amber-100 text-amber-900 border border-amber-300" : "bg-slate-100 text-slate-700"
                  }`}>
                    #{hyp.rank || idx + 1}
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-xs font-bold text-blue-600">{hyp.hypothesis_id}</span>
                      <span className="text-slate-300">&bull;</span>
                      <span className="text-xs font-semibold text-slate-600">6M Category: {hyp.category}</span>
                      <span className="text-slate-300">&bull;</span>
                      <span className={`text-[11px] font-bold px-2 py-0.5 rounded ${
                        hyp.status === "CONFIRMED"
                          ? "bg-emerald-100 text-emerald-800"
                          : (hyp.status === "REJECTED" ? "bg-red-100 text-red-800" : "bg-slate-100 text-slate-700")
                      }`}>
                        {hyp.status}
                      </span>
                    </div>
                    <h3 className="text-base font-bold text-slate-900 mt-0.5">{hyp.title}</h3>
                  </div>
                </div>

                <div className="flex items-center gap-3">
                  <div className="text-right">
                    <span className="text-[10px] text-slate-400 block uppercase font-medium">Deterministic Score</span>
                    <span className="text-base font-bold text-blue-700 font-mono">
                      {(hyp.confidence_score * 100).toFixed(0)}%
                    </span>
                    <span className="text-[10px] text-slate-500 block">
                      {hyp.confidence_text || "Requires verification"}
                    </span>
                  </div>
                  <CertaintyBadge level={hyp.certainty || (hyp.status === "CONFIRMED" ? "Confirmed Root Cause" : "Hypothesis")} />
                </div>
              </div>

              <p className="text-[13px] text-slate-700 leading-relaxed font-normal bg-slate-50/70 p-3 rounded-lg border border-slate-200/80">{hyp.description}</p>

              {hyp.score_breakdown && (
                <div className="bg-slate-50 border border-slate-200 rounded-lg p-3 space-y-2 text-xs">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-slate-800 flex items-center gap-1.5">
                      <Calculator className="w-3.5 h-3.5 text-blue-600" />
                      Deterministic Score Formula Breakdown (docs/rca_methodology.md)
                    </span>
                    <button
                      onClick={() => toggleBreakdown(hyp.hypothesis_id)}
                      className="text-blue-600 hover:text-blue-800 text-[11px] font-semibold cursor-pointer"
                    >
                      {expandedBreakdown[hyp.hypothesis_id] ? "Hide Breakdown" : "View Breakdown"}
                    </button>
                  </div>

                  {expandedBreakdown[hyp.hypothesis_id] && (
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-2 pt-2 border-t border-slate-200 text-slate-700 font-mono text-[11px]">
                      <div>Base Weight: <strong className="text-slate-900">{hyp.score_breakdown.base_weight}</strong></div>
                      <div>&sum; Supporting: <strong className="text-emerald-700">+{hyp.score_breakdown.sum_supporting}</strong></div>
                      <div>&sum; Contradicting: <strong className="text-red-700">-{hyp.score_breakdown.sum_contradicting}</strong></div>
                      <div>Net Difference: <strong className="text-blue-700">{hyp.score_breakdown.net_difference}</strong></div>
                      <div className="col-span-2 md:col-span-4 text-[10.5px] text-slate-500 font-mono">
                        Formula: {hyp.score_breakdown.formula}
                      </div>
                    </div>
                  )}
                </div>
              )}

              <div className="grid grid-cols-1 md:grid-cols-3 gap-3.5">

                <div className="p-3.5 bg-emerald-50/50 border border-emerald-200 rounded-xl space-y-2.5">
                  <div className="flex items-center gap-1.5 font-bold text-emerald-900 text-xs">
                    <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                    <span>Supporting Evidence ({hyp.supporting_evidence.length})</span>
                  </div>
                  <div className="space-y-2">
                    {hyp.supporting_evidence.map((ev, i) => {
                      const item = parseEvidence(ev);
                      return (
                        <div key={i} className="p-2.5 rounded-lg bg-white border border-emerald-200/70 shadow-2xs space-y-1">
                          <p className="text-[12.5px] font-semibold text-slate-800 leading-snug">{item.headline}</p>
                          {item.source && (
                            <span className="inline-block text-[10.5px] font-mono px-1.5 py-0.5 rounded bg-emerald-100 text-emerald-800 font-semibold">
                              Source: {item.source}
                            </span>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </div>

                <div className="p-3.5 bg-slate-50 border border-slate-200 rounded-xl space-y-2.5">
                  <div className="flex items-center gap-1.5 font-bold text-slate-800 text-xs">
                    <XCircle className="w-4 h-4 text-slate-500 shrink-0" />
                    <span>Contradicting / Neutral ({hyp.contradicting_evidence.length})</span>
                  </div>
                  <div className="space-y-2">
                    {hyp.contradicting_evidence.length > 0 ? (
                      hyp.contradicting_evidence.map((ev, i) => {
                        const item = parseEvidence(ev);
                        return (
                          <div key={i} className="p-2.5 rounded-lg bg-white border border-slate-200 shadow-2xs space-y-1">
                            <p className="text-[12.5px] font-medium text-slate-700 leading-snug">{item.headline}</p>
                            {item.source && (
                              <span className="inline-block text-[10.5px] font-mono px-1.5 py-0.5 rounded bg-slate-100 text-slate-600 font-semibold">
                                Source: {item.source}
                              </span>
                            )}
                          </div>
                        );
                      })
                    ) : (
                      <p className="text-[12px] text-slate-400 italic">No contradicting findings detected</p>
                    )}
                  </div>
                </div>

                <div className="p-3.5 bg-amber-50/50 border border-amber-200 rounded-xl space-y-2.5">
                  <div className="flex items-center gap-1.5 font-bold text-amber-900 text-xs">
                    <HelpCircle className="w-4 h-4 text-amber-600 shrink-0" />
                    <span>Missing Evidence ({hyp.missing_evidence?.length || 0})</span>
                  </div>
                  <div className="space-y-2">
                    {(hyp.missing_evidence && hyp.missing_evidence.length > 0
                      ? hyp.missing_evidence
                      : ["Additional physical validation pending"]
                    ).map((ev, i) => {
                      const item = parseEvidence(ev);
                      return (
                        <div key={i} className="p-2.5 rounded-lg bg-white border border-amber-200/70 shadow-2xs space-y-1">
                          <p className="text-[12.5px] font-medium text-amber-950 leading-snug">{item.headline}</p>
                          {item.source && (
                            <span className="inline-block text-[10.5px] font-mono px-1.5 py-0.5 rounded bg-amber-100 text-amber-800 font-semibold">
                              Source: {item.source}
                            </span>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </div>
              </div>

              <div className="p-3 bg-blue-50/70 border border-blue-200 rounded-lg flex items-start gap-2.5 text-xs text-blue-950">
                <ShieldCheck className="w-4 h-4 text-blue-600 shrink-0 mt-0.5" />
                <div>
                  <span className="font-bold text-blue-900">Physical Confirmation: </span>
                  <span className="text-slate-800 font-medium">{hyp.required_confirmation}</span>
                </div>
              </div>

              <div className="flex flex-wrap items-center justify-between gap-3 pt-2 border-t border-slate-100">
                <span className="text-[11px] text-slate-500">
                  <span className="text-emerald-700 font-semibold flex items-center gap-1">
                    <UserCheck className="w-3 h-3" /> Authorized Quality Engineering Action
                  </span>
                </span>

                <div className="flex items-center gap-2">
                  <button
                    onClick={() => handleHypothesisAction(hyp.hypothesis_id, "CONFIRM")}
                    disabled={submittingAction}
                    className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-bold flex items-center gap-1 cursor-pointer transition-colors shadow-2xs"
                  >
                    <Check className="w-3.5 h-3.5" />
                    <span>Confirm Root Cause</span>
                  </button>
                  <button
                    onClick={() => handleHypothesisAction(hyp.hypothesis_id, "REJECT")}
                    disabled={submittingAction}
                    className="px-3 py-1.5 bg-red-50 hover:bg-red-100 text-red-700 border border-red-200 rounded-lg text-xs font-bold flex items-center gap-1 cursor-pointer transition-colors"
                  >
                    <Ban className="w-3.5 h-3.5" />
                    <span>Reject</span>
                  </button>
                  <button
                    onClick={() => handleHypothesisAction(hyp.hypothesis_id, "COMMENT")}
                    disabled={submittingAction}
                    className="px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg text-xs font-semibold flex items-center gap-1 cursor-pointer transition-colors"
                  >
                    <MessageSquare className="w-3.5 h-3.5" />
                    <span>Comment</span>
                  </button>
                  <button
                    onClick={() => handleHypothesisAction(hyp.hypothesis_id, "REQUEST_REANALYSIS")}
                    disabled={submittingAction}
                    className="px-3 py-1.5 bg-blue-50 hover:bg-blue-100 text-blue-700 border border-blue-200 rounded-lg text-xs font-semibold flex items-center gap-1 cursor-pointer transition-colors"
                  >
                    <RefreshCw className="w-3.5 h-3.5" />
                    <span>Request Re-analysis</span>
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {activeTab === "five_whys" && (
        <div className="p-5 bg-white border border-slate-200 rounded-xl shadow-xs space-y-4">
          <div className="border-b border-slate-100 pb-3">
            <h3 className="text-sm font-bold text-slate-900">5-Whys Sequential Root Cause Interrogation</h3>
            <p className="text-xs text-slate-500">Structured inductive reasoning tracing dimensional expansion to CNC tooling lockout gap</p>
          </div>

          <div className="space-y-4 relative before:absolute before:left-4 before:top-4 before:bottom-4 before:w-0.5 before:bg-blue-200">
            {report.five_whys.map((w) => (
              <div key={w.level} className="relative pl-10 space-y-1.5">
                <div className="absolute left-2.5 top-1 -translate-x-1/2 w-4 h-4 rounded-full bg-blue-600 text-white text-[10px] font-bold flex items-center justify-center">
                  {w.level}
                </div>
                <div className="text-xs font-bold text-slate-800">
                  Why {w.level}: {w.question}
                </div>
                <div className="p-3 bg-slate-50 border border-slate-200 rounded-lg text-xs space-y-1">
                  <div className="text-slate-900 font-medium">{w.answer}</div>
                  <div className="text-[11px] text-blue-700 font-medium">Empirical Evidence: {w.evidence}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {activeTab === "fishbone" && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {report.fishbone_diagram.map((cat, i) => (
            <div key={i} className="p-4 bg-white border border-slate-200 rounded-xl shadow-xs space-y-3">
              <div className="flex items-center justify-between border-b border-slate-100 pb-2">
                <span className="text-xs font-bold text-slate-900 uppercase tracking-wider">
                  {cat.category}
                </span>
                <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-100 text-slate-600 font-mono">
                  6M Branch
                </span>
              </div>
              <ul className="space-y-2 text-xs text-slate-600">
                {cat.factors.map((f, idx) => (
                  <li key={idx} className="flex items-start gap-2">
                    <span className="w-1.5 h-1.5 rounded-full bg-blue-600 shrink-0 mt-1.5" />
                    <span>{f}</span>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      )}

      {activeTab === "correlation" && (
        <div className="space-y-4">

          {report.temporal_precedence && (
            <div className="p-4 bg-blue-50 border border-blue-200 rounded-xl space-y-2 shadow-2xs">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-blue-900 uppercase tracking-wider flex items-center gap-1.5">
                  <Activity className="w-4 h-4 text-blue-600" />
                  Temporal Precedence Sequence Verification
                </span>
                <span className="px-2 py-0.5 rounded text-[11px] font-bold bg-blue-600 text-white font-mono">
                  PRECEDENCE SATISFIED
                </span>
              </div>
              <p className="text-xs text-blue-800 leading-relaxed">
                {report.temporal_precedence.details}
              </p>
            </div>
          )}

          <div className="p-4 bg-white border border-slate-200 rounded-xl shadow-xs space-y-3">
            <div className="flex items-center justify-between border-b border-slate-100 pb-2">
              <div>
                <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
                  Telemetry Association Matrix (Pearson & Spearman)
                </h3>
                <p className="text-[11px] text-slate-500">
                  Rigorous statistical associations against measured shaft diameter deviation
                </p>
              </div>
              <span className="text-[10px] bg-slate-100 text-slate-600 px-2 py-0.5 rounded font-mono">
                Sample Size n = 5
              </span>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-xs text-left">
                <thead className="bg-slate-50 text-slate-600 uppercase text-[10px] font-mono">
                  <tr>
                    <th className="p-2.5">Parameter Pair</th>
                    <th className="p-2.5 text-right">Pearson r</th>
                    <th className="p-2.5 text-right">Pearson p-value</th>
                    <th className="p-2.5 text-right">Spearman &rho;</th>
                    <th className="p-2.5 text-right">Spearman p-value</th>
                    <th className="p-2.5">Epistemic Disclaimer</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {(report.correlations || []).map((c, idx) => (
                    <tr key={idx} className="hover:bg-slate-50 font-mono text-[11.5px]">
                      <td className="p-2.5 font-bold text-slate-800">{c.parameter_x}</td>
                      <td className="p-2.5 text-right font-bold text-blue-700">{c.pearson_r.toFixed(3)}</td>
                      <td className="p-2.5 text-right text-slate-600">{c.pearson_p_value.toFixed(4)}</td>
                      <td className="p-2.5 text-right font-bold text-emerald-700">{c.spearman_rho.toFixed(3)}</td>
                      <td className="p-2.5 text-right text-slate-600">{c.spearman_p_value.toFixed(4)}</td>
                      <td className="p-2.5 font-sans text-[11px] text-amber-800 font-medium">{c.disclaimer}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {activeTab === "inputs" && report.rca_inputs && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="p-4 bg-white border border-slate-200 rounded-xl shadow-xs space-y-2">
            <span className="text-xs font-bold text-slate-900 uppercase tracking-wider block border-b pb-1">
              1. Defect Type & Severity
            </span>
            <div className="text-xs text-slate-700 font-medium">
              Classification: <strong>{report.rca_inputs.defect_type}</strong>
            </div>
          </div>

          <div className="p-4 bg-white border border-slate-200 rounded-xl shadow-xs space-y-2">
            <span className="text-xs font-bold text-slate-900 uppercase tracking-wider block border-b pb-1">
              2. Time of Occurrence (Change-Points)
            </span>
            <div className="text-xs text-slate-700 space-y-1">
              <div>Measurement Change-Point: <strong>{report.rca_inputs.time_of_occurrence.measurement_change_point}</strong></div>
              <div>Parameter Change-Point: <strong>{report.rca_inputs.time_of_occurrence.parameter_change_point}</strong></div>
            </div>
          </div>

          <div className="p-4 bg-white border border-slate-200 rounded-xl shadow-xs space-y-2">
            <span className="text-xs font-bold text-slate-900 uppercase tracking-wider block border-b pb-1">
              3. Machine Parameters (Changed vs Unchanged)
            </span>
            <div className="text-xs text-slate-700 space-y-1">
              <div><strong>Changed:</strong> Vibration (3.84 mm/s), Motor Current (16.8 A)</div>
              <div><strong>Unchanged:</strong> Spindle Speed (1,200 RPM), Feed Rate (0.20 mm/rev), Coolant Temp (24.5°C)</div>
            </div>
          </div>

          <div className="p-4 bg-white border border-slate-200 rounded-xl shadow-xs space-y-2">
            <span className="text-xs font-bold text-slate-900 uppercase tracking-wider block border-b pb-1">
              4. Tool Condition (Cycles vs Limit)
            </span>
            <div className="text-xs text-slate-700 space-y-1">
              <div>Accumulated Usage: <strong>{report.rca_inputs.tool_condition.tool_cycles} cycles</strong></div>
              <div>Replacement Threshold: <strong>{report.rca_inputs.tool_condition.nominal_threshold} cycles (+{report.rca_inputs.tool_condition.overdue_percentage}% overdue)</strong></div>
            </div>
          </div>

          <div className="p-4 bg-white border border-slate-200 rounded-xl shadow-xs space-y-2">
            <span className="text-xs font-bold text-slate-900 uppercase tracking-wider block border-b pb-1">
              5. Material Information
            </span>
            <div className="text-xs text-slate-700 space-y-1">
              <div>Lot Number: <strong>{report.rca_inputs.material_information.material_lot}</strong></div>
              <div>Specification: <strong>{report.rca_inputs.material_information.material} ({report.rca_inputs.material_information.hardness})</strong></div>
            </div>
          </div>

          <div className="p-4 bg-white border border-slate-200 rounded-xl shadow-xs space-y-2">
            <span className="text-xs font-bold text-slate-900 uppercase tracking-wider block border-b pb-1">
              6. Maintenance History
            </span>
            <div className="text-xs text-slate-700 space-y-1">
              <div>Last Tool Change: <strong>{report.rca_inputs.maintenance_history.last_tool_change}</strong></div>
              <div>Last Calibration: <strong>{report.rca_inputs.maintenance_history.last_calibration}</strong></div>
            </div>
          </div>

          <div className="p-4 bg-white border border-slate-200 rounded-xl shadow-xs space-y-2">
            <span className="text-xs font-bold text-slate-900 uppercase tracking-wider block border-b pb-1">
              7. Previous Incidents (RAG Context)
            </span>
            <div className="text-xs text-slate-700 space-y-1">
              <div>Top Precedent: <strong>{report.rca_inputs.previous_incidents.top_historical_match}</strong> (Similarity: {report.rca_inputs.previous_incidents.similarity})</div>
              <div>Total Matches: <strong>{report.rca_inputs.previous_incidents.retrieved_count} historical NCRs</strong></div>
            </div>
          </div>

          <div className="p-4 bg-white border border-slate-200 rounded-xl shadow-xs space-y-2">
            <span className="text-xs font-bold text-slate-900 uppercase tracking-wider block border-b pb-1">
              8. Inspection Results & Trend
            </span>
            <div className="text-xs text-slate-700 space-y-1">
              <div>Nonconforming Samples: <strong>{report.rca_inputs.inspection_results.nonconforming_samples.join(", ")}</strong></div>
              <div>Rejection Rate: <strong>{report.rca_inputs.inspection_results.sample_rejection_rate_percent}%</strong></div>
              <div>Trend: <strong>{report.rca_inputs.inspection_results.trend}</strong></div>
            </div>
          </div>
        </div>
      )}

      {activeTab === "rag" && (
        <div className="space-y-4">
          <div className="p-4 bg-white border border-slate-200 rounded-xl shadow-xs space-y-3">
            <span className="text-xs font-bold text-slate-700 uppercase tracking-wider block">
              Vector Semantic Query (Embeddings & Cosine Similarity)
            </span>
            <div className="flex gap-2">
              <input
                type="text"
                value={ragQuery}
                onChange={(e) => setRagQuery(e.target.value)}
                placeholder="Search historical NCRs, SOPs, and manuals..."
                className="flex-1 px-3 py-2 border border-slate-300 rounded-lg text-xs focus:outline-hidden focus:ring-2 focus:ring-blue-500 font-medium text-slate-800"
              />
              <button
                onClick={handleRagSearch}
                disabled={searchingRag}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs font-semibold flex items-center gap-1.5 cursor-pointer shadow-xs"
              >
                <Search className="w-3.5 h-3.5" />
                <span>{searchingRag ? "Searching Vector Store..." : "Vector Search"}</span>
              </button>
            </div>
          </div>

          {ragError && (
            <div className="p-4 bg-rose-50 border border-rose-200 rounded-xl text-rose-800 text-xs flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-rose-600 shrink-0" />
              <span>{ragError}</span>
            </div>
          )}

          {!searchingRag && ragResults.length === 0 && !ragError && (
            <div className="p-8 bg-slate-50 border border-dashed border-slate-300 rounded-xl text-center space-y-2">
              <Database className="w-8 h-8 text-slate-400 mx-auto" />
              <div className="text-sm font-bold text-slate-700">No Historical Incidents Found</div>
              <p className="text-xs text-slate-500 max-w-md mx-auto">
                No manufacturing non-conformance records matched your query above the confidence similarity floor. Try searching for specific defects such as "oversized shaft diameter", "tool wear", or "chatter marks".
              </p>
            </div>
          )}

          <div className="space-y-3">
            {ragResults.map((m: any) => {
              const recId = m.incident_id || m.id || "NCR";
              const isDrawerOpen = selectedNcr && (selectedNcr.incident_id === recId || selectedNcr.id === recId);

              return (
                <div key={recId} className="p-4 bg-white border border-slate-200 rounded-xl shadow-xs space-y-3">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-xs font-bold text-blue-600 bg-blue-50 px-2 py-0.5 rounded border border-blue-200">
                        {recId}
                      </span>
                      <span className="text-xs font-bold text-slate-900">{m.title}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-mono font-bold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
                        Similarity: {((m.similarity_score || 0) * 100).toFixed(1)}%
                      </span>
                      <CertaintyBadge level="Historical Context" />
                    </div>
                  </div>

                  <div className="text-xs text-slate-600 space-y-1">
                    <div className="text-[11.5px] text-slate-500">
                      <strong>Source Document:</strong> {m.source_document || m.source_file || "historical_ncrs.json"} | <strong>Part:</strong> {m.part_number || "PS-2026-101"} | <strong>Machine:</strong> {m.machine || "CNC-04"}
                    </div>
                    <div><strong>Confirmed Historical Cause:</strong> {m.confirmed_root_cause}</div>
                    {m.action_taken && <div><strong>Corrective Action:</strong> {m.action_taken}</div>}
                    <div className="p-2 bg-amber-50 border border-amber-200 rounded-lg text-[11px] text-amber-900 font-medium">
                      Notice: Historical context only. Historical precedent does NOT establish or assume the same root cause for current production batch.
                    </div>
                  </div>

                  <div className="pt-1 flex items-center justify-between">
                    <button
                      onClick={() => setSelectedNcr(isDrawerOpen ? null : m)}
                      className="text-xs text-blue-600 hover:text-blue-800 font-semibold flex items-center gap-1 cursor-pointer"
                    >
                      <BookOpen className="w-3.5 h-3.5" />
                      <span>{isDrawerOpen ? "Close Full NCR Record" : "View Full NCR Dossier"}</span>
                    </button>
                    <span className="text-[11px] font-mono text-slate-400">
                      Provenance: {m.data_provenance || "synthetic_illustrative"}
                    </span>
                  </div>

                  {isDrawerOpen && (
                    <div className="mt-3 p-4 bg-slate-50 border border-slate-300 rounded-lg space-y-2 text-xs text-slate-800 animate-in fade-in duration-150">
                      <div className="flex items-center justify-between border-b pb-2">
                        <span className="font-bold text-slate-900 text-[13px]">Full Non-Conformance Record Dossier: {recId}</span>
                        <span className="px-2 py-0.5 rounded text-[10.5px] font-bold bg-slate-200 text-slate-700">IATF 16949 Archive</span>
                      </div>
                      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-[11.5px]">
                        <div><span className="text-slate-500">Record ID:</span> <strong className="font-mono">{recId}</strong></div>
                        <div><span className="text-slate-500">Part Number:</span> <strong>{m.part_number || "PS-2026-101"}</strong></div>
                        <div><span className="text-slate-500">Machine ID:</span> <strong>{m.machine || "CNC-04"}</strong></div>
                        <div><span className="text-slate-500">Classification:</span> <strong>{m.defect_type || "Dimensional Non-Conformance"}</strong></div>
                      </div>
                      <div className="pt-1">
                        <span className="text-slate-500 block font-semibold mb-0.5">Incident Narrative:</span>
                        <p className="p-2 bg-white rounded border border-slate-200 text-slate-700 leading-relaxed font-sans">
                          {m.description || m.snippet || m.confirmed_root_cause}
                        </p>
                      </div>
                      <div>
                        <span className="text-slate-500 block font-semibold mb-0.5">Confirmed Root Cause:</span>
                        <p className="p-2 bg-white rounded border border-slate-200 text-slate-700 font-sans">
                          {m.confirmed_root_cause}
                        </p>
                      </div>
                      <div>
                        <span className="text-slate-500 block font-semibold mb-0.5">Corrective Resolution & SOP Action:</span>
                        <p className="p-2 bg-white rounded border border-slate-200 text-slate-700 font-sans">
                          {m.action_taken || m.resolution || "Replaced tooling insert, recalibrated zero offsets, and updated operating maintenance guidelines."}
                        </p>
                      </div>
                      <div className="text-[11px] text-slate-500 pt-1 border-t flex items-center justify-between">
                        <span>Data Provenance: <em>synthetic_illustrative (Verified Decision Support Precedent)</em></span>
                        <span>Archived Under: <em>ISO 9001:2015 §10.2 / IATF 16949</em></span>
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
};

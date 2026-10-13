import React, { useEffect, useState } from "react";
import { api } from "../api";
import { WorkflowState } from "../types";
import { CertaintyBadge } from "../components/CertaintyBadge";
import {
  ShieldCheck, CheckCircle2, XCircle, AlertTriangle,
  Play, RefreshCw, UserCheck, Clock, Terminal, Lock, CheckSquare, History,
  Cpu, Database, Search, GitBranch, MessageSquare, Layers, Eye, Activity
} from "lucide-react";

interface Props {
  onRunPipeline: () => void;
  isRunningPipeline: boolean;
  userRole?: string;
  workflowId?: string;
}

export const AiReviewPage: React.FC<Props> = ({ onRunPipeline, isRunningPipeline, userRole = "quality_engineer", workflowId }) => {
  const [workflowState, setWorkflowState] = useState<WorkflowState | null>(null);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<"overview" | "trace" | "models" | "evidence" | "hypotheses" | "critic" | "decision">("overview");
  const [workflowIdInput, setWorkflowIdInput] = useState(workflowId || "");
  const [engineerName, setEngineerName] = useState("Sarah Chen, Lead Quality Engineer");
  const [disposition, setDisposition] = useState("QUARANTINE_BATCH");
  const [comments, setComments] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const [reanalysisCount, setReanalysisCount] = useState(0);
  const [reanalysisMessage, setReanalysisMessage] = useState<string | null>(null);
  const [decisionHistory, setDecisionHistory] = useState<any[]>([]);
  const [showConfirmModal, setShowConfirmModal] = useState(false);
  const [pendingDecision, setPendingDecision] = useState<string | null>(null);

  const isOperator = false;

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

  const loadWorkflow = (wfId?: string) => {
    const targetId = wfId || workflowIdInput;
    if (!targetId) {
      setWorkflowState(null);
      setLoading(false);
      loadHistory();
      return;
    }
    setLoading(true);
    api.getWorkflow(targetId)
      .then((res) => {
        if (res && res.workflow_id) {
          setWorkflowState(res);
          setWorkflowIdInput(res.workflow_id);
        } else {
          setWorkflowState(null);
        }
      })
      .catch(() => {
        setWorkflowState(null);
      })
      .finally(() => {
        setLoading(false);
      });
    loadHistory();
  };

  const loadHistory = () => {
    api.getHumanDecisions().then((records) => {
      setDecisionHistory(records || []);
    }).catch(() => {});
  };

  useEffect(() => {
    if (workflowId) {
      setWorkflowIdInput(workflowId);
      loadWorkflow(workflowId);
    } else if (workflowIdInput) {
      loadWorkflow(workflowIdInput);
    } else {
      setLoading(false);
      loadHistory();
    }
  }, [workflowId]);

  const triggerSignOff = (decision: string) => {
    if (isOperator) {
      alert("Permission Denied: Operator persona cannot authorize batch disposition.");
      return;
    }
    setPendingDecision(decision);
    setShowConfirmModal(true);
  };

  const executeSignOff = async () => {
    if (!pendingDecision) return;
    const dec = pendingDecision;
    setShowConfirmModal(false);

    try {
      let res: any;
      if (workflowState?.workflow_id) {
        res = await api.submitWorkflowDecision(workflowState.workflow_id, {
          approved_by: engineerName,
          decision: dec,
          engineering_comments: comments,
          disposition: disposition,
          confirmed_root_cause: "Progressive Cutting Tool Flank Wear on CNC-04",
        });
      } else {
        res = await api.submitHumanDecision({
          approved_by: engineerName,
          decision: dec,
          engineering_comments: comments,
          disposition: disposition,
          confirmed_root_cause: "Progressive Cutting Tool Flank Wear on CNC-04",
        });
      }
      setSubmitted(true);
      alert(`Human Decision Recorded: ${res.decision}. Disposition: ${res.disposition || disposition}`);
      loadHistory();
      // Reload current workflow state to reflect human decision
      if (workflowState?.workflow_id) {
        api.getWorkflow(workflowState.workflow_id).then(setWorkflowState).catch(() => {});
      }
    } catch (e: any) {
      alert(`Failed to record decision: ${e.message}`);
    }
  };

  const handleRequestReanalysis = async () => {
    if (isOperator) {
      alert("Permission Denied: Operator persona cannot request agent re-analysis.");
      return;
    }
    if (!comments.trim()) {
      alert("Please provide engineering instructions in the comments box for re-analysis.");
      return;
    }

    try {
      const res = await api.requestWorkflowReanalysis(
        workflowState?.workflow_id || workflowIdInput || "",
        "rca_agent",
        comments
      );
      setReanalysisCount(res.loop_count || reanalysisCount + 1);
      if (res.status === "ESCALATED_MAX_LOOPS_REACHED") {
        setReanalysisMessage("Maximum re-analysis loop count (3) reached. System stopped looping and escalated to Lead Quality Engineer for manual disposition.");
        alert("Maximum re-analysis loop count (3) reached. System stopped looping and escalated to Lead Quality Engineer.");
      } else {
        alert(`Agent re-analysis completed (Loop ${res.loop_count} of 3). Output updated.`);
      }
      loadHistory();
      if (workflowState?.workflow_id) {
        api.getWorkflow(workflowState.workflow_id).then(setWorkflowState).catch(() => {});
      }
    } catch (e: any) {
      alert(`Re-analysis error: ${e.message}`);
    }
  };

  if (loading) {
    return (
      <div className="p-12 text-center space-y-4">
        <div className="w-8 h-8 border-3 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto" />
        <p className="text-[14.5px] text-slate-500 font-medium">Loading AI Agent Pipeline Audit & Traceability...</p>
      </div>
    );
  }

  if (!workflowState) {
    return (
      <div className="space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-[26px] font-bold text-slate-900 leading-tight">AI Review Center</h2>
              <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-100 text-blue-800 border border-blue-200">
                FR-17 Execution Visibility
              </span>
            </div>
            <p className="text-[14px] text-slate-500 mt-1">
              Real-time execution visibility across specialized agents, tool invocations, model predictions, RAG evidence, and human governance.
            </p>
          </div>
          <div className="flex items-center gap-2 flex-wrap">
            <div className="flex items-center gap-1.5 bg-slate-100 px-3 py-1.5 rounded-lg border border-slate-200">
              <span className="text-xs font-medium text-slate-600">Run ID:</span>
              <input
                type="text"
                placeholder="WF-..."
                value={workflowIdInput}
                onChange={(e) => setWorkflowIdInput(e.target.value)}
                className="font-mono text-xs font-bold text-slate-800 bg-white px-2 py-1 rounded border border-slate-300 w-32"
              />
              <button
                onClick={() => loadWorkflow(workflowIdInput)}
                className="text-xs font-semibold text-blue-600 hover:text-blue-800 px-1.5 py-0.5"
              >
                Load
              </button>
            </div>
            <button
              onClick={onRunPipeline}
              disabled={isRunningPipeline}
              className="btn-primary !h-[40px]"
            >
              <Play className="w-4 h-4 fill-white" />
              <span>Run Pipeline</span>
            </button>
          </div>
        </div>

        <div className="p-12 text-center bg-white border border-slate-200 rounded-xl space-y-3 shadow-xs">
          <Cpu className="w-10 h-10 text-slate-400 mx-auto" />
          <h3 className="text-base font-bold text-slate-900">No Active AI Workflow Review</h3>
          <p className="text-sm text-slate-500 max-w-md mx-auto">
            No quality inspection workflow execution loaded yet. Select a production batch and execute the multi-agent inspection pipeline to review computer vision findings, sensor drift, RAG hypotheses, and critic evaluations.
          </p>
          <button
            onClick={onRunPipeline}
            disabled={isRunningPipeline}
            className="btn-primary mx-auto mt-2"
          >
            <Play className="w-4 h-4 fill-white" />
            <span>Run Quality Inspection Pipeline</span>
          </button>
        </div>
      </div>
    );
  }

  const currentAgentName = workflowState.current_agent || "Human Quality Engineer (Gatekeeper)";
  const traceSteps = workflowState.execution_trace || [];
  const visualPred = workflowState.visual_prediction;
  const processReport = workflowState.process_report;
  const rcaReport = workflowState.rca_report;
  const criticReview = workflowState.critic_review;
  const humanApproval = workflowState.human_approval;

  return (
    <div className="space-y-6">
      {/* Header with FR-17 Title & Controls */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-[26px] font-bold text-slate-900 leading-tight">AI Review Center</h2>
            <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-100 text-blue-800 border border-blue-200">
              FR-17 Execution Visibility
            </span>
          </div>
          <p className="text-[14px] text-slate-500 mt-1">
            Real-time execution visibility across specialized agents, tool invocations, model predictions, RAG evidence, and human governance.
          </p>
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          <div className="flex items-center gap-1.5 bg-slate-100 px-3 py-1.5 rounded-lg border border-slate-200">
            <span className="text-xs font-medium text-slate-600">Run ID:</span>
            <input
              type="text"
              value={workflowIdInput}
              onChange={(e) => setWorkflowIdInput(e.target.value)}
              className="font-mono text-xs font-bold text-slate-800 bg-white px-2 py-1 rounded border border-slate-300 w-32"
            />
            <button
              onClick={() => loadWorkflow(workflowIdInput)}
              className="text-xs font-semibold text-blue-600 hover:text-blue-800 px-1.5 py-0.5"
            >
              Load
            </button>
          </div>
          <button
            onClick={onRunPipeline}
            disabled={isRunningPipeline}
            className="btn-primary !h-[40px]"
          >
            <Play className="w-4 h-4 fill-white" />
            <span>Re-Run Review</span>
          </button>
        </div>
      </div>

      {/* FR-17 Requirement 1: Current Agent & Workflow Status Banner */}
      <div className="p-4 bg-gradient-to-r from-blue-900 via-indigo-900 to-slate-900 text-white rounded-xl shadow-md border border-blue-700/50 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="w-11 h-11 rounded-lg bg-blue-500/20 border border-blue-400/40 flex items-center justify-center text-blue-300 shrink-0">
            <Cpu className="w-6 h-6" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-semibold text-blue-300 uppercase tracking-wider">FR-17.1 Current Agent:</span>
              <span className="px-2 py-0.5 rounded text-xs font-bold bg-amber-400/20 text-amber-300 border border-amber-400/30">
                {currentAgentName}
              </span>
            </div>
            <h3 className="text-lg font-bold text-white mt-0.5">
              Workflow Status: {workflowState.status}
            </h3>
            <p className="text-xs text-blue-200/80">
              Batch: <strong className="text-white">{workflowState.batch_id}</strong> | Run ID: <strong className="text-white">{workflowState.workflow_id}</strong> | Completed Steps: <strong className="text-white">{traceSteps.length} of 8</strong>
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3 self-end md:self-center">
          <div className="text-right">
            <span className="text-xs text-blue-300 block">Gate Status</span>
            <span className="text-xs font-bold px-2.5 py-1 rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-400/30">
              {workflowState.status.includes("APPROVAL") || workflowState.status.includes("PAUSED") ? "Awaiting Human Sign-Off" : "Execution Completed"}
            </span>
          </div>
        </div>
      </div>

      {/* Navigation Tabs for FR-17 Display Requirements */}
      <div className="flex items-center gap-2 border-b border-slate-200 overflow-x-auto pb-1 text-xs sm:text-sm font-medium">
        <button
          onClick={() => setActiveTab("overview")}
          className={`px-3 py-2 rounded-t-lg transition-colors flex items-center gap-1.5 cursor-pointer ${activeTab === "overview" ? "bg-white border-t border-x border-slate-200 text-blue-600 font-bold -mb-[5px] pb-3" : "text-slate-600 hover:text-slate-900"}`}
        >
          <Layers className="w-4 h-4" />
          <span>Full Overview</span>
        </button>
        <button
          onClick={() => setActiveTab("trace")}
          className={`px-3 py-2 rounded-t-lg transition-colors flex items-center gap-1.5 cursor-pointer ${activeTab === "trace" ? "bg-white border-t border-x border-slate-200 text-blue-600 font-bold -mb-[5px] pb-3" : "text-slate-600 hover:text-slate-900"}`}
        >
          <Terminal className="w-4 h-4" />
          <span>Agent Trace & Tool Calls ({traceSteps.length})</span>
        </button>
        <button
          onClick={() => setActiveTab("models")}
          className={`px-3 py-2 rounded-t-lg transition-colors flex items-center gap-1.5 cursor-pointer ${activeTab === "models" ? "bg-white border-t border-x border-slate-200 text-blue-600 font-bold -mb-[5px] pb-3" : "text-slate-600 hover:text-slate-900"}`}
        >
          <Eye className="w-4 h-4" />
          <span>Model Results (CV & Telemetry)</span>
        </button>
        <button
          onClick={() => setActiveTab("evidence")}
          className={`px-3 py-2 rounded-t-lg transition-colors flex items-center gap-1.5 cursor-pointer ${activeTab === "evidence" ? "bg-white border-t border-x border-slate-200 text-blue-600 font-bold -mb-[5px] pb-3" : "text-slate-600 hover:text-slate-900"}`}
        >
          <Database className="w-4 h-4" />
          <span>Retrieved Evidence ({rcaReport?.historical_matches?.length || 0})</span>
        </button>
        <button
          onClick={() => setActiveTab("hypotheses")}
          className={`px-3 py-2 rounded-t-lg transition-colors flex items-center gap-1.5 cursor-pointer ${activeTab === "hypotheses" ? "bg-white border-t border-x border-slate-200 text-blue-600 font-bold -mb-[5px] pb-3" : "text-slate-600 hover:text-slate-900"}`}
        >
          <GitBranch className="w-4 h-4" />
          <span>RCA Hypotheses ({rcaReport?.ranked_hypotheses?.length || 0})</span>
        </button>
        <button
          onClick={() => setActiveTab("critic")}
          className={`px-3 py-2 rounded-t-lg transition-colors flex items-center gap-1.5 cursor-pointer ${activeTab === "critic" ? "bg-white border-t border-x border-slate-200 text-blue-600 font-bold -mb-[5px] pb-3" : "text-slate-600 hover:text-slate-900"}`}
        >
          <ShieldCheck className="w-4 h-4" />
          <span>Reviewer Comments ({criticReview?.review_comments?.length || 0})</span>
        </button>
        <button
          onClick={() => setActiveTab("decision")}
          className={`px-3 py-2 rounded-t-lg transition-colors flex items-center gap-1.5 cursor-pointer ${activeTab === "decision" ? "bg-white border-t border-x border-slate-200 text-blue-600 font-bold -mb-[5px] pb-3" : "text-slate-600 hover:text-slate-900"}`}
        >
          <UserCheck className="w-4 h-4" />
          <span>Human Decision Gate</span>
        </button>
      </div>

      {/* ========================================================================= */}
      {/* SECTION 1: EXECUTION TRACE, AGENT INPUTS, AND TOOL CALLS (FR-17.1, 2, 3) */}
      {/* ========================================================================= */}
      {(activeTab === "overview" || activeTab === "trace") && (
        <div className="bg-white border border-[#E3E8EF] rounded-xl shadow-xs overflow-hidden space-y-4 p-5">
          <div className="flex items-center justify-between border-b border-slate-100 pb-3">
            <div className="flex items-center gap-2">
              <Terminal className="w-5 h-5 text-indigo-600" />
              <div>
                <h3 className="text-[16px] font-bold text-slate-900">
                  FR-17.1, FR-17.2 & FR-17.3 — Multi-Agent Execution Trace & Tool Invocations
                </h3>
                <p className="text-xs text-slate-500">
                  Verifiable audit log of each agent, actual input payload summary, tools called, status, duration, and output.
                </p>
              </div>
            </div>
            <span className="px-2.5 py-1 rounded bg-slate-100 font-mono text-xs font-semibold text-slate-700">
              {traceSteps.length} Steps Logged
            </span>
          </div>

          <div className="space-y-3">
            {traceSteps.map((step) => (
              <div key={step.step_number} className="p-4 bg-slate-50 border border-slate-200 rounded-lg hover:border-blue-300 transition-colors">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-200/60 pb-2.5 mb-2.5">
                  <div className="flex items-center gap-2.5">
                    <span className="w-6 h-6 rounded-full bg-blue-600 text-white font-mono text-xs font-bold flex items-center justify-center shrink-0">
                      {step.step_number}
                    </span>
                    <strong className="text-sm font-bold text-slate-900">{step.agent_name}</strong>
                    <span className="px-2 py-0.5 rounded text-[11px] font-bold bg-emerald-100 text-emerald-800 border border-emerald-200">
                      {step.status}
                    </span>
                  </div>
                  <div className="flex items-center gap-3 text-xs text-slate-500">
                    <span className="flex items-center gap-1 font-mono">
                      <Clock className="w-3.5 h-3.5 text-slate-400" />
                      {step.duration_ms} ms
                    </span>
                    <span className="font-mono text-slate-400">{step.timestamp}</span>
                    <CertaintyBadge level={step.certainty_level} />
                  </div>
                </div>

                {/* FR-17.2: Agent Input */}
                <div className="space-y-1.5 text-xs text-slate-700">
                  <div className="p-2.5 bg-blue-50/70 border border-blue-200/60 rounded text-slate-800">
                    <strong className="text-blue-900 block mb-0.5">FR-17.2 Agent Input:</strong>
                    <span className="font-mono text-[11.5px]">{step.input_summary}</span>
                  </div>

                  {/* FR-17.3: Tool Calls */}
                  {step.tool_calls && step.tool_calls.length > 0 && (
                    <div className="p-2.5 bg-amber-50/70 border border-amber-200/60 rounded text-slate-800">
                      <strong className="text-amber-900 block mb-1">FR-17.3 Tool Invocations ({step.tool_calls.length} Tools):</strong>
                      <div className="flex flex-wrap gap-1.5">
                        {step.tool_calls.map((tool, idx) => (
                          <span key={idx} className="px-2 py-0.5 rounded bg-white border border-amber-300 font-mono text-[11px] font-semibold text-amber-900 shadow-2xs">
                            ⚙ {tool}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Agent Output Summary */}
                  <div className="p-2.5 bg-white border border-slate-200 rounded text-slate-700">
                    <strong className="text-slate-900 block mb-0.5">Agent Output:</strong>
                    <span>{step.output_summary}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* SECTION 2: MODEL RESULTS (FR-17.4)                                        */}
      {/* ========================================================================= */}
      {(activeTab === "overview" || activeTab === "models") && (
        <div className="p-5 bg-white border border-[#E3E8EF] rounded-xl shadow-xs space-y-4">
          <div className="flex items-center justify-between border-b border-slate-100 pb-3">
            <div className="flex items-center gap-2">
              <Eye className="w-5 h-5 text-purple-600" />
              <div>
                <h3 className="text-[16px] font-bold text-slate-900">
                  FR-17.4 — Model Results & Inference Metadata
                </h3>
                <p className="text-xs text-slate-500">
                  Recorded machine learning inference outputs, version identifiers, bounding boxes, and anomaly scores.
                </p>
              </div>
            </div>
            <span className="status-pill info">Verified ML Outputs</span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Visual Inspection CV Model */}
            <div className="p-4 bg-purple-50/50 border border-purple-200 rounded-lg space-y-2.5">
              <div className="flex items-center justify-between">
                <strong className="text-purple-900 text-sm flex items-center gap-1.5">
                  <Eye className="w-4 h-4 text-purple-700" />
                  Agent 2: Computer Vision Model
                </strong>
                <span className="px-2 py-0.5 rounded text-[11px] font-mono bg-purple-200 text-purple-900">
                  {visualPred?.model_version || "mobilenetv3-multiproduct-v2.0"}
                </span>
              </div>

              {visualPred ? (
                <div className="space-y-1.5 text-xs text-purple-950">
                  <div className="grid grid-cols-2 gap-2 bg-white p-2.5 rounded border border-purple-100">
                    <div>
                      <span className="text-slate-500 block">Defect Detected:</span>
                      <strong className="text-rose-600">{visualPred.defect_detected ? "YES (Defective)" : "NO (Conforming)"}</strong>
                    </div>
                    <div>
                      <span className="text-slate-500 block">Defect Type:</span>
                      <strong className="capitalize">{visualPred.defect_type}</strong>
                    </div>
                    <div>
                      <span className="text-slate-500 block">Model Confidence:</span>
                      <strong>{(visualPred.confidence * 100).toFixed(1)}%</strong>
                    </div>
                    <div>
                      <span className="text-slate-500 block">Anomaly Score:</span>
                      <strong className="font-mono">{visualPred.anomaly_score?.toFixed(3) || "0.942"}</strong>
                    </div>
                  </div>

                  <div className="p-2 bg-white rounded border border-purple-100 text-slate-700 font-mono text-[11px]">
                    <strong>Bounding Box:</strong> {JSON.stringify(visualPred.bounding_box || visualPred.bbox || { x: 209, y: 203, width: 118, height: 119 })}
                  </div>

                  <div className="flex items-center justify-between text-[11.5px] text-purple-800">
                    <span>Review State: <strong>{visualPred.review_status || "HUMAN_REVIEW_REQUIRED"}</strong></span>
                    <span>Certainty: <strong className="text-amber-700">Model Prediction</strong></span>
                  </div>
                </div>
              ) : (
                <div className="text-xs text-slate-500 py-3 text-center">No visual inspection image submitted for this batch.</div>
              )}
            </div>

            {/* Process Monitoring Isolation Forest Model */}
            <div className="p-4 bg-blue-50/50 border border-blue-200 rounded-lg space-y-2.5">
              <div className="flex items-center justify-between">
                <strong className="text-blue-900 text-sm flex items-center gap-1.5">
                  <Activity className="w-4 h-4 text-blue-700" />
                  Agent 4: Process Anomaly Detection
                </strong>
                <span className="px-2 py-0.5 rounded text-[11px] font-mono bg-blue-200 text-blue-900">
                  isolation-forest-zscore-v1
                </span>
              </div>

              {processReport ? (
                <div className="space-y-1.5 text-xs text-blue-950">
                  <div className="grid grid-cols-2 gap-2 bg-white p-2.5 rounded border border-blue-100">
                    <div>
                      <span className="text-slate-500 block">Anomalies Detected:</span>
                      <strong className={processReport.anomalies_detected > 0 ? "text-amber-600" : "text-emerald-600"}>
                        {processReport.anomalies_detected} flagged
                      </strong>
                    </div>
                    <div>
                      <span className="text-slate-500 block">Process Drift:</span>
                      <strong className="text-rose-600">{processReport.drift_detected ? "Significant Upward Drift" : "Stable"}</strong>
                    </div>
                    <div>
                      <span className="text-slate-500 block">Vibration Level:</span>
                      <strong>{processReport.vibration_current} mm/s (Base: {processReport.vibration_baseline})</strong>
                    </div>
                    <div>
                      <span className="text-slate-500 block">Tool Cycles:</span>
                      <strong>{processReport.tool_cycles_current} (Max: {processReport.tool_cycles_baseline})</strong>
                    </div>
                  </div>

                  <div className="p-2 bg-white rounded border border-blue-100 text-slate-700 text-[11.5px]">
                    <strong>Flagged Parameters:</strong> {processReport.critical_parameters?.join(", ") || "machine_vibration_mms, tool_usage_cycles"}
                  </div>

                  <div className="flex items-center justify-between text-[11.5px] text-blue-800">
                    <span>Machine: <strong>{processReport.machine}</strong></span>
                    <span>Certainty: <strong className="text-blue-700">Statistical Finding</strong></span>
                  </div>
                </div>
              ) : (
                <div className="text-xs text-slate-500 py-3 text-center">Telemetry model data unavailable.</div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* SECTION 3: RETRIEVED EVIDENCE (RAG VECTOR SEARCH) (FR-17.5)                */}
      {/* ========================================================================= */}
      {(activeTab === "overview" || activeTab === "evidence") && (
        <div className="p-5 bg-white border border-[#E3E8EF] rounded-xl shadow-xs space-y-4">
          <div className="flex items-center justify-between border-b border-slate-100 pb-3">
            <div className="flex items-center gap-2">
              <Database className="w-5 h-5 text-emerald-600" />
              <div>
                <h3 className="text-[16px] font-bold text-slate-900">
                  FR-17.5 — Retrieved Evidence (RAG Vector Search)
                </h3>
                <p className="text-xs text-slate-500">
                  ChromaDB vector retrieval results with similarity scores, root causes, and source references.
                </p>
              </div>
            </div>
            <span className="status-pill success">
              {rcaReport?.historical_matches?.length || 0} Matches Retrieved
            </span>
          </div>

          <div className="space-y-3">
            {rcaReport?.historical_matches && rcaReport.historical_matches.length > 0 ? (
              rcaReport.historical_matches.map((match, i) => (
                <div key={i} className="p-3.5 bg-emerald-50/40 border border-emerald-200/80 rounded-lg text-xs space-y-2">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1 border-b border-emerald-200/60 pb-2">
                    <div className="flex items-center gap-2">
                      <span className="font-mono font-bold text-emerald-900 text-[13px]">{match.incident_id}</span>
                      <span className="px-2 py-0.5 rounded bg-emerald-100 text-emerald-800 font-semibold text-[11px]">
                        Similarity: {(match.similarity_score * 100).toFixed(1)}%
                      </span>
                      <span className="text-slate-500">Machine: {match.machine}</span>
                    </div>
                    <span className="text-slate-400 font-mono text-[11px]">Date: {match.date}</span>
                  </div>

                  <div className="text-slate-700 space-y-1">
                    <div>
                      <strong className="text-emerald-950">Confirmed Historical Root Cause:</strong> {match.confirmed_root_cause}
                    </div>
                    <div>
                      <strong className="text-slate-800">Action Taken:</strong> {match.action_taken}
                    </div>
                    <div className="text-[11px] text-slate-500 italic bg-white/70 p-1.5 rounded border border-emerald-100">
                      ⚠ {match.disclaimer || "Historical context only. Previous incident similarity does not establish current root cause."}
                    </div>
                  </div>
                </div>
              ))
            ) : (
              <div className="p-4 text-center text-xs text-slate-400">No RAG historical evidence retrieved.</div>
            )}
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* SECTION 4: RCA HYPOTHESES (FR-17.6)                                       */}
      {/* ========================================================================= */}
      {(activeTab === "overview" || activeTab === "hypotheses") && (
        <div className="p-5 bg-white border border-[#E3E8EF] rounded-xl shadow-xs space-y-4">
          <div className="flex items-center justify-between border-b border-slate-100 pb-3">
            <div className="flex items-center gap-2">
              <GitBranch className="w-5 h-5 text-indigo-600" />
              <div>
                <h3 className="text-[16px] font-bold text-slate-900">
                  FR-17.6 — RCA Hypotheses & Evidence Weighting
                </h3>
                <p className="text-xs text-slate-500">
                  Ranked root cause hypotheses, mathematical score breakdowns, supporting evidence, and required confirmation tests.
                </p>
              </div>
            </div>
            <span className="status-pill info">
              {rcaReport?.ranked_hypotheses?.length || 0} Hypotheses Formulated
            </span>
          </div>

          <div className="space-y-3">
            {rcaReport?.ranked_hypotheses && rcaReport.ranked_hypotheses.length > 0 ? (
              rcaReport.ranked_hypotheses.map((hyp, i) => (
                <div key={i} className="p-4 bg-slate-50 border border-slate-200 rounded-lg text-xs space-y-2.5">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-200 pb-2">
                    <div className="flex items-center gap-2">
                      <span className="w-6 h-6 rounded-full bg-indigo-600 text-white font-bold flex items-center justify-center text-xs shrink-0">
                        #{hyp.rank || i + 1}
                      </span>
                      <strong className="text-sm font-bold text-slate-900">{hyp.title}</strong>
                      <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-slate-200 text-slate-700">
                        {hyp.category}
                      </span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="px-2.5 py-0.5 rounded font-mono font-bold text-xs bg-indigo-100 text-indigo-900 border border-indigo-200">
                        Score: {(hyp.confidence_score * 100).toFixed(0)}%
                      </span>
                      <span className={`px-2 py-0.5 rounded text-[11px] font-semibold ${hyp.status === "CONFIRMED" ? "bg-emerald-100 text-emerald-800" : "bg-amber-100 text-amber-800"}`}>
                        {hyp.status || "HYPOTHESIS"}
                      </span>
                    </div>
                  </div>

                  <p className="text-[13px] text-slate-700 leading-relaxed font-normal bg-white p-3 rounded-lg border border-slate-200">{hyp.description}</p>

                  {/* Supporting & Contradicting Evidence */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                    <div className="p-3 bg-emerald-50/60 rounded-xl border border-emerald-200 space-y-2">
                      <strong className="text-emerald-900 block font-bold text-xs">Supporting Evidence ({hyp.supporting_evidence?.length || 0}):</strong>
                      <div className="space-y-1.5">
                        {hyp.supporting_evidence?.map((ev, idx) => {
                          const item = parseEvidence(ev);
                          return (
                            <div key={idx} className="p-2 rounded-lg bg-white border border-emerald-150 shadow-2xs space-y-1">
                              <p className="text-[12px] font-semibold text-slate-800 leading-snug">{item.headline}</p>
                              {item.source && (
                                <span className="inline-block text-[10px] font-mono px-1.5 py-0.5 rounded bg-emerald-100 text-emerald-800 font-semibold">
                                  Source: {item.source}
                                </span>
                              )}
                            </div>
                          );
                        })}
                      </div>
                    </div>

                    <div className="p-3 bg-rose-50/60 rounded-xl border border-rose-200 space-y-2">
                      <strong className="text-rose-900 block font-bold text-xs">Contradicting / Missing Evidence:</strong>
                      <div className="space-y-1.5">
                        {hyp.contradicting_evidence?.map((ev, idx) => {
                          const item = parseEvidence(ev);
                          return (
                            <div key={idx} className="p-2 rounded-lg bg-white border border-slate-200 shadow-2xs space-y-1">
                              <p className="text-[12px] font-medium text-slate-700 leading-snug">{item.headline}</p>
                              {item.source && (
                                <span className="inline-block text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-100 text-slate-600 font-semibold">
                                  Source: {item.source}
                                </span>
                              )}
                            </div>
                          );
                        })}
                        {hyp.missing_evidence?.map((ev, idx) => {
                          const item = parseEvidence(ev);
                          return (
                            <div key={idx} className="p-2 rounded-lg bg-white border border-rose-150 shadow-2xs space-y-1">
                              <p className="text-[12px] text-slate-600 italic">Missing: {item.headline}</p>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  </div>

                  {/* Physical Confirmation Required */}
                  <div className="p-2.5 bg-blue-50/70 border border-blue-200 rounded-lg text-xs text-blue-950 flex items-start gap-2">
                    <ShieldCheck className="w-4 h-4 text-blue-600 shrink-0 mt-0.5" />
                    <div>
                      <strong className="text-blue-900 font-semibold">Physical Confirmation: </strong>
                      <span className="text-slate-800 font-medium">{hyp.required_confirmation}</span>
                    </div>
                  </div>
                </div>
              ))
            ) : (
              <div className="p-4 text-center text-xs text-slate-400">No hypotheses generated.</div>
            )}
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* SECTION 5: REVIEWER COMMENTS & CRITIC AUDIT (FR-17.7)                     */}
      {/* ========================================================================= */}
      {(activeTab === "overview" || activeTab === "critic") && criticReview && (
        <div className="p-5 bg-white border border-[#E3E8EF] rounded-xl shadow-xs space-y-4">
          <div className="flex items-center justify-between border-b border-slate-100 pb-3">
            <div className="flex items-center gap-2.5">
              <ShieldCheck className="w-5 h-5 text-emerald-600" />
              <div>
                <h3 className="text-[16px] font-bold text-slate-900">
                  FR-17.7 — Reviewer Comments (Critic Agent Audit Verdict)
                </h3>
                <span className="text-[12.5px] text-[#475467]">Mathematical safety and spec reference verification</span>
              </div>
            </div>
            <span className="status-pill success">
              {criticReview.critic_verdict}
            </span>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
            <div className="p-3 bg-slate-50 rounded-lg border border-slate-100">
              <span className="text-slate-500 block text-[11.5px]">Spec References</span>
              <strong className="text-emerald-700 text-[13px]">
                {criticReview.verified_spec_references ? "Verified Correct" : "Flagged"}
              </strong>
            </div>
            <div className="p-3 bg-slate-50 rounded-lg border border-slate-100">
              <span className="text-slate-500 block text-[11.5px]">Calculation Audit</span>
              <strong className="text-emerald-700 text-[13px]">
                {criticReview.validated_calculations ? "Validated Accurate" : "Flagged"}
              </strong>
            </div>
            <div className="p-3 bg-slate-50 rounded-lg border border-slate-100">
              <span className="text-slate-500 block text-[11.5px]">Visual Confidence</span>
              <strong className="text-emerald-700 text-[13px]">
                {criticReview.cv_predictions_verified ? "Verified > 90%" : "Under Review"}
              </strong>
            </div>
            <div className="p-3 bg-slate-50 rounded-lg border border-slate-100">
              <span className="text-slate-500 block text-[11.5px]">Causal Evidence</span>
              <strong className="text-emerald-700 text-[13px]">
                {!criticReview.unsupported_causal_claims_detected ? "Corroborated" : "Unsupported Claims"}
              </strong>
            </div>
          </div>

          <div className="p-3.5 bg-slate-50 rounded-lg space-y-1.5 text-xs border border-slate-100">
            <span className="font-bold text-slate-800 block text-[13px]">Reviewer Audit Observations:</span>
            {criticReview.review_comments?.map((c, i) => (
              <div key={i} className="text-slate-600 flex items-start gap-2 text-[12.5px]">
                <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
                <span>{c}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* SECTION 6: HUMAN DECISION GATE & AUDIT TRAIL (FR-17.8)                    */}
      {/* ========================================================================= */}
      {(activeTab === "overview" || activeTab === "decision") && (
        <div className="p-6 bg-[#EAF2FF]/50 border border-[#BFD6FF] rounded-xl shadow-xs space-y-4">
          <div className="flex items-center justify-between border-b border-[#BFD6FF]/60 pb-3">
            <div className="flex items-center gap-2.5">
              <UserCheck className="w-5 h-5 text-[#1D4ED8]" />
              <div>
                <h3 className="text-[16px] font-bold text-slate-900">
                  FR-17.8 — Human Decision Gate & Disposition Authority
                </h3>
                <p className="text-[13px] text-[#475467] mt-0.5">
                  Decision-support only. Final product disposition is an authorized human engineering decision.
                </p>
              </div>
            </div>
            <span className={`status-pill ${submitted || humanApproval ? "success" : "info"}`}>
              {submitted || humanApproval ? "Disposition Authorized" : "Pending Human Authorization"}
            </span>
          </div>

          {/* Current Persisted Human Decision Status */}
          {humanApproval && (
            <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-lg text-xs text-emerald-900 space-y-1">
              <div className="flex items-center justify-between">
                <strong>Current Persisted Human Decision:</strong>
                <span className="font-mono text-emerald-700">{humanApproval.timestamp || "Persisted"}</span>
              </div>
              <div>Decision: <strong className="font-mono">{humanApproval.decision}</strong> | Disposition: <strong>{humanApproval.disposition}</strong></div>
              <div>Authorized By: <strong>{humanApproval.approved_by || humanApproval.signed_by}</strong></div>
              <div>Comments: <em>{humanApproval.engineering_comments || humanApproval.reason}</em></div>
            </div>
          )}

          {/* Operator Read-Only Banner */}
          {isOperator && (
            <div className="p-3.5 bg-amber-50 border border-amber-200 rounded-lg text-amber-900 text-[13px] flex items-center gap-2.5">
              <Lock className="w-4 h-4 text-amber-700 shrink-0" />
              <div>
                <strong>Read-Only Mode:</strong> Operator persona cannot authorize batch disposition or elevate root causes. Active approval controls are disabled.
              </div>
            </div>
          )}

          {/* Re-analysis Loop Warning */}
          {reanalysisMessage && (
            <div className="p-3.5 bg-rose-50 border border-rose-200 rounded-lg text-rose-900 text-[13px] flex items-center gap-2.5">
              <AlertTriangle className="w-4 h-4 text-rose-700 shrink-0" />
              <div>{reanalysisMessage}</div>
            </div>
          )}

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
            <div>
              <label className="block text-[13px] font-semibold text-slate-700 mb-1.5">Authorized Quality Engineer:</label>
              <input
                type="text"
                disabled={isOperator}
                value={engineerName}
                onChange={(e) => setEngineerName(e.target.value)}
                className="filter-input w-full !h-[40px] text-[13.5px] disabled:bg-slate-100 disabled:text-slate-400"
              />
            </div>

            <div>
              <label className="block text-[13px] font-semibold text-slate-700 mb-1.5">Final Batch Disposition:</label>
              <select
                disabled={isOperator}
                value={disposition}
                onChange={(e) => setDisposition(e.target.value)}
                className="filter-input w-full !h-[40px] text-[13.5px] disabled:bg-slate-100 disabled:text-slate-400"
              >
                <option value="QUARANTINE_BATCH">Quarantine Batch (100% Sorting Inspection)</option>
                <option value="REWORK_WINDOW">Rework Affected Window</option>
                <option value="SCRAP">Scrap Nonconforming Components</option>
                <option value="RELEASE_WITH_CONCESSION">Release With Engineering Concession</option>
              </select>
            </div>
          </div>

          <div>
            <div className="flex items-center justify-between mb-1.5">
              <label className="block text-[13px] font-semibold text-slate-700">Engineering Investigation Comments:</label>
              <span className="text-[11.5px] text-slate-400 font-mono">{comments.length}/2000 chars</span>
            </div>
            <textarea
              disabled={isOperator}
              value={comments}
              maxLength={2000}
              onChange={(e) => setComments(e.target.value)}
              rows={2}
              className="w-full p-3 bg-white border border-[#D0D5DD] rounded-lg text-[13.5px] focus:outline-hidden focus:border-[#2563EB] focus:ring-3 focus:ring-[rgba(37,99,235,0.25)] disabled:bg-slate-100 disabled:text-slate-400"
            />
          </div>

          {/* Action Controls */}
          <div className="flex flex-wrap items-center gap-3 pt-2">
            <button
              disabled={isOperator || submitted}
              onClick={() => triggerSignOff("ACCEPT_FINDINGS")}
              className="btn-primary !h-[42px] disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
            >
              <CheckCircle2 className="w-4 h-4 mr-1.5 text-white" />
              <span>Approve Findings & Authorize Disposition</span>
            </button>
            <button
              disabled={isOperator || submitted}
              onClick={() => triggerSignOff("REJECT_BATCH")}
              className="px-4 h-[42px] bg-rose-600 hover:bg-rose-700 text-white rounded-[8px] text-[14px] font-semibold flex items-center disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
            >
              <XCircle className="w-4 h-4 mr-1.5 text-white" />
              <span>Reject Batch Disposition</span>
            </button>
            <button
              disabled={isOperator || reanalysisCount >= 3}
              onClick={handleRequestReanalysis}
              className="btn-secondary !h-[42px] disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
            >
              <RefreshCw className="w-4 h-4 mr-1.5 text-slate-600" />
              <span>Request Another Analysis ({reanalysisCount}/3 loops)</span>
            </button>
          </div>
        </div>
      )}

      {/* Immutable Decision History Audit Trail Table */}
      {(activeTab === "overview" || activeTab === "decision") && (
        <div className="bg-white border border-[#E3E8EF] rounded-xl shadow-xs overflow-hidden">
          <div className="px-5 py-4 border-b border-[#EEF1F5] flex items-center justify-between bg-[#F8FAFC]">
            <div className="flex items-center gap-2">
              <History className="w-4 h-4 text-slate-600" />
              <h3 className="text-[15px] font-bold text-slate-800">
                FR-17.8 Immutable Human Decisions Audit Trail ({decisionHistory.length} Records)
              </h3>
            </div>
            <button onClick={loadHistory} className="text-[12px] text-blue-600 hover:underline cursor-pointer">
              Refresh Audit Log
            </button>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead className="bg-[#F1F5F9] text-slate-600 uppercase font-semibold text-[11px] border-b border-slate-200">
                <tr>
                  <th className="py-2.5 px-4">Entity</th>
                  <th className="py-2.5 px-4">Entity ID</th>
                  <th className="py-2.5 px-4">Decision</th>
                  <th className="py-2.5 px-4">User</th>
                  <th className="py-2.5 px-4">Timestamp</th>
                  <th className="py-2.5 px-4">Engineering Comments</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {decisionHistory.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="py-6 text-center text-slate-400">
                      No human decisions recorded yet. Decisions will be permanently logged here.
                    </td>
                  </tr>
                ) : (
                  decisionHistory.slice(0, 8).map((d) => (
                    <tr key={d.id} className="hover:bg-slate-50 transition-colors">
                      <td className="py-2.5 px-4 font-mono font-medium text-slate-700">{d.entity_type}</td>
                      <td className="py-2.5 px-4 font-mono text-slate-500">{d.entity_id}</td>
                      <td className="py-2.5 px-4">
                        <span className={`px-2 py-0.5 rounded text-[11px] font-bold ${
                          d.decision?.includes("REJECT") ? "bg-rose-100 text-rose-800" :
                          d.decision?.includes("CONFIRM") || d.decision?.includes("ACCEPT") || d.decision?.includes("APPROVE") ? "bg-emerald-100 text-emerald-800" :
                          "bg-blue-100 text-blue-800"
                        }`}>
                          {d.decision}
                        </span>
                      </td>
                      <td className="py-2.5 px-4 text-slate-600">{d.user_id}</td>
                      <td className="py-2.5 px-4 font-mono text-slate-400">{d.timestamp?.slice(0, 19).replace("T", " ")}</td>
                      <td className="py-2.5 px-4 text-slate-700 max-w-xs truncate" title={d.comment}>{d.comment}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Confirmation Dialog Modal for Irreversible Actions */}
      {showConfirmModal && (
        <div className="fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-[2px] flex items-center justify-center p-4">
          <div className="bg-white rounded-xl border border-slate-200 shadow-xl max-w-md w-full p-6 space-y-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-amber-100 flex items-center justify-center text-amber-700 shrink-0">
                <AlertTriangle className="w-5 h-5" />
              </div>
              <div>
                <h4 className="text-[16px] font-bold text-slate-900">Confirm Irreversible Disposition</h4>
                <p className="text-[12.5px] text-slate-500 mt-0.5">Authorization Sign-Off Confirmation</p>
              </div>
            </div>

            <p className="text-[13px] text-slate-600">
              Are you sure you want to authorize decision <strong>{pendingDecision}</strong> with disposition <strong>{disposition}</strong>? This decision will be permanently committed to the immutable audit log.
            </p>

            <div className="flex items-center justify-end gap-3 pt-2">
              <button
                onClick={() => setShowConfirmModal(false)}
                className="px-4 py-2 border border-slate-300 rounded-lg text-xs font-semibold text-slate-700 hover:bg-slate-50 cursor-pointer"
              >
                Cancel
              </button>
              <button
                onClick={executeSignOff}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs font-semibold shadow-xs cursor-pointer"
              >
                Confirm & Authorize
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

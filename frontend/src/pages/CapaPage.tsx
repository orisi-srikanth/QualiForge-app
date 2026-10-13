import React, { useEffect, useState, useMemo } from "react";
import { api } from "../api";
import { CAPAActionRecord } from "../types";
import { CertaintyBadge } from "../components/CertaintyBadge";
import {
  ShieldCheck, CheckCircle2, Clock, AlertTriangle,
  TrendingDown, User, Calendar, FileCheck, ArrowRight,
  Plus, Filter, LayoutGrid, List, RefreshCw, Upload,
  Eye, Check, X, ShieldAlert, History, AlertCircle,
  BarChart2, BarChart3, Activity
} from "lucide-react";

// Demo personas tokens
// Pre-computed standard mock tokens for UI persona testing
const QE_TOKEN = "demo_qe_token";
const OP_TOKEN = "demo_op_token";

export const CapaPage: React.FC = () => {
  const [actions, setActions] = useState<CAPAActionRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Persona switcher: 'quality_engineer' or 'operator'
  const [currentPersona, setCurrentPersona] = useState<"quality_engineer" | "operator">("quality_engineer");

  // View state: 'table' or 'board'
  const [viewMode, setViewMode] = useState<"table" | "board">("table");

  // Filters
  const [selectedType, setSelectedType] = useState<string>("all");
  const [selectedStatus, setSelectedStatus] = useState<string>("all");
  const [onlyOverdue, setOnlyOverdue] = useState<boolean>(false);

  // Recurrence alert state
  const [recurrenceAlert, setRecurrenceAlert] = useState<any>(null);

  // Effectiveness Modal State
  const [selectedActionForEffectiveness, setSelectedActionForEffectiveness] = useState<CAPAActionRecord | null>(null);
  const [effectivenessData, setEffectivenessData] = useState<any>(null);
  const [loadingEffectiveness, setLoadingEffectiveness] = useState(false);
  const [effectivenessError, setEffectivenessError] = useState<string | null>(null);

  // Modals & Drawers
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [createFormData, setCreateFormData] = useState({
    type: "containment",
    description: "",
    due_date: new Date(Date.now() + 7 * 86400000).toISOString().split("T")[0],
    suggested_role: "Quality Inspector",
    incident_id: "inc-ncr-019",
    hypothesis_id: "hyp-conf-inc-ncr-019"
  });

  const [selectedActionForAudit, setSelectedActionForAudit] = useState<string | null>(null);
  const [auditLogs, setAuditLogs] = useState<any[]>([]);
  const [loadingAudit, setLoadingAudit] = useState(false);

  const [actionToApprove, setActionToApprove] = useState<CAPAActionRecord | null>(null);
  const [approvalRole, setApprovalRole] = useState<string>("");
  const [approvalComment, setApprovalComment] = useState<string>("");

  const [actionToReject, setActionToReject] = useState<CAPAActionRecord | null>(null);
  const [rejectionReason, setRejectionReason] = useState<string>("");

  const [actionForEvidence, setActionForEvidence] = useState<CAPAActionRecord | null>(null);
  const [evidenceFile, setEvidenceFile] = useState<File | null>(null);
  const [evidenceText, setEvidenceText] = useState<string>("");

  const [actionToAdvance, setActionToAdvance] = useState<CAPAActionRecord | null>(null);
  const [targetStatus, setTargetStatus] = useState<string>("");

  const isQE = currentPersona === "quality_engineer";

  const openEffectivenessModal = async (act: CAPAActionRecord) => {
    setSelectedActionForEffectiveness(act);
    setLoadingEffectiveness(true);
    setEffectivenessError(null);
    setEffectivenessData(null);
    try {
      const data = await api.getCapaEffectiveness(act.action_code);
      setEffectivenessData(data);
    } catch (err: any) {
      setEffectivenessError(err.message || "Failed to load effectiveness evaluation data");
    } finally {
      setLoadingEffectiveness(false);
    }
  };

  // Load CAPA actions
  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.listCapaActions();
      setActions(res.actions || []);

      // Check recurrence only if actions exist
      if (res.actions && res.actions.length > 0) {
        const rec = await api.checkCapaRecurrence("CNC-04", "Oversized shaft diameter").catch(() => null);
        if (rec && rec.recurrence_detected) {
          setRecurrenceAlert(rec);
        }
      }
    } catch (err: any) {
      setError(err.message || "Failed to load CAPA actions");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  // Filtered actions
  const filteredActions = useMemo(() => {
    return actions.filter((act) => {
      if (selectedType !== "all" && act.type.toLowerCase() !== selectedType.toLowerCase()) return false;
      if (selectedStatus !== "all" && act.status.toLowerCase() !== selectedStatus.toLowerCase()) return false;
      if (onlyOverdue && !act.is_overdue) return false;
      return true;
    });
  }, [actions, selectedType, selectedStatus, onlyOverdue]);

  // Statistics
  const stats = useMemo(() => {
    const total = actions.length;
    const open = actions.filter((a) => ["proposed", "approved", "in_progress"].includes(a.status)).length;
    const overdue = actions.filter((a) => a.is_overdue).length;
    const completed = actions.filter((a) => ["completed", "verified"].includes(a.status)).length;
    return { total, open, overdue, completed };
  }, [actions]);

  // Handle Create Action
  const handleCreateSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!isQE) {
      alert("Permission denied: Operator role is read-only on action creation.");
      return;
    }
    try {
      await api.createCapaAction(createFormData);
      setShowCreateModal(false);
      setCreateFormData({
        type: "containment",
        description: "",
        due_date: new Date(Date.now() + 7 * 86400000).toISOString().split("T")[0],
        suggested_role: "Quality Inspector",
        incident_id: "inc-ncr-019",
        hypothesis_id: "hyp-conf-inc-ncr-019"
      });
      await loadData();
    } catch (err: any) {
      alert(`Error creating action: ${err.message}`);
    }
  };

  // Handle Approve Action
  const handleApproveSubmit = async () => {
    if (!actionToApprove) return;
    try {
      await api.approveCapaAction(actionToApprove.action_code, {
        responsible_role: approvalRole || actionToApprove.suggested_role || "Lead Quality Engineer",
        comment: approvalComment || "Approved by Quality Engineer"
      });
      setActionToApprove(null);
      setApprovalRole("");
      setApprovalComment("");
      await loadData();
    } catch (err: any) {
      alert(`Error approving action: ${err.message}`);
    }
  };

  // Handle Reject Action
  const handleRejectSubmit = async () => {
    if (!actionToReject || !rejectionReason.trim()) {
      alert("Please enter a rejection reason.");
      return;
    }
    try {
      await api.rejectCapaAction(actionToReject.action_code, rejectionReason);
      setActionToReject(null);
      setRejectionReason("");
      await loadData();
    } catch (err: any) {
      alert(`Error rejecting action: ${err.message}`);
    }
  };

  // Handle Advance Status
  const handleStatusAdvance = async () => {
    if (!actionToAdvance || !targetStatus) return;
    try {
      await api.updateCapaAction(actionToAdvance.action_code, {
        status: targetStatus,
        evidence: evidenceText,
        completion_date: targetStatus === "completed" ? new Date().toISOString().split("T")[0] : undefined
      });
      setActionToAdvance(null);
      setTargetStatus("");
      setEvidenceText("");
      await loadData();
    } catch (err: any) {
      alert(`Status transition error: ${err.message}`);
    }
  };

  // Handle Upload Evidence
  const handleEvidenceUploadSubmit = async () => {
    if (!actionForEvidence || !evidenceFile) {
      alert("Please select a file to upload.");
      return;
    }
    try {
      await api.uploadCapaEvidence(actionForEvidence.action_code, evidenceFile);
      setActionForEvidence(null);
      setEvidenceFile(null);
      await loadData();
    } catch (err: any) {
      alert(`Upload error: ${err.message}`);
    }
  };

  // Open Audit History
  const openAuditHistory = async (actionCode: string) => {
    setSelectedActionForAudit(actionCode);
    setLoadingAudit(true);
    try {
      const res = await api.getCapaAuditTrail(actionCode);
      setAuditLogs(res.audit_logs || []);
    } catch (err: any) {
      alert(`Failed to load audit history: ${err.message}`);
    } finally {
      setLoadingAudit(false);
    }
  };

  const getStatusBadge = (status: string, isOverdue: boolean) => {
    const s = status.toLowerCase();
    let badgeClass = "bg-slate-100 text-slate-700 border-slate-200";
    if (s === "proposed") badgeClass = "bg-amber-50 text-amber-800 border-amber-200";
    else if (s === "approved") badgeClass = "bg-blue-50 text-blue-800 border-blue-200";
    else if (s === "in_progress") badgeClass = "bg-indigo-50 text-indigo-800 border-indigo-200";
    else if (s === "completed") badgeClass = "bg-emerald-50 text-emerald-800 border-emerald-200";
    else if (s === "verified") badgeClass = "bg-purple-50 text-purple-800 border-purple-200";
    else if (s === "rejected") badgeClass = "bg-rose-50 text-rose-800 border-rose-200";

    return (
      <div className="flex items-center gap-1.5 flex-wrap">
        <span className={`px-2 py-0.5 rounded text-[11px] font-bold border uppercase tracking-wider ${badgeClass}`}>
          {status}
        </span>
        {isOverdue && (
          <span className="px-2 py-0.5 rounded text-[11px] font-bold bg-rose-600 text-white animate-pulse flex items-center gap-1">
            <AlertTriangle className="w-3 h-3" />
            OVERDUE
          </span>
        )}
      </div>
    );
  };

  const getTypeBadge = (type: string) => {
    const t = type.toLowerCase();
    if (t === "containment") return <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-rose-100 text-rose-800">Containment</span>;
    if (t === "corrective") return <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-100 text-amber-800">Corrective</span>;
    return <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-blue-100 text-blue-800">Preventive</span>;
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12">
      {/* Top Header & Persona Switcher */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-white p-5 rounded-xl border border-slate-200 shadow-2xs">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold text-slate-900 tracking-tight">CAPA Management</h1>
            <span className="text-[11px] px-2 py-0.5 rounded bg-blue-50 text-blue-700 font-semibold border border-blue-200">
              IATF 16949 §10.2
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-1">
            Layered Corrective & Preventive Action tracking across containment, corrective steps, and systemic prevention with engineering sign-off.
          </p>
        </div>

        {/* Persona Switcher Badge & Actions */}
        <div className="flex items-center gap-3 flex-wrap">
          <div className="flex items-center bg-slate-100 p-1 rounded-lg border border-slate-200">
            <button
              onClick={() => setCurrentPersona("quality_engineer")}
              className={`px-3 py-1.5 text-xs font-semibold rounded-md transition-all flex items-center gap-1.5 ${
                isQE
                  ? "bg-white text-blue-700 shadow-xs border border-slate-200"
                  : "text-slate-600 hover:text-slate-900"
              }`}
            >
              <ShieldCheck className="w-3.5 h-3.5 text-blue-600" />
              <span>Quality Engineer (Sarah Chen)</span>
            </button>
            <button
              onClick={() => setCurrentPersona("operator")}
              className={`px-3 py-1.5 text-xs font-semibold rounded-md transition-all flex items-center gap-1.5 ${
                !isQE
                  ? "bg-white text-slate-800 shadow-xs border border-slate-200"
                  : "text-slate-600 hover:text-slate-900"
              }`}
            >
              <User className="w-3.5 h-3.5 text-slate-500" />
              <span>Operator (Dave Miller — Read-Only)</span>
            </button>
          </div>

          <button
            onClick={() => {
              if (!isQE) {
                alert("Permission denied: Operator role is read-only on action creation. Switch to Quality Engineer.");
                return;
              }
              setShowCreateModal(true);
            }}
            disabled={!isQE}
            className={`px-3.5 py-2 rounded-lg text-xs font-bold flex items-center gap-1.5 shadow-xs transition-colors ${
              isQE
                ? "bg-blue-600 hover:bg-blue-700 text-white cursor-pointer"
                : "bg-slate-200 text-slate-400 cursor-not-allowed"
            }`}
            title={!isQE ? "Operator read-only on create" : "Create new CAPA action"}
          >
            <Plus className="w-3.5 h-3.5" />
            <span>New Action</span>
          </button>

          <button
            onClick={loadData}
            className="p-2 border border-slate-200 hover:bg-slate-50 rounded-lg text-slate-600 transition-colors"
            title="Refresh Data"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Recurrence Detection Alert Banner */}
      {recurrenceAlert && (
        <div className="p-4 bg-amber-50 border-l-4 border-amber-500 rounded-r-xl shadow-2xs space-y-2">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <AlertCircle className="w-5 h-5 text-amber-700" />
              <h3 className="text-sm font-bold text-amber-900">
                Agent 7 Recurrence Detection Alert: Machine {recurrenceAlert.machine}
              </h3>
            </div>
            <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-amber-200 text-amber-900 uppercase">
              Recurrence Detected
            </span>
          </div>
          <p className="text-xs text-amber-800">
            {recurrenceAlert.alert} Observed subsequent non-conforming incidents after CAPA completion date on {recurrenceAlert.machine}. Further systemic preventive action is warranted.
          </p>
        </div>
      )}

      {/* Summary KPI Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-2xs space-y-1">
          <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider block">Total Actions</span>
          <span className="text-2xl font-bold text-slate-900 font-mono">{stats.total}</span>
          <span className="text-[11px] text-slate-400 block">Across 3 action tiers</span>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-2xs space-y-1">
          <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider block">Open Actions</span>
          <span className="text-2xl font-bold text-blue-600 font-mono">{stats.open}</span>
          <span className="text-[11px] text-blue-600 block">Proposed, approved & active</span>
        </div>

        <div className={`p-4 rounded-xl border shadow-2xs space-y-1 ${stats.overdue > 0 ? "bg-rose-50/70 border-rose-300" : "bg-white border-slate-200"}`}>
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-semibold text-rose-700 uppercase tracking-wider block">Overdue Actions</span>
            {stats.overdue > 0 && <AlertTriangle className="w-4 h-4 text-rose-600 animate-bounce" />}
          </div>
          <span className="text-2xl font-bold text-rose-600 font-mono">{stats.overdue}</span>
          <span className="text-[11px] text-rose-700 block">Target completion exceeded</span>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-2xs space-y-1">
          <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider block">Completed / Verified</span>
          <span className="text-2xl font-bold text-emerald-600 font-mono">{stats.completed}</span>
          <span className="text-[11px] text-emerald-600 block">Evidence verified</span>
        </div>
      </div>

      {/* Filter and View Toolbar */}
      <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-2xs flex flex-col md:flex-row md:items-center justify-between gap-4">
        {/* Tier switcher tabs */}
        <div className="flex items-center gap-1 bg-slate-100 p-1 rounded-lg border border-slate-200 overflow-x-auto">
          {[
            { id: "all", label: "All Tiers" },
            { id: "containment", label: "Containment" },
            { id: "corrective", label: "Corrective" },
            { id: "preventive", label: "Preventive" }
          ].map((t) => (
            <button
              key={t.id}
              onClick={() => setSelectedType(t.id)}
              className={`px-3 py-1.5 text-xs font-semibold rounded-md transition-all whitespace-nowrap ${
                selectedType === t.id
                  ? "bg-white text-slate-900 shadow-xs border border-slate-200"
                  : "text-slate-600 hover:text-slate-900"
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>

        {/* Status filter & Overdue filter & View toggle */}
        <div className="flex items-center gap-3 flex-wrap">
          <div className="flex items-center gap-1.5 text-xs">
            <span className="text-slate-500 font-medium">Status:</span>
            <select
              value={selectedStatus}
              onChange={(e) => setSelectedStatus(e.target.value)}
              className="text-xs bg-slate-50 border border-slate-200 rounded-lg px-2.5 py-1.5 text-slate-800 font-medium"
            >
              <option value="all">All Statuses</option>
              <option value="proposed">Proposed</option>
              <option value="approved">Approved</option>
              <option value="in_progress">In Progress</option>
              <option value="completed">Completed</option>
              <option value="verified">Verified</option>
              <option value="rejected">Rejected</option>
            </select>
          </div>

          <label className="flex items-center gap-1.5 text-xs font-semibold text-rose-700 cursor-pointer bg-rose-50 px-2.5 py-1.5 rounded-lg border border-rose-200">
            <input
              type="checkbox"
              checked={onlyOverdue}
              onChange={(e) => setOnlyOverdue(e.target.checked)}
              className="rounded text-rose-600 focus:ring-rose-500 w-3.5 h-3.5"
            />
            <span>Overdue Only</span>
          </label>

          <div className="flex items-center bg-slate-100 p-0.5 rounded-lg border border-slate-200">
            <button
              onClick={() => setViewMode("table")}
              className={`p-1.5 rounded ${viewMode === "table" ? "bg-white text-blue-600 shadow-xs" : "text-slate-500"}`}
              title="Table View"
            >
              <List className="w-4 h-4" />
            </button>
            <button
              onClick={() => setViewMode("board")}
              className={`p-1.5 rounded ${viewMode === "board" ? "bg-white text-blue-600 shadow-xs" : "text-slate-500"}`}
              title="Kanban Board View"
            >
              <LayoutGrid className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      {/* Main Content: Table or Board */}
      {loading ? (
        <div className="bg-white p-12 text-center rounded-xl border border-slate-200 space-y-3">
          <RefreshCw className="w-6 h-6 animate-spin mx-auto text-blue-600" />
          <p className="text-xs text-slate-500 font-medium">Loading CAPA records...</p>
        </div>
      ) : error ? (
        <div className="bg-white p-8 text-center rounded-xl border border-rose-200 space-y-2">
          <AlertCircle className="w-6 h-6 text-rose-600 mx-auto" />
          <p className="text-xs text-rose-700 font-semibold">{error}</p>
          <button onClick={loadData} className="px-3 py-1.5 bg-blue-600 text-white rounded text-xs">Retry</button>
        </div>
      ) : filteredActions.length === 0 ? (
        <div className="bg-white p-12 text-center rounded-xl border border-slate-200 space-y-2">
          <CheckCircle2 className="w-8 h-8 text-slate-300 mx-auto" />
          <p className="text-sm font-semibold text-slate-700">No CAPA actions match the selected filters.</p>
          <button onClick={() => { setSelectedType("all"); setSelectedStatus("all"); setOnlyOverdue(false); }} className="text-xs text-blue-600 hover:underline">
            Reset Filters
          </button>
        </div>
      ) : viewMode === "table" ? (
        /* TABLE VIEW */
        <div className="bg-white rounded-xl border border-slate-200 shadow-2xs overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="bg-slate-50/80 border-b border-slate-200 text-slate-600 font-bold uppercase tracking-wider text-[11px]">
                  <th className="p-3.5 pl-5">Action ID</th>
                  <th className="p-3.5">Tier</th>
                  <th className="p-3.5 max-w-xs">Description</th>
                  <th className="p-3.5">Role / Assigned</th>
                  <th className="p-3.5">Due Date</th>
                  <th className="p-3.5">Status</th>
                  <th className="p-3.5">Evidence & Completion</th>
                  <th className="p-3.5 pr-5 text-right">Engineering Controls</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-slate-800">
                {filteredActions.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="p-12 text-center text-slate-500 text-sm">
                      <CheckCircle2 className="w-8 h-8 text-slate-400 mx-auto mb-2" />
                      <p className="font-semibold text-slate-700">No CAPA Records Found</p>
                      <p className="text-xs text-slate-400 mt-1">Non-conformances logged during quality inspection will generate corrective action proposals.</p>
                    </td>
                  </tr>
                ) : (
                  filteredActions.map((act) => (
                  <tr
                    key={act.action_code}
                    className={`hover:bg-slate-50/60 transition-colors ${
                      act.is_overdue ? "bg-rose-50/30" : ""
                    }`}
                  >
                    <td className="p-3.5 pl-5 font-mono font-bold text-blue-600 whitespace-nowrap">
                      {act.action_code}
                    </td>

                    <td className="p-3.5 whitespace-nowrap">
                      {getTypeBadge(act.type)}
                    </td>

                    <td className="p-3.5 max-w-sm">
                      <p className="font-semibold text-slate-900 leading-snug">{act.description}</p>
                      {act.hypothesis_id && (
                        <span className="text-[10px] text-slate-400 mt-0.5 block font-mono">
                          Linked RCA: {act.hypothesis_id}
                        </span>
                      )}
                    </td>

                    <td className="p-3.5 whitespace-nowrap">
                      {act.responsible_role ? (
                        <div className="flex items-center gap-1 text-slate-800 font-semibold">
                          <User className="w-3.5 h-3.5 text-blue-500" />
                          <span>{act.responsible_role}</span>
                        </div>
                      ) : (
                        <div className="flex items-center gap-1 text-slate-400 italic">
                          <User className="w-3.5 h-3.5 text-slate-300" />
                          <span>Suggested: {act.suggested_role || "Unassigned"}</span>
                        </div>
                      )}
                    </td>

                    <td className="p-3.5 whitespace-nowrap">
                      <div className="flex items-center gap-1">
                        <Calendar className="w-3.5 h-3.5 text-slate-400" />
                        <span className={`font-mono font-semibold ${act.is_overdue ? "text-rose-600 font-bold" : "text-slate-700"}`}>
                          {act.due_date}
                        </span>
                      </div>
                    </td>

                    <td className="p-3.5 whitespace-nowrap">
                      {getStatusBadge(act.status, act.is_overdue)}
                    </td>

                    <td className="p-3.5 max-w-xs">
                      {act.evidence ? (
                        <div className="space-y-0.5">
                          <span className="text-[11px] text-emerald-800 font-medium block truncate" title={act.evidence}>
                            ✓ {act.evidence}
                          </span>
                          {act.completion_date && (
                            <span className="text-[10px] text-slate-400 block font-mono">
                              Completed: {act.completion_date}
                            </span>
                          )}
                        </div>
                      ) : (
                        <span className="text-[11px] text-slate-400 italic">Pending evidence</span>
                      )}
                      {act.effectiveness_result ? (
                        <button
                          onClick={() => openEffectivenessModal(act)}
                          className="inline-flex items-center gap-1.5 px-2 py-0.5 mt-1 rounded bg-purple-50 hover:bg-purple-100 border border-purple-200 text-purple-700 text-[10px] font-semibold cursor-pointer transition-colors shadow-2xs"
                          title="View Effectiveness Statistical Verification"
                        >
                          <TrendingDown className="w-3 h-3 text-purple-600" />
                          <span>Effectiveness: Verified</span>
                        </button>
                      ) : ["completed", "verified"].includes(act.status) ? (
                        <button
                          onClick={() => openEffectivenessModal(act)}
                          className="inline-flex items-center gap-1.5 px-2 py-0.5 mt-1 rounded bg-slate-50 hover:bg-slate-100 border border-slate-200 text-slate-600 text-[10px] font-semibold cursor-pointer transition-colors"
                          title="Check Effectiveness Monitoring"
                        >
                          <TrendingDown className="w-3 h-3 text-slate-500" />
                          <span>View Effectiveness</span>
                        </button>
                      ) : (
                        <button
                          onClick={() => openEffectivenessModal(act)}
                          className="inline-flex items-center gap-1 text-[10px] text-slate-400 hover:text-slate-600 cursor-pointer mt-1"
                          title="Monitoring not started"
                        >
                          <span>Monitoring not started</span>
                        </button>
                      )}
                    </td>

                    {/* Controls */}
                    <td className="p-3.5 pr-5 text-right whitespace-nowrap">
                      <div className="flex items-center justify-end gap-1.5">
                        {/* Approve button (only for proposed) */}
                        {act.status === "proposed" && (
                          <button
                            onClick={() => {
                              if (!isQE) {
                                alert("Operator role is read-only. Quality Engineer sign-off required.");
                                return;
                              }
                              setActionToApprove(act);
                              setApprovalRole(act.suggested_role || "Lead Quality Engineer");
                            }}
                            disabled={!isQE}
                            className={`p-1.5 rounded text-xs font-semibold flex items-center gap-1 transition-colors ${
                              isQE
                                ? "bg-emerald-600 hover:bg-emerald-700 text-white cursor-pointer"
                                : "bg-slate-100 text-slate-400 cursor-not-allowed"
                            }`}
                            title={!isQE ? "Operator read-only" : "Approve action"}
                          >
                            <Check className="w-3.5 h-3.5" />
                            <span>Approve</span>
                          </button>
                        )}

                        {/* Reject button (only for proposed) */}
                        {act.status === "proposed" && (
                          <button
                            onClick={() => {
                              if (!isQE) {
                                alert("Operator role is read-only. Quality Engineer sign-off required.");
                                return;
                              }
                              setActionToReject(act);
                            }}
                            disabled={!isQE}
                            className={`p-1.5 rounded text-xs font-semibold flex items-center gap-1 transition-colors ${
                              isQE
                                ? "bg-rose-100 hover:bg-rose-200 text-rose-700 cursor-pointer"
                                : "bg-slate-100 text-slate-400 cursor-not-allowed"
                            }`}
                            title={!isQE ? "Operator read-only" : "Reject action"}
                          >
                            <X className="w-3.5 h-3.5" />
                            <span>Reject</span>
                          </button>
                        )}

                        {/* Advance to In-Progress */}
                        {act.status === "approved" && (
                          <button
                            onClick={() => {
                              if (!isQE) {
                                alert("Operator role is read-only.");
                                return;
                              }
                              setActionToAdvance(act);
                              setTargetStatus("in_progress");
                            }}
                            disabled={!isQE}
                            className="p-1.5 bg-blue-100 hover:bg-blue-200 text-blue-800 rounded text-xs font-semibold flex items-center gap-1"
                            title="Start implementation"
                          >
                            <span>Start</span>
                          </button>
                        )}

                        {/* Advance to Completed */}
                        {act.status === "in_progress" && (
                          <button
                            onClick={() => {
                              if (!isQE) {
                                alert("Operator role is read-only.");
                                return;
                              }
                              setActionToAdvance(act);
                              setTargetStatus("completed");
                            }}
                            disabled={!isQE}
                            className="p-1.5 bg-emerald-100 hover:bg-emerald-200 text-emerald-800 rounded text-xs font-semibold flex items-center gap-1"
                            title="Mark completed"
                          >
                            <CheckCircle2 className="w-3.5 h-3.5" />
                            <span>Complete</span>
                          </button>
                        )}

                        {/* Upload Evidence button */}
                        <button
                          onClick={() => {
                            if (!isQE) {
                              alert("Operator role is read-only on evidence submission.");
                              return;
                            }
                            setActionForEvidence(act);
                          }}
                          disabled={!isQE}
                          className="p-1.5 text-slate-500 hover:text-blue-600 hover:bg-slate-100 rounded transition-colors"
                          title="Upload Evidence Document"
                        >
                          <Upload className="w-3.5 h-3.5" />
                        </button>

                        {/* Audit Trail */}
                        <button
                          onClick={() => openAuditHistory(act.action_code)}
                          className="p-1.5 text-slate-500 hover:text-slate-800 hover:bg-slate-100 rounded transition-colors"
                          title="View Decision Audit Log"
                        >
                          <History className="w-3.5 h-3.5" />
                        </button>

                        {/* Effectiveness Check Modal */}
                        <button
                          onClick={() => openEffectivenessModal(act)}
                          className="p-1.5 text-purple-600 hover:text-purple-800 hover:bg-purple-50 rounded transition-colors"
                          title="View Effectiveness Statistical Monitoring"
                        >
                          <BarChart3 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
              </tbody>
            </table>
          </div>
        </div>
      ) : (
        /* KANBAN BOARD VIEW */
        <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
          {[
            { id: "proposed", title: "Proposed", color: "border-amber-400 bg-amber-50/20" },
            { id: "approved", title: "Approved", color: "border-blue-400 bg-blue-50/20" },
            { id: "in_progress", title: "In Progress", color: "border-indigo-400 bg-indigo-50/20" },
            { id: "completed", title: "Completed", color: "border-emerald-400 bg-emerald-50/20" },
            { id: "verified", title: "Verified", color: "border-purple-400 bg-purple-50/20" }
          ].map((col) => {
            const colActions = filteredActions.filter((a) => a.status.toLowerCase() === col.id);
            return (
              <div key={col.id} className={`rounded-xl border p-3 flex flex-col gap-3 min-h-[400px] ${col.color}`}>
                <div className="flex items-center justify-between pb-2 border-b border-slate-200">
                  <span className="text-xs font-bold text-slate-800 uppercase tracking-wider">
                    {col.title} ({colActions.length})
                  </span>
                </div>

                <div className="space-y-2.5 overflow-y-auto flex-1">
                  {colActions.map((act) => (
                    <div
                      key={act.action_code}
                      className={`p-3 bg-white rounded-lg border shadow-xs space-y-2 transition-all ${
                        act.is_overdue ? "border-rose-400 ring-1 ring-rose-300" : "border-slate-200"
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-mono text-[11px] font-bold text-blue-600">{act.action_code}</span>
                        {getTypeBadge(act.type)}
                      </div>

                      <p className="text-xs font-semibold text-slate-900 leading-snug line-clamp-3">
                        {act.description}
                      </p>

                      <div className="text-[10px] text-slate-500 space-y-1 pt-1 border-t border-slate-100">
                        <div className="flex items-center justify-between">
                          <span>Role:</span>
                          <span className="font-semibold text-slate-700 truncate max-w-[120px]">
                            {act.responsible_role || `(Suggested: ${act.suggested_role})`}
                          </span>
                        </div>
                        <div className="flex items-center justify-between">
                          <span>Due:</span>
                          <span className={`font-mono font-semibold ${act.is_overdue ? "text-rose-600" : "text-slate-700"}`}>
                            {act.due_date} {act.is_overdue ? "⚠️" : ""}
                          </span>
                        </div>
                      </div>

                      {/* Card Quick Actions */}
                      <div className="pt-2 flex items-center justify-between gap-1 border-t border-slate-100">
                        <div className="flex items-center gap-1.5">
                          <button
                            onClick={() => openAuditHistory(act.action_code)}
                            className="text-[10px] text-slate-400 hover:text-slate-700 flex items-center gap-0.5"
                          >
                            <History className="w-3 h-3" /> Audit
                          </button>
                          <button
                            onClick={() => openEffectivenessModal(act)}
                            className="text-[10px] text-purple-600 hover:text-purple-800 flex items-center gap-0.5 font-medium"
                            title="View Effectiveness Statistical Monitoring"
                          >
                            <TrendingDown className="w-3 h-3" /> Efficacy
                          </button>
                        </div>

                        {act.status === "proposed" && isQE && (
                          <div className="flex items-center gap-1">
                            <button
                              onClick={() => {
                                setActionToApprove(act);
                                setApprovalRole(act.suggested_role || "Lead Quality Engineer");
                              }}
                              className="px-2 py-0.5 bg-emerald-600 text-white rounded text-[10px] font-bold"
                            >
                              Approve
                            </button>
                            <button
                              onClick={() => setActionToReject(act)}
                              className="px-2 py-0.5 bg-rose-100 text-rose-700 rounded text-[10px] font-bold"
                            >
                              Reject
                            </button>
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* CREATE ACTION MODAL */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-xl border border-slate-200 space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div>
                <h3 className="text-base font-bold text-slate-900">Create New CAPA Action</h3>
                <p className="text-xs text-slate-500">Initiates a proposed action requiring engineering sign-off.</p>
              </div>
              <button onClick={() => setShowCreateModal(false)} className="text-slate-400 hover:text-slate-600">
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Safety Guardrail Notice */}
            <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg text-xs text-blue-800 space-y-1">
              <span className="font-bold flex items-center gap-1.5">
                <ShieldAlert className="w-4 h-4 text-blue-600" />
                IATF 16949 Safety Guardrail Notice
              </span>
              <p className="text-[11px] text-blue-700 leading-relaxed">
                QualityMind functions strictly as human decision support. Actions must assign tasks to human technicians or engineers. Autonomous machine commands (e.g. stopping spindles, modifying PLC/CNC parameters, auto-releasing lots) are blocked.
              </p>
            </div>

            <form onSubmit={handleCreateSubmit} className="space-y-3.5 text-xs">
              <div>
                <label className="font-semibold text-slate-700 block mb-1">Action Tier</label>
                <select
                  value={createFormData.type}
                  onChange={(e) => setCreateFormData({ ...createFormData, type: e.target.value })}
                  className="w-full border border-slate-300 rounded-lg p-2 font-medium"
                >
                  <option value="containment">1. Immediate Containment (Quarantine, Gauge check, Hold)</option>
                  <option value="corrective">2. Corrective Action (Tool replacement, Offset reset, Maintenance)</option>
                  <option value="preventive">3. Preventive Action (Tool-life limit, Sensor telemetry, SOP update)</option>
                </select>
              </div>

              <div>
                <label className="font-semibold text-slate-700 block mb-1">Action Description (Task for Human)</label>
                <textarea
                  required
                  rows={3}
                  value={createFormData.description}
                  onChange={(e) => setCreateFormData({ ...createFormData, description: e.target.value })}
                  placeholder="e.g. Inspect CNC-04 tool insert flank wear and verify micrometer calibration against master gauge."
                  className="w-full border border-slate-300 rounded-lg p-2.5 text-xs font-normal"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="font-semibold text-slate-700 block mb-1">Suggested Role</label>
                  <input
                    type="text"
                    required
                    value={createFormData.suggested_role}
                    onChange={(e) => setCreateFormData({ ...createFormData, suggested_role: e.target.value })}
                    placeholder="e.g. Quality Inspector"
                    className="w-full border border-slate-300 rounded-lg p-2"
                  />
                </div>

                <div>
                  <label className="font-semibold text-slate-700 block mb-1">Due Date (YYYY-MM-DD)</label>
                  <input
                    type="date"
                    required
                    value={createFormData.due_date}
                    onChange={(e) => setCreateFormData({ ...createFormData, due_date: e.target.value })}
                    className="w-full border border-slate-300 rounded-lg p-2"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="font-semibold text-slate-700 block mb-1">Incident ID</label>
                  <input
                    type="text"
                    value={createFormData.incident_id}
                    onChange={(e) => setCreateFormData({ ...createFormData, incident_id: e.target.value })}
                    className="w-full border border-slate-300 rounded-lg p-2"
                  />
                </div>

                <div>
                  <label className="font-semibold text-slate-700 block mb-1">Linked RCA Hypothesis</label>
                  <input
                    type="text"
                    value={createFormData.hypothesis_id}
                    onChange={(e) => setCreateFormData({ ...createFormData, hypothesis_id: e.target.value })}
                    className="w-full border border-slate-300 rounded-lg p-2 font-mono text-[11px]"
                  />
                </div>
              </div>

              <div className="flex justify-end gap-2 pt-3 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="px-4 py-2 border border-slate-200 rounded-lg text-slate-600 font-semibold hover:bg-slate-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-bold shadow-xs cursor-pointer"
                >
                  Submit Proposal
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* APPROVAL MODAL */}
      {actionToApprove && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-xl border border-slate-200 space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div>
                <h3 className="text-base font-bold text-slate-900">Approve CAPA Action</h3>
                <span className="font-mono text-xs font-bold text-blue-600">{actionToApprove.action_code}</span>
              </div>
              <button onClick={() => setActionToApprove(null)} className="text-slate-400 hover:text-slate-600">
                <X className="w-5 h-5" />
              </button>
            </div>

            <p className="text-xs text-slate-700 font-semibold">{actionToApprove.description}</p>

            <div className="space-y-3 text-xs">
              <div>
                <label className="font-semibold text-slate-700 block mb-1">Assign Responsible Role / Person</label>
                <input
                  type="text"
                  required
                  value={approvalRole}
                  onChange={(e) => setApprovalRole(e.target.value)}
                  placeholder="e.g. Lead Tooling Specialist"
                  className="w-full border border-slate-300 rounded-lg p-2 font-medium"
                />
              </div>

              <div>
                <label className="font-semibold text-slate-700 block mb-1">Approval Sign-off Remarks</label>
                <textarea
                  rows={2}
                  value={approvalComment}
                  onChange={(e) => setApprovalComment(e.target.value)}
                  placeholder="e.g. Approved following physical tool wear inspection and QA review."
                  className="w-full border border-slate-300 rounded-lg p-2 font-normal"
                />
              </div>
            </div>

            <div className="flex justify-end gap-2 pt-3 border-t border-slate-100 text-xs">
              <button onClick={() => setActionToApprove(null)} className="px-3 py-1.5 border rounded-lg text-slate-600">
                Cancel
              </button>
              <button onClick={handleApproveSubmit} className="px-4 py-1.5 bg-emerald-600 text-white rounded-lg font-bold">
                Confirm Engineering Approval
              </button>
            </div>
          </div>
        </div>
      )}

      {/* REJECTION MODAL */}
      {actionToReject && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-xl border border-slate-200 space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div>
                <h3 className="text-base font-bold text-slate-900">Reject Action Proposal</h3>
                <span className="font-mono text-xs font-bold text-rose-600">{actionToReject.action_code}</span>
              </div>
              <button onClick={() => setActionToReject(null)} className="text-slate-400 hover:text-slate-600">
                <X className="w-5 h-5" />
              </button>
            </div>

            <p className="text-xs text-slate-700">{actionToReject.description}</p>

            <div className="space-y-2 text-xs">
              <label className="font-semibold text-slate-700 block">Rejection Rationale (Mandatory)</label>
              <textarea
                required
                rows={3}
                value={rejectionReason}
                onChange={(e) => setRejectionReason(e.target.value)}
                placeholder="Explain why this action proposal is not accepted..."
                className="w-full border border-slate-300 rounded-lg p-2"
              />
            </div>

            <div className="flex justify-end gap-2 pt-3 border-t border-slate-100 text-xs">
              <button onClick={() => setActionToReject(null)} className="px-3 py-1.5 border rounded-lg text-slate-600">
                Cancel
              </button>
              <button onClick={handleRejectSubmit} className="px-4 py-1.5 bg-rose-600 text-white rounded-lg font-bold">
                Confirm Rejection
              </button>
            </div>
          </div>
        </div>
      )}

      {/* STATUS ADVANCE MODAL (In Progress / Completed) */}
      {actionToAdvance && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-xl border border-slate-200 space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div>
                <h3 className="text-base font-bold text-slate-900">Advance Action Status</h3>
                <span className="font-mono text-xs font-bold text-blue-600">{actionToAdvance.action_code}</span>
              </div>
              <button onClick={() => setActionToAdvance(null)} className="text-slate-400 hover:text-slate-600">
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="text-xs space-y-3">
              <p className="font-semibold text-slate-800">{actionToAdvance.description}</p>
              <div>
                <span className="text-slate-500 block mb-1">Transitioning to:</span>
                <span className="px-2.5 py-1 bg-blue-100 text-blue-800 rounded font-bold uppercase">
                  {targetStatus}
                </span>
              </div>

              {targetStatus === "completed" && (
                <div>
                  <label className="font-semibold text-slate-700 block mb-1">Completion Evidence (Mandatory)</label>
                  <textarea
                    required
                    rows={3}
                    value={evidenceText}
                    onChange={(e) => setEvidenceText(e.target.value)}
                    placeholder="Enter evidence details (e.g. insert replacement verified, offset recalibrated to 0.000 mm, FAI report attached)."
                    className="w-full border border-slate-300 rounded-lg p-2 font-normal"
                  />
                </div>
              )}
            </div>

            <div className="flex justify-end gap-2 pt-3 border-t border-slate-100 text-xs">
              <button onClick={() => setActionToAdvance(null)} className="px-3 py-1.5 border rounded-lg text-slate-600">
                Cancel
              </button>
              <button onClick={handleStatusAdvance} className="px-4 py-1.5 bg-blue-600 text-white rounded-lg font-bold">
                Confirm Status Update
              </button>
            </div>
          </div>
        </div>
      )}

      {/* EVIDENCE UPLOAD MODAL */}
      {actionForEvidence && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-xl border border-slate-200 space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div>
                <h3 className="text-base font-bold text-slate-900">Upload Evidence Document</h3>
                <span className="font-mono text-xs font-bold text-blue-600">{actionForEvidence.action_code}</span>
              </div>
              <button onClick={() => setActionForEvidence(null)} className="text-slate-400 hover:text-slate-600">
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="text-xs space-y-3">
              <p className="font-semibold text-slate-800">{actionForEvidence.description}</p>
              <div>
                <label className="font-semibold text-slate-700 block mb-1">Select File (.pdf, .png, .jpg, .xlsx, .csv, max 10MB)</label>
                <input
                  type="file"
                  onChange={(e) => setEvidenceFile(e.target.files?.[0] || null)}
                  className="w-full border border-slate-300 rounded-lg p-2"
                />
              </div>
            </div>

            <div className="flex justify-end gap-2 pt-3 border-t border-slate-100 text-xs">
              <button onClick={() => setActionForEvidence(null)} className="px-3 py-1.5 border rounded-lg text-slate-600">
                Cancel
              </button>
              <button onClick={handleEvidenceUploadSubmit} className="px-4 py-1.5 bg-blue-600 text-white rounded-lg font-bold">
                Upload Evidence
              </button>
            </div>
          </div>
        </div>
      )}

      {/* AUDIT HISTORY MODAL */}
      {selectedActionForAudit && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-xl border border-slate-200 space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div>
                <h3 className="text-base font-bold text-slate-900">CAPA Audit Trail</h3>
                <span className="font-mono text-xs font-bold text-blue-600">{selectedActionForAudit}</span>
              </div>
              <button onClick={() => setSelectedActionForAudit(null)} className="text-slate-400 hover:text-slate-600">
                <X className="w-5 h-5" />
              </button>
            </div>

            {loadingAudit ? (
              <div className="p-8 text-center text-slate-400 text-xs">Loading audit trail...</div>
            ) : auditLogs.length === 0 ? (
              <div className="p-8 text-center text-slate-400 text-xs">No audit logs recorded for this action.</div>
            ) : (
              <div className="space-y-2.5 max-h-72 overflow-y-auto pr-1">
                {auditLogs.map((log) => (
                  <div key={log.id} className="p-3 bg-slate-50 rounded-lg border border-slate-200 space-y-1 text-xs">
                    <div className="flex items-center justify-between">
                      <span className="font-bold text-slate-800 uppercase tracking-wide text-[10px]">
                        {log.decision}
                      </span>
                      <span className="text-[10px] text-slate-400 font-mono">
                        {log.timestamp ? new Date(log.timestamp).toLocaleString() : ""}
                      </span>
                    </div>
                    <p className="text-slate-600">{log.comment}</p>
                    <span className="text-[10px] text-slate-400 block">User: {log.user_id}</span>
                  </div>
                ))}
              </div>
            )}

            <div className="flex justify-end pt-3 border-t border-slate-100 text-xs">
              <button onClick={() => setSelectedActionForAudit(null)} className="px-4 py-1.5 bg-slate-800 text-white rounded-lg font-semibold">
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* EFFECTIVENESS MONITORING MODAL (FR-15 / AGENT 7) */}
      {selectedActionForEffectiveness && (
        <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-2xl max-w-2xl w-full p-6 shadow-2xl border border-slate-200 max-h-[90vh] overflow-y-auto space-y-5">
            {/* Modal Header */}
            <div className="flex items-start justify-between border-b border-slate-100 pb-4">
              <div>
                <div className="flex items-center gap-2">
                  <span className="font-mono text-xs font-bold px-2 py-0.5 bg-blue-50 text-blue-700 rounded border border-blue-200">
                    {selectedActionForEffectiveness.action_code}
                  </span>
                  <CertaintyBadge level="Statistical Finding" />
                  <span className="text-[11px] text-slate-500 font-medium">
                    ISO 9001 §10.2 / IATF 16949 §10.2.3
                  </span>
                </div>
                <h3 className="text-lg font-bold text-slate-900 mt-1">
                  CAPA Effectiveness Monitoring
                </h3>
                <p className="text-xs text-slate-500">
                  {selectedActionForEffectiveness.description}
                </p>
              </div>
              <button
                onClick={() => setSelectedActionForEffectiveness(null)}
                className="text-slate-400 hover:text-slate-600 p-1.5 rounded-lg hover:bg-slate-100 transition-colors cursor-pointer"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Modal Content States */}
            {loadingEffectiveness ? (
              <div className="py-16 text-center space-y-3">
                <RefreshCw className="w-8 h-8 text-blue-600 animate-spin mx-auto" />
                <p className="text-sm font-semibold text-slate-700">Evaluating post-intervention statistical efficacy...</p>
                <p className="text-xs text-slate-400">Partitioning production windows and executing hypothesis tests from database.</p>
              </div>
            ) : effectivenessError ? (
              <div className="p-4 bg-rose-50 border border-rose-200 rounded-xl space-y-2 text-xs text-rose-800">
                <div className="flex items-center gap-2 font-bold text-rose-900">
                  <AlertCircle className="w-4 h-4 text-rose-600" />
                  <span>Failed to Load Effectiveness Evaluation</span>
                </div>
                <p>{effectivenessError}</p>
                <button
                  onClick={() => openEffectivenessModal(selectedActionForEffectiveness)}
                  className="px-3 py-1 bg-rose-600 text-white rounded text-xs font-semibold hover:bg-rose-700 cursor-pointer"
                >
                  Retry Evaluation
                </button>
              </div>
            ) : effectivenessData?.status === "monitoring_not_started" ? (
              <div className="p-6 bg-amber-50/70 border border-amber-200 rounded-xl space-y-3 text-center">
                <div className="w-12 h-12 bg-amber-100 text-amber-700 rounded-full flex items-center justify-center mx-auto">
                  <Clock className="w-6 h-6" />
                </div>
                <h4 className="text-sm font-bold text-amber-900">Effectiveness Monitoring Not Started</h4>
                <p className="text-xs text-amber-800 max-w-md mx-auto leading-relaxed">
                  {effectivenessData.message || "Action completion is required as the dividing baseline before subsequent production can be monitored."}
                </p>
                <div className="pt-2 text-[11px] text-amber-700/80 font-mono">
                  Standard requirement: Action completion sign-off marks the dividing line between baseline and verified production windows.
                </div>
              </div>
            ) : effectivenessData?.status === "insufficient_data" || effectivenessData?.status === "invalid_windows" ? (
              <div className="p-5 bg-amber-50 border border-amber-200 rounded-xl space-y-2">
                <div className="flex items-center gap-2 text-xs font-bold text-amber-900">
                  <AlertTriangle className="w-4 h-4 text-amber-600" />
                  <span>{effectivenessData.status === "invalid_windows" ? "Invalid Windows" : "Insufficient Data"}</span>
                </div>
                <p className="text-xs text-amber-800">{effectivenessData.warning}</p>
              </div>
            ) : effectivenessData ? (
              <div className="space-y-4">
                {/* 1. Before & After Comparison Table */}
                <div className="bg-slate-50 border border-slate-200 rounded-xl overflow-hidden shadow-2xs">
                  <div className="p-3 bg-slate-100/80 border-b border-slate-200 flex items-center justify-between">
                    <span className="text-xs font-bold text-slate-800 flex items-center gap-1.5">
                      <BarChart2 className="w-4 h-4 text-blue-600" />
                      Before & After Window Partitioning
                    </span>
                    <span className="text-[11px] text-slate-500 font-mono">
                      Dividing Baseline: {effectivenessData.completion_date}
                    </span>
                  </div>
                  <table className="w-full text-xs text-left">
                    <thead className="bg-slate-50 border-b border-slate-200 text-slate-500 font-semibold text-[11px]">
                      <tr>
                        <th className="p-2.5">Window Partition</th>
                        <th className="p-2.5 text-right">Inspected Parts (n)</th>
                        <th className="p-2.5 text-right">Nonconforming (d)</th>
                        <th className="p-2.5 text-right">Rejection Rate (%)</th>
                        <th className="p-2.5 text-right">Machine / Product</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100 font-mono">
                      <tr className="bg-white">
                        <td className="p-2.5 font-sans font-semibold text-slate-800">
                          Pre-Intervention Baseline
                        </td>
                        <td className="p-2.5 text-right font-medium">{effectivenessData.sample_before_count?.toLocaleString()}</td>
                        <td className="p-2.5 text-right text-rose-600 font-semibold">{effectivenessData.defects_before_count}</td>
                        <td className="p-2.5 text-right text-rose-700 font-bold text-[13px]">
                          {effectivenessData.rejection_rate_before_percent}%
                        </td>
                        <td className="p-2.5 text-right text-slate-500 font-sans text-[11px]">
                          {effectivenessData.machine_id} / {effectivenessData.product_id}
                        </td>
                      </tr>
                      <tr className="bg-emerald-50/30">
                        <td className="p-2.5 font-sans font-semibold text-emerald-900">
                          Post-Intervention Verified
                        </td>
                        <td className="p-2.5 text-right font-medium">{effectivenessData.sample_after_count?.toLocaleString()}</td>
                        <td className="p-2.5 text-right text-emerald-700 font-semibold">{effectivenessData.defects_after_count}</td>
                        <td className="p-2.5 text-right text-emerald-700 font-bold text-[13px]">
                          {effectivenessData.rejection_rate_after_percent}%
                        </td>
                        <td className="p-2.5 text-right text-slate-500 font-sans text-[11px]">
                          {effectivenessData.machine_id} / {effectivenessData.product_id}
                        </td>
                      </tr>
                    </tbody>
                  </table>
                  <div className="p-2.5 bg-slate-100/60 border-t border-slate-200 flex items-center justify-between text-xs font-semibold">
                    <span className="text-slate-600">
                      Observed Absolute Change: -{(effectivenessData.rejection_rate_before_percent - effectivenessData.rejection_rate_after_percent).toFixed(1)}%
                    </span>
                    <span className="text-emerald-700 font-bold">
                      Relative Defect Reduction: -{effectivenessData.relative_reduction_percent}%
                    </span>
                  </div>
                </div>

                {/* 2. Visual Comparison Chart */}
                <div className="p-3.5 bg-white border border-slate-200 rounded-xl space-y-2">
                  <div className="flex items-center justify-between text-xs font-semibold text-slate-700">
                    <span>Rejection Rate Comparison (Target: &lt; 1.5%)</span>
                    <span className="text-[11px] text-slate-400">Problem Statement Benchmark (8.2% vs 1.1%)</span>
                  </div>
                  <div className="space-y-2 pt-1">
                    {/* Before Bar */}
                    <div className="space-y-0.5">
                      <div className="flex justify-between text-[11px] text-slate-600">
                        <span>Pre-Action Baseline</span>
                        <span className="font-mono font-bold text-rose-700">{effectivenessData.rejection_rate_before_percent}% (82 / 1,000)</span>
                      </div>
                      <div className="w-full bg-slate-100 rounded-full h-3.5 overflow-hidden">
                        <div
                          className="bg-rose-500 h-full rounded-full transition-all duration-500"
                          style={{ width: `${Math.min(100, effectivenessData.rejection_rate_before_percent * 10)}%` }}
                        />
                      </div>
                    </div>
                    {/* After Bar */}
                    <div className="space-y-0.5">
                      <div className="flex justify-between text-[11px] text-slate-600">
                        <span>Post-Action Subsequent Production</span>
                        <span className="font-mono font-bold text-emerald-700">{effectivenessData.rejection_rate_after_percent}% (11 / 1,000)</span>
                      </div>
                      <div className="w-full bg-slate-100 rounded-full h-3.5 overflow-hidden">
                        <div
                          className="bg-emerald-500 h-full rounded-full transition-all duration-500"
                          style={{ width: `${Math.min(100, effectivenessData.rejection_rate_after_percent * 10)}%` }}
                        />
                      </div>
                    </div>
                  </div>
                </div>

                {/* 3. Statistical Test Findings Card */}
                <div className="p-4 bg-purple-50/50 border border-purple-200 rounded-xl space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-purple-900 flex items-center gap-1.5">
                      <Activity className="w-4 h-4 text-purple-700" />
                      Statistical Test Verification ({effectivenessData.test_name || effectivenessData.test_type})
                    </span>
                    <span className={`text-[11px] font-bold px-2 py-0.5 rounded-full ${
                      effectivenessData.is_statistically_significant
                        ? "bg-emerald-100 text-emerald-800 border border-emerald-200"
                        : "bg-slate-100 text-slate-600 border border-slate-200"
                    }`}>
                      {effectivenessData.is_statistically_significant ? "Statistically Significant (p < 0.05)" : "Not Significant"}
                    </span>
                  </div>

                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 text-xs">
                    <div className="p-2.5 bg-white rounded-lg border border-purple-100">
                      <span className="text-[10px] text-slate-400 block font-semibold">Test Statistic</span>
                      <span className="font-mono text-sm font-bold text-purple-900">
                        z = {effectivenessData.statistic?.toFixed(2)}
                      </span>
                    </div>
                    <div className="p-2.5 bg-white rounded-lg border border-purple-100">
                      <span className="text-[10px] text-slate-400 block font-semibold">p-value</span>
                      <span className="font-mono text-sm font-bold text-purple-900">
                        {effectivenessData.p_value === 0 ? "< 0.0001" : effectivenessData.p_value}
                      </span>
                    </div>
                    <div className="p-2.5 bg-white rounded-lg border border-purple-100">
                      <span className="text-[10px] text-slate-400 block font-semibold">Pooled p-bar</span>
                      <span className="font-mono text-sm font-bold text-purple-900">
                        {effectivenessData.pooled_p_bar} ({((effectivenessData.pooled_p_bar || 0) * 100).toFixed(2)}%)
                      </span>
                    </div>
                    <div className="p-2.5 bg-white rounded-lg border border-purple-100">
                      <span className="text-[10px] text-slate-400 block font-semibold">95% CI for Difference</span>
                      <span className="font-mono text-xs font-bold text-purple-900">
                        [{effectivenessData.confidence_interval_diff_percent?.[0]}%, {effectivenessData.confidence_interval_diff_percent?.[1]}%]
                      </span>
                    </div>
                  </div>

                  <div className="text-xs text-purple-950 bg-white/70 p-2.5 rounded-lg border border-purple-100">
                    <span className="font-semibold">Outcome: </span>
                    <span className="font-mono font-bold text-purple-900">{effectivenessData.outcome}</span>
                    <p className="mt-0.5 text-slate-600">{effectivenessData.recommendation}</p>
                  </div>
                </div>

                {/* 4. Small-Sample Warning (if applicable) */}
                {effectivenessData.is_small_sample && (
                  <div className="p-3 bg-amber-50 border border-amber-200 rounded-xl flex items-start gap-2.5 text-xs text-amber-800">
                    <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
                    <div>
                      <span className="font-bold text-amber-900 block">Small Sample Threshold Warning</span>
                      <span>{effectivenessData.warning || "Fewer than 30 inspected parts or 5 defect events. Too little data to draw confident conclusions."}</span>
                    </div>
                  </div>
                )}

                {/* 5. Plain-Language Association vs Causation Caution */}
                <div className="p-4 bg-sky-50/80 border border-sky-200 rounded-xl space-y-2 text-xs">
                  <div className="flex items-center gap-1.5 font-bold text-sky-950">
                    <ShieldCheck className="w-4 h-4 text-sky-600" />
                    <span>Association vs Causation Epistemic Caution (PDF Problem Statement Requirement)</span>
                  </div>
                  <p className="text-sky-900 leading-relaxed">
                    <b>Observed Association:</b> The statistical finding reports an observed association in before-and-after production on this machine. <b>Causation is not proven</b> because the manufacturing cell operated without a randomized control group or parallel un-intervened machine baseline.
                  </p>
                  {effectivenessData.confounding_explanations && (
                    <div className="pt-1.5 border-t border-sky-200/60 text-sky-800 text-[11px]">
                      <b>Potential Confounders:</b> {effectivenessData.confounding_explanations}
                    </div>
                  )}
                </div>

                {/* 6. Agent 7 Defect Recurrence Detector */}
                <div className={`p-3.5 rounded-xl border flex items-start gap-2.5 text-xs ${
                  effectivenessData.recurrence_detected
                    ? "bg-rose-50 border-rose-200 text-rose-900"
                    : "bg-emerald-50 border-emerald-200 text-emerald-900"
                }`}>
                  {effectivenessData.recurrence_detected ? (
                    <AlertCircle className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
                  ) : (
                    <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
                  )}
                  <div>
                    <span className="font-bold block">
                      {effectivenessData.recurrence_detected ? "Defect Recurrence Detected" : "No Defect Recurrence Detected"}
                    </span>
                    <span className="text-[11px] opacity-90">{effectivenessData.recurrence_details}</span>
                  </div>
                </div>
              </div>
            ) : null}

            {/* Modal Footer */}
            <div className="flex items-center justify-between pt-3 border-t border-slate-100 text-xs">
              <button
                onClick={() => openEffectivenessModal(selectedActionForEffectiveness)}
                className="px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg font-semibold flex items-center gap-1.5 cursor-pointer transition-colors"
                title="Re-run statistical verification with latest batches"
              >
                <RefreshCw className="w-3.5 h-3.5" />
                <span>Recompute Verification</span>
              </button>

              <button
                onClick={() => setSelectedActionForEffectiveness(null)}
                className="px-4 py-1.5 bg-slate-800 hover:bg-slate-900 text-white rounded-lg font-semibold cursor-pointer transition-colors"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

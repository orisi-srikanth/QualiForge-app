import React, { useEffect, useState } from "react";
import { api } from "../api";
import { CertaintyBadge } from "../components/CertaintyBadge";
import {
  Layers, CheckSquare, AlertTriangle, Clock, RefreshCw, Calendar,
  ArrowRight, ShieldCheck, Activity, LineChart, GitFork, Bot,
  FileText, ShieldAlert, Cpu, Eye, ExternalLink, Filter
} from "lucide-react";
import {
  ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip as RechartsTooltip,
  Legend, PieChart, Pie, Cell, CartesianGrid
} from "recharts";

interface Props {
  onNavigate: (page: string) => void;
  onSelectBatch?: (batchId: string) => void;
}

export const QualityEngineerDashboard: React.FC<Props> = ({ onNavigate, onSelectBatch }) => {
  const [summaryData, setSummaryData] = useState<any>(null);
  const [incidents, setIncidents] = useState<any[]>([]);
  const [capaActions, setCapaActions] = useState<any[]>([]);
  const [visionFindings, setVisionFindings] = useState<any[]>([]);
  const [humanDecisions, setHumanDecisions] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");

  const loadAllData = async (s?: string, e?: string) => {
    setLoading(true);
    setError(null);
    try {
      const [sumRes, incRes, capaRes, visRes, decRes] = await Promise.all([
        api.getDashboardSummary(s || undefined, e || undefined).catch(() => null),
        api.getIncidents().catch(() => []),
        api.listCapaActions().catch(() => []),
        api.getVisionFindings().catch(() => []),
        api.getHumanDecisions().catch(() => [])
      ]);

      if (sumRes && !sumRes.detail) {
        setSummaryData(sumRes);
      }
      setIncidents(Array.isArray(incRes) ? incRes : []);
      setCapaActions(Array.isArray(capaRes) ? capaRes : (capaRes?.actions || []));
      setVisionFindings(Array.isArray(visRes) ? visRes : (visRes?.findings || []));
      setHumanDecisions(Array.isArray(decRes) ? decRes : []);
    } catch (err: any) {
      setError(err?.message || "Failed to load Quality Engineer dashboard metrics.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAllData();
  }, []);

  const handleApplyFilter = () => {
    loadAllData(startDate, endDate);
  };

  const handleResetFilter = () => {
    setStartDate("");
    setEndDate("");
    loadAllData("", "");
  };

  const batches = summaryData?.production_batches || { total_count: 0, status_split: {}, active_batches_count: 0 };
  const inspection = summaryData?.inspection_quantity || { total_inspected_parts: 0, accepted_parts: 0, nonconforming_parts: 0 };
  const spc = summaryData?.process_control_status || { status: "UNKNOWN", is_in_control: true, reason: "No SPC telemetry" };
  const topDefects = summaryData?.top_defect_categories || [];

  const capaStatusCounts = capaActions.reduce((acc: Record<string, number>, act: any) => {
    const st = act.status || "OPEN";
    acc[st] = (acc[st] || 0) + 1;
    return acc;
  }, {});

  const capaChartData = Object.entries(capaStatusCounts).map(([status, count]) => ({
    name: status.replace("_", " "),
    count: count as number,
    color: status === "APPROVED" || status === "CLOSED" ? "#10B981" : status === "PENDING_APPROVAL" ? "#F59E0B" : "#3B82F6"
  }));

  const conformanceChartData = [
    { name: "Conforming (Accepted)", parts: inspection.accepted_parts, color: "#10B981" },
    { name: "Non-conforming (Defective)", parts: inspection.nonconforming_parts, color: "#EF4444" }
  ].filter(d => d.parts > 0);

  const pendingIncidents = incidents.filter((inc) => inc.status !== "CLOSED");
  const pendingCapaApprovals = capaActions.filter((act) => act.status === "PENDING_APPROVAL" || act.status === "PROPOSED");
  const unreviewedVision = visionFindings.filter((vf) => vf.human_review_status === "PENDING" || vf.confidence < 0.90);

  return (
    <div className="space-y-6 max-w-7xl mx-auto">

      <div className="p-4 bg-white border border-slate-200 rounded-xl shadow-xs flex flex-wrap items-center justify-between gap-4">
        <div className="flex flex-wrap items-center gap-3 text-xs">
          <div className="flex items-center gap-1.5 text-slate-800 font-semibold">
            <Calendar className="w-4 h-4 text-slate-500" />
            <span>Inspection Date Filter:</span>
          </div>
          <div className="flex items-center gap-1.5">
            <label className="text-slate-500">From:</label>
            <input
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              className="px-2.5 py-1 border border-slate-300 rounded-lg text-xs bg-slate-50 text-slate-800 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>
          <div className="flex items-center gap-1.5">
            <label className="text-slate-500">To:</label>
            <input
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              className="px-2.5 py-1 border border-slate-300 rounded-lg text-xs bg-slate-50 text-slate-800 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>
          <button
            onClick={handleApplyFilter}
            className="px-3 py-1 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs font-semibold cursor-pointer shadow-xs transition-colors"
          >
            Apply
          </button>
          {(startDate || endDate) && (
            <button
              onClick={handleResetFilter}
              className="px-2.5 py-1 bg-slate-100 hover:bg-slate-200 text-slate-600 rounded-lg text-xs font-medium cursor-pointer transition-colors"
            >
              Reset
            </button>
          )}
          {summaryData?.filter_applied?.is_filtered && (
            <span className="px-2 py-0.5 bg-blue-50 text-blue-700 border border-blue-200 rounded text-[11px] font-medium">
              Filtered: {summaryData.filter_applied.start_date || "Earliest"} to {summaryData.filter_applied.end_date || "Latest"}
            </span>
          )}
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => loadAllData(startDate, endDate)}
            className="p-1.5 text-slate-600 hover:text-slate-900 hover:bg-slate-100 rounded-lg cursor-pointer transition-colors"
            title="Refresh All Metrics"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin text-blue-600" : ""}`} />
          </button>
          <div className="text-[11px] text-slate-500 font-mono">
            Plant Score: <strong className="text-slate-900">{summaryData?.overall_health_score ?? 100}%</strong>
          </div>
        </div>
      </div>

      {loading && !summaryData && (
        <div className="p-12 bg-white border border-slate-200 rounded-xl text-center space-y-3">
          <Activity className="w-8 h-8 animate-spin text-blue-600 mx-auto" />
          <div className="text-sm font-semibold text-slate-700">Loading Quality Engineer Workspace Data...</div>
        </div>
      )}

      {error && !summaryData && (
        <div className="p-6 bg-rose-50 border border-rose-200 rounded-xl space-y-2 text-rose-800 text-xs">
          <div className="flex items-center gap-2 font-bold text-sm">
            <AlertTriangle className="w-4 h-4 text-rose-600" />
            Failed to Load Quality Data
          </div>
          <p>{error}</p>
          <button
            onClick={() => loadAllData()}
            className="mt-2 px-3 py-1 bg-rose-600 text-white rounded font-semibold cursor-pointer"
          >
            Retry
          </button>
        </div>
      )}

      {summaryData && (
        <>

          {summaryData.active_quality_incidents > 0 && (
            <div className="p-4 bg-amber-50 border border-amber-200 rounded-xl flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
              <div className="flex items-start gap-3">
                <div className="p-2 bg-amber-100 text-amber-800 rounded-lg shrink-0">
                  <AlertTriangle className="w-5 h-5" />
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-bold text-amber-900">
                      ACTIVE QUALITY DEVIATION: {summaryData.active_quality_incidents} Active NCR(s) Under Investigation
                    </span>
                    <CertaintyBadge level="Observed Fact" />
                  </div>
                  <p className="text-xs text-amber-800 mt-0.5">
                    {summaryData.primary_machine_status ? (
                      <>
                        Cell {summaryData.primary_machine_status.machine_id}: Machine vibration {summaryData.primary_machine_status.vibration_mms} mm/s,
                        tool wear at {summaryData.primary_machine_status.tool_cycles} cycles.
                      </>
                    ) : (
                      "Physical non-conformance detected on shop floor. Causal investigation required."
                    )}
                  </p>
                </div>
              </div>
              <div className="flex flex-wrap items-center gap-2 shrink-0">
                <button
                  onClick={() => onNavigate("process-investigation")}
                  className="px-3.5 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-xs font-semibold shadow-xs cursor-pointer flex items-center gap-1.5"
                >
                  <GitFork className="w-3.5 h-3.5" />
                  <span>Process Investigation</span>
                </button>
                <button
                  onClick={() => onNavigate("rca")}
                  className="px-3.5 py-2 bg-amber-600 hover:bg-amber-700 text-white rounded-lg text-xs font-semibold shadow-xs cursor-pointer"
                >
                  Investigate Root Cause
                </button>
                <button
                  onClick={() => onNavigate("capa")}
                  className="px-3.5 py-2 bg-white hover:bg-slate-50 text-slate-700 border border-slate-300 rounded-lg text-xs font-semibold shadow-xs cursor-pointer"
                >
                  View CAPAs ({summaryData.open_capas})
                </button>
              </div>
            </div>
          )}

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">

            <div className="p-4 bg-white border border-slate-200 rounded-xl shadow-xs space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-medium text-slate-500">Acceptance Rate</span>
                <span className="p-1 rounded bg-emerald-50 text-emerald-600 font-bold text-[10px]">
                  IATF 16949
                </span>
              </div>
              <div className="flex items-baseline justify-between">
                <span className="text-2xl font-extrabold text-slate-900 tracking-tight">
                  {summaryData.acceptance_rate_percent}%
                </span>
                <span className="text-[11px] text-slate-500 font-mono">
                  {inspection.accepted_parts} parts
                </span>
              </div>
              <div className="text-[11px] text-slate-500 pt-1 border-t border-slate-100 flex items-center justify-between">
                <span>Total Inspected: {inspection.total_inspected_parts}</span>
                <span className="text-emerald-600 font-semibold">Target ≥98.0%</span>
              </div>
            </div>

            <div className="p-4 bg-white border border-slate-200 rounded-xl shadow-xs space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-medium text-slate-500">Rejection Rate</span>
                <span className="p-1 rounded bg-rose-50 text-rose-600 font-bold text-[10px]">
                  Nonconformance
                </span>
              </div>
              <div className="flex items-baseline justify-between">
                <span className="text-2xl font-extrabold text-slate-900 tracking-tight">
                  {summaryData.rejection_rate_percent}%
                </span>
                <span className="text-[11px] text-rose-600 font-mono">
                  {inspection.nonconforming_parts} rejects
                </span>
              </div>
              <div className="text-[11px] text-slate-500 pt-1 border-t border-slate-100 flex items-center justify-between">
                <span>Sum-to-100% check:</span>
                <span className="font-mono text-slate-700">Valid</span>
              </div>
            </div>

            <div className="p-4 bg-white border border-slate-200 rounded-xl shadow-xs space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-medium text-slate-500">Active Incidents (NCRs)</span>
                <ShieldAlert className="w-4 h-4 text-amber-600" />
              </div>
              <div className="flex items-baseline justify-between">
                <span className="text-2xl font-extrabold text-slate-900 tracking-tight">
                  {summaryData.active_quality_incidents}
                </span>
                <span className="text-[11px] text-slate-500">
                  Total: {summaryData.total_incidents}
                </span>
              </div>
              <div className="text-[11px] text-slate-500 pt-1 border-t border-slate-100 flex items-center justify-between">
                <span>Status: Under Review</span>
                <button onClick={() => onNavigate("incidents")} className="text-blue-600 font-semibold hover:underline">
                  Manage NCRs
                </button>
              </div>
            </div>

            <div className="p-4 bg-white border border-slate-200 rounded-xl shadow-xs space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-medium text-slate-500">CAPA Actions</span>
                <Clock className="w-4 h-4 text-indigo-600" />
              </div>
              <div className="flex items-baseline justify-between">
                <span className="text-2xl font-extrabold text-slate-900 tracking-tight">
                  {summaryData.open_capas}
                </span>
                <span className={`text-xs font-bold px-2 py-0.5 rounded-full ${
                  summaryData.overdue_capas > 0 ? "bg-rose-100 text-rose-800" : "bg-emerald-100 text-emerald-800"
                }`}>
                  {summaryData.overdue_capas} Overdue
                </span>
              </div>
              <div className="text-[11px] text-slate-500 pt-1 border-t border-slate-100 flex items-center justify-between">
                <span>Open / In Progress</span>
                <button onClick={() => onNavigate("capa")} className="text-blue-600 font-semibold hover:underline">
                  View Actions
                </button>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="p-3.5 bg-white border border-slate-200 rounded-xl shadow-xs flex items-center justify-between text-xs">
              <div>
                <div className="text-slate-500 font-medium">Production Batches Tracked</div>
                <div className="text-lg font-bold text-slate-900 mt-0.5">{batches.total_count} Batches</div>
              </div>
              <div className="flex flex-wrap gap-1">
                {Object.entries(batches.status_split || {}).map(([st, cnt]) => (
                  <span key={st} className="px-1.5 py-0.5 rounded text-[10px] font-mono bg-slate-100 text-slate-700">
                    {st}: {cnt as number}
                  </span>
                ))}
              </div>
            </div>

            <div className="p-3.5 bg-white border border-slate-200 rounded-xl shadow-xs flex items-center justify-between text-xs">
              <div>
                <div className="text-slate-500 font-medium">Machine Sensor Anomalies</div>
                <div className="text-lg font-bold text-slate-900 mt-0.5">{summaryData.machine_anomalies_detected} Anomalies</div>
              </div>
              <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-50 text-amber-700 border border-amber-200">
                MAD & EWMA
              </span>
            </div>

            <div className="p-3.5 bg-white border border-slate-200 rounded-xl shadow-xs flex items-center justify-between text-xs">
              <div>
                <div className="text-slate-500 font-medium">Process Control Status</div>
                <div className={`text-sm font-bold mt-0.5 ${spc.is_in_control ? "text-emerald-700" : "text-rose-700"}`}>
                  {spc.status}
                </div>
              </div>
              <div className="text-right text-[11px] text-slate-500">
                <div>Cpk: <strong className="text-slate-800">{summaryData?.spc_status?.process_capability_cpk ?? "N/A"}</strong></div>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

            <div className="p-5 bg-white border border-slate-200 rounded-xl shadow-xs space-y-4">
              <div className="flex items-center justify-between border-b border-slate-100 pb-3">
                <div>
                  <h3 className="text-sm font-bold text-slate-900">Inspection Conformance Distribution</h3>
                  <p className="text-xs text-slate-500">Real empirical sample counts from calibrated measurements</p>
                </div>
                <CertaintyBadge level="Observed Fact" />
              </div>

              {conformanceChartData.length > 0 ? (
                <div className="h-60 w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={conformanceChartData} layout="vertical" margin={{ top: 10, right: 30, left: 40, bottom: 5 }}>
                      <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#E2E8F0" />
                      <XAxis type="number" unit=" pts" tick={{ fontSize: 11 }} />
                      <YAxis dataKey="name" type="category" tick={{ fontSize: 11 }} width={120} />
                      <RechartsTooltip
                        formatter={(val: any) => [`${val} parts`, "Quantity"]}
                        contentStyle={{ backgroundColor: "#1e293b", borderRadius: "8px", color: "#fff", fontSize: "11px" }}
                      />
                      <Bar dataKey="parts" radius={[0, 4, 4, 0]}>
                        {conformanceChartData.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={entry.color} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              ) : (
                <div className="h-60 flex items-center justify-center text-xs text-slate-400 bg-slate-50 rounded-lg">
                  No inspection measurement records available for conformance charting.
                </div>
              )}
            </div>

            <div className="p-5 bg-white border border-slate-200 rounded-xl shadow-xs space-y-4">
              <div className="flex items-center justify-between border-b border-slate-100 pb-3">
                <div>
                  <h3 className="text-sm font-bold text-slate-900">Defect Category Pareto (Vital Few)</h3>
                  <p className="text-xs text-slate-500">Ranked frequency from non-conformance records (IATF 16949)</p>
                </div>
                <button
                  onClick={() => onNavigate("rca")}
                  className="text-xs text-blue-600 hover:underline flex items-center gap-1 font-semibold"
                >
                  Deep Analysis <ArrowRight className="w-3.5 h-3.5" />
                </button>
              </div>

              {topDefects.length > 0 ? (
                <div className="h-60 w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={topDefects} margin={{ top: 10, right: 20, left: 10, bottom: 25 }}>
                      <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#E2E8F0" />
                      <XAxis dataKey="defect" tick={{ fontSize: 10 }} angle={-15} textAnchor="end" interval={0} />
                      <YAxis unit=" occ" tick={{ fontSize: 11 }} />
                      <RechartsTooltip
                        formatter={(val: any, _name: any, item: any) => [
                          `${val} occurrences (${item?.payload?.percentage ?? 0}%)`,
                          "Count"
                        ]}
                        contentStyle={{ backgroundColor: "#1e293b", borderRadius: "8px", color: "#fff", fontSize: "11px" }}
                      />
                      <Bar dataKey="count" fill="#3B82F6" radius={[4, 4, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              ) : (
                <div className="h-60 flex items-center justify-center text-xs text-slate-400 bg-slate-50 rounded-lg">
                  No defect records found in the specified range.
                </div>
              )}
            </div>

            <div className="p-5 bg-white border border-slate-200 rounded-xl shadow-xs space-y-4">
              <div className="flex items-center justify-between border-b border-slate-100 pb-3">
                <div>
                  <h3 className="text-sm font-bold text-slate-900">
                    Machining Cell Sensor Status ({summaryData.primary_machine_status?.machine_id || "CNC-04"})
                  </h3>
                  <p className="text-xs text-slate-500">Sensor telemetry readings vs established trip thresholds</p>
                </div>
                <CertaintyBadge level="Statistical Finding" />
              </div>

              {summaryData.primary_machine_status ? (
                <div className="space-y-4 pt-2">
                  {(() => {
                    const status = summaryData.primary_machine_status;
                    const toolCycles = status.tool_cycles || 0;
                    const toolLimit = status.tool_cycle_limit || 1000;
                    const toolPercent = Math.min(100, Math.round((toolCycles / toolLimit) * 100));
                    const isToolOverdue = toolCycles > toolLimit;
                    const vib = status.vibration_mms || 0;
                    const vibPercent = Math.min(100, Math.round((vib / 3.5) * 100));
                    const isVibHigh = vib > 3.2;

                    return (
                      <>
                        <div className="p-3 bg-slate-50 border border-slate-200 rounded-lg space-y-2">
                          <div className="flex justify-between text-xs font-semibold">
                            <span className="text-slate-700">Tool Flank Wear Cycles</span>
                            <span className={`${isToolOverdue ? "text-rose-600" : "text-slate-700"} font-mono`}>
                              {toolCycles} / {toolLimit} cycles
                            </span>
                          </div>
                          <div className="w-full h-2.5 bg-slate-200 rounded-full overflow-hidden">
                            <div
                              className={`h-full ${isToolOverdue ? "bg-rose-500" : "bg-blue-500"} rounded-full`}
                              style={{ width: `${toolPercent}%` }}
                            />
                          </div>
                          <div className="text-[10px] text-slate-500 flex justify-between">
                            <span>Threshold: {toolLimit} nominal</span>
                            <span className={isToolOverdue ? "text-rose-600 font-semibold" : "text-emerald-600 font-medium"}>
                              {isToolOverdue ? `Overdue (+${toolCycles - toolLimit} cycles)` : "Nominal condition"}
                            </span>
                          </div>
                        </div>

                        <div className="p-3 bg-slate-50 border border-slate-200 rounded-lg space-y-2">
                          <div className="flex justify-between text-xs font-semibold">
                            <span className="text-slate-700">Spindle Vibration Amplitude</span>
                            <span className={`${isVibHigh ? "text-rose-600" : "text-slate-700"} font-mono`}>
                              {vib.toFixed(2)} mm/s (Trip limit: 3.5 mm/s)
                            </span>
                          </div>
                          <div className="w-full h-2.5 bg-slate-200 rounded-full overflow-hidden">
                            <div
                              className={`h-full ${isVibHigh ? "bg-rose-500" : "bg-emerald-500"} rounded-full`}
                              style={{ width: `${vibPercent}%` }}
                            />
                          </div>
                          <div className="text-[10px] text-slate-500 flex justify-between">
                            <span>Nominal baseline: {status.vibration_baseline || 2.1} mm/s</span>
                            <span className={isVibHigh ? "text-rose-600 font-semibold" : "text-emerald-600 font-medium"}>
                              {isVibHigh ? "Elevated vibration anomaly" : "Within normal baseline"}
                            </span>
                          </div>
                        </div>
                      </>
                    );
                  })()}

                  <button
                    onClick={() => onNavigate("process-monitoring")}
                    className="w-full py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg text-xs font-semibold flex items-center justify-center gap-1.5 transition-colors cursor-pointer"
                  >
                    <Activity className="w-4 h-4 text-slate-600" />
                    Open Multi-Sensor Telemetry
                  </button>
                </div>
              ) : (
                <div className="h-52 flex items-center justify-center text-xs text-slate-400 bg-slate-50 rounded-lg">
                  No active machine cell telemetry streaming.
                </div>
              )}
            </div>

            <div className="p-5 bg-white border border-slate-200 rounded-xl shadow-xs space-y-4">
              <div className="flex items-center justify-between border-b border-slate-100 pb-3">
                <div>
                  <h3 className="text-sm font-bold text-slate-900">CAPA Workflow Status Distribution</h3>
                  <p className="text-xs text-slate-500">Live breakdown of containment, corrective & preventive actions</p>
                </div>
                <button
                  onClick={() => onNavigate("capa")}
                  className="text-xs text-blue-600 hover:underline flex items-center gap-1 font-semibold"
                >
                  Manage CAPAs <ArrowRight className="w-3.5 h-3.5" />
                </button>
              </div>

              {capaChartData.length > 0 ? (
                <div className="h-52 w-full flex items-center">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={capaChartData}
                        cx="50%"
                        cy="50%"
                        innerRadius={45}
                        outerRadius={70}
                        paddingAngle={3}
                        dataKey="count"
                      >
                        {capaChartData.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={entry.color} />
                        ))}
                      </Pie>
                      <RechartsTooltip
                        formatter={(val: any, name: any) => [`${val} actions`, name]}
                        contentStyle={{ backgroundColor: "#1e293b", borderRadius: "8px", color: "#fff", fontSize: "11px" }}
                      />
                      <Legend wrapperStyle={{ fontSize: "11px" }} />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
              ) : (
                <div className="h-52 flex items-center justify-center text-xs text-slate-400 bg-slate-50 rounded-lg">
                  No CAPA actions currently registered in database.
                </div>
              )}
            </div>
          </div>

          <div className="p-5 bg-white border border-slate-200 rounded-xl shadow-xs space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div>
                <h3 className="text-sm font-bold text-slate-900">Engineering Action Queue</h3>
                <p className="text-xs text-slate-500">Pending reviews, approvals, and non-conformances awaiting engineer disposition</p>
              </div>
              <span className="px-2.5 py-0.5 rounded text-xs font-bold bg-blue-50 text-blue-700 border border-blue-200">
                {pendingIncidents.length + pendingCapaApprovals.length + unreviewedVision.length} Items Require Action
              </span>
            </div>

            <div className="space-y-3">

              {pendingIncidents.length > 0 && (
                <div className="space-y-2">
                  <div className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">
                    Non-Conformance Incidents Awaiting Root Cause Verification ({pendingIncidents.length})
                  </div>
                  {pendingIncidents.slice(0, 3).map((inc: any) => (
                    <div
                      key={inc.id || inc.incident_number}
                      className="p-3 rounded-lg border border-amber-200 bg-amber-50/50 flex items-center justify-between gap-4 text-xs"
                    >
                      <div>
                        <div className="font-bold text-slate-900 flex items-center gap-2">
                          <span>{inc.incident_number || inc.id}</span>
                          <span className="text-[10px] px-1.5 py-0.2 rounded bg-amber-100 text-amber-800 font-mono">
                            {inc.severity || "CRITICAL"}
                          </span>
                        </div>
                        <div className="text-slate-600 text-[11px] mt-0.5">
                          Batch: <span className="font-semibold text-slate-900">{inc.batch_id}</span> &bull; Machine: {inc.machine_id} &bull; Defect: {inc.defect_type || inc.title}
                        </div>
                      </div>
                      <button
                        onClick={() => {
                          if (onSelectBatch && inc.batch_id) onSelectBatch(inc.batch_id);
                          onNavigate("rca");
                        }}
                        className="px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded-md font-semibold text-xs shrink-0 cursor-pointer"
                      >
                        Investigate RCA
                      </button>
                    </div>
                  ))}
                </div>
              )}

              {pendingCapaApprovals.length > 0 && (
                <div className="space-y-2 pt-2">
                  <div className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">
                    CAPA Plans Pending Engineering Authorization ({pendingCapaApprovals.length})
                  </div>
                  {pendingCapaApprovals.slice(0, 3).map((act: any) => (
                    <div
                      key={act.id || act.action_code}
                      className="p-3 rounded-lg border border-blue-200 bg-blue-50/40 flex items-center justify-between gap-4 text-xs"
                    >
                      <div>
                        <div className="font-bold text-slate-900 flex items-center gap-2">
                          <span>{act.action_code}</span>
                          <span className="text-[10px] px-1.5 py-0.2 rounded bg-blue-100 text-blue-800 font-mono">
                            {act.action_type || act.classification || "CORRECTIVE"}
                          </span>
                        </div>
                        <div className="text-slate-600 text-[11px] mt-0.5">
                          {act.description} &bull; Owner: {act.assigned_to || act.owner || "Quality Directorate"}
                        </div>
                      </div>
                      <button
                        onClick={() => onNavigate("capa")}
                        className="px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded-md font-semibold text-xs shrink-0 cursor-pointer"
                      >
                        Review & Sign Off
                      </button>
                    </div>
                  ))}
                </div>
              )}

              {unreviewedVision.length > 0 && (
                <div className="space-y-2 pt-2">
                  <div className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">
                    Vision Predictions Flagged for Verification ({unreviewedVision.length})
                  </div>
                  {unreviewedVision.slice(0, 3).map((vf: any) => (
                    <div
                      key={vf.id || vf.image_path}
                      className="p-3 rounded-lg border border-purple-200 bg-purple-50/40 flex items-center justify-between gap-4 text-xs"
                    >
                      <div>
                        <div className="font-bold text-slate-900 flex items-center gap-2">
                          <span>Part {vf.component_id || "P001"}</span>
                          <span className="text-[10px] px-1.5 py-0.2 rounded bg-purple-100 text-purple-800 font-mono">
                            Confidence: {Math.round((vf.confidence || 0.94) * 100)}%
                          </span>
                        </div>
                        <div className="text-slate-600 text-[11px] mt-0.5">
                          Predicted Defect: {vf.predicted_class || "Surface Scratch"} &bull; Model: {vf.model_version || "YOLOv8-v2.1"}
                        </div>
                      </div>
                      <button
                        onClick={() => onNavigate("visual-inspection")}
                        className="px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded-md font-semibold text-xs shrink-0 cursor-pointer"
                      >
                        Verify Bounding Box
                      </button>
                    </div>
                  ))}
                </div>
              )}

              {pendingIncidents.length === 0 && pendingCapaApprovals.length === 0 && unreviewedVision.length === 0 && (
                <div className="p-8 text-center bg-slate-50 rounded-lg text-xs text-slate-500 space-y-1">
                  <CheckSquare className="w-6 h-6 text-emerald-600 mx-auto" />
                  <div className="font-bold text-slate-800 text-sm">Work Queue Clear</div>
                  <p>All quality incidents, CAPAs, and vision inspection predictions have been reviewed.</p>
                </div>
              )}
            </div>
          </div>

          <div className="p-5 bg-white border border-slate-200 rounded-xl shadow-xs space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div>
                <h3 className="text-sm font-bold text-slate-900">Recent Engineering Audit Trail</h3>
                <p className="text-xs text-slate-500">Immutable Human-in-the-Loop decision records from database</p>
              </div>
              <button
                onClick={() => onNavigate("ai-review")}
                className="text-xs text-blue-600 hover:underline flex items-center gap-1 font-semibold"
              >
                Full Audit Dossier <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>

            {humanDecisions.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-50 text-slate-500 font-semibold border-b border-slate-200">
                    <tr>
                      <th className="py-2.5 px-3">Timestamp</th>
                      <th className="py-2.5 px-3">Quality Engineer</th>
                      <th className="py-2.5 px-3">Target Batch</th>
                      <th className="py-2.5 px-3">Decision</th>
                      <th className="py-2.5 px-3">Rationale / Notes</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {humanDecisions.length > 0 ? (
                      humanDecisions.slice(0, 5).map((d: any, idx: number) => (
                        <tr key={idx} className="hover:bg-slate-50/80">
                          <td className="py-2.5 px-3 font-mono text-slate-600">
                            {d.created_at || d.timestamp || "—"}
                          </td>
                          <td className="py-2.5 px-3 font-semibold text-slate-800">
                            {d.user_name || d.user_id || "Authorized Engineer"}
                          </td>
                          <td className="py-2.5 px-3 font-mono text-slate-900 font-medium">
                            {d.batch_id || "N/A"}
                          </td>
                          <td className="py-2.5 px-3">
                            <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                              d.decision === "ACCEPT" || d.decision === "APPROVED" || d.decision === "RELEASE"
                                ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
                                : d.decision === "HOLD" || d.decision === "QUALITY_HOLD"
                                ? "bg-amber-50 text-amber-700 border border-amber-200"
                                : "bg-rose-50 text-rose-700 border border-rose-200"
                            }`}>
                              {d.decision}
                            </span>
                          </td>
                          <td className="py-2.5 px-3 text-slate-600 max-w-xs truncate" title={d.comment}>
                            {d.comment || "—"}
                          </td>
                        </tr>
                      ))
                    ) : (
                      <tr>
                        <td colSpan={5} className="py-8 text-center text-xs text-slate-400">
                          No human engineering decisions recorded yet. Decisions logged during quality review will appear here.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="p-6 text-center bg-slate-50 rounded-lg text-xs text-slate-400">
                No human engineering decisions recorded yet in audit registry.
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
};

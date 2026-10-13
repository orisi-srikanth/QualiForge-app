import React, { useEffect, useState } from "react";
import { api } from "../api";
import { CertaintyBadge } from "../components/CertaintyBadge";
import { ParetoAnalysis } from "../components/ParetoAnalysis";
import {
  Activity, AlertTriangle, CheckCircle2, ShieldCheck,
  TrendingDown, TrendingUp, Cpu, Wrench, ArrowRight, Sparkles,
  Calendar, RefreshCw, Layers, ShieldAlert, CheckSquare, Clock
} from "lucide-react";
import { ResponsiveContainer, PieChart, Pie, Cell, Tooltip as RechartsTooltip } from "recharts";

interface Props {
  onNavigate: (page: string) => void;
  onRunPipeline: () => void;
}

export const DashboardPage: React.FC<Props> = ({ onNavigate, onRunPipeline }) => {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [startDate, setStartDate] = useState<string>("");
  const [endDate, setEndDate] = useState<string>("");

  const fetchDashboard = (s?: string, e?: string) => {
    setLoading(true);
    setError(null);
    api.getDashboardSummary(s || undefined, e || undefined)
      .then((res) => {
        if (res && res.detail) {
          setError(typeof res.detail === "string" ? res.detail : JSON.stringify(res.detail));
          setData(null);
        } else {
          setData(res);
        }
      })
      .catch((err) => {
        setError(err.message || "Failed to load dashboard summary");
      })
      .finally(() => {
        setLoading(false);
      });
  };

  useEffect(() => {
    fetchDashboard();
  }, []);

  const handleApplyFilter = () => {
    fetchDashboard(startDate, endDate);
  };

  const handleResetFilter = () => {
    setStartDate("");
    setEndDate("");
    fetchDashboard("", "");
  };

  if (loading && !data) {
    return (
      <div className="p-12 flex flex-col items-center justify-center text-slate-500 space-y-3">
        <Activity className="w-8 h-8 animate-spin text-blue-600" />
        <span className="text-sm font-medium">Loading Executive Quality Dashboard...</span>
      </div>
    );
  }

  if (error && !data) {
    return (
      <div className="p-8 bg-rose-50 border border-rose-200 rounded-xl space-y-3 text-rose-800">
        <div className="flex items-center gap-2 font-bold text-base">
          <AlertTriangle className="w-5 h-5 text-rose-600" />
          <span>Dashboard Error</span>
        </div>
        <p className="text-sm">{error}</p>
        <button
          onClick={() => fetchDashboard()}
          className="px-4 py-1.5 bg-rose-600 hover:bg-rose-700 text-white rounded-lg text-xs font-semibold cursor-pointer"
        >
          Retry
        </button>
      </div>
    );
  }

  // Handle empty data state
  const isEmpty = !data || (data.inspection_quantity?.total_inspected_parts === 0 && data.production_batches?.total_count === 0);

  const batches = data?.production_batches || { total_count: 0, status_split: {}, active_batches_count: 0 };
  const inspection = data?.inspection_quantity || { total_inspected_parts: 0, accepted_parts: 0, nonconforming_parts: 0 };
  const spc = data?.process_control_status || { status: "NO_DATA", is_in_control: true, reason: "No data", notice: "" };
  const machineAnomalies = data?.machine_anomalies_detected ?? 0;
  const topDefects = data?.top_defect_categories || [];

  return (
    <div className="space-y-6">


      {/* Date Filter & Control Bar */}
      <div className="p-4 bg-white border border-slate-200 rounded-xl shadow-xs flex flex-wrap items-center justify-between gap-4">
        <div className="flex flex-wrap items-center gap-3 text-xs">
          <div className="flex items-center gap-1.5 text-slate-700 font-semibold">
            <Calendar className="w-4 h-4 text-slate-500" />
            <span>Inspection Date Filter:</span>
          </div>
          <div className="flex items-center gap-1.5">
            <label className="text-slate-500">From:</label>
            <input
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              className="px-2.5 py-1 border border-slate-300 rounded-lg text-xs bg-slate-50 text-slate-700 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>
          <div className="flex items-center gap-1.5">
            <label className="text-slate-500">To:</label>
            <input
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              className="px-2.5 py-1 border border-slate-300 rounded-lg text-xs bg-slate-50 text-slate-700 focus:outline-none focus:ring-1 focus:ring-blue-500"
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
          {data?.filter_applied?.is_filtered && (
            <span className="px-2 py-0.5 bg-blue-50 text-blue-700 border border-blue-200 rounded text-[11px] font-medium">
              Filtered: {data.filter_applied.start_date || "Earliest"} to {data.filter_applied.end_date || "Latest"}
            </span>
          )}
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => fetchDashboard(startDate, endDate)}
            className="p-1.5 text-slate-600 hover:text-slate-900 hover:bg-slate-100 rounded-lg cursor-pointer transition-colors"
            title="Refresh Dashboard Data"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin text-blue-600" : ""}`} />
          </button>
          <div className="text-[11px] text-slate-500 font-mono">
            Plant Score: <strong className="text-slate-800">{data?.overall_health_score ?? 100}%</strong>
          </div>
        </div>
      </div>

      {isEmpty ? (
        /* Empty State */
        <div className="p-12 bg-white border border-slate-200 rounded-xl text-center space-y-3">
          <div className="w-12 h-12 bg-slate-100 text-slate-400 rounded-full flex items-center justify-center mx-auto">
            <Calendar className="w-6 h-6" />
          </div>
          <h3 className="text-base font-bold text-slate-800">No Production Records In Selected Range</h3>
          <p className="text-xs text-slate-500 max-w-md mx-auto">
            No batch production measurements, quality incidents, or telemetry readings match the specified dates.
            Try resetting the date filter or expanding the query range.
          </p>
          <button
            onClick={handleResetFilter}
            className="px-4 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs font-semibold cursor-pointer"
          >
            View All Records
          </button>
        </div>
      ) : (
        <>
          {/* Active Quality Hold Alert Banner if incidents or holds exist */}
          {data.active_quality_incidents > 0 && (
            <div className="p-4 bg-amber-50 border border-amber-200 rounded-xl flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
              <div className="flex items-start gap-3">
                <div className="p-2 bg-amber-100 text-amber-800 rounded-lg shrink-0">
                  <AlertTriangle className="w-5 h-5" />
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-bold text-amber-900">
                      ACTIVE QUALITY DEVIATION: {data.active_quality_incidents} Active NCR(s) Under Investigation
                    </span>
                    <CertaintyBadge level="Observed Fact" />
                  </div>
                  <p className="text-xs text-amber-800 mt-0.5">
                    {data.primary_machine_status?.machine_id
                      ? `Active quality deviation on machine ${data.primary_machine_status.machine_id}. Vibration: ${data.primary_machine_status?.vibration_mms} mm/s, Tool Wear: ${data.primary_machine_status?.tool_cycles} cycles.`
                      : "Quality non-conformance recorded under investigation. Review root cause analysis and corrective action status."}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2 shrink-0">
                <button
                  onClick={() => onNavigate("rca")}
                  className="px-3 py-1.5 bg-amber-600 hover:bg-amber-700 text-white rounded-lg text-xs font-semibold shadow-xs cursor-pointer"
                >
                  Investigate Root Cause
                </button>
                <button
                  onClick={() => onNavigate("capa")}
                  className="px-3 py-1.5 bg-white hover:bg-slate-50 text-slate-700 border border-slate-300 rounded-lg text-xs font-semibold shadow-xs cursor-pointer"
                >
                  View Open CAPAs ({data.open_capas})
                </button>
              </div>
            </div>
          )}

          {/* Primary Top 4 KPI Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {/* Card 1: Acceptance Rate (Recorded Sample Result) */}
            <div className="p-4 bg-white border border-slate-200 rounded-xl shadow-xs space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-medium text-slate-500">Acceptance Rate</span>
                <div className="p-1.5 rounded-lg text-emerald-600 bg-emerald-50">
                  <CheckCircle2 className="w-4 h-4" />
                </div>
              </div>
              <div className="flex items-baseline justify-between">
                <span className="text-2xl font-bold text-slate-900 tracking-tight">{data.acceptance_rate_percent}%</span>
                <span className="text-[10px] text-slate-400 font-mono">Sample Result</span>
              </div>
              <div className="text-[11px] text-slate-500 pt-1 border-t border-slate-100 flex items-center justify-between">
                <span>Conforming: {inspection.accepted_parts.toLocaleString()} pts</span>
                <span className="text-emerald-600 font-medium">Target: ≥98.0%</span>
              </div>
            </div>

            {/* Card 2: Rejection Rate (Recorded Sample Result) */}
            <div className="p-4 bg-white border border-slate-200 rounded-xl shadow-xs space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-medium text-slate-500">Rejection Rate</span>
                <div className="p-1.5 rounded-lg text-rose-600 bg-rose-50">
                  <AlertTriangle className="w-4 h-4" />
                </div>
              </div>
              <div className="flex items-baseline justify-between">
                <span className="text-2xl font-bold text-slate-900 tracking-tight">{data.rejection_rate_percent}%</span>
                <span className="text-[10px] text-slate-400 font-mono">Sample Result</span>
              </div>
              <div className="text-[11px] text-slate-500 pt-1 border-t border-slate-100 flex items-center justify-between">
                <span>Nonconforming: {inspection.nonconforming_parts.toLocaleString()} pts</span>
                <span className="text-slate-400 font-mono">Sum: 100.0%</span>
              </div>
            </div>

            {/* Card 3: Machine Anomalies (Statistical Finding) */}
            <div className="p-4 bg-white border border-slate-200 rounded-xl shadow-xs space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-medium text-slate-500">Machine Anomalies</span>
                <div className="p-1.5 rounded-lg text-amber-600 bg-amber-50">
                  <Activity className="w-4 h-4" />
                </div>
              </div>
              <div className="flex items-baseline justify-between">
                <span className="text-2xl font-bold text-slate-900 tracking-tight">{machineAnomalies}</span>
                <span className="text-[10px] text-amber-700 bg-amber-50 border border-amber-200 px-1.5 py-0.5 rounded font-mono">
                  Trip Limit
                </span>
              </div>
              <div className="text-[11px] text-slate-500 pt-1 border-t border-slate-100 flex items-center justify-between">
                <span>CNC-04 Spindle Vibration</span>
                <span className="text-rose-600 font-medium">3.85 mm/s</span>
              </div>
            </div>

            {/* Card 4: Process-Control Status (Statistical signal, not a product decision) */}
            <div className="p-4 bg-white border border-slate-200 rounded-xl shadow-xs space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-medium text-slate-500">Process Control Status</span>
                <div className={`p-1.5 rounded-lg ${spc.is_in_control ? "text-emerald-600 bg-emerald-50" : "text-rose-600 bg-rose-50"}`}>
                  <TrendingDown className="w-4 h-4" />
                </div>
              </div>
              <div className="flex items-baseline justify-between">
                <span className={`text-base font-bold tracking-tight ${spc.is_in_control ? "text-emerald-700" : "text-rose-700"}`}>
                  {spc.status === "OUT_OF_CONTROL" ? "OUT OF CONTROL" : (spc.status === "IN_CONTROL" ? "IN CONTROL" : spc.status)}
                </span>
                <span className="text-[10px] text-slate-400 font-mono">Cpk: {data.spc_status?.process_capability_cpk ?? 0.0}</span>
              </div>
              <div className="text-[11px] text-slate-500 pt-1 border-t border-slate-100">
                <p className="truncate" title={spc.reason}>{spc.reason}</p>
                <p className="text-[9.5px] text-slate-400 italic mt-0.5">Notice: statistical signal, not a product decision</p>
              </div>
            </div>
          </div>

          {/* Secondary 6 KPI Cards (Production Batches, Inspection Quantity, Incidents, CAPAs) */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {/* Item 1: Production Batches & Status Split */}
            <div className="p-4 bg-white border border-slate-200 rounded-xl shadow-xs space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-medium text-slate-500">Production Batches</span>
                <div className="p-1.5 rounded-lg text-blue-600 bg-blue-50">
                  <Layers className="w-4 h-4" />
                </div>
              </div>
              <div className="flex items-baseline justify-between">
                <span className="text-2xl font-bold text-slate-900 tracking-tight">{batches.total_count}</span>
                <span className="text-[11px] text-slate-500">Batches tracked</span>
              </div>
              <div className="text-[11px] text-slate-600 pt-1 border-t border-slate-100 flex flex-wrap gap-1">
                {Object.entries(batches.status_split || {}).map(([st, cnt]) => (
                  <span
                    key={st}
                    className={`px-1.5 py-0.5 rounded text-[10px] font-semibold ${
                      st === "CONFORMING" ? "bg-emerald-50 text-emerald-700 border border-emerald-200" :
                      st === "QUALITY_HOLD" ? "bg-amber-50 text-amber-700 border border-amber-200" :
                      "bg-blue-50 text-blue-700 border border-blue-200"
                    }`}
                  >
                    {st}: {cnt as number}
                  </span>
                ))}
              </div>
            </div>

            {/* Item 2: Inspection Quantity */}
            <div className="p-4 bg-white border border-slate-200 rounded-xl shadow-xs space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-medium text-slate-500">Inspection Quantity</span>
                <div className="p-1.5 rounded-lg text-purple-600 bg-purple-50">
                  <CheckSquare className="w-4 h-4" />
                </div>
              </div>
              <div className="flex items-baseline justify-between">
                <span className="text-2xl font-bold text-slate-900 tracking-tight">
                  {inspection.total_inspected_parts.toLocaleString()}
                </span>
                <span className="text-[11px] text-slate-500">Inspected parts</span>
              </div>
              <div className="text-[11px] text-slate-500 pt-1 border-t border-slate-100 flex items-center justify-between">
                <span>Accepted: {inspection.accepted_parts.toLocaleString()}</span>
                <span className="text-rose-600">Rejects: {inspection.nonconforming_parts.toLocaleString()}</span>
              </div>
            </div>

            {/* Item 5: Active Quality Incidents */}
            <div className="p-4 bg-white border border-slate-200 rounded-xl shadow-xs space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-medium text-slate-500">Active Quality Incidents</span>
                <div className="p-1.5 rounded-lg text-amber-600 bg-amber-50">
                  <ShieldAlert className="w-4 h-4" />
                </div>
              </div>
              <div className="flex items-baseline justify-between">
                <span className="text-2xl font-bold text-slate-900 tracking-tight">{data.active_quality_incidents}</span>
                <span className="text-[11px] text-slate-500">Total NCRs: {data.total_incidents}</span>
              </div>
              <div className="text-[11px] text-slate-500 pt-1 border-t border-slate-100 flex items-center justify-between">
                <span>Status: Not Closed</span>
                <button
                  onClick={() => onNavigate("incidents")}
                  className="text-blue-600 hover:underline font-semibold"
                >
                  Manage NCRs
                </button>
              </div>
            </div>

            {/* Items 8 & 9: Open & Overdue CAPAs */}
            <div className="p-4 bg-white border border-slate-200 rounded-xl shadow-xs space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-medium text-slate-500">CAPA Management</span>
                <div className="p-1.5 rounded-lg text-indigo-600 bg-indigo-50">
                  <Clock className="w-4 h-4" />
                </div>
              </div>
              <div className="flex items-baseline justify-between">
                <span className="text-2xl font-bold text-slate-900 tracking-tight">{data.open_capas}</span>
                <span className={`text-xs font-bold px-2 py-0.5 rounded-full ${data.overdue_capas > 0 ? "bg-rose-100 text-rose-800" : "bg-emerald-100 text-emerald-800"}`}>
                  {data.overdue_capas} Overdue
                </span>
              </div>
              <div className="text-[11px] text-slate-500 pt-1 border-t border-slate-100 flex items-center justify-between">
                <span>Open Actions (pending/in-prog)</span>
                <button
                  onClick={() => onNavigate("capa")}
                  className="text-blue-600 hover:underline font-semibold"
                >
                  View CAPA
                </button>
              </div>
            </div>
          </div>

          {/* Two-Column Middle Section: Machine Health & Pareto Defect Categories */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Column 1: Machine Cell Health Card & Telemetry Risk Breakdown Pie Chart */}
            <div className="space-y-4">
              {/* Machine Status & Telemetry Card */}
              <div className="p-5 bg-white border border-slate-200 rounded-xl shadow-xs space-y-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Cpu className="w-4 h-4 text-slate-600" />
                    <h2 className="text-sm font-bold text-slate-900">Machine Cell Health ({data.primary_machine_status?.machine_id})</h2>
                  </div>
                  <span className="px-2 py-0.5 rounded text-xs font-semibold bg-rose-50 text-rose-700 border border-rose-200">
                    {data.primary_machine_status?.status}
                  </span>
                </div>

                <div className="space-y-3">
                  <div>
                    <div className="flex justify-between text-xs font-medium mb-1">
                      <span className="text-slate-600">Cutting Tool Usage Cycles</span>
                      <span className="text-rose-600 font-bold">
                        {data.primary_machine_status?.tool_cycles} / {data.primary_machine_status?.tool_cycle_limit} cycles
                      </span>
                    </div>
                    <div className="w-full h-2 bg-slate-100 rounded-full overflow-hidden">
                      <div className="h-full bg-rose-500 rounded-full" style={{ width: "100%" }} />
                    </div>
                    <p className="text-[10px] text-slate-400 mt-0.5">Threshold: 1,000 cycles | Severe flank wear risk</p>
                  </div>

                  <div>
                    <div className="flex justify-between text-xs font-medium mb-1">
                      <span className="text-slate-600">Machine Vibration Amplitude</span>
                      <span className="text-rose-600 font-bold">
                        {data.primary_machine_status?.vibration_mms} mm/s (Trip: 3.5 mm/s)
                      </span>
                    </div>
                    <div className="w-full h-2 bg-slate-100 rounded-full overflow-hidden">
                      <div className="h-full bg-rose-500 rounded-full" style={{ width: "95%" }} />
                    </div>
                    <p className="text-[10px] text-slate-400 mt-0.5">Baseline: 2.1 mm/s (+83% elevation)</p>
                  </div>
                </div>

                <div className="pt-2 border-t border-slate-100 flex items-center justify-between">
                  <span className="text-xs text-slate-500">Overall Cell Health Index</span>
                  <span className="text-sm font-bold text-slate-800">{data.primary_machine_status?.health_index}</span>
                </div>

                <button
                  onClick={() => onNavigate("process-monitoring")}
                  className="w-full py-2 bg-slate-50 hover:bg-slate-100 text-slate-700 border border-slate-200 rounded-lg text-xs font-medium flex items-center justify-center gap-1 cursor-pointer transition-colors"
                >
                  <span>Inspect Live Machine Telemetry</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </button>
              </div>

              {/* Machine Telemetry Risk Factor Pie Chart */}
              <div className="p-5 bg-white border border-slate-200 rounded-xl shadow-xs space-y-3">
                <div className="flex items-center justify-between border-b border-slate-100 pb-2.5">
                  <div className="flex items-center gap-2">
                    <Activity className="w-4 h-4 text-rose-600" />
                    <h3 className="text-sm font-bold text-slate-900">Cell Risk Factor Distribution</h3>
                  </div>
                  <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-rose-100 text-rose-800 font-mono">
                    ATTENTION REQUIRED
                  </span>
                </div>

                <div className="h-44 w-full relative flex items-center justify-center">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={[
                          { name: "Tool Flank Wear (1,150 cycles)", value: 48, color: "#EF4444" },
                          { name: "Vibration Trip Limit (3.85 mm/s)", value: 34, color: "#F59E0B" },
                          { name: "Thermal Stability (Nominal)", value: 18, color: "#10B981" },
                        ]}
                        cx="50%"
                        cy="50%"
                        innerRadius={45}
                        outerRadius={68}
                        paddingAngle={3}
                        dataKey="value"
                      >
                        {[
                          { color: "#EF4444" },
                          { color: "#F59E0B" },
                          { color: "#10B981" },
                        ].map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={entry.color} />
                        ))}
                      </Pie>
                      <RechartsTooltip
                        formatter={(val: any, name: any) => [`${val}% Risk Share`, name]}
                        contentStyle={{ backgroundColor: "#1e293b", borderColor: "#334155", borderRadius: "8px", fontSize: "11px", color: "#fff" }}
                      />
                    </PieChart>
                  </ResponsiveContainer>
                  <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
                    <span className="text-xs font-bold text-rose-700 font-mono">82%</span>
                    <span className="text-[9px] text-slate-400 font-medium">Critical Severity</span>
                  </div>
                </div>

                <div className="space-y-1.5 pt-1 text-[11px] border-t border-slate-100">
                  <div className="flex items-center justify-between">
                    <span className="flex items-center gap-1.5 text-slate-600">
                      <span className="w-2.5 h-2.5 rounded-full bg-rose-500 shrink-0" />
                      Tool Wear Cycles (1,150)
                    </span>
                    <span className="font-bold text-rose-700 font-mono">48%</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="flex items-center gap-1.5 text-slate-600">
                      <span className="w-2.5 h-2.5 rounded-full bg-amber-500 shrink-0" />
                      Spindle Vibration (3.85 mm/s)
                    </span>
                    <span className="font-bold text-amber-700 font-mono">34%</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="flex items-center gap-1.5 text-slate-600">
                      <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 shrink-0" />
                      Coolant Temp (24.1 &deg;C)
                    </span>
                    <span className="font-bold text-emerald-700 font-mono">18%</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Interactive Pareto Analysis & Top Defect Categories (Item 6) */}
            <div className="lg:col-span-2">
              <div className="space-y-4">
                {/* Top Defect Categories Summary Cards */}
                <div className="p-5 bg-white border border-slate-200 rounded-xl shadow-xs space-y-3">
                  <div className="flex items-center justify-between">
                    <h2 className="text-sm font-bold text-slate-900">Item 6: Top Defect Categories (Pareto Vital Few)</h2>
                    <span className="text-xs text-slate-500 font-mono">Ranked Defect Distribution</span>
                  </div>
                  <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-2">
                    {topDefects.slice(0, 5).map((d: any, idx: number) => (
                      <div key={idx} className="p-2.5 bg-slate-50 border border-slate-200 rounded-lg text-xs space-y-1">
                        <div className="flex items-center justify-between">
                          <span className="font-semibold text-slate-800 truncate" title={d.defect}>{d.defect}</span>
                          <span className="text-blue-600 font-bold ml-1">{d.count}</span>
                        </div>
                        <div className="flex items-center justify-between text-[11px] text-slate-500">
                          <span>Frequency</span>
                          <span>{d.percentage}%</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Pareto Component */}
                <ParetoAnalysis onNavigate={onNavigate} />
              </div>
            </div>
          </div>

        </>
      )}

    </div>
  );
};

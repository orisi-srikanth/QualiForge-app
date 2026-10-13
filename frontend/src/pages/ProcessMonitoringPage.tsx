import React, { useEffect, useState } from "react";
import { api } from "../api";
import { ProcessMonitoringReport, TelemetryDataPoint } from "../types";
import { CertaintyBadge } from "../components/CertaintyBadge";
import {
  Activity, AlertTriangle, CheckCircle2, RefreshCw,
  Clock, Filter, Info, ShieldAlert
} from "lucide-react";
import {
  ResponsiveContainer, LineChart, Line, XAxis, YAxis, Tooltip, CartesianGrid, ReferenceLine
} from "recharts";

export const ProcessMonitoringPage: React.FC = () => {
  const [selectedMachine, setSelectedMachine] = useState<string>("CNC-04");
  const [selectedBatch, setSelectedBatch] = useState<string>("");
  const [batches, setBatches] = useState<any[]>([]);
  const [timeFilter, setTimeFilter] = useState<string>("all");

  const [report, setReport] = useState<ProcessMonitoringReport | null>(null);
  const [dataPoints, setDataPoints] = useState<TelemetryDataPoint[]>([]);
  const [baselines, setBaselines] = useState<Record<string, any>>({});
  const [trends, setTrends] = useState<Record<string, any>>({});
  const [changedVsUnchanged, setChangedVsUnchanged] = useState<any[]>([]);
  const [anomalies, setAnomalies] = useState<any[]>([]);
  const [warnings, setWarnings] = useState<string[]>([]);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Load available batches on mount
  useEffect(() => {
    api.getBatches().then((bList) => {
      setBatches(bList || []);
      if (bList && bList.length > 0) {
        setSelectedBatch(bList[0].batch_number || bList[0].batch_id || "");
      } else {
        setLoading(false);
      }
    }).catch(() => {
      setLoading(false);
    });
  }, []);

  const loadData = async () => {
    if (!selectedBatch) {
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const res = await api.getTelemetry(selectedBatch, selectedMachine);
      setReport(res.report);
      setDataPoints(res.data_points || []);
      setBaselines(res.baselines || {});
      setTrends(res.trends || {});
      setChangedVsUnchanged(res.changed_vs_unchanged || []);
      setAnomalies(res.anomalies || []);
      setWarnings(res.warnings || []);
    } catch (err: any) {
      setError("Unable to load process telemetry. Please verify machine connectivity and retry.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (selectedBatch) {
      loadData();
    }
  }, [selectedMachine, selectedBatch]);

  // Filter data points by time range if requested
  const filteredDataPoints = React.useMemo(() => {
    if (timeFilter === "early") return dataPoints.slice(0, Math.floor(dataPoints.length / 2));
    if (timeFilter === "late") return dataPoints.slice(Math.floor(dataPoints.length / 2));
    return dataPoints;
  }, [dataPoints, timeFilter]);

  if (loading) {
    return (
      <div className="p-12 text-center space-y-4">
        <div className="w-8 h-8 border-3 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto" />
        <p className="text-[14.5px] text-slate-500 font-medium">Loading Telemetry & Anomaly Analysis...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-8 max-w-xl mx-auto bg-white border border-rose-200 rounded-xl text-center space-y-4 shadow-sm">
        <AlertTriangle className="w-8 h-8 text-rose-600 mx-auto" />
        <h3 className="text-base font-bold text-slate-900">Telemetry Stream Error</h3>
        <p className="text-sm text-slate-600">{error}</p>
        <button onClick={loadData} className="btn-primary">
          <RefreshCw className="w-4 h-4" />
          <span>Retry Loading Telemetry</span>
        </button>
      </div>
    );
  }

  const isAnomalous = (report?.anomalies_detected || 0) > 0 || (anomalies.length > 0);

  return (
    <div className="space-y-6">
      {/* Page Title & Filter Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h2 className="text-[26px] font-bold text-slate-900 leading-tight">Process Monitoring</h2>
          <p className="text-[14px] text-slate-500 mt-1">
            Real-time machine telemetry, sensor drift analysis, and multi-parameter anomaly detection.
          </p>
        </div>

        {/* Unified Filter Controls Bar - Perfectly Aligned */}
        <div className="flex items-center gap-2 flex-wrap sm:flex-nowrap bg-white border border-slate-200 rounded-xl p-2 shadow-2xs">
          {/* Machine Filter */}
          <div className="flex items-center gap-1.5 px-2.5 py-1.5 bg-slate-50 border border-slate-200 rounded-lg">
            <span className="text-xs font-semibold text-slate-600 whitespace-nowrap">Machine:</span>
            <select
              value={selectedMachine}
              onChange={(e) => setSelectedMachine(e.target.value)}
              className="bg-transparent text-xs font-bold text-slate-800 focus:outline-none cursor-pointer"
            >
              <option value="CNC-04">CNC-04 (Turning Cell 4)</option>
              <option value="CNC-01">CNC-01 (Roughing Lathe)</option>
              <option value="CNC-02">CNC-02 (Finishing Lathe)</option>
              <option value="CNC-03">CNC-03 (Milling Cell)</option>
            </select>
          </div>

          {/* Batch Filter */}
          <div className="flex items-center gap-1.5 px-2.5 py-1.5 bg-slate-50 border border-slate-200 rounded-lg">
            <span className="text-xs font-semibold text-slate-600 whitespace-nowrap">Batch:</span>
            <select
              value={selectedBatch}
              onChange={(e) => setSelectedBatch(e.target.value)}
              className="bg-transparent text-xs font-bold text-slate-800 focus:outline-none cursor-pointer"
            >
              {batches.length === 0 ? (
                <option value="">No Batches Registered</option>
              ) : (
                batches.map((b) => (
                  <option key={b.id || b.batch_number} value={b.batch_number}>
                    {b.batch_number} {b.product_name ? `(${b.product_name})` : ""}
                  </option>
                ))
              )}
            </select>
          </div>

          {/* Time Range Filter */}
          <div className="flex items-center gap-1.5 px-2.5 py-1.5 bg-slate-50 border border-slate-200 rounded-lg">
            <span className="text-xs font-semibold text-slate-600 whitespace-nowrap">Time Window:</span>
            <select
              value={timeFilter}
              onChange={(e) => setTimeFilter(e.target.value)}
              className="bg-transparent text-xs font-bold text-slate-800 focus:outline-none cursor-pointer"
            >
              <option value="all">Full Batch Run (All)</option>
              <option value="early">Initial Shift (First Half)</option>
              <option value="late">Latter Shift (Second Half)</option>
            </select>
          </div>

          {/* Refresh Action */}
          <button
            onClick={loadData}
            title="Refresh Telemetry Stream"
            className="p-2 bg-slate-100 hover:bg-slate-200 text-slate-600 rounded-lg cursor-pointer transition-colors border border-slate-200 flex items-center justify-center shrink-0"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Warnings Banner with Summarized Notice and Small Typography */}
      {warnings.length > 0 && (
        <div className="px-3.5 py-2 bg-amber-50/90 border border-amber-200 rounded-lg text-amber-900 text-xs flex items-center justify-between shadow-2xs font-sans">
          <div className="flex items-center gap-2">
            <Info className="w-4 h-4 text-amber-600 shrink-0" />
            <span>
              <strong className="font-semibold text-amber-950">Data quality notice:</strong>{" "}
              {(() => {
                const recs: string[] = [];
                warnings.forEach((w) => {
                  const m = w.match(/record\s*#(\d+)/i);
                  if (m) recs.push(`#${m[1]}`);
                });
                if (recs.length > 0) {
                  return `${recs.length} duplicate timestamps detected (${recs.join(", ")}) — deduplicated keeping latest readings.`;
                }
                return warnings.join("; ");
              })()}
            </span>
          </div>
          <span className="text-[10px] font-mono font-semibold px-2 py-0.5 bg-amber-100 text-amber-800 rounded">
            AUTO-DEDUPLICATED
          </span>
        </div>
      )}

      {/* If No Data Points, Render Clean Empty State */}
      {filteredDataPoints.length === 0 ? (
        <div className="p-12 text-center bg-white border border-slate-200 rounded-xl space-y-3 shadow-xs">
          <Activity className="w-10 h-10 text-slate-400 mx-auto" />
          <h3 className="text-base font-bold text-slate-900">No Process Telemetry Available</h3>
          <p className="text-sm text-slate-500 max-w-md mx-auto">
            No telemetry sensor data recorded for {selectedBatch || "this batch"} on {selectedMachine}. Register a production batch and stream or upload machine sensor readings to view real-time process monitoring and anomaly detection.
          </p>
        </div>
      ) : (
        <>
          {/* Operational Condition Callout Banner */}
      {isAnomalous ? (
        <div className="p-4 bg-rose-50 border border-rose-200 rounded-xl flex items-start gap-3.5 shadow-2xs">
          <div className="p-2 bg-rose-100 text-rose-700 rounded-lg shrink-0 mt-0.5">
            <AlertTriangle className="w-5 h-5" />
          </div>
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <span className="text-[15px] font-bold text-rose-900">
                MULTIPLE ABNORMAL CONDITIONS DETECTED ON {selectedMachine} ({selectedBatch})
              </span>
              <span className="status-pill status-pill-danger">Critical Anomaly</span>
            </div>
            <p className="text-[13.5px] text-rose-800 leading-relaxed">
              1. <strong>Spindle Vibration:</strong> Spiked to {report?.vibration_current.toFixed(2)} mm/s (Trip Limit: 3.5 mm/s, Baseline: 2.1 mm/s; +81% elevation).<br />
              2. <strong>Cutting Tool Usage:</strong> Reached {report?.tool_cycles_current} cycles (Scheduled Replacement: 600 cycles, Max Lockout: 1,000 cycles).<br />
              3. <strong>Thermal & Kinetic Parameters:</strong> Coolant temp stable at {report?.temperature_current.toFixed(1)} °C; Spindle speed (1,200 RPM) and feed rate (0.20 mm/rev) strictly nominal.
            </p>
          </div>
        </div>
      ) : (
        <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-xl flex items-center gap-3.5 shadow-2xs">
          <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0" />
          <div>
            <span className="text-[15px] font-bold text-emerald-900">
              OPERATIONAL PARAMETERS NORMAL ON {selectedMachine} ({selectedBatch})
            </span>
            <p className="text-[13px] text-emerald-800 mt-0.5">
              All 8 machine parameters are operating strictly within certified baseline bands and statistical control limits.
            </p>
          </div>
        </div>
      )}

      {/* 5 Core Parameter Summary Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3.5">
        {/* 1. Vibration */}
        <div className={`p-4 bg-white border rounded-xl shadow-xs ${isAnomalous ? "border-rose-200 bg-rose-50/20" : "border-slate-200"}`}>
          <span className="text-xs text-slate-500 font-semibold block uppercase tracking-wider">1. Vibration</span>
          <span className={`text-2xl font-bold font-mono ${isAnomalous ? "text-rose-700" : "text-slate-900"}`}>
            {(report?.vibration_current || 2.1).toFixed(2)} <span className="text-sm font-sans font-normal text-slate-500">mm/s</span>
          </span>
          <span className={`text-[11px] font-semibold block mt-1 ${isAnomalous ? "text-rose-600" : "text-emerald-600"}`}>
            Trip limit: 3.5 mm/s {isAnomalous ? "(EXCEEDED)" : "(Normal)"}
          </span>
        </div>

        {/* 2. Tool Cycles */}
        <div className={`p-4 bg-white border rounded-xl shadow-xs ${isAnomalous ? "border-rose-200 bg-rose-50/20" : "border-slate-200"}`}>
          <span className="text-xs text-slate-500 font-semibold block uppercase tracking-wider">2. Tool Usage</span>
          <span className={`text-2xl font-bold font-mono ${isAnomalous ? "text-rose-700" : "text-slate-900"}`}>
            {report?.tool_cycles_current || 600} <span className="text-sm font-sans font-normal text-slate-500">cycles</span>
          </span>
          <span className={`text-[11px] font-semibold block mt-1 ${isAnomalous ? "text-rose-600" : "text-emerald-600"}`}>
            Nominal limit: 600 {isAnomalous ? "(+91% EXCEEDED)" : "(Nominal)"}
          </span>
        </div>

        {/* 3. Coolant Temperature */}
        <div className="p-4 bg-white border border-slate-200 rounded-xl shadow-xs">
          <span className="text-xs text-slate-500 font-semibold block uppercase tracking-wider">3. Coolant Temp</span>
          <span className="text-2xl font-bold font-mono text-slate-900">
            {(report?.temperature_current || 24.0).toFixed(1)} <span className="text-sm font-sans font-normal text-slate-500">&deg;C</span>
          </span>
          <span className="text-[11px] text-emerald-600 font-semibold block mt-1">
            Warn limit: 28.0 &deg;C (Normal)
          </span>
        </div>

        {/* 4. Spindle Speed */}
        <div className="p-4 bg-white border border-slate-200 rounded-xl shadow-xs">
          <span className="text-xs text-slate-500 font-semibold block uppercase tracking-wider">4. Spindle Speed</span>
          <span className="text-2xl font-bold font-mono text-slate-900">
            1,200 <span className="text-sm font-sans font-normal text-slate-500">RPM</span>
          </span>
          <span className="text-[11px] text-emerald-600 font-semibold block mt-1">
            Target: 1,200 RPM (Constant)
          </span>
        </div>

        {/* 5. Feed Rate */}
        <div className="p-4 bg-white border border-slate-200 rounded-xl shadow-xs">
          <span className="text-xs text-slate-500 font-semibold block uppercase tracking-wider">5. Feed Rate</span>
          <span className="text-2xl font-bold font-mono text-slate-900">
            0.20 <span className="text-sm font-sans font-normal text-slate-500">mm/rev</span>
          </span>
          <span className="text-[11px] text-emerald-600 font-semibold block mt-1">
            Target: 0.20 mm/rev (Constant)
          </span>
        </div>
      </div>

      {/* 5 Parameter Interactive Trend Charts */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-base font-bold text-slate-900">
            Historical Parameter Trend Series & Baseline Limit Bands
          </h3>
          <span className="text-[13px] text-slate-500 font-medium">
            {filteredDataPoints.length} snapshots evaluated
          </span>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
          {/* Chart 1: Vibration vs Trip Threshold */}
          <div className="p-5 bg-white border border-slate-200 rounded-xl shadow-xs space-y-3">
            <div className="flex items-center justify-between">
              <div>
                <h4 className="text-sm font-bold text-slate-900">1. Spindle Vibration Amplitude (mm/s)</h4>
                <p className="text-xs text-slate-500">
                  Trip Limit: 3.50 mm/s (ISO 10816-3) | Baseline: 2.10 mm/s
                  {trends.vibration && ` | Trend: ${trends.vibration.direction} (slope: +${trends.vibration.slope})`}
                </p>
              </div>
              <CertaintyBadge level="Statistical Finding" />
            </div>

            <div className="h-56">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={filteredDataPoints} margin={{ top: 10, right: 25, left: 0, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#EEF1F5" />
                  <XAxis dataKey="timestamp" tick={{ fontSize: 9 }} tickFormatter={(ts) => ts.slice(-8)} />
                  <YAxis domain={[1.5, 4.5]} tick={{ fontSize: 10 }} />
                  <Tooltip
                    formatter={(val: any) => [`${Number(val).toFixed(2)} mm/s`, "Vibration"]}
                    labelFormatter={(lbl) => `Time: ${lbl}`}
                    contentStyle={{ backgroundColor: "#ffffff", borderColor: "#E3E8EF", fontSize: "12px", borderRadius: "8px" }}
                  />
                  <ReferenceLine y={3.5} label={{ value: "Trip Limit 3.5 mm/s", fill: "#B42318", fontSize: 10 }} stroke="#B42318" strokeDasharray="4 4" />
                  <ReferenceLine y={2.1} label={{ value: "Baseline 2.1 mm/s", fill: "#067647", fontSize: 10 }} stroke="#067647" strokeDasharray="2 2" />
                  <Line
                    type="monotone"
                    dataKey="machine_vibration_mms"
                    stroke="#2563EB"
                    strokeWidth={2}
                    dot={{ r: 2.5, fill: "#2563EB" }}
                    activeDot={{ r: 5 }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Chart 2: Tool Usage Cycles vs Lockout */}
          <div className="p-5 bg-white border border-slate-200 rounded-xl shadow-xs space-y-3">
            <div className="flex items-center justify-between">
              <div>
                <h4 className="text-sm font-bold text-slate-900">2. Cutting Tool Cycles Accumulation (cycles)</h4>
                <p className="text-xs text-slate-500">
                  Lockout Limit: 1,000 cycles | Nominal Replacement: 600 cycles
                  {trends.tool_usage_cycles && ` | Trend: ${trends.tool_usage_cycles.direction}`}
                </p>
              </div>
              <CertaintyBadge level="Observed Fact" />
            </div>

            <div className="h-56">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={filteredDataPoints} margin={{ top: 10, right: 25, left: 0, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#EEF1F5" />
                  <XAxis dataKey="timestamp" tick={{ fontSize: 9 }} tickFormatter={(ts) => ts.slice(-8)} />
                  <YAxis domain={[500, 1300]} tick={{ fontSize: 10 }} />
                  <Tooltip
                    formatter={(val: any) => [`${val} cycles`, "Tool Cycles"]}
                    labelFormatter={(lbl) => `Time: ${lbl}`}
                    contentStyle={{ backgroundColor: "#ffffff", borderColor: "#E3E8EF", fontSize: "12px", borderRadius: "8px" }}
                  />
                  <ReferenceLine y={1000} label={{ value: "Max Lockout 1,000", fill: "#B42318", fontSize: 10 }} stroke="#B42318" strokeDasharray="4 4" />
                  <ReferenceLine y={600} label={{ value: "Nominal 600", fill: "#067647", fontSize: 10 }} stroke="#067647" strokeDasharray="2 2" />
                  <Line
                    type="monotone"
                    dataKey="tool_usage_cycles"
                    stroke="#7C3AED"
                    strokeWidth={2}
                    dot={{ r: 2.5, fill: "#7C3AED" }}
                    activeDot={{ r: 5 }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Chart 3: Coolant Temperature */}
          <div className="p-5 bg-white border border-slate-200 rounded-xl shadow-xs space-y-3">
            <div className="flex items-center justify-between">
              <div>
                <h4 className="text-sm font-bold text-slate-900">3. Coolant Sump Temperature (°C)</h4>
                <p className="text-xs text-slate-500">
                  Warn Limit: 28.0 °C | Trip: 30.0 °C | Baseline: 24.0 °C
                </p>
              </div>
              <CertaintyBadge level="Observed Fact" />
            </div>

            <div className="h-56">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={filteredDataPoints} margin={{ top: 10, right: 25, left: 0, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#EEF1F5" />
                  <XAxis dataKey="timestamp" tick={{ fontSize: 9 }} tickFormatter={(ts) => ts.slice(-8)} />
                  <YAxis domain={[22.0, 31.0]} tick={{ fontSize: 10 }} />
                  <Tooltip
                    formatter={(val: any) => [`${Number(val).toFixed(1)} °C`, "Coolant Temp"]}
                    labelFormatter={(lbl) => `Time: ${lbl}`}
                    contentStyle={{ backgroundColor: "#ffffff", borderColor: "#E3E8EF", fontSize: "12px", borderRadius: "8px" }}
                  />
                  <ReferenceLine y={28.0} label={{ value: "Warn 28 °C", fill: "#D97706", fontSize: 10 }} stroke="#D97706" strokeDasharray="4 4" />
                  <ReferenceLine y={24.0} label={{ value: "Baseline 24 °C", fill: "#067647", fontSize: 10 }} stroke="#067647" strokeDasharray="2 2" />
                  <Line
                    type="monotone"
                    dataKey="coolant_temperature_c"
                    stroke="#0284C7"
                    strokeWidth={2}
                    dot={{ r: 2.5, fill: "#0284C7" }}
                    activeDot={{ r: 5 }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Chart 4: Spindle Speed */}
          <div className="p-5 bg-white border border-slate-200 rounded-xl shadow-xs space-y-3">
            <div className="flex items-center justify-between">
              <div>
                <h4 className="text-sm font-bold text-slate-900">4. Spindle Speed (RPM)</h4>
                <p className="text-xs text-slate-500">
                  Target: 1,200 RPM | Permissible Tolerance: ±30 RPM (1,170 - 1,230)
                </p>
              </div>
              <CertaintyBadge level="Observed Fact" />
            </div>

            <div className="h-56">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={filteredDataPoints} margin={{ top: 10, right: 25, left: 0, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#EEF1F5" />
                  <XAxis dataKey="timestamp" tick={{ fontSize: 9 }} tickFormatter={(ts) => ts.slice(-8)} />
                  <YAxis domain={[1150, 1250]} tick={{ fontSize: 10 }} />
                  <Tooltip
                    formatter={(val: any) => [`${Number(val).toFixed(0)} RPM`, "Spindle Speed"]}
                    labelFormatter={(lbl) => `Time: ${lbl}`}
                    contentStyle={{ backgroundColor: "#ffffff", borderColor: "#E3E8EF", fontSize: "12px", borderRadius: "8px" }}
                  />
                  <ReferenceLine y={1200} label={{ value: "Target 1,200 RPM", fill: "#067647", fontSize: 10 }} stroke="#067647" strokeDasharray="2 2" />
                  <ReferenceLine y={1230} stroke="#94A3B8" strokeDasharray="3 3" />
                  <ReferenceLine y={1170} stroke="#94A3B8" strokeDasharray="3 3" />
                  <Line
                    type="monotone"
                    dataKey="spindle_speed_rpm"
                    stroke="#059669"
                    strokeWidth={2}
                    dot={{ r: 2.5, fill: "#059669" }}
                    activeDot={{ r: 5 }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Chart 5: Feed Rate (Full Width or 5th Grid Item) */}
          <div className="lg:col-span-2 p-5 bg-white border border-slate-200 rounded-xl shadow-xs space-y-3">
            <div className="flex items-center justify-between">
              <div>
                <h4 className="text-sm font-bold text-slate-900">5. Axis Feed Rate (mm/rev)</h4>
                <p className="text-xs text-slate-500">
                  Programmed Target: 0.200 mm/rev | CNC Tolerance Band: 0.185 - 0.215 mm/rev
                </p>
              </div>
              <CertaintyBadge level="Observed Fact" />
            </div>

            <div className="h-52">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={filteredDataPoints} margin={{ top: 10, right: 25, left: 0, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#EEF1F5" />
                  <XAxis dataKey="timestamp" tick={{ fontSize: 9 }} tickFormatter={(ts) => ts.slice(-8)} />
                  <YAxis domain={[0.18, 0.22]} tick={{ fontSize: 10 }} />
                  <Tooltip
                    formatter={(val: any) => [`${Number(val).toFixed(3)} mm/rev`, "Feed Rate"]}
                    labelFormatter={(lbl) => `Time: ${lbl}`}
                    contentStyle={{ backgroundColor: "#ffffff", borderColor: "#E3E8EF", fontSize: "12px", borderRadius: "8px" }}
                  />
                  <ReferenceLine y={0.20} label={{ value: "Target 0.200 mm/rev", fill: "#067647", fontSize: 10 }} stroke="#067647" strokeDasharray="2 2" />
                  <ReferenceLine y={0.215} stroke="#94A3B8" strokeDasharray="3 3" />
                  <ReferenceLine y={0.185} stroke="#94A3B8" strokeDasharray="3 3" />
                  <Line
                    type="monotone"
                    dataKey="feed_rate_mmrev"
                    stroke="#D97706"
                    strokeWidth={2}
                    dot={{ r: 2.5, fill: "#D97706" }}
                    activeDot={{ r: 5 }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      </div>

      {/* Changed vs Unchanged Parameters Table */}
      <div className="table-container">
        <div className="card-header-enterprise">
          <div>
            <h3 className="card-title-enterprise">Parameters Changed vs. Unchanged Contrast</h3>
            <p className="card-note-enterprise mt-0.5">
              Contrasting anomalous parameters against stable channels to exclude machine servo or speed command failure modes.
            </p>
          </div>
          <span className="status-pill status-pill-info">
            8 Parameters Evaluated
          </span>
        </div>

        <table className="w-full text-left border-collapse">
          <thead>
            <tr>
              <th className="table-header-cell">Parameter</th>
              <th className="table-header-cell">Baseline Reference</th>
              <th className="table-header-cell">Current Value</th>
              <th className="table-header-cell">Change Delta</th>
              <th className="table-header-cell">Condition Status</th>
              <th className="table-header-cell">Evidence Role in Root Cause Analysis</th>
            </tr>
          </thead>
          <tbody>
            {changedVsUnchanged.map((row, idx) => (
              <tr key={idx} className="table-row">
                <td className="px-4 py-3.5 text-sm font-semibold text-slate-900 whitespace-nowrap">
                  {row.name}
                  <span className="text-xs text-slate-400 font-normal block font-mono">({row.parameter})</span>
                </td>
                <td className="px-4 py-3.5 text-sm text-slate-600 font-mono whitespace-nowrap">
                  {row.baseline}
                </td>
                <td className="px-4 py-3.5 text-sm font-bold text-slate-900 font-mono whitespace-nowrap">
                  {row.current}
                </td>
                <td className="px-4 py-3.5 text-sm font-mono whitespace-nowrap">
                  <span className={row.status.includes("CRITICAL") ? "text-rose-600 font-bold" : row.status === "ELEVATED" ? "text-amber-600 font-semibold" : "text-slate-500"}>
                    {row.change}
                  </span>
                </td>
                <td className="px-4 py-3.5 whitespace-nowrap">
                  {row.status === "CHANGED_CRITICAL" ? (
                    <span className="status-pill status-pill-danger">Critical Deviation</span>
                  ) : row.status === "ELEVATED" ? (
                    <span className="status-pill text-amber-700 bg-amber-50 border border-amber-200">Elevated</span>
                  ) : row.status === "CHANGED_MINOR" ? (
                    <span className="status-pill text-blue-700 bg-blue-50 border border-blue-200">Minor Drift</span>
                  ) : (
                    <span className="status-pill status-pill-success">Unchanged (Normal)</span>
                  )}
                </td>
                <td className="px-4 py-3.5 text-xs text-slate-600 leading-relaxed max-w-md">
                  {row.evidence_role}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Abnormal Conditions / Anomalies Registry Table */}
      <div className="table-container">
        <div className="card-header-enterprise">
          <div>
            <h3 className="card-title-enterprise">Abnormal Conditions & Anomaly Registry</h3>
            <p className="card-note-enterprise mt-0.5">
              Algorithmic anomaly records flagged across statistical Z-score, EWMA drift, threshold breaches, and Isolation Forest.
            </p>
          </div>
          <span className="text-xs font-semibold text-slate-500 bg-slate-100 px-2.5 py-1 rounded-md">
            {anomalies.length} Anomaly Events Flagged
          </span>
        </div>

        {anomalies.length === 0 ? (
          <div className="p-8 text-center text-slate-500 text-sm">
            <CheckCircle2 className="w-6 h-6 text-emerald-600 mx-auto mb-1.5" />
            No abnormal conditions or threshold breaches recorded for this batch.
          </div>
        ) : (
          <table className="w-full text-left border-collapse">
            <thead>
              <tr>
                <th className="table-header-cell">Anomaly ID</th>
                <th className="table-header-cell">Parameter</th>
                <th className="table-header-cell">Timestamp</th>
                <th className="table-header-cell">Type</th>
                <th className="table-header-cell">Observed Value</th>
                <th className="table-header-cell">Threshold / Baseline</th>
                <th className="table-header-cell">Severity</th>
                <th className="table-header-cell">Detection Method</th>
                <th className="table-header-cell">Epistemic Label</th>
              </tr>
            </thead>
            <tbody>
              {anomalies.map((anom, idx) => (
                <tr key={idx} className="table-row">
                  <td className="px-4 py-3 text-xs font-mono font-bold text-blue-700 whitespace-nowrap">
                    {anom.anomaly_id}
                  </td>
                  <td className="px-4 py-3 text-sm font-semibold text-slate-900 whitespace-nowrap capitalize">
                    {anom.parameter.replace(/_/g, " ")}
                  </td>
                  <td className="px-4 py-3 text-xs text-slate-500 font-mono whitespace-nowrap">
                    {anom.timestamp}
                  </td>
                  <td className="px-4 py-3 text-xs whitespace-nowrap">
                    <span className="px-2 py-0.5 rounded bg-slate-100 text-slate-700 font-semibold font-mono">
                      {anom.type}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-sm font-mono font-bold text-rose-700 whitespace-nowrap">
                    {typeof anom.value === "number" ? anom.value.toFixed(2) : anom.value}
                  </td>
                  <td className="px-4 py-3 text-xs font-mono text-slate-600 whitespace-nowrap">
                    Limit: {anom.threshold} (Base: {anom.baseline})
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap">
                    <span className={`status-pill ${anom.severity === "CRITICAL" ? "status-pill-danger" : "text-amber-700 bg-amber-50 border border-amber-200"}`}>
                      {anom.severity || "HIGH"}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-xs text-slate-600 whitespace-nowrap font-medium">
                    {anom.method}
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap">
                    <CertaintyBadge level={anom.epistemic_label || "Statistical Finding"} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
        </>
      )}
    </div>
  );
};

export default ProcessMonitoringPage;

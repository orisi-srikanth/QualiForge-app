import React, { useState, useEffect } from "react";
import { api } from "../api";
import { CertaintyBadge } from "./CertaintyBadge";
import {
  BarChart3, Filter, Calendar, RotateCcw, AlertCircle,
  CheckCircle2, ArrowRight, Loader2, Info, ShieldCheck
} from "lucide-react";
import {
  ResponsiveContainer, ComposedChart, Bar, Line, XAxis, YAxis,
  Tooltip, CartesianGrid, ReferenceLine, Cell
} from "recharts";

interface Props {
  onNavigate?: (page: string) => void;
}

const DIMENSIONS = [
  { id: "defect_type", label: "Defect Types", desc: "Inspection defect classifications" },
  { id: "machine", label: "Machines", desc: "Production CNC equipment" },
  { id: "product_family", label: "Product Families", desc: "Product component families" },
  { id: "root_cause", label: "Confirmed Root Causes", desc: "Verified causes (QE Sign-off)" },
  { id: "rejection_reason", label: "Rejection Reasons", desc: "Recorded nonconformance reasons" },
];

export const ParetoAnalysis: React.FC<Props> = ({ onNavigate }) => {
  const [selectedDimension, setSelectedDimension] = useState<string>("defect_type");
  const [startDate, setStartDate] = useState<string>("");
  const [endDate, setEndDate] = useState<string>("");
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchPareto = async (dim: string, sDate?: string, eDate?: string) => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.getPareto(dim, sDate || undefined, eDate || undefined);
      setData(res);
    } catch (err: any) {
      setError(err.message || "Failed loading Pareto distribution.");
      setData(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPareto(selectedDimension, startDate, endDate);
  }, [selectedDimension]);

  const handleApplyFilter = (e: React.FormEvent) => {
    e.preventDefault();
    fetchPareto(selectedDimension, startDate, endDate);
  };

  const handleResetFilter = () => {
    setStartDate("");
    setEndDate("");
    fetchPareto(selectedDimension, "", "");
  };

  const setPreset = (presetStart: string, presetEnd: string) => {
    setStartDate(presetStart);
    setEndDate(presetEnd);
    fetchPareto(selectedDimension, presetStart, presetEnd);
  };

  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      const d = payload[0].payload;
      return (
        <div className="bg-white p-3 border border-slate-200 rounded-lg shadow-md text-xs space-y-1.5 max-w-xs">
          <div className="font-bold text-slate-900 border-b border-slate-100 pb-1">
            {d.category}
          </div>
          <div className="flex justify-between text-slate-600 gap-4">
            <span>Frequency:</span>
            <span className="font-semibold text-slate-900">{d.count} occurrences</span>
          </div>
          <div className="flex justify-between text-slate-600 gap-4">
            <span>Percentage:</span>
            <span className="font-semibold text-blue-600">{d.percentage}%</span>
          </div>
          <div className="flex justify-between text-slate-600 gap-4">
            <span>Cumulative:</span>
            <span className="font-semibold text-rose-600">{d.cumulative_percentage}%</span>
          </div>
          <div className="pt-1 border-t border-slate-100 flex items-center justify-between">
            <span className="text-[10px] text-slate-400">Classification:</span>
            <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${d.is_vital_few ? "bg-blue-100 text-blue-800" : "bg-slate-100 text-slate-600"}`}>
              {d.is_vital_few ? "Vital Few (80%)" : "Trivial Many"}
            </span>
          </div>
        </div>
      );
    }
    return null;
  };

  return (
    <div className="p-5 bg-white border border-slate-200 rounded-xl shadow-xs space-y-4" id="pareto-analysis-container">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <BarChart3 className="w-5 h-5 text-blue-600" />
            <h2 className="text-base font-bold text-slate-900">Pareto Analysis (IATF 16949 / 80-20 Rule)</h2>
          </div>
          <p className="text-xs text-slate-500 mt-0.5">
            Frequency distribution and cumulative percentage across 5 quality dimensions
            {selectedDimension === "root_cause" && (
              <span className="ml-1 text-emerald-700 font-semibold bg-emerald-50 px-1.5 py-0.5 rounded border border-emerald-200">
                Confirmed causes only
              </span>
            )}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <CertaintyBadge level="Statistical Finding" />
        </div>
      </div>

      {/* Dimension Selector Tabs */}
      <div className="flex flex-wrap gap-1.5 p-1 bg-slate-100 rounded-lg" id="pareto-dimension-tabs">
        {DIMENSIONS.map((dim) => (
          <button
            key={dim.id}
            id={`pareto-tab-${dim.id}`}
            onClick={() => setSelectedDimension(dim.id)}
            className={`px-3 py-1.5 rounded-md text-xs font-semibold transition-colors cursor-pointer ${
              selectedDimension === dim.id
                ? "bg-white text-blue-700 shadow-xs border border-slate-200"
                : "text-slate-600 hover:text-slate-900 hover:bg-slate-200/60"
            }`}
          >
            {dim.label}
          </button>
        ))}
      </div>

      {/* Date Range Filter Bar */}
      <form onSubmit={handleApplyFilter} className="flex flex-wrap items-center gap-2.5 p-3 bg-slate-50 border border-slate-200 rounded-lg text-xs">
        <div className="flex items-center gap-1 text-slate-600 font-medium">
          <Filter className="w-3.5 h-3.5" />
          <span>Date Filter:</span>
        </div>
        <div className="flex items-center gap-1.5">
          <label htmlFor="pareto-start-date" className="text-slate-500">From:</label>
          <input
            id="pareto-start-date"
            type="date"
            value={startDate}
            onChange={(e) => setStartDate(e.target.value)}
            className="px-2 py-1 bg-white border border-slate-300 rounded text-slate-800 text-xs focus:ring-1 focus:ring-blue-500"
          />
        </div>
        <div className="flex items-center gap-1.5">
          <label htmlFor="pareto-end-date" className="text-slate-500">To:</label>
          <input
            id="pareto-end-date"
            type="date"
            value={endDate}
            onChange={(e) => setEndDate(e.target.value)}
            className="px-2 py-1 bg-white border border-slate-300 rounded text-slate-800 text-xs focus:ring-1 focus:ring-blue-500"
          />
        </div>
        <button
          type="submit"
          id="pareto-apply-btn"
          className="px-3 py-1 bg-blue-600 hover:bg-blue-700 text-white rounded font-medium cursor-pointer transition-colors"
        >
          Apply Filter
        </button>
        <button
          type="button"
          id="pareto-reset-btn"
          onClick={handleResetFilter}
          className="px-2.5 py-1 bg-white hover:bg-slate-100 text-slate-600 border border-slate-300 rounded flex items-center gap-1 cursor-pointer"
        >
          <RotateCcw className="w-3 h-3" />
          <span>Reset</span>
        </button>

        {/* Quick Presets */}
        <div className="flex items-center gap-1 ml-auto text-[11px] text-slate-500">
          <span>Presets:</span>
          <button
            type="button"
            onClick={() => setPreset("2026-08-01", "2026-10-31")}
            className="px-1.5 py-0.5 bg-white border border-slate-200 rounded hover:bg-slate-100 text-blue-600 font-medium cursor-pointer"
          >
            Aug–Oct 2026
          </button>
          <button
            type="button"
            onClick={() => setPreset("2026-08-22", "2026-08-22")}
            className="px-1.5 py-0.5 bg-white border border-slate-200 rounded hover:bg-slate-100 text-blue-600 font-medium cursor-pointer"
          >
            Aug 22 (Single Day)
          </button>
          <button
            type="button"
            onClick={() => setPreset("2025-01-01", "2025-01-31")}
            className="px-1.5 py-0.5 bg-white border border-slate-200 rounded hover:bg-slate-100 text-slate-600 font-medium cursor-pointer"
          >
            2025 (Empty)
          </button>
        </div>
      </form>

      {/* Error State */}
      {error && (
        <div className="p-3 bg-rose-50 border border-rose-200 text-rose-800 rounded-lg text-xs flex items-center gap-2">
          <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Loading State */}
      {loading && !error && (
        <div className="h-64 flex flex-col items-center justify-center text-slate-500 text-xs gap-2">
          <Loader2 className="w-6 h-6 animate-spin text-blue-600" />
          <span>Loading Pareto distribution...</span>
        </div>
      )}

      {/* Empty State */}
      {!loading && !error && data && data.total === 0 && (
        <div className="p-8 text-center bg-slate-50 border border-slate-200 rounded-lg space-y-2">
          <Info className="w-6 h-6 text-slate-400 mx-auto" />
          <div className="text-sm font-semibold text-slate-700">No Quality Incidents Found</div>
          <p className="text-xs text-slate-500 max-w-md mx-auto">
            Zero quality events were recorded within the selected date range ({data.date_range_applied || "Specified window"}).
            Adjust your filter bounds or reset to view all historical occurrences.
          </p>
          <button
            onClick={handleResetFilter}
            className="mt-2 px-3 py-1 bg-white border border-slate-300 rounded text-xs text-slate-700 hover:bg-slate-100 cursor-pointer font-medium"
          >
            Reset Date Filter
          </button>
        </div>
      )}

      {/* Loaded Content */}
      {!loading && !error && data && data.total > 0 && (
        <div className="space-y-4">
          {/* Summary KPIs */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
            <div className="p-2.5 bg-slate-50 border border-slate-200 rounded-lg">
              <span className="text-slate-500 block text-[11px]">Total Events</span>
              <span className="text-base font-bold text-slate-900">{data.total}</span>
            </div>
            <div className="p-2.5 bg-slate-50 border border-slate-200 rounded-lg">
              <span className="text-slate-500 block text-[11px]">Categories</span>
              <span className="text-base font-bold text-slate-900">{data.categories_count}</span>
            </div>
            <div className="p-2.5 bg-blue-50/60 border border-blue-200 rounded-lg">
              <span className="text-blue-700 block text-[11px]">Vital Few Categories</span>
              <span className="text-base font-bold text-blue-900">{data.vital_few_categories?.length || 0}</span>
            </div>
            <div className="p-2.5 bg-slate-50 border border-slate-200 rounded-lg">
              <span className="text-slate-500 block text-[11px]">Date Filter Applied</span>
              <span className="text-xs font-semibold text-slate-800 truncate block">
                {startDate || endDate ? `${startDate || 'Earliest'} to ${endDate || 'Latest'}` : 'All Historical'}
              </span>
            </div>
          </div>

          {/* Dual-Axis Pareto Chart */}
          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart
                data={data.items}
                margin={{ top: 15, right: 25, bottom: 25, left: 0 }}
              >
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                <XAxis
                  dataKey="category"
                  tick={{ fontSize: 11, fill: "#475569" }}
                  interval={0}
                  angle={-15}
                  textAnchor="end"
                  height={45}
                />
                <YAxis
                  yAxisId="left"
                  tick={{ fontSize: 11, fill: "#475569" }}
                  allowDecimals={false}
                  label={{ value: "Frequency", angle: -90, position: "insideLeft", fontSize: 11, fill: "#64748b" }}
                />
                <YAxis
                  yAxisId="right"
                  orientation="right"
                  domain={[0, 100]}
                  unit="%"
                  tick={{ fontSize: 11, fill: "#475569" }}
                  label={{ value: "Cumulative %", angle: 90, position: "insideRight", fontSize: 11, fill: "#64748b" }}
                />
                <Tooltip content={<CustomTooltip />} />
                <ReferenceLine
                  yAxisId="right"
                  y={80}
                  stroke="#dc2626"
                  strokeDasharray="4 4"
                  strokeWidth={1.5}
                  label={{ value: "80% Cutoff", fill: "#dc2626", fontSize: 10, position: "top" }}
                />
                <Bar yAxisId="left" dataKey="count" radius={[4, 4, 0, 0]}>
                  {data.items.map((entry: any, index: number) => (
                    <Cell
                      key={`bar-${index}`}
                      fill={entry.is_vital_few ? "#2563eb" : "#94a3b8"}
                    />
                  ))}
                </Bar>
                <Line
                  yAxisId="right"
                  type="monotone"
                  dataKey="cumulative_percentage"
                  stroke="#dc2626"
                  strokeWidth={2.5}
                  dot={{ r: 4, fill: "#dc2626" }}
                  activeDot={{ r: 6 }}
                />
              </ComposedChart>
            </ResponsiveContainer>
          </div>

          {/* Vital Few Summary Bar */}
          <div className="p-3 bg-blue-50/50 border border-blue-100 rounded-lg flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-xs">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="font-bold text-blue-900">Vital Few (80% Focus):</span>
              {data.vital_few_categories?.map((vCat: string, idx: number) => (
                <span
                  key={idx}
                  className="px-2 py-0.5 bg-blue-100 text-blue-800 font-semibold rounded-full text-[11px]"
                >
                  {vCat}
                </span>
              ))}
            </div>
            <div className="text-[11px] text-slate-500">
              Deterministic tie-break applied (Count ↓, Name ↑)
            </div>
          </div>

          {/* Safety & Epistemic Disclaimer */}
          <div className="pt-2 border-t border-slate-100 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 text-[11px] text-slate-500">
            <div className="flex items-center gap-1.5 text-slate-600">
              <Info className="w-3.5 h-3.5 text-slate-400 shrink-0" />
              <span>
                {data.analysis_note}
              </span>
            </div>
            {onNavigate && (
              <button
                onClick={() => onNavigate("inspection")}
                className="text-blue-600 font-semibold hover:underline flex items-center gap-1 cursor-pointer shrink-0"
              >
                <span>View Full Quality Log</span>
                <ArrowRight className="w-3 h-3" />
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

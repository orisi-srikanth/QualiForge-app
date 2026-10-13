import React, { useEffect, useState } from "react";
import { api } from "../api";
import { ProductionBatch } from "../types";
import {
  PlusCircle, Upload, Camera, Activity, Play, Search,
  RefreshCw, CheckCircle2, Clock, AlertTriangle, Layers,
  FileSpreadsheet, ArrowRight, Eye, ShieldAlert, Cpu
} from "lucide-react";

interface Props {
  onNavigate: (page: string) => void;
  onSelectBatch?: (batchId: string) => void;
  onRunAnalysis?: (batchId: string) => void;
}

export const ProductionDashboard: React.FC<Props> = ({
  onNavigate,
  onSelectBatch,
  onRunAnalysis
}) => {
  const [batches, setBatches] = useState<ProductionBatch[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [filterShift, setFilterShift] = useState("");
  const [filterStatus, setFilterStatus] = useState("");

  const loadBatches = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getBatches();
      setBatches(Array.isArray(data) ? data : []);
    } catch (err: any) {
      setError(err?.message || "Failed to load production batches");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadBatches();
  }, []);

  // Filter batches
  const filteredBatches = batches.filter((b) => {
    const batchId = (b.batch_id || (b as any).batch_number || "").toLowerCase();
    const productId = (b.product_id || b.part_number || "").toLowerCase();
    const machineId = (b.machine_id || b.machine || "").toLowerCase();
    const query = searchQuery.toLowerCase();

    const matchesSearch =
      batchId.includes(query) ||
      productId.includes(query) ||
      machineId.includes(query);
    const matchesShift = !filterShift || b.shift === filterShift;
    const matchesStatus = !filterStatus || b.status === filterStatus;
    return matchesSearch && matchesShift && matchesStatus;
  });

  // Calculate real summary statistics from batches
  const totalBatches = batches.length;
  const inProgressBatches = batches.filter((b) => b.status === "IN_PROGRESS" || b.status === "ACTIVE").length;
  const holdBatches = batches.filter((b) => b.status === "QUALITY_HOLD" || b.status === "HELD").length;
  const conformingBatches = batches.filter((b) => b.status === "CONFORMING" || b.status === "COMPLETED").length;
  const totalProducedUnits = batches.reduce((sum, b) => sum + (b.quantity || 0), 0);

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* -------------------- OPERATIONAL CALLOUT -------------------- */}
      <div className="p-5 bg-gradient-to-r from-slate-900 to-slate-800 text-white rounded-2xl shadow-sm flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div>
          <span className="px-2.5 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-emerald-500/20 text-emerald-300 border border-emerald-500/40">
            Shop Floor Cell Operations
          </span>
          <h2 className="text-xl font-extrabold text-white mt-1.5">
            Production Team & Line Operator Workspace
          </h2>
          <p className="text-xs text-slate-300 mt-1 max-w-2xl leading-relaxed">
            Register new manufacturing lots, upload coordinate measuring machine (CMM) data, ingest machine telemetry,
            and submit part surface photography for automated multi-agent inspection.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2.5 shrink-0">
          <button
            onClick={() => onNavigate("batch-intake")}
            className="px-4 py-2.5 bg-blue-600 hover:bg-blue-500 text-white rounded-xl text-xs font-bold shadow-xs transition-all flex items-center gap-1.5 cursor-pointer"
          >
            <PlusCircle className="w-4 h-4" />
            <span>Register New Batch</span>
          </button>
          <button
            onClick={loadBatches}
            className="p-2.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-xl text-xs font-semibold border border-slate-700 transition-colors cursor-pointer"
            title="Refresh Batches"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin text-blue-400" : ""}`} />
          </button>
        </div>
      </div>

      {/* -------------------- A. PRIMARY ACTION TILES -------------------- */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <button
          onClick={() => onNavigate("batch-intake")}
          className="p-4 bg-white border border-slate-200 hover:border-blue-500 rounded-xl shadow-xs text-left group transition-all cursor-pointer"
        >
          <div className="w-9 h-9 rounded-lg bg-blue-50 text-blue-600 flex items-center justify-center mb-3 group-hover:bg-blue-600 group-hover:text-white transition-colors">
            <PlusCircle className="w-5 h-5" />
          </div>
          <div className="text-sm font-bold text-slate-900 group-hover:text-blue-600 transition-colors">
            Register Production Batch
          </div>
          <p className="text-[11px] text-slate-500 mt-1">
            8-step wizard for batch, machine, shift, measurements & telemetry.
          </p>
        </button>

        <button
          onClick={() => onNavigate("inspection")}
          className="p-4 bg-white border border-slate-200 hover:border-blue-500 rounded-xl shadow-xs text-left group transition-all cursor-pointer"
        >
          <div className="w-9 h-9 rounded-lg bg-indigo-50 text-indigo-600 flex items-center justify-center mb-3 group-hover:bg-indigo-600 group-hover:text-white transition-colors">
            <Upload className="w-5 h-5" />
          </div>
          <div className="text-sm font-bold text-slate-900 group-hover:text-blue-600 transition-colors">
            Upload CMM Measurements
          </div>
          <p className="text-[11px] text-slate-500 mt-1">
            Ingest inspection CSV/Excel files with automatic unit normalization.
          </p>
        </button>

        <button
          onClick={() => onNavigate("process-monitoring")}
          className="p-4 bg-white border border-slate-200 hover:border-blue-500 rounded-xl shadow-xs text-left group transition-all cursor-pointer"
        >
          <div className="w-9 h-9 rounded-lg bg-cyan-50 text-cyan-600 flex items-center justify-center mb-3 group-hover:bg-cyan-600 group-hover:text-white transition-colors">
            <Activity className="w-5 h-5" />
          </div>
          <div className="text-sm font-bold text-slate-900 group-hover:text-blue-600 transition-colors">
            Upload Process Telemetry
          </div>
          <p className="text-[11px] text-slate-500 mt-1">
            Stream high-frequency machine vibration and tool cycle logs.
          </p>
        </button>

        <button
          onClick={() => onNavigate("visual-inspection")}
          className="p-4 bg-white border border-slate-200 hover:border-blue-500 rounded-xl shadow-xs text-left group transition-all cursor-pointer"
        >
          <div className="w-9 h-9 rounded-lg bg-purple-50 text-purple-600 flex items-center justify-center mb-3 group-hover:bg-purple-600 group-hover:text-white transition-colors">
            <Camera className="w-5 h-5" />
          </div>
          <div className="text-sm font-bold text-slate-900 group-hover:text-blue-600 transition-colors">
            Upload Part Photos
          </div>
          <p className="text-[11px] text-slate-500 mt-1">
            AI surface defect classification and bounding box localization.
          </p>
        </button>
      </div>

      {/* -------------------- B. PRODUCTION SUMMARY ROW -------------------- */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div className="p-4 bg-white border border-slate-200 rounded-xl shadow-xs">
          <div className="text-xs font-semibold text-slate-500">Tracked Batches</div>
          <div className="text-2xl font-extrabold text-slate-900 mt-1">{totalBatches}</div>
          <div className="text-[11px] text-slate-500 mt-1">{totalProducedUnits.toLocaleString()} units produced</div>
        </div>

        <div className="p-4 bg-white border border-slate-200 rounded-xl shadow-xs">
          <div className="text-xs font-semibold text-slate-500">Active / In Progress</div>
          <div className="text-2xl font-extrabold text-blue-600 mt-1">{inProgressBatches}</div>
          <div className="text-[11px] text-slate-500 mt-1">Under shop floor processing</div>
        </div>

        <div className="p-4 bg-white border border-slate-200 rounded-xl shadow-xs">
          <div className="text-xs font-semibold text-slate-500">Quality Hold (Attention)</div>
          <div className="text-2xl font-extrabold text-amber-600 mt-1">{holdBatches}</div>
          <div className="text-[11px] text-amber-700 font-medium mt-1">Awaiting engineering sign-off</div>
        </div>

        <div className="p-4 bg-white border border-slate-200 rounded-xl shadow-xs">
          <div className="text-xs font-semibold text-slate-500">Conforming / Passed</div>
          <div className="text-2xl font-extrabold text-emerald-600 mt-1">{conformingBatches}</div>
          <div className="text-[11px] text-emerald-700 font-medium mt-1">Released for dispatch</div>
        </div>
      </div>

      {/* -------------------- C. BATCH MANAGEMENT TABLE -------------------- */}
      <div className="bg-white border border-slate-200 rounded-xl shadow-xs overflow-hidden">
        {/* Table Controls */}
        <div className="p-4 border-b border-slate-200 flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <Layers className="w-5 h-5 text-slate-600" />
            <h3 className="text-sm font-bold text-slate-900">Current Production Batches</h3>
            <span className="text-xs text-slate-500">({filteredBatches.length} items)</span>
          </div>

          <div className="flex flex-wrap items-center gap-2 text-xs">
            {/* Search Input */}
            <div className="relative">
              <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-2.5" />
              <input
                type="text"
                placeholder="Search batch, product, machine..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-8 pr-3 py-1.5 border border-slate-300 rounded-lg text-xs bg-slate-50 focus:outline-none focus:ring-1 focus:ring-blue-500 w-52 text-slate-800"
              />
            </div>

            {/* Shift Filter */}
            <select
              value={filterShift}
              onChange={(e) => setFilterShift(e.target.value)}
              className="px-2.5 py-1.5 border border-slate-300 rounded-lg text-xs bg-slate-50 text-slate-700 focus:outline-none"
            >
              <option value="">All Shifts</option>
              <option value="Morning">Morning</option>
              <option value="Evening">Evening</option>
              <option value="Night">Night</option>
            </select>

            {/* Status Filter */}
            <select
              value={filterStatus}
              onChange={(e) => setFilterStatus(e.target.value)}
              className="px-2.5 py-1.5 border border-slate-300 rounded-lg text-xs bg-slate-50 text-slate-700 focus:outline-none"
            >
              <option value="">All Statuses</option>
              <option value="IN_PROGRESS">In Progress</option>
              <option value="QUALITY_HOLD">Quality Hold</option>
              <option value="CONFORMING">Conforming</option>
            </select>
          </div>
        </div>

        {/* Table Content */}
        {loading ? (
          <div className="p-12 text-center text-xs text-slate-500 space-y-2">
            <RefreshCw className="w-6 h-6 animate-spin text-blue-600 mx-auto" />
            <div>Loading production batches...</div>
          </div>
        ) : filteredBatches.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 text-slate-600 font-semibold border-b border-slate-200">
                <tr>
                  <th className="py-3 px-4">Batch Number</th>
                  <th className="py-3 px-4">Product / Part</th>
                  <th className="py-3 px-4">Machine Cell</th>
                  <th className="py-3 px-4">Shift</th>
                  <th className="py-3 px-4">Quantity</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4 text-right">Available Next Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {filteredBatches.map((b) => {
                  const bId = b.batch_id || (b as any).batch_number || "BATCH-UNKNOWN";
                  const mId = b.machine_id || b.machine || "CNC-04";
                  return (
                    <tr key={bId} className="hover:bg-slate-50/70 transition-colors">
                      <td className="py-3 px-4 font-mono font-bold text-slate-900">
                        {bId}
                      </td>
                      <td className="py-3 px-4 font-medium text-slate-800">
                        {b.product_id || b.part_number}
                      </td>
                      <td className="py-3 px-4 font-mono text-slate-600">
                        {mId}
                      </td>
                      <td className="py-3 px-4 text-slate-600">
                        {b.shift}
                      </td>
                      <td className="py-3 px-4 font-mono text-slate-800 font-semibold">
                        {b.quantity?.toLocaleString() ?? 0} units
                      </td>
                      <td className="py-3 px-4">
                        <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                          b.status === "CONFORMING" || b.status === "COMPLETED"
                            ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
                            : b.status === "QUALITY_HOLD" || b.status === "HELD"
                            ? "bg-amber-50 text-amber-700 border border-amber-200"
                            : "bg-blue-50 text-blue-700 border border-blue-200"
                        }`}>
                          {b.status}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-right">
                        <div className="flex items-center justify-end gap-2">
                          <button
                            onClick={() => {
                              if (onSelectBatch) onSelectBatch(bId);
                              onNavigate("inspection");
                            }}
                            className="px-2.5 py-1 rounded bg-slate-100 hover:bg-slate-200 text-slate-700 font-medium transition-colors cursor-pointer"
                          >
                            Measurements
                          </button>
                          <button
                            onClick={() => {
                              if (onRunAnalysis) {
                                onRunAnalysis(bId);
                              } else {
                                if (onSelectBatch) onSelectBatch(bId);
                                onNavigate("batches");
                              }
                            }}
                            className="px-2.5 py-1 rounded bg-blue-600 hover:bg-blue-700 text-white font-medium transition-colors cursor-pointer flex items-center gap-1"
                          >
                            <Play className="w-3 h-3" />
                            <span>Run Analysis</span>
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="p-12 text-center text-xs text-slate-500 space-y-2">
            <Layers className="w-8 h-8 text-slate-400 mx-auto" />
            <div className="font-bold text-slate-800 text-sm">No Batches Found</div>
            <p>No production batches match your current search or filter criteria.</p>
            <button
              onClick={() => onNavigate("batch-intake")}
              className="mt-2 px-3 py-1.5 bg-blue-600 text-white rounded font-semibold cursor-pointer"
            >
              Register First Batch
            </button>
          </div>
        )}
      </div>

      {/* -------------------- D. RECENT UPLOADS & ACTION CENTER -------------------- */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Uploads Panel */}
        <div className="p-5 bg-white border border-slate-200 rounded-xl shadow-xs space-y-3">
          <div className="flex items-center justify-between border-b border-slate-100 pb-3">
            <div>
              <h3 className="text-sm font-bold text-slate-900">Recent File Uploads & Ingestion</h3>
              <p className="text-xs text-slate-500">Measurement sheets, telemetry logs, and part images</p>
            </div>
            <span className="text-xs font-mono text-slate-500">Live Ingest Status</span>
          </div>

          <div className="space-y-2 text-xs">
            {batches.length > 0 ? (
              <div className="p-4 bg-slate-50 border border-slate-200 rounded-lg text-slate-600 space-y-1">
                <div className="font-semibold text-slate-800">Production Ingestion Active</div>
                <div className="text-[11px] text-slate-500">
                  {batches.length} batch(es) registered in current shift schedule.
                </div>
              </div>
            ) : (
              <div className="p-6 text-center text-xs text-slate-400 bg-slate-50 rounded-lg border border-dashed border-slate-200">
                No inspection files or telemetry streams uploaded yet.
                <div className="mt-2">
                  <button
                    onClick={() => onNavigate("inspection")}
                    className="text-blue-600 font-semibold hover:underline cursor-pointer"
                  >
                    Open Measurement Intake &rarr;
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Action Center */}
        <div className="p-5 bg-white border border-slate-200 rounded-xl shadow-xs space-y-3">
          <div className="flex items-center justify-between border-b border-slate-100 pb-3">
            <div>
              <h3 className="text-sm font-bold text-slate-900">Production Action Center</h3>
              <p className="text-xs text-slate-500">Assigned operator tasks and inspection procedures</p>
            </div>
            <span className="text-xs font-mono text-slate-500">Standard Work</span>
          </div>

          <div className="space-y-2 text-xs">
            {holdBatches > 0 ? (
              <div className="p-3 rounded-lg border border-amber-200 bg-amber-50/60 flex items-center justify-between">
                <div>
                  <div className="font-bold text-amber-900">Active Quality Hold ({holdBatches} Lots)</div>
                  <div className="text-amber-800 text-[11px]">Segregate held lot parts pending Quality Engineer review.</div>
                </div>
                <button
                  onClick={() => onNavigate("batches")}
                  className="px-2.5 py-1 bg-amber-600 hover:bg-amber-700 text-white rounded font-medium text-xs shrink-0 cursor-pointer"
                >
                  View Held Lots
                </button>
              </div>
            ) : (
              <div className="p-3 rounded-lg border border-slate-200 bg-slate-50/60 flex items-center justify-between">
                <div>
                  <div className="font-bold text-slate-900">Machinery Baseline Check</div>
                  <div className="text-slate-500 text-[11px]">All 4 CNC machining cells operating within normal baseline limits.</div>
                </div>
                <button
                  onClick={() => onNavigate("process-monitoring")}
                  className="px-2.5 py-1 bg-slate-200 hover:bg-slate-300 text-slate-800 rounded font-medium text-xs shrink-0 cursor-pointer"
                >
                  Telemetry
                </button>
              </div>
            )}

            <div className="p-3 rounded-lg border border-slate-200 bg-slate-50/60 flex items-center justify-between">
              <div>
                <div className="font-bold text-slate-900">Standard Production Work</div>
                <div className="text-slate-500 text-[11px]">Follow SOP-044 Tool Life and SOP-055 Visual Inspection standards.</div>
              </div>
              <button
                onClick={() => onNavigate("knowledge-base")}
                className="px-2.5 py-1 bg-slate-100 hover:bg-slate-200 text-slate-700 border border-slate-300 rounded font-medium text-xs shrink-0 cursor-pointer"
              >
                View SOPs
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

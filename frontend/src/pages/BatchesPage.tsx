import React, { useEffect, useState } from "react";
import { api } from "../api";
import { ProductionBatch, ProductSpec } from "../types";
import { CertaintyBadge } from "../components/CertaintyBadge";
import {
  Layers,
  AlertCircle,
  CheckCircle,
  Clock,
  Plus,
  Play,
  Edit2,
  Trash2,
  Filter,
  RefreshCw,
  Search,
  User,
  Cpu,
  Calendar,
  Sparkles,
  ShieldCheck,
  X,
  AlertTriangle,
  ArrowRight
} from "lucide-react";

interface Props {
  onNavigate: (page: string) => void;
  onSelectWorkflow?: (workflowId: string) => void;
}

type Role = "admin" | "quality_engineer" | "operator";

interface BatchFormData {
  batch_number: string;
  product_id: string;
  machine_id: string;
  shift: string;
  quantity: number;
  start_time: string;
  end_time: string;
  material_lot: string;
  operator_ref: string;
  status: string;
}

const INITIAL_FORM: BatchFormData = {
  batch_number: "",
  product_id: "",
  machine_id: "",
  shift: "Morning",
  quantity: 500,
  start_time: new Date().toISOString().slice(0, 16),
  end_time: "",
  material_lot: "",
  operator_ref: "",
  status: "IN_PROGRESS",
};

export const BatchesPage: React.FC<Props> = ({ onNavigate, onSelectWorkflow }) => {
  const [batches, setBatches] = useState<ProductionBatch[]>([]);
  const [products, setProducts] = useState<ProductSpec[]>([]);
  const [machines, setMachines] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  // RBAC Persona State
  const [activeRole, setActiveRole] = useState<Role>("quality_engineer");
  const [roleTokens, setRoleTokens] = useState<Record<Role, string>>({
    admin: "",
    quality_engineer: "",
    operator: "",
  });

  // Filter & Search State
  const [searchQuery, setSearchQuery] = useState("");
  const [filterProduct, setFilterProduct] = useState("");
  const [filterMachine, setFilterMachine] = useState("");
  const [filterShift, setFilterShift] = useState("");

  // Modal State
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [modalMode, setModalMode] = useState<"create" | "edit">("create");
  const [formData, setFormData] = useState<BatchFormData>(INITIAL_FORM);
  const [formErrors, setFormErrors] = useState<Record<string, string>>({});
  const [submitting, setSubmitting] = useState(false);

  // Alerts & Notifications
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  // AI Workflow Execution State
  const [runningAnalysisBatch, setRunningAnalysisBatch] = useState<string | null>(null);
  const [analysisResult, setAnalysisResult] = useState<any | null>(null);

  // Load all data
  const loadData = async () => {
    try {
      setLoading(true);
      const [batchesRes, prodsRes, machsRes] = await Promise.all([
        api.getBatches(),
        api.getProducts(),
        api.getMachines(),
      ]);

      setBatches(batchesRes);
      setProducts(prodsRes);
      setMachines(machsRes);

      // Default product and machine for new batches
      if (prodsRes.length > 0 && !formData.product_id) {
        setFormData((prev) => ({
          ...prev,
          product_id: prodsRes[0].product_id || prodsRes[0].part_number,
        }));
      }
      if (machsRes.length > 0 && !formData.machine_id) {
        setFormData((prev) => ({
          ...prev,
          machine_id: machsRes[0].code || machsRes[0].machine_id,
        }));
      }
    } catch (err: any) {
      setErrorMessage(err.message || "Failed to load data from server");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  // Validation function
  const validateForm = (): boolean => {
    const errors: Record<string, string> = {};

    if (!formData.batch_number.trim()) {
      errors.batch_number = "Batch number is required.";
    }

    if (!formData.product_id.trim()) {
      errors.product_id = "Product selection is required.";
    }

    if (!formData.machine_id.trim()) {
      errors.machine_id = "Machine selection is required.";
    }

    if (!formData.shift.trim()) {
      errors.shift = "Shift selection is required.";
    }

    if (formData.quantity === undefined || formData.quantity === null || formData.quantity <= 0) {
      errors.quantity = "Quantity must be strictly positive (greater than 0).";
    }

    if (!formData.material_lot.trim()) {
      errors.material_lot = "Material lot is required.";
    }

    if (!formData.start_time) {
      errors.start_time = "Production start time is required.";
    }

    if (formData.start_time && formData.end_time) {
      const start = new Date(formData.start_time).getTime();
      const end = new Date(formData.end_time).getTime();
      if (end < start) {
        errors.end_time = "End time cannot be earlier than start time.";
      }
    }

    setFormErrors(errors);
    return Object.keys(errors).length === 0;
  };

  // Open Create Modal
  const handleOpenCreate = () => {
    const defaultProduct = products.length > 0 ? (products[0].product_id || products[0].part_number) : "";
    const defaultMachine = machines.length > 0 ? (machines[0].code || machines[0].machine_id) : "";
    const now = new Date();
    const isoNow = new Date(now.getTime() - now.getTimezoneOffset() * 60000).toISOString().slice(0, 16);

    setFormData({
      batch_number: `BATCH-${Math.floor(1000 + Math.random() * 9000)}`,
      product_id: defaultProduct,
      machine_id: defaultMachine,
      shift: "Morning",
      quantity: 500,
      start_time: isoNow,
      end_time: "",
      material_lot: `LOT-${new Date().getFullYear()}-STEEL-${Math.floor(10 + Math.random() * 89)}`,
      operator_ref: "OP-401 (Alex Vance)",
      status: "IN_PROGRESS",
    });
    setFormErrors({});
    setModalMode("create");
    setIsModalOpen(true);
  };

  // Open Edit Modal
  const handleOpenEdit = (b: ProductionBatch) => {
    // Format dates to YYYY-MM-DDTHH:mm if available
    let sTime = "";
    if (b.start_time) {
      try {
        const d = new Date(b.start_time);
        sTime = new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 16);
      } catch {
        sTime = b.start_time.slice(0, 16);
      }
    }

    let eTime = "";
    if (b.end_time) {
      try {
        const d = new Date(b.end_time);
        eTime = new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 16);
      } catch {
        eTime = b.end_time.slice(0, 16);
      }
    }

    setFormData({
      batch_number: b.batch_id,
      product_id: b.product_id || b.part_number || "",
      machine_id: b.machine_id || b.machine || "",
      shift: b.shift,
      quantity: b.quantity,
      start_time: sTime,
      end_time: eTime,
      material_lot: b.material_lot,
      operator_ref: b.operator_ref || b.operator || "",
      status: b.status || "IN_PROGRESS",
    });
    setFormErrors({});
    setModalMode("edit");
    setIsModalOpen(true);
  };

  // Submit Modal
  const handleSubmitModal = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!validateForm()) return;

    try {
      setSubmitting(true);
      setErrorMessage(null);
      const token = roleTokens[activeRole];

      const payload = {
        batch_number: formData.batch_number.trim(),
        product_id: formData.product_id.trim(),
        machine_id: formData.machine_id.trim(),
        shift: formData.shift.trim(),
        quantity: Number(formData.quantity),
        start_time: formData.start_time ? new Date(formData.start_time).toISOString() : undefined,
        end_time: formData.end_time ? new Date(formData.end_time).toISOString() : undefined,
        material_lot: formData.material_lot.trim(),
        operator_ref: formData.operator_ref.trim() || undefined,
        status: formData.status,
      };

      if (modalMode === "create") {
        await api.createBatch(payload, token);
        setSuccessMessage(`Successfully registered batch ${payload.batch_number}`);
      } else {
        await api.updateBatch(payload.batch_number, payload, token);
        setSuccessMessage(`Successfully updated batch ${payload.batch_number}`);
      }

      setIsModalOpen(false);
      // Reload batches
      const updated = await api.getBatches();
      setBatches(updated);
    } catch (err: any) {
      setErrorMessage(err.message || "Operation failed.");
    } finally {
      setSubmitting(false);
    }
  };

  // Delete Batch
  const handleDeleteBatch = async (batchId: string) => {
    if (!window.confirm(`Are you sure you want to delete batch ${batchId}? This cannot be undone.`)) {
      return;
    }

    try {
      setErrorMessage(null);
      const token = roleTokens[activeRole];
      await api.deleteBatch(batchId, token);
      setSuccessMessage(`Batch ${batchId} permanently deleted.`);
      const updated = await api.getBatches();
      setBatches(updated);
    } catch (err: any) {
      setErrorMessage(err.message || "Failed to delete batch.");
    }
  };

  // Success / error flash state for row
  const [flashSuccessBatch, setFlashSuccessBatch] = useState<string | null>(null);
  const [flashErrorBatch, setFlashErrorBatch] = useState<string | null>(null);

  // Run AI Analysis Workflow
  const handleRunAiAnalysis = async (batchId: string) => {
    try {
      setRunningAnalysisBatch(batchId);
      setErrorMessage(null);
      const result = await api.runOrchestratedPipeline(batchId);
      setAnalysisResult({
        batchId,
        workflowId: result.workflow_id,
        currentStep: result.current_agent || "Analysis Completed",
        certainty: "Model Prediction",
        disposition: result.status || "EVALUATED",
        timestamp: new Date().toLocaleTimeString(),
      });
      setSuccessMessage(`Analysis completed successfully for batch ${batchId}. Navigating to AI Review...`);
      setFlashSuccessBatch(batchId);
      setTimeout(() => setFlashSuccessBatch(null), 1200);
      // Refresh list to pick up any status changes
      const updated = await api.getBatches();
      setBatches(updated);

      if (result?.workflow_id) {
        setTimeout(() => {
          if (onSelectWorkflow) {
            onSelectWorkflow(result.workflow_id);
          } else {
            onNavigate("ai-review");
          }
        }, 700);
      }
    } catch (err: any) {
      setFlashErrorBatch(batchId);
      setTimeout(() => setFlashErrorBatch(null), 1200);
      setErrorMessage("Analysis could not be completed. Please try again.");
    } finally {
      setRunningAnalysisBatch(null);
    }
  };

  const handleInspectBatchAnalysis = async (batchId: string) => {
    try {
      const wf = await api.getLatestWorkflowForBatch(batchId);
      if (wf?.workflow_id) {
        if (onSelectWorkflow) {
          onSelectWorkflow(wf.workflow_id);
        } else {
          onNavigate("ai-review");
        }
        return;
      }
    } catch {
      // If no workflow found yet, run analysis
    }
    handleRunAiAnalysis(batchId);
  };

  // Filter batches locally for search and selected dropdowns
  const filteredBatches = batches.filter((b) => {
    const q = searchQuery.toLowerCase();
    const matchSearch =
      !q ||
      b.batch_id.toLowerCase().includes(q) ||
      (b.part_number && b.part_number.toLowerCase().includes(q)) ||
      (b.material_lot && b.material_lot.toLowerCase().includes(q)) ||
      (b.operator && b.operator.toLowerCase().includes(q));

    const matchProd = !filterProduct || b.part_number === filterProduct || b.product_id === filterProduct;
    const matchMach = !filterMachine || b.machine === filterMachine || b.machine_id === filterMachine;
    const matchShift = !filterShift || b.shift.toLowerCase().includes(filterShift.toLowerCase());

    return matchSearch && matchProd && matchMach && matchShift;
  });

  return (
    <div className="space-y-6">
      {/* Header and Persona Controls */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h2 className="text-[26px] font-bold text-slate-900 leading-tight">Production Batches & Traceability</h2>
          <p className="text-[14px] text-slate-500 mt-1">
            Create, track and review production batches with full traceability.
          </p>
        </div>

        <div className="flex items-center gap-3 flex-wrap">
          {/* Persona RBAC Switcher */}
          <div className="segmented-control">
            <span className="text-[12px] font-semibold text-slate-500 px-2 flex items-center gap-1.5 whitespace-nowrap">
              <ShieldCheck className="w-3.5 h-3.5 text-slate-400" />
              Role:
            </span>
            {(["quality_engineer", "operator", "admin"] as Role[]).map((r) => (
              <button
                key={r}
                type="button"
                onClick={() => setActiveRole(r)}
                className={`segmented-button ${activeRole === r ? "active" : ""}`}
              >
                {r === "quality_engineer" ? "Quality Engineer" : r === "operator" ? "Operator" : "Admin"}
              </button>
            ))}
          </div>

          {/* New Batch Button */}
          <button
            onClick={handleOpenCreate}
            className="btn-primary"
          >
            <Plus className="w-4 h-4" />
            <span>New Batch</span>
          </button>

          {/* Refresh Button */}
          <button
            onClick={loadData}
            title="Refresh Batches"
            className="btn-secondary !p-2 !h-[40px] !w-[40px] flex items-center justify-center"
          >
            <RefreshCw className={`w-4 h-4 text-slate-600 ${loading ? "animate-spin" : ""}`} />
          </button>
        </div>
      </div>

      {/* Global Toast / Feedback Messages */}
      {errorMessage && (
        <div className="p-3.5 bg-rose-50 border border-rose-200 rounded-lg text-rose-800 text-[13.5px] flex items-center justify-between shadow-2xs">
          <div className="flex items-center gap-2.5">
            <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
            <span>{errorMessage}</span>
          </div>
          <button onClick={() => setErrorMessage(null)} className="text-rose-500 hover:text-rose-700">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {successMessage && (
        <div className="p-3.5 bg-emerald-50 border border-emerald-200 rounded-lg text-emerald-800 text-[13.5px] flex items-center justify-between shadow-2xs">
          <div className="flex items-center gap-2.5">
            <CheckCircle className="w-4 h-4 text-emerald-600 shrink-0" />
            <span>{successMessage}</span>
          </div>
          <button onClick={() => setSuccessMessage(null)} className="text-emerald-500 hover:text-emerald-700">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Filter and Search Bar Styled as Table Control Buttons */}
      <div className="bg-white border border-[#D0D5DD] rounded-xl p-3 shadow-2xs flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2 flex-1 min-w-[260px]">
          <div className="relative w-full max-w-sm">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
            <input
              type="text"
              placeholder="Search batch, lot, operator..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-9 pr-3 py-2 bg-slate-50/70 hover:bg-white focus:bg-white border border-slate-300 focus:border-blue-500 rounded-lg text-xs text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-100 transition-all shadow-2xs font-medium"
            />
          </div>
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          {/* Product Filter Button */}
          <div className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-50/90 hover:bg-slate-100/80 border border-slate-300 rounded-lg shadow-2xs transition-all">
            <Filter className="w-3.5 h-3.5 text-blue-600 shrink-0" />
            <span className="text-xs font-semibold text-slate-600">Product:</span>
            <select
              value={filterProduct}
              onChange={(e) => setFilterProduct(e.target.value)}
              className="bg-transparent text-xs font-bold text-slate-800 focus:outline-none cursor-pointer"
            >
              <option value="">All Products</option>
              {products.map((p) => (
                <option key={p.product_id} value={p.part_number}>
                  {p.part_number} ({p.name})
                </option>
              ))}
            </select>
          </div>

          {/* Machine Filter Button */}
          <div className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-50/90 hover:bg-slate-100/80 border border-slate-300 rounded-lg shadow-2xs transition-all">
            <Cpu className="w-3.5 h-3.5 text-indigo-600 shrink-0" />
            <span className="text-xs font-semibold text-slate-600">Machine:</span>
            <select
              value={filterMachine}
              onChange={(e) => setFilterMachine(e.target.value)}
              className="bg-transparent text-xs font-bold text-slate-800 focus:outline-none cursor-pointer"
            >
              <option value="">All Machines</option>
              {machines.map((m) => (
                <option key={m.code || m.machine_id} value={m.code || m.machine_id}>
                  {m.code || m.machine_id} ({m.type || m.name})
                </option>
              ))}
            </select>
          </div>

          {/* Shift Filter Button */}
          <div className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-50/90 hover:bg-slate-100/80 border border-slate-300 rounded-lg shadow-2xs transition-all">
            <Clock className="w-3.5 h-3.5 text-amber-600 shrink-0" />
            <span className="text-xs font-semibold text-slate-600">Shift:</span>
            <select
              value={filterShift}
              onChange={(e) => setFilterShift(e.target.value)}
              className="bg-transparent text-xs font-bold text-slate-800 focus:outline-none cursor-pointer"
            >
              <option value="">All Shifts</option>
              <option value="Morning">Morning</option>
              <option value="Evening">Evening</option>
              <option value="Night">Night</option>
            </select>
          </div>

          {(searchQuery || filterProduct || filterMachine || filterShift) && (
            <button
              onClick={() => {
                setSearchQuery("");
                setFilterProduct("");
                setFilterMachine("");
                setFilterShift("");
              }}
              className="px-3 py-1.5 bg-blue-50 hover:bg-blue-100 text-blue-700 border border-blue-200 rounded-lg text-xs font-bold cursor-pointer transition-colors shadow-2xs"
            >
              Reset Filters
            </button>
          )}
        </div>
      </div>

      {/* Production Batches Table */}
      <div className="table-container">
        <div className="px-5 py-3.5 border-b border-[#E3E8EF] bg-[#F4F6FA] flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Layers className="w-4 h-4 text-slate-600" />
            <span className="text-[16px] font-bold text-[#101828]">
              Batches Registry ({filteredBatches.length})
            </span>
          </div>
          <span className="text-[13px] text-[#475467]">IATF 16949 Section 8.5.2 Lot Traceability</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left">
            <thead className="table-header">
              <tr>
                <th className="table-header-cell">Batch ID</th>
                <th className="table-header-cell">Product</th>
                <th className="table-header-cell">Machine</th>
                <th className="table-header-cell">Shift</th>
                <th className="table-header-cell">Quantity</th>
                <th className="table-header-cell">Production Times</th>
                <th className="table-header-cell">Material Lot</th>
                <th className="table-header-cell">Operator / Ref</th>
                <th className="table-header-cell">Status</th>
                <th className="table-header-cell text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#EEF1F5]">
              {filteredBatches.map((b) => {
                const isHold = b.status === "QUALITY_HOLD";
                const isCompleted = b.status === "COMPLETED";
                const isRunning = runningAnalysisBatch === b.batch_id;
                const isSuccessFlash = flashSuccessBatch === b.batch_id;
                const isErrorFlash = flashErrorBatch === b.batch_id;

                const friendlyStatus = isHold ? "Quality Hold" : isCompleted ? "Conforming" : "In Progress";
                const pillClass = isHold ? "status-pill danger" : isCompleted ? "status-pill success" : "status-pill info";

                return (
                  <tr
                    key={b.batch_id}
                    className={`table-row ${isSuccessFlash ? "row-flash-success" : ""} ${isErrorFlash ? "row-flash-error animate-shake" : ""} ${isRunning ? "row-processing" : ""}`}
                  >
                    {/* Batch ID */}
                    <td className="px-4 py-3.5 font-semibold">
                      <span
                        onClick={() => handleInspectBatchAnalysis(b.batch_id)}
                        className="batch-link font-tabular cursor-pointer hover:underline text-blue-600 hover:text-blue-800"
                        title="Click to view full AI execution trace and inspection findings"
                      >
                        {b.batch_id}
                      </span>
                    </td>

                    {/* Product */}
                    <td className="px-4 py-3.5">
                      <div className="font-semibold text-slate-900 leading-tight">{b.part_number}</div>
                      <div className="text-[13px] text-[#475467] truncate max-w-[180px]">{b.material || "Precision Component"}</div>
                    </td>

                    {/* Machine */}
                    <td className="px-4 py-3.5">
                      <span className="machine-chip">
                        {b.machine}
                      </span>
                    </td>

                    {/* Shift */}
                    <td className="px-4 py-3.5 font-medium text-slate-700 whitespace-nowrap">
                      {b.shift}
                    </td>

                    {/* Quantity */}
                    <td className="px-4 py-3.5 font-tabular font-semibold text-slate-800 whitespace-nowrap">
                      {b.quantity} pcs
                    </td>

                    {/* Production Times */}
                    <td className="px-4 py-3.5 text-[13px] text-slate-600 whitespace-nowrap">
                      <div className="flex items-center gap-1.5 text-slate-700 font-tabular">
                        <Clock className="w-3.5 h-3.5 text-emerald-600" />
                        <span>{b.start_time || "Not Set"}</span>
                      </div>
                      {b.end_time && (
                        <div className="flex items-center gap-1.5 text-slate-400 mt-0.5 font-tabular">
                          <Clock className="w-3.5 h-3.5 text-slate-400" />
                          <span>{b.end_time}</span>
                        </div>
                      )}
                    </td>

                    {/* Material Lot */}
                    <td className="px-4 py-3.5 font-mono text-[13px] text-slate-600 whitespace-nowrap">
                      {b.material_lot}
                    </td>

                    {/* Operator / Process Ref */}
                    <td className="px-4 py-3.5 text-slate-700">
                      {b.operator || b.operator_ref ? (
                        <div className="flex items-center gap-1.5 text-[13px] whitespace-nowrap">
                          <User className="w-3.5 h-3.5 text-slate-400" />
                          <span>{b.operator || b.operator_ref}</span>
                        </div>
                      ) : (
                        <span className="text-slate-400 italic text-[12.5px]">None</span>
                      )}
                    </td>

                    {/* Status Badge */}
                    <td className="px-4 py-3.5 whitespace-nowrap">
                      <span className={pillClass}>
                        {isHold ? (
                          <AlertCircle className="w-3.5 h-3.5" />
                        ) : isCompleted ? (
                          <CheckCircle className="w-3.5 h-3.5" />
                        ) : (
                          <Clock className="w-3.5 h-3.5" />
                        )}
                        <span>{friendlyStatus}</span>
                      </span>
                    </td>

                    {/* Actions */}
                    <td className="px-4 py-3.5 text-right whitespace-nowrap">
                      <div className="flex items-center justify-end gap-2">
                        {/* Run Analysis Button */}
                        <button
                          onClick={() => handleRunAiAnalysis(b.batch_id)}
                          disabled={isRunning}
                          className="btn-row-action"
                          title="Run quality inspection and analysis"
                        >
                          {isRunning ? (
                            <>
                              <span className="w-3.5 h-3.5 border-2 border-[#2563EB] border-t-transparent rounded-full animate-spin shrink-0" />
                              <span>Analyzing...</span>
                            </>
                          ) : (
                            <>
                              <Play className="w-3.5 h-3.5 fill-[#1D4ED8]" />
                              <span>Run Analysis</span>
                            </>
                          )}
                        </button>

                        {/* Edit Button */}
                        <button
                          onClick={() => handleOpenEdit(b)}
                          className="btn-icon edit"
                          title="Edit Batch"
                        >
                          <Edit2 className="w-4 h-4" />
                        </button>

                        {/* Delete Button (Allowed for Admin) */}
                        <button
                          onClick={() => handleDeleteBatch(b.batch_id)}
                          className="btn-icon delete"
                          title={activeRole === "admin" ? "Delete Batch" : "Delete Batch (Admin only)"}
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}

              {filteredBatches.length === 0 && (
                <tr>
                  <td colSpan={10} className="px-6 py-10 text-center text-slate-400 text-[14px]">
                    No matching production batches found.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Modal: Create / Edit Batch with 8 Core Fields */}
      {isModalOpen && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-xl shadow-xl max-w-2xl w-full overflow-hidden border border-[#E3E8EF] animate-in fade-in zoom-in-95 duration-150">
            <div className="px-6 py-4 border-b border-[#E3E8EF] bg-[#F4F6FA] flex items-center justify-between">
              <div>
                <h3 className="text-[16px] font-bold text-[#101828]">
                  {modalMode === "create" ? "Register New Production Batch" : `Edit Batch: ${formData.batch_number}`}
                </h3>
                <p className="text-[13px] text-[#475467] mt-0.5">
                  Enter batch details and production parameters.
                </p>
              </div>
              <button
                onClick={() => setIsModalOpen(false)}
                className="text-slate-400 hover:text-slate-600 p-1.5 rounded-lg hover:bg-slate-100 transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleSubmitModal} className="p-6 space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Batch Number */}
                <div>
                  <label className="block text-[13px] font-semibold text-slate-700 mb-1">
                    Batch Number <span className="text-rose-500">*</span>
                  </label>
                  <input
                    type="text"
                    disabled={modalMode === "edit"}
                    value={formData.batch_number}
                    onChange={(e) => setFormData({ ...formData, batch_number: e.target.value })}
                    placeholder="e.g. BATCH-0245"
                    className={`w-full px-3 py-2 border rounded-lg text-[13.5px] font-mono ${
                      formErrors.batch_number ? "border-rose-400 bg-rose-50/50" : "border-[#D0D5DD]"
                    }`}
                  />
                  {formErrors.batch_number && (
                    <p className="text-[11.5px] text-rose-600 mt-1">{formErrors.batch_number}</p>
                  )}
                </div>

                {/* Product */}
                <div>
                  <label className="block text-[13px] font-semibold text-slate-700 mb-1">
                    Product (Part Number) <span className="text-rose-500">*</span>
                  </label>
                  <select
                    value={formData.product_id}
                    onChange={(e) => setFormData({ ...formData, product_id: e.target.value })}
                    className={`w-full px-3 py-2 border rounded-lg text-[13.5px] ${
                      formErrors.product_id ? "border-rose-400 bg-rose-50/50" : "border-[#D0D5DD]"
                    }`}
                  >
                    <option value="">-- Select Configured Product --</option>
                    {products.map((p) => (
                      <option key={p.product_id} value={p.product_id || p.part_number}>
                        {p.part_number} — {p.name}
                      </option>
                    ))}
                  </select>
                  {formErrors.product_id && (
                    <p className="text-[11.5px] text-rose-600 mt-1">{formErrors.product_id}</p>
                  )}
                </div>

                {/* Machine */}
                <div>
                  <label className="block text-[13px] font-semibold text-slate-700 mb-1">
                    Manufacturing Machine <span className="text-rose-500">*</span>
                  </label>
                  <select
                    value={formData.machine_id}
                    onChange={(e) => setFormData({ ...formData, machine_id: e.target.value })}
                    className={`w-full px-3 py-2 border rounded-lg text-[13.5px] ${
                      formErrors.machine_id ? "border-rose-400 bg-rose-50/50" : "border-[#D0D5DD]"
                    }`}
                  >
                    <option value="">-- Select Configured Machine --</option>
                    {machines.map((m) => (
                      <option key={m.code || m.machine_id} value={m.code || m.machine_id}>
                        {m.code || m.machine_id} — {m.type || m.name} ({m.location || m.cell || "Floor"})
                      </option>
                    ))}
                  </select>
                  {formErrors.machine_id && (
                    <p className="text-[11.5px] text-rose-600 mt-1">{formErrors.machine_id}</p>
                  )}
                </div>

                {/* Shift */}
                <div>
                  <label className="block text-[13px] font-semibold text-slate-700 mb-1">
                    Production Shift <span className="text-rose-500">*</span>
                  </label>
                  <select
                    value={formData.shift}
                    onChange={(e) => setFormData({ ...formData, shift: e.target.value })}
                    className={`w-full px-3 py-2 border rounded-lg text-[13.5px] ${
                      formErrors.shift ? "border-rose-400 bg-rose-50/50" : "border-[#D0D5DD]"
                    }`}
                  >
                    <option value="Morning">Morning Shift (06:00 - 14:00)</option>
                    <option value="Evening">Evening Shift (14:00 - 22:00)</option>
                    <option value="Night">Night Shift (22:00 - 06:00)</option>
                  </select>
                  {formErrors.shift && (
                    <p className="text-[11.5px] text-rose-600 mt-1">{formErrors.shift}</p>
                  )}
                </div>

                {/* Quantity */}
                <div>
                  <label className="block text-[13px] font-semibold text-slate-700 mb-1">
                    Batch Quantity (pcs) <span className="text-rose-500">*</span>
                  </label>
                  <input
                    type="number"
                    min="1"
                    step="1"
                    value={formData.quantity}
                    onChange={(e) => setFormData({ ...formData, quantity: parseInt(e.target.value) || 0 })}
                    placeholder="e.g. 500"
                    className={`w-full px-3 py-2 border rounded-lg text-[13.5px] font-tabular ${
                      formErrors.quantity ? "border-rose-400 bg-rose-50/50" : "border-[#D0D5DD]"
                    }`}
                  />
                  {formErrors.quantity && (
                    <p className="text-[11.5px] text-rose-600 mt-1">{formErrors.quantity}</p>
                  )}
                </div>

                {/* Production Start Time */}
                <div>
                  <label className="block text-[13px] font-semibold text-slate-700 mb-1">
                    Production Start Time <span className="text-rose-500">*</span>
                  </label>
                  <input
                    type="datetime-local"
                    value={formData.start_time}
                    onChange={(e) => setFormData({ ...formData, start_time: e.target.value })}
                    className={`w-full px-3 py-2 border rounded-lg text-[13.5px] font-tabular ${
                      formErrors.start_time ? "border-rose-400 bg-rose-50/50" : "border-[#D0D5DD]"
                    }`}
                  />
                  {formErrors.start_time && (
                    <p className="text-[11.5px] text-rose-600 mt-1">{formErrors.start_time}</p>
                  )}
                </div>

                {/* Production End Time */}
                <div>
                  <label className="block text-[13px] font-semibold text-slate-700 mb-1">
                    Production End Time <span className="text-slate-400 font-normal">(Optional)</span>
                  </label>
                  <input
                    type="datetime-local"
                    value={formData.end_time}
                    onChange={(e) => setFormData({ ...formData, end_time: e.target.value })}
                    className={`w-full px-3 py-2 border rounded-lg text-[13.5px] font-tabular ${
                      formErrors.end_time ? "border-rose-400 bg-rose-50/50" : "border-[#D0D5DD]"
                    }`}
                  />
                  {formErrors.end_time && (
                    <p className="text-[11.5px] text-rose-600 mt-1">{formErrors.end_time}</p>
                  )}
                </div>

                {/* Material Lot */}
                <div>
                  <label className="block text-[13px] font-semibold text-slate-700 mb-1">
                    Material Heat / Lot Number <span className="text-rose-500">*</span>
                  </label>
                  <input
                    type="text"
                    value={formData.material_lot}
                    onChange={(e) => setFormData({ ...formData, material_lot: e.target.value })}
                    placeholder="e.g. LOT-2026-STEEL-44"
                    className={`w-full px-3 py-2 border rounded-lg text-[13.5px] font-mono ${
                      formErrors.material_lot ? "border-rose-400 bg-rose-50/50" : "border-[#D0D5DD]"
                    }`}
                  />
                  {formErrors.material_lot && (
                    <p className="text-[11.5px] text-rose-600 mt-1">{formErrors.material_lot}</p>
                  )}
                </div>

                {/* Operator / Process Reference */}
                <div>
                  <label className="block text-[13px] font-semibold text-slate-700 mb-1">
                    Operator / Process Reference <span className="text-slate-400 font-normal">(Optional)</span>
                  </label>
                  <input
                    type="text"
                    value={formData.operator_ref}
                    onChange={(e) => setFormData({ ...formData, operator_ref: e.target.value })}
                    placeholder="e.g. OP-782 (Alex Vance)"
                    className="w-full px-3 py-2 border border-[#D0D5DD] rounded-lg text-[13.5px]"
                  />
                  <p className="text-[11px] text-slate-400 mt-1">Accepted empty if not applicable.</p>
                </div>

                {/* Status */}
                <div>
                  <label className="block text-[13px] font-semibold text-slate-700 mb-1">
                    Initial Batch Status
                  </label>
                  <select
                    value={formData.status}
                    onChange={(e) => setFormData({ ...formData, status: e.target.value })}
                    className="w-full px-3 py-2 border border-[#D0D5DD] rounded-lg text-[13.5px]"
                  >
                    <option value="IN_PROGRESS">In Progress</option>
                    <option value="COMPLETED">Completed</option>
                    <option value="QUALITY_HOLD">Quality Hold</option>
                  </select>
                </div>
              </div>

              <div className="pt-4 border-t border-[#E3E8EF] flex items-center justify-between">
                <div className="text-[12px] text-[#475467]">
                  Acting as: <span className="font-semibold text-slate-700 capitalize">{activeRole.replace('_', ' ')}</span>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => setIsModalOpen(false)}
                    className="btn-secondary"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={submitting}
                    className="btn-primary"
                  >
                    {submitting ? "Saving..." : modalMode === "create" ? "Register Batch" : "Save Changes"}
                  </button>
                </div>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

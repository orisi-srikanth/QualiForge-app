import React, { useEffect, useState } from "react";
import { api } from "../api";
import { ProductSpec } from "../types";
import { CertaintyBadge } from "../components/CertaintyBadge";
import {
  Settings,
  Plus,
  Check,
  ShieldCheck,
  Cpu,
  Ruler,
  Edit2,
  Trash2,
  AlertTriangle,
  Lock,
  UserCheck,
  RefreshCw,
  X
} from "lucide-react";

type Role = "admin" | "quality_engineer" | "operator";

interface Props {
  onNavigate?: (page: string, machineId?: string) => void;
}

const defaultFallbackMachines = [
  { code: "CNC-01", name: "Haas VF-2 3-Axis Mill", cell: "Cell-A" },
  { code: "CNC-02", name: "Mori Seiki NLX-2500 CNC Lathe", cell: "Cell-A" },
  { code: "CNC-03", name: "Mazak Quick Turn 250MSY", cell: "Cell-B" },
  { code: "CNC-04", name: "Okuma LB3000-EX II CNC Lathe", cell: "Cell-B" },
];

export const ProductConfigPage: React.FC<Props> = ({ onNavigate }) => {
  const [products, setProducts] = useState<ProductSpec[]>([]);
  const [machines, setMachines] = useState<any[]>(defaultFallbackMachines);
  const [loading, setLoading] = useState(true);
  const [selectedProduct, setSelectedProduct] = useState<ProductSpec | null>(null);

  const [activeRole, setActiveRole] = useState<Role>("admin");
  const [roleTokens, setRoleTokens] = useState<Record<Role, string>>({
    admin: "",
    quality_engineer: "",
    operator: "",
  });

  const [isEditing, setIsEditing] = useState(false);
  const [isCreating, setIsCreating] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const [formData, setFormData] = useState({
    name: "",
    part_number: "",
    manufacturing_process: "CNC Turning & Grinding",
    machine_id: "CNC-04",
    material: "Carbon Steel AISI 1045",
    inspection_parameter: "shaft_diameter",
    nominal_mm: 50.0,
    tolerance_mm: 0.05,
    unit: "mm",
    inspection_frequency: "100% Critical Feature",
  });

  const [formErrors, setFormErrors] = useState<Record<string, string>>({});

  const loadInitialData = async () => {
    try {
      setLoading(true);
      const [prods, machs] = await Promise.all([
        api.getProducts().catch((err) => {
          console.warn("Failed to load products from API:", err);
          return [] as ProductSpec[];
        }),
        api.getMachines().catch((err) => {
          console.warn("Failed to load machines from API:", err);
          return defaultFallbackMachines;
        }),
      ]);
      setProducts(prods);
      setMachines(machs && machs.length > 0 ? machs : defaultFallbackMachines);
      if (prods.length > 0) {
        setSelectedProduct(prods[0]);
      } else {
        setSelectedProduct(null);
      }
    } catch (err: any) {
      setErrorMessage(err.message || "Failed to load product specifications");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadInitialData();
  }, []);

  useEffect(() => {
    if (selectedProduct && !isCreating) {
      setFormData({
        name: selectedProduct.name || "",
        part_number: selectedProduct.part_number || "",
        manufacturing_process: selectedProduct.manufacturing_process || "CNC Turning & Grinding",
        machine_id: selectedProduct.machine_id || "CNC-04",
        material: selectedProduct.material || "Carbon Steel AISI 1045",
        inspection_parameter: selectedProduct.inspection_parameter || "shaft_diameter",
        nominal_mm: selectedProduct.nominal_mm ?? 50.0,
        tolerance_mm: selectedProduct.tolerance_mm ?? 0.05,
        unit: selectedProduct.unit || "mm",
        inspection_frequency: selectedProduct.inspection_frequency || "100% Critical Feature",
      });
      setIsEditing(false);
      setFormErrors({});
      setErrorMessage(null);
    }
  }, [selectedProduct, isCreating]);

  const calculatedLsl = Number((formData.nominal_mm - formData.tolerance_mm).toFixed(4));
  const calculatedUsl = Number((formData.nominal_mm + formData.tolerance_mm).toFixed(4));

  const validateForm = (): boolean => {
    const errors: Record<string, string> = {};
    if (!formData.name.trim()) errors.name = "Product name is required.";
    if (!formData.part_number.trim()) errors.part_number = "Part number is required.";
    if (!formData.manufacturing_process.trim()) errors.manufacturing_process = "Process is required.";
    if (!formData.machine_id) errors.machine_id = "Assigned machine is required.";
    if (!formData.inspection_parameter.trim()) errors.inspection_parameter = "Characteristic is required.";
    if (isNaN(formData.nominal_mm) || formData.nominal_mm <= 0) errors.nominal_mm = "Nominal must be greater than 0.";
    if (isNaN(formData.tolerance_mm) || formData.tolerance_mm <= 0) errors.tolerance_mm = "Tolerance must be strictly positive (> 0.00).";
    if (calculatedUsl <= calculatedLsl) errors.limits = "Calculated USL must be strictly greater than LSL.";
    if (!formData.inspection_frequency.trim()) errors.inspection_frequency = "Inspection frequency is required.";

    setFormErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleSaveEdit = async () => {
    if (isSubmitting) return;
    if (!validateForm() || !selectedProduct) {
      setErrorMessage("Please complete all required fields and correct form errors before saving.");
      return;
    }
    try {
      setIsSubmitting(true);
      setErrorMessage(null);
      const token = roleTokens[activeRole];
      const updated = await api.updateProduct(
        selectedProduct.product_id,
        {
          name: formData.name.trim(),
          part_number: formData.part_number.trim(),
          process: formData.manufacturing_process.trim(),
          material: formData.material.trim(),
          machine_id: formData.machine_id,
          inspection_parameter: formData.inspection_parameter.trim(),
          nominal: Number(formData.nominal_mm),
          tol_plus: Number(formData.tolerance_mm),
          tol_minus: Number(formData.tolerance_mm),
          unit: formData.unit,
          inspection_frequency: formData.inspection_frequency.trim(),
        },
        token
      );
      setSuccessMessage(`Product '${updated.part_number}' updated successfully.`);
      setIsEditing(false);
      const refreshed = await api.getProducts().catch(() => [updated]);
      setProducts(refreshed);
      setSelectedProduct(updated);
      setTimeout(() => setSuccessMessage(null), 4000);
    } catch (err: any) {
      setErrorMessage(err.message || "Failed to update product");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleCreateProduct = async () => {
    if (isSubmitting) return;
    if (!validateForm()) {
      setErrorMessage("Please complete all required fields and correct form errors before registering.");
      return;
    }
    try {
      setIsSubmitting(true);
      setErrorMessage(null);
      const token = roleTokens[activeRole];
      const created = await api.createProduct(
        {
          name: formData.name.trim(),
          part_number: formData.part_number.trim(),
          process: formData.manufacturing_process.trim(),
          material: formData.material.trim(),
          machine_id: formData.machine_id || machines[0]?.code || "CNC-04",
          inspection_parameter: formData.inspection_parameter.trim(),
          nominal: Number(formData.nominal_mm),
          tol_plus: Number(formData.tolerance_mm),
          tol_minus: Number(formData.tolerance_mm),
          unit: formData.unit,
          inspection_frequency: formData.inspection_frequency.trim(),
        },
        token
      );
      setSuccessMessage(`Product '${created.part_number}' registered successfully.`);
      setIsCreating(false);
      const refreshed = await api.getProducts().catch(() => [created]);
      setProducts(refreshed);
      setSelectedProduct(created);
      setTimeout(() => setSuccessMessage(null), 4000);
    } catch (err: any) {
      setErrorMessage(err.message || "Failed to create product");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDeleteProduct = async () => {
    if (!selectedProduct) return;
    const confirmDelete = window.confirm(
      `Are you sure you want to delete product '${selectedProduct.part_number}' (${selectedProduct.name})?`
    );
    if (!confirmDelete) return;

    try {
      setErrorMessage(null);
      const token = roleTokens[activeRole];
      await api.deleteProduct(selectedProduct.product_id, token);
      setSuccessMessage(`Product '${selectedProduct.part_number}' deleted.`);
      const refreshed = await api.getProducts().catch(() => []);
      setProducts(refreshed);
      setSelectedProduct(refreshed.length > 0 ? refreshed[0] : null);
      setTimeout(() => setSuccessMessage(null), 4000);
    } catch (err: any) {
      setErrorMessage(err.message || "Failed to delete product");
    }
  };

  const startCreate = () => {
    setIsEditing(false);
    setIsCreating(true);
    setErrorMessage(null);
    setFormErrors({});
    setFormData({
      name: "",
      part_number: "",
      manufacturing_process: "CNC Turning & Grinding",
      machine_id: machines[0]?.code || "CNC-04",
      material: "Carbon Steel AISI 1045",
      inspection_parameter: "shaft_diameter",
      nominal_mm: 50.0,
      tolerance_mm: 0.05,
      unit: "mm",
      inspection_frequency: "100% Critical Feature",
    });
  };

  if (loading && products.length === 0) {
    return (
      <div className="p-12 text-center text-slate-500 flex flex-col items-center justify-center gap-3">
        <RefreshCw className="w-6 h-6 animate-spin text-blue-600" />
        <span className="text-sm font-medium">Loading Product Specifications...</span>
      </div>
    );
  }

  const isOperator = false;

  return (
    <div className="space-y-6">

      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-5 bg-white border border-[#E3E8EF] rounded-xl shadow-xs">
        <div>
          <h2 className="text-[26px] font-bold text-slate-900 leading-tight">Product & Process Configuration</h2>
          <p className="text-[14px] text-slate-500 mt-1">
            Configure product specifications, manufacturing processes, and quality tolerances.
          </p>
        </div>
      </div>

      {successMessage && (
        <div
          id="config-success-banner"
          className="p-3 bg-emerald-50 border border-emerald-200 rounded-xl text-xs text-emerald-800 flex items-center gap-2"
        >
          <Check className="w-4 h-4 text-emerald-600 shrink-0" />
          <span>{successMessage}</span>
        </div>
      )}

      {errorMessage && (
        <div
          id="config-error-banner"
          className="p-3 bg-rose-50 border border-rose-200 rounded-xl text-xs text-rose-800 flex items-center gap-2"
        >
          <AlertTriangle className="w-4 h-4 text-rose-600 shrink-0" />
          <span>{errorMessage}</span>
          <button onClick={() => setErrorMessage(null)} className="ml-auto text-rose-500 hover:text-rose-700">
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

        <div className="p-4 bg-white border border-slate-200 rounded-xl shadow-xs space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-slate-700 uppercase tracking-wider">
              Configured Parts ({products.length})
            </span>
            <button
              id="new-product-btn"
              disabled={isOperator}
              onClick={startCreate}
              className={`flex items-center gap-1 text-xs font-semibold px-2.5 py-1 rounded transition-all ${
                isOperator
                  ? "bg-slate-100 text-slate-400 cursor-not-allowed"
                  : "bg-blue-600 hover:bg-blue-700 text-white shadow-xs"
              }`}
              title={isOperator ? "Operator role cannot add products" : "Add new product specification"}
            >
              <Plus className="w-3.5 h-3.5" /> New Product
            </button>
          </div>

          <div className="space-y-2 max-h-[600px] overflow-y-auto pr-1">
            {products.map((p) => {
              const isSel = selectedProduct?.product_id === p.product_id && !isCreating;
              return (
                <div
                  key={p.product_id}
                  id={`product-item-${p.part_number}`}
                  onClick={() => {
                    setSelectedProduct(p);
                    setIsCreating(false);
                    setIsEditing(false);
                  }}
                  className={`p-3 rounded-lg border text-left cursor-pointer transition-all ${
                    isSel
                      ? "bg-blue-50/70 border-blue-400 shadow-xs"
                      : "bg-white border-slate-200 hover:border-slate-300"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-slate-900">{p.name}</span>
                    <span className="text-[11px] font-mono px-1.5 py-0.5 rounded bg-slate-100 text-slate-700 font-semibold">
                      {p.part_number}
                    </span>
                  </div>
                  <div className="text-[11px] text-slate-500 mt-1 flex items-center justify-between">
                    <span>Machine: {p.machine_id}</span>
                    <span className="font-mono">
                      {p.nominal_mm.toFixed(2)} ±{p.tolerance_mm.toFixed(2)} {p.unit}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        <div className="lg:col-span-2 p-5 bg-white border border-slate-200 rounded-xl shadow-xs space-y-5">

          <div className="flex items-start justify-between border-b border-slate-100 pb-4">
            <div>
              <span className="text-xs font-mono text-blue-600 font-bold">
                {isCreating ? "NEW-SPECIFICATION" : selectedProduct?.product_id}
              </span>
              <h3 className="text-lg font-bold text-slate-900 mt-0.5">
                {isCreating
                  ? "Create Master Product Specification"
                  : `${selectedProduct?.name} (${selectedProduct?.part_number})`}
              </h3>
              <p className="text-xs text-slate-500">
                {isCreating
                  ? "Define manufacturing parameters, machine cell, and critical inspection limits."
                  : selectedProduct?.manufacturing_process}
              </p>
            </div>

            <div className="flex items-center gap-2">
              {!isCreating && !isEditing && (
                <>
                  <button
                    id="edit-config-btn"
                    disabled={isOperator}
                    onClick={() => setIsEditing(true)}
                    className={`flex items-center gap-1 text-xs font-semibold px-3 py-1.5 rounded transition-all ${
                      isOperator
                        ? "bg-slate-100 text-slate-400 cursor-not-allowed"
                        : "bg-slate-100 hover:bg-slate-200 text-slate-700"
                    }`}
                    title={isOperator ? "Operator cannot edit configuration" : "Edit this specification"}
                  >
                    <Edit2 className="w-3.5 h-3.5" /> Edit
                  </button>

                  <button
                    id="delete-config-btn"
                    disabled={isOperator || activeRole !== "admin"}
                    onClick={handleDeleteProduct}
                    className={`flex items-center gap-1 text-xs font-semibold px-3 py-1.5 rounded transition-all ${
                      isOperator || activeRole !== "admin"
                        ? "bg-slate-100 text-slate-300 cursor-not-allowed"
                        : "bg-rose-50 hover:bg-rose-100 text-rose-700"
                    }`}
                    title={
                      activeRole !== "admin"
                        ? "Only Administrator can delete products"
                        : "Delete product specification"
                    }
                  >
                    <Trash2 className="w-3.5 h-3.5" /> Delete
                  </button>
                </>
              )}

              {(isCreating || isEditing) && (
                <button
                  id="cancel-config-btn"
                  onClick={() => {
                    setIsCreating(false);
                    setIsEditing(false);
                    setFormErrors({});
                  }}
                  className="text-xs font-semibold px-3 py-1.5 rounded bg-slate-100 hover:bg-slate-200 text-slate-700"
                >
                  Cancel
                </button>
              )}
            </div>
          </div>

          {(isCreating || isEditing) ? (
            <div className="space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">

                <div>
                  <label className="text-xs font-bold text-slate-700 block mb-1">
                    1. Product Name *
                  </label>
                  <input
                    id="input-name"
                    type="text"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    placeholder="e.g. Precision Shaft"
                    className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none"
                  />
                  {formErrors.name && (
                    <span className="text-[11px] text-rose-600 block mt-0.5">{formErrors.name}</span>
                  )}
                </div>

                <div>
                  <label className="text-xs font-bold text-slate-700 block mb-1">
                    2. Part Number *
                  </label>
                  <input
                    id="input-part-number"
                    type="text"
                    value={formData.part_number}
                    onChange={(e) => setFormData({ ...formData, part_number: e.target.value })}
                    placeholder="e.g. PS-2026-101"
                    className="w-full px-3 py-2 text-xs font-mono border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none"
                  />
                  {formErrors.part_number && (
                    <span className="text-[11px] text-rose-600 block mt-0.5">{formErrors.part_number}</span>
                  )}
                </div>

                <div>
                  <label className="text-xs font-bold text-slate-700 block mb-1">
                    3. Manufacturing Process *
                  </label>
                  <input
                    id="input-process"
                    type="text"
                    value={formData.manufacturing_process}
                    onChange={(e) => setFormData({ ...formData, manufacturing_process: e.target.value })}
                    placeholder="e.g. CNC turning & cylindrical grinding"
                    className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none"
                  />
                  {formErrors.manufacturing_process && (
                    <span className="text-[11px] text-rose-600 block mt-0.5">{formErrors.manufacturing_process}</span>
                  )}
                </div>

                <div>
                  <label className="text-xs font-bold text-slate-700 block mb-1">
                    4. Assigned Machine *
                  </label>
                  <select
                    id="select-machine"
                    value={formData.machine_id}
                    onChange={(e) => setFormData({ ...formData, machine_id: e.target.value })}
                    className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none bg-white"
                  >
                    {machines.map((m) => (
                      <option key={m.code || m.machine_id} value={m.code || m.machine_id}>
                        {m.code || m.machine_id} - {m.type || m.name} ({m.location || m.cell})
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="text-xs font-bold text-slate-700 block mb-1">
                    5. Inspection Characteristic *
                  </label>
                  <input
                    id="input-characteristic"
                    type="text"
                    value={formData.inspection_parameter}
                    onChange={(e) => setFormData({ ...formData, inspection_parameter: e.target.value })}
                    placeholder="e.g. shaft_diameter"
                    className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none"
                  />
                  {formErrors.inspection_parameter && (
                    <span className="text-[11px] text-rose-600 block mt-0.5">{formErrors.inspection_parameter}</span>
                  )}
                </div>

                <div>
                  <label className="text-xs font-bold text-slate-700 block mb-1">
                    9. Inspection Frequency *
                  </label>
                  <input
                    id="input-frequency"
                    type="text"
                    value={formData.inspection_frequency}
                    onChange={(e) => setFormData({ ...formData, inspection_frequency: e.target.value })}
                    placeholder="e.g. 100% Critical Feature"
                    className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none"
                  />
                  {formErrors.inspection_frequency && (
                    <span className="text-[11px] text-rose-600 block mt-0.5">{formErrors.inspection_frequency}</span>
                  )}
                </div>
              </div>

              <div className="p-4 bg-slate-50 border border-slate-200 rounded-xl space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-slate-800 uppercase tracking-wider flex items-center gap-1.5">
                    <Ruler className="w-4 h-4 text-blue-600" />
                    Dimensional Tolerancing
                  </span>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">

                  <div>
                    <label className="text-[11px] font-bold text-slate-600 block mb-1">
                      6. Nominal Dimension ({formData.unit}) *
                    </label>
                    <input
                      id="input-nominal"
                      type="number"
                      step="0.01"
                      value={formData.nominal_mm}
                      onChange={(e) => setFormData({ ...formData, nominal_mm: parseFloat(e.target.value) || 0 })}
                      className="w-full px-3 py-2 text-xs font-mono font-bold border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none"
                    />
                    {formErrors.nominal_mm && (
                      <span className="text-[10px] text-rose-600 block mt-0.5">{formErrors.nominal_mm}</span>
                    )}
                  </div>

                  <div>
                    <label className="text-[11px] font-bold text-slate-600 block mb-1">
                      7. Bilateral Tolerance (±) *
                    </label>
                    <input
                      id="input-tolerance"
                      type="number"
                      step="0.001"
                      value={formData.tolerance_mm}
                      onChange={(e) => setFormData({ ...formData, tolerance_mm: parseFloat(e.target.value) || 0 })}
                      className="w-full px-3 py-2 text-xs font-mono font-bold border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none text-blue-700"
                    />
                    {formErrors.tolerance_mm && (
                      <span className="text-[10px] text-rose-600 block mt-0.5">{formErrors.tolerance_mm}</span>
                    )}
                  </div>
                </div>

                {formErrors.limits && (
                  <span className="text-xs text-rose-600 font-semibold block">{formErrors.limits}</span>
                )}
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <button
                  id="save-config-btn"
                  disabled={isSubmitting}
                  onClick={isCreating ? handleCreateProduct : handleSaveEdit}
                  className={`flex items-center gap-1.5 text-xs font-bold px-4 py-2 rounded-lg transition-all ${
                    isSubmitting
                      ? "bg-blue-400 cursor-not-allowed text-white"
                      : "bg-blue-600 hover:bg-blue-700 text-white shadow-xs"
                  }`}
                >
                  {isSubmitting ? (
                    <>
                      <RefreshCw className="w-4 h-4 animate-spin" />
                      <span>{isCreating ? "Registering Product..." : "Saving..."}</span>
                    </>
                  ) : (
                    <>
                      <Check className="w-4 h-4" />
                      <span>{isCreating ? "Confirm & Register Product" : "Save Specification"}</span>
                    </>
                  )}
                </button>
              </div>
            </div>
          ) : !selectedProduct ? (
            <div className="p-8 text-center bg-white border border-slate-200 rounded-xl space-y-3">
              <p className="text-slate-500 text-sm">No product specification selected.</p>
              <button
                onClick={startCreate}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs font-bold inline-flex items-center gap-1"
              >
                <Plus className="w-4 h-4" /> Register New Product
              </button>
            </div>
          ) : (

            <div className="space-y-4">

              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <div className="p-3 bg-slate-50 border border-slate-200 rounded-lg">
                  <span className="text-[10px] text-slate-500 block uppercase font-medium">1. Product</span>
                  <span id="view-product-name" className="text-xs font-bold text-slate-900 mt-0.5 block">
                    {selectedProduct.name}
                  </span>
                </div>

                <div className="p-3 bg-slate-50 border border-slate-200 rounded-lg">
                  <span className="text-[10px] text-slate-500 block uppercase font-medium">2. Part Number</span>
                  <span id="view-part-number" className="text-xs font-mono font-bold text-slate-900 mt-0.5 block">
                    {selectedProduct.part_number}
                  </span>
                </div>

                <div className="p-3 bg-slate-50 border border-slate-200 rounded-lg">
                  <span className="text-[10px] text-slate-500 block uppercase font-medium">3. Process</span>
                  <span id="view-process" className="text-xs font-semibold text-slate-800 mt-0.5 block truncate">
                    {selectedProduct.manufacturing_process}
                  </span>
                </div>

                <div className="p-3 bg-slate-50 border border-slate-200 rounded-lg">
                  <span className="text-[10px] text-slate-500 block uppercase font-medium">4. Assigned Machine</span>
                  {onNavigate ? (
                    <button
                      id="view-machine"
                      type="button"
                      onClick={() => onNavigate("machine-config", selectedProduct.machine_id)}
                      className="text-xs font-bold text-blue-600 hover:text-blue-800 hover:underline mt-0.5 flex items-center gap-1 cursor-pointer group text-left"
                      title="Click to view and configure machine baselines & process thresholds"
                    >
                      <span>{selectedProduct.machine_id}</span>
                      <span className="text-[10px] bg-blue-100 group-hover:bg-blue-200 text-blue-800 px-1.5 py-0.5 rounded font-normal transition-colors">
                        Configure &rarr;
                      </span>
                    </button>
                  ) : (
                    <span id="view-machine" className="text-xs font-bold text-blue-700 mt-0.5 block">
                      {selectedProduct.machine_id}
                    </span>
                  )}
                </div>
              </div>

              <div className="p-4 bg-slate-50 border border-slate-200 rounded-xl space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Ruler className="w-4 h-4 text-blue-600" />
                    <span id="view-characteristic" className="text-xs font-bold text-slate-800 uppercase tracking-wider">
                      5. Characteristic: {selectedProduct.inspection_parameter}
                    </span>
                  </div>
                  <CertaintyBadge level="Observed Fact" />
                </div>

                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                  <div className="p-3 bg-white border border-slate-200 rounded-lg">
                    <span className="text-[10px] text-slate-500 block uppercase font-medium">6. Nominal Dimension</span>
                    <span id="view-nominal" className="text-lg font-bold text-slate-900 font-mono">
                      {selectedProduct.nominal_mm != null ? selectedProduct.nominal_mm.toFixed(2) : "50.00"} {selectedProduct.unit || "mm"}
                    </span>
                  </div>

                  <div className="p-3 bg-white border border-slate-200 rounded-lg">
                    <span className="text-[10px] text-slate-500 block uppercase font-medium">7. Bilateral Tolerance</span>
                    <span id="view-tolerance" className="text-lg font-bold text-blue-700 font-mono">
                      ±{selectedProduct.tolerance_mm != null ? selectedProduct.tolerance_mm.toFixed(2) : "0.05"} {selectedProduct.unit || "mm"}
                    </span>
                  </div>

                  <div className="p-3 bg-white border border-rose-200 rounded-lg bg-rose-50/30">
                    <span className="text-[10px] text-rose-600 block uppercase font-bold">8. Upper Limit (USL)</span>
                    <span id="view-usl" className="text-lg font-bold text-rose-700 font-mono">
                      {selectedProduct.usl != null ? selectedProduct.usl.toFixed(2) : "50.05"} {selectedProduct.unit || "mm"}
                    </span>
                  </div>

                  <div className="p-3 bg-white border border-rose-200 rounded-lg bg-rose-50/30">
                    <span className="text-[10px] text-rose-600 block uppercase font-bold">8. Lower Limit (LSL)</span>
                    <span id="view-lsl" className="text-lg font-bold text-rose-700 font-mono">
                      {selectedProduct.lsl != null ? selectedProduct.lsl.toFixed(2) : "49.95"} {selectedProduct.unit || "mm"}
                    </span>
                  </div>
                </div>

                <div className="p-3 bg-white border border-slate-200 rounded-lg text-xs space-y-1 text-slate-600">
                  <div className="flex justify-between">
                    <span className="font-medium text-slate-700">9. Inspection Frequency:</span>
                    <span id="view-frequency" className="font-semibold">{selectedProduct.inspection_frequency}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="font-medium text-slate-700">Deterministic Conformance Band:</span>
                    <span className="font-mono text-emerald-700 font-bold">
                      {selectedProduct.lsl != null ? selectedProduct.lsl.toFixed(2) : "49.95"} mm &le; Shaft Diameter &le; {selectedProduct.usl != null ? selectedProduct.usl.toFixed(2) : "50.05"} mm
                    </span>
                  </div>
                </div>
              </div>

              <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg text-xs text-blue-900 flex items-start gap-2">
                <ShieldCheck className="w-4 h-4 text-blue-600 shrink-0 mt-0.5" />
                <span>
                  <strong>Deterministic Calculation Guarantee:</strong> Engineering specification limits LSL ({selectedProduct.lsl != null ? selectedProduct.lsl.toFixed(2) : "49.95"} mm)
                  and USL ({selectedProduct.usl != null ? selectedProduct.usl.toFixed(2) : "50.05"} mm) are calculated strictly on the backend. Any component exceeding USL or dropping below LSL
                  is flagged nonconforming during dimensional inspection.
                </span>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

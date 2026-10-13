import React, { useEffect, useState, useRef } from "react";
import { api } from "../api";
import { InspectionReport, MeasurementItem } from "../types";
import { CertaintyBadge } from "../components/CertaintyBadge";
import {
  Ruler, Upload, FileSpreadsheet, CheckCircle2, AlertTriangle,
  RefreshCw, BarChart2, Download, X, Info, FileDown, Loader2,
  Plus, Edit2, Trash2, Camera, ShieldCheck, Check, Sparkles,
  AlertCircle, Eye, ArrowRight, Layers
} from "lucide-react";
import {
  ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, CartesianGrid, ReferenceLine, Cell
} from "recharts";

type Role = "admin" | "quality_engineer" | "operator";

interface MeasurementRecord {
  id: string;
  batch_id: string;
  component_id: string;
  value: number;
  unit: string;
  status: string;
  deviation_from_limit?: number;
  source_type?: string;
  file_name?: string;
  uploaded_by?: string;
  upload_time?: string;
  measured_at?: string;
}

interface ValidationReportData {
  status: "success" | "rejected";
  message: string;
  filename?: string;
  sheet_name?: string;
  total_rows?: number;
  accepted_rows?: number;
  rejected_rows?: number;
  missing_values?: Array<{ row: number; column: string; message: string }>;
  errors?: string[];
  warnings?: string[];
  unit_conversions?: Array<{
    sample_id: string;
    row?: number;
    original_value: number;
    original_unit: string;
    converted_value_mm: number;
  }>;
}

export const InspectionPage: React.FC = () => {
  const [report, setReport] = useState<InspectionReport | null>(null);
  const [dbMeasurements, setDbMeasurements] = useState<MeasurementRecord[]>([]);
  const [imagesList, setImagesList] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [activeTab, setActiveTab] = useState<"file_upload" | "manual_entry" | "image_upload" | "charts">("file_upload");

  // Persona / RBAC State
  const [activeRole, setActiveRole] = useState<Role>("quality_engineer");
  const [roleTokens, setRoleTokens] = useState<Record<Role, string>>({
    admin: "",
    quality_engineer: "",
    operator: "",
  });

  // Target Batch
  const [batchId, setBatchId] = useState("");
  const [batches, setBatches] = useState<any[]>([]);

  // Validation Report Panel State
  const [validationReport, setValidationReport] = useState<ValidationReportData | null>(null);
  const [sourceInfo, setSourceInfo] = useState<string>("Master Inspection Registry");
  const [successBanner, setSuccessBanner] = useState<string | null>(null);
  const [errorBanner, setErrorBanner] = useState<string | null>(null);

  // Manual Entry Form State
  const [manualForm, setManualForm] = useState({
    component_id: "SMPL-001",
    value: 50.00,
    unit: "mm",
  });
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editValue, setEditValue] = useState<number>(50.00);
  const [editUnit, setEditUnit] = useState<string>("mm");

  // Image Upload State
  const [imageComponentId, setImageComponentId] = useState("SMPL-001");
  const [uploadingImage, setUploadingImage] = useState(false);
  const [imagePredictionResult, setImagePredictionResult] = useState<any | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const imageInputRef = useRef<HTMLInputElement>(null);

  // Load available batches on mount
  useEffect(() => {
    api.getBatches().then((bList) => {
      setBatches(bList || []);
      if (bList && bList.length > 0) {
        const bId = bList[0].batch_number || bList[0].batch_id || "";
        setBatchId(bId);
        setSourceInfo(`Master Inspection Registry (${bId})`);
      } else {
        setBatchId("");
        setLoading(false);
      }
    }).catch(() => {
      setLoading(false);
    });
  }, []);

  // Load all initial data from backend (data survives page reload!)
  const loadData = async () => {
    if (!batchId) {
      setLoading(false);
      setReport(null);
      setDbMeasurements([]);
      setImagesList([]);
      return;
    }
    try {
      setLoading(true);
      setErrorBanner(null);

      const [specRes, measList, imgsRes] = await Promise.all([
        api.getBatchSpecCheck(batchId),
        api.getBatchMeasurements(batchId),
        api.getInspectionImages(batchId)
      ]);

      // Construct report from spec check
      const incomingReport: InspectionReport = {
        batch_id: batchId,
        total_inspected: specRes.total_inspected ?? measList.length,
        accepted: specRes.accepted_count ?? specRes.accepted ?? 0,
        nonconforming: specRes.nonconforming_count ?? specRes.nonconforming ?? 0,
        rejection_rate_percent: specRes.rejection_rate_percent ?? 0.0,
        measurements: specRes.measurements || [],
        nominal_mm: specRes.spec_limits?.nominal || 50.00,
        tolerance_mm: (specRes.spec_limits?.usl - specRes.spec_limits?.nominal) || 0.05,
        usl: specRes.spec_limits?.usl || 50.05,
        lsl: specRes.spec_limits?.lsl || 49.95,
        certainty: "Observed Fact",
        mean: specRes.mean ?? specRes.mean_measured,
        std_dev_sample: specRes.std_dev_sample,
        min: specRes.min,
        max: specRes.max,
        max_deviation_from_limit: specRes.max_deviation_from_limit,
        histogram_bins: specRes.histogram_bins || [],
        nonconforming_items: specRes.nonconforming_items || [],
        distribution: specRes.distribution,
        disposition_notice: specRes.disposition_notice,
      };

      setReport(incomingReport);
      setDbMeasurements(measList);
      setImagesList(imgsRes);
    } catch (err: any) {
      setErrorBanner(err.message || "Failed to load inspection data from server.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (batchId) {
      loadData();
    }
  }, [batchId]);

  // Handle CSV / Excel File Upload
  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;

    const file = files[0];
    const fn = file.name.toLowerCase();

    // Check allowed format
    if (!fn.endsWith(".csv") && !fn.endsWith(".xlsx") && !fn.endsWith(".xls")) {
      setErrorBanner(`Invalid format: "${file.name}". Only CSV (.csv) and Excel (.xlsx, .xls) files are supported.`);
      if (fileInputRef.current) fileInputRef.current.value = "";
      return;
    }

    setUploading(true);
    setErrorBanner(null);
    setSuccessBanner(null);
    setValidationReport(null);

    try {
      const token = roleTokens[activeRole];
      const res = await api.uploadInspectionFile(file, batchId, token, false);

      // On successful upload
      setValidationReport({
        status: "success",
        message: `Successfully validated and imported ${res.accepted_rows} rows from ${file.name}.`,
        filename: file.name,
        sheet_name: res.sheet_name,
        total_rows: res.total_rows,
        accepted_rows: res.accepted_rows,
        rejected_rows: res.rejected_rows || 0,
        missing_values: res.missing_values || [],
        errors: res.errors || [],
        warnings: res.warnings || [],
        unit_conversions: res.unit_conversions || [],
      });

      setSuccessBanner(
        `Imported ${res.accepted_rows} physical measurements into ${batchId}. Compliance: ${res.spec_check?.accepted} accepted, ${res.spec_check?.nonconforming} nonconforming (${res.spec_check?.rejection_rate_percent}% rejection rate).`
      );
      setSourceInfo(`Uploaded file: ${file.name} (${res.sheet_name ? `Sheet: ${res.sheet_name}` : "CSV"})`);

      // Reload state from database
      await loadData();
    } catch (err: any) {
      // Check if structured validation report was returned
      if (err && typeof err === "object" && err.detail) {
        const detail = err.detail;
        if (typeof detail === "object" && detail.status === "rejected") {
          setValidationReport({
            status: "rejected",
            message: detail.message || "File validation rejected.",
            filename: detail.filename || file.name,
            total_rows: detail.total_rows,
            accepted_rows: detail.accepted_rows || 0,
            rejected_rows: detail.rejected_rows,
            missing_values: detail.missing_values || [],
            errors: detail.errors || [],
            warnings: detail.warnings || [],
            unit_conversions: detail.unit_conversions || [],
          });
          setErrorBanner(detail.message || "File rejected due to schema or validation errors.");
        } else {
          const msg = typeof detail === "string" ? detail : JSON.stringify(detail);
          setErrorBanner(msg);
        }
      } else {
        setErrorBanner(err.message || "Failed to process inspection file.");
      }
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  // Handle Manual Measurement Creation
  const handleAddManualMeasurement = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setErrorBanner(null);
      const token = roleTokens[activeRole];
      await api.addManualMeasurement(
        {
          batch_id: batchId,
          component_id: manualForm.component_id.trim(),
          value: Number(manualForm.value),
          unit: manualForm.unit,
        },
        token
      );
      setSuccessBanner(`Added manual measurement ${manualForm.component_id} = ${manualForm.value} ${manualForm.unit}`);
      // Increment sample ID for fast entry
      const nextNum = parseInt(manualForm.component_id.replace(/\D/g, "")) || 6;
      setManualForm({
        component_id: `P${String(nextNum + 1).padStart(3, "0")}`,
        value: 50.02,
        unit: "mm",
      });
      await loadData();
    } catch (err: any) {
      setErrorBanner(err.message || "Failed to add manual measurement.");
    }
  };

  // Handle Manual Measurement Update
  const handleUpdateManualMeasurement = async (id: string) => {
    try {
      setErrorBanner(null);
      const token = roleTokens[activeRole];
      await api.updateManualMeasurement(id, { value: Number(editValue), unit: editUnit }, token);
      setSuccessBanner(`Updated measurement to ${editValue} ${editUnit}`);
      setEditingId(null);
      await loadData();
    } catch (err: any) {
      setErrorBanner(err.message || "Failed to update measurement.");
    }
  };

  // Handle Manual Measurement Delete
  const handleDeleteManualMeasurement = async (id: string) => {
    if (!window.confirm("Are you sure you want to delete this measurement?")) return;
    try {
      setErrorBanner(null);
      const token = roleTokens[activeRole];
      await api.deleteManualMeasurement(id, token);
      setSuccessBanner("Measurement successfully deleted.");
      await loadData();
    } catch (err: any) {
      setErrorBanner(err.message || "Failed to delete measurement.");
    }
  };

  // Handle Inspection Image Upload (Vision Agent)
  const handleImageUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;
    const file = files[0];

    try {
      setUploadingImage(true);
      setErrorBanner(null);
      setImagePredictionResult(null);
      const token = roleTokens[activeRole];

      const res = await api.uploadInspectionImage(file, batchId, imageComponentId, token);
      setImagePredictionResult(res.vision_prediction);
      setSuccessBanner(`Image uploaded for ${imageComponentId}. AI Vision Defect status: ${res.vision_prediction.defect_type} (${(res.vision_prediction.confidence * 100).toFixed(1)}% confidence)`);
      await loadData();
    } catch (err: any) {
      setErrorBanner(err.message || "Failed to upload inspection image.");
    } finally {
      setUploadingImage(false);
      if (imageInputRef.current) imageInputRef.current.value = "";
    }
  };

  // Template Download
  const handleDownloadTemplate = () => {
    const csvContent =
      "component_id,diameter_mm\n" +
      "P001,50.01\n" +
      "P002,50.03\n" +
      "P003,50.06\n" +
      "P004,50.08\n" +
      "P005,50.07\n";

    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.setAttribute("download", `inspection_template_${batchId}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  if (loading || !report) {
    return (
      <div className="p-12 text-center text-slate-500 flex flex-col items-center justify-center gap-3">
        <Loader2 className="w-6 h-6 animate-spin text-blue-600" />
        <span className="text-sm font-medium">Loading Inspection Data & Validation Models...</span>
      </div>
    );
  }

  // Distribution chart data
  const chartData = report.measurements.map((m) => ({
    sample_id: m.sample_id,
    measured: m.measured_value,
    usl: report.usl,
    lsl: report.lsl,
    nominal: report.nominal_mm,
    is_conforming: m.is_conforming,
    deviation: m.deviation_from_limit,
  }));

  const allValues = [report.usl, report.lsl, report.nominal_mm, ...report.measurements.map((m) => m.measured_value)];
  const minY = Math.floor((Math.min(...allValues) - 0.02) * 100) / 100;
  const maxY = Math.ceil((Math.max(...allValues) + 0.02) * 100) / 100;

  return (
    <div className="space-y-6">
      {/* Header with Persona Switcher & Controls */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h2 className="text-[26px] font-bold text-slate-900 leading-tight">Inspection Center & Measurement Intake</h2>
          <p className="text-[14px] text-slate-500 mt-1">
            Import measurements via CSV, Excel, or manual entry with automated specification checking.
          </p>
        </div>

        <div className="flex items-center flex-wrap gap-3">
          {/* Prominent Visible Target Batch Field */}
          <div className="flex items-center gap-2 px-3 py-1.5 bg-blue-50/80 border border-blue-200 rounded-lg shadow-2xs">
            <Layers className="w-4 h-4 text-blue-600 shrink-0" />
            <span className="text-xs font-bold text-blue-900 whitespace-nowrap">Target Batch:</span>
            {batches.length > 0 ? (
              <select
                value={batchId}
                onChange={(e) => setBatchId(e.target.value)}
                className="bg-white border border-blue-300 rounded px-2.5 py-1 text-xs font-mono font-bold text-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-400 shadow-2xs cursor-pointer"
              >
                {batches.map((b) => (
                  <option key={b.id || b.batch_number} value={b.batch_number}>
                    {b.batch_number}
                  </option>
                ))}
              </select>
            ) : (
              <input
                type="text"
                value={batchId}
                onChange={(e) => setBatchId(e.target.value)}
                className="bg-white border border-blue-300 rounded px-2.5 py-1 text-xs font-mono font-bold text-blue-700 w-32 focus:outline-none focus:ring-2 focus:ring-blue-400 shadow-2xs"
                placeholder="No batches"
              />
            )}
          </div>

          {/* RBAC Persona Switcher */}
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

          {/* Download Template */}
          <button
            onClick={handleDownloadTemplate}
            className="btn-secondary !h-[40px]"
          >
            <Download className="w-4 h-4 text-slate-500" />
            <span>Download Template</span>
          </button>

          {/* Refresh Data */}
          <button
            onClick={loadData}
            title="Reload inspection data"
            className="btn-secondary !p-2 !h-[40px] !w-[40px] flex items-center justify-center"
          >
            <RefreshCw className={`w-4 h-4 text-slate-600 ${loading ? "animate-spin" : ""}`} />
          </button>
        </div>
      </div>

      {/* Global Alerts */}
      {errorBanner && (
        <div className="p-3.5 bg-rose-50 border border-rose-200 rounded-xl text-rose-800 text-[13.5px] flex items-center justify-between shadow-2xs">
          <div className="flex items-center gap-2.5">
            <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
            <span className="font-medium">{errorBanner}</span>
          </div>
          <button onClick={() => setErrorBanner(null)} className="text-rose-500 hover:text-rose-700">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {successBanner && (
        <div className="p-3.5 bg-emerald-50 border border-emerald-200 rounded-xl text-emerald-800 text-[13.5px] flex items-center justify-between shadow-2xs">
          <div className="flex items-center gap-2.5">
            <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
            <span className="font-medium">{successBanner}</span>
          </div>
          <button onClick={() => setSuccessBanner(null)} className="text-emerald-500 hover:text-emerald-700">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Navigation Tabs */}
      <div className="flex border-b border-[#E3E8EF] bg-white rounded-t-xl px-4 pt-2 gap-2 text-[13.5px] font-semibold">
        <button
          onClick={() => setActiveTab("file_upload")}
          className={`pb-2.5 px-3 border-b-2 flex items-center gap-2 transition-colors ${
            activeTab === "file_upload"
              ? "border-[#2563EB] text-[#2563EB]"
              : "border-transparent text-slate-500 hover:text-slate-800"
          }`}
        >
          <Upload className="w-4 h-4" />
          <span>CSV & Excel Upload</span>
        </button>
        <button
          onClick={() => setActiveTab("manual_entry")}
          className={`pb-2.5 px-3 border-b-2 flex items-center gap-2 transition-colors ${
            activeTab === "manual_entry"
              ? "border-[#2563EB] text-[#2563EB]"
              : "border-transparent text-slate-500 hover:text-slate-800"
          }`}
        >
          <Plus className="w-4 h-4" />
          <span>Manual Measurements ({dbMeasurements.length})</span>
        </button>
        <button
          onClick={() => setActiveTab("image_upload")}
          className={`pb-2.5 px-3 border-b-2 flex items-center gap-2 transition-colors ${
            activeTab === "image_upload"
              ? "border-[#2563EB] text-[#2563EB]"
              : "border-transparent text-slate-500 hover:text-slate-800"
          }`}
        >
          <Camera className="w-4 h-4" />
          <span>Visual Inspection Images ({imagesList.length})</span>
        </button>
        <button
          onClick={() => setActiveTab("charts")}
          className={`pb-2.5 px-3 border-b-2 flex items-center gap-2 transition-colors ${
            activeTab === "charts"
              ? "border-[#2563EB] text-[#2563EB]"
              : "border-transparent text-slate-500 hover:text-slate-800"
          }`}
        >
          <BarChart2 className="w-4 h-4" />
          <span>Specification Conformance & Limits</span>
        </button>
      </div>

      {/* TAB 1: CSV & EXCEL DRAG-AND-DROP UPLOAD */}
      {activeTab === "file_upload" && (
        <div className="space-y-6">
          <div className="bg-white border border-[#E3E8EF] rounded-xl p-6 shadow-xs">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-5">
              <div>
                <h3 className="text-[16px] font-bold text-slate-900">Upload Measurement File</h3>
                <p className="text-[13px] text-[#475467] mt-0.5">
                  Import batch measurements from CSV or Excel spreadsheets.
                </p>
              </div>
              <div className="flex items-center gap-2 px-3 py-1.5 bg-blue-50/80 border border-blue-200 rounded-lg shadow-2xs">
                <Layers className="w-4 h-4 text-blue-600 shrink-0" />
                <span className="text-xs font-bold text-blue-900">Target Batch:</span>
                {batches.length > 0 ? (
                  <select
                    value={batchId}
                    onChange={(e) => setBatchId(e.target.value)}
                    className="px-2.5 py-1 bg-white border border-blue-300 rounded-md font-mono font-bold text-xs text-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-400 shadow-2xs cursor-pointer"
                  >
                    {batches.map((b) => (
                      <option key={b.id || b.batch_number} value={b.batch_number}>
                        {b.batch_number}
                      </option>
                    ))}
                  </select>
                ) : (
                  <input
                    type="text"
                    value={batchId}
                    onChange={(e) => setBatchId(e.target.value)}
                    className="px-2.5 py-1 bg-white border border-blue-300 rounded-md font-mono font-bold text-xs text-blue-700 w-32 focus:outline-none focus:ring-2 focus:ring-blue-400 shadow-2xs"
                    placeholder="No batches"
                  />
                )}
              </div>
            </div>

            {/* Drag & Drop Upload Zone */}
            <div
              onClick={() => fileInputRef.current?.click()}
              onDragOver={(e) => { e.preventDefault(); e.stopPropagation(); }}
              onDrop={(e) => {
                e.preventDefault();
                e.stopPropagation();
                if (e.dataTransfer.files && e.dataTransfer.files[0]) {
                  const droppedFile = e.dataTransfer.files[0];
                  // Dispatch file upload
                  const dummyEvent = { target: { files: [droppedFile] } } as any;
                  handleFileUpload(dummyEvent);
                }
              }}
              className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-all flex flex-col items-center justify-center gap-2.5 ${
                uploading
                  ? "border-[#2563EB] bg-[#EAF2FF]"
                  : "border-[#D0D5DD] hover:border-[#2563EB] bg-slate-50/60 hover:bg-[#EAF2FF]/50"
              }`}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept=".csv, .xlsx, .xls"
                onChange={handleFileUpload}
                className="hidden"
              />
              <div className="w-12 h-12 rounded-full bg-[#EAF2FF] text-[#2563EB] flex items-center justify-center shadow-2xs">
                {uploading ? (
                  <Loader2 className="w-6 h-6 animate-spin text-[#2563EB]" />
                ) : (
                  <Upload className="w-6 h-6" />
                )}
              </div>
              <div className="text-[15px] font-bold text-slate-800">
                {uploading ? "Processing and validating measurements..." : "Click or drag & drop inspection file here"}
              </div>
              <p className="text-[13px] text-slate-500 max-w-md">
                Supports <span className="font-semibold text-slate-700">.csv, .xlsx, .xls</span> files. Automatic unit normalization and specification compliance check.
              </p>
            </div>
          </div>

          {/* STRUCTURED VALIDATION REPORT PANEL (Check 5, 6, 8) */}
          {validationReport && (
            <div
              className={`border rounded-xl p-5 shadow-xs transition-all ${
                validationReport.status === "success"
                  ? "bg-emerald-50/40 border-emerald-300"
                  : "bg-rose-50/50 border-rose-300"
              }`}
            >
              <div className="flex items-center justify-between pb-3 border-b border-slate-200 mb-4">
                <div className="flex items-center gap-2">
                  {validationReport.status === "success" ? (
                    <CheckCircle2 className="w-5 h-5 text-emerald-600" />
                  ) : (
                    <AlertTriangle className="w-5 h-5 text-rose-600" />
                  )}
                  <h4 className="text-sm font-bold text-slate-900">
                    Validation Report: {validationReport.filename || "Uploaded File"}
                  </h4>
                  <span
                    className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider ${
                      validationReport.status === "success"
                        ? "bg-emerald-100 text-emerald-800"
                        : "bg-rose-100 text-rose-800"
                    }`}
                  >
                    {validationReport.status.toUpperCase()}
                  </span>
                </div>
                <button
                  onClick={() => setValidationReport(null)}
                  className="text-slate-400 hover:text-slate-600 p-1"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              {/* Summary KPIs */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-4">
                <div className="bg-white p-3 rounded-lg border border-slate-200">
                  <div className="text-[10px] uppercase font-semibold text-slate-400">Total Rows</div>
                  <div className="text-base font-bold text-slate-800">{validationReport.total_rows ?? 0}</div>
                </div>
                <div className="bg-white p-3 rounded-lg border border-slate-200">
                  <div className="text-[10px] uppercase font-semibold text-emerald-600">Accepted Rows</div>
                  <div className="text-base font-bold text-emerald-700">{validationReport.accepted_rows ?? 0}</div>
                </div>
                <div className="bg-white p-3 rounded-lg border border-slate-200">
                  <div className="text-[10px] uppercase font-semibold text-rose-600">Rejected Rows</div>
                  <div className="text-base font-bold text-rose-700">{validationReport.rejected_rows ?? 0}</div>
                </div>
                <div className="bg-white p-3 rounded-lg border border-slate-200">
                  <div className="text-[10px] uppercase font-semibold text-blue-600">Unit Conversions</div>
                  <div className="text-base font-bold text-blue-700">{validationReport.unit_conversions?.length ?? 0}</div>
                </div>
              </div>

              {/* Missing Values List (Check 5) */}
              {validationReport.missing_values && validationReport.missing_values.length > 0 && (
                <div className="mb-4 bg-white rounded-lg p-3.5 border border-rose-200">
                  <div className="text-xs font-bold text-rose-900 mb-2 flex items-center gap-1.5">
                    <AlertCircle className="w-3.5 h-3.5 text-rose-600" />
                    <span>Missing Value Details ({validationReport.missing_values.length}):</span>
                  </div>
                  <ul className="space-y-1 text-xs text-rose-700 list-disc list-inside">
                    {validationReport.missing_values.map((mv, idx) => (
                      <li key={idx}>
                        <span className="font-semibold">Row {mv.row}:</span> Column <code className="bg-rose-100 px-1 py-0.5 rounded font-mono">{mv.column}</code> — {mv.message}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Unit Conversions Applied (Check 6) */}
              {validationReport.unit_conversions && validationReport.unit_conversions.length > 0 && (
                <div className="mb-4 bg-white rounded-lg p-3.5 border border-blue-200">
                  <div className="text-xs font-bold text-blue-900 mb-2 flex items-center gap-1.5">
                    <Ruler className="w-3.5 h-3.5 text-blue-600" />
                    <span>Deterministic Unit Conversions Applied ({validationReport.unit_conversions.length}):</span>
                  </div>
                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-xs">
                      <thead>
                        <tr className="border-b border-slate-200 text-slate-500 font-semibold text-[10px]">
                          <th className="py-1">Sample ID</th>
                          <th className="py-1">Original Reading</th>
                          <th className="py-1">Original Unit</th>
                          <th className="py-1">Converted Value (mm)</th>
                          <th className="py-1">Formula Calculation</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100">
                        {validationReport.unit_conversions.map((uc, idx) => (
                          <tr key={idx} className="font-mono text-[11px]">
                            <td className="py-1 text-blue-600 font-bold">{uc.sample_id}</td>
                            <td className="py-1 text-slate-700">{uc.original_value}</td>
                            <td className="py-1 text-slate-600 uppercase font-semibold">{uc.original_unit}</td>
                            <td className="py-1 text-emerald-700 font-bold">{uc.converted_value_mm} mm</td>
                            <td className="py-1 text-slate-400 text-[10px]">
                              {uc.original_unit === "in" && `${uc.original_value} × 25.4 = ${uc.converted_value_mm} mm`}
                              {uc.original_unit === "um" && `${uc.original_value} × 0.001 = ${uc.converted_value_mm} mm`}
                              {uc.original_unit === "cm" && `${uc.original_value} × 10.0 = ${uc.converted_value_mm} mm`}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {/* Errors List */}
              {validationReport.errors && validationReport.errors.length > 0 && (
                <div className="mb-3 bg-white rounded-lg p-3 border border-rose-200">
                  <div className="text-xs font-bold text-rose-800 mb-1">Errors ({validationReport.errors.length}):</div>
                  <ul className="text-xs text-rose-700 list-disc list-inside space-y-0.5">
                    {validationReport.errors.map((err, idx) => (
                      <li key={idx}>{err}</li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Warnings List */}
              {validationReport.warnings && validationReport.warnings.length > 0 && (
                <div className="bg-white rounded-lg p-3 border border-amber-200">
                  <div className="text-xs font-bold text-amber-800 mb-1">Warnings ({validationReport.warnings.length}):</div>
                  <ul className="text-xs text-amber-700 list-disc list-inside space-y-0.5">
                    {validationReport.warnings.map((w, idx) => (
                      <li key={idx}>{w}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}

          {/* ACTIVE IMPORTED MEASUREMENTS TABLE */}
          <div className="bg-white border border-slate-200 rounded-xl shadow-xs overflow-hidden">
            <div className="px-5 py-3.5 border-b border-slate-200 bg-slate-50/50 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Ruler className="w-4 h-4 text-slate-600" />
                <span className="text-xs font-bold text-slate-800 uppercase tracking-wider">
                  Active Inspection Table: {report?.measurements?.length || 0} Samples
                </span>
              </div>
              <span className="text-xs text-slate-500 font-mono">
                {report ? `Limits: [${report.lsl.toFixed(2)} mm .. ${report.usl.toFixed(2)} mm]` : "Awaiting batch specification"}
              </span>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-50 border-b border-slate-200 text-slate-600 font-semibold uppercase text-[10px] tracking-wider">
                  <tr>
                    <th className="px-4 py-3">Sample ID</th>
                    <th className="px-4 py-3">Measured Value</th>
                    <th className="px-4 py-3">Deviation from Nominal</th>
                    <th className="px-4 py-3">Deviation from Limit</th>
                    <th className="px-4 py-3">Conformance Status</th>
                    <th className="px-4 py-3">Epistemic Certainty</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {(!report || report.measurements.length === 0) ? (
                    <tr>
                      <td colSpan={6} className="px-4 py-8 text-center text-slate-500">
                        No measurements imported yet. Drag & drop a CSV or Excel inspection file above to validate against product specifications.
                      </td>
                    </tr>
                  ) : (
                    report.measurements.map((m) => (
                    <tr
                      key={m.sample_id}
                      className={`hover:bg-slate-50 transition-colors ${
                        !m.is_conforming ? "bg-rose-50/30" : ""
                      }`}
                    >
                      <td className="px-4 py-3 font-mono font-bold text-blue-600">{m.sample_id}</td>
                      <td className="px-4 py-3 font-mono font-semibold text-slate-900">
                        {m.measured_value.toFixed(2)} mm
                      </td>
                      <td className="px-4 py-3 font-mono text-slate-600">
                        {m.deviation_from_nominal > 0 ? `+${m.deviation_from_nominal.toFixed(3)}` : m.deviation_from_nominal.toFixed(3)} mm
                      </td>
                      <td className="px-4 py-3 font-mono text-slate-600">
                        {m.deviation_from_limit > 0 ? (
                          <span className="text-rose-600 font-semibold">+{m.deviation_from_limit.toFixed(3)} mm</span>
                        ) : (
                          <span className="text-emerald-600 font-semibold">In spec</span>
                        )}
                      </td>
                      <td className="px-4 py-3">
                        <span
                          className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold ${
                            m.is_conforming
                              ? "bg-emerald-100 text-emerald-800 border border-emerald-300"
                              : "bg-rose-100 text-rose-800 border border-rose-300"
                          }`}
                        >
                          {m.is_conforming ? <Check className="w-3 h-3" /> : <X className="w-3 h-3" />}
                          <span>{m.is_conforming ? "CONFORMING" : "NONCONFORMING"}</span>
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <CertaintyBadge level={m.certainty || "Observed Fact"} />
                      </td>
                    </tr>
                  ))
                )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* TAB 2: MANUAL MEASUREMENT ENTRY GRID (Check 3) */}
      {activeTab === "manual_entry" && (
        <div className="space-y-6">
          {/* Add Measurement Inline Form */}
          <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-xs">
            <h3 className="text-sm font-bold text-slate-900 mb-1">Add Manual Measurement (Single Entry)</h3>
            <p className="text-xs text-slate-500 mb-4">
              Enter individual piece measurements manually. Validates units and checks limits against nominal specifications.
            </p>
            <form onSubmit={handleAddManualMeasurement} className="flex flex-wrap items-end gap-3">
              <div>
                <label className="block text-[11px] font-semibold text-slate-700 mb-1">Component ID</label>
                <input
                  type="text"
                  required
                  value={manualForm.component_id}
                  onChange={(e) => setManualForm({ ...manualForm, component_id: e.target.value })}
                  placeholder="e.g. P006"
                  className="px-3 py-1.5 border border-slate-300 rounded-lg text-xs font-mono font-semibold"
                />
              </div>

              <div>
                <label className="block text-[11px] font-semibold text-slate-700 mb-1">Measured Value</label>
                <input
                  type="number"
                  step="0.0001"
                  required
                  value={manualForm.value}
                  onChange={(e) => setManualForm({ ...manualForm, value: parseFloat(e.target.value) || 0 })}
                  className="px-3 py-1.5 border border-slate-300 rounded-lg text-xs font-mono"
                />
              </div>

              <div>
                <label className="block text-[11px] font-semibold text-slate-700 mb-1">Unit</label>
                <select
                  value={manualForm.unit}
                  onChange={(e) => setManualForm({ ...manualForm, unit: e.target.value })}
                  className="px-3 py-1.5 border border-slate-300 rounded-lg text-xs"
                >
                  <option value="mm">mm (Millimeters)</option>
                  <option value="in">in (Inches)</option>
                  <option value="um">um (Microns)</option>
                  <option value="cm">cm (Centimeters)</option>
                </select>
              </div>

              <button
                type="submit"
                className="px-4 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs font-semibold shadow-xs flex items-center gap-1.5"
              >
                <Plus className="w-3.5 h-3.5" />
                <span>Add Measurement</span>
              </button>
            </form>
          </div>

          {/* Persisted Measurements Grid with Edit & Delete */}
          <div className="bg-white border border-slate-200 rounded-xl shadow-xs overflow-hidden">
            <div className="px-5 py-3.5 border-b border-slate-200 bg-slate-50/50 flex items-center justify-between">
              <span className="text-xs font-bold text-slate-800 uppercase tracking-wider">
                Persisted Measurements in Database ({dbMeasurements.length})
              </span>
              <span className="text-xs text-slate-500">IATF 16949 Section 8.5.2 Traceability</span>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-50 border-b border-slate-200 text-slate-600 font-semibold uppercase text-[10px] tracking-wider">
                  <tr>
                    <th className="px-4 py-3">Component ID</th>
                    <th className="px-4 py-3">Value</th>
                    <th className="px-4 py-3">Status</th>
                    <th className="px-4 py-3">Source Type</th>
                    <th className="px-4 py-3">Source File</th>
                    <th className="px-4 py-3">Uploader</th>
                    <th className="px-4 py-3">Timestamp</th>
                    <th className="px-4 py-3 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {dbMeasurements.map((m) => {
                    const isEditing = editingId === m.id;
                    const isNonconf = m.status === "nonconforming";

                    return (
                      <tr key={m.id} className={`hover:bg-slate-50 ${isNonconf ? "bg-rose-50/20" : ""}`}>
                        <td className="px-4 py-3 font-mono font-bold text-blue-600">{m.component_id}</td>
                        <td className="px-4 py-3 font-mono font-semibold">
                          {isEditing ? (
                            <div className="flex items-center gap-1">
                              <input
                                type="number"
                                step="0.0001"
                                value={editValue}
                                onChange={(e) => setEditValue(parseFloat(e.target.value) || 0)}
                                className="w-20 px-2 py-0.5 border border-blue-400 rounded text-xs font-mono"
                              />
                              <select
                                value={editUnit}
                                onChange={(e) => setEditUnit(e.target.value)}
                                className="px-1 py-0.5 border border-slate-300 rounded text-xs"
                              >
                                <option value="mm">mm</option>
                                <option value="in">in</option>
                                <option value="um">um</option>
                                <option value="cm">cm</option>
                              </select>
                            </div>
                          ) : (
                            <span>{m.value.toFixed(2)} mm</span>
                          )}
                        </td>
                        <td className="px-4 py-3">
                          <span
                            className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                              m.status === "conforming"
                                ? "bg-emerald-100 text-emerald-800"
                                : "bg-rose-100 text-rose-800"
                            }`}
                          >
                            {m.status.toUpperCase()}
                          </span>
                        </td>
                        <td className="px-4 py-3 font-mono text-[11px] text-slate-600">
                          <span className="px-1.5 py-0.5 rounded bg-slate-100 uppercase text-[10px] font-semibold">
                            {m.source_type || "manual"}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-slate-500 font-mono text-[11px]">
                          {m.file_name || "—"}
                        </td>
                        <td className="px-4 py-3 text-slate-600 text-[11px]">
                          {m.uploaded_by || "quality_engineer"}
                        </td>
                        <td className="px-4 py-3 text-slate-400 text-[11px]">
                          {m.upload_time || m.measured_at || "—"}
                        </td>
                        <td className="px-4 py-3 text-right">
                          <div className="flex items-center justify-end gap-1">
                            {isEditing ? (
                              <>
                                <button
                                  onClick={() => handleUpdateManualMeasurement(m.id)}
                                  className="px-2 py-0.5 bg-blue-600 text-white rounded text-[11px] font-semibold"
                                >
                                  Save
                                </button>
                                <button
                                  onClick={() => setEditingId(null)}
                                  className="px-2 py-0.5 bg-slate-200 text-slate-700 rounded text-[11px]"
                                >
                                  Cancel
                                </button>
                              </>
                            ) : (
                              <>
                                <button
                                  onClick={() => {
                                    setEditingId(m.id);
                                    setEditValue(m.value);
                                    setEditUnit(m.unit || "mm");
                                  }}
                                  className="p-1 hover:bg-slate-100 text-slate-600 rounded"
                                  title="Edit Measurement"
                                >
                                  <Edit2 className="w-3.5 h-3.5" />
                                </button>
                                <button
                                  onClick={() => handleDeleteManualMeasurement(m.id)}
                                  className="p-1 hover:bg-rose-50 text-rose-500 hover:text-rose-700 rounded"
                                  title="Delete Measurement"
                                >
                                  <Trash2 className="w-3.5 h-3.5" />
                                </button>
                              </>
                            )}
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                  {dbMeasurements.length === 0 && (
                    <tr>
                      <td colSpan={8} className="px-4 py-8 text-center text-slate-500">
                        No persisted measurements in database for this batch. Add measurements manually above or import an inspection file.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* TAB 3: IMAGE UPLOAD & VISION AGENT (Check 4) */}
      {activeTab === "image_upload" && (
        <div className="space-y-6">
          <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-xs">
            <h3 className="text-sm font-bold text-slate-900 mb-1">Upload Component Inspection Image</h3>
            <p className="text-xs text-slate-500 mb-4">
              Real-time image intake verified by content (PNG, JPEG, WEBP). Enforces path traversal protection and triggers Agent 2 (PatchCore + MobileNetV3).
            </p>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 items-start">
              <div>
                <div className="mb-3">
                  <label className="block text-xs font-semibold text-slate-700 mb-1">Component / Piece ID</label>
                  <input
                    type="text"
                    value={imageComponentId}
                    onChange={(e) => setImageComponentId(e.target.value)}
                    placeholder="e.g. P001"
                    className="w-full px-3 py-1.5 border border-slate-300 rounded-lg text-xs font-mono font-semibold"
                  />
                </div>

                <div
                  onClick={() => imageInputRef.current?.click()}
                  className="border-2 border-dashed border-slate-300 hover:border-indigo-500 bg-slate-50/60 hover:bg-indigo-50/20 rounded-xl p-6 text-center cursor-pointer transition-all flex flex-col items-center justify-center gap-2"
                >
                  <input
                    ref={imageInputRef}
                    type="file"
                    accept="image/*"
                    onChange={handleImageUpload}
                    className="hidden"
                  />
                  <div className="w-10 h-10 rounded-full bg-indigo-100 text-indigo-600 flex items-center justify-center">
                    {uploadingImage ? <Loader2 className="w-5 h-5 animate-spin" /> : <Camera className="w-5 h-5" />}
                  </div>
                  <div className="text-xs font-bold text-slate-800">
                    {uploadingImage ? "Processing Computer Vision Models..." : "Click or Drag Part Image"}
                  </div>
                  <p className="text-[11px] text-slate-400">PNG, JPEG, WEBP up to 10 MB. Verified by binary header bytes.</p>
                </div>
              </div>

              {/* AI Defect Prediction Card */}
              <div>
                <h4 className="text-xs font-bold text-slate-700 uppercase tracking-wider mb-2">
                  Computer Vision Finding (Agent 2)
                </h4>
                {imagePredictionResult ? (
                  <div className="p-4 bg-slate-50 border border-slate-200 rounded-xl space-y-3">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-bold text-slate-800">{imagePredictionResult.image_id}</span>
                      <span
                        className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                          imagePredictionResult.defect_detected
                            ? "bg-rose-100 text-rose-800 border border-rose-300"
                            : "bg-emerald-100 text-emerald-800 border border-emerald-300"
                        }`}
                      >
                        {imagePredictionResult.defect_detected ? "DEFECT DETECTED" : "NO DEFECT"}
                      </span>
                    </div>

                    <div className="grid grid-cols-2 gap-2 text-xs">
                      <div>
                        <span className="text-slate-400 text-[10px] block">Defect Type</span>
                        <span className="font-semibold text-slate-800">{imagePredictionResult.defect_type}</span>
                      </div>
                      <div>
                        <span className="text-slate-400 text-[10px] block">Model Confidence</span>
                        <span className="font-semibold text-slate-800">
                          {(imagePredictionResult.confidence * 100).toFixed(1)}%
                        </span>
                      </div>
                      <div>
                        <span className="text-slate-400 text-[10px] block">Zone / Location</span>
                        <span className="font-semibold text-slate-800">{imagePredictionResult.location || "Surface center"}</span>
                      </div>
                      <div>
                        <span className="text-slate-400 text-[10px] block">Review Status</span>
                        <span className="font-semibold text-amber-700">HUMAN_REVIEW_REQUIRED</span>
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="p-6 border border-dashed border-slate-200 rounded-xl text-center text-slate-400 text-xs">
                    Upload an image on the left to trigger real-time AI surface defect inspection.
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Uploaded Images Registry */}
          <div className="bg-white border border-slate-200 rounded-xl shadow-xs overflow-hidden">
            <div className="px-5 py-3.5 border-b border-slate-200 bg-slate-50/50 flex items-center justify-between">
              <span className="text-xs font-bold text-slate-800 uppercase tracking-wider">
                Inspection Images in Batch ({imagesList.length})
              </span>
              <span className="text-xs text-slate-500">ISO 9001 Clause 8.5.2 Visual Records</span>
            </div>

            <div className="p-4 grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4">
              {imagesList.map((img) => (
                <div key={img.id} className="border border-slate-200 rounded-lg p-3 bg-slate-50/50 space-y-2">
                  <div className="flex items-center justify-between text-xs font-bold text-blue-600">
                    <span>{img.component_id}</span>
                    <span className="text-[10px] font-mono text-slate-400">
                      {img.file_size_bytes ? `${(img.file_size_bytes / 1024).toFixed(1)} KB` : "Image"}
                    </span>
                  </div>
                  <div className="text-[11px] text-slate-600 truncate font-mono" title={img.file_name}>
                    {img.file_name}
                  </div>
                  <div className="text-[10px] text-slate-400">{img.uploaded_at || "Recent"}</div>
                </div>
              ))}
              {imagesList.length === 0 && (
                <div className="col-span-4 text-center py-6 text-slate-400 text-xs">
                  No images uploaded yet for {batchId}.
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* TAB 4: SPEC LIMITS & CHARTS (Functional Requirement 4) */}
      {activeTab === "charts" && (
        !report || report.total_inspected === 0 ? (
          <div className="p-12 text-center bg-white border border-slate-200 rounded-xl space-y-3 shadow-xs">
            <BarChart2 className="w-10 h-10 text-slate-400 mx-auto" />
            <h3 className="text-base font-bold text-slate-900">No Inspection Data Available</h3>
            <p className="text-sm text-slate-500 max-w-md mx-auto">
              No quality inspection data available to plot capability distribution or tolerance charts. Register a production batch and submit measurements to view analytics.
            </p>
          </div>
        ) : (
          <div className="space-y-6">
            {/* SIX SUMMARY ITEMS (Check 5 & Check 8) */}
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3.5">
            <div className="bg-white border border-slate-200 rounded-xl p-3.5 shadow-xs">
              <div className="text-[11px] font-semibold text-slate-500">1. Total Inspected</div>
              <div className="text-xl font-bold text-slate-900 mt-1">{report.total_inspected} pcs</div>
              <div className="text-[10px] text-slate-400 mt-0.5">Sample volume</div>
            </div>
            <div className="bg-white border border-slate-200 rounded-xl p-3.5 shadow-xs">
              <div className="text-[11px] font-semibold text-emerald-600">2. Conforming (Pass)</div>
              <div className="text-xl font-bold text-emerald-700 mt-1">{report.accepted} pcs</div>
              <div className="text-[10px] text-emerald-600 mt-0.5">Within tolerances</div>
            </div>
            <div className="bg-white border border-slate-200 rounded-xl p-3.5 shadow-xs">
              <div className="text-[11px] font-semibold text-rose-600">3. Nonconforming (Fail)</div>
              <div className="text-xl font-bold text-rose-700 mt-1">{report.nonconforming} pcs</div>
              <div className="text-[10px] text-rose-600 mt-0.5">Breached USL/LSL</div>
            </div>
            <div className="bg-white border border-slate-200 rounded-xl p-3.5 shadow-xs">
              <div className="text-[11px] font-semibold text-amber-600">4. Rejection Rate</div>
              <div className="text-xl font-bold text-amber-700 mt-1">{report.rejection_rate_percent.toFixed(1)}%</div>
              <div className="text-[10px] text-amber-600 mt-0.5">Sample percentage</div>
            </div>
            <div className="bg-white border border-slate-200 rounded-xl p-3.5 shadow-xs">
              <div className="text-[11px] font-semibold text-blue-600">5. Nominal Dimension</div>
              <div className="text-xl font-bold text-blue-800 mt-1">{report.nominal_mm.toFixed(2)} mm</div>
              <div className="text-[10px] text-blue-500 mt-0.5">Target drawing spec</div>
            </div>
            <div className="bg-white border border-slate-200 rounded-xl p-3.5 shadow-xs">
              <div className="text-[11px] font-semibold text-purple-600">6. Specification Limits</div>
              <div className="text-base font-bold text-purple-900 mt-1.5 font-mono">
                {report.lsl.toFixed(2)} - {report.usl.toFixed(2)}
              </div>
              <div className="text-[10px] text-purple-600 mt-0.5">LSL to USL range</div>
            </div>
          </div>

          {/* EPISTEMIC LABELLING & HUMAN DISPOSITION NOTICE (Check 6) */}
          <div className="bg-blue-50/60 border border-blue-200 rounded-xl p-4 flex flex-col md:flex-row items-start md:items-center justify-between gap-3 shadow-xs">
            <div className="flex items-center gap-3">
              <span className="px-2.5 py-1 bg-blue-100 text-blue-800 border border-blue-300 text-xs font-bold rounded-md uppercase tracking-wider shrink-0 flex items-center gap-1.5">
                <Check className="w-3.5 h-3.5 text-blue-700" />
                Observed Fact
              </span>
              <p className="text-xs text-slate-700 leading-relaxed">
                <span className="font-semibold text-slate-900">Sample Evaluation Notice:</span> The rejection rate of{" "}
                <span className="font-bold text-amber-700">{report.rejection_rate_percent.toFixed(1)}%</span> reflects this
                inspected sample only. Final physical batch disposition is an authorized human engineering decision. The system
                never automatically rejects batches or changes batch status to rejected.
              </p>
            </div>
            <div className="text-[11px] text-slate-600 font-mono bg-white px-3 py-1.5 rounded-lg border border-blue-200 shrink-0">
              Batch Status: <span className="font-bold text-amber-700">QUALITY_HOLD</span>
            </div>
          </div>

          {/* DISTRIBUTION METRICS SUMMARY STRIP (Check 5) */}
          <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-xs grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4 text-xs">
            <div>
              <span className="text-slate-400 text-[10px] uppercase font-bold block">Sample Mean (x̄)</span>
              <span className="text-sm font-bold font-mono text-slate-800">
                {report.mean !== undefined && report.mean !== null ? `${report.mean.toFixed(4)} mm` : "N/A"}
              </span>
            </div>
            <div>
              <span className="text-slate-400 text-[10px] uppercase font-bold block">Sample Std Dev (s, n-1)</span>
              <span className="text-sm font-bold font-mono text-slate-800">
                {report.std_dev_sample !== undefined ? `${report.std_dev_sample.toFixed(6)} mm` : "N/A"}
              </span>
            </div>
            <div>
              <span className="text-slate-400 text-[10px] uppercase font-bold block">Max Deviation Beyond Limit</span>
              <span className={`text-sm font-bold font-mono ${report.nonconforming > 0 ? "text-rose-600" : "text-emerald-600"}`}>
                +{((report.max_deviation_from_limit ?? 0)).toFixed(4)} mm
              </span>
            </div>
            <div>
              <span className="text-slate-400 text-[10px] uppercase font-bold block">Minimum Measured</span>
              <span className="text-sm font-bold font-mono text-slate-800">
                {report.min !== undefined && report.min !== null ? `${report.min.toFixed(4)} mm` : "N/A"}
              </span>
            </div>
            <div>
              <span className="text-slate-400 text-[10px] uppercase font-bold block">Maximum Measured</span>
              <span className="text-sm font-bold font-mono text-slate-800">
                {report.max !== undefined && report.max !== null ? `${report.max.toFixed(4)} mm` : "N/A"}
              </span>
            </div>
          </div>

          {/* HISTOGRAM WITH LSL & USL VERTICAL BOUNDARIES & DISTINCT OUT-OF-SPEC BARS (Check 8) */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* HISTOGRAM BAR CHART */}
            <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-xs">
              <div className="flex items-center justify-between mb-3">
                <div>
                  <h3 className="text-xs font-bold text-slate-800 uppercase tracking-wider">
                    Measurement Frequency Histogram
                  </h3>
                  <p className="text-[11px] text-slate-500">
                    Distribution binned against specification limits. Red bars = Out-of-Spec.
                  </p>
                </div>
                <div className="flex items-center gap-3 text-[11px] font-semibold">
                  <span className="flex items-center gap-1 text-emerald-700">
                    <span className="w-2.5 h-2.5 rounded-xs bg-emerald-500"></span> In-Spec
                  </span>
                  <span className="flex items-center gap-1 text-rose-700">
                    <span className="w-2.5 h-2.5 rounded-xs bg-rose-500"></span> Out-of-Spec
                  </span>
                </div>
              </div>

              {report.histogram_bins && report.histogram_bins.length > 0 ? (
                <div className="h-64 w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart
                      data={report.histogram_bins}
                      margin={{ top: 15, right: 15, left: -15, bottom: 25 }}
                    >
                      <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#F1F5F9" />
                      <XAxis
                        dataKey="bin"
                        tick={{ fontSize: 10, fill: "#475569" }}
                        interval={0}
                        angle={-15}
                        textAnchor="end"
                      />
                      <YAxis allowDecimals={false} tick={{ fontSize: 11, fill: "#475569" }} />
                      <Tooltip
                        formatter={(val: any, _name: any, item: any) => [
                          `${val} piece(s) (${item.payload.is_out_of_spec ? "NONCONFORMING" : "CONFORMING"})`,
                          "Frequency"
                        ]}
                      />
                      <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                        {report.histogram_bins.map((entry, index) => (
                          <Cell
                            key={`hist-cell-${index}`}
                            fill={entry.is_out_of_spec ? "#EF4444" : "#10B981"}
                          />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              ) : (
                <div className="h-64 flex items-center justify-center text-xs text-slate-400 border border-dashed border-slate-200 rounded-lg">
                  No histogram distribution data available.
                </div>
              )}
            </div>

            {/* RUN CHART: SAMPLES VS SPECIFICATION LIMITS */}
            <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-xs">
              <div className="flex items-center justify-between mb-3">
                <div>
                  <h3 className="text-xs font-bold text-slate-800 uppercase tracking-wider">
                    Sample Measurements vs Engineering Limits
                  </h3>
                  <p className="text-[11px] text-slate-500">
                    Individual sample values plotted against Nominal, USL, and LSL.
                  </p>
                </div>
                <div className="flex items-center gap-3 text-[11px] font-mono">
                  <span className="text-rose-600 font-bold">USL: {report.usl.toFixed(2)}</span>
                  <span className="text-emerald-600 font-bold">Nom: {report.nominal_mm.toFixed(2)}</span>
                  <span className="text-rose-600 font-bold">LSL: {report.lsl.toFixed(2)}</span>
                </div>
              </div>

              {chartData.length > 0 ? (
                <div className="h-64 w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={chartData} margin={{ top: 15, right: 15, left: -5, bottom: 20 }}>
                      <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#F1F5F9" />
                      <XAxis dataKey="sample_id" tick={{ fontSize: 11, fill: "#475569" }} />
                      <YAxis domain={[minY, maxY]} tick={{ fontSize: 11, fill: "#475569" }} tickFormatter={(v) => v.toFixed(2)} />
                      <Tooltip
                        formatter={(val: any) => [`${Number(val).toFixed(3)} mm`, "Measured Value"]}
                      />
                      <ReferenceLine
                        y={report.usl}
                        stroke="#EF4444"
                        strokeDasharray="4 4"
                        label={{ value: `USL (${report.usl.toFixed(2)})`, fill: "#EF4444", fontSize: 10, position: "top" }}
                      />
                      <ReferenceLine
                        y={report.nominal_mm}
                        stroke="#10B981"
                        strokeWidth={1.5}
                        label={{ value: `Nominal (${report.nominal_mm.toFixed(2)})`, fill: "#10B981", fontSize: 10, position: "top" }}
                      />
                      <ReferenceLine
                        y={report.lsl}
                        stroke="#EF4444"
                        strokeDasharray="4 4"
                        label={{ value: `LSL (${report.lsl.toFixed(2)})`, fill: "#EF4444", fontSize: 10, position: "bottom" }}
                      />
                      <Bar dataKey="measured" radius={[4, 4, 0, 0]}>
                        {chartData.map((entry, index) => (
                          <Cell key={`run-cell-${index}`} fill={entry.is_conforming ? "#3B82F6" : "#EF4444"} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              ) : (
                <div className="h-64 flex items-center justify-center text-xs text-slate-400 border border-dashed border-slate-200 rounded-lg">
                  No sample measurements available.
                </div>
              )}
            </div>
          </div>

          {/* TABLE OF NONCONFORMING COMPONENTS (Check 5 & Check 8) */}
          <div className="bg-white border border-slate-200 rounded-xl shadow-xs overflow-hidden">
            <div className="px-5 py-3.5 border-b border-slate-200 bg-slate-50/50 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-rose-600" />
                <span className="text-xs font-bold text-slate-800 uppercase tracking-wider">
                  Nonconforming Components Audit Table ({report.nonconforming})
                </span>
              </div>
              <span className="text-xs text-slate-500 font-mono">
                {report.nonconforming === 0
                  ? "100% Conforming Batch"
                  : `${report.nonconforming} of ${report.total_inspected} parts out of spec`}
              </span>
            </div>

            {report.nonconforming === 0 ? (
              <div className="p-8 text-center text-emerald-700 bg-emerald-50/20">
                <CheckCircle2 className="w-8 h-8 text-emerald-500 mx-auto mb-2" />
                <h4 className="text-xs font-bold uppercase tracking-wider">Zero Nonconforming Components</h4>
                <p className="text-xs text-slate-500 mt-1">
                  All {report.total_inspected} sample measurements strictly lie within engineering tolerance band [{report.lsl.toFixed(2)} - {report.usl.toFixed(2)} mm].
                </p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs border-collapse">
                  <thead>
                    <tr className="bg-slate-50/80 border-b border-slate-200 text-slate-600 font-bold text-[11px] uppercase tracking-wider">
                      <th className="py-2.5 px-4">Component ID</th>
                      <th className="py-2.5 px-4">Measured Value</th>
                      <th className="py-2.5 px-4">Nominal</th>
                      <th className="py-2.5 px-4">Limit Breached</th>
                      <th className="py-2.5 px-4">Deviation Beyond Limit</th>
                      <th className="py-2.5 px-4">Deviation from Nominal</th>
                      <th className="py-2.5 px-4">Classification</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 font-mono">
                    {(report.nonconforming_items && report.nonconforming_items.length > 0
                      ? report.nonconforming_items
                      : report.measurements.filter((m) => !m.is_conforming).map((m) => ({
                          sample_id: m.sample_id,
                          component_id: m.sample_id,
                          measured_value: m.measured_value,
                          nominal_mm: report.nominal_mm,
                          limit_breached: m.measured_value > report.usl ? "EXCEEDS_USL" : "BELOW_LSL",
                          deviation_from_limit: m.deviation_from_limit,
                          deviation_from_nominal: m.deviation_from_nominal,
                        }))
                    ).map((item, idx) => (
                      <tr key={idx} className="hover:bg-rose-50/30 transition-colors">
                        <td className="py-2.5 px-4 font-bold text-slate-900">{item.component_id || item.sample_id}</td>
                        <td className="py-2.5 px-4 font-bold text-rose-700">{item.measured_value.toFixed(4)} mm</td>
                        <td className="py-2.5 px-4 text-slate-600">{report.nominal_mm.toFixed(2)} mm</td>
                        <td className="py-2.5 px-4">
                          <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-rose-100 text-rose-800 border border-rose-300">
                            {item.limit_breached === "EXCEEDS_USL"
                              ? `> USL (${report.usl.toFixed(2)})`
                              : `< LSL (${report.lsl.toFixed(2)})`}
                          </span>
                        </td>
                        <td className="py-2.5 px-4 font-bold text-rose-600">
                          +{item.deviation_from_limit.toFixed(4)} mm
                        </td>
                        <td className="py-2.5 px-4 text-slate-700">
                          {item.deviation_from_nominal !== undefined
                            ? `${item.deviation_from_nominal > 0 ? "+" : ""}${item.deviation_from_nominal.toFixed(4)} mm`
                            : "—"}
                        </td>
                        <td className="py-2.5 px-4 font-sans">
                          <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-100 text-amber-800 border border-amber-300">
                            NCR Incident Triggered
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
        )
      )}
    </div>
  );
};

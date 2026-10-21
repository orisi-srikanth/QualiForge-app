import React, { useState, useEffect } from "react";
import { api } from "../api";
import { ProductSpec } from "../types";
import {
  CheckCircle2, ArrowRight, ArrowLeft, Upload, FileSpreadsheet,
  Camera, Activity, Layers, AlertCircle, Loader2, Sparkles,
  FileCheck, ShieldCheck, Factory, Cpu, Clock, Lock, AlertTriangle, Image as ImageIcon, X
} from "lucide-react";

interface Props {
  onNavigate: (page: string, params?: Record<string, string>) => void;
  onBatchCreated?: (batchId: string) => void;
}

const STEPS = [
  { id: 1, title: "Batch Details", desc: "Batch identification & naming" },
  { id: 2, title: "Product & Machine", desc: "Select part & assigned CNC cell" },
  { id: 3, title: "Shift & Material", desc: "Quantity, schedule & heat lot" },
  { id: 4, title: "Measurements", desc: "CMM measurements intake" },
  { id: 5, title: "Process Telemetry", desc: "Machine sensor logs intake" },
  { id: 6, title: "Product Images", desc: "Surface photography upload" },
  { id: 7, title: "Validation Review", desc: "Pre-submission deterministic check" },
  { id: 8, title: "Submit & Analysis", desc: "Trigger 8-agent quality pipeline" },
];

export const BatchRegistrationWizard: React.FC<Props> = ({ onNavigate, onBatchCreated }) => {
  const [currentStep, setCurrentStep] = useState(1);
  const [products, setProducts] = useState<ProductSpec[]>([]);
  const [machines, setMachines] = useState<any[]>([]);
  const [loadingData, setLoadingData] = useState(true);

  const [batchNumber, setBatchNumber] = useState(`BATCH-${Math.floor(1000 + Math.random() * 9000)}`);
  const [selectedProductId, setSelectedProductId] = useState("");
  const [selectedMachineId, setSelectedMachineId] = useState("");
  const [shift, setShift] = useState("Morning");
  const [quantity, setQuantity] = useState(500);
  const [materialLot, setMaterialLot] = useState("LOT-AISI1045-88A");
  const [operatorRef, setOperatorRef] = useState("OP-04-JOHN");
  const [startTime, setStartTime] = useState(new Date().toISOString().slice(0, 16));

  const [measurementFile, setMeasurementFile] = useState<File | null>(null);
  const [measurementUploadStatus, setMeasurementUploadStatus] = useState<string | null>(null);
  const [measurementResults, setMeasurementResults] = useState<any | null>(null);
  const [measurementError, setMeasurementError] = useState<string | null>(null);

  const [telemetryFile, setTelemetryFile] = useState<File | null>(null);
  const [telemetryUploadStatus, setTelemetryUploadStatus] = useState<string | null>(null);
  const [telemetryError, setTelemetryError] = useState<string | null>(null);

  const [imageFile, setImageFile] = useState<File | null>(null);
  const [imageUploadStatus, setImageUploadStatus] = useState<string | null>(null);
  const [imageUploadData, setImageUploadData] = useState<any | null>(null);
  const [imagePreviewUrl, setImagePreviewUrl] = useState<string | null>(null);
  const [imageError, setImageError] = useState<string | null>(null);

  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [completedWorkflow, setCompletedWorkflow] = useState<any | null>(null);

  useEffect(() => {
    const fetchPrerequisites = async () => {
      try {
        setLoadingData(true);
        const [prods, machs] = await Promise.all([
          api.getProducts().catch(() => []),
          api.getMachines().catch(() => [])
        ]);
        setProducts(prods);
        setMachines(machs);
        if (prods.length > 0) setSelectedProductId(prods[0].product_id);
        if (machs.length > 0) setSelectedMachineId(machs[0].machine_id);
      } catch (err) {
        console.error(err);
      } finally {
        setLoadingData(false);
      }
    };
    fetchPrerequisites();
  }, []);

  const selectedProduct = products.find((p) => p.product_id === selectedProductId);

  // Verification and Gating Prerequisites
  const isStep1Complete = Boolean(batchNumber && batchNumber.trim().length > 0);
  const isStep2Complete = Boolean(selectedProductId && selectedMachineId);
  const isStep3Complete = Boolean(shift && Number(quantity) > 0 && materialLot && materialLot.trim().length > 0);
  const isStep4Complete = Boolean(measurementUploadStatus === "success" && measurementFile);
  const isStep5Complete = Boolean(telemetryUploadStatus === "success" && telemetryFile);
  const isStep6Complete = Boolean(imageUploadStatus === "success" && imageFile);

  const prerequisites = [
    {
      step: 1,
      title: "Batch Identification",
      isComplete: isStep1Complete,
      summary: batchNumber || "Not specified",
      requiredAction: "Specify batch number"
    },
    {
      step: 2,
      title: "Product & Machine Cell",
      isComplete: isStep2Complete,
      summary: `${selectedProduct?.name || selectedProductId || "None"} (${selectedMachineId || "No Machine"})`,
      requiredAction: "Select product and machine"
    },
    {
      step: 3,
      title: "Shift, Quantity & Heat Lot",
      isComplete: isStep3Complete,
      summary: `${shift} Shift • ${quantity} units • Lot ${materialLot || "None"}`,
      requiredAction: "Configure quantity and heat lot"
    },
    {
      step: 4,
      title: "CMM Measurement Intake",
      isComplete: isStep4Complete,
      summary: measurementFile ? measurementFile.name : "No file uploaded",
      requiredAction: "Upload CMM inspection CSV/Excel"
    },
    {
      step: 5,
      title: "Machine Telemetry Stream",
      isComplete: isStep5Complete,
      summary: telemetryFile ? telemetryFile.name : "No file uploaded",
      requiredAction: "Upload machine sensor logs CSV"
    },
    {
      step: 6,
      title: "Component Surface Image",
      isComplete: isStep6Complete,
      summary: imageFile ? imageFile.name : "No image uploaded",
      requiredAction: "Upload verified component photo"
    }
  ];

  const allPrerequisitesComplete = prerequisites.every((p) => p.isComplete);
  const completedCount = prerequisites.filter((p) => p.isComplete).length;

  const handleMeasurementUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setMeasurementFile(file);
    setMeasurementUploadStatus("uploading");
    setMeasurementError(null);
    try {
      const res = await api.uploadInspectionFile(file, batchNumber, undefined, false, selectedProductId);
      setMeasurementResults(res);
      setMeasurementUploadStatus("success");
    } catch (err: any) {
      setMeasurementUploadStatus("error");
      const msg = err?.detail?.message || err?.detail || err?.message || "Error parsing inspection file. Please verify CSV/Excel format.";
      setMeasurementError(typeof msg === "string" ? msg : JSON.stringify(msg));
    }
  };

  const handleTelemetryUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setTelemetryFile(file);
    setTelemetryUploadStatus("uploading");
    setTelemetryError(null);
    try {
      await api.uploadProcessTelemetry(file, batchNumber, selectedMachineId);
      setTelemetryUploadStatus("success");
    } catch (err: any) {
      setTelemetryUploadStatus("error");
      const msg = err?.detail?.message || err?.detail || err?.message || "Failed to ingest telemetry file.";
      setTelemetryError(typeof msg === "string" ? msg : JSON.stringify(msg));
    }
  };

  const handleImageUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setImageError(null);

    // Fast client pre-check: verify image file extension and MIME type
    if (!file.type.startsWith("image/") && !/\.(png|jpe?g|webp|bmp)$/i.test(file.name)) {
      setImageUploadStatus("error");
      setImageFile(null);
      setImagePreviewUrl(null);
      setImageError(`Invalid file format: "${file.name}" is not a recognized image. Please select a PNG, JPEG, WEBP, or BMP file.`);
      e.target.value = "";
      return;
    }

    const fnLower = file.name.toLowerCase();
    const irrelevantKeywords = [
      "receipt", "invoice", "document", "screenshot", "avatar", "profile",
      "cat", "dog", "pet", "animal", "landscape", "wallpaper", "car", "selfie",
      "meme", "food", "poster", "logo", "icon", "banner", "face", "person",
      "resume", "ticket", "bill", "payment"
    ];
    const matchedIrrelevant = irrelevantKeywords.find((k) => fnLower.includes(k));
    if (matchedIrrelevant) {
      setImageUploadStatus("error");
      setImageFile(null);
      setImagePreviewUrl(null);
      setImageError(`Unrelated file rejected: "${file.name}" appears to be an unrelated file (${matchedIrrelevant}). Please upload a valid component inspection photograph.`);
      e.target.value = "";
      return;
    }

    const prodName = (selectedProduct?.name || selectedProduct?.part_number || "Shaft").toLowerCase();
    if (prodName.includes("shaft")) {
      const incompatible = ["screw", "metal_nut", "nut", "cable", "transistor", "wire", "pcb", "textile", "wood", "zipper", "capsule", "pill", "bottle", "hazelnut", "leather", "gear"];
      const matchedIncomp = incompatible.find((k) => fnLower.includes(k));
      if (matchedIncomp) {
        setImageUploadStatus("error");
        setImageFile(null);
        setImagePreviewUrl(null);
        setImageError(`Product mismatch rejected: "${file.name}" represents an incompatible component category (${matchedIncomp}), but selected product is "${selectedProduct?.name || "Precision Drive Shaft"}". Please upload a valid machined shaft component image.`);
        e.target.value = "";
        return;
      }
    }

    setImageFile(file);
    setImagePreviewUrl(URL.createObjectURL(file));
    setImageUploadStatus("uploading");

    try {
      // Ingest image rapidly with skip_inference=true. YOLO inference will run during Step 8 Agent Orchestration.
      const res = await api.uploadBatchImage(file, batchNumber, selectedProductId);
      setImageUploadData(res);
      setImageUploadStatus("success");
    } catch (err: any) {
      setImageUploadStatus("error");
      setImageFile(null);
      setImagePreviewUrl(null);
      const msg = err?.detail?.message || err?.detail || err?.message || "Failed to validate component image.";
      setImageError(typeof msg === "string" ? msg : JSON.stringify(msg));
      e.target.value = "";
    }
  };

  const handleSubmitBatch = async () => {
    if (!allPrerequisitesComplete) {
      setSubmitError("Cannot orchestrate agents: please complete all required steps and upload valid measurement, telemetry, and component image files.");
      return;
    }
    setSubmitting(true);
    setSubmitError(null);
    try {
      const batchPayload = {
        batch_number: batchNumber,
        product_id: selectedProductId,
        machine_id: selectedMachineId,
        shift,
        quantity: Number(quantity),
        material_lot: materialLot,
        operator_ref: operatorRef,
        start_time: startTime,
        status: "IN_PROGRESS"
      };
      try {
        await api.createBatch(batchPayload);
      } catch (createErr: any) {
        console.warn("Batch record already registered or initialized:", createErr);
      }

      const wfRes = await api.runOrchestratedPipeline(batchNumber);
      setCompletedWorkflow(wfRes);
      if (onBatchCreated) onBatchCreated(batchNumber);
    } catch (err: any) {
      setSubmitError(err?.message || "Failed to create batch and execute multi-agent analysis.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6">

      <div className="p-4 bg-white border border-slate-200 rounded-xl shadow-xs">
        <div className="flex items-center justify-between text-xs font-semibold text-slate-500 mb-3">
          <span>Step {currentStep} of 8: {STEPS[currentStep - 1].title}</span>
          <span>{STEPS[currentStep - 1].desc}</span>
        </div>
        <div className="grid grid-cols-8 gap-1.5">
          {STEPS.map((s) => (
            <button
              key={s.id}
              onClick={() => setCurrentStep(s.id)}
              className={`h-2.5 rounded-full transition-all cursor-pointer ${
                s.id === currentStep
                  ? "bg-blue-600 ring-2 ring-blue-300 ring-offset-1"
                  : s.id < currentStep
                  ? "bg-emerald-500 hover:bg-emerald-600"
                  : "bg-slate-200 hover:bg-slate-300"
              }`}
              title={`Step ${s.id}: ${s.title} (${s.desc})`}
            />
          ))}
        </div>
      </div>

      <div className="p-6 bg-white border border-slate-200 rounded-2xl shadow-xs">
        {loadingData ? (
          <div className="py-12 text-center text-xs text-slate-500 space-y-2">
            <Loader2 className="w-6 h-6 animate-spin text-blue-600 mx-auto" />
            <div>Loading product catalogs and registered machine cells...</div>
          </div>
        ) : (
          <div>

            {currentStep === 1 && (
              <div className="space-y-4">
                <h3 className="text-base font-bold text-slate-900">Step 1: Batch Identification & Lot Tracking</h3>
                <p className="text-xs text-slate-600">
                  Assign a unique production batch number in accordance with factory traceability standards.
                </p>

                <div className="space-y-3 pt-2">
                  <div>
                    <label className="block text-xs font-semibold text-slate-700">Batch Number (Unique Identifier)</label>
                    <input
                      type="text"
                      value={batchNumber}
                      onChange={(e) => setBatchNumber(e.target.value)}
                      required
                      className="mt-1 block w-full px-3 py-2 text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-600 focus:outline-none font-mono"
                      placeholder="e.g. BATCH-0245"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-slate-700">Operator Reference / Station ID</label>
                    <input
                      type="text"
                      value={operatorRef}
                      onChange={(e) => setOperatorRef(e.target.value)}
                      className="mt-1 block w-full px-3 py-2 text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-600 focus:outline-none font-mono"
                      placeholder="e.g. OP-04-JOHN"
                    />
                  </div>
                </div>
              </div>
            )}

            {currentStep === 2 && (
              <div className="space-y-4">
                <h3 className="text-base font-bold text-slate-900">Step 2: Product Specification & Machining Cell</h3>
                <p className="text-xs text-slate-600">
                  Select the manufactured part specification to automatically attach nominal tolerances and engineering limits.
                </p>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-2">
                  <div>
                    <label className="block text-xs font-semibold text-slate-700">Product / Part Specification</label>
                    <select
                      value={selectedProductId}
                      onChange={(e) => setSelectedProductId(e.target.value)}
                      className="mt-1 block w-full px-3 py-2 text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-600 focus:outline-none"
                    >
                      {products.map((p) => (
                        <option key={p.product_id} value={p.product_id}>
                          {p.name || p.part_number || p.product_id} ({p.product_id})
                        </option>
                      ))}
                    </select>

                    {selectedProduct && (
                      <div className="mt-3 p-3 bg-slate-50 border border-slate-200 rounded-lg text-xs space-y-1">
                        <div className="font-semibold text-slate-800">Assigned Specification:</div>
                        <div className="text-slate-600">Nominal: <strong className="font-mono">{selectedProduct.nominal_mm} {selectedProduct.unit}</strong></div>
                        <div className="text-slate-600">
                          Tolerances: <span className="font-mono text-emerald-700 font-semibold">[{selectedProduct.lsl} to {selectedProduct.usl} {selectedProduct.unit}]</span>
                        </div>
                      </div>
                    )}
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-slate-700">Assigned Machining Cell</label>
                    <select
                      value={selectedMachineId}
                      onChange={(e) => setSelectedMachineId(e.target.value)}
                      className="mt-1 block w-full px-3 py-2 text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-600 focus:outline-none"
                    >
                      {machines.map((m) => (
                        <option key={m.machine_id} value={m.machine_id}>
                          {m.machine_name} ({m.machine_id})
                        </option>
                      ))}
                    </select>
                  </div>
                </div>
              </div>
            )}

            {currentStep === 3 && (
              <div className="space-y-4">
                <h3 className="text-base font-bold text-slate-900">Step 3: Shift, Production Quantity & Material Lot</h3>
                <p className="text-xs text-slate-600">
                  Record lot parameters for complete raw material traceability.
                </p>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-2">
                  <div>
                    <label className="block text-xs font-semibold text-slate-700">Work Shift</label>
                    <select
                      value={shift}
                      onChange={(e) => setShift(e.target.value)}
                      className="mt-1 block w-full px-3 py-2 text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-600 focus:outline-none"
                    >
                      <option value="Morning">Morning (06:00 - 14:00)</option>
                      <option value="Evening">Evening (14:00 - 22:00)</option>
                      <option value="Night">Night (22:00 - 06:00)</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-slate-700">Production Quantity (Units)</label>
                    <input
                      type="number"
                      value={quantity}
                      onChange={(e) => setQuantity(Number(e.target.value))}
                      min={1}
                      className="mt-1 block w-full px-3 py-2 text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-600 focus:outline-none font-mono"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-slate-700">Raw Material Heat / Ingot Lot</label>
                    <input
                      type="text"
                      value={materialLot}
                      onChange={(e) => setMaterialLot(e.target.value)}
                      className="mt-1 block w-full px-3 py-2 text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-600 focus:outline-none font-mono"
                      placeholder="e.g. LOT-AISI1045-88A"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-slate-700">Start Timestamp</label>
                    <input
                      type="datetime-local"
                      value={startTime}
                      onChange={(e) => setStartTime(e.target.value)}
                      className="mt-1 block w-full px-3 py-2 text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-600 focus:outline-none font-mono"
                    />
                  </div>
                </div>
              </div>
            )}

            {currentStep === 4 && (
              <div className="space-y-4">
                <h3 className="text-base font-bold text-slate-900">Step 4: Dimensional Inspection Measurements Intake</h3>
                <p className="text-xs text-slate-600">
                  Upload CMM finishing measurement sheet (.csv, .xlsx, .xls) for automated boundary-safe specification conformance.
                </p>

                <div className="p-6 border-2 border-dashed border-slate-300 hover:border-blue-500 rounded-xl bg-slate-50/50 text-center space-y-3 transition-colors">
                  <FileSpreadsheet className="w-10 h-10 text-slate-400 mx-auto" />
                  <div>
                    <label className="cursor-pointer px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs font-semibold shadow-xs inline-block">
                      <span>Choose Inspection CSV / Excel</span>
                      <input
                        type="file"
                        accept=".csv, .xlsx, .xls"
                        onChange={handleMeasurementUpload}
                        className="hidden"
                      />
                    </label>
                  </div>
                  <div className="text-[11px] text-slate-500">
                    Expected columns: <code className="font-mono bg-slate-200 px-1 py-0.5 rounded">component_id, measured_value, unit</code>
                  </div>

                  {measurementUploadStatus === "uploading" && (
                    <div className="text-xs text-blue-600 flex items-center justify-center gap-1 font-semibold">
                      <Loader2 className="w-4 h-4 animate-spin" /> Ingesting and normalizing measurements...
                    </div>
                  )}

                  {measurementUploadStatus === "success" && (
                    <div className="text-xs text-emerald-700 flex items-center justify-center gap-1 font-semibold bg-emerald-50 py-1.5 rounded-lg border border-emerald-200">
                      <CheckCircle2 className="w-4 h-4" /> File &quot;{measurementFile?.name}&quot; successfully validated and ingested.
                    </div>
                  )}

                  {measurementUploadStatus === "error" && (
                    <div className="text-xs text-rose-700 flex items-center justify-center gap-1 font-semibold bg-rose-50 py-1.5 px-3 rounded-lg border border-rose-200">
                      <AlertCircle className="w-4 h-4 shrink-0" />
                      <span>{measurementError || "Error parsing inspection file. Please verify CSV/Excel format."}</span>
                    </div>
                  )}
                </div>
              </div>
            )}

            {currentStep === 5 && (
              <div className="space-y-4">
                <h3 className="text-base font-bold text-slate-900">Step 5: Machine Telemetry & Sensor Log Stream</h3>
                <p className="text-xs text-slate-600">
                  Upload machine telemetry logs (.csv) containing vibration, spindle speed, feed rate, and tool cycles.
                </p>

                <div className="p-6 border-2 border-dashed border-slate-300 hover:border-blue-500 rounded-xl bg-slate-50/50 text-center space-y-3 transition-colors">
                  <Activity className="w-10 h-10 text-cyan-600 mx-auto" />
                  <div>
                    <label className="cursor-pointer px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs font-semibold shadow-xs inline-block">
                      <span>Choose Telemetry CSV</span>
                      <input
                        type="file"
                        accept=".csv, .xlsx"
                        onChange={handleTelemetryUpload}
                        className="hidden"
                      />
                    </label>
                  </div>
                  <div className="text-[11px] text-slate-500">
                    Parameters: <code className="font-mono bg-slate-200 px-1 py-0.5 rounded">vibration_mms, tool_cycles, spindle_rpm, feed_rate_mm_rev</code>
                  </div>

                  {telemetryUploadStatus === "uploading" && (
                    <div className="text-xs text-blue-600 flex items-center justify-center gap-1 font-semibold">
                      <Loader2 className="w-4 h-4 animate-spin" /> Ingesting and evaluating telemetry streams...
                    </div>
                  )}

                  {telemetryUploadStatus === "success" && (
                    <div className="text-xs text-emerald-700 flex items-center justify-center gap-1 font-semibold bg-emerald-50 py-1.5 rounded-lg border border-emerald-200">
                      <CheckCircle2 className="w-4 h-4" /> Telemetry log &quot;{telemetryFile?.name}&quot; successfully connected.
                    </div>
                  )}

                  {telemetryUploadStatus === "error" && (
                    <div className="text-xs text-rose-700 flex items-center justify-center gap-1 font-semibold bg-rose-50 py-1.5 px-3 rounded-lg border border-rose-200">
                      <AlertCircle className="w-4 h-4 shrink-0" />
                      <span>{telemetryError || "Failed to ingest telemetry file."}</span>
                    </div>
                  )}
                </div>
              </div>
            )}

            {currentStep === 6 && (
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="text-base font-bold text-slate-900">Step 6: High-Resolution Component Photography Intake</h3>
                    <p className="text-xs text-slate-600 mt-0.5">
                      Ingest component surface photographs for the selected product ({selectedProduct?.name || selectedProductId || "Shaft"}).
                      Images are verified for product relevance and saved; deep learning defect classification executes during agent orchestration in Step 8.
                    </p>
                  </div>
                </div>

                <div className="p-6 border-2 border-dashed border-slate-300 hover:border-blue-500 rounded-xl bg-slate-50/50 text-center space-y-4 transition-colors">
                  {!imageFile && imageUploadStatus !== "uploading" && (
                    <>
                      <div className="w-12 h-12 bg-purple-100 rounded-xl flex items-center justify-center mx-auto text-purple-600">
                        <Camera className="w-6 h-6" />
                      </div>
                      <div className="space-y-1">
                        <div className="text-xs font-bold text-slate-800">
                          Upload Component Image for {selectedProduct?.name || "Selected Product"}
                        </div>
                        <div className="text-[11px] text-slate-500">
                          Accepts PNG, JPEG, WEBP, BMP (Minimum 100x100 resolution)
                        </div>
                      </div>
                      <div>
                        <label className="cursor-pointer px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs font-semibold shadow-xs inline-flex items-center gap-1.5 transition-colors">
                          <Upload className="w-3.5 h-3.5" />
                          <span>Choose Component Image</span>
                          <input
                            type="file"
                            accept="image/*"
                            onChange={handleImageUpload}
                            className="hidden"
                          />
                        </label>
                      </div>
                      <div className="p-2.5 bg-blue-50/70 border border-blue-200/60 rounded-lg text-left text-[11px] text-blue-900 flex items-start gap-2">
                        <Sparkles className="w-4 h-4 text-blue-600 shrink-0 mt-0.5" />
                        <div>
                          <strong>Relevance Check Active:</strong> Only valid manufactured component photos matching <em>{selectedProduct?.name || "Precision Shaft"}</em> are accepted.
                          Unrelated documents, screenshots, avatars, or mismatched part categories will be rejected.
                          <div className="mt-1 text-slate-600 font-mono text-[10px]">
                            Sample photos: <code>data/synthetic_shafts/images/</code> or <code>backend/app/static/uploads/samples/</code>
                          </div>
                        </div>
                      </div>
                    </>
                  )}

                  {imageUploadStatus === "uploading" && (
                    <div className="py-6 space-y-2 text-center">
                      <Loader2 className="w-6 h-6 animate-spin text-blue-600 mx-auto" />
                      <div className="text-xs text-blue-700 font-semibold">
                        Validating component relevance and ingesting image...
                      </div>
                      <div className="text-[11px] text-slate-500">
                        Fast intake active &bull; Heavy computer vision inference deferred to Step 8 multi-agent orchestration
                      </div>
                    </div>
                  )}

                  {imageUploadStatus === "success" && imageFile && (
                    <div className="p-4 bg-emerald-50/80 border border-emerald-200 rounded-xl text-left space-y-3">
                      <div className="flex items-start justify-between">
                        <div className="flex items-center gap-2">
                          <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0" />
                          <div>
                            <div className="text-xs font-bold text-emerald-950">Component Image Verified & Ingested</div>
                            <div className="text-[11px] text-emerald-700">Matched to product category: <strong>{selectedProduct?.name || "Precision Drive Shaft"}</strong></div>
                          </div>
                        </div>
                        <label className="cursor-pointer px-2.5 py-1 text-[11px] font-semibold text-slate-600 hover:text-slate-900 bg-white border border-slate-300 rounded-lg shadow-2xs hover:bg-slate-50 transition-colors">
                          Replace Image
                          <input type="file" accept="image/*" onChange={handleImageUpload} className="hidden" />
                        </label>
                      </div>

                      <div className="flex items-center gap-4 pt-1">
                        {imagePreviewUrl && (
                          <img
                            src={imagePreviewUrl}
                            alt="Component Preview"
                            className="w-20 h-20 object-cover rounded-lg border border-emerald-300 shadow-2xs"
                          />
                        )}
                        <div className="text-xs space-y-1 text-slate-700">
                          <div><span className="text-slate-500">File Name:</span> <strong className="font-mono">{imageFile.name}</strong></div>
                          <div><span className="text-slate-500">File Size:</span> <strong className="font-mono">{(imageFile.size / 1024).toFixed(1)} KB</strong></div>
                          <div>
                            <span className="text-slate-500">Relevance:</span>{" "}
                            <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-bold bg-emerald-100 text-emerald-800">
                              ✓ Relevant Component Photo
                            </span>
                          </div>
                        </div>
                      </div>

                      <div className="text-[11px] text-emerald-800 bg-emerald-100/60 p-2 rounded-lg border border-emerald-200">
                        ⚡ <strong>Fast Intake Complete:</strong> Image stored and linked to batch <code className="font-mono">{batchNumber}</code>. Multi-scale YOLO defect classification and bounding-box localization will run seamlessly during Step 8 Agent Orchestration.
                      </div>
                    </div>
                  )}

                  {imageUploadStatus === "error" && (
                    <div className="p-4 bg-rose-50 border border-rose-300 rounded-xl text-left space-y-3">
                      <div className="flex items-start gap-2.5">
                        <AlertCircle className="w-5 h-5 text-rose-600 shrink-0 mt-0.5" />
                        <div className="space-y-1">
                          <div className="text-xs font-bold text-rose-950">Unrelated / Incompatible Image Rejected</div>
                          <div className="text-xs text-rose-800 leading-relaxed">{imageError}</div>
                        </div>
                      </div>

                      <div className="p-2.5 bg-white border border-rose-200 rounded-lg text-[11px] text-slate-700 space-y-1">
                        <div className="font-semibold text-slate-900">How to resolve:</div>
                        <ul className="list-disc list-inside text-slate-600 space-y-0.5">
                          <li>Upload an authentic surface inspection photograph of the selected product (<strong>{selectedProduct?.name || "Precision Shaft"}</strong>).</li>
                          <li>Ensure the file is not a document, invoice, screenshot, personal photo, or mismatched part (such as screws, nuts, or cables).</li>
                          <li>You can find validated sample images in <code className="bg-slate-100 px-1 py-0.5 rounded text-[10px]">data/synthetic_shafts/images/</code> or <code className="bg-slate-100 px-1 py-0.5 rounded text-[10px]">backend/app/static/uploads/samples/</code>.</li>
                        </ul>
                      </div>

                      <div className="pt-1">
                        <label className="cursor-pointer px-3.5 py-1.5 bg-rose-600 hover:bg-rose-700 text-white rounded-lg text-xs font-semibold shadow-xs inline-flex items-center gap-1.5 transition-colors">
                          <Upload className="w-3.5 h-3.5" />
                          <span>Choose Valid Component Image</span>
                          <input type="file" accept="image/*" onChange={handleImageUpload} className="hidden" />
                        </label>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}

            {currentStep === 7 && (
              <div className="space-y-4">
                <h3 className="text-base font-bold text-slate-900">Step 7: Pre-Submission Deterministic Validation</h3>
                <p className="text-xs text-slate-600">
                  Review verified batch parameters and data inputs before triggering multi-agent quality orchestration.
                </p>

                <div className="p-4 bg-slate-50 border border-slate-200 rounded-xl space-y-4 text-xs">
                  <div className="grid grid-cols-2 gap-2 pb-3 border-b border-slate-200">
                    <div><span className="text-slate-500">Batch Number:</span> <strong className="font-mono text-slate-900">{batchNumber}</strong></div>
                    <div><span className="text-slate-500">Product:</span> <strong className="text-slate-900">{selectedProduct?.name || selectedProduct?.part_number || selectedProductId}</strong></div>
                    <div><span className="text-slate-500">Machining Cell:</span> <strong className="font-mono text-slate-900">{selectedMachineId}</strong></div>
                    <div><span className="text-slate-500">Shift & Units:</span> <strong className="text-slate-900">{shift} &bull; {quantity} units</strong></div>
                    <div><span className="text-slate-500">Material Heat:</span> <strong className="font-mono text-slate-900">{materialLot}</strong></div>
                    <div><span className="text-slate-500">Operator ID:</span> <strong className="font-mono text-slate-900">{operatorRef}</strong></div>
                  </div>

                  <div className="space-y-2">
                    <div className="font-semibold text-slate-800">Required Intake Files & Data Streams:</div>

                    <div className="flex items-center justify-between p-2 rounded-lg bg-white border border-slate-200">
                      <div className="flex items-center gap-2">
                        {isStep4Complete ? (
                          <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                        ) : (
                          <AlertTriangle className="w-4 h-4 text-amber-500" />
                        )}
                        <span className="text-slate-700">CMM Inspection Measurements:</span>
                      </div>
                      {isStep4Complete ? (
                        <span className="font-mono font-semibold text-emerald-700 text-[11px]">{measurementFile?.name}</span>
                      ) : (
                        <button
                          onClick={() => setCurrentStep(4)}
                          className="px-2 py-0.5 bg-amber-100 hover:bg-amber-200 text-amber-800 font-semibold rounded text-[11px] cursor-pointer"
                        >
                          Upload in Step 4 &rarr;
                        </button>
                      )}
                    </div>

                    <div className="flex items-center justify-between p-2 rounded-lg bg-white border border-slate-200">
                      <div className="flex items-center gap-2">
                        {isStep5Complete ? (
                          <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                        ) : (
                          <AlertTriangle className="w-4 h-4 text-amber-500" />
                        )}
                        <span className="text-slate-700">CNC Machine Telemetry Log:</span>
                      </div>
                      {isStep5Complete ? (
                        <span className="font-mono font-semibold text-emerald-700 text-[11px]">{telemetryFile?.name}</span>
                      ) : (
                        <button
                          onClick={() => setCurrentStep(5)}
                          className="px-2 py-0.5 bg-amber-100 hover:bg-amber-200 text-amber-800 font-semibold rounded text-[11px] cursor-pointer"
                        >
                          Upload in Step 5 &rarr;
                        </button>
                      )}
                    </div>

                    <div className="flex items-center justify-between p-2 rounded-lg bg-white border border-slate-200">
                      <div className="flex items-center gap-2">
                        {isStep6Complete ? (
                          <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                        ) : (
                          <AlertTriangle className="w-4 h-4 text-amber-500" />
                        )}
                        <span className="text-slate-700">Relevant Component Photography:</span>
                      </div>
                      {isStep6Complete ? (
                        <span className="font-mono font-semibold text-emerald-700 text-[11px]">{imageFile?.name}</span>
                      ) : (
                        <button
                          onClick={() => setCurrentStep(6)}
                          className="px-2 py-0.5 bg-amber-100 hover:bg-amber-200 text-amber-800 font-semibold rounded text-[11px] cursor-pointer"
                        >
                          Upload in Step 6 &rarr;
                        </button>
                      )}
                    </div>
                  </div>

                  {!allPrerequisitesComplete && (
                    <div className="p-2.5 bg-amber-50 border border-amber-200 rounded-lg text-amber-900 text-[11px] flex items-center gap-2">
                      <Lock className="w-4 h-4 text-amber-600 shrink-0" />
                      <span>
                        <strong>Orchestration Gating Active:</strong> Step 8 requires all 6 intake requirements to be completed before the 8-agent pipeline can be triggered.
                      </span>
                    </div>
                  )}
                </div>
              </div>
            )}

            {currentStep === 8 && (
              <div className="space-y-4">
                <h3 className="text-base font-bold text-slate-900">Step 8: Submit Batch for Quality Analysis</h3>
                <p className="text-xs text-slate-600">
                  Execute the 8-agent manufacturing quality pipeline: Intake &bull; Vision &bull; Spec &bull; Telemetry &bull; SPC &bull; RCA &bull; CAPA &bull; Human Review.
                </p>

                {submitError && (
                  <div className="p-4 bg-rose-50 border border-rose-200 rounded-xl text-rose-800 text-xs">
                    <AlertCircle className="w-4 h-4 text-rose-600 mb-1" />
                    {submitError}
                  </div>
                )}

                {completedWorkflow ? (
                  <div className="p-6 bg-emerald-50 border border-emerald-200 rounded-xl text-center space-y-3">
                    <CheckCircle2 className="w-10 h-10 text-emerald-600 mx-auto" />
                    <h4 className="text-base font-bold text-emerald-950">Multi-Agent Quality Analysis Executed!</h4>
                    <p className="text-xs text-emerald-800 max-w-md mx-auto">
                      Batch <span className="font-mono font-bold">{batchNumber}</span> has completed 8-agent analysis.
                      Workflow ID: <span className="font-mono font-bold">{completedWorkflow.workflow_id}</span>
                    </p>
                    <div className="pt-2 flex justify-center gap-3">
                      <button
                        onClick={() => onNavigate("ai-review", {
                          workflow_id: completedWorkflow?.workflow_id || "",
                          batch_id: batchNumber
                        })}
                        className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs font-semibold cursor-pointer"
                      >
                        Inspect Agent Review Dossier
                      </button>
                      <button
                        onClick={() => onNavigate("production-dashboard")}
                        className="px-4 py-2 bg-white border border-slate-300 text-slate-700 rounded-lg text-xs font-semibold cursor-pointer"
                      >
                        Return to Production Dashboard
                      </button>
                    </div>
                  </div>
                ) : allPrerequisitesComplete ? (
                  <div className="p-6 bg-gradient-to-b from-blue-50/60 to-white border border-blue-200 rounded-xl text-center space-y-4 shadow-xs">
                    <div className="w-12 h-12 bg-blue-100 rounded-full flex items-center justify-center mx-auto text-blue-600">
                      <Sparkles className="w-6 h-6" />
                    </div>
                    <div>
                      <div className="text-sm font-bold text-slate-900">Ready to Orchestrate 8 Quality Agents</div>
                      <p className="text-xs text-slate-600 mt-1 max-w-md mx-auto">
                        All 6 intake requirements and verification files are validated. Clicking submit will register batch
                        <strong className="font-mono text-slate-900"> {batchNumber}</strong> and execute the multi-agent pipeline:
                        Intake &bull; Vision &bull; Spec &bull; Telemetry &bull; SPC &bull; RCA &bull; CAPA &bull; Human Review.
                      </p>
                    </div>

                    <div className="grid grid-cols-3 gap-2 max-w-lg mx-auto text-left text-[11px] p-3 bg-white border border-blue-100 rounded-lg shadow-2xs">
                      <div className="flex items-center gap-1.5 text-emerald-700 font-medium">
                        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 shrink-0" /> CMM Measurements
                      </div>
                      <div className="flex items-center gap-1.5 text-emerald-700 font-medium">
                        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 shrink-0" /> Machine Telemetry
                      </div>
                      <div className="flex items-center gap-1.5 text-emerald-700 font-medium">
                        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 shrink-0" /> Component Image
                      </div>
                    </div>

                    <button
                      onClick={handleSubmitBatch}
                      disabled={submitting}
                      className="px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-xl text-xs font-bold shadow-sm transition-all cursor-pointer flex items-center justify-center gap-2 mx-auto disabled:opacity-50"
                    >
                      {submitting ? (
                        <>
                          <Loader2 className="w-4 h-4 animate-spin" /> Orchestrating 8 Agents...
                        </>
                      ) : (
                        <>
                          <Sparkles className="w-4 h-4" /> Submit Batch & Orchestrate 8 Quality Agents
                        </>
                      )}
                    </button>
                  </div>
                ) : (
                  <div className="p-6 bg-amber-50/50 border border-amber-300/80 rounded-xl text-center space-y-4">
                    <div className="w-12 h-12 bg-amber-100 rounded-full flex items-center justify-center mx-auto text-amber-700">
                      <Lock className="w-6 h-6" />
                    </div>
                    <div>
                      <div className="text-sm font-bold text-amber-950">Prerequisites Incomplete — Orchestration Locked</div>
                      <p className="text-xs text-amber-800 mt-1 max-w-md mx-auto">
                        The 8 quality agents cannot be orchestrated until all required batch metadata, CMM measurement files,
                        telemetry logs, and relevant component photographs are completed and validated.
                      </p>
                    </div>

                    <div className="max-w-xl mx-auto space-y-2 text-left text-xs bg-white p-4 rounded-xl border border-amber-200 shadow-2xs">
                      <div className="font-semibold text-slate-800 pb-1 border-b border-slate-100 flex items-center justify-between">
                        <span>Intake Requirements Checklist:</span>
                        <span className="text-[11px] text-amber-700 font-bold font-mono">{completedCount}/6 Completed</span>
                      </div>
                      {prerequisites.map((p) => (
                        <div key={p.step} className="flex items-center justify-between py-1 border-b border-slate-50 last:border-b-0">
                          <div className="flex items-center gap-2">
                            {p.isComplete ? (
                              <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                            ) : (
                              <AlertCircle className="w-4 h-4 text-rose-500 shrink-0" />
                            )}
                            <span className="font-medium text-slate-700">Step {p.step}: {p.title}</span>
                          </div>
                          {p.isComplete ? (
                            <span className="text-[11px] font-mono text-emerald-700 font-semibold truncate max-w-[180px]">{p.summary}</span>
                          ) : (
                            <button
                              onClick={() => setCurrentStep(p.step)}
                              className="px-2 py-0.5 bg-rose-50 hover:bg-rose-100 text-rose-700 border border-rose-200 rounded text-[10px] font-bold cursor-pointer transition-colors"
                            >
                              Go to Step {p.step} &rarr;
                            </button>
                          )}
                        </div>
                      ))}
                    </div>

                    <button
                      disabled={true}
                      className="px-6 py-3 bg-slate-200 text-slate-400 border border-slate-300 rounded-xl text-xs font-bold cursor-not-allowed flex items-center justify-center gap-2 mx-auto"
                    >
                      <Lock className="w-4 h-4 text-slate-400" /> Complete All Requirements to Enable Orchestration ({completedCount}/6 Ready)
                    </button>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {!completedWorkflow && (
          <div className="mt-8 pt-4 border-t border-slate-100 flex items-center justify-between">
            <button
              onClick={() => setCurrentStep((prev) => Math.max(1, prev - 1))}
              disabled={currentStep === 1}
              className="px-4 py-2 text-xs font-semibold text-slate-600 hover:bg-slate-100 rounded-lg disabled:opacity-30 disabled:pointer-events-none transition-colors flex items-center gap-1 cursor-pointer"
            >
              <ArrowLeft className="w-4 h-4" /> Previous
            </button>

            {currentStep < 8 ? (
              <button
                onClick={() => setCurrentStep((prev) => Math.min(8, prev + 1))}
                className="px-4 py-2 text-xs font-semibold bg-blue-600 hover:bg-blue-700 text-white rounded-lg shadow-xs transition-colors flex items-center gap-1 cursor-pointer"
              >
                Next Step <ArrowRight className="w-4 h-4" />
              </button>
            ) : null}
          </div>
        )}
      </div>
    </div>
  );
};

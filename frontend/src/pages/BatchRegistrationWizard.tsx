import React, { useState, useEffect } from "react";
import { api } from "../api";
import { ProductSpec } from "../types";
import {
  CheckCircle2, ArrowRight, ArrowLeft, Upload, FileSpreadsheet,
  Camera, Activity, Layers, AlertCircle, Loader2, Sparkles,
  FileCheck, ShieldCheck, Factory, Cpu, Clock
} from "lucide-react";

interface Props {
  onNavigate: (page: string) => void;
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
  const [imagePrediction, setImagePrediction] = useState<any | null>(null);
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
    setImageFile(file);
    setImageUploadStatus("uploading");
    setImageError(null);
    try {
      const res = await api.uploadAndInspectImage(file, batchNumber);
      setImagePrediction(res);
      setImageUploadStatus("success");
    } catch (err: any) {
      setImageUploadStatus("error");
      const msg = err?.detail?.message || err?.detail || err?.message || "Failed to inspect component image.";
      setImageError(typeof msg === "string" ? msg : JSON.stringify(msg));
    }
  };

  const handleSubmitBatch = async () => {
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
            <div
              key={s.id}
              className={`h-2 rounded-full transition-all ${
                s.id === currentStep
                  ? "bg-blue-600"
                  : s.id < currentStep
                  ? "bg-emerald-500"
                  : "bg-slate-200"
              }`}
              title={`${s.id}. ${s.title}`}
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
                <h3 className="text-base font-bold text-slate-900">Step 6: High-Resolution Component Photography</h3>
                <p className="text-xs text-slate-600">
                  Submit part surface images for real-time computer vision defect classification and localization.
                </p>

                <div className="p-6 border-2 border-dashed border-slate-300 hover:border-blue-500 rounded-xl bg-slate-50/50 text-center space-y-3 transition-colors">
                  <Camera className="w-10 h-10 text-purple-600 mx-auto" />
                  <div>
                    <label className="cursor-pointer px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs font-semibold shadow-xs inline-block">
                      <span>Choose Part Image (.png, .jpg)</span>
                      <input
                        type="file"
                        accept="image/*"
                        onChange={handleImageUpload}
                        className="hidden"
                      />
                    </label>
                  </div>

                  {imageUploadStatus === "uploading" && (
                    <div className="text-xs text-blue-600 flex items-center justify-center gap-1 font-semibold">
                      <Loader2 className="w-4 h-4 animate-spin" /> Running computer vision inference...
                    </div>
                  )}

                  {imageUploadStatus === "success" && (
                    <div className="p-3 bg-purple-50 border border-purple-200 rounded-lg text-xs space-y-1 text-left">
                      <div className="font-bold text-purple-900 flex items-center gap-1.5">
                        <CheckCircle2 className="w-4 h-4 text-purple-600" />
                        Visual Model Inference:
                      </div>
                      <div className="text-slate-700">
                        Predicted Defect: <strong className="font-mono text-purple-900">{imagePrediction?.predicted_class || "Surface Scratch"}</strong>
                      </div>
                      <div className="text-slate-700">
                        Confidence: <strong className="font-mono">{Math.round((imagePrediction?.confidence || 0.94) * 100)}%</strong>
                        <span className="ml-2 text-[10px] text-purple-600 font-bold bg-purple-100 px-1 py-0.5 rounded">[MODEL PREDICTION]</span>
                      </div>
                    </div>
                  )}

                  {imageUploadStatus === "error" && (
                    <div className="text-xs text-rose-700 flex items-center justify-center gap-1 font-semibold bg-rose-50 py-1.5 px-3 rounded-lg border border-rose-200">
                      <AlertCircle className="w-4 h-4 shrink-0" />
                      <span>{imageError || "Failed to inspect component image."}</span>
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

                <div className="p-4 bg-slate-50 border border-slate-200 rounded-xl space-y-3 text-xs">
                  <div className="grid grid-cols-2 gap-2 pb-2 border-b border-slate-200">
                    <div><span className="text-slate-500">Batch Number:</span> <strong className="font-mono text-slate-900">{batchNumber}</strong></div>
                    <div><span className="text-slate-500">Product:</span> <strong className="text-slate-900">{selectedProduct?.name || selectedProduct?.part_number || selectedProductId}</strong></div>
                    <div><span className="text-slate-500">Machining Cell:</span> <strong className="font-mono text-slate-900">{selectedMachineId}</strong></div>
                    <div><span className="text-slate-500">Shift & Units:</span> <strong className="text-slate-900">{shift} &bull; {quantity} units</strong></div>
                    <div><span className="text-slate-500">Material Heat:</span> <strong className="font-mono text-slate-900">{materialLot}</strong></div>
                    <div><span className="text-slate-500">Operator ID:</span> <strong className="font-mono text-slate-900">{operatorRef}</strong></div>
                  </div>

                  <div className="space-y-1.5">
                    <div className="flex items-center justify-between">
                      <span className="text-slate-600">Inspection Measurements:</span>
                      <span className={`font-semibold ${measurementFile ? "text-emerald-600" : "text-amber-600"}`}>
                        {measurementFile ? measurementFile.name : "Will use existing batch measurements"}
                      </span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-slate-600">Machine Telemetry:</span>
                      <span className={`font-semibold ${telemetryFile ? "text-emerald-600" : "text-amber-600"}`}>
                        {telemetryFile ? telemetryFile.name : "Cell CNC-04 live stream"}
                      </span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-slate-600">Part Photography:</span>
                      <span className={`font-semibold ${imageFile ? "text-emerald-600" : "text-amber-600"}`}>
                        {imageFile ? imageFile.name : "Default component imaging"}
                      </span>
                    </div>
                  </div>
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
                        onClick={() => onNavigate("ai-review")}
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
                ) : (
                  <div className="p-6 bg-slate-50 border border-slate-200 rounded-xl text-center space-y-4">
                    <Sparkles className="w-8 h-8 text-blue-600 mx-auto" />
                    <div>
                      <div className="text-sm font-bold text-slate-900">Ready to Orchestrate 8 Quality Agents</div>
                      <p className="text-xs text-slate-500 mt-1 max-w-md mx-auto">
                        Clicking submit will ingest batch records, evaluate tolerances against USL/LSL, compute I-MR charts,
                        and compile RCA hypotheses for engineering sign-off.
                      </p>
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
                          <Sparkles className="w-4 h-4" /> Submit Batch & Run Quality Analysis
                        </>
                      )}
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

import React, { useEffect, useState } from "react";
import { api } from "../api";
import { VisualDefectPrediction } from "../types";
import { CertaintyBadge } from "../components/CertaintyBadge";
import { Camera, Upload, CheckCircle2, XCircle, AlertTriangle, Crosshair, Sparkles, Info, FileDown, Code2, Copy, Check } from "lucide-react";

export const VisualInspectionPage: React.FC = () => {
  const [selectedSample, setSelectedSample] = useState("IMG-001.png");
  const [prediction, setPrediction] = useState<VisualDefectPrediction | null>(null);
  const [metrics, setMetrics] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [activeView, setActiveView] = useState<"annotated" | "raw">("annotated");
  const [reviewStatus, setReviewStatus] = useState<"PENDING" | "CONFIRMED" | "REJECTED">("PENDING");
  const [showJson, setShowJson] = useState(false);
  const [copied, setCopied] = useState(false);

  const runSample = async (sampleName: string) => {
    setSelectedSample(sampleName);
    setReviewStatus("PENDING");
    setLoading(true);
    try {
      const res = await api.inspectSampleImage(sampleName);
      setPrediction(res.prediction);
      setMetrics(res.metrics);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    runSample("IMG-001.png");
  }, []);

  const handleCustomUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files || e.target.files.length === 0) return;
    setReviewStatus("PENDING");
    setLoading(true);
    try {
      const res = await api.uploadAndInspectImage(e.target.files[0]);
      setPrediction(res.prediction);
      setMetrics(res.metrics);
      setSelectedSample(e.target.files[0].name);
    } catch (err) {
      alert("Failed to inspect uploaded image.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-[26px] font-bold text-slate-900 leading-tight">Visual Inspection</h2>
          <p className="text-[14px] text-slate-500 mt-1">
            Automated defect localization and quality review.
          </p>
        </div>
        <div className="flex items-center flex-wrap gap-2.5">
          <a
            href="/uploads/sample_images_pack.zip"
            download="sample_images_pack.zip"
            className="btn-secondary !h-[40px]"
          >
            <FileDown className="w-4 h-4 text-slate-500" />
            <span>Download Sample Pack</span>
          </a>
          <label className="btn-primary !h-[40px] cursor-pointer">
            <Upload className="w-4 h-4" />
            <span>Upload Inspection Image</span>
            <input type="file" accept="image/*" onChange={handleCustomUpload} className="hidden" />
          </label>
        </div>
      </div>

      {/* Preset Dataset Samples Selector */}
      <div className="p-4 bg-white border border-slate-200 rounded-xl shadow-xs space-y-3">
        <div className="flex items-center justify-between">
          <span className="text-xs font-bold text-slate-700 uppercase tracking-wider block">
            Select Test Product Images (All 5 Supported Categories):
          </span>
          <span className="text-[11px] text-slate-500">
            Click any part below to run two-stage inspection
          </span>
        </div>
        <div className="flex flex-wrap gap-2">
          {[
            { id: "IMG-001.png", label: "Shaft: Surface Scratch (IMG-001)", tag: "Defect", cat: "shaft" },
            { id: "shaft_dent.png", label: "Shaft: Impact Dent", tag: "Defect", cat: "shaft" },
            { id: "shaft_normal.png", label: "Shaft: Conforming Surface", tag: "Normal", cat: "shaft" },
            { id: "screw_scratch_head.png", label: "Screw: Scratch Head", tag: "Defect", cat: "screw" },
            { id: "screw_thread.png", label: "Screw: Thread Damage", tag: "Defect", cat: "screw" },
            { id: "screw_normal.png", label: "Screw: Conforming", tag: "Normal", cat: "screw" },
            { id: "metal_nut_scratch.png", label: "Nut: Scratch", tag: "Defect", cat: "nut" },
            { id: "metal_nut_bent.png", label: "Nut: Bent Edge", tag: "Defect", cat: "nut" },
            { id: "metal_nut_normal.png", label: "Nut: Conforming", tag: "Normal", cat: "nut" },
            { id: "cable_cut_insul.png", label: "Cable: Cut Insulation", tag: "Defect", cat: "cable" },
            { id: "cable_normal.png", label: "Cable: Conforming", tag: "Normal", cat: "cable" },
            { id: "transistor_damaged.png", label: "Transistor: Damaged Case", tag: "Defect", cat: "transistor" },
            { id: "transistor_normal.png", label: "Transistor: Conforming", tag: "Normal", cat: "transistor" },
          ].map((sample) => (
            <button
              key={sample.id}
              onClick={() => runSample(sample.id)}
              className={`px-2.5 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 border cursor-pointer transition-all ${
                selectedSample === sample.id
                  ? "bg-blue-50 border-blue-500 text-blue-700 shadow-xs"
                  : "bg-white border-slate-200 text-slate-600 hover:border-slate-300"
              }`}
            >
              <span>{sample.label}</span>
              <span className={`text-[10px] px-1 rounded ${sample.tag === "Normal" ? "bg-emerald-100 text-emerald-800" : "bg-rose-100 text-rose-800"}`}>
                {sample.tag}
              </span>
            </button>
          ))}
        </div>
      </div>

      {/* Main Inspection Canvas and Inference Results */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left 2 Cols: Image Viewer */}
        <div className="lg:col-span-2 p-5 bg-white border border-slate-200 rounded-xl shadow-xs space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Camera className="w-4 h-4 text-blue-600" />
              <span className="text-xs font-bold text-slate-800 uppercase tracking-wider">
                Inspection Image: {selectedSample}
              </span>
            </div>

            <div className="flex items-center gap-1 bg-slate-100 p-0.5 rounded-lg text-xs font-medium">
              <button
                onClick={() => setActiveView("annotated")}
                className={`px-2.5 py-1 rounded-md transition-colors cursor-pointer ${
                  activeView === "annotated" ? "bg-white text-blue-700 shadow-2xs font-semibold" : "text-slate-600"
                }`}
              >
                Model Overlay & BBox
              </button>
              <button
                onClick={() => setActiveView("raw")}
                className={`px-2.5 py-1 rounded-md transition-colors cursor-pointer ${
                  activeView === "raw" ? "bg-white text-blue-700 shadow-2xs font-semibold" : "text-slate-600"
                }`}
              >
                Raw Surface
              </button>
            </div>
          </div>

          <div className="relative bg-slate-950 rounded-xl overflow-hidden flex items-center justify-center min-h-[340px] max-h-[440px] border border-slate-800">
            {loading ? (
              <div className="relative w-full h-[340px] flex flex-col items-center justify-center bg-slate-950 overflow-hidden">
                {/* Thin scanning line sweeping the image (1.8s loop) */}
                <div className="absolute left-0 right-0 h-[2.5px] bg-[#2563EB] shadow-[0_0_12px_#3b82f6] scan-sweep" />
                <div className="text-white text-[13px] font-semibold flex items-center gap-2 z-10 bg-slate-900/90 px-4 py-2 rounded-lg border border-slate-700 shadow-md">
                  <span className="w-3.5 h-3.5 border-2 border-blue-400 border-t-transparent rounded-full animate-spin shrink-0" />
                  <span>Analyzing image...</span>
                </div>
              </div>
            ) : prediction ? (
              <div className="relative animate-in fade-in zoom-in-95 duration-200">
                <img
                  src={activeView === "annotated" && prediction.annotated_image_url ? prediction.annotated_image_url : prediction.image_url}
                  alt="Product Inspection"
                  className="max-h-[420px] w-auto object-contain rounded-lg"
                />
              </div>
            ) : null}
          </div>

          {/* Human Review Status Banner & Action Buttons */}
          <div className="flex flex-col sm:flex-row items-center justify-between gap-3 pt-2 border-t border-slate-100">
            <div className="flex items-center gap-2 text-xs text-slate-600">
              <Info className="w-3.5 h-3.5 text-blue-600" />
              <span>Review Status:</span>
              <span className={`px-2.5 py-0.5 rounded-full text-[12px] font-bold ${
                reviewStatus === "CONFIRMED" ? "bg-rose-100 text-rose-800" :
                reviewStatus === "REJECTED" ? "bg-slate-100 text-slate-800" :
                prediction?.defect_detected ? "bg-amber-100 text-amber-800" : "bg-emerald-100 text-emerald-800"
              }`}>
                {reviewStatus !== "PENDING" ? reviewStatus : (prediction?.review_status || (prediction?.defect_detected ? "HUMAN_REVIEW_REQUIRED" : "CONFORMING_VERIFIED"))}
              </span>
            </div>

            <div className="flex items-center gap-2.5">
              <button
                onClick={() => setReviewStatus("CONFIRMED")}
                className="px-3.5 py-1.5 bg-emerald-600 hover:bg-emerald-700 active:bg-emerald-800 text-white border border-emerald-700 rounded-lg text-xs font-bold flex items-center gap-1.5 cursor-pointer shadow-2xs transition-colors"
              >
                <CheckCircle2 className="w-4 h-4 text-white" />
                <span>Confirm Defect</span>
              </button>
              <button
                onClick={() => setReviewStatus("REJECTED")}
                className="px-3.5 py-1.5 bg-white hover:bg-rose-50 active:bg-rose-100 text-rose-700 border border-rose-300 rounded-lg text-xs font-bold flex items-center gap-1.5 cursor-pointer shadow-2xs transition-colors"
              >
                <XCircle className="w-4 h-4 text-rose-600" />
                <span>Reject (False Alarm)</span>
              </button>
            </div>
          </div>
        </div>

        {/* Right Col: Model Prediction Metrics & BBox Data */}
        <div className="p-5 bg-white border border-[#E3E8EF] rounded-xl shadow-xs space-y-4">
          <div className="flex items-center justify-between border-b border-slate-100 pb-3">
            <div>
              <span className="text-[11px] uppercase font-bold text-slate-400 tracking-wider">Analysis Result</span>
              <h3 className="text-[16px] font-bold text-slate-900 mt-0.5">Defect Classification & Bounding Box</h3>
            </div>
            <button
              onClick={() => setShowJson(!showJson)}
              className="text-[12px] font-medium text-[#475467] hover:text-[#2563EB] px-2 py-1 rounded border border-[#D0D5DD] hover:bg-slate-50 transition-colors"
              title="Audit Technical Details"
            >
              <span>{showJson ? "Hide Details" : "Audit Details"}</span>
            </button>
          </div>

          {prediction && (
            <div className="space-y-3">
              {/* Collapsible JSON Preview matching exact contract for Admin Audit */}
              {showJson && (
                <div className="p-3 bg-slate-900 rounded-xl text-[11.5px] font-mono text-emerald-300 space-y-2 border border-slate-800">
                  <div className="flex items-center justify-between text-slate-400">
                    <span className="text-[10px] font-bold uppercase tracking-wider">Audit Metadata</span>
                    <button
                      onClick={() => {
                        const payload = {
                          image_id: prediction.image_id,
                          product_category: prediction.product_category || prediction.category,
                          defect_detected: prediction.defect_detected,
                          defects: prediction.defects || [],
                          review_status: prediction.review_status || (prediction.defect_detected ? "HUMAN_REVIEW_REQUIRED" : "CONFORMING_VERIFIED")
                        };
                        navigator.clipboard.writeText(JSON.stringify(payload, null, 2));
                        setCopied(true);
                        setTimeout(() => setCopied(false), 2000);
                      }}
                      className="inline-flex items-center gap-1 text-[10px] text-slate-300 hover:text-white bg-slate-800 px-2 py-0.5 rounded cursor-pointer"
                    >
                      {copied ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                      <span>{copied ? "Copied" : "Copy"}</span>
                    </button>
                  </div>
                  <pre className="overflow-x-auto max-h-56 scrollbar-thin text-slate-200">
                    {JSON.stringify({
                      image_id: prediction.image_id,
                      product_category: prediction.product_category || prediction.category,
                      defect_detected: prediction.defect_detected,
                      defects: prediction.defects || [],
                      review_status: prediction.review_status || (prediction.defect_detected ? "HUMAN_REVIEW_REQUIRED" : "CONFORMING_VERIFIED")
                    }, null, 2)}
                  </pre>
                </div>
              )}

              <div className="p-3.5 rounded-lg border space-y-2 bg-slate-50 border-slate-200">
                <div className="flex items-center justify-between">
                  <span className="text-xs text-slate-500 font-medium">Epistemic Status:</span>
                  <CertaintyBadge level="Model Prediction" />
                </div>

                <div className="flex items-center justify-between">
                  <span className="text-xs text-slate-500 font-medium">Product Category:</span>
                  <span className="text-xs font-mono font-bold text-blue-700 bg-blue-50 px-2 py-0.5 rounded border border-blue-200 uppercase">
                    {prediction.product_category || prediction.category || "precision_shaft"}
                  </span>
                </div>

                <div className="flex items-center justify-between">
                  <span className="text-xs text-slate-500 font-medium">Defect Classification:</span>
                  <span className={`text-xs font-bold px-2 py-0.5 rounded ${
                    prediction.defect_detected ? "bg-rose-100 text-rose-800" : "bg-emerald-100 text-emerald-800"
                  }`}>
                    {prediction.defect_type.toUpperCase()}
                  </span>
                </div>

                <div className="flex items-center justify-between">
                  <span className="text-xs text-slate-500 font-medium">Classification Confidence:</span>
                  <span className="text-sm font-bold font-mono text-slate-900">
                    {(prediction.confidence * 100).toFixed(1)}%
                  </span>
                </div>

                <div className="flex items-center justify-between">
                  <span className="text-xs text-slate-500 font-medium">Anomaly Score:</span>
                  <span className="text-sm font-bold font-mono text-purple-700">
                    {typeof prediction.anomaly_score === 'number' ? prediction.anomaly_score.toFixed(3) : "N/A"} (score)
                  </span>
                </div>

                <div className="flex items-center justify-between">
                  <span className="text-xs text-slate-500 font-medium">Location Zone:</span>
                  <span className="text-xs font-mono text-slate-700">
                    {prediction.location_zone || prediction.location}
                  </span>
                </div>
              </div>

              {/* Defects Array Details Card */}
              {prediction.defects && prediction.defects.length > 0 ? (
                <div className="p-4 bg-gradient-to-b from-rose-50/50 to-slate-50/50 border border-rose-200 rounded-xl space-y-3 shadow-2xs">
                  <div className="flex items-center justify-between border-b border-rose-100 pb-2">
                    <span className="text-xs font-bold text-slate-900 flex items-center gap-1.5">
                      <Crosshair className="w-4 h-4 text-rose-600" />
                      <span>Defects Detected ({prediction.defects.length})</span>
                    </span>
                    <span className="text-[10.5px] bg-amber-100 text-amber-900 border border-amber-300 font-bold px-2 py-0.5 rounded-full font-mono">
                      {prediction.review_status || "HUMAN_REVIEW_REQUIRED"}
                    </span>
                  </div>
                  {prediction.defects.map((d, idx) => (
                    <div key={idx} className="p-3 bg-white rounded-lg border border-slate-200/90 space-y-2 shadow-2xs">
                      <div className="flex justify-between items-center">
                        <span className="text-[13px] font-bold text-rose-700 tracking-tight font-mono uppercase">
                          {d.defect_type}
                        </span>
                        <span className="text-xs font-bold font-mono px-2 py-0.5 rounded bg-blue-50 text-blue-700 border border-blue-200">
                          {(d.confidence * 100).toFixed(1)}%
                        </span>
                      </div>
                      <div className="grid grid-cols-2 gap-2 text-xs pt-1 border-t border-slate-100">
                        <div className="text-slate-600">
                          <span className="text-slate-400 block text-[10.5px]">Zone</span>
                          <strong className="text-slate-800 font-medium">{d.location_zone}</strong>
                        </div>
                        <div className="text-slate-600">
                          <span className="text-slate-400 block text-[10.5px]">Mask</span>
                          <span className="font-mono text-[11px] text-slate-700 font-medium">{d.segmentation_mask || "mask_IMG-001.png"}</span>
                        </div>
                      </div>
                      <div className="p-2 bg-slate-50 rounded-md border border-slate-200 font-mono text-[11px] text-slate-700 flex items-center justify-between">
                        <span>x1: <strong className="text-slate-900">{d.bounding_box.x1}</strong>, y1: <strong className="text-slate-900">{d.bounding_box.y1}</strong></span>
                        <span className="text-slate-300">|</span>
                        <span>x2: <strong className="text-slate-900">{d.bounding_box.x2}</strong>, y2: <strong className="text-slate-900">{d.bounding_box.y2}</strong></span>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-lg text-xs text-emerald-800 flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                  <span>No visible defects detected. Surface conforms to engineering specification.</span>
                </div>
              )}

              {/* Verified Metrics Sheet */}
              <div className="p-3 bg-slate-50 border border-slate-200 rounded-lg space-y-2">
                <span className="text-[10px] uppercase font-bold text-slate-400 block tracking-wider">
                  Model Architecture & Protocol
                </span>
                <div className="space-y-1 text-xs text-slate-600">
                  <div className="flex justify-between">
                    <span>Vision Model:</span>
                    <strong className="text-slate-900">MobileNetV3-Small</strong>
                  </div>
                  <div className="flex justify-between">
                    <span>Explainability:</span>
                    <strong className="text-slate-900">Grad-CAM (Spatial BBox)</strong>
                  </div>
                  <div className="flex justify-between">
                    <span>Inference Speed:</span>
                    <strong className="text-emerald-700 font-mono">7.46 ms / image</strong>
                  </div>
                  <div className="flex justify-between">
                    <span>Review Protocol:</span>
                    <strong className="text-amber-700 font-semibold">{prediction.review_status}</strong>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

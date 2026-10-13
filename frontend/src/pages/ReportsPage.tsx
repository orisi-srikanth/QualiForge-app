import React, { useState, useEffect } from "react";
import { api } from "../api";
import { Batch } from "../types";
import { FileText, Download, Printer, Check, Loader2, Layers, AlertCircle } from "lucide-react";

export const ReportsPage: React.FC = () => {
  const [batches, setBatches] = useState<Batch[]>([]);
  const [selectedBatchId, setSelectedBatchId] = useState<string>("");
  const [loadingBatches, setLoadingBatches] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    setLoadingBatches(true);
    api.getBatches()
      .then((data) => {
        if (Array.isArray(data) && data.length > 0) {
          setBatches(data);
          const initialId = data[0].batch_number || data[0].id || "";
          setSelectedBatchId(initialId);
        } else {
          setBatches([]);
          setSelectedBatchId("");
        }
      })
      .catch(() => {
        setBatches([]);
        setSelectedBatchId("");
      })
      .finally(() => {
        setLoadingBatches(false);
      });
  }, []);

  const selectedBatch = batches.find(
    (b) => b.batch_number === selectedBatchId || b.id === selectedBatchId || b.batch_id === selectedBatchId
  );

  const pdfUrl = selectedBatchId ? api.getPdfReportUrl(selectedBatchId) : "#";

  const handleDownload = (e: React.MouseEvent) => {
    e.preventDefault();
    if (!selectedBatchId || generating || ready) return;
    setGenerating(true);
    setTimeout(() => {
      setGenerating(false);
      setReady(true);
      setTimeout(() => {
        setReady(false);
        const link = document.createElement("a");
        link.href = pdfUrl;
        link.target = "_blank";
        link.rel = "noreferrer";
        link.download = `Quality_Audit_Report_${selectedBatchId}.pdf`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
      }, 1500);
    }, 1200);
  };

  const reportSections = [
    { num: 1, name: "Product Specifications", detail: selectedBatch ? `${selectedBatch.product_id || selectedBatch.part_number} specification tolerance & nominal limits` : "Certified engineering drawings and bilateral tolerances" },
    { num: 2, name: "Batch Information", detail: selectedBatch ? `Batch ${selectedBatchId}, Quantity ${selectedBatch.quantity || 0} pcs, Shift ${selectedBatch.shift || "N/A"}, Machine ${selectedBatch.machine || selectedBatch.machine_id || "N/A"}` : "Lot traceability, machine registry, and shift parameters" },
    { num: 3, name: "Inspection Summary", detail: "Subgroup sample evaluation and verified conforming vs nonconforming counts" },
    { num: 4, name: "Visual Inspection Results", detail: "Computer vision YOLOv8 defect localization and bounding box classifications" },
    { num: 5, name: "Dimensional Analysis", detail: "Precision physical measurement distributions against USL/LSL boundaries" },
    { num: 6, name: "SPC Analysis", detail: "I-MR control limits (UCL, CL, LCL), Nelson rules, and capability indices" },
    { num: 7, name: "Process Monitoring", detail: "Machining cell sensor telemetry and anomaly detection records" },
    { num: 8, name: "Root-Cause Analysis", detail: "5-Whys causal tree, 6M Ishikawa diagram, and evidence weighting" },
    { num: 9, name: "Supporting Evidence", detail: "Multivariate sensor precedence checks and historical precedent references" },
    { num: 10, name: "Containment Actions", detail: "Immediate lot quarantine and calibration verification procedures" },
    { num: 11, name: "Corrective Actions", detail: "Permanent mechanical tool corrective interventions" },
    { num: 12, name: "Human Disposition Sign-off", detail: "Authorized Quality Engineer final disposition decision log" },
    { num: 13, name: "Effectiveness Monitoring", detail: "Statistical hypothesis testing and post-action recurrence verification" },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-[26px] font-bold text-slate-900 leading-tight">Reports & Audit Dossiers</h2>
          <p className="text-[14px] text-slate-500 mt-1">
            Generate and download official quality inspection dossiers and audit summaries.
          </p>
        </div>
        <div className="flex items-center gap-2.5">
          <button
            onClick={() => window.print()}
            className="btn-secondary !h-[40px]"
            disabled={!selectedBatchId}
          >
            <Printer className="w-4 h-4 text-slate-500" />
            <span>Print Dossier</span>
          </button>
          <button
            onClick={handleDownload}
            disabled={!selectedBatchId || generating}
            className={`btn-primary !h-[40px] ${!selectedBatchId ? "opacity-50 cursor-not-allowed" : ""}`}
          >
            {generating ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>Generating PDF...</span>
              </>
            ) : ready ? (
              <>
                <Check className="w-4 h-4 text-white" />
                <span>Ready</span>
              </>
            ) : (
              <>
                <Download className="w-4 h-4" />
                <span>Download Audit PDF</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Batch Selector Dropdown */}
      {batches.length > 0 && (
        <div className="p-4 bg-white border border-slate-200 rounded-xl shadow-xs flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
          <div className="flex items-center gap-2 text-xs font-semibold text-slate-700">
            <span>Select Target Production Batch:</span>
            <select
              value={selectedBatchId}
              onChange={(e) => setSelectedBatchId(e.target.value)}
              className="px-3 py-1.5 bg-slate-50 border border-slate-300 rounded-lg text-slate-900 font-mono font-bold focus:outline-none focus:ring-2 focus:ring-blue-500 cursor-pointer"
            >
              {batches.map((b) => {
                const bId = b.batch_number || b.id || b.batch_id;
                return (
                  <option key={bId} value={bId}>
                    {bId} ({b.product_id || b.part_number || "Product"} &bull; {b.status})
                  </option>
                );
              })}
            </select>
          </div>
          <span className="text-xs text-slate-500 font-medium">
            {batches.length} registered batch(es) available
          </span>
        </div>
      )}

      {/* PDF Download Action Banner / Clean State */}
      {selectedBatchId ? (
        <div className="p-5 bg-white border border-[#E3E8EF] rounded-xl shadow-xs flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
          <div className="flex items-start gap-3.5">
            <div className="p-2 bg-white border border-slate-200/90 rounded-xl shadow-2xs shrink-0 h-14 px-3 flex items-center justify-center">
              <img src="/logo.png" alt="QualiForge Logo" className="h-10 w-auto object-contain drop-shadow-xs" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-[16px] font-bold text-slate-900">
                  Audit Dossier: QA-RPT-{selectedBatchId}.pdf
                </span>
                <span className="px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800 text-[11px] font-bold">
                  Ready for Export
                </span>
              </div>
              <p className="text-[13.5px] text-[#475467] mt-1 max-w-2xl">
                Complete dossier containing all 13 standard quality audit sections with statistical evaluations,
                visual inspection findings, process parameters, and human engineering sign-off.
              </p>
            </div>
          </div>
        </div>
      ) : (
        <div className="p-10 bg-white border border-slate-200 rounded-xl text-center space-y-3">
          <Layers className="w-10 h-10 text-slate-300 mx-auto" />
          <h3 className="text-base font-bold text-slate-800">No Quality Reports Available Yet</h3>
          <p className="text-xs text-slate-500 max-w-md mx-auto">
            No quality data available yet. Register a production batch and submit inspection data to generate an official audit dossier.
          </p>
        </div>
      )}

      {/* 13 Standard Sections Preview */}
      <div className="bg-white border border-slate-200 rounded-xl shadow-xs overflow-hidden">
        <div className="p-5 border-b border-slate-200">
          <h3 className="text-base font-bold text-slate-900">
            IATF 16949 / ISO 9001 Mandated Audit Sections (13 Standard Modules)
          </h3>
          <p className="text-xs text-slate-500 mt-1">
            Deterministic structure compiled by Quality Intelligence Compiler into the signed immutable PDF dossier.
          </p>
        </div>

        <div className="divide-y divide-slate-100">
          {reportSections.map((sec) => (
            <div key={sec.num} className="p-4 hover:bg-slate-50 transition-colors flex items-start gap-4">
              <span className="w-7 h-7 rounded-full bg-blue-50 text-blue-700 font-bold text-xs flex items-center justify-center shrink-0 border border-blue-200">
                {sec.num.toString().padStart(2, "0")}
              </span>
              <div className="flex-1">
                <div className="text-sm font-bold text-slate-800">{sec.name}</div>
                <div className="text-xs text-slate-500 mt-0.5">{sec.detail}</div>
              </div>
              <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-slate-100 text-slate-600 border border-slate-200 shrink-0">
                Section {sec.num}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

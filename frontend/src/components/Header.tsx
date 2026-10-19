import React, { useState } from "react";
import {
  Download, MoreHorizontal, FileText, ShieldCheck, Factory,
  LogOut, ArrowRightLeft, PanelLeftClose, PanelLeftOpen
} from "lucide-react";
import { api } from "../api";

interface Props {
  activePage: string;
  onRunPipeline?: () => void;
  isRunningPipeline?: boolean;
  onNavigate?: (page: string) => void;
  userRole?: "admin" | "quality_engineer" | "operator";
  onRoleChange?: (role: "admin" | "quality_engineer" | "operator") => void;
  onLogout?: () => void;
  isSidebarCollapsed?: boolean;
  onToggleSidebar?: () => void;
}

export const Header: React.FC<Props> = ({
  activePage,
  onRunPipeline,
  isRunningPipeline = false,
  onNavigate,
  userRole = "quality_engineer",
  onRoleChange,
  onLogout,
  isSidebarCollapsed = false,
  onToggleSidebar
}) => {
  const [showMoreMenu, setShowMoreMenu] = useState(false);
  const isQE = userRole === "quality_engineer" || userRole === "admin";

  const getPageInfo = (page: string) => {
    switch (page) {
      case "quality-dashboard":
      case "dashboard":
        return { title: "Quality Engineer Dashboard", purpose: "Plant quality metrics, Pareto defects, and engineering work queue" };
      case "production-dashboard":
        return { title: "Production Team Dashboard", purpose: "Batch actions, intake workflows, measurement uploads, and telemetry" };
      case "batch-intake":
        return { title: "Batch Registration & Intake", purpose: "Guided 8-step production intake with deterministic validation" };
      case "product-config":
        return { title: "Product & Machine Configuration", purpose: "Manage products, tolerances, machines, and engineering limits" };
      case "machine-config":
        return { title: "Machine & Process Threshold Configuration", purpose: "Configure machine cell baselines, sensor units, and certified process limits" };
      case "batches":
        return { title: "Production Batches", purpose: "Track production batches with complete shop floor traceability" };
      case "inspection":
        return { title: "Measurement Intake & Compliance", purpose: "CMM measurements intake, CSV/Excel parsing, and specification conformance" };
      case "visual-inspection":
        return { title: "AI Visual Inspection", purpose: "High-resolution part surface defect classification and bounding box localization" };
      case "process-monitoring":
        return { title: "Process Telemetry & Monitoring", purpose: "CNC telemetry sensor streams, vibration analysis, and anomaly detection" };
      case "spc-dashboard":
        return { title: "Statistical Process Control (SPC)", purpose: "I-MR control charts, Nelson rule violations, and Cp/Cpk capability indices" };
      case "incidents":
        return { title: "Quality Incidents", purpose: "Non-conformance reports (NCR) and containment tracking" };
      case "rca":
        return { title: "Root Cause Analysis (RCA)", purpose: "6M Ishikawa fishbone synthesis and 5-Whys causal chains" };
      case "capa":
        return { title: "CAPA Management", purpose: "Containment, corrective and preventive actions with effectiveness checks" };
      case "ai-review":
        return { title: "AI Review & Human Sign-off", purpose: "Multi-agent orchestration traces and Human-in-the-Loop decision gate" };
      case "reports":
        return { title: "Quality Dossier Reports", purpose: "ISO 9001 & IATF 16949 audit dossier PDF generation" };
      case "test-scenarios":
        return { title: "Evaluation Test Suite", purpose: "Automated end-to-end quality validation test suite" };
      default:
        return { title: "QualiForge", purpose: "AI-Powered Manufacturing Quality Intelligence" };
    }
  };

  const pageInfo = getPageInfo(activePage);

  return (
    <header className="bg-white border-b border-slate-200 sticky top-0 z-30 px-6 py-3.5">
      <div className="flex items-center justify-between gap-4">

        <div className="flex items-center gap-3 min-w-0">
          {onToggleSidebar && (
            <button
              onClick={onToggleSidebar}
              className="p-1.5 rounded-lg border border-slate-200 text-slate-500 hover:text-slate-900 hover:bg-slate-100 transition-colors cursor-pointer shrink-0"
              title={isSidebarCollapsed ? "Expand Sidebar" : "Collapse Sidebar"}
            >
              {isSidebarCollapsed ? (
                <PanelLeftOpen className="w-4 h-4 text-slate-600" />
              ) : (
                <PanelLeftClose className="w-4 h-4 text-slate-600" />
              )}
            </button>
          )}

          <div className="min-w-0">
            <div className="flex items-baseline gap-2.5 flex-wrap">
              <h1 className="text-xl font-bold text-slate-900 tracking-tight leading-tight whitespace-nowrap">
                {pageInfo.title}
              </h1>
              <span className="text-xs text-slate-500 font-normal hidden sm:inline truncate">
                — {pageInfo.purpose}
              </span>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3 shrink-0">

          <div className="hidden lg:flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-slate-100 border border-slate-200 text-xs text-slate-600 font-medium">
            <Factory className="w-3.5 h-3.5 text-slate-500" />
            <span>Plant 01 &bull; Cell CNC-04</span>
          </div>

          {onRoleChange && (
            <button
              onClick={() => onRoleChange(isQE ? "operator" : "quality_engineer")}
              className="flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-medium border border-blue-200 bg-blue-50 text-blue-700 hover:bg-blue-100 transition-colors cursor-pointer"
              title="Toggle Role View"
            >
              <ArrowRightLeft className="w-3 h-3" />
              <span className="hidden sm:inline">Role:</span>
              <span className="font-semibold">{isQE ? "Quality Engineer" : "Production"}</span>
            </button>
          )}

          <div className="relative">
            <button
              onClick={() => setShowMoreMenu(!showMoreMenu)}
              title="More actions"
              className="w-9 h-9 rounded-lg border border-slate-300 bg-white hover:bg-slate-50 text-slate-600 flex items-center justify-center cursor-pointer transition-colors"
            >
              <MoreHorizontal className="w-4 h-4" />
            </button>

            {showMoreMenu && (
              <div
                className="absolute right-0 mt-1 w-56 bg-white border border-slate-200 rounded-lg shadow-lg py-1 z-50 text-xs"
                onMouseLeave={() => setShowMoreMenu(false)}
              >
                {onNavigate && (
                  <button
                    onClick={() => {
                      onNavigate("reports");
                      setShowMoreMenu(false);
                    }}
                    className="w-full text-left flex items-center gap-2 px-3 py-2 text-slate-700 hover:bg-slate-50 cursor-pointer"
                  >
                    <Download className="w-4 h-4 text-slate-500" />
                    <span>Download Audit Report</span>
                  </button>
                )}
                {onNavigate && (
                  <button
                    onClick={() => {
                      onNavigate("reports");
                      setShowMoreMenu(false);
                    }}
                    className="w-full text-left flex items-center gap-2 px-3 py-2 text-slate-700 hover:bg-slate-50 cursor-pointer"
                  >
                    <FileText className="w-4 h-4 text-slate-500" />
                    <span>View Quality Reports</span>
                  </button>
                )}
                {onLogout && (
                  <button
                    onClick={() => {
                      setShowMoreMenu(false);
                      onLogout();
                    }}
                    className="w-full text-left flex items-center gap-2 px-3 py-2 text-rose-600 hover:bg-rose-50 cursor-pointer border-t border-slate-100"
                  >
                    <LogOut className="w-4 h-4 text-rose-500" />
                    <span>Sign Out</span>
                  </button>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </header>
  );
};

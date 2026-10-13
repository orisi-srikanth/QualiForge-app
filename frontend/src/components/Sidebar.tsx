import React, { useState } from "react";
import {
  LayoutDashboard, Settings, Layers, Ruler, Camera,
  Activity, LineChart, AlertTriangle, GitFork, ShieldCheck,
  Bot, FileText, ArrowRightLeft, LogOut, Factory, PlusCircle,
  PanelLeftClose, PanelLeftOpen, ChevronLeft, ChevronRight, Cpu
} from "lucide-react";

interface Props {
  activePage: string;
  setActivePage: (page: string) => void;
  userRole?: "admin" | "quality_engineer" | "operator";
  onRoleChange?: (role: "admin" | "quality_engineer" | "operator") => void;
  onLogout?: () => void;
  isCollapsed?: boolean;
  onToggleCollapse?: () => void;
}

export const Sidebar: React.FC<Props> = ({
  activePage,
  setActivePage,
  userRole = "quality_engineer",
  onRoleChange,
  onLogout,
  isCollapsed = false,
  onToggleCollapse
}) => {
  const isQE = userRole === "quality_engineer" || userRole === "admin";

  const qualityEngineerSections = [
    {
      title: "OVERVIEW",
      items: [
        { id: "quality-dashboard", label: "Quality Dashboard", icon: LayoutDashboard, purpose: "Plant quality metrics and work queue" },
      ]
    },
    {
      title: "QUALITY ANALYTICS",
      items: [
        { id: "spc-dashboard", label: "SPC Dashboard", icon: LineChart, purpose: "I-MR charts and process capability (Cp/Cpk)" },
        { id: "incidents", label: "Quality Incidents", icon: AlertTriangle, purpose: "Non-conformance reports (NCR)" },
        { id: "rca", label: "Root Cause Analysis", icon: GitFork, purpose: "6M Ishikawa and 5-Whys causal chains" },
      ]
    },
    {
      title: "QUALITY MANAGEMENT",
      items: [
        { id: "capa", label: "CAPA Management", icon: ShieldCheck, purpose: "Containment, corrective & preventive actions" },
        { id: "ai-review", label: "AI Review Center", icon: Bot, purpose: "Multi-agent review and HITL sign-off gate" },
        { id: "reports", label: "Reports", icon: FileText, purpose: "ISO 9001 / IATF 16949 audit dossier PDF" },
      ]
    },
    {
      title: "CONFIGURATION",
      items: [
        { id: "product-config", label: "Product Configuration", icon: Settings, purpose: "Product specs, machines & tolerances" },
        { id: "machine-config", label: "Machine Configuration", icon: Cpu, purpose: "Machine baselines, telemetry thresholds & units" },
      ]
    }
  ];

  const productionTeamSections = [
    {
      title: "OVERVIEW",
      items: [
        { id: "production-dashboard", label: "Production Dashboard", icon: LayoutDashboard, purpose: "Batch actions, intake & active work" },
      ]
    },
    {
      title: "PRODUCTION & INTAKE",
      items: [
        { id: "batch-intake", label: "Batch Registration", icon: PlusCircle, purpose: "Guided 8-step production intake wizard" },
        { id: "batches", label: "Production Batches", icon: Layers, purpose: "Batch records and traceability" },
        { id: "inspection", label: "Measurement Center", icon: Ruler, purpose: "CMM measurements intake and verification" },
        { id: "visual-inspection", label: "Visual Surface Check", icon: Camera, purpose: "Upload part photos for visual inspection" },
        { id: "process-monitoring", label: "Process Telemetry", icon: Activity, purpose: "Machine telemetry and sensor logs" },
      ]
    }
  ];

  const navSections = isQE ? qualityEngineerSections : productionTeamSections;

  return (
    <aside
      className={`bg-slate-900 border-r border-slate-800 flex flex-col h-screen sticky top-0 shrink-0 select-none z-20 text-slate-300 transition-all duration-300 ease-in-out ${
        isCollapsed ? "w-[76px]" : "w-[272px]"
      }`}
    >
      {/* -------------------- BRAND HEADER & TOGGLE OPTION -------------------- */}
      <div className="border-b border-slate-800 shrink-0 bg-slate-950/80 transition-all">
        {isCollapsed ? (
          // Collapsed Brand Header: Compact Icon + Toggle Expand Button
          <div className="py-3.5 px-2 flex flex-col items-center gap-2.5">
            <button
              onClick={onToggleCollapse}
              title="Expand Sidebar"
              className="p-1 rounded-xl bg-slate-900 border border-slate-800 shadow-sm hover:border-blue-500 hover:scale-105 transition-all cursor-pointer group"
            >
              <img
                src="/logo-icon.png"
                alt="QualiForge Logo"
                className="w-10 h-10 object-contain drop-shadow-[0_0_10px_rgba(59,130,246,0.3)]"
              />
            </button>

            {onToggleCollapse && (
              <button
                onClick={onToggleCollapse}
                title="Expand Sidebar"
                className="w-7 h-7 rounded-lg bg-slate-800/80 hover:bg-blue-600 hover:text-white text-slate-400 flex items-center justify-center transition-colors cursor-pointer"
              >
                <ChevronRight className="w-4 h-4" />
              </button>
            )}
          </div>
        ) : (
          // Expanded Brand Header: Full Logo, Title, and Collapse Button
          <div className="px-4 py-3.5">
            <div className="flex items-center justify-between gap-2">
              <div className="p-2 rounded-xl bg-slate-900 border border-slate-800 shadow-sm flex items-center justify-center flex-1">
                <img
                  src="/logo.png"
                  alt="QualiForge Logo"
                  className="h-10 w-auto object-contain drop-shadow-[0_0_12px_rgba(59,130,246,0.35)]"
                />
              </div>

              {onToggleCollapse && (
                <button
                  onClick={onToggleCollapse}
                  title="Collapse Sidebar"
                  className="p-2 rounded-lg bg-slate-800/60 hover:bg-slate-800 hover:text-white text-slate-400 transition-colors cursor-pointer shrink-0"
                >
                  <ChevronLeft className="w-4 h-4" />
                </button>
              )}
            </div>

            <div className="mt-2 px-1 flex items-center justify-between text-[11px] text-slate-400 font-medium">
              <span className="truncate">{isQE ? "Quality Engineer Workspace" : "Production Workspace"}</span>
              <span className="shrink-0 text-[9px] font-mono font-bold px-1.5 py-0.5 rounded bg-blue-950 text-blue-300 border border-blue-800/60">
                ENTERPRISE
              </span>
            </div>
          </div>
        )}
      </div>

      {/* -------------------- ROLE PILL BANNER -------------------- */}
      <div className={`border-b border-slate-800 text-xs transition-all ${
        isCollapsed ? "py-2 px-2 flex justify-center bg-slate-800/40" : "px-4 py-2.5 bg-slate-800/60 flex items-center justify-between"
      }`}>
        {isCollapsed ? (
          <div
            title={`Current Role: ${isQE ? "Quality Engineer" : "Production Team"}`}
            className="p-1 rounded-md bg-slate-800 text-blue-400 flex items-center justify-center cursor-default"
          >
            {isQE ? (
              <ShieldCheck className="w-4 h-4 text-blue-400" />
            ) : (
              <Factory className="w-4 h-4 text-emerald-400" />
            )}
          </div>
        ) : (
          <>
            <div className="flex items-center gap-1.5 font-medium">
              {isQE ? (
                <ShieldCheck className="w-3.5 h-3.5 text-blue-400" />
              ) : (
                <Factory className="w-3.5 h-3.5 text-emerald-400" />
              )}
              <span className="text-slate-300 font-semibold">
                {isQE ? "Quality Engineer" : "Production Team"}
              </span>
            </div>

            {onRoleChange && (
              <button
                onClick={() => onRoleChange(isQE ? "operator" : "quality_engineer")}
                title="Switch Workspace View"
                className="text-[10px] text-blue-400 hover:text-blue-300 flex items-center gap-1 font-mono hover:underline cursor-pointer"
              >
                <ArrowRightLeft className="w-3 h-3" /> Switch
              </button>
            )}
          </>
        )}
      </div>

      {/* -------------------- NAVIGATION LINKS -------------------- */}
      <nav className={`flex-1 overflow-y-auto ${isCollapsed ? "py-4 px-2 space-y-4" : "px-3 py-4 space-y-6"}`}>
        {navSections.map((sec, idx) => (
          <div key={idx} className={idx > 0 && !isCollapsed ? "mt-5" : ""}>
            {/* Category title only visible when expanded */}
            {!isCollapsed && (
              <div className="px-3 mb-2 text-[11px] font-bold text-slate-400 tracking-[0.08em] uppercase">
                {sec.title}
              </div>
            )}

            <div className={isCollapsed ? "space-y-2" : "space-y-1"}>
              {sec.items.map((item) => {
                const Icon = item.icon;
                const isActive = activePage === item.id;

                if (isCollapsed) {
                  // COLLAPSED: ONLY LOGO / ICON FOR EACH AGENT VISIBLE
                  return (
                    <div key={item.id} className="relative group flex justify-center">
                      <button
                        onClick={() => setActivePage(item.id)}
                        className={`w-11 h-11 rounded-xl flex items-center justify-center transition-all cursor-pointer ${
                          isActive
                            ? "bg-blue-600 text-white shadow-md shadow-blue-600/30 ring-2 ring-blue-400/50"
                            : "text-slate-400 hover:bg-slate-800 hover:text-white"
                        }`}
                      >
                        <Icon className="w-5 h-5 shrink-0" />
                      </button>

                      {/* Tooltip on Hover */}
                      <div className="absolute left-full ml-3 top-1/2 -translate-y-1/2 hidden group-hover:flex flex-col bg-slate-950 text-white px-3 py-2 rounded-lg shadow-2xl z-50 pointer-events-none whitespace-nowrap border border-slate-700">
                        <span className="text-xs font-bold text-white leading-tight">{item.label}</span>
                        <span className="text-[10px] text-slate-400 leading-tight mt-0.5">{item.purpose}</span>
                      </div>
                    </div>
                  );
                }

                // EXPANDED: FULL LABEL + ICON + PURPOSE
                return (
                  <button
                    key={item.id}
                    onClick={() => setActivePage(item.id)}
                    title={item.purpose}
                    className={`w-full flex items-center justify-between px-3 py-2 rounded-lg text-xs font-medium transition-all cursor-pointer ${
                      isActive
                        ? "bg-blue-600 text-white font-semibold shadow-xs"
                        : "text-slate-300 hover:bg-slate-800/80 hover:text-white"
                    }`}
                  >
                    <div className="flex items-center gap-2.5 truncate">
                      <Icon className={`w-4 h-4 shrink-0 ${isActive ? "text-white" : "text-slate-400"}`} />
                      <span className="truncate">{item.label}</span>
                    </div>
                  </button>
                );
              })}
            </div>
          </div>
        ))}
      </nav>

      {/* -------------------- USER SESSION FOOTER -------------------- */}
      <div className={`border-t border-slate-800 bg-slate-950/40 transition-all ${isCollapsed ? "p-2 flex flex-col items-center gap-2" : "p-3"}`}>
        {isCollapsed ? (
          <>
            <div
              title={isQE ? "Sarah Chen (Quality Engineer)" : "Line Operator (Shift 1)"}
              className="w-10 h-10 rounded-xl bg-slate-800 text-blue-400 font-bold text-xs flex items-center justify-center cursor-default"
            >
              {isQE ? "SC" : "OP"}
            </div>

            {onLogout && (
              <button
                onClick={onLogout}
                title="Sign Out"
                className="w-8 h-8 rounded-lg text-slate-400 hover:text-rose-400 hover:bg-slate-800 flex items-center justify-center transition-colors cursor-pointer"
              >
                <LogOut className="w-4 h-4" />
              </button>
            )}
          </>
        ) : (
          <div className="flex items-center justify-between px-2 py-1.5 rounded-lg bg-slate-800/50 text-xs">
            <div className="truncate">
              <div className="text-white font-medium truncate">
                {isQE ? "Sarah Chen (QE)" : "Line Operator (Shift 1)"}
              </div>
              <div className="text-[10px] text-slate-400 truncate">Plant 01 &bull; CNC Cell</div>
            </div>
            {onLogout && (
              <button
                onClick={onLogout}
                title="Sign Out"
                className="p-1.5 text-slate-400 hover:text-rose-400 hover:bg-slate-800 rounded transition-colors cursor-pointer"
              >
                <LogOut className="w-4 h-4" />
              </button>
            )}
          </div>
        )}
      </div>
    </aside>
  );
};

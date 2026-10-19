import React, { useState, useEffect } from "react";
import { Sidebar } from "./components/Sidebar";
import { Header } from "./components/Header";
import { LandingPage } from "./pages/LandingPage";
import { LoginPage } from "./pages/LoginPage";
import { RegisterPage } from "./pages/RegisterPage";
import { QualityEngineerDashboard } from "./pages/QualityEngineerDashboard";
import { ProductionDashboard } from "./pages/ProductionDashboard";
import { BatchRegistrationWizard } from "./pages/BatchRegistrationWizard";
import { ProductConfigPage } from "./pages/ProductConfigPage";
import { BatchesPage } from "./pages/BatchesPage";
import { InspectionPage } from "./pages/InspectionPage";
import { VisualInspectionPage } from "./pages/VisualInspectionPage";
import { ProcessMonitoringPage } from "./pages/ProcessMonitoringPage";
import { SpcDashboardPage } from "./pages/SpcDashboardPage";
import { IncidentsPage } from "./pages/IncidentsPage";
import { RcaPage } from "./pages/RcaPage";
import { CapaPage } from "./pages/CapaPage";
import { AiReviewPage } from "./pages/AiReviewPage";
import { ReportsPage } from "./pages/ReportsPage";
import { TestScenariosPage } from "./pages/TestScenariosPage";
import { MachineConfigPage } from "./pages/MachineConfigPage";
import { ProcessInvestigationPage } from "./pages/ProcessInvestigationPage";
import { api } from "./api";
import {
  CheckCircle2, Clock, Loader2, Minus, Maximize2, X, ShieldAlert,
  ArrowRight
} from "lucide-react";

interface PipelineStep {
  id: number;
  label: string;
  durationEstimateMs: number;
}

const PIPELINE_STAGES: PipelineStep[] = [
  { id: 1, label: "Checking batch data and measurement intake", durationEstimateMs: 600 },
  { id: 2, label: "Inspecting surface quality and defect localization", durationEstimateMs: 900 },
  { id: 3, label: "Evaluating dimensional specification conformance", durationEstimateMs: 500 },
  { id: 4, label: "Monitoring machine telemetry and process stability", durationEstimateMs: 700 },
  { id: 5, label: "Computing statistical process control (SPC) metrics", durationEstimateMs: 600 },
  { id: 6, label: "Investigating failure modes and historical root causes", durationEstimateMs: 800 },
  { id: 7, label: "Formulating containment and corrective action plans", durationEstimateMs: 700 },
  { id: 8, label: "Preparing quality dossier for human review", durationEstimateMs: 500 }
];

const VALID_APP_PAGES: Record<string, string> = {
  "quality-dashboard": "quality-dashboard",
  "dashboard": "quality-dashboard",
  "production-dashboard": "production-dashboard",
  "batch-intake": "batch-intake",
  "product-config": "product-config",
  "machine-config": "machine-config",
  "batches": "batches",
  "inspection": "inspection",
  "process-investigation": "process-investigation",
  "visual-inspection": "visual-inspection",
  "process-monitoring": "process-monitoring",
  "spc-dashboard": "spc-dashboard",
  "spc": "spc-dashboard",
  "incidents": "incidents",
  "rca": "rca",
  "capa": "capa",
  "ai-review": "ai-review",
  "reports": "reports",
  "test-scenarios": "test-scenarios"
};

function parseInitialRoute() {
  if (typeof window === "undefined") {
    return { view: "landing" as const, page: "quality-dashboard", batchId: "", machineId: "CNC-01" };
  }
  const cleanPath = window.location.pathname.replace(/^\/+|\/+$/g, "");
  const searchParams = new URLSearchParams(window.location.search);
  const qBatch = searchParams.get("batch_id") || searchParams.get("batch") || "";
  const qMachine = searchParams.get("machine_id") || searchParams.get("machine") || "CNC-01";

  if (cleanPath === "login") {
    return { view: "login" as const, page: "quality-dashboard", batchId: qBatch, machineId: qMachine };
  }
  if (cleanPath === "register") {
    return { view: "register" as const, page: "quality-dashboard", batchId: qBatch, machineId: qMachine };
  }
  if (cleanPath === "landing") {
    return { view: "landing" as const, page: "quality-dashboard", batchId: qBatch, machineId: qMachine };
  }
  if (cleanPath === "") {

    const token = localStorage.getItem("qualiforge_token");
    const savedActive = localStorage.getItem("qualiforge_active_page");
    if (token && savedActive && VALID_APP_PAGES[savedActive]) {
      return { view: "app" as const, page: VALID_APP_PAGES[savedActive], batchId: qBatch, machineId: qMachine };
    }
    return { view: "landing" as const, page: "quality-dashboard", batchId: qBatch, machineId: qMachine };
  }

  if (VALID_APP_PAGES[cleanPath]) {
    return { view: "app" as const, page: VALID_APP_PAGES[cleanPath], batchId: qBatch, machineId: qMachine };
  }

  return { view: "app" as const, page: "quality-dashboard", batchId: qBatch, machineId: qMachine };
}

export function App() {
  const initialRoute = parseInitialRoute();

  const [currentView, setCurrentView] = useState<"landing" | "login" | "register" | "app">(initialRoute.view);

  const [userRole, setUserRole] = useState<"admin" | "quality_engineer" | "operator">(() => {
    const savedRole = localStorage.getItem("qualiforge_role") as any;
    return savedRole || "quality_engineer";
  });

  const [activePage, setActivePage] = useState<string>(initialRoute.page);
  const [activeWorkflowId, setActiveWorkflowId] = useState<string>("");
  const [selectedBatchId, setSelectedBatchId] = useState<string>(initialRoute.batchId || "");
  const [selectedMachineId, setSelectedMachineId] = useState<string>(initialRoute.machineId || "CNC-01");
  const [isRunningPipeline, setIsRunningPipeline] = useState(false);
  const [showProgressModal, setShowProgressModal] = useState(false);
  const [isMinimized, setIsMinimized] = useState(false);
  const [currentStepIndex, setCurrentStepIndex] = useState(0);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [completedSteps, setCompletedSteps] = useState<number[]>([]);
  const [pipelineFinishedBanner, setPipelineFinishedBanner] = useState(false);

  useEffect(() => {
    const onPopState = () => {
      const r = parseInitialRoute();
      setCurrentView(r.view);
      setActivePage(r.page);
      if (r.batchId) setSelectedBatchId(r.batchId);
      if (r.machineId) setSelectedMachineId(r.machineId);
    };
    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, []);

  const navigateTo = (page: string, params?: Record<string, string>) => {
    setActivePage(page);
    setCurrentView("app");
    localStorage.setItem("qualiforge_active_page", page);

    const targetUrl = new URL(window.location.origin + "/" + page);
    if (params) {
      Object.entries(params).forEach(([k, v]) => {
        if (v) targetUrl.searchParams.set(k, v);
      });
    } else {
      const currentBatch = selectedBatchId || initialRoute.batchId;
      if (currentBatch && ["inspection", "process-investigation", "process-monitoring", "rca", "capa", "ai-review"].includes(page)) {
        targetUrl.searchParams.set("batch_id", currentBatch);
      }
    }
    window.history.pushState({ page, view: "app" }, "", targetUrl.pathname + targetUrl.search);
  };

  const navigateToView = (view: "landing" | "login" | "register") => {
    setCurrentView(view);
    const path = view === "landing" ? "/" : "/" + view;
    window.history.pushState({ view }, "", path);
  };

  useEffect(() => {
    api.getBatches().then((batches) => {
      if (Array.isArray(batches) && batches.length > 0) {
        setSelectedBatchId((prev) => prev || batches[0].batch_number || batches[0].batch_id || batches[0].id || "");
      }
    }).catch(() => {});
  }, []);

  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState<boolean>(() => {
    return localStorage.getItem("qualiforge_sidebar_collapsed") === "true";
  });

  const handleToggleSidebar = () => {
    setIsSidebarCollapsed((prev) => {
      const next = !prev;
      localStorage.setItem("qualiforge_sidebar_collapsed", String(next));
      return next;
    });
  };

  useEffect(() => {
    let interval: any = null;
    if (isRunningPipeline) {
      interval = setInterval(() => {
        setElapsedSeconds((s) => s + 1);
      }, 1000);
    } else {
      if (interval) clearInterval(interval);
    }
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [isRunningPipeline]);

  const handleRoleChange = (newRole: "admin" | "quality_engineer" | "operator") => {
    setUserRole(newRole);
    localStorage.setItem("qualiforge_role", newRole);
    const target = newRole === "operator" ? "production-dashboard" : "quality-dashboard";
    navigateTo(target);
  };

  const handleLoginSuccess = (role: "admin" | "quality_engineer" | "operator") => {
    setUserRole(role);
    localStorage.setItem("qualiforge_role", role);
    const target = role === "operator" ? "production-dashboard" : "quality-dashboard";
    navigateTo(target);
  };

  const handleLogout = () => {
    api.logout();
    navigateToView("landing");
  };

  const handleRunPipeline = async (batchId?: string) => {
    const targetBatch = batchId || selectedBatchId;
    if (!targetBatch) {
      alert("No production batch registered yet. Please register a batch before running the quality intelligence pipeline.");
      return;
    }
    setIsRunningPipeline(true);
    setShowProgressModal(true);
    setIsMinimized(false);
    setCurrentStepIndex(0);
    setElapsedSeconds(0);
    setCompletedSteps([]);
    setPipelineFinishedBanner(false);

    try {
      const res = await api.runOrchestratedPipeline(targetBatch);
      if (res?.workflow_id) {
        setActiveWorkflowId(res.workflow_id);
      }
      setCompletedSteps(PIPELINE_STAGES.map((s) => s.id));
      setCurrentStepIndex(PIPELINE_STAGES.length - 1);
      setTimeout(() => {
        setShowProgressModal(false);
        setPipelineFinishedBanner(true);
        navigateTo("ai-review");
        setTimeout(() => setPipelineFinishedBanner(false), 8000);
      }, 900);
    } catch (e) {
      alert("Analysis could not be completed. Please try again.");
    } finally {
      setIsRunningPipeline(false);
    }
  };

  const formatTime = (secs: number) => {
    const m = Math.floor(secs / 60);
    const s = secs % 60;
    return `${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
  };

  if (currentView === "landing") {
    return (
      <LandingPage
        onNavigateToLogin={(initialRole) => {
          if (initialRole) setUserRole(initialRole);
          navigateToView("login");
        }}
        onExplore={() => {
          navigateTo(userRole === "operator" ? "production-dashboard" : "quality-dashboard");
        }}
      />
    );
  }

  if (currentView === "login") {
    return (
      <LoginPage
        onSuccess={handleLoginSuccess}
        onNavigateToRegister={() => navigateToView("register")}
        onNavigateToLanding={() => navigateToView("landing")}
        initialRole={userRole === "operator" ? "operator" : "quality_engineer"}
      />
    );
  }

  if (currentView === "register") {
    return (
      <RegisterPage
        onNavigateToLogin={() => navigateToView("login")}
        onNavigateToLanding={() => navigateToView("landing")}
      />
    );
  }

  const isQE = userRole === "quality_engineer" || userRole === "admin";

  const renderCurrentPage = () => {

    const qeOnlyPages = ["spc-dashboard", "incidents", "rca", "capa", "product-config", "machine-config"];
    if (!isQE && qeOnlyPages.includes(activePage)) {
      return (
        <div className="p-8 bg-amber-50 border border-amber-200 rounded-2xl max-w-2xl mx-auto my-12 text-center space-y-4">
          <div className="w-12 h-12 rounded-full bg-amber-100 text-amber-700 flex items-center justify-center mx-auto">
            <ShieldAlert className="w-6 h-6" />
          </div>
          <h3 className="text-lg font-bold text-slate-900">Quality Engineer Authorization Required</h3>
          <p className="text-xs text-slate-600 leading-relaxed">
            In accordance with industrial quality governance (IATF 16949 / ISO 9001), access to statistical process control limit configuration,
            incident non-conformance records, root cause investigations, and CAPA approval requires authenticated Quality Engineer permissions.
          </p>
          <div className="pt-2 flex justify-center gap-3">
            <button
              onClick={() => navigateTo("production-dashboard")}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs font-semibold cursor-pointer"
            >
              Return to Production Workspace
            </button>
            <button
              onClick={() => handleRoleChange("quality_engineer")}
              className="px-4 py-2 bg-white border border-slate-300 text-slate-700 rounded-lg text-xs font-semibold cursor-pointer"
            >
              Switch to Quality Engineer View
            </button>
          </div>
        </div>
      );
    }

    switch (activePage) {
      case "quality-dashboard":
      case "dashboard":
        return (
          <QualityEngineerDashboard
            onNavigate={navigateTo}
            onSelectBatch={(bId) => {
              setSelectedBatchId(bId);
              navigateTo("inspection", { batch_id: bId });
            }}
          />
        );
      case "production-dashboard":
        return (
          <ProductionDashboard
            onNavigate={navigateTo}
            onSelectBatch={(bId) => {
              setSelectedBatchId(bId);
            }}
            onRunAnalysis={(bId) => handleRunPipeline(bId)}
          />
        );
      case "process-investigation":
        return (
          <ProcessInvestigationPage
            initialBatchId={selectedBatchId || "BATCH-0245"}
            onNavigate={navigateTo}
            onSelectBatch={(bId) => {
              setSelectedBatchId(bId);
            }}
          />
        );
      case "batch-intake":
        return (
          <BatchRegistrationWizard
            onNavigate={navigateTo}
            onBatchCreated={(bId) => {
              setSelectedBatchId(bId);
            }}
          />
        );
      case "product-config":
        return (
          <ProductConfigPage
            onNavigate={(page, mId) => {
              if (mId) setSelectedMachineId(mId);
              navigateTo(page);
            }}
          />
        );
      case "machine-config":
        return (
          <MachineConfigPage
            initialMachineId={selectedMachineId}
            onNavigate={navigateTo}
          />
        );
      case "batches":
        return (
          <BatchesPage
            onNavigate={navigateTo}
            onSelectWorkflow={(wfId: string) => {
              setActiveWorkflowId(wfId);
              navigateTo("ai-review");
            }}
          />
        );
      case "inspection":
        return <InspectionPage />;
      case "visual-inspection":
        return <VisualInspectionPage />;
      case "process-monitoring":
        return <ProcessMonitoringPage />;
      case "spc-dashboard":
        return <SpcDashboardPage />;
      case "incidents":
        return <IncidentsPage onNavigate={navigateTo} />;
      case "rca":
        return <RcaPage />;
      case "capa":
        return <CapaPage />;
      case "ai-review":
        return (
          <AiReviewPage
            onRunPipeline={() => handleRunPipeline(selectedBatchId)}
            isRunningPipeline={isRunningPipeline}
            userRole={userRole}
            workflowId={activeWorkflowId}
          />
        );
      case "reports":
        return <ReportsPage />;
      case "test-scenarios":
        return <TestScenariosPage />;
      default:
        return isQE ? (
          <QualityEngineerDashboard onNavigate={navigateTo} />
        ) : (
          <ProductionDashboard onNavigate={navigateTo} />
        );
    }
  };

  return (
    <div className="flex h-screen bg-slate-100 overflow-hidden font-sans antialiased text-slate-900">

      <Sidebar
        activePage={activePage}
        setActivePage={navigateTo}
        userRole={userRole}
        onRoleChange={handleRoleChange}
        onLogout={handleLogout}
        isCollapsed={isSidebarCollapsed}
        onToggleCollapse={handleToggleSidebar}
      />

      <div className="flex-1 flex flex-col min-w-0 h-screen overflow-hidden">

        <Header
          activePage={activePage}
          onRunPipeline={() => handleRunPipeline(selectedBatchId)}
          isRunningPipeline={isRunningPipeline}
          onNavigate={navigateTo}
          userRole={userRole}
          onRoleChange={handleRoleChange}
          onLogout={handleLogout}
          isSidebarCollapsed={isSidebarCollapsed}
          onToggleSidebar={handleToggleSidebar}
        />

        {pipelineFinishedBanner && (
          <div className="bg-emerald-50 border-b border-emerald-200 text-emerald-800 px-6 py-2.5 flex items-center justify-between text-xs font-semibold shadow-2xs animate-in fade-in duration-200">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-600" />
              <span>Full multi-agent quality analysis completed. Results compiled for human review.</span>
            </div>
            <button
              onClick={() => setPipelineFinishedBanner(false)}
              className="text-emerald-700 hover:text-emerald-900 text-xs font-bold cursor-pointer"
            >
              &times; Dismiss
            </button>
          </div>
        )}

        <main className="flex-1 overflow-y-auto p-6 lg:p-8">
          <div className="max-w-[1500px] mx-auto pb-12">
            {renderCurrentPage()}
          </div>
        </main>
      </div>

      {showProgressModal && (
        <div
          role="region"
          aria-live="polite"
          aria-busy={isRunningPipeline}
          className={`fixed z-50 transition-all duration-200 ${
            isMinimized
              ? "bottom-5 right-5 w-80 bg-white border border-slate-200 rounded-xl shadow-xl p-3"
              : "inset-0 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4"
          }`}
        >
          <div className={`bg-white rounded-2xl shadow-2xl border border-slate-200 overflow-hidden ${isMinimized ? "w-full" : "w-full max-w-lg"}`}>

            <div className="px-5 py-4 bg-slate-900 text-white flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <Loader2 className="w-5 h-5 text-blue-400 animate-spin" />
                <div>
                  <h3 className="text-sm font-bold text-white">8-Agent Quality Pipeline Running</h3>
                  <p className="text-[11px] text-slate-400">Target: {selectedBatchId} &bull; CNC Machining Cell</p>
                </div>
              </div>
              <div className="flex items-center gap-1.5">
                <button
                  onClick={() => setIsMinimized(!isMinimized)}
                  className="p-1 text-slate-400 hover:text-white rounded"
                >
                  {isMinimized ? <Maximize2 className="w-3.5 h-3.5" /> : <Minus className="w-3.5 h-3.5" />}
                </button>
                <button
                  onClick={() => setShowProgressModal(false)}
                  className="p-1 text-slate-400 hover:text-white rounded"
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>

            {!isMinimized && (
              <div className="p-6 space-y-4">
                <div className="space-y-2">
                  {PIPELINE_STAGES.map((st, idx) => {
                    const isDone = completedSteps.includes(st.id);
                    const isCurrent = currentStepIndex === idx;
                    return (
                      <div key={st.id} className="flex items-center gap-3 text-xs">
                        <div className="w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold shrink-0">
                          {isDone ? (
                            <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                          ) : isCurrent ? (
                            <Loader2 className="w-4 h-4 text-blue-600 animate-spin" />
                          ) : (
                            <div className="w-2 h-2 rounded-full bg-slate-300" />
                          )}
                        </div>
                        <span className={isCurrent ? "font-bold text-slate-900" : isDone ? "text-slate-700" : "text-slate-400"}>
                          {st.label}
                        </span>
                      </div>
                    );
                  })}
                </div>

                <div className="pt-3 border-t border-slate-100 flex items-center justify-between text-xs text-slate-500 font-mono">
                  <span>Elapsed Time: {formatTime(elapsedSeconds)}</span>
                  <span>Deterministic Execution</span>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export default App;

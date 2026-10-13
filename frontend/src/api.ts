import {
  ProductSpec, ProductionBatch, InspectionReport, VisualDefectPrediction,
  ProcessMonitoringReport, SPCReport, RCAReport, CAPAReport, CAPAActionRecord,
  WorkflowState, TestScenarioResult, AgentStepLog
} from "./types";

// Resolve API Base URL:
// Prioritizes VITE_API_BASE_URL if configured; otherwise defaults to same-origin "/api"
const rawApiUrl = (import.meta.env.VITE_API_BASE_URL || import.meta.env.VITE_API_URL || "").trim().replace(/\/$/, "");
const API_BASE = rawApiUrl
  ? (rawApiUrl.endsWith("/api") ? rawApiUrl : `${rawApiUrl}/api`)
  : "/api";

async function parseJsonSafe(res: Response): Promise<any> {
  const text = await res.text();
  try {
    return JSON.parse(text);
  } catch {
    if (text.startsWith("<!DOCTYPE") || text.includes("<html")) {
      throw new Error(`API returned HTML (HTTP ${res.status}) instead of JSON. Ensure VITE_API_BASE_URL is set to https://qualiforge-app.onrender.com/api`);
    }
    throw new Error(`API returned invalid JSON (HTTP ${res.status}): ${text.slice(0, 100)}`);
  }
}

function getAuthHeaders(): Record<string, string> {
  const token = localStorage.getItem("qualiforge_token");
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  return headers;
}

export const api = {
  ensureAuthToken: async (): Promise<string> => {
    return localStorage.getItem("qualiforge_token") || "";
  },

  login: async (username?: string, password?: string) => {
    const res = await fetch(`${API_BASE}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    });
    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || "Authentication failed");
    }
    if (data.access_token) {
      localStorage.setItem("qualiforge_token", data.access_token);
      localStorage.setItem("qualiforge_role", data.role);
      localStorage.setItem("qualiforge_user", JSON.stringify(data));
    }
    return data;
  },

  getMe: async () => {
    const token = localStorage.getItem("qualiforge_token");
    const headers: Record<string, string> = {};
    if (token) headers["Authorization"] = `Bearer ${token}`;
    const res = await fetch(`${API_BASE}/auth/me`, { headers });
    return res.json();
  },

  logout: () => {
    localStorage.removeItem("qualiforge_token");
    localStorage.removeItem("qualiforge_role");
    localStorage.removeItem("qualiforge_user");
  },

  getDashboardSummary: async (startDate?: string, endDate?: string) => {
    const params = new URLSearchParams();
    if (startDate) params.set("start_date", startDate);
    if (endDate) params.set("end_date", endDate);
    const qs = params.toString() ? `?${params.toString()}` : "";
    const res = await fetch(`${API_BASE}/dashboard/summary${qs}`);
    return res.json();
  },

  getProducts: async (): Promise<ProductSpec[]> => {
    const res = await fetch(`${API_BASE}/products`);
    return res.json();
  },

  getMachines: async (): Promise<any[]> => {
    const res = await fetch(`${API_BASE}/machines`);
    return res.json();
  },

  getMachine: async (machineId: string): Promise<any> => {
    const res = await fetch(`${API_BASE}/machines/${encodeURIComponent(machineId)}`);
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Failed to load machine details");
    return data;
  },

  createMachine: async (machineData: any, _token?: string): Promise<any> => {
    const token = _token || localStorage.getItem("qualiforge_token");
    const headers: Record<string, string> = { "Content-Type": "application/json" };
    if (token) headers["Authorization"] = `Bearer ${token}`;
    headers["x-enforce-role"] = "true";
    const res = await fetch(`${API_BASE}/machines`, {
      method: "POST",
      headers,
      body: JSON.stringify(machineData),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Failed to register machine");
    return data;
  },

  updateMachine: async (machineId: string, machineData: any, _token?: string): Promise<any> => {
    const token = _token || localStorage.getItem("qualiforge_token");
    const headers: Record<string, string> = { "Content-Type": "application/json" };
    if (token) headers["Authorization"] = `Bearer ${token}`;
    headers["x-enforce-role"] = "true";
    const res = await fetch(`${API_BASE}/machines/${encodeURIComponent(machineId)}`, {
      method: "PUT",
      headers,
      body: JSON.stringify(machineData),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Failed to update machine");
    return data;
  },

  getMachineBaselines: async (machineId: string): Promise<any> => {
    const res = await fetch(`${API_BASE}/process/baselines?machine=${encodeURIComponent(machineId)}`);
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Failed to load machine baselines");
    return data;
  },

  saveMachineBaselines: async (machineId: string, baselines: any[], _token?: string): Promise<any> => {
    const token = _token || localStorage.getItem("qualiforge_token");
    const headers: Record<string, string> = { "Content-Type": "application/json" };
    if (token) headers["Authorization"] = `Bearer ${token}`;
    headers["x-enforce-role"] = "true";
    const res = await fetch(`${API_BASE}/process/baselines`, {
      method: "PUT",
      headers,
      body: JSON.stringify({ machine_id: machineId, baselines }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Failed to save machine baselines");
    return data;
  },


  createProduct: async (productData: any, _token?: string): Promise<ProductSpec> => {
    const res = await fetch(`${API_BASE}/products`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(productData),
    });
    const data = await res.json();
    if (!res.ok) {
      const errMsg = typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail);
      throw new Error(errMsg || "Failed to create product");
    }
    return data;
  },

  updateProduct: async (productId: string, productData: any, _token?: string): Promise<ProductSpec> => {
    const res = await fetch(`${API_BASE}/products/${encodeURIComponent(productId)}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(productData),
    });
    const data = await res.json();
    if (!res.ok) {
      const errMsg = typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail);
      throw new Error(errMsg || "Failed to update product");
    }
    return data;
  },

  deleteProduct: async (productId: string, _token?: string): Promise<any> => {
    const res = await fetch(`${API_BASE}/products/${encodeURIComponent(productId)}`, {
      method: "DELETE",
    });
    const data = await res.json();
    if (!res.ok) {
      const errMsg = typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail);
      throw new Error(errMsg || "Failed to delete product");
    }
    return data;
  },

  loginPersona: async (_role?: string): Promise<string> => {
    return "";
  },

  getBatches: async (params?: Record<string, any>): Promise<ProductionBatch[]> => {
    let url = `${API_BASE}/batches`;
    if (params) {
      const q = new URLSearchParams();
      Object.entries(params).forEach(([k, v]) => {
        if (v !== undefined && v !== null && v !== "") {
          q.append(k, String(v));
        }
      });
      const qs = q.toString();
      if (qs) url += `?${qs}`;
    }
    const res = await fetch(url);
    return res.json();
  },

  createBatch: async (batchData: any, _token?: string): Promise<ProductionBatch> => {
    const res = await fetch(`${API_BASE}/batches`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(batchData),
    });
    const data = await res.json();
    if (!res.ok) {
      const errMsg = typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail);
      throw new Error(errMsg || "Failed to create batch");
    }
    return data;
  },

  updateBatch: async (batchId: string, batchData: any, _token?: string): Promise<ProductionBatch> => {
    const res = await fetch(`${API_BASE}/batches/${encodeURIComponent(batchId)}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(batchData),
    });
    const data = await res.json();
    if (!res.ok) {
      const errMsg = typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail);
      throw new Error(errMsg || "Failed to update batch");
    }
    return data;
  },

  deleteBatch: async (batchId: string, _token?: string): Promise<any> => {
    const res = await fetch(`${API_BASE}/batches/${encodeURIComponent(batchId)}`, {
      method: "DELETE",
    });
    const data = await res.json();
    if (!res.ok) {
      const errMsg = typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail);
      throw new Error(errMsg || "Failed to delete batch");
    }
    return data;
  },

  evaluateMeasurements: async (data: { batch_id: string; measurements: any[] }) => {
    const res = await fetch(`${API_BASE}/inspection/evaluate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
    return res.json();
  },

  uploadInspectionFile: async (file: File, batchId: string = "", _token?: string, allowPartial: boolean = false, productId?: string) => {
    const formData = new FormData();
    formData.append("file", file);
    if (batchId) {
      formData.append("batch_id", batchId);
    }
    if (productId) {
      formData.append("product_id", productId);
    }
    formData.append("allow_partial", String(allowPartial));

    const res = await fetch(`${API_BASE}/inspection/measurements/upload`, {
      method: "POST",
      body: formData,
    });
    const data = await res.json();
    if (!res.ok) {
      throw data;
    }
    return data;
  },

  getBatchMeasurements: async (batchId: string = "") => {
    const res = await fetch(`${API_BASE}/inspection/measurements?batch_id=${encodeURIComponent(batchId)}`);
    return res.json();
  },

  addManualMeasurement: async (payload: { batch_id: string; component_id: string; value: number; unit?: string }, _token?: string) => {
    const res = await fetch(`${API_BASE}/inspection/measurements`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await res.json();
    if (!res.ok) {
      const errMsg = typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail);
      throw new Error(errMsg || "Failed to add measurement");
    }
    return data;
  },

  updateManualMeasurement: async (id: string, payload: { value?: number; unit?: string; component_id?: string }, _token?: string) => {
    const res = await fetch(`${API_BASE}/inspection/measurements/${encodeURIComponent(id)}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await res.json();
    if (!res.ok) {
      const errMsg = typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail);
      throw new Error(errMsg || "Failed to update measurement");
    }
    return data;
  },

  deleteManualMeasurement: async (id: string, _token?: string) => {
    const res = await fetch(`${API_BASE}/inspection/measurements/${encodeURIComponent(id)}`, {
      method: "DELETE",
    });
    const data = await res.json();
    if (!res.ok) {
      const errMsg = typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail);
      throw new Error(errMsg || "Failed to delete measurement");
    }
    return data;
  },

  uploadInspectionImage: async (file: File, batchId: string = "", componentId: string = "", _token?: string) => {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("batch_id", batchId);
    formData.append("component_id", componentId);

    const res = await fetch(`${API_BASE}/inspection/images/upload`, {
      method: "POST",
      body: formData,
    });
    const data = await res.json();
    if (!res.ok) {
      const errMsg = typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail);
      throw new Error(errMsg || "Failed to upload image");
    }
    return data;
  },

  getInspectionImages: async (batchId: string = "") => {
    const res = await fetch(`${API_BASE}/inspection/images?batch_id=${encodeURIComponent(batchId)}`);
    return res.json();
  },

  getBatchSpecCheck: async (batchId: string = "") => {
    const res = await fetch(`${API_BASE}/inspection/${encodeURIComponent(batchId)}/spec-check`);
    return res.json();
  },

  uploadCsvInspection: async (file: File, batchId: string = "") => {
    const formData = new FormData();
    formData.append("file", file);
    if (batchId) {
      formData.append("batch_id", batchId);
    }
    const res = await fetch(`${API_BASE}/inspection/measurements/upload`, {
      method: "POST",
      body: formData,
    });
    const data = await res.json();
    if (!res.ok) {
      const errMsg = typeof data.detail === "string"
        ? data.detail
        : Array.isArray(data.detail)
          ? data.detail.map((d: any) => d.msg || JSON.stringify(d)).join("; ")
          : data.message || "Failed to process inspection CSV.";
      throw new Error(errMsg);
    }
    return data;
  },

  getInspectionTemplateUrl: (batchId: string = "") => {
    return `${API_BASE}/inspection/measurements/template?batch_id=${encodeURIComponent(batchId)}`;
  },

  inspectSampleImage: async (sampleName: string = "IMG-001.png") => {
    const res = await fetch(`${API_BASE}/vision/inspect-sample?sample_name=${encodeURIComponent(sampleName)}`, {
      method: "POST",
    });
    return res.json();
  },

  uploadAndInspectImage: async (file: File, batchId: string = "", componentId: string = "") => {
    const formData = new FormData();
    formData.append("file", file);
    if (batchId) {
      formData.append("batch_id", batchId);
    }
    if (componentId) {
      formData.append("component_id", componentId);
    }
    const res = await fetch(`${API_BASE}/vision/upload`, {
      method: "POST",
      body: formData,
    });
    const data = await res.json();
    if (!res.ok) {
      const errMsg = typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail);
      throw new Error(errMsg || "Failed to inspect component image");
    }
    return data;
  },

  getVisionFindings: async () => {
    const res = await fetch(`${API_BASE}/vision/findings`);
    return res.json();
  },

  getTelemetry: async (batchId: string = "", machine?: string): Promise<{
    batch_id: string;
    machine: string;
    report: ProcessMonitoringReport;
    data_points: any[];
    baselines: Record<string, any>;
    trends: Record<string, any>;
    changed_vs_unchanged: any[];
    anomalies: any[];
    warnings: string[];
    log: any;
  }> => {
    let url = `${API_BASE}/process/telemetry?batch_id=${encodeURIComponent(batchId)}`;
    if (machine) url += `&machine=${encodeURIComponent(machine)}`;
    const res = await fetch(url);
    return res.json();
  },

  getProcessAnomalies: async (batchId: string = "", machine: string = "CNC-04") => {
    const res = await fetch(`${API_BASE}/process/anomalies?batch_id=${encodeURIComponent(batchId)}&machine=${encodeURIComponent(machine)}`);
    return res.json();
  },

  getProcessBaselines: async (machine: string = "CNC-04") => {
    const res = await fetch(`${API_BASE}/process/baselines?machine=${encodeURIComponent(machine)}`);
    return res.json();
  },

  uploadProcessTelemetry: async (file: File, batchId: string = "", machineId: string = "CNC-04") => {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("batch_id", batchId);
    formData.append("machine_id", machineId);
    const res = await fetch(`${API_BASE}/process/upload`, {
      method: "POST",
      body: formData,
    });
    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || "Failed to upload process telemetry");
    }
    return data;
  },


  getSpcAnalysis: async (batchId: string = ""): Promise<{
    report: SPCReport;
    log: any;
  }> => {
    const res = await fetch(`${API_BASE}/spc/analyze?batch_id=${encodeURIComponent(batchId)}`);
    return res.json();
  },

  getSpcCapability: async (batchId: string = "") => {
    const res = await fetch(`${API_BASE}/spc/capability?batch_id=${encodeURIComponent(batchId)}`);
    return res.json();
  },

  computeCustomCapability: async (payload: {
    batch_id?: string;
    values: number[];
    usl?: number;
    lsl?: number;
    nominal?: number;
    subgroup_size?: number;
    machine_ids?: string[];
    batch_ids?: string[];
  }) => {
    const res = await fetch(`${API_BASE}/spc/capability`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    return res.json();
  },

  getIncidents: async () => {
    const res = await fetch(`${API_BASE}/incidents`);
    return res.json();
  },

  getRcaAnalysis: async (incidentId: string = "", batchId: string = ""): Promise<{
    report: RCAReport;
    log: any;
  }> => {
    const res = await fetch(`${API_BASE}/rca/analyze?incident_id=${encodeURIComponent(incidentId)}&batch_id=${encodeURIComponent(batchId)}`);
    return res.json();
  },

  searchHistoricalIncidents: async (query: string) => {
    const res = await fetch(`${API_BASE}/rca/rag-search?q=${encodeURIComponent(query)}`);
    return res.json();
  },

  submitHypothesisDecision: async (hypothesisId: string, decision: string, comment?: string) => {
    const res = await fetch(`${API_BASE}/rca/hypotheses/${encodeURIComponent(hypothesisId)}/decision`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ decision, comment })
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `Request failed with status ${res.status}`);
    }
    return res.json();
  },

  getCapaPlan: async (incidentId: string = "", batchId: string = ""): Promise<{
    capa: CAPAReport;
    log: any;
  }> => {
    const res = await fetch(`${API_BASE}/capa/plan?incident_id=${encodeURIComponent(incidentId)}&batch_id=${encodeURIComponent(batchId)}`);
    return res.json();
  },

  runOrchestratedPipeline: async (batchId: string = ""): Promise<WorkflowState> => {
    const res = await fetch(`${API_BASE}/orchestrator/run?batch_id=${encodeURIComponent(batchId)}`, {
      method: "POST",
    });
    return res.json();
  },

  getWorkflow: async (workflowId: string): Promise<WorkflowState> => {
    const res = await fetch(`${API_BASE}/workflows/${encodeURIComponent(workflowId)}`);
    return res.json();
  },

  getLatestWorkflowForBatch: async (batchId: string): Promise<WorkflowState> => {
    const res = await fetch(`${API_BASE}/workflows/batch/${encodeURIComponent(batchId)}`);
    if (!res.ok) throw new Error(`No workflow found for batch ${batchId}`);
    return res.json();
  },


  getWorkflowTrace: async (workflowId: string): Promise<AgentStepLog[]> => {
    const res = await fetch(`${API_BASE}/workflows/${encodeURIComponent(workflowId)}/trace`);
    return res.json();
  },


  runLangGraphPipeline: async (batchId: string = ""): Promise<any> => {
    const res = await fetch(`${API_BASE}/orchestrator/langgraph-run?batch_id=${encodeURIComponent(batchId)}`, {
      method: "POST",
    });
    return res.json();
  },

  submitHumanDecision: async (decisionData: any, _token?: string) => {
    const res = await fetch(`${API_BASE}/review/sign-off`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(decisionData),
    });
    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail?.message || data.detail || "Failed to submit human decision");
    }
    return data;
  },

  submitWorkflowDecision: async (workflowId: string, payload: any, _token?: string) => {
    const res = await fetch(`${API_BASE}/workflows/${encodeURIComponent(workflowId)}/decision`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail?.message || data.detail || "Failed to submit workflow decision");
    }
    return data;
  },

  requestWorkflowReanalysis: async (workflowId: string, targetAgent: string, comment: string, _token?: string) => {
    const res = await fetch(`${API_BASE}/workflows/${encodeURIComponent(workflowId)}/re-analyze`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ target_agent: targetAgent, comment }),
    });
    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail?.message || data.detail || "Failed to request re-analysis");
    }
    return data;
  },

  getHumanDecisions: async (params?: Record<string, string>) => {
    let url = `${API_BASE}/human-decisions`;
    if (params) {
      const q = new URLSearchParams(params).toString();
      if (q) url += `?${q}`;
    }
    const res = await fetch(url);
    if (!res.ok) throw new Error("Failed to fetch human decisions audit log");
    return res.json();
  },

  decideFinding: async (findingId: string, findingType: string, decision: string, comment?: string, _token?: string) => {
    const res = await fetch(`${API_BASE}/inspection/findings/${encodeURIComponent(findingId)}/decision`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ finding_type: findingType, decision, comment }),
    });
    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail?.message || data.detail || "Failed to decide finding");
    }
    return data;
  },


  getAllTestScenarios: async (): Promise<TestScenarioResult[]> => {
    const res = await fetch(`${API_BASE}/scenarios/all`);
    return res.json();
  },

  getSingleTestScenario: async (scenarioId: string): Promise<TestScenarioResult> => {
    const res = await fetch(`${API_BASE}/scenarios/${scenarioId}`);
    return res.json();
  },

  getPdfReportUrl: (batchId: string = "") => {
    return `${API_BASE}/reports/pdf?batch_id=${encodeURIComponent(batchId)}`;
  },

  getPareto: async (dimension: string = "defect_type", startDate?: string, endDate?: string): Promise<any> => {
    let url = `${API_BASE}/pareto?dimension=${encodeURIComponent(dimension)}`;
    if (startDate) url += `&start_date=${encodeURIComponent(startDate)}`;
    if (endDate) url += `&end_date=${encodeURIComponent(endDate)}`;
    const res = await fetch(url);
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `Failed to fetch Pareto data (${res.status})`);
    }
    return res.json();
  },

  listCapaActions: async (filters?: {
    type?: string;
    status?: string;
    due_date?: string;
    incident_id?: string;
    is_overdue?: boolean;
  }): Promise<{ total: number; actions: CAPAActionRecord[] }> => {
    const params = new URLSearchParams();
    if (filters?.type) params.append("type", filters.type);
    if (filters?.status) params.append("status", filters.status);
    if (filters?.due_date) params.append("due_date", filters.due_date);
    if (filters?.incident_id) params.append("incident_id", filters.incident_id);
    if (filters?.is_overdue !== undefined) params.append("is_overdue", String(filters.is_overdue));
    const res = await fetch(`${API_BASE}/capa/actions?${params.toString()}`);
    if (!res.ok) throw new Error("Failed to list CAPA actions");
    return res.json();
  },

  createCapaAction: async (payload: any, _token?: string): Promise<CAPAActionRecord> => {
    const res = await fetch(`${API_BASE}/capa/actions`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || "Failed to create CAPA action");
    }
    return data;
  },

  approveCapaAction: async (actionCode: string, payload?: any, _token?: string): Promise<any> => {
    const res = await fetch(`${API_BASE}/capa/actions/${encodeURIComponent(actionCode)}/approve`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload || {}),
    });
    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || "Failed to approve CAPA action");
    }
    return data;
  },

  rejectCapaAction: async (actionCode: string, reason: string, _token?: string): Promise<any> => {
    const res = await fetch(`${API_BASE}/capa/actions/${encodeURIComponent(actionCode)}/reject`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ reason }),
    });
    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || "Failed to reject CAPA action");
    }
    return data;
  },

  updateCapaAction: async (actionCode: string, payload: any, _token?: string): Promise<any> => {
    const res = await fetch(`${API_BASE}/capa/actions/${encodeURIComponent(actionCode)}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || "Failed to update CAPA action");
    }
    return data;
  },

  deleteCapaAction: async (actionCode: string, _token?: string): Promise<any> => {
    const res = await fetch(`${API_BASE}/capa/actions/${encodeURIComponent(actionCode)}`, {
      method: "DELETE",
    });
    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || "Failed to delete CAPA action");
    }
    return data;
  },

  uploadCapaEvidence: async (actionCode: string, file: File, _token?: string): Promise<any> => {
    const formData = new FormData();
    formData.append("file", file);
    const res = await fetch(`${API_BASE}/capa/actions/${encodeURIComponent(actionCode)}/evidence`, {
      method: "POST",
      body: formData,
    });
    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || "Failed to upload evidence");
    }
    return data;
  },

  getCapaAuditTrail: async (actionCode: string): Promise<any> => {
    const res = await fetch(`${API_BASE}/capa/actions/${encodeURIComponent(actionCode)}/audit`);
    if (!res.ok) throw new Error("Failed to fetch audit trail");
    return res.json();
  },

  checkCapaRecurrence: async (machine: string = "CNC-04", defectType: string = "Oversized shaft diameter"): Promise<any> => {
    const res = await fetch(`${API_BASE}/capa/recurrence-check?machine=${encodeURIComponent(machine)}&defect_type=${encodeURIComponent(defectType)}`);
    if (!res.ok) throw new Error("Failed to check recurrence");
    return res.json();
  },

  getCapaStats: async (): Promise<any> => {
    const res = await fetch(`${API_BASE}/capa/stats`);
    if (!res.ok) throw new Error("Failed to fetch CAPA stats");
    return res.json();
  },

  generateCapaProposals: async (batchId: string = ""): Promise<any> => {
    const res = await fetch(`${API_BASE}/capa/generate-proposals/${encodeURIComponent(batchId)}`, {
      method: "POST",
    });
    if (!res.ok) throw new Error("Failed to generate CAPA proposals");
    return res.json();
  },

  getCapaEffectiveness: async (actionCode: string = "CAPA-2026-001"): Promise<any> => {
    const res = await fetch(`${API_BASE}/effectiveness/${encodeURIComponent(actionCode)}`);
    if (!res.ok) throw new Error("Failed to fetch CAPA effectiveness");
    return res.json();
  }
};


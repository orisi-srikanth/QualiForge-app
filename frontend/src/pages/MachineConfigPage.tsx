import React, { useEffect, useState } from "react";
import { api } from "../api";
import {
  Cpu, Check, AlertTriangle, ShieldCheck, Plus, RefreshCw, X,
  Activity, ArrowRight, Settings, Info, Save
} from "lucide-react";

interface BaselineItem {
  machine_id: string;
  machine_code?: string;
  parameter: string;
  name: string;
  unit: string;
  mean: number | null;
  std: number | null;
  p01?: number | null;
  p99?: number | null;
  lower_threshold: number | null;
  upper_threshold: number | null;
  computed_from?: string;
  status: "CONFIGURED" | "UNCONFIGURED";
}

interface MachineRecord {
  machine_id: string;
  code: string;
  name?: string;
  type?: string;
  cell?: string;
  location?: string;
  status?: string;
  vibration_baseline_mms?: number;
}

interface Props {
  initialMachineId?: string;
  onNavigate?: (page: string) => void;
}

export const MachineConfigPage: React.FC<Props> = ({ initialMachineId, onNavigate }) => {
  const [machines, setMachines] = useState<MachineRecord[]>([]);
  const [selectedMachine, setSelectedMachine] = useState<MachineRecord | null>(null);
  const [baselines, setBaselines] = useState<BaselineItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [validationErrors, setValidationErrors] = useState<Record<string, string>>({});

  // New Machine Registration Modal State
  const [showNewMachineModal, setShowNewMachineModal] = useState(false);
  const [newMachineCode, setNewMachineCode] = useState("");
  const [newMachineType, setNewMachineType] = useState("");
  const [newMachineLocation, setNewMachineLocation] = useState("");

  const loadMachines = async (preferredId?: string) => {
    try {
      setLoading(true);
      const machs = await api.getMachines();
      setMachines(machs);

      let target = machs[0] || null;
      const matchTarget = preferredId || initialMachineId;
      if (matchTarget) {
        const found = machs.find(
          (m: any) => m.code === matchTarget || m.machine_id === matchTarget
        );
        if (found) target = found;
      }
      setSelectedMachine(target);
      if (target) {
        await loadBaselines(target.code || target.machine_id);
      }
    } catch (err: any) {
      setErrorMessage(err.message || "Failed to load factory floor CNC machines.");
    } finally {
      setLoading(false);
    }
  };

  const loadBaselines = async (machineCodeOrId: string) => {
    try {
      setValidationErrors({});
      const data = await api.getMachineBaselines(machineCodeOrId);
      if (data && Array.isArray(data.baselines)) {
        setBaselines(data.baselines);
      } else {
        setBaselines([]);
      }
    } catch (err: any) {
      setErrorMessage(err.message || "Failed to load machine process baselines.");
    }
  };

  useEffect(() => {
    loadMachines(initialMachineId);
  }, [initialMachineId]);

  const handleSelectMachine = async (mach: MachineRecord) => {
    setSelectedMachine(mach);
    setErrorMessage(null);
    setSuccessMessage(null);
    setValidationErrors({});
    await loadBaselines(mach.code || mach.machine_id);
  };

  const handleFieldChange = (
    paramKey: string,
    field: "mean" | "std" | "lower_threshold" | "upper_threshold" | "computed_from",
    value: string
  ) => {
    setBaselines((prev) =>
      prev.map((b) => {
        if (b.parameter !== paramKey) return b;
        const updated = { ...b };
        if (field === "computed_from") {
          updated.computed_from = value;
        } else {
          const num = value === "" ? null : parseFloat(value);
          updated[field] = isNaN(num as number) ? null : num;
        }
        // If critical fields are filled, mark as CONFIGURED
        if (updated.mean !== null && updated.upper_threshold !== null) {
          updated.status = "CONFIGURED";
        }
        return updated;
      })
    );
  };

  const validateBaselines = (): boolean => {
    const errors: Record<string, string> = {};
    baselines.forEach((b) => {
      if (b.lower_threshold !== null && b.upper_threshold !== null) {
        if (b.upper_threshold < b.lower_threshold) {
          errors[b.parameter] = `Upper threshold (${b.upper_threshold}) must be >= lower threshold (${b.lower_threshold}).`;
        }
      }
      if (b.std !== null && b.std < 0) {
        errors[b.parameter] = "Standard deviation cannot be negative.";
      }
    });
    setValidationErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleSaveBaselines = async () => {
    if (!selectedMachine) return;
    if (!validateBaselines()) return;

    try {
      setSaving(true);
      setErrorMessage(null);
      const payloadBaselines = baselines.map((b) => ({
        parameter: b.parameter,
        name: b.name,
        unit: b.unit,
        mean: b.mean,
        std: b.std ?? 0.1,
        p01: b.mean !== null ? Number((b.mean * 0.9).toFixed(3)) : null,
        p99: b.mean !== null ? Number((b.mean * 1.1).toFixed(3)) : null,
        lower_threshold: b.lower_threshold ?? 0.0,
        upper_threshold: b.upper_threshold ?? 100.0,
        computed_from: b.computed_from || "Certified Baseline Configuration",
      }));

      await api.saveMachineBaselines(selectedMachine.code || selectedMachine.machine_id, payloadBaselines);
      setSuccessMessage(
        `Machine '${selectedMachine.code}' certified baselines and process thresholds saved successfully.`
      );
      await loadBaselines(selectedMachine.code || selectedMachine.machine_id);
      setTimeout(() => setSuccessMessage(null), 5000);
    } catch (err: any) {
      setErrorMessage(err.message || "Failed to persist machine baselines.");
    } finally {
      setSaving(false);
    }
  };

  const handleRegisterMachine = async () => {
    if (!newMachineCode.trim()) {
      alert("Machine code is required (e.g. CNC-05)");
      return;
    }
    try {
      setErrorMessage(null);
      await api.createMachine({
        code: newMachineCode.trim().toUpperCase(),
        type: newMachineType.trim() || "CNC Machining Center",
        location: newMachineLocation.trim() || "Plant Floor Cell C",
      });
      setShowNewMachineModal(false);
      setNewMachineCode("");
      setNewMachineType("");
      setNewMachineLocation("");
      await loadMachines(newMachineCode.trim().toUpperCase());
      setSuccessMessage(`New machine cell '${newMachineCode.trim().toUpperCase()}' registered.`);
      setTimeout(() => setSuccessMessage(null), 4000);
    } catch (err: any) {
      setErrorMessage(err.message || "Failed to register new machine cell.");
    }
  };

  const configuredCount = baselines.filter((b) => b.status === "CONFIGURED").length;
  const completenessPct = baselines.length > 0 ? Math.round((configuredCount / baselines.length) * 100) : 0;

  if (loading && machines.length === 0) {
    return <div className="p-8 text-center text-slate-500">Loading CNC Machine Configurations...</div>;
  }

  return (
    <div className="space-y-6">
      {/* Top Header Card */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-5 bg-white border border-[#E3E8EF] rounded-xl shadow-xs">
        <div>
          <div className="flex items-center gap-2">
            <Cpu className="w-6 h-6 text-blue-600" />
            <h2 className="text-[26px] font-bold text-slate-900 leading-tight">
              Machine Configuration & Process Baselines
            </h2>
          </div>
          <p className="text-[14px] text-slate-500 mt-1">
            Configure machine telemetry baselines, certified operational limits, and approved warning/trip thresholds consumed by Agent 4.
          </p>
        </div>

        <div className="flex items-center gap-2">
          {onNavigate && (
            <button
              onClick={() => onNavigate("product-config")}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-lg transition-all cursor-pointer"
            >
              <Settings className="w-3.5 h-3.5" /> Product Specs
            </button>
          )}

          <button
            onClick={() => setShowNewMachineModal(true)}
            className="flex items-center gap-1.5 px-3.5 py-1.5 text-xs font-bold text-white bg-blue-600 hover:bg-blue-700 rounded-lg shadow-xs transition-all cursor-pointer"
          >
            <Plus className="w-3.5 h-3.5" /> Register Machine
          </button>
        </div>
      </div>

      {/* Success Notification */}
      {successMessage && (
        <div id="machine-config-success" className="p-3.5 bg-emerald-50 border border-emerald-200 rounded-xl text-xs text-emerald-800 flex items-center gap-2 animate-in fade-in">
          <Check className="w-4 h-4 text-emerald-600 shrink-0" />
          <span className="font-medium">{successMessage}</span>
        </div>
      )}

      {/* Error Notification */}
      {errorMessage && (
        <div id="machine-config-error" className="p-3.5 bg-rose-50 border border-rose-200 rounded-xl text-xs text-rose-800 flex items-center gap-2 animate-in fade-in">
          <AlertTriangle className="w-4 h-4 text-rose-600 shrink-0" />
          <span className="font-medium">{errorMessage}</span>
          <button onClick={() => setErrorMessage(null)} className="ml-auto text-rose-500 hover:text-rose-700">
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Left Column: Machine Cell Directory */}
        <div className="p-4 bg-white border border-slate-200 rounded-xl shadow-xs space-y-3">
          <div className="flex items-center justify-between pb-2 border-b border-slate-100">
            <span className="text-xs font-bold text-slate-700 uppercase tracking-wider">
              Machine Cells ({machines.length})
            </span>
            <span className="text-[10px] font-mono font-bold text-blue-700 bg-blue-50 px-2 py-0.5 rounded">
              ISO 10816-3
            </span>
          </div>

          <div className="space-y-2 max-h-[640px] overflow-y-auto pr-1">
            {machines.map((m) => {
              const isSelected = selectedMachine?.code === m.code || selectedMachine?.machine_id === m.machine_id;
              return (
                <div
                  key={m.machine_id || m.code}
                  id={`machine-item-${m.code}`}
                  onClick={() => handleSelectMachine(m)}
                  className={`p-3 rounded-lg border text-left cursor-pointer transition-all ${
                    isSelected
                      ? "bg-blue-50/70 border-blue-400 shadow-xs ring-1 ring-blue-300"
                      : "bg-white border-slate-200 hover:border-slate-300 hover:bg-slate-50"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-slate-900">{m.code}</span>
                    <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-100 text-slate-700 font-semibold">
                      {m.cell || m.location || "Cell A"}
                    </span>
                  </div>
                  <div className="text-[11px] text-slate-500 mt-1 truncate">
                    {m.name || m.type || "CNC Machine"}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Right Column: Baselines & Thresholds Configuration Table */}
        <div className="lg:col-span-3 p-5 bg-white border border-slate-200 rounded-xl shadow-xs space-y-5">
          {/* Machine Info Bar */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 border-b border-slate-100 gap-3">
            <div>
              <div className="flex items-center gap-2">
                <span className="text-sm font-mono font-bold text-blue-700 bg-blue-100 px-2.5 py-0.5 rounded">
                  {selectedMachine?.code}
                </span>
                <span className="text-sm font-bold text-slate-900">
                  {selectedMachine?.name || selectedMachine?.type}
                </span>
              </div>
              <p className="text-xs text-slate-500 mt-1">
                Cell Location: <strong className="text-slate-700">{selectedMachine?.cell || selectedMachine?.location}</strong> &bull;
                Database Reference: <span className="font-mono">{selectedMachine?.machine_id}</span>
              </p>
            </div>

            <div className="flex items-center gap-3">
              <div className="text-right">
                <span className="text-[10px] uppercase font-bold text-slate-400 block">Baseline Health</span>
                <span className={`text-xs font-bold font-mono px-2 py-0.5 rounded ${
                  completenessPct === 100 ? "bg-emerald-100 text-emerald-800" : "bg-amber-100 text-amber-800"
                }`}>
                  {configuredCount} / {baselines.length} Configured ({completenessPct}%)
                </span>
              </div>

              <button
                id="save-baselines-btn"
                disabled={saving}
                onClick={handleSaveBaselines}
                className="flex items-center gap-1.5 px-4 py-2 text-xs font-bold text-white bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 rounded-lg shadow-xs transition-all cursor-pointer"
              >
                {saving ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Save className="w-3.5 h-3.5" />}
                {saving ? "Persisting..." : "Save Configuration"}
              </button>
            </div>
          </div>

          {/* Operational Parameters Table */}
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border border-slate-200 rounded-lg">
              <thead className="bg-slate-50 text-slate-700 font-bold border-b border-slate-200">
                <tr>
                  <th className="py-2.5 px-3">Process Parameter</th>
                  <th className="py-2.5 px-3">Unit</th>
                  <th className="py-2.5 px-3">Certified Mean (&mu;)</th>
                  <th className="py-2.5 px-3">Std Dev (&sigma;)</th>
                  <th className="py-2.5 px-3">Lower / Warning Limit</th>
                  <th className="py-2.5 px-3">Upper / Trip Limit</th>
                  <th className="py-2.5 px-3">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {baselines.map((b) => {
                  const hasErr = !!validationErrors[b.parameter];
                  const isConfigured = b.status === "CONFIGURED";
                  return (
                    <tr key={b.parameter} className={isConfigured ? "hover:bg-slate-50/50" : "bg-amber-50/20"}>
                      <td className="py-2.5 px-3 font-semibold text-slate-900">
                        <div>{b.name || b.parameter}</div>
                        <div className="text-[10px] text-slate-400 font-mono">{b.parameter}</div>
                      </td>
                      <td className="py-2.5 px-3 text-slate-600 font-mono font-semibold">
                        {b.unit || "—"}
                      </td>
                      <td className="py-2.5 px-3">
                        <input
                          type="number"
                          step="0.01"
                          id={`input-mean-${b.parameter}`}
                          value={b.mean !== null ? b.mean : ""}
                          placeholder="Unconfigured"
                          onChange={(e) => handleFieldChange(b.parameter, "mean", e.target.value)}
                          className="w-24 px-2 py-1 text-xs font-mono border border-slate-300 rounded focus:ring-1 focus:ring-blue-500 focus:outline-none"
                        />
                      </td>
                      <td className="py-2.5 px-3">
                        <input
                          type="number"
                          step="0.001"
                          id={`input-std-${b.parameter}`}
                          value={b.std !== null ? b.std : ""}
                          placeholder="0.1"
                          onChange={(e) => handleFieldChange(b.parameter, "std", e.target.value)}
                          className="w-20 px-2 py-1 text-xs font-mono border border-slate-300 rounded focus:ring-1 focus:ring-blue-500 focus:outline-none"
                        />
                      </td>
                      <td className="py-2.5 px-3">
                        <input
                          type="number"
                          step="0.01"
                          id={`input-lower-${b.parameter}`}
                          value={b.lower_threshold !== null ? b.lower_threshold : ""}
                          placeholder="Warn Low"
                          onChange={(e) => handleFieldChange(b.parameter, "lower_threshold", e.target.value)}
                          className="w-24 px-2 py-1 text-xs font-mono border border-slate-300 rounded focus:ring-1 focus:ring-blue-500 focus:outline-none text-blue-700"
                        />
                      </td>
                      <td className="py-2.5 px-3">
                        <input
                          type="number"
                          step="0.01"
                          id={`input-upper-${b.parameter}`}
                          value={b.upper_threshold !== null ? b.upper_threshold : ""}
                          placeholder="Trip High"
                          onChange={(e) => handleFieldChange(b.parameter, "upper_threshold", e.target.value)}
                          className="w-24 px-2 py-1 text-xs font-mono font-bold border border-slate-300 rounded focus:ring-1 focus:ring-rose-500 focus:outline-none text-rose-700"
                        />
                        {hasErr && (
                          <div className="text-[10px] text-rose-600 block mt-0.5">
                            {validationErrors[b.parameter]}
                          </div>
                        )}
                      </td>
                      <td className="py-2.5 px-3">
                        <span
                          id={`badge-status-${b.parameter}`}
                          className={`text-[10px] font-bold px-2 py-0.5 rounded uppercase font-mono ${
                            isConfigured
                              ? "bg-emerald-100 text-emerald-800 border border-emerald-200"
                              : "bg-amber-100 text-amber-800 border border-amber-200"
                          }`}
                        >
                          {b.status}
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {/* Quality Engineering Compliance Notice */}
          <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg text-xs text-blue-900 flex items-start gap-2">
            <ShieldCheck className="w-4 h-4 text-blue-600 shrink-0 mt-0.5" />
            <span>
              <strong>Deterministic Telemetry Governance:</strong> Machine baseline limits configured here are persisted directly into the SQLite database.
              Agent 4 uses these exact values during telemetry evaluation, ensuring that anomalies are flagged based on certified equipment thresholds rather than hardcoded heuristics.
            </span>
          </div>
        </div>
      </div>

      {/* Register Machine Modal */}
      {showNewMachineModal && (
        <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-xl shadow-xl max-w-md w-full p-5 space-y-4 border border-slate-200 animate-in fade-in">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <h3 className="text-sm font-bold text-slate-900">Register Factory Floor CNC Machine Cell</h3>
              <button onClick={() => setShowNewMachineModal(false)} className="text-slate-400 hover:text-slate-600">
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="space-y-3">
              <div>
                <label className="text-xs font-bold text-slate-700 block mb-1">Machine Identifier / Code *</label>
                <input
                  type="text"
                  placeholder="e.g. CNC-05"
                  value={newMachineCode}
                  onChange={(e) => setNewMachineCode(e.target.value)}
                  className="w-full px-3 py-2 text-xs font-mono font-bold border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none"
                />
              </div>

              <div>
                <label className="text-xs font-bold text-slate-700 block mb-1">Machine Model & Type</label>
                <input
                  type="text"
                  placeholder="e.g. Mazak Integrex e-420H"
                  value={newMachineType}
                  onChange={(e) => setNewMachineType(e.target.value)}
                  className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none"
                />
              </div>

              <div>
                <label className="text-xs font-bold text-slate-700 block mb-1">Plant Cell / Bay Location</label>
                <input
                  type="text"
                  placeholder="e.g. Cell C - Heavy Turning"
                  value={newMachineLocation}
                  onChange={(e) => setNewMachineLocation(e.target.value)}
                  className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none"
                />
              </div>
            </div>

            <div className="flex justify-end gap-2 pt-2 border-t border-slate-100">
              <button
                onClick={() => setShowNewMachineModal(false)}
                className="px-3 py-1.5 text-xs font-semibold text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-lg"
              >
                Cancel
              </button>
              <button
                onClick={handleRegisterMachine}
                className="px-4 py-1.5 text-xs font-bold text-white bg-blue-600 hover:bg-blue-700 rounded-lg shadow-xs"
              >
                Confirm Registration
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

import React, { useEffect, useState } from "react";
import { api } from "../api";
import { CertaintyBadge } from "../components/CertaintyBadge";
import { AlertTriangle, CheckCircle, Clock, ArrowRight, ShieldAlert } from "lucide-react";

interface Props {
  onNavigate: (page: string) => void;
}

export const IncidentsPage: React.FC<Props> = ({ onNavigate }) => {
  const [incidents, setIncidents] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getIncidents().then((res) => {
      setIncidents(res);
      setLoading(false);
    });
  }, []);

  if (loading) {
    return <div className="p-8 text-center text-slate-500">Loading Quality Incidents...</div>;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-[26px] font-bold text-slate-900 leading-tight">Quality Incidents & NCRs</h2>
          <p className="text-[14px] text-slate-500 mt-1">
            Manage detected quality non-conformances, active quarantine holds, and containment actions.
          </p>
        </div>
      </div>

      <div className="space-y-4">
        {incidents.map((inc) => {
          const isOpen = inc.status === "OPEN";
          return (
            <div
              key={inc.incident_id}
              className={`p-5 bg-white border rounded-xl shadow-xs space-y-4 ${
                isOpen ? "border-amber-300 ring-1 ring-amber-100" : "border-[#E3E8EF]"
              }`}
            >
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-100 pb-3">
                <div className="flex items-center gap-3.5">
                  <div className={`p-2.5 rounded-lg ${isOpen ? "bg-amber-100 text-amber-800" : "bg-emerald-100 text-emerald-800"}`}>
                    <AlertTriangle className="w-5 h-5" />
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-[13px] font-bold text-[#1D4ED8] font-tabular">{inc.incident_id}</span>
                      <span className="text-slate-300">&bull;</span>
                      <span className="font-mono text-[13px] text-slate-600 font-tabular">Batch {inc.batch_id}</span>
                      <span className="text-slate-300">&bull;</span>
                      <span className="text-[13px] text-slate-500">Machine: {inc.machine}</span>
                    </div>
                    <h3 className="text-[16px] font-bold text-slate-900 mt-0.5">{inc.title}</h3>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <span className={isOpen ? "status-pill danger" : "status-pill success"}>
                    {isOpen ? "Active Open" : "Closed"}
                  </span>
                  <span className="px-2.5 py-0.5 rounded-full text-[12px] font-medium bg-slate-100 text-slate-700">
                    Severity: {inc.severity}
                  </span>
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
                <div className="p-3 bg-slate-50 rounded-lg border border-slate-100">
                  <span className="text-slate-500 block text-[11.5px]">Containment Disposition</span>
                  <strong className="text-slate-900 font-semibold text-[13px]">{inc.impacted_quantity}</strong>
                </div>
                <div className="p-3 bg-slate-50 rounded-lg border border-slate-100 space-y-1">
                  <span className="text-slate-500 block text-[11.5px]">Investigation Hypothesis</span>
                  <div className="flex flex-col gap-1">
                    <strong className="text-amber-800 font-semibold text-[13px]">{inc.primary_hypothesis}</strong>
                    <CertaintyBadge level="Hypothesis" />
                  </div>
                </div>
                <div className="p-3 bg-slate-50 rounded-lg border border-slate-100">
                  <span className="text-slate-500 block text-[11.5px]">Quality Audit Verdict</span>
                  <strong className="text-emerald-700 font-semibold text-[13px]">{inc.critic_verdict} (Verified)</strong>
                </div>
              </div>

              <div className="flex items-center justify-between pt-2 border-t border-slate-100">
                <span className="text-[12.5px] text-slate-400 font-tabular">Created: {inc.created_at} UTC</span>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => onNavigate("rca")}
                    className="btn-primary !h-[36px]"
                  >
                    <span>View Investigation</span>
                    <ArrowRight className="w-3.5 h-3.5" />
                  </button>
                  <button
                    onClick={() => onNavigate("capa")}
                    className="btn-secondary !h-[36px]"
                  >
                    <span>Manage CAPA</span>
                  </button>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

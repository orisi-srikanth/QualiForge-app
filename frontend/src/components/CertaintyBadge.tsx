import React, { useState } from "react";
import { CertaintyLevel } from "../types";
import { CheckCircle2, Eye, LineChart, HelpCircle, ShieldCheck, Info, X } from "lucide-react";

interface Props {
  level: CertaintyLevel | string;
  className?: string;
  showIcon?: boolean;
  requiresVerification?: boolean;
  confirmedBy?: string;
  confirmedAt?: string;
}

export const CertaintyBadge: React.FC<Props> = ({
  level,
  className = "",
  showIcon = true,
  requiresVerification,
  confirmedBy,
  confirmedAt,
}) => {
  // Determine if this item requires engineering verification
  const isUnconfirmed =
    requiresVerification !== undefined
      ? requiresVerification
      : level === "Hypothesis" || level === "Model Prediction";

  const renderBadge = () => {
    switch (level) {
      case "Observed Fact":
        return (
          <span
            title="Observed Fact: Verified direct measurements from physical sensors or calibrated gauges."
            className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-slate-100 text-slate-800 border border-slate-300 ${className}`}
          >
            {showIcon && <CheckCircle2 className="w-3 h-3 text-slate-600" />}
            <span>Observed Fact</span>
          </span>
        );
      case "Model Prediction":
        return (
          <span
            title="Model Prediction: Output from computer vision or machine learning inference models. Requires engineering verification."
            className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-purple-50 text-purple-800 border border-purple-200 ${className}`}
          >
            {showIcon && <Eye className="w-3 h-3 text-purple-600" />}
            <span>Model Prediction</span>
          </span>
        );
      case "Statistical Finding":
        return (
          <span
            title="Statistical Finding: Derived from statistical process control limits, Nelson rules, capability indices, or hypothesis tests."
            className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-blue-50 text-blue-800 border border-blue-200 ${className}`}
          >
            {showIcon && <LineChart className="w-3 h-3 text-blue-600" />}
            <span>Statistical Finding</span>
          </span>
        );
      case "Hypothesis":
        return (
          <span
            title="Hypothesis: Root-cause theory proposed by multi-agent investigation. Requires engineering verification."
            className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-amber-50 text-amber-800 border border-amber-300 ${className}`}
          >
            {showIcon && <HelpCircle className="w-3 h-3 text-amber-600" />}
            <span>Hypothesis</span>
          </span>
        );
      case "Confirmed Root Cause":
        return (
          <span
            title={`Confirmed Root Cause: Verified by authorized quality engineering investigation${confirmedBy ? ` (${confirmedBy})` : ""}.`}
            className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-semibold bg-emerald-50 text-emerald-800 border border-emerald-300 ${className}`}
          >
            {showIcon && <ShieldCheck className="w-3 h-3 text-emerald-600" />}
            <span>Confirmed Root Cause</span>
          </span>
        );
      default:
        return (
          <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-700 ${className}`}>
            {level}
          </span>
        );
    }
  };

  return (
    <div className="inline-flex flex-col items-start gap-0.5">
      <div className="inline-flex items-center gap-1.5">
        {renderBadge()}
        {level === "Confirmed Root Cause" && (confirmedBy || confirmedAt) && (
          <span className="text-[10px] text-emerald-700 font-medium">
            (by {confirmedBy || "Quality Engineer"}{confirmedAt ? ` on ${confirmedAt}` : ""})
          </span>
        )}
      </div>
      {isUnconfirmed && (
        <span className="text-[10px] text-amber-700 font-medium tracking-tight">
          Requires engineering verification
        </span>
      )}
    </div>
  );
};

export const WhatDoTheseLabelsMeanPopover: React.FC = () => {
  return null;
};

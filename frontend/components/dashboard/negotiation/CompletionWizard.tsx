"use client";

import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  CheckCircle, FileText, Download, FileOutput, X, Loader2,
  TrendingDown, BarChart3, Award, Sparkles,
} from "lucide-react";

// ── Types ────────────────────────────────────────────────────────

interface CompletionWizardProps {
  isOpen: boolean;
  onClose: () => void;
  sessionId: string;
  contractTitle: string;
  totalFindings: number;
  resolvedCount: number;
  riskBefore?: number;
  riskAfter?: number;
  onGenerateSummary: () => Promise<void>;
  onGenerateReport: () => Promise<void>;
  onExportContract: () => Promise<void>;
  onCloseSession: () => Promise<void>;
}

// ── Component ────────────────────────────────────────────────────

export function CompletionWizard({
  isOpen,
  onClose,
  contractTitle,
  totalFindings,
  resolvedCount,
  riskBefore,
  riskAfter,
  onGenerateSummary,
  onGenerateReport,
  onExportContract,
  onCloseSession,
}: CompletionWizardProps) {
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  if (!isOpen) return null;

  const riskReduced = riskBefore && riskAfter ? riskBefore - riskAfter : null;
  const riskPct = riskReduced && riskBefore ? Math.round((riskReduced / riskBefore) * 100) : null;

  const actions = [
    {
      id: "summary",
      label: "Generate Executive Summary",
      icon: <FileText className="w-4 h-4" />,
      color: "bg-blue-500 hover:bg-blue-600",
      action: onGenerateSummary,
    },
    {
      id: "report",
      label: "Generate Final Report",
      icon: <BarChart3 className="w-4 h-4" />,
      color: "bg-purple-500 hover:bg-purple-600",
      action: onGenerateReport,
    },
    {
      id: "export",
      label: "Export Negotiated Contract",
      icon: <Download className="w-4 h-4" />,
      color: "bg-emerald-500 hover:bg-emerald-600",
      action: onExportContract,
    },
    {
      id: "close",
      label: "Close Session",
      icon: <FileOutput className="w-4 h-4" />,
      color: "bg-navy-600 hover:bg-navy-700",
      action: onCloseSession,
    },
  ];

  const handleAction = async (id: string, action: () => Promise<void>) => {
    setActionLoading(id);
    try {
      await action();
    } catch { /* ignore */ }
    setActionLoading(null);
  };

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm"
        onClick={onClose}
      >
        <motion.div
          initial={{ scale: 0.9, opacity: 0, y: 20 }}
          animate={{ scale: 1, opacity: 1, y: 0 }}
          exit={{ scale: 0.9, opacity: 0, y: 20 }}
          onClick={(e) => e.stopPropagation()}
          className="bg-white rounded-2xl shadow-2xl max-w-lg w-full mx-4 overflow-hidden"
        >
          {/* Header */}
          <div className="bg-gradient-to-r from-emerald-500 to-emerald-600 px-6 py-5 text-white">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <CheckCircle className="w-6 h-6" />
                <h2 className="text-lg font-bold">Review Complete</h2>
              </div>
              <button onClick={onClose} className="text-white/80 hover:text-white transition-colors">
                <X className="w-5 h-5" />
              </button>
            </div>
            <p className="text-sm text-emerald-100 mt-1">{contractTitle}</p>
          </div>

          {/* Stats */}
          <div className="px-6 py-4 bg-gray-50 border-b border-gray-100">
            <div className="grid grid-cols-3 gap-3">
              <div className="text-center">
                <p className="text-2xl font-bold text-navy-900">{resolvedCount}/{totalFindings}</p>
                <p className="text-[10px] text-gray-500">Findings Closed</p>
              </div>
              <div className="text-center">
                <p className="text-2xl font-bold text-emerald-600">
                  {riskPct !== null ? `-${riskPct}%` : "—"}
                </p>
                <p className="text-[10px] text-gray-500">Risk Reduced</p>
              </div>
              <div className="text-center">
                <p className="text-2xl font-bold text-amber-600">
                  {totalFindings > 0 ? Math.round((resolvedCount / totalFindings) * 100) : 0}%
                </p>
                <p className="text-[10px] text-gray-500">Complete</p>
              </div>
            </div>
            {/* Risk bar */}
            {riskBefore && riskAfter && (
              <div className="mt-3 pt-3 border-t border-gray-200">
                <div className="flex items-center justify-between text-[10px] text-gray-500 mb-1">
                  <span>Risk Score</span>
                  <span className="flex items-center gap-1">
                    <TrendingDown className="w-3 h-3 text-emerald-500" />
                    {riskBefore} → {riskAfter}
                  </span>
                </div>
                <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
                  <motion.div
                    initial={{ width: `${riskBefore}%` }}
                    animate={{ width: `${riskAfter}%` }}
                    transition={{ duration: 1, ease: "easeOut" }}
                    className="h-full bg-gradient-to-r from-red-500 via-amber-500 to-green-500 rounded-full"
                  />
                </div>
              </div>
            )}
          </div>

          {/* Actions */}
          <div className="px-6 py-4 space-y-2">
            <p className="text-[10px] font-semibold text-gray-500 uppercase tracking-wider">Next Steps</p>
            {actions.map((action) => (
              <button
                key={action.id}
                onClick={() => handleAction(action.id, action.action)}
                disabled={actionLoading !== null}
                className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium text-white transition-all ${action.color} disabled:opacity-60`}
              >
                {actionLoading === action.id ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  action.icon
                )}
                <span>{actionLoading === action.id ? "Processing..." : action.label}</span>
                {actionLoading !== action.id && (
                  <Sparkles className="w-3.5 h-3.5 ml-auto opacity-60" />
                )}
              </button>
            ))}
          </div>

          {/* Footer */}
          <div className="px-6 py-3 bg-gray-50 border-t border-gray-100 flex items-center justify-between">
            <div className="flex items-center gap-1.5 text-[10px] text-gray-400">
              <Award className="w-3 h-3" />
              <span>All findings resolved</span>
            </div>
            <button onClick={onClose} className="text-[10px] text-gray-500 hover:text-gray-700">
              Close
            </button>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}

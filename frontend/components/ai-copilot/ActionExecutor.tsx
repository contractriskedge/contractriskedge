"use client";

import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Zap, CheckCircle, AlertTriangle, Loader2, X, FileText, Calendar, Download, UserCheck, Workflow } from "lucide-react";
import type { AiSuggestedAction } from "./types";

interface ActionExecutorProps {
  action: AiSuggestedAction | null;
  onConfirm: (action: AiSuggestedAction) => void;
  onCancel: () => void;
  onComplete: () => void;
}

export function ActionExecutor({ action, onConfirm, onCancel, onComplete }: ActionExecutorProps) {
  const [executing, setExecuting] = useState(false);
  const [completed, setCompleted] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!action) return null;

  const handleExecute = async () => {
    setExecuting(true);
    setError(null);
    try {
      // Simulate execution
      await new Promise((r) => setTimeout(r, 1500));
      setCompleted(true);
      setExecuting(false);
      setTimeout(() => {
        onComplete();
      }, 2000);
    } catch (err: any) {
      setError(err.message || "Execution failed");
      setExecuting(false);
    }
  };

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: 20 }}
        className="fixed bottom-24 right-6 z-50 w-80 bg-white rounded-xl border border-gray-200 shadow-2xl overflow-hidden"
      >
        <div className="px-4 py-3 bg-navy-700 text-white flex items-center gap-2">
          <Zap className="w-4 h-4" />
          <span className="text-xs font-semibold">Execute Action</span>
          <button onClick={onCancel} className="ml-auto p-0.5 rounded hover:bg-navy-600 transition-colors">
            <X className="w-3.5 h-3.5" />
          </button>
        </div>

        <div className="p-4 space-y-3">
          {completed ? (
            <div className="text-center py-4">
              <div className="w-12 h-12 rounded-full bg-green-100 flex items-center justify-center mx-auto mb-2">
                <CheckCircle className="w-6 h-6 text-green-600" />
              </div>
              <p className="text-sm font-semibold text-navy-900">Action Completed</p>
              <p className="text-xs text-gray-500 mt-0.5">{action.label} was executed successfully</p>
            </div>
          ) : (
            <>
              <div className="flex items-start gap-2.5">
                <div className="w-8 h-8 rounded-lg bg-navy-50 flex items-center justify-center flex-shrink-0">
                  <ActionIcon icon={action.icon} />
                </div>
                <div>
                  <h4 className="text-xs font-semibold text-navy-900">{action.label}</h4>
                  <p className="text-[11px] text-gray-500 mt-0.5">{action.description}</p>
                </div>
              </div>

              {action.requiresConfirmation && (
                <div className="p-2.5 bg-amber-50 rounded-lg border border-amber-100 flex items-start gap-1.5">
                  <AlertTriangle className="w-3.5 h-3.5 text-amber-500 mt-0.5 flex-shrink-0" />
                  <p className="text-[10px] text-amber-800">This action requires your confirmation before execution. Please review the details.</p>
                </div>
              )}

              {error && (
                <div className="p-2 bg-red-50 rounded border border-red-100 text-[10px] text-red-700">
                  {error}
                </div>
              )}

              <div className="flex gap-2">
                <button
                  onClick={onCancel}
                  disabled={executing}
                  className="flex-1 text-xs font-medium px-3 py-1.5 rounded-lg bg-white border border-gray-200 text-gray-600 hover:bg-gray-50 transition-colors disabled:opacity-50"
                >
                  Cancel
                </button>
                <button
                  onClick={handleExecute}
                  disabled={executing}
                  className="flex-1 text-xs font-medium px-3 py-1.5 rounded-lg bg-navy-700 text-white hover:bg-navy-800 transition-colors disabled:opacity-50 flex items-center justify-center gap-1"
                >
                  {executing ? (
                    <><Loader2 className="w-3.5 h-3.5 animate-spin" /> Executing...</>
                  ) : (
                    <><Zap className="w-3.5 h-3.5" /> {action.requiresConfirmation ? "Confirm & Execute" : "Execute"}</>
                  )}
                </button>
              </div>
            </>
          )}
        </div>
      </motion.div>
    </AnimatePresence>
  );
}

function ActionIcon({ icon }: { icon: string }) {
  switch (icon) {
    case "FileText": return <FileText className="w-4 h-4 text-navy-600" />;
    case "Calendar": return <Calendar className="w-4 h-4 text-navy-600" />;
    case "Download": return <Download className="w-4 h-4 text-navy-600" />;
    case "UserCheck": return <UserCheck className="w-4 h-4 text-navy-600" />;
    case "Workflow": return <Workflow className="w-4 h-4 text-navy-600" />;
    default: return <Zap className="w-4 h-4 text-navy-600" />;
  }
}

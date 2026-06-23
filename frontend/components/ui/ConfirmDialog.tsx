"use client";

import React from "react";
import { motion, AnimatePresence } from "framer-motion";
import { AlertTriangle, X } from "lucide-react";

interface ConfirmDialogProps {
  isOpen: boolean;
  title: string;
  message: string;
  confirmLabel?: string;
  cancelLabel?: string;
  variant?: "danger" | "warning" | "info";
  onConfirm: () => void;
  onCancel: () => void;
}

export function ConfirmDialog({
  isOpen, title, message, confirmLabel = "Confirm", cancelLabel = "Cancel",
  variant = "danger", onConfirm, onCancel,
}: ConfirmDialogProps) {
  const colors = {
    danger: { bg: "bg-red-50 border-red-200", button: "bg-red-600 hover:bg-red-700", icon: "text-red-500" },
    warning: { bg: "bg-amber-50 border-amber-200", button: "bg-amber-600 hover:bg-amber-700", icon: "text-amber-500" },
    info: { bg: "bg-blue-50 border-blue-200", button: "bg-blue-600 hover:bg-blue-700", icon: "text-blue-500" },
  };
  const c = colors[variant];

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/30 z-[60]"
            onClick={onCancel}
          />
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            className="fixed inset-0 z-[60] flex items-center justify-center p-4"
            onClick={(e) => e.stopPropagation()}
          >
            <div className={`bg-white rounded-xl shadow-2xl border-2 w-full max-w-sm ${c.bg}`}>
              <div className="px-5 py-4 flex items-start gap-3">
                <div className={`p-1.5 rounded-full bg-white ${c.icon}`}>
                  <AlertTriangle className="w-5 h-5" />
                </div>
                <div className="flex-1 min-w-0">
                  <h3 className="text-sm font-semibold text-navy-900">{title}</h3>
                  <p className="text-[11px] text-gray-600 mt-1">{message}</p>
                </div>
                <button onClick={onCancel} className="p-0.5 hover:bg-gray-100 rounded text-gray-400">
                  <X className="w-3.5 h-3.5" />
                </button>
              </div>
              <div className="px-5 pb-4 flex items-center gap-2 justify-end">
                <button onClick={onCancel}
                  className="px-3 py-1.5 border border-gray-200 rounded-lg text-[10px] font-medium text-gray-600 hover:bg-gray-50 transition-colors"
                >
                  {cancelLabel}
                </button>
                <button onClick={onConfirm}
                  className={`px-3 py-1.5 text-white rounded-lg text-[10px] font-medium transition-colors ${c.button}`}
                >
                  {confirmLabel}
                </button>
              </div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}

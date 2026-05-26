/**
 * ActionFramework — unified action execution system for analytics-driven operations.
 *
 * Transforms read-only insights into actionable workflows:
 * - Assign reviewer to contract
 * - Escalate high-risk finding
 * - Bulk re-analyze contracts
 * - Export affected contracts list
 * - Notify legal owner
 * - Create remediation task
 *
 * Each action defines:
 * - id: unique identifier
 * - label: display name
 * - icon: Lucide icon
 * - permissions: required role
 * - confirmation: show confirmation dialog
 * - handler: async execution function
 */

"use client";

import React, { useState, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  UserPlus, AlertTriangle, RefreshCw, Download, Bell, CheckCircle,
  ArrowUpRight, Loader2, X, Send,
} from "lucide-react";

// ── Action Definition ────────────────────────────────────────────

export interface ActionDefinition {
  id: string;
  label: string;
  description?: string;
  icon: React.ReactNode;
  permissions: string[];
  confirmation?: string; // If set, shows confirmation dialog
  handler: (context: ActionContext) => Promise<ActionResult>;
}

export interface ActionContext {
  type: "contract" | "finding" | "review" | "clause" | "batch";
  ids: string[];
  metadata?: Record<string, unknown>;
}

export interface ActionResult {
  success: boolean;
  message: string;
  affectedIds?: string[];
}

// ── Action Registry ──────────────────────────────────────────────

const actionRegistry = new Map<string, ActionDefinition>();

export function registerAction(action: ActionDefinition): void {
  actionRegistry.set(action.id, action);
}

export function getAction(id: string): ActionDefinition | undefined {
  return actionRegistry.get(id);
}

export function getActionsForContext(
  contextType: ActionContext["type"],
  userRole: string,
): ActionDefinition[] {
  const actions: ActionDefinition[] = [];
  for (const action of actionRegistry.values()) {
    if (action.permissions.includes(userRole) || userRole === "admin") {
      actions.push(action);
    }
  }
  return actions;
}

// ── Built-in Actions ─────────────────────────────────────────────

// These are registered on import
registerAction({
  id: "assign_reviewer",
  label: "Assign Reviewer",
  description: "Assign a reviewer to this contract",
  icon: <UserPlus className="w-3.5 h-3.5" />,
  permissions: ["admin", "analyst"],
  confirmation: "Assign a reviewer to the selected items?",
  handler: async (ctx) => {
    // In production, this would call the API
    return { success: true, message: `Reviewer assigned to ${ctx.ids.length} item(s)`, affectedIds: ctx.ids };
  },
});

registerAction({
  id: "escalate",
  label: "Escalate",
  description: "Escalate high-risk finding to senior reviewer",
  icon: <AlertTriangle className="w-3.5 h-3.5" />,
  permissions: ["admin", "analyst"],
  confirmation: "Escalate this item to senior review?",
  handler: async (ctx) => {
    return { success: true, message: `Escalated ${ctx.ids.length} item(s)` };
  },
});

registerAction({
  id: "re_analyze",
  label: "Re-analyze",
  description: "Re-run AI analysis on selected contracts",
  icon: <RefreshCw className="w-3.5 h-3.5" />,
  permissions: ["admin"],
  confirmation: "Re-analyze selected contracts? This may incur AI costs.",
  handler: async (ctx) => {
    return { success: true, message: `Re-analysis queued for ${ctx.ids.length} contract(s)` };
  },
});

registerAction({
  id: "export_csv",
  label: "Export CSV",
  description: "Export selected items as CSV",
  icon: <Download className="w-3.5 h-3.5" />,
  permissions: ["admin", "analyst", "viewer"],
  handler: async (ctx) => {
    return { success: true, message: `Exported ${ctx.ids.length} item(s)` };
  },
});

registerAction({
  id: "notify_owner",
  label: "Notify Owner",
  description: "Send notification to contract owner",
  icon: <Bell className="w-3.5 h-3.5" />,
  permissions: ["admin", "analyst"],
  confirmation: "Send notification to the contract owner?",
  handler: async (ctx) => {
    return { success: true, message: `Notification sent for ${ctx.ids.length} item(s)` };
  },
});

// ── Action Button Component ──────────────────────────────────────

interface ActionButtonProps {
  action: ActionDefinition;
  context: ActionContext;
  onComplete?: (result: ActionResult) => void;
  size?: "sm" | "md";
}

export function ActionButton({ action, context, onComplete, size = "sm" }: ActionButtonProps) {
  const [loading, setLoading] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const [result, setResult] = useState<ActionResult | null>(null);

  const handleExecute = useCallback(async () => {
    if (action.confirmation && !showConfirm) {
      setShowConfirm(true);
      return;
    }
    setShowConfirm(false);
    setLoading(true);
    setResult(null);
    try {
      const res = await action.handler(context);
      setResult(res);
      onComplete?.(res);
    } catch (err) {
      setResult({ success: false, message: err instanceof Error ? err.message : "Action failed" });
    }
    setLoading(false);
    setTimeout(() => setResult(null), 3000);
  }, [action, context, onComplete, showConfirm]);

  const sizeClasses = size === "sm" ? "px-2.5 py-1.5 text-xs" : "px-3 py-2 text-sm";

  return (
    <div className="relative">
      <button
        onClick={handleExecute}
        disabled={loading}
        className={`inline-flex items-center gap-1.5 rounded-lg font-medium transition-colors ${sizeClasses} ${
          action.id === "escalate"
            ? "bg-red-100 text-red-700 hover:bg-red-200"
            : action.id === "re_analyze"
              ? "bg-amber-100 text-amber-700 hover:bg-amber-200"
              : "bg-gray-100 text-gray-700 hover:bg-gray-200"
        } disabled:opacity-50`}
      >
        {loading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : action.icon}
        {action.label}
      </button>

      {/* Confirmation dialog */}
      <AnimatePresence>
        {showConfirm && (
          <motion.div
            initial={{ opacity: 0, y: -4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -4 }}
            className="absolute left-0 top-full mt-1 bg-white border border-gray-200 rounded-lg shadow-lg z-30 p-3 w-64"
          >
            <p className="text-xs text-gray-700 mb-2">{action.confirmation}</p>
            <div className="flex items-center gap-2">
              <button
                onClick={handleExecute}
                className="px-3 py-1.5 text-xs font-medium rounded-lg bg-navy-700 text-white hover:bg-navy-800"
              >
                Confirm
              </button>
              <button
                onClick={() => setShowConfirm(false)}
                className="px-3 py-1.5 text-xs font-medium rounded-lg border border-gray-200 text-gray-600 hover:bg-gray-50"
              >
                Cancel
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Result toast */}
      <AnimatePresence>
        {result && (
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 8 }}
            className={`absolute right-0 top-full mt-1 px-3 py-2 rounded-lg text-xs font-medium shadow-lg whitespace-nowrap ${
              result.success ? "bg-green-50 text-green-700 border border-green-200" : "bg-red-50 text-red-700 border border-red-200"
            }`}
          >
            <div className="flex items-center gap-1.5">
              {result.success ? <CheckCircle className="w-3.5 h-3.5" /> : <X className="w-3.5 h-3.5" />}
              {result.message}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

// ── Action Bar Component ─────────────────────────────────────────

interface ActionBarProps {
  contextType: ActionContext["type"];
  selectedIds: string[];
  userRole: string;
  contextMetadata?: Record<string, unknown>;
}

export function ActionBar({ contextType, selectedIds, userRole, contextMetadata }: ActionBarProps) {
  const actions = getActionsForContext(contextType, userRole);
  if (actions.length === 0 || selectedIds.length === 0) return null;

  return (
    <div className="flex items-center gap-2 px-3 py-2 bg-gray-50 rounded-lg border border-gray-200">
      <span className="text-[10px] font-medium text-gray-500 uppercase tracking-wider mr-1">
        Actions ({selectedIds.length})
      </span>
      {actions.map((action) => (
        <ActionButton
          key={action.id}
          action={action}
          context={{ type: contextType, ids: selectedIds, metadata: contextMetadata }}
        />
      ))}
    </div>
  );
}

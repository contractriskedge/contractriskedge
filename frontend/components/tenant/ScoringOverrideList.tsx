/**
 * ScoringOverrideList — Manage scoring overrides (list, create, delete).
 */

"use client";

import React, { useState } from "react";
import { motion } from "framer-motion";
import {
  Plus, Trash2, Loader2, AlertCircle, RefreshCw,
  CheckCircle2, XCircle, Gauge,
} from "lucide-react";
import {
  useScoringOverrides,
  useCreateScoringOverride,
  useDeleteScoringOverride,
} from "@/services/hooks/useTenantModules";

export function ScoringOverrideList() {
  const { data: overrides, isLoading, error, refetch } = useScoringOverrides();
  const createOverride = useCreateScoringOverride();
  const deleteOverride = useDeleteScoringOverride();
  const [showForm, setShowForm] = useState(false);
  const [clauseType, setClauseType] = useState("");
  const [severity, setSeverity] = useState("high");
  const [weight, setWeight] = useState("1.0");
  const [score, setScore] = useState("0.5");
  const [feedback, setFeedback] = useState<{ type: "success" | "error"; message: string } | null>(null);

  const showFeedback = (type: "success" | "error", message: string) => {
    setFeedback({ type, message });
    setTimeout(() => setFeedback(null), 3000);
  };

  const handleCreate = () => {
    if (!clauseType.trim()) return;
    createOverride.mutate(
      {
        clause_type: clauseType.trim(),
        override_severity: severity,
        override_risk_weight: parseFloat(weight) || 1.0,
        override_risk_score: parseFloat(score) || 0.5,
        is_active: true,
        reason: "Created via Settings UI",
      },
      {
        onSuccess: () => {
          showFeedback("success", `Override for "${clauseType}" created`);
          setClauseType(""); setShowForm(false);
        },
        onError: (err) => showFeedback("error", `Failed to create: ${(err as Error).message}`),
      },
    );
  };

  const handleDelete = (id: string, clause: string) => {
    if (!confirm(`Delete scoring override for "${clause}"?`)) return;
    deleteOverride.mutate(id, {
      onSuccess: () => showFeedback("success", `Override for "${clause}" deleted`),
      onError: (err) => showFeedback("error", `Failed to delete: ${(err as Error).message}`),
    });
  };

  if (isLoading) return <div className="flex justify-center py-12"><Loader2 className="w-6 h-6 text-gold-400 animate-spin" /></div>;
  if (error) return (
    <div className="text-center py-12">
      <AlertCircle className="w-8 h-8 text-red-400 mx-auto mb-2" />
      <p className="text-sm text-gray-500 mb-2">Failed to load scoring overrides</p>
      <button onClick={() => refetch()} className="text-xs text-gold-600 inline-flex items-center gap-1"><RefreshCw className="w-3 h-3" /> Retry</button>
    </div>
  );

  return (
    <div className="space-y-4">
      {feedback && (
        <motion.div initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }}
          className={`flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium border ${
            feedback.type === "success" ? "bg-emerald-50 text-emerald-700 border-emerald-200" : "bg-red-50 text-red-700 border-red-200"
          }`}
        >
          {feedback.type === "success" ? <CheckCircle2 className="w-4 h-4" /> : <XCircle className="w-4 h-4" />}
          {feedback.message}
        </motion.div>
      )}

      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-gray-900">Scoring Overrides ({overrides?.length ?? 0})</h3>
        <button onClick={() => setShowForm(!showForm)}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg bg-navy-700 text-white hover:bg-navy-800"
        ><Plus className="w-3.5 h-3.5" /> New Override</button>
      </div>

      {showForm && (
        <motion.div initial={{ opacity: 0, y: -4 }} animate={{ opacity: 1, y: 0 }}
          className="p-4 rounded-lg border border-gray-200 bg-gray-50 space-y-3"
        >
          <input value={clauseType} onChange={(e) => setClauseType(e.target.value)} placeholder="Clause type * (e.g., liability, indemnification)"
            className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-gold-400" />
          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="block text-xs text-gray-500 mb-1">Severity</label>
              <select value={severity} onChange={(e) => setSeverity(e.target.value)}
                className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-gold-400"
              ><option value="critical">Critical</option><option value="high">High</option><option value="medium">Medium</option><option value="low">Low</option></select>
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">Risk Weight (0-2)</label>
              <input type="number" step="0.1" min="0" max="2" value={weight} onChange={(e) => setWeight(e.target.value)}
                className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-gold-400" />
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">Risk Score (0-1)</label>
              <input type="number" step="0.05" min="0" max="1" value={score} onChange={(e) => setScore(e.target.value)}
                className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-gold-400" />
            </div>
          </div>
          <div className="flex gap-2">
            <button onClick={handleCreate} disabled={!clauseType.trim() || createOverride.isPending}
              className="px-3 py-1.5 text-xs font-medium rounded-lg bg-navy-700 text-white hover:bg-navy-800 disabled:bg-gray-300 disabled:cursor-not-allowed"
            >{createOverride.isPending ? "Creating..." : "Create"}</button>
            <button onClick={() => setShowForm(false)} className="px-3 py-1.5 text-xs font-medium rounded-lg bg-white border border-gray-200 text-gray-600 hover:bg-gray-50">Cancel</button>
          </div>
        </motion.div>
      )}

      {(!overrides || overrides.length === 0) && !showForm ? (
        <div className="text-center py-12 border-2 border-dashed border-gray-200 rounded-lg">
          <Gauge className="w-8 h-8 text-gray-300 mx-auto mb-2" />
          <p className="text-sm text-gray-500">No scoring overrides yet</p>
          <button onClick={() => setShowForm(true)} className="mt-2 text-xs text-gold-600 hover:text-gold-700">Create your first override</button>
        </div>
      ) : (
        <div className="space-y-2">
          {overrides?.map((o) => (
            <motion.div key={o.override_id} initial={{ opacity: 0 }} animate={{ opacity: 1 }}
              className="flex items-start gap-3 p-3 rounded-lg border border-gray-200 bg-white"
            >
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium text-gray-900">{o.clause_type}</span>
                  <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${
                    o.override_severity === "critical" ? "bg-red-50 text-red-700" :
                    o.override_severity === "high" ? "bg-orange-50 text-orange-700" :
                    "bg-amber-50 text-amber-700"
                  }`}>{o.override_severity}</span>
                </div>
                <p className="text-xs text-gray-500 mt-0.5">
                  Weight: {o.override_risk_weight?.toFixed(2)} | Score: {o.override_risk_score?.toFixed(3)}
                  {o.applies_to_business_units?.length ? ` | BUs: ${o.applies_to_business_units.join(", ")}` : ""}
                </p>
                {o.reason && <p className="text-xs text-gray-400 mt-0.5">{o.reason}</p>}
              </div>
              <button onClick={() => handleDelete(o.override_id, o.clause_type)}
                className="p-1.5 text-gray-400 hover:text-red-500 transition-colors" title="Delete override"
              ><Trash2 className="w-4 h-4" /></button>
            </motion.div>
          ))}
        </div>
      )}
    </div>
  );
}

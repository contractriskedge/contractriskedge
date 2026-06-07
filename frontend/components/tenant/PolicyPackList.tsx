/**
 * PolicyPackList — Manage policy packs (list, create, delete).
 */

"use client";

import React, { useState } from "react";
import { motion } from "framer-motion";
import {
  Plus, Trash2, Loader2, AlertCircle, RefreshCw,
  CheckCircle2, XCircle, Package,
} from "lucide-react";
import {
  usePolicyPacks,
  useCreatePolicyPack,
  useDeletePolicyPack,
} from "@/services/hooks/useTenantModules";

export function PolicyPackList() {
  const { data: packs, isLoading, error, refetch } = usePolicyPacks();
  const createPack = useCreatePolicyPack();
  const deletePack = useDeletePolicyPack();
  const [showForm, setShowForm] = useState(false);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [feedback, setFeedback] = useState<{ type: "success" | "error"; message: string } | null>(null);

  const showFeedback = (type: "success" | "error", message: string) => {
    setFeedback({ type, message });
    setTimeout(() => setFeedback(null), 3000);
  };

  const handleCreate = () => {
    if (!name.trim()) return;
    createPack.mutate(
      { name: name.trim(), description: description.trim() || null, scope: "tenant" },
      {
        onSuccess: () => {
          showFeedback("success", `Policy pack "${name}" created`);
          setName(""); setDescription(""); setShowForm(false);
        },
        onError: (err) => showFeedback("error", `Failed to create: ${(err as Error).message}`),
      },
    );
  };

  const handleDelete = (packId: string, packName: string) => {
    if (!confirm(`Delete policy pack "${packName}"?`)) return;
    deletePack.mutate(packId, {
      onSuccess: () => showFeedback("success", `Policy pack "${packName}" deleted`),
      onError: (err) => showFeedback("error", `Failed to delete: ${(err as Error).message}`),
    });
  };

  if (isLoading) return <div className="flex justify-center py-12"><Loader2 className="w-6 h-6 text-gold-400 animate-spin" /></div>;
  if (error) return (
    <div className="text-center py-12">
      <AlertCircle className="w-8 h-8 text-red-400 mx-auto mb-2" />
      <p className="text-sm text-gray-500 mb-2">Failed to load policy packs</p>
      <button onClick={() => refetch()} className="text-xs text-gold-600 hover:text-gold-700 inline-flex items-center gap-1"><RefreshCw className="w-3 h-3" /> Retry</button>
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
        <h3 className="text-sm font-semibold text-gray-900">Policy Packs ({packs?.length ?? 0})</h3>
        <button onClick={() => setShowForm(!showForm)}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg bg-navy-700 text-white hover:bg-navy-800 transition-colors"
        ><Plus className="w-3.5 h-3.5" /> New Pack</button>
      </div>

      {showForm && (
        <motion.div initial={{ opacity: 0, y: -4 }} animate={{ opacity: 1, y: 0 }}
          className="p-4 rounded-lg border border-gray-200 bg-gray-50 space-y-3"
        >
          <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Pack name *"
            className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-gold-400" />
          <textarea value={description} onChange={(e) => setDescription(e.target.value)} placeholder="Description (optional)"
            className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-gold-400" rows={2} />
          <div className="flex gap-2">
            <button onClick={handleCreate} disabled={!name.trim() || createPack.isPending}
              className="px-3 py-1.5 text-xs font-medium rounded-lg bg-navy-700 text-white hover:bg-navy-800 disabled:bg-gray-300 disabled:cursor-not-allowed"
            >{createPack.isPending ? "Creating..." : "Create"}</button>
            <button onClick={() => setShowForm(false)} className="px-3 py-1.5 text-xs font-medium rounded-lg bg-white border border-gray-200 text-gray-600 hover:bg-gray-50">Cancel</button>
          </div>
        </motion.div>
      )}

      {(!packs || packs.length === 0) && !showForm ? (
        <div className="text-center py-12 border-2 border-dashed border-gray-200 rounded-lg">
          <Package className="w-8 h-8 text-gray-300 mx-auto mb-2" />
          <p className="text-sm text-gray-500">No policy packs yet</p>
          <button onClick={() => setShowForm(true)} className="mt-2 text-xs text-gold-600 hover:text-gold-700">Create your first pack</button>
        </div>
      ) : (
        <div className="space-y-2">
          {packs?.map((pack) => (
            <motion.div key={pack.pack_id} initial={{ opacity: 0 }} animate={{ opacity: 1 }}
              className="flex items-start gap-3 p-3 rounded-lg border border-gray-200 bg-white"
            >
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium text-gray-900">{pack.name}</span>
                  <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${
                    pack.is_active ? "bg-emerald-50 text-emerald-700" : "bg-gray-50 text-gray-500"
                  }`}>{pack.is_active ? "Active" : "Inactive"}</span>
                </div>
                {pack.description && <p className="text-xs text-gray-500 mt-0.5">{pack.description}</p>}
                <p className="text-xs text-gray-400 mt-1">
                  Scope: {pack.scope}{pack.region ? ` · ${pack.region}` : ""}{pack.jurisdiction ? ` · ${pack.jurisdiction}` : ""}
                  {pack.rule_overrides?.length ? ` · ${pack.rule_overrides.length} rules` : ""}
                  v{pack.version}
                </p>
              </div>
              <button onClick={() => handleDelete(pack.pack_id, pack.name)}
                className="p-1.5 text-gray-400 hover:text-red-500 transition-colors"
                title="Delete pack"
              ><Trash2 className="w-4 h-4" /></button>
            </motion.div>
          ))}
        </div>
      )}
    </div>
  );
}

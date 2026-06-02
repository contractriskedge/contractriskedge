"use client";

import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X, Loader2, Plus, FileText } from "lucide-react";
import { useCreateClause } from "@/services/hooks/useClauseIntelligence";
import { CLAUSE_CATEGORIES } from "./types";

interface CreateClauseDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onCreated: () => void;
}

export function CreateClauseDialog({ isOpen, onClose, onCreated }: CreateClauseDialogProps) {
  const [name, setName] = useState("");
  const [category, setCategory] = useState(CLAUSE_CATEGORIES[0]?.id || "");
  const [text, setText] = useState("");
  const [jurisdiction, setJurisdiction] = useState("");
  const [owner, setOwner] = useState("");
  const [tags, setTags] = useState("");
  const [governanceNotes, setGovernanceNotes] = useState("");

  const createMutation = useCreateClause();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim() || !text.trim()) return;

    createMutation.mutate(
      {
        name: name.trim(),
        category,
        text: text.trim(),
        jurisdiction: jurisdiction.trim() || undefined,
        owner: owner.trim() || undefined,
        tags: tags.split(",").map(t => t.trim()).filter(Boolean),
        governance_notes: governanceNotes.trim() || undefined,
      },
      {
        onSuccess: () => {
          setName("");
          setText("");
          setJurisdiction("");
          setOwner("");
          setTags("");
          setGovernanceNotes("");
          onCreated();
        },
      },
    );
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/30 z-50"
            onClick={onClose}
          />
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 20 }}
            className="fixed inset-0 z-50 flex items-center justify-center p-4"
          >
            <div className="bg-white rounded-xl shadow-2xl border border-gray-200 w-full max-w-lg max-h-[85vh] overflow-y-auto">
              {/* Header */}
              <div className="flex items-center justify-between px-5 py-4 border-b border-gray-200">
                <div className="flex items-center gap-2">
                  <div className="w-8 h-8 rounded-lg bg-navy-700 flex items-center justify-center">
                    <FileText className="w-4 h-4 text-white" />
                  </div>
                  <h3 className="text-sm font-semibold text-navy-900">Create New Clause</h3>
                </div>
                <button onClick={onClose} className="p-1 rounded hover:bg-gray-100 text-gray-400 transition-colors">
                  <X className="w-4 h-4" />
                </button>
              </div>

              {/* Form */}
              <form onSubmit={handleSubmit} className="p-5 space-y-4">
                {/* Name */}
                <div>
                  <label className="block text-[10px] font-semibold text-gray-500 uppercase mb-1">Clause Name *</label>
                  <input
                    type="text"
                    value={name}
                    onChange={e => setName(e.target.value)}
                    placeholder="e.g., Mutual Indemnification (Standard)"
                    className="w-full text-xs border border-gray-200 rounded-lg px-3 py-2 focus:border-navy-400 focus:ring-1 focus:ring-navy-400"
                    required
                  />
                </div>

                {/* Category */}
                <div>
                  <label className="block text-[10px] font-semibold text-gray-500 uppercase mb-1">Category *</label>
                  <select
                    value={category}
                    onChange={e => setCategory(e.target.value)}
                    className="w-full text-xs border border-gray-200 rounded-lg px-3 py-2 focus:border-navy-400 focus:ring-1 focus:ring-navy-400"
                  >
                    {CLAUSE_CATEGORIES.map(cat => (
                      <option key={cat.id} value={cat.id}>{cat.name}</option>
                    ))}
                  </select>
                </div>

                {/* Clause Text */}
                <div>
                  <label className="block text-[10px] font-semibold text-gray-500 uppercase mb-1">Clause Text *</label>
                  <textarea
                    value={text}
                    onChange={e => setText(e.target.value)}
                    placeholder="Paste the full clause text here..."
                    rows={6}
                    className="w-full text-xs border border-gray-200 rounded-lg px-3 py-2 focus:border-navy-400 focus:ring-1 focus:ring-navy-400 font-mono"
                    required
                  />
                </div>

                {/* Jurisdiction */}
                <div>
                  <label className="block text-[10px] font-semibold text-gray-500 uppercase mb-1">Jurisdiction</label>
                  <input
                    type="text"
                    value={jurisdiction}
                    onChange={e => setJurisdiction(e.target.value)}
                    placeholder="e.g., Delaware"
                    className="w-full text-xs border border-gray-200 rounded-lg px-3 py-2 focus:border-navy-400 focus:ring-1 focus:ring-navy-400"
                  />
                </div>

                {/* Owner */}
                <div>
                  <label className="block text-[10px] font-semibold text-gray-500 uppercase mb-1">Owner</label>
                  <input
                    type="text"
                    value={owner}
                    onChange={e => setOwner(e.target.value)}
                    placeholder="e.g., legal-team"
                    className="w-full text-xs border border-gray-200 rounded-lg px-3 py-2 focus:border-navy-400 focus:ring-1 focus:ring-navy-400"
                  />
                </div>

                {/* Tags */}
                <div>
                  <label className="block text-[10px] font-semibold text-gray-500 uppercase mb-1">Tags (comma-separated)</label>
                  <input
                    type="text"
                    value={tags}
                    onChange={e => setTags(e.target.value)}
                    placeholder="e.g., indemnification, mutual, standard"
                    className="w-full text-xs border border-gray-200 rounded-lg px-3 py-2 focus:border-navy-400 focus:ring-1 focus:ring-navy-400"
                  />
                </div>

                {/* Governance Notes */}
                <div>
                  <label className="block text-[10px] font-semibold text-gray-500 uppercase mb-1">Governance Notes</label>
                  <textarea
                    value={governanceNotes}
                    onChange={e => setGovernanceNotes(e.target.value)}
                    placeholder="Any notes on usage, approval requirements, etc."
                    rows={3}
                    className="w-full text-xs border border-gray-200 rounded-lg px-3 py-2 focus:border-navy-400 focus:ring-1 focus:ring-navy-400"
                  />
                </div>

                {/* Actions */}
                <div className="flex items-center justify-end gap-2 pt-2 border-t border-gray-100">
                  <button
                    type="button"
                    onClick={onClose}
                    className="px-3 py-2 text-xs font-medium text-gray-600 bg-white border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={createMutation.isPending || !name.trim() || !text.trim()}
                    className="inline-flex items-center gap-1.5 px-4 py-2 text-xs font-medium text-white bg-navy-700 rounded-lg hover:bg-navy-800 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
                  >
                    {createMutation.isPending ? (
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    ) : (
                      <Plus className="w-3.5 h-3.5" />
                    )}
                    {createMutation.isPending ? "Creating..." : "Create Clause"}
                  </button>
                </div>
              </form>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}

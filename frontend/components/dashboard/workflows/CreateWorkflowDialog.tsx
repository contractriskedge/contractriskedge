"use client";

import React, { useState } from "react";
import { X, Workflow } from "lucide-react";
import { useCreateWorkflowPack } from "@/services/hooks/useWorkflowAdmin";

interface Props {
  onClose: () => void;
}

export function CreateWorkflowDialog({ onClose }: Props) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [category, setCategory] = useState("custom");
  const [cloneFrom, setCloneFrom] = useState("");

  const mutation = useCreateWorkflowPack();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;
    try {
      await mutation.mutateAsync({
        name: name.trim(),
        description: description.trim() || undefined,
        category,
        clone_from: cloneFrom || undefined,
      });
      onClose();
    } catch {
      // Error handled by mutation state
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/50" onClick={onClose} />
      <div className="relative bg-navy-900 border border-navy-700 rounded-xl shadow-2xl w-full max-w-lg mx-4 p-6">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <Workflow className="w-5 h-5 text-gold-400" />
            <h2 className="text-lg font-semibold text-gray-100">Create Workflow Pack</h2>
          </div>
          <button onClick={onClose} className="p-1 text-gray-400 hover:text-gray-200">
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm text-gray-300 mb-1">Name *</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g., NDA Review"
              className="w-full px-3 py-2 bg-navy-800 border border-navy-600 rounded-lg text-gray-100 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-gold-500/50"
              autoFocus
              required
            />
          </div>

          <div>
            <label className="block text-sm text-gray-300 mb-1">Description</label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Describe what this workflow does..."
              rows={3}
              className="w-full px-3 py-2 bg-navy-800 border border-navy-600 rounded-lg text-gray-100 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-gold-500/50 resize-none"
            />
          </div>

          <div>
            <label className="block text-sm text-gray-300 mb-1">Category</label>
            <select
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              className="w-full px-3 py-2 bg-navy-800 border border-navy-600 rounded-lg text-gray-100 focus:outline-none focus:ring-2 focus:ring-gold-500/50"
            >
              <option value="legal">Legal</option>
              <option value="sales">Sales</option>
              <option value="procurement">Procurement</option>
              <option value="hr">HR</option>
              <option value="privacy">Privacy</option>
              <option value="custom">Custom</option>
            </select>
          </div>

          <div>
            <label className="block text-sm text-gray-300 mb-1">Clone from (optional)</label>
            <select
              value={cloneFrom}
              onChange={(e) => setCloneFrom(e.target.value)}
              className="w-full px-3 py-2 bg-navy-800 border border-navy-600 rounded-lg text-gray-100 focus:outline-none focus:ring-2 focus:ring-gold-500/50"
            >
              <option value="">Start from scratch</option>
              <option value="nda_review">NDA Review</option>
              <option value="procurement">Procurement</option>
              <option value="legal_review">Legal Review</option>
              <option value="sales_contract">Sales Contract</option>
              <option value="high_risk">High Risk</option>
            </select>
          </div>

          {mutation.isError && (
            <div className="p-3 bg-red-500/10 border border-red-500/30 rounded-lg text-red-400 text-sm">
              {mutation.error instanceof Error ? mutation.error.message : "Failed to create workflow pack"}
            </div>
          )}

          <div className="flex justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-gray-300 hover:text-gray-100 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={!name.trim() || mutation.isPending}
              className="px-4 py-2 bg-gold-500 text-navy-900 rounded-lg hover:bg-gold-400 transition-colors font-medium disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {mutation.isPending ? "Creating..." : "Create Pack"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

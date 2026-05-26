/**
 * SavedViews — save, load, and manage dashboard state configurations.
 *
 * Each saved view captures:
 * - Widget layout (positions, sizes, visibility)
 * - Active filters (time range, risk level, clause type)
 * - Selected template
 *
 * Stored in localStorage with export/import capability.
 */

"use client";

import React, { useState, useCallback, useEffect, useMemo } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Save, FileJson, Download, Upload, Trash2, X, Check, Plus, Clock } from "lucide-react";
import type { WidgetLayout } from "./widgets/WidgetRegistry";

// ── Types ────────────────────────────────────────────────────────

export interface SavedView {
  id: string;
  name: string;
  description?: string;
  layout: WidgetLayout[];
  filters: Record<string, string>;
  templateId?: string;
  createdAt: string;
  updatedAt: string;
}

const STORAGE_KEY = "contractrisk_saved_views";

// ── Persistence ──────────────────────────────────────────────────

export function loadSavedViews(): SavedView[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

export function saveSavedViews(views: SavedView[]): void {
  if (typeof window === "undefined") return;
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(views));
  } catch {}
}

export function deleteSavedView(id: string): void {
  const views = loadSavedViews().filter((v) => v.id !== id);
  saveSavedViews(views);
}

// ── Save View Modal ──────────────────────────────────────────────

interface SaveViewModalProps {
  isOpen: boolean;
  onClose: () => void;
  currentLayout: WidgetLayout[];
  currentFilters: Record<string, string>;
  currentTemplateId?: string;
  onSaved: (view: SavedView) => void;
}

export function SaveViewModal({
  isOpen, onClose, currentLayout, currentFilters, currentTemplateId, onSaved,
}: SaveViewModalProps) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");

  const handleSave = useCallback(() => {
    if (!name.trim()) return;
    const now = new Date().toISOString();
    const view: SavedView = {
      id: `view-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
      name: name.trim(),
      description: description.trim() || undefined,
      layout: currentLayout,
      filters: currentFilters,
      templateId: currentTemplateId,
      createdAt: now,
      updatedAt: now,
    };
    onSaved(view);
    setName("");
    setDescription("");
    onClose();
  }, [name, description, currentLayout, currentFilters, currentTemplateId, onSaved, onClose]);

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 0.3 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 bg-black z-40"
          />
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            className="fixed inset-0 flex items-center justify-center z-50 pointer-events-none"
          >
            <div className="bg-white rounded-xl shadow-2xl border border-gray-200 w-full max-w-md pointer-events-auto">
              <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200">
                <div className="flex items-center gap-2">
                  <Save className="w-4 h-4 text-gray-500" />
                  <h3 className="text-sm font-semibold text-navy-900">Save Dashboard View</h3>
                </div>
                <button onClick={onClose} className="p-1 rounded-lg hover:bg-gray-100 text-gray-400">
                  <X className="w-4 h-4" />
                </button>
              </div>
              <div className="p-4 space-y-3">
                <div>
                  <label className="text-xs font-medium text-gray-700 mb-1 block">View Name</label>
                  <input
                    type="text"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="e.g., Board Review, Renewal Risk"
                    className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                    autoFocus
                    onKeyDown={(e) => e.key === "Enter" && handleSave()}
                  />
                </div>
                <div>
                  <label className="text-xs font-medium text-gray-700 mb-1 block">Description (optional)</label>
                  <input
                    type="text"
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                    placeholder="What does this view show?"
                    className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                  />
                </div>
                <div className="text-[10px] text-gray-400">
                  Saves widget layout, filters, and time range
                </div>
              </div>
              <div className="flex items-center justify-end gap-2 px-4 py-3 border-t border-gray-100 bg-gray-50 rounded-b-xl">
                <button onClick={onClose} className="px-3 py-1.5 text-xs font-medium rounded-lg border border-gray-200 text-gray-600 hover:bg-gray-100">
                  Cancel
                </button>
                <button
                  onClick={handleSave}
                  disabled={!name.trim()}
                  className="px-3 py-1.5 text-xs font-medium rounded-lg bg-navy-700 text-white hover:bg-navy-800 disabled:opacity-40"
                >
                  <Check className="w-3 h-3 inline mr-1" /> Save View
                </button>
              </div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}

// ── Saved Views Panel ────────────────────────────────────────────

interface SavedViewsPanelProps {
  views: SavedView[];
  onLoad: (view: SavedView) => void;
  onDelete: (id: string) => void;
  onSaveNew: () => void;
  activeViewId?: string;
}

export function SavedViewsPanel({ views, onLoad, onDelete, onSaveNew, activeViewId }: SavedViewsPanelProps) {
  if (views.length === 0) return null;

  return (
    <div className="mb-3">
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-[10px] font-medium text-gray-400 uppercase tracking-wider">Saved Views</h3>
        <button
          onClick={onSaveNew}
          className="inline-flex items-center gap-1 text-[10px] font-medium text-blue-600 hover:text-blue-700"
        >
          <Plus className="w-3 h-3" /> Save Current
        </button>
      </div>
      <div className="flex flex-wrap gap-1.5">
        {views.map((view) => (
          <div
            key={view.id}
            className={`group inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-[10px] font-medium transition-colors ${
              activeViewId === view.id
                ? "bg-blue-100 text-blue-700 border border-blue-200"
                : "bg-gray-100 text-gray-600 border border-gray-200 hover:bg-gray-200"
            }`}
          >
            <button onClick={() => onLoad(view)} className="flex items-center gap-1">
              <Clock className="w-3 h-3" />
              {view.name}
            </button>
            <button
              onClick={() => onDelete(view.id)}
              className="opacity-0 group-hover:opacity-100 text-gray-400 hover:text-red-500 transition-opacity"
            >
              <X className="w-3 h-3" />
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}

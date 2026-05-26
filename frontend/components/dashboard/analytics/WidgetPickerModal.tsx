/**
 * WidgetPickerModal — visual widget marketplace for adding/removing dashboard widgets.
 *
 * Groups widgets by category (Operations, Risk, AI, Executive).
 * Shows which widgets are active and lets users toggle them.
 */

"use client";

import React from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X, Plus, Eye, EyeOff, Layout, Activity, Shield, Brain, BarChart3 } from "lucide-react";
import type { WidgetDefinition, WidgetLayout } from "./widgets/WidgetRegistry";

interface WidgetPickerModalProps {
  isOpen: boolean;
  onClose: () => void;
  widgets: WidgetDefinition[];
  layout: WidgetLayout[];
  onToggleWidget: (widgetId: string) => void;
  onResetLayout: () => void;
}

const categoryIcons: Record<string, React.ReactNode> = {
  operations: <Activity className="w-4 h-4" />,
  risk: <Shield className="w-4 h-4" />,
  ai: <Brain className="w-4 h-4" />,
  executive: <BarChart3 className="w-4 h-4" />,
};

const categoryLabels: Record<string, string> = {
  operations: "Operations",
  risk: "Risk & Compliance",
  ai: "AI & Cost",
  executive: "Executive",
};

export function WidgetPickerModal({
  isOpen, onClose, widgets, layout, onToggleWidget, onResetLayout,
}: WidgetPickerModalProps) {
  const visibleIds = new Set(layout.filter((l) => l.visible).map((l) => l.widgetId));
  const categories = ["operations", "risk", "ai", "executive"] as const;

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 0.3 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 bg-black z-40"
          />

          {/* Modal */}
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 20 }}
            className="fixed inset-4 md:inset-x-20 md:inset-y-12 bg-white rounded-2xl shadow-2xl z-50 overflow-hidden flex flex-col"
          >
            {/* Header */}
            <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
              <div className="flex items-center gap-3">
                <Layout className="w-5 h-5 text-gray-500" />
                <div>
                  <h2 className="text-base font-semibold text-navy-900">Widget Marketplace</h2>
                  <p className="text-xs text-gray-500 mt-0.5">
                    Add, remove, and organize dashboard widgets
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={onResetLayout}
                  className="px-3 py-1.5 text-xs font-medium rounded-lg border border-gray-200 text-gray-600 hover:bg-gray-50"
                >
                  Reset to Default
                </button>
                <button
                  onClick={onClose}
                  className="p-1.5 rounded-lg hover:bg-gray-100 text-gray-400"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
            </div>

            {/* Body */}
            <div className="flex-1 overflow-y-auto p-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {categories.map((cat) => {
                  const catWidgets = widgets.filter((w) => w.category === cat);
                  if (catWidgets.length === 0) return null;
                  return (
                    <div key={cat}>
                      <div className="flex items-center gap-2 mb-3">
                        <span className="text-gray-400">{categoryIcons[cat]}</span>
                        <h3 className="text-xs font-semibold text-navy-900 uppercase tracking-wider">
                          {categoryLabels[cat]}
                        </h3>
                        <span className="text-[10px] text-gray-400">
                          {catWidgets.filter((w) => visibleIds.has(w.id)).length}/{catWidgets.length}
                        </span>
                      </div>
                      <div className="space-y-2">
                        {catWidgets.map((w) => {
                          const isVisible = visibleIds.has(w.id);
                          return (
                            <div
                              key={w.id}
                              className={`flex items-center gap-3 p-3 rounded-lg border transition-colors ${
                                isVisible
                                  ? "bg-white border-gray-200 hover:border-blue-300"
                                  : "bg-gray-50 border-dashed border-gray-300 opacity-70 hover:opacity-100"
                              }`}
                            >
                              <div className="flex-1 min-w-0">
                                <p className="text-xs font-medium text-navy-900">{w.title}</p>
                                {w.subtitle && (
                                  <p className="text-[10px] text-gray-500 mt-0.5 truncate">{w.subtitle}</p>
                                )}
                                <div className="flex items-center gap-2 mt-1">
                                  <span className="text-[9px] px-1.5 py-0.5 rounded-full bg-gray-100 text-gray-500 capitalize">
                                    {w.category}
                                  </span>
                                  <span className="text-[9px] text-gray-400">
                                    {w.roles.join(", ")}
                                  </span>
                                </div>
                              </div>
                              <button
                                onClick={() => onToggleWidget(w.id)}
                                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors flex-shrink-0 ${
                                  isVisible
                                    ? "bg-blue-100 text-blue-700 hover:bg-blue-200"
                                    : "bg-gray-200 text-gray-600 hover:bg-gray-300"
                                }`}
                              >
                                {isVisible ? (
                                  <><EyeOff className="w-3 h-3" /> Remove</>
                                ) : (
                                  <><Plus className="w-3 h-3" /> Add</>
                                )}
                              </button>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Footer */}
            <div className="px-6 py-3 border-t border-gray-100 bg-gray-50 flex items-center justify-between">
              <p className="text-[10px] text-gray-400">
                {layout.filter((l) => l.visible).length} widgets active
              </p>
              <button
                onClick={onClose}
                className="px-4 py-1.5 text-xs font-medium rounded-lg bg-navy-700 text-white hover:bg-navy-800"
              >
                Done
              </button>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}

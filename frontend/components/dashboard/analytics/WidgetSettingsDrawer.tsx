/**
 * WidgetSettingsDrawer — slide-out panel for customizing the dashboard layout.
 *
 * Users can:
 * - Toggle widget visibility
 * - Select a dashboard template (Executive, Legal Ops, AI Ops, Risk)
 * - See which widgets are active
 */

"use client";

import React from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X, Eye, EyeOff, Layout, Settings } from "lucide-react";
import type { WidgetDefinition, WidgetLayout, DashboardTemplate } from "./widgets/WidgetRegistry";

interface WidgetSettingsDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  widgets: WidgetDefinition[];
  layout: WidgetLayout[];
  onToggleWidget: (widgetId: string) => void;
  templates: DashboardTemplate[];
  onSelectTemplate: (template: DashboardTemplate) => void;
  activeTemplateId?: string;
}

export function WidgetSettingsDrawer({
  isOpen, onClose, widgets, layout, onToggleWidget,
  templates, onSelectTemplate, activeTemplateId,
}: WidgetSettingsDrawerProps) {
  const visibleIds = new Set(layout.filter((l) => l.visible).map((l) => l.widgetId));

  // Group widgets by category
  const categories = [
    { id: "operations", label: "Operations" },
    { id: "risk", label: "Risk & Compliance" },
    { id: "ai", label: "AI & Cost" },
    { id: "executive", label: "Executive" },
  ] as const;

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

          {/* Drawer */}
          <motion.div
            initial={{ x: "100%" }}
            animate={{ x: 0 }}
            exit={{ x: "100%" }}
            transition={{ type: "spring", damping: 25, stiffness: 300 }}
            className="fixed right-0 top-0 h-full w-80 bg-white shadow-2xl z-50 overflow-y-auto"
          >
            {/* Header */}
            <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200">
              <div className="flex items-center gap-2">
                <Settings className="w-4 h-4 text-gray-500" />
                <h2 className="text-sm font-semibold text-navy-900">Dashboard Settings</h2>
              </div>
              <button onClick={onClose} className="p-1 rounded-lg hover:bg-gray-100 text-gray-400">
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Templates */}
            <div className="px-4 py-3 border-b border-gray-100">
              <h3 className="text-xs font-semibold text-navy-900 mb-2 flex items-center gap-1.5">
                <Layout className="w-3.5 h-3.5 text-gray-400" /> Dashboard Templates
              </h3>
              <div className="space-y-1.5">
                {templates.map((t) => (
                  <button
                    key={t.id}
                    onClick={() => onSelectTemplate(t)}
                    className={`w-full text-left px-3 py-2 rounded-lg text-xs transition-colors ${
                      activeTemplateId === t.id
                        ? "bg-blue-50 border border-blue-200 text-blue-700"
                        : "bg-gray-50 hover:bg-gray-100 border border-gray-200 text-gray-700"
                    }`}
                  >
                    <p className="font-medium">{t.name}</p>
                    <p className="text-[10px] text-gray-500 mt-0.5">{t.description}</p>
                  </button>
                ))}
              </div>
            </div>

            {/* Widget Visibility */}
            <div className="px-4 py-3">
              <h3 className="text-xs font-semibold text-navy-900 mb-3">Widget Visibility</h3>
              {categories.map((cat) => {
                const catWidgets = widgets.filter((w) => w.category === cat.id);
                if (catWidgets.length === 0) return null;
                return (
                  <div key={cat.id} className="mb-3">
                    <p className="text-[10px] font-medium text-gray-400 uppercase tracking-wider mb-1.5">{cat.label}</p>
                    <div className="space-y-1">
                      {catWidgets.map((w) => {
                        const isVisible = visibleIds.has(w.id);
                        return (
                          <button
                            key={w.id}
                            onClick={() => onToggleWidget(w.id)}
                            className={`w-full flex items-center justify-between px-3 py-2 rounded-lg text-xs transition-colors ${
                              isVisible ? "bg-white border border-gray-200" : "bg-gray-50 border border-gray-200 opacity-60"
                            }`}
                          >
                            <div className="flex items-center gap-2 min-w-0">
                              {isVisible ? (
                                <Eye className="w-3.5 h-3.5 text-blue-500 flex-shrink-0" />
                              ) : (
                                <EyeOff className="w-3.5 h-3.5 text-gray-400 flex-shrink-0" />
                              )}
                              <span className="truncate">{w.title}</span>
                            </div>
                            <span className={`text-[10px] font-medium flex-shrink-0 ${isVisible ? "text-blue-600" : "text-gray-400"}`}>
                              {isVisible ? "Visible" : "Hidden"}
                            </span>
                          </button>
                        );
                      })}
                    </div>
                  </div>
                );
              })}
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}

/**
 * WidgetManager — Reusable dashboard personalization framework.
 *
 * Provides:
 * - WidgetContainer: Standardized widget wrapper with title, actions, hide, loading/empty states
 * - useWidgetPreferences: Hook for per-user widget visibility with localStorage persistence
 * - WidgetPreferencesModal: Modal for toggling widget visibility
 *
 * Usage:
 *   const { visibleWidgets, preferences, updatePreference, resetDefaults } = useWidgetPreferences("dashboard-name", defaultWidgets);
 *   {visibleWidgets.map(w => (
 *     <WidgetContainer key={w.id} title={w.label} loading={isLoading} isEmpty={!data}>
 *       {children}
 *     </WidgetContainer>
 *   ))}
 */

"use client";

import React, { useState, useCallback, useMemo, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X, Settings, EyeOff, Loader2, AlertCircle, Check, RotateCcw } from "lucide-react";

// ── Types ─────────────────────────────────────────────────────────

export interface WidgetDefinition {
  id: string;
  label: string;
  defaultVisible: boolean;
  description?: string;
}

export interface DashboardPreferences {
  dashboard: string;
  widgets: Record<string, boolean>;
}

// ── Hook: useWidgetPreferences ────────────────────────────────────

const STORAGE_KEY_PREFIX = "cre_widget_prefs_";

export function useWidgetPreferences(
  dashboard: string,
  widgets: WidgetDefinition[],
) {
  const [preferences, setPreferences] = useState<Record<string, boolean>>(() => {
    if (typeof window === "undefined") return {};
    try {
      const stored = localStorage.getItem(`${STORAGE_KEY_PREFIX}${dashboard}`);
      if (stored) {
        const parsed = JSON.parse(stored) as DashboardPreferences;
        // Merge with defaults to handle new widgets added in future releases
        const merged: Record<string, boolean> = {};
        for (const w of widgets) {
          merged[w.id] = parsed.widgets[w.id] ?? w.defaultVisible;
        }
        return merged;
      }
    } catch { /* ignore */ }
    const defaults: Record<string, boolean> = {};
    for (const w of widgets) defaults[w.id] = w.defaultVisible;
    return defaults;
  });

  const persist = useCallback((prefs: Record<string, boolean>) => {
    try {
      localStorage.setItem(`${STORAGE_KEY_PREFIX}${dashboard}`, JSON.stringify({
        dashboard,
        widgets: prefs,
      }));
    } catch { /* ignore */ }
  }, [dashboard]);

  const updatePreference = useCallback((widgetId: string, visible: boolean) => {
    setPreferences((prev) => {
      const next = { ...prev, [widgetId]: visible };
      persist(next);
      return next;
    });
  }, [persist]);

  const resetDefaults = useCallback(() => {
    const defaults: Record<string, boolean> = {};
    for (const w of widgets) defaults[w.id] = w.defaultVisible;
    setPreferences(defaults);
    persist(defaults);
  }, [widgets, persist]);

  const visibleWidgets = useMemo(
    () => widgets.filter((w) => preferences[w.id] !== false),
    [widgets, preferences],
  );

  const hiddenWidgets = useMemo(
    () => widgets.filter((w) => preferences[w.id] === false),
    [widgets, preferences],
  );

  return {
    preferences,
    visibleWidgets,
    hiddenWidgets,
    updatePreference,
    resetDefaults,
    allVisible: visibleWidgets.length === widgets.length,
  };
}

// ── WidgetContainer ───────────────────────────────────────────────

interface WidgetContainerProps {
  id: string;
  title: string;
  loading?: boolean;
  isEmpty?: boolean;
  emptyMessage?: string;
  onHide?: (id: string) => void;
  actions?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
}

export function WidgetContainer({
  id,
  title,
  loading = false,
  isEmpty = false,
  emptyMessage = "No data available",
  onHide,
  actions,
  children,
  className = "",
}: WidgetContainerProps) {
  const [isVisible, setIsVisible] = useState(true);

  if (!isVisible) return null;

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -8 }}
      className={`bg-white dark:bg-navy-800 rounded-xl border border-gray-200 dark:border-navy-700 shadow-sm ${className}`}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-100 dark:border-navy-700">
        <h3 className="text-xs font-semibold text-navy-900 dark:text-white">{title}</h3>
        <div className="flex items-center gap-1">
          {actions}
          {onHide && (
            <button
              onClick={() => onHide(id)}
              className="p-1 rounded hover:bg-gray-100 dark:hover:bg-navy-700 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
              title="Hide widget"
            >
              <EyeOff className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </div>

      {/* Body */}
      <div className="p-4">
        {loading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="w-5 h-5 text-gray-400 animate-spin" />
          </div>
        ) : isEmpty ? (
          <div className="flex flex-col items-center justify-center py-6 text-center">
            <AlertCircle className="w-6 h-6 text-gray-300 dark:text-gray-600 mb-2" />
            <p className="text-xs text-gray-400 dark:text-gray-500">{emptyMessage}</p>
          </div>
        ) : (
          children
        )}
      </div>
    </motion.div>
  );
}

// ── WidgetPreferencesModal ────────────────────────────────────────

interface WidgetPreferencesModalProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  widgets: WidgetDefinition[];
  preferences: Record<string, boolean>;
  onToggle: (widgetId: string, visible: boolean) => void;
  onReset: () => void;
}

export function WidgetPreferencesModal({
  isOpen,
  onClose,
  title,
  widgets,
  preferences,
  onToggle,
  onReset,
}: WidgetPreferencesModalProps) {
  if (!isOpen) return null;

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm"
        onClick={onClose}
      >
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          exit={{ opacity: 0, scale: 0.95 }}
          onClick={(e) => e.stopPropagation()}
          className="bg-white dark:bg-navy-800 rounded-xl shadow-xl max-w-md w-full mx-4 overflow-hidden"
        >
          {/* Header */}
          <div className="flex items-center justify-between px-5 py-4 border-b border-gray-100 dark:border-navy-700">
            <div className="flex items-center gap-2">
              <Settings className="w-4 h-4 text-navy-500 dark:text-navy-300" />
              <h2 className="text-sm font-bold text-navy-900 dark:text-white">Customize {title}</h2>
            </div>
            <button
              onClick={onClose}
              className="p-1 rounded hover:bg-gray-100 dark:hover:bg-navy-700 text-gray-400 hover:text-gray-600"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          {/* Description */}
          <div className="px-5 py-2 border-b border-gray-50 dark:border-navy-700">
            <p className="text-[10px] text-gray-500 dark:text-gray-400">
              Choose which widgets to display. Hidden widgets will not render.
            </p>
          </div>

          {/* Widget List */}
          <div className="px-5 py-3 max-h-80 overflow-y-auto space-y-1">
            {widgets.map((widget) => {
              const isVisible = preferences[widget.id] !== false;
              return (
                <label
                  key={widget.id}
                  className={`flex items-center gap-3 px-3 py-2.5 rounded-lg cursor-pointer transition-colors ${
                    isVisible
                      ? "bg-navy-50/50 dark:bg-navy-700/50"
                      : "bg-gray-50 dark:bg-navy-700/30 opacity-60"
                  }`}
                >
                  <div
                    className={`w-4 h-4 rounded border-2 flex items-center justify-center transition-colors ${
                      isVisible
                        ? "bg-navy-700 border-navy-700 dark:bg-navy-300 dark:border-navy-300"
                        : "border-gray-300 dark:border-navy-500"
                    }`}
                    onClick={() => onToggle(widget.id, !isVisible)}
                  >
                    {isVisible && <Check className="w-3 h-3 text-white dark:text-navy-900" />}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-xs font-medium text-navy-900 dark:text-white">{widget.label}</p>
                    {widget.description && (
                      <p className="text-[10px] text-gray-500 dark:text-gray-400 truncate">{widget.description}</p>
                    )}
                  </div>
                  <span className={`text-[9px] font-medium px-1.5 py-0.5 rounded-full ${
                    isVisible
                      ? "bg-green-100 text-green-700 dark:bg-green-900/20 dark:text-green-400"
                      : "bg-gray-100 text-gray-500 dark:bg-navy-700 dark:text-gray-400"
                  }`}>
                    {isVisible ? "Visible" : "Hidden"}
                  </span>
                </label>
              );
            })}
          </div>

          {/* Footer */}
          <div className="flex items-center justify-between px-5 py-4 border-t border-gray-100 dark:border-navy-700 bg-gray-50/50 dark:bg-navy-900/50">
            <button
              onClick={onReset}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-[10px] font-medium rounded-lg border border-gray-200 dark:border-navy-600 text-gray-600 dark:text-gray-400 hover:bg-white dark:hover:bg-navy-700 transition-colors"
            >
              <RotateCcw className="w-3 h-3" />
              Reset to Default
            </button>
            <button
              onClick={onClose}
              className="px-4 py-1.5 text-[10px] font-medium rounded-lg bg-navy-700 text-white hover:bg-navy-800 transition-colors shadow-sm"
            >
              Save & Close
            </button>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}

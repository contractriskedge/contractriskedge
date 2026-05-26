/**
 * DashboardGrid — runtime dashboard engine with drag-and-drop, edit/view modes,
 * widget lifecycle, and layout persistence.
 *
 * Built on react-grid-layout with:
 * - Edit / View modes
 * - Drag and resize
 * - Auto-save to localStorage
 * - Widget context menu (refresh, export, hide, fullscreen)
 * - Responsive breakpoints
 * - Empty state for hidden widgets panel
 */

"use client";

import React, { useState, useCallback, useEffect, useMemo } from "react";
import GridLayout from "react-grid-layout";
import { motion, AnimatePresence } from "framer-motion";
import {
  Settings, GripHorizontal, Maximize2, Minimize2, RefreshCw,
  Download, EyeOff, Eye, Edit3, Check, X, Trash2,
} from "lucide-react";
import "react-grid-layout/css/styles.css";

import type { WidgetDefinition, WidgetLayout, DashboardTemplate } from "./widgets/WidgetRegistry";
import {
  DASHBOARD_WIDGETS, getDefaultLayout, getWidgetDefinition,
} from "./widgets/WidgetRegistry";
import { WidgetSettingsDrawer } from "./WidgetSettingsDrawer";

// ── Storage Keys ────────────────────────────────────────────────

const STORAGE_KEY = "contractrisk_dashboard_layout";
const TEMPLATE_KEY = "contractrisk_dashboard_template";
const MODE_KEY = "contractrisk_dashboard_mode";

// ── Default Layout for react-grid-layout ────────────────────────

const COLS = 4;
const ROW_HEIGHT = 120;
const MARGIN = [12, 12];

function toGridLayout(layout: WidgetLayout[]): any[] {
  return layout
    .filter((l) => l.visible)
    .map((l, i) => ({
      i: l.widgetId,
      x: (i % COLS) * 2,
      y: Math.floor(i / COLS) * 2,
      w: l.width || 2,
      h: 2,
      minW: 1,
      minH: 1,
    }));
}

function fromGridLayout(gridLayout: any[], currentLayout: WidgetLayout[]): WidgetLayout[] {
  const visibleMap = new Map(currentLayout.filter((l) => l.visible).map((l) => [l.widgetId, l]));
  return gridLayout.map((item, i) => ({
    widgetId: item.i,
    visible: true,
    position: i,
    width: item.w,
  }));
}

// ── Widget Context Menu ─────────────────────────────────────────

function WidgetMenu({ widgetId, onAction }: {
  widgetId: string;
  onAction: (action: string) => void;
}) {
  const [open, setOpen] = useState(false);
  const actions = [
    { id: "refresh", label: "Refresh", icon: RefreshCw },
    { id: "export", label: "Export", icon: Download },
    { id: "fullscreen", label: "Fullscreen", icon: Maximize2 },
    { id: "hide", label: "Hide", icon: EyeOff },
  ];
  return (
    <div className="relative">
      <button
        onClick={(e) => { e.stopPropagation(); setOpen(!open); }}
        className="p-1 rounded hover:bg-gray-200 text-gray-400 hover:text-gray-600"
      >
        <GripHorizontal className="w-3.5 h-3.5" />
      </button>
      <AnimatePresence>
        {open && (
          <>
            <div className="fixed inset-0 z-10" onClick={() => setOpen(false)} />
            <motion.div
              initial={{ opacity: 0, y: -4 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -4 }}
              className="absolute right-0 top-full mt-1 bg-white border border-gray-200 rounded-lg shadow-lg z-20 py-1 w-32"
            >
              {actions.map((a) => (
                <button
                  key={a.id}
                  onClick={(e) => { e.stopPropagation(); onAction(a.id); setOpen(false); }}
                  className="w-full flex items-center gap-2 px-3 py-1.5 text-xs text-gray-700 hover:bg-gray-50"
                >
                  <a.icon className="w-3 h-3" /> {a.label}
                </button>
              ))}
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </div>
  );
}

// ── Dashboard Grid Component ────────────────────────────────────

interface DashboardGridProps {
  widgets: WidgetDefinition[];
  layout: WidgetLayout[];
  onLayoutChange: (layout: WidgetLayout[]) => void;
  renderWidget: (widgetId: string) => React.ReactNode;
  userRole?: string;
}

export function DashboardGrid({
  widgets, layout, onLayoutChange, renderWidget, userRole = "admin",
}: DashboardGridProps) {
  const [editMode, setEditMode] = useState(() => {
    if (typeof window === "undefined") return false;
    return sessionStorage.getItem(MODE_KEY) === "edit";
  });
  const [showSettings, setShowSettings] = useState(false);
  const [fullscreenWidget, setFullscreenWidget] = useState<string | null>(null);

  // Persist edit mode
  useEffect(() => {
    if (typeof window !== "undefined") {
      sessionStorage.setItem(MODE_KEY, editMode ? "edit" : "view");
    }
  }, [editMode]);

  const gridLayout = useMemo(() => toGridLayout(layout), [layout]);

  const handleLayoutChange = useCallback((newLayout: any[]) => {
    const updated = fromGridLayout(newLayout, layout);
    onLayoutChange(updated);
  }, [layout, onLayoutChange]);

  const handleToggleWidget = useCallback((widgetId: string) => {
    const updated = layout.map((l) =>
      l.widgetId === widgetId ? { ...l, visible: !l.visible } : l
    );
    // If hiding, ensure at least one widget remains
    const visibleCount = updated.filter((l) => l.visible).length;
    if (visibleCount === 0) return;
    onLayoutChange(updated);
  }, [layout, onLayoutChange]);

  const handleWidgetAction = useCallback((widgetId: string, action: string) => {
    switch (action) {
      case "hide":
        handleToggleWidget(widgetId);
        break;
      case "fullscreen":
        setFullscreenWidget(fullscreenWidget === widgetId ? null : widgetId);
        break;
      case "refresh":
        // Trigger re-render by toggling a key — handled by parent
        window.dispatchEvent(new CustomEvent("widget-refresh", { detail: { widgetId } }));
        break;
    }
  }, [handleToggleWidget, fullscreenWidget]);

  const visibleLayout = layout.filter((l) => l.visible);
  const hiddenWidgets = layout.filter((l) => !l.visible);

  // ── Fullscreen overlay ────────────────────────────────────────
  if (fullscreenWidget) {
    const def = getWidgetDefinition(fullscreenWidget);
    return (
      <div className="fixed inset-0 bg-white z-50 overflow-y-auto">
        <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200">
          <h2 className="text-sm font-semibold text-navy-900">{def?.title || fullscreenWidget}</h2>
          <button
            onClick={() => setFullscreenWidget(null)}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg bg-gray-100 hover:bg-gray-200"
          >
            <Minimize2 className="w-3.5 h-3.5" /> Exit Fullscreen
          </button>
        </div>
        <div className="p-6 h-[calc(100vh-60px)]">
          {renderWidget(fullscreenWidget)}
        </div>
      </div>
    );
  }

  return (
    <div className="relative">
      {/* ── Toolbar ── */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          {editMode ? (
            <>
              <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-amber-100 text-amber-700 text-xs font-medium">
                <Edit3 className="w-3 h-3" /> Edit Mode
              </span>
              <button
                onClick={() => setEditMode(false)}
                className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-medium rounded-lg bg-green-100 text-green-700 hover:bg-green-200"
              >
                <Check className="w-3 h-3" /> Done
              </button>
            </>
          ) : (
            <button
              onClick={() => setEditMode(true)}
              className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-medium rounded-lg bg-gray-100 text-gray-600 hover:bg-gray-200"
            >
              <Edit3 className="w-3 h-3" /> Customize
            </button>
          )}
        </div>
        <button
          onClick={() => setShowSettings(true)}
          className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-medium rounded-lg bg-gray-100 text-gray-600 hover:bg-gray-200"
        >
          <Settings className="w-3 h-3" /> Widgets
        </button>
      </div>

      {/* ── Hidden Widgets Bar ── */}
      {hiddenWidgets.length > 0 && (
        <div className="mb-3 px-3 py-2 rounded-lg bg-gray-50 border border-dashed border-gray-300">
          <p className="text-[10px] font-medium text-gray-400 uppercase tracking-wider mb-1.5">
            Hidden Widgets ({hiddenWidgets.length})
          </p>
          <div className="flex flex-wrap gap-1.5">
            {hiddenWidgets.map((l) => {
              const def = getWidgetDefinition(l.widgetId);
              return (
                <button
                  key={l.widgetId}
                  onClick={() => handleToggleWidget(l.widgetId)}
                  className="inline-flex items-center gap-1 px-2 py-1 text-[10px] font-medium rounded-md bg-white border border-gray-200 text-gray-500 hover:border-blue-300 hover:text-blue-600"
                >
                  <Eye className="w-3 h-3" /> {def?.title || l.widgetId}
                </button>
              );
            })}
          </div>
        </div>
      )}

      {/* ── Grid ── */}
      <GridLayout
        className="layout"
        layout={gridLayout}
        cols={COLS}
        rowHeight={ROW_HEIGHT}
        width={1200}
        margin={MARGIN}
        isDraggable={editMode}
        isResizable={editMode}
        onLayoutChange={handleLayoutChange}
        compactType="vertical"
        preventCollision={false}
        draggableHandle=".drag-handle"
      >
        {visibleLayout.map((l) => {
          const def = getWidgetDefinition(l.widgetId);
          return (
            <div key={l.widgetId} className="relative group">
              {/* Widget header (only visible in edit mode or on hover) */}
              <div className={`absolute top-0 left-0 right-0 z-10 flex items-center justify-between px-2 py-1 rounded-t-lg ${
                editMode ? "bg-blue-50 border-b border-blue-200" : "opacity-0 group-hover:opacity-100 transition-opacity"
              }`}>
                <div className="flex items-center gap-1.5 drag-handle" style={{ cursor: editMode ? "grab" : "default" }}>
                  {editMode && <GripHorizontal className="w-3 h-3 text-blue-400" />}
                  <span className="text-[10px] font-medium text-gray-500">{def?.title || l.widgetId}</span>
                </div>
                <WidgetMenu widgetId={l.widgetId} onAction={(a) => handleWidgetAction(l.widgetId, a)} />
              </div>
              {/* Widget content */}
              <div className={`h-full ${editMode ? "pt-8" : "pt-0"}`}>
                {renderWidget(l.widgetId)}
              </div>
            </div>
          );
        })}
      </GridLayout>

      {/* ── Settings Drawer ── */}
      <WidgetSettingsDrawer
        isOpen={showSettings}
        onClose={() => setShowSettings(false)}
        widgets={widgets}
        layout={layout}
        onToggleWidget={handleToggleWidget}
        templates={[]}
        onSelectTemplate={() => {}}
      />
    </div>
  );
}

// ── Layout Persistence Helpers ──────────────────────────────────

export function saveLayout(layout: WidgetLayout[]): void {
  if (typeof window === "undefined") return;
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(layout));
  } catch {}
}

export function loadLayout(): WidgetLayout[] | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    return JSON.parse(raw) as WidgetLayout[];
  } catch {
    return null;
  }
}

export function saveTemplate(templateId: string): void {
  if (typeof window === "undefined") return;
  try {
    localStorage.setItem(TEMPLATE_KEY, templateId);
  } catch {}
}

export function loadTemplate(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TEMPLATE_KEY);
}

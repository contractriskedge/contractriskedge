/**
 * FocusModeToggle — toolbar button to toggle focus mode.
 *
 * In focus mode both side panels are hidden and the centre review area
 * expands to fill the full width. Clicking the button again or pressing
 * ESC restores the previous layout.
 */

"use client";

import React from "react";
import { Maximize2, Minimize2 } from "lucide-react";
import { panelStore, usePanelState } from "./panel-store";

export function FocusModeToggle() {
  const state = usePanelState();
  const isActive = state.focusMode;

  return (
    <button
      type="button"
      onClick={() => panelStore.toggleFocusMode()}
      className={`inline-flex items-center gap-1.5 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
        isActive
          ? "bg-navy-700 text-white dark:bg-navy-600"
          : "text-gray-600 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-navy-700 border border-gray-300 dark:border-navy-600"
      }`}
      title={isActive ? "Exit focus mode (ESC)" : "Focus mode — hide side panels (Alt+F)"}
      aria-label={isActive ? "Exit focus mode" : "Enter focus mode"}
      aria-pressed={isActive}
    >
      {isActive ? (
        <Minimize2 className="w-4 h-4" />
      ) : (
        <Maximize2 className="w-4 h-4" />
      )}
      {isActive ? "Exit Focus" : "Focus"}
    </button>
  );
}

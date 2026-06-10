/**
 * useReviewShortcuts — keyboard shortcuts for the Review Workspace.
 *
 * Alt+D  → Toggle document panel mode (pinned ↔ auto_hide)
 * Alt+R  → Toggle risk/right panel mode (pinned ↔ auto_hide)
 * Alt+F  → Toggle focus mode
 * ESC    → Exit focus mode
 *
 * The hook attaches a global keydown listener and cleans up on unmount.
 */

"use client";

import { useEffect } from "react";
import { panelStore } from "./panel-store";

export function useReviewShortcuts(): void {
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      // Alt+ shortcuts
      if (e.altKey && !e.shiftKey && !e.metaKey && !e.ctrlKey) {
        switch (e.code) {
          case "KeyD": // Alt+D → toggle document (left) panel
            e.preventDefault();
            panelStore.toggleLeftMode();
            break;
          case "KeyR": // Alt+R → toggle risk (right) panel
            e.preventDefault();
            panelStore.toggleRightMode();
            break;
          case "KeyF": // Alt+F → toggle focus mode
            e.preventDefault();
            panelStore.toggleFocusMode();
            break;
        }
      }

      // ESC → exit focus mode
      if (e.code === "Escape") {
        const state = panelStore.get();
        if (state.focusMode) {
          e.preventDefault();
          panelStore.exitFocusMode();
        }
      }
    };

    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, []);
}

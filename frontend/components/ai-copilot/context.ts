// ── AI Copilot Context Manager ──────────────────────────────────────────────

import type { CopilotContext } from "./types";

class ContextManager {
  private context: CopilotContext = {
    currentScreen: "portfolio",
    selectedEntityId: null,
    selectedEntityType: null,
    workflowStage: null,
    userRole: "admin",
    businessUnit: null,
    recentActivity: [],
    pageMetadata: {},
  };

  private listeners: Array<(ctx: CopilotContext) => void> = [];

  update(partial: Partial<CopilotContext>) {
    this.context = { ...this.context, ...partial };
    this.listeners.forEach((fn) => fn(this.context));
  }

  get(): CopilotContext {
    return { ...this.context };
  }

  subscribe(fn: (ctx: CopilotContext) => void) {
    this.listeners.push(fn);
    return () => {
      this.listeners = this.listeners.filter((l) => l !== fn);
    };
  }

  setScreen(screen: string) {
    this.update({ currentScreen: screen, selectedEntityId: null, selectedEntityType: null });
  }

  setSelection(type: CopilotContext["selectedEntityType"], id: string | null, metadata?: Record<string, string>) {
    this.update({ selectedEntityType: type, selectedEntityId: id, pageMetadata: metadata || {} });
  }

  addActivity(activity: string) {
    const recent = [activity, ...this.context.recentActivity].slice(0, 10);
    this.update({ recentActivity: recent });
  }

  getContextSummary(): string {
    const ctx = this.context;
    const parts = [
      `Screen: ${ctx.currentScreen}`,
      ctx.selectedEntityId ? `Selected: ${ctx.selectedEntityType} (${ctx.selectedEntityId})` : null,
      ctx.workflowStage ? `Workflow Stage: ${ctx.workflowStage}` : null,
      ctx.businessUnit ? `Business Unit: ${ctx.businessUnit}` : null,
      ctx.recentActivity.length > 0 ? `Recent: ${ctx.recentActivity.slice(0, 3).join(", ")}` : null,
    ].filter(Boolean);
    return parts.join(" | ");
  }
}

export const copilotContext = new ContextManager();

// ── Hook for React components ───────────────────────────────────────────────

import { useState, useEffect } from "react";

export function useCopilotContext() {
  const [context, setContext] = useState(copilotContext.get());

  useEffect(() => {
    const unsub = copilotContext.subscribe(setContext);
    return unsub;
  }, []);

  return context;
}

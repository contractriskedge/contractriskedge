/**
 * Authenticated layout — enterprise application shell.
 *
 * Provides:
 * - Persistent left navigation
 * - Top command bar with global search, notifications, tenant switcher
 * - AI Copilot integration
 * - Theme and accessibility controls
 * - Operational state banners
 * - Route-level error boundaries
 * - Real-time coordination
 */

"use client";

import React, { useState, useCallback } from "react";
import { useAuth } from "@/components/auth/AuthProvider";
import { Sidebar } from "@/components/dashboard/Sidebar";
import { TopNav } from "@/components/dashboard/TopNav";
import { AiCopilot } from "@/components/ai-copilot/AiCopilot";
import { copilotContext } from "@/components/ai-copilot/context";
import { DashboardProvider } from "@/components/dashboard/shared/DashboardContext";
import { useTheme } from "@/components/theme/ThemeProvider";
import { OperationalBannerBar } from "@/src/lib/realtime/operationalBanners";
import { useRealtimeCoordinator } from "@/src/lib/realtime/realtimeCoordinator";
import { useInvalidationOrchestrator } from "@/src/lib/realtime/invalidationOrchestrator";
import { Sun, Moon, ZoomIn, ZoomOut } from "lucide-react";

type ViewType = "portfolio" | "cfo" | "legal" | "procurement" | "contracts" | "benchmarks" | "settings" | "admin" | "relationships" | "workflows" | "contract-detail" | "clause-library" | "obligations" | "analytics" | "negotiation" | "search" | "ingestion" | "compliance" | "review" | "executive-dashboard" | "policy" | "clause-intelligence" | "tenant-settings" | "executive-command-center" | "reviewer-operations" | "governance-dashboard" | "ai-operations-dashboard" | "workflow-intelligence-dashboard" | "command-center";

export default function AuthenticatedLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { user, logout } = useAuth();
  const { isDark, toggleTheme, fontSize, setFontSize, prefersReducedMotion } = useTheme();
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [activeView, setActiveView] = useState<ViewType>("ingestion");

  // Real-time coordination — connects WebSocket events to query invalidation
  const { invalidate } = useInvalidationOrchestrator();
  const { connectionStatus } = useRealtimeCoordinator({
    onInvalidate: invalidate,
    enabled: true,
  });

  // Derive active view from pathname for route-aware navigation
  React.useEffect(() => {
    const path = window.location.pathname;
    if (path.startsWith("/dashboard")) setActiveView("portfolio");
    else if (path.startsWith("/reviews")) setActiveView("review");
    else if (path.startsWith("/contracts")) setActiveView("contracts");
    else if (path.startsWith("/procurement")) setActiveView("procurement");
    else if (path.startsWith("/compliance")) setActiveView("compliance");
    else if (path.startsWith("/workflows")) setActiveView("workflows");
    else if (path.startsWith("/analytics")) setActiveView("analytics");
    else if (path.startsWith("/benchmarks")) setActiveView("benchmarks");
    else if (path.startsWith("/admin")) setActiveView("admin");
    else if (path.startsWith("/settings")) setActiveView("settings");
    else if (path.startsWith("/command-center")) setActiveView("command-center");
    else if (path.startsWith("/executive")) setActiveView("executive-command-center");
    else if (path.startsWith("/search")) setActiveView("search");
    else if (path.startsWith("/clause-library")) setActiveView("clause-library");
    else if (path.startsWith("/obligations")) setActiveView("obligations");
    else if (path.startsWith("/negotiation")) setActiveView("negotiation");
    else if (path.startsWith("/clause-intelligence")) setActiveView("clause-intelligence");
    else if (path.startsWith("/policy")) setActiveView("policy");
    else if (path.startsWith("/relationships")) setActiveView("relationships");
    else if (path.startsWith("/governance-dashboard")) setActiveView("governance-dashboard");
    else if (path.startsWith("/reviewer-operations")) setActiveView("reviewer-operations");
    else if (path.startsWith("/workflow-intelligence-dashboard")) setActiveView("workflow-intelligence-dashboard");
    else if (path.startsWith("/ai-operations-dashboard")) setActiveView("ai-operations-dashboard");
    else if (path.startsWith("/tenant-settings")) setActiveView("tenant-settings");
    else if (path.startsWith("/ai-operations-dashboard")) setActiveView("ai-operations-dashboard");
    else if (path.startsWith("/relationships")) setActiveView("relationships");
    else setActiveView("ingestion");
  }, []);

  React.useEffect(() => {
    copilotContext.setScreen(activeView);
  }, [activeView]);

  return (
    <DashboardProvider>
      <div
        className={`flex h-screen bg-gray-50 dark:bg-navy-900 transition-colors duration-200 ${
          prefersReducedMotion ? "" : "animate-fade-in"
        }`}
        role="application"
        aria-label="Contract Risk Analyzer"
      >
        <Sidebar
          activeView={activeView}
          onViewChange={(view) => {
            setActiveView(view);
            // Map view to route
            const routeMap: Record<string, string> = {
              portfolio: "/dashboard",
              review: "/reviews",
              contracts: "/contracts",
              procurement: "/procurement",
              compliance: "/compliance",
              workflows: "/workflows",
              analytics: "/analytics",
              benchmarks: "/benchmarks",
              admin: "/admin",
              settings: "/settings",
              "command-center": "/command-center",
              "executive-command-center": "/executive",
              "executive-dashboard": "/executive",
              search: "/search",
              ingestion: "/ingestion",
              "clause-library": "/clause-library",
              obligations: "/obligations",
              negotiation: "/negotiation",
              "clause-intelligence": "/clause-intelligence",
              policy: "/policy",
              relationships: "/relationships",
              "governance-dashboard": "/governance-dashboard",
              "reviewer-operations": "/reviewer-operations",
              "workflow-intelligence-dashboard": "/workflow-intelligence-dashboard",
              "ai-operations-dashboard": "/ai-operations-dashboard",
              "tenant-settings": "/tenant-settings",
              "ai-operations-dashboard": "/ai-operations-dashboard",
              relationships: "/relationships",
            };
            window.location.href = routeMap[view] || "/ingestion";
          }}
          collapsed={sidebarCollapsed}
          onToggle={() => setSidebarCollapsed(!sidebarCollapsed)}
        />
        <div className="flex-1 flex flex-col min-w-0">
          <TopNav
            user={user}
            onLogout={logout}
            onToggleSidebar={() => setSidebarCollapsed(!sidebarCollapsed)}
          />
          {/* Accessibility & Theme Toolbar */}
          <div
            className="flex items-center justify-end gap-2 px-4 py-1.5 bg-gray-100 dark:bg-navy-800 border-b border-gray-200 dark:border-navy-700"
            role="toolbar"
            aria-label="Accessibility controls"
          >
            <button
              onClick={() => setFontSize(fontSize - 0.25)}
              className="p-1.5 rounded hover:bg-gray-200 dark:hover:bg-navy-700 text-navy-600 dark:text-navy-200 focus:outline-none focus:ring-2 focus:ring-gold-400 focus:ring-offset-2 dark:focus:ring-offset-navy-800"
              aria-label="Decrease font size"
              title="Decrease font size"
            >
              <ZoomOut className="w-3.5 h-3.5" aria-hidden="true" />
            </button>
            <span className="text-xs text-navy-500 dark:text-navy-300 min-w-[4rem] text-center" aria-live="polite">
              {Math.round(fontSize * 100)}%
            </span>
            <button
              onClick={() => setFontSize(fontSize + 0.25)}
              className="p-1.5 rounded hover:bg-gray-200 dark:hover:bg-navy-700 text-navy-600 dark:text-navy-200 focus:outline-none focus:ring-2 focus:ring-gold-400 focus:ring-offset-2 dark:focus:ring-offset-navy-800"
              aria-label="Increase font size"
              title="Increase font size"
            >
              <ZoomIn className="w-3.5 h-3.5" aria-hidden="true" />
            </button>
            <div className="w-px h-4 bg-gray-300 dark:bg-navy-600 mx-1" aria-hidden="true" />
            <button
              onClick={toggleTheme}
              className="p-1.5 rounded hover:bg-gray-200 dark:hover:bg-navy-700 text-navy-600 dark:text-navy-200 focus:outline-none focus:ring-2 focus:ring-gold-400 focus:ring-offset-2 dark:focus:ring-offset-navy-800"
              aria-label={isDark ? "Switch to light mode" : "Switch to dark mode"}
              title={isDark ? "Switch to light mode" : "Switch to dark mode"}
            >
              {isDark ? (
                <Sun className="w-3.5 h-3.5" aria-hidden="true" />
              ) : (
                <Moon className="w-3.5 h-3.5" aria-hidden="true" />
              )}
            </button>
          </div>
          {/* Operational state banners — live system awareness */}
          <OperationalBannerBar />
          <main
            className="flex-1 overflow-auto p-6"
            role="main"
            aria-label={`${activeView} view`}
          >
            {children}
          </main>
        </div>
        <AiCopilot />
      </div>
    </DashboardProvider>
  );
}

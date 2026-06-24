"use client";

import React, { useState, useEffect, useCallback, lazy, Suspense } from "react";
import { useAuth } from "@/components/auth/AuthProvider";
import { useTheme } from "@/components/theme/ThemeProvider";
import { Sidebar } from "./Sidebar";
import { TopNav } from "./TopNav";
import { AnalyticsCenter } from "./analytics/AnalyticsCenter";
import { SearchHub } from "./search/SearchHub";
import { IngestionCenter } from "./ingestion/IngestionCenter";
import { ReviewWorkspace } from "@/components/review/ReviewWorkspace";
import { ReviewQueue } from "@/components/review/ReviewQueue";
import { ReviewDashboard } from "@/components/review/ReviewDashboard";
import { ProtectedRoute } from "@/components/auth/ProtectedRoute";
import { AdminConsole } from "./AdminConsole";
import { AiCopilot } from "@/components/ai-copilot/AiCopilot";
import { copilotContext } from "@/components/ai-copilot/context";
import { useReviews } from "@/services/hooks/useReviews";
import { CfoView } from "./CfoView";
import { LegalView } from "./LegalView";
import { ProcurementView } from "./ProcurementView";
import { ExecutiveDashboard as ExecutiveDashboardV2 } from "./ExecutiveDashboardV2";
import { ContractsPage } from "./contracts/ContractsPage";
import { BenchmarkPage } from "./BenchmarkPage";
import { SettingsPage } from "./SettingsPage";
import { RelationshipGraph } from "./RelationshipGraph";
import { PlaceholderView } from "./shared/PlaceholderView";
import { PolicyEngine } from "@/components/policy/PolicyEngine";
import { ExplainabilityPanel } from "@/components/explainability/ExplainabilityPanel";
import { GlobalActivityCenter } from "@/components/activity/GlobalActivityCenter";
import { ClauseIntelligenceView } from "@/components/clause-intelligence/ClauseIntelligenceView";
import { ExecutiveDashboardView } from "@/components/executive/ExecutiveDashboard";
import { TenantSettings } from "@/components/tenant/TenantSettings";
import { DashboardProvider } from "./shared/DashboardContext";
import { Sun, Moon, ZoomIn, ZoomOut, FileText } from "lucide-react";

// ── Lazy-loaded Sprint 10 dashboards ──────────────────────────────
const ExecutiveCommandCenter = lazy(() =>
  import("./command-center/ExecutiveCommandCenter").then((m) => ({ default: m.ExecutiveCommandCenter }))
);
const ReviewerOperations = lazy(() =>
  import("./operations/ReviewerOperations").then((m) => ({ default: m.ReviewerOperations }))
);
const GovernanceDashboard = lazy(() =>
  import("./governance/GovernanceDashboard").then((m) => ({ default: m.GovernanceDashboard }))
);
const AiOperationsDashboard = lazy(() =>
  import("./ai-ops/AiOperationsDashboard").then((m) => ({ default: m.AiOperationsDashboard }))
);
const WorkflowIntelligenceDashboard = lazy(() =>
  import("./workflow-intelligence/WorkflowIntelligenceDashboard").then((m) => ({ default: m.WorkflowIntelligenceDashboard }))
);
const ObligationCenter = lazy(() =>
  import("./obligations/ObligationCenter").then((m) => ({ default: m.ObligationCenter }))
);

function DashboardSkeleton() {
  return (
    <div className="p-6 space-y-4 animate-pulse">
      <div className="h-8 bg-gray-200 dark:bg-navy-700 rounded w-64" />
      <div className="h-4 bg-gray-200 dark:bg-navy-700 rounded w-96" />
      <div className="grid grid-cols-2 gap-4 mt-6">
        <div className="h-48 bg-gray-200 dark:bg-navy-700 rounded-xl" />
        <div className="h-48 bg-gray-200 dark:bg-navy-700 rounded-xl" />
        <div className="h-48 bg-gray-200 dark:bg-navy-700 rounded-xl" />
        <div className="h-48 bg-gray-200 dark:bg-navy-700 rounded-xl" />
      </div>
    </div>
  );
}

// Full enterprise view types — all workspaces available in the sidebar.
// Views without full backend integration show a placeholder indicating
// the module is available but pending backend completion.
        type ViewType = "cfo" | "legal" | "procurement" | "contracts" | "benchmarks" | "settings" | "admin" | "relationships" | "workflows" | "contract-detail" | "clause-library" | "obligations" | "analytics" | "negotiation" | "search" | "ingestion" | "compliance" | "review" | "review-dashboard" | "executive-dashboard" | "policy" | "clause-intelligence" | "tenant-settings" | "executive-command-center" | "reviewer-operations" | "governance-dashboard" | "ai-operations-dashboard" | "workflow-intelligence-dashboard" | "command-center" | "activity-center";

export function DashboardLayout() {
  const { user, logout } = useAuth();
  const { isDark, toggleTheme, fontSize, setFontSize, prefersReducedMotion } = useTheme();
  const [activeView, setActiveView] = useState<ViewType>("ingestion");
  const [selectedReviewId, setSelectedReviewId] = useState<string | null>(null);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  // Update AI Copilot context on view change
  React.useEffect(() => {
    copilotContext.setScreen(activeView);
  }, [activeView]);

  // ── Auto-load reviews when Review view is active ────────────────
  const { data: reviewsData } = useReviews({ page_size: 50 });

  // Handle navigation to a specific review from any child component
  const handleNavigateToReview = useCallback((reviewId: string) => {
    setSelectedReviewId(reviewId);
    setActiveView("review");
  }, []);

  // Listen for navigate-to-review custom event from NotificationCenter
  useEffect(() => {
    const handler = (event: Event) => {
      const detail = (event as CustomEvent).detail as { reviewId: string } | undefined;
      if (detail?.reviewId) {
        handleNavigateToReview(detail.reviewId);
      }
    };
    window.addEventListener("navigate-to-review", handler);
    return () => window.removeEventListener("navigate-to-review", handler);
  }, [handleNavigateToReview]);

  // When entering Review view without a specific review selected, show list
  useEffect(() => {
    if (activeView === "review" && !selectedReviewId) {
      // Don't auto-select — let the user pick from the list
    }
  }, [activeView, selectedReviewId]);

  const renderView = () => {
    switch (activeView) {
      // ── Core Workspaces ──
      case "activity-center":
        return (
          <div className="max-w-5xl mx-auto">
            <GlobalActivityCenter />
          </div>
        );
      case "ingestion":
        return <IngestionCenter onReviewNavigate={handleNavigateToReview} />;
      case "search":
        return <SearchHub />;
      case "analytics":
        return (
          <AnalyticsCenter
            onNavigate={(view, params) => {
              if (view === "review" && params?.reviewId) {
                setSelectedReviewId(params.reviewId);
                setActiveView("review");
              } else if (view === "search" && params?.query) {
                setActiveView("search");
                sessionStorage.setItem("searchQuery", params.query);
              } else {
                setActiveView(view as ViewType);
              }
            }}
          />
        );
      case "review":
        return selectedReviewId ? (
          <ProtectedRoute permission="contracts:read">
            <ReviewWorkspace
              reviewId={selectedReviewId}
              onBack={() => { setSelectedReviewId(null); setActiveView("ingestion"); }}
            />
          </ProtectedRoute>
        ) : (
          <ProtectedRoute permission="contracts:read">
            <div className="max-w-5xl mx-auto">
              <ReviewQueue
                onReviewSelect={(reviewId) => setSelectedReviewId(reviewId)}
              />
            </div>
          </ProtectedRoute>
        );
      case "review-dashboard":
        return (
          <ProtectedRoute permission="contracts:read">
            <div className="max-w-6xl mx-auto">
              <ReviewDashboard
                onReviewSelect={(reviewId) => {
                  setSelectedReviewId(reviewId);
                  setActiveView("review");
                }}
              />
            </div>
          </ProtectedRoute>
        );

      // ── Sprint 10 — Unified Dashboards ──
      case "executive-command-center":
        return (
          <Suspense fallback={<DashboardSkeleton />}>
            <ExecutiveCommandCenter />
          </Suspense>
        );
      case "reviewer-operations":
        return (
          <Suspense fallback={<DashboardSkeleton />}>
            <ReviewerOperations />
          </Suspense>
        );
      case "governance-dashboard":
        return (
          <Suspense fallback={<DashboardSkeleton />}>
            <GovernanceDashboard />
          </Suspense>
        );
      case "ai-operations-dashboard":
        return (
          <Suspense fallback={<DashboardSkeleton />}>
            <AiOperationsDashboard />
          </Suspense>
        );
      case "workflow-intelligence-dashboard":
        return (
          <Suspense fallback={<DashboardSkeleton />}>
            <WorkflowIntelligenceDashboard />
          </Suspense>
        );

      // ── Enterprise Workspaces ──
      case "executive-dashboard":
        return <ExecutiveDashboardV2 />;
      case "cfo":
        return <CfoView />;
      case "legal":
        return <LegalView />;
      case "procurement":
        return <ProcurementView />;
      case "compliance":
        return <PlaceholderView
          title="Compliance Center"
          description="Regulatory compliance tracking, obligation management, and audit readiness."
          icon="shield"
          status="In Development"
        />;

      // ── Advanced Modules ──
      case "contracts":
        return <ContractsPage />;
      case "clause-library":
        return <PlaceholderView
          title="Clause Library"
          description="Browse, search, and manage standard and custom contract clauses."
          icon="library"
          status="Coming Soon"
        />;
      case "obligations":
        return (
          <ProtectedRoute permission="contracts:read">
            <Suspense fallback={<DashboardSkeleton />}>
              <ObligationCenter />
            </Suspense>
          </ProtectedRoute>
        );
      case "negotiation":
        return <PlaceholderView
          title="Negotiation Workspace"
          description="AI-assisted contract negotiation with redline comparison and playbook guidance."
          icon="git-merge"
          status="In Development"
        />;
      case "workflows":
        return <PlaceholderView
          title="Workflow Automation"
          description="Design and monitor automated review workflows, approval chains, and SLA policies."
          icon="workflow"
          status="In Development"
        />;
      case "benchmarks":
        return <BenchmarkPage />;
      case "relationships":
        return <RelationshipGraph />;

      // ── Sprint 7 — Enterprise Intelligence ──
      case "policy":
        return (
          <ProtectedRoute permission={["contracts:read", "ai:view"]} requireAll={false}>
            <PolicyEngine />
          </ProtectedRoute>
        );
      case "clause-intelligence":
        return (
          <ProtectedRoute permission="contracts:read">
            <ClauseIntelligenceView />
          </ProtectedRoute>
        );

      // ── Administration ──
      case "admin":
        return (
          <ProtectedRoute permission="admin:system">
            <AdminConsole />
          </ProtectedRoute>
        );
      case "settings":
        return (
          <ProtectedRoute permission="admin:tenant">
            <SettingsPage />
          </ProtectedRoute>
        );
      case "tenant-settings":
        return (
          <ProtectedRoute permission="admin:tenant">
            {user?.tenant_id ? <TenantSettings tenantId={user.tenant_id} /> : <SettingsPage />}
          </ProtectedRoute>
        );

      default:
        return <IngestionCenter onReviewNavigate={handleNavigateToReview} />;
    }
  };

  return (
    <DashboardProvider>
    <div
      className={`flex h-screen bg-gray-50 dark:bg-navy-900 transition-colors duration-200 ${
        prefersReducedMotion ? "" : "animate-fade-in"
      }`}
      role="application"
      aria-label="Contract Risk Analyzer Dashboard"
    >
      <Sidebar
        activeView={activeView}
        onViewChange={(view: ViewType) => setActiveView(view)}
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
        <main
          className="flex-1 overflow-auto p-6"
          role="main"
          aria-label={`${activeView} view`}
        >
          {renderView()}
        </main>
      </div>

      {/* Global AI Copilot */}
      <AiCopilot />
    </div>
    </DashboardProvider>
  );
}

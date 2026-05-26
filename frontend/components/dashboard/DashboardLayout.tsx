"use client";

import React, { useState, useEffect, useCallback } from "react";
import { useAuth } from "@/components/auth/AuthProvider";
import { useTheme } from "@/components/theme/ThemeProvider";
import { Sidebar } from "./Sidebar";
import { TopNav } from "./TopNav";
import { AnalyticsCenter } from "./analytics/AnalyticsCenter";
import { SearchHub } from "./search/SearchHub";
import { IngestionCenter } from "./ingestion/IngestionCenter";
import { ReviewWorkspace } from "@/components/review/ReviewWorkspace";
import { ReviewQueue } from "@/components/review/ReviewQueue";
import { AdminConsole } from "./AdminConsole";
import { AiCopilot } from "@/components/ai-copilot/AiCopilot";
import { copilotContext } from "@/components/ai-copilot/context";
import { useReviews } from "@/services/hooks/useReviews";
import { Sun, Moon, ZoomIn, ZoomOut, FileText } from "lucide-react";

// Only views with real backend API integration are active.
// Non-integrated views are removed until they have real backend endpoints.
type ViewType = "ingestion" | "search" | "analytics" | "review" | "admin";

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

  // When entering Review view without a specific review selected, show list
  useEffect(() => {
    if (activeView === "review" && !selectedReviewId) {
      // Don't auto-select — let the user pick from the list
    }
  }, [activeView, selectedReviewId]);

  const renderView = () => {
    switch (activeView) {
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
                // Store search query for SearchHub to pick up
                sessionStorage.setItem("searchQuery", params.query);
              } else {
                setActiveView(view);
              }
            }}
          />
        );
      case "review":
        return selectedReviewId ? (
          <ReviewWorkspace
            reviewId={selectedReviewId}
            onBack={() => { setSelectedReviewId(null); setActiveView("ingestion"); }}
          />
        ) : (
          <div className="max-w-5xl mx-auto">
            <div className="mb-4">
              <h2 className="text-lg font-bold text-navy-900">Review Queue</h2>
              <p className="text-sm text-gray-500 mt-1">Manage and process contract reviews</p>
            </div>
            <ReviewQueue
              onReviewSelect={(reviewId) => setSelectedReviewId(reviewId)}
            />
          </div>
        );
      case "admin":
        return <AdminConsole />;
      default:
        return <IngestionCenter />;
    }
  };

  return (
    <div
      className={`flex h-screen bg-gray-50 dark:bg-navy-900 transition-colors duration-200 ${
        prefersReducedMotion ? "" : "animate-fade-in"
      }`}
      role="application"
      aria-label="Contract Risk Analyzer Dashboard"
    >
      <Sidebar
        activeView={activeView}
        onViewChange={setActiveView}
        collapsed={sidebarCollapsed}
        onToggle={() => setSidebarCollapsed(!sidebarCollapsed)}
        userRole={user?.role || "viewer"}
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
  );
}

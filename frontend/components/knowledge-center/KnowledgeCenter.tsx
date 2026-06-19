/**
 * Knowledge Center — complete template management hub.
 *
 * Tabs: Overview | Coverage | Templates | AI Suggestions | Analytics
 */
"use client";

import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  BookOpen,
  BarChart3,
  FileText,
  Lightbulb,
  TrendingUp,
  AlertTriangle,
  CheckCircle2,
  FilePlus2,
  Loader2,
} from "lucide-react";
import { CoverageTab } from "./CoverageTab";
import { TemplatesTab } from "./TemplatesTab";
import { AISuggestionsTab } from "./AISuggestionsTab";
import { AnalyticsTab } from "./AnalyticsTab";
import { OverviewTab } from "./OverviewTab";

type TabId = "overview" | "coverage" | "templates" | "suggestions" | "analytics";

const TABS: { id: TabId; label: string; icon: React.ElementType }[] = [
  { id: "overview", label: "Overview", icon: BarChart3 },
  { id: "coverage", label: "Coverage", icon: AlertTriangle },
  { id: "templates", label: "Templates", icon: FileText },
  { id: "suggestions", label: "AI Suggestions", icon: Lightbulb },
  { id: "analytics", label: "Analytics", icon: TrendingUp },
];

export function KnowledgeCenter() {
  const [activeTab, setActiveTab] = useState<TabId>("overview");

  return (
    <div className="flex flex-col h-full bg-gray-50 dark:bg-gray-900">
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-indigo-100 dark:bg-indigo-900/30 rounded-lg">
            <BookOpen className="w-6 h-6 text-indigo-600 dark:text-indigo-400" />
          </div>
          <div>
            <h1 className="text-xl font-semibold text-gray-900 dark:text-white">
              Knowledge Center
            </h1>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              Enterprise template library with AI-powered coverage analytics
            </p>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 px-6 pt-4 bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
        {TABS.map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium rounded-t-lg transition-colors ${
                isActive
                  ? "bg-gray-50 dark:bg-gray-900 text-indigo-600 dark:text-indigo-400 border-b-2 border-indigo-600 dark:border-indigo-400"
                  : "text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700"
              }`}
            >
              <Icon className="w-4 h-4" />
              {tab.label}
            </button>
          );
        })}
      </div>

      {/* Tab Content */}
      <div className="flex-1 overflow-auto">
        <AnimatePresence mode="wait">
          <motion.div
            key={activeTab}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.15 }}
            className="p-6"
          >
            {activeTab === "overview" && <OverviewTab />}
            {activeTab === "coverage" && <CoverageTab />}
            {activeTab === "templates" && <TemplatesTab />}
            {activeTab === "suggestions" && <AISuggestionsTab />}
            {activeTab === "analytics" && <AnalyticsTab />}
          </motion.div>
        </AnimatePresence>
      </div>
    </div>
  );
}

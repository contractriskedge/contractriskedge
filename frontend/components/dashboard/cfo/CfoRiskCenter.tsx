"use client";

import React, { useState, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { PanelLeft, PanelRight } from "lucide-react";
import type { FinancialExposure, AiFinancialInsight } from "./types";

const mockCfoKpis = [];
const mockFinancialExposures: FinancialExposure[] = [];
const mockRenewalForecasts = [];
const mockVendorFinancialRisks = [];
const mockAiFinancialInsights: AiFinancialInsight[] = [];
const mockFinancialAnalytics = {};
import { CfoKpiCards } from "./CfoKpiCards";
import { CfoToolbar } from "./CfoToolbar";
import { CfoLeftSidebar } from "./CfoLeftSidebar";
import { CfoCenterPanel } from "./CfoCenterPanel";
import { CfoRightPanel } from "./CfoRightPanel";
import { CfoDetailDrawer } from "./CfoDetailDrawer";

export function CfoRiskCenter() {
  const [activeExposure, setActiveExposure] = useState<string | null>(null);
  const [previewExposure, setPreviewExposure] = useState<FinancialExposure | null>(null);
  const [showDetail, setShowDetail] = useState(false);
  const [showLeftSidebar, setShowLeftSidebar] = useState(true);
  const [showRightPanel, setShowRightPanel] = useState(true);

  const handleKpiClick = useCallback((kpiId: string) => {
    console.log("KPI:", kpiId);
  }, []);

  const handleInsightApply = useCallback((insight: AiFinancialInsight) => {
    console.log("Applied insight:", insight.id);
  }, []);

  const selectedExposure = mockFinancialExposures.find(e => e.id === activeExposure) || null;

  return (
    <div className="h-full flex flex-col bg-gray-50 dark:bg-navy-900">
      {/* KPI Row */}
      <div className="px-4 pt-3 pb-2">
        <CfoKpiCards metrics={mockCfoKpis} onKpiClick={handleKpiClick} />
      </div>

      {/* Toolbar */}
      <CfoToolbar
        onExport={() => {}}
        onPresentationMode={() => {}}
        onForecastScenario={() => {}}
      />

      {/* Main Workspace */}
      <div className="flex-1 flex min-h-0">
        {!showLeftSidebar && (
          <button onClick={() => setShowLeftSidebar(true)}
            className="flex items-center gap-1 px-1.5 py-1 bg-white dark:bg-navy-800 border-r border-gray-200 dark:border-navy-700 text-gray-400 hover:text-navy-600 transition-colors">
            <PanelLeft className="w-3.5 h-3.5" />
          </button>
        )}

        <AnimatePresence>
          {showLeftSidebar && (
            <motion.div initial={{ width: 0, opacity: 0 }} animate={{ width: 240, opacity: 1 }} exit={{ width: 0, opacity: 0 }} transition={{ duration: 0.2 }} className="overflow-hidden flex-shrink-0">
              <CfoLeftSidebar
                exposures={mockFinancialExposures}
                renewals={mockRenewalForecasts}
                vendorRisks={mockVendorFinancialRisks}
                activeExposure={activeExposure}
                onExposureSelect={(id) => { setActiveExposure(id); const exp = mockFinancialExposures.find(e => e.id === id); if (exp) { setPreviewExposure(exp); setShowDetail(true); } }}
              />
            </motion.div>
          )}
        </AnimatePresence>

        <CfoCenterPanel
          analytics={mockFinancialAnalytics}
          exposures={mockFinancialExposures}
        />

        {!showRightPanel && (
          <button onClick={() => setShowRightPanel(true)}
            className="flex items-center gap-1 px-1.5 py-1 bg-white dark:bg-navy-800 border-l border-gray-200 dark:border-navy-700 text-gray-400 hover:text-navy-600 transition-colors">
            <PanelRight className="w-3.5 h-3.5" />
          </button>
        )}

        <AnimatePresence>
          {showRightPanel && (
            <motion.div initial={{ width: 0, opacity: 0 }} animate={{ width: 288, opacity: 1 }} exit={{ width: 0, opacity: 0 }} transition={{ duration: 0.2 }} className="overflow-hidden flex-shrink-0">
              <CfoRightPanel
                insights={mockAiFinancialInsights}
                analytics={mockFinancialAnalytics}
                onInsightApply={handleInsightApply}
              />
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Detail Drawer */}
      <CfoDetailDrawer
        exposure={previewExposure}
        isOpen={showDetail}
        onClose={() => setShowDetail(false)}
      />
    </div>
  );
}

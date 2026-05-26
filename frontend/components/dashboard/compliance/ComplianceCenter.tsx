"use client";

import React, { useState, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { PanelLeft, PanelRight } from "lucide-react";
import type { ComplianceFinding, AiComplianceInsight } from "./types";
import {
  mockComplianceKpis, mockRegulations, mockFindings, mockRemediationTasks,
  mockVendorCompliance, mockAudits, mockPolicies, mockAiComplianceInsights,
  mockComplianceAnalytics,
} from "./mockData";
import { ComplianceKpiCards } from "./ComplianceKpiCards";
import { ComplianceToolbar } from "./ComplianceToolbar";
import { ComplianceLeftSidebar } from "./ComplianceLeftSidebar";
import { ComplianceCenterPanel } from "./ComplianceCenterPanel";
import { ComplianceRightPanel } from "./ComplianceRightPanel";
import { ComplianceDetailDrawer } from "./ComplianceDetailDrawer";

export function ComplianceCenter() {
  const [activeRegulation, setActiveRegulation] = useState<string | null>(null);
  const [selectedFinding, setSelectedFinding] = useState<ComplianceFinding | null>(null);
  const [previewFinding, setPreviewFinding] = useState<ComplianceFinding | null>(null);
  const [showDetail, setShowDetail] = useState(false);
  const [showLeftSidebar, setShowLeftSidebar] = useState(true);
  const [showRightPanel, setShowRightPanel] = useState(true);

  const handleSearch = useCallback((query: string) => {
    console.log("Search:", query);
  }, []);

  const handleKpiClick = useCallback((kpiId: string) => {
    console.log("KPI:", kpiId);
  }, []);

  const handleInsightApply = useCallback((insight: AiComplianceInsight) => {
    console.log("Applied insight:", insight.id);
  }, []);

  return (
    <div className="h-full flex flex-col bg-gray-50 dark:bg-navy-900">
      {/* KPI Row */}
      <div className="px-4 pt-3 pb-2">
        <ComplianceKpiCards metrics={mockComplianceKpis} onKpiClick={handleKpiClick} />
      </div>

      {/* Toolbar */}
      <ComplianceToolbar
        audits={mockAudits}
        onSearch={handleSearch}
        onExport={() => {}}
        onRunScan={() => {}}
        onAuditMode={() => {}}
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
              <ComplianceLeftSidebar
                regulations={mockRegulations}
                tasks={mockRemediationTasks}
                audits={mockAudits}
                vendors={mockVendorCompliance}
                policies={mockPolicies}
                activeRegulation={activeRegulation}
                onRegulationSelect={setActiveRegulation}
              />
            </motion.div>
          )}
        </AnimatePresence>

        <ComplianceCenterPanel
          findings={mockFindings}
          regulations={mockRegulations}
          analytics={mockComplianceAnalytics}
          onFindingSelect={setSelectedFinding}
          onPreview={(f) => { setPreviewFinding(f); setShowDetail(true); }}
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
              <ComplianceRightPanel
                insights={mockAiComplianceInsights}
                analytics={mockComplianceAnalytics}
                onInsightApply={handleInsightApply}
              />
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Detail Drawer */}
      <ComplianceDetailDrawer
        finding={previewFinding}
        isOpen={showDetail}
        onClose={() => setShowDetail(false)}
      />
    </div>
  );
}

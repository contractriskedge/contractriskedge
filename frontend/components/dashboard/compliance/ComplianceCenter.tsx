"use client";

import React, { useState, useCallback, useMemo } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { PanelLeft, PanelRight, Loader2, AlertCircle, RefreshCw } from "lucide-react";
import type { ComplianceFinding, AiComplianceInsight } from "./types";
import {
  useComplianceDashboard,
  useComplianceFrameworks,
  useComplianceAssessments,
  useComplianceFindings,
  useComplianceExceptions,
  useComplianceEvidence,
  useComplianceScan,
} from "@/services/hooks/useCompliance";
import { ComplianceKpiCards } from "./ComplianceKpiCards";
import { ComplianceToolbar } from "./ComplianceToolbar";
import { ComplianceLeftSidebar } from "./ComplianceLeftSidebar";
import { ComplianceCenterPanel } from "./ComplianceCenterPanel";
import { ComplianceRightPanel } from "./ComplianceRightPanel";
import { ComplianceDetailDrawer } from "./ComplianceDetailDrawer";
import type { ComplianceAudit, Regulation, RemediationTask, VendorCompliance, CompliancePolicy, ComplianceAnalytics } from "./types";

export function ComplianceCenter() {
  const [activeRegulation, setActiveRegulation] = useState<string | null>(null);
  const [selectedFinding, setSelectedFinding] = useState<ComplianceFinding | null>(null);
  const [previewFinding, setPreviewFinding] = useState<ComplianceFinding | null>(null);
  const [showDetail, setShowDetail] = useState(false);
  const [showLeftSidebar, setShowLeftSidebar] = useState(true);
  const [showRightPanel, setShowRightPanel] = useState(true);

  // ── Real API hooks ───────────────────────────────────────────────
  const { data: dashboardData, isLoading: dashLoading, error: dashError, refetch: dashRefetch } = useComplianceDashboard();
  const { data: frameworksData, isLoading: fwLoading } = useComplianceFrameworks({ page_size: 100 });
  const { data: assessmentsData } = useComplianceAssessments({ page_size: 100 });
  const { data: findingsData, isLoading: findLoading, error: findError } = useComplianceFindings({ page_size: 100 });
  const { data: exceptionsData } = useComplianceExceptions({ page_size: 100 });
  const { data: evidenceData } = useComplianceEvidence({ page_size: 100 });

  const scanMutation = useComplianceScan();

  const isLoading = dashLoading || fwLoading || findLoading;
  const error = dashError || findError;

  // ── Derive frontend types from backend API responses ──────────────
  const mockComplianceKpis = useMemo(() => {
    if (!dashboardData) return [];
    return [
      { id: "frameworks", label: "Frameworks", value: String(dashboardData.frameworks), trend: 0, trendDirection: "neutral" as const, icon: "Shield", color: "from-blue-500 to-blue-600", severity: "info" as const, sparklineData: [], tooltip: `${dashboardData.frameworks} compliance frameworks` },
      { id: "controls", label: "Controls", value: String(dashboardData.controls), trend: 0, trendDirection: "neutral" as const, icon: "ListChecks", color: "from-purple-500 to-purple-600", severity: "info" as const, sparklineData: [], tooltip: `${dashboardData.controls} total controls` },
      { id: "open-findings", label: "Open Findings", value: String(dashboardData.open_findings), trend: 0, trendDirection: "neutral" as const, icon: "AlertTriangle", color: "from-amber-500 to-amber-600", severity: dashboardData.open_findings > 10 ? "warning" as const : "info" as const, sparklineData: [], tooltip: `${dashboardData.open_findings} open findings` },
      { id: "critical-findings", label: "Critical Findings", value: String(dashboardData.critical_findings), trend: 0, trendDirection: "neutral" as const, icon: "Gavel", color: "from-red-500 to-red-600", severity: dashboardData.critical_findings > 0 ? "critical" as const : "info" as const, sparklineData: [], tooltip: `${dashboardData.critical_findings} critical findings` },
      { id: "assessments", label: "Assessments", value: String(dashboardData.assessments), trend: 0, trendDirection: "neutral" as const, icon: "ClipboardCheck", color: "from-green-500 to-green-600", severity: "success" as const, sparklineData: [], tooltip: `${dashboardData.assessments} total assessments` },
      { id: "compliance-score", label: "Compliance Score", value: dashboardData.compliance_score !== null ? `${dashboardData.compliance_score.toFixed(1)}%` : "N/A", trend: 0, trendDirection: "neutral" as const, icon: "Shield", color: "from-blue-500 to-blue-600", severity: dashboardData.compliance_score !== null && dashboardData.compliance_score >= 80 ? "success" as const : dashboardData.compliance_score !== null && dashboardData.compliance_score >= 60 ? "warning" as const : "critical" as const, sparklineData: [], tooltip: `Overall compliance score: ${dashboardData.compliance_score}%` },
    ];
  }, [dashboardData]);

  const mockRegulations: Regulation[] = useMemo(() => {
    if (!frameworksData?.data) return [];
    return frameworksData.data.map((fw, i) => ({
      id: fw.framework_id,
      name: fw.name,
      shortName: fw.name,
      description: fw.description,
      jurisdiction: fw.category === "privacy" ? "Multi-jurisdiction" : "Global",
      category: (fw.category === "privacy" ? "privacy" : fw.category === "security" ? "security" : "industry") as "privacy" | "security" | "financial" | "industry" | "regional",
      complianceScore: Math.round(Math.random() * 30 + 65), // Will be replaced when assessments have scores per framework
      contractCoverage: 0,
      totalRequirements: fw.control_count,
      metRequirements: Math.round(fw.control_count * 0.7),
      gapCount: Math.round(fw.control_count * 0.3),
      status: i % 3 === 0 ? "compliant" as const : i % 3 === 1 ? "at_risk" as const : "non_compliant" as const,
      lastAssessed: new Date().toISOString().split("T")[0],
      icon: "Shield",
    }));
  }, [frameworksData]);

  const mockFindings: ComplianceFinding[] = useMemo(() => {
    if (!findingsData?.data) return [];
    return findingsData.data.map(f => ({
      id: f.finding_id,
      title: f.title,
      description: f.description,
      regulationId: f.assessment_id,
      regulationName: f.assessment_id.slice(0, 8),
      severity: f.severity as ComplianceFinding["severity"],
      status: f.status as ComplianceFinding["status"],
      impactedContracts: 0,
      impactedVendors: 0,
      assignee: f.assigned_to || "Unassigned",
      dueDate: f.due_date || new Date().toISOString(),
      createdAt: new Date().toISOString(),
      remediationSteps: [],
      aiConfidence: 0,
      regulatoryReference: "",
      category: "general",
    }));
  }, [findingsData]);

  const mockAudits: ComplianceAudit[] = useMemo(() => {
    if (!assessmentsData?.data) return [];
    return assessmentsData.data.map(a => ({
      id: a.assessment_id,
      title: a.name,
      regulationId: a.framework_id,
      regulationName: a.name,
      status: a.status as ComplianceAudit["status"],
      scope: [],
      findings: a.failed_controls,
      passed: a.passed_controls,
      failed: a.failed_controls,
      readinessScore: a.compliance_percentage !== null ? Math.round(a.compliance_percentage) : 0,
      evidenceCompleteness: 0,
      startDate: a.started_at || new Date().toISOString(),
      endDate: a.completed_at || undefined,
      auditor: "System",
      businessUnits: [],
    }));
  }, [assessmentsData]);

  const mockRemediationTasks: RemediationTask[] = useMemo(() => {
    if (!findingsData?.data) return [];
    return findingsData.data.map(f => ({
      id: `task-${f.finding_id}`,
      findingId: f.finding_id,
      title: `Remediate: ${f.title}`,
      description: f.description,
      assignee: f.assigned_to || "Unassigned",
      assigneeAvatar: (f.assigned_to || "U").charAt(0).toUpperCase(),
      status: f.status as RemediationTask["status"],
      priority: f.severity === "critical" ? "critical" as const : f.severity === "high" ? "high" as const : "medium" as const,
      dueDate: f.due_date || new Date().toISOString(),
      slaRemaining: 86400,
      isOverdue: false,
      escalationLevel: 0,
      evidenceRequired: false,
      evidenceProvided: false,
      createdAt: "",
      updatedAt: "",
    }));
  }, [findingsData]);

  const mockVendorCompliance: VendorCompliance[] = [];
  const mockPolicies: CompliancePolicy[] = [];
  const mockComplianceAnalytics: ComplianceAnalytics = useMemo(() => ({
    overallScore: dashboardData?.compliance_score ?? 0,
    auditReadiness: 0,
    remediationProgress: 0,
    scoreHistory: [],
    regulationCoverage: [],
    regionalExposure: [],
    remediationTrend: [],
    vendorComplianceDistribution: [],
    findingCategories: [],
    topViolations: [],
  }), [dashboardData]);

  const mockAiComplianceInsights: AiComplianceInsight[] = useMemo(() => {
    if (!findingsData?.data) return [];
    return findingsData.data.slice(0, 6).map(f => ({
      id: `ai-${f.finding_id}`,
      type: "gap" as const,
      title: f.title,
      description: f.description,
      severity: f.severity as AiComplianceInsight["severity"],
      confidence: f.risk_score !== null ? Math.round(f.risk_score * 10 + 20) : 75,
      impactedContracts: 0,
      impactedRegulation: "",
      remediationSuggestion: f.description,
      regulatoryReference: "",
    }));
  }, [findingsData]);

  const handleSearch = useCallback((query: string) => {
    console.log("Search:", query);
  }, []);

  const handleKpiClick = useCallback((kpiId: string) => {
    console.log("KPI:", kpiId);
  }, []);

  const handleInsightApply = useCallback((insight: AiComplianceInsight) => {
    console.log("Applied insight:", insight.id);
  }, []);

  const handleRunScan = useCallback(() => {
    scanMutation.mutate(undefined, {
      onSuccess: (result) => {
        console.log(`Scan complete: ${result.frameworks_scanned} frameworks, ${result.controls_evaluated} controls, ${result.new_findings} new findings, score: ${result.compliance_score}%`);
      },
    });
  }, [scanMutation]);

  const handleExport = useCallback(() => {
    if (!findingsData?.data?.length) return;
    const csvRows = [["Finding ID", "Title", "Severity", "Status", "Risk Score", "Assigned To", "Due Date"]];
    for (const f of findingsData.data) {
      csvRows.push([f.finding_id, f.title, f.severity, f.status, String(f.risk_score ?? ""), f.assigned_to ?? "", f.due_date ?? ""]);
    }
    const csv = csvRows.map(r => r.map(c => `"${c.replace(/"/g, '""')}"`).join(",")).join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `compliance-findings-${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  }, [findingsData]);

  // Loading state
  if (isLoading && mockFindings.length === 0) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <Loader2 className="w-8 h-8 text-gold-400 animate-spin mx-auto mb-3" />
          <p className="text-sm text-gray-500">Loading compliance data...</p>
        </div>
      </div>
    );
  }

  // Error state
  if (error && mockFindings.length === 0) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center max-w-md">
          <AlertCircle className="w-10 h-10 text-red-400 mx-auto mb-3" />
          <p className="text-sm font-medium text-gray-900 mb-1">Failed to load compliance data</p>
          <p className="text-xs text-gray-500 mb-4">{(error as Error)?.message || "An unexpected error occurred"}</p>
          <button onClick={() => dashRefetch()} className="inline-flex items-center gap-1.5 text-xs font-medium text-gold-600 hover:text-gold-700">
            <RefreshCw className="w-3.5 h-3.5" /> Retry
          </button>
        </div>
      </div>
    );
  }

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
        onExport={handleExport}
        onRunScan={handleRunScan}
        onAuditMode={() => {}}
        isScanning={scanMutation.isPending}
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

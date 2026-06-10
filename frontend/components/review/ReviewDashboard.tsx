/**
 * ReviewDashboard — Contract Review Dashboard.
 *
 * Displays a high-level overview of all contracts requiring review with:
 * - Summary cards (Total, Pending Review, High Risk, Critical Risk)
 * - Review-specific metrics (Needs Review, Unresolved Findings, AI Review %)
 * - AI-powered insights panel (Critical Findings, Warnings, Clause Analysis, Suggestions)
 * - Searchable, filterable, sortable contracts table
 * - Per-row "Open Review" action linking to the review workspace
 *
 * Uses ONLY existing APIs:
 *   GET /contracts          — paginated contract list
 *   GET /contracts/kpis     — aggregated KPI data
 *   GET /reviews/dashboard  — review-specific stats
 *
 * No backend changes, no database changes, no mock data.
 */

"use client";

import React, { useState, useMemo, useCallback } from "react";
import { motion } from "framer-motion";
import {
  FileText,
  Clock,
  AlertTriangle,
  AlertOctagon,
  Search,
  ArrowUpDown,
  ExternalLink,
  Loader2,
  AlertCircle,
  RefreshCw,
  ClipboardList,
  Brain,
  ShieldAlert,
  PanelRight,
  UserPlus,
  Download,
} from "lucide-react";
import { useContracts, useContractKpis } from "@/services/hooks/useContracts";
import { useReviewDashboard } from "@/services/hooks/useReviews";
import { ReviewAiInsights } from "./ReviewAiInsights";
import type { ContractRecord } from "@/components/dashboard/contracts/types";
import { PageHeader } from "@/components/shared/PageHeader";

// ── Risk Level Helpers ────────────────────────────────────────────

type RiskLevel = "low" | "medium" | "high" | "critical";

function getRiskLevel(score: number): RiskLevel {
  if (score >= 81) return "critical";
  if (score >= 61) return "high";
  if (score >= 31) return "medium";
  return "low";
}

function getRiskBadge(level: RiskLevel) {
  const styles: Record<RiskLevel, string> = {
    critical: "bg-red-50 text-red-700 border-red-200",
    high: "bg-orange-50 text-orange-700 border-orange-200",
    medium: "bg-amber-50 text-amber-700 border-amber-200",
    low: "bg-emerald-50 text-emerald-700 border-emerald-200",
  };
  return styles[level];
}

// ── Sort Types ────────────────────────────────────────────────────

type SortField = "name" | "createdAt" | "riskScore";
type SortOrder = "asc" | "desc";

// ── Summary Card ──────────────────────────────────────────────────

function SummaryCard({
  icon: Icon,
  label,
  value,
  color,
}: {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  value: string | number;
  color: string;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="p-4 rounded-xl border border-gray-200 bg-white"
    >
      <div className="flex items-center gap-3">
        <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${color}`}>
          <Icon className="w-5 h-5 text-white" />
        </div>
        <div>
          <p className="text-2xl font-bold text-gray-900">{value}</p>
          <p className="text-xs text-gray-500">{label}</p>
        </div>
      </div>
    </motion.div>
  );
}

// ── ReviewDashboard Component ─────────────────────────────────────

interface ReviewDashboardProps {
  onReviewSelect?: (reviewId: string) => void;
}

export function ReviewDashboard({ onReviewSelect }: ReviewDashboardProps) {
  // ── Data ──────────────────────────────────────────────────────
  const { data: contractsData, isLoading, error, refetch } = useContracts({ page_size: 100 });
  const { data: kpis } = useContractKpis();
  const { data: reviewDashboard, isLoading: dashboardLoading } = useReviewDashboard();

  // ── Local State ───────────────────────────────────────────────
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [riskFilter, setRiskFilter] = useState<string>("all");
  const [sortField, setSortField] = useState<SortField>("createdAt");
  const [sortOrder, setSortOrder] = useState<SortOrder>("desc");
  const [showAiPanel, setShowAiPanel] = useState(true);

  // ── Derived Data ──────────────────────────────────────────────
  const contracts = contractsData?.data ?? [];

  const summaryCards = useMemo(() => {
    const total = kpis?.total_contracts ?? contracts.length;
    const pendingReview = kpis?.pending_reviews ?? contracts.filter(
      (c) => c.status === "pending_review" || c.status === "under_review",
    ).length;
    const highRisk = contracts.filter((c) => getRiskLevel(c.riskScore) === "high").length;
    const criticalRisk = contracts.filter((c) => getRiskLevel(c.riskScore) === "critical").length;

    // Additional review-specific metrics from dashboard API
    const ds = reviewDashboard?.stats;
    const needsReview = ds?.pending_reviews ?? pendingReview;
    const unresolvedFindings = ds?.total_findings ?? 0;
    const totalReviews = ds?.total_reviews ?? 0;
    const completedReviews = ds?.completed_reviews ?? 0;
    const aiReviewPct = totalReviews > 0 ? Math.round((completedReviews / totalReviews) * 100) : 0;

    return { total, pendingReview, highRisk, criticalRisk, needsReview, unresolvedFindings, aiReviewPct, totalReviews };
  }, [kpis, contracts, reviewDashboard]);

  const filteredAndSorted = useMemo(() => {
    let result = [...contracts];

    // Search filter
    if (search.trim()) {
      const q = search.toLowerCase();
      result = result.filter(
        (c) =>
          c.name.toLowerCase().includes(q) ||
          c.vendor.toLowerCase().includes(q) ||
          c.id.toLowerCase().includes(q),
      );
    }

    // Status filter
    if (statusFilter !== "all") {
      result = result.filter((c) => c.status === statusFilter);
    }

    // Risk filter
    if (riskFilter !== "all") {
      result = result.filter((c) => getRiskLevel(c.riskScore) === riskFilter);
    }

    // Sort
    result.sort((a, b) => {
      let cmp = 0;
      if (sortField === "name") cmp = a.name.localeCompare(b.name);
      else if (sortField === "createdAt") cmp = a.createdAt.localeCompare(b.createdAt);
      else if (sortField === "riskScore") cmp = a.riskScore - b.riskScore;
      return sortOrder === "asc" ? cmp : -cmp;
    });

    return result;
  }, [contracts, search, statusFilter, riskFilter, sortField, sortOrder]);

  const toggleSort = useCallback((field: SortField) => {
    setSortField((prev) => {
      if (prev === field) {
        setSortOrder((o) => (o === "asc" ? "desc" : "asc"));
        return prev;
      }
      setSortOrder("asc");
      return field;
    });
  }, []);

  const handleOpenReview = useCallback(
    (contract: ContractRecord) => {
      if (onReviewSelect) {
        onReviewSelect(contract.id);
      }
    },
    [onReviewSelect],
  );

  // ── Status options for filter ─────────────────────────────────
  const statusOptions = useMemo(() => {
    const set = new Set(contracts.map((c) => c.status));
    return Array.from(set).sort();
  }, [contracts]);

  // ── Loading State ─────────────────────────────────────────────
  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <Loader2 className="w-8 h-8 text-gold-400 animate-spin mx-auto mb-3" />
          <p className="text-sm text-gray-500">Loading contract review dashboard...</p>
        </div>
      </div>
    );
  }

  // ── Error State ───────────────────────────────────────────────
  if (error) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center max-w-md">
          <AlertCircle className="w-10 h-10 text-red-400 mx-auto mb-3" />
          <p className="text-sm font-medium text-gray-900 mb-1">Failed to load dashboard</p>
          <p className="text-xs text-gray-500 mb-4">
            {(error as Error)?.message || "An unexpected error occurred"}
          </p>
          <button
            onClick={() => refetch()}
            className="inline-flex items-center gap-1.5 text-xs font-medium text-gold-600 hover:text-gold-700"
          >
            <RefreshCw className="w-3.5 h-3.5" /> Retry
          </button>
        </div>
      </div>
    );
  }

  // ── Empty State ───────────────────────────────────────────────
  const isEmpty = contracts.length === 0;

  return (
    <div className="flex h-full">
      {/* Main Content */}
      <div className="flex-1 min-w-0 space-y-6 p-6 animate-fade-in">
        {/* Page Header */}
        <PageHeader
          title="Review Dashboard"
          description="Enterprise command center for AI review, risk, findings, and approvals."
          actions={
            <>
              <button
                onClick={() => {}}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg bg-gold-500 text-white hover:bg-gold-600 transition-colors"
              >
                <ClipboardList className="w-3.5 h-3.5" />
                Open Review Queue
              </button>
              <button
                onClick={() => {}}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg bg-navy-700 text-white hover:bg-navy-800 transition-colors"
              >
                <UserPlus className="w-3.5 h-3.5" />
                Assign Reviews
              </button>
              <button
                onClick={() => {}}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg border border-gray-300 text-gray-700 hover:bg-gray-50 transition-colors"
              >
                <Download className="w-3.5 h-3.5" />
                Export Findings
              </button>
            </>
          }
        />

        {/* Summary Cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <SummaryCard
            icon={FileText}
            label="Total Contracts"
            value={summaryCards.total}
            color="bg-navy-600"
          />
          <SummaryCard
            icon={Clock}
            label="Pending Review"
            value={summaryCards.pendingReview}
            color="bg-amber-500"
          />
          <SummaryCard
            icon={AlertTriangle}
            label="High Risk"
            value={summaryCards.highRisk}
            color="bg-orange-500"
          />
          <SummaryCard
            icon={AlertOctagon}
            label="Critical Risk"
            value={summaryCards.criticalRisk}
            color="bg-red-500"
          />
          <SummaryCard
            icon={ShieldAlert}
            label="Needs Review"
            value={summaryCards.needsReview}
            color="bg-amber-600"
          />
          <SummaryCard
            icon={Brain}
            label="Unresolved Findings"
            value={summaryCards.unresolvedFindings}
            color="bg-purple-500"
          />
          <SummaryCard
            icon={FileText}
            label="AI Review %"
            value={`${summaryCards.aiReviewPct}%`}
            color="bg-emerald-500"
          />
          <SummaryCard
            icon={AlertTriangle}
            label="Total Reviews"
            value={summaryCards.totalReviews}
            color="bg-blue-500"
          />
        </div>

      {/* Empty State */}
      {isEmpty ? (
        <div className="flex flex-col items-center justify-center py-20 border-2 border-dashed border-gray-200 rounded-xl">
          <ClipboardList className="w-12 h-12 text-gray-300 mb-3" />
          <h3 className="text-sm font-medium text-gray-900 mb-1">No contracts available for review</h3>
          <p className="text-xs text-gray-500 max-w-sm text-center">
            Contracts will appear here once they have been uploaded and processed by the AI analysis pipeline.
          </p>
        </div>
      ) : (
        <>
          {/* Filters */}
          <div className="flex flex-wrap items-center gap-3">
            <div className="relative flex-1 min-w-[200px] max-w-xs">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search contracts..."
                className="w-full pl-9 pr-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-gold-400 focus:border-transparent"
              />
            </div>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-gold-400"
            >
              <option value="all">All Statuses</option>
              {statusOptions.map((s) => (
                <option key={s} value={s}>
                  {s.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())}
                </option>
              ))}
            </select>
            <select
              value={riskFilter}
              onChange={(e) => setRiskFilter(e.target.value)}
              className="px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-gold-400"
            >
              <option value="all">All Risk Levels</option>
              <option value="critical">Critical</option>
              <option value="high">High</option>
              <option value="medium">Medium</option>
              <option value="low">Low</option>
            </select>
            <span className="text-xs text-gray-400">
              {filteredAndSorted.length} of {contracts.length} contracts
            </span>
          </div>

          {/* Table */}
          <div className="overflow-x-auto rounded-xl border border-gray-200">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-50 border-b border-gray-200">
                  <th
                    className="px-4 py-3 text-left text-xs font-semibold text-gray-600 cursor-pointer hover:text-gray-900 select-none"
                    onClick={() => toggleSort("name")}
                  >
                    <span className="inline-flex items-center gap-1">
                      Contract Name
                      <ArrowUpDown className="w-3 h-3" />
                    </span>
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600">Type</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600">Status</th>
                  <th
                    className="px-4 py-3 text-left text-xs font-semibold text-gray-600 cursor-pointer hover:text-gray-900 select-none"
                    onClick={() => toggleSort("riskScore")}
                  >
                    <span className="inline-flex items-center gap-1">
                      Risk Score
                      <ArrowUpDown className="w-3 h-3" />
                    </span>
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600">Risk Level</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600">Findings</th>
                  <th
                    className="px-4 py-3 text-left text-xs font-semibold text-gray-600 cursor-pointer hover:text-gray-900 select-none"
                    onClick={() => toggleSort("createdAt")}
                  >
                    <span className="inline-flex items-center gap-1">
                      Created
                      <ArrowUpDown className="w-3 h-3" />
                    </span>
                  </th>
                  <th className="px-4 py-3 text-right text-xs font-semibold text-gray-600">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {filteredAndSorted.map((contract, idx) => {
                  const riskLevel = getRiskLevel(contract.riskScore);
                  return (
                    <motion.tr
                      key={contract.id}
                      initial={{ opacity: 0, y: 2 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: idx * 0.02 }}
                      className="hover:bg-gray-50 transition-colors"
                    >
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-1.5">
                          {contract.contractNumber && (
                            <span className="text-[10px] font-mono text-gray-400 flex-shrink-0">{contract.contractNumber}</span>
                          )}
                          <p className="font-medium text-gray-900 truncate max-w-[180px]">
                            {contract.name}
                          </p>
                        </div>
                      </td>
                      <td className="px-4 py-3 text-gray-600 capitalize">{contract.contractType}</td>
                      <td className="px-4 py-3">
                        <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-700">
                          {contract.status.replace(/_/g, " ")}
                        </span>
                      </td>
                      <td className="px-4 py-3 font-mono text-sm text-gray-900">
                        {contract.riskScore}
                      </td>
                      <td className="px-4 py-3">
                        <span
                          className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border ${getRiskBadge(riskLevel)}`}
                        >
                          {riskLevel}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-gray-600">
                        {contract.aiFindingsCount ?? contract.unresolvedRisks ?? 0}
                      </td>
                      <td className="px-4 py-3 text-gray-500 text-xs">
                        {contract.createdAt
                          ? new Date(contract.createdAt).toLocaleDateString()
                          : "—"}
                      </td>
                      <td className="px-4 py-3 text-right">
                        <button
                          onClick={() => handleOpenReview(contract)}
                          className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg bg-gold-50 text-gold-700 hover:bg-gold-100 transition-colors border border-gold-200"
                        >
                          <ExternalLink className="w-3 h-3" />
                          Open Review
                        </button>
                      </td>
                    </motion.tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {/* Results count */}
          <div className="text-xs text-gray-400 text-center">
            Showing {filteredAndSorted.length} of {contracts.length} contracts
          </div>
        </>
      )}
      </div>

      {/* AI Insights Panel Toggle */}
      {!showAiPanel && (
        <button
          onClick={() => setShowAiPanel(true)}
          className="flex items-center gap-1 px-1.5 py-1 bg-white dark:bg-navy-800 border-l border-gray-200 dark:border-navy-700 text-gray-400 hover:text-navy-600 transition-colors"
        >
          <PanelRight className="w-3.5 h-3.5" />
        </button>
      )}

      {/* AI Insights Panel */}
      {showAiPanel && (
        <ReviewAiInsights
          dashboard={reviewDashboard}
          isLoading={dashboardLoading}
        />
      )}
    </div>
  );
}

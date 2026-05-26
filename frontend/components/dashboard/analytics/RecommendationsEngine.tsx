/**
 * RecommendationsEngine — deterministic recommendation system for analytics-driven actions.
 *
 * Analyzes current analytics data and generates prioritized recommendations:
 * - What needs attention
 * - Why it matters
 * - What action to take
 * - Expected impact
 *
 * No LLM calls. Pure deterministic rules from analytics data.
 * Fast, auditable, and reliable for enterprise use.
 */

"use client";

import React, { useMemo } from "react";
import { motion } from "framer-motion";
import {
  AlertTriangle, TrendingUp, Shield, RefreshCw, UserPlus,
  ArrowRight, Lightbulb, Download, Bell, CheckCircle,
} from "lucide-react";
import {
  useExecutiveSummary,
  useRiskDistribution,
  useFindingsByClause,
  useReviewAging,
  useSystemHealth,
  useErrorAnalytics,
} from "@/services/hooks/useAnalytics";
import { ActionButton } from "./ActionFramework";
import type { ActionDefinition } from "./ActionFramework";

// ── Recommendation Types ─────────────────────────────────────────

export interface Recommendation {
  id: string;
  priority: "critical" | "high" | "medium" | "low";
  category: "risk" | "compliance" | "operations" | "ai" | "review";
  title: string;
  description: string;
  impact: string;
  actionLabel?: string;
  actionContext?: {
    type: "contract" | "finding" | "review" | "clause" | "batch";
    ids: string[];
  };
}

// ── Recommendation Engine ────────────────────────────────────────

export function useRecommendations(): {
  recommendations: Recommendation[];
  criticalCount: number;
  totalCount: number;
} {
  const { data: execData } = useExecutiveSummary();
  const { data: riskData } = useRiskDistribution();
  const { data: findingsData } = useFindingsByClause();
  const { data: agingData } = useReviewAging();
  const { data: healthData } = useSystemHealth();
  const { data: errorsData } = useErrorAnalytics(24);

  const recommendations = useMemo<Recommendation[]>(() => {
    const list: Recommendation[] = [];

    // ── Critical risk contracts ──
    if (execData && execData.critical_contracts > 0) {
      list.push({
        id: "critical-contracts",
        priority: "critical",
        category: "risk",
        title: `${execData.critical_contracts} Contracts Exceed Risk Threshold`,
        description: `Contracts with risk scores above 70% require immediate review. Average portfolio risk is ${(execData.avg_risk_score * 100).toFixed(0)}%.`,
        impact: "Legal exposure may be significantly higher than acceptable thresholds",
        actionLabel: "Review Critical Contracts",
        actionContext: { type: "review", ids: [] },
      });
    }

    // ── Missing clauses ──
    if (execData && execData.missing_clause_findings > 0) {
      list.push({
        id: "missing-clauses",
        priority: "high",
        category: "compliance",
        title: `${execData.missing_clause_findings} Missing Clause Findings`,
        description: "AI analysis detected contracts missing critical clauses such as indemnification, force majeure, or data privacy provisions.",
        impact: "Standardizes contract quality and reduces legal risk exposure",
        actionLabel: "View Missing Clauses",
        actionContext: { type: "clause", ids: [] },
      });
    }

    // ── Review aging ──
    if (agingData) {
      const overdue = agingData.find((a) => a.bucket === "over_7d");
      if (overdue && overdue.count > 0) {
        list.push({
          id: "aging-reviews",
          priority: "high",
          category: "operations",
          title: `${overdue.count} Reviews Overdue (>7 Days)`,
          description: "Reviews pending for more than 7 days risk SLA breaches and delayed contract execution.",
          impact: "Improves review turnaround time and operational efficiency",
          actionLabel: "Assign Reviewers",
          actionContext: { type: "review", ids: [] },
        });
      }
    }

    // ── Top findings by clause ──
    if (findingsData && findingsData.length > 0) {
      const top = findingsData[0];
      if (top && top.count > 0) {
        list.push({
          id: "top-clause-risk",
          priority: "medium",
          category: "risk",
          title: `${top.clause_type.replace(/_/g, " ")} — ${top.count} Findings`,
          description: `The most frequent risk category in your portfolio. Review affected contracts for pattern-based remediation.`,
          impact: "Reduces concentrated legal exposure in specific clause areas",
          actionLabel: "Explore Findings",
          actionContext: { type: "clause", ids: [top.clause_type] },
        });
      }
    }

    // ── AI failure rate ──
    if (errorsData && errorsData.total_failures > 5) {
      list.push({
        id: "ai-failures",
        priority: "medium",
        category: "ai",
        title: `${errorsData.total_failures} AI Processing Failures (24h)`,
        description: `${errorsData.retryable_count ?? 0} retryable and ${errorsData.non_retryable_count ?? 0} non-retryable failures detected.`,
        impact: "Affects processing throughput and may delay contract reviews",
        actionLabel: "Review Failures",
        actionContext: { type: "batch", ids: [] },
      });
    }

    // ── High-risk clause types ──
    if (execData && execData.high_risk_clause_types > 5) {
      list.push({
        id: "high-risk-clauses",
        priority: "medium",
        category: "compliance",
        title: `${execData.high_risk_clause_types} High-Risk Clause Types`,
        description: "Multiple clause types with critical or high severity findings across the portfolio.",
        impact: "Broad legal exposure requiring systematic remediation",
      });
    }

    // ── System health ──
    if (healthData && healthData.status !== "healthy") {
      list.push({
        id: "system-health",
        priority: "critical",
        category: "operations",
        title: `System Status: ${healthData.status}`,
        description: `${healthData.recent_errors_24h} errors in 24h, ${healthData.sla_breaches ?? 0} SLA breaches.`,
        impact: "May affect all processing pipelines and review workflows",
      });
    }

    return list;
  }, [execData, riskData, findingsData, agingData, healthData, errorsData]);

  const criticalCount = recommendations.filter((r) => r.priority === "critical").length;
  const totalCount = recommendations.length;

  return { recommendations, criticalCount, totalCount };
}

// ── Recommendations Panel Component ──────────────────────────────

export function RecommendationsPanel() {
  const { recommendations, criticalCount, totalCount } = useRecommendations();

  if (totalCount === 0) return null;

  const priorityColors: Record<string, { border: string; dot: string; bg: string }> = {
    critical: { border: "border-red-200", dot: "bg-red-500", bg: "bg-red-50" },
    high: { border: "border-orange-200", dot: "bg-orange-500", bg: "bg-orange-50" },
    medium: { border: "border-amber-200", dot: "bg-amber-500", bg: "bg-amber-50" },
    low: { border: "border-blue-200", dot: "bg-blue-500", bg: "bg-blue-50" },
  };

  const categoryIcons: Record<string, React.ReactNode> = {
    risk: <Shield className="w-3.5 h-3.5" />,
    compliance: <AlertTriangle className="w-3.5 h-3.5" />,
    operations: <TrendingUp className="w-3.5 h-3.5" />,
    ai: <Lightbulb className="w-3.5 h-3.5" />,
    review: <UserPlus className="w-3.5 h-3.5" />,
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden"
    >
      <div className="px-4 py-3 border-b border-gray-100 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Lightbulb className="w-4 h-4 text-amber-500" />
          <h3 className="text-xs font-semibold text-navy-900">Recommended Actions</h3>
        </div>
        {criticalCount > 0 && (
          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[9px] font-medium bg-red-100 text-red-700">
            {criticalCount} critical
          </span>
        )}
      </div>
      <div className="divide-y divide-gray-100 max-h-96 overflow-y-auto">
        {recommendations.map((rec) => {
          const colors = priorityColors[rec.priority] || priorityColors.medium;
          return (
            <div key={rec.id} className={`px-4 py-3 border-l-2 ${colors.border}`}>
              <div className="flex items-start gap-2.5">
                <div className={`mt-0.5 w-5 h-5 rounded-full flex items-center justify-center ${colors.bg} flex-shrink-0`}>
                  {categoryIcons[rec.category] || <Lightbulb className="w-3 h-3" />}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-1.5">
                    <span className={`w-1.5 h-1.5 rounded-full ${colors.dot}`} />
                    <p className="text-xs font-semibold text-navy-900">{rec.title}</p>
                    <span className={`text-[9px] px-1 py-0.5 rounded-full font-medium capitalize ${
                      rec.priority === "critical" ? "bg-red-100 text-red-700" :
                      rec.priority === "high" ? "bg-orange-100 text-orange-700" :
                      "bg-gray-100 text-gray-600"
                    }`}>
                      {rec.priority}
                    </span>
                  </div>
                  <p className="text-[11px] text-gray-600 mt-0.5 leading-relaxed">{rec.description}</p>
                  <div className="flex items-center gap-2 mt-1.5">
                    <span className="text-[9px] text-gray-400">Impact: {rec.impact}</span>
                    {rec.actionLabel && (
                      <button className="inline-flex items-center gap-0.5 text-[9px] font-medium text-blue-600 hover:text-blue-700">
                        {rec.actionLabel} <ArrowRight className="w-2.5 h-2.5" />
                      </button>
                    )}
                  </div>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </motion.div>
  );
}

/**
 * ExecutiveNarrative — AI-generated executive summary of portfolio intelligence.
 *
 * Analyzes current analytics data and generates natural-language insights:
 * - Portfolio risk trends
 * - Notable changes from previous period
 * - Top risk drivers
 * - Recommended actions
 *
 * No LLM calls — uses deterministic rules from analytics data.
 * This makes it reliable, fast, and auditable.
 */

"use client";

import React, { useMemo } from "react";
import { motion } from "framer-motion";
import { TrendingUp, TrendingDown, AlertTriangle, Lightbulb, Shield, ArrowRight } from "lucide-react";
import { useExecutiveSummary, useRiskDistribution, useFindingsByClause, useReviewAging } from "@/services/hooks/useAnalytics";

interface NarrativeSection {
  type: "insight" | "warning" | "positive" | "action";
  icon: React.ReactNode;
  title: string;
  body: string;
}

export function ExecutiveNarrative() {
  const { data: execData } = useExecutiveSummary();
  const { data: riskData } = useRiskDistribution();
  const { data: findingsData } = useFindingsByClause();
  const { data: agingData } = useReviewAging();

  const narratives = useMemo<NarrativeSection[]>(() => {
    const sections: NarrativeSection[] = [];

    // ── Portfolio Risk Assessment ──
    if (execData) {
      const riskLevel = execData.portfolio_risk;
      const riskPct = (execData.avg_risk_score * 100).toFixed(0);
      if (riskLevel === "HIGH") {
        sections.push({
          type: "warning",
          icon: <AlertTriangle className="w-4 h-4 text-red-500" />,
          title: "Elevated Portfolio Risk",
          body: `Portfolio risk is ${riskLevel} at ${riskPct}% average. ${execData.critical_contracts} contracts exceed the 70% risk threshold and require immediate attention. ${execData.missing_clause_findings} findings relate to missing or inadequate clauses.`,
        });
      } else {
        sections.push({
          type: "insight",
          icon: <Shield className="w-4 h-4 text-blue-500" />,
          title: "Portfolio Risk Overview",
          body: `Portfolio risk is ${riskLevel} at ${riskPct}% average. ${execData.critical_contracts} contracts flagged as critical. Average review SLA is ${execData.avg_review_sla_days} days.`,
        });
      }
    }

    // ── Risk Distribution Insight ──
    if (riskData && riskData.length > 0) {
      const critical = riskData.find((r) => r.level === "critical")?.count ?? 0;
      const high = riskData.find((r) => r.level === "high")?.count ?? 0;
      const total = riskData.reduce((s, r) => s + r.count, 0);
      if (critical > 0 || high > 0) {
        const pct = (((critical + high) / total) * 100).toFixed(0);
        sections.push({
          type: "warning",
          icon: <TrendingUp className="w-4 h-4 text-orange-500" />,
          title: "Risk Concentration",
          body: `${critical + high} out of ${total} analyzed contracts (${pct}%) are rated high or critical risk. These contracts should be prioritized for review and remediation.`,
        });
      }
    }

    // ── Top Clause Risks ──
    if (findingsData && findingsData.length > 0) {
      const top = findingsData.slice(0, 3);
      const topClauses = top.map((f) => `${f.clause_type.replace(/_/g, " ")} (${f.count})`).join(", ");
      sections.push({
        type: "insight",
        icon: <Lightbulb className="w-4 h-4 text-amber-500" />,
        title: "Top Risk Categories",
        body: `The most frequent risk categories across your portfolio are: ${topClauses}. These areas represent the highest concentration of legal exposure.`,
      });
    }

    // ── Review Aging Warning ──
    if (agingData && agingData.length > 0) {
      const overdue = agingData.find((a) => a.bucket === "over_7d" || a.bucket === "3_7d");
      if (overdue && overdue.count > 0) {
        sections.push({
          type: "action",
          icon: <TrendingDown className="w-4 h-4 text-red-500" />,
          title: "Aging Reviews Need Attention",
          body: `${overdue.count} reviews have been pending for more than ${overdue.bucket === "over_7d" ? "7 days" : "3 days"}. Assign reviewers or escalate to prevent SLA breaches.`,
        });
      }
    }

    // ── Positive Note ──
    if (agingData && agingData.length > 0) {
      const recent = agingData.find((a) => a.bucket === "under_1d");
      if (recent && recent.count > 0 && execData) {
        sections.push({
          type: "positive",
          icon: <TrendingDown className="w-4 h-4 text-green-500" />,
          title: "Active Review Pipeline",
          body: `${recent.count} reviews are currently in progress with ${execData.avg_review_sla_days}-day average turnaround. Keep assignments balanced to maintain velocity.`,
        });
      }
    }

    return sections;
  }, [execData, riskData, findingsData, agingData]);

  if (narratives.length === 0) return null;

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden"
    >
      <div className="px-4 py-3 border-b border-gray-100">
        <h3 className="text-xs font-semibold text-navy-900 flex items-center gap-2">
          <Lightbulb className="w-4 h-4 text-amber-500" />
          Portfolio Intelligence
        </h3>
      </div>
      <div className="divide-y divide-gray-100">
        {narratives.map((n, i) => (
          <div key={i} className="px-4 py-3 flex gap-3">
            <div className="mt-0.5 flex-shrink-0">{n.icon}</div>
            <div className="min-w-0 flex-1">
              <p className="text-xs font-semibold text-navy-900">{n.title}</p>
              <p className="text-[11px] text-gray-600 mt-0.5 leading-relaxed">{n.body}</p>
            </div>
          </div>
        ))}
      </div>
    </motion.div>
  );
}

/**
 * ReviewAiInsights — AI-powered insights panel for the Review Dashboard.
 *
 * Consolidates AI widgets previously on the Ingestion page into the Review Dashboard:
 * - AI Summary (overall health & status)
 * - Critical Findings (policy violations, extraction failures)
 * - Warnings / Duplicate Detection
 * - Suggestions / Clause Analysis
 *
 * Uses real data from the review dashboard API (DashboardResponse).
 */

"use client";

import React from "react";
import {
  AlertTriangle,
  XCircle,
  Info,
  Copy,
  FileSearch,
  Sparkles,
  ShieldAlert,
  Brain,
} from "lucide-react";
import type { DashboardResponse } from "@/services/api/client";

// ── Sub-components ───────────────────────────────────────────────────────

function InsightItem({
  icon,
  color,
  title,
  description,
}: {
  icon: React.ReactNode;
  color: string;
  title: string;
  description: string;
}) {
  return (
    <div className="flex items-start gap-1.5 px-3 py-1">
      <span className={`mt-0.5 ${color} flex-shrink-0`}>{icon}</span>
      <div className="min-w-0">
        <p className="text-[11px] font-medium text-navy-900 dark:text-white truncate">
          {title}
        </p>
        <p className="text-[10px] text-gray-500 dark:text-gray-400 line-clamp-2">
          {description}
        </p>
      </div>
    </div>
  );
}

function SectionHeader({
  icon,
  label,
  count,
  color,
}: {
  icon: React.ReactNode;
  label: string;
  count: number;
  color: string;
}) {
  return (
    <div className="flex items-center gap-1 px-3 py-1.5">
      {icon}
      <span className={`text-[10px] font-semibold ${color} uppercase tracking-wider`}>
        {label}
      </span>
      <span className={`text-[9px] font-medium ml-auto ${color}`}>{count}</span>
    </div>
  );
}

// ── Main Component ───────────────────────────────────────────────────────

interface ReviewAiInsightsProps {
  dashboard: DashboardResponse | undefined;
  isLoading: boolean;
}

export function ReviewAiInsights({ dashboard, isLoading }: ReviewAiInsightsProps) {
  if (isLoading) {
    return (
      <div className="w-64 flex-shrink-0 bg-white dark:bg-navy-800 border-l border-gray-200 dark:border-navy-700 flex flex-col h-full">
        <div className="px-3 py-2 border-b border-gray-200 dark:border-navy-700">
          <h3 className="text-[10px] font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">
            AI Insights
          </h3>
        </div>
        <div className="flex-1 flex items-center justify-center">
          <div className="w-5 h-5 border-2 border-gold-400 border-t-transparent rounded-full animate-spin" />
        </div>
      </div>
    );
  }

  const stats = dashboard?.stats;
  const findingsBySeverity = dashboard?.findings_by_severity ?? {};

  const criticalCount = findingsBySeverity["critical"] ?? 0;
  const warningCount = findingsBySeverity["high"] ?? 0;
  const infoCount = findingsBySeverity["medium"] ?? 0;
  const suggestionCount = findingsBySeverity["low"] ?? 0;
  const totalFindings = stats?.total_findings ?? 0;
  const totalReviews = stats?.total_reviews ?? 0;
  const pendingReviews = stats?.pending_reviews ?? 0;
  const escalatedCount = stats?.escalated_count ?? 0;
  const avgConfidence = stats?.average_confidence ?? null;
  const slaBreaches = stats?.sla_breach_count ?? 0;

  return (
    <div className="w-64 flex-shrink-0 bg-white dark:bg-navy-800 border-l border-gray-200 dark:border-navy-700 flex flex-col h-full">
      {/* Header */}
      <div className="px-3 py-2 border-b border-gray-200 dark:border-navy-700">
        <h3 className="text-[10px] font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">
          AI Insights
        </h3>
      </div>

      <div className="flex-1 overflow-y-auto">
        {/* AI Summary */}
        <div className="px-3 py-2 border-b border-gray-100 dark:border-navy-700">
          <div className="flex items-center gap-1 mb-1">
            <Sparkles className="w-3 h-3 text-blue-500" />
            <span className="text-[10px] font-semibold text-gray-500 uppercase tracking-wider">
              AI Summary
            </span>
          </div>
          <p className="text-[11px] text-gray-600 dark:text-gray-300 leading-relaxed">
            {totalReviews === 0
              ? "No reviews yet. Upload and process contracts to see AI insights here."
              : `${totalReviews} reviews · ${totalFindings} total findings · ${pendingReviews} pending`}
          </p>
          {avgConfidence !== null && (
            <div className="mt-1 flex items-center gap-1">
              <Brain className="w-2.5 h-2.5 text-purple-400" />
              <span className="text-[10px] text-gray-400">
                Avg confidence: {(avgConfidence * 100).toFixed(0)}%
              </span>
            </div>
          )}
        </div>

        {/* Critical Findings */}
        <div className="border-b border-gray-100 dark:border-navy-700">
          <SectionHeader
            icon={<XCircle className="w-3 h-3 text-red-500" />}
            label="Critical"
            count={criticalCount + escalatedCount + slaBreaches}
            color="text-red-600"
          />
          <div className="pb-1">
            {criticalCount > 0 && (
              <InsightItem
                icon={<XCircle className="w-3 h-3" />}
                color="text-red-500"
                title={`${criticalCount} Critical Findings`}
                description="Findings with critical severity requiring immediate attention"
              />
            )}
            {escalatedCount > 0 && (
              <InsightItem
                icon={<ShieldAlert className="w-3 h-3" />}
                color="text-red-500"
                title={`${escalatedCount} Escalated Reviews`}
                description="Reviews that have been escalated for higher-level review"
              />
            )}
            {slaBreaches > 0 && (
              <InsightItem
                icon={<AlertTriangle className="w-3 h-3" />}
                color="text-red-500"
                title={`${slaBreaches} SLA Breaches`}
                description="Reviews exceeding their SLA time limit"
              />
            )}
            {criticalCount === 0 && escalatedCount === 0 && slaBreaches === 0 && (
              <div className="px-3 py-2 text-[11px] text-gray-400 italic">
                No critical issues
              </div>
            )}
          </div>
        </div>

        {/* Warnings */}
        <div className="border-b border-gray-100 dark:border-navy-700">
          <SectionHeader
            icon={<AlertTriangle className="w-3 h-3 text-amber-500" />}
            label="Warnings"
            count={warningCount}
            color="text-amber-600"
          />
          <div className="pb-1">
            {warningCount > 0 ? (
              <InsightItem
                icon={<AlertTriangle className="w-3 h-3" />}
                color="text-amber-500"
                title={`${warningCount} High Severity Findings`}
                description="High-severity AI findings that may need attention"
              />
            ) : (
              <div className="px-3 py-2 text-[11px] text-gray-400 italic">
                No warnings
              </div>
            )}
          </div>
        </div>

        {/* Duplicate Detection */}
        <div className="border-b border-gray-100 dark:border-navy-700">
          <SectionHeader
            icon={<Copy className="w-3 h-3 text-amber-500" />}
            label="Duplicates"
            count={0}
            color="text-amber-600"
          />
          <div className="pb-1">
            <div className="px-3 py-2 text-[11px] text-gray-400 italic">
              Duplicate detection runs during ingestion
            </div>
          </div>
        </div>

        {/* Clause Analysis */}
        <div className="border-b border-gray-100 dark:border-navy-700">
          <SectionHeader
            icon={<FileSearch className="w-3 h-3 text-blue-500" />}
            label="Clause Analysis"
            count={infoCount}
            color="text-blue-600"
          />
          <div className="pb-1">
            {infoCount > 0 ? (
              <InsightItem
                icon={<FileSearch className="w-3 h-3" />}
                color="text-blue-500"
                title={`${infoCount} Clause Types Analyzed`}
                description="Medium-severity findings across different clause types"
              />
            ) : (
              <div className="px-3 py-2 text-[11px] text-gray-400 italic">
                No clause analysis data
              </div>
            )}
          </div>
        </div>

        {/* Suggestions */}
        <div>
          <SectionHeader
            icon={<Info className="w-3 h-3 text-blue-500" />}
            label="Suggestions"
            count={suggestionCount}
            color="text-blue-600"
          />
          <div className="pb-1">
            {suggestionCount > 0 ? (
              <InsightItem
                icon={<Info className="w-3 h-3" />}
                color="text-blue-500"
                title={`${suggestionCount} Improvement Suggestions`}
                description="Low-severity findings with actionable recommendations"
              />
            ) : (
              <div className="px-3 py-2 text-[11px] text-gray-400 italic">
                No suggestions
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

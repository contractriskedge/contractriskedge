/**
 * ContractExposureWidget — Total $ at risk, liability concentration, top drivers.
 *
 * Shows:
 * - Total exposure KPI with trend arrow
 * - Top-5 categories by exposure with full display names and tooltips
 * - Risk driver breakdown as horizontal bar chart
 *
 * Data sourced from executive aggregation layer — no hardcoded defaults.
 */

"use client";

import React from "react";
import type { ContractExposureData } from "@/src/lib/executive/executiveTypes";

interface ContractExposureWidgetProps {
  exposure?: ContractExposureData | null;
}

/** Map snake_case category keys to human-readable display names. */
const CATEGORY_LABELS: Record<string, string> = {
  "other": "Other",
  "intellectual_property": "Intellectual Property",
  "indemnification": "Indemnification",
  "data_privacy": "Data Privacy",
  "liability": "Liability",
  "confidentiality": "Confidentiality",
  "termination": "Termination",
  "payment_terms": "Payment Terms",
  "warranty": "Warranty",
  "insurance": "Insurance",
  "force_majeure": "Force Majeure",
  "governing_law": "Governing Law",
  "non_compete": "Non-Compete",
  "non_solicit": "Non-Solicit",
  "assignment": "Assignment",
  "audit_rights": "Audit Rights",
  "compliance": "Compliance",
  "data_security": "Data Security",
  "service_levels": "Service Levels",
  "limitation_of_liability": "Limitation of Liability",
};

/** Format a snake_case key into a readable short form (max ~18 chars). */
function formatCategoryName(key: string): string {
  const label = CATEGORY_LABELS[key];
  if (label) return label;
  // Fallback: replace underscores with spaces, title-case
  return key
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

/** Shorten a name to a max length, adding ellipsis if truncated. */
function shortenName(name: string, maxLen: number): string {
  if (name.length <= maxLen) return name;
  return name.slice(0, maxLen - 1) + "\u2026";
}

export function ContractExposureWidget({ exposure }: ContractExposureWidgetProps) {
  if (!exposure) {
    return (
      <div className="flex items-center justify-center h-32 text-xs text-gray-400">
        No exposure data available
      </div>
    );
  }

  const maxLiability = Math.max(...exposure.by_category.map((c) => c.exposure_score), 1);
  const totalDriverContrib = Math.max(exposure.top_risk_drivers.reduce((a, b) => a + b.contribution_pct, 0), 1);

  const concentrationColor = exposure.concentration_risk === "highly_concentrated" ? "text-red-600" :
    exposure.concentration_risk === "concentrated" ? "text-amber-600" : "text-green-600";

  return (
    <div className="space-y-3">
      {/* ── KPI Row ── */}
      <div className="flex items-center gap-4">
        <div className="flex-1">
          <span className="text-[10px] text-gray-500 dark:text-gray-400 uppercase">Total Exposure Score</span>
          <div className="flex items-center gap-2">
            <span className="text-xl font-bold text-red-600 dark:text-red-400">
              {exposure.total_exposure_score.toFixed(1)}
            </span>
            <span className={`text-xs ${concentrationColor}`}>
              {exposure.concentration_risk === "highly_concentrated" ? "↑" : exposure.concentration_risk === "concentrated" ? "→" : "↓"}
            </span>
          </div>
          <span className="text-[10px] text-gray-400 capitalize">{exposure.concentration_risk.replace(/_/g, " ")}</span>
        </div>
      </div>

      {/* ── Categories by Exposure ── */}
      <div>
        <span className="text-[10px] text-gray-500 dark:text-gray-400 uppercase mb-1 block">
          Exposure by Category
        </span>
        <div className="space-y-1">
          {exposure.by_category.slice(0, 5).map((cat) => {
            const displayName = formatCategoryName(cat.category);
            return (
              <div key={cat.category} className="flex items-center gap-2 group">
                <span
                  className="text-xs text-gray-600 dark:text-gray-400 w-28 truncate"
                  title={displayName}
                >
                  {shortenName(displayName, 18)}
                </span>
                <div className="flex-1 h-2 bg-gray-100 dark:bg-navy-700 rounded-full overflow-hidden">
                  <div
                    className="h-full rounded-full"
                    style={{
                      width: `${(cat.exposure_score / maxLiability) * 100}%`,
                      backgroundColor: cat.avg_severity === "critical" ? "#EF4444" : cat.avg_severity === "high" ? "#F59E0B" : "#10B981",
                    }}
                  />
                </div>
                <span className="text-xs text-navy-900 dark:text-white font-medium w-12 text-right">
                  {cat.exposure_share_pct.toFixed(0)}%
                </span>
              </div>
            );
          })}
        </div>
      </div>

      {/* ── Top Risk Drivers ── */}
      <div>
        <span className="text-[10px] text-gray-500 dark:text-gray-400 uppercase mb-1 block">
          Top Risk Drivers
        </span>
        <div className="space-y-1">
          {exposure.top_risk_drivers.slice(0, 5).map((rd) => {
            const displayName = formatCategoryName(rd.clause_type);
            return (
              <div key={rd.clause_type} className="flex items-center gap-2 group">
                <span
                  className="text-xs text-gray-600 dark:text-gray-400 w-28 truncate"
                  title={displayName}
                >
                  {shortenName(displayName, 18)}
                </span>
                <div className="flex-1 h-2 bg-gray-100 dark:bg-navy-700 rounded-full overflow-hidden">
                  <div
                    className="h-full rounded-full bg-navy-500 dark:bg-navy-400"
                    style={{ width: `${(rd.contribution_pct / totalDriverContrib) * 100}%` }}
                  />
                </div>
                <span className="text-xs text-navy-900 dark:text-white font-medium w-8 text-right">
                  {rd.contribution_pct.toFixed(0)}%
                </span>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

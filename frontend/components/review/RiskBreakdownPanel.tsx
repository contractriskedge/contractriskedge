/**
 * RiskBreakdownPanel — enterprise risk explainability engine.
 *
 * Correct enterprise logic:
 * - Original AI Risk = immutable initial analysis (never changes)
 * - Remaining Exposure = unresolved + accepted risks (the real current risk)
 * - Mitigated = risk resolved through redline changes (green)
 * - Dismissed = AI false positives removed from equation (gray)
 * - Accepted = business knowingly retained exposure (orange)
 *
 * ONE canonical scoring model:
 * - Category bars use normalized_contribution (sum == remaining_exposure)
 * - Exposure contributors show the same normalized values
 * - Ring chart always shows Remaining Exposure after review activity
 *
 * Strict semantic colors:
 * - Red: Active unresolved risk
 * - Orange: Accepted risk
 * - Green: Mitigated
 * - Gray: Dismissed
 * - Blue: Informational
 */

"use client";

import React, { useState } from "react";
import {
  AlertTriangle, TrendingDown, Shield, CheckCircle2, Clock,
  ChevronDown, ChevronRight, XCircle, FileText, Info,
  CornerDownRight, ArrowUp, ArrowDown, Zap, DollarSign, BookOpen, GitBranch,
  Lock,
} from "lucide-react";
import { useRiskBreakdown, useGenerateMitigationRedline } from "@/services/hooks";
import { AsyncBoundary } from "@/components/shared/AsyncBoundary";
import { CardSkeleton } from "@/components/shared/LoadingSkeleton";
import { useAuth } from "@/components/auth/AuthProvider";
import type {
  RiskBreakdown, RiskBreakdownItem, RiskBreakdownFinding, MitigatedFinding,
  ExposureContributor, MitigationSuggestion, TopRecommendedActions, TopRecommendedAction,
} from "@/services/api/client";

interface RiskBreakdownPanelProps {
  reviewId: string;
}

// ── Score interpretation ──────────────────────────────────────────

/**
 * Strict semantic color mapping:
 * - Red: Active unresolved risk (critical/high severity)
 * - Orange: Accepted risk (business knowingly retained)
 * - Amber/Yellow: Elevated / Moderate severity
 * - Green: Mitigated (risk resolved through changes)
 * - Gray: Dismissed (false positive, removed from equation)
 * - Blue: Informational/system (low severity, metadata)
 */
function scoreLabel(score: number): { label: string; color: string; bg: string } {
  if (score >= 0.81) return { label: "Critical", color: "text-red-600", bg: "bg-red-100 text-red-700" };
  if (score >= 0.61) return { label: "High", color: "text-orange-600", bg: "bg-orange-100 text-orange-700" };
  if (score >= 0.41) return { label: "Elevated", color: "text-amber-600", bg: "bg-amber-100 text-amber-700" };
  if (score >= 0.21) return { label: "Moderate", color: "text-yellow-600", bg: "bg-yellow-100 text-yellow-700" };
  return { label: "Minimal", color: "text-green-600", bg: "bg-green-100 text-green-700" };
}

function scoreColor(score: number): string {
  return scoreLabel(score).color;
}

/** Semantic severity colors - Red=unresolved, Orange=accepted, Green=mitigated, Gray=dismissed, Blue=info */
function severityColor(severity: string): string {
  switch (severity) {
    case "critical": return "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400";
    case "high": return "bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400";
    case "medium": return "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400";
    case "low": return "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400";
    default: return "bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400";
  }
}

/** Semantic resolution colors - maps resolution type to strict color */
function resolutionColor(resolutionType: string): { bg: string; text: string; dot: string } {
  switch (resolutionType) {
    case "mitigated":
      return { bg: "bg-green-50 dark:bg-green-900/10", text: "text-green-700 dark:text-green-300", dot: "bg-green-500" };
    case "accepted_risk":
      return { bg: "bg-orange-50 dark:bg-orange-900/10", text: "text-orange-700 dark:text-orange-300", dot: "bg-orange-500" };
    case "dismissed":
      return { bg: "bg-gray-50 dark:bg-gray-800/50", text: "text-gray-500 dark:text-gray-400", dot: "bg-gray-400" };
    default:
      return { bg: "bg-red-50 dark:bg-red-900/10", text: "text-red-700 dark:text-red-300", dot: "bg-red-500" };
  }
}

function formatPct(value: number): string {
  return `${(value * 100).toFixed(0)}%`;
}

// ── Score Gauge ───────────────────────────────────────────────────

function RiskGauge({ score, label, sublabel }: { score: number; label: string; sublabel?: string }) {
  const pct = Math.min(score * 100, 100);
  const labelInfo = scoreLabel(score);
  return (
    <div className="flex flex-col items-center">
      <div className="relative w-20 h-20">
        <svg className="w-20 h-20 -rotate-90" viewBox="0 0 80 80">
          <circle cx="40" cy="40" r="32" fill="none" stroke="#e5e7eb" strokeWidth="6" />
          <circle
            cx="40" cy="40" r="32" fill="none"
            stroke="currentColor" strokeWidth="6" strokeLinecap="round"
            strokeDasharray={`${(pct / 100) * 201} 201`}
            className={scoreColor(score)}
          />
        </svg>
        <div className="absolute inset-0 flex items-center justify-center">
          <span className={`text-lg font-bold ${scoreColor(score)}`}>{formatPct(score)}</span>
        </div>
      </div>
      <p className="mt-1 text-[10px] font-semibold text-gray-700 dark:text-gray-300">{label}</p>
      {sublabel && (
        <span className={`mt-0.5 text-[9px] font-semibold px-1.5 py-0.5 rounded-full ${labelInfo.bg}`}>
          {sublabel}
        </span>
      )}
    </div>
  );
}

// ── Financial Impact Panel ────────────────────────────────────────
//
// Translates the abstract risk score into dollar exposure so the user can
// see the business impact at a glance:
//   • Current Risk %  — current_contract_risk × 100
//   • Financial Exposure $ — contract_value × current_risk
//   • After Mitigation %  — projected residual risk if all suggested
//     mitigations are applied (deterministic 18% of current, capped at 5%)
//   • Potential Savings $  — current_exposure − after_mitigation_exposure

function formatMoney(amount: number, currency: string = "USD"): string {
  if (!amount) return "—";
  const abs = Math.abs(amount);
  const sign = amount < 0 ? "−" : "";
  if (abs >= 1_000_000_000) return `${sign}$${(abs / 1_000_000_000).toFixed(2)}B`;
  if (abs >= 1_000_000) return `${sign}$${(abs / 1_000_000).toFixed(2)}M`;
  if (abs >= 1_000) return `${sign}$${(abs / 1_000).toFixed(1)}K`;
  return `${sign}$${abs.toFixed(0)}`;
}

function FinancialImpactPanel({ impact }: { impact: NonNullable<RiskBreakdown["financial_impact"]> }) {
  const {
    contract_value, currency, current_risk_pct, current_exposure,
    after_mitigation_pct, after_mitigation_exposure, potential_savings,
  } = impact;

  return (
    <div
      className="mb-3 rounded-lg border border-amber-200 bg-gradient-to-br from-amber-50 to-orange-50 dark:border-amber-800 dark:from-amber-900/10 dark:to-orange-900/10 p-3"
      data-testid="financial-impact-panel"
    >
      <div className="flex items-center gap-1.5 mb-2">
        <DollarSign className="w-3.5 h-3.5 text-amber-700 dark:text-amber-400" />
        <span className="text-[10px] font-semibold uppercase tracking-wider text-amber-800 dark:text-amber-300">
          Estimated Business Impact
        </span>
        <span className="ml-auto text-[9px] text-gray-500 dark:text-gray-400 tabular-nums">
          on {formatMoney(contract_value, currency)} contract
        </span>
      </div>

      <div className="grid grid-cols-3 gap-2">
        <div className="rounded-md border border-red-200 bg-white/70 dark:border-red-800 dark:bg-navy-800/50 p-2 text-center">
          <p className="text-[9px] font-medium text-red-600 dark:text-red-400 uppercase tracking-wider">Current</p>
          <p className="text-base font-bold text-red-700 dark:text-red-300 tabular-nums">{current_risk_pct}%</p>
          <p className="text-[10px] font-semibold text-red-700 dark:text-red-300 tabular-nums">
            {formatMoney(current_exposure, currency)}
          </p>
        </div>
        <div className="rounded-md border border-emerald-200 bg-white/70 dark:border-emerald-800 dark:bg-navy-800/50 p-2 text-center">
          <p className="text-[9px] font-medium text-emerald-600 dark:text-emerald-400 uppercase tracking-wider">After Mitigation</p>
          <p className="text-base font-bold text-emerald-700 dark:text-emerald-300 tabular-nums">{after_mitigation_pct}%</p>
          <p className="text-[10px] font-semibold text-emerald-700 dark:text-emerald-300 tabular-nums">
            {formatMoney(after_mitigation_exposure, currency)}
          </p>
        </div>
        <div className="rounded-md border border-blue-200 bg-white/70 dark:border-blue-800 dark:bg-navy-800/50 p-2 text-center">
          <p className="text-[9px] font-medium text-blue-600 dark:text-blue-400 uppercase tracking-wider">Potential Savings</p>
          <p className="text-base font-bold text-blue-700 dark:text-blue-300 tabular-nums">
            {potential_savings > 0 ? formatMoney(potential_savings, currency) : "—"}
          </p>
          <p className="text-[10px] text-gray-500 dark:text-gray-400">if all mitigations accepted</p>
        </div>
      </div>
    </div>
  );
}

/** Secondary metrics beneath the ring — original → deltas → remaining */
function GaugeSecondaryMetrics({
  originalScore,
  mitigatedReduction,
  dismissedReduction,
  acceptedReduction,
  remainingExposure,
}: {
  originalScore: number;
  mitigatedReduction: number;
  dismissedReduction: number;
  acceptedReduction: number;
  remainingExposure: number;
}) {
  return (
    <div className="mt-3 w-full max-w-xs space-y-1 text-[10px]">
      <div className="flex justify-between text-gray-500 dark:text-gray-400">
        <span>Original AI Risk</span>
        <span className="font-semibold text-gray-700 dark:text-gray-300">{formatPct(originalScore)}</span>
      </div>
      {mitigatedReduction > 0 && (
        <div className="flex justify-between text-green-600 dark:text-green-400">
          <span>Mitigated</span>
          <span className="font-semibold">−{formatPct(mitigatedReduction)}</span>
        </div>
      )}
      {dismissedReduction > 0 && (
        <div className="flex justify-between text-gray-500 dark:text-gray-400">
          <span>Removed Exposure</span>
          <span className="font-semibold">−{formatPct(dismissedReduction)}</span>
        </div>
      )}
      {acceptedReduction > 0 && (
        <div className="flex justify-between text-orange-600 dark:text-orange-400">
          <span>Accepted Exposure</span>
          <span className="font-semibold">±{formatPct(acceptedReduction)}</span>
        </div>
      )}
      <div className="flex justify-between border-t border-gray-200 pt-1 dark:border-gray-600">
        <span className="font-semibold text-red-700 dark:text-red-300">Remaining</span>
        <span className={`font-bold ${scoreColor(remainingExposure)}`}>{formatPct(remainingExposure)}</span>
      </div>
    </div>
  );
}

// ── Mitigation Effectiveness Cards ────────────────────────────────
// Separately quantified: Mitigated, Dismissed, Accepted, Remaining

function MitigationEffectiveness({
  originalScore,
  mitigatedReduction,
  dismissedReduction,
  remainingExposure,
  acceptedReduction,
}: {
  originalScore: number;
  mitigatedReduction: number;
  dismissedReduction: number;
  remainingExposure: number;
  acceptedReduction: number;
}) {
  return (
    <div className="grid grid-cols-4 gap-2 mb-4">
      <div className="rounded-lg border border-green-200 bg-green-50/60 p-2 text-center dark:border-green-800 dark:bg-green-900/10">
        <p className="text-[9px] font-medium text-green-600 dark:text-green-400">Mitigated</p>
        <p className="text-sm font-bold text-green-700 dark:text-green-300">
          {mitigatedReduction > 0 ? formatPct(mitigatedReduction) : "—"}
        </p>
      </div>
      <div className="rounded-lg border border-gray-200 bg-gray-50/60 p-2 text-center dark:border-gray-700 dark:bg-gray-800/50">
        <p className="text-[9px] font-medium text-gray-500 dark:text-gray-400">Removed Exposure</p>
        <p className="text-sm font-bold text-gray-500 dark:text-gray-400">
          {dismissedReduction > 0 ? formatPct(dismissedReduction) : "—"}
        </p>
      </div>
      <div className="rounded-lg border border-orange-200 bg-orange-50/60 p-2 text-center dark:border-orange-800 dark:bg-orange-900/10">
        <p className="text-[9px] font-medium text-orange-600 dark:text-orange-400">Accepted Exposure</p>
        <p className="text-sm font-bold text-orange-700 dark:text-orange-300">
          {acceptedReduction > 0 ? formatPct(acceptedReduction) : "—"}
        </p>
      </div>
      <div className="rounded-lg border border-red-200 bg-red-50/60 p-2 text-center dark:border-red-800 dark:bg-red-900/10">
        <p className="text-[9px] font-medium text-red-600 dark:text-red-400">Remaining</p>
        <p className="text-sm font-bold text-red-700 dark:text-red-300">{formatPct(remainingExposure)}</p>
      </div>
    </div>
  );
}

// ── Drill-down finding row ────────────────────────────────────────
// Shows: Finding → Resolution status → Remaining impact
// Uses strict semantic colors: Red=open, Green=mitigated, Orange=accepted, Gray=dismissed

function FindingRow({ finding }: { finding: RiskBreakdownFinding }) {
  const [expanded, setExpanded] = useState(false);
  const isMitigated = finding.resolution_type === "mitigated";
  const isDismissed = finding.resolution_type === "dismissed";
  const isAccepted = finding.resolution_type === "accepted_risk";
  const isOpen = finding.resolution_type === "open";

  const resColors = resolutionColor(finding.resolution_type);

  let icon = <FileText className="w-3 h-3 text-gray-400 flex-shrink-0" />;
  let textColor = "text-gray-700 dark:text-gray-300";
  let sign = "+";
  let signColor = "text-red-500";
  let bgColor = "";

  if (isMitigated) {
    icon = <CheckCircle2 className="w-3 h-3 text-green-500 flex-shrink-0" />;
    textColor = "text-green-700 dark:text-green-400 line-through";
    sign = "−";
    signColor = "text-green-600";
    bgColor = "bg-green-50/50 dark:bg-green-900/10";
  } else if (isDismissed) {
    icon = <XCircle className="w-3 h-3 text-gray-400 flex-shrink-0" />;
    textColor = "text-gray-500 dark:text-gray-500 line-through";
    sign = "✕";
    signColor = "text-gray-400";
    bgColor = "bg-gray-50/50 dark:bg-gray-800/30";
  } else if (isAccepted) {
    icon = <Info className="w-3 h-3 text-orange-500 flex-shrink-0" />;
    textColor = "text-orange-700 dark:text-orange-400";
    sign = "±";
    signColor = "text-orange-500";
    bgColor = "bg-orange-50/50 dark:bg-orange-900/10";
  } else if (isOpen) {
    icon = <Clock className="w-3 h-3 text-red-500 flex-shrink-0" />;
    textColor = "text-red-800 dark:text-red-300";
    sign = "+";
    signColor = "text-red-500";
    bgColor = "hover:bg-gray-50 dark:hover:bg-gray-700/30";
  }

  return (
    <div>
      <div
        className={`flex items-center justify-between py-1 px-2 rounded cursor-pointer ${bgColor}`}
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-center gap-2 min-w-0 flex-1">
          <CornerDownRight className="w-2.5 h-2.5 text-gray-300 flex-shrink-0" />
          {icon}
          <span className={`text-[11px] truncate ${textColor}`}>{finding.title}</span>
          <span className={`text-[8px] font-semibold px-1 py-0.5 rounded-full flex-shrink-0 ${severityColor(finding.severity)}`}>
            {finding.severity}
          </span>
          <span className={`text-[8px] font-medium px-1 py-0.5 rounded-full flex-shrink-0 ${resColors.bg} ${resColors.text}`}>
            {finding.resolution_type === "open" ? "Open" :
             finding.resolution_type === "mitigated" ? "Mitigated" :
             finding.resolution_type === "accepted_risk" ? "Accepted Exposure" :
             finding.resolution_type === "dismissed" ? "Removed Exposure" : finding.resolution_type}
          </span>
        </div>
        <span className={`text-[10px] font-bold flex-shrink-0 ml-2 ${signColor}`}>
          {sign}{formatPct(finding.contribution)}
        </span>
      </div>
      {expanded && (
        <div className="ml-8 pl-3 border-l-2 border-gray-100 dark:border-gray-700 py-1.5 space-y-1">
          {/* ── Finding → Mitigation → Decision → Delta chain ── */}

          {/* Business Impact — transforms technical clause into business risk */}
          {finding.business_impact && (
            <div className="flex items-start gap-1.5 text-[10px] text-amber-700 dark:text-amber-300">
              <AlertTriangle className="w-2.5 h-2.5 mt-0.5 flex-shrink-0" />
              <div>
                <span className="font-medium">Business Impact: </span>
                <span>{finding.business_impact}</span>
              </div>
            </div>
          )}

          {/* Recommended Mitigation — what can be done */}
          {finding.recommended_mitigation && (
            <div className="flex items-start gap-1.5 text-[10px] text-blue-700 dark:text-blue-300">
              <Shield className="w-2.5 h-2.5 mt-0.5 flex-shrink-0" />
              <div>
                <span className="font-medium">Recommended Mitigation: </span>
                <span>{finding.recommended_mitigation}</span>
              </div>
            </div>
          )}

          {/* Decision / Resolution status */}
          <div className="flex items-start gap-1.5 text-[10px] text-gray-500 dark:text-gray-400">
            <CornerDownRight className="w-2.5 h-2.5 mt-0.5 flex-shrink-0" />
            <span>
              <span className="font-medium">Decision: </span>
              {finding.resolution_type === "open" ? "Awaiting review" :
               finding.resolution_type === "mitigated" ? "Mitigated via accepted redline" :
               finding.resolution_type === "accepted_risk" ? "Business-accepted exposure" :
               "Removed as not applicable"}
            </span>
          </div>

          {/* Clause context */}
          <div className="flex items-start gap-1.5 text-[10px] text-gray-400">
            <FileText className="w-2.5 h-2.5 mt-0.5 flex-shrink-0" />
            <span>Clause: {finding.clause_type || "General"} {finding.clause_label ? `· ${finding.clause_label}` : ""}</span>
          </div>
        </div>
      )}
    </div>
  );
}

// ── Contribution bar with drill-down ──────────────────────────────
// Uses normalized_contribution (sum == remaining_exposure) for consistency

function ContributionBar({ item, maxContribution, useRemaining }: { item: RiskBreakdownItem; maxContribution: number; useRemaining: boolean }) {
  const [expanded, setExpanded] = useState(false);
  const displayContrib = useRemaining ? item.normalized_contribution : item.contribution;
  const pct = maxContribution > 0 ? (displayContrib / maxContribution) * 100 : 0;
  const barColor = item.severity === "critical" ? "bg-red-500" :
    item.severity === "high" ? "bg-orange-500" :
    item.severity === "medium" ? "bg-amber-500" :
    "bg-blue-500";

  const openFindings = item.findings.filter(f => f.resolution_type === "open");
  const hasDrillDown = item.findings.length > 0;

  return (
    <div className="group">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between mb-1 hover:bg-gray-50 dark:hover:bg-gray-700/30 rounded px-2 -mx-1 transition-colors"
      >
        <div className="flex items-center gap-2 min-w-0">
          <span className="flex-shrink-0 w-4 flex justify-center">
            {hasDrillDown ? (
              expanded ? <ChevronDown className="w-3 h-3 text-gray-400" /> : <ChevronRight className="w-3 h-3 text-gray-400" />
            ) : (
              <span className="w-3 h-3" />
            )}
          </span>
          <span className="text-xs font-medium text-gray-700 dark:text-gray-300 truncate">{item.label}</span>
          <span className={`text-[9px] font-semibold px-1.5 py-0.5 rounded-full flex-shrink-0 ${severityColor(item.severity)}`}>
            {item.severity}
          </span>
          {item.open_count > 0 && (
            <span className="text-[9px] text-red-500 font-medium flex-shrink-0">
              ({item.open_count} open)
            </span>
          )}
        </div>
        <div className="flex items-center gap-2 flex-shrink-0">
          <span className={`text-xs font-bold ${displayContrib > 0 ? "text-red-600" : "text-gray-400"}`}>
            +{formatPct(displayContrib)}
          </span>
          <span className="text-[9px] text-gray-400">({item.finding_count})</span>
        </div>
      </button>
      <div className="relative h-2 w-full rounded-full bg-gray-100 dark:bg-gray-700 overflow-hidden ml-6" style={{ width: 'calc(100% - 1.5rem)' }}>
        <div
          className={`h-full rounded-full transition-all duration-500 ${barColor}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <div className="flex items-center gap-2 mt-0.5 text-[9px] text-gray-400 ml-6">
        {item.mitigated_count > 0 && (
          <span className="inline-flex items-center gap-0.5 text-green-600">
            <CheckCircle2 className="w-2.5 h-2.5" /> {item.mitigated_count} mitigated
          </span>
        )}
        {item.accepted_count > 0 && (
          <span className="inline-flex items-center gap-0.5 text-orange-600">
            <Info className="w-2.5 h-2.5" /> {item.accepted_count} accepted
          </span>
        )}
        {item.dismissed_count > 0 && (
          <span className="inline-flex items-center gap-0.5 text-gray-400">
            <XCircle className="w-2.5 h-2.5" /> {item.dismissed_count} dismissed
          </span>
        )}
        {item.open_count > 0 && (
          <span className="inline-flex items-center gap-0.5 text-red-500">
            <Clock className="w-2.5 h-2.5" /> {item.open_count} open
          </span>
        )}
      </div>
      {expanded && hasDrillDown && (
        <div className="mt-1.5 ml-6 pl-3 border-l-2 border-gray-200 dark:border-gray-600 space-y-0.5">
          {item.findings.map((finding) => (
            <FindingRow key={finding.finding_id} finding={finding} />
          ))}
        </div>
      )}
    </div>
  );
}

// ── Severity-grouped Open Exposures ───────────────────────────────
// Groups findings into Critical/High/Medium sections for triage

function OpenExposureCard({ finding, accent }: { finding: MitigatedFinding; accent: { color: string; dot: string } }) {
  const [expanded, setExpanded] = useState(false);
  return (
    <div className="rounded border border-gray-100 bg-white/60 dark:border-gray-700 dark:bg-gray-800/40">
      <button
        type="button"
        onClick={() => setExpanded(!expanded)}
        className="flex w-full items-center gap-2 px-2 py-1.5 text-left text-[10px]"
      >
        <span className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${accent.dot}`} />
        <div className="flex-1 min-w-0">
          <span className={`block truncate font-medium ${accent.color}`}>{finding.title}</span>
          {finding.business_impact && (
            <span className="block truncate text-[8px] text-gray-500 dark:text-gray-400 mt-0.5">
              {finding.business_impact}
            </span>
          )}
        </div>
        {finding.remaining_contribution != null && finding.remaining_contribution > 0 && (
          <span className="text-[9px] font-bold text-red-600 flex-shrink-0">+{formatPct(finding.remaining_contribution)}</span>
        )}
        <span className={`text-[8px] font-semibold px-1 py-0.5 rounded-full flex-shrink-0 ${severityColor(finding.severity)}`}>
          {finding.severity}
        </span>
        {expanded ? <ChevronDown className="w-3 h-3 text-gray-400 flex-shrink-0" /> : <ChevronRight className="w-3 h-3 text-gray-400 flex-shrink-0" />}
      </button>
      {expanded && (
        <div className="px-2 pb-2 space-y-1 border-t border-gray-100 dark:border-gray-700">
          {finding.business_impact && (
            <p className="text-[9px] text-gray-600 dark:text-gray-400 pt-1">
              <span className="font-semibold text-gray-700 dark:text-gray-300">Impact: </span>
              {finding.business_impact}
            </p>
          )}
          {finding.recommended_mitigation && (
            <p className="text-[9px] text-blue-700 dark:text-blue-300">
              <span className="font-semibold">Recommended Mitigation: </span>
              {finding.recommended_mitigation}
            </p>
          )}
          <p className="text-[9px] text-gray-500">
            <span className="font-semibold">Review state: </span>
            <span className="text-red-600 font-medium">{finding.review_state || finding.resolution_label || "Open"}</span>
            {finding.linked_redline_count ? ` · ${finding.linked_redline_count} linked redline(s)` : ""}
          </p>
        </div>
      )}
    </div>
  );
}

function GroupedOpenExposures({ findings }: { findings: MitigatedFinding[] }) {
  if (findings.length === 0) return null;

  // Prioritize: 1) highest remaining_contribution first within each severity group
  const sorted = [...findings].sort((a, b) => {
    const sevOrder = { critical: 0, high: 1, medium: 2, low: 3, info: 4 };
    const aSev = sevOrder[a.severity as keyof typeof sevOrder] ?? 5;
    const bSev = sevOrder[b.severity as keyof typeof sevOrder] ?? 5;
    if (aSev !== bSev) return aSev - bSev;
    return (b.remaining_contribution ?? 0) - (a.remaining_contribution ?? 0);
  });

  const critical = sorted.filter(f => f.severity === "critical");
  const high = sorted.filter(f => f.severity === "high");
  const medium = sorted.filter(f => f.severity === "medium");
  const other = sorted.filter(f => !["critical", "high", "medium"].includes(f.severity));

  const groups = [
    { label: "Critical Open Exposures", items: critical, color: "text-red-600", dot: "bg-red-500", bg: "bg-red-50/80 dark:bg-red-900/10", border: "border-red-200 dark:border-red-800" },
    { label: "High Exposure Items", items: high, color: "text-orange-600", dot: "bg-orange-500", bg: "bg-orange-50/80 dark:bg-orange-900/10", border: "border-orange-200 dark:border-orange-800" },
    { label: "Medium Exposure Items", items: medium, color: "text-amber-600", dot: "bg-amber-500", bg: "bg-amber-50/80 dark:bg-amber-900/10", border: "border-amber-200 dark:border-amber-800" },
    { label: "Other Items", items: other, color: "text-gray-500", dot: "bg-gray-400", bg: "bg-gray-50/80 dark:bg-gray-800/50", border: "border-gray-200 dark:border-gray-700" },
  ];

  return (
    <div className="space-y-2 mb-3">
      {groups.map(g => g.items.length > 0 && (
        <div key={g.label} className={`rounded-lg border ${g.border} ${g.bg} p-2.5`}>
          <h4 className={`text-[10px] font-semibold ${g.color} mb-1.5`}>
            {g.label} ({g.items.length})
          </h4>
          <div className="space-y-1">
            {g.items.map((f, i) => (
              <OpenExposureCard key={f.finding_id || i} finding={f} accent={{ color: g.color, dot: g.dot }} />
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

// ── Resolved Section (reusable) ───────────────────────────────────

function ResolvedSection({
  title,
  icon,
  findings,
  bgColor,
  borderColor,
  textColor,
  iconColor,
}: {
  title: string;
  icon: React.ReactNode;
  findings: MitigatedFinding[];
  bgColor: string;
  borderColor: string;
  textColor: string;
  iconColor: string;
}) {
  if (findings.length === 0) return null;

  return (
    <div className={`rounded-lg border ${borderColor} ${bgColor} p-3`}>
      <div className="flex items-center gap-2 mb-2">
        <span className={iconColor}>{icon}</span>
        <h4 className={`text-xs font-semibold ${textColor}`}>
          {title} ({findings.length})
        </h4>
      </div>
      <div className="space-y-1">
        {findings.map((f, i) => (
          <div key={i} className="flex items-center gap-2 text-[11px]">
            <span className="w-1.5 h-1.5 rounded-full flex-shrink-0" style={{ backgroundColor: "currentColor" }} />
            <span className={`flex-1 truncate ${textColor}`}>{f.title}</span>
            <span className={`text-[8px] font-semibold px-1 py-0.5 rounded-full flex-shrink-0 ${severityColor(f.severity)}`}>
              {f.severity}
            </span>
            <span className={`text-[9px] capitalize flex-shrink-0 ${textColor}`}>{f.resolution_label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Open Exposure Contributors Panel ──────────────────────────────
// Visually prominent: delta arrows, mini bars, right-aligned percentages

/** Uses same normalized_contribution values as category bars (absolute exposure points). */
function ExposureContributorsPanel({ contributors, remainingExposure }: { contributors: ExposureContributor[]; remainingExposure: number }) {
  if (contributors.length === 0) return null;

  const active = contributors.filter(c => c.normalized_contribution > 0);
  if (active.length === 0) return null;

  const maxContrib = Math.max(...active.map(c => c.normalized_contribution), 0.001);

  return (
    <div className="rounded-lg border border-blue-200 bg-blue-50/70 p-3 dark:border-blue-800 dark:bg-blue-900/10">
      <div className="flex items-center justify-between mb-2.5">
        <h4 className="text-xs font-bold text-blue-800 dark:text-blue-200">
          Open Exposure Contributors
        </h4>
        <span className="text-[9px] text-blue-500 dark:text-blue-400 font-medium" title="Sum equals remaining exposure">
          ≈ {formatPct(remainingExposure)} remaining
        </span>
      </div>
      <div className="space-y-2">
        {active.map((c) => {
          const barWidth = (c.normalized_contribution / maxContrib) * 100;
          return (
            <div key={c.category}>
              <div className="flex items-center justify-between text-[11px]">
                <div className="flex items-center gap-1.5 min-w-0 flex-1">
                  <ArrowUp className="w-2.5 h-2.5 text-red-400 flex-shrink-0" />
                  <span className="text-blue-800 dark:text-blue-200 font-medium truncate">{c.label}</span>
                </div>
                <span className="text-[11px] font-bold text-red-600 flex-shrink-0 ml-2">
                  +{formatPct(c.normalized_contribution)}
                </span>
              </div>
              <div className="mt-0.5 h-1.5 w-full rounded-full bg-blue-100 dark:bg-blue-900/30 overflow-hidden">
                <div
                  className="h-full rounded-full bg-blue-500 dark:bg-blue-400"
                  style={{ width: `${barWidth}%` }}
                />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function RiskDeltaTimeline({ data }: { data: RiskBreakdown }) {
  if (!data.delta_explanations?.length && (data.risk_delta ?? 0) === 0) return null;

  // Build chronological waterfall: start at original, apply each delta in sequence
  const originalScore = data.original_risk_score ?? data.overall_risk_score;
  const steps: { label: string; delta: number; runningTotal: number; category: string }[] = [];
  let runningTotal = originalScore;

  // Sort deltas: negative (reductions) first, then positive (accepted)
  const sortedDeltas = [...data.delta_explanations].sort((a, b) => a.contribution - b.contribution);

  for (const d of sortedDeltas) {
    runningTotal = Math.max(0, runningTotal + d.contribution);
    steps.push({
      label: d.label,
      delta: d.contribution,
      runningTotal,
      category: d.category,
    });
  }

  // Final step is always remaining exposure
  const finalRisk = data.current_contract_risk ?? data.remaining_exposure;

  return (
    <div className="mb-4 rounded-lg border border-gray-200 bg-gray-50/80 p-3 dark:border-gray-700 dark:bg-gray-800/50">
      <h4 className="text-[10px] font-semibold text-gray-600 dark:text-gray-400 mb-2">Risk Delta Timeline</h4>

      {/* Waterfall visualization */}
      <div className="space-y-2">
        {/* Starting point */}
        <div className="flex items-center gap-2 text-[10px]">
          <div className="flex h-5 w-5 items-center justify-center rounded-full bg-gray-200 text-[8px] font-bold text-gray-600 dark:bg-gray-600 dark:text-gray-300">S</div>
          <span className="text-gray-500 font-medium">Start</span>
          <span className="font-semibold text-gray-700 dark:text-gray-300">{formatPct(originalScore)}</span>
          <div className="flex-1 h-1 rounded-full bg-gray-200 dark:bg-gray-600">
            <div className="h-full rounded-full bg-gray-400" style={{ width: `${Math.min(100, originalScore * 100)}%` }} />
          </div>
        </div>

        {/* Each decision step */}
        {steps.map((step, i) => (
          <div key={i} className="flex items-center gap-2 text-[10px]">
            <div className={`flex h-5 w-5 items-center justify-center rounded-full text-[8px] font-bold ${
              step.category === "mitigation" ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400" :
              step.category === "dismissed" ? "bg-gray-200 text-gray-600 dark:bg-gray-600 dark:text-gray-300" :
              step.category === "accepted" ? "bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400" :
              "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400"
            }`}>
              {i + 1}
            </div>
            <span className={`flex-1 truncate ${
              step.category === "mitigation" ? "text-green-700 dark:text-green-400" :
              step.category === "dismissed" ? "text-gray-500 dark:text-gray-400" :
              step.category === "accepted" ? "text-orange-700 dark:text-orange-400" :
              "text-gray-700 dark:text-gray-300"
            }`}>
              {step.label}
            </span>
            <span className={`font-semibold ${
              step.delta < 0 ? "text-green-600" : "text-orange-600"
            }`}>
              {step.delta < 0 ? `−${formatPct(Math.abs(step.delta))}` : `+${formatPct(step.delta)}`}
            </span>
            <span className="text-gray-400 w-12 text-right font-mono">{formatPct(step.runningTotal)}</span>
          </div>
        ))}

        {/* Separator */}
        <div className="border-t border-gray-200 dark:border-gray-600" />

        {/* Final result */}
        <div className="flex items-center gap-2 text-[10px] font-bold">
          <div className="flex h-5 w-5 items-center justify-center rounded-full bg-amber-100 text-[8px] font-bold text-amber-700 dark:bg-amber-900/30 dark:text-amber-400">E</div>
          <span className="text-amber-800 dark:text-amber-300">Remaining Exposure</span>
          <div className="flex-1 h-1.5 rounded-full bg-amber-100 dark:bg-amber-900/30">
            <div className="h-full rounded-full bg-amber-500" style={{ width: `${Math.min(100, finalRisk * 100)}%` }} />
          </div>
          <span className="text-amber-800 dark:text-amber-300">{formatPct(finalRisk)}</span>
        </div>

        {/* Detail explanations */}
        {data.delta_explanations.map((d, i) => (
          <div key={i} className="pl-7 border-l-2 border-gray-100 dark:border-gray-700 ml-2.5">
            {d.details.map((detail, j) => (
              <p key={j} className="text-[9px] text-gray-500 dark:text-gray-400 leading-relaxed">{detail}</p>
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Mitigation Effectiveness Panel ───────────────────────────────
// Shows explainable remediation intelligence per clause category.
// Backend data from mitigation_effectiveness.py → risk_breakdown_payload.mitigation_suggestions

function MitigationSuggestionsPanel({
  suggestions,
}: {
  suggestions: MitigationSuggestion[];
}) {
  if (!suggestions || suggestions.length === 0) return null;

  return (
    <div className="mb-4 rounded-lg border border-indigo-200 bg-indigo-50/70 p-3 dark:border-indigo-800 dark:bg-indigo-900/10">
      <div className="flex items-center gap-2 mb-2.5">
        <TrendingDown className="w-3.5 h-3.5 text-indigo-500" />
        <h4 className="text-xs font-semibold text-indigo-800 dark:text-indigo-200">
          Recommended Mitigations
        </h4>
        <span className="text-[8px] text-indigo-500 dark:text-indigo-400 ml-auto font-medium">
          Estimated exposure reduction
        </span>
      </div>
      <div className="space-y-2">
        {suggestions.map((s, i) => (
          <div key={i} className="rounded-md border border-indigo-100 bg-white/60 p-2 dark:border-indigo-800 dark:bg-indigo-900/20">
            <div className="flex items-center justify-between mb-1">
              <span className="text-[10px] font-semibold text-indigo-800 dark:text-indigo-200">
                {s.label}
              </span>
              <span className="text-[9px] text-gray-500 dark:text-gray-400">
                {formatPct(s.remaining_contribution)} remaining
              </span>
            </div>
            <div className="space-y-1">
              {s.suggested_mitigations.map((m, j) => (
                <div key={j} className="flex items-start gap-1.5 text-[9px]">
                  <Shield className="w-2.5 h-2.5 text-indigo-400 mt-0.5 flex-shrink-0" />
                  <div className="flex-1 min-w-0">
                    <span className="font-medium text-indigo-700 dark:text-indigo-300">{m.label}</span>
                    <p className="text-gray-500 dark:text-gray-400">{m.description}</p>
                  </div>
                  <div className="flex flex-col items-end flex-shrink-0 ml-1">
                    <span className="font-semibold text-green-600 dark:text-green-400">
                      −{formatPct(m.estimated_reduction_pct)}
                    </span>
                    <span className="text-[7px] font-medium text-amber-600 dark:text-amber-400">
                      Confidence: {Math.round(m.confidence * 100)}%
                    </span>
                    <span className="text-[6px] text-gray-400">
                      {m.source.replace(/_/g, " ")}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
      <p className="mt-2 text-[8px] text-indigo-400 dark:text-indigo-500 italic">
        Estimates based on industry standards, legal precedent, and ML prediction models.
        Actual reduction may vary by contract context and negotiation outcome.
      </p>
    </div>
  );
}

// ── Collapsible Section — progressive disclosure ─────────────────
// Enterprise UX: summary first, investigation second.
// Secondary panels are collapsed by default.

function CollapsibleSection({
  title,
  icon,
  defaultOpen = false,
  children,
  badge,
}: {
  title: string;
  icon: React.ReactNode;
  defaultOpen?: boolean;
  children: React.ReactNode;
  badge?: string | number;
}) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="mb-3">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="flex w-full items-center gap-2 text-[10px] font-medium text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 mb-1"
      >
        {open ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
        {icon}
        <span>{title}</span>
        {badge != null && (
          <span className="text-[9px] font-semibold px-1.5 py-0.5 rounded-full bg-gray-100 text-gray-500 dark:bg-gray-700 dark:text-gray-400">
            {badge}
          </span>
        )}
      </button>
      {open && <div>{children}</div>}
    </div>
  );
}

// ── Top Recommended Actions Widget — executive guidance ──────────
// Shows the 3 highest-impact mitigations across ALL categories.
// Each action is actionable: [Review Finding] [Generate Redline]
// Both buttons are wired to real operational behavior.

function TopActionsWidget({
  actions,
  currentRisk,
  originalRisk,
  reviewId,
}: {
  actions: TopRecommendedActions;
  currentRisk: number;
  originalRisk: number;
  reviewId: string;
}) {
  const { hasPermission } = useAuth();
  const canGenerate = hasPermission("workflows:write") || hasPermission("*");

  if (!actions?.top_actions?.length) return null;

  const totalReduction = actions.total_potential_reduction_abs;
  const estimatedResidual = Math.max(0, currentRisk - totalReduction);
  const [generatingId, setGeneratingId] = useState<string | null>(null);
  const [successId, setSuccessId] = useState<string | null>(null);
  const [successData, setSuccessData] = useState<Record<string, unknown> | null>(null);

  // Generate redline mutation
  const generateMutation = useGenerateMitigationRedline(reviewId);

  const handleGenerateRedline = async (action: TopRecommendedAction) => {
    if (!canGenerate) return;
    setGeneratingId(action.mitigation_type);
    setSuccessId(null);
    setSuccessData(null);
    try {
      const result = await generateMutation.mutateAsync({
        mitigation_type: action.mitigation_type,
        clause_category: action.category,
        finding_ids: [],
      });
      setSuccessId(action.mitigation_type);
      setSuccessData(result as any);
      setTimeout(() => { setSuccessId(null); setSuccessData(null); }, 4000);
    } catch {
      // Error handled by mutation state
    } finally {
      setGeneratingId(null);
    }
  };

  const handleReviewFinding = (action: TopRecommendedAction) => {
    // Dispatch event that ReviewWorkspace listens for to switch to findings tab and highlight
    const event = new CustomEvent("mitigation:filter-findings", {
      detail: {
        category: action.category,
        mitigation_type: action.mitigation_type,
        label: action.label,
      },
    });
    window.dispatchEvent(event);
  };

  return (
    <div className="mb-4 rounded-lg border-2 border-emerald-200 bg-emerald-50/80 p-3 dark:border-emerald-800 dark:bg-emerald-900/10">
      <div className="flex items-center gap-2 mb-2.5">
        <Zap className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
        <h4 className="text-xs font-bold text-emerald-800 dark:text-emerald-200">
          Top Risk Reduction Opportunities
        </h4>
      </div>

      {/* Potential + Estimated residual — EXPLAINABLE math */}
      <div className="flex items-center gap-3 mb-2.5 flex-wrap">
        {actions.total_potential_reduction_pct > 0 && (
          <div className="flex items-center gap-1.5 rounded-md bg-emerald-100 px-2 py-1 dark:bg-emerald-900/30">
            <span className="text-[9px] font-semibold text-emerald-700 dark:text-emerald-300">
              Potential: −{formatPct(actions.total_potential_reduction_pct)}
            </span>
          </div>
        )}
        {totalReduction > 0 && (
          <div className="flex items-center gap-1.5 rounded-md bg-blue-100 px-2 py-1 dark:bg-blue-900/30">
            <span className="text-[9px] font-semibold text-blue-700 dark:text-blue-300">
              Est. residual: {formatPct(estimatedResidual)}
            </span>
          </div>
        )}
      </div>

      {/* Explainable formula — shows the math so users trust the numbers */}
      {totalReduction > 0 && (
        <div className="mb-2.5 rounded-md bg-gray-50 px-2.5 py-1.5 text-[8px] text-gray-500 dark:bg-gray-800/50 dark:text-gray-400 font-mono">
          {formatPct(currentRisk)} − {formatPct(totalReduction)} ({formatPct(actions.total_potential_reduction_pct)} of current) = {formatPct(estimatedResidual)}
        </div>
      )}

      <div className="space-y-2">
        {actions.top_actions.map((action, i) => (
          <div key={i} className="flex items-start gap-2 rounded-md border border-emerald-100 bg-white/70 p-2 dark:border-emerald-800 dark:bg-emerald-900/20">
            <span className="flex h-5 w-5 items-center justify-center rounded-full bg-emerald-100 text-[9px] font-bold text-emerald-700 flex-shrink-0 dark:bg-emerald-900/30 dark:text-emerald-400">
              {i + 1}
            </span>
            <div className="flex-1 min-w-0">
              <div className="flex items-center justify-between gap-2">
                <span className="text-[10px] font-semibold text-emerald-800 dark:text-emerald-200 truncate">
                  {action.mitigation_label}
                </span>
                <span className="text-[10px] font-bold text-green-600 dark:text-green-400 flex-shrink-0">
                  −{formatPct(action.estimated_reduction_pct)}
                </span>
              </div>
              <p className="text-[9px] text-gray-500 dark:text-gray-400 mt-0.5 line-clamp-1">
                {action.description}
              </p>
              <div className="flex items-center gap-2 mt-0.5">
                <span className="text-[8px] text-gray-400 dark:text-gray-500">
                  {action.label}
                </span>
                <span className="text-[8px] text-gray-400 dark:text-gray-500">·</span>
                <span className="text-[8px] font-medium text-amber-600 dark:text-amber-400">
                  Confidence: {Math.round(action.confidence * 100)}%
                </span>
                <span className="text-[8px] text-gray-400 dark:text-gray-500">·</span>
                <span className="text-[8px] font-medium text-indigo-500 dark:text-indigo-400">
                  {action.source.replace(/_/g, " ")}
                </span>
              </div>
              {/* Action buttons — closed-loop remediation */}
              <div className="flex items-center gap-1.5 mt-1.5">
                <button
                  type="button"
                  onClick={() => handleReviewFinding(action)}
                  className="inline-flex items-center gap-1 rounded border border-emerald-200 bg-emerald-50 px-1.5 py-0.5 text-[7px] font-medium text-emerald-700 hover:bg-emerald-100 dark:border-emerald-700 dark:bg-emerald-900/20 dark:text-emerald-300"
                  title="Jump to findings related to this clause category"
                >
                  <FileText className="w-2.5 h-2.5" />
                  Review Finding
                </button>
                {canGenerate ? (
                  <button
                    type="button"
                    onClick={() => handleGenerateRedline(action)}
                    disabled={generatingId === action.mitigation_type}
                    className="inline-flex items-center gap-1 rounded border border-indigo-200 bg-indigo-50 px-1.5 py-0.5 text-[7px] font-medium text-indigo-700 hover:bg-indigo-100 disabled:opacity-50 dark:border-indigo-700 dark:bg-indigo-900/20 dark:text-indigo-300"
                    title="Generate a draft redline for this mitigation"
                  >
                    {generatingId === action.mitigation_type ? (
                      <>Generating...</>
                    ) : successId === action.mitigation_type ? (
                      <>✓ Draft created</>
                    ) : (
                      <>
                        <FileText className="w-2.5 h-2.5" />
                        Generate Redline
                      </>
                    )}
                  </button>
                ) : (
                  <span
                    className="inline-flex items-center gap-1 rounded border border-gray-200 bg-gray-50 px-1.5 py-0.5 text-[7px] font-medium text-gray-400 dark:border-gray-700 dark:bg-gray-800/50"
                    title="You have read-only access"
                  >
                    <Lock className="w-2.5 h-2.5" />
                    Read Only
                  </span>
                )}
              </div>
              {/* Success toast with traceability */}
              {successId === action.mitigation_type && successData && (
                <div className="mt-1 space-y-0.5">
                  <div className="text-[7px] text-emerald-600 dark:text-emerald-400 font-medium">
                    {successData.duplicate ? (
                      <>♻️ Existing draft redline found — reopened for review</>
                    ) : (
                      <>✓ Draft redline created from mitigation recommendation</>
                    )}
                  </div>
                  <div className="text-[7px] text-gray-500 dark:text-gray-400">
                    Generated from: {action.mitigation_label}
                    {successData.estimated_reduction_pct && (
                      <> · Est. reduction: −{((successData.estimated_reduction_pct as number) * 100).toFixed(0)}%</>
                    )}
                    {successData.confidence && (
                      <> · Confidence: {Math.round((successData.confidence as number) * 100)}%</>
                    )}
                  </div>
                </div>
              )}
              {/* Fallback success toast (no data) */}
              {successId === action.mitigation_type && !successData && (
                <div className="mt-1 text-[7px] text-emerald-600 dark:text-emerald-400 font-medium">
                  ✓ Draft redline created. Review it in the Redlines tab.
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
      {totalReduction > 0 && (
        <p className="mt-2 text-[8px] text-emerald-500 dark:text-emerald-400 italic">
          If all {actions.action_count} recommended actions are applied, exposure drops from {formatPct(currentRisk)} → ~{formatPct(estimatedResidual)}.
        </p>
      )}
    </div>
  );
}

// ── Risk Score Stack Layout ───────────────────────────────────────

function RiskScoreStack({
  originalScore,
  mitigatedReduction,
  dismissedReduction,
  acceptedReduction,
  remainingExposure,
}: {
  originalScore: number;
  mitigatedReduction: number;
  dismissedReduction: number;
  acceptedReduction: number;
  remainingExposure: number;
}) {
  const hasReviewActivity = mitigatedReduction > 0 || dismissedReduction > 0 || acceptedReduction > 0
    || Math.abs(remainingExposure - originalScore) > 0.001;

  return (
    <div className="space-y-2">
      {/* Original AI Risk — always shown as reference */}
      <div className="flex items-center justify-between px-2 py-1.5 rounded bg-gray-50 dark:bg-gray-800/50">
        <div className="flex items-center gap-2">
          <Shield className="w-3.5 h-3.5 text-gray-400" />
          <span className="text-[11px] text-gray-600 dark:text-gray-400">Original AI Risk</span>
        </div>
        <span className={`text-xs font-bold ${scoreColor(originalScore)}`}>{formatPct(originalScore)}</span>
      </div>

      {hasReviewActivity && (
        <>
          {mitigatedReduction > 0 && (
            <div className="flex items-center justify-between px-2 py-1.5 rounded bg-green-50 dark:bg-green-900/10">
              <div className="flex items-center gap-2">
                <CheckCircle2 className="w-3.5 h-3.5 text-green-500" />
                <span className="text-[11px] text-green-700 dark:text-green-300">Mitigated Reduction</span>
              </div>
              <span className="text-xs font-bold text-green-600">−{formatPct(mitigatedReduction)}</span>
            </div>
          )}

          {dismissedReduction > 0 && (
            <div className="flex items-center justify-between px-2 py-1.5 rounded bg-gray-50 dark:bg-gray-800/50">
              <div className="flex items-center gap-2">
                <XCircle className="w-3.5 h-3.5 text-gray-400" />
                <span className="text-[11px] text-gray-500 dark:text-gray-400">Dismissed False Positives</span>
              </div>
              <span className="text-xs font-bold text-gray-400">−{formatPct(dismissedReduction)}</span>
            </div>
          )}

          {acceptedReduction > 0 && (
            <div className="flex items-center justify-between px-2 py-1.5 rounded bg-orange-50 dark:bg-orange-900/10">
              <div className="flex items-center gap-2">
                <AlertTriangle className="w-3.5 h-3.5 text-orange-500" />
                <span className="text-[11px] text-orange-700 dark:text-orange-300">Accepted Exposure</span>
              </div>
              <span className="text-xs font-bold text-orange-600">+{formatPct(acceptedReduction)}</span>
            </div>
          )}

          <div className="border-t border-gray-200 dark:border-gray-700" />

          {/* Remaining Exposure — FINAL number (boldest visual weight) */}
          <div className="flex items-center justify-between px-2 py-2 rounded bg-amber-50 dark:bg-amber-900/10 border border-amber-200 dark:border-amber-800">
            <div className="flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-amber-600" />
              <span className="text-xs font-bold text-amber-800 dark:text-amber-300">Remaining Exposure</span>
            </div>
            <span className={`text-sm font-bold ${scoreColor(remainingExposure)}`}>{formatPct(remainingExposure)}</span>
          </div>
        </>
      )}
    </div>
  );
}

// ── Governance Traceability Panel ─────────────────────────────────

function GovernanceTraceabilityPanel({ traceability }: { traceability: GovernanceTraceability }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="mb-3 rounded-lg border border-indigo-200 bg-gradient-to-br from-indigo-50 to-blue-50 dark:border-indigo-800 dark:from-indigo-900/10 dark:to-blue-900/10 p-3">
      <div className="flex items-center gap-1.5 mb-2">
        <GitBranch className="w-3.5 h-3.5 text-indigo-700 dark:text-indigo-400" />
        <span className="text-[10px] font-semibold uppercase tracking-wider text-indigo-800 dark:text-indigo-300">
          Governance Traceability
        </span>
      </div>

      {/* Full chain counts */}
      <div className="grid grid-cols-3 gap-1.5 mb-2">
        <div className="rounded-md border border-indigo-200 bg-white/70 dark:border-indigo-800 dark:bg-navy-800/50 p-1.5 text-center">
          <p className="text-[7px] font-medium text-indigo-600 dark:text-indigo-400 uppercase tracking-wider">Policies</p>
          <p className="text-sm font-bold text-indigo-700 dark:text-indigo-300 tabular-nums">{traceability.linked_policy_count}</p>
        </div>
        <div className="rounded-md border border-blue-200 bg-white/70 dark:border-blue-800 dark:bg-navy-800/50 p-1.5 text-center">
          <p className="text-[7px] font-medium text-blue-600 dark:text-blue-400 uppercase tracking-wider">Rules</p>
          <p className="text-sm font-bold text-blue-700 dark:text-blue-300 tabular-nums">{traceability.linked_rule_count}</p>
        </div>
        <div className="rounded-md border border-amber-200 bg-white/70 dark:border-amber-800 dark:bg-navy-800/50 p-1.5 text-center">
          <p className="text-[7px] font-medium text-amber-600 dark:text-amber-400 uppercase tracking-wider">Requirements</p>
          <p className="text-sm font-bold text-amber-700 dark:text-amber-300 tabular-nums">{traceability.linked_requirement_count}</p>
        </div>
        <div className="rounded-md border border-red-200 bg-white/70 dark:border-red-800 dark:bg-navy-800/50 p-1.5 text-center">
          <p className="text-[7px] font-medium text-red-600 dark:text-red-400 uppercase tracking-wider">Violations</p>
          <p className="text-sm font-bold text-red-700 dark:text-red-300 tabular-nums">{traceability.linked_violation_count}</p>
        </div>
        <div className="rounded-md border border-orange-200 bg-white/70 dark:border-orange-800 dark:bg-navy-800/50 p-1.5 text-center">
          <p className="text-[7px] font-medium text-orange-600 dark:text-orange-400 uppercase tracking-wider">Findings</p>
          <p className="text-sm font-bold text-orange-700 dark:text-orange-300 tabular-nums">{traceability.linked_finding_count}</p>
        </div>
        <div className="rounded-md border border-rose-200 bg-white/70 dark:border-rose-800 dark:bg-navy-800/50 p-1.5 text-center">
          <p className="text-[7px] font-medium text-rose-600 dark:text-rose-400 uppercase tracking-wider">Redlines</p>
          <p className="text-sm font-bold text-rose-700 dark:text-rose-300 tabular-nums">{traceability.linked_redline_count}</p>
        </div>
      </div>

      {traceability.linked_policies.length > 0 && (
        <>
          <button
            type="button"
            onClick={() => setExpanded(!expanded)}
            className="flex items-center gap-1 text-[10px] font-medium text-indigo-600 hover:text-indigo-800 dark:text-indigo-400 dark:hover:text-indigo-300"
          >
            {expanded ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
            <span>{traceability.linked_policies.length} polic{traceability.linked_policies.length === 1 ? "y" : "ies"} applied</span>
          </button>

          {expanded && (
            <div className="mt-2 space-y-1.5">
              {traceability.linked_policies.map((policy) => (
                <div
                  key={policy.playbook_id}
                  className="flex items-center gap-2 rounded-md bg-white/60 dark:bg-navy-800/30 px-2 py-1.5 text-[10px]"
                >
                  <BookOpen className="w-3 h-3 text-indigo-500 flex-shrink-0" />
                  <span className="font-medium text-gray-700 dark:text-gray-300 truncate">
                    {policy.name}
                  </span>
                  {policy.version_label && (
                    <span className="ml-auto text-[8px] font-semibold px-1.5 py-0.5 rounded-full bg-indigo-100 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-300 flex-shrink-0">
                      v{policy.version_label}
                    </span>
                  )}
                </div>
              ))}
            </div>
          )}
        </>
      )}

      {/* Traceability chain summary */}
      <div className="mt-2 pt-2 border-t border-indigo-200/50 dark:border-indigo-800/50">
        <div className="flex items-center justify-between text-[8px] text-gray-500 dark:text-gray-400">
          <span className="inline-flex items-center gap-1">
            <span className="w-1.5 h-1.5 rounded-full bg-indigo-500" /> Policy
          </span>
          <span className="text-indigo-300">→</span>
          <span className="inline-flex items-center gap-1">
            <span className="w-1.5 h-1.5 rounded-full bg-blue-500" /> Rule
          </span>
          <span className="text-indigo-300">→</span>
          <span className="inline-flex items-center gap-1">
            <span className="w-1.5 h-1.5 rounded-full bg-amber-500" /> Req.
          </span>
          <span className="text-indigo-300">→</span>
          <span className="inline-flex items-center gap-1">
            <span className="w-1.5 h-1.5 rounded-full bg-red-500" /> Violation
          </span>
          <span className="text-indigo-300">→</span>
          <span className="inline-flex items-center gap-1">
            <span className="w-1.5 h-1.5 rounded-full bg-orange-500" /> Finding
          </span>
          <span className="text-indigo-300">→</span>
          <span className="inline-flex items-center gap-1">
            <span className="w-1.5 h-1.5 rounded-full bg-rose-500" /> Redline
          </span>
        </div>
      </div>
    </div>
  );
}

// ── Main Panel ────────────────────────────────────────────────────

export function RiskBreakdownPanel({ reviewId }: RiskBreakdownPanelProps) {
  const { data, isLoading, error, refetch } = useRiskBreakdown(reviewId);

  const hasDisplayableScore =
    Boolean(data) &&
    data!.status !== "no_analysis" &&
    data!.status !== "error" &&
    data!.status !== "not_found" &&
    data!.overall_risk_score > 0;

  const isEmpty =
    !data ||
    (data.breakdown.length === 0 &&
      data.status !== "no_analysis" &&
      data.status !== "error" &&
      data.status !== "not_found" &&
      !hasDisplayableScore);

  return (
    <AsyncBoundary
      isLoading={isLoading}
      error={error}
      isEmpty={isEmpty}
      loadingSkeleton={<CardSkeleton count={3} />}
      emptyMessage="No risk data available"
      emptyDescription="Risk breakdown will appear once AI analysis completes."
      onRetry={() => refetch()}
    >
      {data?.status === "no_analysis" || data?.status === "not_found" ? (
        <div className="rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800">
          <div className="text-center py-6">
            <Shield className="w-8 h-8 text-gray-300 mx-auto mb-2" />
            <p className="text-sm font-medium text-gray-500 dark:text-gray-400">AI Analysis Pending</p>
            <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">
              Risk breakdown will appear once AI analysis completes.
            </p>
          </div>
        </div>
      ) : data?.status === "error" ? (
        <div className="rounded-xl border border-red-200 bg-white p-4 dark:border-red-800 dark:bg-gray-800">
          <div className="text-center py-6">
            <Shield className="w-8 h-8 text-red-300 mx-auto mb-2" />
            <p className="text-sm font-medium text-red-600 dark:text-red-400">Unable to load risk data</p>
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
              Risk breakdown encountered an error. Please try again.
            </p>
            <button
              type="button"
              onClick={() => refetch()}
              className="mt-3 text-xs font-medium text-blue-600 hover:text-blue-700 dark:text-blue-400"
            >
              Retry
            </button>
          </div>
        </div>
      ) : data ? (
        <RenderRiskContent data={data} reviewId={reviewId} />
      ) : null}
    </AsyncBoundary>
  );
}

function RenderRiskContent({ data, reviewId }: { data: RiskBreakdown; reviewId: string }) {
  const currentRisk = data.current_contract_risk ?? data.remaining_exposure;
  const [activeTab, setActiveTab] = useState<string>("overview");

  // ── Exposure mode logic ──────────────────────────────────────
  // Before review: show "Detected Risk" (original AI score)
  // After review starts: show "Remaining Exposure" (current state)
  const isRemainingMode = data.exposure_mode === "remaining" || data.review_started;
  const ringScore = isRemainingMode ? currentRisk : data.overall_risk_score;
  const ringLabel = isRemainingMode ? "Remaining Exposure" : "Detected Risk";
  const ringSublabel = isRemainingMode ? data.remaining_label : data.overall_label;

  // Count open exposures for summary header
  const criticalCount = data.open_findings?.filter(f => f.severity === "critical").length ?? 0;
  const highCount = data.open_findings?.filter(f => f.severity === "high").length ?? 0;
  const totalOpen = data.open_findings?.length ?? 0;
  const totalMitigations = data.mitigation_suggestions?.length ?? 0;

  // ── Tab definitions ──────────────────────────────────────────
  const tabs = [
    { id: "overview", label: "Overview", icon: Shield, count: null },
    { id: "mitigations", label: "Mitigations", icon: TrendingDown, count: totalMitigations || undefined },
    { id: "exposure", label: "Exposure", icon: AlertTriangle, count: totalOpen || undefined },
    { id: "categories", label: "Categories", icon: FileText, count: data.breakdown.length || undefined },
  ];

  return (
    <div className="rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800">
      {/* ═══════════════════════════════════════════════════════════
          HEADER — Summary badges always visible
          ═══════════════════════════════════════════════════════════ */}
      <div className="flex items-center gap-2 mb-3">
        <Shield className="w-4 h-4 text-gray-500" />
        <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100">Risk Overview</h3>
        <div className="ml-auto flex items-center gap-2">
          {criticalCount > 0 && (
            <span className="text-[9px] font-semibold px-1.5 py-0.5 rounded-full bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400">
              {criticalCount} critical
            </span>
          )}
          {highCount > 0 && (
            <span className="text-[9px] font-semibold px-1.5 py-0.5 rounded-full bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400">
              {highCount} high
            </span>
          )}
          {totalOpen > 0 && (
            <span className="text-[9px] font-semibold px-1.5 py-0.5 rounded-full bg-gray-100 text-gray-500 dark:bg-gray-700 dark:text-gray-400">
              {totalOpen} open
            </span>
          )}
        </div>
      </div>

      {/* ═══════════════════════════════════════════════════════════
          TAB BAR
          ═══════════════════════════════════════════════════════════ */}
      <div className="flex gap-0.5 mb-3 border-b border-gray-200 dark:border-gray-700">
        {tabs.map((tab) => {
          const TabIcon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              type="button"
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-1.5 px-3 py-1.5 text-[10px] font-medium border-b-2 transition-colors ${
                isActive
                  ? "border-blue-500 text-blue-700 dark:border-blue-400 dark:text-blue-300"
                  : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 dark:text-gray-400 dark:hover:text-gray-200"
              }`}
            >
              <TabIcon className="w-3 h-3" />
              <span>{tab.label}</span>
              {tab.count != null && (
                <span className={`text-[8px] font-semibold px-1.5 py-0.5 rounded-full ${
                  isActive
                    ? "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300"
                    : "bg-gray-100 text-gray-500 dark:bg-gray-700 dark:text-gray-400"
                }`}>
                  {tab.count}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* ═══════════════════════════════════════════════════════════
          TAB: Overview — gauge + score stack + top actions
          ═══════════════════════════════════════════════════════════ */}
      {activeTab === "overview" && (
        <div>
          <div className="flex flex-col items-center mb-3">
            <RiskGauge
              score={ringScore}
              label={ringLabel}
              sublabel={ringSublabel}
            />
            {isRemainingMode && (
              <GaugeSecondaryMetrics
                originalScore={data.overall_risk_score}
                mitigatedReduction={data.risk_reduction}
                dismissedReduction={data.dismissed_reduction}
                acceptedReduction={data.accepted_reduction}
                remainingExposure={currentRisk}
              />
            )}
          </div>

          <div className="mb-3">
            <RiskScoreStack
              originalScore={data.overall_risk_score}
              mitigatedReduction={data.risk_reduction}
              dismissedReduction={data.dismissed_reduction}
              acceptedReduction={data.accepted_reduction}
              remainingExposure={currentRisk}
            />
          </div>

          {/* Financial Exposure — Estimated Business Impact */}
          {data.financial_impact && data.financial_impact.contract_value > 0 && (
            <FinancialImpactPanel impact={data.financial_impact} />
          )}

          {/* Governance Traceability — linked policies and rules */}
          {data.governance_traceability && data.governance_traceability.linked_policy_count > 0 && (
            <GovernanceTraceabilityPanel traceability={data.governance_traceability} />
          )}

          {data.top_recommended_actions && data.top_recommended_actions.top_actions?.length > 0 && (
            <TopActionsWidget
              actions={data.top_recommended_actions}
              currentRisk={currentRisk}
              originalRisk={data.overall_risk_score}
              reviewId={reviewId}
            />
          )}

          {/* Legend */}
          <div className="mt-4 flex flex-wrap items-center gap-x-3 gap-y-1 text-[9px] text-gray-400 border-t border-gray-100 pt-3 dark:border-gray-700">
            <span className="inline-flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-red-500" /> Open
            </span>
            <span className="inline-flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-green-500" /> Mitigated
            </span>
            <span className="inline-flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-orange-500" /> Accepted Exposure
            </span>
            <span className="inline-flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-gray-400" /> Removed Exposure
            </span>
          </div>
        </div>
      )}

      {/* ═══════════════════════════════════════════════════════════
          TAB: Mitigations — effectiveness + suggestions + decisions
          ═══════════════════════════════════════════════════════════ */}
      {activeTab === "mitigations" && (
        <div className="space-y-3">
          {isRemainingMode && (
            <>
              <MitigationEffectiveness
                originalScore={data.overall_risk_score}
                mitigatedReduction={data.risk_reduction}
                dismissedReduction={data.dismissed_reduction}
                acceptedReduction={data.accepted_reduction}
                remainingExposure={currentRisk}
              />
              <RiskDeltaTimeline data={data} />
            </>
          )}

          {data.mitigation_suggestions && data.mitigation_suggestions.length > 0 && (
            <div>
              <h4 className="text-[10px] font-semibold text-gray-700 dark:text-gray-300 mb-2">
                Recommended Mitigations
              </h4>
              <MitigationSuggestionsPanel
                suggestions={data.mitigation_suggestions}
              />
            </div>
          )}

          {(data.mitigated_findings?.length || data.accepted_risk_findings?.length || data.dismissed_findings?.length) ? (
            <div>
              <h4 className="text-[10px] font-semibold text-gray-700 dark:text-gray-300 mb-2">
                Review Decisions
              </h4>
              <div className="space-y-2">
                {data.mitigated_findings && data.mitigated_findings.length > 0 && (
                  <ResolvedSection
                    title="Mitigated Risks"
                    icon={<CheckCircle2 className="w-4 h-4" />}
                    findings={data.mitigated_findings}
                    bgColor="bg-green-50/80 dark:bg-green-900/10"
                    borderColor="border-green-200 dark:border-green-800"
                    textColor="text-green-700 dark:text-green-300"
                    iconColor="text-green-600"
                  />
                )}
                {data.accepted_risk_findings && data.accepted_risk_findings.length > 0 && (
                  <ResolvedSection
                    title="Accepted Exposure"
                    icon={<Info className="w-4 h-4" />}
                    findings={data.accepted_risk_findings}
                    bgColor="bg-orange-50/80 dark:bg-orange-900/10"
                    borderColor="border-orange-200 dark:border-orange-800"
                    textColor="text-orange-700 dark:text-orange-300"
                    iconColor="text-orange-600"
                  />
                )}
                {data.dismissed_findings && data.dismissed_findings.length > 0 && (
                  <ResolvedSection
                    title="Removed Exposure"
                    icon={<XCircle className="w-4 h-4" />}
                    findings={data.dismissed_findings}
                    bgColor="bg-gray-50/80 dark:bg-gray-800/50"
                    borderColor="border-gray-200 dark:border-gray-700"
                    textColor="text-gray-600 dark:text-gray-400"
                    iconColor="text-gray-400"
                  />
                )}
              </div>
            </div>
          ) : null}
        </div>
      )}

      {/* ═══════════════════════════════════════════════════════════
          TAB: Exposure — open findings
          ═══════════════════════════════════════════════════════════ */}
      {activeTab === "exposure" && (
        <div className="space-y-3">
          {data.open_findings && data.open_findings.length > 0 ? (
            <GroupedOpenExposures findings={data.open_findings} />
          ) : (
            <div className="text-center py-6">
              <CheckCircle2 className="w-6 h-6 text-green-400 mx-auto mb-2" />
              <p className="text-xs font-medium text-gray-500 dark:text-gray-400">No open exposures</p>
              <p className="text-[10px] text-gray-400 dark:text-gray-500 mt-1">
                All findings have been resolved.
              </p>
            </div>
          )}

          {data.exposure_contributors && data.exposure_contributors.length > 0 && (
            <div>
              <h4 className="text-[10px] font-semibold text-gray-700 dark:text-gray-300 mb-2">
                Exposure Contributors
              </h4>
              <ExposureContributorsPanel
                contributors={data.exposure_contributors}
                remainingExposure={data.remaining_exposure}
              />
            </div>
          )}
        </div>
      )}

      {/* ═══════════════════════════════════════════════════════════
          TAB: Categories — breakdown bars
          ═══════════════════════════════════════════════════════════ */}
      {activeTab === "categories" && (
        <div className="space-y-3">
          {data.breakdown.length > 0 ? (
            data.breakdown.map((item) => (
              <ContributionBar
                key={item.category}
                item={item}
                useRemaining={isRemainingMode}
                maxContribution={
                  isRemainingMode
                    ? (data.breakdown[0]?.normalized_contribution || 0.001)
                    : (data.breakdown[0]?.contribution || 0.001)
                }
              />
            ))
          ) : (
            <p className="text-xs text-gray-500 dark:text-gray-400 py-2">
              Category breakdown is not available for this analysis run.
            </p>
          )}
        </div>
      )}
    </div>
  );
}

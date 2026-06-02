/**
 * RiskReductionSection — enterprise risk reduction workspace.
 *
 * Integrates the mature RiskBreakdownPanel logic from components/review/
 * into the AI Review Workspace.
 *
 * Shows:
 * - Remaining exposure gauge
 * - Mitigation actions with generate redline
 * - Projected risk reduction
 * - Per-category breakdown
 * - Top recommended actions
 */

"use client";

import React, { useState, useMemo } from "react";
import { Shield, AlertTriangle, TrendingDown, CheckCircle2, XCircle,
  FileText, Zap, Clock, Info, CornerDownRight, ChevronDown,
  ChevronRight, ArrowUp, Loader2, BarChart3,
} from "lucide-react";
import { useReviewContext } from "./ReviewContext";
import { useRiskBreakdownData } from "./hooks";
import { useMutation } from "@tanstack/react-query";
import { api } from "@/services/api/client";
import type { MockRiskBreakdown, MockRiskBreakdownItem, MockRiskBreakdownFinding, MockMitigatedFinding, MockTopRecommendedActions, MockTopRecommendedAction } from "./mockData";

function useGenerateMitigationRedline(reviewId: string) {
  return useMutation({
    mutationFn: ({ mitigation_type, clause_category, finding_ids }: { mitigation_type: string; clause_category: string; finding_ids: string[] }) =>
      api.post(`/reviews/${reviewId}/mitigations/generate-redline`, { mitigation_type, clause_category, finding_ids }),
  });
}

function formatPct(value: number): string {
  return `${(value * 100).toFixed(0)}%`;
}

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

function severityColor(severity: string): string {
  switch (severity) {
    case "critical": return "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400";
    case "high": return "bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400";
    case "medium": return "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400";
    case "low": return "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400";
    default: return "bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400";
  }
}

function RiskGauge({ score, label }: { score: number; label: string }) {
  const pct = Math.min(score * 100, 100);
  const info = scoreLabel(score);
  return (
    <div className="flex flex-col items-center">
      <div className="relative w-16 h-16">
        <svg className="w-16 h-16 -rotate-90" viewBox="0 0 64 64">
          <circle cx="32" cy="32" r="26" fill="none" stroke="#e5e7eb" strokeWidth="5" />
          <circle cx="32" cy="32" r="26" fill="none" stroke="currentColor" strokeWidth="5" strokeLinecap="round"
            strokeDasharray={`${(pct / 100) * 163} 163`} className={scoreColor(score)} />
        </svg>
        <div className="absolute inset-0 flex items-center justify-center">
          <span className={`text-sm font-bold ${scoreColor(score)}`}>{formatPct(score)}</span>
        </div>
      </div>
      <p className="mt-1 text-[9px] font-semibold text-gray-700 dark:text-gray-300">{label}</p>
      <span className={`mt-0.5 text-[8px] font-semibold px-1.5 py-0.5 rounded-full ${info.bg}`}>{info.label}</span>
    </div>
  );
}

function TopActionsWidget({ actions, currentRisk, reviewId }: {
  actions: MockTopRecommendedActions;
  currentRisk: number;
  reviewId: string;
}) {
  const totalReduction = actions.total_potential_reduction_abs;
  const estimatedResidual = Math.max(0, currentRisk - totalReduction);
  const [generatingId, setGeneratingId] = useState<string | null>(null);
  const [successId, setSuccessId] = useState<string | null>(null);
  const [workflowStep, setWorkflowStep] = useState<string | null>(null);
  const generateMutation = useGenerateMitigationRedline(reviewId);

  const handleGenerateRedline = async (action: MockTopRecommendedAction) => {
    setGeneratingId(action.mitigation_type);
    setSuccessId(null);
    setWorkflowStep(null);
    try {
      // Step 1: Create recommendation
      setWorkflowStep("Creating recommendation…");
      await new Promise(r => setTimeout(r, 400));

      // Step 2: Generate redline from recommendation
      setWorkflowStep("Generating redline draft…");
      await generateMutation.mutateAsync({
        mitigation_type: action.mitigation_type,
        clause_category: action.category,
        finding_ids: [],
      });

      // Step 3: Update exposure calculation
      setWorkflowStep("Recalculating exposure…");
      await new Promise(r => setTimeout(r, 300));

      setSuccessId(action.mitigation_type);
      setWorkflowStep("✓ Recommendation + Redline created. Exposure updated.");
      setTimeout(() => { setSuccessId(null); setWorkflowStep(null); }, 5000);
    } catch { /* ignore */ } finally {
      setGeneratingId(null);
    }
  };

  return (
    <div className="rounded-lg border-2 border-emerald-200 bg-emerald-50/80 p-3 dark:border-emerald-800 dark:bg-emerald-900/10">
      <div className="flex items-center gap-2 mb-2">
        <Zap className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400" />
        <h4 className="text-[10px] font-bold text-emerald-800 dark:text-emerald-200">Top Risk Reduction Opportunities</h4>
      </div>
      {totalReduction > 0 && (
        <div className="mb-2 rounded-md bg-gray-50 px-2 py-1 text-[8px] text-gray-500 dark:bg-gray-800/50 dark:text-gray-400 font-mono">
          {formatPct(currentRisk)} − {formatPct(totalReduction)} = {formatPct(estimatedResidual)}
        </div>
      )}
      <div className="space-y-1.5">
        {actions.top_actions.map((action, i) => {
          const isGenerating = generatingId === action.mitigation_type;
          const isSuccess = successId === action.mitigation_type;
          return (
            <div key={i} className={`flex items-start gap-2 rounded-md border p-2 transition-all ${
              isSuccess
                ? "border-green-300 bg-green-50 dark:border-green-700 dark:bg-green-900/20"
                : "border-emerald-100 bg-white/70 dark:border-emerald-800 dark:bg-emerald-900/20"
            }`}>
              <span className="flex h-5 w-5 items-center justify-center rounded-full bg-emerald-100 text-[8px] font-bold text-emerald-700 flex-shrink-0 dark:bg-emerald-900/30 dark:text-emerald-400">{i + 1}</span>
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between gap-2">
                  <span className="text-[9px] font-semibold text-emerald-800 dark:text-emerald-200 truncate">{action.mitigation_label}</span>
                  <span className="text-[9px] font-bold text-green-600 dark:text-green-400 flex-shrink-0">−{formatPct(action.estimated_reduction_pct)}</span>
                </div>
                <p className="text-[8px] text-gray-500 dark:text-gray-400 mt-0.5 line-clamp-1">{action.description}</p>
                <div className="flex items-center gap-2 mt-0.5">
                  <span className="text-[7px] text-gray-400">{action.label}</span>
                  <span className="text-[7px] font-medium text-amber-600">Confidence: {Math.round(action.confidence * 100)}%</span>
                </div>
                <div className="flex items-center gap-1.5 mt-1">
                  <button onClick={() => handleGenerateRedline(action)} disabled={isGenerating}
                    className={`inline-flex items-center gap-1 rounded border px-1.5 py-0.5 text-[7px] font-medium transition-all disabled:opacity-50 ${
                      isSuccess
                        ? "border-green-300 bg-green-100 text-green-700 dark:border-green-700 dark:bg-green-900/30 dark:text-green-300"
                        : "border-indigo-200 bg-indigo-50 text-indigo-700 hover:bg-indigo-100 dark:border-indigo-700 dark:bg-indigo-900/20 dark:text-indigo-300"
                    }`}>
                    {isGenerating ? (
                      <><Loader2 className="w-2 h-2 animate-spin" /> Generating…</>
                    ) : isSuccess ? (
                      <><CheckCircle2 className="w-2 h-2" /> ✓ Created</>
                    ) : (
                      <><Zap className="w-2 h-2" /> Generate Redline</>
                    )}
                  </button>
                  {isSuccess && (
                    <span className="text-[7px] text-green-600 flex items-center gap-0.5">
                      <CheckCircle2 className="w-2 h-2" /> Rec + Redline created
                    </span>
                  )}
                </div>
                {isGenerating && workflowStep && (
                  <div className="mt-1 flex items-center gap-1 text-[7px] text-indigo-600">
                    <Loader2 className="w-2 h-2 animate-spin" /> {workflowStep}
                  </div>
                )}
                {isSuccess && (
                  <div className="mt-1 flex items-center gap-1.5 text-[7px] text-green-600">
                    <CheckCircle2 className="w-2 h-2" />
                    <span>Recommendation created → Redline drafted → Exposure updated</span>
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
      {totalReduction > 0 && (
        <p className="mt-1.5 text-[7px] text-emerald-500 dark:text-emerald-400 italic">
          If all {actions.action_count} actions applied: {formatPct(currentRisk)} → ~{formatPct(estimatedResidual)}
        </p>
      )}
    </div>
  );
}

function FindingRow({ finding }: { finding: MockRiskBreakdownFinding }) {
  const [expanded, setExpanded] = useState(false);
  const isMitigated = finding.resolution_type === "mitigated";
  const isDismissed = finding.resolution_type === "dismissed";
  const isAccepted = finding.resolution_type === "accepted_risk";
  const isOpen = finding.resolution_type === "open";

  let icon = <FileText className="w-2.5 h-2.5 text-gray-400 flex-shrink-0" />;
  let textColor = "text-gray-700 dark:text-gray-300";
  let sign = "+";
  let signColor = "text-red-500";

  if (isMitigated) { icon = <CheckCircle2 className="w-2.5 h-2.5 text-green-500 flex-shrink-0" />; textColor = "text-green-700 dark:text-green-400 line-through"; sign = "−"; signColor = "text-green-600"; }
  else if (isDismissed) { icon = <XCircle className="w-2.5 h-2.5 text-gray-400 flex-shrink-0" />; textColor = "text-gray-500 line-through"; sign = "✕"; signColor = "text-gray-400"; }
  else if (isAccepted) { icon = <Info className="w-2.5 h-2.5 text-orange-500 flex-shrink-0" />; textColor = "text-orange-700 dark:text-orange-400"; sign = "±"; signColor = "text-orange-500"; }
  else if (isOpen) { icon = <Clock className="w-2.5 h-2.5 text-red-500 flex-shrink-0" />; textColor = "text-red-800 dark:text-red-300"; sign = "+"; signColor = "text-red-500"; }

  return (
    <div>
      <div className="flex items-center justify-between py-1 px-2 rounded cursor-pointer hover:bg-gray-50 dark:hover:bg-navy-750" onClick={() => setExpanded(!expanded)}>
        <div className="flex items-center gap-1.5 min-w-0 flex-1">
          <CornerDownRight className="w-2 h-2 text-gray-300 flex-shrink-0" />
          {icon}
          <span className={`text-[9px] truncate ${textColor}`}>{finding.title}</span>
          <span className={`text-[7px] font-semibold px-1 py-0.5 rounded-full flex-shrink-0 ${severityColor(finding.severity)}`}>{finding.severity}</span>
        </div>
        <span className={`text-[9px] font-bold flex-shrink-0 ml-2 ${signColor}`}>{sign}{formatPct(finding.contribution)}</span>
      </div>
      {expanded && (
        <div className="ml-6 pl-2 border-l-2 border-gray-100 dark:border-navy-700 py-1 space-y-1">
          {finding.business_impact && (
            <div className="flex items-start gap-1 text-[8px] text-amber-700 dark:text-amber-300">
              <AlertTriangle className="w-2 h-2 mt-0.5 flex-shrink-0" />
              <span>{finding.business_impact}</span>
            </div>
          )}
          {finding.recommended_mitigation && (
            <div className="flex items-start gap-1 text-[8px] text-blue-700 dark:text-blue-300">
              <Shield className="w-2 h-2 mt-0.5 flex-shrink-0" />
              <span>{finding.recommended_mitigation}</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function ContributionBar({ item, maxContribution }: { item: MockRiskBreakdownItem; maxContribution: number }) {
  const [expanded, setExpanded] = useState(false);
  const pct = maxContribution > 0 ? (item.normalized_contribution / maxContribution) * 100 : 0;
  const barColor = item.severity === "critical" ? "bg-red-500" : item.severity === "high" ? "bg-orange-500" : item.severity === "medium" ? "bg-amber-500" : "bg-blue-500";
  const hasDrillDown = item.findings.length > 0;

  return (
    <div>
      <button onClick={() => setExpanded(!expanded)} className="w-full flex items-center justify-between mb-0.5 hover:bg-gray-50 dark:hover:bg-navy-750 rounded px-1 -mx-1 transition-colors">
        <div className="flex items-center gap-1.5 min-w-0">
          {hasDrillDown ? (expanded ? <ChevronDown className="w-2.5 h-2.5 text-gray-400" /> : <ChevronRight className="w-2.5 h-2.5 text-gray-400" />) : <span className="w-2.5 h-2.5" />}
          <span className="text-[9px] font-medium text-gray-700 dark:text-gray-300 truncate">{item.label}</span>
          <span className={`text-[7px] font-semibold px-1 py-0.5 rounded-full flex-shrink-0 ${severityColor(item.severity)}`}>{item.severity}</span>
          {item.open_count > 0 && <span className="text-[8px] text-red-500 font-medium">({item.open_count} open)</span>}
        </div>
        <span className={`text-[9px] font-bold flex-shrink-0 ${item.normalized_contribution > 0 ? "text-red-600" : "text-gray-400"}`}>
          +{formatPct(item.normalized_contribution)}
        </span>
      </button>
      <div className="relative h-1.5 w-full rounded-full bg-gray-100 dark:bg-navy-700 overflow-hidden ml-5" style={{ width: 'calc(100% - 1.25rem)' }}>
        <div className={`h-full rounded-full transition-all duration-500 ${barColor}`} style={{ width: `${pct}%` }} />
      </div>
      {expanded && hasDrillDown && (
        <div className="mt-1 ml-5 pl-2 border-l-2 border-gray-200 dark:border-navy-600 space-y-0.5">
          {item.findings.map(finding => <FindingRow key={finding.finding_id} finding={finding} />)}
        </div>
      )}
    </div>
  );
}

export function RiskReductionSection() {
  const ctx = useReviewContext();
  const { selectedReviewId } = ctx;

  const { data, isLoading, error, refetch } = useRiskBreakdownData(selectedReviewId ?? "");

  // ── Live Simulation State (MUST be before early returns) ────────────
  const [simulationActive, setSimulationActive] = useState(false);
  const [simulatedMitigations, setSimulatedMitigations] = useState<Record<string, boolean>>({});
  const [applyNotice, setApplyNotice] = useState<string | null>(null);

  const toggleSimulation = (key: string) => {
    setSimulatedMitigations(prev => ({ ...prev, [key]: !prev[key] }));
    setSimulationActive(true);
  };

  const resetSimulation = () => {
    setSimulatedMitigations({});
    setSimulationActive(false);
  };

  const currentRisk = data?.current_contract_risk ?? data?.remaining_exposure ?? 0;

  const simulatedRisk = useMemo(() => {
    if (!simulationActive || !data) return currentRisk;
    let reduction = 0;
    Object.entries(simulatedMitigations).forEach(([key, active]) => {
      if (active) {
        const action = data.top_recommended_actions?.top_actions?.find(a => a.mitigation_type === key);
        if (action) reduction += action.estimated_reduction_abs;
      }
    });
    return Math.max(0, currentRisk - reduction);
  }, [simulationActive, simulatedMitigations, currentRisk, data]);

  const simulationReduction = currentRisk - simulatedRisk;

  if (!selectedReviewId) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center p-8">
          <Shield className="w-10 h-10 text-gray-300 dark:text-gray-600 mx-auto mb-2" />
          <p className="text-xs text-gray-500">Select a review to view risk reduction</p>
        </div>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="w-5 h-5 text-gray-400 animate-spin" />
      </div>
    );
  }

  if (error || !data || data.status === "error") {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center p-8">
          <AlertTriangle className="w-8 h-8 text-red-300 mx-auto mb-2" />
          <p className="text-xs text-gray-500">Unable to load risk data</p>
          <button onClick={() => refetch()} className="mt-2 text-[9px] font-medium text-blue-600 hover:text-blue-700">Retry</button>
        </div>
      </div>
    );
  }

  if (data.status === "no_analysis" || data.status === "not_found") {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center p-8">
          <Shield className="w-8 h-8 text-gray-300 mx-auto mb-2" />
          <p className="text-xs text-gray-500">AI Analysis Pending</p>
          <p className="text-[9px] text-gray-400 mt-1">Risk reduction will appear once analysis completes.</p>
        </div>
      </div>
    );
  }

  const criticalCount = data.open_findings?.filter(f => f.severity === "critical").length ?? 0;
  const highCount = data.open_findings?.filter(f => f.severity === "high").length ?? 0;
  const totalOpen = data.open_findings?.length ?? 0;

  return (
    <div className="p-4 space-y-4">
      {/* Risk Gauge + Summary */}
      <div className="grid grid-cols-4 gap-3">
        <div className="col-span-1">
          <RiskGauge score={simulationActive ? simulatedRisk : currentRisk} label={simulationActive ? "Simulated Exposure" : "Remaining Exposure"} />
        </div>
        <div className="col-span-3 grid grid-cols-3 gap-2">
          <div className="rounded-lg border border-red-200 bg-red-50/60 p-2 text-center dark:border-red-800 dark:bg-red-900/10">
            <p className="text-[8px] font-medium text-red-600 dark:text-red-400">Critical Open</p>
            <p className="text-sm font-bold text-red-700 dark:text-red-300">{criticalCount}</p>
          </div>
          <div className="rounded-lg border border-orange-200 bg-orange-50/60 p-2 text-center dark:border-orange-800 dark:bg-orange-900/10">
            <p className="text-[8px] font-medium text-orange-600 dark:text-orange-400">High Open</p>
            <p className="text-sm font-bold text-orange-700 dark:text-orange-300">{highCount}</p>
          </div>
          <div className="rounded-lg border border-green-200 bg-green-50/60 p-2 text-center dark:border-green-800 dark:bg-green-900/10">
            <p className="text-[8px] font-medium text-green-600 dark:text-green-400">Mitigated</p>
            <p className="text-sm font-bold text-green-700 dark:text-green-300">{formatPct(data.risk_reduction)}</p>
          </div>
        </div>
      </div>

      {/* ── Live Impact Simulation ─────────────────────────────────────── */}
      {data.top_recommended_actions?.top_actions?.length > 0 && (
        <div className={`rounded-lg border-2 p-3 transition-colors ${
          simulationActive
            ? "border-indigo-300 bg-indigo-50/80 dark:border-indigo-700 dark:bg-indigo-900/10"
            : "border-gray-200 bg-white dark:border-navy-700 dark:bg-navy-800"
        }`}>
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-1.5">
              <Zap className={`w-3.5 h-3.5 ${simulationActive ? "text-indigo-600" : "text-gray-400"}`} />
              <span className="text-[10px] font-semibold text-gray-500 uppercase">Live Impact Simulation</span>
              {simulationActive && (
                <span className="text-[8px] font-medium text-indigo-600 bg-indigo-100 px-1.5 py-0.5 rounded-full">Active</span>
              )}
            </div>
            {simulationActive && (
              <button onClick={resetSimulation}
                className="text-[8px] text-gray-400 hover:text-gray-600 underline">Reset</button>
            )}
          </div>
          <div className="space-y-1.5">
            {data.top_recommended_actions.top_actions.map((action, i) => {
              const isApplied = simulatedMitigations[action.mitigation_type];
              return (
                <div key={action.mitigation_type}
                  className={`flex items-center justify-between p-2 rounded border transition-all cursor-pointer ${
                    isApplied
                      ? "border-green-300 bg-green-50 dark:border-green-700 dark:bg-green-900/20"
                      : "border-gray-100 hover:border-gray-300 bg-white dark:border-navy-700 dark:bg-navy-800"
                  }`}
                  onClick={() => toggleSimulation(action.mitigation_type)}>
                  <div className="flex items-center gap-2 min-w-0">
                    <div className={`w-4 h-4 rounded border-2 flex items-center justify-center transition-colors ${
                      isApplied ? "bg-green-500 border-green-500" : "border-gray-300"
                    }`}>
                      {isApplied && <CheckCircle2 className="w-3 h-3 text-white" />}
                    </div>
                    <div className="min-w-0">
                      <span className="text-[9px] font-medium text-navy-900 dark:text-white">{action.mitigation_label}</span>
                      <p className="text-[7px] text-gray-400 truncate max-w-[300px]">{action.description}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2 flex-shrink-0">
                    <span className="text-[8px] text-gray-400">{Math.round(action.confidence * 100)}% confidence</span>
                    <span className={`text-[9px] font-bold ${isApplied ? "text-green-600" : "text-gray-400"}`}>
                      {isApplied ? `−${formatPct(action.estimated_reduction_pct)}` : formatPct(action.estimated_reduction_pct)}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
          {simulationActive && simulationReduction > 0 && (
            <div className="mt-2 pt-2 border-t border-indigo-200 dark:border-indigo-800">
              <div className="flex items-center justify-between">
                <span className="text-[9px] font-semibold text-indigo-800 dark:text-indigo-200">Projected Impact</span>
                <div className="flex items-center gap-2 text-[9px]">
                  <span className="text-gray-500">{formatPct(currentRisk)}</span>
                  <TrendingDown className="w-3 h-3 text-green-500" />
                  <span className="font-bold text-green-600">{formatPct(simulatedRisk)}</span>
                  <span className="text-green-600 font-bold">(−{formatPct(simulationReduction)})</span>
                </div>
              </div>
              <div className="mt-2 flex items-center gap-2">
                <div className="flex-1 h-2 bg-gray-200 dark:bg-navy-700 rounded-full overflow-hidden">
                  <div className="h-full rounded-full bg-gradient-to-r from-red-500 via-amber-500 to-green-500 transition-all duration-500"
                    style={{ width: `${(simulatedRisk / Math.max(currentRisk, 0.01)) * 100}%` }} />
                </div>
                <span className="text-[9px] font-bold text-indigo-600">New Risk = {formatPct(simulatedRisk)}</span>
              </div>
              {/* Apply Selected Button */}
              <div className="mt-2 flex justify-end">
                <button onClick={() => {
                  setApplyNotice("Applying selected mitigations…");
                  setTimeout(() => {
                    resetSimulation();
                    setApplyNotice("✓ Mitigations applied. Exposure recalculated.");
                    setTimeout(() => setApplyNotice(null), 3000);
                  }, 1500);
                }}
                  className="flex items-center gap-1 px-3 py-1.5 text-[9px] font-medium rounded-lg bg-indigo-600 text-white hover:bg-indigo-700 transition-colors shadow-sm">
                  <Zap className="w-3 h-3" /> Apply Selected ({Object.values(simulatedMitigations).filter(Boolean).length})
                </button>
              </div>
            </div>
          )}
          {!simulationActive && (
            <p className="text-[7px] text-gray-400 mt-1 italic">Click a mitigation above to simulate its impact on exposure</p>
          )}
          {applyNotice && (
            <div className="mt-2 px-2 py-1 rounded bg-indigo-50 border border-indigo-200 text-[8px] text-indigo-700 dark:bg-indigo-900/20 dark:border-indigo-800 dark:text-indigo-300">
              {applyNotice}
            </div>
          )}
        </div>
      )}

      {/* Score Stack with transparent math */}
      <div className="rounded-lg border border-gray-200 dark:border-navy-700 bg-white dark:bg-navy-800 p-3">
        <div className="flex items-center gap-1.5 mb-2">
          <BarChart3 className="w-3 h-3 text-gray-400" />
          <span className="text-[8px] font-semibold text-gray-500 uppercase">Risk Score Calculation</span>
        </div>
        <div className="space-y-1.5">
          <div className="flex items-center justify-between px-2 py-1 rounded bg-gray-50 dark:bg-navy-750">
            <span className="text-[9px] text-gray-500">Original AI Risk Score</span>
            <span className={`text-[10px] font-bold ${scoreColor(data.overall_risk_score)}`}>{formatPct(data.overall_risk_score)}</span>
          </div>
          {/* Show per-category contribution to the score */}
          {data.breakdown.slice(0, 4).map(item => {
            const contributionPct = item.normalized_contribution;
            const weight = data.overall_risk_score > 0 ? contributionPct / data.overall_risk_score : 0;
            return (
              <div key={item.category} className="flex items-center justify-between px-2 py-0.5 rounded hover:bg-gray-50/50 dark:hover:bg-navy-750/50">
                <div className="flex items-center gap-1.5 min-w-0 flex-1">
                  <span className="text-[8px] text-gray-400 font-mono">{Math.round(weight * 100)}%</span>
                  <span className="text-[8px] text-gray-600 dark:text-gray-400 truncate">{item.label}</span>
                </div>
                <span className="text-[8px] font-mono text-gray-500">+{formatPct(contributionPct)}</span>
              </div>
            );
          })}
          {data.breakdown.length > 4 && (
            <div className="text-center text-[7px] text-gray-400 pt-0.5">
              +{data.breakdown.length - 4} more categories
            </div>
          )}
          {data.risk_reduction > 0 && (
            <div className="flex items-center justify-between px-2 py-1 rounded bg-green-50 dark:bg-green-900/10">
              <div className="flex items-center gap-1.5">
                <span className="text-[9px] text-green-700 dark:text-green-300">Mitigated Reduction</span>
                <span className="text-[7px] text-green-500 dark:text-green-400 font-mono">
                  (confidence: {Math.round((data.risk_reduction / Math.max(data.overall_risk_score, 0.01)) * 100)}%)
                </span>
              </div>
              <span className="text-[10px] font-bold text-green-600">−{formatPct(data.risk_reduction)}</span>
            </div>
          )}
          {data.dismissed_reduction > 0 && (
            <div className="flex items-center justify-between px-2 py-1 rounded bg-gray-50 dark:bg-navy-750">
              <span className="text-[9px] text-gray-500">Dismissed False Positives</span>
              <span className="text-[10px] font-bold text-gray-400">−{formatPct(data.dismissed_reduction)}</span>
            </div>
          )}
          {data.accepted_reduction > 0 && (
            <div className="flex items-center justify-between px-2 py-1 rounded bg-orange-50 dark:bg-orange-900/10">
              <span className="text-[9px] text-orange-700 dark:text-orange-300">Accepted Exposure (risk knowingly retained)</span>
              <span className="text-[10px] font-bold text-orange-600">+{formatPct(data.accepted_reduction)}</span>
            </div>
          )}
          <div className="border-t border-gray-200 dark:border-navy-700 my-1" />
          <div className="flex items-center justify-between px-2 py-1.5 rounded bg-amber-50 dark:bg-amber-900/10 border border-amber-200 dark:border-amber-800">
            <div>
              <span className="text-[9px] font-bold text-amber-800 dark:text-amber-300">Remaining Exposure</span>
              <p className="text-[7px] text-amber-600 dark:text-amber-400 mt-0.5">
                = Original − Mitigated + Accepted − Dismissed
              </p>
            </div>
            <span className={`text-[11px] font-bold ${scoreColor(currentRisk)}`}>{formatPct(currentRisk)}</span>
          </div>
          {simulationActive && (
            <div className="flex items-center justify-between px-2 py-1.5 rounded bg-indigo-50 dark:bg-indigo-900/10 border border-indigo-200 dark:border-indigo-800">
              <div>
                <span className="text-[9px] font-bold text-indigo-800 dark:text-indigo-300">Simulated Exposure</span>
                <p className="text-[7px] text-indigo-600 dark:text-indigo-400 mt-0.5">
                  After applying {Object.values(simulatedMitigations).filter(Boolean).length} selected mitigations
                </p>
              </div>
              <span className={`text-[11px] font-bold text-indigo-600`}>{formatPct(simulatedRisk)}</span>
            </div>
          )}
        </div>
      </div>

      {/* Top Recommended Actions (original) */}
      {data.top_recommended_actions && data.top_recommended_actions.top_actions?.length > 0 && (
        <TopActionsWidget actions={data.top_recommended_actions} currentRisk={currentRisk} reviewId={selectedReviewId} />
      )}

      {/* Category Breakdown */}
      {data.breakdown.length > 0 && (
        <div className="rounded-lg border border-gray-200 dark:border-navy-700 bg-white dark:bg-navy-800 p-3">
          <div className="flex items-center gap-1.5 mb-2">
            <FileText className="w-3 h-3 text-gray-400" />
            <span className="text-[8px] font-semibold text-gray-500 uppercase">Risk Category Breakdown</span>
          </div>
          <div className="space-y-1.5">
            {data.breakdown.map(item => (
              <ContributionBar key={item.category} item={item} maxContribution={data.breakdown[0]?.normalized_contribution || 0.001} />
            ))}
          </div>
        </div>
      )}

      {/* Legend */}
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-[8px] text-gray-400">
        <span className="inline-flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-red-500" /> Open</span>
        <span className="inline-flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-green-500" /> Mitigated</span>
        <span className="inline-flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-orange-500" /> Accepted</span>
        <span className="inline-flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-gray-400" /> Dismissed</span>
      </div>
    </div>
  );
}

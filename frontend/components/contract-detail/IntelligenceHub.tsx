/**
 * IntelligenceHub — a single-screen, glanceable summary of a contract's
 * risk posture, findings, clauses, policy, related reviews and obligations.
 *
 * Rendered inside the Overview tab so a reviewer can triage the contract
 * without having to switch tabs. Each section is a compact card; if the
 * underlying data is missing the card shows a friendly "no data yet"
 * state instead of disappearing silently.
 */

"use client";

import React, { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  AlertTriangle, CheckCircle2, XCircle, FileText, GitBranch,
  TrendingUp, Shield, Clock, BookOpen, Sparkles,
} from "lucide-react";
import type { AiFinding, ClauseDeviation, Obligation } from "./types";
import { api } from "@/services/api/client";
import { formatDate } from "@/lib/date-utils";

interface IntelligenceHubProps {
  findings: AiFinding[];
  clauses: ClauseDeviation[];
  obligations: Obligation[];
  contractId: string;
  /** Display risk score (0–10). */
  riskScore: number;
  /** Total AI findings count. */
  findingCount: number;
}

interface PolicyViolation {
  id: string;
  rule?: string;
  policy_rule_name?: string;
  policy_name?: string;
  finding_title?: string;
  severity: string;
  status: string;
}

interface RelatedReview {
  id: string;
  document_name?: string;
  status?: string;
  finding_count?: number;
  updated_at?: string;
}

export function IntelligenceHub({
  findings, clauses, obligations, contractId, riskScore, findingCount,
}: IntelligenceHubProps) {
  // ── Findings breakdown by severity ──────────────────────────────
  const breakdown = useMemo(() => {
    const acc: Record<string, number> = { critical: 0, high: 0, medium: 0, low: 0, info: 0 };
    for (const f of findings) {
      const k = (f.severity ?? "info").toLowerCase();
      if (k in acc) acc[k] += 1;
    }
    return acc;
  }, [findings]);

  // ── Top clauses by severity (limit 5) ───────────────────────────
  const topClauses = useMemo(() => {
    const order: Record<string, number> = { critical: 0, high: 1, medium: 2, low: 3, info: 4 };
    return [...clauses]
      .sort((a, b) => (order[a.severity] ?? 9) - (order[b.severity] ?? 9))
      .slice(0, 5);
  }, [clauses]);

  // ── Top contributing finding (for "How is this calculated?") ────
  const topContributor = useMemo(() => {
    const order: Record<string, number> = { critical: 0, high: 1, medium: 2, low: 3, info: 4 };
    return [...findings].sort(
      (a, b) => (order[a.severity] ?? 9) - (order[b.severity] ?? 9),
    )[0];
  }, [findings]);

  // ── Policy violations (best-effort fetch) ───────────────────────
  const { data: policyData } = useQuery<{ violations?: PolicyViolation[] }>({
    queryKey: ["contract-policy-violations", contractId],
    queryFn: async () => {
      try {
        return await api.get<{ violations?: PolicyViolation[] }>(
          `/reviews/${contractId}/policy-violations`,
        );
      } catch {
        return { violations: [] };
      }
    },
    enabled: !!contractId,
    staleTime: 60_000,
  });
  const policyViolations = policyData?.violations ?? [];

  // ── Related reviews (best-effort fetch) ─────────────────────────
  const { data: relatedData } = useQuery<{ data?: RelatedReview[] }>({
    queryKey: ["contract-related-reviews-hub", contractId],
    queryFn: async () => {
      try {
        return await api.get<{ data?: RelatedReview[] }>(
          `/reviews/?contract_id=${contractId}&page_size=5`,
        );
      } catch {
        return { data: [] };
      }
    },
    enabled: !!contractId,
    staleTime: 30_000,
  });
  const relatedReviews = (relatedData?.data ?? []).filter(r => r.id !== contractId).slice(0, 3);

  // ── Open obligations count ──────────────────────────────────────
  const openObligations = obligations.filter(
    (o) => o.status === "pending" || o.status === "in_progress" || o.status === "pending_supplier" || o.status === "overdue",
  ).length;
  const overdueObligations = obligations.filter((o) => o.status === "overdue").length;

  // ── Risk-vs-count anti-coincidence check ────────────────────────
  // If the displayed risk_score (0–10) exactly equals the finding count
  // and the count is 1–9, the LLM is plausibly confusing the two. We
  // surface a small badge so the user can see at a glance that the
  // number is not just "1 point per finding".
  const coincidence = riskScore === findingCount && findingCount >= 1 && findingCount <= 9;

  return (
    <div
      data-testid="intelligence-hub"
      className="rounded-lg border border-gray-200 dark:border-navy-700 overflow-hidden"
    >
      <div className="px-4 py-2 border-b border-gray-100 dark:border-navy-700 bg-gradient-to-r from-navy-50 to-purple-50 dark:from-navy-850 dark:to-navy-800 flex items-center justify-between">
        <div className="flex items-center gap-1.5">
          <Sparkles className="w-3.5 h-3.5 text-purple-500" />
          <span className="text-[9px] font-semibold text-navy-700 dark:text-navy-200 uppercase tracking-wider">
            Contract Intelligence Hub
          </span>
        </div>
        {coincidence && (
          <span
            className="text-[8px] font-medium text-amber-700 bg-amber-50 dark:bg-amber-900/20 dark:text-amber-300 px-1.5 py-0.5 rounded"
            title="Risk score and finding count are numerically equal; verify these are independent values"
          >
            Risk ≈ findings (verify)
          </span>
        )}
      </div>

      <div className="grid grid-cols-2 gap-3 p-3">
        {/* ── Findings by severity ─────────────────────────────────── */}
        <div className="rounded-md border border-gray-100 dark:border-navy-700 p-2.5">
          <div className="flex items-center gap-1.5 mb-2">
            <AlertTriangle className="w-3 h-3 text-orange-500" />
            <span className="text-[9px] font-semibold text-gray-500 uppercase">Findings by Severity</span>
          </div>
          {findingCount === 0 ? (
            <p className="text-[10px] text-gray-400 italic">No findings yet</p>
          ) : (
            <div className="space-y-1">
              {(["critical", "high", "medium", "low", "info"] as const).map((sev) => {
                const n = breakdown[sev] ?? 0;
                const pct = findingCount > 0 ? (n / findingCount) * 100 : 0;
                const color =
                  sev === "critical" ? "bg-red-500"
                  : sev === "high" ? "bg-orange-500"
                  : sev === "medium" ? "bg-amber-500"
                  : sev === "low" ? "bg-green-500"
                  : "bg-blue-500";
                return (
                  <div key={sev} className="flex items-center gap-1.5">
                    <span className="text-[9px] capitalize text-gray-600 dark:text-gray-300 w-12">{sev}</span>
                    <div className="flex-1 h-1.5 bg-gray-100 dark:bg-navy-700 rounded-full overflow-hidden">
                      <div className={`h-full ${color}`} style={{ width: `${pct}%` }} />
                    </div>
                    <span className="text-[9px] font-medium tabular-nums w-6 text-right">{n}</span>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* ── Top clauses ──────────────────────────────────────────── */}
        <div className="rounded-md border border-gray-100 dark:border-navy-700 p-2.5">
          <div className="flex items-center gap-1.5 mb-2">
            <BookOpen className="w-3 h-3 text-navy-500" />
            <span className="text-[9px] font-semibold text-gray-500 uppercase">Top Clauses</span>
          </div>
          {topClauses.length === 0 ? (
            <p className="text-[10px] text-gray-400 italic">No clause analysis yet</p>
          ) : (
            <ul className="space-y-1">
              {topClauses.map((c) => (
                <li key={c.id} className="flex items-center gap-1.5 text-[10px]">
                  <span
                    className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${
                      c.severity === "critical" ? "bg-red-500"
                      : c.severity === "high" ? "bg-orange-500"
                      : c.severity === "medium" ? "bg-amber-500"
                      : "bg-green-500"
                    }`}
                  />
                  <span className="capitalize text-gray-700 dark:text-gray-200 truncate">
                    {(c.clause_type || "").replace(/_/g, " ")}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>

        {/* ── Policy violations ────────────────────────────────────── */}
        <div className="rounded-md border border-gray-100 dark:border-navy-700 p-2.5">
          <div className="flex items-center gap-1.5 mb-2">
            <Shield className="w-3 h-3 text-blue-500" />
            <span className="text-[9px] font-semibold text-gray-500 uppercase">Policy Violations</span>
          </div>
          {policyViolations.length === 0 ? (
            <p className="text-[10px] text-gray-400 italic">No policy violations</p>
          ) : (
            <ul className="space-y-1">
              {policyViolations.slice(0, 4).map((v) => (
                <li key={v.id} className="flex items-center gap-1.5 text-[10px]">
                  <XCircle className="w-3 h-3 text-red-500 flex-shrink-0" />
                  <span className="text-gray-700 dark:text-gray-200 truncate">{v.policy_rule_name || v.finding_title || v.policy_name}</span>
                  <span className={`ml-auto text-[8px] font-medium px-1 py-0.5 rounded-full ${
                    v.severity === "critical" ? "bg-red-100 text-red-700" :
                    v.severity === "high" ? "bg-orange-100 text-orange-700" : "bg-amber-100 text-amber-700"
                  }`}>{v.severity}</span>
                </li>
              ))}
            </ul>
          )}
        </div>

        {/* ── Related reviews ──────────────────────────────────────── */}
        <div className="rounded-md border border-gray-100 dark:border-navy-700 p-2.5">
          <div className="flex items-center gap-1.5 mb-2">
            <GitBranch className="w-3 h-3 text-purple-500" />
            <span className="text-[9px] font-semibold text-gray-500 uppercase">Related Reviews</span>
          </div>
          {relatedReviews.length === 0 ? (
            <p className="text-[10px] text-gray-400 italic">No related reviews</p>
          ) : (
            <ul className="space-y-1">
              {relatedReviews.map((r, idx) => (
                <li key={r?.id || `related-${idx}`} className="flex items-center gap-1.5 text-[10px]">
                  <FileText className="w-3 h-3 text-gray-400 flex-shrink-0" />
                  <span className="text-gray-700 dark:text-gray-200 truncate flex-1">
                    {r?.document_name || (r?.id ? r.id.slice(0, 8) + "…" : "Unknown")}
                  </span>
                  {r?.finding_count !== undefined && (
                    <span className="text-[8px] text-gray-400">{r.finding_count}f</span>
                  )}
                </li>
              ))}
            </ul>
          )}
        </div>

        {/* ── Obligations summary ──────────────────────────────────── */}
        <div className="rounded-md border border-gray-100 dark:border-navy-700 p-2.5 col-span-2">
          <div className="flex items-center gap-1.5 mb-2">
            <Clock className="w-3 h-3 text-amber-500" />
            <span className="text-[9px] font-semibold text-gray-500 uppercase">Obligations Summary</span>
          </div>
          {obligations.length === 0 ? (
            <p className="text-[10px] text-gray-400 italic">No obligations tracked yet</p>
          ) : (
            <div className="flex items-center gap-3 text-[10px]">
              <span className="text-gray-700 dark:text-gray-200">
                <strong>{obligations.length}</strong> total
              </span>
              <span className="text-blue-600">
                <strong>{obligations.filter(o => o.status === "in_progress").length}</strong> in progress
              </span>
              <span className="text-amber-600">
                <strong>{obligations.filter(o => o.status === "pending").length}</strong> pending
              </span>
              {overdueObligations > 0 && (
                <span className="text-red-600 font-medium">
                  <strong>{overdueObligations}</strong> overdue
                </span>
              )}
              <span className="text-green-600">
                <strong>{obligations.filter(o => o.status === "completed").length}</strong> completed
              </span>
            </div>
          )}
        </div>

        {/* ── How is the risk score calculated? ─────────────────────── */}
        {riskScore > 0 && (
          <div className="rounded-md border border-gray-100 dark:border-navy-700 p-2.5 col-span-2 bg-gradient-to-r from-blue-50/50 to-purple-50/50 dark:from-blue-900/10 dark:to-purple-900/10">
            <div className="flex items-center gap-1.5 mb-1.5">
              <TrendingUp className="w-3 h-3 text-navy-500" />
              <span className="text-[9px] font-semibold text-gray-500 uppercase">How is the risk score calculated?</span>
            </div>
            <p className="text-[10px] text-gray-600 dark:text-gray-300 leading-relaxed">
              The risk score is an AI-derived 0–1.0 score (displayed × 10) computed from the
              contract&apos;s clause content, weighted by clause type and severity. It is
              <strong> not</strong> equal to the finding count. The score is then mapped to a label
              (Minimal / Moderate / Elevated / High / Critical).
            </p>
            {topContributor && (
              <div className="mt-2 flex items-start gap-1.5 text-[10px]">
                <CheckCircle2 className="w-3 h-3 text-amber-500 flex-shrink-0 mt-0.5" />
                <span className="text-gray-700 dark:text-gray-200">
                  <strong>Top contributor:</strong> {topContributor.title}
                  {topContributor.clause_type && (
                    <span className="text-gray-400"> ({topContributor.clause_type.replace(/_/g, " ")})</span>
                  )}
                </span>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

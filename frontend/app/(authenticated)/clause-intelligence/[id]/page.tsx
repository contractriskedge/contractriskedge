/**
 * Clause Intelligence Center — detail page.
 *
 * Dedicated route for inspecting a single clause across all of its
 * facets (overview, benchmark, variants, negotiation, usage, related
 * playbooks, AI explanation). Reuses the existing ClauseDetailDrawer
 * tabs so the data layer stays consistent.
 *
 * URL: /clause-intelligence/[id]
 */

"use client";

import React, { useMemo } from "react";
import { useParams, useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, FileText, Star, AlertTriangle, Loader2, ExternalLink } from "lucide-react";
import { useClauses, useBenchmarks, useUpdateClause, useFallbackVariants } from "@/services/hooks/useClauseIntelligence";
import type { ClauseRecord, BenchmarkData, ClauseVariant } from "@/components/dashboard/clause-library/types";
import { RISK_BG, RISK_TEXT, RISK_BG_LIGHT } from "@/components/dashboard/clause-library/types";
import { useAuth } from "@/components/auth/AuthProvider";
import { useFavorites } from "@/hooks/useFavorites";
import { formatDate } from "@/lib/date-utils";

type TabId = "details" | "benchmark" | "comparison" | "risk" | "favorites";

const TABS: { id: TabId; label: string }[] = [
  { id: "details", label: "Details" },
  { id: "benchmark", label: "Benchmark" },
  { id: "comparison", label: "Comparison" },
  { id: "risk", label: "Risk" },
  { id: "favorites", label: "Favorites" },
];

function toClauseRecord(c: ReturnType<typeof useClauses>["data"] extends infer T ? T extends { data: Array<infer R> } ? R : never : never): ClauseRecord {
  return {
    id: c.id,
    name: c.name,
    category: c.category,
    text: c.text,
    riskScore: c.risk_score ?? 0,
    riskLevel: (c.risk_level as ClauseRecord["riskLevel"]) ?? "info",
    jurisdiction: c.jurisdiction ?? "",
    contractTypes: c.contract_types ?? [],
    benchmarkPercentile: c.benchmark_percentile ?? 0,
    usageFrequency: c.usage_frequency ?? 0,
    approvalStatus: (c.approval_status as ClauseRecord["approvalStatus"]) ?? "draft",
    lastUpdated: c.updated_at ?? c.created_at ?? "",
    owner: c.owner ?? "",
    aiConfidence: c.ai_confidence ?? 0,
    negotiationStrength: c.negotiation_strength ?? 0,
    fallbackVariants: [],
    versions: c.version ?? 1,
    isFavorite: c.is_favorite ?? false,
    tags: c.tags ?? [],
    aiExplanation: c.ai_explanation ?? "",
    negotiationGuidance: c.negotiation_guidance ?? "",
    governanceNotes: c.governance_notes ?? "",
  };
}

function BenchmarkTab({ clause, benchmarkData }: { clause: ClauseRecord; benchmarkData: BenchmarkData[] }) {
  const matches = benchmarkData.filter((b) => b.clauseType === clause.category);
  return (
    <div className="space-y-3">
      <div className="rounded-lg border border-gray-200 dark:border-navy-700 p-3">
        <p className="text-[10px] font-semibold text-gray-500 uppercase mb-2">Market Benchmark</p>
        <div className="grid grid-cols-3 gap-2 text-center">
          <div className="p-2 rounded bg-gray-50 dark:bg-navy-700">
            <p className="text-[9px] text-gray-500">P25</p>
            <p className="text-sm font-semibold text-navy-900 dark:text-white">
              {matches[0]?.marketP25?.toFixed(1) ?? "—"}
            </p>
          </div>
          <div className="p-2 rounded bg-navy-50 dark:bg-navy-700">
            <p className="text-[9px] text-gray-500">Median</p>
            <p className="text-sm font-semibold text-navy-900 dark:text-white">
              {matches[0]?.marketMedian?.toFixed(1) ?? "—"}
            </p>
          </div>
          <div className="p-2 rounded bg-gray-50 dark:bg-navy-700">
            <p className="text-[9px] text-gray-500">P75</p>
            <p className="text-sm font-semibold text-navy-900 dark:text-white">
              {matches[0]?.marketP75?.toFixed(1) ?? "—"}
            </p>
          </div>
        </div>
        <p className="text-[9px] text-gray-500 mt-2">
          Your clause: <span className="font-semibold">{clause.riskScore}/10</span> · Sample size: {matches[0]?.sampleSize ?? "—"}
        </p>
      </div>
    </div>
  );
}

function ComparisonTab({ clause }: { clause: ClauseRecord }) {
  return (
    <div className="space-y-3">
      <p className="text-[10px] font-semibold text-gray-500 uppercase">Compare to fallback variants</p>
      <div className="space-y-2">
        {clause.fallbackVariants.length === 0 ? (
          <p className="text-xs text-gray-500 italic">No fallback variants defined yet.</p>
        ) : (
          clause.fallbackVariants.map((v) => (
            <div key={v.id} className="rounded-lg border border-gray-200 dark:border-navy-700 p-3">
              <div className="flex items-center justify-between mb-1">
                <span className="text-[11px] font-medium text-navy-900 dark:text-white">{v.label}</span>
                {v.isPreferred && <span className="text-[9px] font-medium px-1.5 py-0.5 rounded-full bg-emerald-100 text-emerald-700">Preferred</span>}
              </div>
              <p className="text-[10px] text-gray-600 dark:text-gray-300 leading-relaxed mb-2">{v.text}</p>
              <div className="flex items-center gap-2 text-[9px] text-gray-500">
                <span>Risk: {v.riskScore}/10</span>
                <span>·</span>
                <span>Negotiation strength: {v.negotiationStrength}%</span>
                <span>·</span>
                <span>Usage: {v.usageRate.toFixed(0)}%</span>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

function RiskTab({ clause }: { clause: ClauseRecord }) {
  const level = clause.riskLevel;
  return (
    <div className="space-y-3">
      <div className={`rounded-lg border p-3 ${RISK_BG_LIGHT[level] ?? "bg-gray-50"}`}>
        <div className="flex items-center gap-2">
          <span className={`w-3 h-3 rounded-full ${RISK_BG[level] ?? "bg-gray-400"}`} />
          <p className={`text-xs font-semibold uppercase ${RISK_TEXT[level] ?? "text-gray-700"}`}>
            {level} risk
          </p>
        </div>
        <p className="text-2xl font-bold text-navy-900 dark:text-white mt-1">
          {clause.riskScore}<span className="text-sm text-gray-400">/10</span>
        </p>
        <p className="text-[9px] text-gray-500 mt-1">
          {clause.aiExplanation || "No AI explanation available."}
        </p>
      </div>
      {clause.governanceNotes && (
        <div className="rounded-lg border border-amber-200 dark:border-amber-800 bg-amber-50 dark:bg-amber-900/10 p-3">
          <p className="text-[10px] font-semibold text-amber-700 uppercase mb-1">Governance Notes</p>
          <p className="text-[10px] text-amber-800 dark:text-amber-200">{clause.governanceNotes}</p>
        </div>
      )}
    </div>
  );
}

function FavoritesTab() {
  const { user } = useAuth();
  const favorites = useFavorites(user?.tenant_id, user?.sub);
  return (
    <div className="space-y-3">
      <p className="text-[10px] font-semibold text-gray-500 uppercase">Your favorited clauses</p>
      {favorites.count === 0 ? (
        <div className="text-center py-6 text-xs text-gray-400">
          <Star className="w-6 h-6 mx-auto mb-2 text-gray-300" />
          You haven&apos;t favorited any clauses yet. Click the star on a clause row to add it here.
        </div>
      ) : (
        <ul className="space-y-1.5">
          {favorites.ids.map((id) => (
            <li key={id} className="text-[10px] text-gray-700 dark:text-gray-300 px-2 py-1 rounded bg-amber-50 dark:bg-amber-900/10">
              {id}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function DetailsTab({ clause }: { clause: ClauseRecord }) {
  return (
    <div className="space-y-3">
      <div>
        <p className="text-[10px] font-semibold text-gray-500 uppercase mb-1">Clause Text</p>
        <div className="rounded-lg border border-gray-200 dark:border-navy-700 p-3 bg-gray-50 dark:bg-navy-850">
          <p className="text-[11px] text-gray-700 dark:text-gray-300 leading-relaxed whitespace-pre-line">
            {clause.text || "No clause text on record."}
          </p>
        </div>
      </div>
      <div className="grid grid-cols-2 gap-2">
        <div className="rounded-lg border border-gray-200 dark:border-navy-700 p-2.5">
          <p className="text-[9px] text-gray-500">Category</p>
          <p className="text-[11px] font-medium text-navy-900 dark:text-white capitalize">{clause.category.replace(/_/g, " ")}</p>
        </div>
        <div className="rounded-lg border border-gray-200 dark:border-navy-700 p-2.5">
          <p className="text-[9px] text-gray-500">Jurisdiction</p>
          <p className="text-[11px] font-medium text-navy-900 dark:text-white">{clause.jurisdiction || "—"}</p>
        </div>
        <div className="rounded-lg border border-gray-200 dark:border-navy-700 p-2.5">
          <p className="text-[9px] text-gray-500">Status</p>
          <p className="text-[11px] font-medium text-navy-900 dark:text-white capitalize">{clause.approvalStatus.replace(/_/g, " ")}</p>
        </div>
        <div className="rounded-lg border border-gray-200 dark:border-navy-700 p-2.5">
          <p className="text-[9px] text-gray-500">Updated</p>
          <p className="text-[11px] font-medium text-navy-900 dark:text-white">{formatDate(clause.lastUpdated)}</p>
        </div>
      </div>
      {clause.tags.length > 0 && (
        <div>
          <p className="text-[10px] font-semibold text-gray-500 uppercase mb-1">Tags</p>
          <div className="flex flex-wrap gap-1">
            {clause.tags.map((t) => (
              <span key={t} className="text-[9px] px-1.5 py-0.5 rounded-full bg-navy-50 text-navy-700 dark:bg-navy-700 dark:text-navy-200">{t}</span>
            ))}
          </div>
        </div>
      )}
      {clause.negotiationGuidance && (
        <div>
          <p className="text-[10px] font-semibold text-gray-500 uppercase mb-1">Negotiation Guidance</p>
          <p className="text-[10px] text-gray-700 dark:text-gray-300 leading-relaxed">{clause.negotiationGuidance}</p>
        </div>
      )}
    </div>
  );
}

export default function ClauseIntelligenceDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const id = params?.id;
  const { user } = useAuth();
  const favorites = useFavorites(user?.tenant_id, user?.sub);
  const [tab, setTab] = React.useState<TabId>("details");

  const { data: clausesData, isLoading } = useClauses({});
  const { data: benchmarksData } = useBenchmarks();
  const { data: fallbacksData, isLoading: fallbacksLoading } = useFallbackVariants(id ?? "");

  const clause: ClauseRecord | null = useMemo(() => {
    if (!id || !clausesData) return null;
    const found = (clausesData.data ?? []).find((c) => c.id === id);
    if (!found) return null;
    const base = toClauseRecord(found);
    const rawVariants = Array.isArray(fallbacksData) ? fallbacksData : (fallbacksData as { data?: unknown[] } | undefined)?.data ?? [];
    const variants: ClauseVariant[] = (rawVariants as Array<Record<string, unknown>>).map((fb) => ({
      id: String(fb.id ?? ""),
      label: String(fb.label ?? ""),
      text: String(fb.text ?? ""),
      riskScore: Number(fb.risk_score ?? 0),
      negotiationStrength: Number(fb.negotiation_strength ?? 0),
      usageRate: Number(fb.usage_rate ?? 0) * 100,
      isPreferred: Boolean(fb.is_preferred ?? false),
    }));
    return { ...base, fallbackVariants: variants };
  }, [id, clausesData, fallbacksData]);

  const benchmarkData = useMemo<Array<BenchmarkData & { category: string }>>(
    () => (benchmarksData?.data ?? []).map((b) => ({
      clauseType: b.category,
      yourScore: b.avg_risk_score ?? 0,
      marketMedian: b.market_median,
      marketP25: b.market_p25 ?? 0,
      marketP75: b.market_p75 ?? 0,
      percentile: b.acceptance_rate ?? 0,
      sampleSize: b.sample_size,
    })),
    [benchmarksData],
  );

  const updateMutation = useUpdateClause(id);

  const handleToggleFavorite = () => {
    if (!clause) return;
    // Persist in both the global favorites store (localStorage, per user)
    // and the backend (server-side is_favorite) so it follows the user
    // across devices.
    favorites.toggle(clause.id);
    updateMutation.mutate({ id: clause.id, body: { is_favorite: !clause.isFavorite } });
  };

  if (isLoading || fallbacksLoading) {
    return (
      <div className="flex items-center justify-center h-full bg-gray-50 dark:bg-navy-900">
        <div className="text-center">
          <Loader2 className="w-8 h-8 text-blue-500 animate-spin mx-auto mb-3" />
          <p className="text-sm text-gray-500 dark:text-gray-400">Loading clause detail…</p>
        </div>
      </div>
    );
  }

  if (!clause) {
    return (
      <div className="flex items-center justify-center h-full bg-gray-50 dark:bg-navy-900">
        <div className="text-center max-w-md">
          <AlertTriangle className="w-10 h-10 text-red-400 mx-auto mb-3" />
          <p className="text-sm font-medium text-gray-900 dark:text-white mb-1">Clause not found</p>
          <p className="text-xs text-gray-500 dark:text-gray-400 mb-4">No clause with id {id} was found.</p>
          <button
            onClick={() => router.push("/clause-intelligence")}
            className="inline-flex items-center gap-1.5 text-xs font-medium text-blue-600 hover:text-blue-700 dark:text-blue-400"
          >
            <ArrowLeft className="w-3.5 h-3.5" /> Back to Clause Library
          </button>
        </div>
      </div>
    );
  }

  const isFav = favorites.isFavorite(clause.id) || clause.isFavorite;

  return (
    <div className="flex flex-col h-full bg-gray-50 dark:bg-navy-900">
      {/* Sticky action bar */}
      <div className="flex items-center justify-between px-4 py-2 bg-white dark:bg-navy-800 border-b border-gray-200 dark:border-navy-700 shadow-sm z-10">
        <div className="flex items-center gap-3 min-w-0">
          <button
            onClick={() => router.push("/clause-intelligence")}
            className="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-navy-700 text-gray-500 dark:text-gray-400 transition-colors"
            aria-label="Back"
          >
            <ArrowLeft className="w-4 h-4" />
          </button>
          <div className="flex items-center gap-2 min-w-0">
            <div className="w-8 h-8 rounded-lg bg-navy-700 flex items-center justify-center flex-shrink-0">
              <FileText className="w-4 h-4 text-white" />
            </div>
            <div className="min-w-0">
              <h1 className="text-sm font-semibold text-navy-900 dark:text-white truncate">{clause.name}</h1>
              <p className="text-[10px] text-gray-500 dark:text-gray-400 truncate">
                {clause.category.replace(/_/g, " ")} · {clause.jurisdiction || "—"} · v{clause.versions}
              </p>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-1.5">
          <button
            onClick={handleToggleFavorite}
            aria-label={isFav ? "Unfavorite clause" : "Favorite clause"}
            aria-pressed={isFav}
            className={`inline-flex items-center gap-1 px-2.5 py-1.5 text-[10px] font-medium rounded-md border transition-colors ${
              isFav
                ? "bg-amber-50 border-amber-200 text-amber-700 dark:bg-amber-900/20 dark:border-amber-800 dark:text-amber-300"
                : "bg-white dark:bg-navy-700 border-gray-200 dark:border-navy-600 text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-navy-600"
            }`}
          >
            <Star className={`w-3.5 h-3.5 ${isFav ? "fill-current" : ""}`} />
            {isFav ? "Favorited" : "Favorite"}
          </button>
          <a
            href={`/clause-library/${clause.id}`}
            className="inline-flex items-center gap-1 px-2.5 py-1.5 text-[10px] font-medium rounded-md border border-gray-200 dark:border-navy-600 text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-navy-700 transition-colors"
          >
            <ExternalLink className="w-3.5 h-3.5" /> Open in Library
          </a>
        </div>
      </div>

      {/* Tab strip */}
      <div className="flex items-center gap-1 px-4 py-2 bg-white dark:bg-navy-800 border-b border-gray-200 dark:border-navy-700 overflow-x-auto">
        {TABS.map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`px-3 py-1.5 text-[10px] font-medium rounded-md whitespace-nowrap transition-colors ${
              tab === t.id
                ? "bg-navy-700 text-white shadow-sm"
                : "text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-navy-700"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Body */}
      <div className="flex-1 overflow-y-auto p-4">
        {tab === "details" && <DetailsTab clause={clause} />}
        {tab === "benchmark" && <BenchmarkTab clause={clause} benchmarkData={benchmarkData} />}
        {tab === "comparison" && <ComparisonTab clause={clause} />}
        {tab === "risk" && <RiskTab clause={clause} />}
        {tab === "favorites" && <FavoritesTab />}
      </div>
    </div>
  );
}

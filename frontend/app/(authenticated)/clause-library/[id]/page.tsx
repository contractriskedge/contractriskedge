/**
 * Clause detail page — full-screen deep-dive for a single clause.
 *
 * Provides the same information as the side drawer (overview, benchmark,
 * variants, negotiation, usage, related, playbooks, AI) but with a wider
 * canvas and persistent URL for sharing.
 *
 * Linked from the Clause Library's ClauseTable row click.
 */

"use client";

import React, { useMemo } from "react";
import { useRouter, useParams } from "next/navigation";
import { ArrowLeft, FileText, Loader2, Star, AlertCircle } from "lucide-react";
import { useClauses, useUpdateClause, useBenchmarks } from "@/services/hooks/useClauseIntelligence";
import { ClauseDetailDrawer } from "@/components/dashboard/clause-library/ClauseDetailDrawer";
import { useAuth } from "@/components/auth/AuthProvider";
import { useFavorites } from "@/hooks/useFavorites";
import type { ClauseRecord } from "@/components/dashboard/clause-library/types";
import type { BenchmarkData } from "@/components/dashboard/clause-library/types";

/** Map backend snake_case → frontend camelCase ClauseRecord (mirrors the
 *  mapping in ClauseLibrary so the detail page can render the same data
 *  shape the drawer expects). */
function toClauseRecord(c: any): ClauseRecord {
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

export default function ClauseDetailPage() {
  const router = useRouter();
  const params = useParams<{ id: string }>();
  const clauseId = params?.id as string;
  const { user } = useAuth();
  const favorites = useFavorites(user?.tenant_id, user?.sub);
  const updateMutation = useUpdateClause(clauseId);

  // Pull all clauses (small library) so we can show the matching record.
  const { data: clausesData, isLoading } = useClauses({ page_size: 200 });
  const { data: benchmarksData } = useBenchmarks();

  const clause: ClauseRecord | undefined = useMemo(() => {
    const found = (clausesData?.data ?? []).find((c) => c.id === clauseId);
    return found ? toClauseRecord(found) : undefined;
  }, [clausesData, clauseId]);

  const benchmarks: BenchmarkData[] = useMemo(
    () =>
      (benchmarksData?.data ?? []).map((b) => ({
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

  const toggleFavorite = (id: string) => {
    const c = (clausesData?.data ?? []).find((x) => x.id === id);
    if (c) updateMutation.mutate({ id, body: { is_favorite: !c.is_favorite } });
    favorites.toggle(id);
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 className="w-6 h-6 animate-spin text-navy-500" />
      </div>
    );
  }

  if (!clause) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-center max-w-md mx-auto p-8">
        <AlertCircle className="w-10 h-10 text-red-400 mb-3" />
        <p className="text-sm font-medium text-gray-900 dark:text-white">Clause not found</p>
        <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
          The clause <code className="font-mono text-[10px] bg-gray-100 dark:bg-navy-700 px-1 py-0.5 rounded">{clauseId}</code> does not exist or has been removed.
        </p>
        <button
          onClick={() => router.push("/clause-library")}
          className="mt-4 inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg bg-navy-700 text-white hover:bg-navy-800 transition-colors"
        >
          <ArrowLeft className="w-3.5 h-3.5" /> Back to Clause Library
        </button>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      {/* ── Sticky header ── */}
      <div className="flex items-center justify-between px-4 py-2 bg-white dark:bg-navy-800 border-b border-gray-200 dark:border-navy-700">
        <div className="flex items-center gap-2">
          <button
            onClick={() => router.push("/clause-library")}
            className="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-navy-700 text-gray-500 transition-colors"
            aria-label="Back to library"
          >
            <ArrowLeft className="w-4 h-4" />
          </button>
          <FileText className="w-4 h-4 text-navy-600 dark:text-navy-300" />
          <div>
            <h1 className="text-sm font-semibold text-navy-900 dark:text-white leading-tight">
              {clause.name}
            </h1>
            <p className="text-[10px] text-gray-500 dark:text-gray-400">
              {clause.id} · {clause.category.replace(/_/g, " ")}
            </p>
          </div>
        </div>
        <button
          onClick={() => toggleFavorite(clause.id)}
          className={`inline-flex items-center gap-1 px-2.5 py-1.5 text-[10px] font-medium rounded-md transition-colors ${
            (favorites.isFavorite(clause.id) || clause.isFavorite)
              ? "bg-amber-50 text-amber-700 dark:bg-amber-900/20 dark:text-amber-300"
              : "bg-gray-50 dark:bg-navy-700 text-gray-600 dark:text-gray-300 hover:bg-amber-50 hover:text-amber-700"
          }`}
          aria-pressed={favorites.isFavorite(clause.id) || clause.isFavorite}
        >
          <Star className={`w-3.5 h-3.5 ${(favorites.isFavorite(clause.id) || clause.isFavorite) ? "fill-current" : ""}`} />
          {favorites.isFavorite(clause.id) || clause.isFavorite ? "Favorited" : "Favorite"}
        </button>
      </div>

      {/* Reuse the detail drawer for the same content but a deeper canvas. */}
      <div className="flex-1 min-h-0 relative">
        <ClauseDetailDrawer
          clause={clause}
          benchmarks={benchmarks}
          onClose={() => router.push("/clause-library")}
          onToggleFavorite={toggleFavorite}
        />
      </div>
    </div>
  );
}

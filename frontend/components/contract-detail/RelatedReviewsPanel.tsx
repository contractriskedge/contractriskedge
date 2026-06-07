/**
 * RelatedReviewsPanel — show all reviews for a given contract.
 *
 * Pulls the review list and filters by the current contract id
 * (review_id == contract_id in this app — they're 1:1, but the
 * query also surfaces any historic / superseded reviews of the same
 * document via previous_review_id).
 */

"use client";

import React from "react";
import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { reviewService } from "@/services/api/reviews";
import { FileText, ArrowRight, Loader2, History } from "lucide-react";
import { formatDate } from "@/lib/date-utils";

interface RelatedReviewsPanelProps {
  contractId: string;
}

export function RelatedReviewsPanel({ contractId }: RelatedReviewsPanelProps) {
  const router = useRouter();
  const { data, isLoading } = useQuery({
    queryKey: ["contract-related-reviews", contractId],
    queryFn: () => reviewService.list({ page_size: 50 }),
    enabled: !!contractId,
    staleTime: 30_000,
  });

  // Filter to reviews that match this contract id (review_id == contract_id)
  const reviews = (data?.data ?? []).filter(
    (r) => r.review_id === contractId || r.upload_id === contractId,
  );

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-6 text-gray-400 text-xs gap-2">
        <Loader2 className="w-3.5 h-3.5 animate-spin" /> Loading related reviews…
      </div>
    );
  }

  if (reviews.length === 0) {
    return (
      <div className="text-center py-6 text-gray-400 text-xs">
        <History className="w-6 h-6 mx-auto mb-2 text-gray-300" />
        No prior review activity recorded for this contract.
      </div>
    );
  }

  return (
    <div className="space-y-1.5">
      {reviews.map((r) => {
        const sla = r.sla_status || "on_track";
        const isOverdue = sla === "overdue" || sla === "critical_overdue";
        return (
          <button
            key={r.review_id}
            type="button"
            onClick={() => router.push(`/reviews/ai-workspace?reviewId=${r.review_id}`)}
            className="w-full flex items-start gap-2.5 p-2.5 rounded-lg border border-gray-200 dark:border-navy-700 hover:bg-gray-50 dark:hover:bg-navy-750 transition-colors text-left"
          >
            <div className={`w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0 ${
              isOverdue ? "bg-red-100 dark:bg-red-900/20" : "bg-navy-100 dark:bg-navy-700"
            }`}>
              <FileText className={`w-3.5 h-3.5 ${isOverdue ? "text-red-600" : "text-navy-600"}`} />
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-1.5">
                <p className="text-[11px] font-medium text-navy-900 dark:text-white truncate">
                  {r.document_name || r.original_filename || r.review_id}
                </p>
                <span className={`text-[8px] font-semibold px-1.5 py-0.5 rounded-full ${
                  r.priority === "critical" ? "bg-red-100 text-red-700" :
                  r.priority === "high" ? "bg-orange-100 text-orange-700" :
                  r.priority === "medium" ? "bg-amber-100 text-amber-700" :
                  "bg-green-100 text-green-700"
                }`}>{r.priority}</span>
              </div>
              <div className="flex items-center gap-2 mt-0.5 text-[9px] text-gray-500">
                <span className="capitalize">{(r.status || "").replace(/_/g, " ")}</span>
                <span>·</span>
                <span>{formatDate(r.created_at)}</span>
                <span>·</span>
                <span>{r.finding_count} findings</span>
                {r.assigned_to && (
                  <>
                    <span>·</span>
                    <span>{r.assigned_to}</span>
                  </>
                )}
              </div>
            </div>
            <ArrowRight className="w-3.5 h-3.5 text-gray-300 flex-shrink-0" />
          </button>
        );
      })}
    </div>
  );
}

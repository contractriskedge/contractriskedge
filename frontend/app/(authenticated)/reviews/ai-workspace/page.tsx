/**
 * Enterprise AI Review Platform route — premium AI contract review workspace.
 *
 * Accepts query parameters:
 *   ?reviewId={id}    — auto-select a specific review
 *   ?contractId={id}  — auto-select review for a specific contract
 *
 * Document-centric 3-panel layout with:
 * - Review Summary, Findings (inline explainability), Policy, Recommendations, Workflow, Audit
 * - Reviewer productivity: hotkeys, quick actions, assign next, approve/reject shortcuts
 * - AI feedback loop: mark correct/incorrect, retraining feedback
 * - Queue aging, SLA prioritization, workload balancing
 * - Collaboration with threaded comments
 * - Seeded enterprise data for zero empty states
 */

"use client";

import React, { Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { Loader2 } from "lucide-react";
import { EnterpriseReviewPlatform } from "@/components/ai-review/EnterpriseReviewPlatform";
import type { ReviewSection } from "@/components/ai-review/types";

function AiReviewWorkspaceContent() {
  const searchParams = useSearchParams();
  const reviewId = searchParams.get("reviewId");
  const contractId = searchParams.get("contractId");
  const tab = searchParams.get("tab");
  // The `tab` query param is a hint for which section to land on. We
  // accept any of the well-known ReviewSection ids and fall back to
  // undefined (which the platform treats as "summary") for unknown
  // values so a typo doesn't break the page.
  const VALID_SECTIONS = new Set<ReviewSection>([
    "summary", "overview", "findings", "redline", "versions", "policy",
    "recommendations", "risk_reduction", "workflow", "explainability",
    "audit", "governance", "history",
  ]);
  const initialSection = (tab && VALID_SECTIONS.has(tab as ReviewSection))
    ? (tab as ReviewSection)
    : undefined;

  return (
    <EnterpriseReviewPlatform
      preselectedReviewId={reviewId || undefined}
      preselectedContractId={contractId || undefined}
      initialSection={initialSection}
    />
  );
}

export default function AiReviewWorkspacePage() {
  return (
    <Suspense
      fallback={
        <div className="flex h-full items-center justify-center">
          <Loader2 className="w-8 h-8 animate-spin text-navy-500" />
        </div>
      }
    >
      <AiReviewWorkspaceContent />
    </Suspense>
  );
}

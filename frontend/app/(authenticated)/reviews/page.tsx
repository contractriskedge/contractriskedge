/**
 * Reviews route — enterprise review queue.
 * Opens reviews in the dedicated AI Review Workspace.
 */

"use client";

import React from "react";
import { useRouter } from "next/navigation";
import { ReviewQueue } from "@/components/review/ReviewQueue";

export default function ReviewsPage() {
  const router = useRouter();

  return (
    <div className="flex flex-col h-full bg-gray-50 dark:bg-navy-900">
      <ReviewQueue onReviewSelect={(reviewId) => router.push(`/reviews/ai-workspace?reviewId=${reviewId}`)} />
    </div>
  );
}

/**
 * Analytics route — system analytics, errors, stuck workflows, health.
 */

"use client";

import React from "react";
import { AnalyticsCenter } from "@/components/dashboard/analytics/AnalyticsCenter";

export default function AnalyticsRoute() {
  return (
    <AnalyticsCenter
      onNavigate={(view, params) => {
        if (view === "review" && params?.reviewId) {
          window.location.href = `/reviews?reviewId=${params.reviewId}`;
        } else if (view === "search" && params?.query) {
          window.location.href = `/search?q=${encodeURIComponent(params.query)}`;
        }
      }}
    />
  );
}

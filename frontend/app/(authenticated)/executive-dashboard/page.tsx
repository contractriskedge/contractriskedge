/**
 * Executive Dashboard route — Sprint 31.1 leadership pane.
 * Shows aggregate KPIs across the full contract lifecycle.
 */

"use client";

import React, { Suspense } from "react";
import dynamic from "next/dynamic";

const ExecutiveDashboardV2 = dynamic(
  () => import("@/components/dashboard/ExecutiveDashboardV2").then((m) => ({ default: m.ExecutiveDashboard })),
  {
    loading: () => (
      <div className="p-6 space-y-4 animate-pulse">
        <div className="h-8 bg-gray-200 dark:bg-navy-700 rounded w-64" />
        <div className="h-4 bg-gray-200 dark:bg-navy-700 rounded w-96" />
        <div className="grid grid-cols-4 gap-4 mt-6">
          <div className="h-24 bg-gray-200 dark:bg-navy-700 rounded-xl" />
          <div className="h-24 bg-gray-200 dark:bg-navy-700 rounded-xl" />
          <div className="h-24 bg-gray-200 dark:bg-navy-700 rounded-xl" />
          <div className="h-24 bg-gray-200 dark:bg-navy-700 rounded-xl" />
        </div>
        <div className="grid grid-cols-3 gap-4 mt-4">
          <div className="h-64 bg-gray-200 dark:bg-navy-700 rounded-xl" />
          <div className="h-64 bg-gray-200 dark:bg-navy-700 rounded-xl" />
          <div className="h-64 bg-gray-200 dark:bg-navy-700 rounded-xl" />
        </div>
      </div>
    ),
  }
);

export default function ExecutiveDashboardRoute() {
  return (
    <Suspense fallback={null}>
      <ExecutiveDashboardV2 />
    </Suspense>
  );
}

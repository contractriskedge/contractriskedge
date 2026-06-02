/**
 * Executive route — Executive Command Center.
 */

"use client";

import React, { Suspense } from "react";
import dynamic from "next/dynamic";

const ExecutiveCommandCenter = dynamic(
  () => import("@/components/dashboard/command-center/ExecutiveCommandCenter").then((m) => ({ default: m.ExecutiveCommandCenter })),
  {
    loading: () => (
      <div className="p-6 space-y-4 animate-pulse">
        <div className="h-8 bg-gray-200 dark:bg-navy-700 rounded w-64" />
        <div className="h-4 bg-gray-200 dark:bg-navy-700 rounded w-96" />
        <div className="grid grid-cols-2 gap-4 mt-6">
          <div className="h-48 bg-gray-200 dark:bg-navy-700 rounded-xl" />
          <div className="h-48 bg-gray-200 dark:bg-navy-700 rounded-xl" />
          <div className="h-48 bg-gray-200 dark:bg-navy-700 rounded-xl" />
          <div className="h-48 bg-gray-200 dark:bg-navy-700 rounded-xl" />
        </div>
      </div>
    ),
  }
);

export default function ExecutiveRoute() {
  return (
    <Suspense fallback={null}>
      <ExecutiveCommandCenter />
    </Suspense>
  );
}

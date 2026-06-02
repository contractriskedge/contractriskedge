/**
 * Command Center route — Real-time operational cockpit.
 */

"use client";

import React, { Suspense } from "react";
import dynamic from "next/dynamic";

const OperationalCommandCenter = dynamic(
  () =>
    import("@/components/dashboard/operations/OperationalCommandCenter").then(
      (m) => ({ default: m.OperationalCommandCenter })
    ),
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
        <div className="grid grid-cols-4 gap-4">
          <div className="h-24 bg-gray-200 dark:bg-navy-700 rounded-xl" />
          <div className="h-24 bg-gray-200 dark:bg-navy-700 rounded-xl" />
          <div className="h-24 bg-gray-200 dark:bg-navy-700 rounded-xl" />
          <div className="h-24 bg-gray-200 dark:bg-navy-700 rounded-xl" />
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div className="h-48 bg-gray-200 dark:bg-navy-700 rounded-xl" />
          <div className="h-48 bg-gray-200 dark:bg-navy-700 rounded-xl" />
        </div>
      </div>
    ),
  }
);

export default function CommandCenterRoute() {
  return (
    <Suspense fallback={null}>
      <OperationalCommandCenter />
    </Suspense>
  );
}

/**
 * Route error boundary — catches rendering errors with retry.
 */

"use client";

import React from "react";
import { AlertCircle, RefreshCw } from "lucide-react";

export default function RouteError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  React.useEffect(() => {
    console.error("Route error:", error);
  }, [error]);

  return (
    <div className="flex items-center justify-center h-64">
      <div className="text-center max-w-md">
        <AlertCircle className="w-10 h-10 text-red-400 mx-auto mb-3" />
        <p className="text-sm font-medium text-gray-900 mb-1">Something went wrong</p>
        <p className="text-xs text-gray-500 mb-4">
          {error.message || "An unexpected error occurred while rendering this page."}
          {error.digest && <span className="block mt-1 font-mono text-[10px] text-gray-400">Error ID: {error.digest}</span>}
        </p>
        <button
          onClick={reset}
          className="inline-flex items-center gap-1.5 text-xs font-medium text-gold-600 hover:text-gold-700"
        >
          <RefreshCw className="w-3.5 h-3.5" /> Try again
        </button>
      </div>
    </div>
  );
}

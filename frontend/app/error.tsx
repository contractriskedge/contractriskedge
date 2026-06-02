/**
 * Root error boundary — catches unhandled rendering errors.
 */

"use client";

import React from "react";
import { AlertCircle, RefreshCw } from "lucide-react";

export default function RootError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  React.useEffect(() => {
    console.error("Root error:", error);
  }, [error]);

  return (
    <div className="min-h-screen bg-navy-900 flex items-center justify-center">
      <div className="text-center max-w-md">
        <AlertCircle className="w-12 h-12 text-red-400 mx-auto mb-4" />
        <p className="text-base font-semibold text-white mb-2">Application Error</p>
        <p className="text-sm text-gray-400 mb-6">
          {error.message || "An unexpected error occurred. Please try again."}
        </p>
        <button
          onClick={reset}
          className="inline-flex items-center gap-2 px-4 py-2 bg-gold-500 text-navy-900 rounded-lg text-sm font-semibold hover:bg-gold-400 transition"
        >
          <RefreshCw className="w-4 h-4" /> Reload Application
        </button>
      </div>
    </div>
  );
}

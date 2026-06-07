/**
 * Contract not found — route-level not-found for /contracts/[contractId].
 *
 * Triggered by the route segment throwing `notFound()` when the contractId
 * in the URL is invalid. Provides a clear "go back" recovery path.
 */

"use client";

import Link from "next/link";
import { ArrowLeft, FileX } from "lucide-react";

export default function ContractNotFound() {
  return (
    <div className="flex items-center justify-center h-full bg-gray-50 dark:bg-navy-900">
      <div className="text-center max-w-md p-8">
        <div className="w-16 h-16 mx-auto mb-4 rounded-2xl bg-red-50 dark:bg-red-900/20 flex items-center justify-center">
          <FileX className="w-8 h-8 text-red-400" />
        </div>
        <p className="text-5xl font-bold text-gray-300 dark:text-navy-600 mb-2">404</p>
        <p className="text-sm font-semibold text-gray-900 dark:text-white mb-1">
          Contract not found
        </p>
        <p className="text-xs text-gray-500 dark:text-gray-400 mb-6">
          The contract you&apos;re looking for may have been archived, deleted,
          or the link is stale. Try going back to the contracts list.
        </p>
        <Link
          href="/contracts"
          className="inline-flex items-center gap-1.5 px-3 py-2 text-xs font-medium rounded-lg bg-navy-700 text-white hover:bg-navy-800 transition-colors shadow-sm"
        >
          <ArrowLeft className="w-3.5 h-3.5" /> Back to Contracts
        </Link>
      </div>
    </div>
  );
}

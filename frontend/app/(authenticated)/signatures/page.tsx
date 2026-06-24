/**
 * Signatures route — placeholder for signature management.
 * Full implementation planned after Sprint 31.2 Global Search.
 */

"use client";

import React from "react";
import { FileSignature } from "lucide-react";

export default function SignaturesPage() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">Signature Requests</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            Manage electronic signature requests across all contracts
          </p>
        </div>
      </div>

      <div className="flex flex-col items-center justify-center py-20 text-center">
        <FileSignature className="h-16 w-16 text-gray-300 dark:text-gray-600 mb-4" />
        <h2 className="text-xl font-semibold text-gray-700 dark:text-gray-300 mb-2">Signature Management</h2>
        <p className="text-gray-500 dark:text-gray-400 max-w-md">
          The signature management interface is coming soon. 
          Use the contract detail view to send documents for signature via DocuSign.
        </p>
      </div>
    </div>
  );
}

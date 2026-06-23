"use client";

import React from "react";
import { FileSignature, Plus } from "lucide-react";
import type { SignatureRequest, SignatureStatus } from "./types";
import { SignatureRequestCard } from "./SignatureRequestCard";

interface SignatureRequestListProps {
  requests: SignatureRequest[];
  onCreateClick?: () => void;
  onRequestClick?: (id: string) => void;
  loading?: boolean;
}

export function SignatureRequestList({
  requests, onCreateClick, onRequestClick, loading,
}: SignatureRequestListProps) {
  if (loading) {
    return (
      <div className="space-y-2">
        {[1, 2, 3].map((i) => (
          <div key={i} className="p-3 bg-white border border-gray-200 rounded-lg animate-pulse">
            <div className="h-4 bg-gray-200 rounded w-3/4 mb-2" />
            <div className="h-3 bg-gray-200 rounded w-1/2" />
          </div>
        ))}
      </div>
    );
  }

  if (requests.length === 0) {
    return (
      <div className="text-center py-12">
        <FileSignature className="w-12 h-12 text-gray-300 mx-auto mb-3" />
        <h3 className="text-sm font-semibold text-navy-800 mb-1">No Signature Requests</h3>
        <p className="text-xs text-gray-500 mb-4">
          Send a contract for signature to start the execution process.
        </p>
        {onCreateClick && (
          <button
            onClick={onCreateClick}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg bg-gold-500 text-white hover:bg-gold-600 transition-colors"
          >
            <Plus className="w-3.5 h-3.5" />
            New Signature Request
          </button>
        )}
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {requests.map((request) => (
        <SignatureRequestCard
          key={request.id}
          request={request}
          onClick={onRequestClick}
        />
      ))}
    </div>
  );
}

"use client";

import React from "react";
import { Award, Download, Loader2 } from "lucide-react";

interface SignatureCertificateProps {
  requestId: string;
  onDownload?: (requestId: string) => Promise<void>;
  loading?: boolean;
  available?: boolean;
}

export function SignatureCertificate({ requestId, onDownload, loading, available }: SignatureCertificateProps) {
  if (!available) {
    return (
      <div className="text-center py-6">
        <Award className="w-8 h-8 text-gray-300 mx-auto mb-2" />
        <p className="text-[10px] text-gray-500">Certificate available after signing is complete</p>
      </div>
    );
  }

  return (
    <div className="p-4 bg-green-50 border border-green-200 rounded-lg text-center">
      <Award className="w-8 h-8 text-green-500 mx-auto mb-2" />
      <h4 className="text-xs font-semibold text-green-800 mb-1">Completion Certificate</h4>
      <p className="text-[10px] text-green-600 mb-3">
        This document has been fully executed. Download the certificate of completion.
      </p>
      <button
        onClick={() => onDownload?.(requestId)}
        disabled={loading}
        className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:bg-green-300 transition-colors"
      >
        {loading ? (
          <Loader2 className="w-3.5 h-3.5 animate-spin" />
        ) : (
          <Download className="w-3.5 h-3.5" />
        )}
        {loading ? "Downloading..." : "Download Certificate"}
      </button>
    </div>
  );
}

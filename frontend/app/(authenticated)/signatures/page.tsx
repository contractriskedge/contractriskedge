/**
 * Signatures route — lists all signature requests with their DocuSign status.
 */

"use client";

import React, { useMemo } from "react";
import { useRouter } from "next/navigation";
import { FileSignature, RefreshCw, ExternalLink, Clock, CheckCircle2, XCircle, AlertTriangle, Send, Eye } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/services";
import { AsyncBoundary } from "@/components/shared/AsyncBoundary";
import { CardSkeleton } from "@/components/shared/LoadingSkeleton";

interface SignatureRequest {
  id: string;
  title: string;
  status: string;
  provider: string;
  provider_reference: string | null;
  contract_id: string | null;
  email_subject: string | null;
  created_by: string;
  created_at: string;
  signers: Array<{
    id: string;
    email: string;
    name: string;
    status: string;
    signed_at: string | null;
  }>;
}

const STATUS_COLORS: Record<string, string> = {
  draft: "bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400",
  preparing: "bg-blue-100 text-blue-600 dark:bg-blue-900/20 dark:text-blue-400",
  sent: "bg-purple-100 text-purple-600 dark:bg-purple-900/20 dark:text-purple-400",
  viewed: "bg-amber-100 text-amber-600 dark:bg-amber-900/20 dark:text-amber-400",
  partially_signed: "bg-yellow-100 text-yellow-600 dark:bg-yellow-900/20 dark:text-yellow-400",
  completed: "bg-green-100 text-green-600 dark:bg-green-900/20 dark:text-green-400",
  declined: "bg-red-100 text-red-600 dark:bg-red-900/20 dark:text-red-400",
  expired: "bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400",
  voided: "bg-red-100 text-red-600 dark:bg-red-900/20 dark:text-red-400",
};

const STATUS_ICONS: Record<string, React.ElementType> = {
  draft: FileSignature,
  preparing: Clock,
  sent: Send,
  viewed: Eye,
  partially_signed: Clock,
  completed: CheckCircle2,
  declined: XCircle,
  expired: AlertTriangle,
  voided: XCircle,
};

function useSignatures() {
  return useQuery<{ data: SignatureRequest[]; total: number }>({
    queryKey: ["signatures"],
    queryFn: () => api.get("/signatures?page_size=50"),
    staleTime: 30_000,
  });
}

export default function SignaturesPage() {
  const router = useRouter();
  const { data, isLoading, error, refetch } = useSignatures();

  const signatures = data?.data ?? [];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">Signature Requests</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            {data?.total ?? 0} total · Manage electronic signatures via DocuSign
          </p>
        </div>
        <button
          onClick={() => refetch()}
          className="inline-flex items-center gap-1.5 rounded-lg border border-gray-300 px-3 py-2 text-sm font-medium text-gray-600 hover:bg-gray-50 dark:border-gray-600 dark:text-gray-400 dark:hover:bg-gray-700"
        >
          <RefreshCw className="h-4 w-4" />
          Refresh
        </button>
      </div>

      <AsyncBoundary
        isLoading={isLoading}
        error={error}
        isEmpty={signatures.length === 0}
        emptyMessage="No signature requests yet"
        emptyDescription="Go to a contract detail page and click 'Send for Signature' to create one."
        emptyIcon={<FileSignature className="h-12 w-12 text-gray-300" />}
        loadingSkeleton={<CardSkeleton count={3} columns={1} />}
        onRetry={() => refetch()}
      >
        <div className="space-y-3">
          {signatures.map((sig) => {
            const StatusIcon = STATUS_ICONS[sig.status] || FileSignature;
            const statusColor = STATUS_COLORS[sig.status] || "bg-gray-100 text-gray-600";
            const signedCount = sig.signers.filter(s => s.status === "signed").length;
            const totalCount = sig.signers.length;

            return (
              <div
                key={sig.id}
                className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm hover:shadow-md transition-shadow dark:border-gray-700 dark:bg-gray-800"
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100">
                        {sig.title}
                      </h3>
                      <span className={`inline-flex items-center gap-1 px-2 py-0.5 text-[10px] font-medium rounded-full ${statusColor}`}>
                        <StatusIcon className="w-3 h-3" />
                        {sig.status.replace(/_/g, " ")}
                      </span>
                    </div>
                    <p className="text-xs text-gray-500 dark:text-gray-400">
                      Provider: {sig.provider} · Created: {new Date(sig.created_at).toLocaleDateString()}
                      {sig.provider_reference && ` · Envelope: ${sig.provider_reference.slice(0, 20)}...`}
                    </p>
                  </div>
                  <div className="flex items-center gap-2 ml-4">
                    {sig.contract_id && (
                      <button
                        onClick={() => router.push(`/contracts/${sig.contract_id}`)}
                        className="inline-flex items-center gap-1 px-2.5 py-1.5 text-[10px] font-medium rounded-md bg-gray-100 text-gray-700 hover:bg-gray-200 dark:bg-navy-700 dark:text-gray-300 dark:hover:bg-navy-600"
                      >
                        <ExternalLink className="w-3 h-3" />
                        Contract
                      </button>
                    )}
                  </div>
                </div>

                {/* Signers */}
                {sig.signers.length > 0 && (
                  <div className="mt-3 flex flex-wrap gap-2">
                    {sig.signers.map((signer) => (
                      <div
                        key={signer.id}
                        className={`inline-flex items-center gap-1.5 px-2 py-1 rounded-md text-[10px] ${
                          signer.status === "signed"
                            ? "bg-green-50 text-green-700 dark:bg-green-900/20 dark:text-green-400"
                            : signer.status === "declined"
                            ? "bg-red-50 text-red-700 dark:bg-red-900/20 dark:text-red-400"
                            : "bg-gray-50 text-gray-500 dark:bg-navy-700 dark:text-gray-400"
                        }`}
                      >
                        {signer.status === "signed" ? <CheckCircle2 className="w-3 h-3" /> :
                         signer.status === "declined" ? <XCircle className="w-3 h-3" /> :
                         <Clock className="w-3 h-3" />}
                        {signer.name} &lt;{signer.email}&gt;
                        {signer.signed_at && ` · ${new Date(signer.signed_at).toLocaleDateString()}`}
                      </div>
                    ))}
                    <span className="text-[10px] text-gray-400 self-center">
                      {signedCount}/{totalCount} signed
                    </span>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </AsyncBoundary>
    </div>
  );
}

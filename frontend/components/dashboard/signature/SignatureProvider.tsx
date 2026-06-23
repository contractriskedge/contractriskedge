"use client";

import React, { useState } from "react";
import { FileSignature, Plus } from "lucide-react";
import type { SignatureRequest } from "./types";
import { SignatureRequestList } from "./SignatureRequestList";
import { SignatureCreateWizard } from "./SignatureCreateWizard";

interface SignatureProviderProps {
  contractId?: string;
  sessionId?: string;
  contractTitle?: string;
}

// Demo data — will be replaced with real API calls
const DEMO_REQUESTS: SignatureRequest[] = [];

export function SignatureProvider({ contractId, sessionId, contractTitle }: SignatureProviderProps) {
  const [requests, setRequests] = useState<SignatureRequest[]>(DEMO_REQUESTS);
  const [showWizard, setShowWizard] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleCreate = async (data: {
    title: string;
    provider: "docusign" | "adobe_sign" | "dropbox_sign";
    signers: { email: string; name: string; role: "signer" | "approver" | "cc"; signingOrder: number }[];
    expiresInDays: number;
    emailSubject?: string;
  }) => {
    // TODO: Call POST /api/v1/signatures
    const newRequest: SignatureRequest = {
      id: `demo-${Date.now()}`,
      contractId,
      sessionId,
      title: data.title,
      status: "draft",
      provider: data.provider,
      expiresAt: new Date(Date.now() + data.expiresInDays * 86400000).toISOString(),
      createdBy: "current-user",
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      signers: data.signers.map((s, i) => ({
        id: `signer-${i}`,
        email: s.email,
        name: s.name,
        role: s.role,
        signingOrder: s.signingOrder,
        status: "awaiting" as const,
        createdAt: new Date().toISOString(),
      })),
    };
    setRequests(prev => [newRequest, ...prev]);
  };

  const handleRequestClick = (id: string) => {
    // TODO: Navigate to signature request detail
    console.log("Signature request clicked:", id);
  };

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <FileSignature className="w-4 h-4 text-gold-500" />
          <h3 className="text-xs font-semibold text-navy-900">E-Signature</h3>
        </div>
        <button
          onClick={() => setShowWizard(true)}
          className="inline-flex items-center gap-1 px-2 py-1 text-[10px] font-medium bg-gold-500 text-white rounded-md hover:bg-gold-600 transition-colors"
        >
          <Plus className="w-3 h-3" />
          Send for Signature
        </button>
      </div>

      <SignatureRequestList
        requests={requests}
        loading={loading}
        onCreateClick={() => setShowWizard(true)}
        onRequestClick={handleRequestClick}
      />

      <SignatureCreateWizard
        isOpen={showWizard}
        onClose={() => setShowWizard(false)}
        onCreate={handleCreate}
        contractTitle={contractTitle}
        sessionId={sessionId}
      />
    </div>
  );
}

"use client";

import React from "react";
import { motion } from "framer-motion";
import { FileSignature, Clock, Users, ChevronRight } from "lucide-react";
import type { SignatureRequest } from "./types";
import { SignatureStatusBadge } from "./SignatureStatusBadge";
import { PROVIDER_LABELS } from "./types";

interface SignatureRequestCardProps {
  request: SignatureRequest;
  onClick?: (id: string) => void;
}

export function SignatureRequestCard({ request, onClick }: SignatureRequestCardProps) {
  const pendingCount = request.signers.filter(s => s.status === "awaiting" || s.status === "sent").length;
  const completedCount = request.signers.filter(s => s.status === "signed").length;

  return (
    <motion.button
      onClick={() => onClick?.(request.id)}
      className="w-full text-left p-3 bg-white border border-gray-200 rounded-lg hover:shadow-md transition-all hover:border-gold-300"
      whileHover={{ y: -1 }}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2 min-w-0">
          <div className="w-8 h-8 rounded-lg bg-navy-100 flex items-center justify-center flex-shrink-0">
            <FileSignature className="w-4 h-4 text-navy-600" />
          </div>
          <div className="min-w-0">
            <p className="text-sm font-semibold text-navy-900 truncate">{request.title}</p>
            <p className="text-[10px] text-gray-500">{PROVIDER_LABELS[request.provider]}</p>
          </div>
        </div>
        <SignatureStatusBadge status={request.status} />
      </div>

      <div className="flex items-center gap-3 mt-2 text-[10px] text-gray-500">
        <div className="flex items-center gap-1">
          <Users className="w-3 h-3" />
          <span>{completedCount}/{request.signers.length} signed</span>
        </div>
        {request.expiresAt && (
          <div className="flex items-center gap-1">
            <Clock className="w-3 h-3" />
            <span>Expires {new Date(request.expiresAt).toLocaleDateString()}</span>
          </div>
        )}
      </div>

      {/* Signer avatars */}
      {request.signers.length > 0 && (
        <div className="flex items-center gap-1 mt-2">
          {request.signers.slice(0, 5).map((signer) => (
            <div
              key={signer.id}
              className={`w-5 h-5 rounded-full flex items-center justify-center text-[7px] font-bold text-white ${
                signer.status === "signed" ? "bg-green-500" :
                signer.status === "declined" ? "bg-red-500" :
                "bg-navy-400"
              }`}
              title={`${signer.name} - ${signer.status}`}
            >
              {signer.name.charAt(0).toUpperCase()}
            </div>
          ))}
          {request.signers.length > 5 && (
            <span className="text-[9px] text-gray-400">+{request.signers.length - 5}</span>
          )}
          <ChevronRight className="w-3 h-3 text-gray-300 ml-auto" />
        </div>
      )}
    </motion.button>
  );
}

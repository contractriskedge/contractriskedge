"use client";

import React from "react";
import type { SignatureStatus } from "./types";
import { STATUS_LABELS, STATUS_COLORS } from "./types";

interface SignatureStatusBadgeProps {
  status: SignatureStatus;
}

export function SignatureStatusBadge({ status }: SignatureStatusBadgeProps) {
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium ${STATUS_COLORS[status] || "bg-gray-100 text-gray-600"}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${
        status === "completed" || status === "signed" ? "bg-green-500" :
        status === "sent" || status === "viewed" ? "bg-blue-500" :
        status === "declined" || status === "expired" || status === "voided" ? "bg-red-500" :
        "bg-gray-400"
      }`} />
      {STATUS_LABELS[status] || status}
    </span>
  );
}

/**
 * ImmutableBanner — visible indicator when a review is in a locked state.
 *
 * Shows at the top of the review workspace when:
 * - APPROVED
 * - REJECTED
 * - FINALIZED
 * - ARCHIVED
 *
 * Clearly communicates that the review is read-only.
 */

"use client";

import React from "react";
import { Lock, ShieldCheck, Archive, XCircle } from "lucide-react";
import { isImmutable, getImmutableBannerInfo } from "@/lib/workflow";

interface ImmutableBannerProps {
  status: string;
}

const ICON_MAP: Record<string, React.ReactNode> = {
  approved: <ShieldCheck className="w-5 h-5" />,
  rejected: <XCircle className="w-5 h-5" />,
  finalized: <Lock className="w-5 h-5" />,
  archived: <Archive className="w-5 h-5" />,
};

export function ImmutableBanner({ status }: ImmutableBannerProps) {
  if (!isImmutable(status)) return null;

  const info = getImmutableBannerInfo(status);
  if (!info) return null;

  return (
    <div
      className={`flex items-start gap-3 rounded-lg border-2 p-4 ${info.color}`}
      role="alert"
      aria-live="polite"
    >
      <div className="mt-0.5 flex-shrink-0">
        {ICON_MAP[status] || <Lock className="w-5 h-5" />}
      </div>
      <div className="flex-1">
        <p className="text-sm font-bold">{info.title}</p>
        <p className="text-xs mt-1 opacity-80">{info.description}</p>
      </div>
    </div>
  );
}

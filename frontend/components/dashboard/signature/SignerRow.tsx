"use client";

import React from "react";
import { User, CheckCircle, XCircle, Clock, Trash2 } from "lucide-react";
import type { Signer } from "./types";

interface SignerRowProps {
  signer: Signer;
  onRemove?: (id: string) => void;
  removable?: boolean;
}

export function SignerRow({ signer, onRemove, removable }: SignerRowProps) {
  const statusIcon = signer.status === "signed" ? <CheckCircle className="w-3 h-3 text-green-500" /> :
    signer.status === "declined" ? <XCircle className="w-3 h-3 text-red-500" /> :
    <Clock className="w-3 h-3 text-amber-500" />;

  return (
    <div className="flex items-center gap-2 px-3 py-2 hover:bg-gray-50 rounded-lg transition-colors group">
      <div className="w-7 h-7 rounded-full bg-navy-500 flex items-center justify-center text-[10px] font-bold text-white flex-shrink-0">
        {signer.name.charAt(0).toUpperCase()}
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-1.5">
          <span className="text-xs font-medium text-navy-900">{signer.name}</span>
          <span className="text-[9px] text-gray-400">{signer.role}</span>
          {signer.signingOrder > 1 && (
            <span className="text-[9px] text-gray-400">Order #{signer.signingOrder}</span>
          )}
        </div>
        <p className="text-[10px] text-gray-500">{signer.email}</p>
      </div>
      <div className="flex items-center gap-1">
        {statusIcon}
        <span className="text-[10px] text-gray-500 capitalize">{signer.status}</span>
      </div>
      {removable && onRemove && (
        <button
          onClick={() => onRemove(signer.id)}
          className="p-1 text-gray-300 hover:text-red-500 opacity-0 group-hover:opacity-100 transition-all"
        >
          <Trash2 className="w-3 h-3" />
        </button>
      )}
    </div>
  );
}

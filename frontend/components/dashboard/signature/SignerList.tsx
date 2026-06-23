"use client";

import React from "react";
import { Users, Plus } from "lucide-react";
import type { Signer } from "./types";
import { SignerRow } from "./SignerRow";

interface SignerListProps {
  signers: Signer[];
  onAddClick?: () => void;
  onRemoveSigner?: (id: string) => void;
  editable?: boolean;
}

export function SignerList({ signers, onAddClick, onRemoveSigner, editable }: SignerListProps) {
  if (signers.length === 0) {
    return (
      <div className="text-center py-6">
        <Users className="w-8 h-8 text-gray-300 mx-auto mb-2" />
        <p className="text-[10px] text-gray-500">No signers added yet</p>
        {editable && onAddClick && (
          <button
            onClick={onAddClick}
            className="mt-2 inline-flex items-center gap-1 px-2 py-1 text-[10px] font-medium text-gold-600 hover:text-gold-700"
          >
            <Plus className="w-3 h-3" /> Add Signer
          </button>
        )}
      </div>
    );
  }

  return (
    <div className="space-y-0.5">
      {signers.map((signer) => (
        <SignerRow
          key={signer.id}
          signer={signer}
          onRemove={onRemoveSigner}
          removable={editable}
        />
      ))}
      {editable && onAddClick && (
        <button
          onClick={onAddClick}
          className="w-full flex items-center justify-center gap-1 px-3 py-2 text-[10px] text-gold-600 hover:bg-gold-50 rounded-lg transition-colors border border-dashed border-gray-200 mt-2"
        >
          <Plus className="w-3 h-3" /> Add Signer
        </button>
      )}
    </div>
  );
}

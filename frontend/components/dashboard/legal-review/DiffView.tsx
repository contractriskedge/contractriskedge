"use client";

import React from "react";
import { Columns2, AlignJustify, Diff } from "lucide-react";
import { computeSemanticDiff } from "@/lib/semanticDiff";
import type { DiffViewMode } from "./types";

interface DiffViewProps {
  originalText: string;
  proposedText: string;
  mode: DiffViewMode;
  onModeChange: (mode: DiffViewMode) => void;
}

// ── Inline diff helpers ─────────────────────────────────────────────────────

function computeDiff(original: string, proposed: string): React.ReactNode[] {
  const segments = computeSemanticDiff(original, proposed);

  return segments.map((segment, key) => {
    if (segment.tag === "delete") {
      return (
        <del key={key} className="px-0.5 bg-red-100 text-red-800 rounded line-through">
          {segment.text}
        </del>
      );
    }

    if (segment.tag === "insert") {
      return (
        <ins key={key} className="px-0.5 bg-green-100 text-green-800 rounded no-underline">
          {segment.text}
        </ins>
      );
    }

    return <span key={key}>{segment.text}</span>;
  });
}

// ── Mode toggle buttons ─────────────────────────────────────────────────────

const MODES: { value: DiffViewMode; icon: React.ReactNode; label: string }[] = [
  { value: "side-by-side", icon: <Columns2 className="w-3.5 h-3.5" />, label: "Side by Side" },
  { value: "stacked", icon: <AlignJustify className="w-3.5 h-3.5" />, label: "Stacked" },
  { value: "inline-redline", icon: <Diff className="w-3.5 h-3.5" />, label: "Inline Redline" },
];

// ── Component ────────────────────────────────────────────────────────────────

export function DiffView({ originalText, proposedText, mode, onModeChange }: DiffViewProps) {
  return (
    <div className="space-y-3">
      {/* Toggle */}
      <div className="flex items-center gap-1 p-0.5 bg-gray-100 rounded-lg w-fit" role="radiogroup" aria-label="Diff view mode">
        {MODES.map((m) => (
          <button
            key={m.value}
            onClick={() => onModeChange(m.value)}
            className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md transition-all ${
              mode === m.value
                ? "bg-white shadow-sm text-navy-900 border border-gray-200"
                : "text-gray-500 hover:text-gray-700 hover:bg-gray-50"
            }`}
            role="radio"
            aria-checked={mode === m.value}
            aria-label={m.label}
          >
            {m.icon}
            <span className="hidden sm:inline">{m.label}</span>
          </button>
        ))}
      </div>

      {/* Content */}
      {mode === "side-by-side" && (
        <div className="grid grid-cols-2 gap-3">
          <div className="space-y-1.5">
            <h4 className="text-[11px] font-semibold text-gray-500 uppercase tracking-wider">Original</h4>
            <div className="p-3 bg-red-50 border border-red-100 rounded-lg text-sm text-gray-700 leading-relaxed whitespace-pre-wrap">
              {originalText}
            </div>
          </div>
          <div className="space-y-1.5">
            <h4 className="text-[11px] font-semibold text-gray-500 uppercase tracking-wider">Proposed</h4>
            <div className="p-3 bg-green-50 border border-green-100 rounded-lg text-sm text-gray-700 leading-relaxed whitespace-pre-wrap">
              {proposedText}
            </div>
          </div>
        </div>
      )}

      {mode === "stacked" && (
        <div className="space-y-3">
          <div className="space-y-1.5">
            <h4 className="text-[11px] font-semibold text-gray-500 uppercase tracking-wider">Original</h4>
            <div className="p-3 bg-red-50 border border-red-100 rounded-lg text-sm text-gray-700 leading-relaxed whitespace-pre-wrap">
              {originalText}
            </div>
          </div>
          <div className="space-y-1.5">
            <h4 className="text-[11px] font-semibold text-gray-500 uppercase tracking-wider">Proposed</h4>
            <div className="p-3 bg-green-50 border border-green-100 rounded-lg text-sm text-gray-700 leading-relaxed whitespace-pre-wrap">
              {proposedText}
            </div>
          </div>
        </div>
      )}

      {mode === "inline-redline" && (
        <div className="space-y-1.5">
          <h4 className="text-[11px] font-semibold text-gray-500 uppercase tracking-wider">Redline Comparison</h4>
          <div className="p-3 bg-white border border-gray-200 rounded-lg text-sm text-gray-700 leading-relaxed whitespace-pre-wrap">
            <p className="text-[10px] text-gray-400 mb-2">
              <del className="bg-red-100 text-red-800 px-1 rounded">Strikethrough</del> = removed &nbsp;
              <ins className="bg-green-100 text-green-800 px-1 rounded no-underline">Underline</ins> = added
            </p>
            <div className="leading-relaxed">
              {computeDiff(originalText, proposedText)}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

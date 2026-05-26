"use client";

import React, { useState } from "react";
import { BookOpen, ChevronDown, ChevronUp, ExternalLink } from "lucide-react";
import type { PlaybookPosition } from "./types";

interface CorporatePlaybookCardProps {
  playbook: PlaybookPosition;
}

export function CorporatePlaybookCard({ playbook }: CorporatePlaybookCardProps) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="rounded-lg border border-navy-200 bg-navy-50 overflow-hidden">
      {/* Header */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between px-4 py-3 hover:bg-navy-100/50 transition-colors text-left"
        aria-expanded={expanded}
        aria-controls="playbook-body"
      >
        <div className="flex items-center gap-2">
          <BookOpen className="w-4 h-4 text-navy-600" aria-hidden="true" />
          <span className="text-sm font-semibold text-navy-800">Corporate Playbook</span>
          <span className="text-[10px] font-medium px-1.5 py-0.5 rounded bg-navy-200 text-navy-700 capitalize">
            {playbook.clauseType.replace(/_/g, " ")}
          </span>
        </div>
        {expanded ? (
          <ChevronUp className="w-4 h-4 text-navy-500" />
        ) : (
          <ChevronDown className="w-4 h-4 text-navy-500" />
        )}
      </button>

      {/* Body */}
      {expanded && (
        <div id="playbook-body" className="px-4 pb-4 space-y-3">
          {/* Standard Position */}
          <div>
            <h4 className="text-[11px] font-semibold text-navy-700 uppercase tracking-wider mb-1">
              Standard Position
            </h4>
            <div className="p-2.5 bg-white rounded border border-navy-100 text-xs text-gray-700 leading-relaxed">
              {playbook.standardPosition}
            </div>
          </div>

          {/* Fallback Positions */}
          {playbook.fallbackPositions.length > 0 && (
            <div>
              <h4 className="text-[11px] font-semibold text-navy-700 uppercase tracking-wider mb-1">
                Fallback Positions ({playbook.fallbackPositions.length})
              </h4>
              <div className="space-y-1.5">
                {playbook.fallbackPositions.map((fp, idx) => (
                  <div
                    key={idx}
                    className="flex items-start gap-2 p-2 bg-white rounded border border-navy-100"
                  >
                    <span className="text-[10px] font-bold text-navy-400 mt-0.5 flex-shrink-0">
                      F{idx + 1}
                    </span>
                    <p className="text-xs text-gray-600 leading-relaxed">{fp}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Source */}
          {playbook.source && (
            <p className="text-[10px] text-gray-400 flex items-center gap-1">
              <ExternalLink className="w-3 h-3" />
              Source: {playbook.source}
            </p>
          )}
        </div>
      )}

      {/* Collapsed preview */}
      {!expanded && (
        <div className="px-4 pb-3">
          <p className="text-[11px] text-gray-600 line-clamp-1">
            <span className="font-medium text-navy-700">Standard:</span>{" "}
            {playbook.standardPosition}
          </p>
        </div>
      )}
    </div>
  );
}

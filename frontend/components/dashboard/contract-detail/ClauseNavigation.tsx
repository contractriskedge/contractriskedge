"use client";

import React from "react";
import { FileText, AlertTriangle, BookOpen, ClipboardCheck, MessageSquare, Clock, ChevronRight } from "lucide-react";
import type { ClauseData, RiskLevel } from "./types";
import { RISK_BG, RISK_TEXT, RISK_BG_LIGHT } from "./types";

interface ClauseNavProps {
  clauses: ClauseData[];
  selectedClauseId: string | null;
  onSelectClause: (id: string) => void;
}

const statusColors: Record<string, string> = {
  unacceptable: "border-l-red-500 bg-red-50",
  needs_negotiation: "border-l-orange-500 bg-orange-50",
  needs_review: "border-l-yellow-500 bg-yellow-50",
  acceptable: "border-l-green-500 bg-green-50",
};

const statusLabels: Record<string, string> = {
  unacceptable: "Unacceptable", needs_negotiation: "Negotiate", needs_review: "Review", acceptable: "OK",
};

export function ClauseNavigation({ clauses, selectedClauseId, onSelectClause }: ClauseNavProps) {
  const critical = clauses.filter((c) => c.riskLevel === "critical" || c.riskLevel === "high").length;
  const comments = clauses.reduce((s, c) => s + c.comments.filter((cm) => !cm.resolved).length, 0);

  return (
    <div className="flex flex-col h-full bg-white border-r border-gray-200">
      <div className="px-3 py-2.5 border-b border-gray-100">
        <div className="flex items-center gap-2"><BookOpen className="w-4 h-4 text-navy-700" /><h3 className="text-xs font-semibold text-navy-900">Clauses</h3></div>
        <div className="flex gap-2 mt-1 text-[9px] text-gray-400">
          <span className="text-red-500 font-medium">{critical} critical</span>
          <span>{comments} unresolved comments</span>
        </div>
      </div>
      <div className="flex-1 overflow-y-auto">
        {clauses.map((c) => {
          const isSelected = selectedClauseId === c.id;
          const hasComments = c.comments.filter((cm) => !cm.resolved).length > 0;
          return (
            <button key={c.id} onClick={() => onSelectClause(c.id)}
              className={`w-full text-left px-3 py-2 border-l-3 transition-all ${
                isSelected ? "bg-navy-50 border-l-navy-900" : `${statusColors[c.status]} border-l-transparent hover:border-l-gray-300`
              }`}>
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-medium text-gray-400">§{c.section}</span>
                <div className="flex items-center gap-1">
                  {hasComments && <MessageSquare className="w-2.5 h-2.5 text-navy-500" />}
                  <span className={`text-[9px] font-medium px-1 py-0.5 rounded ${RISK_BG_LIGHT[c.riskLevel]} ${RISK_TEXT[c.riskLevel]}`}>{c.riskScore}</span>
                </div>
              </div>
              <p className={`text-[11px] font-medium mt-0.5 ${isSelected ? "text-navy-900" : "text-gray-700"}`}>{c.title}</p>
              <p className={`text-[9px] mt-0.5 ${statusLabels[c.status] === "Unacceptable" ? "text-red-500" : statusLabels[c.status] === "Negotiate" ? "text-orange-500" : "text-gray-400"}`}>{statusLabels[c.status]}</p>
            </button>
          );
        })}
      </div>
    </div>
  );
}

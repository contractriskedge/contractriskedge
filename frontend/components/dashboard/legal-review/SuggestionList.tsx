"use client";

import React from "react";
import { FileText, ChevronRight, MessageSquare, CheckCircle, XCircle, ArrowUpCircle } from "lucide-react";
import type { ClauseSuggestion, SuggestionStatus, RiskLevel } from "./types";
import { STATUS_CONFIG, RISK_LEVEL_CONFIG } from "./types";
import { RiskBadge } from "./RiskBadge";
import { ConfidenceBar } from "./ConfidenceBar";
import { SelectAllCheckbox } from "./SelectAllCheckbox";

// ── Helpers ─────────────────────────────────────────────────────────────────

const changeTypeColor: Record<string, string> = {
  modify: "bg-blue-100 text-blue-700",
  remove: "bg-red-100 text-red-700",
  add:    "bg-green-100 text-green-700",
  review: "bg-yellow-100 text-yellow-700",
};

// ── Props ────────────────────────────────────────────────────────────────────

interface SuggestionListProps {
  suggestions: ClauseSuggestion[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  selectedIds: Set<string>;
  onSelectionChange: (ids: Set<string>) => void;
  // Filters
  riskFilter: string;
  statusFilter: string;
  clauseTypeFilter: string;
  onRiskFilterChange: (v: string) => void;
  onStatusFilterChange: (v: string) => void;
  onClauseTypeFilterChange: (v: string) => void;
}

// ── Component ────────────────────────────────────────────────────────────────

export function SuggestionList({
  suggestions,
  selectedId,
  onSelect,
  selectedIds,
  onSelectionChange,
  riskFilter,
  statusFilter,
  clauseTypeFilter,
  onRiskFilterChange,
  onStatusFilterChange,
  onClauseTypeFilterChange,
}: SuggestionListProps) {
  // ── Filtering ──
  const filtered = suggestions.filter((s) => {
    if (riskFilter !== "all" && s.riskLevel !== riskFilter) return false;
    if (statusFilter !== "all" && s.status !== statusFilter) return false;
    if (clauseTypeFilter !== "all" && s.clauseType !== clauseTypeFilter) return false;
    return true;
  });

  // ── Bulk selection ──
  const allFilteredSelected = filtered.length > 0 && filtered.every((s) => selectedIds.has(s.suggestionId));
  const someFilteredSelected = filtered.some((s) => selectedIds.has(s.suggestionId)) && !allFilteredSelected;

  const handleSelectAll = (checked: boolean) => {
    const next = new Set(selectedIds);
    for (const s of filtered) {
      if (checked) next.add(s.suggestionId);
      else next.delete(s.suggestionId);
    }
    onSelectionChange(next);
  };

  const toggleOne = (id: string) => {
    const next = new Set(selectedIds);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    onSelectionChange(next);
  };

  // ── Group by contract ──
  const grouped: Record<string, ClauseSuggestion[]> = {};
  for (const s of filtered) {
    if (!grouped[s.contractId]) grouped[s.contractId] = [];
    grouped[s.contractId].push(s);
  }

  return (
    <div className="flex flex-col h-full bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
      {/* Header */}
      <div className="px-4 py-3 border-b border-gray-200 bg-white">
        <div className="flex items-center justify-between mb-2">
          <h2 className="text-sm font-semibold text-navy-900">Redline Suggestions</h2>
          <span className="text-[11px] text-gray-500 font-medium px-2 py-0.5 bg-gray-100 rounded-full">
            {filtered.length}
          </span>
        </div>
        {/* Filter row */}
        <div className="flex gap-1.5">
          <select
            value={riskFilter}
            onChange={(e) => onRiskFilterChange(e.target.value)}
            className="flex-1 text-[11px] border border-gray-200 rounded-md px-2 py-1 text-gray-600 bg-white hover:border-gray-300 focus:border-navy-400 focus:ring-1 focus:ring-navy-400 transition-colors"
            aria-label="Filter by risk level"
          >
            <option value="all">All Risk</option>
            <option value="critical">Critical</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
          </select>
          <select
            value={statusFilter}
            onChange={(e) => onStatusFilterChange(e.target.value)}
            className="flex-1 text-[11px] border border-gray-200 rounded-md px-2 py-1 text-gray-600 bg-white hover:border-gray-300 focus:border-navy-400 focus:ring-1 focus:ring-navy-400 transition-colors"
            aria-label="Filter by status"
          >
            <option value="all">All Status</option>
            <option value="pending">Pending</option>
            <option value="accepted">Accepted</option>
            <option value="rejected">Rejected</option>
            <option value="escalated">Escalated</option>
          </select>
          <select
            value={clauseTypeFilter}
            onChange={(e) => onClauseTypeFilterChange(e.target.value)}
            className="flex-1 text-[11px] border border-gray-200 rounded-md px-2 py-1 text-gray-600 bg-white hover:border-gray-300 focus:border-navy-400 focus:ring-1 focus:ring-navy-400 transition-colors"
            aria-label="Filter by clause type"
          >
            <option value="all">All Types</option>
            <option value="indemnification">Indemnification</option>
            <option value="liability_limitation">Liability</option>
            <option value="termination">Termination</option>
            <option value="confidentiality">Confidentiality</option>
            <option value="data_privacy">Data Privacy</option>
            <option value="compliance">Compliance</option>
            <option value="payment_terms">Payment</option>
            <option value="force_majeure">Force Majeure</option>
            <option value="assignment">Assignment</option>
            <option value="governing_law">Governing Law</option>
            <option value="non_compete">Non-Compete</option>
            <option value="intellectual_property">IP</option>
          </select>
        </div>
      </div>

      {/* Select All */}
      <SelectAllCheckbox
        checked={allFilteredSelected}
        indeterminate={someFilteredSelected}
        onChange={handleSelectAll}
        total={filtered.length}
        selected={selectedIds.size}
      />

      {/* List */}
      <div className="flex-1 overflow-y-auto divide-y divide-gray-100">
        {filtered.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 text-gray-400">
            <FileText className="w-8 h-8 mb-2" />
            <p className="text-sm font-medium">No matching suggestions</p>
            <p className="text-xs mt-0.5">Try adjusting your filters</p>
          </div>
        ) : (
          Object.entries(grouped).map(([contractId, clauses]) => (
            <div key={contractId}>
              {/* Contract group header */}
              <div className="px-4 py-1.5 bg-gray-50 border-b border-gray-100 sticky top-0 z-10">
                <p className="text-[11px] font-semibold text-navy-700 truncate flex items-center gap-1">
                  <FileText className="w-3 h-3 flex-shrink-0" />
                  {clauses[0].contractName || contractId.slice(0, 24) + "…"}
                </p>
              </div>
              {clauses.map((s) => {
                const isSelected = selectedId === s.suggestionId;
                const isChecked = selectedIds.has(s.suggestionId);
                const statusCfg = STATUS_CONFIG[s.status];
                const riskCfg = RISK_LEVEL_CONFIG[s.riskLevel];

                return (
                  <div
                    key={s.suggestionId}
                    className={`group relative transition-colors ${
                      isSelected ? "bg-navy-50 border-l-2 border-navy-900" : "border-l-2 border-transparent hover:bg-gray-50"
                    }`}
                  >
                    <div className="flex items-start gap-2 px-3 py-2.5 cursor-pointer" onClick={() => onSelect(s.suggestionId)}>
                      {/* Checkbox */}
                      <div className="pt-0.5" onClick={(e) => { e.stopPropagation(); toggleOne(s.suggestionId); }}>
                        <input
                          type="checkbox"
                          checked={isChecked}
                          readOnly
                          className="w-3.5 h-3.5 rounded border-gray-300 text-navy-700 focus:ring-navy-400 cursor-pointer"
                          aria-label={`Select ${s.clauseType} suggestion`}
                        />
                      </div>
                      {/* Content */}
                      <div className="flex-1 min-w-0">
                        {/* Top row: clause type + status */}
                        <div className="flex items-center justify-between gap-1 mb-0.5">
                          <span className="text-[11px] font-medium text-gray-700 capitalize truncate">
                            {s.clauseType.replace(/_/g, " ")}
                          </span>
                          <div className="flex items-center gap-1 flex-shrink-0">
                            <span className={`text-[10px] font-medium px-1 py-0.5 rounded ${statusCfg.bg} ${statusCfg.color}`}>
                              {statusCfg.label}
                            </span>
                            <ChevronRight className={`w-3 h-3 text-gray-300 transition-transform ${isSelected ? "rotate-90" : ""}`} />
                          </div>
                        </div>
                        {/* Clause preview */}
                        <p className="text-[11px] text-gray-500 leading-relaxed line-clamp-2 mb-1.5">
                          {s.originalText}
                        </p>
                        {/* Bottom row: risk badge + confidence + change type */}
                        <div className="flex items-center gap-2 flex-wrap">
                          <RiskBadge level={s.riskLevel} size="sm" />
                          <span className={`text-[10px] font-medium px-1 py-0.5 rounded ${changeTypeColor[s.changeType] || "bg-gray-100 text-gray-600"}`}>
                            {s.changeType}
                          </span>
                          <div className="flex-1 min-w-[60px] max-w-[100px]">
                            <ConfidenceBar score={s.confidence} size="sm" showLabel={false} />
                          </div>
                          <span className="text-[10px] text-gray-400 tabular-nums">{Math.round(s.confidence * 100)}%</span>
                          {/* Comment indicator */}
                          {s.comments.filter((c) => !c.resolved).length > 0 && (
                            <span className="flex items-center gap-0.5 text-[10px] text-navy-500">
                              <MessageSquare className="w-3 h-3" />
                              {s.comments.filter((c) => !c.resolved).length}
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          ))
        )}
      </div>

      {/* Bulk action bar */}
      {selectedIds.size > 0 && (
        <div className="px-4 py-2.5 border-t border-gray-200 bg-gray-50 flex items-center justify-between">
          <span className="text-xs text-gray-600 font-medium">{selectedIds.size} selected</span>
          <div className="flex gap-1.5">
            <button className="text-xs px-2.5 py-1 rounded-md bg-green-100 text-green-700 hover:bg-green-200 font-medium transition-colors">
              Accept
            </button>
            <button className="text-xs px-2.5 py-1 rounded-md bg-red-100 text-red-700 hover:bg-red-200 font-medium transition-colors">
              Reject
            </button>
            <button className="text-xs px-2.5 py-1 rounded-md bg-purple-100 text-purple-700 hover:bg-purple-200 font-medium transition-colors">
              Escalate
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

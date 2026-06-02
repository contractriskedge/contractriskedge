"use client";

import React, { useState, useMemo } from "react";
import {
  FileText, ChevronLeft, ChevronRight, ArrowUpDown, MoreHorizontal,
  Columns, Eye, AlertTriangle, CheckCircle, XCircle, Clock,
} from "lucide-react";
import type { ContractRecord, RiskLevel, AiFlag } from "./types";
import { RISK_BG, RISK_TEXT, RISK_BG_LIGHT, RISK_DARK_BG, RISK_DARK_TEXT, AI_FLAG_CONFIG, STATUS_CONFIG, WORKFLOW_STAGES } from "./types";

// ── Risk Badge ──────────────────────────────────────────────────────────────

function RiskBadge({ score }: { score: number }) {
  const level: RiskLevel = score >= 8 ? "critical" : score >= 6 ? "high" : score >= 4 ? "medium" : "low";
  return (
    <span className={`inline-flex items-center gap-1 text-[10px] font-bold px-1.5 py-0.5 rounded-full ${RISK_BG_LIGHT[level]} ${RISK_TEXT[level]} ${RISK_DARK_BG[level]} ${RISK_DARK_TEXT[level]}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${RISK_BG[level]}`} />{score}/10
    </span>
  );
}

// ── AI Flag Badge ───────────────────────────────────────────────────────────

function AiFlagBadge({ flag }: { flag: AiFlag }) {
  const cfg = AI_FLAG_CONFIG[flag];
  return <span className={`text-[9px] font-medium px-1.5 py-0.5 rounded-full ${cfg.bg} ${cfg.color} ${cfg.darkBg} ${cfg.darkColor} whitespace-nowrap`}>{cfg.label}</span>;
}

// ── Status Badge ────────────────────────────────────────────────────────────

function StatusBadge({ status }: { status: string }) {
  const c = STATUS_CONFIG[status] || STATUS_CONFIG.draft;
  return <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded-full ${c.bg} ${c.color} ${c.darkBg} ${c.darkColor}`}>{c.label}</span>;
}

// ── Renewal Risk Indicator ──────────────────────────────────────────────────

function RenewalRisk({ level }: { level: string }) {
  const colors: Record<string, string> = {
    high: "text-red-600 bg-red-50 dark:text-red-400 dark:bg-red-900/20",
    medium: "text-amber-600 bg-amber-50 dark:text-amber-400 dark:bg-amber-900/20",
    low: "text-green-600 bg-green-50 dark:text-green-400 dark:bg-green-900/20",
  };
  return <span className={`text-[9px] font-medium px-1.5 py-0.5 rounded-full ${colors[level] || colors.low}`}>{level}</span>;
}

// ── AI Confidence Status ────────────────────────────────────────────────────

function AiStatus({ confidence, findings }: { confidence: number; findings: number }) {
  const color = confidence >= 85 ? "text-green-600" : confidence >= 70 ? "text-amber-600" : "text-red-600";
  const bg = confidence >= 85 ? "bg-green-50 dark:bg-green-900/20" : confidence >= 70 ? "bg-amber-50 dark:bg-amber-900/20" : "bg-red-50 dark:bg-red-900/20";
  return (
    <div className="flex items-center gap-1.5">
      <div className="flex-1 h-1.5 bg-gray-200 dark:bg-navy-700 rounded-full overflow-hidden max-w-[40px]">
        <div className={`h-full rounded-full ${confidence >= 85 ? "bg-green-500" : confidence >= 70 ? "bg-amber-500" : "bg-red-500"}`} style={{ width: `${confidence}%` }} />
      </div>
      <div className="flex flex-col">
        <span className={`text-[9px] font-semibold tabular-nums ${color}`}>{confidence}%</span>
        {findings > 0 && <span className="text-[8px] text-gray-400 dark:text-gray-500">{findings} finding{findings > 1 ? 's' : ''}</span>}
      </div>
    </div>
  );
}

// ── Quick Actions Menu ──────────────────────────────────────────────────────

function QuickActions({ onClose }: { onClose: () => void }) {
  return (
    <>
      <div className="fixed inset-0 z-30" onClick={onClose} />
      <div className="absolute right-0 top-full mt-1 z-40 w-44 bg-white dark:bg-navy-800 rounded-lg border border-gray-200 dark:border-navy-700 shadow-lg py-1">
        {["View Details", "Analyze Risks", "Generate Redlines", "Assign Reviewer", "Add Tags", "Request Approval", "Export PDF", "Archive"].map((action) => (
          <button key={action} onClick={onClose} className="w-full text-left px-3 py-1.5 text-[11px] text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-navy-700 transition-colors">{action}</button>
        ))}
      </div>
    </>
  );
}

// ── Column Config ───────────────────────────────────────────────────────────

const ALL_COLUMNS = [
  { key: "name", label: "Contract Name", default: true },
  { key: "vendor", label: "Vendor", default: true },
  { key: "contractType", label: "Agreement Type", default: true },
  { key: "owner", label: "Owner", default: true },
  { key: "effectiveDate", label: "Effective", default: true },
  { key: "expirationDate", label: "Expiration", default: true },
  { key: "renewalRisk", label: "Renewal Risk", default: true },
  { key: "riskScore", label: "Risk", default: true },
  { key: "aiStatus", label: "AI Review", default: true },
  { key: "status", label: "Status", default: true },
  { key: "lastActivity", label: "Last Activity", default: false },
  { key: "financialValue", label: "Value", default: false },
  { key: "workflowStage", label: "Workflow", default: false },
];

// ── Main Table ──────────────────────────────────────────────────────────────

interface ContractsTableProps {
  contracts: ContractRecord[];
  onSelectContract: (contract: ContractRecord) => void;
}

type SortKey = "riskScore" | "financialValue" | "name" | "vendor" | "renewalDate" | "aiConfidence" | "lastModified" | "effectiveDate" | "expirationDate";

export function ContractsTable({ contracts, onSelectContract }: ContractsTableProps) {
  const [sortKey, setSortKey] = useState<SortKey>("riskScore");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");
  const [page, setPage] = useState(0);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [openActions, setOpenActions] = useState<string | null>(null);
  const [visibleColumns, setVisibleColumns] = useState<Set<string>>(new Set(ALL_COLUMNS.filter(c => c.default).map(c => c.key)));
  const [showColumnChooser, setShowColumnChooser] = useState(false);
  const [hoveredId, setHoveredId] = useState<string | null>(null);
  const pageSize = 15;

  const handleSort = (k: SortKey) => {
    if (sortKey === k) setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    else { setSortKey(k); setSortDir("desc"); }
  };

  const sorted = useMemo(() => {
    const list = [...contracts];
    list.sort((a, b) => {
      const d = sortDir === "asc" ? 1 : -1;
      if (sortKey === "riskScore") return (a.riskScore - b.riskScore) * d;
      if (sortKey === "financialValue") return (a.financialValue - b.financialValue) * d;
      if (sortKey === "aiConfidence") return (a.aiConfidence - b.aiConfidence) * d;
      if (sortKey === "renewalDate" || sortKey === "effectiveDate" || sortKey === "expirationDate") {
        const aVal = a[sortKey] || "";
        const bVal = b[sortKey] || "";
        return aVal.localeCompare(bVal) * d;
      }
      if (sortKey === "lastModified") return (new Date(a.lastModified).getTime() - new Date(b.lastModified).getTime()) * d;
      return a[sortKey].localeCompare(b[sortKey]) * d;
    });
    return list;
  }, [contracts, sortKey, sortDir]);

  const totalPages = Math.ceil(sorted.length / pageSize);
  const pageContracts = sorted.slice(page * pageSize, (page + 1) * pageSize);
  const allSelected = pageContracts.length > 0 && pageContracts.every((c) => selectedIds.has(c.id));
  const someSelected = pageContracts.some((c) => selectedIds.has(c.id));

  const toggleAll = () => {
    if (allSelected) {
      const next = new Set<string>();
      selectedIds.forEach(function(id) { if (!pageContracts.some(function(c) { return c.id === id; })) next.add(id); });
      setSelectedIds(next);
    } else {
      const next = new Set(selectedIds);
      pageContracts.forEach((c) => next.add(c.id));
      setSelectedIds(next);
    }
  };

  const toggleColumn = (key: string) => setVisibleColumns(prev => { const n = new Set(prev); n.has(key) ? n.delete(key) : n.add(key); return n; });

  const colClass = (key: string) => {
    if (key === "name") return "flex-1 min-w-[240px] max-w-[35%]";
    if (key === "vendor") return "w-28";
    if (key === "contractType") return "w-24";
    if (key === "owner") return "w-20";
    if (key === "effectiveDate" || key === "expirationDate") return "w-22";
    if (key === "renewalRisk") return "w-22";
    if (key === "riskScore") return "w-16";
    if (key === "aiStatus") return "w-24";
    if (key === "status") return "w-24";
    if (key === "lastActivity") return "w-22";
    if (key === "financialValue") return "w-16";
    if (key === "workflowStage") return "w-24";
    return "flex-1";
  };

  const SortHeader = ({ label, k }: { label: string; k: SortKey }) => (
    <th className={`text-left py-2 px-2 text-[10px] font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider cursor-pointer hover:text-navy-700 dark:hover:text-gray-200 select-none ${colClass(k)}`} onClick={() => handleSort(k)}>
      <div className="flex items-center gap-1">{label}<ArrowUpDown className={`w-2.5 h-2.5 ${sortKey === k ? "text-blue-500" : "text-gray-300 dark:text-navy-500"}`} /></div>
    </th>
  );

  return (
    <div className="bg-white dark:bg-navy-800 rounded-lg border border-gray-200 dark:border-navy-700 overflow-hidden">
      {/* Selection bar */}
      {selectedIds.size > 0 && (
        <div className="px-3 py-1.5 bg-blue-50 dark:bg-blue-900/10 border-b border-blue-200 dark:border-blue-900/30 flex items-center justify-between">
          <span className="text-[11px] font-medium text-blue-700 dark:text-blue-400">{selectedIds.size} selected</span>
          <div className="flex gap-1">
            {["Analyze", "Export", "Assign", "Tag", "Archive"].map((a) => (
              <button key={a} className="text-[10px] font-medium px-1.5 py-0.5 rounded bg-white dark:bg-navy-700 border border-blue-200 dark:border-blue-800 text-blue-700 dark:text-blue-400 hover:bg-blue-50 dark:hover:bg-navy-600 transition-colors">{a}</button>
            ))}
          </div>
        </div>
      )}

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead className="bg-gray-50 dark:bg-navy-800/50 border-b border-gray-100 dark:border-navy-700 sticky top-0 z-10">
            <tr>
              <th className="py-2 px-2 w-8">
                <input type="checkbox" checked={allSelected} ref={(el) => { if (el) el.indeterminate = someSelected && !allSelected; }} onChange={toggleAll}
                  className="w-3 h-3 rounded border-gray-300 dark:border-navy-500 text-blue-500 focus:ring-blue-400 cursor-pointer" />
              </th>
              {ALL_COLUMNS.filter(c => visibleColumns.has(c.key)).map(col => {
                if (["name", "vendor", "riskScore", "financialValue", "renewalDate", "aiConfidence", "lastModified", "effectiveDate", "expirationDate"].includes(col.key)) {
                  return <SortHeader key={col.key} label={col.label} k={col.key as SortKey} />;
                }
                return <th key={col.key} className={`text-left py-2 px-2 text-[10px] font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider ${colClass(col.key)}`}>{col.label}</th>;
              })}
              <th className="py-2 px-2 w-8">
                <div className="relative">
                  <button onClick={() => setShowColumnChooser(!showColumnChooser)} className="p-0.5 text-gray-400 hover:text-navy-600 dark:hover:text-gray-300 rounded" title="Columns">
                    <Columns className="w-3 h-3" />
                  </button>
                  {showColumnChooser && (
                    <>
                      <div className="fixed inset-0 z-10" onClick={() => setShowColumnChooser(false)} />
                      <div className="absolute right-0 top-full mt-0.5 bg-white dark:bg-navy-800 border border-gray-200 dark:border-navy-700 rounded shadow-lg z-20 py-0.5 w-36">
                        <div className="px-2 py-1 text-[8px] font-semibold text-gray-400 uppercase tracking-wider">Columns</div>
                        {ALL_COLUMNS.map(col => (
                          <label key={col.key} className="flex items-center gap-1.5 px-2 py-0.5 text-[10px] text-navy-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-navy-700 cursor-pointer">
                            <input type="checkbox" checked={visibleColumns.has(col.key)} onChange={() => toggleColumn(col.key)} className="w-2.5 h-2.5 rounded border-gray-300 text-blue-500" />
                            {col.label}
                          </label>
                        ))}
                      </div>
                    </>
                  )}
                </div>
              </th>
              <th className="py-2 px-2 w-8 text-[10px] font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">Act</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-50 dark:divide-navy-800">
            {pageContracts.map((c) => {
              const isSelected = selectedIds.has(c.id);
              const isHovered = hoveredId === c.id;
              return (
                <tr key={c.id}
                  className={`transition-colors cursor-pointer group ${isSelected ? "bg-blue-50/30 dark:bg-blue-900/10" : isHovered ? "bg-gray-50 dark:bg-navy-800/50" : "bg-white dark:bg-navy-800"}`}
                  onClick={() => onSelectContract(c)}
                  onMouseEnter={() => setHoveredId(c.id)}
                  onMouseLeave={() => setHoveredId(null)}
                >
                  <td className="py-2 px-2" onClick={(e) => e.stopPropagation()}>
                    <input type="checkbox" checked={isSelected}
                      onChange={() => { const next = new Set(selectedIds); isSelected ? next.delete(c.id) : next.add(c.id); setSelectedIds(next); }}
                      className="w-3 h-3 rounded border-gray-300 dark:border-navy-500 text-blue-500 focus:ring-blue-400 cursor-pointer" />
                  </td>
                  {visibleColumns.has("name") && (
                    <td className="py-2 px-2">
                      <div className="flex items-start gap-2">
                        <div className={`w-7 h-7 rounded flex items-center justify-center flex-shrink-0 mt-0.5 ${isHovered ? 'bg-blue-50 dark:bg-blue-900/20 text-blue-600' : 'bg-gray-100 dark:bg-navy-700 text-gray-400 dark:text-navy-400'}`}>
                          <FileText className="w-3.5 h-3.5" />
                        </div>
                        <div className="min-w-0 flex-1">
                          <div className="flex items-center gap-1.5">
                            <span className="text-[12px] font-semibold text-navy-900 dark:text-white truncate max-w-[280px] block">{c.name}</span>
                            {isHovered && <Eye className="w-3 h-3 text-blue-500 flex-shrink-0" />}
                          </div>
                          <div className="flex items-center gap-1.5 mt-0.5 flex-wrap">
                            {c.aiFlags.slice(0, 2).map((flag) => <AiFlagBadge key={flag} flag={flag} />)}
                            {c.counterparty && <span className="text-[9px] text-gray-400 dark:text-gray-500 truncate max-w-[120px]">{c.counterparty}</span>}
                          </div>
                        </div>
                      </div>
                    </td>
                  )}
                  {visibleColumns.has("vendor") && <td className="py-2 px-2 text-[11px] text-gray-700 dark:text-gray-200 font-medium">{c.vendor || '—'}</td>}
                  {visibleColumns.has("contractType") && <td className="py-2 px-2"><span className="text-[10px] font-medium px-1.5 py-0.5 rounded bg-gray-100 dark:bg-navy-700 text-gray-600 dark:text-gray-300">{c.contractType}</span></td>}
                  {visibleColumns.has("owner") && <td className="py-2 px-2 text-[11px] text-gray-600 dark:text-gray-300">{c.owner || '—'}</td>}
                  {visibleColumns.has("effectiveDate") && <td className="py-2 px-2 text-[11px] text-gray-600 dark:text-gray-400 tabular-nums">{c.effectiveDate || '—'}</td>}
                  {visibleColumns.has("expirationDate") && (
                    <td className={`py-2 px-2 text-[11px] tabular-nums ${c.status === "expiring_soon" || c.status === "renewal_at_risk" ? "text-orange-600 dark:text-orange-400 font-medium" : "text-gray-600 dark:text-gray-400"}`}>
                      {c.expirationDate || c.renewalDate || '—'}
                    </td>
                  )}
                  {visibleColumns.has("renewalRisk") && <td className="py-2 px-2"><RenewalRisk level={c.renewalRisk || 'low'} /></td>}
                  {visibleColumns.has("riskScore") && <td className="py-2 px-2"><RiskBadge score={c.riskScore} /></td>}
                  {visibleColumns.has("aiStatus") && <td className="py-2 px-2"><AiStatus confidence={c.aiConfidence} findings={c.aiFindingsCount || 0} /></td>}
                  {visibleColumns.has("status") && <td className="py-2 px-2"><StatusBadge status={c.status} /></td>}
                  {visibleColumns.has("lastActivity") && <td className="py-2 px-2 text-[10px] text-gray-400 dark:text-gray-500 tabular-nums">{c.lastActivity || c.lastModified || '—'}</td>}
                  {visibleColumns.has("financialValue") && <td className="py-2 px-2"><span className="font-medium tabular-nums text-[11px] text-gray-800 dark:text-gray-200">${c.financialValue}M</span></td>}
                  {visibleColumns.has("workflowStage") && <td className="py-2 px-2"><span className="text-[10px] font-medium px-1.5 py-0.5 rounded bg-gray-100 dark:bg-navy-700 text-gray-600 dark:text-gray-300">{(WORKFLOW_STAGES[c.workflowStage as keyof typeof WORKFLOW_STAGES] || WORKFLOW_STAGES.draft).label}</span></td>}
                  <td className="py-2 px-2 relative" onClick={(e) => e.stopPropagation()}>
                    <button onClick={() => setOpenActions(openActions === c.id ? null : c.id)}
                      className={`p-0.5 rounded transition-colors ${isHovered ? 'text-gray-500 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-navy-700' : 'text-gray-300 dark:text-navy-500 opacity-0 group-hover:opacity-100'}`}>
                      <MoreHorizontal className="w-3 h-3" />
                    </button>
                    {openActions === c.id && <QuickActions onClose={() => setOpenActions(null)} />}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Empty state */}
      {sorted.length === 0 && (
        <div className="text-center py-12 text-gray-400 dark:text-navy-400">
          <FileText className="w-10 h-10 mx-auto mb-3 text-gray-300 dark:text-navy-500" />
          <p className="text-sm font-medium text-gray-500 dark:text-gray-400">No contracts match your filters</p>
          <p className="text-xs mt-1 text-gray-400 dark:text-navy-400">Try adjusting your search or filter criteria</p>
        </div>
      )}

      {/* Pagination */}
      {sorted.length > 0 && (
        <div className="px-3 py-2 border-t border-gray-100 dark:border-navy-700 flex items-center justify-between">
          <span className="text-[11px] text-gray-500 dark:text-gray-400">Showing {page * pageSize + 1}–{Math.min((page + 1) * pageSize, sorted.length)} of {sorted.length}</span>
          <div className="flex items-center gap-1">
            <button onClick={() => setPage(Math.max(0, page - 1))} disabled={page === 0}
              className="p-1 rounded hover:bg-gray-100 dark:hover:bg-navy-700 disabled:opacity-30 transition-colors text-gray-500 dark:text-gray-400"><ChevronLeft className="w-3 h-3" /></button>
            {Array.from({ length: totalPages }, (_, i) => (
              <button key={i} onClick={() => setPage(i)}
                className={`w-6 h-6 text-[10px] rounded transition-colors ${i === page ? "bg-navy-700 dark:bg-navy-600 text-white" : "text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-navy-700"}`}>{i + 1}</button>
            ))}
            <button onClick={() => setPage(Math.min(totalPages - 1, page + 1))} disabled={page >= totalPages - 1}
              className="p-1 rounded hover:bg-gray-100 dark:hover:bg-navy-700 disabled:opacity-30 transition-colors text-gray-500 dark:text-gray-400"><ChevronRight className="w-3 h-3" /></button>
          </div>
        </div>
      )}
    </div>
  );
}

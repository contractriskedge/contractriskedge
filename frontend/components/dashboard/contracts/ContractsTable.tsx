"use client";

import React, { useState, useMemo } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  FileText, ChevronDown, ChevronUp, ChevronLeft, ChevronRight, Search,
  ArrowUpDown, Eye, MoreHorizontal, CheckSquare, Square,
  AlertTriangle, Brain, FileX, RefreshCw, Shield, BarChart3,
} from "lucide-react";
import type { ContractRecord, RiskLevel, AiFlag } from "./types";
import { RISK_BG, RISK_TEXT, RISK_BG_LIGHT, AI_FLAG_CONFIG, WORKFLOW_STAGES } from "./types";

// ── Risk Badge ──────────────────────────────────────────────────────────────

function RiskBadge({ score }: { score: number }) {
  const level: RiskLevel = score >= 8 ? "critical" : score >= 6 ? "high" : score >= 4 ? "medium" : "low";
  return (
    <span className={`inline-flex items-center gap-1 text-[10px] font-bold px-1.5 py-0.5 rounded-full ${RISK_BG_LIGHT[level]} ${RISK_TEXT[level]}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${RISK_BG[level]}`} />
      {score}/10
    </span>
  );
}

// ── AI Flag Badge ───────────────────────────────────────────────────────────

function AiFlagBadge({ flag }: { flag: AiFlag }) {
  const cfg = AI_FLAG_CONFIG[flag];
  return (
    <span className={`text-[9px] font-medium px-1.5 py-0.5 rounded-full ${cfg.bg} ${cfg.color} whitespace-nowrap`}>
      {cfg.label}
    </span>
  );
}

// ── Status Badge ────────────────────────────────────────────────────────────

function StatusBadge({ status }: { status: string }) {
  const map: Record<string, { bg: string; color: string; label: string }> = {
    active: { bg: "bg-green-100", color: "text-green-700", label: "Active" },
    expiring_soon: { bg: "bg-yellow-100", color: "text-yellow-700", label: "Expiring Soon" },
    under_review: { bg: "bg-blue-100", color: "text-blue-700", label: "Under Review" },
    pending_signature: { bg: "bg-purple-100", color: "text-purple-700", label: "Pending Signature" },
    expired: { bg: "bg-red-100", color: "text-red-700", label: "Expired" },
    draft: { bg: "bg-gray-100", color: "text-gray-600", label: "Draft" },
  };
  const c = map[status] || map.draft;
  return <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded-full ${c.bg} ${c.color}`}>{c.label}</span>;
}

// ── Workflow Badge ──────────────────────────────────────────────────────────

function WorkflowBadge({ stage }: { stage: string }) {
  const cfg = WORKFLOW_STAGES[stage as keyof typeof WORKFLOW_STAGES] || WORKFLOW_STAGES.draft;
  return <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded-full ${cfg.bg} ${cfg.color}`}>{cfg.label}</span>;
}

// ── Quick Actions Menu ──────────────────────────────────────────────────────

function QuickActions({ onClose }: { onClose: () => void }) {
  return (
    <>
      <div className="fixed inset-0 z-30" onClick={onClose} />
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        className="absolute right-0 top-full mt-1 z-40 w-44 bg-white rounded-lg border border-gray-200 shadow-lg py-1"
      >
        {["Analyze Risks", "Generate Redlines", "Assign Reviewer", "Add Tags", "Request Approval", "Export PDF", "Archive"].map((action) => (
          <button key={action} onClick={onClose} className="w-full text-left px-3 py-1.5 text-xs text-gray-700 hover:bg-navy-50 transition-colors">
            {action}
          </button>
        ))}
      </motion.div>
    </>
  );
}

// ── Main Table ──────────────────────────────────────────────────────────────

interface ContractsTableProps {
  contracts: ContractRecord[];
  onSelectContract: (contract: ContractRecord) => void;
}

type SortKey = "riskScore" | "financialValue" | "name" | "vendor" | "renewalDate" | "aiConfidence" | "lastModified";

export function ContractsTable({ contracts, onSelectContract }: ContractsTableProps) {
  const [sortKey, setSortKey] = useState<SortKey>("riskScore");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");
  const [page, setPage] = useState(0);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [openActions, setOpenActions] = useState<string | null>(null);
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
      if (sortKey === "renewalDate") return (new Date(a.renewalDate).getTime() - new Date(b.renewalDate).getTime()) * d;
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
      setSelectedIds(new Set([...selectedIds].filter((id) => !pageContracts.some((c) => c.id === id))));
    } else {
      const next = new Set(selectedIds);
      pageContracts.forEach((c) => next.add(c.id));
      setSelectedIds(next);
    }
  };

  const SortHeader = ({ label, k, className = "" }: { label: string; k: SortKey; className?: string }) => (
    <th
      className={`text-left py-3 px-3 text-[10px] font-semibold text-gray-500 uppercase tracking-wider cursor-pointer hover:text-navy-700 select-none ${className}`}
      onClick={() => handleSort(k)}
    >
      <div className="flex items-center gap-1">
        {label}
        <ArrowUpDown className={`w-3 h-3 ${sortKey === k ? "text-navy-500" : "text-gray-300"}`} />
      </div>
    </th>
  );

  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
      {/* Selection bar */}
      {selectedIds.size > 0 && (
        <div className="px-4 py-2 bg-navy-50 border-b border-navy-100 flex items-center justify-between">
          <span className="text-xs font-medium text-navy-700">{selectedIds.size} selected</span>
          <div className="flex gap-1.5">
            {["Analyze", "Export", "Assign", "Tag", "Archive"].map((a) => (
              <button key={a} className="text-[10px] font-medium px-2 py-1 rounded-md bg-white border border-navy-200 text-navy-700 hover:bg-navy-100 transition-colors">
                {a}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead className="bg-gray-50 border-b border-gray-100 sticky top-0 z-10">
            <tr>
              <th className="py-3 px-3 w-8">
                <input
                  type="checkbox"
                  checked={allSelected}
                  ref={(el) => { if (el) el.indeterminate = someSelected && !allSelected; }}
                  onChange={toggleAll}
                  className="w-3.5 h-3.5 rounded border-gray-300 text-navy-700 focus:ring-navy-400 cursor-pointer"
                />
              </th>
              <SortHeader label="Contract Name" k="name" />
              <SortHeader label="Vendor" k="vendor" />
              <th className="text-left py-3 px-3 text-[10px] font-semibold text-gray-500 uppercase tracking-wider">Type</th>
              <SortHeader label="Risk" k="riskScore" className="w-16" />
              <SortHeader label="Value" k="financialValue" className="w-20" />
              <th className="text-left py-3 px-3 text-[10px] font-semibold text-gray-500 uppercase tracking-wider">Status</th>
              <SortHeader label="Renewal" k="renewalDate" />
              <SortHeader label="AI Conf." k="aiConfidence" className="w-20" />
              <th className="text-left py-3 px-3 text-[10px] font-semibold text-gray-500 uppercase tracking-wider">Owner</th>
              <th className="text-left py-3 px-3 text-[10px] font-semibold text-gray-500 uppercase tracking-wider">Workflow</th>
              <SortHeader label="Modified" k="lastModified" />
              <th className="py-3 px-3 w-10" />
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-50">
            {pageContracts.map((c, i) => {
              const isSelected = selectedIds.has(c.id);
              return (
                <motion.tr
                  key={c.id}
                  initial={{ opacity: 0, y: 3 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.02 }}
                  className={`hover:bg-navy-50/40 transition-colors cursor-pointer group ${isSelected ? "bg-navy-50/60" : ""}`}
                  onClick={() => onSelectContract(c)}
                >
                  <td className="py-2.5 px-3" onClick={(e) => e.stopPropagation()}>
                    <input
                      type="checkbox"
                      checked={isSelected}
                      onChange={() => {
                        const next = new Set(selectedIds);
                        isSelected ? next.delete(c.id) : next.add(c.id);
                        setSelectedIds(next);
                      }}
                      className="w-3.5 h-3.5 rounded border-gray-300 text-navy-700 focus:ring-navy-400 cursor-pointer"
                    />
                  </td>
                  <td className="py-2.5 px-3">
                    <div className="flex items-center gap-2">
                      <FileText className="w-3.5 h-3.5 text-gray-300 flex-shrink-0" />
                      <div>
                        <span className="font-medium text-gray-800 text-[11px] truncate max-w-[160px] block">{c.name}</span>
                        <div className="flex gap-1 mt-0.5">
                          {c.aiFlags.slice(0, 2).map((flag) => (
                            <AiFlagBadge key={flag} flag={flag} />
                          ))}
                        </div>
                      </div>
                    </div>
                  </td>
                  <td className="py-2.5 px-3 text-gray-600 text-[11px]">{c.vendor}</td>
                  <td className="py-2.5 px-3">
                    <span className="text-[10px] font-medium px-1.5 py-0.5 rounded bg-gray-100 text-gray-600">{c.contractType}</span>
                  </td>
                  <td className="py-2.5 px-3"><RiskBadge score={c.riskScore} /></td>
                  <td className="py-2.5 px-3">
                    <span className="font-medium tabular-nums text-[11px]">${c.financialValue}M</span>
                  </td>
                  <td className="py-2.5 px-3"><StatusBadge status={c.status} /></td>
                  <td className="py-2.5 px-3">
                    <span className={`tabular-nums text-[11px] ${c.status === "expiring_soon" ? "text-orange-600 font-medium" : "text-gray-600"}`}>
                      {c.renewalDate}
                    </span>
                  </td>
                  <td className="py-2.5 px-3">
                    <div className="flex items-center gap-1.5">
                      <div className="w-10 h-1.5 bg-gray-200 rounded-full overflow-hidden">
                        <div className={`h-full rounded-full ${c.aiConfidence >= 85 ? "bg-green-500" : c.aiConfidence >= 70 ? "bg-yellow-500" : "bg-red-500"}`}
                          style={{ width: `${c.aiConfidence}%` }} />
                      </div>
                      <span className="text-[10px] text-gray-500 tabular-nums">{c.aiConfidence}%</span>
                    </div>
                  </td>
                  <td className="py-2.5 px-3 text-gray-600 text-[11px]">{c.owner}</td>
                  <td className="py-2.5 px-3"><WorkflowBadge stage={c.workflowStage} /></td>
                  <td className="py-2.5 px-3 text-gray-400 text-[10px] tabular-nums">{c.lastModified}</td>
                  <td className="py-2.5 px-3 relative" onClick={(e) => e.stopPropagation()}>
                    <button
                      onClick={() => setOpenActions(openActions === c.id ? null : c.id)}
                      className="p-1 rounded hover:bg-gray-100 text-gray-300 hover:text-gray-600 opacity-0 group-hover:opacity-100 transition-all"
                    >
                      <MoreHorizontal className="w-3.5 h-3.5" />
                    </button>
                    {openActions === c.id && <QuickActions onClose={() => setOpenActions(null)} />}
                  </td>
                </motion.tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Empty state */}
      {sorted.length === 0 && (
        <div className="text-center py-16 text-gray-400">
          <FileText className="w-10 h-10 mx-auto mb-3 text-gray-300" />
          <p className="text-sm font-medium text-gray-500">No contracts match your filters</p>
          <p className="text-xs mt-1">Try adjusting your search or filter criteria</p>
        </div>
      )}

      {/* Pagination */}
      {sorted.length > 0 && (
        <div className="px-4 py-2.5 border-t border-gray-100 flex items-center justify-between">
          <span className="text-[11px] text-gray-500">
            Showing {page * pageSize + 1}–{Math.min((page + 1) * pageSize, sorted.length)} of {sorted.length}
          </span>
          <div className="flex items-center gap-1">
            <button onClick={() => setPage(Math.max(0, page - 1))} disabled={page === 0}
              className="p-1 rounded hover:bg-gray-100 disabled:opacity-30 transition-colors"><ChevronLeft className="w-3.5 h-3.5" /></button>
            {Array.from({ length: totalPages }, (_, i) => (
              <button key={i} onClick={() => setPage(i)}
                className={`w-6 h-6 text-[10px] rounded transition-colors ${i === page ? "bg-navy-700 text-white" : "text-gray-500 hover:bg-gray-100"}`}>{i + 1}</button>
            ))}
            <button onClick={() => setPage(Math.min(totalPages - 1, page + 1))} disabled={page >= totalPages - 1}
              className="p-1 rounded hover:bg-gray-100 disabled:opacity-30 transition-colors"><ChevronRight className="w-3.5 h-3.5" /></button>
          </div>
        </div>
      )}
    </div>
  );
}

"use client";

import React, { useState, useMemo } from "react";
import { motion } from "framer-motion";
import { ChevronLeft, ChevronRight, Search, ArrowUpDown, Clock, AlertTriangle, MessageSquare, Paperclip, User } from "lucide-react";
import type { WorkflowItem, WorkflowStageType } from "./types";
import { WORKFLOW_STAGES, PRIORITY_CONFIG, RISK_BG, RISK_BG_LIGHT, RISK_TEXT } from "./types";

type SortKey = "priority" | "slaRemaining" | "riskScore" | "contractName" | "vendor" | "value" | "dueDate";

interface ApprovalTableProps {
  workflows: WorkflowItem[];
  onSelect: (w: WorkflowItem) => void;
}

function StageBadge({ stage }: { stage: WorkflowStageType }) {
  const s = WORKFLOW_STAGES.find((st) => st.id === stage);
  if (!s) return null;
  return <span className={`text-[9px] font-medium px-1.5 py-0.5 rounded-full ${s.bg} ${s.color}`}>{s.label}</span>;
}

export function ApprovalTable({ workflows, onSelect }: ApprovalTableProps) {
  const [search, setSearch] = useState("");
  const [sortKey, setSortKey] = useState<SortKey>("slaRemaining");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("asc");
  const [page, setPage] = useState(0);
  const [stageFilter, setStageFilter] = useState<string>("all");
  const pageSize = 12;

  const handleSort = (k: SortKey) => {
    if (sortKey === k) setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    else { setSortKey(k); setSortDir(k === "slaRemaining" ? "asc" : "desc"); }
  };

  const filtered = useMemo(() => {
    let list = workflows.filter((w) =>
      (stageFilter === "all" || w.currentStage === stageFilter) &&
      (w.contractName.toLowerCase().includes(search.toLowerCase()) || w.vendor.toLowerCase().includes(search.toLowerCase()))
    );
    list.sort((a, b) => {
      const d = sortDir === "asc" ? 1 : -1;
      if (sortKey === "slaRemaining") return (a.slaRemaining - b.slaRemaining) * d;
      if (sortKey === "riskScore") return (a.riskScore - b.riskScore) * d;
      if (sortKey === "value") return (a.value - b.value) * d;
      if (sortKey === "priority") {
        const p = { critical: 0, high: 1, medium: 2, low: 3 };
        return (p[a.priority] - p[b.priority]) * d;
      }
      if (sortKey === "dueDate") return (new Date(a.dueDate).getTime() - new Date(b.dueDate).getTime()) * d;
      return a[sortKey].localeCompare(b[sortKey]) * d;
    });
    return list;
  }, [workflows, search, sortKey, sortDir, stageFilter]);

  const totalPages = Math.ceil(filtered.length / pageSize);
  const pageData = filtered.slice(page * pageSize, (page + 1) * pageSize);

  const SortHeader = ({ label, k }: { label: string; k: SortKey }) => (
    <th className="text-left py-2.5 px-2.5 text-[10px] font-semibold text-gray-500 uppercase tracking-wider cursor-pointer hover:text-navy-700 select-none" onClick={() => handleSort(k)}>
      <div className="flex items-center gap-1">{label}<ArrowUpDown className={`w-3 h-3 ${sortKey === k ? "text-navy-500" : "text-gray-300"}`} /></div>
    </th>
  );

  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
      <div className="px-4 py-2.5 border-b border-gray-100 flex items-center justify-between">
        <div><h3 className="text-xs font-semibold text-navy-900">Approval Queue</h3><p className="text-[10px] text-gray-500">{filtered.length} workflows</p></div>
        <div className="flex items-center gap-2">
          <select value={stageFilter} onChange={(e) => { setStageFilter(e.target.value); setPage(0); }}
            className="text-[10px] border border-gray-200 rounded-md px-2 py-1.5 text-gray-600 bg-white hover:border-gray-300 focus:border-navy-400 focus:ring-1 focus:ring-navy-400 transition-colors" aria-label="Stage filter">
            <option value="all">All Stages</option>
            {WORKFLOW_STAGES.map((s) => <option key={s.id} value={s.id}>{s.label}</option>)}
          </select>
          <div className="relative w-44">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3 h-3 text-gray-400" />
            <input value={search} onChange={(e) => { setSearch(e.target.value); setPage(0); }} placeholder="Search..." className="w-full text-[11px] border border-gray-200 rounded-lg pl-7 pr-3 py-1.5 focus:border-navy-400 focus:ring-1 focus:ring-navy-400" />
          </div>
        </div>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead className="bg-gray-50 border-b border-gray-100 sticky top-0 z-10">
            <tr>
              <SortHeader label="Contract" k="contractName" />
              <SortHeader label="Vendor" k="vendor" />
              <th className="text-left py-2.5 px-2.5 text-[10px] font-semibold text-gray-500 uppercase">Stage</th>
              <th className="text-left py-2.5 px-2.5 text-[10px] font-semibold text-gray-500 uppercase">Assignee</th>
              <SortHeader label="Priority" k="priority" />
              <SortHeader label="SLA" k="slaRemaining" />
              <SortHeader label="Risk" k="riskScore" />
              <th className="text-left py-2.5 px-2.5 text-[10px] font-semibold text-gray-500 uppercase">AI Rec.</th>
              <th className="text-left py-2.5 px-2.5 text-[10px] font-semibold text-gray-500 uppercase">Last Action</th>
              <SortHeader label="Due" k="dueDate" />
              <th className="py-2.5 px-2.5 w-12" />
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-50">
            {pageData.map((w, i) => {
              const pCfg = PRIORITY_CONFIG[w.priority];
              const slaUrgent = w.slaRemaining < 0;
              return (
                <motion.tr key={w.id} initial={{ opacity: 0, y: 2 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.02 }}
                  className="hover:bg-navy-50/40 transition-colors cursor-pointer" onClick={() => onSelect(w)}>
                  <td className="py-2.5 px-2.5">
                    <span className="font-medium text-gray-800 text-[11px]">{w.contractName}</span>
                    <div className="flex gap-0.5 mt-0.5">{w.escalationLevel > 0 && <span className="text-[8px] px-1 py-0.5 rounded bg-red-50 text-red-600">Escalated L{w.escalationLevel}</span>}</div>
                  </td>
                  <td className="py-2.5 px-2.5 text-gray-600 text-[10px]">{w.vendor}</td>
                  <td className="py-2.5 px-2.5"><StageBadge stage={w.currentStage} /></td>
                  <td className="py-2.5 px-2.5 text-gray-600 text-[10px]">{w.assignedTo}</td>
                  <td className="py-2.5 px-2.5"><span className={`text-[9px] font-medium px-1.5 py-0.5 rounded-full ${pCfg.bg} ${pCfg.color}`}>{w.priority}</span></td>
                  <td className="py-2.5 px-2.5">
                    <span className={`text-[10px] font-medium flex items-center gap-1 ${slaUrgent ? "text-red-600" : w.slaRemaining < 24 ? "text-orange-600" : "text-gray-600"}`}>
                      <Clock className="w-3 h-3" />
                      {slaUrgent ? `${-w.slaRemaining}h overdue` : `${w.slaRemaining}h`}
                    </span>
                  </td>
                  <td className="py-2.5 px-2.5">
                    <span className={`inline-flex items-center gap-1 text-[10px] font-bold px-1.5 py-0.5 rounded-full ${RISK_BG_LIGHT[w.riskLevel]} ${RISK_TEXT[w.riskLevel]}`}>
                      <span className={`w-1.5 h-1.5 rounded-full ${RISK_BG[w.riskLevel]}`} />{w.riskScore}/10
                    </span>
                  </td>
                  <td className="py-2.5 px-2.5 max-w-[120px]">
                    <span className="text-[10px] text-gray-600 line-clamp-1">{w.aiRecommendation}</span>
                    <span className="text-[8px] text-gray-400">{w.aiConfidence}% conf.</span>
                  </td>
                  <td className="py-2.5 px-2.5 text-[10px] text-gray-500">{w.lastActionBy}<br /><span className="text-[8px] text-gray-400">{formatTime(w.lastActionDate)}</span></td>
                  <td className="py-2.5 px-2.5 text-[10px] text-gray-500">{formatDate(w.dueDate)}</td>
                  <td className="py-2.5 px-2.5">
                    <div className="flex items-center gap-1">
                      {w.comments.filter((c) => !c.resolved).length > 0 && <MessageSquare className="w-3 h-3 text-navy-400" />}
                      {w.attachments > 0 && <Paperclip className="w-3 h-3 text-gray-300" />}
                    </div>
                  </td>
                </motion.tr>
              );
            })}
          </tbody>
        </table>
      </div>
      {filtered.length === 0 && <div className="text-center py-12 text-gray-400"><p className="text-xs font-medium">No workflows match your filters</p></div>}
      {filtered.length > 0 && (
        <div className="px-4 py-2 border-t border-gray-100 flex items-center justify-between">
          <span className="text-[10px] text-gray-500">Showing {page * pageSize + 1}–{Math.min((page + 1) * pageSize, filtered.length)} of {filtered.length}</span>
          <div className="flex items-center gap-1">
            <button onClick={() => setPage(Math.max(0, page - 1))} disabled={page === 0} className="p-1 rounded hover:bg-gray-100 disabled:opacity-30"><ChevronLeft className="w-3.5 h-3.5" /></button>
            {Array.from({ length: totalPages }, (_, i) => (
              <button key={i} onClick={() => setPage(i)} className={`w-5 h-5 text-[10px] rounded transition-colors ${i === page ? "bg-navy-700 text-white" : "text-gray-500 hover:bg-gray-100"}`}>{i + 1}</button>
            ))}
            <button onClick={() => setPage(Math.min(totalPages - 1, page + 1))} disabled={page >= totalPages - 1} className="p-1 rounded hover:bg-gray-100 disabled:opacity-30"><ChevronRight className="w-3.5 h-3.5" /></button>
          </div>
        </div>
      )}
    </div>
  );
}

function formatTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const hrs = Math.floor(diff / 3600000);
  if (hrs < 1) return "just now";
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

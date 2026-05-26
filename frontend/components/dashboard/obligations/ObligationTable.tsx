"use client";

import React, { useState, useMemo } from "react";
import { motion } from "framer-motion";
import { Search, ChevronLeft, ChevronRight, ArrowUpDown, FileText, Clock, AlertTriangle, DollarSign, MoreHorizontal } from "lucide-react";
import type { ObligationRecord, ObligationType } from "./types";
import { RISK_BG, RISK_TEXT, RISK_BG_LIGHT, STATUS_CONFIG, OBLIGATION_TYPES } from "./types";

type SortKey = "dueDate" | "riskScore" | "financialImpact" | "name" | "vendor" | "status" | "aiRiskPrediction" | "slaRemaining";

interface ObligationTableProps {
  obligations: ObligationRecord[];
  onSelect: (o: ObligationRecord) => void;
}

function TypeBadge({ type }: { type: ObligationType }) {
  const t = OBLIGATION_TYPES.find((ot) => ot.id === type);
  return <span className="text-[9px] px-1.5 py-0.5 rounded bg-navy-50 text-navy-700 capitalize">{t?.label || type}</span>;
}

export function ObligationTable({ obligations, onSelect }: ObligationTableProps) {
  const [search, setSearch] = useState("");
  const [sortKey, setSortKey] = useState<SortKey>("dueDate");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("asc");
  const [typeFilter, setTypeFilter] = useState("all");
  const [statusFilter, setStatusFilter] = useState("all");
  const [page, setPage] = useState(0);
  const pageSize = 12;

  const handleSort = (k: SortKey) => {
    if (sortKey === k) setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    else { setSortKey(k); setSortDir(k === "dueDate" ? "asc" : "desc"); }
  };

  const filtered = useMemo(() => {
    let list = obligations.filter((o) => {
      if (typeFilter !== "all" && o.type !== typeFilter) return false;
      if (statusFilter !== "all" && o.status !== statusFilter) return false;
      return o.name.toLowerCase().includes(search.toLowerCase()) || o.vendor.toLowerCase().includes(search.toLowerCase());
    });
    list.sort((a, b) => {
      const d = sortDir === "asc" ? 1 : -1;
      if (sortKey === "dueDate") return (new Date(a.dueDate).getTime() - new Date(b.dueDate).getTime()) * d;
      if (sortKey === "riskScore") return (a.riskScore - b.riskScore) * d;
      if (sortKey === "financialImpact") return (a.financialImpact - b.financialImpact) * d;
      if (sortKey === "aiRiskPrediction") return (a.aiRiskPrediction - b.aiRiskPrediction) * d;
      if (sortKey === "slaRemaining") return (a.slaRemaining - b.slaRemaining) * d;
      const p = { pending: 0, in_progress: 1, escalated: 2, overdue: 3, completed: 4, waived: 5 };
      if (sortKey === "status") return (p[a.status] - p[b.status]) * d;
      return a[sortKey].localeCompare(b[sortKey]) * d;
    });
    return list;
  }, [obligations, search, sortKey, sortDir, typeFilter, statusFilter]);

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
        <div><h3 className="text-xs font-semibold text-navy-900">Obligation Registry</h3><p className="text-[10px] text-gray-500">{filtered.length} obligations</p></div>
        <div className="flex items-center gap-2">
          <select value={typeFilter} onChange={(e) => { setTypeFilter(e.target.value); setPage(0); }} className="text-[10px] border border-gray-200 rounded-md px-2 py-1.5 text-gray-600 bg-white" aria-label="Type">
            <option value="all">All Types</option>
            {OBLIGATION_TYPES.map((t) => <option key={t.id} value={t.id}>{t.label}</option>)}
          </select>
          <select value={statusFilter} onChange={(e) => { setStatusFilter(e.target.value); setPage(0); }} className="text-[10px] border border-gray-200 rounded-md px-2 py-1.5 text-gray-600 bg-white" aria-label="Status">
            <option value="all">All Status</option>
            <option value="pending">Pending</option><option value="in_progress">In Progress</option>
            <option value="overdue">Overdue</option><option value="escalated">Escalated</option><option value="completed">Completed</option>
          </select>
          <div className="relative w-44"><Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3 h-3 text-gray-400" />
            <input value={search} onChange={(e) => { setSearch(e.target.value); setPage(0); }} placeholder="Search..." className="w-full text-[11px] border border-gray-200 rounded-lg pl-7 pr-3 py-1.5 focus:border-navy-400 focus:ring-1 focus:ring-navy-400" /></div>
        </div>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead className="bg-gray-50 border-b border-gray-100 sticky top-0 z-10">
            <tr>
              <SortHeader label="Obligation" k="name" />
              <SortHeader label="Vendor" k="vendor" />
              <th className="text-left py-2.5 px-2.5 text-[10px] font-semibold text-gray-500 uppercase">Type</th>
              <th className="text-left py-2.5 px-2.5 text-[10px] font-semibold text-gray-500 uppercase">Owner</th>
              <SortHeader label="Due Date" k="dueDate" />
              <SortHeader label="Status" k="status" />
              <SortHeader label="Risk" k="riskScore" />
              <th className="text-left py-2.5 px-2.5 text-[10px] font-semibold text-gray-500 uppercase">SLA</th>
              <SortHeader label="Financial" k="financialImpact" />
              <SortHeader label="AI Risk" k="aiRiskPrediction" />
              <th className="py-2.5 px-2.5 w-8" />
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-50">
            {pageData.map((o, i) => {
              const sc = STATUS_CONFIG[o.status];
              return (
                <motion.tr key={o.id} initial={{ opacity: 0, y: 2 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.02 }}
                  className="hover:bg-navy-50/40 transition-colors cursor-pointer" onClick={() => onSelect(o)}>
                  <td className="py-2.5 px-2.5">
                    <span className="font-medium text-gray-800 text-[11px]">{o.name}</span>
                    <div className="text-[9px] text-gray-400 mt-0.5">{o.contractName}</div>
                  </td>
                  <td className="py-2.5 px-2.5 text-gray-600 text-[10px]">{o.vendor}</td>
                  <td className="py-2.5 px-2.5"><TypeBadge type={o.type} /></td>
                  <td className="py-2.5 px-2.5 text-gray-600 text-[10px]">{o.owner}</td>
                  <td className="py-2.5 px-2.5">
                    <span className={`tabular-nums text-[10px] ${o.status === "overdue" || o.status === "escalated" ? "text-red-600 font-medium" : "text-gray-600"}`}>{o.dueDate}</span>
                  </td>
                  <td className="py-2.5 px-2.5"><span className={`text-[9px] font-medium px-1.5 py-0.5 rounded-full ${sc.bg} ${sc.color}`}>{sc.label}</span></td>
                  <td className="py-2.5 px-2.5">
                    <span className={`inline-flex items-center gap-1 text-[10px] font-bold px-1.5 py-0.5 rounded-full ${RISK_BG_LIGHT[o.riskLevel]} ${RISK_TEXT[o.riskLevel]}`}>
                      <span className={`w-1.5 h-1.5 rounded-full ${RISK_BG[o.riskLevel]}`} />{o.riskScore}/10
                    </span>
                  </td>
                  <td className="py-2.5 px-2.5">
                    {o.type === "sla" ? (
                      <span className={`text-[10px] font-medium ${o.slaStatus === "breached" ? "text-red-600" : o.slaStatus === "at_risk" ? "text-orange-600" : "text-green-600"}`}>
                        {o.slaStatus === "breached" ? `${-o.slaRemaining}h breached` : o.slaStatus === "at_risk" ? `${o.slaRemaining}h left` : "On track"}
                      </span>
                    ) : <span className="text-gray-300">—</span>}
                  </td>
                  <td className="py-2.5 px-2.5">
                    <span className="font-medium tabular-nums text-[11px]">${o.financialImpact}M</span>
                  </td>
                  <td className="py-2.5 px-2.5">
                    <div className="flex items-center gap-1.5">
                      <div className="w-10 h-1.5 bg-gray-200 rounded-full overflow-hidden">
                        <div className={`h-full rounded-full ${o.aiRiskPrediction >= 70 ? "bg-red-500" : o.aiRiskPrediction >= 40 ? "bg-yellow-500" : "bg-green-500"}`}
                          style={{ width: `${o.aiRiskPrediction}%` }} />
                      </div>
                      <span className="text-[9px] text-gray-500 tabular-nums">{o.aiRiskPrediction}%</span>
                    </div>
                  </td>
                  <td className="py-2.5 px-2.5"><MoreHorizontal className="w-3 h-3 text-gray-300 opacity-0 group-hover:opacity-100" /></td>
                </motion.tr>
              );
            })}
          </tbody>
        </table>
      </div>
      {filtered.length === 0 && <div className="text-center py-12 text-gray-400"><FileText className="w-8 h-8 mx-auto mb-2" /><p className="text-xs font-medium">No obligations match your filters</p></div>}
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

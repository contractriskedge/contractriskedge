"use client";

import React, { useState, useMemo } from "react";
import { motion } from "framer-motion";
import { Search, ChevronLeft, ChevronRight, ArrowUpDown, FileText, Heart, Star, MoreHorizontal, Brain } from "lucide-react";
import type { ClauseRecord, ClauseStatus } from "./types";
import { RISK_BG, RISK_TEXT, RISK_BG_LIGHT } from "./types";

type SortKey = "riskScore" | "usageFrequency" | "name" | "benchmarkPercentile" | "negotiationStrength" | "aiConfidence" | "lastUpdated";

interface ClauseTableProps {
  clauses: ClauseRecord[];
  onSelect: (c: ClauseRecord) => void;
  onToggleFavorite: (id: string) => void;
}

const statusConfig: Record<ClauseStatus, { color: string; bg: string; label: string }> = {
  approved: { color: "text-green-700", bg: "bg-green-50", label: "Approved" },
  pending_review: { color: "text-yellow-700", bg: "bg-yellow-50", label: "Pending Review" },
  deprecated: { color: "text-red-700", bg: "bg-red-50", label: "Deprecated" },
  draft: { color: "text-gray-600", bg: "bg-gray-100", label: "Draft" },
};

export function ClauseTable({ clauses, onSelect, onToggleFavorite }: ClauseTableProps) {
  const [search, setSearch] = useState("");
  const [sortKey, setSortKey] = useState<SortKey>("usageFrequency");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");
  const [page, setPage] = useState(0);
  const pageSize = 12;

  const handleSort = (k: SortKey) => {
    if (sortKey === k) setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    else { setSortKey(k); setSortDir("desc"); }
  };

  const filtered = useMemo(() => {
    let list = clauses.filter((c) =>
      c.name.toLowerCase().includes(search.toLowerCase()) ||
      c.category.toLowerCase().includes(search.toLowerCase()) ||
      c.tags.some((t) => t.toLowerCase().includes(search.toLowerCase()))
    );
    list.sort((a, b) => {
      const d = sortDir === "asc" ? 1 : -1;
      if (sortKey === "riskScore") return (a.riskScore - b.riskScore) * d;
      if (sortKey === "usageFrequency") return (a.usageFrequency - b.usageFrequency) * d;
      if (sortKey === "benchmarkPercentile") return (a.benchmarkPercentile - b.benchmarkPercentile) * d;
      if (sortKey === "negotiationStrength") return (a.negotiationStrength - b.negotiationStrength) * d;
      if (sortKey === "aiConfidence") return (a.aiConfidence - b.aiConfidence) * d;
      if (sortKey === "lastUpdated") return new Date(b.lastUpdated).getTime() - new Date(a.lastUpdated).getTime() * d;
      return a.name.localeCompare(b.name) * d;
    });
    return list;
  }, [clauses, search, sortKey, sortDir]);

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
        <div><h3 className="text-xs font-semibold text-navy-900">Clause Repository</h3><p className="text-[10px] text-gray-500">{filtered.length} clauses</p></div>
        <div className="relative w-52"><Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3 h-3 text-gray-400" />
          <input value={search} onChange={(e) => { setSearch(e.target.value); setPage(0); }} placeholder="Search clauses..." className="w-full text-[11px] border border-gray-200 rounded-lg pl-7 pr-3 py-1.5 focus:border-navy-400 focus:ring-1 focus:ring-navy-400" /></div>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead className="bg-gray-50 border-b border-gray-100 sticky top-0 z-10">
            <tr>
              <th className="py-2.5 px-2.5 w-6" />
              <SortHeader label="Clause Name" k="name" />
              <th className="text-left py-2.5 px-2.5 text-[10px] font-semibold text-gray-500 uppercase">Category</th>
              <SortHeader label="Risk" k="riskScore" />
              <th className="text-left py-2.5 px-2.5 text-[10px] font-semibold text-gray-500 uppercase">Jurisdiction</th>
              <SortHeader label="Benchmark" k="benchmarkPercentile" />
              <SortHeader label="Usage" k="usageFrequency" />
              <th className="text-left py-2.5 px-2.5 text-[10px] font-semibold text-gray-500 uppercase">Status</th>
              <SortHeader label="AI Conf." k="aiConfidence" />
              <SortHeader label="Neg. Strength" k="negotiationStrength" />
              <SortHeader label="Updated" k="lastUpdated" />
              <th className="py-2.5 px-2.5 w-8" />
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-50">
            {pageData.map((c, i) => {
              const sc = statusConfig[c.approvalStatus];
              return (
                <motion.tr key={c.id} initial={{ opacity: 0, y: 2 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.02 }}
                  className="hover:bg-navy-50/40 transition-colors cursor-pointer" onClick={() => onSelect(c)}>
                  <td className="py-2.5 px-2.5" onClick={(e) => { e.stopPropagation(); onToggleFavorite(c.id); }}>
                    <Heart className={`w-3 h-3 ${c.isFavorite ? "text-red-400 fill-red-400" : "text-gray-300 hover:text-red-300"} transition-colors`} />
                  </td>
                  <td className="py-2.5 px-2.5">
                    <span className="font-medium text-gray-800 text-[11px]">{c.name}</span>
                    <div className="flex gap-0.5 mt-0.5">{c.tags.slice(0, 2).map((t) => (
                      <span key={t} className="text-[8px] px-1 py-0.5 rounded bg-gray-100 text-gray-500">{t}</span>
                    ))}</div>
                  </td>
                  <td className="py-2.5 px-2.5"><span className="text-[10px] px-1.5 py-0.5 rounded bg-navy-50 text-navy-700 capitalize">{c.category.replace(/_/g, " ")}</span></td>
                  <td className="py-2.5 px-2.5">
                    <span className={`inline-flex items-center gap-1 text-[10px] font-bold px-1.5 py-0.5 rounded-full ${RISK_BG_LIGHT[c.riskLevel]} ${RISK_TEXT[c.riskLevel]}`}>
                      <span className={`w-1.5 h-1.5 rounded-full ${RISK_BG[c.riskLevel]}`} />{c.riskScore}/10
                    </span>
                  </td>
                  <td className="py-2.5 px-2.5 text-gray-600 text-[10px]">{c.jurisdiction}</td>
                  <td className="py-2.5 px-2.5">
                    <div className="flex items-center gap-1.5">
                      <div className="w-10 h-1.5 bg-gray-200 rounded-full overflow-hidden">
                        <div className={`h-full rounded-full ${c.benchmarkPercentile >= 75 ? "bg-red-500" : c.benchmarkPercentile >= 50 ? "bg-yellow-500" : "bg-green-500"}`}
                          style={{ width: `${c.benchmarkPercentile}%` }} />
                      </div>
                      <span className="text-[10px] text-gray-500 tabular-nums">{c.benchmarkPercentile}th</span>
                    </div>
                  </td>
                  <td className="py-2.5 px-2.5 text-gray-600 tabular-nums">{c.usageFrequency}</td>
                  <td className="py-2.5 px-2.5"><span className={`text-[9px] font-medium px-1.5 py-0.5 rounded-full ${sc.bg} ${sc.color}`}>{sc.label}</span></td>
                  <td className="py-2.5 px-2.5">
                    <div className="flex items-center gap-1"><div className="w-8 h-1.5 bg-gray-200 rounded-full overflow-hidden"><div className={`h-full rounded-full ${c.aiConfidence >= 85 ? "bg-green-500" : "bg-yellow-500"}`} style={{ width: `${c.aiConfidence}%` }} /></div><span className="text-[9px] text-gray-500">{c.aiConfidence}%</span></div>
                  </td>
                  <td className="py-2.5 px-2.5">
                    <span className={`text-[10px] font-medium ${c.negotiationStrength >= 80 ? "text-green-600" : c.negotiationStrength >= 60 ? "text-yellow-600" : "text-red-600"}`}>{c.negotiationStrength}%</span>
                  </td>
                  <td className="py-2.5 px-2.5 text-gray-400 text-[10px]">{c.lastUpdated}</td>
                  <td className="py-2.5 px-2.5"><MoreHorizontal className="w-3 h-3 text-gray-300 opacity-0 group-hover:opacity-100" /></td>
                </motion.tr>
              );
            })}
          </tbody>
        </table>
      </div>
      {filtered.length === 0 && <div className="text-center py-12 text-gray-400"><FileText className="w-8 h-8 mx-auto mb-2" /><p className="text-xs font-medium">No clauses match your filters</p></div>}
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

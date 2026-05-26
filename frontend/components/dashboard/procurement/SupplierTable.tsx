"use client";

import React, { useState, useMemo } from "react";
import { motion } from "framer-motion";
import { ChevronLeft, ChevronRight, Search, ArrowUpDown, MoreHorizontal, FileText, AlertTriangle, Building2, Globe, Shield } from "lucide-react";
import type { SupplierRecord, RiskLevel, ComplianceStatus } from "./types";
import { RISK_BG, RISK_TEXT, RISK_BG_LIGHT, COMPLIANCE_CONFIG } from "./types";

function RiskBadge({ score }: { score: number }) {
  const l: RiskLevel = score >= 8 ? "critical" : score >= 6 ? "high" : score >= 4 ? "medium" : "low";
  return <span className={`inline-flex items-center gap-1 text-[10px] font-bold px-1.5 py-0.5 rounded-full ${RISK_BG_LIGHT[l]} ${RISK_TEXT[l]}`}><span className={`w-1.5 h-1.5 rounded-full ${RISK_BG[l]}`} />{score}/10</span>;
}

function FinancialBadge({ status }: { status: string }) {
  const map: Record<string, { bg: string; color: string; label: string }> = {
    strong: { bg: "bg-green-50", color: "text-green-700", label: "Strong" },
    stable: { bg: "bg-blue-50", color: "text-blue-700", label: "Stable" },
    weak: { bg: "bg-yellow-50", color: "text-yellow-700", label: "Weak" },
    distressed: { bg: "bg-red-50", color: "text-red-700", label: "Distressed" },
  };
  const c = map[status] || map.stable;
  return <span className={`text-[9px] font-medium px-1.5 py-0.5 rounded-full ${c.bg} ${c.color}`}>{c.label}</span>;
}

function ComplianceBadge({ status }: { status: ComplianceStatus }) {
  const c = COMPLIANCE_CONFIG[status];
  return <span className={`text-[9px] font-medium px-1.5 py-0.5 rounded-full ${c.bg} ${c.color}`}>{c.label}</span>;
}

interface SupplierTableProps {
  suppliers: SupplierRecord[];
  onSelect: (s: SupplierRecord) => void;
}

type SortKey = "riskScore" | "totalSpend" | "name" | "slaPerformance" | "aiConfidence" | "activeContracts";

export function SupplierTable({ suppliers, onSelect }: SupplierTableProps) {
  const [search, setSearch] = useState("");
  const [sortKey, setSortKey] = useState<SortKey>("riskScore");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");
  const [page, setPage] = useState(0);
  const pageSize = 12;

  const handleSort = (k: SortKey) => {
    if (sortKey === k) setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    else { setSortKey(k); setSortDir("desc"); }
  };

  const filtered = useMemo(() => {
    const list = suppliers.filter((s) =>
      s.name.toLowerCase().includes(search.toLowerCase()) ||
      s.category.toLowerCase().includes(search.toLowerCase()) ||
      s.country.toLowerCase().includes(search.toLowerCase())
    );
    list.sort((a, b) => {
      const d = sortDir === "asc" ? 1 : -1;
      if (sortKey === "riskScore") return (a.riskScore - b.riskScore) * d;
      if (sortKey === "totalSpend") return (a.totalSpend - b.totalSpend) * d;
      if (sortKey === "slaPerformance") return (a.slaPerformance - b.slaPerformance) * d;
      if (sortKey === "aiConfidence") return (a.aiConfidence - b.aiConfidence) * d;
      if (sortKey === "activeContracts") return (a.activeContracts - b.activeContracts) * d;
      return a.name.localeCompare(b.name) * d;
    });
    return list;
  }, [suppliers, search, sortKey, sortDir]);

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
        <div><h3 className="text-xs font-semibold text-navy-900">Supplier Directory</h3><p className="text-[10px] text-gray-500">{filtered.length} suppliers</p></div>
        <div className="relative w-52">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-gray-400" />
          <input value={search} onChange={(e) => { setSearch(e.target.value); setPage(0); }} placeholder="Search suppliers..." className="w-full text-xs border border-gray-200 rounded-lg pl-8 pr-3 py-1.5 focus:border-navy-400 focus:ring-1 focus:ring-navy-400" />
        </div>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead className="bg-gray-50 border-b border-gray-100 sticky top-0 z-10">
            <tr>
              <th className="text-left py-2.5 px-2.5 text-[10px] font-semibold text-gray-500 uppercase tracking-wider">Supplier</th>
              <SortHeader label="Risk" k="riskScore" />
              <SortHeader label="Spend" k="totalSpend" />
              <SortHeader label="Contracts" k="activeContracts" />
              <th className="text-left py-2.5 px-2.5 text-[10px] font-semibold text-gray-500 uppercase tracking-wider">Category</th>
              <SortHeader label="SLA%" k="slaPerformance" />
              <th className="text-left py-2.5 px-2.5 text-[10px] font-semibold text-gray-500 uppercase tracking-wider">Compliance</th>
              <th className="text-left py-2.5 px-2.5 text-[10px] font-semibold text-gray-500 uppercase tracking-wider">Top Risk</th>
              <th className="text-left py-2.5 px-2.5 text-[10px] font-semibold text-gray-500 uppercase tracking-wider">Owner</th>
              <th className="text-left py-2.5 px-2.5 text-[10px] font-semibold text-gray-500 uppercase tracking-wider">Country</th>
              <th className="text-left py-2.5 px-2.5 text-[10px] font-semibold text-gray-500 uppercase tracking-wider">Financial</th>
              <SortHeader label="AI" k="aiConfidence" />
              <th className="py-2.5 px-2.5 w-8" />
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-50">
            {pageData.map((s, i) => (
              <motion.tr key={s.id} initial={{ opacity: 0, y: 2 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.02 }}
                className="hover:bg-navy-50/40 transition-colors cursor-pointer" onClick={() => onSelect(s)}>
                <td className="py-2.5 px-2.5">
                  <div className="flex items-center gap-2">
                    <Building2 className="w-3.5 h-3.5 text-gray-300 flex-shrink-0" />
                    <div><span className="font-medium text-gray-800 text-[11px]">{s.name}</span><div className="flex gap-0.5 mt-0.5">{s.aiFlags.slice(0, 1).map((f) => <span key={f} className="text-[8px] px-1 py-0.5 rounded bg-red-50 text-red-600">{f}</span>)}</div></div>
                  </div>
                </td>
                <td className="py-2.5 px-2.5"><RiskBadge score={s.riskScore} /></td>
                <td className="py-2.5 px-2.5"><span className="font-medium tabular-nums text-[11px]">${s.totalSpend}M</span></td>
                <td className="py-2.5 px-2.5 text-gray-600">{s.activeContracts}</td>
                <td className="py-2.5 px-2.5"><span className="text-[10px] px-1.5 py-0.5 rounded bg-gray-100 text-gray-600">{s.category}</span></td>
                <td className="py-2.5 px-2.5">
                  <div className="flex items-center gap-1.5">
                    <div className="w-10 h-1.5 bg-gray-200 rounded-full overflow-hidden">
                      <div className={`h-full rounded-full ${s.slaPerformance >= 95 ? "bg-green-500" : s.slaPerformance >= 85 ? "bg-yellow-500" : "bg-red-500"}`} style={{ width: `${s.slaPerformance}%` }} />
                    </div>
                    <span className="text-[10px] text-gray-500 tabular-nums">{s.slaPerformance}%</span>
                  </div>
                </td>
                <td className="py-2.5 px-2.5"><ComplianceBadge status={s.complianceStatus} /></td>
                <td className="py-2.5 px-2.5"><span className="text-[10px] px-1.5 py-0.5 rounded bg-orange-50 text-orange-700 font-medium">{s.topRiskArea}</span></td>
                <td className="py-2.5 px-2.5 text-gray-600 text-[10px]">{s.procurementOwner}</td>
                <td className="py-2.5 px-2.5"><span className="flex items-center gap-1 text-gray-500 text-[10px]"><Globe className="w-3 h-3" />{s.country}</span></td>
                <td className="py-2.5 px-2.5"><FinancialBadge status={s.financialStability} /></td>
                <td className="py-2.5 px-2.5">
                  <div className="flex items-center gap-1"><div className="w-8 h-1.5 bg-gray-200 rounded-full overflow-hidden"><div className={`h-full rounded-full ${s.aiConfidence >= 85 ? "bg-green-500" : "bg-yellow-500"}`} style={{ width: `${s.aiConfidence}%` }} /></div><span className="text-[9px] text-gray-500">{s.aiConfidence}%</span></div>
                </td>
                <td className="py-2.5 px-2.5"><MoreHorizontal className="w-3.5 h-3.5 text-gray-300 opacity-0 group-hover:opacity-100 transition-opacity" /></td>
              </motion.tr>
            ))}
          </tbody>
        </table>
      </div>
      {filtered.length === 0 && <div className="text-center py-12 text-gray-400"><Building2 className="w-8 h-8 mx-auto mb-2" /><p className="text-xs font-medium">No suppliers match your filters</p></div>}
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

"use client";

import React, { useState, useMemo } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  ChevronDown, ChevronUp, ChevronLeft, ChevronRight, Search,
  ArrowUpDown, Eye, FileText, ExternalLink, AlertTriangle,
} from "lucide-react";
import type { PortfolioContract, RiskLevel } from "./types";
import { RISK_BG_COLORS, RISK_TEXT_COLORS, RISK_BG_LIGHT } from "./types";

// ── Risk Score Badge ────────────────────────────────────────────────────────

function RiskScoreBadge({ score }: { score: number }) {
  const level: RiskLevel = score >= 8 ? "critical" : score >= 6 ? "high" : score >= 4 ? "medium" : "low";
  return (
    <span className={`inline-flex items-center gap-1 text-[10px] font-bold px-1.5 py-0.5 rounded-full ${RISK_BG_LIGHT[level]} ${RISK_TEXT_COLORS[level]}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${RISK_BG_COLORS[level]}`} />
      {score}/10
    </span>
  );
}

// ── Status Badge ────────────────────────────────────────────────────────────

function StatusBadge({ status }: { status: string }) {
  const cfg: Record<string, { bg: string; color: string; label: string }> = {
    active: { bg: "bg-green-100", color: "text-green-700", label: "Active" },
    expiring_soon: { bg: "bg-yellow-100", color: "text-yellow-700", label: "Expiring Soon" },
    expired: { bg: "bg-red-100", color: "text-red-700", label: "Expired" },
    draft: { bg: "bg-gray-100", color: "text-gray-600", label: "Draft" },
    pending_review: { bg: "bg-blue-100", color: "text-blue-700", label: "Pending Review" },
  };
  const c = cfg[status] || cfg.draft;
  return (
    <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded-full ${c.bg} ${c.color}`}>
      {c.label}
    </span>
  );
}

// ── Quick Preview Drawer ────────────────────────────────────────────────────

function ContractPreviewDrawer({ contract, onClose }: { contract: PortfolioContract; onClose: () => void }) {
  return (
    <motion.div
      initial={{ opacity: 0, x: 300 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: 300 }}
      className="fixed right-0 top-0 bottom-0 w-96 bg-white border-l border-gray-200 shadow-xl z-50 overflow-y-auto"
    >
      <div className="p-5 space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold text-navy-900">Contract Preview</h3>
          <button onClick={onClose} className="p-1 rounded hover:bg-gray-100 text-gray-400">
            <ChevronDown className="w-4 h-4 rotate-90" />
          </button>
        </div>

        <div className="space-y-3">
          <div>
            <p className="text-xs font-semibold text-navy-900">{contract.name}</p>
            <p className="text-[11px] text-gray-500">{contract.id}</p>
          </div>

          <div className="grid grid-cols-2 gap-3 p-3 bg-gray-50 rounded-lg">
            <div>
              <p className="text-[10px] text-gray-500">Vendor</p>
              <p className="text-xs font-medium">{contract.vendor}</p>
            </div>
            <div>
              <p className="text-[10px] text-gray-500">Risk Score</p>
              <RiskScoreBadge score={contract.riskScore} />
            </div>
            <div>
              <p className="text-[10px] text-gray-500">Exposure</p>
              <p className="text-xs font-medium">${contract.financialExposure}M</p>
            </div>
            <div>
              <p className="text-[10px] text-gray-500">Expiry</p>
              <p className="text-xs font-medium">{contract.expiryDate}</p>
            </div>
            <div>
              <p className="text-[10px] text-gray-500">Owner</p>
              <p className="text-xs font-medium">{contract.owner}</p>
            </div>
            <div>
              <p className="text-[10px] text-gray-500">AI Confidence</p>
              <p className="text-xs font-medium">{contract.aiConfidence}%</p>
            </div>
          </div>

          <div>
            <p className="text-[10px] font-semibold text-gray-500 uppercase mb-1">Top Risk</p>
            <div className="flex items-center gap-1.5 text-xs text-red-700 bg-red-50 px-2.5 py-1.5 rounded-lg">
              <AlertTriangle className="w-3 h-3" />
              {contract.topRisk}
            </div>
          </div>

          <div>
            <p className="text-[10px] font-semibold text-gray-500 uppercase mb-1">Clause Categories</p>
            <div className="flex gap-1 flex-wrap">
              {contract.clauseCategories.map((cat) => (
                <span key={cat} className="text-[10px] px-1.5 py-0.5 rounded bg-navy-50 text-navy-700">
                  {cat}
                </span>
              ))}
            </div>
          </div>

          <div className="flex gap-2 pt-2">
            <button className="flex-1 text-xs font-medium px-3 py-1.5 rounded-md bg-navy-700 text-white hover:bg-navy-800 transition-colors">
              <ExternalLink className="w-3 h-3 inline mr-1" />
              Open Contract
            </button>
            <button className="flex-1 text-xs font-medium px-3 py-1.5 rounded-md bg-white border border-gray-200 text-gray-700 hover:bg-gray-50 transition-colors">
              View Risks
            </button>
          </div>
        </div>
      </div>
    </motion.div>
  );
}

// ── Contracts Table ─────────────────────────────────────────────────────────

interface ContractsTableProps {
  contracts: PortfolioContract[];
}

type SortKey = "riskScore" | "financialExposure" | "expiryDate" | "name" | "vendor" | "aiConfidence";

export function ContractsTable({ contracts }: ContractsTableProps) {
  const [search, setSearch] = useState("");
  const [sortKey, setSortKey] = useState<SortKey>("riskScore");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");
  const [page, setPage] = useState(0);
  const [previewContract, setPreviewContract] = useState<PortfolioContract | null>(null);
  const pageSize = 10;

  const handleSort = (key: SortKey) => {
    if (sortKey === key) setSortDir(sortDir === "asc" ? "desc" : "asc");
    else { setSortKey(key); setSortDir("desc"); }
  };

  const filtered = useMemo(() => {
    const list = contracts.filter((c) =>
      c.name.toLowerCase().includes(search.toLowerCase()) ||
      c.vendor.toLowerCase().includes(search.toLowerCase()) ||
      c.id.toLowerCase().includes(search.toLowerCase())
    );
    list.sort((a, b) => {
      const dir = sortDir === "asc" ? 1 : -1;
      if (sortKey === "riskScore") return (a.riskScore - b.riskScore) * dir;
      if (sortKey === "financialExposure") return (a.financialExposure - b.financialExposure) * dir;
      if (sortKey === "aiConfidence") return (a.aiConfidence - b.aiConfidence) * dir;
      if (sortKey === "expiryDate") return (new Date(a.expiryDate).getTime() - new Date(b.expiryDate).getTime()) * dir;
      return a[sortKey].localeCompare(b[sortKey]) * dir;
    });
    return list;
  }, [contracts, search, sortKey, sortDir]);

  const totalPages = Math.ceil(filtered.length / pageSize);
  const pageContracts = filtered.slice(page * pageSize, (page + 1) * pageSize);

  const SortHeader = ({ label, k }: { label: string; k: SortKey }) => (
    <th
      className="text-left py-3 px-3 text-[10px] font-semibold text-gray-500 uppercase tracking-wider cursor-pointer hover:text-navy-700 select-none"
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
      {/* Header + Search */}
      <div className="px-5 py-4 border-b border-gray-100 flex items-center justify-between">
        <div>
          <h3 className="text-sm font-semibold text-navy-900">Highest Risk Contracts</h3>
          <p className="text-[11px] text-gray-500 mt-0.5">{filtered.length} contracts • Sorted by risk score</p>
        </div>
        <div className="relative w-56">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-gray-400" />
          <input
            value={search}
            onChange={(e) => { setSearch(e.target.value); setPage(0); }}
            placeholder="Search contracts..."
            className="w-full text-xs border border-gray-200 rounded-lg pl-8 pr-3 py-1.5 focus:border-navy-400 focus:ring-1 focus:ring-navy-400"
          />
        </div>
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead className="bg-gray-50 border-b border-gray-100">
            <tr>
              <SortHeader label="Contract Name" k="name" />
              <SortHeader label="Vendor" k="vendor" />
              <SortHeader label="Risk Score" k="riskScore" />
              <SortHeader label="Exposure" k="financialExposure" />
              <SortHeader label="Expiry Date" k="expiryDate" />
              <th className="text-left py-3 px-3 text-[10px] font-semibold text-gray-500 uppercase tracking-wider">Top Risk</th>
              <SortHeader label="AI Conf." k="aiConfidence" />
              <th className="text-left py-3 px-3 text-[10px] font-semibold text-gray-500 uppercase tracking-wider">Owner</th>
              <th className="text-left py-3 px-3 text-[10px] font-semibold text-gray-500 uppercase tracking-wider">Status</th>
              <th className="py-3 px-3 w-10" />
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-50">
            {pageContracts.map((contract, i) => (
              <motion.tr
                key={contract.id}
                initial={{ opacity: 0, y: 4 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.03 }}
                className="hover:bg-navy-50/40 transition-colors cursor-pointer group"
                onClick={() => setPreviewContract(contract)}
              >
                <td className="py-3 px-3">
                  <div className="flex items-center gap-2">
                    <FileText className="w-3.5 h-3.5 text-gray-300 flex-shrink-0" />
                    <span className="font-medium text-gray-800 truncate max-w-[180px]">{contract.name}</span>
                  </div>
                </td>
                <td className="py-3 px-3 text-gray-600">{contract.vendor}</td>
                <td className="py-3 px-3">
                  <RiskScoreBadge score={contract.riskScore} />
                </td>
                <td className="py-3 px-3">
                  <span className="font-medium tabular-nums">${contract.financialExposure}M</span>
                </td>
                <td className="py-3 px-3">
                  <span className={`tabular-nums ${contract.status === "expiring_soon" ? "text-orange-600 font-medium" : "text-gray-600"}`}>
                    {contract.expiryDate}
                  </span>
                </td>
                <td className="py-3 px-3">
                  <span className="text-[10px] px-1.5 py-0.5 rounded bg-red-50 text-red-700 font-medium">
                    {contract.topRisk}
                  </span>
                </td>
                <td className="py-3 px-3">
                  <div className="flex items-center gap-1.5">
                    <div className="w-12 h-1.5 bg-gray-200 rounded-full overflow-hidden">
                      <div
                        className={`h-full rounded-full ${contract.aiConfidence >= 85 ? "bg-green-500" : contract.aiConfidence >= 70 ? "bg-yellow-500" : "bg-red-500"}`}
                        style={{ width: `${contract.aiConfidence}%` }}
                      />
                    </div>
                    <span className="text-[10px] text-gray-500 tabular-nums">{contract.aiConfidence}%</span>
                  </div>
                </td>
                <td className="py-3 px-3 text-gray-600">{contract.owner}</td>
                <td className="py-3 px-3"><StatusBadge status={contract.status} /></td>
                <td className="py-3 px-3">
                  <Eye className="w-3.5 h-3.5 text-gray-300 opacity-0 group-hover:opacity-100 transition-opacity" />
                </td>
              </motion.tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      <div className="px-5 py-3 border-t border-gray-100 flex items-center justify-between">
        <span className="text-[11px] text-gray-500">
          Showing {page * pageSize + 1}–{Math.min((page + 1) * pageSize, filtered.length)} of {filtered.length}
        </span>
        <div className="flex items-center gap-1">
          <button
            onClick={() => setPage(Math.max(0, page - 1))}
            disabled={page === 0}
            className="p-1 rounded hover:bg-gray-100 disabled:opacity-30 transition-colors"
          >
            <ChevronLeft className="w-4 h-4" />
          </button>
          {Array.from({ length: totalPages }, (_, i) => (
            <button
              key={i}
              onClick={() => setPage(i)}
              className={`w-6 h-6 text-[11px] rounded transition-colors ${
                i === page ? "bg-navy-700 text-white" : "text-gray-500 hover:bg-gray-100"
              }`}
            >
              {i + 1}
            </button>
          ))}
          <button
            onClick={() => setPage(Math.min(totalPages - 1, page + 1))}
            disabled={page >= totalPages - 1}
            className="p-1 rounded hover:bg-gray-100 disabled:opacity-30 transition-colors"
          >
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Preview Drawer */}
      <AnimatePresence>
        {previewContract && (
          <>
            <div className="fixed inset-0 bg-black/20 z-40" onClick={() => setPreviewContract(null)} />
            <ContractPreviewDrawer
              contract={previewContract}
              onClose={() => setPreviewContract(null)}
            />
          </>
        )}
      </AnimatePresence>
    </div>
  );
}

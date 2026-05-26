"use client";

import React, { useState } from "react";
import { motion } from "framer-motion";
import { Handshake, TrendingUp, ChevronRight, Lightbulb, FileEdit, ArrowUpCircle } from "lucide-react";
import type { NegotiationIntel, VendorBenchmark } from "./types";

// ── Negotiation Intel Cards ─────────────────────────────────────────────────

export function NegotiationIntelPanel({ data }: { data: NegotiationIntel[] }) {
  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2"><Handshake className="w-4.5 h-4.5 text-navy-700" /><h2 className="text-sm font-semibold text-navy-900">Negotiation Intelligence</h2></div>
      <div className="space-y-2">
        {data.map((item, i) => (
          <NegotiationCard key={item.clauseType} item={item} index={i} />
        ))}
      </div>
    </div>
  );
}

function NegotiationCard({ item, index }: { item: NegotiationIntel; index: number }) {
  const [expanded, setExpanded] = useState(false);
  return (
    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: index * 0.05 }}
      className="bg-white border border-gray-200 rounded-lg shadow-sm hover:shadow-md transition-all">
      <button onClick={() => setExpanded(!expanded)} className="w-full text-left p-3 flex items-start gap-2.5">
        <div className="w-8 h-8 rounded-full bg-navy-50 flex items-center justify-center flex-shrink-0 mt-0.5">
          <Handshake className="w-4 h-4 text-navy-600" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between mb-0.5">
            <h4 className="text-xs font-semibold text-navy-900">{item.clauseType}</h4>
            <div className="flex items-center gap-2">
              <span className="text-[10px] font-medium text-navy-600 bg-navy-50 px-1.5 py-0.5 rounded">Leverage: {item.leverageScore}%</span>
              <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded ${item.vendorFavorability >= 80 ? "bg-red-50 text-red-700" : item.vendorFavorability >= 60 ? "bg-orange-50 text-orange-700" : "bg-green-50 text-green-700"}`}>
                {item.vendorFavorability}% vendor-favorable
              </span>
            </div>
          </div>
          <p className="text-[10px] text-gray-500">{item.marketPosition}</p>
          {expanded && (
            <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }} className="mt-2 space-y-2 overflow-hidden">
              <div className="p-2 bg-green-50 rounded border border-green-100">
                <p className="text-[10px] font-semibold text-green-700 uppercase tracking-wider mb-0.5">Recommended Position</p>
                <p className="text-[11px] text-gray-700">{item.recommendedPosition}</p>
              </div>
              <div>
                <p className="text-[10px] font-semibold text-gray-500 uppercase mb-1">Fallback Positions</p>
                {item.fallbackPositions.map((fp, j) => (
                  <div key={j} className="flex items-start gap-1.5 text-[11px] text-gray-600 py-0.5">
                    <ChevronRight className="w-3 h-3 text-navy-400 mt-0.5 flex-shrink-0" />
                    <span>{fp}</span>
                  </div>
                ))}
              </div>
            </motion.div>
          )}
        </div>
        <ChevronRight className={`w-4 h-4 text-gray-300 flex-shrink-0 mt-1 transition-transform ${expanded ? "rotate-90" : ""}`} />
      </button>
    </motion.div>
  );
}

// ── Vendor Benchmark Table ──────────────────────────────────────────────────

export function VendorBenchmarkTable({ data }: { data: VendorBenchmark[] }) {
  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2"><TrendingUp className="w-4.5 h-4.5 text-navy-700" /><h2 className="text-sm font-semibold text-navy-900">Vendor Market Analytics</h2></div>
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead className="bg-gray-50 border-b border-gray-100">
              <tr>
                <th className="text-left py-2.5 px-3 text-[10px] font-semibold text-gray-500 uppercase">Vendor</th>
                <th className="text-center py-2.5 px-3 text-[10px] font-semibold text-gray-500 uppercase">Aggressiveness</th>
                <th className="text-center py-2.5 px-3 text-[10px] font-semibold text-gray-500 uppercase">Deviations</th>
                <th className="text-center py-2.5 px-3 text-[10px] font-semibold text-gray-500 uppercase">Avg Deviation</th>
                <th className="text-left py-2.5 px-3 text-[10px] font-semibold text-gray-500 uppercase">Top Deviation</th>
                <th className="text-center py-2.5 px-3 text-[10px] font-semibold text-gray-500 uppercase">Trend</th>
                <th className="text-center py-2.5 px-3 text-[10px] font-semibold text-gray-500 uppercase">Contracts</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {data.map((v, i) => (
                <motion.tr key={v.vendor} initial={{ opacity: 0, y: 2 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.03 }}
                  className="hover:bg-navy-50/40 transition-colors">
                  <td className="py-2.5 px-3 font-medium text-gray-800">{v.vendor}</td>
                  <td className="py-2.5 px-3 text-center">
                    <span className={`inline-flex items-center gap-1 text-[10px] font-bold px-1.5 py-0.5 rounded-full ${
                      v.aggressivenessScore >= 8 ? "bg-red-50 text-red-700" : v.aggressivenessScore >= 6 ? "bg-orange-50 text-orange-700" : v.aggressivenessScore >= 4 ? "bg-yellow-50 text-yellow-700" : "bg-green-50 text-green-700"
                    }`}>
                      <span className={`w-1.5 h-1.5 rounded-full ${v.aggressivenessScore >= 8 ? "bg-red-500" : v.aggressivenessScore >= 6 ? "bg-orange-500" : v.aggressivenessScore >= 4 ? "bg-yellow-500" : "bg-green-500"}`} />
                      {v.aggressivenessScore}/10
                    </span>
                  </td>
                  <td className="py-2.5 px-3 text-center text-gray-600">{v.deviationCount}</td>
                  <td className="py-2.5 px-3 text-center">
                    <span className={`font-medium ${v.avgDeviation >= 3 ? "text-red-600" : v.avgDeviation >= 2 ? "text-orange-600" : "text-green-600"}`}>
                      {v.avgDeviation.toFixed(1)}
                    </span>
                  </td>
                  <td className="py-2.5 px-3 text-gray-600 text-[10px]">{v.topDeviations[0]?.clause || "—"}</td>
                  <td className="py-2.5 px-3 text-center">
                    <span className={`text-[10px] font-medium ${v.trend > 0 ? "text-red-500" : "text-green-500"}`}>
                      {v.trend > 0 ? "↑" : "↓"} {Math.abs(v.trend).toFixed(1)}
                    </span>
                  </td>
                  <td className="py-2.5 px-3 text-center text-gray-500">{v.contractsAnalyzed}</td>
                </motion.tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

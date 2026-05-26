"use client";

import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Brain, AlertTriangle, AlertOctagon, Clock, Lightbulb, ChevronRight, Sparkles, TrendingDown, DollarSign } from "lucide-react";
import type { ProcurementInsight, SavingsOpportunity } from "./types";

const severityCfg = {
  critical: { icon: <AlertTriangle className="w-4 h-4 text-red-500" />, border: "border-l-red-500", bg: "bg-red-50", dot: "bg-red-500" },
  warning: { icon: <AlertOctagon className="w-4 h-4 text-orange-500" />, border: "border-l-orange-500", bg: "bg-orange-50", dot: "bg-orange-500" },
  info: { icon: <Clock className="w-4 h-4 text-blue-500" />, border: "border-l-blue-500", bg: "bg-blue-50", dot: "bg-blue-500" },
  success: { icon: <Lightbulb className="w-4 h-4 text-green-500" />, border: "border-l-green-500", bg: "bg-green-50", dot: "bg-green-500" },
};

function InsightCard({ insight, index }: { insight: ProcurementInsight; index: number }) {
  const [expanded, setExpanded] = useState(false);
  const cfg = severityCfg[insight.severity];
  return (
    <motion.div initial={{ opacity: 0, x: -8 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: index * 0.06 }}
      className={`border-l-4 ${cfg.border} bg-white rounded-lg border border-gray-200 shadow-sm hover:shadow-md transition-all duration-200`}>
      <button onClick={() => setExpanded(!expanded)} className="w-full text-left p-3 flex items-start gap-2.5">
        <div className={`w-8 h-8 rounded-full ${cfg.bg} flex items-center justify-center flex-shrink-0 mt-0.5`}>{cfg.icon}</div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-0.5">
            <h4 className="text-xs font-semibold text-navy-900">{insight.title}</h4>
            <span className={`w-1.5 h-1.5 rounded-full ${cfg.dot}`} />
            <span className="text-[10px] font-medium text-gray-400">{insight.confidence}% conf.</span>
            {insight.savings && <span className="text-[10px] font-semibold text-green-600 bg-green-50 px-1.5 py-0.5 rounded">${insight.savings}M savings</span>}
          </div>
          <p className={`text-[11px] text-gray-600 leading-relaxed ${expanded ? "" : "line-clamp-1"}`}>{insight.description}</p>
          <AnimatePresence>{expanded && (
            <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }} exit={{ height: 0, opacity: 0 }} className="mt-2 space-y-2 overflow-hidden">
              <div className="flex gap-1 flex-wrap">
                {insight.impactedSuppliers.map((s) => (
                  <span key={s} className="text-[10px] px-1.5 py-0.5 rounded bg-navy-50 text-navy-700">{s}</span>
                ))}
              </div>
              <div className="p-2 bg-navy-50 rounded border border-navy-100">
                <p className="text-[10px] font-semibold text-navy-700 uppercase tracking-wider mb-0.5">Suggested Action</p>
                <p className="text-[11px] text-gray-700">{insight.suggestedAction}</p>
              </div>
              <div className="flex gap-1.5">
                {insight.quickActions.map((a) => (
                  <button key={a.label} className="text-[10px] font-medium px-2 py-1 rounded-md bg-navy-700 text-white hover:bg-navy-800 transition-colors">{a.label}</button>
                ))}
              </div>
            </motion.div>
          )}</AnimatePresence>
        </div>
        <ChevronRight className={`w-4 h-4 text-gray-300 flex-shrink-0 mt-1 transition-transform ${expanded ? "rotate-90" : ""}`} />
      </button>
    </motion.div>
  );
}

export function ProcurementAiInsights({ insights }: { insights: ProcurementInsight[] }) {
  const critical = insights.filter((i) => i.severity === "critical").length;
  const warning = insights.filter((i) => i.severity === "warning").length;
  const totalSavings = insights.reduce((s, i) => s + (i.savings || 0), 0);
  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2"><Brain className="w-4.5 h-4.5 text-navy-700" /><h2 className="text-sm font-semibold text-navy-900">AI Procurement Intelligence</h2></div>
        <span className="text-[10px] text-gray-400 bg-gray-100 px-2 py-0.5 rounded-full">{insights.length} insights</span>
      </div>
      <div className="flex items-center gap-3 px-3 py-2 bg-gradient-to-r from-navy-50 to-indigo-50 rounded-lg border border-navy-100">
        <Sparkles className="w-4 h-4 text-navy-600" />
        <span className="text-[11px] font-medium text-navy-700">
          <span className="font-bold text-red-600">{critical} critical</span> and <span className="font-bold text-orange-600">{warning} warnings</span>
        </span>
        {totalSavings > 0 && (
          <><span className="w-px h-3 bg-navy-200" /><span className="text-[11px] text-green-700 font-medium"><TrendingDown className="w-3 h-3 inline" /> ${totalSavings}M savings identified</span></>
        )}
      </div>
      <div className="space-y-1.5">{insights.map((insight, i) => <InsightCard key={insight.id} insight={insight} index={i} />)}</div>
    </div>
  );
}

// ── Savings Opportunities ───────────────────────────────────────────────────

export function SavingsWidget({ opportunities }: { opportunities: SavingsOpportunity[] }) {
  const total = opportunities.reduce((s, o) => s + o.potentialSavings, 0);
  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2"><TrendingDown className="w-4 h-4 text-green-600" /><h3 className="text-xs font-semibold text-navy-900">Savings Opportunities</h3></div>
        <span className="text-xs font-bold text-green-600">${total.toFixed(1)}M</span>
      </div>
      {opportunities.map((opp) => (
        <div key={opp.id} className="p-2.5 bg-white border border-gray-100 rounded-lg hover:shadow-sm transition-shadow">
          <div className="flex items-center justify-between mb-1">
            <h4 className="text-[11px] font-semibold text-navy-900">{opp.title}</h4>
            <span className="text-[11px] font-bold text-green-600">${opp.potentialSavings}M</span>
          </div>
          <p className="text-[10px] text-gray-500 mb-1.5">{opp.description}</p>
          <div className="flex items-center justify-between">
            <div className="flex gap-1">
              {opp.suppliers.slice(0, 2).map((s) => <span key={s} className="text-[9px] px-1 py-0.5 rounded bg-gray-100 text-gray-600">{s}</span>)}
              {opp.suppliers.length > 2 && <span className="text-[9px] text-gray-400">+{opp.suppliers.length - 2}</span>}
            </div>
            <div className="flex items-center gap-1.5">
              <span className={`text-[9px] font-medium px-1.5 py-0.5 rounded-full ${opp.effort === "low" ? "bg-green-50 text-green-700" : opp.effort === "medium" ? "bg-yellow-50 text-yellow-700" : "bg-red-50 text-red-700"}`}>{opp.effort} effort</span>
              <span className="text-[9px] text-gray-400">{opp.confidence}% conf.</span>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

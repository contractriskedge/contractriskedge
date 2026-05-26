"use client";

import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Brain, AlertTriangle, AlertOctagon, Clock, Lightbulb, ChevronRight, Sparkles, TrendingUp } from "lucide-react";
import type { MarketInsight } from "./types";

const severityCfg: Record<string, { icon: React.ReactNode; border: string; bg: string; dot: string }> = {
  critical: { icon: <AlertTriangle className="w-4 h-4 text-red-500" />, border: "border-l-red-500", bg: "bg-red-50", dot: "bg-red-500" },
  warning: { icon: <AlertOctagon className="w-4 h-4 text-orange-500" />, border: "border-l-orange-500", bg: "bg-orange-50", dot: "bg-orange-500" },
  info: { icon: <Clock className="w-4 h-4 text-blue-500" />, border: "border-l-blue-500", bg: "bg-blue-50", dot: "bg-blue-500" },
  success: { icon: <Lightbulb className="w-4 h-4 text-green-500" />, border: "border-l-green-500", bg: "bg-green-50", dot: "bg-green-500" },
};

function InsightCard({ insight, index }: { insight: MarketInsight; index: number }) {
  const [expanded, setExpanded] = useState(false);
  const cfg = severityCfg[insight.severity];
  return (
    <motion.div initial={{ opacity: 0, x: -8 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: index * 0.06 }}
      className={`border-l-4 ${cfg.border} bg-white rounded-lg border border-gray-200 shadow-sm hover:shadow-md transition-all`}>
      <button onClick={() => setExpanded(!expanded)} className="w-full text-left p-3 flex items-start gap-2.5">
        <div className={`w-8 h-8 rounded-full ${cfg.bg} flex items-center justify-center flex-shrink-0 mt-0.5`}>{cfg.icon}</div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-0.5">
            <h4 className="text-xs font-semibold text-navy-900">{insight.title}</h4>
            <span className={`w-1.5 h-1.5 rounded-full ${cfg.dot}`} />
            <span className="text-[10px] font-medium text-gray-400">{insight.confidence}% conf.</span>
            <span className="text-[10px] font-medium text-navy-600 bg-navy-50 px-1.5 py-0.5 rounded">P{insight.percentile}</span>
          </div>
          <p className={`text-[11px] text-gray-600 leading-relaxed ${expanded ? "" : "line-clamp-1"}`}>{insight.description}</p>
          <AnimatePresence>{expanded && (
            <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }} exit={{ height: 0, opacity: 0 }} className="mt-2 space-y-2 overflow-hidden">
              <div className="flex gap-1 flex-wrap">{insight.affectedClauses.map((c) => (
                <span key={c} className="text-[9px] px-1.5 py-0.5 rounded bg-navy-50 text-navy-700 font-medium">{c}</span>
              ))}</div>
              <div className="p-2 bg-navy-50 rounded border border-navy-100">
                <p className="text-[10px] font-semibold text-navy-700 uppercase tracking-wider mb-0.5">Recommendation</p>
                <p className="text-[11px] text-gray-700">{insight.recommendation}</p>
              </div>
              {insight.fallbackLanguage && (
                <div className="p-2 bg-green-50 rounded border border-green-100">
                  <p className="text-[10px] font-semibold text-green-700 uppercase tracking-wider mb-0.5">Suggested Fallback Language</p>
                  <p className="text-[11px] text-gray-700 italic">"{insight.fallbackLanguage}"</p>
                </div>
              )}
              <div className="flex gap-1.5">{insight.quickActions.map((a) => (
                <button key={a.label} className="text-[10px] font-medium px-2 py-1 rounded-md bg-navy-700 text-white hover:bg-navy-800 transition-colors">{a.label}</button>
              ))}</div>
            </motion.div>
          )}</AnimatePresence>
        </div>
        <ChevronRight className={`w-4 h-4 text-gray-300 flex-shrink-0 mt-1 transition-transform ${expanded ? "rotate-90" : ""}`} />
      </button>
    </motion.div>
  );
}

export function BenchmarkAiInsights({ insights }: { insights: MarketInsight[] }) {
  const critical = insights.filter((i) => i.severity === "critical").length;
  const warning = insights.filter((i) => i.severity === "warning").length;
  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2"><TrendingUp className="w-4.5 h-4.5 text-navy-700" /><h2 className="text-sm font-semibold text-navy-900">AI Market Intelligence</h2></div>
        <span className="text-[10px] text-gray-400 bg-gray-100 px-2 py-0.5 rounded-full">{insights.length} insights</span>
      </div>
      <div className="flex items-center gap-3 px-3 py-2 bg-gradient-to-r from-navy-50 to-indigo-50 rounded-lg border border-navy-100">
        <Sparkles className="w-4 h-4 text-navy-600" />
        <span className="text-[11px] font-medium text-navy-700">
          <span className="font-bold text-red-600">{critical} critical</span> and <span className="font-bold text-orange-600">{warning} warnings</span> — {insights.reduce((s, i) => s + i.percentile, 0) / insights.length}th percentile avg
        </span>
      </div>
      <div className="space-y-1.5 max-h-[500px] overflow-y-auto pr-1">{insights.map((insight, i) => <InsightCard key={insight.id} insight={insight} index={i} />)}</div>
    </div>
  );
}

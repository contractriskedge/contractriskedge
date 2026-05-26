"use client";

import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Brain, AlertTriangle, AlertOctagon, Clock, Lightbulb, X,
  ChevronRight, Sparkles, MessageSquare, Send, Loader2,
} from "lucide-react";
import type { AiInsight, AlertSeverity } from "./types";

// ── Severity config ─────────────────────────────────────────────────────────

const severityConfig: Record<AlertSeverity, { icon: React.ReactNode; border: string; bg: string; dot: string }> = {
  critical: {
    icon: <AlertTriangle className="w-4 h-4 text-red-500" />,
    border: "border-l-red-500",
    bg: "bg-red-50",
    dot: "bg-red-500",
  },
  warning: {
    icon: <AlertOctagon className="w-4 h-4 text-orange-500" />,
    border: "border-l-orange-500",
    bg: "bg-orange-50",
    dot: "bg-orange-500",
  },
  info: {
    icon: <Clock className="w-4 h-4 text-blue-500" />,
    border: "border-l-blue-500",
    bg: "bg-blue-50",
    dot: "bg-blue-500",
  },
  success: {
    icon: <Lightbulb className="w-4 h-4 text-green-500" />,
    border: "border-l-green-500",
    bg: "bg-green-50",
    dot: "bg-green-500",
  },
};

// ── AI Insight Card ─────────────────────────────────────────────────────────

function AiInsightCard({ insight, index }: { insight: AiInsight; index: number }) {
  const [expanded, setExpanded] = useState(false);
  const cfg = severityConfig[insight.severity];

  return (
    <motion.div
      initial={{ opacity: 0, x: -10 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: index * 0.08 }}
      className={`border-l-4 ${cfg.border} bg-white rounded-lg border border-gray-200 shadow-sm hover:shadow-md transition-all duration-200`}
    >
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full text-left p-3.5 flex items-start gap-3"
      >
        <div className={`w-8 h-8 rounded-full ${cfg.bg} flex items-center justify-center flex-shrink-0 mt-0.5`}>
          {cfg.icon}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <h4 className="text-xs font-semibold text-navy-900">{insight.title}</h4>
            <span className={`w-1.5 h-1.5 rounded-full ${cfg.dot}`} />
            <span className="text-[10px] font-medium text-gray-400">{insight.confidence}% confidence</span>
          </div>
          <p className={`text-[11px] text-gray-600 leading-relaxed ${expanded ? "" : "line-clamp-2"}`}>
            {insight.description}
          </p>

          {/* Expanded content */}
          <AnimatePresence>
            {expanded && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: "auto", opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                className="mt-3 space-y-2.5 overflow-hidden"
              >
                <div className="p-2.5 bg-navy-50 rounded-lg border border-navy-100">
                  <p className="text-[10px] font-semibold text-navy-700 uppercase tracking-wider mb-1">Recommended Action</p>
                  <p className="text-[11px] text-gray-700">{insight.recommendedAction}</p>
                </div>
                <div className="flex gap-1.5">
                  {insight.quickActions.map((action) => (
                    <button
                      key={action.label}
                      className="text-[10px] font-medium px-2.5 py-1.5 rounded-md bg-navy-700 text-white hover:bg-navy-800 transition-colors"
                    >
                      {action.label}
                    </button>
                  ))}
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
        <ChevronRight
          className={`w-4 h-4 text-gray-300 flex-shrink-0 mt-1 transition-transform duration-200 ${expanded ? "rotate-90" : ""}`}
        />
      </button>
    </motion.div>
  );
}

// ── AI Summary Panel ────────────────────────────────────────────────────────

function AiSummaryBar({ insights }: { insights: AiInsight[] }) {
  const critical = insights.filter((i) => i.severity === "critical").length;
  const warning = insights.filter((i) => i.severity === "warning").length;
  const avgConfidence = Math.round(insights.reduce((s, i) => s + i.confidence, 0) / insights.length);

  return (
    <div className="flex items-center gap-4 px-4 py-2.5 bg-gradient-to-r from-navy-50 to-indigo-50 rounded-lg border border-navy-100">
      <Sparkles className="w-4 h-4 text-navy-600" />
      <span className="text-xs font-medium text-navy-700">
        AI detected <span className="font-bold text-red-600">{critical} critical</span> and <span className="font-bold text-orange-600">{warning} warnings</span>
      </span>
      <div className="w-px h-4 bg-navy-200" />
      <span className="text-[11px] text-gray-500">Avg confidence: <span className="font-semibold text-navy-700">{avgConfidence}%</span></span>
      <span className="text-[11px] text-gray-400 ml-auto">Last analysis: Today, 09:30 AM</span>
    </div>
  );
}

// ── Ask AI Assistant ────────────────────────────────────────────────────────

function AskAiAssistant() {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [response, setResponse] = useState<string | null>(null);

  const handleAsk = () => {
    if (!query.trim()) return;
    setLoading(true);
    setResponse(null);
    // Simulate AI response
    setTimeout(() => {
      setResponse(`Based on your portfolio analysis:\n\n1. **${query}** — Found 12 relevant clauses across 8 contracts.\n2. Top risk: Uncapped liability in Acme Corp agreement.\n3. Recommended action: Schedule legal review for Q2.`);
      setLoading(false);
    }, 1500);
  };

  return (
    <>
      {/* Floating button */}
      <motion.button
        onClick={() => setOpen(!open)}
        className={`fixed bottom-6 right-6 z-40 w-12 h-12 rounded-full shadow-lg flex items-center justify-center transition-all ${
          open ? "bg-navy-800 rotate-45" : "bg-navy-700 hover:bg-navy-800"
        }`}
        whileHover={{ scale: 1.1 }}
        whileTap={{ scale: 0.9 }}
        aria-label="Ask AI Assistant"
      >
        {open ? <X className="w-5 h-5 text-white" /> : <Brain className="w-5 h-5 text-white" />}
      </motion.button>

      {/* Chat panel */}
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: 20, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 20, scale: 0.95 }}
            className="fixed bottom-20 right-6 z-40 w-80 bg-white rounded-xl border border-gray-200 shadow-2xl overflow-hidden"
          >
            <div className="px-4 py-3 bg-navy-700 text-white flex items-center gap-2">
              <Brain className="w-4 h-4" />
              <span className="text-xs font-semibold">Ask AI Assistant</span>
            </div>
            <div className="p-3 max-h-48 overflow-y-auto">
              {response ? (
                <div className="p-2.5 bg-navy-50 rounded-lg text-[11px] text-gray-700 leading-relaxed whitespace-pre-wrap">
                  {response}
                </div>
              ) : loading ? (
                <div className="flex items-center justify-center py-6">
                  <Loader2 className="w-5 h-5 text-navy-500 animate-spin" />
                </div>
              ) : (
                <p className="text-[11px] text-gray-400 text-center py-4">
                  Ask about contracts, risks, exposures, or recommendations
                </p>
              )}
            </div>
            <div className="border-t border-gray-100 p-3 flex gap-2">
              <input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleAsk()}
                placeholder="Ask about your portfolio..."
                className="flex-1 text-xs border border-gray-200 rounded-lg px-2.5 py-1.5 focus:border-navy-400 focus:ring-1 focus:ring-navy-400"
              />
              <button
                onClick={handleAsk}
                disabled={loading || !query.trim()}
                className="p-1.5 rounded-lg bg-navy-700 text-white hover:bg-navy-800 disabled:opacity-40 transition-colors"
              >
                <Send className="w-3.5 h-3.5" />
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}

// ── Main AI Insights Panel ──────────────────────────────────────────────────

interface AiInsightsPanelProps {
  insights: AiInsight[];
}

export function AiInsightsPanel({ insights }: AiInsightsPanelProps) {
  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Brain className="w-5 h-5 text-navy-700" />
          <h2 className="text-sm font-semibold text-navy-900">AI-Powered Insights</h2>
        </div>
        <span className="text-[10px] text-gray-400 bg-gray-100 px-2 py-0.5 rounded-full">
          {insights.length} insights
        </span>
      </div>

      <AiSummaryBar insights={insights} />

      <div className="space-y-2">
        {insights.map((insight, i) => (
          <AiInsightCard key={insight.id} insight={insight} index={i} />
        ))}
      </div>

      <AskAiAssistant />
    </div>
  );
}

"use client";

import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Brain, Lightbulb, AlertTriangle, CheckCircle, XCircle, Info,
  ChevronDown, ChevronRight, Sparkles, Link, Copy, FileSearch,
  BarChart3, TrendingUp, Target,
} from "lucide-react";
import type { AiExtractionInsight, DuplicateGroup, IngestionAnalytics } from "./types";

// ── Extraction Insight Card ──────────────────────────────────────────────

function ExtractionInsightCard({ insight }: { insight: AiExtractionInsight }) {
  const [expanded, setExpanded] = useState(false);
  const colors: Record<string, string> = {
    critical: "border-red-200 bg-red-50/50 dark:border-red-900/50 dark:bg-red-900/10",
    warning: "border-amber-200 bg-amber-50/50 dark:border-amber-900/50 dark:bg-amber-900/10",
    info: "border-blue-200 bg-blue-50/50 dark:border-blue-900/50 dark:bg-blue-900/10",
    success: "border-green-200 bg-green-50/50 dark:border-green-900/50 dark:bg-green-900/10",
  };
  const typeIcons: Record<string, React.ReactNode> = {
    classification: <Brain className="w-3 h-3" />,
    relationship: <Link className="w-3 h-3" />,
    anomaly: <AlertTriangle className="w-3 h-3" />,
    quality: <Target className="w-3 h-3" />,
    suggestion: <Lightbulb className="w-3 h-3" />,
    duplicate: <Copy className="w-3 h-3" />,
  };
  return (
    <div className={`border rounded-lg overflow-hidden ${colors[insight.severity]}`}>
      <button onClick={() => setExpanded(!expanded)} className="w-full text-left px-2.5 py-2 flex items-start gap-2 hover:bg-black/5 dark:hover:bg-white/5 transition-colors">
        <div className={`mt-0.5 ${insight.severity === "critical" ? "text-red-500" : insight.severity === "warning" ? "text-amber-500" : insight.severity === "success" ? "text-green-500" : "text-blue-500"}`}>
          {typeIcons[insight.type] || <Brain className="w-3 h-3" />}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-1.5">
            <span className="text-[10px] font-semibold text-navy-900 dark:text-white">{insight.title}</span>
            <span className={`text-[7px] px-1 py-0.5 rounded-full font-medium ${
              insight.confidence > 90 ? "bg-green-100 text-green-700" : insight.confidence > 80 ? "bg-blue-100 text-blue-700" : "bg-amber-100 text-amber-700"
            }`}>{insight.confidence}%</span>
          </div>
          <p className="text-[9px] text-gray-600 dark:text-gray-300 mt-0.5 line-clamp-2">{insight.description}</p>
        </div>
        {expanded ? <ChevronDown className="w-2.5 h-2.5 text-gray-400" /> : <ChevronRight className="w-2.5 h-2.5 text-gray-400" />}
      </button>
      <AnimatePresence>
        {expanded && (
          <motion.div initial={{ height: 0 }} animate={{ height: "auto" }} exit={{ height: 0 }} className="overflow-hidden">
            <div className="px-2.5 pb-2.5 space-y-1">
              {insight.suggestedAction && (
                <button className="flex items-center gap-1 px-2 py-1 bg-purple-500 hover:bg-purple-600 text-white rounded text-[8px] font-medium transition-colors">
                  <Sparkles className="w-2 h-2" /> {insight.suggestedAction}
                </button>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

// ── Duplicate Group Card ─────────────────────────────────────────────────

function DuplicateGroupCard({ group }: { group: DuplicateGroup }) {
  return (
    <div className="border border-amber-200 dark:border-amber-900/50 bg-amber-50/50 dark:bg-amber-900/10 rounded-lg p-2">
      <div className="flex items-center gap-1.5 mb-1">
        <Copy className="w-3 h-3 text-amber-500" />
        <span className="text-[9px] font-semibold text-navy-900 dark:text-white">Possible Duplicates</span>
        <span className="text-[7px] text-amber-600 font-medium">{group.aiConfidence}% match</span>
      </div>
      <p className="text-[8px] text-gray-500 mb-1">{group.reason}</p>
      <div className="space-y-0.5">
        {group.documents.map(d => (
          <div key={d.id} className="flex items-center gap-1 text-[8px] text-gray-600 dark:text-gray-300">
            <FileSearch className="w-2 h-2 text-gray-400" />
            <span className="truncate flex-1">{d.name}</span>
            <span className="text-gray-400">{d.similarity}%</span>
          </div>
        ))}
      </div>
      <div className="flex items-center gap-1 mt-1">
        <button className="text-[8px] px-1.5 py-0.5 bg-green-500 text-white rounded hover:bg-green-600 transition-colors">Resolve</button>
        <button className="text-[8px] px-1.5 py-0.5 border border-gray-200 rounded hover:bg-gray-50 transition-colors">Review</button>
      </div>
    </div>
  );
}

// ── Right Panel ──────────────────────────────────────────────────────────

interface IngestionRightPanelProps {
  insights: AiExtractionInsight[];
  duplicateGroups: DuplicateGroup[];
  analytics: IngestionAnalytics;
}

type RightTab = "insights" | "duplicates" | "analytics";

export function IngestionRightPanel({ insights, duplicateGroups, analytics }: IngestionRightPanelProps) {
  const [activeTab, setActiveTab] = useState<RightTab>("insights");

  const tabs: { id: RightTab; label: string; icon: React.ReactNode }[] = [
    { id: "insights", label: "AI Insights", icon: <Brain className="w-3 h-3" /> },
    { id: "duplicates", label: "Duplicates", icon: <Copy className="w-3 h-3" /> },
    { id: "analytics", label: "Analytics", icon: <BarChart3 className="w-3 h-3" /> },
  ];

  return (
    <div className="w-72 flex-shrink-0 bg-white dark:bg-navy-800 border-l border-gray-200 dark:border-navy-700 flex flex-col h-full">
      <div className="flex border-b border-gray-200 dark:border-navy-700">
        {tabs.map(tab => (
          <button key={tab.id} onClick={() => setActiveTab(tab.id)}
            className={`flex-1 flex items-center justify-center gap-1 py-2 text-[9px] font-medium transition-colors relative ${
              activeTab === tab.id ? "text-gold-600 dark:text-gold-400" : "text-gray-500 dark:text-gray-400 hover:text-navy-700"
            }`}>
            {tab.icon}<span>{tab.label}</span>
            {activeTab === tab.id && <motion.div layoutId="ing-right-tab" className="absolute bottom-0 left-0 right-0 h-0.5 bg-gold-500" />}
          </button>
        ))}
      </div>

      <div className="flex-1 overflow-y-auto p-2 space-y-1.5">
        {activeTab === "insights" && (
          <>
            <div className="flex items-center justify-between px-1 mb-1">
              <span className="text-[8px] font-semibold text-gray-400 uppercase tracking-wider">AI Extraction ({insights.length})</span>
              <Sparkles className="w-2.5 h-2.5 text-purple-400" />
            </div>
            {insights.map(i => <ExtractionInsightCard key={i.id} insight={i} />)}
          </>
        )}

        {activeTab === "duplicates" && (
          <>
            <div className="flex items-center justify-between px-1 mb-1">
              <span className="text-[8px] font-semibold text-gray-400 uppercase tracking-wider">Duplicate Groups ({duplicateGroups.length})</span>
              <span className="text-[7px] text-amber-600">{duplicateGroups.filter(d => !d.resolved).length} unresolved</span>
            </div>
            {duplicateGroups.map(g => <DuplicateGroupCard key={g.id} group={g} />)}
          </>
        )}

        {activeTab === "analytics" && (
          <div className="space-y-3">
            <div className="grid grid-cols-2 gap-1.5">
              {[
                { label: "Processed", value: analytics.totalProcessed.toLocaleString(), color: "text-blue-600" },
                { label: "Failed", value: analytics.totalFailed.toString(), color: "text-red-600" },
                { label: "Avg OCR", value: `${analytics.avgOcrAccuracy}%`, color: "text-green-600" },
                { label: "Avg Extraction", value: `${analytics.avgExtractionConfidence}%`, color: "text-purple-600" },
              ].map(s => (
                <div key={s.label} className="bg-gray-50 dark:bg-navy-900 rounded-lg p-2 text-center">
                  <p className={`text-sm font-bold ${s.color} tabular-nums`}>{s.value}</p>
                  <p className="text-[7px] text-gray-500 mt-0.5">{s.label}</p>
                </div>
              ))}
            </div>

            {/* Source Distribution */}
            <div>
              <h4 className="text-[8px] font-semibold text-gray-400 uppercase tracking-wider mb-1">By Source</h4>
              <div className="space-y-0.5">
                {analytics.sourceDistribution.slice(0, 4).map(s => (
                  <div key={s.source} className="flex items-center gap-2">
                    <span className="text-[8px] text-gray-600 dark:text-gray-300 w-20 truncate">{s.source}</span>
                    <div className="flex-1 h-2 bg-gray-100 dark:bg-navy-700 rounded-full overflow-hidden">
                      <motion.div initial={{ width: 0 }} animate={{ width: `${(s.count / Math.max(...analytics.sourceDistribution.map(x => x.count))) * 100}%` }} className="h-full bg-gold-500 rounded-full" />
                    </div>
                    <span className="text-[7px] text-gray-500 tabular-nums w-10 text-right">{(s.count / analytics.totalProcessed * 100).toFixed(0)}%</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Failure Reasons */}
            <div>
              <h4 className="text-[8px] font-semibold text-gray-400 uppercase tracking-wider mb-1">Failure Reasons</h4>
              <div className="space-y-0.5">
                {analytics.failureReasons.slice(0, 4).map(f => (
                  <div key={f.reason} className="flex items-center gap-2">
                    <span className="text-[8px] text-gray-600 dark:text-gray-300 w-28 truncate">{f.reason}</span>
                    <div className="flex-1 h-2 bg-gray-100 dark:bg-navy-700 rounded-full overflow-hidden">
                      <motion.div initial={{ width: 0 }} animate={{ width: `${(f.count / Math.max(...analytics.failureReasons.map(x => x.count))) * 100}%` }} className="h-full bg-red-500 rounded-full" />
                    </div>
                    <span className="text-[7px] text-gray-500 tabular-nums w-4 text-right">{f.count}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* OCR Accuracy Trend */}
            <div>
              <h4 className="text-[8px] font-semibold text-gray-400 uppercase tracking-wider mb-1">OCR Accuracy Trend</h4>
              <div className="space-y-0.5">
                {analytics.ocrAccuracyTrend.map(item => (
                  <div key={item.date} className="flex items-center gap-2">
                    <span className="text-[7px] text-gray-500 w-10">{item.date}</span>
                    <div className="flex-1 h-2 bg-gray-100 dark:bg-navy-700 rounded-full overflow-hidden">
                      <motion.div initial={{ width: 0 }} animate={{ width: `${item.accuracy}%` }} className="h-full bg-green-500 rounded-full" />
                    </div>
                    <span className="text-[7px] text-gray-500 tabular-nums w-8 text-right">{item.accuracy}%</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

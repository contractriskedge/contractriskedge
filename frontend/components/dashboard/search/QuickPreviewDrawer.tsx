"use client";

import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  X, FileText, Brain, FileSearch, Share2, Workflow, ClipboardCheck,
  Clock, AlertTriangle, CheckCircle, XCircle, ExternalLink,
  ChevronRight, User, Calendar,
} from "lucide-react";
import type { SearchResult, QuickPreviewData, RiskLevel } from "./types";
import { mockQuickPreviewData } from "./mockData";

// ── Quick Preview Drawer ─────────────────────────────────────────────────

interface QuickPreviewDrawerProps {
  result: SearchResult | null;
  isOpen: boolean;
  onClose: () => void;
}

type PreviewTab = "overview" | "insights" | "clauses" | "relationships" | "workflow" | "obligations" | "activity" | "similar";

export function QuickPreviewDrawer({ result, isOpen, onClose }: QuickPreviewDrawerProps) {
  const [activeTab, setActiveTab] = useState<PreviewTab>("overview");
  const data = mockQuickPreviewData;

  if (!result) return null;

  const tabs: { id: PreviewTab; label: string; icon: React.ReactNode }[] = [
    { id: "overview", label: "Overview", icon: <FileText className="w-3 h-3" /> },
    { id: "insights", label: "AI Insights", icon: <Brain className="w-3 h-3" /> },
    { id: "clauses", label: "Clauses", icon: <FileSearch className="w-3 h-3" /> },
    { id: "relationships", label: "Relationships", icon: <Share2 className="w-3 h-3" /> },
    { id: "workflow", label: "Workflow", icon: <Workflow className="w-3 h-3" /> },
    { id: "obligations", label: "Obligations", icon: <ClipboardCheck className="w-3 h-3" /> },
    { id: "activity", label: "Activity", icon: <Clock className="w-3 h-3" /> },
    { id: "similar", label: "Similar", icon: <Share2 className="w-3 h-3" /> },
  ];

  const riskColors: Record<string, string> = {
    critical: "text-red-600 bg-red-50 dark:bg-red-900/20 dark:text-red-400",
    high: "text-orange-600 bg-orange-50 dark:bg-orange-900/20 dark:text-orange-400",
    medium: "text-yellow-600 bg-yellow-50 dark:bg-yellow-900/20 dark:text-yellow-400",
    low: "text-green-600 bg-green-50 dark:bg-green-900/20 dark:text-green-400",
    info: "text-blue-600 bg-blue-50 dark:bg-blue-900/20 dark:text-blue-400",
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/20 z-40"
            onClick={onClose}
          />
          <motion.div
            initial={{ x: "100%" }}
            animate={{ x: 0 }}
            exit={{ x: "100%" }}
            transition={{ type: "spring", damping: 25, stiffness: 200 }}
            className="fixed right-0 top-0 bottom-0 w-[520px] bg-white dark:bg-navy-800 border-l border-gray-200 dark:border-navy-700 shadow-2xl z-50 flex flex-col"
          >
            {/* Header */}
            <div className="px-4 py-3 border-b border-gray-200 dark:border-navy-700 flex items-center justify-between">
              <div className="flex items-center gap-2 min-w-0">
                <div className="w-7 h-7 rounded-lg bg-gold-100 dark:bg-gold-900/30 flex items-center justify-center flex-shrink-0">
                  <FileText className="w-3.5 h-3.5 text-gold-600" />
                </div>
                <div className="min-w-0">
                  <h3 className="text-sm font-semibold text-navy-900 dark:text-white truncate">{result.title}</h3>
                  <p className="text-[10px] text-gray-500 truncate">{result.subtitle}</p>
                </div>
              </div>
              <button onClick={onClose} className="p-1 hover:bg-gray-100 dark:hover:bg-navy-700 rounded transition-colors flex-shrink-0">
                <X className="w-4 h-4 text-gray-400" />
              </button>
            </div>

            {/* Tabs */}
            <div className="flex border-b border-gray-200 dark:border-navy-700 overflow-x-auto">
              {tabs.map(tab => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`flex items-center gap-1 px-2.5 py-2 text-[9px] font-medium whitespace-nowrap transition-colors border-b-2 ${
                    activeTab === tab.id
                      ? "text-gold-600 border-gold-500"
                      : "text-gray-500 border-transparent hover:text-navy-700 dark:hover:text-gray-300"
                  }`}
                >
                  {tab.icon}
                  {tab.label}
                </button>
              ))}
            </div>

            {/* Content */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4">
              {/* Overview Tab */}
              {activeTab === "overview" && (
                <div className="space-y-4">
                  <p className="text-xs text-gray-600 dark:text-gray-300 leading-relaxed">{data.overview.description}</p>
                  <div className="grid grid-cols-2 gap-3">
                    {[
                      { label: "Status", value: data.overview.status },
                      { label: "Risk Level", value: data.overview.riskLevel, badge: true },
                      { label: "Contract Value", value: data.overview.value },
                      { label: "Counterparty", value: data.overview.counterparty },
                      { label: "Business Unit", value: data.overview.businessUnit },
                      { label: "Term", value: `${data.overview.dates.start} - ${data.overview.dates.end}` },
                    ].map(item => (
                      <div key={item.label} className="bg-gray-50 dark:bg-navy-900 rounded-lg p-2.5">
                        <span className="text-[9px] text-gray-500 uppercase tracking-wider">{item.label}</span>
                        <p className={`text-xs font-semibold mt-0.5 ${
                          item.badge ? riskColors[item.value] || "text-navy-900 dark:text-white" : "text-navy-900 dark:text-white"
                        }`}>
                          {item.value}
                        </p>
                      </div>
                    ))}
                  </div>
                  {/* Match Info */}
                  <div className="bg-purple-50 dark:bg-purple-900/10 border border-purple-100 dark:border-purple-900/30 rounded-lg p-3">
                    <div className="flex items-center gap-1 text-[9px] text-purple-600 font-medium mb-1">
                      <Brain className="w-3 h-3" /> AI Match Analysis
                    </div>
                    <p className="text-[10px] text-gray-700 dark:text-gray-300">{result.matchExplanation}</p>
                    <div className="flex items-center gap-3 mt-1.5 text-[9px] text-gray-500">
                      <span>Confidence: <strong className="text-purple-600">{result.confidence}%</strong></span>
                      {result.vectorScore && <span>Vector: {(result.vectorScore * 100).toFixed(0)}%</span>}
                      {result.hybridScore && <span>Hybrid: {(result.hybridScore * 100).toFixed(0)}%</span>}
                    </div>
                  </div>
                </div>
              )}

              {/* AI Insights Tab */}
              {activeTab === "insights" && (
                <div className="space-y-2">
                  {data.insights.map(insight => (
                    <div key={insight.id} className={`border rounded-lg p-3 ${
                      insight.severity === "critical" ? "border-red-200 bg-red-50/50 dark:border-red-900/50 dark:bg-red-900/10" :
                      insight.severity === "warning" ? "border-amber-200 bg-amber-50/50 dark:border-amber-900/50 dark:bg-amber-900/10" :
                      "border-blue-200 bg-blue-50/50 dark:border-blue-900/50 dark:bg-blue-900/10"
                    }`}>
                      <div className="flex items-center gap-1.5 mb-1">
                        <Brain className="w-3 h-3 text-purple-500" />
                        <span className="text-[10px] font-semibold text-navy-900 dark:text-white">{insight.title}</span>
                        <span className="text-[8px] text-gray-400">{insight.confidence}% conf</span>
                      </div>
                      <p className="text-[10px] text-gray-600 dark:text-gray-300">{insight.description}</p>
                    </div>
                  ))}
                </div>
              )}

              {/* Clauses Tab */}
              {activeTab === "clauses" && (
                <div className="space-y-2">
                  {data.clauses.map(clause => (
                    <div key={clause.id} className="border border-gray-200 dark:border-navy-600 rounded-lg p-3">
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-[10px] font-semibold text-navy-900 dark:text-white">{clause.title}</span>
                        <span className={`text-[8px] px-1.5 py-0.5 rounded-full font-medium ${riskColors[clause.riskLevel]}`}>{clause.riskLevel}</span>
                      </div>
                      <p className="text-[10px] text-gray-500 dark:text-gray-400">{clause.summary}</p>
                    </div>
                  ))}
                </div>
              )}

              {/* Relationships Tab */}
              {activeTab === "relationships" && (
                <div className="space-y-2">
                  {data.relationships.map(rel => (
                    <div key={rel.entity} className="flex items-center gap-3 bg-gray-50 dark:bg-navy-900 rounded-lg p-3">
                      <div className="flex-1">
                        <span className="text-xs font-medium text-navy-900 dark:text-white">{rel.entity}</span>
                        <span className="text-[9px] text-gray-500 ml-2">{rel.type}</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <div className="w-16 h-1.5 bg-gray-200 dark:bg-navy-700 rounded-full overflow-hidden">
                          <motion.div
                            initial={{ width: 0 }}
                            animate={{ width: `${rel.strength}%` }}
                            className={`h-full rounded-full ${rel.strength > 75 ? "bg-green-500" : rel.strength > 50 ? "bg-amber-500" : "bg-red-500"}`}
                          />
                        </div>
                        <span className="text-[9px] text-gray-500 tabular-nums w-6">{rel.strength}%</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {/* Workflow Tab */}
              {activeTab === "workflow" && (
                <div className="space-y-2">
                  {data.workflow.map((step, i) => (
                    <div key={step.stage} className="flex items-center gap-3">
                      <div className="flex flex-col items-center">
                        <div className={`w-6 h-6 rounded-full flex items-center justify-center ${
                          step.status === "completed" ? "bg-green-500" : step.status === "pending" ? "bg-amber-400" : "bg-gray-300"
                        }`}>
                          {step.status === "completed" ? <CheckCircle className="w-3 h-3 text-white" /> :
                           step.status === "pending" ? <Clock className="w-3 h-3 text-white" /> :
                           <XCircle className="w-3 h-3 text-white" />}
                        </div>
                        {i < data.workflow.length - 1 && <div className="w-px h-4 bg-gray-200 dark:bg-navy-600" />}
                      </div>
                      <div className="flex-1">
                        <span className="text-[10px] font-medium text-navy-900 dark:text-white">{step.stage}</span>
                        <div className="flex items-center gap-2 text-[9px] text-gray-500">
                          <span>{step.assignee}</span>
                          <span>·</span>
                          <span>SLA: {step.sla}</span>
                        </div>
                      </div>
                      <span className={`text-[9px] capitalize ${
                        step.status === "completed" ? "text-green-600" : step.status === "pending" ? "text-amber-600" : "text-red-600"
                      }`}>{step.status}</span>
                    </div>
                  ))}
                </div>
              )}

              {/* Obligations Tab */}
              {activeTab === "obligations" && (
                <div className="space-y-2">
                  {data.obligations.map(obl => (
                    <div key={obl.title} className="flex items-center justify-between border border-gray-200 dark:border-navy-600 rounded-lg p-3">
                      <div>
                        <span className="text-[10px] font-medium text-navy-900 dark:text-white">{obl.title}</span>
                        <div className="flex items-center gap-1 text-[9px] text-gray-500 mt-0.5">
                          <Calendar className="w-2.5 h-2.5" />
                          Due: {new Date(obl.dueDate).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })}
                        </div>
                      </div>
                      <span className={`text-[9px] px-1.5 py-0.5 rounded-full font-medium capitalize ${
                        obl.status === "completed" ? "bg-green-100 text-green-700" :
                        obl.status === "overdue" ? "bg-red-100 text-red-700" :
                        "bg-amber-100 text-amber-700"
                      }`}>{obl.status}</span>
                    </div>
                  ))}
                </div>
              )}

              {/* Activity Tab */}
              {activeTab === "activity" && (
                <div className="space-y-3">
                  {data.activity.map((act, i) => (
                    <div key={i} className="flex gap-3">
                      <div className="flex flex-col items-center">
                        <div className="w-5 h-5 rounded-full bg-navy-100 dark:bg-navy-700 flex items-center justify-center">
                          <Clock className="w-2.5 h-2.5 text-navy-500" />
                        </div>
                        {i < data.activity.length - 1 && <div className="w-px flex-1 bg-gray-200 dark:bg-navy-700" />}
                      </div>
                      <div className="flex-1 pb-3">
                        <span className="text-[10px] font-medium text-navy-900 dark:text-white">{act.action}</span>
                        <div className="flex items-center gap-2 text-[9px] text-gray-500">
                          <User className="w-2.5 h-2.5" />
                          <span>{act.user}</span>
                          <span>·</span>
                          <span>{new Date(act.timestamp).toLocaleDateString("en-US", { month: "short", day: "numeric" })}</span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {/* Similar Results Tab */}
              {activeTab === "similar" && (
                <div className="space-y-2">
                  {data.similarResults.map(sr => (
                    <div key={sr.id} className="border border-gray-200 dark:border-navy-600 rounded-lg p-3 hover:border-gray-300 dark:hover:border-navy-500 transition-colors cursor-pointer">
                      <div className="flex items-center gap-2 mb-1">
                        <FileText className="w-3 h-3 text-gray-400" />
                        <span className="text-[10px] font-medium text-navy-900 dark:text-white">{sr.title}</span>
                        <span className="text-[8px] text-gray-400 ml-auto">{sr.confidence}% similar</span>
                      </div>
                      <p className="text-[9px] text-gray-500 dark:text-gray-400 truncate">{sr.snippet}</p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}

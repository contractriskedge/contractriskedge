"use client";

import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  X, DollarSign, AlertTriangle, TrendingUp, Building2, Clock,
  Brain, FileText, BarChart3, User, Calendar, TrendingDown,
} from "lucide-react";
import type { FinancialExposure, FinancialDetail } from "./types";

const mockFinancialDetail: FinancialDetail = {
  id: "",
  contractId: "",
  contractName: "",
  exposureType: "",
  exposureAmount: 0,
  probability: 0,
  riskLevel: "medium",
  description: "No detail available",
  mitigation: "",
  owner: "",
  dueDate: "",
};

interface CfoDetailDrawerProps {
  exposure: FinancialExposure | null;
  isOpen: boolean;
  onClose: () => void;
}

type DetailTab = "overview" | "exposure" | "forecast" | "vendors" | "obligations" | "ai" | "trends" | "audit";

export function CfoDetailDrawer({ exposure, isOpen, onClose }: CfoDetailDrawerProps) {
  const [activeTab, setActiveTab] = useState<DetailTab>("overview");
  const data = mockFinancialDetail;

  if (!exposure) return null;

  const tabs: { id: DetailTab; label: string; icon: React.ReactNode }[] = [
    { id: "overview", label: "Overview", icon: <DollarSign className="w-3 h-3" /> },
    { id: "exposure", label: "Exposure", icon: <AlertTriangle className="w-3 h-3" /> },
    { id: "forecast", label: "Forecast", icon: <TrendingUp className="w-3 h-3" /> },
    { id: "vendors", label: "Vendors", icon: <Building2 className="w-3 h-3" /> },
    { id: "obligations", label: "Obligations", icon: <Clock className="w-3 h-3" /> },
    { id: "ai", label: "AI Insights", icon: <Brain className="w-3 h-3" /> },
    { id: "trends", label: "Trends", icon: <BarChart3 className="w-3 h-3" /> },
    { id: "audit", label: "Audit", icon: <FileText className="w-3 h-3" /> },
  ];

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="fixed inset-0 bg-black/20 z-40" onClick={onClose} />
          <motion.div
            initial={{ x: "100%" }} animate={{ x: 0 }} exit={{ x: "100%" }}
            transition={{ type: "spring", damping: 25, stiffness: 200 }}
            className="fixed right-0 top-0 bottom-0 w-[520px] bg-white dark:bg-navy-800 border-l border-gray-200 dark:border-navy-700 shadow-2xl z-50 flex flex-col"
          >
            <div className="px-4 py-3 border-b border-gray-200 dark:border-navy-700 flex items-center justify-between">
              <div className="flex items-center gap-2 min-w-0">
                <div className={`w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0 ${
                  exposure.riskLevel === "critical" ? "bg-red-100 text-red-600" : exposure.riskLevel === "warning" ? "bg-amber-100 text-amber-600" : "bg-blue-100 text-blue-600"
                }`}><DollarSign className="w-3.5 h-3.5" /></div>
                <div className="min-w-0">
                  <h3 className="text-sm font-semibold text-navy-900 dark:text-white truncate">{exposure.label}</h3>
                  <p className="text-[9px] text-gray-500 capitalize">{exposure.category} · ${(exposure.currentExposure / 1000000).toFixed(1)}M exposure</p>
                </div>
              </div>
              <button onClick={onClose} className="p-1 hover:bg-gray-100 dark:hover:bg-navy-700 rounded transition-colors flex-shrink-0"><X className="w-4 h-4 text-gray-400" /></button>
            </div>

            <div className="flex border-b border-gray-200 dark:border-navy-700 overflow-x-auto">
              {tabs.map(tab => (
                <button key={tab.id} onClick={() => setActiveTab(tab.id)}
                  className={`flex items-center gap-1 px-2 py-2 text-[8px] font-medium whitespace-nowrap transition-colors border-b-2 ${
                    activeTab === tab.id ? "text-gold-600 border-gold-500" : "text-gray-500 border-transparent hover:text-navy-700"
                  }`}>{tab.icon}{tab.label}</button>
              ))}
            </div>

            <div className="flex-1 overflow-y-auto p-4 space-y-4">
              {activeTab === "overview" && (
                <div className="space-y-4">
                  <div className="grid grid-cols-2 gap-3">
                    {[
                      { label: "Current Exposure", value: `$${(exposure.currentExposure / 1000000).toFixed(1)}M` },
                      { label: "Projected Exposure", value: `$${(exposure.projectedExposure / 1000000).toFixed(1)}M` },
                      { label: "Risk Level", value: exposure.riskLevel, badge: true },
                      { label: "Contracts Affected", value: exposure.contractCount.toString() },
                      { label: "Vendors Affected", value: exposure.vendorCount.toString() },
                      { label: "Trend", value: `${exposure.trend > 0 ? "+" : ""}${exposure.trend}%` },
                    ].map(item => (
                      <div key={item.label} className="bg-gray-50 dark:bg-navy-900 rounded-lg p-2.5">
                        <span className="text-[8px] text-gray-500 uppercase tracking-wider">{item.label}</span>
                        <p className={`text-xs font-semibold mt-0.5 ${
                          item.badge ? (item.value === "critical" ? "text-red-600" : item.value === "warning" ? "text-amber-600" : "text-blue-600") : "text-navy-900 dark:text-white"
                        }`}>{item.value}</p>
                      </div>
                    ))}
                  </div>
                  {exposure.details.length > 0 && (
                    <div>
                      <h4 className="text-[9px] font-semibold text-gray-500 uppercase tracking-wider mb-1">Top Exposures</h4>
                      <div className="space-y-1">
                        {exposure.details.map(d => (
                          <div key={d.id} className="border border-gray-200 dark:border-navy-600 rounded-lg p-2 flex items-center justify-between">
                            <div className="flex-1 min-w-0">
                              <span className="text-[10px] font-medium text-navy-900 dark:text-white truncate block">{d.contractTitle}</span>
                              <span className="text-[8px] text-gray-400">{d.clause}</span>
                            </div>
                            <span className={`text-[9px] font-bold tabular-nums ${
                              d.riskLevel === "critical" ? "text-red-600" : d.riskLevel === "high" ? "text-orange-600" : "text-amber-600"
                            }`}>${(d.amount / 1000000).toFixed(1)}M</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {activeTab === "exposure" && (
                <div className="space-y-1.5">
                  {data.exposureAnalysis.map((e, i) => (
                    <div key={i} className="flex items-center justify-between border border-gray-200 dark:border-navy-600 rounded-lg p-2.5">
                      <span className="text-[10px] text-navy-900 dark:text-white">{e.item}</span>
                      <div className="flex items-center gap-2">
                        <span className="text-[9px] font-bold tabular-nums">${(e.amount / 1000000).toFixed(1)}M</span>
                        <span className={`text-[8px] px-1.5 py-0.5 rounded-full font-medium capitalize ${
                          e.risk === "critical" ? "bg-red-100 text-red-700" : e.risk === "high" ? "bg-orange-100 text-orange-700" : "bg-amber-100 text-amber-700"
                        }`}>{e.risk}</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {activeTab === "forecast" && (
                <div>
                  <div className="space-y-1.5">
                    {data.forecasting.map((f, i) => (
                      <div key={i} className="flex items-center gap-2">
                        <span className="text-[8px] text-gray-600 dark:text-gray-300 w-16">{f.period}</span>
                        <div className="flex-1 h-3 bg-gray-100 dark:bg-navy-700 rounded-full overflow-hidden">
                          <motion.div initial={{ width: 0 }} animate={{ width: `${(f.projected / Math.max(...data.forecasting.map(x => x.projected))) * 100}%` }} className="h-full bg-amber-500 rounded-full" />
                        </div>
                        <span className="text-[8px] text-gray-500 tabular-nums w-12 text-right">${f.projected.toFixed(1)}M</span>
                        <span className="text-[7px] text-gray-400 w-8 text-right">{f.confidence}%</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {activeTab === "vendors" && (
                <div className="space-y-1.5">
                  {data.vendorImpact.map(v => (
                    <div key={v.vendor} className="border border-gray-200 dark:border-navy-600 rounded-lg p-2.5 flex items-center justify-between">
                      <div>
                        <span className="text-[10px] font-medium text-navy-900 dark:text-white">{v.vendor}</span>
                        <span className="text-[8px] text-gray-400 ml-2">{v.contracts} contracts</span>
                      </div>
                      <span className="text-[9px] font-bold text-red-600 tabular-nums">${(v.exposure / 1000000).toFixed(1)}M</span>
                    </div>
                  ))}
                </div>
              )}

              {activeTab === "obligations" && (
                <div className="space-y-1.5">
                  {data.obligations.map(o => (
                    <div key={o.title} className="border border-gray-200 dark:border-navy-600 rounded-lg p-2.5">
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-[10px] font-medium text-navy-900 dark:text-white">{o.title}</span>
                        <span className={`text-[8px] px-1.5 py-0.5 rounded-full font-medium capitalize ${
                          o.status === "overdue" ? "bg-red-100 text-red-700" : o.status === "in_progress" ? "bg-blue-100 text-blue-700" : "bg-amber-100 text-amber-700"
                        }`}>{o.status.replace("_", " ")}</span>
                      </div>
                      <div className="flex items-center gap-2 text-[8px] text-gray-400">
                        <DollarSign className="w-2.5 h-2.5" />
                        <span>${(o.amount / 1000000).toFixed(1)}M</span>
                        <Calendar className="w-2.5 h-2.5 ml-1" />
                        <span>{new Date(o.dueDate).toLocaleDateString("en-US", { month: "short", day: "numeric" })}</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {activeTab === "ai" && (
                <div className="space-y-2">
                  {data.aiInsights.map(insight => (
                    <div key={insight.id} className={`border rounded-lg p-3 ${
                      insight.severity === "critical" ? "border-red-200 bg-red-50/50 dark:border-red-900/50 dark:bg-red-900/10" :
                      insight.severity === "warning" ? "border-amber-200 bg-amber-50/50 dark:border-amber-900/50 dark:bg-amber-900/10" :
                      "border-blue-200 bg-blue-50/50 dark:border-blue-900/50 dark:bg-blue-900/10"
                    }`}>
                      <div className="flex items-center gap-1.5 mb-1">
                        <Brain className="w-3 h-3 text-purple-500" />
                        <span className="text-[10px] font-semibold text-navy-900 dark:text-white">{insight.title}</span>
                        <span className="text-[7px] text-gray-400">{insight.confidence}%</span>
                      </div>
                      <p className="text-[9px] text-gray-600 dark:text-gray-300">{insight.recommendedAction}</p>
                    </div>
                  ))}
                </div>
              )}

              {activeTab === "trends" && (
                <div className="space-y-1.5">
                  {data.trends.map((t, i) => (
                    <div key={i} className="flex items-center gap-2">
                      <span className="text-[8px] text-gray-500 w-8">{t.date}</span>
                      <div className="flex-1 h-3 bg-gray-100 dark:bg-navy-700 rounded-full overflow-hidden">
                        <motion.div initial={{ width: 0 }} animate={{ width: `${(t.value / Math.max(...data.trends.map(x => x.value))) * 100}%` }} className="h-full bg-red-500 rounded-full" />
                      </div>
                      <span className="text-[8px] text-gray-500 tabular-nums w-10 text-right">${t.value.toFixed(1)}M</span>
                    </div>
                  ))}
                </div>
              )}

              {activeTab === "audit" && (
                <div className="space-y-3">
                  {data.auditHistory.map((a, i) => (
                    <div key={i} className="flex gap-3">
                      <div className="flex flex-col items-center">
                        <div className="w-5 h-5 rounded-full bg-navy-100 dark:bg-navy-700 flex items-center justify-center"><Clock className="w-2.5 h-2.5 text-navy-500" /></div>
                        {i < data.auditHistory.length - 1 && <div className="w-px flex-1 bg-gray-200 dark:bg-navy-700" />}
                      </div>
                      <div className="flex-1 pb-3">
                        <span className="text-[10px] font-medium text-navy-900 dark:text-white">{a.action}</span>
                        <div className="flex items-center gap-2 text-[8px] text-gray-500 mt-0.5">
                          <User className="w-2.5 h-2.5" /><span>{a.user}</span>
                          <span>·</span>
                          <span>{new Date(a.timestamp).toLocaleDateString("en-US", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" })}</span>
                        </div>
                      </div>
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

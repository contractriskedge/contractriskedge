"use client";

import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  X, Shield, AlertTriangle, FileText, Building2, ClipboardCheck,
  Clock, Brain, BookOpen, CheckCircle, XCircle, ChevronRight,
  ExternalLink, User, Calendar,
} from "lucide-react";
import type { ComplianceFinding, ComplianceDetail } from "./types";

const emptyComplianceDetail: ComplianceDetail = {
  overview: {
    regulation: "",
    score: 0,
    status: "pending",
    lastAssessed: "",
    jurisdiction: "",
    contractsInScope: 0,
    vendorsInScope: 0,
  },
  regulatoryMapping: [],
  impactedContracts: [],
  remediationActions: [],
  auditTrail: [],
  aiRecommendations: [],
  relatedPolicies: [],
  evidence: [],
};

interface ComplianceDetailDrawerProps {
  finding: ComplianceFinding | null;
  isOpen: boolean;
  onClose: () => void;
}

type DetailTab = "overview" | "mapping" | "contracts" | "remediation" | "audit" | "ai" | "policies" | "evidence";

export function ComplianceDetailDrawer({ finding, isOpen, onClose }: ComplianceDetailDrawerProps) {
  const [activeTab, setActiveTab] = useState<DetailTab>("overview");
  const data = emptyComplianceDetail;

  if (!finding) return null;

  const tabs: { id: DetailTab; label: string; icon: React.ReactNode }[] = [
    { id: "overview", label: "Overview", icon: <Shield className="w-3 h-3" /> },
    { id: "mapping", label: "Mapping", icon: <FileText className="w-3 h-3" /> },
    { id: "contracts", label: "Contracts", icon: <FileText className="w-3 h-3" /> },
    { id: "remediation", label: "Remediation", icon: <ClipboardCheck className="w-3 h-3" /> },
    { id: "audit", label: "Audit Trail", icon: <Clock className="w-3 h-3" /> },
    { id: "ai", label: "AI Recs", icon: <Brain className="w-3 h-3" /> },
    { id: "policies", label: "Policies", icon: <BookOpen className="w-3 h-3" /> },
    { id: "evidence", label: "Evidence", icon: <CheckCircle className="w-3 h-3" /> },
  ];

  const severityColors: Record<string, string> = {
    critical: "text-red-600 bg-red-50 dark:bg-red-900/20 dark:text-red-400",
    high: "text-orange-600 bg-orange-50 dark:bg-orange-900/20 dark:text-orange-400",
    medium: "text-amber-600 bg-amber-50 dark:bg-amber-900/20 dark:text-amber-400",
    low: "text-blue-600 bg-blue-50 dark:bg-blue-900/20 dark:text-blue-400",
    info: "text-gray-600 bg-gray-50 dark:bg-navy-700 dark:text-gray-400",
  };

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
            {/* Header */}
            <div className="px-4 py-3 border-b border-gray-200 dark:border-navy-700 flex items-center justify-between">
              <div className="flex items-center gap-2 min-w-0">
                <div className={`w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0 ${severityColors[finding.severity]}`}>
                  <AlertTriangle className="w-3.5 h-3.5" />
                </div>
                <div className="min-w-0">
                  <h3 className="text-sm font-semibold text-navy-900 dark:text-white truncate">{finding.title}</h3>
                  <p className="text-[9px] text-gray-500">{finding.regulationName} · {finding.category}</p>
                </div>
              </div>
              <button onClick={onClose} className="p-1 hover:bg-gray-100 dark:hover:bg-navy-700 rounded transition-colors flex-shrink-0"><X className="w-4 h-4 text-gray-400" /></button>
            </div>

            {/* Tabs */}
            <div className="flex border-b border-gray-200 dark:border-navy-700 overflow-x-auto">
              {tabs.map(tab => (
                <button key={tab.id} onClick={() => setActiveTab(tab.id)}
                  className={`flex items-center gap-1 px-2 py-2 text-[8px] font-medium whitespace-nowrap transition-colors border-b-2 ${
                    activeTab === tab.id ? "text-gold-600 border-gold-500" : "text-gray-500 border-transparent hover:text-navy-700"
                  }`}>
                  {tab.icon}{tab.label}
                </button>
              ))}
            </div>

            {/* Content */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4">
              {activeTab === "overview" && (
                <div className="space-y-4">
                  <p className="text-xs text-gray-600 dark:text-gray-300 leading-relaxed">{finding.description}</p>
                  <div className="grid grid-cols-2 gap-3">
                    {[
                      { label: "Severity", value: finding.severity, badge: true },
                      { label: "Status", value: finding.status.replace("_", " ") },
                      { label: "Regulation", value: finding.regulationName },
                      { label: "AI Confidence", value: `${finding.aiConfidence}%` },
                      { label: "Assignee", value: finding.assignee },
                      { label: "Due Date", value: new Date(finding.dueDate).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" }) },
                      { label: "Impacted Contracts", value: finding.impactedContracts.toString() },
                      { label: "Impacted Vendors", value: finding.impactedVendors.toString() },
                    ].map(item => (
                      <div key={item.label} className="bg-gray-50 dark:bg-navy-900 rounded-lg p-2.5">
                        <span className="text-[8px] text-gray-500 uppercase tracking-wider">{item.label}</span>
                        <p className={`text-xs font-semibold mt-0.5 ${item.badge ? severityColors[item.value] || "text-navy-900 dark:text-white" : "text-navy-900 dark:text-white"}`}>{item.value}</p>
                      </div>
                    ))}
                  </div>
                  {/* Remediation Steps */}
                  <div>
                    <h4 className="text-[9px] font-semibold text-gray-500 uppercase tracking-wider mb-1">Remediation Steps</h4>
                    <ol className="space-y-1">
                      {finding.remediationSteps.map((step, i) => (
                        <li key={i} className="flex items-start gap-2 text-[10px] text-gray-600 dark:text-gray-300">
                          <span className="w-4 h-4 rounded-full bg-gold-100 dark:bg-gold-900/30 text-gold-600 text-[8px] font-bold flex items-center justify-center flex-shrink-0 mt-0.5">{i + 1}</span>
                          {step}
                        </li>
                      ))}
                    </ol>
                  </div>
                  <div className="text-[9px] text-gray-400">Reference: {finding.regulatoryReference}</div>
                </div>
              )}

              {activeTab === "mapping" && (
                <div className="space-y-1.5">
                  {data.regulatoryMapping.map((m, i) => (
                    <div key={i} className="flex items-center justify-between border border-gray-200 dark:border-navy-600 rounded-lg p-2.5">
                      <div className="flex-1 min-w-0">
                        <span className="text-[10px] font-medium text-navy-900 dark:text-white truncate block">{m.requirement}</span>
                        <span className="text-[8px] text-gray-400 truncate block mt-0.5">{m.evidence}</span>
                      </div>
                      <span className={`text-[8px] px-1.5 py-0.5 rounded-full font-medium capitalize ml-2 flex-shrink-0 ${
                        m.status === "compliant" ? "bg-green-100 text-green-700" : m.status === "non_compliant" ? "bg-red-100 text-red-700" : "bg-amber-100 text-amber-700"
                      }`}>{m.status.replace("_", " ")}</span>
                    </div>
                  ))}
                </div>
              )}

              {activeTab === "contracts" && (
                <div className="space-y-1.5">
                  {data.impactedContracts.map(c => (
                    <div key={c.id} className="flex items-center justify-between border border-gray-200 dark:border-navy-600 rounded-lg p-2.5">
                      <div>
                        <span className="text-[10px] font-medium text-navy-900 dark:text-white">{c.title}</span>
                        <span className="text-[8px] text-gray-400 ml-2">{c.clause}</span>
                      </div>
                      <span className={`text-[8px] px-1.5 py-0.5 rounded-full font-medium capitalize ${
                        c.risk === "critical" ? "bg-red-100 text-red-700" : c.risk === "high" ? "bg-orange-100 text-orange-700" : "bg-amber-100 text-amber-700"
                      }`}>{c.risk}</span>
                    </div>
                  ))}
                </div>
              )}

              {activeTab === "remediation" && (
                <div className="space-y-1.5">
                  {data.remediationActions.map(task => (
                    <div key={task.id} className="border border-gray-200 dark:border-navy-600 rounded-lg p-2.5">
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-[10px] font-medium text-navy-900 dark:text-white">{task.title}</span>
                        <span className={`text-[8px] px-1.5 py-0.5 rounded-full font-medium capitalize ${
                          task.status === "overdue" ? "bg-red-100 text-red-700" : task.status === "in_progress" ? "bg-blue-100 text-blue-700" : task.status === "open" ? "bg-amber-100 text-amber-700" : "bg-green-100 text-green-700"
                        }`}>{task.status.replace("_", " ")}</span>
                      </div>
                      <div className="flex items-center gap-2 text-[8px] text-gray-400">
                        <User className="w-2.5 h-2.5" /><span>{task.assignee}</span>
                        <Calendar className="w-2.5 h-2.5 ml-1" /><span>{new Date(task.dueDate).toLocaleDateString("en-US", { month: "short", day: "numeric" })}</span>
                        {task.isOverdue && <span className="text-red-500 font-medium">OVERDUE</span>}
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {activeTab === "audit" && (
                <div className="space-y-3">
                  {data.auditTrail.map((a, i) => (
                    <div key={i} className="flex gap-3">
                      <div className="flex flex-col items-center">
                        <div className="w-5 h-5 rounded-full bg-navy-100 dark:bg-navy-700 flex items-center justify-center"><Clock className="w-2.5 h-2.5 text-navy-500" /></div>
                        {i < data.auditTrail.length - 1 && <div className="w-px flex-1 bg-gray-200 dark:bg-navy-700" />}
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

              {activeTab === "ai" && (
                <div className="space-y-2">
                  {data.aiRecommendations.map(rec => (
                    <div key={rec.id} className={`border rounded-lg p-3 ${
                      rec.severity === "critical" ? "border-red-200 bg-red-50/50 dark:border-red-900/50 dark:bg-red-900/10" :
                      rec.severity === "warning" ? "border-amber-200 bg-amber-50/50 dark:border-amber-900/50 dark:bg-amber-900/10" :
                      "border-blue-200 bg-blue-50/50 dark:border-blue-900/50 dark:bg-blue-900/10"
                    }`}>
                      <div className="flex items-center gap-1.5 mb-1">
                        <Brain className="w-3 h-3 text-purple-500" />
                        <span className="text-[10px] font-semibold text-navy-900 dark:text-white">{rec.title}</span>
                        <span className="text-[7px] text-gray-400">{rec.confidence}%</span>
                      </div>
                      <p className="text-[9px] text-gray-600 dark:text-gray-300">{rec.remediationSuggestion}</p>
                    </div>
                  ))}
                </div>
              )}

              {activeTab === "policies" && (
                <div className="space-y-1.5">
                  {data.relatedPolicies.map(p => (
                    <div key={p.id} className="border border-gray-200 dark:border-navy-600 rounded-lg p-2.5">
                      <div className="flex items-center gap-2 mb-1">
                        <BookOpen className="w-3 h-3 text-gold-500" />
                        <span className="text-[10px] font-medium text-navy-900 dark:text-white">{p.title}</span>
                        <span className="text-[7px] text-gray-400">v{p.version}</span>
                      </div>
                      <p className="text-[8px] text-gray-500">{p.description}</p>
                    </div>
                  ))}
                </div>
              )}

              {activeTab === "evidence" && (
                <div className="space-y-1.5">
                  {data.evidence.map(ev => (
                    <div key={ev.id} className="flex items-center justify-between border border-gray-200 dark:border-navy-600 rounded-lg p-2.5">
                      <div className="flex items-center gap-2">
                        <FileText className="w-3 h-3 text-gray-400" />
                        <div>
                          <span className="text-[10px] font-medium text-navy-900 dark:text-white">{ev.name}</span>
                          <span className="text-[8px] text-gray-400 ml-2">{ev.type}</span>
                        </div>
                      </div>
                      <span className={`text-[8px] px-1.5 py-0.5 rounded-full font-medium capitalize ${
                        ev.status === "approved" ? "bg-green-100 text-green-700" : ev.status === "draft" ? "bg-amber-100 text-amber-700" : "bg-gray-100 text-gray-500"
                      }`}>{ev.status}</span>
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

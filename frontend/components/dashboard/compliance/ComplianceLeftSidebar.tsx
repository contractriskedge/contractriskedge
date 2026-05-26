"use client";

import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Shield, AlertTriangle, Heart, CheckCircle, Award, FileText,
  CreditCard, Gavel, ChevronRight, ChevronDown, Search,
  ListChecks, Building2, ClipboardCheck, BookOpen,
} from "lucide-react";
import type { Regulation, RemediationTask, ComplianceAudit, VendorCompliance, CompliancePolicy } from "./types";

// ── Regulation Item ──────────────────────────────────────────────────────

const regIcons: Record<string, React.ReactNode> = {
  Shield: <Shield className="w-3 h-3" />, Heart: <Heart className="w-3 h-3" />,
  CheckCircle: <CheckCircle className="w-3 h-3" />, Award: <Award className="w-3 h-3" />,
  FileText: <FileText className="w-3 h-3" />, CreditCard: <CreditCard className="w-3 h-3" />,
};

function RegulationItem({ reg, isActive, onClick }: { reg: Regulation; isActive: boolean; onClick: () => void }) {
  const scoreColor = reg.complianceScore >= 85 ? "text-green-600" : reg.complianceScore >= 70 ? "text-amber-600" : "text-red-600";
  return (
    <button onClick={onClick} className={`w-full text-left px-2 py-1.5 rounded-lg flex items-center gap-2 transition-colors ${
      isActive ? "bg-navy-50 dark:bg-navy-700/50 border border-navy-200 dark:border-navy-600" : "hover:bg-gray-50 dark:hover:bg-navy-800/50 border border-transparent"
    }`}>
      <div className={`w-6 h-6 rounded-lg flex items-center justify-center flex-shrink-0 ${
        reg.status === "compliant" ? "bg-green-100 text-green-600" : reg.status === "non_compliant" ? "bg-red-100 text-red-600" : "bg-amber-100 text-amber-600"
      }`}>{regIcons[reg.icon] || <Shield className="w-3 h-3" />}</div>
      <div className="flex-1 min-w-0">
        <span className="text-[10px] font-medium text-navy-900 dark:text-white truncate block">{reg.shortName}</span>
        <span className="text-[8px] text-gray-400 truncate block">{reg.jurisdiction}</span>
      </div>
      <span className={`text-[10px] font-bold tabular-nums ${scoreColor}`}>{reg.complianceScore}%</span>
    </button>
  );
}

// ── Remediation Task Item ────────────────────────────────────────────────

function RemediationTaskItem({ task }: { task: RemediationTask }) {
  const priorityColors: Record<string, string> = {
    critical: "border-l-red-500 bg-red-50/30 dark:bg-red-900/10",
    high: "border-l-orange-500 bg-orange-50/30 dark:bg-orange-900/10",
    medium: "border-l-amber-500 bg-amber-50/30 dark:bg-amber-900/10",
    low: "border-l-blue-500 bg-blue-50/30 dark:bg-blue-900/10",
  };
  return (
    <div className={`border-l-2 pl-2 py-1.5 ${priorityColors[task.priority]} rounded-r`}>
      <div className="flex items-center justify-between">
        <span className="text-[9px] font-medium text-navy-900 dark:text-white truncate flex-1">{task.title}</span>
        <span className={`text-[8px] px-1 py-0.5 rounded font-medium ${
          task.status === "overdue" ? "bg-red-100 text-red-600" : task.status === "in_progress" ? "bg-blue-100 text-blue-600" : "bg-gray-100 text-gray-500"
        }`}>{task.status.replace("_", " ")}</span>
      </div>
      <div className="flex items-center gap-1.5 mt-0.5 text-[7px] text-gray-400">
        <span>{task.assignee}</span>
        {task.isOverdue && <span className="text-red-500">OVERDUE</span>}
        {task.escalationLevel > 0 && <span className="text-amber-500">L{task.escalationLevel}</span>}
      </div>
    </div>
  );
}

// ── Left Sidebar ─────────────────────────────────────────────────────────

interface ComplianceLeftSidebarProps {
  regulations: Regulation[];
  tasks: RemediationTask[];
  audits: ComplianceAudit[];
  vendors: VendorCompliance[];
  policies: CompliancePolicy[];
  activeRegulation: string | null;
  onRegulationSelect: (id: string) => void;
}

type LeftTab = "regulations" | "remediation" | "audits" | "vendors" | "policies";

export function ComplianceLeftSidebar({
  regulations, tasks, audits, vendors, policies, activeRegulation, onRegulationSelect,
}: ComplianceLeftSidebarProps) {
  const [activeTab, setActiveTab] = useState<LeftTab>("regulations");

  const tabs: { id: LeftTab; label: string; icon: React.ReactNode; count?: number }[] = [
    { id: "regulations", label: "Regulations", icon: <Shield className="w-3 h-3" />, count: regulations.length },
    { id: "remediation", label: "Remediation", icon: <ListChecks className="w-3 h-3" />, count: tasks.filter(t => t.status !== "resolved").length },
    { id: "audits", label: "Audits", icon: <ClipboardCheck className="w-3 h-3" />, count: audits.filter(a => a.status === "in_progress" || a.status === "scheduled").length },
    { id: "vendors", label: "Vendors", icon: <Building2 className="w-3 h-3" />, count: vendors.length },
    { id: "policies", label: "Policies", icon: <BookOpen className="w-3 h-3" /> },
  ];

  return (
    <div className="w-60 flex-shrink-0 bg-white dark:bg-navy-800 border-r border-gray-200 dark:border-navy-700 flex flex-col h-full">
      <div className="flex border-b border-gray-200 dark:border-navy-700 overflow-x-auto">
        {tabs.map(tab => (
          <button key={tab.id} onClick={() => setActiveTab(tab.id)}
            className={`flex-1 flex items-center justify-center gap-1 py-2 text-[8px] font-medium transition-colors relative whitespace-nowrap ${
              activeTab === tab.id ? "text-gold-600 dark:text-gold-400" : "text-gray-500 dark:text-gray-400 hover:text-navy-700"
            }`}>
            {tab.icon}<span>{tab.label}</span>
            {tab.count !== undefined && tab.count > 0 && (
              <span className={`text-[7px] px-1 py-0.5 rounded-full ${activeTab === tab.id ? "bg-gold-100 text-gold-700" : "bg-gray-100 text-gray-500"}`}>{tab.count}</span>
            )}
            {activeTab === tab.id && <motion.div layoutId="comp-left-tab" className="absolute bottom-0 left-0 right-0 h-0.5 bg-gold-500" />}
          </button>
        ))}
      </div>

      <div className="flex-1 overflow-y-auto p-1.5 space-y-0.5">
        {activeTab === "regulations" && regulations.map(r => (
          <RegulationItem key={r.id} reg={r} isActive={activeRegulation === r.id} onClick={() => onRegulationSelect(r.id)} />
        ))}

        {activeTab === "remediation" && (
          tasks.length === 0 ? <div className="text-center py-8 text-gray-400 text-[10px]">No tasks</div> :
          tasks.map(t => <RemediationTaskItem key={t.id} task={t} />)
        )}

        {activeTab === "audits" && audits.map(a => (
          <div key={a.id} className="px-2 py-1.5 hover:bg-gray-50 dark:hover:bg-navy-700 rounded-lg transition-colors">
            <div className="flex items-center gap-1.5">
              <div className={`w-2 h-2 rounded-full ${
                a.status === "completed" ? "bg-green-500" : a.status === "in_progress" ? "bg-blue-500 animate-pulse" :
                a.status === "scheduled" ? "bg-amber-400" : "bg-gray-400"
              }`} />
              <span className="text-[9px] font-medium text-navy-900 dark:text-white truncate">{a.regulationName}</span>
            </div>
            <div className="flex items-center gap-2 text-[7px] text-gray-400 mt-0.5 ml-3.5">
              <span className="capitalize">{a.status.replace("_", " ")}</span>
              <span>·</span>
              <span>{a.readinessScore}% ready</span>
              <span>·</span>
              <span>{a.findings} findings</span>
            </div>
          </div>
        ))}

        {activeTab === "vendors" && vendors.map(v => (
          <div key={v.id} className="px-2 py-1.5 hover:bg-gray-50 dark:hover:bg-navy-700 rounded-lg transition-colors">
            <div className="flex items-center justify-between">
              <span className="text-[9px] font-medium text-navy-900 dark:text-white truncate flex-1">{v.vendorName}</span>
              <span className={`text-[8px] font-bold tabular-nums ${
                v.overallScore >= 80 ? "text-green-600" : v.overallScore >= 60 ? "text-amber-600" : "text-red-600"
              }`}>{v.overallScore}%</span>
            </div>
            <div className="flex items-center gap-1 text-[7px] text-gray-400 mt-0.5">
              <span>{v.certifications.length} certs</span>
              <span>·</span>
              <span>{v.contractCount} contracts</span>
              <span>·</span>
              <span className={`capitalize ${
                v.riskLevel === "critical" ? "text-red-500" : v.riskLevel === "high" ? "text-orange-500" : "text-gray-400"
              }`}>{v.riskLevel} risk</span>
            </div>
          </div>
        ))}

        {activeTab === "policies" && policies.map(p => (
          <div key={p.id} className="px-2 py-1.5 hover:bg-gray-50 dark:hover:bg-navy-700 rounded-lg transition-colors">
            <div className="flex items-center gap-1.5">
              <BookOpen className="w-3 h-3 text-gold-400 flex-shrink-0" />
              <div className="flex-1 min-w-0">
                <span className="text-[9px] font-medium text-navy-900 dark:text-white truncate block">{p.title}</span>
                <span className="text-[7px] text-gray-400">v{p.version} · {p.acknowledgements}/{p.totalRequired} acknowledged</span>
              </div>
              <span className={`text-[7px] px-1 py-0.5 rounded font-medium capitalize ${
                p.status === "active" ? "bg-green-100 text-green-600" : p.status === "draft" ? "bg-amber-100 text-amber-600" : "bg-gray-100 text-gray-500"
              }`}>{p.status}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

"use client";

import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X, ClipboardCheck, Clock, AlertTriangle, DollarSign, Activity, Shield, FileText, User, Calendar, Brain, Link } from "lucide-react";
import type { ObligationRecord } from "./types";
import { RISK_BG, RISK_TEXT, RISK_BG_LIGHT, STATUS_CONFIG, OBLIGATION_TYPES } from "./types";

type TabId = "overview" | "timeline" | "sla" | "financial" | "compliance" | "ai" | "activity" | "related";

function TabBtn({ label, icon, active, onClick }: { label: string; icon: React.ReactNode; active: boolean; onClick: () => void }) {
  return (
    <button onClick={onClick} className={`flex items-center gap-1 px-2.5 py-1.5 text-[10px] font-medium rounded-md whitespace-nowrap transition-all ${active ? "bg-navy-700 text-white shadow-sm" : "text-gray-500 hover:text-gray-700 hover:bg-gray-100"}`}>
      {icon}{label}
    </button>
  );
}

interface DrawerProps {
  obligation: ObligationRecord | null;
  onClose: () => void;
}

export function ObligationDetailDrawer({ obligation, onClose }: DrawerProps) {
  const [tab, setTab] = useState<TabId>("overview");

  return (
    <AnimatePresence>
      {obligation && (
        <>
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="fixed inset-0 bg-black/20 z-40" onClick={onClose} />
          <motion.div initial={{ opacity: 0, x: 380 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: 380 }}
            transition={{ type: "spring", damping: 25, stiffness: 250 }}
            className="fixed right-0 top-0 bottom-0 w-[480px] bg-white border-l border-gray-200 shadow-xl z-50 flex flex-col">
            <div className="flex items-center justify-between px-5 py-4 border-b border-gray-200">
              <div className="flex items-center gap-2 min-w-0">
                <div className="w-8 h-8 rounded-lg bg-navy-700 flex items-center justify-center"><ClipboardCheck className="w-4 h-4 text-white" /></div>
                <div className="min-w-0"><h3 className="text-sm font-semibold text-navy-900 truncate">{obligation.name}</h3><p className="text-[10px] text-gray-500">{obligation.id} • {obligation.vendor}</p></div>
              </div>
              <button onClick={onClose} className="p-1 rounded hover:bg-gray-100 text-gray-400"><X className="w-4 h-4" /></button>
            </div>
            <div className="px-4 py-2 border-b border-gray-100 flex gap-1 overflow-x-auto">
              <TabBtn label="Overview" icon={<ClipboardCheck className="w-3 h-3" />} active={tab === "overview"} onClick={() => setTab("overview")} />
              <TabBtn label="Timeline" icon={<Clock className="w-3 h-3" />} active={tab === "timeline"} onClick={() => setTab("timeline")} />
              <TabBtn label="SLA" icon={<Activity className="w-3 h-3" />} active={tab === "sla"} onClick={() => setTab("sla")} />
              <TabBtn label="Financial" icon={<DollarSign className="w-3 h-3" />} active={tab === "financial"} onClick={() => setTab("financial")} />
              <TabBtn label="Compliance" icon={<Shield className="w-3 h-3" />} active={tab === "compliance"} onClick={() => setTab("compliance")} />
              <TabBtn label="AI" icon={<Brain className="w-3 h-3" />} active={tab === "ai"} onClick={() => setTab("ai")} />
              <TabBtn label="Activity" icon={<Activity className="w-3 h-3" />} active={tab === "activity"} onClick={() => setTab("activity")} />
            </div>
            <div className="flex-1 overflow-y-auto p-5 space-y-4">
              {tab === "overview" && <OverviewTab o={obligation} />}
              {tab === "timeline" && <TimelineTab />}
              {tab === "sla" && <SlaTab o={obligation} />}
              {tab === "financial" && <FinancialTab o={obligation} />}
              {tab === "compliance" && <ComplianceTab />}
              {tab === "ai" && <AiTab o={obligation} />}
              {tab === "activity" && <ActivityTab />}
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}

function OverviewTab({ o }: { o: ObligationRecord }) {
  const sc = STATUS_CONFIG[o.status];
  const MetaRow = ({ label, value, icon }: { label: string; value: string | React.ReactNode; icon?: React.ReactNode }) => (
    <div className="flex items-center justify-between py-1.5"><span className="text-[11px] text-gray-500 flex items-center gap-1.5">{icon}{label}</span><span className="text-[11px] font-medium text-gray-800">{value}</span></div>
  );
  return (
    <div className="space-y-4">
      <div className="p-3 bg-navy-50 rounded-lg border border-navy-100">
        <p className="text-[10px] font-semibold text-navy-700 uppercase mb-1">Description</p>
        <p className="text-[11px] text-gray-700 leading-relaxed">{o.description}</p>
      </div>
      <div className="bg-gray-50 rounded-lg p-3 space-y-0.5 divide-y divide-gray-100">
        <MetaRow label="Status" value={<span className={`text-[10px] font-medium px-1.5 py-0.5 rounded-full ${sc.bg} ${sc.color}`}>{sc.label}</span>} />
        <MetaRow label="Type" value={OBLIGATION_TYPES.find((t) => t.id === o.type)?.label || o.type} />
        <MetaRow label="Contract" value={o.contractName} icon={<FileText className="w-3 h-3" />} />
        <MetaRow label="Vendor" value={o.vendor} />
        <MetaRow label="Owner" value={o.owner} icon={<User className="w-3 h-3" />} />
        <MetaRow label="Assignee" value={o.assignee} />
        <MetaRow label="Due Date" value={o.dueDate} icon={<Calendar className="w-3 h-3" />} />
        {o.completedDate && <MetaRow label="Completed" value={o.completedDate} icon={<Calendar className="w-3 h-3" />} />}
        <MetaRow label="Risk Score" value={<RiskBadge score={o.riskScore} />} />
        <MetaRow label="Financial Impact" value={`$${o.financialImpact}M`} icon={<DollarSign className="w-3 h-3" />} />
        <MetaRow label="Clause Reference" value={o.clauseReference} />
        <MetaRow label="Department" value={o.department} />
        <MetaRow label="Business Unit" value={o.businessUnit} />
        <MetaRow label="Geography" value={o.geography} />
        <MetaRow label="Escalation Level" value={o.escalationLevel > 0 ? `Level ${o.escalationLevel}` : "None"} />
        <MetaRow label="Attachments" value={o.attachments.toString()} />
      </div>
    </div>
  );
}

function TimelineTab() {
  const events = [
    { event: "Obligation created", date: "2026-01-15", by: "System" },
    { event: "Assigned to owner", date: "2026-01-16", by: "Alice Chen" },
    { event: "Reminder sent", date: "2026-05-01", by: "System" },
    { event: "Status updated to In Progress", date: "2026-05-10", by: "Bob Martinez" },
    { event: "Escalated to Level 1", date: "2026-05-14", by: "System" },
  ];
  return (
    <div className="space-y-2">
      <p className="text-[10px] font-semibold text-gray-500 uppercase mb-2">Obligation Timeline</p>
      {events.map((e, i) => (
        <div key={i} className="flex items-start gap-2.5">
          <div className="flex flex-col items-center"><div className="w-2 h-2 rounded-full bg-navy-500" />{i < events.length - 1 && <div className="w-px h-5 bg-gray-200" />}</div>
          <div className="pb-1"><p className="text-[11px] font-medium text-gray-800">{e.event}</p><p className="text-[9px] text-gray-400">{e.by} • {e.date}</p></div>
        </div>
      ))}
    </div>
  );
}

function SlaTab({ o }: { o: ObligationRecord }) {
  return (
    <div className="space-y-3">
      <div className={`p-3 rounded-lg border ${o.slaStatus === "breached" ? "bg-red-50 border-red-200" : o.slaStatus === "at_risk" ? "bg-orange-50 border-orange-200" : "bg-green-50 border-green-200"}`}>
        <div className="flex items-center justify-between">
          <span className="text-[10px] font-semibold uppercase">{o.slaStatus === "breached" ? "SLA Breached" : o.slaStatus === "at_risk" ? "At Risk" : "On Track"}</span>
          <span className="text-lg font-bold">{o.slaStatus === "breached" ? `${-o.slaRemaining}h breached` : `${o.slaRemaining}h remaining`}</span>
        </div>
      </div>
      <div className="space-y-1.5">
        {[
          { label: "SLA Target", value: "99.9% uptime" },
          { label: "Current Performance", value: "98.5%" },
          { label: "Breach Count", value: "3" },
          { label: "Escalation Level", value: `Level ${o.escalationLevel}` },
        ].map((item) => (
          <div key={item.label} className="flex justify-between text-xs py-1"><span className="text-gray-500">{item.label}</span><span className="font-medium text-gray-800">{item.value}</span></div>
        ))}
      </div>
    </div>
  );
}

function FinancialTab({ o }: { o: ObligationRecord }) {
  return (
    <div className="space-y-3">
      <div className="p-4 bg-gray-50 rounded-lg text-center">
        <p className="text-[10px] text-gray-500 uppercase font-semibold">Financial Impact</p>
        <p className="text-2xl font-bold text-navy-900 mt-1">${o.financialImpact}M</p>
        <p className="text-[10px] text-gray-400 mt-0.5">{o.currency}</p>
      </div>
      <div className="space-y-1.5">
        {[
          { label: "Overdue Amount", value: `$${(o.financialImpact * 0.4).toFixed(1)}M` },
          { label: "At Risk Amount", value: `$${(o.financialImpact * 0.3).toFixed(1)}M` },
          { label: "Recovered Amount", value: `$${(o.financialImpact * 0.2).toFixed(1)}M` },
          { label: "Penalty Exposure", value: `$${(o.financialImpact * 0.1).toFixed(1)}M` },
        ].map((item) => (
          <div key={item.label} className="flex justify-between text-xs py-1"><span className="text-gray-500">{item.label}</span><span className="font-medium text-gray-800">{item.value}</span></div>
        ))}
      </div>
    </div>
  );
}

function ComplianceTab() {
  return (
    <div className="space-y-2">
      <p className="text-[10px] font-semibold text-gray-500 uppercase mb-2">Compliance Requirements</p>
      {[
        { req: "GDPR Data Processing", status: "Compliant" },
        { req: "SOC2 Type II", status: "In Progress" },
        { req: "Insurance Certificate", status: "Overdue" },
        { req: "Security Assessment", status: "Compliant" },
      ].map((item) => (
        <div key={item.req} className="flex items-center gap-2.5 p-2.5 bg-white border border-gray-100 rounded-lg">
          <Shield className="w-3.5 h-3.5 text-gray-400 flex-shrink-0" />
          <div className="flex-1"><p className="text-[11px] font-medium text-gray-800">{item.req}</p></div>
          <span className={`text-[9px] font-medium px-1.5 py-0.5 rounded-full ${item.status === "Compliant" ? "bg-green-50 text-green-700" : item.status === "In Progress" ? "bg-blue-50 text-blue-700" : "bg-red-50 text-red-700"}`}>{item.status}</span>
        </div>
      ))}
    </div>
  );
}

function AiTab({ o }: { o: ObligationRecord }) {
  return (
    <div className="space-y-3">
      <div className="p-3 bg-purple-50 rounded-lg border border-purple-100">
        <div className="flex items-center gap-1.5 mb-1.5"><Brain className="w-3.5 h-3.5 text-purple-600" /><span className="text-[10px] font-semibold text-purple-700 uppercase">AI Risk Assessment</span></div>
        <div className="space-y-2">
          {[
            { title: "Risk Prediction", desc: `AI predicts ${o.aiRiskPrediction}% probability of this obligation becoming overdue or breached.` },
            { title: "Recommended Action", desc: o.status === "overdue" ? "Escalate immediately. Send formal notice to vendor." : "Set reminder 7 days before due date. Monitor progress weekly." },
            { title: "Confidence", desc: `AI confidence: ${o.aiConfidence}%. Based on ${o.riskScore}/10 risk score and historical patterns.` },
            { title: "Impact Analysis", desc: `Financial impact of non-compliance: $${o.financialImpact}M. ${o.escalationLevel > 0 ? `Currently at escalation level ${o.escalationLevel}.` : "No escalation triggered yet."}` },
          ].map((item) => (
            <div key={item.title} className="p-2 bg-white rounded border border-purple-100">
              <p className="text-[10px] font-semibold text-navy-700 uppercase mb-0.5">{item.title}</p>
              <p className="text-[11px] text-gray-600">{item.desc}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function ActivityTab() {
  const activities = [
    { action: "Obligation created", by: "System", time: "2026-01-15" },
    { action: "Reminder sent", by: "System", time: "2026-05-01" },
    { action: "Status updated", by: "Bob Martinez", time: "2026-05-10" },
    { action: "Comment added", by: "Alice Chen", time: "2026-05-12" },
    { action: "Escalated to Level 1", by: "System", time: "2026-05-14" },
  ];
  return (
    <div className="space-y-1.5">
      <p className="text-[10px] font-semibold text-gray-500 uppercase mb-2">Activity History</p>
      {activities.map((a, i) => (
        <div key={i} className="flex items-start gap-2 p-2 bg-white border border-gray-100 rounded-lg">
          <div className="w-2 h-2 rounded-full bg-navy-400 mt-1.5 flex-shrink-0" />
          <div><p className="text-[11px] text-gray-800">{a.action}</p><p className="text-[9px] text-gray-400">{a.by} • {a.time}</p></div>
        </div>
      ))}
    </div>
  );
}

function RiskBadge({ score }: { score: number }) {
  const level = score >= 8 ? "critical" : score >= 6 ? "high" : score >= 4 ? "medium" : "low";
  return <span className={`inline-flex items-center gap-1 text-[10px] font-bold px-1.5 py-0.5 rounded-full ${RISK_BG_LIGHT[level]} ${RISK_TEXT[level]}`}><span className={`w-1.5 h-1.5 rounded-full ${RISK_BG[level]}`} />{score}/10</span>;
}

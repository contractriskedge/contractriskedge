"use client";

import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X, Clock, AlertTriangle, User, MessageSquare, Paperclip, CheckCircle, ArrowUpCircle, Brain, Scale, FileText, Calendar } from "lucide-react";
import type { WorkflowItem, WorkflowStageType } from "./types";
import { WORKFLOW_STAGES, PRIORITY_CONFIG, RISK_BG, RISK_BG_LIGHT, RISK_TEXT } from "./types";

type TabId = "overview" | "history" | "sla" | "ai" | "comments" | "audit" | "documents" | "automation";

function TabBtn({ label, icon, active, onClick }: { label: string; icon: React.ReactNode; active: boolean; onClick: () => void }) {
  return (
    <button onClick={onClick} className={`flex items-center gap-1 px-2.5 py-1.5 text-[10px] font-medium rounded-md whitespace-nowrap transition-all ${active ? "bg-navy-700 text-white shadow-sm" : "text-gray-500 hover:text-gray-700 hover:bg-gray-100"}`}>
      {icon}{label}
    </button>
  );
}

interface DrawerProps {
  workflow: WorkflowItem | null;
  onClose: () => void;
}

export function WorkflowDetailDrawer({ workflow, onClose }: DrawerProps) {
  const [tab, setTab] = useState<TabId>("overview");

  return (
    <AnimatePresence>
      {workflow && (
        <>
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="fixed inset-0 bg-black/20 z-40" onClick={onClose} />
          <motion.div initial={{ opacity: 0, x: 380 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: 380 }}
            transition={{ type: "spring", damping: 25, stiffness: 250 }}
            className="fixed right-0 top-0 bottom-0 w-[480px] bg-white border-l border-gray-200 shadow-xl z-50 flex flex-col">
            <div className="flex items-center justify-between px-5 py-4 border-b border-gray-200">
              <div className="flex items-center gap-2 min-w-0">
                <div className="w-8 h-8 rounded-lg bg-navy-700 flex items-center justify-center"><Clock className="w-4 h-4 text-white" /></div>
                <div className="min-w-0"><h3 className="text-sm font-semibold text-navy-900 truncate">{workflow.contractName}</h3><p className="text-[10px] text-gray-500">{workflow.id} • {workflow.vendor}</p></div>
              </div>
              <button onClick={onClose} className="p-1 rounded hover:bg-gray-100 text-gray-400"><X className="w-4 h-4" /></button>
            </div>
            <div className="px-4 py-2 border-b border-gray-100 flex gap-1 overflow-x-auto">
              <TabBtn label="Overview" icon={<FileText className="w-3 h-3" />} active={tab === "overview"} onClick={() => setTab("overview")} />
              <TabBtn label="History" icon={<Clock className="w-3 h-3" />} active={tab === "history"} onClick={() => setTab("history")} />
              <TabBtn label="SLA" icon={<AlertTriangle className="w-3 h-3" />} active={tab === "sla"} onClick={() => setTab("sla")} />
              <TabBtn label="AI" icon={<Brain className="w-3 h-3" />} active={tab === "ai"} onClick={() => setTab("ai")} />
              <TabBtn label="Comments" icon={<MessageSquare className="w-3 h-3" />} active={tab === "comments"} onClick={() => setTab("comments")} />
              <TabBtn label="Audit" icon={<Scale className="w-3 h-3" />} active={tab === "audit"} onClick={() => setTab("audit")} />
              <TabBtn label="Automation" icon={<ArrowUpCircle className="w-3 h-3" />} active={tab === "automation"} onClick={() => setTab("automation")} />
            </div>
            <div className="flex-1 overflow-y-auto p-5 space-y-4">
              {tab === "overview" && <OverviewTab w={workflow} />}
              {tab === "history" && <HistoryTab w={workflow} />}
              {tab === "sla" && <SlaTab w={workflow} />}
              {tab === "ai" && <AiTab w={workflow} />}
              {tab === "comments" && <CommentsTab w={workflow} />}
              {tab === "audit" && <AuditTab />}
              {tab === "automation" && <AutomationTab />}
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}

function OverviewTab({ w }: { w: WorkflowItem }) {
  const stage = WORKFLOW_STAGES.find((s) => s.id === w.currentStage);
  const pCfg = PRIORITY_CONFIG[w.priority];
  const MetaRow = ({ label, value, icon }: { label: string; value: string | React.ReactNode; icon?: React.ReactNode }) => (
    <div className="flex items-center justify-between py-1.5"><span className="text-[11px] text-gray-500 flex items-center gap-1.5">{icon}{label}</span><span className="text-[11px] font-medium text-gray-800">{value}</span></div>
  );
  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2 p-3 bg-navy-50 rounded-lg border border-navy-100">
        <Clock className="w-4 h-4 text-navy-600" />
        <div><p className="text-[10px] font-semibold text-navy-700 uppercase">Current Stage</p><p className="text-xs font-medium text-navy-900">{stage?.label || w.currentStage}</p></div>
        <div className="ml-auto flex gap-1">
          <span className={`text-[10px] font-medium px-2 py-0.5 rounded-full ${pCfg.bg} ${pCfg.color}`}>{w.priority}</span>
          {w.escalationLevel > 0 && <span className="text-[10px] font-medium px-2 py-0.5 rounded-full bg-red-50 text-red-700">L{w.escalationLevel}</span>}
        </div>
      </div>
      <div className="bg-gray-50 rounded-lg p-3 space-y-0.5 divide-y divide-gray-100">
        <MetaRow label="Contract" value={w.contractName} icon={<FileText className="w-3 h-3" />} />
        <MetaRow label="Vendor" value={w.vendor} icon={<User className="w-3 h-3" />} />
        <MetaRow label="Type" value={w.contractType} />
        <MetaRow label="Assigned To" value={w.assignedTo} icon={<User className="w-3 h-3" />} />
        <MetaRow label="Department" value={w.department} />
        <MetaRow label="Geography" value={w.geography} />
        <MetaRow label="Value" value={`$${w.value}M`} />
        <MetaRow label="Risk Score" value={`${w.riskScore}/10`} />
        <MetaRow label="Status" value={w.status.replace(/_/g, " ")} />
        <MetaRow label="Created" value={new Date(w.createdAt).toLocaleDateString()} icon={<Calendar className="w-3 h-3" />} />
        <MetaRow label="Due" value={new Date(w.dueDate).toLocaleDateString()} icon={<Calendar className="w-3 h-3" />} />
      </div>
    </div>
  );
}

function HistoryTab({ w }: { w: WorkflowItem }) {
  const events = [
    { action: "Contract uploaded to system", by: w.lastActionBy, time: w.createdAt },
    { action: "AI review completed", by: "AI System", time: new Date(Date.now() - 3600000 * 48).toISOString() },
    { action: w.lastAction, by: w.lastActionBy, time: w.lastActionDate },
    { action: "Assigned to " + w.assignedTo, by: "System", time: new Date(Date.now() - 3600000 * 12).toISOString() },
  ];
  return (
    <div className="space-y-2">
      <p className="text-[10px] font-semibold text-gray-500 uppercase mb-2">Workflow Timeline</p>
      {events.map((e, i) => (
        <div key={i} className="flex items-start gap-3">
          <div className="flex flex-col items-center"><div className="w-2.5 h-2.5 rounded-full bg-navy-500" />{i < events.length - 1 && <div className="w-px h-6 bg-gray-200" />}</div>
          <div className="pb-2"><p className="text-[11px] font-medium text-gray-800">{e.action}</p><p className="text-[9px] text-gray-400">{e.by} • {formatTime(e.time)}</p></div>
        </div>
      ))}
    </div>
  );
}

function SlaTab({ w }: { w: WorkflowItem }) {
  return (
    <div className="space-y-3">
      <div className={`p-3 rounded-lg border ${w.slaRemaining < 0 ? "bg-red-50 border-red-200" : w.slaRemaining < 24 ? "bg-orange-50 border-orange-200" : "bg-green-50 border-green-200"}`}>
        <div className="flex items-center justify-between">
          <span className="text-[10px] font-semibold uppercase">{w.slaRemaining < 0 ? "SLA Breached" : w.slaRemaining < 24 ? "At Risk" : "On Track"}</span>
          <span className="text-lg font-bold">{w.slaRemaining < 0 ? `${-w.slaRemaining}h overdue` : `${w.slaRemaining}h remaining`}</span>
        </div>
      </div>
      <div className="space-y-1.5">
        {[
          { label: "SLA Target", value: "48 hours" },
          { label: "Elapsed", value: `${48 - w.slaRemaining}h` },
          { label: "Remaining", value: `${w.slaRemaining}h` },
          { label: "Escalation Level", value: `Level ${w.escalationLevel}` },
        ].map((item) => (
          <div key={item.label} className="flex justify-between text-xs py-1"><span className="text-gray-500">{item.label}</span><span className="font-medium text-gray-800">{item.value}</span></div>
        ))}
      </div>
    </div>
  );
}

function AiTab({ w }: { w: WorkflowItem }) {
  return (
    <div className="space-y-3">
      <div className="p-3 bg-purple-50 rounded-lg border border-purple-100">
        <div className="flex items-center gap-1.5 mb-1.5"><Brain className="w-3.5 h-3.5 text-purple-600" /><span className="text-[10px] font-semibold text-purple-700 uppercase">AI Recommendation</span></div>
        <p className="text-[11px] text-gray-700 leading-relaxed">{w.aiRecommendation}</p>
        <div className="mt-2 flex items-center gap-2">
          <span className="text-[10px] font-medium text-purple-600">Confidence: {w.aiConfidence}%</span>
          <span className="text-[9px] text-gray-400">Based on {w.riskScore}/10 risk score</span>
        </div>
      </div>
      <div className="space-y-2">
        {[
          { title: "Suggested Route", desc: w.riskScore >= 7 ? "Route to legal review — high risk detected" : "Standard approval path" },
          { title: "Auto-Assignment", desc: `Recommended assignee: ${w.assignedTo}` },
          { title: "Priority Assessment", desc: `AI assessed priority as ${w.priority} based on risk and value` },
          { title: "SLA Prediction", desc: w.slaRemaining < 0 ? "SLA already breached — expedite required" : `Predicted completion within SLA: ${w.slaRemaining > 24 ? "Yes" : "At risk"}` },
        ].map((item) => (
          <div key={item.title} className="p-2 bg-white border border-gray-100 rounded-lg">
            <p className="text-[10px] font-semibold text-navy-700 uppercase mb-0.5">{item.title}</p>
            <p className="text-[11px] text-gray-600">{item.desc}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

function CommentsTab({ w }: { w: WorkflowItem }) {
  return (
    <div className="space-y-2">
      <p className="text-[10px] font-semibold text-gray-500 uppercase mb-2">Comments ({w.comments.length})</p>
      {w.comments.length === 0 && <p className="text-xs text-gray-400 text-center py-6">No comments yet</p>}
      {w.comments.map((c) => (
        <div key={c.id} className={`p-2.5 rounded-lg border ${c.resolved ? "bg-gray-50 border-gray-200" : "bg-white border-gray-100"}`}>
          <div className="flex items-center justify-between mb-1"><span className="text-[11px] font-medium text-gray-800">{c.author}</span><span className="text-[9px] text-gray-400">{formatTime(c.createdAt)}</span></div>
          <p className="text-[11px] text-gray-600">{c.body}</p>
          {c.mentions.length > 0 && <div className="flex gap-1 mt-1">{c.mentions.map((m) => <span key={m} className="text-[9px] px-1 py-0.5 rounded bg-navy-50 text-navy-600">@{m}</span>)}</div>}
          {c.resolved && <span className="text-[9px] text-green-600 mt-1 flex items-center gap-0.5"><CheckCircle className="w-3 h-3" /> Resolved</span>}
        </div>
      ))}
    </div>
  );
}

function AuditTab() {
  const entries = [
    { action: "Workflow created", user: "System", time: new Date(Date.now() - 3600000 * 72).toISOString() },
    { action: "AI review completed — 3 flags detected", user: "AI System", time: new Date(Date.now() - 3600000 * 48).toISOString() },
    { action: "Assigned to legal review", user: "Carol Singh", time: new Date(Date.now() - 3600000 * 36).toISOString() },
    { action: "Comments added by reviewer", user: "Alice Chen", time: new Date(Date.now() - 3600000 * 24).toISOString() },
    { action: "Escalated to Level 1", user: "System", time: new Date(Date.now() - 3600000 * 12).toISOString() },
  ];
  return (
    <div className="space-y-1.5">
      <p className="text-[10px] font-semibold text-gray-500 uppercase mb-2">Audit Trail</p>
      {entries.map((e, i) => (
        <div key={i} className="flex items-start gap-2 p-2 bg-white border border-gray-100 rounded-lg">
          <div className="w-2 h-2 rounded-full bg-navy-400 mt-1.5 flex-shrink-0" />
          <div className="flex-1"><p className="text-[11px] text-gray-800">{e.action}</p><p className="text-[9px] text-gray-400">{e.user} • {formatTime(e.time)}</p></div>
        </div>
      ))}
    </div>
  );
}

function AutomationTab() {
  const rules = [
    { name: "Auto-route High Risk", status: "Triggered", time: "2h ago" },
    { name: "Escalate SLA Breach", status: "Pending", time: "—" },
    { name: "Notify on Critical", status: "Triggered", time: "30m ago" },
  ];
  return (
    <div className="space-y-3">
      <p className="text-[10px] font-semibold text-gray-500 uppercase mb-2">Automation Actions</p>
      {rules.map((r, i) => (
        <div key={i} className="flex items-center gap-2.5 p-2.5 bg-white border border-gray-100 rounded-lg">
          <div className={`w-6 h-6 rounded-full flex items-center justify-center ${r.status === "Triggered" ? "bg-green-50" : "bg-gray-100"}`}>
            {r.status === "Triggered" ? <CheckCircle className="w-3 h-3 text-green-500" /> : <Clock className="w-3 h-3 text-gray-400" />}
          </div>
          <div className="flex-1"><p className="text-[11px] font-medium text-gray-800">{r.name}</p><p className="text-[9px] text-gray-400">{r.status} • {r.time}</p></div>
        </div>
      ))}
    </div>
  );
}

function formatTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const hrs = Math.floor(diff / 3600000);
  if (hrs < 1) return "just now";
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

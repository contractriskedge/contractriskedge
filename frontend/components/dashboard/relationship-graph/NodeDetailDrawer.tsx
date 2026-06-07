"use client";

import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X, Share2, FileText, AlertTriangle, DollarSign, ClipboardCheck, Activity, Link, Clock, Building2, Globe, User, Calendar, Shield } from "lucide-react";
import type { GraphNodeData, NodeType } from "./types";
import { NODE_COLORS, NODE_LABELS, RISK_BG, RISK_TEXT, RISK_BG_LIGHT } from "./types";

type TabId = "overview" | "connections" | "risk" | "financial" | "obligations" | "timeline" | "audit" | "ai";

function TabBtn({ label, icon, active, onClick }: { label: string; icon: React.ReactNode; active: boolean; onClick: () => void }) {
  return (
    <button onClick={onClick} className={`flex items-center gap-1 px-2.5 py-1.5 text-[10px] font-medium rounded-md whitespace-nowrap transition-all ${active ? "bg-navy-700 text-white shadow-sm" : "text-gray-500 hover:text-gray-700 hover:bg-gray-100"}`}>
      {icon}{label}
    </button>
  );
}

interface DrawerProps {
  node: GraphNodeData | null;
  onClose: () => void;
}

export function NodeDetailDrawer({ node, onClose }: DrawerProps) {
  const [tab, setTab] = useState<TabId>("overview");

  return (
    <AnimatePresence>
      {node && (
        <>
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="fixed inset-0 bg-black/20 z-40" onClick={onClose} />
          <motion.div initial={{ opacity: 0, x: 380 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: 380 }}
            transition={{ type: "spring", damping: 25, stiffness: 250 }}
            className="fixed right-0 top-0 bottom-0 w-[480px] bg-white border-l border-gray-200 shadow-xl z-50 flex flex-col">
            <div className="flex items-center justify-between px-5 py-4 border-b border-gray-200">
              <div className="flex items-center gap-2 min-w-0">
                <div className="w-8 h-8 rounded-lg flex items-center justify-center" style={{ backgroundColor: NODE_COLORS[node.type] || "#6B7280" }}>
                  <span className="text-white text-xs font-bold">{NODE_LABELS[node.type] || "?"}</span>
                </div>
                <div className="min-w-0"><h3 className="text-sm font-semibold text-navy-900 truncate">{node.label}</h3><p className="text-[10px] text-gray-500">{node.id} • {node.type.replace(/_/g, " ")}</p></div>
              </div>
              <button onClick={onClose} className="p-1 rounded hover:bg-gray-100 text-gray-400"><X className="w-4 h-4" /></button>
            </div>
            <div className="px-4 py-2 border-b border-gray-100 flex gap-1 overflow-x-auto">
              <TabBtn label="Overview" icon={<Share2 className="w-3 h-3" />} active={tab === "overview"} onClick={() => setTab("overview")} />
              <TabBtn label="Connections" icon={<Link className="w-3 h-3" />} active={tab === "connections"} onClick={() => setTab("connections")} />
              <TabBtn label="Risk" icon={<AlertTriangle className="w-3 h-3" />} active={tab === "risk"} onClick={() => setTab("risk")} />
              <TabBtn label="Financial" icon={<DollarSign className="w-3 h-3" />} active={tab === "financial"} onClick={() => setTab("financial")} />
              <TabBtn label="Obligations" icon={<ClipboardCheck className="w-3 h-3" />} active={tab === "obligations"} onClick={() => setTab("obligations")} />
              <TabBtn label="Timeline" icon={<Clock className="w-3 h-3" />} active={tab === "timeline"} onClick={() => setTab("timeline")} />
              <TabBtn label="AI" icon={<Share2 className="w-3 h-3" />} active={tab === "ai"} onClick={() => setTab("ai")} />
            </div>
            <div className="flex-1 overflow-y-auto p-5 space-y-4">
              {tab === "overview" && <OverviewTab node={node} />}
              {tab === "connections" && <ConnectionsTab />}
              {tab === "risk" && <RiskTab node={node} />}
              {tab === "financial" && <FinancialTab node={node} />}
              {tab === "obligations" && <ObligationsTab />}
              {tab === "timeline" && <TimelineTab />}
              {tab === "ai" && <AiTab node={node} />}
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}

function OverviewTab({ node }: { node: GraphNodeData }) {
  const MetaRow = ({ label, value, icon }: { label: string; value: string | React.ReactNode; icon?: React.ReactNode }) => (
    <div className="flex items-center justify-between py-1.5"><span className="text-[11px] text-gray-500 flex items-center gap-1.5">{icon}{label}</span><span className="text-[11px] font-medium text-gray-800">{value}</span></div>
  );
  return (
    <div className="space-y-4">
      <div className="p-3 bg-navy-50 rounded-lg border border-navy-100">
        <div className="flex items-center gap-1.5 mb-1.5"><Share2 className="w-3.5 h-3.5 text-navy-600" /><span className="text-[10px] font-semibold text-navy-700 uppercase tracking-wider">AI Relationship Summary</span></div>
        <p className="text-[11px] text-gray-700 leading-relaxed">
          {node.label} ({node.id}) is a {node.type.replace(/_/g, " ")}
          {node.metadata?.severity ? ` with severity ${node.metadata.severity}.` : "."}
          {node.metadata?.counterparty ? ` Counterparty: ${node.metadata.counterparty}.` : ""}
          {node.metadata?.vendor_name ? ` Vendor: ${node.metadata.vendor_name}.` : ""}
        </p>
      </div>
      <div className="bg-gray-50 rounded-lg p-3 space-y-0.5 divide-y divide-gray-100">
        <MetaRow label="Node ID" value={node.id} icon={<Share2 className="w-3 h-3" />} />
        <MetaRow label="Type" value={node.type.replace(/_/g, " ")} icon={<FileText className="w-3 h-3" />} />
        <MetaRow label="Status" value={(node.metadata?.status as string) || (node.metadata?.resolution as string) || "—"} />
        {(node.metadata?.severity as string) && <MetaRow label="Severity" value={node.metadata?.severity as string} icon={<AlertTriangle className="w-3 h-3" />} />}
        {(node.metadata?.risk_level as string) && <MetaRow label="Risk Level" value={node.metadata?.risk_level as string} />}
        {(node.metadata?.counterparty as string) && <MetaRow label="Counterparty" value={node.metadata?.counterparty as string} icon={<Building2 className="w-3 h-3" />} />}
        {(node.metadata?.vendor_name as string) && <MetaRow label="Vendor" value={node.metadata?.vendor_name as string} icon={<Building2 className="w-3 h-3" />} />}
        {(node.metadata?.workflow_stage as string) && <MetaRow label="Stage" value={node.metadata?.workflow_stage as string} />}
        {(node.metadata?.stage as string) && <MetaRow label="Stage" value={node.metadata?.stage as string} />}
        {(node.metadata?.clause_type as string) && <MetaRow label="Clause Type" value={node.metadata?.clause_type as string} />}
        {(node.metadata?.priority as string) && <MetaRow label="Priority" value={node.metadata?.priority as string} />}
      </div>
    </div>
  );
}

function ConnectionsTab() {
  const connections = [
    { id: "MSA-101-SOW-1", label: "SOW 1", type: "statement_of_work", relationship: "Downstream", risk: 7 },
    { id: "MSA-101-AMD-1", label: "Amendment 1", type: "amendment", relationship: "Amendment", risk: 6 },
    { id: "MSA-101-DPA", label: "DPA", type: "dpa", relationship: "Compliance", risk: 8 },
    { id: "MSA-102", label: "GlobalTech MSA", type: "master_service_agreement", relationship: "Cross-Dependency", risk: 7 },
    { id: "MSA-105", label: "SecureNet MSA", type: "master_service_agreement", relationship: "Shared SLA", risk: 9 },
  ];
  return (
    <div className="space-y-1.5">
      <p className="text-[10px] font-semibold text-gray-500 uppercase mb-2">Connected Agreements</p>
      {connections.map((c) => (
        <div key={c.id} className="flex items-center gap-2.5 p-2.5 bg-white border border-gray-100 rounded-lg hover:bg-gray-50 transition-colors cursor-pointer">
          <div className="w-7 h-7 rounded-lg flex items-center justify-center" style={{ backgroundColor: NODE_COLORS[c.type as NodeType] || "#6B7280" }}>
            <span className="text-white text-[9px] font-bold">{NODE_LABELS[c.type as NodeType] || "?"}</span>
          </div>
          <div className="flex-1 min-w-0"><p className="text-[11px] font-medium text-gray-800 truncate">{c.label}</p><p className="text-[9px] text-gray-400">{c.id} • {c.relationship}</p></div>
          <RiskBadge score={c.risk} />
        </div>
      ))}
    </div>
  );
}

function RiskTab({ node }: { node: GraphNodeData }) {
  const severity = (node.metadata?.severity as string) || (node.metadata?.risk_level as string) || "info";
  const counterparty = (node.metadata?.counterparty as string) || (node.metadata?.vendor_name as string) || "";
  const nodeType = node.type;
  const risks = [
    { category: "Inherited Risk", score: severity === "critical" ? 9 : severity === "high" ? 7 : severity === "medium" ? 5 : 2, level: severity, detail: "Risk inherited from upstream dependencies" },
    { category: "Propagated Risk", score: severity === "critical" ? 9 : severity === "high" ? 7 : 4, level: severity === "critical" ? "critical" : "high", detail: "Risk propagated to downstream agreements" },
    { category: "Concentration Risk", score: counterparty ? 7 : 3, level: counterparty ? "high" : "low", detail: counterparty ? `Counterparty ${counterparty} has multiple dependencies` : "No concentration risk" },
    { category: "Compliance Risk", score: nodeType === "finding" ? 8 : 3, level: nodeType === "finding" ? "high" : "medium", detail: nodeType === "finding" ? "Finding requires compliance review" : "Standard compliance" },
  ];
  return (
    <div className="space-y-2">
      <p className="text-[10px] font-semibold text-gray-500 uppercase mb-2">Risk Analysis</p>
      {risks.map((r) => (
        <div key={r.category} className="p-2.5 bg-white border border-gray-100 rounded-lg">
          <div className="flex items-center justify-between mb-1"><span className="text-[11px] font-semibold text-navy-900">{r.category}</span><RiskBadge score={r.score} /></div>
          <p className="text-[10px] text-gray-600">{r.detail}</p>
        </div>
      ))}
    </div>
  );
}

function FinancialTab({ node }: { node: GraphNodeData }) {
  const financialValue = (node.metadata?.financial_impact as number) || (node.metadata?.file_size as number) || 0;
  return (
    <div className="space-y-3">
      <div className="p-4 bg-gray-50 rounded-lg text-center">
        <p className="text-[10px] text-gray-500 uppercase font-semibold">Value</p>
        <p className="text-2xl font-bold text-navy-900 mt-1">{financialValue > 0 ? `$${financialValue}` : "—"}</p>
        <p className="text-[10px] text-gray-400 mt-0.5">{node.type === "upload" ? "File size (bytes)" : "Financial impact"}</p>
      </div>
      <div className="p-3 bg-orange-50 rounded-lg border border-orange-100">
        <p className="text-[10px] font-semibold text-orange-700 uppercase mb-1">Entity Details</p>
        <p className="text-xs text-orange-600">{node.type === "finding" ? `${(node.metadata?.clause_type as string) || "Unknown"} clause` : `${node.type} entity`}</p>
      </div>
    </div>
  );
}

function ObligationsTab() {
  const obligations = [
    { desc: "Submit SOC2 Type II report", due: "2026-06-15", owner: "SecureNet Solutions", status: "pending" },
    { desc: "Renew cyber liability insurance", due: "2026-05-30", owner: "Acme Corp", status: "overdue" },
    { desc: "Provide quarterly uptime report", due: "2026-06-01", owner: "CloudServ Ltd", status: "pending" },
    { desc: "GDPR compliance certification", due: "2026-07-01", owner: "EuroLegal Partners", status: "pending" },
  ];
  return (
    <div className="space-y-1.5">
      <p className="text-[10px] font-semibold text-gray-500 uppercase mb-2">Active Obligations</p>
      {obligations.map((o, i) => (
        <div key={i} className="flex items-center gap-2 p-2.5 bg-white border border-gray-100 rounded-lg">
          <div className={`w-6 h-6 rounded-full flex items-center justify-center ${o.status === "overdue" ? "bg-red-50" : "bg-yellow-50"}`}>
            {o.status === "overdue" ? <AlertTriangle className="w-3 h-3 text-red-500" /> : <Clock className="w-3 h-3 text-yellow-500" />}
          </div>
          <div className="flex-1 min-w-0"><p className="text-[11px] font-medium text-gray-800 truncate">{o.desc}</p><p className="text-[9px] text-gray-400">{o.owner} • Due {o.due}</p></div>
          <span className={`text-[9px] font-medium px-1.5 py-0.5 rounded-full ${o.status === "overdue" ? "bg-red-50 text-red-700" : "bg-yellow-50 text-yellow-700"}`}>{o.status}</span>
        </div>
      ))}
    </div>
  );
}

function TimelineTab() {
  const events = [
    { date: "2026-05-14", event: "Obligation Due: SOC2 Report", type: "obligation" },
    { date: "2026-05-10", event: "Amendment Executed: AMD-3", type: "amendment" },
    { date: "2026-05-01", event: "Renewal Notice Sent", type: "renewal" },
    { date: "2026-04-28", event: "DPA Compliance Review", type: "compliance" },
    { date: "2026-04-15", event: "New SOW Signed", type: "signature" },
  ];
  return (
    <div className="space-y-2">
      <p className="text-[10px] font-semibold text-gray-500 uppercase mb-2">Contract Timeline</p>
      {events.map((e, i) => (
        <div key={i} className="flex items-start gap-3">
          <div className="flex flex-col items-center">
            <div className={`w-2.5 h-2.5 rounded-full ${e.type === "obligation" ? "bg-red-500" : e.type === "amendment" ? "bg-amber-500" : e.type === "renewal" ? "bg-green-500" : e.type === "compliance" ? "bg-blue-500" : "bg-purple-500"}`} />
            {i < events.length - 1 && <div className="w-px h-6 bg-gray-200" />}
          </div>
          <div className="pb-3"><p className="text-[11px] font-medium text-gray-800">{e.event}</p><p className="text-[9px] text-gray-400">{e.date}</p></div>
        </div>
      ))}
    </div>
  );
}

function AiTab({ node }: { node: GraphNodeData }) {
  return (
    <div className="space-y-3">
      <div className="p-3 bg-purple-50 rounded-lg border border-purple-100">
        <div className="flex items-center gap-1.5 mb-1.5"><Share2 className="w-3.5 h-3.5 text-purple-600" /><span className="text-[10px] font-semibold text-purple-700 uppercase">AI Relationship Analysis</span></div>
        <p className="text-[11px] text-gray-700 leading-relaxed">This {node.type.replace(/_/g, " ")} has status {String(node.metadata?.status || "unknown")}. {(node.metadata?.severity as string) === "critical" ? "HIGH RISK: Immediate review recommended." : "Risk level is within acceptable thresholds."}</p>
      </div>
      <div className="space-y-2">
        {[
          { title: "Impact Analysis", desc: `This ${node.type} entity has findings and redlines.` },
          { title: "Dependency Health", desc: `${node.metadata?.status || "Unknown"} status.` },
          { title: "Entity Info", desc: `Type: ${node.type}. ${node.metadata?.clause_type ? "Clause: " + String(node.metadata.clause_type) : ""}` },
          { title: "Compliance Status", desc: node.type === "finding" ? "Finding requires review." : "Standard compliance." },
        ].map((item) => (
          <div key={item.title} className="p-2.5 bg-white border border-gray-100 rounded-lg">
            <p className="text-[10px] font-semibold text-navy-700 uppercase mb-0.5">{item.title}</p>
            <p className="text-[11px] text-gray-600">{item.desc}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

function RiskBadge({ score }: { score: number }) {
  const level = score >= 8 ? "critical" : score >= 6 ? "high" : score >= 4 ? "medium" : "low";
  return <span className={`inline-flex items-center gap-1 text-[10px] font-bold px-1.5 py-0.5 rounded-full ${RISK_BG_LIGHT[level]} ${RISK_TEXT[level]}`}><span className={`w-1.5 h-1.5 rounded-full ${RISK_BG[level]}`} />{score}/10</span>;
}

function LayersIcon() {
  return (
    <svg className="w-3 h-3 text-gray-400" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M6.429 9.75L2.25 12l4.179 2.25m0-4.5l5.571 3 5.571-3m-11.142 0L2.25 7.5 12 2.25l9.75 5.25-4.179 2.25m0 0L21.75 12l-4.179 2.25m0 0l4.179 2.25L12 21.75 2.25 16.5l4.179-2.25m11.142 0l-5.571 3-5.571-3" />
    </svg>
  );
}

"use client";

import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X, Building2, FileText, AlertTriangle, DollarSign, Activity, Shield, Link, Clock, CheckCircle, AlertOctagon, Globe, User, Calendar } from "lucide-react";
import type { SupplierRecord } from "./types";
import { RISK_BG, RISK_TEXT, RISK_BG_LIGHT, COMPLIANCE_CONFIG } from "./types";

type TabId = "overview" | "contracts" | "risk" | "spend" | "sla" | "compliance" | "relationships" | "audit";

function TabBtn({ label, icon, active, onClick }: { label: string; icon: React.ReactNode; active: boolean; onClick: () => void }) {
  return (
    <button onClick={onClick} className={`flex items-center gap-1 px-2.5 py-1.5 text-[10px] font-medium rounded-md whitespace-nowrap transition-all ${active ? "bg-navy-700 text-white shadow-sm" : "text-gray-500 hover:text-gray-700 hover:bg-gray-100"}`}>
      {icon}{label}
    </button>
  );
}

function RiskBadge({ score }: { score: number }) {
  const l = score >= 8 ? "critical" : score >= 6 ? "high" : score >= 4 ? "medium" : "low";
  return <span className={`inline-flex items-center gap-1 text-[10px] font-bold px-1.5 py-0.5 rounded-full ${RISK_BG_LIGHT[l]} ${RISK_TEXT[l]}`}><span className={`w-1.5 h-1.5 rounded-full ${RISK_BG[l]}`} />{score}/10</span>;
}

interface DrawerProps {
  supplier: SupplierRecord | null;
  onClose: () => void;
}

export function SupplierDrawer({ supplier, onClose }: DrawerProps) {
  const [tab, setTab] = useState<TabId>("overview");

  return (
    <AnimatePresence>
      {supplier && (
        <>
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="fixed inset-0 bg-black/20 z-40" onClick={onClose} />
          <motion.div initial={{ opacity: 0, x: 380 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: 380 }}
            transition={{ type: "spring", damping: 25, stiffness: 250 }}
            className="fixed right-0 top-0 bottom-0 w-[480px] bg-white border-l border-gray-200 shadow-xl z-50 flex flex-col">
            <div className="flex items-center justify-between px-5 py-4 border-b border-gray-200">
              <div className="flex items-center gap-2 min-w-0">
                <Building2 className="w-4 h-4 text-navy-600 flex-shrink-0" />
                <div className="min-w-0"><h3 className="text-sm font-semibold text-navy-900 truncate">{supplier.name}</h3><p className="text-[10px] text-gray-500">{supplier.id} • {supplier.dunsNumber}</p></div>
              </div>
              <button onClick={onClose} className="p-1 rounded hover:bg-gray-100 text-gray-400"><X className="w-4 h-4" /></button>
            </div>
            <div className="px-4 py-2 border-b border-gray-100 flex gap-1 overflow-x-auto">
              <TabBtn label="Overview" icon={<Building2 className="w-3 h-3" />} active={tab === "overview"} onClick={() => setTab("overview")} />
              <TabBtn label="Contracts" icon={<FileText className="w-3 h-3" />} active={tab === "contracts"} onClick={() => setTab("contracts")} />
              <TabBtn label="Risk" icon={<AlertTriangle className="w-3 h-3" />} active={tab === "risk"} onClick={() => setTab("risk")} />
              <TabBtn label="Spend" icon={<DollarSign className="w-3 h-3" />} active={tab === "spend"} onClick={() => setTab("spend")} />
              <TabBtn label="SLA" icon={<Activity className="w-3 h-3" />} active={tab === "sla"} onClick={() => setTab("sla")} />
              <TabBtn label="Compliance" icon={<Shield className="w-3 h-3" />} active={tab === "compliance"} onClick={() => setTab("compliance")} />
              <TabBtn label="Relationships" icon={<Link className="w-3 h-3" />} active={tab === "relationships"} onClick={() => setTab("relationships")} />
              <TabBtn label="Audit" icon={<FileText className="w-3 h-3" />} active={tab === "audit"} onClick={() => setTab("audit")} />
            </div>
            <div className="flex-1 overflow-y-auto p-5 space-y-4">
              {tab === "overview" && <OverviewTab s={supplier} />}
              {tab === "contracts" && <ContractsTab s={supplier} />}
              {tab === "risk" && <RiskTab s={supplier} />}
              {tab === "spend" && <SpendTab s={supplier} />}
              {tab === "sla" && <SlaTab />}
              {tab === "compliance" && <ComplianceTab s={supplier} />}
              {tab === "relationships" && <RelationshipsTab />}
              {tab === "audit" && <AuditTab s={supplier} />}
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}

function OverviewTab({ s }: { s: SupplierRecord }) {
  const MetaRow = ({ label, value, icon }: { label: string; value: string | React.ReactNode; icon?: React.ReactNode }) => (
    <div className="flex items-center justify-between py-1.5"><span className="text-[11px] text-gray-500 flex items-center gap-1.5">{icon}{label}</span><span className="text-[11px] font-medium text-gray-800">{value}</span></div>
  );
  return (
    <div className="space-y-4">
      <div className="p-3 bg-navy-50 rounded-lg border border-navy-100">
        <div className="flex items-center gap-1.5 mb-1.5"><Building2 className="w-3.5 h-3.5 text-navy-600" /><span className="text-[10px] font-semibold text-navy-700 uppercase tracking-wider">AI Supplier Summary</span></div>
        <p className="text-[11px] text-gray-700 leading-relaxed">{s.name} is a {s.category.toLowerCase()} supplier with {s.activeContracts} active contracts totaling ${s.totalSpend}M in spend. Risk score: {s.riskScore}/10. {s.insuranceCompliant ? "Insurance compliant." : "Insurance compliance gap detected."} {s.hasSla ? "SLA active." : "No SLA in place."}</p>
      </div>
      <div className="bg-gray-50 rounded-lg p-3 space-y-0.5 divide-y divide-gray-100">
        <MetaRow label="Category" value={s.category} icon={<FileText className="w-3 h-3" />} />
        <MetaRow label="Risk Score" value={<RiskBadge score={s.riskScore} />} />
        <MetaRow label="Total Spend" value={`$${s.totalSpend}M`} icon={<DollarSign className="w-3 h-3" />} />
        <MetaRow label="Active Contracts" value={s.activeContracts.toString()} icon={<FileText className="w-3 h-3" />} />
        <MetaRow label="Country" value={s.country} icon={<Globe className="w-3 h-3" />} />
        <MetaRow label="Owner" value={s.procurementOwner} icon={<User className="w-3 h-3" />} />
        <MetaRow label="Financial Stability" value={s.financialStability} />
        <MetaRow label="Relationship Age" value={`${s.relationshipAge} years`} icon={<Clock className="w-3 h-3" />} />
        <MetaRow label="Last Assessment" value={s.lastAssessment} icon={<Calendar className="w-3 h-3" />} />
        <MetaRow label="Insurance Compliant" value={s.insuranceCompliant ? "Yes" : "No"} />
        <MetaRow label="SLA Active" value={s.hasSla ? "Yes" : "No"} />
      </div>
      {s.aiFlags.length > 0 && (
        <div><p className="text-[10px] font-semibold text-gray-500 uppercase mb-1.5">AI Flags</p>
          <div className="space-y-1">{s.aiFlags.map((f) => (
            <div key={f} className="flex items-center gap-2 px-2.5 py-1.5 rounded-lg bg-red-50"><AlertTriangle className="w-3 h-3 text-red-500" /><span className="text-[11px] font-medium text-red-700">{f}</span></div>
          ))}</div>
        </div>
      )}
      {s.missingClauses.length > 0 && (
        <div><p className="text-[10px] font-semibold text-gray-500 uppercase mb-1.5">Missing Clauses</p>
          <div className="space-y-1">{s.missingClauses.map((mc) => (
            <div key={mc} className="flex items-center gap-2 px-2.5 py-1.5 rounded-lg bg-orange-50"><AlertOctagon className="w-3 h-3 text-orange-500" /><span className="text-[11px] font-medium text-orange-700">{mc}</span></div>
          ))}</div>
        </div>
      )}
    </div>
  );
}

function ContractsTab({ s }: { s: SupplierRecord }) {
  const contracts = Array.from({ length: s.activeContracts }, (_, i) => ({
    id: `CT-${2026100 + i}`, name: `${s.category} Agreement ${i + 1}`, value: +(s.totalSpend / s.activeContracts).toFixed(1), status: pick(["Active", "Under Review", "Expiring Soon"]), expiry: new Date(Date.now() + rand(30, 365) * 86400000).toISOString().split("T")[0],
  }));
  return (
    <div className="space-y-1.5">
      <p className="text-[10px] font-semibold text-gray-500 uppercase mb-2">Active Contracts ({s.activeContracts})</p>
      {contracts.map((c) => (
        <div key={c.id} className="flex items-center gap-2.5 p-2.5 bg-white border border-gray-100 rounded-lg hover:bg-gray-50 transition-colors">
          <FileText className="w-3.5 h-3.5 text-navy-400 flex-shrink-0" />
          <div className="flex-1 min-w-0"><p className="text-[11px] font-medium text-gray-800 truncate">{c.name}</p><p className="text-[9px] text-gray-400">{c.id}</p></div>
          <div className="text-right"><p className="text-[11px] font-medium">${c.value}M</p><p className="text-[9px] text-gray-400">Exp: {c.expiry}</p></div>
          <span className={`text-[9px] font-medium px-1.5 py-0.5 rounded-full ${c.status === "Active" ? "bg-green-50 text-green-700" : c.status === "Expiring Soon" ? "bg-yellow-50 text-yellow-700" : "bg-blue-50 text-blue-700"}`}>{c.status}</span>
        </div>
      ))}
    </div>
  );
}

function RiskTab({ s }: { s: SupplierRecord }) {
  const risks = [
    { category: "Liability Exposure", score: s.riskScore, level: s.riskLevel, details: `${s.name} has ${s.riskScore >= 7 ? "uncapped" : "capped"} liability exposure of $${(s.totalSpend * 0.4).toFixed(1)}M.` },
    { category: "Data Privacy", score: Math.min(10, s.riskScore - 1), level: s.riskScore >= 7 ? "high" : "medium", details: s.insuranceCompliant ? "Data privacy controls verified." : "Data privacy compliance requires review." },
    { category: "Financial Stability", score: s.financialStability === "distressed" ? 9 : s.financialStability === "weak" ? 7 : s.financialStability === "stable" ? 4 : 2, level: s.financialStability === "distressed" ? "critical" : s.financialStability === "weak" ? "high" : "low", details: `Financial health: ${s.financialStability}.` },
    { category: "Geopolitical", score: s.country === "India" || s.country === "Brazil" ? 7 : s.country === "China" ? 8 : 3, level: s.country === "India" || s.country === "Brazil" ? "high" : "low", details: `Operations in ${s.country}. ${s.country === "India" ? "Regulatory changes in data localization." : "Stable geopolitical environment."}` },
    { category: "SLA Compliance", score: s.slaPerformance < 85 ? 8 : s.slaPerformance < 95 ? 5 : 2, level: s.slaPerformance < 85 ? "high" : s.slaPerformance < 95 ? "medium" : "low", details: `SLA performance at ${s.slaPerformance}%.` },
  ];
  return (
    <div className="space-y-2">
      <p className="text-[10px] font-semibold text-gray-500 uppercase mb-2">Risk Analysis</p>
      {risks.map((r) => (
        <div key={r.category} className="p-2.5 bg-white border border-gray-100 rounded-lg">
          <div className="flex items-center justify-between mb-1"><span className="text-[11px] font-semibold text-navy-900">{r.category}</span><RiskBadge score={r.score} /></div>
          <p className="text-[10px] text-gray-600">{r.details}</p>
        </div>
      ))}
    </div>
  );
}

function SpendTab({ s }: { s: SupplierRecord }) {
  const years = [2023, 2024, 2025, 2026];
  const quarterly = years.map((y) => ({ year: y, q1: +(s.totalSpend * rand(18, 28) / 100).toFixed(1), q2: +(s.totalSpend * rand(22, 32) / 100).toFixed(1), q3: +(s.totalSpend * rand(20, 30) / 100).toFixed(1), q4: +(s.totalSpend * rand(24, 34) / 100).toFixed(1) }));
  return (
    <div className="space-y-3">
      <div className="p-4 bg-gray-50 rounded-lg text-center"><p className="text-[10px] text-gray-500 uppercase font-semibold">Total Spend</p><p className="text-2xl font-bold text-navy-900 mt-1">${s.totalSpend}M</p><p className="text-[10px] text-gray-400 mt-0.5">Across {s.activeContracts} contracts</p></div>
      <div><p className="text-[10px] font-semibold text-gray-500 uppercase mb-2">Annual Spend History</p>
        {quarterly.map((q) => (
          <div key={q.year} className="flex items-center gap-2 p-2 border-b border-gray-50 last:border-0">
            <span className="text-[11px] font-medium text-gray-700 w-8">{q.year}</span>
            <div className="flex-1 flex gap-1 h-4 items-end">
              {[q.q1, q.q2, q.q3, q.q4].map((v, i) => (
                <div key={i} className="flex-1 bg-navy-500 rounded-t" style={{ height: `${(v / s.totalSpend) * 60}px`, opacity: 0.6 + i * 0.1 }} title={`Q${i + 1}: $${v}M`} />
              ))}
            </div>
            <span className="text-[10px] text-gray-500 tabular-nums w-12 text-right">${(q.q1 + q.q2 + q.q3 + q.q4).toFixed(1)}M</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function SlaTab() {
  const metrics = [
    { metric: "Uptime / Availability", target: 99.9, actual: 99.2, status: "Below Target" },
    { metric: "Response Time (P1)", target: 1, actual: 1.5, status: "Below Target" },
    { metric: "Resolution Time (P1)", target: 4, actual: 3.5, status: "Meeting Target" },
    { metric: "Support Availability", target: 24, actual: 24, status: "Meeting Target" },
    { metric: "Data Backup Frequency", target: 24, actual: 24, status: "Meeting Target" },
  ];
  return (
    <div className="space-y-1.5">
      <p className="text-[10px] font-semibold text-gray-500 uppercase mb-2">SLA Performance Metrics</p>
      {metrics.map((m) => (
        <div key={m.metric} className="flex items-center gap-2.5 p-2.5 bg-white border border-gray-100 rounded-lg">
          <div className={`w-6 h-6 rounded-full flex items-center justify-center ${m.status === "Meeting Target" ? "bg-green-50" : "bg-red-50"}`}>
            {m.status === "Meeting Target" ? <CheckCircle className="w-3 h-3 text-green-500" /> : <AlertTriangle className="w-3 h-3 text-red-500" />}
          </div>
          <div className="flex-1"><p className="text-[11px] font-medium text-gray-800">{m.metric}</p><p className="text-[9px] text-gray-400">Target: {m.target}{m.metric.includes("Time") ? "hrs" : "%"} • Actual: {m.actual}{m.metric.includes("Time") ? "hrs" : "%"}</p></div>
          <span className={`text-[9px] font-medium px-1.5 py-0.5 rounded-full ${m.status === "Meeting Target" ? "bg-green-50 text-green-700" : "bg-red-50 text-red-700"}`}>{m.status}</span>
        </div>
      ))}
    </div>
  );
}

function ComplianceTab({ s }: { s: SupplierRecord }) {
  const items = [
    { requirement: "Cyber Liability Insurance", status: s.insuranceCompliant ? "compliant" : "non_compliant", notes: s.insuranceCompliant ? "Coverage verified ($5M)" : "Proof of insurance required" },
    { requirement: "Professional Indemnity", status: s.insuranceCompliant ? "compliant" : "at_risk", notes: s.insuranceCompliant ? "Coverage verified ($2M)" : "Coverage below minimum threshold" },
    { requirement: "GDPR Compliance", status: s.country === "Germany" || s.country === "France" ? "pending_review" : "compliant", notes: s.country === "Germany" || s.country === "France" ? "GDPR addendum pending" : "Compliant" },
    { requirement: "Data Processing Agreement", status: s.missingClauses.includes("DPA") ? "non_compliant" : "compliant", notes: s.missingClauses.includes("DPA") ? "DPA not executed" : "DPA in place" },
    { requirement: "SOC2 Certification", status: s.riskScore >= 7 ? "at_risk" : "compliant", notes: s.riskScore >= 7 ? "Certification expiring soon" : "Current" },
    { requirement: "Business Continuity Plan", status: s.financialStability === "distressed" ? "non_compliant" : "compliant", notes: s.financialStability === "distressed" ? "BCP documentation missing" : "BCP verified" },
  ];
  return (
    <div className="space-y-1.5">
      <p className="text-[10px] font-semibold text-gray-500 uppercase mb-2">Compliance Status</p>
      {items.map((item) => {
        const cfg = COMPLIANCE_CONFIG[item.status as keyof typeof COMPLIANCE_CONFIG] || COMPLIANCE_CONFIG.pending_review;
        return (
          <div key={item.requirement} className="flex items-center gap-2.5 p-2.5 bg-white border border-gray-100 rounded-lg">
            <Shield className="w-3.5 h-3.5 text-gray-400 flex-shrink-0" />
            <div className="flex-1"><p className="text-[11px] font-medium text-gray-800">{item.requirement}</p><p className="text-[9px] text-gray-400">{item.notes}</p></div>
            <span className={`text-[9px] font-medium px-1.5 py-0.5 rounded-full ${cfg.bg} ${cfg.color}`}>{cfg.label}</span>
          </div>
        );
      })}
    </div>
  );
}

function RelationshipsTab() {
  const rels = [
    { supplier: "CloudServ Ltd", type: "Co-supplier (Cloud)", strength: 85 },
    { supplier: "SecureNet Solutions", type: "Sub-contractor", strength: 70 },
    { supplier: "DataSync Partners", type: "Partner", strength: 90 },
    { supplier: "GlobalTech Inc", type: "Co-supplier (Software)", strength: 75 },
    { supplier: "InnoVate LLC", type: "Reseller", strength: 60 },
  ];
  return (
    <div className="space-y-1.5">
      <p className="text-[10px] font-semibold text-gray-500 uppercase mb-2">Supplier Ecosystem</p>
      {rels.map((r) => (
        <div key={r.supplier} className="flex items-center gap-2.5 p-2.5 bg-white border border-gray-100 rounded-lg hover:bg-gray-50 transition-colors">
          <Link className="w-3.5 h-3.5 text-navy-400 flex-shrink-0" />
          <div className="flex-1"><p className="text-[11px] font-medium text-gray-800">{r.supplier}</p><p className="text-[9px] text-gray-400">{r.type}</p></div>
          <div className="flex items-center gap-1.5"><div className="w-12 h-1.5 bg-gray-200 rounded-full overflow-hidden"><div className="h-full rounded-full bg-navy-500" style={{ width: `${r.strength}%` }} /></div><span className="text-[9px] text-gray-500">{r.strength}%</span></div>
        </div>
      ))}
    </div>
  );
}

function AuditTab({ s }: { s: SupplierRecord }) {
  const events = [
    { date: s.lastAssessment, title: "Risk assessment", detail: `Completed vendor risk review for ${s.name}.`, status: "completed" },
    { date: "2026-05-12", title: "Insurance audit", detail: s.insuranceCompliant ? "Insurance coverage verified." : "Insurance evidence requested.", status: s.insuranceCompliant ? "completed" : "pending" },
    { date: "2026-05-08", title: "SLA review", detail: `SLA performance evaluated at ${s.slaPerformance}%.`, status: s.slaPerformance >= 95 ? "completed" : "pending" },
    { date: "2026-04-28", title: "Compliance check", detail: s.missingClauses.length ? `${s.missingClauses.length} missing clause(s) identified.` : "No gaps reported.", status: s.missingClauses.length ? "pending" : "completed" },
  ];
  return (
    <div className="space-y-3">
      <p className="text-[10px] font-semibold text-gray-500 uppercase mb-2">Audit timeline</p>
      {events.map((event) => (
        <div key={`${event.date}-${event.title}`} className="rounded-2xl border border-gray-100 bg-white p-3">
          <div className="flex items-center justify-between gap-2">
            <div>
              <p className="text-[11px] font-semibold text-navy-900">{event.title}</p>
              <p className="text-[10px] text-gray-500">{event.date}</p>
            </div>
            <span className={`text-[10px] font-semibold px-2 py-1 rounded-full ${event.status === "completed" ? "bg-green-50 text-green-700" : "bg-amber-50 text-amber-700"}`}>{event.status}</span>
          </div>
          <p className="mt-2 text-[10px] text-gray-600">{event.detail}</p>
        </div>
      ))}
    </div>
  );
}

function pick<T>(arr: T[]): T { return arr[Math.floor(Math.random() * arr.length)]; }
function rand(min: number, max: number) { return Math.floor(Math.random() * (max - min + 1)) + min; }

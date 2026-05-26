"use client";

import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Shield, AlertTriangle, CheckCircle, XCircle, Clock, ArrowUpDown,
  Search, Filter, ChevronDown, ChevronRight, Eye, MoreHorizontal,
  Gavel, FileText, Building2, TrendingUp, BarChart3,
} from "lucide-react";
import type { ComplianceFinding, ComplianceAnalytics, Regulation } from "./types";

// ── Finding Card ─────────────────────────────────────────────────────────

function FindingCard({ finding, onSelect, onPreview }: { finding: ComplianceFinding; onSelect: () => void; onPreview: () => void }) {
  const severityColors: Record<string, string> = {
    critical: "border-red-200 bg-red-50/30 dark:border-red-900/30 dark:bg-red-900/10",
    high: "border-orange-200 bg-orange-50/30 dark:border-orange-900/30 dark:bg-orange-900/10",
    medium: "border-amber-200 bg-amber-50/30 dark:border-amber-900/30 dark:bg-amber-900/10",
    low: "border-blue-200 bg-blue-50/30 dark:border-blue-900/30 dark:bg-blue-900/10",
    info: "border-gray-200 dark:border-navy-600",
  };
  const statusColors: Record<string, string> = {
    open: "bg-red-100 text-red-600", in_progress: "bg-blue-100 text-blue-600",
    resolved: "bg-green-100 text-green-600", overdue: "bg-red-100 text-red-600",
    escalated: "bg-orange-100 text-orange-600",
  };
  return (
    <motion.div layout className={`border rounded-lg overflow-hidden ${severityColors[finding.severity]}`}>
      <div className="px-3 py-2">
        <div className="flex items-start gap-2.5">
          <div className={`w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0 ${
            finding.severity === "critical" ? "bg-red-100 text-red-600" :
            finding.severity === "high" ? "bg-orange-100 text-orange-600" :
            "bg-amber-100 text-amber-600"
          }`}>
            {finding.severity === "critical" || finding.severity === "high" ? <AlertTriangle className="w-3.5 h-3.5" /> : <Shield className="w-3.5 h-3.5" />}
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-1.5 flex-wrap">
              <span className="text-xs font-semibold text-navy-900 dark:text-white">{finding.title}</span>
              <span className={`text-[8px] px-1.5 py-0.5 rounded-full font-medium ${statusColors[finding.status]}`}>{finding.status.replace("_", " ")}</span>
              <span className="text-[8px] bg-gray-100 dark:bg-navy-700 text-gray-500 px-1.5 py-0.5 rounded-full">{finding.regulationName}</span>
            </div>
            <p className="text-[10px] text-gray-600 dark:text-gray-300 mt-0.5">{finding.description}</p>
            <div className="flex items-center gap-2 mt-1 text-[8px] text-gray-400">
              <span>{finding.impactedContracts} contracts</span>
              <span>·</span>
              <span>{finding.impactedVendors} vendors</span>
              <span>·</span>
              <span>Assignee: {finding.assignee}</span>
              <span>·</span>
              <span>Due: {new Date(finding.dueDate).toLocaleDateString("en-US", { month: "short", day: "numeric" })}</span>
              {finding.aiConfidence > 90 && (
                <span className="text-purple-500 font-medium">AI {finding.aiConfidence}%</span>
              )}
            </div>
          </div>
          <div className="flex items-center gap-0.5 flex-shrink-0">
            <button onClick={onPreview} className="p-1 text-gray-400 hover:text-gold-600 hover:bg-gold-50 rounded transition-colors"><Eye className="w-3 h-3" /></button>
            <button className="p-1 text-gray-400 hover:text-navy-600 rounded transition-colors"><MoreHorizontal className="w-3 h-3" /></button>
          </div>
        </div>
      </div>
    </motion.div>
  );
}

// ── Compliance Heatmap ──────────────────────────────────────────────────

function ComplianceHeatmap({ regulations }: { regulations: Regulation[] }) {
  return (
    <div className="bg-white dark:bg-navy-800 border border-gray-200 dark:border-navy-600 rounded-lg p-3">
      <h4 className="text-[10px] font-semibold text-gray-500 uppercase tracking-wider mb-2">Regulatory Compliance Heatmap</h4>
      <div className="space-y-1">
        {regulations.map(r => (
          <div key={r.id} className="flex items-center gap-2">
            <span className="text-[9px] text-gray-600 dark:text-gray-300 w-16 truncate">{r.shortName}</span>
            <div className="flex-1 h-4 bg-gray-100 dark:bg-navy-700 rounded-full overflow-hidden">
              <motion.div initial={{ width: 0 }} animate={{ width: `${r.complianceScore}%` }}
                className={`h-full rounded-full ${
                  r.complianceScore >= 85 ? "bg-green-500" : r.complianceScore >= 70 ? "bg-amber-500" : "bg-red-500"
                }`} />
            </div>
            <span className="text-[9px] text-gray-500 tabular-nums w-8 text-right">{r.complianceScore}%</span>
            <div className="flex items-center gap-0.5 w-16 justify-end">
              {Array.from({ length: Math.ceil(r.gapCount / 2) }).map((_, i) => (
                <div key={i} className={`w-1.5 h-3 rounded-sm ${i < 2 ? "bg-red-400" : i < 3 ? "bg-amber-400" : "bg-green-400"}`} />
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Regional Exposure Map ────────────────────────────────────────────────

function RegionalExposure({ analytics }: { analytics: ComplianceAnalytics }) {
  return (
    <div className="bg-white dark:bg-navy-800 border border-gray-200 dark:border-navy-600 rounded-lg p-3">
      <h4 className="text-[10px] font-semibold text-gray-500 uppercase tracking-wider mb-2">Regional Risk Exposure</h4>
      <div className="space-y-1">
        {analytics.regionalExposure.map(r => (
          <div key={r.region} className="flex items-center gap-2">
            <span className="text-[9px] text-gray-600 dark:text-gray-300 w-24 truncate">{r.region}</span>
            <div className="flex-1 h-3 bg-gray-100 dark:bg-navy-700 rounded-full overflow-hidden">
              <motion.div initial={{ width: 0 }} animate={{ width: `${r.riskScore}%` }}
                className={`h-full rounded-full ${r.riskScore >= 70 ? "bg-red-500" : r.riskScore >= 50 ? "bg-amber-500" : "bg-green-500"}`} />
            </div>
            <span className="text-[8px] text-gray-500 tabular-nums w-8 text-right">{r.riskScore}</span>
            <span className="text-[8px] text-gray-400 tabular-nums w-6">{r.contractCount}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Remediation Trend Chart ──────────────────────────────────────────────

function RemediationTrend({ analytics }: { analytics: ComplianceAnalytics }) {
  const maxVal = Math.max(...analytics.remediationTrend.map(t => t.open + t.resolved));
  return (
    <div className="bg-white dark:bg-navy-800 border border-gray-200 dark:border-navy-600 rounded-lg p-3">
      <h4 className="text-[10px] font-semibold text-gray-500 uppercase tracking-wider mb-2">Remediation Progress</h4>
      <div className="flex items-end gap-1.5 h-20">
        {analytics.remediationTrend.map((t, i) => (
          <div key={t.date} className="flex-1 flex flex-col items-center gap-0.5">
            <div className="w-full flex flex-col-reverse" style={{ height: `${((t.open + t.resolved) / maxVal) * 100}%` }}>
              <motion.div initial={{ height: 0 }} animate={{ height: `${(t.resolved / (t.open + t.resolved)) * 100}%` }}
                className="w-full bg-green-400 rounded-t" style={{ minHeight: 2 }} />
              <motion.div initial={{ height: 0 }} animate={{ height: `${(t.open / (t.open + t.resolved)) * 100}%` }}
                className="w-full bg-amber-400 rounded-b" style={{ minHeight: 2 }} />
            </div>
            <span className="text-[7px] text-gray-400 mt-0.5">{t.date.split(" ")[1]}</span>
          </div>
        ))}
      </div>
      <div className="flex items-center gap-3 mt-1.5 text-[8px] text-gray-400">
        <span className="flex items-center gap-1"><div className="w-2 h-2 rounded bg-amber-400" /> Open</span>
        <span className="flex items-center gap-1"><div className="w-2 h-2 rounded bg-green-400" /> Resolved</span>
      </div>
    </div>
  );
}

// ── Top Violations ──────────────────────────────────────────────────────

function TopViolations({ analytics }: { analytics: ComplianceAnalytics }) {
  const maxCount = Math.max(...analytics.topViolations.map(v => v.count));
  return (
    <div className="bg-white dark:bg-navy-800 border border-gray-200 dark:border-navy-600 rounded-lg p-3">
      <h4 className="text-[10px] font-semibold text-gray-500 uppercase tracking-wider mb-2">Top Compliance Violations</h4>
      <div className="space-y-1">
        {analytics.topViolations.map(v => (
          <div key={v.clause} className="flex items-center gap-2">
            <span className="text-[8px] text-gray-600 dark:text-gray-300 w-28 truncate">{v.clause}</span>
            <div className="flex-1 h-3 bg-gray-100 dark:bg-navy-700 rounded-full overflow-hidden">
              <motion.div initial={{ width: 0 }} animate={{ width: `${(v.count / maxCount) * 100}%` }} className="h-full bg-red-500 rounded-full" />
            </div>
            <span className="text-[8px] text-gray-500 tabular-nums w-4 text-right">{v.count}</span>
            <span className="text-[7px] text-gray-400 w-10 text-right">{v.regulation}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Center Panel ─────────────────────────────────────────────────────────

interface ComplianceCenterPanelProps {
  findings: ComplianceFinding[];
  regulations: Regulation[];
  analytics: ComplianceAnalytics;
  onFindingSelect: (finding: ComplianceFinding) => void;
  onPreview: (finding: ComplianceFinding) => void;
}

type CenterTab = "findings" | "heatmap" | "analytics";

export function ComplianceCenterPanel({
  findings, regulations, analytics, onFindingSelect, onPreview,
}: ComplianceCenterPanelProps) {
  const [activeTab, setActiveTab] = useState<CenterTab>("findings");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [severityFilter, setSeverityFilter] = useState<string>("all");
  const [searchQuery, setSearchQuery] = useState("");

  const filteredFindings = findings.filter(f => {
    if (statusFilter !== "all" && f.status !== statusFilter) return false;
    if (severityFilter !== "all" && f.severity !== severityFilter) return false;
    if (searchQuery && !f.title.toLowerCase().includes(searchQuery.toLowerCase()) && !f.description.toLowerCase().includes(searchQuery.toLowerCase())) return false;
    return true;
  });

  const tabs: { id: CenterTab; label: string }[] = [
    { id: "findings", label: "Compliance Findings" },
    { id: "heatmap", label: "Heatmap" },
    { id: "analytics", label: "Analytics" },
  ];

  return (
    <div className="flex-1 flex flex-col min-w-0 bg-gray-50 dark:bg-navy-900">
      <div className="flex items-center justify-between px-3 py-1.5 bg-white dark:bg-navy-800 border-b border-gray-200 dark:border-navy-700">
        <div className="flex items-center gap-1">
          {tabs.map(tab => (
            <button key={tab.id} onClick={() => setActiveTab(tab.id)}
              className={`px-2.5 py-1 rounded-lg text-[10px] font-medium transition-colors ${
                activeTab === tab.id ? "bg-gold-100 text-gold-700 dark:bg-gold-900/20 dark:text-gold-400" : "text-gray-500 hover:text-navy-700 hover:bg-gray-100 dark:hover:bg-navy-700"
              }`}>{tab.label}</button>
          ))}
        </div>
        {activeTab === "findings" && (
          <div className="flex items-center gap-1.5">
            <div className="relative">
              <Search className="absolute left-1.5 top-1/2 -translate-y-1/2 w-3 h-3 text-gray-400" />
              <input type="text" value={searchQuery} onChange={e => setSearchQuery(e.target.value)} placeholder="Search findings..."
                className="w-32 pl-6 pr-2 py-1 text-[10px] border border-gray-200 dark:border-navy-600 rounded-md bg-gray-50 dark:bg-navy-900 text-navy-900 dark:text-white placeholder-gray-400 focus:outline-none focus:ring-1 focus:ring-gold-400" />
            </div>
            <select value={severityFilter} onChange={e => setSeverityFilter(e.target.value)}
              className="text-[9px] border border-gray-200 dark:border-navy-600 rounded-md bg-transparent text-gray-500 py-1 px-1.5 focus:outline-none focus:ring-1 focus:ring-gold-400">
              <option value="all">All Severity</option>
              <option value="critical">Critical</option><option value="high">High</option><option value="medium">Medium</option>
            </select>
            <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)}
              className="text-[9px] border border-gray-200 dark:border-navy-600 rounded-md bg-transparent text-gray-500 py-1 px-1.5 focus:outline-none focus:ring-1 focus:ring-gold-400">
              <option value="all">All Status</option>
              <option value="open">Open</option><option value="in_progress">In Progress</option><option value="resolved">Resolved</option>
            </select>
          </div>
        )}
      </div>

      <div className="flex-1 overflow-y-auto p-3 space-y-3">
        {activeTab === "findings" && (
          filteredFindings.length === 0 ? (
            <div className="text-center py-12 text-gray-400"><Shield className="w-10 h-10 mx-auto mb-2 opacity-50" /><p className="text-xs">No findings match your filters</p></div>
          ) : (
            <div className="space-y-2">
              <div className="flex items-center gap-2 text-[9px] text-gray-500">
                <span className="font-medium text-navy-900 dark:text-white">{filteredFindings.length}</span> findings
                <span className="text-gray-300">|</span>
                <span className="text-red-600">{filteredFindings.filter(f => f.severity === "critical" || f.severity === "high").length} high severity</span>
              </div>
              {filteredFindings.map(f => (
                <FindingCard key={f.id} finding={f} onSelect={() => onFindingSelect(f)} onPreview={() => onPreview(f)} />
              ))}
            </div>
          )
        )}

        {activeTab === "heatmap" && (
          <div className="space-y-3">
            <ComplianceHeatmap regulations={regulations} />
            <RegionalExposure analytics={analytics} />
          </div>
        )}

        {activeTab === "analytics" && (
          <div className="space-y-3">
            {/* Summary cards */}
            <div className="grid grid-cols-4 gap-2">
              {[
                { label: "Overall Score", value: `${analytics.overallScore}%`, color: "text-blue-600" },
                { label: "Audit Readiness", value: `${analytics.auditReadiness}%`, color: "text-green-600" },
                { label: "Remediation Progress", value: `${analytics.remediationProgress}%`, color: "text-purple-600" },
                { label: "Open Findings", value: findings.filter(f => f.status !== "resolved").length.toString(), color: "text-amber-600" },
              ].map(s => (
                <div key={s.label} className="bg-white dark:bg-navy-800 border border-gray-200 dark:border-navy-600 rounded-lg p-2.5 text-center">
                  <p className={`text-lg font-bold ${s.color} tabular-nums`}>{s.value}</p>
                  <p className="text-[8px] text-gray-500 mt-0.5">{s.label}</p>
                </div>
              ))}
            </div>
            <div className="grid grid-cols-2 gap-3">
              <RemediationTrend analytics={analytics} />
              <TopViolations analytics={analytics} />
            </div>
            {/* Finding Categories */}
            <div className="bg-white dark:bg-navy-800 border border-gray-200 dark:border-navy-600 rounded-lg p-3">
              <h4 className="text-[10px] font-semibold text-gray-500 uppercase tracking-wider mb-2">Finding Categories</h4>
              <div className="grid grid-cols-2 gap-1">
                {analytics.findingCategories.map(c => (
                  <div key={c.category} className="flex items-center gap-2">
                    <span className="text-[8px] text-gray-600 dark:text-gray-300 w-24 truncate">{c.category}</span>
                    <div className="flex-1 h-2.5 bg-gray-100 dark:bg-navy-700 rounded-full overflow-hidden">
                      <motion.div initial={{ width: 0 }} animate={{ width: `${(c.count / Math.max(...analytics.findingCategories.map(x => x.count))) * 100}%` }} className="h-full bg-gold-500 rounded-full" />
                    </div>
                    <span className="text-[8px] text-gray-500 tabular-nums w-4 text-right">{c.count}</span>
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

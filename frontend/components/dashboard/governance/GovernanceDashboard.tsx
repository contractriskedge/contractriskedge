/**
 * GovernanceDashboard — Centralized governance view.
 *
 * Sprint 10 Priority 2.
 *
 * Centralizes:
 * - Policy exceptions & overrides
 * - AI quality regressions
 * - Approval chain monitor
 * - Prompt deployment tracker
 * - Compliance pack status
 */

"use client";

import React, { useState } from "react";
import { DashboardHeader } from "../command-center/DashboardHeader";

type DateRange = "24h" | "7d" | "30d" | "90d";
type RefreshInterval = 0 | 15 | 30 | 60;

type SectionId = "exceptions" | "quality" | "approvals" | "prompts" | "compliance";

const SECTIONS: { id: SectionId; label: string }[] = [
  { id: "exceptions", label: "Policy Exceptions" },
  { id: "quality", label: "AI Quality" },
  { id: "approvals", label: "Approval Chains" },
  { id: "prompts", label: "Prompt Deployments" },
  { id: "compliance", label: "Compliance Packs" },
];

export function GovernanceDashboard() {
  const [activeSection, setActiveSection] = useState<SectionId>("exceptions");
  const [dateRange, setDateRange] = useState<DateRange>("30d");
  const [refreshInterval, setRefreshInterval] = useState<RefreshInterval>(0);

  return (
    <div className="p-6 space-y-4">
      <DashboardHeader
        title="Governance Dashboard"
        description="Policy exceptions, AI quality, approval chains, prompt deployments, and compliance pack status"
        dateRange={dateRange}
        onDateRangeChange={setDateRange}
        refreshInterval={refreshInterval}
        onRefreshIntervalChange={setRefreshInterval}
        onExport={() => {}}
      />

      {/* ── Section navigation ───────────────────────────────── */}
      <div className="flex items-center gap-2 flex-wrap">
        {SECTIONS.map((s) => (
          <button
            key={s.id}
            onClick={() => setActiveSection(s.id)}
            className={`px-3 py-1.5 text-xs font-medium rounded-lg transition-colors ${
              activeSection === s.id
                ? "bg-navy-900 dark:bg-navy-600 text-white"
                : "bg-gray-100 dark:bg-navy-700 text-gray-600 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-navy-600"
            }`}
          >
            {s.label}
          </button>
        ))}
      </div>

      {/* ── Section Content ───────────────────────────────────── */}
      <div>
        {activeSection === "exceptions" && <PolicyExceptionCenter />}
        {activeSection === "quality" && <AIQualityRegressionTracker />}
        {activeSection === "approvals" && <ApprovalChainMonitor />}
        {activeSection === "prompts" && <PromptDeploymentTracker />}
        {activeSection === "compliance" && <CompliancePackStatus />}
      </div>
    </div>
  );
}

// ── Section Components ───────────────────────────────────────────────

function PolicyExceptionCenter() {
  const exceptions = [
    { id: "EXC-001", policy: "Liability Cap Policy", grantor: "Sarah Chen", severity: "high", expiresIn: "2 days", reason: "Strategic client relationship — exception approved by legal" },
    { id: "EXC-002", policy: "Standard Approval Chain", grantor: "Mike Johnson", severity: "medium", expiresIn: "5 days", reason: "Temporary delegation during leave coverage" },
    { id: "EXC-003", policy: "Data Retention Policy", grantor: "System", severity: "critical", expiresIn: "1 day", reason: "Emergency extension for active litigation hold" },
    { id: "EXC-004", policy: "Model Tier Restriction", grantor: "Admin", severity: "low", expiresIn: "14 days", reason: "A/B test requiring premium model access" },
  ];

  const severityColor = (s: string) =>
    s === "critical" ? "text-red-600 bg-red-50 dark:bg-red-900/20" :
    s === "high" ? "text-orange-600 bg-orange-50 dark:bg-orange-900/20" :
    s === "medium" ? "text-yellow-600 bg-yellow-50 dark:bg-yellow-900/20" :
    "text-blue-600 bg-blue-50 dark:bg-blue-900/20";

  return (
    <div className="bg-white dark:bg-navy-800 rounded-xl border border-gray-200 dark:border-navy-700 shadow-sm">
      <div className="px-4 py-3 border-b border-gray-100 dark:border-navy-700 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-navy-900 dark:text-white">Active Policy Exceptions</h3>
        <span className="text-xs text-gray-500">{exceptions.length} active</span>
      </div>
      <div className="p-4 space-y-2">
        {exceptions.map((exc) => (
          <div key={exc.id} className="p-3 rounded-lg bg-gray-50 dark:bg-navy-700 flex items-start gap-3">
            <span className={`w-1.5 h-1.5 rounded-full mt-1.5 ${
              exc.severity === "critical" ? "bg-red-500" :
              exc.severity === "high" ? "bg-orange-500" :
              exc.severity === "medium" ? "bg-yellow-500" : "bg-blue-500"
            }`} />
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <span className="text-xs font-medium text-navy-900 dark:text-white">{exc.policy}</span>
                <span className={`text-[10px] px-1.5 py-0.5 rounded-full ${severityColor(exc.severity)}`}>
                  {exc.severity}
                </span>
              </div>
              <p className="text-[10px] text-gray-500 mt-0.5">{exc.reason}</p>
              <div className="flex items-center gap-3 mt-1 text-[10px] text-gray-400">
                <span>Granted by: {exc.grantor}</span>
                <span className={`font-medium ${exc.expiresIn === "1 day" ? "text-red-500" : ""}`}>
                  Expires: {exc.expiresIn}
                </span>
              </div>
            </div>
            <div className="flex gap-1 shrink-0">
              <button className="px-2 py-1 text-[10px] font-medium rounded bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300 hover:bg-red-200">Revoke</button>
              <button className="px-2 py-1 text-[10px] font-medium rounded bg-gray-100 dark:bg-navy-600 text-gray-600 dark:text-gray-300 hover:bg-gray-200">Extend</button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function AIQualityRegressionTracker() {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
      <div className="bg-white dark:bg-navy-800 rounded-xl border border-gray-200 dark:border-navy-700 shadow-sm">
        <div className="px-4 py-3 border-b border-gray-100 dark:border-navy-700">
          <h3 className="text-sm font-semibold text-navy-900 dark:text-white">Quality Score Trend</h3>
        </div>
        <div className="p-4">
          <div className="flex items-end gap-1 h-20">
            {[88, 87, 89, 86, 85, 87, 86, 84, 83, 85, 84, 82, 83, 81, 82].map((val, i) => (
              <div
                key={i}
                className="flex-1 rounded-t"
                style={{
                  height: `${val}%`,
                  backgroundColor: val >= 85 ? "#10B981" : val >= 80 ? "#F59E0B" : "#EF4444",
                  opacity: 0.6 + (i / 15) * 0.4,
                }}
              />
            ))}
          </div>
          <div className="flex items-center justify-between mt-2 text-[10px] text-gray-400">
            <span>30-day trend</span>
            <span className="text-red-500 font-medium">↓ 4.2% decline</span>
          </div>
        </div>
      </div>
      <div className="bg-white dark:bg-navy-800 rounded-xl border border-gray-200 dark:border-navy-700 shadow-sm">
        <div className="px-4 py-3 border-b border-gray-100 dark:border-navy-700">
          <h3 className="text-sm font-semibold text-navy-900 dark:text-white">Recent Regressions</h3>
        </div>
        <div className="p-4 space-y-2">
          {[
            { test: "Liability Clause Extraction", severity: "major", change: "-6.2%" },
            { test: "Jurisdiction Classification", severity: "minor", change: "-2.1%" },
            { test: "Indemnification Scoring", severity: "critical", change: "-11.5%" },
          ].map((r, i) => (
            <div key={i} className="flex items-center justify-between p-2 rounded-lg bg-gray-50 dark:bg-navy-700">
              <div className="flex items-center gap-2">
                <span className={`w-2 h-2 rounded-full ${
                  r.severity === "critical" ? "bg-red-500" : r.severity === "major" ? "bg-orange-500" : "bg-yellow-500"
                }`} />
                <span className="text-xs text-navy-900 dark:text-white">{r.test}</span>
              </div>
              <span className={`text-xs font-medium ${
                r.severity === "critical" ? "text-red-500" : r.severity === "major" ? "text-orange-500" : "text-yellow-500"
              }`}>{r.change}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function ApprovalChainMonitor() {
  const chains = [
    { id: "CHN-001", name: "Standard Review Approval", stages: ["Reviewer", "Senior Reviewer", "Legal Counsel"], current: "Senior Reviewer", completion: 66, status: "in_progress" },
    { id: "CHN-002", name: "High-Risk Escalation", stages: ["Reviewer", "Legal Counsel", "VP Legal", "General Counsel"], current: "Legal Counsel", completion: 50, status: "in_progress" },
    { id: "CHN-003", name: "Emergency Exception", stages: ["Reviewer", "VP Legal"], current: "VP Legal", completion: 50, status: "pending" },
    { id: "CHN-004", name: "Standard Approval", stages: ["Reviewer", "Senior Reviewer"], current: "Reviewer", completion: 0, status: "pending" },
  ];

  return (
    <div className="bg-white dark:bg-navy-800 rounded-xl border border-gray-200 dark:border-navy-700 shadow-sm">
      <div className="px-4 py-3 border-b border-gray-100 dark:border-navy-700">
        <h3 className="text-sm font-semibold text-navy-900 dark:text-white">Active Approval Chains</h3>
      </div>
      <div className="p-4 space-y-3">
        {chains.map((chain) => (
          <div key={chain.id} className="p-3 rounded-lg bg-gray-50 dark:bg-navy-700">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-medium text-navy-900 dark:text-white">{chain.name}</span>
              <span className="text-[10px] text-gray-500">{chain.completion}% complete</span>
            </div>
            {/* Pipeline visual */}
            <div className="flex items-center gap-1">
              {chain.stages.map((stage, i) => {
                const isCurrent = stage === chain.current;
                const isPast = chain.stages.indexOf(chain.current) > i;
                return (
                  <React.Fragment key={stage}>
                    <div className={`px-2 py-1 text-[10px] rounded-full ${
                      isCurrent
                        ? "bg-navy-900 dark:bg-navy-500 text-white"
                        : isPast
                        ? "bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300"
                        : "bg-gray-200 dark:bg-navy-600 text-gray-500"
                    }`}>
                      {stage}
                    </div>
                    {i < chain.stages.length - 1 && (
                      <div className={`flex-1 h-0.5 ${
                        isPast ? "bg-green-400" : "bg-gray-200 dark:bg-navy-600"
                      }`} />
                    )}
                  </React.Fragment>
                );
              })}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function PromptDeploymentTracker() {
  const versions = [
    { version: "v2.4.1", status: "production", deployed: "2026-05-24", rollbacks: 0, abTest: false },
    { version: "v2.4.0", status: "rolled_back", deployed: "2026-05-20", rollbacks: 1, abTest: true, reason: "Quality regression in liability extraction" },
    { version: "v2.3.0", status: "production", deployed: "2026-05-15", rollbacks: 0, abTest: false },
    { version: "v2.4.2-beta", status: "staging", deployed: "2026-05-25", rollbacks: 0, abTest: true },
  ];

  return (
    <div className="bg-white dark:bg-navy-800 rounded-xl border border-gray-200 dark:border-navy-700 shadow-sm">
      <div className="px-4 py-3 border-b border-gray-100 dark:border-navy-700">
        <h3 className="text-sm font-semibold text-navy-900 dark:text-white">Prompt Deployment History</h3>
      </div>
      <div className="p-4">
        <table className="w-full text-xs">
          <thead>
            <tr className="text-gray-500 dark:text-gray-400">
              <th className="text-left pb-2 font-medium">Version</th>
              <th className="text-left pb-2 font-medium">Status</th>
              <th className="text-left pb-2 font-medium">Deployed</th>
              <th className="text-center pb-2 font-medium">A/B Test</th>
              <th className="text-right pb-2 font-medium">Actions</th>
            </tr>
          </thead>
          <tbody>
            {versions.map((v) => (
              <tr key={v.version} className="border-t border-gray-100 dark:border-navy-700">
                <td className="py-2 font-medium text-navy-900 dark:text-white">{v.version}</td>
                <td className="py-2">
                  <span className={`px-1.5 py-0.5 rounded-full text-[10px] font-medium ${
                    v.status === "production" ? "bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300" :
                    v.status === "staging" ? "bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300" :
                    "bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300"
                  }`}>
                    {v.status}
                  </span>
                </td>
                <td className="py-2 text-gray-500">{v.deployed}</td>
                <td className="py-2 text-center text-gray-500">{v.abTest ? "Yes" : "No"}</td>
                <td className="py-2 text-right">
                  {v.status === "staging" && (
                    <button className="text-navy-600 dark:text-navy-200 hover:underline text-[10px]">Promote</button>
                  )}
                  {v.status === "rolled_back" && v.reason && (
                    <span className="text-[10px] text-gray-400" title={v.reason}>Reason</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function CompliancePackStatus() {
  const packs = [
    { name: "GDPR", jurisdiction: "EU", coverage: 92, gaps: 3, lastAudit: "2026-05-01", status: "healthy" },
    { name: "CCPA", jurisdiction: "California", coverage: 88, gaps: 5, lastAudit: "2026-04-15", status: "warning" },
    { name: "SOC 2", jurisdiction: "Global", coverage: 95, gaps: 1, lastAudit: "2026-05-10", status: "healthy" },
    { name: "HIPAA", jurisdiction: "US Healthcare", coverage: 78, gaps: 8, lastAudit: "2026-03-20", status: "critical" },
  ];

  return (
    <div className="bg-white dark:bg-navy-800 rounded-xl border border-gray-200 dark:border-navy-700 shadow-sm">
      <div className="px-4 py-3 border-b border-gray-100 dark:border-navy-700">
        <h3 className="text-sm font-semibold text-navy-900 dark:text-white">Compliance Pack Status</h3>
      </div>
      <div className="p-4 space-y-2">
        {packs.map((pack) => (
          <div key={pack.name} className="flex items-center gap-3 p-3 rounded-lg bg-gray-50 dark:bg-navy-700">
            <span className={`w-2 h-2 rounded-full ${
              pack.status === "healthy" ? "bg-green-500" :
              pack.status === "warning" ? "bg-yellow-500" : "bg-red-500"
            }`} />
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <span className="text-xs font-medium text-navy-900 dark:text-white">{pack.name}</span>
                <span className="text-[10px] text-gray-400">{pack.jurisdiction}</span>
              </div>
              <div className="flex items-center gap-3 mt-1">
                <div className="flex-1 h-1.5 bg-gray-200 dark:bg-navy-600 rounded-full overflow-hidden">
                  <div
                    className="h-full rounded-full"
                    style={{
                      width: `${pack.coverage}%`,
                      backgroundColor: pack.coverage >= 90 ? "#10B981" : pack.coverage >= 80 ? "#F59E0B" : "#EF4444",
                    }}
                  />
                </div>
                <span className="text-[10px] text-gray-500">{pack.coverage}%</span>
                {pack.gaps > 0 && (
                  <span className={`text-[10px] font-medium ${
                    pack.gaps > 5 ? "text-red-500" : "text-amber-500"
                  }`}>{pack.gaps} gaps</span>
                )}
              </div>
            </div>
            <button className="text-[10px] text-navy-600 dark:text-navy-200 hover:underline shrink-0">View</button>
          </div>
        ))}
      </div>
    </div>
  );
}

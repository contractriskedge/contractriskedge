"use client";

import { motion } from "framer-motion";
import { Info, FileText, BarChart3, ShieldCheck, BookOpen, History, Sparkles, AlertCircle, ChevronLeft } from "lucide-react";
import type { ComponentType, SVGProps } from "react";
import type { ReviewQueueItem, DrawerTabId, AIFinding } from "./types";

interface AICopilotDrawerProps {
  selected?: ReviewQueueItem | null;
  activeTab: DrawerTabId;
  onTabChange: (tab: DrawerTabId) => void;
  aiFindings: AIFinding[];
}

const TABS: { id: DrawerTabId; label: string; icon: ComponentType<SVGProps<SVGSVGElement>> }[] = [
  { id: "overview", label: "Overview", icon: Info },
  { id: "clause-analysis", label: "Clause Analysis", icon: FileText },
  { id: "benchmark", label: "Benchmark", icon: BarChart3 },
  { id: "guidance", label: "Negotiation Guidance", icon: Sparkles },
  { id: "workflow", label: "Workflow History", icon: History },
  { id: "recommendations", label: "AI Recommendations", icon: ShieldCheck },
  { id: "playbooks", label: "Related Playbooks", icon: BookOpen },
  { id: "audit", label: "Audit Trail", icon: AlertCircle },
];

function renderTabContent(selected: ReviewQueueItem | null, aiFindings: AIFinding[], activeTab: DrawerTabId) {
  if (!selected) {
    return (
      <div className="rounded-3xl border border-dashed border-slate-300 bg-slate-50 p-6 text-center text-sm text-slate-500 dark:border-navy-700 dark:bg-navy-900/60 dark:text-slate-400">
        Select a review item to surface legal intelligence, playbook guidance, and audit context.
      </div>
    );
  }

  switch (activeTab) {
    case "overview":
      return (
        <div className="space-y-4">
          <p className="text-sm text-slate-500 dark:text-slate-400">AI Legal Copilot is synthesizing risk, SLA, and clause context for this review.</p>
          <div className="rounded-3xl border border-slate-200 bg-white p-4 shadow-sm dark:border-navy-700 dark:bg-navy-950">
            <p className="text-xs uppercase tracking-[0.2em] text-slate-400">Current issue</p>
            <p className="mt-3 text-sm leading-6 text-slate-700 dark:text-slate-300">
              This contract is in the legal review stage and exhibits high-risk indemnity language with an elevated SLA breach likelihood.
            </p>
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            <div className="rounded-3xl border border-slate-200 bg-slate-50 p-4 dark:border-navy-700 dark:bg-navy-900">
              <p className="text-xs uppercase tracking-[0.18em] text-slate-400">SLA trend</p>
              <p className="mt-2 text-lg font-semibold text-navy-900 dark:text-white">At risk</p>
            </div>
            <div className="rounded-3xl border border-slate-200 bg-slate-50 p-4 dark:border-navy-700 dark:bg-navy-900">
              <p className="text-xs uppercase tracking-[0.18em] text-slate-400">Escalation recommendation</p>
              <p className="mt-2 text-lg font-semibold text-orange-600 dark:text-orange-300">Escalate to senior counsel</p>
            </div>
          </div>
        </div>
      );
    case "clause-analysis":
      return (
        <div className="space-y-4">
          <div className="rounded-3xl border border-slate-200 bg-white p-4 dark:border-navy-700 dark:bg-navy-950">
            <p className="text-xs uppercase tracking-[0.18em] text-slate-400">Risk explanation</p>
            <p className="mt-3 text-sm leading-6 text-slate-700 dark:text-slate-300">
              The indemnity clause is broader than corporate risk policy and may expose the company to uncapped third-party claims.
            </p>
          </div>
          <div className="rounded-3xl border border-slate-200 bg-slate-50 p-4 dark:border-navy-700 dark:bg-navy-900">
            <p className="text-xs uppercase tracking-[0.18em] text-slate-400">Related clause issues</p>
            <ul className="mt-3 space-y-2 text-sm text-slate-600 dark:text-slate-300">
              <li>• Missing DPA language detected</li>
              <li>• Liability threshold exceeds jurisdictional cap</li>
              <li>• Fallback clause available from compliance playbook</li>
            </ul>
          </div>
        </div>
      );
    case "benchmark":
      return (
        <div className="space-y-4">
          <div className="rounded-3xl border border-slate-200 bg-white p-4 shadow-sm dark:border-navy-700 dark:bg-navy-950">
            <p className="text-xs uppercase tracking-[0.18em] text-slate-400">Benchmark percentile</p>
            <p className="mt-3 text-3xl font-semibold text-navy-900 dark:text-white">{Math.round(selected.riskScore * 10)}%</p>
            <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">Compared to approved enterprise contracts</p>
          </div>
          <div className="rounded-3xl border border-slate-200 bg-slate-50 p-4 dark:border-navy-700 dark:bg-navy-900">
            <div className="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-300">
              <BarChart3 className="h-4 w-4" aria-hidden="true" />
              Benchmark indicates above-threshold risk for indemnity exposure.
            </div>
          </div>
        </div>
      );
    case "guidance":
      return (
        <div className="space-y-4">
          <div className="rounded-3xl border border-slate-200 bg-white p-4 dark:border-navy-700 dark:bg-navy-950">
            <p className="text-xs uppercase tracking-[0.18em] text-slate-400">Negotiation guidance</p>
            <p className="mt-3 text-sm leading-6 text-slate-700 dark:text-slate-300">
              Propose a counter-offer that preserves confidentiality indemnity while capping overall liability at the approved threshold.
            </p>
          </div>
          <div className="rounded-3xl border border-slate-200 bg-slate-50 p-4 dark:border-navy-700 dark:bg-navy-900">
            <p className="text-xs uppercase tracking-[0.18em] text-slate-400">Escalation recommendation</p>
            <p className="mt-3 text-sm leading-6 text-slate-700 dark:text-slate-300">
              Route to the dispute resolution playbook if counterparty refuses fallback language.
            </p>
          </div>
        </div>
      );
    case "workflow":
      return (
        <div className="space-y-4">
          <div className="rounded-3xl border border-slate-200 bg-white p-4 dark:border-navy-700 dark:bg-navy-950">
            <p className="text-xs uppercase tracking-[0.18em] text-slate-400">Workflow history</p>
            <ol className="mt-3 space-y-3 text-sm text-slate-600 dark:text-slate-300">
              <li>• Triage assigned to legal operations</li>
              <li>• Clause reviewed by Alice Chen</li>
              <li>• Escalation suggested due to SLA risk</li>
              <li>• Awaiting approval from VP Legal</li>
            </ol>
          </div>
        </div>
      );
    case "recommendations":
      return (
        <div className="space-y-4">
          {aiFindings.slice(0, 3).map((finding) => (
            <div key={finding.id} className="rounded-3xl border border-slate-200 bg-white p-4 dark:border-navy-700 dark:bg-navy-950">
              <div className="flex items-center justify-between gap-2">
                <p className="text-sm font-semibold text-navy-900 dark:text-white">{finding.title}</p>
                <span className="text-xs uppercase tracking-[0.18em] text-slate-400">{finding.severity}</span>
              </div>
              <p className="mt-3 text-sm leading-6 text-slate-600 dark:text-slate-300">{finding.description}</p>
              <p className="mt-3 text-sm font-semibold text-slate-800 dark:text-slate-200">Recommendation:</p>
              <p className="text-sm text-slate-600 dark:text-slate-300">{finding.recommendation}</p>
            </div>
          ))}
        </div>
      );
    case "playbooks":
      return (
        <div className="space-y-4">
          <div className="rounded-3xl border border-slate-200 bg-slate-50 p-4 dark:border-navy-700 dark:bg-navy-900">
            <p className="text-xs uppercase tracking-[0.18em] text-slate-400">Related playbooks</p>
            <p className="mt-3 text-sm leading-6 text-slate-700 dark:text-slate-300">
              Access the approved contract review playbook to align fallback language and escalation rules with corporate policy.
            </p>
          </div>
        </div>
      );
    case "audit":
      return (
        <div className="space-y-4">
          <div className="rounded-3xl border border-slate-200 bg-white p-4 dark:border-navy-700 dark:bg-navy-950">
            <p className="text-xs uppercase tracking-[0.18em] text-slate-400">Audit trail</p>
            <ul className="mt-3 space-y-2 text-sm text-slate-600 dark:text-slate-300">
              <li>• 09:12 AM — Review assigned to Alice Chen</li>
              <li>• 10:45 AM — AI risk alert generated</li>
              <li>• 11:05 AM — Escalation recommended</li>
              <li>• 11:27 AM — Clause annotation created</li>
            </ul>
          </div>
        </div>
      );
    default:
      return null;
  }
}

export function AICopilotDrawer({ selected, activeTab, onTabChange, aiFindings }: AICopilotDrawerProps) {
  return (
    <motion.aside
      initial={{ opacity: 0, x: 24 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.25, ease: "easeOut" }}
      className="flex h-full flex-col rounded-3xl border border-slate-200/70 bg-white/95 shadow-sm shadow-slate-200/20 dark:border-navy-700 dark:bg-navy-900/95"
      aria-label="AI legal copilot drawer"
    >
      <div className="border-b border-slate-200/70 p-5 dark:border-navy-700">
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="text-sm font-semibold text-navy-900 dark:text-white">AI Legal Copilot</p>
            <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">Contextual enterprise intelligence for the selected review</p>
          </div>
          <div className="inline-flex items-center gap-2 rounded-3xl bg-slate-100 px-3 py-2 text-xs text-slate-600 dark:bg-navy-800 dark:text-slate-300">
            <Sparkles className="h-4 w-4" aria-hidden="true" />
            Real-time
          </div>
        </div>
      </div>

      <div className="overflow-hidden border-b border-slate-200/70 dark:border-navy-700">
        <div className="flex gap-1 overflow-x-auto px-3 py-3">
          {TABS.map((tab) => {
            const Icon = tab.icon;
            const active = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => onTabChange(tab.id)}
                className={`inline-flex min-w-[9rem] items-center gap-2 rounded-2xl border px-3 py-2 text-xs font-semibold transition ${
                  active
                    ? "border-slate-300 bg-slate-100 text-slate-900 dark:border-navy-600 dark:bg-navy-800 dark:text-white"
                    : "border-transparent text-slate-500 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-navy-850"
                }`}
              >
                <Icon className="h-3.5 w-3.5" aria-hidden="true" />
                {tab.label}
              </button>
            );
          })}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-5">
        {renderTabContent(selected ?? null, aiFindings, activeTab)}
      </div>

      <div className="border-t border-slate-200/70 p-4 text-sm text-slate-500 dark:border-navy-700 dark:text-slate-400">
        <div className="flex items-center justify-between gap-2">
          <div className="inline-flex items-center gap-2">
            <Info className="h-4 w-4" aria-hidden="true" />
            <span>Legal issue details are correlated with corporate policy and escalation rules.</span>
          </div>
          <span className="flex items-center gap-2 text-xs uppercase tracking-[0.18em] text-slate-400">
            <ChevronLeft className="h-3.5 w-3.5" aria-hidden="true" />
            {selected ? "Review item selected" : "Awaiting selection"}
          </span>
        </div>
      </div>
    </motion.aside>
  );
}

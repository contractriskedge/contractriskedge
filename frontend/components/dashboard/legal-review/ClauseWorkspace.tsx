"use client";

import { motion } from "framer-motion";
import { Zap, Shield, BarChart3, FileText, BookOpen, ArrowRight, Sparkles, Clock3, MessageCircle } from "lucide-react";
import type { ReviewQueueItem, AIFinding } from "./types";

interface ClauseWorkspaceProps {
  selected?: ReviewQueueItem | null;
  aiFindings: AIFinding[];
  onOpenAction: (action: string) => void;
}

const sectionStyles = "rounded-3xl border border-slate-200/70 bg-slate-50 p-4 dark:border-navy-700 dark:bg-navy-900";

export function ClauseWorkspace({ selected, aiFindings, onOpenAction }: ClauseWorkspaceProps) {
  if (!selected) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex min-h-[560px] flex-col items-center justify-center rounded-3xl border border-dashed border-slate-300 bg-white/90 p-10 text-center shadow-sm shadow-slate-200/20 dark:border-navy-700 dark:bg-navy-950/80"
      >
        <Shield className="mb-4 h-12 w-12 text-slate-300 dark:text-slate-500" aria-hidden="true" />
        <h3 className="text-2xl font-semibold text-navy-900 dark:text-white">Select a review item to inspect</h3>
        <p className="mt-3 max-w-xl text-sm leading-6 text-slate-500 dark:text-slate-400">
          Drill down into clause risk, fallback language, benchmark recommendations, and negotiation guidance with AI-assisted analysis.
        </p>
      </motion.div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 18 }}
      animate={{ opacity: 1, y: 0 }}
      className="space-y-5"
    >
      <div className="grid gap-4 xl:grid-cols-[1fr_280px]">
        <div className={sectionStyles}>
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="text-xs uppercase tracking-[0.2em] text-slate-400">Clause intelligence</p>
              <h3 className="mt-2 text-lg font-semibold text-navy-900 dark:text-white">{selected.contractName}</h3>
              <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">{selected.vendor} · {selected.contractType}</p>
            </div>
            <span className="rounded-2xl border border-slate-200 bg-slate-100 px-3 py-2 text-sm font-semibold text-slate-700 dark:border-navy-700 dark:bg-navy-800 dark:text-slate-200">
              {selected.workflowStage.replace(/_/g, " ")}
            </span>
          </div>

          <div className="mt-6 grid gap-4 sm:grid-cols-2">
            <div className="rounded-3xl bg-white p-4 shadow-sm shadow-slate-200/20 dark:bg-navy-950 dark:shadow-black/10">
              <p className="text-xs uppercase tracking-[0.18em] text-slate-400">Risk score</p>
              <p className="mt-2 text-3xl font-semibold text-navy-900 dark:text-white">{selected.riskScore}</p>
              <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">AI confidence: {Math.round(selected.aiConfidence * 100)}%</p>
            </div>
            <div className="rounded-3xl bg-white p-4 shadow-sm shadow-slate-200/20 dark:bg-navy-950 dark:shadow-black/10">
              <p className="text-xs uppercase tracking-[0.18em] text-slate-400">Clause issues</p>
              <p className="mt-2 text-3xl font-semibold text-navy-900 dark:text-white">{selected.clauseIssues}</p>
              <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">Escalation: {selected.escalationStatus.replace(/_/g, " ")}</p>
            </div>
          </div>
        </div>

        <div className={sectionStyles}>
          <div className="flex items-center gap-3 text-slate-500 dark:text-slate-400">
            <Sparkles className="h-5 w-5 text-amber-500" aria-hidden="true" />
            <div>
              <p className="text-xs uppercase tracking-[0.2em]">AI Priorities</p>
              <p className="text-sm font-semibold text-navy-900 dark:text-white">Auto-prioritized review workload</p>
            </div>
          </div>

          <div className="mt-4 space-y-3">
            <div className="rounded-3xl border border-slate-200 bg-white p-4 dark:border-navy-700 dark:bg-navy-950">
              <p className="text-xs uppercase tracking-[0.18em] text-slate-400">Priority analysis</p>
              <p className="mt-2 text-sm leading-6 text-slate-600 dark:text-slate-300">
                This contract is flagged for immediate review based on high-risk vendor exposure and SLA breach potential.
              </p>
            </div>
            <div className="rounded-3xl border border-slate-200 bg-white p-4 dark:border-navy-700 dark:bg-navy-950">
              <p className="text-xs uppercase tracking-[0.18em] text-slate-400">Fallback clause</p>
              <p className="mt-2 text-sm leading-6 text-slate-600 dark:text-slate-300">
                A fallback clause is available from approved corporate playbooks to reduce liability and align with jurisdictional rules.
              </p>
            </div>
          </div>
        </div>
      </div>

      <div className={sectionStyles}>
        <div className="flex items-center justify-between gap-4">
          <div>
            <p className="text-xs uppercase tracking-[0.2em] text-slate-400">Clause review experience</p>
            <h3 className="mt-2 text-lg font-semibold text-navy-900 dark:text-white">Risk + clause insight</h3>
          </div>
          <div className="inline-flex items-center gap-2 rounded-full bg-slate-100 px-3 py-1 text-xs text-slate-600 dark:bg-navy-800 dark:text-slate-300">
            <Clock3 className="h-3.5 w-3.5" aria-hidden="true" />
            {selected.slaRemaining} remaining
          </div>
        </div>

        <div className="mt-5 grid gap-4 lg:grid-cols-[2fr_1fr]">
          <div className="rounded-3xl border border-slate-200 bg-white p-4 shadow-sm shadow-slate-200/10 dark:border-navy-700 dark:bg-navy-950 dark:shadow-black/10">
            <p className="text-xs uppercase tracking-[0.18em] text-slate-400">Clause text</p>
            <div className="mt-3 space-y-4 text-sm leading-7 text-slate-700 dark:text-slate-300">
              <p>
                The Supplier shall indemnify the Buyer against any and all claims, damages, losses, liabilities, and expenses arising from or related to breaches of confidentiality obligations and data protection requirements, subject to the limitations described under Section 7.4.
              </p>
              <p className="rounded-3xl border border-orange-100 bg-orange-50 p-4 text-slate-700 dark:border-orange-500/20 dark:bg-orange-500/10">
                AI alert: Liability clause exceeds approved threshold and should be narrowed to vendor indemnity for third-party claims only.
              </p>
              <p>
                Suggested fallback: Use approved playbook fallback language to cap liability at 100% of fees and exclude consequential damages while preserving indemnity for breach of confidentiality.
              </p>
            </div>
          </div>

          <div className="space-y-4">
            <div className="rounded-3xl border border-slate-200 bg-white p-4 shadow-sm shadow-slate-200/10 dark:border-navy-700 dark:bg-navy-950 dark:shadow-black/10">
              <p className="text-xs uppercase tracking-[0.18em] text-slate-400">AI recommendation</p>
              <p className="mt-3 text-sm leading-6 text-slate-700 dark:text-slate-300">
                Remove unilateral termination rights for convenience and replace with a mutual 60-day notice period to align with negotiation guidance.
              </p>
            </div>
            <div className="rounded-3xl border border-slate-200 bg-white p-4 shadow-sm shadow-slate-200/10 dark:border-navy-700 dark:bg-navy-950 dark:shadow-black/10">
              <p className="text-xs uppercase tracking-[0.18em] text-slate-400">Benchmark percentile</p>
              <div className="mt-3 flex items-center gap-3">
                <span className="text-3xl font-semibold text-navy-900 dark:text-white">{Math.round(selected.riskScore * 10)}%</span>
                <div>
                  <p className="text-sm text-slate-500 dark:text-slate-400">Above market threshold for similar SaaS contracts</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className={sectionStyles}>
        <div className="flex items-center justify-between gap-3">
          <div>
            <p className="text-xs uppercase tracking-[0.2em] text-slate-400">Negotiation guidance</p>
            <h3 className="mt-2 text-lg font-semibold text-navy-900 dark:text-white">Recommended next steps</h3>
          </div>
          <button
            onClick={() => onOpenAction("review analytics")}
            className="inline-flex items-center gap-2 rounded-2xl border border-slate-200 bg-slate-100 px-4 py-2 text-sm font-semibold text-slate-700 hover:border-slate-300 hover:bg-slate-200 transition dark:border-navy-700 dark:bg-navy-800 dark:text-slate-200"
          >
            <BarChart3 className="h-4 w-4" aria-hidden="true" />
            Open analytics
          </button>
        </div>

        <div className="grid gap-3 sm:grid-cols-2">
          <div className="rounded-3xl border border-slate-200 bg-white p-4 dark:border-navy-700 dark:bg-navy-950">
            <p className="text-sm font-semibold text-navy-900 dark:text-white">Fallback clause available</p>
            <p className="mt-2 text-sm leading-6 text-slate-600 dark:text-slate-300">
              Use approved fallback language from the corporate playbook to accelerate review and reduce legal risk.
            </p>
          </div>
          <div className="rounded-3xl border border-slate-200 bg-white p-4 dark:border-navy-700 dark:bg-navy-950">
            <p className="text-sm font-semibold text-navy-900 dark:text-white">Negotiation posture</p>
            <p className="mt-2 text-sm leading-6 text-slate-600 dark:text-slate-300">
              Propose a middle-ground amendment and track stakeholder acceptance through the workflow history panel.
            </p>
          </div>
        </div>
      </div>

      <div className={sectionStyles}>
        <div className="flex items-center gap-2 text-slate-500 dark:text-slate-400">
          <MessageCircle className="h-4 w-4" aria-hidden="true" />
          <p className="text-xs uppercase tracking-[0.2em]">Collaborative intelligence</p>
        </div>
        <div className="mt-4 grid gap-4 sm:grid-cols-2">
          {aiFindings.slice(0, 2).map((finding) => (
            <div key={finding.id} className="rounded-3xl border border-slate-200 bg-white p-4 dark:border-navy-700 dark:bg-navy-950">
              <div className="flex items-center justify-between gap-2">
                <p className="text-sm font-semibold text-navy-900 dark:text-white">{finding.title}</p>
                <span className="text-xs text-slate-500 dark:text-slate-400">{finding.severity}</span>
              </div>
              <p className="mt-3 text-sm leading-6 text-slate-600 dark:text-slate-300">{finding.description}</p>
              <p className="mt-3 text-xs uppercase tracking-[0.18em] text-slate-400">Recommendation</p>
              <p className="mt-1 text-sm text-slate-700 dark:text-slate-300">{finding.recommendation}</p>
            </div>
          ))}
        </div>
      </div>
    </motion.div>
  );
}

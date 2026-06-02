/**
 * GovernanceDashboard — Centralized governance view.
 *
 * Sprint 15 Phase 1E — Real data integration.
 *
 * All five widgets are now backed by live API data:
 * - Policy Exceptions  → GET /api/v1/human-oversight/exceptions/pending
 * - Approval Queue     → GET /api/v1/human-oversight/approvals/pending
 * - Compliance Packs   → GET /api/v1/compliance/frameworks
 * - AI Quality         → GET /api/v1/ai-governance/quality-dashboard
 * - Prompt Deployments → GET /api/v1/ai-governance/prompts
 */

"use client";

import React, { useState } from "react";
import { DashboardHeader } from "../command-center/DashboardHeader";
import {
  usePendingExceptions,
  usePendingApprovals,
  useComplianceFrameworks,
  useAIQualityDashboard,
  usePrompts,
  useDecideApproval,
  useReviewException,
} from "@/services/hooks";

type DateRange = "24h" | "7d" | "30d" | "90d";
type RefreshInterval = 0 | 15 | 30 | 60;

type SectionId = "exceptions" | "quality" | "approvals" | "prompts" | "compliance";

const SECTIONS: { id: SectionId; label: string }[] = [
  { id: "exceptions", label: "Policy Exceptions" },
  { id: "quality", label: "AI Quality" },
  { id: "approvals", label: "Approval Queue" },
  { id: "prompts", label: "Prompt Deployments" },
  { id: "compliance", label: "Compliance Packs" },
];

export function GovernanceDashboard() {
  const [activeSection, setActiveSection] = useState<SectionId>("exceptions");
  const [dateRange, setDateRange] = useState<DateRange>("30d");
  const [refreshInterval, setRefreshInterval] = useState<RefreshInterval>(0);
  const [reviewModal, setReviewModal] = useState<{
    type: "approval" | "exception";
    entityId: string;
    title: string;
  } | null>(null);

  const decideApproval = useDecideApproval();
  const reviewException = useReviewException();

  return (
    <div className="p-6 space-y-4">
      <DashboardHeader
        title="Governance Dashboard"
        description="Policy exceptions, AI quality, approval queue, prompt deployments, and compliance pack status"
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
        {activeSection === "exceptions" && <PolicyExceptionCenter onReview={(id, title) => setReviewModal({ type: "exception", entityId: id, title })} />}
        {activeSection === "quality" && <AIQualityRegressionTracker />}
        {activeSection === "approvals" && <ApprovalQueue onReview={(id, title) => setReviewModal({ type: "approval", entityId: id, title })} />}
        {activeSection === "prompts" && <PromptDeploymentTracker />}
        {activeSection === "compliance" && <CompliancePackStatus />}
      </div>

      {/* ── Review Decision Modal ─────────────────────────────── */}
      {reviewModal && (
        <ReviewModal
          type={reviewModal.type}
          entityId={reviewModal.entityId}
          title={reviewModal.title}
          onClose={() => setReviewModal(null)}
          onDecision={async (decision, notes) => {
            try {
              if (reviewModal.type === "approval") {
                await decideApproval.mutateAsync({
                  approvalId: reviewModal.entityId,
                  body: { decision, notes },
                });
              } else {
                await reviewException.mutateAsync({
                  exceptionId: reviewModal.entityId,
                  body: { decision, review_notes: notes },
                });
              }
              setReviewModal(null);
            } catch (err: any) {
              console.error("[GovernanceDashboard] Decision failed:", err);
              alert(`Decision failed: ${err?.message || err}`);
            }
          }}
        />
      )}
    </div>
  );
}

// ── Review Decision Modal ──────────────────────────────────────────────

interface ReviewModalProps {
  type: "approval" | "exception";
  entityId: string;
  title: string;
  onClose: () => void;
  onDecision: (decision: "approved" | "rejected", notes: string) => Promise<void>;
}

function ReviewModal({ type, entityId, title, onClose, onDecision }: ReviewModalProps) {
  const [decision, setDecision] = useState<"approved" | "rejected">("approved");
  const [notes, setNotes] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async () => {
    setSubmitting(true);
    try {
      await onDecision(decision, notes);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="bg-white dark:bg-navy-800 rounded-xl shadow-xl border border-gray-200 dark:border-navy-700 w-full max-w-md mx-4">
        <div className="px-4 py-3 border-b border-gray-100 dark:border-navy-700 flex items-center justify-between">
          <h3 className="text-sm font-semibold text-navy-900 dark:text-white">
            {type === "approval" ? "Review Approval" : "Review Exception"}
          </h3>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-lg leading-none">&times;</button>
        </div>
        <div className="p-4 space-y-3">
          <p className="text-xs text-gray-500">{title}</p>
          <div className="flex gap-2">
            <button
              onClick={() => setDecision("approved")}
              className={`flex-1 px-3 py-2 text-xs font-medium rounded-lg ${
                decision === "approved"
                  ? "bg-green-500 text-white"
                  : "bg-gray-100 dark:bg-navy-600 text-gray-600 dark:text-gray-300"
              }`}
            >
              Approve
            </button>
            <button
              onClick={() => setDecision("rejected")}
              className={`flex-1 px-3 py-2 text-xs font-medium rounded-lg ${
                decision === "rejected"
                  ? "bg-red-500 text-white"
                  : "bg-gray-100 dark:bg-navy-600 text-gray-600 dark:text-gray-300"
              }`}
            >
              Reject
            </button>
          </div>
          <textarea
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="Add review notes..."
            rows={3}
            className="w-full text-xs p-2 border border-gray-200 dark:border-navy-600 rounded-lg bg-white dark:bg-navy-700 text-navy-900 dark:text-white resize-none"
          />
        </div>
        <div className="px-4 py-3 border-t border-gray-100 dark:border-navy-700 flex justify-end gap-2">
          <button
            onClick={onClose}
            className="px-3 py-1.5 text-xs font-medium rounded-lg bg-gray-100 dark:bg-navy-600 text-gray-600 dark:text-gray-300"
          >
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            disabled={submitting}
            className={`px-3 py-1.5 text-xs font-medium rounded-lg text-white ${
              submitting ? "bg-gray-400" : decision === "approved" ? "bg-green-500" : "bg-red-500"
            }`}
          >
            {submitting ? "Submitting..." : decision === "approved" ? "Approve" : "Reject"}
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Shared Components ──────────────────────────────────────────────────

function LoadingCard({ title }: { title: string }) {
  return (
    <div className="bg-white dark:bg-navy-800 rounded-xl border border-gray-200 dark:border-navy-700 shadow-sm">
      <div className="px-4 py-3 border-b border-gray-100 dark:border-navy-700">
        <h3 className="text-sm font-semibold text-navy-900 dark:text-white">{title}</h3>
      </div>
      <div className="p-6 flex items-center justify-center">
        <div className="flex items-center gap-2 text-sm text-gray-400">
          <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
          Loading...
        </div>
      </div>
    </div>
  );
}

function EmptyCard({ title, message }: { title: string; message: string }) {
  return (
    <div className="bg-white dark:bg-navy-800 rounded-xl border border-gray-200 dark:border-navy-700 shadow-sm">
      <div className="px-4 py-3 border-b border-gray-100 dark:border-navy-700">
        <h3 className="text-sm font-semibold text-navy-900 dark:text-white">{title}</h3>
      </div>
      <div className="p-6 text-center text-sm text-gray-400">{message}</div>
    </div>
  );
}

function ErrorCard({ title, message, onRetry }: { title: string; message: string; onRetry?: () => void }) {
  return (
    <div className="bg-white dark:bg-navy-800 rounded-xl border border-red-200 dark:border-red-900/50 shadow-sm">
      <div className="px-4 py-3 border-b border-gray-100 dark:border-navy-700">
        <h3 className="text-sm font-semibold text-navy-900 dark:text-white">{title}</h3>
      </div>
      <div className="p-6 text-center">
        <p className="text-sm text-red-500 mb-2">{message}</p>
        {onRetry && (
          <button onClick={onRetry} className="text-xs text-navy-600 dark:text-navy-200 hover:underline">
            Retry
          </button>
        )}
      </div>
    </div>
  );
}

// ── Policy Exceptions (live: GET /api/v1/human-oversight/exceptions/pending) ──

function PolicyExceptionCenter({ onReview }: { onReview: (id: string, title: string) => void }) {
  const { data: exceptions, isLoading, isError, error, refetch } = usePendingExceptions();

  const severityColor = (s: string) =>
    s === "critical" ? "text-red-600 bg-red-50 dark:bg-red-900/20" :
    s === "high" ? "text-orange-600 bg-orange-50 dark:bg-orange-900/20" :
    s === "medium" ? "text-yellow-600 bg-yellow-50 dark:bg-yellow-900/20" :
    "text-blue-600 bg-blue-50 dark:bg-blue-900/20";

  if (isLoading) return <LoadingCard title="Active Policy Exceptions" />;
  if (isError) return <ErrorCard title="Active Policy Exceptions" message={error?.message ?? "Failed to load"} onRetry={refetch} />;
  if (!exceptions || exceptions.length === 0) return <EmptyCard title="Active Policy Exceptions" message="No pending policy exceptions" />;

  return (
    <div className="bg-white dark:bg-navy-800 rounded-xl border border-gray-200 dark:border-navy-700 shadow-sm">
      <div className="px-4 py-3 border-b border-gray-100 dark:border-navy-700 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-navy-900 dark:text-white">Active Policy Exceptions</h3>
        <span className="text-xs text-gray-500">{exceptions.length} pending</span>
      </div>
      <div className="p-4 space-y-2">
        {exceptions.map((exc) => (
          <div key={exc.exception_id} className="p-3 rounded-lg bg-gray-50 dark:bg-navy-700 flex items-start gap-3">
            <span className={`w-1.5 h-1.5 rounded-full mt-1.5 ${
              exc.severity === "critical" ? "bg-red-500" :
              exc.severity === "high" ? "bg-orange-500" :
              exc.severity === "medium" ? "bg-yellow-500" : "bg-blue-500"
            }`} />
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <span className="text-xs font-medium text-navy-900 dark:text-white">{exc.policy_name || exc.rule_name}</span>
                <span className={`text-[10px] px-1.5 py-0.5 rounded-full ${severityColor(exc.severity)}`}>
                  {exc.severity}
                </span>
              </div>
              <p className="text-[10px] text-gray-500 mt-0.5">{exc.justification}</p>
              <div className="flex items-center gap-3 mt-1 text-[10px] text-gray-400">
                <span>Requested by: {exc.requested_by}</span>
                {exc.expiration_date && (
                  <span className="font-medium">Expires: {new Date(exc.expiration_date).toLocaleDateString()}</span>
                )}
              </div>
            </div>
            <div className="flex gap-1 shrink-0">
              <button
                onClick={() => onReview(exc.exception_id, exc.policy_name || exc.rule_name)}
                className="px-2 py-1 text-[10px] font-medium rounded bg-gray-100 dark:bg-navy-600 text-gray-600 dark:text-gray-300 hover:bg-gray-200"
              >
                Review
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── AI Quality (live: GET /api/v1/ai-governance/quality-dashboard) ──

function AIQualityRegressionTracker() {
  const { data: quality, isLoading, isError, error, refetch } = useAIQualityDashboard();

  if (isLoading) return <LoadingCard title="AI Quality Score" />;
  if (isError) return <ErrorCard title="AI Quality Score" message={error?.message ?? "Failed to load quality data"} onRetry={refetch} />;
  if (!quality) return <EmptyCard title="AI Quality Score" message="No quality data available" />;

  const totalInferences = quality.total_inferences_24h;
  const successRate = quality.inference_success_rate_24h;
  const avgLatency = quality.avg_latency_ms_24h;
  const totalCost = quality.total_cost_24h;
  const regressions = quality.regressions_found_last_run;
  const passRate = quality.last_regression_pass_rate;

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
      {/* ── Quality Score Summary ─────────────────────────────── */}
      <div className="bg-white dark:bg-navy-800 rounded-xl border border-gray-200 dark:border-navy-700 shadow-sm">
        <div className="px-4 py-3 border-b border-gray-100 dark:border-navy-700">
          <h3 className="text-sm font-semibold text-navy-900 dark:text-white">Quality Score Trend</h3>
        </div>
        <div className="p-4 space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs text-gray-500">24h Inferences</span>
            <span className="text-sm font-bold text-navy-900 dark:text-white">{totalInferences.toLocaleString()}</span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-xs text-gray-500">Success Rate</span>
            <span className={`text-sm font-bold ${
              successRate >= 99 ? "text-green-500" :
              successRate >= 95 ? "text-yellow-500" : "text-red-500"
            }`}>
              {successRate}%
            </span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-xs text-gray-500">Regressions Found</span>
            <span className={`text-sm font-bold ${
              regressions === 0 ? "text-green-500" :
              regressions < 5 ? "text-yellow-500" : "text-red-500"
            }`}>
              {regressions}
            </span>
          </div>
          {passRate !== null && (
            <div className="flex items-center justify-between">
              <span className="text-xs text-gray-500">Last Regression Pass Rate</span>
              <span className={`text-sm font-bold ${
                passRate >= 90 ? "text-green-500" :
                passRate >= 80 ? "text-yellow-500" : "text-red-500"
              }`}>
                {passRate}%
              </span>
            </div>
          )}
          <div className="pt-2 border-t border-gray-100 dark:border-navy-700">
            <div className="flex items-center justify-between text-xs text-gray-500">
              <span>Active prompts: {quality.active_prompts}/{quality.total_prompts}</span>
              <span>Datasets: {quality.total_evaluation_datasets}</span>
              <span>Test cases: {quality.total_test_cases}</span>
            </div>
          </div>
        </div>
      </div>

      {/* ── 24h Model Usage ───────────────────────────────────── */}
      <div className="bg-white dark:bg-navy-800 rounded-xl border border-gray-200 dark:border-navy-700 shadow-sm">
        <div className="px-4 py-3 border-b border-gray-100 dark:border-navy-700">
          <h3 className="text-sm font-semibold text-navy-900 dark:text-white">Model Usage (24h)</h3>
        </div>
        <div className="p-4 space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs text-gray-500">Total Inferences</span>
            <span className="text-sm font-bold text-navy-900 dark:text-white">{totalInferences.toLocaleString()}</span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-xs text-gray-500">Total Cost</span>
            <span className="text-sm font-bold text-navy-900 dark:text-white">${totalCost.toFixed(2)}</span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-xs text-gray-500">Success Rate</span>
            <span className={`text-sm font-bold ${
              successRate >= 99 ? "text-green-500" :
              successRate >= 95 ? "text-yellow-500" : "text-red-500"
            }`}>
              {successRate}%
            </span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-xs text-gray-500">Avg Latency</span>
            <span className="text-sm font-bold text-navy-900 dark:text-white">{avgLatency}ms</span>
          </div>
          {quality.model_usage.length > 0 && (
            <div className="pt-2 border-t border-gray-100 dark:border-navy-700">
              <div className="text-[10px] text-gray-400 mb-1">Per-model breakdown</div>
              {quality.model_usage.map((m) => (
                <div key={m.model} className="flex items-center justify-between text-xs text-gray-500">
                  <span>{m.model} ({m.provider})</span>
                  <span>{m.inferences_24h} inferences, {m.total_tokens} tokens</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ── Approval Queue (live: GET /api/v1/human-oversight/approvals/pending) ──

function ApprovalQueue({ onReview }: { onReview: (id: string, title: string) => void }) {
  const { data: approvals, isLoading, isError, error, refetch } = usePendingApprovals();

  const priorityColor = (p: string) =>
    p === "critical" ? "text-red-600 bg-red-50 dark:bg-red-900/20" :
    p === "high" ? "text-orange-600 bg-orange-50 dark:bg-orange-900/20" :
    p === "normal" ? "text-yellow-600 bg-yellow-50 dark:bg-yellow-900/20" :
    "text-blue-600 bg-blue-50 dark:bg-blue-900/20";

  if (isLoading) return <LoadingCard title="Pending Approval Queue" />;
  if (isError) return <ErrorCard title="Pending Approval Queue" message={error?.message ?? "Failed to load"} onRetry={refetch} />;
  if (!approvals || approvals.length === 0) return <EmptyCard title="Pending Approval Queue" message="No pending approvals" />;

  return (
    <div className="bg-white dark:bg-navy-800 rounded-xl border border-gray-200 dark:border-navy-700 shadow-sm">
      <div className="px-4 py-3 border-b border-gray-100 dark:border-navy-700 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-navy-900 dark:text-white">Pending Approval Queue</h3>
        <span className="text-xs text-gray-500">{approvals.length} pending</span>
      </div>
      <div className="p-4 space-y-2">
        {approvals.map((a) => (
          <div key={a.approval_id} className="p-3 rounded-lg bg-gray-50 dark:bg-navy-700 flex items-start gap-3">
            <span className={`w-1.5 h-1.5 rounded-full mt-1.5 ${
              a.priority === "critical" ? "bg-red-500" :
              a.priority === "high" ? "bg-orange-500" :
              a.priority === "normal" ? "bg-yellow-500" : "bg-blue-500"
            }`} />
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <span className="text-xs font-medium text-navy-900 dark:text-white">{a.title}</span>
                <span className={`text-[10px] px-1.5 py-0.5 rounded-full ${priorityColor(a.priority)}`}>
                  {a.priority}
                </span>
              </div>
              <div className="flex items-center gap-3 mt-1 text-[10px] text-gray-400">
                <span>Type: {a.approval_type}</span>
                <span>Requested by: {a.requested_by}</span>
                <span>{new Date(a.requested_at).toLocaleDateString()}</span>
              </div>
              {a.confidence > 0 && (
                <div className="mt-1 text-[10px] text-gray-400">
                  AI confidence: {Math.round(a.confidence * 100)}%
                </div>
              )}
            </div>
            <div className="flex gap-1 shrink-0">
              <button
                onClick={() => onReview(a.approval_id, a.title)}
                className="px-2 py-1 text-[10px] font-medium rounded bg-gray-100 dark:bg-navy-600 text-gray-600 dark:text-gray-300 hover:bg-gray-200"
              >
                Review
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Prompt Deployments (live: GET /api/v1/ai-governance/prompts) ──

function PromptDeploymentTracker() {
  const { data: prompts, isLoading, isError, error, refetch } = usePrompts();

  if (isLoading) return <LoadingCard title="Prompt Deployment History" />;
  if (isError) return <ErrorCard title="Prompt Deployment History" message={error?.message ?? "Failed to load prompts"} onRetry={refetch} />;
  if (!prompts || prompts.length === 0) return <EmptyCard title="Prompt Deployment History" message="No prompts registered" />;

  return (
    <div className="bg-white dark:bg-navy-800 rounded-xl border border-gray-200 dark:border-navy-700 shadow-sm">
      <div className="px-4 py-3 border-b border-gray-100 dark:border-navy-700">
        <h3 className="text-sm font-semibold text-navy-900 dark:text-white">Prompt Deployment History</h3>
      </div>
      <div className="p-4">
        <table className="w-full text-xs">
          <thead>
            <tr className="text-gray-500 dark:text-gray-400">
              <th className="text-left pb-2 font-medium">Prompt Key</th>
              <th className="text-left pb-2 font-medium">Name</th>
              <th className="text-center pb-2 font-medium">Active Version</th>
              <th className="text-left pb-2 font-medium">State</th>
              <th className="text-left pb-2 font-medium">Tags</th>
              <th className="text-right pb-2 font-medium">Updated</th>
            </tr>
          </thead>
          <tbody>
            {prompts.map((p) => (
              <tr key={p.prompt_key} className="border-t border-gray-100 dark:border-navy-700">
                <td className="py-2 font-mono text-[10px] text-navy-900 dark:text-white">{p.prompt_key}</td>
                <td className="py-2 text-navy-900 dark:text-white">{p.name || "—"}</td>
                <td className="py-2 text-center font-medium text-navy-900 dark:text-white">v{p.active_version}</td>
                <td className="py-2">
                  <span className={`px-1.5 py-0.5 rounded-full text-[10px] font-medium ${
                    p.state === "active" ? "bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300" :
                    p.state === "draft" ? "bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300" :
                    "bg-gray-100 dark:bg-gray-700 text-gray-500 dark:text-gray-400"
                  }`}>
                    {p.state}
                  </span>
                </td>
                <td className="py-2">
                  <div className="flex gap-1 flex-wrap">
                    {(p.tags || []).map((t) => (
                      <span key={t} className="text-[10px] px-1 py-0.5 rounded bg-gray-100 dark:bg-navy-600 text-gray-500 dark:text-gray-400">
                        {t}
                      </span>
                    ))}
                  </div>
                </td>
                <td className="py-2 text-right text-gray-500">
                  {new Date(p.updated_at).toLocaleDateString()}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ── Compliance Packs (live: GET /api/v1/compliance/frameworks) ──

function CompliancePackStatus() {
  const { data: frameworksRes, isLoading, isError, error, refetch } = useComplianceFrameworks({ page: 1, page_size: 50 });

  if (isLoading) return <LoadingCard title="Compliance Pack Status" />;
  if (isError) return <ErrorCard title="Compliance Pack Status" message={error?.message ?? "Failed to load"} onRetry={refetch} />;

  const frameworks = frameworksRes?.data ?? [];

  if (frameworks.length === 0) return <EmptyCard title="Compliance Pack Status" message="No compliance frameworks configured" />;

  return (
    <div className="bg-white dark:bg-navy-800 rounded-xl border border-gray-200 dark:border-navy-700 shadow-sm">
      <div className="px-4 py-3 border-b border-gray-100 dark:border-navy-700 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-navy-900 dark:text-white">Compliance Pack Status</h3>
        <span className="text-xs text-gray-500">{frameworks.length} frameworks</span>
      </div>
      <div className="p-4 space-y-2">
        {frameworks.map((fw) => (
          <div key={fw.framework_id} className="flex items-center gap-3 p-3 rounded-lg bg-gray-50 dark:bg-navy-700">
            <span className="w-2 h-2 rounded-full bg-green-500" />
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <span className="text-xs font-medium text-navy-900 dark:text-white">{fw.name}</span>
                <span className="text-[10px] text-gray-400">{fw.category}</span>
              </div>
              <div className="flex items-center gap-3 mt-1">
                <div className="flex-1 h-1.5 bg-gray-200 dark:bg-navy-600 rounded-full overflow-hidden">
                  <div
                    className="h-full rounded-full bg-emerald-500"
                    style={{ width: `${Math.min(100, fw.control_count * 10)}%` }}
                  />
                </div>
                <span className="text-[10px] text-gray-500">{fw.control_count} controls</span>
                <span className="text-[10px] text-gray-400">v{fw.version}</span>
              </div>
            </div>
            <button className="text-[10px] text-navy-600 dark:text-navy-200 hover:underline shrink-0">View</button>
          </div>
        ))}
      </div>
    </div>
  );
}

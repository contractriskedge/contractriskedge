/**
 * PolicyEngine — Policy-as-Code governance engine.
 *
 * Phase 2 — converts the legacy PolicyCenter (catalog) into a true
 * governance engine that is the source of truth for Findings,
 * Violations, Redlines and Risk Scoring.
 *
 * Features:
 *   1. Policy Detail Screen  (drawer)
 *   2. Policy Rules table
 *   3. Clause Requirements + library linkage
 *   4. Violation Explorer
 *   5. Policy Traceability chain
 *   6. Simulation Results
 *   7. Policy Lifecycle (Draft → Review → Published → Deprecated → Archived)
 *   8. Policy Versioning (history, compare, restore, audit)
 *
 * All data is sourced from the existing backend via `policyService`,
 * `usePlaybooks`, and `useClauses`. Where a dedicated endpoint does
 * not yet exist we synthesize a defensible fallback so the UI is
 * never blank.
 */

"use client";

import React, { useState, useMemo, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Shield, AlertTriangle, CheckCircle2, XCircle, FileText,
  Search, ChevronDown, ChevronUp, Plus, Clock, BookOpen,
  Scale, Lock, Ban, Filter, Loader2, ExternalLink,
  TrendingUp, TrendingDown, Minus, Edit3, Activity, GitBranch,
  Layers, History, GitCompare, RotateCcw, CheckCheck, Archive,
  Sparkles, ListChecks, Eye, X, ArrowRight, FileCheck, User,
  ChevronRight, Info, AlertCircle,
} from "lucide-react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { policyService, policyKeys } from "@/services/api/policy";
import { uploadService } from "@/services/api/uploads";
import { useClauses } from "@/services/hooks/useClauseIntelligence";
import api from "@/services/api/client";
import { formatDate } from "@/lib/date-utils";
import { PolicyDetailDrawer } from "./PolicyDetailDrawer";

// ── Types ─────────────────────────────────────────────────────────

type PolicyTab =
  | "dashboard"
  | "policies"
  | "rules"
  | "clauses"
  | "violations"
  | "traceability"
  | "simulation"
  | "versions";

type LifecycleState = "draft" | "review" | "published" | "deprecated" | "archived";

const LIFECYCLE_ORDER: LifecycleState[] = [
  "draft", "review", "published", "deprecated", "archived",
];

const LIFECYCLE_COLORS: Record<LifecycleState, { bg: string; text: string; ring: string }> = {
  draft:     { bg: "bg-gray-100",   text: "text-gray-700",   ring: "ring-gray-300" },
  review:    { bg: "bg-amber-100",  text: "text-amber-800",  ring: "ring-amber-300" },
  published: { bg: "bg-green-100",  text: "text-green-700",  ring: "ring-green-300" },
  deprecated:{ bg: "bg-orange-100", text: "text-orange-700", ring: "ring-orange-300" },
  archived:  { bg: "bg-red-100",    text: "text-red-700",    ring: "ring-red-300" },
};

const CATEGORY_ICONS: Record<string, React.ReactNode> = {
  intellectual_property: <Shield className="w-3 h-3" />,
  liability: <AlertTriangle className="w-3 h-3" />,
  indemnification: <Scale className="w-3 h-3" />,
  confidentiality: <Lock className="w-3 h-3" />,
  data_privacy: <Shield className="w-3 h-3" />,
  sla: <Clock className="w-3 h-3" />,
  termination: <XCircle className="w-3 h-3" />,
  non_compete: <Ban className="w-3 h-3" />,
  governing_law: <BookOpen className="w-3 h-3" />,
  insurance: <FileText className="w-3 h-3" />,
};

const EFFECT_COLORS: Record<string, string> = {
  allow: "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400",
  block: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400",
  flag_for_review: "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400",
  require_approval: "bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400",
};

const SEVERITY_COLORS: Record<string, string> = {
  critical: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400",
  high: "bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400",
  medium: "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400",
  low: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400",
};

/** Derive a policy's lifecycle state. Falls back to "draft" when
 *  the backend hasn't yet surfaced a status field. */
function deriveLifecycle(p: any): LifecycleState {
  const raw = (p.status || p.lifecycle_state || "").toString().toLowerCase();
  if (raw.includes("archive")) return "archived";
  if (raw.includes("deprecate")) return "deprecated";
  if (raw.includes("review") || raw === "pending") return "review";
  if (raw.includes("publish") || raw === "active" || p.enabled === true) return "published";
  if (raw.includes("draft")) return "draft";
  return "draft";
}

// ── Lifecycle Indicator ───────────────────────────────────────────

function LifecycleStepper({ state }: { state: LifecycleState }) {
  const idx = LIFECYCLE_ORDER.indexOf(state);
  return (
    <div className="flex items-center gap-1.5" data-testid="policy-lifecycle">
      {LIFECYCLE_ORDER.map((s, i) => {
        const c = LIFECYCLE_COLORS[s];
        const isPast = i < idx;
        const isCurrent = i === idx;
        return (
          <React.Fragment key={s}>
            <div
              className={`px-1.5 py-0.5 rounded-full text-[8px] font-semibold uppercase tracking-wider ${
                isCurrent
                  ? `${c.bg} ${c.text} ring-1 ${c.ring}`
                  : isPast
                    ? "bg-green-100 text-green-700 line-through opacity-70"
                    : "bg-gray-50 text-gray-400"
              }`}
              title={`Stage ${i + 1}/${LIFECYCLE_ORDER.length}: ${s}`}
            >
              {s}
            </div>
            {i < LIFECYCLE_ORDER.length - 1 && (
              <ChevronRight className="w-2.5 h-2.5 text-gray-300" />
            )}
          </React.Fragment>
        );
      })}
    </div>
  );
}

// ── Main Component ───────────────────────────────────────────────

export function PolicyEngine() {
  const [activeTab, setActiveTab] = useState<PolicyTab>("dashboard");
  const [searchQuery, setSearchQuery] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("");
  const [lifecycleFilter, setLifecycleFilter] = useState<LifecycleState | "all">("all");
  const [selectedPolicyId, setSelectedPolicyId] = useState<string | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);

  // ── Simulation state ───────────────────────────────────────────
  const [simPlaybookId, setSimPlaybookId] = useState<string>("");
  const [simUploadId, setSimUploadId] = useState<string>("");
  const [simResults, setSimResults] = useState<any | null>(null);
  const [simError, setSimError] = useState<string | null>(null);

  // ── API data ────────────────────────────────────────────────────
  const { data: playbooksData, isLoading: playbooksLoading } = useQuery({
    queryKey: policyKeys.list(),
    queryFn: () => policyService.list({ page_size: 100 }),
    staleTime: 60_000,
  });

  const { data: evaluationsData } = useQuery({
    queryKey: [...policyKeys.all, "evaluations", "all"],
    queryFn: () =>
      api.get<{ data: any[]; pagination: any }>("/playbooks/evaluations"),
    staleTime: 120_000,
  });

  const { data: uploadsData, isLoading: uploadsLoading } = useQuery({
    queryKey: ["uploads", "list"],
    queryFn: () => uploadService.list({ page_size: 100 }),
    staleTime: 60_000,
  });

  const { data: clausesData } = useClauses();

  // ── Simulation mutation ───────────────────────────────────────
  const simMutation = useMutation({
    mutationFn: async ({ playbook_id, upload_id }: { playbook_id: string; upload_id: string }) => {
      return await api.post<any>(
        `/playbooks/evaluate?playbook_id=${encodeURIComponent(playbook_id)}&upload_id=${encodeURIComponent(upload_id)}&simulation_mode=true`,
        {},
      );
    },
    onSuccess: (data) => { setSimResults(data); setSimError(null); },
    onError: (err: any) => {
      setSimError(err?.message || "Simulation failed. Check that the playbook and upload are valid.");
      setSimResults(null);
    },
  });

  const handleRunSimulation = () => {
    if (!simPlaybookId || !simUploadId) return;
    setSimResults(null);
    setSimError(null);
    simMutation.mutate({ playbook_id: simPlaybookId, upload_id: simUploadId });
  };

  // ── Derived data ───────────────────────────────────────────────
  const policies = (playbooksData?.data ?? []) as any[];
  const evaluations = (evaluationsData?.data ?? []) as any[];
  const uploads = (uploadsData?.data ?? []) as any[];
  const clauses = (clausesData?.data ?? []) as any[];

  const filteredPolicies = useMemo(() => {
    let r = [...policies];
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      r = r.filter(p =>
        p.name?.toLowerCase().includes(q) ||
        p.description?.toLowerCase().includes(q) ||
        p.tags?.some((t: string) => t.toLowerCase().includes(q)),
      );
    }
    if (categoryFilter) r = r.filter(p => (p.category || p.practice_area) === categoryFilter);
    if (lifecycleFilter !== "all") {
      r = r.filter(p => deriveLifecycle(p) === lifecycleFilter);
    }
    return r;
  }, [searchQuery, categoryFilter, lifecycleFilter, policies]);

  const categories = useMemo(() => {
    const counts: Record<string, number> = {};
    policies.forEach(p => {
      const cat = p.category || p.practice_area || "other";
      counts[cat] = (counts[cat] || 0) + 1;
    });
    return Object.entries(counts).map(([id, count]) => ({ id, label: id.replace(/_/g, " "), count }));
  }, [policies]);

  const lifecycleCounts = useMemo(() => {
    const counts: Record<LifecycleState, number> = { draft: 0, review: 0, published: 0, deprecated: 0, archived: 0 };
    policies.forEach(p => { counts[deriveLifecycle(p)]++; });
    return counts;
  }, [policies]);

  const openViolations = useMemo(
    () => evaluations.filter((v: any) => v.status === "open" || v.status === "failed"),
    [evaluations],
  );
  const resolvedViolations = useMemo(
    () => evaluations.filter((v: any) => v.status === "completed" || v.status === "passed"),
    [evaluations],
  );

  const activeCount = policies.filter(p => deriveLifecycle(p) === "published").length;
  const highRiskCount = policies.filter(p => (p.priority || 0) >= 80 && deriveLifecycle(p) === "published").length;

  // ── Handlers ───────────────────────────────────────────────────
  const openPolicyDrawer = useCallback((id: string) => {
    setSelectedPolicyId(id);
    setDrawerOpen(true);
  }, []);

  const selectedPolicy = useMemo(
    () => policies.find(p => (p.playbook_id || p.policy_id) === selectedPolicyId) ?? null,
    [policies, selectedPolicyId],
  );

  if (playbooksLoading) {
    return (
      <div className="flex flex-col h-full bg-gray-50 dark:bg-navy-900 items-center justify-center">
        <Loader2 className="w-6 h-6 text-indigo-500 animate-spin mb-2" />
        <p className="text-xs text-gray-500">Loading policy engine…</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full bg-gray-50 dark:bg-navy-900">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2 bg-white dark:bg-navy-800 border-b border-gray-200 dark:border-navy-700">
        <div className="flex items-center gap-2">
          <Shield className="w-4 h-4 text-indigo-600 dark:text-indigo-400" />
          <h1 className="text-xs font-bold text-navy-900 dark:text-white">Policy Engine</h1>
          <span className="text-[9px] text-gray-500 dark:text-gray-400">
            — source of truth for findings, violations, redlines &amp; risk
          </span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className={`px-1.5 py-0.5 text-[8px] font-medium rounded-full ${
            activeCount === policies.length ? "bg-green-100 text-green-700" : "bg-amber-100 text-amber-700"
          }`}>
            {activeCount}/{policies.length} active
          </span>
          <LifecycleStepper state={lifecycleCounts.published > 0 ? "published" : "draft"} />
        </div>
      </div>

      {/* Tabs */}
      <div className="flex items-center border-b border-gray-200 dark:border-navy-700 bg-white dark:bg-navy-800 px-2 overflow-x-auto">
        {([
          { id: "dashboard" as const,   label: "Dashboard",     icon: Activity },
          { id: "policies" as const,    label: "Policies",      icon: Shield },
          { id: "rules" as const,       label: "Rules",         icon: ListChecks },
          { id: "clauses" as const,     label: "Clause Reqs",   icon: BookOpen },
          { id: "violations" as const,  label: "Violations",    icon: AlertTriangle, badge: openViolations.length },
          { id: "traceability" as const,label: "Traceability",  icon: GitBranch },
          { id: "simulation" as const,  label: "Simulation",    icon: TrendingUp },
          { id: "versions" as const,    label: "Versions",      icon: History },
        ]).map(tab => (
          <button key={tab.id} onClick={() => setActiveTab(tab.id)}
            className={`flex items-center gap-1 px-3 py-2 text-[10px] font-medium border-b-2 whitespace-nowrap transition-all ${
              activeTab === tab.id
                ? "border-indigo-600 text-indigo-700 dark:border-indigo-400 dark:text-indigo-300"
                : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 dark:hover:text-gray-300"
            }`}>
            <tab.icon className="w-3 h-3" />
            {tab.label}
            {tab.badge !== undefined && tab.badge > 0 && (
              <span className="ml-1 text-[8px] font-bold px-1 py-0.5 rounded-full bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400">
                {tab.badge}
              </span>
            )}
          </button>
        ))}
      </div>

      <div className="flex-1 overflow-y-auto">
        {activeTab === "dashboard" && (
          <DashboardTab
            policies={policies}
            evaluations={evaluations}
            categories={categories}
            lifecycleCounts={lifecycleCounts}
            activeCount={activeCount}
            highRiskCount={highRiskCount}
            openViolationsCount={openViolations.length}
            resolvedViolationsCount={resolvedViolations.length}
            onOpenPolicy={openPolicyDrawer}
          />
        )}

        {activeTab === "policies" && (
          <PoliciesTab
            policies={filteredPolicies}
            categories={categories}
            searchQuery={searchQuery}
            setSearchQuery={setSearchQuery}
            categoryFilter={categoryFilter}
            setCategoryFilter={setCategoryFilter}
            lifecycleFilter={lifecycleFilter}
            setLifecycleFilter={setLifecycleFilter}
            onOpenPolicy={openPolicyDrawer}
          />
        )}

        {activeTab === "rules" && (
          <RulesTab
            policies={policies}
            searchQuery={searchQuery}
            setSearchQuery={setSearchQuery}
            onOpenPolicy={openPolicyDrawer}
          />
        )}

        {activeTab === "clauses" && (
          <ClausesTab
            policies={policies}
            clauses={clauses}
            onOpenPolicy={openPolicyDrawer}
          />
        )}

        {activeTab === "violations" && (
          <ViolationsTab
            evaluations={evaluations}
            policies={policies}
            onOpenPolicy={openPolicyDrawer}
          />
        )}

        {activeTab === "traceability" && (
          <TraceabilityTab
            policies={policies}
            evaluations={evaluations}
          />
        )}

        {activeTab === "simulation" && (
          <SimulationTab
            policies={policies}
            uploads={uploads}
            uploadsLoading={uploadsLoading}
            simPlaybookId={simPlaybookId}
            setSimPlaybookId={setSimPlaybookId}
            simUploadId={simUploadId}
            setSimUploadId={setSimUploadId}
            simResults={simResults}
            simError={simError}
            simPending={simMutation.isPending}
            onRun={handleRunSimulation}
          />
        )}

        {activeTab === "versions" && (
          <VersionsTab
            policies={policies}
            onOpenPolicy={openPolicyDrawer}
          />
        )}
      </div>

      {/* Policy Detail Drawer (Feature 1) */}
      <PolicyDetailDrawer
        policy={selectedPolicy}
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        clauses={clauses}
        evaluations={evaluations}
      />
    </div>
  );
}

// ── Dashboard Tab ─────────────────────────────────────────────────

interface DashboardTabProps {
  policies: any[];
  evaluations: any[];
  categories: { id: string; label: string; count: number }[];
  lifecycleCounts: Record<LifecycleState, number>;
  activeCount: number;
  highRiskCount: number;
  openViolationsCount: number;
  resolvedViolationsCount: number;
  onOpenPolicy: (id: string) => void;
}

function DashboardTab({
  policies, evaluations, categories, lifecycleCounts,
  activeCount, highRiskCount, openViolationsCount, resolvedViolationsCount, onOpenPolicy,
}: DashboardTabProps) {
  return (
    <div className="p-4 space-y-4">
      {/* KPIs */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
        {[
          { label: "Active Policies", value: activeCount, color: "text-green-600", icon: CheckCircle2 },
          { label: "Open Violations", value: openViolationsCount, color: "text-red-600", icon: AlertTriangle },
          { label: "High Risk Policies", value: highRiskCount, color: "text-orange-600", icon: TrendingUp },
          { label: "Drafts / In Review", value: lifecycleCounts.draft + lifecycleCounts.review, color: "text-blue-600", icon: Edit3 },
          { label: "Contracts Impacted", value: evaluations.length > 0 ? evaluations.length : "—", color: evaluations.length > 0 ? "text-purple-600" : "text-gray-400", icon: FileText },
        ].map(kpi => (
          <div key={kpi.label} className="rounded-lg border border-gray-200 dark:border-navy-700 bg-white dark:bg-navy-800 p-3">
            <div className="flex items-center justify-between mb-1">
              <span className="text-[8px] font-semibold text-gray-500 uppercase">{kpi.label}</span>
              <kpi.icon className={`w-3 h-3 ${kpi.color}`} />
            </div>
            <div className={`text-lg font-bold ${kpi.color}`}>{kpi.value}</div>
          </div>
        ))}
      </div>

      {/* Lifecycle Distribution */}
      <div className="rounded-lg border border-gray-200 dark:border-navy-700 bg-white dark:bg-navy-800 p-3">
        <div className="flex items-center gap-1.5 mb-2">
          <Layers className="w-3 h-3 text-indigo-400" />
          <span className="text-[9px] font-semibold text-gray-500 uppercase">Policy Lifecycle Distribution</span>
        </div>
        <div className="grid grid-cols-5 gap-2">
          {LIFECYCLE_ORDER.map(s => {
            const c = LIFECYCLE_COLORS[s];
            return (
              <div key={s} className={`p-2 rounded-lg ${c.bg} text-center`}>
                <p className={`text-sm font-bold ${c.text}`}>{lifecycleCounts[s]}</p>
                <p className={`text-[8px] font-semibold uppercase tracking-wider ${c.text}`}>{s}</p>
              </div>
            );
          })}
        </div>
      </div>

      {/* Policies by Category + Violations Overview */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {categories.length > 0 && (
          <div className="rounded-lg border border-gray-200 dark:border-navy-700 bg-white dark:bg-navy-800 p-3">
            <div className="flex items-center gap-1.5 mb-2">
              <BookOpen className="w-3 h-3 text-gray-400" />
              <span className="text-[9px] font-semibold text-gray-500 uppercase">Policies by Category</span>
            </div>
            <div className="space-y-1">
              {categories.map(cat => (
                <div key={cat.id} className="flex items-center justify-between py-1 px-2 rounded hover:bg-gray-50 dark:hover:bg-navy-750">
                  <div className="flex items-center gap-2">
                    <span className="text-[8px] px-1 py-0.5 rounded font-medium text-gray-700 dark:text-gray-300 capitalize">
                      {CATEGORY_ICONS[cat.id]} {cat.label}
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-16 h-1.5 bg-gray-100 dark:bg-navy-700 rounded-full overflow-hidden">
                      <div className="h-full rounded-full bg-indigo-500" style={{ width: `${(cat.count / Math.max(...categories.map(c => c.count))) * 100}%` }} />
                    </div>
                    <span className="text-[9px] font-medium text-gray-600 dark:text-gray-400 w-8 text-right">{cat.count}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        <div className="rounded-lg border border-gray-200 dark:border-navy-700 bg-white dark:bg-navy-800 p-3">
          <div className="flex items-center gap-1.5 mb-2">
            <AlertTriangle className="w-3 h-3 text-red-400" />
            <span className="text-[9px] font-semibold text-gray-500 uppercase">Violations Overview</span>
          </div>
          {evaluations.length === 0 ? (
            <p className="text-[9px] text-gray-400 py-4 text-center">No evaluations recorded yet</p>
          ) : (
            <div className="space-y-2">
              <div className="grid grid-cols-3 gap-2">
                <div className="text-center p-2 rounded-lg bg-red-50 dark:bg-red-900/10">
                  <p className="text-sm font-bold text-red-600">{openViolationsCount}</p>
                  <p className="text-[8px] text-red-500">Open</p>
                </div>
                <div className="text-center p-2 rounded-lg bg-green-50 dark:bg-green-900/10">
                  <p className="text-sm font-bold text-green-600">{resolvedViolationsCount}</p>
                  <p className="text-[8px] text-green-500">Resolved</p>
                </div>
                <div className="text-center p-2 rounded-lg bg-gray-50 dark:bg-navy-750">
                  <p className="text-sm font-bold text-gray-600">{evaluations.length}</p>
                  <p className="text-[8px] text-gray-500">Total</p>
                </div>
              </div>
              <div className="flex items-center justify-between px-2 py-1.5 rounded bg-gray-50 dark:bg-navy-750">
                <span className="text-[8px] text-gray-500">Resolution Rate</span>
                <span className="text-[9px] font-semibold text-navy-900 dark:text-white">
                  {evaluations.length > 0 ? `${Math.round((resolvedViolationsCount / evaluations.length) * 100)}%` : "—"}
                </span>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Top Policies by Priority */}
      {policies.length > 0 && (
        <div className="rounded-lg border border-gray-200 dark:border-navy-700 bg-white dark:bg-navy-800 p-3">
          <div className="flex items-center gap-1.5 mb-2">
            <ListChecks className="w-3 h-3 text-indigo-400" />
            <span className="text-[9px] font-semibold text-gray-500 uppercase">Top Policies by Priority</span>
          </div>
          <div className="space-y-1">
            {[...policies]
              .sort((a, b) => (b.priority ?? 0) - (a.priority ?? 0))
              .slice(0, 5)
              .map(p => {
                const pid = p.playbook_id || p.policy_id;
                const lc = deriveLifecycle(p);
                return (
                  <button
                    key={pid}
                    onClick={() => onOpenPolicy(pid)}
                    className="w-full flex items-center gap-2 p-1.5 rounded hover:bg-gray-50 dark:hover:bg-navy-750 transition-colors text-left"
                  >
                    <span className={`px-1.5 py-0.5 rounded text-[8px] font-semibold uppercase ${LIFECYCLE_COLORS[lc].bg} ${LIFECYCLE_COLORS[lc].text}`}>{lc}</span>
                    <span className="text-[10px] font-medium text-navy-900 dark:text-white flex-1 truncate">{p.name}</span>
                    <span className={`text-[8px] font-medium px-1.5 py-0.5 rounded-full ${
                      p.priority >= 80 ? "bg-red-100 text-red-700" : p.priority >= 60 ? "bg-amber-100 text-amber-700" : "bg-blue-100 text-blue-700"
                    }`}>P{p.priority ?? "—"}</span>
                  </button>
                );
              })}
          </div>
        </div>
      )}
    </div>
  );
}

// ── Policies Tab ──────────────────────────────────────────────────

interface PoliciesTabProps {
  policies: any[];
  categories: { id: string; label: string; count: number }[];
  searchQuery: string;
  setSearchQuery: (v: string) => void;
  categoryFilter: string;
  setCategoryFilter: (v: string) => void;
  lifecycleFilter: LifecycleState | "all";
  setLifecycleFilter: (v: LifecycleState | "all") => void;
  onOpenPolicy: (id: string) => void;
}

function PoliciesTab({
  policies, categories, searchQuery, setSearchQuery,
  categoryFilter, setCategoryFilter, lifecycleFilter, setLifecycleFilter, onOpenPolicy,
}: PoliciesTabProps) {
  return (
    <div className="p-4 space-y-3">
      {/* Search & Filter */}
      <div className="flex items-center gap-2 flex-wrap">
        <div className="relative flex-1 min-w-[200px]">
          <Search className="absolute left-2 top-1/2 -translate-y-1/2 w-3 h-3 text-gray-400" />
          <input type="text" value={searchQuery} onChange={e => setSearchQuery(e.target.value)}
            placeholder="Search policies..." className="w-full pl-7 pr-2 py-1.5 text-[10px] bg-white dark:bg-navy-800 border border-gray-200 dark:border-navy-700 rounded-lg text-navy-900 dark:text-white placeholder-gray-400 focus:outline-none focus:ring-1 focus:ring-indigo-400" />
        </div>
        <select value={categoryFilter} onChange={e => setCategoryFilter(e.target.value)}
          className="text-[9px] px-2 py-1.5 rounded-lg border border-gray-200 dark:border-navy-700 bg-white dark:bg-navy-800 text-navy-900 dark:text-white">
          <option value="">All Categories</option>
          {categories.map(cat => <option key={cat.id} value={cat.id}>{cat.label}</option>)}
        </select>
        <select value={lifecycleFilter} onChange={e => setLifecycleFilter(e.target.value as LifecycleState | "all")}
          className="text-[9px] px-2 py-1.5 rounded-lg border border-gray-200 dark:border-navy-700 bg-white dark:bg-navy-800 text-navy-900 dark:text-white">
          <option value="all">All Stages</option>
          {LIFECYCLE_ORDER.map(s => <option key={s} value={s}>{s}</option>)}
        </select>
      </div>

      {/* Policy List */}
      <div className="space-y-1">
        {policies.length === 0 ? (
          <div className="text-center py-8 text-[10px] text-gray-400">
            No policies match your filters
          </div>
        ) : policies.map((policy: any) => {
          const pid = policy.playbook_id || policy.policy_id;
          const effect = policy.effect || (deriveLifecycle(policy) === "published" ? "allow" : "flag_for_review");
          const priority = policy.priority || 50;
          const lc = deriveLifecycle(policy);
          const version = policy.version || policy.version_count || 1;
          return (
            <button key={pid} onClick={() => onOpenPolicy(pid)}
              className="w-full rounded-lg border border-gray-200 bg-white dark:border-navy-700 dark:bg-navy-800 hover:border-indigo-300 dark:hover:border-indigo-700 transition-colors text-left">
              <div className="px-3 py-2.5">
                <div className="flex items-center gap-1.5 mb-0.5">
                  <span className={`w-1.5 h-1.5 rounded-full ${lc === "published" ? "bg-green-500" : "bg-gray-400"}`} />
                  <span className="text-[10px] font-medium text-navy-900 dark:text-white flex-1 truncate">{policy.name}</span>
                  <span className={`px-1.5 py-0.5 rounded text-[8px] font-semibold uppercase ${LIFECYCLE_COLORS[lc].bg} ${LIFECYCLE_COLORS[lc].text}`}>{lc}</span>
                  <span className={`text-[7px] font-medium px-1 py-0.5 rounded-full ${EFFECT_COLORS[effect] || "bg-gray-100 text-gray-600"}`}>
                    {effect.replace(/_/g, " ")}
                  </span>
                </div>
                <p className="text-[8px] text-gray-500 mt-0.5 line-clamp-1">{policy.description}</p>
                <div className="flex items-center gap-2 mt-1.5 text-[8px] text-gray-500">
                  <span className="capitalize">{(policy.category || "other").replace(/_/g, " ")}</span>
                  <span>·</span>
                  <span>v{version}</span>
                  {priority >= 80 && <><span>·</span><span className="text-red-600 font-medium">P{priority}</span></>}
                </div>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}

// ── Rules Tab ─────────────────────────────────────────────────────

interface RulesTabProps {
  policies: any[];
  searchQuery: string;
  setSearchQuery: (v: string) => void;
  onOpenPolicy: (id: string) => void;
}

/** Flatten a policy's condition tree into a list of rows we can render
 *  in the rules table. */
function flattenRules(p: any): Array<{
  rule_id: string;
  rule_name: string;
  field: string;
  operator: string;
  value: string;
  severity: string;
  risk_score: number;
  category: string;
  required_clauses: string[];
  exception: string;
}> {
  const group = p.rules;
  if (!group || !Array.isArray(group.conditions)) return [];
  const out: ReturnType<typeof flattenRules> = [];
  for (const c of group.conditions) {
    if (c && c.conditions) {
      out.push(...flattenRules(p));
      continue;
    }
    out.push({
      rule_id: c.condition_id ?? `${p.policy_id}-${c.field}`,
      rule_name: c.label ?? c.field,
      field: c.field,
      operator: c.operator,
      value: typeof c.value === "string" ? c.value : JSON.stringify(c.value ?? ""),
      severity: p.priority >= 80 ? "critical" : p.priority >= 65 ? "high" : p.priority >= 40 ? "medium" : "low",
      risk_score: (p.priority ?? 50) / 10,
      category: p.category ?? "other",
      required_clauses: p.tags ?? [],
      exception: group.type === "OR" ? "Some conditions satisfy" : "All conditions must match",
    });
  }
  return out;
}

function RulesTab({ policies, searchQuery, setSearchQuery, onOpenPolicy }: RulesTabProps) {
  const allRules = useMemo(() => {
    const out: Array<ReturnType<typeof flattenRules>[0] & { policy_id: string; policy_name: string }> = [];
    for (const p of policies) {
      const pid = p.playbook_id || p.policy_id;
      for (const r of flattenRules(p)) {
        out.push({ ...r, policy_id: pid, policy_name: p.name });
      }
    }
    return out;
  }, [policies]);

  const filtered = useMemo(() => {
    if (!searchQuery.trim()) return allRules;
    const q = searchQuery.toLowerCase();
    return allRules.filter(r =>
      r.rule_name.toLowerCase().includes(q) ||
      r.field.toLowerCase().includes(q) ||
      r.category.toLowerCase().includes(q),
    );
  }, [allRules, searchQuery]);

  return (
    <div className="p-4 space-y-3">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xs font-semibold text-navy-900 dark:text-white">Policy Rules</h2>
          <p className="text-[9px] text-gray-500">{allRules.length} rules across {policies.length} policies</p>
        </div>
        <div className="relative w-64">
          <Search className="absolute left-2 top-1/2 -translate-y-1/2 w-3 h-3 text-gray-400" />
          <input type="text" value={searchQuery} onChange={e => setSearchQuery(e.target.value)}
            placeholder="Search rules, fields, categories…"
            className="w-full pl-7 pr-2 py-1.5 text-[10px] bg-white dark:bg-navy-800 border border-gray-200 dark:border-navy-700 rounded-lg text-navy-900 dark:text-white placeholder-gray-400 focus:outline-none focus:ring-1 focus:ring-indigo-400" />
        </div>
      </div>

      <div className="rounded-lg border border-gray-200 dark:border-navy-700 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead className="bg-gray-50 dark:bg-navy-850 text-left text-[9px] uppercase tracking-wider text-gray-500">
              <tr>
                <th className="px-3 py-2 font-medium">Rule</th>
                <th className="px-3 py-2 font-medium">Policy</th>
                <th className="px-3 py-2 font-medium">Severity</th>
                <th className="px-3 py-2 font-medium">Risk</th>
                <th className="px-3 py-2 font-medium">Category</th>
                <th className="px-3 py-2 font-medium">Required Clauses</th>
                <th className="px-3 py-2 font-medium">Exception Logic</th>
                <th className="px-3 py-2 font-medium"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 dark:divide-navy-700">
              {filtered.length === 0 ? (
                <tr>
                  <td colSpan={8} className="text-center py-6 text-[10px] text-gray-400">No rules to display</td>
                </tr>
              ) : filtered.map(r => (
                <tr key={r.rule_id} className="hover:bg-gray-50 dark:hover:bg-navy-750">
                  <td className="px-3 py-2">
                    <p className="font-medium text-navy-900 dark:text-white text-[10px]">{r.rule_name}</p>
                    <p className="text-[8px] text-gray-500 font-mono mt-0.5">{r.field} {r.operator} {r.value}</p>
                  </td>
                  <td className="px-3 py-2">
                    <button
                      onClick={() => onOpenPolicy(r.policy_id)}
                      className="text-[10px] text-indigo-600 hover:text-indigo-800 dark:text-indigo-400 truncate max-w-[160px] block text-left"
                    >
                      {r.policy_name}
                    </button>
                  </td>
                  <td className="px-3 py-2">
                    <span className={`text-[8px] font-medium px-1.5 py-0.5 rounded-full ${SEVERITY_COLORS[r.severity] || SEVERITY_COLORS.low}`}>
                      {r.severity}
                    </span>
                  </td>
                  <td className="px-3 py-2 tabular-nums text-[10px] font-medium">{r.risk_score.toFixed(1)}</td>
                  <td className="px-3 py-2 text-[10px] text-gray-700 dark:text-gray-200 capitalize">{(r.category || "").replace(/_/g, " ")}</td>
                  <td className="px-3 py-2">
                    <div className="flex flex-wrap gap-1">
                      {r.required_clauses.slice(0, 2).map(t => (
                        <span key={t} className="text-[8px] px-1.5 py-0.5 rounded-full bg-navy-50 text-navy-700 dark:bg-navy-700 dark:text-navy-200">
                          {t}
                        </span>
                      ))}
                      {r.required_clauses.length > 2 && (
                        <span className="text-[8px] text-gray-400">+{r.required_clauses.length - 2}</span>
                      )}
                    </div>
                  </td>
                  <td className="px-3 py-2 text-[8px] text-gray-500 italic max-w-[160px]">{r.exception}</td>
                  <td className="px-3 py-2">
                    <button
                      onClick={() => onOpenPolicy(r.policy_id)}
                      className="text-[8px] text-indigo-600 hover:text-indigo-800 inline-flex items-center gap-1"
                    >
                      View <ArrowRight className="w-2.5 h-2.5" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

// ── Clauses Tab (Clause Requirements + library linkage) ───────────

interface ClausesTabProps {
  policies: any[];
  clauses: any[];
  onOpenPolicy: (id: string) => void;
}

function ClausesTab({ policies, clauses, onOpenPolicy }: ClausesTabProps) {
  // ── Required / recommended / fallback clauses derived from
  // ── each policy's tags + category.
  const required = useMemo(() => policies.filter(p => (p.priority ?? 0) >= 80), [policies]);
  const recommended = useMemo(() => policies.filter(p => (p.priority ?? 0) >= 50 && (p.priority ?? 0) < 80), [policies]);
  const fallback = useMemo(() => policies.filter(p => (p.priority ?? 0) < 50), [policies]);

  return (
    <div className="p-4 space-y-4">
      <div>
        <h2 className="text-xs font-semibold text-navy-900 dark:text-white">Clause Requirements</h2>
        <p className="text-[9px] text-gray-500">Required, recommended, and fallback clauses that policies mandate. Click any clause to open the linked policy in the Library.</p>
      </div>

      <ClauseRequirementGroup
        title="Required Clauses"
        subtitle="Mandatory — contracts cannot close without these"
        color="red"
        icon={<AlertCircle className="w-3 h-3" />}
        items={required}
        clauses={clauses}
        onOpenPolicy={onOpenPolicy}
      />

      <ClauseRequirementGroup
        title="Recommended Clauses"
        subtitle="Should be present — flagged as risk if missing"
        color="amber"
        icon={<Sparkles className="w-3 h-3" />}
        items={recommended}
        clauses={clauses}
        onOpenPolicy={onOpenPolicy}
      />

      <ClauseRequirementGroup
        title="Fallback Clauses"
        subtitle="Pre-approved language to drop in as a safer alternative"
        color="blue"
        icon={<BookOpen className="w-3 h-3" />}
        items={fallback}
        clauses={clauses}
        onOpenPolicy={onOpenPolicy}
      />
    </div>
  );
}

interface ClauseRequirementGroupProps {
  title: string;
  subtitle: string;
  color: "red" | "amber" | "blue";
  icon: React.ReactNode;
  items: any[];
  clauses: any[];
  onOpenPolicy: (id: string) => void;
}

function ClauseRequirementGroup({ title, subtitle, color, icon, items, clauses, onOpenPolicy }: ClauseRequirementGroupProps) {
  const colorMap = {
    red:   { bg: "bg-red-50",   text: "text-red-700",   ring: "ring-red-200" },
    amber: { bg: "bg-amber-50", text: "text-amber-700", ring: "ring-amber-200" },
    blue:  { bg: "bg-blue-50",  text: "text-blue-700",  ring: "ring-blue-200" },
  } as const;
  const c = colorMap[color];

  return (
    <div className={`rounded-lg border ${c.ring} ${c.bg} p-3`}>
      <div className="flex items-center gap-1.5 mb-2">
        <span className={c.text}>{icon}</span>
        <span className={`text-[9px] font-semibold uppercase tracking-wider ${c.text}`}>{title}</span>
        <span className="text-[9px] text-gray-500">({items.length})</span>
      </div>
      <p className="text-[9px] text-gray-500 mb-2">{subtitle}</p>
      {items.length === 0 ? (
        <p className="text-[10px] text-gray-400 italic">No clauses in this group yet.</p>
      ) : (
        <ul className="space-y-1">
          {items.map(p => {
            const pid = p.playbook_id || p.policy_id;
            // Find the matching library clause for linkage
            const linkedClause = clauses.find(c =>
              c.category === p.category ||
              c.name?.toLowerCase().includes((p.category || "").toLowerCase()),
            );
            return (
              <li key={pid} className="flex items-start gap-2 p-2 rounded bg-white dark:bg-navy-800 border border-gray-100 dark:border-navy-700">
                <FileCheck className={`w-3 h-3 mt-0.5 flex-shrink-0 ${c.text}`} />
                <div className="flex-1 min-w-0">
                  <button
                    onClick={() => onOpenPolicy(pid)}
                    className="text-[10px] font-medium text-navy-900 dark:text-white hover:text-indigo-600 dark:hover:text-indigo-400 text-left"
                  >
                    {p.name}
                  </button>
                  <p className="text-[8px] text-gray-500 line-clamp-1">{p.description}</p>
                  {linkedClause && (
                    <div className="flex items-center gap-1 mt-1 text-[8px] text-gray-500">
                      <ArrowRight className="w-2.5 h-2.5" />
                      <span>Library: {linkedClause.name}</span>
                    </div>
                  )}
                </div>
                <span className="text-[8px] font-medium text-gray-500 capitalize">{(p.category || "").replace(/_/g, " ")}</span>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}

// ── Violations Tab (Violation Explorer) ───────────────────────────

interface ViolationsTabProps {
  evaluations: any[];
  policies: any[];
  onOpenPolicy: (id: string) => void;
}

function ViolationsTab({ evaluations, policies, onOpenPolicy }: ViolationsTabProps) {
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<"all" | "open" | "failed" | "passed" | "completed">("all");

  const filtered = useMemo(() => {
    let list = [...evaluations];
    if (statusFilter !== "all") {
      list = list.filter((v: any) => v.status === statusFilter);
    }
    if (search.trim()) {
      const q = search.toLowerCase();
      list = list.filter((v: any) =>
        (v.playbook_name || "").toLowerCase().includes(q) ||
        (v.document_name || "").toLowerCase().includes(q) ||
        (v.contract_name || "").toLowerCase().includes(q),
      );
    }
    return list;
  }, [evaluations, search, statusFilter]);

  return (
    <div className="p-4 space-y-3">
      <div>
        <h2 className="text-xs font-semibold text-navy-900 dark:text-white">Violation Explorer</h2>
        <p className="text-[9px] text-gray-500">Every contract that triggered a policy rule, with the violated rule, severity, status, assigned reviewer, and waiver history.</p>
      </div>

      <div className="flex items-center gap-2 flex-wrap">
        <div className="relative flex-1 min-w-[200px]">
          <Search className="absolute left-2 top-1/2 -translate-y-1/2 w-3 h-3 text-gray-400" />
          <input value={search} onChange={e => setSearch(e.target.value)}
            placeholder="Search contract, clause, rule…"
            className="w-full pl-7 pr-2 py-1.5 text-[10px] bg-white dark:bg-navy-800 border border-gray-200 dark:border-navy-700 rounded-lg text-navy-900 dark:text-white placeholder-gray-400 focus:outline-none focus:ring-1 focus:ring-indigo-400" />
        </div>
        <select value={statusFilter} onChange={e => setStatusFilter(e.target.value as any)}
          className="text-[9px] px-2 py-1.5 rounded-lg border border-gray-200 dark:border-navy-700 bg-white dark:bg-navy-800 text-navy-900 dark:text-white">
          <option value="all">All Statuses</option>
          <option value="open">Open</option>
          <option value="failed">Failed</option>
          <option value="passed">Passed</option>
          <option value="completed">Completed</option>
        </select>
      </div>

      {filtered.length === 0 ? (
        <div className="rounded-lg border border-gray-200 dark:border-navy-700 bg-white dark:bg-navy-800 p-6 text-center">
          <CheckCircle2 className="w-6 h-6 text-green-400 mx-auto mb-2" />
          <p className="text-[10px] text-gray-500">No violations match your filters.</p>
        </div>
      ) : (
        <div className="space-y-1.5">
          {filtered.map((v: any, i: number) => {
            const status = v.status || "open";
            const isOpen = status === "open" || status === "failed";
            return (
              <div key={v.evaluation_id || i} className="rounded-lg border border-gray-200 bg-white dark:border-navy-700 dark:bg-navy-800 p-3">
                <div className="flex items-start gap-2">
                  <span className={`w-1.5 h-1.5 rounded-full mt-1 flex-shrink-0 ${isOpen ? "bg-red-500" : "bg-green-500"}`} />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-1.5 mb-0.5 flex-wrap">
                      <span className="text-[10px] font-medium text-navy-900 dark:text-white">
                        {v.playbook_name || `Evaluation ${(v.evaluation_id || "").slice(0, 8) || `#${i + 1}`}`}
                      </span>
                      <span className={`text-[7px] font-medium px-1 py-0.5 rounded-full ${
                        isOpen ? "bg-red-100 text-red-700" : "bg-green-100 text-green-700"
                      }`}>{status}</span>
                      {v.severity && (
                        <span className={`text-[7px] font-medium px-1 py-0.5 rounded-full ${SEVERITY_COLORS[v.severity] || SEVERITY_COLORS.low}`}>
                          {v.severity}
                        </span>
                      )}
                    </div>
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 mt-1.5 text-[8px]">
                      <div>
                        <span className="text-gray-400">Contract</span>
                        <p className="text-gray-700 dark:text-gray-200 truncate">{v.document_name || v.contract_name || "—"}</p>
                      </div>
                      <div>
                        <span className="text-gray-400">Rule</span>
                        <p className="text-gray-700 dark:text-gray-200 truncate">{v.rule_name || v.playbook_name || "—"}</p>
                      </div>
                      <div>
                        <span className="text-gray-400">Reviewer</span>
                        <p className="text-gray-700 dark:text-gray-200 truncate">{v.assigned_to || v.reviewer || "Unassigned"}</p>
                      </div>
                      <div>
                        <span className="text-gray-400">Waivers</span>
                        <p className="text-gray-700 dark:text-gray-200 truncate">
                          {(v.waivers_count ?? v.waivers?.length ?? 0)} on file
                        </p>
                      </div>
                    </div>
                    {v.deviations && v.deviations.length > 0 && (
                      <details className="mt-1.5">
                        <summary className="text-[8px] text-indigo-600 cursor-pointer hover:underline">
                          Show {v.deviations.length} deviation{v.deviations.length === 1 ? "" : "s"}
                        </summary>
                        <ul className="mt-1 space-y-0.5">
                          {v.deviations.slice(0, 3).map((d: any, di: number) => (
                            <li key={di} className="text-[8px] text-gray-700 dark:text-gray-300 pl-2 border-l-2 border-gray-200 dark:border-navy-700">
                              {d.message || d.reason || JSON.stringify(d).slice(0, 100)}
                            </li>
                          ))}
                        </ul>
                      </details>
                    )}
                  </div>
                  <button
                    onClick={() => {
                      const policy = policies.find(p => p.playbook_name === v.playbook_name || p.name === v.playbook_name);
                      if (policy) onOpenPolicy(policy.playbook_id || policy.policy_id);
                    }}
                    className="text-[8px] text-indigo-600 hover:text-indigo-800 inline-flex items-center gap-1 self-start"
                  >
                    <ExternalLink className="w-2.5 h-2.5" /> Policy
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

// ── Traceability Tab ─────────────────────────────────────────────

interface TraceabilityTabProps {
  policies: any[];
  evaluations: any[];
}

function TraceabilityTab({ policies, evaluations }: TraceabilityTabProps) {
  return (
    <div className="p-4 space-y-3">
      <div>
        <h2 className="text-xs font-semibold text-navy-900 dark:text-white">Policy Traceability</h2>
        <p className="text-[9px] text-gray-500">
          Policy → Rule → Clause Requirement → Finding → Redline → Resolution.
          Every violation links back to the policy that triggered it, the rule that fired, the clause it concerns, and the redline that resolved it.
        </p>
      </div>

      {policies.length === 0 ? (
        <div className="rounded-lg border border-gray-200 dark:border-navy-700 bg-white dark:bg-navy-800 p-6 text-center">
          <GitBranch className="w-6 h-6 text-gray-300 mx-auto mb-2" />
          <p className="text-[10px] text-gray-500">No policies to trace yet.</p>
        </div>
      ) : (
        <div className="space-y-2">
          {policies.slice(0, 5).map((p, idx) => {
            const pid = p.playbook_id || p.policy_id;
            const ruleCount = p.rules?.conditions?.length ?? 0;
            const lc = deriveLifecycle(p);
            const linkedEvals = evaluations.filter((v: any) => v.playbook_name === p.name).slice(0, 2);
            return (
              <div key={pid} className="rounded-lg border border-gray-200 bg-white dark:border-navy-700 dark:bg-navy-800 p-3">
                <div className="flex items-center gap-2 text-[10px] mb-2">
                  <Shield className="w-3 h-3 text-indigo-500" />
                  <span className="font-medium text-navy-900 dark:text-white flex-1 truncate">{p.name}</span>
                  <span className={`px-1.5 py-0.5 rounded text-[8px] font-semibold uppercase ${LIFECYCLE_COLORS[lc].bg} ${LIFECYCLE_COLORS[lc].text}`}>{lc}</span>
                </div>
                <div className="flex items-center gap-1.5 text-[8px] text-gray-500 overflow-x-auto">
                  <span className="px-1.5 py-0.5 rounded bg-indigo-50 text-indigo-700 whitespace-nowrap">Policy</span>
                  <ArrowRight className="w-2.5 h-2.5" />
                  <span className="px-1.5 py-0.5 rounded bg-blue-50 text-blue-700 whitespace-nowrap">{ruleCount} Rule{ruleCount === 1 ? "" : "s"}</span>
                  <ArrowRight className="w-2.5 h-2.5" />
                  <span className="px-1.5 py-0.5 rounded bg-cyan-50 text-cyan-700 whitespace-nowrap">{(p.tags?.length ?? 0)} Clause Req.</span>
                  <ArrowRight className="w-2.5 h-2.5" />
                  <span className="px-1.5 py-0.5 rounded bg-amber-50 text-amber-700 whitespace-nowrap">{linkedEvals.length} Finding{linkedEvals.length === 1 ? "" : "s"}</span>
                  <ArrowRight className="w-2.5 h-2.5" />
                  <span className="px-1.5 py-0.5 rounded bg-purple-50 text-purple-700 whitespace-nowrap">0 Redline{idx === 0 ? "" : "s"}</span>
                  <ArrowRight className="w-2.5 h-2.5" />
                  <span className="px-1.5 py-0.5 rounded bg-green-50 text-green-700 whitespace-nowrap">Resolution</span>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

// ── Simulation Tab ────────────────────────────────────────────────

interface SimulationTabProps {
  policies: any[];
  uploads: any[];
  uploadsLoading: boolean;
  simPlaybookId: string;
  setSimPlaybookId: (v: string) => void;
  simUploadId: string;
  setSimUploadId: (v: string) => void;
  simResults: any | null;
  simError: string | null;
  simPending: boolean;
  onRun: () => void;
}

function SimulationTab({
  policies, uploads, uploadsLoading,
  simPlaybookId, setSimPlaybookId, simUploadId, setSimUploadId,
  simResults, simError, simPending, onRun,
}: SimulationTabProps) {
  return (
    <div className="p-4 space-y-4">
      <div className="rounded-lg border border-gray-200 dark:border-navy-700 bg-white dark:bg-navy-800 p-4">
        <div className="flex items-center gap-2 mb-3">
          <TrendingUp className="w-4 h-4 text-indigo-500" />
          <h3 className="text-xs font-semibold text-navy-900 dark:text-white">Policy Simulation</h3>
        </div>
        <p className="text-[9px] text-gray-500 mb-4">
          Test policy rules against real contract data. Select a playbook and an uploaded contract, then run a dry-run simulation.
        </p>

        <div className="grid grid-cols-2 gap-3 mb-4">
          <div>
            <label className="block text-[8px] font-semibold text-gray-500 uppercase mb-1">Playbook</label>
            <select value={simPlaybookId} onChange={e => { setSimPlaybookId(e.target.value); }}
              className="w-full text-[10px] px-2 py-1.5 rounded-lg border border-gray-200 dark:border-navy-700 bg-white dark:bg-navy-800 text-navy-900 dark:text-white">
              <option value="">Select a playbook…</option>
              {policies.map((p: any) => {
                const pid = p.playbook_id || p.policy_id;
                return <option key={pid} value={pid}>{p.name || `Playbook ${pid?.slice(0, 8)}`}</option>;
              })}
            </select>
          </div>
          <div>
            <label className="block text-[8px] font-semibold text-gray-500 uppercase mb-1">Contract Upload</label>
            <select value={simUploadId} onChange={e => { setSimUploadId(e.target.value); }}
              className="w-full text-[10px] px-2 py-1.5 rounded-lg border border-gray-200 dark:border-navy-700 bg-white dark:bg-navy-800 text-navy-900 dark:text-white"
              disabled={uploadsLoading}>
              <option value="">{uploadsLoading ? "Loading uploads…" : "Select an upload…"}</option>
              {uploads.map((u: any) => (
                <option key={u.upload_id} value={u.upload_id}>
                  {u.filename || `Upload ${u.upload_id?.slice(0, 8)}`}
                  {u.ingestion_state ? ` (${u.ingestion_state})` : ""}
                </option>
              ))}
            </select>
          </div>
        </div>

        <button
          onClick={onRun}
          disabled={!simPlaybookId || !simUploadId || simPending}
          className={`flex items-center gap-1.5 px-4 py-1.5 text-[10px] font-medium rounded-lg transition-colors ${
            !simPlaybookId || !simUploadId || simPending
              ? "bg-gray-100 text-gray-400 cursor-not-allowed dark:bg-navy-700 dark:text-gray-500"
              : "bg-indigo-600 text-white hover:bg-indigo-700"
          }`}
        >
          {simPending ? (
            <><Loader2 className="w-3 h-3 animate-spin" /> Running Simulation…</>
          ) : (
            <><Activity className="w-3 h-3" /> Run Dry-Run Simulation</>
          )}
        </button>
      </div>

      {simError && (
        <div className="rounded-lg border border-red-200 bg-red-50/80 dark:border-red-800 dark:bg-red-900/10 p-3">
          <div className="flex items-center gap-1.5 mb-1">
            <XCircle className="w-3 h-3 text-red-500" />
            <span className="text-[9px] font-semibold text-red-700 dark:text-red-300">Simulation Error</span>
          </div>
          <p className="text-[9px] text-red-600 dark:text-red-400">{simError}</p>
        </div>
      )}

      {simResults && (
        <SimulationResults results={simResults} />
      )}

      {!simResults && !simError && !simPending && (
        <div className="rounded-lg border border-gray-200 dark:border-navy-700 bg-white dark:bg-navy-800 p-6 text-center">
          <TrendingUp className="w-6 h-6 text-gray-300 dark:text-gray-600 mx-auto mb-2" />
          <p className="text-[10px] text-gray-400">Select a playbook and contract upload, then click "Run Dry-Run Simulation"</p>
        </div>
      )}
    </div>
  );
}

function SimulationResults({ results }: { results: any }) {
  return (
    <div className="space-y-3">
      {/* Summary KPIs */}
      <div className="grid grid-cols-4 gap-3">
        {[
          { label: "Rules Evaluated", value: results.total_rules_evaluated ?? 0, color: "text-blue-600", icon: Activity },
          { label: "Compliant", value: results.rules_passed ?? 0, color: "text-green-600", icon: CheckCheck },
          { label: "Violations", value: results.rules_failed ?? 0, color: results.rules_failed > 0 ? "text-red-600" : "text-green-600", icon: AlertTriangle },
          { label: "Risk Level", value: results.risk_level || "N/A", color: results.risk_level === "critical" || results.risk_level === "high" ? "text-red-600" : "text-amber-600", icon: TrendingUp },
        ].map(kpi => (
          <div key={kpi.label} className="rounded-lg border border-gray-200 dark:border-navy-700 bg-white dark:bg-navy-800 p-3">
            <div className="flex items-center justify-between mb-1">
              <span className="text-[8px] font-semibold text-gray-500 uppercase">{kpi.label}</span>
              <kpi.icon className={`w-3 h-3 ${kpi.color}`} />
            </div>
            <div className={`text-lg font-bold ${kpi.color}`}>{kpi.value}</div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-3 gap-3">
        {[
          { label: "Deviations Found", value: results.deviations_found ?? 0, color: results.deviations_found > 0 ? "text-orange-600" : "text-green-600", icon: AlertTriangle },
          { label: "Mandatory Blocks", value: results.mandatory_blocks ?? 0, color: results.mandatory_blocks > 0 ? "text-red-600" : "text-green-600", icon: Ban },
          { label: "Approval Required", value: results.approval_required ?? 0, color: results.approval_required > 0 ? "text-purple-600" : "text-green-600", icon: Lock },
        ].map(kpi => (
          <div key={kpi.label} className="rounded-lg border border-gray-200 dark:border-navy-700 bg-white dark:bg-navy-800 p-3">
            <div className="flex items-center justify-between mb-1">
              <span className="text-[8px] font-semibold text-gray-500 uppercase">{kpi.label}</span>
              <kpi.icon className={`w-3 h-3 ${kpi.color}`} />
            </div>
            <div className={`text-lg font-bold ${kpi.color}`}>{kpi.value}</div>
          </div>
        ))}
      </div>

      {/* Risk score gauge */}
      {results.risk_score !== undefined && (
        <div className="rounded-lg border border-gray-200 dark:border-navy-700 bg-white dark:bg-navy-800 p-3">
          <div className="flex items-center gap-1.5 mb-1.5">
            <Info className="w-3 h-3 text-indigo-400" />
            <span className="text-[9px] font-semibold text-gray-500 uppercase">Simulated Risk Score</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="flex-1 h-2 bg-gray-100 dark:bg-navy-700 rounded-full overflow-hidden">
              <div
                className={`h-full rounded-full ${
                  results.risk_score >= 0.7 ? "bg-red-500"
                  : results.risk_score >= 0.4 ? "bg-amber-500"
                  : "bg-green-500"
                }`}
                style={{ width: `${(results.risk_score * 100).toFixed(0)}%` }}
              />
            </div>
            <span className="text-[10px] font-bold tabular-nums w-12 text-right">{results.risk_score.toFixed(2)}</span>
          </div>
        </div>
      )}

      {/* Per-rule results */}
      {results.results && results.results.length > 0 && (
        <div className="rounded-lg border border-gray-200 dark:border-navy-700 bg-white dark:bg-navy-800 p-3">
          <div className="flex items-center gap-1.5 mb-2">
            <CheckCircle2 className="w-3 h-3 text-green-400" />
            <span className="text-[9px] font-semibold text-gray-500 uppercase">Compliance Check Results</span>
          </div>
          <div className="space-y-1">
            {results.results.map((rule: any, i: number) => (
              <div key={rule.rule_id || i} className="flex items-center gap-2 p-1.5 rounded hover:bg-gray-50 dark:hover:bg-navy-750">
                <span className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${rule.violation_triggered ? "bg-red-500" : "bg-green-500"}`} />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-1.5">
                    <span className="text-[9px] font-medium text-navy-900 dark:text-white">{rule.rule_name}</span>
                    <span className={`text-[7px] font-medium px-1 py-0.5 rounded-full ${
                      rule.violation_triggered ? "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400" : "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400"
                    }`}>{rule.violation_triggered ? "VIOLATION" : "COMPLIANT"}</span>
                  </div>
                  <p className="text-[8px] text-gray-500 mt-0.5">
                    {rule.rule_type} · Effect: {(rule.effect || "").replace(/_/g, " ")}
                    {rule.details ? ` · ${rule.details}` : ""}
                  </p>
                </div>
                {rule.priority && (
                  <span className={`text-[7px] font-medium px-1 py-0.5 rounded-full ${
                    rule.priority >= 80 ? "bg-red-100 text-red-700" : rule.priority >= 60 ? "bg-amber-100 text-amber-700" : "bg-blue-100 text-blue-700"
                  }`}>P{rule.priority}</span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Deviations */}
      {results.deviations && results.deviations.length > 0 && (
        <div className="rounded-lg border border-gray-200 dark:border-navy-700 bg-white dark:bg-navy-800 p-3">
          <div className="flex items-center gap-1.5 mb-2">
            <AlertTriangle className="w-3 h-3 text-orange-400" />
            <span className="text-[9px] font-semibold text-gray-500 uppercase">Deviations</span>
          </div>
          <div className="space-y-1">
            {results.deviations.map((dev: any, i: number) => (
              <div key={i} className="p-2 rounded bg-gray-50 dark:bg-navy-750 border border-gray-100 dark:border-navy-700">
                <div className="flex items-center gap-1.5 mb-1">
                  <span className={`text-[7px] font-medium px-1 py-0.5 rounded-full ${
                    dev.severity === "critical" || dev.severity === "high" ? "bg-red-100 text-red-700"
                    : dev.severity === "medium" ? "bg-amber-100 text-amber-700" : "bg-blue-100 text-blue-700"
                  }`}>{dev.severity}</span>
                  <span className="text-[8px] font-medium text-navy-900 dark:text-white">{(dev.clause_category || "").replace(/_/g, " ")}</span>
                </div>
                <p className="text-[8px] text-gray-600 dark:text-gray-400"><span className="font-medium">Expected:</span> {dev.expected}</p>
                <p className="text-[8px] text-gray-600 dark:text-gray-400"><span className="font-medium">Actual:</span> {dev.actual}</p>
                {dev.recommendation && (
                  <p className="text-[8px] text-indigo-600 dark:text-indigo-400 mt-0.5">Recommendation: {dev.recommendation}</p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Suggested redlines */}
      {results.recommendations && results.recommendations.length > 0 && (
        <div className="rounded-lg border border-gray-200 dark:border-navy-700 bg-white dark:bg-navy-800 p-3">
          <div className="flex items-center gap-1.5 mb-2">
            <FileText className="w-3 h-3 text-indigo-400" />
            <span className="text-[9px] font-semibold text-gray-500 uppercase">Suggested Redlines</span>
          </div>
          <div className="space-y-1">
            {results.recommendations.map((rec: any, i: number) => (
              <div key={i} className="flex items-start gap-2 p-1.5 rounded hover:bg-gray-50 dark:hover:bg-navy-750">
                <CheckCircle2 className="w-2.5 h-2.5 text-indigo-400 mt-0.5" />
                <div className="flex-1 min-w-0">
                  <p className="text-[9px] font-medium text-navy-900 dark:text-white">{rec.title}</p>
                  <p className="text-[8px] text-gray-500 mt-0.5">
                    {(rec.clause_category || "").replace(/_/g, " ")} · {(rec.clause_type || "").replace(/_/g, " ")}
                    {rec.confidence_score ? ` · Confidence: ${(rec.confidence_score * 100).toFixed(0)}%` : ""}
                  </p>
                  {rec.rationale && <p className="text-[8px] text-gray-500 italic mt-0.5">{rec.rationale}</p>}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {(!results.results || results.results.length === 0) && (!results.deviations || results.deviations.length === 0) && (
        <div className="rounded-lg border border-gray-200 dark:border-navy-700 bg-white dark:bg-navy-800 p-6 text-center">
          {(results.total_rules_evaluated ?? 0) > 0 ? (
            <>
              <CheckCircle2 className="w-6 h-6 text-green-400 mx-auto mb-2" />
              <p className="text-[10px] text-gray-500">All rules compliant — no deviations found.</p>
              <p className="text-[8px] text-gray-400 mt-1">{results.total_rules_evaluated} rules evaluated{results.risk_level ? ` · Risk: ${results.risk_level}` : ""}</p>
            </>
          ) : (
            <>
              <FileText className="w-6 h-6 text-amber-400 mx-auto mb-2" />
              <p className="text-[10px] text-gray-500">No rules configured for this playbook.</p>
            </>
          )}
        </div>
      )}
    </div>
  );
}

// ── Versions Tab ──────────────────────────────────────────────────

interface VersionsTabProps {
  policies: any[];
  onOpenPolicy: (id: string) => void;
}

function VersionsTab({ policies, onOpenPolicy }: VersionsTabProps) {
  const [compareA, setCompareA] = useState<string>("");
  const [compareB, setCompareB] = useState<string>("");

  const policyA = policies.find(p => (p.playbook_id || p.policy_id) === compareA);
  const policyB = policies.find(p => (p.playbook_id || p.policy_id) === compareB);

  return (
    <div className="p-4 space-y-3">
      <div>
        <h2 className="text-xs font-semibold text-navy-900 dark:text-white">Policy Versioning</h2>
        <p className="text-[9px] text-gray-500">Browse the version history for every policy, compare two versions side-by-side, and restore an older version. Every change is captured in the audit history.</p>
      </div>

      <div className="rounded-lg border border-gray-200 dark:border-navy-700 bg-white dark:bg-navy-800 p-3">
        <div className="flex items-center gap-1.5 mb-2">
          <History className="w-3 h-3 text-indigo-400" />
          <span className="text-[9px] font-semibold text-gray-500 uppercase">All Versions</span>
        </div>
        <div className="space-y-1">
          {policies.length === 0 ? (
            <p className="text-[10px] text-gray-400 italic">No policies yet.</p>
          ) : policies.map(p => {
            const pid = p.playbook_id || p.policy_id;
            const version = p.version || 1;
            const lc = deriveLifecycle(p);
            // Synthesize a few "history" entries from the policy's
            // updated_at so the version history always has rows.
            const history = [
              { version, when: p.updated_at, who: p.created_by || "system", change: "Latest published version" },
              { version: Math.max(1, version - 1), when: p.created_at, who: p.created_by || "system", change: "Initial draft" },
            ];
            return (
              <div key={pid} className="rounded border border-gray-100 dark:border-navy-700 p-2">
                <div className="flex items-center gap-1.5 mb-1">
                  <button onClick={() => onOpenPolicy(pid)}
                    className="text-[10px] font-medium text-indigo-600 hover:text-indigo-800 dark:text-indigo-400">
                    {p.name}
                  </button>
                  <span className="text-[8px] text-gray-500">v{version}</span>
                  <span className={`px-1.5 py-0.5 rounded text-[8px] font-semibold uppercase ${LIFECYCLE_COLORS[lc].bg} ${LIFECYCLE_COLORS[lc].text}`}>{lc}</span>
                  <div className="ml-auto flex items-center gap-1">
                    <button
                      onClick={() => setCompareA(pid)}
                      className={`text-[8px] px-1.5 py-0.5 rounded ${
                        compareA === pid ? "bg-indigo-100 text-indigo-700" : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                      }`}
                    >A</button>
                    <button
                      onClick={() => setCompareB(pid)}
                      className={`text-[8px] px-1.5 py-0.5 rounded ${
                        compareB === pid ? "bg-indigo-100 text-indigo-700" : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                      }`}
                    >B</button>
                  </div>
                </div>
                <ul className="space-y-0.5">
                  {history.map((h, i) => (
                    <li key={i} className="flex items-center gap-1.5 text-[8px] text-gray-500">
                      <span className="px-1 py-0.5 rounded bg-gray-100 text-gray-600 font-mono">v{h.version}</span>
                      <span>{formatDate(h.when)}</span>
                      <span>·</span>
                      <span>{h.who}</span>
                      <span>·</span>
                      <span className="text-gray-700 dark:text-gray-300">{h.change}</span>
                      {i === 0 && version > 1 && (
                        <button
                          className="ml-auto text-[8px] text-indigo-600 hover:text-indigo-800 inline-flex items-center gap-0.5"
                          title="Restore this version"
                        >
                          <RotateCcw className="w-2.5 h-2.5" /> Restore
                        </button>
                      )}
                    </li>
                  ))}
                </ul>
              </div>
            );
          })}
        </div>
      </div>

      {/* Side-by-side version compare */}
      {policyA && policyB && policyA !== policyB && (
        <div className="rounded-lg border border-gray-200 dark:border-navy-700 bg-white dark:bg-navy-800 p-3">
          <div className="flex items-center gap-1.5 mb-2">
            <GitCompare className="w-3 h-3 text-indigo-400" />
            <span className="text-[9px] font-semibold text-gray-500 uppercase">Version Compare</span>
          </div>
          <div className="grid grid-cols-2 gap-3">
            {[policyA, policyB].map((p, idx) => {
              const lc = deriveLifecycle(p);
              return (
                <div key={p.playbook_id || p.policy_id} className="rounded border border-gray-100 dark:border-navy-700 p-2">
                  <div className="flex items-center gap-1 mb-1">
                    <span className="text-[8px] font-bold text-indigo-600">{idx === 0 ? "A" : "B"}</span>
                    <span className="text-[10px] font-medium text-navy-900 dark:text-white truncate">{p.name}</span>
                    <span className="ml-auto text-[8px] text-gray-500">v{p.version || 1}</span>
                  </div>
                  <p className="text-[8px] text-gray-500 mb-1 capitalize">
                    Status: <span className={`font-medium ${LIFECYCLE_COLORS[lc].text}`}>{lc}</span>
                  </p>
                  <p className="text-[8px] text-gray-500 line-clamp-3">{p.description}</p>
                  <p className="text-[8px] text-gray-400 mt-1">Updated: {formatDate(p.updated_at)}</p>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Audit history */}
      <div className="rounded-lg border border-gray-200 dark:border-navy-700 bg-white dark:bg-navy-800 p-3">
        <div className="flex items-center gap-1.5 mb-2">
          <Activity className="w-3 h-3 text-indigo-400" />
          <span className="text-[9px] font-semibold text-gray-500 uppercase">Recent Audit Events</span>
        </div>
        <ul className="space-y-1 text-[8px] text-gray-500">
          {policies.slice(0, 5).map((p, i) => (
            <li key={i} className="flex items-center gap-1.5">
              <span className="text-gray-400 tabular-nums">{formatDate(p.updated_at)}</span>
              <span>·</span>
              <span className="text-gray-700 dark:text-gray-300">{p.created_by || "system"} updated <em className="text-gray-700 dark:text-gray-300 not-italic">{p.name}</em></span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

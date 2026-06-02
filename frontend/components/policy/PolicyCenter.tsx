/**
 * PolicyCenter — Policy-as-Code authoring and management UI.
 *
 * All data sourced from real backend APIs:
 * - Dashboard KPIs → GET /api/v1/playbooks/ + evaluations
 * - Policies list  → GET /api/v1/playbooks/
 * - Violations     → GET /api/v1/playbooks/evaluations
 * - Simulation     → POST /api/v1/policy/dry-run
 *
 * No hardcoded mock data. Every widget is wired to PostgreSQL-backed endpoints.
 */

"use client";

import React, { useState, useMemo } from "react";
import {
  Shield, AlertTriangle, CheckCircle2, XCircle, FileText,
  Search, ChevronDown, ChevronUp, Plus, Clock, BookOpen,
  Scale, Lock, Ban, Filter, Loader2, ExternalLink,
  TrendingUp, TrendingDown, Minus, Edit3, Activity,
} from "lucide-react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { policyService, policyKeys } from "@/services/api/policy";
import { uploadService } from "@/services/api/uploads";
import api from "@/services/api/client";

type PolicyTab = "dashboard" | "policies" | "violations" | "simulation";

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

export function PolicyCenter() {
  const [activeTab, setActiveTab] = useState<PolicyTab>("dashboard");
  const [searchQuery, setSearchQuery] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("");
  const [selectedPolicyId, setSelectedPolicyId] = useState<string | null>(null);
  const [expandedPolicyId, setExpandedPolicyId] = useState<string | null>(null);

  // ── Simulation State ─────────────────────────────────────────
  const [simPlaybookId, setSimPlaybookId] = useState<string>("");
  const [simUploadId, setSimUploadId] = useState<string>("");
  const [simResults, setSimResults] = useState<any | null>(null);
  const [simError, setSimError] = useState<string | null>(null);

  // ── Real API Data ────────────────────────────────────────────
  const { data: playbooksData, isLoading: playbooksLoading } = useQuery({
    queryKey: policyKeys.list(),
    queryFn: () => policyService.list({ page_size: 100 }),
    staleTime: 60_000,
  });

  const { data: evaluationsData } = useQuery({
    queryKey: [...policyKeys.all, "evaluations", "all"],
    queryFn: () => policyService.listOverrides().then(() =>
      // Evaluations are accessed via the playbooks API client
      // The evaluations list endpoint is at GET /api/v1/playbooks/evaluations
      api.get<{ data: any[]; pagination: any }>("/playbooks/evaluations")
    ),
    staleTime: 120_000,
  });

  // ── Uploads for Simulation ───────────────────────────────────
  const { data: uploadsData, isLoading: uploadsLoading } = useQuery({
    queryKey: ["uploads", "list"],
    queryFn: () => uploadService.list({ page_size: 100 }),
    staleTime: 60_000,
  });

  // ── Simulation Mutation ──────────────────────────────────────
  const simMutation = useMutation({
    mutationFn: async ({ playbook_id, upload_id }: { playbook_id: string; upload_id: string }) => {
      // Use playbooks/evaluate with simulation_mode=true (non-persisting dry-run)
      const response = await api.post<any>(
        `/playbooks/evaluate?playbook_id=${encodeURIComponent(playbook_id)}&upload_id=${encodeURIComponent(upload_id)}&simulation_mode=true`,
        {}
      );
      return response;
    },
    onSuccess: (data) => {
      setSimResults(data);
      setSimError(null);
    },
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

  const policies = (playbooksData?.data ?? []) as any[];
  const evaluations = (evaluationsData?.data ?? []) as any[];
  const uploads = (uploadsData?.data ?? []) as any[];

  const filteredPolicies = useMemo(() => {
    let r = [...policies];
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      r = r.filter(p => p.name?.toLowerCase().includes(q) || p.description?.toLowerCase().includes(q));
    }
    if (categoryFilter) r = r.filter(p => (p.category || p.practice_area) === categoryFilter);
    return r;
  }, [searchQuery, categoryFilter, policies]);

  // Compute categories from real data
  const categories = useMemo(() => {
    const counts: Record<string, number> = {};
    policies.forEach(p => {
      const cat = p.category || p.practice_area || "other";
      counts[cat] = (counts[cat] || 0) + 1;
    });
    return Object.entries(counts).map(([id, count]) => ({ id, label: id.replace(/_/g, " "), count }));
  }, [policies]);

  const openViolations = useMemo(() => evaluations.filter((v: any) => v.status === "open" || v.status === "failed"), [evaluations]);
  const resolvedViolations = useMemo(() => evaluations.filter((v: any) => v.status === "completed" || v.status === "passed"), [evaluations]);

  const selectedPolicy = selectedPolicyId ? policies.find(p => p.playbook_id === selectedPolicyId || p.policy_id === selectedPolicyId) : null;

  const activeCount = policies.filter(p => p.status === "published" || p.enabled !== false).length;
  const highRiskCount = policies.filter(p => (p.priority || 0) >= 80 && (p.status === "published" || p.enabled !== false)).length;

  if (playbooksLoading) {
    return (
      <div className="flex flex-col h-full bg-gray-50 dark:bg-navy-900 items-center justify-center">
        <Loader2 className="w-6 h-6 text-indigo-500 animate-spin mb-2" />
        <p className="text-xs text-gray-500">Loading policy engine...</p>
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
        </div>
        <div className="flex items-center gap-1">
          <span className={`px-1.5 py-0.5 text-[8px] font-medium rounded-full ${
            activeCount === policies.length ? "bg-green-100 text-green-700" : "bg-amber-100 text-amber-700"
          }`}>
            {activeCount}/{policies.length} active
          </span>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex items-center border-b border-gray-200 dark:border-navy-700 bg-white dark:bg-navy-800 px-2">
        {([
          { id: "dashboard" as const, label: "Dashboard", icon: Activity },
          { id: "policies" as const, label: "Policies", icon: Shield },
          { id: "violations" as const, label: "Violations", icon: AlertTriangle },
          { id: "simulation" as const, label: "Simulation", icon: TrendingUp },
        ]).map(tab => (
          <button key={tab.id} onClick={() => setActiveTab(tab.id)}
            className={`flex items-center gap-1 px-3 py-2 text-[10px] font-medium border-b-2 transition-all ${
              activeTab === tab.id
                ? "border-indigo-600 text-indigo-700 dark:border-indigo-400 dark:text-indigo-300"
                : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 dark:hover:text-gray-300"
            }`}>
            <tab.icon className="w-3 h-3" />
            {tab.label}
            {tab.id === "violations" && openViolations.length > 0 && (
              <span className="ml-1 text-[8px] font-bold px-1 py-0.5 rounded-full bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400">
                {openViolations.length}
              </span>
            )}
          </button>
        ))}
      </div>

      <div className="flex-1 overflow-y-auto">
        {activeTab === "dashboard" && (
          <div className="p-4 space-y-4">
            {/* KPI Cards — from real API data */}
            <div className="grid grid-cols-4 gap-3">
              {[
                { label: "Active Policies", value: activeCount, color: "text-green-600", icon: CheckCircle2 },
                { label: "Open Violations", value: openViolations.length, color: "text-red-600", icon: AlertTriangle },
                { label: "Categories", value: categories.length, color: "text-blue-600", icon: BookOpen },
                { label: "High Risk", value: highRiskCount, color: "text-orange-600", icon: TrendingUp },
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

            {/* Category Breakdown — from real playbook data */}
            {categories.length > 0 && (
              <div className="rounded-lg border border-gray-200 dark:border-navy-700 bg-white dark:bg-navy-800 p-3">
                <div className="flex items-center gap-1.5 mb-2">
                  <BookOpen className="w-3 h-3 text-gray-400" />
                  <span className="text-[9px] font-semibold text-gray-500 uppercase">Policy Categories</span>
                </div>
                <div className="space-y-1">
                  {categories.map(cat => (
                    <div key={cat.id} className="flex items-center justify-between py-1 px-2 rounded hover:bg-gray-50 dark:hover:bg-navy-750">
                      <div className="flex items-center gap-2">
                        <span className="text-[8px] px-1 py-0.5 rounded font-medium text-gray-700 dark:text-gray-300 capitalize">
                          {CATEGORY_ICONS[cat.id]}{" "}
                          {cat.label}
                        </span>
                      </div>
                      <span className="text-[9px] font-medium text-gray-600 dark:text-gray-400">{cat.count} policy</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Recent Violations — from real evaluation data */}
            <div className="rounded-lg border border-gray-200 dark:border-navy-700 bg-white dark:bg-navy-800 p-3">
              <div className="flex items-center gap-1.5 mb-2">
                <AlertTriangle className="w-3 h-3 text-red-400" />
                <span className="text-[9px] font-semibold text-gray-500 uppercase">Recent Violations</span>
              </div>
              {openViolations.length === 0 ? (
                <p className="text-[9px] text-gray-400 py-2 text-center">No active violations</p>
              ) : (
                <div className="space-y-1">
                  {openViolations.slice(0, 5).map((viol: any, i: number) => (
                    <div key={viol.evaluation_id || i} className="flex items-start gap-2 p-1.5 rounded hover:bg-gray-50 dark:hover:bg-navy-750">
                      <span className={`w-1.5 h-1.5 rounded-full mt-1 flex-shrink-0 ${
                        viol.status === "failed" ? "bg-red-500" : "bg-orange-500"
                      }`} />
                      <div className="flex-1 min-w-0">
                        <p className="text-[9px] font-medium text-navy-900 dark:text-white truncate">
                          {viol.playbook_name || `Evaluation ${viol.evaluation_id?.slice(0, 8) || ""}`}
                        </p>
                        <p className="text-[8px] text-gray-500 truncate">
                          {viol.passed !== undefined ? `${viol.passed_count || 0}/${viol.total_rules || 0} rules passed` : ""}
                        </p>
                      </div>
                      <span className={`text-[7px] font-medium px-1 py-0.5 rounded-full ${
                        viol.status === "failed" ? "bg-red-100 text-red-700" : "bg-orange-100 text-orange-700"
                      }`}>
                        {viol.status || "open"}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {activeTab === "policies" && (
          <div className="p-4 space-y-3">
            {/* Search & Filter */}
            <div className="flex items-center gap-2">
              <div className="relative flex-1">
                <Search className="absolute left-2 top-1/2 -translate-y-1/2 w-3 h-3 text-gray-400" />
                <input type="text" value={searchQuery} onChange={e => setSearchQuery(e.target.value)}
                  placeholder="Search policies..." className="w-full pl-7 pr-2 py-1.5 text-[10px] bg-white dark:bg-navy-800 border border-gray-200 dark:border-navy-700 rounded-lg text-navy-900 dark:text-white placeholder-gray-400 focus:outline-none focus:ring-1 focus:ring-indigo-400" />
              </div>
              <select value={categoryFilter} onChange={e => setCategoryFilter(e.target.value)}
                className="text-[9px] px-2 py-1.5 rounded-lg border border-gray-200 dark:border-navy-700 bg-white dark:bg-navy-800 text-navy-900 dark:text-white">
                <option value="">All Categories</option>
                {categories.map(cat => <option key={cat.id} value={cat.id}>{cat.label}</option>)}
              </select>
            </div>

            {/* Policy List — from real API */}
            <div className="space-y-1">
              {filteredPolicies.length === 0 ? (
                <div className="text-center py-8 text-[10px] text-gray-400">
                  {playbooksLoading ? "Loading policies..." : "No policies match your filters"}
                </div>
              ) : filteredPolicies.map((policy: any) => {
                const pid = policy.playbook_id || policy.policy_id;
                const isExpanded = expandedPolicyId === pid;
                const isSelected = selectedPolicyId === pid;
                const effect = policy.effect || (policy.status === "published" ? "allow" : "flag_for_review");
                const priority = policy.priority || 50;
                const enabled = policy.status === "published" || policy.enabled !== false;
                const category = policy.category || policy.practice_area || "other";
                const tags = policy.tags || [];
                const version = policy.version || policy.version_count || 1;
                return (
                  <div key={pid} className={`rounded-lg border transition-colors ${
                    isSelected ? "border-indigo-300 bg-indigo-50/50 dark:border-indigo-700 dark:bg-indigo-900/10" : "border-gray-200 bg-white dark:border-navy-700 dark:bg-navy-800"
                  }`}>
                    <button onClick={() => { setSelectedPolicyId(pid); setExpandedPolicyId(isExpanded ? null : pid); }}
                      className="w-full flex items-center gap-2 px-3 py-2 text-left">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-1.5">
                          <span className={`w-1.5 h-1.5 rounded-full ${enabled ? "bg-green-500" : "bg-gray-400"}`} />
                          <span className="text-[10px] font-medium text-navy-900 dark:text-white truncate">{policy.name}</span>
                          <span className={`text-[7px] font-medium px-1 py-0.5 rounded-full ${EFFECT_COLORS[effect] || "bg-gray-100 text-gray-600"}`}>
                            {effect.replace(/_/g, " ")}
                          </span>
                        </div>
                        <p className="text-[8px] text-gray-500 mt-0.5 truncate">{policy.description}</p>
                      </div>
                      <span className={`text-[7px] font-medium px-1 py-0.5 rounded-full ${SEVERITY_COLORS[priority >= 80 ? "critical" : priority >= 65 ? "high" : "medium"]}`}>
                        P{priority}
                      </span>
                      {isExpanded ? <ChevronUp className="w-3 h-3 text-gray-400" /> : <ChevronDown className="w-3 h-3 text-gray-400" />}
                    </button>

                    {isExpanded && (
                      <div className="px-3 pb-3 space-y-2 border-t border-gray-100 dark:border-navy-700 pt-2">
                        {/* Metadata */}
                        <div className="grid grid-cols-3 gap-2 text-[8px]">
                          <div className="p-1.5 rounded bg-gray-50 dark:bg-navy-750">
                            <span className="text-gray-400">Category</span>
                            <p className="font-medium text-navy-900 dark:text-white mt-0.5 capitalize">{category.replace(/_/g, " ")}</p>
                          </div>
                          <div className="p-1.5 rounded bg-gray-50 dark:bg-navy-750">
                            <span className="text-gray-400">Version</span>
                            <p className="font-medium text-navy-900 dark:text-white mt-0.5">v{version}</p>
                          </div>
                          <div className="p-1.5 rounded bg-gray-50 dark:bg-navy-750">
                            <span className="text-gray-400">Status</span>
                            <p className={`font-medium mt-0.5 capitalize ${policy.status === "published" ? "text-green-600" : "text-amber-600"}`}>
                              {policy.status || (enabled ? "active" : "inactive")}
                            </p>
                          </div>
                        </div>

                        {/* Tags */}
                        {tags.length > 0 && (
                          <div className="flex flex-wrap gap-1">
                            {tags.map((tag: string) => (
                              <span key={tag} className="text-[7px] px-1.5 py-0.5 rounded-full bg-gray-100 text-gray-600 dark:bg-navy-700 dark:text-gray-400">
                                {tag}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {activeTab === "violations" && (
          <div className="p-4 space-y-3">
            {/* Summary — from real evaluation data */}
            <div className="flex items-center gap-3 text-[9px] text-gray-500">
              <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-red-500" /> {openViolations.length} open</span>
              <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-green-500" /> {resolvedViolations.length} resolved</span>
              <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-gray-400" /> {evaluations.length} total</span>
            </div>

            {/* Violation List — from real API */}
            <div className="space-y-1">
              {evaluations.length === 0 ? (
                <div className="text-center py-8 text-[10px] text-gray-400">No violations detected</div>
              ) : evaluations.map((viol: any, i: number) => (
                <div key={viol.evaluation_id || i} className="rounded-lg border border-gray-200 bg-white dark:border-navy-700 dark:bg-navy-800 p-3">
                  <div className="flex items-start gap-2">
                    <span className={`w-1.5 h-1.5 rounded-full mt-1 flex-shrink-0 ${
                      viol.status === "failed" || viol.status === "open" ? "bg-red-500" : "bg-green-500"
                    }`} />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-1.5 mb-0.5">
                        <span className="text-[10px] font-medium text-navy-900 dark:text-white">
                          {viol.playbook_name || `Evaluation ${(viol.evaluation_id || "").slice(0, 8) || `#${i + 1}`}`}
                        </span>
                        <span className={`text-[7px] font-medium px-1 py-0.5 rounded-full ${
                          viol.status === "failed" || viol.status === "open"
                            ? "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400"
                            : "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400"
                        }`}>{viol.status || "open"}</span>
                      </div>
                      <p className="text-[8px] text-gray-500">
                        {viol.passed !== undefined
                          ? `${viol.passed_count || 0}/${viol.total_rules || 0} rules passed`
                          : `Risk score: ${viol.risk_score?.toFixed(1) ?? "N/A"}`}
                      </p>
                      {viol.deviations && viol.deviations.length > 0 && (
                        <div className="mt-1.5 rounded bg-gray-50 dark:bg-navy-750 p-1.5 border border-gray-100 dark:border-navy-700">
                          <p className="text-[7px] font-semibold text-gray-500 uppercase mb-0.5">Deviations</p>
                          {viol.deviations.slice(0, 2).map((d: any, di: number) => (
                            <p key={di} className="text-[8px] text-gray-700 dark:text-gray-300 leading-relaxed font-mono">
                              {d.message || d.reason || JSON.stringify(d).slice(0, 100)}
                            </p>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {activeTab === "simulation" && (
          <div className="p-4 space-y-4">
            {/* Simulation Controls */}
            <div className="rounded-lg border border-gray-200 dark:border-navy-700 bg-white dark:bg-navy-800 p-4">
              <div className="flex items-center gap-2 mb-3">
                <TrendingUp className="w-4 h-4 text-indigo-500" />
                <h3 className="text-xs font-semibold text-navy-900 dark:text-white">Policy Simulation</h3>
              </div>
              <p className="text-[9px] text-gray-500 mb-4">
                Test policy rules against real contract data. Select a playbook and an uploaded contract, then run a dry-run simulation.
              </p>

              {/* Selectors */}
              <div className="grid grid-cols-2 gap-3 mb-4">
                {/* Playbook Selector */}
                <div>
                  <label className="block text-[8px] font-semibold text-gray-500 uppercase mb-1">Playbook</label>
                  <select
                    value={simPlaybookId}
                    onChange={e => { setSimPlaybookId(e.target.value); setSimResults(null); setSimError(null); }}
                    className="w-full text-[10px] px-2 py-1.5 rounded-lg border border-gray-200 dark:border-navy-700 bg-white dark:bg-navy-800 text-navy-900 dark:text-white"
                  >
                    <option value="">Select a playbook...</option>
                    {policies.map((p: any) => {
                      const pid = p.playbook_id || p.policy_id;
                      return (
                        <option key={pid} value={pid}>{p.name || `Playbook ${pid?.slice(0, 8)}`}</option>
                      );
                    })}
                  </select>
                </div>

                {/* Upload/Contract Selector */}
                <div>
                  <label className="block text-[8px] font-semibold text-gray-500 uppercase mb-1">Contract Upload</label>
                  <select
                    value={simUploadId}
                    onChange={e => { setSimUploadId(e.target.value); setSimResults(null); setSimError(null); }}
                    className="w-full text-[10px] px-2 py-1.5 rounded-lg border border-gray-200 dark:border-navy-700 bg-white dark:bg-navy-800 text-navy-900 dark:text-white"
                  >
                    <option value="">Select an upload...</option>
                    {uploads.map((u: any) => (
                      <option key={u.upload_id} value={u.upload_id}>
                        {u.filename || `Upload ${u.upload_id?.slice(0, 8)}`}
                        {u.ingestion_state ? ` (${u.ingestion_state})` : ""}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              {/* Run Button */}
              <button
                onClick={handleRunSimulation}
                disabled={!simPlaybookId || !simUploadId || simMutation.isPending}
                className={`flex items-center gap-1.5 px-4 py-1.5 text-[10px] font-medium rounded-lg transition-colors ${
                  !simPlaybookId || !simUploadId || simMutation.isPending
                    ? "bg-gray-100 text-gray-400 cursor-not-allowed dark:bg-navy-700 dark:text-gray-500"
                    : "bg-indigo-600 text-white hover:bg-indigo-700"
                }`}
              >
                {simMutation.isPending ? (
                  <>
                    <Loader2 className="w-3 h-3 animate-spin" />
                    Running Simulation...
                  </>
                ) : (
                  <>
                    <Activity className="w-3 h-3" />
                    Run Dry-Run Simulation
                  </>
                )}
              </button>
            </div>

            {/* Error State */}
            {simError && (
              <div className="rounded-lg border border-red-200 bg-red-50/80 dark:border-red-800 dark:bg-red-900/10 p-3">
                <div className="flex items-center gap-1.5 mb-1">
                  <XCircle className="w-3 h-3 text-red-500" />
                  <span className="text-[9px] font-semibold text-red-700 dark:text-red-300">Simulation Error</span>
                </div>
                <p className="text-[9px] text-red-600 dark:text-red-400">{simError}</p>
              </div>
            )}

            {/* Simulation Results */}
            {simResults && (
              <div className="space-y-3">
                {/* Summary Cards */}
                <div className="grid grid-cols-4 gap-3">
                  {[
                    { label: "Rules Evaluated", value: simResults.total_rules_evaluated ?? 0, color: "text-blue-600", icon: Activity },
                    { label: "Compliant Rules", value: simResults.rules_passed ?? 0, color: "text-green-600", icon: CheckCircle2 },
                    { label: "Violations", value: simResults.rules_failed ?? 0, color: simResults.rules_failed > 0 ? "text-red-600" : "text-green-600", icon: AlertTriangle },
                    { label: "Risk Level", value: simResults.risk_level || "N/A", color: simResults.risk_level === "critical" || simResults.risk_level === "high" ? "text-red-600" : "text-amber-600", icon: TrendingUp },
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

                {/* Impact Cards */}
                <div className="grid grid-cols-3 gap-3">
                  {[
                    { label: "Deviations Found", value: simResults.deviations_found ?? 0, color: simResults.deviations_found > 0 ? "text-orange-600" : "text-green-600", icon: AlertTriangle },
                    { label: "Mandatory Blocks", value: simResults.mandatory_blocks ?? 0, color: simResults.mandatory_blocks > 0 ? "text-red-600" : "text-green-600", icon: Ban },
                    { label: "Approval Required", value: simResults.approval_required ?? 0, color: simResults.approval_required > 0 ? "text-purple-600" : "text-green-600", icon: Lock },
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

                {/* Matched Rules Detail */}
                {simResults.results && simResults.results.length > 0 && (
                  <div className="rounded-lg border border-gray-200 dark:border-navy-700 bg-white dark:bg-navy-800 p-3">
                    <div className="flex items-center gap-1.5 mb-2">
                      <Shield className="w-3 h-3 text-gray-400" />
                      <span className="text-[9px] font-semibold text-gray-500 uppercase">Compliance Check Results</span>
                    </div>
                    <div className="space-y-1">
                      {simResults.results.map((rule: any, i: number) => (
                        <div key={rule.rule_id || i} className="flex items-center gap-2 p-1.5 rounded hover:bg-gray-50 dark:hover:bg-navy-750">
                          <span className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${rule.violation_triggered ? "bg-red-500" : "bg-green-500"}`} />
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-1.5">
                              <span className="text-[9px] font-medium text-navy-900 dark:text-white">{rule.rule_name}</span>
                              <span className={`text-[7px] font-medium px-1 py-0.5 rounded-full ${rule.violation_triggered ? "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400" : "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400"}`}>
                                {rule.violation_triggered ? "VIOLATION" : "COMPLIANT"}
                              </span>
                            </div>
                            <p className="text-[8px] text-gray-500 mt-0.5">
                              {rule.rule_type} &middot; Effect: {rule.effect?.replace(/_/g, " ")}
                              {rule.details ? ` &middot; ${rule.details}` : ""}
                            </p>
                          </div>
                          {rule.priority && (
                            <span className={`text-[7px] font-medium px-1 py-0.5 rounded-full ${
                              rule.priority >= 80 ? "bg-red-100 text-red-700" : rule.priority >= 60 ? "bg-amber-100 text-amber-700" : "bg-blue-100 text-blue-700"
                            }`}>
                              P{rule.priority}
                            </span>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Deviations Detail */}
                {simResults.deviations && simResults.deviations.length > 0 && (
                  <div className="rounded-lg border border-gray-200 dark:border-navy-700 bg-white dark:bg-navy-800 p-3">
                    <div className="flex items-center gap-1.5 mb-2">
                      <AlertTriangle className="w-3 h-3 text-orange-400" />
                      <span className="text-[9px] font-semibold text-gray-500 uppercase">Deviations</span>
                    </div>
                    <div className="space-y-1">
                      {simResults.deviations.map((dev: any, i: number) => (
                        <div key={i} className="p-2 rounded bg-gray-50 dark:bg-navy-750 border border-gray-100 dark:border-navy-700">
                          <div className="flex items-center gap-1.5 mb-1">
                            <span className={`text-[7px] font-medium px-1 py-0.5 rounded-full ${
                              dev.severity === "critical" || dev.severity === "high"
                                ? "bg-red-100 text-red-700"
                                : dev.severity === "medium"
                                ? "bg-amber-100 text-amber-700"
                                : "bg-blue-100 text-blue-700"
                            }`}>
                              {dev.severity}
                            </span>
                            <span className="text-[8px] font-medium text-navy-900 dark:text-white">
                              {dev.clause_category?.replace(/_/g, " ")}
                            </span>
                          </div>
                          <p className="text-[8px] text-gray-600 dark:text-gray-400 mb-0.5">
                            <span className="font-medium">Expected:</span> {dev.expected}
                          </p>
                          <p className="text-[8px] text-gray-600 dark:text-gray-400">
                            <span className="font-medium">Actual:</span> {dev.actual}
                          </p>
                          {dev.recommendation && (
                            <p className="text-[8px] text-indigo-600 dark:text-indigo-400 mt-0.5">
                              Recommendation: {dev.recommendation}
                            </p>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Recommendations */}
                {simResults.recommendations && simResults.recommendations.length > 0 && (
                  <div className="rounded-lg border border-gray-200 dark:border-navy-700 bg-white dark:bg-navy-800 p-3">
                    <div className="flex items-center gap-1.5 mb-2">
                      <FileText className="w-3 h-3 text-indigo-400" />
                      <span className="text-[9px] font-semibold text-gray-500 uppercase">Recommendations</span>
                    </div>
                    <div className="space-y-1">
                      {simResults.recommendations.map((rec: any, i: number) => (
                        <div key={i} className="flex items-start gap-2 p-1.5 rounded hover:bg-gray-50 dark:hover:bg-navy-750">
                          <CheckCircle2 className="w-2.5 h-2.5 text-indigo-400 mt-0.5" />
                          <div className="flex-1 min-w-0">
                            <p className="text-[9px] font-medium text-navy-900 dark:text-white">{rec.title}</p>
                            <p className="text-[8px] text-gray-500 mt-0.5">
                              {rec.clause_category?.replace(/_/g, " ")} &middot; {rec.clause_type?.replace(/_/g, " ")}
                              {rec.confidence_score ? ` &middot; Confidence: ${(rec.confidence_score * 100).toFixed(0)}%` : ""}
                            </p>
                            {rec.rationale && (
                              <p className="text-[8px] text-gray-500 italic mt-0.5">{rec.rationale}</p>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Empty State — no rules configured */}
                {(!simResults.results || simResults.results.length === 0) &&
                 (!simResults.deviations || simResults.deviations.length === 0) && (
                  <div className="rounded-lg border border-gray-200 dark:border-navy-700 bg-white dark:bg-navy-800 p-6 text-center">
                    {(simResults.total_rules_evaluated ?? 0) > 0 ? (
                      <>
                        <CheckCircle2 className="w-6 h-6 text-green-400 mx-auto mb-2" />
                        <p className="text-[10px] text-gray-500">Simulation completed — all rules compliant, no deviations found.</p>
                        <p className="text-[8px] text-gray-400 mt-1">
                          {simResults.total_rules_evaluated} rules evaluated
                          {simResults.risk_level ? ` · Risk level: ${simResults.risk_level}` : ""}
                        </p>
                      </>
                    ) : (
                      <>
                        <FileText className="w-6 h-6 text-amber-400 mx-auto mb-2" />
                        <p className="text-[10px] text-gray-500">No rules configured for this playbook.</p>
                        <p className="text-[8px] text-gray-400 mt-1">
                          Add policy rules to this playbook before running a simulation.
                        </p>
                      </>
                    )}
                  </div>
                )}
              </div>
            )}

            {/* Initial Empty State */}
            {!simResults && !simError && !simMutation.isPending && (
              <div className="rounded-lg border border-gray-200 dark:border-navy-700 bg-white dark:bg-navy-800 p-6 text-center">
                <TrendingUp className="w-6 h-6 text-gray-300 dark:text-gray-600 mx-auto mb-2" />
                <p className="text-[10px] text-gray-400">Select a playbook and contract upload, then click "Run Dry-Run Simulation"</p>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

/**
 * ContractDetailWorkspace — Repository-centric contract detail view.
 *
 * Purpose: Contract lifecycle overview, metadata, obligations, version history,
 * high-level risk summary, contract intelligence, and document preview.
 *
 * This is a REPOSITORY view — NOT a review/redline workspace.
 * For detailed review operations, use the dedicated workspaces:
 *   - /reviews/ai-workspace  (AI Review Workspace)
 *   - /reviews/{id}/redline   (Redline Experience)
 *
 * KEEP:
 * - Contract text preview
 * - Risk overview & exposure summary
 * - AI summary
 * - Lifecycle metadata
 * - Obligations
 * - Version history
 * - Document relationships
 * - Activity timeline
 *
 * REMOVED (delegated to dedicated workspaces):
 * - Detailed findings execution → "Open AI Review Workspace"
 * - Detailed explainability → "Open AI Review Workspace"
 * - Mitigation execution → "Open Redline Session"
 * - Inline review operations → "Open AI Review Workspace"
 * - Redline editing → "Open Redline Session"
 * - Negotiation editing → "Start Negotiation"
 * - Reviewer operational workflow controls → "Open AI Review Workspace"
 */

"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import {
  ArrowLeft, FileText, Brain, Shield, AlertTriangle, CheckCircle2,
  Clock, User, RefreshCw, Download, Share2, ExternalLink,
  Edit3, GitCompare, MessageSquare, Activity, Calendar,
  Building2, Globe, Loader2, ChevronDown, ChevronUp,
  BarChart3, BookOpen, XCircle, DollarSign,
} from "lucide-react";
import {
  useContractDetail,
  useContractActivity,
  useContractObligations,
  useContractVersions,
  useContractFindings,
  useContractClauses,
} from "./hooks";

// ── Props ───────────────────────────────────────────────────────────────────

interface ContractDetailWorkspaceProps {
  contractId: string;
}

// ── Main Component ──────────────────────────────────────────────────────────

export function ContractDetailWorkspace({ contractId }: ContractDetailWorkspaceProps) {
  const router = useRouter();
  const [activeTab, setActiveTab] = useState<"overview" | "insights" | "clauses" | "activity" | "versions">("overview");

  // ── Data Fetching (repository-only) ──────────────────────────────────

  const { data: contract, isLoading: contractLoading, error: contractError } = useContractDetail(contractId);
  const { data: activityData } = useContractActivity(contractId);
  const { data: obligationsData } = useContractObligations(contractId);
  const { data: versionsData } = useContractVersions(contractId);
  const { data: findingsData } = useContractFindings(contractId);
  const { data: clausesData } = useContractClauses(contractId);

  const activityEvents = activityData?.events ?? [];
  const obligations = obligationsData?.obligations ?? [];
  const versions = versionsData?.versions ?? [];
  const findings = findingsData?.findings ?? [];
  const clauses = clausesData?.clauses ?? [];

  // ── Navigation Actions ───────────────────────────────────────────────

  const openAiReview = () => router.push(`/reviews/ai-workspace?contractId=${contractId}`);
  const openRedline = () => router.push(`/reviews/${contractId}/redline`);
  const openNegotiation = () => router.push(`/negotiation/${contractId}`);

  // ── Loading ──────────────────────────────────────────────────────────

  if (contractLoading) {
    return (
      <div className="flex items-center justify-center h-full bg-gray-50 dark:bg-navy-900">
        <div className="text-center">
          <Loader2 className="w-8 h-8 text-blue-500 animate-spin mx-auto mb-3" />
          <p className="text-sm text-gray-500 dark:text-gray-400">Loading contract details...</p>
        </div>
      </div>
    );
  }

  if (contractError || !contract) {
    return (
      <div className="flex items-center justify-center h-full bg-gray-50 dark:bg-navy-900">
        <div className="text-center max-w-md">
          <AlertTriangle className="w-10 h-10 text-red-400 mx-auto mb-3" />
          <p className="text-sm font-medium text-gray-900 dark:text-white mb-1">Failed to load contract</p>
          <p className="text-xs text-gray-500 dark:text-gray-400 mb-4">Contract {contractId} could not be found or accessed.</p>
          <button onClick={() => router.push("/contracts")} className="inline-flex items-center gap-1.5 text-xs font-medium text-blue-600 hover:text-blue-700 dark:text-blue-400">
            <ArrowLeft className="w-3.5 h-3.5" /> Back to Contracts
          </button>
        </div>
      </div>
    );
  }

  const openObligations = obligations.filter(o => o.status === "overdue" || o.status === "pending").length;

  return (
    <div className="flex flex-col h-full bg-gray-50 dark:bg-navy-900">
      {/* ── Sticky Action Bar ──────────────────────────────────────────── */}
      <div className="flex items-center justify-between px-4 py-2 bg-white dark:bg-navy-800 border-b border-gray-200 dark:border-navy-700 shadow-sm z-10">
        <div className="flex items-center gap-3">
          <button onClick={() => router.push("/contracts")} className="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-navy-700 text-gray-500 dark:text-gray-400 transition-colors" aria-label="Back">
            <ArrowLeft className="w-4 h-4" />
          </button>
          <div className="flex items-center gap-2">
            <FileText className="w-4 h-4 text-navy-600 dark:text-navy-300" />
            <div>
              <h1 className="text-sm font-semibold text-navy-900 dark:text-white leading-tight">{contract.name}</h1>
              <p className="text-[10px] text-gray-500 dark:text-gray-400">{contract.filename} · {contract.total_pages} pages · v{versions.length > 0 ? versions[0].version_number : 1}</p>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-1.5">
          <button onClick={openAiReview} className="flex items-center gap-1 px-2.5 py-1.5 text-[10px] font-medium rounded-md bg-navy-600 text-white hover:bg-navy-700 transition-colors shadow-sm">
            <Brain className="w-3.5 h-3.5" /> AI Review
          </button>
          <button onClick={openRedline} className="flex items-center gap-1 px-2.5 py-1.5 text-[10px] font-medium rounded-md bg-white dark:bg-navy-700 border border-gray-200 dark:border-navy-600 text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-navy-600 transition-colors">
            <Edit3 className="w-3.5 h-3.5" /> Redline
          </button>
          <button onClick={openNegotiation} className="flex items-center gap-1 px-2.5 py-1.5 text-[10px] font-medium rounded-md bg-white dark:bg-navy-700 border border-gray-200 dark:border-navy-600 text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-navy-600 transition-colors">
            <GitCompare className="w-3.5 h-3.5" /> Negotiate
          </button>
          <div className="w-px h-5 bg-gray-200 dark:bg-navy-700 mx-1" />
          <button className="p-1.5 rounded-lg text-gray-400 hover:text-gray-600 hover:bg-gray-100 dark:hover:bg-navy-700 transition-colors" aria-label="Download"><Download className="w-4 h-4" /></button>
          <button className="p-1.5 rounded-lg text-gray-400 hover:text-gray-600 hover:bg-gray-100 dark:hover:bg-navy-700 transition-colors" aria-label="Share"><Share2 className="w-4 h-4" /></button>
        </div>
      </div>

      {/* ── Main 2-Panel Layout ────────────────────────────────────────── */}
      <div className="flex flex-1 overflow-hidden">
        {/* ── LEFT: Document Preview ───────────────────────────────────── */}
        <div className="w-[45%] min-w-[360px] border-r border-gray-200 dark:border-navy-700 overflow-y-auto bg-white dark:bg-navy-800">
          <div className="p-4">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <FileText className="w-4 h-4 text-gray-400" />
                <span className="text-xs font-medium text-navy-900 dark:text-white">{contract.name}</span>
              </div>
              <span className="text-[10px] text-gray-400">{contract.contract_type} · Page 1 of {contract.total_pages}</span>
            </div>

            <div className="bg-gray-50 dark:bg-navy-900 border border-gray-200 dark:border-navy-700 rounded-lg p-4 min-h-[400px]">
              <div className="text-[11px] leading-relaxed text-gray-700 dark:text-gray-300 space-y-2">
                <p className="font-semibold text-navy-900 dark:text-white text-xs">{contract.name}</p>
                <p className="text-gray-400 text-[10px]">Between {contract.vendor} and {contract.counterparty} · Effective: {new Date(contract.effective_date).toLocaleDateString()}</p>
                <hr className="border-gray-100 dark:border-navy-700 my-2" />
                <p><span className="font-medium">1.1 Services.</span> Vendor shall provide the services described in Exhibit A in accordance with the terms of this Agreement.</p>
                <p><span className="font-medium">1.2 Term.</span> This Agreement shall commence on the Effective Date and continue for an initial term of twelve (12) months.</p>
                <p className="text-gray-400 text-[10px] italic mt-4">Full document preview available in AI Review Workspace.</p>
              </div>
            </div>

            {/* AI Summary */}
            <div className="mt-3 p-3 rounded-lg bg-navy-50 dark:bg-navy-850 border border-navy-100 dark:border-navy-700">
              <div className="flex items-center gap-1.5 mb-1.5">
                <Brain className="w-3.5 h-3.5 text-navy-600" />
                <span className="text-[10px] font-semibold text-navy-700 dark:text-navy-200 uppercase tracking-wider">AI Summary</span>
              </div>
              <p className="text-[11px] text-gray-700 dark:text-gray-300 leading-relaxed">{contract.ai_summary}</p>
            </div>

            {(contract.missing_clauses?.length ?? 0) > 0 && (
              <div className="mt-3 p-3 rounded-lg bg-red-50 dark:bg-red-900/10 border border-red-200 dark:border-red-800">
                <div className="flex items-center gap-1.5 mb-1.5">
                  <XCircle className="w-3.5 h-3.5 text-red-500" />
                  <span className="text-[10px] font-semibold text-red-700 dark:text-red-300 uppercase tracking-wider">Missing Clauses</span>
                </div>
                <div className="space-y-1">
                  {contract.missing_clauses.map(mc => (
                    <div key={mc} className="flex items-center gap-1.5 text-[10px] text-red-600 dark:text-red-400">
                      <AlertTriangle className="w-3 h-3 flex-shrink-0" /> {mc}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* ── RIGHT: Repository Overview ───────────────────────────────── */}
        <div className="flex-1 overflow-y-auto bg-white dark:bg-navy-800">
          <div className="flex items-center border-b border-gray-200 dark:border-navy-700 bg-gray-50 dark:bg-navy-900 px-2">
            {[
              { id: "overview" as const, label: "Overview", icon: FileText },
              { id: "insights" as const, label: "AI Insights", icon: Brain, badge: findings.length },
              { id: "clauses" as const, label: "Clauses", icon: BookOpen, badge: clauses.length },
              { id: "activity" as const, label: "Activity", icon: Activity, badge: activityEvents.length },
              { id: "versions" as const, label: "Versions", icon: Clock, badge: versions.length },
            ].map(tab => {
              const Icon = tab.icon;
              const isActive = activeTab === tab.id;
              return (
                <button key={tab.id} onClick={() => setActiveTab(tab.id)}
                  className={`flex items-center gap-1.5 px-3 py-2.5 text-[11px] font-medium border-b-2 transition-all ${
                    isActive ? "border-navy-600 text-navy-700 dark:border-navy-300 dark:text-navy-200" : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 dark:hover:text-gray-300"
                  }`}>
                  <Icon className="w-3.5 h-3.5" />{tab.label}
                  {tab.badge !== undefined && tab.badge > 0 && (
                    <span className={`ml-1 text-[9px] font-bold px-1.5 py-0.5 rounded-full ${isActive ? "bg-navy-600 text-white" : "bg-gray-200 text-gray-600"}`}>{tab.badge}</span>
                  )}
                </button>
              );
            })}
          </div>

          <div className="p-4">
            {activeTab === "overview" && (
              <div className="space-y-4">
                {/* Risk Overview */}
                <div className="grid grid-cols-3 gap-3">
                  <div className="rounded-lg border border-gray-200 dark:border-navy-700 p-3 bg-gradient-to-br from-white to-gray-50 dark:from-navy-800 dark:to-navy-850">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-[9px] font-semibold text-gray-500 uppercase">Risk Score</span>
                      <span className={`text-lg font-bold ${contract.risk_score >= 8 ? "text-red-600" : contract.risk_score >= 6 ? "text-orange-600" : contract.risk_score >= 4 ? "text-amber-600" : "text-green-600"}`}>{contract.risk_score}</span>
                    </div>
                    <div className="h-1.5 bg-gray-100 dark:bg-navy-700 rounded-full overflow-hidden">
                      <div className={`h-full rounded-full ${contract.risk_score >= 8 ? "bg-red-500" : contract.risk_score >= 6 ? "bg-orange-500" : contract.risk_score >= 4 ? "bg-amber-500" : "bg-green-500"}`} style={{ width: `${(contract.risk_score / 10) * 100}%` }} />
                    </div>
                    <div className="flex items-center gap-2 mt-1.5 text-[8px] text-gray-500">
                      <span className="capitalize font-medium">{contract.risk_level} risk</span>
                      <span>·</span>
                      <span>{Math.round(contract.confidence_score * 100)}% AI confidence</span>
                    </div>
                  </div>
                  <div className="rounded-lg border border-gray-200 dark:border-navy-700 p-3">
                    <div className="text-[9px] font-semibold text-gray-500 uppercase mb-1">AI Findings</div>
                    <div className="text-lg font-bold text-navy-900 dark:text-white">{contract.ai_findings_count || 0}</div>
                    <div className="text-[8px] text-gray-500 mt-0.5">{contract.unresolved_risks || 0} unresolved risks</div>
                  </div>
                  <div className="rounded-lg border border-gray-200 dark:border-navy-700 p-3">
                    <div className="text-[9px] font-semibold text-gray-500 uppercase mb-1">Obligations</div>
                    <div className="text-lg font-bold text-navy-900 dark:text-white">{obligations.length}</div>
                    <div className="text-[8px] text-gray-500 mt-0.5">{openObligations} pending or overdue</div>
                  </div>
                </div>

                {/* Key Details */}
                <div className="rounded-lg border border-gray-200 dark:border-navy-700">
                  <div className="px-4 py-2 border-b border-gray-100 dark:border-navy-700 bg-gray-50 dark:bg-navy-850">
                    <span className="text-[9px] font-semibold text-gray-500 uppercase">Contract Details</span>
                  </div>
                  <div className="divide-y divide-gray-50 dark:divide-navy-800">
                    {[
                      { label: "Vendor", value: contract.vendor, icon: Building2 },
                      { label: "Counterparty", value: contract.counterparty, icon: User },
                      { label: "Type", value: contract.contract_type, icon: FileText },
                      { label: "Business Unit", value: contract.business_unit },
                      { label: "Geography", value: contract.geography, icon: Globe },
                      { label: "Owner", value: contract.owner, icon: User },
                      { label: "Status", value: contract.status.replace(/_/g, " ") },
                      { label: "Workflow Stage", value: contract.workflow_stage?.replace(/_/g, " ") ?? "—" },
                      { label: "Financial Value", value: contract.financial_value != null ? `${contract.currency ?? ""} ${contract.financial_value.toLocaleString()}` : "—", icon: DollarSign },
                      { label: "Auto-Renewal", value: contract.auto_renew ? "Yes" : "No" },
                      { label: "Has DPA", value: contract.has_dpa ? "Yes" : "No" },
                    ].map((row, i) => (
                      <div key={i} className="flex items-center justify-between px-4 py-1.5">
                        <span className="text-[10px] text-gray-500 dark:text-gray-400 flex items-center gap-1">
                          {row.icon && <row.icon className="w-3 h-3" />}{row.label}
                        </span>
                        <span className="text-[10px] font-medium text-gray-800 dark:text-gray-200 text-right max-w-[60%] truncate">{row.value}</span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Key Dates */}
                <div className="rounded-lg border border-gray-200 dark:border-navy-700">
                  <div className="px-4 py-2 border-b border-gray-100 dark:border-navy-700 bg-gray-50 dark:bg-navy-850">
                    <span className="text-[9px] font-semibold text-gray-500 uppercase">Key Dates</span>
                  </div>
                  <div className="divide-y divide-gray-50 dark:divide-navy-800">
                    {[
                      { label: "Effective", value: new Date(contract.effective_date).toLocaleDateString() },
                      { label: "Expiration", value: new Date(contract.expiration_date).toLocaleDateString() },
                      { label: "Renewal", value: new Date(contract.renewal_date).toLocaleDateString() },
                      { label: "Last Activity", value: new Date(contract.last_activity).toLocaleDateString() },
                      { label: "Created", value: new Date(contract.created_at).toLocaleDateString() },
                    ].map((row, i) => (
                      <div key={i} className="flex items-center justify-between px-4 py-1.5">
                        <span className="text-[10px] text-gray-500">{row.label}</span>
                        <span className="text-[10px] font-medium text-gray-800 dark:text-gray-200">{row.value}</span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Tags */}
                {contract.tags.length > 0 && (
                  <div className="rounded-lg border border-gray-200 dark:border-navy-700 p-3">
                    <span className="text-[9px] font-semibold text-gray-500 uppercase mb-2 block">Tags</span>
                    <div className="flex flex-wrap gap-1">
                      {contract.tags.map(tag => (
                        <span key={tag} className="text-[9px] px-2 py-0.5 rounded-full bg-navy-50 text-navy-700 dark:bg-navy-700 dark:text-navy-200">{tag}</span>
                      ))}
                    </div>
                  </div>
                )}

                {/* Navigation Actions */}
                <div className="rounded-lg border border-gray-200 dark:border-navy-700 overflow-hidden">
                  <div className="px-4 py-2 border-b border-gray-100 dark:border-navy-700 bg-gray-50 dark:bg-navy-850">
                    <span className="text-[9px] font-semibold text-gray-500 uppercase">Workspace Actions</span>
                  </div>
                  <div className="grid grid-cols-3 gap-3 p-4">
                    <button onClick={openAiReview} className="flex flex-col items-center gap-2 p-4 rounded-lg border border-gray-200 dark:border-navy-700 hover:border-navy-400 dark:hover:border-navy-400 hover:bg-gray-50 dark:hover:bg-navy-750 transition-all group">
                      <div className="w-10 h-10 rounded-full bg-navy-100 dark:bg-navy-700 flex items-center justify-center group-hover:bg-navy-200 dark:group-hover:bg-navy-600 transition-colors">
                        <Brain className="w-5 h-5 text-navy-600 dark:text-navy-300" />
                      </div>
                      <span className="text-[10px] font-semibold text-navy-900 dark:text-white">AI Review</span>
                      <span className="text-[8px] text-gray-400 text-center">Findings, policy, recommendations</span>
                    </button>
                    <button onClick={openRedline} className="flex flex-col items-center gap-2 p-4 rounded-lg border border-gray-200 dark:border-navy-700 hover:border-navy-400 dark:hover:border-navy-400 hover:bg-gray-50 dark:hover:bg-navy-750 transition-all group">
                      <div className="w-10 h-10 rounded-full bg-green-100 dark:bg-green-900/20 flex items-center justify-center group-hover:bg-green-200 dark:group-hover:bg-green-900/30 transition-colors">
                        <Edit3 className="w-5 h-5 text-green-600 dark:text-green-400" />
                      </div>
                      <span className="text-[10px] font-semibold text-navy-900 dark:text-white">Redline</span>
                      <span className="text-[8px] text-gray-400 text-center">Side-by-side compare, tracked changes</span>
                    </button>
                    <button onClick={openNegotiation} className="flex flex-col items-center gap-2 p-4 rounded-lg border border-gray-200 dark:border-navy-700 hover:border-navy-400 dark:hover:border-navy-400 hover:bg-gray-50 dark:hover:bg-navy-750 transition-all group">
                      <div className="w-10 h-10 rounded-full bg-amber-100 dark:bg-amber-900/20 flex items-center justify-center group-hover:bg-amber-200 dark:group-hover:bg-amber-900/30 transition-colors">
                        <GitCompare className="w-5 h-5 text-amber-600 dark:text-amber-400" />
                      </div>
                      <span className="text-[10px] font-semibold text-navy-900 dark:text-white">Negotiate</span>
                      <span className="text-[8px] text-gray-400 text-center">Concessions, version history, approvals</span>
                    </button>
                  </div>
                </div>

                {/* Obligations */}
                <div className="rounded-lg border border-gray-200 dark:border-navy-700">
                  <div className="px-4 py-2 border-b border-gray-100 dark:border-navy-700 bg-gray-50 dark:bg-navy-850 flex items-center justify-between">
                    <span className="text-[9px] font-semibold text-gray-500 uppercase">Obligations ({obligations.length})</span>
                    {obligations.filter(o => o.status === "overdue").length > 0 && (
                      <span className="text-[8px] font-medium text-red-600 bg-red-50 dark:bg-red-900/10 px-1.5 py-0.5 rounded">
                        {obligations.filter(o => o.status === "overdue").length} overdue
                      </span>
                    )}
                  </div>
                  <div className="divide-y divide-gray-50 dark:divide-navy-800">
                    {obligations.length === 0 ? (
                      <div className="px-4 py-3 text-[10px] text-gray-400 italic">No obligations tracked.</div>
                    ) : obligations.slice(0, 8).map(ob => (
                      <div key={ob.id} className="flex items-start gap-2 px-4 py-2">
                        <span className={`w-1.5 h-1.5 rounded-full mt-1.5 flex-shrink-0 ${
                          ob.status === "overdue" ? "bg-red-500" : ob.status === "completed" ? "bg-green-500" : ob.status === "in_progress" ? "bg-blue-500" : "bg-yellow-500"
                        }`} />
                        <div className="flex-1 min-w-0">
                          <p className="text-[10px] text-gray-700 dark:text-gray-300 truncate">{ob.description}</p>
                          <div className="flex items-center gap-2 mt-0.5">
                            <span className={`text-[8px] px-1 py-0.5 rounded font-medium ${
                              ob.status === "overdue" ? "bg-red-100 text-red-700" : ob.status === "completed" ? "bg-green-100 text-green-700" : ob.status === "in_progress" ? "bg-blue-100 text-blue-700" : "bg-yellow-100 text-yellow-700"
                            }`}>{ob.status.replace(/_/g, " ")}</span>
                            <span className="text-[8px] text-gray-400">Due: {new Date(ob.due_date).toLocaleDateString()}</span>
                            <span className="text-[8px] text-gray-400">{ob.owner}</span>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {activeTab === "insights" && (
              <div className="space-y-3">
                {/* AI Confidence & Summary */}
                <div className="rounded-lg border border-gray-200 dark:border-navy-700 p-3 bg-gradient-to-br from-purple-50 to-white dark:from-navy-800 dark:to-navy-850">
                  <div className="flex items-center gap-1.5 mb-2">
                    <Brain className="w-3.5 h-3.5 text-purple-500" />
                    <span className="text-[9px] font-semibold text-gray-500 uppercase">AI Detection</span>
                  </div>
                  <div className="flex items-center gap-3 mb-2">
                    <span className="text-xs text-gray-500">Confidence</span>
                    <div className="flex-1 h-2 bg-gray-200 dark:bg-navy-700 rounded-full overflow-hidden">
                      <div className={`h-full rounded-full ${(contract.confidence_score ?? 0) >= 0.7 ? "bg-green-500" : (contract.confidence_score ?? 0) >= 0.4 ? "bg-amber-500" : "bg-red-500"}`}
                        style={{ width: `${(contract.confidence_score ?? 0) * 100}%` }} />
                    </div>
                    <span className="text-[10px] font-bold text-navy-900 dark:text-white">{Math.round((contract.confidence_score ?? 0) * 100)}%</span>
                  </div>
                  {contract.ai_summary && (
                    <p className="text-[10px] text-gray-700 dark:text-gray-300 leading-relaxed">{contract.ai_summary}</p>
                  )}
                </div>

                {/* AI Findings */}
                <div className="rounded-lg border border-gray-200 dark:border-navy-700">
                  <div className="px-3 py-2 border-b border-gray-100 dark:border-navy-700 bg-gray-50 dark:bg-navy-850 flex items-center justify-between">
                    <span className="text-[9px] font-semibold text-gray-500 uppercase">AI Findings ({findings.length})</span>
                    <button onClick={openAiReview} className="text-[8px] font-medium text-blue-600 hover:text-blue-700">View all in Review →</button>
                  </div>
                  {findings.length === 0 ? (
                    <div className="px-3 py-4 text-[10px] text-gray-400 italic">No AI findings yet. Run AI analysis to detect risks.</div>
                  ) : (
                    <div className="divide-y divide-gray-50 dark:divide-navy-800">
                      {findings.slice(0, 10).map(f => (
                        <div key={f.id} className="flex items-start gap-2 px-3 py-2">
                          <span className={`w-1.5 h-1.5 rounded-full mt-1 flex-shrink-0 ${
                            f.severity === "critical" ? "bg-red-500" : f.severity === "high" ? "bg-orange-500" : f.severity === "medium" ? "bg-amber-500" : "bg-gray-400"
                          }`} />
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-1.5">
                              <span className="text-[10px] font-medium text-navy-900 dark:text-white">{f.title}</span>
                              <span className={`text-[7px] px-1 py-0.5 rounded font-medium ${
                                f.severity === "critical" ? "bg-red-100 text-red-700" : f.severity === "high" ? "bg-orange-100 text-orange-700" : f.severity === "medium" ? "bg-amber-100 text-amber-700" : "bg-gray-100 text-gray-600"
                              }`}>{f.severity}</span>
                            </div>
                            <p className="text-[9px] text-gray-500 mt-0.5 line-clamp-2">{f.description}</p>
                            {f.recommendation && (
                              <p className="text-[8px] text-blue-600 mt-0.5">{f.recommendation}</p>
                            )}
                          </div>
                          {f.confidence != null && (
                            <span className="text-[8px] text-gray-400 flex-shrink-0">{Math.round(f.confidence * 100)}%</span>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* AI Flags */}
                {contract.ai_flags.length > 0 && (
                  <div className="rounded-lg border border-amber-200 dark:border-amber-800 bg-amber-50 dark:bg-amber-900/10 p-3">
                    <span className="text-[9px] font-semibold text-amber-700 dark:text-amber-300 uppercase">AI Flags</span>
                    <div className="mt-1 space-y-1">
                      {contract.ai_flags.map(flag => (
                        <div key={flag} className="flex items-center gap-1.5 text-[9px] text-amber-600">
                          <AlertTriangle className="w-2.5 h-2.5 flex-shrink-0" /> {flag.replace(/_/g, " ")}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}

            {activeTab === "clauses" && (
              <div className="space-y-2">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-[9px] font-semibold text-gray-500 uppercase">Clause Analysis ({clauses.length})</span>
                  <span className="text-[8px] text-gray-400">{contract.clause_count} total clauses</span>
                </div>
                {clauses.length === 0 ? (
                  <div className="text-center py-8 text-xs text-gray-400">No clause analysis data available.</div>
                ) : (
                  <div className="space-y-1.5">
                    {clauses.map(c => (
                      <div key={c.id} className="flex items-start gap-2 p-2.5 rounded-lg border border-gray-200 dark:border-navy-700 hover:bg-gray-50 dark:hover:bg-navy-750 transition-colors">
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-1.5 mb-0.5">
                            <span className="text-[10px] font-semibold text-navy-900 dark:text-white capitalize">{c.clause_type.replace(/_/g, " ")}</span>
                            <span className={`text-[7px] px-1 py-0.5 rounded font-medium ${
                              c.severity === "critical" ? "bg-red-100 text-red-700" : c.severity === "high" ? "bg-orange-100 text-orange-700" : c.severity === "medium" ? "bg-amber-100 text-amber-700" : "bg-green-100 text-green-700"
                            }`}>{c.severity}</span>
                          </div>
                          <div className="grid grid-cols-2 gap-1 mt-1">
                            <div className="p-1.5 rounded bg-green-50 dark:bg-green-900/10 border border-green-100 dark:border-green-800">
                              <span className="text-[7px] font-semibold text-green-700 uppercase">Expected</span>
                              <p className="text-[8px] text-gray-600 mt-0.5">{c.expected}</p>
                            </div>
                            <div className="p-1.5 rounded bg-red-50 dark:bg-red-900/10 border border-red-100 dark:border-red-800">
                              <span className="text-[7px] font-semibold text-red-700 uppercase">Actual</span>
                              <p className="text-[8px] text-gray-600 mt-0.5">{c.actual}</p>
                            </div>
                          </div>
                          {c.recommendation && (
                            <p className="text-[8px] text-blue-600 mt-1">{c.recommendation}</p>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {activeTab === "activity" && (
              <div className="space-y-2">
                {activityEvents.length === 0 ? (
                  <div className="text-center py-8 text-xs text-gray-400">No activity recorded for this contract.</div>
                ) : (
                  <div className="relative">
                    <div className="absolute left-4 top-2 bottom-2 w-px bg-gray-200 dark:bg-navy-700" />
                    {activityEvents.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()).map(event => {
                      const Icon = EVENT_ICONS[event.type] || Activity;
                      const colors: Record<string, string> = {
                        contract_created: "bg-blue-100 text-blue-600", contract_uploaded: "bg-indigo-100 text-indigo-600",
                        ai_analysis_completed: "bg-purple-100 text-purple-600", finding_resolved: "bg-green-100 text-green-600",
                        comment_added: "bg-teal-100 text-teal-600", review_approved: "bg-green-100 text-green-600",
                        status_changed: "bg-amber-100 text-amber-600", version_created: "bg-blue-100 text-blue-600",
                      };
                      const color = colors[event.type] || "bg-gray-100 text-gray-600";
                      return (
                        <div key={event.id} className="relative flex gap-3 pb-4">
                          <div className={`relative z-10 w-8 h-8 rounded-full ${color} flex items-center justify-center flex-shrink-0`}>
                            <Icon className="w-4 h-4" />
                          </div>
                          <div className="flex-1 min-w-0 pt-0.5">
                            <p className="text-[11px] font-medium text-navy-900 dark:text-white">{event.action}</p>
                            <p className="text-[9px] text-gray-400 mt-0.5">{event.actor} · {formatTime(event.timestamp)}</p>
                            {event.details && <p className="text-[9px] text-gray-500 mt-0.5">{event.details}</p>}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            )}

            {activeTab === "versions" && (
              <div className="space-y-2">
                {versions.length === 0 ? (
                  <div className="text-center py-8 text-xs text-gray-400">No version history available.</div>
                ) : (
                  versions.map(v => (
                    <div key={v.id} className="flex items-center justify-between p-3 rounded-lg border border-gray-200 dark:border-navy-700 hover:bg-gray-50 dark:hover:bg-navy-750 transition-colors">
                      <div className="flex items-center gap-2">
                        <span className={`w-2 h-2 rounded-full ${v.status === "current" ? "bg-green-500" : v.status === "finalized" ? "bg-blue-500" : "bg-gray-400"}`} />
                        <div>
                          <p className="text-[11px] font-medium text-navy-900 dark:text-white">v{v.version_number} {v.label && `- ${v.label}`}</p>
                          <p className="text-[9px] text-gray-400">{v.uploaded_by} · {new Date(v.uploaded_at).toLocaleDateString()} · {v.page_count} pages</p>
                        </div>
                      </div>
                      <button className="p-1 rounded hover:bg-gray-100 dark:hover:bg-navy-700 text-gray-400"><Download className="w-3.5 h-3.5" /></button>
                    </div>
                  ))
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

// ── Helpers ─────────────────────────────────────────────────────────────────

const EVENT_ICONS: Record<string, React.ElementType> = {
  contract_created: FileText, contract_uploaded: FileText, ai_analysis_started: Brain,
  ai_analysis_completed: Brain, finding_resolved: CheckCircle2, finding_dismissed: XCircle,
  comment_added: MessageSquare, review_assigned: User, review_approved: CheckCircle2,
  review_rejected: XCircle, status_changed: Activity, obligation_updated: Calendar,
  renewal_approaching: AlertTriangle, version_created: FileText, metadata_updated: FileText,
};

function formatTime(ts: string): string {
  const diff = Date.now() - new Date(ts).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

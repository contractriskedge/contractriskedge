"use client";

import React, { useState, useMemo } from "react";
import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { motion, AnimatePresence } from "framer-motion";
import {
  X, FileText, Brain, AlertTriangle, DollarSign, Clock, User,
  CheckCircle, FileX, PenSquare,
  MessageSquare, Link, Activity, Calendar, ChevronRight, ExternalLink,
  Loader2, History,
} from "lucide-react";
import type { ContractRecord, ClauseSummary, Obligation, RelatedContract, ActivityEvent, RiskLevel } from "./types";
import { RISK_BG, RISK_TEXT, RISK_BG_LIGHT, AI_FLAG_CONFIG, WORKFLOW_STAGES } from "./types";
import {
  useContractFindings,
  useContractObligations,
  useContractActivity,
  useContractDetail,
} from "@/components/contract-detail/hooks";
import { fetchContracts } from "@/services/api/contracts";
import { formatDate, isMissingDate } from "@/lib/date-utils";

// ── Helpers ─────────────────────────────────────────────────────────────────

function formatMoney(value: number, currency: string = "USD"): string {
  if (!value) return "—";
  if (value >= 1_000_000_000) return `${(value / 1_000_000_000).toFixed(2)}B ${currency}`;
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(2)}M ${currency}`;
  if (value >= 1_000) return `${(value / 1_000).toFixed(1)}K ${currency}`;
  return `${value.toLocaleString()} ${currency}`;
}

function RiskBadge({ score }: { score: number }) {
  const level = score >= 8 ? "critical" : score >= 6 ? "high" : score >= 4 ? "medium" : "low";
  return (
    <span className={`inline-flex items-center gap-1 text-[10px] font-bold px-1.5 py-0.5 rounded-full ${RISK_BG_LIGHT[level]} ${RISK_TEXT[level]}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${RISK_BG[level]}`} />{score}/10
    </span>
  );
}

function TabBtn({ label, icon, active, onClick }: { label: string; icon: React.ReactNode; active: boolean; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className={`flex items-center gap-1 px-2.5 py-1.5 text-[10px] font-medium rounded-md whitespace-nowrap transition-all ${
        active ? "bg-navy-700 text-white shadow-sm" : "text-gray-500 hover:text-gray-700 hover:bg-gray-100"
      }`}
    >
      {icon}{label}
    </button>
  );
}

function EmptyState({ icon, message }: { icon: React.ReactNode; message: string }) {
  return (
    <div className="text-center py-8 text-gray-400">
      <div className="flex justify-center mb-2 opacity-50">{icon}</div>
      <p className="text-[11px]">{message}</p>
    </div>
  );
}

function LoadingState() {
  return (
    <div className="flex items-center justify-center py-10 text-gray-400 gap-2">
      <Loader2 className="w-4 h-4 animate-spin" />
      <span className="text-[11px]">Loading…</span>
    </div>
  );
}

function formatTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  if (Number.isNaN(diff)) return "—";
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

function mapActivityType(type: string): ActivityEvent["type"] {
  if (type.includes("upload")) return "upload";
  if (type.includes("analysis") || type.includes("ai")) return "analysis";
  if (type.includes("review") || type.includes("approved") || type.includes("rejected")) return "review";
  if (type.includes("redline")) return "redline";
  if (type.includes("comment")) return "comment";
  if (type.includes("signature") || type.includes("approved")) return "approval";
  return "review";
}

// ── Preview Drawer ──────────────────────────────────────────────────────────

interface PreviewDrawerProps {
  contract: ContractRecord | null;
  onClose: () => void;
}

type TabId = "overview" | "ai-insights" | "clauses" | "financials" | "activity" | "relationships";

export function PreviewDrawer({ contract, onClose }: PreviewDrawerProps) {
  const [tab, setTab] = useState<TabId>("overview");
  const router = useRouter();

  const openFullWorkspace = () => {
    if (contract) router.push(`/contracts/${contract.id}`);
  };

  return (
    <AnimatePresence>
      {contract && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/20 z-40"
            onClick={onClose}
          />
          <motion.div
            initial={{ opacity: 0, x: 380 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: 380 }}
            transition={{ type: "spring", damping: 25, stiffness: 250 }}
            className="fixed right-0 top-0 bottom-0 w-[480px] bg-white border-l border-gray-200 shadow-xl z-50 flex flex-col"
          >
            <div className="flex items-center justify-between px-5 py-4 border-b border-gray-200">
              <div className="flex items-center gap-2 min-w-0">
                <FileText className="w-4 h-4 text-navy-600 flex-shrink-0" />
                <div className="min-w-0">
                  <h3 className="text-sm font-semibold text-navy-900 truncate">{contract.name}</h3>
                  <p className="text-[10px] text-gray-500 truncate">{contract.contractNumber || contract.id}</p>
                </div>
              </div>
              <div className="flex items-center gap-1">
                <button
                  onClick={openFullWorkspace}
                  className="flex items-center gap-1 px-2 py-1 text-[10px] font-medium rounded-md bg-navy-600 text-white hover:bg-navy-700 transition-colors"
                >
                  <ExternalLink className="w-3 h-3" />
                  Full Workspace
                </button>
                <button onClick={onClose} className="p-1 rounded hover:bg-gray-100 text-gray-400 hover:text-gray-600 transition-colors">
                  <X className="w-4 h-4" />
                </button>
              </div>
            </div>

            <div className="px-4 py-2 border-b border-gray-100 flex gap-1 overflow-x-auto">
              <TabBtn label="Overview" icon={<FileText className="w-3 h-3" />} active={tab === "overview"} onClick={() => setTab("overview")} />
              <TabBtn label="AI Insights" icon={<Brain className="w-3 h-3" />} active={tab === "ai-insights"} onClick={() => setTab("ai-insights")} />
              <TabBtn label="Clauses" icon={<FileX className="w-3 h-3" />} active={tab === "clauses"} onClick={() => setTab("clauses")} />
              <TabBtn label="Financials" icon={<DollarSign className="w-3 h-3" />} active={tab === "financials"} onClick={() => setTab("financials")} />
              <TabBtn label="Activity" icon={<Activity className="w-3 h-3" />} active={tab === "activity"} onClick={() => setTab("activity")} />
              <TabBtn label="Relationships" icon={<Link className="w-3 h-3" />} active={tab === "relationships"} onClick={() => setTab("relationships")} />
            </div>

            <div className="flex-1 overflow-y-auto p-5 space-y-4">
              <PreviewDrawerTabs contract={contract} tab={tab} />
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}

function PreviewDrawerTabs({ contract, tab }: { contract: ContractRecord; tab: TabId }) {
  const contractId = contract.id;
  const { data: detail } = useContractDetail(contractId);
  const { data: findingsData, isLoading: findingsLoading } = useContractFindings(contractId, { page_size: 50 });
  const { data: obligationsData, isLoading: obligationsLoading } = useContractObligations(contractId);
  const { data: activityData, isLoading: activityLoading } = useContractActivity(contractId);

  const merged = useMemo((): ContractRecord => ({
    ...contract,
    vendor: contract.vendor || detail?.vendor || detail?.counterparty || "",
    businessUnit: contract.businessUnit || detail?.business_unit || "",
    geography: contract.geography || detail?.geography || "",
    financialValue: contract.financialValue || detail?.financial_value || 0,
    currency: contract.currency || detail?.currency || "USD",
    effectiveDate: contract.effectiveDate || detail?.effective_date || "",
    expirationDate: contract.expirationDate || detail?.expiration_date || "",
    renewalDate: contract.renewalDate || detail?.renewal_date || "",
    lastReviewDate: contract.lastReviewDate || detail?.updated_at || "",
    aiSummary: contract.aiSummary || detail?.ai_summary || contract.aiSummary,
    aiConfidence: contract.aiConfidence || Math.round((detail?.confidence_score ?? 0) * 100) || contract.aiConfidence,
    missingClauses: contract.missingClauses?.length ? contract.missingClauses : (detail?.missing_clauses ?? []),
    aiFlags: contract.aiFlags?.length ? contract.aiFlags : (detail?.ai_flags as ContractRecord["aiFlags"]) ?? contract.aiFlags,
    tags: contract.tags?.length ? contract.tags : (detail?.tags ?? []),
  }), [contract, detail]);

  const clauses: ClauseSummary[] = useMemo(() =>
    (findingsData?.findings ?? []).map((f) => ({
      type: f.clause_type || f.title || "Clause",
      risk: f.severity as RiskLevel,
      text: (f.clause_text || f.description || "").slice(0, 400),
      suggestion: f.recommendation || undefined,
    })),
  [findingsData]);

  const obligations: Obligation[] = useMemo(() =>
    (obligationsData?.obligations ?? []).map((o) => ({
      id: o.id,
      description: o.description,
      dueDate: o.due_date,
      owner: o.owner,
      status: o.status === "completed" ? "completed" : o.status === "overdue" ? "overdue" : "pending",
    })),
  [obligationsData]);

  const activityEvents: ActivityEvent[] = useMemo(() =>
    (activityData?.events ?? []).map((e) => ({
      id: e.id,
      type: mapActivityType(e.type),
      user: e.actor,
      action: e.action,
      timestamp: e.timestamp,
      details: e.details,
    })),
  [activityData]);

  if (tab === "overview") return <OverviewTab contract={merged} />;
  if (tab === "ai-insights") return (
    <AiInsightsTab
      contract={merged}
      findings={findingsData?.findings ?? []}
      loading={findingsLoading}
    />
  );
  if (tab === "clauses") return <ClausesTab clauses={clauses} loading={findingsLoading} />;
  if (tab === "financials") return (
    <FinancialsTab contract={merged} obligations={obligations} loading={obligationsLoading} />
  );
  if (tab === "activity") return <ActivityTab events={activityEvents} loading={activityLoading} />;
  if (tab === "relationships") return <RelationshipsTab contract={merged} />;
  return null;
}

// ── Overview Tab ────────────────────────────────────────────────────────────

function OverviewTab({ contract }: { contract: ContractRecord }) {
  const MetaRow = ({ label, value, icon }: { label: string; value: string | React.ReactNode; icon?: React.ReactNode }) => (
    <div className="flex items-center justify-between py-1.5">
      <span className="text-[11px] text-gray-500 flex items-center gap-1.5">{icon}{label}</span>
      <span className="text-[11px] font-medium text-gray-800 text-right max-w-[55%] truncate">{value}</span>
    </div>
  );

  return (
    <div className="space-y-4">
      {contract.aiSummary && (
        <div className="p-3 bg-navy-50 rounded-lg border border-navy-100">
          <div className="flex items-center gap-1.5 mb-1.5">
            <Brain className="w-3.5 h-3.5 text-navy-600" />
            <span className="text-[10px] font-semibold text-navy-700 uppercase tracking-wider">AI Summary</span>
          </div>
          <p className="text-[11px] text-gray-700 leading-relaxed">{contract.aiSummary}</p>
        </div>
      )}

      <div className="bg-gray-50 rounded-lg p-3 space-y-0.5 divide-y divide-gray-100">
        <MetaRow label="Contract #" value={contract.contractNumber || "—"} />
        <MetaRow label="Vendor" value={contract.vendor || "—"} icon={<User className="w-3 h-3" />} />
        <MetaRow label="Contract Type" value={contract.contractType || "—"} />
        <MetaRow label="Business Unit" value={contract.businessUnit || "—"} />
        <MetaRow label="Geography" value={contract.geography || "—"} />
        <MetaRow label="Health" value={
          <span className={`inline-flex items-center gap-1.5 text-[10px] font-medium px-1.5 py-0.5 rounded-full ${
            contract.health === "healthy" ? "text-emerald-700 bg-emerald-50" :
            contract.health === "needs_review" ? "text-amber-700 bg-amber-50" :
            contract.health === "high_risk" ? "text-red-700 bg-red-50" :
            "text-orange-700 bg-orange-50"
          }`}>
            {contract.health?.replace(/_/g, " ") || "needs review"}
          </span>
        } />
        <MetaRow label="Risk Score" value={<RiskBadge score={contract.riskScore} />} />
        <MetaRow label="Financial Value" value={formatMoney(contract.financialValue, contract.currency)} icon={<DollarSign className="w-3 h-3" />} />
        <MetaRow label="Status" value={contract.status?.replace(/_/g, " ") || "—"} />
        <MetaRow label="Effective" value={isMissingDate(contract.effectiveDate) ? "—" : formatDate(contract.effectiveDate)} />
        <MetaRow label="Expiration" value={isMissingDate(contract.expirationDate) ? "—" : formatDate(contract.expirationDate)} icon={<Calendar className="w-3 h-3" />} />
        <MetaRow label="Renewal Date" value={isMissingDate(contract.renewalDate) ? "—" : formatDate(contract.renewalDate)} />
        <MetaRow label="Last Review" value={isMissingDate(contract.lastReviewDate) ? "—" : formatDate(contract.lastReviewDate)} />
        <MetaRow label="Owner" value={contract.owner || "Unassigned"} icon={<User className="w-3 h-3" />} />
        <MetaRow label="Workflow Stage" value={WORKFLOW_STAGES[contract.workflowStage as keyof typeof WORKFLOW_STAGES]?.label || contract.workflowStage} />
        <MetaRow label="Original File" value={contract.originalFilename || "—"} />
      </div>

      {contract.tags.length > 0 && (
        <div>
          <p className="text-[10px] font-semibold text-gray-500 uppercase mb-1.5">Tags</p>
          <div className="flex gap-1 flex-wrap">
            {contract.tags.map((t) => (
              <span key={t} className="text-[10px] px-1.5 py-0.5 rounded bg-navy-50 text-navy-700">{t}</span>
            ))}
          </div>
        </div>
      )}

      {contract.aiFlags.length > 0 && (
        <div>
          <p className="text-[10px] font-semibold text-gray-500 uppercase mb-1.5">AI Flags</p>
          <div className="space-y-1">
            {contract.aiFlags.map((flag) => {
              const cfg = AI_FLAG_CONFIG[flag];
              if (!cfg) return null;
              return (
                <div key={flag} className={`flex items-center gap-2 px-2.5 py-1.5 rounded-lg ${cfg.bg}`}>
                  <AlertTriangle className="w-3 h-3" />
                  <span className={`text-[11px] font-medium ${cfg.color}`}>{cfg.label}</span>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {contract.missingClauses.length > 0 && (
        <div>
          <p className="text-[10px] font-semibold text-gray-500 uppercase mb-1.5">Missing Clauses</p>
          <div className="space-y-1">
            {contract.missingClauses.map((mc) => (
              <div key={mc} className="flex items-center gap-2 px-2.5 py-1.5 rounded-lg bg-red-50">
                <FileX className="w-3 h-3 text-red-500" />
                <span className="text-[11px] font-medium text-red-700">{mc}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ── AI Insights Tab ────────────────────────────────────────────────────────

function AiInsightsTab({
  contract,
  findings,
  loading,
}: {
  contract: ContractRecord;
  findings: Array<{ id: string; title: string; severity: string; description: string; recommendation: string; confidence: number }>;
  loading: boolean;
}) {
  if (loading) return <LoadingState />;

  const topFindings = findings.filter((f) => f.severity === "critical" || f.severity === "high").slice(0, 5);

  return (
    <div className="space-y-4">
      <div className="p-3 bg-white border border-gray-200 rounded-lg">
        <div className="flex items-center justify-between mb-1.5">
          <span className="text-[10px] font-semibold text-gray-500 uppercase">AI Detection Confidence</span>
          <span className="text-xs font-bold">{contract.aiConfidence}%</span>
        </div>
        <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
          <div
            className={`h-full rounded-full ${contract.aiConfidence >= 85 ? "bg-green-500" : contract.aiConfidence >= 70 ? "bg-yellow-500" : "bg-red-500"}`}
            style={{ width: `${Math.min(100, contract.aiConfidence)}%` }}
          />
        </div>
      </div>

      {contract.aiFlags.map((flag) => {
        const cfg = AI_FLAG_CONFIG[flag];
        if (!cfg) return null;
        return (
          <div key={flag} className={`p-3 rounded-lg border ${cfg.bg} border-l-4`}>
            <div className="flex items-center gap-1.5 mb-1">
              <AlertTriangle className="w-3.5 h-3.5" />
              <span className={`text-[11px] font-semibold ${cfg.color}`}>{cfg.label}</span>
            </div>
            <p className="text-[11px] text-gray-600 leading-relaxed">
              {flag === "critical" && "This contract contains critical risk indicators that require immediate legal review."}
              {flag === "review_needed" && "AI recommends manual review of specific clauses before proceeding."}
              {flag === "benchmark_deviation" && "Key terms deviate significantly from market benchmarks for similar agreements."}
              {flag === "auto_renewal_risk" && "Auto-renewal clause may trigger unfavorable terms. Review notice period."}
              {flag === "compliance_issue" && "Potential compliance gap detected. Regulatory requirements may not be fully addressed."}
              {flag === "missing_clause" && "Essential clauses missing that are standard for this contract type."}
            </p>
          </div>
        );
      })}

      {topFindings.length > 0 && (
        <div>
          <p className="text-[10px] font-semibold text-gray-500 uppercase mb-2">Top Findings ({findings.length} total)</p>
          <div className="space-y-2">
            {topFindings.map((f) => (
              <div key={f.id} className="p-2.5 bg-white border border-gray-200 rounded-lg">
                <div className="flex items-center justify-between gap-2 mb-1">
                  <span className="text-[11px] font-semibold text-navy-900 truncate">{f.title}</span>
                  <span className={`text-[9px] px-1.5 py-0.5 rounded-full font-medium ${
                    f.severity === "critical" ? "bg-red-100 text-red-700" :
                    f.severity === "high" ? "bg-orange-100 text-orange-700" :
                    "bg-yellow-100 text-yellow-700"
                  }`}>{f.severity}</span>
                </div>
                <p className="text-[10px] text-gray-600 line-clamp-2">{f.description}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="p-3 bg-navy-50 rounded-lg border border-navy-100">
        <h4 className="text-[10px] font-semibold text-navy-700 uppercase mb-1.5">AI Recommendations</h4>
        <ul className="space-y-1.5">
          {contract.missingClauses.length > 0 && (
            <li className="text-[11px] text-gray-700 flex items-start gap-1.5">
              <ChevronRight className="w-3 h-3 text-navy-500 mt-0.5 flex-shrink-0" />
              Add missing {contract.missingClauses.join(", ")} clause{contract.missingClauses.length > 1 ? "s" : ""}
            </li>
          )}
          {findings.length > 0 && (
            <li className="text-[11px] text-gray-700 flex items-start gap-1.5">
              <ChevronRight className="w-3 h-3 text-navy-500 mt-0.5 flex-shrink-0" />
              Review {findings.length} AI finding{findings.length !== 1 ? "s" : ""} in the AI workspace
            </li>
          )}
          {contract.autoRenew && (
            <li className="text-[11px] text-gray-700 flex items-start gap-1.5">
              <ChevronRight className="w-3 h-3 text-navy-500 mt-0.5 flex-shrink-0" />
              Review auto-renewal terms before the notice window
            </li>
          )}
          {findings.length === 0 && contract.missingClauses.length === 0 && (
            <li className="text-[11px] text-gray-700 flex items-start gap-1.5">
              <ChevronRight className="w-3 h-3 text-navy-500 mt-0.5 flex-shrink-0" />
              Schedule quarterly risk review for this contract
            </li>
          )}
        </ul>
      </div>
    </div>
  );
}

// ── Clauses Tab ─────────────────────────────────────────────────────────────

function ClausesTab({ clauses, loading }: { clauses: ClauseSummary[]; loading: boolean }) {
  if (loading) return <LoadingState />;
  if (clauses.length === 0) {
    return <EmptyState icon={<FileX className="w-6 h-6" />} message="No clause findings yet. Run AI review to analyze clauses." />;
  }

  return (
    <div className="space-y-2">
      <p className="text-[10px] font-semibold text-gray-500 uppercase mb-2">Clause Analysis ({clauses.length})</p>
      {clauses.map((clause, i) => (
        <div key={i} className="p-3 bg-white border border-gray-200 rounded-lg space-y-1.5">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-semibold text-navy-900 capitalize">{clause.type.replace(/_/g, " ")}</span>
            <RiskBadge score={clause.risk === "critical" ? 9 : clause.risk === "high" ? 7 : clause.risk === "medium" ? 5 : 2} />
          </div>
          <p className="text-[10px] text-gray-600 leading-relaxed line-clamp-4">{clause.text}</p>
          {clause.suggestion && (
            <div className="p-2 bg-green-50 rounded border border-green-100">
              <span className="text-[9px] font-semibold text-green-700 uppercase">Suggestion</span>
              <p className="text-[10px] text-gray-700 mt-0.5 line-clamp-3">{clause.suggestion}</p>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

// ── Financials Tab ──────────────────────────────────────────────────────────

function FinancialsTab({
  contract,
  obligations,
  loading,
}: {
  contract: ContractRecord;
  obligations: Obligation[];
  loading: boolean;
}) {
  if (loading) return <LoadingState />;

  return (
    <div className="space-y-4">
      <div className="p-4 bg-gray-50 rounded-lg text-center">
        <p className="text-[10px] text-gray-500 uppercase font-semibold">Contract Value</p>
        <p className="text-2xl font-bold text-navy-900 mt-1">
          {contract.financialValue ? formatMoney(contract.financialValue, contract.currency) : "—"}
        </p>
      </div>

      <div>
        <p className="text-[10px] font-semibold text-gray-500 uppercase mb-2">
          Obligations Due {obligations.length > 0 ? `(${obligations.length})` : ""}
        </p>
        {obligations.length === 0 ? (
          <EmptyState icon={<CheckCircle className="w-6 h-6" />} message="No obligations tracked for this contract." />
        ) : (
          <div className="space-y-1.5">
            {obligations.map((obl) => (
              <div key={obl.id} className="flex items-center gap-2 p-2 bg-white border border-gray-100 rounded-lg">
                {obl.status === "completed" ? <CheckCircle className="w-3 h-3 text-green-500" /> :
                 obl.status === "overdue" ? <AlertTriangle className="w-3 h-3 text-red-500" /> :
                 <Clock className="w-3 h-3 text-yellow-500" />}
                <div className="flex-1 min-w-0">
                  <p className="text-[11px] text-gray-700 truncate">{obl.description}</p>
                  <p className="text-[9px] text-gray-400">
                    {obl.owner || "Unassigned"}
                    {obl.dueDate && !isMissingDate(obl.dueDate) ? ` · Due ${formatDate(obl.dueDate)}` : ""}
                  </p>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// ── Activity Tab ────────────────────────────────────────────────────────────

function ActivityTab({ events, loading }: { events: ActivityEvent[]; loading: boolean }) {
  if (loading) return <LoadingState />;
  if (events.length === 0) {
    return <EmptyState icon={<History className="w-6 h-6" />} message="No activity recorded yet for this contract." />;
  }

  return (
    <div className="space-y-2">
      <p className="text-[10px] font-semibold text-gray-500 uppercase mb-2">Recent Activity</p>
      {events.slice(0, 12).map((event) => (
        <div key={event.id} className="flex items-start gap-2.5 p-2.5 bg-white border border-gray-100 rounded-lg">
          <div className={`w-6 h-6 rounded-full flex items-center justify-center flex-shrink-0 ${
            event.type === "upload" ? "bg-blue-50" :
            event.type === "analysis" ? "bg-purple-50" :
            event.type === "review" ? "bg-yellow-50" :
            event.type === "approval" ? "bg-green-50" :
            event.type === "redline" ? "bg-pink-50" :
            "bg-gray-50"
          }`}>
            {event.type === "upload" ? <UploadIcon /> :
             event.type === "analysis" ? <Brain className="w-3 h-3 text-purple-600" /> :
             event.type === "review" ? <FileText className="w-3 h-3 text-yellow-600" /> :
             event.type === "approval" ? <CheckCircle className="w-3 h-3 text-green-600" /> :
             event.type === "redline" ? <PenSquare className="w-3 h-3 text-pink-600" /> :
             <MessageSquare className="w-3 h-3 text-gray-600" />}
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-[11px] font-medium text-gray-800">{event.action}</p>
            {event.details && <p className="text-[10px] text-gray-500 mt-0.5 line-clamp-2">{event.details}</p>}
            <p className="text-[9px] text-gray-400 mt-0.5">{event.user} · {formatTime(event.timestamp)}</p>
          </div>
        </div>
      ))}
    </div>
  );
}

// ── Relationships Tab ───────────────────────────────────────────────────────

function RelationshipsTab({ contract }: { contract: ContractRecord }) {
  const party = (contract.vendor || contract.counterparty || "").trim();

  const { data, isLoading } = useQuery({
    queryKey: ["preview-related-contracts", party],
    queryFn: async () => {
      const res = await fetchContracts({ search: party, page_size: 50 });
      const partyLower = party.toLowerCase();
      return {
        data: (res.data ?? []).filter((c) => {
          if (c.id === contract.id) return false;
          const cParty = (c.vendor || c.counterparty || "").trim().toLowerCase();
          return cParty.length > 0 && cParty === partyLower;
        }),
      };
    },
    enabled: party.length > 0,
    staleTime: 60_000,
  });

  const related: RelatedContract[] = useMemo(() =>
    (data?.data ?? []).slice(0, 10).map((c) => ({
      id: c.id,
      name: c.name,
      relationship: `Same vendor · ${c.contractType || "contract"}`,
      riskScore: c.riskScore,
    })),
  [data]);

  if (!party) {
    return (
      <EmptyState
        icon={<Link className="w-6 h-6" />}
        message="No linked contracts. Vendor must be set to show related agreements."
      />
    );
  }

  if (isLoading) return <LoadingState />;
  if (related.length === 0) {
    return (
      <EmptyState
        icon={<Link className="w-6 h-6" />}
        message={`No other contracts found for ${party}.`}
      />
    );
  }

  return (
    <div className="space-y-2">
      <p className="text-[10px] font-semibold text-gray-500 uppercase mb-2">Related Contracts</p>
      {related.map((rc) => (
        <div key={rc.id} className="flex items-center gap-2.5 p-2.5 bg-white border border-gray-100 rounded-lg hover:bg-gray-50 cursor-pointer transition-colors">
          <Link className="w-3.5 h-3.5 text-navy-400 flex-shrink-0" />
          <div className="flex-1 min-w-0">
            <p className="text-[11px] font-medium text-gray-800 truncate">{rc.name}</p>
            <p className="text-[9px] text-gray-400">{rc.relationship}</p>
          </div>
          <RiskBadge score={rc.riskScore} />
        </div>
      ))}
    </div>
  );
}

function UploadIcon() {
  return (
    <svg className="w-3 h-3 text-blue-600" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5" />
    </svg>
  );
}

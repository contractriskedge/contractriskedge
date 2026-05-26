"use client";

import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  X, FileText, Brain, AlertTriangle, Shield, DollarSign, Clock, User,
  CheckCircle, XCircle, FileX, RefreshCw, BarChart3, PenSquare,
  MessageSquare, Link, Activity, Calendar, ChevronRight,
} from "lucide-react";
import type { ContractRecord, ClauseSummary, Obligation, RelatedContract, ActivityEvent } from "./types";
import { RISK_BG, RISK_TEXT, RISK_BG_LIGHT, AI_FLAG_CONFIG, WORKFLOW_STAGES } from "./types";
import { mockClauses, mockObligations, mockRelatedContracts, activityEvents } from "./mockData";

// ── Risk Badge ──────────────────────────────────────────────────────────────

function RiskBadge({ score }: { score: number }) {
  const level = score >= 8 ? "critical" : score >= 6 ? "high" : score >= 4 ? "medium" : "low";
  return (
    <span className={`inline-flex items-center gap-1 text-[10px] font-bold px-1.5 py-0.5 rounded-full ${RISK_BG_LIGHT[level]} ${RISK_TEXT[level]}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${RISK_BG[level]}`} />{score}/10
    </span>
  );
}

// ── Tab Button ──────────────────────────────────────────────────────────────

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

// ── Preview Drawer ──────────────────────────────────────────────────────────

interface PreviewDrawerProps {
  contract: ContractRecord | null;
  onClose: () => void;
}

type TabId = "overview" | "ai-insights" | "clauses" | "financials" | "activity" | "relationships" | "audit";

export function PreviewDrawer({ contract, onClose }: PreviewDrawerProps) {
  const [tab, setTab] = useState<TabId>("overview");

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
            {/* Header */}
            <div className="flex items-center justify-between px-5 py-4 border-b border-gray-200">
              <div className="flex items-center gap-2 min-w-0">
                <FileText className="w-4 h-4 text-navy-600 flex-shrink-0" />
                <div className="min-w-0">
                  <h3 className="text-sm font-semibold text-navy-900 truncate">{contract.name}</h3>
                  <p className="text-[10px] text-gray-500">{contract.id}</p>
                </div>
              </div>
              <button onClick={onClose} className="p-1 rounded hover:bg-gray-100 text-gray-400 hover:text-gray-600 transition-colors">
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Tabs */}
            <div className="px-4 py-2 border-b border-gray-100 flex gap-1 overflow-x-auto">
              <TabBtn label="Overview" icon={<FileText className="w-3 h-3" />} active={tab === "overview"} onClick={() => setTab("overview")} />
              <TabBtn label="AI Insights" icon={<Brain className="w-3 h-3" />} active={tab === "ai-insights"} onClick={() => setTab("ai-insights")} />
              <TabBtn label="Clauses" icon={<FileX className="w-3 h-3" />} active={tab === "clauses"} onClick={() => setTab("clauses")} />
              <TabBtn label="Financials" icon={<DollarSign className="w-3 h-3" />} active={tab === "financials"} onClick={() => setTab("financials")} />
              <TabBtn label="Activity" icon={<Activity className="w-3 h-3" />} active={tab === "activity"} onClick={() => setTab("activity")} />
              <TabBtn label="Relationships" icon={<Link className="w-3 h-3" />} active={tab === "relationships"} onClick={() => setTab("relationships")} />
            </div>

            {/* Content */}
            <div className="flex-1 overflow-y-auto p-5 space-y-4">
              {tab === "overview" && <OverviewTab contract={contract} />}
              {tab === "ai-insights" && <AiInsightsTab contract={contract} />}
              {tab === "clauses" && <ClausesTab />}
              {tab === "financials" && <FinancialsTab contract={contract} />}
              {tab === "activity" && <ActivityTab />}
              {tab === "relationships" && <RelationshipsTab />}
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}

// ── Overview Tab ────────────────────────────────────────────────────────────

function OverviewTab({ contract }: { contract: ContractRecord }) {
  const MetaRow = ({ label, value, icon }: { label: string; value: string | React.ReactNode; icon?: React.ReactNode }) => (
    <div className="flex items-center justify-between py-1.5">
      <span className="text-[11px] text-gray-500 flex items-center gap-1.5">{icon}{label}</span>
      <span className="text-[11px] font-medium text-gray-800">{value}</span>
    </div>
  );

  return (
    <div className="space-y-4">
      {/* AI Summary */}
      <div className="p-3 bg-navy-50 rounded-lg border border-navy-100">
        <div className="flex items-center gap-1.5 mb-1.5">
          <Brain className="w-3.5 h-3.5 text-navy-600" />
          <span className="text-[10px] font-semibold text-navy-700 uppercase tracking-wider">AI Summary</span>
        </div>
        <p className="text-[11px] text-gray-700 leading-relaxed">{contract.aiSummary}</p>
      </div>

      {/* Metadata */}
      <div className="bg-gray-50 rounded-lg p-3 space-y-0.5 divide-y divide-gray-100">
        <MetaRow label="Vendor" value={contract.vendor} icon={<User className="w-3 h-3" />} />
        <MetaRow label="Contract Type" value={contract.contractType} />
        <MetaRow label="Business Unit" value={contract.businessUnit} />
        <MetaRow label="Geography" value={contract.geography} />
        <MetaRow label="Risk Score" value={<RiskBadge score={contract.riskScore} />} />
        <MetaRow label="Financial Value" value={`$${contract.financialValue}M`} icon={<DollarSign className="w-3 h-3" />} />
        <MetaRow label="Status" value={<span className={`text-[10px] font-medium px-1.5 py-0.5 rounded-full ${contract.status === "active" ? "bg-green-100 text-green-700" : contract.status === "expiring_soon" ? "bg-yellow-100 text-yellow-700" : "bg-gray-100 text-gray-600"}`}>{contract.status.replace(/_/g, " ")}</span>} />
        <MetaRow label="Renewal Date" value={contract.renewalDate} icon={<Calendar className="w-3 h-3" />} />
        <MetaRow label="Owner" value={contract.owner} icon={<User className="w-3 h-3" />} />
        <MetaRow label="Workflow Stage" value={WORKFLOW_STAGES[contract.workflowStage]?.label || contract.workflowStage} />
        <MetaRow label="Pages" value={contract.totalPages.toString()} icon={<FileText className="w-3 h-3" />} />
        <MetaRow label="Clauses" value={contract.clauseCount.toString()} />
        <MetaRow label="Auto-Renewal" value={contract.autoRenew ? "Yes" : "No"} />
        <MetaRow label="Has DPA" value={contract.hasDpa ? "Yes" : "No"} />
      </div>

      {/* Tags */}
      <div>
        <p className="text-[10px] font-semibold text-gray-500 uppercase mb-1.5">Tags</p>
        <div className="flex gap-1 flex-wrap">
          {contract.tags.map((t) => (
            <span key={t} className="text-[10px] px-1.5 py-0.5 rounded bg-navy-50 text-navy-700">{t}</span>
          ))}
        </div>
      </div>

      {/* AI Flags */}
      {contract.aiFlags.length > 0 && (
        <div>
          <p className="text-[10px] font-semibold text-gray-500 uppercase mb-1.5">AI Flags</p>
          <div className="space-y-1">
            {contract.aiFlags.map((flag) => {
              const cfg = AI_FLAG_CONFIG[flag];
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

      {/* Missing Clauses */}
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

function AiInsightsTab({ contract }: { contract: ContractRecord }) {
  return (
    <div className="space-y-4">
      {/* Confidence */}
      <div className="p-3 bg-white border border-gray-200 rounded-lg">
        <div className="flex items-center justify-between mb-1.5">
          <span className="text-[10px] font-semibold text-gray-500 uppercase">AI Detection Confidence</span>
          <span className="text-xs font-bold">{contract.aiConfidence}%</span>
        </div>
        <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
          <div className={`h-full rounded-full ${contract.aiConfidence >= 85 ? "bg-green-500" : contract.aiConfidence >= 70 ? "bg-yellow-500" : "bg-red-500"}`}
            style={{ width: `${contract.aiConfidence}%` }} />
        </div>
      </div>

      {/* AI Flags */}
      {contract.aiFlags.map((flag) => {
        const cfg = AI_FLAG_CONFIG[flag];
        return (
          <div key={flag} className={`p-3 rounded-lg border ${cfg.bg} border-l-4`} style={{ borderLeftColor: cfg.color.replace("text-", "").replace("700", "500") }}>
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

      {/* AI Recommendations */}
      <div className="p-3 bg-navy-50 rounded-lg border border-navy-100">
        <h4 className="text-[10px] font-semibold text-navy-700 uppercase mb-1.5">AI Recommendations</h4>
        <ul className="space-y-1.5">
          {contract.missingClauses.length > 0 && (
            <li className="text-[11px] text-gray-700 flex items-start gap-1.5">
              <ChevronRight className="w-3 h-3 text-navy-500 mt-0.5 flex-shrink-0" />
              Add missing {contract.missingClauses.join(", ")} clause{contract.missingClauses.length > 1 ? "s" : ""}
            </li>
          )}
          {contract.autoRenew && (
            <li className="text-[11px] text-gray-700 flex items-start gap-1.5">
              <ChevronRight className="w-3 h-3 text-navy-500 mt-0.5 flex-shrink-0" />
              Review auto-renewal terms before the 60-day notice window
            </li>
          )}
          <li className="text-[11px] text-gray-700 flex items-start gap-1.5">
            <ChevronRight className="w-3 h-3 text-navy-500 mt-0.5 flex-shrink-0" />
            Schedule quarterly risk review for this contract
          </li>
        </ul>
      </div>
    </div>
  );
}

// ── Clauses Tab ─────────────────────────────────────────────────────────────

function ClausesTab() {
  return (
    <div className="space-y-2">
      <p className="text-[10px] font-semibold text-gray-500 uppercase mb-2">Clause Analysis</p>
      {mockClauses.map((clause, i) => {
        const level = clause.risk === "critical" ? "critical" : clause.risk === "high" ? "high" : clause.risk === "medium" ? "medium" : "low";
        return (
          <div key={i} className="p-3 bg-white border border-gray-200 rounded-lg space-y-1.5">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-semibold text-navy-900">{clause.type}</span>
              <RiskBadge score={clause.risk === "critical" ? 9 : clause.risk === "high" ? 7 : clause.risk === "medium" ? 5 : 2} />
            </div>
            <p className="text-[10px] text-gray-600 leading-relaxed">{clause.text}</p>
            {clause.suggestion && (
              <div className="p-2 bg-green-50 rounded border border-green-100">
                <span className="text-[9px] font-semibold text-green-700 uppercase">Suggestion</span>
                <p className="text-[10px] text-gray-700 mt-0.5">{clause.suggestion}</p>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

// ── Financials Tab ──────────────────────────────────────────────────────────

function FinancialsTab({ contract }: { contract: ContractRecord }) {
  return (
    <div className="space-y-4">
      <div className="p-4 bg-gray-50 rounded-lg text-center">
        <p className="text-[10px] text-gray-500 uppercase font-semibold">Contract Value</p>
        <p className="text-2xl font-bold text-navy-900 mt-1">${contract.financialValue}M</p>
        <p className="text-[10px] text-gray-400 mt-0.5">{contract.currency}</p>
      </div>

      {/* Obligations */}
      <div>
        <p className="text-[10px] font-semibold text-gray-500 uppercase mb-2">Obligations Due</p>
        <div className="space-y-1.5">
          {mockObligations.map((obl) => (
            <div key={obl.id} className="flex items-center gap-2 p-2 bg-white border border-gray-100 rounded-lg">
              {obl.status === "completed" ? <CheckCircle className="w-3 h-3 text-green-500" /> :
               obl.status === "overdue" ? <AlertTriangle className="w-3 h-3 text-red-500" /> :
               <Clock className="w-3 h-3 text-yellow-500" />}
              <div className="flex-1 min-w-0">
                <p className="text-[11px] text-gray-700 truncate">{obl.description}</p>
                <p className="text-[9px] text-gray-400">{obl.owner} • Due {obl.dueDate}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// ── Activity Tab ────────────────────────────────────────────────────────────

function ActivityTab() {
  return (
    <div className="space-y-2">
      <p className="text-[10px] font-semibold text-gray-500 uppercase mb-2">Recent Activity</p>
      {activityEvents.slice(0, 8).map((event) => (
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
             event.type === "analysis" ? <BrainIcon /> :
             event.type === "review" ? <FileTextIcon /> :
             event.type === "approval" ? <CheckIcon /> :
             event.type === "redline" ? <PenSquareIcon /> :
             <MessageSquareIcon />}
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-[11px] font-medium text-gray-800">{event.action}</p>
            {event.details && <p className="text-[10px] text-gray-500 mt-0.5">{event.details}</p>}
            <p className="text-[9px] text-gray-400 mt-0.5">{event.user} • {formatTime(event.timestamp)}</p>
          </div>
        </div>
      ))}
    </div>
  );
}

// ── Relationships Tab ───────────────────────────────────────────────────────

function RelationshipsTab() {
  return (
    <div className="space-y-2">
      <p className="text-[10px] font-semibold text-gray-500 uppercase mb-2">Related Contracts</p>
      {mockRelatedContracts.map((rc) => (
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

// ── Icon helpers ────────────────────────────────────────────────────────────

const UploadIcon = () => <Upload className="w-3 h-3 text-blue-600" />;
const BrainIcon = () => <Brain className="w-3 h-3 text-purple-600" />;
const FileTextIcon = () => <FileText className="w-3 h-3 text-yellow-600" />;
const CheckIcon = () => <CheckCircle className="w-3 h-3 text-green-600" />;
const PenSquareIcon = () => <PenSquare className="w-3 h-3 text-pink-600" />;
const MessageSquareIcon = () => <MessageSquare className="w-3 h-3 text-gray-600" />;

function Upload({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5" />
    </svg>
  );
}

function formatTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

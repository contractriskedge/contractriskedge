/**
 * MetadataPanel — Enterprise contract metadata sidebar.
 *
 * Features:
 * - Contract details (vendor, dates, type, business unit, geography)
 * - Risk summary with score, level, and breakdown
 * - Workflow state with stage indicator
 * - Obligations list with due dates and status
 * - Renewal dates and auto-renewal status
 * - Related contracts
 * - Document versions
 * - AI confidence score
 * - Tags
 *
 * CON-05: Contract metadata panel
 */

"use client";

import React, { useState } from "react";
import {
  FileText,
  User,
  Calendar,
  Shield,
  DollarSign,
  Clock,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  RefreshCw,
  Link,
  Tag,
  Building2,
  Globe,
  FileType,
  ChevronDown,
  ChevronUp,
  ExternalLink,
  BarChart3,
  BookOpen,
  Download,
} from "lucide-react";
import type { ContractDetail, Obligation, DocumentVersion, AiFinding } from "./types";
import { RISK_BG, RISK_TEXT, RISK_BG_LIGHT } from "@/components/dashboard/contracts/types";
import { formatDate } from "@/lib/date-utils";

// ── Props ───────────────────────────────────────────────────────────────────

interface MetadataPanelProps {
  contract: ContractDetail;
  obligations: Obligation[];
  versions: DocumentVersion[];
  findings: AiFinding[];
}

// ── Severity Colors ─────────────────────────────────────────────────────────

const SEVERITY_COLORS: Record<string, string> = {
  critical: "text-red-600 bg-red-50 dark:bg-red-900/10",
  high: "text-orange-600 bg-orange-50 dark:bg-orange-900/10",
  medium: "text-amber-600 bg-amber-50 dark:bg-amber-900/10",
  low: "text-gray-600 bg-gray-50 dark:bg-gray-800",
};

const OBLIGATION_STATUS: Record<string, { label: string; color: string; bg: string }> = {
  pending: { label: "Pending", color: "text-yellow-700", bg: "bg-yellow-100" },
  in_progress: { label: "In Progress", color: "text-blue-700", bg: "bg-blue-100" },
  completed: { label: "Completed", color: "text-green-700", bg: "bg-green-100" },
  overdue: { label: "Overdue", color: "text-red-700", bg: "bg-red-100" },
};

// ── Component ───────────────────────────────────────────────────────────────

export function MetadataPanel({
  contract,
  obligations,
  versions,
  findings,
}: MetadataPanelProps) {
  const [showAllObligations, setShowAllObligations] = useState(false);
  const [showAllVersions, setShowAllVersions] = useState(false);

  const criticalCount = findings.filter((f) => f.severity === "critical").length;
  const highCount = findings.filter((f) => f.severity === "high").length;
  const openFindings = findings.filter((f) => f.status === "open").length;
  const overdueObligations = obligations.filter((o) => o.status === "overdue").length;
  const displayedObligations = showAllObligations ? obligations : obligations.slice(0, 5);
  const displayedVersions = showAllVersions ? versions : versions.slice(0, 3);

  // ── Risk Score Ring ──────────────────────────────────────────────────

  const RiskScoreRing = ({ score }: { score: number }) => {
    const level = score >= 8 ? "critical" : score >= 6 ? "high" : score >= 4 ? "medium" : "low";
    const colors: Record<string, string> = {
      critical: "text-red-500 stroke-red-500",
      high: "text-orange-500 stroke-orange-500",
      medium: "text-amber-500 stroke-amber-500",
      low: "text-green-500 stroke-green-500",
    };
    const circumference = 2 * Math.PI * 28;
    const offset = circumference - (score / 10) * circumference;

    return (
      <div className="flex flex-col items-center">
        <svg width="72" height="72" viewBox="0 0 72 72" className="transform -rotate-90">
          <circle cx="36" cy="36" r="28" fill="none" stroke="currentColor" strokeWidth="4"
            className="text-gray-100 dark:text-navy-700" />
          <circle cx="36" cy="36" r="28" fill="none" strokeWidth="4"
            strokeLinecap="round"
            className={colors[level]}
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            style={{ transition: "stroke-dashoffset 0.5s ease" }}
          />
        </svg>
        <div className="absolute flex flex-col items-center justify-center">
          <span className={`text-lg font-bold ${colors[level].split(" ")[0]}`}>
            {score}
          </span>
          <span className="text-[8px] text-gray-400 uppercase tracking-wider">/10</span>
        </div>
      </div>
    );
  };

  // ── Section Component ────────────────────────────────────────────────

  const Section = ({
    title,
    icon,
    children,
    defaultOpen = true,
    right,
  }: {
    title: string;
    icon: React.ReactNode;
    children: React.ReactNode;
    defaultOpen?: boolean;
    /** Optional accessory rendered in the header (e.g. completion count). */
    right?: React.ReactNode;
  }) => {
    const [open, setOpen] = useState(defaultOpen);
    return (
      <div className="border-b border-gray-100 dark:border-navy-700">
        <button
          onClick={() => setOpen(!open)}
          className="flex items-center justify-between w-full px-4 py-2.5 hover:bg-gray-50 dark:hover:bg-navy-750 transition-colors"
        >
          <div className="flex items-center gap-1.5">
            <span className="text-gray-400 dark:text-gray-500">{icon}</span>
            <span className="text-[11px] font-semibold text-navy-700 dark:text-navy-200 uppercase tracking-wider">
              {title}
            </span>
            {right}
          </div>
          {open ? (
            <ChevronUp className="w-3 h-3 text-gray-400" />
          ) : (
            <ChevronDown className="w-3 h-3 text-gray-400" />
          )}
        </button>
        {open && <div className="px-4 pb-3">{children}</div>}
      </div>
    );
  };

  /**
   * MetaRow — show a friendly placeholder for blank/empty values so the
   * panel never looks half-finished. The placeholder is visually muted
   * with a dashed underline so the reader can tell at a glance which
   * fields are still pending extraction.
   */
  const PLACEHOLDER = "—";
  const isEmpty = (v: React.ReactNode): boolean => {
    if (v === null || v === undefined) return true;
    if (typeof v === "string") return v.trim() === "" || v === PLACEHOLDER;
    if (typeof v === "number") return false;
    return false;
  };

  const MetaRow = ({
    label,
    value,
    icon,
    placeholder = "Not Extracted",
  }: {
    label: string;
    value: React.ReactNode;
    icon?: React.ReactNode;
    placeholder?: string;
  }) => {
    const empty = isEmpty(value);
    return (
      <div className="flex items-center justify-between py-1">
        <span className="text-[10px] text-gray-500 dark:text-gray-400 flex items-center gap-1">
          {icon}{label}
        </span>
        {empty ? (
          <span
            className="text-[10px] font-medium text-gray-400 dark:text-gray-500 italic border-b border-dashed border-gray-300 dark:border-navy-600"
            title="This field has not been extracted yet"
          >
            {placeholder}
          </span>
        ) : (
          <span className="text-[10px] font-medium text-gray-800 dark:text-gray-200 text-right max-w-[60%] truncate">
            {value}
          </span>
        )}
      </div>
    );
  };

  /**
   * metadataCompletion — count how many of the "expected" fields are
   * populated. Used to render a small "Extraction N/M" badge in the
   * panel header so the user knows at a glance how much metadata is
   * still pending.
   */
  const completionFields: Array<[string, unknown]> = [
    ["vendor", contract.vendor],
    ["counterparty", contract.counterparty],
    ["type", contract.contract_type],
    ["business_unit", contract.business_unit],
    ["geography", contract.geography],
    ["owner", contract.owner],
  ];
  const completionDone = completionFields.filter(([, v]) => !isEmpty(v)).length;
  const completionTotal = completionFields.length;
  );

  return (
    <div className="divide-y divide-gray-100 dark:divide-navy-700">
      {/* ── Risk Score Section ────────────────────────────────────────── */}
      <div className="px-4 py-4 bg-gradient-to-br from-white to-gray-50 dark:from-navy-800 dark:to-navy-850">
        <div className="flex items-center gap-4">
          <div className="relative flex items-center justify-center">
            <RiskScoreRing score={contract.risk_score} />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-xs font-semibold text-navy-900 dark:text-white">
              Risk Score
            </p>
            <p className={`text-[10px] font-medium capitalize ${
              contract.risk_level === "critical" ? "text-red-600" :
              contract.risk_level === "high" ? "text-orange-600" :
              contract.risk_level === "medium" ? "text-amber-600" : "text-green-600"
            }`}>
              {contract.risk_level} risk
            </p>
            <div className="flex items-center gap-2 mt-1.5 text-[9px] text-gray-500 dark:text-gray-400">
              <span className="flex items-center gap-0.5">
                <AlertTriangle className="w-2.5 h-2.5 text-red-400" />
                {criticalCount} critical
              </span>
              <span className="flex items-center gap-0.5">
                <BarChart3 className="w-2.5 h-2.5 text-orange-400" />
                {highCount} high
              </span>
              <span className="flex items-center gap-0.5">
                <Shield className="w-2.5 h-2.5 text-blue-400" />
                {openFindings} open
              </span>
            </div>
          </div>
        </div>
        {/* Confidence */}
        <div className="mt-3 flex items-center gap-2">
          <div className="flex-1 bg-gray-100 dark:bg-navy-700 rounded-full h-1.5">
            <div
              className="bg-navy-500 h-1.5 rounded-full transition-all"
              style={{ width: `${Math.round(contract.confidence_score * 100)}%` }}
            />
          </div>
          <span className="text-[9px] text-gray-500 dark:text-gray-400 whitespace-nowrap">
            {Math.round(contract.confidence_score * 100)}% AI confidence
          </span>
        </div>
      </div>

      {/* ── Contract Details ──────────────────────────────────────────── */}
      <Section
        title="Details"
        icon={<FileText className="w-3.5 h-3.5" />}
        right={
          <span
            className="text-[9px] font-medium text-gray-400 dark:text-gray-500"
            title="How many of the core metadata fields have been extracted"
          >
            Metadata {completionDone}/{completionTotal}
          </span>
        }
      >
        <MetaRow label="Vendor" value={contract.vendor} icon={<Building2 className="w-3 h-3" />} />
        <MetaRow label="Counterparty" value={contract.counterparty} icon={<User className="w-3 h-3" />} />
        <MetaRow label="Type" value={contract.contract_type} icon={<FileType className="w-3 h-3" />} placeholder="Pending Review" />
        <MetaRow label="Business Unit" value={contract.business_unit} />
        <MetaRow label="Geography" value={contract.geography} icon={<Globe className="w-3 h-3" />} />
        <MetaRow label="Owner" value={contract.owner} icon={<User className="w-3 h-3" />} placeholder="Unassigned" />
        <MetaRow label="Status" value={
          <span className={`text-[9px] font-medium px-1.5 py-0.5 rounded-full ${
            contract.status === "active" ? "bg-green-100 text-green-700" :
            contract.status === "expiring_soon" ? "bg-yellow-100 text-yellow-700" :
            contract.status === "expired" ? "bg-red-100 text-red-700" :
            "bg-gray-100 text-gray-600"
          }`}>
            {contract.status.replace(/_/g, " ")}
          </span>
        } />
        <MetaRow label="Workflow" value={
          <span className="text-[9px] font-medium capitalize">
            {contract.workflow_stage ? contract.workflow_stage.replace(/_/g, " ") : "—"}
          </span>
        } />
      </Section>

      {/* ── Financial ─────────────────────────────────────────────────── */}
      <Section title="Financial" icon={<DollarSign className="w-3.5 h-3.5" />}>
        <MetaRow
          label="Value"
          value={contract.financial_value > 0 ? `${contract.currency} ${contract.financial_value.toLocaleString()}` : ""}
          placeholder="Not Available"
        />
        <MetaRow label="Auto-Renewal" value={contract.auto_renew ? "Yes" : "No"} />
        <MetaRow label="Has DPA" value={contract.has_dpa ? "Yes" : "No"} />
      </Section>

      {/* ── Dates ──────────────────────────────────────────────────────── */}
      <Section title="Dates" icon={<Calendar className="w-3.5 h-3.5" />}>
        <MetaRow label="Effective" value={formatDate(contract.effective_date)} icon={<Calendar className="w-3 h-3" />} />
        <MetaRow label="Expiration" value={formatDate(contract.expiration_date)} icon={<Clock className="w-3 h-3" />} />
        <MetaRow label="Renewal" value={formatDate(contract.renewal_date)} icon={<RefreshCw className="w-3 h-3" />} />
        <MetaRow label="Last Activity" value={formatDate(contract.last_activity)} icon={<Clock className="w-3 h-3" />} />
        <MetaRow label="Created" value={formatDate(contract.created_at)} />
      </Section>

      {/* ── AI Summary ────────────────────────────────────────────────── */}
      <Section title="AI Summary" icon={<BookOpen className="w-3.5 h-3.5" />}>
        <p className="text-[11px] text-gray-700 dark:text-gray-300 leading-relaxed">
          {contract.ai_summary}
        </p>
      </Section>

      {/* ── Tags ───────────────────────────────────────────────────────── */}
      {contract.tags.length > 0 && (
        <Section title="Tags" icon={<Tag className="w-3.5 h-3.5" />}>
          <div className="flex flex-wrap gap-1">
            {contract.tags.map((tag) => (
              <span
                key={tag}
                className="text-[9px] px-1.5 py-0.5 rounded-full bg-navy-50 text-navy-700 dark:bg-navy-700 dark:text-navy-200"
              >
                {tag}
              </span>
            ))}
          </div>
        </Section>
      )}

      {/* ── Missing Clauses ────────────────────────────────────────────── */}
      {contract.missing_clauses.length > 0 && (
        <Section title="Missing Clauses" icon={<XCircle className="w-3.5 h-3.5 text-red-400" />}>
          <div className="space-y-1">
            {contract.missing_clauses.map((mc) => (
              <div key={mc} className="flex items-center gap-1.5 text-[10px] text-red-600 dark:text-red-400">
                <XCircle className="w-3 h-3 flex-shrink-0" />
                <span>{mc}</span>
              </div>
            ))}
          </div>
        </Section>
      )}

      {/* ── Obligations ───────────────────────────────────────────────── */}
      <Section title={`Obligations (${obligations.length})`} icon={<CheckCircle2 className="w-3.5 h-3.5" />}>
        {obligations.length === 0 ? (
          <p className="text-[10px] text-gray-400 dark:text-gray-500 italic">No obligations tracked.</p>
        ) : (
          <>
            {overdueObligations > 0 && (
              <div className="flex items-center gap-1 mb-2 px-2 py-1 rounded bg-red-50 dark:bg-red-900/10">
                <AlertTriangle className="w-3 h-3 text-red-500" />
                <span className="text-[10px] font-medium text-red-600 dark:text-red-400">
                  {overdueObligations} overdue obligation{overdueObligations > 1 ? "s" : ""}
                </span>
              </div>
            )}
            <div className="space-y-1.5">
              {displayedObligations.map((ob) => {
                const st = OBLIGATION_STATUS[ob.status] || OBLIGATION_STATUS.pending;
                return (
                  <div key={ob.id} className="flex items-start gap-1.5">
                    <span className={`w-1.5 h-1.5 rounded-full mt-1 flex-shrink-0 ${
                      ob.status === "overdue" ? "bg-red-500" :
                      ob.status === "completed" ? "bg-green-500" :
                      ob.status === "in_progress" ? "bg-blue-500" : "bg-yellow-500"
                    }`} />
                    <div className="flex-1 min-w-0">
                      <p className="text-[10px] text-gray-700 dark:text-gray-300 truncate">{ob.description}</p>
                      <div className="flex items-center gap-1.5 mt-0.5">
                        <span className={`text-[8px] px-1 py-0.5 rounded ${st.bg} ${st.color}`}>{st.label}</span>
                        <span className="text-[8px] text-gray-400">Due: {formatDate(ob.due_date)}</span>
                        <span className="text-[8px] text-gray-400">{ob.owner}</span>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
            {obligations.length > 5 && (
              <button
                onClick={() => setShowAllObligations(!showAllObligations)}
                className="text-[10px] text-blue-600 hover:text-blue-700 dark:text-blue-400 mt-1.5"
              >
                {showAllObligations ? "Show less" : `Show all ${obligations.length}`}
              </button>
            )}
          </>
        )}
      </Section>

      {/* ── Document Versions ──────────────────────────────────────────── */}
      <Section title={`Versions (${versions.length})`} icon={<FileText className="w-3.5 h-3.5" />}>
        {versions.length === 0 ? (
          <p className="text-[10px] text-gray-400 dark:text-gray-500 italic">No version history.</p>
        ) : (
          <div className="space-y-1.5">
            {displayedVersions.map((v) => (
              <div key={v.id} className="flex items-center justify-between py-1">
                <div className="flex items-center gap-1.5">
                  <span className={`w-1.5 h-1.5 rounded-full ${
                    v.status === "current" ? "bg-green-500" :
                    v.status === "finalized" ? "bg-blue-500" : "bg-gray-400"
                  }`} />
                  <div>
                    <p className="text-[10px] font-medium text-gray-700 dark:text-gray-300">
                      v{v.version_number} {v.label && `- ${v.label}`}
                    </p>
                    <p className="text-[8px] text-gray-400">
                      {v.uploaded_by} · {formatDate(v.uploaded_at)}
                    </p>
                  </div>
                </div>
                <button
                  className="p-1 rounded hover:bg-gray-100 dark:hover:bg-navy-700 text-gray-400"
                  aria-label={`Download version ${v.version_number}`}
                  title={`Download v${v.version_number}`}
                >
                  <Download className="w-3 h-3" />
                </button>
              </div>
            ))}
          </div>
        )}
        {versions.length > 3 && (
          <button
            onClick={() => setShowAllVersions(!showAllVersions)}
            className="text-[10px] text-blue-600 hover:text-blue-700 dark:text-blue-400 mt-1.5"
          >
            {showAllVersions ? "Show less" : `Show all ${versions.length} versions`}
          </button>
        )}
      </Section>

      {/* ── AI Flags ───────────────────────────────────────────────────── */}
      {contract.ai_flags.length > 0 && (
        <Section title="AI Flags" icon={<AlertTriangle className="w-3.5 h-3.5 text-amber-400" />}>
          <div className="space-y-1">
            {contract.ai_flags.map((flag) => (
              <div key={flag} className="flex items-center gap-1.5 text-[10px] text-amber-700 dark:text-amber-400">
                <AlertTriangle className="w-3 h-3 flex-shrink-0" />
                <span className="capitalize">{flag.replace(/_/g, " ")}</span>
              </div>
            ))}
          </div>
        </Section>
      )}

      {/* ── Contract ID ────────────────────────────────────────────────── */}
      <div className="px-4 py-2 text-center">
        <p className="text-[8px] text-gray-400 dark:text-gray-500 font-mono">
          ID: {contract.id}
        </p>
      </div>
    </div>
  );
}

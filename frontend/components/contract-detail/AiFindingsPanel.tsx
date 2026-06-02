/**
 * AiFindingsPanel — AI review findings with bidirectional document sync.
 *
 * Features:
 * - Severity-coded findings (critical=red, high=orange, medium=amber, low=gray)
 * - Expandable findings with full description, recommendation, evidence
 * - Confidence score indicators
 * - Clause type badges
 * - Status badges (open, resolved, dismissed, accepted_risk)
 * - Filter by severity, status, clause type
 * - Sort by severity, confidence, date
 * - Bidirectional sync: clicking a finding highlights it in the document
 * - Resolve/dismiss actions with confirmation
 * - Clause deviation comparison view
 * - Remediation recommendations
 *
 * CON-03: AI findings engine integration
 * CON-04: Clause highlighting synchronization
 */

"use client";

import React, { useState, useMemo, useCallback } from "react";
import {
  AlertTriangle,
  ChevronDown,
  ChevronUp,
  CheckCircle2,
  XCircle,
  Filter,
  ArrowUpDown,
  Search,
  BookOpen,
  FileText,
  Lightbulb,
  ExternalLink,
  Shield,
  Info,
  Loader2,
} from "lucide-react";
import { useResolveFinding, useDismissFinding } from "./hooks";
import type { AiFinding, ClauseDeviation } from "./types";

// ── Severity Configuration ──────────────────────────────────────────────────

const SEVERITY_ORDER = ["critical", "high", "medium", "low", "info"];

const SEVERITY_STYLES: Record<string, { bg: string; border: string; dot: string; text: string; label: string }> = {
  critical: {
    bg: "bg-red-50 dark:bg-red-900/10",
    border: "border-red-200 dark:border-red-800",
    dot: "bg-red-500",
    text: "text-red-700 dark:text-red-300",
    label: "Critical",
  },
  high: {
    bg: "bg-orange-50 dark:bg-orange-900/10",
    border: "border-orange-200 dark:border-orange-800",
    dot: "bg-orange-500",
    text: "text-orange-700 dark:text-orange-300",
    label: "High",
  },
  medium: {
    bg: "bg-amber-50 dark:bg-amber-900/10",
    border: "border-amber-200 dark:border-amber-800",
    dot: "bg-amber-500",
    text: "text-amber-700 dark:text-amber-300",
    label: "Medium",
  },
  low: {
    bg: "bg-gray-50 dark:bg-gray-800",
    border: "border-gray-200 dark:border-gray-700",
    dot: "bg-gray-400",
    text: "text-gray-600 dark:text-gray-400",
    label: "Low",
  },
  info: {
    bg: "bg-blue-50 dark:bg-blue-900/10",
    border: "border-blue-200 dark:border-blue-800",
    dot: "bg-blue-400",
    text: "text-blue-700 dark:text-blue-300",
    label: "Info",
  },
};

const STATUS_STYLES: Record<string, { bg: string; text: string }> = {
  open: { bg: "bg-blue-100 dark:bg-blue-900/20", text: "text-blue-700 dark:text-blue-300" },
  resolved: { bg: "bg-green-100 dark:bg-green-900/20", text: "text-green-700 dark:text-green-300" },
  dismissed: { bg: "bg-gray-100 dark:bg-gray-800", text: "text-gray-600 dark:text-gray-400" },
  accepted_risk: { bg: "bg-amber-100 dark:bg-amber-900/20", text: "text-amber-700 dark:text-amber-300" },
};

// ── Props ───────────────────────────────────────────────────────────────────

interface AiFindingsPanelProps {
  findings: AiFinding[];
  clauses: ClauseDeviation[];
  isLoading: boolean;
  selectedFindingId: string | null;
  onFindingSelect: (finding: AiFinding) => void;
  contractId: string;
}

// ── Component ───────────────────────────────────────────────────────────────

export function AiFindingsPanel({
  findings,
  clauses,
  isLoading,
  selectedFindingId,
  onFindingSelect,
  contractId,
}: AiFindingsPanelProps) {
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [severityFilter, setSeverityFilter] = useState<string>("");
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [searchQuery, setSearchQuery] = useState("");
  const [sortField, setSortField] = useState<"severity" | "confidence" | "date">("severity");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");
  const [showFilters, setShowFilters] = useState(false);
  const [showClauseDeviations, setShowClauseDeviations] = useState(false);

  const resolveMutation = useResolveFinding(contractId);
  const dismissMutation = useDismissFinding(contractId);

  // ── Filtered & Sorted Findings ────────────────────────────────────────

  const filteredFindings = useMemo(() => {
    let result = [...findings];

    // Filter by severity
    if (severityFilter) {
      result = result.filter((f) => f.severity === severityFilter);
    }

    // Filter by status
    if (statusFilter) {
      result = result.filter((f) => f.status === statusFilter);
    }

    // Search
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      result = result.filter(
        (f) =>
          f.title.toLowerCase().includes(q) ||
          f.description.toLowerCase().includes(q) ||
          f.clause_type.toLowerCase().includes(q) ||
          f.category.toLowerCase().includes(q)
      );
    }

    // Sort
    result.sort((a, b) => {
      let cmp = 0;
      if (sortField === "severity") {
        cmp = SEVERITY_ORDER.indexOf(a.severity) - SEVERITY_ORDER.indexOf(b.severity);
      } else if (sortField === "confidence") {
        cmp = a.confidence - b.confidence;
      } else if (sortField === "date") {
        cmp = new Date(a.created_at).getTime() - new Date(b.created_at).getTime();
      }
      return sortDir === "desc" ? -cmp : cmp;
    });

    return result;
  }, [findings, severityFilter, statusFilter, searchQuery, sortField, sortDir]);

  // ── Stats ─────────────────────────────────────────────────────────────

  const stats = useMemo(() => {
    return {
      total: findings.length,
      critical: findings.filter((f) => f.severity === "critical").length,
      high: findings.filter((f) => f.severity === "high").length,
      medium: findings.filter((f) => f.severity === "medium").length,
      open: findings.filter((f) => f.status === "open").length,
      resolved: findings.filter((f) => f.status === "resolved").length,
    };
  }, [findings]);

  // ── Handlers ──────────────────────────────────────────────────────────

  const toggleExpand = useCallback((id: string) => {
    setExpandedId((prev) => (prev === id ? null : id));
  }, []);

  const handleResolve = useCallback(
    async (e: React.MouseEvent, findingId: string) => {
      e.stopPropagation();
      try {
        await resolveMutation.mutateAsync(findingId);
      } catch {
        // Error handled by query client
      }
    },
    [resolveMutation]
  );

  const handleDismiss = useCallback(
    async (e: React.MouseEvent, findingId: string) => {
      e.stopPropagation();
      try {
        await dismissMutation.mutateAsync(findingId);
      } catch {
        // Error handled by query client
      }
    },
    [dismissMutation]
  );

  // ── Empty State ───────────────────────────────────────────────────────

  if (!isLoading && findings.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-center p-8">
        <div className="w-16 h-16 rounded-full bg-green-50 dark:bg-green-900/10 flex items-center justify-center mb-4">
          <CheckCircle2 className="w-8 h-8 text-green-400" />
        </div>
        <p className="text-sm font-medium text-gray-700 dark:text-gray-300">No AI findings</p>
        <p className="text-xs text-gray-500 dark:text-gray-400 mt-1 max-w-xs">
          The AI analysis did not detect any risks, deviations, or compliance issues in this contract.
        </p>
      </div>
    );
  }

  // ── Loading State ─────────────────────────────────────────────────────

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <Loader2 className="w-8 h-8 text-navy-400 animate-spin mx-auto mb-3" />
          <p className="text-xs text-gray-500 dark:text-gray-400">Analyzing findings...</p>
        </div>
      </div>
    );
  }

  // ── Render ────────────────────────────────────────────────────────────

  return (
    <div className="flex flex-col h-full">
      {/* ── Stats Bar ─────────────────────────────────────────────────── */}
      <div className="grid grid-cols-5 gap-px bg-gray-100 dark:bg-navy-700">
        {[
          { label: "Total", value: stats.total, color: "text-gray-900 dark:text-white" },
          { label: "Critical", value: stats.critical, color: "text-red-600 dark:text-red-400" },
          { label: "High", value: stats.high, color: "text-orange-600 dark:text-orange-400" },
          { label: "Open", value: stats.open, color: "text-blue-600 dark:text-blue-400" },
          { label: "Resolved", value: stats.resolved, color: "text-green-600 dark:text-green-400" },
        ].map((stat) => (
          <div key={stat.label} className="bg-white dark:bg-navy-800 px-3 py-2 text-center">
            <div className={`text-sm font-bold ${stat.color}`}>{stat.value}</div>
            <div className="text-[9px] text-gray-500 dark:text-gray-400 uppercase tracking-wider">{stat.label}</div>
          </div>
        ))}
      </div>

      {/* ── Search & Filter Bar ───────────────────────────────────────── */}
      <div className="flex items-center gap-2 px-3 py-2 border-b border-gray-100 dark:border-navy-700">
        <div className="relative flex-1">
          <Search className="absolute left-2 top-1/2 -translate-y-1/2 w-3 h-3 text-gray-400" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search findings..."
            className="w-full pl-7 pr-2 py-1 text-[11px] bg-gray-50 dark:bg-navy-700 border border-gray-200 dark:border-navy-600 rounded-md text-navy-900 dark:text-white placeholder-gray-400 focus:outline-none focus:ring-1 focus:ring-navy-400"
          />
        </div>
        <button
          onClick={() => setShowFilters(!showFilters)}
          className={`p-1.5 rounded-md transition-colors ${
            showFilters || severityFilter || statusFilter
              ? "bg-navy-100 text-navy-700 dark:bg-navy-700 dark:text-navy-200"
              : "hover:bg-gray-100 dark:hover:bg-navy-700 text-gray-400"
          }`}
          aria-label="Toggle filters"
          title="Toggle filters"
        >
          <Filter className="w-3.5 h-3.5" />
        </button>
        <button
          onClick={() => {
            setSortDir((prev) => (prev === "desc" ? "asc" : "desc"));
          }}
          className="p-1.5 rounded-md hover:bg-gray-100 dark:hover:bg-navy-700 text-gray-400 transition-colors"
          aria-label={`Sort ${sortDir === "desc" ? "ascending" : "descending"}`}
          title={`Sort ${sortDir === "desc" ? "ascending" : "descending"}`}
        >
          <ArrowUpDown className="w-3.5 h-3.5" />
        </button>
        <button
          onClick={() => setShowClauseDeviations(!showClauseDeviations)}
          className={`p-1.5 rounded-md text-[10px] font-medium transition-colors ${
            showClauseDeviations
              ? "bg-navy-100 text-navy-700 dark:bg-navy-700 dark:text-navy-200"
              : "hover:bg-gray-100 dark:hover:bg-navy-700 text-gray-500"
          }`}
        >
          Deviations ({clauses.length})
        </button>
      </div>

      {/* ── Filter Dropdown ───────────────────────────────────────────── */}
      {showFilters && (
        <div className="flex items-center gap-2 px-3 py-2 bg-gray-50 dark:bg-navy-850 border-b border-gray-100 dark:border-navy-700">
          <select
            value={severityFilter}
            onChange={(e) => setSeverityFilter(e.target.value)}
            className="text-[10px] px-2 py-1 rounded border border-gray-200 dark:border-navy-600 bg-white dark:bg-navy-700 text-navy-900 dark:text-white"
            aria-label="Filter by severity"
          >
            <option value="">All Severities</option>
            <option value="critical">Critical</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
            <option value="info">Info</option>
          </select>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="text-[10px] px-2 py-1 rounded border border-gray-200 dark:border-navy-600 bg-white dark:bg-navy-700 text-navy-900 dark:text-white"
            aria-label="Filter by status"
          >
            <option value="">All Statuses</option>
            <option value="open">Open</option>
            <option value="resolved">Resolved</option>
            <option value="dismissed">Dismissed</option>
            <option value="accepted_risk">Accepted Risk</option>
          </select>
          <select
            value={sortField}
            onChange={(e) => setSortField(e.target.value as "severity" | "confidence" | "date")}
            className="text-[10px] px-2 py-1 rounded border border-gray-200 dark:border-navy-600 bg-white dark:bg-navy-700 text-navy-900 dark:text-white"
            aria-label="Sort by"
          >
            <option value="severity">Severity</option>
            <option value="confidence">Confidence</option>
            <option value="date">Date</option>
          </select>
          {(severityFilter || statusFilter) && (
            <button
              onClick={() => {
                setSeverityFilter("");
                setStatusFilter("");
              }}
              className="text-[10px] text-blue-600 hover:text-blue-700 dark:text-blue-400 ml-auto"
            >
              Clear filters
            </button>
          )}
        </div>
      )}

      {/* ── Clause Deviations Sub-Panel ────────────────────────────────── */}
      {showClauseDeviations && clauses.length > 0 && (
        <div className="border-b border-gray-200 dark:border-navy-700">
          <div className="px-3 py-2 bg-purple-50 dark:bg-purple-900/10">
            <div className="flex items-center gap-1.5 mb-2">
              <FileText className="w-3.5 h-3.5 text-purple-600" />
              <span className="text-[11px] font-semibold text-purple-700 dark:text-purple-300">
                Clause Deviations ({clauses.length})
              </span>
            </div>
            <div className="space-y-1.5 max-h-48 overflow-y-auto">
              {clauses.map((clause) => {
                const style = SEVERITY_STYLES[clause.severity] || SEVERITY_STYLES.medium;
                return (
                  <div
                    key={clause.id}
                    className={`text-[10px] p-2 rounded border ${style.bg} ${style.border}`}
                  >
                    <div className="flex items-center gap-1.5 mb-0.5">
                      <span className={`w-1.5 h-1.5 rounded-full ${style.dot}`} />
                      <span className={`font-semibold ${style.text}`}>{clause.clause_type}</span>
                      <span className="text-gray-400 ml-auto">Page {clause.page_number}</span>
                    </div>
                    <div className="grid grid-cols-2 gap-1 mt-1">
                      <div>
                        <span className="text-gray-400">Expected:</span>
                        <p className="text-gray-600 dark:text-gray-400 truncate">{clause.expected}</p>
                      </div>
                      <div>
                        <span className="text-gray-400">Actual:</span>
                        <p className="text-gray-600 dark:text-gray-400 truncate">{clause.actual}</p>
                      </div>
                    </div>
                    {clause.recommendation && (
                      <div className="flex items-start gap-1 mt-1 pt-1 border-t border-gray-200 dark:border-navy-700">
                        <Lightbulb className="w-2.5 h-2.5 text-amber-500 mt-0.5" />
                        <span className="text-gray-500">{clause.recommendation}</span>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}

      {/* ── Findings List ──────────────────────────────────────────────── */}
      <div className="flex-1 overflow-y-auto">
        {filteredFindings.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 text-center px-4">
            <Search className="w-8 h-8 text-gray-300 dark:text-gray-600 mb-2" />
            <p className="text-xs text-gray-500 dark:text-gray-400">
              {searchQuery ? "No findings match your search." : "No findings match the selected filters."}
            </p>
          </div>
        ) : (
          <div className="divide-y divide-gray-100 dark:divide-navy-700">
            {filteredFindings.map((finding) => {
              const style = SEVERITY_STYLES[finding.severity] || SEVERITY_STYLES.medium;
              const statusStyle = STATUS_STYLES[finding.status] || STATUS_STYLES.open;
              const isExpanded = expandedId === finding.id;
              const isSelected = selectedFindingId === finding.id;

              return (
                <div
                  key={finding.id}
                  className={`transition-colors cursor-pointer ${
                    isSelected ? "ring-2 ring-navy-400 ring-inset" : ""
                  }`}
                  onClick={() => {
                    onFindingSelect(finding);
                    toggleExpand(finding.id);
                  }}
                  role="button"
                  tabIndex={0}
                  aria-expanded={isExpanded}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" || e.key === " ") {
                      e.preventDefault();
                      onFindingSelect(finding);
                      toggleExpand(finding.id);
                    }
                  }}
                >
                  {/* Finding Header */}
                  <div className={`px-4 py-2.5 ${style.bg}`}>
                    <div className="flex items-start gap-2">
                      {/* Severity Dot */}
                      <span className={`w-2 h-2 rounded-full mt-1 flex-shrink-0 ${style.dot}`} />

                      {/* Content */}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-1.5 mb-0.5">
                          <span className={`text-[11px] font-semibold ${style.text}`}>
                            {finding.title}
                          </span>
                          <span className={`text-[9px] px-1.5 py-0.5 rounded-full ${statusStyle.bg} ${statusStyle.text}`}>
                            {finding.status.replace(/_/g, " ")}
                          </span>
                        </div>

                        <div className="flex items-center gap-2 text-[10px] text-gray-500 dark:text-gray-400">
                          <span className={`px-1 py-0.5 rounded text-[9px] font-medium ${style.bg} ${style.text}`}>
                            {finding.clause_type}
                          </span>
                          <span>{finding.category}</span>
                          <span className="flex items-center gap-0.5">
                            <Shield className="w-2.5 h-2.5" />
                            {Math.round(finding.confidence * 100)}%
                          </span>
                          {finding.page_numbers.length > 0 && (
                            <span>Page {finding.page_numbers.join(", ")}</span>
                          )}
                        </div>
                      </div>

                      {/* Expand Icon */}
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          toggleExpand(finding.id);
                        }}
                        className="p-0.5 rounded hover:bg-gray-200 dark:hover:bg-navy-700 text-gray-400 mt-0.5"
                        aria-label={isExpanded ? "Collapse" : "Expand"}
                      >
                        {isExpanded ? (
                          <ChevronUp className="w-3.5 h-3.5" />
                        ) : (
                          <ChevronDown className="w-3.5 h-3.5" />
                        )}
                      </button>
                    </div>
                  </div>

                  {/* Expanded Content */}
                  {isExpanded && (
                    <div className="px-4 py-3 bg-white dark:bg-navy-800 space-y-2.5">
                      {/* Description */}
                      <div>
                        <p className="text-[10px] font-semibold text-gray-500 dark:text-gray-400 uppercase mb-1">
                          Description
                        </p>
                        <p className="text-[11px] text-gray-700 dark:text-gray-300 leading-relaxed">
                          {finding.description}
                        </p>
                      </div>

                      {/* Recommendation */}
                      {finding.recommendation && (
                        <div>
                          <div className="flex items-center gap-1 mb-1">
                            <Lightbulb className="w-3 h-3 text-amber-500" />
                            <p className="text-[10px] font-semibold text-gray-500 dark:text-gray-400 uppercase">
                              Recommendation
                            </p>
                          </div>
                          <p className="text-[11px] text-gray-700 dark:text-gray-300 leading-relaxed">
                            {finding.recommendation}
                          </p>
                        </div>
                      )}

                      {/* Remediation */}
                      {finding.remediation && (
                        <div>
                          <div className="flex items-center gap-1 mb-1">
                            <ExternalLink className="w-3 h-3 text-blue-500" />
                            <p className="text-[10px] font-semibold text-gray-500 dark:text-gray-400 uppercase">
                              Remediation
                            </p>
                          </div>
                          <p className="text-[11px] text-gray-700 dark:text-gray-300 leading-relaxed">
                            {finding.remediation}
                          </p>
                        </div>
                      )}

                      {/* Clause Text */}
                      {finding.clause_text && (
                        <div>
                          <div className="flex items-center gap-1 mb-1">
                            <BookOpen className="w-3 h-3 text-gray-400" />
                            <p className="text-[10px] font-semibold text-gray-500 dark:text-gray-400 uppercase">
                              Clause Text
                            </p>
                          </div>
                          <div className="bg-gray-50 dark:bg-navy-900 rounded p-2">
                            <p className="text-[10px] text-gray-600 dark:text-gray-400 italic leading-relaxed font-mono">
                              &ldquo;{finding.clause_text}&rdquo;
                            </p>
                          </div>
                        </div>
                      )}

                      {/* Action Buttons */}
                      {finding.status === "open" && (
                        <div className="flex items-center gap-2 pt-1">
                          <button
                            onClick={(e) => handleResolve(e, finding.id)}
                            disabled={resolveMutation.isPending}
                            className="flex items-center gap-1 px-2.5 py-1 text-[10px] font-medium rounded-md bg-green-50 text-green-700 hover:bg-green-100 border border-green-200 transition-colors disabled:opacity-50"
                          >
                            <CheckCircle2 className="w-3 h-3" />
                            {resolveMutation.isPending ? "Resolving..." : "Resolve"}
                          </button>
                          <button
                            onClick={(e) => handleDismiss(e, finding.id)}
                            disabled={dismissMutation.isPending}
                            className="flex items-center gap-1 px-2.5 py-1 text-[10px] font-medium rounded-md bg-gray-50 text-gray-600 hover:bg-gray-100 border border-gray-200 transition-colors disabled:opacity-50"
                          >
                            <XCircle className="w-3 h-3" />
                            {dismissMutation.isPending ? "Dismissing..." : "Dismiss"}
                          </button>
                        </div>
                      )}

                      {/* Resolution Info */}
                      {finding.status === "resolved" && finding.resolved_at && (
                        <div className="flex items-center gap-1.5 text-[10px] text-green-600 dark:text-green-400">
                          <CheckCircle2 className="w-3 h-3" />
                          <span>Resolved by {finding.resolved_by || "system"} on {new Date(finding.resolved_at).toLocaleDateString()}</span>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* ── Summary Footer ─────────────────────────────────────────────── */}
      <div className="px-4 py-2 bg-gray-50 dark:bg-navy-850 border-t border-gray-100 dark:border-navy-700">
        <div className="flex items-center justify-between text-[10px] text-gray-500 dark:text-gray-400">
          <span>
            Showing {filteredFindings.length} of {findings.length} findings
          </span>
          <span>
            {stats.open} open · {stats.resolved} resolved
          </span>
        </div>
      </div>
    </div>
  );
}

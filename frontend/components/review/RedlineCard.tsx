/**
 * RedlineCard — collapsible redline card with compact summary and expandable detail.
 *
 * COLLAPSED: One-line compact summary with risk badge, action label, impact, placement
 * EXPANDED: Split diff view, rationale bullets, business impact, related risks, actions
 */

"use client";

import React, { useState, useMemo } from "react";
import {
  ChevronDown, ChevronRight, Shield, AlertTriangle, TrendingDown,
  CheckCircle2, XCircle, Edit3, Lock, FileText, Info, Check, X, RefreshCw,
} from "lucide-react";
import type { RedlineItem } from "@/services/api/client";
import { InlineDiffViewer, CompactSummary } from "./InlineDiffViewer";
import { RedlineActions } from "./RedlineActions";
import { extractChangeSummary } from "@/lib/semanticDiff";

const RISK_GROUP_LABELS: Record<string, { label: string; icon: React.ReactNode; color: string }> = {
  financial: { label: "Financial Risk", icon: <TrendingDown className="h-3.5 w-3.5" />, color: "text-red-600 dark:text-red-400" },
  litigation: { label: "Litigation Risk", icon: <AlertTriangle className="h-3.5 w-3.5" />, color: "text-orange-600 dark:text-orange-400" },
  privacy: { label: "Privacy Risk", icon: <Shield className="h-3.5 w-3.5" />, color: "text-purple-600 dark:text-purple-400" },
  compliance: { label: "Compliance Risk", icon: <FileText className="h-3.5 w-3.5" />, color: "text-blue-600 dark:text-blue-400" },
  vendor_lockin: { label: "Vendor Lock-in Risk", icon: <Lock className="h-3.5 w-3.5" />, color: "text-amber-600 dark:text-amber-400" },
  ip_loss: { label: "IP Risk", icon: <Shield className="h-3.5 w-3.5" />, color: "text-indigo-600 dark:text-indigo-400" },
  security: { label: "Security Risk", icon: <Shield className="h-3.5 w-3.5" />, color: "text-rose-600 dark:text-rose-400" },
  operational: { label: "Operational Risk", icon: <Info className="h-3.5 w-3.5" />, color: "text-sky-600 dark:text-sky-400" },
  reputational: { label: "Reputational Risk", icon: <AlertTriangle className="h-3.5 w-3.5" />, color: "text-pink-600 dark:text-pink-400" },
};

interface RedlineCardProps {
  redline: RedlineItem;
  onLocate?: (redline: RedlineItem) => void;
  onAccept?: (id: string) => void;
  onReject?: (id: string) => void;
  onReopen?: (id: string) => void;
  onEdit?: (redline: RedlineItem) => void;
  onRegenerate?: (redline: RedlineItem) => void;
  immutable?: boolean;
  defaultExpanded?: boolean;
}

export function RedlineCard({ redline, onLocate, onAccept, onReject, onReopen, onEdit, onRegenerate, immutable = false, defaultExpanded = false }: RedlineCardProps) {
  const [expanded, setExpanded] = useState(defaultExpanded);
  const loc = redline.locator;
  const actionLabel = loc?.action_label || (redline.operation === "insert" ? "INSERT" : "MODIFY");
  const summaryImpact = loc?.summary_impact || "";
  const bullets: string[] = loc?.rationale_bullets || [];
  const impactAccepted = loc?.impact_accepted;
  const impactRejected = loc?.impact_rejected;
  const source = redline.source_location;

  // ── Finding-to-Redline category validation ────────────────────
  // Compares the linked finding's clause_type (finding_category) against
  // the redline's own clause_type. If they differ, the mapping is invalid.
  // This prevents e.g. a "Data Privacy" finding from being paired with a
  // "Liability Cap" redline.
  // Handles combined categories (e.g. liability_indemnity matches either).
  const findingCategoryMismatch = useMemo(() => {
    if (!redline.finding_id) return false;
    if (!redline.finding_category && !redline.clause_type) return false;
    // Normalize both categories for comparison
    const fc = (redline.finding_category || "").toLowerCase().replace(/[_-]/g, " ").trim();
    const rc = (redline.clause_type || "").toLowerCase().replace(/[_-]/g, " ").trim();
    if (!fc || !rc) return false;
    // Check for exact match first
    if (fc === rc) return false;
    // Check if one contains the other
    if (fc.includes(rc) || rc.includes(fc)) return false;
    // Check word-level overlap (handles combined categories like liability_indemnity)
    const fcWords = new Set(fc.split(/\s+/).filter(w => w.length > 2));
    const rcWords = new Set(rc.split(/\s+/).filter(w => w.length > 2));
    // If any word overlaps, categories are compatible
    for (const fw of fcWords) {
      for (const rw of rcWords) {
        if (rw.includes(fw) || fw.includes(rw)) return false;
      }
    }
    return true;
  }, [redline.finding_id, redline.finding_category, redline.clause_type]);

  // ── Legacy section-title mismatch detection ────────────────────
  const categoryMismatch = useMemo(() => {
    if (!redline.clause_type || !loc?.section_title) return false;
    const ct = redline.clause_type.toLowerCase().replace(/_/g, " ");
    const st = loc.section_title.toLowerCase();
    const clauseKeywords = ct.split(/[\s_]+/);
    const sectionWords = st.split(/[\s_]+/);
    const hasMatch = clauseKeywords.some(kw =>
      kw.length > 3 && sectionWords.some(sw => sw.includes(kw) || kw.includes(sw))
    );
    return !hasMatch;
  }, [redline.clause_type, loc?.section_title]);

  // Combined: this redline has a mapping integrity issue
  const hasMappingIssue = findingCategoryMismatch || categoryMismatch;

  const originalTextMissing = useMemo(() => {
    const orig = (redline.original_text || "").trim();
    const prop = (redline.proposed_text || "").trim();
    // If original is empty or just a short heading (< 30 chars) while proposed is substantial
    return orig.length < 30 && prop.length > 100 && redline.operation !== "insert";
  }, [redline.original_text, redline.proposed_text, redline.operation]);

  // Row state styling
  const rowStateStyle = redline.status === "accepted" ? "border-l-4 border-l-emerald-500 bg-emerald-50/30 dark:bg-emerald-900/5" :
    redline.status === "rejected" ? "border-l-4 border-l-red-400 bg-red-50/30 dark:bg-red-900/5" :
    redline.status === "modified" ? "border-l-4 border-l-purple-400 bg-purple-50/30 dark:bg-purple-900/5" :
    "";

  const statusIcon = redline.status === "accepted" ? <Check className="h-3 w-3 text-emerald-500" /> :
    redline.status === "rejected" ? <X className="h-3 w-3 text-red-400" /> :
    redline.status === "modified" ? <Edit3 className="h-3 w-3 text-purple-400" /> :
    null;

  const statusLabel = redline.status === "accepted" ? "Accepted" :
    redline.status === "rejected" ? "Rejected" :
    redline.status === "modified" ? "Modified" :
    null;

  const statusColor = redline.status === "accepted" ? "text-emerald-600 dark:text-emerald-400" :
    redline.status === "rejected" ? "text-red-500 dark:text-red-400" :
    redline.status === "modified" ? "text-purple-500 dark:text-purple-400" :
    "";

  return (
    <div className={`rounded-lg border border-gray-200 bg-white shadow-sm transition-all hover:shadow-md dark:border-gray-700 dark:bg-gray-800 ${rowStateStyle}`}>
      <button onClick={() => setExpanded(!expanded)} className="flex w-full items-center gap-2 px-3 py-2 text-left transition-colors hover:bg-gray-50 dark:hover:bg-gray-750">
        <div className="flex-shrink-0">
          {expanded ? <ChevronDown className="h-3 w-3 text-gray-400" /> : <ChevronRight className="h-3 w-3 text-gray-400" />}
        </div>
        <div className="flex-1 min-w-0">
          <CompactSummary
            riskLevel={redline.risk_level}
            actionLabel={actionLabel}
            clauseType={redline.clause_type}
            summaryImpact={summaryImpact || undefined}
            sectionTitle={loc?.section_title || undefined}
            insertPosition={loc?.insert_position || undefined}
            confidence={loc?.confidence}
          />
        </div>
        {/* Review state badge */}
        {statusLabel && (
          <div className={`flex-shrink-0 flex items-center gap-1 text-[10px] font-semibold ${statusColor}`}>
            {statusIcon}
            <span>{statusLabel}</span>
          </div>
        )}
      </button>
      {expanded && (
        <div className="border-t border-gray-100 px-4 py-3 dark:border-gray-700">
          {/* ── Validation Warnings ──────────────────────────────── */}
          {/* Finding-to-Redline category mismatch — CRITICAL: redline doesn't match linked finding */}
          {findingCategoryMismatch && (
            <div className="mb-3 rounded-lg border-2 border-red-400 bg-red-50 px-4 py-4 text-xs text-red-800 dark:border-red-600 dark:bg-red-900/20 dark:text-red-200">
              <div className="flex items-start gap-3">
                <div className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full bg-red-100 dark:bg-red-800">
                  <AlertTriangle className="h-5 w-5 text-red-500" />
                </div>
                <div className="flex-1">
                  <p className="text-sm font-bold text-red-700 dark:text-red-300">INVALID REDLINE MAPPING</p>
                  <p className="mt-1 text-[11px] text-red-600 dark:text-red-400">
                    This redline does not correspond to its linked finding. The remediation category does not match the finding category.
                  </p>
                  <div className="mt-3 grid grid-cols-2 gap-4 rounded-lg border border-red-300 bg-red-50/80 p-3 dark:border-red-700 dark:bg-red-950/30">
                    <div className="rounded-md border border-red-200 bg-white p-2 dark:border-red-700 dark:bg-red-900/20">
                      <p className="text-[9px] font-bold uppercase tracking-wider text-red-600 dark:text-red-400">Finding Category</p>
                      <p className="mt-1 text-sm font-bold text-red-800 dark:text-red-200">{redline.finding_category?.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase()) || "Unknown"}</p>
                      {redline.finding_title && (
                        <p className="mt-0.5 text-[10px] text-red-600 dark:text-red-400">{redline.finding_title}</p>
                      )}
                    </div>
                    <div className="rounded-md border border-red-200 bg-white p-2 dark:border-red-700 dark:bg-red-900/20">
                      <p className="text-[9px] font-bold uppercase tracking-wider text-red-600 dark:text-red-400">Redline Category</p>
                      <p className="mt-1 text-sm font-bold text-red-800 dark:text-red-200">{redline.clause_type?.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase()) || "Unknown"}</p>
                      <p className="mt-0.5 text-[10px] font-semibold text-red-500 dark:text-red-400">✗ Does not match finding</p>
                    </div>
                  </div>
                  <div className="mt-3 rounded-md border border-amber-300 bg-amber-50 p-2 dark:border-amber-700 dark:bg-amber-900/20">
                    <p className="text-[10px] font-semibold text-amber-700 dark:text-amber-300">Reason: Category mismatch</p>
                    <p className="mt-0.5 text-[10px] text-amber-600 dark:text-amber-400">
                      Accept and Reject are disabled. Use <strong>Regenerate Redline</strong> below to create a correctly-categorized redline using the finding category as a mandatory filter.
                    </p>
                  </div>
                </div>
              </div>
            </div>
          )}
          {/* Section-title mismatch — less severe, but still flagged */}
          {!findingCategoryMismatch && categoryMismatch && (
            <div className="mb-3 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800 dark:border-amber-700 dark:bg-amber-900/20 dark:text-amber-200">
              <p className="font-semibold">⚠ Possible mapping error detected</p>
              <p className="mt-0.5">
                Source Clause = <span className="font-medium">{loc?.section_title || "unknown"}</span> · 
                Generated Clause = <span className="font-medium">{redline.clause_type?.replace(/_/g, " ") || "unknown"}</span>
              </p>
              <p className="mt-0.5 text-amber-600 dark:text-amber-400">
                The clause category doesn&apos;t match the document section. Verify before accepting.
              </p>
            </div>
          )}
          {originalTextMissing && (
            <div className="mb-3 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800 dark:border-amber-700 dark:bg-amber-900/20 dark:text-amber-200">
              <p className="font-semibold">⚠ Original clause text is missing or only shows a section heading</p>
              <p className="mt-0.5">
                Use <span className="font-medium">View Source Location</span> to verify the baseline in the document viewer.
              </p>
              <p className="mt-0.5 text-amber-600 dark:text-amber-400">
                Possible mapping error — verify before accepting.
              </p>
            </div>
          )}

          <div className="mb-3 rounded-lg border border-blue-200 bg-blue-50/40 p-3 dark:border-blue-800 dark:bg-blue-900/10">
            <p className="text-[10px] font-semibold uppercase tracking-wider text-blue-700 dark:text-blue-300">
              Source Location
            </p>
            {source ? (
              <>
                <div className="mt-2 grid grid-cols-2 gap-2 text-xs text-gray-600 dark:text-gray-300 sm:grid-cols-4">
                  <span>Page: <span className="font-semibold">{source.page_number ?? "—"}</span></span>
                  <span>Section: <span className="font-semibold">{source.section_heading || loc?.section_title || "—"}</span></span>
                  <span>Paragraph: <span className="font-semibold">{source.paragraph_index ?? "—"}</span></span>
                  <span>Confidence: <span className="font-semibold">{source.confidence_score == null ? "—" : `${Math.round(source.confidence_score * 100)}%`}</span></span>
                </div>
                {source.source_text && (
                  <p className="mt-2 text-xs leading-relaxed text-gray-700 dark:text-gray-300">
                    {source.source_text.slice(0, 240)}{source.source_text.length > 240 ? "..." : ""}
                  </p>
                )}
                {onLocate && (
                  <button
                    title="Navigate to the contract text that generated this finding."
                    onClick={() => onLocate(redline)}
                    className="mt-2 inline-flex items-center gap-1.5 rounded-md bg-blue-100 px-3 py-1.5 text-xs font-medium text-blue-700 transition-colors hover:bg-blue-200 dark:bg-blue-900/30 dark:text-blue-300 dark:hover:bg-blue-800"
                  >
                    <FileText className="h-3.5 w-3.5" /> View Source Location
                  </button>
                )}
              </>
            ) : (
              <p className="mt-2 text-xs text-gray-500 dark:text-gray-400">
                Source location unavailable. Finding generated from document-level analysis.
              </p>
            )}
          </div>

          <div className="mb-3 rounded-lg border border-gray-200 bg-gray-50/50 p-3 dark:border-gray-700 dark:bg-gray-800/40">
            <p className="text-[10px] font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400">
              Traceability Chain
            </p>
            <div className="mt-2 space-y-1.5 text-xs text-gray-700 dark:text-gray-300">
              <p><span className="font-semibold">Source Clause:</span> {source?.source_text ? `${source.source_text.slice(0, 180)}${source.source_text.length > 180 ? "..." : ""}` : "Document-level analysis"}</p>
              <p className="text-gray-400">↓</p>
              <p><span className="font-semibold">AI Finding:</span> {redline.traceability?.detected_risk || redline.rationale || redline.clause_type?.replace(/_/g, " ") || "Linked finding"}</p>
              <p className="text-gray-400">↓</p>
              <p><span className="font-semibold">Policy Match:</span> {loc?.risk_type || loc?.legal_domain || redline.clause_type?.replace(/_/g, " ") || "Review policy"}</p>
              <p className="text-gray-400">↓</p>
              <p><span className="font-semibold">Generated Redline:</span> {extractChangeSummary(redline.original_text, redline.reviewer_modified_text || redline.proposed_text, redline.operation || undefined)}</p>
            </div>
          </div>

          {(redline.original_text || redline.proposed_text) && (
            <div className="mb-3">
              <InlineDiffViewer
                original={redline.original_text}
                proposed={redline.proposed_text}
                aiProposedText={redline.ai_proposed_text}
                reviewerModifiedText={redline.reviewer_modified_text}
                isModified={redline.status === "modified"}
                reviewedBy={redline.reviewed_by}
                mode="inline"
              />
            </div>
          )}
          {/* Change summary — one-line legal summary of what changed */}
          {(redline.original_text || redline.proposed_text) && (
            <div className="mb-3 rounded-lg border border-gray-100 bg-gray-50/50 px-3 py-2 dark:border-gray-700 dark:bg-gray-800/30">
              <p className="text-[9px] font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400 mb-0.5">
                Change Summary
              </p>
              <p className="text-xs text-gray-700 dark:text-gray-300">
                {extractChangeSummary(
                  redline.original_text,
                  redline.reviewer_modified_text || redline.proposed_text,
                  redline.operation || undefined,
                )}
              </p>
            </div>
          )}
          {bullets.length > 0 && (
            <div className="mb-3">
              <p className="text-[10px] font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400 mb-1.5">Why This Matters</p>
              <ul className="space-y-1">
                {bullets.map((bullet, i) => (
                  <li key={i} className="flex items-start gap-2 text-xs text-gray-700 dark:text-gray-300">
                    <span className="mt-1.5 h-1 w-1 flex-shrink-0 rounded-full bg-emerald-500" />
                    {bullet}
                  </li>
                ))}
              </ul>
            </div>
          )}
          {(impactAccepted || impactRejected) && (
            <div className="mb-3">
              <p className="text-[10px] font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400 mb-1.5">Risk If Rejected</p>
              <div className="rounded-lg border border-red-200 bg-red-50/50 p-2.5 dark:border-red-800 dark:bg-red-900/10">
                <p className="text-xs text-gray-600 dark:text-gray-300">{impactRejected || impactAccepted}</p>
              </div>
            </div>
          )}
          {loc?.related_risks && loc.related_risks.length > 0 && (
            <div className="mb-3">
              <p className="text-[10px] font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400 mb-1">Related Risks</p>
              <div className="flex flex-wrap gap-1.5">
                {loc.related_risks.map((risk: string) => {
                  const group = RISK_GROUP_LABELS[risk] || { label: risk, icon: null, color: "text-gray-500" };
                  return (
                    <span key={risk} className={`inline-flex items-center gap-1 rounded-full bg-gray-100 px-2 py-0.5 text-[10px] font-medium dark:bg-gray-700 ${group.color}`}>
                      {group.icon}{group.label}
                    </span>
                  );
                })}
              </div>
            </div>
          )}
          <div className="mb-3 flex flex-wrap gap-3 text-[11px] text-gray-500 dark:text-gray-400">
            {redline.clause_type && <span>Type: <span className="font-medium text-gray-700 dark:text-gray-300">{redline.clause_type}</span></span>}
            {loc?.legal_domain && <span>Domain: <span className="font-medium text-gray-700 dark:text-gray-300">{loc.legal_domain}</span></span>}
            {loc?.risk_type && <span>Risk: <span className="font-medium text-gray-700 dark:text-gray-300">{loc.risk_type}</span></span>}
          </div>
          {redline.rationale && bullets.length === 0 && (
            <div className="mb-3 rounded-lg bg-gray-50 p-2.5 dark:bg-gray-700/50">
              <p className="text-[10px] font-semibold text-gray-500 dark:text-gray-400 mb-1">Rationale</p>
              <p className="text-xs text-gray-600 dark:text-gray-300">{redline.rationale}</p>
            </div>
          )}
          {/* Show actions for proposed and invalid_mapping redlines.
              For invalid_mapping: Accept is now allowed (backend bypasses mapping validation),
              Reopen resets to proposed, and Regenerate re-links to the correct finding. */}
          {(redline.status === "proposed" || redline.status === "invalid_mapping") && !immutable && (
            <RedlineActions
              redline={redline}
              findingCategoryMismatch={findingCategoryMismatch}
              onAccept={onAccept}
              onReject={onReject}
              onReopen={onReopen}
              onEdit={onEdit}
              onRegenerate={onRegenerate}
            />
          )}
          {/* Show only Reopen for rejected redlines */}
          {redline.status === "rejected" && !immutable && (
            <RedlineActions
              redline={redline}
              findingCategoryMismatch={findingCategoryMismatch}
              onReopen={onReopen}
            />
          )}
          {redline.status === "proposed" && immutable && (
            <div className="mt-3 flex items-center gap-2 rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 dark:border-gray-700 dark:bg-gray-800">
              <Lock className="h-3.5 w-3.5 text-gray-400" />
              <span className="text-xs text-gray-500 dark:text-gray-400">Redlines are locked</span>
            </div>
          )}
          {/* Mitigation traceability — shown for mitigation-generated redlines */}
          {redline.traceability?.generated_from === "mitigation_recommendation" && (
            <div className="mb-3 rounded-lg border border-emerald-200 bg-emerald-50/60 p-3 dark:border-emerald-800 dark:bg-emerald-900/10">
              <p className="text-[10px] font-semibold uppercase tracking-wider text-emerald-600 dark:text-emerald-400 mb-1.5">
                Generated from Mitigation
              </p>
              <div className="space-y-1 text-[11px]">
                {redline.traceability.mitigation_strategy && (
                  <div className="flex items-center gap-1.5">
                    <Shield className="w-3 h-3 text-emerald-500 flex-shrink-0" />
                    <span className="text-gray-700 dark:text-gray-300">
                      {redline.traceability.mitigation_strategy}
                    </span>
                  </div>
                )}
                {redline.traceability.estimated_reduction_pct != null && (
                  <div className="flex items-center gap-1.5">
                    <TrendingDown className="w-3 h-3 text-green-500 flex-shrink-0" />
                    <span className="text-gray-700 dark:text-gray-300">
                      Estimated reduction: <span className="font-semibold text-green-600 dark:text-green-400">−{Math.round(redline.traceability.estimated_reduction_pct * 100)}%</span>
                    </span>
                  </div>
                )}
                {redline.traceability.confidence != null && (
                  <div className="flex items-center gap-1.5">
                    <Shield className="w-3 h-3 text-indigo-500 flex-shrink-0" />
                    <span className="text-gray-700 dark:text-gray-300">
                      Confidence: <span className="font-semibold">{Math.round(redline.traceability.confidence * 100)}%</span>
                      {redline.traceability.source && (
                        <> · <span className="text-gray-500">{redline.traceability.source.replace(/_/g, " ")}</span></>
                      )}
                    </span>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* ── Reviewer Metadata ──────────────────────────────── */}
          {(redline.created_at || redline.reviewed_at || redline.reviewed_by) && (
            <div className="mt-3 rounded-lg border border-gray-100 bg-gray-50/50 p-3 dark:border-gray-700 dark:bg-gray-800/30">
              <p className="text-[10px] font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400 mb-2">
                Review Metadata
              </p>
              <div className="grid grid-cols-2 gap-2 text-[11px] text-gray-600 dark:text-gray-300">
                {redline.created_at && (
                  <div>
                    <span className="text-gray-400">Generated:</span>{' '}
                    <span className="font-medium">{new Date(redline.created_at).toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}</span>
                  </div>
                )}
                {redline.reviewed_at && (
                  <div>
                    <span className="text-gray-400">Last Updated:</span>{' '}
                    <span className="font-medium">{new Date(redline.reviewed_at).toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}</span>
                  </div>
                )}
                {redline.reviewed_by && (
                  <div>
                    <span className="text-gray-400">Reviewed By:</span>{' '}
                    <span className="font-medium">{redline.reviewed_by}</span>
                  </div>
                )}
                {redline.status === "proposed" && (
                  <div>
                    <span className="text-gray-400">Generated By:</span>{' '}
                    <span className="font-medium">AI System</span>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

interface RiskGroupHeaderProps {
  groupKey: string;
  count: number;
}

export function RiskGroupHeader({ groupKey, count }: RiskGroupHeaderProps) {
  const group = RISK_GROUP_LABELS[groupKey] || {
    label: groupKey.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()),
    icon: <Info className="h-3.5 w-3.5" />,
    color: "text-gray-500 dark:text-gray-400",
  };
  return (
    <div className="flex items-center gap-2 px-1 py-2">
      <span className={group.color}>{group.icon}</span>
      <h3 className={`text-sm font-semibold ${group.color}`}>{group.label}</h3>
      <span className="ml-auto inline-flex items-center justify-center rounded-full bg-gray-100 px-2 py-0.5 text-[11px] font-medium text-gray-500 dark:bg-gray-700 dark:text-gray-400">{count}</span>
    </div>
  );
}

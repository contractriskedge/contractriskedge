"use client";

import React, { useState } from "react";
import {
  FileText, Scale, Lightbulb, BookOpen, MessageSquare,
  AlertTriangle, TrendingUp, BarChart3, Link as LinkIcon,
  Globe, Gavel, Shield
} from "lucide-react";
import type { ClauseSuggestion, DiffViewMode, RiskFlagDetail } from "./types";
import { DiffView } from "./DiffView";
import { ConfidenceBar } from "./ConfidenceBar";
import { RiskBadge } from "./RiskBadge";
import { CorporatePlaybookCard } from "./CorporatePlaybookCard";
import { ActionBar } from "./ActionBar";
import { CollaborationPanel } from "./CollaborationPanel";

// ── Props ────────────────────────────────────────────────────────────────────

interface DetailViewProps {
  suggestion: ClauseSuggestion | null;
  riskFlag: RiskFlagDetail | null;
  onAccept: (id: string) => void;
  onReject: (id: string) => void;
  onEscalate: (id: string, reason: string) => void;
  onAddComment: (id: string) => void;
  onExportDocx: (id: string) => void;
  onExportPdf: (id: string) => void;
  onAddSuggestionComment: (suggestionId: string, body: string, mentions: string[]) => void;
  onResolveSuggestionComment: (suggestionId: string, commentId: string) => void;
  actionLoading: string | null;
}

// ── Component ────────────────────────────────────────────────────────────────

export function DetailView({
  suggestion,
  riskFlag,
  onAccept,
  onReject,
  onEscalate,
  onAddComment,
  onExportDocx,
  onExportPdf,
  onAddSuggestionComment,
  onResolveSuggestionComment,
  actionLoading,
}: DetailViewProps) {
  const [diffMode, setDiffMode] = useState<DiffViewMode>("side-by-side");
  const [collabOpen, setCollabOpen] = useState(false);

  // ── Empty state ──
  if (!suggestion && !riskFlag) {
    return (
      <div className="flex flex-col items-center justify-center h-full py-16 text-gray-400 bg-white rounded-xl border border-gray-200 shadow-sm">
        <Scale className="w-14 h-14 mb-4 text-gray-300" />
        <p className="text-base font-semibold text-gray-500">Select a suggestion to review</p>
        <p className="text-sm mt-1 text-gray-400 max-w-sm text-center">
          Choose a redline suggestion or risk flag from the list to view its detailed analysis, diff comparison, and playbook guidance.
        </p>
      </div>
    );
  }

  // ── Risk Flag Detail ──
  if (riskFlag) {
    return (
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
        <div className="p-5 space-y-4 overflow-y-auto max-h-[calc(100vh-12rem)]">
          {/* Header */}
          <div className="flex items-start justify-between">
            <div>
              <h2 className="text-base font-semibold text-navy-900">8-Field Risk Analysis</h2>
              <p className="text-xs text-gray-500 mt-0.5 capitalize flex items-center gap-2">
                <span>Category: {riskFlag.risk_category?.replace(/_/g, " ")}</span>
                <RiskBadge level={riskFlag.riskLevel || "medium"} size="sm" />
              </p>
            </div>
            <div className="flex items-center gap-2">
              <span className={`text-xs font-medium px-2 py-1 rounded-full border ${
                (riskFlag.confidence_score || 0) >= 0.7 ? "bg-green-50 text-green-700 border-green-200" :
                (riskFlag.confidence_score || 0) >= 0.4 ? "bg-yellow-50 text-yellow-700 border-yellow-200" :
                "bg-red-50 text-red-700 border-red-200"
              }`}>
                {riskFlag.confidence_label || "Unknown"}
              </span>
            </div>
          </div>

          {/* Field 1: Clause Text */}
          <Section icon={<FileText className="w-4 h-4 text-navy-600" />} title="1. Clause Text" color="gray">
            <p className="text-sm text-gray-700 leading-relaxed">{riskFlag.clause_text}</p>
          </Section>

          {/* Field 2: Risk Category + Severity */}
          <Section icon={<AlertTriangle className="w-4 h-4 text-navy-600" />} title="2. Risk Category & Severity" color="gray">
            <p className="text-sm font-medium text-gray-700 capitalize mb-2">
              {riskFlag.risk_category?.replace(/_/g, " ")}
            </p>
            {riskFlag.severity && (
              <div className="flex items-center gap-2">
                <span className="text-xs text-gray-500">Severity:</span>
                <div className="flex gap-0.5">
                  {[1,2,3,4,5,6,7,8,9,10].map((s) => (
                    <div key={s} className={`w-2 h-4 rounded-sm ${
                      s <= (riskFlag.severity?.severity_score || 0)
                        ? (riskFlag.severity?.severity_score || 0) >= 7 ? "bg-red-500"
                          : (riskFlag.severity?.severity_score || 0) >= 4 ? "bg-yellow-500" : "bg-green-500"
                        : "bg-gray-200"
                    }`} />
                  ))}
                </div>
                <span className="text-xs font-medium">{riskFlag.severity?.severity_score}/10</span>
              </div>
            )}
          </Section>

          {/* Field 3: Why Flagged */}
          <Section icon={<AlertTriangle className="w-4 h-4 text-red-600" />} title="3. Why Flagged" color="red">
            <p className="text-sm text-gray-700 leading-relaxed">{riskFlag.why_flagged || "No explanation provided."}</p>
          </Section>

          {/* Field 4: Business Impact */}
          <Section icon={<TrendingUp className="w-4 h-4 text-orange-600" />} title="4. Potential Business Impact" color="orange">
            <p className="text-sm text-gray-700 leading-relaxed">{riskFlag.potential_business_impact || "No assessment."}</p>
          </Section>

          {/* Field 5: Market Benchmark */}
          <Section icon={<BarChart3 className="w-4 h-4 text-blue-600" />} title="5. Market Benchmark Comparison" color="blue">
            <p className="text-sm text-gray-700 leading-relaxed">{riskFlag.market_benchmark_comparison || "No comparison."}</p>
          </Section>

          {/* Field 6: Confidence */}
          <Section icon={<Shield className="w-4 h-4 text-purple-600" />} title="6. Confidence Score" color="purple">
            <ConfidenceBar score={riskFlag.confidence_score || 0} size="md" />
            <p className="text-xs text-gray-500 mt-1">
              Label: <span className="font-medium capitalize">{riskFlag.confidence_label || "unknown"}</span>
            </p>
          </Section>

          {/* Field 7: Suggested Remediation */}
          <Section icon={<Lightbulb className="w-4 h-4 text-green-600" />} title="7. Suggested Remediation" color="green">
            <p className="text-sm text-gray-700 leading-relaxed">{riskFlag.suggested_remediation || "No remediation."}</p>
          </Section>

          {/* Field 8: Linked Evidence */}
          <Section icon={<LinkIcon className="w-4 h-4 text-indigo-600" />} title="8. Linked Evidence" color="indigo">
            {riskFlag.linked_evidence && riskFlag.linked_evidence.length > 0 ? (
              <div className="space-y-2">
                {riskFlag.linked_evidence.map((ev, i) => (
                  <div key={i} className="p-3 bg-white rounded border border-indigo-100">
                    <p className="text-xs font-medium text-indigo-700 mb-1">{ev.clause_reference}</p>
                    <p className="text-xs text-gray-600 italic">&ldquo;{ev.excerpt}&rdquo;</p>
                    <div className="flex items-center gap-2 mt-1">
                      <span className="text-[10px] text-gray-400">Relevance: {Math.round(ev.relevance_score * 100)}%</span>
                      {ev.section && <span className="text-[10px] text-gray-400">Section: {ev.section}</span>}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-gray-500">No linked evidence available.</p>
            )}
          </Section>

          {/* Field 9: Jurisdictional */}
          <Section icon={<Globe className="w-4 h-4 text-teal-600" />} title="9. Jurisdictional Considerations" color="teal">
            {riskFlag.jurisdictional_considerations && riskFlag.jurisdictional_considerations.length > 0 ? (
              <div className="space-y-2">
                {riskFlag.jurisdictional_considerations.map((jc, i) => (
                  <div key={i} className="flex items-start gap-2 p-2 bg-white rounded border border-teal-100">
                    <Gavel className="w-3 h-3 text-teal-500 mt-0.5 flex-shrink-0" />
                    <div>
                      <p className="text-xs font-medium text-teal-700">{jc.jurisdiction} — {jc.rule_reference}</p>
                      <p className="text-xs text-gray-600 mt-0.5">{jc.explanation}</p>
                      <span className={`text-[10px] font-medium ${jc.risk_modifier > 0 ? "text-red-500" : "text-green-500"}`}>
                        Risk modifier: {jc.risk_modifier > 0 ? "+" : ""}{jc.risk_modifier}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-gray-500">No jurisdiction-specific considerations.</p>
            )}
          </Section>
        </div>
      </div>
    );
  }

  // ── Redline Suggestion Detail ──
  if (!suggestion) return null;

  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden flex flex-col h-full">
      {/* Scrollable content */}
      <div className="flex-1 overflow-y-auto p-5 space-y-4">
        {/* Header */}
        <div className="flex items-start justify-between">
          <div>
            <h2 className="text-base font-semibold text-navy-900">Redline Detail</h2>
            <p className="text-xs text-gray-500 mt-0.5 flex items-center gap-1">
              <FileText className="w-3 h-3" />
              {suggestion.contractName || suggestion.contractId.slice(0, 30) + "…"}
            </p>
          </div>
          <RiskBadge level={suggestion.riskLevel} size="md" />
        </div>

        {/* Metadata grid */}
        <div className="grid grid-cols-3 gap-3 p-3 bg-gray-50 rounded-lg border border-gray-100">
          <div>
            <p className="text-[10px] text-gray-500 font-medium uppercase tracking-wider">Clause Type</p>
            <p className="text-xs font-medium text-gray-700 capitalize mt-0.5">
              {suggestion.clauseType.replace(/_/g, " ")}
            </p>
          </div>
          <div>
            <p className="text-[10px] text-gray-500 font-medium uppercase tracking-wider">Change Type</p>
            <p className="text-xs font-medium text-gray-700 capitalize mt-0.5">{suggestion.changeType}</p>
          </div>
          <div>
            <p className="text-[10px] text-gray-500 font-medium uppercase tracking-wider">Severity</p>
            <p className="text-xs font-medium text-gray-700 mt-0.5">
              {suggestion.severityScore}/10
            </p>
          </div>
          <div>
            <p className="text-[10px] text-gray-500 font-medium uppercase tracking-wider">Confidence</p>
            <div className="mt-0.5 max-w-[120px]">
              <ConfidenceBar score={suggestion.confidence} size="sm" />
            </div>
          </div>
          <div>
            <p className="text-[10px] text-gray-500 font-medium uppercase tracking-wider">Section</p>
            <p className="text-xs font-medium text-gray-700 mt-0.5">{suggestion.section || "—"}</p>
          </div>
          <div>
            <p className="text-[10px] text-gray-500 font-medium uppercase tracking-wider">Page</p>
            <p className="text-xs font-medium text-gray-700 mt-0.5">{suggestion.pageNumber || "—"}</p>
          </div>
        </div>

        {/* Diff View */}
        <DiffView
          originalText={suggestion.originalText}
          proposedText={suggestion.proposedText}
          mode={diffMode}
          onModeChange={setDiffMode}
        />

        {/* Rationale */}
        <div className="p-3 bg-navy-50 rounded-lg border border-navy-100">
          <div className="flex items-center gap-2 mb-1.5">
            <Lightbulb className="w-4 h-4 text-navy-600" />
            <span className="text-[11px] font-semibold text-navy-700 uppercase tracking-wider">Rationale</span>
          </div>
          <p className="text-sm text-gray-700 leading-relaxed">{suggestion.rationale}</p>
        </div>

        {/* Corporate Playbook */}
        {suggestion.playbook && (
          <CorporatePlaybookCard playbook={suggestion.playbook} />
        )}
      </div>

      {/* Action Bar + Collaboration (sticky bottom) */}
      <div className="border-t border-gray-200 p-4 bg-white space-y-3">
        <div className="flex items-center justify-between">
          <ActionBar
            suggestionId={suggestion.suggestionId}
            status={suggestion.status}
            onAccept={onAccept}
            onReject={onReject}
            onEscalate={onEscalate}
            onAddComment={() => setCollabOpen(true)}
            onExportDocx={onExportDocx}
            onExportPdf={onExportPdf}
            actionLoading={actionLoading}
          />
          <CollaborationPanel
            comments={suggestion.comments}
            onAddComment={(body, mentions) => onAddSuggestionComment(suggestion.suggestionId, body, mentions)}
            onResolveComment={(commentId) => onResolveSuggestionComment(suggestion.suggestionId, commentId)}
            isOpen={collabOpen}
            onToggle={() => setCollabOpen(!collabOpen)}
          />
        </div>
      </div>
    </div>
  );
}

// ── Section Sub-Component ───────────────────────────────────────────────────

function Section({
  icon,
  title,
  color,
  children,
}: {
  icon: React.ReactNode;
  title: string;
  color: "gray" | "red" | "orange" | "blue" | "purple" | "green" | "indigo" | "teal";
  children: React.ReactNode;
}) {
  const bgMap: Record<string, string> = {
    gray: "bg-gray-50 border-gray-200",
    red: "bg-red-50 border-red-100",
    orange: "bg-orange-50 border-orange-100",
    blue: "bg-blue-50 border-blue-100",
    purple: "bg-purple-50 border-purple-100",
    green: "bg-green-50 border-green-100",
    indigo: "bg-indigo-50 border-indigo-100",
    teal: "bg-teal-50 border-teal-100",
  };

  return (
    <div className={`p-3 rounded-lg border ${bgMap[color]}`}>
      <div className="flex items-center gap-2 mb-1.5">
        {icon}
        <span className="text-[11px] font-semibold uppercase tracking-wider">{title}</span>
      </div>
      {children}
    </div>
  );
}

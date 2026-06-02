"use client";

import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  X, FileText, AlertTriangle, TrendingUp, BarChart3, BookOpen,
  Brain, MessageSquare, User, Clock, CheckCircle, Copy, Sparkles,
  Shield, ChevronDown, ChevronRight, GitBranch, Star,
} from "lucide-react";
import type {
  ClauseContent, RedlineEntry, AiNegotiationInsight,
  NegotiationPlaybook, CommentItem, FallbackClause,
} from "./types";

// ── Negotiation Clause Detail Drawer ──────────────────────────────────────

interface ClauseDrawerProps {
  clause: ClauseContent | null;
  originalText: string;
  modifiedText: string;
  redlines: RedlineEntry[];
  insights: AiNegotiationInsight[];
  playbooks: NegotiationPlaybook[];
  comments: CommentItem[];
  isOpen: boolean;
  onClose: () => void;
  onApplyFallback: (fb: FallbackClause) => void;
}

type DrawerTab = "overview" | "redlines" | "playbook" | "ai" | "comments";

export function NegotiationClauseDrawer({
  clause, originalText, modifiedText, redlines, insights,
  playbooks, comments, isOpen, onClose, onApplyFallback,
}: ClauseDrawerProps) {
  const [tab, setTab] = useState<DrawerTab>("overview");

  if (!clause) return null;

  const clausePlaybooks = playbooks.filter(p => p.clauseCategory === clause.category);
  const clauseInsights = insights.filter(i => i.clauseId === clause.clauseId);
  const clauseRedlines = redlines.filter(r => r.clauseId === clause.clauseId);

  const riskColor = clause.riskLevel === "critical" ? "text-red-600 bg-red-50" :
    clause.riskLevel === "high" ? "text-orange-600 bg-orange-50" :
    clause.riskLevel === "medium" ? "text-yellow-600 bg-yellow-50" :
    "text-green-600 bg-green-50";

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/20 z-40"
            onClick={onClose}
          />
          <motion.div
            initial={{ x: "100%" }}
            animate={{ x: 0 }}
            exit={{ x: "100%" }}
            transition={{ type: "spring", damping: 25, stiffness: 200 }}
            className="fixed right-0 top-0 bottom-0 w-[520px] bg-white dark:bg-navy-800 border-l border-gray-200 dark:border-navy-700 shadow-2xl z-50 flex flex-col"
          >
            {/* Header */}
            <div className="px-5 py-4 border-b border-gray-200 dark:border-navy-700 flex items-center justify-between">
              <div className="flex items-center gap-2 min-w-0">
                <div className="w-8 h-8 rounded-lg bg-navy-700 flex items-center justify-center">
                  <FileText className="w-4 h-4 text-white" />
                </div>
                <div className="min-w-0">
                  <h3 className="text-sm font-semibold text-navy-900 dark:text-white truncate">{clause.title}</h3>
                  <p className="text-[10px] text-gray-500">{clause.sectionNumber} &middot; {clause.category.replace(/_/g, " ")}</p>
                </div>
              </div>
              <button onClick={onClose} className="p-1 rounded hover:bg-gray-100 dark:hover:bg-navy-700 text-gray-400 transition-colors">
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Tabs */}
            <div className="px-4 py-2 border-b border-gray-100 dark:border-navy-700 flex gap-1 overflow-x-auto">
              {[
                { id: "overview" as const, label: "Overview", icon: <FileText className="w-3 h-3" /> },
                { id: "redlines" as const, label: `Redlines (${clauseRedlines.length})`, icon: <GitBranch className="w-3 h-3" /> },
                { id: "playbook" as const, label: "Playbook", icon: <BookOpen className="w-3 h-3" /> },
                { id: "ai" as const, label: "AI Insights", icon: <Brain className="w-3 h-3" /> },
                { id: "comments" as const, label: `Comments (${comments.length})`, icon: <MessageSquare className="w-3 h-3" /> },
              ].map(t => (
                <button key={t.id} onClick={() => setTab(t.id)}
                  className={`flex items-center gap-1 px-2.5 py-1.5 text-[10px] font-medium rounded-md whitespace-nowrap transition-all ${
                    tab === t.id ? "bg-navy-700 text-white shadow-sm" : "text-gray-500 hover:text-gray-700 hover:bg-gray-100 dark:hover:bg-navy-700"
                  }`}>
                  {t.icon}{t.label}
                </button>
              ))}
            </div>

            {/* Content */}
            <div className="flex-1 overflow-y-auto p-5 space-y-4">
              {tab === "overview" && (
                <OverviewContent
                  clause={clause}
                  originalText={originalText}
                  modifiedText={modifiedText}
                  redlines={clauseRedlines}
                  riskColor={riskColor}
                />
              )}
              {tab === "redlines" && (
                <RedlinesContent redlines={clauseRedlines} />
              )}
              {tab === "playbook" && (
                <PlaybookContent
                  playbooks={clausePlaybooks}
                  onApplyFallback={onApplyFallback}
                />
              )}
              {tab === "ai" && (
                <AiContent insights={clauseInsights} />
              )}
              {tab === "comments" && (
                <CommentsContent comments={comments} />
              )}
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}

// ── Overview Tab ──────────────────────────────────────────────────────────

function OverviewContent({
  clause, originalText, modifiedText, redlines, riskColor,
}: {
  clause: ClauseContent; originalText: string; modifiedText: string;
  redlines: RedlineEntry[]; riskColor: string;
}) {
  return (
    <>
      {/* Risk & Status */}
      <div className="flex items-center gap-3">
        <span className={`text-[10px] font-bold px-2 py-1 rounded-full ${riskColor}`}>
          {clause.riskLevel.toUpperCase()}
        </span>
        <span className="text-[10px] text-gray-500">
          {redlines.filter(r => r.status === "pending").length} pending changes
        </span>
        <span className="text-[10px] text-gray-500">
          {redlines.filter(r => r.status === "accepted").length} accepted
        </span>
      </div>

      {/* Current Clause */}
      <div className="p-3 bg-white border border-gray-200 rounded-lg">
        <p className="text-[10px] font-semibold text-gray-500 uppercase mb-1.5">Current Clause</p>
        <p className="text-[11px] text-gray-700 leading-relaxed font-mono bg-gray-50 p-2 rounded border border-gray-100">
          {originalText}
        </p>
      </div>

      {/* Proposed Language */}
      {modifiedText !== originalText && (
        <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg">
          <p className="text-[10px] font-semibold text-amber-700 uppercase mb-1.5">Proposed Language</p>
          <p className="text-[11px] text-gray-700 leading-relaxed font-mono bg-white p-2 rounded border border-amber-200">
            {modifiedText}
          </p>
          <div className="flex items-center gap-2 mt-2 text-[9px] text-gray-500">
            <span className="text-green-600 font-medium">+{redlines.filter(r => r.type === "addition").length} additions</span>
            <span className="text-red-600 font-medium">-{redlines.filter(r => r.type === "deletion").length} deletions</span>
            <span className="text-amber-600 font-medium">~{redlines.filter(r => r.type === "modification").length} modifications</span>
          </div>
        </div>
      )}

      {/* Fallback Language */}
      <div className="p-3 bg-green-50 border border-green-200 rounded-lg">
        <p className="text-[10px] font-semibold text-green-700 uppercase mb-1.5">Fallback Language</p>
        <p className="text-[11px] text-gray-600 leading-relaxed">
          Recommended fallback positions are available in the Playbook tab. These are pre-approved alternatives that maintain strong protection while offering reasonable compromises.
        </p>
      </div>

      {/* Market Benchmark */}
      <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg">
        <p className="text-[10px] font-semibold text-blue-700 uppercase mb-1.5">Market Benchmark</p>
        <p className="text-[11px] text-gray-600 leading-relaxed">
          {clause.category === "liability" && "Current liability cap of 24 months is above market median (12 months). Market range is 6-36 months for enterprise SaaS."}
          {clause.category === "indemnification" && "3-year indemnification survival is above market median (2 years). Market range is 1-4 years."}
          {clause.category === "sla" && "99.95% uptime SLA with enhanced credits is aggressive but defensible. Market median is 99.9%."}
          {clause.category !== "liability" && clause.category !== "indemnification" && clause.category !== "sla" && "Market data available in the full benchmark view. This clause type shows typical variation across jurisdictions."}
        </p>
        <div className="flex items-center gap-2 mt-2 text-[9px] text-gray-500">
          <BarChart3 className="w-3 h-3" />
          <span>View full benchmark comparison in the main panel</span>
        </div>
      </div>

      {/* Approval History */}
      <div className="p-3 bg-white border border-gray-200 rounded-lg">
        <p className="text-[10px] font-semibold text-gray-500 uppercase mb-1.5">Approval History</p>
        <div className="space-y-1.5">
          {[
            { action: "Legal Review", by: "Sarah Chen", date: "2026-05-12", status: "completed" },
            { action: "Vendor Counter", by: "James Wilson", date: "2026-05-07", status: "completed" },
            { action: "Finance Review", by: "Emily Nakamura", date: "2026-05-14", status: "pending" },
          ].map((a, i) => (
            <div key={i} className="flex items-center gap-2 text-[10px] py-1">
              <div className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${
                a.status === "completed" ? "bg-green-500" : "bg-amber-500"
              }`} />
              <span className="text-gray-600 flex-1">{a.action}</span>
              <span className="text-gray-400">{a.by}</span>
              <span className="text-gray-400">{a.date}</span>
            </div>
          ))}
        </div>
      </div>
    </>
  );
}

// ── Redlines Tab ─────────────────────────────────────────────────────────

function RedlinesContent({ redlines }: { redlines: RedlineEntry[] }) {
  if (redlines.length === 0) {
    return (
      <div className="text-center py-12 text-gray-400">
        <GitBranch className="w-10 h-10 mx-auto mb-3 opacity-50" />
        <p className="text-sm">No redlines for this clause</p>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {redlines.map(r => (
        <div key={r.id} className={`p-3 rounded-lg border ${
          r.status === "accepted" ? "border-green-200 bg-green-50" :
          r.status === "rejected" ? "border-red-200 bg-red-50" :
          "border-gray-200 bg-white"
        }`}>
          <div className="flex items-center justify-between mb-1.5">
            <div className="flex items-center gap-1.5">
              <span className="text-[11px] font-semibold text-navy-900">{r.title}</span>
              {r.aiGenerated && (
                <span className="text-[8px] px-1 py-0.5 rounded bg-purple-100 text-purple-600 font-medium">AI</span>
              )}
            </div>
            <span className={`text-[9px] font-medium px-1.5 py-0.5 rounded-full ${
              r.status === "accepted" ? "bg-green-100 text-green-700" :
              r.status === "rejected" ? "bg-red-100 text-red-700" :
              "bg-gray-100 text-gray-600"
            }`}>{r.status}</span>
          </div>
          {r.type === "modification" && (
            <div className="space-y-1 text-[10px]">
              <div className="p-1.5 bg-red-50 rounded"><span className="text-red-500 line-through">{r.originalText}</span></div>
              <div className="p-1.5 bg-green-50 rounded"><span className="text-green-600">{r.modifiedText}</span></div>
            </div>
          )}
          {r.type === "addition" && (
            <div className="p-1.5 bg-green-50 rounded text-[10px]"><span className="text-green-600">+ {r.modifiedText}</span></div>
          )}
          <div className="flex items-center gap-2 mt-1.5 text-[9px] text-gray-400">
            <User className="w-2.5 h-2.5" /><span>{r.author}</span>
            <Clock className="w-2.5 h-2.5" /><span>{new Date(r.timestamp).toLocaleDateString()}</span>
            {r.aiConfidence && <span className="text-purple-500">{r.aiConfidence}% AI confidence</span>}
          </div>
        </div>
      ))}
    </div>
  );
}

// ── Playbook Tab ─────────────────────────────────────────────────────────

function PlaybookContent({
  playbooks, onApplyFallback,
}: {
  playbooks: NegotiationPlaybook[]; onApplyFallback: (fb: FallbackClause) => void;
}) {
  if (playbooks.length === 0) {
    return (
      <div className="text-center py-12 text-gray-400">
        <BookOpen className="w-10 h-10 mx-auto mb-3 opacity-50" />
        <p className="text-sm">No playbooks match this clause category</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {playbooks.map(pb => (
        <div key={pb.id} className="p-3 bg-white border border-gray-200 rounded-lg">
          <div className="flex items-center gap-1.5 mb-2">
            <BookOpen className="w-3.5 h-3.5 text-gold-500" />
            <span className="text-[11px] font-semibold text-navy-900">{pb.title}</span>
            {pb.aiRecommended && <Sparkles className="w-3 h-3 text-purple-500" />}
          </div>
          <p className="text-[10px] text-gray-500 mb-2">{pb.description}</p>

          {/* Fallback Clauses */}
          <p className="text-[9px] font-semibold text-gray-500 uppercase mb-1.5">Fallback Options</p>
          <div className="space-y-1.5">
            {pb.fallbackClauses.map(fb => (
              <div key={fb.id} className="p-2 bg-gray-50 rounded border border-gray-100">
                <div className="flex items-center justify-between mb-1">
                  <div className="flex items-center gap-1.5">
                    <span className="text-[10px] font-semibold text-navy-900">{fb.title}</span>
                    <span className={`text-[8px] px-1 py-0.5 rounded-full font-medium ${
                      fb.strength === "strong" ? "bg-green-100 text-green-700" :
                      fb.strength === "moderate" ? "bg-amber-100 text-amber-700" :
                      "bg-red-100 text-red-700"
                    }`}>{fb.strength}</span>
                  </div>
                  <button
                    onClick={() => onApplyFallback(fb)}
                    className="text-[9px] text-purple-600 hover:text-purple-700 font-medium flex items-center gap-0.5"
                  >
                    <Copy className="w-2.5 h-2.5" /> Apply
                  </button>
                </div>
                <p className="text-[9px] text-gray-600 font-mono">"{fb.content}"</p>
                <div className="flex items-center gap-2 mt-1 text-[8px] text-gray-400">
                  <span>{fb.acceptanceRate}% acceptance</span>
                  <span>{fb.riskReduction}% risk reduction</span>
                  <span>{fb.usageCount} uses</span>
                </div>
              </div>
            ))}
          </div>

          {/* Guidance */}
          <div className="mt-2 p-2 bg-navy-50 rounded border border-navy-100">
            <p className="text-[8px] font-semibold text-navy-600 uppercase mb-0.5">Escalation Guidance</p>
            <p className="text-[9px] text-gray-600">{pb.escalationGuidance}</p>
          </div>
          <div className="flex items-center gap-2 mt-1.5 text-[8px] text-gray-400">
            <Shield className="w-2.5 h-2.5" />
            <span className="capitalize">{pb.riskTolerance} risk tolerance</span>
            {pb.jurisdictionNotes && <span>&middot; {pb.jurisdictionNotes}</span>}
          </div>
        </div>
      ))}
    </div>
  );
}

// ── AI Insights Tab ──────────────────────────────────────────────────────

function AiContent({ insights }: { insights: AiNegotiationInsight[] }) {
  if (insights.length === 0) {
    return (
      <div className="text-center py-12 text-gray-400">
        <Brain className="w-10 h-10 mx-auto mb-3 opacity-50" />
        <p className="text-sm">No AI insights for this clause</p>
      </div>
    );
  }

  const severityColors = {
    critical: "border-red-200 bg-red-50/50",
    warning: "border-amber-200 bg-amber-50/50",
    info: "border-blue-200 bg-blue-50/50",
    success: "border-green-200 bg-green-50/50",
  };

  return (
    <div className="space-y-2">
      {insights.map(insight => (
        <div key={insight.id} className={`p-3 rounded-lg border ${severityColors[insight.severity]}`}>
          <div className="flex items-center gap-1.5 mb-1">
            <Brain className="w-3.5 h-3.5 text-purple-500" />
            <span className="text-[11px] font-semibold text-navy-900">{insight.title}</span>
            <span className={`text-[8px] px-1 py-0.5 rounded-full font-medium ${
              insight.confidence > 90 ? "bg-green-100 text-green-700" :
              insight.confidence > 80 ? "bg-blue-100 text-blue-700" :
              "bg-amber-100 text-amber-700"
            }`}>{insight.confidence}%</span>
          </div>
          <p className="text-[10px] text-gray-600 mb-1.5">{insight.description}</p>
          {insight.suggestedResponse && (
            <div className="p-2 bg-white/80 rounded border border-gray-100 text-[10px] text-gray-700">
              <span className="font-medium">Suggested: </span>{insight.suggestedResponse}
            </div>
          )}
          {insight.fallbackClause && (
            <div className="mt-1 p-2 bg-white/80 rounded border border-gray-100 text-[9px] text-gray-600 font-mono">
              &ldquo;{insight.fallbackClause}&rdquo;
            </div>
          )}
          <div className="flex items-center gap-2 mt-1.5 text-[8px] text-gray-400">
            <TrendingUp className="w-2.5 h-2.5" />
            <span>Impact: {insight.impact}</span>
            {insight.benchmarkPercentile !== undefined && (
              <span>&middot; {insight.benchmarkPercentile}th percentile</span>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}

// ── Comments Tab ─────────────────────────────────────────────────────────

function CommentsContent({ comments }: { comments: CommentItem[] }) {
  if (comments.length === 0) {
    return (
      <div className="text-center py-12 text-gray-400">
        <MessageSquare className="w-10 h-10 mx-auto mb-3 opacity-50" />
        <p className="text-sm">No comments on this clause</p>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {comments.map(c => (
        <div key={c.id} className="p-3 bg-white border border-gray-200 rounded-lg">
          <div className="flex items-center gap-1.5 mb-1.5">
            <div className="w-5 h-5 rounded-full bg-navy-500 flex items-center justify-center text-[8px] font-bold text-white">
              {c.authorAvatar}
            </div>
            <span className="text-[11px] font-semibold text-navy-900">{c.author}</span>
            <span className="text-[9px] text-gray-400">{c.authorRole}</span>
            <span className="text-[9px] text-gray-400 ml-auto">
              {new Date(c.timestamp).toLocaleDateString("en-US", { month: "short", day: "numeric" })}
            </span>
          </div>
          <p className="text-[10px] text-gray-600 leading-relaxed">{c.content}</p>
          {c.replies.length > 0 && (
            <div className="mt-2 pl-3 border-l-2 border-gray-100 space-y-1.5">
              {c.replies.map(r => (
                <div key={r.id} className="flex gap-1.5">
                  <div className="w-4 h-4 rounded-full bg-navy-400 flex items-center justify-center text-[6px] font-bold text-white flex-shrink-0 mt-0.5">
                    {r.authorAvatar}
                  </div>
                  <div>
                    <span className="text-[9px] font-semibold text-navy-900">{r.author}</span>
                    <p className="text-[9px] text-gray-600">{r.content}</p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

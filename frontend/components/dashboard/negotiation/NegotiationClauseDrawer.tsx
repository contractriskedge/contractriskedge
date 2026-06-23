"use client";

import React, { useState, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  X, FileText, AlertTriangle, TrendingUp, BarChart3, BookOpen,
  Brain, MessageSquare, User, Clock, CheckCircle, Copy, Sparkles,
  Shield, ChevronDown, ChevronRight, GitBranch, Star, Check, X as XIcon,
  Loader2, Send, ThumbsUp, ThumbsDown, Minus, Plus, Pencil, Eye,
  History, HelpCircle, Link2, Grid3X3, Activity, Award,
  AtSign, Paperclip, Filter, Edit3, Trash2, RefreshCw, Columns,
} from "lucide-react";
import type {
  ClauseContent, RedlineEntry, AiNegotiationInsight,
  NegotiationPlaybook, CommentItem, FallbackClause,
} from "./types";
import { TrackChangesView } from "./DiffEngine";
import { AiCoachPanel } from "./AiCoachPanel";
import { negotiationsService } from "@/services/api/negotiations";

// ── Unified Clause Drawer ─────────────────────────────────────────

type UnifiedTab =
  | "overview" | "rewrite" | "track-changes" | "comments"
  | "history" | "coach" | "dependencies" | "bundle"
  | "voting" | "metrics" | "comparison";

interface UnifiedDrawerProps {
  clause: ClauseContent | null;
  originalText: string;
  modifiedText: string;
  redlines: RedlineEntry[];
  insights: AiNegotiationInsight[];
  playbooks: NegotiationPlaybook[];
  comments: CommentItem[];
  sessionId: string;
  isOpen: boolean;
  onClose: () => void;
  onApplyFallback: (fb: FallbackClause) => void;
  onApplyBundle?: (clauseId: string, clauseType: string) => void;
  onRedlineAccept?: (redlineId: string) => void;
  onRedlineReject?: (redlineId: string) => void;
  onRefreshSession?: () => void;
}

export function NegotiationClauseDrawer(props: UnifiedDrawerProps) {
  const {
    clause, originalText, modifiedText, redlines, insights,
    playbooks, comments, sessionId, isOpen, onClose,
    onApplyFallback, onApplyBundle, onRedlineAccept, onRedlineReject,
    onRefreshSession,
  } = props;

  const [tab, setTab] = useState<UnifiedTab>("overview");

  if (!clause) return null;

  const clausePlaybooks = playbooks.filter(p => p.clauseCategory === clause.category);
  const clauseInsights = insights.filter(i => i.clauseId === clause.clauseId);
  const clauseRedlines = redlines.filter(r => r.clauseId === clause.clauseId);

  const riskColor = clause.riskLevel === "critical" ? "text-red-600 bg-red-50" :
    clause.riskLevel === "high" ? "text-orange-600 bg-orange-50" :
    clause.riskLevel === "medium" ? "text-yellow-600 bg-yellow-50" :
    "text-green-600 bg-green-50";

  const tabs: { id: UnifiedTab; label: string; icon: React.ReactNode; badge?: string | number }[] = [
    { id: "overview", label: "Overview", icon: <FileText className="w-3 h-3" /> },
    { id: "rewrite", label: "Rewrite", icon: <Sparkles className="w-3 h-3" /> },
    { id: "track-changes", label: "Changes", icon: <Eye className="w-3 h-3" />, badge: clauseRedlines.filter(r => r.status === "pending").length || undefined },
    { id: "comments", label: "Comments", icon: <MessageSquare className="w-3 h-3" />, badge: comments.length || undefined },
    { id: "history", label: "History", icon: <History className="w-3 h-3" /> },
    { id: "coach", label: "Coach", icon: <Brain className="w-3 h-3" /> },
    { id: "voting", label: "Vote", icon: <ThumbsUp className="w-3 h-3" /> },
    { id: "dependencies", label: "Deps", icon: <Link2 className="w-3 h-3" /> },
    { id: "bundle", label: "Bundle", icon: <Grid3X3 className="w-3 h-3" /> },
    { id: "metrics", label: "Metrics", icon: <BarChart3 className="w-3 h-3" /> },
    { id: "comparison", label: "Compare", icon: <Columns className="w-3 h-3" /> },
  ];

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
            className="fixed right-0 top-0 bottom-0 w-[560px] bg-white dark:bg-navy-800 border-l border-gray-200 dark:border-navy-700 shadow-2xl z-50 flex flex-col"
          >
            {/* Header */}
            <div className="px-4 py-3 border-b border-gray-200 dark:border-navy-700 flex items-center justify-between">
              <div className="flex items-center gap-2 min-w-0">
                <div className="w-7 h-7 rounded-lg bg-navy-700 flex items-center justify-center flex-shrink-0">
                  <FileText className="w-3.5 h-3.5 text-white" />
                </div>
                <div className="min-w-0">
                  <h3 className="text-xs font-semibold text-navy-900 dark:text-white truncate">{clause.title}</h3>
                  <p className="text-[9px] text-gray-500">{clause.sectionNumber} &middot; {clause.category.replace(/_/g, " ")}</p>
                </div>
              </div>
              <div className="flex items-center gap-1">
                <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded-full ${riskColor}`}>
                  {clause.riskLevel.toUpperCase()}
                </span>
                <button onClick={onClose} className="p-1 rounded hover:bg-gray-100 dark:hover:bg-navy-700 text-gray-400 transition-colors ml-1">
                  <X className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>

            {/* Scrollable Tabs */}
            <div className="px-3 py-1.5 border-b border-gray-100 dark:border-navy-700 overflow-x-auto">
              <div className="flex gap-0.5 min-w-max">
                {tabs.map(t => (
                  <button
                    key={t.id}
                    onClick={() => setTab(t.id)}
                    className={`flex items-center gap-1 px-2 py-1 text-[9px] font-medium rounded-md whitespace-nowrap transition-all ${
                      tab === t.id
                        ? "bg-navy-700 text-white shadow-sm"
                        : "text-gray-500 hover:text-gray-700 hover:bg-gray-100 dark:hover:bg-navy-700"
                    }`}
                  >
                    {t.icon}
                    <span>{t.label}</span>
                    {t.badge !== undefined && (
                      <span className={`text-[8px] px-1 rounded-full ${
                        tab === t.id ? "bg-white/20 text-white" : "bg-gray-200 dark:bg-navy-600 text-gray-600 dark:text-gray-300"
                      }`}>
                        {t.badge}
                      </span>
                    )}
                  </button>
                ))}
              </div>
            </div>

            {/* Content */}
            <div className="flex-1 overflow-y-auto">
              {tab === "overview" && (
                <OverviewContent clause={clause} originalText={originalText} modifiedText={modifiedText} redlines={clauseRedlines} riskColor={riskColor} sessionId={sessionId} />
              )}
              {tab === "rewrite" && (
                <RewriteContent clause={clause} originalText={originalText} sessionId={sessionId} onRefreshSession={onRefreshSession} />
              )}
              {tab === "track-changes" && (
                <TrackChangesContent originalText={originalText} modifiedText={modifiedText} redlines={clauseRedlines} onAccept={onRedlineAccept} onReject={onRedlineReject} />
              )}
              {tab === "comments" && (
                <CommentsContent comments={comments} sessionId={sessionId} clauseId={clause?.clauseId || ""} onRefreshSession={onRefreshSession} />
              )}
              {tab === "history" && (
                <HistoryContent sessionId={sessionId} clauseId={clause?.clauseId || ""} />
              )}
              {tab === "coach" && (
                <div className="h-full">
                  <AiCoachPanel context={{
                    type: "clause",
                    clauseId: clause?.clauseId || "",
                    clauseText: modifiedText || originalText || "",
                    clauseTitle: clause?.title || "",
                    category: clause?.category || "",
                  }} />
                </div>
              )}
              {tab === "voting" && (
                <VotingContent sessionId={sessionId} clauseId={clause?.clauseId || ""} onRefreshSession={onRefreshSession} />
              )}
              {tab === "dependencies" && (
                <DependenciesContent clauseType={clause?.category || ""} sessionId={sessionId} clauseId={clause?.clauseId || ""} />
              )}
              {tab === "bundle" && (
                <BundleContent clauseId={clause?.clauseId || ""} clauseType={clause?.category || ""} sessionId={sessionId} onApplyBundle={onApplyBundle} />
              )}
              {tab === "metrics" && (
                <MetricsContent sessionId={sessionId} clauseId={clause?.clauseId || ""} />
              )}
              {tab === "comparison" && (
                <ComparisonContent sessionId={sessionId} clauseId={clause?.clauseId || ""} originalText={originalText} modifiedText={modifiedText} />
              )}
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}

// ══════════════════════════════════════════════════════════════════
// TAB: Overview
// ══════════════════════════════════════════════════════════════════

function OverviewContent({ clause, originalText, modifiedText, redlines, riskColor, sessionId }: any) {
  const [summary, setSummary] = useState<any>(null);

  React.useEffect(() => {
    if (!sessionId) return;
    (async () => {
      try {
        const resp = await negotiationsService.getNegotiationSummary(sessionId);
        setSummary(resp);
      } catch { /* ignore */ }
    })();
  }, [sessionId]);

  return (
    <div className="p-4 space-y-3">
      {/* Session summary bar */}
      {summary && (
        <div className="grid grid-cols-4 gap-1 mb-1">
          <div className="text-center p-1.5 bg-blue-50 border border-blue-200 rounded">
            <p className="text-[9px] font-bold text-blue-700">{summary.totalClauses ?? summary.total_clauses ?? "-"}</p>
            <p className="text-[7px] text-blue-500">Clauses</p>
          </div>
          <div className="text-center p-1.5 bg-green-50 border border-green-200 rounded">
            <p className="text-[9px] font-bold text-green-700">{summary.clausesAccepted ?? summary.clauses_accepted ?? "-"}</p>
            <p className="text-[7px] text-green-500">Accepted</p>
          </div>
          <div className="text-center p-1.5 bg-amber-50 border border-amber-200 rounded">
            <p className="text-[9px] font-bold text-amber-700">{summary.clausesPending ?? summary.clauses_pending ?? "-"}</p>
            <p className="text-[7px] text-amber-500">Pending</p>
          </div>
          <div className="text-center p-1.5 bg-purple-50 border border-purple-200 rounded">
            <p className="text-[9px] font-bold text-purple-700">{summary.aiRewritesUsed ?? summary.ai_rewrites_used ?? "-"}</p>
            <p className="text-[7px] text-purple-500">AI Rewrites</p>
          </div>
        </div>
      )}

      <div className="flex items-center gap-3">
        <span className={`text-[10px] font-bold px-2 py-1 rounded-full ${riskColor}`}>{clause.riskLevel.toUpperCase()}</span>
        <span className="text-[10px] text-gray-500">{redlines.filter((r: any) => r.status === "pending").length} pending</span>
        <span className="text-[10px] text-gray-500">{redlines.filter((r: any) => r.status === "accepted").length} accepted</span>
      </div>
      <div className="p-3 bg-white border border-gray-200 rounded-lg">
        <p className="text-[9px] font-semibold text-gray-500 uppercase mb-1">Current Text</p>
        <p className="text-[11px] text-gray-700 leading-relaxed font-mono bg-gray-50 p-2 rounded border border-gray-100">{originalText}</p>
      </div>
      {modifiedText !== originalText && (
        <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg">
          <p className="text-[9px] font-semibold text-amber-700 uppercase mb-1">Proposed</p>
          <p className="text-[11px] text-gray-700 leading-relaxed font-mono bg-white p-2 rounded border border-amber-200">{modifiedText}</p>
        </div>
      )}
    </div>
  );
}

// ══════════════════════════════════════════════════════════════════
// TAB: Rewrite (inline — no modal)
// ══════════════════════════════════════════════════════════════════

const STRATEGIES = [
  { id: "balanced", label: "Balanced", icon: "⚖️", color: "border-blue-300 bg-blue-50" },
  { id: "customer_protective", label: "Customer Protective", icon: "🛡️", color: "border-emerald-300 bg-emerald-50" },
  { id: "supplier_protective", label: "Supplier Protective", icon: "🏢", color: "border-amber-300 bg-amber-50" },
  { id: "legal_standard", label: "Legal Standard", icon: "📋", color: "border-purple-300 bg-purple-50" },
  { id: "aggressive", label: "Aggressive", icon: "⚡", color: "border-red-300 bg-red-50" },
  { id: "fallback", label: "Fallback", icon: "🤝", color: "border-teal-300 bg-teal-50" },
];

function extractFindingId(clauseId: string): string | undefined {
  if (clauseId?.startsWith("finding-")) {
    return clauseId.slice("finding-".length);
  }
  return undefined;
}

function RewriteContent({ clause, originalText, sessionId, onRefreshSession }: any) {
  const clauseText = originalText || clause?.content || "";
  if (!clauseText.trim()) {
    return (
      <div className="p-4 text-center text-gray-400">
        <Sparkles className="w-6 h-6 mx-auto mb-2 opacity-50" />
        <p className="text-[10px]">AI Rewrite available for clauses only</p>
        <p className="text-[9px] mt-1">Select a clause from the Clauses tab to use AI Rewrite</p>
      </div>
    );
  }

  const [strategy, setStrategy] = useState("balanced");
  const [context, setContext] = useState("");
  const [rewrittenText, setRewrittenText] = useState<string | null>(null);
  const [editedText, setEditedText] = useState("");
  const [previousVersions, setPreviousVersions] = useState<string[]>([]);
  const [isGenerating, setIsGenerating] = useState(false);
  const [isApplying, setIsApplying] = useState(false);
  const [showResolvePrompt, setShowResolvePrompt] = useState(false);
  const [showCompare, setShowCompare] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleGenerate = async () => {
    setIsGenerating(true);
    setError(null);
    try {
      const resp = await negotiationsService.aiRewrite(sessionId, clause.clauseId, {
        clause_text: clauseText,
        strategy,
        context: context.trim() || undefined,
      });
      if (rewrittenText) {
        setPreviousVersions(prev => [...prev, editedText]);
      }
      setRewrittenText(resp.rewritten_text);
      setEditedText(resp.rewritten_text);
    } catch (err: any) {
      setError(err?.message || "Rewrite failed");
    } finally {
      setIsGenerating(false);
    }
  };

  const handleRegenerate = () => {
    if (rewrittenText) {
      setPreviousVersions(prev => [...prev, editedText]);
    }
    handleGenerate();
  };

  const handleUndo = () => {
    if (previousVersions.length > 0) {
      const prev = previousVersions[previousVersions.length - 1];
      setPreviousVersions(prev => prev.slice(0, -1));
      setEditedText(prev);
      setRewrittenText(prev);
    }
  };

  const handleApply = async () => {
    setIsApplying(true);
    try {
      await negotiationsService.createRedline(sessionId, {
        clauseId: clause.clauseId,
        type: "modification",
        title: `AI Rewrite (${strategy})`,
        originalText: clauseText,
        modifiedText: editedText,
        riskLevel: "medium",
      });
      setShowResolvePrompt(true);
      onRefreshSession?.();
    } catch {
      setError("Failed to create redline");
    } finally {
      setIsApplying(false);
    }
  };

  return (
    <div className="p-4 space-y-3">
      {/* Strategy selector — compact grid */}
      <div className="grid grid-cols-3 gap-1.5">
        {STRATEGIES.map(s => (
          <button key={s.id} onClick={() => { setStrategy(s.id); setRewrittenText(null); setPreviousVersions([]); }}
            className={`p-1.5 rounded-lg border text-left transition-all text-[9px] ${
              strategy === s.id ? `ring-2 ring-offset-1 ${s.color}` : `border-gray-200 ${s.color}`
            }`}
          >
            <span>{s.icon}</span>
            <p className="font-semibold text-navy-900 dark:text-white mt-0.5">{s.label}</p>
          </button>
        ))}
      </div>

      {/* Context input */}
      <textarea value={context} onChange={e => setContext(e.target.value)}
        placeholder="Additional context (optional)..."
        rows={1}
        className="w-full px-2 py-1 text-[10px] border border-gray-200 rounded-lg bg-gray-50 resize-none focus:outline-none focus:ring-1 focus:ring-gold-400"
      />

      {/* Generate button */}
      {!rewrittenText && (
        <button onClick={handleGenerate} disabled={isGenerating}
          className="w-full flex items-center justify-center gap-1.5 px-3 py-2 bg-purple-600 hover:bg-purple-700 disabled:bg-purple-400 text-white rounded-lg text-[10px] font-semibold transition-colors"
        >
          {isGenerating ? <><Loader2 className="w-3 h-3 animate-spin" /> Rewriting...</> : <><Sparkles className="w-3 h-3" /> AI Rewrite</>}
        </button>
      )}

      {/* Explain button (uses POST /explain endpoint) */}
      {!rewrittenText && clauseText && (
        <button onClick={async () => {
          setIsGenerating(true);
          setError("");
          try {
            const resp = await negotiationsService.aiExplain(sessionId, clause?.clauseId || "", {
              original_text: originalText,
              rewritten_text: clauseText,
              strategy: strategy,
            });
            const explainText = [
              resp.explanation,
              resp.risks_addressed?.length ? `\n\nRisks Addressed:\n- ${resp.risks_addressed.join("\n- ")}` : "",
              resp.benefits?.length ? `\n\nBenefits:\n- ${resp.benefits.join("\n- ")}` : "",
            ].filter(Boolean).join("");
            setRewrittenText(explainText || "No explanation returned.");
          } catch (e: any) {
            setError(e?.message || "Explain request failed");
          }
          setIsGenerating(false);
        }} disabled={isGenerating}
          className="w-full flex items-center justify-center gap-1.5 px-3 py-2 border border-purple-300 text-purple-700 hover:bg-purple-50 disabled:opacity-50 rounded-lg text-[10px] font-semibold transition-colors mt-1"
        >
          {isGenerating ? <Loader2 className="w-3 h-3 animate-spin" /> : <HelpCircle className="w-3 h-3" />}
          {isGenerating ? "Analyzing..." : "AI Explain"}
        </button>
      )}

      {error && <div className="text-[10px] text-red-600 bg-red-50 px-2 py-1.5 rounded-lg">{error}</div>}

      {/* Rewrite result with inline editing */}
      {rewrittenText && (
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-[9px] font-semibold text-gray-500 uppercase">
              Rewritten ({STRATEGIES.find(s => s.id === strategy)?.label})
            </span>
            <div className="flex items-center gap-1">
              <button onClick={() => setShowCompare(!showCompare)}
                className={`text-[9px] px-1.5 py-0.5 rounded ${showCompare ? "bg-navy-100 text-navy-700" : "text-gray-400 hover:text-gray-600"}`}
              >
                Compare
              </button>
              <button onClick={handleUndo} disabled={previousVersions.length === 0}
                className="text-[9px] text-gray-400 hover:text-gray-600 disabled:opacity-30"
              >
                Undo
              </button>
              <button onClick={() => { setRewrittenText(null); setPreviousVersions([]); }}
                className="text-[9px] text-gray-400 hover:text-gray-600"
              >
                Cancel
              </button>
            </div>
          </div>

          {/* Compare mode */}
          {showCompare && (
            <div className="border border-gray-200 rounded-lg overflow-hidden">
              <div className="grid grid-cols-2 divide-x divide-gray-200">
                <div className="p-2">
                  <p className="text-[8px] font-semibold text-gray-500 uppercase mb-1">Original</p>
                  <p className="text-[9px] text-gray-700 font-mono leading-relaxed whitespace-pre-wrap">{originalText}</p>
                </div>
                <div className="p-2">
                  <p className="text-[8px] font-semibold text-purple-600 uppercase mb-1">Rewritten</p>
                  <p className="text-[9px] text-purple-700 font-mono leading-relaxed whitespace-pre-wrap">{editedText}</p>
                </div>
              </div>
            </div>
          )}

          {/* Track changes diff */}
          {!showCompare && (
            <div className="border border-gray-200 rounded-lg overflow-hidden">
              <div className="px-2 py-1 bg-gray-50 border-b border-gray-200 text-[8px] text-gray-500 font-semibold uppercase">Changes</div>
              <div className="max-h-32 overflow-y-auto">
                <TrackChangesView original={originalText} modified={editedText} />
              </div>
            </div>
          )}

          {/* Version history indicator */}
          {previousVersions.length > 0 && (
            <div className="text-[8px] text-gray-400 flex items-center gap-1">
              <RefreshCw className="w-2 h-2" />
              {previousVersions.length} previous version{previousVersions.length > 1 ? 's' : ''} — click Undo to revert
            </div>
          )}

          {/* Editable text area */}
          <textarea value={editedText} onChange={e => setEditedText(e.target.value)}
            rows={5}
            className="w-full px-2 py-1.5 text-[10px] font-mono border border-gray-200 rounded-lg bg-white focus:outline-none focus:ring-1 focus:ring-gold-400 resize-none"
          />

          {/* Action buttons */}
          {!showResolvePrompt ? (
            <div className="flex gap-1.5">
              <button onClick={handleApply} disabled={isApplying}
                className="flex-1 flex items-center justify-center gap-1 px-3 py-1.5 bg-purple-600 hover:bg-purple-700 disabled:bg-purple-400 text-white rounded-lg text-[10px] font-semibold"
              >
                {isApplying ? <Loader2 className="w-3 h-3 animate-spin" /> : <Check className="w-3 h-3" />}
                Create Redline
              </button>
              <button onClick={handleRegenerate} disabled={isGenerating}
                className="flex items-center justify-center gap-1 px-3 py-1.5 border border-gray-200 rounded-lg text-[10px] text-gray-600 hover:bg-gray-50"
              >
                <RefreshCw className="w-3 h-3" /> Regenerate
              </button>
              <button onClick={() => { setRewrittenText(null); setPreviousVersions([]); }}
                className="px-3 py-1.5 border border-gray-200 rounded-lg text-[10px] text-gray-600 hover:bg-gray-50"
              >
                Try Different
              </button>
            </div>
          ) : (
            <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg space-y-2">
              <p className="text-[10px] font-semibold text-amber-700">Redline created. Resolve finding?</p>
              <div className="flex gap-1.5">
                <button onClick={() => { setShowResolvePrompt(false); setRewrittenText(null); onRefreshSession?.(); }}
                  className="flex-1 flex items-center justify-center gap-1 px-3 py-1.5 bg-green-600 hover:bg-green-700 text-white rounded-lg text-[10px] font-semibold"
                >
                  <Check className="w-3 h-3" /> Yes — Resolve
                </button>
                <button onClick={() => { setShowResolvePrompt(false); onRefreshSession?.(); }}
                  className="flex-1 px-3 py-1.5 border border-gray-200 rounded-lg text-[10px] text-gray-600 hover:bg-gray-50"
                >
                  No — Keep Open
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ══════════════════════════════════════════════════════════════════
// TAB: Track Changes with accept/reject
// ══════════════════════════════════════════════════════════════════

function TrackChangesContent({ originalText, modifiedText, redlines, onAccept, onReject }: any) {
  const pending = redlines.filter((r: any) => r.status === "pending");
  const accepted = redlines.filter((r: any) => r.status === "accepted");
  const rejected = redlines.filter((r: any) => r.status === "rejected");

  return (
    <div className="p-4 space-y-3">
      {/* Accept/Reject All */}
      {pending.length > 0 && (
        <div className="flex gap-1.5">
          <button onClick={() => pending.forEach((r: any) => onAccept?.(r.id))}
            className="flex-1 flex items-center justify-center gap-1 px-3 py-1.5 bg-green-600 hover:bg-green-700 text-white rounded-lg text-[10px] font-semibold"
          >
            <Check className="w-3 h-3" /> Accept All ({pending.length})
          </button>
          <button onClick={() => pending.forEach((r: any) => onReject?.(r.id))}
            className="flex-1 flex items-center justify-center gap-1 px-3 py-1.5 bg-red-500 hover:bg-red-600 text-white rounded-lg text-[10px] font-semibold"
          >
            <XIcon className="w-3 h-3" /> Reject All ({pending.length})
          </button>
        </div>
      )}

      {/* Track Changes View */}
      <TrackChangesView original={originalText} modified={modifiedText} />

      {/* Individual redlines */}
      <div className="space-y-1.5">
        {redlines.map((r: any) => (
          <div key={r.id} className={`p-2 rounded-lg border text-[10px] ${
            r.status === "accepted" ? "border-green-200 bg-green-50" :
            r.status === "rejected" ? "border-red-200 bg-red-50" :
            "border-gray-200 bg-white"
          }`}>
            <div className="flex items-center justify-between">
              <span className="font-medium text-navy-900">{r.title}</span>
              <span className={`text-[8px] px-1 py-0.5 rounded-full capitalize ${
                r.status === "accepted" ? "bg-green-100 text-green-700" :
                r.status === "rejected" ? "bg-red-100 text-red-700" :
                "bg-gray-100 text-gray-600"
              }`}>{r.status}</span>
            </div>
            {r.type === "modification" && (
              <div className="mt-1 space-y-0.5">
                <span className="text-red-500 line-through text-[9px]">{r.originalText}</span>
                <br />
                <span className="text-green-600 text-[9px]">{r.modifiedText}</span>
              </div>
            )}
            {r.status === "pending" && onAccept && onReject && (
              <div className="flex gap-1 mt-1.5">
                <button onClick={() => onAccept(r.id)} className="flex items-center gap-0.5 px-2 py-0.5 bg-green-500 text-white rounded text-[8px]"><Check className="w-2 h-2" /> Accept</button>
                <button onClick={() => onReject(r.id)} className="flex items-center gap-0.5 px-2 py-0.5 bg-red-500 text-white rounded text-[8px]"><XIcon className="w-2 h-2" /> Reject</button>
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Summary */}
      <div className="flex items-center gap-2 text-[9px] text-gray-400 pt-1 border-t border-gray-100">
        <span className="text-green-600">{accepted.length} accepted</span>
        <span className="text-red-600">{rejected.length} rejected</span>
        <span className="text-amber-600">{pending.length} pending</span>
      </div>
    </div>
  );
}

// ══════════════════════════════════════════════════════════════════
// TAB: Comments (enterprise)
// ══════════════════════════════════════════════════════════════════

function CommentsContent({ comments: initialComments, sessionId, clauseId, onRefreshSession }: any) {
  const [newComment, setNewComment] = useState("");
  const [filterUnresolved, setFilterUnresolved] = useState(false);
  const [sending, setSending] = useState(false);
  const [comments, setComments] = useState<any[]>(initialComments);

  React.useEffect(() => {
    if (!sessionId || !clauseId) return;
    (async () => {
      try {
        const resp = await negotiationsService.getClauseComments(
          sessionId,
          clauseId,
          extractFindingId(clauseId),
        );
        const raw = Array.isArray(resp) ? resp : [];
        setComments(raw.map((c: any) => ({
          id: c.comment_id,
          author: c.author_name || "User",
          authorAvatar: (c.author_name || "U")[0],
          authorRole: c.author_role || "",
          content: c.body,
          timestamp: c.created_at,
          status: c.resolved ? "resolved" : "active",
          comment_id: c.comment_id,
        })));
      } catch {
        setComments(initialComments);
      }
    })();
  }, [sessionId, clauseId, initialComments]);

  const filtered = filterUnresolved ? comments.filter((c: any) => c.status !== "resolved") : comments;

  const handleSend = async () => {
    if (!newComment.trim()) return;
    setSending(true);
    try {
      await negotiationsService.addClauseComment(sessionId, clauseId, {
        body: newComment.trim(),
        finding_id: extractFindingId(clauseId),
      });
      setNewComment("");
      onRefreshSession?.();
      const resp = await negotiationsService.getClauseComments(sessionId, clauseId);
      const raw = Array.isArray(resp) ? resp : [];
      setComments(raw.map((c: any) => ({
        id: c.comment_id,
        author: c.author_name || "User",
        authorAvatar: (c.author_name || "U")[0],
        authorRole: c.author_role || "",
        content: c.body,
        timestamp: c.created_at,
        status: c.resolved ? "resolved" : "active",
        comment_id: c.comment_id,
      })));
    } catch { /* ignore */ }
    setSending(false);
  };

  return (
    <div className="p-4 space-y-3">
      {/* Filter bar */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1.5">
          <button onClick={() => setFilterUnresolved(!filterUnresolved)}
            className={`text-[9px] px-1.5 py-0.5 rounded-full ${filterUnresolved ? "bg-navy-100 text-navy-700" : "text-gray-400 hover:text-gray-600"}`}
          >
            Unresolved only
          </button>
        </div>
        <span className="text-[9px] text-gray-400">{comments.length} comments</span>
      </div>

      {/* Comment input — disabled for findings */}
      <div className="flex gap-1.5">
        <input value={newComment} onChange={e => setNewComment(e.target.value)}
          placeholder="Add comment... Use @name to mention"
          onKeyDown={e => e.key === "Enter" && !e.shiftKey && handleSend()}
          className="flex-1 px-2 py-1.5 text-[10px] border border-gray-200 rounded-lg bg-gray-50 focus:outline-none focus:ring-1 focus:ring-gold-400"
        />
        <button onClick={handleSend} disabled={sending || !newComment.trim()}
          className="px-2 py-1.5 bg-gold-500 hover:bg-gold-600 disabled:bg-gray-300 text-white rounded-lg transition-colors"
        >
          {sending ? <Loader2 className="w-3 h-3 animate-spin" /> : <Send className="w-3 h-3" />}
        </button>
      </div>

      {/* Comments list */}
      <div className="space-y-2">
        {filtered.length === 0 ? (
          <div className="text-center py-8 text-gray-400">
            <MessageSquare className="w-6 h-6 mx-auto mb-2 opacity-50" />
            <p className="text-[10px]">No comments yet</p>
            <p className="text-[9px] mt-1">Type a comment above and press Enter to start the discussion</p>
          </div>
        ) : (
          filtered.map((c: any) => (
            <CommentCard key={c.id} comment={c} sessionId={sessionId} clauseId={clauseId} onRefresh={onRefreshSession} />
          ))
        )}
      </div>
    </div>
  );
}

function CommentCard({ comment, sessionId, clauseId, onRefresh, depth = 0 }: any) {
  const [showReplyInput, setShowReplyInput] = useState(false);
  const [replyText, setReplyText] = useState("");
  const [sending, setSending] = useState(false);

  const handleReply = async () => {
    if (!replyText.trim()) return;
    setSending(true);
    try {
      await negotiationsService.addClauseComment(sessionId, clauseId, {
        body: replyText.trim(),
        parent_comment_id: comment.comment_id || comment.id,
      });
      setReplyText("");
      setShowReplyInput(false);
      onRefresh?.();
    } catch { /* ignore */ }
    setSending(false);
  };

  const handleResolve = async () => {
    try {
      await negotiationsService.resolveClauseComment(sessionId, clauseId, comment.comment_id || comment.id);
      onRefresh?.();
    } catch { /* ignore */ }
  };

  return (
    <div className={`${depth > 0 ? "ml-3 pl-2 border-l-2 border-gray-100" : ""}`}>
      <div className={`p-2 rounded-lg border ${comment.status === "resolved" ? "border-green-200 bg-green-50/50" : "border-gray-200 bg-white"}`}>
        <div className="flex items-start gap-1.5">
          <div className="w-4 h-4 rounded-full bg-navy-500 flex items-center justify-center text-[6px] font-bold text-white flex-shrink-0 mt-0.5">
            {comment.authorAvatar || comment.author?.[0] || "?"}
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-1 flex-wrap">
              <span className="text-[10px] font-semibold text-navy-900">{comment.author}</span>
              {comment.authorRole && (
                <span className="text-[8px] uppercase tracking-wider px-1 py-0.5 rounded bg-navy-100 text-navy-600 font-medium">{comment.authorRole}</span>
              )}
              <span className="text-[8px] text-gray-400 ml-auto whitespace-nowrap">
                {new Date(comment.timestamp).toLocaleDateString("en-US", {
                  month: "short", day: "numeric", hour: "2-digit", minute: "2-digit",
                })}
              </span>
              {comment.status === "resolved" && <CheckCircle className="w-2.5 h-2.5 text-green-500" />}
            </div>
            <p className="text-[10px] text-gray-600 mt-0.5 leading-relaxed">
              {(comment.content || "").split(/(@\w+)/g).map((part: string, i: number) =>
                part.startsWith("@") ? <span key={i} className="text-purple-600 font-medium">{part}</span> : part
              )}
            </p>
            <div className="flex items-center gap-2 mt-1">
              {comment.status !== "resolved" && (
                <button onClick={handleResolve} className="text-[8px] text-green-600 hover:text-green-700 flex items-center gap-0.5">
                  <CheckCircle className="w-2 h-2" /> Resolve
                </button>
              )}
              <button onClick={() => setShowReplyInput(!showReplyInput)} className="text-[8px] text-gray-400 hover:text-gray-600">
                Reply
              </button>
            </div>

            {/* Reply input */}
            {showReplyInput && (
              <div className="flex gap-1 mt-1">
                <input value={replyText} onChange={e => setReplyText(e.target.value)}
                  placeholder="Write a reply..."
                  className="flex-1 px-1.5 py-0.5 text-[9px] border border-gray-200 rounded bg-gray-50 focus:outline-none"
                />
                <button onClick={handleReply} disabled={sending || !replyText.trim()}
                  className="px-1.5 py-0.5 bg-gold-500 text-white rounded text-[8px]"
                >
                  {sending ? "..." : "Reply"}
                </button>
              </div>
            )}

            {/* Replies */}
            {comment.replies?.length > 0 && (
              <div className="mt-1.5 space-y-1">
                {comment.replies.map((r: any) => (
                  <CommentCard key={r.id} comment={r} sessionId={sessionId} clauseId={clauseId} onRefresh={onRefresh} depth={depth + 1} />
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

// ══════════════════════════════════════════════════════════════════
// TAB: History
// ══════════════════════════════════════════════════════════════════

function HistoryContent({ sessionId, clauseId }: any) {
  const [history, setHistory] = useState<any[] | null>(null);
  const [loading, setLoading] = useState(true);

  React.useEffect(() => {
    if (!clauseId) { setLoading(false); return; }
    (async () => {
      try {
        const resp = await negotiationsService.getClauseHistory(sessionId, clauseId);
        setHistory(Array.isArray(resp) ? resp : (resp as any).history ?? []);
      } catch { setHistory([]); }
      setLoading(false);
    })();
  }, [sessionId, clauseId]);

  if (loading) return <div className="p-4 text-center"><Loader2 className="w-4 h-4 animate-spin text-gray-400 mx-auto" /></div>;

  const entries = history ?? [];

  return (
    <div className="p-4">
      {entries.length === 0 ? (
        <div className="text-center py-8 text-gray-400">
          <History className="w-6 h-6 mx-auto mb-1 opacity-50" />
          <p className="text-[10px]">No history yet</p>
        </div>
      ) : (
        <div className="relative">
          <div className="absolute left-3 top-2 bottom-2 w-0.5 bg-gray-200" />
          <div className="space-y-2">
            {entries.map((entry: any, idx: number) => {
              const icons: Record<string, any> = {
                created: FileText, ai_rewrite: Sparkles, legal_edit: Edit3,
                vendor_edit: User, accepted: CheckCircle,
              };
              const Icon = icons[entry.action] || FileText;
              const colors: Record<string, string> = {
                created: "bg-gray-500", ai_rewrite: "bg-purple-500",
                legal_edit: "bg-blue-500", vendor_edit: "bg-amber-500",
                accepted: "bg-green-500",
              };
              const actionLabels: Record<string, string> = {
                created: "Original", ai_rewrite: "AI Rewrite", legal_edit: "Legal",
                vendor_edit: "Vendor", accepted: "Approved",
              };
              const ts = new Date(entry.timestamp);
              const timeStr = ts.toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" });
              return (
                <div key={idx} className="flex gap-2 items-start">
                  <div className={`w-5 h-5 rounded-full ${colors[entry.action] || "bg-gray-400"} flex items-center justify-center flex-shrink-0 z-10 mt-0.5`}>
                    <Icon className="w-2.5 h-2.5 text-white" />
                  </div>
                  <div className="flex-1 min-w-0 flex items-baseline gap-2">
                    <span className="text-[10px] font-semibold text-navy-900">{actionLabels[entry.action] || entry.action.replace(/_/g, " ")}</span>
                    <span className="text-[8px] text-gray-400">{timeStr}</span>
                    <span className="text-[8px] text-gray-500 ml-auto">{entry.author}</span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

// ══════════════════════════════════════════════════════════════════
// TAB: AI Coach
// ══════════════════════════════════════════════════════════════════

function CoachContent({ clauseText, sessionId, clauseId }: any) {
  const [question, setQuestion] = useState("");
  const [response, setResponse] = useState<any | null>(null);
  const [loading, setLoading] = useState(false);

  // Coach only works for real clauses
  if (!clauseId || clauseId.startsWith("finding-") || clauseId.startsWith("issue-")) {
    return (
      <div className="p-4 text-center text-gray-400">
        <Brain className="w-6 h-6 mx-auto mb-2 opacity-50" />
        <p className="text-[10px]">AI Coach available for clauses only</p>
        <p className="text-[9px] mt-1">Select a clause from the Clauses tab to use the AI Coach</p>
      </div>
    );
  }

  const handleAsk = async () => {
    if (!question.trim()) return;
    setLoading(true);
    try {
      const resp = await negotiationsService.aiCoach(sessionId, clauseId, {
        clause_text: clauseText,
        question: question.trim(),
      });
      setResponse(resp);
    } catch { setResponse({ risks: [], policy_conflicts: [], explanation: "Coach unavailable" }); }
    setLoading(false);
  };

  const quickQuestions = [
    "Why shouldn't I accept this?",
    "What are the risks?",
    "What is market standard?",
    "Suggest alternative language",
  ];

  return (
    <div className="p-4 space-y-3">
      <div className="flex flex-wrap gap-1">
        {quickQuestions.map(q => (
          <button key={q} onClick={() => { setQuestion(q); }}
            className="text-[8px] px-1.5 py-0.5 bg-gray-100 dark:bg-navy-700 text-gray-600 dark:text-gray-300 rounded-full hover:bg-gray-200 transition-colors"
          >
            {q}
          </button>
        ))}
      </div>

      <div className="flex gap-1.5">
        <input value={question} onChange={e => setQuestion(e.target.value)}
          placeholder="Ask about this clause..."
          onKeyDown={e => e.key === "Enter" && handleAsk()}
          className="flex-1 px-2 py-1.5 text-[10px] border border-gray-200 rounded-lg bg-gray-50 focus:outline-none focus:ring-1 focus:ring-gold-400"
        />
        <button onClick={handleAsk} disabled={loading || !question.trim()}
          className="px-2 py-1.5 bg-purple-600 hover:bg-purple-700 disabled:bg-purple-400 text-white rounded-lg"
        >
          {loading ? <Loader2 className="w-3 h-3 animate-spin" /> : <Brain className="w-3 h-3" />}
        </button>
      </div>

      {response && (
        <div className="space-y-2 p-3 bg-purple-50 border border-purple-200 rounded-lg">
          {response.risks?.length > 0 && (
            <div>
              <p className="text-[9px] font-semibold text-red-600 uppercase mb-1">⚠ Risks</p>
              <div className="flex flex-wrap gap-1">{response.risks.map((r: string, i: number) => (
                <span key={i} className="text-[8px] px-1.5 py-0.5 bg-red-50 text-red-700 rounded-full border border-red-200">{r}</span>
              ))}</div>
            </div>
          )}
          {response.policy_conflicts?.length > 0 && (
            <div>
              <p className="text-[9px] font-semibold text-amber-600 uppercase mb-1">🚫 Policy Conflicts</p>
              <div className="flex flex-wrap gap-1">{response.policy_conflicts.map((p: string, i: number) => (
                <span key={i} className="text-[8px] px-1.5 py-0.5 bg-amber-50 text-amber-700 rounded-full border border-amber-200">{p}</span>
              ))}</div>
            </div>
          )}
          {response.recommended_alternative && (
            <div>
              <p className="text-[9px] font-semibold text-green-600 uppercase mb-1">✅ Recommended</p>
              <p className="text-[9px] text-gray-700 font-mono bg-white p-2 rounded border border-green-200">{response.recommended_alternative}</p>
            </div>
          )}
          <p className="text-[9px] text-gray-600 leading-relaxed">{response.explanation}</p>
        </div>
      )}
    </div>
  );
}

// ══════════════════════════════════════════════════════════════════
// TAB: Voting
// ══════════════════════════════════════════════════════════════════

const VOTER_ROLES = [
  { role: "legal", label: "Legal", color: "border-blue-300 bg-blue-50" },
  { role: "security", label: "Security", color: "border-red-300 bg-red-50" },
  { role: "business", label: "Business", color: "border-green-300 bg-green-50" },
  { role: "procurement", label: "Procurement", color: "border-purple-300 bg-purple-50" },
];

function VotingContent({ sessionId, clauseId, onRefreshSession }: any) {
  const [votes, setVotes] = useState<any[]>([]);
  const [voteSummary, setVoteSummary] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [voterName, setVoterName] = useState("");

  React.useEffect(() => {
    if (!clauseId) { setLoading(false); return; }
    (async () => {
      try {
        const resp = await negotiationsService.getClauseVotes(sessionId, clauseId);
        setVotes(Array.isArray(resp) ? resp : (resp as any).votes ?? []);
      } catch { setVotes([]); }
      // Also fetch vote summary
      try {
        const summaryResp = await negotiationsService.getVoteSummary(sessionId);
        const summaryArr = Array.isArray(summaryResp) ? summaryResp : [];
        const match = summaryArr.find((s: any) => s.clauseId === clauseId || s.clause_id === clauseId);
        if (match) setVoteSummary(match);
      } catch { /* ignore */ }
      setLoading(false);
    })();
  }, [sessionId, clauseId]);

  const handleVote = async (role: string, vote: string) => {
    const name = voterName.trim() || role.charAt(0).toUpperCase() + role.slice(1);
    try {
      await negotiationsService.castVote(sessionId, {
        clause_id: clauseId,
        finding_id: extractFindingId(clauseId),
        voter_name: name,
        voter_role: role,
        vote,
      });
      const resp = await negotiationsService.getClauseVotes(sessionId, clauseId);
      setVotes(Array.isArray(resp) ? resp : (resp as any).votes ?? []);
      onRefreshSession?.();
    } catch { /* ignore */ }
  };

  if (loading) return <div className="p-4 text-center"><Loader2 className="w-4 h-4 animate-spin text-gray-400 mx-auto" /></div>;

  const approved = votes.filter((v: any) => v.vote === "approve").length;
  const rejected = votes.filter((v: any) => v.vote === "reject").length;
  const pending = votes.filter((v: any) => v.vote === "pending").length;
  const total = votes.length;
  const approvalPct = total > 0 ? Math.round((approved / total) * 100) : 0;

  return (
    <div className="p-4 space-y-3">
      {/* Overall status */}
      <div className="text-center p-3 bg-white border border-gray-200 rounded-lg">
        <p className="text-2xl font-bold text-navy-900">{approvalPct}%</p>
        <p className="text-[9px] text-gray-500">Approval</p>
        <div className="flex items-center justify-center gap-2 mt-1 text-[9px]">
          <span className="text-green-600">✓ {approved}</span>
          <span className="text-red-600">✗ {rejected}</span>
          <span className="text-gray-400">— {pending}</span>
        </div>
        {/* Vote summary from backend */}
        {voteSummary && (
          <div className="mt-2 pt-2 border-t border-gray-100 text-[8px] text-gray-400 flex items-center justify-center gap-2">
            <span>Total: {voteSummary.totalVotes ?? voteSummary.total ?? total}</span>
            <span>Approve: {voteSummary.approveCount ?? voteSummary.approved ?? approved}</span>
            <span>Reject: {voteSummary.rejectCount ?? voteSummary.rejected ?? rejected}</span>
          </div>
        )}
      </div>

      {/* Voter name */}
      <input value={voterName} onChange={e => setVoterName(e.target.value)}
        placeholder="Your name (for voting)"
        className="w-full px-2 py-1 text-[10px] border border-gray-200 rounded-lg bg-gray-50 focus:outline-none focus:ring-1 focus:ring-gold-400"
      />

      {/* Vote buttons per role */}
      <div className="space-y-1.5">
        {VOTER_ROLES.map((vr: any) => {
          const existing = votes.find((v: any) => v.voter_role === vr.role);
          return (
            <div key={vr.role} className={`p-2 rounded-lg border ${vr.color}`}>
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-semibold text-navy-900 capitalize">{vr.label}</span>
                {existing ? (
                  <span className={`text-[9px] px-1.5 py-0.5 rounded-full ${
                    existing.vote === "approve" ? "bg-green-100 text-green-700" :
                    existing.vote === "reject" ? "bg-red-100 text-red-700" :
                    "bg-gray-100 text-gray-600"
                  }`}>{existing.vote}</span>
                ) : (
                  <span className="text-[9px] text-gray-400">Not voted</span>
                )}
              </div>
              <div className="flex gap-1 mt-1">
                <button onClick={() => handleVote(vr.role, "approve")}
                  className={`flex-1 flex items-center justify-center gap-0.5 px-2 py-1 rounded text-[9px] font-medium transition-colors ${
                    existing?.vote === "approve" ? "bg-green-500 text-white" : "bg-white border border-gray-200 text-gray-600 hover:bg-green-50"
                  }`}
                >
                  <ThumbsUp className="w-2.5 h-2.5" /> Approve
                </button>
                <button onClick={() => handleVote(vr.role, "reject")}
                  className={`flex-1 flex items-center justify-center gap-0.5 px-2 py-1 rounded text-[9px] font-medium transition-colors ${
                    existing?.vote === "reject" ? "bg-red-500 text-white" : "bg-white border border-gray-200 text-gray-600 hover:bg-red-50"
                  }`}
                >
                  <ThumbsDown className="w-2.5 h-2.5" /> Reject
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ══════════════════════════════════════════════════════════════════
// TAB: Dependencies
// ══════════════════════════════════════════════════════════════════

const DEPENDENCY_MAP: Record<string, { clause: string; relationship: string; impact: string; description: string }[]> = {
  liability: [
    { clause: "Indemnification", relationship: "direct", impact: "high", description: "Changes to liability cap directly affect indemnification obligations" },
    { clause: "Insurance", relationship: "implied", impact: "medium", description: "Liability limits determine required insurance coverage" },
    { clause: "Warranty", relationship: "related", impact: "medium", description: "Warranty disclaimers interact with liability limitations" },
    { clause: "Damages", relationship: "direct", impact: "high", description: "Liability cap defines maximum damages exposure" },
  ],
  indemnification: [
    { clause: "Liability", relationship: "direct", impact: "high", description: "Indemnification scope is limited by liability cap" },
    { clause: "Insurance", relationship: "implied", impact: "medium", description: "Indemnification obligations should be insured" },
  ],
  termination: [
    { clause: "Notice Period", relationship: "direct", impact: "high", description: "Termination rights depend on notice period" },
    { clause: "Auto-Renewal", relationship: "implied", impact: "medium", description: "Auto-renewal terms affect termination timing" },
  ],
  confidentiality: [
    { clause: "NDA", relationship: "direct", impact: "high", description: "Confidentiality provisions reference the NDA" },
    { clause: "Return of Information", relationship: "implied", impact: "medium", description: "Post-termination handling of confidential information" },
  ],
  gdpr: [
    { clause: "Data Privacy", relationship: "direct", impact: "high", description: "GDPR compliance requires data privacy provisions" },
    { clause: "Cross-Border Transfer", relationship: "direct", impact: "high", description: "GDPR restricts cross-border data transfers" },
    { clause: "Data Breach", relationship: "direct", impact: "high", description: "GDPR mandates breach notification procedures" },
  ],
  data_privacy: [
    { clause: "GDPR", relationship: "direct", impact: "high", description: "Data privacy obligations stem from GDPR requirements" },
    { clause: "Cross-Border Transfer", relationship: "direct", impact: "high", description: "Privacy compliance requires transfer safeguards" },
    { clause: "Data Breach", relationship: "implied", impact: "medium", description: "Breach notification is a key privacy obligation" },
    { clause: "DPA", relationship: "direct", impact: "high", description: "Data Processing Agreement defines privacy roles" },
  ],
  payment_terms: [
    { clause: "Late Payment", relationship: "direct", impact: "high", description: "Payment terms define late payment interest and penalties" },
    { clause: "Invoicing", relationship: "direct", impact: "high", description: "Invoicing requirements trigger payment obligations" },
    { clause: "Currency", relationship: "implied", impact: "medium", description: "Currency provisions affect payment amounts" },
    { clause: "Tax", relationship: "implied", impact: "medium", description: "Tax withholding affects net payment amounts" },
  ],
  warranty: [
    { clause: "Disclaimer", relationship: "direct", impact: "high", description: "Warranty scope is limited by disclaimers" },
    { clause: "Remedies", relationship: "direct", impact: "high", description: "Warranty breach triggers remedy obligations" },
    { clause: "Limitation of Liability", relationship: "related", impact: "medium", description: "Liability cap limits warranty claim exposure" },
  ],
  force_majeure: [
    { clause: "Notice Period", relationship: "direct", impact: "high", description: "Force majeure requires timely notice" },
    { clause: "Termination", relationship: "implied", impact: "medium", description: "Prolonged force majeure may trigger termination rights" },
    { clause: "Dispute Resolution", relationship: "related", impact: "low", description: "Force majeure disputes may require resolution mechanism" },
  ],
  governing_law: [
    { clause: "Jurisdiction", relationship: "direct", impact: "high", description: "Governing law and jurisdiction are typically paired" },
    { clause: "Dispute Resolution", relationship: "direct", impact: "high", description: "Choice of law affects dispute resolution procedures" },
    { clause: "Arbitration", relationship: "implied", impact: "medium", description: "Arbitration clauses reference governing law" },
    { clause: "Venue", relationship: "direct", impact: "high", description: "Venue is determined by jurisdiction clause" },
  ],
  dispute_resolution: [
    { clause: "Mediation", relationship: "direct", impact: "high", description: "Mediation is a prerequisite to arbitration or litigation" },
    { clause: "Arbitration", relationship: "direct", impact: "high", description: "Arbitration is an alternative to litigation" },
    { clause: "Governing Law", relationship: "direct", impact: "high", description: "Dispute resolution references governing law" },
    { clause: "Jurisdiction", relationship: "direct", impact: "high", description: "Jurisdiction determines where disputes are heard" },
  ],
  insurance: [
    { clause: "Liability", relationship: "direct", impact: "high", description: "Insurance coverage must align with liability limits" },
    { clause: "Indemnification", relationship: "direct", impact: "high", description: "Insurance backs indemnification obligations" },
    { clause: "Coverage Types", relationship: "direct", impact: "high", description: "Policy defines required coverage types and limits" },
  ],
  assignment: [
    { clause: "Change of Control", relationship: "direct", impact: "high", description: "Assignment rights often triggered by change of control" },
    { clause: "Novation", relationship: "implied", impact: "medium", description: "Novation may be required for assignment to third parties" },
    { clause: "Subcontracting", relationship: "related", impact: "medium", description: "Subcontracting restrictions interact with assignment" },
  ],
  non_compete: [
    { clause: "Non-Solicit", relationship: "direct", impact: "high", description: "Non-compete and non-solicit are typically paired" },
    { clause: "Confidentiality", relationship: "direct", impact: "high", description: "Confidentiality protects competitive advantages" },
    { clause: "Scope", relationship: "direct", impact: "high", description: "Scope and duration define non-compete enforceability" },
    { clause: "Geography", relationship: "direct", impact: "high", description: "Geographic restriction limits non-compete scope" },
  ],
  audit: [
    { clause: "Record Keeping", relationship: "direct", impact: "high", description: "Audit rights depend on proper record keeping" },
    { clause: "Compliance", relationship: "direct", impact: "high", description: "Audits verify compliance with contractual obligations" },
    { clause: "Reporting", relationship: "implied", impact: "medium", description: "Reporting obligations support audit findings" },
  ],
  sla: [
    { clause: "Uptime", relationship: "direct", impact: "high", description: "SLA defines uptime guarantees and measurements" },
    { clause: "Credits", relationship: "direct", impact: "high", description: "Service credits are remedy for SLA breaches" },
    { clause: "Support", relationship: "direct", impact: "high", description: "Support hours and response times are part of SLA" },
    { clause: "Escalation", relationship: "implied", impact: "medium", description: "Escalation procedure handles SLA disputes" },
  ],
};

function DependenciesContent({ clauseType, sessionId, clauseId }: any) {
  const [deps, setDeps] = useState<any[] | null>(null);
  const [loading, setLoading] = useState(true);

  React.useEffect(() => {
    if (!clauseId) { setLoading(false); return; }
    (async () => {
      try {
        const resp = await negotiationsService.getClauseDependencies(sessionId, clauseId);
        setDeps(Array.isArray(resp) ? resp : (resp as any).warnings ?? (resp as any).dependencies ?? []);
      } catch {
        // Fall back to static map if API fails
        setDeps(DEPENDENCY_MAP[clauseType] || []);
      }
      setLoading(false);
    })();
  }, [sessionId, clauseId, clauseType]);

  if (loading) return <div className="p-4 text-center"><Loader2 className="w-4 h-4 animate-spin text-gray-400 mx-auto" /></div>;

  const displayDeps = (deps ?? DEPENDENCY_MAP[clauseType]) || [];
  if (displayDeps.length === 0) return <div className="p-4 text-center text-gray-400 text-[10px]">No dependency data for this clause type</div>;

  return (
    <div className="p-4">
      <div className="text-center p-3 mb-3 bg-navy-700 text-white rounded-lg text-[10px] font-semibold capitalize">
        {clauseType.replace(/_/g, " ")}
      </div>
      <div className="space-y-2">
        {displayDeps.map((dep: any, i: number) => (
          <motion.div
            key={i}
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: i * 0.1 }}
            className={`p-2 rounded-lg border text-[10px] ${
              dep.impact === "high" ? "border-red-200 bg-red-50" :
              dep.impact === "medium" ? "border-amber-200 bg-amber-50" :
              "border-blue-200 bg-blue-50"
            }`}
          >
            <div className="flex items-center gap-1.5">
              <div className={`w-1.5 h-1.5 rounded-full ${
                dep.impact === "high" ? "bg-red-500" :
                dep.impact === "medium" ? "bg-amber-500" : "bg-blue-500"
              }`} />
              <span className="font-medium text-navy-900">{dep.clause}</span>
              <span className={`text-[8px] px-1 py-0.5 rounded-full capitalize ${
                dep.relationship === "direct" ? "bg-red-100 text-red-600" : "bg-gray-100 text-gray-600"
              }`}>{dep.relationship}</span>
              <span className={`text-[8px] font-medium ${
                dep.impact === "high" ? "text-red-500" :
                dep.impact === "medium" ? "text-amber-500" : "text-blue-500"
              }`}>{dep.impact.toUpperCase()}</span>
            </div>
            <p className="text-[9px] text-gray-600 mt-0.5">{dep.description}</p>
          </motion.div>
        ))}
      </div>
    </div>
  );
}

// ══════════════════════════════════════════════════════════════════
// TAB: Bundle Preview
// ══════════════════════════════════════════════════════════════════

const BUNDLE_PREVIEWS: Record<string, { clause_type: string; label: string; required: boolean }[]> = {
  gdpr: [
    { clause_type: "gdpr", label: "GDPR Compliance", required: true },
    { clause_type: "cross_border_transfer", label: "Cross-Border Transfer", required: true },
    { clause_type: "data_breach", label: "Data Breach Notification", required: true },
    { clause_type: "dpa", label: "Data Processing Agreement", required: false },
    { clause_type: "scc", label: "Standard Contractual Clauses", required: false },
  ],
  data_privacy: [
    { clause_type: "gdpr", label: "GDPR Compliance", required: true },
    { clause_type: "cross_border_transfer", label: "Cross-Border Transfer", required: true },
    { clause_type: "data_breach", label: "Data Breach Notification", required: true },
  ],
  confidentiality: [
    { clause_type: "confidentiality", label: "Confidentiality", required: true },
    { clause_type: "nda", label: "Non-Disclosure Agreement", required: true },
    { clause_type: "return_of_information", label: "Return of Information", required: false },
    { clause_type: "non_compete", label: "Non-Compete", required: false },
  ],
  indemnification: [
    { clause_type: "indemnification", label: "Indemnification", required: true },
    { clause_type: "liability", label: "Limitation of Liability", required: true },
    { clause_type: "insurance", label: "Insurance Requirements", required: false },
  ],
  liability: [
    { clause_type: "liability", label: "Limitation of Liability", required: true },
    { clause_type: "indemnification", label: "Indemnification", required: true },
    { clause_type: "consequential_damages", label: "Consequential Damages", required: false },
    { clause_type: "insurance", label: "Insurance Requirements", required: false },
  ],
  termination: [
    { clause_type: "termination", label: "Termination", required: true },
    { clause_type: "notice_period", label: "Notice Period", required: true },
    { clause_type: "auto_renewal", label: "Auto-Renewal", required: false },
    { clause_type: "for_cause_termination", label: "For-Cause Termination", required: false },
  ],
  payment_terms: [
    { clause_type: "payment_terms", label: "Payment Terms", required: true },
    { clause_type: "late_payment", label: "Late Payment / Interest", required: true },
    { clause_type: "invoicing", label: "Invoicing Requirements", required: true },
    { clause_type: "currency", label: "Currency / FX", required: false },
    { clause_type: "tax", label: "Tax & Withholding", required: false },
  ],
  warranty: [
    { clause_type: "warranty", label: "Warranty", required: true },
    { clause_type: "disclaimer", label: "Disclaimer of Warranties", required: true },
    { clause_type: "remedies", label: "Remedies", required: false },
    { clause_type: "limitation_of_liability", label: "Limitation of Liability", required: false },
  ],
  force_majeure: [
    { clause_type: "force_majeure", label: "Force Majeure", required: true },
    { clause_type: "notice_period", label: "Notice Period", required: true },
    { clause_type: "termination", label: "Termination Rights", required: false },
    { clause_type: "dispute_resolution", label: "Dispute Resolution", required: false },
  ],
  governing_law: [
    { clause_type: "governing_law", label: "Governing Law", required: true },
    { clause_type: "jurisdiction", label: "Jurisdiction", required: true },
    { clause_type: "dispute_resolution", label: "Dispute Resolution", required: true },
    { clause_type: "arbitration", label: "Arbitration", required: false },
    { clause_type: "venue", label: "Venue", required: false },
  ],
  dispute_resolution: [
    { clause_type: "dispute_resolution", label: "Dispute Resolution", required: true },
    { clause_type: "mediation", label: "Mediation", required: true },
    { clause_type: "arbitration", label: "Arbitration", required: false },
    { clause_type: "litigation", label: "Litigation", required: false },
    { clause_type: "governing_law", label: "Governing Law", required: false },
  ],
  insurance: [
    { clause_type: "insurance", label: "Insurance Requirements", required: true },
    { clause_type: "liability", label: "Limitation of Liability", required: true },
    { clause_type: "indemnification", label: "Indemnification", required: true },
    { clause_type: "coverage", label: "Coverage Types", required: false },
  ],
  assignment: [
    { clause_type: "assignment", label: "Assignment", required: true },
    { clause_type: "change_of_control", label: "Change of Control", required: true },
    { clause_type: "novation", label: "Novation", required: false },
    { clause_type: "subcontracting", label: "Subcontracting", required: false },
  ],
  non_compete: [
    { clause_type: "non_compete", label: "Non-Compete", required: true },
    { clause_type: "non_solicit", label: "Non-Solicit", required: true },
    { clause_type: "confidentiality", label: "Confidentiality", required: true },
    { clause_type: "scope", label: "Scope / Duration", required: false },
    { clause_type: "geography", label: "Geographic Restriction", required: false },
  ],
  audit: [
    { clause_type: "audit", label: "Audit Rights", required: true },
    { clause_type: "record_keeping", label: "Record Keeping", required: true },
    { clause_type: "compliance", label: "Compliance", required: true },
    { clause_type: "reporting", label: "Reporting Obligations", required: false },
  ],
  sla: [
    { clause_type: "sla", label: "Service Level Agreement", required: true },
    { clause_type: "uptime", label: "Uptime Guarantee", required: true },
    { clause_type: "credits", label: "Service Credits", required: true },
    { clause_type: "support", label: "Support Hours", required: false },
    { clause_type: "escalation", label: "Escalation Procedure", required: false },
  ],
};

function BundleContent({ clauseId, clauseType, sessionId, onApplyBundle }: any) {
  const [applying, setApplying] = useState(false);

  // Only block truly empty IDs or issue-level IDs (finding-based clauses are valid)
  if (!clauseId || clauseId.startsWith("issue-")) {
    return (
      <div className="p-4 text-center text-gray-400">
        <Grid3X3 className="w-6 h-6 mx-auto mb-2 opacity-50" />
        <p className="text-[10px]">Bundle available for clauses only</p>
        <p className="text-[9px] mt-1">Select a clause from the Clauses tab to apply a bundle</p>
      </div>
    );
  }

  const bundle = BUNDLE_PREVIEWS[clauseType];

  if (!bundle) return <div className="p-4 text-center text-gray-400 text-[10px]">No bundle available for this clause type</div>;

  const handleApply = async () => {
    setApplying(true);
    try {
      await onApplyBundle?.(clauseId, clauseType);
    } catch { /* ignore */ }
    setApplying(false);
  };

  return (
    <div className="p-4 space-y-3">
      <div className="p-3 bg-gold-50 border border-gold-200 rounded-lg">
        <p className="text-[9px] font-semibold text-gold-700 uppercase mb-1.5">Bundle: {clauseType.replace(/_/g, " ")}</p>
        <p className="text-[9px] text-gray-600 mb-2">This clause type is typically bundled with:</p>
        <div className="space-y-1">
          {bundle.map((item: any, i: number) => (
            <div key={i} className="flex items-center gap-2 text-[10px]">
              <span className={item.required ? "text-green-500" : "text-gray-300"}>
                {item.required ? "✓" : "○"}
              </span>
              <span className="text-navy-900">{item.label}</span>
              {item.required && <span className="text-[8px] text-gray-400">required</span>}
            </div>
          ))}
        </div>
      </div>

      <button onClick={handleApply} disabled={applying}
        className="w-full flex items-center justify-center gap-1.5 px-3 py-2 bg-gold-500 hover:bg-gold-600 disabled:bg-gold-300 text-white rounded-lg text-[10px] font-semibold transition-colors"
      >
        {applying ? <Loader2 className="w-3 h-3 animate-spin" /> : <Grid3X3 className="w-3 h-3" />}
        {applying ? "Applying..." : "Apply Bundle"}
      </button>
    </div>
  );
}

// ══════════════════════════════════════════════════════════════════
// TAB: Metrics
// ══════════════════════════════════════════════════════════════════

function MetricsContent({ sessionId, clauseId }: any) {
  const [scores, setScores] = useState<any | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  React.useEffect(() => {
    // Skip API call only if clauseId is truly empty or is an issue (finding-based clauses are valid)
    if (!clauseId || clauseId.startsWith("issue-")) {
      setLoading(false);
      setError(true);
      return;
    }
    (async () => {
      try {
        const resp = await negotiationsService.getClauseScore(sessionId, clauseId);
        setScores(resp);
      } catch { setScores(null); }
      setLoading(false);
    })();
  }, [sessionId, clauseId]);

  if (loading) return <div className="p-4 text-center"><Loader2 className="w-4 h-4 animate-spin text-gray-400 mx-auto" /></div>;
  if (error || !scores) return (
    <div className="p-4 text-center text-gray-400">
      <BarChart3 className="w-6 h-6 mx-auto mb-1 opacity-50" />
      <p className="text-[10px]">Clause metrics available for clauses only</p>
      <p className="text-[9px] mt-1">Open a clause from the Clauses tab to view scores</p>
    </div>
  );

  const metrics = scores ? [
    { label: "Risk", value: scores.risk_score, color: scores.risk_score > 70 ? "bg-red-500" : scores.risk_score > 40 ? "bg-amber-500" : "bg-green-500" },
    { label: "Negotiability", value: scores.negotiability_score, color: scores.negotiability_score > 70 ? "bg-green-500" : scores.negotiability_score > 40 ? "bg-amber-500" : "bg-red-500" },
    { label: "Readability", value: scores.readability_score, color: scores.readability_score > 70 ? "bg-green-500" : scores.readability_score > 40 ? "bg-amber-500" : "bg-red-500" },
    { label: "Market Standard", value: scores.market_standard_score, color: scores.market_standard_score > 70 ? "bg-green-500" : scores.market_standard_score > 40 ? "bg-amber-500" : "bg-red-500" },
    { label: "Overall", value: scores.overall_score, color: scores.overall_score > 70 ? "bg-green-500" : scores.overall_score > 40 ? "bg-amber-500" : "bg-red-500" },
  ] : [];

  if (loading) return <div className="p-4 text-center"><Loader2 className="w-4 h-4 animate-spin text-gray-400 mx-auto" /></div>;

  return (
    <div className="p-4 space-y-3">
      <div className="grid grid-cols-2 gap-2">
        {metrics.map((m: any) => (
          <div key={m.label} className="p-3 bg-white border border-gray-200 rounded-lg text-center">
            <p className="text-[9px] text-gray-500 uppercase mb-1">{m.label}</p>
            <p className="text-xl font-bold text-navy-900">{m.value}</p>
            <div className="mt-1 h-1.5 bg-gray-100 rounded-full overflow-hidden">
              <motion.div
                initial={{ width: 0 }}
                animate={{ width: `${Math.min(m.value, 100)}%` }}
                className={`h-full rounded-full ${m.color}`}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ══════════════════════════════════════════════════════════════════
// TAB: Comparison (Counterparty Position)
// ══════════════════════════════════════════════════════════════════

function ComparisonContent({ sessionId, clauseId, originalText, modifiedText }: any) {
  const [data, setData] = useState<any | null>(null);
  const [loading, setLoading] = useState(true);

  React.useEffect(() => {
    if (!clauseId || clauseId.startsWith("finding-") || clauseId.startsWith("issue-")) {
      setLoading(false);
      return;
    }
    (async () => {
      try {
        const resp = await negotiationsService.getCounterpartyComparison(sessionId, clauseId);
        setData(resp);
      } catch { setData(null); }
      setLoading(false);
    })();
  }, [sessionId, clauseId]);

  if (loading) return <div className="p-4 text-center"><Loader2 className="w-4 h-4 animate-spin text-gray-400 mx-auto" /></div>;

  if (!data) {
    return (
      <div className="p-4 space-y-3">
        <div className="grid grid-cols-2 gap-2">
          <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg">
            <p className="text-[9px] font-semibold text-blue-700 uppercase mb-1">Our Position</p>
            <p className="text-[10px] text-gray-700 font-mono leading-relaxed whitespace-pre-wrap">{originalText || "(empty)"}</p>
          </div>
          <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg">
            <p className="text-[9px] font-semibold text-amber-700 uppercase mb-1">Vendor Position</p>
            <p className="text-[10px] text-gray-700 font-mono leading-relaxed whitespace-pre-wrap">{modifiedText || originalText || "(empty)"}</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="p-4 space-y-3">
      <div className="grid grid-cols-3 gap-1.5">
        <div className="p-2 bg-blue-50 border border-blue-200 rounded-lg">
          <p className="text-[8px] font-semibold text-blue-700 uppercase mb-0.5">Our Position</p>
          <p className="text-[9px] text-gray-700 font-mono leading-relaxed whitespace-pre-wrap line-clamp-6">{data.our_position || originalText}</p>
        </div>
        <div className="p-2 bg-amber-50 border border-amber-200 rounded-lg">
          <p className="text-[8px] font-semibold text-amber-700 uppercase mb-0.5">Vendor</p>
          <p className="text-[9px] text-gray-700 font-mono leading-relaxed whitespace-pre-wrap line-clamp-6">{data.vendor_position || modifiedText}</p>
        </div>
        <div className="p-2 bg-green-50 border border-green-200 rounded-lg">
          <p className="text-[8px] font-semibold text-green-700 uppercase mb-0.5">Final</p>
          <p className="text-[9px] text-gray-700 font-mono leading-relaxed whitespace-pre-wrap line-clamp-6">{data.final_position || "Not yet agreed"}</p>
        </div>
      </div>
      {data.diff_additions?.length > 0 && (
        <div>
          <p className="text-[9px] font-semibold text-green-600 uppercase mb-1">Additions</p>
          <div className="flex flex-wrap gap-1">
            {data.diff_additions.map((d: string, i: number) => (
              <span key={i} className="text-[8px] px-1.5 py-0.5 bg-green-50 text-green-700 rounded-full border border-green-200">{d}</span>
            ))}
          </div>
        </div>
      )}
      {data.diff_deletions?.length > 0 && (
        <div>
          <p className="text-[9px] font-semibold text-red-600 uppercase mb-1">Deletions</p>
          <div className="flex flex-wrap gap-1">
            {data.diff_deletions.map((d: string, i: number) => (
              <span key={i} className="text-[8px] px-1.5 py-0.5 bg-red-50 text-red-700 rounded-full border border-red-200">{d}</span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

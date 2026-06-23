"use client";

import React, { useState, useMemo } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  MessageSquare, Check, X, AlertTriangle, Lightbulb, User, Clock,
  ChevronDown, ChevronRight, Maximize2, Minimize2, FileText,
  GitBranch, Brain, ExternalLink, PenTool, Sparkles,
} from "lucide-react";
import type {
  RedlineEntry, ClauseContent, CommentItem, CompareMode, PanelMode,
  DocumentVersion, AiNegotiationInsight,
} from "./types";
import { DiffViewer, ClauseDiffSummary, TrackChangesDiffViewer } from "./DiffEngine";

// ── Inline Comment Thread ────────────────────────────────────────────────

function CommentThread({ comment, depth = 0 }: { comment: CommentItem; depth?: number }) {
  const [showReplies, setShowReplies] = useState(true);
  return (
    <div className={`${depth > 0 ? "ml-4 pl-3 border-l-2 border-gray-100 dark:border-navy-600" : ""}`}>
      <div className="flex gap-2 py-1.5 group">
        <div className="w-5 h-5 rounded-full bg-navy-500 flex items-center justify-center text-[8px] font-bold text-white flex-shrink-0 mt-0.5">
          {comment.authorAvatar}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-1.5">
            <span className="text-[11px] font-semibold text-navy-900 dark:text-white">{comment.author}</span>
            <span className="text-[9px] text-gray-400">{comment.authorRole}</span>
            <span className="text-[9px] text-gray-400 ml-auto">
              {new Date(comment.timestamp).toLocaleDateString("en-US", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" })}
            </span>
          </div>
          <p className="text-[11px] text-gray-600 dark:text-gray-300 mt-0.5 leading-relaxed">{comment.content}</p>
          <div className="flex items-center gap-2 mt-1">
            <button className="text-[9px] text-gray-400 hover:text-navy-600 dark:hover:text-gray-300 transition-colors">Reply</button>
            <button className="text-[9px] text-gray-400 hover:text-green-600 transition-colors flex items-center gap-0.5">
              <Check className="w-2.5 h-2.5" /> Resolve
            </button>
          </div>
        </div>
      </div>
      {comment.replies.length > 0 && (
        <div>
          <button
            onClick={() => setShowReplies(!showReplies)}
            className="text-[9px] text-gray-400 hover:text-navy-600 dark:hover:text-gray-300 flex items-center gap-1 ml-4 mb-1"
          >
            {showReplies ? <ChevronDown className="w-2.5 h-2.5" /> : <ChevronRight className="w-2.5 h-2.5" />}
            {comment.replies.length} {comment.replies.length === 1 ? "reply" : "replies"}
          </button>
          <AnimatePresence>
            {showReplies && comment.replies.map(reply => (
              <CommentThread key={reply.id} comment={reply} depth={depth + 1} />
            ))}
          </AnimatePresence>
        </div>
      )}
    </div>
  );
}

// ── AI Highlight Badge ───────────────────────────────────────────────────

function AiHighlightBadge({ insight }: { insight: AiNegotiationInsight }) {
  const colors = {
    critical: "bg-red-50 border-red-200 text-red-700 dark:bg-red-900/20 dark:border-red-800 dark:text-red-400",
    warning: "bg-amber-50 border-amber-200 text-amber-700 dark:bg-amber-900/20 dark:border-amber-800 dark:text-amber-400",
    info: "bg-blue-50 border-blue-200 text-blue-700 dark:bg-blue-900/20 dark:border-blue-800 dark:text-blue-400",
    success: "bg-green-50 border-green-200 text-green-700 dark:bg-green-900/20 dark:border-green-800 dark:text-green-400",
  };
  return (
    <motion.div
      initial={{ opacity: 0, y: -4, scale: 0.95 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      className={`border rounded-lg p-2 ${colors[insight.severity]} mb-1`}
    >
      <div className="flex items-start gap-1.5">
        <Brain className="w-3 h-3 mt-0.5 flex-shrink-0" />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-1.5">
            <span className="text-[10px] font-semibold">{insight.title}</span>
            <span className={`text-[8px] px-1 py-0.5 rounded-full font-medium ${
              insight.confidence > 90 ? "bg-green-100 text-green-700" :
              insight.confidence > 80 ? "bg-blue-100 text-blue-700" :
              "bg-amber-100 text-amber-700"
            }`}>
              {insight.confidence}%
            </span>
          </div>
          <p className="text-[10px] mt-0.5 opacity-80">{insight.description}</p>
          {insight.suggestedResponse && (
            <div className="mt-1 flex items-start gap-1 text-[9px]">
              <Lightbulb className="w-2.5 h-2.5 mt-0.5 flex-shrink-0" />
              <span className="opacity-75">{insight.suggestedResponse}</span>
            </div>
          )}
        </div>
      </div>
    </motion.div>
  );
}

// ── Redline Entry Card ───────────────────────────────────────────────────

function RedlineCard({
  redline, isExpanded, onToggle, onAccept, onReject, insights, onComment, sessionId,
}: {
  redline: RedlineEntry;
  isExpanded: boolean;
  onToggle: () => void;
  onAccept: () => void;
  onReject: () => void;
  insights: AiNegotiationInsight[];
  onComment?: (redlineId: string, body: string) => void;
  sessionId?: string;
}) {
  const [commentText, setCommentText] = useState("");
  const [showCommentInput, setShowCommentInput] = useState(false);
  const typeIcon = redline.type === "addition" ? "text-green-500" :
    redline.type === "deletion" ? "text-red-500" : "text-amber-500";
  const typeLabel = redline.type === "addition" ? "Addition" :
    redline.type === "deletion" ? "Deletion" : "Modification";
  const riskColor = redline.riskLevel === "critical" ? "border-red-300 bg-red-50/50 dark:bg-red-900/10" :
    redline.riskLevel === "high" ? "border-orange-300 bg-orange-50/50 dark:bg-orange-900/10" :
    redline.riskLevel === "medium" ? "border-yellow-200 bg-yellow-50/30 dark:bg-yellow-900/5" :
    "border-gray-200 dark:border-navy-600";

  const relatedInsights = insights.filter(i => i.clauseId === redline.clauseId);

  return (
    <motion.div
      layout
      className={`border rounded-lg overflow-hidden ${riskColor} ${
        redline.status === "accepted" ? "opacity-60" :
        redline.status === "rejected" ? "opacity-40" : ""
      }`}
    >
      {/* Header */}
      <button
        onClick={onToggle}
        className="w-full text-left px-3 py-2 flex items-center justify-between hover:bg-black/5 dark:hover:bg-white/5 transition-colors"
      >
        <div className="flex items-center gap-2 min-w-0">
          <div className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${typeIcon}`} />
          <span className="text-xs font-medium text-navy-900 dark:text-white truncate">{redline.title}</span>
          <span className={`text-[9px] px-1 py-0.5 rounded font-medium flex-shrink-0 ${
            redline.type === "addition" ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400" :
            redline.type === "deletion" ? "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400" :
            "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400"
          }`}>
            {typeLabel}
          </span>
          {redline.aiGenerated && (
            <span className="text-[9px] bg-purple-100 text-purple-600 dark:bg-purple-900/30 dark:text-purple-400 px-1 py-0.5 rounded font-medium flex-shrink-0">
              AI
            </span>
          )}
          {redline.negotiationImpact === "high" && (
            <AlertTriangle className="w-3 h-3 text-red-500 flex-shrink-0" />
          )}
        </div>
        <div className="flex items-center gap-2 flex-shrink-0">
          <span className="text-[9px] text-gray-400">{redline.sectionNumber}</span>
          {isExpanded ? <ChevronDown className="w-3 h-3 text-gray-400" /> : <ChevronRight className="w-3 h-3 text-gray-400" />}
        </div>
      </button>

      {/* Expanded Content */}
      <AnimatePresence>
        {isExpanded && (
          <motion.div initial={{ height: 0 }} animate={{ height: "auto" }} exit={{ height: 0 }} className="overflow-hidden">
            <div className="px-3 pb-3 space-y-2">
              {/* Diff View */}
              <DiffViewer
                original={redline.originalText || (redline.type === "addition" ? "" : redline.modifiedText)}
                modified={redline.modifiedText || (redline.type === "deletion" ? "" : redline.originalText)}
                redlines={[redline]}
                mode="inline"
              />

              {/* AI Insights */}
              {relatedInsights.length > 0 && (
                <div className="space-y-1">
                  {relatedInsights.map(insight => (
                    <AiHighlightBadge key={insight.id} insight={insight} />
                  ))}
                </div>
              )}

              {/* Comments */}
              {redline.comments.length > 0 && (
                <div className="bg-gray-50 dark:bg-navy-900 rounded-lg p-2 space-y-1">
                  <div className="flex items-center gap-1 text-[10px] text-gray-500 font-medium mb-1">
                    <MessageSquare className="w-3 h-3" />
                    Comments ({redline.comments.length})
                  </div>
                  {redline.comments.map(comment => (
                    <CommentThread key={comment.id} comment={comment} />
                  ))}
                </div>
              )}

              {/* Comment input */}
              {showCommentInput && (
                <div className="flex gap-1.5">
                  <input
                    value={commentText}
                    onChange={e => setCommentText(e.target.value)}
                    placeholder="Add a comment..."
                    className="flex-1 px-2 py-1 text-[10px] border border-gray-200 rounded-lg bg-white focus:outline-none focus:ring-1 focus:ring-gold-400"
                    onKeyDown={e => {
                      if (e.key === "Enter" && !e.shiftKey) {
                        e.preventDefault();
                        if (commentText.trim() && onComment) {
                          onComment(redline.id, commentText.trim());
                          setCommentText("");
                          setShowCommentInput(false);
                        }
                      }
                    }}
                  />
                  <button
                    onClick={() => {
                      if (commentText.trim() && onComment) {
                        onComment(redline.id, commentText.trim());
                        setCommentText("");
                        setShowCommentInput(false);
                      }
                    }}
                    disabled={!commentText.trim()}
                    className="px-2 py-1 bg-gold-500 hover:bg-gold-600 disabled:bg-gray-300 text-white rounded-lg text-[10px] transition-colors"
                  >
                    Send
                  </button>
                </div>
              )}

              {/* Actions */}
              {redline.status === "pending" && (
                <div className="flex items-center gap-2 pt-1">
                  <button
                    onClick={onAccept}
                    className="flex items-center gap-1 px-2.5 py-1 bg-green-500 hover:bg-green-600 text-white rounded-md text-[10px] font-medium transition-colors"
                  >
                    <Check className="w-3 h-3" /> Accept
                  </button>
                  <button
                    onClick={onReject}
                    className="flex items-center gap-1 px-2.5 py-1 bg-red-500 hover:bg-red-600 text-white rounded-md text-[10px] font-medium transition-colors"
                  >
                    <X className="w-3 h-3" /> Reject
                  </button>
                  <button
                    onClick={() => setShowCommentInput(!showCommentInput)}
                    className="flex items-center gap-1 px-2.5 py-1 border border-gray-200 dark:border-navy-600 hover:bg-gray-50 dark:hover:bg-navy-700 rounded-md text-[10px] font-medium text-gray-600 dark:text-gray-300 transition-colors"
                  >
                    <MessageSquare className="w-3 h-3" /> {showCommentInput ? "Cancel" : "Comment"}
                  </button>
                  <div className="flex items-center gap-1 ml-auto text-[9px] text-gray-400">
                    <User className="w-2.5 h-2.5" />
                    {redline.author}
                    <Clock className="w-2.5 h-2.5 ml-1" />
                    {new Date(redline.timestamp).toLocaleDateString("en-US", { month: "short", day: "numeric" })}
                  </div>
                </div>
              )}

              {/* Status Badge */}
              {redline.status !== "pending" && (
                <div className="flex items-center gap-1 text-[10px]">
                  {redline.status === "accepted" ? (
                    <span className="text-green-600 flex items-center gap-1"><Check className="w-3 h-3" /> Accepted</span>
                  ) : (
                    <span className="text-red-600 flex items-center gap-1"><X className="w-3 h-3" /> Rejected</span>
                  )}
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}

// ── Center Panel ─────────────────────────────────────────────────────────

interface CenterPanelProps {
  clauses: ClauseContent[];
  redlines: RedlineEntry[];
  activeClauseId: string | null;
  compareMode: CompareMode;
  panelMode: PanelMode;
  versions: DocumentVersion[];
  currentVersionId: string;
  insights: AiNegotiationInsight[];
  onRedlineAccept: (redlineId: string) => void;
  onRedlineReject: (redlineId: string) => void;
  onCreateRedline?: () => void;
  onAiRewrite?: () => void;
  onRedlineComment?: (redlineId: string, body: string) => void;
  sessionId?: string;
}

export function CenterPanel({
  clauses, redlines, activeClauseId, compareMode, panelMode,
  versions, currentVersionId, insights,
  onRedlineAccept, onRedlineReject,
  onCreateRedline, onAiRewrite, onRedlineComment, sessionId,
}: CenterPanelProps) {
  const [expandedRedlines, setExpandedRedlines] = useState<Set<string>>(new Set());
  const [fullscreen, setFullscreen] = useState(false);

  const currentVersion = versions.find(v => v.id === currentVersionId);
  const previousVersion = versions[versions.length - 2];

  const activeClause = activeClauseId
    ? (currentVersion?.content.find(c => c.clauseId === activeClauseId) || clauses.find(c => c.clauseId === activeClauseId))
    : null;

  const clauseRedlines = activeClauseId
    ? redlines.filter(r => r.clauseId === activeClauseId)
    : redlines;

  const toggleRedline = (id: string) => {
    setExpandedRedlines(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const getOriginalContent = (clauseId: string): string => {
    const orig = previousVersion?.content.find(c => c.clauseId === clauseId);
    return orig?.content || "";
  };

  const getModifiedContent = (clauseId: string): string => {
    const mod = currentVersion?.content.find(c => c.clauseId === clauseId);
    return mod?.content || "";
  };

  if (!activeClause) {
    // Show all redlines grouped by clause
    return (
      <div className={`flex-1 flex flex-col bg-white dark:bg-navy-800 min-w-0 ${fullscreen ? "fixed inset-0 z-50" : ""}`}>
        {/* Header */}
        <div className="px-4 py-2 border-b border-gray-200 dark:border-navy-700 flex items-center justify-between">
          <div>
            <h3 className="text-sm font-semibold text-navy-900 dark:text-white">All Redlines</h3>
            <ClauseDiffSummary redlines={redlines} />
          </div>
          <button
            onClick={() => setFullscreen(!fullscreen)}
            className="p-1 hover:bg-gray-100 dark:hover:bg-navy-700 rounded transition-colors"
          >
            {fullscreen ? <Minimize2 className="w-3.5 h-3.5 text-gray-400" /> : <Maximize2 className="w-3.5 h-3.5 text-gray-400" />}
          </button>
        </div>

        {/* Redlines List */}
        <div className="flex-1 overflow-y-auto p-3 space-y-2">
          {clauseRedlines.length === 0 ? (
            <div className="text-center py-12 text-gray-400">
              <FileText className="w-10 h-10 mx-auto mb-3 opacity-50" />
              <p className="text-sm">No redlines for this clause</p>
              <p className="text-xs mt-1">Select a different clause or create a new redline</p>
              <div className="flex items-center justify-center gap-2 mt-3">
                <button onClick={onCreateRedline} className="inline-flex items-center gap-1 px-2.5 py-1 bg-navy-700 hover:bg-navy-800 text-white rounded-md text-[10px] font-medium transition-colors">
                  <PenTool className="w-3 h-3" /> Create Redline
                </button>
                <button onClick={onAiRewrite} className="inline-flex items-center gap-1 px-2.5 py-1 bg-purple-500 hover:bg-purple-600 text-white rounded-md text-[10px] font-medium transition-colors">
                  <Sparkles className="w-3 h-3" /> AI Rewrite
                </button>
              </div>
            </div>
          ) : (
            clauseRedlines.map(redline => (
              <RedlineCard
                key={redline.id}
                redline={redline}
                isExpanded={expandedRedlines.has(redline.id)}
                onToggle={() => toggleRedline(redline.id)}
                onAccept={() => onRedlineAccept(redline.id)}
                onReject={() => onRedlineReject(redline.id)}
                insights={insights}
                onComment={onRedlineComment}
                sessionId={sessionId}
              />
            ))
          )}
        </div>
      </div>
    );
  }

  // Show clause detail with diff
  const originalContent = getOriginalContent(activeClause.clauseId);
  const modifiedContent = getModifiedContent(activeClause.clauseId);
  const clauseSpecificInsights = insights.filter(i => i.clauseId === activeClause.clauseId);

  return (
    <div className={`flex-1 flex flex-col bg-white dark:bg-navy-800 min-w-0 ${fullscreen ? "fixed inset-0 z-50" : ""}`}>
      {/* Clause Header */}
      <div className="px-4 py-2 border-b border-gray-200 dark:border-navy-700">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <FileText className="w-4 h-4 text-gold-500" />
            <h3 className="text-sm font-semibold text-navy-900 dark:text-white">{activeClause.title}</h3>
            <span className="text-[10px] text-gray-400">{activeClause.sectionNumber}</span>
            <span className={`text-[9px] px-1.5 py-0.5 rounded-full font-medium ${
              activeClause.riskLevel === "critical" ? "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400" :
              activeClause.riskLevel === "high" ? "bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400" :
              activeClause.riskLevel === "medium" ? "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400" :
              "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400"
            }`}>
              {activeClause.riskLevel}
            </span>
          </div>
          <button
            onClick={() => setFullscreen(!fullscreen)}
            className="p-1 hover:bg-gray-100 dark:hover:bg-navy-700 rounded transition-colors"
          >
            {fullscreen ? <Minimize2 className="w-3.5 h-3.5 text-gray-400" /> : <Maximize2 className="w-3.5 h-3.5 text-gray-400" />}
          </button>
        </div>
        <ClauseDiffSummary redlines={clauseRedlines} />
      </div>

      {/* AI Insights for this clause */}
      {clauseSpecificInsights.length > 0 && (
        <div className="px-3 py-1.5 bg-purple-50/50 dark:bg-purple-900/10 border-b border-purple-100 dark:border-purple-900/30 space-y-1">
          {clauseSpecificInsights.map(insight => (
            <AiHighlightBadge key={insight.id} insight={insight} />
          ))}
        </div>
      )}

      {/* Diff View */}
      <div className="px-3 py-2 border-b border-gray-100 dark:border-navy-700">
        {compareMode === "track-changes" ? (
          <TrackChangesDiffViewer
            original={originalContent}
            modified={modifiedContent}
            redlines={clauseRedlines}
            mode={compareMode}
          />
        ) : (
          <DiffViewer
            original={originalContent}
            modified={modifiedContent}
            redlines={clauseRedlines}
            mode={compareMode}
          />
        )}
      </div>

      {/* Redlines for this clause */}
      <div className="flex-1 overflow-y-auto p-3 space-y-2">
        <div className="flex items-center gap-2 mb-2">
          <GitBranch className="w-3.5 h-3.5 text-gray-400" />
          <span className="text-[10px] font-semibold text-gray-500 uppercase tracking-wider">
            Redline Changes ({clauseRedlines.length})
          </span>
        </div>
        {clauseRedlines.length === 0 ? (
          <div className="text-center py-8 text-gray-400">
            <Check className="w-8 h-8 mx-auto mb-2 opacity-50" />
            <p className="text-xs">No redlines for this clause</p>
            <p className="text-[10px] mt-1">Use AI Rewrite or create a manual redline</p>
            <div className="flex items-center justify-center gap-2 mt-3">
              <button className="inline-flex items-center gap-1 px-2 py-1 bg-purple-500 hover:bg-purple-600 text-white rounded-md text-[9px] font-medium transition-colors">
                <Sparkles className="w-2.5 h-2.5" /> AI Rewrite
              </button>
              <button className="inline-flex items-center gap-1 px-2 py-1 bg-navy-700 hover:bg-navy-800 text-white rounded-md text-[9px] font-medium transition-colors">
                <PenTool className="w-2.5 h-2.5" /> Create Redline
              </button>
            </div>
          </div>

        ) : (
          clauseRedlines.map(redline => (
            <RedlineCard
              key={redline.id}
              redline={redline}
              isExpanded={expandedRedlines.has(redline.id)}
              onToggle={() => toggleRedline(redline.id)}
              onAccept={() => onRedlineAccept(redline.id)}
              onReject={() => onRedlineReject(redline.id)}
              insights={insights}
            />
          ))
        )}
      </div>
    </div>
  );
}

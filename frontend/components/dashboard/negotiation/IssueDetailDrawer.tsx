"use client";

import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  X, AlertTriangle, User, Calendar, Clock, MessageSquare, Flag,
  ArrowUpCircle, CheckCircle, Tag, Paperclip, Send, ChevronDown,
  ChevronRight, MoreHorizontal,
} from "lucide-react";
import type { NegotiationIssue, CommentItem } from "./types";

// ── Issue Detail Drawer ──────────────────────────────────────────────────

interface IssueDetailDrawerProps {
  issue: NegotiationIssue | null;
  isOpen: boolean;
  onClose: () => void;
  onStatusChange: (issueId: string, status: string) => void;
  onEscalate: (issueId: string) => void;
}

export function IssueDetailDrawer({ issue, isOpen, onClose, onStatusChange, onEscalate }: IssueDetailDrawerProps) {
  const [commentText, setCommentText] = useState("");

  if (!issue) return null;

  const severityColors = {
    blocker: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400",
    critical: "bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400",
    major: "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400",
    minor: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400",
    info: "bg-gray-100 text-gray-600 dark:bg-navy-700 dark:text-gray-400",
  };

  const statusColors = {
    open: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400",
    "in-review": "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400",
    resolved: "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400",
    escalated: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400",
    accepted: "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400",
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/20 z-40"
            onClick={onClose}
          />

          {/* Drawer */}
          <motion.div
            initial={{ x: "100%" }}
            animate={{ x: 0 }}
            exit={{ x: "100%" }}
            transition={{ type: "spring", damping: 25, stiffness: 200 }}
            className="fixed right-0 top-0 bottom-0 w-96 bg-white dark:bg-navy-800 border-l border-gray-200 dark:border-navy-700 shadow-2xl z-50 flex flex-col"
          >
            {/* Header */}
            <div className="px-4 py-3 border-b border-gray-200 dark:border-navy-700 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <AlertTriangle className={`w-4 h-4 ${
                  issue.severity === "blocker" ? "text-red-500" :
                  issue.severity === "critical" ? "text-orange-500" : "text-yellow-500"
                }`} />
                <h3 className="text-sm font-semibold text-navy-900 dark:text-white">Issue Detail</h3>
              </div>
              <button
                onClick={onClose}
                className="p-1 hover:bg-gray-100 dark:hover:bg-navy-700 rounded transition-colors"
              >
                <X className="w-4 h-4 text-gray-400" />
              </button>
            </div>

            {/* Content */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4">
              {/* Title & Status */}
              <div>
                <h4 className="text-sm font-semibold text-navy-900 dark:text-white mb-2">{issue.title}</h4>
                <div className="flex items-center gap-2 flex-wrap">
                  <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${severityColors[issue.severity]}`}>
                    {issue.severity}
                  </span>
                  <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${statusColors[issue.status]}`}>
                    {issue.status.replace("-", " ")}
                  </span>
                  <span className="text-[10px] px-2 py-0.5 bg-gray-100 dark:bg-navy-700 text-gray-600 dark:text-gray-300 rounded-full">
                    {issue.category}
                  </span>
                  {issue.escalationLevel > 0 && (
                    <span className="text-[10px] px-2 py-0.5 bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400 rounded-full font-medium">
                      L{issue.escalationLevel} Escalated
                    </span>
                  )}
                </div>
              </div>

              {/* Description */}
              <div>
                <h5 className="text-[10px] font-semibold text-gray-500 uppercase tracking-wider mb-1">Description</h5>
                <p className="text-xs text-gray-600 dark:text-gray-300 leading-relaxed">{issue.description}</p>
              </div>

              {/* Details Grid */}
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <h5 className="text-[10px] font-semibold text-gray-500 uppercase tracking-wider mb-1">Assignee</h5>
                  <div className="flex items-center gap-1.5">
                    <div className="w-5 h-5 rounded-full bg-navy-500 flex items-center justify-center text-[8px] font-bold text-white">
                      {issue.assigneeAvatar}
                    </div>
                    <span className="text-xs text-navy-900 dark:text-white">{issue.assignee}</span>
                  </div>
                </div>
                <div>
                  <h5 className="text-[10px] font-semibold text-gray-500 uppercase tracking-wider mb-1">Due Date</h5>
                  <div className="flex items-center gap-1">
                    <Calendar className="w-3 h-3 text-gray-400" />
                    <span className="text-xs text-navy-900 dark:text-white">
                      {new Date(issue.dueDate).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })}
                    </span>
                  </div>
                </div>
                <div>
                  <h5 className="text-[10px] font-semibold text-gray-500 uppercase tracking-wider mb-1">Section</h5>
                  <span className="text-xs text-navy-900 dark:text-white">{issue.sectionNumber}</span>
                </div>
                <div>
                  <h5 className="text-[10px] font-semibold text-gray-500 uppercase tracking-wider mb-1">Created</h5>
                  <div className="flex items-center gap-1">
                    <Clock className="w-3 h-3 text-gray-400" />
                    <span className="text-xs text-navy-900 dark:text-white">
                      {new Date(issue.createdAt).toLocaleDateString("en-US", { month: "short", day: "numeric" })}
                    </span>
                  </div>
                </div>
              </div>

              {/* Tags */}
              {issue.tags.length > 0 && (
                <div>
                  <h5 className="text-[10px] font-semibold text-gray-500 uppercase tracking-wider mb-1">Tags</h5>
                  <div className="flex flex-wrap gap-1">
                    {issue.tags.map(tag => (
                      <span key={tag} className="text-[9px] px-1.5 py-0.5 bg-gray-100 dark:bg-navy-700 text-gray-600 dark:text-gray-300 rounded-full flex items-center gap-0.5">
                        <Tag className="w-2 h-2" />
                        {tag}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Actions */}
              <div className="space-y-1.5">
                <h5 className="text-[10px] font-semibold text-gray-500 uppercase tracking-wider mb-1">Actions</h5>
                <div className="flex flex-wrap gap-1.5">
                  {issue.status !== "resolved" && (
                    <button
                      onClick={() => onStatusChange(issue.id, "resolved")}
                      className="flex items-center gap-1 px-2.5 py-1.5 bg-green-500 hover:bg-green-600 text-white rounded-md text-[10px] font-medium transition-colors"
                    >
                      <CheckCircle className="w-3 h-3" /> Resolve
                    </button>
                  )}
                  {issue.status !== "in-review" && issue.status !== "resolved" && (
                    <button
                      onClick={() => onStatusChange(issue.id, "in-review")}
                      className="flex items-center gap-1 px-2.5 py-1.5 bg-blue-500 hover:bg-blue-600 text-white rounded-md text-[10px] font-medium transition-colors"
                    >
                      <Flag className="w-3 h-3" /> Start Review
                    </button>
                  )}
                  {issue.escalationLevel < 3 && (
                    <button
                      onClick={() => onEscalate(issue.id)}
                      className="flex items-center gap-1 px-2.5 py-1.5 bg-orange-500 hover:bg-orange-600 text-white rounded-md text-[10px] font-medium transition-colors"
                    >
                      <ArrowUpCircle className="w-3 h-3" /> Escalate
                    </button>
                  )}
                </div>
              </div>

              {/* Comments */}
              <div>
                <h5 className="text-[10px] font-semibold text-gray-500 uppercase tracking-wider mb-2">
                  Comments ({issue.comments.length})
                </h5>
                <div className="space-y-2 mb-3">
                  {issue.comments.map(comment => (
                    <div key={comment.id} className="bg-gray-50 dark:bg-navy-900 rounded-lg p-2">
                      <div className="flex items-center gap-1.5 mb-1">
                        <div className="w-4 h-4 rounded-full bg-navy-500 flex items-center justify-center text-[7px] font-bold text-white">
                          {comment.authorAvatar}
                        </div>
                        <span className="text-[10px] font-semibold text-navy-900 dark:text-white">{comment.author}</span>
                        <span className="text-[8px] text-gray-400 ml-auto">
                          {new Date(comment.timestamp).toLocaleDateString("en-US", { month: "short", day: "numeric" })}
                        </span>
                      </div>
                      <p className="text-[10px] text-gray-600 dark:text-gray-300">{comment.content}</p>
                    </div>
                  ))}
                </div>
                {/* Add Comment */}
                <div className="flex gap-1">
                  <input
                    type="text"
                    value={commentText}
                    onChange={e => setCommentText(e.target.value)}
                    placeholder="Add a comment..."
                    className="flex-1 px-2 py-1.5 text-[10px] border border-gray-200 dark:border-navy-600 rounded-md bg-gray-50 dark:bg-navy-900 text-navy-900 dark:text-white placeholder-gray-400 focus:outline-none focus:ring-1 focus:ring-gold-400"
                  />
                  <button
                    onClick={() => { setCommentText(""); }}
                    disabled={!commentText.trim()}
                    className="px-2 py-1.5 bg-gold-500 hover:bg-gold-600 disabled:bg-gray-300 text-white rounded-md transition-colors"
                  >
                    <Send className="w-3 h-3" />
                  </button>
                </div>
              </div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}

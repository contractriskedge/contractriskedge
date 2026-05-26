"use client";

import React, { useState, useRef } from "react";
import {
  MessageSquare, Send, AtSign, CheckCheck, X, User,
  MoreHorizontal, Clock
} from "lucide-react";
import type { Comment } from "./types";

// ── Mock user database for @mentions ────────────────────────────────────────

const TEAM_MEMBERS = [
  { id: "user-1", name: "Alice Chen", role: "Senior Counsel" },
  { id: "user-2", name: "Bob Martinez", role: "Contract Analyst" },
  { id: "user-3", name: "Carol Singh", role: "VP Legal" },
  { id: "user-4", name: "David Kim", role: "Compliance Officer" },
  { id: "user-5", name: "Eve Johnson", role: "Paralegal" },
];

interface CollaborationPanelProps {
  comments: Comment[];
  onAddComment: (body: string, mentions: string[]) => void;
  onResolveComment: (commentId: string) => void;
  isOpen: boolean;
  onToggle: () => void;
}

export function CollaborationPanel({
  comments,
  onAddComment,
  onResolveComment,
  isOpen,
  onToggle,
}: CollaborationPanelProps) {
  const [newComment, setNewComment] = useState("");
  const [showMentions, setShowMentions] = useState(false);
  const [mentionFilter, setMentionFilter] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const panelRef = useRef<HTMLDivElement>(null);

  // Detect @ typing for mentions
  const handleCommentChange = (value: string) => {
    setNewComment(value);
    const atIndex = value.lastIndexOf("@");
    if (atIndex !== -1 && (atIndex === 0 || value[atIndex - 1] === " ")) {
      const afterAt = value.slice(atIndex + 1);
      if (!afterAt.includes(" ")) {
        setShowMentions(true);
        setMentionFilter(afterAt.toLowerCase());
        return;
      }
    }
    setShowMentions(false);
  };

  const insertMention = (name: string) => {
    const atIndex = newComment.lastIndexOf("@");
    const before = newComment.slice(0, atIndex);
    setNewComment(`${before}@${name} `);
    setShowMentions(false);
    textareaRef.current?.focus();
  };

  const handleSubmit = () => {
    if (!newComment.trim()) return;
    // Extract @mentions
    const mentionRegex = /@(\w+\s?\w*)/g;
    const mentions: string[] = [];
    let match;
    while ((match = mentionRegex.exec(newComment)) !== null) {
      const name = match[1].trim();
      if (name && TEAM_MEMBERS.some((m) => m.name.toLowerCase().startsWith(name.toLowerCase()))) {
        mentions.push(name);
      }
    }
    onAddComment(newComment.trim(), mentions);
    setNewComment("");
    setShowMentions(false);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const filteredMembers = TEAM_MEMBERS.filter((m) =>
    m.name.toLowerCase().includes(mentionFilter) ||
    m.role.toLowerCase().includes(mentionFilter)
  );

  const openComments = comments.filter((c) => !c.resolved);
  const resolvedComments = comments.filter((c) => c.resolved);

  // ── Slide-out panel ──

  return (
    <>
      {/* Toggle button */}
      <button
        onClick={onToggle}
        className={`inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg transition-colors ${
          isOpen
            ? "bg-navy-100 text-navy-700 border border-navy-200"
            : "bg-white text-gray-600 border border-gray-200 hover:bg-gray-50"
        }`}
        aria-label={isOpen ? "Close collaboration panel" : "Open collaboration panel"}
        aria-expanded={isOpen}
      >
        <MessageSquare className="w-3.5 h-3.5" />
        <span>Collaboration</span>
        {openComments.length > 0 && (
          <span className="bg-navy-600 text-white text-[10px] font-bold rounded-full px-1.5 py-0.5 min-w-[18px] text-center">
            {openComments.length}
          </span>
        )}
      </button>

      {/* Slide-out panel */}
      {isOpen && (
        <>
          <div className="fixed inset-0 bg-black/20 z-30" onClick={onToggle} aria-hidden="true" />
          <div
            ref={panelRef}
            role="dialog"
            aria-label="Collaboration panel"
            className="fixed right-0 top-0 bottom-0 w-96 bg-white border-l border-gray-200 shadow-xl z-40 flex flex-col animate-slide-in"
          >
            {/* Header */}
            <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200">
              <div className="flex items-center gap-2">
                <MessageSquare className="w-4 h-4 text-navy-700" />
                <h3 className="text-sm font-semibold text-navy-900">Collaboration</h3>
                <span className="text-[11px] text-gray-500">
                  {openComments.length} open
                </span>
              </div>
              <button
                onClick={onToggle}
                className="p-1 rounded hover:bg-gray-100 text-gray-400 hover:text-gray-600 transition-colors"
                aria-label="Close panel"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Comments list */}
            <div className="flex-1 overflow-y-auto p-4 space-y-3">
              {/* Open comments */}
              {openComments.map((comment) => (
                <CommentCard
                  key={comment.id}
                  comment={comment}
                  onResolve={onResolveComment}
                />
              ))}

              {/* Resolved comments */}
              {resolvedComments.length > 0 && (
                <details className="group">
                  <summary className="text-[11px] font-medium text-gray-400 cursor-pointer hover:text-gray-600 transition-colors">
                    {resolvedComments.length} resolved comment{resolvedComments.length > 1 ? "s" : ""}
                  </summary>
                  <div className="mt-2 space-y-2">
                    {resolvedComments.map((comment) => (
                      <CommentCard
                        key={comment.id}
                        comment={comment}
                        onResolve={onResolveComment}
                        resolved
                      />
                    ))}
                  </div>
                </details>
              )}

              {comments.length === 0 && (
                <div className="flex flex-col items-center justify-center py-12 text-gray-400">
                  <MessageSquare className="w-8 h-8 mb-2" />
                  <p className="text-sm font-medium">No comments yet</p>
                  <p className="text-xs mt-0.5">Use @ to mention team members</p>
                </div>
              )}
            </div>

            {/* Comment input */}
            <div className="border-t border-gray-200 p-3 bg-gray-50">
              <div className="relative">
                <textarea
                  ref={textareaRef}
                  value={newComment}
                  onChange={(e) => handleCommentChange(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="Add a comment... Use @ to mention"
                  rows={2}
                  className="w-full text-xs border border-gray-200 rounded-lg px-3 py-2 bg-white placeholder-gray-400 focus:border-navy-400 focus:ring-1 focus:ring-navy-400 resize-none"
                  aria-label="New comment"
                />
                {/* @mention dropdown */}
                {showMentions && filteredMembers.length > 0 && (
                  <div className="absolute bottom-full left-0 right-0 mb-1 bg-white border border-gray-200 rounded-lg shadow-lg max-h-32 overflow-y-auto z-50">
                    {filteredMembers.map((member) => (
                      <button
                        key={member.id}
                        onClick={() => insertMention(member.name)}
                        className="w-full text-left px-3 py-1.5 text-xs hover:bg-navy-50 flex items-center gap-2 transition-colors"
                      >
                        <div className="w-5 h-5 rounded-full bg-navy-100 flex items-center justify-center">
                          <User className="w-3 h-3 text-navy-600" />
                        </div>
                        <div>
                          <span className="font-medium text-gray-700">{member.name}</span>
                          <span className="text-gray-400 ml-1">{member.role}</span>
                        </div>
                      </button>
                    ))}
                  </div>
                )}
                <div className="flex items-center justify-between mt-1.5">
                  <span className="text-[10px] text-gray-400 flex items-center gap-1">
                    <AtSign className="w-3 h-3" />
                    @mention to notify
                  </span>
                  <button
                    onClick={handleSubmit}
                    disabled={!newComment.trim()}
                    className="inline-flex items-center gap-1 px-3 py-1 text-xs font-medium rounded-md bg-navy-700 text-white hover:bg-navy-800 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                  >
                    <Send className="w-3 h-3" />
                    Send
                  </button>
                </div>
              </div>
            </div>
          </div>
        </>
      )}
    </>
  );
}

// ── Comment Card Sub-Component ──────────────────────────────────────────────

function CommentCard({
  comment,
  onResolve,
  resolved = false,
}: {
  comment: Comment;
  onResolve: (id: string) => void;
  resolved?: boolean;
}) {
  const timeAgo = getTimeAgo(comment.createdAt);

  return (
    <div className={`p-3 rounded-lg border ${
      resolved ? "bg-gray-50 border-gray-200" : "bg-white border-gray-100 shadow-sm"
    }`}>
      {/* Author + time */}
      <div className="flex items-center justify-between mb-1.5">
        <div className="flex items-center gap-2">
          <div className="w-5 h-5 rounded-full bg-navy-100 flex items-center justify-center">
            <User className="w-3 h-3 text-navy-600" />
          </div>
          <span className="text-xs font-medium text-gray-700">{comment.author}</span>
        </div>
        <div className="flex items-center gap-1">
          <Clock className="w-3 h-3 text-gray-400" />
          <span className="text-[10px] text-gray-400">{timeAgo}</span>
        </div>
      </div>

      {/* Body with @mention highlighting */}
      <p className="text-xs text-gray-600 leading-relaxed whitespace-pre-wrap">
        {renderCommentBody(comment.body)}
      </p>

      {/* Mentions */}
      {comment.mentions.length > 0 && (
        <div className="flex items-center gap-1 mt-1.5 flex-wrap">
          <AtSign className="w-3 h-3 text-navy-400" />
          {comment.mentions.map((m, i) => (
            <span key={i} className="text-[10px] font-medium text-navy-600 bg-navy-50 px-1.5 py-0.5 rounded">
              @{m}
            </span>
          ))}
        </div>
      )}

      {/* Resolve button */}
      {!resolved && (
        <button
          onClick={() => onResolve(comment.id)}
          className="mt-2 text-[10px] font-medium text-green-600 hover:text-green-700 flex items-center gap-1 transition-colors"
        >
          <CheckCheck className="w-3 h-3" />
          Mark as resolved
        </button>
      )}
    </div>
  );
}

// ── Helpers ─────────────────────────────────────────────────────────────────

function renderCommentBody(body: string): React.ReactNode {
  // Highlight @mentions
  const parts = body.split(/(@\w+\s?\w*)/g);
  return parts.map((part, i) => {
    if (part.startsWith("@") && TEAM_MEMBERS.some((m) => m.name.toLowerCase().startsWith(part.slice(1).toLowerCase()))) {
      return (
        <span key={i} className="text-navy-600 font-medium bg-navy-50 px-0.5 rounded">
          {part}
        </span>
      );
    }
    return part;
  });
}

function getTimeAgo(isoString: string): string {
  const now = Date.now();
  const then = new Date(isoString).getTime();
  const diffMs = now - then;
  const diffMin = Math.floor(diffMs / 60000);
  if (diffMin < 1) return "just now";
  if (diffMin < 60) return `${diffMin}m ago`;
  const diffHrs = Math.floor(diffMin / 60);
  if (diffHrs < 24) return `${diffHrs}h ago`;
  const diffDays = Math.floor(diffHrs / 24);
  return `${diffDays}d ago`;
}

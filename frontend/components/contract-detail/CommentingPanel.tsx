/**
 * CommentingPanel — Collaborative review with inline comments and @mentions.
 *
 * Features:
 * - Threaded discussions with replies
 * - @mentions support for user tagging
 * - Page-specific and finding-specific comments
 * - Resolve thread workflow
 * - Author avatars with initials
 * - Relative timestamps
 * - Empty state
 * - Optimistic updates on new comments
 *
 * CON-07: Commenting & collaboration
 */

"use client";

import React, { useState, useCallback, useRef, useEffect } from "react";
import {
  MessageSquare,
  Send,
  CheckCircle2,
  AtSign,
  User,
  Clock,
  Loader2,
  AlertCircle,
  FileText,
  Hash,
} from "lucide-react";
import { useAddComment, useResolveComment } from "./hooks";
import type { Comment } from "./types";

// ── Props ───────────────────────────────────────────────────────────────────

interface CommentingPanelProps {
  comments: Comment[];
  contractId: string;
  currentPage: number;
}

// ── Helpers ─────────────────────────────────────────────────────────────────

function formatRelativeTime(timestamp: string): string {
  const d = new Date(timestamp);
  const now = new Date();
  const diff = now.getTime() - d.getTime();
  const minutes = Math.floor(diff / 60000);
  const hours = Math.floor(diff / 3600000);
  const days = Math.floor(diff / 86400000);

  if (minutes < 1) return "Just now";
  if (minutes < 60) return `${minutes}m ago`;
  if (hours < 24) return `${hours}h ago`;
  if (days < 7) return `${days}d ago`;
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

function getInitials(name: string): string {
  return name
    .split(/[\s._-]+/)
    .map((w) => w[0])
    .join("")
    .toUpperCase()
    .slice(0, 2);
}

function getAvatarColor(id: string): string {
  const colors = [
    "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300",
    "bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300",
    "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300",
    "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300",
    "bg-indigo-100 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-300",
    "bg-rose-100 text-rose-700 dark:bg-rose-900/30 dark:text-rose-300",
  ];
  let hash = 0;
  for (let i = 0; i < id.length; i++) {
    hash = ((hash << 5) - hash) + id.charCodeAt(i);
  }
  return colors[Math.abs(hash) % colors.length];
}

// ── Comment Thread Component ────────────────────────────────────────────────

function CommentThread({
  comment,
  contractId,
  onReply,
}: {
  comment: Comment;
  contractId: string;
  onReply: (parentId: string) => void;
}) {
  const resolveMutation = useResolveComment(contractId);
  const [showReplies, setShowReplies] = useState(true);

  const handleResolve = async () => {
    try {
      await resolveMutation.mutateAsync(comment.id);
    } catch {
      // Error handled by query client
    }
  };

  const renderContent = (content: string) => {
    // Highlight @mentions
    return content.split(/(@\w+)/).map((part, i) => {
      if (part.startsWith("@")) {
        return (
          <span key={i} className="text-blue-600 dark:text-blue-400 font-medium">
            {part}
          </span>
        );
      }
      return part;
    });
  };

  return (
    <div className={`${comment.parent_id ? "ml-8 mt-2" : ""}`}>
      <div className={`rounded-lg p-3 ${
        comment.status === "resolved"
          ? "bg-gray-50 dark:bg-navy-850 opacity-75"
          : "bg-white dark:bg-navy-800 border border-gray-100 dark:border-navy-700"
      }`}>
        {/* Header */}
        <div className="flex items-center gap-2 mb-1.5">
          <span className={`w-6 h-6 rounded-full ${getAvatarColor(comment.author)} flex items-center justify-center text-[9px] font-bold flex-shrink-0`}>
            {getInitials(comment.author)}
          </span>
          <span className="text-[11px] font-medium text-navy-900 dark:text-white">
            {comment.author}
          </span>
          <span className="text-[9px] text-gray-400 dark:text-gray-500">
            {formatRelativeTime(comment.created_at)}
          </span>
          {comment.page_number && (
            <span className="flex items-center gap-0.5 text-[9px] text-gray-400 ml-auto">
              <FileText className="w-2.5 h-2.5" />
              Page {comment.page_number}
            </span>
          )}
          {comment.status === "resolved" && (
            <span className="flex items-center gap-0.5 text-[9px] text-green-600 dark:text-green-400">
              <CheckCircle2 className="w-2.5 h-2.5" />
              Resolved
            </span>
          )}
        </div>

        {/* Content */}
        <p className="text-[11px] text-gray-700 dark:text-gray-300 leading-relaxed">
          {renderContent(comment.content)}
        </p>

        {/* Actions */}
        <div className="flex items-center gap-2 mt-1.5">
          {!comment.parent_id && (
            <button
              onClick={() => onReply(comment.id)}
              className="text-[9px] text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 font-medium"
            >
              Reply
            </button>
          )}
          {comment.status === "active" && !comment.parent_id && (
            <button
              onClick={handleResolve}
              disabled={resolveMutation.isPending}
              className="flex items-center gap-0.5 text-[9px] text-green-600 hover:text-green-700 dark:text-green-400 font-medium"
            >
              <CheckCircle2 className="w-2.5 h-2.5" />
              {resolveMutation.isPending ? "Resolving..." : "Resolve"}
            </button>
          )}
        </div>
      </div>

      {/* Replies */}
      {comment.replies.length > 0 && (
        <div className="mt-1">
          <button
            onClick={() => setShowReplies(!showReplies)}
            className="text-[9px] text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 ml-8 mb-1 font-medium"
          >
            {showReplies ? "Hide replies" : `${comment.replies.length} ${comment.replies.length === 1 ? "reply" : "replies"}`}
          </button>
          {showReplies && comment.replies.map((reply) => (
            <CommentThread
              key={reply.id}
              comment={reply}
              contractId={contractId}
              onReply={onReply}
            />
          ))}
        </div>
      )}
    </div>
  );
}

// ── Main Component ──────────────────────────────────────────────────────────

export function CommentingPanel({ comments, contractId, currentPage }: CommentingPanelProps) {
  const [newComment, setNewComment] = useState("");
  const [replyToId, setReplyToId] = useState<string | null>(null);
  const [showMentions, setShowMentions] = useState(false);
  const [mentionSearch, setMentionSearch] = useState("");
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const addCommentMutation = useAddComment(contractId);

  // Mock users for @mentions — in production, this would come from the API
  const mockUsers = [
    "Alice Johnson", "Bob Smith", "Carol Williams", "David Brown",
    "Eve Davis", "Frank Miller", "Grace Wilson", "Henry Moore",
  ];

  const filteredUsers = mentionSearch
    ? mockUsers.filter((u) => u.toLowerCase().includes(mentionSearch.toLowerCase()))
    : mockUsers;

  // ── Handle Input Change ──────────────────────────────────────────────

  const handleInputChange = useCallback(
    (e: React.ChangeEvent<HTMLTextAreaElement>) => {
      const value = e.target.value;
      setNewComment(value);

      // Detect @mention trigger
      const lastAt = value.lastIndexOf("@");
      if (lastAt >= 0) {
        const afterAt = value.slice(lastAt + 1);
        // Check if we're in the middle of typing a mention
        if (!afterAt.includes(" ") && afterAt.length > 0) {
          setShowMentions(true);
          setMentionSearch(afterAt);
        } else if (afterAt.length === 0) {
          setShowMentions(true);
          setMentionSearch("");
        } else {
          setShowMentions(false);
        }
      } else {
        setShowMentions(false);
      }
    },
    []
  );

  // ── Insert Mention ───────────────────────────────────────────────────

  const insertMention = useCallback(
    (user: string) => {
      const lastAt = newComment.lastIndexOf("@");
      if (lastAt >= 0) {
        const before = newComment.slice(0, lastAt);
        const after = newComment.slice(lastAt + mentionSearch.length + 1);
        setNewComment(`${before}@${user} ${after}`);
      }
      setShowMentions(false);
      inputRef.current?.focus();
    },
    [newComment, mentionSearch]
  );

  // ── Submit Comment ───────────────────────────────────────────────────

  const handleSubmit = useCallback(async () => {
    if (!newComment.trim()) return;

    try {
      // Extract @mentions from content
      const mentions = [...newComment.matchAll(/@(\w+(?:\s+\w+)?)/g)].map((m) => m[1].trim());

      await addCommentMutation.mutateAsync({
        body: newComment.trim(),
        parent_comment_id: replyToId || undefined,
        mentions,
      });

      setNewComment("");
      setReplyToId(null);
    } catch {
      // Error handled by query client
    }
  }, [newComment, replyToId, currentPage, addCommentMutation]);

  // ── Handle Reply ─────────────────────────────────────────────────────

  const handleReply = useCallback((parentId: string) => {
    setReplyToId(parentId);
    inputRef.current?.focus();
  }, []);

  const cancelReply = useCallback(() => {
    setReplyToId(null);
    setNewComment("");
  }, []);

  // ── Keyboard Shortcuts ───────────────────────────────────────────────

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        handleSubmit();
      }
      if (e.key === "Escape") {
        cancelReply();
      }
    },
    [handleSubmit, cancelReply]
  );

  // ── Separate top-level comments from replies ─────────────────────────

  const topLevelComments = comments.filter((c) => !c.parent_id);
  const resolvedComments = topLevelComments.filter((c) => c.status === "resolved");
  const activeComments = topLevelComments.filter((c) => c.status === "active");

  // ── Render ───────────────────────────────────────────────────────────

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="px-4 py-3 border-b border-gray-100 dark:border-navy-700">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold text-navy-900 dark:text-white">
            Comments ({comments.length})
          </h3>
          <div className="flex items-center gap-2 text-[10px] text-gray-500">
            <span className="flex items-center gap-0.5">
              <MessageSquare className="w-3 h-3" />
              {activeComments.length} active
            </span>
            <span className="flex items-center gap-0.5">
              <CheckCircle2 className="w-3 h-3 text-green-500" />
              {resolvedComments.length} resolved
            </span>
          </div>
        </div>
      </div>

      {/* Comments List */}
      <div className="flex-1 overflow-y-auto p-3 space-y-3">
        {comments.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center py-8">
            <MessageSquare className="w-10 h-10 text-gray-300 dark:text-gray-600 mb-3" />
            <p className="text-sm font-medium text-gray-700 dark:text-gray-300">No comments yet</p>
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1 max-w-xs">
              Start a conversation by adding a comment below. Use @ to mention team members.
            </p>
          </div>
        ) : (
          <>
            {/* Active Comments */}
            {activeComments.length > 0 && (
              <div className="space-y-2">
                {activeComments.map((comment) => (
                  <CommentThread
                    key={comment.id}
                    comment={comment}
                    contractId={contractId}
                    onReply={handleReply}
                  />
                ))}
              </div>
            )}

            {/* Resolved Comments */}
            {resolvedComments.length > 0 && (
              <details className="group">
                <summary className="text-[10px] font-medium text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 cursor-pointer py-1">
                  {resolvedComments.length} resolved {resolvedComments.length === 1 ? "thread" : "threads"}
                </summary>
                <div className="mt-2 space-y-2">
                  {resolvedComments.map((comment) => (
                    <CommentThread
                      key={comment.id}
                      comment={comment}
                      contractId={contractId}
                      onReply={handleReply}
                    />
                  ))}
                </div>
              </details>
            )}
          </>
        )}
      </div>

      {/* ── Comment Input ─────────────────────────────────────────────── */}
      <div className="border-t border-gray-100 dark:border-navy-700 p-3 bg-gray-50 dark:bg-navy-850">
        {replyToId && (
          <div className="flex items-center justify-between mb-2 px-2 py-1 rounded bg-blue-50 dark:bg-blue-900/10">
            <span className="text-[10px] text-blue-600 dark:text-blue-400">
              Replying to comment
            </span>
            <button
              onClick={cancelReply}
              className="text-[9px] text-gray-500 hover:text-gray-700"
            >
              Cancel
            </button>
          </div>
        )}

        <div className="relative">
          <textarea
            ref={inputRef}
            value={newComment}
            onChange={handleInputChange}
            onKeyDown={handleKeyDown}
            placeholder={replyToId ? "Write a reply... (@ to mention)" : "Add a comment... (@ to mention)"}
            rows={2}
            className="w-full text-[11px] bg-white dark:bg-navy-700 border border-gray-200 dark:border-navy-600 rounded-lg px-3 py-2 pr-10 text-navy-900 dark:text-white placeholder-gray-400 focus:outline-none focus:ring-1 focus:ring-navy-400 resize-none"
          />
          <button
            onClick={handleSubmit}
            disabled={!newComment.trim() || addCommentMutation.isPending}
            className="absolute right-2 bottom-2 p-1 rounded-md bg-navy-600 text-white hover:bg-navy-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            aria-label="Send comment"
            title="Send (Cmd+Enter)"
          >
            {addCommentMutation.isPending ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
            ) : (
              <Send className="w-3.5 h-3.5" />
            )}
          </button>
        </div>

        <div className="flex items-center justify-between mt-1.5">
          <span className="text-[9px] text-gray-400">
            <kbd className="px-1 py-0.5 rounded bg-gray-100 dark:bg-navy-700 text-gray-500 font-mono text-[8px]">⌘+Enter</kbd> to send
          </span>
          <span className="text-[9px] text-gray-400">
            <AtSign className="w-2.5 h-2.5 inline" /> @ to mention
          </span>
        </div>

        {/* ── @Mention Dropdown ────────────────────────────────────────── */}
        {showMentions && (
          <div className="absolute bottom-full left-0 right-0 mb-1 mx-3 bg-white dark:bg-navy-700 border border-gray-200 dark:border-navy-600 rounded-lg shadow-lg max-h-32 overflow-y-auto z-10">
            {filteredUsers.length === 0 ? (
              <div className="px-3 py-2 text-[10px] text-gray-400">No users found</div>
            ) : (
              filteredUsers.map((user) => (
                <button
                  key={user}
                  onClick={() => insertMention(user)}
                  className="flex items-center gap-2 w-full px-3 py-1.5 text-[11px] text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-navy-600 text-left"
                >
                  <span className={`w-5 h-5 rounded-full ${getAvatarColor(user)} flex items-center justify-center text-[8px] font-bold`}>
                    {getInitials(user)}
                  </span>
                  {user}
                </button>
              ))
            )}
          </div>
        )}
      </div>
    </div>
  );
}

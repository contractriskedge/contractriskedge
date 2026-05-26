/**
 * CommentThread — chronological threaded comments with actor identity.
 *
 * Features:
 * - Chronological order (oldest first)
 * - Actor identity with avatar fallback
 * - Timestamps with relative formatting
 * - Threaded replies via parent_comment_id
 * - System events mixed with human comments
 * - Inline reply input
 * - Loading and error states
 */

"use client";

import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { motion, AnimatePresence } from "framer-motion";
import { MessageSquare, User, Clock, Reply, Loader2 } from "lucide-react";
import { reviewService } from "@/services/api/reviews";
import type { CommentItem } from "@/services/api/client";

// ── Helpers ─────────────────────────────────────────────────────

function formatTimeAgo(dateStr: string): string {
  const now = Date.now();
  const then = new Date(dateStr).getTime();
  const diff = now - then;
  const mins = Math.floor(diff / 60000);
  const hours = Math.floor(diff / 3600000);
  const days = Math.floor(diff / 86400000);

  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  if (hours < 24) return `${hours}h ago`;
  if (days < 7) return `${days}d ago`;
  return new Date(dateStr).toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

function getActorInitials(name: string): string {
  return name
    .split(" ")
    .map((w) => w[0])
    .join("")
    .toUpperCase()
    .slice(0, 2);
}

function getActorColor(id: string): string {
  const colors = [
    "bg-blue-100 text-blue-700",
    "bg-purple-100 text-purple-700",
    "bg-green-100 text-green-700",
    "bg-amber-100 text-amber-700",
    "bg-indigo-100 text-indigo-700",
    "bg-rose-100 text-rose-700",
  ];
  let hash = 0;
  for (let i = 0; i < id.length; i++) {
    hash = ((hash << 5) - hash) + id.charCodeAt(i);
  }
  return colors[Math.abs(hash) % colors.length];
}

function isSystemEvent(comment: CommentItem): boolean {
  return comment.author_id === "system" || comment.author_id === "routing_engine";
}

// ── Props ───────────────────────────────────────────────────────

interface CommentThreadProps {
  reviewId: string;
}

// ── Component ───────────────────────────────────────────────────

export function CommentThread({ reviewId }: CommentThreadProps) {
  const queryClient = useQueryClient();
  const [replyTo, setReplyTo] = useState<string | null>(null);
  const [replyText, setReplyText] = useState("");
  const [newCommentText, setNewCommentText] = useState("");

  // ── Queries ──

  const { data, isLoading } = useQuery({
    queryKey: ["reviews", reviewId, "comments"],
    queryFn: () => reviewService.listComments(reviewId),
    staleTime: 10_000,
    refetchInterval: 30_000,
  });

  const comments = data?.comments ?? [];

  // ── Mutations ──

  const addCommentMut = useMutation({
    mutationFn: ({ body, parentCommentId }: { body: string; parentCommentId?: string }) =>
      reviewService.addComment(reviewId, {
        body,
        parent_comment_id: parentCommentId,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["reviews", reviewId, "comments"] });
      setNewCommentText("");
      setReplyText("");
      setReplyTo(null);
    },
  });

  // ── Threaded organization ──

  const topLevel = comments.filter((c) => !c.parent_comment_id);
  const replies = (parentId: string) => comments.filter((c) => c.parent_comment_id === parentId);

  const sorted = [...topLevel].sort(
    (a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime(),
  );

  // ── Render ──

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-8">
        <Loader2 className="w-5 h-5 text-gray-400 animate-spin" />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* ── New Comment Input ── */}
      <div className="flex items-start gap-3">
        <div className="w-8 h-8 rounded-full bg-gray-200 flex items-center justify-center flex-shrink-0">
          <User className="w-4 h-4 text-gray-500" />
        </div>
        <div className="flex-1 space-y-2">
          <textarea
            value={newCommentText}
            onChange={(e) => setNewCommentText(e.target.value)}
            placeholder="Add a comment..."
            className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 resize-none"
            rows={2}
          />
          <div className="flex justify-end">
            <button
              onClick={() => {
                if (newCommentText.trim()) {
                  addCommentMut.mutate({ body: newCommentText.trim() });
                }
              }}
              disabled={!newCommentText.trim() || addCommentMut.isPending}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {addCommentMut.isPending ? (
                <Loader2 className="w-3 h-3 animate-spin" />
              ) : (
                <MessageSquare className="w-3 h-3" />
              )}
              Comment
            </button>
          </div>
        </div>
      </div>

      {/* ── Comments List ── */}
      {sorted.length === 0 && !isLoading && (
        <div className="text-center py-8">
          <MessageSquare className="w-8 h-8 text-gray-300 mx-auto mb-2" />
          <p className="text-sm text-gray-500">No comments yet</p>
          <p className="text-xs text-gray-400 mt-1">Start the discussion above.</p>
        </div>
      )}

      <div className="space-y-3">
        {sorted.map((comment) => (
          <React.Fragment key={comment.comment_id}>
            {/* ── Comment Card ── */}
            <motion.div
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              className={`group flex items-start gap-3 ${
                isSystemEvent(comment) ? "opacity-80" : ""
              }`}
            >
              {/* Avatar */}
              <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 text-[11px] font-semibold ${
                isSystemEvent(comment)
                  ? "bg-gray-100 text-gray-500"
                  : getActorColor(comment.author_id)
              }`}>
                {isSystemEvent(comment)
                  ? <Clock className="w-4 h-4" />
                  : getActorInitials(comment.author_name || comment.author_id)
                }
              </div>

              {/* Content */}
              <div className="flex-1 min-w-0">
                <div className={`rounded-lg px-3 py-2 ${
                  isSystemEvent(comment)
                    ? "bg-gray-50 border border-gray-100"
                    : "bg-white border border-gray-200"
                }`}>
                  {/* Header */}
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-xs font-semibold text-navy-900">
                      {isSystemEvent(comment) ? "System" : (comment.author_name || comment.author_id)}
                    </span>
                    {isSystemEvent(comment) && (
                      <span className="text-[9px] font-medium text-gray-500 bg-gray-200 px-1.5 py-0.5 rounded">
                        event
                      </span>
                    )}
                    <span className="text-[10px] text-gray-400 ml-auto">
                      {formatTimeAgo(comment.created_at)}
                    </span>
                  </div>

                  {/* Body */}
                  <p className="text-sm text-gray-700 whitespace-pre-wrap">{comment.body}</p>
                </div>

                {/* Reply Button */}
                <button
                  onClick={() => {
                    setReplyTo(replyTo === comment.comment_id ? null : comment.comment_id);
                    setReplyText("");
                  }}
                  className="inline-flex items-center gap-1 text-[10px] text-gray-400 hover:text-blue-600 mt-1 ml-1 transition-colors"
                >
                  <Reply className="w-3 h-3" />
                  Reply
                </button>

                {/* Reply Input */}
                <AnimatePresence>
                  {replyTo === comment.comment_id && (
                    <motion.div
                      initial={{ opacity: 0, height: 0 }}
                      animate={{ opacity: 1, height: "auto" }}
                      exit={{ opacity: 0, height: 0 }}
                      className="ml-4 mt-2"
                    >
                      <div className="flex items-start gap-2">
                        <div className="w-6 h-6 rounded-full bg-gray-200 flex items-center justify-center flex-shrink-0">
                          <User className="w-3 h-3 text-gray-500" />
                        </div>
                        <div className="flex-1 space-y-1.5">
                          <textarea
                            value={replyText}
                            onChange={(e) => setReplyText(e.target.value)}
                            placeholder="Write a reply..."
                            className="w-full px-2.5 py-1.5 text-xs border border-gray-300 rounded-lg focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 resize-none"
                            rows={2}
                            autoFocus
                          />
                          <div className="flex justify-end gap-1.5">
                            <button
                              onClick={() => setReplyTo(null)}
                              className="px-2 py-1 text-[10px] font-medium text-gray-600 hover:text-gray-900"
                            >
                              Cancel
                            </button>
                            <button
                              onClick={() => {
                                if (replyText.trim()) {
                                  addCommentMut.mutate({
                                    body: replyText.trim(),
                                    parentCommentId: comment.comment_id,
                                  });
                                }
                              }}
                              disabled={!replyText.trim() || addCommentMut.isPending}
                              className="px-2 py-1 text-[10px] font-medium rounded-lg bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50 transition-colors"
                            >
                              {addCommentMut.isPending ? "Posting..." : "Reply"}
                            </button>
                          </div>
                        </div>
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            </motion.div>

            {/* ── Replies ── */}
            {replies(comment.comment_id).map((reply) => (
              <motion.div
                key={reply.comment_id}
                initial={{ opacity: 0, x: 8 }}
                animate={{ opacity: 1, x: 0 }}
                className="flex items-start gap-3 ml-10"
              >
                <div className={`w-7 h-7 rounded-full flex items-center justify-center flex-shrink-0 text-[10px] font-semibold ${
                  isSystemEvent(reply)
                    ? "bg-gray-100 text-gray-500"
                    : getActorColor(reply.author_id)
                }`}>
                  {isSystemEvent(reply)
                    ? <Clock className="w-3 h-3" />
                    : getActorInitials(reply.author_name || reply.author_id)
                  }
                </div>
                <div className="flex-1 min-w-0">
                  <div className="rounded-lg px-3 py-2 bg-white border border-gray-200">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-xs font-semibold text-navy-900">
                        {reply.author_name || reply.author_id}
                      </span>
                      <span className="text-[10px] text-gray-400 ml-auto">
                        {formatTimeAgo(reply.created_at)}
                      </span>
                    </div>
                    <p className="text-sm text-gray-700 whitespace-pre-wrap">{reply.body}</p>
                  </div>
                </div>
              </motion.div>
            ))}
          </React.Fragment>
        ))}
      </div>
    </div>
  );
}

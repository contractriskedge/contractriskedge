/**
 * NotificationCenter — in-app notification panel with unread state, 
 * action links, and severity-based styling.
 *
 * Connected to GET /api/v1/notifications backend.
 */

"use client";

import React, { useState, useCallback } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { motion, AnimatePresence } from "framer-motion";
import { useRouter } from "next/navigation";
import {
  Bell, BellRing, CheckCheck, X, AlertTriangle, Info,
  ArrowRight, Loader2, Mail, MailOpen,
} from "lucide-react";
import { api } from "@/services/api/client";
import { getGlobalConnectionState } from "@/services/hooks/useAdaptivePolling";

// ── Types ────────────────────────────────────────────────────────

export interface NotificationItem {
  notification_id: string;
  type: string;
  title: string;
  body: string | null;
  severity: string;
  entity_type: string | null;
  entity_id: string | null;
  action_url: string | null;
  is_read: boolean;
  created_at: string;
}

export interface NotificationsResponse {
  data: NotificationItem[];
  pagination: { total: number; page: number; page_size: number; total_pages: number };
}

// ── Hooks ────────────────────────────────────────────────────────

export function useNotifications(unreadOnly = false) {
  return useQuery({
    queryKey: ["notifications", { unreadOnly }],
    queryFn: () => {
      const params = unreadOnly ? "?unread_only=true&page_size=50" : "?page_size=50";
      return api.get<NotificationsResponse>(`/notifications${params}`);
    },
    staleTime: 30_000,
    gcTime: 5 * 60_000,
    refetchInterval: (query) => {
      // WebSocket-aware polling: when connected, poll less frequently
      const connState = getGlobalConnectionState();
      if (connState === "connected") return 120_000; // Every 2 min when WS connected
      if (connState === "reconnecting") return 15_000; // Every 15s during reconnect
      if (query.state.data) return 60_000; // Every 1 min with data
      return 30_000; // Every 30s without data
    },
  });
}

export function useUnreadCount() {
  return useQuery({
    queryKey: ["notifications", "unread-count"],
    queryFn: () => api.get<NotificationsResponse>("/notifications?unread_only=true&page_size=1")
      .then((res) => res.pagination?.total ?? 0),
    staleTime: 15_000,
    gcTime: 30_000,
    refetchInterval: (query) => {
      const connState = getGlobalConnectionState();
      if (connState === "connected") return 120_000;
      if (connState === "reconnecting") return 15_000;
      if (query.state.data) return 30_000;
      return 15_000;
    },
  });
}

export function useMarkAsRead() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (notificationId: string) =>
      api.post(`/notifications/${notificationId}/read`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["notifications"] });
    },
  });
}

export function useMarkAllAsRead() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => api.post("/notifications/read-all"),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["notifications"] });
    },
  });
}

// ── Severity Styling ─────────────────────────────────────────────

const severityStyles: Record<string, { dot: string; bg: string; icon: React.ReactNode }> = {
  critical: { dot: "bg-red-500", bg: "bg-red-50 border-red-200", icon: <AlertTriangle className="w-4 h-4 text-red-500" /> },
  high: { dot: "bg-orange-500", bg: "bg-orange-50 border-orange-200", icon: <AlertTriangle className="w-4 h-4 text-orange-500" /> },
  medium: { dot: "bg-amber-500", bg: "bg-amber-50 border-amber-200", icon: <Info className="w-4 h-4 text-amber-500" /> },
  low: { dot: "bg-blue-500", bg: "bg-blue-50 border-blue-200", icon: <Info className="w-4 h-4 text-blue-500" /> },
  info: { dot: "bg-gray-400", bg: "bg-gray-50 border-gray-200", icon: <Bell className="w-4 h-4 text-gray-400" /> },
};

// ── Notification Bell Button ─────────────────────────────────────

export function NotificationBell() {
  const router = useRouter();
  const [isOpen, setIsOpen] = useState(false);
  const { data: unreadCount } = useUnreadCount();
  const { data: notifData, isLoading } = useNotifications();
  const markAsRead = useMarkAsRead();
  const markAllAsRead = useMarkAllAsRead();

  const notifications = notifData?.data ?? [];

  const handleMarkRead = useCallback((id: string) => {
    markAsRead.mutate(id);
  }, [markAsRead]);

  /** Navigate to the notification's target within the SPA.
   *  The backend sends action_url like "/reviews/{review_id}".
   *  Instead of <a href> (which causes a 404 since there's no
   *  Next.js route for /reviews/[id]), we dispatch a custom event
   *  that the DashboardLayout listens for, or navigate via router. */
  const handleView = useCallback((notif: NotificationItem) => {
    if (!notif.action_url) return;

    // Mark as read
    if (!notif.is_read) {
      markAsRead.mutate(notif.notification_id);
    }

    // Parse the action URL to determine navigation target
    const url = notif.action_url;
    setIsOpen(false);

    // Match /reviews/{reviewId} → navigate within SPA via custom event
    const reviewMatch = url.match(/^\/reviews\/([^/]+)/);
    if (reviewMatch) {
      const reviewId = reviewMatch[1];
      window.dispatchEvent(
        new CustomEvent("navigate-to-review", { detail: { reviewId } })
      );
      return;
    }

    // Match /contracts/{contractId} → use Next.js router
    const contractMatch = url.match(/^\/contracts\/([^/]+)/);
    if (contractMatch) {
      router.push(`/contracts/${contractMatch[1]}`);
      return;
    }

    // For other URLs, try router push or fall back to window location
    try {
      router.push(url);
    } catch {
      window.open(url, "_blank", "noopener,noreferrer");
    }
  }, [markAsRead, router]);

  const count = typeof unreadCount === 'number' ? unreadCount : 0;

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="relative p-2 rounded-lg hover:bg-gray-100 transition-colors"
        title="Notifications"
      >
        {count > 0 ? (
          <BellRing className="w-5 h-5 text-amber-500" />
        ) : (
          <Bell className="w-5 h-5 text-gray-500" />
        )}
        {count > 0 && (
          <span className="absolute -top-0.5 -right-0.5 inline-flex items-center justify-center w-4 h-4 text-[8px] font-bold text-white bg-red-500 rounded-full">
            {count > 99 ? "99+" : count}
          </span>
        )}
      </button>

      <AnimatePresence>
        {isOpen && (
          <>
            <div className="fixed inset-0 z-30" onClick={() => setIsOpen(false)} />
            <motion.div
              initial={{ opacity: 0, y: -4, scale: 0.95 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: -4, scale: 0.95 }}
              className="absolute right-0 top-full mt-2 w-80 bg-white border border-gray-200 rounded-xl shadow-xl z-40 max-h-96 overflow-hidden"
            >
              {/* Header */}
              <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200">
                <div className="flex items-center gap-2">
                  <Bell className="w-4 h-4 text-gray-500" />
                  <h3 className="text-xs font-semibold text-navy-900">Notifications</h3>
                  {count > 0 && (
                    <span className="inline-flex items-center px-1.5 py-0.5 rounded-full text-[9px] font-medium bg-red-100 text-red-700">
                      {count} new
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-1">
                  {count > 0 && (
                    <button
                      onClick={() => markAllAsRead.mutate()}
                      className="p-1 rounded hover:bg-gray-100 text-gray-400 hover:text-blue-600"
                      title="Mark all as read"
                    >
                      <CheckCheck className="w-3.5 h-3.5" />
                    </button>
                  )}
                  <button onClick={() => setIsOpen(false)} className="p-1 rounded hover:bg-gray-100 text-gray-400">
                    <X className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>

              {/* List */}
              <div className="overflow-y-auto max-h-80">
                {isLoading ? (
                  <div className="flex justify-center py-8">
                    <Loader2 className="w-5 h-5 text-gray-400 animate-spin" />
                  </div>
                ) : notifications.length === 0 ? (
                  <div className="flex flex-col items-center py-8 text-center">
                    <Bell className="w-8 h-8 text-gray-300 mb-2" />
                    <p className="text-xs text-gray-500">No notifications yet</p>
                    <p className="text-[10px] text-gray-400 mt-1">Notifications will appear here as events occur.</p>
                  </div>
                ) : (
                  <div className="divide-y divide-gray-100">
                    {notifications.map((notif) => {
                      const styles = severityStyles[notif.severity] || severityStyles.info;
                      return (
                        <div
                          key={notif.notification_id}
                          className={`px-4 py-3 flex gap-3 transition-colors ${
                            !notif.is_read ? "bg-blue-50/50" : "hover:bg-gray-50"
                          }`}
                        >
                          <div className="mt-0.5 flex-shrink-0">{styles.icon}</div>
                          <div className="flex-1 min-w-0">
                            <div className="flex items-start justify-between gap-1">
                              <p className={`text-xs font-medium ${!notif.is_read ? "text-navy-900" : "text-gray-600"}`}>
                                {notif.title}
                              </p>
                              {!notif.is_read && (
                                <button
                                  onClick={() => handleMarkRead(notif.notification_id)}
                                  className="p-0.5 rounded hover:bg-blue-100 text-blue-400 hover:text-blue-600 flex-shrink-0"
                                >
                                  <CheckCheck className="w-3 h-3" />
                                </button>
                              )}
                            </div>
                            {notif.body && (
                              <p className="text-[10px] text-gray-500 mt-0.5 line-clamp-2">{notif.body}</p>
                            )}
                            <div className="flex items-center gap-2 mt-1">
                              <span className="text-[9px] text-gray-400">
                                {formatTimeAgo(notif.created_at)}
                              </span>
                              {notif.action_url && (
                                <button
                                  onClick={() => handleView(notif)}
                                  className="inline-flex items-center gap-0.5 text-[9px] font-medium text-blue-600 hover:text-blue-700"
                                >
                                  View <ArrowRight className="w-2.5 h-2.5" />
                                </button>
                              )}
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>

              {/* Footer */}
              {notifications.length > 0 && (
                <div className="px-4 py-2 border-t border-gray-100 bg-gray-50 text-center">
                  <button
                    onClick={() => { setIsOpen(false); }}
                    className="text-[10px] font-medium text-gray-500 hover:text-gray-700"
                  >
                    View All Notifications
                  </button>
                </div>
              )}
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </div>
  );
}

// ── Time formatting ──────────────────────────────────────────────

function formatTimeAgo(ts: string): string {
  const d = new Date(ts);
  const now = new Date();
  const diff = now.getTime() - d.getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "Just now";
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  if (days < 7) return `${days}d ago`;
  return d.toLocaleDateString();
}

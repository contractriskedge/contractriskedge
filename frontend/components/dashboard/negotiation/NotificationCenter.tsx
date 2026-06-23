"use client";

import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Bell, MessageSquare, UserPlus, AlertTriangle, CheckCircle,
  ArrowUpCircle, X, Loader2, Clock,
} from "lucide-react";

// ── Types ────────────────────────────────────────────────────────

export interface Notification {
  id: string;
  type: "assignment" | "comment" | "mention" | "escalation" | "approval" | "sla_breach";
  title: string;
  message: string;
  timestamp: string;
  read: boolean;
  link?: string;
  actor?: string;
  actorAvatar?: string;
}

interface NotificationCenterProps {
  notifications: Notification[];
  onMarkRead: (id: string) => void;
  onMarkAllRead: () => void;
  onNotificationClick: (notification: Notification) => void;
}

// ── Icon mapping ─────────────────────────────────────────────────

const NOTIFICATION_ICONS: Record<string, React.ReactNode> = {
  assignment: <UserPlus className="w-3.5 h-3.5" />,
  comment: <MessageSquare className="w-3.5 h-3.5" />,
  mention: <MessageSquare className="w-3.5 h-3.5 text-purple-500" />,
  escalation: <ArrowUpCircle className="w-3.5 h-3.5 text-red-500" />,
  approval: <CheckCircle className="w-3.5 h-3.5 text-green-500" />,
  sla_breach: <AlertTriangle className="w-3.5 h-3.5 text-red-500" />,
};

const NOTIFICATION_COLORS: Record<string, string> = {
  assignment: "bg-blue-50 border-blue-200",
  comment: "bg-gray-50 border-gray-200",
  mention: "bg-purple-50 border-purple-200",
  escalation: "bg-red-50 border-red-200",
  approval: "bg-green-50 border-green-200",
  sla_breach: "bg-red-50 border-red-200",
};

// ── Component ────────────────────────────────────────────────────

export function NotificationBell({
  notifications,
  onMarkRead,
  onMarkAllRead,
  onNotificationClick,
}: NotificationCenterProps) {
  const [isOpen, setIsOpen] = useState(false);

  const unreadCount = notifications.filter((n) => !n.read).length;

  return (
    <div className="relative">
      {/* Bell button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="relative p-1.5 rounded-lg hover:bg-gray-100 transition-colors"
        title="Notifications"
      >
        <Bell className="w-4 h-4 text-gray-500" />
        {unreadCount > 0 && (
          <span className="absolute -top-0.5 -right-0.5 w-4 h-4 flex items-center justify-center bg-red-500 text-white text-[8px] font-bold rounded-full">
            {unreadCount > 9 ? "9+" : unreadCount}
          </span>
        )}
      </button>

      {/* Dropdown */}
      <AnimatePresence>
        {isOpen && (
          <>
            {/* Backdrop */}
            <div className="fixed inset-0 z-40" onClick={() => setIsOpen(false)} />

            {/* Panel */}
            <motion.div
              initial={{ opacity: 0, y: -8, scale: 0.95 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: -8, scale: 0.95 }}
              className="absolute right-0 top-full mt-1 w-80 bg-white rounded-xl shadow-xl border border-gray-200 z-50 overflow-hidden"
            >
              {/* Header */}
              <div className="flex items-center justify-between px-3 py-2 border-b border-gray-100">
                <h3 className="text-[11px] font-semibold text-navy-900">Notifications</h3>
                <div className="flex items-center gap-1">
                  {unreadCount > 0 && (
                    <button
                      onClick={onMarkAllRead}
                      className="text-[9px] text-purple-600 hover:text-purple-700"
                    >
                      Mark all read
                    </button>
                  )}
                  <button onClick={() => setIsOpen(false)} className="text-gray-400 hover:text-gray-600">
                    <X className="w-3 h-3" />
                  </button>
                </div>
              </div>

              {/* List */}
              <div className="max-h-80 overflow-y-auto">
                {notifications.length === 0 ? (
                  <div className="text-center py-8 text-gray-400">
                    <Bell className="w-5 h-5 mx-auto mb-1 opacity-50" />
                    <p className="text-[10px]">No notifications</p>
                  </div>
                ) : (
                  notifications.map((notification) => (
                    <button
                      key={notification.id}
                      onClick={() => {
                        onNotificationClick(notification);
                        if (!notification.read) onMarkRead(notification.id);
                        setIsOpen(false);
                      }}
                      className={`w-full text-left px-3 py-2 border-b border-gray-50 hover:bg-gray-50 transition-colors ${
                        !notification.read ? "bg-purple-50/30" : ""
                      }`}
                    >
                      <div className="flex items-start gap-2">
                        <div className={`mt-0.5 w-6 h-6 rounded-full flex items-center justify-center flex-shrink-0 ${
                          NOTIFICATION_COLORS[notification.type] || "bg-gray-100"
                        }`}>
                          {NOTIFICATION_ICONS[notification.type] || <Bell className="w-3 h-3" />}
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-1">
                            <span className="text-[10px] font-semibold text-navy-900 truncate">
                              {notification.title}
                            </span>
                            {!notification.read && (
                              <span className="w-1.5 h-1.5 rounded-full bg-purple-500 flex-shrink-0" />
                            )}
                          </div>
                          <p className="text-[9px] text-gray-600 mt-0.5 line-clamp-2">{notification.message}</p>
                          <div className="flex items-center gap-1 mt-0.5 text-[8px] text-gray-400">
                            <Clock className="w-2 h-2" />
                            <span>{formatRelativeTime(notification.timestamp)}</span>
                            {notification.actor && (
                              <>
                                <span>·</span>
                                <span>{notification.actor}</span>
                              </>
                            )}
                          </div>
                        </div>
                      </div>
                    </button>
                  ))
                )}
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </div>
  );
}

// ── Relative time formatter ──────────────────────────────────────

function formatRelativeTime(timestamp: string): string {
  const now = Date.now();
  const then = new Date(timestamp).getTime();
  const diffMs = now - then;
  const diffSec = Math.floor(diffMs / 1000);
  const diffMin = Math.floor(diffSec / 60);
  const diffHour = Math.floor(diffMin / 60);
  const diffDay = Math.floor(diffHour / 24);

  if (diffSec < 60) return "just now";
  if (diffMin < 60) return `${diffMin}m ago`;
  if (diffHour < 24) return `${diffHour}h ago`;
  if (diffDay < 7) return `${diffDay}d ago`;
  return new Date(timestamp).toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

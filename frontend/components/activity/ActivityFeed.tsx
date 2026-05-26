/**
 * ActivityFeed — real-time operational activity stream.
 *
 * Shows a chronological feed of platform events:
 * - Notifications sent
 * - Jobs completed/failed
 * - Reviews updated
 * - Uploads completed
 * - AI analyses finished
 * - Recommendations generated
 *
 * Connected to the WebSocket event stream with REST fallback.
 */

"use client";

import React, { useState, useEffect, useCallback, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Bell, CheckCircle, XCircle, RefreshCw, Upload, Brain,
  AlertTriangle, FileText, UserPlus, Download, Clock,
  Loader2, ArrowRight, Filter,
} from "lucide-react";

// ── Types ────────────────────────────────────────────────────────

export interface ActivityEvent {
  id: string;
  type: string;
  title: string;
  description?: string;
  severity: "info" | "success" | "warning" | "error";
  timestamp: string;
  actionUrl?: string;
}

// ── Event Type Config ────────────────────────────────────────────

const eventConfig: Record<string, { icon: React.ReactNode; color: string; label: string }> = {
  "notification.created": { icon: <Bell className="w-3.5 h-3.5" />, color: "bg-blue-500", label: "Notification" },
  "job.completed": { icon: <CheckCircle className="w-3.5 h-3.5" />, color: "bg-green-500", label: "Job Complete" },
  "job.failed": { icon: <XCircle className="w-3.5 h-3.5" />, color: "bg-red-500", label: "Job Failed" },
  "job.updated": { icon: <RefreshCw className="w-3.5 h-3.5" />, color: "bg-amber-500", label: "Job Updated" },
  "review.status_changed": { icon: <FileText className="w-3.5 h-3.5" />, color: "bg-indigo-500", label: "Review" },
  "upload.completed": { icon: <Upload className="w-3.5 h-3.5" />, color: "bg-cyan-500", label: "Upload" },
  "upload.failed": { icon: <AlertTriangle className="w-3.5 h-3.5" />, color: "bg-red-500", label: "Upload Failed" },
  "ai.completed": { icon: <Brain className="w-3.5 h-3.5" />, color: "bg-purple-500", label: "AI Complete" },
  "ai.failed": { icon: <AlertTriangle className="w-3.5 h-3.5" />, color: "bg-orange-500", label: "AI Failed" },
  "recommendation.created": { icon: <AlertTriangle className="w-3.5 h-3.5" />, color: "bg-amber-500", label: "Recommendation" },
  "export.completed": { icon: <Download className="w-3.5 h-3.5" />, color: "bg-teal-500", label: "Export" },
};

const defaultEvent = { icon: <Clock className="w-3.5 h-3.5" />, color: "bg-gray-400", label: "Event" };

// ── Activity Feed Component ──────────────────────────────────────

interface ActivityFeedProps {
  maxItems?: number;
  showFilter?: boolean;
  className?: string;
}

export function ActivityFeed({ maxItems = 50, showFilter = true, className = "" }: ActivityFeedProps) {
  const [events, setEvents] = useState<ActivityEvent[]>([]);
  const [filter, setFilter] = useState<string>("all");
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectRef = useRef<number>(0);

  // ── Connect to WebSocket ───────────────────────────────────────
  useEffect(() => {
    const token = typeof window !== "undefined" ? localStorage.getItem("auth_token") : null;
    if (!token) return;

    let ws: WebSocket | null = null;
    let reconnectTimer: ReturnType<typeof setTimeout>;

    function connect() {
      const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
      const host = window.location.host;
      ws = new WebSocket(`${protocol}//${host}/api/v1/ws/events`);

      ws.onopen = () => {
        ws?.send(JSON.stringify({ type: "auth", token }));
        setConnected(true);
        reconnectRef.current = 0;
      };

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);
          if (msg.type === "connected" || msg.type === "heartbeat" || msg.type === "pong") return;

          const newEvent: ActivityEvent = {
            id: `${msg.type}-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
            type: msg.type,
            title: msg.data?.title || msg.type,
            description: msg.data?.message || msg.data?.description,
            severity: msg.data?.severity === "critical" || msg.type.includes("failed") ? "error"
              : msg.type.includes("completed") ? "success"
              : msg.type.includes("warning") ? "warning" : "info",
            timestamp: new Date().toISOString(),
            actionUrl: msg.data?.action_url,
          };

          setEvents((prev) => [newEvent, ...prev].slice(0, maxItems));
        } catch {}
      };

      ws.onclose = () => {
        setConnected(false);
        // Reconnect with backoff
        const delay = Math.min(1000 * Math.pow(2, reconnectRef.current), 30000);
        reconnectRef.current++;
        reconnectTimer = setTimeout(connect, delay);
      };

      ws.onerror = () => {
        ws?.close();
      };
    }

    connect();

    return () => {
      ws?.close();
      clearTimeout(reconnectTimer);
    };
  }, [maxItems]);

  // ── Filtered events ────────────────────────────────────────────
  const filteredEvents = filter === "all"
    ? events
    : events.filter((e) => e.type.startsWith(filter));

  const eventTypes = Array.from(new Set(events.map((e) => {
    const parts = e.type.split(".");
    return parts[0];
  })));

  return (
    <div className={`bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden ${className}`}>
      {/* Header */}
      <div className="px-4 py-3 border-b border-gray-100 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Clock className="w-4 h-4 text-gray-500" />
          <h3 className="text-xs font-semibold text-navy-900">Activity Feed</h3>
          {connected && (
            <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-full text-[8px] font-medium bg-green-100 text-green-700">
              <span className="w-1.5 h-1.5 rounded-full bg-green-500" />
              Live
            </span>
          )}
          {!connected && events.length > 0 && (
            <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-full text-[8px] font-medium bg-gray-100 text-gray-500">
              <span className="w-1.5 h-1.5 rounded-full bg-gray-400" />
              Offline
            </span>
          )}
        </div>
        <span className="text-[10px] text-gray-400">{events.length} events</span>
      </div>

      {/* Filter bar */}
      {showFilter && eventTypes.length > 1 && (
        <div className="px-4 py-2 border-b border-gray-100 flex flex-wrap gap-1">
          <button
            onClick={() => setFilter("all")}
            className={`px-2 py-0.5 rounded text-[9px] font-medium transition-colors ${
              filter === "all" ? "bg-navy-700 text-white" : "bg-gray-100 text-gray-600 hover:bg-gray-200"
            }`}
          >
            All
          </button>
          {eventTypes.map((type) => (
            <button
              key={type}
              onClick={() => setFilter(type)}
              className={`px-2 py-0.5 rounded text-[9px] font-medium transition-colors capitalize ${
                filter === type ? "bg-navy-700 text-white" : "bg-gray-100 text-gray-600 hover:bg-gray-200"
              }`}
            >
              {type.replace(/_/g, " ")}
            </button>
          ))}
        </div>
      )}

      {/* Event list */}
      <div className="divide-y divide-gray-100 max-h-96 overflow-y-auto">
        {filteredEvents.length === 0 ? (
          <div className="flex flex-col items-center py-8 text-center">
            <Clock className="w-8 h-8 text-gray-300 mb-2" />
            <p className="text-xs text-gray-500">No activity yet</p>
            <p className="text-[10px] text-gray-400 mt-1">Events will appear here in real time.</p>
          </div>
        ) : (
          <AnimatePresence initial={false}>
            {filteredEvents.map((event) => {
              const cfg = eventConfig[event.type] || defaultEvent;
              return (
                <motion.div
                  key={event.id}
                  initial={{ opacity: 0, x: -8 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, height: 0 }}
                  transition={{ duration: 0.2 }}
                  className="px-4 py-2.5 flex gap-3 hover:bg-gray-50 transition-colors"
                >
                  <div className={`mt-0.5 w-6 h-6 rounded-full flex items-center justify-center text-white flex-shrink-0 ${cfg.color}`}>
                    {cfg.icon}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-1.5">
                      <span className="text-[9px] font-medium text-gray-400 uppercase">{cfg.label}</span>
                      <span className="text-[9px] text-gray-400">{formatTimeAgo(event.timestamp)}</span>
                    </div>
                    <p className="text-xs font-medium text-navy-900 mt-0.5">{event.title}</p>
                    {event.description && (
                      <p className="text-[10px] text-gray-500 mt-0.5 line-clamp-2">{event.description}</p>
                    )}
                    {event.actionUrl && (
                      <a href={event.actionUrl} className="inline-flex items-center gap-0.5 text-[9px] font-medium text-blue-600 hover:text-blue-700 mt-0.5">
                        View <ArrowRight className="w-2.5 h-2.5" />
                      </a>
                    )}
                  </div>
                </motion.div>
              );
            })}
          </AnimatePresence>
        )}
      </div>
    </div>
  );
}

// ── Time formatting ──────────────────────────────────────────────

function formatTimeAgo(ts: string): string {
  const d = new Date(ts);
  const now = new Date();
  const diff = now.getTime() - d.getTime();
  const secs = Math.floor(diff / 1000);
  if (secs < 10) return "Just now";
  if (secs < 60) return `${secs}s ago`;
  const mins = Math.floor(secs / 60);
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  return d.toLocaleDateString();
}

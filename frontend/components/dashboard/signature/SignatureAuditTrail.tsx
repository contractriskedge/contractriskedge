"use client";

import React from "react";
import { motion } from "framer-motion";
import {
  History, Send, Eye, CheckCircle, XCircle, Clock, AlertTriangle,
} from "lucide-react";
import type { AuditEvent } from "./types";

interface SignatureAuditTrailProps {
  events: AuditEvent[];
  loading?: boolean;
}

const EVENT_ICONS: Record<string, React.ReactNode> = {
  sent: <Send className="w-3 h-3" />,
  viewed: <Eye className="w-3 h-3" />,
  signed: <CheckCircle className="w-3 h-3" />,
  completed: <CheckCircle className="w-3 h-3" />,
  declined: <XCircle className="w-3 h-3" />,
  expired: <Clock className="w-3 h-3" />,
  voided: <XCircle className="w-3 h-3" />,
  reminder_sent: <Send className="w-3 h-3" />,
  error: <AlertTriangle className="w-3 h-3" />,
};

const EVENT_COLORS: Record<string, string> = {
  sent: "bg-blue-500",
  viewed: "bg-amber-500",
  signed: "bg-green-500",
  completed: "bg-emerald-500",
  declined: "bg-red-500",
  expired: "bg-red-500",
  voided: "bg-gray-500",
  reminder_sent: "bg-purple-500",
  error: "bg-red-500",
};

export function SignatureAuditTrail({ events, loading }: SignatureAuditTrailProps) {
  if (loading) {
    return (
      <div className="space-y-2">
        {[1, 2, 3].map((i) => (
          <div key={i} className="flex gap-2 animate-pulse">
            <div className="w-5 h-5 rounded-full bg-gray-200" />
            <div className="flex-1">
              <div className="h-3 bg-gray-200 rounded w-1/2 mb-1" />
              <div className="h-2 bg-gray-200 rounded w-1/4" />
            </div>
          </div>
        ))}
      </div>
    );
  }

  if (events.length === 0) {
    return (
      <div className="text-center py-6">
        <History className="w-6 h-6 text-gray-300 mx-auto mb-1" />
        <p className="text-[10px] text-gray-500">No audit events yet</p>
      </div>
    );
  }

  return (
    <div className="relative">
      <div className="absolute left-2.5 top-2 bottom-2 w-0.5 bg-gray-100" />
      <div className="space-y-2">
        {events.map((event, i) => (
          <motion.div
            key={event.id}
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: i * 0.05 }}
            className="flex gap-2 items-start"
          >
            <div className={`w-5 h-5 rounded-full flex items-center justify-center flex-shrink-0 z-10 mt-0.5 text-white ${EVENT_COLORS[event.eventType] || "bg-gray-400"}`}>
              {EVENT_ICONS[event.eventType] || <Clock className="w-2.5 h-2.5" />}
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-1.5">
                <span className="text-[10px] font-semibold text-navy-900 capitalize">
                  {event.eventType.replace(/_/g, " ")}
                </span>
                {event.actorEmail && (
                  <span className="text-[9px] text-gray-400">{event.actorEmail}</span>
                )}
                <span className="text-[8px] text-gray-400 ml-auto">
                  {new Date(event.createdAt).toLocaleTimeString("en-US", {
                    month: "short", day: "numeric", hour: "2-digit", minute: "2-digit",
                  })}
                </span>
              </div>
              {event.details && Object.keys(event.details).length > 0 && (
                <p className="text-[9px] text-gray-500 mt-0.5">
                  {JSON.stringify(event.details).substring(0, 100)}
                </p>
              )}
            </div>
          </motion.div>
        ))}
      </div>
    </div>
  );
}

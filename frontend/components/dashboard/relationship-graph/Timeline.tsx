"use client";

import React from "react";
import { motion } from "framer-motion";
import { Clock, FileEdit, RefreshCw, Shield, PenSquare, AlertTriangle, ClipboardCheck } from "lucide-react";
import type { TimelineEvent } from "./types";

const typeConfig: Record<string, { icon: React.ReactNode; color: string; bg: string }> = {
  amendment: { icon: <FileEdit className="w-3 h-3" />, color: "text-amber-600", bg: "bg-amber-50" },
  renewal: { icon: <RefreshCw className="w-3 h-3" />, color: "text-green-600", bg: "bg-green-50" },
  signature: { icon: <PenSquare className="w-3 h-3" />, color: "text-purple-600", bg: "bg-purple-50" },
  review: { icon: <Shield className="w-3 h-3" />, color: "text-blue-600", bg: "bg-blue-50" },
  compliance: { icon: <Shield className="w-3 h-3" />, color: "text-teal-600", bg: "bg-teal-50" },
  obligation: { icon: <ClipboardCheck className="w-3 h-3" />, color: "text-red-600", bg: "bg-red-50" },
};

export function RelationshipTimeline({ events }: { events: TimelineEvent[] }) {
  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2"><Clock className="w-4 h-4 text-navy-700" /><h3 className="text-xs font-semibold text-navy-900">Contract Timeline</h3></div>
      <div className="space-y-0">
        {events.map((event, i) => {
          const cfg = typeConfig[event.type] || typeConfig.review;
          return (
            <motion.div key={event.id} initial={{ opacity: 0, x: -6 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: i * 0.05 }}
              className="flex items-start gap-3 pb-3 last:pb-0">
              <div className="flex flex-col items-center">
                <div className={`w-7 h-7 rounded-full ${cfg.bg} flex items-center justify-center flex-shrink-0`}>{cfg.icon}</div>
                {i < events.length - 1 && <div className="w-px flex-1 bg-gray-200 mt-1" />}
              </div>
              <div className="flex-1 min-w-0 pt-0.5">
                <p className="text-[11px] font-semibold text-navy-900">{event.title}</p>
                <p className="text-[10px] text-gray-500 mt-0.5">{event.description}</p>
                <div className="flex items-center gap-2 mt-1">
                  <span className="text-[9px] text-gray-400">{event.date}</span>
                  {event.contracts.slice(0, 3).map((c) => (
                    <span key={c} className="text-[8px] font-mono px-1 py-0.5 rounded bg-gray-100 text-gray-500">{c}</span>
                  ))}
                </div>
              </div>
            </motion.div>
          );
        })}
      </div>
    </div>
  );
}

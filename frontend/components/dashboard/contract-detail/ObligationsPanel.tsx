"use client";

import React from "react";
import { Clock, CheckCircle, AlertTriangle, FileText, User, ChevronRight } from "lucide-react";
import type { Obligation, VersionRecord, ActivityEvent } from "./types";

export function ObligationsPanel({ obligations }: { obligations: Obligation[] }) {
  const overdue = obligations.filter((o) => o.status === "overdue").length;
  return (
    <div className="p-3 space-y-2">
      <div className="flex items-center justify-between">
        <h3 className="text-xs font-semibold text-navy-900">Obligations</h3>
        {overdue > 0 && <span className="text-[9px] font-medium text-red-600 bg-red-50 px-1.5 py-0.5 rounded">{overdue} overdue</span>}
      </div>
      {obligations.length === 0 ? (
        <p className="text-[10px] text-gray-400 text-center py-4">No obligations tracked for this clause</p>
      ) : (
        <div className="space-y-1.5">
          {obligations.map((o) => (
            <div key={o.id} className="flex items-start gap-2 p-2 bg-white border border-gray-100 rounded-lg">
              <div className={`w-5 h-5 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5 ${o.status === "completed" ? "bg-green-50" : o.status === "overdue" ? "bg-red-50" : "bg-yellow-50"}`}>
                {o.status === "completed" ? <CheckCircle className="w-3 h-3 text-green-500" /> :
                 o.status === "overdue" ? <AlertTriangle className="w-3 h-3 text-red-500" /> :
                 <Clock className="w-3 h-3 text-yellow-500" />}
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-[10px] font-medium text-gray-800">{o.description}</p>
                <div className="flex items-center gap-1.5 text-[8px] text-gray-400 mt-0.5">
                  <span>{o.type}</span><span>•</span><span>{o.owner}</span><span>•</span>
                  <span className={o.status === "overdue" ? "text-red-500" : ""}>Due {o.dueDate}</span>
                </div>
              </div>
              <span className={`text-[8px] font-medium px-1.5 py-0.5 rounded-full ${o.status === "completed" ? "bg-green-50 text-green-700" : o.status === "overdue" ? "bg-red-50 text-red-700" : "bg-yellow-50 text-yellow-700"}`}>{o.status}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export function VersionHistory({ versions }: { versions: VersionRecord[] }) {
  return (
    <div className="p-3 space-y-2">
      <h3 className="text-xs font-semibold text-navy-900">Version History</h3>
      <div className="space-y-1.5">
        {versions.map((v, i) => (
          <div key={v.id} className="flex items-start gap-2.5">
            <div className="flex flex-col items-center">
              <div className={`w-2.5 h-2.5 rounded-full ${v.isCurrent ? "bg-navy-700" : "bg-gray-300"}`} />
              {i < versions.length - 1 && <div className="w-px h-5 bg-gray-200" />}
            </div>
            <div className="flex-1 min-w-0 pb-1">
              <div className="flex items-center gap-1.5">
                <span className="text-[10px] font-semibold text-navy-900">v{v.version}</span>
                {v.isCurrent && <span className="text-[8px] font-medium px-1 py-0.5 rounded bg-navy-50 text-navy-700">Current</span>}
              </div>
              <p className="text-[9px] text-gray-500">{v.summary}</p>
              <p className="text-[8px] text-gray-400">{v.author} • {v.date} • {v.changes} changes</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export function ActivityTimeline({ events }: { events: ActivityEvent[] }) {
  return (
    <div className="p-3 space-y-2">
      <h3 className="text-xs font-semibold text-navy-900">Activity</h3>
      <div className="space-y-1.5">
        {events.map((e, i) => (
          <div key={e.id} className="flex items-start gap-2.5">
            <div className="flex flex-col items-center">
              <div className={`w-2 h-2 rounded-full ${e.type === "comment" ? "bg-blue-500" : e.type === "approval" ? "bg-green-500" : e.type === "ai_action" ? "bg-purple-500" : e.type === "version" ? "bg-orange-500" : "bg-gray-400"}`} />
              {i < events.length - 1 && <div className="w-px h-5 bg-gray-100" />}
            </div>
            <div className="flex-1 min-w-0 pb-1">
              <p className="text-[10px] font-medium text-gray-800">{e.action}</p>
              {e.details && <p className="text-[8px] text-gray-400">{e.details}</p>}
              <p className="text-[8px] text-gray-300 mt-0.5">{e.user} • {formatTime(e.timestamp)}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function formatTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const hrs = Math.floor(diff / 3600000);
  if (hrs < 1) return "just now"; if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

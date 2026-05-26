"use client";

import React from "react";
import { motion } from "framer-motion";
import { Brain, AlertTriangle, BarChart3, Activity, Clock, ChevronRight } from "lucide-react";
import type { AiGovernanceEvent } from "./types";

export function AiGovernanceCenter({ events }: { events: AiGovernanceEvent[] }) {
  const flagged = events.filter((e) => e.flagged);
  const avgConfidence = Math.round(events.reduce((s, e) => s + e.confidence, 0) / events.length);
  const avgLatency = Math.round(events.reduce((s, e) => s + e.latency, 0) / events.length);

  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
      <div className="px-4 py-3 border-b border-gray-100">
        <div className="flex items-center gap-2"><Brain className="w-4 h-4 text-navy-700" /><h3 className="text-xs font-semibold text-navy-900">AI Governance Center</h3></div>
      </div>
      <div className="grid grid-cols-3 divide-x divide-gray-100 border-b border-gray-100">
        {[
          { label: "Avg Confidence", value: `${avgConfidence}%`, color: avgConfidence > 85 ? "text-green-600" : "text-orange-600" },
          { label: "Avg Latency", value: `${avgLatency}ms`, color: avgLatency < 1000 ? "text-green-600" : "text-orange-600" },
          { label: "Flagged Queries", value: `${flagged.length}`, color: flagged.length > 3 ? "text-red-600" : "text-green-600" },
        ].map((stat) => (
          <div key={stat.label} className="text-center py-3"><p className="text-[10px] text-gray-500">{stat.label}</p><p className={`text-sm font-bold ${stat.color}`}>{stat.value}</p></div>
        ))}
      </div>
      <div className="divide-y divide-gray-50 max-h-[240px] overflow-y-auto">
        {events.slice(0, 10).map((e) => (
          <div key={e.id} className="flex items-center gap-2.5 px-4 py-2 hover:bg-gray-50 transition-colors">
            <div className={`w-6 h-6 rounded-full flex items-center justify-center ${e.flagged ? "bg-red-50" : "bg-green-50"}`}>
              {e.flagged ? <AlertTriangle className="w-3 h-3 text-red-500" /> : <Activity className="w-3 h-3 text-green-500" />}
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-1.5">
                <span className="text-[11px] font-medium text-gray-800">{e.queryType.replace(/_/g, " ")}</span>
                <span className="text-[9px] text-gray-400">{e.model}</span>
                {e.flagged && <span className="text-[9px] font-medium px-1 py-0.5 rounded bg-red-50 text-red-600">{e.flagType}</span>}
              </div>
              <div className="flex items-center gap-2 text-[9px] text-gray-400 mt-0.5">
                <span>{e.user}</span><span>{e.confidence}% conf.</span><span>{e.latency}ms</span><span>{e.tokens} tokens</span>
              </div>
            </div>
            <span className="text-[9px] text-gray-400">{formatTime(e.timestamp)}</span>
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

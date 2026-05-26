"use client";

import React from "react";
import { motion } from "framer-motion";
import { Activity, AlertTriangle, CheckCircle, XCircle, Clock, Server } from "lucide-react";
import type { SystemHealthMetric } from "./types";

export function SystemHealth({ metrics }: { metrics: SystemHealthMetric[] }) {
  const healthy = metrics.filter((m) => m.status === "healthy").length;
  const degraded = metrics.filter((m) => m.status === "degraded").length;
  const down = metrics.filter((m) => m.status === "down").length;

  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
      <div className="px-4 py-3 border-b border-gray-100">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2"><Activity className="w-4 h-4 text-navy-700" /><h3 className="text-xs font-semibold text-navy-900">System Health</h3></div>
          <div className="flex gap-2 text-[10px]">
            <span className="text-green-600 font-medium">● {healthy} healthy</span>
            {degraded > 0 && <span className="text-orange-600 font-medium">● {degraded} degraded</span>}
            {down > 0 && <span className="text-red-600 font-medium">● {down} down</span>}
          </div>
        </div>
      </div>
      <div className="divide-y divide-gray-50">
        {metrics.map((m) => (
          <div key={m.id} className="flex items-center gap-3 px-4 py-2.5 hover:bg-gray-50 transition-colors">
            <div className={`w-2 h-2 rounded-full ${m.status === "healthy" ? "bg-green-500" : m.status === "degraded" ? "bg-orange-500" : "bg-red-500"}`} />
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-1.5">
                <span className="text-[11px] font-medium text-gray-800">{m.service}</span>
                <span className={`text-[9px] font-medium px-1.5 py-0.5 rounded-full ${m.status === "healthy" ? "bg-green-50 text-green-700" : m.status === "degraded" ? "bg-orange-50 text-orange-700" : "bg-red-50 text-red-700"}`}>{m.status}</span>
              </div>
              <div className="flex items-center gap-3 text-[9px] text-gray-400 mt-0.5">
                <span>{m.uptime}% uptime</span><span>{m.latency}ms latency</span><span>{m.errorRate}% errors</span><span>{m.requestsPerMin.toLocaleString()} req/min</span><span>{m.region}</span>
              </div>
            </div>
            <span className="text-[9px] text-gray-400">Last incident: {m.lastIncident}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

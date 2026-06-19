"use client";

import React, { useState } from "react";
import { motion } from "framer-motion";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";
import { FileSearch, ChevronRight, AlertTriangle, Shield, User, Activity, Link, Database, Settings } from "lucide-react";
import type { AuditEvent, ComplianceCheck } from "./types";
import { SEVERITY_CONFIG } from "./types";

const typeIcons: Record<string, React.ReactNode> = {
  user: <User className="w-3 h-3" />, auth: <Shield className="w-3 h-3" />, ai: <Activity className="w-3 h-3" />,
  workflow: <Activity className="w-3 h-3" />, security: <AlertTriangle className="w-3 h-3" />,
  integration: <Link className="w-3 h-3" />, data: <Database className="w-3 h-3" />, admin: <Settings className="w-3 h-3" />,
};

export function AuditCenter({ events, compliance }: { events: AuditEvent[]; compliance: ComplianceCheck[] }) {
  const [filter, setFilter] = useState("all");
  const [statusFilter, setStatusFilter] = useState<"all" | "success" | "failure" | "blocked">("all");

  const typeCounts = events.reduce((acc, e) => {
    acc[e.type] = (acc[e.type] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);

  const chartData = Object.entries(typeCounts).map(([type, count]) => ({ name: type, count }));

  const filtered = (filter === "all" ? events : events.filter((e) => e.type === filter))
    .filter((e) => statusFilter === "all" || e.status === statusFilter);

  return (
    <div className="space-y-4">
      {/* Compliance cards */}
      <div className="grid grid-cols-3 gap-3">
        {compliance.map((c) => (
          <div key={c.id} className="p-3 bg-white border border-gray-200 rounded-lg">
            <div className="flex items-center justify-between mb-1">
              <span className="text-[11px] font-semibold text-navy-900">{c.standard}</span>
              <span className={`text-[9px] font-medium px-1.5 py-0.5 rounded-full ${c.status === "compliant" ? "bg-green-50 text-green-700" : c.status === "non_compliant" ? "bg-red-50 text-red-700" : c.status === "in_progress" ? "bg-yellow-50 text-yellow-700" : "bg-gray-50 text-gray-500"}`}>{c.status.replace(/_/g, " ")}</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="flex-1 h-1.5 bg-gray-200 rounded-full overflow-hidden">
                <div className={`h-full rounded-full ${c.score >= 85 ? "bg-green-500" : c.score >= 60 ? "bg-yellow-500" : "bg-red-500"}`} style={{ width: `${c.score}%` }} />
              </div>
              <span className="text-[10px] font-medium tabular-nums">{c.score}%</span>
            </div>
            <p className="text-[9px] text-gray-400 mt-1">{c.findings} findings • Next: {c.nextAudit}</p>
          </div>
        ))}
      </div>

      {/* Audit log */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
        <div className="px-4 py-3 border-b border-gray-100 flex items-center gap-2">
          <FileSearch className="w-4 h-4 text-navy-700" /><h3 className="text-xs font-semibold text-navy-900">Audit Event Log</h3>
          <div className="flex gap-1 ml-auto flex-wrap justify-end">
            {["all", "success", "failure", "blocked"].map((s) => (
              <button key={s} onClick={() => setStatusFilter(s as typeof statusFilter)}
                className={`text-[9px] font-medium px-2 py-0.5 rounded-full transition-colors ${statusFilter === s ? "bg-emerald-700 text-white" : "bg-gray-100 text-gray-600 hover:bg-gray-200"}`}>{s}</button>
            ))}
            {["all", "user", "auth", "ai", "security", "workflow", "integration"].map((t) => (
              <button key={t} onClick={() => setFilter(t)}
                className={`text-[9px] font-medium px-2 py-0.5 rounded-full transition-colors ${filter === t ? "bg-navy-700 text-white" : "bg-gray-100 text-gray-600 hover:bg-gray-200"}`}>{t}</button>
            ))}
          </div>
        </div>
        <div className="divide-y divide-gray-50 max-h-[300px] overflow-y-auto">
          {filtered.slice(0, 15).map((e) => {
            const sev = SEVERITY_CONFIG[e.severity];
            return (
              <div key={e.id} className="flex items-start gap-2.5 px-4 py-2 hover:bg-gray-50 transition-colors">
                <div className={`w-6 h-6 rounded-full flex items-center justify-center ${e.status === "blocked" ? "bg-red-50" : e.status === "failure" ? "bg-orange-50" : "bg-gray-50"}`}>
                  {typeIcons[e.type] || <Activity className="w-3 h-3 text-gray-400" />}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-1.5">
                    <span className="text-[11px] font-medium text-gray-800">{e.action}</span>
                    <span className={`text-[9px] font-medium px-1 py-0.5 rounded-full ${sev.bg} ${sev.color}`}>{e.severity}</span>
                    <span className={`text-[9px] font-medium px-1 py-0.5 rounded-full ${e.status === "blocked" ? "bg-red-50 text-red-700" : e.status === "failure" ? "bg-orange-50 text-orange-700" : "bg-green-50 text-green-700"}`}>{e.status}</span>
                  </div>
                  <p className="text-[9px] text-gray-400 mt-0.5">{e.details} • {e.user} • {e.resource}</p>
                </div>
                <span className="text-[9px] text-gray-400">{formatTime(e.timestamp)}</span>
              </div>
            );
          })}
        </div>
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

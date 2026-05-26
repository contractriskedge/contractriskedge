"use client";

import React from "react";
import { motion } from "framer-motion";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from "recharts";
import type { SlaMetric, TeamMember } from "./types";
import { WORKFLOW_STAGES } from "./types";

function CustomTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-white border border-gray-200 rounded-lg shadow-lg p-2.5 text-xs">
      <p className="font-semibold text-navy-900 mb-1">{label}</p>
      {payload.map((entry: any, i: number) => (
        <div key={i} className="flex items-center gap-2 py-0.5">
          <div className="w-2 h-2 rounded-full" style={{ backgroundColor: entry.color }} />
          <span className="text-gray-600">{entry.name}:</span>
          <span className="font-medium">{entry.value}{entry.name.includes("Rate") ? "%" : "h"}</span>
        </div>
      ))}
    </div>
  );
}

function SectionCard({ title, subtitle, children }: { title: string; subtitle?: string; children: React.ReactNode }) {
  return (
    <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
      <div className="px-4 py-3 border-b border-gray-100"><h3 className="text-xs font-semibold text-navy-900">{title}</h3>{subtitle && <p className="text-[10px] text-gray-500 mt-0.5">{subtitle}</p>}</div>
      <div className="p-4">{children}</div>
    </motion.div>
  );
}

// ── SLA Breach Chart ────────────────────────────────────────────────────────

export function SlaBreachChart({ data }: { data: SlaMetric[] }) {
  const chartData = data.map((d) => {
    const stage = WORKFLOW_STAGES.find((s) => s.id === d.stage);
    return { name: stage?.label || d.stage, target: d.targetHours, actual: d.actualHours, breachRate: d.breachRate };
  });
  return (
    <SectionCard title="SLA Performance by Stage" subtitle="Target vs actual hours with breach rate">
      <div className="h-56">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData} margin={{ top: 5, right: 10, left: -10, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#F3F4F6" />
            <XAxis dataKey="name" tick={{ fontSize: 9, fill: "#6B7280" }} axisLine={false} tickLine={false} angle={-20} textAnchor="end" height={40} />
            <YAxis tick={{ fontSize: 11, fill: "#9CA3AF" }} axisLine={false} tickLine={false} />
            <Tooltip content={<CustomTooltip />} />
            <Legend wrapperStyle={{ fontSize: "10px", paddingTop: "8px" }} iconType="rect" iconSize={7} />
            <Bar dataKey="target" name="Target (hours)" fill="#1B3A6B" radius={[4, 4, 0, 0]} />
            <Bar dataKey="actual" name="Actual (hours)" fill="#C9A84C" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </SectionCard>
  );
}

// ── SLA Breach Rate Chart ───────────────────────────────────────────────────

export function SlaBreachRateChart({ data }: { data: SlaMetric[] }) {
  const chartData = data.map((d) => {
    const stage = WORKFLOW_STAGES.find((s) => s.id === d.stage);
    return { name: stage?.label || d.stage, breachRate: d.breachRate };
  });
  return (
    <SectionCard title="SLA Breach Rate by Stage (%)" subtitle="Percentage of workflows breaching SLA">
      <div className="h-56">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData} margin={{ top: 5, right: 10, left: -10, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#F3F4F6" />
            <XAxis dataKey="name" tick={{ fontSize: 9, fill: "#6B7280" }} axisLine={false} tickLine={false} angle={-20} textAnchor="end" height={40} />
            <YAxis domain={[0, 30]} tick={{ fontSize: 11, fill: "#9CA3AF" }} axisLine={false} tickLine={false} />
            <Tooltip content={<CustomTooltip />} />
            <Bar dataKey="breachRate" name="Breach Rate %" radius={[4, 4, 0, 0]}>
              {chartData.map((entry, i) => (
                <rect key={i} fill={entry.breachRate > 15 ? "#DC2626" : entry.breachRate > 8 ? "#F97316" : "#22C55E"} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </SectionCard>
  );
}

// ── Team Workload ───────────────────────────────────────────────────────────

export function TeamWorkload({ members }: { members: TeamMember[] }) {
  return (
    <SectionCard title="Team Workload" subtitle="Active workflows by team member">
      <div className="space-y-2">
        {members.map((m) => (
          <div key={m.id} className="flex items-center gap-2.5">
            <div className={`w-7 h-7 rounded-full flex items-center justify-center text-[10px] font-bold ${m.online ? "bg-navy-100 text-navy-700" : "bg-gray-100 text-gray-400"}`}>
              {m.avatar}
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-1.5">
                <span className="text-[11px] font-medium text-gray-800">{m.name}</span>
                <span className={`w-1.5 h-1.5 rounded-full ${m.online ? "bg-green-500" : "bg-gray-300"}`} />
                <span className="text-[9px] text-gray-400">{m.role}</span>
              </div>
              <div className="flex items-center gap-2 mt-0.5">
                <div className="flex-1 h-1.5 bg-gray-200 rounded-full overflow-hidden">
                  <div className={`h-full rounded-full ${m.activeWorkflows > 6 ? "bg-red-500" : m.activeWorkflows > 4 ? "bg-yellow-500" : "bg-green-500"}`}
                    style={{ width: `${(m.activeWorkflows / 10) * 100}%` }} />
                </div>
                <span className="text-[10px] text-gray-500 tabular-nums">{m.activeWorkflows} active</span>
                <span className="text-[9px] text-gray-400">{m.completedToday} done today</span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </SectionCard>
  );
}

// ── Automation Rules ────────────────────────────────────────────────────────

export function AutomationRulesPanel({ rules }: { rules: import("./types").AutomationRule[] }) {
  return (
    <SectionCard title="Automation Engine" subtitle="Workflow automation rules">
      <div className="space-y-1.5">
        {rules.map((rule) => (
          <div key={rule.id} className="flex items-center gap-2.5 p-2.5 bg-white border border-gray-100 rounded-lg hover:shadow-sm transition-shadow">
            <div className={`w-6 h-6 rounded-full flex items-center justify-center ${rule.enabled ? "bg-green-50" : "bg-gray-100"}`}>
              {rule.enabled ? <CheckIcon /> : <XIcon />}
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-1.5">
                <span className="text-[11px] font-semibold text-navy-900">{rule.name}</span>
                <span className={`text-[9px] font-medium px-1.5 py-0.5 rounded-full ${rule.enabled ? "bg-green-50 text-green-700" : "bg-gray-100 text-gray-500"}`}>{rule.enabled ? "Enabled" : "Disabled"}</span>
              </div>
              <p className="text-[9px] text-gray-500 mt-0.5">{rule.description}</p>
              <div className="flex items-center gap-2 mt-1 text-[9px] text-gray-400">
                <span>{rule.executions.toLocaleString()} executions</span>
                <span>{rule.successRate}% success</span>
              </div>
            </div>
            <button className="text-[9px] font-medium px-2 py-1 rounded-md bg-navy-50 text-navy-700 hover:bg-navy-100 transition-colors opacity-0 group-hover:opacity-100">
              {rule.enabled ? "Disable" : "Enable"}
            </button>
          </div>
        ))}
      </div>
    </SectionCard>
  );
}

function CheckIcon() { return <svg className="w-3 h-3 text-green-600" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" /></svg>; }
function XIcon() { return <svg className="w-3 h-3 text-gray-400" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" /></svg>; }

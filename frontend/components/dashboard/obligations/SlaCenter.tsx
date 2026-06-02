"use client";

import React from "react";
import { motion } from "framer-motion";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from "recharts";
import { Activity, AlertTriangle, CheckCircle, TrendingUp, TrendingDown } from "lucide-react";
import type { SlaMetric, FinancialExposure } from "./types";

function CustomTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-white border border-gray-200 rounded-lg shadow-lg p-2.5 text-xs">
      <p className="font-semibold text-navy-900 mb-1">{label}</p>
      {payload.map((entry: any, i: number) => (
        <div key={i} className="flex items-center gap-2 py-0.5">
          <div className="w-2 h-2 rounded-full" style={{ backgroundColor: entry.color }} />
          <span className="text-gray-600">{entry.name}:</span>
          <span className="font-medium">{entry.value}{entry.name.includes("Performance") ? "%" : "$"}{entry.name.includes("Exposure") ? "M" : ""}</span>
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

// ── SLA Performance Chart ───────────────────────────────────────────────────

export function SlaPerformanceChart({ data, predictions }: { data: SlaMetric[]; predictions?: any[] }) {
  const chartData = data.map((d) => ({ name: d.vendor, performance: d.performance, target: parseFloat(d.slaTarget.replace("%", "")) }));
  return (
    <SectionCard title="SLA Performance by Vendor" subtitle="Actual vs target performance %">
      <div className="h-56">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData} margin={{ top: 5, right: 10, left: -10, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#F3F4F6" />
            <XAxis dataKey="name" tick={{ fontSize: 8, fill: "#6B7280" }} axisLine={false} tickLine={false} angle={-20} textAnchor="end" height={40} />
            <YAxis domain={[97, 100]} tick={{ fontSize: 11, fill: "#9CA3AF" }} axisLine={false} tickLine={false} />
            <Tooltip content={<CustomTooltip />} />
            <Bar dataKey="performance" name="Performance %" radius={[4, 4, 0, 0]}>
              {chartData.map((entry, i) => (
                <Cell key={i} fill={entry.performance < entry.target ? "#DC2626" : entry.performance < entry.target + 0.3 ? "#F97316" : "#22C55E"} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </SectionCard>
  );
}

// ── SLA Vendor Table ────────────────────────────────────────────────────────

export function SlaVendorTable({ data, breaches }: { data: SlaMetric[]; breaches?: any[] }) {
  return (
    <SectionCard title="SLA Governance" subtitle="Vendor SLA status and breach tracking">
      <div className="space-y-1.5">
        {data.map((s) => (
          <div key={s.vendor} className="flex items-center gap-3 p-2 bg-white border border-gray-100 rounded-lg">
            <div className={`w-2 h-2 rounded-full ${s.status === "on_track" ? "bg-green-500" : s.status === "at_risk" ? "bg-yellow-500" : "bg-red-500"}`} />
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-1.5">
                <span className="text-[11px] font-medium text-gray-800">{s.vendor}</span>
                <span className={`text-[9px] font-medium px-1.5 py-0.5 rounded-full ${s.status === "on_track" ? "bg-green-50 text-green-700" : s.status === "at_risk" ? "bg-yellow-50 text-yellow-700" : "bg-red-50 text-red-700"}`}>{s.status.replace(/_/g, " ")}</span>
              </div>
              <div className="flex items-center gap-2 mt-0.5">
                <div className="flex-1 h-1.5 bg-gray-200 rounded-full overflow-hidden">
                  <div className={`h-full rounded-full ${s.status === "breached" ? "bg-red-500" : s.status === "at_risk" ? "bg-yellow-500" : "bg-green-500"}`}
                    style={{ width: `${Math.min(100, s.performance)}%` }} />
                </div>
                <span className="text-[10px] font-medium tabular-nums">{s.performance}%</span>
                <span className="text-[9px] text-gray-400">{s.slaTarget}</span>
                <span className={`text-[9px] flex items-center gap-0.5 ${s.trend >= 0 ? "text-green-500" : "text-red-500"}`}>
                  {s.trend >= 0 ? <TrendingUp className="w-2.5 h-2.5" /> : <TrendingDown className="w-2.5 h-2.5" />}
                  {Math.abs(s.trend).toFixed(2)}%
                </span>
              </div>
            </div>
            {s.breachCount > 0 && <span className="text-[9px] font-medium text-red-600 bg-red-50 px-1.5 py-0.5 rounded">{s.breachCount} breaches</span>}
          </div>
        ))}
      </div>
    </SectionCard>
  );
}

// ── Financial Exposure ──────────────────────────────────────────────────────

export function FinancialExposurePanel({ data, valueAtRisk }: { data: FinancialExposure[]; valueAtRisk?: any }) {
  const total = data.reduce((s, d) => s + d.totalExposure, 0);
  return (
    <SectionCard title="Financial Exposure Analysis" subtitle={`Total exposure: $${total.toFixed(1)}M`}>
      <div className="space-y-2">
        {data.map((d) => (
          <div key={d.category} className="space-y-1">
            <div className="flex items-center justify-between text-xs">
              <span className="text-gray-700 font-medium">{d.category}</span>
              <span className="font-bold text-red-600">${d.totalExposure.toFixed(1)}M</span>
            </div>
            <div className="h-2 bg-gray-200 rounded-full overflow-hidden flex">
              <div className="h-full bg-green-500" style={{ width: `${(d.recoveredAmount / d.totalExposure) * 100}%` }} />
              <div className="h-full bg-yellow-500" style={{ width: `${(d.atRiskAmount / d.totalExposure) * 100}%` }} />
              <div className="h-full bg-red-500" style={{ width: `${(d.overdueAmount / d.totalExposure) * 100}%` }} />
            </div>
            <div className="flex justify-between text-[9px] text-gray-400">
              <span className="text-green-500">${d.recoveredAmount.toFixed(1)}M recovered</span>
              <span className="text-yellow-500">${d.atRiskAmount.toFixed(1)}M at risk</span>
              <span className="text-red-500">${d.overdueAmount.toFixed(1)}M overdue</span>
            </div>
          </div>
        ))}
      </div>
    </SectionCard>
  );
}

// ── Timeline ────────────────────────────────────────────────────────────────

export function ObligationTimeline({ events }: { events: import("./types").TimelineEvent[] }) {
  return (
    <SectionCard title="Obligation Timeline" subtitle="Upcoming and overdue obligations">
      <div className="space-y-1.5 max-h-[300px] overflow-y-auto">
        {events.map((e, i) => (
          <div key={e.id} className="flex items-start gap-2.5">
            <div className="flex flex-col items-center">
              <div className={`w-2.5 h-2.5 rounded-full ${e.status === "overdue" ? "bg-red-500" : e.status === "in_progress" ? "bg-blue-500" : "bg-gray-300"}`} />
              {i < events.length - 1 && <div className="w-px h-5 bg-gray-100" />}
            </div>
            <div className="flex-1 min-w-0 pb-1">
              <div className="flex items-center gap-1.5">
                <span className="text-[11px] font-semibold text-navy-900">{e.title}</span>
                <span className={`text-[8px] font-medium px-1 py-0.5 rounded-full ${e.status === "overdue" ? "bg-red-50 text-red-700" : e.status === "in_progress" ? "bg-blue-50 text-blue-700" : "bg-gray-50 text-gray-500"}`}>{e.status.replace(/_/g, " ")}</span>
              </div>
              <p className="text-[9px] text-gray-500">{e.description}</p>
              <p className="text-[8px] text-gray-400">{e.date} • {e.vendor}</p>
            </div>
          </div>
        ))}
      </div>
    </SectionCard>
  );
}

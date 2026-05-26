"use client";

import React from "react";
import { motion } from "framer-motion";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, AreaChart, Area, Legend, Cell, ComposedChart, Line } from "recharts";
import type { RiskTrend, DepartmentAnalytics, VendorAnalytics, ComplianceAnalytics, ForecastPoint } from "./types";

const COLORS = { critical: "#DC2626", high: "#EA580C", medium: "#EAB308", low: "#22C55E", navy: "#1B3A6B", blue: "#3B82F6", purple: "#8B5CF6", teal: "#0F766E", gold: "#C9A84C" };

function CustomTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-white border border-gray-200 rounded-lg shadow-lg p-3 text-xs">
      <p className="font-semibold text-navy-900 mb-1.5">{label}</p>
      {payload.map((entry: any, i: number) => (
        <div key={i} className="flex items-center gap-2 py-0.5">
          <div className="w-2 h-2 rounded-full" style={{ backgroundColor: entry.color }} />
          <span className="text-gray-600">{entry.name}:</span>
          <span className="font-medium text-gray-900">{typeof entry.value === "number" ? entry.value.toFixed(1) : entry.value}{entry.name.includes("Exposure") || entry.name.includes("Spend") ? "M" : entry.name.includes("Score") || entry.name.includes("Coverage") ? "%" : ""}</span>
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

// ── 1. Risk Trend ───────────────────────────────────────────────────────────

export function RiskTrendChart({ data }: { data: RiskTrend[] }) {
  return (
    <SectionCard title="Enterprise Risk Trend" subtitle="Risk distribution and exposure over time">
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data} margin={{ top: 5, right: 10, left: -10, bottom: 0 }}>
            <defs>{["critical", "high", "medium", "low"].map((k) => (
              <linearGradient key={k} id={`ar-${k}`} x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor={COLORS[k as keyof typeof COLORS]} stopOpacity={0.3} />
                <stop offset="95%" stopColor={COLORS[k as keyof typeof COLORS]} stopOpacity={0.02} />
              </linearGradient>
            ))}</defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#F3F4F6" />
            <XAxis dataKey="month" tick={{ fontSize: 11, fill: "#9CA3AF" }} axisLine={false} tickLine={false} />
            <YAxis tick={{ fontSize: 11, fill: "#9CA3AF" }} axisLine={false} tickLine={false} />
            <Tooltip content={<CustomTooltip />} />
            <Legend wrapperStyle={{ fontSize: "10px", paddingTop: "8px" }} iconType="circle" iconSize={7} />
            {(["critical", "high", "medium", "low"] as const).map((k) => (
              <Area key={k} type="monotone" dataKey={k} name={k.charAt(0).toUpperCase() + k.slice(1)} stackId="1"
                stroke={COLORS[k]} fill={`url(#ar-${k})`} strokeWidth={1.5} />
            ))}
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </SectionCard>
  );
}

// ── 2. Department Comparison ────────────────────────────────────────────────

export function DepartmentChart({ data }: { data: DepartmentAnalytics[] }) {
  const sorted = [...data].sort((a, b) => b.avgRisk - a.avgRisk);
  return (
    <SectionCard title="Department Risk Comparison" subtitle="Average risk score by department">
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={sorted} layout="vertical" margin={{ top: 5, right: 30, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#F3F4F6" horizontal={false} />
            <XAxis type="number" domain={[0, 10]} tick={{ fontSize: 11, fill: "#9CA3AF" }} axisLine={false} tickLine={false} />
            <YAxis type="category" dataKey="department" tick={{ fontSize: 9, fill: "#6B7280" }} axisLine={false} tickLine={false} width={80} />
            <Tooltip content={<CustomTooltip />} />
            <Bar dataKey="avgRisk" name="Avg Risk Score" radius={[0, 4, 4, 0]}>
              {sorted.map((entry, i) => <Cell key={i} fill={entry.avgRisk >= 7 ? COLORS.critical : entry.avgRisk >= 5 ? COLORS.medium : COLORS.low} />)}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </SectionCard>
  );
}

// ── 3. Vendor Ranking ───────────────────────────────────────────────────────

export function VendorRankingChart({ data }: { data: VendorAnalytics[] }) {
  const sorted = [...data].sort((a, b) => b.totalSpend - a.totalSpend);
  return (
    <SectionCard title="Vendor Spend & Risk Ranking" subtitle="Total spend vs risk score by vendor">
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={sorted} layout="vertical" margin={{ top: 5, right: 30, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#F3F4F6" horizontal={false} />
            <XAxis type="number" tick={{ fontSize: 11, fill: "#9CA3AF" }} axisLine={false} tickLine={false} />
            <YAxis type="category" dataKey="vendor" tick={{ fontSize: 8, fill: "#6B7280" }} axisLine={false} tickLine={false} width={85} />
            <Tooltip content={<CustomTooltip />} />
            <Bar dataKey="totalSpend" name="Total Spend ($M)" fill={COLORS.navy} radius={[0, 4, 4, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </SectionCard>
  );
}

// ── 4. Compliance Comparison ────────────────────────────────────────────────

export function ComplianceChart({ data }: { data: ComplianceAnalytics[] }) {
  return (
    <SectionCard title="Compliance Benchmark" subtitle="Your score vs market average">
      <div className="h-56">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 5, right: 10, left: -10, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#F3F4F6" />
            <XAxis dataKey="standard" tick={{ fontSize: 9, fill: "#6B7280" }} axisLine={false} tickLine={false} />
            <YAxis domain={[0, 100]} tick={{ fontSize: 11, fill: "#9CA3AF" }} axisLine={false} tickLine={false} />
            <Tooltip content={<CustomTooltip />} />
            <Legend wrapperStyle={{ fontSize: "10px", paddingTop: "8px" }} iconType="rect" iconSize={7} />
            <Bar dataKey="marketAvg" name="Market Avg" fill={COLORS.navy} radius={[4, 4, 0, 0]} />
            <Bar dataKey="score" name="Your Score" radius={[4, 4, 0, 0]}>
              {data.map((entry, i) => <Cell key={i} fill={entry.score >= 85 ? COLORS.low : entry.score >= 60 ? COLORS.medium : COLORS.critical} />)}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </SectionCard>
  );
}

// ── 5. Forecast Chart ───────────────────────────────────────────────────────

export function ForecastChart({ data }: { data: ForecastPoint[] }) {
  return (
    <SectionCard title="Risk Exposure Forecast" subtitle="Actual vs predicted exposure with confidence bands">
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data} margin={{ top: 5, right: 10, left: -10, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#F3F4F6" />
            <XAxis dataKey="period" tick={{ fontSize: 11, fill: "#9CA3AF" }} axisLine={false} tickLine={false} />
            <YAxis tick={{ fontSize: 11, fill: "#9CA3AF" }} axisLine={false} tickLine={false} />
            <Tooltip content={<CustomTooltip />} />
            <Legend wrapperStyle={{ fontSize: "10px", paddingTop: "8px" }} iconType="circle" iconSize={7} />
            <Area type="monotone" dataKey="upperBound" name="Upper Bound" stroke="transparent" fill="#EF4444" fillOpacity={0.1} />
            <Area type="monotone" dataKey="lowerBound" name="Lower Bound" stroke="transparent" fill="#22C55E" fillOpacity={0.1} />
            <Line type="monotone" dataKey="forecast" name="Forecast" stroke={COLORS.navy} strokeWidth={2} strokeDasharray="5,5" dot={false} />
            <Line type="monotone" dataKey="actual" name="Actual" stroke={COLORS.gold} strokeWidth={2.5} dot={{ r: 4 }} />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </SectionCard>
  );
}

// ── 6. Legal Ops Metrics ────────────────────────────────────────────────────

export function LegalOpsChart({ data }: { data: { metric: string; value: string; trend: number; benchmark: string }[] }) {
  return (
    <SectionCard title="Legal Operations KPIs" subtitle="Key operational metrics vs benchmarks">
      <div className="space-y-2">
        {data.map((m) => (
          <div key={m.metric} className="flex items-center gap-3">
            <span className="text-[11px] text-gray-700 w-36 font-medium">{m.metric}</span>
            <span className="text-xs font-bold text-navy-900 w-16">{m.value}</span>
            <div className="flex-1 h-2 bg-gray-200 rounded-full overflow-hidden">
              <div className={`h-full rounded-full ${m.trend > 0 ? "bg-green-500" : "bg-red-500"}`} style={{ width: `${Math.min(100, Math.abs(parseFloat(m.value) * 5))}%` }} />
            </div>
            <span className={`text-[10px] font-medium w-20 ${m.trend > 0 ? "text-green-600" : "text-red-600"}`}>
              {m.trend > 0 ? "↑" : "↓"} {Math.abs(m.trend)}%
            </span>
            <span className="text-[10px] text-gray-400 w-16">Target: {m.benchmark}</span>
          </div>
        ))}
      </div>
    </SectionCard>
  );
}

// ── 7. Department Exposure ──────────────────────────────────────────────────

export function DepartmentExposureChart({ data }: { data: DepartmentAnalytics[] }) {
  return (
    <SectionCard title="Financial Exposure by Department" subtitle="Total at-risk contract value ($M)">
      <div className="h-56">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={[...data].sort((a, b) => b.exposure - a.exposure)} margin={{ top: 5, right: 10, left: -10, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#F3F4F6" />
            <XAxis dataKey="department" tick={{ fontSize: 9, fill: "#6B7280" }} axisLine={false} tickLine={false} />
            <YAxis tick={{ fontSize: 11, fill: "#9CA3AF" }} axisLine={false} tickLine={false} />
            <Tooltip content={<CustomTooltip />} />
            <Bar dataKey="exposure" name="Exposure ($M)" radius={[4, 4, 0, 0]}>
              {data.map((entry, i) => <Cell key={i} fill={entry.exposure >= 4 ? COLORS.critical : entry.exposure >= 2 ? COLORS.medium : COLORS.low} />)}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </SectionCard>
  );
}

"use client";

import React from "react";
import { motion } from "framer-motion";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, AreaChart, Area, Legend, Cell, PieChart, Pie } from "recharts";
import type { SpendTrend, VendorCategory, GeoRisk, RiskTrend } from "./types";

const COLORS = { critical: "#DC2626", high: "#EA580C", medium: "#EAB308", low: "#22C55E", navy: "#1B3A6B", blue: "#3B82F6", purple: "#8B5CF6", teal: "#0F766E" };

function CustomTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-white border border-gray-200 rounded-lg shadow-lg p-3 text-xs">
      <p className="font-semibold text-navy-900 mb-1.5">{label}</p>
      {payload.map((entry: any, i: number) => (
        <div key={i} className="flex items-center gap-2 py-0.5">
          <div className="w-2 h-2 rounded-full" style={{ backgroundColor: entry.color }} />
          <span className="text-gray-600">{entry.name}:</span>
          <span className="font-medium text-gray-900">${entry.value}M</span>
        </div>
      ))}
    </div>
  );
}

function SectionCard({ title, subtitle, children, className = "" }: { title: string; subtitle?: string; children: React.ReactNode; className?: string }) {
  return (
    <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className={`bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden ${className}`}>
      <div className="px-4 py-3 border-b border-gray-100">
        <h3 className="text-xs font-semibold text-navy-900">{title}</h3>
        {subtitle && <p className="text-[10px] text-gray-500 mt-0.5">{subtitle}</p>}
      </div>
      <div className="p-4">{children}</div>
    </motion.div>
  );
}

// ── 1. Spend Trend ──────────────────────────────────────────────────────────

export function SpendTrendChart({ data }: { data: SpendTrend[] }) {
  return (
    <SectionCard title="Spend Trend (Monthly)" subtitle="Total procurement spend by category ($M)">
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data} margin={{ top: 5, right: 10, left: -10, bottom: 0 }}>
            <defs>{["cloud", "software", "consulting", "hardware", "services"].map((k) => (
              <linearGradient key={k} id={`grad-${k}`} x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor={k === "cloud" ? "#3B82F6" : k === "software" ? "#8B5CF6" : k === "consulting" ? "#F97316" : k === "hardware" ? "#22C55E" : "#06B6D4"} stopOpacity={0.3} />
                <stop offset="95%" stopColor={k === "cloud" ? "#3B82F6" : k === "software" ? "#8B5CF6" : k === "consulting" ? "#F97316" : k === "hardware" ? "#22C55E" : "#06B6D4"} stopOpacity={0.02} />
              </linearGradient>
            ))}</defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#F3F4F6" />
            <XAxis dataKey="month" tick={{ fontSize: 11, fill: "#9CA3AF" }} axisLine={false} tickLine={false} />
            <YAxis tick={{ fontSize: 11, fill: "#9CA3AF" }} axisLine={false} tickLine={false} />
            <Tooltip content={<CustomTooltip />} />
            <Legend wrapperStyle={{ fontSize: "10px", paddingTop: "8px" }} iconType="circle" iconSize={7} />
            {["cloud", "software", "consulting", "hardware", "services"].map((k) => (
              <Area key={k} type="monotone" dataKey={k} name={k.charAt(0).toUpperCase() + k.slice(1)} stackId="1"
                stroke={k === "cloud" ? "#3B82F6" : k === "software" ? "#8B5CF6" : k === "consulting" ? "#F97316" : k === "hardware" ? "#22C55E" : "#06B6D4"}
                fill={`url(#grad-${k})`} strokeWidth={1.5} />
            ))}
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </SectionCard>
  );
}

// ── 2. Vendor Category Breakdown ────────────────────────────────────────────

export function VendorCategoryChart({ data }: { data: VendorCategory[] }) {
  return (
    <SectionCard title="Vendor Category Breakdown" subtitle="Spend and risk by category">
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 5, right: 10, left: -10, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#F3F4F6" />
            <XAxis dataKey="category" tick={{ fontSize: 9, fill: "#6B7280" }} axisLine={false} tickLine={false} angle={-20} textAnchor="end" height={40} />
            <YAxis yAxisId="left" tick={{ fontSize: 11, fill: "#9CA3AF" }} axisLine={false} tickLine={false} />
            <YAxis yAxisId="right" orientation="right" domain={[0, 10]} tick={{ fontSize: 11, fill: "#9CA3AF" }} axisLine={false} tickLine={false} />
            <Tooltip content={<CustomTooltip />} />
            <Legend wrapperStyle={{ fontSize: "10px", paddingTop: "8px" }} iconType="rect" iconSize={7} />
            <Bar yAxisId="left" dataKey="totalSpend" name="Total Spend ($M)" fill={COLORS.navy} radius={[4, 4, 0, 0]} />
            <Bar yAxisId="right" dataKey="avgRisk" name="Avg Risk Score" fill={COLORS.medium} radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </SectionCard>
  );
}

// ── 3. Geographic Risk ──────────────────────────────────────────────────────

export function GeoRiskChart({ data }: { data: GeoRisk[] }) {
  return (
    <SectionCard title="Geographic Supplier Risk" subtitle="Risk exposure by country">
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={[...data].sort((a, b) => b.avgRisk - a.avgRisk)} layout="vertical" margin={{ top: 5, right: 30, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#F3F4F6" horizontal={false} />
            <XAxis type="number" domain={[0, 10]} tick={{ fontSize: 11, fill: "#9CA3AF" }} axisLine={false} tickLine={false} />
            <YAxis type="category" dataKey="country" tick={{ fontSize: 10, fill: "#6B7280" }} axisLine={false} tickLine={false} width={70} />
            <Tooltip content={<CustomTooltip />} />
            <Bar dataKey="avgRisk" name="Avg Risk Score" radius={[0, 4, 4, 0]}>
              {data.map((entry, i) => <Cell key={i} fill={entry.avgRisk >= 7 ? COLORS.critical : entry.avgRisk >= 5 ? COLORS.medium : COLORS.low} />)}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </SectionCard>
  );
}

// ── 4. Risk Trend ───────────────────────────────────────────────────────────

export function SupplierRiskTrendChart({ data }: { data: RiskTrend[] }) {
  return (
    <SectionCard title="Supplier Risk Trend" subtitle="Risk distribution over time">
      <div className="h-56">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 5, right: 10, left: -10, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#F3F4F6" />
            <XAxis dataKey="date" tick={{ fontSize: 11, fill: "#9CA3AF" }} axisLine={false} tickLine={false} />
            <YAxis tick={{ fontSize: 11, fill: "#9CA3AF" }} axisLine={false} tickLine={false} />
            <Tooltip content={<CustomTooltip />} />
            <Legend wrapperStyle={{ fontSize: "10px", paddingTop: "8px" }} iconType="circle" iconSize={7} />
            {(["critical", "high", "medium", "low"] as const).map((k) => (
              <Bar key={k} dataKey={k} name={k.charAt(0).toUpperCase() + k.slice(1)} stackId="1" fill={COLORS[k]} radius={k === "low" ? [0, 0, 4, 4] : 0} />
            ))}
          </BarChart>
        </ResponsiveContainer>
      </div>
    </SectionCard>
  );
}

// ── 5. Spend Concentration Donut ────────────────────────────────────────────

export function SpendConcentrationChart({ data }: { data: VendorCategory[] }) {
  const pieData = data.map((d) => ({ name: d.category, value: d.totalSpend }));
  return (
    <SectionCard title="Spend Concentration" subtitle="Category distribution">
      <div className="h-56 flex items-center">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie data={pieData} cx="50%" cy="50%" innerRadius={45} outerRadius={70} paddingAngle={2} dataKey="value">
              {pieData.map((_, i) => (
                <Cell key={i} fill={[COLORS.navy, COLORS.blue, COLORS.purple, COLORS.teal, COLORS.critical, COLORS.high, COLORS.medium, COLORS.low][i % 8]} strokeWidth={0} />
              ))}
            </Pie>
            <Tooltip content={({ active, payload }) => active && payload?.length ? (
              <div className="bg-white border border-gray-200 rounded-lg shadow-lg p-2.5 text-xs">
                <p className="font-medium text-gray-900">{payload[0].name}</p>
                <p className="text-gray-600">${payload[0].value}M</p>
              </div>
            ) : null} />
          </PieChart>
        </ResponsiveContainer>
        <div className="space-y-1 pr-2">
          {pieData.slice(0, 5).map((d, i) => (
            <div key={d.name} className="flex items-center gap-1.5 text-[10px]">
              <div className="w-2 h-2 rounded-full" style={{ backgroundColor: [COLORS.navy, COLORS.blue, COLORS.purple, COLORS.teal, COLORS.critical][i] }} />
              <span className="text-gray-500 truncate max-w-[80px]">{d.name}</span>
              <span className="font-medium text-gray-700">${d.value}M</span>
            </div>
          ))}
        </div>
      </div>
    </SectionCard>
  );
}

"use client";

import React, { useState } from "react";
import { motion } from "framer-motion";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  AreaChart, Area, LineChart, Line, Legend, Cell,
} from "recharts";
import { TrendingUp, TrendingDown, Filter } from "lucide-react";
import type { RiskTrendPoint, MonthlyExposure, VendorRisk, ClauseCategoryRisk, DepartmentRisk } from "./types";

// ── Color palette ───────────────────────────────────────────────────────────

const COLORS = {
  critical: "#DC2626",
  high: "#EA580C",
  medium: "#EAB308",
  low: "#22C55E",
  navy: "#1B3A6B",
  gold: "#C9A84C",
  blue: "#3B82F6",
  teal: "#0F766E",
};

// ── Custom Tooltip ──────────────────────────────────────────────────────────

function CustomTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-white border border-gray-200 rounded-lg shadow-lg p-3 text-xs">
      <p className="font-semibold text-navy-900 mb-1.5">{label}</p>
      {payload.map((entry: any, i: number) => (
        <div key={i} className="flex items-center gap-2 py-0.5">
          <div className="w-2 h-2 rounded-full" style={{ backgroundColor: entry.color }} />
          <span className="text-gray-600">{entry.name}:</span>
          <span className="font-medium text-gray-900">{entry.value}</span>
        </div>
      ))}
    </div>
  );
}

// ── Section Wrapper ─────────────────────────────────────────────────────────

function SectionCard({ title, subtitle, children, className = "" }: {
  title: string; subtitle?: string; children: React.ReactNode; className?: string;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      className={`bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden ${className}`}
    >
      <div className="px-5 py-4 border-b border-gray-100">
        <h3 className="text-sm font-semibold text-navy-900">{title}</h3>
        {subtitle && <p className="text-[11px] text-gray-500 mt-0.5">{subtitle}</p>}
      </div>
      <div className="p-5">{children}</div>
    </motion.div>
  );
}

// ── 1. Risk Trend Over Time ────────────────────────────────────────────────

export function RiskTrendChart({ data }: { data: RiskTrendPoint[] }) {
  return (
    <SectionCard title="Risk Trend (12 Months)" subtitle="Monthly contract risk distribution across all categories">
      <div className="h-72">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data} margin={{ top: 5, right: 10, left: -10, bottom: 0 }}>
            <defs>
              {(["critical", "high", "medium", "low"] as const).map((k) => (
                <linearGradient key={k} id={`grad-${k}`} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={COLORS[k]} stopOpacity={0.3} />
                  <stop offset="95%" stopColor={COLORS[k]} stopOpacity={0.02} />
                </linearGradient>
              ))}
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#F3F4F6" />
            <XAxis dataKey="date" tick={{ fontSize: 11, fill: "#9CA3AF" }} axisLine={false} tickLine={false} />
            <YAxis tick={{ fontSize: 11, fill: "#9CA3AF" }} axisLine={false} tickLine={false} />
            <Tooltip content={<CustomTooltip />} />
            <Legend
              wrapperStyle={{ fontSize: "11px", paddingTop: "8px" }}
              iconType="circle"
              iconSize={8}
            />
            {(["critical", "high", "medium", "low"] as const).map((k) => (
              <Area
                key={k}
                type="monotone"
                dataKey={k}
                name={k.charAt(0).toUpperCase() + k.slice(1)}
                stackId="1"
                stroke={COLORS[k]}
                fill={`url(#grad-${k})`}
                strokeWidth={1.5}
              />
            ))}
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </SectionCard>
  );
}

// ── 2. Monthly Exposure ────────────────────────────────────────────────────

export function MonthlyExposureChart({ data }: { data: MonthlyExposure[] }) {
  return (
    <SectionCard title="Monthly Exposure ($M)" subtitle="Total exposure vs. liability vs. insured amount">
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 5, right: 10, left: -10, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#F3F4F6" />
            <XAxis dataKey="month" tick={{ fontSize: 11, fill: "#9CA3AF" }} axisLine={false} tickLine={false} />
            <YAxis tick={{ fontSize: 11, fill: "#9CA3AF" }} axisLine={false} tickLine={false} />
            <Tooltip content={<CustomTooltip />} />
            <Legend wrapperStyle={{ fontSize: "11px", paddingTop: "8px" }} iconType="rect" iconSize={8} />
            <Bar dataKey="exposure" name="Total Exposure" fill={COLORS.critical} radius={[4, 4, 0, 0]} />
            <Bar dataKey="liability" name="Liability" fill={COLORS.high} radius={[4, 4, 0, 0]} />
            <Bar dataKey="insured" name="Insured" fill={COLORS.low} radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </SectionCard>
  );
}

// ── 3. Vendor Risk Distribution ─────────────────────────────────────────────

export function VendorRiskChart({ data }: { data: VendorRisk[] }) {
  const sorted = [...data].sort((a, b) => b.avgRiskScore - a.avgRiskScore);
  return (
    <SectionCard title="Vendor Risk Distribution" subtitle="Average risk score by vendor">
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={sorted} layout="vertical" margin={{ top: 5, right: 30, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#F3F4F6" horizontal={false} />
            <XAxis type="number" domain={[0, 10]} tick={{ fontSize: 11, fill: "#9CA3AF" }} axisLine={false} tickLine={false} />
            <YAxis type="category" dataKey="vendor" tick={{ fontSize: 10, fill: "#6B7280" }} axisLine={false} tickLine={false} width={110} />
            <Tooltip content={<CustomTooltip />} />
            <Bar dataKey="avgRiskScore" name="Avg Risk Score" radius={[0, 4, 4, 0]}>
              {sorted.map((entry, i) => (
                <Cell key={i} fill={entry.avgRiskScore >= 7 ? COLORS.critical : entry.avgRiskScore >= 5 ? COLORS.medium : COLORS.low} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </SectionCard>
  );
}

// ── 4. Clause Category Heatmap ─────────────────────────────────────────────

export function ClauseCategoryChart({ data }: { data: ClauseCategoryRisk[] }) {
  return (
    <SectionCard title="Clause Category Risk Heatmap" subtitle="High/Medium/Low risk counts by clause type">
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-gray-100">
              <th className="text-left py-2 pr-4 font-semibold text-gray-500">Category</th>
              <th className="text-center py-2 px-2 font-semibold text-red-600">Critical</th>
              <th className="text-center py-2 px-2 font-semibold text-orange-600">High</th>
              <th className="text-center py-2 px-2 font-semibold text-yellow-600">Medium</th>
              <th className="text-center py-2 px-2 font-semibold text-green-600">Low</th>
              <th className="text-right py-2 pl-4 font-semibold text-gray-500">Avg Severity</th>
            </tr>
          </thead>
          <tbody>
            {data.map((row) => {
              const total = row.highRiskCount + row.mediumRiskCount + row.lowRiskCount;
              return (
                <tr key={row.category} className="border-b border-gray-50 hover:bg-gray-50 transition-colors">
                  <td className="py-2.5 pr-4 font-medium text-gray-700">{row.category}</td>
                  <td className="text-center py-2.5 px-2">
                    <span className={`inline-block w-full py-1 rounded text-[10px] font-medium ${
                      row.highRiskCount > 20 ? "bg-red-100 text-red-700" :
                      row.highRiskCount > 10 ? "bg-orange-100 text-orange-700" :
                      "bg-gray-100 text-gray-600"
                    }`}>
                      {row.highRiskCount}
                    </span>
                  </td>
                  <td className="text-center py-2.5 px-2">
                    <span className={`inline-block w-full py-1 rounded text-[10px] font-medium ${
                      row.mediumRiskCount > 30 ? "bg-orange-100 text-orange-700" :
                      row.mediumRiskCount > 20 ? "bg-yellow-100 text-yellow-700" :
                      "bg-gray-100 text-gray-600"
                    }`}>
                      {row.mediumRiskCount}
                    </span>
                  </td>
                  <td className="text-center py-2.5 px-2">
                    <span className="inline-block w-full py-1 rounded text-[10px] font-medium bg-green-100 text-green-700">
                      {row.lowRiskCount}
                    </span>
                  </td>
                  <td className="text-center py-2.5 px-2">
                    <span className="text-[10px] text-gray-400">{total}</span>
                  </td>
                  <td className="text-right py-2.5 pl-4">
                    <span className={`text-xs font-bold ${
                      row.avgSeverity >= 7 ? "text-red-600" :
                      row.avgSeverity >= 5 ? "text-orange-600" :
                      "text-green-600"
                    }`}>
                      {row.avgSeverity.toFixed(1)}
                    </span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </SectionCard>
  );
}

// ── 5. Department Risk Comparison ──────────────────────────────────────────

export function DepartmentRiskChart({ data }: { data: DepartmentRisk[] }) {
  const sorted = [...data].sort((a, b) => b.avgRisk - a.avgRisk);
  return (
    <SectionCard title="Department Risk Comparison" subtitle="Average risk score by department">
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={sorted} layout="vertical" margin={{ top: 5, right: 30, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#F3F4F6" horizontal={false} />
            <XAxis type="number" domain={[0, 10]} tick={{ fontSize: 11, fill: "#9CA3AF" }} axisLine={false} tickLine={false} />
            <YAxis type="category" dataKey="department" tick={{ fontSize: 10, fill: "#6B7280" }} axisLine={false} tickLine={false} width={90} />
            <Tooltip content={<CustomTooltip />} />
            <Bar dataKey="avgRisk" name="Avg Risk Score" radius={[0, 4, 4, 0]}>
              {sorted.map((entry, i) => (
                <Cell key={i} fill={entry.avgRisk >= 7 ? COLORS.critical : entry.avgRisk >= 5 ? COLORS.medium : COLORS.low} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </SectionCard>
  );
}

// ── Filter Bar ──────────────────────────────────────────────────────────────

interface FilterBarProps {
  filters: Record<string, string>;
  onChange: (key: string, value: string) => void;
}

export function FilterBar({ filters, onChange }: FilterBarProps) {
  const options = {
    businessUnit: ["All Units", "North America", "EMEA", "APAC", "LATAM"],
    vendor: ["All Vendors", "Acme Corp", "GlobalTech Inc", "SecureNet Solutions", "DataSync Partners"],
    geography: ["All Regions", "United States", "Germany", "Japan", "United Kingdom"],
    contractType: ["All Types", "MSA", "SOW", "License", "NDA", "Service Agreement"],
    riskLevel: ["All Levels", "Critical", "High", "Medium", "Low"],
  };

  return (
    <div className="flex items-center gap-2 flex-wrap bg-white rounded-xl border border-gray-200 shadow-sm px-4 py-3">
      <Filter className="w-4 h-4 text-gray-400 flex-shrink-0" />
      {Object.entries(options).map(([key, vals]) => (
        <select
          key={key}
          value={filters[key]}
          onChange={(e) => onChange(key, e.target.value)}
          className="text-[11px] border border-gray-200 rounded-md px-2 py-1.5 text-gray-600 bg-white hover:border-gray-300 focus:border-navy-400 focus:ring-1 focus:ring-navy-400 transition-colors"
          aria-label={`Filter by ${key}`}
        >
          {vals.map((v) => (
            <option key={v} value={v === `All ${key === "businessUnit" ? "Units" : key === "vendor" ? "Vendors" : key === "geography" ? "Regions" : key === "contractType" ? "Types" : "Levels"}` ? "all" : v}>
              {v}
            </option>
          ))}
        </select>
      ))}
    </div>
  );
}

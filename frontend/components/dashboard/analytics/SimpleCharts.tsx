/**
 * Simple chart components for AnalyticsCenter — lightweight Recharts wrappers.
 *
 * Each component handles loading, empty, and error states gracefully.
 * Supports click events for cross-widget drilldown via AnalyticsEventBus.
 */

"use client";

import React, { useCallback } from "react";
import {
  LineChart, Line, PieChart, Pie, Cell, BarChart, Bar,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend,
} from "recharts";
import { Loader2 } from "lucide-react";
import { analyticsBus } from "./AnalyticsEventBus";

// ── Chart Card Wrapper ───────────────────────────────────────────

export function AnalyticsChartCard({
  title, subtitle, loading, isEmpty, children,
}: {
  title: string;
  subtitle?: string;
  loading: boolean;
  isEmpty: boolean;
  children: React.ReactNode;
}) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
      <div className="px-4 py-3 border-b border-gray-100">
        <h3 className="text-xs font-semibold text-navy-900">{title}</h3>
        {subtitle && <p className="text-[10px] text-gray-500 mt-0.5">{subtitle}</p>}
      </div>
      <div className="p-4">
        {loading ? (
          <div className="flex items-center justify-center h-48">
            <Loader2 className="w-5 h-5 text-gray-400 animate-spin" />
          </div>
        ) : isEmpty ? (
          <div className="flex items-center justify-center h-48">
            <p className="text-xs text-gray-400 italic">No data available for this period</p>
          </div>
        ) : (
          <div className="h-48">{children}</div>
        )}
      </div>
    </div>
  );
}

// ── Custom Tooltip ───────────────────────────────────────────────

function ChartTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-white border border-gray-200 rounded-lg shadow-lg p-2.5 text-xs">
      <p className="font-semibold text-gray-900 mb-1">{label}</p>
      {payload.map((entry: any, i: number) => (
        <div key={i} className="flex items-center gap-2 py-0.5">
          <div className="w-2 h-2 rounded-full" style={{ backgroundColor: entry.color }} />
          <span className="text-gray-600">{entry.name}:</span>
          <span className="font-medium text-gray-900">
            {typeof entry.value === "number" ? entry.value.toLocaleString() : entry.value}
          </span>
        </div>
      ))}
    </div>
  );
}

// ── Simple Line Chart ────────────────────────────────────────────

interface LineConfig {
  key: string;
  color: string;
  name: string;
}

export function SimpleLineChart({
  data, xKey, lines,
}: {
  data: Record<string, unknown>[];
  xKey: string;
  lines: LineConfig[];
}) {
  const handleDotClick = useCallback((entry: any) => {
    // Emit a time range event when clicking a data point
    const day = entry?.[xKey];
    if (day) {
      analyticsBus.emit("TIME_RANGE_CHANGED", { range: String(day) });
    }
  }, [xKey]);

  return (
    <ResponsiveContainer width="100%" height="100%">
      <LineChart data={data} margin={{ top: 5, right: 10, left: -10, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#F3F4F6" />
        <XAxis dataKey={xKey} tick={{ fontSize: 10, fill: "#9CA3AF" }} axisLine={false} tickLine={false} />
        <YAxis tick={{ fontSize: 10, fill: "#9CA3AF" }} axisLine={false} tickLine={false} />
        <Tooltip content={<ChartTooltip />} />
        <Legend wrapperStyle={{ fontSize: "9px", paddingTop: "4px" }} iconType="circle" iconSize={6} />
        {lines.map((l) => (
          <Line
            key={l.key}
            type="monotone"
            dataKey={l.key}
            name={l.name}
            stroke={l.color}
            strokeWidth={2}
            dot={{ r: 2, onClick: handleDotClick, style: { cursor: "pointer" } }}
            activeDot={{ r: 4, onClick: handleDotClick, style: { cursor: "pointer" } }}
          />
        ))}
      </LineChart>
    </ResponsiveContainer>
  );
}

// ── Simple Pie/Donut Chart ───────────────────────────────────────

export function SimplePieChart({
  data, nameKey, valueKey, colors,
}: {
  data: Record<string, unknown>[];
  nameKey: string;
  valueKey: string;
  colors: Record<string, string>;
}) {
  const total = data.reduce((s, d) => s + (Number(d[valueKey]) || 0), 0);

  const handlePieClick = useCallback((entry: any) => {
    const level = entry[nameKey];
    if (level) {
      analyticsBus.emit("RISK_SELECTED", { level: String(level) });
    }
  }, [nameKey]);

  return (
    <div className="flex items-center h-full gap-2">
      <ResponsiveContainer width="60%" height="100%">
        <PieChart>
          <Pie
            data={data}
            dataKey={valueKey}
            nameKey={nameKey}
            cx="50%"
            cy="50%"
            innerRadius={45}
            outerRadius={70}
            paddingAngle={2}
            onClick={handlePieClick}
            style={{ cursor: "pointer" }}
          >
            {data.map((entry) => (
              <Cell key={String(entry[nameKey])} fill={colors[String(entry[nameKey])] || "#9CA3AF"} />
            ))}
          </Pie>
          <Tooltip content={<ChartTooltip />} />
        </PieChart>
      </ResponsiveContainer>
      <div className="flex flex-col gap-1.5 text-[10px]">
        {data.map((entry) => {
          const key = String(entry[nameKey]);
          const val = Number(entry[valueKey]) || 0;
          const pct = total > 0 ? ((val / total) * 100).toFixed(0) : "0";
          return (
            <button
              key={key}
              onClick={() => analyticsBus.emit("RISK_SELECTED", { level: key })}
              className="flex items-center gap-1.5 hover:bg-gray-50 rounded px-1 -mx-1 transition-colors text-left"
            >
              <div className="w-2 h-2 rounded-full flex-shrink-0" style={{ backgroundColor: colors[key] || "#9CA3AF" }} />
              <span className="text-gray-600 capitalize">{key}</span>
              <span className="font-medium text-gray-900 ml-auto">{val} ({pct}%)</span>
            </button>
          );
        })}
      </div>
    </div>
  );
}

// ── Simple Bar Chart ─────────────────────────────────────────────

export function SimpleBarChart({
  data, xKey, barKey, color, horizontal = false,
}: {
  data: Record<string, unknown>[];
  xKey: string;
  barKey: string;
  color: string;
  horizontal?: boolean;
}) {
  const handleBarClick = useCallback((entry: any) => {
    const clauseType = entry?.[xKey];
    if (clauseType) {
      analyticsBus.emit("CLAUSE_SELECTED", { clauseType: String(clauseType) });
    }
  }, [xKey]);

  if (horizontal) {
    const sorted = [...data].sort((a, b) => (Number(b[barKey]) || 0) - (Number(a[barKey]) || 0));
    return (
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={sorted} layout="vertical" margin={{ top: 5, right: 20, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#F3F4F6" horizontal={false} />
          <XAxis type="number" tick={{ fontSize: 10, fill: "#9CA3AF" }} axisLine={false} tickLine={false} />
          <YAxis
            type="category"
            dataKey={xKey}
            tick={{ fontSize: 9, fill: "#6B7280" }}
            axisLine={false}
            tickLine={false}
            width={90}
            tickFormatter={(v: string) => v.replace(/_/g, " ").length > 14 ? v.replace(/_/g, " ").slice(0, 13) + "…" : v.replace(/_/g, " ")}
          />
          <Tooltip content={<ChartTooltip />} />
          <Bar dataKey={barKey} name="Count" fill={color} radius={[0, 3, 3, 0]} onClick={handleBarClick} style={{ cursor: "pointer" }} />
        </BarChart>
      </ResponsiveContainer>
    );
  }

  return (
    <ResponsiveContainer width="100%" height="100%">
      <BarChart data={data} margin={{ top: 5, right: 10, left: -10, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#F3F4F6" />
        <XAxis dataKey={xKey} tick={{ fontSize: 10, fill: "#9CA3AF" }} axisLine={false} tickLine={false} />
        <YAxis tick={{ fontSize: 10, fill: "#9CA3AF" }} axisLine={false} tickLine={false} />
        <Tooltip content={<ChartTooltip />} />
        <Bar dataKey={barKey} name="Count" fill={color} radius={[3, 3, 0, 0]} onClick={handleBarClick} style={{ cursor: "pointer" }} />
      </BarChart>
    </ResponsiveContainer>
  );
}

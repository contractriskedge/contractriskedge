"use client";

import React from "react";
import { motion } from "framer-motion";
import {
  DollarSign, AlertTriangle, Clock, RefreshCw, Brain, Scale, AlertOctagon, ClipboardCheck,
  TrendingUp, TrendingDown, Minus,
} from "lucide-react";
import type { KpiMetric, AlertSeverity } from "./types";

const iconMap: Record<string, React.ReactNode> = {
  DollarSign: <DollarSign className="w-5 h-5" />,
  AlertTriangle: <AlertTriangle className="w-5 h-5" />,
  Clock: <Clock className="w-5 h-5" />,
  RefreshCw: <RefreshCw className="w-5 h-5" />,
  Brain: <Brain className="w-5 h-5" />,
  Scale: <Scale className="w-5 h-5" />,
  AlertOctagon: <AlertOctagon className="w-5 h-5" />,
  ClipboardCheck: <ClipboardCheck className="w-5 h-5" />,
};

const severityBorders: Record<AlertSeverity, string> = {
  critical: "border-l-red-500",
  warning: "border-l-orange-500",
  info: "border-l-blue-500",
  success: "border-l-green-500",
};

const severityIcons: Record<AlertSeverity, React.ReactNode> = {
  critical: <AlertTriangle className="w-3 h-3 text-red-500" />,
  warning: <AlertOctagon className="w-3 h-3 text-orange-500" />,
  info: <Clock className="w-3 h-3 text-blue-500" />,
  success: <Brain className="w-3 h-3 text-green-500" />,
};

// ── Mini Sparkline ─────────────────────────────────────────────────────────

function Sparkline({ data, color }: { data: number[]; color: string }) {
  const max = Math.max(...data);
  const min = Math.min(...data);
  const range = max - min || 1;
  const w = 80;
  const h = 28;
  const points = data.map((v, i) => `${(i / (data.length - 1)) * w},${h - ((v - min) / range) * h}`).join(" ");

  return (
    <svg width={w} height={h} className="flex-shrink-0" aria-hidden="true">
      <polyline
        fill="none"
        stroke={color}
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
        points={points}
      />
    </svg>
  );
}

// ── KPI Card ────────────────────────────────────────────────────────────────

interface KpiCardProps {
  metric: KpiMetric;
  index: number;
}

export function KpiCard({ metric, index }: KpiCardProps) {
  const TrendIcon = metric.trendDirection === "up" ? TrendingUp : metric.trendDirection === "down" ? TrendingDown : Minus;
  const trendColor = metric.trendDirection === "up"
    ? (metric.severity === "critical" || metric.severity === "warning" ? "text-red-500" : "text-green-500")
    : metric.trendDirection === "down"
    ? (metric.severity === "critical" || metric.severity === "warning" ? "text-green-500" : "text-red-500")
    : "text-gray-400";

  const strokeColor = metric.severity === "critical" ? "#EF4444"
    : metric.severity === "warning" ? "#F97316"
    : metric.severity === "success" ? "#22C55E"
    : "#3B82F6";

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay: index * 0.05 }}
      className={`relative bg-white rounded-xl border border-gray-200 shadow-sm hover:shadow-md transition-all duration-200 border-l-4 ${severityBorders[metric.severity]} group cursor-pointer`}
      whileHover={{ y: -2, scale: 1.01 }}
      title={metric.tooltip}
    >
      <div className="p-4">
        {/* Top row: icon + severity indicator */}
        <div className="flex items-center justify-between mb-3">
          <div className={`w-9 h-9 rounded-lg flex items-center justify-center bg-gradient-to-br ${metric.color} text-white shadow-sm`}>
            {iconMap[metric.icon] || <DollarSign className="w-5 h-5" />}
          </div>
          <div className="flex items-center gap-1 text-[10px] text-gray-400 opacity-0 group-hover:opacity-100 transition-opacity">
            {severityIcons[metric.severity]}
            <span className="capitalize">{metric.severity}</span>
          </div>
        </div>

        {/* Value + sparkline */}
        <div className="flex items-center justify-between">
          <div>
            <p className="text-2xl font-bold text-navy-900 tabular-nums tracking-tight">{metric.value}</p>
            <p className="text-[11px] text-gray-500 mt-0.5 font-medium">{metric.label}</p>
          </div>
          <Sparkline data={metric.sparklineData} color={strokeColor} />
        </div>

        {/* Trend */}
        <div className="flex items-center gap-1.5 mt-2 pt-2 border-t border-gray-100">
          <TrendIcon className={`w-3.5 h-3.5 ${trendColor}`} />
          <span className={`text-xs font-semibold tabular-nums ${trendColor}`}>
            {metric.trend > 0 ? "+" : ""}{metric.trend}%
          </span>
          <span className="text-[10px] text-gray-400 ml-auto">vs last month</span>
        </div>
      </div>

      {/* Drill-down overlay */}
      <div className="absolute inset-0 rounded-xl ring-1 ring-inset ring-black/0 group-hover:ring-navy-200/50 transition-all pointer-events-none" />
    </motion.div>
  );
}

// ── KPI Grid ────────────────────────────────────────────────────────────────

interface KpiGridProps {
  metrics: KpiMetric[];
}

export function KpiGrid({ metrics }: KpiGridProps) {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      {metrics.map((metric, i) => (
        <KpiCard key={metric.id} metric={metric} index={i} />
      ))}
    </div>
  );
}

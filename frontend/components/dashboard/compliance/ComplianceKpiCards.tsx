"use client";

import React from "react";
import { motion } from "framer-motion";
import {
  Shield, AlertTriangle, Gavel, FileSearch, Clock, Building2,
  ClipboardCheck, ListChecks, TrendingUp, TrendingDown, Minus,
} from "lucide-react";
import type { ComplianceKpi } from "./types";

const iconMap: Record<string, React.ReactNode> = {
  Shield: <Shield className="w-4 h-4" />,
  AlertTriangle: <AlertTriangle className="w-4 h-4" />,
  Gavel: <Gavel className="w-4 h-4" />,
  FileSearch: <FileSearch className="w-4 h-4" />,
  Clock: <Clock className="w-4 h-4" />,
  Building2: <Building2 className="w-4 h-4" />,
  ClipboardCheck: <ClipboardCheck className="w-4 h-4" />,
  ListChecks: <ListChecks className="w-4 h-4" />,
};

function MiniSparkline({ data, color }: { data: number[]; color: string }) {
  const max = Math.max(...data); const min = Math.min(...data); const range = max - min || 1;
  const w = 64, h = 22;
  const pts = data.map((v, i) => `${(i / (data.length - 1)) * w},${h - ((v - min) / range) * h}`).join(" ");
  return <svg width={w} height={h} className="flex-shrink-0 opacity-70" aria-hidden="true"><polyline fill="none" stroke={color} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" points={pts} /></svg>;
}

export function ComplianceKpiCards({ metrics, onKpiClick }: { metrics: ComplianceKpi[]; onKpiClick?: (id: string) => void }) {
  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-2.5">
      {metrics.map((m, i) => {
        const TrendIcon = m.trendDirection === "up" ? TrendingUp : m.trendDirection === "down" ? TrendingDown : Minus;
        const isBadUp = m.id === "expiring-docs";
        const tc = (m.trendDirection === "up" && isBadUp) ? "text-red-500" :
          (m.trendDirection === "down" && m.id === "open-gaps" || m.id === "violations" || m.id === "missing-clauses" || m.id === "high-risk-vendors" || m.id === "remediation-tasks") ? "text-green-500" :
          m.trendDirection === "up" ? "text-green-500" :
          m.trendDirection === "down" ? "text-red-500" : "text-gray-400";
        const strokeColor = m.severity === "critical" ? "#EF4444" : m.severity === "warning" ? "#F97316" : m.severity === "success" ? "#22C55E" : "#3B82F6";
        return (
          <motion.button key={m.id} initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.04 }}
            className="bg-white rounded-lg border border-gray-200 shadow-sm hover:shadow-md transition-all p-3 cursor-pointer group text-left w-full"
            whileHover={{ y: -1, scale: 1.02 }} onClick={() => onKpiClick?.(m.id)} title={m.tooltip}>
            <div className="flex items-center justify-between mb-2">
              <div className={`w-7 h-7 rounded-lg flex items-center justify-center bg-gradient-to-br ${m.color} text-white shadow-xs`}>{iconMap[m.icon] || <Shield className="w-4 h-4" />}</div>
              <MiniSparkline data={m.sparklineData} color={strokeColor} />
            </div>
            <p className="text-lg font-bold text-navy-900 tabular-nums tracking-tight">{m.value}</p>
            <p className="text-[10px] text-gray-500 mt-0.5 truncate">{m.label}</p>
            <div className="flex items-center gap-1 mt-1 pt-1 border-t border-gray-50">
              <TrendIcon className={`w-3 h-3 ${tc}`} />
              <span className={`text-[10px] font-semibold tabular-nums ${tc}`}>{m.trend > 0 ? "+" : ""}{m.trend}%</span>
            </div>
          </motion.button>
        );
      })}
    </div>
  );
}

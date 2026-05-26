"use client";

import React from "react";
import { motion } from "framer-motion";
import { FileText, Search, AlertTriangle, Clock, RefreshCw, Brain, PenSquare, DollarSign, TrendingUp, TrendingDown, Minus } from "lucide-react";
import type { ContractKpi } from "./types";

const iconMap: Record<string, React.ReactNode> = {
  FileText: <FileText className="w-4.5 h-4.5" />,
  Search: <Search className="w-4.5 h-4.5" />,
  AlertTriangle: <AlertTriangle className="w-4.5 h-4.5" />,
  Clock: <Clock className="w-4.5 h-4.5" />,
  RefreshCw: <RefreshCw className="w-4.5 h-4.5" />,
  Brain: <Brain className="w-4.5 h-4.5" />,
  PenSquare: <PenSquare className="w-4.5 h-4.5" />,
  DollarSign: <DollarSign className="w-4.5 h-4.5" />,
};

function MiniSparkline({ data, color }: { data: number[]; color: string }) {
  const max = Math.max(...data);
  const min = Math.min(...data);
  const range = max - min || 1;
  const w = 64, h = 22;
  const pts = data.map((v, i) => `${(i / (data.length - 1)) * w},${h - ((v - min) / range) * h}`).join(" ");
  return (
    <svg width={w} height={h} className="flex-shrink-0 opacity-70" aria-hidden="true">
      <polyline fill="none" stroke={color} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" points={pts} />
    </svg>
  );
}

export function ContractKpiCards({ metrics }: { metrics: ContractKpi[] }) {
  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-2.5">
      {metrics.map((m, i) => {
        const TrendIcon = m.trendDirection === "up" ? TrendingUp : m.trendDirection === "down" ? TrendingDown : Minus;
        const trendIsBad = (m.trendDirection === "up" && (m.id === "high-risk" || m.id === "ai-flags" || m.id === "auto-renewals")) || (m.trendDirection === "down" && (m.id === "under-review" || m.id === "expiring" || m.id === "pending-signatures"));
        const trendColor = trendIsBad ? "text-red-500" : "text-green-500";
        return (
          <motion.div
            key={m.id}
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.04 }}
            className="bg-white rounded-lg border border-gray-200 shadow-sm hover:shadow-md transition-all duration-200 p-3 cursor-pointer group"
            whileHover={{ y: -1, scale: 1.02 }}
            title={m.tooltip}
          >
            <div className="flex items-center justify-between mb-2">
              <div className={`w-7 h-7 rounded-lg flex items-center justify-center bg-gradient-to-br ${m.color} text-white shadow-xs`}>
                {iconMap[m.icon] || <FileText className="w-4 h-4" />}
              </div>
              <MiniSparkline data={m.sparklineData} color={m.color.includes("red") ? "#EF4444" : m.color.includes("blue") ? "#3B82F6" : m.color.includes("green") ? "#22C55E" : "#EAB308"} />
            </div>
            <p className="text-lg font-bold text-navy-900 tabular-nums tracking-tight">{m.value}</p>
            <p className="text-[10px] text-gray-500 mt-0.5 truncate">{m.label}</p>
            <div className="flex items-center gap-1 mt-1 pt-1 border-t border-gray-50">
              <TrendIcon className={`w-3 h-3 ${trendColor}`} />
              <span className={`text-[10px] font-semibold tabular-nums ${trendColor}`}>{m.trend > 0 ? "+" : ""}{m.trend}%</span>
            </div>
          </motion.div>
        );
      })}
    </div>
  );
}

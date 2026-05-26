"use client";

import React from "react";
import { motion } from "framer-motion";
import { Share2, Link, AlertTriangle, FileEdit, ClipboardCheck, Layers, Building2, Unlink, TrendingUp, TrendingDown, Minus } from "lucide-react";
import type { GraphKpi } from "./types";

const iconMap: Record<string, React.ReactNode> = {
  Share2: <Share2 className="w-4 h-4" />, Link: <Link className="w-4 h-4" />, AlertTriangle: <AlertTriangle className="w-4 h-4" />,
  FileEdit: <FileEdit className="w-4 h-4" />, ClipboardCheck: <ClipboardCheck className="w-4 h-4" />, Layers: <Layers className="w-4 h-4" />,
  Building2: <Building2 className="w-4 h-4" />, Unlink: <Unlink className="w-4 h-4" />,
};

export function GraphKpiCards({ metrics }: { metrics: GraphKpi[] }) {
  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-2.5">
      {metrics.map((m, i) => {
        const TrendIcon = m.trendDirection === "up" ? TrendingUp : m.trendDirection === "down" ? TrendingDown : Minus;
        const isBad = m.trendDirection === "up" && (m.id === "risk-chains" || m.id === "cross-bu");
        const tc = isBad ? "text-red-500" : "text-green-500";
        return (
          <motion.div key={m.id} initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.04 }}
            className="bg-white rounded-lg border border-gray-200 shadow-sm hover:shadow-md transition-all p-3 cursor-pointer group" whileHover={{ y: -1, scale: 1.02 }} title={m.tooltip}>
            <div className="flex items-center justify-between mb-2">
              <div className={`w-7 h-7 rounded-lg flex items-center justify-center bg-gradient-to-br ${m.color} text-white shadow-xs`}>{iconMap[m.icon] || <Share2 className="w-4 h-4" />}</div>
            </div>
            <p className="text-lg font-bold text-navy-900 tabular-nums tracking-tight">{m.value}</p>
            <p className="text-[10px] text-gray-500 mt-0.5 truncate">{m.label}</p>
            <div className="flex items-center gap-1 mt-1 pt-1 border-t border-gray-50">
              <TrendIcon className={`w-3 h-3 ${tc}`} />
              <span className={`text-[10px] font-semibold tabular-nums ${tc}`}>{m.trend > 0 ? "+" : ""}{m.trend}%</span>
            </div>
          </motion.div>
        );
      })}
    </div>
  );
}

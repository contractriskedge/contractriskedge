"use client";

import React from "react";
import { motion } from "framer-motion";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from "recharts";
import type { BenchmarkData } from "./types";

function CustomTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-white border border-gray-200 rounded-lg shadow-lg p-2.5 text-xs">
      <p className="font-semibold text-navy-900 mb-1">{label}</p>
      {payload.map((entry: any, i: number) => (
        <div key={i} className="flex items-center gap-2 py-0.5">
          <div className="w-2 h-2 rounded-full" style={{ backgroundColor: entry.color }} />
          <span className="text-gray-600">{entry.name}:</span>
          <span className="font-medium">{entry.value}/10</span>
        </div>
      ))}
    </div>
  );
}

export function BenchmarkChart({ data }: { data: BenchmarkData[] }) {
  const chartData = data.map((d) => ({
    name: d.clauseType, yourScore: d.yourScore, marketMedian: d.marketMedian,
    marketP25: d.marketP25, marketP75: d.marketP75,
  }));

  return (
    <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}
      className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
      <div className="px-4 py-3 border-b border-gray-100">
        <h3 className="text-xs font-semibold text-navy-900">Clause Benchmark Comparison</h3>
        <p className="text-[10px] text-gray-500 mt-0.5">Your scores vs market median (P25–P75 range)</p>
      </div>
      <div className="p-4">
        <div className="w-full h-72">
          <ResponsiveContainer width="100%" height={190}>
            <BarChart data={chartData} margin={{ top: 5, right: 10, left: -10, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#F3F4F6" />
              <XAxis dataKey="name" tick={{ fontSize: 8, fill: "#6B7280" }} axisLine={false} tickLine={false} angle={-25} textAnchor="end" height={50} interval={0} />
              <YAxis domain={[0, 10]} tick={{ fontSize: 11, fill: "#9CA3AF" }} axisLine={false} tickLine={false} />
              <Tooltip content={<CustomTooltip />} />
              <Bar dataKey="marketMedian" name="Market Median" fill="#1B3A6B" radius={[2, 2, 0, 0]} />
              <Bar dataKey="yourScore" name="Your Score" radius={[2, 2, 0, 0]}>
                {chartData.map((entry, i) => (
                  <Cell key={i} fill={entry.yourScore > entry.marketP75 ? "#DC2626" : entry.yourScore > entry.marketMedian ? "#F97316" : "#22C55E"} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </motion.div>
  );
}

"use client";

import React from "react";
import { motion } from "framer-motion";
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from "recharts";
import { DollarSign, TrendingUp, Shield, AlertTriangle } from "lucide-react";
import type { FinancialExposure, RiskLevel } from "./types";
import { RISK_BG_COLORS, RISK_BG_LIGHT, RISK_TEXT_COLORS } from "./types";

const COLORS = ["#DC2626", "#EA580C", "#EAB308", "#3B82F6", "#8B5CF6", "#6B7280"];

// ── Donut Chart ─────────────────────────────────────────────────────────────

function DonutChart({ data }: { data: { name: string; value: number; color?: string }[] }) {
  return (
    <div className="h-48">
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie
            data={data}
            cx="50%"
            cy="50%"
            innerRadius={50}
            outerRadius={70}
            paddingAngle={3}
            dataKey="value"
          >
            {data.map((entry, i) => (
              <Cell key={i} fill={entry.color || COLORS[i % COLORS.length]} strokeWidth={0} />
            ))}
          </Pie>
          <Tooltip
            content={({ active, payload }) =>
              active && payload?.length ? (
                <div className="bg-white border border-gray-200 rounded-lg shadow-lg p-2.5 text-xs">
                  <p className="font-medium text-gray-900">{payload[0].name}</p>
                  <p className="text-gray-600">${payload[0].value}M ({((payload[0].value as number) / data.reduce((s, d) => s + d.value, 0) * 100).toFixed(1)}%)</p>
                </div>
              ) : null
            }
          />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
}

// ── Section Card ────────────────────────────────────────────────────────────

function Card({ title, subtitle, children, className = "" }: {
  title: string; subtitle?: string; children: React.ReactNode; className?: string;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      className={`bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden ${className}`}
    >
      <div className="px-4 py-3 border-b border-gray-100">
        <h3 className="text-xs font-semibold text-navy-900">{title}</h3>
        {subtitle && <p className="text-[10px] text-gray-500 mt-0.5">{subtitle}</p>}
      </div>
      <div className="p-4">{children}</div>
    </motion.div>
  );
}

// ── Main Component ──────────────────────────────────────────────────────────

interface FinancialExposurePanelProps {
  data: FinancialExposure;
}

export function FinancialExposurePanel({ data }: FinancialExposurePanelProps) {
  const gapPct = Math.round((data.gapAmount / data.totalExposure) * 100);

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <DollarSign className="w-5 h-5 text-navy-700" />
        <h2 className="text-sm font-semibold text-navy-900">Financial Exposure Analysis</h2>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Left: Exposure breakdown */}
        <Card title="Exposure Breakdown" subtitle={`Total: $${data.totalExposure}M • Insured: $${data.insuredAmount}M`}>
          <div className="flex items-start gap-4">
            <div className="flex-shrink-0">
              <DonutChart
                data={data.breakdown.map((b, i) => ({ name: b.category, value: b.amount, color: COLORS[i] }))}
              />
            </div>
            <div className="flex-1 space-y-1.5 pt-1">
              {data.breakdown.map((b) => (
                <div key={b.category} className="flex items-center justify-between text-xs">
                  <span className="text-gray-600 truncate max-w-[100px]">{b.category}</span>
                  <div className="flex items-center gap-2">
                    <div className="w-16 h-1.5 bg-gray-200 rounded-full overflow-hidden">
                      <div className="h-full rounded-full bg-navy-600" style={{ width: `${b.percentage}%` }} />
                    </div>
                    <span className="font-medium tabular-nums text-gray-800 w-12 text-right">${b.amount}M</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </Card>

        {/* Right: Insurance Gap */}
        <Card
          title="Insurance Coverage Gap"
          subtitle={`${gapPct}% of total exposure uninsured — $${data.gapAmount}M gap`}
        >
          {/* Gap meter */}
          <div className="mb-4">
            <div className="flex items-center justify-between text-xs mb-1.5">
              <span className="text-gray-500">Insured</span>
              <span className="font-semibold text-green-600">${data.insuredAmount}M</span>
            </div>
            <div className="h-3 bg-gray-200 rounded-full overflow-hidden flex">
              <div className="h-full bg-green-500 transition-all" style={{ width: `${(data.insuredAmount / data.totalExposure) * 100}%` }} />
              <div className="h-full bg-red-400 transition-all" style={{ width: `${(data.gapAmount / data.totalExposure) * 100}%` }} />
            </div>
            <div className="flex items-center justify-between text-xs mt-1">
              <span className="text-red-600 font-medium">Gap: ${data.gapAmount}M</span>
              <span className="text-gray-400">Total: ${data.totalExposure}M</span>
            </div>
          </div>

          {/* Gap details */}
          <div className="space-y-1.5">
            <p className="text-[10px] font-semibold text-gray-500 uppercase">Gap Details</p>
            {data.insuranceGaps.map((gap) => {
              const level = gap.risk as RiskLevel;
              return (
                <div key={gap.area} className="flex items-center justify-between text-xs py-1">
                  <div className="flex items-center gap-1.5">
                    <span className={`w-1.5 h-1.5 rounded-full ${RISK_BG_COLORS[level]}`} />
                    <span className="text-gray-600">{gap.area}</span>
                  </div>
                  <span className="font-medium text-red-600">${gap.gap}M</span>
                </div>
              );
            })}
          </div>
        </Card>
      </div>

      {/* Vendor Concentration */}
      <Card title="Vendor Concentration Risk" subtitle="Top vendors by financial exposure">
        <div className="space-y-2">
          {data.vendorConcentration.map((v) => (
            <div key={v.vendor} className="flex items-center gap-3">
              <span className="text-xs text-gray-700 w-32 truncate font-medium">{v.vendor}</span>
              <div className="flex-1 h-2 bg-gray-200 rounded-full overflow-hidden">
                <div
                  className="h-full rounded-full bg-gradient-to-r from-orange-400 to-red-500"
                  style={{ width: `${v.percentage}%` }}
                />
              </div>
              <span className="text-xs font-medium tabular-nums text-gray-800 w-16 text-right">${v.exposure}M</span>
              <span className="text-[10px] text-gray-400 w-10 text-right">{v.percentage}%</span>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}

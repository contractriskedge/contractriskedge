"use client";

import React from "react";
import { motion } from "framer-motion";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ScatterChart, Scatter, Cell, ReferenceLine, Legend } from "recharts";
import type { ClauseBenchmark, IndustryComparison, BenchmarkDistribution } from "./types";

const COLORS = { navy: "#1B3A6B", gold: "#C9A84C", red: "#DC2626", orange: "#EA580C", green: "#22C55E", blue: "#3B82F6", purple: "#8B5CF6" };

function CustomTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-white border border-gray-200 rounded-lg shadow-lg p-3 text-xs max-w-[200px]">
      <p className="font-semibold text-navy-900 mb-1.5">{label}</p>
      {payload.map((entry: any, i: number) => (
        <div key={i} className="flex items-center gap-2 py-0.5">
          <div className="w-2 h-2 rounded-full" style={{ backgroundColor: entry.color }} />
          <span className="text-gray-600">{entry.name}:</span>
          <span className="font-medium text-gray-900">{typeof entry.value === "number" ? entry.value.toFixed(1) : entry.value}</span>
        </div>
      ))}
    </div>
  );
}

function SectionCard({ title, subtitle, children, className = "" }: { title: string; subtitle?: string; children: React.ReactNode; className?: string }) {
  return (
    <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className={`bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden ${className}`}>
      <div className="px-4 py-3 border-b border-gray-100"><h3 className="text-xs font-semibold text-navy-900">{title}</h3>{subtitle && <p className="text-[10px] text-gray-500 mt-0.5">{subtitle}</p>}</div>
      <div className="p-4">{children}</div>
    </motion.div>
  );
}

// ── 1. Clause Benchmark Distribution ────────────────────────────────────────

export function ClauseBenchmarkChart({ data }: { data: ClauseBenchmark[] }) {
  const chartData = data.map((d) => ({ name: d.clauseType, yourScore: d.yourScore, marketMedian: d.marketMedian, marketP75: d.marketP75, marketP25: d.marketP25 }));
  return (
    <SectionCard title="Clause Benchmark Distribution" subtitle="Your scores vs market median (P25–P75 range)">
      <div className="h-72">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData} margin={{ top: 5, right: 10, left: -10, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#F3F4F6" />
            <XAxis dataKey="name" tick={{ fontSize: 8, fill: "#6B7280" }} axisLine={false} tickLine={false} angle={-35} textAnchor="end" height={60} interval={0} />
            <YAxis domain={[0, 10]} tick={{ fontSize: 11, fill: "#9CA3AF" }} axisLine={false} tickLine={false} />
            <Tooltip content={<CustomTooltip />} />
            <Legend wrapperStyle={{ fontSize: "10px", paddingTop: "8px" }} iconType="rect" iconSize={7} />
            <Bar dataKey="marketP25" name="Market P25" fill="#E5E7EB" stackId="range" />
            <Bar dataKey="marketP75" name="Market P75" fill="#E5E7EB" stackId="range" />
            <Bar dataKey="marketMedian" name="Market Median" fill={COLORS.navy} radius={[2, 2, 0, 0]} />
            <Bar dataKey="yourScore" name="Your Score" fill={COLORS.gold} radius={[2, 2, 0, 0]}>
              {chartData.map((entry, i) => (
                <Cell key={i} fill={entry.yourScore > entry.marketP75 ? COLORS.red : entry.yourScore > entry.marketMedian ? COLORS.orange : COLORS.green} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </SectionCard>
  );
}

// ── 2. Deviation Heatmap ────────────────────────────────────────────────────

export function DeviationHeatmap({ data }: { data: ClauseBenchmark[] }) {
  const chartData = data.map((d) => ({ name: d.clauseType, deviation: d.deviationPercent, direction: d.direction }));
  return (
    <SectionCard title="Deviation from Market (%)" subtitle="Positive = above market (worse for client)">
      <div className="h-72">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData} layout="vertical" margin={{ top: 5, right: 30, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#F3F4F6" horizontal={false} />
            <XAxis type="number" tick={{ fontSize: 11, fill: "#9CA3AF" }} axisLine={false} tickLine={false} />
            <YAxis type="category" dataKey="name" tick={{ fontSize: 8, fill: "#6B7280" }} axisLine={false} tickLine={false} width={90} />
            <Tooltip content={<CustomTooltip />} />
            <Bar dataKey="deviation" name="Deviation %" radius={[0, 4, 4, 0]}>
              {chartData.map((entry, i) => (
                <Cell key={i} fill={entry.deviation > 50 ? COLORS.red : entry.deviation > 25 ? COLORS.orange : entry.deviation > 10 ? COLORS.blue : COLORS.green} />
              ))}
            </Bar>
            <ReferenceLine x={0} stroke="#9CA3AF" strokeDasharray="3 3" />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </SectionCard>
  );
}

// ── 3. Industry Comparison ──────────────────────────────────────────────────

export function IndustryComparisonChart({ data }: { data: IndustryComparison[] }) {
  const chartData = data.map((d) => ({ name: d.industry, yourScore: d.yourScore, industryAvg: d.industryAvg, industryP10: d.industryP10, industryP90: d.industryP90 }));
  return (
    <SectionCard title="Industry Comparison" subtitle="Your risk profile vs industry averages">
      <div className="h-72">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData} margin={{ top: 5, right: 10, left: -10, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#F3F4F6" />
            <XAxis dataKey="name" tick={{ fontSize: 9, fill: "#6B7280" }} axisLine={false} tickLine={false} angle={-20} textAnchor="end" height={40} />
            <YAxis domain={[0, 10]} tick={{ fontSize: 11, fill: "#9CA3AF" }} axisLine={false} tickLine={false} />
            <Tooltip content={<CustomTooltip />} />
            <Legend wrapperStyle={{ fontSize: "10px", paddingTop: "8px" }} iconType="rect" iconSize={7} />
            <Bar dataKey="industryAvg" name="Industry Avg" fill={COLORS.navy} radius={[4, 4, 0, 0]} />
            <Bar dataKey="yourScore" name="Your Score" fill={COLORS.gold} radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </SectionCard>
  );
}

// ── 4. Vendor Aggressiveness ────────────────────────────────────────────────

export function VendorAggressivenessChart({ data }: { data: { vendor: string; score: number }[] }) {
  return (
    <SectionCard title="Vendor Aggressiveness Index" subtitle="Higher = more vendor-favorable terms">
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={[...data].sort((a, b) => b.score - a.score)} layout="vertical" margin={{ top: 5, right: 30, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#F3F4F6" horizontal={false} />
            <XAxis type="number" domain={[0, 10]} tick={{ fontSize: 11, fill: "#9CA3AF" }} axisLine={false} tickLine={false} />
            <YAxis type="category" dataKey="vendor" tick={{ fontSize: 9, fill: "#6B7280" }} axisLine={false} tickLine={false} width={100} />
            <Tooltip content={<CustomTooltip />} />
            <Bar dataKey="score" name="Aggressiveness" radius={[0, 4, 4, 0]}>
              {data.map((entry, i) => <Cell key={i} fill={entry.score >= 8 ? COLORS.red : entry.score >= 6 ? COLORS.orange : entry.score >= 4 ? COLORS.blue : COLORS.green} />)}
            </Bar>
            <ReferenceLine x={5} stroke="#9CA3AF" strokeDasharray="3 3" label={{ value: "Market Avg", position: "top", fontSize: 9, fill: "#9CA3AF" }} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </SectionCard>
  );
}

// ── 5. Compliance Benchmark ─────────────────────────────────────────────────

export function ComplianceBenchmarkChart({ data }: { data: { regulation: string; yourCoverage: number; marketCoverage: number }[] }) {
  return (
    <SectionCard title="Compliance Benchmark Coverage" subtitle="Your coverage vs market standards (%)">
      <div className="h-56">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 5, right: 10, left: -10, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#F3F4F6" />
            <XAxis dataKey="regulation" tick={{ fontSize: 10, fill: "#6B7280" }} axisLine={false} tickLine={false} />
            <YAxis domain={[0, 100]} tick={{ fontSize: 11, fill: "#9CA3AF" }} axisLine={false} tickLine={false} />
            <Tooltip content={<CustomTooltip />} />
            <Legend wrapperStyle={{ fontSize: "10px", paddingTop: "8px" }} iconType="rect" iconSize={7} />
            <Bar dataKey="marketCoverage" name="Market Coverage %" fill={COLORS.navy} radius={[4, 4, 0, 0]} />
            <Bar dataKey="yourCoverage" name="Your Coverage %" fill={COLORS.gold} radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </SectionCard>
  );
}

// ── 6. Clause Frequency & Risk ──────────────────────────────────────────────

export function ClauseFrequencyChart({ data }: { data: { clauseType: string; frequency: number; riskScore: number }[] }) {
  return (
    <SectionCard title="Clause Library: Frequency vs Risk" subtitle="Bubble size = frequency in corpus">
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <ScatterChart margin={{ top: 5, right: 20, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#F3F4F6" />
            <XAxis dataKey="frequency" name="Frequency %" domain={[0, 100]} tick={{ fontSize: 11, fill: "#9CA3AF" }} axisLine={false} tickLine={false} />
            <YAxis dataKey="riskScore" name="Risk Score" domain={[0, 10]} tick={{ fontSize: 11, fill: "#9CA3AF" }} axisLine={false} tickLine={false} />
            <Tooltip content={({ active, payload }) => active && payload?.length ? (
              <div className="bg-white border border-gray-200 rounded-lg shadow-lg p-2.5 text-xs">
                <p className="font-semibold text-navy-900">{payload[0].payload.clauseType}</p>
                <p className="text-gray-600">Frequency: {payload[0].value}%</p>
                <p className="text-gray-600">Risk: {payload[0].payload.riskScore}/10</p>
              </div>
            ) : null} />
            <Scatter data={data} fill={COLORS.navy}>
              {data.map((entry, i) => (
                <Cell key={i} fill={entry.riskScore >= 7 ? COLORS.red : entry.riskScore >= 5 ? COLORS.orange : entry.riskScore >= 3 ? COLORS.blue : COLORS.green} />
              ))}
            </Scatter>
          </ScatterChart>
        </ResponsiveContainer>
      </div>
    </SectionCard>
  );
}

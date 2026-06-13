"use client";

import React from "react";
import { motion } from "framer-motion";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from "recharts";
import { Activity, AlertTriangle, CheckCircle, TrendingUp, TrendingDown, BarChart3, DollarSign, ShieldCheck, PieChart } from "lucide-react";
import type { SlaMetric, FinancialExposure, ObligationRecord } from "./types";

function PanelEmptyState({ icon, title, message }: { icon: React.ReactNode; title: string; message: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-8 px-4 text-center">
      <div className="w-10 h-10 rounded-full bg-gray-50 border border-gray-100 flex items-center justify-center mb-2.5 text-gray-300">
        {icon}
      </div>
      <p className="text-[11px] font-medium text-gray-500">{title}</p>
      <p className="text-[10px] text-gray-400 mt-0.5 max-w-[220px]">{message}</p>
    </div>
  );
}

function CustomTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-white border border-gray-200 rounded-lg shadow-lg p-2.5 text-xs">
      <p className="font-semibold text-navy-900 mb-1">{label}</p>
      {payload.map((entry: any, i: number) => (
        <div key={i} className="flex items-center gap-2 py-0.5">
          <div className="w-2 h-2 rounded-full" style={{ backgroundColor: entry.color }} />
          <span className="text-gray-600">{entry.name}:</span>
          <span className="font-medium">{entry.value}{entry.name.includes("Performance") ? "%" : "$"}{entry.name.includes("Exposure") ? "M" : ""}</span>
        </div>
      ))}
    </div>
  );
}

function SectionCard({ title, subtitle, children }: { title: string; subtitle?: string; children: React.ReactNode }) {
  return (
    <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
      <div className="px-4 py-3 border-b border-gray-100"><h3 className="text-xs font-semibold text-navy-900">{title}</h3>{subtitle && <p className="text-[10px] text-gray-500 mt-0.5">{subtitle}</p>}</div>
      <div className="p-4">{children}</div>
    </motion.div>
  );
}

// ── SLA Performance Chart ───────────────────────────────────────────────────

export function SlaPerformanceChart({ data, predictions }: { data: SlaMetric[]; predictions?: any[] }) {
  const chartData = data.map((d) => ({ name: d.vendor, performance: d.performance, target: parseFloat(d.slaTarget.replace("%", "")) }));
  return (
    <SectionCard title="SLA Performance by Vendor" subtitle={data.length > 0 ? "Actual vs target performance %" : "No vendor SLA data yet"}>
      {chartData.length === 0 ? (
        <PanelEmptyState
          icon={<BarChart3 className="w-5 h-5" />}
          title="No SLA performance data"
          message="Vendor SLA metrics will appear once SLA-tracked obligations are active."
        />
      ) : (
        <div className="h-48">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData} margin={{ top: 5, right: 10, left: -10, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#F3F4F6" />
              <XAxis dataKey="name" tick={{ fontSize: 8, fill: "#6B7280" }} axisLine={false} tickLine={false} angle={-20} textAnchor="end" height={40} />
              <YAxis domain={[97, 100]} tick={{ fontSize: 11, fill: "#9CA3AF" }} axisLine={false} tickLine={false} />
              <Tooltip content={<CustomTooltip />} />
              <Bar dataKey="performance" name="Performance %" radius={[4, 4, 0, 0]}>
                {chartData.map((entry, i) => (
                  <Cell key={i} fill={entry.performance < entry.target ? "#DC2626" : entry.performance < entry.target + 0.3 ? "#F97316" : "#22C55E"} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </SectionCard>
  );
}

// ── SLA Vendor Table ────────────────────────────────────────────────────────

export function SlaVendorTable({ data, breaches }: { data: SlaMetric[]; breaches?: any[] }) {
  return (
    <SectionCard title="SLA Governance" subtitle={data.length > 0 ? "Vendor SLA status and breach tracking" : "No vendors under SLA governance"}>
      {data.length === 0 ? (
        <PanelEmptyState
          icon={<Activity className="w-5 h-5" />}
          title="No SLA governance records"
          message="Vendor breach tracking and SLA status will populate as obligations are monitored."
        />
      ) : (
      <div className="space-y-1.5">
        {data.map((s) => (
          <div key={s.vendor} className="flex items-center gap-3 p-2 bg-white border border-gray-100 rounded-lg">
            <div className={`w-2 h-2 rounded-full ${s.status === "on_track" ? "bg-green-500" : s.status === "at_risk" ? "bg-yellow-500" : "bg-red-500"}`} />
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-1.5">
                <span className="text-[11px] font-medium text-gray-800">{s.vendor}</span>
                <span className={`text-[9px] font-medium px-1.5 py-0.5 rounded-full ${s.status === "on_track" ? "bg-green-50 text-green-700" : s.status === "at_risk" ? "bg-yellow-50 text-yellow-700" : "bg-red-50 text-red-700"}`}>{s.status.replace(/_/g, " ")}</span>
              </div>
              <div className="flex items-center gap-2 mt-0.5">
                <div className="flex-1 h-1.5 bg-gray-200 rounded-full overflow-hidden">
                  <div className={`h-full rounded-full ${s.status === "breached" ? "bg-red-500" : s.status === "at_risk" ? "bg-yellow-500" : "bg-green-500"}`}
                    style={{ width: `${Math.min(100, s.performance)}%` }} />
                </div>
                <span className="text-[10px] font-medium tabular-nums">{s.performance}%</span>
                <span className="text-[9px] text-gray-400">{s.slaTarget}</span>
                <span className={`text-[9px] flex items-center gap-0.5 ${s.trend >= 0 ? "text-green-500" : "text-red-500"}`}>
                  {s.trend >= 0 ? <TrendingUp className="w-2.5 h-2.5" /> : <TrendingDown className="w-2.5 h-2.5" />}
                  {Math.abs(s.trend).toFixed(2)}%
                </span>
              </div>
            </div>
            {s.breachCount > 0 && <span className="text-[9px] font-medium text-red-600 bg-red-50 px-1.5 py-0.5 rounded">{s.breachCount} breaches</span>}
          </div>
        ))}
      </div>
      )}
    </SectionCard>
  );
}

// ── Financial Exposure ──────────────────────────────────────────────────────

export function FinancialExposurePanel({ data, valueAtRisk }: { data: FinancialExposure[]; valueAtRisk?: any }) {
  const total = data.reduce((s, d) => s + d.totalExposure, 0);
  return (
    <SectionCard title="Financial Exposure Analysis" subtitle={data.length > 0 ? `Total exposure: $${total.toLocaleString()}` : "No financial exposure recorded"}>
      {data.length === 0 ? (
        <PanelEmptyState
          icon={<DollarSign className="w-5 h-5" />}
          title="No financial exposure"
          message="Exposure breakdowns will appear when obligations carry financial impact values."
        />
      ) : (
      <div className="space-y-2">
        {data.map((d) => (
          <div key={d.category} className="space-y-1">
            <div className="flex items-center justify-between text-xs">
              <span className="text-gray-700 font-medium">{d.category}</span>
              <span className="font-bold text-red-600">${d.totalExposure.toLocaleString()}</span>
            </div>
            <div className="h-2 bg-gray-200 rounded-full overflow-hidden flex">
              <div className="h-full bg-green-500" style={{ width: `${(d.recoveredAmount / d.totalExposure) * 100}%` }} />
              <div className="h-full bg-yellow-500" style={{ width: `${(d.atRiskAmount / d.totalExposure) * 100}%` }} />
              <div className="h-full bg-red-500" style={{ width: `${(d.overdueAmount / d.totalExposure) * 100}%` }} />
            </div>
            <div className="flex justify-between text-[9px] text-gray-400">
              <span className="text-green-500">${d.recoveredAmount.toLocaleString()} recovered</span>
              <span className="text-yellow-500">${d.atRiskAmount.toLocaleString()} at risk</span>
              <span className="text-red-500">${d.overdueAmount.toLocaleString()} overdue</span>
            </div>
          </div>
        ))}
      </div>
      )}
    </SectionCard>
  );
}

// ── Compliance Overview (sidebar summary) ───────────────────────────────────

interface KpiSnapshot {
  total_obligations: number;
  active_count: number;
  overdue_count: number;
  completed_count: number;
  breached_count: number;
  compliance_rate: number;
}

export function ComplianceOverviewPanel({ kpis, obligations }: { kpis?: KpiSnapshot | null; obligations: ObligationRecord[] }) {
  const statusCounts = obligations.reduce<Record<string, number>>((acc, o) => {
    acc[o.status] = (acc[o.status] ?? 0) + 1;
    return acc;
  }, {});
  const topStatuses = Object.entries(statusCounts).sort((a, b) => b[1] - a[1]).slice(0, 4);
  const complianceRate = kpis ? Math.min(kpis.compliance_rate, 100) : 100;
  const allClear = kpis ? kpis.overdue_count === 0 && kpis.breached_count === 0 : true;

  return (
    <SectionCard title="Compliance Overview" subtitle="Portfolio health at a glance">
      <div className="space-y-3">
        <div className={`flex items-center gap-2.5 p-2.5 rounded-lg border ${allClear ? "bg-emerald-50 border-emerald-100" : "bg-amber-50 border-amber-100"}`}>
          <div className={`w-8 h-8 rounded-full flex items-center justify-center ${allClear ? "bg-emerald-100 text-emerald-600" : "bg-amber-100 text-amber-600"}`}>
            {allClear ? <ShieldCheck className="w-4 h-4" /> : <AlertTriangle className="w-4 h-4" />}
          </div>
          <div className="min-w-0">
            <p className={`text-[11px] font-semibold ${allClear ? "text-emerald-800" : "text-amber-800"}`}>
              {allClear ? "All systems operational" : "Items require attention"}
            </p>
            <p className="text-[10px] text-gray-500">
              {allClear ? "No overdue or breached obligations" : `${kpis?.overdue_count ?? 0} overdue · ${kpis?.breached_count ?? 0} breached`}
            </p>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-2">
          <div className="p-2 rounded-lg bg-gray-50 border border-gray-100 text-center">
            <p className="text-lg font-bold text-navy-900 tabular-nums">{kpis?.total_obligations ?? obligations.length}</p>
            <p className="text-[9px] text-gray-500 uppercase tracking-wide">Total</p>
          </div>
          <div className="p-2 rounded-lg bg-gray-50 border border-gray-100 text-center">
            <p className="text-lg font-bold text-teal-700 tabular-nums">{complianceRate.toFixed(0)}%</p>
            <p className="text-[9px] text-gray-500 uppercase tracking-wide">Compliance</p>
          </div>
        </div>

        {topStatuses.length > 0 && (
          <div className="space-y-1.5">
            <p className="text-[9px] font-semibold text-gray-400 uppercase tracking-wider">Status Breakdown</p>
            {topStatuses.map(([status, count]) => {
              const pct = obligations.length > 0 ? (count / obligations.length) * 100 : 0;
              return (
                <div key={status} className="flex items-center gap-2">
                  <span className="text-[10px] text-gray-600 w-20 truncate capitalize">{status.replace(/_/g, " ")}</span>
                  <div className="flex-1 h-1.5 bg-gray-100 rounded-full overflow-hidden">
                    <div className="h-full bg-navy-500 rounded-full" style={{ width: `${pct}%` }} />
                  </div>
                  <span className="text-[10px] font-medium text-gray-500 tabular-nums w-4 text-right">{count}</span>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </SectionCard>
  );
}

// ── Timeline ────────────────────────────────────────────────────────────────

export function ObligationTimeline({ events, compact }: { events: import("./types").TimelineEvent[]; compact?: boolean }) {
  return (
    <SectionCard title="Obligation Timeline" subtitle="Recent activity and upcoming deadlines">
      <div className={`space-y-1.5 overflow-y-auto ${compact ? "max-h-[280px]" : "max-h-[360px]"}`}>
        {events.length === 0 ? (
          <PanelEmptyState
            icon={<PieChart className="w-5 h-5" />}
            title="No timeline events"
            message="Lifecycle events, due dates, and escalations will appear here."
          />
        ) : events.map((e, i) => {
          const isOverdue = e.status === "overdue";
          const isEscalated = e.status === "escalated";
          const isUpcoming = e.status === "pending" || e.status === "in_progress";
          const dotColor = isOverdue ? "bg-red-500" : isEscalated ? "bg-purple-500" : isUpcoming ? "bg-blue-500" : "bg-gray-300";
          const badgeColor = isOverdue ? "bg-red-50 text-red-700" : isEscalated ? "bg-purple-50 text-purple-700" : isUpcoming ? "bg-blue-50 text-blue-700" : "bg-gray-50 text-gray-500";
          return (
            <div key={e.id} className="flex items-start gap-2.5">
              <div className="flex flex-col items-center">
                <div className={`w-2.5 h-2.5 rounded-full ${dotColor}`} />
                {i < events.length - 1 && <div className="w-px h-5 bg-gray-100" />}
              </div>
              <div className="flex-1 min-w-0 pb-1">
                <div className="flex items-center gap-1.5">
                  <span className="text-[11px] font-semibold text-navy-900 truncate">{e.title}</span>
                  <span className={`text-[8px] font-medium px-1 py-0.5 rounded-full ${badgeColor}`}>{e.status.replace(/_/g, " ")}</span>
                </div>
                <p className="text-[9px] text-gray-500">{e.description}</p>
                <p className="text-[8px] text-gray-400">{e.date} {e.vendor ? `• ${e.vendor}` : ""}</p>
              </div>
            </div>
          );
        })}
      </div>
    </SectionCard>
  );
}

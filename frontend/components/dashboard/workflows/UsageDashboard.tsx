"use client";

import React from "react";
import { ArrowLeft, TrendingUp, TrendingDown, Clock, Users, Shield, AlertTriangle, CheckCircle } from "lucide-react";

interface Props {
  onBack: () => void;
}

interface MetricCard {
  label: string;
  value: string;
  change: string;
  trend: "up" | "down" | "neutral";
  color: string;
}

interface WorkflowRow {
  name: string;
  running: number;
  avg_time: string;
  sla_breaches: string;
  rejected: string;
}

const metrics: MetricCard[] = [
  { label: "Running Now", value: "47", change: "+8%", trend: "up", color: "text-blue-400" },
  { label: "Completed Today", value: "23", change: "+12%", trend: "up", color: "text-green-400" },
  { label: "Avg Completion", value: "52.3h", change: "-2h", trend: "down", color: "text-yellow-400" },
  { label: "SLA Breaches", value: "4.2%", change: "+0.5%", trend: "up", color: "text-red-400" },
  { label: "Pending Approvals", value: "12", change: "-3", trend: "down", color: "text-gold-400" },
  { label: "Avg Approval", value: "18.2h", change: "-1.5h", trend: "down", color: "text-green-400" },
];

const workflows: WorkflowRow[] = [
  { name: "NDA Review", running: 22, avg_time: "48h", sla_breaches: "3.2%", rejected: "8.1%" },
  { name: "Procurement", running: 15, avg_time: "72h", sla_breaches: "5.1%", rejected: "12.3%" },
  { name: "Legal Review", running: 10, avg_time: "96h", sla_breaches: "8.2%", rejected: "15.7%" },
  { name: "Sales Contract", running: 8, avg_time: "36h", sla_breaches: "2.1%", rejected: "5.2%" },
  { name: "High Value", running: 5, avg_time: "120h", sla_breaches: "12.4%", rejected: "18.3%" },
];

const bottlenecks = [
  { stage: "Executive Approval", avg: "18.2h", rejection: "12.3%", breach: "8.2%" },
  { stage: "Legal Review", avg: "28.4h", rejection: "4.1%", breach: "8.2%" },
  { stage: "Security Review", avg: "6.1h", rejection: "3.1%", breach: "3.1%" },
];

export function UsageDashboard({ onBack }: Props) {
  return (
    <div className="space-y-6">
      <div>
        <button onClick={onBack} className="flex items-center gap-1 text-sm text-gray-400 hover:text-gray-200 mb-2">
          <ArrowLeft className="w-4 h-4" /> Back
        </button>
        <h2 className="text-xl font-semibold text-gray-100">Workflow Usage Dashboard</h2>
        <p className="text-sm text-gray-400">Last 30 days · Updated live</p>
      </div>

      {/* KPI Grid */}
      <div className="grid grid-cols-3 lg:grid-cols-6 gap-3">
        {metrics.map((m, i) => (
          <div key={i} className="p-3 bg-navy-800/50 border border-navy-700 rounded-lg">
            <div className="text-xs text-gray-500 mb-1">{m.label}</div>
            <div className={`text-lg font-bold ${m.color}`}>{m.value}</div>
            <div className="flex items-center gap-0.5 text-xs mt-0.5">
              {m.trend === "up" && <TrendingUp className="w-3 h-3 text-red-400" />}
              {m.trend === "down" && <TrendingDown className="w-3 h-3 text-green-400" />}
              <span className={m.trend === "up" ? "text-red-400" : m.trend === "down" ? "text-green-400" : "text-gray-400"}>
                {m.change}
              </span>
            </div>
          </div>
        ))}
      </div>

      {/* Workflow Comparison Table */}
      <div className="p-4 bg-navy-800/30 border border-navy-700 rounded-xl">
        <h3 className="text-sm font-medium text-gray-300 mb-3">Workflow Comparison</h3>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-xs text-gray-500 border-b border-navy-700">
                <th className="text-left py-2 pr-4">Workflow</th>
                <th className="text-right py-2 px-4">Running</th>
                <th className="text-right py-2 px-4">Avg Time</th>
                <th className="text-right py-2 px-4">SLA Breaches</th>
                <th className="text-right py-2 pl-4">Rejected</th>
              </tr>
            </thead>
            <tbody>
              {workflows.map((w, i) => (
                <tr key={i} className="border-b border-navy-700/50 hover:bg-navy-800/30">
                  <td className="py-2.5 pr-4 text-gray-200">{w.name}</td>
                  <td className="py-2.5 px-4 text-right text-gray-300">{w.running}</td>
                  <td className="py-2.5 px-4 text-right text-gray-300">{w.avg_time}</td>
                  <td className="py-2.5 px-4 text-right">
                    <span className={parseFloat(w.sla_breaches) > 5 ? "text-red-400" : "text-green-400"}>
                      {w.sla_breaches}
                    </span>
                  </td>
                  <td className="py-2.5 pl-4 text-right">
                    <span className={parseFloat(w.rejected) > 10 ? "text-red-400" : "text-yellow-400"}>
                      {w.rejected}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Bottlenecks */}
      <div className="p-4 bg-navy-800/30 border border-navy-700 rounded-xl">
        <h3 className="text-sm font-medium text-gray-300 mb-3">Top Bottlenecks</h3>
        <div className="space-y-3">
          {bottlenecks.map((b, i) => (
            <div key={i} className="flex items-center gap-4 p-3 bg-navy-800 rounded-lg">
              <div className="flex-1">
                <div className="text-sm text-gray-200">{b.stage}</div>
                <div className="text-xs text-gray-500">Avg {b.avg} · {b.rejection} rejected · {b.breach} breach rate</div>
              </div>
              <div className="w-32 h-2 bg-navy-700 rounded-full overflow-hidden">
                <div
                  className={`h-full rounded-full ${i === 0 ? "bg-red-400 w-3/4" : i === 1 ? "bg-yellow-400 w-1/2" : "bg-blue-400 w-1/3"}`}
                />
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Most Used */}
      <div className="p-4 bg-navy-800/30 border border-navy-700 rounded-xl">
        <h3 className="text-sm font-medium text-gray-300 mb-3">Most Used Workflows</h3>
        <div className="space-y-2">
          {workflows.slice(0, 3).map((w, i) => (
            <div key={i} className="flex items-center justify-between p-3 bg-navy-800 rounded-lg">
              <div className="flex items-center gap-3">
                <span className="text-lg font-bold text-gray-500">#{i + 1}</span>
                <div>
                  <div className="text-sm text-gray-200">{w.name}</div>
                  <div className="text-xs text-gray-500">{w.running} running · {w.avg_time} avg</div>
                </div>
              </div>
              <div className="text-xs text-gray-500">{w.running + 10} runs this month</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

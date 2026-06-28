"use client";

import React from "react";
import { ArrowLeft, Heart, AlertTriangle, CheckCircle, Clock } from "lucide-react";

interface Props {
  onBack: () => void;
}

interface HealthRow {
  name: string;
  pack_id: string;
  running: number;
  avg_duration_hours: number;
  failures: number;
  health_score: number;
  sla_breach_rate: number;
  last_published: string;
}

const rows: HealthRow[] = [
  { name: "NDA Review", pack_id: "nda", running: 22, avg_duration_hours: 48, failures: 1, health_score: 95, sla_breach_rate: 3.2, last_published: "Jun 15" },
  { name: "Procurement", pack_id: "procurement", running: 15, avg_duration_hours: 72, failures: 3, health_score: 88, sla_breach_rate: 5.1, last_published: "Jun 10" },
  { name: "Legal Review", pack_id: "legal_review", running: 10, avg_duration_hours: 96, failures: 2, health_score: 82, sla_breach_rate: 8.2, last_published: "May 28" },
  { name: "Sales Contract", pack_id: "sales_contract", running: 8, avg_duration_hours: 36, failures: 0, health_score: 98, sla_breach_rate: 2.1, last_published: "Jun 20" },
  { name: "High Value", pack_id: "high_risk", running: 5, avg_duration_hours: 120, failures: 4, health_score: 65, sla_breach_rate: 12.4, last_published: "Jun 01" },
];

export function WorkflowHealth({ onBack }: Props) {
  return (
    <div className="space-y-6">
      <div>
        <button onClick={onBack} className="flex items-center gap-1 text-sm text-gray-400 hover:text-gray-200 mb-2">
          <ArrowLeft className="w-4 h-4" /> Back
        </button>
        <h2 className="text-xl font-semibold text-gray-100">Workflow Health</h2>
        <p className="text-sm text-gray-400">Per-workflow health scores, failure rates, and performance metrics</p>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-xs text-gray-500 border-b border-navy-700">
              <th className="text-left py-3 pr-4">Workflow</th>
              <th className="text-center py-3 px-4">Health</th>
              <th className="text-right py-3 px-4">Running</th>
              <th className="text-right py-3 px-4">Avg Duration</th>
              <th className="text-right py-3 px-4">Failures</th>
              <th className="text-right py-3 px-4">SLA Breach</th>
              <th className="text-right py-3 pl-4">Published</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r, i) => {
              const healthColor = r.health_score >= 90 ? "text-green-400" : r.health_score >= 75 ? "text-yellow-400" : "text-red-400";
              const barColor = r.health_score >= 90 ? "bg-green-500" : r.health_score >= 75 ? "bg-yellow-500" : "bg-red-500";
              return (
                <tr key={i} className="border-b border-navy-700/50 hover:bg-navy-800/30">
                  <td className="py-3 pr-4">
                    <div className="text-gray-200">{r.name}</div>
                    <div className="text-xs text-gray-600">{r.pack_id}</div>
                  </td>
                  <td className="py-3 px-4 text-center">
                    <div className="flex items-center gap-2 justify-center">
                      <span className={`text-lg font-bold ${healthColor}`}>{r.health_score}</span>
                      <div className="w-16 h-2 bg-navy-700 rounded-full overflow-hidden">
                        <div className={`h-full rounded-full ${barColor}`} style={{ width: `${r.health_score}%` }} />
                      </div>
                    </div>
                  </td>
                  <td className="py-3 px-4 text-right text-gray-300">{r.running}</td>
                  <td className="py-3 px-4 text-right text-gray-300">{r.avg_duration_hours}h</td>
                  <td className="py-3 px-4 text-right">
                    <span className={r.failures > 2 ? "text-red-400" : "text-gray-300"}>{r.failures}</span>
                  </td>
                  <td className="py-3 px-4 text-right">
                    <span className={r.sla_breach_rate > 5 ? "text-red-400" : "text-yellow-400"}>{r.sla_breach_rate}%</span>
                  </td>
                  <td className="py-3 pl-4 text-right text-gray-500">{r.last_published}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-4 gap-4">
        <SummaryCard icon={<Heart className="w-5 h-5" />} color="text-green-400" value="85.6" label="Avg Health Score" />
        <SummaryCard icon={<AlertTriangle className="w-5 h-5" />} color="text-red-400" value="2" label="Unhealthy Workflows" />
        <SummaryCard icon={<Clock className="w-5 h-5" />} color="text-yellow-400" value="74.4h" label="Avg Duration" />
        <SummaryCard icon={<CheckCircle className="w-5 h-5" />} color="text-blue-400" value="60" label="Total Running" />
      </div>
    </div>
  );
}

function SummaryCard({ icon, color, value, label }: { icon: React.ReactNode; color: string; value: string; label: string }) {
  return (
    <div className="p-4 bg-navy-800/50 border border-navy-700 rounded-xl text-center">
      <div className={`flex justify-center mb-1 ${color}`}>{icon}</div>
      <div className={`text-xl font-bold ${color}`}>{value}</div>
      <div className="text-xs text-gray-500">{label}</div>
    </div>
  );
}

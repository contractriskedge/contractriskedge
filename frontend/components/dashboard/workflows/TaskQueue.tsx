"use client";

import React from "react";
import { ArrowLeft, Clock, Users, AlertTriangle, TrendingUp } from "lucide-react";

interface Props {
  onBack: () => void;
}

interface TaskItem {
  id: string;
  workflow_id: string;
  stage: string;
  contract: string;
  assigned_to: string;
  status: "pending" | "in_progress" | "overdue";
  created: string;
  sla_remaining: number;
  priority: "high" | "medium" | "low";
}

const tasks: TaskItem[] = [
  { id: "t1", workflow_id: "COR-0421", stage: "Executive Approval", contract: "Acme Corp MSA", assigned_to: "Sarah Chen", status: "in_progress", created: "Jun 24", sla_remaining: 12, priority: "high" },
  { id: "t2", workflow_id: "COR-0420", stage: "Legal Review", contract: "Beta GmbH SOW", assigned_to: "John Smith", status: "pending", created: "Jun 25", sla_remaining: 24, priority: "medium" },
  { id: "t3", workflow_id: "COR-0419", stage: "Security Review", contract: "Gamma LLC License", assigned_to: "Mike Johnson", status: "overdue", created: "Jun 20", sla_remaining: -6, priority: "high" },
  { id: "t4", workflow_id: "COR-0418", stage: "Finance Review", contract: "Delta Corp Procurement", assigned_to: "Lisa Wang", status: "pending", created: "Jun 26", sla_remaining: 36, priority: "low" },
  { id: "t5", workflow_id: "COR-0417", stage: "Legal Review", contract: "Epsilon Ltd NDA", assigned_to: "Jane Doe", status: "in_progress", created: "Jun 24", sla_remaining: 8, priority: "high" },
];

const priorityConfig = {
  high: { color: "text-red-400", bg: "bg-red-500/10" },
  medium: { color: "text-yellow-400", bg: "bg-yellow-500/10" },
  low: { color: "text-green-400", bg: "bg-green-500/10" },
};

interface Bottleneck {
  stage: string;
  avg_hours: number;
  instances: number;
  rejection_rate: number;
  escalation_rate: number;
  queue: number;
}

const bottlenecks: Bottleneck[] = [
  { stage: "Executive Approval", avg_hours: 28.4, instances: 12, rejection_rate: 12.3, escalation_rate: 8.2, queue: 5 },
  { stage: "Legal Review", avg_hours: 22.1, instances: 18, rejection_rate: 4.1, escalation_rate: 5.3, queue: 8 },
  { stage: "Security Review", avg_hours: 6.1, instances: 7, rejection_rate: 3.1, escalation_rate: 2.1, queue: 3 },
  { stage: "Finance Review", avg_hours: 14.2, instances: 9, rejection_rate: 6.2, escalation_rate: 4.1, queue: 4 },
];

export function TaskQueue({ onBack }: Props) {
  return (
    <div className="space-y-6">
      <div>
        <button onClick={onBack} className="flex items-center gap-1 text-sm text-gray-400 hover:text-gray-200 mb-2">
          <ArrowLeft className="w-4 h-4" /> Back
        </button>
        <h2 className="text-xl font-semibold text-gray-100">Task Queue</h2>
        <p className="text-sm text-gray-400">{tasks.length} pending tasks · {tasks.filter((t) => t.status === "overdue").length} overdue</p>
      </div>

      <div className="space-y-2">
        {tasks.map((task) => {
          const pc = priorityConfig[task.priority];
          return (
            <div key={task.id} className={`p-4 rounded-lg border ${task.status === "overdue" ? "bg-red-500/5 border-red-500/20" : "bg-navy-800/30 border-navy-700"}`}>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className={`w-2 h-2 rounded-full ${task.status === "overdue" ? "bg-red-400" : task.status === "in_progress" ? "bg-blue-400" : "bg-gray-500"}`} />
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium text-gray-200">{task.stage}</span>
                      <span className={`text-xs px-1.5 py-0.5 rounded ${pc.bg} ${pc.color}`}>{task.priority}</span>
                    </div>
                    <div className="text-xs text-gray-500 mt-0.5">
                      {task.contract} · {task.workflow_id} · Created {task.created}
                    </div>
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-sm text-gray-300">{task.assigned_to}</div>
                  <div className={`text-xs ${task.sla_remaining < 0 ? "text-red-400" : task.sla_remaining < 12 ? "text-yellow-400" : "text-gray-500"}`}>
                    {task.sla_remaining < 0 ? `${Math.abs(task.sla_remaining)}h overdue` : `${task.sla_remaining}h remaining`}
                  </div>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Bottleneck Dashboard */}
      <div className="pt-6 border-t border-navy-700">
        <div className="flex items-center gap-2 mb-4">
          <TrendingUp className="w-5 h-5 text-gold-400" />
          <h3 className="text-lg font-semibold text-gray-100">Bottleneck Analysis</h3>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-xs text-gray-500 border-b border-navy-700">
                <th className="text-left py-2 pr-4">Stage</th>
                <th className="text-right py-2 px-4">Avg Time</th>
                <th className="text-right py-2 px-4">Instances</th>
                <th className="text-right py-2 px-4">Rejection</th>
                <th className="text-right py-2 px-4">Escalation</th>
                <th className="text-right py-2 pl-4">Queue</th>
              </tr>
            </thead>
            <tbody>
              {bottlenecks.map((b, i) => (
                <tr key={i} className="border-b border-navy-700/50">
                  <td className="py-2.5 pr-4 text-gray-200">{b.stage}</td>
                  <td className="py-2.5 px-4 text-right text-gray-300">{b.avg_hours}h</td>
                  <td className="py-2.5 px-4 text-right text-gray-300">{b.instances}</td>
                  <td className="py-2.5 px-4 text-right">
                    <span className={b.rejection_rate > 5 ? "text-red-400" : "text-yellow-400"}>{b.rejection_rate}%</span>
                  </td>
                  <td className="py-2.5 px-4 text-right">
                    <span className={b.escalation_rate > 5 ? "text-red-400" : "text-yellow-400"}>{b.escalation_rate}%</span>
                  </td>
                  <td className="py-2.5 pl-4 text-right">
                    <span className={b.queue > 5 ? "text-red-400 font-bold" : "text-gray-300"}>{b.queue}</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

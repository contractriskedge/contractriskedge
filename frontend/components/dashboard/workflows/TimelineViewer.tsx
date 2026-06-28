"use client";

import React from "react";
import { ArrowLeft, Clock, CheckCircle, AlertTriangle, Play, XCircle } from "lucide-react";

interface Props {
  onBack: () => void;
}

interface TimelineStage {
  name: string;
  status: "completed" | "running" | "pending" | "failed" | "skipped";
  assigned_to: string;
  started_at: string;
  completed_at: string | null;
  sla_hours: number;
  sla_remaining: number | null;
}

const mockStages: TimelineStage[] = [
  { name: "Intake", status: "completed", assigned_to: "System", started_at: "Jun 22, 09:00", completed_at: "Jun 22, 09:01", sla_hours: 0, sla_remaining: null },
  { name: "AI Analysis", status: "completed", assigned_to: "System", started_at: "Jun 22, 09:01", completed_at: "Jun 22, 09:05", sla_hours: 0, sla_remaining: null },
  { name: "Legal Review", status: "completed", assigned_to: "Jane Doe", started_at: "Jun 22, 09:05", completed_at: "Jun 24, 14:30", sla_hours: 48, sla_remaining: 6 },
  { name: "Executive Approval", status: "running", assigned_to: "Sarah Chen", started_at: "Jun 24, 14:30", completed_at: null, sla_hours: 24, sla_remaining: 12 },
  { name: "Finalize", status: "pending", assigned_to: "System", started_at: "", completed_at: null, sla_hours: 0, sla_remaining: null },
];

const statusConfig = {
  completed: { color: "bg-green-500", icon: CheckCircle, label: "Completed" },
  running: { color: "bg-blue-500", icon: Play, label: "In Progress" },
  pending: { color: "bg-gray-600", icon: Clock, label: "Pending" },
  failed: { color: "bg-red-500", icon: XCircle, label: "Failed" },
  skipped: { color: "bg-gray-400", icon: XCircle, label: "Skipped" },
};

export function TimelineViewer({ onBack }: Props) {
  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div>
        <button onClick={onBack} className="flex items-center gap-1 text-sm text-gray-400 hover:text-gray-200 mb-2">
          <ArrowLeft className="w-4 h-4" /> Back
        </button>
        <h2 className="text-xl font-semibold text-gray-100">Workflow Timeline</h2>
        <p className="text-sm text-gray-400">COR-2026-0421 · NDA Review v3 · Started Jun 22, 2026</p>
      </div>

      {/* Timeline */}
      <div className="relative">
        {mockStages.map((stage, i) => {
          const cfg = statusConfig[stage.status];
          const Icon = cfg.icon;
          const isLast = i === mockStages.length - 1;

          return (
            <div key={i} className="flex gap-4">
              {/* Timeline line */}
              <div className="flex flex-col items-center">
                <div className={`w-4 h-4 rounded-full ${cfg.color} ring-4 ring-navy-900 z-10 flex items-center justify-center`}>
                  <Icon className="w-2.5 h-2.5 text-white" />
                </div>
                {!isLast && <div className="w-0.5 flex-1 bg-navy-700 -mt-0.5" />}
              </div>

              {/* Content */}
              <div className={`flex-1 pb-8 ${stage.status === "running" ? "bg-navy-800/30 -mx-3 px-3 py-2 rounded-lg border border-blue-500/20" : ""}`}>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className={`font-medium ${stage.status === "running" ? "text-blue-300" : "text-gray-200"}`}>
                      {stage.name}
                    </span>
                    <span className={`text-xs px-2 py-0.5 rounded-full ${
                      stage.status === "completed" ? "bg-green-500/20 text-green-400" :
                      stage.status === "running" ? "bg-blue-500/20 text-blue-400" :
                      stage.status === "failed" ? "bg-red-500/20 text-red-400" :
                      "bg-gray-500/20 text-gray-400"
                    }`}>
                      {cfg.label}
                    </span>
                  </div>
                  {stage.sla_hours > 0 && (
                    <span className={`text-xs ${stage.sla_remaining && stage.sla_remaining < 4 ? "text-red-400" : "text-gray-500"}`}>
                      SLA: {stage.sla_hours}h
                      {stage.sla_remaining !== null && ` · ${stage.sla_remaining}h remaining`}
                    </span>
                  )}
                </div>

                <div className="flex items-center gap-4 mt-1 text-xs text-gray-500">
                  <span>👤 {stage.assigned_to}</span>
                  {stage.started_at && <span>▶ {stage.started_at}</span>}
                  {stage.completed_at && <span>✅ {stage.completed_at}</span>}
                </div>

                {/* Progress bar for running stage */}
                {stage.status === "running" && stage.sla_hours > 0 && stage.sla_remaining !== null && (
                  <div className="mt-2 w-full h-1.5 bg-navy-700 rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full ${stage.sla_remaining < 4 ? "bg-red-500" : "bg-blue-500"}`}
                      style={{ width: `${((stage.sla_hours - stage.sla_remaining) / stage.sla_hours) * 100}%` }}
                    />
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Summary */}
      <div className="p-4 bg-navy-800/30 border border-navy-700 rounded-xl">
        <h3 className="text-sm font-medium text-gray-300 mb-2">Summary</h3>
        <div className="grid grid-cols-4 gap-4 text-center">
          <div>
            <div className="text-lg font-bold text-green-400">{mockStages.filter((s) => s.status === "completed").length}</div>
            <div className="text-xs text-gray-500">Completed</div>
          </div>
          <div>
            <div className="text-lg font-bold text-blue-400">{mockStages.filter((s) => s.status === "running").length}</div>
            <div className="text-xs text-gray-500">In Progress</div>
          </div>
          <div>
            <div className="text-lg font-bold text-gray-400">{mockStages.filter((s) => s.status === "pending").length}</div>
            <div className="text-xs text-gray-500">Pending</div>
          </div>
          <div>
            <div className="text-lg font-bold text-yellow-400">
              {mockStages.reduce((sum, s) => sum + (s.sla_hours || 0), 0)}h
            </div>
            <div className="text-xs text-gray-500">Total SLA</div>
          </div>
        </div>
      </div>
    </div>
  );
}

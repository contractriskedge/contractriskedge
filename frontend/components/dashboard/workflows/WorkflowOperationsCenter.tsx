"use client";

import React, { useState } from "react";
import { ArrowLeft, Activity, ListTodo, Heart, Shield, BarChart3, Search } from "lucide-react";
import { WorkflowInstanceMonitor } from "./WorkflowInstanceMonitor";
import { UsageDashboard } from "./UsageDashboard";

type OpsView = "monitor" | "tasks" | "health" | "audit" | "bottlenecks" | "dashboard";

interface Props {
  onBack: () => void;
}

export function WorkflowOperationsCenter({ onBack }: Props) {
  const [activeView, setActiveView] = useState<OpsView>("monitor");

  const navItems: { id: OpsView; label: string; icon: React.ReactNode; description: string }[] = [
    { id: "monitor", label: "Instance Monitor", icon: <Activity className="w-5 h-5" />, description: "Live view of all running workflow instances" },
    { id: "tasks", label: "Task Queue", icon: <ListTodo className="w-5 h-5" />, description: "Pending tasks and assignments" },
    { id: "bottlenecks", label: "Bottlenecks", icon: <BarChart3 className="w-5 h-5" />, description: "Stage-level performance analysis" },
    { id: "health", label: "Workflow Health", icon: <Heart className="w-5 h-5" />, description: "Per-workflow health scores and metrics" },
    { id: "audit", label: "Audit Explorer", icon: <Shield className="w-5 h-5" />, description: "Searchable workflow event log" },
    { id: "dashboard", label: "Usage Dashboard", icon: <BarChart3 className="w-5 h-5" />, description: "Aggregated usage metrics and trends" },
  ];

  return (
    <div className="space-y-6">
      <div>
        <button onClick={onBack} className="flex items-center gap-1 text-sm text-gray-400 hover:text-gray-200 mb-2">
          <ArrowLeft className="w-4 h-4" /> Back to Workflow Packs
        </button>
        <h2 className="text-xl font-semibold text-gray-100">Workflow Operations</h2>
        <p className="text-sm text-gray-400">Monitor, manage, and analyze your workflow platform</p>
      </div>

      {/* Navigation Tabs */}
      <div className="flex flex-wrap gap-2">
        {navItems.map((item) => (
          <button
            key={item.id}
            onClick={() => setActiveView(item.id)}
            className={`flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm transition-colors ${
              activeView === item.id
                ? "bg-gold-500/20 text-gold-400 border border-gold-500/30"
                : "bg-navy-800/50 text-gray-400 border border-navy-700 hover:border-navy-600"
            }`}
          >
            {item.icon}
            <div className="text-left">
              <div className={activeView === item.id ? "text-gold-400" : "text-gray-300"}>{item.label}</div>
              <div className="text-xs opacity-60 hidden md:block">{item.description}</div>
            </div>
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="mt-4">
        {activeView === "monitor" && (
          <WorkflowInstanceMonitor onBack={() => setActiveView("monitor")} />
        )}
        {activeView === "dashboard" && (
          <UsageDashboard onBack={() => setActiveView("monitor")} />
        )}
        {activeView === "tasks" && (
          <div className="text-center py-16 text-gray-500">
            <ListTodo className="w-12 h-12 mx-auto mb-3 text-gray-600" />
            <p>Task Queue — Coming soon</p>
            <p className="text-sm">View pending tasks, assignments, and SLA deadlines</p>
          </div>
        )}
        {activeView === "bottlenecks" && (
          <div className="text-center py-16 text-gray-500">
            <BarChart3 className="w-12 h-12 mx-auto mb-3 text-gray-600" />
            <p>Bottleneck Analysis — Coming soon</p>
            <p className="text-sm">Stage-level performance metrics and queue analysis</p>
          </div>
        )}
        {activeView === "health" && (
          <div className="text-center py-16 text-gray-500">
            <Heart className="w-12 h-12 mx-auto mb-3 text-gray-600" />
            <p>Workflow Health Dashboard — Coming soon</p>
            <p className="text-sm">Per-workflow health scores, failure rates, and duration</p>
          </div>
        )}
        {activeView === "audit" && (
          <div className="text-center py-16 text-gray-500">
            <Shield className="w-12 h-12 mx-auto mb-3 text-gray-600" />
            <p>Audit Explorer — Coming soon</p>
            <p className="text-sm">Searchable, filterable event log for all workflow actions</p>
          </div>
        )}
      </div>
    </div>
  );
}

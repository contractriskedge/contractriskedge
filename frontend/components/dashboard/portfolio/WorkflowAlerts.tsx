"use client";

import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  ClipboardCheck, AlertTriangle, AlertOctagon, Clock, User,
  ChevronRight, CheckCircle, X, Bell, FileText,
} from "lucide-react";
import type { WorkflowAlert, AlertSeverity } from "./types";

// ── Severity config ─────────────────────────────────────────────────────────

const severityCfg: Record<AlertSeverity, { icon: React.ReactNode; dot: string; bg: string }> = {
  critical: { icon: <AlertOctagon className="w-3.5 h-3.5 text-red-500" />, dot: "bg-red-500", bg: "bg-red-50" },
  warning: { icon: <AlertTriangle className="w-3.5 h-3.5 text-orange-500" />, dot: "bg-orange-500", bg: "bg-orange-50" },
  info: { icon: <Clock className="w-3.5 h-3.5 text-blue-500" />, dot: "bg-blue-500", bg: "bg-blue-50" },
  success: { icon: <CheckCircle className="w-3.5 h-3.5 text-green-500" />, dot: "bg-green-500", bg: "bg-green-50" },
};

const typeLabels: Record<string, string> = {
  approval: "Approval",
  escalation: "Escalation",
  sla_breach: "SLA Breach",
  task: "Task",
  review: "Review",
  notification: "Notification",
};

const typeIcons: Record<string, React.ReactNode> = {
  approval: <ClipboardCheck className="w-3.5 h-3.5" />,
  escalation: <AlertTriangle className="w-3.5 h-3.5" />,
  sla_breach: <AlertOctagon className="w-3.5 h-3.5" />,
  task: <ClipboardCheck className="w-3.5 h-3.5" />,
  review: <FileText className="w-3.5 h-3.5" />,
  notification: <Bell className="w-3.5 h-3.5" />,
};

// ── Alert Card ──────────────────────────────────────────────────────────────

function AlertCard({ alert, index }: { alert: WorkflowAlert; index: number }) {
  const [dismissed, setDismissed] = useState(false);
  const cfg = severityCfg[alert.severity];

  if (dismissed) return null;

  return (
    <motion.div
      initial={{ opacity: 0, x: -8 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, height: 0, marginBottom: 0 }}
      className="flex items-start gap-3 p-3 bg-white rounded-lg border border-gray-100 hover:shadow-sm hover:border-gray-200 transition-all group"
    >
      {/* Type icon */}
      <div className={`w-7 h-7 rounded-full ${cfg.bg} flex items-center justify-center flex-shrink-0 mt-0.5`}>
        {typeIcons[alert.type] || <Bell className="w-3.5 h-3.5 text-gray-500" />}
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-1.5 mb-0.5">
          <span className={`w-1.5 h-1.5 rounded-full ${cfg.dot}`} />
          <span className="text-[10px] font-medium text-gray-400 uppercase">{typeLabels[alert.type] || alert.type}</span>
          {alert.dueDate && (
            <span className="text-[10px] text-gray-400">• Due {alert.dueDate}</span>
          )}
        </div>
        <h4 className="text-xs font-semibold text-navy-900">{alert.title}</h4>
        <p className="text-[11px] text-gray-600 mt-0.5 line-clamp-1">{alert.description}</p>
        {alert.assignee && (
          <div className="flex items-center gap-1 mt-1.5">
            <User className="w-3 h-3 text-gray-400" />
            <span className="text-[10px] text-gray-500">{alert.assignee}</span>
          </div>
        )}
      </div>

      {/* Actions */}
      <div className="flex items-center gap-1 flex-shrink-0">
        {alert.status === "pending" && (
          <button className="text-[10px] font-medium px-2 py-1 rounded-md bg-green-50 text-green-700 hover:bg-green-100 transition-colors opacity-0 group-hover:opacity-100">
            Accept
          </button>
        )}
        <button
          onClick={() => setDismissed(true)}
          className="p-1 rounded hover:bg-gray-100 text-gray-300 hover:text-gray-500 transition-colors opacity-0 group-hover:opacity-100"
        >
          <X className="w-3 h-3" />
        </button>
        <ChevronRight className="w-3.5 h-3.5 text-gray-300" />
      </div>
    </motion.div>
  );
}

// ── Stats summary ───────────────────────────────────────────────────────────

function AlertSummary({ alerts }: { alerts: WorkflowAlert[] }) {
  const pending = alerts.filter((a) => a.status === "pending").length;
  const inProgress = alerts.filter((a) => a.status === "in_progress").length;
  const critical = alerts.filter((a) => a.severity === "critical").length;

  return (
    <div className="flex items-center gap-4 px-4 py-2.5 bg-gray-50 rounded-lg border border-gray-100">
      <div className="flex items-center gap-2 text-xs">
        <Bell className="w-4 h-4 text-navy-600" />
        <span className="font-medium text-navy-700">Workflow Center</span>
      </div>
      <div className="flex gap-3">
        <span className="text-[11px] text-gray-600">
          <span className="font-bold text-red-600">{critical}</span> critical
        </span>
        <span className="text-[11px] text-gray-600">
          <span className="font-bold text-orange-600">{pending}</span> pending
        </span>
        <span className="text-[11px] text-gray-600">
          <span className="font-bold text-blue-600">{inProgress}</span> in progress
        </span>
      </div>
    </div>
  );
}

// ── Main Component ──────────────────────────────────────────────────────────

interface WorkflowAlertsPanelProps {
  alerts: WorkflowAlert[];
}

export function WorkflowAlertsPanel({ alerts }: WorkflowAlertsPanelProps) {
  const [filter, setFilter] = useState<string>("all");

  const filtered = filter === "all" ? alerts : alerts.filter((a) => a.type === filter);
  const types = [...new Set(alerts.map((a) => a.type))];

  return (
    <div className="space-y-3">
      <AlertSummary alerts={alerts} />

      {/* Filter tabs */}
      <div className="flex gap-1 overflow-x-auto pb-1">
        <button
          onClick={() => setFilter("all")}
          className={`text-[10px] font-medium px-2.5 py-1 rounded-full whitespace-nowrap transition-colors ${
            filter === "all" ? "bg-navy-700 text-white" : "bg-gray-100 text-gray-600 hover:bg-gray-200"
          }`}
        >
          All ({alerts.length})
        </button>
        {types.map((t) => {
          const count = alerts.filter((a) => a.type === t).length;
          return (
            <button
              key={t}
              onClick={() => setFilter(t)}
              className={`text-[10px] font-medium px-2.5 py-1 rounded-full whitespace-nowrap transition-colors ${
                filter === t ? "bg-navy-700 text-white" : "bg-gray-100 text-gray-600 hover:bg-gray-200"
              }`}
            >
              {typeLabels[t] || t} ({count})
            </button>
          );
        })}
      </div>

      {/* Alert list */}
      <div className="space-y-1.5">
        <AnimatePresence>
          {filtered.map((alert, i) => (
            <AlertCard key={alert.id} alert={alert} index={i} />
          ))}
        </AnimatePresence>
        {filtered.length === 0 && (
          <div className="text-center py-8 text-gray-400">
            <CheckCircle className="w-8 h-8 mx-auto mb-2" />
            <p className="text-xs font-medium">All clear</p>
            <p className="text-[10px] mt-0.5">No {filter} items</p>
          </div>
        )}
      </div>
    </div>
  );
}

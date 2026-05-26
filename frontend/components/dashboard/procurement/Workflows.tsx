"use client";

import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ClipboardCheck, AlertTriangle, AlertOctagon, Clock, User, X, ChevronRight, Bell, FileText, ShoppingCart, RefreshCw } from "lucide-react";
import type { WorkflowItem } from "./types";

const typeIcons: Record<string, React.ReactNode> = {
  approval: <ClipboardCheck className="w-3.5 h-3.5" />,
  sourcing: <ShoppingCart className="w-3.5 h-3.5" />,
  onboarding: <User className="w-3.5 h-3.5" />,
  review: <FileText className="w-3.5 h-3.5" />,
  escalation: <AlertTriangle className="w-3.5 h-3.5" />,
  renewal: <RefreshCw className="w-3.5 h-3.5" />,
};

const typeLabels: Record<string, string> = {
  approval: "Approval", sourcing: "Sourcing", onboarding: "Onboarding", review: "Review", escalation: "Escalation", renewal: "Renewal",
};

const severityCfg = {
  critical: { dot: "bg-red-500", bg: "bg-red-50" },
  warning: { dot: "bg-orange-500", bg: "bg-orange-50" },
  info: { dot: "bg-blue-500", bg: "bg-blue-50" },
};

function WorkflowCard({ item, index }: { item: WorkflowItem; index: number }) {
  const [dismissed, setDismissed] = useState(false);
  const cfg = severityCfg[item.severity];
  if (dismissed) return null;
  return (
    <motion.div initial={{ opacity: 0, x: -6 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, height: 0 }}
      className="flex items-start gap-2.5 p-2.5 bg-white rounded-lg border border-gray-100 hover:shadow-sm hover:border-gray-200 transition-all group">
      <div className={`w-7 h-7 rounded-full ${cfg.bg} flex items-center justify-center flex-shrink-0 mt-0.5`}>{typeIcons[item.type] || <Bell className="w-3.5 h-3.5 text-gray-500" />}</div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-1.5 mb-0.5">
          <span className={`w-1.5 h-1.5 rounded-full ${cfg.dot}`} />
          <span className="text-[9px] font-medium text-gray-400 uppercase">{typeLabels[item.type] || item.type}</span>
          {item.slaRemaining !== undefined && (
            <span className={`text-[9px] font-medium ${item.slaRemaining <= 5 ? "text-red-500" : item.slaRemaining <= 10 ? "text-orange-500" : "text-gray-400"}`}>
              {item.slaRemaining}d remaining
            </span>
          )}
        </div>
        <h4 className="text-[11px] font-semibold text-navy-900">{item.title}</h4>
        <p className="text-[10px] text-gray-600 mt-0.5 line-clamp-1">{item.description}</p>
        {item.assignee && <div className="flex items-center gap-1 mt-1"><User className="w-2.5 h-2.5 text-gray-400" /><span className="text-[9px] text-gray-500">{item.assignee}</span></div>}
      </div>
      <div className="flex items-center gap-1 flex-shrink-0">
        {item.status === "pending" && (
          <button className="text-[9px] font-medium px-1.5 py-1 rounded-md bg-green-50 text-green-700 hover:bg-green-100 transition-colors opacity-0 group-hover:opacity-100">Accept</button>
        )}
        <button onClick={() => setDismissed(true)} className="p-0.5 rounded hover:bg-gray-100 text-gray-300 hover:text-gray-500 opacity-0 group-hover:opacity-100"><X className="w-3 h-3" /></button>
        <ChevronRight className="w-3 h-3 text-gray-300" />
      </div>
    </motion.div>
  );
}

export function ProcurementWorkflows({ workflows }: { workflows: WorkflowItem[] }) {
  const [filter, setFilter] = useState<string>("all");
  const types = [...new Set(workflows.map((w) => w.type))];
  const filtered = filter === "all" ? workflows : workflows.filter((w) => w.type === filter);
  const critical = workflows.filter((w) => w.severity === "critical").length;
  const pending = workflows.filter((w) => w.status === "pending").length;

  return (
    <div className="space-y-2.5">
      <div className="flex items-center gap-2 px-3 py-2 bg-gray-50 rounded-lg border border-gray-100">
        <Bell className="w-4 h-4 text-navy-600" />
        <span className="text-[11px] font-medium text-navy-700">Procurement Workflows</span>
        <span className="text-[10px] text-red-600 font-bold ml-auto">{critical} critical</span>
        <span className="text-[10px] text-orange-600">{pending} pending</span>
      </div>
      <div className="flex gap-1 overflow-x-auto pb-1">
        <button onClick={() => setFilter("all")} className={`text-[9px] font-medium px-2 py-1 rounded-full whitespace-nowrap transition-colors ${filter === "all" ? "bg-navy-700 text-white" : "bg-gray-100 text-gray-600 hover:bg-gray-200"}`}>All ({workflows.length})</button>
        {types.map((t) => {
          const count = workflows.filter((w) => w.type === t).length;
          return (
            <button key={t} onClick={() => setFilter(t)} className={`text-[9px] font-medium px-2 py-1 rounded-full whitespace-nowrap transition-colors ${filter === t ? "bg-navy-700 text-white" : "bg-gray-100 text-gray-600 hover:bg-gray-200"}`}>
              {typeLabels[t] || t} ({count})
            </button>
          );
        })}
      </div>
      <div className="space-y-1">
        <AnimatePresence>{filtered.map((w, i) => <WorkflowCard key={w.id} item={w} index={i} />)}</AnimatePresence>
      </div>
    </div>
  );
}

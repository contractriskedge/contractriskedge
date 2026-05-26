"use client";

import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Edit3, MessageSquare, Check, X, Sparkles, ArrowUpCircle,
  GitCommit, Activity, Clock, User, FileText, Filter,
  ChevronDown, ChevronRight, Circle,
} from "lucide-react";
import type { ActivityEntry } from "./types";

// ── Activity Timeline ────────────────────────────────────────────────────

const activityIcons: Record<string, React.ReactNode> = {
  edit: <Edit3 className="w-3 h-3" />,
  comment: <MessageSquare className="w-3 h-3" />,
  approval: <Check className="w-3 h-3" />,
  rejection: <X className="w-3 h-3" />,
  ai_action: <Sparkles className="w-3 h-3" />,
  escalation: <ArrowUpCircle className="w-3 h-3" />,
  status_change: <Activity className="w-3 h-3" />,
  version_create: <GitCommit className="w-3 h-3" />,
};

const activityColors: Record<string, string> = {
  edit: "bg-blue-500",
  comment: "bg-green-500",
  approval: "bg-emerald-500",
  rejection: "bg-red-500",
  ai_action: "bg-purple-500",
  escalation: "bg-orange-500",
  status_change: "bg-gray-500",
  version_create: "bg-gold-500",
};

function ActivityItem({ activity, isLast }: { activity: ActivityEntry; isLast: boolean }) {
  return (
    <div className="flex gap-2.5">
      {/* Timeline line & icon */}
      <div className="flex flex-col items-center">
        <div className={`w-5 h-5 rounded-full flex items-center justify-center text-white ${activityColors[activity.type] || "bg-gray-400"}`}>
          {activityIcons[activity.type] || <Circle className="w-3 h-3" />}
        </div>
        {!isLast && <div className="w-px flex-1 bg-gray-200 dark:bg-navy-600 mt-1" />}
      </div>
      {/* Content */}
      <div className="pb-3 flex-1 min-w-0">
        <div className="flex items-center gap-1.5">
          <span className="text-[10px] font-semibold text-navy-900 dark:text-white">{activity.user}</span>
          <span className="text-[9px] text-gray-400">{activity.action}</span>
        </div>
        <p className="text-[10px] text-gray-500 dark:text-gray-400 mt-0.5 leading-relaxed">{activity.description}</p>
        <div className="flex items-center gap-2 mt-0.5">
          <span className="text-[8px] text-gray-400 flex items-center gap-0.5">
            <Clock className="w-2.5 h-2.5" />
            {new Date(activity.timestamp).toLocaleDateString("en-US", {
              month: "short", day: "numeric", hour: "2-digit", minute: "2-digit",
            })}
          </span>
          {activity.clauseId && (
            <span className="text-[8px] text-gray-400 flex items-center gap-0.5">
              <FileText className="w-2.5 h-2.5" />
              Clause {activity.clauseId.toUpperCase()}
            </span>
          )}
        </div>
      </div>
    </div>
  );
}

interface ActivityTimelineProps {
  activities: ActivityEntry[];
  maxItems?: number;
}

export function ActivityTimeline({ activities, maxItems = 20 }: ActivityTimelineProps) {
  const [showAll, setShowAll] = useState(false);
  const [typeFilter, setTypeFilter] = useState<string>("all");

  const filtered = typeFilter === "all"
    ? activities
    : activities.filter(a => a.type === typeFilter);

  const displayed = showAll ? filtered : filtered.slice(0, maxItems);

  const types = Array.from(new Set(activities.map(a => a.type)));

  return (
    <div className="bg-white dark:bg-navy-800 border border-gray-200 dark:border-navy-600 rounded-lg overflow-hidden">
      {/* Header */}
      <div className="px-3 py-2 border-b border-gray-200 dark:border-navy-700 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Activity className="w-3.5 h-3.5 text-gold-500" />
          <span className="text-[10px] font-semibold text-gray-500 uppercase tracking-wider">Activity Timeline</span>
          <span className="text-[9px] text-gray-400">({activities.length} events)</span>
        </div>
        <div className="flex items-center gap-1">
          <Filter className="w-3 h-3 text-gray-400" />
          <select
            value={typeFilter}
            onChange={e => setTypeFilter(e.target.value)}
            className="text-[9px] border border-gray-200 dark:border-navy-600 rounded bg-transparent text-gray-500 dark:text-gray-400 py-0.5 px-1 focus:outline-none focus:ring-1 focus:ring-gold-400"
          >
            <option value="all">All</option>
            {types.map(t => (
              <option key={t} value={t}>{t.replace("_", " ")}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Timeline */}
      <div className="px-3 py-2 max-h-64 overflow-y-auto">
        {displayed.length === 0 ? (
          <div className="text-center py-6 text-gray-400">
            <Activity className="w-6 h-6 mx-auto mb-1 opacity-50" />
            <p className="text-[10px]">No activities found</p>
          </div>
        ) : (
          displayed.map((activity, idx) => (
            <ActivityItem key={activity.id} activity={activity} isLast={idx === displayed.length - 1 && !showAll && filtered.length <= maxItems} />
          ))
        )}
      </div>

      {/* Show more */}
      {filtered.length > maxItems && (
        <button
          onClick={() => setShowAll(!showAll)}
          className="w-full px-3 py-1.5 text-[9px] text-gold-600 hover:text-gold-700 dark:text-gold-400 border-t border-gray-100 dark:border-navy-700 hover:bg-gray-50 dark:hover:bg-navy-700 transition-colors flex items-center justify-center gap-1"
        >
          {showAll ? "Show less" : `Show all ${filtered.length} events`}
          {showAll ? <ChevronDown className="w-2.5 h-2.5" /> : <ChevronRight className="w-2.5 h-2.5" />}
        </button>
      )}
    </div>
  );
}

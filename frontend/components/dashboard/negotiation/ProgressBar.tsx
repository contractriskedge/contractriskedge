"use client";

import React from "react";
import { motion } from "framer-motion";
import { CheckCircle, ArrowUpCircle, XCircle, HelpCircle, Clock } from "lucide-react";

interface ProgressData {
  total: number;
  completed: number;
  pending: number;
  escalated: number;
  ignored: number;
}

interface ProgressBarProps {
  data: ProgressData;
}

export function ProgressBar({ data }: ProgressBarProps) {
  const { total, completed, pending, escalated, ignored } = data;
  const pct = total > 0 ? Math.round(((completed) / total) * 100) : 0;

  if (total === 0) return null;

  const completedWidth = total > 0 ? (completed / total) * 100 : 0;
  const escalatedWidth = total > 0 ? (escalated / total) * 100 : 0;
  const ignoredWidth = total > 0 ? (ignored / total) * 100 : 0;
  const pendingWidth = total > 0 ? (pending / total) * 100 : 0;

  return (
    <div className="bg-white dark:bg-navy-800 border-b border-gray-200 dark:border-navy-700">
      <div className="px-3 py-1.5">
        {/* Stats row */}
        <div className="flex items-center gap-3 text-[10px] mb-1">
          <span className="font-semibold text-navy-900 dark:text-white">{total} Findings</span>
          <span className="flex items-center gap-0.5 text-green-600">
            <CheckCircle className="w-2.5 h-2.5" /> {completed} Completed
          </span>
          <span className="flex items-center gap-0.5 text-amber-600">
            <Clock className="w-2.5 h-2.5" /> {pending} Pending
          </span>
          <span className="flex items-center gap-0.5 text-red-600">
            <ArrowUpCircle className="w-2.5 h-2.5" /> {escalated} Escalated
          </span>
          <span className="flex items-center gap-0.5 text-gray-400">
            <XCircle className="w-2.5 h-2.5" /> {ignored} Ignored
          </span>
          <span className="ml-auto font-semibold text-navy-900 dark:text-white">{pct}%</span>
        </div>

        {/* Progress bar */}
        <div className="h-1.5 bg-gray-100 dark:bg-navy-700 rounded-full overflow-hidden flex">
          {completed > 0 && (
            <motion.div
              initial={{ width: 0 }}
              animate={{ width: `${completedWidth}%` }}
              className="h-full bg-green-500 rounded-full"
              title={`${completed} completed`}
            />
          )}
          {pending > 0 && (
            <motion.div
              initial={{ width: 0 }}
              animate={{ width: `${pendingWidth}%` }}
              className="h-full bg-amber-400"
              title={`${pending} pending`}
            />
          )}
          {escalated > 0 && (
            <motion.div
              initial={{ width: 0 }}
              animate={{ width: `${escalatedWidth}%` }}
              className="h-full bg-red-500"
              title={`${escalated} escalated`}
            />
          )}
          {ignored > 0 && (
            <motion.div
              initial={{ width: 0 }}
              animate={{ width: `${ignoredWidth}%` }}
              className="h-full bg-gray-300 rounded-r-full"
              title={`${ignored} ignored`}
            />
          )}
        </div>
      </div>
    </div>
  );
}

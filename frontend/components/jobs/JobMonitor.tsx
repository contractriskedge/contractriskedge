/**
 * JobMonitor — Action job queue monitoring panel.
 *
 * Shows pending, running, completed, failed, and retrying jobs
 * from the workspace action_jobs API.
 */

"use client";

import React, { useState, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import {
  Clock, CheckCircle, XCircle, RefreshCw, Loader2,
  AlertTriangle, Play, Filter, ArrowRight,
} from "lucide-react";
import { api } from "@/services/api/client";

// ── Types ────────────────────────────────────────────────────────

interface ActionJob {
  job_id: string;
  action_type: string;
  status: string;
  target_type: string;
  target_ids: string[];
  progress: number;
  result_message: string | null;
  error_message: string | null;
  retry_count: number;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
}

interface JobListResponse {
  jobs: ActionJob[];
  total: number;
}

// ── Hook ──────────────────────────────────────────────────────────

function useActionJobs() {
  return useQuery({
    queryKey: ["workspace", "jobs"],
    queryFn: () => api.get<JobListResponse>("/workspace/jobs"),
    staleTime: 10_000,
    refetchInterval: 15_000,
  });
}

// ── Status config ────────────────────────────────────────────────

const statusConfig: Record<string, { bg: string; text: string; dot: string; icon: React.ReactNode }> = {
  pending: { bg: "bg-gray-100", text: "text-gray-600", dot: "bg-gray-400", icon: <Clock className="w-3 h-3" /> },
  running: { bg: "bg-blue-100", text: "text-blue-700", dot: "bg-blue-500", icon: <RefreshCw className="w-3 h-3 animate-spin" /> },
  completed: { bg: "bg-green-100", text: "text-green-700", dot: "bg-green-500", icon: <CheckCircle className="w-3 h-3" /> },
  failed: { bg: "bg-red-100", text: "text-red-700", dot: "bg-red-500", icon: <XCircle className="w-3 h-3" /> },
  retrying: { bg: "bg-amber-100", text: "text-amber-700", dot: "bg-amber-500", icon: <AlertTriangle className="w-3 h-3" /> },
};

const defaultStatus = { bg: "bg-gray-100", text: "text-gray-600", dot: "bg-gray-400", icon: <Clock className="w-3 h-3" /> };

// ── Action Type Icons ────────────────────────────────────────────

const actionIcons: Record<string, string> = {
  assign: "👤",
  escalate: "🚨",
  re_analyze: "🔄",
  export: "📥",
  notify: "🔔",
};

// ── Component ────────────────────────────────────────────────────

export function JobMonitor() {
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const { data, isLoading } = useActionJobs();

  const jobs = data?.jobs ?? [];

  const filtered = useMemo(() => {
    if (statusFilter === "all") return jobs;
    return jobs.filter((j) => j.status === statusFilter);
  }, [jobs, statusFilter]);

  const counts = useMemo(() => {
    const c: Record<string, number> = { all: jobs.length };
    for (const j of jobs) {
      c[j.status] = (c[j.status] || 0) + 1;
    }
    return c;
  }, [jobs]);

  const statuses = ["all", "pending", "running", "completed", "failed", "retrying"];

  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
      {/* Header */}
      <div className="px-4 py-3 border-b border-gray-100 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Play className="w-4 h-4 text-gray-500" />
          <h3 className="text-xs font-semibold text-navy-900">Action Jobs</h3>
          <span className="text-[10px] text-gray-400">({jobs.length} total)</span>
        </div>
        <div className="flex items-center gap-1">
          {statuses.map((s) => (
            <button
              key={s}
              onClick={() => setStatusFilter(s)}
              className={`px-2 py-0.5 rounded text-[9px] font-medium transition-colors ${
                statusFilter === s
                  ? "bg-navy-700 text-white"
                  : "bg-gray-100 text-gray-600 hover:bg-gray-200"
              }`}
            >
              {s.charAt(0).toUpperCase() + s.slice(1)}
              {counts[s] > 0 && <span className="ml-1 opacity-70">({counts[s]})</span>}
            </button>
          ))}
        </div>
      </div>

      {/* List */}
      <div className="divide-y divide-gray-100 max-h-80 overflow-y-auto">
        {isLoading ? (
          <div className="flex justify-center py-8"><Loader2 className="w-5 h-5 text-gray-400 animate-spin" /></div>
        ) : filtered.length === 0 ? (
          <div className="flex flex-col items-center py-8 text-center">
            <Clock className="w-8 h-8 text-gray-300 mb-2" />
            <p className="text-xs text-gray-500">No jobs found</p>
            <p className="text-[10px] text-gray-400 mt-1">Actions you execute will appear here.</p>
          </div>
        ) : (
          filtered.map((job) => {
            const cfg = statusConfig[job.status] || defaultStatus;
            return (
              <div key={job.job_id} className="px-4 py-2.5 flex items-center gap-3 hover:bg-gray-50">
                <span className="text-sm">{actionIcons[job.action_type] || "📋"}</span>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-medium text-navy-900 capitalize">{job.action_type.replace(/_/g, " ")}</span>
                    <span className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded-full text-[9px] font-medium ${cfg.bg} ${cfg.text}`}>
                      {cfg.icon} {job.status}
                    </span>
                    {job.retry_count > 0 && (
                      <span className="text-[9px] text-gray-400">retry #{job.retry_count}</span>
                    )}
                  </div>
                  <div className="flex items-center gap-2 mt-0.5">
                    <span className="text-[9px] text-gray-400 capitalize">{job.target_type}</span>
                    <span className="text-[9px] text-gray-400">{job.target_ids.length} targets</span>
                    {job.started_at && (
                      <span className="text-[9px] text-gray-400">
                        {formatTimeAgo(job.started_at)}
                      </span>
                    )}
                  </div>
                  {job.status === "running" && job.progress > 0 && (
                    <div className="mt-1 w-full h-1 bg-gray-100 rounded-full overflow-hidden">
                      <div className="h-full bg-blue-500 rounded-full transition-all" style={{ width: `${job.progress}%` }} />
                    </div>
                  )}
                  {job.error_message && (
                    <p className="text-[9px] text-red-500 mt-0.5 truncate">{job.error_message}</p>
                  )}
                  {job.result_message && (
                    <p className="text-[9px] text-green-600 mt-0.5 truncate">{job.result_message}</p>
                  )}
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}

// ── Time formatting ──────────────────────────────────────────────

function formatTimeAgo(ts: string): string {
  const d = new Date(ts);
  const now = new Date();
  const diff = now.getTime() - d.getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "Just now";
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  return d.toLocaleDateString();
}

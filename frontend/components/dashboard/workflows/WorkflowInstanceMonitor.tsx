"use client";

import React, { useState } from "react";
import {
  Search, Filter, Clock, Users, AlertTriangle, CheckCircle,
  XCircle, Play, Pause, ArrowLeft, ChevronRight,
} from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { fetchInstances } from "@/services/api/workflowAdmin";
import type { InstanceSummary } from "@/services/api/workflowAdmin";
import { LoadingSkeleton } from "@/components/shared/LoadingSkeleton";
import { ErrorState } from "@/components/shared/ErrorState";
import { EmptyState } from "@/components/shared/EmptyState";

interface Props {
  onBack: () => void;
  onSelectInstance?: (id: string) => void;
}

const statusConfig: Record<string, { color: string; icon: React.ReactNode; label: string }> = {
  running: { color: "text-blue-400", icon: <Play className="w-3.5 h-3.5" />, label: "Running" },
  waiting_approval: { color: "text-yellow-400", icon: <Clock className="w-3.5 h-3.5" />, label: "Waiting Approval" },
  completed: { color: "text-green-400", icon: <CheckCircle className="w-3.5 h-3.5" />, label: "Completed" },
  failed: { color: "text-red-400", icon: <XCircle className="w-3.5 h-3.5" />, label: "Failed" },
  cancelled: { color: "text-gray-400", icon: <XCircle className="w-3.5 h-3.5" />, label: "Cancelled" },
  paused: { color: "text-yellow-400", icon: <Pause className="w-3.5 h-3.5" />, label: "Paused" },
};

export function WorkflowInstanceMonitor({ onBack, onSelectInstance }: Props) {
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const pageSize = 20;

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["workflow-instances", statusFilter, search, page],
    queryFn: () => fetchInstances({
      status: statusFilter || undefined,
      search: search || undefined,
      page,
      page_size: pageSize,
    }),
    refetchInterval: 15_000, // Poll every 15s
  });

  const instances = data?.items ?? [];
  const total = data?.total ?? 0;
  const totalPages = Math.ceil(total / pageSize);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <button onClick={onBack} className="flex items-center gap-1 text-sm text-gray-400 hover:text-gray-200 mb-1">
            <ArrowLeft className="w-4 h-4" /> Back
          </button>
          <h2 className="text-xl font-semibold text-gray-100">Workflow Instance Monitor</h2>
          <p className="text-sm text-gray-400">Live view of all workflow instances · Auto-refreshes every 15s</p>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-3">
        <div className="relative flex-1 min-w-[200px] max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
          <input
            type="text"
            placeholder="Search by contract name or ID..."
            value={search}
            onChange={(e) => { setSearch(e.target.value); setPage(1); }}
            className="w-full pl-10 pr-4 py-2 bg-navy-800/50 border border-navy-600 rounded-lg text-gray-100 text-sm placeholder-gray-600 focus:outline-none focus:ring-2 focus:ring-gold-500/50"
          />
        </div>
        <select
          value={statusFilter}
          onChange={(e) => { setStatusFilter(e.target.value); setPage(1); }}
          className="px-3 py-2 bg-navy-800/50 border border-navy-600 rounded-lg text-gray-100 text-sm"
        >
          <option value="">All Status</option>
          <option value="running">Running</option>
          <option value="waiting_approval">Waiting Approval</option>
          <option value="completed">Completed</option>
          <option value="failed">Failed</option>
          <option value="cancelled">Cancelled</option>
          <option value="paused">Paused</option>
        </select>
        <span className="text-sm text-gray-500">{total} instance{total !== 1 ? "s" : ""}</span>
      </div>

      {/* Content */}
      {isLoading ? (
        <div className="space-y-2">
          {Array.from({ length: 5 }).map((_, i) => (
            <LoadingSkeleton key={i} className="h-16 rounded-lg" />
          ))}
        </div>
      ) : error ? (
        <ErrorState message="Failed to load instances" onRetry={() => refetch()} />
      ) : instances.length === 0 ? (
        <EmptyState icon={<Play className="w-12 h-12" />} title="No workflow instances" description="Instances will appear here when contracts enter a workflow." />
      ) : (
        <>
          {/* Table */}
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-xs text-gray-500 border-b border-navy-700">
                  <th className="text-left py-3 pr-4">Contract</th>
                  <th className="text-left py-3 px-4">Workflow</th>
                  <th className="text-left py-3 px-4">Stage</th>
                  <th className="text-left py-3 px-4">Status</th>
                  <th className="text-left py-3 px-4">Assignee</th>
                  <th className="text-right py-3 pl-4">SLA</th>
                </tr>
              </thead>
              <tbody>
                {instances.map((inst) => {
                  const cfg = statusConfig[inst.status] ?? statusConfig.running;
                  const slaOk = inst.sla_remaining_hours > 0 && !inst.sla_breached;
                  return (
                    <tr
                      key={inst.workflow_id}
                      onClick={() => onSelectInstance?.(inst.workflow_id)}
                      className="border-b border-navy-700/50 hover:bg-navy-800/30 cursor-pointer"
                    >
                      <td className="py-3 pr-4">
                        <div className="text-gray-200">{inst.contract_name}</div>
                        <div className="text-xs text-gray-500">{inst.workflow_id.slice(0, 12)}</div>
                      </td>
                      <td className="py-3 px-4 text-gray-300">{inst.pack_name}</td>
                      <td className="py-3 px-4">
                        <span className="text-gray-300">{inst.current_stage}</span>
                        {inst.version_number > 1 && (
                          <span className="ml-1 text-xs text-gray-600">v{inst.version_number}</span>
                        )}
                      </td>
                      <td className="py-3 px-4">
                        <div className="flex items-center gap-1.5">
                          <span className={cfg.color}>{cfg.icon}</span>
                          <span className={cfg.color}>{cfg.label}</span>
                        </div>
                      </td>
                      <td className="py-3 px-4 text-gray-300">{inst.assigned_to ?? "—"}</td>
                      <td className="py-3 pl-4 text-right">
                        {inst.sla_breached ? (
                          <span className="flex items-center justify-end gap-1 text-red-400">
                            <AlertTriangle className="w-3.5 h-3.5" /> Breached
                          </span>
                        ) : slaOk ? (
                          <span className="text-gray-400">{inst.sla_remaining_hours.toFixed(0)}h</span>
                        ) : (
                          <span className="text-gray-600">—</span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-500">Page {page} of {totalPages}</span>
              <div className="flex gap-2">
                <button
                  onClick={() => setPage(Math.max(1, page - 1))}
                  disabled={page <= 1}
                  className="px-3 py-1.5 bg-navy-800 text-gray-300 rounded-lg text-sm disabled:opacity-30 hover:bg-navy-700"
                >
                  Previous
                </button>
                <button
                  onClick={() => setPage(Math.min(totalPages, page + 1))}
                  disabled={page >= totalPages}
                  className="px-3 py-1.5 bg-navy-800 text-gray-300 rounded-lg text-sm disabled:opacity-30 hover:bg-navy-700"
                >
                  Next
                </button>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}

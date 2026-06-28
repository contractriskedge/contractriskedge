"use client";

import React, { useState } from "react";
import { ArrowLeft, Search, Shield, Filter, Download } from "lucide-react";

interface Props {
  onBack: () => void;
}

interface AuditEvent {
  id: string;
  workflow_id: string;
  event_type: string;
  actor_id: string;
  timestamp: string;
  details: string;
  stage_name: string | null;
}

const mockEvents: AuditEvent[] = [
  { id: "e1", workflow_id: "COR-0421", event_type: "WorkflowStarted", actor_id: "System", timestamp: "2026-06-22 09:00", details: "Contract submitted for NDA Review v3", stage_name: "Intake" },
  { id: "e2", workflow_id: "COR-0421", event_type: "StageCompleted", actor_id: "System", timestamp: "2026-06-22 09:01", details: "Intake completed (automatic)", stage_name: "Intake" },
  { id: "e3", workflow_id: "COR-0421", event_type: "StageCompleted", actor_id: "System", timestamp: "2026-06-22 09:05", details: "AI Analysis completed (automatic)", stage_name: "AI Analysis" },
  { id: "e4", workflow_id: "COR-0421", event_type: "StageEntered", actor_id: "System", timestamp: "2026-06-22 09:05", details: "Assigned to Jane Doe (Legal Reviewer)", stage_name: "Legal Review" },
  { id: "e5", workflow_id: "COR-0421", event_type: "ApprovalGranted", actor_id: "Jane Doe", timestamp: "2026-06-24 14:30", details: "Legal Review approved (All Required mode)", stage_name: "Legal Review" },
  { id: "e6", workflow_id: "COR-0421", event_type: "StageEntered", actor_id: "System", timestamp: "2026-06-24 14:30", details: "Assigned to Sarah Chen (VP Legal)", stage_name: "Executive Approval" },
  { id: "e7", workflow_id: "COR-0420", event_type: "WorkflowStarted", actor_id: "System", timestamp: "2026-06-25 10:00", details: "Contract submitted for Procurement v2", stage_name: "Intake" },
  { id: "e8", workflow_id: "COR-0419", event_type: "WorkflowEscalated", actor_id: "System", timestamp: "2026-06-26 08:00", details: "SLA breach: Security Review overdue by 6h", stage_name: "Security Review" },
  { id: "e9", workflow_id: "COR-0418", event_type: "ApprovalRejected", actor_id: "Lisa Wang", timestamp: "2026-06-25 16:00", details: "Finance Review rejected: Budget not approved", stage_name: "Finance Review" },
  { id: "e10", workflow_id: "COR-0417", event_type: "WorkflowCompleted", actor_id: "System", timestamp: "2026-06-24 18:00", details: "NDA Review completed successfully", stage_name: "Finalize" },
];

const eventTypes = [...new Set(mockEvents.map((e) => e.event_type))];

export function AuditExplorer({ onBack }: Props) {
  const [search, setSearch] = useState("");
  const [typeFilter, setTypeFilter] = useState("");

  const filtered = mockEvents.filter((e) => {
    if (typeFilter && e.event_type !== typeFilter) return false;
    if (search) {
      const q = search.toLowerCase();
      return e.workflow_id.toLowerCase().includes(q) || e.actor_id.toLowerCase().includes(q) || e.details.toLowerCase().includes(q);
    }
    return true;
  });

  return (
    <div className="space-y-4">
      <div>
        <button onClick={onBack} className="flex items-center gap-1 text-sm text-gray-400 hover:text-gray-200 mb-2">
          <ArrowLeft className="w-4 h-4" /> Back
        </button>
        <h2 className="text-xl font-semibold text-gray-100">Audit Explorer</h2>
        <p className="text-sm text-gray-400">Searchable, filterable event log for all workflow actions</p>
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <div className="relative flex-1 min-w-[200px] max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
          <input
            type="text"
            placeholder="Search workflow ID, actor, or details..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-10 pr-4 py-2 bg-navy-800/50 border border-navy-600 rounded-lg text-gray-100 text-sm placeholder-gray-600"
          />
        </div>
        <select value={typeFilter} onChange={(e) => setTypeFilter(e.target.value)}
          className="px-3 py-2 bg-navy-800/50 border border-navy-600 rounded-lg text-gray-100 text-sm">
          <option value="">All Event Types</option>
          {eventTypes.map((t) => <option key={t} value={t}>{t}</option>)}
        </select>
        <span className="text-sm text-gray-500">{filtered.length} events</span>
        <button className="flex items-center gap-1 px-3 py-2 text-sm text-gray-400 hover:text-gray-200">
          <Download className="w-4 h-4" /> Export
        </button>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-xs text-gray-500 border-b border-navy-700">
              <th className="text-left py-3 pr-4">Timestamp</th>
              <th className="text-left py-3 px-4">Workflow</th>
              <th className="text-left py-3 px-4">Event</th>
              <th className="text-left py-3 px-4">Stage</th>
              <th className="text-left py-3 px-4">Actor</th>
              <th className="text-left py-3 pl-4">Details</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((event) => (
              <tr key={event.id} className="border-b border-navy-700/50 hover:bg-navy-800/30">
                <td className="py-2.5 pr-4 text-gray-400 text-xs whitespace-nowrap">{event.timestamp}</td>
                <td className="py-2.5 px-4 text-gray-300 font-mono text-xs">{event.workflow_id}</td>
                <td className="py-2.5 px-4">
                  <span className={`text-xs px-2 py-0.5 rounded ${
                    event.event_type.includes("Approval") ? "bg-gold-500/20 text-gold-400" :
                    event.event_type.includes("Escalated") || event.event_type.includes("Rejected") ? "bg-red-500/20 text-red-400" :
                    event.event_type.includes("Completed") ? "bg-green-500/20 text-green-400" :
                    "bg-blue-500/20 text-blue-400"
                  }`}>
                    {event.event_type}
                  </span>
                </td>
                <td className="py-2.5 px-4 text-gray-400">{event.stage_name ?? "—"}</td>
                <td className="py-2.5 px-4 text-gray-400">{event.actor_id}</td>
                <td className="py-2.5 pl-4 text-gray-500 text-xs max-w-xs truncate">{event.details}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

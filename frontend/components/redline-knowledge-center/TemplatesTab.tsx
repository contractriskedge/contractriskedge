/**
 * Templates tab — library of all redline templates with status badges.
 */
"use client";

import React, { useState } from "react";
import { motion } from "framer-motion";
import {
  FileText,
  Plus,
  Loader2,
  Search,
  CheckCircle2,
  AlertCircle,
  Clock,
  Archive,
  Sparkles,
} from "lucide-react";
import { useTemplates, useDeleteTemplate } from "@/services/hooks/useRedlineTemplates";
import type { RedlineTemplate } from "@/services/api/redlineTemplates";

const STATUS_STYLE: Record<string, { label: string; icon: React.ElementType; class: string }> = {
  active: { label: "Approved", icon: CheckCircle2, class: "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400" },
  ai_draft: { label: "AI Generated", icon: Sparkles, class: "bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400" },
  draft: { label: "Draft", icon: Clock, class: "bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300" },
  retired: { label: "Retired", icon: Archive, class: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400" },
};

export function TemplatesTab() {
  const { data: templates, isLoading } = useTemplates();
  const deleteTemplate = useDeleteTemplate();
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("all");

  const filtered = (templates ?? []).filter((t) => {
    const matchesSearch = t.name.toLowerCase().includes(search.toLowerCase()) ||
      t.clause_type.toLowerCase().includes(search.toLowerCase());
    const matchesStatus = statusFilter === "all" || t.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-6 h-6 animate-spin text-indigo-500" />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Filters */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input
              type="text"
              placeholder="Search templates..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-64 pl-9 pr-3 py-2 text-sm border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
            />
          </div>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="px-3 py-2 text-sm border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
          >
            <option value="all">All Status</option>
            <option value="active">Approved</option>
            <option value="ai_draft">AI Generated</option>
            <option value="draft">Draft</option>
            <option value="retired">Retired</option>
          </select>
        </div>
        <button className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors">
          <Plus className="w-4 h-4" />
          New Template
        </button>
      </div>

      {/* Template Cards */}
      {filtered.length === 0 ? (
        <div className="text-center py-16">
          <FileText className="w-12 h-12 text-gray-300 dark:text-gray-600 mx-auto mb-3" />
          <p className="text-gray-500 dark:text-gray-400">No templates found</p>
          <p className="text-sm text-gray-400 dark:text-gray-500 mt-1">
            {templates?.length === 0
              ? "Create your first template or generate AI drafts from the Coverage tab"
              : "Try adjusting your filters"}
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filtered.map((template) => {
            const status = STATUS_STYLE[template.status] ?? STATUS_STYLE.draft;
            const StatusIcon = status.icon;
            return (
              <motion.div
                key={template.template_id}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4 hover:shadow-md transition-shadow"
              >
                <div className="flex items-start justify-between mb-3">
                  <div className="flex-1 min-w-0">
                    <h3 className="font-medium text-gray-900 dark:text-white truncate">
                      {template.name}
                    </h3>
                    <p className="text-xs text-gray-400 capitalize mt-0.5">
                      {template.clause_type.replace(/_/g, " ")}
                    </p>
                  </div>
                  <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ml-2 ${status.class}`}>
                    <StatusIcon className="w-3 h-3" />
                    {status.label}
                  </span>
                </div>
                <p className="text-xs text-gray-500 dark:text-gray-400 line-clamp-2 mb-3">
                  {template.template_text.slice(0, 200)}
                </p>
                <div className="flex items-center justify-between text-xs text-gray-400">
                  <span>v{template.version}</span>
                  <span>Used {template.usage_count} times</span>
                  <span>{template.accept_rate > 0 ? `${Math.round(template.accept_rate * 100)}% accept` : "—"}</span>
                </div>
              </motion.div>
            );
          })}
        </div>
      )}
    </div>
  );
}

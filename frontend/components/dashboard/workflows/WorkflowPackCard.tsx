"use client";

import React from "react";
import {
  Workflow, Star, Clock, AlertTriangle, MoreHorizontal,
  FileJson, Download, Copy, Archive,
} from "lucide-react";
import type { WorkflowPackSummary } from "@/services/api/workflowAdmin";

interface Props {
  pack: WorkflowPackSummary;
  viewMode: "grid" | "list";
  onClick: () => void;
}

const statusConfig: Record<string, { color: string; label: string }> = {
  published: { color: "text-green-400", label: "Published" },
  draft: { color: "text-yellow-400", label: "Draft" },
  archived: { color: "text-gray-400", label: "Archived" },
};

const categoryColors: Record<string, string> = {
  legal: "bg-purple-500/20 text-purple-300",
  sales: "bg-blue-500/20 text-blue-300",
  procurement: "bg-green-500/20 text-green-300",
  hr: "bg-pink-500/20 text-pink-300",
  privacy: "bg-indigo-500/20 text-indigo-300",
  custom: "bg-gray-500/20 text-gray-300",
};

export function WorkflowPackCard({ pack, viewMode, onClick }: Props) {
  const status = statusConfig[pack.status] ?? statusConfig.draft;
  const healthColor = pack.health_score >= 90 ? "text-green-400" : pack.health_score >= 70 ? "text-yellow-400" : "text-red-400";

  if (viewMode === "list") {
    return (
      <button
        onClick={onClick}
        className="w-full flex items-center gap-4 p-4 bg-navy-800/50 border border-navy-700 rounded-lg hover:border-navy-600 transition-colors text-left"
      >
        <Workflow className="w-5 h-5 text-gold-400 shrink-0" />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="font-medium text-gray-100 truncate">{pack.name}</span>
            {pack.is_built_in && (
              <span className="text-xs px-1.5 py-0.5 bg-navy-700 rounded text-gray-400">Built-in</span>
            )}
          </div>
          <div className="text-sm text-gray-400 truncate">{pack.description}</div>
        </div>
        <div className="flex items-center gap-3 text-sm">
          <span className={healthColor}>{pack.health_score}%</span>
          <span className={status.color}>{status.label}</span>
          <span className="text-gray-400">v{pack.version}</span>
          <span className="text-gray-500">{pack.usage_count}x</span>
        </div>
      </button>
    );
  }

  return (
    <button
      onClick={onClick}
      className="relative p-5 bg-navy-800/50 border border-navy-700 rounded-xl hover:border-navy-600 transition-colors text-left group"
    >
      {/* Header */}
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-2">
          <Workflow className="w-5 h-5 text-gold-400" />
          <div>
            <div className="font-medium text-gray-100">{pack.name}</div>
            {pack.is_built_in && (
              <span className="text-xs px-1.5 py-0.5 bg-navy-700 rounded text-gray-400">Built-in</span>
            )}
          </div>
        </div>
        <div className="flex items-center gap-1">
          <div
            onClick={(e) => { e.stopPropagation(); }}
            className="p-1.5 text-gray-500 hover:text-gold-400 transition-colors cursor-pointer"
          >
            <Star className={`w-4 h-4 ${pack.is_favorite ? "fill-gold-400 text-gold-400" : ""}`} />
          </div>
          <div
            onClick={(e) => { e.stopPropagation(); }}
            className="p-1.5 text-gray-500 hover:text-gray-300 transition-colors cursor-pointer"
          >
            <MoreHorizontal className="w-4 h-4" />
          </div>
        </div>
      </div>

      {/* Health & Status */}
      <div className="flex items-center gap-3 mb-3">
        <span className={`text-lg font-bold ${healthColor}`}>{pack.health_score}%</span>
        <span className={`text-xs px-2 py-0.5 rounded-full ${status.color} bg-navy-700`}>
          {status.label}
        </span>
        <span className="text-xs text-gray-500">v{pack.version}</span>
      </div>

      {/* Category */}
      <span className={`inline-block text-xs px-2 py-0.5 rounded ${categoryColors[pack.category] ?? categoryColors.custom} mb-3`}>
        {pack.category}
      </span>

      {/* Stats */}
      <div className="grid grid-cols-2 gap-2 text-sm">
        <div>
          <span className="text-gray-500">Used</span>
          <span className="ml-1 text-gray-300">{pack.usage_count}x</span>
        </div>
        <div>
          <span className="text-gray-500">Running</span>
          <span className="ml-1 text-gray-300">{pack.running_instances}</span>
        </div>
        {pack.last_published && (
          <div className="col-span-2 flex items-center gap-1 text-gray-500">
            <Clock className="w-3 h-3" />
            <span>Published {formatRelativeTime(pack.last_published)}</span>
          </div>
        )}
      </div>

      {/* Warnings */}
      {pack.warning_count > 0 && (
        <div className="flex items-center gap-1 mt-3 text-yellow-400 text-xs">
          <AlertTriangle className="w-3 h-3" />
          <span>{pack.warning_count} warning{pack.warning_count !== 1 ? "s" : ""}</span>
        </div>
      )}

      {/* Hover actions */}
      <div className="absolute top-12 right-2 hidden group-hover:flex flex-col gap-1 bg-navy-900 border border-navy-600 rounded-lg p-1 shadow-xl z-10">
        <div className="flex items-center gap-2 px-3 py-1.5 text-sm text-gray-300 hover:text-gold-400 hover:bg-navy-700 rounded cursor-pointer">
          <Copy className="w-3.5 h-3.5" /> Clone
        </div>
        <div className="flex items-center gap-2 px-3 py-1.5 text-sm text-gray-300 hover:text-gold-400 hover:bg-navy-700 rounded cursor-pointer">
          <Download className="w-3.5 h-3.5" /> Export
        </div>
        <div className="flex items-center gap-2 px-3 py-1.5 text-sm text-gray-300 hover:text-gold-400 hover:bg-navy-700 rounded cursor-pointer">
          <FileJson className="w-3.5 h-3.5" /> Import
        </div>
        <div className="flex items-center gap-2 px-3 py-1.5 text-sm text-gray-300 hover:text-red-400 hover:bg-navy-700 rounded cursor-pointer">
          <Archive className="w-3.5 h-3.5" /> Archive
        </div>
      </div>
    </button>
  );
}

function formatRelativeTime(dateStr: string): string {
  const now = Date.now();
  const date = new Date(dateStr).getTime();
  const diffMs = now - date;
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
  if (diffDays === 0) return "today";
  if (diffDays === 1) return "yesterday";
  if (diffDays < 7) return `${diffDays}d ago`;
  if (diffDays < 30) return `${Math.floor(diffDays / 7)}w ago`;
  return `${Math.floor(diffDays / 30)}mo ago`;
}

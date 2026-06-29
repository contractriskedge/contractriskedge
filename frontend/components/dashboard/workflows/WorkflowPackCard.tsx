"use client";

import React, { useState, useRef, useEffect } from "react";
import {
  Workflow, Star, Clock, AlertTriangle, MoreHorizontal, Activity,
  FileJson, Download, Copy, Archive, Layers, Edit,
} from "lucide-react";
import { StatusBadge } from "@/components/shared/StatusBadge";
import type { WorkflowPackSummary } from "@/services/api/workflowAdmin";
import { getHealthColors, getHealthLabel } from "./workflowHealthUtils";

interface Props {
  pack: WorkflowPackSummary;
  viewMode: "grid" | "list";
  onClick: () => void;
}

const categoryColors: Record<string, string> = {
  legal: "bg-purple-100 dark:bg-purple-900/20 text-purple-700 dark:text-purple-300",
  sales: "bg-blue-100 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300",
  procurement: "bg-emerald-100 dark:bg-emerald-900/20 text-emerald-700 dark:text-emerald-300",
  hr: "bg-pink-100 dark:bg-pink-900/20 text-pink-700 dark:text-pink-300",
  privacy: "bg-indigo-100 dark:bg-indigo-900/20 text-indigo-700 dark:text-indigo-300",
  healthcare: "bg-cyan-100 dark:bg-cyan-900/20 text-cyan-700 dark:text-cyan-300",
  saas_vendor: "bg-blue-100 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300",
  finance_legal: "bg-amber-100 dark:bg-amber-900/20 text-amber-700 dark:text-amber-300",
  custom: "bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400",
};

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

export function WorkflowPackCard({ pack, viewMode, onClick }: Props) {
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  // Close menu on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setMenuOpen(false);
      }
    };
    if (menuOpen) document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [menuOpen]);

  const healthColors = getHealthColors(pack.health_score);
  const healthColor = healthColors.text;
  const healthLabel = getHealthLabel(healthColors.tier);
  const healthBg = healthColors.bg;

  const ActionMenu = () => (
    <div
      ref={menuRef}
      className="absolute right-0 top-full mt-1 w-40 bg-white dark:bg-navy-800 border border-gray-200 dark:border-navy-600 rounded-lg shadow-lg z-20 py-1"
    >
      <div className="flex items-center gap-2 px-3 py-2 text-xs text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-navy-700 cursor-pointer">
        <Edit className="w-3.5 h-3.5" /> Edit
      </div>
      <div className="flex items-center gap-2 px-3 py-2 text-xs text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-navy-700 cursor-pointer">
        <Copy className="w-3.5 h-3.5" /> Clone
      </div>
      <div className="flex items-center gap-2 px-3 py-2 text-xs text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-navy-700 cursor-pointer">
        <Download className="w-3.5 h-3.5" /> Export
      </div>
      <div className="border-t border-gray-100 dark:border-navy-700 my-1" />
      <div className="flex items-center gap-2 px-3 py-2 text-xs text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 cursor-pointer">
        <Archive className="w-3.5 h-3.5" /> Archive
      </div>
    </div>
  );

  if (viewMode === "list") {
    return (
      <div className="relative">
        <button
          onClick={onClick}
          className="w-full flex items-center gap-3 p-3 rounded-lg border border-gray-200 dark:border-navy-700 bg-white dark:bg-navy-800 hover:bg-gray-50 dark:hover:bg-navy-750 transition-colors text-left"
        >
          <div className="w-9 h-9 rounded-lg bg-navy-50 dark:bg-navy-700 flex items-center justify-center shrink-0">
            <Workflow className="w-4 h-4 text-navy-500 dark:text-navy-300" />
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <span className="text-sm font-semibold text-navy-900 dark:text-white truncate">{pack.name}</span>
              {pack.is_built_in && (
                <span className="text-[8px] px-1.5 py-0.5 rounded-full bg-gray-100 dark:bg-navy-700 text-gray-500 font-medium">Built-in</span>
              )}
            </div>
            <div className="flex items-center gap-2 mt-0.5">
              <span className={`text-[10px] px-1.5 py-0.5 rounded-full font-medium ${categoryColors[pack.category] ?? categoryColors.custom}`}>
                {pack.category}
              </span>
              <StatusBadge variant="secondary" status={pack.status} />
              <span className="text-[10px] text-gray-400">v{pack.version}</span>
            </div>
          </div>
          <div className="flex items-center gap-3 text-[11px] text-gray-500">
            <span className={healthColor + " font-semibold"}>{pack.health_score}%</span>
            <span>{pack.usage_count}x used</span>
          </div>
          <div
            onClick={(e) => { e.stopPropagation(); }}
            className="p-1 text-gray-400 hover:text-amber-500 transition-colors cursor-pointer"
          >
            <Star className={`w-3.5 h-3.5 ${pack.is_favorite ? "fill-amber-400 text-amber-400" : ""}`} />
          </div>
          <div className="relative">
            <div
              onClick={(e) => { e.stopPropagation(); setMenuOpen(!menuOpen); }}
              className="p-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors cursor-pointer"
            >
              <MoreHorizontal className="w-3.5 h-3.5" />
            </div>
            {menuOpen && <ActionMenu />}
          </div>
        </button>
      </div>
    );
  }

  return (
    <div className="relative">
      <button
        onClick={onClick}
        className="relative w-full rounded-xl border border-gray-200 dark:border-navy-700 bg-white dark:bg-navy-800 p-4 hover:shadow-md transition-shadow text-left min-h-[220px]"
      >
        {/* Header */}
        <div className="flex items-start justify-between mb-3">
          <div className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-lg bg-navy-50 dark:bg-navy-700 flex items-center justify-center shrink-0">
              <Workflow className="w-4 h-4 text-navy-500 dark:text-navy-300" />
            </div>
            <div>
              <div className="flex items-center gap-1.5">
                <span className="text-sm font-semibold text-navy-900 dark:text-white leading-tight">{pack.name}</span>
                {pack.is_built_in && (
                  <span className="text-[8px] px-1.5 py-0.5 rounded-full bg-gray-100 dark:bg-navy-700 text-gray-500 font-medium">Built-in</span>
                )}
              </div>
              <span className={`text-[10px] px-1.5 py-0.5 rounded-full font-medium ${categoryColors[pack.category] ?? categoryColors.custom}`}>
                {pack.category}
              </span>
            </div>
          </div>
          <div className="flex items-center gap-0.5">
            <div
              onClick={(e) => { e.stopPropagation(); }}
              className="p-1 text-gray-400 hover:text-amber-500 transition-colors cursor-pointer"
            >
              <Star className={`w-3.5 h-3.5 ${pack.is_favorite ? "fill-amber-400 text-amber-400" : ""}`} />
            </div>
            <div className="relative">
              <div
                onClick={(e) => { e.stopPropagation(); setMenuOpen(!menuOpen); }}
                className="p-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors cursor-pointer"
              >
                <MoreHorizontal className="w-3.5 h-3.5" />
              </div>
              {menuOpen && <ActionMenu />}
            </div>
          </div>
        </div>

        {/* Health Score Card */}
        <div className={`rounded-lg border p-2.5 mb-3 ${healthBg}`}>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className={`text-lg font-bold ${healthColor}`}>{pack.health_score}</span>
              <span className="text-[10px] opacity-75">/ 100</span>
            </div>
            <div className="text-right">
              <div className={`text-[10px] font-semibold ${healthColor}`}>{healthLabel}</div>
              {pack.warning_count > 0 && (
                <div className="flex items-center gap-0.5 text-[9px] text-amber-600 dark:text-amber-400">
                  <AlertTriangle className="w-2.5 h-2.5" />
                  {pack.warning_count} warning{pack.warning_count !== 1 ? "s" : ""}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Status + Version Row */}
        <div className="flex items-center gap-2 mb-2.5">
          <StatusBadge variant="primary" status={pack.status} />
          <span className="text-[10px] text-gray-400">v{pack.version}</span>
          {pack.owner && <span className="text-[10px] text-gray-400 ml-auto">{pack.owner}</span>}
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-2 gap-x-4 gap-y-1.5 text-[11px]">
          <div className="flex items-center gap-1.5 text-gray-500">
            <Clock className="w-3 h-3" />
            <span>{pack.last_published ? formatRelativeTime(pack.last_published) : "Not published"}</span>
          </div>
          <div className="flex items-center gap-1.5 text-gray-500">
            <Layers className="w-3 h-3" />
            <span>{pack.stage_count || 0} stages</span>
          </div>
          <div className="flex items-center gap-1.5 text-gray-500">
            <Activity className="w-3 h-3" />
            <span>{pack.running_instances} running</span>
          </div>
          <div className="flex items-center gap-1.5 text-gray-500">
            <span>Used {pack.usage_count}x</span>
          </div>
        </div>
      </button>
    </div>
  );
}

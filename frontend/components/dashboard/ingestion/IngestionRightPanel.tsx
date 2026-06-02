"use client";

import React from "react";
import {
  AlertTriangle, XCircle, Info, Copy, FileSearch, Sparkles,
} from "lucide-react";
import type { AiExtractionInsight, DuplicateGroup } from "./types";

// ── Priority Grouped Right Panel ─────────────────────────────────────────

function IssueItem({ icon, color, title, description }: { icon: React.ReactNode; color: string; title: string; description: string }) {
  return (
    <div className="flex items-start gap-1.5 px-3 py-1">
      <span className={`mt-0.5 ${color} flex-shrink-0`}>{icon}</span>
      <div className="min-w-0">
        <p className="text-[11px] font-medium text-navy-900 dark:text-white truncate">{title}</p>
        <p className="text-[10px] text-gray-500 dark:text-gray-400 line-clamp-2">{description}</p>
      </div>
    </div>
  );
}

function DuplicateRow({ group }: { group: DuplicateGroup }) {
  return (
    <div className="px-3 py-1">
      <div className="flex items-center gap-1 mb-0.5">
        <Copy className="w-3 h-3 text-amber-500" />
        <span className="text-[11px] font-medium text-navy-900 dark:text-white truncate flex-1">Possible Duplicate</span>
        <span className="text-[9px] text-amber-600 font-medium">{group.aiConfidence}%</span>
      </div>
      <div className="space-y-0.5">
        {group.documents.slice(0, 2).map(d => (
          <div key={d.id} className="flex items-center gap-1 text-[10px] text-gray-500">
            <FileSearch className="w-2.5 h-2.5 text-gray-400 flex-shrink-0" />
            <span className="truncate flex-1">{d.name}</span>
            <span className="text-gray-400 flex-shrink-0">{d.similarity}%</span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Right Panel ──────────────────────────────────────────────────────────

interface IngestionRightPanelProps {
  insights: AiExtractionInsight[];
  duplicateGroups: DuplicateGroup[];
  failedCount: number;
  policyViolations: number;
}

export function IngestionRightPanel({ insights, duplicateGroups, failedCount, policyViolations }: IngestionRightPanelProps) {
  const critical: AiExtractionInsight[] = insights.filter(i => i.severity === "critical");
  const warnings: AiExtractionInsight[] = insights.filter(i => i.severity === "warning");
  const suggestions: AiExtractionInsight[] = insights.filter(i => i.severity === "info" || i.severity === "success");

  return (
    <div className="w-64 flex-shrink-0 bg-white dark:bg-navy-800 border-l border-gray-200 dark:border-navy-700 flex flex-col h-full">
      {/* Header */}
      <div className="px-3 py-2 border-b border-gray-200 dark:border-navy-700">
        <h3 className="text-[10px] font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">Operational Summary</h3>
      </div>

      <div className="flex-1 overflow-y-auto">
        {/* AI Summary */}
        <div className="px-3 py-2 border-b border-gray-100 dark:border-navy-700">
          <div className="flex items-center gap-1 mb-1">
            <Sparkles className="w-3 h-3 text-blue-500" />
            <span className="text-[10px] font-semibold text-gray-500 uppercase tracking-wider">AI Summary</span>
          </div>
          <p className="text-[11px] text-gray-600 dark:text-gray-300 leading-relaxed">
            {insights.length === 0 && failedCount === 0 && policyViolations === 0
              ? "All systems nominal. No issues detected in the current ingestion pipeline."
              : `${insights.length} AI insights · ${failedCount} failures · ${policyViolations} policy issues`}
          </p>
        </div>

        {/* Critical Issues */}
        <div className="border-b border-gray-100 dark:border-navy-700">
          <div className="flex items-center gap-1 px-3 py-1.5">
            <XCircle className="w-3 h-3 text-red-500" />
            <span className="text-[10px] font-semibold text-red-600 uppercase tracking-wider">Critical</span>
            <span className="text-[9px] text-red-500 font-medium ml-auto">{critical.length + failedCount + policyViolations}</span>
          </div>
          <div className="pb-1">
            {failedCount > 0 && <IssueItem icon={<XCircle className="w-3 h-3" />} color="text-red-500" title={`${failedCount} Extraction Failures`} description="Documents failed during AI processing" />}
            {policyViolations > 0 && <IssueItem icon={<AlertTriangle className="w-3 h-3" />} color="text-red-500" title={`${policyViolations} Policy Violations`} description="Documents flagged by policy engine" />}
            {critical.map(i => <IssueItem key={i.id} icon={<XCircle className="w-3 h-3" />} color="text-red-500" title={i.title} description={i.description} />)}
            {critical.length === 0 && failedCount === 0 && policyViolations === 0 && <div className="px-3 py-2 text-[11px] text-gray-400 italic">No critical issues</div>}
          </div>
        </div>

        {/* Warnings */}
        <div className="border-b border-gray-100 dark:border-navy-700">
          <div className="flex items-center gap-1 px-3 py-1.5">
            <AlertTriangle className="w-3 h-3 text-amber-500" />
            <span className="text-[10px] font-semibold text-amber-600 uppercase tracking-wider">Warnings</span>
            <span className="text-[9px] text-amber-500 font-medium ml-auto">{warnings.length + duplicateGroups.length}</span>
          </div>
          <div className="pb-1">
            {duplicateGroups.map(g => <DuplicateRow key={g.id} group={g} />)}
            {warnings.map(i => <IssueItem key={i.id} icon={<AlertTriangle className="w-3 h-3" />} color="text-amber-500" title={i.title} description={i.description} />)}
            {warnings.length === 0 && duplicateGroups.length === 0 && <div className="px-3 py-2 text-[11px] text-gray-400 italic">No warnings</div>}
          </div>
        </div>

        {/* Suggestions */}
        <div>
          <div className="flex items-center gap-1 px-3 py-1.5">
            <Info className="w-3 h-3 text-blue-500" />
            <span className="text-[10px] font-semibold text-blue-600 uppercase tracking-wider">Suggestions</span>
            <span className="text-[9px] text-blue-500 font-medium ml-auto">{suggestions.length}</span>
          </div>
          <div className="pb-1">
            {suggestions.map(i => <IssueItem key={i.id} icon={<Info className="w-3 h-3" />} color="text-blue-500" title={i.title} description={i.description} />)}
            {suggestions.length === 0 && <div className="px-3 py-2 text-[11px] text-gray-400 italic">No suggestions</div>}
          </div>
        </div>
      </div>
    </div>
  );
}


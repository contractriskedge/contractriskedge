"use client";

import React from "react";
import { ArrowLeft, Plus, Minus, Pencil, ArrowUp, ArrowDown } from "lucide-react";

interface Props {
  onBack: () => void;
}

interface DiffItem {
  type: "added" | "removed" | "modified";
  category: "stage" | "rule" | "assignment" | "sla";
  label: string;
  detail: string;
}

const mockDiff: DiffItem[] = [
  { type: "added", category: "stage", label: "Security Review", detail: "Added between Legal Review and Finalize" },
  { type: "removed", category: "stage", label: "Negotiation", detail: "Removed from workflow" },
  { type: "modified", category: "sla", label: "Legal Review", detail: "SLA changed: 24h → 48h" },
  { type: "modified", category: "assignment", label: "Executive Approval", detail: "Mode: any_one → all_required" },
  { type: "added", category: "rule", label: "Rule 4: Value > $5M → VP Legal", detail: "Added for high-value contracts" },
  { type: "modified", category: "rule", label: "Rule 2: Risk threshold", detail: "Threshold changed: 80 → 75" },
];

const typeConfig = {
  added: { icon: Plus, color: "text-green-400", bg: "bg-green-500/10", border: "border-green-500/30", label: "Added" },
  removed: { icon: Minus, color: "text-red-400", bg: "bg-red-500/10", border: "border-red-500/30", label: "Removed" },
  modified: { icon: Pencil, color: "text-yellow-400", bg: "bg-yellow-500/10", border: "border-yellow-500/30", label: "Modified" },
};

const categoryIcon: Record<string, React.ReactNode> = {
  stage: <ArrowDown className="w-4 h-4" />,
  rule: <ArrowUp className="w-4 h-4" />,
  assignment: <Pencil className="w-4 h-4" />,
  sla: <Pencil className="w-4 h-4" />,
};

export function VersionComparison({ onBack }: Props) {
  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div>
        <button onClick={onBack} className="flex items-center gap-1 text-sm text-gray-400 hover:text-gray-200 mb-2">
          <ArrowLeft className="w-4 h-4" /> Back
        </button>
        <h2 className="text-xl font-semibold text-gray-100">Version Comparison</h2>
        <p className="text-sm text-gray-400">Comparing v2 → v3 of NDA Review</p>
      </div>

      {/* Summary */}
      <div className="grid grid-cols-3 gap-4">
        <SummaryBox icon={<Plus className="w-5 h-5" />} color="text-green-400" count={2} label="Additions" />
        <SummaryBox icon={<Minus className="w-5 h-5" />} color="text-red-400" count={1} label="Removals" />
        <SummaryBox icon={<Pencil className="w-5 h-5" />} color="text-yellow-400" count={3} label="Modifications" />
      </div>

      {/* Health Change */}
      <div className="p-4 bg-navy-800/30 border border-navy-700 rounded-xl">
        <div className="flex items-center justify-between">
          <span className="text-sm text-gray-300">Health Score</span>
          <div className="flex items-center gap-2">
            <span className="text-lg font-bold text-yellow-400">96</span>
            <ArrowRight className="w-4 h-4 text-gray-600" />
            <span className="text-lg font-bold text-green-400">100</span>
            <span className="text-xs text-green-400">(+4)</span>
          </div>
        </div>
      </div>

      {/* Diff List */}
      <div className="space-y-2">
        {mockDiff.map((item, i) => {
          const cfg = typeConfig[item.type];
          const Icon = cfg.icon;
          return (
            <div key={i} className={`flex items-start gap-3 p-3 rounded-lg border ${cfg.bg} ${cfg.border}`}>
              <div className={`p-1.5 rounded-full ${cfg.bg} ${cfg.color}`}>
                <Icon className="w-4 h-4" />
              </div>
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <span className="text-xs px-1.5 py-0.5 rounded bg-navy-800 text-gray-400 uppercase">
                    {item.category}
                  </span>
                  <span className={`text-xs font-medium ${cfg.color}`}>{cfg.label}</span>
                </div>
                <div className="text-sm text-gray-200 mt-1">{item.label}</div>
                <div className="text-xs text-gray-500 mt-0.5">{item.detail}</div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function SummaryBox({ icon, color, count, label }: { icon: React.ReactNode; color: string; count: number; label: string }) {
  return (
    <div className="p-4 bg-navy-800/50 border border-navy-700 rounded-xl text-center">
      <div className={`flex justify-center mb-1 ${color}`}>{icon}</div>
      <div className={`text-2xl font-bold ${color}`}>{count}</div>
      <div className="text-xs text-gray-500">{label}</div>
    </div>
  );
}

function ArrowRight({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M5 12h14M12 5l7 7-7 7" />
    </svg>
  );
}

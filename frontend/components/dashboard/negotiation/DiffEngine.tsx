"use client";

import React, { useMemo } from "react";
import { motion } from "framer-motion";
import { Plus, Minus, Pencil, AlertTriangle, Info, Brain } from "lucide-react";
import type { DiffBlock, RedlineEntry, CompareMode, RiskLevel } from "./types";

// ── Semantic Diff Engine ─────────────────────────────────────────────────

function computeDiff(original: string, modified: string): { type: "unchanged" | "added" | "removed" | "modified"; content: string; originalContent?: string }[] {
  const origLines = original.split("\n");
  const modLines = modified.split("\n");

  // Simple LCS-based diff
  const lcs: { origI: number; modJ: number }[][] = [];
  const dp: number[][] = Array.from({ length: origLines.length + 1 }, () => Array(modLines.length + 1).fill(0));

  for (let i = 1; i <= origLines.length; i++) {
    for (let j = 1; j <= modLines.length; j++) {
      if (origLines[i - 1].trim() === modLines[j - 1].trim()) {
        dp[i][j] = dp[i - 1][j - 1] + 1;
      } else {
        dp[i][j] = Math.max(dp[i - 1][j], dp[i][j - 1]);
      }
    }
  }

  const result: { type: "unchanged" | "added" | "removed" | "modified"; content: string; originalContent?: string }[] = [];
  let i = origLines.length, j = modLines.length;

  // Build reverse diff
  const reverseDiff: { type: string; content: string; origContent?: string }[] = [];
  while (i > 0 || j > 0) {
    if (i > 0 && j > 0 && origLines[i - 1].trim() === modLines[j - 1].trim()) {
      reverseDiff.push({ type: "unchanged", content: origLines[i - 1] });
      i--; j--;
    } else if (j > 0 && (i === 0 || dp[i][j - 1] >= dp[i - 1][j])) {
      reverseDiff.push({ type: "added", content: modLines[j - 1] });
      j--;
    } else if (i > 0) {
      reverseDiff.push({ type: "removed", content: origLines[i - 1] });
      i--;
    }
  }

  // Merge adjacent same-type blocks and detect modifications
  const blocks = reverseDiff.reverse();
  for (let idx = 0; idx < blocks.length; idx++) {
    const b = blocks[idx];
    // Check if removed followed by added -> modification
    if (b.type === "removed" && idx + 1 < blocks.length && blocks[idx + 1].type === "added") {
      result.push({
        type: "modified",
        content: blocks[idx + 1].content,
        originalContent: b.content,
      });
      idx++; // skip next
    } else {
      result.push(b as any);
    }
  }

  return result;
}

// ── Diff Block Component ─────────────────────────────────────────────────

function DiffBlockRow({ block, lineNum, riskLevel }: { block: { type: string; content: string; originalContent?: string }; lineNum: number; riskLevel?: RiskLevel }) {
  const bgColor = block.type === "added" ? "bg-green-50 dark:bg-green-900/20" :
    block.type === "removed" ? "bg-red-50 dark:bg-red-900/20" :
    block.type === "modified" ? "bg-amber-50 dark:bg-amber-900/20" :
    "";
  const borderColor = block.type === "added" ? "border-l-green-500" :
    block.type === "removed" ? "border-l-red-500" :
    block.type === "modified" ? "border-l-amber-500" :
    "border-l-transparent";
  const icon = block.type === "added" ? <Plus className="w-3 h-3 text-green-600" /> :
    block.type === "removed" ? <Minus className="w-3 h-3 text-red-600" /> :
    block.type === "modified" ? <Pencil className="w-3 h-3 text-amber-600" /> :
    null;

  return (
    <div className={`flex border-l-2 ${borderColor} ${bgColor} group hover:bg-opacity-80 transition-colors`}>
      <div className="w-10 flex-shrink-0 text-[10px] text-gray-400 text-right pr-2 py-0.5 select-none font-mono tabular-nums">
        {lineNum}
      </div>
      <div className="w-5 flex-shrink-0 flex items-center justify-center py-0.5">
        {icon}
      </div>
      <div className="flex-1 py-0.5 px-1">
        {block.type === "modified" && block.originalContent ? (
          <div className="space-y-0.5">
            <div className="text-red-600 dark:text-red-400 line-through text-xs font-mono leading-relaxed">
              {block.originalContent || "\u00A0"}
            </div>
            <div className="text-green-600 dark:text-green-400 text-xs font-mono leading-relaxed">
              {block.content || "\u00A0"}
            </div>
          </div>
        ) : (
          <span className={`text-xs font-mono leading-relaxed ${
            block.type === "added" ? "text-green-700 dark:text-green-300" :
            block.type === "removed" ? "text-red-700 dark:text-red-300" :
            "text-gray-700 dark:text-gray-300"
          }`}>
            {block.content || "\u00A0"}
          </span>
        )}
      </div>
      {riskLevel && riskLevel !== "low" && (
        <div className="flex-shrink-0 pr-1 flex items-center" title={`Risk: ${riskLevel}`}>
          <AlertTriangle className={`w-3 h-3 ${riskLevel === "critical" ? "text-red-500" : riskLevel === "high" ? "text-orange-500" : "text-yellow-500"}`} />
        </div>
      )}
    </div>
  );
}

// ── Side-by-Side Compare ─────────────────────────────────────────────────

function SideBySideCompare({ original, modified, redlines }: { original: string; modified: string; redlines: RedlineEntry[] }) {
  const origLines = original.split("\n");
  const modLines = modified.split("\n");
  const maxLines = Math.max(origLines.length, modLines.length);

  // Build risk map for modified lines
  const riskMap = new Map<number, RiskLevel>();
  redlines.forEach(r => {
    const modIdx = modified.indexOf(r.modifiedText);
    if (modIdx >= 0) {
      const lineBefore = modified.substring(0, modIdx);
      const lineNum = lineBefore.split("\n").length;
      riskMap.set(lineNum, r.riskLevel);
    }
  });

  return (
    <div className="grid grid-cols-2 divide-x divide-gray-200 dark:divide-navy-600 border border-gray-200 dark:border-navy-600 rounded-lg overflow-hidden">
      {/* Original */}
      <div className="bg-gray-50 dark:bg-navy-900">
        <div className="px-3 py-1.5 bg-gray-100 dark:bg-navy-800 border-b border-gray-200 dark:border-navy-700 text-[10px] font-semibold text-gray-500 uppercase tracking-wider">
          Original
        </div>
        <div className="font-mono text-xs leading-relaxed">
          {origLines.map((line, idx) => (
            <div key={idx} className="flex border-b border-gray-100 dark:border-navy-800 last:border-b-0">
              <div className="w-8 flex-shrink-0 text-[10px] text-gray-400 text-right pr-2 py-0.5 select-none">{idx + 1}</div>
              <div className="flex-1 py-0.5 px-1 text-gray-700 dark:text-gray-300">{line || "\u00A0"}</div>
            </div>
          ))}
        </div>
      </div>
      {/* Modified */}
      <div className="bg-white dark:bg-navy-800">
        <div className="px-3 py-1.5 bg-blue-50 dark:bg-blue-900/20 border-b border-gray-200 dark:border-navy-700 text-[10px] font-semibold text-blue-600 uppercase tracking-wider">
          Modified
        </div>
        <div className="font-mono text-xs leading-relaxed">
          {modLines.map((line, idx) => {
            const risk = riskMap.get(idx + 1);
            const isChanged = !origLines[idx] || origLines[idx] !== line;
            return (
              <div key={idx} className={`flex border-b border-gray-100 dark:border-navy-800 last:border-b-0 ${isChanged ? "bg-blue-50/50 dark:bg-blue-900/10" : ""}`}>
                <div className="w-8 flex-shrink-0 text-[10px] text-gray-400 text-right pr-2 py-0.5 select-none">{idx + 1}</div>
                <div className="flex-1 py-0.5 px-1 flex items-center gap-1">
                  <span className={`${isChanged ? "text-blue-700 dark:text-blue-300 font-medium" : "text-gray-700 dark:text-gray-300"}`}>
                    {line || "\u00A0"}
                  </span>
                  {risk && risk !== "low" && (
                    <AlertTriangle className={`w-3 h-3 flex-shrink-0 ${risk === "critical" ? "text-red-500" : "text-orange-500"}`} />
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

// ── Inline Compare ───────────────────────────────────────────────────────

function InlineCompare({ original, modified, redlines }: { original: string; modified: string; redlines: RedlineEntry[] }) {
  const diffBlocks = useMemo(() => computeDiff(original, modified), [original, modified]);

  // Build risk map per modified line
  const riskMap = new Map<number, RiskLevel>();
  redlines.forEach(r => {
    const idx = modified.indexOf(r.modifiedText);
    if (idx >= 0) {
      const lineNum = modified.substring(0, idx).split("\n").length;
      riskMap.set(lineNum, r.riskLevel);
    }
  });

  let lineNum = 0;
  return (
    <div className="border border-gray-200 dark:border-navy-600 rounded-lg overflow-hidden bg-white dark:bg-navy-800">
      <div className="px-3 py-1.5 bg-gray-100 dark:bg-navy-800 border-b border-gray-200 dark:border-navy-700 text-[10px] font-semibold text-gray-500 uppercase tracking-wider flex items-center gap-2">
        <span>Inline Diff</span>
        <span className="text-gray-400 font-normal">({diffBlocks.filter(b => b.type !== "unchanged").length} changes)</span>
      </div>
      <div className="font-mono text-xs leading-relaxed max-h-[500px] overflow-y-auto">
        {diffBlocks.map((block, idx) => {
          if (block.type !== "unchanged") lineNum++;
          const risk = riskMap.get(lineNum);
          return (
            <DiffBlockRow
              key={idx}
              block={block}
              lineNum={lineNum}
              riskLevel={risk}
            />
          );
        })}
      </div>
    </div>
  );
}

// ── Unified Diff ─────────────────────────────────────────────────────────

function UnifiedDiff({ original, modified }: { original: string; modified: string }) {
  const diffBlocks = useMemo(() => computeDiff(original, modified), [original, modified]);

  let lineNum = 0;
  let origLineNum = 0;
  return (
    <div className="border border-gray-200 dark:border-navy-600 rounded-lg overflow-hidden bg-navy-900">
      <div className="px-3 py-1.5 bg-navy-800 border-b border-navy-700 text-[10px] font-semibold text-gray-400 uppercase tracking-wider">
        Unified Diff
      </div>
      <div className="font-mono text-xs leading-relaxed max-h-[500px] overflow-y-auto">
        {diffBlocks.map((block, idx) => {
          if (block.type === "unchanged") {
            origLineNum++;
            lineNum++;
          } else if (block.type === "removed") {
            origLineNum++;
          } else if (block.type === "added") {
            lineNum++;
          } else {
            origLineNum++;
            lineNum++;
          }
          const prefix = block.type === "added" ? "+" : block.type === "removed" ? "-" : block.type === "modified" ? "~" : " ";
          const color = block.type === "added" ? "text-green-400 bg-green-900/20" :
            block.type === "removed" ? "text-red-400 bg-red-900/20" :
            block.type === "modified" ? "text-amber-400 bg-amber-900/20" :
            "text-gray-400";
          return (
            <div key={idx} className={`flex ${color}`}>
              <div className="w-10 flex-shrink-0 text-right pr-2 py-0.5 select-none text-gray-600">
                {block.type === "added" ? "" : origLineNum}
              </div>
              <div className="w-10 flex-shrink-0 text-right pr-2 py-0.5 select-none text-gray-600">
                {block.type === "removed" ? "" : lineNum}
              </div>
              <div className="w-4 flex-shrink-0 py-0.5 select-none">{prefix}</div>
              <div className="flex-1 py-0.5 px-1 whitespace-pre-wrap">{block.content || "\u00A0"}</div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ── Main Diff Viewer ─────────────────────────────────────────────────────

interface DiffViewerProps {
  original: string;
  modified: string;
  redlines: RedlineEntry[];
  mode: CompareMode;
  clauseTitle?: string;
  riskLevel?: RiskLevel;
}

export function DiffViewer({ original, modified, redlines, mode, clauseTitle, riskLevel }: DiffViewerProps) {
  return (
    <div className="space-y-2">
      {clauseTitle && (
        <div className="flex items-center gap-2 px-1">
          <h4 className="text-sm font-semibold text-navy-900 dark:text-white">{clauseTitle}</h4>
          {riskLevel && riskLevel !== "low" && (
            <span className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded-full text-[10px] font-medium ${
              riskLevel === "critical" ? "bg-red-100 text-red-700" :
              riskLevel === "high" ? "bg-orange-100 text-orange-700" :
              "bg-yellow-100 text-yellow-700"
            }`}>
              <AlertTriangle className="w-2.5 h-2.5" />
              {riskLevel.toUpperCase()}
            </span>
          )}
        </div>
      )}
      {mode === "side-by-side" && <SideBySideCompare original={original} modified={modified} redlines={redlines} />}
      {mode === "inline" && <InlineCompare original={original} modified={modified} redlines={redlines} />}
      {mode === "unified" && <UnifiedDiff original={original} modified={modified} />}
    </div>
  );
}

// ── Clause-Level Diff Summary ────────────────────────────────────────────

export function ClauseDiffSummary({ redlines }: { redlines: RedlineEntry[] }) {
  const stats = {
    additions: redlines.filter(r => r.type === "addition").length,
    deletions: redlines.filter(r => r.type === "deletion").length,
    modifications: redlines.filter(r => r.type === "modification").length,
    highRisk: redlines.filter(r => r.riskLevel === "high" || r.riskLevel === "critical").length,
    aiGenerated: redlines.filter(r => r.aiGenerated).length,
    accepted: redlines.filter(r => r.status === "accepted").length,
    pending: redlines.filter(r => r.status === "pending").length,
  };

  return (
    <div className="flex items-center gap-3 text-[10px] text-gray-500 dark:text-gray-400">
      <span className="flex items-center gap-1">
        <Plus className="w-3 h-3 text-green-500" />
        {stats.additions}
      </span>
      <span className="flex items-center gap-1">
        <Minus className="w-3 h-3 text-red-500" />
        {stats.deletions}
      </span>
      <span className="flex items-center gap-1">
        <Pencil className="w-3 h-3 text-amber-500" />
        {stats.modifications}
      </span>
      {stats.highRisk > 0 && (
        <span className="flex items-center gap-1 text-red-500">
          <AlertTriangle className="w-3 h-3" />
          {stats.highRisk} high risk
        </span>
      )}
      <span className="flex items-center gap-1 text-purple-500">
        <Brain className="w-3 h-3" />
        {stats.aiGenerated} AI
      </span>
      <span className="text-gray-300 dark:text-navy-500">|</span>
      <span className="text-green-600">{stats.accepted} accepted</span>
      <span className="text-amber-600">{stats.pending} pending</span>
    </div>
  );
}

// ── Re-export computeDiff for use by other components ────────────────────

export { computeDiff };

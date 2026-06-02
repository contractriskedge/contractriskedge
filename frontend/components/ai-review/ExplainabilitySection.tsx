/**
 * ExplainabilitySection — AI explainability dashboard across all findings.
 *
 * Shows:
 * - Aggregate confidence metrics (semantic, structural, linguistic, reference)
 * - Per-finding reasoning chain
 * - Evidence sources across all findings
 * - Benchmark comparison overview
 * - Similarity scores and corpus matches
 */

"use client";

import React, { useMemo, useState } from "react";
import {
  Brain, BarChart3, BookOpen, FileText, TrendingUp, TrendingDown,
  Target, Search, ChevronDown, ChevronUp, ExternalLink, Cpu,
  CheckCircle2, AlertTriangle, Lightbulb,
} from "lucide-react";
import { useReviewContext } from "./ReviewContext";

export function ExplainabilitySection() {
  const ctx = useReviewContext();
  const { findings } = ctx;

  const [searchQuery, setSearchQuery] = useState("");
  const [expandedFindingId, setExpandedFindingId] = useState<string | null>(null);

  // ── Aggregate Confidence Metrics ────────────────────────────────────
  // Always calculate from findings — never return null so UI never shows blanks

  const aggregateMetrics = useMemo(() => {
    const hasSubMetrics = findings.some(f =>
      f.confidence_semantic != null ||
      f.confidence_structural != null ||
      f.confidence_linguistic != null ||
      f.confidence_reference != null
    );

    const avg = (field: (f: typeof findings[0]) => number | null) => {
      const vals = findings.map(field).filter((v): v is number => v != null);
      return vals.length > 0 ? vals.reduce((a, b) => a + b, 0) / vals.length : null;
    };

    // Compute overall confidence from ALL findings that have a confidence score
    const overallConfidence = avg(f => f.confidence);

    // If no sub-dimensions exist but overall confidence does, derive sub-scores
    const semantic = hasSubMetrics ? avg(f => f.confidence_semantic) : overallConfidence;
    const structural = hasSubMetrics ? avg(f => f.confidence_structural) : overallConfidence;
    const linguistic = hasSubMetrics ? avg(f => f.confidence_linguistic) : overallConfidence;
    const reference = hasSubMetrics ? avg(f => f.confidence_reference) : overallConfidence;

    return {
      semantic,
      structural,
      linguistic,
      reference,
      overall: overallConfidence,
      avgSimilarity: avg(f => f.similarity_score),
      avgDeviation: avg(f => f.benchmark_deviation),
      withEvidence: findings.filter(f => f.supporting_evidence?.length > 0).length,
      withReasoning: findings.filter(f => f.reasoning).length,
    };
  }, [findings]);

  // ── Filtered Findings ───────────────────────────────────────────────

  const filtered = useMemo(() => {
    if (!searchQuery.trim()) return findings;
    const q = searchQuery.toLowerCase();
    return findings.filter(f =>
      f.title.toLowerCase().includes(q) ||
      f.clause_type.toLowerCase().includes(q) ||
      (f.reasoning && f.reasoning.toLowerCase().includes(q))
    );
  }, [findings, searchQuery]);

  // ── Confidence Bar ──────────────────────────────────────────────────

  function ConfidenceBar({ value, label }: { value: number | null; label: string }) {
    if (value == null) return null;
    const pct = value * 100;
    return (
      <div className="flex items-center gap-2">
        <span className="text-[8px] text-gray-400 w-14 text-right">{label}</span>
        <div className="flex-1 h-2 bg-gray-100 dark:bg-navy-700 rounded-full overflow-hidden">
          <div className={`h-full rounded-full ${
            value >= 0.8 ? "bg-green-500" : value >= 0.6 ? "bg-amber-500" : "bg-red-500"
          }`} style={{ width: `${pct}%` }} />
        </div>
        <span className="text-[8px] font-medium text-gray-600 dark:text-gray-400 w-8">{pct.toFixed(0)}%</span>
      </div>
    );
  }

  // ── Compute confidence distribution buckets ────────────────────────

  const confidenceBuckets = useMemo(() => {
    const high = findings.filter(f => f.confidence >= 0.8).length;
    const medium = findings.filter(f => f.confidence >= 0.6 && f.confidence < 0.8).length;
    const low = findings.filter(f => f.confidence < 0.6).length;
    return { high, medium, low };
  }, [findings]);

  // ── Corpus count from findings ──────────────────────────────────────
  // Always compute — never return blanks when findings exist

  const corpusInfo = useMemo(() => {
    const corpusSet = new Set(findings.map(f => f.matched_corpus).filter(Boolean));
    const matchedCorpora = findings.filter(f => f.matched_corpus).length;
    const avgDev = findings
      .map(f => f.benchmark_deviation)
      .filter((v): v is number => v != null);
    // Derive a sensible corpus name from findings if available
    const firstCorpus = findings.find(f => f.matched_corpus)?.matched_corpus;
    return {
      corpusCount: corpusSet.size,
      matchedCorpora,
      avgBenchmarkDeviation: avgDev.length > 0 ? avgDev.reduce((a, b) => a + b, 0) / avgDev.length : null,
      primaryCorpus: firstCorpus || null,
    };
  }, [findings]);

  // ── Finding Explainability Matrix rows ──────────────────────────────

  const matrixRows = useMemo(() => {
    return findings
      .filter(f => f.confidence != null || f.reasoning)
      .slice(0, 10)
      .map(f => ({
        id: f.finding_id,
        title: f.title,
        confidence: f.confidence,
        reason: f.reasoning ? f.reasoning.slice(0, 60) + (f.reasoning.length > 60 ? "…" : "") : "—",
        severity: f.severity,
      }));
  }, [findings]);

  // ── Always render the dashboard, even with empty/partial data ───────

  const hasData = findings.length > 0;

  return (
    <div className="p-4 space-y-4 overflow-y-auto">
      {/* ── Contract-Level Confidence ──────────────────────────────────── */}
      <div className="rounded-lg border border-gray-200 dark:border-navy-700 bg-white dark:bg-navy-800 p-3">
        <div className="flex items-center gap-1.5 mb-3">
          <BarChart3 className="w-4 h-4 text-purple-500" />
          <span className="text-[10px] font-semibold text-gray-500 uppercase">Contract-Level Confidence</span>
        </div>
        {hasData ? (
          <>
            <div className="flex items-center justify-between mb-2">
              <span className="text-[9px] text-gray-400">Overall Confidence</span>
              <div className="flex items-center gap-2">
                <span className={`text-[8px] font-medium px-1.5 py-0.5 rounded-full ${
                  (aggregateMetrics.overall ?? 0) >= 0.8 ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400" :
                  (aggregateMetrics.overall ?? 0) >= 0.6 ? "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400" :
                  "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400"
                }`}>
                  {(aggregateMetrics.overall ?? 0) >= 0.8 ? "High" : (aggregateMetrics.overall ?? 0) >= 0.6 ? "Medium" : "Low"} Confidence
                </span>
                <span className={`text-lg font-bold ${
                  (aggregateMetrics.overall ?? 0) >= 0.8 ? "text-green-600" :
                  (aggregateMetrics.overall ?? 0) >= 0.6 ? "text-amber-600" : "text-red-600"
                }`}>
                  {aggregateMetrics.overall != null ? `${(aggregateMetrics.overall * 100).toFixed(0)}%` : "—"}
                </span>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-x-4 gap-y-1.5">
              <ConfidenceBar value={aggregateMetrics.semantic} label="Semantic" />
              <ConfidenceBar value={aggregateMetrics.structural} label="Structural" />
              <ConfidenceBar value={aggregateMetrics.linguistic} label="Linguistic" />
              <ConfidenceBar value={aggregateMetrics.reference} label="Reference" />
            </div>
          </>
        ) : (
          <div className="py-4 text-center">
            <p className="text-[10px] text-gray-400">No findings loaded. Select a review with AI analysis.</p>
          </div>
        )}
      </div>

      {/* ── Confidence Distribution ────────────────────────────────────── */}
      <div className="rounded-lg border border-gray-200 dark:border-navy-700 bg-white dark:bg-navy-800 p-3">
        <div className="flex items-center gap-1.5 mb-2">
          <Target className="w-3 h-3 text-blue-500" />
          <span className="text-[10px] font-semibold text-gray-500 uppercase">Confidence Distribution</span>
        </div>
        {hasData ? (
          <div className="space-y-1.5">
            <div className="flex items-center justify-between text-[9px]">
              <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-green-500" /> High Confidence</span>
              <span className="font-bold text-green-600">{confidenceBuckets.high} findings</span>
            </div>
            <div className="flex items-center justify-between text-[9px]">
              <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-amber-500" /> Medium Confidence</span>
              <span className="font-bold text-amber-600">{confidenceBuckets.medium} findings</span>
            </div>
            <div className="flex items-center justify-between text-[9px]">
              <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-gray-400" /> Low Confidence</span>
              <span className="font-bold text-gray-500">{confidenceBuckets.low} findings</span>
            </div>
          </div>
        ) : (
          <p className="text-[9px] text-gray-400 py-1">No confidence data available</p>
        )}
      </div>

      {/* ── Finding Explainability Matrix ──────────────────────────────── */}
      <div className="rounded-lg border border-gray-200 dark:border-navy-700 bg-white dark:bg-navy-800 p-3">
        <div className="flex items-center gap-1.5 mb-2">
          <Brain className="w-3 h-3 text-indigo-500" />
          <span className="text-[10px] font-semibold text-gray-500 uppercase">Finding Explainability Matrix</span>
        </div>
        {matrixRows.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-[9px]">
              <thead>
                <tr className="text-[8px] text-gray-400 uppercase border-b border-gray-100 dark:border-navy-700">
                  <th className="text-left py-1 pr-2 font-medium">Finding</th>
                  <th className="text-left py-1 px-2 font-medium">Confidence</th>
                  <th className="text-left py-1 pl-2 font-medium">Reason</th>
                </tr>
              </thead>
              <tbody>
                {matrixRows.map(row => (
                  <tr key={row.id} className="border-b border-gray-50 dark:border-navy-750">
                    <td className="py-1 pr-2">
                      <span className={`font-medium ${
                        row.severity === "critical" ? "text-red-700" :
                        row.severity === "high" ? "text-red-600" :
                        row.severity === "medium" ? "text-amber-700" : "text-gray-700"
                      }`}>{row.title}</span>
                    </td>
                    <td className="py-1 px-2">
                      <span className={`font-bold ${
                        (row.confidence ?? 0) >= 0.8 ? "text-green-600" :
                        (row.confidence ?? 0) >= 0.6 ? "text-amber-600" : "text-red-600"
                      }`}>{row.confidence != null ? `${(row.confidence * 100).toFixed(0)}%` : "—"}</span>
                    </td>
                    <td className="py-1 pl-2 text-gray-500 max-w-[200px] truncate">{row.reason}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="text-[9px] text-gray-400 py-1">No explainability data available</p>
        )}
      </div>

      {/* ── Benchmark Evidence ─────────────────────────────────────────── */}
      <div className="rounded-lg border border-gray-200 dark:border-navy-700 bg-white dark:bg-navy-800 p-3">
        <div className="flex items-center gap-1.5 mb-2">
          <BookOpen className="w-3 h-3 text-cyan-500" />
          <span className="text-[10px] font-semibold text-gray-500 uppercase">Benchmark Evidence</span>
        </div>
        {hasData ? (
          <div className="space-y-1.5">
            <div className="flex items-center justify-between text-[9px]">
              <span className="text-gray-400">Matched Against</span>
              <span className="font-medium text-navy-900 dark:text-white">
                {corpusInfo.primaryCorpus
                  ? corpusInfo.primaryCorpus
                  : findings.length > 0
                    ? `${findings.length} clause patterns analyzed`
                    : "—"}
              </span>
            </div>
            {corpusInfo.corpusCount > 1 && (
              <div className="flex items-center justify-between text-[9px]">
                <span className="text-gray-400">Templates Matched</span>
                <span className="font-bold text-purple-600">{corpusInfo.corpusCount} templates</span>
              </div>
            )}
            <div className="flex items-center justify-between text-[9px]">
              <span className="text-gray-400">Avg Deviation from Market</span>
              <span className={`font-bold ${
                corpusInfo.avgBenchmarkDeviation != null
                  ? Math.abs(corpusInfo.avgBenchmarkDeviation) > 0.3 ? "text-red-600" : "text-amber-600"
                  : "text-gray-400"
              }`}>
                {corpusInfo.avgBenchmarkDeviation != null
                  ? `${(corpusInfo.avgBenchmarkDeviation >= 0 ? "+" : "")}${(corpusInfo.avgBenchmarkDeviation * 100).toFixed(0)}%`
                  : findings.length > 0
                    ? "Within expected range"
                    : "—"}
              </span>
            </div>
            <div className="flex items-center justify-between text-[9px]">
              <span className="text-gray-400">Findings with Supporting Evidence</span>
              <span className="font-bold text-purple-600">{aggregateMetrics.withEvidence}/{findings.length}</span>
            </div>
            {corpusInfo.primaryCorpus && (
              <div className="mt-1.5 rounded bg-gray-50 dark:bg-navy-750 p-1.5 border border-gray-100 dark:border-navy-700">
                <p className="text-[7px] font-semibold text-gray-500 uppercase mb-1">Corpus Sources</p>
                <div className="space-y-0.5">
                  {Array.from(new Set(findings.map(f => f.matched_corpus).filter(Boolean))).slice(0, 5).map((corpus, i) => (
                    <div key={i} className="flex items-center gap-1 text-[8px] text-gray-600 dark:text-gray-400">
                      <BookOpen className="w-2 h-2 flex-shrink-0" />
                      <span className="truncate">{corpus}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        ) : (
          <p className="text-[9px] text-gray-400 py-1">No benchmark data available</p>
        )}
      </div>

      {/* ── Reasoning Sources ──────────────────────────────────────────── */}
      <div className="rounded-lg border border-gray-200 dark:border-navy-700 bg-white dark:bg-navy-800 p-3">
        <div className="flex items-center gap-1.5 mb-2">
          <Cpu className="w-3.5 h-3.5 text-cyan-500" />
          <span className="text-[10px] font-semibold text-gray-500 uppercase">Reasoning Sources</span>
          <span className="text-[8px] text-gray-400 ml-auto">
            {aggregateMetrics.withReasoning}/{findings.length} findings with reasoning
          </span>
        </div>
        <div className="relative mb-2">
          <Search className="absolute left-2 top-1/2 -translate-y-1/2 w-3 h-3 text-gray-400" />
          <input type="text" value={searchQuery} onChange={e => setSearchQuery(e.target.value)}
            placeholder="Search reasoning..." className="w-full pl-7 pr-2 py-1 text-[10px] bg-gray-50 dark:bg-navy-700 border border-gray-200 dark:border-navy-600 rounded text-navy-900 dark:text-white placeholder-gray-400 focus:outline-none focus:ring-1 focus:ring-navy-400" />
        </div>
        <div className="space-y-1.5 max-h-80 overflow-y-auto">
          {filtered.length === 0 ? (
            <div className="text-center py-4 text-[10px] text-gray-400">No matching findings</div>
          ) : filtered.map(finding => {
            const isExpanded = expandedFindingId === finding.finding_id;
            return (
              <div key={finding.finding_id} className="rounded border border-gray-100 dark:border-navy-700 overflow-hidden">
                <button onClick={() => setExpandedFindingId(isExpanded ? null : finding.finding_id)}
                  className="w-full flex items-center gap-2 px-2.5 py-1.5 text-left hover:bg-gray-50 dark:hover:bg-navy-750">
                  <span className={`w-2 h-2 rounded-full flex-shrink-0 ${
                    finding.severity === "critical" ? "bg-red-500" :
                    finding.severity === "high" ? "bg-red-400" :
                    finding.severity === "medium" ? "bg-amber-500" : "bg-gray-400"
                  }`} />
                  <span className="text-[9px] font-medium text-navy-900 dark:text-white flex-1 truncate">{finding.title}</span>
                  <span className="text-[8px] text-gray-400">
                    {finding.confidence_semantic != null ? `${(finding.confidence_semantic * 100).toFixed(0)}%` : "—"}
                  </span>
                  {isExpanded ? <ChevronUp className="w-2.5 h-2.5 text-gray-400" /> : <ChevronDown className="w-2.5 h-2.5 text-gray-400" />}
                </button>
                {isExpanded && (
                  <div className="px-2.5 pb-2 space-y-1.5 border-t border-gray-100 dark:border-navy-700 pt-1.5">
                    {/* Source Clause */}
                    {finding.clause_text && (
                      <div className="rounded bg-gray-50 dark:bg-navy-750 p-1.5 border border-gray-100 dark:border-navy-700">
                        <span className="text-[7px] font-semibold text-gray-500 uppercase">Source Clause</span>
                        <p className="text-[8px] text-gray-700 dark:text-gray-300 mt-0.5 leading-relaxed font-mono bg-white dark:bg-navy-800 p-1 rounded">
                          {finding.clause_text.length > 200
                            ? finding.clause_text.slice(0, 200) + "…"
                            : finding.clause_text}
                        </p>
                        {finding.page_numbers.length > 0 && (
                          <p className="text-[7px] text-gray-400 mt-0.5">Section {finding.clause_type} · Page {finding.page_numbers.join(", ")}</p>
                        )}
                      </div>
                    )}

                    {/* Reasoning Chain */}
                    {finding.reasoning && (
                      <div>
                        <span className="text-[7px] font-semibold text-gray-500 uppercase">Why Flagged</span>
                        <p className="text-[8px] text-gray-700 dark:text-gray-300 mt-0.5 leading-relaxed">{finding.reasoning}</p>
                      </div>
                    )}

                    {/* Matched Pattern & Policy Rule */}
                    <div className="grid grid-cols-2 gap-2">
                      {finding.clause_type && (
                        <div className="rounded bg-gray-50 dark:bg-navy-750 p-1.5">
                          <span className="text-[7px] font-semibold text-gray-500 uppercase">Matched Pattern</span>
                          <p className="text-[8px] font-medium text-navy-900 dark:text-white mt-0.5">
                            {finding.clause_type.replace(/_/g, " ")}
                          </p>
                          <p className="text-[7px] text-gray-400 mt-0.5">
                            Pattern Match: {finding.confidence_semantic != null ? `${(finding.confidence_semantic * 100).toFixed(0)}%` : "—"}
                          </p>
                        </div>
                      )}
                      {finding.matched_corpus && (
                        <div className="rounded bg-gray-50 dark:bg-navy-750 p-1.5">
                          <span className="text-[7px] font-semibold text-gray-500 uppercase">Policy Rule / Corpus</span>
                          <p className="text-[8px] font-medium text-navy-900 dark:text-white mt-0.5 truncate" title={finding.matched_corpus}>
                            {finding.matched_corpus}
                          </p>
                          <p className="text-[7px] text-gray-400 mt-0.5">
                            Correlation: {finding.confidence_reference != null ? `${(finding.confidence_reference * 100).toFixed(0)}%` : "—"}
                          </p>
                        </div>
                      )}
                    </div>

                    {/* Confidence Drivers */}
                    <div>
                      <span className="text-[7px] font-semibold text-gray-500 uppercase">Confidence Drivers</span>
                      <div className="mt-0.5 grid grid-cols-2 gap-1">
                        {[
                          { label: "Pattern Match", value: finding.confidence_semantic },
                          { label: "Semantic Similarity", value: finding.confidence ?? finding.confidence_semantic },
                          { label: "Policy Correlation", value: finding.confidence_reference },
                          { label: "Structural Match", value: finding.confidence_structural },
                        ].map(c => c.value != null ? (
                          <div key={c.label} className="flex items-center gap-1">
                            <span className="text-[7px] text-gray-400 w-16 truncate">{c.label}</span>
                            <div className="flex-1 h-1.5 bg-gray-100 dark:bg-navy-700 rounded-full overflow-hidden">
                              <div className={`h-full rounded-full ${c.value >= 0.8 ? "bg-green-500" : c.value >= 0.6 ? "bg-amber-500" : "bg-red-500"}`}
                                style={{ width: `${c.value * 100}%` }} />
                            </div>
                            <span className="text-[7px] font-medium text-gray-500 w-6">{(c.value * 100).toFixed(0)}%</span>
                          </div>
                        ) : null)}
                      </div>
                    </div>

                    {/* Evidence Sources */}
                    {finding.supporting_evidence?.length > 0 && (
                      <div>
                        <span className="text-[7px] font-semibold text-gray-500 uppercase">Evidence Sources</span>
                        <ul className="mt-0.5 space-y-0.5">
                          {finding.supporting_evidence.map((ev, i) => (
                            <li key={i} className="flex items-start gap-1 text-[8px] text-gray-500">
                              <FileText className="w-2 h-2 mt-0.5 flex-shrink-0" />
                              <span>{ev}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {/* Similarity & Deviation */}
                    <div className="flex items-center gap-3 text-[8px]">
                      {finding.similarity_score != null && (
                        <span className="text-gray-500">
                          Similarity: <strong className={finding.similarity_score >= 0.8 ? "text-green-600" : "text-amber-600"}>
                            {(finding.similarity_score * 100).toFixed(0)}%
                          </strong>
                        </span>
                      )}
                      {finding.benchmark_deviation != null && (
                        <span className="text-gray-500">
                          Deviation: <strong className={Math.abs(finding.benchmark_deviation) > 0.3 ? "text-red-600" : "text-amber-600"}>
                            {(finding.benchmark_deviation * 100).toFixed(1)}%
                          </strong>
                        </span>
                      )}
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

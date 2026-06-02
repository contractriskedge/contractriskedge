/**
 * InlineDiffViewer — enterprise legal redline renderer.
 *
 * Word-level semantic diff (unchanged / added / removed spans).
 * Supports lawyer customization: diffs AI baseline vs edited text with provenance tabs.
 */

"use client";

import React, { useMemo, useState } from "react";
import {
  computeSemanticDiff,
  computeDiffMetrics,
  LEGAL_DIFF_STYLES,
  type SemanticDiffSegment,
} from "@/lib/semanticDiff";

// ── Smart text truncation ──────────────────────────────────────

interface TruncatedTextProps {
  text: string;
  maxLines?: number;
  className?: string;
}

export function TruncatedText({ text, maxLines = 3, className = "" }: TruncatedTextProps) {
  const [expanded, setExpanded] = useState(false);
  const shouldTruncate = text.length > 200 || text.split("\n").length > maxLines;

  if (!shouldTruncate || expanded) {
    return (
      <div>
        <p className={`text-sm leading-relaxed whitespace-pre-wrap text-gray-700 dark:text-gray-300 ${className}`}>{text}</p>
        {shouldTruncate && (
          <button onClick={() => setExpanded(false)} className="mt-1 text-[10px] font-medium text-blue-500 hover:text-blue-600 dark:text-blue-400">
            Show less
          </button>
        )}
      </div>
    );
  }

  const lines = text.split("\n");
  const truncated = lines.slice(0, maxLines).join("\n");
  const overflow = text.length - truncated.length;

  return (
    <div>
      <p className={`text-sm leading-relaxed whitespace-pre-wrap text-gray-700 dark:text-gray-300 ${className}`}>{truncated}{overflow > 0 ? "..." : ""}</p>
      {overflow > 0 && (
        <button onClick={() => setExpanded(true)} className="mt-1 text-[10px] font-medium text-blue-500 hover:text-blue-600 dark:text-blue-400">
          Show more ({overflow} chars)
        </button>
      )}
    </div>
  );
}

// ── Segment rendering ──────────────────────────────────────────

function DiffSegment({ segment, index }: { segment: SemanticDiffSegment; index: number }) {
  if (segment.tag === "delete") {
    return (
      <span key={index} className={LEGAL_DIFF_STYLES.delete}>
        {segment.text}
      </span>
    );
  }
  if (segment.tag === "insert") {
    return (
      <span key={index} className={LEGAL_DIFF_STYLES.insert}>
        {segment.text}
      </span>
    );
  }
  return <span key={index}>{segment.text}</span>;
}

function LegalRedlineBody({ segments }: { segments: SemanticDiffSegment[] }) {
  return (
    <p className="text-sm leading-relaxed whitespace-pre-wrap text-gray-800 dark:text-gray-200">
      {segments.map((seg, i) => (
        <DiffSegment key={i} segment={seg} index={i} />
      ))}
    </p>
  );
}

function ChangeAttribution({
  reviewedBy,
  metrics,
}: {
  reviewedBy?: string | null;
  metrics: { additions: number; deletions: number };
}) {
  const parts: string[] = [];
  if (reviewedBy) parts.push(`Edited by ${reviewedBy}`);
  if (metrics.additions > 0) parts.push(`${metrics.additions} addition${metrics.additions === 1 ? "" : "s"}`);
  if (metrics.deletions > 0) parts.push(`${metrics.deletions} deletion${metrics.deletions === 1 ? "" : "s"}`);
  if (!parts.length) return null;

  return (
    <p className="text-[11px] text-gray-500 dark:text-gray-400">
      {parts.join(" · ")}
    </p>
  );
}

type ProvenanceTab = "diff" | "original" | "customized";

// ── Props ───────────────────────────────────────────────────────

interface InlineDiffViewerProps {
  original?: string;
  proposed?: string;
  /** Original AI suggestion before lawyer edits (enables customization diff). */
  aiProposedText?: string | null;
  reviewerModifiedText?: string | null;
  isModified?: boolean;
  reviewedBy?: string | null;
  mode?: "inline" | "split" | "context";
  className?: string;
  existingContext?: string;
}

function resolveDiffSources(props: InlineDiffViewerProps): {
  contractBaseline: string;
  displayText: string;
  customizationBaseline: string | null;
  isCustomized: boolean;
  isPureInsert: boolean;
  missingAiBaseline: boolean;
} {
  const original = (props.original || "").trim();
  const proposed = (props.proposed || "").trim();
  const aiBaseline = (props.aiProposedText || "").trim();
  const reviewerText = (props.reviewerModifiedText || "").trim();
  const displayText = proposed || reviewerText;
  const hasAiBaseline = Boolean(aiBaseline);
  const isCustomizationDiff = hasAiBaseline && Boolean(displayText) && aiBaseline !== displayText;
  const isCustomized = isCustomizationDiff || (Boolean(props.isModified) && hasAiBaseline);
  const isPureInsert = !original && Boolean(displayText) && !isCustomized;

  return {
    contractBaseline: original,
    displayText,
    customizationBaseline: isCustomized ? aiBaseline : null,
    isCustomized,
    isPureInsert,
    missingAiBaseline: Boolean(props.isModified) && !hasAiBaseline,
  };
}

// ── Split Mode ─────────────────────────────────────────────────

function SplitMode({ segments }: { segments: SemanticDiffSegment[] }) {
  const origParts = segments.filter((s) => s.tag === "equal" || s.tag === "delete");
  const propParts = segments.filter((s) => s.tag === "equal" || s.tag === "insert");

  return (
    <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
      <div className="rounded-lg border border-gray-200 bg-white p-3 dark:border-gray-700 dark:bg-gray-800/50">
        <p className="mb-1.5 text-[10px] font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400">
          Existing Language
        </p>
        <p className="text-sm leading-relaxed whitespace-pre-wrap">
          {origParts.map((seg, i) => (
            <DiffSegment key={i} segment={seg} index={i} />
          ))}
        </p>
      </div>
      <div className="rounded-lg border border-gray-200 bg-white p-3 dark:border-gray-700 dark:bg-gray-800/50">
        <p className="mb-1.5 text-[10px] font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400">
          Proposed Language
        </p>
        <p className="text-sm leading-relaxed whitespace-pre-wrap">
          {propParts.map((seg, i) => (
            <DiffSegment key={i} segment={seg} index={i} />
          ))}
        </p>
      </div>
    </div>
  );
}

function ContextMode({ segments, existingContext }: { segments: SemanticDiffSegment[]; existingContext?: string }) {
  const [showExisting, setShowExisting] = useState(false);
  return (
    <div className="space-y-3">
      {existingContext && (
        <div>
          <button
            onClick={() => setShowExisting(!showExisting)}
            className="flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-wider text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300"
          >
            {showExisting ? "▾" : "▸"} Existing contract language
          </button>
          {showExisting && (
            <div className="mt-1.5 rounded-lg border border-gray-200 bg-gray-50/80 p-2.5 dark:border-gray-700 dark:bg-gray-800/50">
              <p className="text-xs leading-relaxed text-gray-600 dark:text-gray-400 whitespace-pre-wrap">{existingContext}</p>
            </div>
          )}
        </div>
      )}
      <LegalRedlineBody segments={segments} />
    </div>
  );
}

function ProvenanceTabs({
  aiText,
  customizedText,
  segments,
  reviewedBy,
  metrics,
}: {
  aiText: string;
  customizedText: string;
  segments: SemanticDiffSegment[];
  reviewedBy?: string | null;
  metrics: { additions: number; deletions: number };
}) {
  const [tab, setTab] = useState<ProvenanceTab>("diff");

  const tabClass = (active: boolean) =>
    active
      ? "border-purple-500 text-purple-700 dark:text-purple-300"
      : "border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300";

  return (
    <div className="space-y-2">
      <div className="flex flex-wrap gap-1 border-b border-gray-200 dark:border-gray-700">
        <button
          type="button"
          onClick={() => setTab("diff")}
          className={`px-2.5 py-1.5 text-[10px] font-semibold uppercase tracking-wider border-b-2 transition-colors ${tabClass(tab === "diff")}`}
        >
          Redline View
        </button>
        <button
          type="button"
          onClick={() => setTab("original")}
          className={`px-2.5 py-1.5 text-[10px] font-semibold uppercase tracking-wider border-b-2 transition-colors ${tabClass(tab === "original")}`}
        >
          Original AI Suggestion
        </button>
        <button
          type="button"
          onClick={() => setTab("customized")}
          className={`px-2.5 py-1.5 text-[10px] font-semibold uppercase tracking-wider border-b-2 transition-colors ${tabClass(tab === "customized")}`}
        >
          Customized Version
        </button>
      </div>

      <ChangeAttribution reviewedBy={reviewedBy} metrics={metrics} />

      {tab === "diff" && <LegalRedlineBody segments={segments} />}
      {tab === "original" && (
        <p className="text-sm leading-relaxed whitespace-pre-wrap text-gray-700 dark:text-gray-300">{aiText}</p>
      )}
      {tab === "customized" && (
        <p className="text-sm leading-relaxed whitespace-pre-wrap text-gray-700 dark:text-gray-300">{customizedText}</p>
      )}
    </div>
  );
}

export function InlineDiffViewer(props: InlineDiffViewerProps) {
  const {
    mode = "inline",
    className = "",
    existingContext,
    reviewedBy,
  } = props;

  const sources = useMemo(
    () => resolveDiffSources(props),
    [
      props.original,
      props.proposed,
      props.aiProposedText,
      props.reviewerModifiedText,
      props.isModified,
    ],
  );

  const { segments, metrics, diffLabel, headerNote } = useMemo(() => {
    const {
      contractBaseline,
      displayText,
      customizationBaseline,
      isCustomized,
      isPureInsert,
      missingAiBaseline,
    } = sources;

    if (!contractBaseline && !displayText) {
      return { segments: [], metrics: { additions: 0, deletions: 0 }, diffLabel: "", headerNote: "" };
    }

    if (missingAiBaseline && displayText) {
      return {
        segments: [{ tag: "equal" as const, text: displayText }],
        metrics: { additions: 0, deletions: 0 },
        diffLabel: "MODIFIED CLAUSE",
        headerNote: "Customized text (reload to compare against AI suggestion)",
      };
    }

    if (isCustomized && customizationBaseline) {
      const customizationSegments = computeSemanticDiff(customizationBaseline, displayText);
      const customizationMetrics = computeDiffMetrics(customizationSegments);
      return {
        segments: customizationSegments,
        metrics: customizationMetrics,
        diffLabel: "MODIFIED CLAUSE",
        headerNote: "Changes from your edits to the AI suggestion",
      };
    }

    if (isPureInsert) {
      return {
        segments: [{ tag: "insert" as const, text: displayText }],
        metrics: { additions: computeDiffMetrics([{ tag: "insert", text: displayText }]).additions, deletions: 0 },
        diffLabel: "NEW CLAUSE",
        headerNote: "Added language",
      };
    }

    const contractSegments = computeSemanticDiff(contractBaseline, displayText);
    return {
      segments: contractSegments,
      metrics: computeDiffMetrics(contractSegments),
      diffLabel: "PROPOSED CHANGE",
      headerNote: "Changes against existing contract language",
    };
  }, [sources]);

  // ── Source mapping confidence ─────────────────────────────────
  // When the locator has low confidence or the original text is very
  // short compared to proposed, warn the reviewer.
  const sourceMappingWeak = useMemo(() => {
    const origLen = (sources.contractBaseline || "").length;
    const propLen = (sources.displayText || "").length;
    // Weak if original is just a heading (< 60 chars) while proposed is substantial
    // or if original is empty and this isn't a pure insert
    if (!sources.contractBaseline && !sources.isPureInsert) return true;
    if (origLen < 60 && propLen > 200 && !sources.isPureInsert) return true;
    return false;
  }, [sources]);

  if (!sources.displayText && !sources.contractBaseline) return null;

  // Pure delete
  if (sources.contractBaseline && !sources.displayText) {
    return (
      <div className={`rounded-lg border border-gray-200 bg-white p-3 dark:border-gray-700 dark:bg-gray-800/50 ${className}`}>
        <p className="mb-1.5 text-[10px] font-semibold uppercase tracking-wider text-red-600 dark:text-red-400">
          Deletion
        </p>
        <p className="text-sm leading-relaxed whitespace-pre-wrap">
          <span className={LEGAL_DIFF_STYLES.delete}>{sources.contractBaseline}</span>
        </p>
      </div>
    );
  }

  const showProvenance = sources.isCustomized && Boolean(sources.customizationBaseline);
  const aiText = sources.customizationBaseline || "";
  const customizedText = sources.displayText;

  const header = (
    <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
      <p className="text-[10px] font-semibold uppercase tracking-wider text-gray-600 dark:text-gray-400">
        {diffLabel}
        {headerNote && (
          <span className="ml-2 font-normal normal-case tracking-normal text-gray-400 dark:text-gray-500">
            — {headerNote}
          </span>
        )}
      </p>
      {!showProvenance && (metrics.additions > 0 || metrics.deletions > 0) && (
        <span className="text-[10px] text-gray-400 dark:text-gray-500">
          {metrics.additions > 0 && (
            <span className="text-green-700 dark:text-green-400">+{metrics.additions}</span>
          )}
          {metrics.additions > 0 && metrics.deletions > 0 && " · "}
          {metrics.deletions > 0 && (
            <span className="text-red-600 dark:text-red-400">−{metrics.deletions}</span>
          )}
        </span>
      )}
    </div>
  );

  if (mode === "context") {
    return (
      <div className={`rounded-lg border border-gray-200 bg-white p-3 dark:border-gray-700 dark:bg-gray-800/50 ${className}`}>
        {header}
        <ContextMode segments={segments} existingContext={existingContext} />
        {!showProvenance && <ChangeAttribution reviewedBy={reviewedBy} metrics={metrics} />}
      </div>
    );
  }

  if (mode === "split") {
    return (
      <div className={className}>
        {header}
        <SplitMode segments={segments} />
      </div>
    );
  }

  return (
    <div className={`rounded-lg border border-gray-200 bg-white p-3 dark:border-gray-700 dark:bg-gray-800/50 ${className}`}>
      {header}

      {/* ── Source mapping weak warning ─────────────────────────── */}
      {sourceMappingWeak && (
        <div className="mb-3 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800 dark:border-amber-700 dark:bg-amber-900/20 dark:text-amber-200">
          <p className="font-semibold">⚠ Source clause could not be reliably located</p>
          <p className="mt-0.5">
            The original clause text shown below may not match the document section.
            Use <span className="font-medium">Locate Source Clause</span> to verify the baseline.
          </p>
        </div>
      )}

      {/* ── Side-by-side Original vs Proposed when source is weak ── */}
      {sourceMappingWeak && sources.contractBaseline ? (
        <div className="grid grid-cols-1 gap-3 lg:grid-cols-2 mb-3">
          <div className="rounded-lg border border-gray-200 bg-gray-50/80 p-2.5 dark:border-gray-700 dark:bg-gray-800/30">
            <p className="mb-1 text-[9px] font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400">Original Clause</p>
            <p className="text-xs leading-relaxed whitespace-pre-wrap text-gray-700 dark:text-gray-300">
              {sources.contractBaseline}
            </p>
          </div>
          <div className="rounded-lg border border-gray-200 bg-white p-2.5 dark:border-gray-700 dark:bg-gray-800/50">
            <p className="mb-1 text-[9px] font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400">Proposed Clause</p>
            <p className="text-xs leading-relaxed whitespace-pre-wrap text-gray-700 dark:text-gray-300">
              {sources.displayText}
            </p>
          </div>
        </div>
      ) : showProvenance ? (
        <ProvenanceTabs
          aiText={aiText}
          customizedText={customizedText}
          segments={segments}
          reviewedBy={reviewedBy}
          metrics={metrics}
        />
      ) : (
        <>
          <LegalRedlineBody segments={segments} />
          <div className="mt-2">
            <ChangeAttribution reviewedBy={reviewedBy} metrics={metrics} />
          </div>
        </>
      )}
      {!showProvenance && segments.length > 0 && !sourceMappingWeak && (
        <p className="mt-2 text-[10px] text-gray-400 dark:text-gray-500">
          <span className="text-red-600 dark:text-red-400">Strikethrough</span> = removed ·{" "}
          <span className="text-green-700 dark:text-green-400">Highlight</span> = added
        </p>
      )}
    </div>
  );
}

// ── Compact one-line summary ───────────────────────────────────

interface CompactSummaryProps {
  riskLevel?: string | null;
  actionLabel?: string | null;
  clauseType?: string | null;
  summaryImpact?: string | null;
  sectionTitle?: string | null;
  insertPosition?: string | null;
  confidence?: number;
}

export function CompactSummary({
  riskLevel,
  actionLabel,
  clauseType,
  summaryImpact,
  sectionTitle,
  insertPosition,
  confidence,
}: CompactSummaryProps) {
  const riskColor =
    riskLevel === "critical" ? "text-red-600 bg-red-50 dark:text-red-400 dark:bg-red-900/20" :
    riskLevel === "high" ? "text-orange-600 bg-orange-50 dark:text-orange-400 dark:bg-orange-900/20" :
    riskLevel === "medium" ? "text-yellow-600 bg-yellow-50 dark:text-yellow-400 dark:bg-yellow-900/20" :
    "text-blue-600 bg-blue-50 dark:text-blue-400 dark:bg-blue-900/20";

  const confLabel = confidence != null
    ? confidence >= 0.90 ? "Very High"
      : confidence >= 0.75 ? "High"
      : confidence >= 0.55 ? "Medium"
      : confidence >= 0.35 ? "Low"
      : "Uncertain"
    : "";

  const pos = insertPosition === "within_section" ? "Within" :
              insertPosition === "before_section" ? "Before" : "After";

  return (
    <div className="flex items-center gap-2 text-[11px] text-gray-600 dark:text-gray-400 truncate">
      <span className={`inline-flex items-center rounded px-1 py-0.5 text-[10px] font-bold uppercase tracking-wider ${riskColor}`}>
        {riskLevel || "MEDIUM"}
      </span>
      <span className="text-gray-300 dark:text-gray-600">|</span>
      {actionLabel && (
        <span className="font-semibold text-gray-700 dark:text-gray-300">{actionLabel}</span>
      )}
      <span className="text-gray-300 dark:text-gray-600">—</span>
      <span>{clauseType?.replace(/_/g, " ") || ""}</span>
      {summaryImpact && (
        <>
          <span className="text-gray-300 dark:text-gray-600">·</span>
          <span className="truncate">{summaryImpact}</span>
        </>
      )}
      {sectionTitle && (
        <>
          <span className="text-gray-300 dark:text-gray-600">·</span>
          <span className="text-gray-400 dark:text-gray-500">
            {pos} &ldquo;{sectionTitle}&rdquo;
          </span>
        </>
      )}
      {confLabel && (
        <>
          <span className="text-gray-300 dark:text-gray-600">·</span>
          <span className="text-gray-400 dark:text-gray-500">{confLabel}</span>
        </>
      )}
    </div>
  );
}

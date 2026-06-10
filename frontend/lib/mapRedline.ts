/**
 * Normalize review redline API records for UI display.
 * Backend may send original text under alternate fields (anchor, context, finding).
 */

import type { RedlineItem as ApiRedlineItem, LocatorResponse } from "@/services/api/client";
import {
  applyApiMappingValidation,
  reconcileRedlineAssociations,
  type LinkedFindingInput,
  type RedlineMappingDetails,
} from "@/lib/redlineIntegrity";

type ApiRecord = Record<string, unknown>;

export interface NormalizedRedlineTexts {
  original_text: string;
  proposed_text: string;
  /** True when there is no contract baseline — insertion / missing source */
  is_pure_insert: boolean;
  /** Surrounding contract language when baseline is absent */
  context_excerpt: string;
}

function pickString(...values: unknown[]): string {
  for (const v of values) {
    if (typeof v === "string" && v.trim()) return v.trim();
  }
  return "";
}

export function resolveRedlineTexts(
  raw: ApiRecord,
  findingClauseText?: string | null,
): NormalizedRedlineTexts {
  const locator = raw.locator as LocatorResponse | undefined;
  const operation = String(raw.operation ?? "").toLowerCase();

  const proposed = pickString(
    raw.proposed_text,
    raw.proposed_clause_text,
    raw.suggested_text,
    raw.reviewer_modified_text,
    raw.modified_text,
  );

  const explicitOriginal = pickString(
    raw.original_text,
    raw.original_clause_text,
    raw.source_text,
    raw.existing_text,
    raw.clause_text,
  );

  const anchor = pickString(raw.anchor_text, locator?.matched_text);
  const context = pickString(raw.context_excerpt, locator?.matched_text);

  const findingText = pickString(findingClauseText, raw.finding_clause_text);

  // Do not merge finding clause text here — integrity reconciliation runs after
  // category checks in mapApiRedlineRecord.
  const original =
    explicitOriginal ||
    (operation === "insert" ? "" : anchor || context) ||
    anchor ||
    context;

  const isPureInsert = operation === "insert" && !explicitOriginal && Boolean(proposed);

  return {
    original_text: original,
    proposed_text: proposed,
    is_pure_insert: isPureInsert,
    context_excerpt: context || anchor || findingText,
  };
}

export function mapApiRedlineRecord(
  raw: ApiRecord,
  linkedFinding?: LinkedFindingInput | string | null,
): {
  id: string;
  redline_id: string;
  clause_type: string;
  section: string;
  page: number;
  original_text: string;
  proposed_text: string;
  is_pure_insert: boolean;
  context_excerpt: string;
  status: string;
  severity: string;
  finding_id: string | null;
  finding_title: string | null;
  recommendation_id: string | null;
  author: string;
  created_at: string;
  review_notes?: string;
  modified_text?: string;
  operation?: string;
  mismatch_warning: string | null;
  source_category: string | null;
  proposed_category: string | null;
  mapping_valid: boolean;
  mapping_status: "valid" | "invalid_mapping";
  mapping_warning: string | null;
  redline_title: string | null;
  redline_category: string | null;
  finding_category: string | null;
  mapping_details: RedlineMappingDetails | null;
} {
  const locator = raw.locator as LocatorResponse | undefined;
  const findingClauseText =
    typeof linkedFinding === "string"
      ? linkedFinding
      : pickString(linkedFinding?.clause_text, linkedFinding?.description);
  const texts = resolveRedlineTexts(raw, findingClauseText);
  const redlineId = String(raw.redline_id ?? raw.id ?? "");

  const baseClauseType = String(
    raw.clause_type ?? locator?.legal_domain ?? locator?.risk_type ?? "clause",
  );
  const baseSection = String(
    raw.section ?? locator?.section_title ?? locator?.section_id ?? "—",
  );
  const findingInput: LinkedFindingInput | null =
    typeof linkedFinding === "object" && linkedFinding?.finding_id
      ? linkedFinding
      : null;

  const reconciled = reconcileRedlineAssociations(
    {
      clause_type: baseClauseType,
      section: baseSection,
      page: Number(raw.page ?? 0) || 0,
      original_text: texts.original_text,
      proposed_text: texts.proposed_text,
      context_excerpt: texts.context_excerpt,
      finding_id: raw.finding_id ? String(raw.finding_id) : null,
      finding_title: raw.finding_title
        ? String(raw.finding_title)
        : locator?.summary_title
          ? String(locator.summary_title)
          : findingInput?.title
            ? String(findingInput.title)
            : null,
      locator_section: locator?.section_title ? String(locator.section_title) : null,
      locator_legal_domain: locator?.legal_domain ? String(locator.legal_domain) : null,
    },
    findingInput,
  );

  const validated = applyApiMappingValidation(reconciled, {
    mapping_valid: raw.mapping_valid as boolean | undefined,
    mapping_status: raw.mapping_status ? String(raw.mapping_status) : undefined,
    mapping_warning: raw.mapping_warning ? String(raw.mapping_warning) : null,
    redline_title: raw.redline_title ? String(raw.redline_title) : null,
    redline_category: raw.redline_category ? String(raw.redline_category) : null,
    finding_title: raw.finding_title ? String(raw.finding_title) : null,
    finding_category: raw.finding_category ? String(raw.finding_category) : null,
    mapping_details: raw.mapping_details as RedlineMappingDetails | null | undefined,
  });

  const status =
    !validated.mapping_valid && String(raw.status ?? "proposed") === "proposed"
      ? "invalid_mapping"
      : String(raw.status ?? "proposed");

  return {
    id: redlineId,
    redline_id: redlineId,
    clause_type: validated.clause_type,
    section: validated.section,
    page: validated.page,
    original_text: validated.original_text,
    proposed_text: validated.proposed_text,
    is_pure_insert: texts.is_pure_insert,
    context_excerpt: texts.context_excerpt,
    status,
    severity: String(raw.severity ?? raw.risk_level ?? "medium"),
    finding_id: validated.finding_id,
    finding_title: validated.finding_title,
    recommendation_id: raw.recommendation_id ? String(raw.recommendation_id) : null,
    author: String(raw.author ?? raw.reviewed_by ?? "AI Engine"),
    created_at: String(raw.created_at ?? new Date().toISOString()),
    review_notes: raw.review_notes ? String(raw.review_notes) : undefined,
    modified_text: raw.reviewer_modified_text
      ? String(raw.reviewer_modified_text)
      : raw.modified_text
        ? String(raw.modified_text)
        : undefined,
    operation: raw.operation ? String(raw.operation) : undefined,
    mismatch_warning: validated.mismatch_warning,
    source_category: validated.source_category,
    proposed_category: validated.proposed_category,
    mapping_valid: validated.mapping_valid,
    mapping_status: validated.mapping_status,
    mapping_warning: validated.mapping_warning,
    redline_title: validated.redline_title,
    redline_category: validated.redline_category,
    finding_category: validated.finding_category,
    mapping_details: validated.mapping_details,
  };
}

export type MappedRedline = ReturnType<typeof mapApiRedlineRecord>;

/** Build a document-locate payload from a normalized redline + optional finding. */
export function buildLocatePayloadFromRedline(
  rl: Pick<
    MappedRedline,
    | "redline_id"
    | "finding_id"
    | "page"
    | "section"
    | "clause_type"
    | "original_text"
    | "context_excerpt"
    | "proposed_text"
  >,
  finding?: { page_numbers?: number[]; clause_text?: string; description?: string } | null,
): {
  page: number;
  findingId: string;
  clauseText?: string;
  sectionLabel?: string;
  clauseType?: string;
  redlineId: string;
  preserveReviewContext: true;
} {
  const clauseText = (
    rl.original_text ||
    rl.context_excerpt ||
    finding?.clause_text ||
    finding?.description ||
    ""
  ).trim();

  const inferPageFromClauseType = (clauseType: string): number | undefined => {
    const ct = clauseType.toLowerCase();
    if (ct.includes("indemn")) return 8;
    if (ct.includes("liabilit")) return 12;
    if (ct.includes("renewal") || ct.includes("term")) return 4;
    if (ct.includes("confidential")) return 3;
    if (ct.includes("sla") || ct.includes("service")) return 6;
    if (ct.includes("intellectual") || ct.includes("ip")) return 5;
    return undefined;
  };

  const page =
    rl.page > 0
      ? rl.page
      : finding?.page_numbers?.[0] && finding.page_numbers[0] > 0
        ? finding.page_numbers[0]
        : inferPageFromClauseType(rl.clause_type) ?? 1;

  const sectionLabel =
    rl.section && rl.section !== "—" ? rl.section : undefined;

  return {
    page,
    findingId: rl.finding_id || `redline-${rl.redline_id}`,
    clauseText: clauseText || undefined,
    sectionLabel,
    clauseType: rl.clause_type,
    redlineId: rl.redline_id,
    preserveReviewContext: true,
  };
}

/** Map typed API redline (review workspace / RedlineCard). */
export function mapApiRedlineItem(
  item: ApiRedlineItem,
  linkedFinding?: LinkedFindingInput | string | null,
): MappedRedline {
  return mapApiRedlineRecord(item as unknown as ApiRecord, linkedFinding);
}

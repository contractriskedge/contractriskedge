/**
 * Structural redline locator — resolves redlines to document positions.
 *
 * Replaces the old chunk-based fuzzy-locate approach with a structured system
 * that distinguishes between MODIFY_EXISTING, INSERT_NEW, DELETE, and WARNING_ONLY.
 *
 * UI behavior:
 * - MODIFY_EXISTING → highlight exact text span in the viewer
 * - INSERT_NEW → show insertion banner with section reference, never fake-locate
 * - DELETE → highlight text to remove
 * - WARNING_ONLY → show info icon, no document modification
 * - UNRESOLVED → show warning state with suggestion
 */

// ── Types ──────────────────────────────────────────────────────

export interface LocatorResponse {
  status: "resolved" | "partial" | "unresolved";
  anchor_type: "exact_text_span" | "fuzzy_text_span" | "semantic_clause_match"
    | "structural_insertion" | "none";
  confidence: number;
  section_id: string | null;
  section_title: string | null;
  insert_position: "after_section" | "before_section" | "within_section"
    | "append_document" | null;
  matched_text: string | null;
  chunk_id: string | null;
  reason: string | null;
  suggestion: string | null;
  display_numbering: boolean;
  legal_domain: string | null;
  risk_type: string | null;
  recommendation_type: string | null;
  clause_operation_type: string | null;
  rationale_bullets: string[];
  related_risks: string[];
  impact_accepted: string | null;
  impact_rejected: string | null;
  summary_title: string | null;
  summary_impact: string | null;
  action_label: string | null;
  group_key: string | null;
}

export interface UploadChunk {
  chunk_id: string;
  chunk_index: number;
  text: string;
  page_numbers: number[];
  section_heading?: string | null;
  clause_type?: string | null;
}

export interface LocateResult {
  /** The type of locate action to display */
  action: "modify_existing" | "insert_new" | "delete" | "warning_only" | "unresolved";
  /** Chunk to highlight (for modify_existing / delete) */
  chunk_id: string | null;
  /** Text to highlight in the viewer */
  highlightText: string | null;
  /** Needle for indexOf matching */
  needle: string | null;
  /** Section reference (for insert_new) */
  section_id: string | null;
  section_title: string | null;
  insert_position: string | null;
  /** User-facing messages */
  notice: string | null;
  suggestion: string | null;
  /** Raw locator data from API */
  locator: LocatorResponse;
}

// ── Locate function ────────────────────────────────────────────

/**
 * Locate a redline in the document using the structured locator result.
 */
export function locateRedline(
  redline: { locator?: LocatorResponse | null },
  chunks: UploadChunk[],
): LocateResult {
  const locator = redline.locator;

  if (!locator) {
    return {
      action: "unresolved",
      chunk_id: null,
      highlightText: null,
      needle: null,
      section_id: null,
      section_title: null,
      insert_position: null,
      notice: "This recommendation could not be located in the document.",
      suggestion: null,
      locator: {
        status: "unresolved",
        anchor_type: "none",
        confidence: 0,
        section_id: null,
        section_title: null,
        insert_position: null,
        matched_text: null,
        chunk_id: null,
        reason: null,
        suggestion: null,
        display_numbering: false,
        legal_domain: null,
        risk_type: null,
        recommendation_type: null,
        clause_operation_type: null,
        rationale_bullets: [],
        related_risks: [],
        impact_accepted: null,
        impact_rejected: null,
        summary_title: null,
        summary_impact: null,
        action_label: null,
        group_key: null,
      },
    };
  }

  // ── WARNING_ONLY ──────────────────────────────────────────
  if (locator.anchor_type === "none" && locator.status === "resolved") {
    return {
      action: "warning_only",
      chunk_id: null,
      highlightText: null,
      needle: null,
      section_id: null,
      section_title: null,
      insert_position: null,
      notice: locator.reason || "Informational recommendation.",
      suggestion: null,
      locator,
    };
  }

  // ── MODIFY_EXISTING ───────────────────────────────────────
  if (locator.anchor_type === "exact_text_span" || locator.anchor_type === "fuzzy_text_span") {
    if (locator.matched_text) {
      const hit = searchChunksForText(chunks, locator.matched_text, locator.chunk_id);
      if (hit) {
        return {
          action: "modify_existing",
          chunk_id: hit.chunk_id,
          highlightText: hit.phrase,
          needle: hit.needle,
          section_id: locator.section_id,
          section_title: locator.section_title,
          insert_position: null,
          notice: null,
          suggestion: null,
          locator,
        };
      }
    }
  }

  // ── SEMANTIC / STRUCTURAL (INSERT_NEW or locate section) ──
  if (locator.anchor_type === "semantic_clause_match" || locator.anchor_type === "structural_insertion") {
    const sectionResult = findSectionInChunks(locator, chunks);
    if (sectionResult) {
      return {
        ...sectionResult,
        action: "insert_new",
        insert_position: locator.insert_position,
        notice: locator.reason || buildInsertNotice(locator),
        suggestion: locator.suggestion,
        locator,
      };
    }

    return {
      action: "insert_new",
      chunk_id: null,
      highlightText: null,
      needle: null,
      section_id: locator.section_id,
      section_title: locator.section_title,
      insert_position: locator.insert_position,
      notice: locator.reason || buildInsertNotice(locator),
      suggestion: locator.suggestion,
      locator,
    };
  }

  // ── UNRESOLVED ────────────────────────────────────────────
  return {
    action: "unresolved",
    chunk_id: null,
    highlightText: null,
    needle: null,
    section_id: locator.section_id,
    section_title: locator.section_title,
    insert_position: null,
    notice: locator.reason || "Could not locate this recommendation in the document.",
    suggestion: locator.suggestion,
    locator,
  };
}

// ── Helpers ────────────────────────────────────────────────────

function buildInsertNotice(locator: LocatorResponse): string {
  const pos = locator.insert_position?.replace(/_/g, " ") || "";
  const section = locator.section_title ? `"${locator.section_title}"` : "";
  if (pos && section) {
    return `Insert new clause ${pos} ${section}.`;
  }
  if (section) {
    return `Insert new clause within ${section}.`;
  }
  return "Insert new clause.";
}

function findSectionInChunks(
  locator: LocatorResponse,
  chunks: UploadChunk[],
): LocateResult | null {
  const sectionId = locator.section_id;
  if (!sectionId) return null;

  const headingPattern = new RegExp(
    `(?:^|\\s)${sectionId.replace(/\./g, "\\.")}(?:\\.|\\s)`,
    "i"
  );

  for (const chunk of chunks) {
    const text = chunk.text || "";
    if (!text) continue;

    const match = text.match(headingPattern);
    if (match) {
      const start = Math.max(0, match.index! - 10);
      const end = Math.min(text.length, match.index! + 80);
      const snippet = text.slice(start, end).trim();

      return {
        action: "modify_existing",
        chunk_id: chunk.chunk_id,
        highlightText: snippet,
        needle: snippet.slice(0, 60),
        section_id: sectionId,
        section_title: locator.section_title,
        insert_position: locator.insert_position,
        notice: null,
        suggestion: null,
        locator,
      };
    }
  }

  return null;
}

function searchChunksForText(
  chunks: UploadChunk[],
  text: string,
  preferredChunkId?: string | null,
): { chunk_id: string; phrase: string; needle: string } | null {
  const trimmed = text.trim();
  if (trimmed.length < 4) return null;

  // Try preferred chunk first
  if (preferredChunkId) {
    const chunk = chunks.find((c) => c.chunk_id === preferredChunkId);
    if (chunk) {
      const hit = findTextInChunk(chunk.text, trimmed);
      if (hit) {
        return { chunk_id: chunk.chunk_id, ...hit };
      }
    }
  }

  // Search all chunks
  for (const chunk of chunks) {
    const hit = findTextInChunk(chunk.text || "", trimmed);
    if (hit) {
      return { chunk_id: chunk.chunk_id, ...hit };
    }
  }

  return null;
}

export function findTextInChunk(
  chunkText: string,
  needle: string,
): { phrase: string; needle: string } | null {
  if (!chunkText || !needle) return null;

  const trimmed = needle.trim();
  if (trimmed.length < 4) return null;

  // Exact match
  const idx = chunkText.toLowerCase().indexOf(trimmed.toLowerCase());
  if (idx >= 0) {
    const end = Math.min(idx + trimmed.length, chunkText.length);
    return {
      phrase: chunkText.slice(idx, end),
      needle: trimmed,
    };
  }

  // Whitespace-collapsed match
  const collapseWs = (s: string) => s.replace(/\s+/g, " ").trim();
  const collapsedHay = collapseWs(chunkText).toLowerCase();
  const collapsedNeedle = collapseWs(trimmed).toLowerCase();
  const cIdx = collapsedHay.indexOf(collapsedNeedle);
  if (cIdx >= 0) {
    return { phrase: trimmed, needle: trimmed };
  }

  // Progressive prefix match
  for (let len = Math.min(trimmed.length, 200); len >= 8; len -= 4) {
    const slice = trimmed.slice(0, len);
    const sIdx = chunkText.toLowerCase().indexOf(slice.toLowerCase());
    if (sIdx >= 0) {
      return {
        phrase: chunkText.slice(sIdx, sIdx + slice.length),
        needle: slice,
      };
    }
  }

  return null;
}

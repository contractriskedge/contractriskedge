/**
 * Resolve which contract chunk and phrase to highlight when locating a redline.
 */

import type { RedlineItem } from "@/services/api/client";

export interface UploadChunk {
  chunk_id: string;
  chunk_index: number;
  text: string;
  page_numbers: number[];
  section_heading?: string | null;
  clause_type?: string | null;
}

export interface LocateResult {
  chunk_id: string;
  highlightText: string;
  /** Exact substring used for indexOf in the viewer */
  needle: string;
  /** Shown when we highlight a nearby section because the target § is missing from extracted text */
  notice?: string;
}

interface ParsedSection {
  major: number;
  heading: string;
  chunk_id: string;
}

const SECTION_MARKER_RE = /(?:^|[\s(§]|Section\s+|Article\s+|ART(?:ICLE)?\s+)(\d{1,2}(?:\.\d+)?|\d{1,2}\.)[\s:\-]+/g;
const NEXT_SECTION_MARKER_RE = /\s(?:\d{1,2}(?:\.\d+)?|\d{1,2}\.)\s+/;

const MIN_GENERAL = 8;
const MIN_ANCHOR = 4;
const MIN_SECTION = 5; // e.g. "2. Term", "1. Services"

/** Single-word / generic needles that match the wrong place in MSA text */
const AMBIGUOUS_NEEDLES = new Set([
  "services",
  "termination",
  "agreement",
  "liability",
  "confidential",
]);

function normalize(s: string): string {
  return s.replace(/\s+/g, " ").trim().toLowerCase();
}

function isAmbiguous(needle: string, isAnchor: boolean): boolean {
  if (isAnchor) return false;
  const n = normalize(needle);
  if (n.length >= 20) return false;
  if (/^\d+\./.test(needle.trim())) return false;
  return AMBIGUOUS_NEEDLES.has(n);
}

type Candidate = { text: string; priority: number; isAnchor: boolean };

function collapseWs(text: string): string {
  return text.replace(/\s+/g, " ").trim();
}

function escapeRegExp(text: string): string {
  return text.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function isWeakAnchor(needle: string): boolean {
  const n = normalize(needle);
  if (!n || n.length >= 20 || /^\d+\./.test(n)) return false;
  return AMBIGUOUS_NEEDLES.has(n) || n.split(/\s+/).length === 1;
}

function headingNeedlesForAnchor(
  anchorText: string,
  chunks: UploadChunk[],
  linkedIds: string[],
): Candidate[] {
  const anchor = collapseWs(anchorText);
  if (!anchor || /^\d+\./.test(anchor)) return [];

  const scopedChunks = linkedIds.length
    ? chunks.filter((c) => linkedIds.includes(c.chunk_id))
    : chunks;
  const headingPattern = new RegExp(
    `(?:^|\\s)(\\d+(?:\\.\\d+)?\\.\\s+${escapeRegExp(anchor)}\\b)`,
    "i",
  );

  const out: Candidate[] = [];
  const seen = new Set<string>();
  for (const chunk of scopedChunks) {
    const match = collapseWs(chunk.text || "").match(headingPattern);
    if (!match?.[1]) continue;
    const text = match[1].trim();
    const key = normalize(text);
    if (!seen.has(key)) {
      seen.add(key);
      out.push({ text, priority: 0, isAnchor: true });
    }
  }
  return out;
}

// Roman numeral mapping (I=1, II=2, ..., XV=15)
const ROMAN_TO_INT: Record<string, number> = {
  i: 1, ii: 2, iii: 3, iv: 4, v: 5,
  vi: 6, vii: 7, viii: 8, ix: 9, x: 10,
  xi: 11, xii: 12, xiii: 13, xiv: 14, xv: 15,
};

function targetMajorSection(proposedText: string): number | null {
  const trimmed = proposedText.trim();
  // Arabic numerals: "4.", "4.5", "§4.", "§4.5"
  const arabicMatch = trimmed.match(/^(?:§)?(\d+)(?:\.\d+)?[.\s]/);
  if (arabicMatch) return parseInt(arabicMatch[1], 10);
  // Roman numerals: "IV.", "IV.5"
  const romanMatch = trimmed.match(/^([IVXLCDM]+)(?:\.\d+)?[.\s]/i);
  if (romanMatch) {
    const roman = romanMatch[1].toLowerCase();
    return ROMAN_TO_INT[roman] ?? null;
  }
  return null;
}

/** Extract the full dotted section number from proposed text (e.g. "9.1.1" from "9.1.1 Notice..."). */
function targetFullSection(proposedText: string): string | null {
  const trimmed = proposedText.trim();
  const m = trimmed.match(/^(?:§)?(\d+(?:\.\d+)*)[.\s]/);
  return m ? m[1] : null;
}

function compactSectionHeading(sectionNumber: string, followingText: string): string | null {
  const cleaned = collapseWs(followingText)
    .replace(/^[):;-]\s*/, "")
    .trim();
  if (!cleaned) return null;

  const nextMarkerIndex = cleaned.search(NEXT_SECTION_MARKER_RE);
  const sectionLead = nextMarkerIndex >= 0 ? cleaned.slice(0, nextMarkerIndex) : cleaned;
  const sentence = (sectionLead.split(/[.;:]/)[0] || sectionLead)
    .replace(/\s+State\s+of\b.*$/i, "")
    .trim();
  const words = sentence
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 5);
  if (!words.length) return null;

  const titleWords: string[] = [];
  for (const word of words) {
    const normalized = word.replace(/^[("']+|[)"',]+$/g, "");
    if (!normalized) continue;
    if (titleWords.length > 0 && /^[a-z]/.test(normalized)) break;
    titleWords.push(normalized);
  }

  const headingWords = titleWords.length ? titleWords : words.slice(0, 2);
  const heading = `${sectionNumber}. ${headingWords.join(" ")}`.trim();
  return heading.length >= MIN_SECTION ? heading : null;
}

function parseSectionsInChunks(chunks: UploadChunk[]): ParsedSection[] {
  const seen = new Set<string>();
  const sections: ParsedSection[] = [];

  for (const chunk of chunks) {
    const text = chunk.text || "";
    if (!text) continue;
    SECTION_MARKER_RE.lastIndex = 0;
    let m: RegExpExecArray | null;
    while ((m = SECTION_MARKER_RE.exec(text)) !== null) {
      const sectionNumber = m[1].replace(/\.$/, "");
      const major = parseInt(sectionNumber.split(".")[0], 10);
      const next = text.slice(SECTION_MARKER_RE.lastIndex);
      const heading = compactSectionHeading(sectionNumber, next);
      if (!heading) continue;
      const key = `${major}:${heading.toLowerCase()}`;
      if (seen.has(key)) continue;
      seen.add(key);
      sections.push({ major, heading, chunk_id: chunk.chunk_id });
    }
  }

  return sections.sort((a, b) => a.major - b.major);
}

/** When proposed §N is missing from extraction, anchor to nearest existing section. */
function nearestSectionCandidates(
  proposedText: string,
  chunks: UploadChunk[],
): { candidates: Candidate[]; notice?: string } {
  const target = targetMajorSection(proposedText);
  if (!target || target <= 1) return { candidates: [] };

  const sections = parseSectionsInChunks(chunks);
  if (!sections.length) return { candidates: [] };

  // Deduplicate sections by major number (keep only first occurrence of each major)
  const seenMajors = new Set<number>();
  const uniqueSections = sections.filter(s => {
    if (seenMajors.has(s.major)) return false;
    seenMajors.add(s.major);
    return true;
  });

  const majors = uniqueSections.map((s) => s.major);
  const hasTarget = majors.includes(target);

  // For subsections (e.g. "9.1.1"), check if the FULL section number exists in any chunk.
  // If the parent section exists but the exact subsection doesn't, anchor to the parent.
  const fullSection = targetFullSection(proposedText);
  if (hasTarget && fullSection && fullSection.includes(".")) {
    const fullPattern = new RegExp(`(?:^|[\\s(])${fullSection.replace(/\./g, "\\.")}(?:[.\\s:\\-]|$)`, "i");
    const fullSectionExists = chunks.some(c => fullPattern.test(c.text || ""));
    if (fullSectionExists) {
      // Exact subsection exists — no gap to fill
      return { candidates: [] };
    }
    // Subsection doesn't exist but parent section does — anchor to parent section
    const parentSection = uniqueSections.find(s => s.major === target);
    if (parentSection) {
      return {
        candidates: [{ text: parentSection.heading, priority: -2, isAnchor: true }],
        notice: `Subsection ${fullSection} is not in the extracted text. Showing §${target} as the nearest insertion point (within this section).`,
      };
    }
  }

  // Section completely missing — find nearest
  if (hasTarget) return { candidates: [] };

  const before = [...uniqueSections].reverse().find((s) => s.major < target);
  const after = uniqueSections.find((s) => s.major > target);

  // Prefer the NEAREST section (smallest distance), not always "after".
  const beforeDist = before ? target - before.major : Infinity;
  const afterDist = after ? after.major - target : Infinity;

  const candidates: Candidate[] = [];
  let notice: string | undefined;

  if (beforeDist <= afterDist && before) {
    candidates.push({ text: before.heading, priority: -2, isAnchor: true });
    notice =
      `Section ${target} is not in the extracted text. Showing §${before.major} as the nearest insertion point (after this section).`;
  } else if (after) {
    candidates.push({ text: after.heading, priority: -2, isAnchor: true });
    notice =
      `Section ${target} is not in the extracted text. Showing §${after.major} as the nearest insertion point (before this section).`;
  }

  return { candidates, notice };
}

/** Lines from proposed/modified text that already appear in the contract (modification target). */
function proposedNeedlesInDocument(
  proposed: string,
  chunks: UploadChunk[],
): Candidate[] {
  const corpus = chunks.map((c) => c.text || "").join("\n").toLowerCase();
  if (!corpus) return [];

  const lines = proposed
    .split(/\n+/)
    .map((l) => l.replace(/\s+/g, " ").trim())
    .filter((l) => l.length >= MIN_SECTION);

  const out: Candidate[] = [];
  for (const line of lines) {
    const probe = line.slice(0, Math.min(line.length, 100));
    if (corpus.includes(probe.toLowerCase())) {
      out.push({ text: probe, priority: 15, isAnchor: false });
    }
  }
  const heading = lines.find((l) => /^\d+\./.test(l));
  if (heading && !out.some((c) => c.text === heading)) {
    const probe = heading.slice(0, 80);
    if (corpus.includes(probe.toLowerCase())) {
      out.push({ text: probe, priority: 12, isAnchor: false });
    }
  }
  return out;
}

export function buildLocateCandidates(
  redline: RedlineItem,
  chunks: UploadChunk[],
): Candidate[] {
  const op = redline.operation || "modification";
  const isInsert = op === "insert";
  const proposed =
    (redline.reviewer_modified_text || redline.proposed_text || "").trim();
  const list: Candidate[] = [];
  const linkedIds = redline.chunk_ids?.filter(Boolean) ?? [];

  if (redline.anchor_text?.trim()) {
    // Inserts: anchor is the insertion point. Modifications: prefer the clause span in the doc.
    const anchor = redline.anchor_text.trim();
    list.push(...headingNeedlesForAnchor(anchor, chunks, linkedIds));
    const anchorPriority = isInsert ? (isWeakAnchor(anchor) ? 28 : 0) : 14;
    list.push({ text: anchor, priority: anchorPriority, isAnchor: true });
  }

  if (isInsert && redline.context_excerpt?.trim()) {
    list.push({
      text: redline.context_excerpt.trim().slice(0, 180),
      priority: 2,
      isAnchor: true,
    });
  }

  if (!isInsert && redline.original_text?.trim()) {
    list.push({ text: redline.original_text.trim(), priority: 4, isAnchor: false });
  }

  // Fallback: if no anchor and no original_text, use a snippet of proposed text
  // so the Locate function has something to search for.
  if (!redline.anchor_text?.trim() && !redline.original_text?.trim() && proposed) {
    const snippet = proposed.slice(0, 200).trim();
    if (snippet.length >= MIN_GENERAL) {
      list.push({ text: snippet, priority: 10, isAnchor: false });
    }
  }

  if (proposed) {
    const inDoc = proposedNeedlesInDocument(proposed, chunks).map((c) => ({
      ...c,
      priority: isInsert ? c.priority : Math.min(c.priority, 6),
    }));
    list.push(...inDoc);
    const firstLine = proposed.split("\n")[0].trim();
    if (firstLine.length >= MIN_SECTION && /^\d+\./.test(firstLine)) {
      list.push({
        text: firstLine.slice(0, 80),
        priority: isInsert ? 18 : 8,
        isAnchor: false,
      });
    }
  }

  const seen = new Set<string>();
  const filtered = list
    .filter((c) => {
      const key = normalize(c.text);
      if (!key || seen.has(key) || isAmbiguous(c.text, c.isAnchor)) return false;
      seen.add(key);
      return true;
    })
    .sort((a, b) => a.priority - b.priority);

  return filtered;
}

function indexOfFlexible(haystack: string, needle: string): number {
  const idx = haystack.toLowerCase().indexOf(needle.toLowerCase());
  if (idx >= 0) return idx;
  const collapsedHay = collapseWs(haystack).toLowerCase();
  const collapsedNeedle = collapseWs(needle).toLowerCase();
  if (!collapsedNeedle) return -1;
  const cIdx = collapsedHay.indexOf(collapsedNeedle);
  if (cIdx < 0) return -1;
  // Map collapsed index back to approximate position in original text
  let o = 0;
  let c = 0;
  while (o < haystack.length && c < cIdx) {
    if (/\s/.test(haystack[o]) && (c === 0 || /\s/.test(haystack[o - 1] || ""))) {
      while (o < haystack.length && /\s/.test(haystack[o])) o++;
      if (c > 0) c++;
      continue;
    }
    o++;
    c++;
  }
  return o;
}

export function findPhraseInChunk(
  chunkText: string,
  needle: string,
  isAnchor: boolean,
): { index: number; phrase: string; needle: string } | null {
  const trimmed = needle.trim();
  if (!trimmed) return null;

  const isSection = /^\d+\./.test(trimmed);
  const minLen = isAnchor ? MIN_ANCHOR : isSection ? MIN_SECTION : MIN_GENERAL;
  if (trimmed.length < minLen) return null;

  // 1) Exact / flexible match
  let idx = indexOfFlexible(chunkText, trimmed);
  if (idx >= 0) {
    const end = Math.min(idx + trimmed.length, chunkText.length);
    return {
      index: idx,
      phrase: chunkText.slice(idx, end),
      needle: trimmed,
    };
  }

  // 2) Progressive prefix match (longer anchors / clause spans)
  const maxLen = Math.min(trimmed.length, 200);
  for (let len = maxLen; len >= minLen; len -= 4) {
    const slice = trimmed.slice(0, len);
    idx = indexOfFlexible(chunkText, slice);
    if (idx >= 0) {
      return {
        index: idx,
        phrase: chunkText.slice(idx, idx + slice.length),
        needle: slice,
      };
    }
  }

  return null;
}

function searchChunks(
  chunks: UploadChunk[],
  candidates: Candidate[],
  onlyChunkIds?: string[],
): LocateResult | null {
  const ordered =
    onlyChunkIds?.length
      ? [
          ...chunks.filter((c) => onlyChunkIds.includes(c.chunk_id)),
          ...chunks.filter((c) => !onlyChunkIds.includes(c.chunk_id)),
        ]
      : chunks;

  for (const { text, isAnchor } of candidates) {
    for (const chunk of ordered) {
      if (!chunk.text) continue;
      const hit = findPhraseInChunk(chunk.text, text, isAnchor);
      if (hit) {
        return {
          chunk_id: chunk.chunk_id,
          highlightText: hit.phrase,
          needle: hit.needle,
        };
      }
    }
  }
  return null;
}

export function locateRedlineInChunks(
  chunks: UploadChunk[],
  redline: RedlineItem,
): LocateResult | null {
  if (!chunks.length) return null;

  const proposed = (redline.reviewer_modified_text || redline.proposed_text || "").trim();
  const isInsert = (redline.operation || "modification") === "insert";
  const gap = isInsert && proposed ? nearestSectionCandidates(proposed, chunks) : { candidates: [] };

  const candidates = [
    ...gap.candidates,
    ...buildLocateCandidates(redline, chunks),
  ];
  const linkedIds = redline.chunk_ids?.filter(Boolean) ?? [];

  let located: LocateResult | null = null;
  if (linkedIds.length) {
    located = searchChunks(chunks, candidates, linkedIds);
  }
  if (!located) {
    located = searchChunks(chunks, candidates);
  }
  if (located && gap.notice) {
    located = { ...located, notice: gap.notice };
  }
  return located;
}

export type SemanticDiffTag = "equal" | "insert" | "delete";

export interface SemanticDiffSegment {
  tag: SemanticDiffTag;
  text: string;
}

export interface DiffChangeMetrics {
  additions: number;
  deletions: number;
}

/** Enterprise legal redline styles — highlight only changed spans. */
export const LEGAL_DIFF_STYLES = {
  insert: "rounded-sm px-0.5 text-inherit [background:rgba(34,197,94,0.18)]",
  delete:
    "rounded-sm px-0.5 text-red-700 line-through dark:text-red-300 [background:rgba(239,68,68,0.15)]",
  equal: "",
} as const;

function countWords(text: string): number {
  const tokens = text.match(/[A-Za-z0-9]+(?:['-][A-Za-z0-9]+)*/g);
  return tokens?.length ?? 0;
}

export function computeDiffMetrics(segments: SemanticDiffSegment[]): DiffChangeMetrics {
  let additions = 0;
  let deletions = 0;
  for (const segment of segments) {
    if (segment.tag === "insert") additions += countWords(segment.text);
    if (segment.tag === "delete") deletions += countWords(segment.text);
  }
  return { additions, deletions };
}

interface Edit<T> {
  tag: SemanticDiffTag;
  value: T;
}

const SECTION_HEADING_RE = /^(?:§\s*)?(?:\d+(?:\.\d+)*\.?\s+)?[A-Z][A-Za-z0-9,&()/-]*(?:\s+[A-Z][A-Za-z0-9,&()/-]*){0,8}$/;

function normalizeForSentenceMatch(text: string): string {
  return text.replace(/\s+/g, " ").trim().toLowerCase();
}

function tokenizeSentences(text: string): string[] {
  if (!text) return [];

  const chunks: string[] = [];
  const lines = text.match(/[^\n]*(?:\n|$)/g) ?? [];

  for (const rawLine of lines) {
    if (!rawLine) continue;
    const trailingNewline = rawLine.endsWith("\n") ? "\n" : "";
    const line = trailingNewline ? rawLine.slice(0, -1) : rawLine;
    const trimmed = line.trim();

    if (!trimmed) {
      chunks.push(rawLine);
      continue;
    }

    if (SECTION_HEADING_RE.test(trimmed) && !/[.!?:;]$/.test(trimmed)) {
      chunks.push(rawLine);
      continue;
    }

    let start = 0;
    for (let i = 0; i < line.length; i++) {
      const char = line[i];
      const next = line[i + 1] ?? "";
      if (/[.!?;]/.test(char) && (!next || /\s/.test(next))) {
        chunks.push(line.slice(start, i + 1));
        start = i + 1;
      }
    }

    if (start < line.length) {
      chunks.push(line.slice(start));
    }

    if (trailingNewline) {
      chunks[chunks.length - 1] = `${chunks[chunks.length - 1] ?? ""}\n`;
    }
  }

  return chunks.filter((chunk) => chunk.length > 0);
}

function tokenizeText(text: string): string[] {
  return text.match(/\s+|[A-Za-z0-9]+(?:['-][A-Za-z0-9]+)*|[^\sA-Za-z0-9]/g) ?? [];
}

function getV(map: Map<number, number>, key: number): number {
  return map.get(key) ?? Number.NEGATIVE_INFINITY;
}

function myersDiff<T>(before: T[], after: T[], equals: (a: T, b: T) => boolean): Edit<T>[] {
  const n = before.length;
  const m = after.length;

  if (n === 0) return after.map((value) => ({ tag: "insert", value }));
  if (m === 0) return before.map((value) => ({ tag: "delete", value }));

  const trace: Map<number, number>[] = [];
  let v = new Map<number, number>([[1, 0]]);

  for (let d = 0; d <= n + m; d++) {
    trace.push(new Map(v));
    const nextV = new Map(v);

    for (let k = -d; k <= d; k += 2) {
      const shouldMoveDown = k === -d || (k !== d && getV(v, k - 1) < getV(v, k + 1));
      let x = shouldMoveDown ? getV(v, k + 1) : getV(v, k - 1) + 1;
      let y = x - k;

      while (x < n && y < m && equals(before[x], after[y])) {
        x++;
        y++;
      }

      nextV.set(k, x);

      if (x >= n && y >= m) {
        return backtrack(before, after, trace, x, y);
      }
    }

    v = nextV;
  }

  return [];
}

function backtrack<T>(before: T[], after: T[], trace: Map<number, number>[], endX: number, endY: number): Edit<T>[] {
  const edits: Edit<T>[] = [];
  let x = endX;
  let y = endY;

  for (let d = trace.length - 1; d >= 0; d--) {
    const v = trace[d];
    const k = x - y;
    const moveDown = k === -d || (k !== d && getV(v, k - 1) < getV(v, k + 1));
    const prevK = moveDown ? k + 1 : k - 1;
    const prevX = getV(v, prevK);
    const prevY = prevX - prevK;

    while (x > prevX && y > prevY) {
      edits.push({ tag: "equal", value: before[x - 1] });
      x--;
      y--;
    }

    if (d === 0) break;

    if (moveDown) {
      edits.push({ tag: "insert", value: after[y - 1] });
      y--;
    } else {
      edits.push({ tag: "delete", value: before[x - 1] });
      x--;
    }
  }

  return edits.reverse();
}

function coalesceSegments(segments: SemanticDiffSegment[]): SemanticDiffSegment[] {
  const merged: SemanticDiffSegment[] = [];

  for (const segment of segments) {
    if (!segment.text) continue;
    const previous = merged[merged.length - 1];
    if (previous?.tag === segment.tag) {
      previous.text += segment.text;
    } else {
      merged.push({ ...segment });
    }
  }

  return merged;
}

/**
 * Filter out trivial edits — punctuation-only changes, whitespace-only changes,
 * and single-character noise. These add visual noise without semantic value.
 */
function isTrivialEdit(text: string): boolean {
  if (!text) return true;
  const stripped = text.replace(/\s+/g, "");
  if (!stripped) return true;
  // Punctuation-only (no letters or digits)
  if (!/[A-Za-z0-9]/.test(stripped)) return true;
  // Single punctuation character
  if (stripped.length <= 1 && /[^\w]/.test(stripped)) return true;
  return false;
}

/**
 * Collapse insert+delete pairs where both sides are trivial edits.
 * For example, if a period becomes a semicolon, treat as unchanged.
 */
function collapseTrivialEdits(segments: SemanticDiffSegment[]): SemanticDiffSegment[] {
  const result: SemanticDiffSegment[] = [];
  let i = 0;

  while (i < segments.length) {
    const current = segments[i];

    // Check for insert+delete pair (in either order) where both are trivial
    if (current.tag === "insert" || current.tag === "delete") {
      const next = segments[i + 1];
      if (next && next.tag !== "equal") {
        const insertSeg = current.tag === "insert" ? current : next;
        const deleteSeg = current.tag === "delete" ? current : next;
        if (isTrivialEdit(insertSeg.text) && isTrivialEdit(deleteSeg.text)) {
          // Both trivial — collapse into equal (treat as unchanged)
          result.push({ tag: "equal", text: deleteSeg.text });
          i += 2;
          continue;
        }
      }
    }

    // Filter out standalone trivial edits
    if ((current.tag === "insert" || current.tag === "delete") && isTrivialEdit(current.text)) {
      // Replace trivial delete with equal (keep the text but unhighlight)
      if (current.tag === "delete") {
        result.push({ tag: "equal", text: current.text });
      }
      // Trivial insertions are just dropped
      i++;
      continue;
    }

    result.push(current);
    i++;
  }

  return result;
}

function tokenDiff(before: string, after: string): SemanticDiffSegment[] {
  // Use phrase-level tokenization for more meaningful diffs
  const beforeTokens = tokenizePhrases(before);
  const afterTokens = tokenizePhrases(after);
  const edits = myersDiff(beforeTokens, afterTokens, (a, b) => a === b);

  let segments = coalesceSegments(edits.map((edit) => ({ tag: edit.tag, text: edit.value })));
  segments = collapseTrivialEdits(segments);
  return segments;
}

function similarity(a: string, b: string): number {
  const aTokens = new Set(tokenizeText(normalizeForSentenceMatch(a)).filter((token) => /\S/.test(token)));
  const bTokens = new Set(tokenizeText(normalizeForSentenceMatch(b)).filter((token) => /\S/.test(token)));
  if (!aTokens.size && !bTokens.size) return 1;

  let overlap = 0;
  for (const token of aTokens) {
    if (bTokens.has(token)) overlap++;
  }

  return overlap / Math.max(aTokens.size, bTokens.size);
}

/**
 * Merge adjacent non-equal segments into phrase-level changes.
 * This prevents "modify," "commercially" "exploit" from being individual
 * highlighted spans and instead groups them into meaningful phrases like
 * "modify or commercially exploit Customer Data".
 *
 * The algorithm:
 * 1. Scan for runs of delete/insert pairs (modifications)
 * 2. Merge adjacent delete segments into one phrase
 * 3. Merge adjacent insert segments into one phrase
 * 4. Absorb short (≤3 word) equal segments between delete/insert runs
 *    to capture grammatical phrases like "or", "and", "the"
 */
function mergeAdjacentTokens(segments: SemanticDiffSegment[]): SemanticDiffSegment[] {
  const result: SemanticDiffSegment[] = [];
  let i = 0;

  while (i < segments.length) {
    const current = segments[i];

    // Check for a run of non-equal segments (delete/insert pairs)
    if (current.tag !== "equal") {
      // Collect the entire run of non-equal segments
      const run: SemanticDiffSegment[] = [];
      while (i < segments.length && segments[i].tag !== "equal") {
        run.push(segments[i]);
        i++;
      }

      if (run.length === 0) continue;

      // Merge all deletes into one, all inserts into one
      const deleteText = run.filter(s => s.tag === "delete").map(s => s.text).join("");
      const insertText = run.filter(s => s.tag === "insert").map(s => s.text).join("");

      if (deleteText) {
        result.push({ tag: "delete", text: deleteText });
      }
      if (insertText) {
        result.push({ tag: "insert", text: insertText });
      }
      continue;
    }

    // For equal segments, check if the next non-equal run is short enough to absorb
    const nextNonEqual = segments.slice(i + 1).findIndex(s => s.tag !== "equal");
    if (nextNonEqual > 0) {
      const gapEnd = i + 1 + nextNonEqual;
      const gapSegments = segments.slice(i + 1, gapEnd);
      const gapWords = gapSegments.reduce((sum, s) => sum + wordCount(s.text), 0);

      // If the gap is ≤ 3 words, absorb it into the surrounding equal text
      if (gapWords <= 3 && gapWords > 0) {
        const afterRun = segments.slice(gapEnd);
        const afterNonEqualEnd = afterRun.findIndex(s => s.tag === "equal");
        const nonEqualRun = afterRun.slice(0, afterNonEqualEnd > 0 ? afterNonEqualEnd : undefined);

        if (nonEqualRun.length > 0) {
          // Absorb the gap into current equal text
          const gapText = gapSegments.map(s => s.text).join("");
          result.push({ tag: "equal", text: current.text + gapText });
          i = gapEnd;
          continue;
        }
      }
    }

    result.push(current);
    i++;
  }

  return result;
}

function wordCount(text: string): number {
  const words = text.match(/[A-Za-z0-9]+(?:['-][A-Za-z0-9]+)*/g);
  return words?.length ?? 0;
}

function isSingleWord(text: string): boolean {
  return wordCount(text) <= 2 && text.trim().length < 20;
}

/**
 * Tokenize text into phrase-level chunks instead of raw tokens.
 * Groups words into meaningful phrases (3-5 words) to reduce diff noise.
 * This is the key improvement for lawyer-friendly diffs.
 */
function tokenizePhrases(text: string): string[] {
  const tokens = tokenizeText(text);
  const phrases: string[] = [];
  let i = 0;

  while (i < tokens.length) {
    const token = tokens[i];

    // Whitespace and punctuation are kept as-is
    if (/^\s+$/.test(token) || /^[^\sA-Za-z0-9]$/.test(token)) {
      phrases.push(token);
      i++;
      continue;
    }

    // Group consecutive word tokens into phrases of 3-5 words
    const wordGroup: string[] = [];
    while (i < tokens.length && /^[A-Za-z0-9]+(?:['-][A-Za-z0-9]+)*$/.test(tokens[i])) {
      wordGroup.push(tokens[i]);
      i++;
      // Break at 5 words max per phrase
      if (wordGroup.length >= 5) break;
    }

    if (wordGroup.length > 0) {
      // Reconstruct with original whitespace from the next tokens if available
      let phrase = wordGroup.join("");
      // Add the whitespace/punctuation that followed the last word
      if (i < tokens.length && /^\s+$/.test(tokens[i])) {
        phrase += tokens[i];
        i++;
      }
      phrases.push(phrase);
    }
  }

  return phrases;
}

function diffModifiedBlocks(deleted: string[], inserted: string[]): SemanticDiffSegment[] {
  const segments: SemanticDiffSegment[] = [];
  const max = Math.max(deleted.length, inserted.length);

  for (let i = 0; i < max; i++) {
    const before = deleted[i] ?? "";
    const after = inserted[i] ?? "";

    if (before && after && similarity(before, after) >= 0.2) {
      segments.push(...tokenDiff(before, after));
    } else {
      if (before) segments.push({ tag: "delete", text: before });
      if (after) segments.push({ tag: "insert", text: after });
    }
  }

  return segments;
}

export function computeSemanticDiff(original: string, proposed: string): SemanticDiffSegment[] {
  if (!original && !proposed) return [];
  if (!original) return [{ tag: "insert", text: proposed }];
  if (!proposed) return [{ tag: "delete", text: original }];

  const beforeSentences = tokenizeSentences(original);
  const afterSentences = tokenizeSentences(proposed);
  const sentenceEdits = myersDiff(
    beforeSentences,
    afterSentences,
    (a, b) => normalizeForSentenceMatch(a) === normalizeForSentenceMatch(b),
  );

  const segments: SemanticDiffSegment[] = [];
  let index = 0;

  while (index < sentenceEdits.length) {
    const edit = sentenceEdits[index];

    if (edit.tag === "equal") {
      segments.push({ tag: "equal", text: edit.value });
      index++;
      continue;
    }

    const deleted: string[] = [];
    const inserted: string[] = [];

    while (index < sentenceEdits.length && sentenceEdits[index].tag !== "equal") {
      const current = sentenceEdits[index];
      if (current.tag === "delete") deleted.push(current.value);
      if (current.tag === "insert") inserted.push(current.value);
      index++;
    }

    if (deleted.length && inserted.length) {
      segments.push(...diffModifiedBlocks(deleted, inserted));
    } else {
      deleted.forEach((text) => segments.push({ tag: "delete", text }));
      inserted.forEach((text) => segments.push({ tag: "insert", text }));
    }
  }

  // Apply: coalesce → collapse trivial edits → merge into phrases
  let result = coalesceSegments(segments);
  result = collapseTrivialEdits(result);
  result = mergeAdjacentTokens(result);
  result = collapseTrivialEdits(result);
  return coalesceSegments(result);
}

/**
 * Extract a one-line change summary from a redline diff.
 * Summarizes what the redline does in plain legal language.
 */
export function extractChangeSummary(original: string, proposed: string, operation?: string): string {
  if (!original && proposed) {
    // Pure insert
    const firstLine = proposed.split(".")[0]?.trim() || "";
    return `Adds: ${firstLine}`;
  }
  if (original && !proposed) {
    return "Removes clause";
  }
  if (!original && !proposed) return "";

  // For modifications, extract key changed phrases
  const segments = computeSemanticDiff(original, proposed);
  const deletes = segments.filter(s => s.tag === "delete").map(s => s.text.trim()).filter(Boolean);
  const inserts = segments.filter(s => s.tag === "insert").map(s => s.text.trim()).filter(Boolean);

  const parts: string[] = [];

  // Build summary from insertions
  for (const ins of inserts) {
    const cleaned = ins.replace(/^\s+|\s+$/g, "").substring(0, 60);
    if (cleaned.length > 5) {
      parts.push(cleaned);
    }
  }

  if (parts.length === 0 && deletes.length > 0) {
    // Pure deletion
    const removed = deletes.join(" ").substring(0, 80);
    return `Removes: ${removed}`;
  }

  if (parts.length <= 2) {
    return parts.join("; ") || "Modifies clause language";
  }

  return `${parts[0]}; ${parts[1]}; and more`;
}

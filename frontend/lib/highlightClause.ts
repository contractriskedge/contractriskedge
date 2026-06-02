/**
 * highlightClause — locate and highlight clauses in the document viewer.
 *
 * Dispatches a custom event that DocumentViewer handles:
 * navigate to page → scroll to section → flash highlight → optional toast.
 */

export interface LocateClausePayload {
  /** Page number to navigate to */
  page: number;
  /** Finding or synthetic anchor id for section lookup */
  findingId: string;
  /** Clause text for fuzzy section match */
  clauseText?: string;
  /** Section number/title from redline (e.g. "8.1") */
  sectionLabel?: string;
  /** Clause type from redline (e.g. "indemnification") */
  clauseType?: string;
  /** Redline id when locating from Redline tab */
  redlineId?: string;
  chunkId?: string;
  clauseStartOffset?: number;
  clauseEndOffset?: number;
  /** Do not switch to Findings tab or change finding selection */
  preserveReviewContext?: boolean;
}

export interface LocateClauseSuccessDetail {
  page: number;
  sectionLabel?: string;
  matched: boolean;
}

export const LOCATE_CLAUSE_EVENT = "clause:locate";
export const LOCATE_CLAUSE_SUCCESS_EVENT = "clause:locate-success";
export const REVIEW_SHOW_DOCUMENT_PANEL_EVENT = "review:show-document-panel";
export const REDLINE_LOCATE_SOURCE_EVENT = "redline:locate-source";

export function locateClause(payload: LocateClausePayload): void {
  window.dispatchEvent(
    new CustomEvent<LocateClausePayload>(LOCATE_CLAUSE_EVENT, { detail: payload }),
  );
}

export function requestShowDocumentPanel(): void {
  window.dispatchEvent(new Event(REVIEW_SHOW_DOCUMENT_PANEL_EVENT));
}

/** Ask Redline workspace to locate the currently selected redline (or first expanded). */
export function requestLocateRedlineSource(redlineId?: string): void {
  window.dispatchEvent(
    new CustomEvent<{ redlineId?: string }>(REDLINE_LOCATE_SOURCE_EVENT, {
      detail: { redlineId },
    }),
  );
}

export function onLocateClause(
  handler: (payload: LocateClausePayload) => void,
): () => void {
  const listener = (e: Event) => {
    handler((e as CustomEvent<LocateClausePayload>).detail);
  };
  window.addEventListener(LOCATE_CLAUSE_EVENT, listener);
  return () => window.removeEventListener(LOCATE_CLAUSE_EVENT, listener);
}

export function onLocateClauseSuccess(
  handler: (detail: LocateClauseSuccessDetail) => void,
): () => void {
  const listener = (e: Event) => {
    handler((e as CustomEvent<LocateClauseSuccessDetail>).detail);
  };
  window.addEventListener(LOCATE_CLAUSE_SUCCESS_EVENT, listener);
  return () => window.removeEventListener(LOCATE_CLAUSE_SUCCESS_EVENT, listener);
}

export function onRedlineLocateSource(
  handler: (detail: { redlineId?: string }) => void,
): () => void {
  const listener = (e: Event) => {
    handler((e as CustomEvent<{ redlineId?: string }>).detail);
  };
  window.addEventListener(REDLINE_LOCATE_SOURCE_EVENT, listener);
  return () => window.removeEventListener(REDLINE_LOCATE_SOURCE_EVENT, listener);
}

/**
 * Session persistence for Redline workspace UI (per review).
 * Survives tab switches within the same browser session.
 */

export interface RedlineUiState {
  selectedRedlineId: string | null;
  scrollTop: number;
  statusFilter: string;
}

const STORAGE_PREFIX = "cre-redline-ui:";

export function redlineUiStorageKey(reviewId: string): string {
  return `${STORAGE_PREFIX}${reviewId}`;
}

export function loadRedlineUiState(reviewId: string | null): RedlineUiState {
  const empty: RedlineUiState = {
    selectedRedlineId: null,
    scrollTop: 0,
    statusFilter: "",
  };
  if (!reviewId || typeof window === "undefined") return empty;
  try {
    const raw = sessionStorage.getItem(redlineUiStorageKey(reviewId));
    if (!raw) return empty;
    const parsed = JSON.parse(raw) as Partial<RedlineUiState>;
    return {
      selectedRedlineId:
        typeof parsed.selectedRedlineId === "string" ? parsed.selectedRedlineId : null,
      scrollTop: typeof parsed.scrollTop === "number" ? parsed.scrollTop : 0,
      statusFilter: typeof parsed.statusFilter === "string" ? parsed.statusFilter : "",
    };
  } catch {
    return empty;
  }
}

export function saveRedlineUiState(reviewId: string, state: RedlineUiState): void {
  if (typeof window === "undefined") return;
  try {
    sessionStorage.setItem(redlineUiStorageKey(reviewId), JSON.stringify(state));
  } catch {
    // Quota or private mode — ignore
  }
}

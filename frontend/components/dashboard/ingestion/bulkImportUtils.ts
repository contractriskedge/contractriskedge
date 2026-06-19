import type { UploadSummary } from "@/services/api/uploads";
import type { ImportJob } from "./types";

export interface BulkImportSession {
  id: string;
  startedAt: string;
  expectedCount: number;
  uploadIds: string[];
  dismissed: boolean;
}

export interface BulkImportProgress {
  total: number;
  uploading: number;
  queued: number;
  processing: number;
  analyzing: number;
  completed: number;
  failed: number;
  active: number;
  percentComplete: number;
  isActive: boolean;
  aiQueuePending?: number;
}

export const BULK_IMPORT_SESSION_KEY = "ingestion-bulk-import-session";
export const BULK_IMPORT_MIN_FILES = 2;

const TERMINAL_STATES = new Set(["review_ready", "failed", "cancelled", "quarantined"]);

type PipelineBucket = "queued" | "processing" | "analyzing" | "completed" | "failed";

function bucketIngestionState(state: string): PipelineBucket {
  const normalized = state.toLowerCase();
  if (normalized === "review_ready") return "completed";
  if (normalized === "failed" || normalized === "cancelled" || normalized === "quarantined") {
    return "failed";
  }
  if (normalized === "analysis_pending") return "analyzing";
  if (["uploaded", "validating", "validated", "storage_confirmed"].includes(normalized)) {
    return "queued";
  }
  return "processing";
}

export function isBulkImportSession(session: BulkImportSession | null): session is BulkImportSession {
  return session != null && !session.dismissed;
}

export function loadBulkImportSession(): BulkImportSession | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = sessionStorage.getItem(BULK_IMPORT_SESSION_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as BulkImportSession;
    if (!parsed?.id || parsed.dismissed) return null;
    const ageMs = Date.now() - new Date(parsed.startedAt).getTime();
    if (ageMs > 24 * 60 * 60 * 1000) return null;
    // Repair sessions where expectedCount was inflated by repeated bulk uploads
    if (parsed.uploadIds?.length > 0 && parsed.expectedCount > parsed.uploadIds.length) {
      parsed.expectedCount = parsed.uploadIds.length;
    }
    return parsed;
  } catch {
    return null;
  }
}

export function saveBulkImportSession(session: BulkImportSession | null): void {
  if (typeof window === "undefined") return;
  if (!session || session.dismissed) {
    sessionStorage.removeItem(BULK_IMPORT_SESSION_KEY);
    return;
  }
  sessionStorage.setItem(BULK_IMPORT_SESSION_KEY, JSON.stringify(session));
}

export function createBulkImportSession(fileCount: number): BulkImportSession {
  return {
    id: `bulk-${Date.now()}`,
    startedAt: new Date().toISOString(),
    expectedCount: fileCount,
    uploadIds: [],
    dismissed: false,
  };
}

function sessionUploads(
  uploads: UploadSummary[],
  session: BulkImportSession,
): UploadSummary[] {
  const idSet = new Set(session.uploadIds);
  const startedAt = new Date(session.startedAt).getTime() - 5_000;
  // Match by upload ID and/or session window so sequential uploads stay in scope
  return uploads.filter(
    (u) => idSet.has(u.upload_id) || new Date(u.created_at).getTime() >= startedAt,
  );
}

function resolveBulkTotal(
  session: BulkImportSession,
  relevantUploads: UploadSummary[],
  pendingLocals: number,
): number {
  const received = session.uploadIds.length;
  const inList = relevantUploads.length;

  // Once uploads are registered, trust uploadIds — not an inflated expectedCount
  if (received > 0) {
    return Math.max(received, inList) + pendingLocals;
  }

  // Files still uploading to the API
  if (pendingLocals > 0) {
    return Math.max(session.expectedCount, inList + pendingLocals);
  }

  // HTTP upload finished — use actual rows, not a stale inflated expectedCount
  if (inList > 0) {
    return inList;
  }

  return session.expectedCount;
}

export function computeBulkImportProgress(
  uploads: UploadSummary[],
  localJobs: ImportJob[],
  session: BulkImportSession | null,
  options?: { aiQueuePending?: number },
): BulkImportProgress | null {
  const pendingLocals = localJobs.filter(
    (j) => !j.backendUploadId && (j.status === "running" || j.status === "pending"),
  );
  const failedLocals = localJobs.filter((j) => j.status === "failed" && !j.backendUploadId);

  let relevantUploads: UploadSummary[];
  let total: number;

  if (session) {
    relevantUploads = sessionUploads(uploads, session);
    total = resolveBulkTotal(session, relevantUploads, pendingLocals.length);
  } else if (pendingLocals.length + uploads.filter((u) => !TERMINAL_STATES.has(u.ingestion_state)).length >= 5) {
    relevantUploads = uploads.filter((u) => !TERMINAL_STATES.has(u.ingestion_state));
    total = relevantUploads.length + pendingLocals.length;
  } else {
    return null;
  }

  const counts = {
    uploading: pendingLocals.length,
    queued: 0,
    processing: 0,
    analyzing: 0,
    completed: 0,
    failed: failedLocals.length,
  };

  for (const upload of relevantUploads) {
    const bucket = bucketIngestionState(upload.ingestion_state);
    counts[bucket] += 1;
  }

  const finished = counts.completed + counts.failed;
  const active = counts.uploading + counts.queued + counts.processing + counts.analyzing;
  const percentComplete = total > 0 ? Math.round((finished / total) * 100) : 0;

  return {
    total,
    ...counts,
    active,
    percentComplete,
    isActive: active > 0,
    aiQueuePending: options?.aiQueuePending,
  };
}

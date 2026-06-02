/**
 * Centralized API client layer for ContractRiskEdge.
 *
 * Architecture:
 * - Single fetch wrapper with typed responses
 * - Automatic JWT Bearer token injection
 * - Structured error normalization with error codes
 * - Response retry classification
 * - Request timeout handling
 * - Idempotency-Key header support for mutations
 * - Request coalescing (deduplicates in-flight GET requests)
 * - Stale request cancellation support
 *
 * Usage:
 *   import { api } from '@/services/api/client';
 *   const reviews = await api.get('/reviews/');
 *   const review = await api.get(`/reviews/${id}`);
 *   const created = await api.post('/reviews/', body, { idempotencyKey: 'uuid' });
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "/api/v1";
const DEFAULT_TIMEOUT = 30_000; // 30 seconds
const MAX_RETRIES = 3;

// ── Request Coalescing ────────────────────────────────────────────
// Deduplicates in-flight GET requests so multiple components requesting
// the same endpoint share one HTTP call. This prevents:
// - Duplicate network requests on page load
// - Parallel polling calls for the same resource
// - Infrastructure cost explosion with many concurrent users
import { requestCoalescer } from "@/services/api/requestCoalescer";

// ── Types ─────────────────────────────────────────────────────────

export interface ApiError {
  error_code: string;
  message: string;
  status_code: number;
  category: string;
  retryable: boolean;
  details?: Record<string, unknown>;
}

export interface ApiResponse<T> {
  data: T;
  cached?: boolean;
  resource_id?: string;
}

export interface PaginatedResponse<T> {
  data: T[];
  pagination: {
    page: number;
    page_size: number;
    total: number;
    total_pages: number;
  };
}

export interface ReviewStatusResponse {
  review_id: string;
  upload_id: string;
  status: string;
  ingestion_state: string | null;
  ai_status: string | null;
  review_status: string | null;
  progress: number;
  current_step: string | null;
  error: string | null;
  error_code: string | null;
  can_retry: boolean;
  created_at: string;
  updated_at: string;
  completed_at: string | null;
}

/** Unwrap GET /reviews/:id when a proxy or bug returns a paginated envelope. */
export function normalizeReviewDetail(raw: unknown): ReviewDetail {
  if (!raw || typeof raw !== "object") {
    throw new NetworkError("Invalid review response from server");
  }
  const obj = raw as Record<string, unknown>;
  if (typeof obj.review_id === "string") {
    return obj as ReviewDetail;
  }
  const nested = obj.data;
  if (nested && typeof nested === "object" && !Array.isArray(nested)) {
    const detail = nested as Record<string, unknown>;
    if (typeof detail.review_id === "string") {
      return detail as ReviewDetail;
    }
  }
  if (Array.isArray(nested) && nested.length > 0) {
    const first = nested[0] as Record<string, unknown>;
    if (typeof first.review_id === "string") {
      return first as ReviewDetail;
    }
  }
  throw new NetworkError("Review response missing review_id");
}

export interface ReviewDetail {
  review_id: string;
  upload_id: string;
  contract_id: string | null;
  status: string;
  assigned_to: string | null;
  assigned_by: string | null;
  assigned_at: string | null;
  started_at: string | null;
  workflow_stage: string | null;
  priority: string;
  finding_count: number;
  redline_count: number;
  comment_count: number;
  escalation_count: number;
  sla_deadline: string | null;
  sla_due_at: string | null;
  sla_breached: boolean;
  sla_status: string;
  overdue_hours: number;
  created_by: string;
  created_at: string;
  updated_at: string;
  completed_at: string | null;
  rejection_reason: string | null;
  rejection_category: string | null;
  rejection_severity: string | null;
  rejected_by: string | null;
  rejected_at: string | null;
  approved_version_id: string | null;
  approved_version_number: number | null;
  document_name: string | null;
  original_filename: string | null;
  document_type: string | null;
  risk_score: number | null;
  version: number;
}

export interface WorkloadMetrics {
  total: number;
  unassigned: number;
  in_review: number;
  overdue: number;
  escalated: number;
  critical: number;
  sla_at_risk: number;
  completed_today: number;
}

export interface BulkActionResponse {
  action_id: string;
  action_type: string;
  total: number;
  succeeded: number;
  failed: number;
  errors: string[];
}

export interface DocumentVersionItem {
  version_id: string;
  review_id: string;
  version_number: number;
  label: string | null;
  status: string;
  source_document_id: string | null;
  storage_key: string | null;
  change_summary: string | null;
  accepted_redline_ids: string[];
  file_size_bytes: number | null;
  mime_type: string | null;
  checksum_sha256: string | null;
  created_by: string;
  created_at: string;
}

export interface RiskBreakdownItem {
  category: string;
  label: string;
  contribution: number;
  /** Absolute remaining exposure points — sum == remaining_exposure */
  normalized_contribution: number;
  /** Share of remaining exposure (sums to 100) — display derivative */
  exposure_share_pct?: number;
  finding_count: number;
  severity: string;
  mitigated_count: number;
  dismissed_count: number;
  accepted_count: number;
  open_count: number;
  findings: RiskBreakdownFinding[];
}

export interface RiskBreakdownFinding {
  finding_id: string;
  title: string;
  severity: string;
  risk_score: number | null;
  contribution: number;
  remaining_contribution?: number;
  risk_reduction_value?: number;
  resolution: string | null;
  resolution_type: string;
  clause_type: string | null;
  clause_label?: string;
  recommended_mitigation?: string;
  business_impact?: string;
}

export interface MitigatedFinding {
  finding_id?: string;
  title: string;
  clause_type: string | null;
  clause_label?: string;
  severity: string;
  resolution: string;
  resolution_label: string;
  remaining_contribution?: number;
  risk_reduction_value?: number;
  business_impact?: string;
  recommended_mitigation?: string;
  review_state?: string;
  linked_redline_count?: number;
}

export interface MitigationEffectiveness {
  mitigated_pct: number;
  dismissed_pct: number;
  accepted_pct: number;
  remaining_pct: number;
  effectiveness_score: number;
  total_risk_addressed: number;
}

export interface DeltaExplanation {
  category: string;
  label: string;
  contribution: number;
  details: string[];
}

export interface MitigationSuggestion {
  category: string;
  label: string;
  remaining_contribution: number;
  suggested_mitigations: MitigationSuggestionItem[];
}

export interface MitigationSuggestionItem {
  mitigation_type: string;
  label: string;
  description: string;
  estimated_reduction: number;
  estimated_reduction_pct: number;
  confidence: number;
  source: string;
  range_low: number;
  range_high: number;
}

/** A normalized contributor to remaining exposure — sum(normalized_contribution) == remaining_exposure */
export interface ExposureContributor {
  category: string;
  label: string;
  contribution: number;
  normalized_contribution: number;
  exposure_share_pct?: number;
  open_weight: number;
  accepted_weight: number;
  mitigated_weight: number;
  dismissed_weight: number;
  details: string[];
}

/** A single top recommended action — executive guidance widget item */
export interface TopRecommendedAction {
  category: string;
  label: string;
  mitigation_type: string;
  mitigation_label: string;
  description: string;
  estimated_reduction_pct: number;
  estimated_reduction_abs: number;
  confidence: number;
  source: string;
  remaining_contribution: number;
}

/** Top recommended actions across ALL categories — executive guidance widget */
export interface TopRecommendedActions {
  top_actions: TopRecommendedAction[];
  total_potential_reduction_pct: number;
  total_potential_reduction_abs: number;
  action_count: number;
}

export interface RiskBreakdown {
  overall_risk_score: number;
  overall_label: string;
  /** Immutable original AI risk score — always preserved as reference */
  original_risk_score: number;
  /** Dominant live metric — same as remaining_exposure */
  current_contract_risk: number;
  remaining_exposure: number;
  remaining_label: string;
  /** detected = pre-review; remaining = post-review live exposure */
  exposure_mode?: "detected" | "remaining";
  review_started?: boolean;
  risk_delta?: number;
  mitigation_effectiveness?: MitigationEffectiveness;
  /** Per-category mitigation suggestions from the effectiveness engine */
  mitigation_suggestions?: MitigationSuggestion[];
  /** Top recommended actions across ALL categories — executive guidance widget */
  top_recommended_actions?: TopRecommendedActions;
  /** no_analysis | score_only | analyzed — when breakdown may be empty */
  status?: string;
  breakdown: RiskBreakdownItem[];
  risk_reduction: number;
  dismissed_reduction: number;
  accepted_reduction: number;
  mitigated_findings: MitigatedFinding[];
  accepted_risk_findings: MitigatedFinding[];
  dismissed_findings: MitigatedFinding[];
  open_findings: MitigatedFinding[];
  delta_explanations: DeltaExplanation[];
  /** Canonical contributors — normalized_contribution matches category bars */
  exposure_contributors: ExposureContributor[];
}

export interface FallbackRecommendation {
  clause_id: string;
  playbook_id: string;
  category: string;
  clause_type: string;
  title: string;
  body: string;
  summary: string | null;
  risk_level: string;
  tags: string[];
  is_active: boolean;
}

export interface FindingItem {
  finding_id: string;
  clause_type: string | null;
  severity: string;
  title: string;
  description: string;
  recommendation: string | null;
  confidence: number | null;
  risk_score: number | null;
  page_numbers: number[];
  resolution: string | null;
  resolution_note: string | null;
  resolved_by: string | null;
  resolved_at: string | null;
  created_at: string;
}

export interface WordDiffSegment {
  tag: "equal" | "delete" | "insert";
  text: string;
}

export interface ConfidenceLabel {
  label: "Very High" | "High" | "Medium" | "Low" | "Uncertain";
  tier: "very_high" | "high" | "medium" | "low" | "uncertain";
  numeric: number;
}

export interface RiskTraceability {
  detected_risk: string;
  business_impact: string;
  mitigation_strategy: string;
  /** Extended fields for mitigation-generated redlines */
  mitigation_type?: string;
  estimated_reduction_pct?: number;
  confidence?: number;
  source?: string;
  generated_from?: string;
}

export interface LocatorResponse {
  status: string;
  anchor_type: string;
  confidence: number;
  section_id: string | null;
  section_title: string | null;
  insert_position: string | null;
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

export interface RedlineItem {
  redline_id: string;
  clause_type: string | null;
  original_text: string;
  proposed_text: string;
  /** Original AI suggestion before lawyer customization (when modified). */
  ai_proposed_text?: string | null;
  finding_id?: string | null;
  operation?: string | null;
  anchor_text?: string | null;
  context_excerpt?: string | null;
  chunk_ids?: string[];
  word_diff?: WordDiffSegment[];
  rationale: string | null;
  risk_level: string | null;
  confidence: number | null;
  confidence_label?: ConfidenceLabel | null;
  status: string;
  reviewer_modified_text: string | null;
  review_notes: string | null;
  reviewed_by: string | null;
  reviewed_at: string | null;
  created_at: string;
  locator?: LocatorResponse | null;
  traceability?: RiskTraceability | null;
}

export interface CommentItem {
  comment_id: string;
  entity_type: string | null;
  entity_id: string | null;
  parent_comment_id: string | null;
  author_id: string;
  author_name?: string | null;
  body: string;
  mentions: string[];
  created_at: string;
  updated_at: string;
}

export interface UploadProgress {
  percent: number;
  label: string;
  state: string;
}

export interface UploadStatusResponse {
  upload_id: string;
  filename: string;
  file_size: number;
  content_type: string;
  ingestion_state: string;
  ingestion_error: string | null;
  retry_count: number;
  max_retries: number;
  can_retry: boolean;
  progress: UploadProgress | null;
  storage_key: string | null;
  checksum_sha256: string | null;
  created_at: string;
  updated_at: string;
  completed_at: string | null;
}

export interface UploadResponse {
  upload_id: string;
  filename: string;
  file_size: number;
  content_type: string;
  ingestion_state: string;
  message: string;
  correlation_id: string | null;
}

export interface AnalysisRunResponse {
  run_id: string;
  upload_id: string;
  analysis_type: string;
  status: string;
  model: string;
  provider: string;
  prompt_version: number | null;
  risk_score: number | null;
  findings_count: number;
  redlines_count: number;
  total_tokens: number;
  cost_usd: number;
  latency_ms: number | null;
  error_message: string | null;
  retry_count: number;
  created_at: string;
  completed_at: string | null;
}

export interface DashboardResponse {
  stats: {
    total_reviews: number;
    total_findings: number;
    total_redlines: number;
    average_risk_score: number | null;
    average_confidence: number | null;
    sla_breach_count: number;
    pending_reviews: number;
    completed_reviews: number;
    escalated_count: number;
    total_escalation_events: number;
    resolved_escalations: number;
    escalation_resolution_rate: number;
    unassigned_count: number;
    overdue_count: number;
    completed_7d: number;
    avg_review_age_hours: number;
  };
  findings_by_severity: Record<string, number>;
  findings_by_clause_type: Record<string, number>;
  reviews_by_status: Record<string, number>;
  recent_activity: Array<{
    activity_type: string;
    review_id: string;
    upload_id: string | null;
    description: string;
    actor: string | null;
    timestamp: string;
  }>;
  sla_at_risk: number;
}

// ── Reviewer Ops Types ──────────────────────────────────────────

export interface MyWorkItem {
  review_id: string;
  contract_name: string | null;
  status: string;
  risk_score: number | null;
  sla_deadline: string | null;
  assigned_to: string | null;
  created_at: string;
}

export interface RecommendationItem {
  finding_id: string;
  review_id: string;
  clause_type: string | null;
  severity: string;
  title: string;
  description: string;
  recommendation: string;
  confidence: number;
  risk_score: number | null;
  created_at: string;
}

// ── Error Classes ─────────────────────────────────────────────────

/** Normalize FastAPI error bodies (string detail or validation array). */
function formatApiErrorMessage(
  body: Record<string, unknown>,
  status: number,
): string {
  if (typeof body.message === "string" && body.message) {
    return body.message;
  }
  const detail = body.detail;
  if (typeof detail === "string" && detail) {
    return detail;
  }
  if (detail && typeof detail === "object" && !Array.isArray(detail)) {
    const nested = detail as Record<string, unknown>;
    if (typeof nested.message === "string" && nested.message) {
      return nested.message;
    }
  }
  if (Array.isArray(detail)) {
    const parts = detail.map((item) => {
      if (item && typeof item === "object" && "msg" in item) {
        const entry = item as { loc?: unknown[]; msg: string };
        const field = Array.isArray(entry.loc)
          ? entry.loc.filter((p) => p !== "body").join(".")
          : "";
        return field ? `${field}: ${entry.msg}` : entry.msg;
      }
      return String(item);
    });
    if (parts.length > 0) return parts.join("; ");
  }
  return `HTTP ${status}`;
}

export class ApiRequestError extends Error {
  public error_code: string;
  public status_code: number;
  public category: string;
  public retryable: boolean;
  public details?: Record<string, unknown>;

  constructor(error: ApiError) {
    super(error.message);
    this.name = "ApiRequestError";
    this.error_code = error.error_code;
    this.status_code = error.status_code;
    this.category = error.category;
    this.retryable = error.retryable;
    this.details = error.details;
  }
}

export class NetworkError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "NetworkError";
  }
}

export class TimeoutError extends Error {
  constructor(timeout: number) {
    super(`Request timed out after ${timeout}ms`);
    this.name = "TimeoutError";
  }
}

// ── Token Management ──────────────────────────────────────────────

let _tokenCache: string | null = null;
let _tokenExpiry: number = 0;

function getStoredToken(): string | null {
  if (typeof window === "undefined") return null;
  try {
    return localStorage.getItem("auth_token");
  } catch {
    return null;
  }
}

export async function getValidToken(): Promise<string | null> {
  const token = getStoredToken();
  if (token) return token;

  // Try to get a dev token — retry a few times in case AuthProvider
  // is still initialising.
  for (let attempt = 0; attempt < 3; attempt++) {
    try {
      const res = await fetch(`${API_BASE}/auth/token`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
      });
      if (res.ok) {
        const data = await res.json();
        const newToken = data.access_token;
        if (typeof window !== "undefined") {
          localStorage.setItem("auth_token", newToken);
        }
        return newToken;
      }
    } catch {
      if (attempt === 2) {
        console.warn("[api] Dev token fetch failed after 3 attempts");
      }
      // Wait briefly before retrying
      await new Promise((r) => setTimeout(r, 200));
    }
  }

  return null;
}

// ── Core Request Function ─────────────────────────────────────────

interface RequestOptions {
  method?: string;
  body?: unknown;
  token?: string;
  idempotencyKey?: string;
  timeout?: number;
  retries?: number;
  signal?: AbortSignal;
  headers?: Record<string, string>;
  /** Set to false to disable request coalescing for this request.
   *  Only applies to GET requests. Default: true for GET, false for others. */
  coalesce?: boolean;
}

async function request<T>(
  path: string,
  options: RequestOptions = {},
): Promise<T> {
  const {
    method = "GET",
    body,
    token,
    idempotencyKey,
    timeout = DEFAULT_TIMEOUT,
    signal: externalSignal,
    headers: extraHeaders,
  } = options;

  // Resolve auth token
  const authToken = token || (await getValidToken());

  // Build headers
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...extraHeaders,
  };

  if (authToken) {
    headers["Authorization"] = `Bearer ${authToken}`;
  }

  if (idempotencyKey) {
    headers["Idempotency-Key"] = idempotencyKey;
  }

  // Timeout handling
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeout);

  // Combine with external signal if provided
  const signal = externalSignal
    ? combineSignals(externalSignal, controller.signal)
    : controller.signal;

  try {
    const res = await fetch(`${API_BASE}${path}`, {
      method,
      headers,
      body: body ? JSON.stringify(body) : undefined,
      signal,
    });

    clearTimeout(timeoutId);

    // Handle empty responses (204 No Content)
    if (res.status === 204) {
      return undefined as T;
    }

    const rawText = await res.text();
    let responseBody: Record<string, unknown>;
    try {
      responseBody = rawText ? JSON.parse(rawText) : {};
    } catch {
      throw new NetworkError(
        res.ok
          ? "Invalid JSON response from server"
          : `Server error (${res.status}): ${rawText.slice(0, 300)}`,
      );
    }

    if (!res.ok) {
      if (res.status === 401 && typeof window !== "undefined") {
        try {
          localStorage.removeItem("auth_token");
        } catch {
          /* ignore */
        }
      }
      const apiError: ApiError = {
        error_code: (responseBody.error_code as string) || "UNKNOWN_ERROR",
        message: formatApiErrorMessage(responseBody, res.status),
        status_code: res.status,
        category: (responseBody.category as string) || "unknown",
        retryable:
          (responseBody.retryable as boolean | undefined) ??
          isRetryableStatus(res.status),
        details: responseBody.details as Record<string, unknown> | undefined,
      };
      throw new ApiRequestError(apiError);
    }

    return responseBody as T;
  } catch (err) {
    clearTimeout(timeoutId);

    if (err instanceof ApiRequestError) throw err;

    if (err instanceof DOMException && err.name === "AbortError") {
      throw new TimeoutError(timeout);
    }

    if (err instanceof TypeError && err.message.includes("fetch")) {
      throw new NetworkError("Network request failed. Check your connection.");
    }

    throw new NetworkError(
      err instanceof Error ? err.message : "An unknown network error occurred",
    );
  }
}

// ── Retry Logic ───────────────────────────────────────────────────

async function requestWithRetry<T>(
  path: string,
  options: RequestOptions = {},
): Promise<T> {
  const maxRetries = options.retries ?? MAX_RETRIES;
  let lastError: Error | null = null;

  // ── Request Coalescing for GET requests ───────────────────────
  // When multiple components request the same GET endpoint simultaneously,
  // they share one in-flight HTTP request. This prevents:
  // - Duplicate network requests on page load
  // - Parallel polling calls for the same resource
  // - Infrastructure cost explosion with many concurrent users
  //
  // Mutations (POST, PUT, PATCH, DELETE) are never coalesced.
  const method = options.method ?? "GET";
  if (method === "GET" && options.coalesce !== false) {
    return requestCoalescer.dedup(
      `${API_BASE}${path}`,
      () => executeWithRetry<T>(path, options, maxRetries),
      { method: "GET", signal: options.signal },
    );
  }

  return executeWithRetry<T>(path, options, maxRetries);
}

/**
 * Execute a request with retry logic (inner function, no coalescing).
 */
async function executeWithRetry<T>(
  path: string,
  options: RequestOptions = {},
  maxRetries: number = MAX_RETRIES,
): Promise<T> {
  let lastError: Error | null = null;

  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    try {
      return await request<T>(path, options);
    } catch (err) {
      lastError = err as Error;

      // Don't retry non-retryable errors
      if (err instanceof ApiRequestError && !err.retryable) {
        throw err;
      }

      // Don't retry if this was the last attempt
      if (attempt >= maxRetries) break;

      // Exponential backoff
      const delay = Math.min(1000 * Math.pow(2, attempt), 10_000);
      await new Promise((resolve) => setTimeout(resolve, delay));
    }
  }

  throw lastError || new Error("Request failed after retries");
}

// ── Helper Functions ──────────────────────────────────────────────

function isRetryableStatus(status: number): boolean {
  return (
    status === 429 || // Rate limited
    status === 502 || // Bad gateway
    status === 503 || // Service unavailable
    status === 504    // Gateway timeout
  );
}

function combineSignals(...signals: AbortSignal[]): AbortSignal {
  const controller = new AbortController();
  for (const signal of signals) {
    if (signal.aborted) {
      controller.abort(signal.reason);
      return controller.signal;
    }
    signal.addEventListener("abort", () => controller.abort(signal.reason), {
      once: true,
    });
  }
  return controller.signal;
}

// ── Public API ────────────────────────────────────────────────────

export const api = {
  get: <T>(path: string, options?: RequestOptions) =>
    requestWithRetry<T>(path, { ...options, method: "GET" }),

  post: <T>(path: string, body?: unknown, options?: RequestOptions) =>
    requestWithRetry<T>(path, { ...options, method: "POST", body }),

  put: <T>(path: string, body?: unknown, options?: RequestOptions) =>
    requestWithRetry<T>(path, { ...options, method: "PUT", body }),

  patch: <T>(path: string, body?: unknown, options?: RequestOptions) =>
    requestWithRetry<T>(path, { ...options, method: "PATCH", body }),

  delete: <T>(path: string, options?: RequestOptions) =>
    requestWithRetry<T>(path, { ...options, method: "DELETE" }),

  /** Upload a file via multipart form data */
  uploadFile: async <T>(
    path: string,
    file: File,
    token?: string,
    extraFields?: Record<string, string>,
  ): Promise<T> => {
    const authToken = token || (await getValidToken());
    const formData = new FormData();
    formData.append("file", file);

    if (extraFields) {
      Object.entries(extraFields).forEach(([key, value]) => {
        formData.append(key, value);
      });
    }

    const headers: Record<string, string> = {};
    if (authToken) {
      headers["Authorization"] = `Bearer ${authToken}`;
    }

    const res = await fetch(`${API_BASE}${path}`, {
      method: "POST",
      headers,
      body: formData,
    });

    const rawText = await res.text();
    let responseBody: Record<string, unknown> = {};
    try {
      responseBody = rawText ? JSON.parse(rawText) : {};
    } catch {
      const hint = rawText.includes("InvalidAccessKeyId") || rawText.includes("Object storage")
        ? "Document storage (MinIO) is not reachable or credentials are wrong. Restart MinIO and check S3_ACCESS_KEY in backend/.env."
        : rawText.includes("Exception") || rawText.includes("Traceback")
          ? "The API returned an error page instead of JSON. Is the backend running on port 8000?"
          : `Server returned non-JSON (${res.status}).`;
      throw new NetworkError(
        res.ok ? "Invalid JSON response from server" : `${hint} ${rawText.slice(0, 200)}`.trim(),
      );
    }

    if (!res.ok) {
      if (res.status === 401 && typeof window !== "undefined") {
        try {
          localStorage.removeItem("auth_token");
        } catch {
          /* ignore */
        }
      }
      const message =
        (typeof responseBody.message === "string" && responseBody.message) ||
        formatApiErrorMessage(responseBody, res.status) ||
        "Upload failed";
      const apiError: ApiError = {
        error_code:
          (responseBody.error_code as string) ||
          (responseBody.error as string) ||
          "UPLOAD_FAILURE",
        message,
        status_code: res.status,
        category: (responseBody.category as string) || "ingestion",
        retryable: (responseBody.retryable as boolean | undefined) ?? res.status === 503,
        details: responseBody.details as Record<string, unknown> | undefined,
      };
      throw new ApiRequestError(apiError);
    }
    return responseBody as T;
  },

  /**
   * Download a binary file from the API with auth headers (exports, DOCX, ZIP).
   */
  downloadFile: async (
    path: string,
    filename: string,
    accept?: string,
  ): Promise<void> => {
    const authToken = await getValidToken();
    const headers: Record<string, string> = {};
    if (accept) headers.Accept = accept;
    if (authToken) headers.Authorization = `Bearer ${authToken}`;

    const res = await fetch(`${API_BASE}${path}`, { headers });
    if (!res.ok) {
      const detail = await res.text().catch(() => "");
      throw new NetworkError(
        detail
          ? `Download failed (${res.status}): ${detail.slice(0, 200)}`
          : `Download failed (${res.status})`,
      );
    }

    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = filename;
    document.body.appendChild(anchor);
    anchor.click();
    document.body.removeChild(anchor);
    URL.revokeObjectURL(url);
  },

  /** Generate an idempotency key for mutation operations */
  generateIdempotencyKey: (): string => {
    return crypto.randomUUID ? crypto.randomUUID() : 
      "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => {
        const r = (Math.random() * 16) | 0;
        return (c === "x" ? r : (r & 0x3) | 0x8).toString(16);
      });
  },
};

export default api;

/**
 * Frontend error governance — centralized runtime error handling.
 *
 * Normalizes API errors, realtime errors, and rendering errors into
 * a consistent structure with correlation IDs, severity classification,
 * and actionable user messaging.
 */

"use client";

// ── Error Classification ──────────────────────────────────────────

export type ErrorSeverity = "critical" | "high" | "medium" | "low" | "info";

export type ErrorCategory =
  | "api"
  | "auth"
  | "permission"
  | "timeout"
  | "network"
  | "realtime"
  | "hydration"
  | "render"
  | "validation"
  | "not_found"
  | "rate_limited"
  | "degraded_backend"
  | "unknown";

export interface NormalizedError {
  message: string;
  category: ErrorCategory;
  severity: ErrorSeverity;
  statusCode: number;
  correlationId: string;
  retryable: boolean;
  retryAfterMs?: number;
  details?: Record<string, unknown>;
  originalError?: unknown;
}

// ── Correlation ID ────────────────────────────────────────────────

function generateCorrelationId(): string {
  return `err-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;
}

function extractCorrelationId(error: unknown): string | undefined {
  if (error && typeof error === "object") {
    const e = error as Record<string, unknown>;
    return (e.correlation_id ?? e.correlationId ?? e.requestId ?? e.request_id) as string | undefined;
  }
  return undefined;
}

// ── Error Normalizers ─────────────────────────────────────────────

export function normalizeApiError(error: unknown): NormalizedError {
  const correlationId = extractCorrelationId(error) ?? generateCorrelationId();

  if (!error || typeof error !== "object") {
    return {
      message: "An unexpected error occurred",
      category: "unknown",
      severity: "medium",
      statusCode: 0,
      correlationId,
      retryable: false,
    };
  }

  const e = error as Record<string, unknown>;

  // API error shape from our backend
  if (e.error_code || e.status_code) {
    const statusCode = (e.status_code as number) ?? 500;
    const errorCode = (e.error_code as string) ?? "unknown";

    let category: ErrorCategory = "api";
    let severity: ErrorSeverity = "medium";
    let retryable = false;
    let retryAfterMs: number | undefined;

    switch (statusCode) {
      case 401:
        category = "auth";
        severity = "high";
        retryable = false;
        break;
      case 403:
        category = "permission";
        severity = "high";
        retryable = false;
        break;
      case 404:
        category = "not_found";
        severity = "low";
        retryable = false;
        break;
      case 429:
        category = "rate_limited";
        severity = "medium";
        retryable = true;
        retryAfterMs = ((e.retry_after as number) ?? 5) * 1000;
        break;
      case 502:
      case 503:
      case 504:
        category = "degraded_backend";
        severity = "high";
        retryable = true;
        retryAfterMs = 5000;
        break;
      case 408:
        category = "timeout";
        severity = "medium";
        retryable = true;
        retryAfterMs = 2000;
        break;
      default:
        category = statusCode >= 500 ? "degraded_backend" : "api";
        severity = statusCode >= 500 ? "high" : "medium";
        retryable = statusCode >= 500 || statusCode === 429;
    }

    return {
      message: (e.message as string) ?? `HTTP ${statusCode}: ${errorCode}`,
      category,
      severity,
      statusCode,
      correlationId,
      retryable,
      retryAfterMs,
      details: e.details as Record<string, unknown> | undefined,
      originalError: error,
    };
  }

  // Network error (fetch failed)
  if (e.name === "TypeError" && (e.message as string)?.includes("fetch")) {
    return {
      message: "Network request failed. Please check your connection.",
      category: "network",
      severity: "high",
      statusCode: 0,
      correlationId,
      retryable: true,
      retryAfterMs: 3000,
      originalError: error,
    };
  }

  // Timeout error
  if ((e.name as string) === "TimeoutError" || (e.message as string)?.includes("timeout")) {
    return {
      message: "Request timed out. Please try again.",
      category: "timeout",
      severity: "medium",
      statusCode: 408,
      correlationId,
      retryable: true,
      retryAfterMs: 2000,
      originalError: error,
    };
  }

  return {
    message: (e.message as string) ?? "An unexpected error occurred",
    category: "unknown",
    severity: "medium",
    statusCode: (e.status as number) ?? 0,
    correlationId,
    retryable: false,
    originalError: error,
  };
}

export function normalizeRealtimeError(error: unknown): NormalizedError {
  const correlationId = generateCorrelationId();

  if (!error || typeof error !== "object") {
    return {
      message: "Real-time connection error",
      category: "realtime",
      severity: "medium",
      statusCode: 0,
      correlationId,
      retryable: true,
      retryAfterMs: 3000,
    };
  }

  const e = error as Record<string, unknown>;
  const msg = (e.message as string) ?? "Real-time connection lost. Reconnecting...";

  return {
    message: msg,
    category: "realtime",
    severity: msg.includes("auth") || msg.includes("permission") ? "high" : "medium",
    statusCode: (e.code as number) ?? 0,
    correlationId,
    retryable: true,
    retryAfterMs: 3000,
    details: e as Record<string, unknown>,
    originalError: error,
  };
}

// ── User-Friendly Messages ────────────────────────────────────────

const USER_MESSAGES: Record<ErrorCategory, string> = {
  api: "Something went wrong. Please try again.",
  auth: "Your session has expired. Please log in again.",
  permission: "You don't have permission to perform this action.",
  timeout: "The request took too long. Please try again.",
  network: "Network connection lost. Please check your internet.",
  realtime: "Live updates disconnected. Reconnecting...",
  hydration: "Page did not load correctly. Please refresh.",
  render: "A component failed to render. We've been notified.",
  validation: "Please check your input and try again.",
  not_found: "The requested resource was not found.",
  rate_limited: "Too many requests. Please wait a moment.",
  degraded_backend: "The system is experiencing high load. Please try again shortly.",
  unknown: "An unexpected error occurred. We've been notified.",
};

export function getUserMessage(category: ErrorCategory): string {
  return USER_MESSAGES[category] ?? USER_MESSAGES.unknown;
}

// ── Degraded Mode Detection ───────────────────────────────────────

export interface DegradedModeState {
  isDegraded: boolean;
  reasons: string[];
  since: number;
}

let degradedState: DegradedModeState = { isDegraded: false, reasons: [], since: 0 };

export function enterDegradedMode(reason: string) {
  degradedState = {
    isDegraded: true,
    reasons: [...new Set([...degradedState.reasons, reason])],
    since: degradedState.since || Date.now(),
  };
}

export function exitDegradedMode(reason: string) {
  degradedState = {
    ...degradedState,
    reasons: degradedState.reasons.filter((r) => r !== reason),
    isDegraded: degradedState.reasons.length > 0,
  };
}

export function getDegradedModeState(): DegradedModeState {
  return { ...degradedState };
}

// ── Error Boundary Hook ───────────────────────────────────────────

export function useErrorGovernance() {
  return {
    normalizeApiError,
    normalizeRealtimeError,
    getUserMessage,
    enterDegradedMode,
    exitDegradedMode,
    getDegradedModeState,
  };
}

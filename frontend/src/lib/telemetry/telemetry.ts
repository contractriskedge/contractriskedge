/**
 * Frontend telemetry — operational observability for the enterprise runtime.
 *
 * Tracks:
 * - Route render latency
 * - Widget render latency
 * - API aggregation latency
 * - SSE/WebSocket disconnect frequency
 * - Dashboard refresh duration
 * - Slow drilldowns
 * - Failed mutations
 * - Retry storms
 * - Hydration failures
 * - Stale widget duration
 *
 * Wired to OpenTelemetry via the existing backend OTLP endpoint.
 */

"use client";

import { useEffect, useRef, useCallback } from "react";

// ── Types ─────────────────────────────────────────────────────────

export type TelemetryEventType =
  | "route.render"
  | "widget.render"
  | "api.latency"
  | "realtime.disconnect"
  | "dashboard.refresh"
  | "drilldown.interaction"
  | "mutation.failed"
  | "retry.storm"
  | "hydration.failed"
  | "stale.widget"
  | "error.boundary"
  | "auth.token_refresh";

export interface TelemetryEvent {
  type: TelemetryEventType;
  timestamp: number;
  duration_ms?: number;
  domain?: string;
  widget?: string;
  route?: string;
  error?: string;
  metadata?: Record<string, unknown>;
}

// ── Configuration ─────────────────────────────────────────────────

const TELEMETRY_ENABLED = process.env.NEXT_PUBLIC_TELEMETRY_ENABLED !== "false";
const OTEL_ENDPOINT = process.env.NEXT_PUBLIC_OTEL_ENDPOINT || "/api/v1/telemetry/events";
const BATCH_INTERVAL_MS = 5000; // Flush every 5 seconds
const MAX_BATCH_SIZE = 50;

// ── Telemetry Buffer ──────────────────────────────────────────────

class TelemetryBuffer {
  private events: TelemetryEvent[] = [];
  private flushTimer: ReturnType<typeof setInterval> | null = null;

  push(event: TelemetryEvent) {
    if (!TELEMETRY_ENABLED) return;

    this.events.push(event);

    if (this.events.length >= MAX_BATCH_SIZE) {
      this.flush();
    } else if (!this.flushTimer) {
      this.flushTimer = setInterval(() => this.flush(), BATCH_INTERVAL_MS);
    }
  }

  private async flush() {
    if (this.events.length === 0) return;

    const batch = this.events.splice(0, MAX_BATCH_SIZE);

    try {
      const payload = {
        source: "frontend",
        environment: process.env.NODE_ENV,
        events: batch,
        session_id: getSessionId(),
      };

      // Use sendBeacon for reliability during page unload
      if (navigator.sendBeacon) {
        navigator.sendBeacon(OTEL_ENDPOINT, JSON.stringify(payload));
      } else {
        await fetch(OTEL_ENDPOINT, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
          keepalive: true,
        });
      }
    } catch {
      // Telemetry failures are non-critical — silently drop
    }

    if (this.events.length === 0 && this.flushTimer) {
      clearInterval(this.flushTimer);
      this.flushTimer = null;
    }
  }

  flushNow() {
    this.flush();
  }
}

// Singleton buffer
const buffer = new TelemetryBuffer();

// Flush on page unload
if (typeof window !== "undefined") {
  window.addEventListener("beforeunload", () => buffer.flushNow());
}

// ── Session ID ────────────────────────────────────────────────────

function getSessionId(): string {
  if (typeof window === "undefined") return "";
  let id = sessionStorage.getItem("telemetry_session_id");
  if (!id) {
    id = crypto.randomUUID?.() ?? `${Date.now()}-${Math.random().toString(36).slice(2)}`;
    sessionStorage.setItem("telemetry_session_id", id);
  }
  return id;
}

// ── Public API ────────────────────────────────────────────────────

export function trackEvent(event: TelemetryEvent) {
  buffer.push(event);
}

export function trackRenderLatency(
  type: TelemetryEventType,
  durationMs: number,
  metadata?: Record<string, unknown>,
) {
  buffer.push({
    type,
    timestamp: Date.now(),
    duration_ms: durationMs,
    ...metadata,
  });
}

export function trackApiLatency(
  endpoint: string,
  durationMs: number,
  statusCode: number,
) {
  buffer.push({
    type: "api.latency",
    timestamp: Date.now(),
    duration_ms: durationMs,
    domain: endpoint.split("/")[0],
    metadata: { endpoint, status_code: statusCode },
  });
}

export function trackError(
  errorType: string,
  errorMessage: string,
  metadata?: Record<string, unknown>,
) {
  buffer.push({
    type: "error.boundary",
    timestamp: Date.now(),
    error: errorMessage,
    metadata: { error_type: errorType, ...metadata },
  });
}

// ── React Hook ────────────────────────────────────────────────────

export function useRenderTelemetry(widgetName: string, domain: string) {
  const startRef = useRef<number>(0);

  useEffect(() => {
    startRef.current = performance.now();
    return () => {
      const duration = performance.now() - startRef.current;
      if (duration > 10) {
        // Only track if render took meaningful time
        trackRenderLatency("widget.render", duration, {
          widget: widgetName,
          domain,
        });
      }
    };
  }, [widgetName, domain]);
}

// ── Route Render Tracker ──────────────────────────────────────────

export function useRouteRenderTelemetry(routeName: string) {
  const startRef = useRef(performance.now());

  useEffect(() => {
    startRef.current = performance.now();
  }, [routeName]);

  useEffect(() => {
    return () => {
      const duration = performance.now() - startRef.current;
      trackRenderLatency("route.render", duration, { route: routeName });
    };
  }, [routeName]);
}

// ── Retry Storm Detector ──────────────────────────────────────────

const retryCounts = new Map<string, { count: number; firstSeen: number }>();

export function trackRetry(operationId: string) {
  const now = Date.now();
  const entry = retryCounts.get(operationId);

  if (entry) {
    entry.count++;
    // If 5+ retries in 10 seconds, that's a storm
    if (entry.count >= 5 && now - entry.firstSeen < 10_000) {
      trackEvent({
        type: "retry.storm",
        timestamp: now,
        metadata: {
          operation_id: operationId,
          retry_count: entry.count,
          window_ms: now - entry.firstSeen,
        },
      });
      retryCounts.delete(operationId);
    }
  } else {
    retryCounts.set(operationId, { count: 1, firstSeen: now });
  }

  // Cleanup old entries
  if (retryCounts.size > 100) {
    const cutoff = now - 30_000;
    for (const [key, val] of retryCounts) {
      if (val.firstSeen < cutoff) retryCounts.delete(key);
    }
  }
}

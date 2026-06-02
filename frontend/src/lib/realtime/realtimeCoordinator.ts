/**
 * Real-time event coordinator — bridges WebSocket events to query invalidation.
 *
 * Listens to the existing WebSocket infrastructure and routes events
 * to the invalidation orchestrator. This is the glue between real-time
 * backend events and frontend cache consistency.
 */

"use client";

import { useEffect, useRef } from "react";
import { useAuth } from "@/components/auth/AuthProvider";
import type { InvalidationDomain } from "./invalidationOrchestrator";

export interface RealtimeEvent {
  type: string;
  domain?: InvalidationDomain;
  payload?: Record<string, unknown>;
  timestamp?: number;
}

const EVENT_DOMAIN_MAP: Record<string, InvalidationDomain> = {
  "ingestion.completed": "ingestion",
  "ingestion.failed": "ingestion",
  "review.created": "reviews",
  "review.updated": "reviews",
  "review.completed": "reviews",
  "workflow.updated": "workflows",
  "workflow.completed": "workflows",
  "analysis.completed": "executive-dashboard",
  "analysis.failed": "executive-dashboard",
  "alert.triggered": "executive-alerts",
  "alert.acknowledged": "executive-alerts",
  "anomaly.detected": "anomalies",
  "benchmark.updated": "benchmarks",
  "contract.updated": "contracts",
  "admin.action": "admin",
};

interface RealtimeCoordinatorOptions {
  onInvalidate: (domain: InvalidationDomain, reason: string, source: string) => void;
  enabled?: boolean;
}

export function useRealtimeCoordinator({ onInvalidate, enabled = true }: RealtimeCoordinatorOptions) {
  const { realtimeState: connectionStatus } = useAuth();
  const lastEventRef = useRef<string>("");

  // Route WebSocket messages dispatched by AuthProvider to invalidation orchestrator
  useEffect(() => {
    if (!enabled) return;

    const handler = (e: Event) => {
      try {
        const event = (e as CustomEvent<RealtimeEvent>).detail;
        if (!event?.type) return;

        const eventKey = `${event.type}:${event.timestamp ?? Date.now()}`;
        if (eventKey === lastEventRef.current) return;
        lastEventRef.current = eventKey;

        const domain = event.domain ?? EVENT_DOMAIN_MAP[event.type];
        if (domain) {
          onInvalidate(domain, `realtime:${event.type}`, "realtime-coordinator");
        }
      } catch {
        // Ignore malformed events
      }
    };

    window.addEventListener("realtime-event", handler);
    return () => window.removeEventListener("realtime-event", handler);
  }, [enabled, onInvalidate]);

  return {
    connectionStatus,
    latencyMs: undefined,
    isConnected: connectionStatus === "connected",
  };
}

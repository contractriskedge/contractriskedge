/**
 * Query invalidation orchestrator — centralized runtime coordination.
 *
 * Prevents refetch storms by coordinating cache invalidation across
 * all query domains. All real-time events route through this orchestrator.
 *
 * Instead of each widget calling invalidateQueries independently,
 * they emit domain events here and the orchestrator decides what to refresh.
 */

"use client";

import { useQueryClient } from "@tanstack/react-query";
import { useCallback, useRef } from "react";

export type InvalidationDomain =
  | "executive-dashboard"
  | "executive-kpis"
  | "executive-alerts"
  | "executive-health"
  | "workflows"
  | "reviews"
  | "contracts"
  | "analytics"
  | "anomalies"
  | "ingestion"
  | "benchmarks"
  | "admin";

export type InvalidationEvent = {
  domain: InvalidationDomain;
  reason: string;
  source: string;
  timestamp: number;
};

const DOMAIN_QUERY_KEY_MAP: Record<InvalidationDomain, string[]> = {
  "executive-dashboard": ["executive", "dashboard"],
  "executive-kpis": ["executive", "dashboard"],
  "executive-alerts": ["executive", "anomalies"],
  "executive-health": ["executive", "health-score"],
  "workflows": ["workflows"],
  "reviews": ["reviews"],
  "contracts": ["contracts"],
  "analytics": ["analytics"],
  "anomalies": ["analytics", "errors"],
  "ingestion": ["uploads"],
  "benchmarks": ["benchmarks"],
  "admin": ["admin"],
};

// Cascade map: invalidating one domain may cascade to others
const DOMAIN_CASCADE: Partial<Record<InvalidationDomain, InvalidationDomain[]>> = {
  "executive-dashboard": ["executive-kpis", "executive-alerts"],
  "executive-alerts": ["anomalies"],
  "workflows": ["reviews", "executive-dashboard"],
  "reviews": ["executive-dashboard", "executive-kpis"],
  "ingestion": ["executive-dashboard", "analytics"],
  "anomalies": ["executive-alerts"],
};

export function useInvalidationOrchestrator() {
  const queryClient = useQueryClient();
  const pendingRef = useRef<Map<string, number>>(new Map());
  const DEBOUNCE_MS = 500;

  const invalidate = useCallback(
    (domain: InvalidationDomain, reason: string, source: string) => {
      const eventKey = `${domain}:${reason}`;
      const now = Date.now();
      const last = pendingRef.current.get(eventKey);

      // Debounce: skip if same event fired within DEBOUNCE_MS
      if (last && now - last < DEBOUNCE_MS) return;
      pendingRef.current.set(eventKey, now);

      // Clean up old entries
      if (pendingRef.current.size > 50) {
        const cutoff = now - 5000;
        for (const [key, ts] of pendingRef.current) {
          if (ts < cutoff) pendingRef.current.delete(key);
        }
      }

      // Invalidate primary domain
      const primaryKeys = DOMAIN_QUERY_KEY_MAP[domain];
      if (primaryKeys) {
        queryClient.invalidateQueries({ queryKey: primaryKeys });
      }

      // Cascade to dependent domains
      const cascade = DOMAIN_CASCADE[domain];
      if (cascade) {
        for (const dep of cascade) {
          const depKeys = DOMAIN_QUERY_KEY_MAP[dep];
          if (depKeys) {
            queryClient.invalidateQueries({ queryKey: depKeys });
          }
        }
      }
    },
    [queryClient],
  );

  return { invalidate };
}

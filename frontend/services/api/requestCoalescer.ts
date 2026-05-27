/**
 * Request Coalescer — deduplicates in-flight API requests.
 *
 * When multiple components mount simultaneously and request the same
 * endpoint with the same parameters, this ensures only one actual
 * HTTP request is made. All callers share the same promise.
 *
 * Features:
 * - Request deduplication by URL + method + body
 * - Automatic cleanup of stale entries after configurable TTL
 * - Cancellation support via AbortController
 * - Metrics for monitoring coalescer effectiveness
 *
 * Usage:
 *   import { requestCoalescer } from '@/services/api/requestCoalescer';
 *
 *   // Instead of:
 *   const response = await fetch('/api/reviews/123');
 *
 *   // Use:
 *   const response = await requestCoalescer.dedup(
 *     '/api/reviews/123',
 *     () => fetch('/api/reviews/123').then(r => r.json()),
 *   );
 *
 *   // Two simultaneous calls to the same URL will share one fetch.
 */

"use client";

// ── Types ─────────────────────────────────────────────────────────

type CoalescerKey = string;

type CoalescerEntry = {
  promise: Promise<unknown>;
  createdAt: number;
  callers: number;
};

// ── Configuration ─────────────────────────────────────────────────

const DEFAULT_TTL = 5_000; // 5 seconds — keep coalesced entries for rapid re-mounts
const CLEANUP_INTERVAL = 30_000; // Clean up stale entries every 30s

// ── Metrics ───────────────────────────────────────────────────────

export type CoalescerMetrics = {
  /** Total number of dedup() calls. */
  totalCalls: number;
  /** Number of calls that were deduplicated (shared an in-flight request). */
  deduplicatedCalls: number;
  /** Number of calls that resulted in a new request. */
  uniqueCalls: number;
  /** Current number of entries in the coalescer. */
  activeEntries: number;
  /** Cache hit rate (0-1). */
  hitRate: number;
};

let metrics: CoalescerMetrics = {
  totalCalls: 0,
  deduplicatedCalls: 0,
  uniqueCalls: 0,
  activeEntries: 0,
  hitRate: 0,
};

export function getCoalescerMetrics(): CoalescerMetrics {
  return { ...metrics };
}

// ── Coalescer ─────────────────────────────────────────────────────

class RequestCoalescer {
  private entries = new Map<CoalescerKey, CoalescerEntry>();
  private cleanupTimer: ReturnType<typeof setInterval> | null = null;

  constructor() {
    // Periodic cleanup of stale entries
    if (typeof window !== "undefined") {
      this.cleanupTimer = setInterval(() => {
        this.cleanup();
      }, CLEANUP_INTERVAL);
    }
  }

  /**
   * Build a coalescer key from request parameters.
   */
  private buildKey(
    url: string,
    method: string = "GET",
    body?: unknown,
  ): CoalescerKey {
    const bodyKey = body ? JSON.stringify(body) : "";
    return `${method}:${url}:${bodyKey}`;
  }

  /**
   * Deduplicate an in-flight request.
   *
   * If a request with the same key is already in flight, returns the
   * existing promise. Otherwise, executes the factory function and
   * caches the promise.
   *
   * @param url - The request URL (used for dedup key)
   * @param factory - Function that returns a promise for the request
   * @param options - Optional configuration
   * @returns The response promise
   */
  async dedup<T>(
    url: string,
    factory: () => Promise<T>,
    options?: {
      method?: string;
      body?: unknown;
      /** Custom TTL for this entry in ms. Default: 5000 */
      ttl?: number;
      /** AbortSignal for cancellation. */
      signal?: AbortSignal;
    },
  ): Promise<T> {
    metrics.totalCalls++;
    const key = this.buildKey(url, options?.method ?? "GET", options?.body);

    // Check for existing in-flight request
    const existing = this.entries.get(key);
    if (existing) {
      metrics.deduplicatedCalls++;
      existing.callers++;
      return existing.promise as Promise<T>;
    }

    // Create new entry
    metrics.uniqueCalls++;
    const entry: CoalescerEntry = {
      promise: factory(),
      createdAt: Date.now(),
      callers: 1,
    };

    this.entries.set(key, entry);
    metrics.activeEntries = this.entries.size;
    this.updateHitRate();

    // Handle cancellation via AbortSignal
    if (options?.signal) {
      options.signal.addEventListener("abort", () => {
        this.entries.delete(key);
        metrics.activeEntries = this.entries.size;
        this.updateHitRate();
      });
    }

    // Clean up after the promise resolves
    try {
      const result = await entry.promise;
      // Keep the entry in cache for the TTL to handle rapid re-mounts
      setTimeout(() => {
        // Only remove if no new request has been made with the same key
        if (this.entries.get(key) === entry) {
          this.entries.delete(key);
          metrics.activeEntries = this.entries.size;
          this.updateHitRate();
        }
      }, options?.ttl ?? DEFAULT_TTL);
      return result as T;
    } catch (error) {
      // On failure, remove immediately so retries create a new request
      this.entries.delete(key);
      metrics.activeEntries = this.entries.size;
      this.updateHitRate();
      throw error;
    }
  }

  /**
   * Check if a request with the given parameters is currently in-flight.
   */
  isInFlight(url: string, method: string = "GET", body?: unknown): boolean {
    const key = this.buildKey(url, method, body);
    return this.entries.has(key);
  }

  /**
   * Cancel all in-flight requests matching a URL prefix.
   * Useful for stale request cancellation during navigation.
   */
  cancelByPrefix(urlPrefix: string): void {
    for (const [key, entry] of this.entries.entries()) {
      if (key.includes(urlPrefix)) {
        this.entries.delete(key);
      }
    }
    metrics.activeEntries = this.entries.size;
    this.updateHitRate();
  }

  /**
   * Clear all coalesced entries.
   */
  clear(): void {
    this.entries.clear();
    metrics.activeEntries = 0;
    this.updateHitRate();
  }

  /**
   * Remove stale entries that exceed the TTL.
   */
  private cleanup(): void {
    const now = Date.now();
    for (const [key, entry] of this.entries.entries()) {
      // Remove entries older than 30s that have no active callers
      if (now - entry.createdAt > 30_000 && entry.callers === 0) {
        this.entries.delete(key);
      }
    }
    metrics.activeEntries = this.entries.size;
    this.updateHitRate();
  }

  private updateHitRate(): void {
    metrics.hitRate = metrics.totalCalls > 0
      ? metrics.deduplicatedCalls / metrics.totalCalls
      : 0;
  }

  /**
   * Clean up the cleanup interval.
   */
  destroy(): void {
    if (this.cleanupTimer) {
      clearInterval(this.cleanupTimer);
      this.cleanupTimer = null;
    }
    this.entries.clear();
  }
}

// ── Singleton ─────────────────────────────────────────────────────

export const requestCoalescer = new RequestCoalescer();

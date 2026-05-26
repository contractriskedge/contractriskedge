/**
 * AnalyticsEventBus — typed publish/subscribe event system for cross-widget coordination.
 *
 * Events:
 * - RISK_SELECTED: { level: string }
 * - CLAUSE_SELECTED: { clauseType: string }
 * - CONTRACT_SELECTED: { contractId: string, contractName?: string }
 * - TIME_RANGE_CHANGED: { range: string }
 * - FINDING_SELECTED: { findingId: string, reviewId?: string }
 * - NAVIGATE_TO_REVIEW: { reviewId: string }
 * - NAVIGATE_TO_SEARCH: { query: string }
 * - WIDGET_REFRESH: { widgetId: string }
 * - EXPORT_REQUESTED: { widgetId: string, format: string }
 *
 * Usage:
 *   import { analyticsBus, AnalyticsEvent } from "./AnalyticsEventBus";
 *   analyticsBus.on("RISK_SELECTED", (data) => { ... });
 *   analyticsBus.emit("RISK_SELECTED", { level: "critical" });
 */

"use client";

// ── Event Types ─────────────────────────────────────────────────

export type AnalyticsEventType =
  | "RISK_SELECTED"
  | "CLAUSE_SELECTED"
  | "CONTRACT_SELECTED"
  | "TIME_RANGE_CHANGED"
  | "FINDING_SELECTED"
  | "NAVIGATE_TO_REVIEW"
  | "NAVIGATE_TO_SEARCH"
  | "WIDGET_REFRESH"
  | "EXPORT_REQUESTED"
  | "DASHBOARD_RESET";

export interface AnalyticsEventMap {
  RISK_SELECTED: { level: string };
  CLAUSE_SELECTED: { clauseType: string };
  CONTRACT_SELECTED: { contractId: string; contractName?: string };
  TIME_RANGE_CHANGED: { range: string };
  FINDING_SELECTED: { findingId: string; reviewId?: string };
  NAVIGATE_TO_REVIEW: { reviewId: string };
  NAVIGATE_TO_SEARCH: { query: string };
  WIDGET_REFRESH: { widgetId: string };
  EXPORT_REQUESTED: { widgetId: string; format: string };
  DASHBOARD_RESET: {};
}

type EventCallback<T> = (data: T) => void;

// ── Event Bus ────────────────────────────────────────────────────

class AnalyticsEventBus {
  private listeners: Map<string, Set<EventCallback<any>>> = new Map();
  private history: Array<{ type: string; data: any; timestamp: number }> = [];
  private maxHistory = 50;

  /**
   * Subscribe to an event. Returns an unsubscribe function.
   */
  on<T extends AnalyticsEventType>(
    eventType: T,
    callback: EventCallback<AnalyticsEventMap[T]>,
  ): () => void {
    if (!this.listeners.has(eventType)) {
      this.listeners.set(eventType, new Set());
    }
    this.listeners.get(eventType)!.add(callback);

    // Return unsubscribe function
    return () => {
      this.listeners.get(eventType)?.delete(callback);
    };
  }

  /**
   * Subscribe to an event, but only fire once.
   */
  once<T extends AnalyticsEventType>(
    eventType: T,
    callback: EventCallback<AnalyticsEventMap[T]>,
  ): () => void {
    const wrapped = (data: AnalyticsEventMap[T]) => {
      unsubscribe();
      callback(data);
    };
    const unsubscribe = this.on(eventType, wrapped);
    return unsubscribe;
  }

  /**
   * Emit an event to all subscribers.
   */
  emit<T extends AnalyticsEventType>(
    eventType: T,
    data: AnalyticsEventMap[T],
  ): void {
    // Store in history
    this.history.push({ type: eventType, data, timestamp: Date.now() });
    if (this.history.length > this.maxHistory) {
      this.history.shift();
    }

    // Notify listeners
    const callbacks = this.listeners.get(eventType);
    if (callbacks) {
      callbacks.forEach((cb) => {
        try {
          cb(data);
        } catch (err) {
          console.error(`[AnalyticsEventBus] Error in ${eventType} handler:`, err);
        }
      });
    }
  }

  /**
   * Remove all listeners for an event type.
   */
  clear(eventType?: AnalyticsEventType): void {
    if (eventType) {
      this.listeners.delete(eventType);
    } else {
      this.listeners.clear();
    }
  }

  /**
   * Get recent event history for debugging.
   */
  getHistory(): Array<{ type: string; data: any; timestamp: number }> {
    return [...this.history];
  }

  /**
   * Get count of listeners for an event type.
   */
  listenerCount(eventType: AnalyticsEventType): number {
    return this.listeners.get(eventType)?.size ?? 0;
  }
}

// ── Singleton ────────────────────────────────────────────────────

export const analyticsBus = new AnalyticsEventBus();

// ── React Hook ───────────────────────────────────────────────────

import { useEffect } from "react";

/**
 * React hook to subscribe to analytics events.
 * Automatically unsubscribes on unmount.
 *
 * Usage:
 *   useAnalyticsEvent("RISK_SELECTED", (data) => {
 *     setRiskFilter(data.level);
 *   });
 */
export function useAnalyticsEvent<T extends AnalyticsEventType>(
  eventType: T,
  callback: EventCallback<AnalyticsEventMap[T]>,
): void {
  useEffect(() => {
    const unsubscribe = analyticsBus.on(eventType, callback);
    return unsubscribe;
  }, [eventType, callback]);
}

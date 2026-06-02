/**
 * Operational state banners — top-level system awareness indicators.
 *
 * Shows persistent banners for:
 * - AI provider degraded
 * - Replay validation backlog
 * - High SLA breach volume
 * - System in maintenance mode
 * - OpenTelemetry disconnected
 * - Tenant isolation warning
 */

"use client";

import React, { useState, useCallback } from "react";
import { useAuth } from "@/components/auth/AuthProvider";
import { getDegradedModeState } from "@/src/lib/errors/errorGovernance";
import { AlertTriangle, WifiOff, RefreshCw, Shield, Wrench, Activity } from "lucide-react";

// ── Banner Types ──────────────────────────────────────────────────

interface OperationalBanner {
  id: string;
  message: string;
  severity: "critical" | "high" | "medium" | "low";
  icon: React.ReactNode;
  dismissable: boolean;
  action?: { label: string; onClick: () => void };
}

// ── Hook ──────────────────────────────────────────────────────────

export function useOperationalBanners() {
  // WebSocket is owned by AuthProvider — read connection state only
  const { realtimeState: connectionStatus } = useAuth();
  const latencyMs: number | undefined = undefined;
  const [dismissed, setDismissed] = useState<Set<string>>(new Set());
  const [maintenanceMode, setMaintenanceMode] = useState(false);

  const dismiss = useCallback((id: string) => {
    setDismissed((prev) => new Set([...prev, id]));
  }, []);

  const banners: OperationalBanner[] = [];

  // 1. WebSocket disconnected
  if (connectionStatus === "disconnected" || connectionStatus === "failed") {
    banners.push({
      id: "realtime-disconnected",
      message: "Live updates disconnected. Reconnecting...",
      severity: "high",
      icon: <WifiOff className="w-4 h-4" />,
      dismissable: false,
    });
  }

  // 2. High latency
  if (connectionStatus === "connected" && latencyMs && latencyMs > 1000) {
    banners.push({
      id: "high-latency",
      message: `Real-time latency high (${latencyMs}ms). Performance may be degraded.`,
      severity: "medium",
      icon: <Activity className="w-4 h-4" />,
      dismissable: true,
      action: { label: "Dismiss", onClick: () => dismiss("high-latency") },
    });
  }

  // 3. Degraded mode (from error governance)
  const degraded = getDegradedModeState();
  if (degraded.isDegraded) {
    banners.push({
      id: "degraded-mode",
      message: `System operating in degraded mode: ${degraded.reasons.join(", ")}`,
      severity: "critical",
      icon: <AlertTriangle className="w-4 h-4" />,
      dismissable: false,
    });
  }

  // 4. Maintenance mode (set externally)
  if (maintenanceMode) {
    banners.push({
      id: "maintenance-mode",
      message: "System is in maintenance mode. Some features may be unavailable.",
      severity: "high",
      icon: <Wrench className="w-4 h-4" />,
      dismissable: true,
      action: { label: "Dismiss", onClick: () => dismiss("maintenance-mode") },
    });
  }

  return {
    banners: banners.filter((b) => !dismissed.has(b.id)),
    setMaintenanceMode,
    dismiss,
  };
}

// ── Banner Component ──────────────────────────────────────────────

const SEVERITY_STYLES = {
  critical: "bg-red-50 border-red-200 text-red-800 dark:bg-red-900/20 dark:border-red-800 dark:text-red-300",
  high: "bg-orange-50 border-orange-200 text-orange-800 dark:bg-orange-900/20 dark:border-orange-800 dark:text-orange-300",
  medium: "bg-yellow-50 border-yellow-200 text-yellow-800 dark:bg-yellow-900/20 dark:border-yellow-800 dark:text-yellow-300",
  low: "bg-blue-50 border-blue-200 text-blue-800 dark:bg-blue-900/20 dark:border-blue-800 dark:text-blue-300",
};

export function OperationalBannerBar() {
  const { banners } = useOperationalBanners();

  if (banners.length === 0) return null;

  return (
    <div className="space-y-1 px-4 py-2">
      {banners.map((banner) => (
        <div
          key={banner.id}
          className={`flex items-center gap-2 px-3 py-2 rounded-lg border text-xs ${SEVERITY_STYLES[banner.severity]}`}
          role="alert"
        >
          <span className="flex-shrink-0">{banner.icon}</span>
          <span className="flex-1">{banner.message}</span>
          {banner.action && (
            <button
              onClick={banner.action.onClick}
              className="font-medium underline hover:no-underline flex-shrink-0"
            >
              {banner.action.label}
            </button>
          )}
        </div>
      ))}
    </div>
  );
}

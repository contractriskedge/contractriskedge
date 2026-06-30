/**
 * StatusBadge — Consistent badge hierarchy for status indicators.
 *
 * Hierarchy:
 * - primary: Large, prominent — used for top-level statuses (Approved, Completed, etc.)
 * - secondary: Smaller — used for sub-statuses (Open, Pending, etc.)
 * - informational: Subtle, muted — used for tags, labels, metadata
 *
 * Usage:
 *   <StatusBadge variant="primary" status="approved" />
 *   <StatusBadge variant="secondary" status="open" />
 *   <StatusBadge variant="informational" label="v2.3" />
 */

"use client";

import React from "react";

type BadgeVariant = "primary" | "secondary" | "informational";

type BadgeColor =
  | "green"
  | "blue"
  | "amber"
  | "red"
  | "gray"
  | "purple"
  | "cyan"
  | "orange"
  | "teal"
  | "indigo"
  | "rose";

interface StatusBadgeProps {
  variant?: BadgeVariant;
  status?: string;
  label?: string;
  color?: BadgeColor;
  count?: number;
  className?: string;
}

// ── Color Maps ──────────────────────────────────────────────────────────────

const STATUS_COLOR_MAP: Record<string, BadgeColor> = {
  approved: "green",
  completed: "green",
  finalized: "green",
  executed: "green",
  active: "green",
  resolved: "green",
  success: "green",
  open: "amber",
  pending: "amber",
  in_review: "blue",
  in_progress: "blue",
  "in progress": "blue",
  review: "blue",
  draft: "gray",
  ai_analyzed: "gray",
  archived: "indigo",
  closed: "gray",
  expired: "red",
  critical: "red",
  escalated: "red",
  overdue: "red",
  failed: "red",
  rejected: "red",
  warning: "orange",
  expiring_soon: "orange",
  expiring: "orange",
  info: "cyan",
  informational: "cyan",
  high: "orange",
  medium: "amber",
  low: "gray",
};

const VARIANT_STYLES: Record<BadgeVariant, string> = {
  primary: "px-2.5 py-1 text-[10px] font-bold",
  secondary: "px-2 py-0.5 text-[9px] font-semibold",
  informational: "px-1.5 py-0.5 text-[8px] font-medium",
};

const COLOR_STYLES: Record<BadgeColor, { bg: string; text: string; dot?: string }> = {
  green: { bg: "bg-green-100 dark:bg-green-900/20", text: "text-green-700 dark:text-green-300", dot: "bg-green-500" },
  blue: { bg: "bg-blue-100 dark:bg-blue-900/20", text: "text-blue-700 dark:text-blue-300", dot: "bg-blue-500" },
  amber: { bg: "bg-amber-100 dark:bg-amber-900/20", text: "text-amber-700 dark:text-amber-300", dot: "bg-amber-500" },
  red: { bg: "bg-red-100 dark:bg-red-900/20", text: "text-red-700 dark:text-red-300", dot: "bg-red-500" },
  gray: { bg: "bg-gray-100 dark:bg-gray-800", text: "text-gray-600 dark:text-gray-400", dot: "bg-gray-400" },
  purple: { bg: "bg-purple-100 dark:bg-purple-900/20", text: "text-purple-700 dark:text-purple-300", dot: "bg-purple-500" },
  cyan: { bg: "bg-cyan-100 dark:bg-cyan-900/20", text: "text-cyan-700 dark:text-cyan-300", dot: "bg-cyan-500" },
  orange: { bg: "bg-orange-100 dark:bg-orange-900/20", text: "text-orange-700 dark:text-orange-300", dot: "bg-orange-500" },
  teal: { bg: "bg-teal-100 dark:bg-teal-900/20", text: "text-teal-700 dark:text-teal-300", dot: "bg-teal-500" },
  indigo: { bg: "bg-indigo-100 dark:bg-indigo-900/20", text: "text-indigo-700 dark:text-indigo-300", dot: "bg-indigo-500" },
  rose: { bg: "bg-rose-100 dark:bg-rose-900/20", text: "text-rose-700 dark:text-rose-300", dot: "bg-rose-500" },
};

// ── Helpers ─────────────────────────────────────────────────────────────────

function resolveColor(status?: string, color?: BadgeColor): BadgeColor {
  if (color) return color;
  if (status) {
    const normalized = status.toLowerCase().replace(/\s+/g, "_");
    return STATUS_COLOR_MAP[normalized] ?? STATUS_COLOR_MAP[status.toLowerCase()] ?? "gray";
  }
  return "gray";
}

function formatLabel(status?: string, label?: string): string {
  if (label) return label;
  if (status) return status.replace(/_/g, " ");
  return "—";
}

// ── Component ───────────────────────────────────────────────────────────────

export function StatusBadge({
  variant = "secondary",
  status,
  label,
  color,
  count,
  className = "",
}: StatusBadgeProps) {
  const resolvedColor = resolveColor(status, color);
  const styles = COLOR_STYLES[resolvedColor];
  const variantStyle = VARIANT_STYLES[variant];
  const displayLabel = formatLabel(status, label);

  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full ${styles.bg} ${styles.text} ${variantStyle} ${className}`}
    >
      {variant !== "informational" && (
        <span className={`w-1.5 h-1.5 rounded-full ${styles.dot} flex-shrink-0`} aria-hidden="true" />
      )}
      <span>{displayLabel}</span>
      {count !== undefined && count > 0 && (
        <span className={`ml-0.5 ${variant === "primary" ? "text-[9px]" : "text-[7px]"} opacity-70`}>
          {count}
        </span>
      )}
    </span>
  );
}

/**
 * Date formatting helpers.
 *
 * The backend may return null/empty for any date field. We always want to
 * render a friendly placeholder instead of "Invalid Date" leaking into the UI.
 */

const PLACEHOLDER = "Not Available";

/**
 * Safely format a date string for display.
 * - Returns "Not Available" for null/undefined/empty/invalid dates
 * - Returns a localized short date for valid dates
 */
export function formatDate(
  value: string | null | undefined,
  options: Intl.DateTimeFormatOptions = { year: "numeric", month: "short", day: "numeric" },
): string {
  if (value === null || value === undefined) return PLACEHOLDER;
  const trimmed = String(value).trim();
  if (!trimmed || trimmed === "null" || trimmed === "undefined") return PLACEHOLDER;
  const d = new Date(trimmed);
  if (Number.isNaN(d.getTime())) return PLACEHOLDER;
  return d.toLocaleDateString(undefined, options);
}

/**
 * Returns true if the date is missing or invalid.
 */
export function isMissingDate(value: string | null | undefined): boolean {
  if (value === null || value === undefined) return true;
  const trimmed = String(value).trim();
  if (!trimmed || trimmed === "null" || trimmed === "undefined") return true;
  const d = new Date(trimmed);
  return Number.isNaN(d.getTime());
}

/**
 * Format a date or return the placeholder.
 */
export const formatDateOrDash = (value: string | null | undefined): string => formatDate(value);

/**
 * Format a date for the table column (short).
 */
export function formatDateShort(value: string | null | undefined): string {
  return formatDate(value, { year: "numeric", month: "2-digit", day: "2-digit" });
}

/**
 * Format a timestamp as a relative time string (e.g., "5m ago", "2h ago").
 */
export function formatTime(ts: string | null | undefined): string {
  if (!ts) return "—";
  const t = new Date(ts).getTime();
  if (Number.isNaN(t)) return "—";
  const diff = Date.now() - t;
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

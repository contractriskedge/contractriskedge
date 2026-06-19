/**
 * UserPicker — DB-backed user/assignee chooser for the contract review platform.
 *
 * Pulls active tenant users from `/reviews/assignees` and renders a search-first
 * combobox with role grouping, avatars, and contextual metadata
 * (email, role, active-review workload when available).
 *
 * Used by:
 *  - ReviewQueue → "Assign Reviewer" modal
 *  - ReviewActions → Assign / Reassign modals
 *  - ReviewMoreActionsMenu → "Assign Reviewer" in the More Actions dropdown
 *  - WorkflowSection → Advance-stage + Reassign modals
 *
 * Replaces all free-text `assigneeId` inputs that previously required
 * users to type `user-001 or reviewer@company.com` by hand.
 */

"use client";

import React, { useMemo, useState, useRef, useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { motion, AnimatePresence } from "framer-motion";
import {
  Search, User, X, Check, ChevronDown, Loader2,
  Briefcase, Shield, GavelIcon, Users, UserCog, Crown, Eye,
} from "lucide-react";
import { api } from "@/services/api/client";

// ── Types ─────────────────────────────────────────────────────────

export interface PickerUser {
  user_id: string;
  email: string;
  name: string;
  role: string;
  business_unit?: string | null;
  is_active: boolean;
  active_reviews?: number;
  workload_pct?: number;
}

interface UserPickerProps {
  /** Currently selected user_id. */
  value: string;
  /** Called when the selection changes. */
  onChange: (userId: string) => void;
  /**
   * Optional richer callback that returns the full user object whenever the
   * selection changes. Useful for parents that need the user's name/email
   * for optimistic UI updates.
   */
  onSelectUser?: (user: PickerUser | null) => void;
  /** Restrict the picker to specific roles. Default: any active user. */
  allowedRoles?: string[];
  /** Optional placeholder. */
  placeholder?: string;
  /** Whether the picker is disabled. */
  disabled?: boolean;
  /** Tailwind class overrides for sizing. */
  size?: "xs" | "sm" | "md";
  /** Show a "None / unassign" option at the top. */
  allowNone?: boolean;
  /** Label shown for the none option. */
  noneLabel?: string;
  /** Optional id for the underlying button (a11y). */
  id?: string;
  /** Optional error class for the border. */
  hasError?: boolean;
  /**
   * If provided, the user list is augmented with this active-review count
   * (overrides any value from the workload endpoint).
   */
  reviewerWorkloads?: Array<{ user_id: string; active_reviews: number; workload_pct?: number }>;
}

// ── Role metadata ─────────────────────────────────────────────────

const ROLE_LABELS: Record<string, string> = {
  tenant_admin: "Tenant Admin",
  admin: "Administrator",
  legal_ops: "Legal Ops",
  legal_reviewer: "Legal Reviewer",
  reviewer: "Reviewer",
  compliance: "Compliance",
  executive: "Executive",
  viewer: "Viewer",
  ai_ops: "AI Ops",
  approver: "Approver",
  observer: "Observer",
};

const ROLE_ORDER: string[] = [
  "tenant_admin",
  "executive",
  "legal_ops",
  "legal_reviewer",
  "compliance",
  "reviewer",
  "admin",
  "ai_ops",
  "viewer",
  "approver",
  "observer",
];

function RoleIcon({ role, className }: { role: string; className?: string }) {
  const cls = className ?? "w-3 h-3";
  switch (role) {
    case "tenant_admin": return <Crown className={cls} />;
    case "executive": return <Crown className={cls} />;
    case "legal_ops": return <GavelIcon className={cls} />;
    case "legal_reviewer": return <GavelIcon className={cls} />;
    case "compliance": return <Shield className={cls} />;
    case "reviewer": return <UserCog className={cls} />;
    case "admin": return <Briefcase className={cls} />;
    case "observer": return <Eye className={cls} />;
    default: return <User className={cls} />;
  }
}

function getInitials(name: string): string {
  if (!name) return "??";
  const parts = name.trim().split(/\s+/);
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}

// ── The component ─────────────────────────────────────────────────

export function UserPicker({
  value,
  onChange,
  onSelectUser,
  allowedRoles,
  placeholder = "Select a user…",
  disabled = false,
  size = "md",
  allowNone = false,
  noneLabel = "— Unassigned —",
  id,
  hasError = false,
  reviewerWorkloads,
}: UserPickerProps) {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState("");
  const [activeIndex, setActiveIndex] = useState(0);
  const containerRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLDivElement>(null);

  // Fetch assignable users — workflows:write (reviewers) not users:read (admin only).
  const { data: users = [], isLoading, error } = useQuery({
    queryKey: ["reviews", "assignees", "picker", allowedRoles?.slice().sort().join(",")],
    queryFn: async () => {
      const res = await api.get<Array<{
        user_id: string;
        email: string;
        name: string | null;
        role: string;
        business_unit: string | null;
        is_active: boolean;
      }>>("/reviews/assignees");
      return res.map((u) => ({
        user_id: u.user_id,
        email: u.email,
        name: u.name || u.email,
        role: u.role,
        business_unit: u.business_unit,
        is_active: u.is_active,
      })) satisfies PickerUser[];
    },
    staleTime: 60_000,
  });

  // Augment with workload metadata when supplied
  const enrichedUsers = useMemo<PickerUser[]>(() => {
    if (!reviewerWorkloads?.length) return users;
    const loadMap = new Map(
      reviewerWorkloads.map((w) => [w.user_id, w])
    );
    return users.map((u) => {
      const wl = loadMap.get(u.user_id);
      return wl
        ? { ...u, active_reviews: wl.active_reviews, workload_pct: wl.workload_pct }
        : u;
    });
  }, [users, reviewerWorkloads]);

  // Apply role filter + active filter
  const allowed = useMemo(() => {
    let list = enrichedUsers.filter((u) => u.is_active);
    if (allowedRoles && allowedRoles.length > 0) {
      const allowedSet = new Set(allowedRoles);
      list = list.filter((u) => allowedSet.has(u.role));
    }
    return list;
  }, [enrichedUsers, allowedRoles]);

  // Apply search filter
  const filtered = useMemo(() => {
    if (!search.trim()) return allowed;
    const q = search.toLowerCase();
    return allowed.filter(
      (u) =>
        u.name.toLowerCase().includes(q) ||
        u.email.toLowerCase().includes(q) ||
        ROLE_LABELS[u.role]?.toLowerCase().includes(q) ||
        (u.business_unit || "").toLowerCase().includes(q)
    );
  }, [allowed, search]);

  // Group by role for display
  const grouped = useMemo(() => {
    const groups: Record<string, PickerUser[]> = {};
    filtered.forEach((u) => {
      if (!groups[u.role]) groups[u.role] = [];
      groups[u.role].push(u);
    });
    // Sort by ROLE_ORDER then by name
    return Object.entries(groups)
      .sort(([a], [b]) => {
        const ai = ROLE_ORDER.indexOf(a);
        const bi = ROLE_ORDER.indexOf(b);
        return (ai === -1 ? 999 : ai) - (bi === -1 ? 999 : bi);
      })
      .map(([role, items]) => [
        role,
        items.sort((a, b) => a.name.localeCompare(b.name)),
      ] as [string, PickerUser[]]);
  }, [filtered]);

  // Flat list for keyboard navigation
  const flatList = useMemo(() => {
    const out: Array<PickerUser | { none: true }> = [];
    if (allowNone) out.push({ none: true });
    grouped.forEach(([, items]) => items.forEach((u) => out.push(u)));
    return out;
  }, [grouped, allowNone]);

  const selectedUser = useMemo(
    () => allowed.find((u) => u.user_id === value),
    [allowed, value]
  );

  // ── Click-outside to close ──
  useEffect(() => {
    if (!open) return;
    const handler = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
        setSearch("");
        setActiveIndex(0);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [open]);

  // ── Auto-focus search when opened ──
  useEffect(() => {
    if (open) {
      // Slight delay so the input is mounted
      const t = setTimeout(() => inputRef.current?.focus(), 30);
      return () => clearTimeout(t);
    }
  }, [open]);

  // ── Reset active index when search changes ──
  useEffect(() => {
    setActiveIndex(allowNone ? 1 : 0);
  }, [search, allowNone]);

  // ── Scroll active item into view ──
  useEffect(() => {
    if (!open || !listRef.current) return;
    const el = listRef.current.querySelector<HTMLElement>(
      `[data-pick-index="${activeIndex}"]`
    );
    if (el) {
      el.scrollIntoView({ block: "nearest" });
    }
  }, [activeIndex, open]);

  // ── Size tokens ──
  const sizeClasses = {
    xs: "text-[10px] py-1 px-2",
    sm: "text-[11px] py-1.5 px-2.5",
    md: "text-xs py-2 px-3",
  }[size];

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActiveIndex((i) => Math.min(i + 1, flatList.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActiveIndex((i) => Math.max(i - 1, 0));
    } else if (e.key === "Enter") {
      e.preventDefault();
      const item = flatList[activeIndex];
      if (!item) return;
      if ("none" in item) {
        onChange("");
        onSelectUser?.(null);
      } else {
        onChange(item.user_id);
        onSelectUser?.(item);
      }
      setOpen(false);
      setSearch("");
    } else if (e.key === "Escape") {
      e.preventDefault();
      setOpen(false);
      setSearch("");
    }
  };

  const selectUser = (u: PickerUser) => {
    onChange(u.user_id);
    onSelectUser?.(u);
    setOpen(false);
    setSearch("");
  };

  return (
    <div ref={containerRef} className="relative w-full" data-user-picker>
      {/* Trigger button */}
      <button
        id={id}
        type="button"
        disabled={disabled}
        onClick={() => !disabled && setOpen((o) => !o)}
        className={`w-full flex items-center justify-between gap-2 rounded-lg border ${sizeClasses} text-left transition-colors ${
          hasError
            ? "border-red-400 focus:border-red-500 focus:ring-1 focus:ring-red-200"
            : "border-gray-300 dark:border-gray-600 focus:border-blue-500 focus:ring-1 focus:ring-blue-200"
        } ${
          disabled
            ? "bg-gray-100 dark:bg-gray-800 cursor-not-allowed opacity-60"
            : "bg-white dark:bg-gray-700 hover:border-gray-400"
        } ${open ? "ring-1 ring-blue-300 border-blue-400" : ""}`}
      >
        {selectedUser ? (
          <span className="flex items-center gap-2 min-w-0 flex-1">
            <span className="flex-shrink-0 w-5 h-5 rounded-full bg-gradient-to-br from-blue-500 to-indigo-600 text-white text-[9px] font-semibold flex items-center justify-center">
              {getInitials(selectedUser.name)}
            </span>
            <span className="truncate text-gray-900 dark:text-gray-100">
              {selectedUser.name}
            </span>
            <span className="hidden sm:inline text-[9px] uppercase tracking-wider font-semibold text-gray-500 dark:text-gray-400 flex-shrink-0">
              {ROLE_LABELS[selectedUser.role] || selectedUser.role}
            </span>
          </span>
        ) : (
          <span className="flex items-center gap-2 text-gray-500 dark:text-gray-400 min-w-0 flex-1">
            <User className="w-3.5 h-3.5 flex-shrink-0" />
            <span className="truncate">{placeholder}</span>
          </span>
        )}
        <span className="flex items-center gap-1 flex-shrink-0">
          {value && !disabled && (
            <span
              role="button"
              aria-label="Clear selection"
              onClick={(e) => {
                e.stopPropagation();
                onChange("");
                onSelectUser?.(null);
              }}
              className="p-0.5 rounded hover:bg-gray-200 dark:hover:bg-gray-600 text-gray-400 hover:text-gray-600"
            >
              <X className="w-3 h-3" />
            </span>
          )}
          <ChevronDown
            className={`w-3.5 h-3.5 text-gray-400 transition-transform ${
              open ? "rotate-180" : ""
            }`}
          />
        </span>
      </button>

      {/* Dropdown */}
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: -4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -4 }}
            transition={{ duration: 0.1 }}
            className="absolute z-[100] mt-1 w-full rounded-lg border border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-800 shadow-xl overflow-hidden"
          >
            {/* Search input */}
            <div className="p-2 border-b border-gray-100 dark:border-gray-700">
              <div className="relative">
                <Search className="absolute left-2 top-1/2 -translate-y-1/2 w-3 h-3 text-gray-400" />
                <input
                  ref={inputRef}
                  type="text"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="Search by name, email, role…"
                  className="w-full pl-7 pr-2 py-1.5 text-xs border border-gray-200 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:border-blue-400"
                />
              </div>
            </div>

            {/* Results list */}
            <div ref={listRef} className="max-h-64 overflow-y-auto py-1">
              {isLoading && (
                <div className="flex items-center justify-center gap-2 py-6 text-[11px] text-gray-500">
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  Loading users from database…
                </div>
              )}

              {error && !isLoading && (
                <div className="px-3 py-4 text-[11px] text-red-600 text-center">
                  Failed to load users. Check connection.
                </div>
              )}

              {!isLoading && !error && grouped.length === 0 && (
                <div className="flex flex-col items-center justify-center gap-1 py-6 text-[11px] text-gray-500">
                  <Users className="w-5 h-5 text-gray-300" />
                  <span>
                    {search
                      ? `No users matching "${search}"`
                      : "No active users available"}
                  </span>
                </div>
              )}

              {/* None option */}
              {allowNone && !search.trim() && (
                <button
                  type="button"
                  data-pick-index="0"
                  onClick={() => {
                    onChange("");
                    onSelectUser?.(null);
                    setOpen(false);
                    setSearch("");
                  }}
                  onMouseEnter={() => setActiveIndex(0)}
                  className={`w-full text-left px-3 py-1.5 text-[11px] flex items-center gap-2 ${
                    activeIndex === 0
                      ? "bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300"
                      : "text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700"
                  }`}
                >
                  <span className="w-5 h-5 rounded-full border-2 border-dashed border-gray-300 flex items-center justify-center">
                    <X className="w-2.5 h-2.5 text-gray-400" />
                  </span>
                  <span className="italic">{noneLabel}</span>
                  {!value && <Check className="w-3 h-3 ml-auto text-blue-600" />}
                </button>
              )}

              {/* Grouped users */}
              {grouped.map(([role, items], groupIdx) => {
                let runningIndex = allowNone ? 1 : 0;
                for (let g = 0; g < groupIdx; g++) {
                  runningIndex += grouped[g][1].length;
                }
                return (
                  <div key={role} className="py-0.5">
                    <div className="px-3 py-1 text-[9px] font-bold uppercase tracking-wider text-gray-400 dark:text-gray-500 flex items-center gap-1">
                      <RoleIcon role={role} className="w-2.5 h-2.5" />
                      {ROLE_LABELS[role] || role}
                      <span className="ml-1 text-gray-300 dark:text-gray-600">
                        ({items.length})
                      </span>
                    </div>
                    {items.map((u, itemIdx) => {
                      const pickIndex = runningIndex + itemIdx;
                      const isActive = activeIndex === pickIndex;
                      const isSelected = value === u.user_id;
                      return (
                        <button
                          key={u.user_id}
                          type="button"
                          data-pick-index={pickIndex}
                          onClick={() => selectUser(u)}
                          onMouseEnter={() => setActiveIndex(pickIndex)}
                          className={`w-full text-left px-3 py-1.5 text-[11px] flex items-center gap-2 transition-colors ${
                            isActive
                              ? "bg-blue-50 dark:bg-blue-900/20"
                              : "hover:bg-gray-50 dark:hover:bg-gray-700"
                          }`}
                        >
                          <span className="flex-shrink-0 w-6 h-6 rounded-full bg-gradient-to-br from-blue-500 to-indigo-600 text-white text-[10px] font-semibold flex items-center justify-center">
                            {getInitials(u.name)}
                          </span>
                          <span className="flex-1 min-w-0">
                            <span className="block truncate text-gray-900 dark:text-gray-100 font-medium">
                              {u.name}
                            </span>
                            <span className="block truncate text-[9px] text-gray-500 dark:text-gray-400">
                              {u.email}
                              {u.business_unit ? ` · ${u.business_unit}` : ""}
                              {typeof u.active_reviews === "number"
                                ? ` · ${u.active_reviews} active review${
                                    u.active_reviews === 1 ? "" : "s"
                                  }`
                                : ""}
                            </span>
                          </span>
                          {isSelected && (
                            <Check className="w-3.5 h-3.5 text-blue-600 flex-shrink-0" />
                          )}
                          {typeof u.workload_pct === "number" && (
                            <span
                              className={`text-[9px] font-semibold px-1.5 py-0.5 rounded ${
                                u.workload_pct >= 90
                                  ? "bg-red-100 text-red-700"
                                  : u.workload_pct >= 70
                                  ? "bg-amber-100 text-amber-700"
                                  : "bg-emerald-100 text-emerald-700"
                              }`}
                            >
                              {u.workload_pct}%
                            </span>
                          )}
                        </button>
                      );
                    })}
                  </div>
                );
              })}
            </div>

            {/* Footer hint */}
            <div className="px-3 py-1.5 border-t border-gray-100 dark:border-gray-700 bg-gray-50 dark:bg-gray-900/40 text-[9px] text-gray-500 flex items-center justify-between">
              <span>
                {flatList.length} user{flatList.length === 1 ? "" : "s"} ·
                {" "}
                <span className="text-emerald-600">↑↓ navigate</span>{" "}
                <span className="text-emerald-600">↵ select</span>{" "}
                <span className="text-emerald-600">esc close</span>
              </span>
              <span className="font-mono text-[8px] text-gray-400">DB</span>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export default UserPicker;

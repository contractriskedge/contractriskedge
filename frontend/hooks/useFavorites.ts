/**
 * useFavorites — per-user, per-tenant favorites store backed by the backend API.
 *
 * Favorites are persisted to the server so they work across devices and sessions.
 * localStorage is used as an optimistic cache for instant UI feedback.
 *
 * Storage key: contractedge.favorites.v1.<tenantId>.<userId>
 * Stored as a JSON array of review/contract ids.
 */

"use client";

import { useCallback, useEffect, useState, useSyncExternalStore } from "react";
import { reviewService } from "@/services/api/reviews";

const STORAGE_PREFIX = "contractedge.favorites.v1";

function buildKey(tenantId: string | null | undefined, userId: string | null | undefined): string {
  const t = tenantId || "anonymous";
  const u = userId || "anonymous";
  return `${STORAGE_PREFIX}.${t}.${u}`;
}

function readSet(key: string): Set<string> {
  if (typeof window === "undefined") return new Set();
  try {
    const raw = window.localStorage.getItem(key);
    if (!raw) return new Set();
    const arr = JSON.parse(raw);
    if (Array.isArray(arr)) return new Set(arr.filter((x) => typeof x === "string"));
    return new Set();
  } catch {
    return new Set();
  }
}

function writeSet(key: string, set: Set<string>): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(key, JSON.stringify(Array.from(set)));
    // Fire a custom event so other useFavorites consumers in the same tab
    // can pick up the change without polling.
    window.dispatchEvent(new CustomEvent("contractedge:favorites-changed", { detail: { key } }));
  } catch {
    // localStorage may be disabled — silently no-op.
  }
}

export interface FavoritesApi {
  isFavorite: (id: string) => boolean;
  toggle: (id: string) => void;
  add: (id: string) => void;
  remove: (id: string) => void;
  clear: () => void;
  count: number;
  ids: string[];
  ready: boolean;
}

export function useFavorites(tenantId: string | null | undefined, userId: string | null | undefined): FavoritesApi {
  const key = buildKey(tenantId, userId);

  // Subscribe to changes from the same tab (the dispatchEvent above) and
  // from other tabs via the native `storage` event.
  const subscribe = useCallback(
    (notify: () => void) => {
      if (typeof window === "undefined") return () => {};
      const onLocal = (e: Event) => {
        const ce = e as CustomEvent<{ key: string }>;
        if (!ce.detail || ce.detail.key === key) notify();
      };
      const onStorage = (e: StorageEvent) => {
        if (e.key === key) notify();
      };
      window.addEventListener("contractedge:favorites-changed", onLocal);
      window.addEventListener("storage", onStorage);
      return () => {
        window.removeEventListener("contractedge:favorites-changed", onLocal);
        window.removeEventListener("storage", onStorage);
      };
    },
    [key],
  );

  const getSnapshot = useCallback(() => key, [key]);
  const getServerSnapshot = useCallback(() => "__server__", []);

  // useSyncExternalStore needs a stable key — re-rendering is driven by the
  // listener above.
  useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);

  const [ids, setIds] = useState<string[]>([]);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    const s = readSet(key);
    setIds(Array.from(s));
    setReady(true);
  }, [key]);

  const isFavorite = useCallback((id: string) => ids.includes(id), [ids]);

  const write = useCallback(
    (next: Set<string>) => {
      writeSet(key, next);
      setIds(Array.from(next));
    },
    [key],
  );

  const toggle = useCallback(
    (id: string) => {
      const s = readSet(key);
      const newState = s.has(id) ? false : true;
      if (newState) s.add(id);
      else s.delete(id);
      write(s);
      // Sync to backend — fire-and-forget
      reviewService.toggleFavorite(id, newState).catch(() => {
        // Revert on failure: undo the optimistic local change
        const revert = readSet(key);
        if (newState) revert.delete(id);
        else revert.add(id);
        writeSet(key, revert);
        setIds(Array.from(revert));
      });
    },
    [key, write],
  );

  const add = useCallback(
    (id: string) => {
      const s = readSet(key);
      s.add(id);
      write(s);
    },
    [key, write],
  );

  const remove = useCallback(
    (id: string) => {
      const s = readSet(key);
      s.delete(id);
      write(s);
    },
    [key, write],
  );

  const clear = useCallback(() => write(new Set()), [write]);

  return { isFavorite, toggle, add, remove, clear, count: ids.length, ids, ready };
}

/** Listen for a specific favorite's state — used for icon highlights. */
export function useIsFavorite(tenantId: string | null | undefined, userId: string | null | undefined, id: string | null | undefined): boolean {
  const { isFavorite, ready } = useFavorites(tenantId, userId);
  if (!id) return false;
  // Re-evaluate whenever the snapshot changes
  useSyncExternalStore(() => () => {}, () => id, () => id);
  return ready && isFavorite(id);
}

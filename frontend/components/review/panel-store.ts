/**
 * Panel store — hybrid sidebar state (pinned / auto-hide / focus mode)
 * with per-user persistence via localStorage.
 */

"use client";

export type PanelMode = "pinned" | "auto_hide";

export interface PanelState {
  left: PanelMode;
  right: PanelMode;
  focusMode: boolean;
  /** Transient hover-reveal state for auto-hide panels (not persisted). */
  leftVisible: boolean;
  rightVisible: boolean;
}

interface PersistedPanelPrefs {
  left_panel_mode: PanelMode;
  right_panel_mode: PanelMode;
  focus_mode: boolean;
}

const STORAGE_KEY_BASE = "review:panelState";

const DEFAULT: PanelState = {
  left: "pinned",
  right: "pinned",
  focusMode: false,
  leftVisible: true,
  rightVisible: true,
};

let _storageKey = STORAGE_KEY_BASE;
let _state: PanelState = { ...DEFAULT };
const _listeners = new Set<() => void>();

function defaultVisibility(mode: PanelMode, focusMode: boolean): boolean {
  if (focusMode) return false;
  return mode === "pinned";
}

function normalizeState(partial: Partial<PanelState>): PanelState {
  const left = partial.left ?? DEFAULT.left;
  const right = partial.right ?? DEFAULT.right;
  const focusMode = partial.focusMode ?? DEFAULT.focusMode;
  return {
    left,
    right,
    focusMode,
    leftVisible: partial.leftVisible ?? defaultVisibility(left, focusMode),
    rightVisible: partial.rightVisible ?? defaultVisibility(right, focusMode),
  };
}

function buildStorageKey(tenantId?: string | null, userId?: string | null): string {
  const t = tenantId || "anonymous";
  const u = userId || "anonymous";
  return `${STORAGE_KEY_BASE}.${t}.${u}`;
}

function load(key = _storageKey): PanelState {
  if (typeof window === "undefined") return { ...DEFAULT };
  try {
    const raw = localStorage.getItem(key);
    if (!raw) return { ...DEFAULT };
    const parsed = JSON.parse(raw) as Partial<PersistedPanelPrefs> & Partial<PanelState>;
    return normalizeState({
      left: parsed.left_panel_mode ?? parsed.left ?? DEFAULT.left,
      right: parsed.right_panel_mode ?? parsed.right ?? DEFAULT.right,
      focusMode: parsed.focus_mode ?? parsed.focusMode ?? DEFAULT.focusMode,
    });
  } catch {
    return { ...DEFAULT };
  }
}

function save(state: PanelState): void {
  if (typeof window === "undefined") return;
  const payload: PersistedPanelPrefs = {
    left_panel_mode: state.left,
    right_panel_mode: state.right,
    focus_mode: state.focusMode,
  };
  try {
    localStorage.setItem(_storageKey, JSON.stringify(payload));
  } catch {
    // storage full or unavailable
  }
}

function notify(): void {
  for (const fn of _listeners) fn();
}

/** Scope persistence to the authenticated user/tenant. */
export function setPanelStoreUser(
  tenantId?: string | null,
  userId?: string | null,
): void {
  const nextKey = buildStorageKey(tenantId, userId);
  if (nextKey === _storageKey) return;
  _storageKey = nextKey;
  _state = load(nextKey);
  notify();
}

export const panelStore = {
  get(): PanelState {
    return { ..._state };
  },

  subscribe(listener: () => void): () => void {
    _listeners.add(listener);
    return () => _listeners.delete(listener);
  },

  setLeft(mode: PanelMode): void {
    _state = normalizeState({
      ..._state,
      left: mode,
      leftVisible: defaultVisibility(mode, _state.focusMode),
    });
    save(_state);
    notify();
  },

  setRight(mode: PanelMode): void {
    _state = normalizeState({
      ..._state,
      right: mode,
      rightVisible: defaultVisibility(mode, _state.focusMode),
    });
    save(_state);
    notify();
  },

  toggleLeftMode(): void {
    const next = _state.left === "pinned" ? "auto_hide" : "pinned";
    this.setLeft(next);
  },

  toggleRightMode(): void {
    const next = _state.right === "pinned" ? "auto_hide" : "pinned";
    this.setRight(next);
  },

  setLeftVisible(visible: boolean): void {
    if (_state.focusMode || _state.left === "pinned") return;
    if (_state.leftVisible === visible) return;
    _state = { ..._state, leftVisible: visible };
    notify();
  },

  setRightVisible(visible: boolean): void {
    if (_state.focusMode || _state.right === "pinned") return;
    if (_state.rightVisible === visible) return;
    _state = { ..._state, rightVisible: visible };
    notify();
  },

  toggleFocusMode(): void {
    if (_state.focusMode) {
      this.exitFocusMode();
      return;
    }
    _state = normalizeState({
      ..._state,
      focusMode: true,
      leftVisible: false,
      rightVisible: false,
    });
    save(_state);
    notify();
  },

  exitFocusMode(): void {
    if (!_state.focusMode) return;
    _state = normalizeState({
      ..._state,
      focusMode: false,
      leftVisible: defaultVisibility(_state.left, false),
      rightVisible: defaultVisibility(_state.right, false),
    });
    save(_state);
    notify();
  },
};

if (typeof window !== "undefined") {
  _state = load();
}

import { useSyncExternalStore } from "react";

export function usePanelState(): PanelState {
  return useSyncExternalStore(
    (cb) => panelStore.subscribe(cb),
    () => panelStore.get(),
    () => DEFAULT,
  );
}

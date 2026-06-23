"use client";

import { useCallback, useRef, useState, useEffect } from "react";

// ── Types ────────────────────────────────────────────────────────

type SaveStatus = "idle" | "saving" | "saved" | "error";

interface UseAutosaveOptions {
  /** Key for localStorage (per-session, per-field) */
  storageKey: string;
  /** Debounce delay in ms */
  delay?: number;
  /** Callback to persist to backend */
  onSave?: (value: string) => Promise<void>;
  /** Whether autosave is enabled */
  enabled?: boolean;
}

interface UseAutosaveReturn {
  /** Current value */
  value: string;
  /** Set value (triggers debounced save) */
  setValue: (val: string) => void;
  /** Current save status */
  status: SaveStatus;
  /** Manually trigger save now */
  saveNow: () => Promise<void>;
  /** Recover draft from localStorage */
  recover: () => string;
  /** Clear saved draft */
  clearDraft: () => void;
  /** Whether there's an unsaved draft */
  hasDraft: boolean;
}

// ── Hook ─────────────────────────────────────────────────────────

export function useAutosave({
  storageKey,
  delay = 300,
  onSave,
  enabled = true,
}: UseAutosaveOptions): UseAutosaveReturn {
  const [value, setValueState] = useState("");
  const [status, setStatus] = useState<SaveStatus>("idle");
  const [hasDraft, setHasDraft] = useState(false);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const latestValueRef = useRef(value);
  const onSaveRef = useRef(onSave);
  onSaveRef.current = onSave;

  // Check for existing draft on mount
  useEffect(() => {
    if (typeof window === "undefined") return;
    const saved = localStorage.getItem(storageKey);
    if (saved) {
      setHasDraft(true);
    }
  }, [storageKey]);

  // Persist to localStorage on change
  const persistToLocal = useCallback(
    (val: string) => {
      try {
        if (val.trim()) {
          localStorage.setItem(storageKey, val);
          setHasDraft(true);
        } else {
          localStorage.removeItem(storageKey);
          setHasDraft(false);
        }
      } catch { /* localStorage might be full */ }
    },
    [storageKey],
  );

  const setValue = useCallback(
    (val: string) => {
      setValueState(val);
      latestValueRef.current = val;
      persistToLocal(val);

      if (!enabled) return;

      // Debounced save
      if (timerRef.current) clearTimeout(timerRef.current);
      setStatus("saving");
      timerRef.current = setTimeout(async () => {
        if (onSaveRef.current && val.trim()) {
          try {
            await onSaveRef.current(val);
            setStatus("saved");
            // Clear "saved" status after 2 seconds
            setTimeout(() => setStatus("idle"), 2000);
          } catch {
            setStatus("error");
          }
        } else {
          setStatus("idle");
        }
      }, delay);
    },
    [delay, enabled, persistToLocal],
  );

  const saveNow = useCallback(async () => {
    if (timerRef.current) clearTimeout(timerRef.current);
    if (onSaveRef.current && latestValueRef.current.trim()) {
      setStatus("saving");
      try {
        await onSaveRef.current(latestValueRef.current);
        setStatus("saved");
        setTimeout(() => setStatus("idle"), 2000);
      } catch {
        setStatus("error");
      }
    }
  }, []);

  const recover = useCallback(() => {
    if (typeof window === "undefined") return "";
    const saved = localStorage.getItem(storageKey);
    if (saved) {
      setValueState(saved);
      latestValueRef.current = saved;
      return saved;
    }
    return "";
  }, [storageKey]);

  const clearDraft = useCallback(() => {
    try {
      localStorage.removeItem(storageKey);
      setHasDraft(false);
    } catch { /* ignore */ }
  }, [storageKey]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, []);

  return {
    value,
    setValue,
    status,
    saveNow,
    recover,
    clearDraft,
    hasDraft,
  };
}

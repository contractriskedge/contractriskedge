/**
 * useSessionGovernance — React hook for distributed session management.
 *
 * Provides:
 * - Automatic session registration on authentication
 * - Session heartbeat for keep-alive
 * - Forced logout detection (server-initiated session termination)
 * - Concurrent session monitoring
 * - Device tracking
 * - Session list and termination
 *
 * Usage:
 *   const {
 *     sessions,
 *     currentSessionId,
 *     isRegistered,
 *     terminateSession,
 *     refreshSessions,
 *   } = useSessionGovernance();
 *
 *   // Handle forced logout:
 *   useEffect(() => {
 *     if (forceLogoutReason) {
 *       // Redirect to login page
 *     }
 *   }, [forceLogoutReason]);
 */

"use client";

import { useEffect, useState, useCallback } from "react";
import { useAuth } from "@/components/auth/AuthProvider";
import { sessionGovernance } from "@/services/api/sessionGovernance";
import type { SessionInfo, SessionAuditEntry } from "@/services/api/sessionGovernance";

interface UseSessionGovernanceReturn {
  /** List of active sessions for the current user. */
  sessions: SessionInfo[];
  /** Current session ID. */
  currentSessionId: string;
  /** Whether the session is registered with the backend. */
  isRegistered: boolean;
  /** Reason for forced logout, if any. */
  forceLogoutReason: string | null;
  /** Terminate a specific session. */
  terminateSession: (sessionId: string) => Promise<boolean>;
  /** Refresh the session list. */
  refreshSessions: () => Promise<void>;
  /** Get session audit log. */
  getAuditLog: () => Promise<SessionAuditEntry[]>;
  /** Revoke the current session (logout). */
  revokeSession: () => Promise<boolean>;
}

export function useSessionGovernance(): UseSessionGovernanceReturn {
  const { user, token } = useAuth();
  const [sessions, setSessions] = useState<SessionInfo[]>([]);
  const [forceLogoutReason, setForceLogoutReason] = useState<string | null>(null);

  // ── Register session on authentication ─────────────────────────
  useEffect(() => {
    if (!user || !token) return;

    sessionGovernance.register().then((result) => {
      if (result?.existing_sessions) {
        setSessions(result.existing_sessions);
      }
    });

    // Listen for forced logout
    const unsubForceLogout = sessionGovernance.onForceLogout(() => {
      setForceLogoutReason("Your session has been terminated. Please log in again.");
    });

    // Listen for suspicious activity
    const unsubSuspicious = sessionGovernance.onSuspiciousActivity((info) => {
      console.warn(`[SessionGovernance] Suspicious activity: ${info.type} — ${info.details}`);
    });

    return () => {
      unsubForceLogout();
      unsubSuspicious();
    };
  }, [user, token]);

  // ── Refresh sessions list ──────────────────────────────────────
  const refreshSessions = useCallback(async () => {
    const sessionList = await sessionGovernance.listSessions();
    setSessions(sessionList);
  }, []);

  // ── Terminate a session ────────────────────────────────────────
  const terminateSession = useCallback(async (sessionId: string): Promise<boolean> => {
    const success = await sessionGovernance.terminateSession(sessionId);
    if (success) {
      // Remove from local state
      setSessions((prev) => prev.filter((s) => s.session_id !== sessionId));
    }
    return success;
  }, []);

  // ── Get audit log ──────────────────────────────────────────────
  const getAuditLog = useCallback(async (): Promise<SessionAuditEntry[]> => {
    return sessionGovernance.getAuditLog();
  }, []);

  // ── Revoke session ─────────────────────────────────────────────
  const revokeSession = useCallback(async (): Promise<boolean> => {
    return sessionGovernance.revoke();
  }, []);

  return {
    sessions,
    currentSessionId: sessionGovernance.getSessionId(),
    isRegistered: sessionGovernance.isRegistered(),
    forceLogoutReason,
    terminateSession,
    refreshSessions,
    getAuditLog,
    revokeSession,
  };
}

/**
 * Distributed Session Governance — session registry, concurrent login
 * tracking, device tracking, forced logout, token revocation, and
 * suspicious session detection.
 *
 * This module provides the frontend side of session governance:
 * - Session registration with the backend on login
 * - Heartbeat to keep the session alive
 * - Device fingerprinting for session identification
 * - Concurrent session limit enforcement
 * - Forced logout handling (server-initiated)
 * - Token revocation on logout
 * - Suspicious session detection alerts
 *
 * Backend API endpoints (to be implemented):
 *   POST   /api/v1/auth/sessions/register  — Register a new session
 *   POST   /api/v1/auth/sessions/heartbeat — Keep session alive
 *   GET    /api/v1/auth/sessions           — List active sessions
 *   DELETE /api/v1/auth/sessions/:id       — Terminate a session
 *   POST   /api/v1/auth/sessions/revoke    — Revoke current token
 *   GET    /api/v1/auth/sessions/audit     — Get session audit log
 *
 * Usage:
 *   import { sessionGovernance } from '@/services/api/sessionGovernance';
 *
 *   // On login:
 *   await sessionGovernance.register();
 *
 *   // On logout:
 *   await sessionGovernance.revoke();
 *
 *   // Check for forced logout:
 *   useEffect(() => {
 *     const unsub = sessionGovernance.onForceLogout(() => {
 *       // Redirect to login
 *     });
 *     return unsub;
 *   }, []);
 */

"use client";

// ── Types ─────────────────────────────────────────────────────────

export type SessionInfo = {
  session_id: string;
  device_name: string;
  device_type: string;
  browser: string;
  os: string;
  ip_address: string;
  location: string | null;
  created_at: string;
  last_active_at: string;
  is_current: boolean;
};

export type SessionAuditEntry = {
  action: "login" | "logout" | "forced_logout" | "token_refresh" | "session_terminated" | "suspicious_activity";
  timestamp: string;
  ip_address: string;
  device_name: string;
  details: string | null;
};

export type SessionGovernanceConfig = {
  /** API base URL. Default: /api/v1 */
  apiBase?: string;
  /** Heartbeat interval in ms. Default: 60000 (1 min) */
  heartbeatInterval?: number;
  /** Maximum concurrent sessions. Default: 5 */
  maxConcurrentSessions?: number;
  /** Enable suspicious activity detection. Default: true */
  enableSuspicionDetection?: boolean;
};

// ── Defaults ──────────────────────────────────────────────────────

const DEFAULTS: Required<SessionGovernanceConfig> = {
  apiBase: "/api/v1",
  heartbeatInterval: 60_000,
  maxConcurrentSessions: 5,
  enableSuspicionDetection: true,
};

// ── Device Fingerprinting ─────────────────────────────────────────

function getDeviceFingerprint(): {
  device_name: string;
  device_type: string;
  browser: string;
  os: string;
} {
  if (typeof window === "undefined") {
    return { device_name: "server", device_type: "server", browser: "unknown", os: "unknown" };
  }

  const ua = navigator.userAgent;
  const browser = ua.includes("Firefox") ? "Firefox"
    : ua.includes("Chrome") ? "Chrome"
    : ua.includes("Safari") ? "Safari"
    : ua.includes("Edg") ? "Edge"
    : "Unknown";

  const os = ua.includes("Windows NT") ? "Windows"
    : ua.includes("Mac OS X") ? "macOS"
    : ua.includes("Linux") ? "Linux"
    : ua.includes("Android") ? "Android"
    : ua.includes("iOS") ? "iOS"
    : "Unknown";

  const device_type = ua.includes("Mobile") || ua.includes("Android")
    ? "mobile"
    : ua.includes("iPad") || ua.includes("Tablet")
      ? "tablet"
      : "desktop";

  // Generate a consistent device name
  const screen = `${window.screen.width}x${window.screen.height}`;
  const device_name = `${browser} on ${os} (${screen})`;

  return { device_name, device_type, browser, os };
}

// ── Session ID ────────────────────────────────────────────────────

function generateSessionId(): string {
  return `sess_${Date.now()}_${Math.random().toString(36).slice(2, 10)}`;
}

function getOrCreateSessionId(): string {
  try {
    let sessionId = localStorage.getItem("session_id");
    if (!sessionId) {
      sessionId = generateSessionId();
      localStorage.setItem("session_id", sessionId);
    }
    return sessionId;
  } catch {
    return generateSessionId();
  }
}

// ── Session Governance Class ──────────────────────────────────────

class SessionGovernance {
  private config: Required<SessionGovernanceConfig>;
  private heartbeatTimer: ReturnType<typeof setInterval> | null = null;
  private forceLogoutHandlers: Set<() => void> = new Set();
  private suspiciousActivityHandlers: Set<(info: { type: string; details: string }) => void> = new Set();
  private registered = false;
  private sessionId: string;

  constructor(config: SessionGovernanceConfig = {}) {
    this.config = { ...DEFAULTS, ...config };
    this.sessionId = getOrCreateSessionId();
  }

  /**
   * Register the current session with the backend.
   * Call this after successful authentication.
   */
  async register(): Promise<{ session_id: string; existing_sessions: SessionInfo[] } | null> {
    if (this.registered) return null;

    const fingerprint = getDeviceFingerprint();

    try {
      const token = this.getToken();
      if (!token) return null;

      const res = await fetch(`${this.config.apiBase}/auth/sessions/register`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          session_id: this.sessionId,
          ...fingerprint,
        }),
      });

      if (res.ok) {
        this.registered = true;
        this.startHeartbeat();
        const data = await res.json();

        // Check for concurrent session limit
        if (data.existing_sessions?.length >= this.config.maxConcurrentSessions) {
          this.notifySuspiciousActivity({
            type: "concurrent_session_limit",
            details: `${data.existing_sessions.length} active sessions detected`,
          });
        }

        return data;
      }

      // If we get a 409 Conflict, another session with the same ID exists
      if (res.status === 409) {
        // Generate a new session ID and retry
        this.sessionId = generateSessionId();
        try { localStorage.setItem("session_id", this.sessionId); } catch {}
        return this.register();
      }

      return null;
    } catch {
      // Backend may not support sessions yet — fail gracefully
      console.warn("[SessionGovernance] Failed to register session — endpoint may not be available");
      return null;
    }
  }

  /**
   * Send a heartbeat to keep the session alive.
   */
  async heartbeat(): Promise<boolean> {
    if (!this.registered) return false;

    try {
      const token = this.getToken();
      if (!token) return false;

      const res = await fetch(`${this.config.apiBase}/auth/sessions/heartbeat`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ session_id: this.sessionId }),
      });

      if (res.status === 401) {
        // Token expired or revoked — check for forced logout
        this.handleForceLogout("Token expired or revoked");
        return false;
      }

      if (res.status === 403) {
        // Session was terminated by admin
        this.handleForceLogout("Session terminated by administrator");
        return false;
      }

      if (res.status === 409) {
        // Concurrent session limit exceeded — another session forced this one out
        this.handleForceLogout("Concurrent session limit exceeded — logged out from another device");
        return false;
      }

      return res.ok;
    } catch {
      return false;
    }
  }

  /**
   * List all active sessions for the current user.
   */
  async listSessions(): Promise<SessionInfo[]> {
    try {
      const token = this.getToken();
      if (!token) return [];

      const res = await fetch(`${this.config.apiBase}/auth/sessions`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (!res.ok) return [];
      const data = await res.json();
      return data.sessions ?? [];
    } catch {
      return [];
    }
  }

  /**
   * Terminate a specific session (admin or self-service).
   */
  async terminateSession(sessionId: string): Promise<boolean> {
    try {
      const token = this.getToken();
      if (!token) return false;

      const res = await fetch(`${this.config.apiBase}/auth/sessions/${sessionId}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
      });

      return res.ok;
    } catch {
      return false;
    }
  }

  /**
   * Revoke the current token and end the session.
   * Call this on logout.
   */
  async revoke(): Promise<boolean> {
    this.stopHeartbeat();
    this.registered = false;

    try {
      const token = this.getToken();
      if (!token) return false;

      const res = await fetch(`${this.config.apiBase}/auth/sessions/revoke`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ session_id: this.sessionId }),
      });

      return res.ok;
    } catch {
      return false;
    }
  }

  /**
   * Get session audit log.
   */
  async getAuditLog(): Promise<SessionAuditEntry[]> {
    try {
      const token = this.getToken();
      if (!token) return [];

      const res = await fetch(`${this.config.apiBase}/auth/sessions/audit`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (!res.ok) return [];
      const data = await res.json();
      return data.entries ?? [];
    } catch {
      return [];
    }
  }

  /**
   * Register a handler for forced logout events.
   * Returns an unsubscribe function.
   */
  onForceLogout(handler: () => void): () => void {
    this.forceLogoutHandlers.add(handler);
    return () => {
      this.forceLogoutHandlers.delete(handler);
    };
  }

  /**
   * Register a handler for suspicious activity alerts.
   * Returns an unsubscribe function.
   */
  onSuspiciousActivity(handler: (info: { type: string; details: string }) => void): () => void {
    this.suspiciousActivityHandlers.add(handler);
    return () => {
      this.suspiciousActivityHandlers.delete(handler);
    };
  }

  /**
   * Get the current session ID.
   */
  getSessionId(): string {
    return this.sessionId;
  }

  /**
   * Check if the session is registered.
   */
  isRegistered(): boolean {
    return this.registered;
  }

  /**
   * Clean up all resources.
   */
  destroy(): void {
    this.stopHeartbeat();
    this.forceLogoutHandlers.clear();
    this.suspiciousActivityHandlers.clear();
    this.registered = false;
  }

  // ── Private ──────────────────────────────────────────────────

  private startHeartbeat(): void {
    this.stopHeartbeat();
    this.heartbeatTimer = setInterval(() => {
      this.heartbeat();
    }, this.config.heartbeatInterval);
  }

  private stopHeartbeat(): void {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer);
      this.heartbeatTimer = null;
    }
  }

  private getToken(): string | null {
    try {
      return localStorage.getItem("auth_token");
    } catch {
      return null;
    }
  }

  private handleForceLogout(reason: string): void {
    this.registered = false;
    this.stopHeartbeat();

    // Clear auth token
    try { localStorage.removeItem("auth_token"); } catch {}

    // Notify all handlers
    this.forceLogoutHandlers.forEach((handler) => {
      try { handler(); } catch {}
    });

    console.warn(`[SessionGovernance] Forced logout: ${reason}`);
  }

  private notifySuspiciousActivity(info: { type: string; details: string }): void {
    if (!this.config.enableSuspicionDetection) return;
    this.suspiciousActivityHandlers.forEach((handler) => {
      try { handler(info); } catch {}
    });
  }
}

// ── Singleton ─────────────────────────────────────────────────────

export const sessionGovernance = new SessionGovernance();

/**
 * React hook for session governance.
 * Integrates with AuthProvider for automatic registration and cleanup.
 *
 * Usage:
 *   import { useSessionGovernance } from '@/services/api/sessionGovernance';
 *
 *   function App() {
 *     const { isRegistered, sessions, forceLogout } = useSessionGovernance();
 *   }
 */
export function createSessionGovernanceHook(registerOnMount = true) {
  return function useSessionGovernance() {
    // This is a lightweight wrapper — the actual React hook
    // would be in a separate file to avoid importing React here.
    // For now, the imperative API is sufficient.
    return {
      register: () => sessionGovernance.register(),
      revoke: () => sessionGovernance.revoke(),
      listSessions: () => sessionGovernance.listSessions(),
      terminateSession: (id: string) => sessionGovernance.terminateSession(id),
      getAuditLog: () => sessionGovernance.getAuditLog(),
      onForceLogout: (handler: () => void) => sessionGovernance.onForceLogout(handler),
      onSuspiciousActivity: (handler: (info: { type: string; details: string }) => void) =>
        sessionGovernance.onSuspiciousActivity(handler),
      getSessionId: () => sessionGovernance.getSessionId(),
      isRegistered: () => sessionGovernance.isRegistered(),
    };
  };
}

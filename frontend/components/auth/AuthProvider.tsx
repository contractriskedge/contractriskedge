"use client";

import React, {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  useRef,
} from "react";
import { getRealtimeClient, disconnectRealtimeClient } from "@/lib/realtime";
import type { ConnectionState } from "@/lib/realtime";
import { setGlobalConnectionState } from "@/services/hooks/useAdaptivePolling";
import { sessionGovernance } from "@/services/api/sessionGovernance";

// ── Types ─────────────────────────────────────────────────────────

export interface User {
  sub: string;
  email: string;
  name: string;
  tenant_id: string;
  role: string;
  permissions: string[];
}

export interface AuthContextType {
  user: User | null;
  token: string | null;
  isLoading: boolean;
  error: string | null;
  login: () => Promise<void>;
  logout: () => void;
  hasPermission: (permission: string) => boolean;
  /** Get a valid access token, fetching a new one if necessary. */
  getAccessToken: () => Promise<string | null>;
  /** Connection state of the realtime WebSocket. */
  realtimeState: ConnectionState;
}

const AuthContext = createContext<AuthContextType>({
  user: null,
  token: null,
  isLoading: true,
  error: null,
  login: async () => {},
  logout: () => {},
  hasPermission: () => false,
  getAccessToken: async () => null,
  realtimeState: "disconnected",
});

export const useAuth = () => useContext(AuthContext);

const API_URL = process.env.NEXT_PUBLIC_API_URL || "/api/v1";

function readJwtTenantId(jwt: string): string | null {
  try {
    if (jwt.split(".").length !== 3) return null;
    const payload = JSON.parse(atob(jwt.split(".")[1]));
    return typeof payload.tenant_id === "string" ? payload.tenant_id : null;
  } catch {
    return null;
  }
}

/** Dev JWT aligned with appSession tenant (backend scopes all data by JWT tenant_id). */
async function fetchDevBackendJwt(): Promise<string | null> {
  try {
    const res = await fetch(`${API_URL}/auth/token`, { method: "POST" });
    if (!res.ok) return null;
    const data = await res.json();
    return typeof data.access_token === "string" ? data.access_token : null;
  } catch {
    return null;
  }
}

// ── Token Refresh ─────────────────────────────────────────────────

/**
 * Attempt to refresh the JWT token using Auth0's session.
 */
async function refreshToken(): Promise<string | null> {
  // Fetch the current session from Auth0
  try {
    const res = await fetch("/api/auth/me");
    if (res.ok) {
      const data = await res.json();
      // Auth0 returns the user session — the access token may be in the response
      return data.accessToken || null;
    }
  } catch {
    // Session fetch failed
  }
  return null;
}

// ── Auth Provider ─────────────────────────────────────────────────

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [realtimeState, setRealtimeState] = useState<ConnectionState>("disconnected");
  const realtimeStarted = useRef(false);
  const authChecked = useRef(false);

  // ── Apply a decoded token ──────────────────────────────────────
  const applyToken = useCallback((newToken: string) => {
    try {
      const payload = JSON.parse(atob(newToken.split(".")[1]));
      setUser({
        sub: payload.sub || "",
        email: payload.email || "",
        name: payload.name || "",
        tenant_id: payload.tenant_id || "",
        role: payload.role || "",
        permissions: payload.permissions || [],
      });
      setToken(newToken);
      localStorage.setItem("auth_token", newToken);
    } catch {
      // Invalid token
    }
  }, []);

  /** Keep localStorage JWT tenant_id in sync with the app session (fixes review 404s in dev). */
  const syncBackendJwt = useCallback(
    async (session: User) => {
      if (typeof window === "undefined") return;

      // Always mint a fresh backend dev JWT locally so POST mutations get
      // workflows:approve (stale localStorage tokens often only had contracts:read).
      if (process.env.NODE_ENV === "development") {
        const devJwt = await fetchDevBackendJwt();
        if (devJwt) {
          applyToken(devJwt);
          return;
        }
      }

      const stored = localStorage.getItem("auth_token");
      if (stored && readJwtTenantId(stored) === session.tenant_id) {
        applyToken(stored);
        return;
      }

      if (stored) {
        localStorage.removeItem("auth_token");
      }
    },
    [applyToken],
  );

  // ── Initialize auth on mount (ONCE) ────────────────────────────
  useEffect(() => {
    if (authChecked.current) return;
    authChecked.current = true;

    fetch("/api/auth/me")
      .then((res) => {
        if (!res.ok) throw new Error("Not authenticated");
        return res.json();
      })
      .then(async (session) => {
        if (session?.sub) {
          const nextUser: User = {
            sub: session.sub,
            email: session.email || "",
            name: session.name || "",
            tenant_id: session.tenant_id || "",
            role: session.role || "",
            permissions: session.permissions || [],
          };
          setUser(nextUser);
          await syncBackendJwt(nextUser);
        }
      })
      .catch(() => {
        localStorage.removeItem("auth_token");
      })
      .finally(() => {
        setIsLoading(false);
      });
  }, [syncBackendJwt]);

  // ── Forced logout listener ─────────────────────────────────────
  // When the server terminates the session (admin action, concurrent
  // login limit, token revocation), the session governance system
  // triggers a forced logout.
  useEffect(() => {
    const unsub = sessionGovernance.onForceLogout(() => {
      disconnectRealtimeClient();
      realtimeStarted.current = false;
      setUser(null);
      setToken(null);
      setRealtimeState("disconnected");
      localStorage.removeItem("auth_token");
    });

    return unsub;
  }, []);

  // ── Proactive token refresh ────────────────────────────────────
  // Refreshes the token 5 minutes before expiry to prevent
  // WebSocket disconnects due to stale auth.
  useEffect(() => {
    if (!token) return;

    // Only attempt JWT parsing if token looks like a JWT (has 3 parts)
    if (typeof token !== "string" || token.split(".").length !== 3) return;

    try {
      const payload = JSON.parse(atob(token.split(".")[1]));
      const expMs = payload.exp ? payload.exp * 1000 : 0;
      const now = Date.now();
      const timeUntilExpiry = expMs - now;

      // Only schedule if token expires within reasonable window
      if (timeUntilExpiry <= 0) return; // Already expired — handled on mount

      // Refresh 5 minutes before expiry, or at 75% of token lifetime
      const refreshMargin = Math.min(5 * 60 * 1000, timeUntilExpiry * 0.75);
      const refreshDelay = Math.max(timeUntilExpiry - refreshMargin, 10_000);

      const refreshTimer = setTimeout(async () => {
        const newToken = await refreshToken();
        if (newToken && newToken !== token) {
          applyToken(newToken);
        }
      }, refreshDelay);

      return () => clearTimeout(refreshTimer);
    } catch {
      // Invalid token — skip proactive refresh
    }
  }, [token, applyToken]);

  // ── Start realtime client when user is authenticated ───────────
  useEffect(() => {
    if (!user || !token || realtimeStarted.current) return;

    realtimeStarted.current = true;

    // In development, Next.js rewrites don't proxy WebSocket upgrades,
    // so connect directly to the backend port. In production, the same
    // origin handles both HTTP and WebSocket via reverse proxy.
    const isDev = process.env.NODE_ENV === "development";
    const wsUrl = isDev
      ? `ws://localhost:8000/api/v1/ws/events`
      : undefined;

    const client = getRealtimeClient({
      getToken: async () => {
        // Try to get a fresh token, fall back to current
        const fresh = await refreshToken();
        return fresh || token;
      },
      onEvent: (event) => {
        // Dispatch custom event for other components to listen to
        // (e.g., ActivityFeed, NotificationCenter)
        if (typeof window !== "undefined") {
          window.dispatchEvent(
            new CustomEvent("realtime-event", { detail: event }),
          );
        }

        // Generic event handler — components can subscribe via useWorkspaceRealtime
        if (event.type === "notification.created" && event.data) {
          // Could trigger a toast here
        }
      },
      onStateChange: (state) => {
        setRealtimeState(state);
        setGlobalConnectionState(state);
      },
      topics: ["review.*", "notification.*", "recovery.*", "job.*"],
      tenantId: user.tenant_id,
      userId: user.sub,
      wsUrl,
      connectionOwnerId: "auth-provider",
    });

    client.connect();

    return () => {
      // Don't disconnect on unmount — the singleton persists across navigations.
      // The connection ownership guard handles stale connections.
    };
  }, [user, token]);

  // ── Login ──────────────────────────────────────────────────────
  const login = useCallback(async () => {
    setError(null);
    setIsLoading(true);

    try {
      // Local dev: set appSession cookie so middleware allows /dashboard
      if (process.env.NODE_ENV === "development") {
        const res = await fetch("/api/auth/dev-login", { method: "POST" });
        if (res.ok) {
          const session = await res.json();
          const nextUser: User = {
            sub: session.sub,
            email: session.email || "",
            name: session.name || "",
            tenant_id: session.tenant_id || "",
            role: session.role || "",
            permissions: session.permissions || [],
          };
          setUser(nextUser);
          await syncBackendJwt(nextUser);
          setIsLoading(false);
          window.location.href = "/dashboard";
          return;
        }
      }
    } catch {
      // Fall through to Auth0
    }

    window.location.href = "/api/auth/login";
  }, [syncBackendJwt]);

  // ── Logout ─────────────────────────────────────────────────────
  const logout = useCallback(() => {
    // Revoke session before disconnecting
    sessionGovernance.revoke().catch(() => {});

    disconnectRealtimeClient();
    realtimeStarted.current = false;
    setUser(null);
    setToken(null);
    setRealtimeState("disconnected");
    localStorage.removeItem("auth_token");

    // Redirect to Auth0 logout
    window.location.href = "/api/auth/logout";
  }, []);

  // ── getAccessToken ──────────────────────────────────────────────
  // Returns the current token from state, or fetches a dev JWT if none is set.
  const getAccessToken = useCallback(async (): Promise<string | null> => {
    if (token) return token;

    // Align with api client GETs (localStorage + dev mint), not only React state.
    const { getValidToken } = await import("@/services/api/client");
    const stored = await getValidToken();
    if (stored) {
      applyToken(stored);
      return stored;
    }

    const devJwt = await fetchDevBackendJwt();
    if (devJwt) {
      applyToken(devJwt);
      return devJwt;
    }
    return null;
  }, [token, applyToken]);

  // ── Permission check ───────────────────────────────────────────
  const hasPermission = useCallback(
    (permission: string) => user?.permissions?.includes(permission) ?? false,
    [user],
  );

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isLoading,
        error,
        login,
        logout,
        hasPermission,
        getAccessToken,
        realtimeState,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}


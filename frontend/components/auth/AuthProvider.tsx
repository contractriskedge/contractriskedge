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
  realtimeState: "disconnected",
});

export const useAuth = () => useContext(AuthContext);

const API_URL = process.env.NEXT_PUBLIC_API_URL || "/api/v1";

// ── Token Refresh ─────────────────────────────────────────────────

/**
 * Attempt to refresh the JWT token using Auth0's silent authentication.
 * Falls back to the dev-login endpoint in development environments.
 */
async function refreshToken(currentToken: string | null): Promise<string | null> {
  // If Auth0 SDK is available, use silent auth
  if (typeof window !== "undefined") {
    try {
      // Check if @auth0/auth0-spa-js is loaded (for Auth0 environments)
      const auth0Client = (window as unknown as { __auth0_client?: { getTokenSilently: () => Promise<string> } }).__auth0_client;
      if (auth0Client && typeof auth0Client.getTokenSilently === "function") {
        const token = await auth0Client.getTokenSilently();
        if (token) return token;
      }
    } catch {
      // Silent auth failed — fall through to dev-login
    }
  }

  // Fallback: use the dev-login endpoint (development only)
  try {
    const res = await fetch(`${API_URL}/auth/token`, { method: "POST" });
    if (res.ok) {
      const data = await res.json();
      return data.access_token || null;
    }
  } catch {
    // Network error — return current token (may be expired)
  }

  return currentToken;
}

// ── Auth Provider ─────────────────────────────────────────────────

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [realtimeState, setRealtimeState] = useState<ConnectionState>("disconnected");
  const realtimeStarted = useRef(false);

  // ── Initialize auth on mount ───────────────────────────────────
  useEffect(() => {
    const storedToken = localStorage.getItem("auth_token");
    if (storedToken) {
      try {
        const payload = JSON.parse(atob(storedToken.split(".")[1]));

        // Check expiration
        if (payload.exp && payload.exp * 1000 < Date.now()) {
          // Token expired — try to refresh
          refreshToken(storedToken).then((newToken) => {
            if (newToken && newToken !== storedToken) {
              applyToken(newToken);
            } else {
              localStorage.removeItem("auth_token");
              setIsLoading(false);
            }
          });
          return;
        }

        setUser({
          sub: payload.sub || "",
          email: payload.email || "",
          name: payload.name || "",
          tenant_id: payload.tenant_id || "",
          role: payload.role || "",
          permissions: payload.permissions || [],
        });
        setToken(storedToken);
      } catch {
        localStorage.removeItem("auth_token");
      }
    }
    setIsLoading(false);
  }, []);

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
        const newToken = await refreshToken(token);
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

    const client = getRealtimeClient({
      getToken: async () => {
        // Try to get a fresh token, fall back to current
        const fresh = await refreshToken(token);
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
    try {
      const res = await fetch(`${API_URL}/auth/dev-login`, {
        method: "GET",
        headers: { "Content-Type": "application/json" },
      });

      if (!res.ok) {
        throw new Error("Authentication failed");
      }

      const data = await res.json();
      const accessToken = data.access_token;
      applyToken(accessToken);

      // Register session with governance system
      sessionGovernance.register().catch(() => {
        // Session governance is optional — fail gracefully
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to authenticate");
    }
  }, [applyToken]);

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
  }, []);

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
        realtimeState,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}


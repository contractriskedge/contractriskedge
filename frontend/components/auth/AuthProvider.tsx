"use client";

import React, { createContext, useContext, useState, useEffect, useCallback } from "react";

interface User {
  sub: string;
  email: string;
  name: string;
  tenant_id: string;
  role: string;
  permissions: string[];
}

interface AuthContextType {
  user: User | null;
  token: string | null;
  isLoading: boolean;
  error: string | null;
  login: () => void;
  logout: () => void;
  hasPermission: (permission: string) => boolean;
}

const AuthContext = createContext<AuthContextType>({
  user: null,
  token: null,
  isLoading: true,
  error: null,
  login: () => {},
  logout: () => {},
  hasPermission: () => false,
});

export const useAuth = () => useContext(AuthContext);

const API_URL = process.env.NEXT_PUBLIC_API_URL || "/api/v1";

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // Check for stored token on mount
    const storedToken = localStorage.getItem("auth_token");
    if (storedToken) {
      try {
        const payload = JSON.parse(atob(storedToken.split(".")[1]));
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

  const login = useCallback(async () => {
    setError(null);
    try {
      // Development mode: use the dev-login endpoint
      const res = await fetch(`${API_URL}/auth/dev-login`, {
        method: "GET",
        headers: { "Content-Type": "application/json" },
      });

      if (!res.ok) {
        throw new Error("Authentication failed");
      }

      const data = await res.json();
      const accessToken = data.access_token;

      // Decode JWT to get user info
      const payload = JSON.parse(atob(accessToken.split(".")[1]));
      const userData: User = {
        sub: payload.sub || "",
        email: payload.email || "",
        name: payload.name || "",
        tenant_id: payload.tenant_id || "",
        role: payload.role || "",
        permissions: payload.permissions || [],
      };

      setUser(userData);
      setToken(accessToken);
      localStorage.setItem("auth_token", accessToken);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to authenticate");
    }
  }, []);

  const logout = useCallback(() => {
    setUser(null);
    setToken(null);
    localStorage.removeItem("auth_token");
  }, []);

  const hasPermission = useCallback(
    (permission: string) => {
      return user?.permissions?.includes(permission) ?? false;
    },
    [user]
  );

  return (
    <AuthContext.Provider value={{ user, token, isLoading, error, login, logout, hasPermission }}>
      {children}
    </AuthContext.Provider>
  );
}

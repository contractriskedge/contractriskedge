/**
 * Shared session helpers for Next.js API routes and middleware.
 */

export const SESSION_COOKIE = "appSession";

export interface AppSession {
  sub: string;
  email: string;
  name: string;
  tenant_id: string;
  role: string;
  permissions: string[];
}

/** Dev user aligned with backend DEV_TENANT_ID / DEV_USER_ID. */
export const DEV_SESSION: AppSession = {
  sub: "dev-user",
  email: "dev@contractriskedge.com",
  name: "Dev User",
  tenant_id: "00000000-0000-4000-8000-000000000001",
  role: "tenant_admin",
  permissions: [
    "contracts:read",
    "contracts:write",
    "contracts:delete",
    "workflows:approve",
    "ai:analyze",
    "audit:read",
  ],
};

export function encodeSession(session: AppSession): string {
  return Buffer.from(JSON.stringify(session), "utf8").toString("base64url");
}

export function decodeSession(value: string): AppSession | null {
  try {
    const json = Buffer.from(value, "base64url").toString("utf8");
    const parsed = JSON.parse(json) as AppSession;
    if (!parsed?.sub) return null;
    return parsed;
  } catch {
    return null;
  }
}

export function sessionCookieOptions() {
  return {
    httpOnly: true,
    sameSite: "lax" as const,
    secure: process.env.NODE_ENV === "production",
    path: "/",
    maxAge: 60 * 60 * 24 * 7,
  };
}

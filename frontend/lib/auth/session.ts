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

/** Dev login button keys accepted by POST /api/auth/dev-login and /api/v1/auth/token. */
export type DevLoginRole = "admin" | "reviewer" | "legal" | "viewer";

const DEV_LOGIN_ROLE_BY_SUB: Record<string, DevLoginRole> = {
  "test-admin-1": "admin",
  "test-reviewer-1": "reviewer",
  "test-legal-1": "legal",
  "test-viewer-1": "viewer",
  "dev-user": "admin",
};

const DEV_LOGIN_ROLE_BY_JWT_ROLE: Record<string, DevLoginRole> = {
  tenant_admin: "admin",
  admin: "admin",
  reviewer: "reviewer",
  legal_reviewer: "legal",
  legal_ops: "legal",
  viewer: "viewer",
};

/** Map app session / JWT role to the dev-login role key for backend token minting. */
export function resolveDevLoginRole(session: {
  sub?: string;
  role?: string;
}): DevLoginRole | undefined {
  if (session.sub && DEV_LOGIN_ROLE_BY_SUB[session.sub]) {
    return DEV_LOGIN_ROLE_BY_SUB[session.sub];
  }
  if (session.role && DEV_LOGIN_ROLE_BY_JWT_ROLE[session.role]) {
    return DEV_LOGIN_ROLE_BY_JWT_ROLE[session.role];
  }
  return undefined;
}

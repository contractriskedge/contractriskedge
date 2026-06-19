/**
 * Development login — sets appSession cookie so middleware and /api/auth/me agree.
 *
 * Supports role-based login for testing:
 *   POST /api/auth/dev-login           → default admin (dev-user)
 *   POST /api/auth/dev-login {role}    → specific role
 *
 * Roles: admin, reviewer, legal, viewer
 */

import { NextRequest, NextResponse } from "next/server";
import {
  SESSION_COOKIE,
  AppSession,
  encodeSession,
  sessionCookieOptions,
} from "@/lib/auth/session";

const ROLES: Record<string, AppSession> = {
  admin: {
    sub: "test-admin-1",
    email: "admin@test.cre",
    name: "Test Admin",
    tenant_id: "00000000-0000-4000-8000-000000000001",
    role: "tenant_admin",
    permissions: ["*"],
  },
  reviewer: {
    sub: "test-reviewer-1",
    email: "reviewer@test.cre",
    name: "Test Reviewer",
    tenant_id: "00000000-0000-4000-8000-000000000001",
    role: "reviewer",
    permissions: [
      "contracts:read", "contracts:write",
      "ai:view",
      "workflows:read", "workflows:write",
      "reviews:export", "benchmarks:read",
    ],
  },
  legal: {
    sub: "test-legal-1",
    email: "legal@test.cre",
    name: "Test Legal",
    tenant_id: "00000000-0000-4000-8000-000000000001",
    role: "legal_reviewer",
    permissions: [
      "contracts:read", "contracts:approve", "ai:view",
      "workflows:read", "workflows:write", "workflows:approve",
      "workflows:escalate", "audit:read", "reviews:export",
      "benchmarks:read",
    ],
  },
  viewer: {
    sub: "test-viewer-1",
    email: "viewer@test.cre",
    name: "Test Viewer",
    tenant_id: "00000000-0000-4000-8000-000000000001",
    role: "viewer",
    permissions: [
      "contracts:read", "ai:view",
      "workflows:read", "audit:read",
    ],
  },
};

export async function POST(req: NextRequest) {
  // PRODUCTION HARDENING: Dev login is NEVER available in production.
  if (process.env.NODE_ENV === "production") {
    return NextResponse.json({ error: "Not available" }, { status: 403 });
  }

  let session: AppSession;

  try {
    const body = await req.json();
    const role = body?.role as string;
    if (role && ROLES[role]) {
      session = ROLES[role];
    } else {
      // Default: dev admin
      const { DEV_SESSION } = await import("@/lib/auth/session");
      session = DEV_SESSION;
    }
  } catch {
    // No body or parse error — default to dev admin
    const { DEV_SESSION } = await import("@/lib/auth/session");
    session = DEV_SESSION;
  }

  const res = NextResponse.json({ ...session });
  res.cookies.set(SESSION_COOKIE, encodeSession(session), sessionCookieOptions());
  return res;
}

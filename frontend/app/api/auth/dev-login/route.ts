/**
 * Development login — sets appSession cookie so middleware and /api/auth/me agree.
 */

import { NextResponse } from "next/server";
import {
  DEV_SESSION,
  SESSION_COOKIE,
  encodeSession,
  sessionCookieOptions,
} from "@/lib/auth/session";

export async function POST() {
  // PRODUCTION HARDENING: Dev login is NEVER available in production.
  // The NEXT_PUBLIC_DEV_AUTH env-var override is intentionally ignored
  // for NODE_ENV=production to prevent accidental exposure.
  if (process.env.NODE_ENV === "production") {
    return NextResponse.json({ error: "Not available" }, { status: 403 });
  }

  const res = NextResponse.json(DEV_SESSION);
  res.cookies.set(SESSION_COOKIE, encodeSession(DEV_SESSION), sessionCookieOptions());
  return res;
}

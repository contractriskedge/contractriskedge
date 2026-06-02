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
  if (
    process.env.NODE_ENV === "production" &&
    process.env.NEXT_PUBLIC_DEV_AUTH !== "true"
  ) {
    return NextResponse.json({ error: "Not available" }, { status: 403 });
  }

  const res = NextResponse.json(DEV_SESSION);
  res.cookies.set(SESSION_COOKIE, encodeSession(DEV_SESSION), sessionCookieOptions());
  return res;
}

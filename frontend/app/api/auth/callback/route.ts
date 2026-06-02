/**
 * Auth callback route — handles Auth0 callback after login.
 *
 * In development, redirects to dashboard.
 * In production, this validates the Auth0 callback and sets session cookies.
 */

import { NextResponse } from "next/server";
import {
  DEV_SESSION,
  SESSION_COOKIE,
  encodeSession,
  sessionCookieOptions,
} from "@/lib/auth/session";

export async function GET(req: Request) {
  const res = NextResponse.redirect(new URL("/dashboard", req.url));
  // Dev / implicit-flow callback: establish session cookie for middleware
  if (process.env.NODE_ENV === "development") {
    res.cookies.set(
      SESSION_COOKIE,
      encodeSession(DEV_SESSION),
      sessionCookieOptions(),
    );
  }
  return res;
}

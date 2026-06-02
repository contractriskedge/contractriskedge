/**
 * Auth logout route — clears session cookie and redirects to login.
 */

import { NextResponse } from "next/server";
import { SESSION_COOKIE } from "@/lib/auth/session";

export async function GET(req: Request) {
  const res = NextResponse.redirect(new URL("/auth/login", req.url));
  res.cookies.set(SESSION_COOKIE, "", { httpOnly: true, path: "/", maxAge: 0 });
  return res;
}

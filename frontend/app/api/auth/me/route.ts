/**
 * Auth me route — returns current user session from appSession cookie.
 */

import { cookies } from "next/headers";
import { NextResponse } from "next/server";
import { SESSION_COOKIE, decodeSession } from "@/lib/auth/session";

export async function GET() {
  const cookie = (await cookies()).get(SESSION_COOKIE);
  if (!cookie?.value) {
    return NextResponse.json({ error: "Not authenticated" }, { status: 401 });
  }

  const session = decodeSession(cookie.value);
  if (!session) {
    return NextResponse.json({ error: "Invalid session" }, { status: 401 });
  }

  return NextResponse.json(session);
}

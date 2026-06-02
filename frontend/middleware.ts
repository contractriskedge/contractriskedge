/**
 * Auth middleware — protects authenticated routes and handles session management.
 *
 * Redirects unauthenticated users to /auth/login.
 * Attaches tenant context for route-level authorization.
 *
 * NOTE: Uses a lightweight token check approach since @auth0/nextjs-auth0 v4.20.0
 * doesn't export edge-compatible middleware helpers. The Auth0 session is validated
 * server-side in the API routes and client-side by the AuthProvider.
 */

import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

// List of public routes that don't require authentication
const PUBLIC_ROUTES = [
  "/auth/login",
  "/auth/logout",
  "/api/auth",
  "/_next",
  "/favicon.ico",
  "/static",
];

export function middleware(req: NextRequest) {
  const { pathname } = req.nextUrl;

  // Allow public routes
  if (PUBLIC_ROUTES.some((route) => pathname.startsWith(route))) {
    return NextResponse.next();
  }

  // Check for session cookie (set by Auth0)
  const sessionCookie = req.cookies.get("appSession"); // must match lib/auth/session SESSION_COOKIE
  const isAuthenticated = !!sessionCookie?.value;

  if (!isAuthenticated) {
    const loginUrl = new URL("/auth/login", req.url);
    loginUrl.searchParams.set("returnTo", pathname);
    return NextResponse.redirect(loginUrl);
  }

  const res = NextResponse.next();

  // Inject tenant context header for downstream API calls
  // The actual tenant ID is resolved server-side from the session
  const tenantHeader = req.headers.get("x-tenant-id");
  if (tenantHeader) {
    res.headers.set("X-Tenant-ID", tenantHeader);
  }

  return res;
}

export const config = {
  matcher: [
    // Keep middleware off Next internals and API routes (incl. dev HMR upgrade requests).
    "/((?!api|_next|favicon.ico|static).*)",
  ],
};

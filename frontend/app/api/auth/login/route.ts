/**
 * Auth login route — redirects to Auth0 universal login or dev login page.
 */

import { NextResponse } from "next/server";

export async function GET(req: Request) {
  const domain = process.env.AUTH0_DOMAIN || process.env.NEXT_PUBLIC_AUTH0_DOMAIN;
  const clientId = process.env.AUTH0_CLIENT_ID || process.env.NEXT_PUBLIC_AUTH0_CLIENT_ID;
  const baseUrl = process.env.AUTH0_BASE_URL || process.env.NEXT_PUBLIC_AUTH0_BASE_URL || "http://localhost:3000";

  if (domain && clientId) {
    const auth0Url = new URL(`https://${domain}/authorize`);
    auth0Url.searchParams.set("client_id", clientId);
    auth0Url.searchParams.set("redirect_uri", `${baseUrl}/api/auth/callback`);
    auth0Url.searchParams.set("response_type", "token id_token");
    auth0Url.searchParams.set("scope", "openid profile email");
    return NextResponse.redirect(auth0Url.toString());
  }

  // Fallback: redirect to the dev login page
  return NextResponse.redirect(new URL("/auth/login", req.url));
}

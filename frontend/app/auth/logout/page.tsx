/**
 * Logout page — clears session and redirects.
 */

import { getLogoutUrl } from "@auth0/nextjs-auth0";
import { redirect } from "next/navigation";

export default function LogoutPage() {
  redirect("/api/auth/logout");
}

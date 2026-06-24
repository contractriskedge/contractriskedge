/**
 * Dashboard route — redirects to Executive Dashboard (Sprint 31.1).
 */

import { redirect } from "next/navigation";

export default function DashboardPage() {
  redirect("/executive-dashboard");
}

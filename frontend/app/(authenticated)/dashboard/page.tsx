/**
 * Dashboard route — redirects to Executive Dashboard.
 * Portfolio module was removed in Sprint 26.
 * See: /executive for executive insights.
 */

import { redirect } from "next/navigation";

export default function DashboardPage() {
  redirect("/executive");
}

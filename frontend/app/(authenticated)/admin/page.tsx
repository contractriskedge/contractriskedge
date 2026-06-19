/**
 * Admin route — admin console, user management, security.
 */

"use client";

import React from "react";
import { AdminConsole } from "@/components/dashboard/admin/AdminConsole";
import { ProtectedRoute } from "@/components/auth/ProtectedRoute";

export default function AdminRoute() {
  return (
    <ProtectedRoute permission={["admin:tenant", "audit:read"]} requireAll={false}>
      <AdminConsole />
    </ProtectedRoute>
  );
}

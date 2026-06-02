/**
 * Settings route — tenant and user settings.
 */

"use client";

import React from "react";
import { useAuth } from "@/components/auth/AuthProvider";
import { TenantSettings } from "@/components/tenant/TenantSettings";
import { SettingsPage } from "@/components/dashboard/SettingsPage";

export default function SettingsRoute() {
  const { user } = useAuth();
  return user?.tenant_id ? <TenantSettings tenantId={user.tenant_id} /> : <SettingsPage />;
}

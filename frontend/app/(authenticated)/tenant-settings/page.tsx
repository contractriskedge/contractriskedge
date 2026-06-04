/**
 * Tenant Settings route — tenant configuration and customization.
 */

"use client";

import React from "react";
import { useAuth } from "@/components/auth/AuthProvider";
import { TenantSettings } from "@/components/tenant/TenantSettings";

export default function TenantSettingsRoute() {
  const { user } = useAuth();
  return user?.tenant_id ? <TenantSettings tenantId={user.tenant_id} /> : null;
}

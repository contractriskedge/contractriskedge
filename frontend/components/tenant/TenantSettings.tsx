/**
 * TenantSettings — Tenant customization and configuration UI.
 *
 * Sprint 7 Priority 5.
 *
 * Provides:
 * - White-label branding (logo, colors, favicon, custom CSS)
 * - Feature flag toggles per tenant
 * - Custom risk weight configuration
 * - Workflow builder (visual workflow editor)
 * - Compliance pack selector (regional packs)
 * - Custom routing rules editor
 *
 * Status: Scaffold — pending Sprint 7 implementation.
 */

"use client";

import React from "react";

interface TenantSettingsProps {
  tenantId: string;
}

export function TenantSettings({ tenantId }: TenantSettingsProps) {
  return (
    <div className="p-6">
      <div className="bg-gradient-to-br from-sky-50 to-blue-50 dark:from-sky-900/20 dark:to-blue-900/20 rounded-xl border border-sky-200 dark:border-sky-800 p-8 text-center">
        <div className="w-16 h-16 mx-auto mb-4 rounded-2xl bg-sky-100 dark:bg-sky-800 flex items-center justify-center">
          <svg className="w-8 h-8 text-sky-600 dark:text-sky-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>
        </div>
        <h2 className="text-xl font-bold text-navy-900 dark:text-white mb-2">Tenant Customization</h2>
        <p className="text-sm text-gray-500 dark:text-gray-400 mb-6 max-w-md mx-auto">
          Configure tenant-specific branding, risk models, workflows, feature flags,
          compliance packs, and routing rules. Each tenant operates with its own profile.
        </p>
        <div className="flex items-center justify-center gap-2">
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-sky-100 text-sky-700 dark:bg-sky-800 dark:text-sky-300">
            Sprint 7
          </span>
          <span className="text-xs text-gray-400">|</span>
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-700 dark:bg-yellow-800 dark:text-yellow-300">
            <span className="w-1.5 h-1.5 rounded-full bg-yellow-500" />
            In Development
          </span>
        </div>
      </div>
    </div>
  );
}

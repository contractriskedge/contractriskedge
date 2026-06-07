/**
 * TenantSettings — Tenant customization and configuration UI.
 *
 * Sprint 23 Task 2.7 — Complete Settings module.
 *
 * Tabs:
 *   General       — Branding, AI config, risk thresholds, SLA, email redirect
 *   Features      — Feature flag toggle list with override support
 *   Policy Packs  — Manage bundled policy/threshold/clause overrides
 *   Scoring       — Per-clause-type scoring overrides
 *   Compliance    — Regional compliance packs
 *   Summary       — Configuration overview with health indicators
 */

"use client";

import React, { useState } from "react";
import { motion } from "framer-motion";
import { Settings2, Flag, Package, Gauge, Shield, BarChart3 } from "lucide-react";
import { GeneralSettingsForm } from "./GeneralSettingsForm";
import { FeatureFlagList } from "./FeatureFlagList";
import { PolicyPackList } from "./PolicyPackList";
import { ScoringOverrideList } from "./ScoringOverrideList";
import { CompliancePackList } from "./CompliancePackList";
import { TenantSummary } from "./TenantSummary";

interface TenantSettingsProps {
  tenantId: string;
}

type SettingsTab = "general" | "features" | "policy-packs" | "scoring" | "compliance" | "summary";

const tabs: { id: SettingsTab; label: string; icon: React.ComponentType<{ className?: string }> }[] = [
  { id: "general", label: "General", icon: Settings2 },
  { id: "features", label: "Features", icon: Flag },
  { id: "policy-packs", label: "Policy Packs", icon: Package },
  { id: "scoring", label: "Scoring", icon: Gauge },
  { id: "compliance", label: "Compliance", icon: Shield },
  { id: "summary", label: "Summary", icon: BarChart3 },
];

export function TenantSettings({ tenantId }: TenantSettingsProps) {
  const [activeTab, setActiveTab] = useState<SettingsTab>("general");

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-navy-900">Tenant Settings</h1>
        <p className="text-sm text-gray-500 mt-1">
          Configure tenant-specific branding, AI, risk thresholds, SLA targets, feature flags,
          policy packs, scoring overrides, compliance packs, and more
        </p>
      </div>

      {/* Tab bar */}
      <div className="flex items-center gap-1 border-b border-gray-200 overflow-x-auto">
        {tabs.map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors whitespace-nowrap ${
                isActive
                  ? "border-gold-500 text-gold-700"
                  : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
              }`}
            >
              <Icon className="w-4 h-4" />
              {tab.label}
            </button>
          );
        })}
      </div>

      {/* Tab content */}
      <motion.div
        key={activeTab}
        initial={{ opacity: 0, y: 4 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.15 }}
      >
        {activeTab === "general" && <GeneralSettingsForm />}
        {activeTab === "features" && <FeatureFlagList tenantId={tenantId} />}
        {activeTab === "policy-packs" && <PolicyPackList />}
        {activeTab === "scoring" && <ScoringOverrideList />}
        {activeTab === "compliance" && <CompliancePackList />}
        {activeTab === "summary" && <TenantSummary />}
      </motion.div>
    </div>
  );
}

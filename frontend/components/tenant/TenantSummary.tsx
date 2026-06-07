/**
 * TenantSummary — Overview dashboard of tenant configuration.
 * Displays counts, health indicators, and configuration status.
 */

"use client";

import React from "react";
import { motion } from "framer-motion";
import {
  Loader2, AlertCircle, RefreshCw,
  Flag, Package, Gauge, Shield, CheckCircle2, XCircle, AlertTriangle,
} from "lucide-react";
import { useTenantSummary } from "@/services/hooks/useTenantModules";

function StatCard({ icon: Icon, label, value, color }: {
  icon: React.ComponentType<{ className?: string }>;
  label: string; value: number | string; color: string;
}) {
  return (
    <div className="p-4 rounded-lg border border-gray-200 bg-white">
      <div className="flex items-center gap-3">
        <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${color}`}>
          <Icon className="w-5 h-5 text-white" />
        </div>
        <div>
          <p className="text-2xl font-bold text-gray-900">{value}</p>
          <p className="text-xs text-gray-500">{label}</p>
        </div>
      </div>
    </div>
  );
}

export function TenantSummary() {
  const { data: summary, isLoading, error, refetch } = useTenantSummary();

  if (isLoading) return <div className="flex justify-center py-16"><Loader2 className="w-8 h-8 text-gold-400 animate-spin" /></div>;
  if (error) return (
    <div className="text-center py-16">
      <AlertCircle className="w-10 h-10 text-red-400 mx-auto mb-3" />
      <p className="text-sm font-medium text-gray-900 mb-1">Failed to load summary</p>
      <p className="text-xs text-gray-500 mb-3">{(error as Error)?.message}</p>
      <button onClick={() => refetch()} className="text-xs text-gold-600 inline-flex items-center gap-1"><RefreshCw className="w-3 h-3" /> Retry</button>
    </div>
  );
  if (!summary) return null;

  const enabledFlags = summary.feature_flags?.filter((f) => f.enabled).length ?? 0;
  const totalFlags = summary.feature_flags?.length ?? 0;
  const policyCount = summary.active_policy_packs?.length ?? 0;
  const scoringCount = summary.scoring_overrides?.length ?? 0;
  const complianceCount = summary.compliance_packs?.length ?? 0;
  const buCount = summary.business_units?.length ?? 0;

  const healthIndicators = [
    { label: "Feature Flags", ok: totalFlags > 0, detail: `${enabledFlags}/${totalFlags} enabled` },
    { label: "Policy Packs", ok: policyCount > 0, detail: `${policyCount} active` },
    { label: "Scoring Overrides", ok: scoringCount >= 0, detail: `${scoringCount} configured` },
    { label: "Compliance Packs", ok: complianceCount > 0, detail: `${complianceCount} active` },
    { label: "Business Units", ok: buCount > 0, detail: `${buCount} configured` },
    { label: "Configuration", ok: summary.configuration_version > 0, detail: `v${summary.configuration_version}` },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-lg font-semibold text-navy-900">{summary.tenant_name}</h2>
        <p className="text-xs text-gray-500 mt-0.5">Plan: {summary.plan} · Tenant ID: {summary.tenant_id.slice(0, 8)}...</p>
      </div>

      {/* Stats grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <StatCard icon={Flag} label="Feature Flags" value={`${enabledFlags}/${totalFlags}`} color="bg-purple-500" />
        <StatCard icon={Package} label="Policy Packs" value={policyCount} color="bg-blue-500" />
        <StatCard icon={Gauge} label="Scoring Overrides" value={scoringCount} color="bg-amber-500" />
        <StatCard icon={Shield} label="Compliance Packs" value={complianceCount} color="bg-emerald-500" />
      </div>

      {/* Health indicators */}
      <div>
        <h3 className="text-sm font-semibold text-gray-900 mb-3">Configuration Health</h3>
        <div className="space-y-2">
          {healthIndicators.map((h) => (
            <motion.div key={h.label} initial={{ opacity: 0, x: -4 }} animate={{ opacity: 1, x: 0 }}
              className="flex items-center gap-3 p-3 rounded-lg border border-gray-200 bg-white"
            >
              {h.ok ? (
                <CheckCircle2 className="w-5 h-5 text-emerald-500 flex-shrink-0" />
              ) : (
                <AlertTriangle className="w-5 h-5 text-amber-400 flex-shrink-0" />
              )}
              <div className="flex-1">
                <p className="text-sm font-medium text-gray-900">{h.label}</p>
                <p className="text-xs text-gray-500">{h.detail}</p>
              </div>
            </motion.div>
          ))}
        </div>
      </div>

      {/* Business Units */}
      <div>
        <h3 className="text-sm font-semibold text-gray-900 mb-2">Business Units ({buCount})</h3>
        <div className="flex flex-wrap gap-2">
          {summary.business_units?.map((bu) => (
            <span key={bu} className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-700">
              {bu}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}

/**
 * GeneralSettingsForm — Edit tenant settings (branding, AI, risk thresholds, SLA).
 *
 * Loads current settings from useTenantSettings and provides a form to update them
 * via useUpdateTenantSettings with optimistic UI and success/error feedback.
 */

"use client";

import React, { useState, useEffect, useCallback } from "react";
import { motion } from "framer-motion";
import {
  Loader2,
  AlertCircle,
  RefreshCw,
  Save,
  CheckCircle2,
  XCircle,
} from "lucide-react";
import {
  useTenantSettings,
  useUpdateTenantSettings,
} from "@/services/hooks/useTenantSettings";
import type { TenantSettingsUpdate } from "@/services/api/tenant";

export function GeneralSettingsForm() {
  const { data: settings, isLoading, error, refetch } = useTenantSettings();
  const updateSettings = useUpdateTenantSettings();

  const [form, setForm] = useState<TenantSettingsUpdate>({});
  const [isDirty, setIsDirty] = useState(false);
  const [feedback, setFeedback] = useState<{
    type: "success" | "error";
    message: string;
  } | null>(null);

  // Populate form when data loads
  useEffect(() => {
    if (settings) {
      setForm({
        brand_name: settings.brand_name ?? undefined,
        brand_primary_color: settings.brand_primary_color,
        brand_accent_color: settings.brand_accent_color,
        ai_model: settings.ai_model,
        ai_temperature: settings.ai_temperature,
        ai_max_tokens: settings.ai_max_tokens,
        risk_threshold_critical: settings.risk_threshold_critical,
        risk_threshold_high: settings.risk_threshold_high,
        risk_threshold_medium: settings.risk_threshold_medium,
        sla_critical_hours: settings.sla_critical_hours,
        sla_high_hours: settings.sla_high_hours,
        sla_medium_hours: settings.sla_medium_hours,
        sla_low_hours: settings.sla_low_hours,
        email_redirect_enabled: settings.email_redirect_enabled,
        email_redirect_to: settings.email_redirect_to,
      });
      setIsDirty(false);
    }
  }, [settings]);

  const handleChange = useCallback(
    (key: keyof TenantSettingsUpdate, value: unknown) => {
      setForm((prev) => ({ ...prev, [key]: value }));
      setIsDirty(true);
    },
    [],
  );

  const handleSave = useCallback(() => {
    updateSettings.mutate(form, {
      onSuccess: () => {
        setIsDirty(false);
        setFeedback({ type: "success", message: "Settings saved successfully" });
        setTimeout(() => setFeedback(null), 3000);
      },
      onError: (err) => {
        setFeedback({
          type: "error",
          message: `Failed to save: ${(err as Error).message}`,
        });
        setTimeout(() => setFeedback(null), 5000);
      },
    });
  }, [form, updateSettings]);

  // Loading state
  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-48">
        <div className="text-center">
          <Loader2 className="w-6 h-6 text-gold-400 animate-spin mx-auto mb-2" />
          <p className="text-sm text-gray-500">Loading settings...</p>
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="flex items-center justify-center h-48">
        <div className="text-center max-w-md">
          <AlertCircle className="w-8 h-8 text-red-400 mx-auto mb-2" />
          <p className="text-sm font-medium text-gray-900 mb-1">Failed to load settings</p>
          <p className="text-xs text-gray-500 mb-3">{(error as Error)?.message || "An unexpected error occurred"}</p>
          <button
            onClick={() => refetch()}
            className="inline-flex items-center gap-1.5 text-xs font-medium text-gold-600 hover:text-gold-700"
          >
            <RefreshCw className="w-3.5 h-3.5" /> Retry
          </button>
        </div>
      </div>
    );
  }

  // Empty state
  if (!settings) {
    return (
      <div className="flex items-center justify-center h-48">
        <div className="text-center">
          <p className="text-sm text-gray-500">No settings available</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Feedback toast */}
      {feedback && (
        <motion.div
          initial={{ opacity: 0, y: -8 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -8 }}
          className={`flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium ${
            feedback.type === "success"
              ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
              : "bg-red-50 text-red-700 border border-red-200"
          }`}
        >
          {feedback.type === "success" ? (
            <CheckCircle2 className="w-4 h-4 flex-shrink-0" />
          ) : (
            <XCircle className="w-4 h-4 flex-shrink-0" />
          )}
          {feedback.message}
        </motion.div>
      )}

      {/* Branding section */}
      <section>
        <h3 className="text-sm font-semibold text-gray-900 mb-3">Branding</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Brand Name</label>
            <input
              type="text"
              value={form.brand_name ?? ""}
              onChange={(e) => handleChange("brand_name", e.target.value)}
              className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-gold-400 focus:border-transparent"
              placeholder="My Company"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Primary Color</label>
            <div className="flex items-center gap-2">
              <input
                type="color"
                value={form.brand_primary_color ?? "#1B3A6B"}
                onChange={(e) => handleChange("brand_primary_color", e.target.value)}
                className="w-9 h-9 rounded border border-gray-200 cursor-pointer"
              />
              <input
                type="text"
                value={form.brand_primary_color ?? ""}
                onChange={(e) => handleChange("brand_primary_color", e.target.value)}
                className="flex-1 px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-gold-400 focus:border-transparent font-mono"
              />
            </div>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Accent Color</label>
            <div className="flex items-center gap-2">
              <input
                type="color"
                value={form.brand_accent_color ?? "#C9A84C"}
                onChange={(e) => handleChange("brand_accent_color", e.target.value)}
                className="w-9 h-9 rounded border border-gray-200 cursor-pointer"
              />
              <input
                type="text"
                value={form.brand_accent_color ?? ""}
                onChange={(e) => handleChange("brand_accent_color", e.target.value)}
                className="flex-1 px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-gold-400 focus:border-transparent font-mono"
              />
            </div>
          </div>
        </div>
      </section>

      {/* AI Configuration section */}
      <section>
        <h3 className="text-sm font-semibold text-gray-900 mb-3">AI Configuration</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">AI Model</label>
            <select
              value={form.ai_model ?? "gpt-4o"}
              onChange={(e) => handleChange("ai_model", e.target.value)}
              className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-gold-400 focus:border-transparent"
            >
              <option value="gpt-4o">GPT-4o</option>
              <option value="gpt-4o-mini">GPT-4o Mini</option>
              <option value="gpt-4-turbo">GPT-4 Turbo</option>
              <option value="claude-3-opus">Claude 3 Opus</option>
              <option value="claude-3-sonnet">Claude 3 Sonnet</option>
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">
              Temperature ({form.ai_temperature ?? 10}%)
            </label>
            <input
              type="range"
              min={0}
              max={100}
              value={form.ai_temperature ?? 10}
              onChange={(e) => handleChange("ai_temperature", parseInt(e.target.value))}
              className="w-full accent-gold-500"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Max Tokens</label>
            <select
              value={form.ai_max_tokens ?? 4096}
              onChange={(e) => handleChange("ai_max_tokens", parseInt(e.target.value))}
              className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-gold-400 focus:border-transparent"
            >
              <option value={2048}>2,048</option>
              <option value={4096}>4,096</option>
              <option value={8192}>8,192</option>
              <option value={16384}>16,384</option>
              <option value={32768}>32,768</option>
            </select>
          </div>
        </div>
      </section>

      {/* Risk Thresholds section */}
      <section>
        <h3 className="text-sm font-semibold text-gray-900 mb-3">Risk Thresholds</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">
              Critical (≥{form.risk_threshold_critical ?? 70})
            </label>
            <input
              type="range"
              min={0}
              max={100}
              value={form.risk_threshold_critical ?? 70}
              onChange={(e) => handleChange("risk_threshold_critical", parseInt(e.target.value))}
              className="w-full accent-red-500"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">
              High (≥{form.risk_threshold_high ?? 50})
            </label>
            <input
              type="range"
              min={0}
              max={100}
              value={form.risk_threshold_high ?? 50}
              onChange={(e) => handleChange("risk_threshold_high", parseInt(e.target.value))}
              className="w-full accent-orange-500"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">
              Medium (≥{form.risk_threshold_medium ?? 30})
            </label>
            <input
              type="range"
              min={0}
              max={100}
              value={form.risk_threshold_medium ?? 30}
              onChange={(e) => handleChange("risk_threshold_medium", parseInt(e.target.value))}
              className="w-full accent-amber-500"
            />
          </div>
        </div>
      </section>

      {/* SLA Thresholds section */}
      <section>
        <h3 className="text-sm font-semibold text-gray-900 mb-3">SLA Thresholds (hours)</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Critical</label>
            <input
              type="number"
              min={1}
              value={form.sla_critical_hours ?? 24}
              onChange={(e) => handleChange("sla_critical_hours", parseInt(e.target.value) || 1)}
              className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-gold-400 focus:border-transparent"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">High</label>
            <input
              type="number"
              min={1}
              value={form.sla_high_hours ?? 48}
              onChange={(e) => handleChange("sla_high_hours", parseInt(e.target.value) || 1)}
              className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-gold-400 focus:border-transparent"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Medium</label>
            <input
              type="number"
              min={1}
              value={form.sla_medium_hours ?? 72}
              onChange={(e) => handleChange("sla_medium_hours", parseInt(e.target.value) || 1)}
              className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-gold-400 focus:border-transparent"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Low</label>
            <input
              type="number"
              min={1}
              value={form.sla_low_hours ?? 168}
              onChange={(e) => handleChange("sla_low_hours", parseInt(e.target.value) || 1)}
              className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-gold-400 focus:border-transparent"
            />
          </div>
        </div>
      </section>

      {/* Email section */}
      <section>
        <h3 className="text-sm font-semibold text-gray-900 mb-3">Email Redirect</h3>
        <div className="space-y-3">
          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={form.email_redirect_enabled ?? false}
              onChange={(e) => handleChange("email_redirect_enabled", e.target.checked)}
              className="rounded border-gray-300 text-gold-500 focus:ring-gold-400"
            />
            <span className="text-sm text-gray-700">Enable email redirect</span>
          </label>
          {form.email_redirect_enabled && (
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Redirect To</label>
              <input
                type="email"
                value={form.email_redirect_to ?? ""}
                onChange={(e) => handleChange("email_redirect_to", e.target.value)}
                className="w-full max-w-md px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-gold-400 focus:border-transparent"
                placeholder="admin@example.com"
              />
            </div>
          )}
        </div>
      </section>

      {/* Save button */}
      <div className="flex items-center gap-3 pt-2">
        <button
          onClick={handleSave}
          disabled={!isDirty || updateSettings.isPending}
          className={`inline-flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg transition-colors ${
            !isDirty || updateSettings.isPending
              ? "bg-gray-100 text-gray-400 cursor-not-allowed"
              : "bg-navy-700 text-white hover:bg-navy-800 shadow-sm"
          }`}
        >
          {updateSettings.isPending ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <Save className="w-4 h-4" />
          )}
          {updateSettings.isPending ? "Saving..." : "Save Changes"}
        </button>
        {!isDirty && (
          <span className="text-xs text-gray-400">No changes to save</span>
        )}
      </div>
    </div>
  );
}

/**
 * FeatureFlagList — Interactive feature flag management component.
 *
 * Displays all feature flag definitions with their current evaluated state
 * and allows toggling overrides on/off with optimistic UI updates.
 */

"use client";

import React, { useState, useCallback } from "react";
import { motion } from "framer-motion";
import {
  ToggleLeft,
  ToggleRight,
  Loader2,
  AlertCircle,
  RefreshCw,
  Info,
  CheckCircle2,
  XCircle,
} from "lucide-react";
import {
  useFeatureFlagsWithValues,
  useSetFeatureOverride,
} from "@/services/hooks/useTenantSettings";
import type { FeatureFlagWithValue } from "@/services/hooks/useTenantSettings";

interface FeatureFlagListProps {
  tenantId: string;
}

export function FeatureFlagList({ tenantId }: FeatureFlagListProps) {
  const { data: flags, isLoading, error, refetch } = useFeatureFlagsWithValues();
  const setOverride = useSetFeatureOverride();
  const [feedback, setFeedback] = useState<{
    type: "success" | "error";
    message: string;
    flagKey: string;
  } | null>(null);

  const handleToggle = useCallback(
    (flag: FeatureFlagWithValue) => {
      const currentEnabled = flag.evaluation?.enabled ?? flag.definition.default_enabled;
      const newEnabled = !currentEnabled;

      setOverride.mutate(
        {
          flag_key: flag.definition.flag_key,
          target_type: "tenant",
          target_id: tenantId,
          enabled: newEnabled,
          reason: `Toggled via Settings UI`,
        },
        {
          onSuccess: () => {
            setFeedback({
              type: "success",
              message: `${flag.definition.name} ${newEnabled ? "enabled" : "disabled"}`,
              flagKey: flag.definition.flag_key,
            });
            setTimeout(() => setFeedback(null), 3000);
          },
          onError: (err) => {
            setFeedback({
              type: "error",
              message: `Failed to update ${flag.definition.name}: ${(err as Error).message}`,
              flagKey: flag.definition.flag_key,
            });
            setTimeout(() => setFeedback(null), 5000);
          },
        },
      );
    },
    [setOverride],
  );

  // Loading state
  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-48">
        <div className="text-center">
          <Loader2 className="w-6 h-6 text-gold-400 animate-spin mx-auto mb-2" />
          <p className="text-sm text-gray-500">Loading feature flags...</p>
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
          <p className="text-sm font-medium text-gray-900 mb-1">Failed to load feature flags</p>
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
  if (!flags || flags.length === 0) {
    return (
      <div className="flex items-center justify-center h-48">
        <div className="text-center">
          <Info className="w-8 h-8 text-gray-300 mx-auto mb-2" />
          <p className="text-sm text-gray-500">No feature flags defined</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-3">
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

      {/* Flag list */}
      <div className="space-y-2">
        {flags.map((flag) => {
          const currentEnabled = flag.evaluation?.enabled ?? flag.definition.default_enabled;
          const isPending = setOverride.isPending && setOverride.variables?.flag_key === flag.definition.flag_key;

          return (
            <motion.div
              key={flag.definition.flag_key}
              initial={{ opacity: 0, y: 4 }}
              animate={{ opacity: 1, y: 0 }}
              className="flex items-start gap-4 p-4 rounded-lg border border-gray-200 bg-white hover:border-gray-300 transition-colors"
            >
              {/* Toggle button */}
              <button
                onClick={() => handleToggle(flag)}
                disabled={isPending}
                className={`flex-shrink-0 mt-0.5 transition-colors ${
                  isPending ? "opacity-50 cursor-not-allowed" : "cursor-pointer"
                }`}
                title={currentEnabled ? "Click to disable" : "Click to enable"}
              >
                {isPending ? (
                  <Loader2 className="w-6 h-6 text-gray-400 animate-spin" />
                ) : currentEnabled ? (
                  <ToggleRight className="w-6 h-6 text-emerald-500" />
                ) : (
                  <ToggleLeft className="w-6 h-6 text-gray-300" />
                )}
              </button>

              {/* Flag info */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <h3 className="text-sm font-medium text-gray-900">
                    {flag.definition.name}
                  </h3>
                  <span
                    className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${
                      currentEnabled
                        ? "bg-emerald-50 text-emerald-700"
                        : "bg-gray-50 text-gray-500"
                    }`}
                  >
                    {currentEnabled ? "Enabled" : "Disabled"}
                  </span>
                  {flag.evaluation?.source !== "default" && (
                    <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-amber-50 text-amber-700">
                      Overridden
                    </span>
                  )}
                </div>
                <p className="text-xs text-gray-500 mt-0.5">
                  {flag.definition.description}
                </p>
                {flag.evaluation?.source && (
                  <p className="text-xs text-gray-400 mt-1">
                    Source: {flag.evaluation.source}
                    {flag.evaluation.reason && ` — ${flag.evaluation.reason}`}
                  </p>
                )}
                {flag.definition.dependencies.length > 0 && (
                  <p className="text-xs text-gray-400 mt-0.5">
                    Depends on: {flag.definition.dependencies.join(", ")}
                  </p>
                )}
              </div>
            </motion.div>
          );
        })}
      </div>
    </div>
  );
}

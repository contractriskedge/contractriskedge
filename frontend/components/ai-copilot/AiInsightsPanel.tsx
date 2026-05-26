"use client";

import React, { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { AlertTriangle, AlertOctagon, Clock, Lightbulb, X, ChevronRight, Zap, FileText, Sparkles } from "lucide-react";
import type { AiInsight, AiSuggestedAction } from "./types";
import { aiService } from "./service";
import { useCopilotContext } from "./context";

const severityCfg: Record<string, { icon: React.ReactNode; border: string; bg: string; dot: string }> = {
  critical: { icon: <AlertTriangle className="w-3.5 h-3.5 text-red-500" />, border: "border-l-red-500", bg: "bg-red-50", dot: "bg-red-500" },
  warning: { icon: <AlertOctagon className="w-3.5 h-3.5 text-orange-500" />, border: "border-l-orange-500", bg: "bg-orange-50", dot: "bg-orange-500" },
  info: { icon: <Clock className="w-3.5 h-3.5 text-blue-500" />, border: "border-l-blue-500", bg: "bg-blue-50", dot: "bg-blue-500" },
  success: { icon: <Lightbulb className="w-3.5 h-3.5 text-green-500" />, border: "border-l-green-500", bg: "bg-green-50", dot: "bg-green-500" },
};

interface AiInsightsPanelProps {
  onExecuteAction: (action: AiSuggestedAction) => void;
}

export function AiInsightsPanel({ onExecuteAction }: AiInsightsPanelProps) {
  const ctx = useCopilotContext();
  const [insights, setInsights] = useState<AiInsight[]>([]);
  const [loading, setLoading] = useState(false);
  const [dismissed, setDismissed] = useState<Set<string>>(new Set());

  useEffect(() => {
    setLoading(true);
    aiService.generateInsights(ctx).then((result) => {
      setInsights((prev) => {
        const existingIds = new Set(prev.map((i) => i.id));
        const newInsights = result.filter((i) => !existingIds.has(i.id));
        return [...newInsights, ...prev].slice(0, 10);
      });
      setLoading(false);
    });
  }, [ctx.currentScreen, ctx.selectedEntityId]);

  const visible = insights.filter((i) => !i.dismissed && !dismissed.has(i.id));
  const criticalCount = visible.filter((i) => i.severity === "critical").length;

  if (visible.length === 0 && !loading) return null;

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between px-1">
        <div className="flex items-center gap-1.5">
          <Sparkles className="w-3.5 h-3.5 text-navy-600" />
          <span className="text-[10px] font-semibold text-navy-700 uppercase">AI Insights</span>
          {criticalCount > 0 && (
            <span className="text-[9px] font-bold text-red-600 bg-red-50 px-1.5 py-0.5 rounded-full">{criticalCount} critical</span>
          )}
        </div>
        {loading && <div className="w-3 h-3 border-2 border-navy-300 border-t-navy-600 rounded-full animate-spin" />}
      </div>
      <div className="space-y-1.5 max-h-[300px] overflow-y-auto pr-1">
        <AnimatePresence>
          {visible.map((insight) => {
            const cfg = severityCfg[insight.severity];
            return (
              <motion.div
                key={insight.id}
                initial={{ opacity: 0, x: -8, height: 0 }}
                animate={{ opacity: 1, x: 0, height: "auto" }}
                exit={{ opacity: 0, x: 8, height: 0 }}
                className={`border-l-3 ${cfg.border} bg-white rounded-lg border border-gray-200 shadow-sm p-2.5`}
              >
                <div className="flex items-start gap-2">
                  <div className="mt-0.5 flex-shrink-0">{cfg.icon}</div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-1 mb-0.5">
                      <h4 className="text-[11px] font-semibold text-navy-900">{insight.title}</h4>
                      <span className="text-[9px] text-gray-400 ml-auto">{insight.confidence}%</span>
                    </div>
                    <p className="text-[10px] text-gray-600 leading-relaxed line-clamp-2">{insight.description}</p>
                    {insight.suggestedActions.length > 0 && (
                      <div className="mt-1.5 flex gap-1">
                        {insight.suggestedActions.slice(0, 2).map((action) => (
                          <button
                            key={action.id}
                            onClick={() => onExecuteAction(action)}
                            className="text-[9px] px-1.5 py-0.5 rounded bg-navy-50 text-navy-700 hover:bg-navy-100 transition-colors flex items-center gap-0.5"
                          >
                            <Zap className="w-2.5 h-2.5" />
                            {action.label}
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                  <button
                    onClick={() => setDismissed((prev) => new Set(prev).add(insight.id))}
                    className="p-0.5 rounded hover:bg-gray-100 text-gray-300 hover:text-gray-500 transition-colors flex-shrink-0"
                  >
                    <X className="w-3 h-3" />
                  </button>
                </div>
              </motion.div>
            );
          })}
        </AnimatePresence>
      </div>
    </div>
  );
}

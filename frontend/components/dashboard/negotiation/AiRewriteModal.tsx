"use client";

import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  X, Sparkles, Loader2, Check, Copy, AlertTriangle,
  FileText, Brain, ArrowRight, Info, Shield, TrendingUp,
  BookOpen, Lightbulb,
} from "lucide-react";
import { negotiationsService } from "@/services/api/negotiations";

// ── Types ────────────────────────────────────────────────────────

interface AiRewriteResult {
  original_text: string;
  rewritten_text: string;
  strategy: string;
  changes: { description: string }[];
  model_used: string;
}

interface AiExplanation {
  explanation: string;
  changes: { description: string }[];
  risks_addressed: string[];
  benefits: string[];
}

interface AiRewriteModalProps {
  isOpen: boolean;
  onClose: () => void;
  sessionId: string;
  clauseId: string;
  clauseTitle: string;
  clauseText: string;
  clauseSectionNumber: string;
  onRewriteApplied: (result: AiRewriteResult) => void;
}

// ── Strategy Descriptions ─────────────────────────────────────────

const STRATEGIES = [
  {
    id: "balanced",
    label: "Balanced",
    description: "Fair middle-ground language protecting both parties' interests",
    icon: "⚖️",
    color: "border-blue-300 bg-blue-50 dark:border-blue-800 dark:bg-blue-900/20",
    activeColor: "ring-blue-500 border-blue-500",
  },
  {
    id: "customer_protective",
    label: "Customer Protective",
    description: "Maximizes protections for the customer",
    icon: "🛡️",
    color: "border-emerald-300 bg-emerald-50 dark:border-emerald-800 dark:bg-emerald-900/20",
    activeColor: "ring-emerald-500 border-emerald-500",
  },
  {
    id: "supplier_protective",
    label: "Supplier Protective",
    description: "Pro-supplier wording minimizing liability",
    icon: "🏢",
    color: "border-amber-300 bg-amber-50 dark:border-amber-800 dark:bg-amber-900/20",
    activeColor: "ring-amber-500 border-amber-500",
  },
  {
    id: "legal_standard",
    label: "Legal Standard",
    description: "Industry-standard neutral language",
    icon: "📋",
    color: "border-purple-300 bg-purple-50 dark:border-purple-800 dark:bg-purple-900/20",
    activeColor: "ring-purple-500 border-purple-500",
  },
  {
    id: "aggressive",
    label: "Aggressive",
    description: "Maximally favorable to your side",
    icon: "⚡",
    color: "border-red-300 bg-red-50 dark:border-red-800 dark:bg-red-900/20",
    activeColor: "ring-red-500 border-red-500",
  },
  {
    id: "fallback",
    label: "Fallback Position",
    description: "Pre-approved compromise language",
    icon: "🤝",
    color: "border-teal-300 bg-teal-50 dark:border-teal-800 dark:bg-teal-900/20",
    activeColor: "ring-teal-500 border-teal-500",
  },
];

// ── AI Rewrite Modal ──────────────────────────────────────────────

export function AiRewriteModal({
  isOpen, onClose, sessionId, clauseId, clauseTitle,
  clauseText, clauseSectionNumber, onRewriteApplied,
}: AiRewriteModalProps) {
  const [strategy, setStrategy] = useState<string>("balanced");
  const [context, setContext] = useState("");
  const [isGenerating, setIsGenerating] = useState(false);
  const [result, setResult] = useState<AiRewriteResult | null>(null);
  const [explanation, setExplanation] = useState<AiExplanation | null>(null);
  const [isLoadingExplanation, setIsLoadingExplanation] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [showExplanation, setShowExplanation] = useState(false);

  const handleGenerate = async () => {
    setIsGenerating(true);
    setError(null);
    setResult(null);
    setExplanation(null);
    setShowExplanation(false);

    try {
      const response = await negotiationsService.aiRewrite(sessionId, clauseId, {
        clause_text: clauseText,
        strategy,
        context: context.trim() || undefined,
      });
      setResult(response);
      onRewriteApplied(response);
    } catch (err: any) {
      setError(err?.message || "AI rewrite failed. Please try again.");
    } finally {
      setIsGenerating(false);
    }
  };

  const handleExplain = async () => {
    if (!result) return;
    setIsLoadingExplanation(true);
    try {
      const resp = await negotiationsService.aiExplain(sessionId, clauseId, {
        original_text: result.original_text,
        rewritten_text: result.rewritten_text,
        strategy: result.strategy,
      });
      setExplanation(resp);
      setShowExplanation(true);
    } catch {
      setExplanation({
        explanation: "Analysis not available for this rewrite.",
        changes: [],
        risks_addressed: [],
        benefits: [],
      });
      setShowExplanation(true);
    } finally {
      setIsLoadingExplanation(false);
    }
  };

  const handleCopy = async () => {
    if (!result) return;
    await navigator.clipboard.writeText(result.rewritten_text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleApply = () => {
    if (!result) return;
    onRewriteApplied(result);
    onClose();
  };

  const handleReset = () => {
    setResult(null);
    setError(null);
    setCopied(false);
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/30 z-50"
            onClick={onClose}
          />

          {/* Modal */}
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 20 }}
            transition={{ type: "spring", damping: 25, stiffness: 300 }}
            className="fixed inset-0 z-50 flex items-center justify-center p-4"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="bg-white dark:bg-navy-800 rounded-xl shadow-2xl border border-gray-200 dark:border-navy-700 w-full max-w-2xl max-h-[85vh] flex flex-col">
              {/* Header */}
              <div className="flex items-center justify-between px-5 py-4 border-b border-gray-200 dark:border-navy-700">
                <div className="flex items-center gap-2">
                  <div className="w-8 h-8 rounded-lg bg-purple-100 dark:bg-purple-900/30 flex items-center justify-center">
                    <Brain className="w-4 h-4 text-purple-600 dark:text-purple-400" />
                  </div>
                  <div>
                    <h3 className="text-sm font-semibold text-navy-900 dark:text-white">AI Rewrite</h3>
                    <p className="text-[10px] text-gray-500">
                      {clauseTitle} &middot; {clauseSectionNumber}
                    </p>
                  </div>
                </div>
                <button
                  onClick={onClose}
                  className="p-1 rounded hover:bg-gray-100 dark:hover:bg-navy-700 text-gray-400 transition-colors"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              {/* Body */}
              <div className="flex-1 overflow-y-auto p-5 space-y-4">
                {/* Strategy Selection */}
                <div>
                  <label className="text-[11px] font-semibold text-gray-500 uppercase tracking-wider mb-2 block">
                    Negotiation Strategy
                  </label>
                  <div className="grid grid-cols-3 gap-2">
                    {STRATEGIES.map((s) => (
                      <button
                        key={s.id}
                        onClick={() => { setStrategy(s.id); handleReset(); }}
                        className={`p-2.5 rounded-lg border text-left transition-all ${
                          strategy === s.id
                            ? `${s.activeColor} ring-2 ${s.color}`
                            : `border-gray-200 dark:border-navy-600 hover:border-gray-300 dark:hover:border-navy-500 ${s.color}`
                        }`}
                      >
                        <span className="text-base">{s.icon}</span>
                        <p className="text-[10px] font-semibold text-navy-900 dark:text-white mt-0.5">{s.label}</p>
                        <p className="text-[8px] text-gray-500 mt-0.5 leading-tight">{s.description}</p>
                      </button>
                    ))}
                  </div>
                </div>

                {/* Context Input */}
                <div>
                  <label className="text-[11px] font-semibold text-gray-500 uppercase tracking-wider mb-1.5 block">
                    Additional Context <span className="text-gray-400 font-normal normal-case">(optional)</span>
                  </label>
                  <textarea
                    value={context}
                    onChange={(e) => setContext(e.target.value)}
                    placeholder="e.g., This is a high-value enterprise customer with significant leverage..."
                    rows={2}
                    className="w-full px-3 py-2 text-[11px] border border-gray-200 dark:border-navy-600 rounded-lg bg-gray-50 dark:bg-navy-900 text-navy-900 dark:text-white placeholder-gray-400 focus:outline-none focus:ring-1 focus:ring-gold-400 resize-none"
                  />
                </div>

                {/* Original Clause Preview */}
                <div>
                  <label className="text-[11px] font-semibold text-gray-500 uppercase tracking-wider mb-1.5 block">
                    Original Clause
                  </label>
                  <div className="p-3 bg-gray-50 dark:bg-navy-900 border border-gray-200 dark:border-navy-600 rounded-lg">
                    <p className="text-[11px] text-gray-700 dark:text-gray-300 font-mono leading-relaxed whitespace-pre-wrap">
                      {clauseText}
                    </p>
                  </div>
                </div>

                {/* Generate Button */}
                {!result && (
                  <button
                    onClick={handleGenerate}
                    disabled={isGenerating}
                    className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-purple-600 hover:bg-purple-700 disabled:bg-purple-400 text-white rounded-lg text-[11px] font-semibold transition-colors"
                  >
                    {isGenerating ? (
                      <>
                        <Loader2 className="w-4 h-4 animate-spin" />
                        Rewriting with {STRATEGIES.find(s => s.id === strategy)?.label} strategy...
                      </>
                    ) : (
                      <>
                        <Sparkles className="w-4 h-4" />
                        Generate AI Rewrite
                      </>
                    )}
                  </button>
                )}

                {/* Error */}
                {error && (
                  <div className="flex items-center gap-2 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg text-[11px] text-red-700 dark:text-red-400">
                    <AlertTriangle className="w-4 h-4 flex-shrink-0" />
                    {error}
                  </div>
                )}

                {/* Result */}
                {result && (
                  <motion.div
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="space-y-3"
                  >
                    {/* Strategy badge */}
                    <div className="flex items-center gap-2">
                      <span className="text-[10px] font-medium text-gray-500">Strategy:</span>
                      <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full ${
                        result.strategy === "balanced" ? "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400" :
                        result.strategy === "supplier_friendly" ? "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400" :
                        "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400"
                      }`}>
                        {STRATEGIES.find(s => s.id === result.strategy)?.label || result.strategy}
                      </span>
                      <span className="text-[9px] text-gray-400 ml-auto">via {result.model_used}</span>
                    </div>

                    {/* Rewritten Text */}
                    <div className="p-3 bg-purple-50 dark:bg-purple-900/10 border border-purple-200 dark:border-purple-800 rounded-lg">
                      <div className="flex items-center justify-between mb-1.5">
                        <span className="text-[10px] font-semibold text-purple-700 dark:text-purple-400 uppercase tracking-wider">
                          Rewritten Clause
                        </span>
                        <button
                          onClick={handleCopy}
                          className="flex items-center gap-1 text-[9px] text-gray-400 hover:text-purple-600 transition-colors"
                        >
                          {copied ? (
                            <><Check className="w-3 h-3 text-green-500" /> Copied</>
                          ) : (
                            <><Copy className="w-3 h-3" /> Copy</>
                          )}
                        </button>
                      </div>
                      <p className="text-[11px] text-gray-800 dark:text-gray-200 font-mono leading-relaxed whitespace-pre-wrap">
                        {result.rewritten_text}
                      </p>
                    </div>

                    {/* Changes Summary */}
                    {result.changes.length > 0 && (
                      <div>
                        <label className="text-[10px] font-semibold text-gray-500 uppercase tracking-wider mb-1.5 block">
                          Changes Made ({result.changes.length})
                        </label>
                        <div className="space-y-1">
                          {result.changes.map((change, i) => (
                            <div key={i} className="flex items-start gap-2 p-2 bg-gray-50 dark:bg-navy-900 rounded-lg border border-gray-100 dark:border-navy-700">
                              <ArrowRight className="w-3 h-3 text-purple-500 mt-0.5 flex-shrink-0" />
                              <span className="text-[10px] text-gray-600 dark:text-gray-400">{change.description}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* AI Explanation Button */}
                    {!showExplanation && (
                      <button
                        onClick={handleExplain}
                        disabled={isLoadingExplanation}
                        className="w-full flex items-center justify-center gap-2 px-3 py-2 bg-indigo-50 dark:bg-indigo-900/20 border border-indigo-200 dark:border-indigo-800 text-indigo-700 dark:text-indigo-400 rounded-lg text-[10px] font-medium hover:bg-indigo-100 dark:hover:bg-indigo-900/30 transition-colors"
                      >
                        {isLoadingExplanation ? (
                          <><Loader2 className="w-3.5 h-3.5 animate-spin" /> Analyzing changes...</>
                        ) : (
                          <><Lightbulb className="w-3.5 h-3.5" /> Explain Why These Changes Were Made</>
                        )}
                      </button>
                    )}

                    {/* AI Explanation Panel */}
                    {showExplanation && explanation && (
                      <motion.div
                        initial={{ opacity: 0, y: 8 }}
                        animate={{ opacity: 1, y: 0 }}
                        className="p-3 bg-indigo-50 dark:bg-indigo-900/10 border border-indigo-200 dark:border-indigo-800 rounded-lg space-y-2"
                      >
                        <div className="flex items-center gap-1.5">
                          <Lightbulb className="w-3.5 h-3.5 text-indigo-600 dark:text-indigo-400" />
                          <span className="text-[10px] font-semibold text-indigo-700 dark:text-indigo-400 uppercase tracking-wider">
                            AI Explanation
                          </span>
                        </div>
                        <p className="text-[11px] text-gray-700 dark:text-gray-300 leading-relaxed">
                          {explanation.explanation}
                        </p>

                        {explanation.risks_addressed.length > 0 && (
                          <div>
                            <span className="text-[9px] font-semibold text-red-600 uppercase tracking-wider flex items-center gap-1 mb-1">
                              <Shield className="w-2.5 h-2.5" /> Risks Addressed
                            </span>
                            <div className="flex flex-wrap gap-1">
                              {explanation.risks_addressed.map((r, i) => (
                                <span key={i} className="text-[9px] px-1.5 py-0.5 bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-400 rounded-full border border-red-100 dark:border-red-800">
                                  {r}
                                </span>
                              ))}
                            </div>
                          </div>
                        )}

                        {explanation.benefits.length > 0 && (
                          <div>
                            <span className="text-[9px] font-semibold text-green-600 uppercase tracking-wider flex items-center gap-1 mb-1">
                              <TrendingUp className="w-2.5 h-2.5" /> Benefits
                            </span>
                            <div className="flex flex-wrap gap-1">
                              {explanation.benefits.map((b, i) => (
                                <span key={i} className="text-[9px] px-1.5 py-0.5 bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-400 rounded-full border border-green-100 dark:border-green-800">
                                  {b}
                                </span>
                              ))}
                            </div>
                          </div>
                        )}
                      </motion.div>
                    )}

                    {/* Action Buttons */}
                    <div className="flex items-center gap-2 pt-2">
                      <button
                        onClick={handleApply}
                        className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg text-[11px] font-semibold transition-colors"
                      >
                        <Check className="w-3.5 h-3.5" />
                        Apply Rewrite
                      </button>
                      <button
                        onClick={handleReset}
                        className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 border border-gray-200 dark:border-navy-600 hover:bg-gray-50 dark:hover:bg-navy-700 text-gray-700 dark:text-gray-300 rounded-lg text-[11px] font-semibold transition-colors"
                      >
                        <Sparkles className="w-3.5 h-3.5" />
                        Try Different Strategy
                      </button>
                    </div>
                  </motion.div>
                )}
              </div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}

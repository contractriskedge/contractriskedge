"use client";

import React, { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Brain, Lightbulb, AlertTriangle, TrendingUp, Shield, BookOpen,
  MessageSquare, Send, ChevronDown, ChevronRight, Sparkles,
  ExternalLink, Copy, Check, BarChart3, Target, FileText,
  X, Maximize2, Minimize2, Loader2,
} from "lucide-react";
import type { AiNegotiationInsight, NegotiationPlaybook, FallbackClause, NegotiationAnalytics } from "./types";
import { negotiationsService } from "@/services/api/negotiations";

// ── AI Insight Card ──────────────────────────────────────────────────────

function InsightCard({ insight, onApply }: { insight: AiNegotiationInsight; onApply?: (insight: AiNegotiationInsight) => void }) {
  const [expanded, setExpanded] = useState(false);

  const severityColors = {
    critical: "border-red-200 bg-red-50/50 dark:border-red-900/50 dark:bg-red-900/10",
    warning: "border-amber-200 bg-amber-50/50 dark:border-amber-900/50 dark:bg-amber-900/10",
    info: "border-blue-200 bg-blue-50/50 dark:border-blue-900/50 dark:bg-blue-900/10",
    success: "border-green-200 bg-green-50/50 dark:border-green-900/50 dark:bg-green-900/10",
  };
  const iconColors = {
    critical: "text-red-500", warning: "text-amber-500", info: "text-blue-500", success: "text-green-500",
  };
  const typeIcons = {
    risk: <AlertTriangle className="w-3.5 h-3.5" />,
    opportunity: <TrendingUp className="w-3.5 h-3.5" />,
    benchmark: <BarChart3 className="w-3.5 h-3.5" />,
    strategy: <Target className="w-3.5 h-3.5" />,
    compliance: <Shield className="w-3.5 h-3.5" />,
  };

  return (
    <motion.div
      layout
      className={`border rounded-lg overflow-hidden ${severityColors[insight.severity]}`}
    >
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full text-left px-2.5 py-2 flex items-start gap-2 hover:bg-black/5 dark:hover:bg-white/5 transition-colors"
      >
        <div className={`mt-0.5 ${iconColors[insight.severity]}`}>{typeIcons[insight.type]}</div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-1.5">
            <span className="text-[10px] font-semibold text-navy-900 dark:text-white">{insight.title}</span>
            <span className={`text-[8px] px-1 py-0.5 rounded-full font-medium ${
              insight.confidence > 90 ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400" :
              insight.confidence > 80 ? "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400" :
              "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400"
            }`}>
              {insight.confidence}% confident
            </span>
          </div>
          <p className="text-[10px] text-gray-600 dark:text-gray-300 mt-0.5 line-clamp-2">{insight.description}</p>
        </div>
        {expanded ? <ChevronDown className="w-3 h-3 text-gray-400 flex-shrink-0 mt-0.5" /> : <ChevronRight className="w-3 h-3 text-gray-400 flex-shrink-0 mt-0.5" />}
      </button>

      <AnimatePresence>
        {expanded && (
          <motion.div initial={{ height: 0 }} animate={{ height: "auto" }} exit={{ height: 0 }} className="overflow-hidden">
            <div className="px-2.5 pb-2.5 space-y-1.5">
              {/* Impact & Benchmark */}
              <div className="flex items-center gap-3 text-[9px] text-gray-500">
                <span>Impact: <span className={`font-medium ${
                  insight.impact === "high" ? "text-red-500" :
                  insight.impact === "medium" ? "text-amber-500" : "text-green-500"
                }`}>{insight.impact}</span></span>
                {insight.benchmarkPercentile !== undefined && (
                  <span>Benchmark: <span className="font-medium text-blue-600">{insight.benchmarkPercentile}th percentile</span></span>
                )}
              </div>

              {/* Suggested Response */}
              {insight.suggestedResponse && (
                <div className="bg-white/50 dark:bg-navy-900/50 rounded p-1.5">
                  <div className="flex items-center gap-1 text-[9px] text-gray-500 font-medium mb-0.5">
                    <Lightbulb className="w-2.5 h-2.5" />
                    Suggested Response
                  </div>
                  <p className="text-[10px] text-navy-900 dark:text-white">{insight.suggestedResponse}</p>
                </div>
              )}

              {/* Fallback Clause */}
              {insight.fallbackClause && (
                <div className="bg-white/50 dark:bg-navy-900/50 rounded p-1.5">
                  <div className="flex items-center gap-1 text-[9px] text-gray-500 font-medium mb-0.5">
                    <BookOpen className="w-2.5 h-2.5" />
                    Recommended Fallback
                  </div>
                  <p className="text-[10px] text-navy-900 dark:text-white font-mono">"{insight.fallbackClause}"</p>
                </div>
              )}

              {/* Actions */}
              <div className="flex items-center gap-1.5 pt-0.5">
                <button
                  onClick={() => onApply?.(insight)}
                  className="flex items-center gap-1 px-2 py-1 bg-purple-500 hover:bg-purple-600 text-white rounded text-[9px] font-medium transition-colors"
                >
                  <Sparkles className="w-2.5 h-2.5" /> Apply Suggestion
                </button>
                <button className="flex items-center gap-1 px-2 py-1 border border-gray-200 dark:border-navy-600 hover:bg-gray-50 dark:hover:bg-navy-700 rounded text-[9px] font-medium text-gray-600 dark:text-gray-300 transition-colors">
                  <Copy className="w-2.5 h-2.5" /> Copy
                </button>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}

// ── Fallback Clause Card ─────────────────────────────────────────────────

function FallbackClauseCard({ fallback, onApply }: { fallback: FallbackClause; onApply?: (fb: FallbackClause) => void }) {
  return (
    <div className="border border-gray-200 dark:border-navy-600 rounded-lg p-2 hover:shadow-sm transition-shadow">
      <div className="flex items-center justify-between mb-1">
        <span className="text-[10px] font-semibold text-navy-900 dark:text-white">{fallback.title}</span>
        <span className={`text-[8px] px-1.5 py-0.5 rounded-full font-medium ${
          fallback.strength === "strong" ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400" :
          fallback.strength === "moderate" ? "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400" :
          "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400"
        }`}>
          {fallback.strength}
        </span>
      </div>
      <p className="text-[9px] text-gray-500 dark:text-gray-400 line-clamp-2 mb-1.5 font-mono">"{fallback.content}"</p>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-[8px] text-gray-400">
          <span>{fallback.acceptanceRate}% acceptance</span>
          <span>{fallback.riskReduction}% risk reduction</span>
        </div>
        <button
          onClick={() => onApply?.(fallback)}
          className="text-[9px] text-purple-600 hover:text-purple-700 dark:text-purple-400 font-medium flex items-center gap-0.5"
        >
          <Sparkles className="w-2.5 h-2.5" /> Apply
        </button>
      </div>
    </div>
  );
}

// ── Chat Message ─────────────────────────────────────────────────────────

interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
  citations?: { text: string; source: string }[];
}

function ChatMessageBubble({ message }: { message: ChatMessage }) {
  return (
    <div className={`flex gap-2 ${message.role === "user" ? "flex-row-reverse" : ""}`}>
      <div className={`w-5 h-5 rounded-full flex items-center justify-center text-[8px] font-bold text-white flex-shrink-0 ${
        message.role === "assistant" ? "bg-purple-500" : "bg-navy-500"
      }`}>
        {message.role === "assistant" ? "AI" : "U"}
      </div>
      <div className={`max-w-[85%] ${message.role === "user" ? "bg-navy-500 text-white" : "bg-gray-100 dark:bg-navy-700 text-navy-900 dark:text-white"} rounded-lg px-2.5 py-1.5`}>
        <p className="text-[10px] leading-relaxed">{message.content}</p>
        {message.citations && message.citations.length > 0 && (
          <div className="mt-1 pt-1 border-t border-white/20 dark:border-navy-600 space-y-0.5">
            {message.citations.map((c, i) => (
              <div key={i} className="flex items-start gap-1 text-[8px] text-gray-400 dark:text-gray-500">
                <ExternalLink className="w-2 h-2 mt-0.5 flex-shrink-0" />
                <span>{c.text} - <span className="text-purple-500">{c.source}</span></span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// ── Right Panel ──────────────────────────────────────────────────────────

interface RightPanelProps {
  insights: AiNegotiationInsight[];
  playbooks: NegotiationPlaybook[];
  analytics: NegotiationAnalytics;
  onApplyInsight: (insight: AiNegotiationInsight) => void;
  onApplyFallback: (fb: FallbackClause) => void;
  sessionId?: string;
}

type RightTab = "copilot" | "insights" | "fallbacks" | "analytics";

export function RightPanel({
  insights, playbooks, analytics, onApplyInsight, onApplyFallback, sessionId,
}: RightPanelProps) {
  const [activeTab, setActiveTab] = useState<RightTab>("copilot");
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [chatInput, setChatInput] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const chatEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chatMessages]);

  const handleSendMessage = async () => {
    if (!chatInput.trim() || isStreaming) return;
    const userMsg: ChatMessage = {
      id: `user-${Date.now()}`,
      role: "user",
      content: chatInput.trim(),
      timestamp: new Date(),
    };
    setChatMessages(prev => [...prev, userMsg]);
    setChatInput("");
    setIsStreaming(true);

    try {
      // Use the first available clause ID from insights or a fallback
      const clauseId = insights[0]?.clauseId || "default";
      const response = await negotiationsService.aiCoach(
        sessionId || "",
        clauseId,
        {
          clause_text: chatInput.trim(),
          question: chatInput.trim(),
        },
      );

      const aiMsg: ChatMessage = {
        id: `ai-${Date.now()}`,
        role: "assistant",
        content: response.explanation || "I've analyzed the clause. See the risks and recommendations above.",
        timestamp: new Date(),
        citations: [
          ...(response.risks?.length
            ? [{ text: `Risks identified: ${response.risks.join(", ")}`, source: "AI Coach" }]
            : []),
          ...(response.policy_conflicts?.length
            ? [{ text: `Policy conflicts: ${response.policy_conflicts.join(", ")}`, source: "Policy Engine" }]
            : []),
        ],
      };
      setChatMessages(prev => [...prev, aiMsg]);
    } catch (error) {
      const errorMsg: ChatMessage = {
        id: `ai-${Date.now()}`,
        role: "assistant",
        content: "Sorry, I encountered an error analyzing that. Please try again or contact support.",
        timestamp: new Date(),
      };
      setChatMessages(prev => [...prev, errorMsg]);
    } finally {
      setIsStreaming(false);
    }
  };

  // Add welcome message on mount / session change using analytics data
  useEffect(() => {
    if (chatMessages.length === 0) {
      const topDisputes = analytics.clauseDisputeFrequency
        .slice(0, 3)
        .map(d => d.clause)
        .join(", ");

      const welcomeContent = analytics.totalSessions > 0
        ? `I've analyzed this contract against your playbooks. ` +
          `${analytics.totalSessions} similar sessions on record, ` +
          `${analytics.concessionRate}% avg concession rate.` +
          (topDisputes ? ` Key areas: ${topDisputes}.` : "") +
          ` How can I help?`
        : `Welcome! I'm your AI negotiation copilot. I can help analyze clauses, ` +
          `identify risks, and suggest fallback language. What would you like to explore?`;

      const welcomeMsg: ChatMessage = {
        id: "welcome",
        role: "assistant",
        content: welcomeContent,
        timestamp: new Date(),
      };
      setChatMessages([welcomeMsg]);
    }
  }, [analytics, chatMessages.length]);

  const tabs: { id: RightTab; label: string; icon: React.ReactNode }[] = [
    { id: "copilot", label: "AI Copilot", icon: <Brain className="w-3.5 h-3.5" /> },
    { id: "insights", label: "Insights", icon: <Lightbulb className="w-3.5 h-3.5" /> },
    { id: "fallbacks", label: "Fallbacks", icon: <BookOpen className="w-3.5 h-3.5" /> },
    { id: "analytics", label: "Analytics", icon: <BarChart3 className="w-3.5 h-3.5" /> },
  ];

  return (
    <div className="w-80 flex-shrink-0 bg-white dark:bg-navy-800 border-l border-gray-200 dark:border-navy-700 flex flex-col h-full">
      {/* Tabs */}
      <div className="flex border-b border-gray-200 dark:border-navy-700">
        {tabs.map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`flex-1 flex items-center justify-center gap-1 py-2 text-[10px] font-medium transition-colors relative ${
              activeTab === tab.id
                ? "text-gold-600 dark:text-gold-400"
                : "text-gray-500 dark:text-gray-400 hover:text-navy-700 dark:hover:text-gray-300"
            }`}
          >
            {tab.icon}
            <span>{tab.label}</span>
            {activeTab === tab.id && (
              <motion.div layoutId="right-tab-indicator" className="absolute bottom-0 left-0 right-0 h-0.5 bg-gold-500" />
            )}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto">
        {/* AI Copilot Chat */}
        {activeTab === "copilot" && (
          <div className="flex flex-col h-full">
            <div className="flex-1 overflow-y-auto p-2 space-y-2">
              {chatMessages.map(msg => (
                <ChatMessageBubble key={msg.id} message={msg} />
              ))}
              {isStreaming && (
                <div className="flex gap-2">
                  <div className="w-5 h-5 rounded-full bg-purple-500 flex items-center justify-center text-[8px] font-bold text-white flex-shrink-0">AI</div>
                  <div className="bg-gray-100 dark:bg-navy-700 rounded-lg px-2.5 py-1.5">
                    <div className="flex items-center gap-1">
                      <Loader2 className="w-3 h-3 text-purple-500 animate-spin" />
                      <span className="text-[10px] text-gray-500">Analyzing...</span>
                    </div>
                  </div>
                </div>
              )}
              <div ref={chatEndRef} />
            </div>
            <div className="p-2 border-t border-gray-200 dark:border-navy-700">
              <div className="flex gap-1">
                <input
                  type="text"
                  value={chatInput}
                  onChange={e => setChatInput(e.target.value)}
                  onKeyDown={e => e.key === "Enter" && handleSendMessage()}
                  placeholder="Ask about a clause..."
                  className="flex-1 px-2 py-1.5 text-[10px] border border-gray-200 dark:border-navy-600 rounded-md bg-gray-50 dark:bg-navy-900 text-navy-900 dark:text-white placeholder-gray-400 focus:outline-none focus:ring-1 focus:ring-gold-400"
                />
                <button
                  onClick={handleSendMessage}
                  disabled={isStreaming || !chatInput.trim()}
                  className="px-2 py-1.5 bg-gold-500 hover:bg-gold-600 disabled:bg-gray-300 text-white rounded-md transition-colors"
                >
                  <Send className="w-3 h-3" />
                </button>
              </div>
              <div className="flex gap-1 mt-1">
                {["Liability cap strategy", "Indemnification terms", "SLA negotiation"].map(suggestion => (
                  <button
                    key={suggestion}
                    onClick={() => { setChatInput(suggestion); }}
                    className="text-[8px] px-1.5 py-0.5 bg-gray-100 dark:bg-navy-700 text-gray-500 dark:text-gray-400 rounded-full hover:bg-gray-200 dark:hover:bg-navy-600 transition-colors"
                  >
                    {suggestion}
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Insights Tab */}
        {activeTab === "insights" && (
          <div className="p-2 space-y-1.5">
            <div className="flex items-center justify-between mb-1">
              <span className="text-[10px] font-semibold text-gray-500 uppercase tracking-wider">
                AI Negotiation Insights ({insights.length})
              </span>
              <span className="text-[8px] text-gray-400">Sorted by impact</span>
            </div>
            {insights.map(insight => (
              <InsightCard key={insight.id} insight={insight} onApply={onApplyInsight} />
            ))}
          </div>
        )}

        {/* Fallbacks Tab */}
        {activeTab === "fallbacks" && (
          <div className="p-2 space-y-2">
            {playbooks.map(pb => (
              <div key={pb.id}>
                <div className="flex items-center gap-1.5 mb-1">
                  <BookOpen className="w-3 h-3 text-gold-500" />
                  <span className="text-[10px] font-semibold text-navy-900 dark:text-white">{pb.title}</span>
                  {pb.aiRecommended && <Sparkles className="w-2.5 h-2.5 text-purple-500" />}
                </div>
                <div className="space-y-1.5">
                  {pb.fallbackClauses.map(fb => (
                    <FallbackClauseCard key={fb.id} fallback={fb} onApply={onApplyFallback} />
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Analytics Tab */}
        {activeTab === "analytics" && (
          <div className="p-2 space-y-3">
            {/* Summary Stats */}
            <div className="grid grid-cols-2 gap-1.5">
              {[
                { label: "Total Sessions", value: analytics.totalSessions, color: "text-blue-600" },
                { label: "Avg Cycle Time", value: `${analytics.avgCycleTime}d`, color: "text-green-600" },
                { label: "Concession Rate", value: `${analytics.concessionRate}%`, color: "text-amber-600" },
                { label: "Redline Acceptance", value: `${analytics.redlineAcceptanceRate}%`, color: "text-purple-600" },
              ].map(stat => (
                <div key={stat.label} className="bg-gray-50 dark:bg-navy-900 rounded-lg p-2 text-center">
                  <p className={`text-sm font-bold ${stat.color} tabular-nums`}>{stat.value}</p>
                  <p className="text-[8px] text-gray-500 mt-0.5">{stat.label}</p>
                </div>
              ))}
            </div>

            {/* Clause Dispute Frequency */}
            <div>
              <h4 className="text-[10px] font-semibold text-gray-500 uppercase tracking-wider mb-1">Clause Dispute Frequency</h4>
              <div className="space-y-1">
                {analytics.clauseDisputeFrequency.map(item => (
                  <div key={item.clause} className="flex items-center gap-2">
                    <span className="text-[9px] text-gray-600 dark:text-gray-300 w-28 truncate">{item.clause}</span>
                    <div className="flex-1 h-3 bg-gray-100 dark:bg-navy-700 rounded-full overflow-hidden">
                      <motion.div
                        initial={{ width: 0 }}
                        animate={{ width: `${(item.count / Math.max(...analytics.clauseDisputeFrequency.map(c => c.count))) * 100}%` }}
                        className="h-full bg-gold-500 rounded-full"
                      />
                    </div>
                    <span className="text-[9px] text-gray-500 tabular-nums w-4 text-right">{item.count}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Cycle Bottlenecks */}
            <div>
              <h4 className="text-[10px] font-semibold text-gray-500 uppercase tracking-wider mb-1">Cycle Bottlenecks</h4>
              <div className="space-y-1">
                {analytics.cycleBottlenecks.map(item => (
                  <div key={item.stage} className="flex items-center gap-2">
                    <span className="text-[9px] text-gray-600 dark:text-gray-300 w-24 truncate">{item.stage}</span>
                    <div className="flex-1 h-3 bg-gray-100 dark:bg-navy-700 rounded-full overflow-hidden">
                      <motion.div
                        initial={{ width: 0 }}
                        animate={{ width: `${(item.avgDays / 5) * 100}%` }}
                        className={`h-full rounded-full ${item.avgDays > 3 ? "bg-red-500" : item.avgDays > 2 ? "bg-amber-500" : "bg-green-500"}`}
                      />
                    </div>
                    <span className="text-[9px] text-gray-500 tabular-nums w-6 text-right">{item.avgDays}d</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Vendor Aggressiveness */}
            <div>
              <h4 className="text-[10px] font-semibold text-gray-500 uppercase tracking-wider mb-1">Vendor Aggressiveness</h4>
              <div className="space-y-1">
                {analytics.vendorAggressiveness.map(item => (
                  <div key={item.vendor} className="flex items-center gap-2">
                    <span className="text-[9px] text-gray-600 dark:text-gray-300 w-24 truncate">{item.vendor}</span>
                    <div className="flex-1 h-3 bg-gray-100 dark:bg-navy-700 rounded-full overflow-hidden">
                      <motion.div
                        initial={{ width: 0 }}
                        animate={{ width: `${item.score}%` }}
                        className={`h-full rounded-full ${item.score > 80 ? "bg-red-500" : item.score > 60 ? "bg-amber-500" : "bg-green-500"}`}
                      />
                    </div>
                    <span className="text-[9px] text-gray-500 tabular-nums w-6 text-right">{item.score}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

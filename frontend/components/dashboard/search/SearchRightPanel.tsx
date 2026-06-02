"use client";

import React, { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Brain, Sparkles, Lightbulb, AlertTriangle, TrendingUp, Shield,
  Search, ArrowRight, Loader2, Send, MessageSquare, X,
  ChevronDown, ChevronRight, ExternalLink, Copy, BarChart3,
  Share2,
} from "lucide-react";
import type { AiDiscoveryInsight, AiSearchSuggestion, SearchAnalytics } from "./types";

const mockDiscoveryInsights: AiDiscoveryInsight[] = [];
const mockAiSuggestions: AiSearchSuggestion[] = [];
const mockSearchAnalytics: SearchAnalytics = { totalSearches: 0, avgResponseTime: 0, topQueries: [], zeroResultRate: 0 };

// ── Discovery Insight Card ───────────────────────────────────────────────

function DiscoveryInsightCard({ insight, onApply }: { insight: AiDiscoveryInsight; onApply?: (insight: AiDiscoveryInsight) => void }) {
  const [expanded, setExpanded] = useState(false);

  const typeIcons: Record<string, React.ReactNode> = {
    relationship: <Share2 className="w-3 h-3" />,
    anomaly: <AlertTriangle className="w-3 h-3" />,
    pattern: <BarChart3 className="w-3 h-3" />,
    recommendation: <Lightbulb className="w-3 h-3" />,
    risk: <AlertTriangle className="w-3 h-3" />,
    compliance: <Shield className="w-3 h-3" />,
  };

  const severityBorders: Record<string, string> = {
    critical: "border-red-200 bg-red-50/50 dark:border-red-900/50 dark:bg-red-900/10",
    warning: "border-amber-200 bg-amber-50/50 dark:border-amber-900/50 dark:bg-amber-900/10",
    info: "border-blue-200 bg-blue-50/50 dark:border-blue-900/50 dark:bg-blue-900/10",
    success: "border-green-200 bg-green-50/50 dark:border-green-900/50 dark:bg-green-900/10",
  };

  return (
    <motion.div
      layout
      className={`border rounded-lg overflow-hidden ${severityBorders[insight.severity]}`}
    >
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full text-left px-2.5 py-2 flex items-start gap-2 hover:bg-black/5 dark:hover:bg-white/5 transition-colors"
      >
        <div className={`mt-0.5 ${
          insight.severity === "critical" ? "text-red-500" :
          insight.severity === "warning" ? "text-amber-500" :
          insight.severity === "success" ? "text-green-500" : "text-blue-500"
        }`}>
          {typeIcons[insight.type] || <Lightbulb className="w-3 h-3" />}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-1.5">
            <span className="text-[10px] font-semibold text-navy-900 dark:text-white">{insight.title}</span>
            <span className={`text-[8px] px-1 py-0.5 rounded-full font-medium ${
              insight.confidence > 90 ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400" :
              insight.confidence > 80 ? "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400" :
              "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400"
            }`}>
              {insight.confidence}%
            </span>
          </div>
          <p className="text-[9px] text-gray-600 dark:text-gray-300 mt-0.5 line-clamp-2">{insight.description}</p>
        </div>
        {expanded ? <ChevronDown className="w-2.5 h-2.5 text-gray-400 flex-shrink-0" /> : <ChevronRight className="w-2.5 h-2.5 text-gray-400 flex-shrink-0" />}
      </button>

      <AnimatePresence>
        {expanded && (
          <motion.div initial={{ height: 0 }} animate={{ height: "auto" }} exit={{ height: 0 }} className="overflow-hidden">
            <div className="px-2.5 pb-2.5 space-y-1.5">
              <div className="flex items-center gap-2 text-[8px] text-gray-500">
                <span>Impact: <span className={`font-medium ${
                  insight.impact === "high" ? "text-red-500" :
                  insight.impact === "medium" ? "text-amber-500" : "text-green-500"
                }`}>{insight.impact}</span></span>
                <span>Entities: {insight.entities.join(", ")}</span>
              </div>
              {insight.suggestedQuery && (
                <button
                  onClick={() => onApply?.(insight)}
                  className="flex items-center gap-1 px-2 py-1 bg-purple-500 hover:bg-purple-600 text-white rounded text-[9px] font-medium transition-colors"
                >
                  <Search className="w-2.5 h-2.5" /> Search: "{insight.suggestedQuery}"
                </button>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}

// ── Suggestion Chip ──────────────────────────────────────────────────────

function SuggestionChip({ suggestion, onClick }: { suggestion: AiSearchSuggestion; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className="w-full text-left px-2 py-1.5 bg-purple-50 dark:bg-purple-900/10 border border-purple-100 dark:border-purple-900/30 rounded-lg hover:bg-purple-100 dark:hover:bg-purple-900/20 transition-colors group"
    >
      <div className="flex items-start gap-1.5">
        <Sparkles className="w-2.5 h-2.5 text-purple-500 mt-0.5 flex-shrink-0" />
        <div className="flex-1 min-w-0">
          <span className="text-[9px] font-medium text-navy-900 dark:text-white truncate block">{suggestion.query}</span>
          <span className="text-[8px] text-gray-500">{suggestion.description}</span>
        </div>
        <ArrowRight className="w-2.5 h-2.5 text-purple-400 opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0 mt-0.5" />
      </div>
    </button>
  );
}

// ── Chat Message ─────────────────────────────────────────────────────────

interface ChatMsg {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
}

function ChatBubble({ msg }: { msg: ChatMsg }) {
  return (
    <div className={`flex gap-2 ${msg.role === "user" ? "flex-row-reverse" : ""}`}>
      <div className={`w-5 h-5 rounded-full flex items-center justify-center text-[7px] font-bold text-white flex-shrink-0 ${
        msg.role === "assistant" ? "bg-purple-500" : "bg-navy-500"
      }`}>
        {msg.role === "assistant" ? "AI" : "U"}
      </div>
      <div className={`max-w-[88%] ${
        msg.role === "user"
          ? "bg-navy-500 text-white"
          : "bg-gray-100 dark:bg-navy-700 text-navy-900 dark:text-white"
      } rounded-lg px-2.5 py-1.5`}>
        <p className="text-[10px] leading-relaxed">{msg.content}</p>
      </div>
    </div>
  );
}

// ── Right Panel ──────────────────────────────────────────────────────────

interface SearchRightPanelProps {
  insights: AiDiscoveryInsight[];
  suggestions: AiSearchSuggestion[];
  analytics: SearchAnalytics;
  onInsightClick: (insight: AiDiscoveryInsight) => void;
  onSuggestionClick: (suggestion: AiSearchSuggestion) => void;
}

type RightTab = "assistant" | "insights" | "suggestions" | "analytics";

export function SearchRightPanel({
  insights, suggestions, analytics, onInsightClick, onSuggestionClick,
}: SearchRightPanelProps) {
  const [activeTab, setActiveTab] = useState<RightTab>("assistant");
  const [chatMessages, setChatMessages] = useState<ChatMsg[]>([
    { id: "welcome", role: "assistant", content: "I'm your AI Discovery Assistant. I can help refine searches, discover patterns, find anomalies, and recommend next steps across your contract portfolio.", timestamp: new Date() },
  ]);
  const [chatInput, setChatInput] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const chatEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chatMessages]);

  const handleSend = () => {
    if (!chatInput.trim() || isStreaming) return;
    const userMsg: ChatMsg = { id: `u-${Date.now()}`, role: "user", content: chatInput.trim(), timestamp: new Date() };
    setChatMessages(prev => [...prev, userMsg]);
    setChatInput("");
    setIsStreaming(true);
    setTimeout(() => {
      const responses: Record<string, string> = {
        liability: "I found 18 contracts with uncapped liability language. The most common pattern is in IP infringement and confidentiality breach carve-outs. Would you like me to show you the specific clauses?",
        gdpr: "12 contracts are missing GDPR data processing addendums. This is a critical compliance gap. I recommend prioritizing TechSphere Inc and DataVault Systems agreements.",
        renewal: "7 contracts have auto-renewal clauses with less than 30-day notice periods. CloudNexus and SecurePath Ltd have the highest risk exposure.",
        default: "Based on my analysis of your contract portfolio, I've identified several patterns worth exploring. Try searching for 'uncapped liability', 'GDPR compliance gaps', or 'auto-renewal risk' for specific insights.",
      };
      const matchedKey = Object.keys(responses).find(k => chatInput.toLowerCase().includes(k));
      const aiMsg: ChatMsg = { id: `a-${Date.now()}`, role: "assistant", content: responses[matchedKey || "default"], timestamp: new Date() };
      setChatMessages(prev => [...prev, aiMsg]);
      setIsStreaming(false);
    }, 1200);
  };

  const tabs: { id: RightTab; label: string; icon: React.ReactNode }[] = [
    { id: "assistant", label: "Assistant", icon: <Brain className="w-3 h-3" /> },
    { id: "insights", label: "Discoveries", icon: <Lightbulb className="w-3 h-3" /> },
    { id: "suggestions", label: "Explore", icon: <Sparkles className="w-3 h-3" /> },
    { id: "analytics", label: "Analytics", icon: <BarChart3 className="w-3 h-3" /> },
  ];

  return (
    <div className="w-80 flex-shrink-0 bg-white dark:bg-navy-800 border-l border-gray-200 dark:border-navy-700 flex flex-col h-full">
      {/* Tabs */}
      <div className="flex border-b border-gray-200 dark:border-navy-700">
        {tabs.map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`flex-1 flex items-center justify-center gap-1 py-2 text-[9px] font-medium transition-colors relative ${
              activeTab === tab.id
                ? "text-gold-600 dark:text-gold-400"
                : "text-gray-500 dark:text-gray-400 hover:text-navy-700 dark:hover:text-gray-300"
            }`}
          >
            {tab.icon}
            <span>{tab.label}</span>
            {activeTab === tab.id && (
              <motion.div layoutId="search-right-tab" className="absolute bottom-0 left-0 right-0 h-0.5 bg-gold-500" />
            )}
          </button>
        ))}
      </div>

      <div className="flex-1 overflow-y-auto">
        {/* AI Assistant Chat */}
        {activeTab === "assistant" && (
          <div className="flex flex-col h-full">
            <div className="flex-1 overflow-y-auto p-2 space-y-2">
              {chatMessages.map(msg => <ChatBubble key={msg.id} msg={msg} />)}
              {isStreaming && (
                <div className="flex gap-2">
                  <div className="w-5 h-5 rounded-full bg-purple-500 flex items-center justify-center text-[7px] font-bold text-white">AI</div>
                  <div className="bg-gray-100 dark:bg-navy-700 rounded-lg px-2.5 py-1.5">
                    <Loader2 className="w-3 h-3 text-purple-500 animate-spin" />
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
                  onKeyDown={e => e.key === "Enter" && handleSend()}
                  placeholder="Ask about your contracts..."
                  className="flex-1 px-2 py-1.5 text-[10px] border border-gray-200 dark:border-navy-600 rounded-md bg-gray-50 dark:bg-navy-900 text-navy-900 dark:text-white placeholder-gray-400 focus:outline-none focus:ring-1 focus:ring-gold-400"
                />
                <button onClick={handleSend} disabled={isStreaming || !chatInput.trim()} className="px-2 py-1.5 bg-gold-500 hover:bg-gold-600 disabled:bg-gray-300 text-white rounded-md transition-colors">
                  <Send className="w-3 h-3" />
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Discoveries Tab */}
        {activeTab === "insights" && (
          <div className="p-2 space-y-1.5">
            <div className="flex items-center justify-between px-1 mb-1">
              <span className="text-[9px] font-semibold text-gray-500 uppercase tracking-wider">AI Discoveries ({insights.length})</span>
              <span className="text-[8px] text-gray-400">AI-powered</span>
            </div>
            {insights.map(insight => (
              <DiscoveryInsightCard key={insight.id} insight={insight} onApply={onInsightClick} />
            ))}
          </div>
        )}

        {/* Suggestions Tab */}
        {activeTab === "suggestions" && (
          <div className="p-2 space-y-1.5">
            <div className="flex items-center gap-1 px-1 mb-1">
              <Sparkles className="w-3 h-3 text-purple-500" />
              <span className="text-[9px] font-semibold text-gray-500 uppercase tracking-wider">Suggested Searches</span>
            </div>
            {suggestions.map(s => (
              <SuggestionChip key={s.id} suggestion={s} onClick={() => onSuggestionClick(s)} />
            ))}
          </div>
        )}

        {/* Analytics Tab */}
        {activeTab === "analytics" && (
          <div className="p-2 space-y-3">
            {/* Summary Stats */}
            <div className="grid grid-cols-2 gap-1.5">
              {[
                { label: "Total Searches", value: analytics.totalSearches.toLocaleString(), color: "text-blue-600" },
                { label: "Avg Latency", value: `${analytics.avgLatency}ms`, color: "text-green-600" },
                { label: "Semantic Accuracy", value: `${analytics.semanticAccuracy}%`, color: "text-purple-600" },
                { label: "Click-Through Rate", value: `${analytics.clickThroughRate}%`, color: "text-gold-600" },
              ].map(stat => (
                <div key={stat.label} className="bg-gray-50 dark:bg-navy-900 rounded-lg p-2 text-center">
                  <p className={`text-sm font-bold ${stat.color} tabular-nums`}>{stat.value}</p>
                  <p className="text-[8px] text-gray-500 mt-0.5">{stat.label}</p>
                </div>
              ))}
            </div>

            {/* Popular Searches */}
            <div>
              <h4 className="text-[9px] font-semibold text-gray-500 uppercase tracking-wider mb-1">Popular Searches</h4>
              <div className="space-y-1">
                {analytics.popularSearches.slice(0, 5).map(item => (
                  <div key={item.query} className="flex items-center gap-2">
                    <span className="text-[8px] text-gray-600 dark:text-gray-300 w-28 truncate">{item.query}</span>
                    <div className="flex-1 h-2.5 bg-gray-100 dark:bg-navy-700 rounded-full overflow-hidden">
                      <motion.div
                        initial={{ width: 0 }}
                        animate={{ width: `${(item.count / Math.max(...analytics.popularSearches.map(s => s.count))) * 100}%` }}
                        className="h-full bg-gold-500 rounded-full"
                      />
                    </div>
                    <span className="text-[8px] text-gray-500 tabular-nums w-8 text-right">{item.count}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Latency Distribution */}
            <div>
              <h4 className="text-[9px] font-semibold text-gray-500 uppercase tracking-wider mb-1">Latency Distribution</h4>
              <div className="space-y-1">
                {analytics.latencyDistribution.map(item => (
                  <div key={item.range} className="flex items-center gap-2">
                    <span className="text-[8px] text-gray-600 dark:text-gray-300 w-16 truncate">{item.range}</span>
                    <div className="flex-1 h-2.5 bg-gray-100 dark:bg-navy-700 rounded-full overflow-hidden">
                      <motion.div
                        initial={{ width: 0 }}
                        animate={{ width: `${(item.count / Math.max(...analytics.latencyDistribution.map(s => s.count))) * 100}%` }}
                        className={`h-full rounded-full ${item.range.includes(">") ? "bg-red-500" : item.range.includes("200") ? "bg-amber-500" : "bg-green-500"}`}
                      />
                    </div>
                    <span className="text-[8px] text-gray-500 tabular-nums w-8 text-right">{item.count}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* AI Retrieval Quality */}
            <div>
              <h4 className="text-[9px] font-semibold text-gray-500 uppercase tracking-wider mb-1">AI Retrieval Quality</h4>
              <div className="space-y-1">
                {analytics.aiRetrievalQuality.map(item => (
                  <div key={item.date} className="flex items-center gap-2">
                    <span className="text-[8px] text-gray-600 dark:text-gray-300 w-12">{item.date}</span>
                    <div className="flex-1 space-y-0.5">
                      <div className="flex items-center gap-1">
                        <span className="text-[7px] text-blue-500 w-5">P</span>
                        <div className="flex-1 h-1.5 bg-gray-100 dark:bg-navy-700 rounded-full overflow-hidden">
                          <motion.div initial={{ width: 0 }} animate={{ width: `${item.precision}%` }} className="h-full bg-blue-500 rounded-full" />
                        </div>
                        <span className="text-[7px] text-gray-500 tabular-nums w-7 text-right">{item.precision}%</span>
                      </div>
                      <div className="flex items-center gap-1">
                        <span className="text-[7px] text-green-500 w-5">R</span>
                        <div className="flex-1 h-1.5 bg-gray-100 dark:bg-navy-700 rounded-full overflow-hidden">
                          <motion.div initial={{ width: 0 }} animate={{ width: `${item.recall}%` }} className="h-full bg-green-500 rounded-full" />
                        </div>
                        <span className="text-[7px] text-gray-500 tabular-nums w-7 text-right">{item.recall}%</span>
                      </div>
                    </div>
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

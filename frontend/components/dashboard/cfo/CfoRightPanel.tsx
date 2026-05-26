"use client";

import React, { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Brain, Lightbulb, AlertTriangle, DollarSign, TrendingUp,
  ChevronDown, ChevronRight, Sparkles, Send, Loader2, BarChart3,
  Building2, Target, TrendingDown,
} from "lucide-react";
import type { AiFinancialInsight, FinancialAnalytics } from "./types";

// ── AI Insight Card ──────────────────────────────────────────────────────

function AiInsightCard({ insight, onApply }: { insight: AiFinancialInsight; onApply?: (insight: AiFinancialInsight) => void }) {
  const [expanded, setExpanded] = useState(false);
  const colors: Record<string, string> = {
    critical: "border-red-200 bg-red-50/50 dark:border-red-900/50 dark:bg-red-900/10",
    warning: "border-amber-200 bg-amber-50/50 dark:border-amber-900/50 dark:bg-amber-900/10",
    info: "border-blue-200 bg-blue-50/50 dark:border-blue-900/50 dark:bg-blue-900/10",
    success: "border-green-200 bg-green-50/50 dark:border-green-900/50 dark:bg-green-900/10",
  };
  const typeIcons: Record<string, React.ReactNode> = {
    exposure: <AlertTriangle className="w-3 h-3" />, forecast: <TrendingUp className="w-3 h-3" />,
    anomaly: <TrendingDown className="w-3 h-3" />, savings: <Target className="w-3 h-3" />,
    risk: <AlertTriangle className="w-3 h-3" />, recommendation: <Lightbulb className="w-3 h-3" />,
  };
  return (
    <div className={`border rounded-lg overflow-hidden ${colors[insight.severity]}`}>
      <button onClick={() => setExpanded(!expanded)} className="w-full text-left px-2.5 py-2 flex items-start gap-2 hover:bg-black/5 dark:hover:bg-white/5 transition-colors">
        <div className={`mt-0.5 ${insight.severity === "critical" ? "text-red-500" : insight.severity === "warning" ? "text-amber-500" : insight.severity === "success" ? "text-green-500" : "text-blue-500"}`}>
          {typeIcons[insight.type] || <Brain className="w-3 h-3" />}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-1.5">
            <span className="text-[9px] font-semibold text-navy-900 dark:text-white">{insight.title}</span>
            <span className={`text-[7px] px-1 py-0.5 rounded-full font-medium ${
              insight.confidence > 90 ? "bg-green-100 text-green-700" : insight.confidence > 80 ? "bg-blue-100 text-blue-700" : "bg-amber-100 text-amber-700"
            }`}>{insight.confidence}%</span>
          </div>
          <p className="text-[8px] text-gray-600 dark:text-gray-300 mt-0.5 line-clamp-2">{insight.description}</p>
          <div className="flex items-center gap-1 mt-1 text-[7px] text-gray-500">
            <DollarSign className="w-2 h-2" />
            <span className="font-medium text-red-500">${(insight.financialImpact / 1000000).toFixed(1)}M</span>
            <span>·</span>
            <span>{insight.impactedContracts} contracts</span>
          </div>
        </div>
        {expanded ? <ChevronDown className="w-2 h-2 text-gray-400" /> : <ChevronRight className="w-2 h-2 text-gray-400" />}
      </button>
      <AnimatePresence>
        {expanded && (
          <motion.div initial={{ height: 0 }} animate={{ height: "auto" }} exit={{ height: 0 }} className="overflow-hidden">
            <div className="px-2.5 pb-2.5 space-y-1">
              <div className="bg-white/50 dark:bg-navy-900/50 rounded p-1.5">
                <p className="text-[8px] text-gray-700 dark:text-gray-300 leading-relaxed">{insight.recommendedAction}</p>
              </div>
              <button onClick={() => onApply?.(insight)} className="flex items-center gap-1 px-2 py-0.5 bg-purple-500 hover:bg-purple-600 text-white rounded text-[8px] font-medium transition-colors">
                <Sparkles className="w-2 h-2" /> Apply Recommendation
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

// ── Chat ─────────────────────────────────────────────────────────────────

interface ChatMsg { id: string; role: "user" | "assistant"; content: string; timestamp: Date; }

function ChatBubble({ msg }: { msg: ChatMsg }) {
  return (
    <div className={`flex gap-2 ${msg.role === "user" ? "flex-row-reverse" : ""}`}>
      <div className={`w-5 h-5 rounded-full flex items-center justify-center text-[7px] font-bold text-white flex-shrink-0 ${msg.role === "assistant" ? "bg-purple-500" : "bg-navy-500"}`}>{msg.role === "assistant" ? "AI" : "U"}</div>
      <div className={`max-w-[88%] ${msg.role === "user" ? "bg-navy-500 text-white" : "bg-gray-100 dark:bg-navy-700 text-navy-900 dark:text-white"} rounded-lg px-2.5 py-1.5`}>
        <p className="text-[9px] leading-relaxed">{msg.content}</p>
      </div>
    </div>
  );
}

// ── Right Panel ──────────────────────────────────────────────────────────

interface CfoRightPanelProps {
  insights: AiFinancialInsight[];
  analytics: FinancialAnalytics;
  onInsightApply: (insight: AiFinancialInsight) => void;
}

type RightTab = "assistant" | "insights" | "metrics";

export function CfoRightPanel({ insights, analytics, onInsightApply }: CfoRightPanelProps) {
  const [activeTab, setActiveTab] = useState<RightTab>("insights");
  const [chatMessages, setChatMessages] = useState<ChatMsg[]>([
    { id: "welcome", role: "assistant", content: "I'm your AI Financial Intelligence Copilot. I can analyze contract exposure, forecast renewals, identify savings opportunities, and provide executive recommendations.", timestamp: new Date() },
  ]);
  const [chatInput, setChatInput] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const chatEndRef = useRef<HTMLDivElement>(null);
  useEffect(() => { chatEndRef.current?.scrollIntoView({ behavior: "smooth" }); }, [chatMessages]);

  const handleSend = () => {
    if (!chatInput.trim() || isStreaming) return;
    const userMsg: ChatMsg = { id: `u-${Date.now()}`, role: "user", content: chatInput.trim(), timestamp: new Date() };
    setChatMessages(prev => [...prev, userMsg]); setChatInput(""); setIsStreaming(true);
    setTimeout(() => {
      const responses: Record<string, string> = {
        exposure: "Total financial exposure is $124.8M, with uncapped liability at $42.3M (up 22%). The top 3 risk contracts are TechSphere ($6.2M), CloudNexus ($4.8M), and Acme Corp IP indemnification.",
        renewal: "Q3 renewal exposure is $156.2M across 24 contracts. CloudNexus ($12M) and TechSphere ($18.5M) have the highest risk. I recommend initiating negotiations immediately.",
        savings: "I've identified $18.5M in procurement savings opportunities. Top priority: CloudNexus renegotiation ($2.5M) and Microsoft license optimization ($1.7M).",
        default: "Based on current analytics, your portfolio is $847.2M with $124.8M at risk. Key concerns: uncapped liability (+22% QoQ) and vendor concentration at 68.4%. I recommend focusing on the 3 highest-exposure contracts first.",
      };
      const matchedKey = Object.keys(responses).find(k => chatInput.toLowerCase().includes(k));
      const aiMsg: ChatMsg = { id: `a-${Date.now()}`, role: "assistant", content: responses[matchedKey || "default"], timestamp: new Date() };
      setChatMessages(prev => [...prev, aiMsg]); setIsStreaming(false);
    }, 1200);
  };

  const tabs: { id: RightTab; label: string; icon: React.ReactNode }[] = [
    { id: "assistant", label: "Copilot", icon: <Brain className="w-3 h-3" /> },
    { id: "insights", label: "AI Insights", icon: <Lightbulb className="w-3 h-3" /> },
    { id: "metrics", label: "Metrics", icon: <BarChart3 className="w-3 h-3" /> },
  ];

  return (
    <div className="w-72 flex-shrink-0 bg-white dark:bg-navy-800 border-l border-gray-200 dark:border-navy-700 flex flex-col h-full">
      <div className="flex border-b border-gray-200 dark:border-navy-700">
        {tabs.map(tab => (
          <button key={tab.id} onClick={() => setActiveTab(tab.id)}
            className={`flex-1 flex items-center justify-center gap-1 py-2 text-[8px] font-medium transition-colors relative ${
              activeTab === tab.id ? "text-gold-600 dark:text-gold-400" : "text-gray-500 dark:text-gray-400 hover:text-navy-700"
            }`}>
            {tab.icon}<span>{tab.label}</span>
            {activeTab === tab.id && <motion.div layoutId="cfo-right-tab" className="absolute bottom-0 left-0 right-0 h-0.5 bg-gold-500" />}
          </button>
        ))}
      </div>

      <div className="flex-1 overflow-y-auto">
        {activeTab === "assistant" && (
          <div className="flex flex-col h-full">
            <div className="flex-1 overflow-y-auto p-2 space-y-2">
              {chatMessages.map(msg => <ChatBubble key={msg.id} msg={msg} />)}
              {isStreaming && <div className="flex gap-2"><div className="w-5 h-5 rounded-full bg-purple-500 flex items-center justify-center text-[7px] font-bold text-white">AI</div><div className="bg-gray-100 dark:bg-navy-700 rounded-lg px-2.5 py-1.5"><Loader2 className="w-3 h-3 text-purple-500 animate-spin" /></div></div>}
              <div ref={chatEndRef} />
            </div>
            <div className="p-2 border-t border-gray-200 dark:border-navy-700">
              <div className="flex gap-1">
                <input type="text" value={chatInput} onChange={e => setChatInput(e.target.value)} onKeyDown={e => e.key === "Enter" && handleSend()}
                  placeholder="Ask about financial risk..."
                  className="flex-1 px-2 py-1.5 text-[9px] border border-gray-200 dark:border-navy-600 rounded-md bg-gray-50 dark:bg-navy-900 text-navy-900 dark:text-white placeholder-gray-400 focus:outline-none focus:ring-1 focus:ring-gold-400" />
                <button onClick={handleSend} disabled={isStreaming || !chatInput.trim()} className="px-2 py-1.5 bg-gold-500 hover:bg-gold-600 disabled:bg-gray-300 text-white rounded-md transition-colors"><Send className="w-3 h-3" /></button>
              </div>
            </div>
          </div>
        )}

        {activeTab === "insights" && (
          <div className="p-2 space-y-1.5">
            <div className="flex items-center justify-between px-1 mb-1">
              <span className="text-[8px] font-semibold text-gray-400 uppercase tracking-wider">AI Financial ({insights.length})</span>
              <Sparkles className="w-2.5 h-2.5 text-purple-400" />
            </div>
            {insights.map(i => <AiInsightCard key={i.id} insight={i} onApply={onInsightApply} />)}
          </div>
        )}

        {activeTab === "metrics" && (
          <div className="p-2 space-y-3">
            <div className="grid grid-cols-2 gap-1.5">
              {[
                { label: "Portfolio", value: `$${(analytics.totalPortfolioValue / 1000000).toFixed(1)}M`, color: "text-blue-600" },
                { label: "At Risk", value: `$${(analytics.totalExposure / 1000000).toFixed(1)}M`, color: "text-red-600" },
                { label: "Uncapped", value: `$${(analytics.uncappedLiability / 1000000).toFixed(1)}M`, color: "text-red-600" },
                { label: "Savings", value: `$${(analytics.savingsOpportunities / 1000000).toFixed(1)}M`, color: "text-green-600" },
              ].map(s => (
                <div key={s.label} className="bg-gray-50 dark:bg-navy-900 rounded-lg p-2 text-center">
                  <p className={`text-sm font-bold ${s.color} tabular-nums`}>{s.value}</p>
                  <p className="text-[7px] text-gray-500 mt-0.5">{s.label}</p>
                </div>
              ))}
            </div>
            {/* Exposure Trend */}
            <div>
              <h4 className="text-[8px] font-semibold text-gray-400 uppercase tracking-wider mb-1">Exposure Trend ($M)</h4>
              <div className="space-y-0.5">
                {analytics.exposureTrend.map(t => (
                  <div key={t.date} className="flex items-center gap-2">
                    <span className="text-[7px] text-gray-500 w-6">{t.date}</span>
                    <div className="flex-1 h-2 bg-gray-100 dark:bg-navy-700 rounded-full overflow-hidden">
                      <motion.div initial={{ width: 0 }} animate={{ width: `${(t.amount / Math.max(...analytics.exposureTrend.map(x => x.amount))) * 100}%` }} className="h-full bg-red-500 rounded-full" />
                    </div>
                    <span className="text-[7px] text-gray-500 tabular-nums w-10 text-right">${t.amount.toFixed(1)}M</span>
                  </div>
                ))}
              </div>
            </div>
            {/* Business Unit */}
            <div>
              <h4 className="text-[8px] font-semibold text-gray-400 uppercase tracking-wider mb-1">BU Exposure</h4>
              <div className="space-y-0.5">
                {analytics.businessUnitExposure.slice(0, 3).map(bu => (
                  <div key={bu.unit} className="flex items-center gap-2">
                    <span className="text-[7px] text-gray-600 dark:text-gray-300 w-20 truncate">{bu.unit}</span>
                    <div className="flex-1 h-2 bg-gray-100 dark:bg-navy-700 rounded-full overflow-hidden">
                      <motion.div initial={{ width: 0 }} animate={{ width: `${(bu.exposure / Math.max(...analytics.businessUnitExposure.map(x => x.exposure))) * 100}%` }} className="h-full bg-amber-500 rounded-full" />
                    </div>
                    <span className="text-[7px] text-gray-500 tabular-nums w-10 text-right">${bu.exposure.toFixed(1)}M</span>
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

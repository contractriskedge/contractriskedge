"use client";

import React, { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Brain, Lightbulb, AlertTriangle, Shield, Gavel, FileText,
  ChevronDown, ChevronRight, Sparkles, Send, Loader2, BarChart3,
  Building2, CheckCircle, ExternalLink,
} from "lucide-react";
import type { AiComplianceInsight, ComplianceAnalytics } from "./types";

// ── AI Insight Card ──────────────────────────────────────────────────────

function AiInsightCard({ insight, onApply }: { insight: AiComplianceInsight; onApply?: (insight: AiComplianceInsight) => void }) {
  const [expanded, setExpanded] = useState(false);
  const colors: Record<string, string> = {
    critical: "border-red-200 bg-red-50/50 dark:border-red-900/50 dark:bg-red-900/10",
    warning: "border-amber-200 bg-amber-50/50 dark:border-amber-900/50 dark:bg-amber-900/10",
    info: "border-blue-200 bg-blue-50/50 dark:border-blue-900/50 dark:bg-blue-900/10",
    success: "border-green-200 bg-green-50/50 dark:border-green-900/50 dark:bg-green-900/10",
  };
  const typeIcons: Record<string, React.ReactNode> = {
    gap: <AlertTriangle className="w-3 h-3" />, risk: <Shield className="w-3 h-3" />,
    remediation: <CheckCircle className="w-3 h-3" />, change: <Gavel className="w-3 h-3" />,
    recommendation: <Lightbulb className="w-3 h-3" />, conflict: <AlertTriangle className="w-3 h-3" />,
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
        </div>
        {expanded ? <ChevronDown className="w-2.5 h-2.5 text-gray-400" /> : <ChevronRight className="w-2.5 h-2.5 text-gray-400" />}
      </button>
      <AnimatePresence>
        {expanded && (
          <motion.div initial={{ height: 0 }} animate={{ height: "auto" }} exit={{ height: 0 }} className="overflow-hidden">
            <div className="px-2.5 pb-2.5 space-y-1">
              <div className="flex items-center gap-2 text-[7px] text-gray-500">
                <span>{insight.impactedContracts} contracts affected</span>
                <span>·</span>
                <span>{insight.impactedRegulation}</span>
              </div>
              <div className="bg-white/50 dark:bg-navy-900/50 rounded p-1.5">
                <p className="text-[8px] text-gray-700 dark:text-gray-300">{insight.remediationSuggestion}</p>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-[7px] text-gray-400">{insight.regulatoryReference}</span>
                <button onClick={() => onApply?.(insight)} className="flex items-center gap-1 px-2 py-0.5 bg-purple-500 hover:bg-purple-600 text-white rounded text-[8px] font-medium transition-colors">
                  <Sparkles className="w-2 h-2" /> Apply
                </button>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

// ── Chat Message ─────────────────────────────────────────────────────────

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

interface ComplianceRightPanelProps {
  insights: AiComplianceInsight[];
  analytics: ComplianceAnalytics;
  onInsightApply: (insight: AiComplianceInsight) => void;
}

type RightTab = "assistant" | "insights" | "overview";

export function ComplianceRightPanel({ insights, analytics, onInsightApply }: ComplianceRightPanelProps) {
  const [activeTab, setActiveTab] = useState<RightTab>("insights");
  const [chatMessages, setChatMessages] = useState<ChatMsg[]>([
    { id: "welcome", role: "assistant", content: "I'm your AI Compliance Assistant. I can help identify compliance gaps, suggest remediation actions, and analyze regulatory risks across your contract portfolio.", timestamp: new Date() },
  ]);
  const [chatInput, setChatInput] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const chatEndRef = useRef<HTMLDivElement>(null);
  useEffect(() => { chatEndRef.current?.scrollIntoView({ behavior: "smooth" }); }, [chatMessages]);

  const handleSend = () => {
    if (!chatInput.trim() || isStreaming) return;
    const userMsg: ChatMsg = { id: `u-${Date.now()}`, role: "user", content: chatInput.trim(), timestamp: new Date() };
    setChatMessages(prev => [...prev, userMsg]);
    setChatInput("");
    setIsStreaming(true);
    setTimeout(() => {
      const responses: Record<string, string> = {
        gdpr: "I've identified 12 contracts missing GDPR DPA addendums and 22 contracts with cross-border transfer risks. The highest priority is executing SCCs for EU data transfers.",
        hipaa: "6 healthcare vendor contracts need HIPAA BAA amendments. SecurePath Ltd negotiation is critical - escalated to Level 1.",
        remediation: "There are 89 open remediation tasks. 8 are overdue. The top priority is the GDPR DPA gap affecting 12 contracts with EU counterparties.",
        default: "Based on current compliance analytics, your overall score is 78.4%. The biggest gaps are in GDPR DPA compliance (12 contracts) and FedRAMP authorization (6 vendors). I recommend starting with the critical GDPR findings.",
      };
      const matchedKey = Object.keys(responses).find(k => chatInput.toLowerCase().includes(k));
      const aiMsg: ChatMsg = { id: `a-${Date.now()}`, role: "assistant", content: responses[matchedKey || "default"], timestamp: new Date() };
      setChatMessages(prev => [...prev, aiMsg]);
      setIsStreaming(false);
    }, 1200);
  };

  const tabs: { id: RightTab; label: string; icon: React.ReactNode }[] = [
    { id: "assistant", label: "Assistant", icon: <Brain className="w-3 h-3" /> },
    { id: "insights", label: "AI Insights", icon: <Lightbulb className="w-3 h-3" /> },
    { id: "overview", label: "Overview", icon: <BarChart3 className="w-3 h-3" /> },
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
            {activeTab === tab.id && <motion.div layoutId="comp-right-tab" className="absolute bottom-0 left-0 right-0 h-0.5 bg-gold-500" />}
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
                  placeholder="Ask about compliance..."
                  className="flex-1 px-2 py-1.5 text-[9px] border border-gray-200 dark:border-navy-600 rounded-md bg-gray-50 dark:bg-navy-900 text-navy-900 dark:text-white placeholder-gray-400 focus:outline-none focus:ring-1 focus:ring-gold-400" />
                <button onClick={handleSend} disabled={isStreaming || !chatInput.trim()} className="px-2 py-1.5 bg-gold-500 hover:bg-gold-600 disabled:bg-gray-300 text-white rounded-md transition-colors"><Send className="w-3 h-3" /></button>
              </div>
            </div>
          </div>
        )}

        {activeTab === "insights" && (
          <div className="p-2 space-y-1.5">
            <div className="flex items-center justify-between px-1 mb-1">
              <span className="text-[8px] font-semibold text-gray-400 uppercase tracking-wider">AI Compliance ({insights.length})</span>
              <Sparkles className="w-2.5 h-2.5 text-purple-400" />
            </div>
            {insights.map(i => <AiInsightCard key={i.id} insight={i} onApply={onInsightApply} />)}
          </div>
        )}

        {activeTab === "overview" && (
          <div className="p-2 space-y-3">
            <div className="grid grid-cols-2 gap-1.5">
              {[
                { label: "Overall Score", value: `${analytics.overallScore}%`, color: "text-blue-600" },
                { label: "Audit Readiness", value: `${analytics.auditReadiness}%`, color: "text-green-600" },
                { label: "Remediation", value: `${analytics.remediationProgress}%`, color: "text-purple-600" },
                { label: "Open Gaps", value: "142", color: "text-amber-600" },
              ].map(s => (
                <div key={s.label} className="bg-gray-50 dark:bg-navy-900 rounded-lg p-2 text-center">
                  <p className={`text-sm font-bold ${s.color} tabular-nums`}>{s.value}</p>
                  <p className="text-[7px] text-gray-500 mt-0.5">{s.label}</p>
                </div>
              ))}
            </div>
            {/* Score History */}
            <div>
              <h4 className="text-[8px] font-semibold text-gray-400 uppercase tracking-wider mb-1">Score Trend</h4>
              <div className="space-y-0.5">
                {analytics.scoreHistory.map(s => (
                  <div key={s.date} className="flex items-center gap-2">
                    <span className="text-[7px] text-gray-500 w-6">{s.date}</span>
                    <div className="flex-1 h-2 bg-gray-100 dark:bg-navy-700 rounded-full overflow-hidden">
                      <motion.div initial={{ width: 0 }} animate={{ width: `${s.score}%` }} className="h-full bg-blue-500 rounded-full" />
                    </div>
                    <span className="text-[7px] text-gray-500 tabular-nums w-6 text-right">{s.score}%</span>
                  </div>
                ))}
              </div>
            </div>
            {/* Vendor Distribution */}
            <div>
              <h4 className="text-[8px] font-semibold text-gray-400 uppercase tracking-wider mb-1">Vendor Compliance</h4>
              <div className="space-y-0.5">
                {analytics.vendorComplianceDistribution.map(v => (
                  <div key={v.status} className="flex items-center gap-2">
                    <span className="text-[7px] text-gray-600 dark:text-gray-300 w-20 capitalize">{v.status.replace("_", " ")}</span>
                    <div className="flex-1 h-2 bg-gray-100 dark:bg-navy-700 rounded-full overflow-hidden">
                      <motion.div initial={{ width: 0 }} animate={{ width: `${(v.count / Math.max(...analytics.vendorComplianceDistribution.map(x => x.count))) * 100}%` }}
                        className={`h-full rounded-full ${v.status === "compliant" ? "bg-green-500" : v.status === "at_risk" ? "bg-amber-500" : v.status === "non_compliant" ? "bg-red-500" : "bg-gray-400"}`} />
                    </div>
                    <span className="text-[7px] text-gray-500 tabular-nums w-4 text-right">{v.count}</span>
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

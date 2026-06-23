"use client";

import React, { useState, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Brain, Lightbulb, AlertTriangle, TrendingUp, Shield, BookOpen,
  MessageSquare, Send, Sparkles, ExternalLink, BarChart3, Target,
  FileText, Loader2, RefreshCw, Copy, Check, X, HelpCircle,
  FileSearch, Scale, Globe, Hash, User,
} from "lucide-react";
import { negotiationsService } from "@/services/api/negotiations";

// ── Types ────────────────────────────────────────────────────────

export type CoachContext = 
  | { type: "finding"; findingId: string; findingTitle: string; findingDescription: string; riskLevel?: string }
  | { type: "clause"; clauseId: string; clauseText: string; clauseTitle: string; category: string }
  | { type: "review"; reviewId: string; summary?: string }
  | { type: "contract"; contractId: string; contractTitle: string }
  | { type: "negotiation"; sessionId: string; sessionTitle: string }
  | { type: "obligation"; obligationId: string; obligationTitle: string }
  | { type: "policy"; policyId: string; policyName: string }
  | { type: "template"; templateId: string; templateName: string }
  | { type: "general" };

interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
  actions?: { label: string; action: string }[];
}

// ── Context-specific quick actions ───────────────────────────────

const CONTEXT_ACTIONS: Record<string, { label: string; prompt: string; icon: React.ReactNode }[]> = {
  finding: [
    { label: "Explain", prompt: "Explain this finding in plain English. What is the issue and why does it matter?", icon: <HelpCircle className="w-3 h-3" /> },
    { label: "Business Impact", prompt: "What is the business impact of this finding? What could go wrong if we accept this risk?", icon: <TrendingUp className="w-3 h-3" /> },
    { label: "Market Standard", prompt: "What is the market standard for this type of finding? How do similar companies handle this?", icon: <BarChart3 className="w-3 h-3" /> },
    { label: "Recommended Fix", prompt: "What is the recommended fix for this finding? Show suggested language or action.", icon: <Sparkles className="w-3 h-3" /> },
    { label: "Regulations", prompt: "What regulations or laws apply to this finding? Which compliance requirements are triggered?", icon: <Scale className="w-3 h-3" /> },
    { label: "Negotiate", prompt: "How should I negotiate this finding? What is a good fallback position?", icon: <MessageSquare className="w-3 h-3" /> },
  ],
  clause: [
    { label: "Explain", prompt: "Explain this clause in plain English. What does it mean for each party?", icon: <HelpCircle className="w-3 h-3" /> },
    { label: "Rewrite", prompt: "Rewrite this clause to be more balanced and commercially reasonable.", icon: <Sparkles className="w-3 h-3" /> },
    { label: "Reduce Risk", prompt: "Rewrite this clause to reduce risk for our side while remaining enforceable.", icon: <Shield className="w-3 h-3" /> },
    { label: "Market Standard", prompt: "What is the market standard for this type of clause? How does it compare?", icon: <BarChart3 className="w-3 h-3" /> },
    { label: "Simplify", prompt: "Simplify this clause to make it easier to understand while preserving legal effect.", icon: <FileText className="w-3 h-3" /> },
    { label: "Compare", prompt: "Compare this clause with industry best practices. What's missing or excessive?", icon: <ExternalLink className="w-3 h-3" /> },
  ],
  review: [
    { label: "Summary", prompt: "Summarize this contract review. What are the key findings and overall risk level?", icon: <FileText className="w-3 h-3" /> },
    { label: "Top Risks", prompt: "What are the top 5 risks in this review? Prioritize by severity.", icon: <AlertTriangle className="w-3 h-3" /> },
    { label: "Prioritize", prompt: "Which findings should be fixed first? Prioritize by business impact.", icon: <Target className="w-3 h-3" /> },
    { label: "Executive Summary", prompt: "Generate an executive summary of this contract review for management.", icon: <FileSearch className="w-3 h-3" /> },
  ],
  contract: [
    { label: "Summarize", prompt: "Summarize this contract. What type of agreement is it and what are the key terms?", icon: <FileText className="w-3 h-3" /> },
    { label: "Key Risks", prompt: "What are the key risks in this contract? List the most important ones.", icon: <AlertTriangle className="w-3 h-3" /> },
    { label: "Obligations", prompt: "What are the key obligations for each party in this contract?", icon: <BookOpen className="w-3 h-3" /> },
    { label: "Renewal", prompt: "What are the renewal terms and risks in this contract?", icon: <RefreshCw className="w-3 h-3" /> },
    { label: "Negotiation Strategy", prompt: "What is the recommended negotiation strategy for this contract?", icon: <Target className="w-3 h-3" /> },
  ],
  negotiation: [
    { label: "Strategy", prompt: "What should we negotiate next? Based on the current state of this session.", icon: <Target className="w-3 h-3" /> },
    { label: "Next Best Action", prompt: "What is the single most important thing to do next in this negotiation?", icon: <Sparkles className="w-3 h-3" /> },
    { label: "Summary", prompt: "Summarize the current state of this negotiation session.", icon: <FileText className="w-3 h-3" /> },
  ],
  obligation: [
    { label: "Explain", prompt: "Explain this obligation. What is required and who is responsible?", icon: <HelpCircle className="w-3 h-3" /> },
    { label: "Evidence", prompt: "What evidence is typically required to prove compliance with this obligation?", icon: <FileSearch className="w-3 h-3" /> },
    { label: "Owner", prompt: "Who typically owns this obligation? What department should handle it?", icon: <User className="w-3 h-3" /> },
  ],
  policy: [
    { label: "Explain Rule", prompt: "Explain this policy rule. What does it check and why?", icon: <HelpCircle className="w-3 h-3" /> },
    { label: "Justification", prompt: "Why is this policy rule important? What risk does it address?", icon: <Shield className="w-3 h-3" /> },
  ],
  template: [
    { label: "Usage", prompt: "When should I use this template? What types of contracts is it for?", icon: <HelpCircle className="w-3 h-3" /> },
    { label: "Related", prompt: "What are the related templates I should consider alongside this one?", icon: <ExternalLink className="w-3 h-3" /> },
  ],
};

// ── Context-Aware AI Coach ───────────────────────────────────────

/** Generate a helpful fallback response when the AI API is unavailable. */
function getFallbackResponse(context: CoachContext, question: string): string {
  const q = question.toLowerCase();
  
  // Finding-level fallbacks
  if (context.type === "finding") {
    if (q.includes("explain") || q.includes("what")) {
      return `**Finding:** ${context.findingTitle}\n\n${context.findingDescription}\n\n**Risk Level:** ${context.riskLevel || "Not assessed"}\n\n**Recommendation:** This finding should be reviewed by the appropriate team. Use the AI Rewrite or Coach features with a valid session to get detailed analysis.`;
    }
    if (q.includes("business") || q.includes("impact")) {
      return `**Business Impact Assessment**\n\nThe finding "${context.findingTitle}" has a risk level of ${context.riskLevel || "unknown"}. Business impact depends on the specific contract terms and the counterparty relationship. Consider consulting with Legal and Procurement teams for a full impact assessment.`;
    }
    if (q.includes("market") || q.includes("standard")) {
      return `**Market Standard Analysis**\n\nMarket standards vary by industry, jurisdiction, and contract type. For a precise benchmark, connect this finding to a negotiation session where market data can be analyzed against your specific context.`;
    }
    return `Thank you for your question about "${context.findingTitle}". To provide a detailed analysis, please use this feature within a negotiation session where I have access to the full contract context.`;
  }
  
  // Clause-level fallbacks
  if (context.type === "clause") {
    if (q.includes("explain")) {
      return `**Clause Explanation**\n\nThis is a ${context.category} clause titled "${context.clauseTitle}". Without the full contract context, I can provide general guidance: ${context.category} clauses typically define the rights and obligations of each party regarding ${context.category.replace(/_/g, " ")}. For a detailed analysis with specific recommendations, please open this clause in a negotiation session.`;
    }
    if (q.includes("rewrite") || q.includes("reduce") || q.includes("simplify")) {
      return `**Rewrite Request**\n\nTo rewrite this clause, please use the **Rewrite tab** in this drawer. Select a strategy (Balanced, Customer Protective, Supplier Protective, etc.) and click "AI Rewrite" to generate a new version. You can then edit, compare, and apply the result.`;
    }
    return `Thank you for your question about this ${context.category} clause. For a detailed analysis, please use the Rewrite tab or open this clause in a negotiation session where I can provide context-specific guidance.`;
  }
  
  // Default fallback for other contexts
  return `Thank you for your question. I'm currently analyzing your ${context.type} context. For the most accurate response, please use this feature within a session where I have full access to your contract data.`;
}

interface AiCoachPanelProps {
  context: CoachContext;
  onClose?: () => void;
  sessionId?: string;
}

export function AiCoachPanel({ context, onClose, sessionId }: AiCoachPanelProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [showHistory, setShowHistory] = useState(false);
  const messagesEndRef = React.useRef<HTMLDivElement>(null);

  const contextType = context.type;
  const actions = CONTEXT_ACTIONS[contextType] || [];

  // Welcome message based on context
  React.useEffect(() => {
    const welcomeMessages: Record<string, string> = {
      finding: `I can help you understand this finding. Here are some things to ask:`,
      clause: `I can help you analyze this clause. What would you like to know?`,
      review: `I can help you analyze this contract review. What would you like to explore?`,
      contract: `I can help you understand this contract. What would you like to know?`,
      negotiation: `I can help you with this negotiation. What should we discuss?`,
      obligation: `I can help you understand this obligation. What would you like to know?`,
      policy: `I can help you understand this policy rule.`,
      template: `I can help you understand this template.`,
    };
    if (messages.length === 0) {
      setMessages([{
        id: "welcome",
        role: "assistant",
        content: welcomeMessages[contextType] || "How can I help you?",
        timestamp: new Date(),
      }]);
    }
  }, [contextType]);

  React.useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const buildContextPrompt = useCallback((question: string): string => {
    let ctx = "";
    switch (context.type) {
      case "finding":
        ctx = `I'm looking at a finding titled "${context.findingTitle}" with description: "${context.findingDescription}". Risk level: ${context.riskLevel || "unknown"}.`;
        break;
      case "clause":
        ctx = `I'm looking at a ${context.category} clause titled "${context.clauseTitle}". The clause text is: "${context.clauseText.substring(0, 500)}".`;
        break;
      case "review":
        ctx = `I'm looking at a contract review${context.summary ? `: ${context.summary}` : ""}.`;
        break;
      case "contract":
        ctx = `I'm looking at a contract titled "${context.contractTitle}".`;
        break;
      case "negotiation":
        ctx = `I'm in a negotiation session titled "${context.sessionTitle}".`;
        break;
      case "obligation":
        ctx = `I'm looking at an obligation titled "${context.obligationTitle}".`;
        break;
      case "policy":
        ctx = `I'm looking at a policy rule named "${context.policyName}".`;
        break;
      case "template":
        ctx = `I'm looking at a template named "${context.templateName}".`;
        break;
    }
    return `${ctx}\n\nUser question: ${question}`;
  }, [context]);

  const handleSend = async (prompt?: string) => {
    const q = prompt || input;
    if (!q.trim() || isStreaming) return;

    const userMsg: ChatMessage = {
      id: `user-${Date.now()}`,
      role: "user",
      content: q.trim(),
      timestamp: new Date(),
    };
    setMessages(prev => [...prev, userMsg]);
    setInput("");
    setIsStreaming(true);

    try {
      const contextPrompt = buildContextPrompt(q.trim());
      const coachSessionId = sessionId || (context.type === "negotiation" ? context.sessionId : "") || "";
      const coachClauseId = context.type === "clause" ? context.clauseId : "";
      
      let explanation = "";
      // Only attempt API call if we have a valid session — otherwise skip straight to fallback
      if (coachSessionId && coachClauseId) {
        try {
          const resp = await negotiationsService.aiCoach(coachSessionId, coachClauseId, {
            clause_text: contextPrompt,
            question: q.trim(),
          });
          explanation = resp.explanation || "";
        } catch {
          explanation = getFallbackResponse(context, q.trim());
        }
      } else {
        explanation = getFallbackResponse(context, q.trim());
      }

      const aiMsg: ChatMessage = {
        id: `ai-${Date.now()}`,
        role: "assistant",
        content: explanation,
        timestamp: new Date(),
        actions: actions.slice(0, 3).map(a => ({ label: a.label, action: a.prompt })),
      };
      setMessages(prev => [...prev, aiMsg]);
    } catch {
      setMessages(prev => [...prev, {
        id: `ai-${Date.now()}`,
        role: "assistant",
        content: "I'm sorry, I couldn't process that request right now. Please try again.",
        timestamp: new Date(),
      }]);
    } finally {
      setIsStreaming(false);
    }
  };

  const contextLabel: Record<string, string> = {
    finding: "Finding",
    clause: "Clause",
    review: "Review",
    contract: "Contract",
    negotiation: "Negotiation",
    obligation: "Obligation",
    policy: "Policy",
    template: "Template",
  };

  const contextIcons: Record<string, React.ReactNode> = {
    finding: <AlertTriangle className="w-3 h-3" />,
    clause: <FileText className="w-3 h-3" />,
    review: <FileSearch className="w-3 h-3" />,
    contract: <FileText className="w-3 h-3" />,
    negotiation: <MessageSquare className="w-3 h-3" />,
    obligation: <BookOpen className="w-3 h-3" />,
    policy: <Shield className="w-3 h-3" />,
    template: <Sparkles className="w-3 h-3" />,
  };

  return (
    <div className="flex flex-col h-full bg-white dark:bg-navy-800">
      {/* Header */}
      <div className="px-3 py-2 border-b border-gray-200 dark:border-navy-700 flex items-center justify-between">
        <div className="flex items-center gap-1.5">
          <Brain className="w-3.5 h-3.5 text-purple-500" />
          <span className="text-[10px] font-semibold text-navy-900 dark:text-white">AI Coach</span>
          {contextType !== "general" && (
            <span className="flex items-center gap-0.5 px-1.5 py-0.5 bg-purple-50 dark:bg-purple-900/20 text-purple-600 dark:text-purple-400 rounded-full text-[8px] font-medium">
              {contextIcons[contextType]}
              {contextLabel[contextType] || "General"}
            </span>
          )}
        </div>
        <div className="flex items-center gap-1">
          <button onClick={() => setShowHistory(!showHistory)}
            className={`p-0.5 rounded ${showHistory ? "bg-gray-100" : ""} text-gray-400 hover:text-gray-600`}
            title="History"
          >
            <RefreshCw className="w-3 h-3" />
          </button>
          {onClose && (
            <button onClick={onClose} className="p-0.5 text-gray-400 hover:text-gray-600 rounded">
              <X className="w-3 h-3" />
            </button>
          )}
        </div>
      </div>

      {/* Context indicator */}
      {contextType !== "general" && (
        <div className="px-3 py-1 bg-purple-50/50 dark:bg-purple-900/10 border-b border-purple-100 dark:border-purple-900/30">
          <p className="text-[8px] text-purple-600 dark:text-purple-400 font-medium truncate">
            {context.type === "finding" && `📋 ${context.findingTitle}`}
            {context.type === "clause" && `📄 ${context.clauseTitle}`}
            {context.type === "review" && `🔍 Review ${context.reviewId?.substring(0, 8)}...`}
            {context.type === "contract" && `📑 ${context.contractTitle}`}
            {context.type === "negotiation" && `💬 ${context.sessionTitle}`}
            {context.type === "obligation" && `📋 ${context.obligationTitle}`}
            {context.type === "policy" && `🛡️ ${context.policyName}`}
            {context.type === "template" && `✨ ${context.templateName}`}
          </p>
        </div>
      )}

      {/* Quick Actions */}
      {actions.length > 0 && (
        <div className="px-2 py-1.5 border-b border-gray-100 dark:border-navy-700">
          <div className="flex flex-wrap gap-1">
            {actions.map((action, i) => (
              <button
                key={i}
                onClick={() => handleSend(action.prompt)}
                disabled={isStreaming}
                className="inline-flex items-center gap-0.5 px-1.5 py-0.5 bg-gray-100 dark:bg-navy-700 text-gray-600 dark:text-gray-300 rounded-full text-[8px] hover:bg-gray-200 dark:hover:bg-navy-600 transition-colors disabled:opacity-50"
              >
                {action.icon}
                {action.label}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-2 space-y-2">
        {messages.map(msg => (
          <div key={msg.id} className={`flex gap-1.5 ${msg.role === "user" ? "flex-row-reverse" : ""}`}>
            <div className={`w-4 h-4 rounded-full flex items-center justify-center text-[6px] font-bold text-white flex-shrink-0 mt-0.5 ${
              msg.role === "assistant" ? "bg-purple-500" : "bg-navy-500"
            }`}>
              {msg.role === "assistant" ? "AI" : "U"}
            </div>
            <div className={`max-w-[88%] rounded-lg px-2 py-1.5 ${
              msg.role === "user"
                ? "bg-navy-500 text-white"
                : "bg-gray-100 dark:bg-navy-700 text-navy-900 dark:text-white"
            }`}>
              <p className="text-[9px] leading-relaxed whitespace-pre-wrap">{msg.content}</p>
              {msg.actions && msg.actions.length > 0 && (
                <div className="flex flex-wrap gap-1 mt-1.5 pt-1 border-t border-white/20 dark:border-navy-600">
                  {msg.actions.map((a, i) => (
                    <button key={i} onClick={() => handleSend(a.action)}
                      className="text-[7px] px-1 py-0.5 bg-white/20 hover:bg-white/30 rounded text-white transition-colors"
                    >
                      {a.label}
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>
        ))}
        {isStreaming && (
          <div className="flex gap-1.5">
            <div className="w-4 h-4 rounded-full bg-purple-500 flex items-center justify-center text-[6px] font-bold text-white flex-shrink-0 mt-0.5">AI</div>
            <div className="bg-gray-100 dark:bg-navy-700 rounded-lg px-2 py-1.5">
              <div className="flex items-center gap-1">
                <Loader2 className="w-2.5 h-2.5 text-purple-500 animate-spin" />
                <span className="text-[8px] text-gray-500">Thinking...</span>
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="p-2 border-t border-gray-200 dark:border-navy-700">
        <div className="flex gap-1">
          <input
            type="text"
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => e.key === "Enter" && handleSend()}
            placeholder="Ask anything..."
            className="flex-1 px-2 py-1 text-[9px] border border-gray-200 dark:border-navy-600 rounded-md bg-gray-50 dark:bg-navy-900 text-navy-900 dark:text-white placeholder-gray-400 focus:outline-none focus:ring-1 focus:ring-gold-400"
          />
          <button onClick={() => handleSend()} disabled={isStreaming || !input.trim()}
            className="px-2 py-1 bg-purple-600 hover:bg-purple-700 disabled:bg-purple-400 text-white rounded-md transition-colors"
          >
            <Send className="w-3 h-3" />
          </button>
        </div>
      </div>
    </div>
  );
}

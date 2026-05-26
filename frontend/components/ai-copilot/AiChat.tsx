"use client";

import React, { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Send, Loader2, Bot, User, Sparkles, ChevronDown, AlertTriangle, FileText, Scale, ShoppingCart, TrendingUp, Shield, Workflow, Handshake, Quote, Zap } from "lucide-react";
import type { AiMessage, CopilotMode, AiCitation, AiSuggestedAction } from "./types";
import { COPILOT_MODES } from "./types";
import { aiService } from "./service";

interface AiChatProps {
  mode: CopilotMode;
  onModeChange: (mode: CopilotMode) => void;
  onExecuteAction: (action: AiSuggestedAction) => void;
}

export function AiChat({ mode, onModeChange, onExecuteAction }: AiChatProps) {
  const [messages, setMessages] = useState<AiMessage[]>([
    {
      id: "welcome",
      role: "assistant",
      content: `## 👋 Welcome to AI Copilot

I'm your enterprise contract intelligence assistant. I can help you analyze contracts, assess risks, compare benchmarks, and execute actions across the platform.

**Try asking me:**
- "Summarize top portfolio risks"
- "Find contracts with uncapped liability"
- "Which vendors pose renewal risk?"
- "Generate fallback indemnity language"

Select a specialized mode below for focused assistance.`,
      agent: "executive_intel",
      timestamp: new Date().toISOString(),
      status: "complete",
      followUpSuggestions: [
        "Summarize top portfolio risks",
        "Find contracts with uncapped liability",
        "Which vendors pose renewal risk?",
        "Generate fallback indemnity language",
      ],
    },
  ]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [streamingContent, setStreamingContent] = useState("");
  const [showSuggestions, setShowSuggestions] = useState(true);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamingContent]);

  const handleSend = async () => {
    if (!input.trim() || streaming) return;

    const userMsg: AiMessage = {
      id: `user-${Date.now()}`,
      role: "user",
      content: input.trim(),
      timestamp: new Date().toISOString(),
      status: "complete",
    };

    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setStreaming(true);
    setStreamingContent("");
    setShowSuggestions(false);

    // Simulate streaming
    await aiService.streamMessage(
      userMsg.content,
      mode,
      (chunk) => setStreamingContent((prev) => prev + chunk),
      (response) => {
        setMessages((prev) => [...prev, response]);
        setStreaming(false);
        setStreamingContent("");
      }
    );
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleSuggestionClick = (suggestion: string) => {
    setInput(suggestion);
    inputRef.current?.focus();
  };

  const lastMessage = messages[messages.length - 1];

  return (
    <div className="flex flex-col h-full">
      {/* Mode selector */}
      <div className="px-3 py-2 border-b border-gray-100">
        <div className="flex gap-1 overflow-x-auto pb-0.5">
          {COPILOT_MODES.map((cm) => (
            <button
              key={cm.id}
              onClick={() => onModeChange(cm.id)}
              className={`flex items-center gap-1 px-2 py-1 text-[10px] font-medium rounded-md whitespace-nowrap transition-all ${
                mode === cm.id ? "bg-navy-700 text-white shadow-sm" : "text-gray-500 hover:text-gray-700 hover:bg-gray-100"
              }`}
            >
              {cm.label}
            </button>
          ))}
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-3 space-y-3">
        {messages.map((msg) => (
          <MessageBubble key={msg.id} message={msg} onSuggestionClick={handleSuggestionClick} onExecuteAction={onExecuteAction} />
        ))}

        {/* Streaming message */}
        {streaming && streamingContent && (
          <div className="flex items-start gap-2.5">
            <div className="w-7 h-7 rounded-full bg-navy-100 flex items-center justify-center flex-shrink-0 mt-1">
              <Bot className="w-4 h-4 text-navy-600" />
            </div>
            <div className="flex-1 min-w-0">
              <div className="p-3 bg-navy-50 rounded-xl rounded-tl-none border border-navy-100">
                <p className="text-[13px] text-gray-700 leading-relaxed whitespace-pre-wrap">
                  {streamingContent}
                  <span className="inline-block w-1.5 h-4 bg-navy-500 animate-pulse ml-0.5" />
                </p>
              </div>
            </div>
          </div>
        )}

        {streaming && !streamingContent && (
          <div className="flex items-start gap-2.5">
            <div className="w-7 h-7 rounded-full bg-navy-100 flex items-center justify-center flex-shrink-0 mt-1">
              <Bot className="w-4 h-4 text-navy-600" />
            </div>
            <div className="flex items-center gap-1 p-3 bg-navy-50 rounded-xl rounded-tl-none border border-navy-100">
              <div className="w-1.5 h-1.5 bg-navy-400 rounded-full animate-bounce" style={{ animationDelay: "0ms" }} />
              <div className="w-1.5 h-1.5 bg-navy-400 rounded-full animate-bounce" style={{ animationDelay: "150ms" }} />
              <div className="w-1.5 h-1.5 bg-navy-400 rounded-full animate-bounce" style={{ animationDelay: "300ms" }} />
            </div>
          </div>
        )}

        {/* Suggested follow-ups */}
        {!streaming && lastMessage?.followUpSuggestions && lastMessage.followUpSuggestions.length > 0 && (
          <div className="pt-1">
            <p className="text-[10px] text-gray-400 mb-1.5 font-medium">Suggested follow-ups:</p>
            <div className="flex flex-wrap gap-1">
              {lastMessage.followUpSuggestions.map((s, i) => (
                <button
                  key={i}
                  onClick={() => handleSuggestionClick(s)}
                  className="text-[10px] px-2 py-1 rounded-full bg-gray-100 text-gray-600 hover:bg-navy-50 hover:text-navy-700 transition-colors"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="border-t border-gray-100 p-3 bg-white">
        <div className="flex items-end gap-2">
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask AI Copilot anything..."
            rows={1}
            className="flex-1 text-xs border border-gray-200 rounded-lg px-3 py-2 resize-none focus:border-navy-400 focus:ring-1 focus:ring-navy-400 placeholder-gray-400 max-h-20"
            style={{ minHeight: 32 }}
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || streaming}
            className="p-2 rounded-lg bg-navy-700 text-white hover:bg-navy-800 disabled:opacity-40 disabled:cursor-not-allowed transition-colors flex-shrink-0"
          >
            {streaming ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
          </button>
        </div>
        <p className="text-[9px] text-gray-400 mt-1">AI Copilot can execute actions. Review before confirming.</p>
      </div>
    </div>
  );
}

// ── Message Bubble ──────────────────────────────────────────────────────────

function MessageBubble({
  message,
  onSuggestionClick,
  onExecuteAction,
}: {
  message: AiMessage;
  onSuggestionClick: (s: string) => void;
  onExecuteAction: (a: AiSuggestedAction) => void;
}) {
  const [showReasoning, setShowReasoning] = useState(false);
  const isUser = message.role === "user";

  if (isUser) {
    return (
      <div className="flex items-start gap-2.5 justify-end">
        <div className="flex-1 max-w-[85%]">
          <div className="p-3 bg-navy-700 rounded-xl rounded-tr-none">
            <p className="text-[13px] text-white leading-relaxed whitespace-pre-wrap">{message.content}</p>
          </div>
          <p className="text-[9px] text-gray-400 mt-0.5 text-right">{formatTime(message.timestamp)}</p>
        </div>
        <div className="w-7 h-7 rounded-full bg-navy-800 flex items-center justify-center flex-shrink-0 mt-1">
          <User className="w-4 h-4 text-white" />
        </div>
      </div>
    );
  }

  return (
    <div className="flex items-start gap-2.5">
      <div className="w-7 h-7 rounded-full bg-navy-100 flex items-center justify-center flex-shrink-0 mt-1">
        <Bot className="w-4 h-4 text-navy-600" />
      </div>
      <div className="flex-1 min-w-0">
        <div className="p-3 bg-navy-50 rounded-xl rounded-tl-none border border-navy-100">
          {/* Agent badge */}
          {message.agent && (
            <div className="flex items-center gap-1 mb-1.5">
              <Sparkles className="w-3 h-3 text-navy-500" />
              <span className="text-[9px] font-medium text-navy-600 uppercase tracking-wider">{message.agent.replace(/_/g, " ")}</span>
              {message.confidence && (
                <span className="text-[9px] text-gray-400 ml-auto">{message.confidence}% confidence</span>
              )}
            </div>
          )}
          {/* Content */}
          <div className="text-[13px] text-gray-700 leading-relaxed prose prose-sm max-w-none">
            <Markdown content={message.content} />
          </div>
        </div>

        {/* Citations */}
        {message.citations && message.citations.length > 0 && (
          <div className="mt-1.5 flex flex-wrap gap-1">
            {message.citations.map((c, i) => (
              <div key={i} className="text-[9px] px-1.5 py-0.5 rounded bg-blue-50 text-blue-700 flex items-center gap-0.5">
                <FileText className="w-2.5 h-2.5" />
                {c.source}
                <span className="text-blue-400">· {Math.round(c.relevance * 100)}%</span>
              </div>
            ))}
          </div>
        )}

        {/* Reasoning (expandable) */}
        {message.reasoning && (
          <button
            onClick={() => setShowReasoning(!showReasoning)}
            className="mt-1 text-[9px] text-gray-400 hover:text-navy-600 flex items-center gap-0.5 transition-colors"
          >
            <Zap className="w-2.5 h-2.5" />
            {showReasoning ? "Hide reasoning" : "Show reasoning"}
            <ChevronDown className={`w-2.5 h-2.5 transition-transform ${showReasoning ? "rotate-180" : ""}`} />
          </button>
        )}
        {showReasoning && message.reasoning && (
          <div className="mt-1 p-2 bg-gray-50 rounded border border-gray-200 text-[10px] text-gray-600 leading-relaxed">
            {message.reasoning}
          </div>
        )}

        {/* Suggested Actions */}
        {message.suggestedActions && message.suggestedActions.length > 0 && (
          <div className="mt-2 space-y-1">
            <p className="text-[9px] font-medium text-gray-400 uppercase">Actions</p>
            {message.suggestedActions.map((action) => (
              <button
                key={action.id}
                onClick={() => onExecuteAction(action)}
                className="w-full text-left text-[10px] px-2.5 py-1.5 rounded-lg bg-white border border-gray-200 hover:border-navy-300 hover:bg-navy-50 transition-all flex items-center gap-1.5"
              >
                <Zap className="w-3 h-3 text-navy-500" />
                <span className="font-medium text-navy-700">{action.label}</span>
                <span className="text-gray-400 ml-auto">{action.requiresConfirmation ? "Requires confirmation" : "Instant"}</span>
              </button>
            ))}
          </div>
        )}

        <p className="text-[9px] text-gray-400 mt-0.5">{formatTime(message.timestamp)}</p>
      </div>
    </div>
  );
}

// ── Simple Markdown Renderer ────────────────────────────────────────────────

function Markdown({ content }: { content: string }) {
  const lines = content.split("\n");
  const elements: React.ReactNode[] = [];
  let inTable = false;
  let tableRows: string[][] = [];
  let key = 0;

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];

    // Headers
    if (line.startsWith("### ")) {
      elements.push(<h3 key={key++} className="text-sm font-semibold text-navy-900 mt-3 mb-1">{line.slice(4)}</h3>);
      continue;
    }
    if (line.startsWith("## ")) {
      elements.push(<h2 key={key++} className="text-base font-bold text-navy-900 mt-3 mb-1.5">{line.slice(3)}</h2>);
      continue;
    }

    // Table
    if (line.startsWith("|") && line.endsWith("|")) {
      if (!inTable) { inTable = true; tableRows = []; }
      const cells = line.split("|").filter(Boolean).map((c) => c.trim());
      if (!cells.every((c) => /^[-:]+$/.test(c))) {
        tableRows.push(cells);
      }
      if (i === lines.length - 1 || !lines[i + 1]?.startsWith("|")) {
        inTable = false;
        elements.push(<TableView key={key++} headers={tableRows[0]} rows={tableRows.slice(1)} />);
      }
      continue;
    }

    // Bullet points
    if (line.startsWith("- ") || line.startsWith("* ")) {
      elements.push(
        <div key={key++} className="flex items-start gap-1.5 text-[13px] text-gray-700 py-0.5">
          <span className="text-navy-400 mt-1 flex-shrink-0">•</span>
          <span>{line.slice(2)}</span>
        </div>
      );
      continue;
    }

    // Numbered items
    const numberedMatch = line.match(/^\d+\.\s(.+)/);
    if (numberedMatch) {
      elements.push(
        <div key={key++} className="flex items-start gap-1.5 text-[13px] text-gray-700 py-0.5">
          <span className="text-navy-500 font-medium flex-shrink-0">{line.match(/^\d+/)?.[0]}.</span>
          <span>{numberedMatch[1]}</span>
        </div>
      );
      continue;
    }

    // Bold text
    if (line.startsWith("**") && line.endsWith("**")) {
      elements.push(<p key={key++} className="text-[13px] font-semibold text-navy-800 mt-2 mb-1">{line.slice(2, -2)}</p>);
      continue;
    }

    // Empty line
    if (line.trim() === "") {
      elements.push(<div key={key++} className="h-1" />);
      continue;
    }

    // Regular paragraph
    elements.push(<p key={key++} className="text-[13px] text-gray-700 leading-relaxed">{line}</p>);
  }

  return <>{elements}</>;
}

function TableView({ headers, rows }: { headers: string[]; rows: string[][] }) {
  return (
    <div className="my-2 overflow-x-auto">
      <table className="w-full text-[11px] border-collapse">
        <thead>
          <tr className="border-b border-gray-200">
            {headers?.map((h, i) => (
              <th key={i} className="text-left py-1.5 px-2 font-semibold text-gray-600">{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i} className="border-b border-gray-50">
              {row.map((cell, j) => (
                <td key={j} className="py-1.5 px-2 text-gray-700">{cell}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function formatTime(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" });
}

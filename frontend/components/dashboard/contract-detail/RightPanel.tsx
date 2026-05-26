"use client";

import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Brain, AlertTriangle, Lightbulb, TrendingUp, BarChart3, FileEdit, ChevronDown, ChevronUp, Sparkles, MessageSquare, Send, ClipboardCheck, Scale } from "lucide-react";
import type { ClauseData, NegotiationIssue, WorkflowState } from "./types";
import { RISK_BG, RISK_TEXT, RISK_BG_LIGHT } from "./types";

interface RightPanelProps {
  clause: ClauseData | null;
  issues: NegotiationIssue[];
  workflow: WorkflowState;
  onAddComment: (clauseId: string, body: string) => void;
}

export function RightPanel({ clause, issues, workflow, onAddComment }: RightPanelProps) {
  const [commentText, setCommentText] = useState("");
  const [expandedSection, setExpandedSection] = useState<string>("ai-insights");

  if (!clause) {
    return (
      <div className="flex flex-col h-full bg-white border-l border-gray-200">
        <div className="flex items-center justify-center h-full text-gray-400">
          <div className="text-center p-6">
            <Brain className="w-10 h-10 mx-auto mb-3 text-gray-300" />
            <p className="text-sm font-medium">Select a clause</p>
            <p className="text-xs mt-1">Click on a clause in the document to view AI analysis</p>
          </div>
        </div>
      </div>
    );
  }

  const toggleSection = (id: string) => {
    setExpandedSection(expandedSection === id ? "" : id);
  };

  const clauseIssues = issues.filter((i) => i.clauseId === clause.id);

  return (
    <div className="flex flex-col h-full bg-white border-l border-gray-200">
      {/* Header */}
      <div className="px-4 py-3 border-b border-gray-100">
        <div className="flex items-center gap-2"><Brain className="w-4 h-4 text-navy-700" /><h3 className="text-xs font-semibold text-navy-900">Clause Intelligence</h3></div>
        <p className="text-[10px] text-gray-500 mt-0.5">Section {clause.section}: {clause.title}</p>
      </div>

      <div className="flex-1 overflow-y-auto p-3 space-y-2">
        {/* AI Summary */}
        <Section title="AI Analysis" icon={<Brain className="w-3.5 h-3.5" />} id="ai-insights" expanded={expandedSection === "ai-insights"} onToggle={toggleSection}>
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-[10px] text-gray-500">Risk Score</span>
              <span className={`text-[11px] font-bold px-2 py-0.5 rounded-full ${RISK_BG_LIGHT[clause.riskLevel]} ${RISK_TEXT[clause.riskLevel]}`}>{clause.riskScore}/10</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-[10px] text-gray-500">Market Percentile</span>
              <span className="text-[11px] font-medium">{clause.benchmarkPercentile}th</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-[10px] text-gray-500">AI Confidence</span>
              <span className="text-[11px] font-medium">{clause.confidence}%</span>
            </div>
            <div className="p-2 bg-navy-50 rounded border border-navy-100 text-[10px] text-gray-700 leading-relaxed">
              {clause.aiExplanation}
            </div>
          </div>
        </Section>

        {/* Fallback Language */}
        {clause.fallbackLanguage && (
          <Section title="Suggested Fallback" icon={<FileEdit className="w-3.5 h-3.5" />} id="fallback" expanded={expandedSection === "fallback"} onToggle={toggleSection}>
            <div className="p-2 bg-green-50 rounded border border-green-100">
              <p className="text-[10px] font-semibold text-green-700 uppercase mb-1">Recommended Language</p>
              <p className="text-[10px] text-gray-700 leading-relaxed italic">"{clause.fallbackLanguage}"</p>
            </div>
          </Section>
        )}

        {/* Negotiation Issues */}
        {clauseIssues.length > 0 && (
          <Section title="Negotiation Issues" icon={<Scale className="w-3.5 h-3.5" />} id="negotiation" expanded={expandedSection === "negotiation"} onToggle={toggleSection}>
            <div className="space-y-1.5">
              {clauseIssues.map((issue) => (
                <div key={issue.id} className="p-2 bg-white border border-gray-100 rounded-lg">
                  <div className="flex items-center justify-between mb-1">
                    <span className={`text-[9px] font-medium px-1.5 py-0.5 rounded-full ${issue.priority === "high" ? "bg-red-50 text-red-700" : "bg-yellow-50 text-yellow-700"}`}>{issue.priority}</span>
                    <span className={`text-[9px] font-medium px-1.5 py-0.5 rounded-full ${issue.status === "open" ? "bg-red-50 text-red-700" : issue.status === "discussing" ? "bg-blue-50 text-blue-700" : "bg-green-50 text-green-700"}`}>{issue.status}</span>
                  </div>
                  <p className="text-[10px] text-gray-600 mb-1">{issue.issue}</p>
                  <div className="text-[9px] space-y-0.5">
                    <p><span className="text-gray-400">You:</span> <span className="text-gray-700">{issue.yourPosition}</span></p>
                    <p><span className="text-gray-400">Vendor:</span> <span className="text-gray-700">{issue.vendorPosition}</span></p>
                    <p><span className="text-green-600 font-medium">Recommended:</span> <span className="text-gray-700">{issue.recommendedPosition}</span></p>
                  </div>
                </div>
              ))}
            </div>
          </Section>
        )}

        {/* Workflow Status */}
        <Section title="Workflow" icon={<ClipboardCheck className="w-3.5 h-3.5" />} id="workflow" expanded={expandedSection === "workflow"} onToggle={toggleSection}>
          <div className="space-y-2">
            <div className="flex items-center justify-between text-[10px]">
              <span className="text-gray-500">SLA Remaining</span>
              <span className={`font-medium ${workflow.slaRemaining < 24 ? "text-red-600" : "text-green-600"}`}>{workflow.slaRemaining}h</span>
            </div>
            <div className="space-y-1">
              {workflow.stages.map((stage) => (
                <div key={stage.id} className="flex items-center gap-2 text-[10px]">
                  <div className={`w-2 h-2 rounded-full ${stage.status === "completed" ? "bg-green-500" : stage.status === "current" ? "bg-navy-500" : "bg-gray-200"}`} />
                  <span className={`flex-1 ${stage.status === "current" ? "font-medium text-navy-900" : "text-gray-500"}`}>{stage.label}</span>
                  {stage.assignee && <span className="text-gray-400">{stage.assignee}</span>}
                </div>
              ))}
            </div>
          </div>
        </Section>

        {/* Comments */}
        <Section title={`Comments (${clause.comments.length})`} icon={<MessageSquare className="w-3.5 h-3.5" />} id="comments" expanded={expandedSection === "comments"} onToggle={toggleSection}>
          <div className="space-y-2">
            {clause.comments.map((c) => (
              <div key={c.id} className="p-2 bg-white border border-gray-100 rounded-lg">
                <div className="flex items-center justify-between mb-0.5">
                  <span className="text-[10px] font-medium text-navy-700">{c.author}</span>
                  <span className="text-[8px] text-gray-400">{formatTime(c.createdAt)}</span>
                </div>
                <p className="text-[10px] text-gray-600">{c.body}</p>
                {c.mentions.length > 0 && (
                  <div className="flex gap-1 mt-1">{c.mentions.map((m) => <span key={m} className="text-[8px] px-1 py-0.5 rounded bg-navy-50 text-navy-600">@{m}</span>)}</div>
                )}
              </div>
            ))}
            <div className="flex gap-1.5 pt-1">
              <input value={commentText} onChange={(e) => setCommentText(e.target.value)} placeholder="Add a comment..." className="flex-1 text-[10px] border border-gray-200 rounded-md px-2 py-1.5 focus:border-navy-400 focus:ring-1 focus:ring-navy-400" />
              <button onClick={() => { if (commentText.trim()) { onAddComment(clause.id, commentText.trim()); setCommentText(""); } }} className="p-1.5 rounded-md bg-navy-700 text-white hover:bg-navy-800 transition-colors"><Send className="w-3 h-3" /></button>
            </div>
          </div>
        </Section>
      </div>
    </div>
  );
}

// ── Collapsible Section ─────────────────────────────────────────────────────

function Section({ title, icon, id, expanded, onToggle, children }: {
  title: string; icon: React.ReactNode; id: string; expanded: boolean; onToggle: (id: string) => void; children: React.ReactNode;
}) {
  return (
    <div className="bg-white border border-gray-100 rounded-lg overflow-hidden">
      <button onClick={() => onToggle(id)} className="w-full flex items-center justify-between px-3 py-2 hover:bg-gray-50 transition-colors">
        <div className="flex items-center gap-1.5"><span className="text-navy-600">{icon}</span><span className="text-[11px] font-medium text-navy-900">{title}</span></div>
        {expanded ? <ChevronUp className="w-3 h-3 text-gray-400" /> : <ChevronDown className="w-3 h-3 text-gray-400" />}
      </button>
      <AnimatePresence>
        {expanded && <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }} exit={{ height: 0, opacity: 0 }} className="px-3 pb-3">{children}</motion.div>}
      </AnimatePresence>
    </div>
  );
}

function formatTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const hrs = Math.floor(diff / 3600000);
  if (hrs < 1) return "just now"; if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

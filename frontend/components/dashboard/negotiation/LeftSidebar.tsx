"use client";

import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  AlertTriangle, CheckCircle, Clock, User, MessageSquare, ChevronRight,
  ChevronDown, FileText, BookOpen, Shield, Flag, ArrowUpCircle,
  Filter, Search, Circle, MoreHorizontal, Play,
} from "lucide-react";
import type { NegotiationIssue, Participant, NegotiationPlaybook, ClauseContent, CommentItem } from "./types";

// ── Issue Item ───────────────────────────────────────────────────────────

function IssueItem({ issue, isActive, onClick }: { issue: NegotiationIssue; isActive: boolean; onClick: () => void }) {
  const severityColor = {
    blocker: "text-red-500 bg-red-50 dark:bg-red-900/20",
    critical: "text-orange-500 bg-orange-50 dark:bg-orange-900/20",
    major: "text-yellow-500 bg-yellow-50 dark:bg-yellow-900/20",
    minor: "text-blue-500 bg-blue-50 dark:bg-blue-900/20",
    info: "text-gray-500 bg-gray-50 dark:bg-gray-900/20",
  };
  const statusIcon = issue.status === "resolved" ? <CheckCircle className="w-3 h-3 text-green-500" /> :
    issue.status === "escalated" ? <ArrowUpCircle className="w-3 h-3 text-red-500" /> :
    issue.status === "in-review" ? <Clock className="w-3 h-3 text-blue-500" /> :
    <Circle className="w-3 h-3 text-gray-400" />;

  return (
    <motion.button
      layout
      onClick={onClick}
      className={`w-full text-left px-3 py-2 rounded-lg transition-all ${
        isActive
          ? "bg-navy-50 dark:bg-navy-700/50 border border-navy-200 dark:border-navy-600"
          : "hover:bg-gray-50 dark:hover:bg-navy-800/50 border border-transparent"
      }`}
      whileHover={{ x: 2 }}
    >
      <div className="flex items-start gap-2">
        <div className={`mt-0.5 w-5 h-5 rounded flex items-center justify-center flex-shrink-0 ${severityColor[issue.severity]}`}>
          <AlertTriangle className="w-3 h-3" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-1.5">
            {statusIcon}
            <span className="text-xs font-medium text-navy-900 dark:text-white truncate">{issue.title}</span>
          </div>
          <p className="text-[10px] text-gray-500 dark:text-gray-400 mt-0.5 truncate">{issue.sectionNumber} &middot; {issue.category}</p>
          <div className="flex items-center gap-2 mt-1">
            <div className="flex items-center gap-1 text-[10px] text-gray-400">
              <User className="w-2.5 h-2.5" />
              <span>{issue.assignee.split(" ").pop()}</span>
            </div>
            {issue.comments.length > 0 && (
              <div className="flex items-center gap-1 text-[10px] text-gray-400">
                <MessageSquare className="w-2.5 h-2.5" />
                <span>{issue.comments.length}</span>
              </div>
            )}
            {issue.escalationLevel > 0 && (
              <span className="text-[10px] text-red-500 font-medium">L{issue.escalationLevel}</span>
            )}
          </div>
        </div>
      </div>
    </motion.button>
  );
}

// ── Clause Navigation Item ───────────────────────────────────────────────

function ClauseNavItem({ clause, isActive, redlineCount, onClick }: { clause: ClauseContent; isActive: boolean; redlineCount: number; onClick: () => void }) {
  const riskDot = clause.riskLevel === "critical" ? "bg-red-500" :
    clause.riskLevel === "high" ? "bg-orange-500" :
    clause.riskLevel === "medium" ? "bg-yellow-500" : "bg-green-500";

  return (
    <motion.button
      onClick={onClick}
      className={`w-full text-left px-3 py-1.5 rounded-lg transition-all flex items-center gap-2 ${
        isActive
          ? "bg-navy-50 dark:bg-navy-700/50 border border-navy-200 dark:border-navy-600"
          : "hover:bg-gray-50 dark:hover:bg-navy-800/50 border border-transparent"
      }`}
      whileHover={{ x: 2 }}
    >
      <div className={`w-2 h-2 rounded-full flex-shrink-0 ${riskDot}`} />
      <div className="flex-1 min-w-0">
        <span className="text-xs font-medium text-navy-900 dark:text-white truncate block">{clause.title}</span>
        <span className="text-[10px] text-gray-400">{clause.sectionNumber}</span>
      </div>
      {redlineCount > 0 && (
        <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded-full ${
          clause.riskLevel === "high" || clause.riskLevel === "critical"
            ? "bg-red-100 text-red-600 dark:bg-red-900/30 dark:text-red-400"
            : "bg-gray-100 text-gray-500 dark:bg-navy-700 dark:text-gray-400"
        }`}>
          {redlineCount}
        </span>
      )}
    </motion.button>
  );
}

// ── Participant Badge ────────────────────────────────────────────────────

function ParticipantBadge({ participant }: { participant: Participant }) {
  const roleColors: Record<string, string> = {
    owner: "bg-gold-100 text-gold-700 dark:bg-gold-900/30 dark:text-gold-400",
    reviewer: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400",
    approver: "bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400",
    viewer: "bg-gray-100 text-gray-600 dark:bg-navy-700 dark:text-gray-400",
    external: "bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400",
  };

  return (
    <div className="flex items-center gap-2 px-3 py-1.5 hover:bg-gray-50 dark:hover:bg-navy-800/50 rounded-lg transition-colors">
      <div className={`w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-bold text-white ${
        participant.role === "owner" ? "bg-gold-500" :
        participant.role === "external" ? "bg-orange-500" :
        "bg-navy-500"
      }`}>
        {participant.avatar}
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-1.5">
          <span className="text-xs font-medium text-navy-900 dark:text-white truncate">{participant.name}</span>
          {participant.isOnline && <div className="w-1.5 h-1.5 rounded-full bg-green-500 flex-shrink-0" />}
        </div>
        <span className={`text-[10px] ${roleColors[participant.role]} px-1 rounded`}>
          {participant.role}
        </span>
      </div>
      {participant.pendingApprovals > 0 && (
        <span className="text-[10px] bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400 px-1.5 py-0.5 rounded-full font-medium">
          {participant.pendingApprovals}
        </span>
      )}
    </div>
  );
}

// ── Playbook Card ────────────────────────────────────────────────────────

function PlaybookCard({ playbook }: { playbook: NegotiationPlaybook }) {
  const [expanded, setExpanded] = useState(false);
  return (
    <div className="border border-gray-200 dark:border-navy-600 rounded-lg overflow-hidden">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full text-left px-3 py-2 flex items-center justify-between hover:bg-gray-50 dark:hover:bg-navy-800/50 transition-colors"
      >
        <div className="flex items-center gap-2">
          <BookOpen className="w-3.5 h-3.5 text-gold-500" />
          <span className="text-xs font-medium text-navy-900 dark:text-white">{playbook.title}</span>
          {playbook.aiRecommended && (
            <span className="text-[10px] bg-purple-100 text-purple-600 dark:bg-purple-900/30 dark:text-purple-400 px-1 py-0.5 rounded font-medium">AI</span>
          )}
        </div>
        {expanded ? <ChevronDown className="w-3 h-3 text-gray-400" /> : <ChevronRight className="w-3 h-3 text-gray-400" />}
      </button>
      <AnimatePresence>
        {expanded && (
          <motion.div initial={{ height: 0 }} animate={{ height: "auto" }} exit={{ height: 0 }} className="overflow-hidden">
            <div className="px-3 pb-2 space-y-1.5">
              <p className="text-[10px] text-gray-500 dark:text-gray-400">{playbook.description}</p>
              <div className="space-y-1">
                {playbook.fallbackClauses.map(fb => (
                  <div key={fb.id} className="flex items-center justify-between px-2 py-1 bg-gray-50 dark:bg-navy-800 rounded text-[10px]">
                    <span className="text-navy-900 dark:text-white font-medium truncate flex-1">{fb.title}</span>
                    <div className="flex items-center gap-2 ml-2 flex-shrink-0">
                      <span className={`text-[10px] ${
                        fb.strength === "strong" ? "text-green-600" :
                        fb.strength === "moderate" ? "text-amber-600" : "text-red-600"
                      }`}>
                        {fb.acceptanceRate}%
                      </span>
                      <Play className="w-2.5 h-2.5 text-gray-400" />
                    </div>
                  </div>
                ))}
              </div>
              <div className="flex items-center gap-2 pt-1 text-[10px] text-gray-400">
                <Shield className="w-2.5 h-2.5" />
                <span className="capitalize">{playbook.riskTolerance} risk tolerance</span>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

// ── Left Sidebar (Composite) ─────────────────────────────────────────────

interface LeftSidebarProps {
  issues: NegotiationIssue[];
  clauses: ClauseContent[];
  participants: Participant[];
  playbooks: NegotiationPlaybook[];
  activeClauseId: string | null;
  activeIssueId: string | null;
  redlineCountByClause: Record<string, number>;
  onClauseSelect: (clauseId: string) => void;
  onIssueSelect: (issueId: string) => void;
}

type LeftTab = "issues" | "clauses" | "playbooks" | "participants";

export function LeftSidebar({
  issues, clauses, participants, playbooks, activeClauseId, activeIssueId,
  redlineCountByClause, onClauseSelect, onIssueSelect,
}: LeftSidebarProps) {
  const [activeTab, setActiveTab] = useState<LeftTab>("issues");
  const [searchQuery, setSearchQuery] = useState("");
  const [severityFilter, setSeverityFilter] = useState<string>("all");

  const tabs: { id: LeftTab; label: string; icon: React.ReactNode; count?: number }[] = [
    { id: "issues", label: "Issues", icon: <Flag className="w-3.5 h-3.5" />, count: issues.filter(i => i.status !== "resolved").length },
    { id: "clauses", label: "Clauses", icon: <FileText className="w-3.5 h-3.5" /> },
    { id: "playbooks", label: "Playbooks", icon: <BookOpen className="w-3.5 h-3.5" /> },
    { id: "participants", label: "Team", icon: <User className="w-3.5 h-3.5" />, count: participants.length },
  ];

  const filteredIssues = issues.filter(i => {
    if (severityFilter !== "all" && i.severity !== severityFilter) return false;
    if (searchQuery && !i.title.toLowerCase().includes(searchQuery.toLowerCase())) return false;
    return true;
  });

  const filteredClauses = clauses.filter(c => {
    if (searchQuery && !c.title.toLowerCase().includes(searchQuery.toLowerCase()) && !c.sectionNumber.toLowerCase().includes(searchQuery.toLowerCase())) return false;
    return true;
  });

  return (
    <div className="w-72 flex-shrink-0 bg-white dark:bg-navy-800 border-r border-gray-200 dark:border-navy-700 flex flex-col h-full">
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
            {tab.count !== undefined && tab.count > 0 && (
              <span className={`text-[9px] px-1 py-0.5 rounded-full ${
                activeTab === tab.id ? "bg-gold-100 text-gold-700 dark:bg-gold-900/30 dark:text-gold-400" : "bg-gray-100 text-gray-500 dark:bg-navy-700 dark:text-gray-400"
              }`}>
                {tab.count}
              </span>
            )}
            {activeTab === tab.id && (
              <motion.div layoutId="left-tab-indicator" className="absolute bottom-0 left-0 right-0 h-0.5 bg-gold-500" />
            )}
          </button>
        ))}
      </div>

      {/* Search */}
      <div className="px-2 py-2">
        <div className="relative">
          <Search className="absolute left-2 top-1/2 -translate-y-1/2 w-3 h-3 text-gray-400" />
          <input
            type="text"
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            placeholder={`Search ${activeTab}...`}
            className="w-full pl-7 pr-2 py-1.5 text-[11px] border border-gray-200 dark:border-navy-600 rounded-md bg-gray-50 dark:bg-navy-900 text-navy-900 dark:text-white placeholder-gray-400 focus:outline-none focus:ring-1 focus:ring-gold-400"
          />
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto px-2 pb-2 space-y-0.5">
        {/* Issues Tab */}
        {activeTab === "issues" && (
          <>
            {/* Severity filter */}
            <div className="flex gap-1 pb-1">
              {["all", "blocker", "critical", "major", "minor"].map(s => (
                <button
                  key={s}
                  onClick={() => setSeverityFilter(s)}
                  className={`text-[9px] px-1.5 py-0.5 rounded-full capitalize ${
                    severityFilter === s
                      ? "bg-navy-100 text-navy-700 dark:bg-navy-600 dark:text-white"
                      : "text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
                  }`}
                >
                  {s === "all" ? "All" : s}
                </button>
              ))}
            </div>
            {filteredIssues.length === 0 ? (
              <div className="text-center py-8 text-gray-400">
                <CheckCircle className="w-8 h-8 mx-auto mb-2 opacity-50" />
                <p className="text-xs">No issues found</p>
              </div>
            ) : (
              filteredIssues.map(issue => (
                <IssueItem key={issue.id} issue={issue} isActive={activeIssueId === issue.id} onClick={() => onIssueSelect(issue.id)} />
              ))
            )}
          </>
        )}

        {/* Clauses Tab */}
        {activeTab === "clauses" && (
          filteredClauses.length === 0 ? (
            <div className="text-center py-8 text-gray-400">
              <FileText className="w-8 h-8 mx-auto mb-2 opacity-50" />
              <p className="text-xs">No clauses found</p>
            </div>
          ) : (
            filteredClauses.map(clause => (
              <ClauseNavItem
                key={clause.clauseId}
                clause={clause}
                isActive={activeClauseId === clause.clauseId}
                redlineCount={redlineCountByClause[clause.clauseId] || 0}
                onClick={() => onClauseSelect(clause.clauseId)}
              />
            ))
          )
        )}

        {/* Playbooks Tab */}
        {activeTab === "playbooks" && (
          <div className="space-y-2 pt-1">
            {playbooks.map(pb => (
              <PlaybookCard key={pb.id} playbook={pb} />
            ))}
          </div>
        )}

        {/* Participants Tab */}
        {activeTab === "participants" && (
          <div className="space-y-0.5 pt-1">
            {participants.map(p => (
              <ParticipantBadge key={p.id} participant={p} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

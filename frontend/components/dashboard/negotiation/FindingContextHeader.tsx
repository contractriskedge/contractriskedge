"use client";

import React from "react";
import {
  FileText, AlertTriangle, User, Hash, CheckCircle,
  ArrowUpCircle, XCircle, Clock, HelpCircle,
} from "lucide-react";

interface FindingContextHeaderProps {
  contractTitle: string;
  counterparty: string;
  findingIndex: number;
  totalFindings: number;
  clauseTitle?: string;
  riskLevel?: string;
  status?: string;
  assignedTo?: string;
}

export function FindingContextHeader({
  contractTitle, counterparty, findingIndex, totalFindings,
  clauseTitle, riskLevel, status, assignedTo,
}: FindingContextHeaderProps) {
  const riskColor = riskLevel === "critical" ? "bg-red-100 text-red-700 border-red-200" :
    riskLevel === "high" ? "bg-orange-100 text-orange-700 border-orange-200" :
    riskLevel === "medium" ? "bg-yellow-100 text-yellow-700 border-yellow-200" :
    "bg-green-100 text-green-700 border-green-200";

  const statusIcon = status === "resolved" || status === "accepted" ? <CheckCircle className="w-3 h-3" /> :
    status === "escalated" ? <ArrowUpCircle className="w-3 h-3" /> :
    status === "rejected" ? <XCircle className="w-3 h-3" /> :
    status === "in_review" ? <Clock className="w-3 h-3" /> :
    <HelpCircle className="w-3 h-3" />;

  const statusColor = status === "resolved" || status === "accepted" ? "text-green-600 bg-green-50 border-green-200" :
    status === "escalated" ? "text-red-600 bg-red-50 border-red-200" :
    status === "rejected" ? "text-gray-500 bg-gray-50 border-gray-200" :
    status === "in_review" ? "text-blue-600 bg-blue-50 border-blue-200" :
    "text-amber-600 bg-amber-50 border-amber-200";

  return (
    <div className="bg-white dark:bg-navy-800 border-b border-gray-200 dark:border-navy-700">
      <div className="flex items-center gap-3 px-3 py-1.5 text-[10px]">
        {/* Contract Info */}
        <div className="flex items-center gap-1.5 min-w-0">
          <FileText className="w-3 h-3 text-gold-500 flex-shrink-0" />
          <span className="font-medium text-navy-900 dark:text-white truncate max-w-[180px]" title={contractTitle}>
            {contractTitle}
          </span>
          {counterparty && (
            <span className="text-gray-400 truncate max-w-[100px]">— {counterparty}</span>
          )}
        </div>

        <div className="h-3 w-px bg-gray-200 dark:bg-navy-600" />

        {/* Finding Counter */}
        <div className="flex items-center gap-1 text-gray-600 dark:text-gray-300">
          <Hash className="w-3 h-3 text-gray-400" />
          <span>
            Finding <span className="font-semibold text-navy-900 dark:text-white">{findingIndex + 1}</span>
            <span className="text-gray-400"> / {totalFindings}</span>
          </span>
        </div>

        <div className="h-3 w-px bg-gray-200 dark:bg-navy-600" />

        {/* Clause */}
        {clauseTitle && (
          <>
            <div className="flex items-center gap-1 text-gray-600 dark:text-gray-300 min-w-0">
              <FileText className="w-3 h-3 text-gray-400 flex-shrink-0" />
              <span className="truncate max-w-[160px]" title={clauseTitle}>{clauseTitle}</span>
            </div>
            <div className="h-3 w-px bg-gray-200 dark:bg-navy-600" />
          </>
        )}

        {/* Risk Level */}
        {riskLevel && (
          <span className={`px-1.5 py-0.5 rounded-full text-[9px] font-semibold border ${riskColor}`}>
            {riskLevel.toUpperCase()}
          </span>
        )}

        {/* Status */}
        {status && (
          <span className={`flex items-center gap-0.5 px-1.5 py-0.5 rounded-full text-[9px] font-medium border ${statusColor}`}>
            {statusIcon}
            <span className="capitalize">{status.replace(/_/g, " ")}</span>
          </span>
        )}

        {/* Assigned To */}
        {assignedTo && (
          <>
            <div className="h-3 w-px bg-gray-200 dark:bg-navy-600" />
            <div className="flex items-center gap-1 text-gray-500">
              <User className="w-3 h-3" />
              <span>{assignedTo}</span>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

"use client";

import React, { useState } from "react";
import { motion } from "framer-motion";
import { Search, ZoomIn, ZoomOut, Maximize2, FileText, AlertTriangle, MessageSquare, CheckCircle, XCircle, ChevronDown, ChevronUp, Lightbulb } from "lucide-react";
import type { ClauseData, AnnotationType } from "./types";
import { RISK_BG, RISK_TEXT, RISK_BG_LIGHT } from "./types";

interface DocumentViewerProps {
  clauses: ClauseData[];
  selectedClauseId: string | null;
  showRedlines: boolean;
  onShowRedlinesChange: (v: boolean) => void;
  onSelectClause: (id: string) => void;
}

export function DocumentViewer({ clauses, selectedClauseId, showRedlines, onShowRedlinesChange, onSelectClause }: DocumentViewerProps) {
  const [zoom, setZoom] = useState(100);
  const [searchQuery, setSearchQuery] = useState("");
  const [showAnnotations, setShowAnnotations] = useState(true);

  return (
    <div className="flex flex-col h-full bg-white">
      {/* Toolbar */}
      <div className="flex items-center justify-between px-4 py-2 border-b border-gray-200 bg-gray-50">
        <div className="flex items-center gap-1.5">
          <button onClick={() => setZoom(Math.max(50, zoom - 10))} className="p-1 rounded hover:bg-gray-200 text-gray-500"><ZoomOut className="w-3.5 h-3.5" /></button>
          <span className="text-[10px] text-gray-500 w-8 text-center tabular-nums">{zoom}%</span>
          <button onClick={() => setZoom(Math.min(200, zoom + 10))} className="p-1 rounded hover:bg-gray-200 text-gray-500"><ZoomIn className="w-3.5 h-3.5" /></button>
          <div className="w-px h-4 bg-gray-200 mx-1" />
          <div className="relative w-36"><Search className="absolute left-2 top-1/2 -translate-y-1/2 w-3 h-3 text-gray-400" />
            <input value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)} placeholder="Search in contract..." className="w-full text-[10px] border border-gray-200 rounded-md pl-6 pr-2 py-1 focus:border-navy-400 focus:ring-1 focus:ring-navy-400" /></div>
        </div>
        <div className="flex items-center gap-1.5">
          <button onClick={() => setShowAnnotations(!showAnnotations)} className={`text-[10px] font-medium px-2 py-1 rounded-md transition-colors ${showAnnotations ? "bg-navy-100 text-navy-700" : "text-gray-500 hover:bg-gray-100"}`}>Annotations</button>
          <button onClick={() => onShowRedlinesChange(!showRedlines)} className={`text-[10px] font-medium px-2 py-1 rounded-md transition-colors ${showRedlines ? "bg-green-100 text-green-700" : "text-gray-500 hover:bg-gray-100"}`}>Redlines</button>
          <button className="p-1 rounded hover:bg-gray-200 text-gray-500"><Maximize2 className="w-3.5 h-3.5" /></button>
        </div>
      </div>

      {/* Document content */}
      <div className="flex-1 overflow-y-auto p-6 bg-gray-50">
        <div className="max-w-[800px] mx-auto bg-white rounded-xl border border-gray-200 shadow-sm p-8" style={{ zoom: `${zoom}%` }}>
          {/* Header */}
          <div className="text-center mb-6 pb-6 border-b border-gray-200">
            <h1 className="text-lg font-bold text-navy-900">MASTER SERVICE AGREEMENT</h1>
            <p className="text-xs text-gray-500 mt-1">by and between</p>
            <p className="text-sm font-semibold text-navy-800 mt-1">Customer Company Inc.</p>
            <p className="text-xs text-gray-400">and</p>
            <p className="text-sm font-semibold text-navy-800">SecureNet Solutions LLC</p>
            <p className="text-xs text-gray-400 mt-2">Effective Date: January 15, 2026</p>
          </div>

          {/* Clauses */}
          {clauses.map((clause) => {
            const isSelected = selectedClauseId === clause.id;
            const hasHighRisk = clause.riskLevel === "critical" || clause.riskLevel === "high";
            const hasComments = clause.comments.filter((c) => !c.resolved).length > 0;
            const showHighlight = hasHighRisk && showAnnotations;

            return (
              <motion.div
                key={clause.id}
                id={`clause-${clause.id}`}
                layout
                onClick={() => onSelectClause(clause.id)}
                className={`relative mb-4 p-4 rounded-lg border-2 cursor-pointer transition-all ${
                  isSelected ? "border-navy-400 bg-navy-50/30 shadow-sm" :
                  showHighlight ? "border-red-200 bg-red-50/30" : "border-gray-100 hover:border-gray-200"
                }`}
              >
                {/* Clause header */}
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] font-medium text-gray-400">Section {clause.section}</span>
                    <h3 className="text-xs font-semibold text-navy-900">{clause.title}</h3>
                    <span className={`text-[9px] font-medium px-1.5 py-0.5 rounded-full ${RISK_BG_LIGHT[clause.riskLevel]} ${RISK_TEXT[clause.riskLevel]}`}>{clause.riskScore}/10</span>
                  </div>
                  <div className="flex items-center gap-1">
                    {hasComments && <MessageSquare className="w-3 h-3 text-navy-500" />}
                    {clause.isRedlined && showRedlines && <span className="text-[9px] font-medium px-1.5 py-0.5 rounded-full bg-green-50 text-green-700">Redlined</span>}
                    {hasHighRisk && showAnnotations && <AlertTriangle className="w-3 h-3 text-red-500" />}
                  </div>
                </div>

                {/* Clause text */}
                <div className="relative">
                  {clause.isRedlined && showRedlines ? (
                    <div className="space-y-2">
                      <div className="p-2.5 bg-red-50 border border-red-100 rounded text-[11px] text-gray-600 leading-relaxed">
                        <p className="text-[9px] font-semibold text-red-600 uppercase mb-1">Original</p>
                        <span className="line-through decoration-red-400 decoration-2">{clause.text}</span>
                      </div>
                      <div className="p-2.5 bg-green-50 border border-green-100 rounded text-[11px] text-gray-700 leading-relaxed">
                        <p className="text-[9px] font-semibold text-green-600 uppercase mb-1">Proposed</p>
                        {clause.redlinedText}
                      </div>
                    </div>
                  ) : (
                    <p className="text-[11px] text-gray-700 leading-relaxed">{clause.text}</p>
                  )}
                </div>

                {/* AI annotation */}
                {hasHighRisk && showAnnotations && (
                  <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: "auto" }}
                    className="mt-2 p-2 bg-red-50 border border-red-100 rounded text-[10px] text-gray-600 leading-relaxed">
                    <div className="flex items-start gap-1.5">
                      <Lightbulb className="w-3 h-3 text-red-500 mt-0.5 flex-shrink-0" />
                      <span>{clause.aiExplanation}</span>
                    </div>
                  </motion.div>
                )}

                {/* Inline comments */}
                {clause.comments.filter((c) => !c.resolved).map((comment) => (
                  <div key={comment.id} className="mt-2 p-2 bg-navy-50 border border-navy-100 rounded text-[10px]">
                    <div className="flex items-center gap-1 mb-0.5">
                      <MessageSquare className="w-3 h-3 text-navy-500" />
                      <span className="font-medium text-navy-700">{comment.author}</span>
                      <span className="text-gray-400 ml-auto">{formatTime(comment.createdAt)}</span>
                    </div>
                    <p className="text-gray-600">{comment.body}</p>
                  </div>
                ))}
              </motion.div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

function formatTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const hrs = Math.floor(diff / 3600000);
  if (hrs < 1) return "just now"; if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

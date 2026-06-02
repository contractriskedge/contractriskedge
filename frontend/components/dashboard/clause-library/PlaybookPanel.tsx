"use client";

import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { BookOpen, ChevronRight, CheckCircle, AlertTriangle, FileText, User, Clock, TrendingUp, X, Shield, Sparkles } from "lucide-react";
import type { Playbook } from "./types";

export function PlaybookPanel({ playbooks }: { playbooks: Playbook[] }) {
  const [expanded, setExpanded] = useState<string | null>(null);
  const [viewingPlaybook, setViewingPlaybook] = useState<Playbook | null>(null);

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2"><BookOpen className="w-4.5 h-4.5 text-navy-700" /><h2 className="text-sm font-semibold text-navy-900">Negotiation Playbooks</h2></div>
      <div className="space-y-2">
        {playbooks.map((pb) => {
          const isExpanded = expanded === pb.id;
          return (
            <motion.div key={pb.id} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
              className="bg-white border border-gray-200 rounded-lg shadow-sm hover:shadow-md transition-all">
              <button onClick={() => setExpanded(isExpanded ? null : pb.id)} className="w-full text-left p-3 flex items-start gap-2.5">
                <div className="w-8 h-8 rounded-lg bg-navy-50 flex items-center justify-center flex-shrink-0 mt-0.5">
                  <BookOpen className="w-4 h-4 text-navy-600" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between mb-0.5">
                    <h4 className="text-xs font-semibold text-navy-900">{pb.name}</h4>
                    <div className="flex items-center gap-1.5">
                      <span className="text-[9px] font-medium text-green-600 bg-green-50 px-1.5 py-0.5 rounded">{pb.successRate}% success</span>
                      <span className="text-[9px] text-gray-400">{pb.usageCount} uses</span>
                    </div>
                  </div>
                  <p className="text-[10px] text-gray-500">{pb.description}</p>
                  <div className="flex items-center gap-2 mt-1 text-[9px] text-gray-400">
                    <span>{pb.jurisdiction}</span><span>•</span><span>{pb.contractTypes.join(", ")}</span><span>•</span><span>{pb.owner}</span>
                  </div>
                  {isExpanded && (
                    <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }} className="mt-2 space-y-2 overflow-hidden">
                      <div className="p-2 bg-navy-50 rounded border border-navy-100">
                        <p className="text-[9px] font-semibold text-navy-700 uppercase mb-1">Automation Rules</p>
                        {pb.rules.map((r) => (
                          <div key={r.id} className="flex items-center gap-1.5 text-[10px] text-gray-600 py-0.5">
                            <span className={`w-1.5 h-1.5 rounded-full ${r.enabled ? "bg-green-500" : "bg-gray-300"}`} />
                            <span className="font-medium">{r.condition}</span>
                            <span>→</span>
                            <span>{r.action}</span>
                          </div>
                        ))}
                      </div>
                      <div className="flex gap-1">
                        <button
                          onClick={() => setViewingPlaybook(pb)}
                          className="text-[9px] font-medium px-2 py-1 rounded-md bg-navy-700 text-white hover:bg-navy-800 transition-colors"
                        >
                          View Playbook
                        </button>
                        <button className="text-[9px] font-medium px-2 py-1 rounded-md bg-white border border-gray-200 text-gray-600 hover:bg-gray-50 transition-colors">Edit Rules</button>
                      </div>
                    </motion.div>
                  )}
                </div>
                <ChevronRight className={`w-4 h-4 text-gray-300 flex-shrink-0 mt-1 transition-transform ${isExpanded ? "rotate-90" : ""}`} />
              </button>
            </motion.div>
          );
        })}
      </div>

      {/* Playbook Detail Modal */}
      <AnimatePresence>
        {viewingPlaybook && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 bg-black/30 z-50"
              onClick={() => setViewingPlaybook(null)}
            />
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="fixed inset-0 z-50 flex items-center justify-center p-4"
            >
              <div className="bg-white rounded-xl shadow-2xl border border-gray-200 w-full max-w-lg max-h-[80vh] overflow-y-auto">
                <div className="flex items-center justify-between px-5 py-4 border-b border-gray-200">
                  <div className="flex items-center gap-2">
                    <BookOpen className="w-4 h-4 text-gold-500" />
                    <h3 className="text-sm font-semibold text-navy-900">{viewingPlaybook.name}</h3>
                  </div>
                  <button onClick={() => setViewingPlaybook(null)} className="p-1 rounded hover:bg-gray-100 text-gray-400">
                    <X className="w-4 h-4" />
                  </button>
                </div>
                <div className="p-5 space-y-4">
                  <p className="text-xs text-gray-600">{viewingPlaybook.description}</p>

                  <div className="grid grid-cols-3 gap-2">
                    <div className="p-2 bg-green-50 rounded-lg text-center">
                      <p className="text-lg font-bold text-green-600">{viewingPlaybook.successRate}%</p>
                      <p className="text-[9px] text-gray-500">Success Rate</p>
                    </div>
                    <div className="p-2 bg-blue-50 rounded-lg text-center">
                      <p className="text-lg font-bold text-blue-600">{viewingPlaybook.usageCount}</p>
                      <p className="text-[9px] text-gray-500">Total Uses</p>
                    </div>
                    <div className="p-2 bg-purple-50 rounded-lg text-center">
                      <p className="text-lg font-bold text-purple-600">{viewingPlaybook.rules.length}</p>
                      <p className="text-[9px] text-gray-500">Active Rules</p>
                    </div>
                  </div>

                  <div>
                    <p className="text-[10px] font-semibold text-gray-500 uppercase mb-2">Rules & Conditions</p>
                    <div className="space-y-1.5">
                      {viewingPlaybook.rules.map(r => (
                        <div key={r.id} className="flex items-start gap-2 p-2 bg-gray-50 rounded-lg border border-gray-100">
                          <div className={`w-1.5 h-1.5 rounded-full mt-1 flex-shrink-0 ${r.enabled ? "bg-green-500" : "bg-gray-300"}`} />
                          <div className="flex-1">
                            <div className="flex items-center gap-1.5">
                              <span className="text-[10px] font-medium text-navy-900">{r.condition}</span>
                              <span className="text-[9px] text-gray-400">→</span>
                              <span className="text-[10px] text-gray-600">{r.action}</span>
                            </div>
                            <div className="flex items-center gap-2 mt-0.5 text-[8px] text-gray-400">
                              <span>Priority: P{r.priority}</span>
                              <span className={`px-1 py-0.5 rounded ${r.enabled ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-500"}`}>
                                {r.enabled ? "Enabled" : "Disabled"}
                              </span>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>

                  <div className="flex items-center gap-2 text-[9px] text-gray-400 pt-2 border-t border-gray-100">
                    <Shield className="w-3 h-3" />
                    <span>{viewingPlaybook.jurisdiction}</span>
                    <span>•</span>
                    <span>{viewingPlaybook.contractTypes.join(", ")}</span>
                    <span>•</span>
                    <span>{viewingPlaybook.owner}</span>
                  </div>
                </div>
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </div>
  );
}

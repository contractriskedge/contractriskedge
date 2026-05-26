"use client";

import React, { useState } from "react";
import { motion } from "framer-motion";
import { BookOpen, ChevronRight, CheckCircle, AlertTriangle, FileText, User, Clock, TrendingUp } from "lucide-react";
import type { Playbook } from "./types";

export function PlaybookPanel({ playbooks }: { playbooks: Playbook[] }) {
  const [expanded, setExpanded] = useState<string | null>(null);

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
                        <button className="text-[9px] font-medium px-2 py-1 rounded-md bg-navy-700 text-white hover:bg-navy-800 transition-colors">View Playbook</button>
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
    </div>
  );
}

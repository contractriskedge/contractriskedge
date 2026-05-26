"use client";

import React, { useState } from "react";
import { motion } from "framer-motion";
import { FileText, Download, Calendar, Clock, BarChart3, CheckCircle, ChevronRight } from "lucide-react";
import type { ReportTemplate } from "./types";

export function ReportBuilder({ templates }: { templates: ReportTemplate[] }) {
  const [selected, setSelected] = useState<string | null>(null);

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2"><BarChart3 className="w-4.5 h-4.5 text-navy-700" /><h2 className="text-sm font-semibold text-navy-900">Report Builder</h2></div>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
        {templates.map((rt) => {
          const isSelected = selected === rt.id;
          return (
            <motion.div key={rt.id} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
              onClick={() => setSelected(isSelected ? null : rt.id)}
              className={`p-3 rounded-lg border-2 cursor-pointer transition-all ${
                isSelected ? "border-navy-400 bg-navy-50" : "border-gray-200 bg-white hover:border-gray-300"
              }`}>
              <div className="flex items-center justify-between mb-1.5">
                <div className="flex items-center gap-2">
                  <div className="w-7 h-7 rounded-lg bg-navy-50 flex items-center justify-center"><FileText className="w-3.5 h-3.5 text-navy-600" /></div>
                  <div>
                    <h4 className="text-[11px] font-semibold text-navy-900">{rt.name}</h4>
                    <span className="text-[9px] text-gray-400">{rt.category}</span>
                  </div>
                </div>
                {isSelected && <CheckCircle className="w-4 h-4 text-navy-600" />}
              </div>
              <p className="text-[10px] text-gray-500 line-clamp-1">{rt.description}</p>
              <div className="flex items-center gap-2 mt-1.5 text-[9px] text-gray-400">
                <Clock className="w-3 h-3" /><span>{rt.lastGenerated}</span>
                <span className="text-navy-500 font-medium">{rt.format}</span>
              </div>
              {isSelected && (
                <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }} className="mt-2 space-y-1.5 overflow-hidden">
                  <div className="flex gap-1 flex-wrap">{rt.charts.map((c) => (
                    <span key={c} className="text-[8px] px-1.5 py-0.5 rounded bg-gray-100 text-gray-600">{c}</span>
                  ))}</div>
                  <div className="flex gap-1.5">
                    <button className="text-[9px] font-medium px-2 py-1 rounded-md bg-navy-700 text-white hover:bg-navy-800 transition-colors flex items-center gap-0.5">
                      <Download className="w-3 h-3" /> Generate
                    </button>
                    <button className="text-[9px] font-medium px-2 py-1 rounded-md bg-white border border-gray-200 text-gray-600 hover:bg-gray-50 transition-colors">
                      Schedule
                    </button>
                    <button className="text-[9px] font-medium px-2 py-1 rounded-md bg-white border border-gray-200 text-gray-600 hover:bg-gray-50 transition-colors">
                      Customize
                    </button>
                  </div>
                </motion.div>
              )}
            </motion.div>
          );
        })}
      </div>
    </div>
  );
}

"use client";

import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Download, BarChart3, FileText, ChevronDown, Eye, SlidersHorizontal,
  TrendingUp, DollarSign, RefreshCw, Presentation,
} from "lucide-react";

interface CfoToolbarProps {
  onExport: () => void;
  onPresentationMode: () => void;
  onForecastScenario: () => void;
}

export function CfoToolbar({ onExport, onPresentationMode, onForecastScenario }: CfoToolbarProps) {
  return (
    <div className="bg-white dark:bg-navy-800 border-b border-gray-200 dark:border-navy-700">
      <div className="flex items-center justify-between px-3 py-1.5">
        <div className="flex items-center gap-1.5">
          <h3 className="text-xs font-semibold text-navy-900 dark:text-white mr-2">CFO Risk & Exposure Dashboard</h3>
          <div className="w-px h-4 bg-gray-200 dark:bg-navy-600" />
          <button onClick={onForecastScenario} className="flex items-center gap-1 px-2.5 py-1.5 bg-gold-500 hover:bg-gold-600 text-white rounded-lg text-[10px] font-medium transition-colors">
            <TrendingUp className="w-3 h-3" /> Forecast Scenarios
          </button>
          <button onClick={onPresentationMode} className="flex items-center gap-1 px-2.5 py-1.5 border border-gray-200 dark:border-navy-600 hover:bg-gray-50 dark:hover:bg-navy-700 rounded-lg text-[10px] font-medium text-gray-600 dark:text-gray-300 transition-colors">
            <Presentation className="w-3 h-3" /> Board View
          </button>
          <div className="w-px h-4 bg-gray-200 dark:bg-navy-600 mx-1" />
          <button onClick={onExport} className="flex items-center gap-1 px-2.5 py-1.5 text-gray-500 hover:text-navy-700 dark:hover:text-gray-300 hover:bg-gray-50 dark:hover:bg-navy-700 rounded-lg text-[10px] font-medium transition-colors">
            <Download className="w-3 h-3" /> Export Report
          </button>
        </div>

        {/* Summary Badge */}
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1.5 px-2.5 py-1 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-900/50 rounded-lg">
            <DollarSign className="w-3 h-3 text-blue-600" />
            <span className="text-[10px] text-blue-700 dark:text-blue-300 font-medium">Portfolio: <strong>$847.2M</strong></span>
          </div>
          <div className="flex items-center gap-1.5 px-2.5 py-1 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-900/50 rounded-lg">
            <TrendingUp className="w-3 h-3 text-red-600" />
            <span className="text-[10px] text-red-700 dark:text-red-300 font-medium">At Risk: <strong>$124.8M</strong></span>
          </div>
        </div>
      </div>
    </div>
  );
}

"use client";

import React from "react";
import { FileText, AlertTriangle, XCircle, Lock, Shield, CheckCircle, DollarSign, Lightbulb, Cloud, Activity, Scale, Star, BookOpen, Search, Heart } from "lucide-react";
import type { ClauseCategory } from "./types";

const iconMap: Record<string, React.ReactNode> = {
  Shield: <Shield className="w-3.5 h-3.5" />, AlertTriangle: <AlertTriangle className="w-3.5 h-3.5" />,
  XCircle: <XCircle className="w-3.5 h-3.5" />, Lock: <Lock className="w-3.5 h-3.5" />,
  CheckCircle: <CheckCircle className="w-3.5 h-3.5" />, DollarSign: <DollarSign className="w-3.5 h-3.5" />,
  Lightbulb: <Lightbulb className="w-3.5 h-3.5" />, Cloud: <Cloud className="w-3.5 h-3.5" />,
  Activity: <Activity className="w-3.5 h-3.5" />, Scale: <Scale className="w-3.5 h-3.5" />,
};

interface ClauseSidebarProps {
  categories: ClauseCategory[];
  selectedCategory: string | null;
  onSelectCategory: (id: string | null) => void;
  showFavorites: boolean;
  onToggleFavorites: () => void;
}

export function ClauseSidebar({ categories, selectedCategory, onSelectCategory, showFavorites, onToggleFavorites }: ClauseSidebarProps) {
  return (
    <div className="flex flex-col h-full bg-white border-r border-gray-200">
      <div className="px-3 py-2.5 border-b border-gray-100">
        <div className="flex items-center gap-2"><BookOpen className="w-4 h-4 text-navy-700" /><h3 className="text-xs font-semibold text-navy-900">Clause Library</h3></div>
      </div>

      <div className="px-3 py-2 border-b border-gray-100">
        <button onClick={() => onSelectCategory(null)}
          className={`w-full text-left px-2.5 py-1.5 rounded-lg text-[11px] font-medium transition-colors ${!selectedCategory ? "bg-navy-100 text-navy-900" : "text-gray-600 hover:bg-gray-50"}`}>
          <FileText className="w-3.5 h-3.5 inline mr-1.5" />All Clauses
        </button>
        <button onClick={onToggleFavorites}
          className={`w-full text-left px-2.5 py-1.5 rounded-lg text-[11px] font-medium transition-colors ${showFavorites ? "bg-navy-100 text-navy-900" : "text-gray-600 hover:bg-gray-50"}`}>
          <Heart className={`w-3.5 h-3.5 inline mr-1.5 ${showFavorites ? "text-red-400 fill-red-400" : ""}`} />Favorites
        </button>
      </div>

      <div className="px-3 py-2">
        <p className="text-[9px] font-semibold text-gray-400 uppercase tracking-wider mb-1.5">Categories</p>
        <div className="space-y-0.5">
          {categories.map((cat) => (
            <button key={cat.id} onClick={() => onSelectCategory(cat.id)}
              className={`w-full flex items-center justify-between px-2.5 py-1.5 rounded-lg text-[11px] transition-colors ${
                selectedCategory === cat.id ? "bg-navy-100 text-navy-900 font-medium" : "text-gray-600 hover:bg-gray-50"
              }`}>
              <span className="flex items-center gap-1.5">
                {iconMap[cat.icon] || <FileText className="w-3.5 h-3.5" />}
                {cat.name}
              </span>
              <span className="text-[10px] text-gray-400">{cat.count}</span>
            </button>
          ))}
        </div>
      </div>

      <div className="mt-auto px-3 py-3 border-t border-gray-100">
        <div className="p-2.5 bg-navy-50 rounded-lg border border-navy-100">
          <p className="text-[10px] font-semibold text-navy-700">AI Knowledge Base</p>
          <p className="text-[9px] text-gray-500 mt-0.5">156 approved clauses • 10 jurisdictions</p>
        </div>
      </div>
    </div>
  );
}

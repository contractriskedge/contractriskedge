"use client";

import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  DollarSign, AlertTriangle, Gavel, RefreshCw, Building2,
  TrendingDown, Clock, PiggyBank, ChevronRight, Search,
  TrendingUp, FileText, BarChart3, Shield,
} from "lucide-react";
import type { FinancialExposure, RenewalForecast, VendorFinancialRisk } from "./types";

// ── Exposure Item ────────────────────────────────────────────────────────

const exposureIcons: Record<string, React.ReactNode> = {
  liability: <Gavel className="w-3 h-3" />, renewal: <RefreshCw className="w-3 h-3" />,
  vendor: <Building2 className="w-3 h-3" />, operational: <Clock className="w-3 h-3" />,
  revenue: <TrendingDown className="w-3 h-3" />, compliance: <Shield className="w-3 h-3" />,
};

function ExposureItem({ exp, isActive, onClick }: { exp: FinancialExposure; isActive: boolean; onClick: () => void }) {
  return (
    <button onClick={onClick} className={`w-full text-left px-2 py-1.5 rounded-lg flex items-center gap-2 transition-colors ${
      isActive ? "bg-navy-50 dark:bg-navy-700/50 border border-navy-200 dark:border-navy-600" : "hover:bg-gray-50 dark:hover:bg-navy-800/50 border border-transparent"
    }`}>
      <div className={`w-6 h-6 rounded-lg flex items-center justify-center flex-shrink-0 ${
        exp.riskLevel === "critical" ? "bg-red-100 text-red-600" : exp.riskLevel === "warning" ? "bg-amber-100 text-amber-600" : "bg-blue-100 text-blue-600"
      }`}>{exposureIcons[exp.category] || <DollarSign className="w-3 h-3" />}</div>
      <div className="flex-1 min-w-0">
        <span className="text-[10px] font-medium text-navy-900 dark:text-white truncate block">{exp.label}</span>
        <span className="text-[8px] text-gray-400">${(exp.currentExposure / 1000000).toFixed(1)}M · {exp.contractCount} contracts</span>
      </div>
      <span className={`text-[9px] font-bold tabular-nums ${
        exp.riskLevel === "critical" ? "text-red-600" : exp.riskLevel === "warning" ? "text-amber-600" : "text-blue-600"
      }`}>${(exp.currentExposure / 1000000).toFixed(1)}M</span>
    </button>
  );
}

// ── Renewal Item ─────────────────────────────────────────────────────────

function RenewalItem({ forecast }: { forecast: RenewalForecast }) {
  return (
    <div className="px-2 py-1.5 hover:bg-gray-50 dark:hover:bg-navy-700 rounded-lg transition-colors">
      <div className="flex items-center justify-between">
        <span className="text-[9px] font-medium text-navy-900 dark:text-white truncate flex-1">{forecast.vendor}</span>
        <span className={`text-[8px] px-1 py-0.5 rounded font-medium ${
          forecast.probability >= 80 ? "bg-green-100 text-green-600" : forecast.probability >= 60 ? "bg-amber-100 text-amber-600" : "bg-red-100 text-red-600"
        }`}>{forecast.probability}%</span>
      </div>
      <div className="flex items-center gap-1.5 text-[7px] text-gray-400 mt-0.5">
        <span>${(forecast.currentValue / 1000000).toFixed(1)}M</span>
        <span>→</span>
        <span>${(forecast.projectedValue / 1000000).toFixed(1)}M</span>
        <span>·</span>
        <span>{new Date(forecast.renewalDate).toLocaleDateString("en-US", { month: "short", day: "numeric" })}</span>
      </div>
    </div>
  );
}

// ── Vendor Risk Item ─────────────────────────────────────────────────────

function VendorRiskItem({ vendor }: { vendor: VendorFinancialRisk }) {
  return (
    <div className="px-2 py-1.5 hover:bg-gray-50 dark:hover:bg-navy-700 rounded-lg transition-colors">
      <div className="flex items-center justify-between">
        <span className="text-[9px] font-medium text-navy-900 dark:text-white truncate flex-1">{vendor.vendorName}</span>
        <span className={`text-[8px] font-bold tabular-nums ${
          vendor.riskScore >= 70 ? "text-red-600" : vendor.riskScore >= 50 ? "text-amber-600" : "text-green-600"
        }`}>{vendor.riskScore}</span>
      </div>
      <div className="flex items-center gap-1 text-[7px] text-gray-400 mt-0.5">
        <span>${(vendor.totalSpend / 1000000).toFixed(1)}M spend</span>
        <span>·</span>
        <span>{vendor.concentration.toFixed(1)}% conc.</span>
        <span>·</span>
        <span>{vendor.contractCount} contracts</span>
      </div>
    </div>
  );
}

// ── Left Sidebar ─────────────────────────────────────────────────────────

interface CfoLeftSidebarProps {
  exposures: FinancialExposure[];
  renewals: RenewalForecast[];
  vendorRisks: VendorFinancialRisk[];
  activeExposure: string | null;
  onExposureSelect: (id: string) => void;
}

type LeftTab = "exposure" | "renewals" | "vendors";

export function CfoLeftSidebar({
  exposures, renewals, vendorRisks, activeExposure, onExposureSelect,
}: CfoLeftSidebarProps) {
  const [activeTab, setActiveTab] = useState<LeftTab>("exposure");

  const tabs: { id: LeftTab; label: string; icon: React.ReactNode; count?: number }[] = [
    { id: "exposure", label: "Exposure", icon: <AlertTriangle className="w-3 h-3" />, count: exposures.filter(e => e.riskLevel === "critical" || e.riskLevel === "warning").length },
    { id: "renewals", label: "Renewals", icon: <RefreshCw className="w-3 h-3" />, count: renewals.filter(r => r.riskLevel === "critical" || r.riskLevel === "high").length },
    { id: "vendors", label: "Vendors", icon: <Building2 className="w-3 h-3" />, count: vendorRisks.filter(v => v.riskLevel === "critical" || v.riskLevel === "high").length },
  ];

  return (
    <div className="w-60 flex-shrink-0 bg-white dark:bg-navy-800 border-r border-gray-200 dark:border-navy-700 flex flex-col h-full">
      <div className="flex border-b border-gray-200 dark:border-navy-700">
        {tabs.map(tab => (
          <button key={tab.id} onClick={() => setActiveTab(tab.id)}
            className={`flex-1 flex items-center justify-center gap-1 py-2 text-[8px] font-medium transition-colors relative ${
              activeTab === tab.id ? "text-gold-600 dark:text-gold-400" : "text-gray-500 dark:text-gray-400 hover:text-navy-700"
            }`}>
            {tab.icon}<span>{tab.label}</span>
            {tab.count !== undefined && tab.count > 0 && (
              <span className={`text-[7px] px-1 py-0.5 rounded-full ${activeTab === tab.id ? "bg-gold-100 text-gold-700" : "bg-gray-100 text-gray-500"}`}>{tab.count}</span>
            )}
            {activeTab === tab.id && <motion.div layoutId="cfo-left-tab" className="absolute bottom-0 left-0 right-0 h-0.5 bg-gold-500" />}
          </button>
        ))}
      </div>
      <div className="flex-1 overflow-y-auto p-1.5 space-y-0.5">
        {activeTab === "exposure" && exposures.map(e => (
          <ExposureItem key={e.id} exp={e} isActive={activeExposure === e.id} onClick={() => onExposureSelect(e.id)} />
        ))}
        {activeTab === "renewals" && renewals.map(r => <RenewalItem key={r.id} forecast={r} />)}
        {activeTab === "vendors" && vendorRisks.map(v => <VendorRiskItem key={v.id} vendor={v} />)}
      </div>
    </div>
  );
}

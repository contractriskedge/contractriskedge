"use client";

import React, { useState } from "react";
import { motion } from "framer-motion";
import {
  BarChart3, TrendingUp, DollarSign, AlertTriangle, Building2,
  Search, Filter, ChevronDown, Eye, MoreHorizontal,
} from "lucide-react";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  AreaChart, Area, LineChart, Line, PieChart, Pie, Cell, Legend,
} from "recharts";
import type { FinancialAnalytics, FinancialExposure } from "./types";

// ── Exposure Waterfall Chart ─────────────────────────────────────────────

function ExposureWaterfall({ analytics }: { analytics: FinancialAnalytics }) {
  return (
    <div className="bg-white dark:bg-navy-800 border border-gray-200 dark:border-navy-600 rounded-lg p-3">
      <h4 className="text-[10px] font-semibold text-gray-500 uppercase tracking-wider mb-2">Exposure by Category</h4>
      <ResponsiveContainer width="100%" height={160}>
        <BarChart data={analytics.exposureByCategory} margin={{ top: 5, right: 5, left: -10, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" />
          <XAxis dataKey="category" tick={{ fontSize: 8 }} tickLine={false} />
          <YAxis tick={{ fontSize: 8 }} tickFormatter={(v) => `$${v / 1000000}M`} tickLine={false} />
          <Tooltip contentStyle={{ fontSize: 10, borderRadius: 8 }} formatter={(v: any) => [`$${(Number(v) / 1000000).toFixed(1)}M`, "Exposure"]} />
          <Bar dataKey="amount" radius={[4, 4, 0, 0]}>
            {analytics.exposureByCategory.map((entry, i) => (
              <Cell key={i} fill={["#EF4444", "#F97316", "#F59E0B", "#22C55E", "#EF4444", "#8B5CF6"][i]} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

// ── Exposure Trend Chart ─────────────────────────────────────────────────

function ExposureTrendChart({ analytics }: { analytics: FinancialAnalytics }) {
  return (
    <div className="bg-white dark:bg-navy-800 border border-gray-200 dark:border-navy-600 rounded-lg p-3">
      <h4 className="text-[10px] font-semibold text-gray-500 uppercase tracking-wider mb-2">Exposure Trend ($M)</h4>
      <ResponsiveContainer width="100%" height={140}>
        <AreaChart data={analytics.exposureTrend} margin={{ top: 5, right: 5, left: -10, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" />
          <XAxis dataKey="date" tick={{ fontSize: 8 }} tickLine={false} />
          <YAxis tick={{ fontSize: 8 }} tickFormatter={(v) => `$${v}M`} tickLine={false} />
          <Tooltip contentStyle={{ fontSize: 10, borderRadius: 8 }} formatter={(v: any) => [`$${Number(v)}M`, "Exposure"]} />
          <defs><linearGradient id="expGrad" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor="#EF4444" stopOpacity={0.3} /><stop offset="95%" stopColor="#EF4444" stopOpacity={0} /></linearGradient></defs>
          <Area type="monotone" dataKey="amount" stroke="#EF4444" fill="url(#expGrad)" strokeWidth={2} />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}

// ── Vendor Concentration Pie ─────────────────────────────────────────────

function VendorConcentrationChart({ analytics }: { analytics: FinancialAnalytics }) {
  const COLORS = ["#3B82F6", "#8B5CF6", "#F59E0B", "#22C55E", "#EF4444", "#EC4899", "#9CA3AF"];
  return (
    <div className="bg-white dark:bg-navy-800 border border-gray-200 dark:border-navy-600 rounded-lg p-3">
      <h4 className="text-[10px] font-semibold text-gray-500 uppercase tracking-wider mb-2">Vendor Spend Concentration</h4>
      <ResponsiveContainer width="100%" height={160}>
        <PieChart>
          <Pie data={analytics.vendorConcentrationData} cx="50%" cy="50%" innerRadius={35} outerRadius={60} paddingAngle={2} dataKey="spend">
            {analytics.vendorConcentrationData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
          </Pie>
          <Tooltip contentStyle={{ fontSize: 10, borderRadius: 8 }} formatter={(v: any) => [`$${Number(v)}M`, "Spend"]} />
        </PieChart>
      </ResponsiveContainer>
      <div className="flex flex-wrap gap-1 mt-1">
        {analytics.vendorConcentrationData.map((v, i) => (
          <span key={v.vendor} className="flex items-center gap-0.5 text-[7px] text-gray-500">
            <div className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: COLORS[i % COLORS.length] }} />
            {v.vendor}
          </span>
        ))}
      </div>
    </div>
  );
}

// ── Renewal Forecast Chart ───────────────────────────────────────────────

function RenewalForecastChart({ analytics }: { analytics: FinancialAnalytics }) {
  return (
    <div className="bg-white dark:bg-navy-800 border border-gray-200 dark:border-navy-600 rounded-lg p-3">
      <h4 className="text-[10px] font-semibold text-gray-500 uppercase tracking-wider mb-2">Renewal Forecast ($M)</h4>
      <ResponsiveContainer width="100%" height={140}>
        <BarChart data={analytics.renewalForecast} margin={{ top: 5, right: 5, left: -10, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" />
          <XAxis dataKey="period" tick={{ fontSize: 8 }} tickLine={false} />
          <YAxis tick={{ fontSize: 8 }} tickFormatter={(v) => `$${v}M`} tickLine={false} />
          <Tooltip contentStyle={{ fontSize: 10, borderRadius: 8 }} />
          <Bar dataKey="amount" fill="#F59E0B" radius={[4, 4, 0, 0]} />
          <Line type="monotone" dataKey="probability" stroke="#3B82F6" strokeWidth={2} dot={{ r: 3 }} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

// ── Business Unit Exposure ───────────────────────────────────────────────

function BusinessUnitExposure({ analytics }: { analytics: FinancialAnalytics }) {
  return (
    <div className="bg-white dark:bg-navy-800 border border-gray-200 dark:border-navy-600 rounded-lg p-3">
      <h4 className="text-[10px] font-semibold text-gray-500 uppercase tracking-wider mb-2">Business Unit Exposure</h4>
      <div className="space-y-1">
        {analytics.businessUnitExposure.map(bu => (
          <div key={bu.unit} className="flex items-center gap-2">
            <span className="text-[8px] text-gray-600 dark:text-gray-300 w-24 truncate">{bu.unit}</span>
            <div className="flex-1 h-3 bg-gray-100 dark:bg-navy-700 rounded-full overflow-hidden">
              <motion.div initial={{ width: 0 }} animate={{ width: `${(bu.exposure / Math.max(...analytics.businessUnitExposure.map(x => x.exposure))) * 100}%` }}
                className={`h-full rounded-full ${bu.exposure > 40 ? "bg-red-500" : bu.exposure > 20 ? "bg-amber-500" : "bg-green-500"}`} />
            </div>
            <span className="text-[8px] text-gray-500 tabular-nums w-12 text-right">${bu.exposure.toFixed(1)}M</span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Savings Trend Chart ──────────────────────────────────────────────────

function SavingsTrendChart({ analytics }: { analytics: FinancialAnalytics }) {
  return (
    <div className="bg-white dark:bg-navy-800 border border-gray-200 dark:border-navy-600 rounded-lg p-3">
      <h4 className="text-[10px] font-semibold text-gray-500 uppercase tracking-wider mb-2">Savings Trend ($M)</h4>
      <ResponsiveContainer width="100%" height={140}>
        <AreaChart data={analytics.savingsTrend} margin={{ top: 5, right: 5, left: -10, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" />
          <XAxis dataKey="date" tick={{ fontSize: 8 }} tickLine={false} />
          <YAxis tick={{ fontSize: 8 }} tickFormatter={(v) => `$${v}M`} tickLine={false} />
          <Tooltip contentStyle={{ fontSize: 10, borderRadius: 8 }} />
          <defs><linearGradient id="saveGrad" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor="#22C55E" stopOpacity={0.3} /><stop offset="95%" stopColor="#22C55E" stopOpacity={0} /></linearGradient></defs>
          <Area type="monotone" dataKey="identified" stroke="#F59E0B" fill="none" strokeWidth={2} strokeDasharray="4 4" />
          <Area type="monotone" dataKey="realized" stroke="#22C55E" fill="url(#saveGrad)" strokeWidth={2} />
        </AreaChart>
      </ResponsiveContainer>
      <div className="flex items-center gap-3 mt-1 text-[7px] text-gray-400">
        <span className="flex items-center gap-1"><div className="w-2 h-0.5 bg-amber-500" /> Identified</span>
        <span className="flex items-center gap-1"><div className="w-2 h-0.5 bg-green-500" /> Realized</span>
      </div>
    </div>
  );
}

// ── Forecast Accuracy ────────────────────────────────────────────────────

function ForecastAccuracyChart({ analytics }: { analytics: FinancialAnalytics }) {
  return (
    <div className="bg-white dark:bg-navy-800 border border-gray-200 dark:border-navy-600 rounded-lg p-3">
      <h4 className="text-[10px] font-semibold text-gray-500 uppercase tracking-wider mb-2">Forecast Accuracy ($M)</h4>
      <ResponsiveContainer width="100%" height={120}>
        <BarChart data={analytics.forecastAccuracy} margin={{ top: 5, right: 5, left: -10, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" />
          <XAxis dataKey="period" tick={{ fontSize: 8 }} tickLine={false} />
          <YAxis tick={{ fontSize: 8 }} tickFormatter={(v) => `$${v}M`} tickLine={false} />
          <Tooltip contentStyle={{ fontSize: 10, borderRadius: 8 }} />
          <Bar dataKey="predicted" fill="#93C5FD" radius={[3, 3, 0, 0]} />
          <Bar dataKey="actual" fill="#3B82F6" radius={[3, 3, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

// ── Center Panel ─────────────────────────────────────────────────────────

interface CfoCenterPanelProps {
  analytics: FinancialAnalytics;
  exposures: FinancialExposure[];
}

type CenterTab = "overview" | "exposure" | "forecast" | "savings";

export function CfoCenterPanel({ analytics, exposures }: CfoCenterPanelProps) {
  const [activeTab, setActiveTab] = useState<CenterTab>("overview");

  const tabs: { id: CenterTab; label: string }[] = [
    { id: "overview", label: "Executive Overview" },
    { id: "exposure", label: "Exposure Analysis" },
    { id: "forecast", label: "Forecasting" },
    { id: "savings", label: "Savings Intelligence" },
  ];

  return (
    <div className="flex-1 flex flex-col min-w-0 bg-gray-50 dark:bg-navy-900">
      <div className="flex items-center justify-between px-3 py-1.5 bg-white dark:bg-navy-800 border-b border-gray-200 dark:border-navy-700">
        <div className="flex items-center gap-1">
          {tabs.map(tab => (
            <button key={tab.id} onClick={() => setActiveTab(tab.id)}
              className={`px-2.5 py-1 rounded-lg text-[10px] font-medium transition-colors ${
                activeTab === tab.id ? "bg-gold-100 text-gold-700 dark:bg-gold-900/20 dark:text-gold-400" : "text-gray-500 hover:text-navy-700 hover:bg-gray-100 dark:hover:bg-navy-700"
              }`}>{tab.label}</button>
          ))}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-3 space-y-3">
        {/* Executive Overview */}
        {activeTab === "overview" && (
          <>
            {/* Summary Cards */}
            <div className="grid grid-cols-4 gap-2">
              {[
                { label: "Portfolio Value", value: `$${(analytics.totalPortfolioValue / 1000000).toFixed(1)}M`, color: "text-blue-600", icon: <DollarSign className="w-3 h-3" /> },
                { label: "At-Risk Exposure", value: `$${(analytics.totalExposure / 1000000).toFixed(1)}M`, color: "text-red-600", icon: <AlertTriangle className="w-3 h-3" /> },
                { label: "Vendor Concentration", value: `${analytics.vendorConcentration}%`, color: "text-amber-600", icon: <Building2 className="w-3 h-3" /> },
                { label: "Savings Identified", value: `$${(analytics.savingsOpportunities / 1000000).toFixed(1)}M`, color: "text-green-600", icon: <TrendingUp className="w-3 h-3" /> },
              ].map(s => (
                <div key={s.label} className="bg-white dark:bg-navy-800 border border-gray-200 dark:border-navy-600 rounded-lg p-2.5">
                  <div className="flex items-center gap-1.5 mb-1">
                    <span className={s.color}>{s.icon}</span>
                    <span className="text-[8px] text-gray-500">{s.label}</span>
                  </div>
                  <p className={`text-lg font-bold ${s.color} tabular-nums`}>{s.value}</p>
                </div>
              ))}
            </div>

            <div className="grid grid-cols-2 gap-3">
              <ExposureWaterfall analytics={analytics} />
              <ExposureTrendChart analytics={analytics} />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <VendorConcentrationChart analytics={analytics} />
              <BusinessUnitExposure analytics={analytics} />
            </div>
          </>
        )}

        {/* Exposure Analysis */}
        {activeTab === "exposure" && (
          <div className="grid grid-cols-2 gap-3">
            <ExposureWaterfall analytics={analytics} />
            <ExposureTrendChart analytics={analytics} />
            <BusinessUnitExposure analytics={analytics} />
            <div className="bg-white dark:bg-navy-800 border border-gray-200 dark:border-navy-600 rounded-lg p-3">
              <h4 className="text-[10px] font-semibold text-gray-500 uppercase tracking-wider mb-2">Regional Exposure</h4>
              <div className="space-y-1">
                {analytics.regionalExposure.map(r => (
                  <div key={r.region} className="flex items-center gap-2">
                    <span className="text-[8px] text-gray-600 dark:text-gray-300 w-24 truncate">{r.region}</span>
                    <div className="flex-1 h-3 bg-gray-100 dark:bg-navy-700 rounded-full overflow-hidden">
                      <motion.div initial={{ width: 0 }} animate={{ width: `${(r.exposure / Math.max(...analytics.regionalExposure.map(x => x.exposure))) * 100}%` }}
                        className={`h-full rounded-full ${r.exposure > 50 ? "bg-red-500" : r.exposure > 20 ? "bg-amber-500" : "bg-green-500"}`} />
                    </div>
                    <span className="text-[8px] text-gray-500 tabular-nums w-10 text-right">${r.exposure.toFixed(1)}M</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Forecasting */}
        {activeTab === "forecast" && (
          <div className="grid grid-cols-2 gap-3">
            <RenewalForecastChart analytics={analytics} />
            <ForecastAccuracyChart analytics={analytics} />
            <div className="bg-white dark:bg-navy-800 border border-gray-200 dark:border-navy-600 rounded-lg p-3 col-span-2">
              <h4 className="text-[10px] font-semibold text-gray-500 uppercase tracking-wider mb-2">Renewal Forecast Details</h4>
              <div className="space-y-1">
                {analytics.renewalForecast.map(rf => (
                  <div key={rf.period} className="flex items-center gap-2">
                    <span className="text-[8px] text-gray-600 dark:text-gray-300 w-16">{rf.period}</span>
                    <div className="flex-1 h-3 bg-gray-100 dark:bg-navy-700 rounded-full overflow-hidden">
                      <motion.div initial={{ width: 0 }} animate={{ width: `${(rf.amount / Math.max(...analytics.renewalForecast.map(x => x.amount))) * 100}%` }} className="h-full bg-amber-500 rounded-full" />
                    </div>
                    <span className="text-[8px] text-gray-500 tabular-nums w-12 text-right">${rf.amount.toFixed(1)}M</span>
                    <span className="text-[7px] text-gray-400 w-8 text-right">{rf.probability}%</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Savings Intelligence */}
        {activeTab === "savings" && (
          <div className="grid grid-cols-2 gap-3">
            <SavingsTrendChart analytics={analytics} />
            <div className="bg-white dark:bg-navy-800 border border-gray-200 dark:border-navy-600 rounded-lg p-3">
              <h4 className="text-[10px] font-semibold text-gray-500 uppercase tracking-wider mb-2">Savings by Category</h4>
              <div className="space-y-1">
                {[
                  { cat: "Vendor Consolidation", amount: 1.4, pct: 27 },
                  { cat: "Contract Renegotiation", amount: 2.5, pct: 21 },
                  { cat: "License Optimization", amount: 1.7, pct: 20 },
                  { cat: "Bundled Procurement", amount: 1.1, pct: 26 },
                  { cat: "Payment Terms", amount: 1.8, pct: 4 },
                ].map(s => (
                  <div key={s.cat} className="flex items-center gap-2">
                    <span className="text-[8px] text-gray-600 dark:text-gray-300 w-28 truncate">{s.cat}</span>
                    <div className="flex-1 h-3 bg-gray-100 dark:bg-navy-700 rounded-full overflow-hidden">
                      <motion.div initial={{ width: 0 }} animate={{ width: `${(s.amount / 2.5) * 100}%` }} className="h-full bg-green-500 rounded-full" />
                    </div>
                    <span className="text-[8px] text-gray-500 tabular-nums w-10 text-right">${s.amount.toFixed(1)}M</span>
                    <span className="text-[7px] text-green-600 w-6 text-right">{s.pct}%</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

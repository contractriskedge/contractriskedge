"use client";

import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X, TrendingUp, BarChart3, AlertTriangle, DollarSign, FileEdit, Lightbulb, Database, Shield, Globe, BookOpen } from "lucide-react";
import type { ClauseBenchmark } from "./types";
import { RISK_BG, RISK_TEXT, RISK_BG_LIGHT } from "./types";

type TabId = "overview" | "market" | "variations" | "negotiation" | "trends" | "risk" | "ai" | "sources";

function TabBtn({ label, icon, active, onClick }: { label: string; icon: React.ReactNode; active: boolean; onClick: () => void }) {
  return (
    <button onClick={onClick} className={`flex items-center gap-1 px-2.5 py-1.5 text-[10px] font-medium rounded-md whitespace-nowrap transition-all ${active ? "bg-navy-700 text-white shadow-sm" : "text-gray-500 hover:text-gray-700 hover:bg-gray-100"}`}>
      {icon}{label}
    </button>
  );
}

interface DrawerProps {
  benchmark: ClauseBenchmark | null;
  onClose: () => void;
}

export function BenchmarkDetailDrawer({ benchmark, onClose }: DrawerProps) {
  const [tab, setTab] = useState<TabId>("overview");

  return (
    <AnimatePresence>
      {benchmark && (
        <>
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="fixed inset-0 bg-black/20 z-40" onClick={onClose} />
          <motion.div initial={{ opacity: 0, x: 380 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: 380 }}
            transition={{ type: "spring", damping: 25, stiffness: 250 }}
            className="fixed right-0 top-0 bottom-0 w-[480px] bg-white border-l border-gray-200 shadow-xl z-50 flex flex-col">
            <div className="flex items-center justify-between px-5 py-4 border-b border-gray-200">
              <div className="flex items-center gap-2 min-w-0">
                <div className="w-8 h-8 rounded-lg bg-navy-700 flex items-center justify-center"><BarChart3 className="w-4 h-4 text-white" /></div>
                <div className="min-w-0"><h3 className="text-sm font-semibold text-navy-900 truncate">{benchmark.clauseType}</h3><p className="text-[10px] text-gray-500">{benchmark.category} • {benchmark.sampleSize.toLocaleString()} samples</p></div>
              </div>
              <button onClick={onClose} className="p-1 rounded hover:bg-gray-100 text-gray-400"><X className="w-4 h-4" /></button>
            </div>
            <div className="px-4 py-2 border-b border-gray-100 flex gap-1 overflow-x-auto">
              <TabBtn label="Overview" icon={<BarChart3 className="w-3 h-3" />} active={tab === "overview"} onClick={() => setTab("overview")} />
              <TabBtn label="Market" icon={<Globe className="w-3 h-3" />} active={tab === "market"} onClick={() => setTab("market")} />
              <TabBtn label="Variations" icon={<FileEdit className="w-3 h-3" />} active={tab === "variations"} onClick={() => setTab("variations")} />
              <TabBtn label="Negotiation" icon={<HandshakeIcon />} active={tab === "negotiation"} onClick={() => setTab("negotiation")} />
              <TabBtn label="Trends" icon={<TrendingUp className="w-3 h-3" />} active={tab === "trends"} onClick={() => setTab("trends")} />
              <TabBtn label="Risk" icon={<AlertTriangle className="w-3 h-3" />} active={tab === "risk"} onClick={() => setTab("risk")} />
              <TabBtn label="AI" icon={<Lightbulb className="w-3 h-3" />} active={tab === "ai"} onClick={() => setTab("ai")} />
            </div>
            <div className="flex-1 overflow-y-auto p-5 space-y-4">
              {tab === "overview" && <OverviewTab bm={benchmark} />}
              {tab === "market" && <MarketTab bm={benchmark} />}
              {tab === "variations" && <VariationsTab />}
              {tab === "negotiation" && <NegotiationTab bm={benchmark} />}
              {tab === "trends" && <TrendsTab bm={benchmark} />}
              {tab === "risk" && <RiskTab bm={benchmark} />}
              {tab === "ai" && <AiTab bm={benchmark} />}
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}

function OverviewTab({ bm }: { bm: ClauseBenchmark }) {
  const MetaRow = ({ label, value, icon }: { label: string; value: string | React.ReactNode; icon?: React.ReactNode }) => (
    <div className="flex items-center justify-between py-1.5"><span className="text-[11px] text-gray-500 flex items-center gap-1.5">{icon}{label}</span><span className="text-[11px] font-medium text-gray-800">{value}</span></div>
  );
  return (
    <div className="space-y-4">
      <div className="p-3 bg-navy-50 rounded-lg border border-navy-100">
        <div className="flex items-center gap-1.5 mb-1.5"><TrendingUp className="w-3.5 h-3.5 text-navy-600" /><span className="text-[10px] font-semibold text-navy-700 uppercase">AI Benchmark Summary</span></div>
        <p className="text-[11px] text-gray-700 leading-relaxed">Your {bm.clauseType} clause scores {bm.yourScore}/10 vs market median of {bm.marketMedian}/10. This places you in the <strong>{bm.percentile}th percentile</strong> — a deviation of {bm.deviationPercent > 0 ? "+" : ""}{bm.deviationPercent.toFixed(0)}% from market norms. Based on {bm.sampleSize.toLocaleString()} anonymized contract samples.</p>
      </div>
      <div className="bg-gray-50 rounded-lg p-3 space-y-0.5 divide-y divide-gray-100">
        <MetaRow label="Your Score" value={<RiskBadge score={bm.yourScore} />} />
        <MetaRow label="Market Median" value={bm.marketMedian.toFixed(1) + "/10"} />
        <MetaRow label="Market Range" value={`P25: ${bm.marketP25} – P75: ${bm.marketP75}`} />
        <MetaRow label="Deviation" value={`${bm.deviationPercent > 0 ? "+" : ""}${bm.deviationPercent.toFixed(0)}%`} />
        <MetaRow label="Percentile" value={`${bm.percentile}th`} />
        <MetaRow label="Sample Size" value={bm.sampleSize.toLocaleString()} icon={<Database className="w-3 h-3" />} />
        <MetaRow label="Confidence" value={`${bm.confidence}%`} icon={<Shield className="w-3 h-3" />} />
        <MetaRow label="Trend" value={`${bm.trend > 0 ? "↑ Rising" : "↓ Falling"} (${Math.abs(bm.trend).toFixed(1)}%)`} icon={<TrendingUp className="w-3 h-3" />} />
        <MetaRow label="Category" value={bm.category} />
      </div>
    </div>
  );
}

function MarketTab({ bm }: { bm: ClauseBenchmark }) {
  return (
    <div className="space-y-4">
      <div className="p-4 bg-gray-50 rounded-lg">
        <p className="text-[10px] font-semibold text-gray-500 uppercase mb-3">Market Position</p>
        <div className="relative h-8 bg-gray-200 rounded-full overflow-hidden">
          <div className="absolute inset-0 flex items-center justify-center text-[10px] font-medium text-gray-500">Market Range</div>
          <div className="absolute top-0 left-0 h-full bg-green-200" style={{ width: `${bm.marketP25 * 10}%` }} />
          <div className="absolute top-0 h-full bg-yellow-200" style={{ left: `${bm.marketP25 * 10}%`, width: `${(bm.marketP75 - bm.marketP25) * 10}%` }} />
          <div className="absolute top-0 h-full bg-red-200" style={{ left: `${bm.marketP75 * 10}%`, width: `${(10 - bm.marketP75) * 10}%` }} />
          <div className="absolute top-0 h-full w-0.5 bg-navy-900 z-10" style={{ left: `${bm.marketMedian * 10}%` }} />
          <div className="absolute top-0 h-full w-0.5 bg-gold-400 z-10" style={{ left: `${bm.yourScore * 10}%` }} />
        </div>
        <div className="flex justify-between mt-1.5 text-[10px]">
          <span className="text-green-600">P25: {bm.marketP25}</span>
          <span className="text-navy-900 font-semibold">Median: {bm.marketMedian}</span>
          <span className="text-red-600">P75: {bm.marketP75}</span>
        </div>
        <div className="flex justify-center mt-1">
          <span className="text-[10px] font-semibold text-gold-500">Your Score: {bm.yourScore}</span>
        </div>
      </div>
      <div className="space-y-2">
        <p className="text-[10px] font-semibold text-gray-500 uppercase">Key Statistics</p>
        {[
          { label: "Your Percentile", value: `${bm.percentile}th`, color: bm.percentile > 75 ? "text-red-600" : bm.percentile > 50 ? "text-orange-600" : "text-green-600" },
          { label: "Deviation from Median", value: `${bm.deviationPercent > 0 ? "+" : ""}${bm.deviationPercent.toFixed(0)}%`, color: bm.deviationPercent > 50 ? "text-red-600" : bm.deviationPercent > 20 ? "text-orange-600" : "text-green-600" },
          { label: "Sample Reliability", value: bm.sampleSize > 2000 ? "High" : bm.sampleSize > 1000 ? "Medium" : "Low", color: "text-gray-700" },
        ].map((item) => (
          <div key={item.label} className="flex justify-between text-xs py-1"><span className="text-gray-500">{item.label}</span><span className={`font-medium ${item.color}`}>{item.value}</span></div>
        ))}
      </div>
    </div>
  );
}

function VariationsTab() {
  const variations = [
    { label: "Mutual with IP exception", frequency: "35%", risk: "Low" },
    { label: "One-way vendor favorable", frequency: "28%", risk: "High" },
    { label: "Capped at fees (100%)", frequency: "22%", risk: "Medium" },
    { label: "Uncapped", frequency: "10%", risk: "Critical" },
    { label: "Mutual with $ cap", frequency: "5%", risk: "Low" },
  ];
  return (
    <div className="space-y-2">
      <p className="text-[10px] font-semibold text-gray-500 uppercase mb-2">Common Variations</p>
      {variations.map((v) => (
        <div key={v.label} className="flex items-center gap-2.5 p-2.5 bg-white border border-gray-100 rounded-lg">
          <FileEdit className="w-3.5 h-3.5 text-gray-400 flex-shrink-0" />
          <div className="flex-1"><p className="text-[11px] font-medium text-gray-800">{v.label}</p></div>
          <span className="text-[10px] text-gray-500">{v.frequency}</span>
          <span className={`text-[9px] font-medium px-1.5 py-0.5 rounded-full ${v.risk === "Low" ? "bg-green-50 text-green-700" : v.risk === "Medium" ? "bg-yellow-50 text-yellow-700" : v.risk === "High" ? "bg-orange-50 text-orange-700" : "bg-red-50 text-red-700"}`}>{v.risk}</span>
        </div>
      ))}
    </div>
  );
}

function NegotiationTab({ bm }: { bm: ClauseBenchmark }) {
  return (
    <div className="space-y-3">
      <div className="p-3 bg-green-50 rounded-lg border border-green-100">
        <p className="text-[10px] font-semibold text-green-700 uppercase mb-1">Recommended Position</p>
        <p className="text-[11px] text-gray-700">Target market median ({bm.marketMedian}/10) or P75 ({bm.marketP75}/10). Current position ({bm.yourScore}/10) is {bm.deviationPercent.toFixed(0)}% above market.</p>
      </div>
      <div className="p-3 bg-navy-50 rounded-lg border border-navy-100">
        <p className="text-[10px] font-semibold text-navy-700 uppercase mb-1">Fallback Positions</p>
        <div className="space-y-1">
          {["Cap at 100% of fees paid", "Mutual exclusion for consequential damages", "IP infringement exception"].map((fp, i) => (
            <div key={i} className="flex items-start gap-1.5 text-[11px] text-gray-600"><span className="text-navy-400 font-bold">{i + 1}.</span>{fp}</div>
          ))}
        </div>
      </div>
      <div className="p-3 bg-amber-50 rounded-lg border border-amber-100">
        <p className="text-[10px] font-semibold text-amber-700 uppercase mb-1">Leverage Analysis</p>
        <p className="text-[11px] text-gray-700">You have <strong>strong leverage</strong> — {bm.percentile}% of peer contracts have less aggressive terms. Use market benchmark data to negotiate alignment with industry standards.</p>
      </div>
    </div>
  );
}

function TrendsTab({ bm }: { bm: ClauseBenchmark }) {
  return (
    <div className="space-y-3">
      <p className="text-[10px] font-semibold text-gray-500 uppercase mb-2">Historical Trend</p>
      <div className="h-40 bg-gray-50 rounded-lg flex items-center justify-center text-gray-400 text-xs">
        <div className="text-center"><TrendingUp className="w-6 h-6 mx-auto mb-1" /><p>Trend chart: {bm.trend > 0 ? "Rising" : "Falling"} {Math.abs(bm.trend).toFixed(1)}% period-over-period</p></div>
      </div>
      <div className="space-y-1.5">
        {[
          { period: "Last 30 days", change: `${bm.trend > 0 ? "+" : ""}${(bm.trend * 0.3).toFixed(1)}%` },
          { period: "Last 90 days", change: `${bm.trend > 0 ? "+" : ""}${(bm.trend * 0.7).toFixed(1)}%` },
          { period: "Last 12 months", change: `${bm.trend > 0 ? "+" : ""}${bm.trend.toFixed(1)}%` },
        ].map((item) => (
          <div key={item.period} className="flex justify-between text-xs py-1"><span className="text-gray-500">{item.period}</span><span className={`font-medium ${bm.trend > 0 ? "text-red-500" : "text-green-500"}`}>{item.change}</span></div>
        ))}
      </div>
    </div>
  );
}

function RiskTab({ bm }: { bm: ClauseBenchmark }) {
  const risks = [
    { name: "Market Deviation Risk", score: Math.min(10, Math.abs(bm.deviationPercent) / 10), detail: `${bm.deviationPercent.toFixed(0)}% deviation from market median` },
    { name: "Negotiation Risk", score: bm.percentile > 75 ? 8 : bm.percentile > 50 ? 5 : 2, detail: `${bm.percentile}th percentile — ${bm.percentile > 75 ? "aggressive" : "favorable"} position` },
    { name: "Sample Reliability Risk", score: bm.sampleSize > 2000 ? 2 : bm.sampleSize > 1000 ? 5 : 8, detail: `${bm.sampleSize.toLocaleString()} samples — ${bm.sampleSize > 2000 ? "high" : "medium"} reliability` },
    { name: "Trend Risk", score: Math.min(10, Math.abs(bm.trend) * 1.5), detail: `${bm.trend > 0 ? "Rising" : "Falling"} trend of ${Math.abs(bm.trend).toFixed(1)}%` },
  ];
  return (
    <div className="space-y-2">
      <p className="text-[10px] font-semibold text-gray-500 uppercase mb-2">Risk Analysis</p>
      {risks.map((r) => (
        <div key={r.name} className="p-2.5 bg-white border border-gray-100 rounded-lg">
          <div className="flex items-center justify-between mb-1"><span className="text-[11px] font-semibold text-navy-900">{r.name}</span><RiskBadge score={r.score} /></div>
          <p className="text-[10px] text-gray-600">{r.detail}</p>
        </div>
      ))}
    </div>
  );
}

function AiTab({ bm }: { bm: ClauseBenchmark }) {
  return (
    <div className="space-y-3">
      <div className="p-3 bg-purple-50 rounded-lg border border-purple-100">
        <div className="flex items-center gap-1.5 mb-1.5"><Lightbulb className="w-3.5 h-3.5 text-purple-600" /><span className="text-[10px] font-semibold text-purple-700 uppercase">AI Recommendations</span></div>
        <div className="space-y-2">
          {[
            { title: "Negotiation Priority", desc: `High priority — ${bm.percentile}th percentile is significantly above market.` },
            { title: "Suggested Approach", desc: `Present market benchmark data showing median of ${bm.marketMedian}/10 vs your ${bm.yourScore}/10.` },
            { title: "Risk Mitigation", desc: `Target ${bm.marketP75}/10 or lower. Current position exposes ${bm.deviationPercent.toFixed(0)}% above-market risk.` },
            { title: "Market Intelligence", desc: `${bm.sampleSize.toLocaleString()} contracts analyzed across ${bm.category} category.` },
          ].map((item) => (
            <div key={item.title} className="p-2 bg-white rounded border border-purple-100">
              <p className="text-[10px] font-semibold text-navy-700 uppercase mb-0.5">{item.title}</p>
              <p className="text-[11px] text-gray-600">{item.desc}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function RiskBadge({ score }: { score: number }) {
  const level = score >= 8 ? "critical" : score >= 6 ? "high" : score >= 4 ? "medium" : "low";
  return <span className={`inline-flex items-center gap-1 text-[10px] font-bold px-1.5 py-0.5 rounded-full ${RISK_BG_LIGHT[level]} ${RISK_TEXT[level]}`}><span className={`w-1.5 h-1.5 rounded-full ${RISK_BG[level]}`} />{score.toFixed(0)}/10</span>;
}

function HandshakeIcon() {
  return (
    <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75m-3-7.036A11.959 11.959 0 013.598 6 11.99 11.99 0 003 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285z" />
    </svg>
  );
}

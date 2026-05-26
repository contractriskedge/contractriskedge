"use client";

import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X, FileText, TrendingUp, BarChart3, BookOpen, Activity, Link, Clock, Brain, ChevronDown, ChevronUp, CheckCircle, AlertTriangle, Copy, Star } from "lucide-react";
import type { ClauseRecord, BenchmarkData } from "./types";
import { RISK_BG, RISK_TEXT, RISK_BG_LIGHT } from "./types";

type TabId = "overview" | "benchmark" | "variants" | "negotiation" | "usage" | "related" | "versions" | "ai";

function TabBtn({ label, icon, active, onClick }: { label: string; icon: React.ReactNode; active: boolean; onClick: () => void }) {
  return (
    <button onClick={onClick} className={`flex items-center gap-1 px-2.5 py-1.5 text-[10px] font-medium rounded-md whitespace-nowrap transition-all ${active ? "bg-navy-700 text-white shadow-sm" : "text-gray-500 hover:text-gray-700 hover:bg-gray-100"}`}>
      {icon}{label}
    </button>
  );
}

interface DrawerProps {
  clause: ClauseRecord | null;
  benchmarks: BenchmarkData[];
  onClose: () => void;
  onToggleFavorite: (id: string) => void;
}

export function ClauseDetailDrawer({ clause, benchmarks, onClose, onToggleFavorite }: DrawerProps) {
  const [tab, setTab] = useState<TabId>("overview");

  return (
    <AnimatePresence>
      {clause && (
        <>
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="fixed inset-0 bg-black/20 z-40" onClick={onClose} />
          <motion.div initial={{ opacity: 0, x: 380 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: 380 }}
            transition={{ type: "spring", damping: 25, stiffness: 250 }}
            className="fixed right-0 top-0 bottom-0 w-[500px] bg-white border-l border-gray-200 shadow-xl z-50 flex flex-col">
            <div className="flex items-center justify-between px-5 py-4 border-b border-gray-200">
              <div className="flex items-center gap-2 min-w-0">
                <div className="w-8 h-8 rounded-lg bg-navy-700 flex items-center justify-center"><FileText className="w-4 h-4 text-white" /></div>
                <div className="min-w-0"><h3 className="text-sm font-semibold text-navy-900 truncate">{clause.name}</h3><p className="text-[10px] text-gray-500">{clause.id} • {clause.category.replace(/_/g, " ")}</p></div>
              </div>
              <div className="flex items-center gap-1">
                <button onClick={() => onToggleFavorite(clause.id)} className="p-1 rounded hover:bg-gray-100 transition-colors">
                  <Star className={`w-4 h-4 ${clause.isFavorite ? "text-gold-400 fill-gold-400" : "text-gray-300"}`} />
                </button>
                <button onClick={onClose} className="p-1 rounded hover:bg-gray-100 text-gray-400"><X className="w-4 h-4" /></button>
              </div>
            </div>
            <div className="px-4 py-2 border-b border-gray-100 flex gap-1 overflow-x-auto">
              <TabBtn label="Overview" icon={<FileText className="w-3 h-3" />} active={tab === "overview"} onClick={() => setTab("overview")} />
              <TabBtn label="Benchmark" icon={<BarChart3 className="w-3 h-3" />} active={tab === "benchmark"} onClick={() => setTab("benchmark")} />
              <TabBtn label="Variants" icon={<Copy className="w-3 h-3" />} active={tab === "variants"} onClick={() => setTab("variants")} />
              <TabBtn label="Negotiation" icon={<BookOpen className="w-3 h-3" />} active={tab === "negotiation"} onClick={() => setTab("negotiation")} />
              <TabBtn label="Usage" icon={<Activity className="w-3 h-3" />} active={tab === "usage"} onClick={() => setTab("usage")} />
              <TabBtn label="Related" icon={<Link className="w-3 h-3" />} active={tab === "related"} onClick={() => setTab("related")} />
              <TabBtn label="AI" icon={<Brain className="w-3 h-3" />} active={tab === "ai"} onClick={() => setTab("ai")} />
            </div>
            <div className="flex-1 overflow-y-auto p-5 space-y-4">
              {tab === "overview" && <OverviewTab c={clause} />}
              {tab === "benchmark" && <BenchmarkTab c={clause} benchmarks={benchmarks} />}
              {tab === "variants" && <VariantsTab c={clause} />}
              {tab === "negotiation" && <NegotiationTab c={clause} />}
              {tab === "usage" && <UsageTab c={clause} />}
              {tab === "related" && <RelatedTab />}
              {tab === "ai" && <AiTab c={clause} />}
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}

function OverviewTab({ c }: { c: ClauseRecord }) {
  const MetaRow = ({ label, value, icon }: { label: string; value: string | React.ReactNode; icon?: React.ReactNode }) => (
    <div className="flex items-center justify-between py-1.5"><span className="text-[11px] text-gray-500 flex items-center gap-1.5">{icon}{label}</span><span className="text-[11px] font-medium text-gray-800">{value}</span></div>
  );
  return (
    <div className="space-y-4">
      <div className="p-3 bg-navy-50 rounded-lg border border-navy-100">
        <div className="flex items-center gap-1.5 mb-1.5"><Brain className="w-3.5 h-3.5 text-navy-600" /><span className="text-[10px] font-semibold text-navy-700 uppercase">AI Analysis</span></div>
        <p className="text-[11px] text-gray-700 leading-relaxed">{c.aiExplanation}</p>
      </div>
      <div className="p-3 bg-white border border-gray-200 rounded-lg">
        <p className="text-[10px] font-semibold text-gray-500 uppercase mb-1.5">Clause Text</p>
        <p className="text-[11px] text-gray-700 leading-relaxed">{c.text}</p>
      </div>
      <div className="bg-gray-50 rounded-lg p-3 space-y-0.5 divide-y divide-gray-100">
        <MetaRow label="Category" value={c.category.replace(/_/g, " ")} />
        <MetaRow label="Risk Score" value={<RiskBadge score={c.riskScore} />} />
        <MetaRow label="Benchmark" value={`${c.benchmarkPercentile}th percentile`} />
        <MetaRow label="Jurisdiction" value={c.jurisdiction} />
        <MetaRow label="Status" value={c.approvalStatus.replace(/_/g, " ")} />
        <MetaRow label="Owner" value={c.owner} />
        <MetaRow label="Versions" value={c.versions.toString()} />
        <MetaRow label="Last Updated" value={c.lastUpdated} />
        <MetaRow label="AI Confidence" value={`${c.aiConfidence}%`} />
        <MetaRow label="Neg. Strength" value={`${c.negotiationStrength}%`} />
      </div>
    </div>
  );
}

function BenchmarkTab({ c, benchmarks }: { c: ClauseRecord; benchmarks: BenchmarkData[] }) {
  const bm = benchmarks.find((b) => b.clauseType.toLowerCase() === c.category);
  return (
    <div className="space-y-4">
      {bm && (
        <>
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
            <div className="flex justify-between mt-1.5 text-[10px]"><span className="text-green-600">P25: {bm.marketP25}</span><span className="text-navy-900 font-semibold">Median: {bm.marketMedian}</span><span className="text-red-600">P75: {bm.marketP75}</span></div>
          </div>
          <div className="space-y-1.5">
            {[
              { label: "Your Score", value: `${bm.yourScore}/10` },
              { label: "Market Median", value: `${bm.marketMedian}/10` },
              { label: "Percentile", value: `${bm.percentile}th` },
              { label: "Sample Size", value: bm.sampleSize.toLocaleString() },
            ].map((item) => (
              <div key={item.label} className="flex justify-between text-xs py-1"><span className="text-gray-500">{item.label}</span><span className="font-medium text-gray-800">{item.value}</span></div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}

function VariantsTab({ c }: { c: ClauseRecord }) {
  return (
    <div className="space-y-2">
      <p className="text-[10px] font-semibold text-gray-500 uppercase mb-2">Fallback Variants ({c.fallbackVariants.length})</p>
      {c.fallbackVariants.map((v) => (
        <div key={v.id} className={`p-3 rounded-lg border ${v.isPreferred ? "border-green-200 bg-green-50" : "border-gray-200 bg-white"}`}>
          <div className="flex items-center justify-between mb-1.5">
            <div className="flex items-center gap-1.5">
              <span className="text-[11px] font-semibold text-navy-900">{v.label}</span>
              {v.isPreferred && <span className="text-[9px] font-medium px-1.5 py-0.5 rounded-full bg-green-100 text-green-700">Preferred</span>}
            </div>
            <div className="flex items-center gap-2">
              <RiskBadge score={v.riskScore} />
              <span className="text-[10px] text-gray-500">{v.negotiationStrength}% strength</span>
            </div>
          </div>
          <p className="text-[10px] text-gray-600 leading-relaxed">{v.text}</p>
          <div className="flex items-center gap-2 mt-1.5 text-[9px] text-gray-400">
            <span>{v.usageRate}% usage rate</span>
            <button className="text-navy-600 hover:text-navy-800 font-medium">Copy</button>
          </div>
        </div>
      ))}
    </div>
  );
}

function NegotiationTab({ c }: { c: ClauseRecord }) {
  return (
    <div className="space-y-3">
      <div className="p-3 bg-green-50 rounded-lg border border-green-100">
        <p className="text-[10px] font-semibold text-green-700 uppercase mb-1">Negotiation Guidance</p>
        <p className="text-[11px] text-gray-700 leading-relaxed">{c.negotiationGuidance}</p>
      </div>
      <div className="p-3 bg-navy-50 rounded-lg border border-navy-100">
        <p className="text-[10px] font-semibold text-navy-700 uppercase mb-1">Governance Notes</p>
        <p className="text-[11px] text-gray-700">{c.governanceNotes}</p>
      </div>
      <div className="space-y-1.5">
        {[
          { label: "Negotiation Strength", value: `${c.negotiationStrength}%`, color: c.negotiationStrength >= 80 ? "text-green-600" : c.negotiationStrength >= 60 ? "text-yellow-600" : "text-red-600" },
          { label: "Usage Frequency", value: c.usageFrequency.toString() },
          { label: "Preferred Variant", value: c.fallbackVariants.find((v) => v.isPreferred)?.label || "Standard" },
          { label: "Jurisdiction Coverage", value: c.jurisdiction },
        ].map((item) => (
          <div key={item.label} className="flex justify-between text-xs py-1"><span className="text-gray-500">{item.label}</span><span className={`font-medium ${item.color || "text-gray-800"}`}>{item.value}</span></div>
        ))}
      </div>
    </div>
  );
}

function UsageTab({ c }: { c: ClauseRecord }) {
  return (
    <div className="space-y-3">
      <div className="grid grid-cols-2 gap-3">
        {[
          { label: "Total Uses", value: c.usageFrequency.toString() },
          { label: "Success Rate", value: `${c.negotiationStrength}%` },
          { label: "Versions", value: c.versions.toString() },
          { label: "AI Confidence", value: `${c.aiConfidence}%` },
        ].map((item) => (
          <div key={item.label} className="p-3 bg-gray-50 rounded-lg text-center">
            <p className="text-[9px] text-gray-500 uppercase">{item.label}</p>
            <p className="text-lg font-bold text-navy-900 mt-1">{item.value}</p>
          </div>
        ))}
      </div>
      <div>
        <p className="text-[10px] font-semibold text-gray-500 uppercase mb-1.5">Contract Types</p>
        <div className="flex gap-1 flex-wrap">{c.contractTypes.map((t) => (
          <span key={t} className="text-[10px] px-1.5 py-0.5 rounded bg-navy-50 text-navy-700">{t}</span>
        ))}</div>
      </div>
    </div>
  );
}

function RelatedTab() {
  const related = [
    { name: "Liability Cap Clause", relationship: "Companion clause", risk: 5.0 },
    { name: "Termination Clause", relationship: "Often paired", risk: 4.5 },
    { name: "Confidentiality Clause", relationship: "Related protection", risk: 3.8 },
  ];
  return (
    <div className="space-y-1.5">
      <p className="text-[10px] font-semibold text-gray-500 uppercase mb-2">Related Clauses</p>
      {related.map((r, i) => (
        <div key={i} className="flex items-center gap-2.5 p-2.5 bg-white border border-gray-100 rounded-lg hover:bg-gray-50 transition-colors cursor-pointer">
          <Link className="w-3.5 h-3.5 text-navy-400 flex-shrink-0" />
          <div className="flex-1"><p className="text-[11px] font-medium text-gray-800">{r.name}</p><p className="text-[9px] text-gray-400">{r.relationship}</p></div>
          <RiskBadge score={r.risk} />
        </div>
      ))}
    </div>
  );
}

function AiTab({ c }: { c: ClauseRecord }) {
  return (
    <div className="space-y-3">
      <div className="p-3 bg-purple-50 rounded-lg border border-purple-100">
        <div className="flex items-center gap-1.5 mb-1.5"><Brain className="w-3.5 h-3.5 text-purple-600" /><span className="text-[10px] font-semibold text-purple-700 uppercase">AI Recommendations</span></div>
        <div className="space-y-2">
          {[
            { title: "Risk Assessment", desc: `Risk score ${c.riskScore}/10 — ${c.riskLevel} risk level. ${c.benchmarkPercentile}th percentile vs market.` },
            { title: "Improvement Suggestion", desc: c.riskScore >= 6 ? "Consider adopting the preferred variant to reduce risk exposure." : "Current clause is well-aligned with market standards." },
            { title: "Usage Recommendation", desc: `Used ${c.usageFrequency} times with ${c.negotiationStrength}% negotiation strength. Recommended for ${c.contractTypes.join(", ")}.` },
            { title: "Review Schedule", desc: `Last updated ${c.lastUpdated}. Next review recommended within 90 days.` },
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
  return <span className={`inline-flex items-center gap-1 text-[10px] font-bold px-1.5 py-0.5 rounded-full ${RISK_BG_LIGHT[level]} ${RISK_TEXT[level]}`}><span className={`w-1.5 h-1.5 rounded-full ${RISK_BG[level]}`} />{score}/10</span>;
}

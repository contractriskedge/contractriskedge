// ── Enterprise Benchmark Intelligence Mock Data ─────────────────────────────

import type { BenchmarkKpi, ClauseBenchmark, IndustryComparison, MarketInsight, VendorBenchmark, NegotiationIntel, ComplianceBenchmark, ClauseLibrary, BenchmarkDistribution } from "./types";

function rand(min: number, max: number) { return Math.floor(Math.random() * (max - min + 1)) + min; }

// ── KPI Metrics ─────────────────────────────────────────────────────────────

export const benchmarkKpis: BenchmarkKpi[] = [
  { id: "corpus-size", label: "Benchmark Corpus Size", value: "12,847", trend: 15.3, trendDirection: "up", icon: "Database", color: "from-navy-600 to-navy-800", severity: "info", sparklineData: [8500, 9200, 9800, 10400, 11000, 11600, 12200, 12847], tooltip: "Total anonymized contracts in benchmark corpus" },
  { id: "deviations", label: "Benchmark Deviations", value: "47", trend: 12.8, trendDirection: "up", icon: "AlertTriangle", color: "from-red-500 to-orange-500", severity: "critical", sparklineData: [32, 35, 37, 39, 41, 43, 45, 47], tooltip: "Clauses deviating significantly from market norms" },
  { id: "above-market", label: "Above-Market Risk Clauses", value: "28", trend: 7.7, trendDirection: "up", icon: "TrendingUp", color: "from-orange-500 to-red-500", severity: "warning", sparklineData: [22, 23, 24, 25, 25, 26, 27, 28], tooltip: "Clauses with risk scores exceeding market median" },
  { id: "negotiation-opps", label: "Negotiation Opportunities", value: "34", trend: -8.1, trendDirection: "down", icon: "Handshake", color: "from-green-500 to-emerald-500", severity: "success", sparklineData: [42, 40, 39, 38, 37, 36, 35, 34], tooltip: "Clauses with room for negotiation improvement" },
  { id: "coverage", label: "Industry Coverage", value: "92%", trend: 4.5, trendDirection: "up", icon: "PieChart", color: "from-blue-500 to-indigo-500", severity: "info", sparklineData: [82, 84, 86, 87, 88, 90, 91, 92], tooltip: "Percentage of industries covered in benchmark corpus" },
  { id: "pricing-variance", label: "Pricing Variance Alerts", value: "15", trend: 25.0, trendDirection: "up", icon: "DollarSign", color: "from-amber-500 to-yellow-500", severity: "warning", sparklineData: [8, 9, 10, 11, 12, 13, 14, 15], tooltip: "Contracts with pricing outside market norms" },
  { id: "aggressiveness", label: "Avg Vendor Aggressiveness", value: "7.2", trend: 5.9, trendDirection: "up", icon: "Swords", color: "from-purple-500 to-pink-500", severity: "warning", sparklineData: [6.2, 6.4, 6.6, 6.7, 6.9, 7.0, 7.1, 7.2], tooltip: "Average vendor aggressiveness score (1-10)" },
  { id: "compliance-gaps", label: "Compliance Benchmark Gaps", value: "12", trend: -20.0, trendDirection: "down", icon: "Shield", color: "from-red-500 to-rose-500", severity: "critical", sparklineData: [18, 17, 16, 15, 14, 13, 13, 12], tooltip: "Compliance gaps relative to regulatory benchmarks" },
];

// ── Clause Benchmarks ───────────────────────────────────────────────────────

export const clauseBenchmarks: ClauseBenchmark[] = [
  { clauseType: "Indemnification", yourScore: 8.5, marketMedian: 5.2, marketP25: 3.5, marketP75: 6.8, deviation: 3.3, deviationPercent: 63.5, direction: "far_above", percentile: 92, sampleSize: 2847, confidence: 94, trend: 5.2, category: "Liability" },
  { clauseType: "Liability Cap", yourScore: 7.8, marketMedian: 4.5, marketP25: 3.0, marketP75: 6.0, deviation: 3.3, deviationPercent: 73.3, direction: "far_above", percentile: 88, sampleSize: 2654, confidence: 92, trend: 4.8, category: "Liability" },
  { clauseType: "Termination", yourScore: 6.5, marketMedian: 4.8, marketP25: 3.2, marketP75: 6.2, deviation: 1.7, deviationPercent: 35.4, direction: "above_market", percentile: 76, sampleSize: 3120, confidence: 95, trend: 2.1, category: "Rights" },
  { clauseType: "Confidentiality", yourScore: 4.2, marketMedian: 3.8, marketP25: 2.5, marketP75: 5.0, deviation: 0.4, deviationPercent: 10.5, direction: "at_market", percentile: 55, sampleSize: 2890, confidence: 90, trend: -1.2, category: "Protection" },
  { clauseType: "Data Privacy", yourScore: 6.8, marketMedian: 5.5, marketP25: 4.0, marketP75: 7.0, deviation: 1.3, deviationPercent: 23.6, direction: "above_market", percentile: 72, sampleSize: 2156, confidence: 88, trend: 3.5, category: "Compliance" },
  { clauseType: "Compliance", yourScore: 7.2, marketMedian: 5.0, marketP25: 3.5, marketP75: 6.5, deviation: 2.2, deviationPercent: 44.0, direction: "above_market", percentile: 80, sampleSize: 2340, confidence: 91, trend: 4.2, category: "Compliance" },
  { clauseType: "Payment Terms", yourScore: 5.5, marketMedian: 4.2, marketP25: 3.0, marketP75: 5.5, deviation: 1.3, deviationPercent: 31.0, direction: "above_market", percentile: 68, sampleSize: 2780, confidence: 89, trend: 1.8, category: "Financial" },
  { clauseType: "Force Majeure", yourScore: 3.8, marketMedian: 4.5, marketP25: 3.0, marketP75: 6.0, deviation: -0.7, deviationPercent: -15.6, direction: "below_market", percentile: 35, sampleSize: 1890, confidence: 85, trend: -2.5, category: "Rights" },
  { clauseType: "Assignment", yourScore: 4.5, marketMedian: 3.5, marketP25: 2.5, marketP75: 4.5, deviation: 1.0, deviationPercent: 28.6, direction: "above_market", percentile: 65, sampleSize: 1654, confidence: 82, trend: 1.5, category: "Rights" },
  { clauseType: "Governing Law", yourScore: 5.2, marketMedian: 4.0, marketP25: 2.5, marketP75: 5.5, deviation: 1.2, deviationPercent: 30.0, direction: "above_market", percentile: 70, sampleSize: 2100, confidence: 87, trend: 2.0, category: "Legal" },
  { clauseType: "Non-Compete", yourScore: 6.0, marketMedian: 4.5, marketP25: 3.0, marketP75: 6.0, deviation: 1.5, deviationPercent: 33.3, direction: "above_market", percentile: 72, sampleSize: 1450, confidence: 84, trend: 3.0, category: "Restrictions" },
  { clauseType: "IP Ownership", yourScore: 7.5, marketMedian: 5.0, marketP25: 3.5, marketP75: 6.5, deviation: 2.5, deviationPercent: 50.0, direction: "far_above", percentile: 85, sampleSize: 1890, confidence: 90, trend: 4.5, category: "IP" },
  { clauseType: "Auto-Renewal", yourScore: 6.2, marketMedian: 4.0, marketP25: 2.5, marketP75: 5.5, deviation: 2.2, deviationPercent: 55.0, direction: "far_above", percentile: 82, sampleSize: 1250, confidence: 86, trend: 5.5, category: "Rights" },
  { clauseType: "SLA", yourScore: 5.8, marketMedian: 5.0, marketP25: 3.5, marketP75: 6.5, deviation: 0.8, deviationPercent: 16.0, direction: "at_market", percentile: 60, sampleSize: 1980, confidence: 88, trend: 1.0, category: "Performance" },
  { clauseType: "Insurance", yourScore: 4.8, marketMedian: 4.0, marketP25: 2.5, marketP75: 5.5, deviation: 0.8, deviationPercent: 20.0, direction: "above_market", percentile: 62, sampleSize: 1120, confidence: 80, trend: 2.2, category: "Protection" },
  { clauseType: "Audit Rights", yourScore: 5.0, marketMedian: 3.5, marketP25: 2.0, marketP75: 5.0, deviation: 1.5, deviationPercent: 42.9, direction: "above_market", percentile: 75, sampleSize: 980, confidence: 78, trend: 3.8, category: "Rights" },
];

// ── Benchmark Distributions ─────────────────────────────────────────────────

export const benchmarkDistributions: BenchmarkDistribution[] = clauseBenchmarks.map((cb) => ({
  clauseType: cb.clauseType,
  values: Array.from({ length: 50 }, () => +(cb.marketMedian + (Math.random() - 0.5) * cb.marketMedian * 0.8).toFixed(1)),
  yourValue: cb.yourScore,
  marketMedian: cb.marketMedian,
}));

// ── Industry Comparisons ────────────────────────────────────────────────────

export const industryComparisons: IndustryComparison[] = [
  { industry: "Technology", yourScore: 6.8, industryAvg: 5.2, industryP10: 3.0, industryP90: 7.5, deviation: 1.6, sampleSize: 3200 },
  { industry: "Financial Services", yourScore: 6.8, industryAvg: 5.8, industryP10: 3.5, industryP90: 8.0, deviation: 1.0, sampleSize: 2800 },
  { industry: "Healthcare", yourScore: 6.8, industryAvg: 4.5, industryP10: 2.5, industryP90: 6.5, deviation: 2.3, sampleSize: 1800 },
  { industry: "Manufacturing", yourScore: 6.8, industryAvg: 4.0, industryP10: 2.0, industryP90: 6.0, deviation: 2.8, sampleSize: 1500 },
  { industry: "Retail", yourScore: 6.8, industryAvg: 3.8, industryP10: 2.0, industryP90: 5.5, deviation: 3.0, sampleSize: 1200 },
  { industry: "Energy", yourScore: 6.8, industryAvg: 4.8, industryP10: 3.0, industryP90: 6.8, deviation: 2.0, sampleSize: 900 },
  { industry: "Telecom", yourScore: 6.8, industryAvg: 5.5, industryP10: 3.5, industryP90: 7.5, deviation: 1.3, sampleSize: 800 },
  { industry: "Pharmaceutical", yourScore: 6.8, industryAvg: 5.0, industryP10: 3.0, industryP90: 7.0, deviation: 1.8, sampleSize: 647 },
];

// ── Market Insights ─────────────────────────────────────────────────────────

export const marketInsights: MarketInsight[] = [
  { id: "mi-1", title: "Liability Cap Exceeds Market by 240%", description: "Your liability cap of 8.5/10 far exceeds the market median of 5.2/10. This places you in the 92nd percentile for risk exposure — significantly more vendor-favorable than peers.", severity: "critical", confidence: 94, percentile: 92, affectedClauses: ["Liability Cap", "Indemnification"], recommendation: "Negotiate liability cap down to market median (5.2) or P75 (6.8). Consider mutual cap structure.", fallbackLanguage: "Neither party's aggregate liability shall exceed [100% / 200%] of fees paid during the preceding 12-month period.", category: "Liability", quickActions: [{ label: "View Clauses", action: "view" }, { label: "Generate Redline", action: "redline" }] },
  { id: "mi-2", title: "Termination Clause More Favorable to Vendor Than 82% of Peers", description: "Your termination clause scores 6.5/10 vs market median 4.8/10. Only 18% of peer contracts have more vendor-favorable termination terms.", severity: "warning", confidence: 91, percentile: 82, affectedClauses: ["Termination"], recommendation: "Negotiate mutual termination rights. Add for-cause termination with 30-day cure period.", fallbackLanguage: "Either party may terminate this agreement upon [30/60] days written notice, or immediately for material breach.", category: "Rights", quickActions: [{ label: "Market Comparison", action: "compare" }, { label: "Redline", action: "redline" }] },
  { id: "mi-3", title: "IP Ownership Clause in 85th Percentile", description: "IP ownership terms score 7.5/10 vs market median 5.0/10. 85% of peer contracts have less vendor-favorable IP terms.", severity: "warning", confidence: 88, percentile: 85, affectedClauses: ["IP Ownership"], recommendation: "Ensure IP assignment covers all work product. Consider separate IP schedule.", fallbackLanguage: "All intellectual property rights in deliverables shall vest in the Client upon full payment.", category: "IP", quickActions: [{ label: "Review", action: "review" }, { label: "Benchmark", action: "benchmark" }] },
  { id: "mi-4", title: "Payment Terms Within Market Range", description: "Payment terms at 5.5/10 are within the market range (P25: 3.0, P75: 5.5). Aligned with enterprise norms.", severity: "success", confidence: 89, percentile: 68, affectedClauses: ["Payment Terms"], recommendation: "No action required. Current terms are market-aligned.", category: "Financial", quickActions: [{ label: "Details", action: "details" }] },
  { id: "mi-5", title: "Auto-Renewal Risk Significantly Above Market", description: "Auto-renewal clause scores 6.2/10 vs market median 4.0/10. 82nd percentile — 55% above market average.", severity: "critical", confidence: 86, percentile: 82, affectedClauses: ["Auto-Renewal"], recommendation: "Add 60-day notice period for non-renewal. Ensure automatic renewal has opt-out mechanism.", fallbackLanguage: "This agreement shall automatically renew for successive [one-year] terms unless either party provides [60/90] days written notice.", category: "Rights", quickActions: [{ label: "View Contracts", action: "view" }, { label: "Generate Alert", action: "alert" }] },
  { id: "mi-6", title: "Compliance Clause Coverage Strong vs Healthcare Peers", description: "Compliance clause scores 7.2/10 vs healthcare industry average 4.5/10. 60% above industry norm.", severity: "info", confidence: 85, percentile: 80, affectedClauses: ["Compliance", "Data Privacy"], recommendation: "Maintain current compliance language. Consider adding sector-specific regulatory references.", category: "Compliance", quickActions: [{ label: "Industry View", action: "view" }, { label: "Compliance Report", action: "report" }] },
];

// ── Vendor Benchmarks ───────────────────────────────────────────────────────

export const vendorBenchmarks: VendorBenchmark[] = [
  { vendor: "SecureNet Solutions", aggressivenessScore: 9.2, deviationCount: 8, avgDeviation: 3.8, topDeviations: [{ clause: "Liability Cap", deviation: 4.5 }, { clause: "Indemnification", deviation: 4.2 }, { clause: "Termination", deviation: 3.5 }], trend: 8.5, contractsAnalyzed: 12 },
  { vendor: "Acme Corp", aggressivenessScore: 8.5, deviationCount: 6, avgDeviation: 3.2, topDeviations: [{ clause: "IP Ownership", deviation: 4.0 }, { clause: "Auto-Renewal", deviation: 3.8 }, { clause: "Liability Cap", deviation: 3.2 }], trend: 5.2, contractsAnalyzed: 24 },
  { vendor: "GlobalTech Inc", aggressivenessScore: 7.8, deviationCount: 5, avgDeviation: 2.8, topDeviations: [{ clause: "Data Privacy", deviation: 3.5 }, { clause: "Compliance", deviation: 3.0 }, { clause: "Governing Law", deviation: 2.5 }], trend: 4.8, contractsAnalyzed: 18 },
  { vendor: "Pacific Rim Trading", aggressivenessScore: 7.2, deviationCount: 4, avgDeviation: 2.2, topDeviations: [{ clause: "Force Majeure", deviation: 3.0 }, { clause: "Assignment", deviation: 2.5 }, { clause: "Payment Terms", deviation: 2.0 }], trend: 3.5, contractsAnalyzed: 6 },
  { vendor: "DataSync Partners", aggressivenessScore: 6.5, deviationCount: 3, avgDeviation: 1.8, topDeviations: [{ clause: "Non-Compete", deviation: 2.5 }, { clause: "Confidentiality", deviation: 2.0 }, { clause: "SLA", deviation: 1.5 }], trend: 2.0, contractsAnalyzed: 15 },
  { vendor: "CloudServ Ltd", aggressivenessScore: 5.2, deviationCount: 2, avgDeviation: 1.2, topDeviations: [{ clause: "SLA", deviation: 1.8 }, { clause: "Payment Terms", deviation: 1.0 }], trend: -1.5, contractsAnalyzed: 22 },
  { vendor: "InnoVate LLC", aggressivenessScore: 4.5, deviationCount: 1, avgDeviation: 0.8, topDeviations: [{ clause: "IP Ownership", deviation: 0.8 }], trend: -3.0, contractsAnalyzed: 8 },
  { vendor: "EuroLegal Partners", aggressivenessScore: 3.8, deviationCount: 0, avgDeviation: 0.2, topDeviations: [], trend: -5.5, contractsAnalyzed: 10 },
];

// ── Negotiation Intelligence ────────────────────────────────────────────────

export const negotiationIntel: NegotiationIntel[] = [
  { clauseType: "Liability Cap", leverageScore: 85, marketPosition: "Significantly above market (92nd percentile)", recommendedPosition: "Cap at 100% of fees with mutual exclusion for consequential damages", fallbackPositions: ["Cap at 200% of fees", "Cap at 150% with IP infringement exception", "Mutual uncapped for breach of confidentiality"], vendorFavorability: 92, confidence: 94 },
  { clauseType: "Indemnification", leverageScore: 78, marketPosition: "Above market (88th percentile)", recommendedPosition: "Mutual indemnification capped at liability limit with IP infringement exception", fallbackPositions: ["One-way indemnification capped at 100% fees", "Mutual with $500K cap", "Uncapped for IP and confidentiality"], vendorFavorability: 85, confidence: 91 },
  { clauseType: "Termination", leverageScore: 72, marketPosition: "Above market (76th percentile)", recommendedPosition: "Mutual 30-day for convenience, immediate for cause", fallbackPositions: ["60-day notice for convenience", "90-day for provider, 30-day for client", "For cause only with 30-day cure"], vendorFavorability: 76, confidence: 89 },
  { clauseType: "Auto-Renewal", leverageScore: 80, marketPosition: "Far above market (82nd percentile)", recommendedPosition: "60-day notice for non-renewal, automatic renewal with opt-out", fallbackPositions: ["90-day notice", "Manual renewal only", "30-day notice with auto-renewal"], vendorFavorability: 82, confidence: 86 },
  { clauseType: "IP Ownership", leverageScore: 75, marketPosition: "Above market (85th percentile)", recommendedPosition: "Client owns all IP developed under agreement", fallbackPositions: ["Joint ownership", "License to client for internal use", "IP assignment upon full payment"], vendorFavorability: 85, confidence: 88 },
];

// ── Compliance Benchmarks ───────────────────────────────────────────────────

export const complianceBenchmarks: ComplianceBenchmark[] = [
  { regulation: "GDPR", yourCoverage: 75, marketCoverage: 85, gap: -10, severity: "high", affectedClauses: ["Data Privacy", "Compliance", "DPA"] },
  { regulation: "CCPA", yourCoverage: 60, marketCoverage: 70, gap: -10, severity: "high", affectedClauses: ["Data Privacy", "Compliance"] },
  { regulation: "HIPAA", yourCoverage: 45, marketCoverage: 55, gap: -10, severity: "critical", affectedClauses: ["Confidentiality", "Data Privacy", "SLA"] },
  { regulation: "SOX", yourCoverage: 80, marketCoverage: 75, gap: 5, severity: "low", affectedClauses: ["Compliance", "Audit Rights"] },
  { regulation: "PCI-DSS", yourCoverage: 55, marketCoverage: 65, gap: -10, severity: "high", affectedClauses: ["Data Privacy", "SLA", "Insurance"] },
  { regulation: "FCRA", yourCoverage: 40, marketCoverage: 50, gap: -10, severity: "critical", affectedClauses: ["Compliance", "Data Privacy"] },
];

// ── Clause Library ──────────────────────────────────────────────────────────

export const clauseLibrary: ClauseLibrary[] = [
  { clauseType: "Indemnification", frequency: 95, trend: 2.1, riskScore: 7.5, industryStandard: "Mutual indemnification for IP infringement and breach of confidentiality", commonVariations: 12, lastUpdated: "2026-05-01" },
  { clauseType: "Confidentiality", frequency: 92, trend: 1.5, riskScore: 4.2, industryStandard: "Mutual confidentiality with 3-year survival, standard exclusions", commonVariations: 8, lastUpdated: "2026-04-15" },
  { clauseType: "Termination", frequency: 88, trend: -0.5, riskScore: 5.5, industryStandard: "Mutual termination for convenience (30-60 days) and for cause", commonVariations: 10, lastUpdated: "2026-05-10" },
  { clauseType: "Liability Cap", frequency: 85, trend: 3.2, riskScore: 8.0, industryStandard: "Cap at 100% of fees, mutual exclusion for consequential damages", commonVariations: 15, lastUpdated: "2026-05-05" },
  { clauseType: "Data Privacy", frequency: 78, trend: 8.5, riskScore: 6.8, industryStandard: "GDPR-compliant data processing terms with DPA reference", commonVariations: 18, lastUpdated: "2026-05-12" },
  { clauseType: "Force Majeure", frequency: 72, trend: 2.5, riskScore: 3.5, industryStandard: "Standard force majeure with pandemic coverage, 30-day notice", commonVariations: 6, lastUpdated: "2026-03-20" },
  { clauseType: "Auto-Renewal", frequency: 65, trend: 5.5, riskScore: 7.2, industryStandard: "Auto-renewal with 60-day notice period and opt-out", commonVariations: 8, lastUpdated: "2026-05-08" },
  { clauseType: "IP Ownership", frequency: 60, trend: 4.0, riskScore: 6.5, industryStandard: "Client owns all IP developed under agreement with license back", commonVariations: 14, lastUpdated: "2026-04-28" },
];

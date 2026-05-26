// ── Enterprise CFO Risk & Financial Exposure Dashboard Mock Data ─────────

import type {
  CfoKpi, FinancialExposure, RenewalForecast, VendorFinancialRisk,
  SlaFinancialImpact, RevenueLeakage, ProcurementSaving,
  AiFinancialInsight, FinancialAnalytics, FinancialDetail,
} from "./types";

// ── KPI Data ─────────────────────────────────────────────────────────────

export const mockCfoKpis: CfoKpi[] = [
  { id: "portfolio-value", label: "Total Contract Portfolio", value: "$847.2M", trend: 8.2, trendDirection: "up", icon: "DollarSign", color: "from-blue-500 to-blue-600", severity: "info", sparklineData: [720, 745, 768, 790, 820, 847.2], tooltip: "Total contract portfolio value across all active agreements" },
  { id: "exposure-risk", label: "Financial Exposure at Risk", value: "$124.8M", trend: 12, trendDirection: "up", icon: "AlertTriangle", color: "from-red-500 to-red-600", severity: "critical", sparklineData: [98, 105, 112, 118, 122, 124.8], tooltip: "Total financial exposure from high-risk clauses and obligations" },
  { id: "uncapped-liability", label: "Uncapped Liability Exposure", value: "$42.3M", trend: 22, trendDirection: "up", icon: "Gavel", color: "from-red-500 to-red-600", severity: "critical", sparklineData: [28, 32, 35, 38, 40, 42.3], tooltip: "Exposure from contracts with uncapped or unlimited liability clauses" },
  { id: "renewal-commitments", label: "Upcoming Renewal Commitments", value: "$156.2M", trend: 8, trendDirection: "up", icon: "RefreshCw", color: "from-amber-500 to-amber-600", severity: "warning", sparklineData: [120, 128, 138, 145, 150, 156.2], tooltip: "Total financial commitments from contracts renewing in next 90 days" },
  { id: "vendor-concentration", label: "Vendor Concentration Risk", value: "68.4%", trend: 5, trendDirection: "up", icon: "Building2", color: "from-orange-500 to-orange-600", severity: "warning", sparklineData: [58, 61, 63, 65, 67, 68.4], tooltip: "Percentage of spend concentrated in top 5 vendors" },
  { id: "revenue-leakage", label: "Revenue Leakage Risk", value: "$8.7M", trend: -15, trendDirection: "down", icon: "TrendingDown", color: "from-red-500 to-red-600", severity: "critical", sparklineData: [12.5, 11.8, 10.9, 10.1, 9.3, 8.7], tooltip: "Estimated annual revenue leakage from missed obligations and pricing gaps" },
  { id: "sla-penalties", label: "SLA Financial Penalties", value: "$2.4M", trend: -25, trendDirection: "down", icon: "Clock", color: "from-green-500 to-green-600", severity: "success", sparklineData: [4.2, 3.8, 3.4, 3.0, 2.7, 2.4], tooltip: "Accumulated SLA penalty exposure from vendor underperformance" },
  { id: "savings-opps", label: "Procurement Savings Opps", value: "$18.5M", trend: 14, trendDirection: "up", icon: "PiggyBank", color: "from-emerald-500 to-emerald-600", severity: "success", sparklineData: [12, 13.2, 14.8, 16.1, 17.3, 18.5], tooltip: "Identified procurement savings opportunities across vendor portfolio" },
];

// ── Financial Exposures ──────────────────────────────────────────────────

export const mockFinancialExposures: FinancialExposure[] = [
  { id: "exp-001", category: "liability", label: "Uncapped Liability Clauses", currentExposure: 42300000, projectedExposure: 52000000, riskLevel: "critical", contractCount: 18, vendorCount: 12, trend: 22, details: [
    { id: "ed-001", contractTitle: "MSA - Acme Corp", vendor: "Acme Corporation", amount: 8500000, riskLevel: "critical", clause: "Section 12.1 - Unlimited Liability", dueDate: "2026-12-31", status: "active" },
    { id: "ed-002", contractTitle: "SaaS Agreement - TechSphere", vendor: "TechSphere Inc", amount: 6200000, riskLevel: "critical", clause: "Section 14.2 - No Cap", dueDate: "2027-03-15", status: "active" },
    { id: "ed-003", contractTitle: "Cloud Services - CloudNexus", vendor: "CloudNexus", amount: 4800000, riskLevel: "high", clause: "Section 10.1 - IP Indemnification", dueDate: "2026-09-30", status: "active" },
  ]},
  { id: "exp-002", category: "renewal", label: "Upcoming Renewal Exposure", currentExposure: 156200000, projectedExposure: 172000000, riskLevel: "warning", contractCount: 24, vendorCount: 18, trend: 8, details: [
    { id: "ed-004", contractTitle: "Enterprise License - DataVault", vendor: "DataVault Systems", amount: 24000000, riskLevel: "high", clause: "Auto-Renewal", dueDate: "2026-08-01", status: "pending" },
    { id: "ed-005", contractTitle: "SaaS Platform - TechSphere", vendor: "TechSphere Inc", amount: 18500000, riskLevel: "medium", clause: "Termination Notice", dueDate: "2026-07-15", status: "pending" },
  ]},
  { id: "exp-003", category: "vendor", label: "Vendor Concentration Risk", currentExposure: 89200000, projectedExposure: 95000000, riskLevel: "warning", contractCount: 32, vendorCount: 5, trend: 5, details: []},
  { id: "exp-004", category: "operational", label: "SLA Penalty Exposure", currentExposure: 2400000, projectedExposure: 1800000, riskLevel: "low", contractCount: 8, vendorCount: 6, trend: -25, details: []},
  { id: "exp-005", category: "revenue", label: "Revenue Leakage", currentExposure: 8700000, projectedExposure: 6500000, riskLevel: "critical", contractCount: 22, vendorCount: 15, trend: -15, details: []},
  { id: "exp-006", category: "compliance", label: "Regulatory Penalty Exposure", currentExposure: 18500000, projectedExposure: 22000000, riskLevel: "high", contractCount: 28, vendorCount: 20, trend: 10, details: []},
];

// ── Renewal Forecasts ────────────────────────────────────────────────────

export const mockRenewalForecasts: RenewalForecast[] = [
  { id: "rf-001", contractTitle: "Enterprise License - DataVault Systems", vendor: "DataVault Systems", currentValue: 24000000, projectedValue: 28500000, renewalDate: "2026-08-01", riskLevel: "high", probability: 75, savingsOpportunity: 3200000, autoRenewal: true, noticeDeadline: "2026-06-01", status: "at_risk" },
  { id: "rf-002", contractTitle: "SaaS Platform - TechSphere Inc", vendor: "TechSphere Inc", currentValue: 18500000, projectedValue: 21000000, renewalDate: "2026-07-15", riskLevel: "medium", probability: 85, savingsOpportunity: 1800000, autoRenewal: false, noticeDeadline: "2026-05-15", status: "pending" },
  { id: "rf-003", contractTitle: "Cloud Infrastructure - CloudNexus", vendor: "CloudNexus", currentValue: 12000000, projectedValue: 14500000, renewalDate: "2026-09-30", riskLevel: "critical", probability: 60, savingsOpportunity: 2500000, autoRenewal: true, noticeDeadline: "2026-07-31", status: "at_risk" },
  { id: "rf-004", contractTitle: "MSA - Acme Corp", vendor: "Acme Corporation", currentValue: 32000000, projectedValue: 35000000, renewalDate: "2026-10-15", riskLevel: "low", probability: 92, savingsOpportunity: 1500000, autoRenewal: false, noticeDeadline: "2026-08-15", status: "on_track" },
  { id: "rf-005", contractTitle: "Security Suite - SecurePath Ltd", vendor: "SecurePath Ltd", currentValue: 8900000, projectedValue: 10200000, renewalDate: "2026-11-01", riskLevel: "medium", probability: 78, savingsOpportunity: 800000, autoRenewal: true, noticeDeadline: "2026-09-01", status: "pending" },
  { id: "rf-006", contractTitle: "Data Analytics - GlobalTech", vendor: "GlobalTech Partners", currentValue: 15000000, projectedValue: 12000000, renewalDate: "2026-12-01", riskLevel: "high", probability: 45, savingsOpportunity: 3500000, autoRenewal: false, noticeDeadline: "2026-10-01", status: "at_risk" },
];

// ── Vendor Financial Risks ───────────────────────────────────────────────

export const mockVendorFinancialRisks: VendorFinancialRisk[] = [
  { id: "vfr-001", vendorName: "TechSphere Inc", totalSpend: 42500000, contractCount: 8, riskScore: 82, riskLevel: "critical", concentration: 18.5, liabilityExposure: 12500000, slaPenalties: 850000, paymentTerms: "Net 30", dso: 42, trend: 12 },
  { id: "vfr-002", vendorName: "CloudNexus", totalSpend: 38500000, contractCount: 6, riskScore: 74, riskLevel: "high", concentration: 16.8, liabilityExposure: 9800000, slaPenalties: 620000, paymentTerms: "Net 45", dso: 38, trend: 8 },
  { id: "vfr-003", vendorName: "Acme Corporation", totalSpend: 52000000, contractCount: 12, riskScore: 35, riskLevel: "low", concentration: 22.6, liabilityExposure: 4200000, slaPenalties: 120000, paymentTerms: "Net 60", dso: 28, trend: -5 },
  { id: "vfr-004", vendorName: "DataVault Systems", totalSpend: 34000000, contractCount: 7, riskScore: 42, riskLevel: "medium", concentration: 14.8, liabilityExposure: 5600000, slaPenalties: 180000, paymentTerms: "Net 30", dso: 32, trend: 3 },
  { id: "vfr-005", vendorName: "SecurePath Ltd", totalSpend: 18000000, contractCount: 4, riskScore: 58, riskLevel: "medium", concentration: 7.8, liabilityExposure: 3800000, slaPenalties: 240000, paymentTerms: "Net 45", dso: 45, trend: 15 },
  { id: "vfr-006", vendorName: "GlobalTech Partners", totalSpend: 22000000, contractCount: 5, riskScore: 68, riskLevel: "high", concentration: 9.6, liabilityExposure: 7200000, slaPenalties: 410000, paymentTerms: "Net 30", dso: 52, trend: 20 },
];

// ── SLA Financial Impacts ────────────────────────────────────────────────

export const mockSlaImpacts: SlaFinancialImpact[] = [
  { id: "sla-001", contractTitle: "Cloud Infrastructure SLA", vendor: "CloudNexus", penaltyType: "Uptime Credit", penaltyAmount: 45000, incidentCount: 3, totalImpact: 135000, period: "Q2 2026", riskLevel: "high" },
  { id: "sla-002", contractTitle: "SaaS Platform - TechSphere", vendor: "TechSphere Inc", penaltyType: "Performance Credit", penaltyAmount: 28000, incidentCount: 5, totalImpact: 140000, period: "Q2 2026", riskLevel: "high" },
  { id: "sla-003", contractTitle: "Data Center Services", vendor: "DataVault Systems", penaltyType: "Availability Credit", penaltyAmount: 12000, incidentCount: 2, totalImpact: 24000, period: "Q2 2026", riskLevel: "medium" },
  { id: "sla-004", contractTitle: "Security Monitoring", vendor: "SecurePath Ltd", penaltyType: "Response Time", penaltyAmount: 8500, incidentCount: 4, totalImpact: 34000, period: "Q2 2026", riskLevel: "medium" },
  { id: "sla-005", contractTitle: "Enterprise Support", vendor: "Acme Corporation", penaltyType: "Resolution Time", penaltyAmount: 5000, incidentCount: 1, totalImpact: 5000, period: "Q2 2026", riskLevel: "low" },
];

// ── Revenue Leakage ──────────────────────────────────────────────────────

export const mockRevenueLeakage: RevenueLeakage[] = [
  { id: "rl-001", category: "Missed Billing", description: "Auto-renewal contracts not invoiced at escalated rates", estimatedLoss: 2800000, probability: 75, riskLevel: "critical", affectedContracts: 12, recoveryPotential: 1800000, recommendation: "Audit all auto-renewal contracts for correct pricing tier application" },
  { id: "rl-002", category: "Discount Leakage", description: "Legacy discount structures not aligned with current volume", estimatedLoss: 2100000, probability: 65, riskLevel: "high", affectedContracts: 18, recoveryPotential: 1400000, recommendation: "Review all contracts with discounts >25% for volume alignment" },
  { id: "rl-003", category: "Obligation Failures", description: "Unmet vendor obligations not triggering penalty clauses", estimatedLoss: 1800000, probability: 80, riskLevel: "critical", affectedContracts: 8, recoveryPotential: 1500000, recommendation: "Automate obligation monitoring and penalty enforcement" },
  { id: "rl-004", category: "Underutilization", description: "Licensed capacity significantly exceeding actual usage", estimatedLoss: 1200000, probability: 55, riskLevel: "medium", affectedContracts: 15, recoveryPotential: 900000, recommendation: "Right-size licensing based on actual usage analytics" },
  { id: "rl-005", category: "Pricing Inconsistency", description: "Same vendor, different pricing across business units", estimatedLoss: 800000, probability: 70, riskLevel: "medium", affectedContracts: 22, recoveryPotential: 600000, recommendation: "Standardize vendor pricing across all business units" },
];

// ── Procurement Savings ──────────────────────────────────────────────────

export const mockProcurementSavings: ProcurementSaving[] = [
  { id: "ps-001", category: "Vendor Consolidation", description: "Consolidate 3 telecom vendors to single provider", currentSpend: 5200000, projectedSpend: 3800000, savingsAmount: 1400000, savingsPercent: 27, confidence: 85, timeline: "6 months", vendorCount: 3 },
  { id: "ps-002", category: "Contract Renegotiation", description: "Renegotiate CloudNexus contract at market rates", currentSpend: 12000000, projectedSpend: 9500000, savingsAmount: 2500000, savingsPercent: 21, confidence: 72, timeline: "3 months", vendorCount: 1 },
  { id: "ps-003", category: "License Optimization", description: "Optimize Microsoft enterprise license allocation", currentSpend: 8500000, projectedSpend: 6800000, savingsAmount: 1700000, savingsPercent: 20, confidence: 90, timeline: "4 months", vendorCount: 1 },
  { id: "ps-004", category: "Bundled Procurement", description: "Bundle security services across business units", currentSpend: 4200000, projectedSpend: 3100000, savingsAmount: 1100000, savingsPercent: 26, confidence: 78, timeline: "8 months", vendorCount: 4 },
  { id: "ps-005", category: "Payment Terms Optimization", description: "Negotiate early payment discounts with top vendors", currentSpend: 45000000, projectedSpend: 43200000, savingsAmount: 1800000, savingsPercent: 4, confidence: 95, timeline: "2 months", vendorCount: 6 },
];

// ── AI Financial Insights ────────────────────────────────────────────────

export const mockAiFinancialInsights: AiFinancialInsight[] = [
  { id: "afi-001", type: "exposure", title: "Uncapped Liability Exposure Increased 22%", description: "AI analysis detected 18 contracts with uncapped liability clauses totaling $42.3M exposure. This represents a 22% increase from last quarter, driven by 3 new agreements with unlimited IP indemnification.", severity: "critical", confidence: 94, financialImpact: 42300000, impactedContracts: 18, impactedVendors: 12, recommendedAction: "Prioritize negotiation of liability caps on the 3 highest-exposure contracts. Target $25M aggregate cap with standard carve-outs." },
  { id: "afi-002", type: "forecast", title: "Q3 Renewal Exposure: $156.2M at Risk", description: "24 contracts renewing in Q3 with total commitments of $156.2M. CloudNexus and TechSphere renewals represent 38% of exposure and have below-average renewal probability.", severity: "warning", confidence: 88, financialImpact: 156200000, impactedContracts: 24, impactedVendors: 18, recommendedAction: "Initiate renewal negotiations for CloudNexus and TechSphere immediately. Target 15% savings on combined $30.5M spend." },
  { id: "afi-003", type: "anomaly", title: "Vendor Concentration Exceeds Threshold", description: "Top 5 vendors now represent 68.4% of total contract spend, exceeding the 65% board-mandated threshold. TechSphere and CloudNexus concentration growing fastest.", severity: "warning", confidence: 92, financialImpact: 89200000, impactedContracts: 32, impactedVendors: 5, recommendedAction: "Implement vendor diversification plan. Identify alternative suppliers for at least 15% of TechSphere and CloudNexus spend." },
  { id: "afi-004", type: "savings", title: "$18.5M Procurement Savings Identified", description: "AI identified 5 high-confidence savings opportunities across vendor consolidation, contract renegotiation, and license optimization. Average confidence: 84%.", severity: "success", confidence: 91, financialImpact: 18500000, impactedContracts: 28, impactedVendors: 15, recommendedAction: "Prioritize CloudNexus renegotiation ($2.5M savings) and Microsoft license optimization ($1.7M savings) for immediate action." },
  { id: "afi-005", type: "risk", title: "Revenue Leakage: $8.7M Annual Risk", description: "Missed billing opportunities and discount leakage represent $8.7M in annual revenue leakage. Auto-renewal pricing gaps are the largest contributor at $2.8M.", severity: "critical", confidence: 86, financialImpact: 8700000, impactedContracts: 22, impactedVendors: 15, recommendedAction: "Audit all auto-renewal contracts for correct pricing. Implement automated obligation monitoring to capture penalty opportunities." },
  { id: "afi-006", type: "recommendation", title: "SLA Penalty Recovery Opportunity", description: "Current SLA penalty recovery rate is 62%. AI estimates $900K in unclaimed penalties from Q2 2026. CloudNexus and TechSphere have the highest unclaimed amounts.", severity: "info", confidence: 82, financialImpact: 900000, impactedContracts: 8, impactedVendors: 4, recommendedAction: "Implement automated SLA monitoring and penalty claiming process. Target 90% recovery rate by Q4." },
];

// ── Financial Analytics ──────────────────────────────────────────────────

export const mockFinancialAnalytics: FinancialAnalytics = {
  totalPortfolioValue: 847200000,
  totalExposure: 124800000,
  uncappedLiability: 42300000,
  upcomingRenewals: 156200000,
  vendorConcentration: 68.4,
  revenueLeakage: 8700000,
  slaPenalties: 2400000,
  savingsOpportunities: 18500000,
  exposureByCategory: [
    { category: "Liability", amount: 42300000 },
    { category: "Renewal", amount: 156200000 },
    { category: "Vendor Concentration", amount: 89200000 },
    { category: "Operational", amount: 2400000 },
    { category: "Revenue Leakage", amount: 8700000 },
    { category: "Compliance", amount: 18500000 },
  ],
  exposureTrend: [
    { date: "Jan", amount: 98 }, { date: "Feb", amount: 105 },
    { date: "Mar", amount: 112 }, { date: "Apr", amount: 118 },
    { date: "May", amount: 122 }, { date: "Jun", amount: 124.8 },
  ],
  renewalForecast: [
    { period: "Q3 2026", amount: 156.2, probability: 72 },
    { period: "Q4 2026", amount: 98.5, probability: 65 },
    { period: "Q1 2027", amount: 142.8, probability: 58 },
    { period: "Q2 2027", amount: 112.4, probability: 70 },
  ],
  vendorConcentrationData: [
    { vendor: "Acme Corp", spend: 52 },
    { vendor: "TechSphere", spend: 42.5 },
    { vendor: "CloudNexus", spend: 38.5 },
    { vendor: "DataVault", spend: 34 },
    { vendor: "GlobalTech", spend: 22 },
    { vendor: "SecurePath", spend: 18 },
    { vendor: "Others", spend: 22.2 },
  ],
  businessUnitExposure: [
    { unit: "Enterprise Tech", exposure: 48.2, contracts: 145 },
    { unit: "Financial Services", exposure: 32.5, contracts: 98 },
    { unit: "Healthcare", exposure: 22.8, contracts: 67 },
    { unit: "Manufacturing", exposure: 12.3, contracts: 42 },
    { unit: "Retail", exposure: 9.0, contracts: 28 },
  ],
  regionalExposure: [
    { region: "North America", exposure: 68.4 },
    { region: "Europe", exposure: 28.2 },
    { region: "Asia Pacific", exposure: 15.6 },
    { region: "Latin America", exposure: 8.2 },
    { region: "Middle East", exposure: 4.4 },
  ],
  savingsTrend: [
    { date: "Q1 2025", identified: 12.5, realized: 8.2 },
    { date: "Q2 2025", identified: 14.8, realized: 10.5 },
    { date: "Q3 2025", identified: 16.2, realized: 12.8 },
    { date: "Q4 2025", identified: 18.5, realized: 14.2 },
    { date: "Q1 2026", identified: 20.1, realized: 16.5 },
    { date: "Q2 2026", identified: 18.5, realized: 15.8 },
  ],
  forecastAccuracy: [
    { period: "Q1 2025", predicted: 92, actual: 88 },
    { period: "Q2 2025", predicted: 95, actual: 91 },
    { period: "Q3 2025", predicted: 98, actual: 94 },
    { period: "Q4 2025", predicted: 102, actual: 97 },
    { period: "Q1 2026", predicted: 105, actual: 101 },
  ],
};

// ── Financial Detail ─────────────────────────────────────────────────────

export const mockFinancialDetail: FinancialDetail = {
  overview: {
    title: "Uncapped Liability Exposure",
    category: "Liability",
    currentExposure: 42300000,
    projectedExposure: 52000000,
    riskLevel: "critical",
    contractCount: 18,
    vendorCount: 12,
  },
  exposureAnalysis: [
    { item: "IP Indemnification", amount: 18500000, risk: "critical" },
    { item: "Confidentiality Breach", amount: 12400000, risk: "critical" },
    { item: "Data Protection", amount: 8200000, risk: "high" },
    { item: "Service Performance", amount: 3200000, risk: "medium" },
  ],
  forecasting: [
    { period: "Q3 2026", projected: 48.5, confidence: 85 },
    { period: "Q4 2026", projected: 52.0, confidence: 78 },
    { period: "Q1 2027", projected: 55.2, confidence: 72 },
    { period: "Q2 2027", projected: 58.8, confidence: 65 },
  ],
  vendorImpact: [
    { vendor: "TechSphere Inc", exposure: 12500000, contracts: 8 },
    { vendor: "CloudNexus", exposure: 9800000, contracts: 6 },
    { vendor: "Acme Corporation", exposure: 4200000, contracts: 12 },
    { vendor: "GlobalTech Partners", exposure: 7200000, contracts: 5 },
  ],
  obligations: [
    { title: "Liability Cap Negotiation - TechSphere", amount: 6200000, dueDate: "2026-08-15", status: "pending" },
    { title: "IP Indemnification Review - CloudNexus", amount: 4800000, dueDate: "2026-07-01", status: "in_progress" },
    { title: "Data Protection Amendment - Acme", amount: 2800000, dueDate: "2026-09-30", status: "overdue" },
  ],
  aiInsights: mockAiFinancialInsights.slice(0, 3),
  trends: [
    { date: "Jan", value: 28 }, { date: "Feb", value: 32 },
    { date: "Mar", value: 35 }, { date: "Apr", value: 38 },
    { date: "May", value: 40 }, { date: "Jun", value: 42.3 },
  ],
  auditHistory: [
    { action: "Financial exposure analysis completed", user: "AI System", timestamp: "2026-05-15T10:00:00Z" },
    { action: "Uncapped liability threshold breached", user: "AI System", timestamp: "2026-05-12T14:00:00Z" },
    { action: "Board report generated - Q2 exposure", user: "Sarah Chen", timestamp: "2026-05-10T09:00:00Z" },
    { action: "Vendor concentration review initiated", user: "Emily Nakamura", timestamp: "2026-05-08T11:00:00Z" },
    { action: "Renewal forecast updated - CloudNexus", user: "Michael Torres", timestamp: "2026-05-05T16:00:00Z" },
  ],
};

// ── Enterprise Analytics Mock Data ──────────────────────────────────────────

import type { AnalyticsKpi, ExecutiveInsight, RiskTrend, DepartmentAnalytics, VendorAnalytics, ComplianceAnalytics, ForecastPoint, ReportTemplate, LegalOpsMetric } from "./types";

function rand(min: number, max: number) { return Math.floor(Math.random() * (max - min + 1)) + min; }

// ── KPI Metrics ─────────────────────────────────────────────────────────────

export const analyticsKpis: AnalyticsKpi[] = [
  { id: "portfolio-value", label: "Total Portfolio Value", value: "$142.8M", trend: 12.3, trendDirection: "up", icon: "DollarSign", color: "from-green-500 to-emerald-500", severity: "success", sparklineData: [98, 105, 112, 118, 125, 132, 138, 142.8], tooltip: "Total value of all active contracts" },
  { id: "risk-exposure", label: "Enterprise Risk Exposure", value: "$18.4M", trend: 8.2, trendDirection: "up", icon: "AlertTriangle", color: "from-red-500 to-orange-500", severity: "critical", sparklineData: [14.2, 15.0, 15.8, 16.2, 16.9, 17.5, 18.1, 18.4], tooltip: "Total financial exposure from high-risk contracts" },
  { id: "savings", label: "Procurement Savings", value: "$4.2M", trend: 23.5, trendDirection: "up", icon: "TrendingDown", color: "from-green-500 to-teal-500", severity: "success", sparklineData: [2.1, 2.5, 2.8, 3.1, 3.4, 3.7, 4.0, 4.2], tooltip: "Total procurement savings realized YTD" },
  { id: "concentration", label: "Vendor Concentration", value: "42%", trend: 3.1, trendDirection: "up", icon: "PieChart", color: "from-orange-500 to-red-500", severity: "warning", sparklineData: [36, 37, 38, 39, 40, 41, 41, 42], tooltip: "Percentage of spend in top 5 vendors" },
  { id: "compliance", label: "Compliance Score", value: "92%", trend: 4.5, trendDirection: "up", icon: "Shield", color: "from-blue-500 to-indigo-500", severity: "success", sparklineData: [84, 86, 87, 88, 89, 90, 91, 92], tooltip: "Overall enterprise compliance score" },
  { id: "cycle-time", label: "Avg Negotiation Cycle", value: "18.5d", trend: -12.4, trendDirection: "down", icon: "Zap", color: "from-cyan-500 to-blue-500", severity: "success", sparklineData: [24, 23, 22, 21, 20, 19.5, 19, 18.5], tooltip: "Average days from draft to signature" },
  { id: "ai-accuracy", label: "AI Detection Accuracy", value: "94.2%", trend: 2.1, trendDirection: "up", icon: "Brain", color: "from-purple-500 to-pink-500", severity: "success", sparklineData: [88, 89, 90, 91, 92, 93, 93.5, 94.2], tooltip: "AI model accuracy across all detection categories" },
  { id: "fulfillment", label: "Obligations Fulfillment", value: "87%", trend: 5.7, trendDirection: "up", icon: "ClipboardCheck", color: "from-teal-500 to-green-500", severity: "success", sparklineData: [78, 80, 81, 82, 83, 85, 86, 87], tooltip: "Percentage of obligations fulfilled on time" },
];

// ── Risk Trends ─────────────────────────────────────────────────────────────

export const riskTrendData: RiskTrend[] = [
  { month: "Dec", critical: 8, high: 42, medium: 58, low: 120, totalExposure: 14.2 },
  { month: "Jan", critical: 9, high: 45, medium: 55, low: 118, totalExposure: 15.0 },
  { month: "Feb", critical: 10, high: 48, medium: 60, low: 115, totalExposure: 15.8 },
  { month: "Mar", critical: 11, high: 50, medium: 62, low: 112, totalExposure: 16.2 },
  { month: "Apr", critical: 12, high: 52, medium: 63, low: 120, totalExposure: 16.9 },
  { month: "May", critical: 11, high: 47, medium: 62, low: 128, totalExposure: 18.4 },
];

// ── Department Analytics ────────────────────────────────────────────────────

export const departmentAnalytics: DepartmentAnalytics[] = [
  { department: "Engineering", contracts: 85, avgRisk: 6.8, highRiskCount: 18, exposure: 5.2, cycleTime: 22, complianceScore: 88, slaScore: 92 },
  { department: "Marketing", contracts: 42, avgRisk: 4.2, highRiskCount: 5, exposure: 2.1, cycleTime: 14, complianceScore: 95, slaScore: 98 },
  { department: "Finance", contracts: 38, avgRisk: 5.5, highRiskCount: 8, exposure: 3.4, cycleTime: 28, complianceScore: 90, slaScore: 85 },
  { department: "Operations", contracts: 55, avgRisk: 7.2, highRiskCount: 14, exposure: 4.8, cycleTime: 20, complianceScore: 82, slaScore: 78 },
  { department: "Sales", contracts: 48, avgRisk: 5.8, highRiskCount: 7, exposure: 2.9, cycleTime: 12, complianceScore: 85, slaScore: 90 },
  { department: "Legal", contracts: 25, avgRisk: 3.5, highRiskCount: 2, exposure: 0.8, cycleTime: 35, complianceScore: 98, slaScore: 95 },
  { department: "HR", contracts: 30, avgRisk: 4.8, highRiskCount: 4, exposure: 1.5, cycleTime: 16, complianceScore: 92, slaScore: 88 },
  { department: "IT", contracts: 62, avgRisk: 6.2, highRiskCount: 12, exposure: 3.8, cycleTime: 18, complianceScore: 86, slaScore: 82 },
];

// ── Vendor Analytics ────────────────────────────────────────────────────────

export const vendorAnalytics: VendorAnalytics[] = [
  { vendor: "Acme Corp", totalSpend: 5.2, contracts: 24, avgRisk: 8.2, slaScore: 92, savings: 0.8, complianceScore: 88, trend: 12 },
  { vendor: "GlobalTech Inc", totalSpend: 3.8, contracts: 18, avgRisk: 7.5, slaScore: 85, savings: 0.5, complianceScore: 82, trend: 8 },
  { vendor: "SecureNet Solutions", totalSpend: 3.5, contracts: 12, avgRisk: 8.8, slaScore: 72, savings: 0.3, complianceScore: 65, trend: 15 },
  { vendor: "CloudServ Ltd", totalSpend: 4.1, contracts: 22, avgRisk: 5.2, slaScore: 98, savings: 1.2, complianceScore: 94, trend: -3 },
  { vendor: "DataSync Partners", totalSpend: 2.9, contracts: 15, avgRisk: 6.8, slaScore: 88, savings: 0.6, complianceScore: 85, trend: 5 },
  { vendor: "InnoVate LLC", totalSpend: 1.8, contracts: 8, avgRisk: 4.5, slaScore: 95, savings: 0.4, complianceScore: 92, trend: -8 },
  { vendor: "Pacific Rim Trading", totalSpend: 2.2, contracts: 6, avgRisk: 7.2, slaScore: 78, savings: 0.2, complianceScore: 72, trend: 10 },
  { vendor: "EuroLegal Partners", totalSpend: 1.5, contracts: 10, avgRisk: 3.8, slaScore: 96, savings: 0.2, complianceScore: 96, trend: -12 },
];

// ── Executive Insights ──────────────────────────────────────────────────────

export const executiveInsights: ExecutiveInsight[] = [
  { id: "ei-1", title: "Portfolio Exposure Increased 14%", description: "Enterprise risk exposure has grown from $16.2M to $18.4M this quarter, driven primarily by SecureNet Solutions and Acme Corp contracts with uncapped liability clauses.", severity: "critical", confidence: 94, businessImpact: "$2.2M increase in at-risk contract value", affectedEntities: ["SecureNet Solutions", "Acme Corp", "GlobalTech Inc"], recommendedAction: "Prioritize remediation of uncapped liability clauses. Target $4M reduction in exposure by Q3.", category: "risk", quickActions: [{ label: "View Exposure", action: "view" }, { label: "Generate Report", action: "report" }] },
  { id: "ei-2", title: "Vendor Concentration Risk Identified", description: "Cloud services spend concentration has reached 62% in top 2 vendors. Single point of failure risk for critical infrastructure detected.", severity: "warning", confidence: 88, businessImpact: "Potential $8.2M service disruption exposure", affectedEntities: ["CloudServ Ltd", "Horizon Cloud"], recommendedAction: "Develop multi-vendor cloud strategy. Target max 40% concentration per vendor.", category: "vendor", quickActions: [{ label: "Concentration Analysis", action: "analysis" }, { label: "Risk Assessment", action: "assessment" }] },
  { id: "ei-3", title: "Negotiation Cycle Efficiency Improved 22%", description: "Average negotiation cycle reduced from 24 days to 18.5 days through AI-assisted redlining and clause library adoption. Annualized savings: $340K in legal costs.", severity: "success", confidence: 91, businessImpact: "$340K annual legal cost savings", affectedEntities: ["Legal Team", "Procurement Team"], recommendedAction: "Continue AI clause recommendation adoption. Target 15-day cycle by Q4.", category: "operations", quickActions: [{ label: "View Metrics", action: "metrics" }, { label: "Share Report", action: "share" }] },
  { id: "ei-4", title: "Compliance Gaps in APAC Contracts", description: "15 contracts with APAC counterparties lack adequate data privacy clauses. Singapore and Japan contracts show highest gap rate at 35%.", severity: "warning", confidence: 86, businessImpact: "Regulatory fine exposure up to $4.2M", affectedEntities: ["Pacific Rim Trading", "DataSync Partners"], recommendedAction: "Prioritize APAC contract review. Add GDPR-equivalent clauses for Singapore and Japan.", category: "compliance", quickActions: [{ label: "View Gaps", action: "gaps" }, { label: "Compliance Report", action: "report" }] },
  { id: "ei-5", title: "AI Risk Detection Now at 94.2% Accuracy", description: "AI model accuracy has improved 2.1% this quarter. False positive rate reduced to 3.8%. Top performing category: liability detection at 97%.", severity: "success", confidence: 95, businessImpact: "Improved risk coverage across 12 categories", affectedEntities: ["All Contracts"], recommendedAction: "Deploy updated model to production. Monitor confidence calibration.", category: "ai", quickActions: [{ label: "Model Performance", action: "performance" }, { label: "Accuracy Report", action: "report" }] },
  { id: "ei-6", title: "Q3 Renewal Forecast: $12.5M at Risk", description: "18 contracts worth $12.5M are renewing in Q3. 8 have auto-renewal clauses that may trigger unfavorable terms if not addressed.", severity: "warning", confidence: 82, businessImpact: "$12.5M renewal exposure", affectedEntities: ["Acme Corp", "CloudServ Ltd", "DataSync Partners", "InnoVate LLC", "EuroLegal Partners"], recommendedAction: "Begin renewal negotiations 90 days before expiry. Prioritize auto-renewal contracts.", category: "renewal", quickActions: [{ label: "Renewal Calendar", action: "calendar" }, { label: "Strategy Session", action: "strategy" }] },
];

// ── Compliance Analytics ────────────────────────────────────────────────────

export const complianceAnalytics: ComplianceAnalytics[] = [
  { standard: "SOC 2 Type II", score: 94, marketAvg: 88, gap: 6, status: "compliant", trend: 2 },
  { standard: "GDPR", score: 91, marketAvg: 82, gap: 9, status: "compliant", trend: 4 },
  { standard: "HIPAA", score: 72, marketAvg: 68, gap: 4, status: "in_progress", trend: 8 },
  { standard: "ISO 27001", score: 96, marketAvg: 85, gap: 11, status: "compliant", trend: 1 },
  { standard: "CCPA", score: 58, marketAvg: 62, gap: -4, status: "non_compliant", trend: -5 },
  { standard: "PCI-DSS", score: 65, marketAvg: 70, gap: -5, status: "non_compliant", trend: 3 },
];

// ── Forecast Data ───────────────────────────────────────────────────────────

export const forecastData: ForecastPoint[] = [
  { period: "May", actual: 18.4, forecast: 18.4, upperBound: 19.2, lowerBound: 17.6 },
  { period: "Jun", actual: 0, forecast: 19.1, upperBound: 20.5, lowerBound: 17.8 },
  { period: "Jul", actual: 0, forecast: 19.8, upperBound: 21.5, lowerBound: 18.2 },
  { period: "Aug", actual: 0, forecast: 20.2, upperBound: 22.0, lowerBound: 18.5 },
  { period: "Sep", actual: 0, forecast: 20.8, upperBound: 22.8, lowerBound: 18.8 },
  { period: "Oct", actual: 0, forecast: 21.2, upperBound: 23.5, lowerBound: 19.0 },
];

// ── Report Templates ────────────────────────────────────────────────────────

export const reportTemplates: ReportTemplate[] = [
  { id: "rt-1", name: "Executive Risk Summary", description: "Board-ready risk exposure and portfolio health report", category: "Executive", charts: ["risk_trend", "exposure_breakdown", "vendor_risk"], sections: ["Executive Summary", "Risk Analysis", "Vendor Intelligence", "Recommendations"], lastGenerated: "2026-05-14", format: "PDF" },
  { id: "rt-2", name: "Quarterly Compliance Report", description: "Compliance status across all regulatory standards", category: "Compliance", charts: ["compliance_heatmap", "gap_analysis", "trend_comparison"], sections: ["Compliance Overview", "Gap Analysis", "Remediation Plan"], lastGenerated: "2026-04-30", format: "PDF" },
  { id: "rt-3", name: "Procurement Intelligence Report", description: "Vendor performance, savings, and spend analytics", category: "Procurement", charts: ["spend_trend", "vendor_ranking", "savings_waterfall"], sections: ["Spend Analysis", "Vendor Performance", "Savings Opportunities"], lastGenerated: "2026-05-10", format: "Excel" },
  { id: "rt-4", name: "Legal Operations Dashboard", description: "Workflow efficiency, cycle times, and team performance", category: "Legal", charts: ["cycle_time", "workload_distribution", "bottleneck_analysis"], sections: ["Operations Overview", "Team Performance", "Bottleneck Analysis"], lastGenerated: "2026-05-12", format: "PDF" },
  { id: "rt-5", name: "Board Presentation Pack", description: "Executive summary with key metrics and strategic recommendations", category: "Executive", charts: ["portfolio_health", "risk_heatmap", "forecast_trend"], sections: ["Portfolio Overview", "Risk Intelligence", "Strategic Recommendations", "Financial Impact"], lastGenerated: "2026-05-01", format: "PowerPoint" },
];

// ── Legal Ops Metrics ───────────────────────────────────────────────────────

export const legalOpsMetrics: LegalOpsMetric[] = [
  { metric: "Avg Approval Cycle", value: "4.2 days", trend: -12.5, trendDir: "down", benchmark: "3.0 days" },
  { metric: "Negotiation Success Rate", value: "87%", trend: 4.8, trendDir: "up", benchmark: "82%" },
  { metric: "Clause Reuse Rate", value: "72%", trend: 5.9, trendDir: "up", benchmark: "65%" },
  { metric: "SLA Compliance", value: "94%", trend: 2.1, trendDir: "up", benchmark: "90%" },
  { metric: "Active Workflows", value: "24", trend: 14.3, trendDir: "up", benchmark: "18" },
  { metric: "Escalation Rate", value: "8.3%", trend: -5.2, trendDir: "down", benchmark: "10%" },
];

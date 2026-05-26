// ── Enterprise Mock Data for Portfolio Dashboard ──────────────────────────

import type {
  KpiMetric, RiskTrendPoint, MonthlyExposure, VendorRisk,
  ClauseCategoryRisk, DepartmentRisk, AiInsight, PortfolioContract,
  FinancialExposure, WorkflowAlert,
} from "./types";

// ── KPI Metrics ─────────────────────────────────────────────────────────────

export const kpiMetrics: KpiMetric[] = [
  {
    id: "tcv-risk",
    label: "Total Contract Value at Risk",
    value: "$18.4M",
    trend: 12.5,
    trendDirection: "up",
    icon: "DollarSign",
    color: "from-red-500 to-orange-500",
    severity: "critical",
    sparklineData: [12, 14, 13, 15, 16, 14, 17, 18.4],
    tooltip: "Sum of all contract values flagged with high or critical risk",
  },
  {
    id: "high-risk-count",
    label: "High-Risk Contracts",
    value: "47",
    trend: 8.3,
    trendDirection: "up",
    icon: "AlertTriangle",
    color: "from-orange-500 to-red-500",
    severity: "critical",
    sparklineData: [32, 35, 33, 38, 40, 42, 45, 47],
    tooltip: "Contracts with risk score ≥ 7",
  },
  {
    id: "expiring-90",
    label: "Expiring in 90 Days",
    value: "23",
    trend: -5.2,
    trendDirection: "down",
    icon: "Clock",
    color: "from-yellow-500 to-orange-500",
    severity: "warning",
    sparklineData: [28, 27, 25, 26, 24, 23, 22, 23],
    tooltip: "Contracts expiring within the next 90 calendar days",
  },
  {
    id: "auto-renew",
    label: "Auto-Renewal Exposure",
    value: "$6.2M",
    trend: 3.1,
    trendDirection: "up",
    icon: "RefreshCw",
    color: "from-yellow-500 to-amber-500",
    severity: "warning",
    sparklineData: [5.1, 5.3, 5.5, 5.8, 5.9, 6.0, 6.1, 6.2],
    tooltip: "Total value of contracts with auto-renewal clauses that may renew unfavorably",
  },
  {
    id: "ai-accuracy",
    label: "AI Detection Accuracy",
    value: "94.2%",
    trend: 2.1,
    trendDirection: "up",
    icon: "Brain",
    color: "from-green-500 to-emerald-500",
    severity: "success",
    sparklineData: [88, 89, 90, 91, 92, 93, 93.5, 94.2],
    tooltip: "AI model accuracy for risk detection across all analyzed clauses",
  },
  {
    id: "escalations",
    label: "Open Legal Escalations",
    value: "12",
    trend: -15.8,
    trendDirection: "down",
    icon: "Scale",
    color: "from-orange-500 to-yellow-500",
    severity: "warning",
    sparklineData: [18, 17, 16, 15, 14, 13, 13, 12],
    tooltip: "Active escalations pending legal review",
  },
  {
    id: "sla-violations",
    label: "SLA Violations",
    value: "8",
    trend: -33.3,
    trendDirection: "down",
    icon: "AlertOctagon",
    color: "from-red-500 to-rose-500",
    severity: "critical",
    sparklineData: [14, 13, 12, 11, 10, 9, 9, 8],
    tooltip: "Contracts with SLA breaches in the current period",
  },
  {
    id: "obligations-due",
    label: "Obligations Due",
    value: "156",
    trend: 22.4,
    trendDirection: "up",
    icon: "ClipboardCheck",
    color: "from-blue-500 to-indigo-500",
    severity: "info",
    sparklineData: [98, 105, 112, 118, 125, 134, 145, 156],
    tooltip: "Total contractual obligations due this month across all active contracts",
  },
];

// ── Risk Trends (12 months) ────────────────────────────────────────────────

export const riskTrendData: RiskTrendPoint[] = [
  { date: "Jun", high: 42, medium: 58, low: 120, critical: 8, total: 228 },
  { date: "Jul", high: 45, medium: 55, low: 118, critical: 9, total: 227 },
  { date: "Aug", high: 48, medium: 60, low: 115, critical: 10, total: 233 },
  { date: "Sep", high: 50, medium: 62, low: 112, critical: 11, total: 235 },
  { date: "Oct", high: 47, medium: 58, low: 125, critical: 10, total: 240 },
  { date: "Nov", high: 52, medium: 63, low: 120, critical: 12, total: 247 },
  { date: "Dec", high: 55, medium: 65, low: 118, critical: 13, total: 251 },
  { date: "Jan", high: 58, medium: 68, low: 115, critical: 14, total: 255 },
  { date: "Feb", high: 53, medium: 64, low: 122, critical: 12, total: 251 },
  { date: "Mar", high: 56, medium: 66, low: 119, critical: 13, total: 254 },
  { date: "Apr", high: 60, medium: 70, low: 116, critical: 15, total: 261 },
  { date: "May", high: 47, medium: 62, low: 128, critical: 11, total: 248 },
];

// ── Monthly Exposure ───────────────────────────────────────────────────────

export const monthlyExposureData: MonthlyExposure[] = [
  { month: "Jan", exposure: 14.2, liability: 8.1, insured: 6.1 },
  { month: "Feb", exposure: 15.0, liability: 8.5, insured: 6.5 },
  { month: "Mar", exposure: 16.1, liability: 9.2, insured: 6.9 },
  { month: "Apr", exposure: 17.5, liability: 10.0, insured: 7.5 },
  { month: "May", exposure: 18.4, liability: 10.8, insured: 7.6 },
];

// ── Vendor Risk Distribution ───────────────────────────────────────────────

export const vendorRiskData: VendorRisk[] = [
  { vendor: "Acme Corp", contracts: 24, avgRiskScore: 8.2, totalExposure: 4.2, trend: 12 },
  { vendor: "GlobalTech Inc", contracts: 18, avgRiskScore: 7.5, totalExposure: 3.8, trend: 8 },
  { vendor: "DataSync Partners", contracts: 15, avgRiskScore: 6.8, totalExposure: 2.9, trend: -3 },
  { vendor: "CloudServ Ltd", contracts: 22, avgRiskScore: 5.2, totalExposure: 2.1, trend: -8 },
  { vendor: "SecureNet Solutions", contracts: 12, avgRiskScore: 8.8, totalExposure: 3.5, trend: 15 },
  { vendor: "InnoVate LLC", contracts: 8, avgRiskScore: 4.5, totalExposure: 1.2, trend: -12 },
  { vendor: "Pacific Rim Trading", contracts: 6, avgRiskScore: 7.2, totalExposure: 2.8, trend: 5 },
  { vendor: "EuroLegal Partners", contracts: 10, avgRiskScore: 3.8, totalExposure: 0.9, trend: -20 },
];

// ── Clause Category Heatmap ────────────────────────────────────────────────

export const clauseCategoryData: ClauseCategoryRisk[] = [
  { category: "Indemnification", highRiskCount: 28, mediumRiskCount: 35, lowRiskCount: 12, totalCount: 75, avgSeverity: 8.2 },
  { category: "Liability Cap", highRiskCount: 22, mediumRiskCount: 30, lowRiskCount: 18, totalCount: 70, avgSeverity: 7.8 },
  { category: "Termination", highRiskCount: 15, mediumRiskCount: 40, lowRiskCount: 25, totalCount: 80, avgSeverity: 6.5 },
  { category: "Confidentiality", highRiskCount: 10, mediumRiskCount: 25, lowRiskCount: 45, totalCount: 80, avgSeverity: 5.2 },
  { category: "Data Privacy", highRiskCount: 18, mediumRiskCount: 22, lowRiskCount: 30, totalCount: 70, avgSeverity: 7.1 },
  { category: "Compliance", highRiskCount: 20, mediumRiskCount: 28, lowRiskCount: 22, totalCount: 70, avgSeverity: 7.5 },
  { category: "Payment Terms", highRiskCount: 12, mediumRiskCount: 32, lowRiskCount: 36, totalCount: 80, avgSeverity: 5.8 },
  { category: "Force Majeure", highRiskCount: 8, mediumRiskCount: 18, lowRiskCount: 24, totalCount: 50, avgSeverity: 4.5 },
  { category: "Assignment", highRiskCount: 6, mediumRiskCount: 15, lowRiskCount: 19, totalCount: 40, avgSeverity: 4.2 },
  { category: "Governing Law", highRiskCount: 14, mediumRiskCount: 20, lowRiskCount: 16, totalCount: 50, avgSeverity: 6.8 },
  { category: "Non-Compete", highRiskCount: 10, mediumRiskCount: 12, lowRiskCount: 8, totalCount: 30, avgSeverity: 7.0 },
  { category: "IP Ownership", highRiskCount: 16, mediumRiskCount: 24, lowRiskCount: 20, totalCount: 60, avgSeverity: 7.3 },
];

// ── Department Risk ────────────────────────────────────────────────────────

export const departmentRiskData: DepartmentRisk[] = [
  { department: "Engineering", contracts: 85, avgRisk: 6.8, highRiskCount: 18, exposure: 5.2 },
  { department: "Marketing", contracts: 42, avgRisk: 4.2, highRiskCount: 5, exposure: 2.1 },
  { department: "Finance", contracts: 38, avgRisk: 5.5, highRiskCount: 8, exposure: 3.4 },
  { department: "Operations", contracts: 55, avgRisk: 7.2, highRiskCount: 14, exposure: 4.8 },
  { department: "Sales", contracts: 48, avgRisk: 5.8, highRiskCount: 7, exposure: 2.9 },
  { department: "Legal", contracts: 25, avgRisk: 3.5, highRiskCount: 2, exposure: 0.8 },
  { department: "HR", contracts: 30, avgRisk: 4.8, highRiskCount: 4, exposure: 1.5 },
  { department: "IT", contracts: 62, avgRisk: 6.2, highRiskCount: 12, exposure: 3.8 },
];

// ── AI Insights ────────────────────────────────────────────────────────────

export const aiInsights: AiInsight[] = [
  {
    id: "insight-1",
    title: "Uncapped Liability Detected",
    description: "12 contracts contain uncapped liability clauses that expose the organization to unlimited financial risk. 8 of these are with new vendors from the past quarter.",
    severity: "critical",
    confidence: 96,
    recommendedAction: "Review and amend uncapped liability clauses in 12 contracts. Prioritize the 8 new vendor agreements.",
    category: "liability",
    quickActions: [
      { label: "View Contracts", action: "view_contracts" },
      { label: "Generate Report", action: "generate_report" },
    ],
    createdAt: "2026-05-14T08:30:00Z",
  },
  {
    id: "insight-2",
    title: "Vendor Risk Threshold Breached",
    description: "3 vendors (SecureNet Solutions, Acme Corp, GlobalTech Inc) exceed the acceptable risk threshold of 7.5. Combined exposure: $11.5M.",
    severity: "critical",
    confidence: 92,
    recommendedAction: "Schedule risk review meetings with top 3 high-risk vendors. Consider renegotiation or alternative sourcing.",
    category: "vendor",
    quickActions: [
      { label: "Vendor Profile", action: "vendor_profile" },
      { label: "Risk Report", action: "risk_report" },
    ],
    createdAt: "2026-05-14T07:15:00Z",
  },
  {
    id: "insight-3",
    title: "Impending Contract Expirations",
    description: "7 contracts worth $3.2M are expiring within 30 days. 4 have auto-renewal clauses that may trigger unfavorable terms.",
    severity: "warning",
    confidence: 98,
    recommendedAction: "Review expiring contracts immediately. Prioritize the 4 with auto-renewal to renegotiate terms before renewal triggers.",
    category: "expiry",
    quickActions: [
      { label: "View Expiring", action: "view_expiring" },
      { label: "Extend All", action: "extend_all" },
    ],
    createdAt: "2026-05-14T06:45:00Z",
  },
  {
    id: "insight-4",
    title: "Financial Exposure Identified",
    description: "Potential $2.4M exposure identified in 5 contracts with liquidated damages clauses that lack caps. Average exposure per contract: $480K.",
    severity: "warning",
    confidence: 88,
    recommendedAction: "Engage legal to review liquidated damages clauses. Target adding liability caps of 100% of contract value.",
    category: "financial",
    quickActions: [
      { label: "Exposure Details", action: "exposure_details" },
      { label: "Legal Review", action: "legal_review" },
    ],
    createdAt: "2026-05-13T22:00:00Z",
  },
  {
    id: "insight-5",
    title: "GDPR Compliance Gap",
    description: "15 contracts with EU counterparties lack adequate GDPR data processing clauses. Potential regulatory fines up to 4% of global revenue.",
    severity: "critical",
    confidence: 85,
    recommendedAction: "Prioritize GDPR amendment addendums for all 15 contracts. Engage DPO for compliance sign-off.",
    category: "compliance",
    quickActions: [
      { label: "View Contracts", action: "view_contracts" },
      { label: "Compliance Report", action: "compliance_report" },
    ],
    createdAt: "2026-05-13T18:30:00Z",
  },
  {
    id: "insight-6",
    title: "Auto-Renewal Savings Opportunity",
    description: "8 contracts with favorable terms are set to auto-renew. Locking in current rates could save $1.8M vs. market rates.",
    severity: "info",
    confidence: 78,
    recommendedAction: "Confirm auto-renewal elections for the 8 identified contracts before the 30-day notice window closes.",
    category: "financial",
    quickActions: [
      { label: "Review Terms", action: "review_terms" },
      { label: "Confirm Renewal", action: "confirm_renewal" },
    ],
    createdAt: "2026-05-13T15:00:00Z",
  },
];

// ── Portfolio Contracts ────────────────────────────────────────────────────

const vendors = ["Acme Corp", "GlobalTech Inc", "DataSync Partners", "CloudServ Ltd", "SecureNet Solutions", "InnoVate LLC", "Pacific Rim Trading", "EuroLegal Partners"];
const owners = ["Alice Chen", "Bob Martinez", "Carol Singh", "David Kim", "Eve Johnson", "Frank Wilson"];
const departments = ["Engineering", "Marketing", "Finance", "Operations", "Sales", "Legal", "HR", "IT"];
const businessUnits = ["North America", "EMEA", "APAC", "LATAM"];
const geographies = ["United States", "Germany", "Japan", "United Kingdom", "Canada", "Australia", "France", "Singapore"];
const contractTypes = ["MSA", "SOW", "NDA", "License", "Service Agreement", "Partnership", "Employment", "Lease"];
const topRisks = ["Uncapped Liability", "Data Privacy", "Auto-Renewal", "SLA Breach", "Indemnification Gap", "Termination Notice", "IP Ownership", "Compliance Risk"];
const clauseCats = ["Indemnification", "Liability Cap", "Termination", "Confidentiality", "Data Privacy", "Compliance"];

function rand(min: number, max: number) { return Math.floor(Math.random() * (max - min + 1)) + min; }
function pick<T>(arr: T[]): T { return arr[rand(0, arr.length - 1)]; }
function pickN<T>(arr: T[], n: number): T[] {
  const shuffled = [...arr].sort(() => Math.random() - 0.5);
  return shuffled.slice(0, n);
}

export const portfolioContracts: PortfolioContract[] = Array.from({ length: 48 }, (_, i) => {
  const riskScore = rand(2, 10);
  const riskLevel = riskScore >= 8 ? "critical" : riskScore >= 6 ? "high" : riskScore >= 4 ? "medium" : "low";
  const exposure = +(rand(50, 2500) / 100).toFixed(1);
  const daysToExpiry = rand(-30, 365);
  const status = daysToExpiry <= 0 ? "expired" : daysToExpiry <= 90 ? "expiring_soon" : "active";
  const vendor = pick(vendors);

  return {
    id: `CT-${2026001 + i}`,
    name: `${pick(["Master Service Agreement", "Software License", "Cloud Services", "Consulting Services", "Supply Agreement", "Distribution Agreement", "Partnership Agreement", "Professional Services"])} - ${vendor}`,
    vendor,
    riskScore,
    riskLevel,
    financialExposure: exposure,
    currency: "USD",
    expiryDate: new Date(Date.now() + daysToExpiry * 86400000).toISOString().split("T")[0],
    topRisk: pick(topRisks),
    aiConfidence: rand(72, 99),
    owner: pick(owners),
    status: status as any,
    department: pick(departments),
    businessUnit: pick(businessUnits),
    geography: pick(geographies),
    contractType: pick(contractTypes),
    clauseCategories: pickN(clauseCats, rand(2, 4)),
    autoRenew: Math.random() > 0.6,
    slaCompliant: Math.random() > 0.25,
    obligationsDue: rand(0, 12),
  };
});

// ── Financial Exposure ─────────────────────────────────────────────────────

export const financialExposure: FinancialExposure = {
  totalExposure: 18.4,
  insuredAmount: 11.2,
  gapAmount: 7.2,
  currency: "USD",
  breakdown: [
    { category: "Indemnification", amount: 5.2, percentage: 28.3 },
    { category: "Liability Damages", amount: 4.1, percentage: 22.3 },
    { category: "Data Breach", amount: 3.8, percentage: 20.7 },
    { category: "IP Infringement", amount: 2.9, percentage: 15.8 },
    { category: "SLA Penalties", amount: 2.4, percentage: 13.0 },
  ],
  vendorConcentration: [
    { vendor: "SecureNet Solutions", exposure: 4.2, percentage: 22.8 },
    { vendor: "Acme Corp", exposure: 3.8, percentage: 20.7 },
    { vendor: "GlobalTech Inc", exposure: 3.5, percentage: 19.0 },
    { vendor: "Pacific Rim Trading", exposure: 2.8, percentage: 15.2 },
    { vendor: "DataSync Partners", exposure: 2.1, percentage: 11.4 },
    { vendor: "Others", exposure: 2.0, percentage: 10.9 },
  ],
  insuranceGaps: [
    { area: "Cyber Liability", gap: 2.8, risk: "critical" },
    { area: "Professional Indemnity", gap: 1.9, risk: "high" },
    { area: "Directors & Officers", gap: 1.2, risk: "medium" },
    { area: "Product Liability", gap: 0.8, risk: "low" },
    { area: "Environmental", gap: 0.5, risk: "low" },
  ],
};

// ── Workflow Alerts ────────────────────────────────────────────────────────

export const workflowAlerts: WorkflowAlert[] = [
  {
    id: "wf-1",
    type: "approval",
    title: "Contract Renewal: SecureNet Solutions",
    description: "MSA renewal with SecureNet Solutions requires VP-level approval. Value: $1.2M",
    severity: "warning",
    assignee: "Carol Singh",
    dueDate: "2026-05-20",
    createdAt: "2026-05-14T09:00:00Z",
    status: "pending",
  },
  {
    id: "wf-2",
    type: "escalation",
    title: "Uncapped Liability: Acme Corp",
    description: "Legal escalation required — Acme Corp contract has uncapped indemnification clause.",
    severity: "critical",
    assignee: "Alice Chen",
    dueDate: "2026-05-18",
    createdAt: "2026-05-14T08:00:00Z",
    status: "pending",
  },
  {
    id: "wf-3",
    type: "sla_breach",
    title: "SLA Breach: GlobalTech Inc",
    description: "GlobalTech Inc failed to meet 99.9% uptime SLA for 3rd consecutive month.",
    severity: "critical",
    assignee: "David Kim",
    dueDate: "2026-05-16",
    createdAt: "2026-05-14T07:30:00Z",
    status: "in_progress",
  },
  {
    id: "wf-4",
    type: "task",
    title: "GDPR Amendment Review",
    description: "Review and approve GDPR data processing addendums for 15 EU contracts.",
    severity: "warning",
    assignee: "Eve Johnson",
    dueDate: "2026-05-25",
    createdAt: "2026-05-13T16:00:00Z",
    status: "pending",
  },
  {
    id: "wf-5",
    type: "review",
    title: "Q2 Risk Review Queue",
    description: "24 contracts pending quarterly risk review. 8 are overdue.",
    severity: "warning",
    assignee: "Bob Martinez",
    dueDate: "2026-05-30",
    createdAt: "2026-05-13T14:00:00Z",
    status: "in_progress",
  },
  {
    id: "wf-6",
    type: "notification",
    title: "Auto-Renewal Notice: DataSync Partners",
    description: "30-day notice window closing for DataSync Partners agreement. Current terms are favorable.",
    severity: "info",
    dueDate: "2026-05-19",
    createdAt: "2026-05-13T10:00:00Z",
    status: "pending",
  },
  {
    id: "wf-7",
    type: "approval",
    title: "New Vendor Onboarding: Quantum Labs",
    description: "New $850K software licensing agreement pending procurement approval.",
    severity: "info",
    assignee: "Frank Wilson",
    dueDate: "2026-05-22",
    createdAt: "2026-05-12T15:00:00Z",
    status: "pending",
  },
  {
    id: "wf-8",
    type: "escalation",
    title: "Data Privacy Concern: Pacific Rim Trading",
    description: "Cross-border data transfer clauses need legal review for GDPR compliance.",
    severity: "warning",
    assignee: "Alice Chen",
    dueDate: "2026-05-21",
    createdAt: "2026-05-12T11:00:00Z",
    status: "pending",
  },
];

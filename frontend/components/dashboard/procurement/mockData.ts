// ── Enterprise Procurement Mock Data ────────────────────────────────────────

import type { ProcurementKpi, SupplierRecord, SpendTrend, VendorCategory, GeoRisk, RiskTrend, ProcurementInsight, WorkflowItem, SavingsOpportunity } from "./types";

function rand(min: number, max: number) { return Math.floor(Math.random() * (max - min + 1)) + min; }
function pick<T>(arr: T[]): T { return arr[rand(0, arr.length - 1)]; }
function pickN<T>(arr: T[], n: number): T[] { const s = [...arr].sort(() => Math.random() - 0.5); return s.slice(0, n); }

// ── KPI Metrics ─────────────────────────────────────────────────────────────

export const procurementKpis: ProcurementKpi[] = [
  { id: "total-spend", label: "Total Supplier Spend", value: "$142.8M", trend: 12.3, trendDirection: "up", icon: "DollarSign", color: "from-navy-600 to-navy-800", severity: "info", sparklineData: [98, 105, 112, 118, 125, 132, 138, 142.8], tooltip: "Total spend across all active supplier contracts" },
  { id: "high-risk", label: "High-Risk Vendors", value: "18", trend: 20.0, trendDirection: "up", icon: "AlertTriangle", color: "from-red-500 to-orange-500", severity: "critical", sparklineData: [12, 13, 14, 14, 15, 16, 17, 18], tooltip: "Vendors with risk score ≥ 7" },
  { id: "expiring", label: "Contracts Expiring Soon", value: "24", trend: -7.7, trendDirection: "down", icon: "Clock", color: "from-yellow-500 to-orange-500", severity: "warning", sparklineData: [28, 27, 26, 25, 25, 24, 23, 24], tooltip: "Contracts expiring within 90 days" },
  { id: "concentration", label: "Supplier Concentration", value: "42%", trend: 5.2, trendDirection: "up", icon: "PieChart", color: "from-purple-500 to-indigo-500", severity: "warning", sparklineData: [35, 36, 37, 38, 39, 40, 41, 42], tooltip: "Percentage of spend concentrated in top 5 suppliers" },
  { id: "sla-violations", label: "SLA Violations", value: "11", trend: -21.4, trendDirection: "down", icon: "AlertOctagon", color: "from-red-500 to-rose-500", severity: "critical", sparklineData: [16, 15, 15, 14, 13, 12, 12, 11], tooltip: "Active SLA breaches across supplier contracts" },
  { id: "savings", label: "Savings Opportunities", value: "$4.2M", trend: 35.5, trendDirection: "up", icon: "TrendingDown", color: "from-green-500 to-emerald-500", severity: "success", sparklineData: [2.1, 2.5, 2.8, 3.1, 3.4, 3.7, 4.0, 4.2], tooltip: "Total identified cost savings opportunities" },
  { id: "auto-renewal", label: "Auto-Renewal Exposure", value: "$18.6M", trend: 8.1, trendDirection: "up", icon: "RefreshCw", color: "from-amber-500 to-yellow-500", severity: "warning", sparklineData: [14.2, 15.0, 15.8, 16.2, 16.9, 17.5, 18.1, 18.6], tooltip: "Total value of contracts with auto-renewal clauses" },
  { id: "cycle-time", label: "Procurement Cycle Time", value: "34d", trend: -15.0, trendDirection: "down", icon: "Zap", color: "from-blue-500 to-cyan-500", severity: "success", sparklineData: [45, 42, 40, 38, 37, 36, 35, 34], tooltip: "Average days from requisition to contract execution" },
];

// ── Suppliers ───────────────────────────────────────────────────────────────

const categories = ["Cloud Services", "Software Licensing", "Professional Services", "Hardware", "Consulting", "Marketing", "Logistics", "Facilities", "IT Support", "Telecom"];
const countries = ["United States", "Germany", "Japan", "United Kingdom", "Canada", "India", "France", "Singapore", "Australia", "Brazil"];
const owners = ["Alice Chen", "Bob Martinez", "Carol Singh", "David Kim", "Eve Johnson", "Frank Wilson"];
const riskAreas = ["Liability", "Data Privacy", "IP Ownership", "SLA Compliance", "Insurance Gap", "Auto-Renewal", "Termination Notice", "Compliance", "Financial Stability", "Geopolitical"];
const aiFlags = ["Uncapped Liability", "Missing DPA", "Insurance Gap", "SLA Breach", "Auto-Renewal Risk", "Compliance Issue", "Financial Distress", "Concentration Risk", "Benchmark Deviation", "Geopolitical Risk"];
const missingClauses = ["DPA", "SLA", "Liability Cap", "Auto-Renewal Notice", "Insurance Requirements", "Data Processing", "Force Majeure", "Non-Compete"];

export const supplierRecords: SupplierRecord[] = Array.from({ length: 40 }, (_, i) => {
  const riskScore = rand(2, 10);
  const rl = riskScore >= 8 ? "critical" : riskScore >= 6 ? "high" : riskScore >= 4 ? "medium" : "low";
  const spend = +(rand(5, 8500) / 100).toFixed(1);
  const contracts = rand(1, 8);
  const sla = rand(60, 100);
  const financial = pick(["strong", "stable", "weak", "distressed"] as const);
  const cat = pick(categories);
  const country = pick(countries);
  const name = pick([
    "Acme Corp", "GlobalTech Inc", "DataSync Partners", "CloudServ Ltd", "SecureNet Solutions",
    "InnoVate LLC", "Pacific Rim Trading", "EuroLegal Partners", "NovaTech Systems", "Quantum Labs",
    "Atlas Logistics", "Vertex Security", "Pinnacle Software", "Meridian Consulting", "Horizon Cloud",
    "Summit Solutions", "Apex Digital", "Core Infrastructure", "Fusion Networks", "Prism Analytics",
    "Titan Supply Co", "Orion Tech", "Crest Data Systems", "Vanguard Security", "Elite Services",
    "NorthStar Logistics", "Silverline Consulting", "BrightPath Solutions", "Cobalt Systems", "Driftwood Analytics",
    "PineTree Software", "Redstone Partners", "BluePeak Cloud", "StoneWall Security", "GoldenGate Logistics",
    "IronClad Services", "SilverCreek Consulting", "ThunderCloud Inc", "ValleyTech Solutions", "WestWind Partners",
  ]);

  return {
    id: `SUP-${2026001 + i}`,
    name: name,
    riskScore,
    riskLevel: rl,
    totalSpend: spend,
    currency: "USD",
    activeContracts: contracts,
    renewalExposure: +(spend * (contracts * 0.3)).toFixed(1),
    slaPerformance: sla,
    complianceStatus: pick(["compliant", "at_risk", "non_compliant", "pending_review"] as const),
    topRiskArea: pick(riskAreas),
    procurementOwner: pick(owners),
    country,
    financialStability: financial,
    lastAssessment: new Date(Date.now() - rand(0, 180) * 86400000).toISOString().split("T")[0],
    aiConfidence: rand(72, 99),
    category: cat,
    businessUnit: pick(["North America", "EMEA", "APAC", "LATAM"]),
    contractValue: spend,
    avgContractTerm: rand(12, 48),
    insuranceCompliant: Math.random() > 0.35,
    hasSla: Math.random() > 0.2,
    onboardingDate: new Date(Date.now() - rand(180, 1095) * 86400000).toISOString().split("T")[0],
    dunsNumber: `${rand(10, 99)}-${rand(100, 999)}-${rand(1000, 9999)}`,
    taxId: `XX-XXXXXXX${rand(100, 999)}`,
    aiFlags: riskScore >= 6 ? pickN(aiFlags, rand(1, 4)) : [],
    missingClauses: riskScore >= 5 ? pickN(missingClauses, rand(0, 3)) : [],
    negotiationHistory: rand(0, 12),
    relationshipAge: rand(1, 15),
  };
});

// ── Spend Trends ────────────────────────────────────────────────────────────

export const spendTrendData: SpendTrend[] = [
  { month: "Jan", total: 112, cloud: 28, software: 35, consulting: 22, hardware: 15, services: 12 },
  { month: "Feb", total: 118, cloud: 30, software: 36, consulting: 23, hardware: 16, services: 13 },
  { month: "Mar", total: 125, cloud: 32, software: 38, consulting: 24, hardware: 18, services: 13 },
  { month: "Apr", total: 132, cloud: 34, software: 40, consulting: 26, hardware: 18, services: 14 },
  { month: "May", total: 138, cloud: 36, software: 42, consulting: 27, hardware: 19, services: 14 },
  { month: "Jun", total: 142.8, cloud: 38, software: 43, consulting: 28, hardware: 20, services: 13.8 },
];

// ── Vendor Categories ───────────────────────────────────────────────────────

export const vendorCategoryData: VendorCategory[] = [
  { category: "Cloud Services", suppliers: 8, totalSpend: 38.2, avgRisk: 7.2, highRiskCount: 4 },
  { category: "Software Licensing", suppliers: 10, totalSpend: 35.5, avgRisk: 5.8, highRiskCount: 3 },
  { category: "Professional Services", suppliers: 6, totalSpend: 22.1, avgRisk: 6.5, highRiskCount: 3 },
  { category: "Hardware", suppliers: 5, totalSpend: 15.8, avgRisk: 4.2, highRiskCount: 1 },
  { category: "Consulting", suppliers: 4, totalSpend: 12.4, avgRisk: 5.5, highRiskCount: 2 },
  { category: "Marketing", suppliers: 3, totalSpend: 8.2, avgRisk: 3.8, highRiskCount: 1 },
  { category: "Logistics", suppliers: 2, totalSpend: 5.6, avgRisk: 6.2, highRiskCount: 2 },
  { category: "Facilities", suppliers: 2, totalSpend: 5.0, avgRisk: 3.5, highRiskCount: 0 },
];

// ── Geographic Risk ─────────────────────────────────────────────────────────

export const geoRiskData: GeoRisk[] = [
  { country: "United States", suppliers: 14, avgRisk: 5.8, totalExposure: 52.4, code: "US" },
  { country: "Germany", suppliers: 5, avgRisk: 4.2, totalExposure: 18.5, code: "DE" },
  { country: "Japan", suppliers: 4, avgRisk: 3.5, totalExposure: 15.2, code: "JP" },
  { country: "United Kingdom", suppliers: 4, avgRisk: 5.2, totalExposure: 14.8, code: "GB" },
  { country: "Canada", suppliers: 3, avgRisk: 4.8, totalExposure: 12.1, code: "CA" },
  { country: "India", suppliers: 4, avgRisk: 7.2, totalExposure: 11.5, code: "IN" },
  { country: "France", suppliers: 2, avgRisk: 3.8, totalExposure: 8.2, code: "FR" },
  { country: "Singapore", suppliers: 2, avgRisk: 4.5, totalExposure: 6.8, code: "SG" },
  { country: "Australia", suppliers: 1, avgRisk: 3.0, totalExposure: 2.5, code: "AU" },
  { country: "Brazil", suppliers: 1, avgRisk: 6.5, totalExposure: 1.8, code: "BR" },
];

// ── Risk Trends ─────────────────────────────────────────────────────────────

export const riskTrendData: RiskTrend[] = [
  { date: "Dec", critical: 3, high: 8, medium: 12, low: 17 },
  { date: "Jan", critical: 4, high: 9, medium: 11, low: 16 },
  { date: "Feb", critical: 4, high: 10, medium: 12, low: 14 },
  { date: "Mar", critical: 5, high: 11, medium: 10, low: 14 },
  { date: "Apr", critical: 5, high: 12, medium: 11, low: 12 },
  { date: "May", critical: 4, high: 10, medium: 13, low: 13 },
];

// ── AI Procurement Insights ─────────────────────────────────────────────────

export const procurementInsights: ProcurementInsight[] = [
  { id: "pi-1", title: "Vendor Liability Threshold Breached", description: "3 vendors (Acme Corp, SecureNet Solutions, GlobalTech Inc) exceed acceptable liability thresholds with uncapped indemnification clauses totaling $12.5M exposure.", severity: "critical", confidence: 94, impactedSuppliers: ["Acme Corp", "SecureNet Solutions", "GlobalTech Inc"], suggestedAction: "Review and amend uncapped liability clauses. Prioritize Acme Corp with $5.2M exposure.", category: "liability", quickActions: [{ label: "View Vendors", action: "view" }, { label: "Generate Report", action: "report" }] },
  { id: "pi-2", title: "Cost Savings Opportunity Identified", description: "Consolidating cloud services spend across 3 suppliers (CloudServ, Horizon Cloud, BluePeak) could yield $1.8M in annual savings through volume discounts.", severity: "success", confidence: 88, impactedSuppliers: ["CloudServ Ltd", "Horizon Cloud", "BluePeak Cloud"], suggestedAction: "Initiate consolidated sourcing event for cloud infrastructure services.", category: "savings", quickActions: [{ label: "Savings Analysis", action: "analysis" }, { label: "Start Sourcing", action: "sourcing" }], savings: 1.8 },
  { id: "pi-3", title: "Insurance Compliance Gap Detected", description: "5 suppliers lack required insurance clauses including cyber liability and professional indemnity coverage. Combined gap exposure: $4.2M.", severity: "critical", confidence: 91, impactedSuppliers: ["DataSync Partners", "Pacific Rim Trading", "InnoVate LLC", "NovaTech Systems", "Quantum Labs"], suggestedAction: "Send insurance compliance notice to 5 suppliers. Set 30-day deadline for proof of coverage.", category: "compliance", quickActions: [{ label: "View Gap Analysis", action: "gap" }, { label: "Send Notices", action: "notices" }] },
  { id: "pi-4", title: "Vendor Concentration Risk: Cloud Services", description: "62% of cloud spend concentrated in top 2 suppliers. Single point of failure risk identified for critical infrastructure.", severity: "warning", confidence: 85, impactedSuppliers: ["CloudServ Ltd", "Horizon Cloud"], suggestedAction: "Develop multi-vendor cloud strategy. Target max 40% concentration per supplier.", category: "risk", quickActions: [{ label: "Concentration Report", action: "report" }, { label: "Risk Assessment", action: "assessment" }] },
  { id: "pi-5", title: "Renewal Optimization Opportunity", description: "8 contracts with favorable terms are renewing in Q3. Locking in current rates could save $1.2M vs projected market increases of 12-15%.", severity: "info", confidence: 82, impactedSuppliers: ["Atlas Logistics", "Summit Solutions", "Prism Analytics", "Titan Supply Co", "Cobalt Systems", "Silverline Consulting", "Redstone Partners", "ValleyTech Solutions"], suggestedAction: "Begin renewal negotiations 90 days before expiry. Prioritize volume-based discount discussions.", category: "renewal", quickActions: [{ label: "Renewal Calendar", action: "calendar" }, { label: "Strategy Review", action: "strategy" }], savings: 1.2 },
  { id: "pi-6", title: "Geopolitical Risk: India Operations", description: "4 suppliers in India show elevated risk due to regulatory changes in data localization requirements. Potential service disruption for 3 critical contracts.", severity: "warning", confidence: 78, impactedSuppliers: ["Prism Analytics", "Crest Data Systems", "Driftwood Analytics", "BrightPath Solutions"], suggestedAction: "Review data localization compliance for India-based suppliers. Identify alternate suppliers if needed.", category: "risk", quickActions: [{ label: "Risk Details", action: "details" }, { label: "Supplier Review", action: "review" }] },
];

// ── Workflow Items ──────────────────────────────────────────────────────────

export const workflowItems: WorkflowItem[] = [
  { id: "wf-1", type: "approval", title: "Cloud Services Renewal: CloudServ Ltd", description: "$2.8M renewal requires VP Procurement approval. Current terms favorable vs market.", severity: "warning", assignee: "Carol Singh", dueDate: "2026-05-22", status: "pending", slaRemaining: 8 },
  { id: "wf-2", type: "sourcing", title: "RFP Response Evaluation: IT Infrastructure", description: "5 vendor responses received for $4.5M IT infrastructure RFP. Evaluation in progress.", severity: "info", assignee: "Bob Martinez", dueDate: "2026-06-01", status: "in_progress", slaRemaining: 18 },
  { id: "wf-3", type: "onboarding", title: "Supplier Onboarding: Quantum Labs", description: "New software vendor requires background check, financial review, and legal approval.", severity: "info", assignee: "Eve Johnson", dueDate: "2026-05-28", status: "pending", slaRemaining: 14 },
  { id: "wf-4", type: "review", title: "Quarterly Supplier Risk Review", description: "12 high-risk suppliers due for quarterly risk reassessment. 5 completed, 7 remaining.", severity: "warning", assignee: "David Kim", dueDate: "2026-05-30", status: "in_progress", slaRemaining: 16 },
  { id: "wf-5", type: "escalation", title: "SLA Breach: SecureNet Solutions", description: "3rd consecutive month below 99.9% uptime target. Escalation to vendor management.", severity: "critical", assignee: "Alice Chen", dueDate: "2026-05-18", status: "pending", slaRemaining: 4 },
  { id: "wf-6", type: "renewal", title: "MSA Renewal: Acme Corp", description: "Master Services Agreement expiring June 30. Begin renegotiation for updated terms.", severity: "warning", assignee: "Frank Wilson", dueDate: "2026-06-15", status: "pending", slaRemaining: 32 },
  { id: "wf-7", type: "approval", title: "New Vendor: PineTree Software", description: "$850K software licensing agreement pending procurement committee approval.", severity: "info", assignee: "Carol Singh", dueDate: "2026-05-25", status: "pending", slaRemaining: 11 },
  { id: "wf-8", type: "escalation", title: "Insurance Compliance: DataSync Partners", description: "Failure to provide proof of cyber liability insurance within 30-day notice period.", severity: "critical", assignee: "Alice Chen", dueDate: "2026-05-16", status: "pending", slaRemaining: 2 },
];

// ── Savings Opportunities ───────────────────────────────────────────────────

export const savingsOpportunities: SavingsOpportunity[] = [
  { id: "so-1", title: "Cloud Services Consolidation", potentialSavings: 1.8, category: "Cloud", confidence: 88, effort: "medium", suppliers: ["CloudServ Ltd", "Horizon Cloud", "BluePeak Cloud"], description: "Consolidate 3 cloud providers into 1-2 for volume discounts and reduced management overhead." },
  { id: "so-2", title: "Software License Optimization", potentialSavings: 1.2, category: "Software", confidence: 82, effort: "low", suppliers: ["GlobalTech Inc", "Pinnacle Software", "Orion Tech"], description: "Eliminate unused licenses and negotiate enterprise-wide agreements." },
  { id: "so-3", title: "Consulting Rate Renegotiation", potentialSavings: 0.8, category: "Consulting", confidence: 75, effort: "medium", suppliers: ["Meridian Consulting", "Silverline Consulting", "BrightPath Solutions"], description: "Benchmark consulting rates against market. Target 15% rate reduction." },
  { id: "so-4", title: "Logistics Contract Optimization", potentialSavings: 0.4, category: "Logistics", confidence: 70, effort: "high", suppliers: ["Atlas Logistics", "NorthStar Logistics"], description: "Renegotiate shipping rates based on volume commitments and multi-year terms." },
];

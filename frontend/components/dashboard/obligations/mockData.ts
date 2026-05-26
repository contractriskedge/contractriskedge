// ── Enterprise Obligation Management Mock Data ─────────────────────────────

import type { ObligationKpi, ObligationRecord, ObligationInsight, SlaMetric, FinancialExposure, TimelineEvent, RiskLevel, SlaStatus, ObligationStatus } from "./types";

function rand(min: number, max: number) { return Math.floor(Math.random() * (max - min + 1)) + min; }
function pick<T>(arr: T[]): T { return arr[rand(0, arr.length - 1)]; }

const vendors = ["Acme Corp", "GlobalTech Inc", "DataSync Partners", "CloudServ Ltd", "SecureNet Solutions", "InnoVate LLC", "Pacific Rim Trading", "EuroLegal Partners", "NovaTech Systems", "Quantum Labs"];
const owners = ["Alice Chen", "Bob Martinez", "Carol Singh", "David Kim", "Eve Johnson", "Frank Wilson"];
const departments = ["Legal", "Procurement", "Finance", "Operations", "Compliance", "IT", "Engineering", "Sales"];
const businessUnits = ["North America", "EMEA", "APAC", "LATAM"];
const geographies = ["United States", "Germany", "Japan", "United Kingdom", "Canada", "Australia", "France", "Singapore"];

// ── KPI Metrics ─────────────────────────────────────────────────────────────

export const obligationKpis: ObligationKpi[] = [
  { id: "active", label: "Active Obligations", value: "156", trend: 8.3, trendDirection: "up", icon: "ClipboardCheck", color: "from-blue-500 to-indigo-500", severity: "info", sparklineData: [120, 125, 130, 135, 140, 145, 150, 156], tooltip: "Total active obligations across all contracts" },
  { id: "overdue", label: "Overdue Obligations", value: "23", trend: -11.5, trendDirection: "down", icon: "AlertTriangle", color: "from-red-500 to-orange-500", severity: "critical", sparklineData: [32, 30, 29, 28, 27, 25, 24, 23], tooltip: "Obligations past their due date" },
  { id: "sla-breaches", label: "SLA Breaches", value: "11", trend: -21.4, trendDirection: "down", icon: "AlertOctagon", color: "from-red-500 to-rose-500", severity: "critical", sparklineData: [18, 17, 15, 14, 13, 12, 12, 11], tooltip: "SLA breaches in current period" },
  { id: "milestones", label: "Upcoming Milestones", value: "34", trend: 9.7, trendDirection: "up", icon: "Flag", color: "from-purple-500 to-pink-500", severity: "info", sparklineData: [25, 27, 28, 30, 31, 32, 33, 34], tooltip: "Milestones due in the next 30 days" },
  { id: "exposure", label: "Financial Exposure", value: "$4.2M", trend: 15.1, trendDirection: "up", icon: "DollarSign", color: "from-red-500 to-orange-500", severity: "critical", sparklineData: [2.8, 3.1, 3.3, 3.5, 3.7, 3.9, 4.1, 4.2], tooltip: "Total financial exposure from overdue/at-risk obligations" },
  { id: "compliance", label: "Vendor Compliance", value: "84%", trend: 3.7, trendDirection: "up", icon: "Shield", color: "from-green-500 to-emerald-500", severity: "success", sparklineData: [76, 78, 79, 80, 81, 82, 83, 84], tooltip: "Overall vendor compliance score" },
  { id: "completed", label: "Completed (MTD)", value: "42", trend: 23.5, trendDirection: "up", icon: "CheckCircle", color: "from-green-500 to-teal-500", severity: "success", sparklineData: [28, 30, 32, 34, 36, 38, 40, 42], tooltip: "Obligations completed this month" },
  { id: "escalated", label: "Escalated", value: "8", trend: 14.3, trendDirection: "up", icon: "ArrowUpCircle", color: "from-purple-500 to-pink-500", severity: "warning", sparklineData: [5, 6, 6, 6, 7, 7, 7, 8], tooltip: "Obligations that have been escalated" },
];

// ── Generate 48 Obligations ─────────────────────────────────────────────────

export const obligationRecords: ObligationRecord[] = Array.from({ length: 48 }, (_, i) => {
  const daysToDue = rand(-30, 120);
  const status: ObligationStatus = daysToDue < 0 ? (Math.random() > 0.4 ? "overdue" : "escalated") : daysToDue < 7 ? "in_progress" : daysToDue < 30 ? "pending" : Math.random() > 0.5 ? "pending" : "completed";
  const riskScore = rand(2, 10);
  const rl: RiskLevel = riskScore >= 8 ? "critical" : riskScore >= 6 ? "high" : riskScore >= 4 ? "medium" : "low";
  const type = pick(["payment", "deliverable", "milestone", "sla", "renewal", "compliance", "reporting", "insurance"] as const);
  const vendor = pick(vendors);
  const slaRemaining = type === "sla" ? rand(-48, 168) : 0;
  const slaSt: SlaStatus = slaRemaining < 0 ? "breached" : slaRemaining < 24 ? "at_risk" : "on_track";

  return {
    id: `OBL-${2026001 + i}`,
    name: pick([
      "Submit SOC2 Type II Report", "Renew Cyber Liability Insurance", "Provide Quarterly Uptime Report",
      "GDPR Compliance Certification", "Deliver Q2 Statement of Work", "Annual Security Assessment",
      "Payment — License Fees (Q3)", "Milestone — Phase 2 Completion", "SLA — 99.9% Uptime Commitment",
      "Renewal Notice — 90 Days", "Data Processing Addendum", "Penetration Test Results",
      "Financial Audit Documentation", "Business Continuity Plan Update", "Insurance Certificate Renewal",
      "Regulatory Filing — Quarterly", "Disaster Recovery Test Results", "Vendor Risk Assessment",
      "Compliance Training Completion", "Service Credit Calculation",
    ]),
    contractId: `CON-${2026001 + (i % 20)}`,
    contractName: `${pick(["MSA", "SOW", "License", "Service Agreement", "Partnership"])} - ${vendor}`,
    vendor,
    type,
    owner: pick(owners),
    assignee: pick(owners),
    dueDate: new Date(Date.now() + daysToDue * 86400000).toISOString().split("T")[0],
    completedDate: status === "completed" ? new Date(Date.now() - rand(1, 30) * 86400000).toISOString().split("T")[0] : undefined,
    status,
    riskLevel: rl,
    riskScore,
    slaStatus: slaSt,
    slaRemaining,
    financialImpact: +(rand(10, 2500) / 100).toFixed(1),
    currency: "USD",
    escalationLevel: status === "escalated" ? rand(1, 3) : 0,
    aiRiskPrediction: rand(20, 95),
    aiConfidence: rand(72, 96),
    description: pick([
      "Annual security compliance certification required", "Quarterly service level performance report",
      "Contractual payment obligation for licensing fees", "Project milestone delivery and sign-off",
      "Regulatory compliance documentation submission", "Insurance policy renewal and proof of coverage",
      "Service level agreement performance monitoring", "Data protection compliance certification",
    ]),
    clauseReference: `Section ${rand(3, 16)}.${rand(1, 5)}`,
    attachments: rand(0, 5),
    reminders: rand(0, 3),
    notes: "",
    department: pick(departments),
    businessUnit: pick(businessUnits),
    geography: pick(geographies),
    createdAt: new Date(Date.now() - rand(30, 365) * 86400000).toISOString().split("T")[0],
    lastModified: new Date(Date.now() - rand(0, 14) * 86400000).toISOString().split("T")[0],
  };
});

// ── AI Insights ─────────────────────────────────────────────────────────────

export const obligationInsights: ObligationInsight[] = [
  { id: "oi-1", title: "SecureNet Solutions Likely to Miss SLA", description: "AI predicts SecureNet Solutions will breach 99.9% uptime SLA for 4th consecutive month. Estimated penalty exposure: $240K.", severity: "critical", confidence: 92, impactedObligations: ["OBL-2026005", "OBL-2026010"], suggestedAction: "Initiate SLA breach escalation process. Schedule vendor performance review.", category: "sla", quickActions: [{ label: "View SLA", action: "view" }, { label: "Escalate", action: "escalate" }] },
  { id: "oi-2", title: "Payment Overdue — Potential $1.2M Exposure", description: "3 payment obligations totaling $1.2M are overdue by an average of 14 days. Pacific Rim Trading accounts for $680K.", severity: "critical", confidence: 88, impactedObligations: ["OBL-2026008", "OBL-2026015", "OBL-2026022"], suggestedAction: "Send payment reminders. Escalate Pacific Rim Trading to finance team.", category: "financial", quickActions: [{ label: "View Payments", action: "view" }, { label: "Send Reminders", action: "remind" }] },
  { id: "oi-3", title: "Compliance Deadline Approaching", description: "4 compliance obligations due within 14 days. GDPR certification for 2 vendors requires immediate action.", severity: "warning", confidence: 85, impactedObligations: ["OBL-2026004", "OBL-2026012", "OBL-2026028", "OBL-2026035"], suggestedAction: "Expedite compliance review for EU vendors. Assign compliance officer.", category: "compliance", quickActions: [{ label: "View Compliance", action: "view" }, { label: "Assign Reviewer", action: "assign" }] },
  { id: "oi-4", title: "Renewal Obligation Cluster Detected", description: "5 renewal obligations cluster in Q3 2026. Total renewal value: $8.5M. Early negotiation could save $1.2M.", severity: "info", confidence: 82, impactedObligations: ["OBL-2026018", "OBL-2026025", "OBL-2026031", "OBL-2026038", "OBL-2026042"], suggestedAction: "Begin renewal negotiations 90 days before expiry. Prioritize volume discounts.", category: "renewal", quickActions: [{ label: "View Renewals", action: "view" }, { label: "Strategy Session", action: "strategy" }] },
  { id: "oi-5", title: "Insurance Certificate Gaps Detected", description: "3 vendors have expired or expiring insurance certificates. Gap in cyber liability coverage: $2.8M.", severity: "warning", confidence: 78, impactedObligations: ["OBL-2026002", "OBL-2026016", "OBL-2026030"], suggestedAction: "Send insurance compliance notices. Set 14-day deadline for proof of coverage.", category: "compliance", quickActions: [{ label: "View Gap", action: "view" }, { label: "Send Notices", action: "notices" }] },
  { id: "oi-6", title: "Milestone Dependency Risk", description: "3 milestones for DataSync Partners Q2 engagement are interdependent. Delay in Phase 1 impacts $450K in subsequent milestones.", severity: "warning", confidence: 80, impactedObligations: ["OBL-2026007", "OBL-2026014", "OBL-2026021"], suggestedAction: "Review milestone dependency chain. Consider parallel execution where possible.", category: "milestone", quickActions: [{ label: "View Dependencies", action: "dependencies" }, { label: "Risk Assessment", action: "assessment" }] },
];

// ── SLA Metrics ─────────────────────────────────────────────────────────────

export const slaMetrics: SlaMetric[] = [
  { vendor: "CloudServ Ltd", contractType: "SaaS Agreement", slaTarget: "99.9% Uptime", performance: 99.92, trend: 0.02, breachCount: 0, status: "on_track" },
  { vendor: "SecureNet Solutions", contractType: "MSA", slaTarget: "99.9% Uptime", performance: 98.50, trend: -0.35, breachCount: 3, status: "breached" },
  { vendor: "GlobalTech Inc", contractType: "Service Agreement", slaTarget: "99.5% Uptime", performance: 99.45, trend: -0.05, breachCount: 1, status: "at_risk" },
  { vendor: "DataSync Partners", contractType: "Partnership", slaTarget: "99.0% Uptime", performance: 99.10, trend: 0.08, breachCount: 0, status: "on_track" },
  { vendor: "Acme Corp", contractType: "MSA", slaTarget: "99.95% Uptime", performance: 99.88, trend: -0.12, breachCount: 2, status: "at_risk" },
  { vendor: "NovaTech Systems", contractType: "License", slaTarget: "99.5% Uptime", performance: 99.60, trend: 0.05, breachCount: 0, status: "on_track" },
  { vendor: "Pacific Rim Trading", contractType: "Service Agreement", slaTarget: "99.0% Uptime", performance: 97.80, trend: -0.50, breachCount: 4, status: "breached" },
  { vendor: "EuroLegal Partners", contractType: "Consulting", slaTarget: "99.5% Uptime", performance: 99.55, trend: 0.03, breachCount: 0, status: "on_track" },
];

// ── Financial Exposure ──────────────────────────────────────────────────────

export const financialExposureData: FinancialExposure[] = [
  { category: "Payment Obligations", totalExposure: 2.8, overdueAmount: 1.2, atRiskAmount: 0.8, recoveredAmount: 0.5, trend: 12 },
  { category: "SLA Penalties", totalExposure: 0.9, overdueAmount: 0.4, atRiskAmount: 0.3, recoveredAmount: 0.1, trend: 8 },
  { category: "Missed Milestones", totalExposure: 1.5, overdueAmount: 0.6, atRiskAmount: 0.5, recoveredAmount: 0.2, trend: 15 },
  { category: "Compliance Fines", totalExposure: 0.6, overdueAmount: 0.2, atRiskAmount: 0.3, recoveredAmount: 0.1, trend: -5 },
  { category: "Renewal Exposure", totalExposure: 1.2, overdueAmount: 0.3, atRiskAmount: 0.6, recoveredAmount: 0.1, trend: 20 },
];

// ── Timeline Events ─────────────────────────────────────────────────────────

export const timelineEvents: TimelineEvent[] = [
  { id: "tl-1", date: "2026-05-20", type: "compliance", title: "GDPR Certification Due", description: "Annual GDPR compliance certification for EU vendors", status: "pending", vendor: "EuroLegal Partners", contractId: "CON-2026008" },
  { id: "tl-2", date: "2026-05-25", type: "deliverable", title: "Q2 SOW Delivery", description: "Q2 Statement of Work delivery for DataSync Partners", status: "in_progress", vendor: "DataSync Partners", contractId: "CON-2026003" },
  { id: "tl-3", date: "2026-05-15", type: "payment", title: "License Fee Payment", description: "Quarterly license fee payment for GlobalTech Inc", status: "overdue", vendor: "GlobalTech Inc", contractId: "CON-2026002" },
  { id: "tl-4", date: "2026-06-01", type: "sla", title: "SLA Performance Report", description: "Monthly SLA performance report for all vendors", status: "pending", vendor: "All Vendors", contractId: "—" },
  { id: "tl-5", date: "2026-05-10", type: "insurance", title: "Insurance Certificate Renewal", description: "Cyber liability insurance renewal for SecureNet Solutions", status: "overdue", vendor: "SecureNet Solutions", contractId: "CON-2026005" },
  { id: "tl-6", date: "2026-06-15", type: "milestone", title: "Phase 2 Milestone", description: "Phase 2 completion milestone for CloudServ Ltd migration", status: "pending", vendor: "CloudServ Ltd", contractId: "CON-2026004" },
  { id: "tl-7", date: "2026-05-30", type: "reporting", title: "Quarterly Compliance Report", description: "Q2 quarterly compliance report submission", status: "pending", vendor: "Internal", contractId: "—" },
  { id: "tl-8", date: "2026-07-01", type: "renewal", title: "MSA Renewal Notice", description: "90-day renewal notice for Acme Corp MSA", status: "pending", vendor: "Acme Corp", contractId: "CON-2026001" },
];

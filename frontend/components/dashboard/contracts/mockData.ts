// ── Enterprise Mock Data for Contract Repository ───────────────────────────

import type { ContractRecord, ContractKpi, SavedView, ActivityEvent, ClauseSummary, Obligation, RelatedContract, ContractStatus, WorkflowStage } from "./types";

// ── Helpers ─────────────────────────────────────────────────────────────────

function rand(min: number, max: number) { return Math.floor(Math.random() * (max - min + 1)) + min; }
function pick<T>(arr: T[]): T { return arr[rand(0, arr.length - 1)]; }
function pickN<T>(arr: T[], n: number): T[] { const s = [...arr].sort(() => Math.random() - 0.5); return s.slice(0, n); }

// ── Data pools ──────────────────────────────────────────────────────────────

const vendors = ["Acme Corp", "GlobalTech Inc", "DataSync Partners", "CloudServ Ltd", "SecureNet Solutions", "InnoVate LLC", "Pacific Rim Trading", "EuroLegal Partners", "NovaTech Systems", "Quantum Labs", "Atlas Logistics", "Vertex Security"];
const owners = ["Alice Chen", "Bob Martinez", "Carol Singh", "David Kim", "Eve Johnson", "Frank Wilson", "Grace Lee", "Henry Park"];
const businessUnits = ["North America", "EMEA", "APAC", "LATAM"];
const geographies = ["United States", "Germany", "Japan", "United Kingdom", "Canada", "Australia", "France", "Singapore", "Brazil", "India"];
const contractTypes = ["MSA", "SOW", "NDA", "License", "Service Agreement", "Partnership", "Employment", "Lease", "SaaS Agreement", "Consulting"];
const tags = ["high-value", "critical-vendor", "gdpr", "auto-renew", "sla-heavy", "confidential", "international", "ip-critical", "financial", "compliance"];
const riskLevels = ["critical", "high", "medium", "low"] as const;
const statuses = ["active", "expiring_soon", "under_review", "pending_signature", "expired", "draft"] as const;
const workflowStages = ["draft", "review", "approval", "negotiation", "executed", "renewal", "archived"] as const;
const aiFlags = ["critical", "review_needed", "benchmark_deviation", "auto_renewal_risk", "compliance_issue", "missing_clause"] as const;
const missingClausePool = ["DPA", "SLA", "Indemnification Cap", "Auto-Renewal Notice", "Data Processing", "Limitation of Liability", "Governing Law", "Force Majeure", "Non-Compete", "IP Ownership"];

const aiSummaries = [
  "Standard MSA with moderate risk. Key concerns: uncapped liability in Section 7, missing DPA. Recommend adding liability cap and data processing addendum.",
  "Low-risk NDA with standard confidentiality terms. Mutual obligations with 3-year survival period. No unusual provisions detected.",
  "High-value SaaS agreement with significant data privacy exposure. Missing GDPR-compliant data processing clauses. Auto-renewal at 90 days requires attention.",
  "Partnership agreement with revenue-sharing model. IP ownership clause needs clarification. Benchmark deviation detected on termination notice period.",
  "Service agreement with aggressive SLA targets. 99.9% uptime commitment with substantial penalties. Insurance coverage gap identified.",
  "Software license with enterprise-wide deployment. Compliance risk due to missing audit clause. Recommended: add right-to-audit provision.",
  "Consulting agreement with time-and-materials pricing. Low risk profile. Standard indemnification, 30-day termination notice. No action required.",
  "Lease agreement for data center facilities. Auto-renewal risk identified. Current terms are 15% below market but renewal may trigger market-rate adjustment.",
];

// ── Generate 60 contracts ───────────────────────────────────────────────────

export const contractRecords: ContractRecord[] = Array.from({ length: 60 }, (_, i) => {
  const riskScore = rand(2, 10);
  const riskLevel = riskScore >= 8 ? "critical" : riskScore >= 6 ? "high" : riskScore >= 4 ? "medium" : "low";
  const value = +(rand(10, 9500) / 100).toFixed(1);
  const daysToRenewal = rand(-60, 365);
  const status: ContractStatus = daysToRenewal <= 0 ? "expired" : daysToRenewal <= 90 ? "expiring_soon" : pick(["active", "under_review", "pending_signature"]) as ContractStatus;
  const vendor = pick(vendors);
  const ct = pick(contractTypes);
  const stage: WorkflowStage = status === "expired" ? "archived" : status === "pending_signature" ? "approval" : status === "under_review" ? "review" : pick(["executed", "renewal"]) as WorkflowStage;
  const reviewStatus =
    stage === "archived" ? "archived"
    : stage === "approval" ? "approved"
    : stage === "review" ? "in_review"
    : stage === "executed" ? "executed"
    : "draft";
  const slaStatus =
    reviewStatus === "archived" ? "on_track"
    : status === "expired" ? "critical_overdue"
    : status === "expiring_soon" ? "overdue"
    : "on_track";

  return {
    id: `CON-${2026001 + i}`,
    name: `${ct} - ${vendor}`,
    vendor,
    contractType: ct,
    businessUnit: pick(businessUnits),
    riskScore,
    riskLevel,
    financialValue: value,
    currency: "USD",
    status,
    reviewStatus,
    renewalDate: new Date(Date.now() + daysToRenewal * 86400000).toISOString().split("T")[0],
    aiConfidence: rand(72, 99),
    owner: pick(owners),
    workflowStage: stage,
    lastModified: new Date(Date.now() - rand(0, 90) * 86400000).toISOString().split("T")[0],
    tags: pickN(tags, rand(1, 4)),
    geography: pick(geographies),
    counterparty: vendor,
    description: `${ct} agreement with ${vendor} for ${pick(["cloud infrastructure", "software licensing", "professional services", "data processing", "supply chain", "marketing services", "IT support", "consulting"])}.`,
    aiSummary: pick(aiSummaries),
    clauseCount: rand(8, 24),
    missingClauses: pickN(missingClausePool, rand(0, 3)),
    aiFlags: riskScore >= 7 ? pickN([...aiFlags], rand(1, 3)) : riskScore >= 4 ? pickN([...aiFlags], rand(0, 1)) : [],
    obligationsDue: rand(0, 8),
    hasRedlines: Math.random() > 0.6,
    hasDpa: Math.random() > 0.3,
    autoRenew: Math.random() > 0.55,
    slaStatus,
    health: status === "expired" ? "expired" : status === "expiring_soon" ? "expiring_soon" : "healthy",
    totalPages: rand(3, 45),
    createdAt: new Date(Date.now() - rand(30, 730) * 86400000).toISOString().split("T")[0],
  };
});

// ── KPI Metrics ─────────────────────────────────────────────────────────────

export const contractKpis: ContractKpi[] = [
  { id: "total", label: "Total Contracts", value: "60", trend: 8.3, trendDirection: "up", icon: "FileText", color: "from-navy-600 to-navy-800", sparklineData: [42, 45, 48, 50, 52, 55, 58, 60], tooltip: "Total active contracts in repository" },
  { id: "under-review", label: "Under Review", value: "14", trend: -12.5, trendDirection: "down", icon: "Search", color: "from-blue-500 to-blue-700", sparklineData: [18, 17, 16, 15, 14, 14, 13, 14], tooltip: "Contracts currently in review workflow" },
  { id: "high-risk", label: "High Risk", value: "28", trend: 16.7, trendDirection: "up", icon: "AlertTriangle", color: "from-red-500 to-orange-500", sparklineData: [20, 22, 24, 23, 25, 26, 27, 28], tooltip: "Contracts with risk score ≥ 6" },
  { id: "expiring", label: "Expiring This Quarter", value: "18", trend: -10.0, trendDirection: "down", icon: "Clock", color: "from-yellow-500 to-orange-500", sparklineData: [22, 21, 20, 19, 19, 18, 17, 18], tooltip: "Contracts expiring within the current quarter" },
  { id: "auto-renewals", label: "Auto-Renewals", value: "24", trend: 4.3, trendDirection: "up", icon: "RefreshCw", color: "from-amber-500 to-yellow-500", sparklineData: [20, 21, 21, 22, 22, 23, 23, 24], tooltip: "Contracts with auto-renewal clauses" },
  { id: "ai-flags", label: "AI Flags Detected", value: "142", trend: 22.8, trendDirection: "up", icon: "Brain", color: "from-purple-500 to-indigo-500", sparklineData: [85, 92, 100, 108, 115, 122, 132, 142], tooltip: "Total AI-identified issues across all contracts" },
  { id: "pending-signatures", label: "Pending Signatures", value: "7", trend: -30.0, trendDirection: "down", icon: "PenSquare", color: "from-teal-500 to-green-500", sparklineData: [12, 11, 10, 9, 8, 8, 7, 7], tooltip: "Contracts awaiting signature" },
  { id: "total-value", label: "Total Contract Value", value: "$142.8M", trend: 12.1, trendDirection: "up", icon: "DollarSign", color: "from-green-500 to-emerald-500", sparklineData: [98, 105, 112, 118, 125, 132, 138, 142.8], tooltip: "Aggregated value of all contracts" },
];

// ── Saved Views ─────────────────────────────────────────────────────────────

export const savedViews: SavedView[] = [
  { id: "view-1", name: "All Contracts", filters: { search: "", vendor: "", geography: "", contractType: "", businessUnit: "", owner: "", riskLevel: "", status: "", workflowStage: "", aiConfidence: "", expirationRange: "" }, isDefault: true },
  { id: "view-2", name: "High Risk", filters: { search: "", vendor: "", geography: "", contractType: "", businessUnit: "", owner: "", riskLevel: "high", status: "", workflowStage: "", aiConfidence: "", expirationRange: "" }, isDefault: false },
  { id: "view-3", name: "Expiring Soon", filters: { search: "", vendor: "", geography: "", contractType: "", businessUnit: "", owner: "", riskLevel: "", status: "expiring_soon", workflowStage: "", aiConfidence: "", expirationRange: "90" }, isDefault: false },
  { id: "view-4", name: "Missing DPA Clauses", filters: { search: "missing DPA", vendor: "", geography: "", contractType: "", businessUnit: "", owner: "", riskLevel: "", status: "", workflowStage: "", aiConfidence: "", expirationRange: "" }, isDefault: false },
  { id: "view-5", name: "My Contracts", filters: { search: "", vendor: "", geography: "", contractType: "", businessUnit: "", owner: "Alice Chen", riskLevel: "", status: "", workflowStage: "", aiConfidence: "", expirationRange: "" }, isDefault: false },
];

// ── Activity Events ─────────────────────────────────────────────────────────

export const activityEvents: ActivityEvent[] = [
  { id: "act-1", type: "upload", user: "Alice Chen", action: "Uploaded MSA - Acme Corp", timestamp: new Date(Date.now() - 1800000).toISOString(), details: "24 pages, OCR completed" },
  { id: "act-2", type: "analysis", user: "AI System", action: "Risk analysis complete: SecureNet Solutions", timestamp: new Date(Date.now() - 3600000).toISOString(), details: "3 critical flags detected" },
  { id: "act-3", type: "review", user: "Bob Martinez", action: "Started review: GlobalTech Inc SOW", timestamp: new Date(Date.now() - 7200000).toISOString() },
  { id: "act-4", type: "comment", user: "Carol Singh", action: "Commented on DataSync Partners agreement", timestamp: new Date(Date.now() - 10800000).toISOString(), details: "Need to review liability cap in Section 4.2" },
  { id: "act-5", type: "redline", user: "AI System", action: "Redlines generated for CloudServ Ltd", timestamp: new Date(Date.now() - 14400000).toISOString(), details: "8 suggestions, 3 auto-accepted" },
  { id: "act-6", type: "approval", user: "David Kim", action: "Approved renewal: Pacific Rim Trading", timestamp: new Date(Date.now() - 18000000).toISOString() },
  { id: "act-7", type: "signature", user: "Eve Johnson", action: "Contract executed: InnoVate LLC License", timestamp: new Date(Date.now() - 21600000).toISOString() },
  { id: "act-8", type: "upload", user: "Frank Wilson", action: "Batch uploaded 5 contracts", timestamp: new Date(Date.now() - 25200000).toISOString(), details: "OCR processing, AI extraction in progress" },
];

// ── Clause Analysis (for preview drawer) ────────────────────────────────────

export const mockClauses: ClauseSummary[] = [
  { type: "Indemnification", risk: "critical", text: "Provider shall indemnify Client for all claims including indirect and consequential damages.", suggestion: "Cap indemnification at 100% of fees paid, exclude consequential damages." },
  { type: "Liability Cap", risk: "high", text: "Neither party's aggregate liability shall exceed $100.", suggestion: "Increase liability cap to 12 months of fees (approx. $500K)." },
  { type: "Termination", risk: "medium", text: "Either party may terminate for convenience upon 30 days notice.", suggestion: "Extend notice period to 60 days for client, 90 days for provider." },
  { type: "Confidentiality", risk: "low", text: "Confidential Information excludes information independently developed.", suggestion: "Standard clause — no changes needed." },
  { type: "Data Privacy", risk: "high", text: "No specific GDPR data processing clauses included.", suggestion: "Add GDPR-compliant data processing addendum (DPA)." },
  { type: "Auto-Renewal", risk: "warning", text: "This agreement shall automatically renew for successive 1-year terms.", suggestion: "Add 60-day notice period for non-renewal." },
];

// ── Obligations ─────────────────────────────────────────────────────────────

export const mockObligations: Obligation[] = [
  { id: "obl-1", description: "Submit SOC2 Type II report", dueDate: "2026-06-15", owner: "SecureNet Solutions", status: "pending" },
  { id: "obl-2", description: "Renew cyber liability insurance ($5M)", dueDate: "2026-05-30", owner: "Acme Corp", status: "overdue" },
  { id: "obl-3", description: "Provide quarterly uptime report", dueDate: "2026-06-01", owner: "CloudServ Ltd", status: "pending" },
  { id: "obl-4", description: "GDPR data processing registration", dueDate: "2026-07-01", owner: "EuroLegal Partners", status: "pending" },
  { id: "obl-5", description: "IP assignment documentation", dueDate: "2026-05-20", owner: "InnoVate LLC", status: "completed" },
];

// ── Related Contracts ───────────────────────────────────────────────────────

export const mockRelatedContracts: RelatedContract[] = [
  { id: "CON-2026001", name: "MSA - Acme Corp", relationship: "Parent Agreement", riskScore: 8 },
  { id: "CON-2026005", name: "SOW - Acme Corp (Q2)", relationship: "Statement of Work", riskScore: 6 },
  { id: "CON-2026012", name: "NDA - Acme Corp", relationship: "Related NDA", riskScore: 3 },
  { id: "CON-2026020", name: "License - Acme Corp", relationship: "Addendum", riskScore: 5 },
];

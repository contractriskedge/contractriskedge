// ── Enterprise Clause Library Mock Data ─────────────────────────────────────

import type { ClauseKpi, ClauseRecord, ClauseVariant, Playbook, BenchmarkData } from "./types";

function rand(min: number, max: number) { return Math.floor(Math.random() * (max - min + 1)) + min; }
function pick<T>(arr: T[]): T { return arr[rand(0, arr.length - 1)]; }
function pickN<T>(arr: T[], n: number): T[] { const s = [...arr].sort(() => Math.random() - 0.5); return s.slice(0, n); }

const JURISDICTIONS = ["New York", "Delaware", "California", "England & Wales", "Singapore", "Hong Kong", "Ontario", "Germany", "France", "Australia"];
const CONTRACT_TYPES = ["MSA", "SOW", "NDA", "License", "Service Agreement", "Partnership", "SaaS Agreement", "Employment", "Lease", "Consulting"];
const OWNERS = ["Alice Chen", "Bob Martinez", "Carol Singh", "David Kim", "Eve Johnson", "Frank Wilson"];
const TAGS = ["high-risk", "standard", "preferred", "vendor-friendly", "client-friendly", "gdpr", "hipaa", "enterprise", "startup", "international"];

const CLAUSE_TEXTS: Record<string, { text: string; explanation: string; guidance: string }> = {
  indemnification: {
    text: "The Provider shall indemnify, defend, and hold harmless the Customer from and against any and all claims, damages, losses, liabilities, and expenses arising out of or related to any breach of this Agreement by the Provider, including without limitation any third-party claims alleging infringement of intellectual property rights.",
    explanation: "This is a broad indemnification clause favoring the indemnified party. Market standard is mutual indemnification capped at fees paid. Consider adding materiality qualifiers and IP infringement exceptions.",
    guidance: "Preferred position: Mutual indemnification capped at 100% of fees. Fallback 1: Mutual capped at 200% fees. Fallback 2: One-way vendor indemnification for IP infringement only. Do not accept uncapped indemnification.",
  },
  liability_cap: {
    text: "In no event shall either party's aggregate liability exceed the total fees paid by Customer to Provider during the twelve (12) months immediately preceding the claim. This limitation applies regardless of the theory of liability.",
    explanation: "Standard liability cap at 100% of annual fees. Market median is also 100% of fees. This is a balanced clause that aligns with enterprise norms.",
    guidance: "Preferred position: 100% of fees paid. Acceptable range: 100-200% of fees. Escalate if vendor proposes cap below 12 months of fees or above 300%.",
  },
  termination: {
    text: "Either party may terminate this Agreement upon thirty (30) days written notice. Either party may terminate immediately for material breach that remains uncured for thirty (30) days after written notice.",
    explanation: "Standard termination clause with mutual 30-day for convenience and 30-day cure period for breach. Market aligned.",
    guidance: "Preferred: 30-day for convenience, 30-day cure. Fallback: 60-day for convenience, 30-day cure. Avoid asymmetric termination rights.",
  },
  confidentiality: {
    text: "The Receiving Party shall maintain all Confidential Information in strict confidence and shall not disclose such information to any third party without the Disclosing Party's prior written consent. Confidentiality obligations shall survive for a period of three (3) years.",
    explanation: "Standard mutual confidentiality with 3-year survival. Market standard is 2-5 years. This clause is well-aligned with enterprise norms.",
    guidance: "Preferred: 3-year survival. Acceptable: 2-5 years. Ensure mutual obligations and standard exclusions for independently developed information.",
  },
  data_privacy: {
    text: "Each party shall comply with all applicable data protection laws. Provider shall maintain reasonable administrative, physical, and technical safeguards for the protection of Personal Data. Upon request, the parties shall enter into a Data Processing Agreement.",
    explanation: "This clause references DPA but lacks specific GDPR/CCPA compliance language. Consider adding more specific regulatory references and data breach notification timelines.",
    guidance: "Preferred: Include specific GDPR/CCPA references and 72-hour breach notification. Fallback: General compliance language with DPA reference. Must include DPA for EU/California data.",
  },
  force_majeure: {
    text: "Neither party shall be liable for any failure or delay in performance caused by acts of God, war, terrorism, natural disasters, pandemics, public health emergencies, or other events beyond the reasonable control of the affected party.",
    explanation: "Modern force majeure clause with pandemic coverage. This is current market standard post-2020. Well-drafted and comprehensive.",
    guidance: "Preferred: Include pandemics and public health emergencies. Ensure mutual applicability. Add notice requirement within reasonable time.",
  },
  auto_renewal: {
    text: "This Agreement shall automatically renew for successive one (1) year terms unless either party provides written notice of non-renewal at least ninety (90) days prior to the end of the then-current term.",
    explanation: "Auto-renewal with 90-day notice period. This is above market standard (60 days) and provides adequate time for review. Well-positioned for enterprise.",
    guidance: "Preferred: 90-day notice. Acceptable: 60-90 days. Reject anything below 30 days. Ensure opt-out mechanism is clearly defined.",
  },
  ip_ownership: {
    text: "All intellectual property rights in any deliverables, work product, or materials created by Provider under this Agreement shall vest in Customer upon full payment of all amounts due. Provider retains the right to use general methodologies and know-how.",
    explanation: "Customer-friendly IP clause with ownership upon payment. Provider retains only methodologies. This is the preferred enterprise position.",
    guidance: "Preferred: Customer owns all custom IP. Fallback: Joint ownership with customer license. Avoid vendor ownership with only license to customer.",
  },
};

function generateClause(key: string, idx: number): ClauseRecord {
  const ct = CLAUSE_TEXTS[key] || CLAUSE_TEXTS.indemnification;
  const riskScore = key === "indemnification" ? 8.5 : key === "liability_cap" ? 5.0 : key === "termination" ? 4.5 : key === "confidentiality" ? 3.8 : key === "data_privacy" ? 6.5 : key === "force_majeure" ? 3.2 : key === "auto_renewal" ? 6.0 : key === "ip_ownership" ? 4.0 : rand(2, 8);
  const rl = riskScore >= 8 ? "critical" : riskScore >= 6 ? "high" : riskScore >= 4 ? "medium" : "low";
  const variants: ClauseVariant[] = [
    { id: `${key}-v1`, label: "Standard", text: ct.text, riskScore, negotiationStrength: key === "indemnification" ? 65 : key === "liability_cap" ? 80 : key === "ip_ownership" ? 85 : 75, usageRate: rand(40, 80), isPreferred: true },
    { id: `${key}-v2`, label: "Vendor-Friendly", text: ct.text.replace("Customer", "Provider").replace("Provider", "Customer"), riskScore: Math.min(10, riskScore + 2), negotiationStrength: Math.max(10, (key === "indemnification" ? 65 : 75) - 15), usageRate: rand(10, 30), isPreferred: false },
    { id: `${key}-v3`, label: "Balanced", text: ct.text, riskScore: Math.max(1, riskScore - 1), negotiationStrength: Math.min(100, (key === "indemnification" ? 65 : 75) + 10), usageRate: rand(20, 40), isPreferred: false },
  ];
  return {
    id: `CL-${2026001 + idx}`, name: `${key.replace(/_/g, " ")} Clause`, category: key, text: ct.text,
    riskScore, riskLevel: rl, jurisdiction: pick(JURISDICTIONS), contractTypes: pickN(CONTRACT_TYPES, rand(2, 5)),
    benchmarkPercentile: riskScore >= 7 ? rand(75, 95) : riskScore >= 5 ? rand(45, 70) : rand(20, 45),
    usageFrequency: rand(50, 500), approvalStatus: pick(["approved", "approved", "approved", "pending_review", "deprecated"]),
    lastUpdated: new Date(Date.now() - rand(0, 180) * 86400000).toISOString().split("T")[0],
    owner: pick(OWNERS), aiConfidence: rand(78, 97), negotiationStrength: key === "indemnification" ? 65 : key === "liability_cap" ? 80 : key === "ip_ownership" ? 85 : key === "force_majeure" ? 72 : key === "confidentiality" ? 78 : 75,
    fallbackVariants: variants, versions: rand(2, 8), isFavorite: Math.random() > 0.7,
    tags: pickN(TAGS, rand(2, 4)), aiExplanation: ct.explanation, negotiationGuidance: ct.guidance, governanceNotes: `Last reviewed by ${pick(OWNERS)}. Next review: ${new Date(Date.now() + rand(30, 180) * 86400000).toISOString().split("T")[0]}.`,
  };
}

const CLAUSE_KEYS = ["indemnification", "liability_cap", "termination", "confidentiality", "data_privacy", "force_majeure", "auto_renewal", "ip_ownership"];

export const clauseRecords: ClauseRecord[] = Array.from({ length: 48 }, (_, i) => {
  const key = CLAUSE_KEYS[i % CLAUSE_KEYS.length];
  return generateClause(key, i);
});

// ── KPI Metrics ─────────────────────────────────────────────────────────────

export const clauseKpis: ClauseKpi[] = [
  { id: "total-clauses", label: "Total Approved Clauses", value: "156", trend: 8.3, trendDirection: "up", icon: "FileText", color: "from-navy-600 to-navy-800", severity: "info", sparklineData: [120, 125, 130, 135, 140, 145, 150, 156], tooltip: "Total approved clauses in the library" },
  { id: "most-used", label: "Most Used Clauses", value: "Indemnification", trend: 12.5, trendDirection: "up", icon: "TrendingUp", color: "from-blue-500 to-indigo-500", severity: "info", sparklineData: [180, 195, 210, 225, 240, 260, 280, 310], tooltip: "Most frequently used clause type this quarter" },
  { id: "deviations", label: "Benchmark Deviations", value: "14", trend: -17.6, trendDirection: "down", icon: "BarChart3", color: "from-orange-500 to-red-500", severity: "warning", sparklineData: [22, 20, 19, 18, 17, 16, 15, 14], tooltip: "Clauses deviating significantly from market benchmarks" },
  { id: "success-rate", label: "Negotiation Success Rate", value: "87%", trend: 4.8, trendDirection: "up", icon: "CheckCircle", color: "from-green-500 to-emerald-500", severity: "success", sparklineData: [78, 80, 81, 82, 83, 85, 86, 87], tooltip: "Percentage of negotiations using preferred clauses" },
  { id: "reuse-rate", label: "Clause Reuse Rate", value: "72%", trend: 5.9, trendDirection: "up", icon: "RefreshCw", color: "from-teal-500 to-green-500", severity: "success", sparklineData: [62, 64, 65, 67, 68, 70, 71, 72], tooltip: "Percentage of contracts reusing approved clauses" },
  { id: "jurisdictions", label: "Jurisdiction Variants", value: "10", trend: 11.1, trendDirection: "up", icon: "Globe", color: "from-purple-500 to-pink-500", severity: "info", sparklineData: [7, 7, 8, 8, 9, 9, 9, 10], tooltip: "Number of jurisdiction-specific clause variants" },
  { id: "ai-improvements", label: "AI Suggested Improvements", value: "23", trend: 27.8, trendDirection: "up", icon: "Brain", color: "from-indigo-500 to-purple-500", severity: "info", sparklineData: [12, 14, 15, 17, 18, 20, 22, 23], tooltip: "AI-generated clause improvement suggestions" },
  { id: "deprecated", label: "Deprecated Clauses", value: "8", trend: -11.1, trendDirection: "down", icon: "Archive", color: "from-gray-500 to-gray-600", severity: "info", sparklineData: [12, 11, 11, 10, 10, 9, 9, 8], tooltip: "Clauses marked as deprecated" },
];

// ── Playbooks ───────────────────────────────────────────────────────────────

export const playbooks: Playbook[] = [
  { id: "pb-1", name: "Standard MSA Playbook", description: "Preferred positions for Master Service Agreements across all jurisdictions", type: "negotiation", jurisdiction: "Global", contractTypes: ["MSA", "Service Agreement"], clauses: ["CL-2026001", "CL-2026002", "CL-2026003", "CL-2026004"], rules: [{ id: "pr-1", condition: "Contract value > $1M", action: "Require VP Legal approval", priority: 1, enabled: true }, { id: "pr-2", condition: "Uncapped liability proposed", action: "Escalate to General Counsel", priority: 2, enabled: true }], successRate: 92, usageCount: 345, lastUpdated: "2026-05-10", owner: "Alice Chen" },
  { id: "pb-2", name: "GDPR Compliance Playbook", description: "Data privacy clauses for EU counterparties with GDPR requirements", type: "compliance", jurisdiction: "EU/EEA", contractTypes: ["MSA", "SaaS Agreement", "Service Agreement"], clauses: ["CL-2026005", "CL-2026006"], rules: [{ id: "pr-3", condition: "EU data processing", action: "Must include DPA addendum", priority: 1, enabled: true }], successRate: 95, usageCount: 189, lastUpdated: "2026-05-08", owner: "Bob Martinez" },
  { id: "pb-3", name: "Vendor-Friendly Software License", description: "Balanced positions for software licensing negotiations", type: "negotiation", jurisdiction: "Global", contractTypes: ["License", "SaaS Agreement"], clauses: ["CL-2026007", "CL-2026008", "CL-2026001"], rules: [{ id: "pr-4", condition: "Per-seat pricing > $100/mo", action: "Request volume discount", priority: 2, enabled: true }], successRate: 85, usageCount: 234, lastUpdated: "2026-05-05", owner: "Carol Singh" },
  { id: "pb-4", name: "APAC Region Playbook", description: "Jurisdiction-specific clauses for Asia Pacific contracts", type: "jurisdiction", jurisdiction: "APAC", contractTypes: ["MSA", "Partnership", "License"], clauses: ["CL-2026003", "CL-2026004", "CL-2026006"], rules: [{ id: "pr-5", condition: "Singapore governing law", action: "Use Singapore-specific termination clause", priority: 1, enabled: true }], successRate: 88, usageCount: 156, lastUpdated: "2026-04-28", owner: "David Kim" },
  { id: "pb-5", name: "Financial Services Compliance", description: "Regulatory compliance clauses for financial services vendors", type: "compliance", jurisdiction: "Global", contractTypes: ["MSA", "Service Agreement", "SaaS Agreement"], clauses: ["CL-2026005", "CL-2026006", "CL-2026002"], rules: [{ id: "pr-6", condition: "FINRA regulated vendor", action: "Add regulatory compliance addendum", priority: 1, enabled: true }], successRate: 90, usageCount: 98, lastUpdated: "2026-04-20", owner: "Eve Johnson" },
];

// ── Benchmark Data ──────────────────────────────────────────────────────────

export const benchmarkData: BenchmarkData[] = [
  { clauseType: "Indemnification", yourScore: 8.5, marketMedian: 5.2, marketP25: 3.5, marketP75: 6.8, percentile: 92, sampleSize: 2847 },
  { clauseType: "Liability Cap", yourScore: 5.0, marketMedian: 4.5, marketP25: 3.0, marketP75: 6.0, percentile: 55, sampleSize: 2654 },
  { clauseType: "Termination", yourScore: 4.5, marketMedian: 4.8, marketP25: 3.2, marketP75: 6.2, percentile: 42, sampleSize: 3120 },
  { clauseType: "Confidentiality", yourScore: 3.8, marketMedian: 3.8, marketP25: 2.5, marketP75: 5.0, percentile: 50, sampleSize: 2890 },
  { clauseType: "Data Privacy", yourScore: 6.5, marketMedian: 5.5, marketP25: 4.0, marketP75: 7.0, percentile: 68, sampleSize: 2156 },
  { clauseType: "Force Majeure", yourScore: 3.2, marketMedian: 4.5, marketP25: 3.0, marketP75: 6.0, percentile: 28, sampleSize: 1890 },
  { clauseType: "Auto-Renewal", yourScore: 6.0, marketMedian: 4.0, marketP25: 2.5, marketP75: 5.5, percentile: 78, sampleSize: 1250 },
  { clauseType: "IP Ownership", yourScore: 4.0, marketMedian: 5.0, marketP25: 3.5, marketP75: 6.5, percentile: 35, sampleSize: 1890 },
];

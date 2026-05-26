// ── Enterprise Contract Detail Mock Data ────────────────────────────────────

import type { ContractDocument, ClauseData, VersionRecord, ActivityEvent, NegotiationIssue, WorkflowState } from "./types";

function rand(min: number, max: number) { return Math.floor(Math.random() * (max - min + 1)) + min; }

// ── Clause Data ─────────────────────────────────────────────────────────────

const clauseTexts: Record<string, { text: string; risk: number; explanation: string; fallback: string }> = {
  indemnification: {
    text: "The Provider shall indemnify, defend, and hold harmless the Customer from and against any and all claims, damages, losses, liabilities, and expenses arising out of or related to any breach of this Agreement by the Provider, including without limitation any third-party claims alleging infringement of intellectual property rights.",
    risk: 8.5, explanation: "This clause has uncapped indemnification with no materiality qualifier. Market standard is mutual indemnification capped at fees paid. This exposes the client to potentially unlimited liability.",
    fallback: "Each party shall indemnify the other for claims arising from breach of confidentiality and IP infringement, capped at the total fees paid under this agreement.",
  },
  liability_cap: {
    text: "In no event shall either party's aggregate liability exceed One Hundred Dollars ($100.00). This limitation applies regardless of the theory of liability and notwithstanding any failure of essential purpose of any limited remedy.",
    risk: 7.8, explanation: "The $100 liability cap is extremely low and may be unenforceable in many jurisdictions. Market median is 100% of fees paid. This could be struck down by courts.",
    fallback: "Neither party's aggregate liability shall exceed the total fees paid by Customer to Provider during the twelve (12) months preceding the claim.",
  },
  termination: {
    text: "This Agreement may be terminated by either party upon thirty (30) days written notice. Provider may also terminate this Agreement immediately if Customer fails to pay any amounts due within fifteen (15) days of the due date.",
    risk: 6.5, explanation: "Termination for convenience is mutual at 30 days, which is standard. However, provider-only termination rights for non-payment with only 15-day cure period is aggressive.",
    fallback: "Either party may terminate for convenience upon sixty (60) days written notice. Either party may terminate for material breach with thirty (30) days cure period.",
  },
  confidentiality: {
    text: "The Receiving Party shall maintain all Confidential Information in strict confidence and shall not disclose such information to any third party without the Disclosing Party's prior written consent. Confidentiality obligations shall survive for a period of three (3) years.",
    risk: 4.2, explanation: "Standard confidentiality clause with 3-year survival. Mutual obligations. No unusual provisions detected. Aligned with market standards.",
    fallback: "",
  },
  data_privacy: {
    text: "Each party shall comply with all applicable data protection laws. Provider shall maintain reasonable administrative, physical, and technical safeguards for the protection of Personal Data.",
    risk: 6.8, explanation: "No specific GDPR or CCPA data processing terms. Missing DPA reference. No data breach notification timeline. Should include specific regulatory compliance language.",
    fallback: "Provider shall comply with GDPR, CCPA, and all applicable data protection laws. The parties shall enter into a Data Processing Agreement in the form attached hereto as Schedule A.",
  },
  force_majeure: {
    text: "Neither party shall be liable for any failure or delay in performance caused by acts of God, war, terrorism, natural disasters, or other events beyond the reasonable control of the affected party.",
    risk: 3.8, explanation: "Standard force majeure clause. No pandemic or public health crisis language. Consider adding explicit pandemic coverage given recent market evolution.",
    fallback: "Force majeure includes pandemics, public health emergencies, government orders, and supply chain disruptions beyond the affected party's reasonable control.",
  },
  auto_renewal: {
    text: "This Agreement shall automatically renew for successive one (1) year terms unless either party provides written notice of non-renewal at least thirty (30) days prior to the end of the then-current term.",
    risk: 6.2, explanation: "Auto-renewal with only 30-day notice period is below market standard of 60-90 days. Risk of unfavorable automatic renewal without adequate review time.",
    fallback: "This Agreement shall automatically renew for successive one-year terms unless either party provides written notice at least ninety (90) days prior to expiration.",
  },
  ip_ownership: {
    text: "All intellectual property rights in any deliverables, work product, or materials created by Provider under this Agreement shall be owned exclusively by Provider. Customer receives a non-exclusive, non-transferable license to use such deliverables.",
    risk: 7.5, explanation: "IP ownership remains with Provider — highly vendor-favorable. Market standard is customer ownership of custom-developed IP. Only a license is insufficient for most enterprises.",
    fallback: "All intellectual property rights in deliverables shall vest in Customer upon full payment. Provider retains the right to use general methodologies and know-how.",
  },
};

// ── Build clauses ───────────────────────────────────────────────────────────

const clauseOrder = [
  { id: "cl-1", section: "1", title: "Definitions", category: "General", text: "As used in this Agreement, the following terms shall have the meanings set forth below...", risk: 2.0 },
  { id: "cl-2", section: "2", title: "Scope of Services", category: "Services", text: "Provider shall provide the Services described in Exhibit A attached hereto...", risk: 3.0 },
  { id: "cl-3", section: "3", title: "Fees and Payment", category: "Financial", text: "Customer shall pay Provider the fees set forth in Exhibit A within thirty (30) days of receipt of invoice...", risk: 5.5 },
  { id: "cl-4", section: "4", title: "Indemnification", category: "Liability", text: clauseTexts.indemnification.text, risk: 8.5 },
  { id: "cl-5", section: "5", title: "Limitation of Liability", category: "Liability", text: clauseTexts.liability_cap.text, risk: 7.8 },
  { id: "cl-6", section: "6", title: "Term and Termination", category: "Rights", text: clauseTexts.termination.text, risk: 6.5 },
  { id: "cl-7", section: "7", title: "Confidentiality", category: "Protection", text: clauseTexts.confidentiality.text, risk: 4.2 },
  { id: "cl-8", section: "8", title: "Data Privacy and Security", category: "Compliance", text: clauseTexts.data_privacy.text, risk: 6.8 },
  { id: "cl-9", section: "9", title: "Intellectual Property", category: "IP", text: clauseTexts.ip_ownership.text, risk: 7.5 },
  { id: "cl-10", section: "10", title: "Representations and Warranties", category: "General", text: "Each party represents and warrants that it has the full right and authority to enter into this Agreement...", risk: 3.2 },
  { id: "cl-11", section: "11", title: "Insurance", category: "Protection", text: "Provider shall maintain commercial general liability insurance with limits of not less than $1,000,000 per occurrence...", risk: 4.8 },
  { id: "cl-12", section: "12", title: "Force Majeure", category: "Rights", text: clauseTexts.force_majeure.text, risk: 3.8 },
  { id: "cl-13", section: "13", title: "Assignment", category: "Rights", text: "Neither party may assign this Agreement without the prior written consent of the other party...", risk: 4.5 },
  { id: "cl-14", section: "14", title: "Governing Law", category: "Legal", text: "This Agreement shall be governed by and construed in accordance with the laws of the State of New York...", risk: 5.2 },
  { id: "cl-15", section: "15", title: "Auto-Renewal", category: "Rights", text: clauseTexts.auto_renewal.text, risk: 6.2 },
  { id: "cl-16", section: "16", title: "Entire Agreement", category: "General", text: "This Agreement constitutes the entire agreement between the parties...", risk: 2.0 },
];

function getClauseStatus(risk: number): "acceptable" | "needs_review" | "needs_negotiation" | "unacceptable" {
  if (risk >= 8) return "unacceptable";
  if (risk >= 6) return "needs_negotiation";
  if (risk >= 4) return "needs_review";
  return "acceptable";
}

export const mockContract: ContractDocument = {
  id: "CON-2026001",
  name: "Master Service Agreement - SecureNet Solutions",
  vendor: "SecureNet Solutions",
  contractType: "MSA",
  status: "under_review",
  riskScore: 7.2,
  riskLevel: "high",
  pages: 24,
  clauses: clauseOrder.map((c) => {
    const key = c.id === "cl-4" ? "indemnification" : c.id === "cl-5" ? "liability_cap" : c.id === "cl-6" ? "termination" : c.id === "cl-7" ? "confidentiality" : c.id === "cl-8" ? "data_privacy" : c.id === "cl-12" ? "force_majeure" : c.id === "cl-15" ? "auto_renewal" : c.id === "cl-9" ? "ip_ownership" : null;
    const ct = key ? clauseTexts[key] : null;
    const riskScore = ct?.risk || c.risk;
    return {
      id: c.id, section: c.section, title: c.title, text: c.text, category: c.category,
      riskScore, riskLevel: riskScore >= 8 ? "critical" : riskScore >= 6 ? "high" : riskScore >= 4 ? "medium" : "low",
      status: getClauseStatus(riskScore),
      aiExplanation: ct?.explanation || "Standard clause aligned with market norms.",
      benchmarkPercentile: riskScore >= 8 ? rand(85, 95) : riskScore >= 6 ? rand(65, 80) : riskScore >= 4 ? rand(40, 60) : rand(20, 40),
      confidence: rand(78, 96),
      fallbackLanguage: ct?.fallback || undefined,
      annotations: riskScore >= 6 ? [{ id: `ann-${c.id}`, type: "risk", text: `High risk clause — score ${riskScore}/10`, startOffset: 0, endOffset: 50, severity: riskScore >= 8 ? "critical" : "high", createdBy: "AI System", createdAt: new Date().toISOString(), resolved: false }] : [],
      comments: c.id === "cl-4" ? [
        { id: `cmt-${c.id}-1`, author: "Alice Chen", body: "This indemnification clause needs immediate attention — uncapped liability is unacceptable.", mentions: ["Bob Martinez"], createdAt: new Date(Date.now() - 7200000).toISOString(), resolved: false, isResolving: false },
        { id: `cmt-${c.id}-2`, author: "Bob Martinez", body: "Agreed. I've seen SecureNet use this language before. We should counter with mutual capped at fees.", mentions: [], createdAt: new Date(Date.now() - 3600000).toISOString(), resolved: false, isResolving: false },
      ] : [],
      isRedlined: c.id === "cl-4" || c.id === "cl-5",
      redlinedText: c.id === "cl-4" ? clauseTexts.indemnification.fallback : c.id === "cl-5" ? clauseTexts.liability_cap.fallback : undefined,
      obligations: c.category === "Financial" ? [{ id: `obl-${c.id}-1`, description: "Pay invoice within 30 days", type: "payment", dueDate: "2026-06-15", owner: "Accounts Payable", status: "pending", clauseId: c.id }] :
        c.id === "cl-11" ? [{ id: `obl-${c.id}-1`, description: "Provide proof of insurance", type: "insurance", dueDate: "2026-05-30", owner: "SecureNet Solutions", status: "overdue", clauseId: c.id }] : [],
    };
  }),
  parties: ["Customer Company Inc.", "SecureNet Solutions LLC"],
  effectiveDate: "2026-01-15",
  expiryDate: "2027-01-14",
  governingLaw: "New York, USA",
  jurisdiction: "New York County, NY",
  value: 3.5,
  currency: "USD",
  owner: "Alice Chen",
  department: "Legal",
  businessUnit: "North America",
  aiSummary: "This MSA with SecureNet Solutions presents elevated risk (7.2/10) primarily due to uncapped indemnification and an extremely low $100 liability cap. Key concerns include IP ownership remaining with vendor, auto-renewal with only 30-day notice, and missing GDPR-specific data privacy language. Recommended actions: (1) Cap indemnification at fees paid, (2) Increase liability cap to market standard, (3) Secure IP ownership for custom work, (4) Extend auto-renewal notice to 90 days.",
  version: 3,
  lastModified: new Date(Date.now() - 3600000).toISOString(),
  created: "2026-01-10",
};

// ── Version History ─────────────────────────────────────────────────────────

export const versionHistory: VersionRecord[] = [
  { id: "ver-1", version: 1, date: "2026-01-10", author: "SecureNet Solutions", summary: "Initial draft", changes: 0, isCurrent: false },
  { id: "ver-2", version: 2, date: "2026-01-20", author: "Alice Chen", summary: "Redlined indemnification and liability cap", changes: 2, isCurrent: false },
  { id: "ver-3", version: 3, date: "2026-05-14", author: "SecureNet Solutions", summary: "Responded to redlines — rejected liability cap change, proposed compromise on indemnification", changes: 4, isCurrent: true },
];

// ── Activity ────────────────────────────────────────────────────────────────

export const activityEvents: ActivityEvent[] = [
  { id: "act-1", type: "version", user: "SecureNet Solutions", action: "Uploaded version 3", details: "Responded to redlines with counter-proposals", timestamp: new Date(Date.now() - 3600000).toISOString() },
  { id: "act-2", type: "comment", user: "Alice Chen", action: "Commented on Indemnification clause", details: "Flagged uncapped liability as unacceptable", timestamp: new Date(Date.now() - 7200000).toISOString() },
  { id: "act-3", type: "comment", user: "Bob Martinez", action: "Replied to comment on Indemnification", details: "Suggested mutual capped indemnification", timestamp: new Date(Date.now() - 3600000).toISOString() },
  { id: "act-4", type: "ai_action", user: "AI System", action: "Risk analysis completed", details: "7 clauses flagged — 2 critical, 3 high risk", timestamp: new Date(Date.now() - 10800000).toISOString() },
  { id: "act-5", type: "review", user: "Carol Singh", action: "Started legal review", details: "Assigned as primary reviewer", timestamp: new Date(Date.now() - 14400000).toISOString() },
  { id: "act-6", type: "workflow", user: "System", action: "Workflow moved to Legal Review", details: "Previous stage: AI Review completed", timestamp: new Date(Date.now() - 18000000).toISOString() },
];

// ── Negotiation Issues ──────────────────────────────────────────────────────

export const negotiationIssues: NegotiationIssue[] = [
  { id: "neg-1", clauseId: "cl-4", clauseTitle: "Indemnification", issue: "Uncapped indemnification — no materiality qualifier", yourPosition: "Mutual indemnification capped at fees paid", vendorPosition: "Uncapped for IP infringement, capped at 200% fees for others", recommendedPosition: "Mutual capped at 100% fees with IP infringement exception", status: "discussing", priority: "high", updatedAt: new Date(Date.now() - 3600000).toISOString() },
  { id: "neg-2", clauseId: "cl-5", clauseTitle: "Limitation of Liability", issue: "$100 liability cap — extremely low and potentially unenforceable", yourPosition: "Cap at 100% of fees paid (approx. $3.5M)", vendorPosition: "$100 cap — non-negotiable per vendor policy", recommendedPosition: "Cap at 100% of fees with mutual exclusion for consequential", status: "open", priority: "high", updatedAt: new Date(Date.now() - 7200000).toISOString() },
  { id: "neg-3", clauseId: "cl-9", clauseTitle: "Intellectual Property", issue: "IP ownership remains with vendor — only license granted", yourPosition: "Customer owns all custom-developed IP", vendorPosition: "Vendor retains ownership, customer receives license", recommendedPosition: "Customer ownership upon full payment, vendor retains methodologies", status: "open", priority: "medium", updatedAt: new Date(Date.now() - 10800000).toISOString() },
  { id: "neg-4", clauseId: "cl-15", clauseTitle: "Auto-Renewal", issue: "Only 30-day notice period — insufficient for enterprise review", yourPosition: "90-day notice period", vendorPosition: "30 days — standard for all vendor contracts", recommendedPosition: "60-day notice as compromise", status: "discussing", priority: "medium", updatedAt: new Date(Date.now() - 14400000).toISOString() },
];

// ── Workflow State ──────────────────────────────────────────────────────────

export const workflowState: WorkflowState = {
  currentStage: "legal_review",
  stages: [
    { id: "intake", label: "Intake", status: "completed" },
    { id: "ai_review", label: "AI Review", status: "completed" },
    { id: "legal_review", label: "Legal Review", status: "current", assignee: "Alice Chen" },
    { id: "procurement_review", label: "Procurement Review", status: "pending" },
    { id: "finance_approval", label: "Finance Approval", status: "pending" },
    { id: "executive_approval", label: "Executive Approval", status: "pending" },
    { id: "signature", label: "Signature", status: "pending" },
  ],
  slaRemaining: 36,
  escalationLevel: 0,
  reviewers: [
    { name: "Alice Chen", role: "Legal Counsel", status: "in_progress" },
    { name: "Bob Martinez", role: "Contract Analyst", status: "completed" },
    { name: "Carol Singh", role: "VP Legal", status: "pending" },
  ],
};

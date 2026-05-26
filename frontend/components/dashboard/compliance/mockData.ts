// ── Enterprise Compliance & Regulatory Intelligence Center Mock Data ─────

import type {
  ComplianceKpi, Regulation, ComplianceFinding, RemediationTask,
  VendorCompliance, VendorCertification, ComplianceAudit,
  AiComplianceInsight, CompliancePolicy, ComplianceAnalytics, ComplianceDetail,
} from "./types";

// ── KPI Data ─────────────────────────────────────────────────────────────

export const mockComplianceKpis: ComplianceKpi[] = [
  { id: "overall-score", label: "Overall Compliance Score", value: "78.4%", trend: 3.2, trendDirection: "up", icon: "Shield", color: "from-blue-500 to-blue-600", severity: "info", sparklineData: [72, 73.5, 74.8, 76.2, 77.1, 78.4], tooltip: "78.4% overall compliance score across all regulations" },
  { id: "open-gaps", label: "Open Compliance Gaps", value: "142", trend: -12, trendDirection: "down", icon: "AlertTriangle", color: "from-amber-500 to-amber-600", severity: "warning", sparklineData: [210, 195, 178, 162, 152, 142], tooltip: "142 open compliance gaps requiring remediation" },
  { id: "violations", label: "Regulatory Violations", value: "28", trend: -22, trendDirection: "down", icon: "Gavel", color: "from-red-500 to-red-600", severity: "critical", sparklineData: [52, 46, 40, 35, 31, 28], tooltip: "28 active regulatory violations identified" },
  { id: "missing-clauses", label: "Missing Required Clauses", value: "187", trend: -8, trendDirection: "down", icon: "FileSearch", color: "from-orange-500 to-orange-600", severity: "warning", sparklineData: [230, 218, 205, 195, 190, 187], tooltip: "187 contracts missing required compliance clauses" },
  { id: "expiring-docs", label: "Expiring Compliance Docs", value: "34", trend: 15, trendDirection: "up", icon: "Clock", color: "from-yellow-500 to-yellow-600", severity: "warning", sparklineData: [18, 22, 25, 28, 31, 34], tooltip: "34 compliance documents expiring within 90 days" },
  { id: "high-risk-vendors", label: "High-Risk Vendors", value: "18", trend: -10, trendDirection: "down", icon: "Building2", color: "from-red-500 to-red-600", severity: "critical", sparklineData: [28, 25, 23, 21, 19, 18], tooltip: "18 vendors with high compliance risk scores" },
  { id: "audit-readiness", label: "Audit Readiness Score", value: "82.6%", trend: 4.5, trendDirection: "up", icon: "ClipboardCheck", color: "from-green-500 to-green-600", severity: "success", sparklineData: [74, 76.5, 78.2, 80.1, 81.4, 82.6], tooltip: "82.6% audit readiness across all business units" },
  { id: "remediation-tasks", label: "Remediation Tasks Open", value: "89", trend: -18, trendDirection: "down", icon: "ListChecks", color: "from-purple-500 to-purple-600", severity: "info", sparklineData: [145, 132, 118, 105, 94, 89], tooltip: "89 open remediation tasks requiring action" },
];

// ── Regulations ──────────────────────────────────────────────────────────

export const mockRegulations: Regulation[] = [
  { id: "reg-gdpr", name: "General Data Protection Regulation", shortName: "GDPR", description: "EU data protection and privacy regulation", jurisdiction: "European Union", category: "privacy", complianceScore: 82, contractCoverage: 76, totalRequirements: 28, metRequirements: 23, gapCount: 5, status: "at_risk", lastAssessed: "2026-05-10", icon: "Shield" },
  { id: "reg-hipaa", name: "Health Insurance Portability and Accountability Act", shortName: "HIPAA", description: "US healthcare data privacy and security", jurisdiction: "United States", category: "security", complianceScore: 74, contractCoverage: 68, totalRequirements: 22, metRequirements: 16, gapCount: 6, status: "non_compliant", lastAssessed: "2026-05-08", icon: "Heart" },
  { id: "reg-soc2", name: "SOC 2 Type II", shortName: "SOC 2", description: "Service organization security and availability", jurisdiction: "Global", category: "security", complianceScore: 91, contractCoverage: 88, totalRequirements: 18, metRequirements: 16, gapCount: 2, status: "compliant", lastAssessed: "2026-05-12", icon: "CheckCircle" },
  { id: "reg-iso27001", name: "ISO/IEC 27001", shortName: "ISO 27001", description: "Information security management standard", jurisdiction: "Global", category: "security", complianceScore: 88, contractCoverage: 84, totalRequirements: 15, metRequirements: 13, gapCount: 2, status: "compliant", lastAssessed: "2026-05-05", icon: "Award" },
  { id: "reg-ccpa", name: "California Consumer Privacy Act", shortName: "CCPA", description: "California consumer privacy rights", jurisdiction: "California, USA", category: "privacy", complianceScore: 76, contractCoverage: 72, totalRequirements: 20, metRequirements: 15, gapCount: 5, status: "at_risk", lastAssessed: "2026-05-01", icon: "FileText" },
  { id: "reg-pci", name: "Payment Card Industry Data Security Standard", shortName: "PCI-DSS", description: "Payment card data security standard", jurisdiction: "Global", category: "financial", complianceScore: 95, contractCoverage: 92, totalRequirements: 12, metRequirements: 11, gapCount: 1, status: "compliant", lastAssessed: "2026-04-28", icon: "CreditCard" },
  { id: "reg-fedramp", name: "FedRAMP", shortName: "FedRAMP", description: "US federal cloud security authorization", jurisdiction: "United States", category: "security", complianceScore: 70, contractCoverage: 45, totalRequirements: 25, metRequirements: 17, gapCount: 8, status: "non_compliant", lastAssessed: "2026-04-20", icon: "Shield" },
  { id: "reg-dpa", name: "Data Processing Addendum Requirements", shortName: "DPA", description: "GDPR-required data processing agreements", jurisdiction: "European Union", category: "privacy", complianceScore: 65, contractCoverage: 58, totalRequirements: 10, metRequirements: 6, gapCount: 4, status: "non_compliant", lastAssessed: "2026-05-10", icon: "FileText" },
];

// ── Compliance Findings ──────────────────────────────────────────────────

export const mockFindings: ComplianceFinding[] = [
  { id: "find-001", title: "Missing GDPR Data Processing Addendums", description: "12 contracts with EU counterparties lack required GDPR DPA clauses", regulationId: "reg-gdpr", regulationName: "GDPR", severity: "critical", status: "open", impactedContracts: 12, impactedVendors: 8, assignee: "Sarah Chen", dueDate: "2026-06-30", createdAt: "2026-05-01", remediationSteps: ["Identify all EU counterparty contracts", "Generate DPA addendum templates", "Route for legal review", "Execute addendums with counterparties"], aiConfidence: 96, regulatoryReference: "GDPR Article 28", category: "data_privacy" },
  { id: "find-002", title: "HIPAA Business Associate Agreements Missing", description: "6 healthcare vendor contracts missing required HIPAA BAAs", regulationId: "reg-hipaa", regulationName: "HIPAA", severity: "critical", status: "in_progress", impactedContracts: 6, impactedVendors: 4, assignee: "Michael Torres", dueDate: "2026-06-15", createdAt: "2026-04-28", remediationSteps: ["Identify covered vendor contracts", "Draft BAA amendments", "Negotiate with vendors", "Execute and archive"], aiConfidence: 94, regulatoryReference: "HIPAA §164.504(e)", category: "healthcare" },
  { id: "find-003", title: "Data Retention Policy Conflicts", description: "18 contracts have data retention terms conflicting with GDPR Article 17 right to erasure", regulationId: "reg-gdpr", regulationName: "GDPR", severity: "high", status: "open", impactedContracts: 18, impactedVendors: 12, assignee: "Sarah Chen", dueDate: "2026-07-15", createdAt: "2026-05-05", remediationSteps: ["Audit all data retention clauses", "Identify conflicts with GDPR Article 17", "Draft amendment language", "Prioritize by data sensitivity"], aiConfidence: 89, regulatoryReference: "GDPR Article 17", category: "data_privacy" },
  { id: "find-004", title: "Cross-Border Transfer Compliance Risk", description: "22 contracts involve cross-border data transfers without standard contractual clauses", regulationId: "reg-gdpr", regulationName: "GDPR", severity: "critical", status: "open", impactedContracts: 22, impactedVendors: 15, assignee: "Michael Torres", dueDate: "2026-06-30", createdAt: "2026-05-03", remediationSteps: ["Map all cross-border data flows", "Identify missing SCCs", "Generate SCC addendums", "Execute with counterparties"], aiConfidence: 92, regulatoryReference: "GDPR Article 44-49", category: "data_privacy" },
  { id: "find-005", title: "FedRAMP Authorization Gaps", description: "8 cloud vendor contracts require FedRAMP authorization but only 2 have it", regulationId: "reg-fedramp", regulationName: "FedRAMP", severity: "high", status: "in_progress", impactedContracts: 8, impactedVendors: 6, assignee: "David Park", dueDate: "2026-08-01", createdAt: "2026-04-15", remediationSteps: ["Verify current vendor authorizations", "Request FedRAMP status from vendors", "Evaluate alternative vendors if needed", "Document risk acceptance"], aiConfidence: 86, regulatoryReference: "FedRAMP Rev 5", category: "security" },
  { id: "find-006", title: "CCPA Consumer Rights Notice Missing", description: "15 contracts with California residents lack CCPA-required consumer rights notices", regulationId: "reg-ccpa", regulationName: "CCPA", severity: "high", status: "open", impactedContracts: 15, impactedVendors: 10, assignee: "Emily Nakamura", dueDate: "2026-07-01", createdAt: "2026-05-02", remediationSteps: ["Identify California-scope contracts", "Generate CCPA notice addendums", "Route for legal approval", "Distribute to counterparties"], aiConfidence: 88, regulatoryReference: "CCPA §1798.100", category: "privacy" },
  { id: "find-007", title: "SOC 2 Report Delivery Delays", description: "4 vendor contracts where SOC 2 reports are overdue by more than 60 days", regulationId: "reg-soc2", regulationName: "SOC 2", severity: "medium", status: "open", impactedContracts: 4, impactedVendors: 4, assignee: "David Park", dueDate: "2026-06-01", createdAt: "2026-05-10", remediationSteps: ["Contact vendors for updated reports", "Evaluate interim risk", "Escalate if not received within 30 days", "Update vendor risk scores"], aiConfidence: 82, regulatoryReference: "SOC 2 Type II §3.1", category: "security" },
  { id: "find-008", title: "ISO 27001 Certification Expiry", description: "3 vendor ISO 27001 certifications expiring within 60 days without renewal evidence", regulationId: "reg-iso27001", regulationName: "ISO 27001", severity: "medium", status: "in_progress", impactedContracts: 5, impactedVendors: 3, assignee: "Emily Nakamura", dueDate: "2026-06-15", createdAt: "2026-05-08", remediationSteps: ["Request renewal certificates", "Evaluate interim security posture", "Update vendor compliance records", "Flag for procurement review"], aiConfidence: 85, regulatoryReference: "ISO 27001:2022 §9", category: "security" },
];

// ── Remediation Tasks ────────────────────────────────────────────────────

export const mockRemediationTasks: RemediationTask[] = [
  { id: "task-001", findingId: "find-001", title: "Generate DPA addendums for EU contracts", description: "Create standardized DPA addendum templates for 12 affected contracts", assignee: "Sarah Chen", assigneeAvatar: "SC", status: "in_progress", priority: "critical", dueDate: "2026-06-15", slaRemaining: 86400 * 25, isOverdue: false, escalationLevel: 0, evidenceRequired: true, evidenceProvided: false, createdAt: "2026-05-01", updatedAt: "2026-05-12" },
  { id: "task-002", findingId: "find-001", title: "Execute DPA addendums with top 5 vendors", description: "Priority execution of DPA addendums with highest-risk vendors", assignee: "Michael Torres", assigneeAvatar: "MT", status: "open", priority: "critical", dueDate: "2026-06-20", slaRemaining: 86400 * 30, isOverdue: false, escalationLevel: 0, evidenceRequired: true, evidenceProvided: false, createdAt: "2026-05-01", updatedAt: "2026-05-12" },
  { id: "task-003", findingId: "find-002", title: "Draft HIPAA BAA amendments", description: "Legal review and drafting of BAA amendments for healthcare vendors", assignee: "Michael Torres", assigneeAvatar: "MT", status: "in_progress", priority: "critical", dueDate: "2026-06-01", slaRemaining: 86400 * 12, isOverdue: false, escalationLevel: 1, evidenceRequired: true, evidenceProvided: false, createdAt: "2026-04-28", updatedAt: "2026-05-10" },
  { id: "task-004", findingId: "find-003", title: "Audit data retention clauses across 18 contracts", description: "Systematic review of all data retention terms for GDPR conflicts", assignee: "Sarah Chen", assigneeAvatar: "SC", status: "open", priority: "high", dueDate: "2026-06-30", slaRemaining: 86400 * 40, isOverdue: false, escalationLevel: 0, evidenceRequired: false, evidenceProvided: false, createdAt: "2026-05-05", updatedAt: "2026-05-12" },
  { id: "task-005", findingId: "find-004", title: "Map cross-border data flows", description: "Document all data flows between entities for SCC assessment", assignee: "David Park", assigneeAvatar: "DP", status: "open", priority: "critical", dueDate: "2026-06-10", slaRemaining: 86400 * 21, isOverdue: false, escalationLevel: 0, evidenceRequired: true, evidenceProvided: false, createdAt: "2026-05-03", updatedAt: "2026-05-12" },
  { id: "task-006", findingId: "find-005", title: "Request FedRAMP status from 6 vendors", description: "Formal request for FedRAMP authorization status and documentation", assignee: "David Park", assigneeAvatar: "DP", status: "in_progress", priority: "high", dueDate: "2026-06-15", slaRemaining: 86400 * 26, isOverdue: false, escalationLevel: 0, evidenceRequired: true, evidenceProvided: false, createdAt: "2026-04-15", updatedAt: "2026-05-08" },
  { id: "task-007", findingId: "find-006", title: "Generate CCPA notice addendums", description: "Create standardized CCPA consumer rights notice addendums", assignee: "Emily Nakamura", assigneeAvatar: "EN", status: "open", priority: "high", dueDate: "2026-06-20", slaRemaining: 86400 * 31, isOverdue: false, escalationLevel: 0, evidenceRequired: false, evidenceProvided: false, createdAt: "2026-05-02", updatedAt: "2026-05-12" },
  { id: "task-008", findingId: "find-007", title: "Escalate SOC 2 report requests", description: "Escalate overdue SOC 2 report requests to vendor management", assignee: "David Park", assigneeAvatar: "DP", status: "overdue", priority: "medium", dueDate: "2026-05-15", slaRemaining: -86400 * 3, isOverdue: true, escalationLevel: 2, evidenceRequired: true, evidenceProvided: false, createdAt: "2026-05-10", updatedAt: "2026-05-12" },
  { id: "task-009", findingId: "find-008", title: "Request ISO 27001 renewal certificates", description: "Contact 3 vendors for updated ISO 27001 certification evidence", assignee: "Emily Nakamura", assigneeAvatar: "EN", status: "in_progress", priority: "medium", dueDate: "2026-06-01", slaRemaining: 86400 * 12, isOverdue: false, escalationLevel: 0, evidenceRequired: true, evidenceProvided: false, createdAt: "2026-05-08", updatedAt: "2026-05-11" },
  { id: "task-010", findingId: "find-002", title: "Negotiate BAA terms with SecurePath Ltd", description: "Negotiate HIPAA-compliant BAA terms with SecurePath Ltd legal team", assignee: "Sarah Chen", assigneeAvatar: "SC", status: "open", priority: "critical", dueDate: "2026-06-10", slaRemaining: 86400 * 21, isOverdue: false, escalationLevel: 1, evidenceRequired: true, evidenceProvided: false, createdAt: "2026-04-28", updatedAt: "2026-05-10" },
];

// ── Vendor Compliance ────────────────────────────────────────────────────

export const mockVendorCompliance: VendorCompliance[] = [
  { id: "vc-001", vendorName: "Acme Corporation", overallScore: 88, certifications: [
    { id: "cert-001", name: "SOC 2 Type II", standard: "SOC 2", issueDate: "2025-06-01", expirationDate: "2026-12-31", status: "active", score: 92 },
    { id: "cert-002", name: "ISO 27001", standard: "ISO 27001", issueDate: "2025-03-15", expirationDate: "2026-09-15", status: "active", score: 90 },
  ], riskLevel: "low", contractCount: 4, lastAssessed: "2026-05-10", status: "compliant" },
  { id: "vc-002", vendorName: "TechSphere Inc", overallScore: 65, certifications: [
    { id: "cert-003", name: "SOC 2 Type I", standard: "SOC 2", issueDate: "2025-01-01", expirationDate: "2026-06-30", status: "expiring", score: 72 },
  ], riskLevel: "high", contractCount: 3, lastAssessed: "2026-05-08", status: "at_risk" },
  { id: "vc-003", vendorName: "DataVault Systems", overallScore: 92, certifications: [
    { id: "cert-004", name: "SOC 2 Type II", standard: "SOC 2", issueDate: "2025-09-01", expirationDate: "2027-09-01", status: "active", score: 95 },
    { id: "cert-005", name: "ISO 27001", standard: "ISO 27001", issueDate: "2025-06-01", expirationDate: "2027-06-01", status: "active", score: 93 },
    { id: "cert-006", name: "FedRAMP Moderate", standard: "FedRAMP", issueDate: "2025-04-01", expirationDate: "2027-04-01", status: "active", score: 88 },
  ], riskLevel: "low", contractCount: 5, lastAssessed: "2026-05-12", status: "compliant" },
  { id: "vc-004", vendorName: "CloudNexus", overallScore: 55, certifications: [
    { id: "cert-007", name: "ISO 27001", standard: "ISO 27001", issueDate: "2024-01-01", expirationDate: "2026-01-01", status: "expired", score: 45 },
  ], riskLevel: "critical", contractCount: 2, lastAssessed: "2026-05-05", status: "non_compliant" },
  { id: "vc-005", vendorName: "SecurePath Ltd", overallScore: 72, certifications: [
    { id: "cert-008", name: "SOC 2 Type II", standard: "SOC 2", issueDate: "2025-11-01", expirationDate: "2026-11-01", status: "active", score: 78 },
  ], riskLevel: "medium", contractCount: 3, lastAssessed: "2026-05-01", status: "at_risk" },
  { id: "vc-006", vendorName: "GlobalTech Partners", overallScore: 45, certifications: [], riskLevel: "critical", contractCount: 1, lastAssessed: "2026-04-28", status: "non_compliant" },
];

// ── Audits ───────────────────────────────────────────────────────────────

export const mockAudits: ComplianceAudit[] = [
  { id: "aud-001", title: "GDPR Compliance Audit Q2 2026", regulationId: "reg-gdpr", regulationName: "GDPR", status: "in_progress", scope: ["Data Processing", "Cross-border Transfers", "DPA Compliance", "Data Retention"], findings: 18, passed: 12, failed: 6, readinessScore: 74, evidenceCompleteness: 68, startDate: "2026-05-01", endDate: undefined, auditor: "External - Deloitte", businessUnits: ["Enterprise Tech", "Healthcare", "Financial Services"] },
  { id: "aud-002", title: "HIPAA Compliance Review", regulationId: "reg-hipaa", regulationName: "HIPAA", status: "scheduled", scope: ["BAA Compliance", "Security Controls", "Privacy Practices", "Breach Notification"], findings: 0, passed: 0, failed: 0, readinessScore: 72, evidenceCompleteness: 55, startDate: "2026-06-01", endDate: undefined, auditor: "Internal Audit Team", businessUnits: ["Healthcare"] },
  { id: "aud-003", title: "SOC 2 Type II Surveillance", regulationId: "reg-soc2", regulationName: "SOC 2", status: "completed", scope: ["Security", "Availability", "Processing Integrity", "Confidentiality", "Privacy"], findings: 4, passed: 16, failed: 2, readinessScore: 91, evidenceCompleteness: 95, startDate: "2026-03-01", endDate: "2026-04-15", auditor: "External - KPMG", businessUnits: ["Enterprise Tech", "Financial Services"] },
  { id: "aud-004", title: "FedRAMP Annual Assessment", regulationId: "reg-fedramp", regulationName: "FedRAMP", status: "pending", scope: ["Access Control", "Audit Logging", "Configuration Management", "Incident Response"], findings: 0, passed: 0, failed: 0, readinessScore: 65, evidenceCompleteness: 42, startDate: "2026-07-01", endDate: undefined, auditor: "External - Coalfire", businessUnits: ["Enterprise Tech"] },
  { id: "aud-005", title: "CCPA Compliance Verification", regulationId: "reg-ccpa", regulationName: "CCPA", status: "completed", scope: ["Consumer Rights Notices", "Data Collection Practices", "Opt-out Mechanisms", "Third-party Disclosures"], findings: 8, passed: 6, failed: 2, readinessScore: 78, evidenceCompleteness: 82, startDate: "2026-04-01", endDate: "2026-04-30", auditor: "Internal Legal Team", businessUnits: ["Enterprise Tech", "Financial Services"] },
];

// ── AI Compliance Insights ───────────────────────────────────────────────

export const mockAiComplianceInsights: AiComplianceInsight[] = [
  { id: "ai-001", type: "gap", title: "GDPR DPA Gap - 12 Contracts at Risk", description: "AI analysis identified 12 contracts with EU counterparties that lack required GDPR Data Processing Addendums. This is the highest priority compliance gap.", severity: "critical", confidence: 96, impactedContracts: 12, impactedRegulation: "GDPR", remediationSuggestion: "Generate and execute DPA addendums for all affected contracts. Prioritize contracts with active data processing.", regulatoryReference: "GDPR Article 28" },
  { id: "ai-002", type: "risk", title: "Cross-Border Transfer Exposure", description: "22 contracts involve cross-border data transfers without Standard Contractual Clauses. Potential regulatory action risk: HIGH.", severity: "critical", confidence: 92, impactedContracts: 22, impactedRegulation: "GDPR", remediationSuggestion: "Implement SCCs for all cross-border transfers. Map data flows and prioritize by data sensitivity.", regulatoryReference: "GDPR Articles 44-49" },
  { id: "ai-003", type: "remediation", title: "HIPAA BAA Remediation Progressing", description: "6 of 6 healthcare vendor contracts identified for BAA remediation. 2 BAAs executed, 2 in negotiation, 2 pending.", severity: "info", confidence: 88, impactedContracts: 6, impactedRegulation: "HIPAA", remediationSuggestion: "Continue BAA negotiations. Escalate SecurePath Ltd if not resolved within 30 days.", regulatoryReference: "HIPAA §164.504(e)" },
  { id: "ai-004", type: "change", title: "GDPR Enforcement Update - Impact Analysis", description: "Recent EDPB guidance on cross-border transfers may affect 8 additional contracts. Recommended review within 60 days.", severity: "warning", confidence: 84, impactedContracts: 8, impactedRegulation: "GDPR", remediationSuggestion: "Review new EDPB guidance. Assess impact on existing transfer mechanisms. Plan SCC updates.", regulatoryReference: "EDPB Guidelines 2026" },
  { id: "ai-005", type: "conflict", title: "Data Retention Policy Conflict Detected", description: "18 contracts have data retention periods exceeding GDPR right to erasure requirements. Policy conflicts identified across 3 business units.", severity: "high", confidence: 89, impactedContracts: 18, impactedRegulation: "GDPR", remediationSuggestion: "Amend data retention clauses to include erasure mechanisms. Prioritize contracts with sensitive personal data.", regulatoryReference: "GDPR Article 17" },
  { id: "ai-006", type: "recommendation", title: "FedRAMP Vendor Consolidation Opportunity", description: "8 cloud vendor contracts need FedRAMP authorization. 2 vendors already have it. Consider consolidating to authorized vendors.", severity: "info", confidence: 78, impactedContracts: 8, impactedRegulation: "FedRAMP", remediationSuggestion: "Evaluate total cost of FedRAMP compliance vs vendor consolidation. Recommend procurement review.", regulatoryReference: "FedRAMP Rev 5" },
];

// ── Policies ─────────────────────────────────────────────────────────────

export const mockPolicies: CompliancePolicy[] = [
  { id: "pol-001", title: "Data Protection Policy", description: "Enterprise data protection and privacy requirements aligned with GDPR", regulationId: "reg-gdpr", version: "3.2", status: "active", lastReviewed: "2026-03-15", nextReview: "2027-03-15", acknowledgements: 2842, totalRequired: 3200 },
  { id: "pol-002", title: "Information Security Policy", description: "Security controls and incident response procedures", regulationId: "reg-iso27001", version: "4.1", status: "active", lastReviewed: "2026-02-01", nextReview: "2027-02-01", acknowledgements: 2650, totalRequired: 3200 },
  { id: "pol-003", title: "Vendor Risk Management Policy", description: "Third-party risk assessment and compliance requirements", regulationId: "reg-soc2", version: "2.0", status: "review", lastReviewed: "2025-11-01", nextReview: "2026-06-01", acknowledgements: 1850, totalRequired: 3200 },
  { id: "pol-004", title: "Data Retention and Disposal Policy", description: "Data lifecycle management and erasure procedures", regulationId: "reg-gdpr", version: "1.5", status: "active", lastReviewed: "2026-04-01", nextReview: "2027-04-01", acknowledgements: 2100, totalRequired: 3200 },
  { id: "pol-005", title: "HIPAA Privacy and Security Policy", description: "Healthcare data handling and BAA requirements", regulationId: "reg-hipaa", version: "2.3", status: "draft", lastReviewed: "2026-05-01", nextReview: "2026-11-01", acknowledgements: 450, totalRequired: 800 },
];

// ── Compliance Analytics ─────────────────────────────────────────────────

export const mockComplianceAnalytics: ComplianceAnalytics = {
  overallScore: 78.4,
  auditReadiness: 82.6,
  remediationProgress: 58,
  scoreHistory: [
    { date: "Jan", score: 72 }, { date: "Feb", score: 73.5 }, { date: "Mar", score: 74.8 },
    { date: "Apr", score: 76.2 }, { date: "May", score: 77.1 }, { date: "Jun", score: 78.4 },
  ],
  regulationCoverage: [
    { regulation: "GDPR", coverage: 76 }, { regulation: "HIPAA", coverage: 68 },
    { regulation: "SOC 2", coverage: 88 }, { regulation: "ISO 27001", coverage: 84 },
    { regulation: "CCPA", coverage: 72 }, { regulation: "PCI-DSS", coverage: 92 },
    { regulation: "FedRAMP", coverage: 45 }, { regulation: "DPA", coverage: 58 },
  ],
  regionalExposure: [
    { region: "European Union", riskScore: 72, contractCount: 145 },
    { region: "United States", riskScore: 58, contractCount: 320 },
    { region: "California", riskScore: 65, contractCount: 89 },
    { region: "Asia Pacific", riskScore: 45, contractCount: 67 },
    { region: "United Kingdom", riskScore: 52, contractCount: 48 },
    { region: "Latin America", riskScore: 38, contractCount: 32 },
  ],
  remediationTrend: [
    { date: "May 1", open: 145, resolved: 12 },
    { date: "May 4", open: 132, resolved: 18 },
    { date: "May 7", open: 118, resolved: 24 },
    { date: "May 10", open: 105, resolved: 31 },
    { date: "May 13", open: 94, resolved: 38 },
  ],
  vendorComplianceDistribution: [
    { status: "compliant", count: 18 },
    { status: "at_risk", count: 12 },
    { status: "non_compliant", count: 8 },
    { status: "pending", count: 6 },
  ],
  findingCategories: [
    { category: "Data Privacy", count: 42 },
    { category: "Security Controls", count: 28 },
    { category: "Vendor Compliance", count: 35 },
    { category: "Data Retention", count: 18 },
    { category: "Cross-border Transfer", count: 22 },
    { category: "Policy Compliance", count: 15 },
  ],
  topViolations: [
    { clause: "Data Processing Addendum", regulation: "GDPR", count: 12 },
    { clause: "Business Associate Agreement", regulation: "HIPAA", count: 6 },
    { clause: "Standard Contractual Clauses", regulation: "GDPR", count: 22 },
    { clause: "Consumer Rights Notice", regulation: "CCPA", count: 15 },
    { clause: "Data Retention Period", regulation: "GDPR", count: 18 },
  ],
};

// ── Compliance Detail ────────────────────────────────────────────────────

export const mockComplianceDetail: ComplianceDetail = {
  overview: {
    regulation: "GDPR",
    score: 82,
    status: "at_risk",
    lastAssessed: "2026-05-10",
    jurisdiction: "European Union",
    contractsInScope: 145,
    vendorsInScope: 38,
  },
  regulatoryMapping: [
    { requirement: "Article 5 - Data Processing Principles", status: "compliant", evidence: "Data processing register maintained" },
    { requirement: "Article 6 - Lawful Processing", status: "compliant", evidence: "Consent mechanisms documented" },
    { requirement: "Article 17 - Right to Erasure", status: "non_compliant", evidence: "18 contracts lack erasure mechanisms" },
    { requirement: "Article 28 - Data Processor", status: "non_compliant", evidence: "12 contracts missing DPA addendums" },
    { requirement: "Article 44-49 - Cross-border Transfers", status: "non_compliant", evidence: "22 transfers lack SCCs" },
    { requirement: "Article 30 - Records of Processing", status: "compliant", evidence: "Processing register current" },
    { requirement: "Article 32 - Security of Processing", status: "compliant", evidence: "SOC 2 controls in place" },
    { requirement: "Article 33 - Breach Notification", status: "at_risk", evidence: "Notification SLA needs review" },
  ],
  impactedContracts: [
    { id: "c001", title: "MSA - Acme Corp", risk: "critical", clause: "Data Processing" },
    { id: "c002", title: "SaaS Agreement - TechSphere", risk: "critical", clause: "Cross-border Transfer" },
    { id: "c003", title: "DPA - DataVault Systems", risk: "medium", clause: "Data Retention" },
    { id: "c004", title: "License - CloudNexus", risk: "high", clause: "Data Processing" },
    { id: "c005", title: "MSA - SecurePath Ltd", risk: "high", clause: "Cross-border Transfer" },
  ],
  remediationActions: mockRemediationTasks.slice(0, 5),
  auditTrail: [
    { action: "Compliance gap analysis completed", user: "AI System", timestamp: "2026-05-12T10:00:00Z" },
    { action: "GDPR audit scope defined", user: "Sarah Chen", timestamp: "2026-05-10T14:00:00Z" },
    { action: "DPA gap identified - 12 contracts", user: "AI System", timestamp: "2026-05-08T09:00:00Z" },
    { action: "Remediation plan created", user: "Michael Torres", timestamp: "2026-05-05T11:00:00Z" },
    { action: "Cross-border transfer risk assessment", user: "AI System", timestamp: "2026-05-03T16:00:00Z" },
  ],
  aiRecommendations: mockAiComplianceInsights.slice(0, 3),
  relatedPolicies: [mockPolicies[0], mockPolicies[3]],
  evidence: [
    { id: "ev-001", name: "Data Processing Register Q2", type: "Spreadsheet", status: "approved" },
    { id: "ev-002", name: "DPA Template v3.1", type: "Document", status: "draft" },
    { id: "ev-003", name: "SCC Implementation Guide", type: "Document", status: "approved" },
    { id: "ev-004", name: "Vendor DPA Status Report", type: "Report", status: "pending" },
  ],
};

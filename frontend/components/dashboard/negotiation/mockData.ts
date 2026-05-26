// ── Enterprise Negotiation & Redline Center Mock Data ─────────────────────

import type {
  NegotiationSession, NegotiationKpi, DocumentVersion, ClauseContent,
  RedlineEntry, NegotiationIssue, Participant, CommentItem,
  AiNegotiationInsight, NegotiationPlaybook, FallbackClause,
  NegotiationWorkflow, NegotiationAnalytics, ActivityEntry,
} from "./types";

// ── KPI Data ─────────────────────────────────────────────────────────────

export const mockNegotiationKpis: NegotiationKpi[] = [
  { id: "active-negotiations", label: "Active Negotiations", value: "24", trend: 12, trendDirection: "up", icon: "MessageSquare", color: "from-blue-500 to-blue-600", severity: "info", sparklineData: [18, 20, 19, 22, 21, 24], tooltip: "24 active negotiation sessions across all contracts" },
  { id: "open-redlines", label: "Open Redlines", value: "187", trend: -8, trendDirection: "down", icon: "PenTool", color: "from-amber-500 to-amber-600", severity: "warning", sparklineData: [210, 195, 188, 192, 185, 187], tooltip: "187 pending redline changes requiring review" },
  { id: "high-risk-clauses", label: "High-Risk Clauses", value: "34", trend: 5, trendDirection: "up", icon: "AlertTriangle", color: "from-red-500 to-red-600", severity: "critical", sparklineData: [28, 30, 29, 32, 31, 34], tooltip: "34 clauses flagged as high-risk in active negotiations" },
  { id: "avg-cycle-time", label: "Avg Cycle Time", value: "6.2d", trend: -15, trendDirection: "down", icon: "Clock", color: "from-green-500 to-green-600", severity: "success", sparklineData: [8.5, 7.8, 7.2, 6.9, 6.5, 6.2], tooltip: "Average negotiation cycle time reduced to 6.2 days" },
  { id: "ai-acceptance", label: "AI Redline Acceptance", value: "84%", trend: 7, trendDirection: "up", icon: "Brain", color: "from-purple-500 to-purple-600", severity: "success", sparklineData: [72, 75, 78, 80, 82, 84], tooltip: "84% of AI-suggested redlines accepted by reviewers" },
  { id: "escalated-issues", label: "Escalated Issues", value: "8", trend: -25, trendDirection: "down", icon: "ArrowUpCircle", color: "from-orange-500 to-orange-600", severity: "warning", sparklineData: [14, 12, 11, 10, 9, 8], tooltip: "8 issues escalated to senior legal review" },
  { id: "fallback-usage", label: "Fallback Clause Usage", value: "142", trend: 18, trendDirection: "up", icon: "GitBranch", color: "from-teal-500 to-teal-600", severity: "info", sparklineData: [98, 105, 115, 122, 135, 142], tooltip: "142 fallback clauses deployed across negotiations" },
  { id: "success-rate", label: "Negotiation Success", value: "91%", trend: 3, trendDirection: "up", icon: "Target", color: "from-emerald-500 to-emerald-600", severity: "success", sparklineData: [85, 86, 88, 89, 90, 91], tooltip: "91% of negotiations reach successful resolution" },
];

// ── Helper: Clause Content ───────────────────────────────────────────────

const originalClauses: ClauseContent[] = [
  { clauseId: "c1", title: "Limitation of Liability", sectionNumber: "12.1", content: "Neither party shall be liable to the other for any indirect, incidental, special, consequential, or punitive damages arising out of or relating to this Agreement, whether based on contract, tort, or any other legal theory, regardless of whether such party has been advised of the possibility of such damages. The total aggregate liability of either party under this Agreement shall not exceed the total fees paid or payable by Customer to Vendor during the twelve (12) months immediately preceding the event giving rise to such liability.", riskLevel: "medium", category: "liability" },
  { clauseId: "c2", title: "Indemnification", sectionNumber: "13.1", content: "Vendor shall indemnify, defend, and hold harmless Customer and its affiliates, officers, directors, employees, and agents from and against any and all claims, damages, losses, liabilities, costs, and expenses arising out of or related to: (i) any breach of this Agreement by Vendor; (ii) any infringement of third-party intellectual property rights by Vendor's products or services; (iii) any gross negligence or willful misconduct of Vendor.", riskLevel: "high", category: "indemnification" },
  { clauseId: "c3", title: "Termination for Convenience", sectionNumber: "14.2", content: "Either party may terminate this Agreement for any reason or no reason upon ninety (90) days prior written notice to the other party. In the event of such termination, Customer shall pay Vendor for all Services rendered and expenses incurred up to the effective date of termination.", riskLevel: "low", category: "termination" },
  { clauseId: "c4", title: "Data Protection & Security", sectionNumber: "10.1", content: "Vendor shall implement and maintain appropriate technical and organizational measures to protect Customer Data against unauthorized or unlawful processing, accidental loss, destruction, damage, alteration, or disclosure. Such measures shall comply with applicable data protection laws and regulations, including but not limited to GDPR, CCPA, and SOC 2 Type II standards.", riskLevel: "high", category: "data_privacy" },
  { clauseId: "c5", title: "Service Level Agreement", sectionNumber: "8.1", content: "Vendor shall maintain a service uptime of 99.9% availability, measured monthly. If Vendor fails to meet this SLA, Customer shall be entitled to service credits as follows: 5% of monthly fees for uptime below 99.9% but above 99.0%, 10% for uptime below 99.0% but above 95.0%, and 25% for uptime below 95.0%.", riskLevel: "medium", category: "sla" },
  { clauseId: "c6", title: "Intellectual Property Rights", sectionNumber: "11.1", content: "All intellectual property rights in and to the Services, including all software, algorithms, data models, and documentation, shall remain the sole and exclusive property of Vendor. Customer retains all rights to its data and any deliverables specifically developed for Customer under this Agreement.", riskLevel: "medium", category: "ip" },
  { clauseId: "c7", title: "Confidentiality", sectionNumber: "9.1", content: "Each party agrees to maintain the confidentiality of the other party's Confidential Information for a period of three (3) years from the date of disclosure. Confidential Information shall not be disclosed to any third party without the prior written consent of the disclosing party, except as required by law.", riskLevel: "low", category: "confidentiality" },
  { clauseId: "c8", title: "Payment Terms", sectionNumber: "5.1", content: "Customer shall pay Vendor within thirty (30) days of receipt of invoice. Late payments shall accrue interest at the rate of 1.5% per month or the maximum rate permitted by law, whichever is less. All fees are non-refundable except as expressly provided in this Agreement.", riskLevel: "medium", category: "commercial" },
  { clauseId: "c9", title: "Warranty Disclaimer", sectionNumber: "15.1", content: "EXCEPT AS EXPRESSLY SET FORTH IN THIS AGREEMENT, VENDOR MAKES NO WARRANTIES, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE IMPLIED WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, AND NON-INFRINGEMENT. VENDOR DOES NOT WARRANT THAT THE SERVICES WILL BE UNINTERRUPTED OR ERROR-FREE.", riskLevel: "high", category: "warranty" },
  { clauseId: "c10", title: "Governing Law & Jurisdiction", sectionNumber: "17.1", content: "This Agreement shall be governed by and construed in accordance with the laws of the State of Delaware, without regard to its conflict of laws principles. Any legal action or proceeding arising under this Agreement shall be brought exclusively in the federal or state courts located in New Castle County, Delaware.", riskLevel: "medium", category: "legal" },
];

const modifiedClauses: ClauseContent[] = [
  { clauseId: "c1", title: "Limitation of Liability", sectionNumber: "12.1", content: "Neither party shall be liable to the other for any indirect, incidental, special, consequential, or punitive damages arising out of or relating to this Agreement, whether based on contract, tort, or any other legal theory, regardless of whether such party has been advised of the possibility of such damages. The total aggregate liability of either party under this Agreement shall not exceed the total fees paid or payable by Customer to Vendor during the twenty-four (24) months immediately preceding the event giving rise to such liability. Notwithstanding the foregoing, nothing in this Section 12.1 shall limit either party's liability for: (a) breach of confidentiality obligations; (b) infringement of intellectual property rights; (c) death or personal injury caused by negligence; or (d) fraud or willful misconduct.", riskLevel: "medium", category: "liability" },
  { clauseId: "c2", title: "Indemnification", sectionNumber: "13.1", content: "Vendor shall indemnify, defend, and hold harmless Customer and its affiliates, officers, directors, employees, and agents from and against any and all claims, damages, losses, liabilities, costs, and expenses arising out of or related to: (i) any breach of this Agreement by Vendor; (ii) any infringement of third-party intellectual property rights by Vendor's products or services; (iii) any gross negligence or willful misconduct of Vendor. Vendor's indemnification obligations shall survive termination of this Agreement for a period of three (3) years.", riskLevel: "medium", category: "indemnification" },
  { clauseId: "c3", title: "Termination for Convenience", sectionNumber: "14.2", content: "Either party may terminate this Agreement for any reason or no reason upon sixty (60) days prior written notice to the other party. In the event of such termination, Customer shall pay Vendor for all Services rendered up to the effective date of termination. Customer shall not be liable for any early termination fees, cancellation penalties, or future commitments.", riskLevel: "low", category: "termination" },
  { clauseId: "c4", title: "Data Protection & Security", sectionNumber: "10.1", content: "Vendor shall implement and maintain appropriate technical and organizational measures to protect Customer Data against unauthorized or unlawful processing, accidental loss, destruction, damage, alteration, or disclosure. Such measures shall comply with applicable data protection laws and regulations, including but not limited to GDPR, CCPA, SOC 2 Type II standards, and ISO 27001 certification. Vendor shall provide Customer with quarterly security reports and immediate notification of any data breach within 24 hours of discovery.", riskLevel: "medium", category: "data_privacy" },
  { clauseId: "c5", title: "Service Level Agreement", sectionNumber: "8.1", content: "Vendor shall maintain a service uptime of 99.95% availability, measured monthly. If Vendor fails to meet this SLA, Customer shall be entitled to service credits as follows: 10% of monthly fees for uptime below 99.95% but above 99.0%, 20% for uptime below 99.0% but above 95.0%, and 50% for uptime below 95.0%. Customer may also terminate this Agreement for cause if SLA performance falls below 95.0% for two consecutive months.", riskLevel: "medium", category: "sla" },
  { clauseId: "c6", title: "Intellectual Property Rights", sectionNumber: "11.1", content: "All intellectual property rights in and to the Services, including all software, algorithms, data models, and documentation, shall remain the sole and exclusive property of Vendor. Customer retains all rights to its data and any deliverables specifically developed for Customer under this Agreement. Vendor grants Customer a perpetual, irrevocable, royalty-free license to any improvements, modifications, or customizations developed specifically for Customer.", riskLevel: "low", category: "ip" },
  { clauseId: "c7", title: "Confidentiality", sectionNumber: "9.1", content: "Each party agrees to maintain the confidentiality of the other party's Confidential Information for a period of five (5) years from the date of disclosure. Confidential Information shall not be disclosed to any third party without the prior written consent of the disclosing party, except as required by law. Each party shall limit access to Confidential Information to those personnel who have a need to know and who are bound by confidentiality obligations at least as restrictive as those contained herein.", riskLevel: "low", category: "confidentiality" },
  { clauseId: "c8", title: "Payment Terms", sectionNumber: "5.1", content: "Customer shall pay Vendor within forty-five (45) days of receipt of invoice. Late payments shall accrue interest at the rate of 1.0% per month or the maximum rate permitted by law, whichever is less. All fees are non-refundable except as expressly provided in this Agreement. Customer may withhold payment of disputed amounts in good faith pending resolution of the dispute.", riskLevel: "low", category: "commercial" },
  { clauseId: "c9", title: "Warranty Disclaimer", sectionNumber: "15.1", content: "EXCEPT AS EXPRESSLY SET FORTH IN THIS AGREEMENT, VENDOR MAKES NO WARRANTIES, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE IMPLIED WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, AND NON-INFRINGEMENT. VENDOR DOES NOT WARRANT THAT THE SERVICES WILL BE UNINTERRUPTED OR ERROR-FREE. Notwithstanding the foregoing, Vendor warrants that the Services will conform in all material respects to the applicable specifications for a period of ninety (90) days following delivery.", riskLevel: "medium", category: "warranty" },
  { clauseId: "c10", title: "Governing Law & Jurisdiction", sectionNumber: "17.1", content: "This Agreement shall be governed by and construed in accordance with the laws of the State of New York, without regard to its conflict of laws principles. Any legal action or proceeding arising under this Agreement shall be brought exclusively in the federal or state courts located in New York County, New York. The parties irrevocably submit to the personal jurisdiction of such courts.", riskLevel: "medium", category: "legal" },
];

// ── Versions ─────────────────────────────────────────────────────────────

export const mockVersions: DocumentVersion[] = [
  { id: "v1", label: "Original Draft", timestamp: "2026-04-28T09:00:00Z", author: "Sarah Chen", authorAvatar: "SC", status: "superseded", content: originalClauses, wordCount: 4850, changeSummary: "Initial vendor draft" },
  { id: "v2", label: "Legal Review v1", timestamp: "2026-05-02T14:30:00Z", author: "Michael Torres", authorAvatar: "MT", status: "superseded", content: modifiedClauses.map((c, i) => i === 0 || i === 1 || i === 3 ? c : originalClauses[i]), wordCount: 5120, changeSummary: "Updated liability, indemnification, data protection clauses" },
  { id: "v3", label: "Counter Proposal", timestamp: "2026-05-07T11:00:00Z", author: "James Wilson (Vendor)", authorAvatar: "JW", status: "superseded", content: modifiedClauses.map((c, i) => i === 2 || i === 4 || i === 7 ? c : i === 0 || i === 1 || i === 3 ? originalClauses[i] : modifiedClauses[i]), wordCount: 4980, changeSummary: "Vendor counter on termination, SLA, payment terms" },
  { id: "v4", label: "Current - Redline", timestamp: "2026-05-12T16:45:00Z", author: "Sarah Chen", authorAvatar: "SC", status: "current", content: modifiedClauses, wordCount: 5340, changeSummary: "Comprehensive redline with AI-suggested fallbacks" },
];

// ── Redline Entries ──────────────────────────────────────────────────────

export const mockRedlines: RedlineEntry[] = [
  { id: "r1", type: "modification", clauseId: "c1", sectionNumber: "12.1", title: "Limitation of Liability - Cap Increase", originalText: "twelve (12) months", modifiedText: "twenty-four (24) months", author: "Sarah Chen", authorAvatar: "SC", timestamp: "2026-05-12T10:30:00Z", riskLevel: "medium", category: "liability", status: "pending", aiGenerated: true, aiConfidence: 92, negotiationImpact: "high", benchmarkDeviation: 15, comments: [] },
  { id: "r2", type: "addition", clauseId: "c1", sectionNumber: "12.1", title: "Liability Carve-outs", originalText: "", modifiedText: "Notwithstanding the foregoing, nothing in this Section 12.1 shall limit either party's liability for: (a) breach of confidentiality obligations; (b) infringement of intellectual property rights; (c) death or personal injury caused by negligence; or (d) fraud or willful misconduct.", author: "Sarah Chen", authorAvatar: "SC", timestamp: "2026-05-12T10:32:00Z", riskLevel: "low", category: "liability", status: "pending", aiGenerated: true, aiConfidence: 88, negotiationImpact: "medium", benchmarkDeviation: 8, comments: [] },
  { id: "r3", type: "modification", clauseId: "c2", sectionNumber: "13.1", title: "Indemnification Survival Period", originalText: "", modifiedText: "Vendor's indemnification obligations shall survive termination of this Agreement for a period of three (3) years.", author: "Michael Torres", authorAvatar: "MT", timestamp: "2026-05-12T11:00:00Z", riskLevel: "high", category: "indemnification", status: "pending", aiGenerated: false, aiConfidence: undefined, negotiationImpact: "high", benchmarkDeviation: 12, comments: [] },
  { id: "r4", type: "modification", clauseId: "c3", sectionNumber: "14.2", title: "Termination Notice Reduction", originalText: "ninety (90) days", modifiedText: "sixty (60) days", author: "Sarah Chen", authorAvatar: "SC", timestamp: "2026-05-12T11:15:00Z", riskLevel: "low", category: "termination", status: "accepted", aiGenerated: true, aiConfidence: 95, negotiationImpact: "medium", benchmarkDeviation: -5, comments: [] },
  { id: "r5", type: "addition", clauseId: "c3", sectionNumber: "14.2", title: "No Early Termination Fees", originalText: "", modifiedText: "Customer shall not be liable for any early termination fees, cancellation penalties, or future commitments.", author: "Sarah Chen", authorAvatar: "SC", timestamp: "2026-05-12T11:20:00Z", riskLevel: "low", category: "termination", status: "pending", aiGenerated: true, aiConfidence: 91, negotiationImpact: "high", benchmarkDeviation: 20, comments: [] },
  { id: "r6", type: "modification", clauseId: "c4", sectionNumber: "10.1", title: "Security Standards Upgrade", originalText: "including but not limited to GDPR, CCPA, and SOC 2 Type II standards", modifiedText: "including but not limited to GDPR, CCPA, SOC 2 Type II standards, and ISO 27001 certification", author: "Michael Torres", authorAvatar: "MT", timestamp: "2026-05-12T11:45:00Z", riskLevel: "medium", category: "data_privacy", status: "pending", aiGenerated: false, aiConfidence: undefined, negotiationImpact: "medium", benchmarkDeviation: 5, comments: [] },
  { id: "r7", type: "addition", clauseId: "c4", sectionNumber: "10.1", title: "Breach Notification SLA", originalText: "", modifiedText: "Vendor shall provide Customer with quarterly security reports and immediate notification of any data breach within 24 hours of discovery.", author: "Sarah Chen", authorAvatar: "SC", timestamp: "2026-05-12T12:00:00Z", riskLevel: "high", category: "data_privacy", status: "pending", aiGenerated: true, aiConfidence: 96, negotiationImpact: "high", benchmarkDeviation: 25, comments: [] },
  { id: "r8", type: "modification", clauseId: "c5", sectionNumber: "8.1", title: "SLA Uptime Increase", originalText: "99.9% availability", modifiedText: "99.95% availability", author: "Sarah Chen", authorAvatar: "SC", timestamp: "2026-05-12T12:30:00Z", riskLevel: "medium", category: "sla", status: "pending", aiGenerated: true, aiConfidence: 87, negotiationImpact: "medium", benchmarkDeviation: 10, comments: [] },
  { id: "r9", type: "modification", clauseId: "c5", sectionNumber: "8.1", title: "SLA Credit Escalation", originalText: "5% of monthly fees for uptime below 99.9% but above 99.0%, 10% for uptime below 99.0% but above 95.0%, and 25% for uptime below 95.0%", modifiedText: "10% of monthly fees for uptime below 99.95% but above 99.0%, 20% for uptime below 99.0% but above 95.0%, and 50% for uptime below 95.0%", author: "Sarah Chen", authorAvatar: "SC", timestamp: "2026-05-12T12:35:00Z", riskLevel: "high", category: "sla", status: "pending", aiGenerated: true, aiConfidence: 84, negotiationImpact: "high", benchmarkDeviation: 18, comments: [] },
  { id: "r10", type: "addition", clauseId: "c5", sectionNumber: "8.1", title: "SLA Termination Right", originalText: "", modifiedText: "Customer may also terminate this Agreement for cause if SLA performance falls below 95.0% for two consecutive months.", author: "Michael Torres", authorAvatar: "MT", timestamp: "2026-05-12T13:00:00Z", riskLevel: "high", category: "sla", status: "pending", aiGenerated: false, aiConfidence: undefined, negotiationImpact: "high", benchmarkDeviation: 22, comments: [] },
  { id: "r11", type: "addition", clauseId: "c6", sectionNumber: "11.1", title: "Custom Development License", originalText: "", modifiedText: "Vendor grants Customer a perpetual, irrevocable, royalty-free license to any improvements, modifications, or customizations developed specifically for Customer.", author: "Sarah Chen", authorAvatar: "SC", timestamp: "2026-05-12T13:30:00Z", riskLevel: "medium", category: "ip", status: "pending", aiGenerated: true, aiConfidence: 79, negotiationImpact: "high", benchmarkDeviation: 30, comments: [] },
  { id: "r12", type: "modification", clauseId: "c7", sectionNumber: "9.1", title: "Confidentiality Period Extension", originalText: "three (3) years", modifiedText: "five (5) years", author: "Sarah Chen", authorAvatar: "SC", timestamp: "2026-05-12T14:00:00Z", riskLevel: "low", category: "confidentiality", status: "accepted", aiGenerated: true, aiConfidence: 93, negotiationImpact: "low", benchmarkDeviation: 3, comments: [] },
  { id: "r13", type: "modification", clauseId: "c8", sectionNumber: "5.1", title: "Payment Terms Extension", originalText: "thirty (30) days", modifiedText: "forty-five (45) days", author: "Sarah Chen", authorAvatar: "SC", timestamp: "2026-05-12T14:15:00Z", riskLevel: "low", category: "commercial", status: "pending", aiGenerated: true, aiConfidence: 86, negotiationImpact: "medium", benchmarkDeviation: -8, comments: [] },
  { id: "r14", type: "addition", clauseId: "c8", sectionNumber: "5.1", title: "Disputed Amounts Withholding", originalText: "", modifiedText: "Customer may withhold payment of disputed amounts in good faith pending resolution of the dispute.", author: "Michael Torres", authorAvatar: "MT", timestamp: "2026-05-12T14:30:00Z", riskLevel: "medium", category: "commercial", status: "pending", aiGenerated: false, aiConfidence: undefined, negotiationImpact: "medium", benchmarkDeviation: 15, comments: [] },
  { id: "r15", type: "addition", clauseId: "c9", sectionNumber: "15.1", title: "Limited Warranty", originalText: "", modifiedText: "Notwithstanding the foregoing, Vendor warrants that the Services will conform in all material respects to the applicable specifications for a period of ninety (90) days following delivery.", author: "Sarah Chen", authorAvatar: "SC", timestamp: "2026-05-12T15:00:00Z", riskLevel: "medium", category: "warranty", status: "pending", aiGenerated: true, aiConfidence: 82, negotiationImpact: "high", benchmarkDeviation: 20, comments: [] },
  { id: "r16", type: "modification", clauseId: "c10", sectionNumber: "17.1", title: "Jurisdiction Change", originalText: "State of Delaware...New Castle County, Delaware", modifiedText: "State of New York...New York County, New York", author: "Sarah Chen", authorAvatar: "SC", timestamp: "2026-05-12T15:30:00Z", riskLevel: "medium", category: "legal", status: "pending", aiGenerated: true, aiConfidence: 77, negotiationImpact: "high", benchmarkDeviation: 35, comments: [] },
];

// ── Issues ───────────────────────────────────────────────────────────────

export const mockIssues: NegotiationIssue[] = [
  { id: "i1", title: "Liability cap insufficient for data breach risks", description: "Current proposed cap of 24 months fees does not adequately cover potential data breach exposure. Industry standard for enterprise SaaS is 12-24 months with security carve-outs.", clauseId: "c1", sectionNumber: "12.1", severity: "blocker", status: "open", assignee: "Sarah Chen", assigneeAvatar: "SC", dueDate: "2026-05-20", createdBy: "Michael Torres", createdAt: "2026-05-12T10:30:00Z", updatedAt: "2026-05-12T16:00:00Z", category: "legal", escalationLevel: 2, comments: [], tags: ["liability", "data-security", "blocker"] },
  { id: "i2", title: "Indemnification survival period dispute", description: "Vendor pushing back on 3-year survival period for indemnification. Standard market practice is 2-3 years for SaaS agreements.", clauseId: "c2", sectionNumber: "13.1", severity: "critical", status: "in-review", assignee: "Michael Torres", assigneeAvatar: "MT", dueDate: "2026-05-18", createdBy: "Sarah Chen", createdAt: "2026-05-12T11:00:00Z", updatedAt: "2026-05-13T09:00:00Z", category: "legal", escalationLevel: 1, comments: [], tags: ["indemnification", "survival"] },
  { id: "i3", title: "SLA credit structure too aggressive", description: "Vendor concerned that 50% credit for <95% uptime is disproportionate. May need to negotiate tiered approach with termination right as leverage.", clauseId: "c5", sectionNumber: "8.1", severity: "major", status: "open", assignee: "James Wilson", assigneeAvatar: "JW", dueDate: "2026-05-22", createdBy: "Sarah Chen", createdAt: "2026-05-12T12:35:00Z", updatedAt: "2026-05-13T10:00:00Z", category: "commercial", escalationLevel: 0, comments: [], tags: ["sla", "credits", "negotiation"] },
  { id: "i4", title: "Custom IP license scope needs definition", description: "Perpetual license to custom developments is broad. Need to define scope of 'customizations' and ensure it doesn't include Vendor's core IP.", clauseId: "c6", sectionNumber: "11.1", severity: "major", status: "open", assignee: "Sarah Chen", assigneeAvatar: "SC", dueDate: "2026-05-21", createdBy: "Michael Torres", createdAt: "2026-05-12T13:30:00Z", updatedAt: "2026-05-13T11:00:00Z", category: "legal", escalationLevel: 1, comments: [], tags: ["ip", "license", "scope"] },
  { id: "i5", title: "Jurisdiction change to NY requires legal review", description: "Changing governing law from Delaware to New York has significant implications. Need approval from corporate legal before proceeding.", clauseId: "c10", sectionNumber: "17.1", severity: "critical", status: "escalated", assignee: "General Counsel", assigneeAvatar: "GC", dueDate: "2026-05-25", createdBy: "Sarah Chen", createdAt: "2026-05-12T15:30:00Z", updatedAt: "2026-05-13T14:00:00Z", category: "legal", escalationLevel: 3, comments: [], tags: ["jurisdiction", "legal-review", "escalated"] },
  { id: "i6", title: "Data breach notification 24h SLA is aggressive", description: "Vendor's security team indicates 24-hour breach notification may not be feasible for all incident types. Consider 48-72 hour window with exceptions.", clauseId: "c4", sectionNumber: "10.1", severity: "major", status: "open", assignee: "James Wilson", assigneeAvatar: "JW", dueDate: "2026-05-19", createdBy: "Michael Torres", createdAt: "2026-05-12T12:00:00Z", updatedAt: "2026-05-13T09:30:00Z", category: "compliance", escalationLevel: 0, comments: [], tags: ["data-privacy", "notification", "sla"] },
  { id: "i7", title: "Warranty disclaimer conflicts with service promises", description: "Adding limited warranty to Section 15 creates tension with broad disclaimer. Need to ensure consistency between warranty and disclaimer language.", clauseId: "c9", sectionNumber: "15.1", severity: "minor", status: "open", assignee: "Sarah Chen", assigneeAvatar: "SC", dueDate: "2026-05-23", createdBy: "Michael Torres", createdAt: "2026-05-12T15:00:00Z", updatedAt: "2026-05-13T12:00:00Z", category: "legal", escalationLevel: 0, comments: [], tags: ["warranty", "consistency"] },
  { id: "i8", title: "Payment dispute withholding needs safeguards", description: "Right to withhold disputed payments needs safeguards against abuse. Suggest requiring good faith certification and dispute escalation process.", clauseId: "c8", sectionNumber: "5.1", severity: "minor", status: "in-review", assignee: "Michael Torres", assigneeAvatar: "MT", dueDate: "2026-05-24", createdBy: "James Wilson", createdAt: "2026-05-12T14:30:00Z", updatedAt: "2026-05-13T13:00:00Z", category: "commercial", escalationLevel: 0, comments: [], tags: ["payment", "dispute", "safeguards"] },
];

// ── Participants ─────────────────────────────────────────────────────────

export const mockParticipants: Participant[] = [
  { id: "p1", name: "Sarah Chen", avatar: "SC", role: "owner", department: "Legal", isOnline: true, lastActive: "now", reviewedClauses: 8, pendingApprovals: 2 },
  { id: "p2", name: "Michael Torres", avatar: "MT", role: "reviewer", department: "Legal", isOnline: true, lastActive: "5m ago", reviewedClauses: 5, pendingApprovals: 3 },
  { id: "p3", name: "James Wilson", avatar: "JW", role: "external", department: "Vendor - Acme Corp", isOnline: false, lastActive: "2h ago", reviewedClauses: 3, pendingApprovals: 5 },
  { id: "p4", name: "Emily Nakamura", avatar: "EN", role: "approver", department: "Finance", isOnline: true, lastActive: "15m ago", reviewedClauses: 2, pendingApprovals: 1 },
  { id: "p5", name: "David Park", avatar: "DP", role: "reviewer", department: "Security", isOnline: false, lastActive: "1d ago", reviewedClauses: 4, pendingApprovals: 0 },
  { id: "p6", name: "Lisa Martinez", avatar: "LM", role: "viewer", department: "Procurement", isOnline: true, lastActive: "30m ago", reviewedClauses: 0, pendingApprovals: 0 },
];

// ── Comments ─────────────────────────────────────────────────────────────

export const mockComments: CommentItem[] = [
  { id: "cm1", author: "Michael Torres", authorAvatar: "MT", authorRole: "Legal Reviewer", content: "The 24-month liability cap is actually within market range for enterprise SaaS of this size. I've seen caps up to 36 months in similar deals. The carve-outs are the key protection here.", timestamp: "2026-05-12T16:00:00Z", status: "active", mentions: ["Sarah Chen"], clauseId: "c1", replies: [
    { id: "cm1a", author: "Sarah Chen", authorAvatar: "SC", authorRole: "Legal Lead", content: "Agreed. The carve-outs for IP infringement, confidentiality breach, and fraud give us the essential protection. Let's hold firm on the cap with these exceptions.", timestamp: "2026-05-12T16:30:00Z", status: "active", mentions: [], clauseId: "c1", replies: [] },
  ]},
  { id: "cm2", author: "James Wilson", authorAvatar: "JW", authorRole: "Vendor Counsel", content: "The 3-year indemnification survival is problematic for us. Our standard is 1 year. Can we meet at 2 years?", timestamp: "2026-05-13T09:00:00Z", status: "active", mentions: ["Michael Torres", "Sarah Chen"], clauseId: "c2", replies: [] },
  { id: "cm3", author: "Sarah Chen", authorAvatar: "SC", authorRole: "Legal Lead", content: "50% SLA credit for <95% uptime is aggressive but justified given the criticality of this platform. We can use this as a bargaining chip for the termination right.", timestamp: "2026-05-13T10:00:00Z", status: "active", mentions: [], clauseId: "c5", replies: [] },
  { id: "cm4", author: "Emily Nakamura", authorAvatar: "EN", authorRole: "Finance Approver", content: "From a finance perspective, the 45-day payment terms and dispute withholding are reasonable. We need the cash flow flexibility.", timestamp: "2026-05-13T11:00:00Z", status: "active", mentions: [], clauseId: "c8", replies: [] },
];

// Attach comments to redlines
mockRedlines[0].comments = [mockComments[0]];
mockRedlines[2].comments = [mockComments[1]];
mockRedlines[8].comments = [mockComments[2]];
mockRedlines[12].comments = [mockComments[3]];

// Attach comments to issues
mockIssues[0].comments = [mockComments[0]];
mockIssues[1].comments = [mockComments[1]];

// ── AI Insights ──────────────────────────────────────────────────────────

export const mockAiInsights: AiNegotiationInsight[] = [
  { id: "ai1", type: "benchmark", title: "Liability Cap Above Market Median", description: "The proposed 24-month liability cap is in the 75th percentile for enterprise SaaS agreements. Market median is 12 months. Consider negotiating down to 18 months as a compromise.", confidence: 92, impact: "high", benchmarkPercentile: 75, clauseId: "c1", suggestedResponse: "Offer to reduce to 18 months if vendor accepts the full liability carve-out list.", fallbackClause: "The total aggregate liability shall not exceed 150% of fees paid in the preceding 18 months.", severity: "warning", category: "liability" },
  { id: "ai2", type: "strategy", title: "Fallback Position Strengthens Leverage", description: "Adding no-early-termination-fee language gives significant leverage in future negotiations. This is a strong fallback position that 85% of enterprise buyers successfully include.", confidence: 88, impact: "high", benchmarkPercentile: 85, clauseId: "c3", suggestedResponse: "Maintain this position. Vendor may push back but market data supports it.", fallbackClause: "Customer may terminate without penalty upon 60 days notice.", severity: "success", category: "termination" },
  { id: "ai3", type: "risk", title: "Data Breach Notification SLA Exceeds Norms", description: "24-hour breach notification is in the 95th percentile. Most enterprise agreements specify 48-72 hours. Vendor may have legitimate operational concerns.", confidence: 85, impact: "medium", benchmarkPercentile: 95, clauseId: "c4", suggestedResponse: "Consider 48 hours for critical breaches, 72 hours for standard incidents as compromise.", fallbackClause: "Notification within 48 hours for critical breaches, 72 hours for all others.", severity: "warning", category: "data_privacy" },
  { id: "ai4", type: "opportunity", title: "SLA Termination Right as Key Leverage", description: "Adding termination right for sustained SLA failure is a powerful protection. Only 35% of agreements include this. It significantly strengthens your negotiating position on credits.", confidence: 94, impact: "high", benchmarkPercentile: 35, clauseId: "c5", suggestedResponse: "Use this as a bargaining chip - offer to increase credit thresholds in exchange for keeping termination right.", fallbackClause: "Customer may terminate if SLA < 95% for 3 consecutive months.", severity: "info", category: "sla" },
  { id: "ai5", type: "compliance", title: "Jurisdiction Change Requires Board Approval", description: "Changing from Delaware to New York jurisdiction is a significant legal shift. New York law is generally more plaintiff-friendly for contract disputes. This change requires formal board-level approval per corporate policy.", confidence: 96, impact: "high", benchmarkPercentile: 60, clauseId: "c10", suggestedResponse: "Flag for General Counsel review. Consider Delaware with vendor-favorable provisions as alternative.", fallbackClause: "Governed by Delaware law with mandatory arbitration in New York.", severity: "critical", category: "legal" },
  { id: "ai6", type: "benchmark", title: "Custom IP License Above Market", description: "Perpetual, irrevocable license to custom developments is in the 90th percentile. Most vendors grant limited-term licenses. Consider narrowing scope to 'material customizations' only.", confidence: 79, impact: "high", benchmarkPercentile: 90, clauseId: "c6", suggestedResponse: "Define 'customizations' explicitly and exclude Vendor's core platform IP.", fallbackClause: "License term matching the Agreement term with renewal option.", severity: "warning", category: "ip" },
  { id: "ai7", type: "strategy", title: "Confidentiality Extension - Low Risk", description: "Extending confidentiality from 3 to 5 years is well within market norms (3-7 years). This should be a straightforward acceptance.", confidence: 97, impact: "low", benchmarkPercentile: 55, clauseId: "c7", suggestedResponse: "Accept as is - no material risk.", fallbackClause: "Standard 5-year confidentiality term.", severity: "success", category: "confidentiality" },
  { id: "ai8", type: "risk", title: "Warranty Disclaimer vs Limited Warranty Conflict", description: "Adding a limited warranty while maintaining broad disclaimers creates potential ambiguity. Courts may interpret these inconsistently. Recommend aligning language to clarify that the limited warranty supersedes the disclaimer for specified periods.", confidence: 83, impact: "medium", benchmarkPercentile: 40, clauseId: "c9", suggestedResponse: "Add clarifying language that the limited warranty is an express exception to the disclaimer.", fallbackClause: "Warranty disclaimer applies except as expressly set forth in Section 15.2.", severity: "warning", category: "warranty" },
];

// ── Playbooks ────────────────────────────────────────────────────────────

export const mockPlaybooks: NegotiationPlaybook[] = [
  { id: "pb1", title: "Liability & Indemnification Playbook", description: "Standard approach for liability caps and indemnification clauses in enterprise SaaS agreements.", clauseCategory: "liability", fallbackClauses: [
    { id: "fb1", title: "12-Month Cap with Carve-outs", content: "Total aggregate liability not to exceed fees paid in preceding 12 months. Standard carve-outs for IP, confidentiality, GDPR, fraud.", strength: "strong", acceptanceRate: 92, riskReduction: 65, usageCount: 187 },
    { id: "fb2", title: "18-Month Cap (Compromise)", content: "Total aggregate liability not to exceed 150% of fees paid in preceding 18 months. Standard carve-outs apply.", strength: "moderate", acceptanceRate: 78, riskReduction: 45, usageCount: 124 },
    { id: "fb3", title: "24-Month Cap (Vendor-Friendly)", content: "Total aggregate liability not to exceed fees paid in preceding 24 months. No carve-outs.", strength: "weak", acceptanceRate: 45, riskReduction: 20, usageCount: 56 },
  ], escalationGuidance: "If vendor rejects all carve-outs, escalate to General Counsel. If cap exceeds 24 months, negotiate down with market benchmarking data.", riskTolerance: "moderate", jurisdictionNotes: "Delaware courts generally enforce liability caps. New York courts more likely to scrutinize.", aiRecommended: true },
  { id: "pb2", title: "Data Protection & Security Playbook", description: "Negotiation strategy for data privacy, security standards, and breach notification terms.", clauseCategory: "data_privacy", fallbackClauses: [
    { id: "fb4", title: "48-Hour Breach Notification", content: "Vendor shall notify Customer of any data breach within 48 hours of confirmation.", strength: "strong", acceptanceRate: 85, riskReduction: 55, usageCount: 203 },
    { id: "fb5", title: "72-Hour Breach Notification", content: "Vendor shall notify Customer of any data breach within 72 hours of discovery.", strength: "moderate", acceptanceRate: 72, riskReduction: 35, usageCount: 145 },
  ], escalationGuidance: "GDPR requires 72-hour notification. Use regulatory requirement as leverage for 48-hour SLA.", riskTolerance: "conservative", aiRecommended: true },
  { id: "pb3", title: "SLA & Performance Playbook", description: "Service level agreement negotiation strategies including uptime, credits, and termination rights.", clauseCategory: "sla", fallbackClauses: [
    { id: "fb6", title: "Tiered Credits + Termination", content: "99.9% uptime SLA with escalating credits (5%/10%/25%) and termination right for sustained failure.", strength: "strong", acceptanceRate: 82, riskReduction: 70, usageCount: 156 },
    { id: "fb7", title: "Enhanced Credits No Termination", content: "99.95% uptime with enhanced credits (10%/20%/50%) but no termination right.", strength: "moderate", acceptanceRate: 68, riskReduction: 45, usageCount: 89 },
  ], escalationGuidance: "If vendor insists on removing termination right, demand significantly higher credit rates (2x standard).", riskTolerance: "moderate", aiRecommended: true },
];

// ── Workflow ─────────────────────────────────────────────────────────────

export const mockWorkflow: NegotiationWorkflow = {
  id: "wf1",
  stage: "negotiating",
  slaDeadline: "2026-05-25T17:00:00Z",
  slaRemaining: 86400 * 5,
  approvers: [
    { name: "Emily Nakamura", avatar: "EN", status: "pending" },
    { name: "David Park", avatar: "DP", status: "pending" },
    { name: "General Counsel", avatar: "GC", status: "pending" },
  ],
  escalationLevel: 2,
  isOverdue: false,
  healthScore: 72,
};

// ── Analytics ────────────────────────────────────────────────────────────

export const mockAnalytics: NegotiationAnalytics = {
  totalSessions: 24,
  avgCycleTime: 6.2,
  concessionRate: 34,
  redlineAcceptanceRate: 84,
  clauseDisputeFrequency: [
    { clause: "Limitation of Liability", count: 18 },
    { clause: "Indemnification", count: 14 },
    { clause: "SLA & Credits", count: 12 },
    { clause: "Data Protection", count: 10 },
    { clause: "IP Rights", count: 8 },
    { clause: "Termination", count: 6 },
  ],
  vendorAggressiveness: [
    { vendor: "Acme Corp", score: 78 },
    { vendor: "TechSphere Inc", score: 92 },
    { vendor: "DataVault Systems", score: 45 },
    { vendor: "CloudNexus", score: 65 },
    { vendor: "SecurePath Ltd", score: 55 },
  ],
  cycleBottlenecks: [
    { stage: "Legal Review", avgDays: 2.5 },
    { stage: "Vendor Response", avgDays: 3.2 },
    { stage: "Security Review", avgDays: 1.8 },
    { stage: "Finance Approval", avgDays: 1.2 },
    { stage: "Final Sign-off", avgDays: 0.8 },
  ],
  timelineData: [
    { date: "May 1", redlines: 12, approvals: 5, comments: 8 },
    { date: "May 3", redlines: 18, approvals: 7, comments: 12 },
    { date: "May 5", redlines: 15, approvals: 10, comments: 15 },
    { date: "May 7", redlines: 22, approvals: 8, comments: 20 },
    { date: "May 9", redlines: 20, approvals: 12, comments: 18 },
    { date: "May 11", redlines: 25, approvals: 15, comments: 22 },
    { date: "May 13", redlines: 28, approvals: 18, comments: 25 },
  ],
  issueHeatmap: [
    { category: "Liability", severity: "blocker", count: 2 },
    { category: "Liability", severity: "critical", count: 3 },
    { category: "Liability", severity: "major", count: 5 },
    { category: "Indemnification", severity: "critical", count: 4 },
    { category: "Indemnification", severity: "major", count: 3 },
    { category: "SLA", severity: "major", count: 6 },
    { category: "SLA", severity: "minor", count: 4 },
    { category: "Data Privacy", severity: "critical", count: 3 },
    { category: "Data Privacy", severity: "major", count: 4 },
    { category: "IP", severity: "major", count: 3 },
    { category: "Commercial", severity: "minor", count: 5 },
  ],
  reviewThroughput: [
    { reviewer: "Sarah Chen", reviewed: 8, avgTime: 1.5 },
    { reviewer: "Michael Torres", reviewed: 5, avgTime: 2.1 },
    { reviewer: "David Park", reviewed: 4, avgTime: 3.2 },
    { reviewer: "Emily Nakamura", reviewed: 2, avgTime: 0.8 },
  ],
};

// ── Activity ─────────────────────────────────────────────────────────────

export const mockActivities: ActivityEntry[] = [
  { id: "a1", type: "edit", user: "Sarah Chen", userAvatar: "SC", action: "Modified clause", description: "Updated Limitation of Liability - cap increased to 24 months with carve-outs", timestamp: "2026-05-12T16:45:00Z", clauseId: "c1", versionId: "v4" },
  { id: "a2", type: "ai_action", user: "AI Assistant", userAvatar: "AI", action: "Suggested redline", description: "AI generated fallback clause for Limitation of Liability - 18 month compromise option", timestamp: "2026-05-12T16:30:00Z", clauseId: "c1" },
  { id: "a3", type: "comment", user: "Michael Torres", userAvatar: "MT", action: "Added comment", description: "Commented on Limitation of Liability - market range validation", timestamp: "2026-05-12T16:00:00Z", clauseId: "c1" },
  { id: "a4", type: "edit", user: "Michael Torres", userAvatar: "MT", action: "Modified clause", description: "Added indemnification survival period of 3 years", timestamp: "2026-05-12T11:00:00Z", clauseId: "c2", versionId: "v2" },
  { id: "a5", type: "approval", user: "Sarah Chen", userAvatar: "SC", action: "Accepted redline", description: "Accepted termination notice reduction from 90 to 60 days", timestamp: "2026-05-12T11:15:00Z", clauseId: "c3" },
  { id: "a6", type: "ai_action", user: "AI Assistant", userAvatar: "AI", action: "Generated insight", description: "AI identified jurisdiction change requires board approval", timestamp: "2026-05-12T15:35:00Z", clauseId: "c10" },
  { id: "a7", type: "escalation", user: "Sarah Chen", userAvatar: "SC", action: "Escalated issue", description: "Jurisdiction change escalated to General Counsel for review", timestamp: "2026-05-12T15:30:00Z", clauseId: "c10" },
  { id: "a8", type: "status_change", user: "System", userAvatar: "S", action: "Stage changed", description: "Negotiation moved from Review to Negotiating stage", timestamp: "2026-05-12T10:00:00Z" },
  { id: "a9", type: "version_create", user: "Sarah Chen", userAvatar: "SC", action: "Created version", description: "Created version v4 - Current Redline with comprehensive AI suggestions", timestamp: "2026-05-12T16:45:00Z", versionId: "v4" },
  { id: "a10", type: "comment", user: "James Wilson", userAvatar: "JW", action: "Added comment", description: "Vendor counsel pushed back on 3-year indemnification survival", timestamp: "2026-05-13T09:00:00Z", clauseId: "c2" },
  { id: "a11", type: "edit", user: "Sarah Chen", userAvatar: "SC", action: "Modified clause", description: "Updated SLA uptime to 99.95% with enhanced credit structure", timestamp: "2026-05-12T12:35:00Z", clauseId: "c5", versionId: "v4" },
  { id: "a12", type: "ai_action", user: "AI Assistant", userAvatar: "AI", action: "Generated strategy", description: "AI recommended using SLA termination right as negotiation leverage", timestamp: "2026-05-12T12:40:00Z", clauseId: "c5" },
];

// ── Complete Session ─────────────────────────────────────────────────────

export const mockNegotiationSession: NegotiationSession = {
  id: "ns1",
  contractTitle: "Master Service Agreement - Acme Corp",
  counterparty: "Acme Corporation",
  stage: "negotiating",
  versions: mockVersions,
  currentVersionId: "v4",
  redlines: mockRedlines,
  issues: mockIssues,
  participants: mockParticipants,
  insights: mockAiInsights,
  playbooks: mockPlaybooks,
  workflow: mockWorkflow,
  analytics: mockAnalytics,
  activities: mockActivities,
  healthScore: 72,
  startedAt: "2026-04-28T09:00:00Z",
  updatedAt: "2026-05-13T14:00:00Z",
};

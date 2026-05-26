// ── Enterprise Search & Discovery Hub Mock Data ──────────────────────────

import type {
  SearchKpi, SearchResult, SearchCategory, SavedSearch, RecentSearch,
  AiSearchSuggestion, AiDiscoveryInsight, SearchAnalytics, QuickPreviewData,
  SearchFilter, SearchHighlight, RelatedEntity,
} from "./types";

// ── KPI Data ─────────────────────────────────────────────────────────────

export const mockSearchKpis: SearchKpi[] = [
  { id: "indexed-contracts", label: "Indexed Contracts", value: "14,892", trend: 8, trendDirection: "up", icon: "FileText", color: "from-blue-500 to-blue-600", severity: "info", sparklineData: [12000, 12800, 13500, 14000, 14500, 14892], tooltip: "14,892 contracts indexed and searchable across all sources" },
  { id: "search-accuracy", label: "Search Accuracy", value: "96.2%", trend: 2.1, trendDirection: "up", icon: "Target", color: "from-green-500 to-green-600", severity: "success", sparklineData: [91, 92.5, 93.8, 94.5, 95.3, 96.2], tooltip: "96.2% semantic search accuracy rate with vector retrieval" },
  { id: "ai-confidence", label: "AI Retrieval Confidence", value: "88.7%", trend: 4.3, trendDirection: "up", icon: "Brain", color: "from-purple-500 to-purple-600", severity: "success", sparklineData: [82, 83.5, 85, 86.2, 87.5, 88.7], tooltip: "88.7% average AI retrieval confidence score" },
  { id: "clause-matches", label: "Clause Matches Found", value: "47,321", trend: 15, trendDirection: "up", icon: "FileSearch", color: "from-amber-500 to-amber-600", severity: "info", sparklineData: [32000, 36000, 39000, 42000, 45000, 47321], tooltip: "47,321 clause-level matches discovered across corpus" },
  { id: "relationship-disc", label: "Relationship Discoveries", value: "1,847", trend: 22, trendDirection: "up", icon: "Share2", color: "from-teal-500 to-teal-600", severity: "info", sparklineData: [980, 1150, 1320, 1500, 1680, 1847], tooltip: "1,847 hidden relationships discovered by AI analysis" },
  { id: "ai-insights", label: "Recent AI Insights", value: "342", trend: 18, trendDirection: "up", icon: "Lightbulb", color: "from-gold-500 to-gold-600", severity: "info", sparklineData: [180, 210, 245, 280, 310, 342], tooltip: "342 AI-generated insights in the last 30 days" },
  { id: "saved-alerts", label: "Saved Search Alerts", value: "56", trend: 12, trendDirection: "up", icon: "Bell", color: "from-rose-500 to-rose-600", severity: "info", sparklineData: [38, 42, 45, 48, 52, 56], tooltip: "56 active saved search alerts monitoring for changes" },
  { id: "high-risk-disc", label: "High-Risk Discoveries", value: "128", trend: -8, trendDirection: "down", icon: "AlertTriangle", color: "from-red-500 to-red-600", severity: "critical", sparklineData: [165, 158, 148, 140, 132, 128], tooltip: "128 high-risk clauses and obligations discovered" },
];

// ── Search Categories ────────────────────────────────────────────────────

export const mockSearchCategories: SearchCategory[] = [
  { id: "all", label: "All Results", icon: "Search", count: 14892, description: "Search across all indexed content" },
  { id: "contracts", label: "Contracts", icon: "FileText", count: 4892, description: "Full contract documents" },
  { id: "clauses", label: "Clauses", icon: "FileSearch", count: 32104, description: "Individual clause extractions" },
  { id: "obligations", label: "Obligations", icon: "ClipboardCheck", count: 8942, description: "Post-signature obligations" },
  { id: "vendors", label: "Vendors", icon: "Building2", count: 1247, description: "Vendor profiles and relationships" },
  { id: "workflows", label: "Workflows", icon: "Workflow", count: 892, description: "Active and completed workflows" },
  { id: "negotiations", label: "Negotiations", icon: "GitMerge", count: 456, description: "Negotiation sessions and redlines" },
  { id: "benchmarks", label: "Benchmarks", icon: "BarChart3", count: 284, description: "Market benchmark data" },
  { id: "audit", label: "Audit Events", icon: "ScrollText", count: 12842, description: "Audit trail and compliance events" },
];

// ── Saved Searches ───────────────────────────────────────────────────────

export const mockSavedSearches: SavedSearch[] = [
  { id: "ss1", name: "Uncapped Liability", query: "uncapped liability OR unlimited liability", mode: "semantic", filters: [{ id: "f1", category: "risk_level", label: "Risk Level", value: "high" }], alertEnabled: true, lastRun: "2026-05-15T09:00:00Z", resultCount: 18, frequency: "daily" },
  { id: "ss2", name: "GDPR Compliance Gaps", query: "GDPR compliance missing data protection", mode: "ai_assisted", filters: [{ id: "f2", category: "compliance_category", label: "Compliance", value: "gdpr" }], alertEnabled: true, lastRun: "2026-05-14T14:00:00Z", resultCount: 24, frequency: "daily" },
  { id: "ss3", name: "German Contracts Expiring", query: "contracts expiring Germany Q3 2026", mode: "hybrid", filters: [{ id: "f3", category: "geography", label: "Geography", value: "Germany" }], alertEnabled: false, lastRun: "2026-05-13T11:00:00Z", resultCount: 7, frequency: "weekly" },
  { id: "ss4", name: "SLA Breach Patterns", query: "SLA breach OR service level failure remedies", mode: "semantic", filters: [], alertEnabled: true, lastRun: "2026-05-15T06:00:00Z", resultCount: 31, frequency: "daily" },
  { id: "ss5", name: "Indemnification Clauses", query: "indemnify indemnification hold harmless", mode: "keyword", filters: [{ id: "f4", category: "clause_category", label: "Clause Category", value: "indemnification" }], alertEnabled: false, lastRun: "2026-05-10T16:00:00Z", resultCount: 142, frequency: "weekly" },
];

// ── Recent Searches ──────────────────────────────────────────────────────

export const mockRecentSearches: RecentSearch[] = [
  { id: "rs1", query: "uncapped liability exposure", mode: "semantic", timestamp: "2026-05-15T08:45:00Z", resultCount: 18 },
  { id: "rs2", query: "GDPR data processing agreements", mode: "ai_assisted", timestamp: "2026-05-15T08:30:00Z", resultCount: 24 },
  { id: "rs3", query: "contracts similar to MSA-204", mode: "vector", timestamp: "2026-05-15T08:15:00Z", resultCount: 12 },
  { id: "rs4", query: "force majeure pandemic clause", mode: "semantic", timestamp: "2026-05-14T16:20:00Z", resultCount: 37 },
  { id: "rs5", query: "termination for convenience 30 days", mode: "keyword", timestamp: "2026-05-14T14:00:00Z", resultCount: 53 },
];

// ── AI Suggestions ───────────────────────────────────────────────────────

export const mockAiSuggestions: AiSearchSuggestion[] = [
  { id: "as1", query: "unlimited liability OR no cap liability damages", description: "Broaden to find all uncapped liability variants", type: "expansion", confidence: 94, reason: "Semantic similarity detected across 42 contracts" },
  { id: "as2", query: "data breach notification 24 hours", description: "Find breach notification SLAs", type: "refinement", confidence: 91, reason: "Refining from GDPR compliance search" },
  { id: "as3", query: "contracts with auto-renewal clauses Germany", description: "German contracts with auto-renewal risk", type: "exploration", confidence: 87, reason: "Cross-reference: geography + clause category" },
  { id: "as4", query: "vendor agreements with most-favored-nation pricing", description: "MFN pricing clauses in vendor contracts", type: "related", confidence: 83, reason: "Related to your uncapped liability search pattern" },
  { id: "as5", query: "indemnification survival period 3 years", description: "Extended indemnification terms", type: "anomaly", confidence: 76, reason: "Above-market survival periods detected in 8 contracts" },
];

// ── AI Discovery Insights ────────────────────────────────────────────────

export const mockDiscoveryInsights: AiDiscoveryInsight[] = [
  { id: "di1", type: "relationship", title: "Related Vendor Agreements Found", description: "18 contracts share similar liability language with Acme Corp MSA. Potential for consolidated negotiation.", confidence: 94, impact: "high", entities: ["Acme Corp", "TechSphere Inc", "DataVault Systems"], severity: "info", suggestedQuery: "liability language similar to MSA-204" },
  { id: "di2", type: "anomaly", title: "Hidden Renewal Exposure Detected", description: "7 contracts have auto-renewal clauses with less than 30-day notice periods. Risk of unintended renewals.", confidence: 92, impact: "high", entities: ["CloudNexus", "SecurePath Ltd", "GlobalTech Partners"], severity: "critical", suggestedQuery: "auto-renewal notice period < 30 days" },
  { id: "di3", type: "pattern", title: "Clause Similarity Cluster Identified", description: "Limitation of liability clauses across 18 contracts share 85%+ semantic similarity. Consider standardizing.", confidence: 88, impact: "medium", entities: ["18 contracts in portfolio"], severity: "info", suggestedQuery: "limitation of liability standardize" },
  { id: "di4", type: "compliance", title: "Compliance Gap Pattern Discovered", description: "12 contracts lack required GDPR data processing addendums. Non-compliance risk for EU operations.", confidence: 96, impact: "high", entities: ["GDPR", "EU Operations"], severity: "critical", suggestedQuery: "contracts missing DPA GDPR" },
  { id: "di5", type: "recommendation", title: "Negotiation Leverage Opportunity", description: "8 vendor contracts with below-market indemnification terms. Renegotiation opportunity identified.", confidence: 84, impact: "medium", entities: ["TechSphere Inc", "DataVault Systems", "CloudNexus"], severity: "info", suggestedQuery: "below-market indemnification terms" },
];

// ── Search Results ───────────────────────────────────────────────────────

const makeHighlights = (): SearchHighlight[] => [
  { field: "content", text: "unlimited liability", startOffset: 0, endOffset: 17, type: "keyword" },
  { field: "content", text: "uncapped damages", startOffset: 45, endOffset: 60, type: "semantic" },
  { field: "summary", text: "financial exposure risk", startOffset: 10, endOffset: 30, type: "ai_highlight" },
];

const makeEntities = (type: string): RelatedEntity[] => [
  { id: "e1", type: "contract", label: "MSA-204", relationship: "Parent contract", riskLevel: "high" },
  { id: "e2", type: "vendor", label: "Acme Corp", relationship: "Counterparty", riskLevel: "medium" },
  { id: "e3", type: "clause", label: "Section 12.1", relationship: "Related clause", riskLevel: "high" },
];

export const mockSearchResults: SearchResult[] = [
  { id: "res1", type: "contract", title: "Master Service Agreement - Acme Corp", subtitle: "MSA-204 · Enterprise Software License", snippet: "...shall not be liable for any indirect damages, provided that <mark>unlimited liability</mark> shall apply for breach of confidentiality, IP infringement, and fraud...", semanticSummary: "This MSA contains uncapped liability provisions for specific high-risk categories including confidentiality breaches and IP infringement. The unlimited liability exposure represents significant financial risk.", matchExplanation: "Semantic match: 'uncapped liability' detected in liability clause. Keyword match: 'unlimited liability' found in Section 12.1 carve-outs.", confidence: 96, riskLevel: "high", highlights: makeHighlights(), entities: makeEntities("contract"), metadata: { value: "$2.4M", jurisdiction: "Delaware", term: "36 months" }, lastUpdated: "2026-05-12T16:45:00Z", status: "active", vectorScore: 0.94, keywordScore: 0.88, hybridScore: 0.92 },
  { id: "res2", type: "clause", title: "Limitation of Liability - Section 12.1", subtitle: "Clause · Acme Corp MSA", snippet: "Notwithstanding the foregoing, nothing in this Section 12.1 shall limit either party's liability for: (a) breach of confidentiality obligations; (b) <mark>infringement of intellectual property</mark> rights; (c) death or personal injury; or (d) fraud or willful misconduct. These carve-outs represent <mark>uncapped liability exposure</mark>.", semanticSummary: "Clause 12.1 contains four uncapped liability carve-outs. The IP infringement and confidentiality breach exceptions are particularly broad and exceed market norms.", matchExplanation: "Semantic match: 'uncapped liability' identified in carve-out provisions. Vector similarity: 94% match to similar clauses in 18 other contracts.", confidence: 94, riskLevel: "critical", highlights: makeHighlights(), entities: makeEntities("clause"), metadata: { section: "12.1", category: "liability", risk: "critical" }, lastUpdated: "2026-05-12T10:30:00Z", status: "active", vectorScore: 0.96, keywordScore: 0.85, hybridScore: 0.93 },
  { id: "res3", type: "obligation", title: "GDPR Data Processing Addendum Required", subtitle: "Obligation · TechSphere Inc Agreement", snippet: "Obligation to execute <mark>GDPR-compliant data processing addendum</mark> within 30 days of contract effective date. Current status: OVERDUE by 45 days. Non-compliance risk: HIGH.", semanticSummary: "This obligation requires a GDPR DPA that has not been executed. The 45-day overdue status indicates active compliance risk for EU operations.", matchExplanation: "AI-assisted discovery: Pattern match for 'missing GDPR documentation' across vendor agreements. Semantic query expansion from 'GDPR compliance'.", confidence: 97, riskLevel: "critical", highlights: makeHighlights(), entities: [{ id: "e4", type: "vendor", label: "TechSphere Inc", relationship: "Counterparty" }, { id: "e5", type: "obligation", label: "DPA-Required", relationship: "Compliance obligation" }], metadata: { priority: "critical", daysOverdue: "45", regulation: "GDPR" }, lastUpdated: "2026-05-15T06:00:00Z", status: "overdue", vectorScore: 0.91, keywordScore: 0.79, hybridScore: 0.87 },
  { id: "res4", type: "contract", title: "Software License Agreement - TechSphere Inc", subtitle: "SLA-089 · SaaS Platform License", snippet: "Vendor shall maintain <mark>99.9% service availability</mark>. In the event of SLA breach, Customer shall receive service credits... SLA breach history: 3 incidents in last 6 months.", semanticSummary: "This agreement has experienced 3 SLA breaches in 6 months with accumulated service credits. The current SLA remedy structure may be insufficient for business impact.", matchExplanation: "Keyword match: 'SLA breach'. Semantic context: service level failure patterns detected across multiple periods.", confidence: 89, riskLevel: "high", highlights: makeHighlights(), entities: [{ id: "e6", type: "vendor", label: "TechSphere Inc", relationship: "Counterparty" }, { id: "e7", type: "workflow", label: "SLA-CLAIM-089", relationship: "Active claim" }], metadata: { value: "$890K", sla: "99.9%", breaches: "3" }, lastUpdated: "2026-05-14T11:00:00Z", status: "active", vectorScore: 0.87, keywordScore: 0.92, hybridScore: 0.89 },
  { id: "res5", type: "vendor", title: "DataVault Systems - Vendor Profile", subtitle: "Vendor · Cloud Infrastructure Provider", snippet: "Relationship strength: STRONG. 4 active contracts. Total spend: $4.2M. <mark>Risk score: 72/100</mark>. Recent negotiation: Liability cap increased to 24 months. Compliance: SOC 2 Type II certified.", semanticSummary: "DataVault Systems is a strategic vendor with 4 active contracts. Recent negotiation improved liability terms. Ongoing monitoring recommended for SLA compliance.", matchExplanation: "Relationship-aware search: Cross-reference vendor profile with contract portfolio. Semantic discovery: vendor concentration risk.", confidence: 85, riskLevel: "medium", highlights: makeHighlights(), entities: [{ id: "e8", type: "contract", label: "MSA-089", relationship: "Active contract" }, { id: "e9", type: "contract", label: "DPA-012", relationship: "Active contract" }], metadata: { contracts: "4", totalSpend: "$4.2M", riskScore: "72" }, lastUpdated: "2026-05-13T14:00:00Z", status: "active", vectorScore: 0.82, keywordScore: 0.75, hybridScore: 0.79 },
  { id: "res6", type: "negotiation", title: "Negotiation Session - CloudNexus Renewal", subtitle: "Negotiation · MSA-156 Renewal", snippet: "Stage: NEGOTIATING. Key issues: <mark>Auto-renewal clause dispute</mark>, liability cap (proposed: 12 months, vendor: 24 months), SLA credits. AI recommendation: Hold firm on 12-month cap.", semanticSummary: "Active negotiation with CloudNexus for MSA renewal. Critical issue: auto-renewal terms. AI suggests maintaining 12-month liability cap position.", matchExplanation: "AI-assisted discovery: Negotiation with high-risk auto-renewal clause. Semantic match: 'auto-renewal dispute' detected.", confidence: 92, riskLevel: "high", highlights: makeHighlights(), entities: [{ id: "e10", type: "vendor", label: "CloudNexus", relationship: "Counterparty" }, { id: "e11", type: "workflow", label: "NEG-156", relationship: "Active workflow" }], metadata: { stage: "negotiating", started: "2026-04-28", deadline: "2026-05-25" }, lastUpdated: "2026-05-15T10:00:00Z", status: "in_progress", vectorScore: 0.88, keywordScore: 0.81, hybridScore: 0.85 },
  { id: "res7", type: "clause", title: "Auto-Renewal Clause - Section 16.3", subtitle: "Clause · CloudNexus Agreement", snippet: "This Agreement shall <mark>automatically renew for successive one-year terms</mark> unless either party provides written notice of non-renewal at least <mark>15 days prior</mark> to the end of the current term.", semanticSummary: "Auto-renewal clause with only 15-day notice period. Significantly below market standard of 60-90 days. High risk of unintended renewal.", matchExplanation: "Semantic match: 'auto-renewal' detected. Anomaly detection: 15-day notice period is in bottom 5th percentile (market median: 60 days).", confidence: 95, riskLevel: "critical", highlights: makeHighlights(), entities: [{ id: "e12", type: "contract", label: "CLA-156", relationship: "Parent contract" }, { id: "e13", type: "vendor", label: "CloudNexus", relationship: "Counterparty" }], metadata: { section: "16.3", noticePeriod: "15 days", marketMedian: "60 days" }, lastUpdated: "2026-05-12T15:30:00Z", status: "active", vectorScore: 0.93, keywordScore: 0.87, hybridScore: 0.91 },
  { id: "res8", type: "benchmark", title: "Liability Cap Market Benchmark", subtitle: "Benchmark · Enterprise SaaS 2026", snippet: "Market analysis of 500+ enterprise SaaS agreements. <mark>Median liability cap: 12 months fees</mark>. 75th percentile: 24 months. Your portfolio average: 18 months. Acme Corp MSA at 24 months is above market.", semanticSummary: "Benchmark data shows your portfolio's liability caps are above market median. The Acme Corp MSA at 24 months is in the 75th percentile.", matchExplanation: "Benchmark cross-reference: portfolio liability caps vs market data. AI insight: optimization opportunity identified.", confidence: 93, riskLevel: "medium", highlights: makeHighlights(), entities: [{ id: "e14", type: "contract", label: "MSA-204", relationship: "Above benchmark" }], metadata: { source: "500+ agreements", median: "12 months", portfolioAvg: "18 months" }, lastUpdated: "2026-05-10T09:00:00Z", status: "active", vectorScore: 0.86, keywordScore: 0.78, hybridScore: 0.83 },
  { id: "res9", type: "workflow", title: "SLA Credit Claim - TechSphere Inc", subtitle: "Workflow · SLA-CLAIM-089", snippet: "Status: IN REVIEW. <mark>3 SLA breaches in Q2 2026</mark>. Claimed credits: $12,450. Approver: Emily Nakamura. SLA: 5 business days remaining.", semanticSummary: "Active SLA credit claim for TechSphere Inc. Three breaches in Q2 with $12,450 in claimed credits. Requires finance approval.", matchExplanation: "Keyword match: 'SLA breach'. Workflow correlation: active claim tied to search query.", confidence: 88, riskLevel: "medium", highlights: makeHighlights(), entities: [{ id: "e15", type: "contract", label: "SLA-089", relationship: "Source agreement" }, { id: "e16", type: "user", label: "Emily Nakamura", relationship: "Approver" }], metadata: { status: "in_review", credits: "$12,450", slaRemaining: "5 days" }, lastUpdated: "2026-05-15T08:00:00Z", status: "in_review", vectorScore: 0.84, keywordScore: 0.82, hybridScore: 0.83 },
  { id: "res10", type: "audit_event", title: "Compliance Audit - GDPR Gap Analysis", subtitle: "Audit · Q2 2026 Compliance Review", snippet: "Audit finding: <mark>12 contracts missing required GDPR DPAs</mark>. Risk level: CRITICAL. Remediation deadline: 2026-06-30. Assigned to: Sarah Chen, Legal.", semanticSummary: "Q2 compliance audit identified 12 contracts without required GDPR data processing addendums. Critical finding requiring remediation by June 30.", matchExplanation: "AI-assisted discovery: Pattern detection for missing compliance documentation. Semantic expansion from 'GDPR compliance'.", confidence: 98, riskLevel: "critical", highlights: makeHighlights(), entities: [{ id: "e17", type: "user", label: "Sarah Chen", relationship: "Assignee" }, { id: "e18", type: "obligation", label: "GDPR-DPA", relationship: "Remediation required" }], metadata: { finding: "Missing DPAs", count: "12", deadline: "2026-06-30" }, lastUpdated: "2026-05-14T16:00:00Z", status: "open", vectorScore: 0.95, keywordScore: 0.84, hybridScore: 0.91 },
];

// ── Quick Preview Data ───────────────────────────────────────────────────

export const mockQuickPreviewData: QuickPreviewData = {
  overview: {
    description: "Master Service Agreement between Customer and Acme Corporation for enterprise software licensing and professional services.",
    status: "Active",
    riskLevel: "high",
    value: "$2,400,000",
    counterparty: "Acme Corporation",
    dates: { start: "2026-01-15", end: "2028-01-14" },
    businessUnit: "Enterprise Technology",
  },
  insights: mockDiscoveryInsights,
  clauses: [
    { id: "c1", title: "Limitation of Liability", riskLevel: "critical", summary: "Uncapped liability for IP infringement, confidentiality breach, fraud" },
    { id: "c2", title: "Indemnification", riskLevel: "high", summary: "3-year survival period above market norm" },
    { id: "c3", title: "Data Protection", riskLevel: "high", summary: "GDPR compliance required, DPA status unknown" },
    { id: "c4", title: "Termination", riskLevel: "medium", summary: "60-day notice, no early termination fees" },
  ],
  relationships: [
    { entity: "TechSphere Inc", type: "Vendor", strength: 85 },
    { entity: "DataVault Systems", type: "Vendor", strength: 72 },
    { entity: "CloudNexus", type: "Vendor", strength: 65 },
    { entity: "SecurePath Ltd", type: "Vendor", strength: 58 },
  ],
  workflow: [
    { stage: "Legal Review", assignee: "Sarah Chen", sla: "5 days", status: "completed" },
    { stage: "Security Review", assignee: "David Park", sla: "3 days", status: "completed" },
    { stage: "Finance Approval", assignee: "Emily Nakamura", sla: "2 days", status: "pending" },
    { stage: "Final Sign-off", assignee: "General Counsel", sla: "1 day", status: "pending" },
  ],
  obligations: [
    { title: "GDPR DPA Execution", status: "overdue", dueDate: "2026-04-30" },
    { title: "SOC 2 Report Submission", status: "pending", dueDate: "2026-06-30" },
    { title: "Quarterly Security Review", status: "completed", dueDate: "2026-03-31" },
  ],
  activity: [
    { action: "Contract signed", user: "Sarah Chen", timestamp: "2026-01-15T10:00:00Z" },
    { action: "Liability clause modified", user: "Michael Torres", timestamp: "2026-05-12T16:45:00Z" },
    { action: "AI risk assessment completed", user: "AI Assistant", timestamp: "2026-05-13T09:00:00Z" },
    { action: "Compliance gap flagged", user: "AI Assistant", timestamp: "2026-05-14T16:00:00Z" },
  ],
  similarResults: mockSearchResults.slice(0, 3),
};

// ── Search Analytics ─────────────────────────────────────────────────────

export const mockSearchAnalytics: SearchAnalytics = {
  totalSearches: 28472,
  avgLatency: 142,
  semanticAccuracy: 96.2,
  zeroResultRate: 2.1,
  clickThroughRate: 68.4,
  popularSearches: [
    { query: "uncapped liability", count: 342, trend: 15 },
    { query: "GDPR compliance", count: 287, trend: 22 },
    { query: "SLA breach", count: 198, trend: -5 },
    { query: "auto-renewal", count: 165, trend: 35 },
    { query: "indemnification", count: 142, trend: 8 },
    { query: "force majeure", count: 98, trend: -12 },
    { query: "termination for convenience", count: 87, trend: 3 },
    { query: "data processing agreement", count: 76, trend: 28 },
  ],
  failedSearches: [
    { query: "contracts with pink elephants", count: 12, reason: "Zero results - no semantic matches" },
    { query: "asdfgh", count: 8, reason: "Typo - no close matches" },
    { query: "quantum computing liability", count: 5, reason: "No contracts in this domain" },
  ],
  searchTrends: [
    { date: "May 1", searches: 892, uniqueUsers: 145 },
    { date: "May 3", searches: 945, uniqueUsers: 162 },
    { date: "May 5", searches: 1024, uniqueUsers: 178 },
    { date: "May 7", searches: 987, uniqueUsers: 155 },
    { date: "May 9", searches: 1102, uniqueUsers: 188 },
    { date: "May 11", searches: 1156, uniqueUsers: 195 },
    { date: "May 13", searches: 1245, uniqueUsers: 210 },
    { date: "May 15", searches: 1189, uniqueUsers: 202 },
  ],
  latencyDistribution: [
    { range: "<50ms", count: 8542 },
    { range: "50-100ms", count: 11245 },
    { range: "100-200ms", count: 5698 },
    { range: "200-500ms", count: 2135 },
    { range: ">500ms", count: 852 },
  ],
  categoryDistribution: [
    { category: "Contracts", count: 8942 },
    { category: "Clauses", count: 7124 },
    { category: "Obligations", count: 4562 },
    { category: "Vendors", count: 3241 },
    { category: "Workflows", count: 1872 },
    { category: "Negotiations", count: 1245 },
    { category: "Benchmarks", count: 856 },
    { category: "Audit Events", count: 630 },
  ],
  aiRetrievalQuality: [
    { date: "May 1", precision: 94.5, recall: 91.2 },
    { date: "May 4", precision: 95.1, recall: 92.0 },
    { date: "May 7", precision: 95.8, recall: 92.5 },
    { date: "May 10", precision: 96.0, recall: 93.1 },
    { date: "May 13", precision: 96.2, recall: 93.5 },
  ],
};

// ── Search Mode Labels ───────────────────────────────────────────────────

export const searchModeLabels: Record<string, { label: string; description: string; icon: string }> = {
  semantic: { label: "Semantic Search", description: "Understands meaning and context beyond keywords", icon: "Brain" },
  keyword: { label: "Keyword Search", description: "Exact term and phrase matching", icon: "Search" },
  vector: { label: "Vector Search", description: "Similarity-based retrieval using embeddings", icon: "Layers" },
  hybrid: { label: "Hybrid Search", description: "Combined semantic + keyword for optimal results", icon: "GitMerge" },
  ai_assisted: { label: "AI-Assisted", description: "Full AI-powered retrieval with contextual understanding", icon: "Sparkles" },
};

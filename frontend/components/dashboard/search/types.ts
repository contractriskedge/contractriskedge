// ── Enterprise Search & Discovery Hub Types ──────────────────────────────

export type RiskLevel = "critical" | "high" | "medium" | "low" | "info";
export type SearchResultType = "contract" | "clause" | "obligation" | "signature" | "vendor" | "workflow" | "negotiation" | "benchmark" | "audit_event" | "playbook" | "redline";
export type SearchMode = "semantic" | "keyword" | "vector" | "hybrid" | "ai_assisted";
export type FilterCategory = "contract_type" | "vendor" | "geography" | "risk_level" | "workflow_stage" | "clause_category" | "business_unit" | "date_range" | "compliance_category" | "negotiation_status";

// ── Search KPI ───────────────────────────────────────────────────────────

export interface SearchKpi {
  id: string; label: string; value: string; trend: number;
  trendDirection: "up" | "down" | "neutral";
  icon: string; color: string; severity: "critical" | "warning" | "success" | "info";
  sparklineData: number[]; tooltip: string;
}

// ── Search Query ─────────────────────────────────────────────────────────

export interface SearchQuery {
  text: string;
  mode: SearchMode;
  filters: SearchFilter[];
  sortBy: "relevance" | "date" | "risk" | "name";
  page: number;
  pageSize: number;
}

export interface SearchFilter {
  id: string;
  category: FilterCategory;
  label: string;
  value: string;
  count?: number;
}

// ── Search Result ────────────────────────────────────────────────────────

export interface SearchResult {
  id: string;
  type: SearchResultType;
  title: string;
  subtitle: string;
  snippet: string;
  semanticSummary: string;
  matchExplanation: string;
  confidence: number;
  riskLevel: RiskLevel;
  highlights: SearchHighlight[];
  entities: RelatedEntity[];
  metadata: Record<string, string>;
  lastUpdated: string;
  status: string;
  url?: string;
  vectorScore?: number;
  keywordScore?: number;
  hybridScore?: number;
}

export interface SearchHighlight {
  field: string;
  text: string;
  startOffset: number;
  endOffset: number;
  type: "semantic" | "keyword" | "ai_highlight";
}

export interface RelatedEntity {
  id: string;
  type: string;
  label: string;
  relationship: string;
  riskLevel?: RiskLevel;
}

// ── AI Suggestion ────────────────────────────────────────────────────────

export interface AiSearchSuggestion {
  id: string;
  query: string;
  description: string;
  type: "refinement" | "expansion" | "related" | "exploration" | "anomaly";
  confidence: number;
  reason: string;
}

// ── Search Category ──────────────────────────────────────────────────────

export interface SearchCategory {
  id: string;
  label: string;
  icon: string;
  count: number;
  description: string;
}

// ── Saved Search ─────────────────────────────────────────────────────────

export interface SavedSearch {
  id: string;
  name: string;
  query: string;
  mode: SearchMode;
  filters: SearchFilter[];
  alertEnabled: boolean;
  lastRun: string;
  resultCount: number;
  frequency: "daily" | "weekly" | "monthly" | "never";
}

// ── Recent Search ────────────────────────────────────────────────────────

export interface RecentSearch {
  id: string;
  query: string;
  mode: SearchMode;
  timestamp: string;
  resultCount: number;
}

// ── AI Discovery Insight ─────────────────────────────────────────────────

export interface AiDiscoveryInsight {
  id: string;
  type: "relationship" | "anomaly" | "pattern" | "recommendation" | "risk" | "compliance";
  title: string;
  description: string;
  confidence: number;
  impact: "high" | "medium" | "low";
  entities: string[];
  severity: "critical" | "warning" | "info" | "success";
  suggestedQuery?: string;
}

// ── Quick Preview ────────────────────────────────────────────────────────

export interface QuickPreviewData {
  overview: {
    description: string;
    status: string;
    riskLevel: RiskLevel;
    value: string;
    counterparty: string;
    dates: { start: string; end: string; };
    businessUnit: string;
  };
  insights: AiDiscoveryInsight[];
  clauses: { id: string; title: string; riskLevel: RiskLevel; summary: string; }[];
  relationships: { entity: string; type: string; strength: number; }[];
  workflow: { stage: string; assignee: string; sla: string; status: string; }[];
  obligations: { title: string; status: string; dueDate: string; }[];
  activity: { action: string; user: string; timestamp: string; }[];
  similarResults: SearchResult[];
}

// ── Search Analytics ─────────────────────────────────────────────────────

export interface SearchAnalytics {
  totalSearches: number;
  avgLatency: number;
  semanticAccuracy: number;
  zeroResultRate: number;
  clickThroughRate: number;
  popularSearches: { query: string; count: number; trend: number; }[];
  failedSearches: { query: string; count: number; reason: string; }[];
  searchTrends: { date: string; searches: number; uniqueUsers: number; }[];
  latencyDistribution: { range: string; count: number; }[];
  categoryDistribution: { category: string; count: number; }[];
  aiRetrievalQuality: { date: string; precision: number; recall: number; }[];
}

// ── Search Session ───────────────────────────────────────────────────────

export interface SearchSession {
  id: string;
  query: SearchQuery;
  results: SearchResult[];
  totalResults: number;
  processingTime: number;
  mode: SearchMode;
  suggestions: AiSearchSuggestion[];
  insights: AiDiscoveryInsight[];
  relatedCategories: SearchCategory[];
}

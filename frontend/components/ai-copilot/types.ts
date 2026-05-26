// ── Global AI Copilot Type System ──────────────────────────────────────────

export type CopilotMode =
  | "legal_assistant" | "procurement_assistant" | "risk_analyst"
  | "negotiation_advisor" | "executive_intelligence" | "compliance_assistant"
  | "workflow_coordinator";

export type MessageRole = "user" | "assistant" | "system" | "agent";
export type MessageStatus = "streaming" | "complete" | "error" | "pending_action";
export type InsightSeverity = "critical" | "warning" | "info" | "success";

export interface CopilotContext {
  currentScreen: string;
  selectedEntityId: string | null;
  selectedEntityType: "contract" | "workflow" | "vendor" | "clause" | "benchmark" | null;
  workflowStage: string | null;
  userRole: string;
  businessUnit: string | null;
  recentActivity: string[];
  pageMetadata: Record<string, string>;
}

export interface AiMessage {
  id: string;
  role: MessageRole;
  content: string;
  agent?: string;
  timestamp: string;
  status: MessageStatus;
  citations?: AiCitation[];
  reasoning?: string;
  confidence?: number;
  suggestedActions?: AiSuggestedAction[];
  followUpSuggestions?: string[];
  metadata?: Record<string, string>;
}

export interface AiCitation {
  source: string;
  excerpt: string;
  relevance: number;
  contractId?: string;
  clauseType?: string;
}

export interface AiSuggestedAction {
  id: string;
  label: string;
  description: string;
  action: string;
  params: Record<string, string>;
  requiresConfirmation: boolean;
  icon: string;
}

export interface AiInsight {
  id: string;
  title: string;
  description: string;
  severity: InsightSeverity;
  confidence: number;
  category: string;
  sourceScreen: string;
  impactedEntities: string[];
  suggestedActions: AiSuggestedAction[];
  reasoning: string;
  citations: AiCitation[];
  dismissed: boolean;
  createdAt: string;
}

export interface AgentCapability {
  agent: string;
  label: string;
  description: string;
  icon: string;
  mode: CopilotMode;
  capabilities: string[];
  examplePrompts: string[];
}

export interface Conversation {
  id: string;
  title: string;
  messages: AiMessage[];
  mode: CopilotMode;
  context: CopilotContext;
  createdAt: string;
  updatedAt: string;
  saved: boolean;
  shared: boolean;
}

export interface AiAnalytics {
  totalQueries: number;
  avgConfidence: number;
  avgResponseTime: number;
  topAgents: { agent: string; count: number; avgRating: number }[];
  insightsGenerated: number;
  actionsExecuted: number;
  feedbackScore: number;
  hallucinationRate: number;
}

// ── Agent Configurations ────────────────────────────────────────────────────

export const AGENTS: AgentCapability[] = [
  {
    agent: "legal_risk", label: "Legal Risk Agent", description: "Analyzes contract clauses and identifies legal risks",
    icon: "Scale", mode: "legal_assistant",
    capabilities: ["Clause analysis", "Risk scoring", "Redline generation", "Obligation extraction", "Compliance checking"],
    examplePrompts: ["Analyze this indemnification clause", "What are the top risks in this contract?", "Generate redline for liability cap"],
  },
  {
    agent: "procurement_intel", label: "Procurement Agent", description: "Vendor intelligence and procurement optimization",
    icon: "ShoppingCart", mode: "procurement_assistant",
    capabilities: ["Vendor risk analysis", "Spend intelligence", "Contract benchmarking", "Negotiation support", "Supplier scoring"],
    examplePrompts: ["Compare this vendor against market benchmarks", "Analyze supplier concentration risk", "Find savings opportunities"],
  },
  {
    agent: "risk_analyst", label: "Risk Analyst Agent", description: "Portfolio-wide risk detection and analysis",
    icon: "AlertTriangle", mode: "risk_analyst",
    capabilities: ["Portfolio risk scanning", "Trend analysis", "Exposure calculation", "Risk forecasting", "Anomaly detection"],
    examplePrompts: ["Summarize top portfolio risks", "Show risk trends this quarter", "Identify emerging risk patterns"],
  },
  {
    agent: "negotiation_strategy", label: "Negotiation Advisor", description: "Strategic negotiation guidance and fallback language",
    icon: "Handshake", mode: "negotiation_advisor",
    capabilities: ["Market benchmarking", "Fallback language generation", "Leverage analysis", "Concession planning", "Strategy recommendations"],
    examplePrompts: ["What's the market standard for liability caps?", "Generate fallback indemnity language", "Assess negotiation leverage"],
  },
  {
    agent: "executive_intel", label: "Executive Intelligence", description: "Executive-level portfolio intelligence",
    icon: "TrendingUp", mode: "executive_intelligence",
    capabilities: ["Portfolio summary", "Financial exposure analysis", "Risk heatmaps", "Strategic recommendations", "KPI tracking"],
    examplePrompts: ["Executive summary of portfolio health", "Top 5 risks requiring attention", "Quarterly risk report"],
  },
  {
    agent: "compliance", label: "Compliance Agent", description: "Regulatory compliance analysis and gap detection",
    icon: "Shield", mode: "compliance_assistant",
    capabilities: ["GDPR analysis", "CCPA compliance", "HIPAA checking", "Regulatory gap detection", "Compliance reporting"],
    examplePrompts: ["Check GDPR compliance for EU contracts", "Identify compliance gaps in portfolio", "Generate compliance report"],
  },
  {
    agent: "workflow_coordinator", label: "Workflow Coordinator", description: "Workflow orchestration and optimization",
    icon: "Workflow", mode: "workflow_coordinator",
    capabilities: ["Workflow status", "Bottleneck detection", "Approval recommendations", "SLA tracking", "Automation suggestions"],
    examplePrompts: ["Show workflow bottlenecks", "Recommend approval actions", "Optimize review assignments"],
  },
];

// ── Copilot Mode Config ─────────────────────────────────────────────────────

export const COPILOT_MODES: { id: CopilotMode; label: string; icon: string; color: string; bg: string }[] = [
  { id: "legal_assistant", label: "Legal Assistant", icon: "Scale", color: "text-blue-700", bg: "bg-blue-50" },
  { id: "procurement_assistant", label: "Procurement", icon: "ShoppingCart", color: "text-teal-700", bg: "bg-teal-50" },
  { id: "risk_analyst", label: "Risk Analyst", icon: "AlertTriangle", color: "text-orange-700", bg: "bg-orange-50" },
  { id: "negotiation_advisor", label: "Negotiation", icon: "Handshake", color: "text-purple-700", bg: "bg-purple-50" },
  { id: "executive_intelligence", label: "Executive Intel", icon: "TrendingUp", color: "text-navy-700", bg: "bg-navy-50" },
  { id: "compliance_assistant", label: "Compliance", icon: "Shield", color: "text-green-700", bg: "bg-green-50" },
  { id: "workflow_coordinator", label: "Workflows", icon: "Workflow", color: "text-red-700", bg: "bg-red-50" },
];

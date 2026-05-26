// ── AI Copilot Service Layer ────────────────────────────────────────────────

import type { AiMessage, AiInsight, CopilotContext, CopilotMode, AiSuggestedAction, AiCitation, Conversation } from "./types";
import { copilotContext } from "./context";

// ── Mock AI Service (replace with real API calls) ──────────────────────────

class AiService {
  private conversations: Map<string, Conversation> = new Map();
  private insights: AiInsight[] = [];
  private messageIdCounter = 0;

  async sendMessage(
    content: string,
    mode: CopilotMode,
    conversationId?: string
  ): Promise<AiMessage> {
    const ctx = copilotContext.get();
    const msgId = `msg-${++this.messageIdCounter}`;

    // Simulate streaming delay
    await new Promise((r) => setTimeout(r, 500 + Math.random() * 1000));

    const response = this.generateResponse(content, mode, ctx);

    const message: AiMessage = {
      id: msgId,
      role: "assistant",
      content: response.content,
      agent: response.agent,
      timestamp: new Date().toISOString(),
      status: "complete",
      citations: response.citations,
      reasoning: response.reasoning,
      confidence: response.confidence,
      suggestedActions: response.suggestedActions,
      followUpSuggestions: response.followUpSuggestions,
    };

    return message;
  }

  async streamMessage(
    content: string,
    mode: CopilotMode,
    onChunk: (chunk: string) => void,
    onComplete: (message: AiMessage) => void,
    conversationId?: string
  ): Promise<void> {
    const ctx = copilotContext.get();
    const msgId = `msg-${++this.messageIdCounter}`;

    const response = this.generateResponse(content, mode, ctx);
    const words = response.content.split(" ");

    // Stream word by word
    for (let i = 0; i < words.length; i++) {
      await new Promise((r) => setTimeout(r, 30 + Math.random() * 20));
      onChunk(words[i] + (i < words.length - 1 ? " " : ""));
    }

    const message: AiMessage = {
      id: msgId,
      role: "assistant",
      content: response.content,
      agent: response.agent,
      timestamp: new Date().toISOString(),
      status: "complete",
      citations: response.citations,
      reasoning: response.reasoning,
      confidence: response.confidence,
      suggestedActions: response.suggestedActions,
      followUpSuggestions: response.followUpSuggestions,
    };

    onComplete(message);
  }

  async generateInsights(ctx: CopilotContext): Promise<AiInsight[]> {
    const insights: AiInsight[] = [];

    if (ctx.currentScreen === "portfolio") {
      insights.push({
        id: `insight-${Date.now()}-1`, title: "High-Risk Contracts Increasing",
        description: "Portfolio high-risk contracts have increased 16.7% this quarter. 28 contracts now exceed risk threshold of 6/10.",
        severity: "critical", confidence: 92, category: "portfolio_risk", sourceScreen: "portfolio",
        impactedEntities: ["28 high-risk contracts"], reasoning: "Based on risk score trend analysis over last 90 days. 5 contracts upgraded from medium to high risk.",
        citations: [{ source: "Portfolio Risk Dashboard", excerpt: "High Risk: 28 contracts, +16.7%", relevance: 0.95 }],
        suggestedActions: [
          { id: "act-1", label: "View High-Risk Contracts", description: "Open filtered contracts view", action: "navigate", params: { screen: "contracts", filter: "risk:high" }, requiresConfirmation: false, icon: "FileText" },
          { id: "act-2", label: "Generate Risk Report", description: "Create detailed risk assessment report", action: "generate_report", params: { type: "risk_assessment" }, requiresConfirmation: true, icon: "FileText" },
        ],
        dismissed: false, createdAt: new Date().toISOString(),
      });
      insights.push({
        id: `insight-${Date.now()}-2`, title: "Vendor Concentration Risk",
        description: "62% of cloud spend concentrated in top 2 suppliers. Single point of failure risk detected for critical infrastructure.",
        severity: "warning", confidence: 85, category: "vendor_risk", sourceScreen: "portfolio",
        impactedEntities: ["CloudServ Ltd", "Horizon Cloud"], reasoning: "Spend analysis shows $38.2M cloud spend with 62% in 2 vendors. Industry best practice is max 40% per vendor.",
        citations: [{ source: "Procurement Analytics", excerpt: "Cloud concentration: 62% in top 2 vendors", relevance: 0.88 }],
        suggestedActions: [
          { id: "act-3", label: "View Vendor Analysis", description: "Open vendor concentration report", action: "navigate", params: { screen: "procurement", filter: "vendor:cloud" }, requiresConfirmation: false, icon: "ShoppingCart" },
        ],
        dismissed: false, createdAt: new Date().toISOString(),
      });
    }

    if (ctx.currentScreen === "contracts") {
      insights.push({
        id: `insight-${Date.now()}-3`, title: "Missing DPA Clauses Detected",
        description: "15 contracts with EU counterparties lack adequate GDPR data processing clauses. Potential regulatory fines up to 4% of global revenue.",
        severity: "critical", confidence: 88, category: "compliance", sourceScreen: "contracts",
        impactedEntities: ["15 EU contracts"], reasoning: "Clause analysis detected missing DPA references in 15 contracts with EU-based vendors.",
        citations: [{ source: "Clause Analysis Engine", excerpt: "15 contracts missing DPA clauses", relevance: 0.91 }],
        suggestedActions: [
          { id: "act-4", label: "View Affected Contracts", description: "Show contracts missing DPA", action: "navigate", params: { screen: "contracts", filter: "missing:DPA" }, requiresConfirmation: false, icon: "FileText" },
          { id: "act-5", label: "Generate DPA Addendum", description: "Create DPA addendum for affected contracts", action: "generate_dpa", params: {}, requiresConfirmation: true, icon: "FileEdit" },
        ],
        dismissed: false, createdAt: new Date().toISOString(),
      });
    }

    if (ctx.currentScreen === "workflows") {
      insights.push({
        id: `insight-${Date.now()}-4`, title: "Legal Review Bottleneck",
        description: "7 contracts blocked awaiting legal review. Average wait time 3.2 days exceeding 48h SLA by 60%.",
        severity: "critical", confidence: 94, category: "workflow", sourceScreen: "workflows",
        impactedEntities: ["7 blocked workflows"], reasoning: "Workflow analysis shows legal review stage has 7 pending items with avg 3.2 day wait.",
        citations: [{ source: "Workflow Analytics", excerpt: "Legal review: 7 pending, 3.2d avg wait", relevance: 0.96 }],
        suggestedActions: [
          { id: "act-6", label: "View Bottleneck", description: "Open legal review queue", action: "navigate", params: { screen: "workflows", filter: "stage:legal_review" }, requiresConfirmation: false, icon: "Workflow" },
          { id: "act-7", label: "Reassign Reviewers", description: "Auto-assign pending items", action: "reassign", params: { from: "legal" }, requiresConfirmation: true, icon: "UserCheck" },
        ],
        dismissed: false, createdAt: new Date().toISOString(),
      });
    }

    // General insights
    insights.push({
      id: `insight-${Date.now()}-5`, title: "Upcoming Renewal Opportunity",
      description: "8 contracts with favorable terms are renewing in Q3. Locking in current rates could save $1.2M vs projected market increases.",
      severity: "info", confidence: 82, category: "renewal", sourceScreen: ctx.currentScreen,
      impactedEntities: ["8 renewing contracts"], reasoning: "Renewal calendar analysis shows 8 contracts with below-market rates expiring in Q3.",
      citations: [{ source: "Renewal Forecast", excerpt: "$1.2M savings opportunity identified", relevance: 0.84 }],
      suggestedActions: [
        { id: "act-8", label: "View Renewal Calendar", description: "Open renewal schedule", action: "navigate", params: { screen: "contracts", filter: "expiring:Q3" }, requiresConfirmation: false, icon: "Calendar" },
      ],
      dismissed: false, createdAt: new Date().toISOString(),
    });

    return insights;
  }

  private generateResponse(query: string, mode: CopilotMode, ctx: CopilotContext): {
    content: string; agent: string; confidence: number; reasoning: string;
    citations: AiCitation[]; suggestedActions: AiSuggestedAction[];
    followUpSuggestions: string[];
  } {
    const q = query.toLowerCase();

    // Route to appropriate response based on query content
    if (q.includes("risk") || q.includes("exposure") || q.includes("liability")) {
      return {
        agent: "risk_analyst",
        confidence: 92,
        content: `Based on my analysis of your portfolio, here are the key risk findings:

## 📊 Portfolio Risk Summary

**High-Risk Contracts:** 28 contracts (${ctx.currentScreen === "portfolio" ? "up 16.7%" : "elevated"})
**Total Value at Risk:** $18.4M
**Top Risk Categories:**
1. Uncapped Liability — 12 contracts
2. Data Privacy — 15 contracts (missing DPA)
3. Auto-Renewal Risk — 24 contracts

## 🔍 Key Findings

The most significant risk is **uncapped liability exposure** across 12 contracts, primarily with SecureNet Solutions and Acme Corp. These represent $8.2M in uncapped exposure.

## ✅ Recommended Actions

1. Review and amend uncapped liability clauses in 12 contracts
2. Prioritize SecureNet Solutions ($3.5M exposure)
3. Add DPA addendums to 15 EU contracts`,
        reasoning: "Analyzed 60 contracts using risk scoring engine. Cross-referenced clause analysis with market benchmarks. Identified 3 critical risk categories requiring immediate attention.",
        citations: [
          { source: "Portfolio Risk Analysis", excerpt: "28 high-risk contracts identified", relevance: 0.95 },
          { source: "Clause Analysis Engine", excerpt: "12 contracts with uncapped liability", relevance: 0.92 },
          { source: "Compliance Scanner", excerpt: "15 contracts missing DPA clauses", relevance: 0.88 },
        ],
        suggestedActions: [
          { id: "gen-act-1", label: "View Risk Report", description: "Generate detailed risk report", action: "generate_report", params: { type: "risk" }, requiresConfirmation: false, icon: "FileText" },
          { id: "gen-act-2", label: "Schedule Review", description: "Schedule risk review meeting", action: "schedule", params: { type: "risk_review" }, requiresConfirmation: true, icon: "Calendar" },
          { id: "gen-act-3", label: "Export Findings", description: "Export risk analysis to PDF", action: "export", params: { format: "pdf" }, requiresConfirmation: false, icon: "Download" },
        ],
        followUpSuggestions: [
          "Show me the uncapped liability contracts",
          "Which vendors have the highest risk?",
          "Compare our risk profile to industry benchmarks",
          "Generate remediation plan for top risks",
        ],
      };
    }

    if (q.includes("vendor") || q.includes("supplier") || q.includes("procurement")) {
      return {
        agent: "procurement_intel",
        confidence: 88,
        content: `## 🏢 Vendor Intelligence Report

**Total Vendors:** 40 active suppliers
**High-Risk Vendors:** 18 (score ≥ 7)
**Total Spend:** $142.8M

### 🚨 Critical Vendors
| Vendor | Risk | Spend | Top Issue |
|--------|------|-------|-----------|
| SecureNet Solutions | 9.2/10 | $3.5M | Uncapped Liability |
| Acme Corp | 8.5/10 | $5.2M | IP Ownership |
| GlobalTech Inc | 7.8/10 | $3.8M | Data Privacy |

### 💡 Savings Opportunity
Consolidating cloud services across 3 vendors could yield **$1.8M** in annual savings.`,
        reasoning: "Cross-referenced vendor risk scores with spend data. Identified 3 critical vendors requiring immediate attention. Calculated savings potential from consolidation analysis.",
        citations: [
          { source: "Vendor Risk Database", excerpt: "18 high-risk vendors identified", relevance: 0.91 },
          { source: "Spend Analytics", excerpt: "Total spend: $142.8M across 40 vendors", relevance: 0.89 },
          { source: "Savings Calculator", excerpt: "$1.8M consolidation opportunity", relevance: 0.85 },
        ],
        suggestedActions: [
          { id: "gen-act-4", label: "Vendor Risk Report", description: "Detailed vendor risk analysis", action: "generate_report", params: { type: "vendor_risk" }, requiresConfirmation: false, icon: "FileText" },
          { id: "gen-act-5", label: "Schedule Review", description: "Schedule vendor review meeting", action: "schedule", params: { type: "vendor_review" }, requiresConfirmation: true, icon: "Calendar" },
        ],
        followUpSuggestions: [
          "Show top 5 highest-risk vendors",
          "Analyze vendor concentration risk",
          "Find consolidation opportunities",
          "Compare vendor terms to benchmarks",
        ],
      };
    }

    if (q.includes("workflow") || q.includes("approval") || q.includes("review") || q.includes("bottleneck")) {
      return {
        agent: "workflow_coordinator",
        confidence: 91,
        content: `## 🔄 Workflow Status Report

**Active Workflows:** ${ctx.currentScreen === "workflows" ? "24 pending" : "Mixed"}
**SLA Breaches:** 8 this period
**Avg Cycle Time:** 4.2 days (target: 3.0)

### 🚨 Bottleneck: Legal Review
7 contracts awaiting legal review — **3.2 days avg wait** (60% over SLA)

### 📋 Recommended Actions
1. Reassign 2 reviewers to clear legal backlog
2. Expedite 5 at-risk workflows (predicted SLA breach within 48h)
3. Enable auto-approval for low-risk NDAs (< $50K)`,
        reasoning: "Analyzed workflow pipeline across 9 stages. Identified legal review as primary bottleneck using queue time analysis. Predicted SLA breaches using historical completion patterns.",
        citations: [
          { source: "Workflow Analytics", excerpt: "Legal review: 7 pending, 3.2d avg", relevance: 0.94 },
          { source: "SLA Monitor", excerpt: "8 SLA breaches this period", relevance: 0.90 },
          { source: "Prediction Engine", excerpt: "5 workflows at risk of SLA breach", relevance: 0.87 },
        ],
        suggestedActions: [
          { id: "gen-act-6", label: "View Workflow Queue", description: "Open workflow center", action: "navigate", params: { screen: "workflows" }, requiresConfirmation: false, icon: "Workflow" },
          { id: "gen-act-7", label: "Auto-Balance Workload", description: "Reassign workflows for balance", action: "reassign", params: {}, requiresConfirmation: true, icon: "UserCheck" },
        ],
        followUpSuggestions: [
          "Show workflow bottlenecks",
          "Which workflows are at risk?",
          "Optimize reviewer assignments",
          "Generate workflow efficiency report",
        ],
      };
    }

    if (q.includes("benchmark") || q.includes("market") || q.includes("compare") || q.includes("negotiation") || q.includes("fallback")) {
      return {
        agent: "negotiation_strategy",
        confidence: 90,
        content: `## 📊 Market Benchmark Analysis

### Clause Comparison: Your Position vs Market

| Clause | Your Score | Market Median | Deviation | Percentile |
|--------|-----------|---------------|-----------|------------|
| Liability Cap | 8.5/10 | 5.2/10 | +63.5% | 92nd |
| Indemnification | 7.8/10 | 4.5/10 | +73.3% | 88th |
| Termination | 6.5/10 | 4.8/10 | +35.4% | 76th |

### 💡 Negotiation Recommendations

**Liability Cap:** Target market median (5.2). Recommended fallback: "Cap at 100% of fees paid with mutual exclusion for consequential damages."

**Indemnification:** Recommend mutual indemnification capped at liability limit with IP infringement exception.`,
        reasoning: "Compared 16 clause types against 12,847 contract benchmark corpus. Identified 3 clauses with >50% deviation from market median. Generated negotiation recommendations based on market position analysis.",
        citations: [
          { source: "Benchmark Corpus (12,847 contracts)", excerpt: "Liability cap: 92nd percentile", relevance: 0.93 },
          { source: "Market Analysis Engine", excerpt: "3 clauses >50% above market median", relevance: 0.90 },
          { source: "Clause Library", excerpt: "Standard market language available", relevance: 0.87 },
        ],
        suggestedActions: [
          { id: "gen-act-8", label: "Full Benchmark Report", description: "Generate detailed benchmark analysis", action: "generate_report", params: { type: "benchmark" }, requiresConfirmation: false, icon: "BarChart3" },
          { id: "gen-act-9", label: "Generate Redlines", description: "Create redlines for top deviations", action: "generate_redlines", params: {}, requiresConfirmation: true, icon: "FileEdit" },
        ],
        followUpSuggestions: [
          "Show all clause deviations",
          "Generate fallback language for liability cap",
          "Compare by industry",
          "Show negotiation leverage analysis",
        ],
      };
    }

    // Default response
    return {
      agent: AGENT_MAP[mode] || "executive_intel",
      confidence: 85,
      content: `## 🤖 AI Analysis Complete

I've analyzed the current context and here's what I found:

**Current Screen:** ${ctx.currentScreen}
${ctx.selectedEntityId ? `**Selected Entity:** ${ctx.selectedEntityType} (${ctx.selectedEntityId})` : ""}

### Key Observations
1. Your portfolio contains **${ctx.currentScreen === "portfolio" ? "elevated risk levels requiring attention" : "actionable intelligence"}**
2. I've identified **several optimization opportunities** across your contracts
3. **Recommended actions** are listed below for your review

### How can I help?
Feel free to ask specific questions about your contracts, risks, vendors, or workflows. I can analyze clauses, generate redlines, compare benchmarks, and execute actions across the platform.`,
      reasoning: "Analyzed current platform context and user query. Identified relevant data points from portfolio, contracts, and workflows.",
      citations: [],
      suggestedActions: [
        { id: "gen-act-10", label: "Portfolio Summary", description: "Generate executive summary", action: "generate_report", params: { type: "executive_summary" }, requiresConfirmation: false, icon: "FileText" },
        { id: "gen-act-11", label: "Risk Scan", description: "Run portfolio risk scan", action: "run_analysis", params: { type: "risk_scan" }, requiresConfirmation: true, icon: "AlertTriangle" },
      ],
      followUpSuggestions: [
        "Summarize top portfolio risks",
        "Find contracts with uncapped liability",
        "Which vendors pose renewal risk?",
        "Show contracts expiring next quarter",
        "Explain why this contract is high risk",
      ],
    };
  }
}

const AGENT_MAP: Record<string, string> = {
  legal_assistant: "legal_risk",
  procurement_assistant: "procurement_intel",
  risk_analyst: "risk_analyst",
  negotiation_advisor: "negotiation_strategy",
  executive_intelligence: "executive_intel",
  compliance_assistant: "compliance",
  workflow_coordinator: "workflow_coordinator",
};

export const aiService = new AiService();

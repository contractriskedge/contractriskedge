// ── Enterprise Workflow Center Mock Data ────────────────────────────────────

import type { WorkflowKpi, WorkflowItem, WorkflowInsight, SlaMetric, AutomationRule, TeamMember } from "./types";
import { STAGE_ORDER } from "./types";

function rand(min: number, max: number) { return Math.floor(Math.random() * (max - min + 1)) + min; }
function pick<T>(arr: T[]): T { return arr[rand(0, arr.length - 1)]; }

const vendors = ["Acme Corp", "GlobalTech Inc", "DataSync Partners", "CloudServ Ltd", "SecureNet Solutions", "InnoVate LLC", "Pacific Rim Trading", "EuroLegal Partners", "NovaTech Systems", "Quantum Labs"];
const owners = ["Alice Chen", "Bob Martinez", "Carol Singh", "David Kim", "Eve Johnson", "Frank Wilson", "Grace Lee", "Henry Park"];
const contractTypes = ["MSA", "SOW", "NDA", "License", "Service Agreement", "Partnership", "SaaS Agreement", "Consulting"];
const departments = ["Engineering", "Marketing", "Finance", "Operations", "Sales", "Legal", "HR", "IT"];
const geographies = ["North America", "EMEA", "APAC", "LATAM"];
const actions = ["Uploaded contract", "Completed AI review", "Added comments", "Requested changes", "Approved stage", "Escalated review", "Assigned reviewer", "Rejected with comments"];

// ── KPI Metrics ─────────────────────────────────────────────────────────────

export const workflowKpis: WorkflowKpi[] = [
  { id: "pending-approvals", label: "Pending Approvals", value: "24", trend: 14.3, trendDirection: "up", icon: "Clock", color: "from-amber-500 to-yellow-500", severity: "warning", sparklineData: [18, 19, 20, 21, 22, 22, 23, 24], tooltip: "Workflows awaiting approval action" },
  { id: "overdue-tasks", label: "Overdue Tasks", value: "11", trend: -15.4, trendDirection: "down", icon: "AlertTriangle", color: "from-red-500 to-orange-500", severity: "critical", sparklineData: [16, 15, 14, 14, 13, 12, 12, 11], tooltip: "Workflows past their SLA deadline" },
  { id: "sla-breaches", label: "SLA Breaches", value: "8", trend: -27.3, trendDirection: "down", icon: "AlertOctagon", color: "from-red-500 to-rose-500", severity: "critical", sparklineData: [14, 13, 12, 11, 10, 9, 9, 8], tooltip: "SLA breaches in current period" },
  { id: "escalated", label: "Escalated Reviews", value: "6", trend: 20.0, trendDirection: "up", icon: "ArrowUpCircle", color: "from-purple-500 to-pink-500", severity: "warning", sparklineData: [4, 4, 5, 5, 5, 5, 6, 6], tooltip: "Workflows escalated for higher-level review" },
  { id: "completion-rate", label: "Completion Rate", value: "87%", trend: 4.8, trendDirection: "up", icon: "CheckCircle", color: "from-green-500 to-emerald-500", severity: "success", sparklineData: [78, 80, 81, 82, 83, 85, 86, 87], tooltip: "Percentage of workflows completed within SLA" },
  { id: "cycle-time", label: "Avg Cycle Time", value: "4.2d", trend: -12.5, trendDirection: "down", icon: "Zap", color: "from-blue-500 to-cyan-500", severity: "success", sparklineData: [5.8, 5.5, 5.2, 5.0, 4.8, 4.5, 4.3, 4.2], tooltip: "Average days from intake to completion" },
  { id: "blocked", label: "Blocked Contracts", value: "9", trend: 28.6, trendDirection: "up", icon: "Ban", color: "from-red-500 to-orange-500", severity: "critical", sparklineData: [5, 6, 6, 7, 7, 8, 8, 9], tooltip: "Contracts blocked awaiting resolution" },
  { id: "automation-rate", label: "Automation Rate", value: "72%", trend: 8.5, trendDirection: "up", icon: "Bot", color: "from-indigo-500 to-purple-500", severity: "success", sparklineData: [58, 61, 63, 65, 67, 69, 71, 72], tooltip: "Percentage of workflows with automated actions" },
];

// ── Generate 36 workflow items ──────────────────────────────────────────────

export const workflowItems: WorkflowItem[] = Array.from({ length: 36 }, (_, i) => {
  const stageIdx = rand(0, STAGE_ORDER.length - 2); // exclude completed
  const stage = STAGE_ORDER[stageIdx];
  const priority = pick(["critical", "high", "medium", "low"] as const);
  const riskScore = rand(2, 10);
  const riskLevel = riskScore >= 8 ? "critical" : riskScore >= 6 ? "high" : riskScore >= 4 ? "medium" : "low";
  const slaHours = stageIdx <= 1 ? 24 : stageIdx <= 3 ? 48 : stageIdx <= 5 ? 72 : 120;
  const slaRemaining = rand(-12, slaHours);
  const vendor = pick(vendors);
  const ct = pick(contractTypes);

  return {
    id: `WF-${2026001 + i}`,
    contractName: `${ct} - ${vendor}`,
    vendor,
    contractType: ct,
    currentStage: stage,
    assignedTo: pick(owners),
    priority,
    slaRemaining,
    riskLevel,
    riskScore,
    status: slaRemaining < 0 ? "escalated" : pick(["active", "on_hold", "active", "active"]),
    lastAction: pick(actions),
    lastActionBy: pick(owners),
    lastActionDate: new Date(Date.now() - rand(0, 72) * 3600000).toISOString(),
    dueDate: new Date(Date.now() + slaRemaining * 3600000).toISOString(),
    escalationLevel: slaRemaining < 0 ? rand(1, 3) : 0,
    aiRecommendation: pick([
      "Auto-approve — low risk NDA",
      "Route to legal — high risk detected",
      "Expedite — SLA critical",
      "Standard review path",
      "Flag for executive approval",
      "Return for clarification",
    ]),
    aiConfidence: rand(72, 98),
    comments: i % 3 === 0 ? [
      { id: `c-${i}-1`, author: pick(owners), body: "Please review the liability cap in Section 4.2.", mentions: [], createdAt: new Date(Date.now() - rand(1, 48) * 3600000).toISOString(), resolved: false },
      { id: `c-${i}-2`, author: pick(owners), body: "Insurance certificates need renewal before approval.", mentions: ["Alice Chen"], createdAt: new Date(Date.now() - rand(1, 24) * 3600000).toISOString(), resolved: true },
    ] : [],
    attachments: rand(0, 5),
    value: +(rand(5, 5000) / 100).toFixed(1),
    department: pick(departments),
    geography: pick(geographies),
    createdAt: new Date(Date.now() - rand(24, 720) * 3600000).toISOString(),
  };
});

// ── Workflow Insights ───────────────────────────────────────────────────────

export const workflowInsights: WorkflowInsight[] = [
  { id: "wi-1", title: "Legal Review Bottleneck Detected", description: "7 contracts are blocked awaiting legal review. Average wait time is 3.2 days — exceeding the 48-hour SLA by 60%.", severity: "critical", confidence: 94, impactedWorkflows: ["WF-2026003", "WF-2026007", "WF-2026011", "WF-2026015", "WF-2026019", "WF-2026023", "WF-2026027"], suggestedAction: "Reassign 2 legal reviewers from completed workflows to clear backlog.", category: "bottleneck", quickActions: [{ label: "View Queue", action: "view" }, { label: "Reassign", action: "reassign" }] },
  { id: "wi-2", title: "Approval Cycle Time Exceeds Target", description: "Average approval cycle time is 4.2 days vs target of 3.0 days — 40% above target. Finance approval is the slowest stage.", severity: "warning", confidence: 88, impactedWorkflows: ["WF-2026002", "WF-2026006", "WF-2026010", "WF-2026014"], suggestedAction: "Implement auto-approval for contracts under $100K to reduce finance bottleneck.", category: "cycle_time", quickActions: [{ label: "Cycle Analysis", action: "analysis" }, { label: "Auto-Approval Rules", action: "rules" }] },
  { id: "wi-3", title: "SLA Breach Predicted for 5 Workflows", description: "AI predicts 5 active workflows will breach SLA within 48 hours if not expedited. Critical path: Legal → Finance.", severity: "critical", confidence: 91, impactedWorkflows: ["WF-2026005", "WF-2026009", "WF-2026013", "WF-2026017", "WF-2026021"], suggestedAction: "Expedite 5 at-risk workflows. Consider parallel review for Legal and Finance stages.", category: "sla", quickActions: [{ label: "View At-Risk", action: "view" }, { label: "Expedite All", action: "expedite" }] },
  { id: "wi-4", title: "Finance Approval Bottleneck", description: "Finance stage has 8 pending workflows with average wait of 2.8 days. 3 are critical priority from SecureNet Solutions.", severity: "warning", confidence: 86, impactedWorkflows: ["WF-2026004", "WF-2026008", "WF-2026012", "WF-2026016", "WF-2026020", "WF-2026024", "WF-2026028", "WF-2026032"], suggestedAction: "Temporarily assign additional finance reviewer. Prioritize SecureNet Solutions contracts.", category: "bottleneck", quickActions: [{ label: "Finance Queue", action: "queue" }, { label: "Reassign", action: "reassign" }] },
  { id: "wi-5", title: "Automation Opportunity: Low-Risk NDAs", description: "12 low-risk NDAs processed this quarter could have been auto-approved, saving 18 person-hours. Estimated 85% automation potential.", severity: "success", confidence: 82, impactedWorkflows: ["WF-2026001", "WF-2026018", "WF-2026025"], suggestedAction: "Enable auto-approval rule for NDAs with risk score < 4 and value < $50K.", category: "automation", quickActions: [{ label: "Configure Rule", action: "configure" }, { label: "Impact Report", action: "report" }] },
  { id: "wi-6", title: "Workload Balancing Recommended", description: "Carol Singh has 9 active workflows (highest). Bob Martinez has 2 (lowest). Rebalancing could improve overall cycle time by 18%.", severity: "info", confidence: 78, impactedWorkflows: ["WF-2026003", "WF-2026007", "WF-2026011", "WF-2026015", "WF-2026019", "WF-2026023", "WF-2026027", "WF-2026031", "WF-2026035"], suggestedAction: "Reassign 3 workflows from Carol Singh to Bob Martinez for workload balancing.", category: "workload", quickActions: [{ label: "Workload View", action: "view" }, { label: "Auto-Balance", action: "balance" }] },
];

// ── SLA Metrics ─────────────────────────────────────────────────────────────

export const slaMetrics: SlaMetric[] = [
  { stage: "intake", targetHours: 4, actualHours: 3.2, breachCount: 2, breachRate: 5.6, trend: -12 },
  { stage: "ai_review", targetHours: 2, actualHours: 1.5, breachCount: 1, breachRate: 2.8, trend: -25 },
  { stage: "legal_review", targetHours: 48, actualHours: 62.5, breachCount: 18, breachRate: 22.5, trend: 15 },
  { stage: "procurement_review", targetHours: 24, actualHours: 28.0, breachCount: 8, breachRate: 11.1, trend: 8 },
  { stage: "security_review", targetHours: 24, actualHours: 20.5, breachCount: 4, breachRate: 5.6, trend: -10 },
  { stage: "finance_approval", targetHours: 48, actualHours: 58.0, breachCount: 14, breachRate: 19.4, trend: 12 },
  { stage: "executive_approval", targetHours: 72, actualHours: 48.0, breachCount: 3, breachRate: 4.2, trend: -20 },
  { stage: "signature", targetHours: 24, actualHours: 18.0, breachCount: 2, breachRate: 2.8, trend: -15 },
];

// ── Automation Rules ────────────────────────────────────────────────────────

export const automationRules: AutomationRule[] = [
  { id: "ar-1", name: "Auto-route High Risk to Legal", description: "Contracts with risk score ≥ 7 are automatically routed to Legal Review", trigger: "Risk score ≥ 7 on AI review completion", action: "Route to legal_review stage", enabled: true, priority: 1, successRate: 98, executions: 342 },
  { id: "ar-2", name: "Escalate SLA Breach After 48h", description: "Workflows exceeding SLA by 48 hours are auto-escalated to manager", trigger: "SLA remaining < -48 hours", action: "Set escalation level +1, notify manager", enabled: true, priority: 2, successRate: 95, executions: 87 },
  { id: "ar-3", name: "Auto-approve Low-Risk NDAs", description: "NDAs with risk score < 4 and value < $50K are auto-approved", trigger: "Contract type = NDA AND risk < 4 AND value < $50K", action: "Skip to signature stage", enabled: false, priority: 3, successRate: 100, executions: 0 },
  { id: "ar-4", name: "Route DPAs to Compliance", description: "Contracts requiring DPA are auto-routed to Compliance team", trigger: "Missing DPA clause detected", action: "Route to compliance_review stage", enabled: true, priority: 4, successRate: 97, executions: 156 },
  { id: "ar-5", name: "Notify on Critical Priority", description: "Critical priority workflows trigger immediate notification to all reviewers", trigger: "Priority = critical on intake", action: "Send notification to assignedTo + manager", enabled: true, priority: 5, successRate: 100, executions: 234 },
  { id: "ar-6", name: "Auto-Assign Based on Workload", description: "New workflows are assigned to the reviewer with lowest active count", trigger: "New workflow created", action: "Assign to team member with least active workflows", enabled: false, priority: 6, successRate: 92, executions: 0 },
];

// ── Team Members ────────────────────────────────────────────────────────────

export const teamMembers: TeamMember[] = [
  { id: "tm-1", name: "Alice Chen", role: "Senior Counsel", avatar: "AC", activeWorkflows: 5, completedToday: 3, avgCompletionTime: 3.8, online: true },
  { id: "tm-2", name: "Bob Martinez", role: "Contract Analyst", avatar: "BM", activeWorkflows: 2, completedToday: 5, avgCompletionTime: 2.5, online: true },
  { id: "tm-3", name: "Carol Singh", role: "VP Legal", avatar: "CS", activeWorkflows: 9, completedToday: 1, avgCompletionTime: 5.2, online: true },
  { id: "tm-4", name: "David Kim", role: "Compliance Officer", avatar: "DK", activeWorkflows: 4, completedToday: 2, avgCompletionTime: 4.1, online: false },
  { id: "tm-5", name: "Eve Johnson", role: "Paralegal", avatar: "EJ", activeWorkflows: 6, completedToday: 4, avgCompletionTime: 2.8, online: true },
  { id: "tm-6", name: "Frank Wilson", role: "Procurement Manager", avatar: "FW", activeWorkflows: 3, completedToday: 3, avgCompletionTime: 3.5, online: true },
  { id: "tm-7", name: "Grace Lee", role: "Finance Approver", avatar: "GL", activeWorkflows: 7, completedToday: 2, avgCompletionTime: 4.5, online: true },
  { id: "tm-8", name: "Henry Park", role: "Security Analyst", avatar: "HP", activeWorkflows: 3, completedToday: 4, avgCompletionTime: 3.0, online: false },
];

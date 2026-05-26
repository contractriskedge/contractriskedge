// ── Enterprise Admin Mock Data ──────────────────────────────────────────────

import type { AdminKpi, AdminUser, RoleDefinition, AiGovernanceEvent, AuditEvent, SystemHealthMetric, Integration, ComplianceCheck, SecurityAlert, TenantConfig } from "./types";

function rand(min: number, max: number) { return Math.floor(Math.random() * (max - min + 1)) + min; }
function pick<T>(arr: T[]): T { return arr[rand(0, arr.length - 1)]; }

// ── KPI Metrics ─────────────────────────────────────────────────────────────

export const adminKpis: AdminKpi[] = [
  { id: "active-users", label: "Active Users", value: "847", trend: 12.3, trendDirection: "up", icon: "Users", color: "from-blue-500 to-indigo-500", severity: "info", sparklineData: [620, 650, 690, 720, 750, 780, 810, 847], tooltip: "Active users in the current period" },
  { id: "security-alerts", label: "Security Alerts", value: "14", trend: -22.2, trendDirection: "down", icon: "Shield", color: "from-red-500 to-orange-500", severity: "critical", sparklineData: [22, 20, 19, 18, 17, 16, 15, 14], tooltip: "Open security alerts requiring attention" },
  { id: "ai-violations", label: "AI Policy Violations", value: "8", trend: 33.3, trendDirection: "up", icon: "Brain", color: "from-purple-500 to-pink-500", severity: "high", sparklineData: [4, 5, 5, 6, 6, 7, 7, 8], tooltip: "AI governance policy violations detected" },
  { id: "failed-logins", label: "Failed Logins (24h)", value: "23", trend: -8.0, trendDirection: "down", icon: "Lock", color: "from-amber-500 to-yellow-500", severity: "warning", sparklineData: [31, 29, 28, 27, 26, 25, 24, 23], tooltip: "Failed login attempts in the last 24 hours" },
  { id: "integrations", label: "Active Integrations", value: "18", trend: 5.9, trendDirection: "up", icon: "Link", color: "from-teal-500 to-green-500", severity: "success", sparklineData: [14, 15, 15, 16, 16, 17, 17, 18], tooltip: "Active platform integrations" },
  { id: "system-health", label: "System Health", value: "98.7%", trend: 0.5, trendDirection: "up", icon: "Activity", color: "from-green-500 to-emerald-500", severity: "success", sparklineData: [97.2, 97.5, 97.8, 98.0, 98.2, 98.4, 98.5, 98.7], tooltip: "Overall system uptime percentage" },
  { id: "audit-events", label: "Audit Events Today", value: "1,247", trend: 8.1, trendDirection: "up", icon: "FileSearch", color: "from-navy-600 to-navy-800", severity: "info", sparklineData: [890, 950, 1020, 1080, 1120, 1180, 1200, 1247], tooltip: "Audit events recorded today" },
  { id: "compliance-score", label: "Compliance Score", value: "92%", trend: 3.4, trendDirection: "up", icon: "ShieldCheck", color: "from-green-500 to-teal-500", severity: "success", sparklineData: [84, 86, 87, 88, 89, 90, 91, 92], tooltip: "Overall tenant compliance score" },
];

// ── Users ───────────────────────────────────────────────────────────────────

const roles = ["Admin", "Legal Counsel", "Contract Analyst", "Procurement Manager", "Compliance Officer", "Viewer"];
const departments = ["Legal", "Procurement", "Finance", "Operations", "Compliance", "IT", "Sales", "Engineering"];
const groups = ["Contract-Admins", "Legal-Team", "Procurement-Team", "Compliance-Team", "Finance-Approvers", "Executive-Reviewers"];

export const adminUsers: AdminUser[] = Array.from({ length: 24 }, (_, i) => ({
  id: `USR-${2026001 + i}`, name: pick(["Alice Chen", "Bob Martinez", "Carol Singh", "David Kim", "Eve Johnson", "Frank Wilson", "Grace Lee", "Henry Park", "Iris Zhang", "Jack Thompson", "Karen Davis", "Leo Garcia", "Maria Rodriguez", "Nathan Brown", "Olivia Taylor", "Peter Anderson", "Quinn Mitchell", "Rachel White", "Sam Patel", "Tina Jackson", "Uma Sharma", "Victor Nguyen", "Wendy Cooper", "Xander Brooks"]),
  email: `user${i + 1}@company.com`, role: pick(roles), status: pick(["active", "active", "active", "inactive", "suspended"]),
  lastActive: new Date(Date.now() - rand(0, 168) * 3600000).toISOString(),
  mfaEnabled: Math.random() > 0.3, ssoConnected: Math.random() > 0.4,
  department: pick(departments), groups: [pick(groups), pick(groups)].filter((v, idx, a) => a.indexOf(v) === idx),
  permissions: ["contracts.read", "contracts.write", "risks.read", "workflows.read"].slice(0, rand(1, 4)),
  created: new Date(Date.now() - rand(30, 730) * 86400000).toISOString(),
  loginCount: rand(10, 500), lastIp: `192.168.${rand(1, 255)}.${rand(1, 255)}`,
}));

// ── Roles ───────────────────────────────────────────────────────────────────

export const roleDefinitions: RoleDefinition[] = [
  { id: "role-1", name: "Super Admin", description: "Full platform access with all permissions", permissions: ["*"], userCount: 3, isSystem: true, inheritance: [] },
  { id: "role-2", name: "Legal Counsel", description: "Contract review, redlining, and legal analysis", permissions: ["contracts.read", "contracts.write", "risks.read", "risks.write", "redlines.read", "redlines.write", "workflows.read"], userCount: 12, isSystem: true, inheritance: ["contracts.read"] },
  { id: "role-3", name: "Contract Analyst", description: "Contract analysis, risk assessment, and reporting", permissions: ["contracts.read", "risks.read", "benchmarks.read", "reports.read"], userCount: 28, isSystem: true, inheritance: ["contracts.read"] },
  { id: "role-4", name: "Procurement Manager", description: "Vendor management, procurement workflows", permissions: ["contracts.read", "contracts.write", "vendors.read", "vendors.write", "workflows.read", "workflows.write"], userCount: 8, isSystem: true, inheritance: ["contracts.read"] },
  { id: "role-5", name: "Compliance Officer", description: "Compliance monitoring, audit access", permissions: ["contracts.read", "compliance.read", "compliance.write", "audit.read", "reports.read"], userCount: 5, isSystem: true, inheritance: ["contracts.read"] },
  { id: "role-6", name: "Viewer", description: "Read-only access to assigned contracts", permissions: ["contracts.read"], userCount: 45, isSystem: true, inheritance: [] },
];

// ── AI Governance Events ────────────────────────────────────────────────────

export const aiGovernanceEvents: AiGovernanceEvent[] = Array.from({ length: 20 }, (_, i) => ({
  id: `AIE-${2026001 + i}`, timestamp: new Date(Date.now() - rand(0, 72) * 3600000).toISOString(),
  model: pick(["gpt-4o", "claude-3.5-sonnet", "deepseek-chat", "gpt-4o-mini"]),
  queryType: pick(["clause_analysis", "risk_scoring", "redline_generation", "summarization", "benchmark_comparison"]),
  confidence: rand(65, 99), latency: rand(200, 3500), tokens: rand(100, 4000),
  flagged: Math.random() > 0.75, flagType: Math.random() > 0.5 ? "low_confidence" : "sensitive_content",
  user: pick(["Alice Chen", "Bob Martinez", "Carol Singh", "David Kim"]), status: pick(["completed", "completed", "completed", "flagged", "failed"]),
}));

// ── Audit Events ────────────────────────────────────────────────────────────

export const auditEvents: AuditEvent[] = Array.from({ length: 30 }, (_, i) => ({
  id: `AUD-${2026001 + i}`, timestamp: new Date(Date.now() - rand(0, 48) * 3600000).toISOString(),
  type: pick(["user", "auth", "ai", "workflow", "security", "integration", "data", "admin"]),
  action: pick(["user.login", "user.create", "contract.upload", "risk.analyze", "workflow.approve", "integration.sync", "permission.change", "settings.update", "data.export", "ai.query"]),
  user: pick(["Alice Chen", "Bob Martinez", "Carol Singh", "David Kim", "System", "Admin"]),
  resource: pick(["CON-2026001", "MSA-101", "WF-2026003", "SUP-2026005", "User Settings", "Integration Hub"]),
  details: pick(["User logged in from new IP", "Contract uploaded via API", "Risk analysis completed", "Workflow approved", "Integration synced successfully", "Permission updated for role"]),
  severity: pick(["info", "info", "info", "low", "medium", "high"]),
  ip: `203.0.113.${rand(1, 255)}`, status: pick(["success", "success", "success", "failure", "blocked"]),
}));

// ── System Health ───────────────────────────────────────────────────────────

export const systemHealthMetrics: SystemHealthMetric[] = [
  { id: "svc-1", service: "API Gateway", status: "healthy", uptime: 99.98, latency: 45, errorRate: 0.02, requestsPerMin: 12500, lastIncident: "2026-04-28", region: "us-east-1" },
  { id: "svc-2", service: "AI Inference", status: "healthy", uptime: 99.92, latency: 850, errorRate: 0.15, requestsPerMin: 3400, lastIncident: "2026-05-01", region: "us-east-1" },
  { id: "svc-3", service: "Vector Database", status: "healthy", uptime: 99.95, latency: 120, errorRate: 0.05, requestsPerMin: 8900, lastIncident: "2026-04-15", region: "us-west-2" },
  { id: "svc-4", service: "OCR Processing", status: "degraded", uptime: 98.50, latency: 3200, errorRate: 1.20, requestsPerMin: 450, lastIncident: "2026-05-14", region: "eu-west-1" },
  { id: "svc-5", service: "WebSocket Gateway", status: "healthy", uptime: 99.99, latency: 25, errorRate: 0.01, requestsPerMin: 2200, lastIncident: "2026-03-20", region: "us-east-1" },
  { id: "svc-6", service: "Document Store", status: "healthy", uptime: 99.97, latency: 65, errorRate: 0.03, requestsPerMin: 5600, lastIncident: "2026-05-05", region: "us-east-1" },
  { id: "svc-7", service: "Redis Cache", status: "healthy", uptime: 99.99, latency: 2, errorRate: 0.00, requestsPerMin: 45000, lastIncident: "2026-02-10", region: "us-east-1" },
  { id: "svc-8", service: "Workflow Engine", status: "degraded", uptime: 99.10, latency: 450, errorRate: 0.80, requestsPerMin: 1800, lastIncident: "2026-05-13", region: "eu-west-1" },
];

// ── Integrations ────────────────────────────────────────────────────────────

export const integrations: Integration[] = [
  { id: "int-1", name: "DocuSign", type: "eSignature", status: "connected", lastSync: "2026-05-15T09:30:00Z", errorRate: 0.1, version: "v2.1", configUrl: "/admin/integrations/docusign", enabled: true },
  { id: "int-2", name: "Salesforce", type: "CRM", status: "connected", lastSync: "2026-05-15T09:25:00Z", errorRate: 0.3, version: "v58.0", configUrl: "/admin/integrations/salesforce", enabled: true },
  { id: "int-3", name: "Slack", type: "Messaging", status: "connected", lastSync: "2026-05-15T09:28:00Z", errorRate: 0.0, version: "v2.0", configUrl: "/admin/integrations/slack", enabled: true },
  { id: "int-4", name: "Jira", type: "Project Management", status: "connected", lastSync: "2026-05-15T09:20:00Z", errorRate: 0.5, version: "v3.0", configUrl: "/admin/integrations/jira", enabled: true },
  { id: "int-5", name: "SAP Ariba", type: "Procurement", status: "error", lastSync: "2026-05-14T22:00:00Z", errorRate: 5.2, version: "v1.0", configUrl: "/admin/integrations/ariba", enabled: true },
  { id: "int-6", name: "Microsoft 365", type: "Productivity", status: "connected", lastSync: "2026-05-15T09:29:00Z", errorRate: 0.05, version: "v1.0", configUrl: "/admin/integrations/m365", enabled: true },
  { id: "int-7", name: "Google Workspace", type: "Productivity", status: "disconnected", lastSync: "2026-05-10T12:00:00Z", errorRate: 0.0, version: "v1.0", configUrl: "/admin/integrations/google", enabled: false },
  { id: "int-8", name: "ServiceNow", type: "ITSM", status: "connected", lastSync: "2026-05-15T09:15:00Z", errorRate: 0.2, version: "v2.0", configUrl: "/admin/integrations/servicenow", enabled: true },
  { id: "int-9", name: "Coupa", type: "Procurement", status: "pending", lastSync: "—", errorRate: 0.0, version: "v1.0", configUrl: "/admin/integrations/coupa", enabled: false },
  { id: "int-10", name: "Teams", type: "Messaging", status: "connected", lastSync: "2026-05-15T09:27:00Z", errorRate: 0.1, version: "v1.0", configUrl: "/admin/integrations/teams", enabled: true },
];

// ── Compliance ──────────────────────────────────────────────────────────────

export const complianceChecks: ComplianceCheck[] = [
  { id: "comp-1", standard: "SOC 2 Type II", status: "compliant", score: 94, lastAudit: "2026-04-15", nextAudit: "2026-10-15", findings: 2 },
  { id: "comp-2", standard: "GDPR", status: "compliant", score: 91, lastAudit: "2026-03-20", nextAudit: "2026-09-20", findings: 5 },
  { id: "comp-3", standard: "HIPAA", status: "in_progress", score: 72, lastAudit: "2026-05-01", nextAudit: "2026-08-01", findings: 12 },
  { id: "comp-4", standard: "ISO 27001", status: "compliant", score: 96, lastAudit: "2026-02-10", nextAudit: "2026-08-10", findings: 1 },
  { id: "comp-5", standard: "CCPA", status: "non_compliant", score: 58, lastAudit: "2026-05-10", nextAudit: "2026-07-10", findings: 18 },
  { id: "comp-6", standard: "FedRAMP", status: "not_applicable", score: 0, lastAudit: "—", nextAudit: "—", findings: 0 },
];

// ── Security Alerts ─────────────────────────────────────────────────────────

export const securityAlerts: SecurityAlert[] = [
  { id: "sec-1", title: "Suspicious Login Pattern Detected", description: "Multiple failed login attempts from IP 185.220.101.x across 3 user accounts within 5 minutes.", severity: "critical", timestamp: new Date(Date.now() - 3600000).toISOString(), source: "Auth0", status: "open", assignedTo: "Alice Chen" },
  { id: "sec-2", title: "API Key Rotation Required", description: "API key sk-proj-...f3K8 has been active for 178 days. Policy requires rotation every 90 days.", severity: "high", timestamp: new Date(Date.now() - 7200000).toISOString(), source: "Security Scanner", status: "open" },
  { id: "sec-3", title: "Sensitive Data Exposure Attempt", description: "AI query attempted to extract PII from contract corpus. Pattern matched SSN regex.", severity: "critical", timestamp: new Date(Date.now() - 10800000).toISOString(), source: "AI Governance", status: "investigating", assignedTo: "Bob Martinez" },
  { id: "sec-4", title: "New Device Login Alert", description: "User Carol Singh logged in from unrecognized device (Chrome 125, macOS, IP: 203.0.113.42).", severity: "medium", timestamp: new Date(Date.now() - 14400000).toISOString(), source: "Auth0", status: "open" },
  { id: "sec-5", title: "Integration Sync Failure", description: "SAP Ariba integration sync failed 3 times in the last hour. Error: OAuth token expired.", severity: "high", timestamp: new Date(Date.now() - 18000000).toISOString(), source: "Integration Hub", status: "investigating", assignedTo: "David Kim" },
  { id: "sec-6", title: "Rate Limit Threshold Approaching", description: "API Gateway approaching rate limit for tenant 'acme-corp'. Current: 11,200/12,000 req/min.", severity: "medium", timestamp: new Date(Date.now() - 21600000).toISOString(), source: "API Gateway", status: "open" },
];

// ── Tenants ─────────────────────────────────────────────────────────────────

export const tenants: TenantConfig[] = [
  { id: "tnt-1", name: "Acme Corp", plan: "Enterprise", users: 245, storage: "4.2 TB", region: "us-east-1", complianceScore: 94, status: "active", created: "2025-01-15" },
  { id: "tnt-2", name: "GlobalTech Inc", plan: "Enterprise", users: 182, storage: "3.1 TB", region: "eu-west-1", complianceScore: 88, status: "active", created: "2025-03-20" },
  { id: "tnt-3", name: "SecureNet Solutions", plan: "Business", users: 89, storage: "1.8 TB", region: "us-west-2", complianceScore: 76, status: "active", created: "2025-06-01" },
  { id: "tnt-4", name: "DataSync Partners", plan: "Business", users: 64, storage: "950 GB", region: "ap-southeast-1", complianceScore: 82, status: "active", created: "2025-08-15" },
  { id: "tnt-5", name: "Pacific Rim Trading", plan: "Starter", users: 12, storage: "120 GB", region: "ap-northeast-1", complianceScore: 45, status: "trial", created: "2026-04-01" },
];

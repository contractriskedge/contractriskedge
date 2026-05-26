// ── Enterprise Admin & Security Console Types ──────────────────────────────

export type SeverityLevel = "critical" | "high" | "medium" | "low" | "info" | "warning" | "success";
export type UserStatus = "active" | "inactive" | "suspended" | "pending";
export type IntegrationStatus = "connected" | "disconnected" | "error" | "pending";
export type AuditEventType = "user" | "auth" | "ai" | "workflow" | "security" | "integration" | "data" | "admin";

export interface AdminKpi {
  id: string; label: string; value: string; trend: number;
  trendDirection: "up" | "down" | "neutral";
  icon: string; color: string; severity: SeverityLevel;
  sparklineData: number[]; tooltip: string;
}

export interface AdminUser {
  id: string; name: string; email: string; role: string; status: UserStatus;
  lastActive: string; mfaEnabled: boolean; ssoConnected: boolean;
  department: string; groups: string[]; permissions: string[];
  created: string; loginCount: number; lastIp: string;
}

export interface RoleDefinition {
  id: string; name: string; description: string; permissions: string[];
  userCount: number; isSystem: boolean; inheritance: string[];
}

export interface AiGovernanceEvent {
  id: string; timestamp: string; model: string; queryType: string;
  confidence: number; latency: number; tokens: number;
  flagged: boolean; flagType?: string; user: string; status: string;
}

export interface AuditEvent {
  id: string; timestamp: string; type: AuditEventType;
  action: string; user: string; resource: string; details: string;
  severity: SeverityLevel; ip: string; status: "success" | "failure" | "blocked";
}

export interface SystemHealthMetric {
  id: string; service: string; status: "healthy" | "degraded" | "down";
  uptime: number; latency: number; errorRate: number; requestsPerMin: number;
  lastIncident: string; region: string;
}

export interface Integration {
  id: string; name: string; type: string; status: IntegrationStatus;
  lastSync: string; errorRate: number; version: string;
  configUrl: string; enabled: boolean;
}

export interface ComplianceCheck {
  id: string; standard: string; status: "compliant" | "non_compliant" | "in_progress" | "not_applicable";
  score: number; lastAudit: string; nextAudit: string; findings: number;
}

export interface SecurityAlert {
  id: string; title: string; description: string; severity: SeverityLevel;
  timestamp: string; source: string; status: "open" | "investigating" | "resolved";
  assignedTo?: string;
}

export interface TenantConfig {
  id: string; name: string; plan: string; users: number; storage: string;
  region: string; complianceScore: number; status: "active" | "suspended" | "trial";
  created: string;
}

export const SEVERITY_CONFIG: Record<SeverityLevel, { color: string; bg: string; label: string }> = {
  critical: { color: "text-red-700", bg: "bg-red-50", label: "Critical" },
  high: { color: "text-orange-700", bg: "bg-orange-50", label: "High" },
  medium: { color: "text-yellow-700", bg: "bg-yellow-50", label: "Medium" },
  low: { color: "text-green-700", bg: "bg-green-50", label: "Low" },
  info: { color: "text-blue-700", bg: "bg-blue-50", label: "Info" },
  warning: { color: "text-amber-700", bg: "bg-amber-50", label: "Warning" },
  success: { color: "text-emerald-700", bg: "bg-emerald-50", label: "Success" },
};

export const RISK_BG: Record<SeverityLevel, string> = { critical: "bg-red-500", high: "bg-orange-500", medium: "bg-yellow-500", low: "bg-green-500", info: "bg-blue-500", warning: "bg-amber-500", success: "bg-emerald-500" };
export const RISK_TEXT: Record<SeverityLevel, string> = { critical: "text-red-700", high: "text-orange-700", medium: "text-yellow-700", low: "text-green-700", info: "text-blue-700", warning: "text-amber-700", success: "text-emerald-700" };
export const RISK_BG_LIGHT: Record<SeverityLevel, string> = { critical: "bg-red-50", high: "bg-orange-50", medium: "bg-yellow-50", low: "bg-green-50", info: "bg-blue-50", warning: "bg-amber-50", success: "bg-emerald-50" };

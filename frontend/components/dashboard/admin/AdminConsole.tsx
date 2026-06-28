"use client";

import React, { useState, useCallback } from "react";
import { motion } from "framer-motion";
import { Shield, Download, RefreshCw, Search, Loader2, AlertCircle } from "lucide-react";
import { AdminKpiCards } from "./AdminKpiCards";
import { UserManagement } from "./UserManagement";
import { AiGovernanceCenter } from "./AiGovernanceCenter";
import { AuditCenter } from "./AuditCenter";
import { AuditReportsPanel } from "./AuditReportsPanel";
import { SystemHealth } from "./SystemHealth";
import { IntegrationsHub } from "./IntegrationsHub";
import { SecurityCenter } from "./SecurityCenter";
import { AdminDetailDrawer } from "./AdminDetailDrawer";
import { AdminFilterBar } from "./AdminFilterBar";
import { useAdminDashboard, useAdminUsers, useAuditLogs } from "@/services/hooks/useAdmin";
import { useAuth } from "@/components/auth/AuthProvider";
import type { AdminUser, AuditEventType } from "./types";

// ── Audit event type/severity mapping ────────────────────────────
function mapAuditEventType(eventType: string): AuditEventType {
  if (eventType.startsWith("review.") || eventType.startsWith("finding.") || eventType.startsWith("redline.")) return "workflow";
  if (eventType.startsWith("ai.") || eventType.includes("copilot")) return "ai";
  if (eventType.startsWith("version.")) return "data";
  if (eventType.startsWith("user.") || eventType.includes("auth")) return "auth";
  if (eventType.startsWith("security.")) return "security";
  if (eventType.startsWith("integration.")) return "integration";
  return "admin";
}

function mapAuditSeverity(eventType: string): "critical" | "high" | "medium" | "low" | "info" {
  if (eventType.includes("escalated") || eventType.includes("rejected") || eventType.includes("breach")) return "high";
  if (eventType.includes("approved") || eventType.includes("resolved") || eventType.includes("accepted")) return "low";
  if (eventType.includes("deleted") || eventType.includes("failure")) return "medium";
  return "info";
}

interface AdminFilters {
  tenant: string; userRole: string; complianceStatus: string;
  integrationType: string; auditSeverity: string; aiModel: string;
}

const defaultFilters: AdminFilters = {
  tenant: "", userRole: "", complianceStatus: "", integrationType: "", auditSeverity: "", aiModel: "",
};

export function AdminConsole() {
  const { hasPermission } = useAuth();
  const isFullAdmin = hasPermission("admin:tenant");
  const canViewAudit = hasPermission("audit:read");

  const [filters, setFilters] = useState<AdminFilters>({ ...defaultFilters });
  const [selectedUser, setSelectedUser] = useState<AdminUser | null>(null);

  const { data: dashboardData, isLoading, error, refetch } = useAdminDashboard(isFullAdmin);
  const { data: usersData } = useAdminUsers(undefined, isFullAdmin);
  const { data: auditLogsData } = useAuditLogs({ page_size: 50 }, canViewAudit);

  const adminKpis = dashboardData?.kpis ?? [];
  const adminUsers = usersData?.data ?? [];
  const systemHealthMetrics = dashboardData?.system_health
    ? [{
        id: "system-health-1",
        service: "API Server",
        status: dashboardData.system_health,
        uptime: 99.9,
        latency: 45,
        errorRate: 0.1,
        requestsPerMin: 1200,
        region: "us-east-1",
        lastIncident: "3 days ago",
      }]
    : [];
  const auditEvents = (auditLogsData?.events ?? []).map((e) => ({
    id: String(e.event_id ?? ""),
    timestamp: String(e.created_at ?? ""),
    type: mapAuditEventType(String(e.event_type ?? "")),
    action: String(e.action ?? e.event_type ?? ""),
    user: String(e.actor_id ?? ""),
    resource: String(e.resource_id ?? e.resource_type ?? ""),
    details: String(e.description ?? `${e.event_type} on ${e.resource_type}`),
    severity: mapAuditSeverity(String(e.event_type ?? "")),
    ip: "",
    status: (e.status === "failure" || e.status === "blocked" ? e.status : "success") as "success" | "failure" | "blocked",
  }));
  const integrations = [];
  const securityAlerts = [];
  const tenants = [];
  const roleDefinitions = [];
  const aiGovernanceEvents = [];
  const complianceChecks = [];

  const handleFilterChange = useCallback((key: keyof AdminFilters, value: string) => {
    setFilters((prev) => ({ ...prev, [key]: value }));
  }, []);
  const resetFilters = useCallback(() => setFilters({ ...defaultFilters }), []);

  // Loading state (full admin only)
  if (isFullAdmin && isLoading && adminUsers.length === 0) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <Loader2 className="w-8 h-8 text-gold-400 animate-spin mx-auto mb-3" />
          <p className="text-sm text-gray-500">Loading admin console...</p>
        </div>
      </div>
    );
  }

  // Error state (full admin only — audit-only users still see audit panel)
  if (isFullAdmin && error && adminUsers.length === 0) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center max-w-md">
          <AlertCircle className="w-10 h-10 text-red-400 mx-auto mb-3" />
          <p className="text-sm font-medium text-gray-900 mb-1">Failed to load admin data</p>
          <p className="text-xs text-gray-500 mb-4">{(error as Error)?.message || "An unexpected error occurred"}</p>
          <button onClick={() => refetch()} className="inline-flex items-center gap-1.5 text-xs font-medium text-gold-600 hover:text-gold-700">
            <RefreshCw className="w-3.5 h-3.5" /> Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4 pb-24">
      {/* Header */}
      <motion.div initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }} className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-slate-700 to-navy-900 flex items-center justify-center shadow-sm">
            <Shield className="w-5 h-5 text-white" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-navy-900">
              {isFullAdmin ? "Admin & Security Console" : "Audit & Compliance"}
            </h1>
            <p className="text-xs text-gray-500 mt-0.5">
              {isFullAdmin
                ? "Enterprise governance, security, and administration"
                : "View and export tenant audit logs"}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg bg-white border border-gray-200 text-gray-600 hover:bg-gray-50 transition-colors">
            <RefreshCw className="w-3.5 h-3.5" /> Refresh
          </button>
          <button className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg bg-navy-700 text-white hover:bg-navy-800 transition-colors shadow-sm">
            <Download className="w-3.5 h-3.5" /> Export Report
          </button>
        </div>
      </motion.div>

      {/* KPI Row — tenant admins only */}
      {isFullAdmin && <AdminKpiCards metrics={adminKpis} />}

      {/* Filter Bar — tenant admins only */}
      {isFullAdmin && (
        <AdminFilterBar filters={filters} onChange={handleFilterChange} onReset={resetFilters} />
      )}

      {/* Section 1: User Management */}
      {isFullAdmin && (
        <UserManagement users={adminUsers} roles={roleDefinitions} onSelectUser={setSelectedUser} />
      )}

      {/* Section 2: AI Governance + System Health */}
      {isFullAdmin && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <AiGovernanceCenter events={aiGovernanceEvents} />
          <SystemHealth metrics={systemHealthMetrics} />
        </div>
      )}

      {/* Enterprise Audit Reports */}
      {canViewAudit && <AuditReportsPanel />}

      {/* Audit summary cards */}
      {canViewAudit && <AuditCenter events={auditEvents} compliance={complianceChecks} />}

      {/* Section 4: Integrations + Security */}
      {isFullAdmin && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <IntegrationsHub integrations={integrations} />
          <SecurityCenter alerts={securityAlerts} tenants={tenants} />
        </div>
      )}

      {/* Detail Drawer */}
      {isFullAdmin && (
        <AdminDetailDrawer user={selectedUser} onClose={() => setSelectedUser(null)} />
      )}
    </div>
  );
}

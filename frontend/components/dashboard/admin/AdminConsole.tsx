"use client";

import React, { useState, useCallback } from "react";
import { motion } from "framer-motion";
import { Shield, Download, RefreshCw, Search } from "lucide-react";
import { AdminKpiCards } from "./AdminKpiCards";
import { UserManagement } from "./UserManagement";
import { AiGovernanceCenter } from "./AiGovernanceCenter";
import { AuditCenter } from "./AuditCenter";
import { SystemHealth } from "./SystemHealth";
import { IntegrationsHub } from "./IntegrationsHub";
import { SecurityCenter } from "./SecurityCenter";
import { AdminDetailDrawer } from "./AdminDetailDrawer";
import { AdminFilterBar } from "./AdminFilterBar";
import { adminKpis, adminUsers, roleDefinitions, aiGovernanceEvents, auditEvents, complianceChecks, systemHealthMetrics, integrations, securityAlerts, tenants } from "./mockData";
import type { AdminUser } from "./types";

interface AdminFilters {
  tenant: string; userRole: string; complianceStatus: string;
  integrationType: string; auditSeverity: string; aiModel: string;
}

const defaultFilters: AdminFilters = {
  tenant: "", userRole: "", complianceStatus: "", integrationType: "", auditSeverity: "", aiModel: "",
};

export function AdminConsole() {
  const [filters, setFilters] = useState<AdminFilters>({ ...defaultFilters });
  const [selectedUser, setSelectedUser] = useState<AdminUser | null>(null);

  const handleFilterChange = useCallback((key: keyof AdminFilters, value: string) => {
    setFilters((prev) => ({ ...prev, [key]: value }));
  }, []);
  const resetFilters = useCallback(() => setFilters({ ...defaultFilters }), []);

  return (
    <div className="space-y-4 pb-24">
      {/* Header */}
      <motion.div initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }} className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-slate-700 to-navy-900 flex items-center justify-center shadow-sm">
            <Shield className="w-5 h-5 text-white" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-navy-900">Admin & Security Console</h1>
            <p className="text-xs text-gray-500 mt-0.5">Enterprise governance, security, and administration</p>
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

      {/* KPI Row */}
      <AdminKpiCards metrics={adminKpis} />

      {/* Filter Bar */}
      <AdminFilterBar filters={filters} onChange={handleFilterChange} onReset={resetFilters} />

      {/* Section 1: User Management */}
      <UserManagement users={adminUsers} roles={roleDefinitions} onSelectUser={setSelectedUser} />

      {/* Section 2: AI Governance + System Health */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <AiGovernanceCenter events={aiGovernanceEvents} />
        <SystemHealth metrics={systemHealthMetrics} />
      </div>

      {/* Section 3: Audit + Compliance */}
      <AuditCenter events={auditEvents} compliance={complianceChecks} />

      {/* Section 4: Integrations + Security */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <IntegrationsHub integrations={integrations} />
        <SecurityCenter alerts={securityAlerts} tenants={tenants} />
      </div>

      {/* Detail Drawer */}
      <AdminDetailDrawer user={selectedUser} onClose={() => setSelectedUser(null)} />
    </div>
  );
}

"use client";

import React from "react";
import { motion } from "framer-motion";
import { Shield, AlertTriangle, AlertOctagon, Clock, User, MoreHorizontal } from "lucide-react";
import type { SecurityAlert, TenantConfig } from "./types";
import { SEVERITY_CONFIG } from "./types";

export function SecurityCenter({ alerts, tenants }: { alerts: SecurityAlert[]; tenants: TenantConfig[] }) {
  const openAlerts = alerts.filter((a) => a.status === "open" || a.status === "investigating");

  return (
    <div className="space-y-4">
      {/* Security alerts */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
        <div className="px-4 py-3 border-b border-gray-100 flex items-center justify-between">
          <div className="flex items-center gap-2"><Shield className="w-4 h-4 text-navy-700" /><h3 className="text-xs font-semibold text-navy-900">Security Alerts</h3></div>
          <span className="text-[10px] text-red-600 font-medium bg-red-50 px-2 py-0.5 rounded-full">{openAlerts.length} open</span>
        </div>
        <div className="divide-y divide-gray-50">
          {alerts.map((a) => {
            const sev = SEVERITY_CONFIG[a.severity];
            return (
              <div key={a.id} className="flex items-start gap-2.5 px-4 py-2.5 hover:bg-gray-50 transition-colors">
                <div className={`w-7 h-7 rounded-full flex items-center justify-center ${sev.bg} mt-0.5`}>
                  {a.severity === "critical" ? <AlertOctagon className="w-3.5 h-3.5" /> : <AlertTriangle className="w-3.5 h-3.5" />}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-1.5">
                    <span className="text-[11px] font-semibold text-navy-900">{a.title}</span>
                    <span className={`text-[9px] font-medium px-1.5 py-0.5 rounded-full ${sev.bg} ${sev.color}`}>{a.severity}</span>
                    <span className={`text-[9px] font-medium px-1.5 py-0.5 rounded-full ${a.status === "open" ? "bg-red-50 text-red-700" : a.status === "investigating" ? "bg-yellow-50 text-yellow-700" : "bg-green-50 text-green-700"}`}>{a.status.replace(/_/g, " ")}</span>
                  </div>
                  <p className="text-[10px] text-gray-600 mt-0.5">{a.description}</p>
                  <div className="flex items-center gap-2 text-[9px] text-gray-400 mt-1">
                    <span>Source: {a.source}</span>
                    {a.assignedTo && <span>• Assigned: {a.assignedTo}</span>}
                    <span>• {formatTime(a.timestamp)}</span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Tenants */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
        <div className="px-4 py-3 border-b border-gray-100"><h3 className="text-xs font-semibold text-navy-900">Tenants</h3></div>
        <div className="divide-y divide-gray-50">
          {tenants.map((t) => (
            <div key={t.id} className="flex items-center gap-3 px-4 py-2.5 hover:bg-gray-50 transition-colors">
              <div className={`w-2 h-2 rounded-full ${t.status === "active" ? "bg-green-500" : t.status === "trial" ? "bg-yellow-500" : "bg-red-500"}`} />
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-1.5">
                  <span className="text-[11px] font-medium text-gray-800">{t.name}</span>
                  <span className="text-[9px] text-gray-400">{t.plan}</span>
                </div>
                <div className="flex items-center gap-2 text-[9px] text-gray-400 mt-0.5">
                  <span>{t.users} users</span><span>{t.storage}</span><span>{t.region}</span>
                </div>
              </div>
              <div className="text-right">
                <div className="flex items-center gap-1.5">
                  <div className="w-12 h-1.5 bg-gray-200 rounded-full overflow-hidden">
                    <div className={`h-full rounded-full ${t.complianceScore >= 85 ? "bg-green-500" : t.complianceScore >= 60 ? "bg-yellow-500" : "bg-red-500"}`} style={{ width: `${t.complianceScore}%` }} />
                  </div>
                  <span className="text-[10px] font-medium tabular-nums">{t.complianceScore}%</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function formatTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const hrs = Math.floor(diff / 3600000);
  if (hrs < 1) return "just now"; if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

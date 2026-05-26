/**
 * AdminConsole — Enterprise administration dashboard.
 *
 * Tabs:
 * - Dashboard: Platform overview with KPI cards
 * - Users: User and role management
 * - Health: System infrastructure monitoring
 * - Settings: Tenant configuration
 */

"use client";

import React, { useState, useCallback, useMemo } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { motion } from "framer-motion";
import {
  LayoutDashboard, Users, Activity, Settings, Shield,
  RefreshCw, Loader2, Search, Plus, X, Check, AlertTriangle,
  Server, Database, HardDrive, Bell, Brain, Zap, Clock,
  UserPlus, UserX, ChevronDown, MoreHorizontal,
} from "lucide-react";
import { api } from "@/services/api/client";

// ── Types ────────────────────────────────────────────────────────

interface AdminUser {
  user_id: string;
  email: string;
  name: string | null;
  role: string;
  business_unit: string | null;
  is_active: boolean;
  is_invited: boolean;
  last_login_at: string | null;
  created_at: string;
}

interface AdminRole {
  role_id: string;
  name: string;
  description: string | null;
  permissions: string[];
  is_system: boolean;
}

interface SystemHealth {
  status: string;
  database: { connected: boolean; pool_size: number };
  redis: { connected: boolean; queue_depth: number; memory_used_mb: number };
  celery: { worker_count: number; active_tasks: number; queue_sizes: Record<string, number> };
  websocket: { active_connections: number; messages_sent: number };
  ai: { model: string; avg_latency_ms: number; failures_24h: number; tokens_24h: number; cost_24h: number };
  storage: { total_documents: number; total_chunks: number };
}

interface TenantSettings {
  brand_name: string | null;
  ai_model: string;
  risk_threshold_critical: number;
  sla_critical_hours: number;
  features_enabled: Record<string, boolean>;
}

// ── Hooks ────────────────────────────────────────────────────────

function useAdminUsers() {
  return useQuery({ queryKey: ["admin", "users"], queryFn: () => api.get<AdminUser[]>("/admin/users"), staleTime: 30_000 });
}

function useAdminRoles() {
  return useQuery({ queryKey: ["admin", "roles"], queryFn: () => api.get<AdminRole[]>("/admin/roles"), staleTime: 60_000 });
}

function useSystemHealth() {
  return useQuery({ queryKey: ["admin", "health"], queryFn: () => api.get<SystemHealth>("/admin/health"), staleTime: 15_000, refetchInterval: 30_000 });
}

function useTenantSettings() {
  return useQuery({ queryKey: ["admin", "settings"], queryFn: () => api.get<TenantSettings>("/admin/settings"), staleTime: 60_000 });
}

// ── Stat Card ────────────────────────────────────────────────────

function StatCard({ icon, label, value, sub, color }: {
  icon: React.ReactNode; label: string; value: string | number; sub?: string; color: string;
}) {
  return (
    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
      className="bg-white rounded-xl border border-gray-200 shadow-sm p-4 hover:shadow-md transition-all"
    >
      <div className="flex items-start justify-between mb-2">
        <div className={`w-9 h-9 rounded-lg flex items-center justify-center bg-gradient-to-br ${color} text-white shadow-xs`}>
          {icon}
        </div>
      </div>
      <p className="text-2xl font-bold text-navy-900 tabular-nums">{value}</p>
      <p className="text-xs text-gray-500 mt-0.5">{label}</p>
      {sub && <p className="text-[10px] text-gray-400 mt-0.5">{sub}</p>}
    </motion.div>
  );
}

// ── Status Badge ─────────────────────────────────────────────────

function StatusBadge({ status }: { status: string }) {
  const cfg: Record<string, { bg: string; text: string; dot: string; label: string }> = {
    healthy: { bg: "bg-green-50", text: "text-green-700", dot: "bg-green-500", label: "Healthy" },
    degraded: { bg: "bg-yellow-50", text: "text-yellow-700", dot: "bg-yellow-500", label: "Degraded" },
    unhealthy: { bg: "bg-red-50", text: "text-red-700", dot: "bg-red-500", label: "Unhealthy" },
    connected: { bg: "bg-green-50", text: "text-green-700", dot: "bg-green-500", label: "Connected" },
    disconnected: { bg: "bg-red-50", text: "text-red-700", dot: "bg-red-500", label: "Disconnected" },
  };
  const c = cfg[status] ?? cfg.healthy;
  return <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-semibold ${c.bg} ${c.text}`}><span className={`w-1.5 h-1.5 rounded-full ${c.dot}`} />{c.label}</span>;
}

// ── Main Component ───────────────────────────────────────────────

type AdminTab = "dashboard" | "users" | "health" | "settings";

export function AdminConsole() {
  const [activeTab, setActiveTab] = useState<AdminTab>("dashboard");
  const [userSearch, setUserSearch] = useState("");

  const { data: users, isLoading: usersLoading } = useAdminUsers();
  const { data: roles } = useAdminRoles();
  const { data: health, isLoading: healthLoading } = useSystemHealth();
  const { data: settings } = useTenantSettings();

  const tabs: { id: AdminTab; label: string; icon: React.ReactNode }[] = [
    { id: "dashboard", label: "Dashboard", icon: <LayoutDashboard className="w-4 h-4" /> },
    { id: "users", label: "Users", icon: <Users className="w-4 h-4" /> },
    { id: "health", label: "Health", icon: <Activity className="w-4 h-4" /> },
    { id: "settings", label: "Settings", icon: <Settings className="w-4 h-4" /> },
  ];

  const filteredUsers = useMemo(() => {
    if (!users) return [];
    if (!userSearch) return users;
    const q = userSearch.toLowerCase();
    return users.filter((u) => u.email.toLowerCase().includes(q) || u.name?.toLowerCase().includes(q) || u.role.includes(q));
  }, [users, userSearch]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-navy-900">Admin Console</h1>
          <p className="text-sm text-gray-500 mt-1">Platform administration and system operations</p>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-gray-400">
            {users?.length ?? 0} users &middot; {health?.websocket.active_connections ?? 0} live connections
          </span>
        </div>
      </div>

      {/* Tab bar */}
      <div className="flex gap-1 bg-gray-100 p-1 rounded-lg w-fit">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md transition-colors ${
              activeTab === tab.id ? "bg-white text-navy-900 shadow-sm" : "text-gray-500 hover:text-gray-700"
            }`}
          >
            {tab.icon} {tab.label}
          </button>
        ))}
      </div>

      {/* ── DASHBOARD TAB ── */}
      {activeTab === "dashboard" && (
        <div className="space-y-4">
          <h2 className="text-sm font-semibold text-navy-900">Platform Overview</h2>
          <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-6 gap-3">
            <StatCard icon={<Users className="w-4 h-4" />} label="Total Users" value={users?.length ?? 0} color="from-blue-500 to-indigo-600" />
            <StatCard icon={<Server className="w-4 h-4" />} label="System Status" value={health?.status ?? "unknown"} color={health?.status === "healthy" ? "from-green-500 to-emerald-600" : "from-red-500 to-rose-600"} />
            <StatCard icon={<HardDrive className="w-4 h-4" />} label="Documents" value={health?.storage.total_documents ?? 0} sub={`${health?.storage.total_chunks ?? 0} chunks`} color="from-cyan-500 to-teal-600" />
            <StatCard icon={<Zap className="w-4 h-4" />} label="AI Cost (24h)" value={`$${(health?.ai.cost_24h ?? 0).toFixed(2)}`} sub={`${(health?.ai.tokens_24h ?? 0).toLocaleString()} tokens`} color="from-amber-500 to-orange-600" />
            <StatCard icon={<Activity className="w-4 h-4" />} label="WS Connections" value={health?.websocket.active_connections ?? 0} sub={`${health?.websocket.messages_sent ?? 0} msgs sent`} color="from-purple-500 to-violet-600" />
            <StatCard icon={<Brain className="w-4 h-4" />} label="AI Latency" value={`${health?.ai.avg_latency_ms ?? 0}ms`} sub={`${health?.ai.failures_24h ?? 0} failures`} color="from-pink-500 to-rose-600" />
          </div>

          {/* Queue depths */}
          {health?.celery.queue_sizes && Object.keys(health.celery.queue_sizes).length > 0 && (
            <div>
              <h3 className="text-xs font-semibold text-navy-900 mb-2">Queue Depths</h3>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                {Object.entries(health.celery.queue_sizes).map(([name, depth]) => (
                  <div key={name} className="bg-white rounded-lg border border-gray-200 p-3 flex items-center justify-between">
                    <span className="text-xs text-gray-600 capitalize">{name}</span>
                    <span className={`text-sm font-bold ${(depth as number) > 0 ? "text-amber-600" : "text-navy-900"}`}>{depth as number}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Feature flags */}
          {settings?.features_enabled && (
            <div>
              <h3 className="text-xs font-semibold text-navy-900 mb-2">Feature Status</h3>
              <div className="flex flex-wrap gap-2">
                {Object.entries(settings.features_enabled).map(([key, enabled]) => (
                  <span key={key} className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[10px] font-medium ${
                    enabled ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-500"
                  }`}>
                    {enabled ? <Check className="w-3 h-3" /> : <X className="w-3 h-3" />}
                    {key.replace(/_/g, " ")}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* ── USERS TAB ── */}
      {activeTab === "users" && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-navy-900">User Management ({users?.length ?? 0})</h2>
            <div className="flex items-center gap-2">
              <div className="relative">
                <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-gray-400" />
                <input
                  type="text"
                  value={userSearch}
                  onChange={(e) => setUserSearch(e.target.value)}
                  placeholder="Search users..."
                  className="w-48 pl-8 pr-3 py-1.5 text-xs border border-gray-300 rounded-lg focus:border-blue-500 focus:outline-none"
                />
              </div>
            </div>
          </div>

          <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
            {usersLoading ? (
              <div className="flex justify-center py-12"><Loader2 className="w-6 h-6 text-gray-400 animate-spin" /></div>
            ) : filteredUsers.length === 0 ? (
              <div className="flex flex-col items-center py-12 text-center">
                <Users className="w-10 h-10 text-gray-300 mb-3" />
                <p className="text-sm text-gray-500">No users found</p>
              </div>
            ) : (
              <div className="divide-y divide-gray-100">
                {filteredUsers.map((user) => (
                  <div key={user.user_id} className="flex items-center gap-4 px-4 py-3 hover:bg-gray-50">
                    <div className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold text-white ${
                      user.role === "admin" ? "bg-red-500" : user.role === "legal_ops" ? "bg-blue-500" : user.role === "reviewer" ? "bg-green-500" : "bg-gray-500"
                    }`}>
                      {(user.name || user.email).charAt(0).toUpperCase()}
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-navy-900">{user.name || user.email}</p>
                      <p className="text-xs text-gray-500">{user.email}</p>
                    </div>
                    <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-medium capitalize bg-gray-100 text-gray-600">
                      {user.role.replace(/_/g, " ")}
                    </span>
                    {user.business_unit && (
                      <span className="text-xs text-gray-400">{user.business_unit}</span>
                    )}
                    <StatusBadge status={user.is_active ? "connected" : "disconnected"} />
                    {user.last_login_at && (
                      <span className="text-[10px] text-gray-400">{new Date(user.last_login_at).toLocaleDateString()}</span>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* ── HEALTH TAB ── */}
      {activeTab === "health" && (
        <div className="space-y-4">
          <h2 className="text-sm font-semibold text-navy-900">System Health</h2>

          {healthLoading ? (
            <div className="flex justify-center py-12"><Loader2 className="w-6 h-6 text-gray-400 animate-spin" /></div>
          ) : (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              {/* Database */}
              <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-4">
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2"><Database className="w-4 h-4 text-blue-500" /><h3 className="text-xs font-semibold text-navy-900">Database</h3></div>
                  <StatusBadge status={health?.database.connected ? "connected" : "disconnected"} />
                </div>
                <div className="text-xs text-gray-500">Pool: {health?.database.pool_size ?? "N/A"} connections</div>
              </div>

              {/* Redis */}
              <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-4">
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2"><Zap className="w-4 h-4 text-red-500" /><h3 className="text-xs font-semibold text-navy-900">Redis</h3></div>
                  <StatusBadge status={health?.redis.connected ? "connected" : "disconnected"} />
                </div>
                <div className="text-xs text-gray-500">Memory: {health?.redis.memory_used_mb ?? 0}MB &middot; Queue depth: {health?.redis.queue_depth ?? 0}</div>
              </div>

              {/* WebSocket */}
              <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-4">
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2"><Activity className="w-4 h-4 text-purple-500" /><h3 className="text-xs font-semibold text-navy-900">WebSocket</h3></div>
                  <StatusBadge status={(health?.websocket.active_connections ?? 0) > 0 ? "connected" : "disconnected"} />
                </div>
                <div className="text-xs text-gray-500">{health?.websocket.active_connections ?? 0} active connections &middot; {health?.websocket.messages_sent ?? 0} messages sent</div>
              </div>

              {/* AI Operations */}
              <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-4">
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2"><Brain className="w-4 h-4 text-amber-500" /><h3 className="text-xs font-semibold text-navy-900">AI Operations</h3></div>
                  <span className="text-[10px] text-gray-400">{health?.ai.model}</span>
                </div>
                <div className="grid grid-cols-2 gap-2 text-xs">
                  <div><span className="text-gray-500">Latency:</span> <span className="font-medium">{health?.ai.avg_latency_ms ?? 0}ms</span></div>
                  <div><span className="text-gray-500">Failures:</span> <span className="font-medium text-red-600">{health?.ai.failures_24h ?? 0}</span></div>
                  <div><span className="text-gray-500">Tokens:</span> <span className="font-medium">{(health?.ai.tokens_24h ?? 0).toLocaleString()}</span></div>
                  <div><span className="text-gray-500">Cost:</span> <span className="font-medium">${(health?.ai.cost_24h ?? 0).toFixed(2)}</span></div>
                </div>
              </div>

              {/* Celery Queues */}
              {health?.celery.queue_sizes && (
                <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-4 lg:col-span-2">
                  <div className="flex items-center gap-2 mb-3"><Clock className="w-4 h-4 text-indigo-500" /><h3 className="text-xs font-semibold text-navy-900">Celery Queues</h3></div>
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                    {Object.entries(health.celery.queue_sizes).map(([name, depth]) => (
                      <div key={name} className="p-3 rounded-lg bg-gray-50">
                        <p className="text-[10px] text-gray-500 capitalize">{name}</p>
                        <p className="text-lg font-bold text-navy-900">{depth as number}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* ── SETTINGS TAB ── */}
      {activeTab === "settings" && (
        <div className="space-y-4">
          <h2 className="text-sm font-semibold text-navy-900">Tenant Settings</h2>
          {settings ? (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-4">
                <h3 className="text-xs font-semibold text-navy-900 mb-3 flex items-center gap-2"><Brain className="w-4 h-4 text-amber-500" /> AI Configuration</h3>
                <div className="space-y-2 text-xs">
                  <div className="flex justify-between"><span className="text-gray-500">Model</span><span className="font-medium">{settings.ai_model}</span></div>
                  <div className="flex justify-between"><span className="text-gray-500">Critical Risk ≥</span><span className="font-medium">{settings.risk_threshold_critical}%</span></div>
                  <div className="flex justify-between"><span className="text-gray-500">SLA (Critical)</span><span className="font-medium">{settings.sla_critical_hours}h</span></div>
                </div>
              </div>
              <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-4">
                <h3 className="text-xs font-semibold text-navy-900 mb-3 flex items-center gap-2"><Shield className="w-4 h-4 text-green-500" /> Features</h3>
                <div className="space-y-2">
                  {Object.entries(settings.features_enabled).map(([key, enabled]) => (
                    <div key={key} className="flex items-center justify-between text-xs">
                      <span className="text-gray-600 capitalize">{key.replace(/_/g, " ")}</span>
                      <span className={`font-medium ${enabled ? "text-green-600" : "text-gray-400"}`}>{enabled ? "Enabled" : "Disabled"}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            <div className="flex justify-center py-12"><Loader2 className="w-6 h-6 text-gray-400 animate-spin" /></div>
          )}
        </div>
      )}
    </div>
  );
}

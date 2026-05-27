/**
 * DiagnosticsPanel — Operational observability dashboard for the admin console.
 *
 * Tabs:
 *   - Overview: Aggregate system metrics, WebSocket health, reconnect storms
 *   - Event Trace: Correlation timeline viewer for event chains
 *   - Outbox: Outbox audit explorer with dead-letter inspection
 *   - Workers: Worker heartbeat monitoring and queue depths
 *
 * All data comes from real API endpoints (not mock data).
 */

"use client";

import React, { useState } from "react";
import { motion } from "framer-motion";
import {
  Activity, Wifi, Archive, Server, AlertTriangle, Search,
  ChevronRight, Clock, RefreshCw, Loader2, Zap, Database,
  HardDrive, Brain, MessageSquare, History, Shield,
} from "lucide-react";
import {
  useSystemDiagnostics,
  useEventChain,
  useOutboxDiagnostics,
  useWorkerDiagnostics,
} from "@/services/hooks/useDiagnostics";

type DiagTab = "overview" | "event-trace" | "outbox" | "workers";

// ── Stat Card ────────────────────────────────────────────────────

function StatCard({ icon, label, value, sub, color, bad }: {
  icon: React.ReactNode; label: string; value: string | number; sub?: string; color: string; bad?: boolean;
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
      <p className={`text-2xl font-bold tabular-nums ${bad ? "text-red-600" : "text-navy-900"}`}>{value}</p>
      <p className="text-xs text-gray-500 mt-0.5">{label}</p>
      {sub && <p className="text-[10px] text-gray-400 mt-0.5">{sub}</p>}
    </motion.div>
  );
}

// ── Status Badge ─────────────────────────────────────────────────

function StatusBadge({ status, label }: { status: string; label?: string }) {
  const cfg: Record<string, { bg: string; text: string; dot: string }> = {
    healthy: { bg: "bg-green-50", text: "text-green-700", dot: "bg-green-500" },
    degraded: { bg: "bg-yellow-50", text: "text-yellow-700", dot: "bg-yellow-500" },
    unhealthy: { bg: "bg-red-50", text: "text-red-700", dot: "bg-red-500" },
    connected: { bg: "bg-green-50", text: "text-green-700", dot: "bg-green-500" },
    disconnected: { bg: "bg-red-50", text: "text-red-700", dot: "bg-red-500" },
    storm: { bg: "bg-red-50", text: "text-red-700", dot: "bg-red-500" },
    ok: { bg: "bg-green-50", text: "text-green-700", dot: "bg-green-500" },
    warning: { bg: "bg-yellow-50", text: "text-yellow-700", dot: "bg-yellow-500" },
  };
  const c = cfg[status] ?? cfg.healthy;
  return (
    <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-semibold ${c.bg} ${c.text}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${c.dot}`} />
      {label ?? status}
    </span>
  );
}

// ── Main Component ───────────────────────────────────────────────

export function DiagnosticsPanel() {
  const [activeTab, setActiveTab] = useState<DiagTab>("overview");
  const [correlationSearch, setCorrelationSearch] = useState("");

  const { data: diagnostics, isLoading: diagLoading } = useSystemDiagnostics();
  const { data: eventChain, isLoading: chainLoading } = useEventChain(
    correlationSearch.length > 5 ? correlationSearch : null,
  );
  const { data: outbox, isLoading: outboxLoading } = useOutboxDiagnostics();
  const { data: workers, isLoading: workersLoading } = useWorkerDiagnostics();

  const tabs: { id: DiagTab; label: string; icon: React.ReactNode }[] = [
    { id: "overview", label: "Overview", icon: <Activity className="w-4 h-4" /> },
    { id: "event-trace", label: "Event Trace", icon: <History className="w-4 h-4" /> },
    { id: "outbox", label: "Outbox", icon: <Archive className="w-4 h-4" /> },
    { id: "workers", label: "Workers", icon: <Server className="w-4 h-4" /> },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-bold text-navy-900">Operational Diagnostics</h2>
          <p className="text-xs text-gray-500 mt-0.5">
            Real-time system observability and event diagnostics
          </p>
        </div>
        {diagnostics && (
          <span className="text-[10px] text-gray-400 tabular-nums">
            Updated {new Date(diagnostics.timestamp).toLocaleTimeString()}
          </span>
        )}
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

      {/* ── OVERVIEW TAB ── */}
      {activeTab === "overview" && (
        <div className="space-y-4">
          {diagLoading ? (
            <div className="flex justify-center py-12"><Loader2 className="w-6 h-6 text-gray-400 animate-spin" /></div>
          ) : diagnostics ? (
            <>
              {/* Key Metrics */}
              <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-6 gap-3">
                <StatCard
                  icon={<Wifi className="w-4 h-4" />}
                  label="WS Connections"
                  value={diagnostics.websocket.active_connections}
                  sub={`${diagnostics.websocket.tenant_count} tenants`}
                  color="from-purple-500 to-violet-600"
                />
                <StatCard
                  icon={<MessageSquare className="w-4 h-4" />}
                  label="WS Messages Sent"
                  value={diagnostics.websocket.messages_sent.toLocaleString()}
                  color="from-blue-500 to-indigo-600"
                />
                <StatCard
                  icon={<RefreshCw className="w-4 h-4" />}
                  label="Reconnect Storms"
                  value={Object.keys(diagnostics.reconnect_storms).length}
                  sub={Object.values(diagnostics.reconnect_storms).some((s) => s.storm_detected) ? "ACTIVE" : "None"}
                  color="from-red-500 to-rose-600"
                  bad={Object.values(diagnostics.reconnect_storms).some((s) => s.storm_detected)}
                />
                <StatCard
                  icon={<Archive className="w-4 h-4" />}
                  label="Dead-Letter Events"
                  value={diagnostics.prometheus.outbox_events_dead_letter_total ?? 0}
                  color="from-amber-500 to-orange-600"
                  bad={(diagnostics.prometheus.outbox_events_dead_letter_total ?? 0) > 0}
                />
                <StatCard
                  icon={<Shield className="w-4 h-4" />}
                  label="Stale Events Rejected"
                  value={diagnostics.prometheus.stale_events_rejected_total ?? 0}
                  color="from-emerald-500 to-green-600"
                />
                <StatCard
                  icon={<Zap className="w-4 h-4" />}
                  label="Duplicate Suppressions"
                  value={diagnostics.prometheus.duplicate_invalidations_suppressed_total ?? 0}
                  color="from-cyan-500 to-teal-600"
                />
              </div>

              {/* Reconnect Storm Details */}
              {Object.keys(diagnostics.reconnect_storms).length > 0 && (
                <div>
                  <h3 className="text-xs font-semibold text-navy-900 mb-2">Reconnect Activity</h3>
                  <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
                    <div className="divide-y divide-gray-100">
                      {Object.entries(diagnostics.reconnect_storms).map(([tid, stats]) => (
                        <div key={tid} className="flex items-center justify-between px-4 py-2.5">
                          <div className="flex items-center gap-2">
                            <span className="text-xs font-medium text-navy-900">Tenant {tid}</span>
                            <StatusBadge
                              status={stats.storm_detected ? "storm" : "ok"}
                              label={stats.storm_detected ? "Storm Detected" : "Normal"}
                            />
                          </div>
                          <span className="text-xs text-gray-500 tabular-nums">
                            {stats.recent_reconnects} reconnects (60s window)
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}

              {/* WebSocket Subscriptions */}
              {diagnostics.websocket.subscriptions &&
                Object.keys(diagnostics.websocket.subscriptions).length > 0 && (
                <div>
                  <h3 className="text-xs font-semibold text-navy-900 mb-2">Active Subscriptions</h3>
                  <div className="flex flex-wrap gap-2">
                    {Object.entries(diagnostics.websocket.subscriptions).map(([topic, count]) => (
                      <span
                        key={topic}
                        className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[10px] font-medium bg-indigo-50 text-indigo-700"
                      >
                        {topic}
                        <span className="bg-indigo-200 text-indigo-800 rounded-full px-1.5 py-0.5 text-[9px]">
                          {count}
                        </span>
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Prometheus Metrics Summary */}
              <div>
                <h3 className="text-xs font-semibold text-navy-900 mb-2">Prometheus Counters</h3>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                  {Object.entries(diagnostics.prometheus).map(([name, value]) => (
                    <div key={name} className="bg-white rounded-lg border border-gray-200 p-2.5">
                      <p className="text-[10px] text-gray-500 truncate max-w-[160px]" title={name}>
                        {name.replace(/_/g, " ")}
                      </p>
                      <p className="text-sm font-bold text-navy-900 tabular-nums">
                        {typeof value === "number" ? value.toLocaleString() : String(value)}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            </>
          ) : (
            <div className="flex flex-col items-center py-12 text-center">
              <Activity className="w-10 h-10 text-gray-300 mb-3" />
              <p className="text-sm text-gray-500">Unable to load diagnostics data</p>
            </div>
          )}
        </div>
      )}

      {/* ── EVENT TRACE TAB ── */}
      {activeTab === "event-trace" && (
        <div className="space-y-4">
          <div className="flex items-center gap-3">
            <div className="relative flex-1 max-w-md">
              <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-gray-400" />
              <input
                type="text"
                value={correlationSearch}
                onChange={(e) => setCorrelationSearch(e.target.value)}
                placeholder="Enter correlation ID to trace..."
                className="w-full pl-8 pr-3 py-1.5 text-xs border border-gray-300 rounded-lg focus:border-blue-500 focus:outline-none"
              />
            </div>
            <span className="text-[10px] text-gray-400">
              {eventChain ? `${eventChain.length} events` : ""}
            </span>
          </div>

          {chainLoading ? (
            <div className="flex justify-center py-12"><Loader2 className="w-6 h-6 text-gray-400 animate-spin" /></div>
          ) : eventChain && eventChain.length > 0 ? (
            <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
              <div className="divide-y divide-gray-100">
                {eventChain.map((event, idx) => (
                  <div key={event.event_id} className="px-4 py-3 hover:bg-gray-50">
                    <div className="flex items-center gap-3">
                      {/* Sequence indicator */}
                      <div className="flex flex-col items-center gap-0.5">
                        <div className={`w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-bold text-white ${
                          event.delivery_state === "dead_letter" ? "bg-red-500" :
                          event.delivery_state === "delivered" || event.delivery_state === "acknowledged" ? "bg-green-500" :
                          event.delivery_state === "failed" ? "bg-amber-500" : "bg-gray-400"
                        }`}>
                          {event.sequence_id}
                        </div>
                        {idx < eventChain.length - 1 && (
                          <div className="w-px h-4 bg-gray-200" />
                        )}
                      </div>
                      {/* Event details */}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-medium text-navy-900">{event.event_type}</span>
                          <StatusBadge
                            status={
                              event.delivery_state === "dead_letter" ? "unhealthy" :
                              event.delivery_state === "delivered" || event.delivery_state === "acknowledged" ? "healthy" :
                              event.delivery_state === "failed" ? "degraded" : "warning"
                            }
                            label={event.delivery_state}
                          />
                          <span className="text-[10px] text-gray-400">v{event.event_version}</span>
                        </div>
                        <div className="flex items-center gap-3 text-[10px] text-gray-500 mt-0.5">
                          <span>Attempts: {event.delivery_attempts}</span>
                          {event.delivered_at && <span>Delivered: {new Date(event.delivered_at).toLocaleTimeString()}</span>}
                          {event.last_error && (
                            <span className="text-red-500" title={event.last_error}>Error: {event.last_error.slice(0, 50)}</span>
                          )}
                          {event.dead_letter_reason && (
                            <span className="text-red-600 font-medium">Dead: {event.dead_letter_reason}</span>
                          )}
                        </div>
                      </div>
                      <ChevronRight className="w-3.5 h-3.5 text-gray-300" />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ) : correlationSearch.length > 5 ? (
            <div className="flex flex-col items-center py-12 text-center">
              <Search className="w-10 h-10 text-gray-300 mb-3" />
              <p className="text-sm text-gray-500">No events found for this correlation ID</p>
            </div>
          ) : (
            <div className="flex flex-col items-center py-12 text-center">
              <History className="w-10 h-10 text-gray-300 mb-3" />
              <p className="text-sm text-gray-500">Enter a correlation ID to trace event chains</p>
            </div>
          )}
        </div>
      )}

      {/* ── OUTBOX TAB ── */}
      {activeTab === "outbox" && (
        <div className="space-y-4">
          {outboxLoading ? (
            <div className="flex justify-center py-12"><Loader2 className="w-6 h-6 text-gray-400 animate-spin" /></div>
          ) : outbox ? (
            <>
              {/* Counts */}
              <div className="grid grid-cols-3 sm:grid-cols-6 gap-2">
                {Object.entries(outbox.counts).map(([state, count]) => (
                  <div key={state} className={`bg-white rounded-lg border p-3 text-center ${
                    state === "dead_letter" && count > 0 ? "border-red-200 bg-red-50" :
                    state === "pending" && count > 0 ? "border-amber-200 bg-amber-50" :
                    "border-gray-200"
                  }`}>
                    <p className="text-lg font-bold text-navy-900 tabular-nums">{count as number}</p>
                    <p className="text-[10px] text-gray-500 capitalize">{state.replace(/_/g, " ")}</p>
                  </div>
                ))}
              </div>

              {/* Dead Letters */}
              {outbox.dead_letters.length > 0 && (
                <div>
                  <h3 className="text-xs font-semibold text-navy-900 mb-2 flex items-center gap-1.5">
                    <AlertTriangle className="w-3.5 h-3.5 text-red-500" />
                    Dead-Letter Events ({outbox.dead_letters.length})
                  </h3>
                  <div className="bg-white rounded-xl border border-red-200 shadow-sm overflow-hidden">
                    <div className="divide-y divide-red-100">
                      {outbox.dead_letters.map((dl) => (
                        <div key={dl.event_id} className="px-4 py-2.5 hover:bg-red-50">
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-2">
                              <span className="text-xs font-medium text-navy-900">{dl.event_type}</span>
                              <span className="text-[10px] text-gray-400">{dl.event_id.slice(0, 8)}...</span>
                            </div>
                            <span className="text-[10px] text-gray-500 tabular-nums">
                              {dl.delivery_attempts} attempts
                            </span>
                          </div>
                          <p className="text-[10px] text-red-600 mt-0.5 truncate" title={dl.dead_letter_reason ?? ""}>
                            {dl.dead_letter_reason ?? dl.last_error ?? "Unknown"}
                          </p>
                          {dl.correlation_id && (
                            <p className="text-[9px] text-gray-400 mt-0.5">Correlation: {dl.correlation_id}</p>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}

              {/* Recent Events */}
              {outbox.recent_events.length > 0 && (
                <div>
                  <h3 className="text-xs font-semibold text-navy-900 mb-2">Recent Events</h3>
                  <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
                    <div className="divide-y divide-gray-100 max-h-64 overflow-y-auto">
                      {outbox.recent_events.map((ev) => (
                        <div key={ev.event_id} className="px-4 py-2 flex items-center justify-between hover:bg-gray-50">
                          <div className="flex items-center gap-2">
                            <span className="text-xs text-navy-900">{ev.event_type}</span>
                            <StatusBadge
                              status={
                                ev.delivery_state === "dead_letter" ? "unhealthy" :
                                ev.delivery_state === "delivered" ? "healthy" :
                                ev.delivery_state === "pending" ? "warning" : "degraded"
                              }
                              label={ev.delivery_state}
                            />
                          </div>
                          <div className="flex items-center gap-3 text-[10px] text-gray-400">
                            <span>{ev.delivery_attempts} attempts</span>
                            {ev.created_at && <span>{new Date(ev.created_at).toLocaleTimeString()}</span>}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}
            </>
          ) : (
            <div className="flex flex-col items-center py-12 text-center">
              <Archive className="w-10 h-10 text-gray-300 mb-3" />
              <p className="text-sm text-gray-500">Unable to load outbox diagnostics</p>
            </div>
          )}
        </div>
      )}

      {/* ── WORKERS TAB ── */}
      {activeTab === "workers" && (
        <div className="space-y-4">
          {workersLoading ? (
            <div className="flex justify-center py-12"><Loader2 className="w-6 h-6 text-gray-400 animate-spin" /></div>
          ) : workers ? (
            <>
              {/* Queue Depths */}
              <div>
                <h3 className="text-xs font-semibold text-navy-900 mb-2">Queue Depths</h3>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                  {Object.entries(workers.queues).map(([name, depth]) => (
                    <div key={name} className={`bg-white rounded-lg border p-3 ${
                      (depth as number) > 10 ? "border-red-200 bg-red-50" :
                      (depth as number) > 0 ? "border-amber-200 bg-amber-50" :
                      "border-gray-200"
                    }`}>
                      <p className="text-[10px] text-gray-500 capitalize">{name}</p>
                      <p className="text-lg font-bold text-navy-900 tabular-nums">{depth as number}</p>
                    </div>
                  ))}
                </div>
              </div>

              {/* Active Workers */}
              {Object.keys(workers.workers).length > 0 && (
                <div>
                  <h3 className="text-xs font-semibold text-navy-900 mb-2">
                    Active Workers ({Object.keys(workers.workers).length})
                  </h3>
                  <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
                    <div className="divide-y divide-gray-100">
                      {Object.entries(workers.workers).map(([id, w]) => (
                        <div key={id} className="px-4 py-2.5 flex items-center justify-between hover:bg-gray-50">
                          <div className="flex items-center gap-2">
                            <div className={`w-2 h-2 rounded-full ${
                              w.status === "active" ? "bg-green-500" :
                              w.status === "idle" ? "bg-yellow-500" : "bg-gray-400"
                            }`} />
                            <span className="text-xs font-medium text-navy-900">{id}</span>
                            <span className="text-[10px] text-gray-400 bg-gray-100 rounded px-1.5 py-0.5">{w.queue}</span>
                          </div>
                          <div className="flex items-center gap-4 text-[10px] text-gray-500">
                            <span className="tabular-nums">{w.tasks_completed} completed</span>
                            <span className={`tabular-nums ${w.tasks_failed > 0 ? "text-red-500 font-medium" : ""}`}>
                              {w.tasks_failed} failed
                            </span>
                            {w.last_heartbeat && (
                              <span>{new Date(w.last_heartbeat).toLocaleTimeString()}</span>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}

              {/* Stuck Jobs */}
              {Object.keys(workers.stuck_jobs).length > 0 && (
                <div>
                  <h3 className="text-xs font-semibold text-navy-900 mb-2 flex items-center gap-1.5">
                    <AlertTriangle className="w-3.5 h-3.5 text-amber-500" />
                    Stuck Jobs (24h)
                  </h3>
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                    {Object.entries(workers.stuck_jobs).map(([queue, count]) => (
                      <div key={queue} className="bg-white rounded-lg border border-amber-200 p-3">
                        <p className="text-[10px] text-gray-500 capitalize">{queue}</p>
                        <p className="text-lg font-bold text-red-600 tabular-nums">{count as number}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {Object.keys(workers.workers).length === 0 && Object.keys(workers.queues).length === 0 && (
                <div className="flex flex-col items-center py-12 text-center">
                  <Server className="w-10 h-10 text-gray-300 mb-3" />
                  <p className="text-sm text-gray-500">No worker data available</p>
                  <p className="text-[10px] text-gray-400 mt-1">Workers may not have reported heartbeats yet</p>
                </div>
              )}
            </>
          ) : (
            <div className="flex flex-col items-center py-12 text-center">
              <Server className="w-10 h-10 text-gray-300 mb-3" />
              <p className="text-sm text-gray-500">Unable to load worker diagnostics</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

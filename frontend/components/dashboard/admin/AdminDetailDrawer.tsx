"use client";

import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X, User, Activity, Shield, FileSearch, Lock, Brain, Link, Clock, Calendar, CheckCircle, XCircle } from "lucide-react";
import type { AdminUser } from "./types";

type TabId = "overview" | "activity" | "permissions" | "audit" | "security" | "ai" | "dependencies" | "events";

function TabBtn({ label, icon, active, onClick }: { label: string; icon: React.ReactNode; active: boolean; onClick: () => void }) {
  return (
    <button onClick={onClick} className={`flex items-center gap-1 px-2.5 py-1.5 text-[10px] font-medium rounded-md whitespace-nowrap transition-all ${active ? "bg-navy-700 text-white shadow-sm" : "text-gray-500 hover:text-gray-700 hover:bg-gray-100"}`}>
      {icon}{label}
    </button>
  );
}

interface DrawerProps {
  user: AdminUser | null;
  onClose: () => void;
}

export function AdminDetailDrawer({ user, onClose }: DrawerProps) {
  const [tab, setTab] = useState<TabId>("overview");

  return (
    <AnimatePresence>
      {user && (
        <>
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="fixed inset-0 bg-black/20 z-40" onClick={onClose} />
          <motion.div initial={{ opacity: 0, x: 380 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: 380 }}
            transition={{ type: "spring", damping: 25, stiffness: 250 }}
            className="fixed right-0 top-0 bottom-0 w-[480px] bg-white border-l border-gray-200 shadow-xl z-50 flex flex-col">
            <div className="flex items-center justify-between px-5 py-4 border-b border-gray-200">
              <div className="flex items-center gap-2 min-w-0">
                <div className="w-8 h-8 rounded-full bg-navy-100 flex items-center justify-center"><User className="w-4 h-4 text-navy-600" /></div>
                <div className="min-w-0"><h3 className="text-sm font-semibold text-navy-900 truncate">{user.name}</h3><p className="text-[10px] text-gray-500">{user.email} • {user.id}</p></div>
              </div>
              <button onClick={onClose} className="p-1 rounded hover:bg-gray-100 text-gray-400"><X className="w-4 h-4" /></button>
            </div>
            <div className="px-4 py-2 border-b border-gray-100 flex gap-1 overflow-x-auto">
              <TabBtn label="Overview" icon={<User className="w-3 h-3" />} active={tab === "overview"} onClick={() => setTab("overview")} />
              <TabBtn label="Activity" icon={<Activity className="w-3 h-3" />} active={tab === "activity"} onClick={() => setTab("activity")} />
              <TabBtn label="Permissions" icon={<Shield className="w-3 h-3" />} active={tab === "permissions"} onClick={() => setTab("permissions")} />
              <TabBtn label="Audit" icon={<FileSearch className="w-3 h-3" />} active={tab === "audit"} onClick={() => setTab("audit")} />
              <TabBtn label="Security" icon={<Lock className="w-3 h-3" />} active={tab === "security"} onClick={() => setTab("security")} />
              <TabBtn label="AI" icon={<Brain className="w-3 h-3" />} active={tab === "ai"} onClick={() => setTab("ai")} />
              <TabBtn label="Events" icon={<Clock className="w-3 h-3" />} active={tab === "events"} onClick={() => setTab("events")} />
            </div>
            <div className="flex-1 overflow-y-auto p-5 space-y-4">
              {tab === "overview" && <OverviewTab u={user} />}
              {tab === "activity" && <ActivityTab />}
              {tab === "permissions" && <PermissionsTab u={user} />}
              {tab === "audit" && <AuditTab />}
              {tab === "security" && <SecurityTab u={user} />}
              {tab === "ai" && <AiTab />}
              {tab === "events" && <EventsTab />}
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}

function OverviewTab({ u }: { u: AdminUser }) {
  const MetaRow = ({ label, value, icon }: { label: string; value: string | React.ReactNode; icon?: React.ReactNode }) => (
    <div className="flex items-center justify-between py-1.5"><span className="text-[11px] text-gray-500 flex items-center gap-1.5">{icon}{label}</span><span className="text-[11px] font-medium text-gray-800">{value}</span></div>
  );
  return (
    <div className="space-y-4">
      <div className="p-3 bg-navy-50 rounded-lg border border-navy-100">
        <div className="flex items-center gap-1.5 mb-1.5"><User className="w-3.5 h-3.5 text-navy-600" /><span className="text-[10px] font-semibold text-navy-700 uppercase">User Summary</span></div>
        <p className="text-[11px] text-gray-700 leading-relaxed">{u.name} is a {u.role} in the {u.department} department. Account created {new Date(u.created).toLocaleDateString()}. {u.mfaEnabled ? "MFA enabled." : "MFA not enabled."} {u.ssoConnected ? "SSO connected." : "SSO not configured."}</p>
      </div>
      <div className="bg-gray-50 rounded-lg p-3 space-y-0.5 divide-y divide-gray-100">
        <MetaRow label="Name" value={u.name} icon={<User className="w-3 h-3" />} />
        <MetaRow label="Email" value={u.email} />
        <MetaRow label="Role" value={u.role} icon={<Shield className="w-3 h-3" />} />
        <MetaRow label="Status" value={u.status} />
        <MetaRow label="Department" value={u.department} />
        <MetaRow label="MFA" value={u.mfaEnabled ? "Enabled" : "Disabled"} />
        <MetaRow label="SSO" value={u.ssoConnected ? "Connected" : "Not configured"} />
        <MetaRow label="Logins" value={u.loginCount.toString()} />
        <MetaRow label="Last Active" value={formatTimeAgo(u.lastActive)} icon={<Clock className="w-3 h-3" />} />
        <MetaRow label="Last IP" value={u.lastIp} icon={<Lock className="w-3 h-3" />} />
        <MetaRow label="Created" value={new Date(u.created).toLocaleDateString()} icon={<Calendar className="w-3 h-3" />} />
      </div>
    </div>
  );
}

function ActivityTab() {
  const activities = [
    { action: "Logged in from new IP", time: "2h ago" },
    { action: "Reviewed contract CON-2026005", time: "4h ago" },
    { action: "Approved workflow WF-2026003", time: "6h ago" },
    { action: "Exported risk report", time: "1d ago" },
    { action: "Updated user profile", time: "3d ago" },
  ];
  return (
    <div className="space-y-2">
      <p className="text-[10px] font-semibold text-gray-500 uppercase mb-2">Recent Activity</p>
      {activities.map((a, i) => (
        <div key={i} className="flex items-start gap-2 p-2 bg-white border border-gray-100 rounded-lg">
          <div className="w-2 h-2 rounded-full bg-navy-400 mt-1.5 flex-shrink-0" />
          <div><p className="text-[11px] text-gray-800">{a.action}</p><p className="text-[9px] text-gray-400">{a.time}</p></div>
        </div>
      ))}
    </div>
  );
}

function PermissionsTab({ u }: { u: AdminUser }) {
  return (
    <div className="space-y-2">
      <p className="text-[10px] font-semibold text-gray-500 uppercase mb-2">Permissions ({u.permissions.length})</p>
      {u.permissions.map((p) => (
        <div key={p} className="flex items-center gap-2 p-2 bg-white border border-gray-100 rounded-lg">
          <CheckCircle className="w-3.5 h-3.5 text-green-500" />
          <span className="text-[11px] text-gray-700 font-mono">{p}</span>
        </div>
      ))}
      <div className="mt-3">
        <p className="text-[10px] font-semibold text-gray-500 uppercase mb-2">Groups ({u.groups.length})</p>
        {u.groups.map((g) => (
          <span key={g} className="text-[10px] px-1.5 py-0.5 rounded bg-navy-50 text-navy-700 mr-1">{g}</span>
        ))}
      </div>
    </div>
  );
}

function AuditTab() {
  const entries = [
    { action: "User created", by: "Admin", time: "2026-01-15" },
    { action: "Role assigned: Legal Counsel", by: "Admin", time: "2026-01-15" },
    { action: "MFA enabled", by: "User", time: "2026-02-20" },
    { action: "SSO connected", by: "User", time: "2026-03-10" },
    { action: "Password changed", by: "User", time: "2026-04-05" },
  ];
  return (
    <div className="space-y-1.5">
      <p className="text-[10px] font-semibold text-gray-500 uppercase mb-2">Audit Trail</p>
      {entries.map((e, i) => (
        <div key={i} className="flex items-start gap-2 p-2 bg-white border border-gray-100 rounded-lg">
          <div className="w-2 h-2 rounded-full bg-navy-400 mt-1.5 flex-shrink-0" />
          <div><p className="text-[11px] text-gray-800">{e.action}</p><p className="text-[9px] text-gray-400">{e.by} • {e.time}</p></div>
        </div>
      ))}
    </div>
  );
}

function SecurityTab({ u }: { u: AdminUser }) {
  return (
    <div className="space-y-3">
      <div className="p-3 bg-white border border-gray-200 rounded-lg space-y-2">
        <div className="flex items-center justify-between"><span className="text-[11px] text-gray-600">Multi-Factor Auth</span>{u.mfaEnabled ? <span className="text-[10px] font-medium text-green-600 bg-green-50 px-1.5 py-0.5 rounded-full">Enabled</span> : <span className="text-[10px] font-medium text-red-600 bg-red-50 px-1.5 py-0.5 rounded-full">Disabled</span>}</div>
        <div className="flex items-center justify-between"><span className="text-[11px] text-gray-600">SSO Connection</span>{u.ssoConnected ? <span className="text-[10px] font-medium text-green-600 bg-green-50 px-1.5 py-0.5 rounded-full">Connected</span> : <span className="text-[10px] font-medium text-orange-600 bg-orange-50 px-1.5 py-0.5 rounded-full">Not configured</span>}</div>
        <div className="flex items-center justify-between"><span className="text-[11px] text-gray-600">Session Timeout</span><span className="text-[10px] text-gray-700">24 hours</span></div>
        <div className="flex items-center justify-between"><span className="text-[11px] text-gray-600">Last IP</span><span className="text-[10px] font-mono text-gray-700">{u.lastIp}</span></div>
        <div className="flex items-center justify-between"><span className="text-[11px] text-gray-600">Login Count</span><span className="text-[10px] text-gray-700">{u.loginCount}</span></div>
      </div>
    </div>
  );
}

function AiTab() {
  return (
    <div className="space-y-3">
      <div className="p-3 bg-purple-50 rounded-lg border border-purple-100">
        <p className="text-[10px] font-semibold text-purple-700 uppercase mb-1">AI Usage Summary</p>
        <div className="space-y-1.5">
          {[
            { label: "Total AI Queries", value: "342" },
            { label: "Avg Confidence", value: "91%" },
            { label: "Flagged Queries", value: "3" },
            { label: "Preferred Model", value: "gpt-4o" },
          ].map((item) => (
            <div key={item.label} className="flex justify-between text-xs"><span className="text-gray-600">{item.label}</span><span className="font-medium text-gray-800">{item.value}</span></div>
          ))}
        </div>
      </div>
    </div>
  );
}

function EventsTab() {
  const events = [
    { event: "System login", time: "2h ago", type: "auth" },
    { event: "Contract review completed", time: "4h ago", type: "workflow" },
    { event: "Risk analysis requested", time: "6h ago", type: "ai" },
    { event: "Export performed", time: "1d ago", type: "data" },
    { event: "Profile updated", time: "3d ago", type: "user" },
  ];
  return (
    <div className="space-y-1.5">
      <p className="text-[10px] font-semibold text-gray-500 uppercase mb-2">System Events</p>
      {events.map((e, i) => (
        <div key={i} className="flex items-start gap-2 p-2 bg-white border border-gray-100 rounded-lg">
          <div className="w-2 h-2 rounded-full bg-navy-400 mt-1.5 flex-shrink-0" />
          <div><p className="text-[11px] text-gray-800">{e.event}</p><p className="text-[9px] text-gray-400">{e.type} • {e.time}</p></div>
        </div>
      ))}
    </div>
  );
}

function formatTimeAgo(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const hrs = Math.floor(diff / 3600000);
  if (hrs < 1) return "just now"; if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

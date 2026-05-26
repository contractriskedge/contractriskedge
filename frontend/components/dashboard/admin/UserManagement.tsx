"use client";

import React, { useState } from "react";
import { motion } from "framer-motion";
import { Search, ChevronLeft, ChevronRight, ArrowUpDown, User, Shield, MoreHorizontal, CheckCircle, XCircle } from "lucide-react";
import type { AdminUser, RoleDefinition } from "./types";

interface UserManagementProps {
  users: AdminUser[];
  roles: RoleDefinition[];
  onSelectUser: (u: AdminUser) => void;
}

export function UserManagement({ users, roles, onSelectUser }: UserManagementProps) {
  const [search, setSearch] = useState("");
  const [roleFilter, setRoleFilter] = useState("all");
  const [statusFilter, setStatusFilter] = useState("all");
  const [page, setPage] = useState(0);
  const pageSize = 10;

  const filtered = users.filter((u) => {
    const matchSearch = u.name.toLowerCase().includes(search.toLowerCase()) || u.email.toLowerCase().includes(search.toLowerCase());
    const matchRole = roleFilter === "all" || u.role === roleFilter;
    const matchStatus = statusFilter === "all" || u.status === statusFilter;
    return matchSearch && matchRole && matchStatus;
  });

  const totalPages = Math.ceil(filtered.length / pageSize);
  const pageData = filtered.slice(page * pageSize, (page + 1) * pageSize);

  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
      <div className="px-4 py-3 border-b border-gray-100 flex items-center justify-between">
        <div><h3 className="text-xs font-semibold text-navy-900">User Management</h3><p className="text-[10px] text-gray-500">{filtered.length} users</p></div>
        <div className="flex items-center gap-2">
          <select value={roleFilter} onChange={(e) => { setRoleFilter(e.target.value); setPage(0); }} className="text-[10px] border border-gray-200 rounded-md px-2 py-1.5 text-gray-600 bg-white" aria-label="Role">
            <option value="all">All Roles</option>
            {roles.map((r) => <option key={r.id} value={r.name}>{r.name}</option>)}
          </select>
          <select value={statusFilter} onChange={(e) => { setStatusFilter(e.target.value); setPage(0); }} className="text-[10px] border border-gray-200 rounded-md px-2 py-1.5 text-gray-600 bg-white" aria-label="Status">
            <option value="all">All Status</option>
            <option value="active">Active</option><option value="inactive">Inactive</option><option value="suspended">Suspended</option>
          </select>
          <div className="relative w-44"><Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3 h-3 text-gray-400" />
            <input value={search} onChange={(e) => { setSearch(e.target.value); setPage(0); }} placeholder="Search users..." className="w-full text-[11px] border border-gray-200 rounded-lg pl-7 pr-3 py-1.5 focus:border-navy-400 focus:ring-1 focus:ring-navy-400" /></div>
        </div>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead className="bg-gray-50 border-b border-gray-100">
            <tr>
              <th className="text-left py-2.5 px-3 text-[10px] font-semibold text-gray-500 uppercase">User</th>
              <th className="text-left py-2.5 px-3 text-[10px] font-semibold text-gray-500 uppercase">Role</th>
              <th className="text-left py-2.5 px-3 text-[10px] font-semibold text-gray-500 uppercase">Status</th>
              <th className="text-left py-2.5 px-3 text-[10px] font-semibold text-gray-500 uppercase">MFA</th>
              <th className="text-left py-2.5 px-3 text-[10px] font-semibold text-gray-500 uppercase">SSO</th>
              <th className="text-left py-2.5 px-3 text-[10px] font-semibold text-gray-500 uppercase">Department</th>
              <th className="text-left py-2.5 px-3 text-[10px] font-semibold text-gray-500 uppercase">Last Active</th>
              <th className="text-left py-2.5 px-3 text-[10px] font-semibold text-gray-500 uppercase">Logins</th>
              <th className="py-2.5 px-3 w-8" />
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-50">
            {pageData.map((u, i) => (
              <motion.tr key={u.id} initial={{ opacity: 0, y: 2 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.02 }}
                className="hover:bg-navy-50/40 transition-colors cursor-pointer" onClick={() => onSelectUser(u)}>
                <td className="py-2.5 px-3">
                  <div className="flex items-center gap-2">
                    <div className="w-7 h-7 rounded-full bg-navy-100 flex items-center justify-center"><User className="w-3.5 h-3.5 text-navy-600" /></div>
                    <div><p className="text-[11px] font-medium text-gray-800">{u.name}</p><p className="text-[9px] text-gray-400">{u.email}</p></div>
                  </div>
                </td>
                <td className="py-2.5 px-3"><span className="text-[10px] px-1.5 py-0.5 rounded bg-navy-50 text-navy-700">{u.role}</span></td>
                <td className="py-2.5 px-3">
                  <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded-full ${u.status === "active" ? "bg-green-50 text-green-700" : u.status === "inactive" ? "bg-gray-100 text-gray-600" : "bg-red-50 text-red-700"}`}>{u.status}</span>
                </td>
                <td className="py-2.5 px-3">{u.mfaEnabled ? <CheckCircle className="w-3.5 h-3.5 text-green-500" /> : <XCircle className="w-3.5 h-3.5 text-gray-300" />}</td>
                <td className="py-2.5 px-3">{u.ssoConnected ? <CheckCircle className="w-3.5 h-3.5 text-green-500" /> : <XCircle className="w-3.5 h-3.5 text-gray-300" />}</td>
                <td className="py-2.5 px-3 text-gray-600 text-[10px]">{u.department}</td>
                <td className="py-2.5 px-3 text-gray-400 text-[10px]">{formatTimeAgo(u.lastActive)}</td>
                <td className="py-2.5 px-3 text-gray-500 text-[10px] tabular-nums">{u.loginCount}</td>
                <td className="py-2.5 px-3"><MoreHorizontal className="w-3.5 h-3.5 text-gray-300 opacity-0 group-hover:opacity-100" /></td>
              </motion.tr>
            ))}
          </tbody>
        </table>
      </div>
      {filtered.length > 0 && (
        <div className="px-4 py-2 border-t border-gray-100 flex items-center justify-between">
          <span className="text-[10px] text-gray-500">Showing {page * pageSize + 1}–{Math.min((page + 1) * pageSize, filtered.length)} of {filtered.length}</span>
          <div className="flex items-center gap-1">
            <button onClick={() => setPage(Math.max(0, page - 1))} disabled={page === 0} className="p-1 rounded hover:bg-gray-100 disabled:opacity-30"><ChevronLeft className="w-3.5 h-3.5" /></button>
            {Array.from({ length: totalPages }, (_, i) => (
              <button key={i} onClick={() => setPage(i)} className={`w-5 h-5 text-[10px] rounded transition-colors ${i === page ? "bg-navy-700 text-white" : "text-gray-500 hover:bg-gray-100"}`}>{i + 1}</button>
            ))}
            <button onClick={() => setPage(Math.min(totalPages - 1, page + 1))} disabled={page >= totalPages - 1} className="p-1 rounded hover:bg-gray-100 disabled:opacity-30"><ChevronRight className="w-3.5 h-3.5" /></button>
          </div>
        </div>
      )}
    </div>
  );
}

function formatTimeAgo(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const hrs = Math.floor(diff / 3600000);
  if (hrs < 1) return "just now"; if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

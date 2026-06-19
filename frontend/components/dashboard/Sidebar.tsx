"use client";

import React from "react";
import { useAuth } from "@/components/auth/AuthProvider";
import {
  LayoutDashboard,
  TrendingUp,
  Scale,
  ShoppingCart,
  FileText,
  BarChart3,
  Settings,
  LogOut,
  ChevronLeft,
  ChevronRight,
  Shield,
  Share2,
  Workflow,
  ShieldAlert,
  BookOpen,
  Library,
  ClipboardCheck,
  GitMerge,
  Search,
  Upload,
  ShieldCheck,
  Eye,
  LayoutGrid,
  Briefcase,
  Users,
  FileCheck,
  Gavel,
  Building2,
  ScrollText,
  Network,
  Sliders,
  Cpu,
  ClipboardList,
  FileSearch,
  Activity,
} from "lucide-react";

type ViewType = "cfo" | "legal" | "procurement" | "contracts" | "benchmarks" | "settings" | "admin" | "relationships" | "workflows" | "contract-detail" | "clause-library" | "obligations" | "analytics" | "negotiation" | "search" | "ingestion" | "compliance" | "review" | "review-dashboard" | "executive-dashboard" | "policy" | "clause-intelligence" | "tenant-settings" | "executive-command-center" | "reviewer-operations" | "governance-dashboard" | "ai-operations-dashboard" | "workflow-intelligence-dashboard" | "command-center";

interface SidebarProps {
  activeView: ViewType;
  onViewChange: (view: ViewType) => void;
  collapsed: boolean;
  onToggle: () => void;
}

interface NavItem {
  id: ViewType;
  label: string;
  icon: React.ElementType;
  /** Optional permission required to see this nav item. Default: visible to all. */
  permission?: string | string[];
  /** If true (default for arrays), ALL permissions required. If false, ANY. */
  requireAll?: boolean;
}

interface NavGroup {
  label: string;
  items: NavItem[];
}

// Enterprise navigation — organized by operational domain.
// Items without a `permission` field are visible to all authenticated users.
// Items with a `permission` field are filtered based on the user's permissions.
const navGroups: NavGroup[] = [
  {
    label: "Contracts",
    items: [
      { id: "ingestion", label: "Ingestion", icon: Upload, permission: "contracts:write" },
      { id: "contracts", label: "Contracts", icon: FileText, permission: "contracts:read" },
      { id: "clause-library", label: "Clause Intelligence Center", icon: Library, permission: "contracts:read" },
      { id: "obligations", label: "Obligations", icon: ClipboardCheck, permission: "contracts:read" },
    ],
  },
  {
    label: "AI Review",
    items: [
      { id: "review-dashboard", label: "Review Dashboard", icon: ClipboardList, permission: "contracts:read" },
      { id: "review", label: "Review Queue", icon: Eye, permission: "contracts:read" },
      { id: "negotiation", label: "Negotiation", icon: GitMerge, permission: "contracts:read" },
      { id: "clause-intelligence", label: "Clause Intel", icon: Network, permission: "contracts:read" },
      { id: "policy", label: "Policy Engine", icon: ScrollText, permission: "contracts:read" },
    ],
  },
  {
    label: "Operations",
    items: [
      { id: "command-center", label: "Command Center", icon: LayoutDashboard, permission: "contracts:read" },
      { id: "activity-center", label: "Activity Center", icon: Activity, permission: "contracts:read" },
      { id: "reviewer-operations", label: "Reviewer Ops", icon: ClipboardCheck, permission: "workflows:read" },
      { id: "workflow-intelligence-dashboard", label: "Workflow Intel", icon: BarChart3, permission: "workflows:read" },
      { id: "search", label: "Search & Discovery", icon: Search, permission: "contracts:read" },
    ],
  },
  {
    label: "Analytics",
    items: [
      { id: "analytics", label: "Analytics", icon: TrendingUp, permission: "audit:read" },
      { id: "benchmarks", label: "Benchmarks", icon: BarChart3, permission: "benchmarks:read" },
      { id: "executive-dashboard", label: "Executive", icon: LayoutDashboard, permission: "contracts:read" },
    ],
  },
  {
    label: "Governance",
    items: [
      { id: "compliance", label: "Compliance", icon: ShieldCheck, permission: "contracts:read" },
      { id: "governance-dashboard", label: "Governance", icon: ShieldCheck, permission: "audit:read" },
      { id: "relationships", label: "Relationships", icon: Share2, permission: "contracts:read" },
      { id: "workflows", label: "Workflows", icon: Workflow, permission: "workflows:read" },
    ],
  },
  {
    label: "Administration",
    items: [
      {
        id: "admin",
        label: "Admin & Audit",
        icon: FileSearch,
        permission: ["admin:tenant", "audit:read"],
        requireAll: false,
      },
      { id: "settings", label: "Settings", icon: Settings, permission: "admin:tenant" },
      { id: "tenant-settings", label: "Tenant Config", icon: Sliders, permission: "admin:tenant" },
      { id: "ai-operations-dashboard", label: "AI Ops", icon: Cpu, permission: "ai:view" },
    ],
  },
];

export function Sidebar({ activeView, onViewChange, collapsed, onToggle }: SidebarProps) {
  const { hasPermission } = useAuth();

  // Filter nav items based on user permissions
  const filteredGroups = navGroups
    .map((group) => ({
      ...group,
      items: group.items.filter((item) => {
        if (!item.permission) return true;
        const perms = Array.isArray(item.permission) ? item.permission : [item.permission];
        return item.requireAll !== false
          ? perms.every((p) => hasPermission(p))
          : perms.some((p) => hasPermission(p));
      }),
    }))
    .filter((group) => group.items.length > 0);

  return (
    <aside
      className={`${
        collapsed ? "w-16" : "w-64"
      } bg-navy-900 text-white flex flex-col transition-all duration-200 ease-in-out flex-shrink-0`}
    >
      {/* Logo */}
      <div className={`h-16 flex items-center ${collapsed ? "justify-center" : "px-4"} border-b border-navy-700`}>
        <Shield className="w-7 h-7 text-gold-400 flex-shrink-0" />
        {!collapsed && (
          <span className="ml-3 font-bold text-sm whitespace-nowrap">
            ContractRisk<span className="text-gold-400">Edge</span>
          </span>
        )}
      </div>

      {/* Navigation */}
      <nav className="flex-1 py-2 px-2 overflow-y-auto space-y-3">
        {filteredGroups.map((group) => (
          <div key={group.label}>
            {!collapsed && (
              <div className="px-3 mb-1">
                <span className="text-[9px] font-semibold text-navy-400 uppercase tracking-widest">{group.label}</span>
              </div>
            )}
            <div className="space-y-0.5">
              {group.items.map((item) => {
                const Icon = item.icon;
                const isActive = activeView === item.id;
                return (
                  <button
                    key={item.id}
                    onClick={() => onViewChange(item.id)}
                    className={`w-full flex items-center ${
                      collapsed ? "justify-center" : "px-3"
                    } py-2 rounded-lg transition-colors duration-150 ${
                      isActive
                        ? "bg-navy-700 text-gold-400"
                        : "text-navy-300 hover:bg-navy-800 hover:text-white"
                    }`}
                    title={collapsed ? item.label : undefined}
                  >
                    <Icon className="w-4 h-4 flex-shrink-0" />
                    {!collapsed && <span className="ml-3 text-xs font-medium">{item.label}</span>}
                  </button>
                );
              })}
            </div>
          </div>
        ))}
      </nav>

      {/* Collapse Toggle */}
      <button
        onClick={onToggle}
        className="h-12 flex items-center justify-center border-t border-navy-700 text-navy-400 hover:text-white hover:bg-navy-800 transition-colors"
      >
        {collapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
      </button>
    </aside>
  );
}

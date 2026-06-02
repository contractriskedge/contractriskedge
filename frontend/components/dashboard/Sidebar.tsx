"use client";

import React from "react";
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
  PieChart,
  Users,
  FileCheck,
  Gavel,
  Building2,
  ScrollText,
  Network,
  Sliders,
  Cpu,
} from "lucide-react";

type ViewType = "portfolio" | "cfo" | "legal" | "procurement" | "contracts" | "benchmarks" | "settings" | "admin" | "relationships" | "workflows" | "contract-detail" | "clause-library" | "obligations" | "analytics" | "negotiation" | "search" | "ingestion" | "compliance" | "review" | "executive-dashboard" | "policy" | "clause-intelligence" | "tenant-settings" | "executive-command-center" | "reviewer-operations" | "governance-dashboard" | "ai-operations-dashboard" | "workflow-intelligence-dashboard" | "command-center";

interface SidebarProps {
  activeView: ViewType;
  onViewChange: (view: ViewType) => void;
  collapsed: boolean;
  onToggle: () => void;
}

// Enterprise navigation — organized by operational domain.
// Role-based access control is enforced at the API level, not in the UI.
const navGroups: { label: string; items: { id: ViewType; label: string; icon: React.ElementType }[] }[] = [
  {
    label: "Contracts",
    items: [
      { id: "ingestion", label: "Ingestion", icon: Upload },
      { id: "contracts", label: "Contracts", icon: FileText },
      { id: "clause-library", label: "Clause Library", icon: Library },
      { id: "obligations", label: "Obligations", icon: ClipboardCheck },
    ],
  },
  {
    label: "AI Review",
    items: [
      { id: "review", label: "Review Queue", icon: Eye },
      { id: "negotiation", label: "Negotiation", icon: GitMerge },
      { id: "clause-intelligence", label: "Clause Intel", icon: Network },
      { id: "policy", label: "Policy Engine", icon: ScrollText },
    ],
  },
  {
    label: "Operations",
    items: [
      { id: "command-center", label: "Command Center", icon: LayoutDashboard },
      { id: "reviewer-operations", label: "Reviewer Ops", icon: ClipboardCheck },
      { id: "workflow-intelligence-dashboard", label: "Workflow Intel", icon: BarChart3 },
      { id: "search", label: "Search & Discovery", icon: Search },
    ],
  },
  {
    label: "Analytics",
    items: [
      { id: "analytics", label: "Analytics", icon: TrendingUp },
      { id: "benchmarks", label: "Benchmarks", icon: BarChart3 },
      { id: "portfolio", label: "Portfolio", icon: PieChart },
      { id: "executive-dashboard", label: "Executive", icon: LayoutDashboard },
    ],
  },
  {
    label: "Governance",
    items: [
      { id: "compliance", label: "Compliance", icon: ShieldCheck },
      { id: "governance-dashboard", label: "Governance", icon: ShieldCheck },
      { id: "relationships", label: "Relationships", icon: Share2 },
      { id: "workflows", label: "Workflows", icon: Workflow },
    ],
  },
  {
    label: "Administration",
    items: [
      { id: "admin", label: "Admin Console", icon: ShieldAlert },
      { id: "settings", label: "Settings", icon: Settings },
      { id: "tenant-settings", label: "Tenant Config", icon: Sliders },
      { id: "ai-operations-dashboard", label: "AI Ops", icon: Cpu },
    ],
  },
];

export function Sidebar({ activeView, onViewChange, collapsed, onToggle }: SidebarProps) {
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
        {navGroups.map((group) => (
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

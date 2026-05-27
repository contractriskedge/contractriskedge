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

type ViewType = "portfolio" | "cfo" | "legal" | "procurement" | "contracts" | "benchmarks" | "settings" | "admin" | "relationships" | "workflows" | "contract-detail" | "clause-library" | "obligations" | "analytics" | "negotiation" | "search" | "ingestion" | "compliance" | "review" | "executive-dashboard" | "policy" | "clause-intelligence" | "tenant-settings" | "executive-command-center" | "reviewer-operations" | "governance-dashboard" | "ai-operations-dashboard" | "workflow-intelligence-dashboard";

interface SidebarProps {
  activeView: ViewType;
  onViewChange: (view: ViewType) => void;
  collapsed: boolean;
  onToggle: () => void;
}

// Full navigation with all enterprise workspaces.
// All items are shown to all users — role-based access control
// is enforced at the API level (backend permissions), not in the UI.
const navItems: { id: ViewType; label: string; icon: React.ElementType }[] = [
  // ── Core Workspaces ──
  { id: "ingestion", label: "Ingestion", icon: Upload },
  { id: "review", label: "Review", icon: Eye },
  { id: "search", label: "Search & Discovery", icon: Search },
  { id: "analytics", label: "Analytics", icon: TrendingUp },

  // ── Sprint 10 — Unified Dashboards ──
  { id: "executive-command-center", label: "Command Center", icon: LayoutDashboard },
  { id: "reviewer-operations", label: "Reviewer Operations", icon: ClipboardCheck },
  { id: "governance-dashboard", label: "Governance", icon: ShieldCheck },
  { id: "ai-operations-dashboard", label: "AI Operations", icon: Cpu },
  { id: "workflow-intelligence-dashboard", label: "Workflow Intel", icon: BarChart3 },

  // ── Enterprise Workspaces ──
  { id: "portfolio", label: "Portfolio Dashboard", icon: PieChart },
  { id: "executive-dashboard", label: "Executive Dashboard", icon: LayoutDashboard },
  { id: "cfo", label: "CFO Workspace", icon: Briefcase },
  { id: "legal", label: "Legal Workspace", icon: Gavel },
  { id: "procurement", label: "Procurement Workspace", icon: ShoppingCart },
  { id: "compliance", label: "Compliance Center", icon: ShieldCheck },

  // ── Advanced Modules ──
  { id: "contracts", label: "Contracts", icon: FileText },
  { id: "clause-library", label: "Clause Library", icon: Library },
  { id: "obligations", label: "Obligations", icon: ClipboardCheck },
  { id: "negotiation", label: "Negotiation", icon: GitMerge },
  { id: "workflows", label: "Workflows", icon: Workflow },
  { id: "benchmarks", label: "Benchmarks", icon: BarChart3 },
  { id: "relationships", label: "Relationship Graph", icon: Share2 },

  // ── Sprint 7 — Enterprise Intelligence ──
  { id: "policy", label: "Policy Engine", icon: ScrollText },
  { id: "clause-intelligence", label: "Clause Intelligence", icon: Network },
  { id: "tenant-settings", label: "Tenant Settings", icon: Sliders },

  // ── Administration ──
  { id: "admin", label: "Admin Console", icon: ShieldAlert },
  { id: "settings", label: "Settings", icon: Settings },
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
      <nav className="flex-1 py-4 space-y-1 px-2 overflow-y-auto">
        {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeView === item.id;
            return (
              <button
                key={item.id}
                onClick={() => onViewChange(item.id)}
                className={`w-full flex items-center ${
                  collapsed ? "justify-center" : "px-3"
                } py-2.5 rounded-lg transition-colors duration-150 ${
                  isActive
                    ? "bg-navy-700 text-gold-400"
                    : "text-navy-200 hover:bg-navy-800 hover:text-white"
                }`}
                title={collapsed ? item.label : undefined}
              >
                <Icon className="w-5 h-5 flex-shrink-0" />
                {!collapsed && <span className="ml-3 text-sm font-medium">{item.label}</span>}
              </button>
            );
          })}
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

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
} from "lucide-react";

type ViewType = "portfolio" | "cfo" | "legal" | "procurement" | "contracts" | "benchmarks" | "settings" | "admin" | "relationships" | "workflows" | "contract-detail" | "clause-library" | "obligations" | "analytics" | "negotiation" | "search" | "ingestion" | "compliance" | "review" | "executive-dashboard";

interface SidebarProps {
  activeView: ViewType;
  onViewChange: (view: ViewType) => void;
  collapsed: boolean;
  onToggle: () => void;
  userRole: string;
}

// Only modules with real backend API integration are shown.
// Non-integrated modules (CFO, Portfolio, Compliance, etc.) are hidden
// until they have real backend endpoints.
const navItems: { id: ViewType; label: string; icon: React.ElementType; roles: string[] }[] = [
  { id: "ingestion", label: "Ingestion", icon: Upload, roles: ["admin", "analyst"] },
  { id: "review", label: "Review", icon: Eye, roles: ["admin", "analyst"] },
  { id: "search", label: "Search & Discovery", icon: Search, roles: ["admin", "analyst", "viewer"] },
  { id: "analytics", label: "Analytics", icon: TrendingUp, roles: ["admin", "analyst", "viewer"] },
  { id: "admin", label: "Admin Console", icon: ShieldAlert, roles: ["admin"] },
];

export function Sidebar({ activeView, onViewChange, collapsed, onToggle, userRole }: SidebarProps) {
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
        {navItems
          .filter((item) => item.roles.includes(userRole) || userRole === "admin")
          .map((item) => {
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

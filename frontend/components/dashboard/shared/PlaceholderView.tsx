/**
 * PlaceholderView — Graceful placeholder for modules in development.
 *
 * Shows a clear, branded placeholder when a workspace is selected
 * but doesn't yet have full backend API integration. Includes the
 * module name, description, and development status.
 *
 * Usage:
 *   <PlaceholderView
 *     title="Compliance Center"
 *     description="Regulatory compliance tracking and audit readiness."
 *     icon="shield"
 *     status="In Development"
 *   />
 */

"use client";

import React from "react";
import {
  Shield,
  ShieldAlert,
  Library,
  ClipboardCheck,
  GitMerge,
  Workflow,
  FileText,
  BarChart3,
  Share2,
  Settings,
  LayoutDashboard,
  Briefcase,
  Gavel,
  ShoppingCart,
  PieChart,
  Eye,
  Search,
  Upload,
  TrendingUp,
  Building2,
  Construction,
} from "lucide-react";

const iconMap: Record<string, React.ElementType> = {
  shield: Shield,
  "shield-alert": ShieldAlert,
  library: Library,
  check: ClipboardCheck,
  "git-merge": GitMerge,
  workflow: Workflow,
  file: FileText,
  chart: BarChart3,
  share: Share2,
  settings: Settings,
  dashboard: LayoutDashboard,
  briefcase: Briefcase,
  gavel: Gavel,
  cart: ShoppingCart,
  pie: PieChart,
  eye: Eye,
  search: Search,
  upload: Upload,
  trending: TrendingUp,
  building: Building2,
};

interface Props {
  title: string;
  description: string;
  icon?: string;
  status?: "Coming Soon" | "In Development" | "Planned";
}

const statusStyles: Record<string, { bg: string; text: string; dot: string }> = {
  "Coming Soon": { bg: "bg-blue-50", text: "text-blue-700", dot: "bg-blue-500" },
  "In Development": { bg: "bg-amber-50", text: "text-amber-700", dot: "bg-amber-500" },
  Planned: { bg: "bg-gray-50", text: "text-gray-600", dot: "bg-gray-400" },
};

export function PlaceholderView({ title, description, icon = "shield", status = "Coming Soon" }: Props) {
  const Icon = iconMap[icon] ?? Shield;
  const statusStyle = statusStyles[status] ?? statusStyles["Coming Soon"];

  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] text-center px-6">
      {/* Icon */}
      <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-navy-50 to-navy-100 dark:from-navy-800 dark:to-navy-700 flex items-center justify-center mb-6 shadow-sm">
        <Construction className="w-10 h-10 text-navy-400 dark:text-navy-300" />
      </div>

      {/* Title */}
      <h2 className="text-xl font-bold text-navy-900 dark:text-white mb-2">{title}</h2>

      {/* Description */}
      <p className="text-sm text-gray-500 dark:text-gray-400 max-w-md mb-6">{description}</p>

      {/* Status Badge */}
      <div className={`inline-flex items-center gap-2 px-4 py-2 rounded-full text-xs font-medium ${statusStyle.bg} ${statusStyle.text}`}>
        <span className={`w-2 h-2 rounded-full ${statusStyle.dot}`} />
        {status}
      </div>

      {/* Feature List */}
      <div className="mt-8 grid grid-cols-1 sm:grid-cols-2 gap-3 max-w-lg w-full">
        {[
          { label: "Backend API", done: status === "Coming Soon" ? false : false },
          { label: "Database Schema", done: status === "Coming Soon" ? false : true },
          { label: "Frontend UI", done: false },
          { label: "Real-time Updates", done: false },
        ].map((feature) => (
          <div
            key={feature.label}
            className="flex items-center gap-2 px-3 py-2 rounded-lg bg-gray-50 dark:bg-navy-800 text-xs"
          >
            <div className={`w-2 h-2 rounded-full ${feature.done ? "bg-green-500" : "bg-gray-300 dark:bg-gray-600"}`} />
            <span className={feature.done ? "text-gray-700 dark:text-gray-300" : "text-gray-400 dark:text-gray-500"}>
              {feature.label}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

/**
 * CollapsibleSection — A collapsible container for drawer panels.
 *
 * Reduces visual load by letting users expand/collapse sections
 * such as Findings, Obligations, Timeline, and Metadata.
 *
 * Usage:
 *   <CollapsibleSection title="Findings" icon={FileText} defaultOpen>
 *     ...content...
 *   </CollapsibleSection>
 */

"use client";

import React, { useState } from "react";
import { ChevronDown, ChevronRight, type LucideIcon } from "lucide-react";

interface CollapsibleSectionProps {
  title: string;
  icon?: LucideIcon;
  defaultOpen?: boolean;
  badge?: string | number;
  badgeColor?: string;
  children: React.ReactNode;
  className?: string;
}

export function CollapsibleSection({
  title,
  icon: Icon,
  defaultOpen = true,
  badge,
  badgeColor,
  children,
  className = "",
}: CollapsibleSectionProps) {
  const [isOpen, setIsOpen] = useState(defaultOpen);

  return (
    <div className={`rounded-lg border border-gray-200 dark:border-navy-700 ${className}`}>
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center justify-between px-4 py-2.5 bg-gray-50 dark:bg-navy-850 hover:bg-gray-100 dark:hover:bg-navy-800 transition-colors rounded-t-lg"
      >
        <div className="flex items-center gap-2">
          {Icon && <Icon className="w-3.5 h-3.5 text-gray-500 dark:text-gray-400" />}
          <span className="text-[9px] font-semibold text-gray-600 dark:text-gray-400 uppercase tracking-wider">
            {title}
          </span>
          {badge !== undefined && (
            <span className={`text-[8px] font-bold px-1.5 py-0.5 rounded-full ${badgeColor || "bg-gray-200 text-gray-600 dark:bg-navy-600 dark:text-gray-300"}`}>
              {badge}
            </span>
          )}
        </div>
        {isOpen ? (
          <ChevronDown className="w-3.5 h-3.5 text-gray-400" />
        ) : (
          <ChevronRight className="w-3.5 h-3.5 text-gray-400" />
        )}
      </button>
      {isOpen && (
        <div className="divide-y divide-gray-50 dark:divide-navy-800">
          {children}
        </div>
      )}
    </div>
  );
}

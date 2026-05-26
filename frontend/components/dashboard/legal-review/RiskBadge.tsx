"use client";

import React from "react";
import { AlertTriangle, AlertCircle, Info, MinusCircle } from "lucide-react";
import type { RiskLevel } from "./types";
import { RISK_LEVEL_CONFIG } from "./types";

interface RiskBadgeProps {
  level: RiskLevel;
  size?: "sm" | "md";
  showIcon?: boolean;
  className?: string;
}

const icons: Record<RiskLevel, React.ReactNode> = {
  critical: <AlertTriangle className="w-3 h-3" aria-hidden="true" />,
  high:     <AlertCircle className="w-3 h-3" aria-hidden="true" />,
  medium:   <AlertCircle className="w-3 h-3" aria-hidden="true" />,
  low:      <MinusCircle className="w-3 h-3" aria-hidden="true" />,
  info:     <Info className="w-3 h-3" aria-hidden="true" />,
};

export function RiskBadge({ level, size = "sm", showIcon = true, className = "" }: RiskBadgeProps) {
  const cfg = RISK_LEVEL_CONFIG[level];
  const sizeClasses = size === "sm" ? "text-[10px] px-1.5 py-0.5" : "text-xs px-2 py-1";

  return (
    <span
      className={`inline-flex items-center gap-1 font-medium rounded-full border ${cfg.bg} ${cfg.border} ${cfg.color} ${sizeClasses} ${className}`}
      role="status"
      aria-label={`Risk level: ${cfg.label}`}
    >
      {showIcon && icons[level]}
      {cfg.label}
    </span>
  );
}

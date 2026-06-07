/**
 * PageHeader — Shared enterprise page header component.
 *
 * Provides a consistent layout for every screen:
 * - Page title (required)
 * - One-line purpose description (required)
 * - Primary actions aligned right (optional)
 *
 * Usage:
 *   <PageHeader
 *     title="Ingestion Pipeline"
 *     description="Monitor contract uploads, OCR, extraction, AI processing, and pipeline health."
 *     actions={<><button>Upload</button><button>Export</button></>}
 *   />
 */

"use client";

import React from "react";

interface PageHeaderProps {
  title: string;
  description: string;
  actions?: React.ReactNode;
  className?: string;
}

export function PageHeader({ title, description, actions, className = "" }: PageHeaderProps) {
  return (
    <div className={`flex items-start justify-between gap-4 ${className}`}>
      <div className="min-w-0 flex-1">
        <h1 className="text-xl font-bold text-navy-900 dark:text-white truncate">
          {title}
        </h1>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-0.5">
          {description}
        </p>
      </div>
      {actions && (
        <div className="flex items-center gap-2 shrink-0">
          {actions}
        </div>
      )}
    </div>
  );
}

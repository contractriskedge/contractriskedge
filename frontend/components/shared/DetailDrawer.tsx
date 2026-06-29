"use client";

import React from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X } from "lucide-react";

export type DetailDrawerSize = "md" | "lg" | "xl";

const SIZE_CLASSES: Record<DetailDrawerSize, string> = {
  md: "w-[480px] max-w-[90vw]",
  lg: "w-[72vw] max-w-5xl",
  xl: "w-[75vw] max-w-6xl",
};

interface DetailDrawerProps {
  open: boolean;
  onClose: () => void;
  size?: DetailDrawerSize;
  /** Breadcrumb trail rendered above the title */
  breadcrumbs?: React.ReactNode;
  title: React.ReactNode;
  subtitle?: React.ReactNode;
  icon?: React.ReactNode;
  headerActions?: React.ReactNode;
  stickyActions?: React.ReactNode;
  tabs?: React.ReactNode;
  children: React.ReactNode;
  footer?: React.ReactNode;
}

export function DetailDrawer({
  open,
  onClose,
  size = "md",
  breadcrumbs,
  title,
  subtitle,
  icon,
  headerActions,
  stickyActions,
  tabs,
  children,
  footer,
}: DetailDrawerProps) {
  return (
    <AnimatePresence>
      {open && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/20 z-40"
            onClick={onClose}
          />
          <motion.div
            initial={{ opacity: 0, x: 380 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: 380 }}
            transition={{ type: "spring", damping: 25, stiffness: 250 }}
            className={`fixed right-0 top-0 bottom-0 ${SIZE_CLASSES[size]} bg-white border-l border-gray-200 shadow-xl z-50 flex flex-col`}
          >
            {/* Header */}
            <div className="flex-shrink-0 border-b border-gray-200">
              <div className="flex items-center justify-between px-5 py-3">
                <div className="flex items-center gap-2 min-w-0 flex-1">
                  {icon && <div className="flex-shrink-0">{icon}</div>}
                  <div className="min-w-0 flex-1">
                    {breadcrumbs && (
                      <div className="mb-1">{breadcrumbs}</div>
                    )}
                    <h3 className="text-sm font-semibold text-navy-900 truncate">{title}</h3>
                    {subtitle && (
                      <p className="text-[10px] text-gray-500 truncate">{subtitle}</p>
                    )}
                  </div>
                </div>
                <div className="flex items-center gap-1 flex-shrink-0 ml-2">
                  {headerActions}
                  <button
                    onClick={onClose}
                    className="p-1 rounded-lg hover:bg-gray-100 text-gray-400 hover:text-gray-600 transition-colors"
                    aria-label="Close"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>
              </div>

              {/* Sticky editing actions */}
              {stickyActions && (
                <div className="flex items-center justify-end gap-2 px-5 py-2 border-t border-gray-100 bg-gray-50/80">
                  {stickyActions}
                </div>
              )}
            </div>

            {/* Tabs */}
            {tabs && (
              <div className="flex-shrink-0 px-4 py-2 border-b border-gray-100 flex gap-1 overflow-x-auto">
                {tabs}
              </div>
            )}

            {/* Content */}
            <div className="flex-1 overflow-y-auto p-5">{children}</div>

            {footer && (
              <div className="flex-shrink-0 border-t border-gray-200 px-5 py-3 bg-gray-50">
                {footer}
              </div>
            )}
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}

/** Pill tab button — matches PreviewDrawer / ClauseDetailDrawer convention */
export function DrawerTabBtn({
  label,
  icon,
  active,
  onClick,
}: {
  label: string;
  icon: React.ReactNode;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={`flex items-center gap-1 px-2.5 py-1.5 text-[10px] font-medium rounded-md whitespace-nowrap transition-all ${
        active
          ? "bg-navy-700 text-white shadow-sm"
          : "text-gray-500 hover:text-gray-700 hover:bg-gray-100"
      }`}
    >
      {icon}
      {label}
    </button>
  );
}

/** Breadcrumb trail for detail drawers */
export function DrawerBreadcrumbs({
  items,
}: {
  items: { label: string; onClick?: () => void }[];
}) {
  return (
    <nav className="flex items-center gap-1 text-[10px] text-gray-400 flex-wrap">
      {items.map((item, i) => (
        <React.Fragment key={`${item.label}-${i}`}>
          {i > 0 && <span className="text-gray-300">/</span>}
          {item.onClick ? (
            <button
              onClick={item.onClick}
              className="hover:text-navy-600 transition-colors truncate max-w-[140px]"
            >
              {item.label}
            </button>
          ) : (
            <span className="text-gray-600 font-medium truncate max-w-[160px]">{item.label}</span>
          )}
        </React.Fragment>
      ))}
    </nav>
  );
}

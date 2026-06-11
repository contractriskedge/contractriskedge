"use client";

import React, { useCallback, useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";

export interface AnchoredMenuProps {
  open: boolean;
  onClose: () => void;
  anchorRect: DOMRect | null;
  /** Exclude trigger from click-outside (so the menu can toggle on re-click). */
  anchorEl?: HTMLElement | null;
  children: React.ReactNode;
  width?: number;
  className?: string;
}

/**
 * Renders a dropdown menu in a portal, positioned relative to an anchor rect.
 * Avoids clipping from parent overflow:hidden / overflow-x-auto containers.
 */
export function AnchoredMenu({
  open,
  onClose,
  anchorRect,
  anchorEl,
  children,
  width = 176,
  className = "",
}: AnchoredMenuProps) {
  const menuRef = useRef<HTMLDivElement>(null);
  const [style, setStyle] = useState<React.CSSProperties>({});

  const updatePosition = useCallback(() => {
    if (!anchorRect) return;
    const menuH = menuRef.current?.offsetHeight ?? 280;
    const spaceBelow = window.innerHeight - anchorRect.bottom;
    const openUp = spaceBelow < menuH + 8 && anchorRect.top > spaceBelow;

    setStyle({
      position: "fixed",
      left: Math.max(8, Math.min(anchorRect.right - width, window.innerWidth - width - 8)),
      width,
      top: openUp ? undefined : anchorRect.bottom + 4,
      bottom: openUp ? window.innerHeight - anchorRect.top + 4 : undefined,
      zIndex: 9999,
    });
  }, [anchorRect, width]);

  useEffect(() => {
    if (!open) return;
    updatePosition();
    const onMouseDown = (e: MouseEvent) => {
      const target = e.target as Node;
      if (menuRef.current?.contains(target)) return;
      if (anchorEl?.contains(target)) return;
      onClose();
    };
    const onLayout = () => updatePosition();
    document.addEventListener("mousedown", onMouseDown);
    window.addEventListener("resize", onLayout);
    window.addEventListener("scroll", onLayout, true);
    return () => {
      document.removeEventListener("mousedown", onMouseDown);
      window.removeEventListener("resize", onLayout);
      window.removeEventListener("scroll", onLayout, true);
    };
  }, [open, onClose, updatePosition, anchorEl]);

  useEffect(() => {
    if (open) updatePosition();
  }, [open, children, updatePosition]);

  if (!open || !anchorRect || typeof document === "undefined") return null;

  return createPortal(
    <div
      ref={menuRef}
      style={style}
      className={`rounded-lg border border-gray-200 dark:border-navy-700 bg-white dark:bg-navy-800 shadow-lg py-1 ${className}`}
      role="menu"
    >
      {children}
    </div>,
    document.body,
  );
}

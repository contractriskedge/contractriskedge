/**
 * HybridSidePanel — pinned or auto-hide side panel with edge reveal.
 *
 * Pinned panels participate in flex layout. Auto-hide panels overlay the
 * workspace on reveal so the centre column does not reflow.
 */

"use client";

import React, { useRef, useCallback, useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Pin, PinOff } from "lucide-react";
import { panelStore, usePanelState, type PanelMode } from "./panel-store";

type Side = "left" | "right";

interface HybridSidePanelProps {
  side: Side;
  width?: number;
  minWidth?: number;
  children: React.ReactNode;
  className?: string;
  label?: string;
  /** Bounding container for edge-hover detection (split-pane root). */
  edgeContainerRef?: React.RefObject<HTMLElement | null>;
}

const EDGE_HIT_ZONE = 24;
const HIDE_DELAY = 400;

function PanelChrome({
  side,
  label,
  isPinned,
  toggleMode,
  children,
  className,
}: {
  side: Side;
  label: string;
  isPinned: boolean;
  toggleMode: () => void;
  children: React.ReactNode;
  className: string;
}) {
  return (
    <>
      <div
        className={`sticky top-0 z-10 flex items-center justify-between px-3 py-2 border-b border-gray-200 dark:border-navy-700 bg-white dark:bg-navy-800 ${side === "left" ? "border-r-0" : "border-l-0"}`}
      >
        <span className="text-[10px] font-semibold text-gray-500 uppercase tracking-wider">
          {label}
        </span>
        <button
          type="button"
          onClick={toggleMode}
          className="inline-flex items-center gap-1 px-2 py-1 rounded-md text-[10px] font-medium text-gray-500 hover:text-gray-700 hover:bg-gray-100 dark:hover:bg-navy-700 transition-colors"
          title={isPinned ? `Switch ${label} to auto-hide` : `Pin ${label} always visible`}
          aria-label={isPinned ? `Unpin ${label}` : `Pin ${label}`}
        >
          {isPinned ? (
            <>
              <PinOff className="w-3 h-3" />
              <span>Auto-hide</span>
            </>
          ) : (
            <>
              <Pin className="w-3 h-3" />
              <span>Pin</span>
            </>
          )}
        </button>
      </div>
      <div className={className}>{children}</div>
    </>
  );
}

export function HybridSidePanel({
  side,
  width = 480,
  minWidth = 320,
  children,
  className = "",
  label = "Side panel",
  edgeContainerRef,
}: HybridSidePanelProps) {
  const state = usePanelState();
  const mode: PanelMode = side === "left" ? state.left : state.right;
  const isPinned = mode === "pinned";
  const isRevealed = side === "left" ? state.leftVisible : state.rightVisible;

  const hideTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const overlayRef = useRef<HTMLDivElement>(null);
  const [panelWidth, setPanelWidth] = useState(width);

  const clearHideTimer = useCallback(() => {
    if (hideTimerRef.current) {
      clearTimeout(hideTimerRef.current);
      hideTimerRef.current = null;
    }
  }, []);

  const isInEdgeZone = useCallback(
    (clientX: number): boolean => {
      const container = edgeContainerRef?.current;
      if (!container) return false;
      const rect = container.getBoundingClientRect();
      if (side === "left") {
        return clientX >= rect.left && clientX <= rect.left + EDGE_HIT_ZONE;
      }
      return clientX <= rect.right && clientX >= rect.right - EDGE_HIT_ZONE;
    },
    [edgeContainerRef, side],
  );

  const reveal = useCallback(() => {
    if (state.focusMode || isPinned) return;
    clearHideTimer();
    if (side === "left") panelStore.setLeftVisible(true);
    else panelStore.setRightVisible(true);
  }, [clearHideTimer, isPinned, side, state.focusMode]);

  const hide = useCallback(() => {
    if (state.focusMode || isPinned) return;
    if (side === "left") panelStore.setLeftVisible(false);
    else panelStore.setRightVisible(false);
  }, [isPinned, side, state.focusMode]);

  const scheduleHide = useCallback(() => {
    if (isPinned || state.focusMode) return;
    clearHideTimer();
    hideTimerRef.current = setTimeout(() => {
      hideTimerRef.current = null;
      hide();
    }, HIDE_DELAY);
  }, [clearHideTimer, hide, isPinned, state.focusMode]);

  const isOverPanel = useCallback((clientX: number, clientY: number): boolean => {
    const panelRect = overlayRef.current?.getBoundingClientRect();
    if (!panelRect) return false;
    return (
      clientX >= panelRect.left &&
      clientX <= panelRect.right &&
      clientY >= panelRect.top &&
      clientY <= panelRect.bottom
    );
  }, []);

  const handleMouseMove = useCallback(
    (e: MouseEvent) => {
      if (isPinned || state.focusMode) return;
      if (isInEdgeZone(e.clientX)) {
        reveal();
        return;
      }
      if (isRevealed && !isOverPanel(e.clientX, e.clientY)) {
        scheduleHide();
      }
    },
    [isInEdgeZone, isOverPanel, isPinned, isRevealed, reveal, scheduleHide, state.focusMode],
  );

  const handlePanelMouseEnter = useCallback(() => {
    if (isPinned || state.focusMode) return;
    clearHideTimer();
    reveal();
  }, [clearHideTimer, isPinned, reveal, state.focusMode]);

  const handlePanelMouseLeave = useCallback(
    (e: React.MouseEvent) => {
      if (isPinned || state.focusMode) return;
      if (isInEdgeZone(e.clientX)) return;
      scheduleHide();
    },
    [isInEdgeZone, isPinned, scheduleHide, state.focusMode],
  );

  useEffect(() => {
    document.addEventListener("mousemove", handleMouseMove);
    return () => document.removeEventListener("mousemove", handleMouseMove);
  }, [handleMouseMove]);

  useEffect(() => clearHideTimer, [clearHideTimer]);

  useEffect(() => {
    const updateWidth = () => {
      setPanelWidth(Math.max(minWidth, Math.min(width, window.innerWidth * 0.45)));
    };
    updateWidth();
    window.addEventListener("resize", updateWidth);
    return () => window.removeEventListener("resize", updateWidth);
  }, [minWidth, width]);

  const toggleMode = useCallback(() => {
    if (side === "left") panelStore.toggleLeftMode();
    else panelStore.toggleRightMode();
  }, [side]);

  const showPinned = !state.focusMode && isPinned;
  const showOverlay = !state.focusMode && !isPinned && isRevealed;
  const showEdge = !state.focusMode && !isPinned && !isRevealed;

  const panelClasses = `
    h-full bg-white dark:bg-navy-800 border-gray-200 dark:border-navy-700
    ${side === "left" ? "border-r" : "border-l"}
  `;

  return (
    <>
      {/* Pinned panels reserve flex width. */}
      <div
        className={`relative shrink-0 h-full ${side === "left" ? "order-first" : "order-last"}`}
        style={{
          width: showPinned ? panelWidth : 0,
          minWidth: showPinned ? minWidth : 0,
          maxWidth: showPinned ? "50vw" : 0,
          overflow: "hidden",
        }}
        aria-hidden={!showPinned}
      >
        {showPinned && (
          <div
            className={`${panelClasses} h-full flex flex-col`}
            role="region"
            aria-label={label}
          >
            <PanelChrome
              side={side}
              label={label}
              isPinned={isPinned}
              toggleMode={toggleMode}
              className={`flex-1 min-h-0 overflow-y-auto ${className}`}
            >
              {children}
            </PanelChrome>
          </div>
        )}
      </div>

      {/* Auto-hide edge indicator and overlay are positioned in the split pane. */}
      {showEdge && (
        <div
          className={`absolute top-0 bottom-0 z-30 pointer-events-auto ${
            side === "left" ? "left-0" : "right-0"
          }`}
          style={{ width: EDGE_HIT_ZONE }}
          onMouseEnter={reveal}
        >
          <div
            className={`absolute top-0 bottom-0 w-[5px] ${
              side === "left" ? "left-0" : "right-0"
            } bg-gradient-to-b from-blue-400/70 via-blue-500/80 to-blue-400/70 opacity-80 hover:opacity-100 transition-opacity`}
            title={`Hover to reveal ${label}`}
            aria-hidden="true"
          />
        </div>
      )}

      <AnimatePresence initial={false}>
        {showOverlay && (
          <motion.div
            ref={overlayRef}
            key={`${side}-overlay`}
            initial={{ x: side === "left" ? -panelWidth : panelWidth, opacity: 0 }}
            animate={{
              x: 0,
              opacity: 1,
              transition: { type: "spring", damping: 28, stiffness: 260, mass: 0.8 },
            }}
            exit={{
              x: side === "left" ? -panelWidth : panelWidth,
              opacity: 0,
              transition: { duration: 0.18, ease: "easeInOut" },
            }}
            style={{
              width: panelWidth,
              minWidth,
              maxWidth: "50vw",
              [side]: 0,
            }}
            className={`absolute top-0 bottom-0 z-40 shadow-xl flex flex-col ${panelClasses}`}
            role="region"
            aria-label={label}
            onMouseEnter={handlePanelMouseEnter}
            onMouseLeave={handlePanelMouseLeave}
          >
            <PanelChrome
              side={side}
              label={label}
              isPinned={isPinned}
              toggleMode={toggleMode}
              className={`flex-1 min-h-0 overflow-y-auto ${className}`}
            >
              {children}
            </PanelChrome>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}

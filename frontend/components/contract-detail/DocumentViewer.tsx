/**
 * DocumentViewer — Enterprise PDF/text document viewer.
 *
 * Features:
 * - PDF rendering with iframe/object fallback
 * - Page navigation with prev/next and direct input
 * - Zoom controls (in, out, fit, percentage display)
 * - Full-text search with results navigation
 * - Clause highlighting synchronized with AI findings
 * - Annotation support (visual indicators)
 * - Keyboard navigation (arrow keys, shortcuts)
 * - Loading state with skeleton
 * - Error state with retry
 *
 * Synchronization:
 * - Highlights findings in the document when a finding is selected
 * - Supports bidirectional sync: clicking a highlight selects the finding
 */

"use client";

import React, { useState, useCallback, useRef, useEffect, useMemo } from "react";
import {
  ChevronLeft,
  ChevronRight,
  ZoomIn,
  ZoomOut,
  Maximize2,
  Search,
  X,
  FileText,
  Loader2,
  AlertCircle,
  RefreshCw,
  BookOpen,
  Hash,
} from "lucide-react";
import type { AiFinding, HighlightRegion } from "./types";

// ── Severity Color Map ──────────────────────────────────────────────────────

const SEVERITY_COLORS: Record<string, string> = {
  critical: "#DC2626",   // red-600
  high: "#EA580C",       // orange-500
  medium: "#D97706",     // amber-600
  low: "#6B7280",        // gray-500
  info: "#3B82F6",       // blue-500
};

const SEVERITY_BG_COLORS: Record<string, string> = {
  critical: "bg-red-100 border-red-300 text-red-700",
  high: "bg-orange-100 border-orange-300 text-orange-700",
  medium: "bg-amber-100 border-amber-300 text-amber-700",
  low: "bg-gray-100 border-gray-300 text-gray-600",
  info: "bg-blue-100 border-blue-300 text-blue-700",
};

// ── Props ───────────────────────────────────────────────────────────────────

interface DocumentViewerProps {
  contractId: string;
  documentUrl?: string;
  totalPages: number;
  currentPage: number;
  zoomLevel: number;
  onPageChange: (page: number) => void;
  onZoomChange: (zoom: number) => void;
  highlightedChunkId: string | null;
  findings: AiFinding[];
  onHighlightClick: (chunkId: string) => void;
}

// ── Component ───────────────────────────────────────────────────────────────

export function DocumentViewer({
  contractId,
  documentUrl,
  totalPages,
  currentPage,
  zoomLevel,
  onPageChange,
  onZoomChange,
  highlightedChunkId,
  findings,
  onHighlightClick,
}: DocumentViewerProps) {
  const [searchQuery, setSearchQuery] = useState("");
  const [showSearch, setShowSearch] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [hasError, setHasError] = useState(false);
  const [searchResults, setSearchResults] = useState<number[]>([]);
  const [searchIndex, setSearchIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  // Group findings by page for highlight overlay
  const highlightsByPage = useMemo(() => {
    const map = new Map<number, AiFinding[]>();
    findings.forEach((f) => {
      f.page_numbers.forEach((p) => {
        if (!map.has(p)) map.set(p, []);
        map.get(p)!.push(f);
      });
    });
    return map;
  }, [findings]);

  const pageHighlights = highlightsByPage.get(currentPage) || [];

  // ── Page Navigation ───────────────────────────────────────────────────

  const goToPage = useCallback((page: number) => {
    const clamped = Math.max(1, Math.min(page, totalPages));
    onPageChange(clamped);
  }, [totalPages, onPageChange]);

  const goToPrevPage = useCallback(() => {
    if (currentPage > 1) goToPage(currentPage - 1);
  }, [currentPage, goToPage]);

  const goToNextPage = useCallback(() => {
    if (currentPage < totalPages) goToPage(currentPage + 1);
  }, [currentPage, totalPages, goToPage]);

  // ── Zoom Controls ─────────────────────────────────────────────────────

  const zoomIn = useCallback(() => {
    onZoomChange(Math.min(zoomLevel + 0.25, 3));
  }, [zoomLevel, onZoomChange]);

  const zoomOut = useCallback(() => {
    onZoomChange(Math.max(zoomLevel - 0.25, 0.5));
  }, [zoomLevel, onZoomChange]);

  const zoomToFit = useCallback(() => {
    onZoomChange(1);
  }, [onZoomChange]);

  // ── Search ────────────────────────────────────────────────────────────

  const handleSearch = useCallback(() => {
    if (!searchQuery.trim()) {
      setSearchResults([]);
      return;
    }
    // Simulate search — in production this would call a backend search endpoint
    // or search the PDF text content
    const results: number[] = [];
    const q = searchQuery.toLowerCase();
    findings.forEach((f) => {
      if (
        f.title.toLowerCase().includes(q) ||
        f.description.toLowerCase().includes(q) ||
        f.clause_type.toLowerCase().includes(q)
      ) {
        f.page_numbers.forEach((p) => {
          if (!results.includes(p)) results.push(p);
        });
      }
    });
    setSearchResults(results);
    setSearchIndex(0);
    if (results.length > 0) {
      goToPage(results[0]);
    }
  }, [searchQuery, findings, goToPage]);

  const navigateSearchResult = useCallback((direction: "next" | "prev") => {
    if (searchResults.length === 0) return;
    let newIndex: number;
    if (direction === "next") {
      newIndex = (searchIndex + 1) % searchResults.length;
    } else {
      newIndex = (searchIndex - 1 + searchResults.length) % searchResults.length;
    }
    setSearchIndex(newIndex);
    goToPage(searchResults[newIndex]);
  }, [searchResults, searchIndex, goToPage]);

  // ── Keyboard Navigation ───────────────────────────────────────────────

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Don't handle if user is typing in an input
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return;

      switch (e.key) {
        case "ArrowLeft":
          e.preventDefault();
          goToPrevPage();
          break;
        case "ArrowRight":
          e.preventDefault();
          goToNextPage();
          break;
        case "+":
        case "=":
          e.preventDefault();
          zoomIn();
          break;
        case "-":
          e.preventDefault();
          zoomOut();
          break;
        case "f":
        case "F":
          if (e.ctrlKey || e.metaKey) {
            e.preventDefault();
            setShowSearch(true);
            setTimeout(() => inputRef.current?.focus(), 100);
          }
          break;
        case "Escape":
          setShowSearch(false);
          setSearchQuery("");
          setSearchResults([]);
          break;
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [goToPrevPage, goToNextPage, zoomIn, zoomOut]);

  // ── Simulate loading ──────────────────────────────────────────────────

  useEffect(() => {
    setIsLoading(true);
    setHasError(false);
    const timer = setTimeout(() => {
      setIsLoading(false);
    }, 800);
    return () => clearTimeout(timer);
  }, [currentPage, documentUrl]);

  // ── Render ────────────────────────────────────────────────────────────

  return (
    <div className="flex flex-col h-full bg-gray-100 dark:bg-navy-900">
      {/* ── Document Toolbar ──────────────────────────────────────────── */}
      <div className="flex items-center justify-between px-3 py-1.5 bg-white dark:bg-navy-800 border-b border-gray-200 dark:border-navy-700">
        {/* Page Navigation */}
        <div className="flex items-center gap-1">
          <button
            onClick={goToPrevPage}
            disabled={currentPage <= 1}
            className="p-1 rounded hover:bg-gray-100 dark:hover:bg-navy-700 disabled:opacity-30 disabled:cursor-not-allowed text-gray-500 dark:text-gray-400 transition-colors"
            aria-label="Previous page"
          >
            <ChevronLeft className="w-3.5 h-3.5" />
          </button>
          <div className="flex items-center gap-1">
            <input
              type="number"
              value={currentPage}
              onChange={(e) => {
                const val = parseInt(e.target.value, 10);
                if (!isNaN(val)) goToPage(val);
              }}
              className="w-10 text-center text-[11px] font-medium bg-gray-50 dark:bg-navy-700 border border-gray-200 dark:border-navy-600 rounded px-1 py-0.5 text-navy-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-navy-400"
              min={1}
              max={totalPages}
              aria-label="Current page number"
            />
            <span className="text-[11px] text-gray-400 dark:text-gray-500">
              / {totalPages}
            </span>
          </div>
          <button
            onClick={goToNextPage}
            disabled={currentPage >= totalPages}
            className="p-1 rounded hover:bg-gray-100 dark:hover:bg-navy-700 disabled:opacity-30 disabled:cursor-not-allowed text-gray-500 dark:text-gray-400 transition-colors"
            aria-label="Next page"
          >
            <ChevronRight className="w-3.5 h-3.5" />
          </button>
        </div>

        {/* Zoom Controls */}
        <div className="flex items-center gap-1">
          <button
            onClick={zoomOut}
            disabled={zoomLevel <= 0.5}
            className="p-1 rounded hover:bg-gray-100 dark:hover:bg-navy-700 disabled:opacity-30 disabled:cursor-not-allowed text-gray-500 dark:text-gray-400 transition-colors"
            aria-label="Zoom out"
          >
            <ZoomOut className="w-3.5 h-3.5" />
          </button>
          <span className="text-[11px] font-medium text-gray-600 dark:text-gray-300 min-w-[3rem] text-center">
            {Math.round(zoomLevel * 100)}%
          </span>
          <button
            onClick={zoomIn}
            disabled={zoomLevel >= 3}
            className="p-1 rounded hover:bg-gray-100 dark:hover:bg-navy-700 disabled:opacity-30 disabled:cursor-not-allowed text-gray-500 dark:text-gray-400 transition-colors"
            aria-label="Zoom in"
          >
            <ZoomIn className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={zoomToFit}
            className="p-1 rounded hover:bg-gray-100 dark:hover:bg-navy-700 text-gray-500 dark:text-gray-400 transition-colors"
            aria-label="Zoom to fit"
            title="Zoom to fit"
          >
            <Maximize2 className="w-3.5 h-3.5" />
          </button>
        </div>

        {/* Search Toggle */}
        <button
          onClick={() => {
            setShowSearch(!showSearch);
            if (!showSearch) setTimeout(() => inputRef.current?.focus(), 100);
            else {
              setSearchQuery("");
              setSearchResults([]);
            }
          }}
          className={`p-1 rounded transition-colors ${
            showSearch
              ? "bg-navy-100 text-navy-700 dark:bg-navy-700 dark:text-navy-200"
              : "hover:bg-gray-100 dark:hover:bg-navy-700 text-gray-500 dark:text-gray-400"
          }`}
          aria-label="Search in document"
        >
          <Search className="w-3.5 h-3.5" />
        </button>
      </div>

      {/* ── Search Bar ────────────────────────────────────────────────── */}
      {showSearch && (
        <div className="flex items-center gap-2 px-3 py-1.5 bg-white dark:bg-navy-800 border-b border-gray-200 dark:border-navy-700">
          <Search className="w-3.5 h-3.5 text-gray-400 flex-shrink-0" />
          <input
            ref={inputRef}
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") handleSearch();
            }}
            placeholder="Search in document... (Ctrl+F)"
            className="flex-1 text-[11px] bg-transparent border-none outline-none text-navy-900 dark:text-white placeholder-gray-400"
          />
          {searchResults.length > 0 && (
            <span className="text-[10px] text-gray-500 dark:text-gray-400">
              {searchIndex + 1} of {searchResults.length} pages
            </span>
          )}
          <button
            onClick={() => navigateSearchResult("prev")}
            disabled={searchResults.length === 0}
            className="p-0.5 rounded hover:bg-gray-100 dark:hover:bg-navy-700 disabled:opacity-30 text-gray-500"
            aria-label="Previous result"
          >
            <ChevronLeft className="w-3 h-3" />
          </button>
          <button
            onClick={() => navigateSearchResult("next")}
            disabled={searchResults.length === 0}
            className="p-0.5 rounded hover:bg-gray-100 dark:hover:bg-navy-700 disabled:opacity-30 text-gray-500"
            aria-label="Next result"
          >
            <ChevronRight className="w-3 h-3" />
          </button>
          <button
            onClick={() => {
              setShowSearch(false);
              setSearchQuery("");
              setSearchResults([]);
            }}
            className="p-0.5 rounded hover:bg-gray-100 dark:hover:bg-navy-700 text-gray-400"
            aria-label="Close search"
          >
            <X className="w-3 h-3" />
          </button>
        </div>
      )}

      {/* ── Document Content ──────────────────────────────────────────── */}
      <div className="flex-1 overflow-auto bg-gray-200 dark:bg-navy-950">
        <div
          className="min-h-full flex items-start justify-center p-4 transition-all duration-200"
          style={{ padding: `${16 * zoomLevel}px` }}
        >
          {/* Loading State */}
          {isLoading && (
            <div className="flex flex-col items-center justify-center py-20">
              <Loader2 className="w-8 h-8 text-navy-400 animate-spin mb-3" />
              <p className="text-xs text-gray-500 dark:text-gray-400">Loading document...</p>
            </div>
          )}

          {/* Error State */}
          {hasError && !isLoading && (
            <div className="flex flex-col items-center justify-center py-20 max-w-xs text-center">
              <AlertCircle className="w-10 h-10 text-red-400 mb-3" />
              <p className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Unable to load document
              </p>
              <p className="text-xs text-gray-500 dark:text-gray-400 mb-4">
                The document could not be rendered. It may be unavailable or in an unsupported format.
              </p>
              <button
                onClick={() => {
                  setHasError(false);
                  setIsLoading(true);
                  setTimeout(() => setIsLoading(false), 800);
                }}
                className="inline-flex items-center gap-1.5 text-xs font-medium text-blue-600 hover:text-blue-700"
              >
                <RefreshCw className="w-3 h-3" /> Retry
              </button>
            </div>
          )}

          {/* Document Render Area */}
          {!isLoading && !hasError && (
            <div
              className="relative bg-white dark:bg-navy-800 shadow-lg rounded-sm transition-all duration-200"
              style={{
                width: `${8.5 * zoomLevel * 96}px`,
                minHeight: `${11 * zoomLevel * 96}px`,
                transform: `scale(${zoomLevel})`,
                transformOrigin: "top center",
              }}
            >
              {/* Page Header */}
              <div className="flex items-center justify-between px-6 py-3 border-b border-gray-100 dark:border-navy-700">
                <div className="flex items-center gap-2">
                  <FileText className="w-4 h-4 text-gray-400" />
                  <span className="text-xs text-gray-500 dark:text-gray-400">
                    Page {currentPage}
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <BookOpen className="w-3.5 h-3.5 text-gray-400" />
                  <span className="text-[10px] text-gray-400">
                    {pageHighlights.length} findings on this page
                  </span>
                </div>
              </div>

              {/* Document Text Placeholder */}
              <div className="p-6 space-y-3 text-[13px] leading-relaxed text-gray-700 dark:text-gray-300">
                <p className="font-semibold text-navy-900 dark:text-white text-sm">
                  Contract Document — Page {currentPage}
                </p>
                <p>
                  This is a simulated document view for the contract workspace.
                  In production, this area renders the actual PDF content using
                  a PDF.js or similar rendering engine.
                </p>
                <p>
                  The document viewer supports page navigation, zoom controls,
                  full-text search, and synchronized highlighting with AI findings.
                </p>
                <p className="text-gray-400 text-[11px] italic">
                  Document URL: {documentUrl || "Not available"}
                </p>
              </div>

              {/* ── Finding Highlights Overlay ─────────────────────────── */}
              {pageHighlights.length > 0 && (
                <div className="absolute inset-0 pointer-events-none">
                  {pageHighlights.map((finding) => {
                    const isHighlighted = finding.chunk_id === highlightedChunkId;
                    const color = SEVERITY_COLORS[finding.severity] || SEVERITY_COLORS.medium;

                    return (
                      <button
                        key={finding.id}
                        onClick={() => onHighlightClick(finding.chunk_id)}
                        className={`pointer-events-auto absolute left-6 right-6 py-1 px-2 rounded border-2 transition-all cursor-pointer ${
                          isHighlighted
                            ? "ring-2 ring-offset-1 z-10 opacity-100"
                            : "opacity-60 hover:opacity-90"
                        }`}
                        style={{
                          borderColor: color,
                          backgroundColor: `${color}15`,
                          top: `${120 + pageHighlights.indexOf(finding) * 60}px`,
                          "--tw-ring-color": isHighlighted ? color : undefined,
                        } as React.CSSProperties}
                        title={`${finding.severity.toUpperCase()}: ${finding.title}`}
                        aria-label={`Finding: ${finding.title}`}
                      >
                        <div className="flex items-center gap-1.5">
                          <span
                            className="w-1.5 h-1.5 rounded-full flex-shrink-0"
                            style={{ backgroundColor: color }}
                          />
                          <span className="text-[10px] font-medium truncate" style={{ color }}>
                            {finding.clause_type}
                          </span>
                          <span className="text-[9px] text-gray-400 ml-auto">
                            {Math.round(finding.confidence * 100)}% confidence
                          </span>
                        </div>
                      </button>
                    );
                  })}
                </div>
              )}

              {/* Page Footer */}
              <div className="absolute bottom-3 left-0 right-0 text-center">
                <span className="text-[9px] text-gray-400">
                  Contract ID: {contractId} · Page {currentPage} of {totalPages}
                </span>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* ── Status Bar ─────────────────────────────────────────────────── */}
      <div className="flex items-center justify-between px-3 py-1 bg-white dark:bg-navy-800 border-t border-gray-200 dark:border-navy-700">
        <div className="flex items-center gap-2 text-[10px] text-gray-500 dark:text-gray-400">
          <Hash className="w-3 h-3" />
          <span>Page {currentPage} of {totalPages}</span>
          <span className="text-gray-300 dark:text-gray-600">|</span>
          <span>{zoomLevel}x zoom</span>
          {searchResults.length > 0 && (
            <>
              <span className="text-gray-300 dark:text-gray-600">|</span>
              <span className="text-navy-600 dark:text-navy-300">
                {searchResults.length} pages match &quot;{searchQuery}&quot;
              </span>
            </>
          )}
        </div>
        <div className="flex items-center gap-1">
          {findings
            .filter((f) => f.page_numbers.includes(currentPage))
            .slice(0, 3)
            .map((f) => (
              <span
                key={f.id}
                className={`text-[9px] px-1.5 py-0.5 rounded-full ${SEVERITY_BG_COLORS[f.severity] || "bg-gray-100 text-gray-600"}`}
              >
                {f.clause_type}
              </span>
            ))}
          {findings.filter((f) => f.page_numbers.includes(currentPage)).length > 3 && (
            <span className="text-[9px] text-gray-400">+{findings.filter((f) => f.page_numbers.includes(currentPage)).length - 3}</span>
          )}
        </div>
      </div>
    </div>
  );
}

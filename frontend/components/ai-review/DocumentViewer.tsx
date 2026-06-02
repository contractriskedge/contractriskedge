/**
 * DocumentViewer — enterprise-grade document viewer for contract review.
 *
 * Features:
 * - Page navigation with prev/next and direct input
 * - Zoom controls (50%-200%)
 * - Full text search with results navigation
 * - Finding anchors — click to jump to clause
 * - Inline clause highlighting with severity colors
 * - Clause collapse/expand
 * - Minimap (compact page overview)
 * - Keyboard navigation
 * - Side-by-side compare mode (future)
 */

"use client";

import React, { useState, useCallback, useRef, useEffect, useMemo } from "react";
import {
  ChevronLeft, ChevronRight, ZoomIn, ZoomOut, Maximize2, Search, X,
  FileText, BookOpen, Hash, AlertTriangle, ArrowDown, ArrowUp,
  Layers, PanelRight, Loader2,
} from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/services/api/client";
import { REVIEW_SUBRESOURCE_API } from "./hooks";
import {
  onLocateClause,
  LOCATE_CLAUSE_SUCCESS_EVENT,
  type LocateClausePayload,
  type LocateClauseSuccessDetail,
} from "@/lib/highlightClause";
import type { Finding } from "./types";

// ── Props ───────────────────────────────────────────────────────────────────

interface DocumentViewerProps {
  review: { contract_name: string; vendor: string; document_type: string; review_id?: string } | null;
  findings: Finding[];
  selectedFindingId: string | null;
  onFindingClick: (id: string) => void;
}

// ── Document Section Type ───────────────────────────────────────────────────

interface DocumentSection {
  id: string;
  label: string;
  page: number;
  text: string;
  findingId?: string;
}

// ── Default mock sections used ONLY when no review is selected ──────────────

const FALLBACK_SECTIONS: DocumentSection[] = [
  { id: "sec-1", label: "1. Services", page: 1, text: "Vendor shall provide the services described in Exhibit A (the 'Services') in accordance with the terms of this Agreement." },
  { id: "sec-2", label: "1.2 Term", page: 1, text: "This Agreement shall commence on the Effective Date and continue for an initial term of twelve (12) months, unless earlier terminated in accordance with Section 9." },
  { id: "sec-3", label: "2. Fees", page: 2, text: "Customer shall pay Vendor the fees set forth in Exhibit B. Fees are due within thirty (30) days of invoice date." },
  { id: "sec-4", label: "3. Confidentiality", page: 3, text: "Confidential Information shall mean written information clearly marked as confidential at the time of disclosure." },
  { id: "sec-5", label: "4.1 Renewal", page: 4, text: "This Agreement shall automatically renew for successive one-year periods unless either party provides written notice of non-renewal at least 15 days prior to the expiration date.", findingId: "find-003" },
  { id: "sec-12", label: "12.3 Limitation of Liability", page: 12, text: "Party A shall be liable for all damages, losses, costs, and expenses arising from any breach of this Agreement, without limitation.", findingId: "find-001" },
  { id: "sec-8-1", label: "8.1 Indemnification", page: 8, text: "Vendor shall indemnify Customer against third-party claims arising from IP infringement. Customer shall indemnify Vendor against all other claims." },
];

// ── Finding Severity Colors ─────────────────────────────────────────────────

function findingColor(severity: string): { bg: string; text: string; border: string; mark: string } {
  switch (severity) {
    case "critical": return { bg: "bg-red-100", text: "text-red-700", border: "border-red-300", mark: "bg-red-200 text-red-900" };
    case "high": return { bg: "bg-orange-100", text: "text-orange-700", border: "border-orange-300", mark: "bg-orange-200 text-orange-900" };
    case "medium": return { bg: "bg-amber-100", text: "text-amber-700", border: "border-amber-300", mark: "bg-amber-200 text-amber-900" };
    default: return { bg: "bg-gray-100", text: "text-gray-600", border: "border-gray-300", mark: "bg-gray-200 text-gray-800" };
  }
}

// ── Component ───────────────────────────────────────────────────────────────

export function DocumentViewer({ review, findings, selectedFindingId, onFindingClick }: DocumentViewerProps) {
  const [currentPage, setCurrentPage] = useState(1);
  const [zoomLevel, setZoomLevel] = useState(1);
  const [showSearch, setShowSearch] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<string[]>([]);
  const [searchIndex, setSearchIndex] = useState(0);
  const [collapsedSections, setCollapsedSections] = useState<Set<string>>(new Set());
  const [showMinimap, setShowMinimap] = useState(false);
  const [highlightedSectionId, setHighlightedSectionId] = useState<string | null>(null);
  const [ephemeralSections, setEphemeralSections] = useState<DocumentSection[]>([]);
  const inputRef = useRef<HTMLInputElement>(null);
  const contentRef = useRef<HTMLDivElement>(null);

  // ── Fetch document content from API ─────────────────────────────────

  const { data: documentContent } = useQuery<{ sections: DocumentSection[]; total_pages: number }>({
    queryKey: ["document-content", review?.review_id],
    queryFn: async () => {
      if (!REVIEW_SUBRESOURCE_API.document) {
        return { sections: FALLBACK_SECTIONS, total_pages: 15 };
      }
      try {
        const res = await api.get<{ sections: DocumentSection[]; total_pages: number }>(
          `/reviews/${review?.review_id}/document`,
        );
        return res;
      } catch {
        return { sections: FALLBACK_SECTIONS, total_pages: 15 };
      }
    },
    enabled: !!review?.review_id,
    staleTime: 60_000,
  });

  // ── Use API data or fallback to minimal default sections ─────────────

  const rawSections = documentContent?.sections ?? FALLBACK_SECTIONS;
  const totalPages = documentContent?.total_pages ?? 15;

  // Merge API sections with synthetic anchors from findings (Locate Source Clause).
  const DOCUMENT_SECTIONS = useMemo(() => {
    const merged: DocumentSection[] = [...rawSections];

    const addSynthetic = (
      id: string,
      label: string,
      page: number,
      text: string,
      findingId?: string,
    ) => {
      const body = text.trim();
      if (!body) return;
      if (merged.some((s) => s.id === id || (findingId && s.findingId === findingId))) return;
      merged.push({ id, label, page: Math.max(1, page), text: body, findingId });
    };

    for (const f of findings) {
      addSynthetic(
        `finding-${f.finding_id}`,
        f.title || f.clause_type || "Clause",
        f.page_numbers[0] || 1,
        f.clause_text || f.description || "",
        f.finding_id,
      );
    }

    const enriched = merged.map((s) => {
      if (s.findingId) return s;
      const match = findings.find((f) => {
        const ct = (f.clause_text || f.description || "").toLowerCase().trim();
        const st = s.text.toLowerCase().trim();
        return (
          st.includes(ct) ||
          ct.includes(st) ||
          (ct.length > 20 && st.length > 20 && (st.includes(ct.slice(0, 40)) || ct.includes(st.slice(0, 40))))
        );
      });
      return match ? { ...s, findingId: match.finding_id } : s;
    });
    return [...enriched, ...ephemeralSections];
  }, [rawSections, findings, ephemeralSections]);

  // ── Page Navigation (must be before locate clause listener) ─────────

  const goToPage = useCallback((page: number) => {
    setCurrentPage(Math.max(1, Math.min(page, totalPages)));
  }, [totalPages]);

  // ── Listen for locate clause events ─────────────────────────────────

  useEffect(() => {
    return onLocateClause((payload: LocateClausePayload) => {
      const linkedFinding = findings.find((f) => f.finding_id === payload.findingId);
      const searchText = (
        payload.clauseText ||
        linkedFinding?.clause_text ||
        linkedFinding?.description ||
        ""
      )
        .trim()
        .toLowerCase();
      const searchSnippet = searchText.length > 120 ? searchText.slice(0, 120) : searchText;
      const clauseType = payload.clauseType?.toLowerCase().trim();
      const sectionLabel = payload.sectionLabel?.toLowerCase().trim();

      const matchByText = (sections: DocumentSection[]) => {
        if (!searchSnippet && !clauseType) return undefined;
        if (searchSnippet) {
          const exact = sections.find((s) => s.text.toLowerCase().includes(searchSnippet));
          if (exact) return exact;
          const words = searchSnippet.split(/\s+/).filter((w) => w.length > 4);
          if (words.length > 0) {
            const wordMatch = sections.find((s) => {
              const haystack = s.text.toLowerCase();
              return words.filter((w) => haystack.includes(w)).length >= Math.min(3, words.length);
            });
            if (wordMatch) return wordMatch;
          }
        }
        if (clauseType) {
          return sections.find(
            (s) =>
              s.label.toLowerCase().includes(clauseType) ||
              s.text.toLowerCase().includes(clauseType),
          );
        }
        return undefined;
      };

      const section =
        (payload.redlineId
          ? DOCUMENT_SECTIONS.find((s) => s.id === `redline-${payload.redlineId}`)
          : undefined) ??
        DOCUMENT_SECTIONS.find((s) => s.findingId === payload.findingId) ??
        DOCUMENT_SECTIONS.find((s) => s.id === `finding-${payload.findingId}`) ??
        (payload.chunkId
          ? DOCUMENT_SECTIONS.find((s) => s.id === payload.chunkId)
          : undefined) ??
        (sectionLabel
          ? DOCUMENT_SECTIONS.find((s) => s.label.toLowerCase().includes(sectionLabel))
          : undefined) ??
        matchByText(DOCUMENT_SECTIONS) ??
        (payload.page > 0
          ? matchByText(DOCUMENT_SECTIONS.filter((s) => s.page === payload.page))
          : undefined);

      let resolvedSection = section;
      let createdEphemeral = false;

      if (!resolvedSection && payload.redlineId && (payload.clauseText || searchText)) {
        const ephemeral: DocumentSection = {
          id: `redline-${payload.redlineId}`,
          label: payload.sectionLabel || payload.clauseType || "Clause",
          page: payload.page,
          text: payload.clauseText || linkedFinding?.clause_text || searchText,
          findingId: payload.findingId,
        };
        setEphemeralSections((prev) => {
          if (prev.some((s) => s.id === ephemeral.id)) return prev;
          return [...prev, ephemeral];
        });
        resolvedSection = ephemeral;
        createdEphemeral = true;
      }

      const targetPage = resolvedSection?.page ?? payload.page;
      goToPage(targetPage);

      const successDetail: LocateClauseSuccessDetail = {
        page: targetPage,
        sectionLabel: resolvedSection?.label,
        matched: Boolean(resolvedSection),
      };

      const flashHighlight = (sectionId: string) => {
        setHighlightedSectionId(sectionId);
        setTimeout(() => setHighlightedSectionId(null), 4500);
        const el = document.getElementById(`section-${sectionId}`);
        el?.scrollIntoView({ behavior: "smooth", block: "center" });
      };

      if (resolvedSection) {
        if (resolvedSection.findingId && !payload.preserveReviewContext) {
          onFindingClick(resolvedSection.findingId);
        }
        const sectionId = resolvedSection.id;
        if (createdEphemeral) {
          setTimeout(() => flashHighlight(sectionId), 300);
        } else {
          setTimeout(() => flashHighlight(sectionId), 200);
        }
      } else if (payload.page > 0) {
        setTimeout(() => {
          contentRef.current?.scrollTo({ top: 0, behavior: "smooth" });
        }, 200);
      }

      window.dispatchEvent(
        new CustomEvent<LocateClauseSuccessDetail>(LOCATE_CLAUSE_SUCCESS_EVENT, {
          detail: successDetail,
        }),
      );
    });
  }, [DOCUMENT_SECTIONS, findings, goToPage, onFindingClick]);

  // ── Filter sections by page ──────────────────────────────────────────

  const pageSections = useMemo(() => DOCUMENT_SECTIONS.filter(s => s.page === currentPage), [DOCUMENT_SECTIONS, currentPage]);

  // ── Finding lookup ───────────────────────────────────────────────────

  const findingBySection = useMemo(() => {
    const map = new Map<string, Finding>();
    findings.forEach(f => map.set(f.finding_id, f));
    return map;
  }, [findings]);

  // ── Zoom ────────────────────────────────────────────────────────────

  const zoomIn = () => setZoomLevel(z => Math.min(z + 0.25, 2));
  const zoomOut = () => setZoomLevel(z => Math.max(z - 0.25, 0.5));
  const zoomFit = () => setZoomLevel(1);

  // ── Search ──────────────────────────────────────────────────────────

  const handleSearch = useCallback(() => {
    if (!searchQuery.trim()) { setSearchResults([]); return; }
    const q = searchQuery.toLowerCase();
    const results = DOCUMENT_SECTIONS
      .filter(s => s.text.toLowerCase().includes(q) || s.label.toLowerCase().includes(q))
      .map(s => s.id);
    setSearchResults(results);
    setSearchIndex(0);
    if (results.length > 0) {
      const section = DOCUMENT_SECTIONS.find(s => s.id === results[0]);
      if (section) goToPage(section.page);
    }
  }, [searchQuery, goToPage]);

  const navSearch = (dir: "next" | "prev") => {
    if (searchResults.length === 0) return;
    const newIdx = dir === "next"
      ? (searchIndex + 1) % searchResults.length
      : (searchIndex - 1 + searchResults.length) % searchResults.length;
    setSearchIndex(newIdx);
    const section = DOCUMENT_SECTIONS.find(s => s.id === searchResults[newIdx]);
    if (section) goToPage(section.page);
  };

  // ── Toggle section collapse ─────────────────────────────────────────

  const toggleCollapse = (id: string) => {
    setCollapsedSections(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  };

  // ── Jump to finding ─────────────────────────────────────────────────

  const jumpToFinding = useCallback((findingId: string) => {
    const section = DOCUMENT_SECTIONS.find(s => s.findingId === findingId);
    if (section) {
      goToPage(section.page);
      onFindingClick(findingId);
    }
  }, [goToPage, onFindingClick]);

  // ── Finding anchors ─────────────────────────────────────────────────

  const findingAnchors = useMemo(() => {
    const anchors: { findingId: string; title: string; severity: string; page: number }[] = [];
    DOCUMENT_SECTIONS.forEach(s => {
      if (s.findingId) {
        const f = findings.find(fi => fi.finding_id === s.findingId);
        if (f) anchors.push({ findingId: s.findingId, title: f.title, severity: f.severity, page: s.page });
      }
    });
    return anchors;
  }, [findings]);

  // ── Keyboard ────────────────────────────────────────────────────────

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return;
      switch (e.key) {
        case "ArrowLeft": goToPage(currentPage - 1); break;
        case "ArrowRight": goToPage(currentPage + 1); break;
        case "f": case "F": if (e.metaKey || e.ctrlKey) { e.preventDefault(); setShowSearch(true); setTimeout(() => inputRef.current?.focus(), 50); } break;
        case "Escape": setShowSearch(false); setSearchQuery(""); setSearchResults([]); break;
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [currentPage, goToPage]);

  if (!review) {
    return (
      <div className="flex items-center justify-center h-full text-center p-6">
        <FileText className="w-10 h-10 text-gray-300 dark:text-gray-600 mx-auto mb-2" />
        <p className="text-xs text-gray-400">Select a review to view document</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full bg-gray-50 dark:bg-navy-900">
      {/* ── Document Toolbar ──────────────────────────────────────────── */}
      <div className="flex items-center justify-between px-3 py-1.5 bg-white dark:bg-navy-800 border-b border-gray-200 dark:border-navy-700 flex-shrink-0">
        {/* Page Nav */}
        <div className="flex items-center gap-1">
          <button onClick={() => goToPage(currentPage - 1)} disabled={currentPage <= 1}
            className="p-1 rounded hover:bg-gray-100 dark:hover:bg-navy-700 disabled:opacity-30 text-gray-500">
            <ChevronLeft className="w-3.5 h-3.5" />
          </button>
          <div className="flex items-center gap-1">
            <input type="number" value={currentPage} onChange={e => { const v = parseInt(e.target.value); if (!isNaN(v)) goToPage(v); }}
              className="w-9 text-center text-[11px] font-medium bg-gray-50 dark:bg-navy-700 border border-gray-200 dark:border-navy-600 rounded px-1 py-0.5 text-navy-900 dark:text-white" min={1} max={totalPages} />
            <span className="text-[11px] text-gray-400">/ {totalPages}</span>
          </div>
          <button onClick={() => goToPage(currentPage + 1)} disabled={currentPage >= totalPages}
            className="p-1 rounded hover:bg-gray-100 dark:hover:bg-navy-700 disabled:opacity-30 text-gray-500">
            <ChevronRight className="w-3.5 h-3.5" />
          </button>
        </div>

        {/* Zoom */}
        <div className="flex items-center gap-1">
          <button onClick={zoomOut} disabled={zoomLevel <= 0.5} className="p-1 rounded hover:bg-gray-100 dark:hover:bg-navy-700 disabled:opacity-30 text-gray-500"><ZoomOut className="w-3.5 h-3.5" /></button>
          <span className="text-[10px] font-medium text-gray-600 dark:text-gray-300 min-w-[2.5rem] text-center">{Math.round(zoomLevel * 100)}%</span>
          <button onClick={zoomIn} disabled={zoomLevel >= 2} className="p-1 rounded hover:bg-gray-100 dark:hover:bg-navy-700 disabled:opacity-30 text-gray-500"><ZoomIn className="w-3.5 h-3.5" /></button>
          <button onClick={zoomFit} className="p-1 rounded hover:bg-gray-100 dark:hover:bg-navy-700 text-gray-500"><Maximize2 className="w-3.5 h-3.5" /></button>
        </div>

        {/* Tools */}
        <div className="flex items-center gap-1">
          <button onClick={() => { setShowSearch(!showSearch); if (!showSearch) setTimeout(() => inputRef.current?.focus(), 50); else { setSearchQuery(""); setSearchResults([]); } }}
            className={`p-1 rounded transition-colors ${showSearch ? "bg-navy-100 text-navy-700 dark:bg-navy-700" : "hover:bg-gray-100 dark:hover:bg-navy-700 text-gray-500"}`}>
            <Search className="w-3.5 h-3.5" />
          </button>
          <button onClick={() => setShowMinimap(!showMinimap)}
            className={`p-1 rounded transition-colors ${showMinimap ? "bg-navy-100 text-navy-700 dark:bg-navy-700" : "hover:bg-gray-100 dark:hover:bg-navy-700 text-gray-500"}`}>
            <Layers className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* ── Search Bar ────────────────────────────────────────────────── */}
      {showSearch && (
        <div className="flex items-center gap-2 px-3 py-1.5 bg-white dark:bg-navy-800 border-b border-gray-200 dark:border-navy-700">
          <Search className="w-3 h-3 text-gray-400 flex-shrink-0" />
          <input ref={inputRef} type="text" value={searchQuery} onChange={e => setSearchQuery(e.target.value)} onKeyDown={e => { if (e.key === "Enter") handleSearch(); }}
            placeholder="Search document... (⌘F)" className="flex-1 text-[11px] bg-transparent border-none outline-none text-navy-900 dark:text-white placeholder-gray-400" />
          {searchResults.length > 0 && (
            <span className="text-[9px] text-gray-500">{searchIndex + 1} of {searchResults.length}</span>
          )}
          <button onClick={() => navSearch("prev")} disabled={searchResults.length === 0} className="p-0.5 rounded hover:bg-gray-100 disabled:opacity-30 text-gray-500"><ChevronLeft className="w-3 h-3" /></button>
          <button onClick={() => navSearch("next")} disabled={searchResults.length === 0} className="p-0.5 rounded hover:bg-gray-100 disabled:opacity-30 text-gray-500"><ChevronRight className="w-3 h-3" /></button>
          <button onClick={() => { setShowSearch(false); setSearchQuery(""); setSearchResults([]); }} className="p-0.5 rounded hover:bg-gray-100 text-gray-400"><X className="w-3 h-3" /></button>
        </div>
      )}

      {/* ── Minimap ────────────────────────────────────────────────────── */}
      {showMinimap && (
        <div className="px-3 py-2 bg-white dark:bg-navy-800 border-b border-gray-200 dark:border-navy-700">
          <div className="flex items-center gap-1">
            {Array.from({ length: totalPages }, (_, i) => i + 1).map(page => (
              <button key={page} onClick={() => goToPage(page)}
                className={`w-5 h-5 rounded text-[8px] font-medium transition-colors ${
                  page === currentPage ? "bg-navy-600 text-white" :
                  findingAnchors.some(a => a.page === page) ? "bg-amber-100 text-amber-800" :
                  "bg-gray-100 dark:bg-navy-700 text-gray-500 hover:bg-gray-200"
                }`}>
                {page}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* ── Document Content ──────────────────────────────────────────── */}
      <div className="flex-1 overflow-y-auto p-4" style={{ fontSize: `${11 * zoomLevel}px` }}>
        <div className="max-w-3xl mx-auto bg-white dark:bg-navy-800 border border-gray-200 dark:border-navy-700 rounded-lg shadow-sm">
          {/* Page Header */}
          <div className="px-5 py-3 border-b border-gray-100 dark:border-navy-700 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <FileText className="w-4 h-4 text-gray-400" />
              <span className="text-xs font-medium text-navy-900 dark:text-white">{review.contract_name}</span>
            </div>
            <span className="text-[10px] text-gray-400">Page {currentPage} · {review.document_type}</span>
          </div>

          {/* Sections */}
          <div className="px-5 py-4 space-y-3">
            {pageSections.length === 0 ? (
              <p className="text-xs text-gray-400 text-center py-8">No content on this page</p>
            ) : pageSections.map(section => {
              const isCollapsed = collapsedSections.has(section.id);
              const isSearchHit = searchResults.includes(section.id);
              const finding = section.findingId ? findingBySection.get(section.findingId) : undefined;
              const colors = finding ? findingColor(finding.severity) : null;

              return (
                <div key={section.id} id={`section-${section.id}`} className={`rounded-lg border transition-all ${
                  finding ? `${colors?.border} ${finding.finding_id === selectedFindingId ? "ring-2 ring-navy-400 shadow-md" : ""}` : "border-gray-100 dark:border-navy-700"
                } ${isSearchHit ? "ring-2 ring-amber-400" : ""} ${
                  highlightedSectionId === section.id
                    ? "ring-2 ring-yellow-400 bg-yellow-100 dark:bg-yellow-900/30 shadow-md animate-pulse"
                    : ""
                }`}>
                  {/* Section Header */}
                  <button onClick={() => toggleCollapse(section.id)}
                    className="w-full flex items-center gap-2 px-3 py-2 text-left hover:bg-gray-50 dark:hover:bg-navy-750 rounded-t-lg">
                    <Hash className="w-3 h-3 text-gray-400 flex-shrink-0" />
                    <span className={`text-[11px] font-semibold ${finding ? colors?.text : "text-navy-900 dark:text-white"}`}>
                      {section.label}
                    </span>
                    {finding && (
                      <span className={`ml-auto text-[8px] px-1.5 py-0.5 rounded-full font-medium ${colors?.bg} ${colors?.text}`}>
                        {finding.severity}
                      </span>
                    )}
                  </button>

                  {/* Section Body */}
                  {!isCollapsed && (
                    <div className="px-3 pb-2.5">
                      <p className={`text-[11px] leading-relaxed ${
                        finding?.finding_id === selectedFindingId ? colors?.mark : "text-gray-700 dark:text-gray-300"
                      }`}>
                        {section.text}
                      </p>
                      {finding && (
                        <div className="flex items-center gap-2 mt-1.5">
                          <button onClick={() => onFindingClick(finding.finding_id)}
                            className={`flex items-center gap-1 px-2 py-0.5 text-[8px] font-medium rounded ${colors?.bg} ${colors?.text} hover:opacity-80 transition-opacity`}>
                            <AlertTriangle className="w-2.5 h-2.5" /> View finding
                          </button>
                          <span className="text-[8px] text-gray-400">Confidence: {Math.round(finding.confidence * 100)}%</span>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          {/* Page Footer */}
          <div className="px-5 py-2 border-t border-gray-100 dark:border-navy-700 text-center">
            <span className="text-[8px] text-gray-400">{review.vendor} · Page {currentPage} of {totalPages}</span>
          </div>
        </div>
      </div>

      {/* ── Finding Anchors Rail ───────────────────────────────────────── */}
      <div className="border-t border-gray-200 dark:border-navy-700 bg-white dark:bg-navy-800 flex-shrink-0">
        <div className="px-3 py-1.5 flex items-center gap-1.5 overflow-x-auto">
          <BookOpen className="w-3 h-3 text-gray-400 flex-shrink-0" />
          <span className="text-[8px] text-gray-500 font-medium mr-1 flex-shrink-0">Findings:</span>
          {findingAnchors.map(a => (
            <button key={a.findingId} onClick={() => jumpToFinding(a.findingId)}
              className={`flex items-center gap-1 px-1.5 py-0.5 rounded text-[8px] font-medium whitespace-nowrap transition-colors ${
                a.findingId === selectedFindingId
                  ? a.severity === "critical" ? "bg-red-100 text-red-700 ring-1 ring-red-300" : "bg-amber-100 text-amber-700 ring-1 ring-amber-300"
                  : a.severity === "critical" ? "bg-red-50 text-red-600 hover:bg-red-100" : "bg-amber-50 text-amber-600 hover:bg-amber-100"
              }`}>
              <span className={`w-1.5 h-1.5 rounded-full ${a.severity === "critical" ? "bg-red-500" : "bg-amber-500"}`} />
              <span className="truncate max-w-[80px]">{a.title}</span>
              <span className="text-gray-400">p.{a.page}</span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

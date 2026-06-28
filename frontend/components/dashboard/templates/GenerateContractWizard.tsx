/**
 * GenerateContractWizard — Multi-step wizard: select template, fill variables, choose clauses, preview, generate.
 *
 * Enterprise features:
 * - Template version pinning (freezes version at step 1)
 * - Idempotency key (prevents duplicate generation)
 * - Auto-save draft on every step transition
 * - Required-field validation gate on Step 2 → Step 3
 * - Inline variable validation (format, min/max, required)
 * - Draft resume via /drafts endpoint
 * - Browser-close warning for unsaved work
 */

"use client";

import React, { useState, useMemo, useCallback, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  ArrowLeft, ArrowRight, Check, FileText, Loader2, AlertTriangle,
  ExternalLink, Send, Sparkles, Shield, Star,
  ChevronDown, ChevronUp, MessageSquare, AlertCircle, XCircle,
  RefreshCw, Eye, FileDown,
} from "lucide-react";
import { api } from "@/services";
import { reviewService } from "@/services/api/reviews";
import type {
  TemplateListItem, TemplateCategory, TemplateDetail, TemplateVariable,
  GenerateContractResponse, PaginatedTemplateList, PaginatedCategoryList,
} from "./types";
import type { ReviewStatusResponse } from "@/services/api/client";

const STEPS = ["Select Template", "Fill Variables", "Suggested Clauses", "Clause Selection", "Preview", "Generate"];

const STEP_META = [
  { title: "Select Template", description: "Choose an approved gold-standard template", icon: FileText },
  { title: "Fill Variables", description: "Complete contract metadata and commercial terms", icon: Shield },
  { title: "Suggested Clauses", description: "Review AI-suggested clauses based on your variables", icon: Sparkles },
  { title: "Clause Selection", description: "Include or exclude governed clauses with audit trail", icon: MessageSquare },
  { title: "Preview", description: "Review assembled document before generation", icon: Eye },
  { title: "Generate", description: "Create contract, DOCX artifact, and AI review queue", icon: Send },
];

interface ClauseSelection {
  clause_id: string;
  clause_title: string;
  clause_type: string;
  risk_level?: string | null;
  content: string;
  is_required: boolean;
  included: boolean;
  reason_removed: string;
  notes: string;
  fallback_clause_id?: string | null;
}

interface GenerateContractWizardProps {
  preSelectedTemplateId?: string;
  draftId?: string;
}

interface SuggestedClauseItem {
  clause_id: string;
  clause_title: string;
  clause_type: string;
  clause_content: string;
  risk_level?: string | null;
  recommendation_type: string; // required, recommended, optional
  reason: string;
  rule_id: string;
  rule_name: string;
  is_checked: boolean;
}

// ── Validation helpers ───────────────────────────────────────────

/** ISO 4217 currency codes for searchable select */
const CURRENCY_CODES = [
  { code: "USD", name: "US Dollar", symbol: "$" },
  { code: "EUR", name: "Euro", symbol: "€" },
  { code: "GBP", name: "British Pound", symbol: "£" },
  { code: "JPY", name: "Japanese Yen", symbol: "¥" },
  { code: "CAD", name: "Canadian Dollar", symbol: "CA$" },
  { code: "AUD", name: "Australian Dollar", symbol: "A$" },
  { code: "CHF", name: "Swiss Franc", symbol: "CHF" },
  { code: "CNY", name: "Chinese Yuan", symbol: "¥" },
  { code: "INR", name: "Indian Rupee", symbol: "₹" },
  { code: "SGD", name: "Singapore Dollar", symbol: "S$" },
  { code: "NZD", name: "New Zealand Dollar", symbol: "NZ$" },
  { code: "HKD", name: "Hong Kong Dollar", symbol: "HK$" },
  { code: "SEK", name: "Swedish Krona", symbol: "kr" },
  { code: "NOK", name: "Norwegian Krone", symbol: "kr" },
  { code: "DKK", name: "Danish Krone", symbol: "kr" },
  { code: "MXN", name: "Mexican Peso", symbol: "Mex$" },
  { code: "BRL", name: "Brazilian Real", symbol: "R$" },
  { code: "ZAR", name: "South African Rand", symbol: "R" },
  { code: "AED", name: "UAE Dirham", symbol: "د.إ" },
  { code: "SAR", name: "Saudi Riyal", symbol: "﷼" },
];

/** Countries with states/provinces for jurisdiction picker */
const JURISDICTIONS: Record<string, string[]> = {
  "United States": ["Alabama","Alaska","Arizona","Arkansas","California","Colorado","Connecticut","Delaware","Florida","Georgia","Hawaii","Idaho","Illinois","Indiana","Iowa","Kansas","Kentucky","Louisiana","Maine","Maryland","Massachusetts","Michigan","Minnesota","Mississippi","Missouri","Montana","Nebraska","Nevada","New Hampshire","New Jersey","New Mexico","New York","North Carolina","North Dakota","Ohio","Oklahoma","Oregon","Pennsylvania","Rhode Island","South Carolina","South Dakota","Tennessee","Texas","Utah","Vermont","Virginia","Washington","West Virginia","Wisconsin","Wyoming"],
  "Canada": ["Alberta","British Columbia","Manitoba","New Brunswick","Newfoundland and Labrador","Nova Scotia","Ontario","Prince Edward Island","Quebec","Saskatchewan"],
  "United Kingdom": ["England","Scotland","Wales","Northern Ireland"],
  "Australia": ["New South Wales","Queensland","South Australia","Tasmania","Victoria","Western Australia"],
  "Germany": ["Baden-Württemberg","Bavaria","Berlin","Brandenburg","Bremen","Hamburg","Hesse","Lower Saxony","Mecklenburg-Vorpommern","North Rhine-Westphalia","Rhineland-Palatinate","Saarland","Saxony","Saxony-Anhalt","Schleswig-Holstein","Thuringia"],
  "India": ["Andhra Pradesh","Delhi","Karnataka","Maharashtra","Tamil Nadu","Telangana","Uttar Pradesh","West Bengal"],
  "France": ["Île-de-France","Auvergne-Rhône-Alpes","Nouvelle-Aquitaine","Occitanie","Hauts-de-France"],
  "Singapore": ["Singapore"],
  "Japan": ["Tokyo","Osaka","Kanagawa","Aichi","Hokkaido"],
  "Switzerland": ["Zürich","Bern","Geneva","Basel-Stadt","Vaud"],
  "Netherlands": ["North Holland","South Holland","Utrecht","Gelderland"],
  "United Arab Emirates": ["Abu Dhabi","Dubai","Sharjah"],
};

const COMMON_COUNTRIES = Object.keys(JURISDICTIONS);

/** Check if a value looks like placeholder/test junk */
function isPlaceholderOrTestValue(value: string, fieldLabel: string, placeholder?: string | null): boolean {
  const cleaned = value.trim().toLowerCase();
  if (!cleaned) return false;
  // Reject values identical to placeholder text
  if (placeholder && cleaned === placeholder.trim().toLowerCase()) return true;
  // Reject common test/junk patterns
  const junkPatterns = ["test", "asdf", "xxx", "abc", "123", "n/a", "na", "tbd", "todo", "asaa", "asasa", "zzz", "qwerty"];
  if (junkPatterns.includes(cleaned)) return true;
  // Reject single-character or repeated single char
  if (cleaned.length <= 2 && /^[a-z]{1,2}$/.test(cleaned)) return true;
  // Reject values that are just the field label repeated
  const labelNorm = fieldLabel.toLowerCase().replace(/[^a-z0-9]/g, "");
  if (cleaned === labelNorm) return true;
  return false;
}

function validateVariableValue(v: TemplateVariable, value: any, allValues?: Record<string, any>): string | null {
  // Required check
  if (v.is_required && (value === undefined || value === null || String(value).trim() === "")) {
    return `${v.label} is required`;
  }
  // If empty and not required, skip further validation
  if (value === undefined || value === null || String(value).trim() === "") {
    return null;
  }

  const strVal = String(value).trim();
  const rules = v.validation_rules || {};

  // Placeholder/junk detection for text-like fields
  if (["text", "string", undefined].includes(v.field_type) && strVal.length > 0) {
    if (isPlaceholderOrTestValue(strVal, v.label, v.placeholder)) {
      return `Please enter a valid ${v.label.toLowerCase()}`;
    }
  }

  // Type-specific validation
  if (v.field_type === "email" && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(strVal)) {
    return "Invalid email format";
  }
  if (v.field_type === "phone" && !/^[\d\s\-+()]{7,20}$/.test(strVal)) {
    return "Invalid phone format";
  }
  if (v.field_type === "url" && !/^https?:\/\/.+/.test(strVal)) {
    return "Invalid URL format";
  }
  if (v.field_type === "select" && v.choices && v.choices.length > 0) {
    const validValues = v.choices.map(c => c.value);
    if (!validValues.includes(strVal)) {
      return `Please select a valid ${v.label.toLowerCase()}`;
    }
  }

  // Numeric types (number, currency, duration)
  if (["number", "currency", "duration"].includes(v.field_type || "")) {
    const num = parseFloat(strVal);
    if (isNaN(num) || !/^\d+(\.\d+)?$/.test(strVal)) return `Must be a valid number`;
    const rawMin = rules.min !== undefined ? Number(rules.min) : v.min_length;
    const rawMax = rules.max !== undefined ? Number(rules.max) : v.max_length;
    const minVal = rawMin !== null && rawMin !== undefined ? rawMin : NaN;
    const maxVal = rawMax !== null && rawMax !== undefined ? rawMax : NaN;
    if (!isNaN(minVal) && num < minVal) return `Minimum value is ${minVal}`;
    if (!isNaN(maxVal) && num > maxVal) return `Maximum value is ${maxVal}`;
    if (v.field_type === "duration" && (!Number.isInteger(num) || num < 1)) {
      return `Must be a whole number greater than 0`;
    }
  }

  if (v.field_type === "date" && strVal) {
    const d = new Date(strVal);
    if (isNaN(d.getTime())) return "Invalid date";
  }

  // Min/max length for text
  if (v.min_length && strVal.length < v.min_length) {
    return `Minimum ${v.min_length} characters`;
  }
  if (v.max_length && strVal.length > v.max_length) {
    return `Maximum ${v.max_length} characters`;
  }

  // Regex pattern
  if (v.pattern && strVal) {
    try {
      if (!new RegExp(v.pattern).test(strVal)) {
        return v.pattern_message || `Invalid format`;
      }
    } catch { /* ignore bad regex */ }
  }

  return null;
}

function generateIdempotencyKey(): string {
  return `gen_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
}

export default function GenerateContractWizard({ preSelectedTemplateId, draftId }: GenerateContractWizardProps) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const idempotencyKey = useRef(draftId || generateIdempotencyKey());

  const [step, setStep] = useState(preSelectedTemplateId ? 1 : 0);
  const [selectedTemplateId, setSelectedTemplateId] = useState<string | null>(preSelectedTemplateId || null);
  const [templateVersionId, setTemplateVersionId] = useState<string | null>(null);
  const [variableValues, setVariableValues] = useState<Record<string, any>>({});
  const [title, setTitle] = useState("");
  const [clauseSelections, setClauseSelections] = useState<ClauseSelection[]>([]);
  const [expandedClauses, setExpandedClauses] = useState<Set<string>>(new Set());
  const [generated, setGenerated] = useState<GenerateContractResponse | null>(null);
  const [error, setError] = useState("");
  const [clauseError, setClauseError] = useState("");
  const [varErrors, setVarErrors] = useState<Record<string, string>>({});
  const [draftSaved, setDraftSaved] = useState(false);
  const [savingDraft, setSavingDraft] = useState(false);
  const [lastSavedAt, setLastSavedAt] = useState<Date | null>(null);
  const [confirmFinal, setConfirmFinal] = useState(false);
  const [resumed, setResumed] = useState(false);

  // ── Suggested Clauses state ─────────────────────────────────
  const [suggestedClauses, setSuggestedClauses] = useState<SuggestedClauseItem[]>([]);
  const [suggestedClauseSelections, setSuggestedClauseSelections] = useState<Record<string, boolean>>({});
  const [suggestionsLoading, setSuggestionsLoading] = useState(false);
  const [suggestionsError, setSuggestionsError] = useState("");
  const [downloadingDocx, setDownloadingDocx] = useState(false);

  // ── Load draft if draftId provided ─────────────────────────────
  const { data: draftData } = useQuery({
    queryKey: ["draft", draftId],
    queryFn: () => api.get<any>(`/templates/drafts/${draftId}`),
    enabled: !!draftId,
    staleTime: 0,
  });

  useEffect(() => {
    if (draftData && !resumed) {
      setResumed(true);
      setSelectedTemplateId(draftData.template_id);
      setTemplateVersionId(draftData.template_version_id);
      setVariableValues(draftData.variable_values || {});
      setTitle(draftData.title || "");
      if (draftData.clause_selections?.length > 0) {
        setClauseSelections(draftData.clause_selections);
      }
      setStep(1);
    }
  }, [draftData, resumed]);

  // ── Queries ──────────────────────────────────────────────────

  const { data: templatesData } = useQuery<PaginatedTemplateList>({
    queryKey: ["templates", "approved"],
    queryFn: () => api.get("/templates?status=approved&page_size=50"),
    staleTime: 30_000,
  });

  const { data: categoriesData } = useQuery<PaginatedCategoryList>({
    queryKey: ["template-categories"],
    queryFn: () => api.get("/templates/categories"),
    staleTime: 60_000,
  });

  const { data: templateDetail } = useQuery<TemplateDetail>({
    queryKey: ["template", selectedTemplateId],
    queryFn: () => api.get(`/templates/${selectedTemplateId}`),
    enabled: !!selectedTemplateId,
    staleTime: 30_000,
  });

  const { data: availableClauses } = useQuery({
    queryKey: ["available-clauses", selectedTemplateId],
    queryFn: () => api.get<any[]>(`/templates/${selectedTemplateId}/available-clauses`),
    enabled: !!selectedTemplateId,
    staleTime: 30_000,
  });

  // ── Pin template version on first load ───────────────────────
  useEffect(() => {
    if (templateDetail?.current_version && !templateVersionId && !draftId) {
      setTemplateVersionId(templateDetail.current_version.id);
    }
  }, [templateDetail, templateVersionId, draftId]);

  // ── Initialize clause selections ─────────────────────────────
  useEffect(() => {
    if (availableClauses && availableClauses.length > 0 && clauseSelections.length === 0 && !draftId) {
      const selections: ClauseSelection[] = availableClauses.map((ref: any) => ({
        clause_id: ref.clause_id,
        clause_title: ref.clause_title || ref.clause_id,
        clause_type: ref.clause_type || "general",
        risk_level: ref.risk_level,
        content: ref.clause_content || "",
        is_required: ref.is_required,
        included: ref.is_required,
        reason_removed: "",
        notes: "",
        fallback_clause_id: ref.fallback_clause_id,
      }));
      setClauseSelections(selections);
    }
  }, [availableClauses, draftId]);

  // ── Auto-save draft on step change ───────────────────────────
  const saveDraft = useCallback(async () => {
    if (!selectedTemplateId) return;
    setSavingDraft(true);
    try {
      await api.post("/templates/drafts", {
        template_id: selectedTemplateId,
        template_version_id: templateVersionId,
        variable_values: variableValues,
        clause_selections: clauseSelections
          .map((cs) => ({
            clause_id: cs.clause_id,
            included: cs.included,
            reason_removed: cs.included ? null : cs.reason_removed,
            notes: cs.notes || null,
          })),
        title: title || undefined,
        idempotency_key: idempotencyKey.current,
        status: "draft",
      });
      setDraftSaved(true);
      setLastSavedAt(new Date());
    } catch {
      // Silent fail for auto-save
    } finally {
      setSavingDraft(false);
    }
  }, [selectedTemplateId, templateVersionId, variableValues, clauseSelections, title]);

  // Auto-save on step transitions
  const prevStepRef = useRef(step);
  useEffect(() => {
    if (prevStepRef.current !== step && step > 0) {
      saveDraft();
    }
    prevStepRef.current = step;
  }, [step, saveDraft]);

  // ── Generate mutation ────────────────────────────────────────
  const generateMut = useMutation({
    mutationFn: async () => {
      if (!selectedTemplateId) throw new Error("No template selected");
      return api.post<GenerateContractResponse>(`/templates/${selectedTemplateId}/generate`, {
        template_id: selectedTemplateId,
        template_version_id: templateVersionId,
        variable_values: variableValues,
        clause_selections: clauseSelections
          .map((cs) => ({
            clause_id: cs.clause_id,
            included: cs.included,
            reason_removed: cs.included ? null : cs.reason_removed,
            notes: cs.notes || null,
          })),
        title: title || undefined,
        idempotency_key: idempotencyKey.current,
        status: "finalized",
      });
    },
    onSuccess: (data) => {
      setGenerated(data);
      setStep(5);
      queryClient.invalidateQueries({ queryKey: ["drafts"] });
      queryClient.invalidateQueries({ queryKey: ["contracts"] });
    },
    onError: (err: any) => {
      setError(err?.message || "Generation failed");
    },
  });

  const serverPreviewMut = useMutation({
    mutationFn: async () => {
      if (!selectedTemplateId) throw new Error("No template selected");
      return api.post<GenerateContractResponse>(`/templates/${selectedTemplateId}/preview`, {
        template_id: selectedTemplateId,
        template_version_id: templateVersionId,
        variable_values: variableValues,
        clause_selections: clauseSelections.map((cs) => ({
          clause_id: cs.clause_id,
          included: cs.included,
          reason_removed: cs.included ? null : cs.reason_removed,
          notes: cs.notes || null,
        })),
        title: title || undefined,
        preview_only: true,
      });
    },
  });

  const templates = (templatesData?.data ?? []).filter((t) => t.status === "approved");
  const categories = categoriesData?.data ?? [];
  const variables = templateDetail?.current_version?.variables ?? [];
  const [search, setSearch] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("all");
  const [sortBy, setSortBy] = useState<"usage" | "name" | "recent">("usage");
  const [previewHoverId, setPreviewHoverId] = useState<string | null>(null);

  // Get recently used from localStorage
  const recentlyUsedIds = useMemo(() => {
    try {
      const stored = localStorage.getItem("recentlyUsedTemplates");
      return stored ? JSON.parse(stored) as string[] : [];
    } catch { return []; }
  }, []);

  const filteredTemplates = useMemo(() => {
    let list = templates.filter((t) => {
      if (search && !t.name.toLowerCase().includes(search.toLowerCase())) return false;
      if (categoryFilter !== "all" && t.category_id !== categoryFilter) return false;
      return true;
    });
    // Sort
    if (sortBy === "usage") list.sort((a, b) => b.usage_count - a.usage_count);
    else if (sortBy === "name") list.sort((a, b) => a.name.localeCompare(b.name));
    else if (sortBy === "recent") list.sort((a, b) => (b.updated_at || "").localeCompare(a.updated_at || ""));
    return list;
  }, [templates, search, categoryFilter, sortBy]);

  // Recently used templates (pinned to top)
  const recentTemplates = useMemo(() => {
    return recentlyUsedIds.map((id) => templates.find((t) => t.id === id)).filter(Boolean) as typeof templates;
  }, [recentlyUsedIds, templates]);

  // ── Smart defaults ──────────────────────────────────────────
  useEffect(() => {
    if (templateDetail && Object.keys(variableValues).length === 0 && !draftId) {
      const defaults: Record<string, any> = {};
      const today = new Date().toISOString().split('T')[0];
      for (const v of variables) {
        if (v.default_value) {
          defaults[v.key] = v.default_value;
        } else if (v.key.toLowerCase().includes('effectivedate') || v.key.toLowerCase().includes('date')) {
          defaults[v.key] = today;
        } else if (v.key === 'Currency' || v.key === 'currency') {
          defaults[v.key] = 'USD';
        }
      }
      if (Object.keys(defaults).length > 0) {
        setVariableValues(defaults);
      }
    }
  }, [templateDetail, draftId]);

  // ── Evaluate recommendation rules when entering Step 2 ──────
  useEffect(() => {
    if (step === 2 && selectedTemplateId && Object.keys(variableValues).length > 0) {
      setSuggestionsLoading(true);
      setSuggestionsError("");
      api.post("/templates/recommendation-rules/evaluate", {
        variable_values: variableValues,
        template_id: selectedTemplateId,
      }).then((data: any) => {
        const clauses: SuggestedClauseItem[] = data.suggested_clauses || [];
        setSuggestedClauses(clauses);
        const selections: Record<string, boolean> = {};
        for (const c of clauses) {
          selections[c.clause_id] = c.is_checked;
        }
        setSuggestedClauseSelections(selections);
        setSuggestionsLoading(false);
      }).catch((err: any) => {
        setSuggestionsError(err?.message || "Failed to evaluate clause suggestions");
        setSuggestionsLoading(false);
      });
    }
  }, [step, selectedTemplateId, variableValues]);

  // ── Conditional logic: show/hide variables based on values ──
  const visibleVariables = useMemo(() => {
    return variables.filter((v) => {
      // If variable has a condition in validation_rules, check it
      const rules = v.validation_rules || {};
      const condition = (rules as any).condition;
      if (condition) {
        // Simple condition: {"field": "AutoRenewal", "equals": true}
        const fieldValue = variableValues[condition.field];
        return fieldValue === condition.equals;
      }
      return true;
    });
  }, [variables, variableValues]);

  // ── Cross-field validation ──────────────────────────────────
  const crossFieldErrors = useMemo(() => {
    const errors: Record<string, string> = {};
    // EndDate must be after EffectiveDate
    const effDate = variableValues['EffectiveDate'];
    const endDate = variableValues['EndDate'] || variableValues['DeliveryDate'];
    if (effDate && endDate && endDate < effDate) {
      const endKey = variableValues['EndDate'] ? 'EndDate' : 'DeliveryDate';
      errors[endKey] = 'Must be after Effective Date';
    }
    return errors;
  }, [variableValues]);
  const handleVariableChange = (key: string, value: any) => {
    setVariableValues((prev) => ({ ...prev, [key]: value }));
    setVarErrors((prev) => { const n = { ...prev }; delete n[key]; return n; });
    setDraftSaved(false);
  };

  const validateField = useCallback((v: TemplateVariable, value: any): string | null => {
    return validateVariableValue(v, value, variableValues);
  }, [variableValues]);

  // ── Group variables by section ──────────────────────────────
  const groupedVariables = useMemo(() => {
    const groups: Record<string, typeof visibleVariables> = {};
    const sectionOrder: string[] = [];
    for (const v of visibleVariables) {
      const section = v.section || "General";
      if (!groups[section]) {
        groups[section] = [];
        sectionOrder.push(section);
      }
      groups[section].push(v);
    }
    return { groups, sectionOrder };
  }, [visibleVariables]);

  const renderVariableInput = (v: TemplateVariable) => {
    const val = variableValues[v.key] ?? v.default_value ?? "";
    const err = varErrors[v.key] || crossFieldErrors[v.key];
    const hasDefault = v.default_value && variableValues[v.key] === v.default_value;
    const common = `w-full px-3 py-2 text-sm border rounded-lg focus:ring-1 ${
      err
        ? "border-red-300 focus:border-red-500 focus:ring-red-500"
        : "border-gray-200 focus:border-navy-400 focus:ring-navy-400"
    }`;

    const handleBlur = () => {
      const e = validateField(v, variableValues[v.key]);
      if (e) setVarErrors((prev) => ({ ...prev, [v.key]: e }));
      else setVarErrors((prev) => { const n = { ...prev }; delete n[v.key]; return n; });
    };

    const inputProps = { onBlur: handleBlur };

    switch (v.field_type) {
      case "date":
        return (
          <div>
            <input type="date" value={val} onChange={(e) => handleVariableChange(v.key, e.target.value)}
              className={common} {...inputProps} />
            <span className="text-[9px] text-gray-400 mt-0.5 block">Format: MM/DD/YYYY</span>
          </div>
        );
      case "currency":
        return (
          <div className="relative">
            <span className="absolute left-2.5 top-1/2 -translate-y-1/2 text-xs text-gray-400">$</span>
            <input type="text" inputMode="decimal" value={val}
              onChange={(e) => {
                // Strip non-numeric except dot
                const cleaned = e.target.value.replace(/[^0-9.]/g, "");
                handleVariableChange(v.key, cleaned);
              }}
              className={`${common} pl-6`}
              placeholder="0.00"
              {...inputProps} />
          </div>
        );
      case "number":
        return (
          <div className="relative">
            <input type="number" value={val} onChange={(e) => handleVariableChange(v.key, e.target.value)}
              className={common} {...inputProps} />
            {v.unit_label && (
              <span className="absolute right-2.5 top-1/2 -translate-y-1/2 text-[10px] text-gray-400 pointer-events-none">
                {v.unit_label}
              </span>
            )}
          </div>
        );
      case "duration":
        return (
          <div className="relative flex items-center">
            <button type="button" onClick={() => handleVariableChange(v.key, Math.max(1, (parseInt(val) || 1) - 1))}
              className="px-2 py-2 text-sm border rounded-l-lg bg-gray-50 hover:bg-gray-100 text-gray-600">−</button>
            <input type="number" min="1" step="1" value={val}
              onChange={(e) => {
                const n = parseInt(e.target.value);
                if (!isNaN(n) && n >= 1) handleVariableChange(v.key, n);
                else if (e.target.value === "") handleVariableChange(v.key, "");
              }}
              className={`${common} rounded-none text-center [appearance:textfield] [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none`}
              {...inputProps} />
            <button type="button" onClick={() => handleVariableChange(v.key, (parseInt(val) || 1) + 1)}
              className="px-2 py-2 text-sm border rounded-r-lg bg-gray-50 hover:bg-gray-100 text-gray-600">+</button>
            {v.unit_label && (
              <span className="ml-2 text-xs text-gray-500 min-w-fit">{v.unit_label}</span>
            )}
          </div>
        );
      case "boolean":
        return (
          <input type="checkbox" checked={!!val} onChange={(e) => handleVariableChange(v.key, e.target.checked)}
            className="w-4 h-4 rounded border-gray-300" />
        );
      case "select":
      case "dropdown":
        // If choices are defined, use them; otherwise use options
        const choices = v.choices || (v.options || []).map(o => ({ value: o, label: o }));
        return (
          <select value={val} onChange={(e) => handleVariableChange(v.key, e.target.value)} className={common}>
            <option value="">Select...</option>
            {choices.map((opt) => <option key={opt.value} value={opt.value}>{opt.label}</option>)}
          </select>
        );
      case "jurisdiction":
        return (
          <div className="space-y-1.5">
            <select value={val.split("/")[0] || ""} onChange={(e) => {
              const country = e.target.value;
              const states = JURISDICTIONS[country] || [];
              handleVariableChange(v.key, states.length === 1 ? `${country}/${states[0]}` : country);
            }} className={common}>
              <option value="">Select country...</option>
              {COMMON_COUNTRIES.map((c) => <option key={c} value={c}>{c}</option>)}
            </select>
            {val.split("/")[0] && (JURISDICTIONS[val.split("/")[0]] || []).length > 1 && (
              <select value={val.split("/")[1] || ""} onChange={(e) => {
                const country = val.split("/")[0];
                handleVariableChange(v.key, e.target.value ? `${country}/${e.target.value}` : country);
              }} className={common}>
                <option value="">Select state/province...</option>
                {(JURISDICTIONS[val.split("/")[0]] || []).map((s) => <option key={s} value={s}>{s}</option>)}
              </select>
            )}
          </div>
        );
      case "email":
        return <input type="email" value={val} onChange={(e) => handleVariableChange(v.key, e.target.value)} className={common} {...inputProps} />;
      case "phone":
        return <input type="tel" value={val} onChange={(e) => handleVariableChange(v.key, e.target.value)} className={common} {...inputProps} />;
      case "url":
        return <input type="url" value={val} onChange={(e) => handleVariableChange(v.key, e.target.value)} className={common} {...inputProps} />;
      case "address":
        return <textarea value={val} onChange={(e) => handleVariableChange(v.key, e.target.value)} rows={2} className={common} {...inputProps} />;
      default:
        return (
          <div className="relative">
            <input type="text" value={val} onChange={(e) => handleVariableChange(v.key, e.target.value)}
              className={common} placeholder={v.placeholder || `Enter ${v.label.toLowerCase()}`}
              {...inputProps} />
            {hasDefault && (
              <span className="absolute right-2 top-1/2 -translate-y-1/2 text-[8px] px-1 py-0.5 rounded bg-blue-50 text-blue-500 font-medium">
                Default
              </span>
            )}
          </div>
        );
    }
  };

  // ── Clause handlers ──────────────────────────────────────────
  const handleSelectTemplate = (id: string) => {
    setSelectedTemplateId(id);
    setStep(1);
    try {
      const stored = localStorage.getItem("recentlyUsedTemplates");
      const ids = stored ? JSON.parse(stored) as string[] : [];
      const updated = [id, ...ids.filter((i) => i !== id)].slice(0, 10);
      localStorage.setItem("recentlyUsedTemplates", JSON.stringify(updated));
    } catch { /* ignore */ }
  };

  // ── Group clauses by type ───────────────────────────────────
  const [collapsedTypes, setCollapsedTypes] = useState<Set<string>>(new Set());

  const groupedClauses = useMemo(() => {
    const groups: Record<string, typeof clauseSelections> = {};
    const typeOrder: string[] = [];
    for (const cs of clauseSelections) {
      const type = cs.clause_type || "other";
      if (!groups[type]) {
        groups[type] = [];
        typeOrder.push(type);
      }
      groups[type].push(cs);
    }
    return { groups, typeOrder };
  }, [clauseSelections]);

  const toggleTypeCollapse = (type: string) => {
    setCollapsedTypes((prev) => {
      const next = new Set(prev);
      if (next.has(type)) next.delete(type);
      else next.add(type);
      return next;
    });
  };

  const toggleClause = (clauseId: string) => {
    setClauseSelections((prev) =>
      prev.map((cs) => {
        if (cs.clause_id !== clauseId) return cs;
        // Required clauses cannot be toggled off directly — use exception flow
        if (cs.is_required && cs.included) return cs;
        return { ...cs, included: !cs.included, reason_removed: cs.included ? cs.reason_removed : "" };
      }),
    );
    setClauseError("");
    setDraftSaved(false);
  };

  // Exception flow state for Required clauses
  const [exceptionModal, setExceptionModal] = useState<{ clauseId: string; title: string } | null>(null);
  const [exceptionReason, setExceptionReason] = useState("");

  const requestException = (clauseId: string, title: string) => {
    setExceptionModal({ clauseId, title });
    setExceptionReason("");
  };

  const confirmException = () => {
    if (!exceptionModal || !exceptionReason.trim()) return;
    setClauseSelections((prev) =>
      prev.map((cs) =>
        cs.clause_id === exceptionModal.clauseId
          ? { ...cs, included: false, reason_removed: exceptionReason.trim() }
          : cs,
      ),
    );
    setExceptionModal(null);
    setExceptionReason("");
    setDraftSaved(false);
  };

  const updateClauseNote = (clauseId: string, notes: string) => {
    setClauseSelections((prev) =>
      prev.map((cs) => (cs.clause_id === clauseId ? { ...cs, notes } : cs)),
    );
    setDraftSaved(false);
  };

  const updateClauseReason = (clauseId: string, reason_removed: string) => {
    setClauseSelections((prev) =>
      prev.map((cs) => (cs.clause_id === clauseId ? { ...cs, reason_removed } : cs)),
    );
    setDraftSaved(false);
  };

  const toggleExpanded = (clauseId: string) => {
    setExpandedClauses((prev) => {
      const next = new Set(prev);
      if (next.has(clauseId)) next.delete(clauseId);
      else next.add(clauseId);
      return next;
    });
  };

  // Auto-expand critical and required clauses
  useEffect(() => {
    setExpandedClauses((prev) => {
      const next = new Set(prev);
      for (const cs of clauseSelections) {
        if (cs.risk_level === "critical" || cs.is_required) {
          next.add(cs.clause_id);
        }
      }
      return next;
    });
  }, [clauseSelections.length]);

  const resetToRecommended = () => {
    setClauseSelections((prev) =>
      prev.map((cs) => ({ ...cs, included: cs.is_required, reason_removed: "" })),
    );
    setClauseError("");
  };

  // ── Risk score computation ───────────────────────────────────
  const riskScore = useMemo(() => {
    const criticalIncluded = clauseSelections.filter((cs) => cs.included && cs.risk_level === "critical").length;
    const highIncluded = clauseSelections.filter((cs) => cs.included && cs.risk_level === "high").length;
    const criticalExcluded = clauseSelections.filter((cs) => !cs.included && cs.risk_level === "critical").length;
    const highExcluded = clauseSelections.filter((cs) => !cs.included && cs.risk_level === "high").length;
    const totalCritical = clauseSelections.filter((cs) => cs.risk_level === "critical").length;
    const totalHigh = clauseSelections.filter((cs) => cs.risk_level === "high").length;

    // Base score: 100 - penalty for excluded critical/high
    let score = 100;
    score -= criticalExcluded * 25;
    score -= highExcluded * 10;

    // Bonus for including critical/high (up to 10 points)
    if (totalCritical > 0) score += Math.min(10, (criticalIncluded / totalCritical) * 10);
    if (totalHigh > 0) score += Math.min(5, (highIncluded / totalHigh) * 5);

    score = Math.max(0, Math.min(100, score));
    const level = score >= 80 ? "Low" : score >= 50 ? "Medium" : "High";
    return { score: Math.round(score), level, criticalExcluded, highExcluded, criticalIncluded, highIncluded, totalCritical, totalHigh };
  }, [clauseSelections]);

  // ── Step-level validation state (persistent, re-checked on mount/navigation) ──
  const stepValidity = useMemo(() => {
    const result: Record<number, { valid: boolean; errors: string[] }> = {
      0: { valid: !!selectedTemplateId, errors: selectedTemplateId ? [] : ["No template selected"] },
      1: { valid: true, errors: [] },
      2: { valid: true, errors: [] },
      3: { valid: true, errors: [] },
      4: { valid: true, errors: [] },
      5: { valid: true, errors: [] },
    };

    // Step 1 (Fill Variables) validation
    const varErrorsList: string[] = [];
    for (const v of variables) {
      const e = validateField(v, variableValues[v.key]);
      if (e) varErrorsList.push(e);
    }
    result[1] = { valid: varErrorsList.length === 0, errors: varErrorsList };

    // Step 3 (Clause Selection) validation
    const clauseErrorsList: string[] = [];
    for (const cs of clauseSelections) {
      if (cs.is_required && !cs.included && !cs.reason_removed.trim()) {
        clauseErrorsList.push(`Required clause "${cs.clause_title}" needs an exclusion reason`);
      }
      if (!cs.included && cs.risk_level === "critical" && (!cs.notes || cs.notes.trim().length < 20)) {
        clauseErrorsList.push(`Critical clause "${cs.clause_title}" excluded without justification (min 20 chars)`);
      }
    }
    result[3] = { valid: clauseErrorsList.length === 0, errors: clauseErrorsList };

    return result;
  }, [selectedTemplateId, variables, variableValues, clauseSelections, validateField]);

  // ── "Required fields remaining" for Step 1 ──
  const requiredFieldsRemaining = useMemo(() => {
    return variables
      .filter((v) => v.is_required && !variableValues[v.key])
      .map((v) => v.label);
  }, [variables, variableValues]);

  // ── Step 2 validation gate ───────────────────────────────────
  const handleNextFromVariables = () => {
    const errors: Record<string, string> = {};
    let hasError = false;
    for (const v of variables) {
      const e = validateField(v, variableValues[v.key]);
      if (e) {
        errors[v.key] = e;
        hasError = true;
      }
    }
    setVarErrors(errors);
    if (hasError) {
      setError("Please fix the highlighted fields before proceeding.");
      return;
    }
    setError("");
    setStep(step + 1);
  };

  // ── Step 3 validation gate ───────────────────────────────────
  const handleNextFromClauses = () => {
    // Required clauses must have reason if excluded
    const missingReasons = clauseSelections.filter(
      (cs) => cs.is_required && !cs.included && !cs.reason_removed.trim(),
    );
    if (missingReasons.length > 0) {
      setClauseError(
        `Please provide a reason for removing: ${missingReasons.map((cs) => cs.clause_title).join(", ")}`,
      );
      return;
    }
    // Critical clauses must have ≥20 char notes if excluded
    const missingNotes = clauseSelections.filter(
      (cs) => !cs.included && cs.risk_level === "critical" && (!cs.notes || cs.notes.trim().length < 20),
    );
    if (missingNotes.length > 0) {
      setClauseError(
        `Please provide a justification (min 20 characters) for excluding: ${missingNotes.map((cs) => cs.clause_title).join(", ")}`,
      );
      return;
    }
    setClauseError("");
    setStep(step + 1);
  };

  // ── Preview content + view mode ─────────────────────────────
  const [previewMode, setPreviewMode] = useState<"rendered" | "raw">("rendered");

  const previewContent = useMemo(() => {
    if (serverPreviewMut.data?.preview_content) return serverPreviewMut.data.preview_content;
    if (!templateDetail?.current_version?.placeholder_content) return "";
    let text = templateDetail.current_version.placeholder_content;
    for (const [key, val] of Object.entries(variableValues)) {
      text = text.replace(new RegExp(`\\{\\{${key}\\}\\}`, "g"), val ? String(val) : `<span class="text-red-500 font-bold">{{${key}}}</span>`);
    }
    const included = clauseSelections.filter((cs) => cs.included);
    for (const cs of included) {
      if (cs.content) {
        text += `\n\n## ${cs.clause_title}\n\n${cs.content}`;
      }
    }
    return text;
  }, [serverPreviewMut.data?.preview_content, templateDetail, variableValues, clauseSelections]);

  useEffect(() => {
    if (step === 4 && selectedTemplateId) {
      serverPreviewMut.mutate();
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [step, selectedTemplateId, variableValues, clauseSelections, title, templateVersionId]);

  // Rendered preview (formatted) — single implementation
  const renderedPreview = useMemo(() => {
    const raw = previewContent || "";
    // Convert markdown-like formatting to HTML
    return raw
      .split('\n\n')
      .map((p, i) => {
        const trimmed = p.trim();
        if (!trimmed) return '';
        // Headings
        if (trimmed.startsWith('## ')) {
          return `<h3 key={i} class="text-sm font-bold text-navy-800 mt-4 mb-2">${trimmed.replace('## ', '')}</h3>`;
        }
        if (trimmed.startsWith('**') && trimmed.endsWith('**')) {
          return `<h4 key={i} class="text-xs font-semibold text-navy-700 mt-3 mb-1">${trimmed.replace(/\*\*/g, '')}</h4>`;
        }
        return `<p key={i} class="text-xs leading-relaxed text-gray-700 mb-2">${trimmed.replace(/\n/g, '<br/>')}</p>`;
      })
      .filter(Boolean)
      .join('');
  }, [previewContent]);

  // Count unfilled variables (those with empty or invalid values)
  const unfilledVars = useMemo(() => {
    return variables.filter((v) => {
      const val = variableValues[v.key];
      return !val || String(val).trim() === "" || validateField(v, val) !== null;
    });
  }, [variables, variableValues, validateField]);

  const riskColor = (level?: string | null) => {
    const colors: Record<string, string> = {
      critical: "bg-red-100 text-red-700",
      high: "bg-orange-100 text-orange-700",
      medium: "bg-yellow-100 text-yellow-700",
      low: "bg-green-100 text-green-700",
    };
    return colors[level || ""] || "bg-gray-100 text-gray-600";
  };

  // ── Locale-aware formatting ─────────────────────────────────
  const locale = typeof navigator !== 'undefined' ? navigator.language : 'en-US';
  const dateFormatter = useMemo(() => new Intl.DateTimeFormat(locale, { dateStyle: 'medium' }), [locale]);
  const currencyFormatter = useMemo(() => new Intl.NumberFormat(locale, { style: 'currency', currency: 'USD' }), [locale]);
  const numberFormatter = useMemo(() => new Intl.NumberFormat(locale), [locale]);

  const formatValue = (key: string, val: any): string => {
    if (!val) return '';
    const v = variables.find((x) => x.key === key);
    if (v?.field_type === 'date') {
      try { return dateFormatter.format(new Date(val)); } catch { return val; }
    }
    if (v?.field_type === 'currency') {
      try { return currencyFormatter.format(parseFloat(val)); } catch { return val; }
    }
    if (v?.field_type === 'number') {
      try { return numberFormatter.format(parseFloat(val)); } catch { return val; }
    }
    return String(val);
  };

  const requiredCount = variables.filter((v) => v.is_required).length;
  const filledRequired = variables.filter((v) => v.is_required && variableValues[v.key] && String(variableValues[v.key]).trim()).length;

  // ── Browser close warning ────────────────────────────────────
  useEffect(() => {
    const handler = (e: BeforeUnloadEvent) => {
      if (!generated) {
        e.preventDefault();
        e.returnValue = "";
      }
    };
    window.addEventListener("beforeunload", handler);
    return () => window.removeEventListener("beforeunload", handler);
  }, [generated]);

  // ── Auto-redirect countdown ─────────────────────────────────
  const [redirectCountdown, setRedirectCountdown] = useState(12);
  const [redirected, setRedirected] = useState(false);

  useEffect(() => {
    if (generated && !redirected) {
      const timer = setInterval(() => {
        setRedirectCountdown((prev) => {
          if (prev <= 1) {
            clearInterval(timer);
            return 0;
          }
          return prev - 1;
        });
      }, 1000);
      return () => clearInterval(timer);
    }
  }, [generated, redirected]);

  // Separate effect for redirect to avoid setState inside functional updater
  useEffect(() => {
    if (redirectCountdown <= 0 && generated?.review_id && !redirected) {
      setRedirected(true);
      router.push(`/contracts/${generated.review_id}`);
    }
  }, [redirectCountdown, generated, redirected, router]);

  const handleDownloadGeneratedDocx = async () => {
    if (!generated?.review_id) return;
    setDownloadingDocx(true);
    try {
      let versionId = generated.document_version_id;
      if (!versionId) {
        const versions = await reviewService.listVersions(generated.review_id);
        versionId = versions[0]?.version_id;
      }
      if (!versionId) {
        throw new Error("Document version not available yet");
      }
      await reviewService.downloadVersion(
        generated.review_id,
        versionId,
        `${generated.title || "contract"}.docx`,
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Download failed");
    } finally {
      setDownloadingDocx(false);
    }
  };

  // ── Live pipeline status polling ────────────────────────────
  const [pipelineStatus, setPipelineStatus] = useState<ReviewStatusResponse | null>(null);
  const [pipelineElapsed, setPipelineElapsed] = useState(0);
  const POLL_INTERVAL = 5000; // 5 seconds

  useEffect(() => {
    if (!generated?.review_id) return;

    const interval = setInterval(async () => {
      try {
        const status = await reviewService.getStatus(generated.review_id);
        setPipelineStatus(status);
      } catch {
        // Silently retry on next interval
      }
    }, POLL_INTERVAL);

    // Initial fetch
    reviewService.getStatus(generated.review_id).then(setPipelineStatus).catch(() => {});

    return () => clearInterval(interval);
  }, [generated?.review_id]);

  // Elapsed timer
  useEffect(() => {
    if (!generated) return;
    const interval = setInterval(() => {
      setPipelineElapsed((prev) => prev + 1);
    }, 1000);
    return () => clearInterval(interval);
  }, [generated]);

  // Derive current pipeline stage from status
  const pipelineStage = useMemo<{
    stage: "ingestion" | "ai_review" | "ready" | "error";
    label: string;
    progress: number;
    eta: string;
  }>(() => {
    const s = pipelineStatus;
    if (!s) {
      return { stage: "ingestion", label: "Starting ingestion…", progress: 10, eta: "~30s" };
    }

    const ingestion = s.ingestion_state || "";
    const aiStatus = s.ai_status || "";
    const reviewStatus = s.review_status || "";

    // Error state
    if (s.error || ingestion === "failed") {
      return { stage: "error", label: s.error || "Ingestion failed", progress: 0, eta: "—" };
    }

    // Ingestion pipeline stages
    if (["uploaded", "validating", "validated", "storage_confirmed", "ocr_pending", "ocr_processing", "ocr_complete", "chunking_pending", "chunking_processing", "embedding_pending", "embedding_processing"].includes(ingestion)) {
      return { stage: "ingestion", label: "Ingesting document…", progress: 30, eta: "~1-2 min" };
    }

    // Ready for AI analysis
    if (ingestion === "review_ready" || ingestion === "analysis_pending") {
      return { stage: "ai_review", label: "AI review pending…", progress: 45, eta: "~30s" };
    }

    // AI analysis running
    if (aiStatus === "processing" || aiStatus === "pending") {
      return { stage: "ai_review", label: "AI analyzing contract…", progress: 60, eta: "~1-2 min" };
    }

    // AI analysis complete
    if (aiStatus === "completed" || reviewStatus === "ai_analyzed") {
      return { stage: "ready", label: "Ready for review!", progress: 100, eta: "Now" };
    }

    return { stage: "ingestion", label: "Processing…", progress: 20, eta: "~30s" };
  }, [pipelineStatus]);

  const stageIcon = (stage: string) => {
    if (stage === "ingestion") return pipelineStage.stage === "ingestion" ? "animate-pulse" : "text-green-500";
    if (stage === "ai_review") {
      if (pipelineStage.stage === "ingestion") return "text-gray-300";
      if (pipelineStage.stage === "ai_review") return "animate-pulse";
      return "text-green-500";
    }
    if (stage === "ready") {
      if (pipelineStage.stage === "ready") return "text-green-500";
      return "text-gray-300";
    }
    return "text-gray-300";
  };

  // ── Render ───────────────────────────────────────────────────
  if (generated) {
    const includedClauses = clauseSelections.filter((cs) => cs.included);
    const excludedClauses = clauseSelections.filter((cs) => !cs.included);
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40" onClick={() => {}}>
        <div className="bg-white dark:bg-navy-800 rounded-2xl shadow-2xl max-w-lg w-full mx-4 max-h-[90vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
          <div className="p-6 space-y-5">
            {/* Success header */}
            <div className="text-center space-y-3">
              <div className="w-16 h-16 rounded-full bg-green-100 dark:bg-green-900/20 flex items-center justify-center mx-auto">
                <Check className="w-8 h-8 text-green-600" />
              </div>
              <div>
                <h2 className="text-xl font-bold text-navy-900 dark:text-white">Contract Generated</h2>
                <p className="text-sm text-gray-500 mt-1">{generated.title}</p>
                <p className="text-[11px] text-purple-600 mt-2 flex items-center justify-center gap-1">
                  <Sparkles className="w-3.5 h-3.5" /> Document ingestion and AI review queued — findings will populate shortly
                </p>
              </div>
            </div>

            {/* ── Live Pipeline Status ── */}
            <div className={`rounded-lg border p-4 text-center transition-colors ${
              pipelineStage.stage === "error" ? "border-red-200 bg-red-50" :
              pipelineStage.stage === "ready" ? "border-green-200 bg-green-50" :
              "border-purple-200 bg-purple-50"
            }`}>
              {/* Stage icons with animated connector */}
              <div className="flex items-center justify-center gap-1">
                {/* Ingestion */}
                <div className={`w-8 h-8 rounded-full flex items-center justify-center transition-all ${
                  pipelineStage.stage === "ingestion" ? "bg-purple-600 scale-110" :
                  pipelineStage.stage === "ai_review" || pipelineStage.stage === "ready" ? "bg-green-500" :
                  "bg-gray-200"
                }`}>
                  {pipelineStage.stage === "ready" || pipelineStage.stage === "ai_review" ? (
                    <Check className="w-4 h-4 text-white" />
                  ) : (
                    <Loader2 className={`w-4 h-4 text-white ${pipelineStage.stage === "ingestion" ? "animate-spin" : ""}`} />
                  )}
                </div>
                <div className={`w-8 h-0.5 ${pipelineStage.stage === "ai_review" || pipelineStage.stage === "ready" ? "bg-green-400" : "bg-gray-200"}`} />

                {/* AI Review */}
                <div className={`w-8 h-8 rounded-full flex items-center justify-center transition-all ${
                  pipelineStage.stage === "ai_review" ? "bg-purple-600 scale-110" :
                  pipelineStage.stage === "ready" ? "bg-green-500" :
                  "bg-gray-200"
                }`}>
                  {pipelineStage.stage === "ready" ? (
                    <Check className="w-4 h-4 text-white" />
                  ) : (
                    <Sparkles className={`w-4 h-4 text-white ${pipelineStage.stage === "ai_review" ? "animate-pulse" : ""}`} />
                  )}
                </div>
                <div className={`w-8 h-0.5 ${pipelineStage.stage === "ready" ? "bg-green-400" : "bg-gray-200"}`} />

                {/* Ready */}
                <div className={`w-8 h-8 rounded-full flex items-center justify-center transition-all ${
                  pipelineStage.stage === "ready" ? "bg-green-500 scale-110" : "bg-gray-200"
                }`}>
                  <Check className={`w-4 h-4 ${pipelineStage.stage === "ready" ? "text-white" : "text-gray-400"}`} />
                </div>
              </div>

              {/* Label + ETA */}
              <div className="mt-3 space-y-1">
                <p className={`text-xs font-semibold ${
                  pipelineStage.stage === "error" ? "text-red-700" :
                  pipelineStage.stage === "ready" ? "text-green-700" :
                  "text-purple-700"
                }`}>
                  {pipelineStage.stage === "error" ? (
                    <><AlertTriangle className="w-3.5 h-3.5 inline mr-1" />{pipelineStage.label}</>
                  ) : pipelineStage.stage === "ready" ? (
                    <><Check className="w-3.5 h-3.5 inline mr-1" />{pipelineStage.label}</>
                  ) : (
                    <>{pipelineStage.label}</>
                  )}
                </p>
                {pipelineStage.stage !== "ready" && pipelineStage.stage !== "error" && (
                  <p className="text-[9px] text-gray-500">
                    Estimated wait: {pipelineStage.eta} · {Math.floor(pipelineElapsed / 60)}m{pipelineElapsed % 60}s elapsed
                  </p>
                )}
                {pipelineStage.stage === "ready" && (
                  <p className="text-[9px] text-green-600">Completed in {Math.floor(pipelineElapsed / 60)}m{pipelineElapsed % 60}s</p>
                )}
              </div>

              {/* Progress bar */}
              {pipelineStage.stage !== "error" && (
                <div className="mt-2 h-1 bg-gray-200 rounded-full overflow-hidden">
                  <div className={`h-full rounded-full transition-all duration-1000 ease-out ${
                    pipelineStage.stage === "ready" ? "bg-green-500" : "bg-purple-500"
                  }`} style={{ width: `${pipelineStage.progress}%` }} />
                </div>
              )}
            </div>

            {/* Summary card */}
            <div className="rounded-lg border border-gray-200 dark:border-navy-700 divide-y divide-gray-100 dark:divide-navy-700">
              <div className="flex justify-between px-4 py-2.5 text-xs">
                <span className="text-gray-500">Status</span>
                <span className="font-medium text-green-600 capitalize">{generated.status}</span>
              </div>
              <div className="flex justify-between px-4 py-2.5 text-xs">
                <span className="text-gray-500">Template</span>
                <span className="font-medium">{templateDetail?.name}</span>
              </div>
              <div className="flex justify-between px-4 py-2.5 text-xs">
                <span className="text-gray-500">Variables Filled</span>
                <span className="font-medium">{Object.keys(variableValues).length}</span>
              </div>
              <div className="flex justify-between px-4 py-2.5 text-xs">
                <span className="text-gray-500">Clauses Included</span>
                <span className="font-medium">{includedClauses.length}</span>
              </div>
              <div className="flex justify-between px-4 py-2.5 text-xs">
                <span className="text-gray-500">Review ID</span>
                <span className="font-mono text-[9px]">{generated.review_id}</span>
              </div>
            </div>

            {/* Included clauses */}
            {includedClauses.length > 0 && (
              <div>
                <h3 className="text-[10px] font-semibold text-gray-500 uppercase mb-2">Included Clauses ({includedClauses.length})</h3>
                <div className="space-y-1">
                  {includedClauses.map((cs) => (
                    <div key={cs.clause_id} className="flex items-center gap-1.5 text-[10px]">
                      <Check className="w-3 h-3 text-green-500 flex-shrink-0" />
                      <span className="text-gray-700 dark:text-gray-300">{cs.clause_title}</span>
                      <span className={`text-[7px] px-1 py-0.5 rounded-full ${riskColor(cs.risk_level)}`}>{cs.risk_level}</span>
                      {cs.notes && <span className="text-gray-400 italic">— {cs.notes}</span>}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Excluded clauses */}
            {excludedClauses.length > 0 && (
              <div className="rounded-lg border border-red-200 dark:border-red-900/30 bg-red-50/50 p-3">
                <h3 className="text-[10px] font-semibold text-red-600 uppercase mb-1">Excluded Clauses ({excludedClauses.length})</h3>
                <div className="space-y-1">
                  {excludedClauses.map((cs) => (
                    <div key={cs.clause_id} className="flex items-start gap-1.5 text-[9px] text-red-500">
                      <XCircle className="w-3 h-3 mt-0.5 flex-shrink-0" />
                      <div>
                        <span className="line-through">{cs.clause_title}</span>
                        {cs.reason_removed && <span className="text-red-400 italic"> — {cs.reason_removed}</span>}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Auto-redirect notice */}
            <div className="text-center text-[10px] text-gray-400">
              {redirected ? "Redirect cancelled." : `Opening Contract 360 in ${redirectCountdown}s…`}
              {!redirected && (
                <button onClick={() => setRedirected(true)} className="ml-2 text-navy-600 hover:underline">
                  Cancel
                </button>
              )}
            </div>

            {/* Actions */}
            <div className="flex flex-col items-center gap-2 pt-1">
              <div className="flex items-center justify-center gap-3 flex-wrap">
                <button onClick={() => { setRedirected(true); router.push(`/contracts/${generated.review_id}`); }}
                  className="inline-flex items-center gap-1.5 px-4 py-2 text-sm font-medium rounded-lg bg-navy-700 text-white hover:bg-navy-800">
                  <ExternalLink className="w-4 h-4" /> Open Contract 360
                </button>
                <button onClick={() => { setRedirected(true); router.push(`/reviews/ai-workspace?contractId=${generated.review_id}`); }}
                  className="inline-flex items-center gap-1.5 px-4 py-2 text-sm font-medium rounded-lg bg-purple-600 text-white hover:bg-purple-700">
                  <Sparkles className="w-4 h-4" /> Start AI Review
                </button>
                {(generated.generated_docx_url || generated.review_id) && (
                  <button
                    type="button"
                    onClick={handleDownloadGeneratedDocx}
                    disabled={downloadingDocx}
                    className="inline-flex items-center gap-1.5 px-4 py-2 text-sm font-medium rounded-lg border border-gray-200 text-gray-700 hover:bg-gray-50 disabled:opacity-50"
                  >
                    <FileDown className="w-4 h-4" />
                    {downloadingDocx ? "Downloading…" : "Download DOCX"}
                  </button>
                )}
              </div>
              <button onClick={() => { setRedirected(true); router.push("/templates"); }}
                className="text-xs text-gray-500 hover:text-gray-700">
                Back to Template Library
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-4xl mx-auto space-y-6">
      {/* Enterprise wizard header */}
      <div className="rounded-xl border border-navy-100 bg-gradient-to-r from-navy-50 to-white dark:from-navy-900 dark:to-navy-800 dark:border-navy-700 p-4">
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-[10px] font-semibold uppercase tracking-wider text-navy-500">Contract Generation Wizard</p>
            <h1 className="text-lg font-bold text-navy-900 dark:text-white mt-0.5">
              {STEP_META[step]?.title || "Generate Contract"}
            </h1>
            <p className="text-xs text-gray-500 mt-1">{STEP_META[step]?.description}</p>
          </div>
          <div className="text-right">
            <p className="text-[10px] text-gray-400">Step {step + 1} of {STEPS.length}</p>
            <p className="text-sm font-semibold text-navy-700 dark:text-navy-200">{Math.round(((step + 1) / STEPS.length) * 100)}%</p>
          </div>
        </div>
        <div className="mt-3 h-1.5 bg-gray-200 dark:bg-navy-700 rounded-full overflow-hidden">
          <div className="h-full bg-navy-600 rounded-full transition-all" style={{ width: `${((step + 1) / STEPS.length) * 100}%` }} />
        </div>
      </div>

      {/* Stepper */}
      <div className="flex items-center gap-2">
        {STEPS.map((s, i) => (
          <React.Fragment key={s}>
            <div className={`flex items-center gap-1.5 ${i <= step ? "text-navy-700 dark:text-navy-200" : "text-gray-400"}`}>
              <div className={`w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-bold ${
                i < step ? "bg-green-500 text-white" : i === step ? "bg-navy-600 text-white" : "bg-gray-200 text-gray-500"
              }`}>
                {i < step ? <Check className="w-3 h-3" /> : i + 1}
              </div>
              <span className="text-[10px] font-medium hidden sm:inline">{s}</span>
            </div>
            {i < STEPS.length - 1 && <div className={`flex-1 h-px ${i < step ? "bg-green-500" : "bg-gray-200"}`} />}
          </React.Fragment>
        ))}
      </div>

      {/* Draft saved indicator */}
      {draftSaved && step > 0 && step < 6 && (
        <div className="flex items-center gap-1.5 text-[9px] text-green-600 justify-end">
          <Check className="w-3 h-3" /> Draft saved
          {lastSavedAt && (
            <span className="text-gray-400">
              · {Math.max(1, Math.floor((Date.now() - lastSavedAt.getTime()) / 1000))}s ago
            </span>
          )}
        </div>
      )}
      {savingDraft && (
        <div className="flex items-center gap-1.5 text-[9px] text-gray-400 justify-end">
          <Loader2 className="w-3 h-3 animate-spin" /> Saving draft...
        </div>
      )}

      {error && (
        <div className="flex items-center gap-2 p-3 rounded-lg bg-red-50 border border-red-200 text-red-700 text-xs">
          <AlertTriangle className="w-4 h-4" /> {error}
        </div>
      )}

      {/* Step 0: Select Template */}
      {step === 0 && (
        <div className="space-y-4">
          <h2 className="text-lg font-semibold text-navy-900 dark:text-white">Select a Template</h2>
          <div className="flex items-center gap-3">
            <input type="text" value={search} onChange={(e) => setSearch(e.target.value)}
              placeholder="Search templates..."
              className="flex-1 px-3 py-2 text-sm border border-gray-200 rounded-lg focus:border-navy-400 focus:ring-1 focus:ring-navy-400" />
            <select value={categoryFilter} onChange={(e) => setCategoryFilter(e.target.value)}
              className="px-3 py-2 text-sm border border-gray-200 rounded-lg">
              <option value="all">All Categories</option>
              {categories.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
            </select>
            <select value={sortBy} onChange={(e) => setSortBy(e.target.value as any)}
              className="px-3 py-2 text-sm border border-gray-200 rounded-lg">
              <option value="usage">Most Used</option>
              <option value="name">A-Z</option>
              <option value="recent">Recently Updated</option>
            </select>
          </div>

          {/* Recently used */}
          {recentTemplates.length > 0 && (
            <div>
              <p className="text-[10px] font-semibold text-gray-500 uppercase mb-2">Recently Used</p>
              <div className="flex gap-2 overflow-x-auto pb-2">
                {recentTemplates.map((t) => (
                  <button key={t.id} onClick={() => handleSelectTemplate(t.id)}
                    className="flex-shrink-0 text-left p-3 rounded-xl border border-navy-200 bg-navy-50/50 hover:bg-navy-50 hover:border-navy-400 transition-all max-w-[200px]">
                    <p className="text-xs font-semibold text-navy-900 truncate">{t.name}</p>
                    <p className="text-[9px] text-gray-500 mt-0.5">{t.usage_count} uses</p>
                  </button>
                ))}
              </div>
            </div>
          )}

          <div className="grid grid-cols-2 gap-3 max-h-96 overflow-y-auto">
            {filteredTemplates.map((t) => {
              const cat = categories.find((c) => c.id === t.category_id);
              return (
                <button key={t.id}
                  onMouseEnter={() => setPreviewHoverId(t.id)}
                  onMouseLeave={() => setPreviewHoverId(null)}
                  onClick={() => handleSelectTemplate(t.id)}
                  className={`text-left p-4 rounded-xl border transition-all relative ${
                    selectedTemplateId === t.id
                      ? "border-navy-400 bg-navy-50 dark:bg-navy-800/50"
                      : "border-gray-200 dark:border-navy-700 bg-white dark:bg-navy-800 hover:border-gray-300 hover:shadow-sm"
                  }`}>
                  <div className="flex items-center gap-2 mb-1">
                    <FileText className="w-4 h-4 text-navy-500" />
                    <span className="text-sm font-semibold text-navy-900 dark:text-white">{t.name}</span>
                    {t.is_favorite && <Star className="w-3 h-3 text-yellow-500" fill="currentColor" />}
                  </div>
                  {t.description && <p className="text-[10px] text-gray-500 line-clamp-2">{t.description}</p>}
                  <div className="flex items-center gap-2 mt-2 text-[9px] text-gray-400">
                    {cat && <span>{cat.name}</span>}
                    {t.current_version_number && <span>· v{t.current_version_number}</span>}
                    <span>· {t.usage_count} uses</span>
                  </div>
                  {/* Preview on hover tooltip */}
                  {previewHoverId === t.id && t.description && (
                    <div className="absolute z-10 left-0 right-0 top-full mt-1 p-3 rounded-lg bg-white dark:bg-navy-800 border border-gray-200 dark:border-navy-700 shadow-lg text-[10px] text-gray-600 dark:text-gray-400">
                      <p className="font-medium text-navy-900 dark:text-white mb-1">{t.name}</p>
                      <p>{t.description}</p>
                      {t.department && <p className="mt-1 text-gray-400">Dept: {t.department}</p>}
                    </div>
                  )}
                </button>
              );
            })}
            {filteredTemplates.length === 0 && (
              <div className="col-span-2 text-center py-8 text-sm text-gray-400">No approved templates found.</div>
            )}
          </div>
        </div>
      )}

      {/* Step 1: Fill Variables */}
      {step === 1 && templateDetail && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-semibold text-navy-900 dark:text-white">Fill Variables</h2>
              {requiredCount > 0 && (
                <p className="text-[10px] text-gray-500 mt-0.5">
                  {filledRequired} of {requiredCount} required fields complete
                  {filledRequired < requiredCount && (
                    <span className="text-amber-600 ml-1">({requiredCount - filledRequired} remaining)</span>
                  )}
                </p>
              )}
            </div>
            <p className="text-xs text-gray-500">{templateDetail.name} · v{templateDetail.current_version?.version_number}</p>
          </div>

          {/* Required fields remaining list */}
          {requiredFieldsRemaining.length > 0 && (
            <div className="rounded-lg border border-amber-200 bg-amber-50 p-3">
              <p className="text-[9px] font-medium text-amber-700 mb-1.5 flex items-center gap-1">
                <AlertCircle className="w-3 h-3" /> Required fields remaining ({requiredFieldsRemaining.length})
              </p>
              <div className="flex flex-wrap gap-1">
                {requiredFieldsRemaining.map((label) => (
                  <span key={label} className="text-[8px] px-1.5 py-0.5 rounded bg-amber-100 text-amber-700 font-medium cursor-pointer hover:bg-amber-200">
                    {label}
                  </span>
                ))}
              </div>
            </div>
          )}

          <div className="space-y-1">
            <label className="text-[10px] font-medium text-gray-600">Contract Title</label>
            <input type="text" value={title} onChange={(e) => setTitle(e.target.value)}
              placeholder={`${templateDetail.name} - ${new Date().toLocaleDateString()}`}
              className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:border-navy-400 focus:ring-1 focus:ring-navy-400" />
          </div>
          {variables.length === 0 ? (
            <p className="text-sm text-gray-400 italic">No variables to fill. This template has no placeholders.</p>
          ) : (
            <div className="space-y-4">
              {groupedVariables.sectionOrder.map((section) => (
                <div key={section}>
                  <h3 className="text-[10px] font-semibold text-gray-500 uppercase tracking-wider mb-2 pb-1 border-b border-gray-100 dark:border-navy-700">
                    {section}
                  </h3>
                  <div className="grid grid-cols-2 gap-3">
                    {groupedVariables.groups[section].map((v) => (
                      <div key={v.key}>
                        <label className="flex items-center gap-1 text-[10px] font-medium text-gray-600 mb-1">
                          {v.label}
                          {v.is_required && <span className="text-red-500">*</span>}
                          <span className="text-gray-400 font-mono">({`{{${v.key}}}`})</span>
                        </label>
                        {renderVariableInput(v)}
                        {(varErrors[v.key] || crossFieldErrors[v.key]) && (
                          <p className="text-[9px] text-red-500 mt-0.5 flex items-center gap-0.5">
                            <AlertCircle className="w-2.5 h-2.5" /> {varErrors[v.key] || crossFieldErrors[v.key]}
                          </p>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Step 2: Suggested Clauses — NEW */}
      {step === 2 && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-semibold text-navy-900 dark:text-white">Suggested Clauses</h2>
              <p className="text-[10px] text-gray-500 mt-0.5">
                Based on your variable values, the system recommends the following clauses
              </p>
            </div>
          </div>

          {suggestionsLoading && (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="w-6 h-6 animate-spin text-navy-500" />
              <span className="ml-2 text-sm text-gray-500">Evaluating clause recommendations...</span>
            </div>
          )}

          {suggestionsError && (
            <div className="flex items-center gap-2 p-3 rounded-lg bg-red-50 border border-red-200 text-red-700 text-xs">
              <AlertCircle className="w-4 h-4" /> {suggestionsError}
            </div>
          )}

          {!suggestionsLoading && !suggestionsError && suggestedClauses.length === 0 && (
            <div className="text-center py-12">
              <Sparkles className="w-10 h-10 text-gray-300 mx-auto mb-3" />
              <p className="text-sm text-gray-500">No additional clauses suggested for your current inputs.</p>
              <p className="text-[10px] text-gray-400 mt-1">You can proceed to the next step to manually select clauses.</p>
            </div>
          )}

          {!suggestionsLoading && suggestedClauses.length > 0 && (
            <div className="space-y-3">
              {/* Summary bar */}
              <div className="flex items-center gap-2 text-[10px] text-gray-500 bg-gray-50 rounded-lg px-3 py-2">
                <Sparkles className="w-3.5 h-3.5 text-purple-500" />
                <span>
                  {suggestedClauses.filter((c) => c.recommendation_type === "required").length} required · 
                  {suggestedClauses.filter((c) => c.recommendation_type === "recommended").length} recommended · 
                  {suggestedClauses.filter((c) => c.recommendation_type === "optional").length} optional
                </span>
              </div>

              {suggestedClauses.map((sc) => {
                const isChecked = suggestedClauseSelections[sc.clause_id] ?? sc.is_checked;
                const isRequired = sc.recommendation_type === "required";
                return (
                  <div key={sc.clause_id}
                    className={`rounded-lg border p-4 transition-all ${
                      isChecked
                        ? "border-gray-200 bg-white dark:border-navy-700 dark:bg-navy-800"
                        : "border-red-200 bg-red-50/50 dark:border-red-900/30"
                    }`}>
                    <div className="flex items-start gap-3">
                      {isRequired ? (
                        <div className="pt-0.5">
                          <input type="checkbox" checked={true} disabled
                            className="w-4 h-4 rounded border-gray-300 bg-gray-100 opacity-60 cursor-not-allowed" />
                        </div>
                      ) : (
                        <div className="pt-0.5">
                          <input type="checkbox" checked={isChecked}
                            onChange={() => setSuggestedClauseSelections((prev) => ({
                              ...prev,
                              [sc.clause_id]: !isChecked,
                            }))}
                            className="w-4 h-4 rounded border-gray-300 text-navy-600 focus:ring-navy-500" />
                        </div>
                      )}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className={`text-sm font-medium ${isChecked ? "text-navy-900 dark:text-white" : "text-gray-500 line-through"}`}>
                            {sc.clause_title}
                          </span>
                          <span className={`text-[8px] px-1.5 py-0.5 rounded-full ${riskColor(sc.risk_level)}`}>
                            {sc.risk_level || "unspecified"}
                          </span>
                          {isRequired && (
                            <span className="text-[8px] px-1.5 py-0.5 rounded-full bg-red-100 text-red-600 flex items-center gap-0.5">
                              <AlertCircle className="w-2.5 h-2.5" /> Required
                            </span>
                          )}
                          {sc.recommendation_type === "recommended" && (
                            <span className="text-[8px] px-1.5 py-0.5 rounded-full bg-blue-100 text-blue-600">Recommended</span>
                          )}
                          {sc.recommendation_type === "optional" && (
                            <span className="text-[8px] px-1.5 py-0.5 rounded-full bg-gray-100 text-gray-500">Optional</span>
                          )}
                        </div>
                        {/* Reason badge */}
                        <div className="mt-1.5 flex items-center gap-1">
                          <span className="text-[8px] px-1.5 py-0.5 rounded-full bg-purple-100 text-purple-700">
                            {sc.reason}
                          </span>
                        </div>
                        {/* Content preview */}
                        <div className="mt-2 p-2 rounded bg-gray-50 dark:bg-navy-900 text-[10px] text-gray-600 dark:text-gray-400 whitespace-pre-wrap max-h-20 overflow-y-auto">
                          {sc.clause_content || "No content"}
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* Step 3: Clause Selection */}
      {step === 3 && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-semibold text-navy-900 dark:text-white">Select Clauses</h2>
              <p className="text-[10px] text-gray-500 mt-0.5">
                {clauseSelections.filter((cs) => cs.included).length} of {clauseSelections.length} selected
                {riskScore.criticalExcluded > 0 && (
                  <span className="text-red-600 font-medium ml-2">
                    · {riskScore.criticalExcluded} critical excluded (legal sign-off required)
                  </span>
                )}
              </p>
              {/* Risk badges */}
              <div className="flex items-center gap-2 mt-1">
                {clauseSelections.filter((cs) => cs.included && cs.risk_level === "critical").length > 0 && (
                  <span className="text-[8px] px-1.5 py-0.5 rounded-full bg-red-100 text-red-700 font-medium">
                    ⚠ {clauseSelections.filter((cs) => cs.included && cs.risk_level === "critical").length} critical-risk clause(s)
                  </span>
                )}
                {riskScore.criticalExcluded > 0 && (
                  <span className="text-[8px] px-1.5 py-0.5 rounded-full bg-orange-100 text-orange-700 font-medium flex items-center gap-0.5">
                    <AlertTriangle className="w-2.5 h-2.5" /> {riskScore.criticalExcluded} critical excluded
                  </span>
                )}
                {riskScore.highExcluded > 0 && (
                  <span className="text-[8px] px-1.5 py-0.5 rounded-full bg-amber-100 text-amber-700 font-medium">
                    {riskScore.highExcluded} high-risk excluded
                  </span>
                )}
              </div>
            </div>
            <div className="flex items-center gap-2">
              {clauseSelections.length > 0 && (
                <button onClick={resetToRecommended} className="text-[9px] text-blue-600 hover:text-blue-700 flex items-center gap-0.5">
                  <RefreshCw className="w-3 h-3" /> Reset to recommended
                </button>
              )}
            </div>
          </div>

          {clauseError && (
            <div className="flex items-center gap-2 p-3 rounded-lg bg-red-50 border border-red-200 text-red-700 text-xs">
              <AlertCircle className="w-4 h-4" /> {clauseError}
            </div>
          )}

          {clauseSelections.length === 0 ? (
            <div className="text-center py-8">
              <Shield className="w-10 h-10 text-gray-300 mx-auto mb-3" />
              <p className="text-sm text-gray-400 italic">No clauses defined for this template.</p>
              <p className="text-[10px] text-gray-400 mt-1">The contract will be generated without managed clauses.</p>
            </div>
          ) : (
            <div className="space-y-4">
              {groupedClauses.typeOrder.map((type) => {
                const clauses = groupedClauses.groups[type];
                const included = clauses.filter((c) => c.included).length;
                const isCollapsed = collapsedTypes.has(type);
                return (
                  <div key={type} className="rounded-lg border border-gray-200 dark:border-navy-700 overflow-hidden">
                    <button
                      onClick={() => toggleTypeCollapse(type)}
                      className="w-full flex items-center justify-between px-4 py-2 bg-gray-50 dark:bg-navy-900 hover:bg-gray-100 dark:hover:bg-navy-800 transition-colors"
                    >
                      <div className="flex items-center gap-2">
                        <span className="text-[10px] font-semibold text-gray-700 dark:text-gray-300 uppercase">
                          {type.replace(/_/g, " ")}
                        </span>
                        <span className="text-[8px] text-gray-400">({clauses.length})</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className={`text-[8px] px-1.5 py-0.5 rounded-full ${
                          included === clauses.length ? "bg-green-100 text-green-700" : "bg-amber-100 text-amber-700"
                        }`}>
                          {included}/{clauses.length}
                        </span>
                        {isCollapsed ? <ChevronDown className="w-3.5 h-3.5 text-gray-400" /> : <ChevronUp className="w-3.5 h-3.5 text-gray-400" />}
                      </div>
                    </button>
                    {!isCollapsed && (
                      <div className="p-3 space-y-3">
                        {clauses.map((cs) => (
                          <div key={cs.clause_id}
                            className={`rounded-lg border p-3 bg-white dark:bg-navy-800 transition-all ${
                              cs.included ? "border-gray-200 dark:border-navy-700" : "border-red-200 dark:border-red-900/30 bg-red-50/50 dark:bg-red-900/10"
                            }`}>
                            <div className="flex items-start justify-between">
                              <div className="flex items-start gap-3 flex-1 min-w-0">
                                <div className="pt-0.5">
                                  {cs.is_required ? (
                                    /* Required clause: locked checkbox with lock icon */
                                    <div className="relative group">
                                      <input type="checkbox" checked={true} disabled
                                        className="w-4 h-4 mt-0.5 rounded border-gray-300 bg-gray-100 text-navy-600 opacity-60 cursor-not-allowed" />
                                      <span className="absolute -top-1 -right-1 w-2.5 h-2.5 bg-gray-400 rounded-full flex items-center justify-center"
                                        title="Required clause — use 'Request exception' to exclude">
                                      </span>
                                    </div>
                                  ) : (
                                    <input type="checkbox" checked={cs.included}
                                      onChange={() => toggleClause(cs.clause_id)}
                                      className="w-4 h-4 mt-0.5 rounded border-gray-300 text-navy-600 focus:ring-navy-500" />
                                  )}
                                </div>
                                <div className="flex-1 min-w-0">
                                  <div className="flex items-center gap-2 flex-wrap">
                                    <span className={`text-sm font-medium ${cs.included ? "text-navy-900 dark:text-white" : "text-gray-500 line-through"}`}>
                                      {cs.clause_title}
                                    </span>
                                    <span className={`text-[8px] px-1.5 py-0.5 rounded-full ${riskColor(cs.risk_level)}`}>
                                      {cs.risk_level || "unspecified"}
                                    </span>
                                    {cs.is_required && (
                                      <span className="text-[8px] px-1.5 py-0.5 rounded-full bg-red-100 text-red-600 flex items-center gap-0.5">
                                        <AlertCircle className="w-2.5 h-2.5" /> Required
                                      </span>
                                    )}
                                    {!cs.is_required && cs.risk_level === "critical" && (
                                      <span className="text-[8px] px-1.5 py-0.5 rounded-full bg-orange-100 text-orange-600">
                                        Mandatory justification required if excluded
                                      </span>
                                    )}
                                  </div>
                                  <button onClick={() => toggleExpanded(cs.clause_id)}
                                    className="flex items-center gap-1 text-[9px] text-gray-500 hover:text-gray-700 mt-1">
                                    {expandedClauses.has(cs.clause_id) ? <><ChevronUp className="w-3 h-3" /> Hide</> : <><ChevronDown className="w-3 h-3" /> Show content</>}
                                  </button>
                                  {expandedClauses.has(cs.clause_id) && (
                                    <div className="mt-2 p-2 rounded bg-gray-50 dark:bg-navy-900 text-[10px] text-gray-600 dark:text-gray-400 whitespace-pre-wrap max-h-32 overflow-y-auto">
                                      {cs.content || "No content"}
                                    </div>
                                  )}
                                </div>
                              </div>
                              {/* Required clause: show "Request exception" button instead of checkbox toggle */}
                              {cs.is_required && cs.included && (
                                <button onClick={() => requestException(cs.clause_id, cs.clause_title)}
                                  className="text-[8px] px-2 py-1 rounded border border-amber-200 text-amber-700 hover:bg-amber-50 flex items-center gap-0.5 flex-shrink-0">
                                  <AlertTriangle className="w-2.5 h-2.5" /> Request exception
                                </button>
                              )}
                            </div>

                            {/* Exclusion reason for required clauses (after exception granted) */}
                            {cs.is_required && !cs.included && (
                              <div className="mt-3 ml-7">
                                <label className="text-[9px] font-medium text-red-600 flex items-center gap-1">
                                  <AlertCircle className="w-3 h-3" /> Reason for removing *
                                </label>
                                <textarea value={cs.reason_removed} onChange={(e) => updateClauseReason(cs.clause_id, e.target.value)}
                                  rows={2} placeholder="Explain why this clause is being removed (required for compliance audit)"
                                  className="w-full mt-1 px-2 py-1.5 text-[10px] border border-red-300 rounded-lg focus:border-red-500 focus:ring-1 focus:ring-red-500 bg-white dark:bg-navy-900" />
                              </div>
                            )}

                            {/* Mandatory notes for critical clauses that are excluded */}
                            {!cs.is_required && cs.risk_level === "critical" && !cs.included && (
                              <div className="mt-3 ml-7">
                                <label className="text-[9px] font-medium text-orange-600 flex items-center gap-1">
                                  <AlertCircle className="w-3 h-3" /> Justification (min 20 characters) *
                                </label>
                                <textarea value={cs.notes} onChange={(e) => updateClauseNote(cs.clause_id, e.target.value)}
                                  rows={2} placeholder="Explain why this critical clause is being excluded..."
                                  className={`w-full mt-1 px-2 py-1.5 text-[10px] border rounded-lg focus:ring-1 bg-white dark:bg-navy-900 ${
                                    cs.notes && cs.notes.trim().length < 20
                                      ? "border-orange-300 focus:border-orange-500 focus:ring-orange-500"
                                      : cs.notes && cs.notes.trim().length >= 20
                                      ? "border-green-300 focus:border-green-500 focus:ring-green-500"
                                      : "border-gray-200 focus:border-navy-400 focus:ring-navy-400"
                                  }`} />
                                {cs.notes && cs.notes.trim().length < 20 && (
                                  <p className="text-[8px] text-orange-500 mt-0.5">
                                    {20 - cs.notes.trim().length} more characters required
                                  </p>
                                )}
                                {cs.notes && cs.notes.trim().length >= 20 && (
                                  <p className="text-[8px] text-green-500 mt-0.5 flex items-center gap-0.5">
                                    <Check className="w-2 h-2" /> Justification complete
                                  </p>
                                )}
                              </div>
                            )}

                            {/* Optional notes for all other clauses */}
                            {(!cs.is_required || cs.included) && (cs.risk_level !== "critical" || cs.included) && (
                              <div className="mt-2 ml-7">
                                <label className="text-[9px] font-medium text-gray-500 flex items-center gap-1">
                                  <MessageSquare className="w-3 h-3" /> Notes (optional)
                                </label>
                                <textarea value={cs.notes} onChange={(e) => updateClauseNote(cs.clause_id, e.target.value)}
                                  rows={1} placeholder="Add notes about this clause selection..."
                                  className="w-full mt-1 px-2 py-1.5 text-[10px] border border-gray-200 rounded-lg focus:border-navy-400 focus:ring-1 focus:ring-navy-400 bg-white dark:bg-navy-900" />
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* Step 3: Preview */}
      {step === 4 && templateDetail && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-navy-900 dark:text-white">Preview Generated Contract</h2>
            <div className="flex items-center gap-2">
              <button onClick={() => setPreviewMode("raw")}
                className={`text-[9px] px-2 py-1 rounded ${previewMode === "raw" ? "bg-navy-100 text-navy-700" : "text-gray-400 hover:text-gray-600"}`}>
                Raw
              </button>
              <button onClick={() => setPreviewMode("rendered")}
                className={`text-[9px] px-2 py-1 rounded ${previewMode === "rendered" ? "bg-navy-100 text-navy-700" : "text-gray-400 hover:text-gray-600"}`}>
                <Eye className="w-3 h-3 inline mr-0.5" /> Rendered
              </button>
            </div>
          </div>
          <p className="text-xs text-gray-500">{title || `${templateDetail.name} - ${new Date().toLocaleDateString()}`}</p>

          {/* Risk Summary Panel */}
          <div className={`rounded-lg border p-4 ${
            riskScore.level === "Low" ? "border-green-200 bg-green-50" :
            riskScore.level === "Medium" ? "border-yellow-200 bg-yellow-50" :
            "border-red-200 bg-red-50"
          }`}>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <Shield className={`w-8 h-8 ${
                  riskScore.level === "Low" ? "text-green-600" :
                  riskScore.level === "Medium" ? "text-yellow-600" :
                  "text-red-600"
                }`} />
                <div>
                  <p className="text-sm font-bold text-navy-900">Risk Score: {riskScore.score}/100 — {riskScore.level}</p>
                  <p className="text-[10px] text-gray-500 mt-0.5">
                    {riskScore.totalCritical > 0 && `${riskScore.criticalIncluded}/${riskScore.totalCritical} critical clauses included`}
                    {riskScore.totalCritical > 0 && riskScore.totalHigh > 0 && " · "}
                    {riskScore.totalHigh > 0 && `${riskScore.highIncluded}/${riskScore.totalHigh} high-risk clauses included`}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-1">
                {riskScore.criticalExcluded > 0 && (
                  <span className="text-[8px] px-1.5 py-0.5 rounded-full bg-red-100 text-red-700">
                    {riskScore.criticalExcluded} critical excluded
                  </span>
                )}
                {riskScore.highExcluded > 0 && (
                  <span className="text-[8px] px-1.5 py-0.5 rounded-full bg-amber-100 text-amber-700">
                    {riskScore.highExcluded} high excluded
                  </span>
                )}
              </div>
            </div>
            {/* Risk bar */}
            <div className="mt-2 h-1.5 bg-gray-200 rounded-full overflow-hidden">
              <div className={`h-full rounded-full transition-all ${
                riskScore.score >= 80 ? "bg-green-500" :
                riskScore.score >= 50 ? "bg-yellow-500" :
                "bg-red-500"
              }`} style={{ width: `${riskScore.score}%` }} />
            </div>
          </div>

          <div className="rounded-lg border border-gray-200 dark:border-navy-700 bg-white dark:bg-navy-800 overflow-hidden">
            <div className="px-4 py-2 bg-gray-50 dark:bg-navy-900 border-b border-gray-200 dark:border-navy-700 flex items-center justify-between">
              <span className="text-[10px] font-semibold text-gray-500 uppercase">Document Preview</span>
              <div className="flex items-center gap-2">
                {serverPreviewMut.isPending && (
                  <span className="text-[9px] text-gray-400 flex items-center gap-1">
                    <Loader2 className="w-3 h-3 animate-spin" /> Server preview…
                  </span>
                )}
                <span className="text-[9px] text-gray-400">{unfilledVars.length} unfilled</span>
              </div>
            </div>
            {previewMode === "raw" ? (
              <pre className="p-4 text-[11px] font-mono text-gray-700 dark:text-gray-300 whitespace-pre-wrap max-h-96 overflow-y-auto">
                {previewContent}
              </pre>
            ) : (
              <div className="p-4 text-[11px] text-gray-700 dark:text-gray-300 max-h-96 overflow-y-auto leading-relaxed"
                dangerouslySetInnerHTML={{ __html: renderedPreview }} />
            )}
          </div>
          {/* Unfilled variables inline list */}
          {unfilledVars.length > 0 && (
            <div className="rounded-lg border border-amber-200 bg-amber-50 p-3">
              <p className="text-[10px] font-medium text-amber-700 mb-1">
                {unfilledVars.length} unfilled variable(s) (shown in red in preview):
              </p>
              <div className="flex flex-wrap gap-1">
                {unfilledVars.map((v) => (
                  <button key={v.key} onClick={() => { setStep(1); }}
                    className="text-[9px] px-1.5 py-0.5 rounded bg-amber-100 text-amber-700 hover:bg-amber-200 font-mono">
                    {'{{'}{v.key}{'}}'}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Clause Summary with full text */}
          {clauseSelections.filter((cs) => cs.included).length > 0 && (
            <div className="rounded-lg border border-gray-200 dark:border-navy-700 bg-white dark:bg-navy-800 overflow-hidden">
              <div className="px-4 py-2 bg-gray-50 dark:bg-navy-900 border-b border-gray-200 dark:border-navy-700">
                <h3 className="text-[10px] font-semibold text-gray-500 uppercase">Included Clauses</h3>
              </div>
              <div className="p-3 space-y-3">
                {clauseSelections.filter((cs) => cs.included).map((cs) => (
                  <div key={cs.clause_id} className="text-[10px]">
                    <div className="flex items-center gap-1.5 mb-1">
                      <Check className="w-3 h-3 text-green-500 flex-shrink-0" />
                      <span className="font-semibold text-navy-900 dark:text-white">{cs.clause_title}</span>
                      <span className={`text-[7px] px-1 py-0.5 rounded-full ${riskColor(cs.risk_level)}`}>
                        {cs.risk_level || "unspecified"}
                      </span>
                    </div>
                    <div className="ml-5 p-2 rounded bg-gray-50 dark:bg-navy-900 text-[9px] text-gray-600 dark:text-gray-400 leading-relaxed whitespace-pre-wrap">
                      {cs.content || "No content"}
                    </div>
                    {cs.notes && (
                      <div className="ml-5 mt-1 text-[8px] text-gray-400 italic">
                        Note: {cs.notes}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Excluded clauses summary */}
          {clauseSelections.filter((cs) => !cs.included).length > 0 && (
            <div className="rounded-lg border border-red-200 dark:border-red-900/30 bg-red-50/50 dark:bg-red-900/10 p-3">
              <h3 className="text-[10px] font-semibold text-red-600 uppercase mb-1">Excluded Clauses ({clauseSelections.filter((cs) => !cs.included).length})</h3>
              <div className="space-y-1">
                {clauseSelections.filter((cs) => !cs.included).map((cs) => (
                  <div key={cs.clause_id} className="flex items-start gap-1.5 text-[9px] text-red-500">
                    <XCircle className="w-3 h-3 mt-0.5 flex-shrink-0" />
                    <div>
                      <span className="line-through">{cs.clause_title}</span>
                      {cs.reason_removed && <span className="text-red-400 italic"> — {cs.reason_removed}</span>}
                      {cs.notes && <span className="text-gray-400 italic"> (justification: {cs.notes})</span>}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
      {/* Step 4: Generate */}
      {step === 5 && (
        <div className="space-y-4">
          {/* Re-validate on entry: show blocking errors if any */}
          {!stepValidity[1]?.valid && (
            <div className="rounded-lg border border-red-200 bg-red-50 p-4">
              <div className="flex items-center gap-2 text-red-700 text-sm font-medium mb-2">
                <AlertTriangle className="w-4 h-4" /> Cannot generate — validation errors exist
              </div>
              <ul className="text-[10px] text-red-600 space-y-1 ml-5 list-disc">
                {stepValidity[1]?.errors.map((e, i) => <li key={i}>{e} <button onClick={() => setStep(1)} className="underline hover:text-red-800">Fix in Step 2</button></li>)}
                {stepValidity[3]?.errors.map((e, i) => <li key={`c${i}`}>{e} <button onClick={() => setStep(3)} className="underline hover:text-red-800">Fix in Step 4</button></li>)}
              </ul>
            </div>
          )}

          <div className="text-center space-y-4 py-4">
            <Sparkles className="w-12 h-12 text-navy-400 mx-auto" />
            <h2 className="text-lg font-semibold text-navy-900 dark:text-white">Ready to Generate</h2>
            <p className="text-sm text-gray-500 max-w-md mx-auto">
              This will create a new contract from "{templateDetail?.name}" and route it through the contract lifecycle.
            </p>
          </div>

          {/* Risk Score Summary */}
          <div className={`rounded-lg border p-4 max-w-md mx-auto ${
            riskScore.level === "Low" ? "border-green-200 bg-green-50" :
            riskScore.level === "Medium" ? "border-yellow-200 bg-yellow-50" :
            "border-red-200 bg-red-50"
          }`}>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Shield className={`w-5 h-5 ${
                  riskScore.level === "Low" ? "text-green-600" :
                  riskScore.level === "Medium" ? "text-yellow-600" :
                  "text-red-600"
                }`} />
                <span className="text-xs font-bold text-navy-900">Risk Score: {riskScore.score}/100 — {riskScore.level}</span>
              </div>
            </div>
            <div className="mt-1.5 h-1 bg-gray-200 rounded-full overflow-hidden">
              <div className={`h-full rounded-full ${
                riskScore.score >= 80 ? "bg-green-500" :
                riskScore.score >= 50 ? "bg-yellow-500" :
                "bg-red-500"
              }`} style={{ width: `${riskScore.score}%` }} />
            </div>
            {riskScore.criticalExcluded > 0 && (
              <p className="text-[9px] text-red-600 mt-1 font-medium">
                ⚠ {riskScore.criticalExcluded} critical clause(s) excluded — requires legal sign-off
              </p>
            )}
          </div>

          {/* Summary card */}
          <div className="rounded-lg border border-gray-200 dark:border-navy-700 p-4 bg-white dark:bg-navy-800 max-w-md mx-auto text-left text-xs space-y-2">
            <div className="flex justify-between"><span className="text-gray-500">Template</span><span className="font-medium">{templateDetail?.name}</span></div>
            <div className="flex justify-between"><span className="text-gray-500">Version</span><span className="font-medium">v{templateDetail?.current_version?.version_number}</span></div>
            <div className="flex justify-between"><span className="text-gray-500">Variables</span><span className="font-medium">{variables.length} ({requiredCount} required)</span></div>
            <div className="flex justify-between"><span className="text-gray-500">Clauses</span><span className="font-medium">{clauseSelections.filter((cs) => cs.included).length} included, {clauseSelections.filter((cs) => !cs.included).length} excluded</span></div>
            <div className="flex justify-between"><span className="text-gray-500">Title</span><span className="font-medium">{title || `${templateDetail?.name} - ${new Date().toLocaleDateString()}`}</span></div>
            <div className="flex justify-between"><span className="text-gray-500">Next step</span><span className="font-medium text-purple-600">Ingestion → AI Review → Review Queue</span></div>
          </div>

          {/* Included clauses list */}
          {clauseSelections.filter((cs) => cs.included).length > 0 && (
            <div className="max-w-md mx-auto text-left text-[9px] text-gray-500 space-y-0.5">
              <p className="font-medium text-gray-600 mb-1">Included clauses ({clauseSelections.filter((cs) => cs.included).length}):</p>
              {clauseSelections.filter((cs) => cs.included).map((cs) => (
                <div key={cs.clause_id} className="flex items-center gap-1">
                  <Check className="w-2.5 h-2.5 text-green-500" />
                  <span>{cs.clause_title}</span>
                  <span className={`text-[7px] px-1 py-0.5 rounded-full ${riskColor(cs.risk_level)}`}>{cs.risk_level}</span>
                </div>
              ))}
            </div>
          )}

          {/* Excluded clauses list */}
          {clauseSelections.filter((cs) => !cs.included).length > 0 && (
            <div className="max-w-md mx-auto text-left text-[9px] text-red-500 space-y-0.5">
              <p className="font-medium text-red-600 mb-1">Excluded clauses ({clauseSelections.filter((cs) => !cs.included).length}):</p>
              {clauseSelections.filter((cs) => !cs.included).map((cs) => (
                <div key={cs.clause_id} className="flex items-start gap-1">
                  <XCircle className="w-2.5 h-2.5 mt-0.5 flex-shrink-0" />
                  <div>
                    <span className="line-through">{cs.clause_title}</span>
                    {cs.reason_removed && <span className="text-red-400"> — {cs.reason_removed}</span>}
                  </div>
                </div>
              ))}
            </div>
          )}

          <label className="flex items-center justify-center gap-2 text-xs text-gray-600 cursor-pointer max-w-md mx-auto">
            <input type="checkbox" checked={confirmFinal} onChange={(e) => setConfirmFinal(e.target.checked)}
              className="w-4 h-4 rounded border-gray-300" />
            I confirm these terms are accurate and authorize routing this contract to <strong>Ingestion → AI Review → Review Queue</strong>
          </label>
        </div>
      )}

      {/* Exception modal for Required clauses */}
      {exceptionModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40" onClick={() => setExceptionModal(null)}>
          <div className="bg-white rounded-xl shadow-2xl max-w-md w-full mx-4 p-6" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center gap-2 text-amber-700 mb-3">
              <AlertTriangle className="w-5 h-5" />
              <h3 className="text-sm font-bold">Request Exception — Required Clause</h3>
            </div>
            <p className="text-xs text-gray-600 mb-3">
              You are requesting to exclude <strong>{exceptionModal.title}</strong>, which is marked as Required.
              This will flag the contract for mandatory secondary legal review.
            </p>
            <label className="text-[10px] font-medium text-gray-600 mb-1 block">Reason for exception *</label>
            <textarea value={exceptionReason} onChange={(e) => setExceptionReason(e.target.value)}
              rows={3} placeholder="Explain why this required clause should be excluded..."
              className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:border-amber-400 focus:ring-1 focus:ring-amber-400" />
            {exceptionReason.trim().length > 0 && exceptionReason.trim().length < 10 && (
              <p className="text-[9px] text-amber-500 mt-1">Please provide a detailed reason (min 10 characters)</p>
            )}
            <div className="flex items-center justify-end gap-2 mt-4">
              <button onClick={() => setExceptionModal(null)}
                className="px-3 py-1.5 text-xs font-medium rounded-lg border border-gray-200 text-gray-700 hover:bg-gray-50">
                Cancel
              </button>
              <button onClick={confirmException} disabled={exceptionReason.trim().length < 10}
                className="px-3 py-1.5 text-xs font-medium rounded-lg bg-amber-600 text-white hover:bg-amber-700 disabled:opacity-50">
                Confirm Exception
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Navigation */}
      <div className="flex items-center justify-between pt-4 border-t border-gray-200 dark:border-navy-700">
        <button onClick={() => setStep(Math.max(0, step - 1))} disabled={step === 0}
          className="inline-flex items-center gap-1 px-3 py-2 text-sm font-medium rounded-lg border border-gray-200 text-gray-700 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed">
          <ArrowLeft className="w-4 h-4" /> Back
        </button>

        <div className="flex items-center gap-2">
          {step === 1 ? (
            <button onClick={handleNextFromVariables}
              disabled={!stepValidity[1]?.valid}
              className="inline-flex items-center gap-1 px-4 py-2 text-sm font-medium rounded-lg bg-navy-700 text-white hover:bg-navy-800 disabled:opacity-50 disabled:cursor-not-allowed">
              Next <ArrowRight className="w-4 h-4" />
            </button>
          ) : step === 2 ? (
            <button onClick={() => {
              // Merge accepted suggested clauses into clause selections
              if (suggestedClauses.length > 0) {
                const acceptedIds = Object.entries(suggestedClauseSelections)
                  .filter(([, checked]) => checked)
                  .map(([id]) => id);
                const accepted = suggestedClauses.filter((sc) => acceptedIds.includes(sc.clause_id));
                if (accepted.length > 0) {
                  setClauseSelections((prev) => {
                    const existingIds = new Set(prev.map((c) => c.clause_id));
                    const newClauses = accepted
                      .filter((sc) => !existingIds.has(sc.clause_id))
                      .map((sc) => ({
                        clause_id: sc.clause_id,
                        clause_title: sc.clause_title,
                        clause_type: sc.clause_type,
                        risk_level: sc.risk_level,
                        content: sc.clause_content,
                        is_required: sc.recommendation_type === "required",
                        included: true,
                        reason_removed: "",
                        notes: `Suggested: ${sc.reason}`,
                        fallback_clause_id: null,
                      }));
                    return [...prev, ...newClauses];
                  });
                }
              }
              setStep(step + 1);
            }}
              className="inline-flex items-center gap-1 px-4 py-2 text-sm font-medium rounded-lg bg-navy-700 text-white hover:bg-navy-800">
              Next <ArrowRight className="w-4 h-4" />
            </button>
          ) : step === 3 ? (
            <button onClick={() => setStep(step + 1)}
              disabled={!stepValidity[1]?.valid || !stepValidity[3]?.valid}
              className="inline-flex items-center gap-1 px-4 py-2 text-sm font-medium rounded-lg bg-navy-700 text-white hover:bg-navy-800 disabled:opacity-50 disabled:cursor-not-allowed">
              Next <ArrowRight className="w-4 h-4" />
            </button>
          ) : step === 4 ? (
            <button onClick={() => setStep(step + 1)}
              className="inline-flex items-center gap-1 px-4 py-2 text-sm font-medium rounded-lg bg-navy-700 text-white hover:bg-navy-800">
              Next <ArrowRight className="w-4 h-4" />
            </button>
          ) : step === 5 ? (
            <button onClick={() => generateMut.mutate()} disabled={generateMut.isPending || !confirmFinal}
              className="inline-flex items-center gap-1.5 px-4 py-2 text-sm font-medium rounded-lg bg-green-600 text-white hover:bg-green-700 disabled:opacity-50">
              {generateMut.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
              {generateMut.isPending ? "Generating..." : "Generate Contract"}
            </button>
          ) : null}
        </div>
      </div>
    </div>
  );
}

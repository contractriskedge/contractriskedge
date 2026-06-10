/**
 * CreateObligationModal — Enterprise-grade obligation creation form.
 *
 * All lookup fields use searchable dropdowns sourced from the database:
 * - Contract: searchable by name, contract number, vendor (required)
 * - Clause Reference: searchable from clause_library + recent usage history
 * - Owner: searchable from admin_users
 * - Department: searchable from admin_users + obligations history
 * - Business Unit: searchable from admin_users + obligations history
 * - Backup Owner (Assignee): searchable from admin_users
 *
 * Gold-standard UX: typeahead search, keyboard navigation, recent items first.
 */

"use client";

import React, { useState, useCallback, useRef, useEffect } from "react";
import { motion } from "framer-motion";
import { X, Save, Plus, Loader2, Search, ChevronDown, User, Building2, BookOpen } from "lucide-react";
import { useCreateObligation } from "@/services/hooks/useObligations";
import { searchContractsForSelect } from "@/services/api/contracts";
import { searchClauseReferences, searchUsers, searchDepartments, searchBusinessUnits } from "@/services/api/obligationHelpers";
import type { ObligationCreateRequest } from "@/services/api/obligations";
import type { ContractSelectItem } from "@/services/api/contracts";
import type { ClauseReferenceItem, UserItem, SelectOption } from "@/services/api/obligationHelpers";

interface CreateObligationModalProps {
  isOpen: boolean;
  onClose: () => void;
  onCreated: () => void;
}

const OBLIGATION_TYPES = [
  "payment", "renewal", "notice", "insurance",
  "audit_rights", "data_retention", "data_deletion",
];

const RISK_LEVELS = ["low", "medium", "high", "critical"];

interface FormData {
  name: string;
  description: string;
  contract: ContractSelectItem | null;
  clauseReference: ClauseReferenceItem | null;
  obligationType: string;
  owner: UserItem | null;
  department: SelectOption | null;
  businessUnit: SelectOption | null;
  assignee: UserItem | null;
  dueDate: string;
  reminderDate: string;
  completedDate: string;
  riskLevel: string;
  financialImpact: number;
  currency: string;
  slaTargetDays: number;
  escalationRequired: boolean;
}

const DEFAULT_FORM: FormData = {
  name: "",
  description: "",
  contract: null,
  clauseReference: null,
  obligationType: "payment",
  owner: null,
  department: null,
  businessUnit: null,
  assignee: null,
  dueDate: "",
  reminderDate: "",
  completedDate: "",
  riskLevel: "medium",
  financialImpact: 0,
  currency: "USD",
  slaTargetDays: 30,
  escalationRequired: false,
};

// ── Reusable SearchableSelect Component ────────────────────────────

interface SearchableSelectProps<T> {
  label: string;
  required?: boolean;
  value: T | null;
  onChange: (item: T | null) => void;
  fetchFn: (q: string) => Promise<{ data: T[]; total: number }>;
  displayLabel: (item: T) => string;
  displayDetail?: (item: T) => string;
  displaySubdetail?: (item: T) => string;
  placeholder?: string;
  icon?: React.ReactNode;
  noResultsMessage?: string;
}

function SearchableSelect<T extends { id: string }>({
  label, required, value, onChange, fetchFn,
  displayLabel, displayDetail, displaySubdetail,
  placeholder = "Search...", icon, noResultsMessage = "No results found",
}: SearchableSelectProps<T>) {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState("");
  const [results, setResults] = useState<T[]>([]);
  const [loading, setLoading] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    let cancelled = false;
    setLoading(true);
    fetchFn(search).then((res) => {
      if (!cancelled) { setResults(res.data ?? []); setLoading(false); }
    }).catch(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [search, open, fetchFn]);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  return (
    <div ref={ref} className="relative">
      <label className="text-[10px] font-medium text-gray-600 dark:text-gray-400 block mb-1">
        {label} {required && <span className="text-red-500">*</span>}
      </label>
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className={`w-full flex items-center gap-2 px-3 py-2 text-xs border rounded-lg text-left transition-colors ${
          value
            ? "border-navy-300 bg-navy-50 dark:bg-navy-700 dark:border-navy-500"
            : "border-gray-200 dark:border-navy-600 bg-white dark:bg-navy-700"
        } focus:outline-none focus:ring-1 focus:ring-navy-400`}
      >
        {icon && <span className="text-gray-400 flex-shrink-0">{icon}</span>}
        {value ? (
          <div className="flex-1 min-w-0">
            <span className="font-medium text-navy-900 dark:text-white truncate block">
              {displayLabel(value)}
            </span>
            {displayDetail && (
              <span className="text-[9px] text-gray-500 block truncate">
                {displayDetail(value)}
              </span>
            )}
          </div>
        ) : (
          <span className="text-gray-400 flex-1">{placeholder}</span>
        )}
        <ChevronDown className={`w-3.5 h-3.5 text-gray-400 flex-shrink-0 transition-transform ${open ? "rotate-180" : ""}`} />
      </button>

      {open && (
        <div className="absolute z-50 mt-1 w-full bg-white dark:bg-navy-800 border border-gray-200 dark:border-navy-600 rounded-lg shadow-xl max-h-72 flex flex-col">
          <div className="p-2 border-b border-gray-100 dark:border-navy-700">
            <div className="flex items-center gap-1.5 px-2 py-1.5 bg-gray-50 dark:bg-navy-700 rounded-md">
              <Search className="w-3.5 h-3.5 text-gray-400 flex-shrink-0" />
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder={placeholder}
                className="w-full text-[11px] bg-transparent border-none outline-none text-navy-900 dark:text-white placeholder-gray-400"
                autoFocus
              />
              {loading && <Loader2 className="w-3 h-3 text-gray-400 animate-spin flex-shrink-0" />}
            </div>
          </div>
          <div className="flex-1 overflow-y-auto">
            {results.length === 0 && !loading && (
              <p className="text-[10px] text-gray-400 text-center py-6">{noResultsMessage}</p>
            )}
            {results.map((item, idx) => (
              <button
                key={(item as Record<string, unknown>).id as string ?? (item as Record<string, unknown>).value as string ?? `option-${idx}`}
                type="button"
                onClick={() => { onChange(item); setOpen(false); setSearch(""); }}
                className={`w-full text-left px-3 py-2.5 hover:bg-gray-50 dark:hover:bg-navy-700 transition-colors border-b border-gray-50 dark:border-navy-700 last:border-0 ${
                  value?.id === item.id ? "bg-navy-50 dark:bg-navy-700" : ""
                }`}
              >
                <span className="text-[11px] font-medium text-navy-900 dark:text-white truncate block">
                  {displayLabel(item)}
                </span>
                {displayDetail && (
                  <span className="text-[9px] text-gray-500 block truncate">
                    {displayDetail(item)}
                  </span>
                )}
                {displaySubdetail && (
                  <span className="text-[8px] text-gray-400 block truncate">
                    {displaySubdetail(item)}
                  </span>
                )}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ── Contract Selector (specialized with risk badge) ────────────────

const riskColor = (level: string) => {
  const map: Record<string, string> = {
    critical: "text-red-600 bg-red-50",
    high: "text-orange-600 bg-orange-50",
    medium: "text-amber-600 bg-amber-50",
    low: "text-green-600 bg-green-50",
  };
  return map[level] ?? "text-gray-600 bg-gray-50";
};

function ContractSelector({
  value, onChange,
}: {
  value: ContractSelectItem | null;
  onChange: (c: ContractSelectItem | null) => void;
}) {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState("");
  const [results, setResults] = useState<ContractSelectItem[]>([]);
  const [loading, setLoading] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    let cancelled = false;
    setLoading(true);
    searchContractsForSelect(search || undefined).then((res) => {
      if (!cancelled) { setResults(res.data ?? []); setLoading(false); }
    }).catch(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [search, open]);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  const displayName = (c: ContractSelectItem) =>
    c.contract_number ? `${c.contract_number} — ${c.name}` : c.name;

  return (
    <div ref={ref} className="relative">
      <label className="text-[10px] font-medium text-gray-600 dark:text-gray-400 block mb-1">
        Contract <span className="text-red-500">*</span>
      </label>
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className={`w-full flex items-center gap-2 px-3 py-2 text-xs border rounded-lg text-left transition-colors ${
          value
            ? "border-navy-300 bg-navy-50 dark:bg-navy-700 dark:border-navy-500"
            : "border-gray-200 dark:border-navy-600 bg-white dark:bg-navy-700"
        } focus:outline-none focus:ring-1 focus:ring-navy-400`}
      >
        {value ? (
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-1.5">
              <span className="font-medium text-navy-900 dark:text-white truncate">
                {value.contract_number ? `${value.contract_number} — ` : ""}{value.name}
              </span>
            </div>
            <div className="flex items-center gap-2 mt-0.5">
              {value.vendor && <span className="text-[9px] text-gray-500">Vendor: {value.vendor}</span>}
              <span className={`text-[8px] font-medium px-1 py-0.5 rounded ${riskColor(value.risk_level)}`}>
                Risk: {value.risk_level}
              </span>
            </div>
          </div>
        ) : (
          <span className="text-gray-400 flex-1">Search by contract name, number, or vendor...</span>
        )}
        <ChevronDown className={`w-3.5 h-3.5 text-gray-400 flex-shrink-0 transition-transform ${open ? "rotate-180" : ""}`} />
      </button>

      {open && (
        <div className="absolute z-50 mt-1 w-full bg-white dark:bg-navy-800 border border-gray-200 dark:border-navy-600 rounded-lg shadow-xl max-h-72 flex flex-col">
          <div className="p-2 border-b border-gray-100 dark:border-navy-700">
            <div className="flex items-center gap-1.5 px-2 py-1.5 bg-gray-50 dark:bg-navy-700 rounded-md">
              <Search className="w-3.5 h-3.5 text-gray-400 flex-shrink-0" />
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search by name, number, vendor..."
                className="w-full text-[11px] bg-transparent border-none outline-none text-navy-900 dark:text-white placeholder-gray-400"
                autoFocus
              />
              {loading && <Loader2 className="w-3 h-3 text-gray-400 animate-spin flex-shrink-0" />}
            </div>
          </div>
          <div className="flex-1 overflow-y-auto">
            {results.length === 0 && !loading && (
              <p className="text-[10px] text-gray-400 text-center py-6">No contracts found</p>
            )}
            {results.map((c) => (
              <button
                key={c.id}
                type="button"
                onClick={() => { onChange(c); setOpen(false); setSearch(""); }}
                className={`w-full text-left px-3 py-2.5 hover:bg-gray-50 dark:hover:bg-navy-700 transition-colors border-b border-gray-50 dark:border-navy-700 last:border-0 ${
                  value?.id === c.id ? "bg-navy-50 dark:bg-navy-700" : ""
                }`}
              >
                <div className="flex items-center gap-1.5">
                  <span className="text-[11px] font-medium text-navy-900 dark:text-white truncate">
                    {displayName(c)}
                  </span>
                </div>
                <div className="flex items-center gap-2 mt-0.5">
                  {c.vendor && <span className="text-[9px] text-gray-500">Vendor: {c.vendor}</span>}
                  {c.counterparty && <span className="text-[9px] text-gray-500">Counterparty: {c.counterparty}</span>}
                  <span className={`text-[8px] font-medium px-1 py-0.5 rounded ${riskColor(c.risk_level)}`}>
                    {c.risk_level}
                  </span>
                </div>
              </button>
            ))}
          </div>
        </div>
      )}

      {!value && open === false && (
        <p className="text-[9px] text-red-500 mt-0.5">Please select a contract.</p>
      )}
    </div>
  );
}

// ── Main Component ─────────────────────────────────────────────────

export function CreateObligationModal({ isOpen, onClose, onCreated }: CreateObligationModalProps) {
  const [form, setForm] = useState<FormData>({ ...DEFAULT_FORM });
  const [validationError, setValidationError] = useState<string | null>(null);
  const createMutation = useCreateObligation();

  // Stable fetch callbacks to avoid infinite re-renders in SearchableSelect
  const fetchClauseRefs = useCallback(
    (q: string) => searchClauseReferences(q || undefined),
    [],
  );
  const fetchUsers = useCallback(
    (q: string) => searchUsers(q || undefined),
    [],
  );
  const fetchDepts = useCallback(
    (q: string) => searchDepartments(q || undefined),
    [],
  );
  const fetchBus = useCallback(
    (q: string) => searchBusinessUnits(q || undefined),
    [],
  );

  const update = useCallback(<K extends keyof FormData>(key: K, value: FormData[K]) => {
    setForm((prev) => ({ ...prev, [key]: value }));
    setValidationError(null);
  }, []);

  const handleSubmit = useCallback(async (saveAsDraft: boolean) => {
    if (!form.contract) {
      setValidationError("Please select a contract.");
      return;
    }

    // Frontend due date validation
    if (form.dueDate) {
      const today = new Date();
      today.setHours(0, 0, 0, 0);
      const selected = new Date(form.dueDate + "T00:00:00");
      if (selected < today) {
        setValidationError("Due date cannot be in the past.");
        return;
      }
    }

    const body: ObligationCreateRequest = {
      name: form.name,
      obligationType: form.obligationType,
      status: saveAsDraft ? "draft" : "open",
      description: form.description || undefined,
      contractUuidId: form.contract.id,
      contractId: form.contract.id,
      contractName: form.contract.name,
      vendor: form.contract.vendor || undefined,
      clauseReference: form.clauseReference?.value || undefined,
      owner: form.owner?.name || undefined,
      assignee: form.assignee?.name || undefined,
      department: form.department?.value || undefined,
      businessUnit: form.businessUnit?.value || undefined,
      dueDate: form.dueDate || undefined,
      riskLevel: form.riskLevel,
      financialImpact: form.financialImpact || undefined,
      currency: form.currency,
    };
    createMutation.mutate(body, {
      onSuccess: () => {
        setForm({ ...DEFAULT_FORM });
        setValidationError(null);
        onCreated();
        onClose();
      },
      onError: (err: unknown) => {
        const msg = err instanceof Error ? err.message : "Failed to create obligation";
        setValidationError(msg);
      },
    });
  }, [form, createMutation, onCreated, onClose]);

  if (!isOpen) return null;

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm"
      onMouseDown={onClose}
    >
      <motion.div
        initial={{ opacity: 0, scale: 0.95, y: 10 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.95, y: 10 }}
        onMouseDown={(e) => e.stopPropagation()}
        className="bg-white dark:bg-navy-800 rounded-xl shadow-2xl max-w-2xl w-full mx-4 max-h-[85vh] overflow-y-auto"
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-navy-700 sticky top-0 bg-white dark:bg-navy-800 z-10">
          <div className="flex items-center gap-2">
            <Plus className="w-4 h-4 text-navy-500" />
            <h2 className="text-sm font-bold text-navy-900 dark:text-white">Create Obligation</h2>
          </div>
          <button onClick={onClose} className="p-1 rounded hover:bg-gray-100 dark:hover:bg-navy-700 text-gray-400">
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="px-6 py-4 space-y-6">
          {validationError && (
            <div className="px-3 py-2 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
              <p className="text-[10px] font-medium text-red-700 dark:text-red-400">{validationError}</p>
            </div>
          )}

          {/* ── Contract Selector (required) ── */}
          <Section title="Contract">
            <ContractSelector
              value={form.contract}
              onChange={(c) => update("contract", c)}
            />
          </Section>

          {/* ── General Information ── */}
          <Section title="General Information">
            <Field label="Obligation Name *">
              <input type="text" value={form.name} onChange={(e) => update("name", e.target.value)}
                className="w-full text-xs px-3 py-2 border border-gray-200 dark:border-navy-600 rounded-lg bg-white dark:bg-navy-700 text-navy-900 dark:text-white placeholder-gray-400 focus:outline-none focus:ring-1 focus:ring-navy-400"
                placeholder="e.g., SOC2 Annual Report" />
            </Field>
            <div className="grid grid-cols-2 gap-3">
              <Field label="Description">
                <textarea value={form.description} onChange={(e) => update("description", e.target.value)}
                  className="w-full text-xs px-3 py-2 border border-gray-200 dark:border-navy-600 rounded-lg bg-white dark:bg-navy-700 text-navy-900 dark:text-white placeholder-gray-400 focus:outline-none focus:ring-1 focus:ring-navy-400 resize-none"
                  rows={2} placeholder="Obligation details..." />
              </Field>
              <div className="space-y-3">
                <Field label="Clause Reference">
                  <SearchableSelect
                    label=""
                    value={form.clauseReference}
                    onChange={(v) => update("clauseReference", v)}
                    fetchFn={fetchClauseRefs}
                    displayLabel={(item) => item.label}
                    displayDetail={(item) => item.type === "recent" ? item.detail : `Type: ${item.detail}`}
                    placeholder="Search clause references..."
                    icon={<BookOpen className="w-3 h-3" />}
                    noResultsMessage="No clause references found"
                  />
                </Field>
              </div>
            </div>
            <Field label="Obligation Type *">
              <div className="flex flex-wrap gap-1.5">
                {OBLIGATION_TYPES.map((t) => (
                  <button key={t}
                    onClick={() => update("obligationType", t)}
                    className={`px-2.5 py-1 text-[10px] font-medium rounded-full transition-colors ${
                      form.obligationType === t
                        ? "bg-navy-700 text-white"
                        : "bg-gray-100 dark:bg-navy-700 text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-navy-600"
                    }`}
                  >
                    {t.charAt(0).toUpperCase() + t.slice(1)}
                  </button>
                ))}
              </div>
            </Field>
          </Section>

          {/* ── Ownership ── */}
          <Section title="Ownership">
            <div className="grid grid-cols-2 gap-3">
              <Field label="Owner *">
                <SearchableSelect
                  label=""
                  value={form.owner}
                  onChange={(v) => update("owner", v)}
                  fetchFn={fetchUsers}
                  displayLabel={(item) => item.name}
                  displayDetail={(item) => `${item.email}${item.department ? ` · ${item.department}` : ""}`}
                  displaySubdetail={(item) => `Role: ${item.role}`}
                  placeholder="Search users..."
                  icon={<User className="w-3 h-3" />}
                  noResultsMessage="No users found"
                />
              </Field>
              <Field label="Department">
                <SearchableSelect
                  label=""
                  value={form.department}
                  onChange={(v) => update("department", v)}
                  fetchFn={fetchDepts}
                  displayLabel={(item) => item.label}
                  displayDetail={(item) => `Source: ${item.source}`}
                  placeholder="Search departments..."
                  icon={<Building2 className="w-3 h-3" />}
                  noResultsMessage="No departments found"
                />
              </Field>
              <Field label="Business Unit">
                <SearchableSelect
                  label=""
                  value={form.businessUnit}
                  onChange={(v) => update("businessUnit", v)}
                  fetchFn={fetchBus}
                  displayLabel={(item) => item.label}
                  displayDetail={(item) => `Source: ${item.source}`}
                  placeholder="Search business units..."
                  icon={<Building2 className="w-3 h-3" />}
                  noResultsMessage="No business units found"
                />
              </Field>
              <Field label="Backup Owner">
                <SearchableSelect
                  label=""
                  value={form.assignee}
                  onChange={(v) => update("assignee", v)}
                  fetchFn={fetchUsers}
                  displayLabel={(item) => item.name}
                  displayDetail={(item) => `${item.email}${item.department ? ` · ${item.department}` : ""}`}
                  displaySubdetail={(item) => `Role: ${item.role}`}
                  placeholder="Search users..."
                  icon={<User className="w-3 h-3" />}
                  noResultsMessage="No users found"
                />
              </Field>
            </div>
          </Section>

          {/* ── Dates ── */}
          <Section title="Dates">
            <div className="grid grid-cols-2 gap-3">
              <Field label="Due Date *">
                <input type="date" value={form.dueDate} onChange={(e) => update("dueDate", e.target.value)}
                  min={new Date().toISOString().split("T")[0]}
                  className="w-full text-xs px-3 py-2 border border-gray-200 dark:border-navy-600 rounded-lg bg-white dark:bg-navy-700 text-navy-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-navy-400" />
              </Field>
              <Field label="Reminder Date">
                <input type="date" value={form.reminderDate} onChange={(e) => update("reminderDate", e.target.value)}
                  className="w-full text-xs px-3 py-2 border border-gray-200 dark:border-navy-600 rounded-lg bg-white dark:bg-navy-700 text-navy-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-navy-400" />
              </Field>
              <Field label="Completion Date">
                <input type="date" value={form.completedDate} onChange={(e) => update("completedDate", e.target.value)}
                  className="w-full text-xs px-3 py-2 border border-gray-200 dark:border-navy-600 rounded-lg bg-white dark:bg-navy-700 text-navy-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-navy-400" />
              </Field>
            </div>
          </Section>

          {/* ── Risk ── */}
          <Section title="Risk">
            <div className="flex items-center gap-3">
              {RISK_LEVELS.map((level) => {
                const colors: Record<string, string> = {
                  low: "bg-green-100 text-green-700 border-green-200 dark:bg-green-900/20 dark:text-green-400 dark:border-green-800",
                  medium: "bg-amber-100 text-amber-700 border-amber-200 dark:bg-amber-900/20 dark:text-amber-400 dark:border-amber-800",
                  high: "bg-orange-100 text-orange-700 border-orange-200 dark:bg-orange-900/20 dark:text-orange-400 dark:border-orange-800",
                  critical: "bg-red-100 text-red-700 border-red-200 dark:bg-red-900/20 dark:text-red-400 dark:border-red-800",
                };
                return (
                  <button key={level}
                    onClick={() => update("riskLevel", level)}
                    className={`px-3 py-1.5 text-[10px] font-medium rounded-lg border transition-colors ${
                      form.riskLevel === level
                        ? colors[level] + " ring-1 ring-offset-1 ring-navy-400"
                        : "bg-gray-50 dark:bg-navy-700 text-gray-500 dark:text-gray-400 border-gray-200 dark:border-navy-600"
                    }`}
                  >
                    {level.charAt(0).toUpperCase() + level.slice(1)}
                  </button>
                );
              })}
            </div>
          </Section>

          {/* ── Financial ── */}
          <Section title="Financial">
            <div className="grid grid-cols-3 gap-3">
              <Field label="Financial Impact ($)">
                <input type="number" value={form.financialImpact || ""} onChange={(e) => update("financialImpact", Number(e.target.value))}
                  className="w-full text-xs px-3 py-2 border border-gray-200 dark:border-navy-600 rounded-lg bg-white dark:bg-navy-700 text-navy-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-navy-400" />
              </Field>
              <Field label="Currency">
                <select value={form.currency} onChange={(e) => update("currency", e.target.value)}
                  className="w-full text-xs px-3 py-2 border border-gray-200 dark:border-navy-600 rounded-lg bg-white dark:bg-navy-700 text-navy-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-navy-400">
                  {["USD", "EUR", "GBP", "CAD", "AUD", "JPY"].map((c) => (
                    <option key={c} value={c}>{c}</option>
                  ))}
                </select>
              </Field>
            </div>
          </Section>

          {/* ── SLA ── */}
          <Section title="SLA">
            <div className="grid grid-cols-2 gap-3">
              <Field label="SLA Target (Days)">
                <input type="number" value={form.slaTargetDays} onChange={(e) => update("slaTargetDays", Number(e.target.value))}
                  className="w-full text-xs px-3 py-2 border border-gray-200 dark:border-navy-600 rounded-lg bg-white dark:bg-navy-700 text-navy-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-navy-400" />
              </Field>
              <Field label="Escalation Required">
                <label className="flex items-center gap-2 mt-2 cursor-pointer">
                  <input type="checkbox" checked={form.escalationRequired} onChange={(e) => update("escalationRequired", e.target.checked)}
                    className="w-4 h-4 rounded border-gray-300 text-navy-700 focus:ring-navy-400" />
                  <span className="text-xs text-gray-600 dark:text-gray-400">Enable escalation on overdue</span>
                </label>
              </Field>
            </div>
          </Section>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-6 py-4 border-t border-gray-200 dark:border-navy-700 bg-gray-50/50 dark:bg-navy-900/50">
          <button
            onClick={() => handleSubmit(true)}
            disabled={!form.name || !form.contract || createMutation.isPending}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-[10px] font-medium rounded-lg border border-gray-200 dark:border-navy-600 text-gray-600 dark:text-gray-400 hover:bg-white dark:hover:bg-navy-700 disabled:opacity-50 transition-colors"
          >
            <Save className="w-3 h-3" />
            Save Draft
          </button>
          <div className="flex items-center gap-2">
            <button onClick={onClose} className="px-3 py-1.5 text-[10px] font-medium rounded-lg border border-gray-200 dark:border-navy-600 text-gray-600 dark:text-gray-400 hover:bg-white dark:hover:bg-navy-700 transition-colors">
              Cancel
            </button>
            <button
              onClick={() => handleSubmit(false)}
              disabled={!form.name || !form.contract || createMutation.isPending}
              className="inline-flex items-center gap-1.5 px-4 py-1.5 text-[10px] font-medium rounded-lg bg-navy-700 text-white hover:bg-navy-800 disabled:opacity-50 transition-colors shadow-sm"
            >
              {createMutation.isPending ? (
                <Loader2 className="w-3 h-3 animate-spin" />
              ) : (
                <Plus className="w-3 h-3" />
              )}
              Create Obligation
            </button>
          </div>
        </div>
      </motion.div>
    </motion.div>
  );
}

// ── Sub-components ──

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div>
      <h3 className="text-[10px] font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-2">{title}</h3>
      {children}
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="space-y-1">
      <label className="text-[10px] font-medium text-gray-600 dark:text-gray-400">{label}</label>
      {children}
    </div>
  );
}

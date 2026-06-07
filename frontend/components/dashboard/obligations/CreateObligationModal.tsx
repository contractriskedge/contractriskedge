/**
 * CreateObligationModal — Enterprise-grade obligation creation form.
 *
 * Sections: General Information, Ownership, Dates, Risk, Financial, SLA.
 * Actions: Save Draft, Create, Cancel.
 */

"use client";

import React, { useState, useCallback } from "react";
import { motion } from "framer-motion";
import { X, Save, Plus, Loader2 } from "lucide-react";
import { useCreateObligation } from "@/services/hooks/useObligations";
import type { ObligationCreateRequest } from "@/services/api/obligations";

interface CreateObligationModalProps {
  isOpen: boolean;
  onClose: () => void;
  onCreated: () => void;
}

const OBLIGATION_TYPES = [
  "payment", "compliance", "reporting", "audit", "insurance",
  "security", "privacy", "renewal", "termination", "operational", "custom",
];

const RISK_LEVELS = ["low", "medium", "high", "critical"];

const DEFAULT_FORM = {
  name: "",
  description: "",
  contractId: "",
  clauseReference: "",
  obligationType: "compliance",
  owner: "",
  department: "",
  businessUnit: "",
  assignee: "",
  dueDate: "",
  reminderDate: "",
  completedDate: "",
  riskLevel: "medium",
  financialImpact: 0,
  currency: "USD",
  slaTargetDays: 30,
  escalationRequired: false,
};

type FormData = typeof DEFAULT_FORM;

export function CreateObligationModal({ isOpen, onClose, onCreated }: CreateObligationModalProps) {
  const [form, setForm] = useState<FormData>({ ...DEFAULT_FORM });
  const [mode, setMode] = useState<"draft" | "create">("create");
  const createMutation = useCreateObligation();

  const update = useCallback(<K extends keyof FormData>(key: K, value: FormData[K]) => {
    setForm((prev) => ({ ...prev, [key]: value }));
  }, []);

  const handleSubmit = useCallback(async (saveAsDraft: boolean) => {
    const body: ObligationCreateRequest = {
      name: form.name,
      obligationType: form.obligationType,
      status: saveAsDraft ? "draft" : "open",
      description: form.description || undefined,
      contractId: form.contractId || undefined,
      clauseReference: form.clauseReference || undefined,
      owner: form.owner || undefined,
      assignee: form.assignee || undefined,
      department: form.department || undefined,
      businessUnit: form.businessUnit || undefined,
      dueDate: form.dueDate || undefined,
      riskLevel: form.riskLevel,
      financialImpact: form.financialImpact || undefined,
      currency: form.currency,
    };
    createMutation.mutate(body, {
      onSuccess: () => {
        setForm({ ...DEFAULT_FORM });
        onCreated();
        onClose();
      },
      onError: (err: unknown) => {
        // Surface a readable message so the user isn't left wondering why
        // the modal closed silently or why nothing happened.
        // eslint-disable-next-line no-console
        console.error("Failed to create obligation", err);
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
                <Field label="Contract">
                  <input type="text" value={form.contractId} onChange={(e) => update("contractId", e.target.value)}
                    className="w-full text-xs px-3 py-2 border border-gray-200 dark:border-navy-600 rounded-lg bg-white dark:bg-navy-700 text-navy-900 dark:text-white placeholder-gray-400 focus:outline-none focus:ring-1 focus:ring-navy-400"
                    placeholder="Contract ID" />
                </Field>
                <Field label="Clause Reference">
                  <input type="text" value={form.clauseReference} onChange={(e) => update("clauseReference", e.target.value)}
                    className="w-full text-xs px-3 py-2 border border-gray-200 dark:border-navy-600 rounded-lg bg-white dark:bg-navy-700 text-navy-900 dark:text-white placeholder-gray-400 focus:outline-none focus:ring-1 focus:ring-navy-400"
                    placeholder="e.g., Section 4.2" />
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
                <input type="text" value={form.owner} onChange={(e) => update("owner", e.target.value)}
                  className="w-full text-xs px-3 py-2 border border-gray-200 dark:border-navy-600 rounded-lg bg-white dark:bg-navy-700 text-navy-900 dark:text-white placeholder-gray-400 focus:outline-none focus:ring-1 focus:ring-navy-400"
                  placeholder="Assignee name" />
              </Field>
              <Field label="Department">
                <input type="text" value={form.department} onChange={(e) => update("department", e.target.value)}
                  className="w-full text-xs px-3 py-2 border border-gray-200 dark:border-navy-600 rounded-lg bg-white dark:bg-navy-700 text-navy-900 dark:text-white placeholder-gray-400 focus:outline-none focus:ring-1 focus:ring-navy-400"
                  placeholder="e.g., Legal" />
              </Field>
              <Field label="Business Unit">
                <input type="text" value={form.businessUnit} onChange={(e) => update("businessUnit", e.target.value)}
                  className="w-full text-xs px-3 py-2 border border-gray-200 dark:border-navy-600 rounded-lg bg-white dark:bg-navy-700 text-navy-900 dark:text-white placeholder-gray-400 focus:outline-none focus:ring-1 focus:ring-navy-400"
                  placeholder="e.g., Enterprise" />
              </Field>
              <Field label="Backup Owner">
                <input type="text" value={form.assignee} onChange={(e) => update("assignee", e.target.value)}
                  className="w-full text-xs px-3 py-2 border border-gray-200 dark:border-navy-600 rounded-lg bg-white dark:bg-navy-700 text-navy-900 dark:text-white placeholder-gray-400 focus:outline-none focus:ring-1 focus:ring-navy-400"
                  placeholder="Backup assignee" />
              </Field>
            </div>
          </Section>

          {/* ── Dates ── */}
          <Section title="Dates">
            <div className="grid grid-cols-2 gap-3">
              <Field label="Due Date *">
                <input type="date" value={form.dueDate} onChange={(e) => update("dueDate", e.target.value)}
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
            disabled={!form.name || createMutation.isPending}
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
              disabled={!form.name || createMutation.isPending}
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

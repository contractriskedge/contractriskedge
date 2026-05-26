"use client";

import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  CheckCircle, XCircle, AlertTriangle, Info, Edit3, Save,
  X, ChevronDown, ChevronRight, Brain, Sparkles,
} from "lucide-react";
import type { ExtractedMetadata, ValidationResult } from "./types";

interface MetadataReviewProps {
  metadata: ExtractedMetadata;
  validations: ValidationResult[];
  onUpdateField: (field: string, value: string) => void;
}

const fieldLabels: Record<string, string> = {
  contractTitle: "Contract Title",
  counterparty: "Counterparty",
  contractType: "Contract Type",
  effectiveDate: "Effective Date",
  expirationDate: "Expiration Date",
  jurisdiction: "Jurisdiction",
  governingLaw: "Governing Law",
  businessUnit: "Business Unit",
  value: "Contract Value",
  currency: "Currency",
  status: "Status",
  description: "Description",
};

export function MetadataReview({ metadata, validations, onUpdateField }: MetadataReviewProps) {
  const [editingField, setEditingField] = useState<string | null>(null);
  const [editValue, setEditValue] = useState("");

  const startEdit = (field: string, currentValue: string) => {
    setEditingField(field);
    setEditValue(currentValue);
  };

  const saveEdit = () => {
    if (editingField) {
      onUpdateField(editingField, editValue);
      setEditingField(null);
    }
  };

  const getValidationForField = (field: string) => validations.find(v => v.field === field);

  const typeIcons: Record<string, React.ReactNode> = {
    error: <XCircle className="w-3 h-3 text-red-500" />,
    warning: <AlertTriangle className="w-3 h-3 text-amber-500" />,
    info: <Info className="w-3 h-3 text-blue-500" />,
    success: <CheckCircle className="w-3 h-3 text-green-500" />,
  };

  const typeColors: Record<string, string> = {
    error: "border-red-200 bg-red-50 dark:border-red-900/30 dark:bg-red-900/10",
    warning: "border-amber-200 bg-amber-50 dark:border-amber-900/30 dark:bg-amber-900/10",
    info: "border-blue-200 bg-blue-50 dark:border-blue-900/30 dark:bg-blue-900/10",
    success: "border-green-200 bg-green-50 dark:border-green-900/30 dark:bg-green-900/10",
  };

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <h4 className="text-[9px] font-semibold text-gray-500 uppercase tracking-wider">Extracted Metadata</h4>
        <div className="flex items-center gap-1 text-[8px] text-gray-400">
          <Brain className="w-2.5 h-2.5" />
          AI Extracted
        </div>
      </div>

      <div className="grid grid-cols-2 gap-1.5">
        {Object.entries(fieldLabels).map(([field, label]) => {
          const value = metadata[field] || "";
          const validation = getValidationForField(field);
          const isEditing = editingField === field;

          return (
            <div key={field} className={`border rounded-lg p-2 transition-colors ${
              validation ? typeColors[validation.type] : "border-gray-200 dark:border-navy-600"
            }`}>
              <div className="flex items-center justify-between mb-0.5">
                <span className="text-[8px] text-gray-500 uppercase tracking-wider">{label}</span>
                {validation && (
                  <div className="flex items-center gap-0.5" title={validation.message}>
                    {typeIcons[validation.type]}
                    <span className="text-[7px] text-gray-400">{validation.confidence}%</span>
                  </div>
                )}
              </div>

              {isEditing ? (
                <div className="flex items-center gap-1">
                  <input
                    type="text"
                    value={editValue}
                    onChange={e => setEditValue(e.target.value)}
                    onKeyDown={e => { if (e.key === "Enter") saveEdit(); if (e.key === "Escape") setEditingField(null); }}
                    className="flex-1 px-1.5 py-0.5 text-[10px] border border-gold-400 rounded bg-white dark:bg-navy-800 text-navy-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-gold-400"
                    autoFocus
                  />
                  <button onClick={saveEdit} className="p-0.5 text-green-600 hover:text-green-700"><Save className="w-2.5 h-2.5" /></button>
                  <button onClick={() => setEditingField(null)} className="p-0.5 text-gray-400 hover:text-gray-600"><X className="w-2.5 h-2.5" /></button>
                </div>
              ) : (
                <div className="flex items-center justify-between group">
                  <span className="text-[10px] font-medium text-navy-900 dark:text-white truncate">{value || <span className="text-gray-300 italic">Not extracted</span>}</span>
                  <button
                    onClick={() => startEdit(field, value)}
                    className="p-0.5 text-gray-300 hover:text-gold-500 opacity-0 group-hover:opacity-100 transition-all"
                  >
                    <Edit3 className="w-2.5 h-2.5" />
                  </button>
                </div>
              )}

              {/* Validation message */}
              {validation && validation.type !== "success" && (
                <p className="text-[7px] text-gray-500 mt-0.5 leading-tight">{validation.message}</p>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

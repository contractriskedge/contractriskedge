/**
 * TemplateEditorPage — Create or edit a template with variable management.
 */

"use client";

import React, { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  ArrowLeft, Save, Loader2, Plus, Trash2, AlertTriangle, FileText,
  GripVertical, ChevronUp, ChevronDown,
} from "lucide-react";
import { api } from "@/services";
import type { TemplateCategory, TemplateDetail } from "./types";

interface TemplateEditorPageProps {
  templateId?: string; // undefined = create new
}

const FIELD_TYPES = [
  { value: "text", label: "Text" },
  { value: "currency", label: "Currency" },
  { value: "number", label: "Number" },
  { value: "date", label: "Date" },
  { value: "boolean", label: "Boolean" },
  { value: "dropdown", label: "Dropdown" },
  { value: "multi_select", label: "Multi Select" },
  { value: "address", label: "Address" },
  { value: "email", label: "Email" },
  { value: "phone", label: "Phone" },
  { value: "url", label: "URL" },
];

interface VariableEntry {
  key: string;
  label: string;
  field_type: string;
  is_required: boolean;
  display_order: number;
  options: string[];
}

export default function TemplateEditorPage({ templateId }: TemplateEditorPageProps) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const isEditing = !!templateId;

  const { data: categoriesData } = useQuery({
    queryKey: ["template-categories"],
    queryFn: () => api.get<{ data: TemplateCategory[]; total: number }>("/templates/categories"),
    staleTime: 60_000,
  });

  const { data: existingTemplate } = useQuery<TemplateDetail>({
    queryKey: ["template", templateId],
    queryFn: () => api.get(`/templates/${templateId}`),
    enabled: isEditing,
    staleTime: 30_000,
  });

  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [categoryId, setCategoryId] = useState("");
  const [tagsStr, setTagsStr] = useState("");
  const [owner, setOwner] = useState("");
  const [department, setDepartment] = useState("");
  const [content, setContent] = useState("");
  const [variables, setVariables] = useState<VariableEntry[]>([]);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  // Load existing template data
  useEffect(() => {
    if (existingTemplate) {
      setName(existingTemplate.name);
      setDescription(existingTemplate.description || "");
      setCategoryId(existingTemplate.category?.id || "");
      setTagsStr(existingTemplate.tags.join(", "));
      setOwner(existingTemplate.owner || "");
      setDepartment(existingTemplate.department || "");
      if (existingTemplate.current_version) {
        setContent(existingTemplate.current_version.placeholder_content || "");
        setVariables(
          (existingTemplate.current_version.variables || []).map((v, i) => ({
            key: v.key,
            label: v.label,
            field_type: v.field_type,
            is_required: v.is_required,
            display_order: i,
            options: Array.isArray(v.options) ? v.options : [],
          })),
        );
      }
    }
  }, [existingTemplate]);

  // Auto-extract variables from content
  const extractVariables = () => {
    const matches = content.matchAll(/\{\{(\w+)\}\}/g);
    const seen = new Set<string>();
    const extracted: VariableEntry[] = [];
    for (const match of matches) {
      const key = match[1];
      if (!seen.has(key)) {
        seen.add(key);
        const label = key.replace(/([a-z])([A-Z])/g, "$1 $2").replace(/([A-Z]+)([A-Z][a-z])/g, "$1 $2");
        extracted.push({
          key,
          label,
          field_type: inferFieldType(key),
          is_required: true,
          display_order: extracted.length,
          options: [],
        });
      }
    }
    // Merge with existing variables (preserve labels/types)
    const existingMap = new Map(variables.map((v) => [v.key, v]));
    const merged = extracted.map((v) => existingMap.get(v.key) || v);
    // Add any existing variables not found in content
    for (const v of variables) {
      if (!seen.has(v.key)) {
        merged.push(v);
      }
    }
    setVariables(merged);
  };

  const inferFieldType = (key: string): string => {
    const k = key.toLowerCase();
    if (/date|day|effective|expiration|renewal/.test(k)) return "date";
    if (/email/.test(k)) return "email";
    if (/phone|telephone|fax/.test(k)) return "phone";
    if (/url|website/.test(k)) return "url";
    if (/value|amount|price|fee|cost|budget/.test(k)) return "currency";
    if (/count|number|quantity|percent|rate/.test(k)) return "number";
    if (/boolean|is_|has_|enable|flag/.test(k)) return "boolean";
    if (/address|location/.test(k)) return "address";
    return "text";
  };

  const addVariable = () => {
    const key = `var${variables.length + 1}`;
    setVariables([...variables, { key, label: key, field_type: "text", is_required: false, display_order: variables.length, options: [] }]);
  };

  const removeVariable = (index: number) => {
    setVariables(variables.filter((_, i) => i !== index));
  };

  const updateVariable = (index: number, field: string, value: any) => {
    const updated = [...variables];
    (updated[index] as any)[field] = value;
    setVariables(updated);
  };

  const moveVariable = (index: number, direction: -1 | 1) => {
    const newIndex = index + direction;
    if (newIndex < 0 || newIndex >= variables.length) return;
    const updated = [...variables];
    [updated[index], updated[newIndex]] = [updated[newIndex], updated[index]];
    updated.forEach((v, i) => (v.display_order = i));
    setVariables(updated);
  };

  const handleSave = async () => {
    if (!name.trim()) { setError("Template name is required"); return; }
    setSaving(true);
    setError("");
    try {
      const versionData = {
        version_number: existingTemplate?.current_version ? existingTemplate.current_version.version_number + 1 : 1,
        label: isEditing ? `Updated ${new Date().toLocaleDateString()}` : "Initial version",
        change_summary: isEditing ? "Template updated" : "Initial creation",
        variables: variables.map((v) => ({
          key: v.key,
          label: v.label,
          field_type: v.field_type,
          is_required: v.is_required,
          display_order: v.display_order,
          options: v.field_type === "dropdown" || v.field_type === "multi_select" ? v.options : [],
        })),
        placeholder_content: content,
        file_name: `${name.replace(/[^a-zA-Z0-9]/g, "_")}_template.docx`,
      };

      if (isEditing) {
        // Update template
        await api.put(`/templates/${templateId}`, {
          name,
          description: description || null,
          category_id: categoryId || null,
          tags: tagsStr.split(",").map((t) => t.trim()).filter(Boolean),
          owner: owner || null,
          department: department || null,
        });
        // Create new version
        await api.post(`/templates/${templateId}/versions`, versionData);
      } else {
        // Create template with initial version
        await api.post("/templates", {
          name,
          description: description || null,
          category_id: categoryId || null,
          tags: tagsStr.split(",").map((t) => t.trim()).filter(Boolean),
          owner: owner || null,
          department: department || null,
          version: versionData,
        });
      }
      queryClient.invalidateQueries({ queryKey: ["templates"] });
      router.push("/templates");
    } catch (err: any) {
      setError(err?.message || "Failed to save template");
    } finally {
      setSaving(false);
    }
  };

  const categories = categoriesData?.data ?? [];

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <button onClick={() => router.push("/templates")} className="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-navy-700 text-gray-500">
            <ArrowLeft className="w-4 h-4" />
          </button>
          <h1 className="text-xl font-bold text-navy-900 dark:text-white">{isEditing ? "Edit Template" : "New Template"}</h1>
        </div>
        <button
          onClick={handleSave}
          disabled={saving}
          className="inline-flex items-center gap-1.5 px-3 py-2 text-sm font-medium rounded-lg bg-navy-700 text-white hover:bg-navy-800 disabled:opacity-50"
        >
          {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
          {saving ? "Saving..." : "Save Template"}
        </button>
      </div>

      {error && (
        <div className="flex items-center gap-2 p-3 rounded-lg bg-red-50 border border-red-200 text-red-700 text-xs">
          <AlertTriangle className="w-4 h-4" /> {error}
        </div>
      )}

      <div className="grid grid-cols-3 gap-6">
        {/* Left: Template Details */}
        <div className="col-span-2 space-y-4">
          <div className="rounded-lg border border-gray-200 dark:border-navy-700 p-4 bg-white dark:bg-navy-800">
            <h3 className="text-xs font-semibold text-gray-500 uppercase mb-3">Template Details</h3>
            <div className="space-y-3">
              <div>
                <label className="text-[10px] font-medium text-gray-600">Name *</label>
                <input type="text" value={name} onChange={(e) => setName(e.target.value)}
                  className="w-full mt-1 px-3 py-2 text-sm border border-gray-200 rounded-lg focus:border-navy-400 focus:ring-1 focus:ring-navy-400" />
              </div>
              <div>
                <label className="text-[10px] font-medium text-gray-600">Description</label>
                <textarea value={description} onChange={(e) => setDescription(e.target.value)} rows={3}
                  className="w-full mt-1 px-3 py-2 text-sm border border-gray-200 rounded-lg focus:border-navy-400 focus:ring-1 focus:ring-navy-400" />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-[10px] font-medium text-gray-600">Category</label>
                  <select value={categoryId} onChange={(e) => setCategoryId(e.target.value)}
                    className="w-full mt-1 px-3 py-2 text-sm border border-gray-200 rounded-lg focus:border-navy-400 focus:ring-1 focus:ring-navy-400">
                    <option value="">Uncategorized</option>
                    {categories.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
                  </select>
                </div>
                <div>
                  <label className="text-[10px] font-medium text-gray-600">Tags (comma separated)</label>
                  <input type="text" value={tagsStr} onChange={(e) => setTagsStr(e.target.value)}
                    className="w-full mt-1 px-3 py-2 text-sm border border-gray-200 rounded-lg focus:border-navy-400 focus:ring-1 focus:ring-navy-400" />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-[10px] font-medium text-gray-600">Owner</label>
                  <input type="text" value={owner} onChange={(e) => setOwner(e.target.value)}
                    className="w-full mt-1 px-3 py-2 text-sm border border-gray-200 rounded-lg focus:border-navy-400 focus:ring-1 focus:ring-navy-400" />
                </div>
                <div>
                  <label className="text-[10px] font-medium text-gray-600">Department</label>
                  <input type="text" value={department} onChange={(e) => setDepartment(e.target.value)}
                    className="w-full mt-1 px-3 py-2 text-sm border border-gray-200 rounded-lg focus:border-navy-400 focus:ring-1 focus:ring-navy-400" />
                </div>
              </div>
            </div>
          </div>

          {/* Template Content */}
          <div className="rounded-lg border border-gray-200 dark:border-navy-700 p-4 bg-white dark:bg-navy-800">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-xs font-semibold text-gray-500 uppercase">Template Content</h3>
              <button onClick={extractVariables}
                className="text-[10px] font-medium text-blue-600 hover:text-blue-700">
                Extract {'{{'}variables{'}}'}
              </button>
            </div>
            <p className="text-[9px] text-gray-400 mb-2">Use {'{{'}VariableName{'}}'} placeholders for dynamic fields.</p>
            <textarea
              value={content}
              onChange={(e) => setContent(e.target.value)}
              rows={20}
              className="w-full px-3 py-2 text-[11px] font-mono border border-gray-200 rounded-lg focus:border-navy-400 focus:ring-1 focus:ring-navy-400 bg-gray-50 dark:bg-navy-900"
              placeholder={`MASTER SERVICE AGREEMENT\n\nThis Agreement is entered into as of {{EffectiveDate}} by {{CompanyName}} and {{VendorName}}.\n\n...`}
            />
          </div>
        </div>

        {/* Right: Variables */}
        <div className="space-y-4">
          <div className="rounded-lg border border-gray-200 dark:border-navy-700 p-4 bg-white dark:bg-navy-800">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-xs font-semibold text-gray-500 uppercase">Variables ({variables.length})</h3>
              <button onClick={addVariable} className="p-1 rounded hover:bg-gray-100 dark:hover:bg-navy-700 text-gray-400">
                <Plus className="w-3.5 h-3.5" />
              </button>
            </div>
            {variables.length === 0 ? (
              <p className="text-[10px] text-gray-400 italic">No variables defined. Add them manually or click "Extract" above.</p>
            ) : (
              <div className="space-y-2 max-h-[600px] overflow-y-auto">
                {variables.map((v, i) => (
                  <div key={i} className="p-2 rounded bg-gray-50 dark:bg-navy-900 border border-gray-100 dark:border-navy-700">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-[9px] font-mono font-medium text-navy-700 dark:text-navy-200">{`{{${v.key}}}`}</span>
                      <div className="flex items-center gap-0.5">
                        <button onClick={() => moveVariable(i, -1)} className="p-0.5 text-gray-400 hover:text-gray-600"><ChevronUp className="w-3 h-3" /></button>
                        <button onClick={() => moveVariable(i, 1)} className="p-0.5 text-gray-400 hover:text-gray-600"><ChevronDown className="w-3 h-3" /></button>
                        <button onClick={() => removeVariable(i)} className="p-0.5 text-red-400 hover:text-red-600"><Trash2 className="w-3 h-3" /></button>
                      </div>
                    </div>
                    <div className="space-y-1">
                      <input type="text" value={v.key} onChange={(e) => updateVariable(i, "key", e.target.value)}
                        className="w-full px-2 py-1 text-[9px] font-mono border border-gray-200 rounded" placeholder="Key" />
                      <input type="text" value={v.label} onChange={(e) => updateVariable(i, "label", e.target.value)}
                        className="w-full px-2 py-1 text-[9px] border border-gray-200 rounded" placeholder="Label" />
                      <div className="flex gap-1">
                        <select value={v.field_type} onChange={(e) => updateVariable(i, "field_type", e.target.value)}
                          className="flex-1 px-2 py-1 text-[9px] border border-gray-200 rounded">
                          {FIELD_TYPES.map((ft) => <option key={ft.value} value={ft.value}>{ft.label}</option>)}
                        </select>
                        <label className="flex items-center gap-1 text-[9px] text-gray-500">
                          <input type="checkbox" checked={v.is_required} onChange={(e) => updateVariable(i, "is_required", e.target.checked)} />
                          Required
                        </label>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

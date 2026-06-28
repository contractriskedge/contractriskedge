"use client";

import React, { useState, useCallback } from "react";
import {
  Plus, Trash2, GripVertical, Play, AlertTriangle, CheckCircle,
  Users, Shield, Clock,
} from "lucide-react";

// ── Types ──────────────────────────────────────────────────────────

type FieldType = "number" | "text" | "list" | "date" | "boolean";

interface FieldDef {
  name: string;
  label: string;
  type: FieldType;
  options?: string[];
}

interface Condition {
  id: string;
  field: string;
  operator: string;
  value: string;
}

interface ConditionGroup {
  id: string;
  combinator: "ALL" | "ANY";
  conditions: (Condition | ConditionGroup)[];
}

interface Rule {
  id: string;
  name: string;
  priority: number;
  condition: ConditionGroup;
  assignee_role: string;
  approval_mode: string;
  resolution_strategy: string;
  sla_hours: number;
}

// ── Available Fields ───────────────────────────────────────────────

const AVAILABLE_FIELDS: FieldDef[] = [
  { name: "contract.risk_score", label: "Risk Score", type: "number" },
  { name: "contract.value", label: "Contract Value", type: "number" },
  { name: "contract.contract_type", label: "Contract Type", type: "text", options: ["MSA", "NDA", "SOW", "Amendment", "License", "DPA"] },
  { name: "contract.jurisdiction", label: "Country", type: "text", options: ["US", "UK", "DE", "FR", "IN", "CA", "AU", "JP", "BR", "SG"] },
  { name: "contract.department", label: "Department", type: "text", options: ["Engineering", "Procurement", "Legal", "Sales", "HR", "Finance", "Marketing"] },
  { name: "contract.region", label: "Region", type: "text", options: ["AMER", "EMEA", "APAC", "LATAM"] },
  { name: "contract.industry", label: "Industry", type: "text", options: ["Technology", "Healthcare", "Finance", "Manufacturing", "Retail", "Energy"] },
  { name: "contract.has_redlines", label: "Has Redlines", type: "boolean" },
  { name: "supplier.region", label: "Supplier Region", type: "text", options: ["AMER", "EMEA", "APAC"] },
  { name: "supplier.tier", label: "Supplier Tier", type: "number" },
  { name: "ai.findings_count", label: "AI Findings Count", type: "number" },
  { name: "ai.top_risk", label: "AI Top Risk", type: "text", options: ["GDPR", "Data Privacy", "IP", "Indemnification", "Limitation", "Termination"] },
];

const NUMERIC_OPS = ["=", "!=", ">", ">=", "<", "<=", "BETWEEN"];
const TEXT_OPS = ["=", "!=", "CONTAINS", "STARTS WITH", "ENDS WITH"];
const LIST_OPS = ["IN", "NOT IN"];
const DATE_OPS = ["Before", "After", "Between"];
const BOOL_OPS = ["is"];

const RESOLUTION_STRATEGIES = [
  "role", "specific_user", "manager", "round_robin", "least_loaded",
  "random", "hierarchy", "business_owner", "contract_owner",
  "department_head", "legal_director", "custom_resolver",
];

const APPROVAL_MODES = [
  "any_one", "all_required", "majority", "minimum_count",
  "weighted_voting", "sequential", "parallel",
];

let idCounter = 0;
const uid = () => `rule_${++idCounter}`;

const defaultCondition = (): Condition => ({ id: uid(), field: "", operator: "", value: "" });
const defaultGroup = (combinator: "ALL" | "ANY" = "ALL"): ConditionGroup => ({
  id: uid(), combinator, conditions: [defaultCondition()],
});

const defaultRule = (priority: number): Rule => ({
  id: uid(),
  name: `Rule ${priority}`,
  priority,
  condition: defaultGroup("ALL"),
  assignee_role: "",
  approval_mode: "all_required",
  resolution_strategy: "least_loaded",
  sla_hours: 48,
});

// ── JSON Logic Generation ──────────────────────────────────────────

function generateJsonLogic(group: ConditionGroup): Record<string, unknown> {
  const items = group.conditions.map((c) => {
    if ("combinator" in c) return generateJsonLogic(c as ConditionGroup);
    return generateConditionLogic(c as Condition);
  });
  if (items.length === 0) return {};
  if (items.length === 1) return items[0];
  return group.combinator === "ALL" ? { and: items } : { or: items };
}

function generateConditionLogic(c: Condition): Record<string, unknown> {
  if (!c.field || !c.operator) return {};
  const varPath = { var: c.field };
  const upperOp = c.operator.toUpperCase();

  if (upperOp === "IS" && c.value.toLowerCase() === "true") return varPath;
  if (upperOp === "IS" && c.value.toLowerCase() === "false") return { "!": [varPath] };
  if (upperOp === "CONTAINS") return { in: [c.value, varPath] };
  if (upperOp === "STARTS WITH") return { starts_with: [varPath, c.value] };
  if (upperOp === "ENDS WITH") return { ends_with: [varPath, c.value] };
  if (upperOp === "IN") return { in: [varPath, (c.value || "").split(",").map((s) => s.trim())] };
  if (upperOp === "NOT IN") return { "!": [{ in: [varPath, (c.value || "").split(",").map((s) => s.trim())] }] };
  if (upperOp === "BETWEEN") {
    const parts = (c.value || "").split(",").map((s) => parseFloat(s.trim()));
    return { and: [{ ">=": [varPath, parts[0]] }, { "<=": [varPath, parts[1] ?? parts[0]] }] };
  }
  if (upperOp === "BEFORE") return { "<": [varPath, c.value] };
  if (upperOp === "AFTER") return { ">": [varPath, c.value] };

  const opMap: Record<string, string> = { "=": "==", "!=": "!=", ">": ">", ">=": ">=", "<": "<", "<=": "<=" };
  const op = opMap[c.operator];
  if (!op) return {};
  const numVal = parseFloat(c.value);
  return { [op]: [varPath, isNaN(numVal) ? c.value : numVal] };
}

// ── Human-Readable Explanation ─────────────────────────────────────

function explainGroup(group: ConditionGroup, fields: FieldDef[]): string[] {
  const lines: string[] = [];
  const items = group.conditions.map((c) => {
    if ("combinator" in c) return `(${explainGroup(c as ConditionGroup, fields).join(" ")})`;
    return explainCondition(c as Condition, fields);
  });
  const joiner = group.combinator === "ALL" ? " AND " : " OR ";
  items.forEach((item, i) => {
    if (i > 0) lines.push(joiner);
    lines.push(item);
  });
  return lines;
}

function explainCondition(c: Condition, fields: FieldDef[]): string {
  const field = fields.find((f) => f.name === c.field);
  const label = field?.label ?? c.field;
  if (c.operator === "is") return `${label} is ${c.value}`;
  if (c.operator === "IN") return `${label} is one of ${c.value}`;
  if (c.operator === "NOT IN") return `${label} is not one of ${c.value}`;
  if (c.operator === "CONTAINS") return `${label} contains "${c.value}"`;
  if (c.operator === "STARTS WITH") return `${label} starts with "${c.value}"`;
  if (c.operator === "ENDS WITH") return `${label} ends with "${c.value}"`;
  if (c.operator === "BETWEEN") return `${label} is between ${c.value}`;
  return `${label} ${c.operator} ${c.value}`;
}

// ── Props ──────────────────────────────────────────────────────────

interface Props {
  onSave: (rules: Rule[]) => void;
  onBack: () => void;
}

export function RuleBuilder({ onSave, onBack }: Props) {
  const [rules, setRules] = useState<Rule[]>([defaultRule(1), defaultRule(2)]);
  const [selectedRuleIdx, setSelectedRuleIdx] = useState(0);
  const [testValues, setTestValues] = useState<Record<string, string>>({});
  const [testResult, setTestResult] = useState<{ matched: boolean; ruleName: string } | null>(null);

  const selectedRule = rules[selectedRuleIdx];

  // ── Rule Operations ─────────────────────────────────────────────

  const addRule = () => {
    setRules([...rules, defaultRule(rules.length + 1)]);
  };

  const deleteRule = (idx: number) => {
    if (rules.length <= 1) return;
    const newRules = rules.filter((_, i) => i !== idx).map((r, i) => ({ ...r, priority: i + 1 }));
    setRules(newRules);
    if (selectedRuleIdx >= newRules.length) setSelectedRuleIdx(newRules.length - 1);
  };

  const updateRule = (idx: number, updates: Partial<Rule>) => {
    setRules(rules.map((r, i) => i === idx ? { ...r, ...updates } : r));
  };

  // ── Condition Operations ────────────────────────────────────────

  const addCondition = (groupId: string, combinator: "ALL" | "ANY") => {
    const update = (items: (Condition | ConditionGroup)[]): (Condition | ConditionGroup)[] =>
      items.map((item) => {
        if ("combinator" in item && (item as ConditionGroup).id === groupId) {
          return { ...(item as ConditionGroup), conditions: [...(item as ConditionGroup).conditions, defaultCondition()] };
        }
        if ("combinator" in item) return { ...(item as ConditionGroup), conditions: update((item as ConditionGroup).conditions) };
        return item;
      });
    setRules(rules.map((r, i) => i === selectedRuleIdx ? { ...r, condition: { ...r.condition, conditions: update(r.condition.conditions) } } : r));
  };

  const addGroup = (parentId: string, combinator: "ALL" | "ANY") => {
    const update = (items: (Condition | ConditionGroup)[]): (Condition | ConditionGroup)[] =>
      items.map((item) => {
        if ("combinator" in item && (item as ConditionGroup).id === parentId) {
          return { ...(item as ConditionGroup), conditions: [...(item as ConditionGroup).conditions, defaultGroup(combinator)] };
        }
        if ("combinator" in item) return { ...(item as ConditionGroup), conditions: update((item as ConditionGroup).conditions) };
        return item;
      });
    setRules(rules.map((r, i) => i === selectedRuleIdx ? { ...r, condition: { ...r.condition, conditions: update(r.condition.conditions) } } : r));
  };

  const updateConditionInGroup = (groupId: string, condId: string, updates: Partial<Condition>) => {
    const update = (items: (Condition | ConditionGroup)[]): (Condition | ConditionGroup)[] =>
      items.map((item) => {
        if ("combinator" in item) {
          return { ...(item as ConditionGroup), conditions: update((item as ConditionGroup).conditions) };
        }
        const c = item as Condition;
        if (c.id === condId) return { ...c, ...updates };
        return c;
      });
    setRules(rules.map((r, i) => i === selectedRuleIdx ? { ...r, condition: { ...r.condition, conditions: update(r.condition.conditions) } } : r));
  };

  const removeCondition = (groupId: string, condId: string) => {
    const remove = (items: (Condition | ConditionGroup)[]): (Condition | ConditionGroup)[] =>
      items.filter((item) => {
        if ("combinator" in item) {
          const g = item as ConditionGroup;
          if (g.id === groupId) {
            (g as ConditionGroup).conditions = remove(g.conditions);
            return g.conditions.length > 0;
          }
          return true;
        }
        return (item as Condition).id !== condId;
      });
    setRules(rules.map((r, i) => i === selectedRuleIdx ? { ...r, condition: { ...r.condition, conditions: remove(r.condition.conditions) } } : r));
  };

  // ── Test Rule ───────────────────────────────────────────────────

  const evaluateTest = () => {
    if (!selectedRule) return;
    const logic = generateJsonLogic(selectedRule.condition);
    const context: Record<string, unknown> = {};
    for (const [key, val] of Object.entries(testValues)) {
      const field = AVAILABLE_FIELDS.find((f) => f.name === key);
      if (field?.type === "number") context[key] = parseFloat(val) || 0;
      else if (field?.type === "boolean") context[key] = val.toLowerCase() === "true";
      else context[key] = val;
    }
    try {
      const matched = evaluateJsonLogic(logic, context);
      setTestResult({ matched: matched as boolean, ruleName: selectedRule.name });
    } catch {
      setTestResult({ matched: false, ruleName: selectedRule.name });
    }
  };

  // ── Validation ──────────────────────────────────────────────────

  const errors: string[] = [];
  rules.forEach((r, i) => {
    if (!r.assignee_role) errors.push(`Rule ${i + 1} "${r.name}" has no assignee`);
    if (r.priority < 1) errors.push(`Rule ${i + 1} "${r.name}" has invalid priority`);
  });

  // Check for duplicate priorities
  const priorities = rules.map((r) => r.priority);
  const dupPriorities = priorities.filter((p, i) => priorities.indexOf(p) !== i);
  if (dupPriorities.length > 0) errors.push(`Duplicate priorities: ${[...new Set(dupPriorities)].join(", ")}`);

  // ── Render ──────────────────────────────────────────────────────

  return (
    <div className="flex gap-6 h-[calc(100vh-12rem)]">
      {/* Left: Rule List */}
      <div className="w-80 shrink-0 space-y-4 overflow-y-auto pr-2">
        <h2 className="text-lg font-semibold text-gray-100">Routing Rules</h2>

        <div className="space-y-2">
          {rules.map((rule, i) => (
            <button
              key={rule.id}
              onClick={() => setSelectedRuleIdx(i)}
              className={`w-full p-3 rounded-lg border text-left transition-colors ${
                i === selectedRuleIdx
                  ? "bg-navy-700 border-gold-500/50"
                  : "bg-navy-800/50 border-navy-700 hover:border-navy-600"
              }`}
            >
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium text-gray-200">{rule.name}</span>
                <span className="text-xs text-gray-500">#{rule.priority}</span>
              </div>
              <div className="flex items-center gap-2 mt-1 text-xs text-gray-500">
                <Shield className="w-3 h-3" />
                {rule.assignee_role || "No assignee"}
              </div>
              {i > 0 && (
                <button
                  onClick={(e) => { e.stopPropagation(); deleteRule(i); }}
                  className="mt-1 text-xs text-red-400 hover:text-red-300"
                >
                  Remove
                </button>
              )}
            </button>
          ))}
        </div>

        <button
          onClick={addRule}
          className="w-full flex items-center justify-center gap-2 p-3 border border-dashed border-navy-600 rounded-lg text-sm text-gray-400 hover:text-gray-200 hover:border-navy-500"
        >
          <Plus className="w-4 h-4" /> Add Rule
        </button>

        {/* Validation Summary */}
        <div className="p-3 bg-navy-800/50 border border-navy-700 rounded-lg space-y-1">
          <div className="flex items-center justify-between text-sm">
            <span className="text-gray-400">Validation</span>
            <span className={errors.length === 0 ? "text-green-400" : "text-red-400"}>
              {errors.length === 0 ? "✅ Valid" : `${errors.length} issue${errors.length > 1 ? "s" : ""}`}
            </span>
          </div>
          {errors.map((err, i) => (
            <div key={i} className="flex items-center gap-1 text-xs text-red-400">
              <AlertTriangle className="w-3 h-3" /> {err}
            </div>
          ))}
        </div>

        {/* Save / Back */}
        <div className="flex gap-2">
          <button onClick={onBack} className="flex-1 px-4 py-2 bg-navy-800 text-gray-300 rounded-lg hover:bg-navy-700">
            Back
          </button>
          <button
            onClick={() => onSave(rules)}
            disabled={errors.length > 0}
            className="flex-1 px-4 py-2 bg-gold-500 text-navy-900 rounded-lg hover:bg-gold-400 font-medium disabled:opacity-50"
          >
            Save Rules
          </button>
        </div>
      </div>

      {/* Center: Rule Editor */}
      <div className="flex-1 overflow-y-auto space-y-6">
        {selectedRule && (
          <>
            {/* Rule Header */}
            <div className="flex items-center gap-4">
              <input
                type="text"
                value={selectedRule.name}
                onChange={(e) => updateRule(selectedRuleIdx, { name: e.target.value })}
                className="text-lg font-semibold bg-transparent text-gray-100 border-b border-navy-600 focus:border-gold-500 outline-none pb-1"
              />
              <span className="text-sm text-gray-500">Priority:</span>
              <input
                type="number"
                value={selectedRule.priority}
                onChange={(e) => updateRule(selectedRuleIdx, { priority: parseInt(e.target.value) || 1 })}
                className="w-16 px-2 py-1 bg-navy-800 border border-navy-600 rounded text-gray-100 text-sm text-center"
                min={1}
              />
            </div>

            {/* Conditions */}
            <div className="p-4 bg-navy-800/30 border border-navy-700 rounded-xl">
              <h3 className="text-sm font-medium text-gray-300 mb-3">IF</h3>
              <ConditionGroupEditor
                group={selectedRule.condition}
                depth={0}
                fields={AVAILABLE_FIELDS}
                onUpdate={(updates) => updateRule(selectedRuleIdx, { condition: updates as ConditionGroup })}
                onAddCondition={addCondition}
                onAddGroup={addGroup}
                onUpdateCondition={updateConditionInGroup}
                onRemoveCondition={removeCondition}
              />
            </div>

            {/* THEN Actions */}
            <div className="p-4 bg-navy-800/30 border border-navy-700 rounded-xl">
              <h3 className="text-sm font-medium text-gray-300 mb-3">THEN</h3>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs text-gray-500 mb-1">Assign to Role</label>
                  <select
                    value={selectedRule.assignee_role}
                    onChange={(e) => updateRule(selectedRuleIdx, { assignee_role: e.target.value })}
                    className="w-full px-3 py-2 bg-navy-800 border border-navy-600 rounded-lg text-gray-100"
                  >
                    <option value="">Select role...</option>
                    <option value="legal_reviewer">Legal Reviewer</option>
                    <option value="legal_manager">Legal Manager</option>
                    <option value="legal_director">Legal Director</option>
                    <option value="vp_legal">VP Legal</option>
                    <option value="senior_counsel">Senior Counsel</option>
                    <option value="procurement">Procurement</option>
                    <option value="compliance">Compliance</option>
                    <option value="security">Security</option>
                    <option value="finance">Finance</option>
                    <option value="executive">Executive</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs text-gray-500 mb-1">Approval Mode</label>
                  <select
                    value={selectedRule.approval_mode}
                    onChange={(e) => updateRule(selectedRuleIdx, { approval_mode: e.target.value })}
                    className="w-full px-3 py-2 bg-navy-800 border border-navy-600 rounded-lg text-gray-100"
                  >
                    {APPROVAL_MODES.map((m) => (
                      <option key={m} value={m}>{m.replace(/_/g, " ")}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-xs text-gray-500 mb-1">Resolution Strategy</label>
                  <select
                    value={selectedRule.resolution_strategy}
                    onChange={(e) => updateRule(selectedRuleIdx, { resolution_strategy: e.target.value })}
                    className="w-full px-3 py-2 bg-navy-800 border border-navy-600 rounded-lg text-gray-100"
                  >
                    {RESOLUTION_STRATEGIES.map((s) => (
                      <option key={s} value={s}>{s.replace(/_/g, " ")}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-xs text-gray-500 mb-1">SLA (hours)</label>
                  <input
                    type="number"
                    value={selectedRule.sla_hours}
                    onChange={(e) => updateRule(selectedRuleIdx, { sla_hours: parseInt(e.target.value) || 0 })}
                    className="w-full px-3 py-2 bg-navy-800 border border-navy-600 rounded-lg text-gray-100"
                    min={0}
                  />
                </div>
              </div>
            </div>

            {/* Assignment Preview */}
            {selectedRule.assignee_role && (
              <div className="p-4 bg-navy-800/30 border border-navy-700 rounded-xl">
                <h3 className="text-sm font-medium text-gray-300 mb-3">Assignment Preview</h3>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-gray-400">Matched Role</span>
                    <span className="text-gray-200 capitalize">{selectedRule.assignee_role.replace(/_/g, " ")}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-400">Resolution Strategy</span>
                    <span className="text-gray-200 capitalize">{selectedRule.resolution_strategy.replace(/_/g, " ")}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-400">Candidates</span>
                    <span className="text-gray-200">John Smith, Jane Doe, Alex Brown</span>
                  </div>
                  <div className="flex justify-between text-gold-400">
                    <span>Selected</span>
                    <span>Jane Doe (least loaded — 2 open tasks)</span>
                  </div>
                </div>
              </div>
            )}

            {/* Live Explanation */}
            <div className="p-4 bg-navy-800/30 border border-navy-700 rounded-xl">
              <h3 className="text-sm font-medium text-gray-300 mb-3">Explanation</h3>
              <div className="text-sm text-gray-400 space-y-1">
                <p>This rule applies when:</p>
                <ul className="list-disc list-inside space-y-0.5">
                  {explainGroup(selectedRule.condition, AVAILABLE_FIELDS).map((line, i) => (
                    <li key={i}>{line}</li>
                  ))}
                </ul>
              </div>
            </div>
          </>
        )}
      </div>

      {/* Right: Test Panel */}
      <div className="w-80 shrink-0 space-y-4 overflow-y-auto pr-2">
        <h3 className="text-sm font-medium text-gray-300">Test Rule</h3>

        <div className="space-y-3">
          {AVAILABLE_FIELDS.slice(0, 6).map((field) => (
            <div key={field.name}>
              <label className="block text-xs text-gray-500 mb-1">{field.label}</label>
              {field.type === "boolean" ? (
                <select
                  value={testValues[field.name] ?? ""}
                  onChange={(e) => setTestValues({ ...testValues, [field.name]: e.target.value })}
                  className="w-full px-3 py-2 bg-navy-800 border border-navy-600 rounded-lg text-gray-100 text-sm"
                >
                  <option value="">Select...</option>
                  <option value="true">True</option>
                  <option value="false">False</option>
                </select>
              ) : field.options ? (
                <select
                  value={testValues[field.name] ?? ""}
                  onChange={(e) => setTestValues({ ...testValues, [field.name]: e.target.value })}
                  className="w-full px-3 py-2 bg-navy-800 border border-navy-600 rounded-lg text-gray-100 text-sm"
                >
                  <option value="">Select...</option>
                  {field.options.map((o) => (
                    <option key={o} value={o}>{o}</option>
                  ))}
                </select>
              ) : (
                <input
                  type={field.type === "number" ? "number" : "text"}
                  value={testValues[field.name] ?? ""}
                  onChange={(e) => setTestValues({ ...testValues, [field.name]: e.target.value })}
                  placeholder={`Enter ${field.label.toLowerCase()}...`}
                  className="w-full px-3 py-2 bg-navy-800 border border-navy-600 rounded-lg text-gray-100 text-sm placeholder-gray-600"
                />
              )}
            </div>
          ))}
        </div>

        <button
          onClick={evaluateTest}
          className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-gold-500 text-navy-900 rounded-lg hover:bg-gold-400 font-medium"
        >
          <Play className="w-4 h-4" /> Evaluate
        </button>

        {testResult && (
          <div className={`p-4 rounded-lg border ${
            testResult.matched
              ? "bg-green-500/10 border-green-500/30"
              : "bg-navy-800/50 border-navy-700"
          }`}>
            <div className="flex items-center gap-2 mb-2">
              {testResult.matched
                ? <CheckCircle className="w-5 h-5 text-green-400" />
                : <AlertTriangle className="w-5 h-5 text-gray-400" />
              }
              <span className={testResult.matched ? "text-green-400 font-medium" : "text-gray-400"}>
                {testResult.matched ? "Rule matched" : "No match"}
              </span>
            </div>
            {testResult.matched && (
              <div className="text-sm text-gray-300 space-y-1">
                <p>Assigned: <span className="capitalize">{selectedRule?.assignee_role.replace(/_/g, " ")}</span></p>
                <p>Mode: <span className="capitalize">{selectedRule?.approval_mode.replace(/_/g, " ")}</span></p>
                <p>SLA: {selectedRule?.sla_hours} hours</p>
              </div>
            )}
          </div>
        )}

        {/* Generated JSON Logic (hidden in production, shown for debugging) */}
        {selectedRule && (
          <details className="text-xs text-gray-600">
            <summary className="cursor-pointer hover:text-gray-400">Generated JSON Logic</summary>
            <pre className="mt-1 p-2 bg-navy-900 rounded overflow-x-auto">
              {JSON.stringify(generateJsonLogic(selectedRule.condition), null, 2)}
            </pre>
          </details>
        )}
      </div>
    </div>
  );
}

// ── Condition Group Editor ─────────────────────────────────────────

function ConditionGroupEditor({
  group,
  depth,
  fields,
  onUpdate,
  onAddCondition,
  onAddGroup,
  onUpdateCondition,
  onRemoveCondition,
}: {
  group: ConditionGroup;
  depth: number;
  fields: FieldDef[];
  onUpdate: (updates: ConditionGroup) => void;
  onAddCondition: (groupId: string, combinator: "ALL" | "ANY") => void;
  onAddGroup: (parentId: string, combinator: "ALL" | "ANY") => void;
  onUpdateCondition: (groupId: string, condId: string, updates: Partial<Condition>) => void;
  onRemoveCondition: (groupId: string, condId: string) => void;
}) {
  return (
    <div className={`space-y-2 ${depth > 0 ? "ml-4 pl-4 border-l-2 border-navy-600" : ""}`}>
      {/* Combinator toggle */}
      {depth > 0 && (
        <div className="flex items-center gap-2 mb-2">
          <button
            onClick={() => onUpdate({ ...group, combinator: group.combinator === "ALL" ? "ANY" : "ALL" })}
            className={`text-xs px-2 py-0.5 rounded font-medium ${
              group.combinator === "ALL"
                ? "bg-blue-500/20 text-blue-300"
                : "bg-purple-500/20 text-purple-300"
            }`}
          >
            {group.combinator}
          </button>
          <span className="text-xs text-gray-600">conditions</span>
        </div>
      )}

      {group.conditions.map((item) => {
        if ("combinator" in item) {
          const subGroup = item as ConditionGroup;
          return (
            <ConditionGroupEditor
              key={subGroup.id}
              group={subGroup}
              depth={depth + 1}
              fields={fields}
              onUpdate={(updates) => {
                const newConditions = group.conditions.map((c) =>
                  "combinator" in c && (c as ConditionGroup).id === subGroup.id ? updates : c
                );
                onUpdate({ ...group, conditions: newConditions });
              }}
              onAddCondition={onAddCondition}
              onAddGroup={onAddGroup}
              onUpdateCondition={onUpdateCondition}
              onRemoveCondition={onRemoveCondition}
            />
          );
        }

        const cond = item as Condition;
        const fieldDef = fields.find((f) => f.name === cond.field);
        const getOps = () => {
          if (!fieldDef) return [];
          if (fieldDef.type === "number") return NUMERIC_OPS;
          if (fieldDef.type === "boolean") return BOOL_OPS;
          if (fieldDef.type === "list") return LIST_OPS;
          if (fieldDef.type === "date") return DATE_OPS;
          return TEXT_OPS;
        };

        return (
          <div key={cond.id} className="flex items-center gap-2">
            <GripVertical className="w-3.5 h-3.5 text-gray-600 shrink-0" />
            <select
              value={cond.field}
              onChange={(e) => onUpdateCondition(group.id, cond.id, { field: e.target.value, operator: "", value: "" })}
              className="flex-1 min-w-[140px] px-2 py-1.5 bg-navy-800 border border-navy-600 rounded text-gray-100 text-sm"
            >
              <option value="">Select field...</option>
              {fields.map((f) => (
                <option key={f.name} value={f.name}>{f.label}</option>
              ))}
            </select>
            {cond.field && (
              <select
                value={cond.operator}
                onChange={(e) => onUpdateCondition(group.id, cond.id, { operator: e.target.value, value: "" })}
                className="w-28 px-2 py-1.5 bg-navy-800 border border-navy-600 rounded text-gray-100 text-sm"
              >
                <option value="">Op...</option>
                {getOps().map((op) => (
                  <option key={op} value={op}>{op}</option>
                ))}
              </select>
            )}
            {cond.operator && fieldDef?.options && (cond.operator === "=" || cond.operator === "!=") && (
              <select
                value={cond.value}
                onChange={(e) => onUpdateCondition(group.id, cond.id, { value: e.target.value })}
                className="flex-1 px-2 py-1.5 bg-navy-800 border border-navy-600 rounded text-gray-100 text-sm"
              >
                <option value="">Select value...</option>
                {fieldDef.options.map((o) => (
                  <option key={o} value={o}>{o}</option>
                ))}
              </select>
            )}
            {cond.operator && !(fieldDef?.options && (cond.operator === "=" || cond.operator === "!=")) && (
              <input
                type={fieldDef?.type === "number" ? "number" : "text"}
                value={cond.value}
                onChange={(e) => onUpdateCondition(group.id, cond.id, { value: e.target.value })}
                placeholder="Value..."
                className="flex-1 px-2 py-1.5 bg-navy-800 border border-navy-600 rounded text-gray-100 text-sm placeholder-gray-600"
              />
            )}
            <button
              onClick={() => onRemoveCondition(group.id, cond.id)}
              className="p-1 text-gray-500 hover:text-red-400"
            >
              <Trash2 className="w-3.5 h-3.5" />
            </button>
          </div>
        );
      })}

      {/* Add buttons */}
      <div className="flex gap-2 pt-1">
        <button
          onClick={() => onAddCondition(group.id, group.combinator)}
          className="flex items-center gap-1 text-xs text-gray-500 hover:text-gray-300"
        >
          <Plus className="w-3 h-3" /> Add condition
        </button>
        <button
          onClick={() => onAddGroup(group.id, "ALL")}
          className="flex items-center gap-1 text-xs text-gray-500 hover:text-gray-300"
        >
          <Plus className="w-3 h-3" /> Add ALL group
        </button>
        <button
          onClick={() => onAddGroup(group.id, "ANY")}
          className="flex items-center gap-1 text-xs text-gray-500 hover:text-gray-300"
        >
          <Plus className="w-3 h-3" /> Add ANY group
        </button>
      </div>
    </div>
  );
}

// ── Minimal JSON Logic Evaluator ───────────────────────────────────

function evaluateJsonLogic(rule: Record<string, unknown>, context: Record<string, unknown>): unknown {
  if (!rule || typeof rule !== "object") return rule;
  const entries = Object.entries(rule);
  if (entries.length === 0) return true;
  const [op, args] = entries[0];

  const resolve = (v: unknown): unknown => {
    if (v && typeof v === "object" && "var" in v) {
      const path = (v as Record<string, string>).var;
      return path.split(".").reduce((acc: unknown, key: string) =>
        acc && typeof acc === "object" ? (acc as Record<string, unknown>)[key] : undefined, context);
    }
    if (v && typeof v === "object") return evaluateJsonLogic(v as Record<string, unknown>, context);
    return v;
  };

  const arr = Array.isArray(args) ? args : [args];

  switch (op) {
    case "==": return resolve(arr[0]) === resolve(arr[1]);
    case "!=": return resolve(arr[0]) !== resolve(arr[1]);
    case ">": return Number(resolve(arr[0])) > Number(resolve(arr[1]));
    case ">=": return Number(resolve(arr[0])) >= Number(resolve(arr[1]));
    case "<": return Number(resolve(arr[0])) < Number(resolve(arr[1]));
    case "<=": return Number(resolve(arr[0])) <= Number(resolve(arr[1]));
    case "and": return arr.every((a: unknown) => evaluateJsonLogic({ "and": [a] }, context));
    case "or": return arr.some((a: unknown) => evaluateJsonLogic({ "or": [a] }, context));
    case "!": return !resolve(arr[0]);
    case "in": {
      const val = resolve(arr[0]);
      const list = resolve(arr[1]);
      return Array.isArray(list) ? list.includes(val) : false;
    }
    default: {
      const a = resolve(arr[0]);
      const b = resolve(arr[1]);
      switch (op) {
        case "===": return a === b;
        case "!==": return a !== b;
        default: return true;
      }
    }
  }
}

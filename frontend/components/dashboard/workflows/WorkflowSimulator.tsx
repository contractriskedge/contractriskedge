"use client";

import React, { useState } from "react";
import {
  Play, Save, RotateCcw, FileText, CheckCircle, AlertTriangle,
  Clock, Users, Shield, ArrowRight, ChevronDown, ChevronRight,
  Search,
} from "lucide-react";

// ── Types ──────────────────────────────────────────────────────────

interface SimInput {
  risk_score: number;
  contract_value: number;
  country: string;
  contract_type: string;
  department: string;
  has_redlines: boolean;
  supplier_region: string;
  ai_findings: number;
}

interface RuleResult {
  rule_id: string;
  rule_name: string;
  matched: boolean;
  conditions: { label: string; result: boolean }[];
  assignee_role: string;
  approval_mode: string;
  sla_hours: number;
}

interface StageResult {
  name: string;
  stage_type: string;
  sla_hours: number;
  assigned_to: string;
  candidates: string[];
  selected_user: string;
  selection_reason: string;
  estimated_days: number;
  matched_rule?: string;
}

interface SimResult {
  workflow_name: string;
  rules: RuleResult[];
  stages: StageResult[];
  total_days: number;
  total_approvers: number;
  escalation_count: number;
}

const defaultInput: SimInput = {
  risk_score: 50,
  contract_value: 100000,
  country: "US",
  contract_type: "MSA",
  department: "Procurement",
  has_redlines: false,
  supplier_region: "AMER",
  ai_findings: 0,
};

const COUNTRIES = ["US", "UK", "DE", "FR", "IN", "CA", "AU", "JP", "BR", "SG"];
const CONTRACT_TYPES = ["MSA", "NDA", "SOW", "Amendment", "License", "DPA"];
const DEPARTMENTS = ["Engineering", "Procurement", "Legal", "Sales", "HR", "Finance", "Marketing"];
const REGIONS = ["AMER", "EMEA", "APAC", "LATAM"];

// ── Mock Simulator Engine ──────────────────────────────────────────

function simulate(input: SimInput): SimResult {
  const rules: RuleResult[] = [];

  // Rule 1: High Risk
  const r1Conditions = [
    { label: `Risk Score ${input.risk_score} > 80`, result: input.risk_score > 80 },
    { label: `Country is ${input.country}`, result: true },
  ];
  const r1Matched = r1Conditions.every((c) => c.result);
  rules.push({
    rule_id: "rule_1", rule_name: "High Risk Detection",
    matched: r1Matched, conditions: r1Conditions,
    assignee_role: "Senior Counsel", approval_mode: "all_required", sla_hours: 48,
  });

  // Rule 2: Medium Value
  const r2Conditions = [
    { label: `Contract Value $${(input.contract_value / 1000).toFixed(0)}K > $500K`, result: input.contract_value > 500000 },
    { label: `Department is ${input.department}`, result: true },
  ];
  const r2Matched = r2Conditions.every((c) => c.result) && !r1Matched;
  rules.push({
    rule_id: "rule_2", rule_name: "Medium Value Review",
    matched: r2Matched, conditions: r2Conditions,
    assignee_role: "Legal Reviewer", approval_mode: "any_one", sla_hours: 24,
  });

  // Rule 3: Low Risk Auto
  const r3Conditions = [
    { label: `Risk Score ${input.risk_score} < 30`, result: input.risk_score < 30 },
    { label: `Has Redlines: ${input.has_redlines ? "Yes" : "No"}`, result: !input.has_redlines },
  ];
  const r3Matched = r3Conditions.every((c) => c.result) && !r1Matched && !r2Matched;
  rules.push({
    rule_id: "rule_3", rule_name: "Low Risk Auto-Approve",
    matched: r3Matched, conditions: r3Conditions,
    assignee_role: "System", approval_mode: "auto", sla_hours: 2,
  });

  // Determine which rule matched
  const matchedRule = rules.find((r) => r.matched) ?? rules[rules.length - 1];

  // Build stages based on matched rule
  const stages: StageResult[] = [
    {
      name: "Intake", stage_type: "automatic", sla_hours: 0,
      assigned_to: "System", candidates: [], selected_user: "",
      selection_reason: "Automatic", estimated_days: 0,
    },
    {
      name: "AI Analysis", stage_type: "automatic", sla_hours: 0,
      assigned_to: "System", candidates: [], selected_user: "",
      selection_reason: "Automatic", estimated_days: 0,
    },
  ];

  if (matchedRule.rule_name === "Low Risk Auto-Approve") {
    stages.push({
      name: "Auto-Approval", stage_type: "automatic", sla_hours: 2,
      assigned_to: "System", candidates: [], selected_user: "",
      selection_reason: "Auto-approved (low risk)", estimated_days: 0.1,
      matched_rule: matchedRule.rule_name,
    });
  } else {
    stages.push({
      name: "Legal Review", stage_type: "approval",
      sla_hours: matchedRule.sla_hours,
      assigned_to: matchedRule.assignee_role,
      candidates: ["John Smith", "Jane Doe", "Alex Brown"],
      selected_user: "Jane Doe",
      selection_reason: `Least loaded (2 open tasks) via ${matchedRule.assignee_role}`,
      estimated_days: matchedRule.sla_hours / 8,
      matched_rule: matchedRule.rule_name,
    });

    if (input.contract_value > 1000000 || input.risk_score > 80) {
      stages.push({
        name: "Executive Approval", stage_type: "approval", sla_hours: 24,
        assigned_to: "VP Legal",
        candidates: ["Sarah Chen", "Mike Johnson"],
        selected_user: "Sarah Chen",
        selection_reason: "Hierarchy escalation (value > $1M)",
        estimated_days: 3,
        matched_rule: matchedRule.rule_name,
      });
    }
  }

  stages.push({
    name: "Finalize", stage_type: "automatic", sla_hours: 0,
    assigned_to: "System", candidates: [], selected_user: "",
    selection_reason: "Automatic", estimated_days: 0,
  });

  const totalDays = stages.reduce((sum, s) => sum + s.estimated_days, 0);
  const totalApprovers = stages.filter((s) => s.stage_type === "approval").length;
  const escalationCount = input.risk_score > 80 ? 1 : 0;

  return {
    workflow_name: matchedRule.rule_name === "High Risk Detection" ? "High Value Procurement" :
                   matchedRule.rule_name === "Low Risk Auto-Approve" ? "Low Risk NDA" :
                   "Standard Procurement",
    rules,
    stages,
    total_days: Math.round(totalDays * 10) / 10,
    total_approvers,
    escalation_count: escalationCount,
  };
}

// ── Saved Test Cases ───────────────────────────────────────────────

interface TestCase {
  name: string;
  input: SimInput;
}

const defaultTestCases: TestCase[] = [
  {
    name: "High Risk NDA",
    input: { risk_score: 92, contract_value: 50000, country: "DE", contract_type: "NDA", department: "Legal", has_redlines: true, supplier_region: "EMEA", ai_findings: 8 },
  },
  {
    name: "Low Value Procurement",
    input: { risk_score: 25, contract_value: 10000, country: "US", contract_type: "MSA", department: "Procurement", has_redlines: false, supplier_region: "AMER", ai_findings: 1 },
  },
  {
    name: "Enterprise MSA",
    input: { risk_score: 70, contract_value: 5000000, country: "UK", contract_type: "MSA", department: "Engineering", has_redlines: true, supplier_region: "EMEA", ai_findings: 5 },
  },
];

// ── Props ──────────────────────────────────────────────────────────

interface Props {
  onBack: () => void;
}

export function WorkflowSimulator({ onBack }: Props) {
  const [mode, setMode] = useState<"manual" | "contract">("manual");
  const [input, setInput] = useState<SimInput>(defaultInput);
  const [result, setResult] = useState<SimResult | null>(null);
  const [testCases] = useState<TestCase[]>(defaultTestCases);
  const [expandedRules, setExpandedRules] = useState<Set<string>>(new Set());
  const [contractSearch, setContractSearch] = useState("");

  const toggleRule = (id: string) => {
    const next = new Set(expandedRules);
    if (next.has(id)) next.delete(id); else next.add(id);
    setExpandedRules(next);
  };

  const runSimulation = () => {
    const res = simulate(input);
    setResult(res);
    // Expand all rules by default
    setExpandedRules(new Set(res.rules.map((r) => r.rule_id)));
  };

  const loadTestCase = (tc: TestCase) => {
    setInput(tc.input);
    setResult(null);
  };

  // ── Render ──────────────────────────────────────────────────────

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold text-gray-100">Workflow Simulator</h2>
          <p className="text-sm text-gray-400">Test how a contract would route through your workflows</p>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={onBack} className="px-4 py-2 bg-navy-800 text-gray-300 rounded-lg hover:bg-navy-700">
            Back
          </button>
          <button
            onClick={runSimulation}
            className="flex items-center gap-2 px-4 py-2 bg-gold-500 text-navy-900 rounded-lg hover:bg-gold-400 font-medium"
          >
            <Play className="w-4 h-4" /> Run Simulation
          </button>
        </div>
      </div>

      <div className="flex gap-6">
        {/* Left: Input Panel */}
        <div className="w-96 shrink-0 space-y-4">
          {/* Mode Toggle */}
          <div className="flex bg-navy-800 rounded-lg p-1">
            <button
              onClick={() => setMode("manual")}
              className={`flex-1 px-4 py-2 text-sm rounded-md ${mode === "manual" ? "bg-navy-700 text-gray-100" : "text-gray-400"}`}
            >
              Manual Entry
            </button>
            <button
              onClick={() => setMode("contract")}
              className={`flex-1 px-4 py-2 text-sm rounded-md ${mode === "contract" ? "bg-navy-700 text-gray-100" : "text-gray-400"}`}
            >
              From Contract
            </button>
          </div>

          {mode === "manual" ? (
            <div className="space-y-3">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs text-gray-500 mb-1">Risk Score</label>
                  <input type="number" value={input.risk_score}
                    onChange={(e) => setInput({ ...input, risk_score: parseInt(e.target.value) || 0 })}
                    className="w-full px-3 py-2 bg-navy-800 border border-navy-600 rounded-lg text-gray-100 text-sm" min={0} max={100} />
                </div>
                <div>
                  <label className="block text-xs text-gray-500 mb-1">Contract Value ($)</label>
                  <input type="number" value={input.contract_value}
                    onChange={(e) => setInput({ ...input, contract_value: parseInt(e.target.value) || 0 })}
                    className="w-full px-3 py-2 bg-navy-800 border border-navy-600 rounded-lg text-gray-100 text-sm" />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs text-gray-500 mb-1">Country</label>
                  <select value={input.country} onChange={(e) => setInput({ ...input, country: e.target.value })}
                    className="w-full px-3 py-2 bg-navy-800 border border-navy-600 rounded-lg text-gray-100 text-sm">
                    {COUNTRIES.map((c) => <option key={c} value={c}>{c}</option>)}
                  </select>
                </div>
                <div>
                  <label className="block text-xs text-gray-500 mb-1">Contract Type</label>
                  <select value={input.contract_type} onChange={(e) => setInput({ ...input, contract_type: e.target.value })}
                    className="w-full px-3 py-2 bg-navy-800 border border-navy-600 rounded-lg text-gray-100 text-sm">
                    {CONTRACT_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
                  </select>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs text-gray-500 mb-1">Department</label>
                  <select value={input.department} onChange={(e) => setInput({ ...input, department: e.target.value })}
                    className="w-full px-3 py-2 bg-navy-800 border border-navy-600 rounded-lg text-gray-100 text-sm">
                    {DEPARTMENTS.map((d) => <option key={d} value={d}>{d}</option>)}
                  </select>
                </div>
                <div>
                  <label className="block text-xs text-gray-500 mb-1">Supplier Region</label>
                  <select value={input.supplier_region} onChange={(e) => setInput({ ...input, supplier_region: e.target.value })}
                    className="w-full px-3 py-2 bg-navy-800 border border-navy-600 rounded-lg text-gray-100 text-sm">
                    {REGIONS.map((r) => <option key={r} value={r}>{r}</option>)}
                  </select>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <input type="checkbox" id="redlines" checked={input.has_redlines}
                  onChange={(e) => setInput({ ...input, has_redlines: e.target.checked })}
                  className="rounded border-navy-600 bg-navy-800" />
                <label htmlFor="redlines" className="text-sm text-gray-300">Has Redlines</label>
              </div>
              <div>
                <label className="block text-xs text-gray-500 mb-1">AI Findings Count</label>
                <input type="number" value={input.ai_findings}
                  onChange={(e) => setInput({ ...input, ai_findings: parseInt(e.target.value) || 0 })}
                  className="w-full px-3 py-2 bg-navy-800 border border-navy-600 rounded-lg text-gray-100 text-sm" min={0} />
              </div>
            </div>
          ) : (
            <div className="space-y-3">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
                <input type="text" placeholder="Search contracts..." value={contractSearch}
                  onChange={(e) => setContractSearch(e.target.value)}
                  className="w-full pl-10 pr-4 py-2 bg-navy-800 border border-navy-600 rounded-lg text-gray-100 text-sm placeholder-gray-600" />
              </div>
              <div className="space-y-2 max-h-64 overflow-y-auto">
                {["MSA-000123", "NDA-000456", "SOW-000789", "LIC-000321", "DPA-000654"].filter((c) => c.includes(contractSearch)).map((cid) => (
                  <button key={cid} onClick={() => {/* Load from API */}}
                    className="w-full flex items-center gap-3 p-3 bg-navy-800/50 border border-navy-700 rounded-lg hover:border-navy-600 text-left">
                    <FileText className="w-4 h-4 text-gold-400" />
                    <div>
                      <div className="text-sm text-gray-200">{cid}</div>
                      <div className="text-xs text-gray-500">Acme Corp · MSA · $1.2M</div>
                    </div>
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Saved Test Cases */}
          <div>
            <h4 className="text-sm font-medium text-gray-300 mb-2">Saved Test Cases</h4>
            <div className="space-y-1">
              {testCases.map((tc) => (
                <button key={tc.name} onClick={() => loadTestCase(tc)}
                  className="w-full flex items-center gap-2 px-3 py-2 bg-navy-800/50 border border-navy-700 rounded-lg hover:border-navy-600 text-left text-sm">
                  <Save className="w-3.5 h-3.5 text-gray-500" />
                  <span className="text-gray-300">{tc.name}</span>
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Right: Results */}
        <div className="flex-1 space-y-4 overflow-y-auto max-h-[calc(100vh-16rem)]">
          {!result ? (
            <div className="flex items-center justify-center h-64 text-gray-500">
              <div className="text-center">
                <Play className="w-12 h-12 mx-auto mb-3 text-gray-600" />
                <p>Enter contract details and run a simulation</p>
              </div>
            </div>
          ) : (
            <>
              {/* Summary Card */}
              <div className="p-4 bg-navy-800/30 border border-navy-700 rounded-xl">
                <div className="flex items-center gap-3 mb-3">
                  <CheckCircle className="w-5 h-5 text-green-400" />
                  <span className="text-lg font-medium text-gray-100">Matched: {result.workflow_name}</span>
                </div>
                <div className="grid grid-cols-4 gap-4">
                  <SummaryStat label="Approvers" value={String(result.total_approvers)} />
                  <SummaryStat label="Est. Duration" value={`${result.total_days} days`} />
                  <SummaryStat label="Escalations" value={String(result.escalation_count)} />
                  <SummaryStat label="Stages" value={String(result.stages.length)} />
                </div>
              </div>

              {/* Rule Evaluation */}
              <div className="p-4 bg-navy-800/30 border border-navy-700 rounded-xl">
                <h3 className="text-sm font-medium text-gray-300 mb-3">Rule Evaluation</h3>
                <div className="space-y-2">
                  {result.rules.map((rule) => (
                    <div key={rule.rule_id} className="border border-navy-700 rounded-lg overflow-hidden">
                      <button
                        onClick={() => toggleRule(rule.rule_id)}
                        className="w-full flex items-center justify-between p-3 hover:bg-navy-700/50 text-left"
                      >
                        <div className="flex items-center gap-2">
                          {rule.matched
                            ? <CheckCircle className="w-4 h-4 text-green-400" />
                            : <AlertTriangle className="w-4 h-4 text-gray-500" />
                          }
                          <span className={`text-sm font-medium ${rule.matched ? "text-green-400" : "text-gray-400"}`}>
                            {rule.rule_name}
                          </span>
                        </div>
                        <div className="flex items-center gap-2">
                          <span className="text-xs text-gray-500">
                            {rule.conditions.filter((c) => c.result).length}/{rule.conditions.length} matched
                          </span>
                          {expandedRules.has(rule.rule_id)
                            ? <ChevronDown className="w-4 h-4 text-gray-500" />
                            : <ChevronRight className="w-4 h-4 text-gray-500" />
                          }
                        </div>
                      </button>
                      {expandedRules.has(rule.rule_id) && (
                        <div className="px-3 pb-3 space-y-1">
                          {rule.conditions.map((cond, i) => (
                            <div key={i} className="flex items-center gap-2 text-sm ml-6">
                              {cond.result
                                ? <CheckCircle className="w-3.5 h-3.5 text-green-400 shrink-0" />
                                : <AlertTriangle className="w-3.5 h-3.5 text-red-400 shrink-0" />
                              }
                              <span className={cond.result ? "text-gray-300" : "text-gray-500"}>{cond.label}</span>
                            </div>
                          ))}
                          {rule.matched && (
                            <div className="ml-6 mt-2 p-2 bg-navy-800 rounded text-xs text-gray-400 space-y-1">
                              <div>→ Assign: <span className="text-gray-200">{rule.assignee_role}</span></div>
                              <div>→ Mode: <span className="text-gray-200 capitalize">{rule.approval_mode.replace(/_/g, " ")}</span></div>
                              <div>→ SLA: <span className="text-gray-200">{rule.sla_hours}h</span></div>
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>

              {/* Timeline */}
              <div className="p-4 bg-navy-800/30 border border-navy-700 rounded-xl">
                <h3 className="text-sm font-medium text-gray-300 mb-3">Execution Timeline</h3>
                <div className="space-y-0">
                  {result.stages.map((stage, i) => (
                    <React.Fragment key={i}>
                      <div className="flex items-start gap-3 p-2">
                        <div className="flex flex-col items-center">
                          <div className={`w-3 h-3 rounded-full ${
                            stage.stage_type === "automatic" ? "bg-blue-400" : "bg-gold-400"
                          }`} />
                          {i < result.stages.length - 1 && <div className="w-0.5 h-8 bg-navy-600" />}
                        </div>
                        <div className="flex-1">
                          <div className="flex items-center justify-between">
                            <span className="text-sm font-medium text-gray-200">{stage.name}</span>
                            <span className="text-xs text-gray-500">
                              {stage.estimated_days > 0 ? `${stage.estimated_days} days` : "Instant"}
                            </span>
                          </div>
                          {stage.assigned_to && (
                            <div className="flex items-center gap-1 text-xs text-gray-400 mt-0.5">
                              <Users className="w-3 h-3" />
                              {stage.assigned_to}
                              {stage.selected_user && <span> → {stage.selected_user}</span>}
                            </div>
                          )}
                          {stage.selection_reason && (
                            <div className="text-xs text-gray-500 mt-0.5">{stage.selection_reason}</div>
                          )}
                        </div>
                      </div>
                    </React.Fragment>
                  ))}
                </div>
              </div>

              {/* Assignment Details */}
              {result.stages.filter((s) => s.candidates.length > 0).length > 0 && (
                <div className="p-4 bg-navy-800/30 border border-navy-700 rounded-xl">
                  <h3 className="text-sm font-medium text-gray-300 mb-3">Assignment Details</h3>
                  {result.stages.filter((s) => s.candidates.length > 0).map((stage, i) => (
                    <div key={i} className="mb-3 last:mb-0 p-3 bg-navy-800 rounded-lg">
                      <div className="text-sm text-gray-200 mb-2">{stage.name}</div>
                      <div className="space-y-1 text-xs text-gray-400">
                        <div className="flex justify-between">
                          <span>Matched Role</span>
                          <span className="text-gray-200">{stage.assigned_to}</span>
                        </div>
                        <div className="flex justify-between">
                          <span>Candidates</span>
                          <span className="text-gray-200">{stage.candidates.join(", ")}</span>
                        </div>
                        <div className="flex justify-between text-gold-400">
                          <span>Selected</span>
                          <span>{stage.selected_user}</span>
                        </div>
                        <div className="flex justify-between">
                          <span>Reason</span>
                          <span className="text-gray-200 text-right max-w-[200px]">{stage.selection_reason}</span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {/* Explanation Tree */}
              <div className="p-4 bg-navy-800/30 border border-navy-700 rounded-xl">
                <h3 className="text-sm font-medium text-gray-300 mb-3">Explanation</h3>
                <div className="text-sm text-gray-400 space-y-2">
                  <div className="flex items-center gap-2">
                    <CheckCircle className="w-4 h-4 text-green-400" />
                    <span>Workflow: <strong className="text-gray-200">{result.workflow_name}</strong></span>
                  </div>
                  {result.rules.filter((r) => r.matched).map((rule) => (
                    <div key={rule.rule_id} className="ml-6 space-y-1">
                      <div className="flex items-center gap-2">
                        <ArrowRight className="w-3.5 h-3.5 text-gold-400" />
                        <span className="text-gold-400">{rule.rule_name}</span>
                      </div>
                      {rule.conditions.filter((c) => c.result).map((cond, i) => (
                        <div key={i} className="ml-6 flex items-center gap-2 text-xs">
                          <CheckCircle className="w-3 h-3 text-green-400" />
                          <span>{cond.label}</span>
                        </div>
                      ))}
                      <div className="ml-6 flex items-center gap-2 text-xs text-gray-500">
                        <Users className="w-3 h-3" />
                        Assigned: {rule.assignee_role} · {rule.approval_mode.replace(/_/g, " ")}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

function SummaryStat({ label, value }: { label: string; value: string }) {
  return (
    <div className="text-center">
      <div className="text-lg font-bold text-gray-100">{value}</div>
      <div className="text-xs text-gray-500">{label}</div>
    </div>
  );
}

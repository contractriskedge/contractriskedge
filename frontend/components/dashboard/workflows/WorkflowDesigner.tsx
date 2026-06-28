"use client";

import React, { useState, useCallback } from "react";
import {
  ArrowUp, ArrowDown, Plus, Trash2, GripVertical,
  AlertTriangle, CheckCircle, Clock, Users, Shield,
  Bell, Webhook, Zap, ChevronRight, Settings,
} from "lucide-react";
import type { StageDefinition } from "@/services/api/workflowAdmin";

// ── Types ──────────────────────────────────────────────────────────

interface StageConfig {
  name: string;
  stage_type: "start" | "end" | "approval" | "review" | "automatic" | "condition" | "notification" | "escalation";
  sla_hours: number;
  calendar_id: string;
  assignee_role: string;
  assignee_user: string;
  resolution_strategy: string;
  approval_mode: string;
  min_approvals: number;
  transitions: string[];
  requires_approval: boolean;
  has_escalation: boolean;
  escalation_after_hours: number;
  escalation_role: string;
  notify_on_assignment: boolean;
  notify_on_completion: boolean;
}

interface DesignerState {
  stages: StageConfig[];
  history: StageConfig[][];
  future: StageConfig[][];
  selectedIndex: number | null;
}

const defaultStage = (type: StageConfig["stage_type"] = "review"): StageConfig => ({
  name: "",
  stage_type: type,
  sla_hours: 24,
  calendar_id: "24x7",
  assignee_role: "",
  assignee_user: "",
  resolution_strategy: "role",
  approval_mode: "any_one",
  min_approvals: 1,
  transitions: [],
  requires_approval: type === "approval",
  has_escalation: false,
  escalation_after_hours: 24,
  escalation_role: "",
  notify_on_assignment: false,
  notify_on_completion: false,
});

const stageTypeOptions: { value: StageConfig["stage_type"]; label: string; icon: React.ReactNode }[] = [
  { value: "start", label: "Start", icon: <ChevronRight className="w-4 h-4" /> },
  { value: "approval", label: "Approval", icon: <Shield className="w-4 h-4" /> },
  { value: "review", label: "Review", icon: <Users className="w-4 h-4" /> },
  { value: "automatic", label: "Automatic", icon: <Zap className="w-4 h-4" /> },
  { value: "condition", label: "Condition", icon: <Bell className="w-4 h-4" /> },
  { value: "notification", label: "Notification", icon: <Bell className="w-4 h-4" /> },
  { value: "escalation", label: "Escalation", icon: <AlertTriangle className="w-4 h-4" /> },
  { value: "end", label: "End", icon: <CheckCircle className="w-4 h-4" /> },
];

const resolutionStrategies = [
  "role", "specific_user", "manager", "round_robin",
  "least_loaded", "random", "hierarchy", "business_owner",
  "contract_owner", "department_head", "legal_director", "custom_resolver",
];

const approvalModes = [
  "any_one", "all_required", "majority", "minimum_count",
  "weighted_voting", "sequential", "parallel",
];

// ── Props ──────────────────────────────────────────────────────────

interface Props {
  initialStages?: StageDefinition[];
  onSave: (stages: StageConfig[]) => void;
  onBack: () => void;
}

export function WorkflowDesigner({ initialStages, onSave, onBack }: Props) {
  const [state, setState] = useState<DesignerState>(() => ({
    stages: initialStages?.length
      ? initialStages.map((s) => ({
          name: s.name,
          stage_type: s.stage_type as StageConfig["stage_type"],
          sla_hours: s.sla_hours ?? 24,
          calendar_id: s.calendar_id ?? "24x7",
          assignee_role: s.assignee_role ?? "",
          assignee_user: s.assignee_user ?? "",
          resolution_strategy: s.resolution_strategy ?? "role",
          approval_mode: s.approval_mode ?? "any_one",
          min_approvals: s.min_approvals ?? 1,
          transitions: s.transitions ?? [],
          requires_approval: s.requires_approval ?? false,
          has_escalation: false,
          escalation_after_hours: 24,
          escalation_role: "",
          notify_on_assignment: false,
          notify_on_completion: false,
        }))
      : [
          { ...defaultStage("start"), name: "Intake" },
          { ...defaultStage("review"), name: "Review" },
          { ...defaultStage("approval"), name: "Approval" },
          { ...defaultStage("end"), name: "Complete" },
        ],
    history: [],
    future: [],
    selectedIndex: null,
  }));

  const selectedStage = state.selectedIndex !== null ? state.stages[state.selectedIndex] : null;

  // ── Undo/Redo ──────────────────────────────────────────────────

  const pushHistory = useCallback((newStages: StageConfig[]) => {
    setState((prev) => ({
      ...prev,
      stages: newStages,
      history: [...prev.history.slice(-50), prev.stages],
      future: [],
    }));
  }, []);

  const undo = useCallback(() => {
    setState((prev) => {
      if (prev.history.length === 0) return prev;
      const previous = prev.history[prev.history.length - 1];
      return {
        ...prev,
        stages: previous,
        history: prev.history.slice(0, -1),
        future: [prev.stages, ...prev.future],
      };
    });
  }, []);

  const redo = useCallback(() => {
    setState((prev) => {
      if (prev.future.length === 0) return prev;
      const next = prev.future[0];
      return {
        ...prev,
        stages: next,
        history: [...prev.history, prev.stages],
        future: prev.future.slice(1),
      };
    });
  }, []);

  // ── Stage Operations ───────────────────────────────────────────

  const addStage = useCallback((type: StageConfig["stage_type"]) => {
    const stage = { ...defaultStage(type), name: `New ${type}` };
    pushHistory([...state.stages.slice(0, -1), stage, state.stages[state.stages.length - 1]]);
  }, [state.stages, pushHistory]);

  const deleteStage = useCallback((index: number) => {
    if (state.stages.length <= 2) return; // must keep start + end
    const newStages = state.stages.filter((_, i) => i !== index);
    pushHistory(newStages);
    setState((prev) => ({ ...prev, selectedIndex: null }));
  }, [state.stages, pushHistory]);

  const moveStage = useCallback((index: number, direction: "up" | "down") => {
    const newIndex = direction === "up" ? index - 1 : index + 1;
    if (newIndex < 0 || newIndex >= state.stages.length) return;
    // Don't move start (index 0) or end (last)
    if (index === 0 || index === state.stages.length - 1) return;
    if (newIndex === 0 || newIndex === state.stages.length - 1) return;
    const newStages = [...state.stages];
    [newStages[index], newStages[newIndex]] = [newStages[newIndex], newStages[index]];
    pushHistory(newStages);
    setState((prev) => ({ ...prev, selectedIndex: newIndex }));
  }, [state.stages, pushHistory]);

  const updateStage = useCallback((index: number, updates: Partial<StageConfig>) => {
    const newStages = state.stages.map((s, i) => i === index ? { ...s, ...updates } : s);
    pushHistory(newStages);
  }, [state.stages, pushHistory]);

  // ── Validation ─────────────────────────────────────────────────

  const errors: string[] = [];
  const warnings: string[] = [];

  if (state.stages.length < 2) errors.push("Workflow must have at least a start and end stage");
  if (state.stages[0]?.stage_type !== "start") errors.push("First stage must be a Start stage");
  if (state.stages[state.stages.length - 1]?.stage_type !== "end") errors.push("Last stage must be an End stage");

  const names = state.stages.map((s) => s.name.toLowerCase());
  const dupes = names.filter((n, i) => n && names.indexOf(n) !== i);
  if (dupes.length > 0) errors.push(`Duplicate stage names: ${[...new Set(dupes)].join(", ")}`);

  state.stages.forEach((s, i) => {
    if ((s.stage_type === "approval" || s.stage_type === "review") && !s.assignee_role && !s.assignee_user) {
      warnings.push(`"${s.name || `Stage ${i + 1}`}" has no assignee`);
    }
    if ((s.stage_type === "approval" || s.stage_type === "review") && s.sla_hours <= 0) {
      warnings.push(`"${s.name || `Stage ${i + 1}`}" has no SLA`);
    }
  });

  // ── Keyboard shortcuts ─────────────────────────────────────────

  React.useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "z") {
        if (e.shiftKey) redo();
        else undo();
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [undo, redo]);

  return (
    <div className="flex gap-6 h-[calc(100vh-12rem)]">
      {/* Left: Stage List */}
      <div className="w-96 shrink-0 space-y-4 overflow-y-auto pr-2">
        {/* Toolbar */}
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-100">Workflow Stages</h2>
          <div className="flex items-center gap-1">
            <div
              onClick={undo}
              className={`px-2 py-1 text-xs rounded cursor-pointer ${state.history.length === 0 ? "bg-navy-900 text-gray-600 cursor-not-allowed" : "bg-navy-800 text-gray-300 hover:bg-navy-700"}`}
            >
              Undo
            </div>
            <div
              onClick={redo}
              className={`px-2 py-1 text-xs rounded cursor-pointer ${state.future.length === 0 ? "bg-navy-900 text-gray-600 cursor-not-allowed" : "bg-navy-800 text-gray-300 hover:bg-navy-700"}`}
            >
              Redo
            </div>
          </div>
        </div>

        {/* Add Stage Dropdown */}
        <div className="flex gap-2">
          <select
            value=""
            onChange={(e) => { if (e.target.value) addStage(e.target.value as StageConfig["stage_type"]); }}
            className="flex-1 px-3 py-2 bg-navy-800 border border-navy-600 rounded-lg text-gray-300 text-sm"
          >
            <option value="">+ Add Stage</option>
            {stageTypeOptions.filter((o) => o.value !== "start" && o.value !== "end").map((o) => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>
        </div>

        {/* Stage List */}
        <div className="space-y-1">
          {state.stages.map((stage, i) => (
            <div key={i}>
              <button
                onClick={() => setState((prev) => ({ ...prev, selectedIndex: i }))}
                className={`w-full flex items-center gap-3 p-3 rounded-lg border transition-colors text-left ${
                  state.selectedIndex === i
                    ? "bg-navy-700 border-gold-500/50"
                    : "bg-navy-800/50 border-navy-700 hover:border-navy-600"
                }`}
              >
                <GripVertical className="w-4 h-4 text-gray-600 shrink-0" />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className={`w-2 h-2 rounded-full ${
                      stage.stage_type === "start" ? "bg-green-400" :
                      stage.stage_type === "end" ? "bg-red-400" :
                      stage.stage_type === "approval" ? "bg-gold-400" :
                      "bg-blue-400"
                    }`} />
                    <span className="text-sm font-medium text-gray-200 truncate">
                      {stage.name || `Stage ${i + 1}`}
                    </span>
                    <span className="text-xs text-gray-500 capitalize">{stage.stage_type}</span>
                  </div>
                  {stage.sla_hours > 0 && (
                    <div className="flex items-center gap-1 mt-0.5 text-xs text-gray-500">
                      <Clock className="w-3 h-3" />
                      {stage.sla_hours}h SLA
                      {stage.assignee_role && ` · ${stage.assignee_role}`}
                    </div>
                  )}
                </div>
                <div className="flex items-center gap-0.5">
                  <div onClick={(e) => { e.stopPropagation(); moveStage(i, "up"); }}
                    className={`p-1 cursor-pointer ${i <= 1 ? "text-gray-700 cursor-not-allowed" : "text-gray-500 hover:text-gray-200"}`}>
                    <ArrowUp className="w-3.5 h-3.5" />
                  </div>
                  <div onClick={(e) => { e.stopPropagation(); moveStage(i, "down"); }}
                    className={`p-1 cursor-pointer ${i >= state.stages.length - 2 ? "text-gray-700 cursor-not-allowed" : "text-gray-500 hover:text-gray-200"}`}>
                    <ArrowDown className="w-3.5 h-3.5" />
                  </div>
                  <div onClick={(e) => { e.stopPropagation(); deleteStage(i); }}
                    className={`p-1 cursor-pointer ${state.stages.length <= 2 ? "text-gray-700 cursor-not-allowed" : "text-gray-500 hover:text-red-400"}`}>
                    <Trash2 className="w-3.5 h-3.5" />
                  </div>
                </div>
              </button>
              {/* Arrow between stages */}
              {i < state.stages.length - 1 && (
                <div className="flex justify-center py-0.5">
                  <div className="w-0.5 h-3 bg-navy-600" />
                </div>
              )}
            </div>
          ))}
        </div>

        {/* Live Validation Summary */}
        <div className="p-3 bg-navy-800/50 border border-navy-700 rounded-lg space-y-1">
          <div className="flex items-center justify-between text-sm">
            <span className="text-gray-400">Workflow Health</span>
            <span className={`font-medium ${errors.length === 0 ? "text-green-400" : "text-red-400"}`}>
              {errors.length === 0 ? "✅ Valid" : `${errors.length} error${errors.length > 1 ? "s" : ""}`}
            </span>
          </div>
          <div className="text-xs text-gray-500">
            {state.stages.length} stages · {warnings.length} warning{warnings.length !== 1 ? "s" : ""}
          </div>
          {errors.map((err, i) => (
            <div key={i} className="flex items-center gap-1 text-xs text-red-400">
              <AlertTriangle className="w-3 h-3" /> {err}
            </div>
          ))}
          {warnings.map((warn, i) => (
            <div key={i} className="flex items-center gap-1 text-xs text-yellow-400">
              <AlertTriangle className="w-3 h-3" /> {warn}
            </div>
          ))}
        </div>

        {/* Save / Back */}
        <div className="flex gap-2">
          <button onClick={onBack} className="flex-1 px-4 py-2 bg-navy-800 text-gray-300 rounded-lg hover:bg-navy-700">
            Back
          </button>
          <button
            onClick={() => onSave(state.stages)}
            disabled={errors.length > 0}
            className="flex-1 px-4 py-2 bg-gold-500 text-navy-900 rounded-lg hover:bg-gold-400 font-medium disabled:opacity-50"
          >
            Save Stages
          </button>
        </div>
      </div>

      {/* Right: Configuration Panel */}
      <div className="flex-1 overflow-y-auto">
        {selectedStage ? (
          <StageConfigPanel
            stage={selectedStage}
            index={state.selectedIndex!}
            onUpdate={(updates) => updateStage(state.selectedIndex!, updates)}
          />
        ) : (
          <div className="flex items-center justify-center h-full text-gray-500">
            <div className="text-center">
              <Settings className="w-12 h-12 mx-auto mb-3 text-gray-600" />
              <p>Select a stage to configure</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// ── Stage Configuration Panel ──────────────────────────────────────

function StageConfigPanel({
  stage,
  index,
  onUpdate,
}: {
  stage: StageConfig;
  index: number;
  onUpdate: (updates: Partial<StageConfig>) => void;
}) {
  return (
    <div className="space-y-6">
      <h3 className="text-lg font-semibold text-gray-100">
        Stage {index + 1}: {stage.name || "Untitled"}
      </h3>

      {/* General */}
      <section>
        <h4 className="text-sm font-medium text-gray-300 mb-3">General</h4>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-xs text-gray-500 mb-1">Name</label>
            <input
              type="text"
              value={stage.name}
              onChange={(e) => onUpdate({ name: e.target.value })}
              className="w-full px-3 py-2 bg-navy-800 border border-navy-600 rounded-lg text-gray-100 focus:outline-none focus:ring-2 focus:ring-gold-500/50"
            />
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">Type</label>
            <select
              value={stage.stage_type}
              onChange={(e) => onUpdate({ stage_type: e.target.value as StageConfig["stage_type"] })}
              className="w-full px-3 py-2 bg-navy-800 border border-navy-600 rounded-lg text-gray-100 focus:outline-none focus:ring-2 focus:ring-gold-500/50"
              disabled={index === 0 || index === (() => false)()}
            >
              {stageTypeOptions.map((o) => (
                <option key={o.value} value={o.value}>{o.label}</option>
              ))}
            </select>
          </div>
        </div>
      </section>

      {/* SLA */}
      <section>
        <h4 className="text-sm font-medium text-gray-300 mb-3">SLA</h4>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-xs text-gray-500 mb-1">Duration (hours)</label>
            <input
              type="number"
              value={stage.sla_hours}
              onChange={(e) => onUpdate({ sla_hours: parseInt(e.target.value) || 0 })}
              min={0}
              className="w-full px-3 py-2 bg-navy-800 border border-navy-600 rounded-lg text-gray-100 focus:outline-none focus:ring-2 focus:ring-gold-500/50"
            />
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">Business Calendar</label>
            <select
              value={stage.calendar_id}
              onChange={(e) => onUpdate({ calendar_id: e.target.value })}
              className="w-full px-3 py-2 bg-navy-800 border border-navy-600 rounded-lg text-gray-100 focus:outline-none focus:ring-2 focus:ring-gold-500/50"
            >
              <option value="24x7">24x7 (Default)</option>
              <option value="us_business">US Business</option>
              <option value="uk_business">UK Business</option>
              <option value="de_business">Germany Business</option>
            </select>
          </div>
        </div>
      </section>

      {/* Assignment */}
      {(stage.stage_type === "approval" || stage.stage_type === "review") && (
        <section>
          <h4 className="text-sm font-medium text-gray-300 mb-3">Assignment</h4>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs text-gray-500 mb-1">Assignee Role</label>
              <select
                value={stage.assignee_role}
                onChange={(e) => onUpdate({ assignee_role: e.target.value })}
                className="w-full px-3 py-2 bg-navy-800 border border-navy-600 rounded-lg text-gray-100 focus:outline-none focus:ring-2 focus:ring-gold-500/50"
              >
                <option value="">Select role...</option>
                <option value="legal_reviewer">Legal Reviewer</option>
                <option value="legal_manager">Legal Manager</option>
                <option value="legal_director">Legal Director</option>
                <option value="vp_legal">VP Legal</option>
                <option value="procurement">Procurement</option>
                <option value="compliance">Compliance</option>
                <option value="security">Security</option>
                <option value="finance">Finance</option>
                <option value="executive">Executive</option>
              </select>
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">Resolution Strategy</label>
              <select
                value={stage.resolution_strategy}
                onChange={(e) => onUpdate({ resolution_strategy: e.target.value })}
                className="w-full px-3 py-2 bg-navy-800 border border-navy-600 rounded-lg text-gray-100 focus:outline-none focus:ring-2 focus:ring-gold-500/50"
              >
                {resolutionStrategies.map((s) => (
                  <option key={s} value={s}>{s.replace(/_/g, " ")}</option>
                ))}
              </select>
            </div>
          </div>
        </section>
      )}

      {/* Approval Mode */}
      {stage.stage_type === "approval" && (
        <section>
          <h4 className="text-sm font-medium text-gray-300 mb-3">Approval Mode</h4>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs text-gray-500 mb-1">Mode</label>
              <select
                value={stage.approval_mode}
                onChange={(e) => onUpdate({ approval_mode: e.target.value })}
                className="w-full px-3 py-2 bg-navy-800 border border-navy-600 rounded-lg text-gray-100 focus:outline-none focus:ring-2 focus:ring-gold-500/50"
              >
                {approvalModes.map((m) => (
                  <option key={m} value={m}>{m.replace(/_/g, " ")}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">Min Approvals</label>
              <input
                type="number"
                value={stage.min_approvals}
                onChange={(e) => onUpdate({ min_approvals: parseInt(e.target.value) || 1 })}
                min={1}
                className="w-full px-3 py-2 bg-navy-800 border border-navy-600 rounded-lg text-gray-100 focus:outline-none focus:ring-2 focus:ring-gold-500/50"
              />
            </div>
          </div>
        </section>
      )}

      {/* Escalation */}
      <section>
        <h4 className="text-sm font-medium text-gray-300 mb-3">Escalation</h4>
        <div className="space-y-3">
          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={stage.has_escalation}
              onChange={(e) => onUpdate({ has_escalation: e.target.checked })}
              className="rounded border-navy-600 bg-navy-800"
            />
            <span className="text-sm text-gray-300">Enable escalation</span>
          </label>
          {stage.has_escalation && (
            <div className="grid grid-cols-2 gap-4 pl-6">
              <div>
                <label className="block text-xs text-gray-500 mb-1">After (hours)</label>
                <input
                  type="number"
                  value={stage.escalation_after_hours}
                  onChange={(e) => onUpdate({ escalation_after_hours: parseInt(e.target.value) || 0 })}
                  min={0}
                  className="w-full px-3 py-2 bg-navy-800 border border-navy-600 rounded-lg text-gray-100 focus:outline-none focus:ring-2 focus:ring-gold-500/50"
                />
              </div>
              <div>
                <label className="block text-xs text-gray-500 mb-1">Escalate to</label>
                <select
                  value={stage.escalation_role}
                  onChange={(e) => onUpdate({ escalation_role: e.target.value })}
                  className="w-full px-3 py-2 bg-navy-800 border border-navy-600 rounded-lg text-gray-100 focus:outline-none focus:ring-2 focus:ring-gold-500/50"
                >
                  <option value="">Select role...</option>
                  <option value="legal_manager">Legal Manager</option>
                  <option value="legal_director">Legal Director</option>
                  <option value="vp_legal">VP Legal</option>
                </select>
              </div>
            </div>
          )}
        </div>
      </section>

      {/* Notifications */}
      <section>
        <h4 className="text-sm font-medium text-gray-300 mb-3">Notifications</h4>
        <div className="space-y-2">
          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={stage.notify_on_assignment}
              onChange={(e) => onUpdate({ notify_on_assignment: e.target.checked })}
              className="rounded border-navy-600 bg-navy-800"
            />
            <span className="text-sm text-gray-300">Notify on assignment</span>
          </label>
          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={stage.notify_on_completion}
              onChange={(e) => onUpdate({ notify_on_completion: e.target.checked })}
              className="rounded border-navy-600 bg-navy-800"
            />
            <span className="text-sm text-gray-300">Notify on completion</span>
          </label>
        </div>
      </section>
    </div>
  );
}

"use client";

import React, { useState } from "react";
import {
  CheckCircle, AlertTriangle, ArrowLeft, Calendar,
  FileText, Shield, Clock, Users, Layers,
} from "lucide-react";

// ── Types ──────────────────────────────────────────────────────────

interface ValidationIssue {
  severity: "error" | "warning";
  code: string;
  message: string;
  suggestion: string;
}

interface ValidationResult {
  score: number;
  is_valid: boolean;
  errors: ValidationIssue[];
  warnings: ValidationIssue[];
}

interface ImpactResult {
  template_count: number;
  active_contract_count: number;
  future_contract_count: number;
  departments: string[];
  regions: string[];
}

interface VersionInfo {
  current_version: number;
  current_status: "draft" | "published";
  new_version: number;
}

// ── Mock Data ──────────────────────────────────────────────────────

const mockValidation: ValidationResult = {
  score: 96,
  is_valid: true,
  errors: [],
  warnings: [
    { severity: "warning", code: "missing_description", message: "No description provided for this version", suggestion: "Add a description to help other administrators understand what changed." },
    { severity: "warning", code: "no_escalation", message: "Stage 'Legal Review' has no escalation configured", suggestion: "Add escalation to prevent SLA breaches from going unnoticed." },
  ],
};

const mockImpact: ImpactResult = {
  template_count: 12,
  active_contract_count: 47,
  future_contract_count: 430,
  departments: ["Legal", "Procurement", "Engineering"],
  regions: ["AMER", "EMEA", "APAC"],
};

// ── Props ──────────────────────────────────────────────────────────

interface Props {
  packName: string;
  versionInfo: VersionInfo;
  onPublish: (data: { effective_date?: string; change_summary: string }) => void;
  onRollback: (targetVersion: number) => void;
  onBack: () => void;
}

export function PublishingFlow({ packName, versionInfo, onPublish, onRollback, onBack }: Props) {
  const [step, setStep] = useState<"review" | "confirm" | "done">("review");
  const [effectiveDate, setEffectiveDate] = useState("");
  const [changeSummary, setChangeSummary] = useState("");
  const [rollbackTarget, setRollbackTarget] = useState<number>(versionInfo.current_version - 1);
  const [showRollback, setShowRollback] = useState(false);

  const validation = mockValidation;
  const impact = mockImpact;

  const handlePublish = () => {
    onPublish({
      effective_date: effectiveDate || undefined,
      change_summary: changeSummary,
    });
    setStep("done");
  };

  const handleRollback = () => {
    onRollback(rollbackTarget);
    setStep("done");
  };

  // ── Render ──────────────────────────────────────────────────────

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <button onClick={onBack} className="flex items-center gap-1 text-sm text-gray-400 hover:text-gray-200 mb-2">
            <ArrowLeft className="w-4 h-4" /> Back
          </button>
          <h2 className="text-xl font-semibold text-gray-100">
            {showRollback ? "Rollback Workflow" : `Publish ${packName}`}
          </h2>
          <p className="text-sm text-gray-400">
            {showRollback
              ? `Current: v${versionInfo.current_version} · Rollback to: v${rollbackTarget}`
              : `Current: v${versionInfo.current_version} · New: v${versionInfo.new_version}`
            }
          </p>
        </div>
      </div>

      {step === "done" ? (
        /* ── Success ──────────────────────────────────────────── */
        <div className="text-center py-16">
          <CheckCircle className="w-16 h-16 text-green-400 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-gray-100 mb-2">
            {showRollback ? "Rollback Complete" : "Published Successfully"}
          </h3>
          <p className="text-gray-400 mb-6">
            {showRollback
              ? `v${rollbackTarget} is now active. A new version (v${versionInfo.new_version}) has been created.`
              : `v${versionInfo.new_version} is now live${effectiveDate ? ` (effective ${effectiveDate})` : ""}.`
            }
          </p>
          <button onClick={onBack} className="px-6 py-2 bg-gold-500 text-navy-900 rounded-lg hover:bg-gold-400 font-medium">
            Return to Workflow Packs
          </button>
        </div>
      ) : showRollback ? (
        /* ── Rollback ─────────────────────────────────────────── */
        <div className="space-y-6">
          <div className="p-4 bg-navy-800/30 border border-navy-700 rounded-xl">
            <h3 className="text-sm font-medium text-gray-300 mb-3">Rollback to Previous Version</h3>
            <p className="text-sm text-gray-400 mb-4">
              This will create a new version (v{versionInfo.new_version}) with the same configuration as v{rollbackTarget}.
              Existing workflow instances will NOT be affected — they remain on their pinned version.
            </p>
            <div className="flex items-center gap-3">
              <label className="text-sm text-gray-300">Rollback to:</label>
              <select
                value={rollbackTarget}
                onChange={(e) => setRollbackTarget(parseInt(e.target.value))}
                className="px-3 py-2 bg-navy-800 border border-navy-600 rounded-lg text-gray-100"
              >
                {Array.from({ length: versionInfo.current_version - 1 }, (_, i) => i + 1).map((v) => (
                  <option key={v} value={v}>Version {v}</option>
                ))}
              </select>
            </div>
          </div>

          <div className="flex gap-3 justify-end">
            <button onClick={() => setShowRollback(false)} className="px-4 py-2 bg-navy-800 text-gray-300 rounded-lg hover:bg-navy-700">
              Cancel
            </button>
            <button onClick={handleRollback} className="px-4 py-2 bg-gold-500 text-navy-900 rounded-lg hover:bg-gold-400 font-medium">
              Rollback to v{rollbackTarget}
            </button>
          </div>
        </div>
      ) : (
        /* ── Publish Flow ─────────────────────────────────────── */
        <>
          {/* Step 1: Validation */}
          <div className="p-4 bg-navy-800/30 border border-navy-700 rounded-xl">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-medium text-gray-300">Validation</h3>
              <div className="flex items-center gap-2">
                <span className={`text-lg font-bold ${validation.score >= 90 ? "text-green-400" : "text-yellow-400"}`}>
                  {validation.score}/100
                </span>
                {validation.is_valid
                  ? <CheckCircle className="w-5 h-5 text-green-400" />
                  : <AlertTriangle className="w-5 h-5 text-red-400" />
                }
              </div>
            </div>

            {validation.errors.length > 0 && (
              <div className="space-y-2 mb-3">
                {validation.errors.map((err, i) => (
                  <div key={i} className="flex items-start gap-2 text-sm">
                    <AlertTriangle className="w-4 h-4 text-red-400 mt-0.5 shrink-0" />
                    <div>
                      <span className="text-red-400">{err.message}</span>
                      <p className="text-xs text-gray-500 mt-0.5">{err.suggestion}</p>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {validation.warnings.length > 0 && (
              <div className="space-y-2">
                {validation.warnings.map((warn, i) => (
                  <div key={i} className="flex items-start gap-2 text-sm">
                    <AlertTriangle className="w-4 h-4 text-yellow-400 mt-0.5 shrink-0" />
                    <div>
                      <span className="text-yellow-400">{warn.message}</span>
                      <p className="text-xs text-gray-500 mt-0.5">{warn.suggestion}</p>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Step 2: Impact Analysis */}
          <div className="p-4 bg-navy-800/30 border border-navy-700 rounded-xl">
            <h3 className="text-sm font-medium text-gray-300 mb-3">Impact Analysis</h3>

            <div className="grid grid-cols-3 gap-4 mb-4">
              <ImpactCard icon={<FileText className="w-4 h-4" />} label="Templates" value={String(impact.template_count)} note="will use new version" />
              <ImpactCard icon={<Users className="w-4 h-4" />} label="Active Contracts" value={String(impact.active_contract_count)} note="pinned to current version" />
              <ImpactCard icon={<Layers className="w-4 h-4" />} label="Future Contracts" value={String(impact.future_contract_count)} note="will use new version" />
            </div>

            <div className="flex gap-4 text-sm text-gray-400">
              <div className="flex items-center gap-1">
                <Users className="w-3.5 h-3.5" />
                Departments: {impact.departments.join(", ")}
              </div>
              <div className="flex items-center gap-1">
                <Shield className="w-3.5 h-3.5" />
                Regions: {impact.regions.join(", ")}
              </div>
            </div>
          </div>

          {/* Step 3: Publishing Options */}
          <div className="p-4 bg-navy-800/30 border border-navy-700 rounded-xl space-y-4">
            <h3 className="text-sm font-medium text-gray-300">Publishing Options</h3>

            <div>
              <label className="block text-xs text-gray-500 mb-1">Effective Date (optional)</label>
              <div className="relative">
                <Calendar className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
                <input
                  type="date"
                  value={effectiveDate}
                  onChange={(e) => setEffectiveDate(e.target.value)}
                  className="w-full pl-10 pr-4 py-2 bg-navy-800 border border-navy-600 rounded-lg text-gray-100 text-sm"
                />
              </div>
              <p className="text-xs text-gray-500 mt-1">Leave blank to publish immediately</p>
            </div>

            <div>
              <label className="block text-xs text-gray-500 mb-1">Change Summary *</label>
              <textarea
                value={changeSummary}
                onChange={(e) => setChangeSummary(e.target.value)}
                placeholder="Describe what changed in this version..."
                rows={3}
                className="w-full px-3 py-2 bg-navy-800 border border-navy-600 rounded-lg text-gray-100 text-sm placeholder-gray-600 resize-none"
                required
              />
            </div>
          </div>

          {/* Actions */}
          <div className="flex items-center justify-between">
            <button
              onClick={() => setShowRollback(true)}
              className="text-sm text-gray-400 hover:text-gray-200"
            >
              Rollback to previous version
            </button>
            <div className="flex gap-3">
              <button onClick={onBack} className="px-4 py-2 bg-navy-800 text-gray-300 rounded-lg hover:bg-navy-700">
                Cancel
              </button>
              <button
                onClick={handlePublish}
                disabled={!changeSummary.trim()}
                className="flex items-center gap-2 px-6 py-2 bg-gold-500 text-navy-900 rounded-lg hover:bg-gold-400 font-medium disabled:opacity-50"
              >
                <Layers className="w-4 h-4" />
                Publish v{versionInfo.new_version}
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

function ImpactCard({ icon, label, value, note }: { icon: React.ReactNode; label: string; value: string; note: string }) {
  return (
    <div className="p-3 bg-navy-800 rounded-lg text-center">
      <div className="flex items-center justify-center gap-1 text-gold-400 mb-1">{icon}</div>
      <div className="text-lg font-bold text-gray-100">{value}</div>
      <div className="text-xs text-gray-500">{label}</div>
      <div className="text-xs text-gray-600">{note}</div>
    </div>
  );
}

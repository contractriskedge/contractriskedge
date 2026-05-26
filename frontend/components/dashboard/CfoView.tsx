"use client";

import React, { useState, useEffect } from "react";
import {
  DollarSign,
  TrendingUp,
  TrendingDown,
  AlertTriangle,
  Download,
  FileText,
  Loader2,
} from "lucide-react";
import { useAuth } from "@/components/auth/AuthProvider";
import * as api from "@/lib/api";

export function CfoView() {
  const { token } = useAuth();
  const [contracts, setContracts] = useState<api.Contract[]>([]);
  const [loading, setLoading] = useState(true);
  const [metrics, setMetrics] = useState<api.EvaluationMetrics | null>(null);

  useEffect(() => {
    if (!token) return;
    Promise.all([
      api.listContracts(token).then((d) => setContracts(d.contracts || [])).catch(() => {}),
      api.getEvaluationMetrics(token).then((d) => setMetrics(d.metrics)).catch(() => {}),
    ]).finally(() => setLoading(false));
  }, [token]);

  // Compute stats from real data
  const totalContracts = contracts.length;
  const highRisk = contracts.filter((c) => (c.risk_score || 0) >= 7).length;
  const totalExposureNum = contracts.reduce((sum, c) => sum + (c.risk_score || 0) * 100000, 0);
  const totalExposure = `$${(totalExposureNum / 1_000_000).toFixed(1)}M`;
  const avgRisk = totalContracts > 0
    ? (contracts.reduce((s, c) => s + (c.risk_score || 0), 0) / totalContracts).toFixed(1)
    : "0.0";

  if (loading) {
    return (
      <div className="space-y-6 animate-pulse">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          {[...Array(4)].map((_, i) => <div key={i} className="h-28 bg-gray-200 rounded-xl" />)}
        </div>
        <div className="h-64 bg-gray-200 rounded-xl" />
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-navy-900">CFO Risk Dashboard</h1>
          <p className="text-sm text-gray-500 mt-1">
            Financial exposure summary across all contracts
          </p>
        </div>
        <button
          onClick={() => {
            if (token) {
              api.downloadExportCsv(token, api.getExportAuditCsvUrl(), "cfo_report.csv")
                .catch(err => console.error("Export failed:", err));
            }
          }}
          className="btn-primary gap-2"
        >
          <Download className="w-4 h-4" />
          Export PDF Report
        </button>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="stat-card">
          <DollarSign className="w-5 h-5 text-gold-500 mb-1" />
          <span className="stat-label">Total $ at Risk</span>
          <span className="stat-value text-gold-500">{totalExposure}</span>
          <span className="stat-trend text-risk-high">{highRisk} high-risk contracts</span>
        </div>

        <div className="stat-card">
          <TrendingUp className="w-5 h-5 text-navy-500 mb-1" />
          <span className="stat-label">Avg Risk Score</span>
          <span className="stat-value">{avgRisk}</span>
          <span className="stat-trend text-gray-500">Across {totalContracts} contracts</span>
        </div>

        <div className="stat-card">
          <AlertTriangle className="w-5 h-5 text-risk-high mb-1" />
          <span className="stat-label">High Risk Contracts</span>
          <span className="stat-value text-risk-high">{highRisk}</span>
          <span className="stat-trend text-risk-high">Requires immediate attention</span>
        </div>

        <div className="stat-card">
          <FileText className="w-5 h-5 text-risk-medium mb-1" />
          <span className="stat-label">Model Accuracy</span>
          <span className="stat-value text-risk-medium">
            {metrics ? `${Math.round(metrics.overall_accuracy * 100)}%` : "N/A"}
          </span>
          <span className="stat-trend text-gray-500">
            {metrics ? `${(metrics.false_positive_rate * 100).toFixed(1)}% FP rate` : "Awaiting eval"}
          </span>
        </div>
      </div>

      {/* Two-column layout */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Risk Exposure by Category */}
        <div className="card">
          <div className="card-header">
            <h2 className="font-semibold text-navy-900">Contract Risk Distribution</h2>
          </div>
          <div className="card-body space-y-4">
            {contracts.length === 0 ? (
              <p className="text-gray-500 text-center py-8 text-sm">No contracts analyzed yet</p>
            ) : (
              contracts.slice(0, 10).map((c) => (
                <div key={c.contract_id} className="flex items-center justify-between">
                  <div className="flex-1">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-sm font-medium text-gray-900 truncate mr-2">{c.filename}</span>
                      <span className="text-sm font-bold text-navy-900">{c.risk_score || "—"}/10</span>
                    </div>
                    <div className="flex-1 h-2 bg-gray-100 rounded-full overflow-hidden">
                      <div
                        className={`h-full rounded-full ${
                          (c.risk_score || 0) >= 7 ? "bg-risk-high" :
                          (c.risk_score || 0) >= 4 ? "bg-risk-medium" : "bg-risk-low"
                        }`}
                        style={{ width: `${(c.risk_score || 0) * 10}%` }}
                      />
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Top High-Risk Contracts */}
        <div className="card">
          <div className="card-header">
            <h2 className="font-semibold text-navy-900">Highest-Risk Contracts</h2>
          </div>
          <div className="card-body p-0 divide-y divide-gray-100">
            {contracts.length === 0 ? (
              <div className="text-center py-12 text-gray-500 text-sm">No contracts uploaded yet</div>
            ) : (
              [...contracts]
                .sort((a, b) => (b.risk_score || 0) - (a.risk_score || 0))
                .slice(0, 5)
                .map((c, i) => (
                  <div key={c.contract_id} className="flex items-center gap-4 px-6 py-4 hover:bg-gray-50">
                    <span className="text-lg font-bold text-gray-300 w-6">{(i + 1).toString().padStart(2, "0")}</span>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-gray-900 truncate">{c.filename}</p>
                      <p className="text-xs text-gray-500 mt-0.5">
                        {c.contract_type?.replace(/_/g, " ")} • {new Date(c.created_at).toLocaleDateString()}
                      </p>
                    </div>
                    <div className={`w-10 h-10 rounded-full flex items-center justify-center text-white font-bold text-sm ${
                      (c.risk_score || 0) >= 7 ? "bg-risk-high" : "bg-risk-medium"
                    }`}>
                      {c.risk_score || "—"}
                    </div>
                  </div>
                ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

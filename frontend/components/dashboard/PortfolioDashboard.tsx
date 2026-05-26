"use client";

import React, { useState, useEffect } from "react";
import { useAuth } from "@/components/auth/AuthProvider";
import {
  FileText,
  AlertTriangle,
  TrendingUp,
  Shield,
  Download,
  Filter,
  Search,
  ArrowUpDown,
} from "lucide-react";
import * as api from "@/lib/api";

function RiskGauge({ score }: { score: number }) {
  const color =
    score >= 8 ? "bg-risk-critical" :
    score >= 6 ? "bg-risk-high" :
    score >= 4 ? "bg-risk-medium" :
    "bg-risk-low";
  return (
    <div className={`w-10 h-10 rounded-full flex items-center justify-center text-white font-bold text-sm ${color}`}>
      {score}
    </div>
  );
}

export function PortfolioDashboard() {
  const { token } = useAuth();
  const [contracts, setContracts] = useState<api.Contract[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [filterRisk, setFilterRisk] = useState<string>("all");

  useEffect(() => {
    if (!token) return;
    api.listContracts(token).then((data) => {
      setContracts(data.contracts || []);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, [token]);

  // Stats
  const totalContracts = contracts.length;
  const highRisk = contracts.filter((c) => (c.risk_score || 0) >= 7).length;
  const mediumRisk = contracts.filter((c) => (c.risk_score || 0) >= 4 && (c.risk_score || 0) < 7).length;
  const lowRisk = contracts.filter((c) => (c.risk_score || 0) < 4).length;

  const filtered = contracts.filter((c) => {
    const matchesSearch = c.filename.toLowerCase().includes(search.toLowerCase());
    const matchesRisk =
      filterRisk === "all" ||
      (filterRisk === "high" && (c.risk_score || 0) >= 7) ||
      (filterRisk === "medium" && (c.risk_score || 0) >= 4 && (c.risk_score || 0) < 7) ||
      (filterRisk === "low" && (c.risk_score || 0) < 4);
    return matchesSearch && matchesRisk;
  });

  if (loading) {
    return (
      <div className="space-y-6 animate-pulse">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="h-28 bg-gray-200 rounded-xl" />
          ))}
        </div>
        <div className="h-96 bg-gray-200 rounded-xl" />
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-navy-900">Portfolio Risk Dashboard</h1>
          <p className="text-sm text-gray-500 mt-1">
            Real-time risk overview across all contracts
          </p>
        </div>
        <button
          onClick={() => {
            if (token) {
              api.downloadExportCsv(token, api.getExportAuditCsvUrl(), "audit_log.csv")
                .catch(err => console.error("Export failed:", err));
            }
          }}
          className="btn-secondary gap-2"
        >
          <Download className="w-4 h-4" />
          Export Report
        </button>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="stat-card">
          <div className="flex items-center justify-between">
            <span className="stat-label">Total Contracts</span>
            <FileText className="w-5 h-5 text-navy-400" />
          </div>
          <span className="stat-value">{totalContracts}</span>
          <span className="stat-trend text-gray-500">Active agreements</span>
        </div>

        <div className="stat-card">
          <div className="flex items-center justify-between">
            <span className="stat-label">High Risk</span>
            <AlertTriangle className="w-5 h-5 text-risk-high" />
          </div>
          <span className="stat-value text-risk-high">{highRisk}</span>
          <span className="stat-trend text-risk-high">
            {totalContracts > 0 ? ` ${Math.round((highRisk / totalContracts) * 100)}% of portfolio` : "0%"}
          </span>
        </div>

        <div className="stat-card">
          <div className="flex items-center justify-between">
            <span className="stat-label">Medium Risk</span>
            <TrendingUp className="w-5 h-5 text-risk-medium" />
          </div>
          <span className="stat-value text-risk-medium">{mediumRisk}</span>
          <span className="stat-trend text-risk-medium">
            {totalContracts > 0 ? `${Math.round((mediumRisk / totalContracts) * 100)}% of portfolio` : "0%"}
          </span>
        </div>

        <div className="stat-card">
          <div className="flex items-center justify-between">
            <span className="stat-label">Low Risk</span>
            <Shield className="w-5 h-5 text-risk-low" />
          </div>
          <span className="stat-value text-risk-low">{lowRisk}</span>
          <span className="stat-trend text-risk-low">
            {totalContracts > 0 ? `${Math.round((lowRisk / totalContracts) * 100)}% of portfolio` : "0%"}
          </span>
        </div>
      </div>

      {/* Filters & Search */}
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            type="text"
            placeholder="Search contracts..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="input pl-10"
          />
        </div>
        <select
          value={filterRisk}
          onChange={(e) => setFilterRisk(e.target.value)}
          className="select w-40"
        >
          <option value="all">All Risk Levels</option>
          <option value="high">High Risk (7+)</option>
          <option value="medium">Medium Risk (4-6)</option>
          <option value="low">Low Risk (1-3)</option>
        </select>
      </div>

      {/* Contract Heatmap */}
      <div className="card">
        <div className="card-header flex items-center justify-between">
          <h2 className="font-semibold text-navy-900">Contract Risk Heatmap</h2>
          <span className="text-xs text-gray-500">{filtered.length} contracts</span>
        </div>
        <div className="card-body p-0">
          {filtered.length === 0 ? (
            <div className="text-center py-12 text-gray-500">
              <FileText className="w-12 h-12 mx-auto mb-3 text-gray-300" />
              <p className="font-medium">No contracts found</p>
              <p className="text-sm mt-1">Upload contracts to see them here</p>
            </div>
          ) : (
            <div className="divide-y divide-gray-100">
              {filtered.map((contract) => (
                <div
                  key={contract.contract_id}
                  className="flex items-center gap-4 px-6 py-4 hover:bg-gray-50 transition-colors cursor-pointer"
                >
                  <RiskGauge score={contract.risk_score || 0} />
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-gray-900 truncate">
                      {contract.filename}
                    </p>
                    <div className="flex items-center gap-3 mt-1">
                      <span className="text-xs text-gray-500 capitalize">
                        {contract.contract_type?.replace(/_/g, " ")}
                      </span>
                      {contract.counterparty && (
                        <span className="text-xs text-gray-400">• {contract.counterparty}</span>
                      )}
                      <span className="text-xs text-gray-400">
                        • {new Date(contract.created_at).toLocaleDateString()}
                      </span>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    {contract.tags?.slice(0, 2).map((tag) => (
                      <span key={tag} className="badge bg-navy-50 text-navy-700">
                        {tag}
                      </span>
                    ))}
                  </div>
                  <ArrowUpDown className="w-4 h-4 text-gray-300" />
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

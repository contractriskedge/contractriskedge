"use client";

import React, { useState, useRef } from "react";
import { ShoppingCart, Upload, Download, FileSpreadsheet, Search, Loader2, CheckCircle, XCircle, AlertCircle } from "lucide-react";
import { useAuth } from "@/components/auth/AuthProvider";
import * as api from "@/lib/api";
import { useProcurementDashboard } from "@/services/hooks/useProcurement";

export function ProcurementView() {
  const { token } = useAuth();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);
  const [batchResult, setBatchResult] = useState<api.BatchUploadResponse | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");

  // Real procurement dashboard data
  const { data: dashboardData, isLoading, error } = useProcurementDashboard();
  const suppliers = dashboardData?.suppliers ?? [];
  const totalSuppliers = dashboardData?.total_suppliers ?? 0;
  const highRiskSuppliers = dashboardData?.high_risk_suppliers ?? 0;
  const avgRiskScore = dashboardData?.avg_risk_score ?? 0;
  const totalContractValue = dashboardData?.total_contract_value ?? 0;
  const kpis = dashboardData?.kpis ?? [];

  // Format total contract value
  const formattedTotalValue = totalContractValue >= 1_000_000
    ? `$${(totalContractValue / 1_000_000).toFixed(1)}M`
    : totalContractValue >= 1_000
      ? `$${(totalContractValue / 1_000).toFixed(1)}K`
      : `$${totalContractValue.toLocaleString()}`;

  const handleBatchUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0 || !token) return;

    setUploading(true);
    setUploadError(null);
    setBatchResult(null);

    try {
      const result = await api.batchUploadDocuments(token, Array.from(files));
      setBatchResult(result);
    } catch (err: any) {
      setUploadError(err.message || "Batch upload failed");
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-navy-900">Procurement Dashboard</h1>
          <p className="text-sm text-gray-500 mt-1">Vendor contract risk comparison matrix</p>
        </div>
        <div className="flex gap-2">
          <input
            ref={fileInputRef}
            type="file"
            multiple
            accept=".pdf,.docx,.doc,.txt"
            className="hidden"
            onChange={handleBatchUpload}
          />
          <button
            onClick={() => fileInputRef.current?.click()}
            disabled={uploading}
            className="btn-secondary gap-2"
          >
            {uploading ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Upload className="w-4 h-4" />
            )}
            {uploading ? "Uploading..." : "Batch Upload"}
          </button>
          <button
            onClick={() => {
              if (token) {
                api.downloadExportCsv(token, api.getExportProcurementCsvUrl(), "procurement_vendors.csv")
                  .catch(err => console.error("Export failed:", err));
              }
            }}
            className="btn-secondary gap-2"
          >
            <FileSpreadsheet className="w-4 h-4" />
            Export Excel
          </button>
        </div>
      </div>

      {/* Batch upload feedback */}
      {batchResult && (
        <div className="flex items-center gap-3 p-4 bg-green-50 border border-green-200 rounded-lg">
          <CheckCircle className="w-5 h-5 text-green-600" />
          <div>
            <p className="text-sm font-medium text-green-800">
              Batch upload complete: {batchResult.accepted} accepted, {batchResult.failed} failed
            </p>
            <p className="text-xs text-green-600">Batch ID: {batchResult.batch_id}</p>
          </div>
        </div>
      )}

      {uploadError && (
        <div className="flex items-center gap-3 p-4 bg-red-50 border border-red-200 rounded-lg">
          <XCircle className="w-5 h-5 text-red-600" />
          <p className="text-sm text-red-700">{uploadError}</p>
        </div>
      )}

      {/* KPI Summary Cards */}
      {kpis.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          {kpis.map((kpi, i) => (
            <div key={i} className="stat-card">
              <span className="stat-label">{kpi.label}</span>
              <span className="stat-value">
                {kpi.format === "currency"
                  ? `$${(kpi.value / 1_000_000).toFixed(1)}M`
                  : kpi.format === "percentage"
                    ? `${kpi.value}%`
                    : kpi.value.toLocaleString()}
              </span>
              <span className={`stat-trend ${kpi.trend === "up" ? "text-green-600" : kpi.trend === "down" ? "text-red-500" : "text-gray-400"}`}>
                {kpi.change > 0 ? "+" : ""}{kpi.change}%
              </span>
            </div>
          ))}
        </div>
      )}

      {/* Vendor Comparison Matrix */}
      <div className="card overflow-hidden">
        <div className="card-header flex items-center justify-between">
          <h2 className="font-semibold text-navy-900">Vendor Risk Comparison</h2>
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input
              type="text"
              placeholder="Search vendors..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="input pl-9 w-64"
            />
          </div>
        </div>

        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="w-6 h-6 text-gold-400 animate-spin" />
          </div>
        ) : error ? (
          <div className="flex items-center gap-2 p-6 text-red-600">
            <AlertCircle className="w-5 h-5" />
            <span className="text-sm">Failed to load vendor data</span>
          </div>
        ) : suppliers.length === 0 ? (
          <div className="text-center py-12 text-gray-500 text-sm">No vendors found</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="bg-gray-50">
                  <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">Vendor</th>
                  <th className="text-center px-6 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">Risk Score</th>
                  <th className="text-center px-6 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">Contract Value</th>
                  <th className="text-center px-6 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">Renewal Date</th>
                  <th className="text-center px-6 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">SLA Compliance</th>
                  <th className="text-center px-6 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">Incidents (30d)</th>
                  <th className="text-center px-6 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {suppliers
                  .filter((v) => v.name.toLowerCase().includes(searchQuery.toLowerCase()))
                  .map((v) => (
                  <tr key={v.id} className="hover:bg-gray-50 transition-colors">
                    <td className="px-6 py-4">
                      <p className="text-sm font-medium text-gray-900">{v.name}</p>
                      <p className="text-xs text-gray-500">{v.category}</p>
                    </td>
                    <td className="px-6 py-4 text-center">
                      <div className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${
                        v.risk_score >= 7 ? "bg-red-100 text-red-800" :
                        v.risk_score >= 5 ? "bg-orange-100 text-orange-800" :
                        "bg-green-100 text-green-800"
                      }`}>
                        {v.risk_score}/10
                      </div>
                    </td>
                    <td className="px-6 py-4 text-center text-sm font-medium text-gray-900">
                      ${(v.contract_value / 1_000).toFixed(0)}K
                    </td>
                    <td className="px-6 py-4 text-center text-sm text-gray-600">{v.renewal_date}</td>
                    <td className="px-6 py-4 text-center">
                      <span className={`text-sm font-medium ${
                        v.sla_compliance >= 95 ? "text-green-600" :
                        v.sla_compliance >= 85 ? "text-orange-600" :
                        "text-red-600"
                      }`}>
                        {v.sla_compliance}%
                      </span>
                    </td>
                    <td className="px-6 py-4 text-center text-sm text-gray-600">{v.incidents_30d}</td>
                    <td className="px-6 py-4 text-center">
                      <span className={`badge ${
                        v.status === "active" ? "bg-green-100 text-green-800" :
                        v.status === "under_review" ? "bg-orange-100 text-orange-800" :
                        v.status === "onboarding" ? "bg-blue-100 text-blue-800" :
                        "bg-gray-100 text-gray-800"
                      }`}>
                        {v.status.replace(/_/g, " ")}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

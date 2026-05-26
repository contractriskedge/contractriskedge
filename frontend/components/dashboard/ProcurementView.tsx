"use client";

import React, { useState, useRef } from "react";
import { ShoppingCart, Upload, Download, FileSpreadsheet, Search, Loader2, CheckCircle, XCircle } from "lucide-react";
import { useAuth } from "@/components/auth/AuthProvider";
import * as api from "@/lib/api";

export function ProcurementView() {
  const { token } = useAuth();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);
  const [batchResult, setBatchResult] = useState<api.BatchUploadResponse | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");

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
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="bg-gray-50">
                <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">Vendor</th>
                <th className="text-center px-6 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">Risk Score</th>
                <th className="text-center px-6 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">Contracts</th>
                <th className="text-center px-6 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">Contract Value</th>
                <th className="text-center px-6 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">Expiry</th>
                <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">Top Risk</th>
                <th className="text-center px-6 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {vendors
                .filter((v) => v.name.toLowerCase().includes(searchQuery.toLowerCase()))
                .map((v) => (
                <tr key={v.name} className="hover:bg-gray-50 transition-colors">
                  <td className="px-6 py-4">
                    <p className="text-sm font-medium text-gray-900">{v.name}</p>
                  </td>
                  <td className="px-6 py-4 text-center">
                    <div className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${
                      v.risk >= 7 ? "bg-red-100 text-red-800" :
                      v.risk >= 5 ? "bg-orange-100 text-orange-800" :
                      "bg-green-100 text-green-800"
                    }`}>
                      {v.risk}/10
                    </div>
                  </td>
                  <td className="px-6 py-4 text-center text-sm text-gray-600">{v.contracts}</td>
                  <td className="px-6 py-4 text-center text-sm font-medium text-gray-900">{v.value}</td>
                  <td className="px-6 py-4 text-center text-sm text-gray-600">{v.expiry}</td>
                  <td className="px-6 py-4 text-sm text-gray-600">{v.topRisk}</td>
                  <td className="px-6 py-4 text-center">
                    <span className="badge bg-green-100 text-green-800">Active</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

const vendors = [
  { name: "TechSolutions Inc.", risk: 8.5, contracts: 3, expiry: "2027-03-15", value: "$500K", topRisk: "Liability" },
  { name: "CloudSoft Inc.", risk: 7.2, contracts: 2, expiry: "2026-11-30", value: "$350K", topRisk: "IP Ownership" },
  { name: "DataPartner LLC", risk: 6.8, contracts: 1, expiry: "2026-09-01", value: "$250K", topRisk: "Confidentiality" },
  { name: "SecureHost Corp", risk: 4.2, contracts: 2, expiry: "2027-06-30", value: "$180K", topRisk: "SLA" },
  { name: "GlobalLogistics Ltd", risk: 3.1, contracts: 1, expiry: "2026-12-31", value: "$120K", topRisk: "Payment" },
];

"use client";

import React, { useState, useRef } from "react";
import { FileText, Upload, Search, Filter, CheckCircle, XCircle, Loader2, AlertTriangle, BarChart3 } from "lucide-react";
import { useAuth } from "@/components/auth/AuthProvider";
import * as api from "@/lib/api";

export function ContractsPage() {
  const { token } = useAuth();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState<api.IngestionJobResult | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [contracts, setContracts] = useState<api.Contract[]>([]);
  const [loading, setLoading] = useState(true);
  const [analyzing, setAnalyzing] = useState<string | null>(null);
  const [analysisResult, setAnalysisResult] = useState<{ contractId: string; reportId: string } | null>(null);
  const [generatingRedlines, setGeneratingRedlines] = useState<string | null>(null);
  const [redlineResult, setRedlineResult] = useState<string | null>(null);

  React.useEffect(() => {
    if (!token) return;
    api.listContracts(token).then((data) => {
      setContracts(data.contracts || []);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, [token]);

  const handleUploadClick = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !token) return;

    setUploading(true);
    setUploadError(null);
    setUploadResult(null);

    try {
      const result = await api.uploadDocument(token, file);
      setUploadResult(result);
    } catch (err: any) {
      setUploadError(err.message || "Upload failed");
    } finally {
      setUploading(false);
      try {
        const data = await api.listContracts(token);
        setContracts(data.contracts || []);
      } catch {}
    }
  };

  const handleAnalyze = async (contractId: string) => {
    if (!token) return;
    setAnalyzing(contractId);
    setAnalysisResult(null);
    try {
      const result = await api.analyzeContractRisks(token, contractId);
      setAnalysisResult({ contractId, reportId: result.report_id });
    } catch (err: any) {
      console.error("Analysis failed:", err);
    } finally {
      setAnalyzing(null);
    }
  };

  const handleGenerateRedlines = async (contractId: string) => {
    if (!token) return;
    setGeneratingRedlines(contractId);
    setRedlineResult(null);
    try {
      // Generate redline suggestions for common clause types
      const clauseTypes = ["indemnification", "liability_caps", "termination_rights", "confidentiality"];
      const sampleTexts: Record<string, string> = {
        indemnification: "The Supplier shall indemnify, defend, and hold harmless the Customer from and against any and all claims, damages, losses, liabilities, and expenses arising out of or related to any breach of this Agreement by the Supplier.",
        liability_caps: "In no event shall either party be liable for any indirect, incidental, special, consequential, or punitive damages, regardless of the theory of liability.",
        termination_rights: "This Agreement may be terminated by either party upon 30 days written notice to the other party.",
        confidentiality: "The Receiving Party shall maintain strict confidentiality of all Confidential Information disclosed by the Disclosing Party.",
      };
      
      let count = 0;
      for (const clauseType of clauseTypes) {
        try {
          await api.createRedlineSuggestion(
            token, contractId, clauseType, sampleTexts[clauseType]
          );
          count++;
        } catch (e) {
          console.error(`Failed to generate redline for ${clauseType}:`, e);
        }
      }
      setRedlineResult(`Generated ${count} redline suggestions`);
    } catch (err: any) {
      console.error("Redline generation failed:", err);
    } finally {
      setGeneratingRedlines(null);
    }
  };

  if (loading) {
    return (
      <div className="space-y-6 animate-pulse">
        <div className="h-10 bg-gray-200 rounded-lg w-1/3" />
        <div className="h-96 bg-gray-200 rounded-xl" />
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-navy-900">Contracts</h1>
          <p className="text-sm text-gray-500 mt-1">Manage and analyze your contract portfolio</p>
        </div>
        <div className="flex gap-2">
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,.docx,.doc,.txt"
            className="hidden"
            onChange={handleFileChange}
          />
          <button
            onClick={handleUploadClick}
            disabled={uploading}
            className="btn-primary gap-2"
          >
            {uploading ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Upload className="w-4 h-4" />
            )}
            {uploading ? "Uploading..." : "Upload Contract"}
          </button>
        </div>
      </div>

      {/* Upload result feedback */}
      {uploadResult && (
        <div className="flex items-center gap-3 p-4 bg-green-50 border border-green-200 rounded-lg">
          <CheckCircle className="w-5 h-5 text-green-600" />
          <div>
            <p className="text-sm font-medium text-green-800">Upload successful</p>
            <p className="text-xs text-green-600">
              Job ID: {uploadResult.job_id} — Status: {uploadResult.status}
            </p>
          </div>
        </div>
      )}

      {uploadError && (
        <div className="flex items-center gap-3 p-4 bg-red-50 border border-red-200 rounded-lg">
          <XCircle className="w-5 h-5 text-red-600" />
          <p className="text-sm text-red-700">{uploadError}</p>
        </div>
      )}

      {/* Analysis result feedback */}
      {analysisResult && (
        <div className="flex items-center gap-3 p-4 bg-blue-50 border border-blue-200 rounded-lg">
          <BarChart3 className="w-5 h-5 text-blue-600" />
          <div>
            <p className="text-sm font-medium text-blue-800">Risk analysis started</p>
            <p className="text-xs text-blue-600">
              Report ID: {analysisResult.reportId} — Check the Portfolio dashboard for results
            </p>
          </div>
        </div>
      )}

      {/* Redline result feedback */}
      {redlineResult && (
        <div className="flex items-center gap-3 p-4 bg-purple-50 border border-purple-200 rounded-lg">
          <FileText className="w-5 h-5 text-purple-600" />
          <div>
            <p className="text-sm font-medium text-purple-800">{redlineResult}</p>
            <p className="text-xs text-purple-600">Go to Legal Review to view and accept/reject suggestions</p>
          </div>
        </div>
      )}

      {/* Contract list */}
      <div className="card">
        <div className="card-body">
          {contracts.length === 0 ? (
            <div className="text-center py-12 text-gray-500">
              <FileText className="w-12 h-12 mx-auto mb-3 text-gray-300" />
              <p className="font-medium">No contracts yet</p>
              <p className="text-sm mt-1">Upload a PDF, DOCX, or TXT file to get started</p>
              <button onClick={handleUploadClick} className="btn-primary mt-4 gap-2">
                <Upload className="w-4 h-4" />
                Upload Your First Contract
              </button>
            </div>
          ) : (
            <div className="divide-y divide-gray-100">
              {contracts.map((c) => (
                <div key={c.contract_id} className="flex items-center gap-4 px-4 py-3 hover:bg-gray-50">
                  <FileText className="w-5 h-5 text-navy-400" />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900 truncate">{c.filename}</p>
                    <p className="text-xs text-gray-500">
                      {c.contract_type?.replace(/_/g, " ")} — {new Date(c.created_at).toLocaleDateString()}
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => handleAnalyze(c.contract_id)}
                      disabled={analyzing === c.contract_id}
                      className="btn-ghost text-xs gap-1"
                    >
                      {analyzing === c.contract_id ? (
                        <Loader2 className="w-3 h-3 animate-spin" />
                      ) : (
                        <AlertTriangle className="w-3 h-3" />
                      )}
                      {analyzing === c.contract_id ? "Analyzing..." : "Analyze Risks"}
                    </button>
                    <button
                      onClick={() => handleGenerateRedlines(c.contract_id)}
                      disabled={generatingRedlines === c.contract_id}
                      className="btn-ghost text-xs gap-1"
                    >
                      {generatingRedlines === c.contract_id ? (
                        <Loader2 className="w-3 h-3 animate-spin" />
                      ) : (
                        <FileText className="w-3 h-3" />
                      )}
                      {generatingRedlines === c.contract_id ? "Generating..." : "Generate Redlines"}
                    </button>
                    <span className={`badge ${
                      c.status === "ready" ? "bg-green-100 text-green-800" :
                      c.status === "processing" ? "bg-yellow-100 text-yellow-800" :
                      c.status === "error" ? "bg-red-100 text-red-800" :
                      "bg-gray-100 text-gray-800"
                    }`}>
                      {c.status}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

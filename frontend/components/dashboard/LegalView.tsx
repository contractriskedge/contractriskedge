"use client";

import React, { useState, useEffect } from "react";
import { Scale, FileText, ChevronRight, AlertTriangle, Loader2, Download, CheckCircle, XCircle, Shield, TrendingUp, Gavel, Link as LinkIcon, Globe, Lightbulb, BarChart3, Flag } from "lucide-react";
import { useAuth } from "@/components/auth/AuthProvider";
import * as api from "@/lib/api";

// ── Types for 8-field explainability ──

interface LinkedEvidence {
  clause_reference: string;
  excerpt: string;
  page_number?: number;
  section?: string;
  relevance_score: number;
}

interface JurisdictionalConsideration {
  jurisdiction: string;
  rule_reference: string;
  risk_modifier: number;
  explanation: string;
}

interface RiskFlagDetail {
  clause_text: string;
  risk_category: string;
  why_flagged: string;
  potential_business_impact: string;
  market_benchmark_comparison: string;
  confidence_score: number;
  confidence_label: string;
  suggested_remediation: string;
  linked_evidence: LinkedEvidence[];
  jurisdictional_considerations: JurisdictionalConsideration[];
  severity?: { severity_score?: number };
  rationale?: any;
  assessment?: any;
}

// ── Escalation Item ──

interface EscalationItem {
  escalation_id: string;
  contract_id: string;
  clause_text: string;
  risk_category: string;
  severity_score: number;
  confidence_score: number;
  escalation_reason: string;
  status: string;
  created_at: string;
}

export function LegalView() {
  const { token } = useAuth();
  const [selectedClause, setSelectedClause] = useState<string | null>(null);
  const [redlines, setRedlines] = useState<api.RedlineSuggestion[]>([]);
  const [contracts, setContracts] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [filterContract, setFilterContract] = useState<string>("all");
  const [activeTab, setActiveTab] = useState<"redlines" | "escalations" | "risk-flags">("redlines");
  const [escalations, setEscalations] = useState<EscalationItem[]>([]);
  const [riskFlags, setRiskFlags] = useState<RiskFlagDetail[]>([]);
  const [selectedRiskFlag, setSelectedRiskFlag] = useState<number | null>(null);

  useEffect(() => {
    if (!token) return;
    // Fetch both redlines and contracts to map contract IDs to names
    Promise.all([
      api.listRedlines(token),
      api.listContracts(token).catch(() => ({ contracts: [], total: 0 })),
    ]).then(([redlineData, contractData]) => {
      let suggestions: api.RedlineSuggestion[] = [];
      if (Array.isArray(redlineData)) {
        suggestions = redlineData;
      } else if ((redlineData as any).suggestions) {
        suggestions = (redlineData as any).suggestions;
      }
      setRedlines(suggestions);

      // Build contract ID -> name mapping
      const contractMap: Record<string, string> = {};
      for (const c of contractData.contracts || []) {
        contractMap[c.contract_id] = c.filename;
      }
      setContracts(contractMap);
      setLoading(false);
    }).catch((err) => {
      setError(err.message);
      setLoading(false);
    });
  }, [token]);

  useEffect(() => {
    if (!token || activeTab !== "escalations") return;
    fetch(`${process.env.NEXT_PUBLIC_API_URL || "/api/v1"}/risks/escalations`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((r) => r.json())
      .then((data) => {
        if (data.escalations) setEscalations(data.escalations);
      })
      .catch(() => {});
  }, [token, activeTab]);

  useEffect(() => {
    if (!token || activeTab !== "risk-flags") return;
    api.listRisks(token).then((data) => {
      if ((data as any).risks) {
        setRiskFlags((data as any).risks);
      }
    }).catch(() => {});
  }, [token, activeTab]);

  const handleAccept = async (suggestionId: string) => {
    if (!token) return;
    setActionLoading(suggestionId);
    try {
      await api.acceptRedlineSuggestion(token, suggestionId);
      setRedlines((prev) =>
        prev.map((r) => (r.suggestion_id === suggestionId ? { ...r, status: "accepted" } : r))
      );
    } catch (err: any) {
      setError(err.message);
    } finally {
      setActionLoading(null);
    }
  };

  const handleReject = async (suggestionId: string) => {
    if (!token) return;
    setActionLoading(suggestionId);
    try {
      await api.rejectRedlineSuggestion(token, suggestionId);
      setRedlines((prev) =>
        prev.map((r) => (r.suggestion_id === suggestionId ? { ...r, status: "rejected" } : r))
      );
    } catch (err: any) {
      setError(err.message);
    } finally {
      setActionLoading(null);
    }
  };

  const selected = redlines.find((r) => r.suggestion_id === selectedClause);
  const selectedFlag = selectedRiskFlag !== null ? riskFlags[selectedRiskFlag] : null;

  // Get unique contract IDs that have suggestions
  const contractIds = [...new Set(redlines.map((r) => r.contract_id))];
  
  // Filter suggestions by selected contract
  const filteredRedlines = filterContract === "all"
    ? redlines
    : redlines.filter((r) => r.contract_id === filterContract);

  // Group filtered suggestions by contract
  const groupedRedlines: Record<string, api.RedlineSuggestion[]> = {};
  for (const r of filteredRedlines) {
    if (!groupedRedlines[r.contract_id]) groupedRedlines[r.contract_id] = [];
    groupedRedlines[r.contract_id].push(r);
  }

  const getContractName = (contractId: string) => {
    return contracts[contractId] || contractId.slice(0, 20) + "...";
  };

  const getConfidenceColor = (score: number) => {
    if (score >= 0.7) return "text-green-600 bg-green-50 border-green-200";
    if (score >= 0.4) return "text-yellow-600 bg-yellow-50 border-yellow-200";
    return "text-red-600 bg-red-50 border-red-200";
  };

  const getConfidenceBar = (score: number) => {
    const pct = Math.round(score * 100);
    const color = score >= 0.7 ? "bg-green-500" : score >= 0.4 ? "bg-yellow-500" : "bg-red-500";
    return (
      <div className="flex items-center gap-2">
        <div className="flex-1 h-2 bg-gray-200 rounded-full overflow-hidden">
          <div className={`h-full rounded-full transition-all ${color}`} style={{ width: `${pct}%` }} />
        </div>
        <span className="text-xs font-medium w-10 text-right">{pct}%</span>
      </div>
    );
  };

  if (loading) {
    return (
      <div className="space-y-6 animate-pulse">
        <div className="h-8 bg-gray-200 rounded-lg w-1/4" />
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-1 h-96 bg-gray-200 rounded-xl" />
          <div className="lg:col-span-2 h-96 bg-gray-200 rounded-xl" />
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-navy-900">Legal Review</h1>
          <p className="text-sm text-gray-500 mt-1">Clause-level risk analysis with 8-field explainability</p>
        </div>
        {/* Tab navigation */}
        <div className="flex bg-gray-100 rounded-lg p-1">
          <button
            onClick={() => setActiveTab("redlines")}
            className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors ${
              activeTab === "redlines" ? "bg-white shadow-sm text-navy-900" : "text-gray-500 hover:text-gray-700"
            }`}
          >
            Redlines
          </button>
          <button
            onClick={() => setActiveTab("risk-flags")}
            className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors ${
              activeTab === "risk-flags" ? "bg-white shadow-sm text-navy-900" : "text-gray-500 hover:text-gray-700"
            }`}
          >
            <Shield className="w-3 h-3 inline mr-1" />
            Risk Flags
          </button>
          <button
            onClick={() => setActiveTab("escalations")}
            className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors ${
              activeTab === "escalations" ? "bg-white shadow-sm text-navy-900" : "text-gray-500 hover:text-gray-700"
            }`}
          >
            <AlertTriangle className="w-3 h-3 inline mr-1" />
            Escalations
            {escalations.filter(e => e.status === "pending").length > 0 && (
              <span className="ml-1 bg-red-500 text-white rounded-full px-1.5 py-0.5 text-[9px]">
                {escalations.filter(e => e.status === "pending").length}
              </span>
            )}
          </button>
        </div>
      </div>

      {error && (
        <div className="flex items-center gap-3 p-4 bg-red-50 border border-red-200 rounded-lg">
          <XCircle className="w-5 h-5 text-red-600" />
          <p className="text-sm text-red-700">{error}</p>
        </div>
      )}

      {/* ── ESCALATIONS TAB ── */}
      {activeTab === "escalations" && (
        <div className="card">
          <div className="card-header">
            <h2 className="font-semibold text-navy-900">Attorney Review Queue</h2>
            <span className="text-xs text-gray-500">{escalations.length} items</span>
          </div>
          <div className="card-body p-0">
            {escalations.length === 0 ? (
              <div className="text-center py-12 text-gray-500">
                <CheckCircle className="w-10 h-10 mx-auto mb-2 text-green-300" />
                <p className="text-sm font-medium">No pending escalations</p>
                <p className="text-xs mt-1">All risk flags have sufficient confidence</p>
              </div>
            ) : (
              <div className="divide-y divide-gray-100">
                {escalations.map((item) => (
                  <div key={item.escalation_id} className="p-4 hover:bg-gray-50">
                    <div className="flex items-start justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <AlertTriangle className={`w-4 h-4 ${
                          item.escalation_reason === "low_confidence" ? "text-yellow-500" : "text-red-500"
                        }`} />
                        <span className="text-sm font-medium text-navy-900 capitalize">
                          {item.escalation_reason.replace(/_/g, " ")}
                        </span>
                      </div>
                      <span className={`badge text-[10px] ${
                        item.status === "pending" ? "bg-yellow-100 text-yellow-800" :
                        item.status === "in_review" ? "bg-blue-100 text-blue-800" : "bg-gray-100 text-gray-800"
                      }`}>
                        {item.status}
                      </span>
                    </div>
                    <p className="text-xs text-gray-600 line-clamp-2 mb-2">{item.clause_text}</p>
                    <div className="flex items-center gap-3 text-xs text-gray-500">
                      <span>Severity: {item.severity_score}/10</span>
                      <span>Confidence: {Math.round(item.confidence_score * 100)}%</span>
                      <span>{item.risk_category}</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* ── RISK FLAGS TAB (8-field explainability) ── */}
      {activeTab === "risk-flags" && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Risk Flag List */}
          <div className="lg:col-span-1 card">
            <div className="card-header">
              <h2 className="font-semibold text-navy-900">Risk Flags</h2>
              <span className="text-xs text-gray-500">{riskFlags.length} items</span>
            </div>
            <div className="card-body p-0 divide-y divide-gray-100 max-h-[600px] overflow-y-auto">
              {riskFlags.length === 0 ? (
                <div className="text-center py-12 text-gray-500">
                  <Shield className="w-10 h-10 mx-auto mb-2 text-gray-300" />
                  <p className="text-sm font-medium">No risk flags yet</p>
                  <p className="text-xs mt-1">Run a risk analysis to see flags</p>
                </div>
              ) : (
                riskFlags.map((flag, idx) => (
                  <button
                    key={idx}
                    onClick={() => setSelectedRiskFlag(idx)}
                    className={`w-full text-left px-4 py-3 hover:bg-gray-50 transition-colors ${
                      selectedRiskFlag === idx ? "bg-navy-50 border-l-2 border-navy-900" : ""
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-xs font-medium text-gray-700 capitalize">
                        {flag.risk_category?.replace(/_/g, " ") || "Unknown"}
                      </span>
                      <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded ${
                        (flag.severity?.severity_score || 5) >= 7 ? "bg-red-100 text-red-800" :
                        (flag.severity?.severity_score || 5) >= 4 ? "bg-yellow-100 text-yellow-800" :
                        "bg-green-100 text-green-800"
                      }`}>
                        Severity: {flag.severity?.severity_score || "?"}/10
                      </span>
                    </div>
                    <p className="text-xs text-gray-600 line-clamp-2 leading-relaxed">{flag.clause_text}</p>
                    <div className="flex items-center gap-2 mt-1.5">
                      <span className={`text-[10px] px-1.5 py-0.5 rounded ${getConfidenceColor(flag.confidence_score || 0)}`}>
                        {Math.round((flag.confidence_score || 0) * 100)}% confidence
                      </span>
                    </div>
                  </button>
                ))
              )}
            </div>
          </div>

          {/* 8-Field Explainability Detail Panel */}
          <div className="lg:col-span-2 card">
            {selectedFlag ? (
              <div className="p-6 space-y-5 overflow-y-auto max-h-[800px]">
                {/* Header */}
                <div className="flex items-center justify-between">
                  <div>
                    <h2 className="text-lg font-semibold text-navy-900">8-Field Risk Analysis</h2>
                    <p className="text-xs text-gray-500 mt-0.5 capitalize">
                      Category: {selectedFlag.risk_category?.replace(/_/g, " ")}
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className={`text-xs font-medium px-2 py-1 rounded-full border ${getConfidenceColor(selectedFlag.confidence_score || 0)}`}>
                      {selectedFlag.confidence_label || "unknown"}
                    </span>
                  </div>
                </div>

                {/* Field 1: Clause Text */}
                <div className="p-4 bg-gray-50 rounded-lg border border-gray-200">
                  <div className="flex items-center gap-2 mb-2">
                    <FileText className="w-4 h-4 text-navy-600" />
                    <span className="text-xs font-semibold text-navy-700 uppercase tracking-wider">1. Clause Text</span>
                  </div>
                  <p className="text-sm text-gray-700 leading-relaxed">{selectedFlag.clause_text}</p>
                </div>

                {/* Field 2: Risk Category */}
                <div className="p-4 bg-gray-50 rounded-lg border border-gray-200">
                  <div className="flex items-center gap-2 mb-2">
                    <Flag className="w-4 h-4 text-navy-600" />
                    <span className="text-xs font-semibold text-navy-700 uppercase tracking-wider">2. Risk Category</span>
                  </div>
                  <p className="text-sm font-medium text-gray-700 capitalize">{selectedFlag.risk_category?.replace(/_/g, " ")}</p>
                  {selectedFlag.severity && (
                    <div className="flex items-center gap-2 mt-1">
                      <span className="text-xs text-gray-500">Severity:</span>
                      <div className="flex gap-0.5">
                        {[1,2,3,4,5,6,7,8,9,10].map((s) => (
                          <div key={s} className={`w-2 h-4 rounded-sm ${
                            s <= (selectedFlag.severity?.severity_score || 0)
                              ? (selectedFlag.severity?.severity_score || 0) >= 7 ? "bg-red-500"
                                : (selectedFlag.severity?.severity_score || 0) >= 4 ? "bg-yellow-500" : "bg-green-500"
                              : "bg-gray-200"
                          }`} />
                        ))}
                      </div>
                      <span className="text-xs font-medium">{selectedFlag.severity?.severity_score}/10</span>
                    </div>
                  )}
                </div>

                {/* Field 3: Why Flagged */}
                <div className="p-4 bg-red-50 rounded-lg border border-red-100">
                  <div className="flex items-center gap-2 mb-2">
                    <AlertTriangle className="w-4 h-4 text-red-600" />
                    <span className="text-xs font-semibold text-red-700 uppercase tracking-wider">3. Why Flagged</span>
                  </div>
                  <p className="text-sm text-gray-700 leading-relaxed">{selectedFlag.why_flagged || "No explanation provided."}</p>
                </div>

                {/* Field 4: Potential Business Impact */}
                <div className="p-4 bg-orange-50 rounded-lg border border-orange-100">
                  <div className="flex items-center gap-2 mb-2">
                    <TrendingUp className="w-4 h-4 text-orange-600" />
                    <span className="text-xs font-semibold text-orange-700 uppercase tracking-wider">4. Potential Business Impact</span>
                  </div>
                  <p className="text-sm text-gray-700 leading-relaxed">{selectedFlag.potential_business_impact || "No business impact assessment."}</p>
                </div>

                {/* Field 5: Market Benchmark Comparison */}
                <div className="p-4 bg-blue-50 rounded-lg border border-blue-100">
                  <div className="flex items-center gap-2 mb-2">
                    <BarChart3 className="w-4 h-4 text-blue-600" />
                    <span className="text-xs font-semibold text-blue-700 uppercase tracking-wider">5. Market Benchmark Comparison</span>
                  </div>
                  <p className="text-sm text-gray-700 leading-relaxed">{selectedFlag.market_benchmark_comparison || "No benchmark comparison available."}</p>
                </div>

                {/* Field 6: Confidence Score */}
                <div className="p-4 bg-purple-50 rounded-lg border border-purple-100">
                  <div className="flex items-center gap-2 mb-2">
                    <Shield className="w-4 h-4 text-purple-600" />
                    <span className="text-xs font-semibold text-purple-700 uppercase tracking-wider">6. Confidence Score</span>
                  </div>
                  <div className="space-y-2">
                    {getConfidenceBar(selectedFlag.confidence_score || 0)}
                    <p className="text-xs text-gray-500">
                      Label: <span className="font-medium capitalize">{selectedFlag.confidence_label || "unknown"}</span>
                    </p>
                  </div>
                </div>

                {/* Field 7: Suggested Remediation */}
                <div className="p-4 bg-green-50 rounded-lg border border-green-100">
                  <div className="flex items-center gap-2 mb-2">
                    <Lightbulb className="w-4 h-4 text-green-600" />
                    <span className="text-xs font-semibold text-green-700 uppercase tracking-wider">7. Suggested Remediation</span>
                  </div>
                  <p className="text-sm text-gray-700 leading-relaxed">{selectedFlag.suggested_remediation || "No remediation suggested."}</p>
                </div>

                {/* Field 8: Linked Evidence */}
                <div className="p-4 bg-indigo-50 rounded-lg border border-indigo-100">
                  <div className="flex items-center gap-2 mb-2">
                    <LinkIcon className="w-4 h-4 text-indigo-600" />
                    <span className="text-xs font-semibold text-indigo-700 uppercase tracking-wider">8. Linked Evidence</span>
                  </div>
                  {selectedFlag.linked_evidence && selectedFlag.linked_evidence.length > 0 ? (
                    <div className="space-y-2">
                      {selectedFlag.linked_evidence.map((evidence, i) => (
                        <div key={i} className="p-3 bg-white rounded border border-indigo-100">
                          <p className="text-xs font-medium text-indigo-700 mb-1">
                            {evidence.clause_reference}
                          </p>
                          <p className="text-xs text-gray-600 italic">&ldquo;{evidence.excerpt}&rdquo;</p>
                          <div className="flex items-center gap-2 mt-1">
                            <span className="text-[10px] text-gray-400">
                              Relevance: {Math.round(evidence.relevance_score * 100)}%
                            </span>
                            {evidence.section && (
                              <span className="text-[10px] text-gray-400">Section: {evidence.section}</span>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-sm text-gray-500">No linked evidence available.</p>
                  )}
                </div>

                {/* Field 9: Jurisdictional Considerations */}
                <div className="p-4 bg-teal-50 rounded-lg border border-teal-100">
                  <div className="flex items-center gap-2 mb-2">
                    <Globe className="w-4 h-4 text-teal-600" />
                    <span className="text-xs font-semibold text-teal-700 uppercase tracking-wider">9. Jurisdictional Considerations</span>
                  </div>
                  {selectedFlag.jurisdictional_considerations && selectedFlag.jurisdictional_considerations.length > 0 ? (
                    <div className="space-y-2">
                      {selectedFlag.jurisdictional_considerations.map((jc, i) => (
                        <div key={i} className="flex items-start gap-2 p-2 bg-white rounded border border-teal-100">
                          <Gavel className="w-3 h-3 text-teal-500 mt-0.5 flex-shrink-0" />
                          <div>
                            <p className="text-xs font-medium text-teal-700">
                              {jc.jurisdiction} — {jc.rule_reference}
                            </p>
                            <p className="text-xs text-gray-600 mt-0.5">{jc.explanation}</p>
                            <span className={`text-[10px] font-medium ${
                              jc.risk_modifier > 0 ? "text-red-500" : "text-green-500"
                            }`}>
                              Risk modifier: {jc.risk_modifier > 0 ? "+" : ""}{jc.risk_modifier}
                            </span>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-sm text-gray-500">No jurisdiction-specific considerations.</p>
                  )}
                </div>
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center py-16 text-gray-500">
                <Scale className="w-12 h-12 mb-3 text-gray-300" />
                <p className="font-medium">Select a risk flag to view</p>
                <p className="text-sm mt-1">Choose a risk flag from the left panel to see the 8-field explainability analysis</p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ── REDLINES TAB ── */}
      {activeTab === "redlines" && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Clause List */}
          <div className="lg:col-span-1 card">
            <div className="card-header flex items-center justify-between">
              <h2 className="font-semibold text-navy-900">Redline Suggestions</h2>
              <span className="text-xs text-gray-500">{filteredRedlines.length} items</span>
            </div>
            {/* Contract filter */}
            {contractIds.length > 1 && (
              <div className="px-4 py-2 border-b border-gray-100">
                <select
                  value={filterContract}
                  onChange={(e) => { setFilterContract(e.target.value); setSelectedClause(null); }}
                  className="w-full text-xs border border-gray-200 rounded-md px-2 py-1.5"
                >
                  <option value="all">All Contracts</option>
                  {contractIds.map((cid) => (
                    <option key={cid} value={cid}>{getContractName(cid)}</option>
                  ))}
                </select>
              </div>
            )}
            <div className="card-body p-0 divide-y divide-gray-100 max-h-[600px] overflow-y-auto">
              {filteredRedlines.length === 0 ? (
                <div className="text-center py-12 text-gray-500">
                  <FileText className="w-10 h-10 mx-auto mb-2 text-gray-300" />
                  <p className="text-sm font-medium">No redline suggestions yet</p>
                  <p className="text-xs mt-1">Go to Contracts and click Generate Redlines</p>
                </div>
              ) : (
                Object.entries(groupedRedlines).map(([contractId, suggestions]) => (
                  <div key={contractId}>
                    {/* Contract header */}
                    <div className="px-4 py-2 bg-gray-50 border-b border-gray-100">
                      <p className="text-xs font-semibold text-navy-700 truncate">
                        <FileText className="w-3 h-3 inline mr-1" />
                        {getContractName(contractId)}
                      </p>
                    </div>
                    {suggestions.map((suggestion) => (
                      <button
                        key={suggestion.suggestion_id}
                        onClick={() => setSelectedClause(suggestion.suggestion_id)}
                        className={`w-full text-left px-4 py-3 hover:bg-gray-50 transition-colors ${
                          selectedClause === suggestion.suggestion_id ? "bg-navy-50 border-l-2 border-navy-900" : ""
                        }`}
                      >
                        <div className="flex items-center justify-between mb-1">
                          <span className="text-xs font-medium text-gray-700 capitalize">{suggestion.clause_type.replace(/_/g, " ")}</span>
                          <span className={`badge text-[10px] ${
                            suggestion.status === "accepted" ? "bg-green-100 text-green-800" :
                            suggestion.status === "rejected" ? "bg-red-100 text-red-800" :
                            "bg-yellow-100 text-yellow-800"
                          }`}>
                            {suggestion.status}
                          </span>
                        </div>
                        <p className="text-xs text-gray-600 line-clamp-2 leading-relaxed">{suggestion.original_text}</p>
                        <div className="flex items-center gap-2 mt-1.5">
                          <span className="text-[10px] text-gray-400 capitalize bg-gray-100 px-1.5 py-0.5 rounded">{suggestion.change_type}</span>
                          <span className="text-[10px] text-gray-400">{Math.round(suggestion.confidence * 100)}% confidence</span>
                        </div>
                      </button>
                    ))}
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Clause Detail */}
          <div className="lg:col-span-2 card">
            {selected ? (
              <div className="p-6 space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <h2 className="text-lg font-semibold text-navy-900">Redline Detail</h2>
                    <p className="text-xs text-gray-500 mt-0.5">
                      <FileText className="w-3 h-3 inline mr-1" />
                      {getContractName(selected.contract_id)}
                    </p>
                  </div>
                  <div className="flex gap-2">
                    {selected.status === "pending" && (
                      <>
                        <button
                          onClick={() => handleAccept(selected.suggestion_id)}
                          disabled={actionLoading === selected.suggestion_id}
                          className="btn-primary text-sm gap-1"
                        >
                          {actionLoading === selected.suggestion_id ? (
                            <Loader2 className="w-3 h-3 animate-spin" />
                          ) : (
                            <CheckCircle className="w-3 h-3" />
                          )}
                          Accept
                        </button>
                        <button
                          onClick={() => handleReject(selected.suggestion_id)}
                          disabled={actionLoading === selected.suggestion_id}
                          className="btn-secondary text-sm gap-1"
                        >
                          <XCircle className="w-3 h-3" />
                          Reject
                        </button>
                      </>
                    )}
                    <a
                      href={api.getExportDocxUrl(selected.suggestion_id)}
                      download
                      className="btn-ghost text-sm gap-1"
                    >
                      <Download className="w-3 h-3" />
                      Export DOCX
                    </a>
                    <a
                      href={api.getExportPdfUrl(selected.suggestion_id)}
                      download
                      className="btn-ghost text-sm gap-1"
                    >
                      <Download className="w-3 h-3" />
                      Export PDF
                    </a>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4 p-4 bg-gray-50 rounded-lg">
                  <div className="col-span-2">
                    <p className="text-xs text-gray-500 mb-1">Contract</p>
                    <p className="font-medium text-sm truncate">{getContractName(selected.contract_id)}</p>
                  </div>
                  <div>
                    <p className="text-xs text-gray-500 mb-1">Change Type</p>
                    <p className="font-medium text-sm capitalize">{selected.change_type}</p>
                  </div>
                  <div>
                    <p className="text-xs text-gray-500 mb-1">Confidence</p>
                    <p className="font-medium text-sm">{Math.round(selected.confidence * 100)}%</p>
                  </div>
                  <div>
                    <p className="text-xs text-gray-500 mb-1">Clause Type</p>
                    <p className="font-medium text-sm capitalize">{selected.clause_type.replace(/_/g, " ")}</p>
                  </div>
                  <div>
                    <p className="text-xs text-gray-500 mb-1">Status</p>
                    <p className="font-medium text-sm capitalize">{selected.status}</p>
                  </div>
                </div>

                <div>
                  <p className="text-xs text-gray-500 mb-2 uppercase tracking-wider font-medium">Original Text</p>
                  <div className="p-4 bg-red-50 border border-red-100 rounded-lg text-sm text-gray-700">
                    {selected.original_text}
                  </div>
                </div>

                <div>
                  <p className="text-xs text-gray-500 mb-2 uppercase tracking-wider font-medium">Proposed Text</p>
                  <div className="p-4 bg-green-50 border border-green-100 rounded-lg text-sm text-gray-700">
                    {selected.proposed_text}
                  </div>
                </div>

                <div className="p-4 bg-navy-50 rounded-lg">
                  <p className="text-xs text-gray-500 mb-1 uppercase tracking-wider font-medium">Rationale</p>
                  <p className="text-sm text-gray-700">{selected.rationale}</p>
                </div>
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center py-16 text-gray-500">
                <Scale className="w-12 h-12 mb-3 text-gray-300" />
                <p className="font-medium">Select a suggestion to review</p>
                <p className="text-sm mt-1">Choose a redline suggestion from the left panel</p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

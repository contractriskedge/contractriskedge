"use client";

import React, { useState, useEffect } from "react";
import { BarChart3, TrendingUp, Database, Loader2 } from "lucide-react";
import { useAuth } from "@/components/auth/AuthProvider";
import * as api from "@/lib/api";

export function BenchmarkPage() {
  const { token } = useAuth();
  const [corpusStats, setCorpusStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!token) return;
    // Try to get benchmark corpus stats
    fetch(`${api.getExportBenchmarksCsvUrl()}`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((res) => {
        if (res.ok) setCorpusStats({ available: true });
        else setCorpusStats({ available: false });
      })
      .catch(() => setCorpusStats({ available: false }))
      .finally(() => setLoading(false));
  }, [token]);

  if (loading) {
    return (
      <div className="space-y-6 animate-pulse">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {[...Array(3)].map((_, i) => <div key={i} className="h-28 bg-gray-200 rounded-xl" />)}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-fade-in">
      <div>
        <h1 className="text-2xl font-bold text-navy-900">Market Benchmarks</h1>
        <p className="text-sm text-gray-500 mt-1">Compare your contract terms against market standards</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="stat-card">
          <Database className="w-5 h-5 text-navy-500 mb-1" />
          <span className="stat-label">Corpus Size</span>
          <span className="stat-value">{corpusStats?.available ? "Available" : "N/A"}</span>
          <span className="stat-trend text-gray-500">Anonymized contracts</span>
        </div>
        <div className="stat-card">
          <BarChart3 className="w-5 h-5 text-navy-500 mb-1" />
          <span className="stat-label">Categories</span>
          <span className="stat-value">12</span>
          <span className="stat-trend text-gray-500">Risk categories</span>
        </div>
        <div className="stat-card">
          <TrendingUp className="w-5 h-5 text-navy-500 mb-1" />
          <span className="stat-label">Status</span>
          <span className={`stat-value text-sm mt-2 ${corpusStats?.available ? "text-risk-low" : "text-risk-medium"}`}>
            {corpusStats?.available ? "Ready" : "Not Loaded"}
          </span>
          <span className="stat-trend text-gray-500">
            {corpusStats?.available ? "● Corpus available" : "Run corpus ingestion first"}
          </span>
        </div>
      </div>
    </div>
  );
}

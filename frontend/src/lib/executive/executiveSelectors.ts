/**
 * Executive selectors — derive widget-level data from the executive dashboard response.
 *
 * Each selector extracts exactly the slice of data a specific widget needs.
 * This keeps widgets simple and the transformation logic testable.
 */

"use client";

import type {
  ExecutiveDashboardData,
  HealthScoreData,
  ExecutiveKpi,
  WidgetDataMap,
  PortfolioSummary,
  CycleTimeAnalytics,
  ReviewerEfficiency,
  SLARiskOverview,
  ContractExposureData,
  ThroughputBottlenecks,
  CostGovernanceData,
  AIQualityGateData,
  BenchmarkAnalyticsData,
  RiskScoreTrendPoint,
  ReviewVolumeTrendPoint,
} from "./executiveTypes";

// ── Widget Data Map ────────────────────────────────────────────────

export function extractWidgetData(
  dashboard: ExecutiveDashboardData | undefined,
  healthScore: HealthScoreData | null | undefined,
): WidgetDataMap {
  if (!dashboard) {
    return {
      healthScore: healthScore ?? null,
      slaRisk: null,
      contractExposure: null,
      reviewerLoad: null,
      bottlenecks: null,
      cycleTime: null,
      negotiationTrends: null,
      portfolioSummary: null,
      costGovernance: null,
      aiQualityGate: null,
      benchmarkAnalytics: null,
      riskScoreTrend: [],
      reviewVolumeTrend: [],
    };
  }

  return {
    healthScore: healthScore ?? null,
    slaRisk: dashboard.sla_risk_overview,
    contractExposure: dashboard.contract_exposure,
    reviewerLoad: dashboard.reviewer_efficiency,
    bottlenecks: dashboard.throughput_bottlenecks,
    cycleTime: dashboard.cycle_time_analytics,
    negotiationTrends: dashboard.negotiation_trends,
    portfolioSummary: dashboard.portfolio_summary,
    costGovernance: dashboard.cost_governance ?? null,
    aiQualityGate: dashboard.ai_quality_gate ?? null,
    benchmarkAnalytics: dashboard.benchmark_analytics ?? null,
    riskScoreTrend: dashboard.risk_score_trend ?? [],
    reviewVolumeTrend: dashboard.review_volume_trend ?? [],
  };
}

// ── KPI Extraction ─────────────────────────────────────────────────

export function extractExecutiveKpis(
  portfolio: PortfolioSummary | undefined,
  cycleTime: CycleTimeAnalytics | undefined,
  slaRisk: SLARiskOverview | undefined,
  bottlenecks: ThroughputBottlenecks | undefined,
  reviewerEfficiency?: ReviewerEfficiency | undefined,
): ExecutiveKpi[] {
  if (!portfolio) return [];

  return [
    {
      id: "active-reviews",
      label: "Active Reviews",
      value: portfolio.active_reviews.toLocaleString(),
      subtitle: `${portfolio.contracts_this_period} new this period`,
      trend: 0,
      trendDirection: "neutral",
      icon: "FileText",
      color: "from-blue-500 to-blue-600",
    },
    {
      id: "high-risk-vendors",
      label: "High-Risk Vendors",
      value: portfolio.high_risk_vendors.toLocaleString(),
      subtitle: `${portfolio.critical_contracts} critical contracts`,
      trend: 0,
      trendDirection: portfolio.high_risk_vendors > 10 ? "up" : "neutral",
      icon: "AlertTriangle",
      color: "from-red-500 to-red-600",
    },
    {
      id: "avg-risk-score",
      label: "Avg Risk Score",
      value: portfolio.avg_risk_score != null ? (portfolio.avg_risk_score).toFixed(1) : "—",
      subtitle: `/10 — ${portfolio.total_contracts} contracts`,
      trend: 0,
      trendDirection: (portfolio.avg_risk_score ?? 0) > 5 ? "up" : "neutral",
      icon: "Brain",
      color: "from-purple-500 to-purple-600",
    },
    {
      id: "sla-breaches",
      label: "SLA Breaches",
      value: slaRisk ? slaRisk.breached.toLocaleString() : "—",
      subtitle: slaRisk ? `${slaRisk.at_risk} at risk` : "",
      trend: 0,
      trendDirection: slaRisk && slaRisk.breached > 0 ? "up" : "neutral",
      icon: "Clock",
      color: "from-amber-500 to-amber-600",
    },
    {
      id: "cycle-time",
      label: "Avg Cycle Time",
      value: cycleTime ? `${cycleTime.overall_avg_days.toFixed(1)}d` : "—",
      subtitle: cycleTime ? `Median: ${cycleTime.median_days.toFixed(1)}d` : "",
      trend: 0,
      trendDirection: cycleTime && cycleTime.overall_avg_days > 5 ? "down" : "neutral",
      icon: "RefreshCw",
      color: "from-teal-500 to-teal-600",
    },
    {
      id: "total-exposure",
      label: "Total Exposure",
      value: `$${((portfolio.total_exposure ?? 0) / 1_000_000).toFixed(1)}M`,
      subtitle: `${portfolio.total_contracts} contracts analyzed`,
      trend: 0,
      trendDirection: (portfolio.total_exposure ?? 0) > 10_000_000 ? "up" : "neutral",
      icon: "DollarSign",
      color: "from-green-500 to-green-600",
    },
    {
      id: "queue-depth",
      label: "Queue Depth",
      value: bottlenecks ? bottlenecks.queue_depth.toLocaleString() : "—",
      subtitle: bottlenecks ? `${bottlenecks.avg_wait_time_hours.toFixed(1)}h avg wait` : "",
      trend: 0,
      trendDirection: bottlenecks && bottlenecks.queue_depth > 20 ? "up" : "neutral",
      icon: "Layers",
      color: "from-indigo-500 to-indigo-600",
    },
    {
      id: "reviewer-load",
      label: "Overloaded Reviewers",
      value: reviewerEfficiency ? reviewerEfficiency.overloaded_reviewers.toLocaleString() : "—",
      subtitle: reviewerEfficiency ? `${reviewerEfficiency.reviewer_backlog} total backlog` : "",
      trend: 0,
      trendDirection: reviewerEfficiency && reviewerEfficiency.overloaded_reviewers > 3 ? "up" : "neutral",
      icon: "Users",
      color: "from-sky-500 to-sky-600",
    },
  ];
}

// ── SLA Risk Summary ───────────────────────────────────────────────

export function extractSLARiskSummary(slaRisk: SLARiskOverview | null | undefined): {
  total: number;
  atRisk: number;
  critical: number;
  breached: number;
  onTrack: number;
  avgRemaining: number;
} {
  if (!slaRisk) {
    return { total: 0, atRisk: 0, critical: 0, breached: 0, onTrack: 0, avgRemaining: 0 };
  }
  return {
    total: slaRisk.total_active_reviews,
    atRisk: slaRisk.at_risk,
    critical: slaRisk.critical,
    breached: slaRisk.breached,
    onTrack: slaRisk.on_track,
    avgRemaining: slaRisk.avg_sla_remaining_pct,
  };
}

// ── Bottleneck Summary ─────────────────────────────────────────────

export function extractBottleneckSummary(bottlenecks: ThroughputBottlenecks | null | undefined): {
  count: number;
  critical: number;
  topBottleneck: string;
  throughput: number;
} {
  if (!bottlenecks || !bottlenecks.bottlenecks) {
    return { count: 0, critical: 0, topBottleneck: "", throughput: 0 };
  }
  const critical = bottlenecks.bottlenecks.filter((b) => b.severity === "critical").length;
  return {
    count: bottlenecks.bottlenecks.length,
    critical,
    topBottleneck: bottlenecks.bottlenecks[0]?.stage ?? "",
    throughput: bottlenecks.overall_throughput,
  };
}

// ── Exposure Summary ───────────────────────────────────────────────

export function extractExposureSummary(exposure: ContractExposureData | null | undefined): {
  score: number;
  topDriver: string;
  concentration: string;
  improving: boolean;
} {
  if (!exposure) {
    return { score: 0, topDriver: "", concentration: "unknown", improving: false };
  }
  return {
    score: exposure.total_exposure_score,
    topDriver: exposure.top_risk_drivers[0]?.clause_type ?? "",
    concentration: exposure.concentration_risk,
    improving: exposure.exposure_trend.length >= 2
      && exposure.exposure_trend[exposure.exposure_trend.length - 1].exposure_score
      < exposure.exposure_trend[0].exposure_score,
  };
}

/**
 * Executive types — shared type definitions for the executive data layer.
 */

"use client";

// ── Top-Level Dashboard ───────────────────────────────────────────

export interface ExecutiveDashboardData {
  portfolio_summary: PortfolioSummary;
  cycle_time_analytics: CycleTimeAnalytics;
  reviewer_efficiency: ReviewerEfficiency;
  sla_risk_overview: SLARiskOverview;
  negotiation_trends: NegotiationTrends;
  contract_exposure: ContractExposureData;
  throughput_bottlenecks: ThroughputBottlenecks;
  cost_governance: CostGovernanceData;
  ai_quality_gate: AIQualityGateData;
  benchmark_analytics: BenchmarkAnalyticsData;
  risk_score_trend: RiskScoreTrendPoint[];
  review_volume_trend: ReviewVolumeTrendPoint[];
  exposure_trend: ExposureTrendPoint[];
  throughput_trend: ThroughputTrendPoint[];
  period: string;
  generated_at: string;
}

// ── Cost Governance ────────────────────────────────────────────────

export interface CostGovernanceData {
  total_ai_reviews: number;
  estimated_ai_cost: number;
  cost_per_contract: number;
  monthly_projection: number;
  trend: CostTrendPoint[];
}

export interface CostTrendPoint {
  period: string;
  ai_reviews: number;
  estimated_cost: number;
}

// ── AI Quality Gate ────────────────────────────────────────────────

export interface AIQualityGateData {
  success_rate: number;
  completed_runs: number;
  failed_runs: number;
  avg_findings: number;
  avg_processing_seconds: number;
}

// ── Benchmark Analytics ────────────────────────────────────────────

export interface BenchmarkAnalyticsData {
  cycle_time_vs_benchmark: string;
  sla_vs_benchmark: string;
  reviewer_efficiency_vs_benchmark: string;
  benchmark_cycle_time_days: number;
  benchmark_sla_pct: number;
  benchmark_reviewer_load: number;
  current_cycle_time_days: number;
  current_sla_pct: number;
  current_reviewer_load: number;
}

// ── Executive Trend Points ─────────────────────────────────────────

export interface RiskScoreTrendPoint {
  period: string;
  avg_risk_score: number;
  contract_count: number;
}

export interface ReviewVolumeTrendPoint {
  period: string;
  reviews_created: number;
  reviews_completed: number;
}

// ── Portfolio ──────────────────────────────────────────────────────

export interface PortfolioSummary {
  total_contracts: number;
  active_reviews: number;
  contracts_this_period: number;
  avg_risk_score: number;
  risk_distribution: RiskDistribution;
  total_exposure: number;
  critical_contracts: number;
  high_risk_vendors: number;
}

export interface RiskDistribution {
  critical: number;
  high: number;
  medium: number;
  low: number;
  info: number;
}

// ── Cycle Time ─────────────────────────────────────────────────────

export interface CycleTimeAnalytics {
  overall_avg_days: number;
  median_days: number;
  p95_days: number;
  by_stage: StageCycleTime[];
  trend: CycleTimeTrendPoint[];
  comparison_to_benchmark: string;
}

export interface StageCycleTime {
  stage: string;
  avg_days: number;
  median_days: number;
  p95_days: number;
  sample_count: number;
}

export interface CycleTimeTrendPoint {
  period: string;
  avg_days: number;
  contract_count: number;
}

// ── Reviewer Efficiency ────────────────────────────────────────────

export interface ReviewerEfficiency {
  total_reviewers: number;
  active_reviewers: number;
  avg_reviews_per_reviewer: number;
  avg_review_completion_hours: number;
  reviewer_backlog: number;
  overloaded_reviewers: number;
  reviewer_details: ReviewerMetric[];
  trend: EfficiencyTrendPoint[];
}

export interface ReviewerMetric {
  reviewer_id: string;
  reviewer_name: string;
  active_reviews: number;
  completed_reviews: number;
  avg_completion_hours: number;
  backlog_hours: number;
  is_overloaded: boolean;
  sla_breach_count: number;
  acceptance_rate: number;
}

export interface EfficiencyTrendPoint {
  period: string;
  avg_completion_hours: number;
  reviews_completed: number;
}

// ── SLA Risk ───────────────────────────────────────────────────────

export interface SLARiskOverview {
  total_active_reviews: number;
  on_track: number;
  at_risk: number;
  critical: number;
  breached: number;
  avg_sla_remaining_pct: number;
  at_risk_reviews: SLARiskItem[];
  breach_prediction: BreachPrediction;
}

export interface SLARiskItem {
  review_id: string;
  document_name: string;
  assigned_to: string;
  status: string;
  sla_deadline: string;
  sla_remaining_pct: number;
  risk_level: string;
  breach_probability: number;
  days_remaining: number;
}

export interface BreachPrediction {
  predicted_breaches_next_7d: number;
  predicted_breaches_next_30d: number;
  high_risk_reviews: string[];
  primary_risk_factors: string[];
}

// ── Negotiation Trends ─────────────────────────────────────────────

export interface NegotiationTrends {
  total_redlines_proposed: number;
  acceptance_rate: number;
  avg_rounds_per_clause: number;
  by_clause_type: ClauseNegotiationMetric[];
  most_contested_clauses: string[];
  trend: NegotiationTrendPoint[];
}

export interface ClauseNegotiationMetric {
  clause_type: string;
  proposed: number;
  accepted: number;
  acceptance_rate: number;
  avg_rounds: number;
  avg_risk_reduction: number;
}

export interface NegotiationTrendPoint {
  period: string;
  proposed: number;
  accepted: number;
  acceptance_rate: number;
}

// ── Contract Exposure ──────────────────────────────────────────────

export interface ContractExposureData {
  total_exposure_score: number;
  by_category: CategoryExposure[];
  top_risk_drivers: RiskDriver[];
  exposure_trend: ExposureTrendPoint[];
  concentration_risk: string;
  top_riskiest_contracts: RiskiestContractItem[];
}

export interface RiskiestContractItem {
  review_id: string;
  document_name: string;
  risk_score: number;
  exposure_score: number;
  top_finding: string;
}

export interface CategoryExposure {
  category: string;
  exposure_score: number;
  exposure_share_pct: number;
  contract_count: number;
  avg_severity: string;
  trend: string;
}

export interface RiskDriver {
  clause_type: string;
  contribution_pct: number;
  severity: string;
  affected_contracts: number;
  recommendation: string;
}

export interface ExposureTrendPoint {
  period: string;
  exposure_score: number;
  contract_count: number;
}

// ── Throughput Bottlenecks ─────────────────────────────────────────

export interface ThroughputBottlenecks {
  bottlenecks: Bottleneck[];
  overall_throughput: number;
  queue_depth: number;
  avg_wait_time_hours: number;
  trend: ThroughputTrendPoint[];
}

export interface Bottleneck {
  stage: string;
  severity: string;
  queue_depth: number;
  avg_wait_time_hours: number;
  resource_constraint: string;
  recommendation: string;
  affected_reviews: number;
}

export interface ThroughputTrendPoint {
  period: string;
  contracts_completed: number;
  avg_cycle_time_days: number;
}

// ── Health Score ───────────────────────────────────────────────────

export interface HealthScoreData {
  composite: number;
  dimensions: HealthDimension[];
  status: "healthy" | "degraded" | "unhealthy";
}

export interface HealthDimension {
  label: string;
  value: number;
  trend: "up" | "down" | "stable";
  history?: number[];
}

// ── KPI Definitions ────────────────────────────────────────────────

export interface ExecutiveKpi {
  id: string;
  label: string;
  value: string;
  subtitle: string;
  trend: number;
  trendDirection: "up" | "down" | "neutral";
  icon: string;
  color: string;
  format?: "currency" | "percentage" | "number" | "days";
}

// ── Widget Data Map ────────────────────────────────────────────────

export interface WidgetDataMap {
  healthScore: HealthScoreData | null;
  slaRisk: SLARiskOverview | null;
  contractExposure: ContractExposureData | null;
  reviewerLoad: ReviewerEfficiency | null;
  bottlenecks: ThroughputBottlenecks | null;
  cycleTime: CycleTimeAnalytics | null;
  negotiationTrends: NegotiationTrends | null;
  portfolioSummary: PortfolioSummary | null;
  costGovernance: CostGovernanceData | null;
  aiQualityGate: AIQualityGateData | null;
  benchmarkAnalytics: BenchmarkAnalyticsData | null;
  riskScoreTrend: RiskScoreTrendPoint[];
  reviewVolumeTrend: ReviewVolumeTrendPoint[];
}

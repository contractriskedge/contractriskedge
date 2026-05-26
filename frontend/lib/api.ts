const API_BASE = process.env.NEXT_PUBLIC_API_URL || "/api/v1";

interface FetchOptions extends RequestInit {
  token?: string;
}

async function fetchApi<T>(path: string, options: FetchOptions = {}): Promise<T> {
  const { token, ...fetchOpts } = options;

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(fetchOpts.headers as Record<string, string>),
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_BASE}${path}`, {
    ...fetchOpts,
    headers,
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail || `API error: ${res.status}`);
  }

  return res.json();
}

// ── Auth ──

export async function getAuthToken(): Promise<string> {
  const stored = localStorage.getItem("auth_token");
  if (stored) return stored;

  const res = await fetch(`${API_BASE}/auth/token`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
  });
  const data = await res.json();
  localStorage.setItem("auth_token", data.access_token);
  return data.access_token;
}

// ── Contracts ──

export interface Contract {
  contract_id: string;
  filename: string;
  status: string;
  contract_type: string;
  risk_score?: number;
  counterparty?: string;
  total_pages?: number;
  created_at: string;
  tags?: string[];
}

export async function listContracts(token: string): Promise<{ contracts: Contract[]; total: number }> {
  return fetchApi("/contracts/", { token });
}

// ── Risks ──

export interface LinkedEvidence {
  clause_reference: string;
  excerpt: string;
  page_number?: number;
  section?: string;
  relevance_score: number;
}

export interface JurisdictionalConsideration {
  jurisdiction: string;
  rule_reference: string;
  risk_modifier: number;
  explanation: string;
}

export interface RiskFlag {
  risk_flag_id: string;
  contract_id: string;
  clause_text: string;
  risk_category: string;
  severity: number;
  confidence: string;
  rationale: string;
  page_number?: number;
  // 8-field explainability fields
  why_flagged?: string;
  potential_business_impact?: string;
  market_benchmark_comparison?: string;
  confidence_score?: number;
  confidence_label?: string;
  suggested_remediation?: string;
  linked_evidence?: LinkedEvidence[];
  jurisdictional_considerations?: JurisdictionalConsideration[];
}

export interface RiskAnalysisResult {
  report_id: string;
  status: string;
  status_url: string;
  total_clauses?: number;
}

export interface RiskReport {
  report_id: string;
  contract_id: string;
  status: string;
  progress?: number;
  results?: any;
  summary?: {
    total_clauses: number;
    analyzed: number;
    avg_severity: number;
    high_risk_count: number;
    medium_risk_count: number;
  };
  created_at: string;
  completed_at?: string;
  error?: string;
}

export async function analyzeContractRisks(
  token: string,
  contractId: string,
  categories?: string[]
): Promise<RiskAnalysisResult> {
  const params = new URLSearchParams({ contract_id: contractId });
  if (categories) categories.forEach((c) => params.append("categories", c));
  return fetchApi(`/risks/analyze?${params}`, { method: "POST", token });
}

export async function getRiskReport(token: string, reportId: string): Promise<RiskReport> {
  return fetchApi(`/risks/${reportId}`, { token });
}

export async function listRisks(token: string, contractId?: string): Promise<{ risks: RiskFlag[]; total: number }> {
  const path = contractId ? `/risks/?contract_id=${contractId}` : "/risks/";
  return fetchApi(path, { token });
}

// ── Redlines ──

export interface RedlineSuggestion {
  suggestion_id: string;
  contract_id: string;
  clause_type: string;
  original_text: string;
  proposed_text: string;
  change_type: string;
  rationale: string;
  confidence: number;
  status: string;
  created_at: string;
}

export async function listRedlines(token: string): Promise<{ suggestions: RedlineSuggestion[]; total: number }> {
  return fetchApi("/redlines/suggest", { token });
}

export async function createRedlineSuggestion(
  token: string,
  contractId: string,
  clauseType: string,
  originalClauseText: string,
  partyRole: string = "buyer",
  dealSizeTier: string = "medium",
  industry: string = "technology",
  counterpartyAggressiveness: string = "moderate",
  jurisdiction: string = "New York, USA"
): Promise<RedlineSuggestion> {
  return fetchApi("/redlines/suggest", {
    method: "POST",
    token,
    body: JSON.stringify({
      contract_id: contractId,
      clause_type: clauseType,
      original_clause_text: originalClauseText,
      party_role: partyRole,
      deal_size_tier: dealSizeTier,
      industry: industry,
      counterparty_aggressiveness: counterpartyAggressiveness,
      jurisdiction: jurisdiction,
    }),
  });
}

export async function acceptRedlineSuggestion(token: string, suggestionId: string): Promise<void> {
  await fetchApi(`/redlines/suggest/${suggestionId}/accept`, { method: "POST", token });
}

export async function rejectRedlineSuggestion(token: string, suggestionId: string, comment?: string): Promise<void> {
  const params = comment ? `?comment=${encodeURIComponent(comment)}` : "";
  await fetchApi(`/redlines/suggest/${suggestionId}/reject${params}`, { method: "POST", token });
}

// ── Benchmarks ──

export interface BenchmarkScore {
  scored: boolean;
  percentile?: number;
  classification?: string;
  clause_type: string;
}

export async function getBenchmarkScore(
  token: string,
  clauseText: string,
  clauseType: string
): Promise<BenchmarkScore> {
  return fetchApi(
    `/benchmarks/score?clause_text=${encodeURIComponent(clauseText)}&clause_type=${encodeURIComponent(clauseType)}`,
    { token }
  );
}

// ── Evaluation ──

export interface EvaluationMetrics {
  overall_accuracy: number;
  macro_f1: number;
  severity_mae: number;
  false_positive_rate: number;
}

export async function getEvaluationMetrics(token: string): Promise<{
  status: string;
  metrics: EvaluationMetrics;
  history: any[];
}> {
  return fetchApi("/evaluation/metrics", { token });
}

// ── Ingestion / Upload ──

export interface IngestionJobResult {
  job_id: string;
  document_id: string;
  status: string;
  status_url: string;
  filename: string;
}

export interface BatchUploadResult {
  filename: string;
  job_id: string;
  document_id: string;
  status: string;
  error?: string;
}

export interface BatchUploadResponse {
  batch_id: string;
  total: number;
  accepted: number;
  failed: number;
  results: BatchUploadResult[];
}

export async function uploadDocument(
  token: string,
  file: File,
  enableOcr: boolean = false
): Promise<IngestionJobResult> {
  const formData = new FormData();
  formData.append("file", file);
  const params = new URLSearchParams({ enable_ocr: String(enableOcr) });

  const res = await fetch(`${API_BASE}/ingest/upload?${params}`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: formData,
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail || `Upload failed: ${res.status}`);
  }
  return res.json();
}

export async function batchUploadDocuments(
  token: string,
  files: File[],
  enableOcr: boolean = false
): Promise<BatchUploadResponse> {
  const formData = new FormData();
  files.forEach((f) => formData.append("files", f));
  const params = new URLSearchParams({ enable_ocr: String(enableOcr) });

  const res = await fetch(`${API_BASE}/ingest/batch-upload?${params}`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: formData,
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail || `Batch upload failed: ${res.status}`);
  }
  return res.json();
}

export async function getIngestionStatus(token: string, jobId: string): Promise<{
  job_id: string;
  status: string;
  progress: number;
  error_message?: string;
}> {
  return fetchApi(`/ingest/status/${jobId}`, { token });
}

// ── Export ──

export function getExportDocxUrl(suggestionId: string): string {
  return `${API_BASE}/export/redlines/${suggestionId}/docx`;
}

export function getExportPdfUrl(suggestionId: string): string {
  return `${API_BASE}/export/redlines/${suggestionId}/pdf`;
}

export async function downloadExportCsv(token: string, url: string, filename: string): Promise<void> {
  const res = await fetch(url, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error(`Export failed: ${res.status}`);
  const blob = await res.blob();
  const blobUrl = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = blobUrl;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(blobUrl);
}

export function getExportAuditCsvUrl(): string {
  return `${API_BASE}/export/audit/csv`;
}

export function getExportBenchmarksCsvUrl(): string {
  return `${API_BASE}/export/benchmarks/csv`;
}

export function getExportProcurementCsvUrl(): string {
  return `${API_BASE}/export/procurement/csv`;
}

// ── Playbooks ──

export interface Playbook {
  playbook_id: string;
  name: string;
  description: string;
  contract_types: string[];
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface PlaybookRule {
  rule_id: string;
  clause_type: string;
  condition: string;
  value: string;
  action: string;
  action_value: string;
  priority: number;
  enabled: boolean;
}

export async function listPlaybooks(token: string): Promise<Playbook[]> {
  return fetchApi("/playbooks", { token });
}

export async function getPlaybook(token: string, playbookId: string): Promise<Playbook & { versions: any[] }> {
  return fetchApi(`/playbooks/${playbookId}`, { token });
}

export async function createPlaybook(token: string, data: {
  name: string; description?: string; contract_types?: string[];
}): Promise<Playbook> {
  return fetchApi("/playbooks", {
    method: "POST",
    token,
    body: JSON.stringify(data),
  });
}

export async function listPlaybookRules(token: string, playbookId: string): Promise<PlaybookRule[]> {
  return fetchApi(`/playbooks/${playbookId}/rules`, { token });
}

export async function addPlaybookRule(token: string, playbookId: string, rule: {
  clause_type: string; condition: string; value: string;
  action: string; action_value: string; priority?: number;
}): Promise<PlaybookRule> {
  return fetchApi(`/playbooks/${playbookId}/rules`, {
    method: "POST",
    token,
    body: JSON.stringify(rule),
  });
}

// ── Monitoring ──

export async function getMonitoringMetrics(token: string): Promise<any> {
  return fetchApi("/monitoring/metrics", { token });
}

export async function getDetailedHealth(token: string): Promise<any> {
  return fetchApi("/monitoring/health/detailed", { token });
}

// ── Enterprise Document Ingestion & Import Center Types ──────────────────

export type RiskLevel = "critical" | "high" | "medium" | "low" | "info";

export type IngestionSource = "local" | "sharepoint" | "googledrive" | "box" | "onedrive" | "dropbox" | "email" | "sftp" | "api" | "slack";
export type ProcessingStage = "uploading" | "queued" | "ocr" | "classifying" | "extracting" | "validating" | "relationships" | "review" | "completed" | "failed";
export type ImportJobStatus = "running" | "completed" | "failed" | "cancelled" | "pending" | "paused";
export type DocumentType = "contract" | "amendment" | "sla" | "dpa" | "nda" | "license" | "addendum" | "correspondence" | "invoice" | "other";
export type ReviewStatus = "pending" | "approved" | "rejected" | "needs_review";

// ── Ingestion KPI ────────────────────────────────────────────────────────

export interface IngestionKpi {
  id: string; label: string; value: string; trend: number;
  trendDirection: "up" | "down" | "neutral";
  icon: string; color: string; severity: "critical" | "warning" | "success" | "info";
  sparklineData: number[]; tooltip: string;
}

// ── Import Source ────────────────────────────────────────────────────────

export interface ImportSource {
  id: string;
  name: string;
  type: IngestionSource;
  icon: string;
  connected: boolean;
  lastSync: string;
  documentCount: number;
  status: "active" | "error" | "disconnected" | "syncing";
}

// ── Processing Pipeline ──────────────────────────────────────────────────

export interface PipelineStage {
  id: ProcessingStage;
  label: string;
  status: "pending" | "active" | "completed" | "failed" | "skipped";
  startedAt?: string;
  completedAt?: string;
  progress: number;
  confidence?: number;
  error?: string;
}

// ── Import Job ───────────────────────────────────────────────────────────

export interface ImportJob {
  id: string;
  /** Set when this job is backed by POST /api/v1/uploads (real ingestion pipeline). */
  backendUploadId?: string;
  fileName: string;
  fileSize: number;
  fileType: string;
  source: IngestionSource;
  sourceLabel: string;
  status: ImportJobStatus;
  pipeline: PipelineStage[];
  documentType: DocumentType;
  confidence: number;
  ocrAccuracy: number;
  classificationScore: number;
  extractionScore: number;
  duplicateScore?: number;
  isDuplicate: boolean;
  duplicateOf?: string;
  metadata: ExtractedMetadata;
  validation: ValidationResult[];
  error?: string;
  createdAt: string;
  updatedAt: string;
  completedAt?: string;
  submittedBy: string;
  priority: "high" | "medium" | "low";
}

// ── Extracted Metadata ───────────────────────────────────────────────────

export interface ExtractedMetadata {
  contractTitle: string;
  counterparty: string;
  contractType: DocumentType;
  effectiveDate: string;
  expirationDate: string;
  jurisdiction: string;
  governingLaw: string;
  businessUnit: string;
  value: string;
  currency: string;
  status: string;
  description: string;
  [key: string]: string;
}

// ── Validation Result ────────────────────────────────────────────────────

export interface ValidationResult {
  id: string;
  field: string;
  type: "error" | "warning" | "info" | "success";
  message: string;
  suggestedValue?: string;
  confidence: number;
  actionable: boolean;
}

// ── AI Extraction Insight ────────────────────────────────────────────────

export interface AiExtractionInsight {
  id: string;
  type: "classification" | "relationship" | "anomaly" | "quality" | "suggestion" | "duplicate";
  title: string;
  description: string;
  confidence: number;
  severity: "critical" | "warning" | "info" | "success";
  affectedField?: string;
  suggestedAction?: string;
}

// ── Duplicate Detection ──────────────────────────────────────────────────

export interface DuplicateGroup {
  id: string;
  documents: { id: string; name: string; similarity: number; }[];
  reason: string;
  aiConfidence: number;
  resolved: boolean;
}

// ── Processing Queue ─────────────────────────────────────────────────────

export interface ProcessingQueue {
  id: string;
  name: string;
  status: "active" | "paused" | "idle";
  pendingCount: number;
  processingCount: number;
  completedCount: number;
  failedCount: number;
  throughput: number;
  avgLatency: number;
}

// ── Ingestion Analytics ──────────────────────────────────────────────────

export interface IngestionAnalytics {
  totalProcessed: number;
  totalFailed: number;
  avgOcrAccuracy: number;
  avgExtractionConfidence: number;
  avgProcessingTime: number;
  throughputHistory: { date: string; count: number; }[];
  ocrAccuracyTrend: { date: string; accuracy: number; }[];
  extractionConfidenceTrend: { date: string; confidence: number; }[];
  sourceDistribution: { source: string; count: number; }[];
  failureReasons: { reason: string; count: number; }[];
  documentTypeDistribution: { type: string; count: number; }[];
  processingTimeDistribution: { range: string; count: number; }[];
  queueHealth: ProcessingQueue[];
}

// ── Failed Import ────────────────────────────────────────────────────────

export interface FailedImport {
  id: string;
  fileName: string;
  error: string;
  errorType: "ocr" | "classification" | "extraction" | "validation" | "network" | "format" | "duplicate";
  failedStage: ProcessingStage;
  retryCount: number;
  maxRetries: number;
  canRetry: boolean;
  aiRepairSuggestion?: string;
  submittedBy: string;
  failedAt: string;
  fileSize: number;
}

// ── Import Template ──────────────────────────────────────────────────────

export interface ImportTemplate {
  id: string;
  name: string;
  description: string;
  source: IngestionSource;
  documentType: DocumentType;
  autoClassify: boolean;
  autoExtract: boolean;
  runValidation: boolean;
  detectRelationships: boolean;
  confidenceThreshold: number;
  createdBy: string;
  usageCount: number;
  lastUsed: string;
}

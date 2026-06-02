// ── Enterprise Document Ingestion & Import Center Mock Data ──────────────

import type {
  CompactKpi, ImportSource, ImportJob, ProcessingQueue, FailedImport,
  ImportTemplate, AiExtractionInsight, DuplicateGroup, IngestionAnalytics,
  PipelineStage, ValidationResult, ExtractedMetadata,
} from "./types";

// ── KPI Data ─────────────────────────────────────────────────────────────

export const mockCompactKpis: CompactKpi[] = [
  { id: "uploaded-today", label: "Uploaded Today", value: "24,892", trend: 12, trendDirection: "up", icon: "Upload", severity: "info", tooltip: "24,892 documents uploaded today" },
  { id: "processing-queue", label: "Processing Queue", value: "234", trend: -22, trendDirection: "down", icon: "ListOrdered", severity: "info", tooltip: "234 documents in processing queue" },
  { id: "failed-jobs", label: "Failed Jobs", value: "28", trend: -35, trendDirection: "down", icon: "AlertTriangle", severity: "critical", tooltip: "28 failed imports" },
  { id: "avg-processing-time", label: "Avg Processing Time", value: "2.4m", trend: -8, trendDirection: "down", icon: "Clock", severity: "info", tooltip: "Average processing time per document" },
  { id: "ocr-accuracy", label: "OCR Accuracy", value: "97.4%", trend: 1.8, trendDirection: "up", icon: "ScanEye", severity: "success", tooltip: "97.4% average OCR accuracy" },
  { id: "high-risk-contracts", label: "High Risk Contracts", value: "12", trend: -5, trendDirection: "down", icon: "ShieldAlert", severity: "warning", tooltip: "12 contracts flagged as high risk" },
];

// ── Import Sources ───────────────────────────────────────────────────────

export const mockImportSources: ImportSource[] = [
  { id: "src1", name: "Local Uploads", type: "local", icon: "Upload", connected: true, lastSync: "2026-05-15T10:30:00Z", documentCount: 8924, status: "active" },
  { id: "src2", name: "SharePoint - Legal Docs", type: "sharepoint", icon: "Share2", connected: true, lastSync: "2026-05-15T09:45:00Z", documentCount: 6842, status: "active" },
  { id: "src3", name: "Google Drive - Contracts", type: "googledrive", icon: "Cloud", connected: true, lastSync: "2026-05-15T08:30:00Z", documentCount: 3210, status: "active" },
  { id: "src4", name: "Box - Vendor Agreements", type: "box", icon: "Box", connected: false, lastSync: "2026-05-14T16:00:00Z", documentCount: 1892, status: "disconnected" },
  { id: "src5", name: "Email - Contract Inbox", type: "email", icon: "Mail", connected: true, lastSync: "2026-05-15T10:25:00Z", documentCount: 1456, status: "syncing" },
  { id: "src6", name: "SFTP - Partner Portal", type: "sftp", icon: "Server", connected: true, lastSync: "2026-05-15T07:00:00Z", documentCount: 2568, status: "active" },
];

// ── Processing Queues ────────────────────────────────────────────────────

export const mockProcessingQueues: ProcessingQueue[] = [
  { id: "q1", name: "Main Ingestion", status: "active", pendingCount: 89, processingCount: 6, completedCount: 18432, failedCount: 28, throughput: 145, avgLatency: 3200 },
  { id: "q2", name: "OCR Processing", status: "active", pendingCount: 45, processingCount: 4, completedCount: 18200, failedCount: 12, throughput: 89, avgLatency: 4800 },
  { id: "q3", name: "AI Classification", status: "active", pendingCount: 67, processingCount: 3, completedCount: 18432, failedCount: 8, throughput: 62, avgLatency: 2100 },
  { id: "q4", name: "Metadata Extraction", status: "active", pendingCount: 34, processingCount: 5, completedCount: 17650, failedCount: 15, throughput: 78, avgLatency: 3500 },
  { id: "q5", name: "Validation Queue", status: "paused", pendingCount: 128, processingCount: 0, completedCount: 16500, failedCount: 22, throughput: 0, avgLatency: 0 },
  { id: "q6", name: "Human Review", status: "active", pendingCount: 56, processingCount: 2, completedCount: 3200, failedCount: 5, throughput: 12, avgLatency: 120000 },
];

// ── Pipeline Stages ──────────────────────────────────────────────────────

const makePipeline = (status: "completed" | "failed" | "running"): PipelineStage[] => {
  const stages: PipelineStage[] = [
    { id: "uploading", label: "Upload", status: "completed", startedAt: "2026-05-15T10:00:00Z", completedAt: "2026-05-15T10:00:02Z", progress: 100 },
    { id: "queued", label: "Queue", status: "completed", startedAt: "2026-05-15T10:00:02Z", completedAt: "2026-05-15T10:00:05Z", progress: 100 },
    { id: "ocr", label: "OCR Processing", status: status === "failed" && Math.random() > 0.7 ? "failed" : "completed", startedAt: "2026-05-15T10:00:05Z", completedAt: status !== "running" ? "2026-05-15T10:00:35Z" : undefined, progress: status === "running" ? 65 : 100, confidence: status === "completed" ? 97.4 : undefined },
    { id: "classifying", label: "AI Classification", status: status === "failed" && Math.random() > 0.8 ? "failed" : "completed", startedAt: "2026-05-15T10:00:35Z", completedAt: status !== "running" ? "2026-05-15T10:00:42Z" : undefined, progress: status === "running" ? 40 : 100, confidence: status === "completed" ? 93.2 : undefined },
    { id: "extracting", label: "Metadata Extraction", status: status === "failed" && Math.random() > 0.85 ? "failed" : status === "running" ? "active" : "completed", startedAt: "2026-05-15T10:00:42Z", completedAt: status === "completed" ? "2026-05-15T10:01:15Z" : undefined, progress: status === "running" ? 25 : 100, confidence: status === "completed" ? 91.5 : undefined },
    { id: "validating", label: "Validation", status: status === "running" ? "pending" : "completed", progress: status === "running" ? 0 : 100, confidence: status === "completed" ? 88.9 : undefined },
    { id: "relationships", label: "Relationships", status: status === "running" ? "pending" : "completed", progress: status === "running" ? 0 : 100, confidence: 85.2 },
    { id: "review", label: "Final Review", status: status === "running" ? "pending" : "pending", progress: 0 },
  ];
  if (status === "completed") stages[stages.length - 1].status = "completed";
  return stages;
};

// ── Validation Results ───────────────────────────────────────────────────

const mockValidations: ValidationResult[] = [
  { id: "v1", field: "contractTitle", type: "success", message: "Title extracted successfully", confidence: 98, actionable: false },
  { id: "v2", field: "counterparty", type: "warning", message: "Counterparty name may be abbreviated. Expected: 'Acme Corporation', Found: 'Acme Corp'", suggestedValue: "Acme Corporation", confidence: 82, actionable: true },
  { id: "v3", field: "effectiveDate", type: "success", message: "Date parsed successfully", confidence: 96, actionable: false },
  { id: "v4", field: "jurisdiction", type: "warning", message: "Jurisdiction not explicitly stated. Inferred from governing law clause.", suggestedValue: "Delaware, USA", confidence: 74, actionable: true },
  { id: "v5", field: "value", type: "error", message: "Contract value not found in document. May be in a separate exhibit.", confidence: 45, actionable: true },
  { id: "v6", field: "expirationDate", type: "info", message: "Auto-renewal clause detected. Expiration date may change upon renewal.", confidence: 88, actionable: false },
];

// ── Extracted Metadata ───────────────────────────────────────────────────

const mockMetadata: ExtractedMetadata = {
  contractTitle: "Master Service Agreement",
  counterparty: "Acme Corp",
  contractType: "contract",
  effectiveDate: "2026-01-15",
  expirationDate: "2028-01-14",
  jurisdiction: "Delaware",
  governingLaw: "Delaware",
  businessUnit: "Enterprise Technology",
  value: "$2,400,000",
  currency: "USD",
  status: "Active",
  description: "Enterprise software licensing and professional services agreement",
};

// ── AI Extraction Insights ───────────────────────────────────────────────

export const mockExtractionInsights: AiExtractionInsight[] = [
  { id: "ei1", type: "classification", title: "Contract Type Confirmed", description: "Document classified as Master Service Agreement with 96% confidence. Matches MSA template #204.", confidence: 96, severity: "success", affectedField: "contractType" },
  { id: "ei2", type: "relationship", title: "Amendment Relationship Detected", description: "This document appears to be Amendment 3 to MSA-204. Consider linking to parent agreement.", confidence: 88, severity: "info", affectedField: "relationships", suggestedAction: "Link to MSA-204" },
  { id: "ei3", type: "quality", title: "OCR Quality Alert - Page 7", description: "Page 7 has smudged text in signature block. OCR confidence dropped to 72%. Recommend manual review.", confidence: 72, severity: "warning", affectedField: "ocr", suggestedAction: "Review page 7 manually" },
  { id: "ei4", type: "anomaly", title: "Missing Standard Clauses", description: "Document missing standard 'Force Majeure' and 'Confidentiality' clauses. May be incomplete.", confidence: 85, severity: "warning", affectedField: "clauses", suggestedAction: "Flag for completeness review" },
  { id: "ei5", type: "duplicate", title: "Possible Duplicate Detected", description: "85% semantic similarity with 'MSA-204_Acme_Corp_v2.pdf'. Check if this is a newer version.", confidence: 85, severity: "info", affectedField: "duplicate", suggestedAction: "Compare with MSA-204_Acme_Corp_v2.pdf" },
  { id: "ei6", type: "suggestion", title: "Metadata Enhancement Available", description: "Suggestion to extract 'Payment Terms: Net 30' from Section 5.1. Add as custom field?", confidence: 91, severity: "info", affectedField: "metadata", suggestedAction: "Add Payment Terms field" },
];

// ── Duplicate Groups ─────────────────────────────────────────────────────

export const mockDuplicateGroups: DuplicateGroup[] = [
  { id: "dg1", documents: [{ id: "job-001", name: "MSA-204_Acme_Corp.pdf", similarity: 100 }, { id: "job-015", name: "MSA-204_Acme_Corp_v2.pdf", similarity: 85 }, { id: "job-032", name: "ACME_MSA_2026_FINAL.pdf", similarity: 78 }], reason: "Identical content with minor formatting differences", aiConfidence: 94, resolved: false },
  { id: "dg2", documents: [{ id: "job-008", name: "DPA_TechSphere_v1.pdf", similarity: 100 }, { id: "job-022", name: "Data_Processing_Agreement_TechSphere.pdf", similarity: 92 }], reason: "Same DPA uploaded twice from different sources", aiConfidence: 97, resolved: true },
  { id: "dg3", documents: [{ id: "job-012", name: "SLA_CloudNexus.pdf", similarity: 100 }, { id: "job-028", name: "CloudNexus_SLA_2026_signed.pdf", similarity: 82 }], reason: "Version 2 detected - supersedes original", aiConfidence: 89, resolved: false },
];

// ── Import Jobs ──────────────────────────────────────────────────────────

export const mockImportJobs: ImportJob[] = [
  { id: "job-001", fileName: "MSA-204_Acme_Corp.pdf", fileSize: 2450000, fileType: "application/pdf", source: "local", sourceLabel: "Local Upload", status: "completed", pipeline: makePipeline("completed"), documentType: "contract", confidence: 96, ocrAccuracy: 98.2, classificationScore: 96.5, extractionScore: 93.8, duplicateScore: 12, isDuplicate: false, metadata: { ...mockMetadata, contractTitle: "Master Service Agreement - Acme Corp" }, validation: mockValidations.slice(0, 3), createdAt: "2026-05-15T10:00:00Z", updatedAt: "2026-05-15T10:02:30Z", completedAt: "2026-05-15T10:02:30Z", submittedBy: "Sarah Chen", priority: "high" },
  { id: "job-002", fileName: "DPA_TechSphere_Inc.pdf", fileSize: 890000, fileType: "application/pdf", source: "sharepoint", sourceLabel: "SharePoint - Legal Docs", status: "running", pipeline: makePipeline("running"), documentType: "dpa", confidence: 88, ocrAccuracy: 95.6, classificationScore: 91.2, extractionScore: 84.5, duplicateScore: 8, isDuplicate: false, metadata: { ...mockMetadata, contractTitle: "Data Processing Agreement", counterparty: "TechSphere Inc", value: "$0" }, validation: mockValidations.slice(0, 2), createdAt: "2026-05-15T10:05:00Z", updatedAt: "2026-05-15T10:06:30Z", submittedBy: "Michael Torres", priority: "high" },
  { id: "job-003", fileName: "SLA_CloudNexus_2026.docx", fileSize: 1200000, fileType: "application/vnd.openxmlformats-officedocument.wordprocessingml.document", source: "googledrive", sourceLabel: "Google Drive - Contracts", status: "failed", pipeline: makePipeline("failed"), documentType: "sla", confidence: 65, ocrAccuracy: 88.3, classificationScore: 72.1, extractionScore: 58.4, duplicateScore: 15, isDuplicate: false, metadata: { ...mockMetadata, contractTitle: "Service Level Agreement", counterparty: "CloudNexus", value: "$890,000" }, validation: [{ id: "v7", field: "ocr", type: "error", message: "OCR failed on pages 4-6: corrupted image data", confidence: 45, actionable: true }], error: "OCR processing failed: image corruption detected in pages 4-6", createdAt: "2026-05-15T09:45:00Z", updatedAt: "2026-05-15T09:47:30Z", submittedBy: "System", priority: "high" },
  { id: "job-004", fileName: "NDA_DataVault_Systems.pdf", fileSize: 450000, fileType: "application/pdf", source: "email", sourceLabel: "Email - Contract Inbox", status: "completed", pipeline: makePipeline("completed"), documentType: "nda", confidence: 94, ocrAccuracy: 99.1, classificationScore: 97.8, extractionScore: 92.3, duplicateScore: 5, isDuplicate: false, metadata: { ...mockMetadata, contractTitle: "Non-Disclosure Agreement", counterparty: "DataVault Systems", value: "$0", expirationDate: "2027-05-14" }, validation: mockValidations.slice(0, 4), createdAt: "2026-05-15T09:30:00Z", updatedAt: "2026-05-15T09:32:15Z", completedAt: "2026-05-15T09:32:15Z", submittedBy: "System", priority: "medium" },
  { id: "job-005", fileName: "Amendment_3_MSA-204.pdf", fileSize: 320000, fileType: "application/pdf", source: "sftp", sourceLabel: "SFTP - Partner Portal", status: "completed", pipeline: makePipeline("completed"), documentType: "amendment", confidence: 91, ocrAccuracy: 97.5, classificationScore: 94.2, extractionScore: 89.7, duplicateScore: 18, isDuplicate: false, metadata: { ...mockMetadata, contractTitle: "Amendment 3 to MSA-204", counterparty: "Acme Corp", value: "$350,000" }, validation: mockValidations, createdAt: "2026-05-15T09:15:00Z", updatedAt: "2026-05-15T09:17:45Z", completedAt: "2026-05-15T09:17:45Z", submittedBy: "System", priority: "high" },
  { id: "job-006", fileName: "Acme_Corp_MSA_v2_duplicate.pdf", fileSize: 2400000, fileType: "application/pdf", source: "local", sourceLabel: "Local Upload", status: "completed", pipeline: makePipeline("completed"), documentType: "contract", confidence: 78, ocrAccuracy: 97.8, classificationScore: 95.1, extractionScore: 92.4, duplicateScore: 85, isDuplicate: true, duplicateOf: "job-001", metadata: { ...mockMetadata, contractTitle: "Master Service Agreement - Acme Corp" }, validation: [{ id: "v8", field: "duplicate", type: "warning", message: "85% match with existing document MSA-204_Acme_Corp.pdf", suggestedValue: "Mark as duplicate", confidence: 85, actionable: true }], createdAt: "2026-05-15T08:45:00Z", updatedAt: "2026-05-15T08:47:30Z", completedAt: "2026-05-15T08:47:30Z", submittedBy: "Emily Nakamura", priority: "low" },
  { id: "job-007", fileName: "License_Agreement_SecurePath.pdf", fileSize: 1800000, fileType: "application/pdf", source: "sharepoint", sourceLabel: "SharePoint - Legal Docs", status: "pending", pipeline: makePipeline("running").map(s => ({ ...s, status: "pending" as const, progress: 0 })), documentType: "license", confidence: 0, ocrAccuracy: 0, classificationScore: 0, extractionScore: 0, duplicateScore: 0, isDuplicate: false, metadata: { ...mockMetadata, contractTitle: "Software License Agreement", counterparty: "SecurePath Ltd", value: "$1,200,000" }, validation: [], createdAt: "2026-05-15T10:10:00Z", updatedAt: "2026-05-15T10:10:00Z", submittedBy: "David Park", priority: "medium" },
  { id: "job-008", fileName: "Correspondence_Acme_Legal.pdf", fileSize: 210000, fileType: "application/pdf", source: "email", sourceLabel: "Email - Contract Inbox", status: "failed", pipeline: makePipeline("failed"), documentType: "correspondence", confidence: 35, ocrAccuracy: 92.1, classificationScore: 45.3, extractionScore: 28.7, duplicateScore: 0, isDuplicate: false, metadata: { ...mockMetadata, contractTitle: "Legal Correspondence", counterparty: "Acme Corp", value: "$0" }, validation: [{ id: "v9", field: "type", type: "error", message: "Document type 'correspondence' not supported for full extraction", confidence: 95, actionable: false }], error: "Unsupported document type for AI extraction pipeline", createdAt: "2026-05-15T08:30:00Z", updatedAt: "2026-05-15T08:32:00Z", submittedBy: "System", priority: "low" },
  { id: "job-009", fileName: "GDPR_DPA_Addendum.pdf", fileSize: 560000, fileType: "application/pdf", source: "googledrive", sourceLabel: "Google Drive - Contracts", status: "completed", pipeline: makePipeline("completed"), documentType: "addendum", confidence: 93, ocrAccuracy: 98.5, classificationScore: 95.8, extractionScore: 90.2, duplicateScore: 0, isDuplicate: false, metadata: { ...mockMetadata, contractTitle: "GDPR Data Processing Addendum", counterparty: "Multiple", value: "$0" }, validation: mockValidations.slice(0, 3), createdAt: "2026-05-15T08:00:00Z", updatedAt: "2026-05-15T08:02:45Z", completedAt: "2026-05-15T08:02:45Z", submittedBy: "Sarah Chen", priority: "high" },
  { id: "job-010", fileName: "Invoice_Q2_2026_Acme.pdf", fileSize: 180000, fileType: "application/pdf", source: "sftp", sourceLabel: "SFTP - Partner Portal", status: "completed", pipeline: makePipeline("completed"), documentType: "invoice", confidence: 72, ocrAccuracy: 96.3, classificationScore: 78.5, extractionScore: 65.2, duplicateScore: 0, isDuplicate: false, metadata: { ...mockMetadata, contractTitle: "Q2 2026 Invoice", counterparty: "Acme Corp", value: "$400,000" }, validation: [{ id: "v10", field: "type", type: "info", message: "Invoice routed to AP system. Not indexed in contract repository.", confidence: 95, actionable: false }], createdAt: "2026-05-15T07:30:00Z", updatedAt: "2026-05-15T07:32:30Z", completedAt: "2026-05-15T07:32:30Z", submittedBy: "System", priority: "low" },
];

// ── Failed Imports ───────────────────────────────────────────────────────

export const mockFailedImports: FailedImport[] = [
  { id: "fail-001", fileName: "SLA_CloudNexus_2026.docx", error: "OCR processing failed: image corruption detected in pages 4-6", errorType: "ocr", failedStage: "ocr", retryCount: 2, maxRetries: 3, canRetry: true, aiRepairSuggestion: "Try converting DOCX to PDF before upload. Pages 4-6 may contain embedded images with compression artifacts.", submittedBy: "System", failedAt: "2026-05-15T09:47:30Z", fileSize: 1200000 },
  { id: "fail-002", fileName: "Correspondence_Acme_Legal.pdf", error: "Unsupported document type for AI extraction pipeline", errorType: "classification", failedStage: "classifying", retryCount: 1, maxRetries: 3, canRetry: false, aiRepairSuggestion: "This appears to be legal correspondence, not a contract. Route to correspondence management system.", submittedBy: "System", failedAt: "2026-05-15T08:32:00Z", fileSize: 210000 },
  { id: "fail-003", fileName: "Scanned_Agreement_Handwritten.pdf", error: "Handwritten text detection: OCR confidence below 50% threshold", errorType: "ocr", failedStage: "ocr", retryCount: 3, maxRetries: 3, canRetry: false, aiRepairSuggestion: "Document contains significant handwritten annotations. Recommend manual transcription for pages 2, 5, 8.", submittedBy: "Michael Torres", failedAt: "2026-05-14T16:00:00Z", fileSize: 3400000 },
  { id: "fail-004", fileName: "Contract_FR_v3.pdf", error: "Multilingual OCR failed: French language pack not installed", errorType: "ocr", failedStage: "ocr", retryCount: 0, maxRetries: 3, canRetry: true, aiRepairSuggestion: "Enable French OCR language pack in system settings. Document is primarily French with English summary.", submittedBy: "System", failedAt: "2026-05-14T14:30:00Z", fileSize: 1800000 },
  { id: "fail-005", fileName: "Corrupted_File.pdf", error: "File integrity check failed: MD5 hash mismatch", errorType: "format", failedStage: "uploading", retryCount: 2, maxRetries: 3, canRetry: true, aiRepairSuggestion: "File may be corrupted during transfer. Request re-upload from source.", submittedBy: "System", failedAt: "2026-05-14T11:00:00Z", fileSize: 5000000 },
];

// ── Import Templates ─────────────────────────────────────────────────────

export const mockImportTemplates: ImportTemplate[] = [
  { id: "tpl-001", name: "Standard Contract Import", description: "Full pipeline: OCR, classification, extraction, validation, relationships", source: "local", documentType: "contract", autoClassify: true, autoExtract: true, runValidation: true, detectRelationships: true, confidenceThreshold: 80, createdBy: "System", usageCount: 1245, lastUsed: "2026-05-15T10:00:00Z" },
  { id: "tpl-002", name: "Quick DPA Import", description: "Fast-track DPA import with reduced validation", source: "sharepoint", documentType: "dpa", autoClassify: true, autoExtract: true, runValidation: false, detectRelationships: true, confidenceThreshold: 70, createdBy: "Sarah Chen", usageCount: 342, lastUsed: "2026-05-15T10:05:00Z" },
  { id: "tpl-003", name: "Bulk Amendment Import", description: "Batch import for contract amendments with parent linking", source: "sftp", documentType: "amendment", autoClassify: true, autoExtract: true, runValidation: true, detectRelationships: true, confidenceThreshold: 75, createdBy: "Michael Torres", usageCount: 187, lastUsed: "2026-05-15T09:15:00Z" },
  { id: "tpl-004", name: "High-Confidence Only", description: "Only accept documents with >90% confidence across all stages", source: "local", documentType: "contract", autoClassify: true, autoExtract: true, runValidation: true, detectRelationships: true, confidenceThreshold: 90, createdBy: "System", usageCount: 456, lastUsed: "2026-05-14T16:00:00Z" },
  { id: "tpl-005", name: "Email Attachment Import", description: "Process email attachments with sender metadata mapping", source: "email", documentType: "other", autoClassify: true, autoExtract: true, runValidation: false, detectRelationships: false, confidenceThreshold: 60, createdBy: "System", usageCount: 892, lastUsed: "2026-05-15T09:30:00Z" },
];

// ── Ingestion Analytics ──────────────────────────────────────────────────

export const mockIngestionAnalytics: IngestionAnalytics = {
  totalProcessed: 24892,
  totalFailed: 28,
  avgOcrAccuracy: 97.4,
  avgExtractionConfidence: 91.2,
  avgProcessingTime: 145,
  throughputHistory: [
    { date: "May 1", count: 892 }, { date: "May 3", count: 945 }, { date: "May 5", count: 1024 },
    { date: "May 7", count: 987 }, { date: "May 9", count: 1102 }, { date: "May 11", count: 1156 },
    { date: "May 13", count: 1245 }, { date: "May 15", count: 1189 },
  ],
  ocrAccuracyTrend: [
    { date: "May 1", accuracy: 96.2 }, { date: "May 4", accuracy: 96.5 },
    { date: "May 7", accuracy: 96.8 }, { date: "May 10", accuracy: 97.1 },
    { date: "May 13", accuracy: 97.4 },
  ],
  extractionConfidenceTrend: [
    { date: "May 1", confidence: 89.2 }, { date: "May 4", confidence: 89.8 },
    { date: "May 7", confidence: 90.3 }, { date: "May 10", confidence: 90.8 },
    { date: "May 13", confidence: 91.2 },
  ],
  sourceDistribution: [
    { source: "Local Upload", count: 8924 }, { source: "SharePoint", count: 6842 },
    { source: "Google Drive", count: 3210 }, { source: "SFTP", count: 2568 },
    { source: "Email", count: 1456 }, { source: "Box", count: 1892 },
  ],
  failureReasons: [
    { reason: "OCR image corruption", count: 8 },
    { reason: "Unsupported document type", count: 6 },
    { reason: "Classification confidence too low", count: 5 },
    { reason: "File integrity check failed", count: 4 },
    { reason: "Multilingual OCR not configured", count: 3 },
    { reason: "Metadata extraction timeout", count: 2 },
  ],
  documentTypeDistribution: [
    { type: "Contracts", count: 8924 }, { type: "Amendments", count: 3210 },
    { type: "DPAs", count: 2456 }, { type: "NDAs", count: 3420 },
    { type: "SLAs", count: 1892 }, { type: "Licenses", count: 1456 },
    { type: "Addendums", count: 892 }, { type: "Other", count: 2642 },
  ],
  processingTimeDistribution: [
    { range: "<30s", count: 4520 }, { range: "30-60s", count: 8230 },
    { range: "1-3m", count: 6540 }, { range: "3-5m", count: 3210 },
    { range: ">5m", count: 2392 },
  ],
  queueHealth: mockProcessingQueues,
};

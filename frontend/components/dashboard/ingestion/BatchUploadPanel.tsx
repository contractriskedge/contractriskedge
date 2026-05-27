"use client";

import React, { useState, useCallback, useEffect } from "react";
import { useDropzone } from "react-dropzone";
import { motion, AnimatePresence } from "framer-motion";
import {
  Upload, FileText, CheckCircle, XCircle, AlertTriangle, Clock,
  Loader2, FolderUp, List, Grid, Trash2, Play, Ban, ExternalLink,
  ChevronDown, ChevronRight, BarChart3,
} from "lucide-react";
import {
  useCreateBatch,
  useUploadBatchFile,
  useProcessBatch,
  useCancelBatch,
  useBatchDetail,
  useBatches,
} from "@/services/hooks/useUploads";
import type { BatchUploadDetailResponse, BatchUploadFileItem } from "@/services/api/uploads";

// ── Batch Upload Panel ────────────────────────────────────────────────────

interface BatchUploadPanelProps {
  onClose?: () => void;
}

export function BatchUploadPanel({ onClose }: BatchUploadPanelProps) {
  const [activeView, setActiveView] = useState<"upload" | "history">("upload");
  const [currentBatchId, setCurrentBatchId] = useState<string | null>(null);
  const [batchName, setBatchName] = useState("");
  const [uploadQueue, setUploadQueue] = useState<File[]>([]);
  const [uploadProgress, setUploadProgress] = useState<Record<string, { status: "pending" | "uploading" | "done" | "error"; error?: string }>>({});

  // Mutations
  const createBatch = useCreateBatch();
  const uploadFile = useUploadBatchFile();
  const processBatch = useProcessBatch();
  const cancelBatch = useCancelBatch();

  // Poll batch details when a batch is active
  const batchDetail = useBatchDetail(currentBatchId ?? undefined);

  // Batches list for history view
  const batchesList = useBatches({ page: 1, page_size: 20 });

  // Handle file drop — create batch if needed, then upload files
  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    if (acceptedFiles.length === 0) return;

    setUploadQueue((prev) => [...prev, ...acceptedFiles]);

    try {
      // Create batch if we don't have one
      let batchId = currentBatchId;
      if (!batchId) {
        const result = await createBatch.mutateAsync(batchName || undefined);
        batchId = result.batch_id;
        setCurrentBatchId(batchId);
      }

      // Upload each file
      for (const file of acceptedFiles) {
        setUploadProgress((prev) => ({
          ...prev,
          [file.name]: { status: "uploading" },
        }));
        try {
          await uploadFile.mutateAsync({ batchId, file });
          setUploadProgress((prev) => ({
            ...prev,
            [file.name]: { status: "done" },
          }));
        } catch (err) {
          setUploadProgress((prev) => ({
            ...prev,
            [file.name]: { status: "error", error: String(err) },
          }));
        }
      }
    } catch (err) {
      console.error("Batch upload failed:", err);
    }
  }, [currentBatchId, batchName, createBatch, uploadFile]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      "application/pdf": [".pdf"],
      "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [".docx"],
      "text/plain": [".txt"],
    },
    multiple: true,
  });

  const handleProcessBatch = async () => {
    if (!currentBatchId) return;
    await processBatch.mutateAsync(currentBatchId);
  };

  const handleCancelBatch = async () => {
    if (!currentBatchId) return;
    await cancelBatch.mutateAsync(currentBatchId);
    setCurrentBatchId(null);
    setUploadQueue([]);
    setUploadProgress({});
  };

  const handleNewBatch = () => {
    setCurrentBatchId(null);
    setUploadQueue([]);
    setUploadProgress({});
    setBatchName("");
  };

  // File status color
  const fileStatusColor = (status: string) => {
    switch (status) {
      case "review_ready": return "text-green-500";
      case "failed": return "text-red-500";
      case "uploaded": return "text-blue-500";
      case "processing": return "text-yellow-500";
      default: return "text-gray-400";
    }
  };

  const fileStatusIcon = (status: string) => {
    switch (status) {
      case "review_ready": return <CheckCircle className="w-4 h-4 text-green-500" />;
      case "failed": return <XCircle className="w-4 h-4 text-red-500" />;
      case "uploaded":
      case "uploading": return <Loader2 className="w-4 h-4 text-blue-500 animate-spin" />;
      default: return <Clock className="w-4 h-4 text-gray-400" />;
    }
  };

  const batch = batchDetail.data;
  const isProcessing = batch?.status === "processing" || batch?.status === "uploading";
  const isTerminal = batch?.status === "completed" || batch?.status === "failed" || batch?.status === "cancelled" || batch?.status === "partial";

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200 dark:border-navy-600">
        <div className="flex items-center gap-2">
          <FolderUp className="w-5 h-5 text-blue-500" />
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Batch Upload</h2>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setActiveView("upload")}
            className={`px-3 py-1.5 text-sm rounded-lg transition-colors ${
              activeView === "upload"
                ? "bg-blue-500 text-white"
                : "text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-navy-700"
            }`}
          >
            <Upload className="w-4 h-4 inline mr-1" /> Upload
          </button>
          <button
            onClick={() => setActiveView("history")}
            className={`px-3 py-1.5 text-sm rounded-lg transition-colors ${
              activeView === "history"
                ? "bg-blue-500 text-white"
                : "text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-navy-700"
            }`}
          >
            <Clock className="w-4 h-4 inline mr-1" /> History
          </button>
        </div>
      </div>

      {activeView === "upload" ? (
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {/* Batch Name Input */}
          {!currentBatchId && (
            <input
              type="text"
              value={batchName}
              onChange={(e) => setBatchName(e.target.value)}
              placeholder="Batch name (optional)"
              className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-navy-500 rounded-lg bg-white dark:bg-navy-700 text-gray-900 dark:text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          )}

          {/* Drop Zone */}
          {!isProcessing && (
            <div
              {...getRootProps()}
              className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-colors ${
                isDragActive
                  ? "border-blue-500 bg-blue-50 dark:bg-blue-900/20"
                  : "border-gray-300 dark:border-navy-500 hover:border-blue-400 dark:hover:border-blue-500"
              }`}
            >
              <input {...getInputProps()} />
              <FolderUp className="w-12 h-12 mx-auto mb-3 text-gray-400 dark:text-gray-500" />
              <p className="text-sm text-gray-600 dark:text-gray-300">
                {isDragActive ? "Drop files here..." : "Drag & drop files here, or click to select"}
              </p>
              <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">
                PDF, DOCX, TXT — multiple files supported
              </p>
            </div>
          )}

          {/* Upload Queue Progress */}
          {uploadQueue.length > 0 && (
            <div className="space-y-2">
              <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300">
                Upload Queue ({uploadQueue.length} files)
              </h3>
              <div className="space-y-1 max-h-40 overflow-y-auto">
                {uploadQueue.map((file) => (
                  <div key={file.name} className="flex items-center justify-between px-3 py-2 bg-gray-50 dark:bg-navy-700 rounded-lg text-sm">
                    <div className="flex items-center gap-2 min-w-0">
                      <FileText className="w-4 h-4 text-gray-400 shrink-0" />
                      <span className="truncate text-gray-700 dark:text-gray-300">{file.name}</span>
                      <span className="text-xs text-gray-400">({(file.size / 1024).toFixed(0)} KB)</span>
                    </div>
                    <div className="shrink-0">
                      {uploadProgress[file.name]?.status === "uploading" && (
                        <Loader2 className="w-4 h-4 text-blue-500 animate-spin" />
                      )}
                      {uploadProgress[file.name]?.status === "done" && (
                        <CheckCircle className="w-4 h-4 text-green-500" />
                      )}
                      {uploadProgress[file.name]?.status === "error" && (
                        <XCircle className="w-4 h-4 text-red-500" title={uploadProgress[file.name]?.error} />
                      )}
                      {!uploadProgress[file.name] && (
                        <Clock className="w-4 h-4 text-gray-400" />
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Active Batch Status */}
          {currentBatchId && batch && (
            <div className="bg-white dark:bg-navy-700 rounded-xl border border-gray-200 dark:border-navy-600 p-4 space-y-3">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300">
                  Batch: {batch.name || batch.batch_id.slice(0, 8)}
                </h3>
                <span className={`px-2 py-0.5 text-xs font-medium rounded-full ${
                  batch.status === "completed" ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400" :
                  batch.status === "failed" ? "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400" :
                  batch.status === "partial" ? "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400" :
                  batch.status === "processing" ? "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400" :
                  "bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300"
                }`}>
                  {batch.status}
                </span>
              </div>

              {/* Progress Bar */}
              {batch.total_files > 0 && (
                <div className="space-y-1">
                  <div className="flex justify-between text-xs text-gray-500">
                    <span>{batch.completed_files + batch.failed_files} / {batch.total_files} files</span>
                    <span>{Math.round((batch.completed_files + batch.failed_files) / batch.total_files * 100)}%</span>
                  </div>
                  <div className="w-full h-2 bg-gray-200 dark:bg-navy-600 rounded-full overflow-hidden">
                    <div
                      className="h-full rounded-full transition-all duration-500"
                      style={{
                        width: `${(batch.completed_files + batch.failed_files) / batch.total_files * 100}%`,
                        background: batch.failed_files > 0
                          ? `linear-gradient(90deg, #22c55e ${batch.completed_files / (batch.completed_files + batch.failed_files) * 100}%, #ef4444 100%)`
                          : "#22c55e",
                      }}
                    />
                  </div>
                </div>
              )}

              {/* Per-file Status */}
              {batch.files && batch.files.length > 0 && (
                <div className="space-y-1 max-h-48 overflow-y-auto">
                  {batch.files.map((file) => (
                    <div key={file.upload_id} className="flex items-center justify-between px-2 py-1.5 text-sm rounded hover:bg-gray-50 dark:hover:bg-navy-600">
                      <div className="flex items-center gap-2 min-w-0">
                        {fileStatusIcon(file.status)}
                        <span className="truncate text-gray-700 dark:text-gray-300">{file.filename}</span>
                      </div>
                      <span className={`text-xs ${fileStatusColor(file.status)}`}>
                        {file.status}
                      </span>
                    </div>
                  ))}
                </div>
              )}

              {/* Action Buttons */}
              <div className="flex gap-2 pt-2">
                {!isTerminal && !isProcessing && (
                  <button
                    onClick={handleProcessBatch}
                    disabled={processBatch.isPending || batch.total_files === 0}
                    className="flex items-center gap-1.5 px-4 py-2 text-sm font-medium text-white bg-blue-500 rounded-lg hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  >
                    {processBatch.isPending ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <Play className="w-4 h-4" />
                    )}
                    Process All
                  </button>
                )}
                {!isTerminal && (
                  <button
                    onClick={handleCancelBatch}
                    disabled={cancelBatch.isPending}
                    className="flex items-center gap-1.5 px-4 py-2 text-sm font-medium text-red-600 bg-red-50 dark:bg-red-900/20 rounded-lg hover:bg-red-100 dark:hover:bg-red-900/30 disabled:opacity-50 transition-colors"
                  >
                    <Ban className="w-4 h-4" />
                    Cancel
                  </button>
                )}
                {isTerminal && (
                  <button
                    onClick={handleNewBatch}
                    className="flex items-center gap-1.5 px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 dark:bg-navy-600 dark:text-gray-300 rounded-lg hover:bg-gray-200 dark:hover:bg-navy-500 transition-colors"
                  >
                    <Upload className="w-4 h-4" />
                    New Batch
                  </button>
                )}
              </div>
            </div>
          )}
        </div>
      ) : (
        /* History View */
        <div className="flex-1 overflow-y-auto p-4">
          {batchesList.isLoading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="w-6 h-6 animate-spin text-blue-500" />
            </div>
          ) : (
            <div className="space-y-2">
              {batchesList.data?.items.map((b) => (
                <div
                  key={b.batch_id}
                  className="flex items-center justify-between px-3 py-3 bg-white dark:bg-navy-700 rounded-lg border border-gray-200 dark:border-navy-600 hover:border-blue-300 dark:hover:border-blue-500 cursor-pointer transition-colors"
                  onClick={() => {
                    setCurrentBatchId(b.batch_id);
                    setActiveView("upload");
                  }}
                >
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-gray-900 dark:text-white truncate">
                      {b.name || b.batch_id.slice(0, 8)}
                    </p>
                    <p className="text-xs text-gray-500 dark:text-gray-400">
                      {b.total_files} files · {(b.total_bytes / 1024 / 1024).toFixed(1)} MB · {new Date(b.created_at).toLocaleString()}
                    </p>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <span className={`px-2 py-0.5 text-xs font-medium rounded-full ${
                      b.status === "completed" ? "bg-green-100 text-green-700" :
                      b.status === "failed" ? "bg-red-100 text-red-700" :
                      b.status === "partial" ? "bg-yellow-100 text-yellow-700" :
                      b.status === "processing" ? "bg-blue-100 text-blue-700" :
                      "bg-gray-100 text-gray-700"
                    }`}>
                      {b.status}
                    </span>
                    <ChevronRight className="w-4 h-4 text-gray-400" />
                  </div>
                </div>
              ))}
              {(!batchesList.data?.items || batchesList.data.items.length === 0) && (
                <div className="text-center py-12 text-gray-400 dark:text-gray-500">
                  <FolderUp className="w-12 h-12 mx-auto mb-2 opacity-50" />
                  <p className="text-sm">No batch uploads yet</p>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

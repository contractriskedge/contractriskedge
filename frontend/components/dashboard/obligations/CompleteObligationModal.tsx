/**
 * CompleteObligationModal — modal for completing an obligation with audit evidence.
 *
 * Features:
 * - Completion Notes (required textarea)
 * - Evidence Attachment Upload (optional)
 * - Completion Date (default = current date)
 * - Completed By (read-only, current user)
 * - Creates OBLIGATION_COMPLETED audit event
 * - Propagates to Contract 360 Activity Timeline
 */

"use client";

import React, { useState } from "react";
import { motion } from "framer-motion";
import { X, FileText, Upload, Calendar, User, Loader2, CheckCircle2, AlertCircle } from "lucide-react";
import { obligationsService } from "@/services/api/obligations";

interface CompleteObligationModalProps {
  obligationId: string;
  obligationName: string;
  currentUserName?: string;
  onComplete: () => void;
  onClose: () => void;
}

export function CompleteObligationModal({
  obligationId,
  obligationName,
  currentUserName = "Current User",
  onComplete,
  onClose,
}: CompleteObligationModalProps) {
  const [completionNotes, setCompletionNotes] = useState("");
  const [completionDate, setCompletionDate] = useState(new Date().toISOString().split("T")[0]);
  const [evidenceFiles, setEvidenceFiles] = useState<File[]>([]);
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async () => {
    setError("");

    if (!completionNotes.trim()) {
      setError("Completion notes are required. Please explain how this obligation was satisfied.");
      return;
    }

    setIsSubmitting(true);
    try {
      // Step 1: Upload evidence files first (if any)
      const evidenceIds: string[] = [];
      for (const file of evidenceFiles) {
        try {
          const result = await obligationsService.uploadEvidence(obligationId, file);
          if (result?.id) {
            evidenceIds.push(result.id);
          }
        } catch (uploadErr: any) {
          setError(`Failed to upload evidence file "${file.name}": ${uploadErr?.message || "Upload failed"}`);
          setIsSubmitting(false);
          return;
        }
      }

      // Step 2: Complete the obligation with evidence IDs
      await obligationsService.completeObligationWithEvidence(obligationId, {
        completionNotes: completionNotes.trim(),
        completionDate: new Date(completionDate).toISOString(),
        evidenceAttachmentIds: evidenceIds.length > 0 ? evidenceIds : undefined,
      });
      onComplete();
      onClose();
    } catch (err: any) {
      setError(err?.message || "Failed to complete obligation. Please try again.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      setEvidenceFiles(Array.from(e.target.files));
    }
  };

  const removeFile = (index: number) => {
    setEvidenceFiles((prev) => prev.filter((_, i) => i !== index));
  };

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
      onClick={onClose}
    >
      <motion.div
        initial={{ scale: 0.95, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        exit={{ scale: 0.95, opacity: 0 }}
        className="bg-white rounded-xl shadow-2xl border border-gray-200 w-full max-w-lg max-h-[90vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="sticky top-0 px-6 py-4 border-b border-gray-100 bg-gradient-to-r from-emerald-50 to-teal-50 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-emerald-600 flex items-center justify-center">
              <CheckCircle2 className="w-5 h-5 text-white" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-navy-900">Complete Obligation</h2>
              <p className="text-sm text-gray-500 mt-0.5 truncate max-w-xs">{obligationName}</p>
            </div>
          </div>
          <button onClick={onClose} disabled={isSubmitting} className="text-gray-400 hover:text-gray-600 disabled:opacity-50">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-5">
          {/* Completion Notes (Required) */}
          <div>
            <label className="block text-sm font-medium text-gray-900 mb-2">
              Completion Notes <span className="text-red-500">*</span>
            </label>
            <textarea
              value={completionNotes}
              onChange={(e) => { setCompletionNotes(e.target.value); setError(""); }}
              placeholder="Describe how this obligation was satisfied, including any relevant details, dates, or references..."
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:border-emerald-500 focus:outline-none focus:ring-1 focus:ring-emerald-500 min-h-[120px]"
              rows={5}
              disabled={isSubmitting}
            />
            <p className="text-xs text-gray-500 mt-1">
              Required. Explain how, when, and by whom the obligation was fulfilled.
            </p>
          </div>

          {/* Completion Date (Optional, defaults to today) */}
          <div>
            <label className="block text-sm font-medium text-gray-900 mb-2">
              <Calendar className="w-4 h-4 inline mr-1.5 text-gray-400" />
              Completion Date
            </label>
            <input
              type="date"
              value={completionDate}
              onChange={(e) => setCompletionDate(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:border-emerald-500 focus:outline-none focus:ring-1 focus:ring-emerald-500"
              disabled={isSubmitting}
            />
            <p className="text-xs text-gray-500 mt-1">Defaults to today. Change if the obligation was completed earlier.</p>
          </div>

          {/* Evidence Attachment (Optional) */}
          <div>
            <label className="block text-sm font-medium text-gray-900 mb-2">
              <Upload className="w-4 h-4 inline mr-1.5 text-gray-400" />
              Evidence Attachments <span className="text-gray-400 font-normal">(Optional)</span>
            </label>
            <div className="border-2 border-dashed border-gray-300 rounded-lg p-4 text-center hover:border-emerald-400 transition-colors">
              <input
                type="file"
                multiple
                onChange={handleFileChange}
                className="hidden"
                id="evidence-upload"
                disabled={isSubmitting}
              />
              <label htmlFor="evidence-upload" className="cursor-pointer">
                <Upload className="w-6 h-6 text-gray-400 mx-auto mb-2" />
                <p className="text-sm text-gray-600 font-medium">Click to upload evidence files</p>
                <p className="text-xs text-gray-400 mt-1">PDF, DOCX, images, or other supporting documents</p>
              </label>
            </div>
            {evidenceFiles.length > 0 && (
              <div className="mt-2 space-y-1">
                {evidenceFiles.map((file, i) => (
                  <div key={i} className="flex items-center justify-between px-3 py-2 bg-gray-50 rounded-lg border border-gray-200">
                    <div className="flex items-center gap-2 min-w-0">
                      <FileText className="w-4 h-4 text-gray-400 shrink-0" />
                      <span className="text-xs text-gray-700 truncate">{file.name}</span>
                      <span className="text-[10px] text-gray-400 shrink-0">({(file.size / 1024).toFixed(0)} KB)</span>
                    </div>
                    <button onClick={() => removeFile(i)} className="text-gray-400 hover:text-red-500 shrink-0">
                      <X className="w-3.5 h-3.5" />
                    </button>
                  </div>
                ))}
              </div>
            )}
            <p className="text-xs text-gray-500 mt-1">Optional. Upload supporting documents as evidence of completion.</p>
          </div>

          {/* Completed By (Read-only) */}
          <div>
            <label className="block text-sm font-medium text-gray-900 mb-2">
              <User className="w-4 h-4 inline mr-1.5 text-gray-400" />
              Completed By
            </label>
            <div className="px-3 py-2 bg-gray-50 border border-gray-200 rounded-lg text-sm text-gray-700 flex items-center gap-2">
              <div className="w-6 h-6 rounded-full bg-emerald-100 flex items-center justify-center">
                <User className="w-3.5 h-3.5 text-emerald-600" />
              </div>
              {currentUserName}
            </div>
            <p className="text-xs text-gray-500 mt-1">Read-only. Recorded as the user completing this obligation.</p>
          </div>

          {/* Error Message */}
          {error && (
            <div className="p-3 bg-red-50 rounded-lg border border-red-200 flex items-start gap-2">
              <AlertCircle className="w-4 h-4 text-red-600 mt-0.5 shrink-0" />
              <p className="text-sm text-red-800">{error}</p>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="sticky bottom-0 px-6 py-4 border-t border-gray-100 bg-gray-50 flex items-center justify-end gap-3">
          <button
            onClick={onClose}
            disabled={isSubmitting}
            className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            disabled={isSubmitting || !completionNotes.trim()}
            className="px-4 py-2 text-sm font-medium text-white bg-emerald-600 rounded-lg hover:bg-emerald-700 disabled:opacity-50 transition-colors inline-flex items-center gap-2"
          >
            {isSubmitting ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Completing...
              </>
            ) : (
              <>
                <CheckCircle2 className="w-4 h-4" />
                Complete Obligation
              </>
            )}
          </button>
        </div>
      </motion.div>
    </motion.div>
  );
}

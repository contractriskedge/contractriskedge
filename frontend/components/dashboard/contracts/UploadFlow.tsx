"use client";

import React, { useState, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Upload, FileText, X, CheckCircle, AlertTriangle, Loader2, Sparkles, Search } from "lucide-react";

interface UploadFlowProps {
  isOpen: boolean;
  onClose: () => void;
}

export function UploadFlow({ isOpen, onClose }: UploadFlowProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [files, setFiles] = useState<File[]>([]);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [complete, setComplete] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };
  const handleDragLeave = () => setIsDragging(false);
  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files.length) {
      setFiles(Array.from(e.dataTransfer.files));
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files?.length) {
      setFiles(Array.from(e.target.files));
    }
  };

  const handleUpload = () => {
    if (!files.length) return;
    setUploading(true);
    setProgress(0);
    const interval = setInterval(() => {
      setProgress((p) => {
        if (p >= 100) {
          clearInterval(interval);
          setUploading(false);
          setComplete(true);
          return 100;
        }
        return p + 5;
      });
    }, 200);
  };

  const reset = () => {
    setFiles([]);
    setUploading(false);
    setProgress(0);
    setComplete(false);
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/30 z-50"
            onClick={onClose}
          />
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 20 }}
            className="fixed left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 w-full max-w-lg max-h-[90vh] flex flex-col bg-white rounded-2xl border border-gray-200 shadow-2xl z-50 overflow-hidden"
          >
            {/* Header */}
            <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100 shrink-0">
              <div className="flex items-center gap-2">
                <Upload className="w-4.5 h-4.5 text-navy-700" />
                <h2 className="text-sm font-semibold text-navy-900">
                  {complete ? "Upload Complete" : uploading ? "Uploading..." : "Upload Contracts"}
                </h2>
              </div>
              <button onClick={onClose} className="p-1 rounded hover:bg-gray-100 text-gray-400 transition-colors"><X className="w-4 h-4" /></button>
            </div>

            <div className="flex-1 min-h-0 overflow-y-auto p-6 space-y-4">
              {!uploading && !complete && (
                <>
                  {/* Drop zone */}
                  <div
                    onDragOver={handleDragOver}
                    onDragLeave={handleDragLeave}
                    onDrop={handleDrop}
                    className={`border-2 border-dashed rounded-xl p-8 text-center transition-all ${
                      isDragging ? "border-navy-400 bg-navy-50" : "border-gray-200 hover:border-gray-300 bg-gray-50/50"
                    }`}
                  >
                    <Upload className="w-10 h-10 mx-auto mb-3 text-gray-300" />
                    <p className="text-sm font-medium text-gray-600">Drag & drop files here</p>
                    <p className="text-xs text-gray-400 mt-1">or</p>
                    <button
                      onClick={() => fileInputRef.current?.click()}
                      className="mt-2 text-xs font-medium px-4 py-1.5 rounded-lg bg-navy-700 text-white hover:bg-navy-800 transition-colors"
                    >
                      Browse Files
                    </button>
                    <input ref={fileInputRef} type="file" multiple accept=".pdf,.docx,.doc,.txt" className="hidden" onChange={handleFileSelect} />
                    <p className="text-[10px] text-gray-400 mt-2">PDF, DOCX, DOC, TXT — up to 50MB each</p>
                  </div>

                  {/* Selected files */}
                  {files.length > 0 && (
                    <div className="space-y-1.5">
                      <p className="text-[10px] font-semibold text-gray-500 uppercase sticky top-0 bg-white py-1 z-10">
                        {files.length} file{files.length > 1 ? "s" : ""} selected
                      </p>
                      <div className="space-y-1.5 max-h-48 overflow-y-auto pr-1">
                        {files.map((f, i) => (
                          <div key={`${f.name}-${i}`} className="flex items-center gap-2 p-2 bg-gray-50 rounded-lg">
                            <FileText className="w-4 h-4 text-navy-400 shrink-0" />
                            <span className="text-xs text-gray-700 flex-1 truncate">{f.name}</span>
                            <span className="text-[10px] text-gray-400 shrink-0">{(f.size / 1024 / 1024).toFixed(1)}MB</span>
                            <button onClick={() => setFiles(files.filter((_, j) => j !== i))} className="p-0.5 rounded hover:bg-gray-200 text-gray-400 shrink-0">
                              <X className="w-3 h-3" />
                            </button>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* AI metadata extraction preview */}
                  {files.length > 0 && (
                    <div className="p-3 bg-purple-50 rounded-lg border border-purple-100">
                      <div className="flex items-center gap-1.5 mb-1">
                        <Sparkles className="w-3.5 h-3.5 text-purple-600" />
                        <span className="text-[10px] font-semibold text-purple-700 uppercase">AI Pre-Processing</span>
                      </div>
                      <div className="space-y-1">
                        {[
                          { label: "OCR Processing", ready: true },
                          { label: "Metadata Extraction", ready: true },
                          { label: "Clause Detection", ready: files.length > 0 },
                          { label: "Duplicate Check", ready: files.length > 0 },
                        ].map((item) => (
                          <div key={item.label} className="flex items-center gap-1.5 text-[11px]">
                            {item.ready ? (
                              <CheckCircle className="w-3 h-3 text-green-500" />
                            ) : (
                              <Loader2 className="w-3 h-3 text-gray-400 animate-spin" />
                            )}
                            <span className={item.ready ? "text-gray-700" : "text-gray-400"}>{item.label}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Upload button */}
                  {files.length > 0 && (
                    <button
                      onClick={handleUpload}
                      className="w-full py-2.5 text-xs font-semibold rounded-lg bg-navy-700 text-white hover:bg-navy-800 transition-colors shadow-sm"
                    >
                      Upload {files.length} Contract{files.length > 1 ? "s" : ""}
                    </button>
                  )}
                </>
              )}

              {/* Upload progress */}
              {uploading && (
                <div className="space-y-4 py-4">
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-gray-600">Uploading and processing...</span>
                    <span className="font-semibold text-navy-700">{progress}%</span>
                  </div>
                  <div className="h-2.5 bg-gray-200 rounded-full overflow-hidden">
                    <motion.div
                      className="h-full rounded-full bg-gradient-to-r from-navy-500 to-navy-700"
                      initial={{ width: "0%" }}
                      animate={{ width: `${progress}%` }}
                      transition={{ duration: 0.3 }}
                    />
                  </div>
                  <div className="space-y-1 text-[11px] text-gray-500">
                    <div className="flex items-center gap-1.5">
                      <Loader2 className="w-3 h-3 animate-spin text-navy-500" />
                      Extracting text with OCR...
                    </div>
                    {progress > 30 && (
                      <div className="flex items-center gap-1.5">
                        <Loader2 className="w-3 h-3 animate-spin text-navy-500" />
                        Detecting clauses and metadata...
                      </div>
                    )}
                    {progress > 60 && (
                      <div className="flex items-center gap-1.5">
                        <Loader2 className="w-3 h-3 animate-spin text-navy-500" />
                        Running AI risk analysis...
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Complete */}
              {complete && (
                <div className="text-center py-4 space-y-3">
                  <div className="w-14 h-14 rounded-full bg-green-100 flex items-center justify-center mx-auto">
                    <CheckCircle className="w-7 h-7 text-green-600" />
                  </div>
                  <div>
                    <p className="text-sm font-semibold text-navy-900">Upload Complete</p>
                    <p className="text-xs text-gray-500 mt-0.5">{files.length} contract{files.length > 1 ? "s" : ""} processed successfully</p>
                  </div>
                  <div className="flex gap-2 justify-center">
                    <button onClick={reset} className="text-xs font-medium px-4 py-1.5 rounded-lg bg-navy-700 text-white hover:bg-navy-800 transition-colors">
                      Upload More
                    </button>
                    <button onClick={onClose} className="text-xs font-medium px-4 py-1.5 rounded-lg bg-white border border-gray-200 text-gray-600 hover:bg-gray-50 transition-colors">
                      Done
                    </button>
                  </div>
                </div>
              )}
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}

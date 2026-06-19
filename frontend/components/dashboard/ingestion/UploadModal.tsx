"use client";

import React, { useState, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Upload, FileText, X, CheckCircle, Sparkles } from "lucide-react";

interface UploadModalProps {
  isOpen: boolean;
  onClose: () => void;
  onUpload: (files: FileList | null) => void;
}

export function UploadModal({ isOpen, onClose, onUpload }: UploadModalProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleClose = () => {
    setSelectedFiles([]);
    setIsDragging(false);
    onClose();
  };

  const handleDragOver = (e: React.DragEvent) => { e.preventDefault(); setIsDragging(true); };
  const handleDragLeave = () => setIsDragging(false);
  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files.length) {
      setSelectedFiles(Array.from(e.dataTransfer.files));
    }
  };
  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files?.length) {
      setSelectedFiles(Array.from(e.target.files));
    }
  };

  const handleUpload = () => {
    if (!selectedFiles.length) return;
    const dt = new DataTransfer();
    selectedFiles.forEach(f => dt.items.add(f));
    onUpload(dt.files);
    setSelectedFiles([]);
    onClose();
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
            onClick={handleClose}
          />
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 20 }}
            className="fixed left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 w-full max-w-lg max-h-[90vh] flex flex-col bg-white rounded-2xl border border-gray-200 shadow-2xl z-50 overflow-hidden"
          >
            <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100 shrink-0">
              <div className="flex items-center gap-2">
                <Upload className="w-4.5 h-4.5 text-navy-700" />
                <h2 className="text-sm font-semibold text-navy-900">Upload Contracts</h2>
              </div>
              <button onClick={handleClose} className="p-1 rounded hover:bg-gray-100 text-gray-400 transition-colors"><X className="w-4 h-4" /></button>
            </div>

            <div className="flex-1 min-h-0 overflow-y-auto p-6 space-y-4">
              <div
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
                className={`border-2 border-dashed rounded-xl p-6 text-center transition-all ${
                  isDragging ? "border-blue-400 bg-blue-50" : "border-gray-200 hover:border-gray-300 bg-gray-50/50"
                }`}
              >
                <Upload className={`w-10 h-10 mx-auto mb-3 ${isDragging ? "text-blue-500" : "text-gray-300"}`} />
                <p className="text-sm font-medium text-gray-600">Drag & drop files here</p>
                <p className="text-xs text-gray-400 mt-1">or</p>
                <button
                  onClick={() => fileInputRef.current?.click()}
                  className="mt-2 text-xs font-medium px-4 py-1.5 rounded-lg bg-blue-600 text-white hover:bg-blue-700 transition-colors"
                >
                  Browse Files
                </button>
                <input ref={fileInputRef} type="file" multiple accept=".pdf,.docx,.doc,.tiff,.tif,.png,.jpg,.jpeg" className="hidden" onChange={handleFileSelect} />
                <p className="text-[10px] text-gray-400 mt-2">PDF, DOCX, DOC, TIFF, PNG, JPG — up to 100MB each</p>
              </div>

              {selectedFiles.length > 0 && (
                <div className="space-y-1.5">
                  <p className="text-[10px] font-semibold text-gray-500 uppercase sticky top-0 bg-white py-1 z-10">
                    {selectedFiles.length} file{selectedFiles.length > 1 ? "s" : ""} selected
                  </p>
                  <div className="space-y-1.5 max-h-48 overflow-y-auto pr-1">
                    {selectedFiles.map((f, i) => (
                      <div key={`${f.name}-${i}`} className="flex items-center gap-2 p-2 bg-gray-50 rounded-lg">
                        <FileText className="w-4 h-4 text-navy-400 shrink-0" />
                        <span className="text-xs text-gray-700 flex-1 truncate">{f.name}</span>
                        <span className="text-[10px] text-gray-400 shrink-0">{(f.size / 1024 / 1024).toFixed(1)}MB</span>
                        <button onClick={() => setSelectedFiles(prev => prev.filter((_, j) => j !== i))} className="p-0.5 rounded hover:bg-gray-200 text-gray-400 shrink-0">
                          <X className="w-3 h-3" />
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {selectedFiles.length > 0 && (
                <div className="p-3 bg-purple-50 rounded-lg border border-purple-100">
                  <div className="flex items-center gap-1.5 mb-1">
                    <Sparkles className="w-3.5 h-3.5 text-purple-600" />
                    <span className="text-[10px] font-semibold text-purple-700 uppercase">AI Pre-Processing</span>
                  </div>
                  <div className="space-y-1">
                    {[
                      { label: "OCR Processing", ready: true },
                      { label: "Metadata Extraction", ready: true },
                      { label: "Clause Detection", ready: selectedFiles.length > 0 },
                      { label: "Duplicate Check", ready: selectedFiles.length > 0 },
                    ].map((item) => (
                      <div key={item.label} className="flex items-center gap-1.5 text-[11px]">
                        {item.ready ? (
                          <CheckCircle className="w-3 h-3 text-green-500" />
                        ) : (
                          <div className="w-3 h-3 rounded-full border-2 border-gray-300" />
                        )}
                        <span className={item.ready ? "text-gray-700" : "text-gray-400"}>{item.label}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-gray-100 bg-gray-50 shrink-0">
              <button onClick={handleClose} className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors">
                Cancel
              </button>
              <button
                onClick={handleUpload}
                disabled={selectedFiles.length === 0}
                className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
              >
                <Upload className="w-4 h-4" />
                Upload {selectedFiles.length > 0 ? `(${selectedFiles.length} file${selectedFiles.length > 1 ? "s" : ""})` : ""}
              </button>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}

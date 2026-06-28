"use client";

import React, { useState, useRef } from "react";
import { useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { Upload, FileText, X, CheckCircle, Loader2, FilePlus, Layers } from "lucide-react";

interface UploadFlowProps {
  isOpen: boolean;
  onClose: () => void;
}

export function UploadFlow({ isOpen, onClose }: UploadFlowProps) {
  const router = useRouter();
  const [mode, setMode] = useState<"choose" | "upload" | "uploading" | "complete">("choose");
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
      setMode("upload");
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files?.length) {
      setFiles(Array.from(e.target.files));
      setMode("upload");
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
    setMode("choose");
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
                {mode === "choose" ? <FilePlus className="w-4.5 h-4.5 text-navy-700" /> : <Upload className="w-4.5 h-4.5 text-navy-700" />}
                <h2 className="text-sm font-semibold text-navy-900">
                  {mode === "complete" ? "Upload Complete" : mode === "uploading" ? "Uploading..." : mode === "upload" ? "Upload Contracts" : "New Contract"}
                </h2>
              </div>
              <button onClick={onClose} className="p-1 rounded hover:bg-gray-100 text-gray-400 transition-colors"><X className="w-4 h-4" /></button>
            </div>

            <div className="flex-1 min-h-0 overflow-y-auto p-6 space-y-4">
              {/* Mode: Choose */}
              {mode === "choose" && (
                <div className="space-y-3">
                  <p className="text-xs text-gray-500">Choose how to create this contract.</p>
                  <button onClick={() => setMode("upload")}
                    className="w-full flex items-start gap-4 p-4 rounded-xl border-2 border-gray-200 hover:border-navy-400 hover:bg-navy-50/50 transition-all text-left">
                    <div className="w-10 h-10 rounded-lg bg-blue-50 flex items-center justify-center flex-shrink-0">
                      <Upload className="w-5 h-5 text-blue-600" />
                    </div>
                    <div>
                      <p className="text-sm font-semibold text-navy-900">Upload Existing Contract</p>
                      <p className="text-[10px] text-gray-500 mt-0.5">Upload PDF or DOCX. Used for third-party contracts.</p>
                    </div>
                  </button>
                  <button onClick={() => { onClose(); router.push("/templates"); }}
                    className="w-full flex items-start gap-4 p-4 rounded-xl border-2 border-gray-200 hover:border-navy-400 hover:bg-navy-50/50 transition-all text-left">
                    <div className="w-10 h-10 rounded-lg bg-purple-50 flex items-center justify-center flex-shrink-0">
                      <FilePlus className="w-5 h-5 text-purple-600" />
                    </div>
                    <div>
                      <p className="text-sm font-semibold text-navy-900">Create From Template</p>
                      <p className="text-[10px] text-gray-500 mt-0.5">Generate a new contract using company templates.</p>
                    </div>
                  </button>
                  <div className="w-full flex items-start gap-4 p-4 rounded-xl border-2 border-gray-100 bg-gray-50 opacity-60 cursor-not-allowed text-left">
                    <div className="w-10 h-10 rounded-lg bg-gray-100 flex items-center justify-center flex-shrink-0">
                      <Layers className="w-5 h-5 text-gray-400" />
                    </div>
                    <div>
                      <p className="text-sm font-semibold text-gray-400">Import Legacy Contract</p>
                      <p className="text-[10px] text-gray-400 mt-0.5">Coming Soon</p>
                    </div>
                  </div>
                </div>
              )}

              {/* Upload mode */}
              {mode === "upload" && !uploading && !complete && (
                <>
                  <div onDragOver={handleDragOver} onDragLeave={handleDragLeave} onDrop={handleDrop}
                    className={`border-2 border-dashed rounded-xl p-8 text-center transition-all ${isDragging ? "border-navy-400 bg-navy-50" : "border-gray-200 hover:border-gray-300 bg-gray-50/50"}`}>
                    <Upload className="w-10 h-10 mx-auto mb-3 text-gray-300" />
                    <p className="text-sm font-medium text-gray-600">Drag & drop files here</p>
                    <p className="text-xs text-gray-400 mt-1">or</p>
                    <button onClick={() => fileInputRef.current?.click()}
                      className="mt-2 text-xs font-medium px-4 py-1.5 rounded-lg bg-navy-700 text-white hover:bg-navy-800">Browse Files</button>
                    <input ref={fileInputRef} type="file" multiple accept=".pdf,.docx,.doc,.txt" className="hidden" onChange={handleFileSelect} />
                  </div>
                  {files.length > 0 && (
                    <div className="space-y-1.5">
                      {files.map((f, i) => (
                        <div key={i} className="flex items-center gap-2 p-2 bg-gray-50 rounded-lg">
                          <FileText className="w-4 h-4 text-navy-400 shrink-0" />
                          <span className="text-xs text-gray-700 flex-1 truncate">{f.name}</span>
                          <button onClick={() => setFiles(files.filter((_, j) => j !== i))} className="p-0.5 rounded hover:bg-gray-200 text-gray-400"><X className="w-3 h-3" /></button>
                        </div>
                      ))}
                    </div>
                  )}
                  {files.length > 0 && (
                    <button onClick={handleUpload} className="w-full py-2.5 text-xs font-semibold rounded-lg bg-navy-700 text-white hover:bg-navy-800">
                      Upload {files.length} Contract(s)
                    </button>
                  )}
                  <button onClick={() => setMode("choose")} className="w-full py-2 text-xs text-gray-500 hover:text-gray-700">Back to options</button>
                </>
              )}

              {uploading && (
                <div className="space-y-4 py-4">
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-gray-600">Uploading...</span>
                    <span className="font-semibold text-navy-700">{progress}%</span>
                  </div>
                  <div className="h-2.5 bg-gray-200 rounded-full overflow-hidden">
                    <motion.div className="h-full rounded-full bg-gradient-to-r from-navy-500 to-navy-700"
                      initial={{ width: "0%" }} animate={{ width: `${progress}%` }} transition={{ duration: 0.3 }} />
                  </div>
                </div>
              )}

              {complete && (
                <div className="text-center py-4 space-y-3">
                  <div className="w-14 h-14 rounded-full bg-green-100 flex items-center justify-center mx-auto">
                    <CheckCircle className="w-7 h-7 text-green-600" />
                  </div>
                  <p className="text-sm font-semibold text-navy-900">Upload Complete</p>
                  <p className="text-xs text-gray-500">{files.length} contract(s) processed</p>
                  <div className="flex gap-2 justify-center">
                    <button onClick={reset} className="text-xs font-medium px-4 py-1.5 rounded-lg bg-navy-700 text-white hover:bg-navy-800">Upload More</button>
                    <button onClick={onClose} className="text-xs font-medium px-4 py-1.5 rounded-lg bg-white border border-gray-200 text-gray-600 hover:bg-gray-50">Done</button>
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

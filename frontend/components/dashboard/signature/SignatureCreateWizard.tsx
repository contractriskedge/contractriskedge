"use client";

import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  X, FileSignature, Users, Send, ArrowRight, ArrowLeft,
  Loader2, Check,
} from "lucide-react";
import type { SignatureProvider, SignerRole, AuthType } from "./types";
import { PROVIDER_LABELS } from "./types";
import { SignerList } from "./SignerList";
import { SignerAddDialog } from "./SignerAddDialog";

interface SignatureCreateWizardProps {
  isOpen: boolean;
  onClose: () => void;
  onCreate: (data: {
    title: string;
    provider: SignatureProvider;
    signers: { email: string; name: string; role: SignerRole; signingOrder: number; routingOrder: number; authenticationType: string }[];
    expiresInDays: number;
    reminderDays: number;
    emailSubject?: string;
    emailMessage?: string;
    allowDecline?: boolean;
    allowPrint?: boolean;
  }) => Promise<void>;
  contractTitle?: string;
  sessionId?: string;
}

export function SignatureCreateWizard({
  isOpen, onClose, onCreate, contractTitle, sessionId,
}: SignatureCreateWizardProps) {
  const [step, setStep] = useState(0);
  const [title, setTitle] = useState(contractTitle || "");
  const [provider] = useState<SignatureProvider>("docusign");
  const [signers, setSigners] = useState<{
    email: string; name: string; title?: string; company?: string;
    role: SignerRole; signingOrder: number; routingOrder: number;
    authenticationType: string; phone?: string;
  }[]>([]);
  const [expiresInDays, setExpiresInDays] = useState(30);
  const [reminderDays, setReminderDays] = useState(3);
  const [emailSubject, setEmailSubject] = useState("");
  const [emailMessage, setEmailMessage] = useState("");
  const [allowDecline, setAllowDecline] = useState(true);
  const [allowPrint, setAllowPrint] = useState(true);
  const [showAddDialog, setShowAddDialog] = useState(false);
  const [sending, setSending] = useState(false);
  const [sent, setSent] = useState(false);

  const handleAddSigner = (signer: { email: string; name: string; role: string; signingOrder: number }) => {
    setSigners(prev => [...prev, {
      ...signer, role: signer.role as SignerRole,
      routingOrder: 1, authenticationType: "none",
    }]);
    setShowAddDialog(false);
  };

  const handleRemoveSigner = (id: string) => {
    setSigners(prev => prev.filter((_, i) => i !== parseInt(id)));
  };

  const handleSend = async () => {
    setSending(true);
    try {
      await onCreate({
        title,
        provider,
        signers,
        expiresInDays,
        reminderDays,
        emailSubject: emailSubject || undefined,
        emailMessage: emailMessage || undefined,
        allowDecline,
        allowPrint,
      });
      setSent(true);
      setTimeout(() => { onClose(); setStep(0); setSent(false); }, 1500);
    } catch { /* ignore */ }
    setSending(false);
  };

  const reset = () => {
    setStep(0);
    setTitle(contractTitle || "");
    setSigners([]);
    setExpiresInDays(30);
    setReminderDays(3);
    setEmailSubject("");
    setEmailMessage("");
    setAllowDecline(true);
    setAllowPrint(true);
    setSending(false);
    setSent(false);
  };

  if (!isOpen) return null;

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/30 z-50"
            onClick={() => { if (!sending) { onClose(); reset(); } }}
          />
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 20 }}
            className="fixed inset-0 z-50 flex items-center justify-center p-4"
          >
            <div className="bg-white rounded-xl shadow-2xl border border-gray-200 w-full max-w-lg max-h-[85vh] flex flex-col">
              {/* Header */}
              <div className="flex items-center justify-between px-5 py-4 border-b border-gray-200">
                <div className="flex items-center gap-2">
                  <FileSignature className="w-5 h-5 text-gold-500" />
                  <h2 className="text-sm font-semibold text-navy-900">Send for Signature</h2>
                </div>
                <button onClick={() => { if (!sending) { onClose(); reset(); } }}
                  className="text-gray-400 hover:text-gray-600"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              {/* Steps */}
              <div className="flex px-5 pt-3 pb-2 gap-1">
                {["Details", "Signers", "Send"].map((label, i) => (
                  <div key={label} className="flex-1 flex items-center gap-1">
                    <div className={`w-5 h-5 rounded-full flex items-center justify-center text-[9px] font-bold ${
                      i < step ? "bg-green-500 text-white" :
                      i === step ? "bg-gold-500 text-white" :
                      "bg-gray-100 text-gray-400"
                    }`}>
                      {i < step ? <Check className="w-2.5 h-2.5" /> : i + 1}
                    </div>
                    <span className={`text-[9px] ${i === step ? "text-navy-900 font-medium" : "text-gray-400"}`}>
                      {label}
                    </span>
                    {i < 2 && <div className="flex-1 h-px bg-gray-200 mx-1" />}
                  </div>
                ))}
              </div>

              {/* Content */}
              <div className="flex-1 overflow-y-auto px-5 py-3">
                {step === 0 && (
                  <div className="space-y-3">
                    <div>
                      <label className="text-[10px] font-medium text-gray-500 uppercase">Document Title</label>
                      <input type="text" value={title} onChange={e => setTitle(e.target.value)}
                        className="w-full px-2 py-1.5 text-xs border border-gray-200 rounded-lg mt-1 focus:outline-none focus:ring-1 focus:ring-gold-400"
                        placeholder="Contract title" required />
                    </div>
                    <div>
                      <label className="text-[10px] font-medium text-gray-500 uppercase">Signature Provider</label>
                      <div className="p-2 rounded-lg border border-gold-500 bg-gold-50 text-gold-700 text-[10px] font-medium text-center">
                      DocuSign (Phase 1)
                    </div>
                    </div>
                    <div>
                      <label className="text-[10px] font-medium text-gray-500 uppercase">Expires In</label>
                      <select value={expiresInDays} onChange={e => setExpiresInDays(Number(e.target.value))}
                        className="w-full px-2 py-1.5 text-xs border border-gray-200 rounded-lg mt-1 focus:outline-none focus:ring-1 focus:ring-gold-400"
                      >
                        <option value={7}>7 days</option>
                        <option value={14}>14 days</option>
                        <option value={30}>30 days</option>
                        <option value={60}>60 days</option>
                        <option value={90}>90 days</option>
                      </select>
                    </div>
                    <div>
                      <label className="text-[10px] font-medium text-gray-500 uppercase">Email Subject (optional)</label>
                      <input type="text" value={emailSubject} onChange={e => setEmailSubject(e.target.value)}
                        className="w-full px-2 py-1.5 text-xs border border-gray-200 rounded-lg mt-1 focus:outline-none focus:ring-1 focus:ring-gold-400"
                        placeholder={`Please sign: ${title || "document"}`} />
                    </div>
                  </div>
                )}

                {step === 1 && (
                  <div>
                    <SignerList
                      signers={signers.map((s, i) => ({ ...s, id: String(i), authenticationType: s.authenticationType as AuthType, status: "awaiting" as const, createdAt: new Date().toISOString() }))}
                      onAddClick={() => setShowAddDialog(true)}
                      onRemoveSigner={(id) => handleRemoveSigner(id)}
                      editable
                    />
                  </div>
                )}

                {step === 2 && (
                  <div className="space-y-3 text-center py-4">
                    <FileSignature className="w-10 h-10 text-gold-500 mx-auto" />
                    <h3 className="text-sm font-semibold text-navy-900">Ready to Send</h3>
                    <div className="text-left bg-gray-50 rounded-lg p-3 space-y-1">
                      <p className="text-[10px]"><span className="font-medium text-gray-500">Document:</span> {title}</p>
                      <p className="text-[10px]"><span className="font-medium text-gray-500">Provider:</span> {PROVIDER_LABELS[provider]}</p>
                      <p className="text-[10px]"><span className="font-medium text-gray-500">Signers:</span> {signers.length}</p>
                      <p className="text-[10px]"><span className="font-medium text-gray-500">Expires:</span> In {expiresInDays} days</p>
                    </div>
                  </div>
                )}
              </div>

              {/* Footer */}
              <div className="flex items-center justify-between px-5 py-3 border-t border-gray-100">
                {step > 0 ? (
                  <button onClick={() => setStep(step - 1)}
                    className="flex items-center gap-1 px-3 py-1.5 text-xs font-medium text-gray-600 hover:text-gray-800"
                  >
                    <ArrowLeft className="w-3 h-3" /> Back
                  </button>
                ) : <div />}
                {sent ? (
                  <div className="flex items-center gap-1 text-green-600 text-xs font-medium">
                    <Check className="w-4 h-4" /> Sent!
                  </div>
                ) : step < 2 ? (
                  <button onClick={() => setStep(step + 1)}
                    disabled={step === 0 && (!title.trim() || signers.length === 0)}
                    className="flex items-center gap-1 px-4 py-1.5 text-xs font-medium bg-gold-500 text-white rounded-lg hover:bg-gold-600 disabled:bg-gray-300"
                  >
                    Next <ArrowRight className="w-3 h-3" />
                  </button>
                ) : (
                  <button onClick={handleSend} disabled={sending}
                    className="flex items-center gap-1 px-4 py-1.5 text-xs font-medium bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:bg-gray-300"
                  >
                    {sending ? <><Loader2 className="w-3 h-3 animate-spin" /> Sending...</> : <><Send className="w-3 h-3" /> Send for Signature</>}
                  </button>
                )}
              </div>
            </div>
          </motion.div>

          <SignerAddDialog
            isOpen={showAddDialog}
            onClose={() => setShowAddDialog(false)}
            onAdd={handleAddSigner}
            nextOrder={signers.length + 1}
          />
        </>
      )}
    </AnimatePresence>
  );
}

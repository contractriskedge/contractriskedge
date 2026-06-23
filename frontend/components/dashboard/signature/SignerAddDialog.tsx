"use client";

import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X, UserPlus } from "lucide-react";

interface SignerAddDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onAdd: (signer: { email: string; name: string; role: string; signingOrder: number }) => void;
  nextOrder: number;
}

export function SignerAddDialog({ isOpen, onClose, onAdd, nextOrder }: SignerAddDialogProps) {
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [role, setRole] = useState("signer");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!email.trim() || !name.trim()) return;
    onAdd({ email: email.trim(), name: name.trim(), role, signingOrder: nextOrder });
    setEmail("");
    setName("");
    setRole("signer");
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/20 z-40"
            onClick={onClose}
          />
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 10 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 10 }}
            className="fixed inset-0 z-50 flex items-center justify-center p-4"
          >
            <div className="bg-white rounded-xl shadow-xl border border-gray-200 w-full max-w-sm">
              <div className="flex items-center justify-between px-4 py-3 border-b border-gray-100">
                <div className="flex items-center gap-2">
                  <UserPlus className="w-4 h-4 text-gold-500" />
                  <h3 className="text-sm font-semibold text-navy-900">Add Signer</h3>
                </div>
                <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
                  <X className="w-4 h-4" />
                </button>
              </div>
              <form onSubmit={handleSubmit} className="p-4 space-y-3">
                <div>
                  <label className="text-[10px] font-medium text-gray-500 uppercase">Name</label>
                  <input
                    type="text"
                    value={name}
                    onChange={e => setName(e.target.value)}
                    placeholder="Full name"
                    className="w-full px-2 py-1.5 text-xs border border-gray-200 rounded-lg mt-1 focus:outline-none focus:ring-1 focus:ring-gold-400"
                    required
                  />
                </div>
                <div>
                  <label className="text-[10px] font-medium text-gray-500 uppercase">Email</label>
                  <input
                    type="email"
                    value={email}
                    onChange={e => setEmail(e.target.value)}
                    placeholder="email@example.com"
                    className="w-full px-2 py-1.5 text-xs border border-gray-200 rounded-lg mt-1 focus:outline-none focus:ring-1 focus:ring-gold-400"
                    required
                  />
                </div>
                <div>
                  <label className="text-[10px] font-medium text-gray-500 uppercase">Role</label>
                  <select
                    value={role}
                    onChange={e => setRole(e.target.value)}
                    className="w-full px-2 py-1.5 text-xs border border-gray-200 rounded-lg mt-1 focus:outline-none focus:ring-1 focus:ring-gold-400"
                  >
                    <option value="signer">Signer</option>
                    <option value="approver">Approver</option>
                    <option value="cc">Carbon Copy (CC)</option>
                  </select>
                </div>
                <div className="flex gap-2 pt-2">
                  <button type="button" onClick={onClose}
                    className="flex-1 px-3 py-1.5 text-xs font-medium border border-gray-200 rounded-lg text-gray-600 hover:bg-gray-50"
                  >
                    Cancel
                  </button>
                  <button type="submit"
                    className="flex-1 px-3 py-1.5 text-xs font-medium bg-gold-500 text-white rounded-lg hover:bg-gold-600"
                  >
                    Add Signer
                  </button>
                </div>
              </form>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}

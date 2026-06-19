"use client";

import React, { useState } from "react";
import { useAuth } from "@/components/auth/AuthProvider";
import { Shield, AlertTriangle, Loader2, UserCheck, Eye, Scale, BookOpen } from "lucide-react";

const DEV_ROLES = [
  { id: "admin",    label: "Admin",      icon: Shield,    color: "bg-red-500 hover:bg-red-600",      desc: "Full access — upload, review, approve, configure" },
  { id: "reviewer", label: "Reviewer",   icon: BookOpen,  color: "bg-blue-500 hover:bg-blue-600",    desc: "Review, comment, resolve findings, create obligations" },
  { id: "legal",    label: "Legal Ops",  icon: Scale,     color: "bg-purple-500 hover:bg-purple-600", desc: "Approve contracts, view audit, override findings" },
  { id: "viewer",   label: "Read-Only",  icon: Eye,       color: "bg-gray-500 hover:bg-gray-600",    desc: "View and search only" },
];

export function LoginPage() {
  const { login, isLoading, error } = useAuth();
  const [selectedRole, setSelectedRole] = useState<string | null>(null);

  const handleLogin = async (role?: string) => {
    setSelectedRole(role || null);
    await login(role);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-navy-900 via-navy-800 to-navy-950 flex items-center justify-center p-4">
      <div className="w-full max-w-lg animate-fade-in">
        {/* Logo & Branding */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gold-400/20 mb-4">
            <Shield className="w-8 h-8 text-gold-400" />
          </div>
          <h1 className="text-3xl font-bold text-white mb-2">
            ContractRisk<span className="text-gold-400">Edge</span>
          </h1>
          <p className="text-navy-200 text-sm">
            AI-Powered Contract Risk Analysis Platform
          </p>
        </div>

        {/* Login Card */}
        <div className="bg-white/10 backdrop-blur-lg rounded-2xl p-8 border border-white/10">
          <h2 className="text-xl font-semibold text-white mb-2">Welcome Back</h2>
          <p className="text-navy-200 text-sm mb-6">
            Sign in to access your contract risk dashboard
          </p>

          {error && (
            <div className="flex items-center gap-2 p-3 mb-4 bg-red-500/10 border border-red-500/20 rounded-lg text-red-300 text-sm">
              <AlertTriangle className="w-4 h-4 flex-shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {/* Dev role selector */}
          {process.env.NODE_ENV === "development" && (
            <div className="mb-6 space-y-2">
              <p className="text-navy-300 text-xs font-semibold uppercase tracking-wider mb-3">
                Development — Select a role
              </p>
              {DEV_ROLES.map((role) => (
                <button
                  key={role.id}
                  onClick={() => handleLogin(role.id)}
                  disabled={isLoading && selectedRole === role.id}
                  className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg text-white text-sm font-medium transition-colors disabled:opacity-50 ${role.color}`}
                >
                  {isLoading && selectedRole === role.id ? (
                    <Loader2 className="w-5 h-5 animate-spin" />
                  ) : (
                    <role.icon className="w-5 h-5" />
                  )}
                  <div className="text-left">
                    <p className="font-semibold">{role.label}</p>
                    <p className="text-xs opacity-80">{role.desc}</p>
                  </div>
                </button>
              ))}
            </div>
          )}

          {/* Production login */}
          {process.env.NODE_ENV !== "development" && (
            <button
              onClick={() => handleLogin()}
              disabled={isLoading}
              className="w-full py-3 px-4 bg-gold-400 hover:bg-gold-500 text-navy-900 font-semibold rounded-lg transition-colors duration-150 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              {isLoading ? (
                <Loader2 className="w-5 h-5 animate-spin" />
              ) : (
                "Sign In with Auth0"
              )}
            </button>
          )}

          <div className="mt-6 pt-6 border-t border-white/10">
            <p className="text-navy-300 text-xs text-center">
              Secured by Auth0 • SOC 2 Type II Compliant • AES-256 Encrypted
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

"use client";

import React from "react";
import { useAuth } from "@/components/auth/AuthProvider";
import { Shield, AlertTriangle, Loader2 } from "lucide-react";

export function LoginPage() {
  const { login, isLoading, error } = useAuth();

  return (
    <div className="min-h-screen bg-gradient-to-br from-navy-900 via-navy-800 to-navy-950 flex items-center justify-center p-4">
      <div className="w-full max-w-md animate-fade-in">
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

          <button
            onClick={login}
            disabled={isLoading}
            className="w-full py-3 px-4 bg-gold-400 hover:bg-gold-500 text-navy-900 font-semibold rounded-lg transition-colors duration-150 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
          >
            {isLoading ? (
              <Loader2 className="w-5 h-5 animate-spin" />
            ) : process.env.NODE_ENV === "development" ? (
              "Sign In (Dev)"
            ) : (
              "Sign In with Auth0"
            )}
          </button>

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

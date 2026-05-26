"use client";

import React from "react";
import { Settings as SettingsIcon, User, Bell, Shield, Key, CreditCard } from "lucide-react";

export function SettingsPage() {
  return (
    <div className="space-y-6 animate-fade-in">
      <div>
        <h1 className="text-2xl font-bold text-navy-900">Settings</h1>
        <p className="text-sm text-gray-500 mt-1">Manage your account and platform configuration</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {[
          { icon: User, label: "Profile", desc: "Manage your personal information" },
          { icon: Bell, label: "Notifications", desc: "Configure alert preferences" },
          { icon: Shield, label: "Security", desc: "Password and authentication" },
          { icon: Key, label: "API Keys", desc: "Manage API access tokens" },
          { icon: CreditCard, label: "Billing", desc: "Subscription and invoices" },
          { icon: SettingsIcon, label: "Integrations", desc: "Connected services" },
        ].map((item) => (
          <button key={item.label} className="card p-6 text-left hover:shadow-md transition-all group">
            <item.icon className="w-6 h-6 text-navy-500 mb-3 group-hover:text-gold-500 transition-colors" />
            <h3 className="font-medium text-gray-900">{item.label}</h3>
            <p className="text-sm text-gray-500 mt-1">{item.desc}</p>
          </button>
        ))}
      </div>
    </div>
  );
}

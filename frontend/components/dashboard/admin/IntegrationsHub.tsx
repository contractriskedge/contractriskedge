"use client";

import React from "react";
import { motion } from "framer-motion";
import { Link, CheckCircle, XCircle, AlertTriangle, RefreshCw, Clock, ExternalLink } from "lucide-react";
import type { Integration } from "./types";

export function IntegrationsHub({ integrations }: { integrations: Integration[] }) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
      <div className="px-4 py-3 border-b border-gray-100">
        <div className="flex items-center gap-2"><Link className="w-4 h-4 text-navy-700" /><h3 className="text-xs font-semibold text-navy-900">Integration Hub</h3></div>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 p-3">
        {integrations.map((int) => (
          <div key={int.id} className="flex items-center gap-3 p-3 bg-white border border-gray-100 rounded-lg hover:shadow-sm transition-shadow">
            <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${int.status === "connected" ? "bg-green-50" : int.status === "error" ? "bg-red-50" : int.status === "pending" ? "bg-yellow-50" : "bg-gray-50"}`}>
              {int.status === "connected" ? <CheckCircle className="w-4 h-4 text-green-500" /> :
               int.status === "error" ? <AlertTriangle className="w-4 h-4 text-red-500" /> :
               int.status === "pending" ? <Clock className="w-4 h-4 text-yellow-500" /> :
               <XCircle className="w-4 h-4 text-gray-400" />}
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-1.5">
                <span className="text-[11px] font-semibold text-navy-900">{int.name}</span>
                <span className={`text-[9px] font-medium px-1.5 py-0.5 rounded-full ${int.status === "connected" ? "bg-green-50 text-green-700" : int.status === "error" ? "bg-red-50 text-red-700" : int.status === "pending" ? "bg-yellow-50 text-yellow-700" : "bg-gray-50 text-gray-500"}`}>{int.status}</span>
              </div>
              <p className="text-[9px] text-gray-400 mt-0.5">{int.type} • v{int.version} • {int.errorRate}% error rate</p>
              <p className="text-[8px] text-gray-300 mt-0.5">Last sync: {int.lastSync === "—" ? "Never" : formatTime(int.lastSync)}</p>
            </div>
            <button className="text-[9px] font-medium px-2 py-1 rounded-md bg-navy-50 text-navy-700 hover:bg-navy-100 transition-colors opacity-0 group-hover:opacity-100">
              <ExternalLink className="w-3 h-3" />
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}

function formatTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const hrs = Math.floor(diff / 3600000);
  if (hrs < 1) return "just now"; if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

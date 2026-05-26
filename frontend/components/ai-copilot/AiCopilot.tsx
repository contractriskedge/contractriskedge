"use client";

import React, { useState, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Bot, X, PanelRightOpen, PanelRightClose, Sparkles, Zap, MessageSquare, Lightbulb } from "lucide-react";
import { AiChat } from "./AiChat";
import { AiInsightsPanel } from "./AiInsightsPanel";
import { ActionExecutor } from "./ActionExecutor";
import { copilotContext } from "./context";
import type { CopilotMode, AiSuggestedAction } from "./types";

type PanelView = "chat" | "insights";

export function AiCopilot() {
  const [isOpen, setIsOpen] = useState(false);
  const [panelView, setPanelView] = useState<PanelView>("chat");
  const [mode, setMode] = useState<CopilotMode>("executive_intelligence");
  const [pendingAction, setPendingAction] = useState<AiSuggestedAction | null>(null);
  const [unreadInsights, setUnreadInsights] = useState(0);

  const handleModeChange = useCallback((newMode: CopilotMode) => {
    setMode(newMode);
    copilotContext.addActivity(`Switched to ${newMode} mode`);
  }, []);

  const handleExecuteAction = useCallback((action: AiSuggestedAction) => {
    if (action.requiresConfirmation) {
      setPendingAction(action);
    } else {
      // Execute immediately
      copilotContext.addActivity(`Executed: ${action.label}`);
    }
  }, []);

  const handleActionConfirm = useCallback((action: AiSuggestedAction) => {
    copilotContext.addActivity(`Executed: ${action.label}`);
    setPendingAction(null);
  }, []);

  const handleActionCancel = useCallback(() => {
    setPendingAction(null);
  }, []);

  const handleActionComplete = useCallback(() => {
    setPendingAction(null);
  }, []);

  return (
    <>
      {/* Floating toggle button */}
      <motion.button
        onClick={() => setIsOpen(!isOpen)}
        className={`fixed bottom-6 right-6 z-40 w-12 h-12 rounded-full shadow-lg flex items-center justify-center transition-all ${
          isOpen ? "bg-navy-800 rotate-45" : "bg-navy-700 hover:bg-navy-800"
        }`}
        whileHover={{ scale: 1.1 }}
        whileTap={{ scale: 0.9 }}
        aria-label={isOpen ? "Close AI Copilot" : "Open AI Copilot"}
      >
        {isOpen ? <X className="w-5 h-5 text-white" /> : <Bot className="w-5 h-5 text-white" />}
      </motion.button>

      {/* Main copilot panel */}
      <AnimatePresence>
        {isOpen && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 bg-black/10 z-30"
              onClick={() => setIsOpen(false)}
            />
            <motion.div
              initial={{ opacity: 0, y: 20, scale: 0.95 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: 20, scale: 0.95 }}
              className="fixed bottom-20 right-6 z-40 w-[420px] h-[600px] bg-white rounded-2xl border border-gray-200 shadow-2xl overflow-hidden flex flex-col"
            >
              {/* Header */}
              <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200 bg-gradient-to-r from-navy-700 to-navy-800 text-white">
                <div className="flex items-center gap-2">
                  <Bot className="w-5 h-5" />
                  <div>
                    <h2 className="text-sm font-semibold">AI Copilot</h2>
                    <p className="text-[9px] text-navy-200">Enterprise Contract Intelligence</p>
                  </div>
                </div>
                <div className="flex items-center gap-1">
                  <button
                    onClick={() => setPanelView("chat")}
                    className={`p-1.5 rounded-lg transition-colors ${panelView === "chat" ? "bg-white/20" : "hover:bg-white/10"}`}
                    title="Chat"
                  >
                    <MessageSquare className="w-4 h-4" />
                  </button>
                  <button
                    onClick={() => setPanelView("insights")}
                    className={`p-1.5 rounded-lg transition-colors relative ${panelView === "insights" ? "bg-white/20" : "hover:bg-white/10"}`}
                    title="Insights"
                  >
                    <Lightbulb className="w-4 h-4" />
                    {unreadInsights > 0 && (
                      <span className="absolute -top-0.5 -right-0.5 w-3.5 h-3.5 bg-red-500 text-white text-[7px] font-bold rounded-full flex items-center justify-center">
                        {unreadInsights}
                      </span>
                    )}
                  </button>
                  <button
                    onClick={() => setIsOpen(false)}
                    className="p-1.5 rounded-lg hover:bg-white/10 transition-colors ml-1"
                  >
                    <PanelRightClose className="w-4 h-4" />
                  </button>
                </div>
              </div>

              {/* Body */}
              <div className="flex-1 overflow-hidden">
                {panelView === "chat" ? (
                  <AiChat mode={mode} onModeChange={handleModeChange} onExecuteAction={handleExecuteAction} />
                ) : (
                  <div className="p-3 overflow-y-auto h-full">
                    <AiInsightsPanel onExecuteAction={handleExecuteAction} />
                  </div>
                )}
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>

      {/* Action Executor */}
      <ActionExecutor
        action={pendingAction}
        onConfirm={handleActionConfirm}
        onCancel={handleActionCancel}
        onComplete={handleActionComplete}
      />
    </>
  );
}

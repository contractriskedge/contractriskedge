"use client";

import React from "react";
import { motion } from "framer-motion";
import {
  Search, FileText, Brain, Edit3, MessageSquare, ThumbsUp,
  CheckCircle, ArrowRight, Check,
} from "lucide-react";

type WorkflowStep =
  | "open"
  | "findings"
  | "review"
  | "rewrite"
  | "comment"
  | "vote"
  | "approve"
  | "resolve"
  | "complete";

const STEPS: { id: WorkflowStep; label: string; icon: React.ReactNode }[] = [
  { id: "open", label: "Open", icon: <Search className="w-3 h-3" /> },
  { id: "findings", label: "Findings", icon: <FileText className="w-3 h-3" /> },
  { id: "review", label: "Review", icon: <Brain className="w-3 h-3" /> },
  { id: "rewrite", label: "Rewrite", icon: <Edit3 className="w-3 h-3" /> },
  { id: "comment", label: "Comment", icon: <MessageSquare className="w-3 h-3" /> },
  { id: "vote", label: "Vote", icon: <ThumbsUp className="w-3 h-3" /> },
  { id: "approve", label: "Approve", icon: <CheckCircle className="w-3 h-3" /> },
  { id: "resolve", label: "Resolve", icon: <Check className="w-3 h-3" /> },
];

// Map workflow steps to drawer tabs for navigation
export const WORKFLOW_TO_TAB: Record<WorkflowStep, string> = {
  open: "overview",
  findings: "overview",
  review: "overview",
  rewrite: "rewrite",
  comment: "comments",
  vote: "voting",
  approve: "voting",
  resolve: "overview",
  complete: "overview",
};

interface WorkflowStepperProps {
  currentStep: WorkflowStep;
  onStepClick?: (step: WorkflowStep) => void;
}

export function WorkflowStepper({ currentStep, onStepClick }: WorkflowStepperProps) {
  const currentIdx = STEPS.findIndex(s => s.id === currentStep);

  return (
    <div className="bg-white dark:bg-navy-800 border-b border-gray-200 dark:border-navy-700">
      <div className="px-3 py-1.5 flex items-center gap-0 overflow-x-auto">
        {STEPS.map((step, idx) => {
          const isCompleted = idx < currentIdx;
          const isCurrent = idx === currentIdx;
          const isFuture = idx > currentIdx;

          return (
            <React.Fragment key={step.id}>
              <button
                onClick={() => onStepClick?.(step.id)}
                className={`flex items-center gap-1 px-2 py-1 rounded-md text-[9px] font-medium whitespace-nowrap transition-all ${
                  isCompleted
                    ? "text-green-600 hover:bg-green-50"
                    : isCurrent
                    ? "text-white bg-navy-700 shadow-sm"
                    : "text-gray-400 hover:text-gray-600 hover:bg-gray-50"
                }`}
                disabled={isFuture}
              >
                <span className={`${isCompleted ? "text-green-500" : isCurrent ? "text-white" : "text-gray-400"}`}>
                  {isCompleted ? <Check className="w-2.5 h-2.5" /> : step.icon}
                </span>
                <span>{step.label}</span>
              </button>
              {idx < STEPS.length - 1 && (
                <div className={`flex-shrink-0 w-4 h-px mx-0.5 ${
                  idx < currentIdx ? "bg-green-400" : "bg-gray-200 dark:bg-navy-600"
                }`} />
              )}
            </React.Fragment>
          );
        })}
      </div>
    </div>
  );
}

export type { WorkflowStep };

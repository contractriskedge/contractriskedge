"use client";

import React, { useState } from "react";
import { motion } from "framer-motion";
import { Clock, AlertTriangle, User, MessageSquare, Paperclip, ChevronRight, Inbox, Brain, Scale, ShoppingCart, Shield, DollarSign, UserCheck, PenSquare, CheckCircle } from "lucide-react";
import type { WorkflowItem, WorkflowStageType } from "./types";
import { WORKFLOW_STAGES, STAGE_ORDER, PRIORITY_CONFIG, RISK_BG, RISK_BG_LIGHT, RISK_TEXT } from "./types";

const stageIcons: Record<string, React.ReactNode> = {
  intake: <Inbox className="w-3.5 h-3.5" />, ai_review: <Brain className="w-3.5 h-3.5" />,
  legal_review: <Scale className="w-3.5 h-3.5" />, procurement_review: <ShoppingCart className="w-3.5 h-3.5" />,
  security_review: <Shield className="w-3.5 h-3.5" />, finance_approval: <DollarSign className="w-3.5 h-3.5" />,
  executive_approval: <UserCheck className="w-3.5 h-3.5" />, signature: <PenSquare className="w-3.5 h-3.5" />,
  completed: <CheckCircle className="w-3.5 h-3.5" />,
};

function WorkflowCard({ item }: { item: WorkflowItem }) {
  const pCfg = PRIORITY_CONFIG[item.priority];
  return (
    <motion.div layout initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
      className="bg-white rounded-lg border border-gray-200 shadow-sm p-3 space-y-2 hover:shadow-md transition-all cursor-pointer group">
      <div className="flex items-start justify-between gap-1">
        <h4 className="text-[11px] font-semibold text-navy-900 leading-tight line-clamp-2">{item.contractName}</h4>
        <span className={`text-[9px] font-medium px-1.5 py-0.5 rounded-full whitespace-nowrap ${pCfg.bg} ${pCfg.color}`}>{item.priority}</span>
      </div>
      <p className="text-[10px] text-gray-500">{item.vendor}</p>
      <div className="flex items-center gap-1.5 text-[10px] text-gray-500">
        <User className="w-3 h-3" /><span className="truncate">{item.assignedTo}</span>
      </div>
      <div className="flex items-center justify-between pt-1 border-t border-gray-50">
        <div className="flex items-center gap-1">
          {item.slaRemaining < 0 ? (
            <span className="text-[9px] font-medium text-red-600 flex items-center gap-0.5"><AlertTriangle className="w-3 h-3" />{-item.slaRemaining}h overdue</span>
          ) : item.slaRemaining < 24 ? (
            <span className="text-[9px] font-medium text-orange-600 flex items-center gap-0.5"><Clock className="w-3 h-3" />{item.slaRemaining}h left</span>
          ) : (
            <span className="text-[9px] text-gray-400">{Math.floor(item.slaRemaining / 24)}d left</span>
          )}
        </div>
        <div className="flex items-center gap-1">
          {item.comments.filter((c) => !c.resolved).length > 0 && (
            <span className="text-[9px] text-navy-500 flex items-center gap-0.5"><MessageSquare className="w-3 h-3" />{item.comments.filter((c) => !c.resolved).length}</span>
          )}
          {item.attachments > 0 && <span className="text-[9px] text-gray-400"><Paperclip className="w-3 h-3" /></span>}
        </div>
      </div>
    </motion.div>
  );
}

interface KanbanBoardProps {
  workflows: WorkflowItem[];
  onSelectWorkflow: (w: WorkflowItem) => void;
}

export function KanbanBoard({ workflows, onSelectWorkflow }: KanbanBoardProps) {
  const [expandedStages, setExpandedStages] = useState<Set<string>>(new Set(STAGE_ORDER.map((s) => s)));

  const grouped = STAGE_ORDER.reduce((acc, stage) => {
    acc[stage] = workflows.filter((w) => w.currentStage === stage);
    return acc;
  }, {} as Record<string, WorkflowItem[]>);

  const toggleStage = (stage: string) => {
    setExpandedStages((prev) => {
      const next = new Set(prev);
      next.has(stage) ? next.delete(stage) : next.add(stage);
      return next;
    });
  };

  return (
    <div className="flex gap-3 overflow-x-auto pb-2" style={{ minHeight: 300 }}>
      {STAGE_ORDER.map((stageId) => {
        const stage = WORKFLOW_STAGES.find((s) => s.id === stageId)!;
        const items = grouped[stageId] || [];
        const isExpanded = expandedStages.has(stageId);
        const avgSla = items.length > 0 ? items.reduce((s, i) => s + i.slaRemaining, 0) / items.length : 0;
        const overdue = items.filter((i) => i.slaRemaining < 0).length;

        return (
          <div key={stageId} className="flex-shrink-0 w-64 bg-gray-50 rounded-xl border border-gray-200 flex flex-col max-h-[600px]">
            {/* Stage header */}
            <div
              onClick={() => toggleStage(stageId)}
              className="flex items-center justify-between px-3 py-2.5 border-b border-gray-200 cursor-pointer hover:bg-gray-100/50 transition-colors"
            >
              <div className="flex items-center gap-2">
                <div className={`w-7 h-7 rounded-lg flex items-center justify-center ${stage.bg}`}>
                  {stageIcons[stageId] || <Inbox className="w-3.5 h-3.5" />}
                </div>
                <div>
                  <p className="text-[11px] font-semibold text-navy-900">{stage.label}</p>
                  <p className="text-[9px] text-gray-400">{items.length} items • {overdue > 0 && <span className="text-red-500">{overdue} overdue</span>}</p>
                </div>
              </div>
              <ChevronRight className={`w-3.5 h-3.5 text-gray-300 transition-transform ${isExpanded ? "rotate-90" : ""}`} />
            </div>

            {/* Stage body */}
            {isExpanded && (
              <div className="flex-1 overflow-y-auto p-2 space-y-2">
                {items.length === 0 ? (
                  <div className="text-center py-6 text-gray-400 text-[10px]">No items</div>
                ) : (
                  items.map((item) => (
                    <div key={item.id} onClick={() => onSelectWorkflow(item)}>
                      <WorkflowCard item={item} />
                    </div>
                  ))
                )}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

/**
 * Contract Detail Workspace — Enterprise 3-panel layout.
 *
 * LEFT:   Document viewer (PDF/text rendering, page navigation, zoom, search, highlights)
 * CENTER: AI review workspace (findings, clause deviations, compliance issues)
 * RIGHT:  Metadata/context panel (contract details, risk summary, activity timeline)
 *
 * Features:
 * - Collapsible panels with sticky action bar
 * - Bidirectional synchronization between AI findings and document highlights
 * - Real-time activity timeline with audit events
 * - Collaborative commenting with @mentions and threaded discussions
 * - Enterprise-grade information hierarchy
 */

"use client";

import React from "react";
import { ContractDetailWorkspace } from "@/components/contract-detail/ContractDetailWorkspace";

export default function ContractDetailPage({
  params,
}: {
  params: { contractId: string };
}) {
  // Use key={contractId} to force a full remount when navigating between contracts.
  // This ensures all React Query hooks re-fire with clean state for the new contract.
  return <ContractDetailWorkspace key={params.contractId} contractId={params.contractId} />;
}

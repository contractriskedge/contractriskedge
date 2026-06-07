// ── Backend Graph Schema Types (from GET /api/v1/relationships/graph) ───────

export type NodeType =
  | "review" | "upload" | "finding" | "redline"
  | "negotiation" | "obligation" | "workflow" | "vendor";

export type EdgeType =
  | "uploaded_as" | "reviewed_in" | "redlined_in"
  | "negotiates" | "obligates" | "workflow_for" | "vendor_for";

export type GraphMode =
  | "relationship" | "risk_propagation" | "financial_exposure"
  | "vendor_ecosystem" | "compliance_dependency" | "renewal_timeline" | "obligation_flow";

export interface GraphNodeData {
  id: string;
  type: NodeType;
  label: string;
  tenant_id: string;
  metadata: Record<string, unknown>;
  // D3 layout fields (set by D3 simulation)
  x?: number;
  y?: number;
  fx?: number | null;
  fy?: number | null;
  vx?: number;
  vy?: number;
}

export interface GraphEdgeData {
  id: string;
  source: string;
  target: string;
  type: EdgeType;
  label: string;
  metadata: Record<string, unknown>;
}

export interface GraphData {
  nodes: GraphNodeData[];
  edges: GraphEdgeData[];
}

export interface RelationshipGraphResponse {
  nodes: GraphNodeData[];
  edges: GraphEdgeData[];
  total_nodes: number;
  total_edges: number;
  generated_at: string;
}

export interface GraphKpi {
  id: string;
  label: string;
  value: string;
  trend: number;
  trendDirection: "up" | "down" | "neutral";
  icon: string;
  color: string;
  severity: "critical" | "warning" | "success" | "info";
  tooltip: string;
}

export interface RelationshipInsight {
  id: string;
  title: string;
  description: string;
  severity: "critical" | "warning" | "info" | "success";
  confidence: number;
  impactedContracts: string[];
  suggestedAction: string;
  category: string;
  quickActions: { label: string; action: string }[];
}

export interface TimelineEvent {
  id: string;
  date: string;
  type: "amendment" | "renewal" | "signature" | "review" | "compliance" | "obligation";
  title: string;
  description: string;
  contracts: string[];
}

export const NODE_COLORS: Record<NodeType, string> = {
  review: "#6366F1",
  upload: "#06B6D4",
  finding: "#EF4444",
  redline: "#F59E0B",
  negotiation: "#8B5CF6",
  obligation: "#22C55E",
  workflow: "#3B82F6",
  vendor: "#F97316",
};

export const EDGE_COLORS: Record<EdgeType, string> = {
  uploaded_as: "#6366F1",
  reviewed_in: "#EF4444",
  redlined_in: "#F59E0B",
  negotiates: "#8B5CF6",
  obligates: "#22C55E",
  workflow_for: "#3B82F6",
  vendor_for: "#F97316",
};

export const NODE_LABELS: Record<NodeType, string> = {
  review: "REV",
  upload: "DOC",
  finding: "FND",
  redline: "RED",
  negotiation: "NEG",
  obligation: "OBL",
  workflow: "WF",
  vendor: "VDR",
};

export const GRAPH_MODES: { id: GraphMode; label: string; icon: string; description: string }[] = [
  { id: "relationship", label: "Relationships", icon: "Share2", description: "Standard contract relationship view" },
  { id: "risk_propagation", label: "Risk Propagation", icon: "AlertTriangle", description: "Risk flow through dependencies" },
  { id: "financial_exposure", label: "Financial Exposure", icon: "DollarSign", description: "Financial value propagation" },
  { id: "vendor_ecosystem", label: "Vendor Ecosystem", icon: "Building2", description: "Vendor-centric relationship view" },
  { id: "compliance_dependency", label: "Compliance", icon: "Shield", description: "Compliance requirement chains" },
  { id: "renewal_timeline", label: "Renewals", icon: "RefreshCw", description: "Upcoming renewal dependencies" },
  { id: "obligation_flow", label: "Obligations", icon: "ClipboardCheck", description: "Obligation tracking chains" },
];

export const RISK_BG = { critical: "bg-red-500", high: "bg-orange-500", medium: "bg-yellow-500", low: "bg-green-500", info: "bg-blue-500" };
export const RISK_TEXT = { critical: "text-red-700", high: "text-orange-700", medium: "text-yellow-700", low: "text-green-700", info: "text-blue-700" };
export const RISK_BG_LIGHT = { critical: "bg-red-50", high: "bg-orange-50", medium: "bg-yellow-50", low: "bg-green-50", info: "bg-blue-50" };

/** Extract a human-readable status from a node's metadata. */
export function getNodeStatus(node: GraphNodeData): string {
  return (node.metadata?.status as string) || "";
}

/** Extract risk severity from a node's metadata. */
export function getNodeSeverity(node: GraphNodeData): string {
  return (node.metadata?.severity as string) || (node.metadata?.risk_level as string) || "info";
}

/** Get a display label for a node type. */
export function getNodeTypeLabel(type: NodeType): string {
  const labels: Record<NodeType, string> = {
    review: "Review", upload: "Document", finding: "Finding",
    redline: "Redline", negotiation: "Negotiation", obligation: "Obligation",
    workflow: "Workflow", vendor: "Vendor",
  };
  return labels[type] || type;
}

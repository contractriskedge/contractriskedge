// ── Enterprise Relationship Graph Types ─────────────────────────────────────

export type NodeType =
  | "master_service_agreement" | "amendment" | "statement_of_work" | "dpa"
  | "nda" | "license" | "addendum" | "vendor" | "business_unit"
  | "obligation" | "insurance" | "compliance" | "procurement";

export type EdgeType =
  | "parent_child" | "amendment" | "dependency" | "renewal"
  | "obligation" | "financial_exposure" | "compliance_link" | "sla_link";

export type GraphMode =
  | "relationship" | "risk_propagation" | "financial_exposure"
  | "vendor_ecosystem" | "compliance_dependency" | "renewal_timeline" | "obligation_flow";

export type RiskLevel = "critical" | "high" | "medium" | "low" | "info";

export interface GraphNodeData {
  id: string;
  label: string;
  type: NodeType;
  riskScore: number;
  riskLevel: RiskLevel;
  status: string;
  vendor?: string;
  businessUnit?: string;
  geography?: string;
  financialValue?: number;
  expiryDate?: string;
  owner?: string;
  depth: number;
  cluster?: number;
  // D3 layout
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
  strength: number;
  animated: boolean;
}

export interface GraphData {
  nodes: GraphNodeData[];
  edges: GraphEdgeData[];
  metadata: {
    totalNodes: number;
    totalEdges: number;
    clusters: number;
    highRiskChains: number;
    avgDepth: number;
  };
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
  master_service_agreement: "#6366F1",
  amendment: "#F59E0B",
  statement_of_work: "#06B6D4",
  dpa: "#EC4899",
  nda: "#22C55E",
  license: "#8B5CF6",
  addendum: "#14B8A6",
  vendor: "#F97316",
  business_unit: "#3B82F6",
  obligation: "#EF4444",
  insurance: "#0EA5E9",
  compliance: "#84CC16",
  procurement: "#A855F7",
};

export const EDGE_COLORS: Record<EdgeType, string> = {
  parent_child: "#6366F1",
  amendment: "#F59E0B",
  dependency: "#EF4444",
  renewal: "#22C55E",
  obligation: "#F97316",
  financial_exposure: "#DC2626",
  compliance_link: "#84CC16",
  sla_link: "#06B6D4",
};

export const NODE_LABELS: Record<NodeType, string> = {
  master_service_agreement: "MSA",
  amendment: "AMD",
  statement_of_work: "SOW",
  dpa: "DPA",
  nda: "NDA",
  license: "LIC",
  addendum: "ADD",
  vendor: "VDR",
  business_unit: "BU",
  obligation: "OBL",
  insurance: "INS",
  compliance: "CMP",
  procurement: "PRO",
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

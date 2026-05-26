// ── Enterprise Relationship Graph Mock Data ─────────────────────────────────

import type { GraphData, GraphKpi, RelationshipInsight, TimelineEvent } from "./types";

function rand(min: number, max: number) { return Math.floor(Math.random() * (max - min + 1)) + min; }

// ── Generate a complex graph with ~80 nodes and ~120 edges ──────────────────

const vendors = ["Acme Corp", "GlobalTech Inc", "DataSync Partners", "CloudServ Ltd", "SecureNet Solutions", "InnoVate LLC", "Pacific Rim Trading", "EuroLegal Partners"];
const businessUnits = ["North America", "EMEA", "APAC", "LATAM"];
const geographies = ["US", "DE", "JP", "GB", "CA", "IN", "FR", "SG"];
const owners = ["Alice Chen", "Bob Martinez", "Carol Singh", "David Kim"];

// Master agreements
const msas = [
  { id: "MSA-101", vendor: "Acme Corp", bu: "North America", geo: "US", risk: 8, value: 5.2 },
  { id: "MSA-102", vendor: "GlobalTech Inc", bu: "EMEA", geo: "DE", risk: 7, value: 3.8 },
  { id: "MSA-103", vendor: "DataSync Partners", bu: "APAC", geo: "SG", risk: 6, value: 2.9 },
  { id: "MSA-104", vendor: "CloudServ Ltd", bu: "North America", geo: "US", risk: 5, value: 4.1 },
  { id: "MSA-105", vendor: "SecureNet Solutions", bu: "EMEA", geo: "GB", risk: 9, value: 3.5 },
  { id: "MSA-106", vendor: "InnoVate LLC", bu: "APAC", geo: "JP", risk: 4, value: 1.8 },
  { id: "MSA-107", vendor: "Pacific Rim Trading", bu: "LATAM", geo: "BR", risk: 7, value: 2.2 },
  { id: "MSA-108", vendor: "EuroLegal Partners", bu: "EMEA", geo: "FR", risk: 3, value: 1.5 },
];

function generateGraph(): GraphData {
  const nodes: GraphData["nodes"] = [];
  const edges: GraphData["edges"] = [];
  let nodeId = 0;
  let edgeId = 0;

  // Add master agreements
  msas.forEach((msa, i) => {
    nodes.push({
      id: msa.id, label: `${msa.vendor} MSA`, type: "master_service_agreement",
      riskScore: msa.risk, riskLevel: msa.risk >= 8 ? "critical" : msa.risk >= 6 ? "high" : msa.risk >= 4 ? "medium" : "low",
      status: "active", vendor: msa.vendor, businessUnit: msa.bu, geography: msa.geo,
      financialValue: msa.value, owner: owners[i % owners.length], depth: 0, cluster: i,
    });

    // Add vendor node
    const vendorId = `V-${msa.vendor.replace(/\s/g, "")}`;
    if (!nodes.find((n) => n.id === vendorId)) {
      nodes.push({
        id: vendorId, label: msa.vendor, type: "vendor",
        riskScore: msa.risk, riskLevel: msa.risk >= 8 ? "critical" : msa.risk >= 6 ? "high" : msa.risk >= 4 ? "medium" : "low",
        status: "active", vendor: msa.vendor, depth: 0, cluster: i,
      });
      edges.push({ id: `E${edgeId++}`, source: vendorId, target: msa.id, type: "parent_child", label: "CONTRACT", strength: 1, animated: false });
    }

    // Add business unit node
    const buId = `BU-${msa.bu.replace(/\s/g, "")}`;
    if (!nodes.find((n) => n.id === buId)) {
      nodes.push({
        id: buId, label: msa.bu, type: "business_unit",
        riskScore: rand(3, 6), riskLevel: "medium", status: "active", depth: 0, cluster: i,
      });
    }

    // Amendments (1-3 per MSA)
    const numAmendments = rand(1, 3);
    for (let a = 0; a < numAmendments; a++) {
      const amdId = `${msa.id}-AMD-${a + 1}`;
      nodes.push({
        id: amdId, label: `Amendment ${a + 1}`, type: "amendment",
        riskScore: Math.min(10, msa.risk + rand(-2, 2)), riskLevel: "medium",
        status: "active", vendor: msa.vendor, financialValue: +(msa.value * 0.15).toFixed(1), depth: 1, cluster: i,
      });
      edges.push({ id: `E${edgeId++}`, source: msa.id, target: amdId, type: "amendment", label: "AMENDS", strength: 0.8, animated: true });
    }

    // SOWs (1-2 per MSA)
    const numSows = rand(1, 2);
    for (let s = 0; s < numSows; s++) {
      const sowId = `${msa.id}-SOW-${s + 1}`;
      nodes.push({
        id: sowId, label: `SOW ${s + 1}`, type: "statement_of_work",
        riskScore: Math.min(10, msa.risk + rand(-1, 3)), riskLevel: "high",
        status: "active", vendor: msa.vendor, financialValue: +(msa.value * 0.3).toFixed(1), depth: 1, cluster: i,
      });
      edges.push({ id: `E${edgeId++}`, source: msa.id, target: sowId, type: "parent_child", label: "SCOPE", strength: 0.9, animated: false });
    }

    // DPAs (some MSAs have them)
    if (i % 2 === 0) {
      const dpaId = `${msa.id}-DPA`;
      nodes.push({
        id: dpaId, label: "DPA", type: "dpa",
        riskScore: Math.min(10, msa.risk + 1), riskLevel: "high",
        status: "active", vendor: msa.vendor, geography: msa.geo, depth: 1, cluster: i,
      });
      edges.push({ id: `E${edgeId++}`, source: msa.id, target: dpaId, type: "compliance_link", label: "COMPLIES", strength: 0.7, animated: false });
    }

    // Obligations
    const numObl = rand(1, 2);
    for (let o = 0; o < numObl; o++) {
      const oblId = `${msa.id}-OBL-${o + 1}`;
      nodes.push({
        id: oblId, label: `Obligation ${o + 1}`, type: "obligation",
        riskScore: Math.min(10, msa.risk + rand(0, 2)), riskLevel: "critical",
        status: "pending", vendor: msa.vendor, depth: 2, cluster: i,
      });
      edges.push({ id: `E${edgeId++}`, source: msa.id, target: oblId, type: "obligation", label: "OWES", strength: 0.6, animated: true });
    }

    // Cross-dependencies between MSAs
    if (i > 0) {
      const prevMsa = msas[i - 1];
      edges.push({
        id: `E${edgeId++}`, source: msa.id, target: prevMsa.id,
        type: "dependency", label: "DEPENDS", strength: 0.3, animated: true,
      });
    }
  });

  // Add some cross-vendor dependencies
  edges.push({ id: `E${edgeId++}`, source: "MSA-101", target: "MSA-105", type: "dependency", label: "SHARED_SLA", strength: 0.4, animated: true });
  edges.push({ id: `E${edgeId++}`, source: "MSA-103", target: "MSA-107", type: "financial_exposure", label: "$2.1M", strength: 0.5, animated: true });

  // Add insurance nodes
  ["INS-Acme", "INS-GlobalTech", "INS-SecureNet"].forEach((insId, i) => {
    const msa = i === 0 ? msas[0] : i === 1 ? msas[1] : msas[4];
    nodes.push({
      id: insId, label: "Insurance Policy", type: "insurance",
      riskScore: rand(2, 5), riskLevel: "low", status: "active",
      vendor: msa.vendor, depth: 1, cluster: i * 2,
    });
    edges.push({ id: `E${edgeId++}`, source: msa.id, target: insId, type: "compliance_link", label: "INSURES", strength: 0.5, animated: false });
  });

  return {
    nodes,
    edges,
    metadata: {
      totalNodes: nodes.length,
      totalEdges: edges.length,
      clusters: msas.length,
      highRiskChains: 12,
      avgDepth: 1.4,
    },
  };
}

export const mockGraphData = generateGraph();

// ── KPI Metrics ─────────────────────────────────────────────────────────────

export const graphKpis: GraphKpi[] = [
  { id: "total-nodes", label: "Relationship Nodes", value: `${mockGraphData.metadata.totalNodes}`, trend: 8.3, trendDirection: "up", icon: "Share2", color: "from-navy-600 to-navy-800", severity: "info", tooltip: "Total contract and entity nodes in the relationship graph" },
  { id: "connected", label: "Connected Contracts", value: `${mockGraphData.metadata.totalNodes - 8}`, trend: 12.5, trendDirection: "up", icon: "Link", color: "from-blue-500 to-blue-700", severity: "info", tooltip: "Contracts with at least one relationship connection" },
  { id: "risk-chains", label: "High-Risk Chains", value: "12", trend: 20.0, trendDirection: "up", icon: "AlertTriangle", color: "from-red-500 to-orange-500", severity: "critical", tooltip: "Dependency chains containing high-risk contracts" },
  { id: "amendments", label: "Amendments", value: "16", trend: 6.7, trendDirection: "up", icon: "FileEdit", color: "from-amber-500 to-yellow-500", severity: "warning", tooltip: "Total amendments across all agreements" },
  { id: "obligations", label: "Active Obligations", value: "14", trend: -12.5, trendDirection: "down", icon: "ClipboardCheck", color: "from-green-500 to-emerald-500", severity: "success", tooltip: "Active contractual obligations being tracked" },
  { id: "clusters", label: "Vendor Clusters", value: `${mockGraphData.metadata.clusters}`, trend: 0, trendDirection: "neutral", icon: "Layers", color: "from-purple-500 to-indigo-500", severity: "info", tooltip: "Distinct vendor relationship clusters" },
  { id: "cross-bu", label: "Cross-BU Dependencies", value: "8", trend: 14.3, trendDirection: "up", icon: "Building2", color: "from-cyan-500 to-blue-500", severity: "warning", tooltip: "Dependencies spanning multiple business units" },
  { id: "orphaned", label: "Orphaned Agreements", value: "3", trend: -40.0, trendDirection: "down", icon: "Unlink", color: "from-gray-500 to-gray-600", severity: "info", tooltip: "Contracts with no parent or child relationships" },
];

// ── AI Insights ─────────────────────────────────────────────────────────────

export const relationshipInsights: RelationshipInsight[] = [
  { id: "ri-1", title: "Termination Impact: MSA-102", description: "Termination of GlobalTech Inc MSA would impact 14 downstream agreements including 3 SOWs, 2 amendments, and 9 obligation chains across EMEA region.", severity: "critical", confidence: 94, impactedContracts: ["MSA-102", "MSA-102-SOW-1", "MSA-102-SOW-2", "MSA-102-AMD-1", "MSA-102-AMD-2", "MSA-102-OBL-1", "MSA-102-OBL-2"], suggestedAction: "Review termination clause cascading effects. Consider phased transition plan.", category: "dependency", quickActions: [{ label: "View Chain", action: "chain" }, { label: "Impact Report", action: "report" }] },
  { id: "ri-2", title: "Vendor Concentration Risk", description: "Acme Corp and SecureNet Solutions form a critical dependency cluster. Combined termination could affect 35% of active obligations.", severity: "critical", confidence: 88, impactedContracts: ["MSA-101", "MSA-105", "MSA-101-SOW-1", "MSA-105-SOW-1", "MSA-101-OBL-1", "MSA-105-OBL-1"], suggestedAction: "Develop vendor diversification strategy for critical dependencies.", category: "vendor", quickActions: [{ label: "Concentration Map", action: "map" }, { label: "Risk Assessment", action: "assessment" }] },
  { id: "ri-3", title: "Cross-Region Compliance Dependency", description: "DataSync Partners MSA (Singapore) has DPA dependencies with Pacific Rim Trading (Brazil). Cross-region data flow compliance gap detected.", severity: "warning", confidence: 82, impactedContracts: ["MSA-103", "MSA-107", "MSA-103-DPA"], suggestedAction: "Review cross-border data transfer agreements. Ensure GDPR/LGPD compliance.", category: "compliance", quickActions: [{ label: "Compliance View", action: "compliance" }, { label: "Legal Review", action: "legal" }] },
  { id: "ri-4", title: "Amendment Liability Chain", description: "5 amendments across 3 MSAs modify liability obligations. Cumulative exposure of $8.2M identified through amendment chain analysis.", severity: "warning", confidence: 85, impactedContracts: ["MSA-101-AMD-1", "MSA-101-AMD-2", "MSA-102-AMD-1", "MSA-105-AMD-1", "MSA-105-AMD-2"], suggestedAction: "Audit amendment liability modifications. Consolidate exposure report.", category: "financial", quickActions: [{ label: "Liability Chain", action: "chain" }, { label: "Exposure Report", action: "report" }] },
  { id: "ri-5", title: "Renewal Dependency Alert", description: "3 MSAs expiring in Q3 have 8 downstream agreements with staggered renewal dates. Coordinated renewal strategy recommended.", severity: "info", confidence: 76, impactedContracts: ["MSA-104", "MSA-106", "MSA-108", "MSA-104-SOW-1", "MSA-106-SOW-1", "MSA-108-SOW-1"], suggestedAction: "Initiate coordinated renewal negotiations for MSA cluster.", category: "renewal", quickActions: [{ label: "Renewal Timeline", action: "timeline" }, { label: "Strategy Session", action: "strategy" }] },
  { id: "ri-6", title: "Obligation Propagation Risk", description: "14 active obligations propagate across 6 contract chains. 4 obligations in 2 chains are overdue, creating cascading compliance risk.", severity: "critical", confidence: 91, impactedContracts: ["MSA-101-OBL-1", "MSA-101-OBL-2", "MSA-105-OBL-1", "MSA-102-OBL-1"], suggestedAction: "Escalate overdue obligations. Implement automated obligation tracking.", category: "obligation", quickActions: [{ label: "Obligation Map", action: "map" }, { label: "Escalate All", action: "escalate" }] },
];

// ── Timeline Events ─────────────────────────────────────────────────────────

export const timelineEvents: TimelineEvent[] = [
  { id: "tl-1", date: "2026-05-14", type: "obligation", title: "Obligation Due: SOC2 Report", description: "SecureNet Solutions SOC2 Type II report submission due", contracts: ["MSA-105"] },
  { id: "tl-2", date: "2026-05-10", type: "amendment", title: "Amendment Executed: MSA-101-AMD-3", description: "Liability cap amendment for Acme Corp MSA executed", contracts: ["MSA-101", "MSA-101-AMD-3"] },
  { id: "tl-3", date: "2026-05-01", type: "renewal", title: "Renewal Notice: CloudServ Ltd", description: "30-day renewal notice sent for CloudServ Ltd MSA", contracts: ["MSA-104"] },
  { id: "tl-4", date: "2026-04-28", type: "compliance", title: "DPA Compliance Review", description: "Annual DPA compliance review completed for all EU vendors", contracts: ["MSA-102", "MSA-105", "MSA-108"] },
  { id: "tl-5", date: "2026-04-15", type: "signature", title: "New SOW: DataSync Q2 Engagement", description: "Q2 statement of work signed with DataSync Partners", contracts: ["MSA-103", "MSA-103-SOW-2"] },
  { id: "tl-6", date: "2026-04-10", type: "review", title: "Quarterly Risk Review", description: "Q2 risk review completed for all vendor relationships", contracts: ["MSA-101", "MSA-102", "MSA-103", "MSA-104", "MSA-105"] },
  { id: "tl-7", date: "2026-03-25", type: "amendment", title: "Amendment: Pacific Rim Pricing", description: "Pricing amendment for Pacific Rim Trading MSA executed", contracts: ["MSA-107", "MSA-107-AMD-1"] },
  { id: "tl-8", date: "2026-03-15", type: "obligation", title: "Insurance Certificate Renewal", description: "Cyber liability insurance certificates renewed for all vendors", contracts: ["MSA-101", "MSA-102", "MSA-105"] },
];

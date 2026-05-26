"use client";

import React, { useEffect, useRef, useState, useCallback } from "react";
import * as d3 from "d3";
import { useAuth } from "@/components/auth/AuthProvider";
import * as api from "@/lib/api";

// ── Types ───────────────────────────────────────────────────────────────────

interface RelationshipNode {
  contract_id: string;
  contract_data?: {
    filename?: string;
    contract_type?: string;
    risk_score?: number;
    status?: string;
    [key: string]: any;
  };
  relationship_type?: string;
  children: RelationshipNode[];
}

interface RelationshipData {
  contract_id: string;
  tree: RelationshipNode;
  total_nodes: number;
}

interface GraphNode {
  id: string;
  label: string;
  type: string;
  riskScore: number;
  status: string;
  depth: number;
  x?: number;
  y?: number;
  fx?: number | null;
  fy?: number | null;
}

interface GraphLink {
  source: string | GraphNode;
  target: string | GraphNode;
  relationshipType: string;
}

// ── Helpers ─────────────────────────────────────────────────────────────────

function flattenTree(
  node: RelationshipNode,
  depth: number = 0,
  nodes: Map<string, GraphNode> = new Map(),
  links: GraphLink[] = []
): { nodes: Map<string, GraphNode>; links: GraphLink[] } {
  if (!nodes.has(node.contract_id)) {
    const data = node.contract_data || {};
    nodes.set(node.contract_id, {
      id: node.contract_id,
      label: data.filename || node.contract_id.slice(0, 8) + "...",
      type: data.contract_type || "unknown",
      riskScore: data.risk_score ?? 0.25,
      status: data.status || "unknown",
      depth,
    });
  }

  for (const child of node.children) {
    links.push({
      source: node.contract_id,
      target: child.contract_id,
      relationshipType: child.relationship_type || "child",
    });
    flattenTree(child, depth + 1, nodes, links);
  }

  return { nodes, links };
}

function getRiskColor(score: number): string {
  if (score >= 0.7) return "#ef4444"; // red
  if (score >= 0.4) return "#f59e0b"; // amber
  return "#22c55e"; // green
}

function getTypeIcon(type: string): string {
  const icons: Record<string, string> = {
    master_service_agreement: "MSA",
    nda: "NDA",
    statement_of_work: "SOW",
    license: "LIC",
    service_agreement: "SA",
    employment: "EMP",
    lease: "LSE",
    amendment: "AMD",
    addendum: "ADD",
    dpa: "DPA",
  };
  return icons[type] || "CTR";
}

function getRelationshipColor(type: string): string {
  const colors: Record<string, string> = {
    parent: "#6366f1",
    child: "#8b5cf6",
    amendment: "#f59e0b",
    addendum: "#06b6d4",
    dpa: "#ec4899",
  };
  return colors[type] || "#94a3b8";
}

// ── Component ───────────────────────────────────────────────────────────────

interface RelationshipGraphProps {
  contractId?: string;
  width?: number;
  height?: number;
}

export function RelationshipGraph({
  contractId,
  width = 900,
  height = 600,
}: RelationshipGraphProps) {
  const { token } = useAuth();
  const svgRef = useRef<SVGSVGElement>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<RelationshipData | null>(null);
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [inputContractId, setInputContractId] = useState(contractId || "");

  const fetchGraph = useCallback(
    async (cid: string) => {
      if (!token || !cid) return;
      setLoading(true);
      setError(null);
      try {
        const res = await fetch(
          `${process.env.NEXT_PUBLIC_API_URL || "/api/v1"}/contracts/${cid}/relationship-tree?max_depth=5`,
          { headers: { Authorization: `Bearer ${token}` } }
        );
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const json: RelationshipData = await res.json();
        setData(json);
      } catch (err: any) {
        setError(err.message || "Failed to load relationship graph");
      } finally {
        setLoading(false);
      }
    },
    [token]
  );

  useEffect(() => {
    if (contractId) {
      setInputContractId(contractId);
      fetchGraph(contractId);
    }
  }, [contractId, fetchGraph]);

  // Draw the D3 force graph
  useEffect(() => {
    if (!data || !svgRef.current) return;

    const { nodes: nodeMap, links: linkData } = flattenTree(data.tree);
    const nodesArray = Array.from(nodeMap.values());
    const svg = d3.select(svgRef.current);
    svg.selectAll("*").remove();

    const g = svg.append("g");

    // Zoom behavior
    const zoom = d3.zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.1, 4])
      .on("zoom", (event) => {
        g.attr("transform", event.transform);
      });
    svg.call(zoom);

    // Tooltip
    const tooltip = d3.select("body")
      .append("div")
      .attr("class", "relationship-tooltip")
      .style("position", "absolute")
      .style("background", "rgba(15, 23, 42, 0.95)")
      .style("color", "#fff")
      .style("padding", "10px 14px")
      .style("border-radius", "8px")
      .style("font-size", "12px")
      .style("pointer-events", "none")
      .style("opacity", "0")
      .style("z-index", "1000")
      .style("box-shadow", "0 4px 12px rgba(0,0,0,0.3)")
      .style("max-width", "300px")
      .style("line-height", "1.5");

    // Create force simulation
    const simulation = d3.forceSimulation<GraphNode>(nodesArray)
      .force(
        "link",
        d3.forceLink<GraphNode, GraphLink>(linkData)
          .id((d) => d.id)
          .distance(120)
          .strength(0.3)
      )
      .force("charge", d3.forceManyBody().strength(-300))
      .force("center", d3.forceCenter(width / 2, height / 2))
      .force("collision", d3.forceCollide().radius(40));

    // Draw links
    const link = g
      .append("g")
      .selectAll<SVGLineElement, GraphLink>("line")
      .data(linkData)
      .join("line")
      .attr("stroke", (d) => getRelationshipColor(d.relationshipType))
      .attr("stroke-width", 2)
      .attr("stroke-opacity", 0.6)
      .attr("stroke-dasharray", (d) =>
        d.relationshipType === "amendment" || d.relationshipType === "addendum"
          ? "5,5"
          : "none"
      );

    // Draw link labels
    const linkLabel = g
      .append("g")
      .selectAll<SVGTextElement, GraphLink>("text")
      .data(linkData)
      .join("text")
      .text((d) => d.relationshipType.toUpperCase())
      .attr("font-size", "8px")
      .attr("fill", "#94a3b8")
      .attr("text-anchor", "middle")
      .attr("dy", "-6");

    // Draw nodes
    const node = g
      .append("g")
      .selectAll<SVGGElement, GraphNode>("g")
      .data(nodesArray)
      .join("g")
      .style("cursor", "pointer")
      .on("mouseover", function (event, d) {
        tooltip
          .style("opacity", "1")
          .html(`
            <strong>${d.label}</strong><br/>
            Type: ${d.type}<br/>
            Risk Score: ${(d.riskScore * 100).toFixed(0)}%<br/>
            Status: ${d.status}<br/>
            ID: ${d.id.slice(0, 12)}...
          `);
      })
      .on("mousemove", function (event) {
        tooltip
          .style("left", event.pageX + 14 + "px")
          .style("top", event.pageY - 10 + "px");
      })
      .on("mouseout", function () {
        tooltip.style("opacity", "0");
      })
      .on("click", function (event, d) {
        setSelectedNode(d);
      })
      // @ts-ignore - d3 drag type
      .call(
        d3
          .drag<SVGGElement, GraphNode>()
          .on("start", (event, d) => {
            if (!event.active) simulation.alphaTarget(0.3).restart();
            d.fx = d.x;
            d.fy = d.y;
          })
          .on("drag", (event, d) => {
            d.fx = event.x;
            d.fy = event.y;
          })
          .on("end", (event, d) => {
            if (!event.active) simulation.alphaTarget(0);
            d.fx = null;
            d.fy = null;
          })
      );

    // Node circles
    node
      .append("circle")
      .attr("r", 22)
      .attr("fill", (d) => getRiskColor(d.riskScore))
      .attr("stroke", "#1e293b")
      .attr("stroke-width", 2);

    // Node type labels
    node
      .append("text")
      .text((d) => getTypeIcon(d.type))
      .attr("text-anchor", "middle")
      .attr("dy", "0.35em")
      .attr("fill", "#fff")
      .attr("font-size", "10px")
      .attr("font-weight", "bold");

    // Node name labels
    node
      .append("text")
      .text((d) => d.label.length > 18 ? d.label.slice(0, 16) + "..." : d.label)
      .attr("text-anchor", "middle")
      .attr("dy", 34)
      .attr("fill", "#cbd5e1")
      .attr("font-size", "10px");

    // Simulation tick
    simulation.on("tick", () => {
      link
        .attr("x1", (d: any) => d.source.x)
        .attr("y1", (d: any) => d.source.y)
        .attr("x2", (d: any) => d.target.x)
        .attr("y2", (d: any) => d.target.y);

      linkLabel
        .attr("x", (d: any) => (d.source.x + d.target.x) / 2)
        .attr("y", (d: any) => (d.source.y + d.target.y) / 2);

      node.attr("transform", (d: any) => `translate(${d.x},${d.y})`);
    });

    return () => {
      simulation.stop();
      tooltip.remove();
    };
  }, [data, width, height]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (inputContractId.trim()) {
      fetchGraph(inputContractId.trim());
    }
  };

  return (
    <div className="space-y-4">
      {/* Search / Controls */}
      <div className="flex items-center gap-4 flex-wrap">
        <form onSubmit={handleSearch} className="flex items-center gap-2">
          <input
            type="text"
            value={inputContractId}
            onChange={(e) => setInputContractId(e.target.value)}
            placeholder="Enter contract ID..."
            className="px-3 py-2 bg-navy-800 border border-navy-600 rounded-lg text-sm text-white placeholder-navy-400 w-72 focus:outline-none focus:ring-2 focus:ring-gold-400"
          />
          <button
            type="submit"
            disabled={loading || !token}
            className="px-4 py-2 bg-gold-500 hover:bg-gold-400 text-navy-900 font-medium rounded-lg text-sm transition-colors disabled:opacity-50"
          >
            {loading ? "Loading..." : "View Graph"}
          </button>
        </form>

        {/* Legend */}
        <div className="flex items-center gap-3 text-xs text-navy-300">
          <span className="flex items-center gap-1">
            <span className="w-3 h-0.5 bg-indigo-400 inline-block" /> Parent
          </span>
          <span className="flex items-center gap-1">
            <span className="w-3 h-0.5 bg-violet-400 inline-block" /> Child
          </span>
          <span className="flex items-center gap-1">
            <span className="w-3 h-0.5 bg-amber-400 inline-block" style={{ borderTop: "2px dashed #f59e0b", height: 0, width: 12 }} /> Amendment
          </span>
          <span className="flex items-center gap-1">
            <span className="w-3 h-0.5 bg-cyan-400 inline-block" style={{ borderTop: "2px dashed #06b6d4", height: 0, width: 12 }} /> Addendum
          </span>
          <span className="flex items-center gap-1">
            <span className="w-3 h-0.5 bg-pink-400 inline-block" /> DPA
          </span>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="p-3 bg-red-900/30 border border-red-700 rounded-lg text-red-300 text-sm">
          {error}
        </div>
      )}

      {/* Graph */}
      <div className="relative bg-navy-900 rounded-xl border border-navy-700 overflow-hidden">
        {loading && (
          <div className="absolute inset-0 flex items-center justify-center bg-navy-900/70 z-10">
            <div className="text-navy-300 text-sm">Loading relationship graph...</div>
          </div>
        )}
        <svg
          ref={svgRef}
          width={width}
          height={height}
          className="w-full"
          style={{ minHeight: height }}
        />
      </div>

      {/* Selected Node Info */}
      {selectedNode && (
        <div className="p-4 bg-navy-800 rounded-xl border border-navy-700">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-white font-medium text-sm">Selected Contract</h3>
            <button
              onClick={() => setSelectedNode(null)}
              className="text-navy-400 hover:text-white text-xs"
            >
              Close
            </button>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
            <div>
              <span className="text-navy-400 block">ID</span>
              <span className="text-white font-mono text-xs">{selectedNode.id}</span>
            </div>
            <div>
              <span className="text-navy-400 block">Filename</span>
              <span className="text-white">{selectedNode.label}</span>
            </div>
            <div>
              <span className="text-navy-400 block">Type</span>
              <span className="text-white">{selectedNode.type}</span>
            </div>
            <div>
              <span className="text-navy-400 block">Risk Score</span>
              <span
                className="font-medium"
                style={{ color: getRiskColor(selectedNode.riskScore) }}
              >
                {(selectedNode.riskScore * 100).toFixed(0)}%
              </span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

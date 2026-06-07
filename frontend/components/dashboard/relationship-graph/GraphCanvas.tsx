"use client";

import React, { useRef, useEffect, useState, useCallback } from "react";
import * as d3 from "d3";
import { motion } from "framer-motion";
import { ZoomIn, ZoomOut, Maximize2, Minimize2, RotateCcw } from "lucide-react";
import type { GraphData, GraphNodeData, GraphEdgeData, NodeType, EdgeType, GraphMode } from "./types";
import { NODE_COLORS, EDGE_COLORS, NODE_LABELS } from "./types";

interface GraphCanvasProps {
  data: GraphData;
  mode: GraphMode;
  onNodeSelect: (node: GraphNodeData | null) => void;
  selectedNodeId: string | null;
  filterVendor: string;
  filterType: string;
  filterRisk: string;
}

export function GraphCanvas({ data, mode, onNodeSelect, selectedNodeId, filterVendor, filterType, filterRisk }: GraphCanvasProps) {
  const svgRef = useRef<SVGSVGElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const zoomRef = useRef<d3.ZoomBehavior<SVGSVGElement, unknown> | null>(null);
  const [dimensions, setDimensions] = useState({ width: 900, height: 600 });
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [zoomLevel, setZoomLevel] = useState(1);

  // Filter nodes based on metadata fields
  const filteredData = React.useMemo(() => {
    let nodes = data.nodes;
    let edges = data.edges;
    if (filterVendor) {
      nodes = nodes.filter((n) => {
        const vendor = n.metadata?.counterparty as string || n.metadata?.vendor_name as string || n.metadata?.name as string || "";
        return vendor.toLowerCase().includes(filterVendor.toLowerCase());
      });
    }
    if (filterType) nodes = nodes.filter((n) => n.type === filterType);
    if (filterRisk) {
      nodes = nodes.filter((n) => {
        const severity = (n.metadata?.severity as string || n.metadata?.risk_level as string || "info").toLowerCase();
        if (filterRisk === "critical") return severity === "critical";
        if (filterRisk === "high") return severity === "critical" || severity === "high";
        if (filterRisk === "medium") return severity === "critical" || severity === "high" || severity === "medium";
        return true;
      });
    }
    const nodeIds = new Set(nodes.map((n) => n.id));
    edges = edges.filter((e) => nodeIds.has(e.source) && nodeIds.has(e.target));
    return { nodes, edges };
  }, [data, filterVendor, filterType, filterRisk]);

  // Resize observer
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;
    const observer = new ResizeObserver((entries) => {
      for (const entry of entries) {
        setDimensions({ width: entry.contentRect.width, height: entry.contentRect.height });
      }
    });
    observer.observe(container);
    return () => observer.disconnect();
  }, []);

  // D3 force simulation
  useEffect(() => {
    if (!svgRef.current || filteredData.nodes.length === 0) return;

    const { width, height } = dimensions;
    const svg = d3.select(svgRef.current);
    svg.selectAll("*").remove();

    const g = svg.append("g");

    // Zoom
    const zoom = d3.zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.1, 4])
      .on("zoom", (event) => {
        g.attr("transform", event.transform);
        setZoomLevel(event.transform.k);
      });
    zoomRef.current = zoom;
    svg.call(zoom);

    // Tooltip
    const tooltip = d3.select("body").append("div")
      .attr("class", "graph-tooltip")
      .style("position", "absolute").style("background", "#fff").style("border", "1px solid #e5e7eb")
      .style("border-radius", "8px").style("padding", "10px 14px").style("font-size", "11px")
      .style("box-shadow", "0 4px 12px rgba(0,0,0,0.1)").style("pointer-events", "none")
      .style("opacity", "0").style("z-index", "1000").style("max-width", "280px");

    // Node sizing based on type
    const nodeRadius = (d: GraphNodeData) => {
      if (d.type === "review") return 26;
      if (d.type === "vendor") return 24;
      if (d.type === "upload") return 22;
      if (d.type === "finding") return 18;
      if (d.type === "negotiation") return 20;
      if (d.type === "obligation") return 18;
      return 16;
    };

    const nodeColor = (d: GraphNodeData) => {
      if (mode === "risk_propagation") {
        const sev = (d.metadata?.severity as string || d.metadata?.risk_level as string || "info").toLowerCase();
        return sev === "critical" ? "#EF4444" : sev === "high" ? "#F97316" : sev === "medium" ? "#EAB308" : "#22C55E";
      }
      return NODE_COLORS[d.type] || "#6B7280";
    };

    const edgeWidth = (_d: GraphEdgeData) => 1.5;

    const edgeColor = (d: GraphEdgeData) => {
      return EDGE_COLORS[d.type] || "#94A3B8";
    };

    // Create simulation
    const simulation = d3.forceSimulation<GraphNodeData>(filteredData.nodes)
      .force("link", d3.forceLink<GraphNodeData, GraphEdgeData>(filteredData.edges)
        .id((d) => d.id).distance(140).strength(0.4))
      .force("charge", d3.forceManyBody().strength(-400))
      .force("center", d3.forceCenter(width / 2, height / 2))
      .force("collision", d3.forceCollide().radius(50));

    // Draw edges
    const link = g.append("g").selectAll<SVGLineElement, GraphEdgeData>("line")
      .data(filteredData.edges).join("line")
      .attr("stroke", (d) => edgeColor(d))
      .attr("stroke-width", (d) => edgeWidth(d))
      .attr("stroke-opacity", 0.5)
      .attr("stroke-dasharray", (d) => d.type === "vendor_for" ? "6,4" : "none")
      .attr("marker-end", "url(#arrowhead)");

    // Edge labels
    const edgeLabel = g.append("g").selectAll<SVGTextElement, GraphEdgeData>("text")
      .data(filteredData.edges).join("text")
      .text((d) => d.label)
      .attr("font-size", "7px").attr("fill", "#9CA3AF").attr("text-anchor", "middle").attr("dy", "-8");

    // Draw nodes
    const node = g.append("g").selectAll<SVGGElement, GraphNodeData>("g")
      .data(filteredData.nodes).join("g")
      .style("cursor", "pointer")
      .on("mouseover", function (event, d) {
        const status = (d.metadata?.status as string) || (d.metadata?.resolution as string) || "";
        const severity = (d.metadata?.severity as string) || (d.metadata?.risk_level as string) || "";
        const counterparty = (d.metadata?.counterparty as string) || (d.metadata?.vendor_name as string) || (d.metadata?.name as string) || "";
        const stage = (d.metadata?.stage as string) || (d.metadata?.workflow_stage as string) || "";
        tooltip.style("opacity", "1").html(`
          <strong style="color:#1B3A6B">${d.label}</strong><br/>
          <span style="color:#6B7280">Type: ${d.type}</span><br/>
          ${severity ? `<span style="color:#6B7280">Severity: ${severity}</span><br/>` : ""}
          ${status ? `<span style="color:#6B7280">Status: ${status}</span><br/>` : ""}
          ${stage ? `<span style="color:#6B7280">Stage: ${stage}</span><br/>` : ""}
          ${counterparty ? `<span style="color:#6B7280">Counterparty: ${counterparty}</span>` : ""}
        `);
        d3.select(this).select("circle").transition().duration(200).attr("r", (dd: any) => nodeRadius(dd) + 4);
      })
      .on("mousemove", (event) => tooltip.style("left", (event.pageX + 14) + "px").style("top", (event.pageY - 10) + "px"))
      .on("mouseout", function () {
        tooltip.style("opacity", "0");
        d3.select(this).select("circle").transition().duration(200).attr("r", (d: any) => nodeRadius(d));
      })
      .on("click", (event, d) => {
        onNodeSelect(d);
        event.stopPropagation();
      })
      .call(d3.drag<SVGGElement, GraphNodeData>()
        .on("start", (event, d) => { if (!event.active) simulation.alphaTarget(0.3).restart(); d.fx = d.x; d.fy = d.y; })
        .on("drag", (event, d) => { d.fx = event.x; d.fy = event.y; })
        .on("end", (event, d) => { if (!event.active) simulation.alphaTarget(0); d.fx = null; d.fy = null; })
      );

    // Node circles
    node.append("circle")
      .attr("r", (d) => nodeRadius(d))
      .attr("fill", (d) => nodeColor(d))
      .attr("stroke", (d) => d.id === selectedNodeId ? "#C9A84C" : "#fff")
      .attr("stroke-width", (d) => d.id === selectedNodeId ? 3 : 1.5)
      .attr("filter", (d) => d.id === selectedNodeId ? "url(#glow)" : "none");

    // Node type labels
    node.append("text")
      .text((d) => NODE_LABELS[d.type] || "?")
      .attr("text-anchor", "middle").attr("dy", "0.35em")
      .attr("fill", "#fff").attr("font-size", "9px").attr("font-weight", "bold");

    // Node name labels
    node.append("text")
      .text((d) => d.label.length > 14 ? d.label.slice(0, 12) + "…" : d.label)
      .attr("text-anchor", "middle").attr("dy", (d) => nodeRadius(d) + 14)
      .attr("fill", "#4B5563").attr("font-size", "8px");

    // Pulse animation for high-risk nodes
    const pulseNodes = filteredData.nodes.filter((n) => (n.metadata?.severity as string) === "critical" || (n.metadata?.risk_level as string) === "critical");
    pulseNodes.forEach((d) => {
      const idx = filteredData.nodes.indexOf(d);
      const circle = node.filter((_, i) => i === idx).select("circle");
      circle.append("animate")
        .attr("attributeName", "r")
        .attr("values", `${nodeRadius(d)};${nodeRadius(d) + 6};${nodeRadius(d)}`)
        .attr("dur", "2s")
        .attr("repeatCount", "indefinite");
    });

    // Click on background to deselect
    svg.on("click", () => onNodeSelect(null));

    // Simulation tick
    simulation.on("tick", () => {
      link.attr("x1", (d: any) => d.source.x).attr("y1", (d: any) => d.source.y)
          .attr("x2", (d: any) => d.target.x).attr("y2", (d: any) => d.target.y);
      edgeLabel.attr("x", (d: any) => (d.source.x + d.target.x) / 2)
               .attr("y", (d: any) => (d.source.y + d.target.y) / 2);
      node.attr("transform", (d: any) => `translate(${d.x},${d.y})`);
    });

    // Zoom to fit
    const initialZoom = () => {
      const bounds = (g.node() as SVGGElement)?.getBBox();
      if (bounds) {
        const scale = Math.min(width / (bounds.width + 100), height / (bounds.height + 100), 1.2);
        const tx = width / 2 - (bounds.x + bounds.width / 2) * scale;
        const ty = height / 2 - (bounds.y + bounds.height / 2) * scale;
        svg.transition().duration(500).call(zoom.transform, d3.zoomIdentity.translate(tx, ty).scale(scale));
        setZoomLevel(scale);
      }
    };
    setTimeout(initialZoom, 100);

    return () => { simulation.stop(); tooltip.remove(); };
  }, [filteredData, dimensions, mode, selectedNodeId, onNodeSelect]);

  const applyZoomTransform = (transform: d3.ZoomTransform, duration = 0) => {
    if (!svgRef.current || !zoomRef.current) return;
    const svg = d3.select<SVGSVGElement, unknown>(svgRef.current);
    const transition = duration > 0 ? svg.transition().duration(duration) : svg;
    transition.call(zoomRef.current.transform, transform);
    setZoomLevel(transform.k);
  };

  const handleZoomIn = () => {
    if (!svgRef.current) return;
    const current = d3.zoomTransform(svgRef.current);
    applyZoomTransform(current.scale(Math.min(current.k * 1.3, 4)), 300);
  };
  const handleZoomOut = () => {
    if (!svgRef.current) return;
    const current = d3.zoomTransform(svgRef.current);
    applyZoomTransform(current.scale(Math.max(current.k * 0.7, 0.1)), 300);
  };
  const handleReset = () => {
    applyZoomTransform(d3.zoomIdentity, 500);
  };
  const toggleFullscreen = () => {
    if (!containerRef.current) return;
    if (!isFullscreen) {
      containerRef.current.requestFullscreen?.();
    } else {
      document.exitFullscreen?.();
    }
    setIsFullscreen(!isFullscreen);
  };

  return (
    <div ref={containerRef} className={`relative bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden ${isFullscreen ? "fixed inset-0 z-50" : ""}`}>
      {/* Controls overlay */}
      <div className="absolute top-3 right-3 z-10 flex flex-col gap-1">
        <button onClick={handleZoomIn} className="p-1.5 bg-white border border-gray-200 rounded-lg shadow-sm hover:bg-gray-50 text-gray-500 transition-colors" title="Zoom in"><ZoomIn className="w-3.5 h-3.5" /></button>
        <button onClick={handleZoomOut} className="p-1.5 bg-white border border-gray-200 rounded-lg shadow-sm hover:bg-gray-50 text-gray-500 transition-colors" title="Zoom out"><ZoomOut className="w-3.5 h-3.5" /></button>
        <button onClick={handleReset} className="p-1.5 bg-white border border-gray-200 rounded-lg shadow-sm hover:bg-gray-50 text-gray-500 transition-colors" title="Reset view"><RotateCcw className="w-3.5 h-3.5" /></button>
        <button onClick={toggleFullscreen} className="p-1.5 bg-white border border-gray-200 rounded-lg shadow-sm hover:bg-gray-50 text-gray-500 transition-colors" title="Toggle fullscreen">
          {isFullscreen ? <Minimize2 className="w-3.5 h-3.5" /> : <Maximize2 className="w-3.5 h-3.5" />}
        </button>
      </div>

      {/* Legend overlay */}
      <div className="absolute bottom-3 left-3 z-10 bg-white/90 backdrop-blur-sm border border-gray-200 rounded-lg p-2.5 text-[10px] space-y-1">
        <p className="font-semibold text-navy-700 text-[9px] uppercase">Legend</p>
        {Object.entries(NODE_COLORS).slice(0, 6).map(([type, color]) => (
          <div key={type} className="flex items-center gap-1.5">
            <div className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: color }} />
            <span className="text-gray-500">{type.replace(/_/g, " ")}</span>
          </div>
        ))}
      </div>

      {/* Zoom indicator */}
      <div className="absolute bottom-3 right-3 z-10 bg-white/90 backdrop-blur-sm border border-gray-200 rounded-lg px-2 py-1 text-[10px] text-gray-500">
        {Math.round(zoomLevel * 100)}%
      </div>

      {/* SVG */}
      <svg id="graph-canvas-svg" ref={svgRef} width={dimensions.width} height={dimensions.height} className="w-full" style={{ minHeight: 500 }}>
        <defs>
          <filter id="glow">
            <feGaussianBlur stdDeviation="3" result="coloredBlur" />
            <feMerge><feMergeNode in="coloredBlur" /><feMergeNode in="SourceGraphic" /></feMerge>
          </filter>
          <marker id="arrowhead" viewBox="0 0 10 10" refX="20" refY="5" markerWidth="6" markerHeight="6" orient="auto">
            <polygon points="0 0, 10 5, 0 10" fill="#94A3B8" />
          </marker>
        </defs>
      </svg>

      {/* Empty state */}
      {filteredData.nodes.length === 0 && (
        <div className="absolute inset-0 flex items-center justify-center text-gray-400 bg-gray-50/50">
          <div className="text-center"><Share2Icon /><p className="text-sm font-medium mt-2">No nodes match filters</p><p className="text-xs mt-0.5">Try adjusting your filter criteria</p></div>
        </div>
      )}
    </div>
  );
}

function Share2Icon() {
  return (
    <svg className="w-10 h-10 mx-auto text-gray-300" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M7.217 10.907a2.25 2.25 0 100 2.186m0-2.186c.18.324.283.696.283 1.093s-.103.77-.283 1.093m0-2.186l9.566-5.314m-9.566 7.5l9.566 5.314m0 0a2.25 2.25 0 103.935 2.186 2.25 2.25 0 00-3.935-2.186zm0-12.814a2.25 2.25 0 103.933-2.185 2.25 2.25 0 00-3.933 2.185z" />
    </svg>
  );
}

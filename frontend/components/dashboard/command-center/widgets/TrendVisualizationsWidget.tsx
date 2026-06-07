/**
 * TrendVisualizationsWidget — Risk Trend, Exposure Trend, Review Volume Trend,
 * Throughput Trend.
 *
 * Shows line charts for each trend dimension over the selected period.
 * Data sourced from executive aggregation layer — no hardcoded defaults.
 */

"use client";

import React from "react";
import type {
  RiskScoreTrendPoint,
  ReviewVolumeTrendPoint,
  ExposureTrendPoint,
  ThroughputTrendPoint,
} from "@/src/lib/executive/executiveTypes";

interface TrendVisualizationsWidgetProps {
  riskTrend?: RiskScoreTrendPoint[];
  volumeTrend?: ReviewVolumeTrendPoint[];
  exposureTrend?: ExposureTrendPoint[];
  throughputTrend?: ThroughputTrendPoint[];
}

/** Simple inline sparkline SVG chart — no external charting library needed. */
function MiniSparkline({
  data,
  color = "#3B82F6",
  height = 40,
  width = 120,
}: {
  data: { value: number; label: string }[];
  color?: string;
  height?: number;
  width?: number;
}) {
  if (data.length === 0) {
    return (
      <div className="flex items-center justify-center text-[10px] text-gray-400" style={{ height }}>
        Minimum 2 data points required
      </div>
    );
  }
  if (data.length < 2) {
    return (
      <div className="flex items-center justify-center text-[10px] text-gray-400" style={{ height }}>
        Collecting historical data — {data.length}/2 periods
      </div>
    );
  }

  const values = data.map((d) => d.value);
  const max = Math.max(...values, 1);
  const min = Math.min(...values, 0);
  const range = Math.max(max - min, 1);

  const padding = 2;
  const chartW = width - padding * 2;
  const chartH = height - padding * 2;
  const stepX = chartW / (data.length - 1);

  const points = values.map((v, i) => {
    const x = padding + i * stepX;
    const y = padding + chartH - ((v - min) / range) * chartH;
    return `${x},${y}`;
  });

  const polyline = points.join(" ");

  return (
    <svg width={width} height={height} className="overflow-visible">
      {/* Grid lines */}
      <line x1={padding} y1={padding} x2={padding + chartW} y2={padding} stroke="#E5E7EB" strokeWidth="0.5" />
      <line x1={padding} y1={padding + chartH / 2} x2={padding + chartW} y2={padding + chartH / 2} stroke="#E5E7EB" strokeWidth="0.5" />
      <line x1={padding} y1={padding + chartH} x2={padding + chartW} y2={padding + chartH} stroke="#E5E7EB" strokeWidth="0.5" />
      {/* Area fill */}
      <polygon
        points={`${padding},${padding + chartH} ${polyline} ${padding + chartW},${padding + chartH}`}
        fill={color}
        fillOpacity="0.1"
      />
      {/* Line */}
      <polyline
        points={polyline}
        fill="none"
        stroke={color}
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      {/* End dot */}
      <circle cx={points[points.length - 1].split(",")[0]} cy={points[points.length - 1].split(",")[1]} r="2.5" fill={color} />
    </svg>
  );
}

function TrendCard({
  title,
  currentValue,
  unit,
  trend,
  color,
  data,
}: {
  title: string;
  currentValue: string;
  unit: string;
  trend: "up" | "down" | "stable";
  color: string;
  data: { value: number; label: string }[];
}) {
  const trendIcon = trend === "up" ? "↑" : trend === "down" ? "↓" : "→";
  const trendColor = trend === "up" ? "text-red-500" : trend === "down" ? "text-green-500" : "text-gray-400";

  return (
    <div className="p-3 rounded-lg bg-gray-50 dark:bg-navy-700">
      <div className="flex items-center justify-between mb-1">
        <span className="text-[10px] text-gray-500 dark:text-gray-400 uppercase font-medium">{title}</span>
        <span className={`text-xs font-bold ${trendColor}`}>{trendIcon}</span>
      </div>
      <div className="flex items-baseline gap-1">
        <span className="text-lg font-bold text-navy-900 dark:text-white">{currentValue}</span>
        <span className="text-[10px] text-gray-400">{unit}</span>
      </div>
      <div className="mt-1">
        <MiniSparkline data={data} color={color} height={36} width={140} />
      </div>
    </div>
  );
}

export function TrendVisualizationsWidget({
  riskTrend,
  volumeTrend,
  exposureTrend,
  throughputTrend,
}: TrendVisualizationsWidgetProps) {
  const hasAnyData = (riskTrend?.length ?? 0) > 0 ||
    (volumeTrend?.length ?? 0) > 0 ||
    (exposureTrend?.length ?? 0) > 0 ||
    (throughputTrend?.length ?? 0) > 0;

  if (!hasAnyData) {
    return (
      <div className="flex flex-col items-center justify-center py-8 text-center">
        <div className="w-10 h-10 rounded-full bg-gray-100 dark:bg-navy-700 flex items-center justify-center mb-2">
          <svg className="w-5 h-5 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 12l3-3 3 3 4-4M8 21l4-4 4 4M3 4h18M4 4h16v12a1 1 0 01-1 1H5a1 1 0 01-1-1V4z" />
          </svg>
        </div>
        <p className="text-sm font-medium text-gray-500 dark:text-gray-400">No trend data available</p>
        <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">Trend data will appear once sufficient history is collected.</p>
      </div>
    );
  }

  // Compute current values and trends
  const riskData = (riskTrend ?? []).map((p) => ({ value: p.avg_risk_score, label: p.period }));
  const lastRisk = riskData.length > 0 ? riskData[riskData.length - 1].value : 0;
  const firstRisk = riskData.length > 1 ? riskData[0].value : lastRisk;
  const riskDirection = riskData.length > 1 ? (lastRisk > firstRisk ? "up" : lastRisk < firstRisk ? "down" : "stable") : "stable";

  const volData = (volumeTrend ?? []).map((p) => ({ value: p.reviews_created, label: p.period }));
  const lastVol = volData.length > 0 ? volData[volData.length - 1].value : 0;
  const firstVol = volData.length > 1 ? volData[0].value : lastVol;
  const volDirection = volData.length > 1 ? (lastVol > firstVol ? "up" : lastVol < firstVol ? "down" : "stable") : "stable";

  const expData = (exposureTrend ?? []).map((p) => ({ value: p.exposure_score, label: p.period }));
  const lastExp = expData.length > 0 ? expData[expData.length - 1].value : 0;
  const firstExp = expData.length > 1 ? expData[0].value : lastExp;
  const expDirection = expData.length > 1 ? (lastExp > firstExp ? "up" : lastExp < firstExp ? "down" : "stable") : "stable";

  const tpData = (throughputTrend ?? []).map((p) => ({ value: p.contracts_completed, label: p.period }));
  const lastTp = tpData.length > 0 ? tpData[tpData.length - 1].value : 0;
  const firstTp = tpData.length > 1 ? tpData[0].value : lastTp;
  const tpDirection = tpData.length > 1 ? (lastTp > firstTp ? "up" : lastTp < firstTp ? "down" : "stable") : "stable";

  return (
    <div className="space-y-3">
      <div className="grid grid-cols-2 gap-2">
        <TrendCard
          title="Risk Trend"
          currentValue={lastRisk.toFixed(2)}
          unit="avg score"
          trend={riskDirection}
          color="#EF4444"
          data={riskData}
        />
        <TrendCard
          title="Exposure Trend"
          currentValue={lastExp.toFixed(1)}
          unit="weighted score"
          trend={expDirection}
          color="#F59E0B"
          data={expData}
        />
        <TrendCard
          title="Review Volume"
          currentValue={lastVol.toFixed(0)}
          unit="created"
          trend={volDirection}
          color="#3B82F6"
          data={volData}
        />
        <TrendCard
          title="Throughput"
          currentValue={lastTp.toFixed(0)}
          unit="completed"
          trend={tpDirection}
          color="#10B981"
          data={tpData}
        />
      </div>
    </div>
  );
}

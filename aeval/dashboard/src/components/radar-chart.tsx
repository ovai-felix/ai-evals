"use client";

import {
  RadarChart as RechartsRadar,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
  Legend,
  ResponsiveContainer,
} from "recharts";

const COLORS = ["#3b82f6", "#22c55e", "#f59e0b", "#ef4444", "#a855f7"];

export function RadarChartView({
  data,
  models,
}: {
  data: Record<string, string | number>[];
  models: string[];
}) {
  if (data.length === 0) return null;

  return (
    <ResponsiveContainer width="100%" height={400}>
      <RechartsRadar data={data} cx="50%" cy="50%" outerRadius="80%">
        <PolarGrid stroke="#334155" />
        <PolarAngleAxis
          dataKey="eval_name"
          tick={{ fill: "#94a3b8", fontSize: 12 }}
        />
        <PolarRadiusAxis
          angle={90}
          domain={[0, 1]}
          tick={{ fill: "#64748b", fontSize: 10 }}
          tickFormatter={(v: number) => `${(v * 100).toFixed(0)}%`}
        />
        {models.map((model, i) => (
          <Radar
            key={model}
            name={model}
            dataKey={model}
            stroke={COLORS[i % COLORS.length]}
            fill={COLORS[i % COLORS.length]}
            fillOpacity={0.15}
          />
        ))}
        <Legend
          wrapperStyle={{ color: "#94a3b8", fontSize: 12 }}
        />
      </RechartsRadar>
    </ResponsiveContainer>
  );
}

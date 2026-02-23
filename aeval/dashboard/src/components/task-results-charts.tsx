"use client";

import { useMemo } from "react";
import {
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  ScatterChart,
  Scatter,
  CartesianGrid,
} from "recharts";
import type { TaskResult } from "@/lib/types";

const COLOR = {
  success: "#22c55e",
  danger: "#ef4444",
  dangerDim: "#7f1d1d",
  accent: "#3b82f6",
  warning: "#f59e0b",
  surface: "#1e293b",
  border: "#334155",
  textSecondary: "#94a3b8",
  textPrimary: "#f8fafc",
} as const;

/* ---------- custom tooltip ---------- */
function ChartTooltip({
  active,
  payload,
  label,
}: {
  active?: boolean;
  payload?: { name: string; value: number; color?: string }[];
  label?: string;
}) {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-surface border border-border rounded px-3 py-2 text-xs shadow-lg">
      {label && <p className="text-text-secondary mb-1">{label}</p>}
      {payload.map((p, i) => (
        <p key={i} style={{ color: p.color ?? COLOR.textPrimary }}>
          {p.name}: {typeof p.value === "number" ? p.value.toLocaleString() : p.value}
        </p>
      ))}
    </div>
  );
}

/* ---------- stat card ---------- */
function StatCard({
  label,
  value,
  sub,
  accent,
}: {
  label: string;
  value: string;
  sub?: string;
  accent?: string;
}) {
  return (
    <div className="bg-surface border border-border rounded p-3 min-w-[120px]">
      <p className="text-xs text-text-secondary">{label}</p>
      <p className="text-lg font-semibold font-mono" style={{ color: accent ?? COLOR.textPrimary }}>
        {value}
      </p>
      {sub && <p className="text-xs text-text-secondary mt-0.5">{sub}</p>}
    </div>
  );
}

/* ---------- center label for donut ---------- */
function DonutCenter({ cx, cy, total }: { cx: number; cy: number; total: number }) {
  return (
    <text
      x={cx}
      y={cy}
      textAnchor="middle"
      dominantBaseline="central"
      fill={COLOR.textPrimary}
      fontSize={20}
      fontWeight={600}
    >
      {total}
    </text>
  );
}

/* ---------- observation generator ---------- */
function generateObservations(
  results: TaskResult[],
  stats: {
    pass: number;
    fail: number;
    total: number;
    passRate: number;
    hasLatency: boolean;
    avgLatency: number;
    minLatency: number;
    maxLatency: number;
    hasTokens: boolean;
    avgTokens: number;
  }
): string[] {
  const obs: string[] = [];
  const { pass, fail, total, passRate, hasLatency, hasTokens } = stats;

  // 1. Pass rate context
  if (total > 0) {
    if (passRate === 1) {
      obs.push(`All **${total} tasks** passed — perfect score across the board.`);
    } else if (passRate === 0) {
      obs.push(`All **${total} tasks** failed — no tasks met the passing criteria.`);
    } else if (passRate >= 0.8) {
      obs.push(`Strong pass rate at **${(passRate * 100).toFixed(0)}%** — ${pass} of ${total} tasks succeeded.`);
    } else if (passRate < 0.5) {
      obs.push(`Low pass rate at **${(passRate * 100).toFixed(0)}%** — only ${pass} of ${total} tasks passed.`);
    }
  }

  // 2. Latency comparison: pass vs fail
  if (hasLatency && pass > 0 && fail > 0) {
    const passResults = results.filter((r) => r.passed === true && r.latency_ms > 0);
    const failResults = results.filter((r) => r.passed === false && r.latency_ms > 0);
    if (passResults.length > 0 && failResults.length > 0) {
      const avgPassLatency = passResults.reduce((s, r) => s + r.latency_ms, 0) / passResults.length;
      const avgFailLatency = failResults.reduce((s, r) => s + r.latency_ms, 0) / failResults.length;
      if (avgPassLatency > avgFailLatency * 1.2) {
        obs.push(
          `Passing tasks averaged **${(avgPassLatency / 1000).toFixed(1)}s** latency vs **${(avgFailLatency / 1000).toFixed(1)}s** for failures — longer processing correlated with better results.`
        );
      } else if (avgFailLatency > avgPassLatency * 1.2) {
        obs.push(
          `Failing tasks averaged **${(avgFailLatency / 1000).toFixed(1)}s** latency vs **${(avgPassLatency / 1000).toFixed(1)}s** for passes — extra time did not translate to better outcomes.`
        );
      } else {
        obs.push(
          `Latency was similar across pass (**${(avgPassLatency / 1000).toFixed(1)}s**) and fail (**${(avgFailLatency / 1000).toFixed(1)}s**) tasks — speed was not a differentiating factor.`
        );
      }
    }
  }

  // 3. Token comparison: pass vs fail
  if (hasTokens && pass > 0 && fail > 0) {
    const passResults = results.filter((r) => r.passed === true && r.tokens_used > 0);
    const failResults = results.filter((r) => r.passed === false && r.tokens_used > 0);
    if (passResults.length > 0 && failResults.length > 0) {
      const avgPassTokens = passResults.reduce((s, r) => s + r.tokens_used, 0) / passResults.length;
      const avgFailTokens = failResults.reduce((s, r) => s + r.tokens_used, 0) / failResults.length;
      if (avgPassTokens < avgFailTokens * 0.85) {
        obs.push(
          `Passing tasks used fewer tokens on average (**${avgPassTokens.toFixed(0)}**) compared to failures (**${avgFailTokens.toFixed(0)}**) — lower token counts correlate with better performance.`
        );
      } else if (avgFailTokens < avgPassTokens * 0.85) {
        obs.push(
          `Passing tasks used more tokens (**${avgPassTokens.toFixed(0)}**) than failures (**${avgFailTokens.toFixed(0)}**) — more thorough responses tended to succeed.`
        );
      }
    }
  }

  // 4. Latency outlier detection
  if (hasLatency && total >= 3) {
    const latencies = results.filter((r) => r.latency_ms > 0).map((r) => r.latency_ms);
    const avg = latencies.reduce((a, b) => a + b, 0) / latencies.length;
    const outliers = results.filter((r) => r.latency_ms > avg * 2 && r.latency_ms > 0);
    if (outliers.length > 0 && outliers.length <= 3) {
      const desc = outliers
        .map((r) => {
          const ratio = (r.latency_ms / avg).toFixed(1);
          return `**${r.task_id}** at **${(r.latency_ms / 1000).toFixed(1)}s** (${ratio}x avg, ${r.passed ? "passed" : "failed"})`;
        })
        .join(", ");
      obs.push(`Latency outlier${outliers.length > 1 ? "s" : ""}: ${desc}.`);
    }
  }

  // 5. Score distribution
  const scores = results.map((r) => r.score);
  const uniqueScores = [...new Set(scores)];
  if (uniqueScores.length <= 2 && total > 2) {
    obs.push(
      `Scoring is **binary** (${uniqueScores.sort((a, b) => a - b).join(" vs ")}) — no partial credit awarded.`
    );
  } else if (uniqueScores.length > 2 && total > 2) {
    const avgScore = scores.reduce((a, b) => a + b, 0) / scores.length;
    obs.push(
      `Scores range from **${Math.min(...scores)}** to **${Math.max(...scores)}** with an average of **${avgScore.toFixed(1)}** — grading uses a continuous scale.`
    );
  }

  // 6. Consecutive failure streaks
  if (fail > 0 && total >= 5) {
    let maxStreak = 0;
    let current = 0;
    for (const r of results) {
      if (r.passed === false) {
        current++;
        maxStreak = Math.max(maxStreak, current);
      } else {
        current = 0;
      }
    }
    if (maxStreak >= 3) {
      obs.push(
        `Longest consecutive failure streak was **${maxStreak} tasks** — may indicate a systematic issue in a subset of inputs.`
      );
    }
  }

  return obs;
}

/* ---------- main component ---------- */
export function TaskResultsCharts({ results }: { results: TaskResult[] }) {
  const stats = useMemo(() => {
    const pass = results.filter((r) => r.passed === true).length;
    const fail = results.filter((r) => r.passed === false).length;
    const total = results.length;
    const passRate = total > 0 ? pass / total : 0;

    const latencies = results.map((r) => r.latency_ms).filter((v) => v > 0);
    const hasLatency = latencies.length > 0;
    const avgLatency = hasLatency ? latencies.reduce((a, b) => a + b, 0) / latencies.length : 0;
    const minLatency = hasLatency ? Math.min(...latencies) : 0;
    const maxLatency = hasLatency ? Math.max(...latencies) : 0;

    const tokens = results.map((r) => r.tokens_used).filter((v) => v > 0);
    const hasTokens = tokens.length > 0;
    const avgTokens = hasTokens ? tokens.reduce((a, b) => a + b, 0) / tokens.length : 0;

    const pieData = [
      { name: "Pass", value: pass, color: COLOR.success },
      { name: "Fail", value: fail, color: COLOR.danger },
    ];

    const barData = results.map((r, i) => ({
      name: `T${i + 1}`,
      latency: r.latency_ms,
      fill: r.passed ? COLOR.success : COLOR.dangerDim,
    }));

    const scatterPass = results
      .filter((r) => r.passed === true && (r.latency_ms > 0 || r.tokens_used > 0))
      .map((r) => ({ x: r.latency_ms, y: r.tokens_used }));
    const scatterFail = results
      .filter((r) => r.passed === false && (r.latency_ms > 0 || r.tokens_used > 0))
      .map((r) => ({ x: r.latency_ms, y: r.tokens_used }));
    const hasScatter = scatterPass.length + scatterFail.length > 0;

    return {
      pass,
      fail,
      total,
      passRate,
      hasLatency,
      avgLatency,
      minLatency,
      maxLatency,
      hasTokens,
      avgTokens,
      pieData,
      barData,
      scatterPass,
      scatterFail,
      hasScatter,
    };
  }, [results]);

  const observations = useMemo(
    () => generateObservations(results, stats),
    [results, stats]
  );

  if (results.length === 0) return null;

  return (
    <div className="space-y-4">
      <h3 className="text-lg font-medium">Results Overview</h3>

      {/* task strip */}
      <div className="flex gap-0.5 flex-wrap">
        {results.map((r, i) => (
          <div
            key={i}
            className="h-3 rounded-sm"
            style={{
              width: `${Math.max(100 / results.length, 3)}%`,
              maxWidth: 28,
              minWidth: 6,
              backgroundColor: r.passed ? COLOR.success : COLOR.dangerDim,
            }}
            title={`${r.task_id}: ${r.passed ? "pass" : "fail"}`}
          />
        ))}
      </div>

      {/* stat cards */}
      <div className="flex flex-wrap gap-3">
        <StatCard
          label="Pass Rate"
          value={`${(stats.passRate * 100).toFixed(1)}%`}
          sub={`${stats.pass}/${stats.total}`}
          accent={stats.passRate >= 0.5 ? COLOR.success : COLOR.danger}
        />
        {stats.hasLatency && (
          <StatCard
            label="Avg Latency"
            value={`${(stats.avgLatency / 1000).toFixed(2)}s`}
            sub={`${(stats.minLatency / 1000).toFixed(2)}s – ${(stats.maxLatency / 1000).toFixed(2)}s`}
          />
        )}
        {stats.hasTokens && (
          <StatCard
            label="Avg Tokens"
            value={Math.round(stats.avgTokens).toLocaleString()}
          />
        )}
        {stats.hasLatency && (
          <StatCard
            label="Latency Range"
            value={`${((stats.maxLatency - stats.minLatency) / 1000).toFixed(2)}s`}
            accent={COLOR.warning}
          />
        )}
      </div>

      {/* charts row */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        {/* donut */}
        <div className="bg-surface border border-border rounded p-4">
          <p className="text-xs text-text-secondary mb-2">Pass / Fail</p>
          <ResponsiveContainer width="100%" height={200}>
            <PieChart>
              <Pie
                data={stats.pieData}
                dataKey="value"
                nameKey="name"
                cx="50%"
                cy="50%"
                innerRadius={55}
                outerRadius={80}
                paddingAngle={2}
                label={false}
              >
                {stats.pieData.map((entry, i) => (
                  <Cell key={i} fill={entry.color} stroke="none" />
                ))}
              </Pie>
              <Tooltip content={<ChartTooltip />} />
              {/* center label */}
              <text
                x="50%"
                y="50%"
                textAnchor="middle"
                dominantBaseline="central"
                fill={COLOR.textPrimary}
                fontSize={20}
                fontWeight={600}
              >
                {stats.total}
              </text>
            </PieChart>
          </ResponsiveContainer>
          <div className="flex justify-center gap-4 text-xs mt-1">
            <span className="flex items-center gap-1">
              <span className="inline-block w-2.5 h-2.5 rounded-sm" style={{ backgroundColor: COLOR.success }} />
              Pass {stats.pass}
            </span>
            <span className="flex items-center gap-1">
              <span className="inline-block w-2.5 h-2.5 rounded-sm" style={{ backgroundColor: COLOR.danger }} />
              Fail {stats.fail}
            </span>
          </div>
        </div>

        {/* latency bar chart */}
        {stats.hasLatency && (
          <div className="bg-surface border border-border rounded p-4">
            <p className="text-xs text-text-secondary mb-2">Latency per Task (s)</p>
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={stats.barData}>
                <CartesianGrid strokeDasharray="3 3" stroke={COLOR.border} />
                <XAxis
                  dataKey="name"
                  tick={{ fill: COLOR.textSecondary, fontSize: 10 }}
                  interval={results.length > 20 ? Math.floor(results.length / 10) : 0}
                />
                <YAxis
                  tick={{ fill: COLOR.textSecondary, fontSize: 10 }}
                  tickFormatter={(v: number) => `${(v / 1000).toFixed(1)}`}
                />
                <Tooltip
                  content={<ChartTooltip />}
                  formatter={(v: number) => [`${(v / 1000).toFixed(2)}s`, "Latency"]}
                />
                <Bar dataKey="latency" radius={[2, 2, 0, 0]}>
                  {stats.barData.map((entry, i) => (
                    <Cell key={i} fill={entry.fill} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}

        {/* scatter */}
        {stats.hasScatter && stats.hasLatency && stats.hasTokens && (
          <div className="bg-surface border border-border rounded p-4">
            <p className="text-xs text-text-secondary mb-2">Latency vs Tokens</p>
            <ResponsiveContainer width="100%" height={200}>
              <ScatterChart>
                <CartesianGrid strokeDasharray="3 3" stroke={COLOR.border} />
                <XAxis
                  dataKey="x"
                  name="Latency (ms)"
                  tick={{ fill: COLOR.textSecondary, fontSize: 10 }}
                  tickFormatter={(v: number) => `${(v / 1000).toFixed(1)}s`}
                />
                <YAxis
                  dataKey="y"
                  name="Tokens"
                  tick={{ fill: COLOR.textSecondary, fontSize: 10 }}
                />
                <Tooltip
                  content={<ChartTooltip />}
                  formatter={(v: number, name: string) =>
                    name === "Latency (ms)" ? [`${(v / 1000).toFixed(2)}s`, name] : [v.toLocaleString(), name]
                  }
                />
                {stats.scatterPass.length > 0 && (
                  <Scatter name="Pass" data={stats.scatterPass} fill={COLOR.success} opacity={0.7} />
                )}
                {stats.scatterFail.length > 0 && (
                  <Scatter name="Fail" data={stats.scatterFail} fill={COLOR.danger} opacity={0.7} />
                )}
              </ScatterChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>

      {/* key observations */}
      {observations.length > 0 && (
        <div className="bg-surface border border-border rounded p-5">
          <p className="text-xs uppercase tracking-wider text-text-secondary mb-3 font-mono">
            Key Observations
          </p>
          <div className="flex flex-col gap-2.5 text-sm text-text-secondary leading-relaxed">
            {observations.map((text, i) => (
              <div key={i} className="flex gap-2.5">
                <span className="text-accent shrink-0">→</span>
                <span dangerouslySetInnerHTML={{
                  __html: text.replace(
                    /\*\*(.+?)\*\*/g,
                    '<strong class="text-text-primary">$1</strong>'
                  ),
                }} />
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

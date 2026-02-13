"use client";

import { formatScore } from "@/lib/utils";

interface ComparisonRow {
  eval_name: string;
  scores: Record<string, number | null>;
}

export function ComparisonTable({
  rows,
  models,
}: {
  rows: ComparisonRow[];
  models: string[];
}) {
  if (rows.length === 0 || models.length < 2) return null;

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-border text-left text-text-secondary">
            <th className="pb-2 pr-4">Eval</th>
            {models.map((m) => (
              <th key={m} className="pb-2 pr-4 font-mono text-xs">
                {m}
              </th>
            ))}
            {models.length === 2 && <th className="pb-2">Delta</th>}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => {
            const s0 = row.scores[models[0]];
            const s1 = row.scores[models[1]];
            const delta =
              models.length === 2 && s0 !== null && s0 !== undefined && s1 !== null && s1 !== undefined
                ? s0 - s1
                : null;
            return (
              <tr key={row.eval_name} className="border-b border-border/50">
                <td className="py-2 pr-4">{row.eval_name}</td>
                {models.map((m) => (
                  <td key={m} className="py-2 pr-4 font-mono">
                    {formatScore(row.scores[m] ?? null)}
                  </td>
                ))}
                {models.length === 2 && (
                  <td className="py-2 font-mono">
                    {delta !== null ? (
                      <span
                        className={
                          delta > 0
                            ? "text-success"
                            : delta < 0
                              ? "text-danger"
                              : "text-text-secondary"
                        }
                      >
                        {delta > 0 ? "+" : ""}
                        {(delta * 100).toFixed(1)}%
                      </span>
                    ) : (
                      "—"
                    )}
                  </td>
                )}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

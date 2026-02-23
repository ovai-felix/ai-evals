import type { TaskResult } from "@/lib/types";
import { formatScore } from "@/lib/utils";

/** Keys to exclude from dimension aggregation. */
const HIDDEN_KEYS = new Set(["weights"]);

/** Detect numeric metadata keys present in >50% of results. */
function detectDimensions(
  results: TaskResult[]
): { key: string; mean: number; min: number; max: number }[] {
  if (results.length === 0) return [];

  const accum = new Map<string, number[]>();

  for (const r of results) {
    for (const [k, v] of Object.entries(r.metadata ?? {})) {
      if (HIDDEN_KEYS.has(k)) continue;
      if (typeof v === "number") {
        if (!accum.has(k)) accum.set(k, []);
        accum.get(k)!.push(v);
      }
    }
  }

  const threshold = results.length * 0.5;
  return [...accum.entries()]
    .filter(([, vals]) => vals.length >= threshold)
    .map(([key, vals]) => ({
      key,
      mean: vals.reduce((a, b) => a + b, 0) / vals.length,
      min: Math.min(...vals),
      max: Math.max(...vals),
    }))
    .sort((a, b) => a.key.localeCompare(b.key));
}

function labelFromKey(key: string): string {
  return key
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

/**
 * Renders a summary panel of aggregated dimension scores when task results
 * contain numeric metadata (e.g. helpfulness_score, completeness_score).
 * Shows nothing if no numeric metadata dimensions are detected.
 */
export function DimensionSummary({ results }: { results: TaskResult[] }) {
  const dimensions = detectDimensions(results);
  if (dimensions.length === 0) return null;

  return (
    <div>
      <h3 className="text-lg font-medium mb-3">Score Dimensions</h3>
      <div className="bg-surface border border-border rounded p-4 grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
        {dimensions.map((d) => (
          <div key={d.key}>
            <p className="text-xs text-text-secondary">{labelFromKey(d.key)}</p>
            <p
              className={`font-mono text-sm ${d.mean >= 0.5 ? "text-success" : "text-danger"}`}
            >
              {formatScore(d.mean)}
            </p>
            <div className="mt-1 w-full bg-border rounded-full h-1.5">
              <div
                className={`h-1.5 rounded-full ${d.mean >= 0.5 ? "bg-success" : "bg-danger"}`}
                style={{ width: `${Math.min(d.mean * 100, 100)}%` }}
              />
            </div>
            <p className="text-xs text-text-secondary mt-1">
              {formatScore(d.min)} – {formatScore(d.max)}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}

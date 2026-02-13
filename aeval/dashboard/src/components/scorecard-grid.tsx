import type { RunSummary } from "@/lib/types";
import { formatScore } from "@/lib/utils";

interface ScorecardProps {
  results: RunSummary[];
}

export function ScorecardGrid({ results }: ScorecardProps) {
  const models = [...new Set(results.map((r) => r.model_name))].sort();
  const evals = [...new Set(results.map((r) => r.eval_name))].sort();

  // Build a map of latest result per (model, eval)
  const grid: Record<string, Record<string, RunSummary | null>> = {};
  for (const model of models) {
    grid[model] = {};
    for (const evalName of evals) {
      const runs = results.filter(
        (r) => r.model_name === model && r.eval_name === evalName,
      );
      if (runs.length === 0) {
        grid[model][evalName] = null;
      } else {
        grid[model][evalName] = runs.reduce((a, b) =>
          a.submitted_at > b.submitted_at ? a : b,
        );
      }
    }
  }

  // A model is READY if it passed all evals it was tested on
  function isReady(model: string): boolean {
    const tested = evals.filter((e) => grid[model][e] !== null);
    if (tested.length === 0) return false;
    return tested.every((e) => grid[model][e]?.passed === true);
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-border text-left">
            <th className="pb-2 pr-4 text-text-secondary">Model</th>
            {evals.map((e) => (
              <th key={e} className="pb-2 pr-4 text-text-secondary text-xs">
                {e}
              </th>
            ))}
            <th className="pb-2 text-text-secondary">Verdict</th>
          </tr>
        </thead>
        <tbody>
          {models.map((model) => (
            <tr key={model} className="border-b border-border/50">
              <td className="py-2 pr-4 font-mono text-xs">{model}</td>
              {evals.map((evalName) => {
                const run = grid[model][evalName];
                if (!run) {
                  return (
                    <td key={evalName} className="py-2 pr-4">
                      <span className="inline-block w-8 h-8 bg-border/50 rounded text-center leading-8 text-text-secondary text-xs">
                        —
                      </span>
                    </td>
                  );
                }
                const passed = run.passed;
                return (
                  <td key={evalName} className="py-2 pr-4">
                    <span
                      className={`inline-block w-8 h-8 rounded text-center leading-8 text-xs font-medium ${
                        passed
                          ? "bg-success/20 text-success"
                          : passed === false
                            ? "bg-danger/20 text-danger"
                            : "bg-border/50 text-text-secondary"
                      }`}
                      title={formatScore(run.score)}
                    >
                      {passed ? "P" : passed === false ? "F" : "?"}
                    </span>
                  </td>
                );
              })}
              <td className="py-2">
                <span
                  className={`inline-block px-3 py-1 rounded text-xs font-bold ${
                    isReady(model)
                      ? "bg-success/20 text-success"
                      : "bg-danger/20 text-danger"
                  }`}
                >
                  {isReady(model) ? "READY" : "NOT READY"}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

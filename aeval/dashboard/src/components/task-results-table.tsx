import type { TaskResult } from "@/lib/types";
import { formatScore } from "@/lib/utils";

export function TaskResultsTable({ results }: { results: TaskResult[] }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-border text-left text-text-secondary">
            <th className="pb-2 pr-4">Task ID</th>
            <th className="pb-2 pr-4">Score</th>
            <th className="pb-2 pr-4">Passed</th>
            <th className="pb-2 pr-4">Prediction</th>
            <th className="pb-2 pr-4">Reference</th>
            <th className="pb-2 pr-4">Latency</th>
            <th className="pb-2">Tokens</th>
          </tr>
        </thead>
        <tbody>
          {results.map((r) => (
            <tr key={r.task_id} className="border-b border-border/50">
              <td className="py-2 pr-4 font-mono text-xs">{r.task_id}</td>
              <td className="py-2 pr-4 font-mono">
                <span className={r.score >= 0.5 ? "text-success" : "text-danger"}>
                  {formatScore(r.score)}
                </span>
              </td>
              <td className="py-2 pr-4">
                {r.passed === null ? (
                  <span className="text-text-secondary">—</span>
                ) : r.passed ? (
                  <span className="text-success">Pass</span>
                ) : (
                  <span className="text-danger">Fail</span>
                )}
              </td>
              <td className="py-2 pr-4 max-w-xs truncate text-text-secondary">
                {r.prediction || "—"}
              </td>
              <td className="py-2 pr-4 max-w-xs truncate text-text-secondary">
                {r.reference || "—"}
              </td>
              <td className="py-2 pr-4 text-text-secondary font-mono text-xs">
                {r.latency_ms > 0 ? `${r.latency_ms.toFixed(0)}ms` : "—"}
              </td>
              <td className="py-2 text-text-secondary font-mono text-xs">
                {r.tokens_used > 0 ? r.tokens_used : "—"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

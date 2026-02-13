import Link from "next/link";
import type { RunSummary } from "@/lib/types";
import { formatDate, formatDuration, formatScore } from "@/lib/utils";
import { StatusBadge } from "./status-badge";
import { ScoreBadge } from "./score-badge";

export function RunsTable({ runs }: { runs: RunSummary[] }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-border text-left text-text-secondary">
            <th className="pb-2 pr-4">ID</th>
            <th className="pb-2 pr-4">Eval</th>
            <th className="pb-2 pr-4">Model</th>
            <th className="pb-2 pr-4">Status</th>
            <th className="pb-2 pr-4">Score</th>
            <th className="pb-2 pr-4">Tasks</th>
            <th className="pb-2 pr-4">Duration</th>
            <th className="pb-2">Submitted</th>
          </tr>
        </thead>
        <tbody>
          {runs.map((run) => (
            <tr key={run.id} className="border-b border-border/50 hover:bg-surface/50">
              <td className="py-2 pr-4 font-mono text-xs">
                <Link href={`/runs/${run.id}`}>
                  {run.id.slice(0, 8)}
                </Link>
              </td>
              <td className="py-2 pr-4">{run.eval_name}</td>
              <td className="py-2 pr-4 font-mono text-xs">{run.model_name}</td>
              <td className="py-2 pr-4">
                <StatusBadge status={run.status} />
              </td>
              <td className="py-2 pr-4">
                <ScoreBadge score={run.score} ci={run.ci} threshold={run.threshold} />
              </td>
              <td className="py-2 pr-4 text-text-secondary">
                {run.num_tasks ?? "—"}
              </td>
              <td className="py-2 pr-4 text-text-secondary">
                {formatDuration(run)}
              </td>
              <td className="py-2 text-text-secondary">{formatDate(run.submitted_at)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

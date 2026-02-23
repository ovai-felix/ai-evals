import { getRun } from "@/lib/api";
import { formatDate, formatDuration, formatScore } from "@/lib/utils";
import { StatusBadge } from "@/components/status-badge";
import { ScoreBadge } from "@/components/score-badge";
import { TaskResultsTable } from "@/components/task-results-table";
import { EmptyState } from "@/components/empty-state";
import { TerminalLogViewer } from "@/components/terminal-log-viewer";
import { DimensionSummary } from "@/components/dimension-summary";

export const dynamic = "force-dynamic";

export default async function RunDetailPage({
  params,
}: {
  params: { id: string };
}) {
  const run = await getRun(params.id);

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <h2 className="text-xl font-semibold">Run {run.id.slice(0, 8)}</h2>
        <StatusBadge status={run.status} />
      </div>

      <div className="bg-surface border border-border rounded p-4 grid grid-cols-2 md:grid-cols-4 gap-4">
        <div>
          <p className="text-xs text-text-secondary">Eval</p>
          <p className="font-medium">{run.eval_name}</p>
        </div>
        <div>
          <p className="text-xs text-text-secondary">Model</p>
          <p className="font-mono text-sm">{run.model_name}</p>
        </div>
        <div>
          <p className="text-xs text-text-secondary">Score</p>
          <ScoreBadge score={run.score} ci={run.ci} threshold={run.threshold} />
        </div>
        <div>
          <p className="text-xs text-text-secondary">Passed</p>
          <p>
            {run.passed === null ? (
              <span className="text-text-secondary">—</span>
            ) : run.passed ? (
              <span className="text-success">Yes</span>
            ) : (
              <span className="text-danger">No</span>
            )}
          </p>
        </div>
        <div>
          <p className="text-xs text-text-secondary">Tasks</p>
          <p>{run.num_tasks ?? "—"}</p>
        </div>
        <div>
          <p className="text-xs text-text-secondary">Duration</p>
          <p>{formatDuration(run)}</p>
        </div>
        <div>
          <p className="text-xs text-text-secondary">Submitted</p>
          <p className="text-sm">{formatDate(run.submitted_at)}</p>
        </div>
        <div>
          <p className="text-xs text-text-secondary">Threshold</p>
          <p className="font-mono text-sm">{run.threshold ? formatScore(run.threshold) : "—"}</p>
        </div>
      </div>

      {run.error && (
        <div className="bg-danger/10 border border-danger/30 rounded p-4">
          <p className="text-sm text-danger font-medium">Error</p>
          <p className="text-sm text-text-primary mt-1">{run.error}</p>
        </div>
      )}

      <TerminalLogViewer runId={run.id} runStatus={run.status} />

      {run.results.length > 0 && (
        <DimensionSummary results={run.results} />
      )}

      <div>
        <h3 className="text-lg font-medium mb-3">Task Results</h3>
        {run.results.length > 0 ? (
          <TaskResultsTable results={run.results} />
        ) : (
          <EmptyState message="No task results available for this run." />
        )}
      </div>
    </div>
  );
}

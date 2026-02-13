import { Suspense } from "react";
import { getRuns } from "@/lib/api";
import { RunsTable } from "@/components/runs-table";
import { RunFilters } from "@/components/run-filters";
import { EmptyState } from "@/components/empty-state";

export const dynamic = "force-dynamic";

export default async function RunsPage({
  searchParams,
}: {
  searchParams: { eval_name?: string; model?: string; status?: string };
}) {
  const runs = await getRuns({
    eval_name: searchParams.eval_name,
    model: searchParams.model,
    status: searchParams.status,
    limit: 100,
  });

  return (
    <div className="space-y-6">
      <h2 className="text-xl font-semibold">Eval Runs</h2>
      <Suspense>
        <RunFilters />
      </Suspense>
      {runs.length > 0 ? (
        <RunsTable runs={runs} />
      ) : (
        <EmptyState message="No runs match the current filters." />
      )}
    </div>
  );
}

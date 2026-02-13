import { getHealth, getRuns } from "@/lib/api";
import { HealthPanel } from "@/components/health-panel";
import { RunsTable } from "@/components/runs-table";
import { EmptyState } from "@/components/empty-state";

export const dynamic = "force-dynamic";

export default async function HomePage() {
  const [health, runs] = await Promise.all([
    getHealth(),
    getRuns({ limit: 10 }),
  ]);

  return (
    <div className="space-y-6">
      <h2 className="text-xl font-semibold">Dashboard</h2>
      <HealthPanel health={health} />

      <div>
        <h3 className="text-lg font-medium mb-3">Recent Runs</h3>
        {runs.length > 0 ? (
          <RunsTable runs={runs} />
        ) : (
          <EmptyState message="No eval runs yet. Submit a run via the API to get started." />
        )}
      </div>
    </div>
  );
}

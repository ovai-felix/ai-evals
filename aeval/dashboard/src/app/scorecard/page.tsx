import { getResults } from "@/lib/api";
import { ScorecardGrid } from "@/components/scorecard-grid";
import { EmptyState } from "@/components/empty-state";

export const dynamic = "force-dynamic";

export default async function ScorecardPage() {
  const results = await getResults({ limit: 500 });

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-semibold">Release Scorecard</h2>
        <p className="text-sm text-text-secondary mt-1">
          Pass/fail matrix across all evals and models. A model is READY when it
          passes every eval it has been tested on.
        </p>
      </div>
      {results.length > 0 ? (
        <ScorecardGrid results={results} />
      ) : (
        <EmptyState message="No completed results yet. Run some evals to see the scorecard." />
      )}
    </div>
  );
}

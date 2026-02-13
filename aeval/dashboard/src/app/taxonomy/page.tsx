import { getCoverage, getTaxonomy } from "@/lib/api";
import { TaxonomyTree } from "@/components/taxonomy-tree";
import { CoverageHeatmap } from "@/components/coverage-heatmap";
import { EmptyState } from "@/components/empty-state";

export const dynamic = "force-dynamic";

export default async function TaxonomyPage() {
  let taxonomy;
  let coverage;

  try {
    [taxonomy, coverage] = await Promise.all([getTaxonomy(), getCoverage()]);
  } catch {
    return (
      <EmptyState message="Cannot load taxonomy data. Is the orchestrator running?" />
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-semibold">Capability Taxonomy</h2>
        <p className="text-sm text-text-secondary mt-1">
          Coverage heat map and taxonomy tree. Green = active evals with good
          discrimination. Yellow = watch. Red = gap or saturated.
        </p>
      </div>

      {/* Coverage summary bar */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        <StatCard label="Leaf Nodes" value={coverage.total_nodes} />
        <StatCard
          label="Covered"
          value={`${coverage.covered_nodes}/${coverage.total_nodes}`}
          sub={`${coverage.coverage_pct}%`}
        />
        <StatCard label="Gaps" value={coverage.gap_count} danger={coverage.gap_count > 0} />
        <StatCard label="Avg Discrimination" value={coverage.avg_discrimination.toFixed(4)} />
        <StatCard
          label="Active / Watch / Sat"
          value={`${coverage.active_count} / ${coverage.watch_count} / ${coverage.saturated_count}`}
        />
      </div>

      {/* Heat map */}
      {taxonomy.length > 0 ? (
        <CoverageHeatmap taxonomy={taxonomy} />
      ) : (
        <EmptyState message="No taxonomy data available." />
      )}

      {/* Tree view */}
      {taxonomy.length > 0 && <TaxonomyTree taxonomy={taxonomy} />}
    </div>
  );
}

function StatCard({
  label,
  value,
  sub,
  danger,
}: {
  label: string;
  value: string | number;
  sub?: string;
  danger?: boolean;
}) {
  return (
    <div className="bg-surface border border-border rounded-lg p-3">
      <p className="text-xs text-text-secondary">{label}</p>
      <p className={`text-lg font-bold ${danger ? "text-danger" : "text-text-primary"}`}>
        {value}
        {sub && <span className="text-xs text-text-secondary ml-1">{sub}</span>}
      </p>
    </div>
  );
}

"use client";

import type { TaxonomyNode } from "@/lib/types";

interface HeatmapProps {
  taxonomy: TaxonomyNode[];
}

function nodeColor(node: TaxonomyNode): string {
  if (node.eval_count === 0) return "bg-danger/30 border-danger/50";
  if (node.avg_discrimination < 0.08) return "bg-danger/20 border-danger/40";
  if (node.avg_discrimination < 0.15) return "bg-warning/20 border-warning/40";
  return "bg-success/20 border-success/40";
}

function nodeTextColor(node: TaxonomyNode): string {
  if (node.eval_count === 0) return "text-danger";
  if (node.avg_discrimination < 0.08) return "text-danger";
  if (node.avg_discrimination < 0.15) return "text-warning";
  return "text-success";
}

export function CoverageHeatmap({ taxonomy }: HeatmapProps) {
  return (
    <div className="space-y-4">
      <h3 className="text-sm font-medium text-text-secondary">Coverage Heat Map</h3>
      <div className="space-y-3">
        {taxonomy.map((category) => (
          <div key={category.id}>
            <p className="text-xs font-medium text-text-secondary mb-1.5">
              {category.name}
            </p>
            <div className="flex flex-wrap gap-1.5">
              {category.children.map((leaf) => (
                <div
                  key={leaf.id}
                  className={`border rounded px-2.5 py-1.5 text-xs cursor-default transition-colors ${nodeColor(leaf)}`}
                  title={`${leaf.name}\nEvals: ${leaf.eval_count}\nDiscrimination: ${leaf.avg_discrimination.toFixed(4)}`}
                >
                  <span className={nodeTextColor(leaf)}>{leaf.name}</span>
                  {leaf.eval_count > 0 && (
                    <span className="ml-1 text-text-secondary">
                      ({leaf.eval_count})
                    </span>
                  )}
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>

      {/* Legend */}
      <div className="flex gap-4 text-xs text-text-secondary pt-2 border-t border-border">
        <span className="flex items-center gap-1">
          <span className="w-3 h-3 rounded bg-success/30 border border-success/50 inline-block" />
          Active
        </span>
        <span className="flex items-center gap-1">
          <span className="w-3 h-3 rounded bg-warning/30 border border-warning/50 inline-block" />
          Watch
        </span>
        <span className="flex items-center gap-1">
          <span className="w-3 h-3 rounded bg-danger/30 border border-danger/50 inline-block" />
          Gap / Saturated
        </span>
      </div>
    </div>
  );
}

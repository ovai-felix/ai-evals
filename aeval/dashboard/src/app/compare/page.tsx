"use client";

import { useEffect, useState, useCallback } from "react";
import type { RunSummary } from "@/lib/types";
import { RadarChartView } from "@/components/radar-chart";
import { ComparisonTable } from "@/components/comparison-table";
import { EmptyState } from "@/components/empty-state";

const API_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8081";

export default function ComparePage() {
  const [results, setResults] = useState<RunSummary[]>([]);
  const [allModels, setAllModels] = useState<string[]>([]);
  const [selected, setSelected] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`${API_URL}/api/v1/results?limit=500`)
      .then((r) => r.json())
      .then((data: RunSummary[]) => {
        setResults(data);
        const models = [...new Set(data.map((r) => r.model_name))];
        setAllModels(models);
        setSelected(models.slice(0, 2));
      })
      .catch(() => setResults([]))
      .finally(() => setLoading(false));
  }, []);

  const toggle = useCallback(
    (model: string) => {
      setSelected((prev) =>
        prev.includes(model)
          ? prev.filter((m) => m !== model)
          : [...prev, model],
      );
    },
    [],
  );

  if (loading) {
    return (
      <div className="space-y-4 animate-pulse">
        <div className="h-8 w-48 bg-surface rounded" />
        <div className="h-96 bg-surface rounded" />
      </div>
    );
  }

  if (results.length === 0) {
    return (
      <div className="space-y-6">
        <h2 className="text-xl font-semibold">Compare Models</h2>
        <EmptyState message="No completed results to compare. Run some evals first." />
      </div>
    );
  }

  const evalNames = [...new Set(results.map((r) => r.eval_name))];

  // Build per-eval best score for each selected model
  const scoreMap: Record<string, Record<string, number | null>> = {};
  for (const evalName of evalNames) {
    scoreMap[evalName] = {};
    for (const model of selected) {
      const modelRuns = results.filter(
        (r) => r.eval_name === evalName && r.model_name === model,
      );
      if (modelRuns.length === 0) {
        scoreMap[evalName][model] = null;
      } else {
        // Use most recent completed score
        const best = modelRuns.reduce((a, b) =>
          (a.submitted_at > b.submitted_at ? a : b)
        );
        scoreMap[evalName][model] = best.score;
      }
    }
  }

  const radarData = evalNames.map((evalName) => {
    const point: Record<string, string | number> = { eval_name: evalName };
    for (const model of selected) {
      point[model] = scoreMap[evalName][model] ?? 0;
    }
    return point;
  });

  const tableRows = evalNames.map((evalName) => ({
    eval_name: evalName,
    scores: scoreMap[evalName],
  }));

  return (
    <div className="space-y-6">
      <h2 className="text-xl font-semibold">Compare Models</h2>

      <div className="flex flex-wrap gap-2">
        {allModels.map((model) => (
          <button
            key={model}
            onClick={() => toggle(model)}
            className={`px-3 py-1.5 rounded text-xs font-mono border ${
              selected.includes(model)
                ? "bg-accent/20 border-accent text-accent"
                : "bg-surface border-border text-text-secondary hover:text-text-primary"
            }`}
          >
            {model}
          </button>
        ))}
      </div>

      {selected.length >= 2 ? (
        <>
          <div className="bg-surface border border-border rounded p-4">
            <RadarChartView data={radarData} models={selected} />
          </div>
          <ComparisonTable rows={tableRows} models={selected} />
        </>
      ) : (
        <EmptyState message="Select at least 2 models to compare." />
      )}
    </div>
  );
}

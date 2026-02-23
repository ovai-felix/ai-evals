"use client";

import { Fragment, useState } from "react";
import type { TaskResult } from "@/lib/types";
import { formatScore } from "@/lib/utils";

/** Keys to exclude from the metadata display (internal/redundant). */
const HIDDEN_META_KEYS = new Set(["weights"]);

/**
 * Detect metadata keys that hold numeric scores across all results.
 * These get promoted to dedicated table columns.
 */
function detectScoreColumns(results: TaskResult[]): string[] {
  if (results.length === 0) return [];
  const candidates = new Map<string, number>();

  for (const r of results) {
    for (const [k, v] of Object.entries(r.metadata ?? {})) {
      if (HIDDEN_META_KEYS.has(k)) continue;
      if (typeof v === "number") {
        candidates.set(k, (candidates.get(k) ?? 0) + 1);
      }
    }
  }

  // Only promote keys present in >50% of results
  const threshold = results.length * 0.5;
  return [...candidates.entries()]
    .filter(([, count]) => count >= threshold)
    .map(([key]) => key)
    .sort();
}

/** Pretty-print a metadata key: "helpfulness_score" → "Helpfulness Score" */
function labelFromKey(key: string): string {
  return key
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

/** Format a single metadata value for display. */
function formatMetaValue(value: unknown): string {
  if (value === null || value === undefined) return "—";
  if (typeof value === "number") return formatScore(value);
  if (typeof value === "boolean") return value ? "Yes" : "No";
  if (Array.isArray(value)) {
    if (value.length === 0) return "—";
    return value.map(String).join(", ");
  }
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

/** Format a metadata key's value with appropriate color for scores. */
function ScoreCell({ value }: { value: unknown }) {
  if (typeof value !== "number") {
    return <span className="text-text-secondary">{formatMetaValue(value)}</span>;
  }
  return (
    <span className={value >= 0.5 ? "text-success" : "text-danger"}>
      {formatScore(value)}
    </span>
  );
}

function MetadataPanel({ metadata }: { metadata: Record<string, unknown> }) {
  const entries = Object.entries(metadata).filter(
    ([k]) => !HIDDEN_META_KEYS.has(k)
  );

  if (entries.length === 0) {
    return (
      <p className="text-xs text-text-secondary italic">No metadata</p>
    );
  }

  return (
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-x-6 gap-y-2">
      {entries.map(([key, value]) => (
        <div key={key}>
          <p className="text-xs text-text-secondary">{labelFromKey(key)}</p>
          <p className="text-sm font-mono break-all">{formatMetaValue(value)}</p>
        </div>
      ))}
    </div>
  );
}

export function TaskResultsTable({ results }: { results: TaskResult[] }) {
  const [expandedRows, setExpandedRows] = useState<Set<string>>(new Set());
  const scoreColumns = detectScoreColumns(results);
  const hasMetadata = results.some(
    (r) => r.metadata && Object.keys(r.metadata).length > 0
  );

  function toggleRow(taskId: string) {
    setExpandedRows((prev) => {
      const next = new Set(prev);
      if (next.has(taskId)) {
        next.delete(taskId);
      } else {
        next.add(taskId);
      }
      return next;
    });
  }

  const baseCols = 7; // task_id, score, passed, prediction, reference, latency, tokens
  const totalCols = baseCols + scoreColumns.length;

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-border text-left text-text-secondary">
            <th className="pb-2 pr-4">Task ID</th>
            <th className="pb-2 pr-4">Score</th>
            {scoreColumns.map((col) => (
              <th key={col} className="pb-2 pr-4">
                {labelFromKey(col)}
              </th>
            ))}
            <th className="pb-2 pr-4">Passed</th>
            <th className="pb-2 pr-4">Prediction</th>
            <th className="pb-2 pr-4">Reference</th>
            <th className="pb-2 pr-4">Latency</th>
            <th className="pb-2">Tokens</th>
          </tr>
        </thead>
        <tbody>
          {results.map((r) => {
            const isExpanded = expandedRows.has(r.task_id);
            // Metadata keys not already shown as score columns
            const remainingMeta = Object.fromEntries(
              Object.entries(r.metadata ?? {}).filter(
                ([k]) => !scoreColumns.includes(k) && !HIDDEN_META_KEYS.has(k)
              )
            );
            const hasRemainingMeta = Object.keys(remainingMeta).length > 0;

            return (
              <Fragment key={r.task_id}>
                <tr
                  className={`border-b border-border/50 ${hasRemainingMeta ? "cursor-pointer hover:bg-surface-hover" : ""}`}
                  onClick={() => hasRemainingMeta && toggleRow(r.task_id)}
                >
                  <td className="py-2 pr-4 font-mono text-xs">
                    {hasRemainingMeta && (
                      <span className="inline-block w-4 text-text-secondary mr-1">
                        {isExpanded ? "▾" : "▸"}
                      </span>
                    )}
                    {r.task_id}
                  </td>
                  <td className="py-2 pr-4 font-mono">
                    <span className={r.score >= 0.5 ? "text-success" : "text-danger"}>
                      {formatScore(r.score)}
                    </span>
                  </td>
                  {scoreColumns.map((col) => (
                    <td key={col} className="py-2 pr-4 font-mono">
                      <ScoreCell value={r.metadata?.[col]} />
                    </td>
                  ))}
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
                {isExpanded && hasRemainingMeta && (
                  <tr className="border-b border-border/50 bg-surface/50">
                    <td colSpan={totalCols} className="px-4 py-3">
                      <MetadataPanel metadata={remainingMeta} />
                    </td>
                  </tr>
                )}
              </Fragment>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

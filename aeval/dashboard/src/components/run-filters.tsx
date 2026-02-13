"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useCallback } from "react";

const statuses = ["", "pending", "running", "completed", "failed"];

export function RunFilters() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const update = useCallback(
    (key: string, value: string) => {
      const params = new URLSearchParams(searchParams.toString());
      if (value) {
        params.set(key, value);
      } else {
        params.delete(key);
      }
      router.push(`/runs?${params.toString()}`);
    },
    [router, searchParams],
  );

  return (
    <div className="flex gap-3 items-center">
      <input
        type="text"
        placeholder="Eval name..."
        defaultValue={searchParams.get("eval_name") ?? ""}
        onBlur={(e) => update("eval_name", e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter")
            update("eval_name", (e.target as HTMLInputElement).value);
        }}
        className="bg-surface border border-border rounded px-3 py-1.5 text-sm text-text-primary placeholder:text-text-secondary focus:outline-none focus:ring-1 focus:ring-accent"
      />
      <input
        type="text"
        placeholder="Model..."
        defaultValue={searchParams.get("model") ?? ""}
        onBlur={(e) => update("model", e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter")
            update("model", (e.target as HTMLInputElement).value);
        }}
        className="bg-surface border border-border rounded px-3 py-1.5 text-sm text-text-primary placeholder:text-text-secondary focus:outline-none focus:ring-1 focus:ring-accent"
      />
      <select
        value={searchParams.get("status") ?? ""}
        onChange={(e) => update("status", e.target.value)}
        className="bg-surface border border-border rounded px-3 py-1.5 text-sm text-text-primary focus:outline-none focus:ring-1 focus:ring-accent"
      >
        <option value="">All statuses</option>
        {statuses
          .filter(Boolean)
          .map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
      </select>
    </div>
  );
}

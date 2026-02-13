import type { ConfidenceInterval, RunSummary } from "./types";

export function formatScore(score: number | null): string {
  if (score === null) return "—";
  return `${(score * 100).toFixed(1)}%`;
}

export function formatCI(ci: ConfidenceInterval | null): string {
  if (!ci) return "";
  return `±${(((ci.upper - ci.lower) / 2) * 100).toFixed(1)}%`;
}

export function formatDate(iso: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function formatDuration(run: RunSummary): string {
  if (!run.started_at || !run.completed_at) return "—";
  const ms =
    new Date(run.completed_at).getTime() - new Date(run.started_at).getTime();
  if (ms < 1000) return `${ms}ms`;
  const s = ms / 1000;
  if (s < 60) return `${s.toFixed(1)}s`;
  const m = Math.floor(s / 60);
  const rem = Math.round(s % 60);
  return `${m}m ${rem}s`;
}

export function statusColor(status: string): string {
  switch (status) {
    case "completed":
      return "bg-success/20 text-success";
    case "running":
      return "bg-accent/20 text-accent";
    case "pending":
      return "bg-warning/20 text-warning";
    case "failed":
      return "bg-danger/20 text-danger";
    default:
      return "bg-border text-text-secondary";
  }
}

export function scoreColor(score: number | null, threshold?: number | null): string {
  if (score === null) return "text-text-secondary";
  const t = threshold ?? 0.7;
  return score >= t ? "text-success" : "text-danger";
}

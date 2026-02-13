import { formatCI, formatScore, scoreColor } from "@/lib/utils";
import type { ConfidenceInterval } from "@/lib/types";

export function ScoreBadge({
  score,
  ci,
  threshold,
}: {
  score: number | null;
  ci?: ConfidenceInterval | null;
  threshold?: number | null;
}) {
  return (
    <span className={`font-mono text-sm ${scoreColor(score, threshold)}`}>
      {formatScore(score)}
      {ci && (
        <span className="text-text-secondary text-xs ml-1">
          {formatCI(ci)}
        </span>
      )}
    </span>
  );
}

import type { HealthStatus } from "@/lib/types";

function Dot({ ok }: { ok: boolean }) {
  return (
    <span
      className={`inline-block w-2.5 h-2.5 rounded-full ${ok ? "bg-success" : "bg-danger"}`}
    />
  );
}

function Card({ label, ok }: { label: string; ok: boolean }) {
  return (
    <div className="bg-surface border border-border rounded p-4 flex items-center gap-3">
      <Dot ok={ok} />
      <div>
        <p className="text-sm font-medium text-text-primary">{label}</p>
        <p className="text-xs text-text-secondary">
          {ok ? "Connected" : "Unavailable"}
        </p>
      </div>
    </div>
  );
}

export function HealthPanel({ health }: { health: HealthStatus }) {
  return (
    <div className="grid grid-cols-3 gap-4">
      <Card label="Database" ok={health.db} />
      <Card label="Redis" ok={health.redis} />
      <Card label="Ollama" ok={health.ollama} />
    </div>
  );
}

import { getModels } from "@/lib/api";
import { EmptyState } from "@/components/empty-state";
import type { ModelInfo } from "@/lib/types";

export const dynamic = "force-dynamic";

function ModelCard({ model }: { model: ModelInfo }) {
  return (
    <div className="bg-surface border border-border rounded p-4 space-y-2">
      <h3 className="font-medium font-mono text-sm">{model.name}</h3>
      <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
        {model.family && (
          <>
            <span className="text-text-secondary">Family</span>
            <span>{model.family}</span>
          </>
        )}
        {model.parameter_size && (
          <>
            <span className="text-text-secondary">Size</span>
            <span>{model.parameter_size}</span>
          </>
        )}
        {model.quantization && (
          <>
            <span className="text-text-secondary">Quantization</span>
            <span>{model.quantization}</span>
          </>
        )}
        <span className="text-text-secondary">Multimodal</span>
        <span>{model.multimodal ? "Yes" : "No"}</span>
      </div>
      {model.digest && (
        <p className="text-xs text-text-secondary font-mono truncate">
          {model.digest.slice(0, 16)}
        </p>
      )}
    </div>
  );
}

export default async function ModelsPage() {
  const models = await getModels();

  return (
    <div className="space-y-6">
      <h2 className="text-xl font-semibold">Models</h2>
      {models.length > 0 ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {models.map((m) => (
            <ModelCard key={m.name} model={m} />
          ))}
        </div>
      ) : (
        <EmptyState message="No models available. Ensure Ollama is running with models pulled." />
      )}
    </div>
  );
}

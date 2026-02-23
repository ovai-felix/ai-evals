"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

interface EvalOption {
  id: number;
  name: string;
  description: string;
  threshold: number | null;
}

const API_BASE =
  (typeof window !== "undefined"
    ? process.env.NEXT_PUBLIC_API_URL
    : "") || "http://localhost:8081";

const MODEL_PRESETS = [
  "openrouter:anthropic/claude-sonnet-4",
  "openrouter:google/gemini-2.5-flash",
  "openrouter:google/gemini-2.5-pro",
  "openrouter:openai/gpt-4o",
  "openrouter:openai/o3-mini",
  "openrouter:meta-llama/llama-4-scout",
  "openrouter:deepseek/deepseek-r1",
];

export function RunEvalForm() {
  const router = useRouter();
  const [evals, setEvals] = useState<EvalOption[]>([]);
  const [evalName, setEvalName] = useState("");
  const [model, setModel] = useState(MODEL_PRESETS[0]);
  const [customModel, setCustomModel] = useState("");
  const [threshold, setThreshold] = useState("");
  const [loading, setLoading] = useState(false);
  const [evalsLoading, setEvalsLoading] = useState(true);
  const [message, setMessage] = useState<{
    type: "success" | "error";
    text: string;
  } | null>(null);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    fetch(`${API_BASE}/api/v1/evals`)
      .then((res) => {
        if (!res.ok) throw new Error("Failed to fetch evals");
        return res.json();
      })
      .then((data: EvalOption[]) => {
        setEvals(data);
        if (data.length > 0) setEvalName(data[0].name);
      })
      .catch(() => setEvals([]))
      .finally(() => setEvalsLoading(false));
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!evalName || !model) return;

    setLoading(true);
    setMessage(null);

    try {
      const body: Record<string, unknown> = { eval_name: evalName, model };
      if (threshold) body.threshold = parseFloat(threshold);

      const res = await fetch(`${API_BASE}/api/v1/runs`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });

      if (!res.ok) {
        const text = await res.text().catch(() => "");
        throw new Error(text || `HTTP ${res.status}`);
      }

      const data = await res.json();
      setMessage({
        type: "success",
        text: `Run submitted (ID: ${data.id})`,
      });
      router.refresh();
    } catch (err) {
      setMessage({
        type: "error",
        text: err instanceof Error ? err.message : "Submit failed",
      });
    } finally {
      setLoading(false);
    }
  };

  const inputClass =
    "bg-surface border border-border rounded px-3 py-1.5 text-sm text-text-primary placeholder:text-text-secondary focus:outline-none focus:ring-1 focus:ring-accent";

  return (
    <div className="border border-border rounded-lg">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between px-4 py-3 text-sm font-medium text-text-primary hover:bg-surface/50 transition-colors"
      >
        <span>Run Eval</span>
        <svg
          className={`w-4 h-4 transition-transform ${open ? "rotate-180" : ""}`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M19 9l-7 7-7-7"
          />
        </svg>
      </button>

      {open && (
        <form onSubmit={handleSubmit} className="px-4 pb-4 space-y-3">
          <div className="flex flex-wrap gap-3 items-end">
            {/* Eval selector */}
            <div className="flex flex-col gap-1">
              <label className="text-xs text-text-secondary">Eval</label>
              <select
                value={evalName}
                onChange={(e) => setEvalName(e.target.value)}
                disabled={evalsLoading}
                className={inputClass}
              >
                {evalsLoading ? (
                  <option>Loading...</option>
                ) : evals.length === 0 ? (
                  <option>No evals found</option>
                ) : (
                  evals.map((ev) => (
                    <option key={ev.id} value={ev.name}>
                      {ev.name}
                    </option>
                  ))
                )}
              </select>
            </div>

            {/* Model selector */}
            <div className="flex flex-col gap-1">
              <label className="text-xs text-text-secondary">Model</label>
              <select
                value={MODEL_PRESETS.includes(model) ? model : "__custom__"}
                onChange={(e) => {
                  if (e.target.value === "__custom__") {
                    setModel(customModel);
                  } else {
                    setModel(e.target.value);
                  }
                }}
                className={`${inputClass} min-w-[320px]`}
              >
                {MODEL_PRESETS.map((preset) => (
                  <option key={preset} value={preset}>
                    {preset}
                  </option>
                ))}
                <option value="__custom__">Other...</option>
              </select>
            </div>

            {/* Custom model input (shown when "Other" selected) */}
            {!MODEL_PRESETS.includes(model) && (
              <div className="flex flex-col gap-1">
                <label className="text-xs text-text-secondary">Custom Model</label>
                <input
                  type="text"
                  value={customModel}
                  onChange={(e) => {
                    setCustomModel(e.target.value);
                    setModel(e.target.value);
                  }}
                  placeholder="e.g. openrouter:provider/model-name"
                  className={`${inputClass} min-w-[280px]`}
                />
              </div>
            )}

            {/* Threshold input */}
            <div className="flex flex-col gap-1">
              <label className="text-xs text-text-secondary">
                Threshold (optional)
              </label>
              <input
                type="number"
                value={threshold}
                onChange={(e) => setThreshold(e.target.value)}
                placeholder="0.7"
                step="0.01"
                min="0"
                max="1"
                className={`${inputClass} w-24`}
              />
            </div>

            {/* Submit button */}
            <button
              type="submit"
              disabled={loading || !evalName || !model}
              className="bg-accent text-white rounded px-4 py-1.5 text-sm font-medium hover:bg-accent/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {loading ? "Submitting..." : "Submit"}
            </button>
          </div>

          {/* Status message */}
          {message && (
            <p
              className={`text-sm ${
                message.type === "success"
                  ? "text-green-400"
                  : "text-red-400"
              }`}
            >
              {message.text}
            </p>
          )}
        </form>
      )}
    </div>
  );
}

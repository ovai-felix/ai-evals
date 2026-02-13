export interface ConfidenceInterval {
  lower: number;
  upper: number;
  level: number;
}

export interface RunSummary {
  id: string;
  eval_name: string;
  model_name: string;
  status: "pending" | "running" | "completed" | "failed";
  score: number | null;
  ci: ConfidenceInterval | null;
  num_tasks: number | null;
  passed: boolean | null;
  threshold: number | null;
  error: string | null;
  submitted_at: string;
  started_at: string | null;
  completed_at: string | null;
}

export interface TaskResult {
  task_id: string;
  score: number;
  passed: boolean | null;
  prediction: string;
  reference: string;
  latency_ms: number;
  tokens_used: number;
  metadata: Record<string, unknown>;
  time: string | null;
}

export interface RunDetail extends RunSummary {
  results: TaskResult[];
  metadata: Record<string, unknown>;
}

export interface ModelInfo {
  name: string;
  family: string;
  parameter_size: string;
  quantization: string;
  multimodal: boolean;
  digest: string;
}

export interface HealthStatus {
  status: string;
  db: boolean;
  redis: boolean;
  ollama: boolean;
}

export interface TaxonomyNode {
  id: number;
  parent_id: number | null;
  name: string;
  description: string;
  level: number;
  eval_count: number;
  avg_discrimination: number;
  children: TaxonomyNode[];
  evals: {
    id: number;
    name: string;
    discrimination_power: number | null;
    lifecycle_state: string | null;
  }[];
}

export interface EvalHealth {
  eval_id: number;
  eval_name: string;
  discrimination_power: number;
  saturation_type: string | null;
  lifecycle_state: string;
  last_checked: string | null;
}

export interface CoverageSummary {
  total_categories: number;
  total_nodes: number;
  covered_nodes: number;
  gap_count: number;
  coverage_pct: number;
  saturation_rate: number;
  avg_discrimination: number;
  active_count: number;
  watch_count: number;
  saturated_count: number;
  archived_count: number;
}

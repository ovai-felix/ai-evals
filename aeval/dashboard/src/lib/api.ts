import type {
  CoverageSummary,
  EvalHealth,
  HealthStatus,
  ModelInfo,
  RunDetail,
  RunSummary,
  TaxonomyNode,
} from "./types";

const API_URL = process.env.API_URL || "http://localhost:8081";
const BASE = `${API_URL}/api/v1`;

async function fetchAPI<T>(path: string, revalidate = 5): Promise<T> {
  const res = await fetch(`${BASE}${path}`, { next: { revalidate } });
  if (!res.ok) {
    throw new Error(`API error ${res.status}: ${path}`);
  }
  return res.json() as Promise<T>;
}

export function getHealth(): Promise<HealthStatus> {
  return fetchAPI<HealthStatus>("/health");
}

export function getRuns(params?: {
  eval_name?: string;
  model?: string;
  status?: string;
  limit?: number;
  offset?: number;
}): Promise<RunSummary[]> {
  const sp = new URLSearchParams();
  if (params?.eval_name) sp.set("eval_name", params.eval_name);
  if (params?.model) sp.set("model", params.model);
  if (params?.status) sp.set("status", params.status);
  if (params?.limit) sp.set("limit", String(params.limit));
  if (params?.offset) sp.set("offset", String(params.offset));
  const qs = sp.toString();
  return fetchAPI<RunSummary[]>(`/runs${qs ? `?${qs}` : ""}`);
}

export function getRun(id: string): Promise<RunDetail> {
  return fetchAPI<RunDetail>(`/runs/${id}`);
}

export function getResults(params?: {
  eval_name?: string;
  model?: string;
  limit?: number;
  offset?: number;
}): Promise<RunSummary[]> {
  const sp = new URLSearchParams();
  if (params?.eval_name) sp.set("eval_name", params.eval_name);
  if (params?.model) sp.set("model", params.model);
  if (params?.limit) sp.set("limit", String(params.limit));
  if (params?.offset) sp.set("offset", String(params.offset));
  const qs = sp.toString();
  return fetchAPI<RunSummary[]>(`/results${qs ? `?${qs}` : ""}`);
}

export function getModels(): Promise<ModelInfo[]> {
  return fetchAPI<ModelInfo[]>("/models");
}

export function getTaxonomy(): Promise<TaxonomyNode[]> {
  return fetchAPI<TaxonomyNode[]>("/taxonomy");
}

export function getCoverage(): Promise<CoverageSummary> {
  return fetchAPI<CoverageSummary>("/health/coverage");
}

export function getEvalHealth(params?: {
  lifecycle_state?: string;
}): Promise<EvalHealth[]> {
  const sp = new URLSearchParams();
  if (params?.lifecycle_state) sp.set("lifecycle_state", params.lifecycle_state);
  const qs = sp.toString();
  return fetchAPI<EvalHealth[]>(`/health/evals${qs ? `?${qs}` : ""}`);
}

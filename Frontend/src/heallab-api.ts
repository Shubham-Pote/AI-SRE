export type Mode = "observe" | "automatic";
export type Fault = "none" | "errors" | "memory" | "cpu";
export type IncidentStatus = "detected" | "observed" | "executing" | "verifying" | "resolved" | "escalated";

export interface Telemetry {
  timestamp: number;
  rps: number;
  errors: number;
  latency: number;
  memory: number;
  memory_limit: number;
  cpu: number;
  ready: number;
  replicas: number;
  revision: string;
  rollout_complete: boolean;
  anomaly?: boolean;
  score?: number | null;
  model_version?: string | null;
  model_error?: string;
  forecast_seconds?: number | null;
}

export interface Status {
  mode: Mode;
  telemetry: Partial<Telemetry>;
  stale: boolean;
  worker_error: string | null;
  baseline_ready: boolean;
}

export interface Incident {
  id: number;
  created: number;
  updated: number;
  status: IncidentStatus;
  payload: {
    cause: string;
    action: string;
    evidence: string;
    cluster?: string;
    namespace?: string;
    workload?: string;
    window?: Partial<Telemetry>;
    ml?: { anomaly?: boolean; score?: number | null; model_version?: string | null };
  };
}

export interface IncidentEvent {
  id: number;
  incident: number;
  time: number;
  kind: string;
  payload: Record<string, unknown>;
}

export interface IncidentDetail extends Incident {
  events: IncidentEvent[];
}

export interface Experiment {
  timestamp?: number;
  fault?: Fault;
  revision?: string;
}

async function request<T>(path: string, init?: RequestInit, signal?: AbortSignal): Promise<T> {
  const response = await fetch(`/control${path}`, {
    ...init,
    signal,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!response.ok) {
    let detail = `${response.status} ${response.statusText}`;
    try {
      const body = await response.json();
      if (typeof body.detail === "string") detail = body.detail;
    } catch { /* Keep the HTTP message. */ }
    throw new Error(detail);
  }
  return response.json() as Promise<T>;
}

export const api = {
  status: (signal?: AbortSignal) => request<Status>("/status", undefined, signal),
  history: (signal?: AbortSignal) => request<Telemetry[]>("/telemetry/history", undefined, signal),
  incidents: (signal?: AbortSignal) => request<Incident[]>("/incidents", undefined, signal),
  incident: (id: number, signal?: AbortSignal) => request<IncidentDetail>(`/incidents/${id}`, undefined, signal),
  experiment: (signal?: AbortSignal) => request<Experiment>("/experiments", undefined, signal),
  setMode: (mode: Mode) => request<{ mode: Mode }>("/mode", { method: "PUT", body: JSON.stringify({ mode }) }),
  setFault: (fault: Fault) => request<Experiment>("/experiments", { method: "POST", body: JSON.stringify({ fault }) }),
};

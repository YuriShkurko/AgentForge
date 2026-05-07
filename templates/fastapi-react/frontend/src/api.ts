const BASE = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

async function post<T>(path: string, body?: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: body !== undefined ? { "Content-Type": "application/json" } : {},
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) throw new Error(`POST ${path} failed: ${res.status}`);
  return res.json();
}

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) throw new Error(`GET ${path} failed: ${res.status}`);
  return res.json();
}

export const api = {
  ingest: () => post<{ run_id: string; raw_records_inserted: number; normalized_inserted: number }>("/ingest"),
  score: (rescore = false) => post<{ scores_written: number; rescore: boolean }>(`/records/score?rescore=${rescore}`),
  getRuns: () => get<{ runs: import("./types").ProviderRun[] }>("/runs"),
  getRecords: () => get<{ records: import("./types").RecordItem[] }>("/records"),
  getScoredRecords: () => get<{ records: import("./types").ScoredRecord[] }>("/records/scored"),
  recordAction: (recordId: string, actionType: "accept" | "skip" | "save") =>
    post<{ ok: boolean; record_id: string; action_type: string; status: string }>(
      `/records/${recordId}/action`,
      { action_type: actionType }
    ),
};

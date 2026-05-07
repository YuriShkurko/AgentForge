export interface ProviderRun {
  id: string;
  provider_name: string;
  started_at: string;
  finished_at: string | null;
  status: "running" | "complete" | "error";
  stats: { raw_inserted: number; normalized_inserted: number } | null;
  error: string | null;
}

export interface RecordItem {
  id: string;
  external_id: string;
  source: string;
  title: string;
  category: string;
  value: number;
  ingested_at: string;
}

export interface Explanation {
  fit_score: number;
  summary: string;
  drivers: string[];
  risks: string[];
}

export interface ScoreDetail {
  fit: number;
  label: "high" | "medium" | "low";
  recommendation: "accept" | "review" | "skip";
  explanation: Explanation;
}

export interface ActionStatus {
  action_type: string;
  status: "pending" | "accepted" | "skipped" | "saved";
}

export interface ScoredRecord {
  record: RecordItem;
  score: ScoreDetail;
  action: ActionStatus | null;
}

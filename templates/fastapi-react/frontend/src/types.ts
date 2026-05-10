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
  updated_at?: string | null;
}

export interface ScoredRecord {
  record: RecordItem;
  score: ScoreDetail;
  action: ActionStatus | null;
}

export interface NotificationPreview {
  id: string;
  record_id: string;
  title: string;
  score: number;
  label: "high" | "medium" | "low";
  recommendation: "accept" | "review" | "skip";
  summary: string;
  drivers: string[];
  risks: string[];
  available_actions: TriageAction[];
  delivery_channel: "preview";
  delivery_status: "previewed";
  action: ActionStatus | null;
  created_at: string;
  updated_at: string;
}

export type TriageAction = "accept" | "skip" | "save";

export interface ActionEvent {
  id: string;
  record_id: string;
  action_type: TriageAction;
  status: "accepted" | "skipped" | "saved";
  created_at: string;
}

export interface AgentMessage {
  id: string;
  role: "user" | "assistant" | "tool";
  content: string;
  metadata: Record<string, unknown> | null;
  created_at: string;
}

export interface AgentToolEvent {
  tool_name: string;
  arguments: Record<string, unknown>;
  ok: boolean;
  result: Record<string, unknown> | null;
  error: string | null;
  error_code?: string | null;
  status?: "running" | "succeeded" | "failed";
}

export interface AgentChatResponse {
  conversation_id: string;
  assistant_message: AgentMessage;
  messages: AgentMessage[];
  tool_events: AgentToolEvent[];
}

export type AgentStreamEventName = "message_start" | "text_delta" | "tool_call" | "tool_result" | "error" | "done";

export interface AgentStreamEvent {
  event: AgentStreamEventName;
  data: Record<string, unknown>;
}

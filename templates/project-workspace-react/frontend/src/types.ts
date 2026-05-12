export interface Project {
  id: string;
  name: string;
  description: string;
  owner: string;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface Task {
  id: string;
  project_id: string;
  title: string;
  description: string;
  status: "todo" | "in_progress" | "blocked" | "done" | string;
  priority: "low" | "medium" | "high" | string;
  owner: string;
  due_date: string | null;
  created_at: string;
  updated_at: string;
}

export interface ActivityEvent {
  id: string;
  project_id: string;
  task_id: string | null;
  event_type: string;
  body: string;
  actor: string;
  event_metadata: Record<string, unknown> | null;
  created_at: string;
}

export interface AgentMessage {
  id: string;
  role: "user" | "assistant" | "tool" | string;
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
  status?: "running" | "succeeded" | "failed" | string;
}

export interface AgentChatResponse {
  conversation_id: string;
  assistant_message: AgentMessage;
  messages: AgentMessage[];
  tool_events: AgentToolEvent[];
}

export interface WorkspaceWidget {
  id: string;
  widget_type: string;
  title: string;
  source_tool: string;
  data: unknown;
  position: number;
  metadata: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
}

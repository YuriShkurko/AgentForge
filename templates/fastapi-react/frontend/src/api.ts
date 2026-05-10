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

async function del<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`, { method: "DELETE" });
  if (!res.ok) throw new Error(`DELETE ${path} failed: ${res.status}`);
  return res.json();
}

async function streamAgentChat(
  message: string,
  conversationId: string | undefined,
  onEvent: (event: import("./types").AgentStreamEvent) => void
): Promise<void> {
  const res = await fetch(`${BASE}/agent/chat/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
    body: JSON.stringify({ message, conversation_id: conversationId ?? null }),
  });
  if (!res.ok) throw new Error(`POST /agent/chat/stream failed: ${res.status}`);
  if (!res.body) throw new Error("Streaming response body is unavailable.");

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();
    buffer += decoder.decode(value, { stream: !done });
    const frames = buffer.split("\n\n");
    buffer = frames.pop() ?? "";

    for (const frame of frames) {
      const event = parseSseFrame(frame);
      if (event) onEvent(event);
    }

    if (done) break;
  }

  const event = parseSseFrame(buffer);
  if (event) onEvent(event);
}

function parseSseFrame(frame: string): import("./types").AgentStreamEvent | null {
  const lines = frame.split("\n").filter(Boolean);
  const eventLine = lines.find((line) => line.startsWith("event: "));
  const dataLine = lines.find((line) => line.startsWith("data: "));
  if (!eventLine || !dataLine) return null;
  return {
    event: eventLine.slice("event: ".length) as import("./types").AgentStreamEventName,
    data: JSON.parse(dataLine.slice("data: ".length)) as Record<string, unknown>,
  };
}

export const api = {
  ingest: () => post<{ run_id: string; raw_records_inserted: number; normalized_inserted: number }>("/ingest"),
  score: (rescore = false) => post<{ scores_written: number; rescore: boolean }>(`/records/score?rescore=${rescore}`),
  createNotificationPreviews: () => post<{ previews_written: number }>("/notifications/previews"),
  getNotificationPreviews: () => get<{ previews: import("./types").NotificationPreview[] }>("/notifications/previews"),
  getActionHistory: () => get<{ events: import("./types").ActionEvent[] }>("/actions/history"),
  getRuns: () => get<{ runs: import("./types").ProviderRun[] }>("/runs"),
  getRecords: () => get<{ records: import("./types").RecordItem[] }>("/records"),
  getScoredRecords: () => get<{ records: import("./types").ScoredRecord[] }>("/records/scored"),
  agentChat: (message: string, conversationId?: string) =>
    post<import("./types").AgentChatResponse>("/agent/chat", {
      message,
      conversation_id: conversationId ?? null,
    }),
  streamAgentChat,
  getAgentConversation: (conversationId: string) =>
    get<{ conversation_id: string; messages: import("./types").AgentMessage[] }>(
      `/agent/conversations/${conversationId}`
    ),
  getWorkspaceWidgets: () => get<{ widgets: import("./types").WorkspaceWidget[] }>("/workspace/widgets"),
  createWorkspaceWidget: (body: {
    widget_type: string;
    title: string;
    source_tool: string;
    data: unknown;
    metadata?: Record<string, unknown> | null;
  }) => post<{ widget: import("./types").WorkspaceWidget }>("/workspace/widgets", body),
  removeWorkspaceWidget: (widgetId: string) =>
    del<{ removed: boolean; widget_id: string }>(`/workspace/widgets/${widgetId}`),
  reorderWorkspaceWidgets: (widgetIds: string[]) =>
    post<{ reordered: boolean; widget_ids: string[]; widgets: import("./types").WorkspaceWidget[] }>(
      "/workspace/widgets/reorder",
      { widget_ids: widgetIds }
    ),
  recordAction: (recordId: string, actionType: import("./types").TriageAction) =>
    post<{ ok: boolean; record_id: string; action_type: string; status: string }>(
      `/records/${recordId}/action`,
      { action_type: actionType }
    ),
};

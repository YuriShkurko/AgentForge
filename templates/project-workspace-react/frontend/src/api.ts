const BASE = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) throw new Error(`GET ${path} failed: ${res.status}`);
  return res.json();
}

async function post<T>(path: string, body?: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: body !== undefined ? { "Content-Type": "application/json" } : {},
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) throw new Error(`POST ${path} failed: ${res.status}`);
  return res.json();
}

async function patch<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`PATCH ${path} failed: ${res.status}`);
  return res.json();
}

async function del<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`, { method: "DELETE" });
  if (!res.ok) throw new Error(`DELETE ${path} failed: ${res.status}`);
  return res.json();
}

export const api = {
  seed: () => post<{ created_projects: number; created_tasks: number }>("/seed"),
  getProjects: () => get<import("./types").Project[]>("/projects"),
  getTasks: () => get<import("./types").Task[]>("/tasks"),
  createTask: (body: Partial<import("./types").Task> & { project_id: string; title: string }) => post<import("./types").Task>("/tasks", body),
  updateTask: (taskId: string, body: Partial<import("./types").Task>) => patch<import("./types").Task>(`/tasks/${taskId}`, body),
  addNote: (projectId: string, body: { body: string; task_id?: string | null; actor?: string }) => post<import("./types").ActivityEvent>(`/projects/${projectId}/notes`, body),
  getActivity: () => get<import("./types").ActivityEvent[]>("/activity"),
  agentChat: (message: string, conversationId?: string) => post<import("./types").AgentChatResponse>("/agent/chat", { message, conversation_id: conversationId ?? null }),
  getWidgets: () => get<import("./types").WorkspaceWidget[]>("/workspace/widgets"),
  removeWidget: (widgetId: string) => del<{ removed: boolean; widget_id: string }>(`/workspace/widgets/${widgetId}`),
};

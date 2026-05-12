import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { api } from "./api";
import { WorkspacePanel } from "./components/WorkspacePanel";
import type { ActivityEvent, AgentMessage, AgentToolEvent, Project, Task, WorkspaceWidget } from "./types";
import "./styles.css";

const STORAGE_KEY = "project-workspace-agent-conversation";

export default function App() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [activity, setActivity] = useState<ActivityEvent[]>([]);
  const [widgets, setWidgets] = useState<WorkspaceWidget[]>([]);
  const [messages, setMessages] = useState<AgentMessage[]>([]);
  const [toolEvents, setToolEvents] = useState<AgentToolEvent[]>([]);
  const [conversationId, setConversationId] = useState<string | undefined>(() => localStorage.getItem(STORAGE_KEY) ?? undefined);
  const [agentInput, setAgentInput] = useState("summarize the project workspace");
  const [note, setNote] = useState("Reviewed launch risk and next task owner.");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    const [nextProjects, nextTasks, nextActivity, nextWidgets] = await Promise.all([
      api.getProjects(),
      api.getTasks(),
      api.getActivity(),
      api.getWidgets(),
    ]);
    setProjects(nextProjects);
    setTasks(nextTasks);
    setActivity(nextActivity);
    setWidgets(nextWidgets);
  }, []);

  useEffect(() => {
    refresh().catch((err) => setError(String(err)));
  }, [refresh]);

  const stats = useMemo(() => {
    const open = tasks.filter((task) => task.status !== "done").length;
    const blocked = tasks.filter((task) => task.status === "blocked").length;
    const high = tasks.filter((task) => task.priority === "high").length;
    return { open, blocked, high };
  }, [tasks]);

  async function seed() {
    setBusy(true);
    setError(null);
    try {
      await api.seed();
      await refresh();
    } catch (err) {
      setError(String(err));
    } finally {
      setBusy(false);
    }
  }

  async function cycleTask(task: Task) {
    const next = task.status === "todo" ? "in_progress" : task.status === "in_progress" ? "done" : task.status === "blocked" ? "in_progress" : "todo";
    await api.updateTask(task.id, { status: next });
    await refresh();
  }

  async function addNote(event: FormEvent) {
    event.preventDefault();
    if (!projects[0] || !note.trim()) return;
    await api.addNote(projects[0].id, { body: note, actor: "operator" });
    setNote("");
    await refresh();
  }

  async function sendAgent(event: FormEvent) {
    event.preventDefault();
    if (!agentInput.trim()) return;
    setBusy(true);
    setError(null);
    try {
      const result = await api.agentChat(agentInput, conversationId);
      setConversationId(result.conversation_id);
      localStorage.setItem(STORAGE_KEY, result.conversation_id);
      setMessages(result.messages);
      setToolEvents(result.tool_events);
      setAgentInput("");
      await refresh();
    } catch (err) {
      setError(String(err));
    } finally {
      setBusy(false);
    }
  }

  async function removeWidget(id: string) {
    await api.removeWidget(id);
    await refresh();
  }

  return (
    <main className="app-shell">
      <header className="hero">
        <div>
          <p className="eyebrow">AgentForge generated app</p>
          <h1>Project Workspace Demo</h1>
          <p>A local task planning workspace with seeded projects, deterministic persistence, scripted agent tools, and pinned widgets.</p>
        </div>
        <button data-testid="seed-btn" type="button" onClick={seed} disabled={busy}>Seed sample workspace</button>
      </header>

      {error && <p className="error">{error}</p>}

      <section className="stat-grid">
        <div><span>{projects.length}</span><small>Projects</small></div>
        <div><span>{tasks.length}</span><small>Total tasks</small></div>
        <div><span>{stats.open}</span><small>Open tasks</small></div>
        <div><span>{stats.blocked}</span><small>Blocked</small></div>
      </section>

      <div className="main-grid">
        <section className="panel" data-testid="project-panel">
          <div className="panel-head"><h2>Projects</h2><span className="count-pill">{stats.high} high priority</span></div>
          {projects.length === 0 ? <p className="empty">No projects yet. Seed the sample workspace.</p> : projects.map((project) => (
            <article key={project.id} className="project-card" data-testid="project-card">
              <strong>{project.name}</strong>
              <p>{project.description}</p>
              <small>Owner: {project.owner}</small>
            </article>
          ))}
        </section>

        <section className="panel" data-testid="task-panel">
          <div className="panel-head"><h2>Tasks</h2><span className="count-pill">Click status to advance</span></div>
          <div className="task-list">
            {tasks.map((task) => (
              <article key={task.id} className={`task-card ${task.priority}`} data-testid="task-card">
                <div>
                  <strong>{task.title}</strong>
                  <p>{task.owner} · due {task.due_date ?? "unscheduled"}</p>
                </div>
                <button data-testid="task-status-btn" type="button" onClick={() => cycleTask(task)}>{task.status}</button>
              </article>
            ))}
          </div>
        </section>
      </div>

      <div className="main-grid lower">
        <section className="panel agent-panel" data-testid="agent-panel">
          <div className="panel-head"><h2>Scripted agent</h2><span className="count-pill">Local tools</span></div>
          <p className="helper">Try “list tasks”, “summarize project”, or “pin task list”.</p>
          <div className="messages" data-testid="agent-messages">
            {messages.length === 0 ? <p className="empty">No conversation yet.</p> : messages.map((message) => <p key={message.id}><strong>{message.role}:</strong> {message.content}</p>)}
          </div>
          {toolEvents.map((tool, index) => <p key={`${tool.tool_name}-${index}`} data-testid="agent-tool-event" className="tool-event">ran {tool.tool_name}</p>)}
          <form onSubmit={sendAgent} className="agent-form">
            <input data-testid="agent-input" value={agentInput} onChange={(event) => setAgentInput(event.target.value)} disabled={busy} />
            <button data-testid="agent-send-btn" disabled={busy}>Send</button>
          </form>
        </section>

        <WorkspacePanel widgets={widgets} onRemove={removeWidget} />
      </div>

      <section className="panel activity-panel" data-testid="activity-panel">
        <div className="panel-head"><h2>Notes and activity</h2></div>
        <form onSubmit={addNote} className="note-form">
          <input data-testid="note-input" value={note} onChange={(event) => setNote(event.target.value)} />
          <button data-testid="note-btn">Add note</button>
        </form>
        <ul>
          {activity.slice(0, 10).map((item) => <li key={item.id} data-testid="activity-row"><strong>{item.event_type}</strong> — {item.body}</li>)}
        </ul>
      </section>
    </main>
  );
}

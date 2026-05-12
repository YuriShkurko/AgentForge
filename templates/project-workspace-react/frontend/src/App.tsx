import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { api } from "./api";
import { WorkspacePanel } from "./components/WorkspacePanel";
import { customization } from "./customization";
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
  const [agentInput, setAgentInput] = useState<string>(customization.agentStarters[0] ?? "summarize the project workspace");
  const [note, setNote] = useState(`Reviewed next ${customization.projectWorkspace.taskLabel.singular} owner.`);
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
    const done = tasks.filter((task) => task.status === "done").length;
    return { open, blocked, high, done };
  }, [tasks]);

  const visibleActivity = useMemo(() => {
    const priority: Record<string, number> = {
      note_added: 3,
      task_updated: 2,
      task_created: 1,
      project_created: 1,
    };
    return [...activity].sort((a, b) => {
      const timeDelta = new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
      if (timeDelta !== 0) return timeDelta;
      return (priority[b.event_type] ?? 0) - (priority[a.event_type] ?? 0);
    });
  }, [activity]);

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
      <aside className="side-rail" aria-label="Workspace navigation">
        <div>
          <p className="eyebrow">AgentForge</p>
          <strong>{customization.app.name}</strong>
        </div>
        <nav>
          <span>Overview</span>
          <span>{titleCase(customization.projectWorkspace.taskLabel.plural)}</span>
          <span>Agent tools</span>
          <span>Activity</span>
        </nav>
        <div className="mode-card">
          <span className="mode-dot" />
          <div>
            <strong>Local safe mode</strong>
            <small>Seeded data, SQLite-ready persistence, no live LLM.</small>
          </div>
        </div>
      </aside>

      <div className="workspace-shell">
        <header className="hero">
          <div>
            <p className="eyebrow">{customization.app.workflowLabel}</p>
            <h1>{customization.app.name}</h1>
            <p>{customization.app.subtitle}</p>
          </div>
          <button data-testid="seed-btn" type="button" onClick={seed} disabled={busy}>Seed {customization.projectWorkspace.sampleDataLabel}</button>
        </header>

        {error && <p className="error">{error}</p>}

        <section className="stat-grid">
          <div><span>{projects.length}</span><small>{titleCase(customization.projectWorkspace.projectLabel.plural)}</small></div>
          <div><span>{tasks.length}</span><small>Total {customization.projectWorkspace.taskLabel.plural}</small></div>
          <div><span>{stats.open}</span><small>Open {customization.projectWorkspace.taskLabel.plural}</small></div>
          <div><span>{stats.done}</span><small>Done</small></div>
          <div><span>{stats.blocked}</span><small>Blocked</small></div>
        </section>

        <div className="main-grid">
          <section className="panel" data-testid="project-panel">
            <div className="panel-head">
              <div>
                <p className="eyebrow">Overview</p>
                <h2>{titleCase(customization.projectWorkspace.projectLabel.plural)}</h2>
              </div>
              <span className="count-pill">{stats.high} high priority</span>
            </div>
            {projects.length === 0 ? <p className="empty-card">No {customization.projectWorkspace.projectLabel.plural} yet. Seed {customization.projectWorkspace.sampleDataLabel}.</p> : projects.map((project) => (
              <article key={project.id} className="project-card" data-testid="project-card">
                <div>
                  <strong>{project.name}</strong>
                  <p>{project.description}</p>
                </div>
                <div className="project-meta">
                  <span className="count-pill">Owner: {project.owner}</span>
                  <span className="status-pill">{project.status}</span>
                </div>
              </article>
            ))}
          </section>

          <section className="panel" data-testid="task-panel">
            <div className="panel-head">
              <div>
                <p className="eyebrow">{titleCase(customization.projectWorkspace.taskLabel.singular)} queue</p>
                <h2>{titleCase(customization.projectWorkspace.taskLabel.plural)}</h2>
              </div>
              <span className="count-pill">Click status to advance</span>
            </div>
            <div className="task-list">
              {tasks.length === 0 ? <p className="empty-card">No {customization.projectWorkspace.taskLabel.plural} yet. Seed {customization.projectWorkspace.sampleDataLabel}.</p> : tasks.map((task) => (
                <article key={task.id} className={`task-card ${task.priority}`} data-testid="task-card">
                  <div>
                    <strong>{task.title}</strong>
                    <p>{task.owner} · due {task.due_date ?? "unscheduled"}</p>
                    <div className="task-meta">
                      <span className={`priority-pill ${task.priority}`}>{task.priority}</span>
                      <span className={`status-pill ${task.status}`}>{task.status}</span>
                    </div>
                  </div>
                  <button data-testid="task-status-btn" type="button" onClick={() => cycleTask(task)}>{task.status}</button>
                </article>
              ))}
            </div>
          </section>
        </div>

        <div className="main-grid lower">
          <section className="panel agent-panel" data-testid="agent-panel">
            <div className="panel-head">
              <div>
                <p className="eyebrow">Agent tools</p>
                <h2>Scripted agent</h2>
              </div>
              <span className="count-pill">Local tools</span>
            </div>
            <p className="helper">Try {formatStarters(customization.agentStarters)}.</p>
            <div className="messages" data-testid="agent-messages">
              {messages.length === 0 ? <p className="empty-card">No conversation yet.</p> : messages.map((message) => <p key={message.id} className="message-bubble"><strong>{message.role}:</strong> {message.content}</p>)}
            </div>
            {toolEvents.map((tool, index) => <p key={`${tool.tool_name}-${index}`} data-testid="agent-tool-event" className={`tool-event ${tool.ok === false ? "failed" : ""}`}>{tool.ok === false ? "failed" : "ran"} {tool.tool_name}</p>)}
            <form onSubmit={sendAgent} className="agent-form">
              <input aria-label="Agent message" data-testid="agent-input" value={agentInput} onChange={(event) => setAgentInput(event.target.value)} disabled={busy} />
              <button data-testid="agent-send-btn" disabled={busy}>Send</button>
            </form>
          </section>

          <WorkspacePanel widgets={widgets} onRemove={removeWidget} />
        </div>

        <section className="panel activity-panel" data-testid="activity-panel">
          <div className="panel-head">
            <div>
              <p className="eyebrow">Project log</p>
              <h2>{customization.projectWorkspace.activityLabel}</h2>
            </div>
          </div>
          <form onSubmit={addNote} className="note-form">
            <input aria-label="Project note" data-testid="note-input" value={note} onChange={(event) => setNote(event.target.value)} />
            <button data-testid="note-btn">Add note</button>
          </form>
          <ul>
            {visibleActivity.length === 0 ? <li className="empty-card">No activity yet.</li> : visibleActivity.slice(0, 10).map((item) => <li key={item.id} data-testid="activity-row"><span className="status-pill">{item.event_type}</span><strong>{item.actor}</strong><span>{item.body}</span></li>)}
          </ul>
        </section>
      </div>
    </main>
  );
}

function titleCase(value: string): string {
  return value.replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function formatStarters(starters: readonly string[]): string {
  return starters.map((starter) => `“${starter}”`).join(", ");
}

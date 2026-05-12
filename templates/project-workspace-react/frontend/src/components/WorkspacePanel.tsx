import type { WorkspaceWidget } from "../types";

interface Props {
  widgets: WorkspaceWidget[];
  onRemove: (id: string) => void;
}

export function WorkspacePanel({ widgets, onRemove }: Props) {
  return (
    <section className="panel workspace-panel" data-testid="workspace-panel">
      <div className="panel-head">
        <div>
          <p className="eyebrow">Workspace</p>
          <h2>Pinned project context</h2>
        </div>
        <span className="count-pill">{widgets.length} widgets</span>
      </div>
      {widgets.length === 0 ? (
        <p data-testid="workspace-empty" className="empty">Ask the agent to pin a project summary or task list.</p>
      ) : (
        <div className="widget-grid">
          {widgets.map((widget) => (
            <article key={widget.id} className="widget" data-testid="workspace-widget">
              <div className="widget-head">
                <strong>{widget.title}</strong>
                <button type="button" onClick={() => onRemove(widget.id)}>Remove</button>
              </div>
              <div className="widget-body">
                <WidgetBody widget={widget} />
              </div>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}

function WidgetBody({ widget }: { widget: WorkspaceWidget }) {
  if (widget.widget_type === "task_list") {
    const tasks = getArray(widget.data, "tasks");
    if (tasks.length === 0) return <p className="empty">No task rows were pinned.</p>;
    return (
      <ul className="widget-list">
        {tasks.slice(0, 6).map((item, index) => {
          const task = asObject(item);
          return (
            <li key={`${String(task.id ?? task.title ?? index)}-${index}`} className="widget-task-row">
              <span>
                <strong>{String(task.title ?? "Untitled task")}</strong>
                <small>{String(task.owner ?? "unassigned")} · due {String(task.due_date ?? "unscheduled")}</small>
              </span>
              <span className={`status-pill ${String(task.status ?? "")}`}>{String(task.status ?? "unknown")}</span>
            </li>
          );
        })}
      </ul>
    );
  }

  if (widget.widget_type === "project_summary") {
    const summary = asObject(widget.data);
    const projects = getArray(widget.data, "projects");
    return (
      <div>
        <p className="helper">{String(summary.summary ?? "Project summary pinned by the agent.")}</p>
        <ul className="summary-list">
          {projects.slice(0, 4).map((item, index) => {
            const project = asObject(item);
            const counts = asObject(project.task_counts);
            return (
              <li key={`${String(project.id ?? project.name ?? index)}-${index}`} className="summary-row">
                <strong>{String(project.name ?? "Project")}</strong>
                <span className="count-pill">{sumCounts(counts)} tasks</span>
              </li>
            );
          })}
        </ul>
      </div>
    );
  }

  return <pre>{JSON.stringify(widget.data, null, 2)}</pre>;
}

function asObject(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : {};
}

function getArray(value: unknown, key: string): unknown[] {
  const object = asObject(value);
  return Array.isArray(object[key]) ? (object[key] as unknown[]) : [];
}

function sumCounts(counts: Record<string, unknown>): number {
  return Object.values(counts).reduce<number>((total, value) => total + Number(value ?? 0), 0);
}

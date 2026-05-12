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
              <pre>{JSON.stringify(widget.data, null, 2)}</pre>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}

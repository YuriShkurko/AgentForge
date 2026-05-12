import { api } from "../api";
import { customization } from "../customization";
import type { WorkspaceWidget } from "../types";
import { WidgetRenderer } from "./WidgetRenderer";

interface Props {
  widgets: WorkspaceWidget[];
  loading: boolean;
  error: string | null;
  onChanged: () => Promise<void>;
}

export function WorkspacePanel({ widgets, loading, error, onChanged }: Props) {
  async function removeWidget(widgetId: string) {
    await api.removeWorkspaceWidget(widgetId);
    await onChanged();
  }

  async function moveWidget(index: number, direction: -1 | 1) {
    const nextIndex = index + direction;
    if (nextIndex < 0 || nextIndex >= widgets.length) return;
    const nextIds = widgets.map((widget) => widget.id);
    [nextIds[index], nextIds[nextIndex]] = [nextIds[nextIndex], nextIds[index]];
    await api.reorderWorkspaceWidgets(nextIds);
    await onChanged();
  }

  return (
    <section data-testid="workspace-panel" className="panel workspace-panel">
      <div className="workspace-top">
        <div>
          <div>
          <p className="eyebrow">Persisted workspace</p>
            <h2>
              Workspace
            <span
              data-testid="workspace-count"
              className="status-pill workspace-count"
            >
              {widgets.length} {widgets.length === 1 ? "widget" : customization.workspace.widgetLabel}
            </span>
            </h2>
          </div>
          <p className="panel-kicker">
            {customization.workspace.pinnedLabel} pinned by the scripted agent. Refreshing
            the page keeps saved widgets.
          </p>
        </div>
        <button
          data-testid="workspace-refresh-btn"
          onClick={onChanged}
          disabled={loading}
          className="workspace-refresh"
        >
          {loading ? "Refreshing" : "Refresh"}
        </button>
      </div>
      {loading && (
        <StatusMessage
          testId="workspace-loading"
          tone="muted"
          text={`Loading persisted workspace ${customization.workspace.widgetLabel}...`}
        />
      )}
      {error && (
        <StatusMessage testId="workspace-error" tone="error" text={error} />
      )}
      {!loading && widgets.length === 0 ? (
        <div
          data-testid="workspace-empty"
          className="empty-card"
        >
          <strong>
            No {customization.workspace.widgetLabel} pinned yet.
          </strong>
          {customization.workspace.emptyState}
        </div>
      ) : (
        <div className="widget-list">
          {widgets.map((widget, index) => (
            <article
              key={widget.id}
              data-testid="workspace-widget"
              className="widget-card"
            >
              <div className="widget-head">
                <div>
                  <strong>
                    {widget.title}
                  </strong>
                  <div className="widget-labels">
                    <Label>{labelize(widget.widget_type)}</Label>
                    <Label>{labelize(widget.source_tool)}</Label>
                  </div>
                </div>
                <div className="widget-actions">
                  <button
                    data-testid="workspace-move-up-btn"
                    onClick={() => moveWidget(index, -1)}
                    disabled={index === 0}
                    aria-label={`Move ${widget.title} up`}
                    className="widget-action"
                  >
                    Up
                  </button>
                  <button
                    data-testid="workspace-move-down-btn"
                    onClick={() => moveWidget(index, 1)}
                    disabled={index === widgets.length - 1}
                    aria-label={`Move ${widget.title} down`}
                    className="widget-action"
                  >
                    Down
                  </button>
                  <button
                    data-testid="workspace-remove-btn"
                    onClick={() => removeWidget(widget.id)}
                    aria-label={`Remove ${widget.title}`}
                    className="widget-action button-danger"
                  >
                    Remove
                  </button>
                </div>
              </div>
              <div className="widget-body">
                <WidgetRenderer widget={widget} />
              </div>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}

function Label({ children }: { children: string }) {
  return (
    <span className="label-pill">
      {children}
    </span>
  );
}

function StatusMessage({
  testId,
  tone,
  text,
}: {
  testId: string;
  tone: "muted" | "error";
  text: string;
}) {
  return (
    <p
      data-testid={testId}
      className={tone === "error" ? "result-card error-text" : "result-card"}
    >
      {text}
    </p>
  );
}

function labelize(value: string): string {
  return value
    .replace(/_/g, " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}


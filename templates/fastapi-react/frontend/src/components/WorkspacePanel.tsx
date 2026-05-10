import { api } from "../api";
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
    <section
      data-testid="workspace-panel"
      style={{
        border: "1px solid #d7dee8",
        borderRadius: 8,
        padding: "1rem",
        background: "#fbfcfe",
        marginTop: "1rem",
      }}
    >
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          gap: "1rem",
          alignItems: "flex-start",
          flexWrap: "wrap",
        }}
      >
        <div style={{ maxWidth: 620 }}>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "0.6rem",
              flexWrap: "wrap",
            }}
          >
            <h2 style={{ margin: 0 }}>Workspace</h2>
            <span
              data-testid="workspace-count"
              style={{
                border: "1px solid #cbd5e1",
                borderRadius: 999,
                padding: "0.15rem 0.5rem",
                fontSize: "0.78rem",
                fontWeight: 700,
                color: "#334155",
                background: "#fff",
              }}
            >
              {widgets.length} {widgets.length === 1 ? "widget" : "widgets"}
            </span>
          </div>
          <p
            style={{
              margin: "0.35rem 0 0",
              color: "#475569",
              fontSize: "0.92rem",
              lineHeight: 1.45,
            }}
          >
            Persisted dashboard cards pinned by the scripted agent. Refreshing
            the page keeps saved widgets.
          </p>
        </div>
        <button
          data-testid="workspace-refresh-btn"
          onClick={onChanged}
          disabled={loading}
          style={quietButtonStyle}
        >
          {loading ? "Refreshing" : "Refresh"}
        </button>
      </div>
      {loading && (
        <StatusMessage
          testId="workspace-loading"
          tone="muted"
          text="Loading persisted workspace widgets..."
        />
      )}
      {error && (
        <StatusMessage testId="workspace-error" tone="error" text={error} />
      )}
      {!loading && widgets.length === 0 ? (
        <div
          data-testid="workspace-empty"
          style={{
            border: "1px dashed #b8c4d4",
            borderRadius: 8,
            padding: "0.9rem",
            marginTop: "0.85rem",
            background: "#fff",
            color: "#475569",
            lineHeight: 1.45,
          }}
        >
          <strong
            style={{
              display: "block",
              color: "#1f2937",
              marginBottom: "0.25rem",
            }}
          >
            No widgets pinned yet.
          </strong>
          Ask the agent to pin scored records, notification previews, or action
          history.
        </div>
      ) : (
        <div style={{ display: "grid", gap: "0.85rem", marginTop: "0.9rem" }}>
          {widgets.map((widget, index) => (
            <article
              key={widget.id}
              data-testid="workspace-widget"
              style={{
                border: "1px solid #dbe3ee",
                borderRadius: 8,
                padding: "0.85rem",
                background: "#fff",
              }}
            >
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  gap: "0.75rem",
                  alignItems: "flex-start",
                  flexWrap: "wrap",
                }}
              >
                <div style={{ minWidth: 0 }}>
                  <strong
                    style={{
                      display: "block",
                      color: "#111827",
                      lineHeight: 1.3,
                    }}
                  >
                    {widget.title}
                  </strong>
                  <div
                    style={{
                      display: "flex",
                      gap: "0.35rem",
                      flexWrap: "wrap",
                      marginTop: "0.35rem",
                    }}
                  >
                    <Label>{labelize(widget.widget_type)}</Label>
                    <Label>{labelize(widget.source_tool)}</Label>
                  </div>
                </div>
                <div
                  style={{ display: "flex", gap: "0.35rem", flexWrap: "wrap" }}
                >
                  <button
                    data-testid="workspace-move-up-btn"
                    onClick={() => moveWidget(index, -1)}
                    disabled={index === 0}
                    aria-label={`Move ${widget.title} up`}
                    style={quietButtonStyle}
                  >
                    Up
                  </button>
                  <button
                    data-testid="workspace-move-down-btn"
                    onClick={() => moveWidget(index, 1)}
                    disabled={index === widgets.length - 1}
                    aria-label={`Move ${widget.title} down`}
                    style={quietButtonStyle}
                  >
                    Down
                  </button>
                  <button
                    data-testid="workspace-remove-btn"
                    onClick={() => removeWidget(widget.id)}
                    aria-label={`Remove ${widget.title}`}
                    style={dangerButtonStyle}
                  >
                    Remove
                  </button>
                </div>
              </div>
              <div style={{ marginTop: "0.75rem" }}>
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
    <span
      style={{
        border: "1px solid #e2e8f0",
        borderRadius: 999,
        padding: "0.12rem 0.45rem",
        fontSize: "0.76rem",
        color: "#475569",
        background: "#f8fafc",
      }}
    >
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
      style={{
        border: `1px solid ${tone === "error" ? "#fecaca" : "#dbe3ee"}`,
        borderRadius: 8,
        padding: "0.65rem 0.75rem",
        margin: "0.85rem 0 0",
        color: tone === "error" ? "#991b1b" : "#475569",
        background: tone === "error" ? "#fff7f7" : "#fff",
        fontSize: "0.9rem",
      }}
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

const quietButtonStyle = {
  border: "1px solid #cbd5e1",
  borderRadius: 6,
  background: "#fff",
  color: "#334155",
  padding: "0.35rem 0.55rem",
};

const dangerButtonStyle = {
  ...quietButtonStyle,
  color: "#9f1239",
  borderColor: "#fecdd3",
};

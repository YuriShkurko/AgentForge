import { api } from "../api";
import type { NotificationPreview, TriageAction } from "../types";

interface Props {
  previews: NotificationPreview[];
  onActionDone: () => void;
}

export function NotificationPreviewPanel({ previews, onActionDone }: Props) {
  async function handleAction(recordId: string, actionType: TriageAction) {
    await api.recordAction(recordId, actionType);
    onActionDone();
  }

  return (
    <section data-testid="notification-preview-panel">
      <h2>Notification Previews</h2>
      {previews.length === 0 ? (
        <p data-testid="preview-empty">No notification previews. Score records, then preview notifications.</p>
      ) : (
        <div style={{ display: "grid", gap: "0.75rem" }}>
          {previews.map((preview) => (
            <article
              key={preview.id}
              data-testid="notification-preview"
              style={{ border: "1px solid #ddd", borderRadius: 8, padding: "0.75rem" }}
            >
              <strong>{preview.title}</strong>
              <p style={{ margin: "0.35rem 0" }}>{preview.summary}</p>
              <div style={{ fontSize: "0.85rem", color: "#555" }}>
                Score {(preview.score * 100).toFixed(0)}% · {preview.label} · {preview.recommendation}
              </div>
              {preview.risks.length > 0 && (
                <div style={{ fontSize: "0.85rem", marginTop: "0.35rem" }}>
                  Risks: {preview.risks.join(", ")}
                </div>
              )}
              <div style={{ display: "flex", gap: "0.4rem", marginTop: "0.5rem", alignItems: "center" }}>
                {preview.available_actions.map((action) => (
                  <button
                    key={action}
                    data-testid={`preview-${action}-btn`}
                    onClick={() => handleAction(preview.record_id, action)}
                  >
                    {action === "save" ? "Save" : action[0].toUpperCase() + action.slice(1)}
                  </button>
                ))}
                <span data-testid="preview-action-state" style={{ fontSize: "0.85rem", fontWeight: 600 }}>
                  {preview.action ? preview.action.status : "pending"}
                </span>
              </div>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}

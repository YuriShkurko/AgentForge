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
    <section data-testid="notification-preview-panel" className="panel">
      <div className="panel-head">
        <div>
          <h2>Notification Previews</h2>
          <p className="panel-kicker">Preview-only outreach drafts, with no external delivery.</p>
        </div>
        <span className="status-pill">{previews.length} previews</span>
      </div>
      {previews.length === 0 ? (
        <p data-testid="preview-empty" className="empty-card">No notification previews. Score records, then preview notifications.</p>
      ) : (
        <div className="preview-grid">
          {previews.map((preview) => (
            <article
              key={preview.id}
              data-testid="notification-preview"
              className="preview-card"
            >
              <strong>{preview.title}</strong>
              <p>{preview.summary}</p>
              <div className="preview-meta">
                <span className="score-pill">Score {(preview.score * 100).toFixed(0)}%</span>
                <span className={`label-pill ${preview.label}`}>{preview.label}</span>
                <span className="status-pill">{preview.recommendation}</span>
              </div>
              {preview.risks.length > 0 && (
                <div className="helper">
                  Risks: {preview.risks.join(", ")}
                </div>
              )}
              <div className="preview-actions">
                {preview.available_actions.map((action) => (
                  <button
                    key={action}
                    data-testid={`preview-${action}-btn`}
                    className={action === "skip" ? "button-danger" : action === "save" ? "button-secondary" : undefined}
                    onClick={() => handleAction(preview.record_id, action)}
                  >
                    {action === "save" ? "Save" : action[0].toUpperCase() + action.slice(1)}
                  </button>
                ))}
                <span data-testid="preview-action-state" className={`status-pill ${preview.action?.status ?? "pending"}`}>
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

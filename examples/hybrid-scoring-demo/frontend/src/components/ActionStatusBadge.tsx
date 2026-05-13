import type { ActionStatus, TriageAction } from "../types";

interface Props {
  action: ActionStatus | null;
  recordId: string;
  onAction: (recordId: string, actionType: TriageAction) => void;
}

export function ActionStatusBadge({ action, recordId, onAction }: Props) {
  if (action) {
    return (
      <span
        data-testid="action-badge"
        className={`status-pill ${action.status}`}
      >
        {action.status}
      </span>
    );
  }

  return (
    <span className="action-buttons">
      <button data-testid="accept-btn" onClick={() => onAction(recordId, "accept")}>Accept</button>
      <button data-testid="skip-btn" className="button-danger" onClick={() => onAction(recordId, "skip")}>Skip</button>
      <button data-testid="save-btn" className="button-secondary" onClick={() => onAction(recordId, "save")}>Save</button>
    </span>
  );
}

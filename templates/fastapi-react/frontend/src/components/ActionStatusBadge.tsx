import type { ActionStatus } from "../types";

const COLORS: Record<string, string> = {
  accepted: "#2e7d32",
  skipped:  "#b71c1c",
  saved:    "#1565c0",
  pending:  "#795548",
};

interface Props {
  action: ActionStatus | null;
  recordId: string;
  onAction: (recordId: string, actionType: "accept" | "skip" | "save") => void;
}

export function ActionStatusBadge({ action, recordId, onAction }: Props) {
  if (action) {
    return (
      <span
        data-testid="action-badge"
        style={{ color: COLORS[action.status] ?? "#333", fontWeight: 600 }}
      >
        {action.status}
      </span>
    );
  }

  return (
    <span style={{ display: "flex", gap: "0.4rem" }}>
      <button data-testid="accept-btn" onClick={() => onAction(recordId, "accept")}>Accept</button>
      <button data-testid="skip-btn"   onClick={() => onAction(recordId, "skip")}>Skip</button>
      <button data-testid="save-btn"   onClick={() => onAction(recordId, "save")}>Save</button>
    </span>
  );
}

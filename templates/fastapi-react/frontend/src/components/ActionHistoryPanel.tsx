import type { ActionEvent } from "../types";

interface Props {
  events: ActionEvent[];
}

export function ActionHistoryPanel({ events }: Props) {
  return (
    <section data-testid="action-history-panel">
      <h2>Action History</h2>
      {events.length === 0 ? (
        <p data-testid="history-empty">No actions recorded yet.</p>
      ) : (
        <ul data-testid="action-history" style={{ fontSize: "0.85rem", paddingLeft: "1.2rem" }}>
          {events.map((event) => (
            <li key={event.id} data-testid="action-history-row">
              {event.status} · {event.action_type} · {event.record_id.slice(0, 8)}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

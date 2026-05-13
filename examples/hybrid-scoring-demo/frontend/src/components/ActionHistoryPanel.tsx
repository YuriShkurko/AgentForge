import type { ActionEvent } from "../types";

interface Props {
  events: ActionEvent[];
}

export function ActionHistoryPanel({ events }: Props) {
  return (
    <section data-testid="action-history-panel" className="panel">
      <div className="panel-head">
        <div>
          <h2>Action History</h2>
          <p className="panel-kicker">Operator decisions recorded by the local app.</p>
        </div>
        <span className="status-pill">{events.length} actions</span>
      </div>
      {events.length === 0 ? (
        <p data-testid="history-empty" className="empty-card">No actions recorded yet.</p>
      ) : (
        <ul data-testid="action-history" className="history-list">
          {events.map((event) => (
            <li key={event.id} data-testid="action-history-row" className="history-row">
              <span className={`status-pill ${event.status}`}>{event.status}</span>{" "}
              {event.action_type} · record {event.record_id.slice(0, 8)}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

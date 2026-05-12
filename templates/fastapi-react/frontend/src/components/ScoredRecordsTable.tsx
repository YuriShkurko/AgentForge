import { api } from "../api";
import type { ScoredRecord, TriageAction } from "../types";
import { ActionStatusBadge } from "./ActionStatusBadge";

interface Props {
  records: ScoredRecord[];
  onActionDone: () => void;
}

export function ScoredRecordsTable({ records, onActionDone }: Props) {
  if (records.length === 0) {
    return (
      <section className="panel data-panel">
        <div className="panel-head">
          <div>
            <h2>Scored Records</h2>
            <p className="panel-kicker">Ranked review queue with deterministic fit scoring.</p>
          </div>
        </div>
        <p data-testid="scored-empty" className="empty-card">
          No scored records yet. Ingest records, then run scoring.
        </p>
      </section>
    );
  }

  async function handleAction(recordId: string, actionType: TriageAction) {
    await api.recordAction(recordId, actionType);
    onActionDone();
  }

  return (
    <section className="panel data-panel">
      <div className="panel-head">
        <div>
          <h2>Scored Records</h2>
          <p className="panel-kicker">Highest-fit records stay at the top for quick operator review.</p>
        </div>
        <span className="status-pill">{records.length} records</span>
      </div>
      <div className="table-wrap">
        <table data-testid="scored-table">
          <thead>
            <tr>
              <th>Title</th>
              <th>Category</th>
              <th>Fit</th>
              <th>Label</th>
              <th>Recommendation</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {records.map(({ record, score, action }) => (
              <tr key={record.id} data-testid="scored-row">
                <td><strong>{record.title}</strong></td>
                <td>{record.category}</td>
                <td data-testid="fit-score"><span className="score-pill">{(score.fit * 100).toFixed(0)}%</span></td>
                <td>
                  <span className={`label-pill ${score.label}`} data-testid="score-label">
                    {score.label}
                  </span>
                </td>
                <td>{score.recommendation}</td>
                <td>
                  <ActionStatusBadge action={action} recordId={record.id} onAction={handleAction} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

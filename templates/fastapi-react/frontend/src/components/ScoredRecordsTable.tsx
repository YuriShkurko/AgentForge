import { api } from "../api";
import { customization } from "../customization";
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
            <h2>{customization.scoring.reviewQueueLabel}</h2>
            <p className="panel-kicker">Ranked review queue with deterministic {customization.scoring.criteriaLabels.join(", ").toLowerCase()} scoring.</p>
          </div>
        </div>
        <p data-testid="scored-empty" className="empty-card">
          No scored {customization.scoring.recordLabel.plural} yet. Ingest {customization.scoring.recordLabel.plural}, then run scoring.
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
          <h2>{customization.scoring.reviewQueueLabel}</h2>
          <p className="panel-kicker">Highest-fit {customization.scoring.recordLabel.plural} stay at the top for quick {customization.app.targetUserLabel} review.</p>
        </div>
        <span className="status-pill">{records.length} {customization.scoring.recordLabel.plural}</span>
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

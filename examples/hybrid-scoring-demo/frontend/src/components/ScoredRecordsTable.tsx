import { api } from "../api";
import type { ScoredRecord } from "../types";
import { ActionStatusBadge } from "./ActionStatusBadge";

interface Props {
  records: ScoredRecord[];
  onActionDone: () => void;
}

const LABEL_COLORS: Record<string, string> = {
  high:   "#2e7d32",
  medium: "#e65100",
  low:    "#b71c1c",
};

export function ScoredRecordsTable({ records, onActionDone }: Props) {
  if (records.length === 0) {
    return (
      <section>
        <h2>Scored Records</h2>
        <p data-testid="scored-empty">No scored records. Run ingest then score.</p>
      </section>
    );
  }

  async function handleAction(recordId: string, actionType: "accept" | "skip" | "save") {
    await api.recordAction(recordId, actionType);
    onActionDone();
  }

  return (
    <section>
      <h2>Scored Records</h2>
      <table data-testid="scored-table" style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.9rem" }}>
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
              <td>{record.title}</td>
              <td>{record.category}</td>
              <td data-testid="fit-score">{(score.fit * 100).toFixed(0)}%</td>
              <td>
                <span style={{ color: LABEL_COLORS[score.label], fontWeight: 600 }} data-testid="score-label">
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
    </section>
  );
}

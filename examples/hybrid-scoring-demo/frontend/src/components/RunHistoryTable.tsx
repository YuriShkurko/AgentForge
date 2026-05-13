import type { ProviderRun } from "../types";

interface Props {
  runs: ProviderRun[];
}

export function RunHistoryTable({ runs }: Props) {
  if (runs.length === 0) {
    return (
      <section className="panel data-panel">
        <div className="panel-head">
          <div>
            <h2>Run History</h2>
            <p className="panel-kicker">Provider activity for local fixture/import runs.</p>
          </div>
        </div>
        <p data-testid="runs-empty" className="empty-card">No runs yet. Use Ingest Demo Data or Import JSON Records to start.</p>
      </section>
    );
  }

  return (
    <section className="panel data-panel">
      <div className="panel-head">
        <div>
          <h2>Run History</h2>
          <p className="panel-kicker">Recent deterministic ingestion/import activity.</p>
        </div>
        <span className="status-pill">{runs.length} runs</span>
      </div>
      <div className="table-wrap">
        <table data-testid="runs-table">
          <thead>
            <tr>
              <th>Provider</th>
              <th>Status</th>
              <th>Started</th>
              <th>Raw</th>
              <th>Normalized</th>
              <th>Error</th>
            </tr>
          </thead>
          <tbody>
            {runs.map((run) => (
              <tr key={run.id} data-testid="run-row">
                <td><strong>{run.provider_name}</strong></td>
                <td data-testid="run-status"><span className={`status-pill ${run.status}`}>{run.status}</span></td>
                <td>{new Date(run.started_at).toLocaleTimeString()}</td>
                <td>{run.stats?.raw_inserted ?? "—"}</td>
                <td>{run.stats?.normalized_inserted ?? "—"}</td>
                <td>{run.error ?? ""}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

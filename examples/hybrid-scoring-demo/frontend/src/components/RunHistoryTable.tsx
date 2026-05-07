import type { ProviderRun } from "../types";

interface Props {
  runs: ProviderRun[];
}

export function RunHistoryTable({ runs }: Props) {
  if (runs.length === 0) {
    return (
      <section>
        <h2>Run History</h2>
        <p data-testid="runs-empty">No runs yet. Use the Ingest button to start.</p>
      </section>
    );
  }

  return (
    <section>
      <h2>Run History</h2>
      <table data-testid="runs-table" style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.9rem" }}>
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
              <td>{run.provider_name}</td>
              <td data-testid="run-status">{run.status}</td>
              <td>{new Date(run.started_at).toLocaleTimeString()}</td>
              <td>{run.stats?.raw_inserted ?? "—"}</td>
              <td>{run.stats?.normalized_inserted ?? "—"}</td>
              <td>{run.error ?? ""}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}

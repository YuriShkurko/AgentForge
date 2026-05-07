import { useState } from "react";
import { api } from "../api";

interface Props {
  onIngestDone: () => void;
  onScoreDone: () => void;
}

export function OpsPanel({ onIngestDone, onScoreDone }: Props) {
  const [log, setLog] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);

  async function ingest() {
    setBusy(true);
    try {
      const r = await api.ingest();
      setLog((l) => [`Ingested: ${r.raw_records_inserted} raw, ${r.normalized_inserted} normalized`, ...l]);
      onIngestDone();
    } catch (e) {
      setLog((l) => [`Ingest error: ${e}`, ...l]);
    } finally {
      setBusy(false);
    }
  }

  async function score() {
    setBusy(true);
    try {
      const r = await api.score();
      setLog((l) => [`Scored: ${r.scores_written} records`, ...l]);
      onScoreDone();
    } catch (e) {
      setLog((l) => [`Score error: ${e}`, ...l]);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section data-testid="ops-panel" style={{ marginBottom: "1.5rem" }}>
      <h2>Operations</h2>
      <div style={{ display: "flex", gap: "0.75rem", marginBottom: "0.75rem" }}>
        <button data-testid="ingest-btn" onClick={ingest} disabled={busy}>
          Ingest
        </button>
        <button data-testid="score-btn" onClick={score} disabled={busy}>
          Score
        </button>
      </div>
      {log.length > 0 && (
        <ul data-testid="activity-log" style={{ fontSize: "0.85rem", listStyle: "none", padding: 0, margin: 0 }}>
          {log.map((entry, i) => (
            <li key={i}>{entry}</li>
          ))}
        </ul>
      )}
    </section>
  );
}

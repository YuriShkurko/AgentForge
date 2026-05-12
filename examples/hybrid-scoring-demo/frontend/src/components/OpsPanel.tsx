import { useState } from "react";
import { api } from "../api";
import type { ImportRecordsResult } from "../types";

const SAMPLE_IMPORT_JSON = `[
  { "external_id": "user-1", "title": "Urgent customer request", "category": "support", "value": 92 },
  { "id": "user-2", "name": "Follow-up opportunity", "type": "sales", "priority": 68 }
]`;

interface Props {
  onIngestDone: () => void;
  onScoreDone: () => void;
  onPreviewDone: () => void;
}

export function OpsPanel({ onIngestDone, onScoreDone, onPreviewDone }: Props) {
  const [log, setLog] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);
  const [importJson, setImportJson] = useState(SAMPLE_IMPORT_JSON);
  const [lastImport, setLastImport] = useState<ImportRecordsResult | null>(null);

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

  async function importRecords() {
    setBusy(true);
    try {
      const parsed = JSON.parse(importJson);
      if (!Array.isArray(parsed)) throw new Error("Paste a JSON array of records.");
      const r = await api.importRecords(parsed);
      setLastImport(r);
      const errorSummary = r.errors.length ? ` (${r.errors.length} validation issue${r.errors.length === 1 ? "" : "s"})` : "";
      setLog((l) => [`Imported: ${r.accepted} accepted, ${r.skipped} skipped${errorSummary}`, ...l]);
      onIngestDone();
    } catch (e) {
      setLastImport(null);
      setLog((l) => [`Import error: ${e}`, ...l]);
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

  async function previewNotifications() {
    setBusy(true);
    try {
      const r = await api.createNotificationPreviews();
      setLog((l) => [`Previewed: ${r.previews_written} notifications`, ...l]);
      onPreviewDone();
    } catch (e) {
      setLog((l) => [`Preview error: ${e}`, ...l]);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section data-testid="ops-panel" style={{ marginBottom: "1.5rem" }}>
      <h2>Operations</h2>
      <div style={{ display: "flex", gap: "0.75rem", marginBottom: "0.75rem", flexWrap: "wrap" }}>
        <button data-testid="ingest-btn" onClick={ingest} disabled={busy}>
          Ingest Demo Data
        </button>
        <button data-testid="import-btn" onClick={importRecords} disabled={busy}>
          Import JSON Records
        </button>
        <button data-testid="score-btn" onClick={score} disabled={busy}>
          Score
        </button>
        <button data-testid="preview-btn" onClick={previewNotifications} disabled={busy}>
          Preview Notifications
        </button>
      </div>
      <div style={{ marginBottom: "0.5rem" }}>
        <label style={{ display: "block", fontSize: "0.85rem", fontWeight: 600, marginBottom: "0.25rem" }}>
          Your data JSON
        </label>
        <p style={{ margin: 0, color: "#4b5563", fontSize: "0.85rem" }}>
          Works without API keys. Paste an array with <code>title</code>/<code>name</code>, optional <code>category</code>/<code>type</code>, and <code>value</code>/<code>priority</code>.
        </p>
      </div>
      <textarea
        data-testid="import-json"
        value={importJson}
        onChange={(event) => setImportJson(event.target.value)}
        rows={6}
        style={{ width: "100%", boxSizing: "border-box", fontFamily: "monospace", marginBottom: "0.5rem" }}
      />
      <button type="button" onClick={() => setImportJson(SAMPLE_IMPORT_JSON)} disabled={busy} style={{ marginBottom: "0.75rem" }}>
        Reset Sample JSON
      </button>
      {lastImport && (
        <div data-testid="import-result" style={{ border: "1px solid #d1d5db", borderRadius: 8, padding: "0.75rem", marginBottom: "0.75rem", background: "#f9fafb" }}>
          <strong>Import result:</strong> {lastImport.accepted} accepted, {lastImport.skipped} skipped.
          {lastImport.errors.length > 0 && (
            <ul style={{ margin: "0.5rem 0 0", paddingLeft: "1.25rem" }}>
              {lastImport.errors.slice(0, 5).map((error) => (
                <li key={`${error.index}-${error.external_id ?? "none"}`}>
                  Row {error.index + 1}{error.external_id ? ` (${error.external_id})` : ""}: {error.error}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
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

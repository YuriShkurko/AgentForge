import { useCallback, useEffect, useState } from "react";
import { api } from "./api";
import { OpsPanel } from "./components/OpsPanel";
import { RunHistoryTable } from "./components/RunHistoryTable";
import { ScoredRecordsTable } from "./components/ScoredRecordsTable";
import type { ProviderRun, ScoredRecord } from "./types";

export default function App() {
  const [runs, setRuns] = useState<ProviderRun[]>([]);
  const [scored, setScored] = useState<ScoredRecord[]>([]);

  const refreshRuns = useCallback(async () => {
    const data = await api.getRuns();
    setRuns(data.runs);
  }, []);

  const refreshScored = useCallback(async () => {
    const data = await api.getScoredRecords();
    setScored(data.records);
  }, []);

  useEffect(() => {
    refreshRuns();
    refreshScored();
  }, [refreshRuns, refreshScored]);

  return (
    <main style={{ maxWidth: 900, margin: "0 auto", padding: "1.5rem", fontFamily: "system-ui, sans-serif" }}>
      <h1>Hybrid Scoring Demo</h1>
      <OpsPanel onIngestDone={refreshRuns} onScoreDone={refreshScored} />
      <RunHistoryTable runs={runs} />
      <hr style={{ margin: "1.5rem 0" }} />
      <ScoredRecordsTable records={scored} onActionDone={refreshScored} />
    </main>
  );
}

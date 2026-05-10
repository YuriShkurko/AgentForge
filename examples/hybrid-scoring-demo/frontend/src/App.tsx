import { useCallback, useEffect, useState } from "react";
import { api } from "./api";
import { ActionHistoryPanel } from "./components/ActionHistoryPanel";
import { AgentChatPanel } from "./components/AgentChatPanel";
import { NotificationPreviewPanel } from "./components/NotificationPreviewPanel";
import { OpsPanel } from "./components/OpsPanel";
import { RunHistoryTable } from "./components/RunHistoryTable";
import { ScoredRecordsTable } from "./components/ScoredRecordsTable";
import type { ActionEvent, NotificationPreview, ProviderRun, ScoredRecord } from "./types";

export default function App() {
  const [runs, setRuns] = useState<ProviderRun[]>([]);
  const [scored, setScored] = useState<ScoredRecord[]>([]);
  const [previews, setPreviews] = useState<NotificationPreview[]>([]);
  const [history, setHistory] = useState<ActionEvent[]>([]);

  const refreshRuns = useCallback(async () => {
    const data = await api.getRuns();
    setRuns(data.runs);
  }, []);

  const refreshScored = useCallback(async () => {
    const data = await api.getScoredRecords();
    setScored(data.records);
  }, []);

  const refreshPreviews = useCallback(async () => {
    const data = await api.getNotificationPreviews();
    setPreviews(data.previews);
  }, []);

  const refreshHistory = useCallback(async () => {
    const data = await api.getActionHistory();
    setHistory(data.events);
  }, []);

  const refreshAfterAction = useCallback(async () => {
    await Promise.all([refreshScored(), refreshPreviews(), refreshHistory()]);
  }, [refreshHistory, refreshPreviews, refreshScored]);

  const refreshAfterAgent = useCallback(async () => {
    await Promise.all([refreshRuns(), refreshScored(), refreshPreviews(), refreshHistory()]);
  }, [refreshHistory, refreshPreviews, refreshRuns, refreshScored]);

  useEffect(() => {
    refreshRuns();
    refreshScored();
    refreshPreviews();
    refreshHistory();
  }, [refreshHistory, refreshPreviews, refreshRuns, refreshScored]);

  return (
    <main style={{ maxWidth: 900, margin: "0 auto", padding: "1.5rem", fontFamily: "system-ui, sans-serif" }}>
      <h1>Hybrid Scoring Demo</h1>
      <AgentChatPanel onAgentDone={refreshAfterAgent} />
      <hr style={{ margin: "1.5rem 0" }} />
      <OpsPanel onIngestDone={refreshRuns} onScoreDone={refreshScored} onPreviewDone={refreshPreviews} />
      <RunHistoryTable runs={runs} />
      <hr style={{ margin: "1.5rem 0" }} />
      <ScoredRecordsTable records={scored} onActionDone={refreshAfterAction} />
      <hr style={{ margin: "1.5rem 0" }} />
      <NotificationPreviewPanel previews={previews} onActionDone={refreshAfterAction} />
      <hr style={{ margin: "1.5rem 0" }} />
      <ActionHistoryPanel events={history} />
    </main>
  );
}

import { useCallback, useEffect, useState } from "react";
import { api } from "./api";
import { ActionHistoryPanel } from "./components/ActionHistoryPanel";
import { AgentChatPanel } from "./components/AgentChatPanel";
import { NotificationPreviewPanel } from "./components/NotificationPreviewPanel";
import { OpsPanel } from "./components/OpsPanel";
import { RunHistoryTable } from "./components/RunHistoryTable";
import { ScoredRecordsTable } from "./components/ScoredRecordsTable";
import { WorkspacePanel } from "./components/WorkspacePanel";
import type {
  ActionEvent,
  NotificationPreview,
  ProviderRun,
  ScoredRecord,
  WorkspaceWidget,
} from "./types";

export default function App() {
  const [runs, setRuns] = useState<ProviderRun[]>([]);
  const [scored, setScored] = useState<ScoredRecord[]>([]);
  const [previews, setPreviews] = useState<NotificationPreview[]>([]);
  const [history, setHistory] = useState<ActionEvent[]>([]);
  const [widgets, setWidgets] = useState<WorkspaceWidget[]>([]);
  const [workspaceLoading, setWorkspaceLoading] = useState(false);
  const [workspaceError, setWorkspaceError] = useState<string | null>(null);

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

  const refreshWidgets = useCallback(async () => {
    setWorkspaceLoading(true);
    setWorkspaceError(null);
    try {
      const data = await api.getWorkspaceWidgets();
      setWidgets(data.widgets);
    } catch (error) {
      setWorkspaceError(String(error));
    } finally {
      setWorkspaceLoading(false);
    }
  }, []);

  const refreshAfterAction = useCallback(async () => {
    await Promise.all([refreshScored(), refreshPreviews(), refreshHistory()]);
  }, [refreshHistory, refreshPreviews, refreshScored]);

  const refreshAfterAgent = useCallback(async () => {
    await Promise.all([
      refreshRuns(),
      refreshScored(),
      refreshPreviews(),
      refreshHistory(),
      refreshWidgets(),
    ]);
  }, [
    refreshHistory,
    refreshPreviews,
    refreshRuns,
    refreshScored,
    refreshWidgets,
  ]);

  useEffect(() => {
    refreshRuns();
    refreshScored();
    refreshPreviews();
    refreshHistory();
    refreshWidgets();
  }, [
    refreshHistory,
    refreshPreviews,
    refreshRuns,
    refreshScored,
    refreshWidgets,
  ]);

  return (
    <main
      style={{
        maxWidth: 980,
        margin: "0 auto",
        padding: "1.5rem",
        fontFamily: "system-ui, sans-serif",
        color: "#1f2937",
      }}
    >
      <h1 style={{ marginBottom: "1rem" }}>Hybrid Scoring Demo</h1>
      <AgentChatPanel onAgentDone={refreshAfterAgent} />
      <WorkspacePanel
        widgets={widgets}
        loading={workspaceLoading}
        error={workspaceError}
        onChanged={refreshWidgets}
      />
      <hr style={{ margin: "1.5rem 0" }} />
      <OpsPanel
        onIngestDone={refreshRuns}
        onScoreDone={refreshScored}
        onPreviewDone={refreshPreviews}
      />
      <RunHistoryTable runs={runs} />
      <hr style={{ margin: "1.5rem 0" }} />
      <ScoredRecordsTable records={scored} onActionDone={refreshAfterAction} />
      <hr style={{ margin: "1.5rem 0" }} />
      <NotificationPreviewPanel
        previews={previews}
        onActionDone={refreshAfterAction}
      />
      <hr style={{ margin: "1.5rem 0" }} />
      <ActionHistoryPanel events={history} />
    </main>
  );
}

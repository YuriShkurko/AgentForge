import { useCallback, useEffect, useMemo, useState } from "react";
import { api } from "./api";
import { ActionHistoryPanel } from "./components/ActionHistoryPanel";
import { AgentChatPanel } from "./components/AgentChatPanel";
import { NotificationPreviewPanel } from "./components/NotificationPreviewPanel";
import { OpsPanel } from "./components/OpsPanel";
import { RunHistoryTable } from "./components/RunHistoryTable";
import { ScoredRecordsTable } from "./components/ScoredRecordsTable";
import { WorkspacePanel } from "./components/WorkspacePanel";
import { customization } from "./customization";
import type {
  ActionEvent,
  NotificationPreview,
  ProviderRun,
  ScoredRecord,
  WorkspaceWidget,
} from "./types";
import "./styles.css";

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

  const summary = useMemo(() => {
    const activeRun = runs[0];
    const topFit = scored[0] ? `${(scored[0].score.fit * 100).toFixed(0)}%` : "-";
    const acceptedActions = history.filter((event) => event.status === "accepted").length;
    return {
      activeRun: activeRun?.status ?? "idle",
      scoredCount: scored.length,
      topFit,
      previewCount: previews.length,
      acceptedActions,
      widgetCount: widgets.length,
    };
  }, [history, previews.length, runs, scored, widgets.length]);

  return (
    <main className="app-shell">
      <header className="app-hero">
        <div className="hero-copy">
          <p className="eyebrow">AgentForge generated app</p>
          <h1>{customization.app.name}</h1>
          <p>{customization.app.subtitle}</p>
        </div>
        <aside className="mode-card" aria-label="Demo mode">
          <span className="mode-dot" />
          <strong>Local safe mode</strong>
          <small>No API keys, live delivery, or external LLM required.</small>
        </aside>
      </header>

      <section className="metric-grid" aria-label="Workflow summary">
        <MetricCard label="Run state" value={summary.activeRun} />
        <MetricCard label={`Scored ${customization.scoring.recordLabel.plural}`} value={summary.scoredCount} />
        <MetricCard label="Top fit" value={summary.topFit} />
        <MetricCard label="Previews" value={summary.previewCount} />
        <MetricCard label="Accepted" value={summary.acceptedActions} />
        <MetricCard label="Widgets" value={summary.widgetCount} />
      </section>

      <div className="workspace-grid">
        <AgentChatPanel onAgentDone={refreshAfterAgent} />
        <WorkspacePanel
          widgets={widgets}
          loading={workspaceLoading}
          error={workspaceError}
          onChanged={refreshWidgets}
        />
      </div>

      <div className="review-grid">
        <OpsPanel
          onIngestDone={refreshRuns}
          onScoreDone={refreshScored}
          onPreviewDone={refreshPreviews}
        />
        <RunHistoryTable runs={runs} />
      </div>

      <ScoredRecordsTable records={scored} onActionDone={refreshAfterAction} />
      <NotificationPreviewPanel
        previews={previews}
        onActionDone={refreshAfterAction}
      />
      <ActionHistoryPanel events={history} />
    </main>
  );
}

function MetricCard({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="metric-card">
      <span>{value}</span>
      <small>{label}</small>
    </div>
  );
}

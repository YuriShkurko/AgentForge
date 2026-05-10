import type { WorkspaceWidget } from "../types";

interface Props {
  widget: WorkspaceWidget;
}

type JsonObject = Record<string, unknown>;

export function WidgetRenderer({ widget }: Props) {
  if (!hasRenderableData(widget.data)) {
    return <EmptyWidget text="No renderable data was saved for this widget." />;
  }

  switch (widget.widget_type) {
    case "summary_card":
    case "score_card":
      return <SummaryCard data={widget.data} />;
    case "ranking_list":
      return <RankingList data={widget.data} />;
    case "score_table":
      return <ScoreTable data={widget.data} />;
    case "run_history_list":
      return <RunHistoryList data={widget.data} />;
    case "notification_preview_card":
      return <NotificationPreviewCard data={widget.data} />;
    case "action_history_list":
      return <ActionHistoryList data={widget.data} />;
    default:
      return (
        <EmptyWidget
          testId="widget-unknown"
          text={`Unsupported widget type: ${labelize(widget.widget_type)}`}
        />
      );
  }
}

function SummaryCard({ data }: { data: unknown }) {
  const object = asObject(data);
  const entries = Object.entries(object)
    .filter(([, value]) => value !== undefined)
    .slice(0, 6);
  if (entries.length === 0)
    return <EmptyWidget text="No summary fields available." />;

  return (
    <dl data-testid="widget-summary" style={summaryGridStyle}>
      {entries.map(([key, value]) => (
        <FragmentRow
          key={key}
          label={labelize(key)}
          value={formatValue(value)}
        />
      ))}
    </dl>
  );
}

function RankingList({ data }: { data: unknown }) {
  const records = getArray(data, "records");
  if (records.length === 0)
    return <EmptyWidget text="No ranked records were returned." />;
  return (
    <ol
      data-testid="widget-ranking-list"
      style={{
        display: "grid",
        gap: "0.45rem",
        margin: 0,
        padding: 0,
        listStyle: "none",
      }}
    >
      {records.slice(0, 5).map((item, index) => {
        const row = asObject(item);
        const fit = getScore(row);
        return (
          <li
            key={`${String(row.id ?? row.title ?? index)}-${index}`}
            style={rowCardStyle}
          >
            <span style={rankStyle}>{index + 1}</span>
            <span style={{ minWidth: 0, flex: 1 }}>
              <strong style={{ display: "block", color: "#111827" }}>
                {String(row.title ?? "Untitled")}
              </strong>
              <span style={mutedTextStyle}>
                {String(row.category ?? row.label ?? "record")}
              </span>
            </span>
            {typeof fit === "number" && <ScorePill value={fit} />}
          </li>
        );
      })}
    </ol>
  );
}

function ScoreTable({ data }: { data: unknown }) {
  const records = getArray(data, "records");
  if (records.length === 0)
    return <EmptyWidget text="No score rows were returned." />;
  return (
    <div style={{ overflowX: "auto" }}>
      <table
        data-testid="widget-score-table"
        style={{
          width: "100%",
          borderCollapse: "collapse",
          fontSize: "0.85rem",
        }}
      >
        <thead>
          <tr>
            <th style={tableHeaderStyle}>Title</th>
            <th style={tableHeaderStyle}>Fit</th>
            <th style={tableHeaderStyle}>Label</th>
          </tr>
        </thead>
        <tbody>
          {records.slice(0, 5).map((item, index) => {
            const row = asObject(item);
            const fit = getScore(row);
            return (
              <tr key={`${String(row.id ?? row.title ?? index)}-${index}`}>
                <td style={tableCellStyle}>
                  {String(row.title ?? "Untitled")}
                </td>
                <td style={tableCellStyle}>
                  {typeof fit === "number" ? <ScorePill value={fit} /> : "-"}
                </td>
                <td style={tableCellStyle}>{String(row.label ?? "-")}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function RunHistoryList({ data }: { data: unknown }) {
  const runs = getArray(data, "runs");
  if (runs.length === 0) return <EmptyWidget text="No runs were returned." />;
  return (
    <ul data-testid="widget-run-history" style={listStyle}>
      {runs.slice(0, 5).map((item, index) => {
        const run = asObject(item);
        return (
          <li key={`${String(run.id ?? index)}-${index}`} style={rowCardStyle}>
            <span style={{ flex: 1 }}>
              <strong>{String(run.provider_name ?? "Provider")}</strong>
              <span style={mutedTextStyle}>Run {shortId(run.id)}</span>
            </span>
            <StatusPill value={String(run.status ?? "unknown")} />
          </li>
        );
      })}
    </ul>
  );
}

function NotificationPreviewCard({ data }: { data: unknown }) {
  const object = asObject(data);
  return (
    <div data-testid="widget-notification-preview" style={noticeStyle}>
      <strong>Preview-only notification result</strong>
      <p style={{ margin: "0.25rem 0 0", color: "#475569" }}>
        Stored previews:{" "}
        <strong>{formatValue(object.previews_written ?? 0)}</strong>
      </p>
    </div>
  );
}

function ActionHistoryList({ data }: { data: unknown }) {
  const events = getArray(data, "events");
  if (events.length === 0)
    return <EmptyWidget text="No action history was returned." />;
  return (
    <ul data-testid="widget-action-history" style={listStyle}>
      {events.slice(0, 5).map((item, index) => {
        const event = asObject(item);
        return (
          <li
            key={`${String(event.id ?? index)}-${index}`}
            style={rowCardStyle}
          >
            <span style={{ flex: 1 }}>
              <strong>{labelize(String(event.action_type ?? "action"))}</strong>
              <span style={mutedTextStyle}>
                {formatTimestamp(event.created_at)}
              </span>
            </span>
            <StatusPill value={String(event.status ?? "unknown")} />
          </li>
        );
      })}
    </ul>
  );
}

function FragmentRow({ label, value }: { label: string; value: string }) {
  return (
    <>
      <dt style={{ fontWeight: 600 }}>{label}</dt>
      <dd
        style={{
          margin: 0,
          minWidth: 0,
          overflowWrap: "anywhere",
          color: "#334155",
        }}
      >
        {value}
      </dd>
    </>
  );
}

function EmptyWidget({
  text,
  testId = "widget-empty",
}: {
  text: string;
  testId?: string;
}) {
  return (
    <p
      data-testid={testId}
      style={{ margin: 0, color: "#64748b", fontSize: "0.88rem" }}
    >
      {text}
    </p>
  );
}

function ScorePill({ value }: { value: number }) {
  const percent = value > 1 ? value : value * 100;
  const color =
    percent >= 80 ? "#166534" : percent >= 60 ? "#92400e" : "#991b1b";
  const background =
    percent >= 80 ? "#ecfdf3" : percent >= 60 ? "#fffbeb" : "#fff1f2";
  return (
    <span
      style={{
        borderRadius: 999,
        padding: "0.12rem 0.45rem",
        fontWeight: 700,
        color,
        background,
      }}
    >
      {percent.toFixed(0)}%
    </span>
  );
}

function StatusPill({ value }: { value: string }) {
  return (
    <span
      style={{
        border: "1px solid #e2e8f0",
        borderRadius: 999,
        padding: "0.12rem 0.45rem",
        color: "#334155",
        background: "#f8fafc",
        fontSize: "0.78rem",
        fontWeight: 700,
      }}
    >
      {labelize(value)}
    </span>
  );
}

function hasRenderableData(data: unknown): boolean {
  if (Array.isArray(data)) return data.length > 0;
  if (data && typeof data === "object") return Object.keys(data).length > 0;
  return data !== null && data !== undefined && data !== "";
}

function asObject(value: unknown): JsonObject {
  return value && typeof value === "object" && !Array.isArray(value)
    ? (value as JsonObject)
    : {};
}

function getArray(value: unknown, key: string): unknown[] {
  const object = asObject(value);
  return Array.isArray(object[key]) ? (object[key] as unknown[]) : [];
}

function getScore(row: JsonObject): number | undefined {
  if (typeof row.fit === "number") return row.fit;
  if (typeof row.score === "number") return row.score;
  return undefined;
}

function formatValue(value: unknown): string {
  if (value === null || value === undefined) return "-";
  if (
    typeof value === "string" ||
    typeof value === "number" ||
    typeof value === "boolean"
  )
    return String(value);
  return JSON.stringify(value);
}

function formatTimestamp(value: unknown): string {
  if (typeof value !== "string") return "No timestamp";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString();
}

function shortId(value: unknown): string {
  return typeof value === "string" && value.length > 8
    ? value.slice(0, 8)
    : String(value ?? "-");
}

function labelize(value: string): string {
  return value
    .replace(/_/g, " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

const summaryGridStyle = {
  display: "grid",
  gridTemplateColumns: "minmax(7rem, max-content) minmax(0, 1fr)",
  gap: "0.35rem 0.75rem",
  margin: 0,
  fontSize: "0.88rem",
};

const rowCardStyle = {
  display: "flex",
  gap: "0.65rem",
  alignItems: "center",
  border: "1px solid #edf2f7",
  borderRadius: 6,
  padding: "0.5rem 0.6rem",
  background: "#fbfdff",
};

const rankStyle = {
  display: "inline-flex",
  alignItems: "center",
  justifyContent: "center",
  width: "1.45rem",
  height: "1.45rem",
  borderRadius: 999,
  background: "#e8eef7",
  color: "#334155",
  fontSize: "0.78rem",
  fontWeight: 700,
  flex: "0 0 auto",
};

const mutedTextStyle = {
  display: "block",
  color: "#64748b",
  fontSize: "0.78rem",
  marginTop: "0.1rem",
};

const listStyle = {
  display: "grid",
  gap: "0.45rem",
  margin: 0,
  padding: 0,
  listStyle: "none",
};

const tableHeaderStyle = {
  borderBottom: "1px solid #e2e8f0",
  color: "#475569",
  fontSize: "0.76rem",
  padding: "0.35rem 0.45rem",
  textAlign: "left" as const,
};

const tableCellStyle = {
  borderBottom: "1px solid #f1f5f9",
  padding: "0.45rem",
  verticalAlign: "top" as const,
};

const noticeStyle = {
  border: "1px solid #dbe3ee",
  borderRadius: 6,
  padding: "0.65rem",
  background: "#fbfdff",
};

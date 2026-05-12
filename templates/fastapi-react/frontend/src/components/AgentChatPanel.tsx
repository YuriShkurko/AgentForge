import { FormEvent, useEffect, useState } from "react";
import { api } from "../api";
import type { AgentMessage, AgentStreamEvent, AgentToolEvent } from "../types";

const STORAGE_KEY = "hybrid-scoring-demo-agent-conversation";

interface Props {
  onAgentDone: () => void;
}

export function AgentChatPanel({ onAgentDone }: Props) {
  const [conversationId, setConversationId] = useState<string | undefined>(
    () => {
      return window.localStorage.getItem(STORAGE_KEY) ?? undefined;
    },
  );
  const [messages, setMessages] = useState<AgentMessage[]>([]);
  const [toolEvents, setToolEvents] = useState<AgentToolEvent[]>([]);
  const [input, setInput] = useState("score the records");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!conversationId) return;
    api
      .getAgentConversation(conversationId)
      .then((data) => setMessages(data.messages))
      .catch(() => {
        window.localStorage.removeItem(STORAGE_KEY);
        setConversationId(undefined);
      });
  }, [conversationId]);

  async function send(event: FormEvent) {
    event.preventDefault();
    const message = input.trim();
    if (!message) {
      setError("Message must not be empty.");
      return;
    }

    setBusy(true);
    setError(null);
    setToolEvents([]);
    const now = new Date().toISOString();
    const assistantId = `pending-assistant-${Date.now()}`;
    setMessages((current) => [
      ...current,
      {
        id: `pending-user-${Date.now()}`,
        role: "user",
        content: message,
        metadata: null,
        created_at: now,
      },
      {
        id: assistantId,
        role: "assistant",
        content: "",
        metadata: null,
        created_at: now,
      },
    ]);
    try {
      await api.streamAgentChat(message, conversationId, (streamEvent) => {
        handleStreamEvent(streamEvent, assistantId);
      });
    } catch (e) {
      try {
        const response = await api.agentChat(message, conversationId);
        storeConversation(response.conversation_id);
        setMessages(response.messages);
        setToolEvents(response.tool_events);
        setInput("");
        onAgentDone();
      } catch (fallbackError) {
        setError(String(fallbackError || e));
      }
    } finally {
      setBusy(false);
    }
  }

  function storeConversation(nextConversationId: string) {
    setConversationId(nextConversationId);
    window.localStorage.setItem(STORAGE_KEY, nextConversationId);
  }

  function handleStreamEvent(
    streamEvent: AgentStreamEvent,
    assistantId: string,
  ) {
    if (
      streamEvent.event === "message_start" &&
      typeof streamEvent.data.conversation_id === "string"
    ) {
      storeConversation(streamEvent.data.conversation_id);
      return;
    }
    if (streamEvent.event === "tool_call") {
      setToolEvents((current) => [
        ...current,
        {
          tool_name: String(streamEvent.data.tool_name),
          arguments: (streamEvent.data.arguments ?? {}) as Record<
            string,
            unknown
          >,
          ok: true,
          result: null,
          error: null,
          status: "running",
        },
      ]);
      return;
    }
    if (streamEvent.event === "tool_result") {
      const toolEvent = streamEvent.data as unknown as AgentToolEvent;
      setToolEvents((current) => [
        ...current.filter(
          (event) =>
            event.status !== "running" ||
            event.tool_name !== toolEvent.tool_name,
        ),
        { ...toolEvent, status: toolEvent.ok ? "succeeded" : "failed" },
      ]);
      return;
    }
    if (streamEvent.event === "text_delta") {
      setMessages((current) =>
        current.map((item) =>
          item.id === assistantId
            ? {
                ...item,
                content: `${item.content}${String(streamEvent.data.text ?? "")}`,
              }
            : item,
        ),
      );
      return;
    }
    if (streamEvent.event === "error") {
      setError(String(streamEvent.data.error ?? "Agent stream failed."));
      return;
    }
    if (streamEvent.event === "done") {
      if (streamEvent.data.ok === false) return;
      if (typeof streamEvent.data.conversation_id === "string") {
        storeConversation(streamEvent.data.conversation_id);
      }
      if (Array.isArray(streamEvent.data.messages)) {
        setMessages(streamEvent.data.messages as AgentMessage[]);
      }
      if (Array.isArray(streamEvent.data.tool_events)) {
        setToolEvents(streamEvent.data.tool_events as AgentToolEvent[]);
      }
      setInput("");
      onAgentDone();
    }
  }

  return (
    <section data-testid="agent-chat-panel" className="panel agent-panel">
      <div className="panel-head">
        <div>
          <p className="eyebrow">Scripted agent</p>
          <h2>Agent Runtime</h2>
          <p className="panel-kicker">
            Try: "ingest records", "score the records", "show best records", or
            "create notification preview".
          </p>
        </div>
        <span className="status-pill">Local tools</span>
      </div>
      <div data-testid="agent-messages" className="messages">
        {messages.length === 0 ? (
          <p data-testid="agent-empty" className="empty-card">
            No conversation yet. Ask the agent to run or pin part of the review
            workflow.
          </p>
        ) : (
          messages
            .filter((message) => message.role !== "tool")
            .map((message) => (
              <div
                key={message.id}
                data-testid={`agent-message-${message.role}`}
                className="message-bubble"
              >
                <strong>{message.role}:</strong> {message.content}
              </div>
            ))
        )}
      </div>
      {toolEvents.length > 0 && (
        <ul data-testid="agent-tool-activity" className="tool-list">
          {toolEvents.map((event, index) => (
            <li
              key={`${event.tool_name}-${index}`}
              data-testid="agent-tool-event"
              className={`tool-event ${event.ok === false ? "failed" : ""}`}
            >
              <strong>
                {event.status === "running"
                  ? "running"
                  : event.ok
                    ? "ran"
                    : "failed"}{" "}
                {event.tool_name}
              </strong>
              <small>{describeToolEvent(event)}</small>
            </li>
          ))}
        </ul>
      )}
      <form onSubmit={send} className="agent-form">
        <input
          data-testid="agent-input"
          value={input}
          onChange={(event) => setInput(event.target.value)}
          disabled={busy}
        />
        <button data-testid="agent-send-btn" disabled={busy}>
          {busy ? "Sending..." : "Send"}
        </button>
      </form>
      {error && (
        <p data-testid="agent-error" className="error-text">
          {error}
        </p>
      )}
    </section>
  );
}

function describeToolEvent(event: AgentToolEvent): string {
  if (event.status === "running") {
    return event.tool_name === "pin_widget"
      ? "Saving a workspace widget..."
      : "Tool is running.";
  }
  if (!event.ok) {
    return event.tool_name === "pin_widget"
      ? `Widget was not persisted: ${event.error ?? "tool failed"}`
      : (event.error ?? "Tool failed.");
  }
  if (event.tool_name === "pin_widget") {
    return "Workspace widget persisted. The workspace refreshes when the turn completes.";
  }
  return "Tool completed.";
}

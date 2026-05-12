import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Protocol


@dataclass
class AgentToolCall:
    name: str
    arguments: dict[str, Any]


@dataclass
class AgentPlan:
    tool_calls: list[AgentToolCall]
    final_text: str


class AgentProvider:
    name = "base"

    def plan(self, message: str) -> AgentPlan:
        raise NotImplementedError


class AgentProviderConfigurationError(RuntimeError):
    pass


class OpenAIChatClient(Protocol):
    def complete(self, message: str) -> str:
        ...


class ScriptedAgentProvider(AgentProvider):
    """Deterministic provider used by local development and tests."""

    name = "scripted"

    def plan(self, message: str) -> AgentPlan:
        text = message.lower()

        if "unknown tool" in text or "invalid tool" in text:
            return AgentPlan(
                tool_calls=[AgentToolCall("unknown_tool", {})],
                final_text="I could not run the requested tool.",
            )
        if "invalid args" in text or "bad args" in text:
            return AgentPlan(
                tool_calls=[AgentToolCall("score_records", {"rescore": "yes"})],
                final_text="I could not run the tool with those arguments.",
            )
        if "invalid widget" in text or "bad widget" in text:
            return AgentPlan(
                tool_calls=[
                    AgentToolCall("get_scored_records", {"limit": 3}),
                    AgentToolCall(
                        "pin_widget",
                        {
                            "widget_type": "run_history_list",
                            "title": "Invalid scored records widget",
                            "source_tool": "get_scored_records",
                            "__from_tool": "get_scored_records",
                        },
                    ),
                ],
                final_text="I could not pin that widget.",
            )
        if "pin" in text and ("scored records" in text or "best records" in text or "records" in text):
            return AgentPlan(
                tool_calls=[
                    AgentToolCall("get_scored_records", {"limit": 3}),
                    AgentToolCall(
                        "pin_widget",
                        {
                            "widget_type": "ranking_list",
                            "title": "Top scored records",
                            "source_tool": "get_scored_records",
                            "__from_tool": "get_scored_records",
                        },
                    ),
                ],
                final_text="I pinned the scored records to the workspace.",
            )
        if "pin" in text and ("preview" in text or "notification" in text):
            return AgentPlan(
                tool_calls=[
                    AgentToolCall("create_notification_preview", {}),
                    AgentToolCall(
                        "pin_widget",
                        {
                            "widget_type": "notification_preview_card",
                            "title": "Notification preview",
                            "source_tool": "create_notification_preview",
                            "__from_tool": "create_notification_preview",
                        },
                    ),
                ],
                final_text="I created notification previews and pinned the result to the workspace.",
            )
        if "pin" in text and "history" in text:
            return AgentPlan(
                tool_calls=[
                    AgentToolCall("list_action_history", {"limit": 5}),
                    AgentToolCall(
                        "pin_widget",
                        {
                            "widget_type": "action_history_list",
                            "title": "Action history",
                            "source_tool": "list_action_history",
                            "__from_tool": "list_action_history",
                        },
                    ),
                ],
                final_text="I pinned the action history to the workspace.",
            )
        if "ingest" in text:
            return AgentPlan(
                tool_calls=[AgentToolCall("run_ingest", {})],
                final_text="I ingested fixture records through the provider interface.",
            )
        if "score" in text:
            return AgentPlan(
                tool_calls=[AgentToolCall("score_records", {"rescore": False})],
                final_text="I scored the records using the deterministic scoring adapter.",
            )
        if "best" in text or "show records" in text or "scored records" in text:
            return AgentPlan(
                tool_calls=[AgentToolCall("get_scored_records", {"limit": 3})],
                final_text="Here are the highest-scored records from the latest run.",
            )
        if "preview" in text or "notification" in text:
            return AgentPlan(
                tool_calls=[AgentToolCall("create_notification_preview", {})],
                final_text="I created preview-only notification payloads for scored records.",
            )
        if "history" in text:
            return AgentPlan(
                tool_calls=[AgentToolCall("list_action_history", {"limit": 5})],
                final_text="Here is the latest triage action history.",
            )

        return AgentPlan(
            tool_calls=[],
            final_text=(
                "I can help ingest fixture records, score records, show the best records, "
                "create notification previews, or show action history."
            ),
        )


class OpenAICompatibleProvider(AgentProvider):
    """Optional live provider for chat-only responses. Scripted remains the default."""

    name = "openai"

    def __init__(self, client: OpenAIChatClient | None = None):
        self.client = client or OpenAIResponsesClient.from_env()

    def plan(self, message: str) -> AgentPlan:
        return AgentPlan(tool_calls=[], final_text=self.client.complete(message))


class OpenAIResponsesClient:
    def __init__(self, api_key: str, model: str = "gpt-4o-mini", timeout: float = 30.0):
        self.api_key = api_key
        self.model = model
        self.timeout = timeout

    @classmethod
    def from_env(cls) -> "OpenAIResponsesClient":
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        if not api_key:
            raise AgentProviderConfigurationError(
                "AGENT_PROVIDER=openai requires OPENAI_API_KEY. Set OPENAI_API_KEY or use AGENT_PROVIDER=scripted."
            )
        return cls(
            api_key=api_key,
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip() or "gpt-4o-mini",
        )

    def complete(self, message: str) -> str:
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are the optional live agent for a local AgentForge demo app. "
                        "Be concise. Explain that scoring remains deterministic and local. "
                        "Do not claim to have called tools or changed records."
                    ),
                },
                {"role": "user", "content": message},
            ],
            "temperature": 0.2,
        }
        request = urllib.request.Request(
            "https://api.openai.com/v1/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                data = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"OpenAI request failed with status {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"OpenAI request failed: {exc.reason}") from exc

        try:
            return str(data["choices"][0]["message"]["content"]).strip()
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError("OpenAI response did not include assistant content.") from exc


def get_agent_provider() -> AgentProvider:
    provider = os.getenv("AGENT_PROVIDER", "scripted").strip().lower()
    if provider in {"", "scripted", "local"}:
        return ScriptedAgentProvider()
    if provider == "openai":
        return OpenAICompatibleProvider()
    raise AgentProviderConfigurationError(
        f"Unsupported AGENT_PROVIDER={provider!r}. Use 'scripted' or 'openai'."
    )

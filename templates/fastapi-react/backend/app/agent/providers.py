from dataclasses import dataclass
from typing import Any


@dataclass
class AgentToolCall:
    name: str
    arguments: dict[str, Any]


@dataclass
class AgentPlan:
    tool_calls: list[AgentToolCall]
    final_text: str


class AgentProvider:
    def plan(self, message: str) -> AgentPlan:
        raise NotImplementedError


class ScriptedAgentProvider(AgentProvider):
    """Deterministic provider used by local development and tests."""

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
    """Placeholder for future live providers. Not used by tests."""

    def plan(self, message: str) -> AgentPlan:
        raise RuntimeError("OpenAI-compatible provider is not configured in this generated app.")

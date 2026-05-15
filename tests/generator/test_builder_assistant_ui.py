"""Phase 2 UI smoke tests for the Builder Assistant chat panel.

These tests treat the builder/ files as static assets: they only confirm that
the markup, styles, and script reference the assistant endpoints. They do not
spin up a browser. Server-side regressions are covered by
``test_builder_assistant.py``.
"""
from pathlib import Path

BUILDER_DIR = Path(__file__).resolve().parents[2] / "builder"


def _read(name: str) -> str:
    return (BUILDER_DIR / name).read_text(encoding="utf-8")


def test_index_html_contains_assistant_panel_with_labelled_controls():
    html = _read("index.html")

    assert 'id="assistant-panel"' in html
    assert 'aria-labelledby="assistant-heading"' in html
    assert 'id="assistant-heading"' in html
    assert 'id="assistant-log"' in html
    assert 'role="log"' in html
    assert 'aria-live="polite"' in html
    assert 'id="assistant-questions"' in html
    assert 'id="assistant-proposal"' in html
    assert 'id="assistant-form"' in html
    assert 'id="assistant-input"' in html
    assert 'for="assistant-input"' in html
    assert 'id="assistant-send"' in html
    assert 'id="assistant-reset"' in html


def test_index_html_keeps_existing_wizard_steps():
    html = _read("index.html")

    for step in ("start", "new-app", "review", "generate", "repo"):
        assert f'data-step="{step}"' in html
    assert 'id="planner-idea"' in html
    assert 'id="draft-blueprint"' in html
    assert 'id="yaml-preview"' in html


def test_assistant_panel_is_inside_describe_step():
    html = _read("index.html")
    describe_start = html.index('id="new-app-flow"')
    describe_end = html.index('id="review-flow"')
    describe_block = html[describe_start:describe_end]
    assert 'id="assistant-panel"' in describe_block, (
        "assistant panel must live inside the Describe wizard step so static "
        "mode and the existing planner flow stay intact"
    )


def test_app_mjs_calls_assistant_endpoints_and_handles_fallback():
    script = _read("app.mjs")

    assert "/api/planner/assistant/${action}" in script.replace("'", '"') or "assistant/${action}" in script
    assert '"start"' in script or "'start'" in script
    assert '"message"' in script or "'message'" in script
    assert "submitAssistantMessage" in script
    assert "clearAssistantConversation" in script
    assert "updateAssistantAvailability" in script
    assert "plannerAvailable" in script
    # Fallback message wired when planner is offline.
    assert "Static mode" in script
    # No hidden mutation: the assistant must not call applyBlueprintToForm.
    assert "applyBlueprintToForm(result.proposal" not in script
    assert "applyBlueprintToForm(assistant" not in script


def test_styles_css_defines_assistant_panel_styles():
    css = _read("styles.css")

    for selector in (
        ".assistant-panel",
        ".assistant-log",
        ".assistant-message",
        ".assistant-questions",
        ".assistant-proposal",
        ".assistant-footnote",
    ):
        assert selector in css


def test_readme_documents_assistant_chat_mode():
    readme = _read("README.md")
    assert "Builder Assistant chat" in readme
    assert "/api/planner/assistant" in readme

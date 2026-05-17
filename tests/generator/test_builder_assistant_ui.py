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


def test_describe_step_makes_assistant_primary_and_keeps_classic_draft():
    html = _read("index.html")
    describe_block = html[html.index('id="new-app-flow"'):html.index('id="review-flow"')]

    assert "assistant-primary-path" in describe_block
    assert describe_block.index('id="assistant-panel"') < describe_block.index("classic-draft-panel")
    assert "Plan with the Builder Assistant" in describe_block
    assert "Use classic text-only draft" in describe_block
    assert "Draft from text only" in describe_block
    assert "Draft app plan" not in describe_block


def test_app_mjs_calls_assistant_endpoints_and_handles_fallback():
    script = _read("app.mjs")

    assert "/api/planner/assistant/${action}" in script.replace("'", '"') or "assistant/${action}" in script
    assert '"start"' in script or "'start'" in script
    assert '"message"' in script or "'message'" in script
    assert "submitAssistantMessage" in script
    assert "clearAssistantConversation" in script
    assert "updateAssistantAvailability" in script
    assert "plannerAvailable" in script
    assert "Fallback to scripted" in script
    # Fallback message wired when planner is offline.
    assert "Static mode" in script
    # No hidden mutation from message handling: response handler must not auto-apply.
    response_handler = _extract_function(script, "handleAssistantResponse")
    assert response_handler is not None
    assert "applyBlueprintToForm" not in response_handler


def test_app_mjs_exposes_explicit_apply_and_reject_paths():
    script = _read("app.mjs")

    assert "applyAssistantProposal" in script
    assert "rejectAssistantProposal" in script
    assert "apply-preview" in script
    # Apply must mutate the in-memory Builder draft via the existing helper.
    apply_handler = _extract_function(script, "applyAssistantProposal")
    assert apply_handler is not None
    assert "plannerBlueprint = validated.blueprint" in apply_handler
    assert "applyBlueprintToForm(plannerBlueprint)" in apply_handler
    assert "plannerYaml" in apply_handler
    assert "updatePreview()" in apply_handler
    assert "setActiveStep(\"review\")" in apply_handler
    assert "Apply and review plan" in script
    assert "you do not need to click Draft app plan again" in apply_handler
    # Reject must NOT touch the Builder draft.
    reject_handler = _extract_function(script, "rejectAssistantProposal")
    assert reject_handler is not None
    assert "applyBlueprintToForm" not in reject_handler
    assert "plannerBlueprint =" not in reject_handler
    assert "plannerYaml =" not in reject_handler


def _extract_function(script: str, name: str) -> str | None:
    """Return the body of a top-level function/async function declaration."""
    for prefix in (f"async function {name}", f"function {name}"):
        marker = script.find(prefix)
        if marker == -1:
            continue
        brace = script.find("{", marker)
        if brace == -1:
            return None
        depth = 0
        for index in range(brace, len(script)):
            char = script[index]
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    return script[brace : index + 1]
        return None
    return None


def test_styles_css_defines_assistant_panel_styles():
    css = _read("styles.css")

    for selector in (
        ".assistant-primary-path",
        ".classic-draft-panel",
        ".assistant-panel",
        ".assistant-log",
        ".assistant-message",
        ".assistant-questions",
        ".assistant-proposal",
        ".assistant-footnote",
        ".assistant-change",
        ".assistant-change-add",
        ".assistant-change-remove",
        ".assistant-change-replace",
        ".assistant-proposal-actions",
    ):
        assert selector in css


def test_index_html_documents_apply_reject_workflow():
    html = _read("index.html")
    script = _read("app.mjs")

    # The phase 2 placeholder copy must not leak into the phase 3 UI.
    assert "Apply/Reject controls arrive in a later phase" not in html
    assert "Apply and review plan" in script
    assert "Reject" in html


def test_app_mjs_renders_static_scripted_live_status_labels_safely():
    script = _read("app.mjs")

    mode_text = _extract_function(script, "assistantModeText")
    assert mode_text is not None
    assert "Static mode" in mode_text
    assert "Local scripted" in mode_text
    assert "Live OpenAI" in mode_text
    assert "Fallback to scripted" in mode_text
    status = _extract_function(script, "checkPlannerStatus")
    assert status is not None
    assert "status.mode" in status
    assert "status.live_provider" in status


def test_app_mjs_renders_guided_questions_with_chips_and_examples():
    script = _read("app.mjs")

    render = _extract_function(script, "renderAssistantQuestions")
    assert render is not None
    # Guided rendering uses the question_details payload from the backend.
    assert "detailList" in render
    assert "assistant-question-prompt" in render
    assert "assistant-question-helper" in render
    assert "assistant-question-examples" in render
    assert "assistant-question-chips" in render
    assert "assistant-chip" in render
    assert "data-chip-value" in render
    # The chip fill helper exists and never auto-sends — submission stays explicit.
    fill = _extract_function(script, "fillAssistantInputFromChip")
    assert fill is not None
    assert "submitAssistantMessage" not in fill
    assert "assistantSendButton" not in fill


def test_app_mjs_response_handler_passes_question_details_through():
    script = _read("app.mjs")

    response_handler = _extract_function(script, "handleAssistantResponse")
    assert response_handler is not None
    assert "result.question_details" in response_handler
    # Click delegation on #assistant-questions routes chips into the input.
    assert "assistantQuestions?.addEventListener" in script
    assert "data-chip-value" in script
    assert "fillAssistantInputFromChip" in script


def test_styles_css_defines_guided_question_styles():
    css = _read("styles.css")

    for selector in (
        ".assistant-question-list",
        ".assistant-question",
        ".assistant-question-prompt",
        ".assistant-question-helper",
        ".assistant-question-examples",
        ".assistant-question-template",
        ".assistant-question-chips",
        ".assistant-chip",
        ".assistant-questions-hint",
    ):
        assert selector in css


def test_app_mjs_renders_import_and_provider_meta_rows():
    script = _read("app.mjs")

    render = _extract_function(script, "renderAssistantProposal")
    assert render is not None
    # Phase 4: proposal meta block surfaces imports + providers before Apply.
    assert "Imports:" in render
    assert "Providers:" in render
    assert "model?.imports" in render
    assert "model?.providers" in render


def test_index_html_contains_assistant_guidance_container():
    html = _read("index.html")

    # Phase 5: validation guidance lives in a dedicated live region next to the proposal.
    assert 'id="assistant-guidance"' in html
    assert 'role="status"' in html
    assert 'aria-live="polite"' in html


def test_app_mjs_defines_render_assistant_guidance_and_wires_apply_failure():
    script = _read("app.mjs")

    assert "renderAssistantGuidance" in script
    render = _extract_function(script, "renderAssistantGuidance")
    assert render is not None
    # Guidance entries surface message, suggested fix, follow-up question, and the raw error.
    assert "suggested_fix" in render
    assert "follow_up_question" in render
    assert "Raw validation error" in render
    # Apply path must surface guidance on failure (no destructive auto-fix).
    apply_handler = _extract_function(script, "applyAssistantProposal")
    assert apply_handler is not None
    assert "renderAssistantGuidance(result.guidance)" in apply_handler
    # Response handler also surfaces guidance for needs_clarification / message turns.
    response_handler = _extract_function(script, "handleAssistantResponse")
    assert response_handler is not None
    assert "renderAssistantGuidance(result.guidance)" in response_handler
    # Reset/reject clear the guidance.
    reject_handler = _extract_function(script, "rejectAssistantProposal")
    assert reject_handler is not None
    assert "renderAssistantGuidance(null)" in reject_handler


def test_styles_css_defines_assistant_guidance_styles():
    css = _read("styles.css")

    for selector in (
        ".assistant-guidance",
        ".assistant-guidance-item",
        ".assistant-guidance-message",
        ".assistant-guidance-fix",
        ".assistant-guidance-question",
        ".assistant-guidance-raw",
        ".assistant-guidance-tag",
    ):
        assert selector in css


def test_app_mjs_model_driven_apply_updates_review_and_live_plan():
    script = _read("app.mjs")

    assert "modelDrivenSummary" in script
    assert "modelDrivenCapabilityGroups" in script
    assert "renderModelDrivenReviewSummary" in script
    preview = _extract_function(script, "renderGenerationPreview")
    assert preview is not None
    assert "model-driven-review-summary" in preview
    assert "you do not need to click Draft app plan again" in preview
    build_summary = _extract_function(script, "renderBuildSummary")
    assert build_summary is not None
    assert "modelDrivenCapabilityGroups(modelSummary)" in build_summary
    assert "activeBlueprint?.display_name" in build_summary


def test_app_mjs_model_driven_review_replaces_scoring_customization():
    script = _read("app.mjs")

    render_customization = _extract_function(script, "renderCustomizationPanel")
    assert render_customization is not None
    assert "isModelDrivenBlueprint" in render_customization
    assert "renderModelDrivenReviewSummary" in render_customization
    model_summary = _extract_function(script, "renderModelDrivenReviewSummary")
    assert model_summary is not None
    assert "Model-driven app summary" in model_summary
    assert "UI recipe/composition" in model_summary
    assert "Scoring / triage labels" not in model_summary


def test_styles_css_defines_model_driven_summary_styles():
    css = _read("styles.css")
    assert ".model-driven-summary-card" in css


def test_readme_documents_assistant_chat_mode():
    readme = _read("README.md")
    assert "Builder Assistant chat" in readme
    assert "/api/planner/assistant" in readme

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


def test_assistant_panel_is_persistent_outside_describe_step():
    html = _read("index.html")
    describe_block = html[html.index('id="new-app-flow"'):html.index('id="review-flow"')]
    side_panel = html[html.index('class="builder-side-panel"'):html.index('</aside>', html.index('class="builder-side-panel"'))]

    assert 'id="assistant-panel"' not in describe_block
    assert 'id="assistant-panel"' in side_panel
    assert 'persistent-assistant-panel' in side_panel
    assert 'aria-label="Persistent Builder assistant"' in html
    # Agent-first canvas: composer + proposal live in the Describe step.
    assert 'id="assistant-form"' in describe_block
    assert 'id="assistant-input"' in describe_block
    assert 'id="assistant-proposal"' in describe_block
    # Rail no longer carries the proposal block — it now shows just a pointer.
    assert 'id="assistant-proposal"' not in side_panel
    assert 'id="assistant-proposal-pointer"' in side_panel


def test_review_workspace_renders_plan_build_run_cards_without_advanced_drawer():
    html = _read("index.html")
    review_block = html[html.index('id="review-flow"'):html.index('id="generate-flow"')]

    assert 'class="plan-build-run-workspace"' in review_block
    assert 'class="workspace-card plan-card"' in review_block
    assert 'Plan, build, and run your local demo' in review_block
    assert 'workspace-step-number' in review_block
    assert 'Plan</p>' in review_block
    assert 'id="assistant-proposal"' in html
    assert 'id="assistant-guidance"' in html
    assert 'class="build-summary live-plan plan-card-live-plan"' in review_block
    assert 'class="local-run-panel workspace-card build-card"' in review_block
    assert 'Build</p>' in review_block
    assert 'class="workspace-card run-card"' in review_block
    assert 'Run</p>' in review_block
    assert 'Advanced: YAML, CLI, logs' in html


def test_advanced_surface_contains_yaml_cli_logs_and_diagnostics():
    html = _read("index.html")
    script = _read("app.mjs")
    review_block = html[html.index('id="review-flow"'):html.index('id="generate-flow"')]
    export_block = html[html.index('id="generate-flow"'):html.index('id="existing-repo-flow"')]

    assert 'id="advanced-drawer"' in review_block
    assert review_block.count("Advanced: YAML, CLI, logs") == 1
    assert 'id="yaml-preview"' in review_block
    assert 'id="copy-yaml"' in review_block
    assert 'id="download-yaml"' in review_block
    assert 'id="local-run-log"' in review_block
    assert 'id="copy-local-run-log"' in review_block
    assert 'Planner diagnostics' in review_block
    assert 'id="copy-yaml-export"' in export_block
    assert 'id="copy-cli-commands"' in export_block
    assert 'id="plan-preview"' in export_block
    assert "copyCliCommands" in script
    assert "copyLocalRunLog" in script


def test_describe_step_keeps_classic_draft_without_plan_build_run_rewrite():
    html = _read("index.html")
    describe_block = html[html.index('id="new-app-flow"'):html.index('id="review-flow"')]

    assert "Use classic text-only draft" in describe_block
    assert "Draft from text only" in describe_block
    assert "Draft app plan" not in describe_block
    # Slice A removes the 4-step wizard nav entirely.
    assert '<nav class="flow-rail"' not in html
    # Canvas state strip replaces the nav as the top-of-canvas affordance.
    assert 'class="canvas-state-strip"' in html
    assert 'id="canvas-state-badge"' in html


def test_phase_8e_polish_adds_clear_states_and_responsive_styles():
    html = _read("index.html")
    script = _read("app.mjs")
    css = _read("styles.css")

    assert "Run app checks" in html
    assert "Plan needed" in html
    assert "Plan ready" in script
    assert "Blueprint pending" in html
    assert "Next step" in html
    assert "Build status" in script
    assert "Keep this tab open" in script
    assert "renderBuildRunStatusChips" in script
    assert "aria-busy" in script
    assert ".compact-status-row" in css
    assert ".status-chip" in css
    assert ".next-action-row" in css
    assert ".local-run-empty-state" in css
    assert ".local-run-result.pending" in css
    assert ".service-status" in css and "grid-template-columns: 1fr" in css


def test_phase_8e_simplification_promotes_one_next_action():
    html = _read("index.html")
    script = _read("app.mjs")
    css = _read("styles.css")

    # Build card has a single dominant primary action button.
    assert 'id="build-primary-action"' in html
    assert 'class="primary-button next-action-button"' in html
    # Secondary build actions are demoted behind a details element.
    assert 'class="inline-advanced secondary-build-actions-details"' in html
    assert 'id="local-run-validate-blueprint"' in html
    assert 'class="quiet-button"' in html
    # JS derives the next step from current state and wires it to the primary button.
    assert "function computeNextStep" in script
    assert "updateBuildPrimaryAction" in script
    assert "buildPrimaryAction?.addEventListener" in script
    # CSS demotes secondary build actions and styles the next-action button.
    assert ".next-action-button" in css
    assert ".secondary-build-actions-details" in css


def test_phase_8e_simplification_rebuilds_run_controls_as_service_rows():
    html = _read("index.html")
    script = _read("app.mjs")
    css = _read("styles.css")

    # Run card uses compact per-service rows instead of a flat 4-button row.
    assert 'class="run-service-rows"' in html
    assert 'class="service-row"' in html
    assert 'data-service="backend"' in html
    assert 'data-service="frontend"' in html
    # Service-row controls are secondary; the main Build button owns the default path.
    assert 'id="local-run-start-backend" type="button" class="quiet-button service-row-primary"' in html
    assert 'id="local-run-stop-backend" type="button" class="quiet-button service-row-stop" hidden' in html
    assert 'id="local-run-start-frontend" type="button" class="quiet-button service-row-primary"' in html
    assert 'id="local-run-stop-frontend" type="button" class="quiet-button service-row-stop" hidden' in html
    assert 'class="inline-advanced service-controls-details"' in html
    # The "Open in browser" link is rendered next to the frontend row when reachable.
    assert 'id="frontend-open-link"' in html
    # JS toggles Start/Stop visibility based on status and never renders both as equally prominent.
    assert "updateServiceRow" in script
    assert "stopButton.hidden" in script
    assert "startButton.hidden" in script
    # CSS gives status-specific border tones so the row reflects state at a glance.
    assert ".service-row" in css
    assert '.service-row[data-status="running"]' in css
    assert ".service-row-primary" in css
    assert ".service-row-stop" in css


def test_phase_8e_simplification_simplifies_plan_card_and_customize():
    html = _read("index.html")
    script = _read("app.mjs")
    css = _read("styles.css")

    # Plan summary leads with human copy; technical metadata stays behind Advanced details.
    assert 'class="plan-summary-human"' in html
    assert "AgentForge will turn it into a plain-language plan" in html
    assert '<summary>Advanced plan details</summary>' in html
    assert 'class="plan-summary-list"' in html
    assert 'id="plan-summary-app"' in html
    assert 'id="plan-summary-type"' in html
    assert 'id="plan-summary-entities"' in html
    assert 'id="plan-summary-providers"' in html
    assert 'id="plan-summary-status"' in html
    # Assumptions/warnings are demoted behind a details element.
    assert 'id="plan-summary-extras"' in html
    # Customize panel is moved behind a details element and not in the default view.
    assert 'id="customize-details"' in html
    assert "<summary>Customize app details</summary>" in html
    # JS renders into the new summary fields.
    assert "renderPlanSummaryList" in script
    assert "planSummarySentence" in script
    assert "planSummaryApp" in script
    # CSS defines the compact summary list layout and the customize details container.
    assert ".plan-summary-human" in css
    assert ".plan-summary-list" in css
    assert ".customize-details" in css


def test_phase_8e_simplification_adds_assistant_current_guidance_and_collapses_history():
    html = _read("index.html")
    script = _read("app.mjs")
    css = _read("styles.css")

    # The persistent assistant panel surfaces a compact next-action block.
    assert 'id="assistant-next-step"' in html
    assert 'aria-label="Next action"' in html
    assert 'id="assistant-next-step-label"' in html
    assert 'id="assistant-next-step-detail"' in html
    # Conversation history is wrapped in a details element so it can collapse.
    assert 'id="assistant-history"' in html
    assert 'class="assistant-history-details"' in html
    # The original assistant-log lives inside the history details, still labelled.
    assert 'id="assistant-log"' in html
    assert 'role="log"' in html
    # JS marks the panel as applied so older conversation collapses after Apply.
    assert "setAssistantApplied" in script
    assert 'assistantPanel.dataset.applied = "true"' in script
    assert "renderAssistantNextStep" in script
    # CSS defines next-step styling and the applied-state visual treatment.
    assert ".assistant-next-step" in css
    assert ".assistant-history-details" in css
    assert '.assistant-panel[data-applied="true"]' in css


def test_app_mjs_calls_assistant_endpoints_and_handles_fallback():
    script = _read("app.mjs")

    assert "/api/planner/assistant/${action}" in script.replace("'", '"') or "assistant/${action}" in script
    assert '"start"' in script or "'start'" in script
    assert '"message"' in script or "'message'" in script
    assert "submitAssistantMessage" in script
    assert "clearAssistantConversation" in script
    assert "updateAssistantAvailability" in script
    assert "plannerAvailable" in script
    # The clear-on-form-input guard moved into shouldClearOnFormInput, which
    # still respects .planner-panel and #assistant-panel exemptions (and now
    # also exempts Advanced/details inspection regions).
    should_clear = _extract_function(script, "shouldClearOnFormInput")
    assert should_clear is not None
    assert '.planner-panel' in should_clear
    assert '#assistant-panel' in should_clear
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
    assert "Validate Blueprint in the Local Control Room" in apply_handler
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


def test_app_mjs_supports_assistant_activity_messages():
    script = _read("app.mjs")

    assert "appendAssistantMessage(\"activity\"" in script
    role_label = _extract_function(script, "assistantMessageRoleLabel")
    assert role_label is not None
    assert "Activity" in role_label


def test_styles_css_defines_assistant_panel_styles():
    css = _read("styles.css")

    for selector in (
        ".builder-side-panel",
        ".persistent-assistant-panel",
        ".assistant-shell-note",
        ".assistant-primary-path",
        ".classic-draft-panel",
        ".assistant-panel",
        ".assistant-log",
        ".assistant-message",
        ".assistant-message-activity",
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
    assert "Reject" in script


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
    # Proposal summary still surfaces imports + providers before Apply, via the shared model summary.
    assert "Imports:" in render
    assert "Providers:" in render
    assert "modelDrivenSummary(proposal.blueprint)" in render
    assert "importLabel" in render
    assert "providerLabel" in render


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
    assert "displayTitleForBlueprint(activeBlueprint" in build_summary


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


# ---------------------------------------------------------------------------
# Agent-first canvas correction (pre-commit Phase 8E) — composer + proposal in
# main canvas; right rail is compact guidance; thinking state; copy cleanup.
# ---------------------------------------------------------------------------


def test_agent_first_main_canvas_composer_lives_on_start_and_describe():
    html = _read("index.html")
    script = _read("app.mjs")
    css = _read("styles.css")

    # Start step exposes a primary composer in the main canvas.
    start_block = html[html.index('data-step="start"'):html.index('data-step="new-app"')]
    assert 'id="hero-composer"' in start_block
    assert 'id="hero-composer-input"' in start_block
    assert 'id="hero-composer-send"' in start_block
    assert "main-canvas-composer" in start_block
    # Path grid is reduced — only the secondary repo affordance remains.
    assert "Start from an app idea" not in start_block

    # Describe step main canvas hosts the assistant conversation composer.
    describe_block = html[html.index('id="new-app-flow"'):html.index('id="review-flow"')]
    assert 'class="main-canvas-conversation"' in describe_block
    assert 'class="assistant-form main-canvas-composer"' in describe_block
    assert 'id="assistant-input"' in describe_block
    assert 'id="assistant-send"' in describe_block

    # JS routes the hero composer through the existing send pipeline.
    assert "heroComposer?.addEventListener" in script
    assert "submitAssistantMessage(heroComposerInput" in script

    # CSS provides composer styling.
    assert ".main-canvas-composer" in css
    assert ".main-canvas-conversation" in css


def test_agent_first_proposal_renders_in_main_canvas():
    html = _read("index.html")
    script = _read("app.mjs")
    css = _read("styles.css")

    describe_block = html[html.index('id="new-app-flow"'):html.index('id="review-flow"')]
    side_panel = html[html.index('class="builder-side-panel'):html.index('</aside>', html.index('class="builder-side-panel'))]

    # Proposal block sits in main canvas with the wide-canvas class.
    assert 'id="assistant-proposal"' in describe_block
    assert "main-canvas-proposal" in describe_block
    # Old in-rail proposal block is gone.
    assert 'id="assistant-proposal"' not in side_panel
    # Rail surfaces only a compact pointer to the main canvas card.
    assert 'id="assistant-proposal-pointer"' in side_panel
    assert "Plan ready — review in main area" in side_panel

    # Proposal copy is human-first with technical diff collapsed behind details.
    assert "Plan ready" in script
    assert "Technical changes" in script
    assert 'class="assistant-proposal-facts"' in script
    assert 'class="assistant-proposal-chips"' in script
    assert '<details class="assistant-proposal-changes"><summary>Technical changes' in script

    # CSS styles the wide proposal card without trapping the entire card in a tiny scroller.
    assert ".assistant-proposal.main-canvas-proposal" in css
    assert "max-height: none" in css
    assert "overflow: visible" in css
    assert ".assistant-proposal-pointer" in css


def test_agent_first_thinking_state_marks_main_canvas():
    html = _read("index.html")
    script = _read("app.mjs")
    css = _read("styles.css")

    # Thinking indicators exist but hidden indicators must not be revealed by class display rules at idle.
    assert 'id="assistant-thinking"' in html
    assert 'id="hero-composer-thinking"' in html
    assert ">Drafting plan…<" in html
    assert ".composer-thinking[hidden]" in css
    # JS exposes a dedicated setAssistantThinking helper and toggles it on submit.
    assert "function setAssistantThinking" in script
    submit = _extract_function(script, "submitAssistantMessage")
    assert submit is not None
    assert "setAssistantThinking(true)" in submit
    assert "setAssistantThinking(false)" in submit
    assert "setAssistantThinking(false);\n    handleAssistantResponse(result)" in submit
    # CSS pulses the indicator so the main canvas does not look empty.
    assert ".composer-thinking" in css
    assert "composer-thinking-pulse" in css
    assert 'assistant-panel[data-thinking="true"]' in css


def test_builder_title_cleanup_removes_prompt_prefixes():
    script = _read("app.mjs")
    assert "function cleanAppDisplayTitle" in script
    assert "function displayTitleForBlueprint" in script
    assert "I Want Manage My" not in script
    assert "replace(/^(?:please\\s+)?(?:i|we)\\s+(?:want|need|would like)" in script
    assert "replace(/^(?:to\\s+)?(?:manage|track|organize|monitor)" in script
    assert "finance" in script and "Manager" in script


def test_shell_spacing_centers_workspace_as_single_unit():
    css = _read("styles.css")
    assert ".builder.wizard-shell" in css
    assert "width: min(1360px, calc(100% - 24px))" in css
    assert "padding: 14px 0 32px" in css
    assert "box-shadow: 0 22px 70px" in css


def test_agent_first_right_rail_is_compact_guidance_only():
    html = _read("index.html")

    side_panel = html[html.index('class="builder-side-panel'):html.index('</aside>', html.index('class="builder-side-panel'))]

    # Compact rail markers.
    assert "compact-side-panel" in side_panel
    assert "compact-assistant-panel" in side_panel
    # Rail keeps HUD state, next action, compact summaries, and a collapsed history trigger.
    assert 'id="assistant-current-state"' in side_panel
    assert 'id="assistant-next-step"' in side_panel
    assert 'id="assistant-app-summary"' in side_panel
    assert 'id="assistant-service-summary"' in side_panel
    assert 'id="assistant-history"' in side_panel
    assert "History" in side_panel
    # Rail no longer hosts the input/send affordance — that lives in main canvas.
    assert 'id="assistant-form"' not in side_panel
    assert 'id="assistant-input"' not in side_panel
    assert 'id="assistant-send"' not in side_panel
    # Rail still shows the assistant mode and status.
    assert 'id="assistant-mode-label"' in side_panel
    assert 'id="assistant-status"' in side_panel


def test_agent_first_assistant_history_collapses_by_default():
    html = _read("index.html")

    history_index = html.index('id="assistant-history"')
    tag_start = html.rfind("<details", 0, history_index)
    open_tag_end = html.index(">", tag_start)
    open_tag = html[tag_start : open_tag_end + 1]

    # Conversation history is NOT auto-open — rail starts compact.
    assert " open" not in open_tag


def test_agent_first_assistant_history_scrolls_when_expanded():
    css = _read("styles.css")

    assert ".assistant-history-details[open]" in css
    assert "min-height: 0" in css
    assert "overflow: hidden" in css
    assert ".assistant-history-details[open] .assistant-log" in css
    assert "max-height: min(360px, 45vh)" in css
    assert "overflow-y: auto" in css
    assert "overscroll-behavior: contain" in css


def test_agent_first_copy_cleanup_filters_generic_acknowledgements():
    script = _read("app.mjs")

    # Generic ack patterns are filtered before being appended to the log.
    assert "GENERIC_ACK_PATTERNS" in script
    assert "function isGenericAcknowledgement" in script
    handler = _extract_function(script, "handleAssistantResponse")
    assert handler is not None
    assert "isGenericAcknowledgement" in handler
    # A synthetic Plan ready activity message replaces verbose echoes when a proposal arrives.
    assert "function planReadyMessage" in script
    assert "Plan ready" in script


def test_agent_first_compact_start_hero_reduces_first_viewport():
    html = _read("index.html")
    css = _read("styles.css")

    start_block = html[html.index('data-step="start"'):html.index('data-step="new-app"')]
    # Compact markers on entry hero.
    assert "compact-entry-hero" in start_block
    assert "compact-lede" in start_block
    assert "compact-entry-step" in html
    # The eyebrow above the heading was removed.
    assert "No-key local demo" not in start_block
    # CSS tightens the hero.
    assert ".compact-entry-hero" in css
    assert ".compact-lede" in css


# === Slice A — canvas state machine acceptance ===


def test_slice_a_builder_shell_carries_canvas_state_attribute():
    html = _read("index.html")
    assert 'id="builder-shell"' in html
    assert 'data-canvas-state="empty"' in html
    # Strip + badge replace the wizard nav.
    assert 'class="canvas-state-strip"' in html
    assert 'id="canvas-state-badge"' in html
    assert 'id="canvas-state-label"' in html
    assert 'id="canvas-state-detail"' in html


def test_slice_a_canvas_state_machine_defines_required_states():
    script = _read("app.mjs")
    assert "function computeCanvasState" in script
    assert "function applyCanvasState" in script
    for state in (
        "empty",
        "thinking",
        "plan-ready",
        "plan-applied",
        "validating",
        "generating",
        "checking",
        "running",
        "open-app",
        "error",
    ):
        assert f'"{state}"' in script, f"canvas state {state!r} should be referenced in app.mjs"
    # Apply hook is reachable from all the major state-change call sites.
    assert "applyCanvasState();" in script


def test_slice_a_thinking_state_gated_by_submission_in_flight():
    script = _read("app.mjs")
    assert "assistantSubmissionInFlight" in script
    # The submission flag is set in setAssistantThinking only.
    assert "assistantSubmissionInFlight = Boolean(thinking)" in script
    # computeCanvasState returns "thinking" only when the flag is true.
    assert 'if (assistantSubmissionInFlight) return "thinking";' in script
    # submitAssistantMessage is the single producer of the flag.
    submit_index = script.index("async function submitAssistantMessage")
    submit_end = script.index("}\n", submit_index) + 1
    submit_body = script[submit_index:submit_end]
    assert "setAssistantThinking(true)" in submit_body
    assert "setAssistantThinking(false)" in submit_body
    # No other call site flips the flag on.
    other_calls = [
        line
        for line in script.splitlines()
        if "setAssistantThinking(true)" in line and "//" not in line
    ]
    assert len(other_calls) == 1, "setAssistantThinking(true) should only be called from submitAssistantMessage"


def test_slice_a_thinking_overlay_exists_in_canvas():
    html = _read("index.html")
    css = _read("styles.css")
    assert 'id="canvas-thinking-overlay"' in html
    assert "Drafting your app plan" in html
    assert "Finding entities, pages, and build steps." in html
    assert 'id="canvas-thinking-echo"' in html
    # CSS makes the overlay a dominant centered surface and hides other steps in thinking state.
    assert ".canvas-thinking-overlay" in css
    assert '.builder[data-canvas-state="thinking"] .wizard-step' in css
    assert '.canvas-thinking-overlay[hidden]' in css
    assert '.builder:not([data-canvas-state="thinking"]) .canvas-thinking-overlay' in css


def test_slice_a_plan_ready_state_hides_composer():
    css = _read("styles.css")
    # plan-ready collapses the composer so the proposal owns the canvas.
    assert '.builder[data-canvas-state="plan-ready"] #assistant-form' in css
    assert '.builder[data-canvas-state="plan-ready"] #hero-composer' in css


def test_slice_a_wizard_chrome_is_removed():
    html = _read("index.html")
    # No flow-rail nav element.
    assert '<nav class="flow-rail"' not in html
    # No visible "Step N" labels above each panel head.
    for label in ("Step 2", "Step 3", "Step 4"):
        # Allowed inside JS strings or CSS comments only — assert no <p class="step-label"> wrapper survives.
        assert f'<p class="step-label">{label}</p>' not in html
    # No "Secondary flow" wizard label either.
    assert '<p class="step-label">Secondary flow</p>' not in html


def test_slice_a_canvas_state_badge_carries_state_copy():
    script = _read("app.mjs")
    assert "CANVAS_STATE_COPY" in script
    # Each major state has a label and detail string; identifier keys are unquoted in JS,
    # hyphenated keys are quoted.
    for ident_state in ("empty", "thinking", "running", "error"):
        assert f"  {ident_state}: {{" in script, f"canvas state {ident_state!r} should have a copy entry"
    for quoted_state in ("plan-ready", "plan-applied", "open-app"):
        assert f'"{quoted_state}":' in script, f"canvas state {quoted_state!r} should have a copy entry"


def test_slice_a_local_run_busy_tracks_active_build_op():
    script = _read("app.mjs")
    assert "activeBuildOp" in script
    # setLocalRunBusy accepts an op argument and assigns it.
    assert "function setLocalRunBusy(message, op = null)" in script
    assert "activeBuildOp = op" in script
    # The four local-run actions pass the op key. Copy was humanized in the
    # Builder UX persistence/progress polish pass.
    assert 'setLocalRunBusy("Validating plan…", "validate-blueprint")' in script
    assert 'setLocalRunBusy("Generating your app…", "generate")' in script
    assert 'setLocalRunBusy("Running app checks…", "validate-app")' in script
    assert 'setLocalRunBusy(`${verb} ${service}...`, action)' in script


def test_slice_a_advanced_yaml_cli_logs_still_exposed():
    html = _read("index.html")
    # Advanced drawer still hosts YAML, CLI, raw logs after slice A.
    assert 'id="advanced-drawer"' in html
    assert 'id="yaml-preview"' in html
    assert 'id="copy-yaml"' in html
    assert 'id="local-run-log"' in html
    assert 'id="copy-local-run-log"' in html
    # Export advanced drawer still has CLI commands.
    assert 'id="plan-preview"' in html
    assert 'id="copy-cli-commands"' in html


def test_slice_a_right_rail_remains_compact():
    html = _read("index.html")
    aside_index = html.index('<aside class="builder-side-panel"')
    aside_block = html[aside_index:html.index("</aside>", aside_index)]
    # Rail keeps mode, current guidance, next-action label, and history.
    assert 'id="assistant-next-step"' in aside_block
    assert 'id="assistant-history"' in aside_block
    # No composer or proposal moved back into the rail.
    assert "<textarea" not in aside_block
    assert 'id="assistant-proposal"' not in aside_block
    assert 'id="assistant-form"' not in aside_block


def test_slice_a_advanced_drawer_opens_without_page_wide_grid_shift():
    css = _read("styles.css")
    assert ".advanced-drawer[open]" in css
    assert "display: block" in css
    assert ".advanced-drawer[open] > .advanced-section" in css


def test_slice_a_progressive_next_action_still_drives_build_card():
    script = _read("app.mjs")
    # The morphing primary button + computeNextStep contract is intact.
    assert "function computeNextStep" in script
    assert "updateBuildPrimaryAction" in script
    assert "buildPrimaryAction?.addEventListener" in script


def test_slice_b_right_rail_hud_blocks_and_no_heavy_content():
    html = _read("index.html")
    side_panel = html[html.index('class="builder-side-panel'):html.index('</aside>', html.index('class="builder-side-panel'))]

    for marker in (
        'id="assistant-current-state"',
        'id="assistant-current-state-label"',
        'id="assistant-next-step"',
        'id="assistant-app-summary"',
        'id="assistant-app-name"',
        'id="assistant-app-type"',
        'id="assistant-app-entities"',
        'id="assistant-service-summary"',
        'id="assistant-backend-chip"',
        'id="assistant-frontend-chip"',
        'id="assistant-open-app-link"',
    ):
        assert marker in side_panel

    assert "<form" not in side_panel
    assert "<textarea" not in side_panel
    assert 'id="assistant-proposal"' not in side_panel
    assert 'id="local-run-log"' not in side_panel
    assert "Apply installs only" not in side_panel


def test_slice_b_rail_state_next_action_and_summary_are_computed_in_app_mjs():
    script = _read("app.mjs")

    for function_name in (
        "function renderRailHud",
        "function railStatusLine",
        "function hudNextStepCopy",
        "function renderRailAppSummary",
        "function renderRailServiceSummary",
        "function updateRailServiceChip",
    ):
        assert function_name in script

    for copy in (
        "Describe your app.",
        "Review the proposed plan.",
        "Validate the Blueprint.",
        "Generate the local app.",
        "Run checks.",
        "Start app.",
        "Open the app.",
        "Something failed. See Advanced/logs.",
    ):
        assert copy in script

    assert "assistantAppSummary.hidden" in script
    assert "assistantServiceSummary.hidden" in script
    assert "assistantOpenAppLink.hidden = false" in script


def test_slice_b_rail_css_keeps_hud_compact_and_scrolls_history():
    css = _read("styles.css")

    assert ".compact-assistant-panel" in css
    assert "max-height: calc(100vh - 28px)" in css
    assert "overflow-y: auto" in css
    assert ".assistant-hud-block" in css
    assert ".assistant-app-entities" in css
    assert ".assistant-service-chip" in css
    assert ".assistant-open-app-link" in css
    assert ".assistant-history-details[open] .assistant-log" in css
    assert "overflow-y: auto" in css

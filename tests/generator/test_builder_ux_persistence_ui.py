"""Static UI tests for Builder UX persistence and progress polish.

These tests treat builder/ files as static assets and inspect markup and the
client-side script for the persistence/progress behaviours required by the
"Builder UX persistence + progress polish" phase.
"""
from pathlib import Path

BUILDER_DIR = Path(__file__).resolve().parents[2] / "builder"


def _read(name: str) -> str:
    return (BUILDER_DIR / name).read_text(encoding="utf-8")


def _extract_function(script: str, name: str) -> str | None:
    marker = f"function {name}"
    start = script.find(marker)
    if start == -1:
        return None
    depth = 0
    body_start = script.find("{", start)
    for index in range(body_start, len(script)):
        char = script[index]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return script[start:index + 1]
    return None


def test_session_storage_helpers_exist_and_use_versioned_key():
    script = _read("app.mjs")
    assert 'SESSION_STORAGE_KEY = "agentforge.builder.session.v1"' in script
    assert "SESSION_SCHEMA_VERSION" in script
    for name in (
        "safeReadSession",
        "safeWriteSession",
        "safeClearSession",
        "collectSessionSnapshot",
        "restoreSessionFromStorage",
        "resetBuilderSession",
        "persistSessionSoon",
    ):
        assert _extract_function(script, name) is not None, name


def test_persistence_avoids_secrets_and_large_logs():
    script = _read("app.mjs")
    snapshot = _extract_function(script, "collectSessionSnapshot")
    sanitize_step = _extract_function(script, "sanitizeStepForPersistence")
    sanitize_log = _extract_function(script, "sanitizeLogEntriesForPersistence")
    assert snapshot is not None and sanitize_step is not None and sanitize_log is not None
    # The raw stdout/stderr captured by local-run are never serialised.
    assert "stdout" not in sanitize_step
    assert "stderr" not in sanitize_step
    # Secrets-shaped log lines are redacted on the way to localStorage.
    assert "SECRET_KEY_PATTERN" in script
    assert "[redacted line]" in sanitize_log
    # Persisted summary stays bounded.
    assert "MAX_PERSISTED_HISTORY" in script
    assert "MAX_PERSISTED_STEP_DETAIL" in script
    # plannerYaml is sliced to a reasonable cap.
    assert "plannerYaml.slice" in snapshot


def test_persistence_restores_blueprint_run_summary_and_log():
    script = _read("app.mjs")
    restore = _extract_function(script, "restoreSessionFromStorage")
    assert restore is not None
    assert "applyBlueprintToForm(plannerBlueprint)" in restore
    assert "localRunState =" in restore
    assert "appendAssistantMessage" in restore
    assert "Re-checking live services" in restore


def test_boot_attempts_restore_before_planner_check():
    script = _read("app.mjs")
    boot_index = script.find("renderArchetypes();")
    restore_index = script.find("restoreSessionFromStorage()", boot_index)
    planner_status_index = script.find("checkPlannerStatus();", boot_index)
    assert boot_index >= 0 and restore_index >= 0 and planner_status_index >= 0
    assert restore_index < planner_status_index


def test_reset_session_button_present_and_wired():
    html = _read("index.html")
    script = _read("app.mjs")
    assert 'id="reset-session"' in html
    assert "Reset session" in html
    assert "resetSessionButton?.addEventListener" in script
    assert "resetBuilderSession" in script
    reset_start = script.find("function resetBuilderSession")
    assert reset_start >= 0
    # Search a generous window after the signature for the storage clear call.
    assert "safeClearSession()" in script[reset_start:reset_start + 800]


def test_beforeunload_flushes_session_to_storage():
    script = _read("app.mjs")
    assert 'window.addEventListener("beforeunload"' in script
    # The handler must write the current snapshot, not just clear the debounce.
    handler_start = script.find('window.addEventListener("beforeunload"')
    handler_block = script[handler_start:handler_start + 400]
    assert "safeWriteSession(collectSessionSnapshot())" in handler_block


def test_advanced_details_clicks_do_not_navigate_canvas_or_clear_plan():
    script = _read("app.mjs")
    assert _extract_function(script, "isInsideAdvancedRegion") is not None
    should_clear = _extract_function(script, "shouldClearOnFormInput")
    assert should_clear is not None
    assert "isInsideAdvancedRegion(target)" in should_clear
    # The document click listener must short-circuit on summary clicks and
    # inside Advanced regions before evaluating data-step-target.
    click_listener_index = script.find('document.addEventListener("click"')
    assert click_listener_index >= 0
    click_block = script[click_listener_index:click_listener_index + 600]
    assert 'event.target.closest("summary")' in click_block
    assert "isInsideAdvancedRegion(event.target)" in click_block


def test_input_change_listeners_skip_advanced_regions():
    script = _read("app.mjs")
    should_clear = _extract_function(script, "shouldClearOnFormInput")
    is_advanced = _extract_function(script, "isInsideAdvancedRegion")
    assert should_clear is not None and is_advanced is not None
    assert "isInsideAdvancedRegion(target)" in should_clear
    for selector in ("#advanced-drawer", ".inline-advanced", ".plan-summary-extras", ".customize-details"):
        assert selector in is_advanced


def test_build_op_progress_table_has_user_facing_expectation_copy():
    script = _read("app.mjs")
    progress_index = script.find("BUILD_OP_PROGRESS")
    assert progress_index >= 0
    block = script[progress_index:progress_index + 1800]
    # Hyphenated keys must be quoted; bare identifier keys may be unquoted.
    for quoted in ("validate-blueprint", "validate-app", "start-app"):
        assert f'"{quoted}"' in block
    assert "generate:" in block or '"generate"' in block
    # No fake exact-percentage progress bars; instead ranged or qualitative text.
    assert "Usually a few seconds" in block
    assert "May take 20–60 seconds on first install" in block
    assert "Starting services… this can take a moment" in block
    assert "%" not in block.replace("100%", "")


def test_set_local_run_busy_disables_primary_action_and_surfaces_expectation():
    script = _read("app.mjs")
    fn = _extract_function(script, "setLocalRunBusy")
    assert fn is not None
    assert "buildPrimaryAction.disabled = true" in fn
    assert 'buildPrimaryAction.dataset.busy = "true"' in fn
    assert "BUILD_OP_PROGRESS[op]" in fn
    assert 'localRunPanel?.setAttribute("aria-busy", "true")' in fn
    assert 'data-busy-op' in fn
    assert "persistSessionSoon()" in fn


def test_finish_local_run_clears_busy_state_and_persists():
    script = _read("app.mjs")
    fn = _extract_function(script, "finishLocalRun")
    assert fn is not None
    assert 'localRunPanel?.setAttribute("aria-busy", "false")' in fn
    assert "data-busy-op" in fn
    assert "persistSessionSoon()" in fn


def test_canvas_overlay_shows_during_local_run_operations_with_per_op_copy():
    script = _read("app.mjs")
    apply = _extract_function(script, "applyCanvasState")
    assert apply is not None
    assert "localRunBusy" in apply
    assert "BUILD_OP_PROGRESS[activeBuildOp]" in apply
    assert "canvasThinkingHeadline" in apply
    assert "canvasThinkingExpectation" in apply


def test_thinking_overlay_markup_includes_expectation_line():
    html = _read("index.html")
    assert 'id="canvas-thinking-headline"' in html
    assert 'id="canvas-thinking-subline"' in html
    assert 'id="canvas-thinking-expectation"' in html
    assert "Usually a few seconds." in html


def test_failure_messages_still_point_to_advanced_logs():
    script = _read("app.mjs")
    fn = _extract_function(script, "renderLocalRunResult")
    assert fn is not None
    assert "Advanced logs" in fn
    assert 'href="#advanced-logs"' in fn


def test_clarifying_questions_inference_surfaces_questions_when_assistant_signals_more_detail():
    script = _read("app.mjs")
    fn = _extract_function(script, "inferClarifyingQuestions")
    assert fn is not None
    assert "NEEDS_DETAIL_PATTERNS" in script
    assert "Reply in the assistant composer below." in fn
    assert "Tell the assistant a bit more about the app you want to build." in fn


def test_handle_assistant_response_uses_inferred_questions_when_present():
    script = _read("app.mjs")
    fn = _extract_function(script, "handleAssistantResponse")
    assert fn is not None
    assert "inferClarifyingQuestions(result, filtered)" in fn
    assert "renderAssistantQuestions(" in fn
    assert "inferred ? inferred.questions : result.questions" in fn


def test_question_renderer_shows_examples_and_chips_in_main_canvas():
    html = _read("index.html")
    script = _read("app.mjs")
    # The assistant-questions container lives inside the main-canvas-conversation, not the rail.
    main_canvas_start = html.index('main-canvas-conversation')
    main_canvas_end = html.index('</section>', main_canvas_start)
    assert 'id="assistant-questions"' in html[main_canvas_start:main_canvas_end]
    fn = _extract_function(script, "renderAssistantQuestions")
    assert fn is not None
    assert "assistant-question-examples" in fn
    assert "assistant-question-chips" in fn
    assert "Guided questions" in fn


def test_styles_define_new_persistence_progress_classes():
    css = _read("styles.css")
    for selector in (
        ".canvas-thinking-expectation",
        ".reset-session-button",
        ".local-run-busy-hint",
    ):
        assert selector in css

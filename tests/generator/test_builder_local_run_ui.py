"""Static UI tests for the Builder Local Control Room MVP."""
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


def test_step_labels_reframe_review_build_and_export_next_steps():
    html = _read("index.html")
    step4_block = html[html.index('id="generate-flow"'):html.index('id="existing-repo-flow"')]

    # Slice A removes the 4-step wizard nav. Canvas region headings carry the labels now.
    assert '<nav class="flow-rail"' not in html
    assert "Plan, build, and run your local demo" in html
    # Slice 8E re-titled the panel to "Export / CLI" and demoted it from primary path.
    assert "Export / CLI" in step4_block
    assert "Export / next steps" not in step4_block
    assert "Generate and run locally" not in step4_block
    # Visible "Step N" labels are removed in favour of the canvas state badge.
    assert "<p class=\"step-label\">Step 2</p>" not in html
    assert "<p class=\"step-label\">Step 3</p>" not in html
    assert "<p class=\"step-label\">Step 4</p>" not in html


def test_review_step_contains_local_control_room_panel():
    html = _read("index.html")
    review_block = html[html.index('id="review-flow"'):html.index('id="generate-flow"')]

    assert 'id="local-run-panel"' in review_block
    assert 'id="local-run-validate-blueprint"' in review_block
    assert 'id="local-run-generate"' in review_block
    assert 'id="local-run-validate-app"' in review_block
    assert 'id="local-run-start-backend"' in review_block
    assert 'id="local-run-stop-backend"' in review_block
    assert 'id="local-run-start-frontend"' in review_block
    assert 'id="local-run-stop-frontend"' in review_block
    assert 'id="local-run-process-status"' in review_block
    assert 'id="local-run-results"' in review_block
    assert 'id="local-run-log"' in review_block
    assert 'class="local-run-panel workspace-card build-card"' in review_block
    assert 'class="workspace-card run-card"' in review_block
    assert "Static mode. Start the Builder server" in review_block
    assert "Safety details" in review_block
    assert "No GitHub, deployment, arbitrary shell commands" in review_block
    assert "fixed Makefile targets" in review_block


def test_app_mjs_calls_only_local_run_lifecycle_endpoints():
    script = _read("app.mjs")

    assert "local-run/${action}" in script
    assert '"validate-blueprint"' in script
    assert '"generate"' in script
    assert '"validate-app"' in script
    assert '"start-service"' in script
    assert '"stop-service"' in script
    assert "localRunRequest" in script
    assert "run_id: localRunState.runId" in script
    validate_app = _extract_function(script, "validateLocalRunApp")
    assert 'localRunRequest("validate-app", { run_id: localRunState.runId })' in validate_app


def test_static_mode_disables_local_control_room_until_planner_and_blueprint():
    script = _read("app.mjs")
    fn = _extract_function(script, "updateLocalRunAvailability")

    assert fn is not None
    assert "plannerAvailable" in fn
    assert "hasBlueprint" in fn
    assert "Static mode. Start the Builder server" in fn
    assert "Apply an assistant proposal" in fn
    assert "localRunValidateBlueprintButton.disabled = !canUseServer" in fn
    assert "localRunGenerateButton.disabled = !canUseServer" in fn
    assert "localRunValidateAppButton.disabled = !canUseServer || !localRunState.runId" in fn


def test_static_mode_disables_service_controls_until_generated_run():
    script = _read("app.mjs")
    fn = _extract_function(script, "updateServiceButtons")

    assert fn is not None
    assert "localRunStartBackendButton.disabled = !canUseServer || !hasRun || backendActive" in fn
    assert "localRunStopBackendButton.disabled = !canUseServer || !hasRun || !backendActive" in fn
    assert "localRunStartFrontendButton.disabled = !canUseServer || !hasRun || frontendActive" in fn
    assert "localRunStopFrontendButton.disabled = !canUseServer || !hasRun || !frontendActive" in fn


def test_service_status_urls_logs_and_handlers_render():
    script = _read("app.mjs")
    render_status = _extract_function(script, "renderServiceStatus")
    control_service = _extract_function(script, "controlLocalRunService")
    render_result = _extract_function(script, "renderLocalRunResult")

    assert render_status is not None
    assert "App services" in render_status
    assert "Start to get link" in render_status
    assert "Generated app servers" not in render_status
    assert "URL appears after Start" not in render_status
    assert control_service is not None
    assert 'localRunRequest(action, { run_id: localRunState.runId, service })' in control_service
    assert "localRunStartBackendButton?.addEventListener" in script
    assert "localRunStopBackendButton?.addEventListener" in script
    assert "localRunStartFrontendButton?.addEventListener" in script
    assert "localRunStopFrontendButton?.addEventListener" in script
    assert "scheduleServiceStatusPoll" in script
    assert 'localRunRequest("service-status", { run_id: localRunState.runId, service })' in script
    assert "Ready link:" in render_result
    assert "stdout" in render_result
    assert "stderr" in render_result
    assert "Advanced logs" in render_result


def test_step_4_manual_fallback_keeps_yaml_and_cli_export_path():
    html = _read("index.html")
    step4_block = html[html.index('id="generate-flow"'):html.index('id="existing-repo-flow"')]
    script = _read("app.mjs")
    render_export = _extract_function(script, "renderExportSummary")

    assert 'id="export-summary"' in step4_block
    assert 'class="advanced-drawer export-advanced-drawer"' in step4_block
    assert 'id="copy-yaml-export"' in step4_block
    assert 'id="download-yaml-export"' in step4_block
    assert 'id="copy-cli-commands"' in step4_block
    assert "Advanced: YAML, CLI, logs" in step4_block
    assert "Manual CLI commands" in step4_block
    assert render_export is not None
    assert "No local Builder run yet" in render_export
    assert "Static browser mode and offline sharing still work" in render_export
    assert "plannerCommands.length ? plannerCommands : preview.commands" in render_export


def test_step_4_local_run_summary_shows_path_validation_and_next_commands():
    script = _read("app.mjs")
    render_export = _extract_function(script, "renderExportSummary")

    assert render_export is not None
    assert "Local run summary" in render_export
    assert "Generated path" in render_export
    assert "Validation status" in render_export
    assert "make validate passed" in render_export
    assert "make validate failed" in render_export
    assert "make validate not run yet" in render_export
    assert "Copyable next commands" in render_export
    assert "make run-backend" in render_export
    assert "make run-frontend" in render_export


def test_local_run_results_render_status_path_logs_and_commands():
    script = _read("app.mjs")
    fn = _extract_function(script, "renderLocalRunResult")

    assert fn is not None
    assert "Generated path" in fn
    assert "Exit code" in fn
    assert "Equivalent command" not in fn
    assert "stdout" in fn
    assert "stderr" in fn
    assert "advancedLink" in fn
    assert "timed_out" in fn
    assert "truncated" in fn
    assert "renderExportSummary" in fn
    assert "const hasExitCode = result.exit_code !== undefined && result.exit_code !== null" in fn
    assert "${hasExitCode ? ` · exit ${result.exit_code}` : \"\"}" in fn


def test_local_run_results_append_assistant_activity_narration():
    script = _read("app.mjs")
    finish = _extract_function(script, "finishLocalRun")
    activity = _extract_function(script, "assistantActivityMessageForLocalRun")
    service = _extract_function(script, "serviceActivityMessage")

    assert finish is not None
    assert "appendAssistantActivityForLocalRun(result)" in finish
    assert activity is not None
    assert "Blueprint validation passed. Next: generate the app locally." in activity
    assert "Blueprint validation failed" in activity
    assert "Generated app at" in activity
    assert "Generate failed" in activity
    assert "make validate passed" in activity
    assert "make validate failed" in activity
    assert "exit code" in activity
    assert "See Local Control Room" in activity
    assert "service-status" in activity
    assert service is not None
    assert "is running at" in service
    assert "is stopped" in service
    assert "${action} failed" in service


def test_no_duplicate_conflicting_generate_step_messaging():
    html = _read("index.html")
    step4_block = html[html.index('id="generate-flow"'):html.index('id="existing-repo-flow"')]

    # Slice A removed the wizard nav; the assertion just confirms the legacy "Generate" tab is gone for good.
    assert '<nav class="flow-rail"' not in html
    assert "Generate and run locally" not in step4_block
    assert "Manual CLI commands" in step4_block
    assert "Advanced: YAML, CLI, logs" in step4_block
    # Slice 8E reframed the description to make local Run the recommended path.
    assert "local Validate" in step4_block


def test_styles_define_local_run_panel():
    css = _read("styles.css")

    for selector in (
        ".plan-build-run-workspace",
        ".workspace-card",
        ".workspace-step-number",
        ".advanced-drawer",
        ".export-advanced-drawer",
        ".plan-card",
        ".build-card",
        ".run-card",
        ".local-run-panel",
        ".export-summary",
        ".export-card",
        ".local-run-empty-state",
        ".local-run-result",
        ".local-run-result.pending",
        ".compact-status-row",
        ".status-chip",
        ".next-action-row",
        ".local-run-process-status",
        ".service-status",
        ".service-status.starting",
        ".local-run-result.success",
        ".local-run-result.error",
        "#local-run-log",
    ):
        assert selector in css



def test_slice_c_build_run_has_single_primary_next_action_and_secondary_controls():
    html = _read("index.html")
    review_block = html[html.index('id="review-flow"'):html.index('id="generate-flow"')]

    assert review_block.count('id="build-primary-action"') == 1
    assert 'id="build-next-action"' in review_block
    assert 'All build actions' in review_block
    assert 'class="inline-advanced secondary-build-actions-details"' in review_block
    assert 'class="inline-advanced service-controls-details"' in review_block
    assert 'Use the main next-action button above to start or open the app' in review_block


def test_slice_c_compute_next_step_progresses_through_guided_build_run_flow():
    script = _read("app.mjs")
    fn = _extract_function(script, "computeNextStep")

    assert fn is not None
    for expected in (
        'label: "Validate Blueprint"',
        'label: "Generate app locally"',
        'label: "Run app checks"',
        'id: "start-app", label: "Start app"',
        'id: "open-app", label: "Open app"',
    ):
        assert expected in fn
    assert 'action: validateLocalRunBlueprint' in fn
    assert 'action: generateLocalRunApp' in fn
    assert 'action: validateLocalRunApp' in fn
    assert 'action: startLocalRunApp' in fn


def test_slice_c_service_copy_and_open_app_are_human_and_reachable_only():
    script = _read("app.mjs")
    service_label = _extract_function(script, "serviceStatusLabel")
    update_row = _extract_function(script, "updateServiceRow")
    render_status = _extract_function(script, "renderServiceStatus")

    assert service_label is not None
    assert "Backend ready" in service_label
    assert "Frontend ready" in service_label
    assert "failed" in service_label
    assert update_row is not None
    assert 'if (running && url)' in update_row
    assert 'frontendOpenLink.hidden = true' in update_row
    assert render_status is not None
    assert 'status === "running" && result?.url' in render_status
    assert "Start to get link" in render_status


def test_slice_c_errors_point_to_advanced_logs_without_default_raw_log_dump():
    html = _read("index.html")
    script = _read("app.mjs")
    render_result = _extract_function(script, "renderLocalRunResult")

    assert 'id="advanced-logs"' in html
    assert render_result is not None
    assert 'href="#advanced-logs"' in render_result
    assert "Advanced logs" in render_result
    assert "Equivalent command" not in render_result
    # Raw streams are still captured into the Advanced log pre, not rendered as default result blocks.
    assert "localRunLog.textContent" in render_result
    assert "[stdout]" in render_result and "[stderr]" in render_result


def test_slice_c_right_rail_next_action_sync_uses_start_app_copy():
    script = _read("app.mjs")
    hud = _extract_function(script, "hudNextStepCopy")

    assert hud is not None
    assert '"start-app": "Start app."' in hud
    assert "Starts backend, then frontend" in hud


def test_slice_c1_start_app_orchestrates_backend_then_frontend_with_existing_endpoints():
    script = _read("app.mjs")
    fn = _extract_function(script, "startLocalRunApp")

    assert fn is not None
    assert 'localRunRequest("start-service", { run_id: localRunState.runId, service: "backend" })' in fn
    assert 'waitForLocalRunService("backend", backend)' in fn
    assert 'localRunRequest("start-service", { run_id: localRunState.runId, service: "frontend" })' in fn
    assert 'waitForLocalRunService("frontend", frontend)' in fn
    assert fn.index('service: "backend"') < fn.index('service: "frontend"')
    assert "Starting backend…" in fn
    assert "Starting frontend…" in fn
    assert "App is running." in fn


def test_slice_c1_start_app_failure_stops_and_points_to_advanced_logs():
    script = _read("app.mjs")
    fn = _extract_function(script, "startLocalRunApp")
    waiter = _extract_function(script, "waitForLocalRunService")

    assert fn is not None and waiter is not None
    assert "Backend failed to start. See Advanced/logs." in fn
    assert "Frontend failed to start. See Advanced/logs." in fn
    assert "Frontend failed to start. See Advanced/logs." in waiter or "did not become reachable. See Advanced/logs." in waiter
    assert "finishLocalRun({ step: \"start-service\", service, ok: false" in fn
    assert "exit_code: null" in fn


def test_slice_c1_start_app_reuses_service_status_polling_and_no_new_endpoints():
    script = _read("app.mjs")
    waiter = _extract_function(script, "waitForLocalRunService")

    assert waiter is not None
    assert 'localRunRequest("service-status", { run_id: localRunState.runId, service })' in waiter
    assert '"/api/planner/local-run/start-app"' not in script
    assert 'startLocalRunApp' in script
    assert 'controlLocalRunService' in script


def test_review_step_demotes_export_to_secondary_when_local_run_available():
    """After 2026-05-23: 'Continue to export / next steps' is no longer the primary
    action at the end of Review. The wizard button is a secondary 'Export / CLI'
    affordance; the primary happy path is the Build/Run next-action button above.
    """
    html = _read("index.html")
    review_block = html[html.index('id="review-flow"'):html.index('id="generate-flow"')]

    # The old primary "Continue to export / next steps" button is gone.
    assert "Continue to export / next steps" not in review_block
    assert 'class="primary-button" data-step-target="generate"' not in review_block

    # A secondary export affordance still exists and is reachable.
    assert 'data-step-target="generate"' in review_block
    assert "secondary-export-action" in review_block
    assert "Export / CLI" in review_block

    # Local run is still the primary happy-path call-to-action.
    assert 'id="build-primary-action"' in review_block
    assert 'class="primary-button next-action-button"' in review_block


def test_export_step_describes_itself_as_secondary_and_advanced():
    """The export/CLI heading is no longer framed as the required next step
    after Review. Static/manual users can still discover it.
    """
    html = _read("index.html")
    step4_block = html[html.index('id="generate-flow"'):html.index('id="existing-repo-flow"')]

    # The export step still copies/downloads YAML and shows CLI commands
    # (so static/manual users keep their fallback path).
    assert "Blueprint YAML export" in step4_block
    assert "Manual CLI commands" in step4_block

    # But the framing makes clear that the local Run flow is the recommended path.
    assert (
        "local Validate" in step4_block or "local Build" in step4_block or "local run" in step4_block
    )
    assert "Optional" in step4_block or "secondary" in step4_block.lower()


def test_secondary_export_button_styles_register_as_demoted():
    css = _read("styles.css")
    # The new CSS class must apply less visual weight than primary-button.
    assert ".secondary-export-action" in css

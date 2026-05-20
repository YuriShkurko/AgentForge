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
    nav = html[html.index('<nav class="flow-rail"'):html.index('</nav>')]
    step4_block = html[html.index('id="generate-flow"'):html.index('id="existing-repo-flow"')]

    assert "Review &amp; Build" in nav
    assert "Export / Next Steps" in nav
    assert "Review" in nav
    assert ">Generate<" not in nav
    assert "Review &amp; build the app plan" in html
    assert "Export / next steps" in step4_block
    assert "Generate and run locally" not in step4_block


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
    assert "Static browser mode" in review_block
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
    assert "Static browser mode" in fn
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
    assert "Generated app servers" in render_status
    assert "URL appears after Start" in render_status
    assert control_service is not None
    assert 'localRunRequest(action, { run_id: localRunState.runId, service })' in control_service
    assert "localRunStartBackendButton?.addEventListener" in script
    assert "localRunStopBackendButton?.addEventListener" in script
    assert "localRunStartFrontendButton?.addEventListener" in script
    assert "localRunStopFrontendButton?.addEventListener" in script
    assert "scheduleServiceStatusPoll" in script
    assert 'localRunRequest("service-status", { run_id: localRunState.runId, service })' in script
    assert "URL:" in render_result
    assert "stdout" in render_result
    assert "stderr" in render_result


def test_step_4_manual_fallback_keeps_yaml_and_cli_export_path():
    html = _read("index.html")
    step4_block = html[html.index('id="generate-flow"'):html.index('id="existing-repo-flow"')]
    script = _read("app.mjs")
    render_export = _extract_function(script, "renderExportSummary")

    assert 'id="export-summary"' in step4_block
    assert 'id="copy-yaml-export"' in step4_block
    assert 'id="download-yaml-export"' in step4_block
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
    assert "Equivalent command" in fn
    assert "stdout" in fn
    assert "stderr" in fn
    assert "timed_out" in fn
    assert "truncated" in fn
    assert "renderExportSummary" in fn


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

    assert ">Generate<" not in html[html.index('<nav class="flow-rail"'):html.index('</nav>')]
    assert "Generate and run locally" not in step4_block
    assert "Manual CLI commands" in step4_block
    assert "The CLI remains the source of truth" in step4_block


def test_styles_define_local_run_panel():
    css = _read("styles.css")

    for selector in (
        ".local-run-panel",
        ".export-summary",
        ".export-card",
        ".local-run-result",
        ".local-run-process-status",
        ".service-status",
        ".service-status.starting",
        ".local-run-result.success",
        ".local-run-result.error",
        "#local-run-log",
    ):
        assert selector in css

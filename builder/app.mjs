import { analyzerCommandExamples, archetypes, createDefaultCustomization, exampleIdeas, extensionCommandExamples, getArchetypeFamilyLabel, getGenerationPreview, modules, parseAnalyzerReport, parseExtensionPlan, createBlueprint, createBlueprintYaml, sanitizeName, validateBuilderState } from "./blueprint-builder.mjs";

const form = {
  name: document.querySelector("#app-name"),
  displayName: document.querySelector("#display-name"),
  description: document.querySelector("#description"),
  targetUser: document.querySelector("#target-user"),
  archetype: document.querySelector("#archetype"),
  actionAccept: document.querySelector("#action-accept"),
  actionSkip: document.querySelector("#action-skip"),
  actionMaybe: document.querySelector("#action-maybe"),
  notificationMode: document.querySelector("#notification-mode"),
  llmMode: document.querySelector("#llm-mode"),
  widgetPreset: document.querySelector("#widget-preset"),
  workspaceEnabled: document.querySelector("#workspace-enabled"),
  fixtureEnabled: document.querySelector("#fixture-enabled"),
};

const moduleList = document.querySelector("#module-list");
const yamlPreview = document.querySelector("#yaml-preview");
const planPreview = document.querySelector("#plan-preview");
const statusPill = document.querySelector("#status-pill");
const validationSummary = document.querySelector("#validation-summary");
const copyButton = document.querySelector("#copy-yaml");
const downloadButton = document.querySelector("#download-yaml");
const copyYamlExportButton = document.querySelector("#copy-yaml-export");
const downloadYamlExportButton = document.querySelector("#download-yaml-export");
const copyCliCommandsButton = document.querySelector("#copy-cli-commands");
const copyLocalRunLogButton = document.querySelector("#copy-local-run-log");
const plannerStatus = document.querySelector("#planner-status");
const plannerIdea = document.querySelector("#planner-idea");
const draftButton = document.querySelector("#draft-blueprint");
const clarifyButton = document.querySelector("#clarify-idea");
const clarificationPanel = document.querySelector("#clarification-panel");
const clarificationQuestions = document.querySelector("#clarification-questions");
const submitAnswersButton = document.querySelector("#submit-answers");
const draftPanel = document.querySelector("#draft-panel");
const draftSummary = document.querySelector("#draft-summary");
const plannerAssumptions = document.querySelector("#planner-assumptions");
const plannerWarnings = document.querySelector("#planner-warnings");
const plannerRefine = document.querySelector("#planner-refine");
const refineButton = document.querySelector("#refine-blueprint");
const validateButton = document.querySelector("#validate-blueprint");
const ideaExamples = document.querySelector("#idea-examples");
const draftChips = document.querySelector("#draft-chips");
const analyzerCommands = document.querySelector("#analyzer-commands");
const extensionCommands = document.querySelector("#extension-commands");
const analyzerReport = document.querySelector("#analyzer-report");
const extensionPlanReport = document.querySelector("#extension-plan-report");
const parseAnalyzerButton = document.querySelector("#parse-analyzer-report");
const parseExtensionPlanButton = document.querySelector("#parse-extension-plan");
const copyBlueprintSeedButton = document.querySelector("#copy-blueprint-seed");
const analyzerOutput = document.querySelector("#analyzer-output");
const extensionPlanOutput = document.querySelector("#extension-plan-output");
const generationPreview = document.querySelector("#generation-preview");
const summaryName = document.querySelector("#summary-name");
const summaryArchetype = document.querySelector("#summary-archetype");
const summaryStatus = document.querySelector("#summary-status");
const planReadyChip = document.querySelector("#plan-ready-chip");
const blueprintValidChip = document.querySelector("#blueprint-valid-chip");
const buildBlueprintChip = document.querySelector("#build-blueprint-chip");
const buildGeneratedChip = document.querySelector("#build-generated-chip");
const buildChecksChip = document.querySelector("#build-checks-chip");
const buildNextAction = document.querySelector("#build-next-action");
const buildPrimaryAction = document.querySelector("#build-primary-action");
const backendStatusChip = document.querySelector("#backend-status-chip");
const frontendStatusChip = document.querySelector("#frontend-status-chip");
const planSummaryApp = document.querySelector("#plan-summary-app");
const planSummaryType = document.querySelector("#plan-summary-type");
const planSummaryEntities = document.querySelector("#plan-summary-entities");
const planSummaryProviders = document.querySelector("#plan-summary-providers");
const planSummaryStatus = document.querySelector("#plan-summary-status");
const planSummaryExtras = document.querySelector("#plan-summary-extras");
const assistantHistoryDetails = document.querySelector("#assistant-history");
const assistantHistoryCount = document.querySelector("#assistant-history-count");
const assistantCurrentState = document.querySelector("#assistant-current-state");
const assistantCurrentStateLabel = document.querySelector("#assistant-current-state-label");
const assistantNextStepLabel = document.querySelector("#assistant-next-step-label");
const assistantNextStepDetail = document.querySelector("#assistant-next-step-detail");
const assistantProposalPointer = document.querySelector("#assistant-proposal-pointer");
const assistantAppSummary = document.querySelector("#assistant-app-summary");
const assistantAppName = document.querySelector("#assistant-app-name");
const assistantAppType = document.querySelector("#assistant-app-type");
const assistantAppEntities = document.querySelector("#assistant-app-entities");
const assistantServiceSummary = document.querySelector("#assistant-service-summary");
const assistantBackendChip = document.querySelector("#assistant-backend-chip");
const assistantFrontendChip = document.querySelector("#assistant-frontend-chip");
const assistantOpenAppLink = document.querySelector("#assistant-open-app-link");
const assistantThinking = document.querySelector("#assistant-thinking");
const heroComposer = document.querySelector("#hero-composer");
const heroComposerInput = document.querySelector("#hero-composer-input");
const heroComposerSend = document.querySelector("#hero-composer-send");
const heroComposerThinking = document.querySelector("#hero-composer-thinking");
const frontendOpenLink = document.querySelector("#frontend-open-link");
const backendMeta = document.querySelector("#backend-meta");
const serviceControlsDetails = document.querySelector(".service-controls-details");
const serviceRows = {
  backend: document.querySelector('.service-row[data-service="backend"]'),
  frontend: document.querySelector('.service-row[data-service="frontend"]'),
};
const builderShell = document.querySelector("#builder-shell");
const canvasStateBadge = document.querySelector("#canvas-state-badge");
const canvasStateLabel = document.querySelector("#canvas-state-label");
const canvasStateDetail = document.querySelector("#canvas-state-detail");
const canvasThinkingOverlay = document.querySelector("#canvas-thinking-overlay");
const canvasThinkingEcho = document.querySelector("#canvas-thinking-echo");
const canvasThinkingHeadline = document.querySelector("#canvas-thinking-headline");
const canvasThinkingSubline = document.querySelector("#canvas-thinking-subline");
const canvasThinkingExpectation = document.querySelector("#canvas-thinking-expectation");
const resetSessionButton = document.querySelector("#reset-session");
const summaryCapabilityGroups = document.querySelector("#summary-capability-groups");
const summaryCommands = document.querySelector("#summary-commands");
const customizePanel = document.querySelector("#customize-panel");
const customizeFamily = document.querySelector("#customize-family");
const customizeFields = document.querySelector("#customize-fields");
const resetCustomizationButton = document.querySelector("#reset-customization");
const assistantPanel = document.querySelector("#assistant-panel");
const assistantStatus = document.querySelector("#assistant-status");
const assistantLog = document.querySelector("#assistant-log");
const assistantQuestions = document.querySelector("#assistant-questions");
const assistantProposal = document.querySelector("#assistant-proposal");
const assistantGuidance = document.querySelector("#assistant-guidance");
const assistantForm = document.querySelector("#assistant-form");
const assistantInput = document.querySelector("#assistant-input");
const assistantSendButton = document.querySelector("#assistant-send");
const assistantResetButton = document.querySelector("#assistant-reset");
const localRunPanel = document.querySelector("#local-run-panel");
const localRunStatus = document.querySelector("#local-run-status");
const localRunValidateBlueprintButton = document.querySelector("#local-run-validate-blueprint");
const localRunGenerateButton = document.querySelector("#local-run-generate");
const localRunValidateAppButton = document.querySelector("#local-run-validate-app");
const localRunStartBackendButton = document.querySelector("#local-run-start-backend");
const localRunStopBackendButton = document.querySelector("#local-run-stop-backend");
const localRunStartFrontendButton = document.querySelector("#local-run-start-frontend");
const localRunStopFrontendButton = document.querySelector("#local-run-stop-frontend");
const localRunProcessStatus = document.querySelector("#local-run-process-status");
const localRunResults = document.querySelector("#local-run-results");
const localRunLog = document.querySelector("#local-run-log");
const exportSummary = document.querySelector("#export-summary");

const plannerApi = window.location.protocol.startsWith("http") ? `${window.location.origin}/api/planner` : "http://127.0.0.1:8765/api/planner";

const SESSION_STORAGE_KEY = "agentforge.builder.session.v1";
const SESSION_SCHEMA_VERSION = 1;
const MAX_PERSISTED_HISTORY = 40;
const MAX_PERSISTED_STEP_DETAIL = 280;
const SECRET_KEY_PATTERN = /(secret|token|password|api[_-]?key|bearer|authorization)/i;

const BUILD_OP_PROGRESS = {
  "validate-blueprint": {
    headline: "Validating plan…",
    subline: "Checking the Blueprint before we generate files.",
    expectation: "Usually a few seconds.",
    busy: "Validating plan…",
  },
  generate: {
    headline: "Generating your app…",
    subline: "Writing backend, frontend, and tests.",
    expectation: "May take 20–60 seconds on first install.",
    busy: "Generating your app…",
  },
  "validate-app": {
    headline: "Running app checks…",
    subline: "Making sure the generated app builds cleanly.",
    expectation: "Usually 10–30 seconds.",
    busy: "Running app checks…",
  },
  "start-app": {
    headline: "Starting your app…",
    subline: "Backend first, then the frontend.",
    expectation: "Starting services… this can take a moment (10–30s).",
    busy: "Starting your app…",
  },
  "start-service": {
    headline: "Starting service…",
    subline: "Bringing the service up.",
    expectation: "Usually a few seconds.",
    busy: "Starting service…",
  },
  "stop-service": {
    headline: "Stopping service…",
    subline: "Shutting the service down.",
    expectation: "Usually a few seconds.",
    busy: "Stopping service…",
  },
};

function isInsideAdvancedRegion(node) {
  if (!node || !node.closest) return false;
  return Boolean(
    node.closest("#advanced-drawer") ||
    node.closest(".inline-advanced") ||
    node.closest(".assistant-history-details") ||
    node.closest(".plan-summary-extras") ||
    node.closest(".customize-details") ||
    node.closest(".assistant-proposal-changes") ||
    node.closest(".assistant-guidance-raw")
  );
}

function safeReadSession() {
  try {
    const raw = window.localStorage?.getItem(SESSION_STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    if (!parsed || parsed.version !== SESSION_SCHEMA_VERSION) return null;
    return parsed;
  } catch {
    return null;
  }
}

function safeWriteSession(snapshot) {
  try {
    window.localStorage?.setItem(SESSION_STORAGE_KEY, JSON.stringify(snapshot));
  } catch {
    // Quota or disabled storage — fail silently; Builder still works in-memory.
  }
}

function safeClearSession() {
  try {
    window.localStorage?.removeItem(SESSION_STORAGE_KEY);
  } catch {
    // ignore
  }
}

function sanitizeStepForPersistence(step) {
  if (!step || typeof step !== "object") return null;
  const errors = Array.isArray(step.errors)
    ? step.errors.filter(Boolean).map((value) => String(value).slice(0, MAX_PERSISTED_STEP_DETAIL))
    : [];
  return {
    step: step.step,
    ok: Boolean(step.ok),
    status: step.status || (step.ok ? "ok" : "failed"),
    exit_code: step.exit_code ?? null,
    service: step.service || null,
    generated_path: step.generated_path || null,
    run_id: step.run_id || null,
    errors,
    url: step.url || null,
    timed_out: Boolean(step.timed_out),
    truncated: Boolean(step.truncated),
  };
}

function sanitizeServiceForPersistence(service) {
  if (!service || typeof service !== "object") return null;
  return {
    status: service.status || "stopped",
    service: service.service || null,
    url: service.url || null,
    ok: service.ok !== false,
  };
}

function sanitizeSessionStateForPersistence(state) {
  if (!state || typeof state !== "object") return null;
  const proposal = state.proposal && state.proposal.blueprint
    ? { blueprint: state.proposal.blueprint, changes: Array.isArray(state.proposal.changes) ? state.proposal.changes : [] }
    : null;
  return {
    status: state.status || null,
    proposal,
    // Drop large internal fields (raw turns, scratch buffers). The applied
    // blueprint is recoverable from plannerBlueprint; the assistant turn
    // history is recoverable by reading the truncated log buffer.
  };
}

function sanitizeLogEntriesForPersistence() {
  if (!assistantLog) return [];
  const entries = Array.from(assistantLog.querySelectorAll(".assistant-message"));
  const recent = entries.slice(-MAX_PERSISTED_HISTORY);
  return recent.map((entry) => {
    const role = entry.classList.contains("assistant-message-user")
      ? "user"
      : entry.classList.contains("assistant-message-activity")
        ? "activity"
        : "assistant";
    const body = entry.querySelector(".assistant-message-body");
    const text = body ? String(body.textContent || "") : "";
    if (SECRET_KEY_PATTERN.test(text)) return { role, text: "[redacted line]" };
    return { role, text: text.slice(0, 600) };
  });
}

function collectSessionSnapshot() {
  return {
    version: SESSION_SCHEMA_VERSION,
    savedAt: Date.now(),
    activeStep,
    canvasState: builderShell?.dataset.canvasState || null,
    plannerBlueprint,
    plannerYaml: plannerYaml ? plannerYaml.slice(0, 20000) : "",
    plannerCommands: Array.isArray(plannerCommands) ? plannerCommands.slice(0, 24) : [],
    assistantSessionState: sanitizeSessionStateForPersistence(assistantSessionState),
    assistantLog: sanitizeLogEntriesForPersistence(),
    lastUserPrompt: typeof lastUserPrompt === "string" ? lastUserPrompt.slice(0, 600) : "",
    localRunState: {
      runId: localRunState.runId,
      generatedPath: localRunState.generatedPath,
      steps: (localRunState.steps || []).map(sanitizeStepForPersistence).filter(Boolean),
      services: {
        backend: sanitizeServiceForPersistence(localRunState.services?.backend),
        frontend: sanitizeServiceForPersistence(localRunState.services?.frontend),
      },
    },
  };
}

let sessionPersistDebounce = null;
let sessionResetInFlight = false;
function persistSessionSoon() {
  if (sessionResetInFlight) return;
  if (sessionPersistDebounce) return;
  sessionPersistDebounce = window.setTimeout(() => {
    sessionPersistDebounce = null;
    if (sessionResetInFlight) return;
    safeWriteSession(collectSessionSnapshot());
  }, 120);
}

function restoreSessionFromStorage() {
  const snapshot = safeReadSession();
  if (!snapshot) return false;
  try {
    if (snapshot.plannerBlueprint) {
      plannerBlueprint = snapshot.plannerBlueprint;
      plannerYaml = snapshot.plannerYaml || "";
      plannerCommands = Array.isArray(snapshot.plannerCommands) ? snapshot.plannerCommands : [];
      applyBlueprintToForm(plannerBlueprint);
    }
    if (snapshot.assistantSessionState) {
      assistantSessionState = snapshot.assistantSessionState;
      if (assistantSessionState?.proposal?.blueprint) {
        renderAssistantProposal(assistantSessionState.proposal);
      } else if (assistantSessionState?.status === "applied") {
        setAssistantApplied(true);
      }
    }
    if (Array.isArray(snapshot.assistantLog) && snapshot.assistantLog.length > 0) {
      snapshot.assistantLog.forEach((entry) => {
        if (entry && entry.text) appendAssistantMessage(entry.role || "assistant", entry.text);
      });
      appendAssistantMessage("activity", "Restored from your previous session. Re-checking live services…");
    }
    if (snapshot.localRunState) {
      const restoredLocal = snapshot.localRunState;
      localRunState = {
        runId: restoredLocal.runId || null,
        generatedPath: restoredLocal.generatedPath || null,
        steps: Array.isArray(restoredLocal.steps) ? restoredLocal.steps.map(sanitizeStepForPersistence).filter(Boolean) : [],
        services: {
          backend: sanitizeServiceForPersistence(restoredLocal.services?.backend),
          frontend: sanitizeServiceForPersistence(restoredLocal.services?.frontend),
        },
      };
    }
    if (typeof snapshot.lastUserPrompt === "string") lastUserPrompt = snapshot.lastUserPrompt;
    if (snapshot.activeStep && typeof snapshot.activeStep === "string") activeStep = snapshot.activeStep;
    return true;
  } catch {
    return false;
  }
}

async function resetLocalRunServicesForSessionReset() {
  if (!plannerAvailable) return;
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), 2500);
  try {
    await fetch(`${plannerApi}/local-run/reset-session`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ run_id: localRunState.runId }),
      signal: controller.signal,
    });
  } catch {
    // Reset must still clear local UI state even if serve-builder is offline.
  } finally {
    window.clearTimeout(timeout);
  }
}

async function resetBuilderSession({ reload = true } = {}) {
  await resetLocalRunServicesForSessionReset();
  // Set the reset flag BEFORE clearing storage so the beforeunload flush
  // (triggered by the reload below) cannot re-write the snapshot we just
  // erased. Without this guard the page would reload back into the same
  // restored state and reset would appear to do nothing.
  sessionResetInFlight = true;
  safeClearSession();
  if (sessionPersistDebounce) {
    window.clearTimeout(sessionPersistDebounce);
    sessionPersistDebounce = null;
  }
  if (!reload) return;
  // Reload to a clean canvas; the planner status check + canvas state recompute.
  window.location.reload();
}
let plannerAvailable = false;
let plannerBlueprint = null;
let plannerYaml = "";
let plannerCommands = [];
let activeQuestions = [];
let parsedBlueprintSeed = "";
let activeStep = "start";
let customizationValues = null;
let customizationDirty = false;
let renderedCustomizationArchetype = "";
let assistantSessionState = null;
let assistantBusy = false;
let assistantMode = "static";
let assistantLiveProvider = false;
let localRunBusy = false;
let localRunServicePollTimer = null;
let localRunState = { runId: null, generatedPath: null, steps: [], services: { backend: null, frontend: null } };
let assistantSubmissionInFlight = false;
let activeBuildOp = null;
let lastUserPrompt = "";

function state() {
  return {
    name: form.name.value,
    displayName: form.displayName.value,
    description: form.description.value,
    targetUser: form.targetUser.value,
    archetype: form.archetype.value,
    selectedModules: [...document.querySelectorAll("[data-module]:checked")].map((item) => item.dataset.module),
    actionAccept: form.actionAccept.value,
    actionSkip: form.actionSkip.value,
    actionMaybe: form.actionMaybe.value,
    notificationMode: form.notificationMode.value,
    llmMode: form.llmMode.value,
    widgetPreset: form.widgetPreset.value,
    workspaceEnabled: form.workspaceEnabled.checked,
    fixtureEnabled: form.fixtureEnabled.checked,
    customization: customizationDirty && customizationValues ? customizationValues : createDefaultCustomizationFromForm(),
  };
}

function createDefaultCustomizationFromForm() {
  return createDefaultCustomization(
    {
      name: form.name.value,
      displayName: form.displayName.value,
      description: form.description.value,
      targetUser: form.targetUser.value,
    },
    form.archetype.value,
  );
}

function renderArchetypes() {
  form.archetype.innerHTML = archetypes
    .map((item) => `<option value="${item.id}" ${item.status === "planned" ? "disabled" : ""}>${item.label}${item.status === "planned" ? " (planned)" : ""}</option>`)
    .join("");
}

function renderEntryHelpers() {
  ideaExamples.innerHTML = exampleIdeas
    .map((idea) => `<button class="example-chip" type="button" data-idea="${escapeHtml(idea)}">${escapeHtml(idea)}</button>`)
    .join("");
  analyzerCommands.innerHTML = analyzerCommandExamples
    .map((command) => `<code>${escapeHtml(command)}</code>`)
    .join("");
  extensionCommands.innerHTML = extensionCommandExamples
    .map((command) => `<code>${escapeHtml(command)}</code>`)
    .join("");
}

function renderModules() {
  const selectedArchetype = archetypes.find((item) => item.id === form.archetype.value) || archetypes[0];
  moduleList.innerHTML = modules
    .map((module) => {
      const required = selectedArchetype.required.includes(module.id);
      const checked = required || ["notification_action", "triage_ui", "agent_runtime", "workspace"].includes(module.id);
      const disabled = required || !module.supported;
      const label = required ? "required" : module.supported ? "optional" : "planned";
      return `
        <label class="module-card ${disabled ? "muted" : ""}">
          <input data-module="${module.id}" type="checkbox" ${checked ? "checked" : ""} ${disabled ? "disabled" : ""} />
          <span>
            <strong>${module.label}</strong>
            <small>${module.id} - ${label}</small>
          </span>
        </label>
      `;
    })
    .join("");
}

function renderCustomizationPanel(current, activeBlueprint = plannerBlueprint) {
  if (!customizePanel) return;
  customizeFamily.textContent = `Detected app family: ${getArchetypeFamilyLabel(current.archetype)}`;
  if (isModelDrivenBlueprint(activeBlueprint || current)) {
    renderedCustomizationArchetype = current.archetype;
    customizeFields.innerHTML = renderModelDrivenReviewSummary(activeBlueprint);
    return;
  }
  const currentDefaults = createDefaultCustomizationFromForm();
  if (!customizationDirty) customizationValues = currentDefaults;
  if (renderedCustomizationArchetype === current.archetype && customizationDirty) return;
  renderedCustomizationArchetype = current.archetype;
  const c = customizationDirty && customizationValues ? customizationValues : currentDefaults;
  const common = `
    <div class="customize-group wide"><h3>Common app details</h3></div>
    <label>App subtitle<input data-custom-path="app.subtitle" value="${escapeHtml(c.app?.subtitle || "")}" /></label>
    <label>Target user label<input data-custom-path="app.target_user_label" value="${escapeHtml(c.app?.target_user_label || "")}" /></label>
    <label>Workflow label<input data-custom-path="app.workflow_label" value="${escapeHtml(c.app?.workflow_label || "")}" /></label>
    <label>Workspace empty state<input data-custom-path="workspace.empty_state" value="${escapeHtml(c.workspace?.empty_state || "")}" /></label>
    <label class="wide">Agent starter prompts <span class="field-hint">One per line.</span><textarea data-custom-path="agent_starters">${escapeHtml((c.agent_starters || []).join("\n"))}</textarea></label>
  `;
  const archetypeFields = current.archetype === "project_workspace_app"
    ? `
      <div class="customize-group wide"><h3>Project workspace labels</h3></div>
      <label>Project singular<input data-custom-path="project_workspace.project_label.singular" value="${escapeHtml(c.project_workspace?.project_label?.singular || "")}" /></label>
      <label>Project plural<input data-custom-path="project_workspace.project_label.plural" value="${escapeHtml(c.project_workspace?.project_label?.plural || "")}" /></label>
      <label>Task singular<input data-custom-path="project_workspace.task_label.singular" value="${escapeHtml(c.project_workspace?.task_label?.singular || "")}" /></label>
      <label>Task plural<input data-custom-path="project_workspace.task_label.plural" value="${escapeHtml(c.project_workspace?.task_label?.plural || "")}" /></label>
      <label>Activity label<input data-custom-path="project_workspace.activity_label" value="${escapeHtml(c.project_workspace?.activity_label || "")}" /></label>
      <label>Sample workspace label<input data-custom-path="project_workspace.sample_data_label" value="${escapeHtml(c.project_workspace?.sample_data_label || "")}" /></label>
    `
    : `
      <div class="customize-group wide"><h3>Scoring / triage labels</h3></div>
      <label>Record singular<input data-custom-path="scoring.record_label.singular" value="${escapeHtml(c.scoring?.record_label?.singular || "")}" /></label>
      <label>Record plural<input data-custom-path="scoring.record_label.plural" value="${escapeHtml(c.scoring?.record_label?.plural || "")}" /></label>
      <label>Review queue label<input data-custom-path="scoring.review_queue_label" value="${escapeHtml(c.scoring?.review_queue_label || "")}" /></label>
      <label>Notification label<input data-custom-path="scoring.notification_label" value="${escapeHtml(c.scoring?.notification_label || "")}" /></label>
      <label>Sample data label<input data-custom-path="scoring.sample_data_label" value="${escapeHtml(c.scoring?.sample_data_label || "")}" /></label>
      <label>Scoring criteria labels <span class="field-hint">One per line.</span><textarea data-custom-path="scoring.criteria_labels">${escapeHtml((c.scoring?.criteria_labels || []).join("\n"))}</textarea></label>
    `;
  customizeFields.innerHTML = common + archetypeFields;
}

function readCustomizationInputs() {
  const defaults = createDefaultCustomizationFromForm();
  const next = JSON.parse(JSON.stringify(defaults));
  customizeFields?.querySelectorAll("[data-custom-path]").forEach((input) => {
    const path = input.dataset.customPath;
    const value = path === "agent_starters" || path === "scoring.criteria_labels"
      ? input.value.split("\n").map((item) => item.trim()).filter(Boolean)
      : input.value;
    setNested(next, path.split("."), value);
  });
  customizationValues = next;
  customizationDirty = true;
}

function setNested(target, path, value) {
  const key = path[0];
  if (path.length === 1) {
    target[key] = value;
    return;
  }
  target[key] = target[key] || {};
  setNested(target[key], path.slice(1), value);
}

function resetCustomization() {
  customizationValues = createDefaultCustomizationFromForm();
  customizationDirty = false;
  renderedCustomizationArchetype = "";
  clearPlannerDraft();
  updatePreview();
}

function updatePreview() {
  const current = state();
  const yaml = createBlueprintYaml(current);
  const issues = validateBuilderState(current);
  const preview = getGenerationPreview(current);
  yamlPreview.textContent = plannerYaml || yaml;
  planPreview.textContent = plannerCommands.length ? plannerCommands.join("\n") : preview.commands.join("\n");
  statusPill.textContent = issues.length ? `${issues.length} issue${issues.length === 1 ? "" : "s"}` : "Valid draft";
  statusPill.classList.toggle("warning", issues.length > 0);
  validationSummary.textContent = issues.length ? issues.join(" ") : "Blueprint source is ready for `agentforge plan`.";
  renderGenerationPreview(preview, plannerBlueprint);
  renderExportSummary(preview);
  renderBuildSummary(current, preview, issues, plannerBlueprint);
  renderCustomizationPanel(current, plannerBlueprint);
  updateLocalRunAvailability();
}

function renderBuildSummary(current, preview, issues, activeBlueprint = plannerBlueprint) {
  const modelSummary = modelDrivenSummary(activeBlueprint);
  summaryName.textContent = displayTitleForBlueprint(activeBlueprint, current.displayName || current.name || "Untitled app");
  summaryArchetype.textContent = modelSummary ? "Model-driven CRUD/workflow app" : plainArchetype(preview.archetype);
  summaryStatus.textContent = issues.length ? `${issues.length} issue${issues.length === 1 ? "" : "s"} to resolve` : plannerBlueprint ? "Plan ready" : "Ready for an app idea";
  renderPlanStatusChips(issues);
  renderPlanSummaryList(current, preview, issues, activeBlueprint);
  const groups = modelSummary ? modelDrivenCapabilityGroups(modelSummary) : capabilityGroups(preview);
  summaryCapabilityGroups.innerHTML = groups
    .map((group) => `
      <section>
        <h3>${escapeHtml(group.title)}</h3>
        <ul>${group.items.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>
      </section>
    `)
    .join("");
  summaryCommands.textContent = (plannerCommands.length ? plannerCommands : preview.commands).join("\n");
}

function plainArchetype(label) {
  return String(label || "Local app").replace("Pipeline", "app").replace("App", "app").replaceAll("_", " ");
}

function titleCaseWords(value) {
  return String(value || "")
    .replace(/[_-]+/g, " ")
    .replace(/\s+/g, " ")
    .trim()
    .toLowerCase()
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function cleanAppDisplayTitle(value, fallback = "Local App") {
  let title = String(value || "").replace(/[_-]+/g, " ").replace(/\s+/g, " ").trim();
  title = title
    .replace(/^(?:please\s+)?(?:i|we)\s+(?:want|need|would like)(?:\s+to)?\s+/i, "")
    .replace(/^(?:please\s+)?(?:build|create|make|generate)\s+(?:me\s+|us\s+)?(?:an?\s+)?/i, "")
    .replace(/^(?:an?\s+)?(?:app|workspace|dashboard|tool)\s+(?:to|for)\s+/i, "")
    .replace(/^(?:to\s+)?(?:manage|track|organize|monitor)\s+(?:my|our|the)?\s*/i, "")
    .trim();
  title = title.replace(/\bfinances\b/gi, "finance");
  const fallbackTitle = titleCaseWords(fallback || "Local App");
  title = titleCaseWords(title) || fallbackTitle;
  if (/\bfinance\b/i.test(title) && !/\b(manager|workspace|dashboard|app|tool)\b/i.test(title)) return `${title} Manager`;
  if (!/\b(workspace|manager|dashboard|app|tool|tracker|portal|console)\b/i.test(title)) return `${title} Workspace`;
  return title;
}

function displayTitleForBlueprint(blueprint, fallback = "Local App") {
  return cleanAppDisplayTitle(blueprint?.display_name || blueprint?.name || fallback, fallback);
}

function plainCapabilityLabel(value) {
  const labels = {
    agent_runtime: "Agent chat",
    provider_adapter: "Data adapter",
    pipeline: "Data pipeline",
    scoring_explanation: "Scoring explanations",
    notification_action: "Notification previews",
    triage_ui: "Triage actions",
    workspace: "Workspace dashboard",
    operations_ui: "Operations screen",
    persistence: "Local persistence",
    test: "Test harness",
  };
  return labels[value] || plainArchetype(value);
}

function capabilityGroups(preview) {
  const outputs = new Set(preview.outputs || []);
  const has = (text) => [...outputs].some((item) => item.toLowerCase().includes(text));
  const groups = [
    { title: "App foundation", items: ["FastAPI backend", "React frontend", "Local persistence"] },
    { title: "AI workflow", items: [] },
    { title: "Product surfaces", items: [] },
    { title: "Validation", items: ["Backend tests", "Frontend build/lint"] },
  ];
  if (has("agent")) groups[1].items.push("Scripted agent chat", "Typed tools");
  if (has("sample")) groups[2].items.push("Data import");
  if (has("scoring")) groups[2].items.push("Scoring explanations");
  if (has("notification")) groups[2].items.push("Notification previews", "Triage actions");
  if (has("workspace")) groups[2].items.push("Workspace dashboard");
  return groups.filter((group) => group.items.length > 0);
}

function isModelDrivenBlueprint(blueprint) {
  return Boolean(blueprint && blueprint.app_archetype === "model_driven_app" && blueprint.model);
}

function modelDrivenSummary(blueprint) {
  if (!isModelDrivenBlueprint(blueprint)) return null;
  const model = blueprint.model || {};
  const entities = Array.isArray(model.entities) ? model.entities : [];
  const imports = Array.isArray(model.imports) ? model.imports : [];
  const providers = Array.isArray(model.providers) ? model.providers : [];
  const ui = model.ui || {};
  const fieldCount = entities.reduce((total, entity) => total + (Array.isArray(entity.fields) ? entity.fields.length : 0), 0);
  return {
    entities,
    imports,
    providers,
    fieldCount,
    entityLabel: entities.map((entity) => entity.label_plural || entity.name).filter(Boolean).join(", ") || "(none)",
    importLabel: imports.length ? imports.map((entry) => entry.label || entry.id || entry.entity || "import").join(", ") : "None",
    providerLabel: providers.length ? providers.map((entry) => `${entry.label || entry.id || "provider"} (${entry.type || "provider"})`).join(", ") : "None",
    uiLabel: [ui.recipe, ui.composition].filter(Boolean).join(" / ") || "Default model-driven UI",
  };
}

function modelDrivenCapabilityGroups(summary) {
  return [
    { title: "Model", items: [`${summary.entities.length} entities`, `${summary.fieldCount} fields`, `Entities: ${summary.entityLabel}`] },
    { title: "Data sources", items: [`Imports: ${summary.importLabel}`, `Providers: ${summary.providerLabel}`] },
    { title: "Product surfaces", items: ["Generated CRUD routes", "Entity list/detail forms", `UI: ${summary.uiLabel}`] },
    { title: "Next action", items: ["Continue to Review", "No Draft app plan click required"] },
  ];
}

function renderModelDrivenReviewSummary(blueprint) {
  const summary = modelDrivenSummary(blueprint);
  if (!summary) return '<p class="helper-copy wide">Model-driven summary will appear after an assistant proposal is applied.</p>';
  const entityRows = summary.entities.map((entity) => {
    const fields = Array.isArray(entity.fields) ? entity.fields : [];
    const names = fields.map((field) => field.label || field.name).filter(Boolean).join(", ") || "No fields";
    return `<li><strong>${escapeHtml(entity.label_plural || entity.name)}</strong>: ${escapeHtml(fields.length)} fields — ${escapeHtml(names)}</li>`;
  }).join("");
  return `
    <div class="customize-group wide model-driven-review-summary"><h3>Model-driven app summary</h3></div>
    <div class="wide model-driven-summary-card">
      <p class="helper-copy">This assistant-applied Blueprint is the active Builder draft. Continue to Review; no extra Draft app plan step is required.</p>
      <ul>
        ${entityRows}
        <li><strong>Imports:</strong> ${escapeHtml(summary.importLabel)}</li>
        <li><strong>Providers:</strong> ${escapeHtml(summary.providerLabel)}</li>
        <li><strong>UI recipe/composition:</strong> ${escapeHtml(summary.uiLabel)}</li>
      </ul>
    </div>
  `;
}

function setActiveStep(step) {
  activeStep = step;
  document.querySelectorAll("[data-step]").forEach((panel) => {
    panel.classList.toggle("active", panel.dataset.step === step);
  });
  document.querySelectorAll("[data-step-target]").forEach((button) => {
    button.classList.toggle("active", button.dataset.stepTarget === step);
  });
  const activePanel = document.querySelector(`[data-step="${step}"]`);
  if (activePanel) activePanel.focus?.({ preventScroll: true });
}

function renderExportSummary(preview) {
  if (!exportSummary) return;
  const stepsByName = new Map((localRunState.steps || []).map((step) => [step.step, step]));
  const generated = stepsByName.get("generate");
  const validated = stepsByName.get("validate-app");
  const generatedPath = localRunState.generatedPath || generated?.generated_path;
  if (generatedPath) {
    const validationStatus = validated
      ? (validated.ok ? "make validate passed" : "make validate failed")
      : "make validate not run yet";
    const nextCommands = [`cd ${generatedPath}`, "make validate", "make run-backend", "make run-frontend"];
    exportSummary.innerHTML = `
      <article class="export-card local-run-summary">
        <p class="eyebrow">Local run summary</p>
        <h3>Generated app is ready for next steps</h3>
        <p><strong>Generated path:</strong> <code>${escapeHtml(generatedPath)}</code></p>
        <p><strong>Validation status:</strong> ${escapeHtml(validationStatus)}</p>
        <h4>Copyable next commands</h4>
        <pre class="mini-pre">${escapeHtml(nextCommands.join("\n"))}</pre>
        <p class="helper-copy">You can continue from this sandboxed app, or export the Blueprint and rerun the source-of-truth CLI commands below.</p>
      </article>
    `;
    return;
  }
  exportSummary.innerHTML = `
    <article class="export-card manual-cli-summary">
      <p class="eyebrow">Manual export path</p>
      <h3>No local Builder run yet</h3>
      <p>Static browser mode and offline sharing still work: copy or download the Blueprint YAML, then run the CLI commands below from your AgentForge workspace.</p>
      <h4>Copyable CLI commands</h4>
      <pre class="mini-pre">${escapeHtml((plannerCommands.length ? plannerCommands : preview.commands).join("\n"))}</pre>
    </article>
  `;
}

function renderGenerationPreview(preview, activeBlueprint = plannerBlueprint) {
  const modelSummary = modelDrivenSummary(activeBlueprint);
  const modelBlock = modelSummary ? `
    <div class="preview-block outcome-block wide-preview model-driven-review-summary">
      <p class="eyebrow">Model-driven draft</p>
      <h3>${escapeHtml(modelSummary.entities.length)} entities · ${escapeHtml(modelSummary.fieldCount)} fields</h3>
      <ul>
        <li>Entities: <strong>${escapeHtml(modelSummary.entityLabel)}</strong></li>
        <li>Imports: <strong>${escapeHtml(modelSummary.importLabel)}</strong></li>
        <li>Providers: <strong>${escapeHtml(modelSummary.providerLabel)}</strong></li>
        <li>UI recipe: <strong>${escapeHtml(modelSummary.uiLabel)}</strong></li>
      </ul>
      <p class="helper-copy">This assistant-applied Blueprint is already validated. Continue to Review; you do not need to click Draft app plan again.</p>
    </div>
  ` : "";
  generationPreview.innerHTML = `
    <div class="preview-block outcome-block">
      <p class="eyebrow">App type</p>
      <h3>${escapeHtml(modelSummary ? "Model-driven CRUD/workflow app" : preview.archetype)}</h3>
      <p class="helper-copy">A local app demo with deterministic validation and no required external services.</p>
    </div>
    ${modelBlock}
    <div class="preview-block outcome-block wide-preview">
      <p class="eyebrow">What you will get</p>
      <ul>${preview.outputs.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>
    </div>
    <details class="preview-block module-details">
      <summary>Advanced module details</summary>
      <h3>Advanced capability/module details</h3>
      <div class="chip-row">${preview.supportedModules.map((item) => `<span class="chip">${escapeHtml(item)}</span>`).join("")}</div>
      <h3>Planned / unsupported advanced details</h3>
      <ul>${(preview.gaps.length ? preview.gaps : ["No planned/unsupported modules selected."]).map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>
    </details>
    <details class="preview-block command-preview-block">
      <summary>Preview next commands</summary>
      <pre class="mini-pre">${escapeHtml((plannerCommands.length ? plannerCommands : preview.commands).join("\n"))}</pre>
    </details>
  `;
}

async function plannerRequest(action, payload) {
  if (!plannerAvailable) {
    throw new Error("Planner server is not running.");
  }
  const response = await fetch(`${plannerApi}/${action}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) throw new Error(`Planner request failed with ${response.status}`);
  return response.json();
}

async function checkPlannerStatus() {
  try {
    const response = await fetch(`${plannerApi}/status`);
    if (!response.ok) throw new Error("planner unavailable");
    const status = await response.json();
    plannerAvailable = status.planner_available === true;
    assistantMode = status.mode || (status.live_provider ? "live" : "scripted");
    assistantLiveProvider = status.live_provider === true;
    plannerStatus.textContent = plannerAvailable
      ? "Local planner connected. Use the assistant-first path, or open classic text-only draft controls."
      : "Static mode. Start `agentforge serve-builder` to enable scripted drafting.";
  } catch {
    plannerAvailable = false;
    assistantMode = "static";
    assistantLiveProvider = false;
    plannerStatus.textContent = "Static mode. Start `agentforge serve-builder` to enable scripted drafting.";
  }
  updateAssistantAvailability();
  updateLocalRunAvailability();
}

function assistantModeText(turnMode = null, fallbackReason = null) {
  if (!plannerAvailable) return "Static mode";
  if (fallbackReason) return `Fallback to scripted (${fallbackReason})`;
  if (turnMode === "live" || assistantLiveProvider || assistantMode === "live") return "Live OpenAI";
  return "Local scripted";
}

function updateAssistantModeLabel(turnMode = null, fallbackReason = null) {
  const label = document.querySelector("#assistant-mode-label");
  if (label) label.textContent = `Assistant-first path · ${assistantModeText(turnMode, fallbackReason)}`;
}

function setStatusChip(element, label, tone = "neutral") {
  if (!element) return;
  element.textContent = label;
  element.className = `status-chip ${tone}`;
}

function renderPlanStatusChips(issues = []) {
  const hasPlan = Boolean(plannerBlueprint);
  setStatusChip(planReadyChip, hasPlan ? "Plan ready" : "Plan needed", hasPlan ? "success" : "neutral");
  setStatusChip(blueprintValidChip, hasPlan && issues.length === 0 ? "Blueprint valid" : hasPlan ? "Blueprint needs review" : "Blueprint pending", hasPlan && issues.length === 0 ? "success" : hasPlan ? "warning" : "neutral");
  setStatusChip(buildBlueprintChip, hasPlan && issues.length === 0 ? "Blueprint valid" : hasPlan ? "Blueprint needs review" : "Blueprint pending", hasPlan && issues.length === 0 ? "success" : hasPlan ? "warning" : "neutral");
}

function readableList(items, empty = "nothing yet") {
  const values = (items || []).filter(Boolean);
  if (values.length === 0) return empty;
  if (values.length === 1) return values[0];
  return `${values.slice(0, -1).join(", ")}, and ${values[values.length - 1]}`;
}

function planSummarySentence(current, preview, activeBlueprint = plannerBlueprint) {
  const modelSummary = modelDrivenSummary(activeBlueprint);
  const appLabel = displayTitleForBlueprint(activeBlueprint, current.displayName || current.name || "this local app");
  if (modelSummary) {
    const entities = readableList(modelSummary.entities.map((entity) => entity.label_plural || entity.name), "no entities yet");
    const dataSources = modelSummary.imports.length || modelSummary.providers.length
      ? ` It will use ${readableList([
        modelSummary.imports.length ? `imports for ${modelSummary.importLabel}` : "",
        modelSummary.providers.length ? `providers for ${modelSummary.providerLabel}` : "",
      ], "local sample data")}.`
      : " No imports or providers are configured yet.";
    return `AgentForge will build ${appLabel} as a local model-driven workspace with ${entities}.${dataSources}`;
  }
  if (activeBlueprint) {
    return `AgentForge will build ${appLabel} as a ${plainArchetype(preview.archetype)} with the selected local demo capabilities. No external providers are required.`;
  }
  return "Describe an app idea and AgentForge will turn it into a plain-language plan here before anything is generated.";
}

function renderPlanSummaryList(current, preview, issues, activeBlueprint = plannerBlueprint) {
  if (!planSummaryApp) return;
  const modelSummary = modelDrivenSummary(activeBlueprint);
  const appLabel = displayTitleForBlueprint(activeBlueprint, current.displayName || current.name || "—");
  const typeLabel = modelSummary ? "Model-driven CRUD/workflow app" : plainArchetype(preview.archetype);
  const entityLabel = modelSummary
    ? `${modelSummary.entities.length} entities · ${modelSummary.entityLabel}`
    : activeBlueprint
      ? "Driven by selected feature modules"
      : "—";
  const importLabel = modelSummary
    ? `Imports: ${modelSummary.importLabel} · Providers: ${modelSummary.providerLabel}`
    : activeBlueprint
      ? "Local sample data only"
      : "—";
  const statusLabel = issues.length
    ? `${issues.length} issue${issues.length === 1 ? "" : "s"} to resolve`
    : activeBlueprint
      ? "Plan ready — validate the Blueprint next"
      : "Ready for an app idea";
  if (draftSummary) {
    draftSummary.hidden = false;
    draftSummary.textContent = planSummarySentence(current, preview, activeBlueprint);
  }
  planSummaryApp.textContent = appLabel;
  planSummaryType.textContent = typeLabel;
  planSummaryEntities.textContent = entityLabel;
  planSummaryProviders.textContent = importLabel;
  planSummaryStatus.textContent = statusLabel;
}

function computeBuildState() {
  const validateBlueprint = localRunState.steps.find((step) => step.step === "validate-blueprint");
  const generated = localRunState.steps.find((step) => step.step === "generate") || (localRunState.runId ? { ok: true } : null);
  const appChecks = localRunState.steps.find((step) => step.step === "validate-app");
  return {
    validateBlueprint,
    generated,
    appChecks,
    backendStatus: localRunState.services.backend?.status || "stopped",
    frontendStatus: localRunState.services.frontend?.status || "stopped",
    frontendUrl: localRunState.services.frontend?.url || "",
    backendUrl: localRunState.services.backend?.url || "",
  };
}

function computeNextStep() {
  const build = computeBuildState();
  const pendingProposal = Boolean(assistantSessionState?.proposal && assistantSessionState.proposal.blueprint);
  if (!plannerAvailable) {
    return { id: "start-server", label: "Start Builder server", detail: "Run `agentforge serve-builder` from the AgentForge workspace.", action: null };
  }
  if (pendingProposal) {
    return { id: "review-proposal", label: "Review the proposed Blueprint", detail: "Apply to install the validated draft, or Reject to keep your current one.", action: null };
  }
  if (!plannerBlueprint) {
    return { id: "describe-app", label: "Describe the app you want to build", detail: "Send a message to the assistant on the right to start a plan.", action: null };
  }
  if (!build.validateBlueprint) {
    return { id: "validate-blueprint", label: "Validate Blueprint", detail: "Run a schema validation pass on the applied Blueprint before generating files.", action: validateLocalRunBlueprint };
  }
  if (!build.validateBlueprint.ok) {
    return { id: "review-validation", label: "Retry validation", detail: "Fix the Blueprint, then retry. Advanced/logs has details.", action: validateLocalRunBlueprint };
  }
  if (!build.generated) {
    return { id: "generate", label: "Generate app locally", detail: "Create the sandboxed local app from the validated Blueprint.", action: generateLocalRunApp };
  }
  if (!build.generated.ok) {
    return { id: "review-generate", label: "Retry generate", detail: "Advanced/logs has the raw output.", action: generateLocalRunApp };
  }
  if (!build.appChecks) {
    return { id: "run-checks", label: "Run app checks", detail: "Validate the generated app before starting it.", action: validateLocalRunApp };
  }
  if (!build.appChecks.ok) {
    return { id: "review-checks", label: "Retry checks", detail: "Advanced/logs has the raw output.", action: validateLocalRunApp };
  }
  if (build.backendStatus !== "running" || build.frontendStatus !== "running") {
    return { id: "start-app", label: "Start app", detail: "Start backend, then frontend with the existing service controls.", action: startLocalRunApp };
  }
  if (build.frontendUrl) {
    return { id: "open-app", label: "Open app", detail: `Open ${build.frontendUrl} in your browser.`, action: () => window.open(build.frontendUrl, "_blank", "noreferrer") };
  }
  return { id: "ready", label: "App is running", detail: "Backend and frontend are healthy.", action: null };
}

function renderBuildRunStatusChips() {
  const { generated, appChecks, backendStatus, frontendStatus, frontendUrl, backendUrl } = computeBuildState();
  setStatusChip(buildGeneratedChip, generated ? (generated.ok ? "Generated" : "Generate failed") : "Not generated", generated ? (generated.ok ? "success" : "error") : "neutral");
  setStatusChip(buildChecksChip, appChecks ? (appChecks.ok ? "Checks passed" : "Checks failed") : "Checks pending", appChecks ? (appChecks.ok ? "success" : "error") : "neutral");
  setStatusChip(backendStatusChip, serviceStatusLabel("backend", backendStatus), backendStatus === "running" ? "success" : backendStatus === "starting" ? "warning" : ["failed", "error"].includes(backendStatus) ? "error" : "neutral");
  setStatusChip(frontendStatusChip, serviceStatusLabel("frontend", frontendStatus), frontendStatus === "running" ? "success" : frontendStatus === "starting" ? "warning" : ["failed", "error"].includes(frontendStatus) ? "error" : "neutral");
  updateServiceRow("backend", backendStatus, backendUrl);
  updateServiceRow("frontend", frontendStatus, frontendUrl);
  const next = computeNextStep();
  if (buildNextAction) buildNextAction.textContent = next.label;
  updateBuildPrimaryAction(next);
  renderAssistantNextStep(next);
  applyCanvasState();
}

function serviceStatusLabel(service, status) {
  if (service === "backend" && status === "running") return "Backend ready";
  if (service === "frontend" && status === "running") return "Frontend ready";
  const name = service === "backend" ? "Backend" : service === "frontend" ? "Frontend" : plainServiceName(service);
  if (status === "starting") return `${name} starting`;
  if (status === "stopping") return `${name} stopping`;
  if (status === "failed" || status === "error") return `${name} failed`;
  return `${name} stopped`;
}

function updateServiceRow(service, status, url = "") {
  const row = serviceRows[service];
  if (!row) return;
  row.dataset.status = status;
  const stopButton = row.querySelector(".service-row-stop");
  const startButton = row.querySelector(".service-row-primary");
  const running = status === "running";
  const transitional = status === "starting" || status === "stopping";
  if (stopButton) stopButton.hidden = !running && !transitional;
  if (startButton) {
    startButton.hidden = running || transitional;
    startButton.textContent = status === "failed" || status === "error" ? `Retry ${service}` : `Start ${service}`;
  }
  if ((status === "failed" || status === "error") && serviceControlsDetails) serviceControlsDetails.open = true;
  if (service === "frontend" && frontendOpenLink) {
    if (running && url) {
      frontendOpenLink.hidden = false;
      frontendOpenLink.href = url;
      frontendOpenLink.textContent = `Open ${url}`;
    } else {
      frontendOpenLink.hidden = true;
      frontendOpenLink.removeAttribute("href");
    }
  }
  if (service === "backend" && backendMeta) {
    if (running && url) {
      backendMeta.hidden = false;
      backendMeta.textContent = url;
    } else {
      backendMeta.hidden = true;
      backendMeta.textContent = "";
    }
  }
}

function updateBuildPrimaryAction(next = computeNextStep()) {
  if (!buildPrimaryAction) return;
  buildPrimaryAction.textContent = next.label;
  const hasAction = typeof next.action === "function";
  buildPrimaryAction.disabled = !hasAction || localRunBusy;
  buildPrimaryAction.dataset.nextId = next.id;
}

function renderAssistantNextStep(next = computeNextStep()) {
  const stateName = computeCanvasState();
  const hudNext = hudNextStepCopy(stateName, next);
  if (!assistantNextStepLabel) return;
  assistantNextStepLabel.textContent = hudNext.label;
  if (assistantNextStepDetail) {
    if (hudNext.detail) {
      assistantNextStepDetail.hidden = false;
      assistantNextStepDetail.textContent = hudNext.detail;
    } else {
      assistantNextStepDetail.hidden = true;
      assistantNextStepDetail.textContent = "";
    }
  }
}

function hudNextStepCopy(stateName, next) {
  if (stateName === "thinking") return { label: "Wait for the plan.", detail: "Drafting in the main canvas." };
  if (stateName === "plan-ready") return { label: "Review the proposed plan.", detail: "Apply or reject it in the main canvas." };
  if (stateName === "error") return { label: "Retry or refine.", detail: "See Advanced/logs for details." };
  const labels = {
    "start-server": "Start Builder server.",
    "describe-app": "Describe your app.",
    "validate-blueprint": "Validate the Blueprint.",
    "review-validation": "Fix validation errors.",
    generate: "Generate the local app.",
    "review-generate": "Review generate error.",
    "run-checks": "Run checks.",
    "review-checks": "Review check error.",
    "start-app": "Start app.",
    "open-app": "Open the app.",
    ready: "Open the app.",
  };
  const shortDetail = {
    "start-server": "Use Advanced for CLI details.",
    "describe-app": "Use the main composer.",
    "validate-blueprint": "Build controls are in the main canvas.",
    "review-validation": "Use Advanced/logs, then retry.",
    generate: "Build controls are in the main canvas.",
    "review-generate": "Use Advanced/logs, then retry.",
    "run-checks": "Build controls are in the main canvas.",
    "review-checks": "Use Advanced/logs, then retry.",
    "start-app": "Starts backend, then frontend.",
    "open-app": "Frontend is reachable.",
    ready: "Services are healthy.",
  };
  return { label: labels[next.id] || next.label, detail: shortDetail[next.id] || "" };
}

function blueprintForHud() {
  return assistantSessionState?.proposal?.blueprint || plannerBlueprint;
}

function renderRailHud(stateName = computeCanvasState()) {
  const next = computeNextStep();
  renderAssistantNextStep(next);
  const copy = CANVAS_STATE_COPY[stateName] || CANVAS_STATE_COPY.empty;
  if (assistantCurrentState) assistantCurrentState.dataset.state = stateName;
  if (assistantCurrentStateLabel) assistantCurrentStateLabel.textContent = copy.label;
  if (assistantStatus) assistantStatus.textContent = railStatusLine(stateName);
  renderRailAppSummary(stateName);
  renderRailServiceSummary();
}

function railStatusLine(stateName) {
  if (stateName === "static") return "Scripted drafting is unavailable.";
  if (stateName === "thinking") return "Drafting plan…";
  if (stateName === "plan-ready") return "Plan ready in main area.";
  if (stateName === "plan-applied") return "Plan applied.";
  if (stateName === "validating") return "Validating…";
  if (stateName === "generating") return "Generating…";
  if (stateName === "checking") return "Running checks…";
  if (stateName === "running") return activeBuildOp === "start-app" ? "Starting app…" : "Services are starting.";
  if (stateName === "open-app") return "App is running.";
  if (stateName === "error") return "Something failed. See Advanced/logs.";
  return "Ready.";
}

function renderRailAppSummary(stateName) {
  const blueprint = blueprintForHud();
  if (!assistantAppSummary || !blueprint || stateName === "static" || stateName === "empty" || stateName === "thinking") {
    if (assistantAppSummary) assistantAppSummary.hidden = true;
    return;
  }
  const summary = modelDrivenSummary(blueprint);
  const entities = summary?.entities || [];
  assistantAppSummary.hidden = false;
  if (assistantAppName) assistantAppName.textContent = displayTitleForBlueprint(blueprint, "Proposed app");
  if (assistantAppType) assistantAppType.textContent = summary ? "Model-driven app" : plainArchetype(blueprint.app_archetype || "local app");
  if (assistantAppEntities) {
    assistantAppEntities.innerHTML = entities.length
      ? entities.slice(0, 4).map((entity) => `<span>${escapeHtml(entity.label_plural || entity.name)}</span>`).join("")
      : `<span>${escapeHtml(summary ? "0 entities" : "Feature modules")}</span>`;
    if (entities.length > 4) assistantAppEntities.insertAdjacentHTML("beforeend", `<span>+${entities.length - 4}</span>`);
  }
}

function renderRailServiceSummary() {
  const build = computeBuildState();
  const hasServiceInfo = Boolean(localRunState.runId || build.generated || build.backendStatus !== "stopped" || build.frontendStatus !== "stopped");
  if (!assistantServiceSummary) return;
  assistantServiceSummary.hidden = !hasServiceInfo;
  if (!hasServiceInfo) return;
  updateRailServiceChip(assistantBackendChip, "Backend", build.backendStatus, build.backendUrl);
  updateRailServiceChip(assistantFrontendChip, "Frontend", build.frontendStatus, build.frontendUrl);
  if (assistantOpenAppLink) {
    if (build.frontendStatus === "running" && build.frontendUrl) {
      assistantOpenAppLink.hidden = false;
      assistantOpenAppLink.href = build.frontendUrl;
    } else {
      assistantOpenAppLink.hidden = true;
      assistantOpenAppLink.removeAttribute("href");
    }
  }
}

function updateRailServiceChip(chip, label, status, url = "") {
  if (!chip) return;
  chip.dataset.status = status;
  const strong = chip.querySelector("strong");
  const detail = chip.querySelector("em");
  if (strong) strong.textContent = label;
  if (detail) detail.textContent = url && status === "running" ? `${status} · ${url}` : status;
}

function setAssistantApplied(applied) {
  if (!assistantPanel) return;
  if (applied) {
    assistantPanel.dataset.applied = "true";
    if (assistantHistoryDetails) assistantHistoryDetails.open = false;
  } else {
    delete assistantPanel.dataset.applied;
    if (assistantHistoryDetails) assistantHistoryDetails.open = true;
  }
}

function updateAssistantAvailability() {
  if (!assistantPanel) return;
  assistantPanel.dataset.state = plannerAvailable ? "ready" : "static";
  updateAssistantModeLabel();
  if (plannerAvailable) {
    assistantStatus.textContent = assistantSessionState
      ? `${assistantModeText()} connected. Continue, or reset to start over.`
      : `${assistantModeText()} connected. Send your app idea to start.`;
    assistantSendButton.disabled = assistantBusy;
    assistantInput.disabled = false;
    if (heroComposerSend) heroComposerSend.disabled = assistantBusy;
    if (heroComposerInput) heroComposerInput.disabled = false;
  } else {
    assistantStatus.textContent = "Static mode. Start the Builder server.";
    assistantSendButton.disabled = true;
    assistantInput.disabled = true;
    if (heroComposerSend) heroComposerSend.disabled = true;
    if (heroComposerInput) heroComposerInput.disabled = true;
  }
  applyCanvasState();
}

function updateLocalRunAvailability() {
  if (!localRunPanel) return;
  const hasBlueprint = Boolean(plannerBlueprint);
  const canUseServer = plannerAvailable && hasBlueprint && !localRunBusy;
  localRunPanel.dataset.state = plannerAvailable ? (hasBlueprint ? "ready" : "needs-blueprint") : "static";
  localRunValidateBlueprintButton.disabled = !canUseServer;
  localRunGenerateButton.disabled = !canUseServer;
  localRunValidateAppButton.disabled = !canUseServer || !localRunState.runId;
  updateServiceButtons(canUseServer);
  renderServiceStatus();
  renderBuildRunStatusChips();
  if (localRunBusy) return;
  if (!plannerAvailable) {
    localRunStatus.textContent = "Static mode. Start the Builder server to enable Build actions.";
    renderLocalRunEmptyState("Start the Builder server, then apply an assistant proposal to unlock Build actions.");
  } else if (!hasBlueprint) {
    localRunStatus.textContent = "Apply an assistant proposal before Build actions.";
    renderLocalRunEmptyState("Apply a proposal first. Build actions stay disabled until there is an active Blueprint.");
  } else if (!localRunState.runId && localRunState.steps.length === 0) {
    localRunStatus.textContent = "Ready for validation and generation.";
    renderLocalRunEmptyState("No build results yet. Start with Validate Blueprint, then Generate app locally.");
  }
}

function renderLocalRunEmptyState(message) {
  if (!localRunResults || localRunResults.children.length > 0) return;
  localRunResults.innerHTML = `<article class="local-run-empty-state"><strong>Build status</strong><p>${escapeHtml(message)}</p></article>`;
}

async function localRunRequest(action, payload) {
  const response = await fetch(`${plannerApi}/local-run/${action}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload || {}),
  });
  const result = await response.json();
  if (!response.ok) throw new Error((result.errors || [result.error || "local run request failed"]).join(" "));
  return result;
}

function setLocalRunBusy(message, op = null) {
  localRunBusy = true;
  activeBuildOp = op;
  localRunPanel?.setAttribute("aria-busy", "true");
  localRunPanel?.setAttribute("data-busy-op", op || "");
  if (buildPrimaryAction) {
    buildPrimaryAction.disabled = true;
    buildPrimaryAction.dataset.busy = "true";
  }
  const expectation = BUILD_OP_PROGRESS[op]?.expectation;
  localRunStatus.textContent = expectation ? `${message} ${expectation}` : message;
  if (localRunResults) {
    const helperLine = expectation
      ? expectation
      : "Keep this tab open. The assistant will summarize the result when the action finishes.";
    localRunResults.innerHTML = `<article class="local-run-result pending" aria-live="polite"><h3>${escapeHtml(message)}</h3><p class="helper-copy">${escapeHtml(helperLine)}</p><p class="local-run-busy-hint helper-copy">Keep this tab open — primary action stays disabled until the step finishes.</p></article>`;
  }
  updateLocalRunAvailability();
  applyCanvasState();
  persistSessionSoon();
}

function finishLocalRun(result) {
  localRunBusy = false;
  activeBuildOp = null;
  localRunPanel?.setAttribute("aria-busy", "false");
  localRunPanel?.removeAttribute("data-busy-op");
  if (buildPrimaryAction) {
    delete buildPrimaryAction.dataset.busy;
  }
  if (result.run_id) localRunState.runId = result.run_id;
  if (result.generated_path) localRunState.generatedPath = result.generated_path;
  if (result.service) localRunState.services[result.service] = result;
  if (result.step && !["start-service", "stop-service", "service-status"].includes(result.step)) {
    localRunState.steps = [...localRunState.steps.filter((step) => step.step !== result.step), result];
  }
  renderLocalRunResult(result);
  appendAssistantActivityForLocalRun(result);
  updateLocalRunAvailability();
  if (result.step === "start-service" || result.step === "service-status") scheduleServiceStatusPoll();
  persistSessionSoon();
}

function appendAssistantActivityForLocalRun(result) {
  const message = assistantActivityMessageForLocalRun(result);
  if (message) appendAssistantMessage("activity", message);
}

function assistantActivityMessageForLocalRun(result) {
  if (!result || result.step === "service-status") return "";
  const detail = summarizeLocalRunIssue(result);
  const exitCode = result.exit_code ?? "n/a";
  if (result.step === "validate-blueprint") {
    return result.ok
      ? "Blueprint validation passed. Next: generate the app locally."
      : `Blueprint validation failed: ${detail}. See Local Control Room details/logs, then update the plan.`;
  }
  if (result.step === "generate") {
    return result.ok
      ? `Generated app at ${result.generated_path || localRunState.generatedPath || "the sandboxed run folder"}. Next: run make validate.`
      : `Generate failed: ${detail}. See Local Control Room details/logs, then retry after fixing the Blueprint.`;
  }
  if (result.step === "validate-app") {
    return result.ok
      ? `make validate passed (exit code ${exitCode}). Next: start the backend and frontend.`
      : `make validate failed (exit code ${exitCode}): ${detail}. See Local Control Room logs, then fix and rerun.`;
  }
  if (result.step === "start-service") {
    return serviceActivityMessage(result, "start");
  }
  if (result.step === "stop-service") {
    return serviceActivityMessage(result, "stop");
  }
  return "";
}

function serviceActivityMessage(result, action) {
  const service = plainServiceName(result.service);
  const detail = summarizeLocalRunIssue(result);
  if (!result.ok) {
    return `${service} ${action} failed: ${detail}. See Local Control Room details/logs, then retry.`;
  }
  const status = result.status || (action === "stop" ? "stopped" : "running");
  if (action === "stop") return status === "stopped" ? `${service} is stopped.` : `${service} is ${status}.`;
  if (result.url && status === "running") return `${service} is running at ${result.url}.`;
  if (result.url) return `${service} is ${status} at ${result.url}.`;
  return `${service} is ${status}.`;
}

function summarizeLocalRunIssue(result) {
  const errors = Array.isArray(result.errors) ? result.errors.filter(Boolean) : [];
  const first = errors[0] || result.error || result.status || "action failed";
  return String(first).replace(/\s+/g, " ").trim();
}

function plainServiceName(service) {
  const value = String(service || "service");
  return value ? value.charAt(0).toUpperCase() + value.slice(1) : "Service";
}

function renderLocalRunResult(result) {
  const statusLabel = result.ok ? "success" : "failed";
  const pathLine = result.generated_path ? `<p><strong>Generated path:</strong> <code>${escapeHtml(result.generated_path)}</code></p>` : "";
  const label = localRunStepLabel(result.step, result.service);
  const urlLine = result.url && result.status === "running" ? `<p><strong>Ready link:</strong> <a href="${escapeHtml(result.url)}" target="_blank" rel="noreferrer">${escapeHtml(result.url)}</a></p>` : "";
  const hasExitCode = result.exit_code !== undefined && result.exit_code !== null;
  const exitLine = hasExitCode ? `<p><strong>Exit code:</strong> ${escapeHtml(result.exit_code)}</p>` : "";
  const advancedLink = `<a href="#advanced-logs">Advanced logs</a>`;
  localRunStatus.textContent = `${compactLocalRunStatus(result, label)}${hasExitCode ? ` · exit ${result.exit_code}` : ""}`;
  localRunResults.innerHTML = `
    <article class="local-run-result ${result.ok ? "success" : "error"}">
      <h3>${escapeHtml(label)}: ${escapeHtml(result.status || statusLabel)}</h3>
      <p>${escapeHtml(localRunResultSummary(result, label))} ${advancedLink}</p>
      ${result.ok ? exitLine : ""}
      ${pathLine}
      ${urlLine}
      ${result.timed_out ? '<p class="error-text">Command timed out. See Advanced logs, then retry.</p>' : ""}
      ${result.truncated ? '<p class="helper-copy">Long logs were truncated here. Full output stays in Advanced logs.</p>' : ""}
    </article>
  `;
  const logs = [
    `# ${label} (${result.status || statusLabel})`,
    ...(result.commands || []).map((command) => `$ ${command}`),
    `# exit_code=${result.exit_code ?? "n/a"}`,
    "\n[stdout]",
    result.stdout || "",
    "\n[stderr]",
    result.stderr || "",
  ];
  localRunLog.textContent = logs.join("\n");
  renderExportSummary(getGenerationPreview(state()));
}

function localRunResultSummary(result, label) {
  if (!result.ok) return `${label} didn't finish — see`;
  if (result.step === "validate-blueprint") return "Plan looks good. Next: generate the app.";
  if (result.step === "generate") return "App is generated. Next: run checks.";
  if (result.step === "validate-app") return "Checks passed. Next: start the app.";
  if (result.step === "start-service") return result.service === "frontend" ? "Your app is running." : "Backend is ready. Click Start app to launch the frontend.";
  if (result.step === "stop-service") return `${plainServiceName(result.service)} is stopped.`;
  return `${label} is done.`;
}

function compactLocalRunStatus(result, label) {
  if (result.step === "validate-blueprint") return result.ok ? "Blueprint valid" : "Blueprint failed";
  if (result.step === "generate") return result.ok ? "Generated" : "Generate failed";
  if (result.step === "validate-app") return result.ok ? "Checks passed" : "Checks failed";
  if (result.step === "start-service" || result.step === "stop-service" || result.step === "service-status") {
    const service = plainServiceName(result.service);
    return `${service} ${result.status || (result.ok ? "updated" : "failed")}`;
  }
  return `${label} ${result.ok ? "passed" : "failed"}`;
}

function localRunStepLabel(step, service = "") {
  if (step === "validate-blueprint") return "Validate Blueprint";
  if (step === "generate") return "Generate app";
  if (step === "validate-app") return "Run app checks";
  if (step === "start-service") return `Start ${service || "service"}`;
  if (step === "stop-service") return `Stop ${service || "service"}`;
  if (step === "service-status") return `${service || "Service"} status`;
  return "Local run";
}

async function validateLocalRunBlueprint() {
  if (!plannerAvailable || !plannerBlueprint || localRunBusy) return;
  setLocalRunBusy("Validating plan…", "validate-blueprint");
  try {
    finishLocalRun(await localRunRequest("validate-blueprint", { blueprint: plannerBlueprint }));
  } catch (error) {
    finishLocalRun({ step: "validate-blueprint", ok: false, status: "error", exit_code: 1, errors: [error.message], stderr: error.message, stdout: "", commands: [] });
  }
}

async function generateLocalRunApp() {
  if (!plannerAvailable || !plannerBlueprint || localRunBusy) return;
  setLocalRunBusy("Generating your app…", "generate");
  try {
    finishLocalRun(await localRunRequest("generate", { blueprint: plannerBlueprint }));
  } catch (error) {
    finishLocalRun({ step: "generate", ok: false, status: "error", exit_code: 1, errors: [error.message], stderr: error.message, stdout: "", commands: [] });
  }
}

async function validateLocalRunApp() {
  if (!plannerAvailable || !plannerBlueprint || !localRunState.runId || localRunBusy) return;
  setLocalRunBusy("Running app checks…", "validate-app");
  try {
    finishLocalRun(await localRunRequest("validate-app", { run_id: localRunState.runId }));
  } catch (error) {
    finishLocalRun({ step: "validate-app", ok: false, status: "error", exit_code: 1, run_id: localRunState.runId, generated_path: localRunState.generatedPath, errors: [error.message], stderr: error.message, stdout: "", commands: [] });
  }
}

function updateServiceButtons(canUseServer) {
  const hasRun = Boolean(localRunState.runId);
  const backendActive = ["starting", "running"].includes(localRunState.services.backend?.status);
  const frontendActive = ["starting", "running"].includes(localRunState.services.frontend?.status);
  localRunStartBackendButton.disabled = !canUseServer || !hasRun || backendActive;
  localRunStopBackendButton.disabled = !canUseServer || !hasRun || !backendActive;
  localRunStartFrontendButton.disabled = !canUseServer || !hasRun || frontendActive;
  localRunStopFrontendButton.disabled = !canUseServer || !hasRun || !frontendActive;
}

function renderServiceStatus() {
  if (!localRunProcessStatus) return;
  const serviceRows = ["backend", "frontend"].map((service) => {
    const result = localRunState.services[service];
    const status = result?.status || "stopped";
    const label = serviceStatusLabel(service, status);
    const url = status === "running" && result?.url ? `<a href="${escapeHtml(result.url)}" target="_blank" rel="noreferrer">${escapeHtml(result.url)}</a>` : "Start to get link";
    return `<div class="service-status ${escapeHtml(status)}"><strong>${escapeHtml(service)}</strong><span>${escapeHtml(label)}</span><span>${url}</span></div>`;
  }).join("");
  localRunProcessStatus.innerHTML = `<h3>App services</h3>${serviceRows}`;
  renderBuildRunStatusChips();
}

function sleep(ms) {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}

function renderStartAppProgress(message) {
  if (localRunStatus) localRunStatus.textContent = message;
  if (localRunResults) {
    localRunResults.innerHTML = `<article class="local-run-result pending"><h3>${escapeHtml(message)}</h3><p class="helper-copy">Starting the generated app with existing local-run service endpoints.</p></article>`;
  }
  renderServiceStatus();
  renderBuildRunStatusChips();
}

async function waitForLocalRunService(service, initialResult = null) {
  let latest = initialResult;
  for (let attempt = 0; attempt < 12; attempt += 1) {
    if (latest?.status === "running" && (service !== "frontend" || latest.url)) return latest;
    if (["failed", "error"].includes(latest?.status)) throw new Error(`${plainServiceName(service)} failed to start. See Advanced/logs.`);
    await sleep(attempt === 0 ? 250 : 1000);
    latest = await localRunRequest("service-status", { run_id: localRunState.runId, service });
    localRunState.services[service] = latest;
    renderServiceStatus();
  }
  throw new Error(`${plainServiceName(service)} did not become reachable. See Advanced/logs.`);
}

async function startLocalRunApp() {
  if (!plannerAvailable || !plannerBlueprint || !localRunState.runId || localRunBusy) return;
  localRunBusy = true;
  activeBuildOp = "start-app";
  localRunPanel?.setAttribute("aria-busy", "true");
  try {
    let backend = localRunState.services.backend;
    if (backend?.status !== "running") {
      renderStartAppProgress("Starting backend…");
      backend = await localRunRequest("start-service", { run_id: localRunState.runId, service: "backend" });
      localRunState.services.backend = backend;
      if (backend.ok === false) throw new Error("Backend failed to start. See Advanced/logs.");
      backend = await waitForLocalRunService("backend", backend);
      localRunState.services.backend = backend;
    }

    renderStartAppProgress("Starting frontend…");
    let frontend = await localRunRequest("start-service", { run_id: localRunState.runId, service: "frontend" });
    localRunState.services.frontend = frontend;
    if (frontend.ok === false) throw new Error("Frontend failed to start. See Advanced/logs.");
    frontend = await waitForLocalRunService("frontend", frontend);
    localRunState.services.frontend = frontend;

    localRunBusy = false;
    activeBuildOp = null;
    localRunPanel?.setAttribute("aria-busy", "false");
    finishLocalRun({ ...frontend, step: "start-service", service: "frontend", ok: true, status: "running", run_id: localRunState.runId, generated_path: localRunState.generatedPath });
    localRunStatus.textContent = "App is running.";
  } catch (error) {
    localRunBusy = false;
    activeBuildOp = null;
    localRunPanel?.setAttribute("aria-busy", "false");
    const message = String(error.message || error);
    const service = message.toLowerCase().includes("frontend") ? "frontend" : "backend";
    finishLocalRun({ step: "start-service", service, ok: false, status: "error", exit_code: null, run_id: localRunState.runId, generated_path: localRunState.generatedPath, errors: [message], stderr: message, stdout: "", commands: [] });
    localRunStatus.textContent = message;
  }
}

async function controlLocalRunService(service, action) {
  if (!plannerAvailable || !plannerBlueprint || !localRunState.runId || localRunBusy) return;
  const verb = action === "start-service" ? "Starting" : "Stopping";
  setLocalRunBusy(`${verb} ${service}...`, action);
  try {
    finishLocalRun(await localRunRequest(action, { run_id: localRunState.runId, service }));
  } catch (error) {
    finishLocalRun({ step: action, service, ok: false, status: "error", exit_code: 1, run_id: localRunState.runId, generated_path: localRunState.generatedPath, errors: [error.message], stderr: error.message, stdout: "", commands: [] });
  }
}

function scheduleServiceStatusPoll() {
  if (localRunServicePollTimer || !localRunState.runId) return;
  const hasActive = ["backend", "frontend"].some((service) => ["starting", "running"].includes(localRunState.services[service]?.status));
  if (!hasActive) return;
  localRunServicePollTimer = window.setTimeout(pollLocalRunServices, 2000);
}

async function pollLocalRunServices() {
  localRunServicePollTimer = null;
  if (!plannerAvailable || !localRunState.runId) return;
  const active = ["backend", "frontend"].filter((service) => ["starting", "running"].includes(localRunState.services[service]?.status));
  if (active.length === 0) return;
  for (const service of active) {
    try {
      const result = await localRunRequest("service-status", { run_id: localRunState.runId, service });
      localRunState.services[service] = result;
    } catch {
      // Keep the last visible status; explicit Start/Stop actions still surface errors.
    }
  }
  renderServiceStatus();
  updateLocalRunAvailability();
  scheduleServiceStatusPoll();
}

async function draftBlueprint() {
  setPlannerBusy("Drafting...");
  try {
    const result = await plannerRequest("draft", { idea: plannerIdea.value, prior_answers: collectAnswers() });
    handlePlannerResult(result);
    if (result.status !== "needs_clarification") setActiveStep("review");
  } catch (error) {
    showPlannerError(error.message);
  }
}

async function clarifyIdea() {
  setPlannerBusy("Preparing questions...");
  try {
    const result = await plannerRequest("clarify", { idea: plannerIdea.value });
    handlePlannerResult(result);
  } catch (error) {
    showPlannerError(error.message);
  }
}

async function refineBlueprint() {
  setPlannerBusy("Refining...");
  try {
    const result = await plannerRequest("refine", {
      blueprint: plannerBlueprint || createBlueprintFromManualState(),
      instruction: plannerRefine.value,
    });
    handlePlannerResult(result);
    if (result.status !== "needs_clarification") setActiveStep("review");
  } catch (error) {
    showPlannerError(error.message);
  }
}

async function validateBlueprint() {
  setPlannerBusy("Validating...");
  try {
    const current = plannerBlueprint || createBlueprintFromManualState();
    const result = await plannerRequest("validate", {
      blueprint: current,
      path: `./domain-packs/${sanitizeName(current.name)}/domain-pack.yaml`,
    });
    handlePlannerResult(result, { preserveForm: true });
    if (result.status !== "needs_clarification") setActiveStep("review");
  } catch (error) {
    showPlannerError(error.message);
  }
}

function createBlueprintFromManualState() {
  return createBlueprint(state());
}

function handlePlannerResult(result, options = {}) {
  if (result.status === "needs_clarification") {
    activeQuestions = result.questions || [];
    renderQuestions(activeQuestions);
    clarificationPanel.classList.remove("hidden");
    draftPanel.classList.add("hidden");
    plannerStatus.textContent = "Answer the questions, then submit answers to draft the blueprint.";
    return;
  }

  if (result.status === "error") {
    showPlannerError((result.errors || ["Planner returned an error."]).join(" "));
    return;
  }

  resetLocalRunState();
  plannerBlueprint = result.blueprint;
  plannerYaml = result.yaml || "";
  plannerCommands = result.commands || [];
  if (!options.preserveForm && plannerBlueprint) applyBlueprintToForm(plannerBlueprint);
  renderDraftResult(result);
  clarificationPanel.classList.add("hidden");
  draftPanel.classList.remove("hidden");
  plannerStatus.textContent = "Planner draft ready. Review the plain-language plan, then run the CLI commands.";
  updatePreview();
}

function renderQuestions(questions) {
  clarificationQuestions.innerHTML = questions
    .map(
      (question, index) => `
        <label>
          ${escapeHtml(question)}
          <input data-question-index="${index}" autocomplete="off" />
        </label>
      `,
    )
    .join("");
}

function collectAnswers() {
  const answers = {};
  document.querySelectorAll("[data-question-index]").forEach((input) => {
    const index = Number(input.dataset.questionIndex);
    if (activeQuestions[index] && input.value.trim()) {
      answers[activeQuestions[index]] = input.value.trim();
    }
  });
  return answers;
}

function renderDraftResult(result) {
  const modules = result.suggested_modules || [];
  const archetype = result.blueprint?.app_archetype || form.archetype.value;
  if (draftSummary && !result.blueprint) {
    draftSummary.hidden = false;
    draftSummary.textContent = "Draft from an idea or chat with the assistant to fill this in.";
  }
  draftChips.innerHTML = [plainArchetype(archetype), ...modules.map(plainCapabilityLabel)]
    .slice(0, 7)
    .map((item) => `<span class="capability-token">${escapeHtml(item)}</span>`)
    .join("");
  const assumptions = result.assumptions || [];
  const warnings = result.warnings || [];
  renderList(plannerAssumptions, assumptions);
  renderList(plannerWarnings, warnings);
  if (planSummaryExtras) {
    const hasAdvancedPlanDetails = Boolean(result.blueprint) || assumptions.length > 0 || warnings.length > 0;
    planSummaryExtras.hidden = !hasAdvancedPlanDetails;
    if (warnings.length > 0) planSummaryExtras.open = true;
  }
}

function renderList(target, items) {
  const values = items.length ? items : ["None."];
  target.innerHTML = values.map((item) => `<li>${escapeHtml(item)}</li>`).join("");
}

function previewAnalyzerReport() {
  const parsed = parseAnalyzerReport(analyzerReport.value);
  analyzerOutput.classList.remove("hidden");
  if (!parsed.ok) {
    parsedBlueprintSeed = "";
    analyzerOutput.innerHTML = `<h3>Analyzer report</h3><p class="error-text">${escapeHtml(parsed.error)}</p>`;
    return;
  }
  parsedBlueprintSeed = parsed.blueprintSeed || "";
  const stackItems = Object.entries(parsed.detectedStack)
    .map(([group, items]) => `<li><strong>${escapeHtml(group)}</strong>: ${escapeHtml((items || []).slice(0, 4).join(", ") || "none detected")}</li>`)
    .join("");
  const modules = parsed.moduleCompatibility
    .map((item) => `<span class="chip ${escapeHtml(item.status || "unknown")}">${escapeHtml(item.module)}: ${escapeHtml(item.status || "unknown")}</span>`)
    .join("");
  const phases = parsed.migrationPlan
    .slice(0, 6)
    .map((phase) => `<li>${escapeHtml(phase.phase || "Phase")}: ${escapeHtml(phase.title || phase.step || "Review migration step")}</li>`)
    .join("");
  analyzerOutput.innerHTML = `
    <h3>${escapeHtml(parsed.repoName)} analysis</h3>
    <p class="helper-copy">Likely archetype: <strong>${escapeHtml(parsed.archetype)}</strong> (${escapeHtml(parsed.confidence)} confidence)</p>
    <div class="result-grid">
      <div><h4>Detected stack</h4><ul>${stackItems}</ul></div>
      <div><h4>Migration phases</h4><ul>${phases || "<li>No phases reported.</li>"}</ul></div>
    </div>
    <h4>Module compatibility</h4>
    <div class="chip-row">${modules || '<span class="chip">No module compatibility reported</span>'}</div>
    ${parsedBlueprintSeed ? '<h4>Blueprint seed</h4><pre class="mini-pre">' + escapeHtml(parsedBlueprintSeed) + '</pre>' : '<p class="helper-copy">No blueprint seed was included.</p>'}
  `;
}

function previewExtensionPlan() {
  const parsed = parseExtensionPlan(extensionPlanReport.value);
  extensionPlanOutput.classList.remove("hidden");
  if (!parsed.ok) {
    extensionPlanOutput.innerHTML = `<h3>Extension plan</h3><p class="error-text">${escapeHtml(parsed.error)}</p>`;
    return;
  }
  const modules = parsed.modulePlans
    .map((item) => `<span class="chip ${escapeHtml(item.status || "unknown")}">${escapeHtml(item.module)}: ${escapeHtml(item.status || "unknown")}</span>`)
    .join("");
  const phases = parsed.migrationPhases
    .slice(0, 7)
    .map((phase) => `<li>${escapeHtml(phase.phase || "Phase")}: ${escapeHtml(phase.title || "Review migration phase")}</li>`)
    .join("");
  const adds = (parsed.fileImpact.likely_files_to_add || []).slice(0, 8).map((item) => `<li>${escapeHtml(item)}</li>`).join("");
  const risks = parsed.risks.slice(0, 6).map((risk) => `<li>${escapeHtml(risk.risk)}: ${escapeHtml(risk.detail)}</li>`).join("");
  extensionPlanOutput.innerHTML = `
    <h3>${escapeHtml(parsed.repoName)} extension plan</h3>
    <p class="helper-copy">${escapeHtml(parsed.statement)}</p>
    <div class="chip-row">${modules || '<span class="chip">No module plans reported</span>'}</div>
    <div class="result-grid">
      <div><h4>Migration phases</h4><ul>${phases || "<li>No phases reported.</li>"}</ul></div>
      <div><h4>Likely files to add</h4><ul>${adds || "<li>No file additions reported.</li>"}</ul></div>
    </div>
    <h4>Risks</h4><ul>${risks || "<li>No risks reported.</li>"}</ul>
  `;
}

async function copyBlueprintSeed() {
  if (!parsedBlueprintSeed) previewAnalyzerReport();
  if (!parsedBlueprintSeed) return;
  await navigator.clipboard.writeText(parsedBlueprintSeed);
  copyBlueprintSeedButton.textContent = "Copied seed";
  window.setTimeout(() => {
    copyBlueprintSeedButton.textContent = "Copy blueprint seed";
  }, 1200);
}

function applyBlueprintToForm(blueprint) {
  form.name.value = blueprint.name || form.name.value;
  form.displayName.value = blueprint.display_name || form.displayName.value;
  form.description.value = blueprint.domain?.product_purpose || form.description.value;
  form.targetUser.value = blueprint.domain?.target_users?.[0] || form.targetUser.value;
  if (blueprint.app_archetype) form.archetype.value = blueprint.app_archetype;
  renderModules();
  const selected = new Set(blueprint.optional_shell_modules || []);
  document.querySelectorAll("[data-module]").forEach((input) => {
    if (!input.disabled) input.checked = selected.has(input.dataset.module);
  });
  form.workspaceEnabled.checked = Boolean(blueprint.workspace?.enabled);
  form.fixtureEnabled.checked = Boolean(blueprint.seed_data?.fixture_provider_records || blueprint.seed_data?.sample_projects);
  customizationValues = blueprint.customization || createDefaultCustomizationFromForm();
  customizationDirty = Boolean(blueprint.customization);
  renderedCustomizationArchetype = "";
}

function clearPlannerDraft() {
  plannerBlueprint = null;
  plannerYaml = "";
  plannerCommands = [];
  resetLocalRunState();
}

function resetLocalRunState() {
  if (localRunServicePollTimer) window.clearTimeout(localRunServicePollTimer);
  localRunServicePollTimer = null;
  localRunState = { runId: null, generatedPath: null, steps: [], services: { backend: null, frontend: null } };
  localRunPanel?.setAttribute("aria-busy", "false");
  if (localRunResults) localRunResults.innerHTML = "";
  if (localRunLog) localRunLog.textContent = "Local run logs will appear here after you click a control room action.";
  renderServiceStatus();
  renderExportSummary(getGenerationPreview(state()));
  updateLocalRunAvailability();
}

function setPlannerBusy(message) {
  plannerStatus.textContent = plannerAvailable ? message : "Static mode. Start `agentforge serve-builder` to enable scripted drafting.";
}

function showPlannerError(message) {
  plannerStatus.textContent = message;
  draftPanel.classList.remove("hidden");
  draftSummary.textContent = "Planner error";
  renderList(plannerAssumptions, []);
  renderList(plannerWarnings, [message]);
}

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (char) => {
    const escapes = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" };
    return escapes[char];
  });
}

async function copyYaml(event = null) {
  await navigator.clipboard.writeText(yamlPreview.textContent);
  const target = event?.currentTarget || copyButton;
  showCopied(target, target?.textContent || "Copy YAML");
}

async function copyCliCommands() {
  await navigator.clipboard.writeText(planPreview.textContent);
  showCopied(copyCliCommandsButton, "Copy CLI commands");
}

async function copyLocalRunLog() {
  await navigator.clipboard.writeText(localRunLog.textContent);
  showCopied(copyLocalRunLogButton, "Copy local run log");
}

function showCopied(button, originalLabel) {
  if (!button) return;
  button.textContent = "Copied";
  window.setTimeout(() => {
    button.textContent = originalLabel;
  }, 1200);
}

function downloadYaml() {
  const blob = new Blob([yamlPreview.textContent], { type: "text/yaml" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "domain-pack.yaml";
  link.click();
  URL.revokeObjectURL(url);
}

async function assistantRequest(action, payload) {
  if (!plannerAvailable) throw new Error("Planner server is not running.");
  const response = await fetch(`${plannerApi}/assistant/${action}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) throw new Error(`Assistant request failed with ${response.status}`);
  return response.json();
}

function appendAssistantMessage(role, text) {
  if (!assistantLog || !text) return;
  const entry = document.createElement("div");
  entry.className = `assistant-message assistant-message-${role}`;
  const label = document.createElement("span");
  label.className = "assistant-message-role";
  label.textContent = assistantMessageRoleLabel(role);
  const body = document.createElement("p");
  body.className = "assistant-message-body";
  body.textContent = text;
  entry.appendChild(label);
  entry.appendChild(body);
  assistantLog.appendChild(entry);
  assistantLog.scrollTop = assistantLog.scrollHeight;
  updateAssistantHistoryCount();
}

function updateAssistantHistoryCount() {
  if (!assistantHistoryCount || !assistantLog) return;
  assistantHistoryCount.textContent = String(assistantLog.querySelectorAll(".assistant-message").length);
}

function assistantMessageRoleLabel(role) {
  if (role === "user") return "You";
  if (role === "activity") return "Activity";
  return "Assistant";
}

function renderAssistantQuestions(questions, details) {
  if (!assistantQuestions) return;
  const detailList = Array.isArray(details) ? details : [];
  const promptList = Array.isArray(questions) ? questions : [];
  if (detailList.length === 0 && promptList.length === 0) {
    assistantQuestions.classList.add("hidden");
    assistantQuestions.innerHTML = "";
    return;
  }
  assistantQuestions.classList.remove("hidden");
  if (detailList.length > 0) {
    const items = detailList.map((entry) => {
      const prompt = escapeHtml(String(entry.prompt || ""));
      const helper = entry.helper ? `<p class="assistant-question-helper">${escapeHtml(entry.helper)}</p>` : "";
      const examples = Array.isArray(entry.examples) && entry.examples.length
        ? `<p class="assistant-question-examples-label">Examples</p><ul class="assistant-question-examples">${entry.examples.map((ex) => `<li>${escapeHtml(ex)}</li>`).join("")}</ul>`
        : "";
      const template = entry.template
        ? `<p class="assistant-question-template"><span>Template:</span> <code>${escapeHtml(entry.template)}</code></p>`
        : "";
      const chips = Array.isArray(entry.chips) && entry.chips.length
        ? `<div class="assistant-question-chips">${entry.chips.map((chip) => {
            const label = escapeHtml(String(chip.label || chip.value || ""));
            const value = escapeHtml(String(chip.value || chip.label || ""));
            return `<button type="button" class="assistant-chip" data-chip-value="${value}">${label}</button>`;
          }).join("")}</div>`
        : "";
      return `<li class="assistant-question" data-question-id="${escapeHtml(String(entry.id || ""))}"><p class="assistant-question-prompt">${prompt}</p>${helper}${examples}${template}${chips}</li>`;
    }).join("");
    assistantQuestions.innerHTML = `
      <p class="assistant-questions-label">Guided questions</p>
      <ul class="assistant-question-list">${items}</ul>
      <p class="assistant-questions-hint">Tip: click a chip to fill the input. Nothing is sent until you press Send.</p>
    `;
    return;
  }
  assistantQuestions.innerHTML = `
    <p class="assistant-questions-label">Open questions</p>
    <ul>${promptList.map((question) => `<li>${escapeHtml(String(question))}</li>`).join("")}</ul>
  `;
}

function fillAssistantInputFromChip(value) {
  if (!assistantInput || !value) return;
  const current = assistantInput.value.trim();
  if (!current) {
    assistantInput.value = value;
  } else if (current.endsWith(",") || current.endsWith(":")) {
    assistantInput.value = `${current} ${value}`;
  } else {
    assistantInput.value = `${current}, ${value}`;
  }
  assistantInput.focus({ preventScroll: true });
}

function renderAssistantProposal(proposal) {
  if (!assistantProposal) return;
  if (!proposal || !proposal.blueprint) {
    assistantProposal.classList.add("hidden");
    assistantProposal.innerHTML = "";
    setProposalPointer(false);
    applyCanvasState();
    return;
  }
  setAssistantApplied(false);
  setProposalPointer(true);
  const changesList = proposal.changes || [];
  const changes = changesList.map((change) => {
    const op = String(change.operation || "replace");
    return `<li class="assistant-change assistant-change-${escapeHtml(op)}"><span class="assistant-change-op">${escapeHtml(op)}</span><code>${escapeHtml(change.path)}</code>${change.to && typeof change.to === "string" ? ` <span class="assistant-change-summary">${escapeHtml(change.to)}</span>` : ""}</li>`;
  }).join("");
  const archetype = proposal.blueprint.app_archetype || "model_driven_app";
  const appName = displayTitleForBlueprint(proposal.blueprint, "Proposed app");
  const summary = modelDrivenSummary(proposal.blueprint);
  const entityNames = summary?.entities.map((entity) => entity.label_plural || entity.name).filter(Boolean) || [];
  const entities = readableList(entityNames, "no entities yet");
  const importLabel = summary?.importLabel || "None";
  const providerLabel = summary?.providerLabel || "None";
  const dataSourceSentence = importLabel === "None" && providerLabel === "None"
    ? "No imports or providers are configured yet."
    : `Imports: ${importLabel}. Providers: ${providerLabel}.`;
  const entityChips = entityNames.map((name) => `<span class="assistant-proposal-chip">${escapeHtml(name)}</span>`).join("");
  const applyDisabled = assistantBusy || !plannerAvailable ? "disabled" : "";
  assistantProposal.classList.remove("hidden");
  assistantProposal.innerHTML = `
    <div class="assistant-proposal-head">
      <p class="eyebrow">Plan ready</p>
      <h3>${escapeHtml(appName)}</h3>
      <p class="assistant-proposal-summary">AgentForge will build ${escapeHtml(appName)} as a ${escapeHtml(plainArchetype(archetype))} with ${escapeHtml(entities)}. ${escapeHtml(dataSourceSentence)}</p>
    </div>
    <div class="assistant-proposal-facts" aria-label="Proposal summary">
      <div><span>App type</span><strong>${escapeHtml(plainArchetype(archetype))}</strong></div>
      <div><span>Entities</span><strong>${entityNames.length || 0}</strong></div>
      <div><span>Data sources</span><strong>${importLabel === "None" && providerLabel === "None" ? "Local only" : "Configured"}</strong></div>
    </div>
    ${entityChips ? `<div class="assistant-proposal-chips" aria-label="Entities">${entityChips}</div>` : ""}
    ${changes ? `<details class="assistant-proposal-changes"><summary>Technical changes (${changesList.length})</summary><ul class="assistant-change-list">${changes}</ul></details>` : ""}
    <div class="assistant-proposal-actions actions" aria-label="Proposal actions">
      <button id="assistant-apply" type="button" class="primary-button" ${applyDisabled}>Apply and review plan</button>
      <button id="assistant-reject" type="button" class="quiet-button" ${applyDisabled}>Reject</button>
    </div>
    <p class="assistant-proposal-note">Apply updates only the in-memory Builder draft and re-runs schema validation. Reject keeps your current draft unchanged.</p>
  `;
  applyCanvasState();
}

function clearAssistantConversation() {
  assistantSessionState = null;
  if (assistantLog) assistantLog.innerHTML = "";
  renderAssistantQuestions([], []);
  renderAssistantProposal(null);
  renderAssistantGuidance(null);
  setAssistantApplied(false);
  setProposalPointer(false);
  renderAssistantNextStep();
  applyCanvasState();
}

const NEEDS_DETAIL_PATTERNS = [
  /need (?:a bit )?more (?:details|info|information)/i,
  /tell me more/i,
  /could you (?:share|describe)/i,
  /what (?:kind|type) of/i,
  /can you (?:share|describe|tell)/i,
  /can propose (?:once|after)/i,
];

function inferClarifyingQuestions(result, incomingMessages) {
  const hasQuestions = Array.isArray(result.questions) && result.questions.length > 0;
  const hasDetails = Array.isArray(result.question_details) && result.question_details.length > 0;
  if (hasQuestions || hasDetails) return null;
  if (result.proposal && result.proposal.blueprint) return null;
  const messages = (incomingMessages || []).map((value) => String(value || "").trim()).filter(Boolean);
  const lastQuestion = messages.reverse().find((text) => text.endsWith("?"));
  if (lastQuestion) {
    return {
      questions: [lastQuestion],
      details: [{
        id: "auto-clarify",
        prompt: lastQuestion,
        helper: "Reply in the assistant composer below.",
        examples: ["A short, plain-English answer is enough.", "If you're unsure, share one concrete example."],
      }],
    };
  }
  const signalsMoreDetail = messages.some((text) => NEEDS_DETAIL_PATTERNS.some((pattern) => pattern.test(text)));
  if (signalsMoreDetail) {
    return {
      questions: ["Tell the assistant a bit more about the app you want to build."],
      details: [{
        id: "auto-clarify",
        prompt: "Tell the assistant a bit more about the app you want to build.",
        helper: "Share entities, who uses it, and one concrete workflow.",
        examples: ["Manage clients and lessons for a tennis coach.", "Track support tickets and let an operator triage them."],
      }],
    };
  }
  return null;
}

function handleAssistantResponse(result) {
  assistantSessionState = result.state || null;
  updateAssistantModeLabel(result.turn_mode, result.fallback_reason);
  if (result.fallback_reason) {
    assistantStatus.textContent = `Assistant mode: ${assistantModeText(result.turn_mode, result.fallback_reason)}.`;
  }
  const incoming = Array.isArray(result.messages) ? result.messages : [];
  const filtered = incoming.filter((message) => !isGenericAcknowledgement(message));
  filtered.forEach((message) => appendAssistantMessage("assistant", message));
  if (result.proposal && result.proposal.blueprint) {
    const planMsg = planReadyMessage(result.proposal);
    if (planMsg) appendAssistantMessage("activity", planMsg);
  }
  const inferred = inferClarifyingQuestions(result, filtered);
  renderAssistantQuestions(
    inferred ? inferred.questions : result.questions,
    inferred ? inferred.details : result.question_details,
  );
  renderAssistantProposal(result.proposal);
  renderAssistantGuidance(result.guidance);
  if (result.errors && result.errors.length) {
    appendAssistantMessage("assistant", result.errors.join(" "));
  }
  renderAssistantNextStep();
  persistSessionSoon();
}

function renderAssistantGuidance(guidance) {
  if (!assistantGuidance) return;
  const entries = Array.isArray(guidance) ? guidance : [];
  if (entries.length === 0) {
    assistantGuidance.classList.add("hidden");
    assistantGuidance.innerHTML = "";
    return;
  }
  const items = entries.map((entry) => {
    const category = escapeHtml(String(entry.category || "unknown"));
    const message = escapeHtml(String(entry.message || "Validation failed."));
    const fix = entry.suggested_fix ? `<p class="assistant-guidance-fix"><strong>Try:</strong> ${escapeHtml(entry.suggested_fix)}</p>` : "";
    const question = entry.follow_up_question ? `<p class="assistant-guidance-question"><strong>Follow-up:</strong> ${escapeHtml(entry.follow_up_question)}</p>` : "";
    const raw = entry.error ? `<details class="assistant-guidance-raw"><summary>Raw validation error</summary><pre>${escapeHtml(entry.error)}</pre></details>` : "";
    return `<li class="assistant-guidance-item assistant-guidance-${category}"><p class="assistant-guidance-message"><span class="assistant-guidance-tag">${category}</span> ${message}</p>${fix}${question}${raw}</li>`;
  }).join("");
  assistantGuidance.classList.remove("hidden");
  assistantGuidance.innerHTML = `
    <p class="eyebrow">Validation guidance</p>
    <p class="assistant-guidance-summary">The proposal did not pass schema validation. Edit the Blueprint or answer the follow-up, then click Apply again. Nothing is changed automatically.</p>
    <ul class="assistant-guidance-list">${items}</ul>
  `;
}

function setAssistantBusy(busy) {
  assistantBusy = busy;
  if (assistantSendButton) assistantSendButton.disabled = busy || !plannerAvailable;
  if (heroComposerSend) heroComposerSend.disabled = busy || !plannerAvailable;
  if (assistantInput) assistantInput.dataset.busy = busy ? "true" : "false";
  if (heroComposerInput) heroComposerInput.dataset.busy = busy ? "true" : "false";
  assistantProposal?.querySelectorAll("button").forEach((button) => {
    button.disabled = busy || !plannerAvailable;
  });
}

function setAssistantThinking(thinking) {
  assistantSubmissionInFlight = Boolean(thinking);
  if (assistantThinking) assistantThinking.hidden = !thinking;
  if (heroComposerThinking) heroComposerThinking.hidden = !thinking;
  if (assistantPanel) {
    if (thinking) assistantPanel.dataset.thinking = "true";
    else delete assistantPanel.dataset.thinking;
  }
  if (canvasThinkingEcho) {
    if (thinking && lastUserPrompt) {
      canvasThinkingEcho.hidden = false;
      canvasThinkingEcho.textContent = `“${lastUserPrompt}”`;
    } else {
      canvasThinkingEcho.hidden = true;
      canvasThinkingEcho.textContent = "";
    }
  }
  applyCanvasState();
}

const CANVAS_STATE_COPY = {
  empty: { label: "Ready", detail: "Describe an app idea to begin." },
  thinking: { label: "Working", detail: "Drafting your app plan…" },
  clarifying: { label: "Question", detail: "Answer the assistant's guided question to continue." },
  "plan-ready": { label: "Plan ready", detail: "Review the proposed plan in the main canvas." },
  "plan-applied": { label: "Plan applied", detail: "Validate the Blueprint to continue." },
  validating: { label: "Working", detail: "Validating Blueprint…" },
  generating: { label: "Working", detail: "Generating the local app…" },
  checking: { label: "Working", detail: "Running app checks…" },
  running: { label: "Running", detail: "Services are starting." },
  "open-app": { label: "Running", detail: "App is running — open the frontend." },
  error: { label: "Error", detail: "Something failed — review details below." },
  static: { label: "Static", detail: "Start the Builder server to enable drafting." },
};

const CANVAS_STATE_REGION = {
  empty: "start",
  thinking: null,
  clarifying: "new-app",
  "plan-ready": "new-app",
  "plan-applied": "review",
  validating: "review",
  generating: "review",
  checking: "review",
  running: "review",
  "open-app": "review",
  error: "review",
  static: "start",
};

function buildOpToState(op) {
  if (op === "validate-blueprint") return "validating";
  if (op === "generate") return "generating";
  if (op === "validate-app") return "checking";
  if (op === "start-service" || op === "stop-service" || op === "start-app") return "running";
  return null;
}

function computeCanvasState() {
  if (assistantSubmissionInFlight) return "thinking";
  if (!plannerAvailable) return "static";
  const pendingProposal = Boolean(assistantSessionState?.proposal && assistantSessionState.proposal.blueprint);
  if (pendingProposal) return "plan-ready";
  const pendingQuestion = assistantSessionState?.status === "needs_clarification" && Array.isArray(assistantSessionState.questions) && assistantSessionState.questions.length > 0;
  if (pendingQuestion) return "clarifying";
  if (!plannerBlueprint) return "empty";
  if (localRunBusy) {
    const opState = buildOpToState(activeBuildOp);
    if (opState) return opState;
    return "plan-applied";
  }
  const build = computeBuildState();
  const validateFailed = build.validateBlueprint && !build.validateBlueprint.ok;
  const generateFailed = build.generated && !build.generated.ok;
  const checksFailed = build.appChecks && !build.appChecks.ok;
  const serviceFailed = ["failed", "error"].includes(build.backendStatus) || ["failed", "error"].includes(build.frontendStatus);
  if (validateFailed || generateFailed || checksFailed || serviceFailed) return "error";
  if (build.backendStatus === "running" && build.frontendStatus === "running" && build.frontendUrl) return "open-app";
  if (build.backendStatus === "running" || build.frontendStatus === "running") return "running";
  return "plan-applied";
}

function applyCanvasState() {
  if (!builderShell) return;
  const stateName = computeCanvasState();
  if (builderShell.dataset.canvasState !== stateName) {
    builderShell.dataset.canvasState = stateName;
  }
  const copy = CANVAS_STATE_COPY[stateName] || CANVAS_STATE_COPY.empty;
  if (canvasStateBadge) canvasStateBadge.dataset.state = stateName;
  if (canvasStateLabel) canvasStateLabel.textContent = copy.label;
  if (canvasStateDetail) canvasStateDetail.textContent = copy.detail;
  const showOverlay = stateName === "thinking" || (localRunBusy && ["validating", "generating", "checking", "running"].includes(stateName));
  if (canvasThinkingOverlay) canvasThinkingOverlay.hidden = !showOverlay;
  const opProgress = activeBuildOp ? BUILD_OP_PROGRESS[activeBuildOp] : null;
  if (canvasThinkingHeadline) {
    canvasThinkingHeadline.textContent = opProgress ? opProgress.headline : (stateName === "thinking" ? "Drafting your app plan…" : copy.detail);
  }
  if (canvasThinkingSubline) {
    canvasThinkingSubline.textContent = opProgress ? opProgress.subline : "Finding entities, pages, and build steps.";
  }
  if (canvasThinkingExpectation) {
    canvasThinkingExpectation.textContent = opProgress ? opProgress.expectation : "Usually a few seconds.";
  }
  renderRailHud(stateName);
  const region = CANVAS_STATE_REGION[stateName];
  if (region && region !== activeStep) setActiveStep(region);
  persistSessionSoon();
}

const GENERIC_ACK_PATTERNS = [
  /^i understand (?:that )?you want/i,
  /^i (?:will|'ll) (?:draft|create|help|put together)/i,
  /^sure[!,.]/i,
  /^(?:got it|okay|ok)[!,.]/i,
  /^happy to help/i,
  /^let me (?:help|put together|draft)/i,
  /^thanks for (?:that|sharing|the)/i,
];

function isGenericAcknowledgement(text) {
  if (!text) return false;
  const trimmed = String(text).trim();
  if (trimmed.length === 0) return false;
  return GENERIC_ACK_PATTERNS.some((pattern) => pattern.test(trimmed));
}

function planReadyMessage(proposal) {
  if (!proposal || !proposal.blueprint) return "";
  const entities = (proposal.blueprint.model?.entities || [])
    .map((entity) => entity.label_plural || entity.name)
    .filter(Boolean);
  if (entities.length === 0) return "Plan ready for review.";
  return `Plan ready: ${entities.join(", ")}.`;
}

function setProposalPointer(visible) {
  if (!assistantProposalPointer) return;
  assistantProposalPointer.hidden = !visible;
}

async function applyAssistantProposal() {
  if (!plannerAvailable || assistantBusy) return;
  const proposal = assistantSessionState?.proposal;
  if (!proposal || !proposal.blueprint) return;
  setAssistantBusy(true);
  try {
    const result = await assistantRequest("apply-preview", { proposal });
    if (!result.apply_ready) {
      const reason = (result.errors && result.errors.length ? result.errors : ["validation failed"]).join("; ");
      appendAssistantMessage("assistant", `Cannot apply proposal: ${reason}`);
      renderAssistantGuidance(result.guidance);
      return;
    }
    renderAssistantGuidance(null);
    const validated = result.proposal || proposal;
    resetLocalRunState();
    plannerBlueprint = validated.blueprint;
    plannerYaml = validated.yaml || "";
    plannerCommands = [];
    applyBlueprintToForm(plannerBlueprint);
    renderDraftResult({
      status: result.validation?.status || "draft",
      blueprint: plannerBlueprint,
      assumptions: result.validation?.assumptions || ["Builder Assistant applied a deterministic model-driven Blueprint."],
      warnings: result.validation?.warnings || [],
      suggested_modules: plannerBlueprint.optional_shell_modules || [],
    });
    clarificationPanel.classList.add("hidden");
    draftPanel.classList.remove("hidden");
    const appliedSummary = modelDrivenSummary(plannerBlueprint);
    const successParts = ["Blueprint applied", `App type: ${plannerBlueprint.app_archetype || "app"}`];
    if (appliedSummary) {
      successParts.push(
        `Entities: ${appliedSummary.entityLabel}`,
        `Imports: ${appliedSummary.importLabel}`,
        `Providers: ${appliedSummary.providerLabel}`,
        "Next action: Validate Blueprint in the Local Control Room",
      );
    }
    plannerStatus.textContent = `Assistant proposal applied. ${successParts.join(" · ")}.`;
    setActiveStep("review");
    appendAssistantMessage("assistant", `${successParts.join(". ")}. Validation passed; you do not need to click Draft app plan again.`);
    assistantSessionState = { ...assistantSessionState, proposal: null, status: "applied" };
    renderAssistantProposal(null);
    setAssistantApplied(true);
    updatePreview();
  } catch (error) {
    appendAssistantMessage("assistant", `Apply failed: ${error.message}`);
  } finally {
    setAssistantBusy(false);
  }
}

function rejectAssistantProposal() {
  if (!assistantSessionState || !assistantSessionState.proposal) return;
  assistantSessionState = { ...assistantSessionState, proposal: null, status: "rejected" };
  renderAssistantProposal(null);
  renderAssistantGuidance(null);
  setProposalPointer(false);
  appendAssistantMessage("assistant", "Rejected the proposed Blueprint. The Builder draft is unchanged.");
  renderAssistantNextStep();
}

async function submitAssistantMessage(textOverride, sourceInput) {
  if (!plannerAvailable || assistantBusy) return;
  const source = sourceInput || assistantInput;
  const text = (typeof textOverride === "string" ? textOverride : source?.value || "").trim();
  if (!text) return;
  lastUserPrompt = text;
  setAssistantBusy(true);
  setAssistantThinking(true);
  appendAssistantMessage("user", text);
  if (source) source.value = "";
  if (assistantInput && source !== assistantInput) assistantInput.value = "";
  try {
    const result = assistantSessionState
      ? await assistantRequest("message", { state: assistantSessionState, message: text })
      : await assistantRequest("start", { idea: text });
    setAssistantThinking(false);
    handleAssistantResponse(result);
    assistantStatus.textContent = `${assistantModeText(result.turn_mode, result.fallback_reason)} connected. Continue, or reset to start over.`;
  } catch (error) {
    setAssistantThinking(false);
    appendAssistantMessage("assistant", `Assistant error: ${error.message}`);
  } finally {
    setAssistantBusy(false);
    setAssistantThinking(false);
    applyCanvasState();
    (assistantInput || source)?.focus?.({ preventScroll: true });
  }
}

renderArchetypes();
renderEntryHelpers();
renderModules();
const sessionRestored = restoreSessionFromStorage();
updatePreview();
setActiveStep(activeStep);
updateAssistantAvailability();
updateLocalRunAvailability();
applyCanvasState();
checkPlannerStatus();
if (sessionRestored) persistSessionSoon();

window.addEventListener("beforeunload", () => {
  if (sessionPersistDebounce) {
    window.clearTimeout(sessionPersistDebounce);
    sessionPersistDebounce = null;
  }
  if (sessionResetInFlight) return;
  safeWriteSession(collectSessionSnapshot());
});

form.archetype.addEventListener("change", () => {
  clearPlannerDraft();
  customizationValues = createDefaultCustomizationFromForm();
  customizationDirty = false;
  renderedCustomizationArchetype = "";
  renderModules();
  updatePreview();
});

function shouldClearOnFormInput(target) {
  if (!target || !target.closest) return false;
  if (target.closest(".planner-panel")) return false;
  if (target.closest("#assistant-panel")) return false;
  // Inputs inside any Advanced/details region are inspection or post-apply
  // edits. They must not wipe the applied plan and reset the build flow.
  if (isInsideAdvancedRegion(target)) return false;
  return true;
}

document.addEventListener("input", (event) => {
  if (event.target.closest("#customize-panel")) readCustomizationInputs();
  if (shouldClearOnFormInput(event.target)) clearPlannerDraft();
  updatePreview();
  persistSessionSoon();
});
document.addEventListener("change", (event) => {
  if (event.target.closest("#customize-panel")) readCustomizationInputs();
  if (shouldClearOnFormInput(event.target)) clearPlannerDraft();
  updatePreview();
  persistSessionSoon();
});

document.addEventListener("click", (event) => {
  // A <summary> click toggles its <details>. Some legacy panels carry a
  // [data-step-target] attribute on an ancestor; opening Advanced/details
  // should never count as a step-target click.
  if (event.target.closest("summary")) return;
  if (isInsideAdvancedRegion(event.target)) return;
  const target = event.target.closest("[data-step-target]");
  if (!target) return;
  setActiveStep(target.dataset.stepTarget);
});

resetSessionButton?.addEventListener("click", async () => {
  if (typeof window.confirm === "function") {
    if (!window.confirm("Reset Builder session? This clears the saved plan, run summary, and chat history in this browser.")) return;
  }
  await resetBuilderSession();
});
copyButton.addEventListener("click", copyYaml);
downloadButton.addEventListener("click", downloadYaml);
copyYamlExportButton?.addEventListener("click", copyYaml);
downloadYamlExportButton?.addEventListener("click", downloadYaml);
copyCliCommandsButton?.addEventListener("click", copyCliCommands);
copyLocalRunLogButton?.addEventListener("click", copyLocalRunLog);
draftButton.addEventListener("click", draftBlueprint);
clarifyButton.addEventListener("click", clarifyIdea);
submitAnswersButton.addEventListener("click", draftBlueprint);
refineButton.addEventListener("click", refineBlueprint);
validateButton.addEventListener("click", validateBlueprint);
localRunValidateBlueprintButton?.addEventListener("click", validateLocalRunBlueprint);
localRunGenerateButton?.addEventListener("click", generateLocalRunApp);
localRunValidateAppButton?.addEventListener("click", validateLocalRunApp);
localRunStartBackendButton?.addEventListener("click", () => controlLocalRunService("backend", "start-service"));
localRunStopBackendButton?.addEventListener("click", () => controlLocalRunService("backend", "stop-service"));
localRunStartFrontendButton?.addEventListener("click", () => controlLocalRunService("frontend", "start-service"));
localRunStopFrontendButton?.addEventListener("click", () => controlLocalRunService("frontend", "stop-service"));
buildPrimaryAction?.addEventListener("click", () => {
  const next = computeNextStep();
  if (typeof next.action === "function") next.action();
});
parseAnalyzerButton.addEventListener("click", previewAnalyzerReport);
parseExtensionPlanButton.addEventListener("click", previewExtensionPlan);
copyBlueprintSeedButton.addEventListener("click", copyBlueprintSeed);
resetCustomizationButton.addEventListener("click", resetCustomization);
ideaExamples.addEventListener("click", (event) => {
  const button = event.target.closest("[data-idea]");
  if (!button) return;
  plannerIdea.value = button.dataset.idea;
  plannerIdea.focus({ preventScroll: true });
});
assistantForm?.addEventListener("submit", (event) => {
  event.preventDefault();
  submitAssistantMessage();
});
heroComposer?.addEventListener("submit", (event) => {
  event.preventDefault();
  submitAssistantMessage(heroComposerInput?.value || "", heroComposerInput);
});
assistantResetButton?.addEventListener("click", () => {
  clearAssistantConversation();
  if (plannerAvailable) assistantStatus.textContent = `${assistantModeText()} assistant connected. Send your app idea to start a guided plan.`;
  assistantInput.focus({ preventScroll: true });
});
assistantQuestions?.addEventListener("click", (event) => {
  const target = event.target;
  if (!(target instanceof HTMLElement)) return;
  const chip = target.closest(".assistant-chip");
  if (chip instanceof HTMLElement && chip.dataset.chipValue) {
    fillAssistantInputFromChip(chip.dataset.chipValue);
  }
});
assistantProposal?.addEventListener("click", (event) => {
  const target = event.target;
  if (!(target instanceof HTMLElement)) return;
  if (target.closest("#assistant-apply")) {
    applyAssistantProposal();
  } else if (target.closest("#assistant-reject")) {
    rejectAssistantProposal();
  }
});

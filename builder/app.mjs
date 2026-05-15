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
const assistantForm = document.querySelector("#assistant-form");
const assistantInput = document.querySelector("#assistant-input");
const assistantSendButton = document.querySelector("#assistant-send");
const assistantResetButton = document.querySelector("#assistant-reset");

const plannerApi = window.location.protocol.startsWith("http") ? `${window.location.origin}/api/planner` : "http://127.0.0.1:8765/api/planner";
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

function renderCustomizationPanel(current) {
  if (!customizePanel) return;
  const currentDefaults = createDefaultCustomizationFromForm();
  if (!customizationDirty) customizationValues = currentDefaults;
  customizeFamily.textContent = `Detected app family: ${getArchetypeFamilyLabel(current.archetype)}`;
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
  renderGenerationPreview(preview);
  renderBuildSummary(current, preview, issues);
  renderCustomizationPanel(current);
}

function renderBuildSummary(current, preview, issues) {
  summaryName.textContent = current.displayName || current.name || "Untitled app";
  summaryArchetype.textContent = plainArchetype(preview.archetype);
  summaryStatus.textContent = issues.length ? `${issues.length} issue${issues.length === 1 ? "" : "s"} to resolve` : plannerBlueprint ? "Plan drafted — ready to review" : "Ready for an app idea";
  summaryCapabilityGroups.innerHTML = capabilityGroups(preview)
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

function renderGenerationPreview(preview) {
  generationPreview.innerHTML = `
    <div class="preview-block outcome-block">
      <p class="eyebrow">App type</p>
      <h3>${escapeHtml(preview.archetype)}</h3>
      <p class="helper-copy">A local app demo with deterministic validation and no required external services.</p>
    </div>
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
    plannerStatus.textContent = plannerAvailable
      ? "Local planner connected. Draft, clarify, refine, and validate use the deterministic Python schema."
      : "Static mode. Start `agentforge serve-builder` to enable scripted drafting.";
  } catch {
    plannerAvailable = false;
    plannerStatus.textContent = "Static mode. Start `agentforge serve-builder` to enable scripted drafting.";
  }
  updateAssistantAvailability();
}

function updateAssistantAvailability() {
  if (!assistantPanel) return;
  assistantPanel.dataset.state = plannerAvailable ? "ready" : "static";
  if (plannerAvailable) {
    assistantStatus.textContent = assistantSessionState
      ? "Local assistant connected. Continue the conversation or reset to start over."
      : "Local assistant connected. Send your app idea to start a scripted conversation.";
    assistantSendButton.disabled = assistantBusy;
    assistantInput.disabled = false;
  } else {
    assistantStatus.textContent = "Static mode. Start `agentforge serve-builder` to chat with the local scripted assistant.";
    assistantSendButton.disabled = true;
    assistantInput.disabled = true;
  }
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
  draftSummary.textContent = `${result.status}: AgentForge drafted a local app plan. Review the app type, included capabilities, assumptions, and next commands before generating.`;
  draftChips.innerHTML = [plainArchetype(archetype), ...modules.map(plainCapabilityLabel)]
    .slice(0, 7)
    .map((item) => `<span class="capability-token">${escapeHtml(item)}</span>`)
    .join("");
  renderList(plannerAssumptions, result.assumptions || []);
  renderList(plannerWarnings, result.warnings || []);
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

async function copyYaml() {
  await navigator.clipboard.writeText(yamlPreview.textContent);
  copyButton.textContent = "Copied";
  window.setTimeout(() => {
    copyButton.textContent = "Copy YAML";
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
  label.textContent = role === "user" ? "You" : "Assistant";
  const body = document.createElement("p");
  body.className = "assistant-message-body";
  body.textContent = text;
  entry.appendChild(label);
  entry.appendChild(body);
  assistantLog.appendChild(entry);
  assistantLog.scrollTop = assistantLog.scrollHeight;
}

function renderAssistantQuestions(questions) {
  if (!assistantQuestions) return;
  if (!questions || !questions.length) {
    assistantQuestions.classList.add("hidden");
    assistantQuestions.innerHTML = "";
    return;
  }
  assistantQuestions.classList.remove("hidden");
  assistantQuestions.innerHTML = `
    <p class="assistant-questions-label">Open questions</p>
    <ul>${questions.map((question) => `<li>${escapeHtml(question)}</li>`).join("")}</ul>
  `;
}

function renderAssistantProposal(proposal) {
  if (!assistantProposal) return;
  if (!proposal || !proposal.blueprint) {
    assistantProposal.classList.add("hidden");
    assistantProposal.innerHTML = "";
    return;
  }
  const changes = (proposal.changes || []).map((change) => `<li><code>${escapeHtml(change.path)}</code> · ${escapeHtml(change.operation)}</li>`).join("");
  const archetype = proposal.blueprint.app_archetype || "model_driven_app";
  const entities = (proposal.blueprint.model?.entities || []).map((entity) => escapeHtml(entity.name)).join(", ") || "(no entities)";
  assistantProposal.classList.remove("hidden");
  assistantProposal.innerHTML = `
    <p class="eyebrow">Proposed Blueprint preview</p>
    <p class="assistant-proposal-summary">${escapeHtml(proposal.summary || "Proposed model-driven Blueprint.")}</p>
    <ul class="assistant-proposal-meta">
      <li>App type: <strong>${escapeHtml(archetype)}</strong></li>
      <li>Entities: <strong>${entities}</strong></li>
      <li>Status: <strong>${escapeHtml(proposal.validation?.status || "draft")}</strong></li>
    </ul>
    ${changes ? `<details class="assistant-proposal-changes"><summary>Changed fields (${(proposal.changes || []).length})</summary><ul>${changes}</ul></details>` : ""}
    <p class="assistant-proposal-note">Review only. The Builder draft above is unchanged. Apply/Reject controls arrive in a later phase.</p>
  `;
}

function clearAssistantConversation() {
  assistantSessionState = null;
  if (assistantLog) assistantLog.innerHTML = "";
  renderAssistantQuestions([]);
  renderAssistantProposal(null);
}

function handleAssistantResponse(result) {
  assistantSessionState = result.state || null;
  (result.messages || []).forEach((message) => appendAssistantMessage("assistant", message));
  renderAssistantQuestions(result.questions);
  renderAssistantProposal(result.proposal);
  if (result.errors && result.errors.length) {
    appendAssistantMessage("assistant", result.errors.join(" "));
  }
}

async function submitAssistantMessage() {
  if (!plannerAvailable || assistantBusy) return;
  const text = assistantInput.value.trim();
  if (!text) return;
  assistantBusy = true;
  assistantSendButton.disabled = true;
  appendAssistantMessage("user", text);
  assistantInput.value = "";
  try {
    const result = assistantSessionState
      ? await assistantRequest("message", { state: assistantSessionState, message: text })
      : await assistantRequest("start", { idea: text });
    handleAssistantResponse(result);
    assistantStatus.textContent = "Local assistant connected. Continue the conversation or reset to start over.";
  } catch (error) {
    appendAssistantMessage("assistant", `Assistant error: ${error.message}`);
  } finally {
    assistantBusy = false;
    if (plannerAvailable) assistantSendButton.disabled = false;
    assistantInput.focus({ preventScroll: true });
  }
}

renderArchetypes();
renderEntryHelpers();
renderModules();
updatePreview();
setActiveStep(activeStep);
updateAssistantAvailability();
checkPlannerStatus();

form.archetype.addEventListener("change", () => {
  clearPlannerDraft();
  customizationValues = createDefaultCustomizationFromForm();
  customizationDirty = false;
  renderedCustomizationArchetype = "";
  renderModules();
  updatePreview();
});

document.addEventListener("input", (event) => {
  if (event.target.closest("#customize-panel")) readCustomizationInputs();
  if (!event.target.closest(".planner-panel")) clearPlannerDraft();
  updatePreview();
});
document.addEventListener("change", (event) => {
  if (event.target.closest("#customize-panel")) readCustomizationInputs();
  if (!event.target.closest(".planner-panel")) clearPlannerDraft();
  updatePreview();
});

document.addEventListener("click", (event) => {
  const target = event.target.closest("[data-step-target]");
  if (!target) return;
  setActiveStep(target.dataset.stepTarget);
});
copyButton.addEventListener("click", copyYaml);
downloadButton.addEventListener("click", downloadYaml);
draftButton.addEventListener("click", draftBlueprint);
clarifyButton.addEventListener("click", clarifyIdea);
submitAnswersButton.addEventListener("click", draftBlueprint);
refineButton.addEventListener("click", refineBlueprint);
validateButton.addEventListener("click", validateBlueprint);
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
assistantResetButton?.addEventListener("click", () => {
  clearAssistantConversation();
  if (plannerAvailable) assistantStatus.textContent = "Local assistant connected. Send your app idea to start a scripted conversation.";
  assistantInput.focus({ preventScroll: true });
});

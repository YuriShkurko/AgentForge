import { analyzerCommandExamples, archetypes, exampleIdeas, extensionCommandExamples, getGenerationPreview, modules, parseAnalyzerReport, parseExtensionPlan, createBlueprint, createBlueprintYaml, sanitizeName, validateBuilderState } from "./blueprint-builder.mjs";

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

const plannerApi = window.location.protocol.startsWith("http") ? `${window.location.origin}/api/planner` : "http://127.0.0.1:8765/api/planner";
let plannerAvailable = false;
let plannerBlueprint = null;
let plannerYaml = "";
let plannerCommands = [];
let activeQuestions = [];
let parsedBlueprintSeed = "";

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
  };
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
}

function renderGenerationPreview(preview) {
  generationPreview.innerHTML = `
    <div class="preview-block">
      <h3>${escapeHtml(preview.archetype)}</h3>
      <p class="helper-copy">Generated app pieces</p>
      <ul>${preview.outputs.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>
    </div>
    <div class="preview-block">
      <h3>Supported modules</h3>
      <div class="chip-row">${preview.supportedModules.map((item) => `<span class="chip">${escapeHtml(item)}</span>`).join("")}</div>
    </div>
    <div class="preview-block">
      <h3>Gaps / planned</h3>
      <ul>${(preview.gaps.length ? preview.gaps : ["No planned/unsupported modules selected."]).map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>
    </div>
    <div class="preview-block">
      <h3>Next commands</h3>
      <pre class="mini-pre">${escapeHtml((plannerCommands.length ? plannerCommands : preview.commands).join("\n"))}</pre>
    </div>
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
      ? "Scripted planner connected. Draft, clarify, refine, and validate use the local Python schema."
      : "Static mode. Start `agentforge serve-builder` to enable scripted drafting.";
  } catch {
    plannerAvailable = false;
    plannerStatus.textContent = "Static mode. Start `agentforge serve-builder` to enable scripted drafting.";
  }
}

async function draftBlueprint() {
  setPlannerBusy("Drafting...");
  try {
    const result = await plannerRequest("draft", { idea: plannerIdea.value, prior_answers: collectAnswers() });
    handlePlannerResult(result);
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
  plannerStatus.textContent = "Planner draft ready. Review the YAML, then run the CLI commands.";
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
  draftSummary.textContent = `${result.status}: review the recommended archetype, modules, assumptions, and Blueprint Source before running the CLI.`;
  draftChips.innerHTML = [`Archetype: ${archetype}`, ...modules].map((item) => `<span class="chip">${escapeHtml(item)}</span>`).join("");
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
  form.fixtureEnabled.checked = Boolean(blueprint.seed_data?.fixture_provider_records);
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

renderArchetypes();
renderEntryHelpers();
renderModules();
updatePreview();
checkPlannerStatus();

form.archetype.addEventListener("change", () => {
  clearPlannerDraft();
  renderModules();
  updatePreview();
});

document.addEventListener("input", (event) => {
  if (!event.target.closest(".planner-panel")) clearPlannerDraft();
  updatePreview();
});
document.addEventListener("change", (event) => {
  if (!event.target.closest(".planner-panel")) clearPlannerDraft();
  updatePreview();
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
ideaExamples.addEventListener("click", (event) => {
  const button = event.target.closest("[data-idea]");
  if (!button) return;
  plannerIdea.value = button.dataset.idea;
  plannerIdea.focus();
});

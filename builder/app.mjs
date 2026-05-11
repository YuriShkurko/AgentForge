import { archetypes, modules, createBlueprint, createBlueprintYaml, sanitizeName, validateBuilderState } from "./blueprint-builder.mjs";

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

const plannerApi = window.location.protocol.startsWith("http") ? `${window.location.origin}/api/planner` : "http://127.0.0.1:8765/api/planner";
let plannerAvailable = false;
let plannerBlueprint = null;
let plannerYaml = "";
let plannerCommands = [];
let activeQuestions = [];

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
  const filename = `domain-packs/${sanitizeName(current.name)}/domain-pack.yaml`;
  yamlPreview.textContent = plannerYaml || yaml;
  planPreview.textContent = plannerCommands.length ? plannerCommands.join("\n") : `agentforge plan ${filename}\nagentforge generate ${filename}`;
  statusPill.textContent = issues.length ? `${issues.length} issue${issues.length === 1 ? "" : "s"}` : "Valid draft";
  statusPill.classList.toggle("warning", issues.length > 0);
  validationSummary.textContent = issues.length ? issues.join(" ") : "Ready for `agentforge plan`.";
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
  const modules = result.suggested_modules?.length ? result.suggested_modules.join(", ") : "No modules suggested.";
  draftSummary.textContent = `${result.status}: ${modules}`;
  renderList(plannerAssumptions, result.assumptions || []);
  renderList(plannerWarnings, result.warnings || []);
}

function renderList(target, items) {
  const values = items.length ? items : ["None."];
  target.innerHTML = values.map((item) => `<li>${escapeHtml(item)}</li>`).join("");
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

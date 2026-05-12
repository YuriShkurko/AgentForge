export const archetypes = [
  {
    id: "ingestion_scoring_pipeline",
    label: "Ingestion Scoring Pipeline",
    required: ["pipeline", "provider_adapter", "scoring_explanation", "operations_ui", "persistence", "test"],
    status: "supported",
  },
  {
    id: "notification_triage_app",
    label: "Notification Triage App",
    required: ["notification_action", "triage_ui", "persistence", "scoring_explanation"],
    status: "supported",
  },
  {
    id: "agent_dashboard_app",
    label: "Agent Dashboard App",
    required: ["agent", "workspace", "provider_adapter", "test"],
    status: "supported",
  },
  {
    id: "hybrid_agent_pipeline",
    label: "Hybrid Agent Pipeline",
    required: ["pipeline", "provider_adapter", "operations_ui"],
    status: "supported",
  },
  {
    id: "deploy_planner_app",
    label: "Deploy Planner App",
    required: ["pipeline", "persistence", "test"],
    status: "planned",
  },
  {
    id: "project_workspace_app",
    label: "Project Workspace App",
    required: ["operations_ui", "persistence", "agent_runtime", "workspace", "test"],
    status: "supported",
  },
];

export const modules = [
  { id: "provider_adapter", label: "Integration Adapters", supported: true, generates: "Provider interfaces and normalization adapters" },
  { id: "pipeline", label: "Pipeline", supported: true, generates: "Ingest, normalize, run history, and deterministic processing flow" },
  { id: "scoring_explanation", label: "Scoring / Explanation", supported: true, generates: "Fit scores, labels, drivers, risks, and explanation DTOs" },
  { id: "notification_action", label: "Notification Actions", supported: true, generates: "Preview-only notifications and append-only action history" },
  { id: "triage_ui", label: "Triage UI", supported: true, generates: "Decision cards, action buttons, and triage history" },
  { id: "agent_runtime", label: "Agent Runtime", supported: true, generates: "Scripted chat, tool registry, typed validation, and SSE streaming" },
  { id: "workspace", label: "Dashboard / Workspace", supported: true, generates: "Persisted generic widgets and workspace panel" },
  { id: "test", label: "Deterministic Test Harness", supported: true, generates: "Offline fixture tests with no live LLM/API dependency" },
  { id: "operations_ui", label: "Operations UI", supported: true, generates: "React operations panels for runs and results" },
  { id: "persistence", label: "Persistence", supported: true, generates: "SQLite-local/PostgreSQL-ready persistence models" },
  { id: "observability_debug", label: "Local Validation / Debug", supported: false, generates: "Future richer observability/debug tooling" },
  { id: "repo_analyzer", label: "Repo Analyzer", supported: false, generates: "Analysis-only CLI report; not generated into apps" },
  { id: "deploy_planner", label: "Deploy Planner", supported: false, generates: "Future dry-run deployment planning" },
  { id: "real_delivery_adapters", label: "Real Delivery Adapters", supported: false, generates: "Future external email/Slack/etc. delivery" },
  { id: "live_llm_provider", label: "Live LLM Provider", supported: false, generates: "Future live provider configuration" },
  { id: "advanced_workspace_renderers", label: "Advanced Workspace Renderers", supported: false, generates: "Future domain-specific dashboards" },
];

export const analyzerCommandExamples = [
  "agentforge analyze-repo ../my-project",
  "agentforge analyze-repo ../my-project --format md",
  "agentforge analyze-repo ../my-project --json --output report.json",
];

export const extensionCommandExamples = [
  "agentforge plan-extension ../my-project",
  "agentforge plan-extension report.json --from-report",
  "agentforge plan-extension ../my-project --modules agent_runtime,dashboard_workspace --format md --output extension-plan.md",
];

export const exampleIdeas = [
  "Job triage app for ranking opportunities and deciding what to apply to first.",
  "Lead scoring dashboard for sales reps to review the best-fit accounts.",
  "Customer feedback analyzer that groups urgent issues and explains priority.",
  "Internal agent workspace that summarizes records and pins useful widgets.",
  "Existing repo modernization plan for a FastAPI and React project.",
  "Project workspace for tracking tasks, owners, due dates, notes, and activity."
];

export function getGenerationPreview(state) {
  const archetype = archetypes.find((item) => item.id === state.archetype) || archetypes[0];
  const selected = unique([...(archetype.required || []), ...(state.selectedModules || [])]);
  const byId = new Map(modules.map((module) => [module.id, module]));
  const supportedModules = selected.filter((id) => byId.get(id)?.supported !== false);
  const plannedModules = selected.filter((id) => byId.get(id)?.supported === false);
  const outputs = [
    "FastAPI backend",
    "React + TypeScript frontend",
    "SQLite-local/PostgreSQL-ready persistence",
    "Generator, backend, frontend, and CI-ready validation commands",
  ];
  if (supportedModules.includes("provider_adapter")) outputs.push("Included sample records + adapter (no external provider setup)");
  if (supportedModules.includes("pipeline")) outputs.push("Ingestion pipeline and run history");
  if (supportedModules.includes("scoring_explanation")) outputs.push("Deterministic scoring and explanations");
  if (supportedModules.includes("notification_action") || supportedModules.includes("triage_ui")) outputs.push("Preview notification and triage surfaces");
  if (supportedModules.includes("agent_runtime") || supportedModules.includes("agent")) outputs.push("Scripted local agent chat with typed tools");
  if (supportedModules.includes("workspace")) outputs.push("Dashboard/workspace widgets");
  if (supportedModules.includes("test")) outputs.push("Deterministic test harness");
  if (archetype.id === "project_workspace_app") {
    outputs.splice(4, 0, "Project/task workspace with notes and activity", "Seeded local projects and task status updates");
  }
  const name = sanitizeName(state.name);
  const blueprintPath = `domain-packs/${name}/domain-pack.yaml`;
  const gaps = plannedModules.map((id) => `${byId.get(id)?.label || id} is planned/unsupported in current generation.`);
  if (archetype.status === "planned") gaps.push(`${archetype.label} is a future archetype.`);
  return {
    archetype: archetype.label,
    supportedModules: supportedModules.map((id) => byId.get(id)?.label || id),
    plannedModules: plannedModules.map((id) => byId.get(id)?.label || id),
    outputs: unique(outputs),
    gaps,
    commands: [`agentforge plan ${blueprintPath}`, `agentforge generate ${blueprintPath}`],
  };
}

export function parseExtensionPlan(text) {
  const raw = String(text || "").trim();
  if (!raw) return { ok: false, error: "Paste JSON output from `agentforge plan-extension --json` to preview it here." };
  let data;
  try {
    data = JSON.parse(raw);
  } catch {
    return { ok: false, error: "Could not parse extension plan JSON. Use `agentforge plan-extension <path> --json`." };
  }
  return {
    ok: true,
    repoName: data.target_repo?.name || "Unknown repo",
    selectedModules: data.selected_modules || [],
    modulePlans: data.module_plans || [],
    migrationPhases: data.migration_phases || [],
    fileImpact: data.file_impact || {},
    risks: data.risks || [],
    statement: data.no_files_modified_statement || "No files were modified.",
  };
}

export function parseAnalyzerReport(text) {
  const raw = String(text || "").trim();
  if (!raw) return { ok: false, error: "Paste JSON output from `agentforge analyze-repo --json` to preview it here." };
  let data;
  try {
    data = JSON.parse(raw);
  } catch {
    return { ok: false, error: "Could not parse analyzer JSON. Use `agentforge analyze-repo <path> --json`." };
  }
  const archetype = data.archetype_candidates?.[0] || null;
  return {
    ok: true,
    repoName: data.repo?.name || "Unknown repo",
    detectedStack: data.detected_stack || {},
    archetype: archetype?.archetype || "unknown/custom",
    confidence: archetype?.confidence || "low",
    moduleCompatibility: data.module_compatibility || [],
    migrationPlan: data.migration_plan || [],
    blueprintSeed: data.blueprint_seed || "",
  };
}

export function sanitizeName(value) {
  const clean = String(value || "")
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
  return clean || "new-app";
}

function scalar(value) {
  const text = String(value ?? "");
  if (text === "") return '""';
  if (/^[a-zA-Z0-9_./:-]+$/.test(text)) return text;
  return JSON.stringify(text);
}

function yaml(value, indent = 0) {
  const pad = " ".repeat(indent);
  if (Array.isArray(value)) {
    if (value.length === 0) return "[]";
    return value
      .map((item) => {
        if (item && typeof item === "object") {
          const nested = yaml(item, indent + 2);
          return `${pad}- ${nested.trimStart()}`;
        }
        return `${pad}- ${scalar(item)}`;
      })
      .join("\n");
  }
  if (value && typeof value === "object") {
    return Object.entries(value)
      .map(([key, item]) => {
        if (Array.isArray(item) && item.length === 0) return `${pad}${key}: []`;
        if (item && typeof item === "object") return `${pad}${key}:\n${yaml(item, indent + 2)}`;
        return `${pad}${key}: ${scalar(item)}`;
      })
      .join("\n");
  }
  return `${pad}${scalar(value)}`;
}

function unique(values) {
  return [...new Set(values.filter(Boolean))];
}

export function createBlueprint(state) {
  const archetype = archetypes.find((item) => item.id === state.archetype) || archetypes[0];
  const name = sanitizeName(state.name);
  const optional = unique(state.selectedModules || []).filter((module) => !archetype.required.includes(module));
  if (archetype.id === "project_workspace_app") return createProjectWorkspaceBlueprint(state, archetype, name, optional);
  const actionLabels = unique([state.actionAccept, state.actionSkip, state.actionMaybe].map((item) => sanitizeName(item)));
  const hasAgentRuntime = optional.includes("agent_runtime") || archetype.required.includes("agent");
  const hasWorkspace = state.workspaceEnabled || optional.includes("workspace") || archetype.required.includes("workspace");
  const hasNotifications = optional.includes("notification_action") || archetype.required.includes("notification_action");

  const pack = {
    name,
    display_name: state.displayName?.trim() || name.replace(/-/g, " ").replace(/\b\w/g, (char) => char.toUpperCase()),
    version: "0.1.0",
    domain: {
      domain_name: state.displayName?.trim() || name,
      app_type: archetype.id,
      target_users: [state.targetUser?.trim() || "developer"],
      product_purpose: state.description?.trim() || "A local AgentForge app.",
      main_user_goals: ["configure_app_blueprint", "run_agentforge_plan", "generate_with_cli"],
    },
    app_archetype: archetype.id,
    required_shell_modules: archetype.required,
    optional_shell_modules: optional,
    customization: createCustomization(state, archetype.id),
    capabilities: [
      {
        name: "ingest_records",
        purpose: "Load deterministic fixture records through the provider interface.",
        input_summary: "POST /ingest",
        output_shape: { fields: ["raw_records_inserted", "normalized_inserted", "run_id"] },
        mutates_state: true,
        data_mode: state.fixtureEnabled ? "fixture_provider" : "configured_provider",
        deterministic_test_safe: state.fixtureEnabled,
        implementation_status: "planned",
      },
      {
        name: "score_records",
        purpose: "Score normalized records with deterministic heuristics.",
        input_summary: "POST /score",
        output_shape: { fields: ["scores_written", "rescore"] },
        mutates_state: true,
        data_mode: "deterministic_heuristics",
        deterministic_test_safe: true,
        implementation_status: "planned",
      },
    ],
    ui_surfaces: [
      {
        surface_type: "operations_panel",
        renderer: "OpsPanel",
        data_source: "ingest_records, score_records",
        section: "operations",
        expected_data_shape: "Run controls, activity status, and recent results.",
        empty_state: "Ready. No recent operations.",
      },
    ],
    providers: {
      record_sources: [
        {
          name: "fixture",
          class: "FixtureRecordProvider",
          interface: "RecordProvider",
          source: "deterministic in-code fixture list",
          current_status: state.fixtureEnabled ? "planned" : "optional",
        },
      ],
    },
    adapters: [
      {
        name: "normalized_dto_from_raw",
        purpose: "Convert raw provider records into a stable normalized DTO.",
        normalized_shape: ["external_id", "source", "title", "category", "value", "ingested_at"],
      },
    ],
    run_history: {
      enabled: archetype.required.includes("pipeline") || optional.includes("pipeline"),
      table_name: "provider_runs",
      tracked_fields: ["provider_name", "started_at", "finished_at", "status", "stats", "error"],
      frontend_surface: "run_history_table",
    },
    notification_actions: hasNotifications
      ? [
          {
            name: "record_decision",
            trigger: "user chooses an action in the triage UI",
            delivery_channel: "preview",
            delivery_mode: state.notificationMode || "preview_only",
            decision_states: ["pending", ...actionLabels],
            dedupe_key: "record_id + action_type",
            persistence_table: "record_actions",
            history_table: "record_action_events",
            preview_table: "notification_previews",
          },
        ]
      : [],
    seed_data: state.fixtureEnabled ? { fixture_provider_records: "backend/app/providers/fixture/records.py" } : {},
    tests: {
      expectations: {
        no_live_provider_in_tests: true,
        no_live_llm_in_tests: true,
        deterministic_fixture_data: state.fixtureEnabled,
      },
      commands: {
        backend: "pytest",
        frontend_build: "npm run build",
        frontend_lint: "npm run lint",
      },
    },
    future_extensions: {
      features: ["repo_analyzer", "deploy_planner", "real_delivery_adapters", "live_llm_provider"],
    },
    compatibility_gaps: archetype.status === "planned" ? ["deploy_planner_app is a future archetype"] : [],
  };

  if (hasAgentRuntime) {
    pack.agent_runtime = {
      enabled: true,
      provider_mode: state.llmMode || "scripted",
      scripted_fixture_path: "backend/app/agent/providers.py",
      conversation_persistence: { enabled: true, tables: ["conversations", "conversation_messages"] },
      streaming: {
        enabled: true,
        endpoint: "/agent/chat/stream",
        events: ["message_start", "text_delta", "tool_call", "tool_result", "error", "done"],
      },
      guardrails: { reject_empty_message: true },
      tools: [
        {
          name: "score_records",
          purpose: "Run deterministic scoring through the generated tool registry.",
          input_schema: { rescore: { type: "boolean", required: false, default: false } },
          output_schema: { fields: ["scores_written", "rescore"] },
        },
      ],
      scripted_turns: [
        {
          match: "score",
          tool_calls: [{ name: "score_records", arguments: { rescore: false } }],
          final_text: "I scored the fixture records with the deterministic adapter.",
        },
      ],
    };
  }

  if (hasWorkspace) {
    pack.workspace = {
      enabled: true,
      persistence: {
        table_name: "workspace_widgets",
        fields: ["id", "widget_type", "title", "source_tool", "data", "position", "metadata"],
      },
      default_layout: [],
      remove_enabled: true,
      reorder_enabled: true,
      empty_state: "No widgets yet. Ask the agent to pin a result to the workspace.",
      frontend_surface: "workspace_panel",
    };
    pack.tool_widget_compatibility = {
      score_records: ["summary_card"],
      get_scored_records: ["ranking_list", "score_table"],
    };
    pack.widgets = ["summary_card", "ranking_list", "score_table", "run_history_list", "notification_preview_card", "action_history_list"].map(
      (widgetType) => ({
        widget_type: widgetType,
        renderer: widgetType.split("_").map((part) => part[0].toUpperCase() + part.slice(1)).join(""),
        compatible_source_tools: widgetType === "summary_card" ? ["score_records"] : ["get_scored_records"],
        section: "workspace",
        expected_data_shape: "Generic deterministic payload rendered by the workspace.",
        empty_state: "No widget data.",
        implementation_status: "planned",
      }),
    );
    pack.ui_surfaces.push({
      surface_type: "workspace_panel",
      renderer: "WorkspacePanel",
      data_source: "workspace_widgets",
      section: "dashboard_workspace",
      expected_data_shape: "Persisted workspace widgets.",
      empty_state: "No widgets yet.",
    });
  }

  return pack;
}

function createProjectWorkspaceBlueprint(state, archetype, name, optional) {
  const displayName = state.displayName?.trim() || name.replace(/-/g, " ").replace(/\b\w/g, (char) => char.toUpperCase());
  return {
    name,
    display_name: displayName,
    version: "0.1.0",
    domain: {
      domain_name: displayName,
      app_type: archetype.id,
      target_users: [state.targetUser?.trim() || "project operator"],
      product_purpose: state.description?.trim() || "A local project workspace for tasks, notes, and agent-assisted planning.",
      main_user_goals: ["seed_sample_workspace", "manage_project_tasks", "pin_agent_workspace_widgets"],
    },
    app_archetype: archetype.id,
    required_shell_modules: archetype.required,
    optional_shell_modules: optional,
    customization: createCustomization(state, archetype.id),
    capabilities: [
      {
        name: "seed_sample_workspace",
        purpose: "Create deterministic sample projects and tasks for local validation.",
        input_summary: "POST /seed",
        output_shape: { fields: ["created_projects", "created_tasks"] },
        mutates_state: true,
        data_mode: "deterministic_fixture_data",
        deterministic_test_safe: true,
        implementation_status: "planned",
      },
      {
        name: "manage_tasks",
        purpose: "Create tasks, update status/priority, and add project notes.",
        input_summary: "POST /tasks, PATCH /tasks/{task_id}, POST /projects/{project_id}/notes",
        output_shape: { fields: ["projects", "tasks", "activity"] },
        mutates_state: true,
        data_mode: "database",
        deterministic_test_safe: true,
        implementation_status: "planned",
      },
    ],
    ui_surfaces: [
      { surface_type: "project_overview", renderer: "ProjectPanel", data_source: "projects, tasks", section: "workspace", expected_data_shape: "Projects with task counts, owners, status, and due dates.", empty_state: "No projects yet. Seed the sample workspace." },
      { surface_type: "task_board", renderer: "TaskPanel", data_source: "tasks", section: "planning", expected_data_shape: "Task rows with status, priority, owner, and due date.", empty_state: "No tasks yet." },
    ],
    providers: { sample_workspace: [{ name: "fixture", source: "deterministic in-code project/task seed data", current_status: state.fixtureEnabled ? "planned" : "optional" }] },
    adapters: [],
    seed_data: state.fixtureEnabled ? { sample_projects: "backend/app/services/projects.py" } : {},
    agent_runtime: {
      enabled: true,
      provider_mode: state.llmMode || "scripted",
      scripted_fixture_path: "backend/app/agent/runtime.py",
      conversation_persistence: { enabled: true, tables: ["conversations", "conversation_messages"] },
      streaming: { enabled: true, endpoint: "/agent/chat/stream", events: ["message_start", "tool_call", "tool_result", "text_delta", "done"] },
      guardrails: { reject_empty_message: true },
      tools: [
        { name: "list_tasks", purpose: "List project tasks.", input_schema: {}, output_schema: { fields: ["tasks"] } },
        { name: "summarize_project", purpose: "Summarize project status counts.", input_schema: {}, output_schema: { fields: ["summary", "projects"] } },
        { name: "pin_task_list", purpose: "Pin current task list into the workspace.", input_schema: {}, output_schema: { fields: ["pinned", "widget"] } },
      ],
      scripted_turns: [{ match: "tasks", tool_calls: [{ name: "list_tasks", arguments: {} }], final_text: "I listed the current project tasks." }],
    },
    workspace: {
      enabled: true,
      persistence: { table_name: "workspace_widgets", fields: ["id", "widget_type", "title", "source_tool", "data", "position", "metadata"] },
      default_layout: [],
      remove_enabled: true,
      reorder_enabled: false,
      empty_state: "No widgets yet. Ask the agent to pin a project summary or task list.",
      frontend_surface: "workspace_panel",
    },
    tool_widget_compatibility: { list_tasks: ["task_list", "summary_card"], summarize_project: ["project_summary", "summary_card"], pin_task_list: ["task_list"] },
    widgets: ["project_summary", "task_list"].map((widgetType) => ({
      widget_type: widgetType,
      renderer: widgetType.split("_").map((part) => part[0].toUpperCase() + part.slice(1)).join(""),
      compatible_source_tools: widgetType === "task_list" ? ["list_tasks", "pin_task_list"] : ["summarize_project"],
      section: "workspace",
      expected_data_shape: widgetType === "task_list" ? "Task rows with status and priority." : "Project summary with task counts.",
      empty_state: "No widget data.",
      implementation_status: "planned",
    })),
    tests: { expectations: { no_live_provider_in_tests: true, no_live_llm_in_tests: true, deterministic_fixture_data: state.fixtureEnabled }, commands: { backend: "pytest", frontend_build: "npm run build", frontend_lint: "npm run lint" } },
    future_extensions: { features: ["auth", "teams", "calendar_integrations", "live_llm_provider"] },
    compatibility_gaps: [],
  };
}

function createCustomization(state, archetypeId) {
  const description = state.description?.trim() || "A local AgentForge app.";
  const targetUser = state.targetUser?.trim() || (archetypeId === "project_workspace_app" ? "project operator" : "operator");
  if (archetypeId === "project_workspace_app") {
    return {
      app: {
        subtitle: description,
        target_user_label: targetUser,
        workflow_label: "Project command center",
      },
      agent_starters: ["list tasks", "summarize project", "pin task list"],
      workspace: {
        empty_state: "Ask the agent to pin a project summary or task list.",
        widget_label: "widgets",
        pinned_label: "Pinned project context",
      },
      project_workspace: {
        project_label: { singular: "project", plural: "projects" },
        task_label: { singular: "task", plural: "tasks" },
        activity_label: "Notes and activity",
        sample_data_label: "sample workspace",
      },
    };
  }
  const [singular, plural] = recordLabelsFromText(`${state.name || ""} ${state.displayName || ""} ${description}`);
  return {
    app: {
      subtitle: description,
      target_user_label: targetUser,
      workflow_label: `${capitalize(singular)} review`,
    },
    agent_starters: [`score the ${plural}`, `show best ${plural}`, `pin the scored ${plural} to the workspace`],
    workspace: {
      empty_state: `Ask the agent to pin scored ${plural}, notification previews, or action history.`,
      widget_label: "widgets",
      pinned_label: "Pinned context",
    },
    scoring: {
      record_label: { singular, plural },
      criteria_labels: ["Fit", "Priority", "Risk"],
      review_queue_label: `Scored ${capitalize(plural)}`,
      notification_label: "Notification Previews",
      sample_data_label: `demo ${plural}`,
    },
  };
}

function recordLabelsFromText(value) {
  const text = String(value || "").toLowerCase();
  if (text.includes("ticket")) return ["ticket", "tickets"];
  if (text.includes("candidate") || text.includes("resume") || text.includes("applicant")) return ["candidate", "candidates"];
  if (text.includes("account") || text.includes("renewal") || text.includes("customer success")) return ["account", "accounts"];
  if (text.includes("lead") || text.includes("sales")) return ["lead", "leads"];
  if (text.includes("job") || text.includes("opportunity")) return ["opportunity", "opportunities"];
  return ["record", "records"];
}

function capitalize(value) {
  return String(value || "").replace(/^\w/, (char) => char.toUpperCase());
}

export function createBlueprintYaml(state) {
  return `${yaml(createBlueprint(state))}\n`;
}

export function validateBuilderState(state) {
  const issues = [];
  const archetype = archetypes.find((item) => item.id === state.archetype);
  if (!archetype) issues.push("Choose a known archetype.");
  if (archetype?.status === "planned") issues.push("This archetype is planned and will report generator gaps.");
  if (!String(state.name || "").trim()) issues.push("App name is required.");
  if ((state.selectedModules || []).includes("live_llm_provider")) issues.push("Live LLM provider is not supported in v0.7.1.");
  if ((state.selectedModules || []).includes("repo_analyzer")) issues.push("Repo analyzer is an analysis-only CLI report, not a generated app module.");
  return issues;
}

export const customization = {
  app: {
    name: "Project Workspace Demo",
    subtitle: "A local task planning workspace with seeded projects, deterministic persistence, scripted agent tools, and pinned widgets.",
    targetUserLabel: "project operator",
    workflowLabel: "Project command center",
  },
  agentStarters: ["list tasks", "summarize project", "pin task list"],
  workspace: {
    emptyState: "Ask the agent to pin a project summary or task list.",
    widgetLabel: "widgets",
    pinnedLabel: "Pinned project context",
  },
  scoring: {
    recordLabel: { singular: "record", plural: "records" },
    criteriaLabels: ["Fit", "Priority", "Risk"],
    reviewQueueLabel: "Scored Records",
    notificationLabel: "Notification Previews",
    sampleDataLabel: "demo records",
  },
  projectWorkspace: {
    projectLabel: { singular: "project", plural: "projects" },
    taskLabel: { singular: "task", plural: "tasks" },
    activityLabel: "Notes and activity",
    sampleDataLabel: "sample workspace",
  },
} as const;

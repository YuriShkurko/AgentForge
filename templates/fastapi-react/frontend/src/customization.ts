export const customization = {
  app: {
    name: "Hybrid Scoring Demo",
    subtitle: "Review fixture or imported records, run deterministic scoring, preview notifications, and pin agent results into a persisted workspace.",
    targetUserLabel: "operator",
    workflowLabel: "Review workflow",
  },
  agentStarters: ["score the records", "show best records", "pin the scored records to the workspace"],
  workspace: {
    emptyState: "Ask the agent to pin scored records, notification previews, or action history.",
    widgetLabel: "widgets",
    pinnedLabel: "Pinned context",
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

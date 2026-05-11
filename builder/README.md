# AgentForge Blueprint Builder

The Blueprint Builder is a small local/dev UI for drafting AgentForge App Blueprints. It supports two modes:

- Static/manual mode: open `index.html` directly, edit the fields, copy or download the YAML.
- Scripted planner mode: run `agentforge serve-builder`, open the printed URL, then draft/refine/validate through the local Python planner.

In both modes, use the CLI as the source of truth:

```bash
agentforge plan path/to/domain-pack.yaml
agentforge generate path/to/domain-pack.yaml
```

It does not call a live LLM, inspect repositories, convert existing apps, deploy infrastructure, or modify files automatically. When the local planner server is running, planner output is validated through `agentforge.pack.load_pack` before it is shown as a draft. `agentforge plan` remains authoritative validation before generation.

Planner mode can:

- draft from a short app idea;
- ask clarifying questions for vague ideas;
- refine a draft with bounded instructions;
- show assumptions, warnings, YAML, and CLI commands;
- validate the current draft against the Python generator schema.

For a CLI-only starter file:

```bash
agentforge init-blueprint my-app --optional-module agent_runtime
```

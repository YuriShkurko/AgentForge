# AgentForge Blueprint Builder

The Blueprint Builder is a small local/dev UI for drafting AgentForge App Blueprints. It is intentionally static: open `index.html` in a browser, edit the fields, copy or download the YAML, then use the CLI as the source of truth:

```bash
agentforge plan path/to/domain-pack.yaml
agentforge generate path/to/domain-pack.yaml
```

It does not call a live LLM, inspect repositories, convert existing apps, deploy infrastructure, or modify files automatically. The UI mirrors the current generator schema closely enough to draft valid YAML, while `agentforge plan` and `agentforge.pack.load_pack` remain authoritative validation.

For a CLI-only starter file:

```bash
agentforge init-blueprint my-app --optional-module agent_runtime
```

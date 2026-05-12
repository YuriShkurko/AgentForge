---
name: agentforge-template-change
description: Use when changing AgentForge generated app templates, examples, generator output, FastAPI/React demo behavior, or tests. Ensures template/example parity and validates generated-app changes safely.
---

# AgentForge Template Change

Use this skill for changes under `templates/fastapi-react`, `examples/hybrid-scoring-demo`, generator code, or tests that affect generated FastAPI/React apps.

## Principles

- Treat `templates/fastapi-react` as the source of generated app behavior.
- Keep `examples/hybrid-scoring-demo` in sync when it is the checked-in generated demo.
- Preserve no-key local demo behavior unless the user explicitly asks otherwise.
- Do not introduce live API calls, external credentials, deployment, or non-deterministic CI behavior by default.

## Common workflow

1. Edit the template first.
2. Mirror equivalent files into the example if applicable:
   ```bash
   cp templates/fastapi-react/<path> examples/hybrid-scoring-demo/<path>
   ```
3. Add or update backend integration/unit tests in the template.
4. Update template README and example README when user-facing behavior changes.
5. Run focused validation before broad validation.

## Validation commands

For backend template changes:

```bash
cd templates/fastapi-react/backend && python -m pytest -q
```

For frontend template changes:

```bash
cd templates/fastapi-react/frontend && npm run build
```

For generator or parity-sensitive changes:

```bash
python -m pytest tests/generator -q
```

If time is limited, run the narrowest relevant test first, then report what was and was not run.

## Final response checklist

- List changed areas by path.
- Summarize behavior change from a user's perspective.
- Include validation commands and results.
- Call out any existing unrelated modified files seen in `git status` only if relevant to handoff.

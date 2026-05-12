---
name: scribe-planning
description: Use when starting, finishing, or changing scope on AgentForge work that should be tracked in the local Scribe artifact store. Helps find the latest plan/task, record implementation notes, and avoid losing project intent.
---

# Scribe Planning

Use this skill whenever the user asks about the latest plan, starts a new project phase, asks what to do next, or wants durable project memory updated.

## Local Scribe commands

This repository uses the wrapper:

```bash
./scribe-local.cmd <command>
```

The wrapper sets `SCRIBE_ROOT` to this repo's `.scribe` directory. Prefer it over plain `scribe`.

## Start-of-work checklist

1. Inspect current Scribe state:
   ```bash
   ./scribe-local.cmd list
   ./scribe-local.cmd motd
   ```
2. If the user refers to a plan/spec/task, show it:
   ```bash
   ./scribe-local.cmd show <ID>
   ```
3. For implementation work tied to a draft spec, create a task with `--depends-on <SPEC_ID>` instead of `--parent` because specs are leaf artifacts in this store:
   ```bash
   ./scribe-local.cmd create --kind task --scope AgentForge --depends-on <SPEC_ID> --title "..." --goal "..."
   ```

## During work

- Keep Scribe advisory; do not let artifact bookkeeping block code fixes.
- Record important decisions in a named section:
  ```bash
  ./scribe-local.cmd section add <TASK_ID> implementation "..."
  ```
- If a task depends on a draft spec, Scribe may refuse to mark the task complete. In that case, leave the task draft and add an implementation/status section explaining what shipped.

## End-of-work checklist

1. Add a concise implementation/validation section to the related task or spec.
2. Mention exact validation commands in the final user response.
3. Do not mark draft-spec-dependent tasks complete unless Scribe allows it.

# Safe Patch Bundle and Approved Apply

`agentforge prepare-extension` is the v0.8.1-v0.8.3 bridge after `agentforge plan-extension`: v0.8.1 creates bundles, v0.8.2 applies approved low-risk files, and v0.8.3 improves previews, dry-run safety reporting, and interactive confirmation.

## Modes

```bash
agentforge prepare-extension ../my-project --output agentforge-output/my-project-extension
agentforge prepare-extension analysis.json --from-report --output agentforge-output/from-report
agentforge prepare-extension ../my-project --modules agent_runtime --dry-run
agentforge prepare-extension ../my-project --modules agent_runtime --apply
agentforge prepare-extension ../my-project --modules agent_runtime --apply --yes
```

Default behavior creates a patch bundle/preview only. It does **not** modify the target repository. `--dry-run` prints planned bundle/apply writes, dirty git state, overwrite conflicts, safety checks, validation commands, and next steps without creating bundle output or target files.

## Bundle contents

- `README.md`
- `manifest.json`
- `extension-plan.md`
- `file-impact.md`
- `migration-phases.md`
- `validation-checklist.md`
- `patch-preview.md`
- `proposed-files/` with AgentForge migration docs, extension plan docs, validation checklists, TODOs, env suggestions, and an App Blueprint seed when available

## Preview output

Text and Markdown previews include Summary, Selected Modules, Planned Operations, Apply-Eligible Files, Refused / Skipped Operations, Safety Checks, Validation Checklist, and Next Steps. JSON output includes stable fields such as `mode`, `target_repo`, `selected_modules`, `planned_operations`, `apply_eligible_operations`, `refused_operations`, `skipped_operations`, `safety_checks`, `warnings`, and `next_steps`.

## Apply restrictions

Apply mode requires `--apply` plus either an interactive `yes` confirmation or `--yes`. It:

- refuses dirty git working trees unless `--allow-dirty` is passed;
- refuses overwrites unless `--overwrite` is passed;
- writes only low-risk AgentForge docs, checklists, and App Blueprint seed files;
- produces `AGENTFORGE_APPLICATION_MANIFEST.json`;
- never stages, commits, pushes, deploys, installs dependencies, runs target scripts, calls live LLMs/APIs, or edits runtime/business logic.

If stdin is non-interactive and `--yes` is omitted, apply fails safely after printing the preview. Not allowed in v0.8.3: package/lockfile edits, app router/main edits, existing frontend/backend runtime edits, CI workflow mutation, dependency additions, business logic edits, or generated code execution.

## Rollback

Delete the AgentForge docs/blueprint/checklist files written by apply mode. Since AgentForge does not stage or commit, normal git review remains under user control.

# AgentForge Repo Analyzer

`agentforge analyze-repo` is the v0.7 analysis-only local repository analyzer.

It inspects a local project directory and prints an advisory AgentForge compatibility and migration report. It does **not** modify the analyzed repository. In v0.8, analyzer JSON can also feed `agentforge plan-extension` to produce a planning-only file impact and migration plan.

## Commands

```bash
agentforge analyze-repo path/to/repo
agentforge analyze-repo path/to/repo --format md
agentforge analyze-repo path/to/repo --format json
agentforge analyze-repo path/to/repo --json
agentforge analyze-repo path/to/repo --output repo-analysis.md --format md
```

Options:

- `--format text|md|json`: choose report format. Default is `text`.
- `--json`: shortcut for JSON output.
- `--output <path>`: write the report to the requested path instead of stdout.
- `--max-files <n>`: cap scanned files for safety and deterministic runtime.
- `--include-tests`: include deep test directory content sniffing. Test framework config/package references can still be detected without this flag.
- `--no-blueprint-draft`: omit the draft App Blueprint seed section.

## Safety boundaries

The analyzer is intentionally conservative:

- no target repository writes;
- no generated patches;
- no repo conversion;
- no deployment planning or execution;
- no live LLM calls;
- no external API or internet requirement;
- no GitHub API calls;
- no secret value extraction.

Secret risk detection is limited to safe filename/pattern signals such as environment-like files. Report evidence uses relative paths and short labels rather than raw source excerpts.

## Ignored directories

The scanner skips common generated, vendor, cache, and local state directories by default:

- `node_modules`
- `.venv`
- `venv`
- `__pycache__`
- `.git`
- `dist`
- `build`
- `.next`
- `coverage`
- `playwright-report`
- `test-results`
- `.scribe`
- `.tmp`

## What the report contains

Reports include:

1. Repository basics: name, path, Git directory signal, top-level directories, package/build files, monorepo hint, and scan cap status.
2. Stack detection: backend, frontend, data, testing, devops, AI/agent, and observability signals.
3. Architecture signals: API routes, services/domain layers, providers/adapters, models/schemas, components/pages, background jobs, notifications/actions, and dashboard/workspace surfaces.
4. AgentForge module compatibility table.
5. Likely archetype candidates with confidence and evidence.
6. Risks and blockers.
7. Advisory phased migration plan.
8. Optional draft App Blueprint seed for review.

## Compatibility statuses

- `compatible`: strong evidence exists for the module or support capability.
- `partial`: related structure exists, but AgentForge boundaries or tests are incomplete.
- `missing`: no useful signal was detected.
- `conflict`: detected patterns oppose AgentForge safety or architecture assumptions.
- `unknown`: evidence is insufficient for a confident classification.

The analyzer is conservative. A `partial` or `missing` status is not a failure; it identifies where migration work would be needed.

## Using the migration plan

The migration plan is advisory only. Treat it as a review checklist before creating or editing an App Blueprint. It generally starts with Blueprint alignment and deterministic tests, then moves toward provider/adapter boundaries, pipeline/scoring, agent runtime, workspace/dashboard, notification/triage, and CI/local validation as relevant.

The draft Blueprint seed is not written to the analyzed repo and is not guaranteed to be a complete `domain-pack.yaml`. Review it, then use `agentforge init-blueprint`, the Blueprint Builder, or manual editing to create a real App Blueprint.

## Builder handoff

For existing repositories, the intended v0.7.1 flow is:

1. Run `agentforge analyze-repo ../my-project --json --output report.json`.
2. Open the Blueprint Builder.
3. Paste the JSON report into **Start from an existing repo**.
4. Review detected stack, archetype, module compatibility, migration phases, and the draft Blueprint seed.
5. Optionally run `agentforge plan-extension report.json --from-report --format md --output extension-plan.md` for a planning-only file impact and migration sequence.
6. Create/review a real App Blueprint, then run `agentforge plan` and `agentforge generate` from the CLI.

The browser builder does not perform filesystem analysis or extension planning itself; it only displays report text you explicitly paste.

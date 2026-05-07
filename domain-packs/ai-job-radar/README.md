# AI Job Radar Domain Pack

This pack describes the current AI Job Radar domain extracted from the sibling `AIJobRadar` application. It is documentation and metadata only; it does not change runtime behavior.

AI Job Radar is a job discovery and triage pipeline for a developer/job seeker. It ingests jobs from email and web/source adapters, normalizes inconsistent provider payloads, deduplicates postings, scores fit against a candidate technical profile, explains fit/strictness, sends Telegram alerts, and provides React operations and triage views.

## Shell Versus Pack

The reusable Agent Shell candidate is not a chat shell in this app today. The reusable parts are the operational shell around pipelines: provider/adapters, persistence, run history, deterministic testable services, background worker scheduling, notification dispatch, observability, debug MCP, and React operations surfaces.

This Domain Pack owns the AI Job Radar-specific surface:

- Job source providers for LinkedIn alerts, LinkedIn IMAP, Startup for Startup, optional LinkedIn public search, and mock friend data.
- Job normalization, dedupe, technology extraction, fit scoring, strictness scoring, recommendation, and explanation shapes.
- Candidate profile providers from Reactive Resume JSON or a deterministic git repository scan.
- Telegram notification and review/triage commands for job decisions.
- React surfaces for operations, scored job cards, triage, provider runs, normalized jobs, and rendered PNG cards.
- Parser, scoring, strictness, Telegram parse, and normalization tests.

## Current Capabilities

The current backend is a FastAPI application with domain/application/infrastructure boundaries. Its main flows are:

- Ingest pull providers through `POST /ingestion/pull`.
- Ingest LinkedIn alert emails through JSON, multipart, raw bytes, or IMAP sync endpoints.
- Normalize raw jobs into `NormalizedJobDTO` and skip duplicate or out-of-location postings.
- Score jobs with deterministic heuristics against a CV-derived or repo-derived technical profile.
- List normalized jobs, scored jobs, Easy Apply stats, and provider runs.
- Render job cards in React and optionally export a PNG through Playwright.
- Send Telegram messages/photos and record notification outcomes.
- Triage jobs in a swipe UI and persist APPLY/MAYBE/SKIP decisions.
- Expose Prometheus/Grafana observability and read-only debug MCP tools.

No active runtime LLM prompt, chat agent, or tool-calling mediator was found. `profile_llm_enrich` and `llm_summary` fields exist, but scoring explanations are heuristic.

## AgentForge Use

A future AgentForge generator could use this pack to scaffold a job-search app from reusable infrastructure:

- Register job source provider ports and normalization adapters.
- Generate the normalized job, score explanation, provider run, notification, and decision schemas.
- Wire deterministic mock/parser fixtures for CI.
- Generate operations UI surfaces for pipeline controls, run history, scored cards, and triage.
- Install background worker jobs for ingest, IMAP, score, and notify intervals.
- Add observability and read-only debug MCP as optional shell capabilities.

The pack deliberately does not define Business Insight-style workspace widgets because AI Job Radar does not currently have persisted agent widgets.

## Comparison With Business Insight

Shared/reusable candidates between Business Insight and AI Job Radar:

- Provider/adapter pattern for messy external data.
- Persistence-backed run history and inspectable operational state.
- Deterministic mock or fixture data for tests.
- Scoring/explanation pattern: convert raw evidence into a score, reasons, limitations/risks, and a recommendation.
- Notification/action loop: surface a result, let the user act, and persist the decision.
- Observability and local validation commands.
- Reusable frontend operations surfaces for cards, tables, filters, status chips, and action controls.

Project-specific AI Job Radar parts:

- Job posting schemas, technology extraction, location filters, fit/strictness scoring, and APPLY/MAYBE/SKIP decisions.
- LinkedIn alert parsing, IMAP sync, Startup for Startup parsing, optional Crawl4AI LinkedIn public search, and Telegram job-card formatting.
- Candidate CV/repo profile extraction.
- Triage swipe UI and job card image rendering.

Project-specific Business Insight parts:

- Review analytics, competitor comparisons, business health, signal timelines, money flow, opportunities, action plans, dashboard sections, and agent workspace widget compatibility.

What should become Agent Shell:

- Chat, streaming, tool calling, workspace persistence, and widget lifecycle for Business Insight-style agent apps.
- Operational pipeline shell for AI Job Radar-style apps: run controls, run history, background jobs, persistence, notifications, observability, debug MCP, and deterministic tests.

What should become reusable adapter/pipeline infrastructure:

- Provider result contracts, normalization adapters, dedupe hooks, provider run logging, source health/error capture, replayable parser tests, score/result explanation schemas, and notification dispatch records.

What should remain domain-specific:

- The job schema, scoring heuristics, candidate profile logic, provider parsers, Telegram copy/buttons, triage semantics, and future application-material generation.

## Future Extensions

Future ideas are listed separately in `domain-pack.yaml` and should not be treated as current capabilities. Likely extensions include cover letter generation, CV tailoring, apply bundles, browser apply automation, recruiter/contact enrichment, job market analytics, score tuning/replay dashboards, deploy planner packs, generic ingestion/scoring templates, and an agentic chat layer for job-search questions.

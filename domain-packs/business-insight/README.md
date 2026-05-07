# Business Insight Domain Pack

This pack describes the current Business Insight domain extracted from the existing MicroSaas application. It is documentation and metadata only; it does not change runtime behavior.

Business Insight is an agentic business dashboard for local SMB owners and managers. It helps users understand customer feedback, compare competitors, monitor business health, inspect timelines and money flow, find opportunities, create action plans, and build dashboard presentations.

## Shell Versus Pack

The reusable Agent Shell owns chat, streaming, tool calling, conversations, workspace persistence, widget lifecycle events, dashboard layout behavior, guardrails, and scripted LLM testing infrastructure.

This Domain Pack owns the Business Insight-specific surface:

- Review, analysis, competitor, demo signal, Business Insight, and dashboard workspace tools.
- Business Insight widget types and compatible renderer components.
- Review and LLM provider choices.
- Demo/offline signal behavior.
- Prompt routing for review analytics, business health, signal timeline, money flow, opportunities, and action plans.
- Scripted and Playwright test scenarios for this domain.

## Current Capabilities

The current app includes review ingestion through mock, offline, Outscraper, and simulation providers; analysis and competitor comparison services; an agent tool registry; persistent workspace widgets; demo sales/operations/local/social/financial signals; and deterministic scripted LLM test flows.

The strongest current compatibility rule is that persisted widgets must use a supported `source_tool` and `widget_type` pair. The app already enforces this and has a special guard to route money-flow requests to `get_financial_flow` plus the `money_flow` widget instead of generic bar charts.

## Scaffolder Use

A future scaffolder could read `domain-pack.yaml` to generate a Business Insight app from a reusable Agent Shell:

- Register tools and schemas.
- Register widget renderers and dashboard sections.
- Generate compatibility validation.
- Install prompt sections and routing rules.
- Wire mock/offline/demo providers for local development and CI.
- Generate deterministic scripted LLM and Playwright coverage.

Planned capabilities such as Google Business Profile, Square POS, Toast POS, social imports, CSV/manual imports, deploy planner/deployer packs, and AI Job Radar extraction are listed as future extensions, not current capabilities.

---
name: demo-flow-review
description: Use when reviewing or improving AgentForge's first-run/demo flow, onboarding, README demo steps, or generated-app walkthroughs. Keeps the path simple: idea to local demo to user data to optional live provider.
---

# Demo Flow Review

Use this skill for AgentForge onboarding, builder flow, generated app demo flow, README walkthroughs, screenshots/GIF planning, or anything meant to help a new user understand the product quickly.

## Core narrative

AgentForge should communicate this progression:

1. **No-key demo** — run locally with fixture data and scripted agent.
2. **Your data** — paste/upload records and use deterministic scoring/triage.
3. **Optional live agent** — add OpenAI later only if the user wants real agent responses.

Do not let optional provider/API-key work obscure the no-key path.

## Review checklist

- Can a new user identify the first command or first button within 5 seconds?
- Is there a visible success moment after each step?
- Does each step naturally lead to the next one?
- Are risky/future features labeled as optional or planned?
- Are validation commands shown near the steps they validate?
- Is the demo script short enough to record as a GIF or narrated walkthrough?

## Recommended demo structure

1. Start app.
2. Ingest demo data.
3. Score records.
4. Preview notifications or triage one record.
5. Ask/pin something via the scripted agent/workspace.
6. Import a small JSON sample as user data.
7. Score again and show the imported record in the same flow.

## Anti-overkill rules

- Avoid multi-page onboarding unless the current screen is truly overloaded.
- Prefer inline helper text and better labels over new modals.
- Prefer one good sample JSON block over a full mapping wizard.
- Keep future OpenAI/provider copy short and clearly optional.

## Final response

When used, report the before/after user journey and any remaining friction points.

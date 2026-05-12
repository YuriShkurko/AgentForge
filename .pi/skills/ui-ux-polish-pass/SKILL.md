---
name: ui-ux-polish-pass
description: Use for lightweight UI/UX review and polish of AgentForge builder or generated React app screens. Focuses on clarity, hierarchy, empty/loading/error states, button labels, and low-risk improvements without redesigning the product.
---

# UI/UX Polish Pass

Use this skill when the user asks to improve UI, make a screen clearer, review a flow, or polish React components without a full redesign.

## Scope guardrails

- Prefer small changes with high clarity impact.
- Do not introduce new UI libraries unless explicitly requested.
- Preserve existing data flow and API contracts unless the user asks for deeper product changes.
- Avoid pixel-perfect overwork; optimize for understandable demo/user flow.

## Review checklist

1. **User goal clarity**
   - Is the primary next action obvious?
   - Does the screen explain whether API keys/accounts are required?
   - Are demo mode, user-data mode, and optional live mode clearly separated?

2. **Hierarchy**
   - Headings should describe outcomes, not internals.
   - Primary actions should be visually/positionally prioritized.
   - Advanced/secondary actions should not compete with first-run actions.

3. **States**
   - Empty state tells the user what to do next.
   - Loading state confirms work is happening.
   - Error state includes actionable recovery copy.
   - Success state summarizes what changed.

4. **Copy**
   - Button labels should be specific: `Import JSON Records`, not just `Submit`.
   - Avoid implementation jargon unless the user is a developer.
   - Keep safety copy explicit: `Works without API keys`.

5. **Accessibility basics**
   - Inputs have labels.
   - Buttons are disabled only when necessary.
   - Text contrast and font sizes remain readable.
   - Dynamic results are visible as text, not only color.

## Implementation pattern

- First, inspect the component and surrounding CSS.
- Make the smallest useful component/CSS edits.
- If behavior changes, update tests/docs where appropriate.
- Validate with `npm run build` for frontend changes.

## Final response

Summarize the UX improvement as user-facing changes, not just file edits.

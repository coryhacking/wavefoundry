# Dashboard Wave Framework Visualization

Change ID: `12rqj-enh dashboard-wave-framework-visualization`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-05-20
Wave: `12rnv agent-prompt-harness`

## Rationale

The dashboard currently exposes operational state, agent groupings, and wave records, but it does not help a user understand how the Wave Framework itself fits together. A first-time operator has to infer the process from separate docs and prompt surfaces.

This change adds an explanatory dashboard layer that visualizes the Wave Framework as a set of clickable sections and process arrows. The current design focuses on how a change moves through a wave, from planning through closure, with explicit review gates and loop-backs where the operator has to make a decision.

## Requirements

1. The dashboard home page must include a visible Wave Framework visualization section.
2. The visualization must be divided into clickable sections that represent the major framework stages.
3. The visualization must show the flow direction with arrows and represent review loops where a stage can send the operator back to a prior stage.
4. Clicking a section must open a short description of that stage without leaving the dashboard.
5. The descriptions must explain the process in operational terms, using change and wave language to show what decision the operator makes and where the review gate happens.
6. The visualization must fit the existing dashboard visual language and not require a separate application surface.
7. The change must not alter wave state, agent discovery, or docs lint behavior.
8. The change must remain local to the dashboard and its supporting docs unless a follow-on architecture update is explicitly justified.

## Scope

**Problem statement:** The dashboard shows live state, but it does not teach the Wave Framework flow. Users can see what is present, but not how the framework stages connect.

**In scope:**

- A dashboard visualization panel for the Wave Framework
- Clickable sections for the main process stages
- Visual arrows and loop-backs for the operator path
- Descriptive copy for each process
- Dashboard UI wiring for the interaction model
- Supporting tests for the new section layout and click behavior

**Out of scope:**

- Changing wave lifecycle rules
- Changing agent taxonomy or dashboard agent grouping
- Changing the underlying snapshot data contract
- Changing prompt surfaces or seed prompts as part of this feature unless later required by the implementation
- Building a new documentation site outside the dashboard

## Acceptance Criteria

- AC-1: The dashboard home page includes a Wave Framework visualization section.
- AC-2: The visualization is split into clickable sections that represent the framework processes.
- AC-3: Clicking a section opens process guidance inside the dashboard.
- AC-4: The process guidance is readable and specific enough to explain the role of that part of the framework.
- AC-5: The existing dashboard state and agent sections still render normally.
- AC-6: Dashboard tests cover both the presence of the visualization and the clickable section behavior.

## Tasks

- [x] Design the section model for the Wave Framework visualization.
- [x] Add the new dashboard UI section and click behavior.
- [x] Write the explanatory copy for each framework process section.
- [x] Add or update dashboard tests for the new interaction.
- [x] Verify the new section does not regress existing dashboard surfaces.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| dashboard-ux | implementer | — | Add the new visualization surface and interaction model. |
| dashboard-verification | qa-reviewer | dashboard-ux | Verify the section order, click behavior, and unchanged existing surfaces. |
| dashboard-review | code-reviewer | dashboard-ux | Check the UI change for clarity and consistency with the existing dashboard style. |

## Serialization Points

- `dashboard.js` and `dashboard.css` if the visualization needs new shared layout primitives.
- Any dashboard copy source if the section descriptions are centralized rather than inline.

## Affected Architecture Docs

`docs/references/dashboard-adapter-model.md` should be updated if the new visualization changes how the dashboard presents the framework process model to operators. If the feature remains a purely presentational addition with no data-contract change, the architecture update can be deferred with rationale recorded during implementation.

## AC Priority

(Populated at Prepare wave.)

| AC   | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The visualization itself is the feature. |
| AC-2 | required | Clickable sections are the core interaction model. |
| AC-3 | required | The dashboard must explain processes in place. |
| AC-4 | important | The copy must teach, not merely label. |
| AC-5 | required | Existing dashboard surfaces must remain intact. |
| AC-6 | important | Tests should prove the interaction and layout. |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-05-20 | Change doc created for a dashboard visualization that explains the Wave Framework through clickable process sections. | Operator request; `dashboard.js`; `dashboard.css` |
| 2026-05-20 | Implemented framework-flow visualization cards and dialogs in the dashboard; renamed stages to Plan Change / Prepare Wave / Implement Wave / Review Wave / Close & Maintain, simplified the Implement Wave teaching copy, tightened the dialogs into centered step-chip diagrams, updated the Review stage wording to start from Review, removed redundant sequence sentences from the dialog details, renamed the close-stage rail to Completed Wave and then shortened it again to Signoff → Archive, added stage-color tints to the dashboard cards, gave the open-wave, metric, and change surfaces a light resting shadow with a matching hover shadow, then removed hover affordance from the outer wave cards so only the internal IDs read as clickable, styled the dialog step number as plain oversized title text, then reduced its size and aligned it to the text baseline, reset the close button so it does not inherit browser chrome, widened the flow-note line so it uses the dialog space instead of wrapping early, changed the Prepare Wave mini-flow to Review → Open questions → Prepare Wave, stacked the file-dialog title/count so the Changed files header does not crowd its file-count subtitle, moved the agent dialog category badge below the title, constrained that badge to its text width instead of the full header column, and restored spacing between the process step number and title text. | `python3 -B -m unittest discover -s .wavefoundry/framework/scripts/tests -p 'test_dashboard_server.py'` |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-05-20 | Keep the feature inside the existing dashboard rather than creating a separate explainer tool. | Users already look at the dashboard for live status; the explanatory layer should live where the state lives. | External docs site, separate tutorial page, or modal-only explainer (rejected for fragmentation). |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| The new visualization becomes decorative instead of useful | Keep each section tied to a concrete framework process and pair it with concise operational guidance. |
| The additional UI pushes important state lower on the page | Preserve the current dashboard sections and keep the visualization compact. |
| Clickable sections introduce too much interaction complexity | Use a simple, consistent dialog or accordion pattern already compatible with the dashboard. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.

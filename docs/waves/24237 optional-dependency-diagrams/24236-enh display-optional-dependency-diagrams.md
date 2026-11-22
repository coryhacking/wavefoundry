# Show dependency diagrams in the local dashboard

Change ID: `24236-enh display-optional-dependency-diagrams`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-11-21
Wave: 24237 optional-dependency-diagrams

## Rationale

The [pilot](../../reports/review-handoff-graph-pilot.md) found that both readers chose the correct actions. One reader found the four-way join implicit in a table. The dashboard currently displays the equivalent diagram as code.

## Product Intent

An operator opening a spec or wave sees which tasks can run together and which checks must finish before the next step. Authors can keep a linear plan short. The review ledger owns status and signoffs.

## Requirements

1. Recommend an optional fenced Mermaid dependency diagram where work branches or rejoins. Place cross-spec dependencies in the wave record and internal dependencies in their spec. Use a list for simple sequences and a sentence explaining the join. Preserve required planning fields and machine-readable dependencies.
2. Render the documented dependency flowchart subset offline in the existing dashboard document views. Support the pilot's flowchart LR, rectangular nodes with quoted plain-text labels, bare node references and directed edges on separate lines. Also support top-down flow. Show complete readable source for unsupported syntax, incomplete fences, over-budget input or layout failure. Preserve surrounding Markdown and ordinary code blocks.
3. Treat diagram text as untrusted. Use fixed drawing elements and text nodes only. Keep directives, links, HTML and unknown syntax inert. Bound diagram work before layout. Expose the relationships to assistive technology, preserve readable labels on narrow screens and isolate multiple diagrams. Reuse shipped assets and the existing document path.

## Scope

Planning guidance, its shipped and self-hosted copies, dashboard Markdown rendering and regression coverage. Scheduling, workflow authority and generated live status stay outside this change.

## Acceptance Criteria

- [x] AC-1: In a spec detail view, the exact pilot example displays seven labeled nodes and eight directed connections offline. A wave detail view displays a cross-spec diagram through the same path. Readers can inspect relationships without interpreting a drawing.
- [x] AC-2: Unsupported, oversized, malformed and unclosed inputs display their original source. Adjacent Markdown, ordinary fences and independent diagrams still work. Document text cannot initiate fetches or create active content.
- [x] AC-3: Shipped and local planning guidance tells authors when and where to add a diagram, documents supported syntax and keeps list-only plans and established dependency records valid.

## Tasks

- [x] Implement the shared renderer and regression tests.
- [x] Align shipped and local planning guidance and verify the example through the dashboard.
- [x] Run focused checks, docs validation and framework tests, then complete delivery review.

## Agent Execution Graph

Dashboard and planning changes can proceed independently after readiness. QA exercises the pilot against their combined output.

## Serialization Points

- `.wavefoundry/framework/dashboard/`
- `.wavefoundry/framework/scripts/tests/test_dashboard_server.py`
- `.wavefoundry/framework/seeds/170-plan-spec.prompt.md`
- `.wavefoundry/framework/install/plan-template.md`
- `docs/plans/plan-template.md`
- `docs/prompts/plan-spec.prompt.md`

## Affected Architecture Docs

The existing dashboard document dialog and local asset boundary remain in place. The planning guidance documents the supported syntax.

## AC Priority

| AC | Priority | Reason |
| --- | --- | --- |
| AC-1 | required | Establishes the operator outcome on actual document views. |
| AC-2 | required | Protects existing documents and the local browser boundary. |
| AC-3 | required | Downstream and local authors need the same convention. |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-11-21 | Used the completed historical replay to scope this change to presentation. | Pilot spec 23z5n and its report. |
| 2026-11-21 | Verified both document dialogs in headless Chrome with the shipped assets and a disposable project. At 390 px the staged pilot and admitted spec each displayed all seven pilot nodes and the wave displayed its cross-spec join. Both dialogs stayed within their viewport and neither requested an external URL. Before the change both showed code. | Local browser trial and the portable regression in test_dashboard_server.py. |
| 2026-11-21 | Compared all eight directed edges with the expected endpoints in the SVG and accessible list. Reversing every arrow caused the regression to fail even with the same node and edge counts. | RenderMarkdownishDependencyDiagramTests.test_dependency_diagrams_and_source_fallback. |
| 2026-11-21 | All four delivery reviewers approved. Independent verification cleared the planning syntax correction. The default framework suite passed 13,194 tests across 253 files with 12 skips (803 seconds). | Current framework test receipt and the wave review ledger. |

## Decision Log

| Date | Decision | Reason |
| --- | --- | --- |
| 2026-11-21 | Render a small dependency syntax with the existing offline layout capability. | A full Mermaid runtime brings a second rendering stack. Static screenshots require authors to maintain two copies. Both exceed the pilot's needs. |

## Risks

Layout can fail or finish after the document changes. Keep source available and discard stale results. Keep titles and arrows usable in both themes and on narrow screens.

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.

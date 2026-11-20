# Make dashboard requirements and lifecycle progress readable

Change ID: `23td1-bug render-numbered-dashboard-requirements`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-11-19
Wave: 23td0 downstream-lifecycle-compatibility

## Rationale

The dashboard displays the four numbered requirements in 23tcz as a single paragraph. The Markdown renderer groups hyphen bullets but sends numbered lines to its paragraph buffer.

## Product Intent

A reviewer can scan and refer to each numbered requirement in a spec opened from the dashboard. AC-1 checks the reported document view.

## Requirements

1. Display consecutive numbered Markdown items as an ordered list with a distinct item and visible number for each. Preserve inline formatting, wrapped item text and the starting number.
2. Keep bullets, headings, paragraphs, fenced code and hidden comments working in the shared renderer. Switching between ordered and unordered items starts the appropriate list.

3. In the Progress card show a compact aligned row per metric with its label, bar and fraction. Put repeated count breakdowns and scope details in accessible details on hover and keyboard focus. Keep missing coverage and unavailable states visible. Long labels must not overlap the bar, including at narrow widths.
4. In the Wave lifecycle diagram and its stage dialogs use the actual Plan spec shortcut and the project planning noun for its document. Respect custom distribution names and keep machine fields and routes stable.

## Scope

Shared dashboard Markdown rendering, Progress presentation and Wave lifecycle labels. No edits to requirements in the source documents or changes to the counting rules. Existing support for a single list level is sufficient.

## Acceptance Criteria

- [x] AC-1: Opening 23tcz in the local dashboard shows four individually numbered requirements in order, with inline code retained. A renderer test checks the ordered list, individual item nodes and continuation text.
- [x] AC-2: A non-one start and transitions to bullets and following prose render correctly. A fenced or commented numbered line creates no visible list item.

- [x] AC-3: Four progress rows retain their fractions and accessible breakdowns without repeating them below each bar. Wide and narrow viewports show no label overlap. A coverage warning and unavailable values remain visible.
- [x] AC-4: The Wave lifecycle diagram and its stage details identify Plan spec and specs under the shipped profile. Under a renamed profile they identify the configured shortcut and planning document. Existing workflow routes still open.

## Tasks

- [x] Render and style ordered items using the existing list and inline formatting logic.
- [x] Compact the Progress rows and apply profile-aware wording to Wave lifecycle.
- [x] Run the dashboard regressions and verify the served spec view.

## Agent Execution Graph

| Workstream | Owner | Depends on |
| --- | --- | --- |
| Markdown renderer and controls | Dashboard implementer | Readiness |
| Served spec check | QA | Renderer |

## Serialization Points

- `.wavefoundry/framework/dashboard/ds/wfds.js`
- `.wavefoundry/framework/dashboard/dashboard.css`
- `.wavefoundry/framework/scripts/tests/test_dashboard_server.py`
- `.wavefoundry/framework/dashboard/dashboard.js`
- `.wavefoundry/framework/scripts/dashboard_lib.py`
- `.wavefoundry/framework/scripts/tests/test_dashboard_progress_ui.py`

## Affected Architecture Docs

The dashboard uses its existing shared Markdown renderer.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Reproduces the reader's reported difficulty. |
| AC-2 | required | Protects other Markdown blocks rendered by the same component. |
| AC-3 | required | Keeps the counts readable and preserves coverage limitations. |
| AC-4 | required | The lifecycle diagram teaches the actual workflow. |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-11-19 | Located the paragraph fallback for numbered lines in renderMarkdownish. | Supplied screenshot of the 23tcz Requirements section. |
| 2026-11-19 | Verified the live dashboard in Chrome at 1440 and 375 CSS pixels. | Progress shrank from 559 to 210 px and from 865 to 350 px. Labels clear every bar, hover and keyboard disclose counts, and the 23tcz Requirements display as one ordered list with four entries and inline code. The first stage reads Plan spec. |
| 2026-11-19 | Implemented the lifecycle diagram and stage details against the selected repository's planning shortcut and document noun. A custom plan button opens the existing plan dialog. | Dashboard terminology and served JavaScript regression checks passed (13 tests). |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-11-19 | Extend the shared renderer. | Numbered requirements are valid in existing specs. | Adding blank lines to each spec still produces separate paragraphs without list semantics. |

## Risks

| Risk | Mitigation |
| --- | --- |
| Ordered and unordered items share a buffer. | Exercise transitions in both directions. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.

# Dashboard markdown renderer: thematic break (`---`) → `<hr>`

Change ID: `1p8pg-bug dashboard-markdown-thematic-break-render`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-06-28
Wave: `1p8ph windows-console-window-dashboard-hardening`

## Rationale

In the dashboard's agent-detail dialog (full-doc markdown render, wave 12mc6), a standalone `---` separator renders as the literal text `---` instead of a horizontal rule. The shared renderer **`renderMarkdownish`** (`.wavefoundry/framework/dashboard/ds/wfds.js:360`) classifies each line as fenced-code → table (`|`) → heading (`###`/`##`/`#`) → list (`- `) → **else paragraph**. There is **no thematic-break branch**, so a line of `---` (which does not match the `- ` list prefix) falls through to the `else` and is emitted as `<p>---</p>`. The doc metadata block is stripped before render, so any `---` that reaches the renderer is a genuine section separator. This affects every doc rendered through `renderMarkdownish` (agent docs, change descriptions, journals) that contains a `---` — hence it appears only in some windows.

## Requirements

1. Add a thematic-break branch to `renderMarkdownish` that emits `<hr>` for a standalone rule line matching `^(-{3,}|\*{3,}|_{3,})$`, with `flushList()` + `flushTable()` first (close any open list/table before the rule). Covers `---`, `***`, `___`.
2. Place the branch so it does not disturb existing classification (a `---`/`***`/`___` inside a fenced code block or a table must NOT be converted; a `- ` list item is unaffected since it requires the trailing space).
3. Shared-renderer fix → benefits all dashboard markdown surfaces (agent docs, change descriptions, journals).

## Scope

**Problem statement:** the dashboard markdown renderer omits thematic breaks, rendering `---`/`***`/`___` as literal paragraphs.

**In scope:** `renderMarkdownish` in `.wavefoundry/framework/dashboard/ds/wfds.js`; a dashboard render test.

**Out of scope:** the pythonw spawns (`1p8pe`), the dashboard lock race (`1p8pf`), any other markdown feature (setext headings, etc.) — `---` is treated as a thematic break, not a setext underline (this renderer has no setext support and the corpus uses `---` as separators).

## Acceptance Criteria

- [x] AC-1: `renderMarkdownish` renders a standalone `---` (and `***`, `___`) line as an `<hr>` element, not a `<p>`. (Branch `^(-{3,}|\*{3,}|_{3,})$` → `h("hr")` with `flushList()`/`flushTable()`; `test_dashboard_server.RenderMarkdownishThematicBreakTests` executes the real renderer via node and asserts `---`/`***`/`___` → `<hr>`.)
- [x] AC-2: existing rendering is unchanged — fenced code containing `---`, table rows, headings, `- ` list items, and normal paragraphs render exactly as before (a `---` inside a code block stays literal). (Node test: fenced `---` → single `<pre>` literal; `- a/- b` → `<ul>`; `# Title` → `<h1>`.)
- [x] AC-3: a dashboard render test asserts the `<hr>` conversion (and the code-block-`---`-stays-literal guard); full suite + docs-lint pass. (`RenderMarkdownishThematicBreakTests` — always-on source-text guard + node-execution behavioral assertions.)

## Tasks

- [x] Add the thematic-break branch (`^(-{3,}|\*{3,}|_{3,})$` → `h("hr")`, with flushList/flushTable) to `renderMarkdownish` (before the final `else`, after the `- ` list check; the code-block collector already `continue`s first).
- [x] Test: standalone rule → `<hr>`; code-block `---` → literal; list/heading/table unaffected (`RenderMarkdownishThematicBreakTests`).
- [x] Suite + docs-lint.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| renderMarkdownish hr branch + test | implementer | — | front-end JS (ds/wfds.js) |

## Serialization Points

- Independent of `1p8pe`/`1p8pf` (front-end JS only; no shared files).

## Affected Architecture Docs

`N/A` (dashboard front-end behavior; covered by a dashboard test).

## AC Priority

(Populated at Prepare wave.)

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | The reported defect. |
| AC-2 | required | Must not regress existing rendering. |
| AC-3 | required | Regression coverage. |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-06-28 | Planned from an operator screenshot — `---` rendering literally in the agent dialog. Confirmed: `renderMarkdownish` has no thematic-break branch. | `.wavefoundry/framework/dashboard/ds/wfds.js:360` (line classification, no `hr`); wave 12mc6 full-doc agent-dialog render. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-06-28 | Treat `---`/`***`/`___` as a thematic break (`<hr>`), not a setext heading underline. | The renderer has no setext support and the agent-doc corpus uses `---` as section separators; metadata is stripped before render so a leading `---` is never frontmatter. | Setext h2 (rejected — wrong for the corpus, no setext elsewhere). |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| A `---` inside a fenced code block gets converted. | The branch runs only outside the `codeLines` collector (the code-block guard already `continue`s first); AC-2 tests this. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.

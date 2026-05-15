# Dashboard: Markdown Table Rendering

Change ID: `12mgm-enh dashboard-markdown-table-render`
Change Status: `complete`
Previous Change Status: `planned`
Owner: Engineering
Status: active
Last verified: 2026-05-14
Wave: TBD

## Rationale

The agent dialog full-doc render (12mc6-enh) noted markdown table support as a known limitation — tables render as raw pipe-delimited text. Agent docs, the CIA role doc in particular, use tables extensively (retrieval strategy, tag vocabulary, usage-by-agent, write permissions). Rendering them as proper HTML tables makes the dialog significantly more readable.

## Requirements

1. `renderMarkdownish` in `dashboard.js` must detect markdown table blocks and render them as an HTML `<table>` with a `<thead>` (first row) and `<tbody>` (remaining data rows), skipping the separator row (`|---|---|`).
2. Each cell's content must pass through `renderInline` so bold and code formatting inside cells is preserved.
3. A CSS rule for `.agent-dialog-body table` must produce a readable, compact table style consistent with the existing dialog design.
4. The existing paragraph/bullet/heading logic must be unaffected for non-table lines.

## Scope

**Problem statement:** Markdown tables in agent docs render as raw pipe-delimited text in the agent dialog.

**In scope:**

- Table detection and rendering in `renderMarkdownish`
- CSS for `.agent-dialog-body table`
- `framework_edit_allowed` gate required for `dashboard.js` and `dashboard.css`

**Out of scope:**

- Table rendering outside the agent dialog
- Alignment hints from separator row (`:---:`, `---:`)

## Acceptance Criteria

- AC-1: A markdown table in an agent doc renders as a styled HTML table in the dialog, not raw pipe-delimited text.
- AC-2: The separator row (`|---|---|`) is not rendered as a table row.
- AC-3: Bold and inline code inside table cells render correctly.
- AC-4: Non-table content immediately before and after a table renders correctly.

## Tasks

- [ ] Extend `renderMarkdownish` to collect consecutive `|`-prefixed lines into a table block, parse header/separator/data rows, render as `<table>/<thead>/<tbody>/<tr>/<th>/<td>` with `renderInline` on each cell.
- [ ] Add `.agent-dialog-body table` CSS.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
|---|---|---|---|
| js-render | implementer | — | dashboard.js + dashboard.css; framework_edit_allowed gate |

## Serialization Points

- `framework_edit_allowed` gate required for `dashboard.js` and `dashboard.css`.

## Affected Architecture Docs

N/A — confined to dashboard rendering; no boundary or flow changes.

## AC Priority

| AC | Priority | Rationale |
|----|----------|-----------|
| AC-1 | required | Core fix — tables must not render as raw text |
| AC-2 | required | Separator row must be suppressed |
| AC-3 | important | Inline formatting common in CIA tables |
| AC-4 | required | Must not regress surrounding content |

## Progress Log

| Date | Update | Evidence |
|------|--------|----------|
| 2026-05-14 | Change scoped; noted as known limitation in 12mc6-enh | 12mc6 Scope section |

## Decision Log

| Date | Decision | Reason | Alternatives |
|------|----------|--------|--------------|
| 2026-05-14 | Collect consecutive pipe lines as a block | Simple, no lookahead needed | Per-line state machine — more complex for no gain |

## Risks

| Risk | Mitigation |
|------|------------|
| Pipe characters in inline code inside cells | Cell content is passed through renderInline which handles backtick spans before splitting — split on `|` after inline spans are resolved, or treat raw `|` in code as literal |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.

# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-05-14

wave-id: `12mgm dashboard-table-render`
Title: Dashboard Table Render

## Changes

Change ID: `12mgm-enh dashboard-markdown-table-render`
Change Status: `complete`
Previous Change Status: `planned`

## Objective

Extend `renderMarkdownish` in `dashboard.js` to render markdown tables as styled HTML tables in the agent dialog, eliminating the raw pipe-delimited text fallback noted as a known limitation in wave 12mc3.

Completed At: 2026-05-14

## Wave Summary

One change: add table block detection and rendering to `renderMarkdownish`, with matching CSS. Tables in agent docs (CIA retrieval strategy, tag vocabulary, usage-by-agent) will render as proper HTML tables.

## Journal Watchpoints

- **Watchpoint:** `framework_edit_allowed` gate required for `dashboard.js` and `dashboard.css` — open before editing, close immediately after.

## Review Evidence

- wave-council-readiness: approved (2026-05-14 — single focused change; approach straightforward; no architectural impact)
- wave-council-delivery: approved (2026-05-14 — implemented; 1172 tests pass; docs-lint clean)
- operator-signoff: approved (2026-05-14)

## Dependencies

- No external wave dependencies.

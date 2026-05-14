# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-05-14

wave-id: `12m6b dashboard-ac-numbered-list-parser`
Title: Dashboard: Parse Numbered-List AC Items

## Objective

Fix `_AC_LINE_RE` in `dashboard_lib.py` to match ordered list items (`1.`, `2.`, …) in addition to bullet list items so that change docs using numbered ACs are visible in the dashboard.

## Changes

Change ID: `12m6b-bug ac-line-regex-misses-numbered-lists`
Change Status: `complete`

Completed At: 2026-05-14

## Wave Summary

One-line regex fix extending `_AC_LINE_RE` to accept `(?:-|\d+\.)` as the list prefix.

## Journal Watchpoints

- **Watchpoint: checkbox marks on numbered items** — `[x]` / `[ ]` syntax on numbered list items must parse correctly; verify test coverage for both marked and unmarked numbered ACs.

## Review Evidence

- wave-council-readiness: approved (2026-05-14 — single regex extension, root cause confirmed, Option A chosen over doc migration)
- wave-council-delivery: approved (2026-05-14 — fix applied, tests pass)
- operator-signoff: approved

## Dependencies

- No external wave dependencies.

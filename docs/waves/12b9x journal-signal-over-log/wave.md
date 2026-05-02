# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-05-02

wave-id: `12b9x journal-signal-over-log`
Title: Journal Signal Over Log

## Changes

Change ID: `12b9v-feat journal-signal-over-log`
Change Status: `complete`

Change ID: `12bb9-doc mcp-search-tool-routing-guidance`
Change Status: `complete`

Completed At: 2026-05-02

## Wave Summary

Refactors the journal framework to enforce signal-over-log discipline: renames `Recent Captures` → `Active Signals`, adds a filter gate, reorders sections to front-load operating identity, and cleans up all five in-repo journals. Upgrade guidance is embedded in seed-160 so deployed repos get the same treatment on next upgrade.

## Journal Watchpoints

- Watchpoint: seed edits (006, 130, 210, 160) must be made under `seed_edit_allowed` gate — open immediately before edits, close immediately after.
- Follow-up: verify all five in-repo journals pass docs-lint after cleanup.
- Watchpoint: do not strip journal entries that carry genuine durable lessons — only remove wave-closed/change-shipped activity-log entries.

## Review Evidence

- wave-coordinator signoff: doc review, code review, architecture review complete — no concerns. All ACs verified, lint clean, stale references removed.

## Dependencies

- No external wave dependencies.

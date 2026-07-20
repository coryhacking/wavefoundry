# Decision: Inline a small stdlib `sqlite3` + `json` reader in `upgrade…

Owner: Engineering
Status: superseded
Last verified: 2026-07-18

Memory ID: `mem-decision-inline-a-small-stdlib-sqlite3-json-reader-in-upgrad`
Kind: `decision`
Confidence: 0.6
Created: 2026-07-18
Updated: 2026-07-18
Source exploration cost: 0
Source event: `decision-log:1rvfx-bug upgrade-graph-version-transition-log:6cbe53f749f757c2`
Validation: rewrite
Validated by: agent
Action delta: Use a small local stdlib probe when upgrade logic must inspect pre-extraction state; do not import replaceable or heavy framework modules.
Validation rationale: Upgrade executes across a framework replacement boundary, and the current implementation explicitly preserves an import-light, fail-safe probe for that reason.
Evidence verified: true
Current target verified: true
Canonical overlap: supplements
Superseded by: `mem-keep-upgrade-time-state-probes-stdlib-only`
## Summary

Decision (wave 1rvfy): Inline a small stdlib `sqlite3` + `json` reader in `upgrade_wavefoundry.py` rather than import `graph_indexer.read_state_builder_version`.. Rationale: The upgrade module deliberately avoids imports of framework code that gets replaced during extraction (and `graph_indexer` is heavy / tree-sitter-dependent, and may not import cleanly in a minimal upgrade context). The state files + `meta` schema (`builder_version` key) are stable; the inline reader mirrors the canonical function and is stdlib-only..

## Evidence

- `1rvfx-bug upgrade-graph-version-transition-log`
- `1rvfy`

## Targets

- `upgrade_wavefoundry.py`

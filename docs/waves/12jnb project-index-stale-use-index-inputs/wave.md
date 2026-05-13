# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-05-12

wave-id: `12jnb project-index-stale-use-index-inputs`
Title: Dashboard: Use Project Index Inputs for Stale Detection

## Objective

Stop idle dashboard-triggered project index rebuild loops by making project-layer stale detection use indexed project inputs instead of raw git history when `file_meta` is available.

## Changes

Change ID: `12jnb-bug project-stale-use-index-inputs-not-git-history`
Change Status: `complete`

Change ID: `12jne-enh dashboard-log-timestamps`
Change Status: `complete`

Change ID: `12jnf-bug dashboard-log-helper-unified-format`
Change Status: `complete`

Change ID: `12jng-bug remove-dialog-item-strikethrough`
Change Status: `complete`

Change ID: `12jnh-enh multi-language-code-navigation`
Change Status: `complete`

Change ID: `12jnj-enh treesitter-symbol-navigation`
Change Status: `complete`

Change ID: `12jnk-doc upgrade-and-mcp-guidance-clarity`
Change Status: `complete`

Change ID: `12jqm-bug mixed-language-navigation-aggregation`
Change Status: `complete`

Change ID: `12jv3-enh reference-filtering`
Change Status: `complete`

Change ID: `12jv4-enh python-reference-signal-and-limit`
Change Status: `complete`

Completed At: 2026-05-12

## Wave Summary

Completed follow-up to the dashboard index-monitoring fixes and adjacent MCP tooling improvements. The project layer now uses indexed project inputs as the primary stale signal, excludes host-local `.wavefoundry` runtime artifacts from semantic project inputs, keeps real project docs/code changes as true-positive stale triggers, uses one timestamp-first dashboard log format across indexing diagnostics and HTTP access logs, removes strike-through styling from completed AC/task dialog items, expands MCP symbol navigation beyond Python, uses tree-sitter-backed definitions and references for Java, C#, JavaScript, and TypeScript, preserves mixed-language aggregation across tree-sitter and fallback navigation paths, adds AST-backed Python call-site detection plus optional result capping for `code_references`, and clarifies both MCP tool-selection guidance and the target-repo framework upgrade flow across rendered docs and canonical seeds.

## Journal Watchpoints

- **Watchpoint: project runtime artifacts** — `.wavefoundry/dashboard-server.json` and `.wavefoundry/guard-overrides.json` are host-local operational files, not semantic project inputs, and must not keep the project docs/code index stale.
- **Watchpoint: project/file-meta parity** — the framework layer already prefers `file_meta` over generic git dirtiness; the project layer should not lag behind with different stale semantics.

## Review Checkpoints

- Prepare wave — readiness verdict: **pass** on 2026-05-12 for `12jv3-enh reference-filtering`. The change doc is complete, AC priority is recorded, and the review council aligned that the proposal is scoped correctly for implementation: `code_references` keeps its broad mode, higher-signal call-site classification is additive, and structural-first navigation is limited to primary languages with fallback retained.
- Wave Council — readiness roster (2026-05-12): fixed seats were `architecture-reviewer`, `security-reviewer`, `qa-reviewer`, and `reality-checker`; the rotating fifth seat was `performance-reviewer` because this change touches the MCP search/reference hot path. `reality-checker` served as the red-team seat and found no blockers, but called out the expected risks around over-filtering and parser gaps, both of which are already mitigated in the change doc by keeping broad behavior available and retaining fallback paths.
- Council moderator synthesis (2026-05-12): the council agreed the change is ready to implement because the contract is additive, the noisy-reference problem is real, and the acceptance criteria leave enough room to preserve existing behavior while improving signal for refactors.
- Implementation verification (2026-05-12): `code_references` now returns bucketed evidence with `reference_kind`, `counts`, `all_counts`, and optional `exclude_tests` / `exclude_docs` / `call_sites_only` filters; docs and tests are included in the broad response and sorted behind call sites. Verification passed with `python3 -B -m unittest discover -s .wavefoundry/framework/scripts/tests -p 'test_server_tools.py'`, `python3 -B .wavefoundry/framework/scripts/run_tests.py` (1125 tests), and `./.wavefoundry/bin/docs-lint`.
- Implementation verification (2026-05-12): `code_references` now returns bucketed evidence with `reference_kind`, `counts`, `all_counts`, `matched_count`, `matched_counts`, and optional `exclude_tests` / `exclude_docs` / `call_sites_only` / `limit` filters; Python call sites are detected structurally before broader text matches. Verification passed with `python3 -B -m unittest discover -s .wavefoundry/framework/scripts/tests -p 'test_server_tools.py'`, `python3 -B .wavefoundry/framework/scripts/run_tests.py`, and `./.wavefoundry/bin/docs-lint`.

## Review Evidence

- wave-council-readiness: approved (2026-05-12 — refreshed full-scope review covering `12jnb`, `12jne`, `12jnf`, `12jng`, `12jnh`, `12jnj`, `12jnk`, and `12jqm`: project stale detection now uses indexed inputs, dashboard logs are unified and timestamped, completed AC/task dialog items no longer strike through, symbol navigation is multi-language with tree-sitter-backed Java/C#/JavaScript/TypeScript support plus mixed-language aggregation preservation, and the MCP/upgrade guidance docs and canonical seeds are aligned)
- wave-council-readiness: approved (2026-05-12 — readiness review for `12jv3-enh reference-filtering`; fixed seats: architecture-reviewer, security-reviewer, qa-reviewer, reality-checker; rotating seat: performance-reviewer; red-team seat: reality-checker — council agreed the proposal is additive, broad `code_references` behavior remains available, and the structural-first / filterable output shape is ready for implementation)
- wave-council-delivery: approved (2026-05-12 — delivery review for `12jv4-enh python-reference-signal-and-limit`; fixed seats: architecture-reviewer, security-reviewer, qa-reviewer, reality-checker; rotating seat: performance-reviewer — Python call-site detection is AST-backed, `limit` preserves matched vs returned counts, and the broad fallback behavior remains intact)
- operator-signoff: approved

## Dependencies

- No external wave dependencies.

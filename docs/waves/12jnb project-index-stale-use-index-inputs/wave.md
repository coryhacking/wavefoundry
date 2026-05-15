# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-05-14

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

Change ID: `12jv5-enh exact-match-definition-and-richer-reference-buckets`
Change Status: `complete`

Change ID: `12jv6-enh non-call-site-reference-splits`
Change Status: `complete`

Change ID: `12jv7-enh sql-structural-navigation-and-indexing`
Change Status: `complete`

Change ID: `12jv8-enh sql-tree-sitter-auto-install`
Change Status: `complete`

Change ID: `12jv9-enh sql-extension-alias-detection`
Change Status: `complete`

Change ID: `12jva-enh ac-priority-order-mapping`
Change Status: `complete`

Change ID: `12jvb-enh ac-priority-lint-no-unknown`
Change Status: `complete`

Change ID: `12jvc-enh active-wave-scoped-metric-tiles`
Change Status: `complete`

Change ID: `12kfe-enh active-wave-pending-first-metric-tiles`
Change Status: `complete`

Change ID: `12kfe-enh active-wave-detail-dialog-pending-first`
Change Status: `complete`

Change ID: `12kff-enh active-wave-metric-subtext-total-only`
Change Status: `complete`

Change ID: `12kfh-enh active-wave-index-note-comma-separator`
Change Status: `complete`

Change ID: `12kfk-enh active-wave-footer-version-live-format`
Change Status: `complete`

Change ID: `12kfm-enh footer-distinguished-even-spacing`
Change Status: `complete`

Change ID: `12kfp-doc reuse-existing-change-and-extend-acs-tasks`
Change Status: `complete`

Change ID: `12kg8-enh sql-anonymous-block-chunking-qualified-fallback`
Change Status: `complete`

Change ID: `12kg9-enh dashboard-persistent-launcher-and-seed-reconciliation`
Change Status: `complete`

Change ID: `12kgw-bug walk-repo-node-modules-pruning`
Change Status: `complete`

Change ID: `12kgx-bug walk-repo-streamed-output-buffer-reduction`
Change Status: `complete`

Change ID: `12kgy-enh index-reload-file-stat-signature`
Change Status: `complete`

Change ID: `12kh0-enh sql-qualified-doc-mention-pass-and-build-stats-refresh`
Change Status: `complete`

Change ID: `12kh1-enh dashboard-repo-title-and-no-active-wave-fallback`
Change Status: `complete`

Change ID: `12kh2-bug active-change-dialog-header-overflow-wrap`
Change Status: `complete`

Change ID: `12kh3-enh progress-stats-always-visible-zero-total`
Change Status: `complete`

Change ID: `12kh4-enh dashboard-title-repo-only`
Change Status: `complete`

Change ID: `12kh5-enh pending-dialog-titles-when-no-active-wave`
Change Status: `complete`

Change ID: `12kh6-enh active-wave-tile-switches-to-pending-label`
Change Status: `complete`

Change ID: `12kh7-enh dashboard-stop-restart-mcp-commands`
Change Status: `complete`

Change ID: `12kh8-enh pending-ac-counts-use-visible-items`
Change Status: `complete`

Change ID: `12kh9-enh pending-waves-dialog-title`
Change Status: `complete`

Change ID: `12kha-enh active-wave-metric-tiles-use-active-labels`
Change Status: `complete`

Change ID: `12khb-bug exclude-wavefoundry-logs-from-project-stale-detection`
Change Status: `complete`


Change ID: `12khc-enh dashboard-index-build-guidance-background-rebuilds`
Change Status: `complete`

Change ID: `12khd-enh progress-card-uses-scoped-change-set`
Change Status: `complete`

Change ID: `12khe-enh semantic-index-tile-uses-generic-build-status`
Change Status: `complete`

Change ID: `12khf-enh semantic-index-detail-distinguishes-update-vs-rebuild`
Change Status: `complete`

Change ID: `12kq4-enh index-builder-writes-state-files`
Change Status: `complete`

Completed At: 2026-05-13

## Wave Summary

Completed follow-up to the dashboard index-monitoring fixes and adjacent MCP tooling improvements. The project layer now uses indexed project inputs as the primary stale signal, excludes host-local `.wavefoundry` runtime artifacts and dashboard logs from semantic project inputs, keeps real project docs/code changes as true-positive stale triggers, uses one timestamp-first dashboard log format across indexing diagnostics and HTTP access logs, removes strike-through styling from completed AC/task dialog items, expands MCP symbol navigation beyond Python, uses tree-sitter-backed definitions and references for Java, C#, JavaScript, and TypeScript, preserves mixed-language aggregation across tree-sitter and fallback navigation paths, adds AST-backed Python call-site detection plus optional result capping for `code_references`, and clarifies both MCP tool-selection guidance and the target-repo framework upgrade flow across rendered docs and canonical seeds.

## Journal Watchpoints

- **Watchpoint: project runtime artifacts** — `.wavefoundry/dashboard-server.json`, `.wavefoundry/guard-overrides.json`, and `.wavefoundry/logs/` are host-local operational artifacts, not semantic project inputs, and must not keep the project docs/code index stale.
- **Watchpoint: project/file-meta parity** — the framework layer already prefers `file_meta` over generic git dirtiness; the project layer should not lag behind with different stale semantics.

## Review Checkpoints

- Prepare wave — readiness verdict: **pass** on 2026-05-12 for `12jv3-enh reference-filtering`. The change doc is complete, AC priority is recorded, and the review council aligned that the proposal is scoped correctly for implementation: `code_references` keeps its broad mode, higher-signal call-site classification is additive, and structural-first navigation is limited to primary languages with fallback retained.
- Wave Council — readiness roster (2026-05-12): fixed seats were `architecture-reviewer`, `security-reviewer`, `qa-reviewer`, and `reality-checker`; the rotating fifth seat was `performance-reviewer` because this change touches the MCP search/reference hot path. `reality-checker` served as the red-team seat and found no blockers, but called out the expected risks around over-filtering and parser gaps, both of which are already mitigated in the change doc by keeping broad behavior available and retaining fallback paths.
- Council moderator synthesis (2026-05-12): the council agreed the change is ready to implement because the contract is additive, the noisy-reference problem is real, and the acceptance criteria leave enough room to preserve existing behavior while improving signal for refactors.
- Implementation verification (2026-05-12): `code_references` now returns bucketed evidence with `reference_kind`, `counts`, `all_counts`, and optional `exclude_tests` / `exclude_docs` / `call_sites_only` filters; docs and tests are included in the broad response and sorted behind call sites. Verification passed with `python3 -B -m unittest discover -s .wavefoundry/framework/scripts/tests -p 'test_server_tools.py'`, `python3 -B .wavefoundry/framework/scripts/run_tests.py` (1125 tests), and `./.wavefoundry/bin/docs-lint`.
- Implementation verification (2026-05-12): `code_references` now returns bucketed evidence with `reference_kind`, `counts`, `all_counts`, `matched_count`, `matched_counts`, and optional `exclude_tests` / `exclude_docs` / `call_sites_only` / `limit` filters; Python call sites are detected structurally before broader text matches. Verification passed with `python3 -B -m unittest discover -s .wavefoundry/framework/scripts/tests -p 'test_server_tools.py'`, `python3 -B .wavefoundry/framework/scripts/run_tests.py`, and `./.wavefoundry/bin/docs-lint`.
- Implementation verification (2026-05-13): common SQL aliases now route through the SQL chunking and navigation path alongside `.sql`, with tree-sitter-first parsing preserved when available and regex fallback retained. Verification passed with `python3 -B -m unittest discover -s .wavefoundry/framework/scripts/tests -p 'test_server_tools.py'`, `python3 -B .wavefoundry/framework/scripts/run_tests.py` (1131 tests), and `./.wavefoundry/bin/docs-lint`.
- Implementation verification (2026-05-13): anonymous SQL `DO $$...$$` and tagged `DO $tag$...$tag$` blocks now chunk as searchable units, schema-qualified SQL lookup retries the unqualified name before keyword fallback, and SQL files preserve a file-level safety-net chunk when no searchable SQL chunks would otherwise exist. `CHUNKER_VERSION` is `20`, so existing indexes rebuild cleanly. Verification passed with `python3 -B -m unittest discover -s .wavefoundry/framework/scripts/tests -p 'test_chunker.py'`, `python3 -B -m unittest discover -s .wavefoundry/framework/scripts/tests -p 'test_server_tools.py'`, `python3 -B .wavefoundry/framework/scripts/run_tests.py` (1139 tests), and `./.wavefoundry/bin/docs-lint`.
- Implementation verification (2026-05-13): the dashboard persistent launcher is now generated automatically, survives shell exit via `nohup`, writes logs to `.wavefoundry/logs/dashboard.log`, and remains the operator-facing `Start dashboard` shortcut while the low-level no-browser fallback stays documented. Verification passed with `python3 -B -m unittest discover -s .wavefoundry/framework/scripts/tests -p 'test_render_platform_surfaces.py'`, `python3 -B .wavefoundry/framework/scripts/run_tests.py` (1139 tests), and `./.wavefoundry/bin/docs-lint`.
- Implementation verification (2026-05-13): `walk_repo()` now prunes excluded directories before descending, keeps `.wavefoundry/` reachable, preserves the returned file set, and no longer relies on `Path.rglob("*")` for traversal. Verification passed with `PYTHONPATH=.wavefoundry/framework/scripts python3 -B -m unittest discover -s .wavefoundry/framework/scripts/tests -p 'test_indexer.py'`, `python3 -B .wavefoundry/framework/scripts/run_tests.py` (1140 tests), and `./.wavefoundry/bin/docs-lint`.
- Implementation verification (2026-05-13): `.wavefoundry/logs/` is excluded from the project walk and project stale detection, so the dashboard no longer rebuilds because of its own runtime log writes. Verification passed with `PYTHONPATH=.wavefoundry/framework/scripts python3 -B -m unittest discover -s .wavefoundry/framework/scripts/tests -p 'test_indexer.py'`, `python3 -B -m unittest discover -s .wavefoundry/framework/scripts/tests -p 'test_dashboard_server.py'` (111 tests), `python3 .wavefoundry/framework/scripts/run_tests.py` (1153 tests), and `./.wavefoundry/bin/docs-lint`.
- Implementation verification (2026-05-13): `walk_repo()` now streams accepted files directly into the result list instead of buffering every enumerated path, while preserving deterministic ordering and the same pruning/filter behavior. Verification passed with `PYTHONPATH=.wavefoundry/framework/scripts python3 -B -m unittest discover -s .wavefoundry/framework/scripts/tests -p 'test_indexer.py'`, `python3 -B .wavefoundry/framework/scripts/run_tests.py` (1141 tests), and `./.wavefoundry/bin/docs-lint`.
- Prepare wave — readiness verdict: **ready** on 2026-05-12 for `12jv5-enh exact-match-definition-and-richer-reference-buckets`, `12jv6-enh non-call-site-reference-splits`, and `12jv7-enh sql-structural-navigation-and-indexing`. All three change docs are complete, AC priority is recorded, and the scope remains additive: exact-match ranking plus richer buckets, finer non-call-site splits, and SQL structural navigation with regex fallback retained. Required review lanes for the new set are `code-reviewer`, `qa-reviewer`, and `architecture-reviewer`; `performance-reviewer` is additionally applicable for the SQL/indexer hot path.
- Prepare wave — readiness verdict: **ready** on 2026-05-12 for `12jv5-enh exact-match-definition-and-richer-reference-buckets`, `12jv6-enh non-call-site-reference-splits`, `12jv7-enh sql-structural-navigation-and-indexing`, and `12jv8-enh sql-tree-sitter-auto-install`. All four change docs are complete or ready, AC priority is recorded, and the scope remains additive: exact-match ranking plus richer buckets, finer non-call-site splits, SQL structural navigation with regex fallback retained, and installer parity for the SQL tree-sitter grammar. Required review lanes for the new set are `code-reviewer`, `qa-reviewer`, and `architecture-reviewer`; `performance-reviewer` is additionally applicable for the SQL/indexer hot path.
- Prepare wave — readiness verdict: **ready** on 2026-05-13 for `12jv9-enh sql-extension-alias-detection`. The new change doc is complete, AC priority is recorded, and the scope is additive: common SQL aliases should route through the existing SQL chunking and navigation path without changing parser behavior. Required review lanes are `code-reviewer`, `qa-reviewer`, and `architecture-reviewer`; `performance-reviewer` is optional but applicable if alias routing changes the hot path.
- Prepare wave — readiness verdict: **ready** on 2026-05-13 for `12jva-enh ac-priority-order-mapping`. The new change doc is complete, AC priority is recorded, and the scope is additive: dashboard AC summaries should read the ordered AC bullets directly when explicit IDs are absent so the visible tile counts match the actual wave contents. Required review lanes are `code-reviewer` and `qa-reviewer`; `performance-reviewer` is optional because the fix is parser-side and small.
- Prepare wave — readiness verdict: **ready** on 2026-05-13 for `12kh2-bug active-change-dialog-header-overflow-wrap`. The new change doc is complete, AC priority is recorded, and the scope is additive: long change IDs in the active changes dialog should stay inside the card boundary and remain readable. Required review lanes are `code-reviewer` and `qa-reviewer`; `performance-reviewer` is optional because this is a layout-only fix.
- Implementation verification (2026-05-13): exact-match definition ranking now prioritizes exact hits over partial hits, `code_references` exposes detailed `definition` / `import` / `mention` splits alongside broad buckets, SQL participates in structural chunking/navigation with regex fallback preserved, and common SQL aliases route through the same path. `CHUNKER_VERSION` is `19`, so a full rebuild is required to refresh existing indexes. Verification passed with `python3 -B -m unittest discover -s .wavefoundry/framework/scripts/tests -p 'test_server_tools.py'`, `python3 -B .wavefoundry/framework/scripts/run_tests.py` (1131 tests), and `./.wavefoundry/bin/docs-lint`.
- Implementation verification (2026-05-13): `wave_index_health` now refreshes `previous_build_stats` from the freshest finished build log, including the background code build log used by `setup_index.py --background-code`, so finished MCP-triggered and background index updates surface current stats without a restart. Verification passed with `python3 -B -m unittest discover -s .wavefoundry/framework/scripts/tests -p 'test_server_tools.py'` (417 tests), and `./.wavefoundry/bin/docs-lint`.
- Implementation verification (2026-05-13): dashboard AC parsing now falls back to AC Priority row order when explicit AC IDs are absent, so the visible AC tiles count the actual bullets rather than hiding `unknown` buckets. Verification passed with `python3 -B -m unittest discover -s .wavefoundry/framework/scripts/tests -p 'test_dashboard_server.py'`, `python3 -B .wavefoundry/framework/scripts/run_tests.py` (1132 tests), and `./.wavefoundry/bin/docs-lint`.
- Implementation verification (2026-05-13): docs-lint now fails admitted change docs whose Acceptance Criteria bullets are not fully accounted for by AC Priority rows, or whose AC Priority values are malformed. Verification passed with `python3 -B -m unittest discover -s .wavefoundry/framework/scripts/tests -p 'test_docs_lint.py'`, `python3 -B .wavefoundry/framework/scripts/run_tests.py` (1136 tests), and `./.wavefoundry/bin/docs-lint`.
- Implementation verification (2026-05-13): dashboard metric tiles for changes, ACs, and tasks now scope pending and total counts to the active wave(s) only, while the progress bars keep the broader repository-level totals. Verification passed with `python3 -B -m unittest discover -s .wavefoundry/framework/scripts/tests -p 'test_dashboard_server.py'`, `python3 -B .wavefoundry/framework/scripts/run_tests.py` (1136 tests), and `./.wavefoundry/bin/docs-lint`.
- Prepare wave — readiness verdict: **ready** on 2026-05-13 for `12kfe-enh active-wave-pending-first-metric-tiles`. The new change doc is complete, AC priority is recorded, and the scope is additive: the active-wave-scoped metric tiles should present pending as the headline number while keeping the scoped total visible. Required review lanes are `code-reviewer` and `qa-reviewer`; `performance-reviewer` is optional because this is a rendering-copy update.
- Prepare wave — readiness verdict: **ready** on 2026-05-13 for `12kff-enh active-wave-metric-subtext-total-only`. The new change doc is complete, AC priority is recorded, and the scope is additive: active-wave metric tiles should keep pending as the headline number while the subtext shows `pending, N total`. Required review lanes are `code-reviewer` and `qa-reviewer`; `performance-reviewer` is optional because this is a rendering-copy update.
- Prepare wave — readiness verdict: **ready** on 2026-05-13 for `12kfh-enh active-wave-index-note-comma-separator`. The new change doc is complete, AC priority is recorded, and the scope is additive: the Semantic Index tile should switch from `files / N chunks` to `files, N chunks` to match the rest of the tile copy. Required review lanes are `code-reviewer` and `qa-reviewer`; `performance-reviewer` is optional because this is a rendering-copy update.
- Prepare wave — readiness verdict: **ready** on 2026-05-13 for `12kh1-enh dashboard-repo-title-and-no-active-wave-fallback`. The new change doc is complete, AC priority is recorded, and the scope is additive: the dashboard tab title should use a repo-first label, and the active-wave metric tiles should fall back to repo-wide pending totals only when no wave is open. Required review lanes are `code-reviewer` and `qa-reviewer`; `performance-reviewer` is optional because this is a rendering-copy update.
- Implementation verification (2026-05-13): the dashboard footer now surfaces the Wavefoundry version up front, keeps the live/refresh indicator visible on the left, and leaves the updated timestamp on the right. Verification passed with `node --check .wavefoundry/framework/dashboard/dashboard.js` and `./.wavefoundry/bin/docs-lint`.
- Implementation verification (2026-05-13): the header no longer repeats the framework version, and the footer now reads as a footer line instead of a tile, keeps the Wavefoundry version in mixed case blue text with the same weight and size as the LIVE indicator, and tightens the extra space below the footer. Verification passed with `node --check .wavefoundry/framework/dashboard/dashboard.js`, `python3 -B -m unittest discover -s .wavefoundry/framework/scripts/tests -p 'test_dashboard_server.py'`, and `./.wavefoundry/bin/docs-lint`.
- Implementation verification (2026-05-13): the planning and implementation prompts now instruct agents to reuse an existing admitted change in the current wave when follow-up scope still fits, extending ACs and tasks instead of creating a fresh change. Verification passed with `./.wavefoundry/bin/docs-lint`.
- Implementation verification (2026-05-13): the Semantic Index tile now uses a comma separator in its subtext, matching the other active-wave metric tiles. Verification passed with `node --check .wavefoundry/framework/dashboard/dashboard.js` and `./.wavefoundry/bin/docs-lint`.
- Implementation verification (2026-05-13): active-wave metric tiles now show pending as the headline number and `pending, N total` in the subtext, without repeating the pending count. Verification passed with `node --check .wavefoundry/framework/dashboard/dashboard.js` and `./.wavefoundry/bin/docs-lint`.
- Implementation verification (2026-05-13): detail dialogs for changes, ACs, and tasks now sort pending entries before closed entries without changing counts. Verification passed with `python3 -B -m unittest discover -s .wavefoundry/framework/scripts/tests -p 'test_dashboard_server.py'` and `node --check .wavefoundry/framework/dashboard/dashboard.js`.
- Implementation verification (2026-05-13): the active-wave metric tiles now show pending as the headline number and `pending, N total` as secondary context, while the wave tile itself remains unchanged. Verification passed with `node --check .wavefoundry/framework/dashboard/dashboard.js` and `./.wavefoundry/bin/docs-lint`.
- Implementation verification (2026-05-13): the progress card now keeps AC and Task rows visible even when their totals are zero, showing `0/0` instead of hiding the rows. Verification passed with `python3 -B -m unittest discover -s .wavefoundry/framework/scripts/tests -p 'test_dashboard_server.py'` and `./.wavefoundry/bin/docs-lint`.
- Implementation verification (2026-05-13): the dashboard tab title now uses the repository name plus `Wavefoundry`, without the `Dashboard` suffix, and the browser/server title helpers agree. Verification passed with `python3 -B -m unittest discover -s .wavefoundry/framework/scripts/tests -p 'test_dashboard_server.py'` and `./.wavefoundry/bin/docs-lint`.
- Implementation verification (2026-05-13): when no wave is active, the Changes / ACs / Tasks detail dialogs now switch to pending wording and pending-scope content instead of retaining the active-wave labels. Verification passed with `python3 -B -m unittest discover -s .wavefoundry/framework/scripts/tests -p 'test_dashboard_server.py'` and `./.wavefoundry/bin/docs-lint`.
- Implementation verification (2026-05-13): the dashboard tab title is repo-first, and when no wave is active the Changes / ACs / Tasks tiles fall back to repo-wide pending totals while the active-wave behavior remains unchanged when a wave is open. Verification passed with `python3 -B -m unittest discover -s .wavefoundry/framework/scripts/tests -p 'test_dashboard_server.py'`, `python3 -B .wavefoundry/framework/scripts/run_tests.py` (104 tests in `test_dashboard_server.py`), and `./.wavefoundry/bin/docs-lint`.
- Implementation verification (2026-05-13): the active changes dialog header now wraps long change IDs before the status badge can escape the card boundary, keeping the shared dashboard dialogs visually contained. Verification passed with `python3 -B -m unittest discover -s .wavefoundry/framework/scripts/tests -p 'test_dashboard_server.py'` (105 tests), and `./.wavefoundry/bin/docs-lint`.

## Review Evidence

- wave-council-readiness: approved (2026-05-12 — refreshed full-scope review covering `12jnb`, `12jne`, `12jnf`, `12jng`, `12jnh`, `12jnj`, `12jnk`, and `12jqm`: project stale detection now uses indexed inputs, dashboard logs are unified and timestamped, completed AC/task dialog items no longer strike through, symbol navigation is multi-language with tree-sitter-backed Java/C#/JavaScript/TypeScript support plus mixed-language aggregation preservation, and the MCP/upgrade guidance docs and canonical seeds are aligned)
- wave-council-readiness: approved (2026-05-12 — readiness review for `12jv3-enh reference-filtering`; fixed seats: architecture-reviewer, security-reviewer, qa-reviewer, reality-checker; rotating seat: performance-reviewer; red-team seat: reality-checker — council agreed the proposal is additive, broad `code_references` behavior remains available, and the structural-first / filterable output shape is ready for implementation)
- wave-council-delivery: approved (2026-05-12 — delivery review for `12jv4-enh python-reference-signal-and-limit`; fixed seats: architecture-reviewer, security-reviewer, qa-reviewer, reality-checker; rotating seat: performance-reviewer — Python call-site detection is AST-backed, `limit` preserves matched vs returned counts, and the broad fallback behavior remains intact)
- operator-signoff: approved

## Dependencies

- No external wave dependencies.

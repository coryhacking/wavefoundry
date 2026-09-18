# Honor Configured Record Roots Through One Shared Path Resolver

Change ID: `1y042-enh record-roots-config-and-resolver`
Change Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-09-17
Wave: `1y0gz record-layout-roots`

## Rationale

**Brief.** Goal: let a downstream fork relocate its wave and plan roots by editing one set of module constants at merge time, with the shipped constants reproducing today's `docs/waves` and `docs/plans` layout exactly. Audience: integrators such as Waveforge whose document tree differs from the shipped layout, and framework maintainers who currently maintain the same two literals in about twenty files. Approach: one import-light resolver module whose constants are the only definition of the layout, and a census test that forbids new literal joins. Constraints: no configuration read at runtime and no repository code loaded by the server; fail-closed on an invalid root; byte-identical shipped behavior. Success: a repository whose `record_paths` constants point elsewhere passes every lifecycle tool, docs-lint, and indexing with no other patched framework file. (Redirected 2026-09-17 during delivery review from the first delivery's `record_layout` config block; see the Decision Log.)

Census re-derived 2026-09-17 at readiness under two stated predicates over every non-test `.py` under `.wavefoundry/framework/scripts/` (the earlier "41 plus about 60 across 19 scripts" figure mixed the two predicates and is withdrawn). Predicate A, the single literal substring `docs/waves` or `docs/plans` in any quoting: 97 occurrences in 26 files, most of them comments, docstrings, and user-facing messages; the code hits are path-prefix checks such as `normalized.startswith("docs/waves/")` in `_trust_label`, `_doc_demotion_weight`, and `_assessment_evidence_weight`, the substring test in `wf_add_change_response`, the `wave` tag rule in `_tag_utils.infer_tags`, and the `rel_parts[:2] == ("docs", "waves")` tuple test in `memory_records.py`. Predicate B, the two-token join `"docs" / "waves"` or `"docs" / "plans"` (also `os.path.join` and tuple forms): 41 occurrences in 15 files, of which 16 are in `server_impl.py` (`list_waves`, `list_plans`, `McpRepoCache._wave_fingerprint`, `McpRepoCache._plans_fingerprint`, `wf_get_change_response`, `_resolve_wave_md_matches`, `_resolve_change_doc_matches` (two on one line), `_plan_change_doc_path`, `_contained_wave_review_paths` (two), `create_wave`, `new_change`, `change_create`, `_audit_commit_governance`, `_state_sources_memory_propose`), 6 in `dashboard_server.py`, 3 in `wave_lint_lib/wave_validators.py`, and the rest one or two each. The union is 35 files: `server_impl.py` (Requirement 4), the six `wave_lint_lib` modules including `wave_validators.py` (Requirement 5), and the 27 named in Requirement 6; every one is classified at implementation time. Predicate-A hits inside `wave_lint_lib/wave_validators.py` and `constants.py` are string-form joins (`root / "docs/waves"`) and count as construction. There is no shared helper analogous to `repo_root.py` or `index_paths.py`. `docs/workflow-config.json` already declares `wave_implement.wave_root`, but nothing reads it (and after this change nothing does; the key is inert), and a comment at `docs_gardener.py:172-174` claiming the linter consumes it is stale. The RFC in `docs/reports/wavefoundry-modularity-rfc.md` proposes a `PathResolver` protocol bound by auto-discovered modules; this change takes the constants route instead: no repository code is loaded and no runtime configuration is read.

Re-verified 2026-09-17 against four intervening commits (`1y3og setup-local-reconciliation`, `1y0h*` orchestration guidance, `1y4j8 portable-windows-path-test`, `1y6hg python-runtime-deprecation-advisory`): `docs/workflow-config.json` and both `wave_lint_lib` files are byte-identical across all four (`git diff` empty on each). Navigation anchors are symbols, not line numbers, because sibling waves move lines: `list_waves`, `_resolve_change_doc_matches`, `_resolve_unique_change_doc`, `create_wave`, and the repo-cache pair `_wave_fingerprint` / `_plans_fingerprint` (each calls `_dir_fingerprint` on the joined root; the resolver must yield the same path for the default layout so cache identity is unchanged). `setup_readiness.py`, the new module from `1y3og`, reads only `('indexing', 'setup', 'platforms', 'embedding', 'providers')` from workflow-config and writes nothing — no collision with this change, which adds no workflow-config key.

Directly validated 2026-09-17 against Waveforge's real fork (`docs/reports/waveforge-fork-audit.md`): their `set_root: "docs/features/"` config key and their own `_resolve_wave_doc_matches`/`_plan_wave_doc_path`/`_move_wave_doc` functions confirm they already built a bespoke path-resolution layer for exactly this need — this change's premise is not hypothetical. Separately confirmed: `chunker.py` and `graph_indexer.py`'s "wave" references are almost entirely internal development-provenance comments, not document-model coupling, so once this change and `1y043` remove the remaining path-level coupling, the indexing pipeline built on top should merge cleanly for Waveforge with no further work on this side.

## Requirements

1. A new module `.wavefoundry/framework/scripts/record_paths.py` with only stdlib imports exposes `load_record_roots(root) -> RecordRoots`, where `RecordRoots` carries the repo-relative and absolute paths for the waves root and the plans root, plus `validate_record_layout(root) -> list[diagnostic]`, `unvalidated_record_roots(root)` for observational callers that must never refuse, and `layout_constants()` for cache keys.
2. The layout is defined by module constants in `record_paths.py` and nowhere else: `WAVES_ROOT = "docs/waves"` and `PLANS_ROOT = "docs/plans"` (repository-relative POSIX strings), which a downstream fork edits at merge time. No configuration is read at runtime: a `record_layout` block in `docs/workflow-config.json` or a `wave_implement.wave_root` key is inert, there is no legacy fallback, and no migration hint is emitted.
3. Validation is fail-closed, applied to the constants against the repository root. A root is invalid when it is absolute, empty, contains `..`, names a file or a dangling symlink (itself or any existing ancestor of an absent root), resolves outside the repository root, passes through a symlink that leaves the repository, is a symlink alias or case alias of the canonical in-repository directory (an in-repository symlink is no longer accepted), equals the other root (by spelling or by inode), or nests inside the other root (by spelling or on disk), with the equal and nested checks judged against the nearest existing ancestor of an absent root. An invalid layout is a docs-lint error (`record_layout_invalid`), and every MCP tool that constructs a record path returns that same diagnostic and performs no read or write. Nothing silently falls back to the shipped constants.
4. Every path construction and every path-prefix check in `server_impl.py` routes through the resolver: the 16 two-token joins named in the Rationale, the `startswith("docs/waves/")` checks in `_trust_label`, `_doc_demotion_weight`, and `_assessment_evidence_weight`, and the substring test in `wf_add_change_response`. Prefix checks compare against the resolver's repo-relative root with a trailing separator, so the default layout compares the same bytes it does today.
5. Every path construction in `wave_lint_lib` routes through the resolver (`constants.py` `WAVE_REQUIRED_PATHS`; in `wave_validators.py` the string-form joins in `_collect_wave_state`, `check_closed_wave_requirements`, `check_wave_docs`, `check_migration_edges`, the two-token joins in `check_orphan_wave_ledgers`, `check_prepare_council_verdict`, `check_prepare_council_roster_evidence`, plus `cli.py`, `core_validators.py`, `link_validators.py`, `helpers.py`, and `docs_constants_validators.py`), so docs-lint validates the roots the constants name, and the lint and gardener document walkers union `docs/` with those roots when a root lies outside `docs/`.
6. Every other non-test module the census finds is classified and, where the site is a construction or a prefix check, routed through the resolver: `_tag_utils.py` (the `wave` tag rule in `infer_tags`, which is how the indexer classifies a document as a wave record), `commit_provenance.py`, `context_efficiency.py`, `dashboard_lib.py`, `dashboard_server.py`, `docs_gardener.py`, `gardener_metadata.py`, `graph_indexer.py`, `graph_quality_eval.py`, `index_state_store.py`, `indexer.py`, `install_log_lib.py`, `lifecycle_id.py`, `memory_backfill.py`, `memory_records.py`, `memory_supply.py`, `reconcile_scan.py`, `render_agent_surfaces.py`, `render_platform_surfaces.py`, `retrieval_eval.py`, `review_evidence.py`, `review_policy.py`, `review_policy_reconcile.py`, `review_policy_upgrade.py`, `techdocs_audit_lib.py`, `upgrade_extensions.py`, `upgrade_wavefoundry.py`. Sites that are comments, docstrings, or user-facing message text are left in place and named in the census allowlist. The classification table (file, site symbol, class) is committed in the change's test module before routing starts.
7. A census test walks every non-test `.py` under `.wavefoundry/framework/scripts/` (the whole tree, not the list above) and asserts that outside `record_paths.py` no module matches either predicate from the Rationale except through an explicit allowlist in the test that names file, symbol, and reason (comment, docstring, or user-facing message). The test fails when a new construction or prefix check is added anywhere in the tree.
8. The shipped constants produce paths byte-identical to today: the existing lifecycle, lint, indexing, and rendering test corpora pass unchanged, and the golden tool-surface fixture from `1y0do` (landed 2026-09-17) is unchanged. A small schema-pin test for the eight lifecycle tools this change touches (`wf_create_wave`, `wf_add_change`, `wf_remove_change`, `wf_list_waves`, `wf_list_plans`, `wf_get_change`, `wf_current_wave`, `wf_prepare_wave`) is kept as a fast change-local check.
9. The stale comment in `docs_gardener.py` is corrected, and `record_paths` is added to the module purge list at the top of `server_impl.py` so `wf_reload_mcp` picks up changes to it.
10. Documentation: `docs/architecture/layering-rules.md` "Shared path resolution" is the key reference for the constants and their validation rules, and `docs/references/project-overview.md` names the constants (`WAVES_ROOT`, `PLANS_ROOT`, `NESTED`, `MAX_DEPTH`), that a fork edits them at merge time, and that a relocated waves root needs a `README.md` because lint requires `<waves_root>/README.md`.

## Scope

**Problem statement:** The record layout is a hardcoded literal repeated across the framework, so any target repository with a different tree must patch framework files and re-patch on every upgrade.

**In scope:**

- The resolver module, its layout constants, and validation.
- Routing all listed scripts through the resolver.
- The census test and the layout-fixture tests (which relocate by patching the constants).
- Documentation of the constants.

**Out of scope:**

- Nested discovery of wave records at arbitrary depth (`1y043-enh nested-record-lookup`).
- Installer and bootstrap seeds creating non-shipped roots; a fork edits the constants at merge time and moves its records.
- Any runtime configuration of the layout (`record_layout`, `wave_implement.wave_root`): rejected during delivery review, see the Decision Log.
- Rendered prose in `AGENTS.md`, seeds, and prompt docs that mentions `docs/waves` as the conventional location.
- Dashboard configuration beyond what `dashboard_lib.py` already reads from workflow-config.

## Acceptance Criteria

- [x] AC-1: With the shipped constants, every path the resolver returns equals the corresponding literal path used today, and the existing lifecycle, lint, indexing, and rendering suites pass without modification.
- [x] AC-2: In a fixture repository with the constants patched to `project/records/waves` and `project/records/plans`, `wf_create_wave`, `wf_add_change`, `wf_remove_change`, `wf_list_waves`, `wf_list_plans`, `wf_get_change`, `wf_current_wave`, and `wf_prepare_wave` dry-run operate on the relocated roots, and docs-lint passes on that fixture.
- [x] AC-3: Each invalid-root class (absolute, `..`, escape via resolution, escaping symlink, file or dangling symlink as the root or an existing ancestor, symlink alias, case alias, equal roots, nested roots) produces the `record_layout_invalid` diagnostic from docs-lint and from `wf_create_wave`, and no file is created.
- [x] AC-4: No configuration is read: with a `record_layout` block or a `wave_implement.wave_root` key set to a non-shipped value in `docs/workflow-config.json`, the resolver still returns the paths the constants name and docs-lint emits no hint (pinned by `test_record_paths.ShippedLayoutTests.test_no_configuration_is_read`).
- [x] AC-5: The census test passes on the completed tree and fails when a literal `docs/waves` join is reintroduced in a non-allowlisted module.
- [x] AC-6: The golden tool-surface fixture and the eight-tool schema-pin test both pass unchanged, and `wf_reload_mcp` picks up a modified `record_paths.py` in the reload test.
- [x] AC-8: The dashboard listing and the memory-backfill wave scan each show a wave placed under the relocated root in the AC-2 fixture, and the indexer tags a document under the relocated root with the `wave` classification through the live path `server_impl._infer_tags` -> `_tag_utils.infer_tags(path, waves_prefix=...)`, with the prefix threaded from `_record_prefixes(root)`; these three cold sites have no wave-path coverage today.
- [x] AC-7: The change's own suites and every test it adds pass; the documents this change authors or edits validate; and no failure elsewhere is attributable to this change.

## Tasks

- [x] Write `record_paths.py` with `RecordRoots`, `load_record_roots`, `validate_record_layout`, and unit tests for every validation class.
- [x] Report the constants' validation diagnostics from docs-lint (`record_layout_invalid`), reading no workflow-config key.
- [x] Commit the site classification table (file, symbol, class) in the test module before routing.
- [x] Route `server_impl.py` sites through the resolver, batch by area: lifecycle helpers, listing and lookup helpers, cache fingerprint, prefix checks, remaining sites; golden test after each batch.
- [x] Route `wave_lint_lib` through the resolver and re-run the lint corpus.
- [x] Route the remaining scripts in Requirement 6 through the resolver, `_tag_utils.py` first.
- [x] Write the census test with its allowlist.
- [x] Build the relocated-roots fixture repository and the AC-2 lifecycle tests.
- [x] Add `record_paths` to the `server_impl.py` purge list and extend the reload test.
- [x] Correct the `docs_gardener.py` comment.
- [x] Update `docs/architecture/layering-rules.md` "Shared path resolution" and `docs/references/project-overview.md`.
- [x] Run `python3 .wavefoundry/framework/scripts/run_tests.py` last and record the receipt.

## Agent Execution Graph


| Workstream     | Owner       | Depends On   | Notes |
| -------------- | ----------- | ------------ | ----- |
| resolver       | implementer | —            | module, validation, unit tests, lint hook |
| server-routing | implementer | resolver     | 41 sites in batches, golden unchanged after each |
| lint-routing   | implementer | resolver     | wave_lint_lib, runs in parallel with server-routing |
| script-routing | implementer | resolver     | fifteen remaining scripts |
| census-fixture | qa          | server-routing, lint-routing, script-routing | census test, relocated fixture, AC-2 and AC-3 |
| docs           | implementer | resolver     | layering-rules "Shared path resolution", overview, comment fix |


## Serialization Points

- `.wavefoundry/framework/scripts/record_paths.py`
- `.wavefoundry/framework/scripts/server_impl.py`
- `.wavefoundry/framework/scripts/wave_lint_lib/`
- `.wavefoundry/framework/scripts/docs_lint.py`
- `.wavefoundry/framework/scripts/tests/`
- `docs/references/project-overview.md`

## Affected Architecture Docs

`docs/architecture/current-state.md` and `docs/architecture/layering-rules.md` gain the resolver as the single owner of record-root resolution, alongside `repo_root.py` and `index_paths.py`. `docs/architecture/data-and-control-flow.md` notes that lifecycle tools and docs-lint read the same roots from the constants. A short decision record under `docs/architecture/decisions/` (`1yb8v-adr`) records the constants choice over both a runtime `record_layout` config block and an auto-discovered resolver protocol.

## AC Priority


| AC   | Priority  | Rationale |
| ---- | --------- | --------- |
| AC-1 | required  | Default behavior must be byte-identical |
| AC-2 | required  | This is the integrator outcome the change exists for |
| AC-3 | required  | Fail-closed containment is the security posture of the change |
| AC-4 | important | A stray config key must not silently move the roots |
| AC-5 | required  | Prevents the literal creeping back in later waves |
| AC-6 | required  | Public surface unchanged; reload freshness for a purged module |
| AC-7 | required  | Standard change-local verification |
| AC-8 | required  | Cold sites are where a mechanical routing slip would hide |


## Progress Log

Observe (2026-09-17 supplemental repair): dashboard document reads now use bounded identity discovery and validated document roots; memory-ID migration unions record roots and resolves discovered live-wave ownership; embedded Windows drive components are rejected; cache fingerprint stats discovered records only. Same-class inspection confirmed nested historical drift attribution lost its landing ID; it now resolves discovered wave prefixes. Targeted runs: 83 record tests, 217 memory tests, 19 dashboard routed-handler tests, and 103 drift tests pass. Guard controls killed 14 isolated/in-process mutants (5 dashboard, 6 memory, drive guard, recursive fingerprint, nested attribution); no repository source mutation was used for these controls. Broader dashboard process tests need unsandboxed process inspection and will be covered by the full runner. Final verification: full suite 9,277 tests across 103 files passed, 12 skips, fresh receipt; independent code/QA/council focused replay approves all five repairs. See supplemental-goal-review.md for per-finding evidence and limits.

Readback / Thought (2026-09-17): repair the four supplemental findings within the approved constants design. Dashboard opens discovered records within validated roots; memory rename repairs eligible relocated/nested references; malformed Windows drive components fail before joining; cached fingerprints reuse bounded discovery. Relevant ACs are reopened below until tests and independent reverification pass. No new configuration or tool surface. Split ownership: dashboard implementer, memory implementer, coordinator for resolver/cache; inherited host settings used for bounded lanes, effective worker identity unknown. Gapfill: code_ask reports index_not_ready; targeted live code_read and scoped shell reads validate current source.


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-09-17 | Final batch (cycle-3 heads): dangling and looping symlink roots or ancestors refused by `_nearest_existing`/`_check_root` (lexists but not exists); the `wave/current` and `waves` MCP resources render the Ambiguous Wave markdown on a duplicated id and the no-waves message names the resolved root; `commit_provenance._wave_dir_for_id` and `_state_sources_memory_propose` locate wave folders through discovery; `wf_remove_change` joins the duplicate-id test; eight mutants killed. The full suite then failed once on `test_allowlist_has_no_stale_entries` because the batch removed the two literals those allowlist entries covered (a docstring in commit_provenance and the no-waves message); the two entries were deleted and the suite rerun. | final-batch report; full-suite-1y0gz-9.log |
| 2026-09-17 | Delivery review cycles 2 and 3. Cycle 2 (six independent reverifiers on the constants rework): four heads confirmed repaired (lint corpus, resolver identity, both cache heads, lint own-walk, wrapper-level fail-closed later), one code-reviewer approval withheld and four new heads recorded: `root-ancestor-is-file` (file as an existing ancestor of an absent root), `audit-wave-snapshot-picks-one-twin`, `plans-cache-layout-key` (the plans cache sibling), `cycle2-adjacent-gaps` (wf_get_change envelope, lint doc walk into a nested sub-wave, aliased roots, walk-count comment, two unpinned guards, the session-capture hook), and `fail-closed-wrapper-telemetry` (wrapper telemetry re-raised after the decorated refusal for six tools). Repair batch 2 landed all of them with 14 mutants killed; full suite 9,255 green. Cycle 3 (four reverifiers): all five confirmed repaired, code-reviewer and qa-reviewer approve, and three last siblings recorded and repaired in the final batch: `dangling-symlink-root-invisible`, `wave-current-resource-serves-one-twin`, `commit-provenance-nested-wave-dir` (plus the docs naming the alias, file-ancestor, dangling-symlink, and nearest-ancestor classes and the discovery sentence). | events.jsonl; lane reports; full-suite-1y0gz-8.log |
| 2026-09-17 | Full suite after the repair lanes: 9,245 tests, two failures from pre-existing tests that symlink `docs/waves` itself outside the repository (`test_memory_backfill...test_inventory_rejects_symlinked_waves_parent`, `test_upgrade_wavefoundry...test_symlinked_waves_parent_refuses_and_leaves_outside_sentinel`). Under the constants design the shipped roots are validated on every load, so the resolver now refuses that layout before those sites' own guards run. Repairs, both contract-preserving: `memory_backfill._canonical_waves_dir` maps `RecordLayoutInvalid` to the `OSError` its callers translate into `historical_memory_inventory_failed`; the resolver's escape message reads "resolves outside the repository through a symlink", which is the only way an existing relative root can leave the repository, so the upgrade sidecar refusal still names the symlink. These two edits landed while the cycle-2 reverifiers were running; the record_paths change is message text only and the backfill site is outside every reverified head. | full-suite-1y0gz-6.log; targeted runs 117 OK |
| 2026-09-17 | Delivery review cycle 1: six lanes (code-reviewer, qa-reviewer, red-team primer, architecture and docs-contract seats, rotating integrator-operator seat), seven finding heads recorded in events.jsonl, all do_now; operator redirected the design to constants; repairs landed in lanes A (server), B (lint and gardener), C (docs) | events.jsonl; lane reports |
| 2026-09-17 | First full-suite run after routing: 9,207 tests, four failures in three files, each a real cause. (1) `dashboard_server.SnapshotStore` reader tests build the store without `__init__`, so the eagerly resolved roots attribute was missing; `_record_roots` is now a lazily resolving property that `__init__` still primes eagerly for fail-fast. (2) Two relocated-layout lint fixtures kept a hand-written manifest naming `docs/waves/`, while the check now requires the resolved root; the fixture helper mirrors the real producer (`default_manifest_payload`) per the faithful-fixture rule. (3) The events-only residue census forbids two retired sidecar basenames in test files; the census allowlist quoted them inside upgrade docstrings, so those two snippets are assembled at import time. Targeted re-runs green; full suite re-run for the receipt. | full-suite log; targeted runs |
| 2026-09-17 | Lanes landed. (superseded by the constants redirect of 2026-09-17, see the Decision Log; kept as history) Lint lane: `helpers.resolve_record_roots` (fail-closed, cached on the config file's stat identity) routes every `wave_lint_lib` validator; `check_workflow_config` emits the layout diagnostics; the legacy hint prints as `INFO:`; six new tests in `test_docs_lint.py`; mutants (equal-roots guard deleted; `check_wave_roots` fallback to defaults) both killed. Script lane: 58-row classification table in `test_record_layout_census.py`, 32 construction and prefix-check sites routed across 25 files, whole-tree census with exact allowlist and polarity test; two existing test fixtures adjusted for the new sibling import (`_DELEGATE_CHILD_MODULES` in the upgrade tests, `PYTHONPATH` for the rendered stop hook). Coordinator follow-through: the two manifest-membership constants in `wave_lint_lib/constants.py` lost their `docs/waves/` entry and `check_cross_artifact_consistency` appends the resolved `waves_prefix` at check time, otherwise a relocated repository's manifest could never satisfy lint; the stale `docs_gardener.py` comment now describes `wave_root` as the legacy key `record_paths` honors. Deliberate exception recorded: `graph_quality_eval.py`'s control-corpus literal is left in place under the allowlist reason `pinned_evidence`, because the shipped report pair `docs/reports/graph-quality-{baseline,post}.json` pins that module's SHA-256 as `evaluator_identity` and the baseline was produced against pre-change production code, so editing the module would void a shipped attributable comparison; the lane's edit there was reverted byte-for-byte. AC-8 cold sites covered in `test_record_layout_cold_sites.py`: dashboard `collect_waves`, memory-backfill `inventory_closed_waves`, and the `wave` tag through the chunker's `_infer_tags` binding. Pre-existing gap noted, out of scope: `chunker.py` binds `_infer_tags` but never calls it, so chunk tags are not produced by the live indexer today. The rendered `.claude/hooks/session-capture.py` drifts from its template until surfaces are re-rendered. | lane reports; focused runs |
| 2026-09-17 | Readback before editing. (superseded by the constants redirect of 2026-09-17, see the Decision Log; kept as history) Behavior: a stdlib-only `record_paths.py` resolves the waves and plans roots from `record_layout` (or the legacy `wave_implement.wave_root`), fails closed with `record_layout_invalid` on absolute, `..`, escaping, equal, or nested roots; every construction and prefix check in `server_impl.py`, `wave_lint_lib`, and the 27 other scripts routes through it; a census test over the whole tree forbids the literals outside an explicit allowlist. Files: new `record_paths.py`, `tests/test_record_paths.py`, `tests/test_record_layout_lifecycle.py`, `tests/test_record_layout_census.py`; edits across the 35 census files. Lanes: the coordinator routes `server_impl.py`; one implementer lane routes `wave_lint_lib` and adds the lint validation; one implementer lane routes the 27 other scripts and writes the census. | this document |
| 2026-09-17 | Implemented `server_impl.py`: import plus eviction entry; 16 two-token joins routed (`list_waves`, `list_plans`, `McpRepoCache._wave_fingerprint`/`_plans_fingerprint`, `wf_get_change_response`, `_resolve_wave_md_matches`, `_resolve_change_doc_matches`, `_plan_change_doc_path`, `_contained_wave_review_paths`, `create_wave`, `new_change`, `change_create`, `_audit_commit_governance`, `_state_sources_memory_propose`); the substring test in `wf_add_change_response` and the three prefix helpers (`_trust_label`, `_doc_demotion_weight`, `_assessment_evidence_weight`) take a `prefixes` tuple threaded from the five call sites that own a root via `_record_prefixes(root)`, which degrades to the default prefixes for ranking so a search is never refused. Fail-closed: `_fail_closed_on_record_layout` decorates the eight lifecycle response functions. Design correction found by the AC-3 test: `RecordLayoutInvalid` must not subclass `ValueError`, because `wf_create_wave` and `wf_add_change` map `ValueError` to `invalid_arguments` and `review_evidence_path_escape` and would have hidden the layout error behind the wrong code. Focused runs: server-tools, lifecycle, retrieval shards plus `test_record_paths` 1,944 green; golden fixture unchanged. | focused runs |
| 2026-09-17 | Independent reverification of the census repair: hit totals and the 35-file union confirmed; per-predicate file counts corrected from line counts to occurrence counts (26 and 15); `create_wave` "(three)" was wrong, two of those joins are in `_contained_wave_review_paths`, now named; `wave_validators.py` now named as a file in Requirement 5 | reverifier report |
| 2026-09-17 | Readiness lanes (code-reviewer BLOCK, qa-reviewer approve-with-notes) found the census wrong and the file list incomplete. Repaired: census re-derived under two named predicates (97 substring hits in 30 files, 41 two-token joins in 16 files, union 35 files); Requirement 6 now lists all 35 with `_tag_utils.py`, `dashboard_server.py`, `graph_indexer.py`, `index_state_store.py`, `memory_records.py`, `memory_supply.py`, `review_policy_upgrade.py`, `upgrade_extensions.py` and five others added; the nonexistent "substring check near the fingerprint" replaced by the three named prefix-check functions; line anchors replaced by symbols; AC-6 updated for the landed golden fixture; AC-8 added for the three untested cold sites | lane reports; census script output |
| 2026-09-14 | Change planned and admitted to `1y0gz record-layout-roots` | this document |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-09-17 | Record roots are module constants in record_paths.py, not a workflow-config block | Operator decision during delivery review: a downstream fork edits the constants at merge time; a runtime-dynamic layout needed input validation, cache invalidation, and lint-corpus following that produced three review findings | Keep the config block (rejected: same three costs); constants as defaults with a config override (rejected: keeps the runtime-dynamic surface) |
| 2026-09-14 | Config-driven roots in `workflow-config.json`, resolved by one stdlib module | Waveforge already commits that file; no repository code is imported by the server; matches the recorded config-over-plugin stance and the `index_paths.py` pattern | (a) RFC `PathResolver` protocol with auto-discovered modules: most flexible, but the server would execute repository-supplied Python at startup in every host that auto-starts MCP. (b) Environment variable overrides: zero-config for the operator, but invisible to reviewers and not shared across a team |
| 2026-09-14 | Fail-closed on invalid layout, no default fallback | A silent fallback would write records to the wrong tree while the operator believes the config is honored | Warn-and-fallback: friendlier, but creates split-brain record trees that lint then flags after the fact |
| 2026-09-14 | New `record_layout` block rather than extending `wave_implement.wave_root` | `wave_implement` is about implementation policy; the roots are layout; keeping the legacy key as a fallback avoids breaking existing configs | Reuse `wave_implement.wave_root` and add `plans_root` beside it: fewer keys, wrong home |
| 2026-09-14 | Route all nineteen files in this change rather than server plus lint only | A partial routing leaves docs-lint and indexing disagreeing with the server about where records live; the census test only has teeth when it covers everything | Two changes: smaller PRs, but an intermediate state where relocating roots half-works |
| 2026-09-17 | Own schema-pin test for the eight lifecycle tools rather than a hard dependency on `1y0do`'s full fixture | Archetype Council (Sun Tzu, 2026-09-17) found this change's own success criterion transitively blocked on a prerequisite wave whose primary audience is the two maintainer-only refactor waves, not this one — an unforced coupling for the wave Waveforge actually needs first | Keep the hard dependency: fewer moving parts, but delays the Waveforge-blocking change behind unrelated maintainer-facing work if `1y0do` slips |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Mechanical routing of about a hundred sites introduces one wrong root | Batches land behind the existing corpus plus the golden snapshot; the relocated fixture exercises both roots through every lifecycle tool |
| A literal is legitimately needed in a user-facing message and the census blocks it | The allowlist is explicit and reviewed; the message can also be built from the resolver |
| Waveforge's real layout needs nesting the roots cannot express | Nesting is the companion change in this wave; this change only relocates roots |
| Seeds and rendered docs keep saying `docs/waves` | Accepted for this change; the conventional location remains the shipped constant, and a seed follow-up can add one sentence about the `record_paths` constants under the seed gate |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.

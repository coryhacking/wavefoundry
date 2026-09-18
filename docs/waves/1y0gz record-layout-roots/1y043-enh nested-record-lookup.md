# Nested Wave Record Discovery Under Configured Roots

Change ID: `1y043-enh nested-record-lookup`
Change Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-09-17
Wave: `1y0gz record-layout-roots`

## Rationale

**Brief.** Goal: allow wave record folders to live at any bounded depth beneath the waves root, so a per-feature or per-team tree works with one constant edit in a fork and no other patched framework file. Audience: Waveforge and any integrator with a grouped record tree. Approach: the `record_paths.NESTED` constant (off as shipped), one recursive discovery walk shared by the server, docs-lint, indexing, and memory backfill, with deterministic ambiguity handling. Constraints: shipped off with byte-identical behavior; bounded depth; symlinks never followed; no new tool parameters; no runtime configuration (redirected 2026-09-17 during delivery review, see the Decision Log). Success: a fixture tree with waves two and three levels deep passes every lifecycle tool and docs-lint.

Verification found the asymmetry that makes this tractable: change-doc lookup in `_resolve_change_doc_matches` already walks both roots recursively with `rglob`, and `_resolve_unique_change_doc` already reports `ambiguous_change_id` deterministically. Only the server's wave record discovery assumes one level: `list_waves` iterates the root's immediate children and `_resolve_wave_md_matches` globs `*/wave.md`. Corrected at readiness 2026-09-17: `check_wave_roots` in `wave_lint_lib/wave_validators.py` only checks that the required paths exist and does not validate folder shape; the lint validators that enumerate waves (`_collect_wave_state`, `check_closed_wave_requirements`, `check_wave_docs`, `check_prepare_council_verdict`, `check_prepare_council_roster_evidence`) used their own `rglob`, which is depth-tolerant but unbounded and unguarded; delivery review (finding `lint-validators-own-walk`, 2026-09-17) found that an own walk diverges from `discover_wave_dirs` under `NESTED` with a small `MAX_DEPTH` or an `.archive/` folder, so those five sites and `check_orphan_wave_ledgers` (direct children only) all move to the shared walk. The generic-nested option was selected over targeting one known layout because Waveforge's exact tree has not been stated; a bounded recursive walk covers any grouping.

Waveforge's exact tree is now partially known (`docs/reports/waveforge-fork-audit.md`, 2026-09-17): `set_root: "docs/features/"` groups by feature, consistent with a nested rather than flat layout at their "wave" (Wavefoundry "change") tier. Their fork's own `_move_wave_doc` and `_resolve_wave_doc_matches` functions confirm relocation-by-discovery is already a need they've built for independently — validating Requirement 6 (relocation support with no stored depth-specific path) directly rather than by inference.

## Requirements

1. `record_paths.py` (from `1y042-enh record-roots-config-and-resolver`) gains two module constants beside `WAVES_ROOT` and `PLANS_ROOT`: `NESTED` (boolean, shipped `False`) and `MAX_DEPTH` (integer 1 to 8, shipped 4), where `MAX_DEPTH` counts the wave folder's own depth below the waves root, so 1 means direct children only. A fork edits them at merge time; nothing is read from configuration. A non-boolean `NESTED` or an out-of-range or non-integer `MAX_DEPTH` is a `record_layout_invalid` error from docs-lint and from every lifecycle tool.
2. `record_paths.py` exposes `discover_wave_dirs(root) -> list[Path]`. With `NESTED` false it returns exactly today's immediate children. With `NESTED` true it walks the waves root to `MAX_DEPTH`, returns every directory that contains a `wave.md`, never descends into a directory that is a symlink or whose name starts with a dot, and never descends into a discovered wave folder.
3. Wave identity is unchanged: the wave folder name is `<id> <slug>` at any depth, and wave IDs remain unique across the whole tree. Two wave folders with the same ID at different paths produce an `ambiguous_wave_id` diagnostic listing both repo-relative paths from every tool that resolves a wave, and docs-lint reports the same error.
4. `list_waves`, `_resolve_wave_md_matches`, `wf_current_wave`, the repo-cache `_wave_fingerprint`, and every `wave_lint_lib` wave enumerator named in the Rationale use `discover_wave_dirs`; no lint validator enumerates the waves root with an `rglob` or glob of its own. The `wave` document classification in `_tag_utils.infer_tags` (a path-prefix rule, reached live through `server_impl._infer_tags`, which threads `waves_prefix` from `_record_prefixes(root)`) is rewritten as "under the waves root", which is depth-independent, so a nested wave is indexed with the `wave` tag. `memory_backfill.py` wave scanning and `dashboard_lib.py` wave listing use the same walk, so a nested wave is eligible for memory backfill and shown on the dashboard.
5. Change-doc lookup keeps its existing recursive behavior and existing ambiguity diagnostic; a test pins that plan docs nested under the plans root are found in both modes.
6. `wf_create_wave` continues to create the new wave folder directly under the waves root. Relocating a wave folder deeper within the root after creation is supported: every lookup is by discovery, and no tool stores an absolute or depth-specific wave path in a record it later re-reads.
7. Discovery cost is bounded by argument threading through the existing repo-cache seam, not by a new cache. Today `wf_current_wave_response` and its siblings call `McpRepoCache.list_waves_cached`, which computes `self._wave_fingerprint()` and, on a miss, `list_waves(self.root)`; both would walk. The repair: `list_waves_cached` calls `discover_wave_dirs` once and passes the list to both `_wave_fingerprint(wave_dirs=...)` and `list_waves(root, wave_dirs=...)`; `_resolve_wave_md_matches` gains the same optional parameter for the callers that reach it directly; each helper walks only when the parameter is `None`. The fingerprint stats only the discovered wave.md files; it performs no second recursive filesystem scan. No other cache is introduced. A test asserts the walk visits no directory beyond `MAX_DEPTH`, and a call-counter test patches `discover_wave_dirs` and proves exactly one call for a `wf_current_wave` invocation on a cold `McpRepoCache`, the path that consults both the fingerprint and `list_waves`. The cache key folds in `record_paths.layout_constants()` and the discovered paths (delivery-review finding `warm-cache-layout-flip`), so a warm cache never serves paths from another layout. Fan-out at each level is not bounded by `MAX_DEPTH` alone; a large flat directory count at one level is a known, accepted cost of enabling `NESTED`, not silently hidden.
8. The shipped constants are byte-identical to today: existing suites pass unchanged and the golden tool-surface fixture is unchanged.

## Scope

**Problem statement:** Wave records must be immediate children of the waves root, so integrators who group records by feature or team cannot use the framework without patching discovery in several files.

**In scope:**

- The `NESTED` and `MAX_DEPTH` constants, the shared discovery walk, and the ambiguity diagnostic.
- Routing server, lint, indexer, memory backfill, and dashboard wave discovery through the walk.
- Fixture trees and tests for nested, ambiguous, symlinked, hidden, and over-depth cases.

**Out of scope:**

- A `parent` argument on `wf_create_wave` or a configured default parent for new waves; revisit when an integrator states the need, since it changes the public tool schema.
- Nested plans roots beyond what the existing recursive change-doc lookup already supports.
- Any change to wave folder naming or wave ID format.

## Acceptance Criteria

- [x] AC-1: With the shipped `NESTED = False`, `discover_wave_dirs` returns exactly the immediate children containing `wave.md`, and the existing lifecycle, lint, indexing, and dashboard suites pass unchanged.
- [x] AC-2: In a fixture with waves at depth one, two, and three under the waves root and `NESTED` patched to `True`, `wf_list_waves`, `wf_current_wave`, `wf_get_change` by prefix, `wf_add_change`, `wf_remove_change`, `wf_prepare_wave` dry-run, and docs-lint all resolve every wave, and the indexer tags each wave's documents with the `wave` classification through the live path `server_impl._infer_tags` -> `_tag_utils.infer_tags(path, waves_prefix=...)`.
- [x] AC-3: A duplicate wave ID at two depths produces `ambiguous_wave_id` naming both paths from every tool that resolves a wave (`wf_current_wave`, `wf_list_waves`, `wf_get_change`, `wf_add_change`, `wf_remove_change`, `wf_prepare_wave`, `wf_review_event`, `wf_close_wave`, `wf_pause_wave`, `wf_implement_wave`, `wf_review_wave`, `wf_reopen_wave`, `wf_audit`, `wf_mark_ac`, `wf_mark_task`), on the registered tool surface as well as the response functions, and from docs-lint, and no mutation proceeds.
- [x] AC-4a: A symlinked directory is not discovered, and a dot-prefixed directory is not discovered, each as its own named test.
- [x] AC-4b: A wave folder beyond `MAX_DEPTH` is not discovered and the instrumented walk records no directory visit beyond the limit.
- [x] AC-4c: With `discover_wave_dirs` patched to count calls, one `wf_current_wave` invocation on a cold `McpRepoCache` makes exactly one call.
- [x] AC-5: Moving a wave folder from depth one to depth three in the fixture leaves every lookup by ID working with no edit to any record.
- [x] AC-6: The golden tool-surface fixture is unchanged.
- [x] AC-7: The change's own suites and every test it adds pass; the documents this change authors or edits validate; and no failure elsewhere is attributable to this change.

## Tasks

- [x] Add the `NESTED` and `MAX_DEPTH` constants and their validation to `record_paths.py`.
- [x] Implement `discover_wave_dirs` with symlink, hidden-directory, and depth guards, plus unit tests.
- [x] Route `list_waves`, `_resolve_wave_md_matches`, the cache fingerprint, and `wf_current_wave` through discovery; add `ambiguous_wave_id`.
- [x] Route `wave_lint_lib` wave-root validation through discovery and add the duplicate-ID lint error.
- [x] Route `memory_backfill.py` and `dashboard_lib.py` (via `server.list_waves`) wave scanning through discovery, and thread the waves prefix into the `wave` classifier (`_tag_utils.infer_tags` via `server_impl._infer_tags`; `indexer.py` itself scans no waves).
- [x] Build the nested fixture tree and the AC-2 through AC-5 tests.
- [x] Update `docs/architecture/layering-rules.md` "Shared path resolution" for the two new constants.
- [x] Run `python3 .wavefoundry/framework/scripts/run_tests.py` last and record the receipt.

## Agent Execution Graph


| Workstream     | Owner       | Depends On   | Notes |
| -------------- | ----------- | ------------ | ----- |
| discovery      | implementer | `1y042` resolver | walk, guards, the two constants |
| server-lint    | implementer | discovery    | server and lint routing, ambiguity diagnostic |
| index-memory-dashboard | implementer | discovery | three consumers, can run in parallel with server-lint |
| fixtures       | qa          | server-lint, index-memory-dashboard | nested fixture and AC tests |


## Serialization Points

- `.wavefoundry/framework/scripts/record_paths.py`
- `.wavefoundry/framework/scripts/server_impl.py`
- `.wavefoundry/framework/scripts/wave_lint_lib/`
- `.wavefoundry/framework/scripts/indexer.py`
- `.wavefoundry/framework/scripts/memory_backfill.py`
- `.wavefoundry/framework/scripts/dashboard_lib.py`
- `.wavefoundry/framework/scripts/tests/`

## Affected Architecture Docs

`docs/architecture/data-and-control-flow.md` gains the discovery walk as the single path from the constant roots to wave records for the server, lint, indexer, memory, and dashboard. The decision record created by `1y042` gains a paragraph on nested discovery and the deferred `parent` argument.

## AC Priority


| AC   | Priority  | Rationale |
| ---- | --------- | --------- |
| AC-1 | required  | Default off must be byte-identical |
| AC-2 | required  | The integrator outcome |
| AC-3 | required  | Deterministic ambiguity handling is what makes discovery safe |
| AC-4a | required  | Containment: the walk never leaves the root through a link or a hidden directory |
| AC-4b | required  | Cost bound on depth |
| AC-4c | required  | Cost bound on call count, made falsifiable by the argument-threading mechanism |
| AC-5 | important | Proves no tool depends on depth after creation |
| AC-6 | required  | No public schema change in this wave |
| AC-7 | required  | Standard change-local verification |


## Progress Log

Observe (2026-09-17 supplemental repair): dashboard document reads now use bounded identity discovery and validated document roots; memory-ID migration unions record roots and resolves discovered live-wave ownership; embedded Windows drive components are rejected; cache fingerprint stats discovered records only. Same-class inspection confirmed nested historical drift attribution lost its landing ID; it now resolves discovered wave prefixes. Targeted runs: 83 record tests, 217 memory tests, 19 dashboard routed-handler tests, and 103 drift tests pass. Guard controls killed 14 isolated/in-process mutants (5 dashboard, 6 memory, drive guard, recursive fingerprint, nested attribution); no repository source mutation was used for these controls. Broader dashboard process tests need unsandboxed process inspection and will be covered by the full runner. Final verification: full suite 9,277 tests across 103 files passed, 12 skips, fresh receipt; independent code/QA/council focused replay approves all five repairs. See supplemental-goal-review.md for per-finding evidence and limits.

Readback / Thought (2026-09-17): repair the four supplemental findings within the approved constants design. Dashboard opens discovered records within validated roots; memory rename repairs eligible relocated/nested references; malformed Windows drive components fail before joining; cached fingerprints reuse bounded discovery. Relevant ACs are reopened below until tests and independent reverification pass. No new configuration or tool surface. Split ownership: dashboard implementer, memory implementer, coordinator for resolver/cache; inherited host settings used for bounded lanes, effective worker identity unknown. Gapfill: code_ask reports index_not_ready; targeted live code_read and scoped shell reads validate current source.


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-09-17 | Delivery review cycles 2 and 3. Cycle 2 (six independent reverifiers on the constants rework): four heads confirmed repaired (lint corpus, resolver identity, both cache heads, lint own-walk, wrapper-level fail-closed later), one code-reviewer approval withheld and four new heads recorded: `root-ancestor-is-file` (file as an existing ancestor of an absent root), `audit-wave-snapshot-picks-one-twin`, `plans-cache-layout-key` (the plans cache sibling), `cycle2-adjacent-gaps` (wf_get_change envelope, lint doc walk into a nested sub-wave, aliased roots, walk-count comment, two unpinned guards, the session-capture hook), and `fail-closed-wrapper-telemetry` (wrapper telemetry re-raised after the decorated refusal for six tools). Repair batch 2 landed all of them with 14 mutants killed; full suite 9,255 green. Cycle 3 (four reverifiers): all five confirmed repaired, code-reviewer and qa-reviewer approve, and three last siblings recorded and repaired in the final batch: `dangling-symlink-root-invisible`, `wave-current-resource-serves-one-twin`, `commit-provenance-nested-wave-dir` (plus the docs naming the alias, file-ancestor, dangling-symlink, and nearest-ancestor classes and the discovery sentence). | events.jsonl; lane reports; full-suite-1y0gz-8.log |
| 2026-09-17 | Delivery review cycle 1: six lanes (code-reviewer, qa-reviewer, red-team primer, architecture and docs-contract seats, rotating integrator-operator seat), seven finding heads recorded in events.jsonl, all do_now; operator redirected the design to constants; repairs landed in lanes A (server), B (lint and gardener), C (docs) | events.jsonl; lane reports |
| 2026-09-17 | Third full-suite run green: 9,226 tests, 0 failures, 21 skipped; receipt `.wavefoundry/framework/test-cache.json` written (inputs hash `b029469b0fb8`). AC-1 to AC-7 marked; Change Status `complete`. | full-suite-1y0gz-5.log; test-cache.json |
| 2026-09-17 | Second full-suite run: 9,226 tests, one failure, `test_memory_backfill...test_inventory_and_resolver_ignore_symlinked_wave_directories`. Restoring the flat `iterdir` enumeration re-exposed symlinked children to the two memory sites that had excluded them on their own before routing. Repair: `memory_backfill.inventory_closed_waves` and `memory_supply.resolve_wave_dir` filter `is_symlink()` over the walk result, as at HEAD; every other walk consumer's `is_symlink` count matches HEAD (context_efficiency 0, commit_provenance 0, lifecycle_id 0, review_policy_upgrade 0, docs_constants_validators 0, wave_validators 1, server_impl 1). The existing backfill test is the named guard (it failed with the guard absent, so no separate mutant was needed). Third full-suite run recorded below. | full-suite-1y0gz-4.log |
| 2026-09-17 | First full-suite run: 9,225 tests, one failure, `test_typed_review_writer_rejects_symlinked_wave_directory_escape`, which expects a symlinked wave folder under the flat layout to be found and then refused by the record-writer path-escape guard; the flat walk was skipping symlinks, so the tool answered `wave_not_found` instead and AC-1's byte-identical claim did not hold. Repair: `_list_subdirs(directory, *, guarded=True)`, with the flat branch of `walk_wave_candidates` passing `guarded=False`, so only the nested walk applies the symlink and dot-directory guards (Requirement 2 scopes them to `nested` true). New pin `test_flat_layout_still_enumerates_a_symlinked_child`; landing-rule mutant (flat branch back to the guarded listing) fails both that pin and the lifecycle test, restored byte-for-byte. Golden tool-surface fixture unchanged (AC-6). Second full-suite run recorded below. | full-suite-1y0gz-3.log; mutant output |
| 2026-09-17 | Implemented. `record_paths`: `nested` and `max_depth` validated (bool; int 1 to 8, bool rejected), `_list_subdirs` as the single walk primitive (sorted, no symlinks, no dot directories), `walk_wave_candidates` (flat: the root's child directories; nested: bounded depth-first that never enters a discovered wave folder), `discover_wave_dirs`, `ambiguous_wave_ids`, `ambiguous_wave_id_diagnostics`. Server: `list_waves` and `_resolve_wave_md_matches` take `wave_dirs`; `McpRepoCache.list_waves_cached` walks once and keeps the list; `_waves_and_dirs` plus `_ambiguous_wave_id_response` give `wf_current_wave` and `wf_list_waves` the refusal; `_find_wave_md` threads `wave_dirs` so `wf_list_waves` walks once for its metrics loop; `_contained_wave_review_paths` accepts depth 1 flat or up to `max_depth` nested; `_audit_commit_governance` walks candidates. Deviation from Requirement 7 as written: `_wave_fingerprint` already hashes recursively through `_dir_fingerprint(recursive=True)`, so it needs no `wave_dirs` parameter and the count stays at one walk. Routed enumerations: `context_efficiency.resolve_open_wave`, `commit_provenance.resolve_via_evidence`, `review_policy_upgrade.plan_migration`, `lifecycle_id._existing_prefixes`, `memory_supply.resolve_wave_dir`, `memory_backfill.inventory_closed_waves`, `check_orphan_wave_ledgers` (candidate walk, content-driven), `check_wave_scaffolding_integrity`; `check_wave_roots` reports `ambiguous_wave_id` with the same text as the server. Flat-mode tightening (WITHDRAWN by the first full-suite run, see the repair row): symlinked and dot-prefixed children of the waves root were briefly not enumerated by `list_waves`; the flat layout now matches the pre-change `iterdir` enumeration, and only the nested walk carries the symlink and dot-directory guards. Tests: `test_record_paths.NestedDiscoveryTests` (AC-1, 4a as two named tests, 4b with an instrumented walk, validation), `test_record_layout_nested.py` (AC-2, AC-3, AC-4c, AC-5, Requirement 5). Landing rule, six mutants each killed by the named test and restored byte-for-byte: depth bound removed; symlink guard removed; dot-directory guard removed; ambiguity never reported; walk not threaded into `list_waves`; direct-child containment rule kept. Gapfill: navigation used `code_read` and the earlier Read passes; shell `grep` located the eleven one-level enumeration sites as a whole-tree census, which the MCP keyword tool cannot express as a single regex. | targeted runs; mutant script output |
| 2026-09-17 | Readback before editing. (superseded by the constants redirect of 2026-09-17, see the Decision Log; kept as history) Behavior: `record_layout` gains `nested` (bool, default false) and `max_depth` (1 to 8, default 4); `record_paths.walk_wave_candidates` is the one walk primitive (flat: the root's child directories exactly as `iterdir` gave them, so content-driven validators keep seeing folders without a `wave.md`; nested: bounded depth-first, no symlinks, no dot directories, never into a discovered wave folder), `discover_wave_dirs` filters it to folders holding `wave.md`, and `ambiguous_wave_id_diagnostics` names duplicated ids with both paths. Sites: `list_waves`, `_resolve_wave_md_matches`, `McpRepoCache._wave_fingerprint` and `list_waves_cached` (one walk threaded as `wave_dirs`), `_audit_commit_governance`, `_contained_wave_review_paths` (bounded depth instead of direct child), `context_efficiency.resolve_open_wave`, `commit_provenance.resolve_via_evidence`, `review_policy_upgrade.plan_migration`, `lifecycle_id._existing_prefixes`, `memory_supply.resolve_wave_dir`, `memory_backfill.inventory_closed_waves`, `wave_lint_lib` `check_orphan_wave_ledgers` and `check_wave_scaffolding_integrity` plus the duplicate-id lint error. ACs 1 to 7 with 4a, 4b, 4c. Boundary: `wf_create_wave` still creates at the root; no tool parameter added. | this document |
| 2026-09-17 | Independent reverification refuted the first draft of Requirement 7: `wf_current_wave_response` reaches `list_waves` and the fingerprint only through `McpRepoCache.list_waves_cached`, so threading must happen at that seam; repaired to name it, AC-4c now specifies a cold cache | reverifier report; `McpRepoCache.list_waves_cached` |
| 2026-09-17 | Readiness repairs: corrected the `check_wave_roots` claim (it checks existence only; the enumerating lint validators already rglob, `check_orphan_wave_ledgers` is the one direct-children site); added the `_tag_utils.infer_tags` classifier that the qa lane found in neither change's scope; stated the once-per-invocation mechanism as argument threading so the call-counter test is falsifiable; split AC-4 into three named ACs | lane reports |
| 2026-09-14 | Change planned and admitted to `1y0gz record-layout-roots` | this document |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-09-17 | Record roots are module constants in record_paths.py, not a workflow-config block | Operator decision during delivery review: a downstream fork edits the constants at merge time; a runtime-dynamic layout needed input validation, cache invalidation, and lint-corpus following that produced three review findings | Keep the config block (rejected: same three costs); constants as defaults with a config override (rejected: keeps the runtime-dynamic surface) |
| 2026-09-14 | Generic bounded recursive discovery, opt-in | Waveforge's exact tree is unstated; a bounded walk covers any grouping and stays off by default | (a) Target one known layout such as `docs/features/<f>/waves/`: smallest, but wrong the moment the layout differs. (b) Flat roots only: already covered by `1y042`, does not fit a per-feature tree |
| 2026-09-14 | Create at the waves root, support relocation, defer a `parent` argument | Adding a tool parameter changes the public schema guarded by the golden fixture; relocation covers the need until an integrator asks | Add `parent` now: convenient, but speculative and a contract change |
| 2026-09-14 | Never follow symlinks or hidden directories during discovery | Matches the existing skill-rendering symlink containment and keeps the walk inside the repository | Follow symlinks within the root: more flexible, harder to reason about containment |
| 2026-09-17 | Argument threading over a per-root cache for the single walk per invocation | A cache needs an invalidation contract and a staleness test across two calls in one process; threading the list through the helpers a tool already calls has no state and is directly countable | Module-level cache keyed by root and mtime: fewer signature changes, but a second cache-consistency surface beside the existing repo-cache fingerprint |
| 2026-09-17 | Prove "once per invocation" with a call-counter test rather than leaving it as an unverified requirement | Archetype Council (Spock, 2026-09-17) found the requirement made a cost claim with no AC that could falsify it — only depth-bounding was tested, not call frequency, which is the user-facing performance property that actually matters | Leave as-is: cheaper now, but the claim is currently unfalsifiable and this is a Waveforge-facing feature meant to run on every lifecycle tool call |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| A consumer of wave paths is missed and sees only depth-one waves | The nested fixture exercises server, lint, indexer, memory backfill, and dashboard together in AC-2 |
| Large trees make discovery slow on every tool call | Depth bound, single walk per invocation, and the existing repo cache fingerprint |
| Duplicate IDs already exist in some repository when `NESTED` is enabled | Lint and every lifecycle tool report `ambiguous_wave_id` before any mutation, so enabling the constant is safe to trial |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.

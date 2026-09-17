# Nested Wave Record Discovery Under Configured Roots

Change ID: `1y043-enh nested-record-lookup`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-09-14
Wave: `1y0gz record-layout-roots`

## Rationale

**Brief.** Goal: allow wave record folders to live at any bounded depth beneath the configured waves root, so a per-feature or per-team tree works without patching the framework. Audience: Waveforge and any integrator with a grouped record tree. Approach: opt-in `record_layout.nested` flag, one recursive discovery walk shared by the server, docs-lint, indexing, and memory backfill, with deterministic ambiguity handling. Constraints: default off with byte-identical behavior; bounded depth; symlinks never followed; no new tool parameters. Success: a fixture tree with waves two and three levels deep passes every lifecycle tool and docs-lint.

Verification found the asymmetry that makes this tractable: change-doc lookup in `_resolve_change_doc_matches` already walks both roots recursively with `rglob`, and `_resolve_unique_change_doc` already reports `ambiguous_change_id` deterministically. Only wave record discovery assumes one level: `list_waves` (`server_impl.py:3678`) and `_resolve_wave_md_matches` (line 7182) expect `<waves_root>/<id> <slug>/wave.md`, and `check_wave_roots` in `wave_lint_lib/wave_validators.py:1204` validates the same shape. The generic-nested option was selected over targeting one known layout because Waveforge's exact tree has not been stated; a bounded recursive walk covers any grouping.

Waveforge's exact tree is now partially known (`docs/reports/waveforge-fork-audit.md`, 2026-09-17): `set_root: "docs/features/"` groups by feature, consistent with a nested rather than flat layout at their "wave" (Wavefoundry "change") tier. Their fork's own `_move_wave_doc` and `_resolve_wave_doc_matches` functions confirm relocation-by-discovery is already a need they've built for independently — validating Requirement 6 (relocation support with no stored depth-specific path) directly rather than by inference.

## Requirements

1. `record_layout` (from `1y042-enh record-roots-config-and-resolver`) gains two optional keys: `nested` (boolean, default `false`) and `max_depth` (integer 1 to 8, default 4), where depth counts directories between the waves root and the wave folder. Unknown keys and out-of-range values are docs-lint errors.
2. `record_paths.py` exposes `discover_wave_dirs(root) -> list[Path]`. With `nested` false it returns exactly today's immediate children. With `nested` true it walks the waves root to `max_depth`, returns every directory that contains a `wave.md`, never descends into a directory that is a symlink or whose name starts with a dot, and never descends into a discovered wave folder.
3. Wave identity is unchanged: the wave folder name is `<id> <slug>` at any depth, and wave IDs remain unique across the whole tree. Two wave folders with the same ID at different paths produce an `ambiguous_wave_id` diagnostic listing both repo-relative paths from every tool that resolves a wave, and docs-lint reports the same error.
4. `list_waves`, `_resolve_wave_md_matches`, `wf_current_wave`, the repo-cache wave fingerprint, and `wave_lint_lib` wave-root validation use `discover_wave_dirs`. `indexer.py` wave classification, `memory_backfill.py` wave scanning, and `dashboard_lib.py` wave listing use the same walk, so a nested wave is indexed, eligible for memory backfill, and shown on the dashboard.
5. Change-doc lookup keeps its existing recursive behavior and existing ambiguity diagnostic; a test pins that plan docs nested under the plans root are found in both modes.
6. `wf_create_wave` continues to create the new wave folder directly under the waves root. Relocating a wave folder deeper within the root after creation is supported: every lookup is by discovery, and no tool stores an absolute or depth-specific wave path in a record it later re-reads.
7. Discovery cost is bounded: the walk runs at most once per tool invocation and its result is reused within that invocation; a test asserts the walk visits no directory beyond `max_depth`, and a separate call-counter test proves exactly one `discover_wave_dirs` call occurs even when a handler internally needs the result twice (for example `wf_current_wave` consulting both `list_waves` and the wave fingerprint). Fan-out at each level is not bounded by `max_depth` alone; a large flat directory count at one level is a known, accepted cost of enabling `nested`, not silently hidden.
8. The default configuration is byte-identical to today: existing suites pass unchanged and the golden tool-surface fixture is unchanged.

## Scope

**Problem statement:** Wave records must be immediate children of the waves root, so integrators who group records by feature or team cannot use the framework without patching discovery in several files.

**In scope:**

- The `nested` and `max_depth` keys, the shared discovery walk, and the ambiguity diagnostic.
- Routing server, lint, indexer, memory backfill, and dashboard wave discovery through the walk.
- Fixture trees and tests for nested, ambiguous, symlinked, hidden, and over-depth cases.

**Out of scope:**

- A `parent` argument on `wf_create_wave` or a configured default parent for new waves; revisit when an integrator states the need, since it changes the public tool schema.
- Nested plans roots beyond what the existing recursive change-doc lookup already supports.
- Any change to wave folder naming or wave ID format.

## Acceptance Criteria

- [ ] AC-1: With `nested` absent or `false`, `discover_wave_dirs` returns exactly the immediate children containing `wave.md`, and the existing lifecycle, lint, indexing, and dashboard suites pass unchanged.
- [ ] AC-2: In a fixture with waves at depth one, two, and three under the configured root and `nested: true`, `wf_list_waves`, `wf_current_wave`, `wf_get_change` by prefix, `wf_add_change`, `wf_remove_change`, `wf_prepare_wave` dry-run, and docs-lint all resolve every wave, and the indexer tags each wave's documents with the `wave` classification.
- [ ] AC-3: A duplicate wave ID at two depths produces `ambiguous_wave_id` naming both paths from `wf_current_wave` and from docs-lint, and no mutation proceeds.
- [ ] AC-4: A symlinked directory, a dot-prefixed directory, and a wave folder beyond `max_depth` are not discovered, the depth test records no directory visits beyond the limit, and the call-counter test proves the walk runs exactly once per tool invocation regardless of how many routed functions consult its result within that invocation.
- [ ] AC-5: Moving a wave folder from depth one to depth three in the fixture leaves every lookup by ID working with no edit to any record.
- [ ] AC-6: The golden tool-surface fixture is unchanged.
- [ ] AC-7: The change's own suites and every test it adds pass; the documents this change authors or edits validate; and no failure elsewhere is attributable to this change.

## Tasks

- [ ] Add `nested` and `max_depth` to the `record_layout` validation and to `record_paths.py`.
- [ ] Implement `discover_wave_dirs` with symlink, hidden-directory, and depth guards, plus unit tests.
- [ ] Route `list_waves`, `_resolve_wave_md_matches`, the cache fingerprint, and `wf_current_wave` through discovery; add `ambiguous_wave_id`.
- [ ] Route `wave_lint_lib` wave-root validation through discovery and add the duplicate-ID lint error.
- [ ] Route `indexer.py`, `memory_backfill.py`, and `dashboard_lib.py` wave scanning through discovery.
- [ ] Build the nested fixture tree and the AC-2 through AC-5 tests.
- [ ] Update the workflow-config key reference for the two new keys.
- [ ] Run `python3 .wavefoundry/framework/scripts/run_tests.py` last and record the receipt.

## Agent Execution Graph


| Workstream     | Owner       | Depends On   | Notes |
| -------------- | ----------- | ------------ | ----- |
| discovery      | implementer | `1y042` resolver | walk, guards, config keys |
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

`docs/architecture/data-and-control-flow.md` gains the discovery walk as the single path from configured roots to wave records for the server, lint, indexer, memory, and dashboard. The decision record created by `1y042` gains a paragraph on nested discovery and the deferred `parent` argument.

## AC Priority


| AC   | Priority  | Rationale |
| ---- | --------- | --------- |
| AC-1 | required  | Default off must be byte-identical |
| AC-2 | required  | The integrator outcome |
| AC-3 | required  | Deterministic ambiguity handling is what makes discovery safe |
| AC-4 | required  | Containment and cost bounds |
| AC-5 | important | Proves no tool depends on depth after creation |
| AC-6 | required  | No public schema change in this wave |
| AC-7 | required  | Standard change-local verification |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-09-14 | Change planned and admitted to `1y0gz record-layout-roots` | this document |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-09-14 | Generic bounded recursive discovery, opt-in | Waveforge's exact tree is unstated; a bounded walk covers any grouping and stays off by default | (a) Target one known layout such as `docs/features/<f>/waves/`: smallest, but wrong the moment the layout differs. (b) Flat roots only: already covered by `1y042`, does not fit a per-feature tree |
| 2026-09-14 | Create at the waves root, support relocation, defer a `parent` argument | Adding a tool parameter changes the public schema guarded by the golden fixture; relocation covers the need until an integrator asks | Add `parent` now: convenient, but speculative and a contract change |
| 2026-09-14 | Never follow symlinks or hidden directories during discovery | Matches the existing skill-rendering symlink containment and keeps the walk inside the repository | Follow symlinks within the root: more flexible, harder to reason about containment |
| 2026-09-17 | Prove "once per invocation" with a call-counter test rather than leaving it as an unverified requirement | Archetype Council (Spock, 2026-09-17) found the requirement made a cost claim with no AC that could falsify it — only depth-bounding was tested, not call frequency, which is the user-facing performance property that actually matters | Leave as-is: cheaper now, but the claim is currently unfalsifiable and this is a Waveforge-facing feature meant to run on every lifecycle tool call |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| A consumer of wave paths is missed and sees only depth-one waves | The nested fixture exercises server, lint, indexer, memory backfill, and dashboard together in AC-2 |
| Large trees make discovery slow on every tool call | Depth bound, single walk per invocation, and the existing repo cache fingerprint |
| Duplicate IDs already exist in some repository when `nested` is enabled | Lint reports `ambiguous_wave_id` before any mutation, so enabling the flag is safe to trial |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.

# Project-Layer Meta Persists Framework Paths, Causing Permanent Phantom-Removed Health

Change ID: `130nf-bug project-meta-broad-walk-mismatch`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-05-31
Wave: 130et framework-bin-mcp-server-launcher

## Rationale

External operator bug report (Solaris project, 2026-05-31): after upgrading to framework 1.1.0+30n0, `wave_index_health` permanently reports the project layer as `stale` with 110 phantom "removed" paths — every one under `.wavefoundry/framework/*`. `wave_index_build(content="docs", mode="update", layer="project")` returns success and logs `build_index: index is up to date`, but the health check is never satisfied. Update mode cannot converge the discrepancy; only a full rebuild clears it, and even then only until the next incremental run writes a fresh `meta.json` and the cycle restarts.

Root cause (verified locally on this repo — project `meta.json` has 163 `.wavefoundry/framework/*` entries that should not be there):

Two functions disagree on which files belong to the project layer:

- **`_layer_current_hashes("project")` in `server_impl.py:391–403`** (powers `wave_index_health`) applies `_filter_project_index_excludes`, which strips `.wavefoundry/framework/**` from the result. **Narrow set.**
- **`build_index` in `indexer.py:1810–1822`** captures `files_for_meta = files` **before** calling `_filter_project_index_excludes`, so `meta.json` persists hashes for the **broad set** that includes every `.wavefoundry/framework/*` file the walker found.

Diff in `_layer_health` (server_impl.py:442–446) then surfaces every framework-prefixed entry as `removed`, because the narrow current set never contains them. Meanwhile `build_index` recomputes `files_for_meta` (broad again) and `_detect_changes` reports no changes, so the incremental rebuild short-circuits at `indexer.py:1914` with "index is up to date" and the meta is never rewritten.

The widening of `files_for_meta` at line 1822 was originally introduced to fix an unrelated bug — alternating 93-files-added/93-files-removed cycles between docs-only and code-only runs that used different `include_prefixes`. The inline comment (lines 1817–1821) documents this intent. The fix went too far: it widened the meta past the layer boundary, contaminating the project layer's meta with files that belong to the framework layer's meta.

## Requirements

1. The project layer's `meta.json` `file_meta` dict must contain only files that belong to the project layer (no `.wavefoundry/framework/*` entries unless explicitly opted in via `project_include_prefixes` in `docs/workflow-config.json`).
2. `files_for_meta` must remain **stable** across docs-only and code-only runs of the same layer, preserving the existing fix that eliminated the 93-files-added/93-files-removed alternating cycle. The stabilization technique is to filter by the **union** of `workflow-config.json`'s docs+code project_include_prefixes (the same superset already computed by `_merged_project_include_prefixes_for_graph`), not by the per-run content type.
3. The framework layer's `meta.json` must be unchanged — its `files_for_meta` is already narrow (filtered to `.wavefoundry/framework/**` by `include_prefixes` at line 1814 and then through `_filter_framework_pack_artifacts`). The fix touches the project-layer path only.
4. The fix must self-heal existing meta.json files in the wild: on the first incremental build after upgrade, `_detect_changes` must see the previously-persisted framework entries as `removed_broad` and evict them, causing the next written meta to be narrow. No operator action required beyond running `wave_index_build`.
5. The fix must apply to both branches that compute `files_for_meta` in `build_index`: the walk branch (line 1822) and the explicit-files branch (line 1863), so callers that pass `files=` directly are not exempted from the project-layer narrowing.

## Scope

**Problem statement:** Project-layer `meta.json` persists hashes for `.wavefoundry/framework/*` files that the project layer is supposed to exclude. This causes `wave_index_health` to permanently report those files as "removed" and `wave_index_build(mode="update")` to permanently disagree, because it sees the same broad walk on both sides.

**In scope:**

- `.wavefoundry/framework/scripts/indexer.py` — narrow `files_for_meta` to the project layer in both `build_index` branches (walk + explicit-files). Use the `_merged_project_include_prefixes_for_graph` superset so the filter is stable across docs/code content runs.
- `.wavefoundry/framework/scripts/tests/test_indexer.py` — regression test that exercises a docs-then-code (and code-then-docs) run sequence on a tree containing both project files and `.wavefoundry/framework/*` files, asserts the resulting `meta.json` `file_meta` contains only project files, and asserts the docs and code runs produce identical `file_meta` (the original "no alternating cycle" invariant remains).

**Out of scope:**

- The framework layer's meta computation. Not affected — its `files_for_meta` is already narrow via `include_prefixes`.
- The health check in `server_impl.py:_layer_current_hashes`. Already correct — the bug is on the meta-write side, not the health-read side. The reporter's Option B (loosen the health check to match the buggy meta) is explicitly rejected — it trades a real bug for documentation drift.
- The `project_include_prefixes` resolution in `_effective_project_include_prefixes`. Untouched — the run still uses the content-specific prefixes for what it embeds; only the meta-write filter uses the docs+code union.
- Changes to `wave_index_build` CLI surface or `wave_index_health` output schema.
- Tests in downstream projects (Solaris). The reporter will verify after this ships.

## Acceptance Criteria

- [x] AC-1: In `build_index` (walk branch at `indexer.py:~1822`), `files_for_meta` for the project layer is filtered through `_filter_project_index_excludes` using `_merged_project_include_prefixes_for_graph(root, project_include_prefixes)` as the include set — i.e. the docs+code union from `workflow-config.json`, not the per-run content type's include set.
- [x] AC-2: In `build_index` (explicit-files branch at `indexer.py:~1863`), the same narrowing is applied for the project layer. Framework-layer runs in either branch remain unchanged.
- [x] AC-3: After running `build_index(content="docs", mode="update")` and then `build_index(content="code", mode="update")` (or any order) on a tree containing both project files and `.wavefoundry/framework/*` files, the resulting `meta.json` `file_meta` contains **only** project files. No `.wavefoundry/framework/*` entries unless `project_include_prefixes` explicitly admits them.
- [x] AC-4: Docs-then-code and code-then-docs run sequences produce **byte-identical** `file_meta` dicts (the original "no alternating cycle" invariant — a single docs run does not "remove" code-run entries on the next code run, and vice versa).
- [x] AC-5: Self-heal: after this change ships, an existing project `meta.json` containing the 110+ phantom `.wavefoundry/framework/*` entries from the broken build is re-written without those entries on the first `build_index(mode="update")` call. `wave_index_health` reports the project layer as `current` (or only stale on legitimately changed paths) after that update.
- [x] AC-6: Framework layer health and meta are unchanged. `wave_index_health` for the framework layer reports the same set of files before and after this fix.
- [x] AC-7: New regression test in `tests/test_indexer.py` covers AC-3 and AC-4. All existing tests continue to pass.

## Tasks

- [x] Open `framework_edit_allowed` gate
- [x] Patch `indexer.py:~1822` (walk branch) to filter `files_for_meta` through `_filter_project_index_excludes` with the docs+code superset for project-layer runs
- [x] Patch `indexer.py:~1863` (explicit-files branch) with the same narrowing
- [x] Add regression test to `tests/test_indexer.py` covering the two-run sequence + assertion that framework files are absent from project meta
- [x] Run framework tests; verify all 1893 pass
- [x] Verified self-heal: injected 3 phantom framework entries into this repo's project meta, ran `build_index(content="docs", mode="update")`, all 3 were evicted
- [x] Close gate
- [x] Mark change `implemented`

## AC Priority

| AC | Priority | Rationale |
|---|---|---|
| AC-1 | required | The headline bug fix at the walk branch |
| AC-2 | required | Without it the explicit-files path leaks the same bug for callers that pass `files=` |
| AC-3 | required | The contract operators actually depend on — project meta is project-scoped |
| AC-4 | required | Preserves the original fix at line 1822 (no add/remove cycle) |
| AC-5 | required | Self-healing matters because the bug already shipped — operators should not have to manually `mode="rebuild"` |
| AC-6 | required | No regression for the working framework layer |
| AC-7 | required | Regression coverage so the line-1822 widening doesn't re-introduce the bug on a future refactor |

## Decision Log

| Date | Decision | Reason | Alternatives |
|---|---|---|---|
| 2026-05-31 | Option A (narrow `files_for_meta` to project layer with docs+code superset) | The bug is on the meta-write side; keeping `files_for_meta` in the broad walk leaks framework files into the project layer's persisted state. Using the docs+code union preserves the line-1822 fix (stable across content runs) | Option B (loosen the health check to match the broad meta — rejected, trades a real bug for documentation drift). Option C (have `build_index` self-evict cross-layer entries — rejected, adds a special case that obscures the layer boundary; the right place to enforce the boundary is the filter itself) |
| 2026-05-31 | Reuse `_merged_project_include_prefixes_for_graph` as the stable superset | Same function already exists for graph extraction and computes the same union of `workflow-config.json` docs+code prefixes; reusing it keeps the meta and graph layers consistent | Define a new helper (rejected — duplicates the existing one). Hardcode the prefixes (rejected — operators can override via `workflow-config.json`) |
| 2026-05-31 | Patch both `build_index` branches (walk + explicit-files) in the same change | The bug logically exists on both code paths; if only the walk branch is fixed, callers passing `files=` directly still leak | Patch only walk (rejected — leaves a known hole). Add a wrapper that callers must use (rejected — invasive caller change) |
| 2026-05-31 | Add to existing wave 130et rather than open a new wave | Operator request; the wave is in `implementing` status; one additional change keeps overhead low. The wave's bin-launcher objective is unrelated to indexer staleness, but the wave already serves as a "framework provisioning hot-fix" bucket | Open a new wave 130ng-bug-... (rejected per operator direction — wave 130et is the catch-all for this session's framework fixes) |

## Risks

| Risk | Mitigation |
|---|---|
| Filtering `files_for_meta` could re-introduce the 93-files-added/93-files-removed alternating cycle if the superset is computed inconsistently | Use `_merged_project_include_prefixes_for_graph`, which already provides a content-mode-independent union. Add an explicit AC-4 regression test asserting docs-run and code-run produce identical meta |
| Existing project meta.json files contain ~110+ phantom entries; downgrading framework versions could leave the meta inconsistent again | Documented as self-healing behavior (AC-5); on first incremental build with the fix, `_detect_changes` evicts the entries as `removed_broad` and writes the narrow meta. Downgrade is a separate failure mode and not a goal of this fix |
| Reporter's Option C (`build_index` self-heals cross-layer entries) could appear more robust to future filter drift | Rejected because it would mask future bugs of the same shape rather than enforce the layer boundary at the filter. AC-7's regression test is the correct safety net |
| `project_include_prefixes` that include `.wavefoundry/framework/scripts` (a common pattern for repos that want to search framework code) could behave unexpectedly | The same prefixes are passed through to `_filter_project_index_excludes`, so an explicit opt-in still admits those paths. Self-hosting repos (like this one) that include framework prefixes will see those specific paths persisted, which is the desired behavior — the bug was only about paths the layer was supposed to exclude |

## Related Work

- Companion to `130eu` (mcp-server launcher) and `130f9` (wave-gate rearchitecture) in the same wave (`130et`). All three are framework-provisioning hot-fixes surfaced by operator reports from downstream projects in the same session.
- Closes the same class of bug that the line-1822 inline comment was originally introduced to fix — the "alternating cycle" — by using the right narrowing technique (stable superset filter) instead of the wrong one (skip the filter entirely).

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.

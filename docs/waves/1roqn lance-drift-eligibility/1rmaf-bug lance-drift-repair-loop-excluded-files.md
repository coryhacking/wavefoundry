# Lance drift detection re-flags chunking-excluded files forever: non-converging repair loop defeats incremental-build fast paths

Change ID: `1rmaf-bug lance-drift-repair-loop-excluded-files`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-07-04
Wave: `1roqn lance-drift-eligibility`

## Rationale

`_detect_lance_drift` (`indexer.py:1892-1968`, waves 1p3b9/1p3iw) flags any `meta.json` path with zero Lance rows so a repair pass can re-chunk it. Its self-healing assumption — "one repair learns the true count and populates `chunks_emitted`; subsequent updates skip silently" (docstring, `indexer.py:1916-1920`) — **does not hold for files excluded from semantic chunking upstream**. `meta.json` tracks the full walked set (`files_for_meta`), but `chunks_emitted` is only recorded for files that pass the content filters (`files_for_content` → `files_to_index`, `indexer.py:3338-3361`). A meta-tracked file outside the content set therefore loops forever: drift check flags it (field absent or stale) → repair forces it into `changed` → chunking skips it (not in `files_for_content`) → the field never updates → next build re-flags it.

Live impact measured during wave `1p9q3`'s delivery review (performance lane, 2026-07-04): on this repo, `.wavefoundry/framework/scripts/tests/test_graph_incremental_merge.py` (unconditionally excluded from semantic chunking, 0 Lance rows) is drift-flagged on **every** build, forcing a ~1 s incremental graph merge plus ~1.35 MB of artifact writes per post-edit hook fire — permanently nullifying the zero-change fast path (0.3 s / 0 bytes) that wave `1p9q3` shipped as its dominant-case win. The reality-checker seat confirmed the loop persists whether the field holds a stale positive count or is absent entirely. Any target repo with at least one meta-tracked, chunking-excluded, zero-row file pays the same permanent tax.

## Requirements

1. **Eligibility-scoped drift detection.** Drift detection considers only paths that are chunk-eligible under the current build's content filters: the call site (`indexer.py:~3198`) passes the chunk-eligible rel-path set (derived from `files_for_content`) and `_detect_lance_drift` excludes paths outside it, alongside the existing `chunks_emitted == 0` exclusion. A path the current build would never chunk can never be "drifted".
2. **Stale-positive self-heal.** A path excluded from the content set whose meta entry carries a stale positive `chunks_emitted` (recorded under earlier include flags) is likewise not flagged — eligibility, not the recorded count, is the primary gate.
3. **Legitimate drift still repairs.** Chunk-eligible files with zero Lance rows and a missing/positive `chunks_emitted` field are still flagged and repaired exactly as today (the 1p3b9 contract is narrowed only by eligibility, not weakened for eligible files).
4. **Include-flag transitions stay sound.** When include flags change (e.g. `--include-tests` turns on), previously excluded files become eligible and, having zero rows, are flagged and repaired on the next build — the eligibility gate must be computed per build from the current filters, never persisted.
5. **Docstring truth.** The `_detect_lance_drift` docstring's self-healing narrative is corrected to state the eligibility precondition. It also states the per-branch eligibility semantics (qa challenge-round advisory): in the walk branch, `files_for_content` is content-scoped by the include-prefix reassignment (`indexer.py:3103-3112`); in the explicit-`files=` branch (3123-3164) no content-scoped reassignment occurs, so eligibility there is the normalized passed-in list — stated, not assumed.
6. **Diagnostic visibility.** When verbose, the build log distinguishes "N paths skipped as chunk-ineligible" from genuine drift repairs, so field reports can tell the two apart.
7. **Write-capability guard (council amendment, readiness review 2026-07-04).** Drift detection is skipped outright (or eligibility = ∅) when the build writes no semantic rows — `not (build_docs or build_code)`, i.e. `content="graph"` — because in that mode `files_for_content` is the UNFILTERED code walk (`_filter_code_files` is skipped when `build_code` is False) while nothing is ever written: the planned intersection would be a no-op and the loop would survive. "Chunk-eligible" must mean "row-writable this build", not merely "in the content walk".
8. **Distinct parameter naming (council amendment).** The new eligibility parameter is named distinctly (e.g. `chunk_eligible_rel_paths`) — `_reap_stranded_lance_rows` already takes an `eligible_paths` meaning the WIDER meta union; unifying them would make a docs-only run reap every code-table row. The reaper is untouched.

## Scope

**Problem statement:** Drift detection's candidate set (all of `meta.json`) is wider than the repair path's reach (content-filtered files), so excluded files loop forever, defeating the incremental build's zero-change fast path on every affected repo.

**In scope:**

- The eligibility parameter/intersection in `_detect_lance_drift` and its call site; docstring correction; verbose diagnostic.
- Tests: excluded-file non-flagging (missing field AND stale-positive field), eligible-file drift still repairs, include-flag transition re-flags, and a regression fixture mirroring the live loop (meta-tracked + excluded + zero rows → zero drift flags across two consecutive builds).
- Live verification on the self-hosted repo: after the fix, a graph-excluded doc edit takes the zero-change path (`merge[zero-change]`, 0 bytes) with no drift-repair line.

**Out of scope:**

- Changing which files are chunk-eligible (the content filters themselves).
- The graph subsystem (wave `1p9q3` — this defect merely nullified its win; no graph code changes here).
- Reworking `chunks_emitted` persistence shape or `meta.json` schema.
- Lance table hygiene/reaping (separate machinery; the reaper's WIDER `eligible_paths` semantics are deliberately untouched — Requirement 8).
- **Per-kind residual (named, deferred — council):** a docs-set file emitting only code-kind chunks records `chunks_emitted > 0` (the count sums both kinds, `indexer.py:3361`) while writes are per-layer-gated — such a file stays an eligible, zero-row, permanent drift candidate in docs builds even after this fix. Not present on this repo; recorded so the one-week watchpoint does not misattribute a recurrence.

## Acceptance Criteria

- [x] AC-1: On a fixture repo with a meta-tracked, chunking-excluded, zero-row file, two consecutive incremental builds produce zero drift flags for that file (both field states: absent and stale-positive). Unit-tested **at `content="docs"`** — the post-edit hook's default mode and the mode in which the live loop manifests (council amendment: an `all`-mode fixture would self-heal and prove nothing). *(Met 2026-07-04: `LanceDriftEligibilityBuildTests.test_ac1_docs_mode_excluded_zero_row_file_field_absent_never_flagged` + `…_stale_positive_never_flagged` — real `build_index` fixture with a `.wavefoundry/framework/scripts` file made meta-trackable via the workflow-config code prefix but outside the docs content walk; fixture-validity asserts pin the field-absent state before the incrementals; helper-level twins `test_excludes_chunk_ineligible_path_field_absent` / `…_stale_positive_field`.)*
- [x] AC-2: A chunk-eligible file with zero Lance rows is still drift-flagged and repaired (existing behavior preserved); the repair records `chunks_emitted` and the next build is quiet. Unit-tested (existing tests keep passing plus an explicit guard test). *(Met 2026-07-04: all 1p3b9/1p3iw drift tests pass with explicit eligibility supersets; new `test_ac2_eligible_zero_row_file_still_repaired_then_quiet` deletes an eligible file's Lance rows, asserts the repair line + row restoration + recorded `chunks_emitted` + quiet next build; helper-level `test_eligible_zero_row_path_still_flagged_alongside_ineligible_skip`.)*
- [x] AC-3: Flipping the include flag makes a previously excluded zero-row file eligible → flagged → repaired on the next build. Unit-tested **at `content="code"` with a regular test-path file** (`_is_test_code_path` class) — the live file's own exclusion is the UNCONDITIONAL framework-test carve-out (`_is_framework_test_path`), which no flag can re-include, so the transition necessarily exercises the flag-sensitive layer (council amendment). *(Met 2026-07-04: `test_ac3_include_tests_flip_makes_excluded_file_eligible_flagged_repaired` — `tests/test_helper.py` at `content="code"`: quiet with the flag off, flagged + repaired (rows written, `chunks_emitted > 0`) with `include_tests=True`, quiet again on the next build.)*
- [x] AC-4: Live self-hosted verification: post-fix, an edit to a graph-excluded doc produces a zero-change build (0 bytes written, no drift-repair for `test_graph_incremental_merge.py`); recorded in the Progress Log with the before/after build log lines. Note (council): the exact log token (`merge[zero-change]`) ships with wave `1p9q3` — re-verify the landed wording before asserting on it. Trial validity (rotating seat): the edited doc must be DOCS-ELIGIBLE so the build passes the stale gate — expected evidence is the line pair (incremental-update line + `merge[zero-change]`) plus the ABSENCE of the "repairing N drifted file(s)" stderr line; a bare "index is up to date" early-return is an INVALID trial (re-pick the edit target), not a pass. *(Met 2026-07-04: token re-verified in landed code (`indexer.py` merge log line + `graph_indexer.py` mode="zero-change"); before/after log lines in the Progress Log — the first AFTER target (`docs/references/project-overview.md`) proved graph-INCLUDED and was re-picked per protocol to a `docs/waves/` file; all edited files restored byte-identically (`cmp`-verified).)*
- [x] AC-5: Docstring corrected; verbose log distinguishes ineligible-skips from drift repairs (log-shape asserted in test). *(Met 2026-07-04: docstring states the eligibility precondition, per-branch semantics, the write-capability rule, and the reaper naming firewall; log shape pinned by `test_verbose_logs_ineligible_skip_count_with_reason` (+ quiet contrapositive) and the graph-mode reason line by `test_ac6_graph_only_incremental_no_repair_log_and_verbose_reason`.)*
- [x] AC-6: A `content="graph"` incremental build performs no drift detection (or an empty eligibility set) and flags nothing — the write-capability guard (Requirement 7) is pinned by test, including asserting the ABSENCE of the "repairing N drifted file(s)" stderr line (qa seat: an empty drift set alone would not prove the misleading log path is dead in that mode). *(Met 2026-07-04: `test_ac6_graph_only_incremental_performs_no_drift_detection` pins zero `_detect_lance_drift` calls via monkeypatch capture; the unpatched twin asserts the repairing line is ABSENT with a meta-tracked zero-row file present and that the verbose skip line states the "no semantic writes" reason.)*
- [x] AC-7: `python3 .wavefoundry/framework/scripts/run_tests.py` passes; `wave_validate` clean; no `__pycache__` under `scripts/`. *(Met 2026-07-04: 4,358 tests OK — 12 new (5 helper-level + 7 build-level); one pre-existing unrelated `test_wf_cli` failure (stale generated `codebase-map.md` committed during wave `1p9q3`'s no-graph-artifact window) fixed in-session by regenerating the map; `wave_validate` clean; `__pycache__` cleaned.)*

## Tasks

- [x] Derive the chunk-eligible rel-path set at the `_detect_lance_drift` call site from `files_for_content` — gated on `build_docs or build_code` (empty/skip for graph-only builds, Requirement 7); pass it as `chunk_eligible_rel_paths` (distinct from the reaper's `eligible_paths`, Requirement 8); intersect in the helper alongside the `chunks_emitted == 0` exclusion. *(Done 2026-07-04: call site skips drift outright when neither boolean is set, with the reasoned verbose line; helper takes the REQUIRED keyword-only set and intersects before the `chunks_emitted == 0` exclusion.)*
- [x] Correct the docstring; add the verbose ineligible-skip line. *(Done 2026-07-04: eligibility precondition + per-branch semantics + write-capability rule + reaper naming firewall in the docstring; "drift-detect skipped N path(s) as chunk-ineligible (outside this build's content filters)" verbose line.)*
- [x] Tests per AC-1..AC-3 + AC-6 + the log-shape assertion (AC-5), in the existing drift-test conventions; update the ~12 existing `_detect_lance_drift` direct callers for the required keyword-only parameter; add the reaper-wide-set tripwire test (idle path passes the meta union, never the narrow eligibility set). *(Done 2026-07-04: all 13 existing direct call sites migrated to explicit eligibility supersets — the 1p3iw narrowing-guard tests stay non-vacuous with the zero-row path IN the eligibility set; 5 new helper-level tests + new `LanceDriftEligibilityBuildTests` (7 tests) incl. the `test_idle_reap_still_receives_wide_meta_union` tripwire asserting the captured reap argument equals the full meta union including the chunk-ineligible path.)*
- [x] Live before/after verification on the self-hosted repo (AC-4); record build-log evidence. *(Done 2026-07-04: Progress Log rows below with the actual log lines.)*
- [x] Run `run_tests.py` + `wave_validate`; clean `__pycache__`. *(Done 2026-07-04: 4,358 OK; validate clean; pycache cleaned.)*

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| ws1-eligibility-gate | implementer | — | Call-site set derivation + helper intersection + docstring + verbose line. |
| ws2-tests-and-verify | implementer | ws1-eligibility-gate | Fixture tests (both field states, eligible-repair guard, flag transition, log shape) + live self-hosted verification. |


## Serialization Points

- Single-file change surface (`indexer.py` + its test file) — no cross-lane coordination. Wave `1p9q3` must be closed first (single-OPEN rule); no code overlap with its diff beyond reading the build log format.

## Affected Architecture Docs

N/A — confined to the semantic-index drift-detection path inside `indexer.py`; no boundary, flow, or contract change. (The drift-detection behavior notes in `docs/architecture/` are audited for the docstring-truth correction if any doc restates the self-healing narrative.)

## AC Priority

(Populated at Prepare wave.)


| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The non-converging loop is the defect; both field states must be covered. |
| AC-2 | required | Narrowing must not weaken legitimate drift repair — the 1p3b9 contract stands for eligible files. |
| AC-3 | required | Include-flag transitions are the boundary where an over-broad exclusion would silently strand real drift. |
| AC-4 | required | The live nullifier on this repo is the motivating evidence; its disappearance is the proof. |
| AC-5 | important | Docstring truth + field diagnosability; no behavioral risk. |
| AC-6 | required | Council amendment: the graph-mode no-op hole is the exact defect shape surviving in one mode — the guard must be pinned, not assumed. |
| AC-7 | required | Standing merge gates. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-07-04 | **Live before/after verification (AC-4, self-hosted repo, fresh venv subprocess `~/.wavefoundry/venv/bin/python3 .wavefoundry/framework/scripts/indexer.py --root .` — bare, docs default, exactly like the hook; trial edits = trailing append to a docs file, restored byte-identically and `cmp`-verified).** BEFORE (single docs-file change): `build_index: repairing 1 drifted file(s): .wavefoundry/framework/scripts/tests/test_graph_incremental_merge.py` + `finished graph: 2 changed … merge[incremental]: 1.0s \| delta: files=2 … \| sidecar: reads=1 writes=1 bytes=785522` — the drift-injected framework-test file inflates the graph delta and forces the incremental merge + ~785 KB sidecar write on every build. AFTER, trial 1 (`docs/references/project-overview.md`): NO repairing line, but graph delta still incremental — the target proved graph-INCLUDED (its pre-fix restore run showed `files=2`, i.e. itself + the drifted file), an invalid target for the zero-change token; re-picked per the AC-4 protocol. AFTER, trial 2 (`docs/waves/1p9q3 graph-index-efficiency/wave.md`, graph-excluded + docs-eligible): the exact expected line pair — `build_index: updating docs/seed index — 1 file(s) changed, 0 removed` … `finished doc files: 0 added, 1 updated` PLUS `finished graph: 1 changed, 0 removed … merge[zero-change]: 0.0s \| delta: files=0 removed=0 symbols=0 edges_reresolved=0 \| state io: reads=0 writes=0 \| sidecar: reads=0 writes=0 bytes=0` — and the repairing line ABSENT (not an "index is up to date" early return: the docs update ran, so the trial is valid). The restore run reproduced the same zero-change pair. `merge[zero-change]` token re-verified in landed code before asserting (merge log line in `indexer.py`; `mode="zero-change"` in `graph_indexer.py`). | Build logs 2026-07-04 06:33Z (before) / 06:45–06:46Z (after); `cmp` byte-identical restore checks. |
| 2026-07-04 | **Implementation landed (builder lane).** `_detect_lance_drift` gains REQUIRED keyword-only `chunk_eligible_rel_paths: set[str]`; the eligibility intersection sits alongside the `chunks_emitted == 0` exclusion, with the verbose "drift-detect skipped N path(s) as chunk-ineligible (outside this build's content filters)" line; docstring rewritten per Req-5 (eligibility precondition, per-branch walk vs explicit-`files=` semantics, write-capability rule, reaper naming firewall). Call site: eligibility derived from `files_for_content` with the standard normalization, gated on the `build_docs or build_code` BOOLEANS; graph-only builds skip drift detection outright (no Lance column scans, no repairing line) with the reasoned verbose skip ("no semantic writes this build (graph-only)"). `_reap_stranded_lance_rows` and its wide idle-path call untouched (Req-8). Tests: 13 existing direct callers migrated to explicit eligibility supersets (narrowing guards non-vacuous); 5 new helper-level tests (ineligible field-absent, ineligible stale-positive, eligible-still-flagged, AC-5 log shape + quiet contrapositive); new `LanceDriftEligibilityBuildTests` (7 real-`build_index` tests: AC-1 both field states at docs mode, AC-2 repair-and-converge, AC-3 include-tests flip at code mode, AC-6 patched no-call + unpatched no-repair-line/verbose-reason, reaper-wide-union tripwire). Fixture note: docs-mode fixtures pin `docs/workflow-config.json`'s `chunks_emitted` to 0 post-build — the file emits only code-KIND chunks, i.e. the change doc's named-deferred per-kind residual, which would otherwise be drift-flagged and drown the assertions (on the live repo the equivalent files have code-table rows from all-mode setup). Suite: 4,358 OK (12 new). One unrelated pre-existing failure fixed in-session: `test_wf_cli` docs lint tripped on the committed `docs/references/codebase-map.md` fallback content (regenerated during wave `1p9q3`'s no-graph-artifact window); regenerated via `gen_codebase_map.py` (the same run also rewrote `docs/repo-index.md`'s `waveframework:repo-index-modules` marker block — both purely generated) from the current graph artifact. | `indexer.py` (helper + call site), `tests/test_indexer.py`; test runs 2026-07-04; regenerated `docs/references/codebase-map.md`. |
| 2026-07-04 | Readiness-council seat amendments (qa + security seats): (1) **Signature migration decision** — `chunk_eligible_rel_paths` is a REQUIRED keyword-only parameter of `_detect_lance_drift`; all ~12 existing direct test callers (`LanceDriftDetectionTests` / `LanceDriftDetectionScaleTests`, `tests/test_indexer.py:2320-2560`) are updated to pass explicit eligibility supersets — an optional default of "no filtering" would silently preserve the bug for future callers and make the existing narrowing-guard tests vacuous. (2) AC-6 additionally asserts the absence of the "repairing" stderr line (amended in place). (3) Security-seat tripwire test added to ws2: the idle-path `_reap_stranded_lance_rows` call must still receive the WIDE meta union — the zero-change fast path becomes the common path post-fix, so a set mix-up would be high-frequency destructive; pin it. (4) Verbose ineligible-skip line states the REASON ("no semantic writes this build" for graph mode) so quiet builds are distinguishable from no-drift builds in field logs. | qa/security readiness seats 2026-07-04. |
| 2026-07-04 | Readiness-council amendments (red-team primer at standard depth): (1) write-capability guard — `content="graph"` builds have `build_docs=build_code=False`, `files_for_content` = UNFILTERED code walk, zero rows written → the bare intersection is a no-op and the loop survives in that mode; Requirement 7 + AC-6 added. (2) Test content-mode pinning — the hook invokes the indexer bare (default `content="docs"`), which is where the live loop manifests; AC-1 pinned to docs mode, AC-3 pinned to code mode with the flag-sensitive file class (the live file's carve-out is unconditional and can never re-include). (3) Parameter naming hazard vs the reaper's wider `eligible_paths` — Requirement 8. (4) Per-kind residual (docs-set file emitting only code-kind chunks) named as deferred out-of-scope. (5) AC-4's log token depends on wave `1p9q3` landing — note added. | Red-team readiness primer 2026-07-04. |
| 2026-07-04 | Scoped from wave `1p9q3` delivery-review findings (performance lane discovery; reality-checker framing correction: the defect is the exclusion-vs-drift-scope mismatch, not any particular `chunks_emitted` value — the self-healing assumption cannot hold for files that never reach the chunk-write path). Mechanism verified: meta covers `files_for_meta`; `chunks_emitted` recorded only inside the `files_to_index` loop (`indexer.py:3353-3361`); drift check consults only the field (`indexer.py:1938-1941`). Live loop measured: ~1 s + ~1.35 MB per hook fire on this repo, permanent. | Wave `1p9q3` review records 2026-07-04; `indexer.py` reads; performance-lane build logs. |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-07-04 | Gate drift candidacy on current-build chunk eligibility (intersection at the call site), computed per build and never persisted. | The candidate set must match the repair path's reach or the loop is structural; per-build computation keeps include-flag transitions sound (Req-4) with zero schema change. | (B) Persist an `excluded: true` marker in meta — rejected: persisted eligibility goes stale the moment flags change, recreating the loop in the other direction. (C) Record `chunks_emitted: 0` for excluded files at walk time — rejected: lies about what a chunking pass would produce and breaks the include-flag transition (a newly eligible file would be skipped as "legitimately empty"). |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Over-broad eligibility derivation silently exempts genuinely drifted eligible files. | AC-2 guard test pins that eligible zero-row files still repair; the eligibility set is derived from the same `files_for_content` the chunk loop uses — one source of truth. |
| Include-flag transition edge (excluded → eligible) misses the one-shot repair. | AC-3 test pins the transition; eligibility computed per build from current flags. |
| The live nullifier has a second contributing cause not covered by eligibility gating. | AC-4 live verification is the end-to-end proof on the motivating repo; failure there reopens the diagnosis before close. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.

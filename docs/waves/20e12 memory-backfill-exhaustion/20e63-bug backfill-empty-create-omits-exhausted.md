# Memory Backfill Never Completes A Wave Whose Sources All Already Exist

Change ID: `20e63-bug backfill-empty-create-omits-exhausted`
Change Status: `implemented`
Owner: Engineering
Status: active
Last verified: 2026-10-11
Wave: 20e12 memory-backfill-exhaustion

## Rationale

**Brief.** Goal: a historical memory backfill batch completes a wave whose sources are all already recorded, dispositioned or purged, instead of re-claiming it forever. Consumer: an operator running `wf_upgrade` (protocol-2 memory step) or `memory_backfill` on a repository whose memory records already cover the wave. Constraint: no change to what is written, only to the completion signal on an empty page. Success: such a wave is marked complete in one batch and the run converges.

Field report (a consumer-repository upgrade, relayed by the operator): the memory backfill step could not complete; the same wave was processed on every batch. The reporter diagnosed that, when every candidate already exists, the response omits `exhausted: true`, and proposed adding `exhausted: true` and `records_remaining: 0` to the empty create result. The proposal was reviewed against HEAD and is confirmed below.

**Verified at HEAD** (read-only, `wf_server/memory_handlers.py`; symbols are the anchors, line numbers are advisory).

- `_memory_propose_response_locked` builds `drafts`, then counts `eligible_count` after skipping drafts whose source is already a record, a disposition or a purged digest, and drafts whose normalized content duplicates an existing record. When `unique` is empty in `mode="create"` it returns early (near line 991-992) with `records_written`, `records_promoted`, `records_proposed`, `written`, `skipped_dispositions`, `skipped_duplicates` and `mode`, and NO `exhausted` or `records_remaining`.
- The `dry_run` return (near 977-978) and the normal create return (near 1045-1046) set both; the other ok returns omit them, and by read-only census none is on the historical batch path except `no_material_evidence`, which the consumer covers through `no_source`: `selection_required` (public tool only), the `source_events == []` return (the batch never passes `source_events`) and `no_material_evidence`. The two set paths compute `records_remaining = max(0, eligible_count - len(unique))` and `exhausted = eligible_count <= len(unique)`.
- `_memory_backfill_batch_locked` computes `exhausted = no_source or bool(data.get("exhausted"))` (near 1290). `no_source` is true only for the `no_material_evidence` diagnostic, which the `if not drafts` branch emits. A wave with drafts that are all already covered has drafts, so `no_source` is false, `data.get("exhausted")` is `None`, and `complete_claim(..., exhausted=False)` leaves the wave pending. The next batch claims it again: an unbounded loop.
- `remaining_budget` is floored at 1 (near 1223) and passed as `limit`, so an empty `unique` on this path implies `eligible_count == 0`; reporting `exhausted: true` is correct, not optimistic. The `if not unique` branch is also reachable when a caller supplies `source_events` that filter every draft out; there too `eligible_count` counts only the surviving drafts, so the same reasoning holds.
- Existing tests (`tests/test_memory_backfill.py`, near 311 and 675) pass `exhausted=True` directly to the completion helper and a two-step page test (near 754-762) covers a non-empty page; none drives the all-covered empty create result.
- The upgrade runner calls `_memory_backfill_batch_locked` once in Phase 3 (a review traced it in `upgrade_wavefoundry.py` `main`). With the wave still pending the run stays `awaiting_validation`, the runner writes the historical-memory action-required pause and exits before Phase 4, and repeated `memory_backfill` calls then re-claim the same wave: the upgrade stalls at that pause rather than looping inside the runner. Because `remaining_budget -= count` subtracts 0, the same wave can also be re-claimed up to `MAX_WAVES_PER_CALL` times within one call.
- Not verified here: whether any other consumer of the empty create result treats a missing `exhausted` as meaningful, and whether the reporter's repository hit exactly this branch (their account of the symptom matches it).

## Requirements

1. The create-mode empty-`unique` result of `_memory_propose_response_locked` carries `records_remaining: 0` and `exhausted: True`, so the shape matches the sibling return paths.
2. `_memory_backfill_batch_locked` marks a wave whose drafts are all already covered as complete (`complete_claim(..., exhausted=True)`) with outcome `extracted` and zero candidates written, and the run then advances to the next wave or to validation.
3. No other behavior changes: `records_written`, the skip counters, the fence handling, the `no_material_evidence` path and the non-empty create path are untouched.
4. The set of return paths is derived by rule, not by memory: every `return server_impl._response("ok", ...)` inside `_memory_propose_response_locked` that can be reached in `mode="create"` is listed in the Progress Log with whether it carries `exhausted`, and any further omission found is fixed or dispositioned with a reason. The `source_events == []` early return (near line 928) is known to omit the flag and must be listed with its disposition (a caller that selects nothing reaches it, not the historical batch path, which is unverified).

## Scope

**Problem statement:** the empty create result omits the completion flag, so backfill never marks an already-covered wave complete and loops.

**In scope:**

- The one return payload and the Requirement 4 census in `wf_server/memory_handlers.py`.
- A regression test in `tests/test_memory_backfill.py` (or the suite that already drives `_memory_backfill_batch_locked`).

**Out of scope:**

- Changing how drafts are deduplicated or dispositioned.
- A loop guard that bounds repeated claims of one wave (worth considering separately; recorded in the Decision Log).
- Patching any consumer repository's installed framework; that stays a temporary local workaround until a release carries this fix.

## Acceptance Criteria

- [x] AC-1: A test builds a wave whose draftable sources all already exist as memory records, runs `_memory_backfill_batch_locked` (or the public `memory_backfill` in create mode), and asserts the processed entry has `exhausted: True`, `candidates_written: 0` and a non-failed outcome, and that the claim is completed (the wave is not claimable again). The test fails on the unfixed code (record the observed failure in the Progress Log).
- [x] AC-2: After ONE batch on the all-covered fixture, `len(processed) == 1`, the entry has `exhausted` True, and the run summary reports `remaining_waves == 0`; a second batch returns `processed == []`. The unfixed code returns `MAX_WAVES_PER_CALL` entries for the same wave, so the test fails by assertion and cannot hang. Extraction completion is determined by processed/remaining fields, independently of run-state name; this fixture additionally asserts `awaiting_validation` because its deliberately seeded candidate must retain the validation gate.
- [x] AC-3: The direct response test reaches the empty-`unique` branch through `_memory_propose_response_locked(..., mode="create", _historical_batch=True)` (the public `memory_propose` without `source_events` returns `selection_required` first) on the all-covered fixture, and asserts `records_remaining == 0`, `exhausted is True` and no record written. The empty-`unique` inference needs a page limit of at least 1; the test pins that precondition and the doc records it.
- [x] AC-4: A two-sided positive control: a wave with one uncovered draft and a limit that fits it reports `exhausted` True, and an overflow variant with more uncovered drafts than the limit reports `exhausted` False with a positive `records_remaining`, so a fix that blanket-sets the flag fails.
- [x] AC-5: The Requirement 4 census is recorded in the Progress Log.
- [x] AC-6: The suites `tests/test_memory_backfill.py` and the memory handler suites that exercise `memory_propose` pass, with every test this change adds; the documents this change authors or edits validate.

## Tasks

- [x] Add the failing regression tests first (AC-1, AC-2, AC-3, AC-4) and record the observed failure.
- [x] Add `records_remaining` and `exhausted` to the empty create payload.
- [x] Run the Requirement 4 census over the create-reachable return paths and log it.
- [x] Add the `CHANGELOG.md` Unreleased bullet, stating the old-code-window behavior from Serialization Points.
- [x] Run the memory suites and validate docs.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| regression-tests | implementer | none | All-covered fixture; fails before the fix |
| payload-fix | implementer | regression-tests | One return payload |
| census | guru | none | Read-only; create-reachable return paths |


## Serialization Points

Windows (native), macOS, Linux and WSL2 behavior: pure Python control flow over already-loaded records, with no filesystem, newline or process behavior involved, so it is identical on every platform.

Sequencing: all earlier implementation waves, including `20dkl`, are closed, so this change needs its own new wave; it touches neither `upgrade_wavefoundry.py` nor `upgrade_extensions.py` and adds no ordering constraint on other waves.

Old-code window: the upgrade runner's memory step (Phase 3) imports `server_impl` after extraction, so a runner that reaches that phase loads the pack's fixed `memory_handlers.py` on the same upgrade that ships it. A consumer already stopped at the historical-memory action-required pause on an older install needs the next upgrade to a release carrying the fix; a local patch there is discarded when extraction overwrites the file.

The CHANGELOG bullet is a root-level file and so is declared in prose rather than as a review target: `CHANGELOG.md` gets one Unreleased bullet.

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/scripts/wf_server/memory_handlers.py`
- `.wavefoundry/framework/scripts/tests/test_memory_backfill.py`

## Affected Architecture Docs

N/A: one return payload in one handler with no boundary or flow change. `docs/specs/mcp-tool-surface.md` documents no `exhausted` or `records_remaining` result shape for `memory_propose` or `memory_backfill` (checked by a read-only review), so no spec edit is needed; the sibling code paths already set the fields.

## AC Priority


| AC | Priority | Rationale |
| -- | -------- | --------- |
| AC-1 | required | The reported non-completion |
| AC-2 | required | Proves the loop actually ends |
| AC-3 | important | Pins the response contract directly |
| AC-4 | important | Guards against blanket-setting the flag |
| AC-5 | important | Bounds other omissions on the same function |
| AC-6 | required | Change-local test and doc validity |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-10-11 | Planned from a consumer-repository upgrade report; the reporter's diagnosis and proposed payload fix were confirmed against HEAD by reading the code, not by running it | Read-only review of `memory_handlers.py` |
| 2026-10-11 | Product Intent: not applicable (bounded existing-behavior bug repair; operator explicitly requested implementation on 2026-10-11) | Planning |
| 2026-10-11 | Readback: add only zero-remaining/exhausted metadata to the empty create result. Before: an already-covered wave is reclaimed ten times; after: one completed extraction and an empty second batch, while the existing candidate still awaits validation. AC-1 through AC-6 cover real producer/consumer behavior, paging controls and the return census. Affected files are the declared handler, backfill tests and one Unreleased changelog bullet. | Independent readiness council and required lanes approved; Prepare recorded readiness before implementation. |
| 2026-10-11 | Added four real-handler regression tests before changing production code. Pre-fix run: 4 tests, one assertion failure (`10 != 1`), two subtest errors (missing `records_remaining`), zero skips; exact-fit and overflow controls passed. Adding only the two fields makes all four pass. The all-covered test also preserves the seeded candidate and its validation gate. | `HistoricalMemoryBackfillTests.test_all_handled_wave_completes_once_without_bypassing_validation`, `test_empty_create_reports_exhaustion_for_already_handled_sources`, `test_nonempty_exact_final_page_reports_exhaustion`, `test_nonempty_overflow_page_remains_unexhausted`; explicit unittest selection, real scratch repository and producer/consumer. |
| 2026-10-11 | Closed return census: AST rule enumerates every successful response return in `_memory_propose_response_locked`; control flow makes five of six create-reachable. `selection_required` and explicit `source_events == []` intentionally omit completion (no reviewed selection is not proof the wave is handled); neither is a historical-batch path. `if not drafts` omits completion but emits `no_material_evidence`, which the consumer already treats as exhausted. `dry_run` has completion fields and is not create-reachable. Empty `unique` now has both fields; normal create already has both and retains paging arithmetic. No further repair is needed. | Actual source reads and executable AST census independently confirmed by readiness Council; page size `n >= 1` makes empty `unique` imply zero eligible candidates. AC-5. |
| 2026-10-11 | Added one Unreleased changelog bullet. The installing upgrade imports `server_impl` in Phase 3 after extraction, then calls the same producer through `_memory_backfill_batch_locked`; no runner edit, additional upgrade scan or qualification step was introduced. | `upgrade_wavefoundry.main`, historical-memory block; `CHANGELOG.md`. Live consumer upgrade and native Windows execution remain untested. |

| 2026-10-11 | Focused qualification passed: the backfill and memory-record suites ran 285 tests with zero skips. Full docs validation passed; canonical full-suite qualification follows on the frozen source. | `python3 -B -m unittest test_memory_backfill test_memory_records` with framework/tests on PYTHONPATH; full `wf_validate_docs`; `git diff --check`. |

| 2026-10-11 | Canonical qualification passed on the unchanged source: 12,340 tests across 185 files, 12 skips, 1040.494 seconds. Initial sandbox run was stopped after the host denied loopback binding; host-permission rerun passed the dashboard and entire suite. | `python3 -B .wavefoundry/framework/scripts/run_tests.py`, bytecode disabled, four workers; genuine green receipt at `2026-10-11T21:14:42.201623+00:00`, inputs hash `5ed1b9307eb4afdd8d269742ef9721b91caf8523c5a76a7712a00a186071a17b`. No injected receipt, consumer upgrade or package build. |

| 2026-10-11 | Independent delivery code, QA, architecture and full standard Council approved with no material findings. In-memory removal and blanket-exhaustion mutants were detected; interrupted-checkpoint retry passed. Clarified AC-2 in its owning section to distinguish extraction completion from the seeded-candidate state control; fresh focused readiness reviewers and Council approved the new receipt, then Prepare passed. Source/test behavior and full suite receipt remain unchanged. | Typed delivery/readiness events; source/test mutant table and actual seat roster consolidated in `wave.md`. No additional full suite, persistent review sidecars or upgrade work added. |

## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-10-11 | Set the flag at the empty create return | Matches the sibling return shapes and is provably correct there (empty `unique` implies zero eligible) | A: treat a missing `exhausted` as true in the batch consumer (weakness: hides future payload omissions and changes a shared consumer). B: also add a repeated-claim loop guard (weakness: separate failure class, larger change; left as a follow-up). C (selected): fix the producer |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Another create-reachable return path also omits the flag | Requirement 4 census and AC-5 |
| The flag is set where eligible sources remain | The empty branch implies `eligible_count == 0`; AC-4 is the positive control |
| The reporter's repository hit a different branch | The Rationale marks that as unverified; AC-1 reproduces the described state independently |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.

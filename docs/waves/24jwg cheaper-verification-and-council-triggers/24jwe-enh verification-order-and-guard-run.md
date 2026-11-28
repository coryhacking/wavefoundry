# Order verification by cost, with a guard run

Spec ID: `24jwe-enh verification-order-and-guard-run`
Spec Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-11-27
Wave: 24jwg cheaper-verification-and-council-triggers

## Rationale

Wave 24i2t spent about 95 minutes on seven full framework suite runs against about 25 minutes of review (`.wavefoundry/work/24i2t/process-review.md`). Two of those runs failed in guard files that take seconds: the handler-digest pin (`tests/test_mcp_tool_registry.py`, 5.8 s) and the single-reader scan (`tests/test_venv_bootstrap.py`, 3.3 s). The runner prints each file's ok or FAIL line as that file completes (`run_tests._execute_files`, the `as_completed` loop, `flush=True`; the module docstring's "buffered" note describes only the failure detail), but it starts files alphabetically by default (`run_tests._schedule_order`, `"alphabetical"` at the default call site), so `test_venv_bootstrap.py` started 238th of 261 and its failure line appeared only near the end of a 13 to 15 minute run. Four more runs followed repairs that a focused run would have checked; close needs only one green receipt on the final tree (`lifecycle_gates._framework_test_receipt_status`). The canonical seeds say nothing about ordering verification by cost, so every target project, and Waveforge after it takes a release, repeats the pattern.

## Product Intent

An agent implementing or repairing a wave, in any project that installs Wavefoundry, finds its cheap failures in seconds and runs the full verification once, as the last step before close. In this repository a maintainer gets a one-command guard run. Before: guard failures surface after a full run, and full runs repeat after every repair. After: touched-file tests and guards run first and after each repair, and the full suite runs once. Boundaries: the close gate, the receipt and its scope are unchanged; no test is skipped from the full run.

AC-1 and AC-2 establish the maintainer outcome; AC-3 and AC-4 establish the guidance every project receives. Agent behaviour downstream is observable only in later waves: the number of full runs per wave in work logs.

## Requirements

1. The guard set is a module-level `GUARD_TEST_FILES` tuple in `run_tests.py`: test files that assert a source-wide invariant (a pinned digest, a single-reader or literal scan, a census) and finish in seconds. It starts with `test_mcp_tool_registry.py`, `test_venv_bootstrap.py` and the census and scan files the implementer selects by that rule, each named with the invariant it guards in a comment; behaviour suites whose names happen to contain "guard" are not included. A name in the tuple that matches no discovered file is a usage error for `--guards` runs; full runs order by the guard files that exist, so a renamed guard never blocks the run that writes the receipt, and a static test asserts every name exists in the real tests directory.
2. `run_tests.py --guards` runs a focused run over the guard set and writes no receipt. It combines with `--file` as a deduplicated union (guards first, then the `--file` selections in the given order); only overlap between the two is deduplicated, so a repeated `--file X --file X` is still refused. It is accepted or refused in exactly the combinations `--file` is: allowed with `--profile`, refused with `--no-cache`, `--schedule-control` and `--qualify-profile`. The usage text documents it and states that it is not delivery evidence.
3. In full runs (default and `--no-cache`), the guard files start first and the remaining files keep their existing order, applied at the production call site only; the schedule-control benchmark modes and `_schedule_order`'s alphabetical branch are unchanged, so a guard failure's FAIL line appears within about the first minute. Every file still runs; the receipt rules are unchanged.
4. Seed 180 gains a short section on ordering verification by cost: run the tests for touched files and the project's fast guard tests (pins, scans, censuses) first; after each repair rerun only what the repair affects plus the guards; run the project's full verification once per wave, after the last repair, as the last step before close. It names the project's declared verification commands, not this repository's runner.
5. Seed 209 "Repair re-verification" states that a re-verifying lane is briefed with the original finding, the repair diff and the directly affected context rather than the full packet, while keeping its existing duties (rerun the original reproduction, run the named adjacent controls, check for a replacement defect), and that the full verification runs once per wave after the last repair.
6. `docs/contributing/build-and-verification.md` documents `--guards`, the guard-first full run and the order: `--file` for touched files plus `--guards` after each edit, then one plain full run (which writes the receipt) before close.

## Scope

**In scope:** `run_tests.py` argument parsing, guard-set derivation and usage text; its tests; seeds 180 and 209; `docs/contributing/build-and-verification.md`; CHANGELOG.

**Out of scope:**

- A per-file or incremental receipt for test-only edits (declined at planning: 40 test files import other test modules, so a sound rule needs a dependency scan and a new trust rule for the receipt, and batching repairs already removes most of the saving).
- Streaming failure detail early.
- Changing the receipt's scope or the close gate.

## Acceptance Criteria

- [x] AC-1: `run_tests.py --guards` runs exactly `GUARD_TEST_FILES`, writes no receipt, and combines with `--file` as a deduplicated union in the stated order, including when a selection overlaps the guard set. Oracle: runner tests over a fixture discovery list; fails today because `--guards` is an unknown option.
- [x] AC-2: In a `--guards` run, a `GUARD_TEST_FILES` name that matches no discovered file produces a usage error, and a static test asserts every listed name exists. Oracle: runner tests.
- [x] AC-3: Seed 180 and seed 209 carry the Requirement 4 and 5 guidance in project-neutral terms, and seed 209 keeps its re-verification duties. Oracle: a seed text test asserting the key clauses and the absence of `run_tests.py`, `--guards`, `GUARD_TEST_FILES` and repository test file names.
- [x] AC-6: The order the production full-run path submits starts with the guard files and keeps the rest in their previous order, while schedule-control orders are unchanged. Oracle: a test that drives the default full-run path (not `_schedule_order` alone) and captures the submitted order; fails today (alphabetical puts `test_venv_bootstrap.py` near the end).
- [x] AC-4: `docs/contributing/build-and-verification.md` documents `--guards` and the verification order. Oracle: docs review plus `wf_validate_docs`.
- [x] AC-5: The change's own suites and every test it adds pass, including the second profile for each touched test file; the documents this change authors or edits validate; and no failure elsewhere is attributable to this change.

## Tasks

- [x] Add `GUARD_TEST_FILES`, `--guards` and guard-first ordering to `run_tests.py`, with tests; correct the module docstring's buffering note.
- [x] Add the seed 180 section and the seed 209 sentences (under `seed_edit_allowed`), with a seed text test.
- [x] Update `docs/contributing/build-and-verification.md` and the CHANGELOG.

## Serialization Points

- `.wavefoundry/framework/scripts/run_tests.py`, `.wavefoundry/framework/scripts/tests/test_run_tests_cache.py`
- `.wavefoundry/framework/seeds/180-implement-spec.prompt.md`, `.wavefoundry/framework/seeds/209-agent-harness-core.prompt.md`
- `docs/contributing/build-and-verification.md`, `docs/architecture/testing-architecture.md`

## Affected Architecture Docs

`docs/architecture/testing-architecture.md`: its runner row and its record of the measured alphabetical schedule change to describe guard-first ordering of production full runs. No boundary or flow change otherwise.

## Platform Behaviour

`--guards` uses the existing discovery and worker path, so it behaves the same on Windows, macOS, Linux and WSL2. Native Windows is not executed in this wave.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | The maintainer outcome |
| AC-2 | important | Keeps the explicit list from rotting |
| AC-3 | required | The guidance every project receives |
| AC-4 | important | This repository's procedure |
| AC-5 | required | Change-local verification |
| AC-6 | required | Early signal on the full run |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-11-27 | Close preparation: the `.wavefoundry/work/24jwg/` readiness and delivery reports, delivery paths and final suite log are archived in `evidence/review-notes.tar.gz` | `evidence/review-notes.tar.gz` |
| 2026-11-27 | Gapfill: implementation edits were bulk-mechanical exact-string replacements and appends applied with short Python scripts, and code was read with targeted `sed`/`grep` over known symbols named by the readiness reports; MCP code tools were used by every review lane for claim checks. Recorded so the retrieval-posture advisory has its explanation | close dry run `retrieval_posture_gap` |
| 2026-11-27 | Final verification: three full runs launched from the shell harness were killed externally (exit 144, at files 191, 6 and 15, no summary; memory and framework code ruled out); a run launched in its own session completed. It surfaced two more evaluator-version pins, both confirmed version-only: `test_close_change.py` digest (reproduces the old value with the version line set back to 8) and the `_check_comment_evaluator_upgrade` current-version pin in `test_server_tools_lifecycle.py`; both moved to v9 with notes. The partial runs showed the guard files completing first, as AC-6 requires | `run_tests.py --no-cache`: 13673 tests, 261 files OK, receipt written |
| 2026-11-27 | Delivery lane notes repaired inline in one editorial batch after all four lanes approved (review-wave step 8): the line-of-its-own rule stated in the CHANGELOG, `mcp-tool-surface.md` and `data-and-control-flow.md` (docs-contract, architecture, code nit 4); `_schedule_order` docstring names the production `_guard_first` wrapper (architecture); `--guards --no-cache` message now asserted (code nit 1); the intended-diff half of the F1 test uses a bare `cross_platform_changed: false` so it tests F1 alone (code nit 2); a test docstring no longer claims cached timings (code nit 3). Not repaired: QA's note that 24jwf AC-3 is covered indirectly (golden digest and receipt-id change across versions; the existing upgrade path marks a different-version receipt for re-Prepare) | delivery reports in `.wavefoundry/work/24jwg/`; focused + guards 267 tests OK |
| 2026-11-27 | Delivery red-team primer repairs: F3 the alphabetical schedule-control test now includes a guard-named file and asserts it stays in name order (mutant M10 now killed); F4 the redundant missing-guard branch in `_main` is removed, because focus validation already exits 2 naming the missing file (AC-2's tests still pass); F5 `--guards --no-cache` now names `--guards` in its refusal | `.wavefoundry/work/24jwg/delivery-red-team.md` |
| 2026-11-27 | Implemented: `GUARD_TEST_FILES` (9 files: handler-digest pin, single-reader scans, censuses; `test_line_ending_census.py` left to the full run at about a minute), `--guards` expanded during parsing after the duplicate check, guard-first order at the production call site via `_guard_first`, docstring corrected; seed 180 `## Order verification by cost`, seed 209 re-verification sentences; build-and-verification and testing-architecture updated. The new guard run caught its own first defect in 5 s: a comment naming the tool-venv override variable tripped the single-reader scan. Also fixed a pre-existing parity break from the 24i2t close (gardening re-stamped `docs/references/install-log-format.md` but not the framework copy) | `run_tests.py --guards` 136 tests, 5.4 s; focused runner, seed and golden files OK; `--profile second` on touched test files OK |
| 2026-11-27 | Architecture readiness notes (implementation): rewrite the `testing-architecture.md` schedule paragraph keeping the 1tmtx alphabetical-versus-longest-first comparison as history, state production now runs `GUARD_TEST_FILES` first then alphabetical with the wall-time effect unmeasured, state `--schedule-control alphabetical` no longer matches production order exactly, and update the stale production-order comment near the default call site | `.wavefoundry/work/24jwg/readiness-architecture.md` |
| 2026-11-27 | Readiness lane repairs (one batch, cycle 1): CODE-RDY-2 removed the out-of-scope line that contradicted Requirement 3 and reworded the stale Risks row; QA and code notes scoped the stale-name check to `--guards` plus a static test, kept duplicate `--file` refusal, put guard-first at the production call site with schedule-control unchanged and made AC-6 drive the production path; docs-contract added `testing-architecture.md` and the runner test file. Implementation notes: seed 180 section goes after `## Choose evidence for the claim` and points at seed 209's fast-checks guidance; seed 209 sentences go in `### Repair re-verification`, worded "once per wave, after the last repair"; correct the `run_tests.py` docstring buffering note; rename `test_production_full_run_order_stays_alphabetical_despite_cached_timings` and keep its fixture expectation | `.wavefoundry/work/24jwg/readiness-code.md`, `readiness-qa.md`, `readiness-docs-contract.md` |
| 2026-11-27 | Readiness red-team primer: findings 1, 3, 5, 6 and 7 repaired into Requirements 1 to 6, AC-1 to AC-3, AC-6 and the Decision Log before any lane approval | `.wavefoundry/work/24jwg/readiness-red-team.md` |
| 2026-11-27 | Planned from the 24i2t process review | `.wavefoundry/work/24i2t/process-review.md`; guard set sized from `test-cache.json` durations: 19 files, longest 72.4 s |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-11-27 | Both a named `--guards` run and guard-first ordering in full runs | Readiness red-team corrected the planner's premise: per-file ok/FAIL lines already stream as files complete, so guard-first ordering surfaces a guard failure early even when nobody runs `--guards`. Efficacy: replaying 24i2t, both failing files are in the initial list, so either path shows the failure within about a minute; future pins depend on someone adding them to the list, which the comment rule and review keep visible | `--guards` only (rejected: relies on agents remembering it); streaming failure detail (rejected: not needed) |
| 2026-11-27 | Decline the per-file receipt for test-only edits | Planner default after grounding: 40 test files import other test modules (executed: `grep -l -E "^(from|import) test_[a-z_]+" tests/test_*.py`), so a sound rule needs a dependency scan and a new receipt trust rule; batching removes most of the saving | Incremental receipt with import scan (rejected for now) |
| 2026-11-27 | A curated `GUARD_TEST_FILES` list with a stated selection rule | Readiness red-team: the name rule pulled in behaviour suites (`test_run_tests_repo_guard.py`, `test_index_upgrade_guard.py`) and missed pins whose names do not say "guard"; the selection rule plus AC-2's existence check keep the list honest | Name rule (rejected: noisy and incomplete) |

## Risks

| Risk | Mitigation |
| --- | --- |
| Agents skip `--guards` | Seed guidance makes it the first verification step; the full run before close still catches everything |
| A slow file is added to the guard list | The selection rule requires seconds-scale files; revisit if the guard run exceeds about 2 minutes |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.

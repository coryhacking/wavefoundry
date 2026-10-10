# Emit compact exact qualification evidence

Change ID: `20al0-enh compact-qualification-manifest`
Change Status: `implemented`
Owner: Engineering
Status: active
Last verified: 2026-10-10
Wave: `2087n workflow-overhead-reduction`

## Rationale

Current FileResult retains verbose output but publishes only skip counts. Exact packaging checks consequently require hundreds of external captures. Expose the identities and reasons already present in executed worker output in one optional compact report.

Evidence: the recent-ten-wave audit and final cleanup are summarized in `docs/waves/2071p bounded-reconciliation-reporting/wave.md` and `docs/waves/2071n profile-skip-qualification/wave.md`. Existing unique proof and ledger citations remain available. This plan does not claim future implementation tests passed.

## Requirements

1. Add an explicit optional --qualification-report PATH to run_tests.py; ordinary runs create no new durable artifact. The report names run/profile identity, framework/test source identity, expected and observed worker files, return codes, test/skip counts, exact skipped-test IDs/reasons, and completeness. It contains no verbose transcript or copied source and is not packed.
2. Parse the last real unittest summary and corresponding skip observations conservatively; missing, duplicate, malformed or contradictory observations make qualification incomplete. Never synthesize executed identities from source decorators or allow telemetry to turn a failed worker into success.
3. Profile reports describe the actual copied/applied profile and original input identity, survive temporary-tree cleanup, and never write the source framework test receipt. Exact comparison retains the second-profile default_profile_only rule and declared-profile equality rule.
4. A cache hit cannot invent per-worker data. Reuse exact report data only when its identity matches; otherwise explicitly report unavailable executed detail and require an authorized qualifying run when that detail is needed. Preserve current green-receipt authority and backward-compatible ordinary CLI output.
5. Use one report per requested qualification run, not one file per worker. Bound serialized fields and diagnostic output, refuse linked/special output targets through existing contained I/O, and replace an owned report atomically. No upgrade invokes this release-only facility.

## Scope

**Problem statement:** Current FileResult retains verbose output but publishes only skip counts. Exact packaging checks consequently require hundreds of external captures. Expose the identities and reasons already present in executed worker output in one optional compact report.

**In scope:** the named behavior, its existing module owners, finite contract regressions and affected documentation. Canonical seeds are edited first; generated lifecycle/role surfaces are regenerated from those seeds, not patched as a substitute.

The report schema and packaging comparison share a deterministic reader. Worker identity is module plus test ID, with exact reasons, not bare counts. The existing profile selector remains authoritative. The opt-in path must be contained within the selected repository root; external output is refused. On a cache hit without a matching executed report, report availability is false and exact qualification requires an explicit uncached run. Diagnostics are capped with explicit truncation/incompleteness rather than silently losing records.

**Out of scope:** graph-query provenance wave2071o, unrelated scanner repairs, mandatory-lane removal, weakening full lifecycle gates, rewriting ledger history, release/tag/publish, new broad maintenance during consumer upgrades and product-wide refactoring. No implementation is authorized by this planning pass.

## Acceptance Criteria

- [x] AC-1: A real finite runner workload produces one compact report with exact worker/skip identities and reasons; verbose routine captures are unnecessary for comparison. Oracle: public CLI execution with passing, intentionally skipped and failing worker controls.
- [x] AC-2: Missing workers, duplicate IDs, malformed summaries, unexpected skips and changed reasons cannot pass the exact qualification comparison; legitimate second-profile default-only skips and equal declared skips pass. Oracle: executed finite report/reader controls.
- [x] AC-3: Cached or profile runs cannot claim unexecuted identities or alter the canonical receipt; matching executed report reuse is explicit. Oracle: cache/profile/receipt identity matrix.
- [x] AC-4: Optional report output is contained, bounded and atomic, ordinary runs add no files, and packaging/upgrade behavior remains opt-in. Oracle: regular/link/special/replacement output controls and existing command contracts.

## Tasks

- [x] Implement the scoped requirements in the existing owning modules and canonical instructions.
- [x] Execute the finite positive and known-bad controls named in the ACs through actual public/registered paths; record observations and limits in wave.md.
- [x] Update affected architecture and operator contracts; regenerate affected local surfaces from canonical seeds.
- [x] Run required independent delivery review and fresh framework qualification after source edits; consolidate useful long-run evidence and current handoff without routine per-seat files.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| implementation | implementer | readied wave and later operator activation | Existing module owners; no code edit during readiness. |
| focused verification | qa-reviewer | implementation | AC-scoped real controls; preserve independent judgment. |
| delivery lanes | required specialists | verified implementation | Existing selected authority, no new roster. |

## Serialization Points

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/scripts/run_tests.py`
- `.wavefoundry/framework/scripts/tests/test_run_tests_cache.py`
- `.wavefoundry/framework/scripts/tests/test_vocabulary_second_profile.py`
- `docs/prompts/package-wavefoundry.prompt.md`
- `docs/contributing/build-and-verification.md`

One implementer owns shared server_impl.py, seed190, build-and-verification and generated outputs. Qualification, memory and advisory changes settle their APIs before the compact-workflow instructions describe them. Index work may be isolated; final integration and canonical receipt run are serialized after all framework edits. Reviewer contexts do not edit source or plans.

## Affected Architecture Docs

- `docs/architecture/testing-architecture.md`
- `docs/architecture/performance-budget.md`

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | All four ACs are required: exact execution identity, negative comparison controls, receipt independence and safe optional output are the benefit and safety boundary. |
| AC-2 | required | All four ACs are required: exact execution identity, negative comparison controls, receipt independence and safe optional output are the benefit and safety boundary. |
| AC-3 | required | All four ACs are required: exact execution identity, negative comparison controls, receipt independence and safe optional output are the benefit and safety boundary. |
| AC-4 | required | All four ACs are required: exact execution identity, negative comparison controls, receipt independence and safe optional output are the benefit and safety boundary. |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-10-09 | Consolidated plan; implementation and delivery ACs remain unmet. | Current requirements and named AC oracles; operator requested create/prepare/review. |

| 2026-10-09 | Readback: Opt-in exact executed qualification report, outside framework source, survives profile cleanup and refuses unsafe/unowned outputs; ordinary runs and receipts stay compatible (AC-1–4). Update run_tests, focused runner tests and package contracts. Before: skip counts/raw transcripts; after: one bounded execution-origin report. | Operator implementation request; admitted ACs unchanged. |
| 2026-10-09 | Implemented one opt-in bounded execution-origin report, strict exact profile comparison and owned atomic cache output. Worker callbacks supply module-qualified skip IDs/reasons; the final unittest summary must agree. Profile export records original, copied and actual applied-profile identities before cleanup. Cache reuse requires exact source identity and worker inventory; unavailable detail stays incomplete. | run_tests.py; qualification_worker.py; qualification_report.py; package-wavefoundry.prompt.md. Reports restricted to .wavefoundry/cache/qualification/ outside hashed source and packed payload. |
| 2026-10-09 | Focused public runner passed 196 tests across four files; the 12 new finite controls include real pass/skip/fail workers, convincing stdout lookalikes, method/class default-only skips, second/declared comparison, canonical receipt preservation, cache identity matrix, six corrupted reader controls, unsafe outputs and atomic publication failure. Full docs validation passed. | test_qualification_report.py (12), test_run_tests_cache.py (97), test_profile_support.py (76), test_vocabulary_second_profile.py (11); 15.046s, zero failed/skipped. Captures remain temporary; full framework suite and independent delivery review are coordinator-owned and not claimed. |
| 2026-10-09 | Landing proof: 12 loosened guard mutants failed named tests. Protected path, final link and unowned output failed test_output_refuses_external_protected_unowned_links_and_special_targets; byte bound failed test_serialization_bound_refuses_without_replacing_owned_report; duplicate envelope failed test_missing_duplicate_malformed_summary_and_truncated_detail_incomplete; duplicate skip/changed reason/missing run identity failed test_known_bad_missing_duplicate_malformed_contradictory_and_reason_changed_refused; missing worker inventory failed test_missing_duplicate_or_unexpected_worker_inventory_refused_without_skips; cache source identity failed test_real_worker_ignores_lookalikes_and_cache_reuses_only_exact_detail; actual-profile provenance failed test_missing_malformed_or_wrong_profile_provenance_refused; default-only marker failed test_second_requires_executed_default_only_marker_and_declared_equality. | Mutations executed in temporary script trees, never repository source. Initial controls were strengthened when a macOS temp-root alias and a baseline skip caused rejection for unrelated reasons. Final named pins fail when their guard is removed. |
| 2026-10-09 | Added the explicit plain buffered-stdout public fixture; the module now has 13 tests. Worker capture deliberately combines stdout before stderr, retaining the real unittest terminal summary despite delayed stdout flushing. Both later 197-test public runner attempts had all four workers green, but the outer repository-state guard failed on concurrent edits to test_advisory_lint_reuse.py. | Preserve both guarded-run failures; do not call these runs green. Coordinator will run the integrated focused/full suite after all writers freeze. The earlier 196-test authoritative focused pass and finite public fixture results remain valid evidence. |
| 2026-10-09 | Evidence limits: local macOS finite qualification only; no native Windows run, full suite, pack/release or consumer upgrade execution. Report ownership is a format marker, not authentication; static link refusal is proven without claiming hostile same-user concurrent replacement immunity. | Source frozen for coordinator integration and fresh independent review; no new repository reports, receipt, closure or commit. |
| 2026-10-09 | Full integration exposed missing bytecode-entry setup in both new CLI modules. Repaired the established guarded flag/import/configure pattern; qualification workers explicitly configure read-only caching. The real CallSiteCensusTests.test_every_entry_and_library_site_follows_the_rule passed, and the 13 qualification controls passed in 11.416s. | Full suite remains red pending coordinator integration of all owned repairs; no skip, census or guard weakened. Removing either new entry's bytecode flag failed the named census with that exact module diagnostic in two temporary mutants. No py_compile or source-tree bytecode files produced. |

| 2026-10-09 | D2 captures output before test wrappers; D3 owns a non-inheritable descriptor duplicate so actual server isolation cannot repoint the protocol sink. Borrowed streams remain open; owned descriptors close on normal, discovery/runner exception and failed opening. | Actual isolation regression failed before repair. All19 report/ownership tests pass13.640s; fresh code/QA/security actual-consumer controls and old-capture/cleanup/inheritance mutants passed. Release/final quiet suite pending; wave.md and typed ledger retain final synthesis. |

| 2026-10-10 | Implementation complete; all tasks and ACs met. Required independent delivery lanes approved and current canonical qualification passed. | wave.md retains consolidated proof and limits; events.jsonl holds typed authority. Fresh source receipt bfdf8d1ecb910925f9633f3ff215385ca38110310d77faf1bc9f74114695f7af; 12,108 tests/181 files/13 skips; no closure or commit authorized. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-10-09 | Adopt the scoped approach above for readiness review. | Concrete ten-wave waste and current source owners support a bounded repair; retain quality and authority boundaries. | Selected one optional report derived from real FileResult observations. Rejected keeping hundreds of raw worker captures because it preserves avoidable noise. Rejected comparing counts or decorators alone because that can conceal substituted or unexecuted skips. |

## Risks

| Risk | Mitigation |
| --- | --- |
| Saving work conceals missing proof or stale authority. | Required negative controls, exact input identities, retained unique evidence and unchanged full gates. |
| Cross-change source ownership causes conflicting edits. | Shared-file serialization; canonical seeds first; focused independent integration review. |
| Upgrade performs unrelated maintenance. | Consumer upgrade trace and explicit no-source-suite/no-extra-evidence boundary in every applicable contract. |

## Session Handoff

Planned for readiness review only. See `docs/agents/session-handoff.md`; no code edited under this wave, no AC marked complete and no OPEN slot taken.

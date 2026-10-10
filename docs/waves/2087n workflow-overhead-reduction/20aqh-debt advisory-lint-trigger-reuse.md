# Avoid repeated advisory full-corpus lint

Change ID: `20aqh-debt advisory-lint-trigger-reuse`
Change Status: `implemented`
Owner: Engineering
Status: active
Last verified: 2026-10-10
Wave: `2087n workflow-overhead-reduction`

## Rationale

Five consecutive documentation scaffold mutations each returned full-fallback after a successful package docs gate. run_validate_incremental uses the global Git changed set; the unchanged but dirty prompt manifest repeatedly triggers full-corpus validation. Reuse proven trigger identity for advisory feedback rather than repeatedly checking the same config/corpus state. This is a measured follow-on to the prior audit; full lifecycle gates remain fresh.

Evidence: the recent-ten-wave audit and final cleanup are summarized in `docs/waves/2071p bounded-reconciliation-reporting/wave.md` and `docs/waves/2071n profile-skip-qualification/wave.md`. Existing unique proof and ledger citations remain available. This plan does not claim future implementation tests passed.

## Requirements

1. Maintain only bounded process-local identity of trigger inputs and validation rules after a genuinely completed green full validation; establish it only when those inputs are stable across the check. No new durable cache, readiness artifact or host registry.
2. When the same root and identical proven trigger/rule inputs remain dirty in Git, post-write feedback may run the existing changed-set validation without repeating full-corpus work solely for that unchanged trigger. Continue validating changed documentation and its existing dependency closure; this is advisory scoped feedback, never a whole-repository approval.
3. A new root, changed trigger, changed rules, failed/incomplete full scan, missing provenance or concurrent trigger movement requires the existing conservative full fallback. Do not accept timestamps alone as identity or share root-specific proof across repositories.
4. Keep subprocess isolation, finite timeout handling, skip/no-op visibility and honest output scope. The mode and timeout knob must describe the actual work; an error/timeout/unchecked set cannot be cached or reported clean.
5. Prepare, delivery review, close and other explicit full-validation boundaries continue using fresh run_validate; the advisory optimization must not satisfy or bypass any hard gate. Ordinary consumer upgrades gain no extra validation pass or persistent evidence.

## Scope

**Problem statement:** Five consecutive documentation scaffold mutations each returned full-fallback after a successful package docs gate. run_validate_incremental uses the global Git changed set; the unchanged but dirty prompt manifest repeatedly triggers full-corpus validation. Reuse proven trigger identity for advisory feedback rather than repeatedly checking the same config/corpus state. This is a measured follow-on to the prior audit; full lifecycle gates remain fresh.

**In scope:** the named behavior, its existing module owners, finite contract regressions and affected documentation. Canonical seeds are edited first; generated lifecycle/role surfaces are regenerated from those seeds, not patched as a substitute.

Identity includes root, content digests of every fallback trigger and lint rule, relevant workflow configuration and prompt manifest, plus command/scope semantics. Ignore Git dirtiness only for those exact proven triggers; continue validating current changed documents and dependency closure. Prefer a single bounded entry per configured root with a finite eviction cap. Recheck identity around execution; movement invalidates reuse and does not mint a baseline. No green result is cached for the changed documents. Hard-gate calls never consume this advisory state.

**Out of scope:** graph-query provenance wave2071o, unrelated scanner repairs, mandatory-lane removal, weakening full lifecycle gates, rewriting ledger history, release/tag/publish, new broad maintenance during consumer upgrades and product-wide refactoring. No implementation is authorized by this planning pass.

## Acceptance Criteria

- [x] AC-1: Repeated post-write feedback with an unchanged dirty trigger performs one full validation followed by changed-set validation, and a newly invalid changed document is still reported. Oracle: real finite dirty-repository mutation trace plus invocation counts.
- [x] AC-2: Changed trigger/rule inputs, different roots, failed scans, missing baseline and movement during full validation force conservative fallback without inheriting false-green state. Oracle: identity/failure/concurrency matrix.
- [x] AC-3: Explicit lifecycle validation remains full even after a reusable advisory baseline; output modes, skip visibility and timeouts remain truthful. Oracle: registered workflow boundaries and subprocess timeout controls.
- [x] AC-4: The optimization creates no durable sidecar or extra upgrade pass and reduces repeated advisory work on a bounded representative fixture without dropping diagnostics. Oracle: before/after invocation/time counts and filesystem/diagnostic comparisons.

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

- `.wavefoundry/framework/scripts/wf_server/server_impl.py`
- `.wavefoundry/framework/scripts/docs_lint.py`
- `.wavefoundry/framework/scripts/wave_lint_lib/cli.py`
- `.wavefoundry/framework/scripts/tests/test_server_tools.py`
- `.wavefoundry/framework/scripts/tests/test_docs_lint.py`
- `docs/contributing/build-and-verification.md`

One implementer owns shared server_impl.py, seed190, build-and-verification and generated outputs. Qualification, memory and advisory changes settle their APIs before the compact-workflow instructions describe them. Index work may be isolated; final integration and canonical receipt run are serialized after all framework edits. Reviewer contexts do not edit source or plans.

## Affected Architecture Docs

- `docs/architecture/data-and-control-flow.md`
- `docs/architecture/performance-budget.md`

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | All four ACs are required to prove actual savings, invalidation, hard-gate independence and the absence of persistent artifacts. |
| AC-2 | required | All four ACs are required to prove actual savings, invalidation, hard-gate independence and the absence of persistent artifacts. |
| AC-3 | required | All four ACs are required to prove actual savings, invalidation, hard-gate independence and the absence of persistent artifacts. |
| AC-4 | required | All four ACs are required to prove actual savings, invalidation, hard-gate independence and the absence of persistent artifacts. |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-10-09 | Consolidated plan; implementation and delivery ACs remain unmet. | Current requirements and named AC oracles; operator requested create/prepare/review. |

| 2026-10-09 | Readback: Reuse only bounded process-local stable full-fallback trigger/rule proof for advisory changed-doc lint, never hard gates (AC-1–4). Update server_impl lint seam, docs_lint/CLI, tests and contracts. Before: identical dirty config repeatedly forces full lint; after: current changed docs and dependencies checked while exact proven triggers are exempted. | Operator implementation request; admitted ACs unchanged. |

| 2026-10-09 | AC-1/2/4 implementation and bounded evidence: a genuinely completed warning-free full CLI scan establishes one exact stable proof per root; only the three canonical triggers reuse it. Current changed documents/dependencies still execute, and explicit full validation never consumes proof. Source frozen and shared server ownership returned to coordinator. | New `test_advisory_lint_reuse.py`: real Git/subprocess traces for all three triggers, new-invalid-document diagnostics, root/trigger/rule bytes/names/VERSION/seed/install/docs assets, missing/failed/incomplete/moving scans, child race, unexpected trigger, full seam, timeout/non-Git skip, finite eight-root eviction, no sidecar and equal invalid-document diagnostics. AC-3 registered lifecycle integration remains coordinator-owned. |
| 2026-10-09 | Proof identity refuses special, oversized, linked and unreadable inputs; bounds 8 MiB/file, 2,048 inputs, 64 MiB aggregate. Cached helper executing-code/source mismatch declines proof. These are advisory reuse limits, not additional hard gates. | FIFO, 9 MiB trigger, linked rule directory and unreadable inventory controls return no identity without hanging; `test_cached_helper_source_mismatch_declines_proof`. All shipped Python rules excluding tests plus source/target rule assets are conservatively bound; no timestamp-only authority. |
| 2026-10-09 | Six finite load-bearing mutants detected by named controls; no production source mutated during probes. | TMP `wf-advisory-final-controls.py`: unproven-root-proof → `test_real_dirty_trace_reuses_all_three_triggers_and_catches_new_doc`; moving-full-proof → `test_failed_incomplete_and_moving_full_scan_never_mint_proof`; unbounded-proof-cache → `test_proof_cache_has_one_entry_per_root_and_finite_eviction`; oversize-proof-input → `test_special_large_linked_and_unreadable_inputs_decline_without_hang`; target-VERSION-unbound → `test_version_and_template_seed_assets_invalidate_exact_proof`; cached-helper-source-unbound → `test_cached_helper_source_mismatch_declines_proof`. Every mutant produced an assertion failure with no test execution error. |
| 2026-10-09 | Bounded before/after work-count reduction proven; tiny-fixture wall-time improvement was not observed. No broad consumer-upgrade qualification added. | Same dirty fixture, three actual child invocations each: baseline proof-cleared calls full/full/full at 362.3/350.6/353.6 ms; reusable calls full/incremental/incremental at 360.8/384.7/384.4 ms. Conservative source identity: 234 inventoried source files, 9,476,541 bytes, mean 47.2 ms over three snapshots. Two repeated full scans avoided; subprocess count unchanged. Timings are local samples, not a large-repository or Windows performance claim. |

| 2026-10-09 | Frozen-source narrow regression run green; integration qualification and independent delivery remain coordinator-owned. | From `scripts/tests`: `PYTHONPATH=.. python3 -B -m unittest test_advisory_lint_reuse test_server_tools.PostWriteLintIncrementalTests test_server_tools.PostWriteLintIncrementalGitBehaviorTests test_compact_review_artifacts` — 33 tests passed in 21.658 s. Scoped `git diff --check` passed. |

| 2026-10-10 | Implementation complete; all tasks and ACs met. Required independent delivery lanes approved and current canonical qualification passed. | wave.md retains consolidated proof and limits; events.jsonl holds typed authority. Fresh source receipt bfdf8d1ecb910925f9633f3ff215385ca38110310d77faf1bc9f74114695f7af; 12,108 tests/181 files/13 skips; no closure or commit authorized. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-10-09 | Adopt the scoped approach above for readiness review. | Concrete ten-wave waste and current source owners support a bounded repair; retain quality and authority boundaries. | Selected bounded process-local reuse of proven trigger identity for advisory feedback only. Rejected suppressing all fallback because new config/rule changes must remain visible. Rejected persistent full-lint result caching because it adds durable artifacts and broader stale-approval risk. Initial audit deferred memoization until a concrete cause and benefit were shown; the repeated unchanged dirty-trigger fallback supplies that evidence. |

## Risks

| Risk | Mitigation |
| --- | --- |
| Saving work conceals missing proof or stale authority. | Required negative controls, exact input identities, retained unique evidence and unchanged full gates. |
| Cross-change source ownership causes conflicting edits. | Shared-file serialization; canonical seeds first; focused independent integration review. |
| Upgrade performs unrelated maintenance. | Consumer upgrade trace and explicit no-source-suite/no-extra-evidence boundary in every applicable contract. |

## Session Handoff

Planned for readiness review only. See `docs/agents/session-handoff.md`; no code edited under this wave, no AC marked complete and no OPEN slot taken.

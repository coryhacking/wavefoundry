# Fixture-fidelity independent delivery QA

Owner: Engineering
Status: active
Last verified: 2026-09-20

## Verdict and identity

Needs bounded repair before QA approval. The current helper correctly rejects unexpected Prepare blockers; its new blocker allowlist has no discriminating durable test. Deleting that guard passes the targeted refusal test and the entire 11-test fixture module. Seed 209, `Landing rule for guards`, requires a named test that fails when the guard is removed or loosened.

Reviewer: `qa-reviewer`, context `fixture-delivery-qa-fresh-20260920`. Fresh context and independent are true: this reviewer did not author the plans, implementation, readiness review or repair. Prior evidence and a lead were treated as hypotheses and independently executed. MCP `code_read`, `code_outline`, and `code_keyword` supplied current source; shell supplied Git diff, subprocess tests and local AST/token enumeration. No production or test source was edited. No lifecycle ledger was written.

The standard budget selected three probe groups: (1) canonical creation/admission/receipt/run/approval and final Prepare with omitted-run negative control; (2) refusal/restoration and the receipt-then-extra-blocker mutation; (3) declaration-token guard and public renderer transport, paired with named mutations. The review uses the admitted requirements and immutable baseline diff as independent references. Time budget: 12 minutes; targeted tests per mutant, whole module only for a survivor.

## Executed evidence

Interpreter: `/Users/coryhacking/.wavefoundry/venv/bin/python -B`; `PYTHONPATH=.wavefoundry/framework/scripts:.wavefoundry/framework/scripts/tests`.

- `python -B -m unittest test_declared_wave_fixtures test_fixture_fidelity_guidance -v`: 14 tests, zero failures/errors/skips. Valid generated fixture reaches final Prepare `ok` with no blocking diagnostics; omitted readiness run still parses, but final Prepare rejects specifically for the missing readiness Review Run Record. Producer ordering, all four restored stubs, receipt proof, explicit stubs and admitted-change requirements, and synthetic Status-only edit execute.
- `python -B -m unittest test_dashboard_server.DashboardSnapshotTests test_memory_records.MemoryProposeTests test_server_tools_lifecycle.ReviewPhaseAliasTests test_docs_lint.PrepareCouncilVerdictLintTests`: 168 tests, zero failures/errors/skips. This executes migrated consumer behavior, including misleading dashboard prose, memory decision inputs, phase aliases and typed readiness lint. Stable IDs are injected into the producer ID seam, not rewritten after creation. The dashboard malformed-projection edit now follows canonical section order. Golden files are unchanged in the baseline diff.
- The guidance tests execute the public renderer in disposable roots: fresh QA gets seed239 wording, common carriers contain the seed209 reference, source remains separately available, and changed seed plus rerender preserves existing project prose. Eight phrase deletions fail the same phrase assertions. These prove contract availability/transport, never agent adherence.
- Replayed `author-mutation-probe.py` independently; seven focused mutants produced assertion failures and zero infrastructure errors. Mutation results below.
- Current token inventory independently recomputed: 46 tokens in eight files, exactly matching declaration-census.json; 24 component, 12 declaration-check, 10 negative. Raw-line inventory also yields 46. Independent AST scanning found 45 text constants: three location differences are adjacent-literal folding, and the remaining token is a bytes literal in the historical upgrade fixture. Targeted reads reconcile all differences. Literal scope is explicit; computed declarations are not claimed statically detected. Retained test subjects and negative sites remain intentional rather than blanket malformed labels.

Logs: `/tmp/1yd24-qa-focused.log`, `/tmp/1yd24-qa-migrations.log`, `/tmp/1yd24-qa-mutations.json`, `/tmp/1yd24-qa-probe.json`. The mutation recipe is durable below even if temporary logs expire.

## Mutation table

| Mechanism | Mutation | Result / named test |
| --- | --- | --- |
| Readiness run | Replace `if readiness_run:` with `if False:` | Killed: `test_valid_fixture_and_independent_readiness_oracle` |
| Approval producer | Replace `for key in approvals:` with empty tuple | Killed: same final-Prepare test |
| Receipt proof | Disable `errors or not any(review_policy_receipt...)` branch | Killed: `test_missing_receipt_cannot_hide_behind_expected_initial_refusal` |
| Scoped restoration | ExitStack created without context exit | Killed: `test_refusals_fail_at_the_producer_and_restore_all_stubs` |
| Per-token exemption | Let any helper call exempt file | Killed: `test_unrelated_helper_or_comment_cannot_exempt_a_site` |
| F-string segments | Remove FSTRING_MIDDLE from token types | Killed: `test_classifications_and_multiline_and_fstring_literal_segments` |
| Comment adjacency | Accept comment two lines before token | Killed: `test_unrelated_helper_or_comment_cannot_exempt_a_site` |
| Prepare blocker allowlist | Delete only `or any(d["code"] != "missing_wave_council_signoff" for d in blockers)` | **NOT CAUGHT**: targeted refusal test green; all 11 module tests green |
| Guidance presence | Remove each of eight pinned phrases | Killed by `test_seed_rules_and_each_deleted_phrase_control` assertions |

The surviving guard was independently discriminated with a new safe control: instantiate `DeclaredWaveFixtureTests`, retain the real `wf_prepare_wave_response`, and patch it with a wrapper that calls the real producer first, appends `{'code': 'qa_unexpected_blocker', 'message': 'QA injected extra blocker after real receipt publication'}` to diagnostics, sets status `error`, and returns the envelope. Call `build(change_ids=[change_id], ready=True)`. Original rejects and includes the full injected message; the in-memory mutant accepts. This control uses the real receipt side effect, avoiding the existing refusal test's unrelated missing-receipt failure. All mutation edits were in-memory, using `inspect.getsource`, `compile`, and restored module bindings; repository source remained frozen.

## Finding for typed coordinator serialization

ID suggestion: `fixture-prepare-blocker-pin`. Proposition: the landed unexpected-Prepare-blocker guard lacks a durable discriminating test. Failure condition: removing only its allowlist clause leaves the claimed refusal tests green. Expected: a named durable test fails against that mutant. Observed: one targeted test and all 11 fixture-module tests pass; independent receipt-then-extra-blocker probe distinguishes original reject from mutant accept.

Recommended repair: add `test_unexpected_prepare_blocker_after_published_receipt_is_rejected`, wrapping real Prepare to retain receipt publication before appending an unexpected blocker; assert exact blocker message and all four stub identities restored, and demonstrate failure with the clause removed. Test-only bounded repair; no production behavior change is needed.

Judgment facts: validation_status=validated; scope_relation=in_scope; introduced_or_worsened_by_wave=true; contract_relevance=required_ac (1yd25 Requirement 3 plus canonical guard landing rule); supported_reachability=true (local fixture builder, real Prepare response boundary); attacker_reachability=false; authority_domain=test correctness; authority_delta=none; observable_impact=regression protection absent for newly landed refusal guard; containment=test infrastructure. Fix risk low; optional value not applicable because this is required guard evidence; repair_scope_bounded=true; repair_safety=safe; benefit_vs_fix_risk=favorable; rejection_basis=none. Disposition recommendation: do_now. Blocking required lane: qa-reviewer. This is a verification defect, not a current incorrect production refusal.

Executed finding integrity: test_ran_without_unintended_skip=true; public_path_reached=true (real Prepare and closest faithful helper boundary); boundary_values_realistic=true (real producer response/receipt with additional blocking diagnostic); assertions_non_vacuous=true; known_bad_detected=true; known_bad_detection_method=focused-mutation (durable suite survivor plus independent discriminating control). Local temporary roots/in-memory patches only; authorized local-safe review, no external effects. The positive approval claim for complete guard coverage is withheld.

## Required AC coverage and limits

| Change / AC | Assessment |
| --- | --- |
| 1yd25 AC-1 | Executed parser and dry-run properties pass |
| 1yd25 AC-2 | Real final Prepare succeeds; omitted-run control fails for exact later readiness condition |
| 1yd25 AC-3 | Per-token guard, classifications, adjacency, f-string known-bad and non-vacuity floor pass; independent inventory reconciled |
| 1yd25 AC-4 | Migrated focused consumer tests pass; full-suite receipt pending below |
| 1yd25 AC-5 | Baseline Git diff confines helper/migration changes to tests; no immutable baseline or production-module changes; sibling two seeds and QA doc are separate scope |
| 1yd96 AC-1 | Both source passages inspected, five conditions retained; current seed gate closed per tool metadata. Historical open/edit/close sequence requires coordinator session evidence |
| 1yd96 AC-2 | Eight deletion controls executed |
| 1yd96 AC-3 | Public consumer transport/preservation and explicit self-hosted wording executed; no claim of automatic existing-body replacement |
| 1yd96 AC-4 | Full docs validation is coordinator-owned evidence; full-suite receipt pending below |

No new concurrency, external trust or production lifecycle mechanism is introduced; no interleaving claim is made. Selected stateful cells cover success, missing run, producer refusal, restoration, receipt publication plus unexpected blocker, and rerender after changed seed. The existing tests do not establish future agent adherence. No additional arbitrary guard mutants beyond the bounded table were run.

## Final fingerprint and suite verification

Start and end each independently match all 16 frozen path Git blob hashes and aggregate `8452d2142d17db36e4754d7e986ce5d9b54bd33c5c20a35e1db98847fd3694f5`. At conclusion, inspected full-suite log reports 9442 tests across 117 files, 12 skips, 290.430 seconds, OK. Independently imported `run_tests` and recomputed `_hash_inputs()`: current digest and receipt both equal `40b2a3e4e53ed350da7fbab56d1b84d624c7098a588209c163cff1b6fe521f94`; receipt result `ok`, test_count 9442, ran_at `2026-09-21T04:20:53.635924+00:00`. This completes full-suite evidence for 1yd25 AC-4 and the suite part of 1yd96 AC-4 on this frozen tree. The 12 full-suite skips were outside the selected focused probes, which ran zero skips; this reviewer has not separately classified every whole-suite skip. Required overall QA approval remains withheld for the independently reproduced coverage finding. Sibling code-review mutations are not incorporated as independently verified QA findings.

## Focused repair reverification — cycle 2

Focused verdict: the six repaired guard-coverage controls now pass and the original QA blocker is resolved. This is a focused replay of `fixture-helper-guard-pins`, not a new broad review. The helper implementation is unchanged; only `test_declared_wave_fixtures.py` changed in the frozen source list. Start fingerprint verified with all path hashes: `2acf31a17f865b1ab3798eaff36c7689ea5506c11d0497243a1c5da20f1adb87`.

Read the two new tests and mutation recipe directly before executing. `test_invalid_helper_inputs_fail_before_producer_entry` rejects approvals without ready, unsupported synthetic status, and each noncallable stub before producer entry. `test_invalid_prepare_envelopes_reject_after_real_receipt_publication` calls real Prepare, proves receipt existence first, then injects unexpected blocker, unsupported status, or error without blockers; each must refuse, and all four stub bindings must restore. Its extra-message assertion specifically kills the earlier survivor rather than failing on missing receipt.

Executed `python -B -m unittest test_declared_wave_fixtures test_fixture_fidelity_guidance -v`: 16 tests, zero failures/errors/skips (1.643 seconds). Independently replayed `repair-mutation-probe.py` with the same interpreter and PYTHONPATH stated above. All six mutants are caught by assertion failure; none fails through infrastructure errors or skips:

| Mutated guard | Durable failing test | Failures / errors / skips |
| --- | --- | --- |
| Approvals require ready | `test_invalid_helper_inputs_fail_before_producer_entry` | 2 / 0 / 0 |
| Supported synthetic status | same | 2 / 0 / 0 |
| Callable stub values | same | 4 / 0 / 0 |
| Prepare status allowed set | `test_invalid_prepare_envelopes_reject_after_real_receipt_publication` | 1 / 0 / 0 |
| Prepare error requires blocker | same | 1 / 0 / 0 |
| Prepare unexpected-blocker allowlist | same | 1 / 0 / 0 |

Logs: `/tmp/1yd24-qa-repair-focused.log`, `/tmp/1yd24-qa-repair-mutations.json`; durable reproduction: `repair-mutation-probe.py`. No survivors remain in this bounded repair set. Adjacent controls include the valid final-Prepare path, missing readiness run, missing receipt, producer-order/restoration, census, and guidance transport tests in the same 16-test run.

Reverification facts: execution_status=executed; repair_execution_state=completed for this guard coverage finding; all five integrity booleans true; known_bad_detection_method=focused-mutation. Independent=true: reviewer neither authored nor implemented the repair. Context identity remains `fixture-delivery-qa-fresh-20260920`; this review retains its own initial-delivery assessment but no implementation or earlier reverification context. Fresh_context=true under seed209's definition of no retained implementation/recheck context at entry to this focused recheck; it does not mean a new process or that the original finding was forgotten. Root owns typed lane clearance and final approval bookkeeping.

Expected repair behavior is tied to Requirement 3 and seed209's guard landing rule; observed real receipt-before-refusal plus six killed mutants fulfills that property. Only disposable roots and in-memory copied function code were used; no source/ledger writes or external effects. Final full-suite receipt for the repaired tree remains pending at this focused checkpoint; the previous 9442-test receipt is stale after the two added tests and cannot establish aggregate completion.

End of focused replay: all frozen path hashes still match aggregate `2acf31a17f865b1ab3798eaff36c7689ea5506c11d0497243a1c5da20f1adb87`. Reviewer context `fixture-delivery-qa-fresh-20260920` is distinct from repairing implementer context `1yd24-guard-pin-repair`.

## Final aggregate QA approval

QA verdict: approved on the repaired frozen source. This is the receipt attestation completing the existing review and focused repair, not a new verification round. Recomputed `run_tests._hash_inputs()` equals receipt `inputs_hash`: `4decf445ea1e79f2584c875baea38b21ba8179d1aa445eb7abaa67b5107c6132`. Receipt result `ok`, count 9444, timestamp `2026-09-21T04:29:57.997599+00:00`. Independently read final log: 9444 tests across 117 files, 281.625 seconds, OK, with 12 whole-suite skips; all selected focused and mutation controls ran without skips. Recomputed every frozen source Git blob hash and aggregate: no mismatches; aggregate remains `2acf31a17f865b1ab3798eaff36c7689ea5506c11d0497243a1c5da20f1adb87`.

The six guard controls now discriminate the claimed behavior and the repaired suite receipt is current, completing the previously pending suite evidence for both admitted changes. This approval uses the same independently reviewed source and context `fixture-delivery-qa-fresh-20260920`, with the integrity and limitations recorded above. No source, ledger, commit or closure action was taken. Coordinator still owns final full-docs-validation evidence and lifecycle bookkeeping; this attestation does not assert those concurrent operations have completed.

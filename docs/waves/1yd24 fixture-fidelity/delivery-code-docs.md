# Fixture fidelity delivery code and docs review

Owner: Engineering
Status: active
Last verified: 2026-09-20

Fresh review context: fixture_delivery_code_docs. One context performed both remits; this is not two independent votes. No implementation context retained. No source edits or lifecycle writes.

Code verdict: changes requested for one bounded test-coverage finding below. Current helper behavior inspected and exercised is correct; the finding concerns missing regression controls.
Docs-contract verdict: approve the guidance changes and their stated propagation contract. Full-suite and full-docs-validation completion remain coordinator evidence, not independently claimed here.

## Scope and independent references

Reviewed the two admitted change documents, code/docs reviewer roles, seed 209 evidence protocol, all changed test/seed/local-QA diffs against baseline `8877a000`, and both new test files. MCP `code_read` provided helper/test source; shell diff and local execution supplied bounded gapfill. The codebase map names only root AGENTS for the reviewed area.

The independent reference is the admitted strict producer contract (1yd25 Requirements 1–5), interpreted directly: a published receipt must not permit an unrelated Prepare refusal, all explicit stub bindings must restore, and every literal site needs its own classification. The docs reference is 1yd96 Requirements 1–5: producer-backed setup is distinct from an independent expected-value oracle, exceptions remain available, new-role seeding differs from preservation of existing project prose. Implementer-authored mutation reports were not used as the correctness oracle. A supplied review lead about the Prepare guard was independently reproduced.

Start and end hashes of all 16 frozen source paths matched delivery-fingerprint.json; aggregate `8452d2142d17db36e4754d7e986ce5d9b54bd33c5c20a35e1db98847fd3694f5`. Production modules and immutable golden baselines were not modified in the reviewed diff. Unrelated generated drift and 1ycrj remain excluded.

## Executed evidence

Interpreter `/Users/coryhacking/.wavefoundry/venv/bin/python -B`, environment `PYTHONPATH=.wavefoundry/framework/scripts:.wavefoundry/framework/scripts/tests`.

1. `-m unittest test_declared_wave_fixtures test_fixture_fidelity_guidance -v`: 14 passing tests, zero skips; `/tmp/1yd24-code-docs-baseline.log`. This exercises canonical create/admit/Prepare/run/approval, final readiness and missing-run control, stub restoration, literal census, real rendering into disposable target roots, fresh QA guidance, and preservation of existing QA text after a changed seed.
2. `/tmp/1yd24-code-docs-probe.py`: independently executed a real Prepare, asserted its receipt exists through the real ledger reader, then appended an unexpected blocking diagnostic. Current helper rejected it with its detailed message. Removing only the unexpected-blocker guard accepted it. The existing refusal test and all 11 fixture-file tests nevertheless passed that mutant. Evidence `/tmp/1yd24-code-docs-probe.json`.
3. Same-root-cause bounded guard sweep `/tmp/1yd24-code-docs-guard-sweep.py`, results `/tmp/1yd24-code-docs-guard-sweep.json`. Targeted tests first; whole file only for survivors. All mutations were compiled in memory and patched locally; reviewed source bytes never changed.

The independent AST census counted 45 string-valued declaration sites across eight files; the recorded 46th is the intentional bytes literal in test_upgrade_wavefoundry.py. Token guard covers both, and its corpus test passed. The migration preserves parser/projection/index subjects as component fixtures and negative/diagnostic inputs as such; assertion/removal tokens are declaration checks. No blanket helper exemption was introduced.

## Mutation table

| Mechanism removed | Targeted test | Observed |
| --- | --- | --- |
| Ready requires an admitted change | test_explicit_stubs_and_admitted_change_are_required | Killed: one failure |
| Unexpected Prepare blocker rejection | test_refusals_fail_at_the_producer_and_restore_all_stubs | NOT CAUGHT; all 11 file tests pass; independent receipt-backed discriminator rejects baseline and detects mutant acceptance |
| Approvals require ready | test_explicit_stubs_and_admitted_change_are_required | NOT CAUGHT; all 11 file tests pass |
| Supported synthetic status set | test_synthetic_status_changes_only_the_status_line | NOT CAUGHT; all 11 file tests pass |
| All four supplied stubs must be callable | test_explicit_stubs_and_admitted_change_are_required | NOT CAUGHT; all 11 file tests pass |
| Prepare response status must be ok/error | test_refusals_fail_at_the_producer_and_restore_all_stubs | NOT CAUGHT; all 11 file tests pass |
| Error Prepare requires a blocking diagnostic | test_refusals_fail_at_the_producer_and_restore_all_stubs | NOT CAUGHT; all 11 file tests pass |
| Each guidance phrase deleted | test_seed_rules_and_each_deleted_phrase_control | All eight deletion controls rejected by the phrase assertions |

The last row proves availability only, not agent adherence. No whole-repository mutant runs, cross-Python tokenizer matrix, exhaustive synthetic-status mutations, or concurrency stress were performed. Scope has no production mutable mechanism change. The canonical suite is coordinator-owned and was still running during review.

## Finding F1 — strict-helper guard tests can pass for the wrong reason

Level 2; one grouped same-root-cause finding; repair is bounded to tests. The most concrete counterexample is server_tools_support.py lines 153–160 versus test_declared_wave_fixtures.py lines 114–135: the mocked unexpected Prepare refusal creates no receipt. With the unexpected-blocker guard removed, the next missing-receipt assertion still raises and includes the original message, satisfying the existing assertion. All 11 file tests stay green. The independent wrapper first lets real Prepare publish its receipt, so only the intended guard can reject the unexpected blocker; baseline rejects, mutant accepts.

The same guard-contract coverage census found five sibling guard deletions that also survive the entire new fixture test file. Minimal repair: add direct ValueError cases for approvals without ready, unsupported synthetic status, and a noncallable stub; parameterize a real-Prepare-after-receipt wrapper over unexpected blocker, unsupported response status, and error with no blocker. Assert the intended producer-stage message, then show each named mutation fails that check. Do not alter the currently correct helper or any production code.

Typed judgment facts for the coordinator: `validation_status=validated`, `scope_relation=in_scope`, `introduced_or_worsened_by_wave=true`, `contract_relevance=required_ac` (strict fixture contract and guard landing rule), `supported_reachability=true`, `attacker_reachability=false`, `authority_domain=none`, `authority_delta=none`, `observable_impact=immaterial`, `containment=detect_only`, `fix_risk=low`, `optional_value=meaningful`, `repair_scope_bounded=true`, `repair_safety=safe`, `benefit_vs_fix_risk=favorable`, `rejection_basis=none`. These are semantic facts; coordinator must use current registry enum spellings where different. Expected disposition is do_now, test-only repair plus focused independent reverification. No architecture, ownership, trust-boundary, required-AC semantics, or production protocol change is requested.

Failure condition: deletion of a newly landed strict producer guard leaves its purported coverage green. Public path: make_declared_wave calling actual lifecycle response producers, plus typed receipt reader. Expected: only allowed initial missing-readiness refusal is tolerated and named tests discriminate the enforcement. Observed: baseline enforces it, but existing tests fail to detect six guard deletions. Artifact IDs: commands/results above. Authorized local temporary roots and in-memory mutations only; no network, external effects, source mutation, commit or close.

## Docs alignment and integrity

Seed 209 remains generic, explicitly preserves malformed/component/direct-producer input subjects, says producers are not an independent correctness oracle, and requires refusal-message diagnosis. Seed 239 and the local QA body strengthen condition 2 without adding a sixth condition. The renderer test uses actual temporary-root rendering, proves canonical pointer availability and newly seeded QA wording, changes seed content before rerendering, and confirms existing prose remains intact. The prose makes no promise of automatically replacing project-owned QA bodies. No runtime/tool/validator change is hidden in this guidance diff.

For the executed finding evidence and docs approval evidence: `test_ran_without_unintended_skip=true`, `public_path_reached=true`, `boundary_values_realistic=true`, `assertions_non_vacuous=true`, `known_bad_detected=true`. Method: `focused-mutation` (real-receipt blocker discriminator for finding; individually deleted guidance phrases for docs contract-presence approval). The finding explicitly reports that the existing suite does not detect the selected mutants; known_bad_detected refers to this review's discriminating probe, not a claim that those existing pins work. Independence is fresh review against separately read admitted requirements; common-mode limits remain the real producer implementation and renderer, bounded valid fixture inputs, and presence rather than reviewer adherence.

## Focused repair reverification — cycle 2

Code verdict: approve; F1 (`fixture-helper-guard-pins`) resolved. Docs-contract verdict: approve; test-only repair does not change the reviewed guidance contract. This section supersedes the initial code changes-requested verdict above.

Reverification actor/context: fixture_delivery_code_docs. This is the original independent reviewer context, retaining its finding, and is distinct from implementer / 1yd24-guard-pin-repair. The reviewer did not implement the repair or edit reviewed sources. `fresh_context=true` means fresh relative to the repair context; it does not claim this is a newly spawned reviewer without prior review history. `independent=true` is based on separately read requirements and independent execution, not the author's mutation receipt.

Both start/end 16-path fingerprints matched `2acf31a17f865b1ab3798eaff36c7689ea5506c11d0497243a1c5da20f1adb87`. Comparison with delivery-fingerprint-initial.json confirms only test_declared_wave_fixtures.py changed. The helper, seeds and local QA body are unchanged. Read the two new tests directly through MCP and verified their assertions: invalid inputs fail before producer entry; each Prepare corruption occurs only after real Prepare published a receipt; rejection is tied to the intended producer-stage assertion; original seams restore after every failure.

Independent commands (same interpreter/environment as initial review):

- `-m unittest test_declared_wave_fixtures test_fixture_fidelity_guidance -v`: 16 tests passed, zero skips. `/tmp/1yd24-code-docs-reverify-baseline.log`.
- `/tmp/1yd24-code-docs-reverify.py`: the reviewer's original guard-deletion harness, adjusted to the two new test names and six original survivors; no author receipt used as an execution substitute. `/tmp/1yd24-code-docs-reverify.json` records all six killed by assertion failures with zero errors/skips. All failed targeted tests, so no whole-file mutant escalation was needed.

| Original survivor | New discriminating test | Result |
| --- | --- | --- |
| Unexpected Prepare blocker | test_invalid_prepare_envelopes_reject_after_real_receipt_publication | Killed, 1 assertion failure |
| Approvals without ready | test_invalid_helper_inputs_fail_before_producer_entry | Killed, 2 assertion failures |
| Unsupported synthetic status | test_invalid_helper_inputs_fail_before_producer_entry | Killed, 2 assertion failures |
| Noncallable stub | test_invalid_helper_inputs_fail_before_producer_entry | Killed, 4 assertion failures |
| Unsupported Prepare status | test_invalid_prepare_envelopes_reject_after_real_receipt_publication | Killed, 1 assertion failure |
| Error Prepare without blocker | test_invalid_prepare_envelopes_reject_after_real_receipt_publication | Killed, 1 assertion failure |

Observed: all six previously surviving mutations now fail named tests; baseline fixture/readiness/census and guidance/rendering behavior remains green. Minimal test-only repair closes the finding with no helper behavior change. Adjacent checks cover pre-producer rejection, retained receipt proof, failure-stage diagnostics, and scoped seam restoration. No additional finding arose in this focused scope.

Reverification integrity: `test_ran_without_unintended_skip=true`, `public_path_reached=true`, `boundary_values_realistic=true`, `assertions_non_vacuous=true`, `known_bad_detected=true`, `known_bad_detection_method=focused-mutation`. Invalid input/envelope controls intentionally exercise failure contracts; baseline uses real lifecycle producers and real published receipt state. Local disposable roots and in-memory mutants only; no source modification or external effects. Full-suite and docs-validation claims remain coordinator-owned; original cross-Python/adherence limitations remain. No full-council trigger was introduced by the repair.

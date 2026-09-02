# Evaluator-Only Edits Record No Close-Time Baseline

Change ID: `1wybq-enh evaluator-edit-baseline-policy`
Change Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-09-01
Wave: 1wybs review-churn-follow-ups

## Rationale

`1wujt` edited `retrieval_eval.py`, which moved `evaluator_identity` (the
evaluator binds its own module bytes, kept at whole-module granularity by
readiness decision RT-RDY-4), so the standing `1wur7` receipt no longer bound
and `docs/contributing/review-and-evals.md` ("land the change, index, then
record a fresh baseline before the gate judges anything") obliged the wave to
record a fresh baseline at close. That run cost the close a quiet-machine
window and three invalidated attempts (the index generation moved under the
run each time) while retrieval quality was unchanged by construction: `1wujt`
edited no production retrieval module, so `production_identity` (`2cb07c8f`
on the recorded receipt) could not have moved, and every metric was identical
to the `1wur7` receipt. A baseline recorded by the evaluator-editing wave
proves nothing that the next ranking wave's own before-receipt would not prove
better, because the before-receipt is recorded with the evaluator that will
judge the comparison. The obligation belongs to the wave that changes
production retrieval bytes, not to the wave that changes the evaluator. The
operator raised this at the `1wuju` close and it was recorded as a follow-up.

## Requirements

1. `docs/contributing/review-and-evals.md` SHALL replace the sentence "land the change, index, then record a fresh baseline before the gate judges anything" and the later sentence "The next ranking change records its own single-run baseline the same way after any evaluator edit" with one rule: an edit that moves `evaluator_identity` without moving `production_identity` records no baseline at its close; the standing baseline becomes incomparable and stays so; the next wave that changes production retrieval bytes records a before-receipt on its pre-change tree with the current evaluator (before its first production edit, or on a checkout of the pre-change tree with the index rebuilt) and an after-receipt on its delivered tree, and compares the two. The rule SHALL state that in this repository the pair is a `cross_generation` comparison, because every production retrieval module is indexed (`.wavefoundry/framework/scripts` is under `project_include_prefixes.code`), the evaluator's preflight refuses a stale index, and every completed build advances the generation; `production_change_same_generation` is reachable only when production bytes change with no indexed file changing. It SHALL name the sequencing that avoids a mid-run rebuild (index current first, the `reindex-pending` marker kept fresh, a foreground run, no other session mutating the tree), as recorded in `1wujt`'s Progress Log. It SHALL state that a `cross_generation` comparison attributes corpus drift to the change because the regression rule has no tolerance, that a `fail` is read together with the production diff between the two receipts' identity blocks (drift when the diff reaches no retrieval tool, the change's regression when it does), and that a drift-free same-generation pair is a recorded follow-up because `production_scripts_dir` is identity-only (delivery review: the receipt this wave recorded under ARCH-DEL-1 was exactly that case).
2. The same document's **Standing artifact** paragraph SHALL name the current reference receipt, state that after an evaluator edit there is none until the next ranking wave records its before-receipt, and state that an `invalid_baseline` refusal in that window, typically "baseline evaluator identity differs", is the expected signal, not a defect.
3. `docs/architecture/testing-architecture.md` SHALL carry the rule in one sentence beside its reproducibility paragraph, consistent with the contributing document, and its standing-evaluation row (row 38) SHALL say that the `--baseline` receipt it names is the reference only until the next evaluator edit.
4. Both policy sentences SHALL be pinned by `assertIn` tests in `test_docs_lint.py`: the `testing-architecture.md` pin sits beside that document's existing prose pins; the `review-and-evals.md` pin is the first prose pin on that document.
5. `CHANGELOG.md` `## [Unreleased]` SHALL announce the policy, and the existing `1wur7` bullet in the same section, whose tail reads "so the discontinuity is deliberate: land, index, then record a fresh baseline", SHALL be corrected to the new rule so the section states one policy; a pin asserts the retired phrase is absent from the Unreleased section.

## Scope

**Problem statement:** The standing-gate documentation obliges the wave that edits the evaluator to record a close-time baseline that measures nothing the evaluator edit could have changed, and offers a comparison kind the next ranking wave cannot reach in this repository.

**In scope:**

- The policy text in `docs/contributing/review-and-evals.md` and `docs/architecture/testing-architecture.md`.
- The pins, the new CHANGELOG bullet, and the corrected `1wur7` CHANGELOG bullet.

**Out of scope:**

- Any edit to `retrieval_eval.py` or to `benchmarks/compare_retrieval_receipts.py`. An evaluator edit moves `evaluator_identity`, and a message improvement is not worth the discontinuity; the refusal text stays as it is.
- Identity granularity (RT-RDY-4 stands: whole-module byte binding).
- Recording any receipt in this wave. No change in this wave touches production retrieval bytes or the evaluator.

## Acceptance Criteria

- [x] AC-1: `docs/contributing/review-and-evals.md` states the rule (an evaluator-only edit records no close-time baseline; the next ranking wave records a before-receipt with the current evaluator and an after-receipt, and compares them as `cross_generation` in this repository, reading a `fail` together with the production diff because the comparison attributes corpus drift to the change), no longer instructs the evaluator-editing wave to record a fresh baseline, and no longer says the next ranking change records "its own single-run baseline the same way"; pinned by an `assertIn` test that fails when the sentence is removed.
- [x] AC-2: `docs/architecture/testing-architecture.md` carries the one-sentence rule and its row 38 qualifies the named `--baseline` receipt; pinned the same way.
- [x] AC-3: The **Standing artifact** paragraph names the current reference receipt and the post-evaluator-edit state with the expected refusal, the new CHANGELOG bullet is present, the `1wur7` bullet no longer says "record a fresh baseline" (pinned by an `assertNotIn` on the Unreleased section), and `wf_validate_docs` passes on the edited documents.
- [x] AC-4: The tests this change adds pass, the documents this change authors or edits validate, and no failure elsewhere is attributable to this change.

## Tasks

- [x] Rewrite the discontinuity paragraph, the trailing "same way" sentence, and the **Standing artifact** paragraph in `docs/contributing/review-and-evals.md`.
- [x] Add the one-sentence rule to `docs/architecture/testing-architecture.md` and qualify row 38's `--baseline` receipt.
- [x] Add the pins in `test_docs_lint.py` (two `assertIn`, one `assertNotIn` on the Unreleased section).
- [x] CHANGELOG: new bullet; correct the `1wur7` bullet's tail; `wf_validate_docs`.
- [x] Record the mutant table in this Progress Log: each sentence deleted in a scratch copy fails its pin; the retired phrase restored in the CHANGELOG fails the `assertNotIn`.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Policy text | implementer | — | Two documents plus the CHANGELOG |
| Pins | implementer | Policy text | Mutant table before review |


## Serialization Points

- `docs/contributing/review-and-evals.md`, `docs/architecture/testing-architecture.md`
- `.wavefoundry/framework/scripts/tests/test_docs_lint.py`
- The root `CHANGELOG.md` Unreleased section (a root-level file cannot be declared as a path; it is named here in prose).

## Affected Architecture Docs

- `docs/architecture/testing-architecture.md` (the standing retrieval gate's baseline rule).

## AC Priority


| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | The contributing document is the contract the next ranking wave reads. |
| AC-2 | required | The architecture document must not contradict it. |
| AC-3 | important | The reference receipt, the expected refusal, and one CHANGELOG policy are what an operator looks for first. |
| AC-4 | required | The change's own evidence. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-09-02 | Delivery round 1 repair, policy disclosure from ARCH-DEL-1's receipt: the after-receipt this wave recorded (`docs/reports/retrieval-quality-post-1wybs.json`, run `2691fb86`, `cross_generation` 174 to 211, evaluator `aa5a57e4` on both sides) returned `fail` on five zero-tolerance `quality_regression` violations on `code_ask` holdout (aggregate nDCG@10 0.5270 to 0.5232 and agentic MRR@10 0.3936 to 0.3900; `agentic_fix_localization` nDCG 0.1993 to 0.1981 and MRR; `assessment_boundary_control` nDCG 0.7309 to 0.6764) while nine case metrics moved in both directions, two of them on `code_search`, and the production diff, reconstructed byte-exactly against the `1wuju` receipt's digest `2cb07c8f`, touches only `_docs_lint_verdict_gap_error`, `_strip_repository_root`, `_repo_rel`'s neighbour `_install_artifact_display`, and `wf_audit_install_response`, none reachable from a retrieval tool. The contributing document, the architecture sentence, and the CHANGELOG bullet now disclose that a cross-generation comparison attributes corpus drift to the change and how to read a `fail`; pinned (`EvaluatorEditBaselinePolicyPinTests`). Follow-up recorded for the operator: `production_scripts_dir` is identity-only, so a drift-free same-generation pair is unreachable until the evaluator loads the modules it hashes. | `baseline_1wybs_1.log`; `recon_vs_current.diff` and the digest match in the session scratchpad; `retrieval_eval._quality_comparison`. |
| 2026-09-02 | Delivery round 1: no finding against this change. The primer and three lanes verified the policy mechanism by reading `run_evaluation`'s preflight, `docs_health`'s `semantic_ready`, `project_include_prefixes.code`, and both generation-advancing completion paths (`finalize_build_epoch` and `finalize_staged_build_epoch`; the former's docstring claims sole ownership and is stale, pre-existing, `index_state_store.py` untouched), and confirmed the retired obligation survives nowhere outside the pins' `assertNotIn` strings and wave records. The first application of the policy is this wave itself (ARCH-DEL-1 in `1wybr`): `server_impl.py` is a production module, so the wave records an after-receipt against the `1wuju` receipt as `cross_generation`. Noted by the primer: the three pins are exact-phrase pins, so a paraphrased reversal would pass (inherent to `assertIn`). | Delivery lane reports (architecture, docs-contract, code); `mut15_run.log`. |
| 2026-09-01 | Landing rule: three scratch-copy mutants under session scratch `mut15`, each caught on an otherwise green base: the contributing sentence deleted (`test_the_contributing_document_states_the_rule`); the retired phrase restored in the CHANGELOG (`test_the_unreleased_changelog_states_one_policy`); the architecture sentence deleted (`test_the_architecture_document_agrees`). | `mut15_run.log`: 16 of 16 caught across the wave. |
| 2026-09-01 | Implemented. `docs/contributing/review-and-evals.md`: the discontinuity paragraph now states that an evaluator-only edit records no close-time baseline, that the next wave changing production retrieval bytes records a before-receipt with the current evaluator and an after-receipt, that the pair is `cross_generation` in this repository (production modules indexed, preflight refuses a stale index, a completed build advances the generation), and the collision-avoiding sequencing; the trailing "same way" sentence is gone; the Standing artifact paragraph names the reference receipt, the post-evaluator-edit window, and the expected `invalid_baseline` refusal. `docs/architecture/testing-architecture.md`: one-sentence rule beside the reproducibility paragraph and row 38's `--baseline` receipt qualified. CHANGELOG: new Changed bullet; the `1wur7` bullet's tail no longer says "record a fresh baseline". Pins: `EvaluatorEditBaselinePolicyPinTests` in `test_docs_lint.py` (two `assertIn` pins and the `assertNotIn` on the Unreleased section; the contributing-document pin is the first prose pin on that file). No evaluator or production module was touched. Gapfill: docs-only work applied as exact-string replacements with the shell; the mechanism claims behind the sentences were verified by the readiness seats through MCP reads of `retrieval_eval.run_evaluation`, `docs_health`, and the state store. | `1wybs_targeted_1.log` (199 OK); `wf_validate_docs` green. |
| 2026-09-01 | Readiness council amendments applied (RT-RDY-2, RT-RDY-3, RT-RDY-10, DOCS-RDY-4 to DOCS-RDY-7): the `1wur7` CHANGELOG bullet is corrected in the same change; the pair is stated as `cross_generation` with the preflight and generation mechanism (production modules are indexed; `stale_index` refuses; a completed build advances the generation); the trailing "same way" sentence is replaced too; the refusal is "typically" the identity one; row 38's receipt is qualified; the `review-and-evals.md` pin is new. | Readiness council checkpoint in `wave.md`; `retrieval_eval.run_evaluation` preflight; `docs_health` `semantic_ready`; `index_state_store` generation increment. |
| 2026-09-01 | Drafted from the `1wuju` close: the baseline run was needed only because the evaluator changed, and the metrics were identical to the `1wur7` receipt on the same fixture digest. | `docs/reports/retrieval-quality-post-1wuju.json` (run `60eed88e`); `1wujt` Progress Log baseline row; `docs/contributing/review-and-evals.md` lines 253 to 270. |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-09-01 | Policy only: the next ranking wave records its own before-receipt and after-receipt, compared as `cross_generation`. | The before-receipt is recorded with the evaluator that judges the comparison, so it is the stronger reference; an evaluator-editing wave has nothing to measure; and the same-generation kind is unreachable for a production-module edit in this repository, so naming it as the primary case would send the next wave after a comparison the preflight forbids. | **Finer evaluator identity (hash only the scoring and comparison functions):** reverses RT-RDY-4, and deciding which lines count as scoring is a judgment the receipt cannot defend. **Automate the close-time baseline inside `wf_close_wave`:** close would need a quiet machine and a frozen index for five minutes, which is the cost the retro named. |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| A ranking wave forgets its before-receipt. | The evaluator refuses a cross-identity comparison, so the omission cannot be silent; the contributing document names the before-receipt as the wave's first evidence step. |
| The before-receipt is recorded on a tree that already carries production edits. | The rule says before the first production edit, or on a checkout of the pre-change tree with the index rebuilt, as wave `1seaw` did. |
| The before-receipt and after-receipt collide with a mid-run rebuild, as `1wuju`'s three invalidated attempts did. | The rule names the sequencing: index current, `reindex-pending` kept fresh, foreground run, no other session mutating the tree. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.

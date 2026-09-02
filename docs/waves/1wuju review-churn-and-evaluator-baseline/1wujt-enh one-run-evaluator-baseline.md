# One-Run Evaluator Baseline

Change ID: `1wujt-enh one-run-evaluator-baseline`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-09-01
Wave: 1wuju review-churn-and-evaluator-baseline

## Rationale

A standing retrieval baseline currently needs two evaluator runs on one frozen
index, because the run-to-run shift is the only jitter estimate the gate has.
Each run takes minutes with the reranker on CPU. `1wur7` recorded a quiet pair
on generation 53, lost it to the evaluator's own identity binding when later
repair rounds edited the module, and then recorded two more pairs on a shared
machine, both contended. With latency advisory for every comparison kind
(operator decision at the `1wur7` close), the pair-derived jitter only sizes an
advisory band, and on every quiet pair on file that band is the 25% floor
anyway (`max(0.25, 3 x jitter)` with jitter at or below 1.7%). A single receipt
can therefore stand as a baseline at the floor. The readiness council tested
the tempting alternative, a within-run estimate from the three repetitions each
case already records, against the committed fixture and refuted it: robust
floor and median statistics cannot see contention from inside one run, and
`code_ask` has 12% to 27% intrinsic per-call spread on a quiet machine, so any
within-run estimator misjudges contention in both directions. This change
ships the one-run baseline without an estimator and records that refutation.

## Requirements

1. A receipt that carries no pair-derived `jitter_ratio` SHALL be accepted as a baseline. The single-run branch of `apply_baseline_comparison` sets `permitted_relative_regression` to the existing 0.25 floor explicitly, records `jitter_source: "single_run_floor"`, sets `pair_contended` to `null` with `contention_judged: false` and the reason "a single run has no reference level", and inherits nothing else. The `invalid_baseline` refusal "baseline lacks same-generation jitter" becomes acceptance; this is a disclosed loosening of baseline VALIDITY and of nothing else (no retrieval-quality floor and no response-size ceiling moves).
2. The pair path SHALL remain available and SHALL be preferred when a pair-derived `jitter_ratio` is present, unchanged in behaviour.
3. No within-run jitter estimator SHALL be shipped. The readiness council's replay of `.wavefoundry/framework/scripts/tests/fixtures/retrieval_eval/warm_sample_pairs.json` (three estimators: repetition-index pseudo-arms, per-case relative range, half-corpus split) found none that separates the quiet pairs from the contended pair at `PAIR_JITTER_THRESHOLD`, and any per-tool threshold that appears to would be fitted to one contended run; the Decision Log records the table, and a test pins that the single-run branch computes no such ratio and judges no contention.
4. The standing-baseline procedure in `docs/contributing/review-and-evals.md`, `docs/architecture/testing-architecture.md`, and `CHANGELOG.md` SHALL describe the one-run flow as the default and the pair as optional, and every sentence the readiness docs-contract seat listed as becoming false SHALL be corrected (they are enumerated in the Progress Log). The quiet-machine obligation moves into the operator procedure: record a baseline when nothing else is running, because a single run cannot detect its own contention.
5. Evaluator identity keeps whole-module byte binding (`_evaluator_identity` over the module's own bytes); decided at readiness (RT-RDY-4) and recorded in the Decision Log. A declared contract version would make a body change inside a listed function comparable without a bump, which an enumeration test cannot see; the one-run baseline is what makes whole-module binding affordable.

## Scope

**Problem statement:** A baseline costs two runs on a quiet machine while the band it would size is the 25% floor on every quiet pair on file; one receipt can stand as a baseline at that floor, and contention is left to the operator procedure because a single run cannot detect it.

**In scope:**

- `retrieval_eval.py` comparison path: the single-run baseline branch and its recorded fields.
- Tests including deletion pins for the new branch and a pin that no within-run ratio is computed.
- The contributing, architecture, and CHANGELOG passages describing the baseline procedure.

**Out of scope:**

- Any change to retrieval-quality metrics, floors, or the golden corpus.
- The reranker's execution provider or its latency.
- Removing the pair path.
- A within-run jitter estimator (refuted at readiness; see Requirement 3).

## Acceptance Criteria

- [x] AC-1: A comparison against a single-run baseline succeeds with `permitted_relative_regression` 0.25, `jitter_source: single_run_floor`, `pair_contended: null`, and `contention_judged: false` with its reason, on both comparison kinds that inherit a band; deleting the branch restores the refusal and fails a named test.
- [x] AC-2: A baseline carrying a pair-derived `jitter_ratio` is still preferred and its band is unchanged, pinned by the recorded fixture pairs; and the single-run branch computes no within-run ratio, pinned by a test that fails if one is written.
- [x] AC-3: The sentences in `review-and-evals.md`, `testing-architecture.md`, and `CHANGELOG.md` that the readiness docs-contract seat listed are corrected, and the procedure describes the one-run default, the optional pair, and the quiet-machine obligation.
- [x] AC-4: The tests this change adds pass, the documents this change authors or edits validate, and no failure elsewhere is attributable to this change.

## Tasks

- [x] Add the single-run baseline branch to the comparison with its recorded fields and the explicit 0.25 band.
- [x] Pin the branch by deletion, pin the pair preference on the recorded fixture pairs, and pin the absence of a within-run ratio.
- [x] Correct the listed sentences and restate the procedure in the three documents.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Single-run baseline | implementer | — | Pair path preferred when present; band is the explicit floor |
| Evidence and docs | implementer | Single-run baseline | Recorded fixtures, no synthetic scores |


## Serialization Points

- `.wavefoundry/framework/scripts/retrieval_eval.py`, `.wavefoundry/framework/scripts/tests/test_retrieval_eval.py`, `.wavefoundry/framework/scripts/tests/fixtures/retrieval_eval/warm_sample_pairs.json`
- `docs/contributing/review-and-evals.md`, `docs/architecture/testing-architecture.md`
- The root `CHANGELOG.md` Unreleased section (a root-level file cannot be declared as a path; it is named here in prose).

## Affected Architecture Docs

- `docs/architecture/testing-architecture.md` (standing evaluation row, the reproducibility paragraph, and the reported-statistics sentence)

## AC Priority


| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | The one-run baseline is the outcome the change exists for. |
| AC-2 | required | The pair path must not regress and the refuted estimator must not creep back in. |
| AC-3 | required | The listed sentences become false, not incomplete, once the code lands (readiness DOCS-RDY-9). |
| AC-4 | required | The replacement shape, applied to itself. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-09-01 | AC on the change's own evidence, the replacement shape applied to itself: the tests this change adds pass, the documents it authors or edits validate (`wf_validate_docs` green), and the coordinator's full run on the implemented tree shows no failure elsewhere (8,026 tests across 69 files, all green, receipt `ok`). | `full_suite_1wuju2.log` in session scratch; `.wavefoundry/framework/test-cache.json` 8,026 ok. |
| 2026-09-01 | Implemented. `apply_baseline_comparison` gained a third branch: a baseline with no numeric `jitter_ratio` is accepted with `jitter_source: single_run_floor`, `jitter_ratio: null`, `pair_contended: null`, `contention_judged: false`, and the reason "a single run has no reference level"; the band is the existing 0.25 floor. The pair branch is unchanged and taken whenever a numeric `jitter_ratio` is present. Landing rule applied: three scratch-copy mutants each fail a named test (restoring the refusal fails `test_single_run_baseline_is_accepted_at_the_floor` on both kinds; writing a `within_run_jitter_ratio` fails its `assertNotIn`; ignoring pair-derived jitter fails `test_a_recorded_pair_is_preferred_over_the_single_run_floor` on the recorded quiet pair). The legacy pin `test_same_generation_production_change_is_a_receipt_not_a_jitter_pair` asserted the refusal this change removes and now asserts the floor acceptance. Docs: the seven listed sentences in `review-and-evals.md`, `testing-architecture.md`, and the CHANGELOG corrected; the standing baseline is named as `docs/reports/retrieval-quality-post-1wuju.json`, a single run to be recorded at the close on a quiet machine. | `test_retrieval_eval.py` 61 OK; scratch mutants under session scratch `mut8`; `wf_validate_docs` after the docs edits. |
| 2026-09-01 | Readiness amendments adopted (RT-RDY-1 through RT-RDY-4, DOCS-RDY-7 through DOCS-RDY-9): the within-run estimator was refuted on the fixture and dropped; the single-run baseline stands at the explicit 0.25 floor with contention not judged; whole-module identity binding is kept; AC-3 lost its always-satisfiable escape clause; the docs AC is required. Sentences to correct (docs-contract seat): in `review-and-evals.md` the `comparison_kind` sentence ("is the only pair that measures jitter"), the `jitter_components` sentence, the inherited-contended recovery wording, the discontinuity paragraph ("record a fresh same_generation_pair before the gate judges anything"), and the standing-artifact paragraph including "Both are committed with wave 1wur7"; in `testing-architecture.md` the standing-evaluation row's baseline pointer and command, the reproducibility paragraph, and the `jitter_components` sentence; in `CHANGELOG.md` the discontinuity bullet ("then record a fresh same_generation_pair") and the inherited-contended sentence. | Readiness council reports; the refutation table in the Decision Log. |
| 2026-09-01 | Delivery round 1 (DOCS-DEL-1): census re-derived. Readiness listed ten sentences, not seven: seven were corrected in the implementation row above; three stand unchanged because the pair path they describe is unchanged and each is still true (the `jitter_components` sentence and the inherited-contended recovery wording in `review-and-evals.md`, and the inherited-contended sentence in the CHANGELOG). The standing-baseline pointer in `testing-architecture.md` now says the receipt is recorded at the close and absent until then. ARCH-DEL-2: the data-level disclosure tool mirrors the single-run floor (`jitter_source: single_run_floor`, band 0.25) instead of skipping, pinned by `test_the_disclosure_tool_mirrors_the_single_run_floor`. QA-DEL-1: the boolean `jitter_ratio` guard is pinned by `test_a_boolean_jitter_ratio_is_not_a_reference_level`. | `test_retrieval_eval.py` (targeted); docs-lint. |
| 2026-09-01 | Landing rule, delivery round 1: two scratch-copy mutants under `mut10`, each caught: the boolean guard removed from the pair-branch condition (`test_a_boolean_jitter_ratio_is_not_a_reference_level`); the disclosure tool's single-run branch reverted to the skipped entry (`test_the_disclosure_tool_mirrors_the_single_run_floor`). | `mut10_run.py` log. |
| 2026-09-01 | Delivery round 2 (DOCS-DEL-2, low): `review-and-evals.md` names the standing baseline with the same "absent until then" qualifier as the architecture row. | docs-lint. |
| 2026-09-01 | Standing baseline recorded at close: `docs/reports/retrieval-quality-post-1wuju.json` (run `60eed88e`, evaluator identity `aa5a57e4` = the delivered module, production `2cb07c8f`, index generation 174 at start and end, verdict `baseline`, zero violations, zero operator-review reasons, `jitter_ratio` null on every tool as a single run). Retrieval quality is unchanged against the `1wur7` receipt on the same fixture digest `bda67546`: identical recall@10 and nDCG@10 on every holdout split (`code_ask` 0.594 / 0.527, `code_lexical` 0.75 / 0.608, `code_search` 0.833 / 0.642, `docs_search` 0.0 / 0.0 on its single holdout case), as expected for a wave that touched no retrieval code. Three earlier attempts were invalidated (`index_not_ready` twice, `stale_index` once): the context-efficiency projection writes into the open wave's record whenever its telemetry settles, that edit makes the index stale, and the staleness monitor rebuilds five minutes later, so a five-minute run collided every time; the signed run was made in the foreground with the index brought current first and the `reindex-pending` marker kept fresh so the monitor deferred. Follow-up (not this wave): evaluator-only edits should not require a close-time re-baseline; the next ranking change can record its own before-receipt on the pre-change tree. | `baseline_1wuju_6.log`; receipt sha256 `6c772165543e1746`. |
| 2026-09-01 | Drafted from the `1wur7` retrospective: a quiet pair lost to the evaluator's identity binding, then two contended pairs on a shared machine; the operator questioned the two-run design and made latency advisory at close. | `1wuuh` Progress Log; `docs/reports/retrieval-quality-post-1wur7*.json`. |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-09-01 | No within-run jitter estimator (RT-RDY-1). Replay of the committed fixture with the evaluator's own helpers, three estimators (A: repetition-index pseudo-arms; B: per-case relative range, median across cases; C: half-corpus split), threshold 0.05: contended `code_search` PAIR 0.181 but A 0.020/0.025, B 0.024/0.022; contended `docs_search` PAIR 0.208 but A 0.017/0.017, B 0.017/0.021; contended `code_ask` PAIR 0.250, A 0.258/0.151, B 0.179/0.149; quiet `1seaw` `code_ask` PAIR 0.017 but A 0.257/0.266, B 0.196/0.196; quiet `before-1seas` `code_ask` PAIR 0.009 but A 0.125/0.130, B 0.198/0.196; quiet `code_search` and `docs_search` at or below 0.014 under every estimator. No estimator separates: A and B miss two of four contended tools and flag every quiet `code_ask` run; C compares different fixtures. A per-tool threshold near 0.012 would be fitted to one contended run. | Robust floor and median statistics are blind to a load that lifts a minority of cases or the whole run uniformly when seen from inside one run; `code_ask` carries 12% to 27% intrinsic per-call spread. | **Ship the estimator with per-tool thresholds:** K fitted to fixture labels, which the operator's rule forbids. **Ship it informational only:** records a number that would be read as a judgement. |
| 2026-09-01 | Keep whole-module byte binding for `evaluator_identity` (RT-RDY-4). | A declared measurement-contract version pinned by a function enumeration cannot see a body change inside a listed function, so a stale baseline would become comparable without a bump; the one-run baseline makes whole-module binding affordable. | **Contract version:** loosens identity in exactly the case that matters. |
| 2026-09-01 | Keep the pair path and prefer it when present. | A pair still measures true run-to-run shift; the one-run estimate is a floor for the common case, not a replacement for evidence that exists. | **Remove the pair path:** loses information the framework already knows how to record. |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| A single-run baseline recorded under load is accepted with no signal. | Contention is recorded as not judged rather than as absent; the procedure requires a quiet machine; the pair path remains for evidence-grade comparisons. |
| The refuted estimator creeps back in later as a convenience. | AC-2 pins that the single-run branch computes no within-run ratio, and the Decision Log carries the refutation table. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.

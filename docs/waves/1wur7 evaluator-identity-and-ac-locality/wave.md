# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-09-08
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1wur7 evaluator-identity-and-ac-locality`
Title: Evaluator Identity And Ac Locality

## Objective

Repair three self-correctness defects that wave `1wpif`'s reviews exposed in the framework's own verification machinery: the standing retrieval evaluator binds the sqlite store file inode, so its own `cross_generation` comparison cannot survive the controlled rebuild it exists for; it estimates run-to-run jitter from a single near-max sample, so it cannot tell a quiet pair from a contended one and promoted a contended pair as evidence; and several hundred change documents carry an acceptance criterion asserting whole-repository state (the delivered rule finds eight in non-closed waves and five in parked plans; the readiness-time figures of 297 and then 317 were both withdrawn as mis-scanned, and the total across closed archives is scan-dependent and not load-bearing), so a finished change can be unattestable because a concurrent wave's edit is red. Each defect misled a real delivery judgment during `1wpif`, so the machinery is repaired before the next wave leans on it.

## Changes

Change ID: `1wtpl-bug retrieval-eval-store-identity-binding`
Change Status: `implemented`

Change ID: `1wuuh-bug retrieval-eval-jitter-estimator-and-sample-floor`
Change Status: `implemented`

Change ID: `1wuui-enh acceptance-criteria-locality-and-gate-scope`
Change Status: `implemented`

## Participants

- Coordinator: coordinator
- Write-owning roles: implementer
- Requested review lanes: none
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer, release-reviewer
- Product-owner admission review: operator-approved on 2026-08-31 by the request to put these three follow-ups into a wave and take them through prepare, implement, and review; the changes alter verification machinery and AC-authoring guidance, not product behavior.

Completed At: 2026-09-01

## Wave Summary

Wave `1wur7 evaluator-identity-and-ac-locality` (Evaluator Identity And Ac Locality) delivered 3 changes: Retrieval Evaluator Binds the Store File Inode Instead of the Store Identity, Retrieval Evaluator Estimates Pair Jitter From One Order Statistic, and Acceptance Criteria Assert What the Change Controls. Notable adjustments during implementation: Acceptance Criteria Assert What the Change Controls: Implemented. Seed `170` gained *"Acceptance criteria assert what the change controls"* with the worked before/after example, and `docs/prompts/plan-feature.prompt.md` was hand-reconciled. `_check_ac_asserts_repository_state` was added beside the three existing AC validators and wired at the same call site inside the wave-owned change-doc loop, so `_wave_requires_wave_owned_change_docs` scopes it. Polarity: BLOCKING error, matching its siblings. `wf_close_wave` gained `_framework_test_receipt_status`, which reuses `run_tests.py`'s own `_hash_inputs` (loaded from the target root's copy, both import side effects restored) and never runs a suite or spawns a subprocess.; Acceptance Criteria Assert What the Change Controls: Round-5 reverification, five independent lanes against the settled tree. Release, docs-contract, and architecture reported first: DOCS-DEL-2 repaired from every stance that has reported, DOCS-DEL-1 repaired, REL-DEL-6 repaired (a fresh clone without the two paths fails `test_retrieval_eval.py` at import; with exactly them it is 59 green). Repaired here where a mechanism was concerned: (a) `_ac_bullet_lines` now folds a loose-list continuation paragraph (blank line, then indented text) into its bullet, the wrapped-bullet hole in a different costume, pinned by `test_loose_list_continuation_paragraph_is_inspected_whole`; (b) the carve-out search runs on a copy with code spans blanked, so a marker such as a backticked `must not` is quoting, not applying, pinned by a matrix row, and the straight and curly double-quote span branches, which the code lane's sweep found survived deletion (M15b), each gained a matrix row with the coverage floor extended to the three span delimiters; (c) the sensor message says "a gate concern, not an acceptance criterion" rather than "close-gate", because a pack-vendored repository has no close gate; (d) the two removal comments are made precise (the `framework` gap word decides only inverted word orders, all in the miss direction; the lookbehind is inert at 27 and above, so the delivered 40 was inert); (e) seed 170, the prompt, and `change-workflow.md` now state the `Activated at:` fallback and the miss-versus-false-positive trade; (f) the CHANGELOG states that the upgrade itself halts at its docs gate with the lock retained and names the resume verb (release lane, material), the identity bullet says one index generation rather than one comparison kind, and the standing-pair receipts join the commit obligation because no other tracked receipt is comparable; (g) every close-gate summary now lists `unreadable` beside missing, red, and stale. Disclosed, not repaired, all in the declared miss direction or pre-existing: unlisted repository-wide adjectives pass silently; the house-style bullet `Full suite bytecode-free + docs validation` has no health verb and stays silent; two closed-archive shapes read as change-local yet fire (a relative-clause narrowing such as `All existing tests that exercised the old names pass`, and `clean` read as a health predicate in `from a clean tree`), so a consumer hitting either rewrites one line as the diagnostic instructs; and the incremental `--changed` lint reaches the wave-owned AC validators only when `wave.md` is in the changed set, a layering shared by the sibling validators. The qa lane's whole-file sweep then closed hole 6's residue exactly: at its second snapshot 17 mechanisms still survived deletion. Each now has an exact-boundary matrix row verified by mutation: all eleven carve-out markers (silent rows), the `passed` and `passing` predicate forms, the plural `tests suite` noun, the two-word gap cap in BOTH directions, and the health window (predicate ending at 120 fires, 121 is silent), the runner window (24 fires, 25 silent) and the carve-out tail (16 exempts, 17 fires); `_AC_REPO_STATE_CARVE_OUT_RE` joined the coverage floor. Two more undecidable alternatives were REMOVED rather than pinned: `test[-\s]+suites?`, subsumed by its plural neighbour, and the runner lookahead's `--file; Acceptance Criteria Assert What the Change Controls: Round 5, structural repair after the round-4 reverification showed roughly sixty alternation members and tuning constants could be deleted or loosened with the whole suite green. Three moves: the change-local modifier DENYLIST inside the quantifier-to-noun gap was inverted to a finite ALLOWLIST of repository-scope words (`_AC_SCOPE_GAP_WORD`), because enumerating what a change may call its own work is open-ended and every miss was a blocking error on a compliant criterion, whereas an unlisted repository-wide adjective is a silent miss; two mechanisms that could not be pinned were REMOVED rather than given a decorative pin (`framework` in the gap list was dead behind the corpus noun's optional `framework` prefix, and `_AC_CARVE_OUT_LOOKBEHIND` was inert from 20 through 400 because the carve-out pattern's anchored 16-character tail binds tighter); and the hand-written pins were replaced by `AC_RULE_MATRIX`, 61 literal `(bullet, fires)` rows kept in the test module with no reference to the validator's constants, each generated and then VERIFIED discriminating by deleting its member in a scratch copy and watching the outcome flip. A coverage-floor test reads the alternations and fails when any member lacks a row; it fired on its first run for the `.wavefoundry/` path referent. Census unchanged under the allowlist: eight non-closed carriers, five parked, zero in this wave; closed archives moved 442 to 433 as the deliberate trade.

**Changes delivered:**

- **Retrieval Evaluator Binds the Store File Inode Instead of the Store Identity** (`1wtpl-bug retrieval-eval-store-identity-binding`) — 3 ACs completed. Key decisions: ADOPT the data-level comparison tool into this wave (Requirement 4). `benchmarks/compare_retrieval_receipts.py` stays where wave `1wpif` wrote it and is declared by this wave, so the requirement's subject is present in the repository rather than dependent on a paused wave's commit. Its docstring is updated: the blocker it was written for is repaired here, so it now documents the residual case (a comparison across two `evaluator_identity` values, which the compatibility rule binds unconditionally and by design).; Select the inode-split implementation and reject the store-instance-identifier alternative (readiness CODE-RDY-6).
- **Retrieval Evaluator Estimates Pair Jitter From One Order Statistic** (`1wuuh-bug retrieval-eval-jitter-estimator-and-sample-floor`) — 5 ACs completed. Key decisions: CODE-DEL-3 (delivery review, OPERATOR-APPROVED): amend Requirement 4 so hard latency enforcement applies only to `production_change_same_generation`.; The latency BAND is driven by the floor and median only; the p95 component is recorded but excluded from `jitter_ratio` (Requirement 1's "not `warm_p95_ms` alone" read literally as floor-and-median).
- **Acceptance Criteria Assert What the Change Controls** (`1wuui-enh acceptance-criteria-locality-and-gate-scope`) — 5 ACs completed. Key decisions: QA-DEL-10 (delivery review, OPERATOR-APPROVED): fix the documentation to match the code rather than the code to match the documentation.; REL-DEL-3 (delivery review, OPERATOR-APPROVED): keep the blocking polarity and announce it.
## Watchpoints

- Watchpoint (single re-baseline): `1wtpl` and `1wuuh` both edit `retrieval_eval.py`'s compatibility and comparison logic. Land them in one pass and re-baseline ONCE at the end; two separate re-baselines would burn a second frozen-generation evidence window for no gain.
- Watchpoint (self-reference): changing the evaluator changes its `evaluator_identity` digest, which the compatibility rule itself binds, so no receipt recorded before this wave can be compared against one recorded after it. The re-baseline is a deliberate discontinuity, recorded as such, not a regression.
- Watchpoint (no gate shaping): neither evaluator defect may be repaired by loosening a gate so an existing receipt passes. Both were found because the gate refused something; the repair makes the gate measure the right thing, and the new baseline is recorded afterwards.
- Watchpoint (seed gate): `1wuui` edits a seed under `.wavefoundry/framework/seeds/`, which requires `seed_edit_allowed` opened immediately before and closed immediately after, and affects every target repository.
- Watchpoint (no retro-edits): the existing change documents carrying the whole-repository AC clause (the overwhelming majority in closed waves; the exact archive total is scan-dependent, see `1wuui` Progress Log) are left as authored; closed wave records are historical and open waves own their own criteria. The lint sensor must be scoped so it cannot fail them.
- Watchpoint (evidence hygiene, carried from `1wpif`): record any evaluator pair on a quiet machine, and never write evaluator output directly onto a published receipt path (write to temp, promote only after both runs succeed on one frozen generation).
- Blocking coordination: wave `1wpif` is PAUSED with attestation outstanding and receipts recorded under the CURRENT evaluator identity. Landing the evaluator changes first forces `1wpif` to re-record its pair before closing. Decide the order at Prepare; do not discover it at `1wpif`'s close.
- Follow-up (deferred, not this wave): whether the framework suite itself should be judged at the close gate is decided and recorded by `1wuui` AC-3, but any implementation of a suite-running close gate is a separate change.

## Commit Obligation (delivery review REL-DEL-6)

The operator's commit for this wave MUST explicitly stage four paths that are
still untracked while tracked files already reference them. `git commit -a` does
not pick up untracked paths, and omitting them lands a tracked test that reads a
missing fixture, so a fresh clone fails at collection:

```
git add ".wavefoundry/framework/scripts/benchmarks/compare_retrieval_receipts.py"
git add ".wavefoundry/framework/scripts/tests/fixtures/retrieval_eval/"
git add "docs/reports/retrieval-quality-post-1wur7-run1.json"
git add "docs/reports/retrieval-quality-post-1wur7.json"
```

None of the four ships: `build_pack.py` excludes `scripts/benchmarks` and
`scripts/tests`, which the release lane verified directly, and `docs/` is never
packaged. The exposure is entirely at the commit step. The two receipts are the
standing pair under the delivered evaluator identity (round-5 release
reverification): `docs/contributing/review-and-evals.md` names the second as the
`--baseline` source, every earlier `retrieval-quality-*.json` receipt is
tracked, and no other tracked receipt is comparable. The `1wpif` receipts under
`docs/reports/` belong to that wave's obligation, not this one.

## Review Checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-08-31: PASS with amendments** (moderator: wave-council; primer-depth: standard; seats: red-team, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: `1wtpl` plus `1wuuh` Requirement 4 were exactly the pair that converts paused wave `1wpif`'s unsignable cross-generation receipt into a passing one, authored by the coordinator whose wave benefits, against this wave's own "no gate shaping" watchpoint; strongest-alternative: split the wave and hold the enforcement changes until `1wpif` closes, ADOPTED in the narrower form the primer itself recommended, namely route the cross-generation latency clause to `operator_review_required` instead of a silent report and record the ordering decision now rather than deferring it a third time).
- Council seat evidence — red-team (adversarial primer, standard depth): reconstructed the blocked comparison arithmetically from the two receipts and showed `code_search` 807.11 against a 793.92 threshold and `docs_search` 783.34 against 763.17, so `1wtpl` alone yields `fail` and the original Requirement 4 yields `pass`; verified every load-bearing premise of all three change documents against source (`_index_identity`'s seven bound fields, the unconditional whole-mapping identity comparison, `_nearest_rank_p95`'s `ceil(0.95*n)` making a 9-sample p95 the maximum); REFUTED the plan's "297" census as unreproducible across eight phrasings; found `1wuuh` AC-5 to be the outlawed shape inside the wave that outlaws it, `1wtpl` AC-1 unsatisfiable after its own change, `1wtpl` Requirement 4 bound to an untracked artifact, and `operator_review_required` unreachable because its return value is discarded at the call site.
- Lane evidence — qa-reviewer (needs-revision, strong confidence): RESOLVED the primer's hardest open question with data the primer lacked, recomputing quiet pairs (`1seaw` baseline, `before-1seas`) at 0.0% to 1.7% floor and median jitter against the contended pair's 11.8% to 36.7%, so a threshold anywhere in roughly the 3% to 10% band separates them and is chosen from the system rather than fitted; established that the comparator compares report to report and never checks the running module's identity, which makes recorded-receipt replay a legitimate post-change oracle and removes the need for an induced-load fixture; and found that `1wuui` AC-2 quotes the banned clause inside its own Acceptance Criteria section.
- Lane evidence — code-reviewer (needs-revision, narrowly, on plan text rather than approach): confirmed every premise against the tree including the inode pair and all three jitter percentages to the decimal; established that `comparison_kind` is derived AFTER the identity check so `_validated_epoch` must be reordered; that no store-instance identifier exists and minting one would perturb `production_identity`; that `docs_search`'s 9 warm samples are permanent given the frozen corpus, so a verdict-escalating small-sample rule would make a clean pass unreachable forever; and that the census depends on phrasing breadth, with the load-bearing figure being the roughly ten carriers in non-closed waves.
- Seat and lane evidence — docs-contract-reviewer (rotating council seat: approve-with-notes; docs-contract lane: needs-revision, both strong confidence), run LAST against the already-amended packet: judged the gate-shaping repair GENUINELY RESOLVED rather than relabelled, tracing the verdict and exit-code paths to show the outcome moves from a zero-exit `pass` to a non-zero-exit `operator_review_required` naming both regressions, and reproducing the primer's arithmetic to the decimal from the recorded receipt; judged the ordering decision honest about who benefits. Its lane findings drove a second amendment round: DOCS-RDY-1 (severe) showed the close-gate check as specified would permanently block wave close in EVERY target repository, since `build_pack.py` excludes the runner, the test tree, and the receipt from the distribution under the standing "seeds must not instruct them to run tests" policy, so the check is now scoped to where the runner exists with a documented no-op elsewhere; DOCS-RDY-7 caught the replacement shape itself carrying a repository-wide clause ("docs validation passes"), which the seed would have propagated to every future change document; DOCS-RDY-5 caught that the claimed "297" correction had not actually been performed (four instances survived, and the replacement figure did not reproduce either), so both figures are now withdrawn in favour of the enumerated live carriers; DOCS-RDY-6 showed the two cited scoping precedents disagree on `planned` and `paused`, so one is selected explicitly; DOCS-RDY-4 widened the carrier enumeration to seven ACs across three waves; DOCS-RDY-2 gave the new close-gate contract and the extended receipt schema real documentation homes; DOCS-RDY-3 corrected the reachability wording; DOCS-RDY-9 scoped the quote carve-out to the AC bullet rather than the document. It also surfaced an aliasing trap one line from re-creating the silent path, now pinned in `1wuuh`: `report["operator_review_reasons"]` is bound to the same list object the verdict reads, so the wiring must EXTEND rather than reassign.
- Council synthesis: PASS with amendments. All three change documents were amended in this cycle before readiness was recorded: the gate-shaping repair and its recorded ordering decision (`1wuuh` Requirement 4 and two Decision Log rows), the inode-split selection and fixture-level verification (`1wtpl` Requirements 2 and 5, AC-1 and AC-2, two Decision Log rows), status-based validator scoping with the corrected census and an assertion-shape rule that does not fire on documents quoting the clause (`1wuui` Requirements 3 and 4, AC-1, AC-2, new AC-5, one Decision Log row), the replacement-shape restatement of `1wuuh` AC-5, explicit `operator_review_required` wiring, the recorded-pair replay oracle, and the committed sample-array fixture. No blocking finding remains unaddressed; docs validation passes.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| ARCH-DEL-1 | not_issue | no | not_required | — |
| ARCH-DEL-2 | not_issue | no | not_required | — |
| ARCH-DEL-6 | not_issue | no | not_required | — |
| CODE-DEL-3 | not_issue | no | not_required | — |
| DOCS-DEL-1 | not_issue | no | not_required | — |
| DOCS-DEL-2 | not_issue | no | not_required | — |
| QA-DEL-1 | not_issue | no | not_required | — |
| QA-DEL-2 | not_issue | no | not_required | — |
| REL-DEL-11 | not_issue | no | not_required | — |
| REL-DEL-2 | not_issue | no | not_required | — |
| REL-DEL-6 | not_issue | no | not_required | — |

*Machine review state — 11 findings; current: do_now 0, maybe_later 0, dont_do_later 0, not_issue 11*
<!-- wave:finding-synthesis end -->

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| wave-council-readiness | approved | current executed approval follows every affected repair | none |
| code-reviewer | approved | current executed approval follows every affected repair | none |
| qa-reviewer | approved | current executed approval follows every affected repair | none |
| architecture-reviewer | approved | current executed approval follows every affected repair | none |
| docs-contract-reviewer | approved | current executed approval follows every affected repair | none |
| release-reviewer | approved | current executed approval follows every affected repair | none |
| operator-signoff | approved | current executed approval follows every affected repair | none |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Dependencies

- No blocking external wave dependency: all three changes are framework self-correctness repairs and none needs another wave's output.
- Provenance (not a dependency): every defect here was found by wave `1wpif`'s delivery review. `1wtpl` from the evaluator refusing its own `cross_generation` comparison after a compatibility rebuild; `1wuuh` from an independent performance adjudication showing the pair's reported 2.6% jitter against a measured 18.1% median; `1wuui` from one clause producing opposite outcomes across three sibling change documents in that wave.
- Coordination: `1wpif` is PAUSED with attestation outstanding and receipts recorded under the CURRENT evaluator identity. Landing `1wtpl`/`1wuuh` changes that identity, so `1wpif`'s closing round must either re-record its pair afterwards or close before these land. Decide the order explicitly at Prepare rather than discovering it at `1wpif`'s close.

## Current Assumptions

- The framework's own verification machinery is in scope for repair by an ordinary wave; no product retrieval behavior changes here.
- A deliberate evaluator re-baseline is acceptable and is recorded as a discontinuity rather than treated as a regression.
- The existing whole-repository AC clauses are left as authored; only documents in non-closed waves are ever reached by the validator.

## Outputs Produced or Expected

- An evaluator whose store identity survives a controlled rebuild and whose jitter estimate can distinguish a quiet pair from a contended one, plus a fresh same-generation baseline pair recorded under the new evaluator identity.
- Seed-level AC-locality guidance, a lint sensor scoped to newly authored documents, and a recorded decision on where whole-suite state is judged.
- Updated contributor and testing-architecture contract prose.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated token savings use phase-unique returned source versions and mapped workflow prompts, minus recorded request and response tokens. Saved model output or avoided tool loops count only through quality-equivalent paired evidence.

| Stage | Tool calls | Estimated token savings |
| --- | ---: | ---: |
| plan | 27 | 5,918 |
| implement | 15 | 16,562 |
| review | 165 | 4,241,379 |
| **Total** | **207** | **4,263,859** |

<!-- wave:context-efficiency-state {"generation":211,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":15,"content_source_credit":20259,"derived_artifact_credit":0,"direct_net":16562,"estimated_tokens_saved":16562,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":69,"response_debit":3628,"source_credit_count":5,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":0},"plan":{"calls":27,"content_source_credit":26730,"derived_artifact_credit":186,"direct_net":5918,"estimated_tokens_saved":5918,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":3589,"response_debit":20915,"source_credit_count":5,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3506},"review":{"calls":165,"content_source_credit":4700519,"derived_artifact_credit":1836,"direct_net":4241379,"estimated_tokens_saved":4241379,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":78867,"response_debit":383873,"source_credit_count":211,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1764}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":207,"content_source_credit":4747508,"derived_artifact_credit":2022,"direct_net":4263859,"estimated_tokens_saved":4263859,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":82525,"response_debit":408416,"source_credit_count":221,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":5270},"wave_id":"1wur7 evaluator-identity-and-ac-locality"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 5 | 0 | 4 | 176,984 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":4,"estimated_exploration_avoided":176984,"surfaced_events":5} -->
<!-- wave:exploration-avoided end -->

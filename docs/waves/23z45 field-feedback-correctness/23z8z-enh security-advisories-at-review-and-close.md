# Name accepted security candidates at Review and both closes

Change ID: `23z8z-enh security-advisories-at-review-and-close`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-11-20
Wave: 23z45

## Rationale

Field feedback against v1.46.0 (items 2 and 3 in `.wavefoundry/work/23z45/field-feedback-v1.46.0.md`) reports two security candidates that are accepted without a block and then drop out of sight.

1. A real finding shown unreachable (`rejection_basis: unsupported_reachability` with `supported_reachability: false`) is exempt from `security_unsettled` whatever gate factor is `unverified`. It records as `dont_do_later` with a required `promotion_trigger`. Review, wave close and change close say nothing about it, so the condition that would reopen it is readable only in `events.jsonl`.
2. A head written before the `security_unsettled` rule existed is reported at Review and wave close as the advisory `security_candidate_predates_rule`. `wf_close_change` keeps only `unsettled_security_candidate` from the same source, so the change close is silent about it.

Both are accepted states and stay accepted. The gap is that the operator who signs off or closes does not see them.

## Product Intent

The operator who reviews a delivery or closes a change or a wave sees every security candidate that was accepted with a gate factor still unknown, with the condition that would reopen it, on the response they are already reading. Before this change two kinds are silent: a finding shown unreachable is named nowhere, and a pre-rule head is not named at the change close. After it, Review (implementation phase), wave close and change close name each one as a non-blocking advisory with its promotion trigger. No gate outcome changes: nothing that passed is refused, and nothing that was refused passes. AC-1 and AC-2 together test the visibility; AC-3 tests that no outcome moved.

The first outcome worth delivering alone is the change-close advisory for pre-rule heads (AC-2), because the diagnostic already exists and only its delivery is missing. The shown-unreachable advisory (AC-1) is independent of it.

## Requirements

1. **Shown-unreachable class.** `review_evidence.security_candidate_state` reports a fourth class beside `unsettled`, `waived` and `predates`. A current synthesis head belongs to it when all of these hold, and it belongs to none of the three earlier classes:
   1. `validation_status` is `real`.
   2. `rejection_basis` is `unsupported_reachability` and `supported_reachability` is `false`.
   3. At least one gate factor is `unverified` under the rule `unsettled_security_factors` applies to a head that is not exempt: `attacker_reachability` or `authority_delta` under any `authority_domain`, and `observable_impact` or `containment` when `authority_domain` is not `none`.
2. **One factor rule.** The factor list in Requirement 1.3 and the list `unsettled_security_factors` returns come from one implementation, so the two cannot drift. `unsettled_security_factors` keeps its present return value for every input, including `()` for an exempt head.
3. **Advisory content.** For each head in the class, `lifecycle_gates._security_candidate_diagnostics` emits one diagnostic with code `security_candidate_shown_unreachable` and `advisory: True`. Its message names the `finding_id`, the unverified factors in gate order, the recorded disposition and the promotion trigger (`none recorded` when the head has none). It states that the finding is accepted as shown unreachable and holds no signoff, and that it is missing evidence, not a demonstrated defect. It names the reconsideration route: a `repair_start` in the next cycle whose judgment no longer records the finding as shown unreachable and leaves the factor `unverified`.
4. **Review and wave close.** The advisory reaches `wf_review_wave` (implementation phase) and `wf_close_wave` through the shared delivery evaluator they already consume. It is not added to `SHARED_DELIVERY_DIAGNOSTIC_CODES`.
5. **Change close carries the advisories.** `wf_close_change` returns every diagnostic from `lifecycle_gates.security_candidate_diagnostics` that carries `advisory: True` on its `dry_run` and `ok` responses, in the response `diagnostics` list beside the advisories it already returns there. The rule is the `advisory` flag, not a list of codes; at HEAD plus this change the set is `security_candidate_predates_rule`, `security_candidate_waived` and `security_candidate_shown_unreachable`.
6. **No gate outcome changes.** The diagnostics that refuse a change close are the same as at HEAD: from this source, only `unsettled_security_candidate`. An advisory never enters the list whose non-emptiness refuses the close. Derived dispositions, `blocking`, the status rows, the `Machine review state` line and every `error` response of `wf_close_change` are unchanged.
7. **Unchanged cases.** A legacy prose record (no `review-evidence-source` declaration) gets no security advisory on any of the three surfaces. A typed record whose ledger is unreadable still refuses the change close with `review_ledger_unreadable` and reports no advisory. A closed record is out of reach of all three surfaces, as today.
8. **Platform behaviour.** The change is in-memory classification and message text over parsed ledger records. It touches no path, file mode, process or encoding handling, so behaviour is identical on native Windows, macOS, Linux and WSL2.
9. **Seed 209 states the visibility.** `.wavefoundry/framework/seeds/209-agent-harness-core.prompt.md` gains one sentence in the section whose heading begins `### Credible-threat gate` (line 222 at HEAD), inside the paragraph that opens `**An unknown factor is not an absent factor.**` (line 238 at HEAD), immediately after the sentence that begins `So does a candidate whose` (the `observable_impact` or `containment` sentence) and before the sentence that begins `Unknown evidence is not a demonstrated defect`. It must not sit between the sentence that states the shown-unreachable exception and the `So does a candidate whose` sentence, which depends on that sentence for its meaning. The one sentence says two things. First, a finding shown unreachable with a gate factor still `unverified` stays `dont_do_later`, and Review and close name it with its promotion trigger as a non-blocking advisory. Second, the reconsideration route: a `repair_start` for such a finding must carry a judgment that no longer records it as shown unreachable (it drops the `unsupported_reachability` basis) and leaves the factor `unverified`; a start that keeps the exempt judgment is refused, as the claim table records. This is the route the Requirement 3 advisory message names. No other seed sentence changes, and the sentence repeats none of the clauses that `test_credible_threat_unknown_factor.py` requires exactly once in that section, including `kept on record with its trigger`, `does not hold a gate or status row open` and `a promotion_trigger that names the unknown factor and the evidence that would settle it`.

### Claim status (seed-209 `execution_status`)

Executed with a scratch probe that drives the served handlers through the fixtures of `test_security_unsettled_disposition.py` (probe kept outside the repository; nothing under the repository was written).

| Claim | Status |
| ----- | ------ |
| A served finding with `unsupported_reachability`, `supported_reachability: false` and `attacker_reachability: unverified` records as `dont_do_later` / `not_required`, keeps its `promotion_trigger` on the head, returns `()` from `unsettled_security_factors`, is not `predates_security_rule`, and is in none of the three `security_candidate_state` classes | `executed` |
| On that record `wf_review_wave(phase="implementation")` returns `ok` and `wf_close_wave(mode="dry_run")` returns `dry_run`, each with no diagnostic naming the finding or its trigger; `operator-signoff` reads `approved`; the wave record names the finding id but not the trigger | `executed` |
| `wf_close_change` on a closable member with that head returns `dry_run` and `ok` with no security diagnostic | `executed` |
| With a pre-rule head, Review and wave close carry `security_candidate_predates_rule` with the trigger, while `wf_close_change` returns `dry_run` and `ok` without it | `executed` |
| `wf_close_change` builds its refusal from `if diagnostics:` after filtering the source to `unsettled_security_candidate`, and carries its own advisories in a separate list passed as `diagnostics` on the `dry_run` and `ok` responses | `executed` (read at `server_impl.py` lines 15775 to 15784, 15806 and 15967; observed in the probe responses) |
| The served writer refuses an exempt judgment without a `promotion_trigger` (`selected rejection_basis requires promotion_trigger`) | `executed` |
| A `repair_start` that keeps the exempt judgment is refused (`repair_start requires an actionable synthesis row`); one whose judgment drops the exemption and keeps the factor `unverified` is accepted and yields a `security_unsettled`, `pending` head that Review blocks on | `executed` |
| The shared evaluator decides its blocking list from `SHARED_DELIVERY_DIAGNOSTIC_CODES` and the close envelope from the `advisory` flag, so a new code that is absent from the tuple and carries `advisory: True` blocks neither | `inferred` (read at `lifecycle_gates.py` lines 56 to 67 and 590 to 594; the existing two advisories behave this way in the probe, the new code does not exist yet) |
| An exempt head always stores `dont_do_later` in an open wave, because the validator requires `rejection_basis: none` for `do_now`, `maybe_later` and `not_issue` | `inferred` (read at `review_evidence.py` lines 5623 to 5627) |
| The seed 209 paragraph has no verbatim copy under `docs/`; seeds 213 and 229 and their rendered agent docs carry their own shorter wording and do not mention the exception | `executed` (`grep` for the paragraph's opening phrase over `docs/`, the host surface folders and the seeds) |
| `test_credible_threat_unknown_factor.py` requires each of fourteen clauses exactly once inside the seed 209 gate section, so an added sentence must not repeat one | `executed` (read at lines 29 to 44 and 140 to 141) |
| `security_candidate_state` has two readers, `_security_candidate_diagnostics` and the status-row builder, and the second reads only `unsettled` | `executed` (`grep` census over `.wavefoundry/framework/`: `lifecycle_gates.py:287`, `review_evidence.py:2629`) |

## Scope

**Problem statement:** Two kinds of accepted security candidate are not shown to the operator at the lifecycle steps where they decide: a finding shown unreachable with an unknown gate factor (silent everywhere) and a pre-rule head (silent at the change close).

**In scope:**

- The shown-unreachable class in `security_candidate_state` and its advisory diagnostic.
- Delivery of the security advisories on the `dry_run` and `ok` responses of `wf_close_change`.
- Tests for both, including the no-outcome-change proof and the advisory census entry.
- The tool contract in `docs/specs/mcp-tool-surface.md`, the two architecture passages named below, and a changelog entry.
- One sentence in seed 209 (Requirement 9).

**Out of scope:**

- Any change to derivation, blocking, the exemption itself, the status rows or the signoff state.
- Security advisories on an `error` response of `wf_close_change`. A refused close is unchanged; the operator reads the full list at Review.
- Review in the prepare phase, which does not consume the shared delivery evaluator.
- Naming exempt heads in the wave record's rendered projections or the dashboard.
- Any other seed prose, including the shorter restatements in seeds 213 and 229, and hand edits to rendered surfaces.

## Acceptance Criteria

- [x] AC-1: With a current head shown unreachable that has an unverified gate factor, the Review implementation phase, the wave close dry run and the change close (`dry_run` and `create`) each return exactly one `security_candidate_shown_unreachable` diagnostic with `advisory: True` whose message contains the finding id, each unverified factor and the promotion trigger text. Oracle: served handlers over a producer-built ledger. Fails at HEAD, where no response names the finding or the trigger.
  1. A head shown unreachable with every gate factor settled, and one whose only unknown is `observable_impact` or `containment` under `authority_domain: none`, produce no such diagnostic.
  2. The factor list in the message equals what `unsettled_security_factors` returns for the same judgment with the exemption removed, over the existing fifteen-combination factor matrix.
- [x] AC-2: With a pre-rule head on a closable member, `wf_close_change` returns `dry_run` and then `ok` and each response carries one `security_candidate_predates_rule` diagnostic with `advisory: True` and the same message Review returns for that head. A waived head is carried the same way as `security_candidate_waived`. Fails at HEAD, where both responses carry no security diagnostic.
- [x] AC-3: No gate outcome moves. Oracle: the same fixtures run through each surface before and after the advisory exists.
  1. For a shown-unreachable head and for a pre-rule head, the `status` of Review, wave close dry run and change close (`dry_run`, `create`) equals the HEAD value recorded in the claim table, `operator-signoff` reads `approved`, the stored disposition and `blocking` of every head are unchanged, and the change close writes the same files.
  2. A pending `security_unsettled` head still refuses the change close with `unsettled_security_candidate` and writes nothing, and `unsettled_security_factors` still returns `()` for an exempt head.
  3. Known-bad, two mutations, each recorded in the delivery evidence with its outcome and the failing test. Mutation A passes the unfiltered source into the change close's refusing list: the change close then returns `error` for an advisory-only record. Mutation B emits the new diagnostic without `advisory: True`: the wave close refuses, and the change close returns `ok` without the advisory, because its refusing filter is by code and its carrying rule is by flag. Each mutation makes a test added by this change fail.
- [x] AC-4: A legacy prose record and a typed record with an unreadable ledger return the same change-close response as at HEAD: no security advisory, and `review_ledger_unreadable` for the second. Fails if the advisory pass runs outside the branch that established authority.
- [x] AC-5: `docs/specs/mcp-tool-surface.md` states the new advisory, the class rule and the change-close delivery rule (the `advisory` flag, `dry_run` and `ok` only), and the advisory census in `test_server_tools_lifecycle.py` lists the new code. Fails at HEAD: the census test fails as soon as the diagnostic exists without its entry, and the contract names only `unsettled_security_candidate` for change close.
- [x] AC-6: The change's own suites and every test it adds pass; the documents this change authors or edits validate; and no failure elsewhere is attributable to this change.
- [x] AC-7: Inside the `### Credible-threat gate` section of seed 209, the paragraph that opens `**An unknown factor is not an absent factor.**` states that Review and close name a finding shown unreachable with an unverified factor, with its promotion trigger, as an advisory, and states that a `repair_start` reconsidering such a finding needs a judgment that no longer records it as shown unreachable. The sentence sits immediately after the sentence that begins `So does a candidate whose`, which still directly follows the sentence that states the shown-unreachable exception. Oracle: a test that reads the seed section, plus the existing exactly-once clause tests in `test_credible_threat_unknown_factor.py`, which still pass. Fails at HEAD, where the section has no such statement; fails also if the sentence is placed outside the gate section, is placed between the exception sentence and the `So does a candidate whose` sentence, or repeats a counted clause.

## Tasks

- [x] Open `framework_edit_allowed`; close it when the framework edits are done.
- [x] `review_evidence.py`: factor the gate-factor list out of `unsettled_security_factors` so the exemption wraps one shared rule; add the shown-unreachable class to `security_candidate_state` as the last branch, with `finding_id`, `promotion_trigger`, `disposition` and `unverified_factors`; update the docstrings.
- [x] `lifecycle_gates.py`: emit `security_candidate_shown_unreachable` (advisory) in `_security_candidate_diagnostics`; update its docstring.
- [x] `wf_server/server_impl.py`: in `wf_close_change_response`, call the source once, keep the refusing filter as it is, and add the `advisory: True` diagnostics to the advisory list returned on `dry_run` and `ok`. Update the tool docstring if it enumerates change-close diagnostics.
- [x] Tests in `test_security_unsettled_disposition.py` for AC-1 to AC-4; add the census tuple in `test_server_tools_lifecycle.py`.
- [x] Run the AC-3 known-bad mutation in a scratch tree and record the failing test.
- [x] `docs/specs/mcp-tool-surface.md`: the unsettled-security-candidates paragraph and the `wf_close_change` Gate and Response entries.
- [x] `docs/architecture/data-and-control-flow.md`: the per-change close passage (8b) and the security reconsideration passage.
- [x] Seed 209: open `seed_edit_allowed`, add the Requirement 9 sentence after the sentence that begins `So does a candidate whose`, and close the gate immediately after the edit. Then regenerate the rendered surfaces with the framework's surface sync; if it reports drift, resolve it by regenerating, never by hand-editing a rendered file.
- [x] Add the AC-7 seed test beside the existing seed 209 checks.
- [x] Root changelog: one entry under an Unreleased heading.
- [x] Run the focused suites, then the full framework suite last.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| classification-and-diagnostic | implementer | none | `review_evidence.py`, `lifecycle_gates.py` |
| change-close-delivery | implementer | classification-and-diagnostic | `server_impl.py`; no other change in the wave edits it |
| tests | implementer | change-close-delivery | includes the known-bad mutation |
| contract-docs | implementer | change-close-delivery | spec, architecture doc, changelog; every change in the wave edits the changelog, so serialize it |
| seed-sentence | implementer | classification-and-diagnostic | seed 209 under `seed_edit_allowed`; surfaces regenerated |

## Serialization Points

- `.wavefoundry/framework/scripts/review_evidence.py`
- `.wavefoundry/framework/scripts/lifecycle_gates.py`
- `.wavefoundry/framework/scripts/wf_server/server_impl.py`
- `.wavefoundry/framework/scripts/tests/test_security_unsettled_disposition.py`
- `.wavefoundry/framework/scripts/tests/test_server_tools_lifecycle.py`
- `.wavefoundry/framework/scripts/tests/test_credible_threat_unknown_factor.py`
- `.wavefoundry/framework/seeds/209-agent-harness-core.prompt.md`
- `docs/specs/mcp-tool-surface.md`
- `docs/architecture/data-and-control-flow.md`
- The root changelog gains one entry.

## Affected Architecture Docs

`docs/architecture/data-and-control-flow.md`: the per-change close passage (8b) says the pending candidates come from the shared source and should add that its advisories are carried on a successful close; the security reconsideration passage should name the shown-unreachable class beside `unsettled_security_factors`. No boundary, layering or test-seam change: `lifecycle_gates.py` still never imports `server_impl`, and the change close still writes no review evidence. Other architecture docs: N/A.

## AC Priority

| AC   | Priority  | Rationale |
| ---- | --------- | --------- |
| AC-1 | required  | The requested advisory for findings shown unreachable (feedback item 2). |
| AC-2 | required  | The requested change-close parity (feedback item 3). |
| AC-3 | required  | Security review semantics: the change must be proven to move no gate outcome. |
| AC-4 | required  | The authority branch boundary is the existing refusal for unreadable ledgers. |
| AC-5 | important | The tool contract and the advisory census must describe the new response content. |
| AC-6 | required  | The change's own verification. |
| AC-7 | required  | Operator-directed scope: reviewers must know the trigger they write is shown to the operator. |

## Progress Log

2026-11-21: The full framework suite passed on the reviewed changes. It ran 13,123 tests across 251 files in 741 seconds with 12 skips.

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-11-20 | Spec authored from field feedback items 2 and 3; mechanism claims executed against HEAD with a scratch probe. | Claim status table above |
| 2026-11-20 | Operator decisions recorded: advisory-flag selection accepted, change-close error responses stay unchanged, and scope extended with one sentence in seed 209 (Requirement 9, AC-7). | Decision Log rows marked operator decision |
| 2026-11-20 | Readiness repair pass 1. Finding `R1-23z8z-seed209-anchor`: Requirement 9, AC-7 and the seed task now anchor the sentence after the `So does a candidate whose` sentence. Notes folded in: Requirement 9 and AC-7 state the reconsideration route for an exempt head; AC-3.3 records both mutation outcomes; the Risk and Agent Execution Graph rows that called `server_impl.py` shared now name the changelog; AC-6 and AC-7 put in numeric order. | `.wavefoundry/work/23z45/review/docs-contract-reviewer.md` (F1, N1, N4), `security-reviewer.md` (N4), `architecture-reviewer.md` (N5); seed 209 line 238 read |
| 2026-11-20 | Readback: add a fourth `shown_unreachable` class to `security_candidate_state` (real head, `unsupported_reachability` with `supported_reachability: false`, at least one gate factor `unverified` under the one shared factor rule) and emit one advisory `security_candidate_shown_unreachable` per head from `_security_candidate_diagnostics`; have `wf_close_change` carry every `advisory: True` diagnostic from that source on `dry_run` and `ok` only, with the refusing filter untouched; add one sentence to the seed 209 gate paragraph after the `So does a candidate whose` sentence. ACs 1 to 7. Scope boundary: no derivation, blocking, status-row, signoff or error-response change; seeds 213 and 229 untouched. Files: the nine Serialization Points and the root changelog. Example: before, an exempt head with `attacker_reachability: unverified` gives Review `ok` with no diagnostic naming it; after, Review returns `ok` with one advisory naming the finding, the factor, `dont_do_later` and its trigger. | Spec Requirements 1 to 9 |
| 2026-11-20 | Implemented. `review_evidence.py`: `_shown_unreachable` and `_unverified_security_gate_factors` hold the exemption and the one factor rule; `unsettled_security_factors` wraps them and `security_candidate_state` adds the `shown_unreachable` class as its last branch. `lifecycle_gates.py` emits `security_candidate_shown_unreachable` with `advisory=True`. `wf_close_change_response` calls the source once inside the branch that established authority, keeps the refusing filter by code, and seeds its `advisories` list with the `advisory: True` diagnostics, so they reach only the `dry_run` and `ok` responses. Seed 209 gained the one sentence under `seed_edit_allowed` (opened and closed around the edit); `wf_sync_surfaces(mode='run')` wrote nothing. | `git diff` of the three scripts and the seed |
| 2026-11-20 | Tests added: `AcceptedCandidateAdvisoryTests` (nine tests) in `test_security_unsettled_disposition.py`, `ShownUnreachableVisibilityTests` (two tests) in `test_credible_threat_unknown_factor.py`, one census tuple in `test_server_tools_lifecycle.py`. Fix absent (the three scripts at HEAD in a scratch copy): all nine advisory tests fail or error. Seed at HEAD: both seed tests error. Census without the tuple: `test_advisory_tags_appear_only_at_the_sanctioned_sites` fails naming the new code. | `.wavefoundry/work/23z45/23z8z/known-bad-head.log`, `known-bad-seed-head.log`, `known-bad-census.log` |
| 2026-11-20 | AC-3.3 known-bad, scratch tree. Mutation A (unfiltered source into the change close's refusing list): the change close returns `error` for an advisory-only record; five failures, including `test_review_and_both_closes_name_a_finding_shown_unreachable`, `test_change_close_carries_the_pre_rule_advisory_review_returns` and `test_change_close_carries_the_waived_advisory_review_returns`. Mutation B (new diagnostic without `advisory=True`): the wave close dry run refuses, so `test_review_and_both_closes_name_a_finding_shown_unreachable` fails; `test_the_named_factors_match_the_unsettled_rule_over_the_factor_matrix` and `test_a_legacy_or_unreadable_record_gets_no_security_advisory` (its readable-record control, where the change close carries no advisory) fail too. Landing-rule mutants: C (advisories appended to a refusal) fails `test_a_pending_unsettled_head_still_refuses_the_change_close_without_an_advisory`; D (class rule ignoring the `authority_domain` condition) fails the matrix test and `test_a_settled_or_correctness_side_head_shown_unreachable_gets_no_advisory`. The scratch tree restored to the working copy passes all nine. | `.wavefoundry/work/23z45/23z8z/known-bad-mutation-a.log` to `known-bad-mutation-d.log` |
| 2026-11-20 | Observations. AC-4: as the QA readiness note N9 says, moving the advisory pass outside the authority branch is not observable for a correct design (the source returns nothing for a legacy record and a refusal carries no advisory), so the AC-4 test gives the unreadable ledger an advisory-eligible head, first shows that the readable record carries the advisory, and pins that a refusal lists only `review_ledger_unreadable`; mutant C is the one it and the AC-3.2 test catch. AC-1.2 asserts the message's factor list against the literal combination (QA N7) and against `unsettled_security_factors` with the exemption removed, for both a security domain and `none`. AC-3.1 compares the written files with a control record that has no such head (QA N8). The registered `wf_close_change` tool docstring lists the refusing gates, which did not change, and is pinned by a handler-digest fixture outside this change's Serialization Points, so it was left as is; the `wf_close_change_response` docstring and the tool contract state the advisory delivery. The security lane's note stands: the new class does not carry `superseded_waiver_id`. | `test_security_unsettled_disposition.py`; `.wavefoundry/work/23z45/review/qa-reviewer.md` |
| 2026-11-20 | Platform behaviour: in-memory classification and message text over parsed ledger records; no path, file mode, process or encoding handling is touched, so native Windows, macOS, Linux and WSL2 behave identically. Executed on macOS only. Gapfill: `grep` used for symbol and passage census in files already named by the spec, and for the docstring pin census, where exact-text line listings across several files were needed in one pass. | Requirement 8 |
| 2026-11-20 | Focused suites, working tree: `test_security_unsettled_disposition` 60 OK, `test_credible_threat_unknown_factor` 10 OK, `test_server_tools_lifecycle` 712 OK (2 skipped), `test_lifecycle_gates` 27 OK, `test_lifecycle_gates_structure` 15 OK, `test_review_evidence` 227 OK, `test_review_policy` 123 OK and nine further doc and census modules OK. `test_mcp_tool_registry`: 26 pass, and `test_reload_rebuilds_the_registry_from_fresh_code` fails because the bare `python3` used for this focused run cannot import `mcp` in its child process; that is the interpreter, not this change. `wf_validate_docs` passes. AC-6 and the last task stay open for the coordinator's full suite run; the first task stays open because the coordinator owns `framework_edit_allowed`. | `.wavefoundry/work/23z45/23z8z/focused.log` |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-11-20 | Selected: add a fourth class to `security_candidate_state` and one advisory diagnostic from the shared source; have the change close carry the source's `advisory: True` diagnostics on `dry_run` and `ok`. | One source already feeds all three surfaces, so Review and wave close gain the advisory with no new call site and the change close needs only delivery. It reuses the per-candidate advisory shape of `security_candidate_predates_rule`. | A: widen the `predates` class to include exempt heads. Weakness: the pre-rule message says the head was recorded before the rule and would now derive `security_unsettled`, which is false for an exempt head. B: show the trigger in the wave record's rendered projection instead. Weakness: it changes a rendered record surface and its byte oracles, and still leaves the lifecycle responses silent, which is where the request asks for it. |
| 2026-11-20 | Mechanism efficacy for the selected approach. | Replay: the probe's exempt head (reachability unverified, trigger recorded) would be named with its trigger on all three surfaces, and its pre-rule head would be named at the change close. Control: the mechanism only advises; the operator acts on it because it appears on the Review response read before `operator-signoff` and on the close response, with the reconsideration route stated. Wrong flags and misses: it names a head whose factor was left `unverified` only because unreachability made it moot, so a record with many such heads produces one line each and may be skimmed; it misses nothing the rule defines, but it cannot judge whether the unreachability evidence is sound. Existing data: the trigger is already on the ledger head, so no new data is recorded. Measure after release: the reporting distribution confirms the advisory appears at Review and both closes, and no report arrives of a close that changed outcome. | None. |
| 2026-11-20 | The change close selects advisories by the `advisory` flag, so it also carries `security_candidate_waived`. | The request is parity with Review and wave close, and a code list would repeat the omission this change fixes the next time an advisory is added. The refusing filter is left exactly as it is, so the flag rule cannot widen what refuses. | Carry only `security_candidate_predates_rule` and the new code. Weakness: a waived candidate stays silent at change close for no stated reason. Operator decision, 2026-11-20: accepted as selected. |
| 2026-11-20 | Error responses of `wf_close_change` stay unchanged. | The conservative reading of "change no gate outcome" is to leave refusals byte-identical; a refused close routes the operator to Review, which lists everything. | Attach advisories to refusals too. Weakness: it edits every refusal envelope for no decision the operator makes there. Operator decision, 2026-11-20: error responses stay unchanged. |
| 2026-11-20 | Operator decision: add one sentence to seed 209 saying Review and close show the promotion trigger for a finding shown unreachable with an unverified factor. | The reviewer who writes the trigger should know the operator reads it at sign-off and close, so it is written to be acted on. The paragraph in the credible-threat gate section already states the exception, so the sentence sits beside it. | Leave seed prose unchanged (the earlier plan). Weakness: the guidance would describe the exception without saying the trigger is now visible. Seeds 213 and 229 are not edited; they do not mention the exception. |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| An advisory leaks into the change close's refusing list and a record that closed at HEAD is refused. | Requirement 6 and AC-3, with a recorded known-bad mutation. |
| The class rule drifts from the `security_unsettled` factor rule when a factor is added later. | Requirement 2: one shared implementation, checked over the factor matrix (AC-1.2). |
| A record with many findings shown unreachable produces a long advisory list that is skimmed. | One line per head, the existing shape; no cap is added until field data shows a need. |
| The seed sentence repeats a clause that a test counts exactly once, lands outside the gate section, or splits the exception sentence from the `So does a candidate whose` sentence. | Requirement 9 names the anchor and AC-7 tests it; the existing clause tests fail on a repeated clause. |
| A seed edit reaches every target repository. | One sentence, descriptive only, under `seed_edit_allowed`; it instructs no new reviewer action. |
| A distribution that asserts an exact diagnostic list on a clean Review or close sees a new advisory. | The code is additive and advisory; the changelog entry and the tool contract name it. |
| The root changelog is edited by every change in the same wave. | Declared in Serialization Points; the coordinator serializes changelog edits. No other change edits `server_impl.py`, and this change's edit there is confined to the security branch of `wf_close_change_response`. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.

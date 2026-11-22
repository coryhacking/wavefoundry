# Review Event Execution Status Honesty

Change ID: `242k4-bug review-event-execution-status-honesty`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-11-22
Wave: 242k5 review-evidence-execution-honesty

## Rationale

`wf_review_event` cannot record a finding that a reviewer verified by reading. Every finding and approval is stored as `execution_status: executed`, and the tool refuses the honest alternative in two ways. A reviewer who could not run a check therefore has two choices: leave the finding out of the ledger, or affirm integrity checks that did not happen. The 23z46 wave record shows the second outcome. Its Progress Log entry "Evidence correction" of 2026-11-20 says that one architecture finding, its reverification and one release reverification carry `true` integrity values that overstate what those reviewers executed. The same entry records that a preview of the honest form was refused with "dedup evidence must be executed". The ledger is the review authority, so a tool that accepts only the overstated form damages every later reader of it.

**Observed failure.** All three results come from the real `wf_review_event_response` handler in a throwaway root. The script is `.wavefoundry/work/242k5/planning/repro_handler.py`, run with `python3 -B` on the tree of 2026-11-22. The qa-reviewer reran a copy of it during readiness review and got the same three results.

| Input | Actual result | Expected result |
| --- | --- | --- |
| A finding with no status stated, five integrity checks `true`, `limitations: "read-only, no probe run"`, `mode: create` | Appended. The stored record carries `execution_status: executed` beside the reviewer's own "read-only, no probe run". The caller had no documented way to state another status. | The caller can state how the claim was verified, and the record stores that statement. An omitted status still stores `executed`. |
| The same finding with honest checks: `public_path_reached: false`, `known_bad_detected: false`, `test_ran_without_unintended_skip: false` | Refused: `executed finding event cannot carry integrity_checks.public_path_reached=false`. The message tells the caller not to record the claim as executed, and names no way to do that. | A read-only finding that states its status is recorded with honest `false` checks. |
| The same honest finding with `evidence.execution_status` set to `inferred`, `unverified` or `not_applicable`, blocking or not, `dry_run` or `create` | Refused: `review run ... dedup evidence must be executed`. | The finding is recorded. It clears no lane and completes no repair. |

A fourth result concerns approvals. An approval that states `evidence.execution_status: inferred` is accepted, and `build_compact_review_event` stores `executed` (`repro_builder.py`, case 4). The tool silently replaces the caller's statement.

**Mechanism.** These claims are `executed` unless marked otherwise.

- `evidence.execution_status` already reaches the finding builder. `wf_review_event_response` merges the `evidence` object into the semantic event, and `build_compact_review_event` reads `event.get("execution_status", "executed")`. No document, docstring or schema names the field, so no caller knows it exists.
- A caller who finds the field is still refused. The builder reuses the finding's evidence record as the run's `dedup_evidence_id`, and `_validate_relationships` requires that record to be `executed`. The existing unit test for the honest-false path, `test_non_executed_finding_may_honestly_carry_false_integrity_check`, calls the builder alone and never reaches the validator, so the suite stays green while the public path refuses.
- The approval branch and `_build_operator_close` write the literal `"executed"` and never read the caller's value.

**Extent.** The census script `scan_status_census.py` read all 396 ledgers under `docs/waves/`. It found 3,884 `finding` evidence rows stored as `executed`, and two stored as `inferred`. Both `inferred` rows are in the closed wave `1skt1`, whose records were authored before this tool existed. So the tool has never recorded a non-executed finding. A lexical scan of the two cited ledgers (`scan_ledgers.py`) matched 33 of 112 evidence rows in 23z46 and 28 of 72 in 23zbf whose text says a check was read or not run. That scan matches wording, so it bounds the problem and does not count overstated records exactly. In 23zbf, three qa-reviewer readiness findings say "Read-only; no probe executed" and store `executed` with all five checks `true`. The reality-checker reran both scripts during readiness review and got the same figures.

## Product Intent

Reviewers, the coordinator who records their evidence, and anyone who later reads a ledger benefit. Before this change, every finding says `executed` whatever the reviewer did. After it, a reviewer who only read can say so: the finding stores the stated status and the reviewer's own integrity values, and a reader can separate a finding that was run from one that was read.

The boundary is that no gate changes. Evidence that was not executed can open and record a finding. It clears no lane, completes no repair, satisfies no approval and completes no checkpoint. Records written before the change stay as written and stay valid, and a caller that never states the status sees no change in behavior.

One pressure remains, by operator decision. A lane that clears its block must still record `executed` evidence, at readiness as well as at delivery. A reviewer who verified a repair only by reading cannot clear the lane honestly; the reviewer runs a check, or the finding stays open. This change removes the pressure to overstate when a finding is recorded. It does not remove it when a lane is cleared.

AC-1 and AC-3 together test whether the intent was established: a read-only finding with honest `false` checks is recorded through the public tool, and the stored status is the stated one. AC-5 and AC-6 test the boundary.

One effect can only be observed after delivery: whether reviewers use the field. Observe the next two waves that run a prepare council after release. Their ledgers should contain `inferred` findings where a lane's `limitations` says it only read.

## Requirements

1. **Meaning of each status.** Seed 209 defines the four values of `execution_status` for a finding. The status describes what the recording actor did to verify the claim in this review.
   1. `executed`: a command, test, probe or handler call ran, and its result is the observation. The thing that ran exercised the system or evaluated the claim: a test, a probe script, a tool or handler call against the named path, or a checker such as docs-lint or a render.
   2. `inferred`: the actor read code, documents, a plan or earlier output. A read-only search that only retrieves text for the actor to read, such as `grep` or `code_read`, is reading, so it is `inferred`.
   3. `unverified`: neither. The actor did not run the claim and did not read enough to conclude, or a tool failed, or a census was open, stale or truncated.
   4. `not_applicable`: as seed 209 already defines it. The state or path the claim concerns does not exist, and the record cites the contract fact that proves it.
   5. One existing exception stays. A safe-boundary demonstration runs the nearest faithful boundary and not the claimed path. It is recorded as `inferred` with `safe_boundary: true`, as the validator requires today.
2. **Caller input for a finding.** `evidence.execution_status` is an optional, documented input on a finding event. The value is one of the four in `EVIDENCE_STATUSES`.
   1. When the field is omitted, the stored status is `executed`, as today. A caller that never states the status sees no change.
   2. When the field is stated, the stored record carries exactly that value. The tool never replaces a stated status.
   3. A value outside the vocabulary is refused by the builder with the allowed values, before any ledger validation runs.
   4. The rule is the same for every finding event a caller authors: `readiness`, `initial_delivery`, `repair_start` and `reverification`. No run kind is forced to state a status, so a `repair_start` needs none.
   5. A `convergence_checkpoint` is minted by the builder inside the final reverification, and that minted run carries no evidence record and no status. Where the builder accepts a checkpoint authored by a caller, as it does today, that event passes through the same finding branch and the same rules, including requirement 5.1.
   6. Replay is unchanged. An identical retry of an event already in the ledger replays without a second append, and the replay lookup runs before any refusal this change adds. Request-digest normalization keeps treating an omitted status as `executed`, so digests stored before this change still match.
3. **Integrity checks per status, for a finding.** The five booleans stay required and typed for every status.
   1. `executed`: every boolean is `true`, as today.
   2. `inferred`, `unverified` and `not_applicable`: each boolean is `true` or `false` as the actor honestly states. `false` means the check was not demonstrated. `known_bad_detected: false` means no known-bad control was run. `known_bad_detection_method` stays a required non-empty string and says so.
   3. `null` is accepted only where seed 209 permits it today: an `operator-signoff` approval, operator-close evidence, and `known_bad_detected` on an unaffected specialist readiness approval. It stays refused on every other finding.
   4. When the builder refuses a `false` check on an `executed` finding, the message names the remedy: state `evidence.execution_status` as `inferred` or `unverified` when the check was not run. The existing sentence that tells the caller never to change `false` to `true` stays.
4. **Approvals and operator records stay `executed`.** An approval record stores `executed`, as today. On an approval the status attests that the approving actor performed its review pass for its phase, which is how seed 209 already defines an approval's check. It is not a claim that code ran. What the actor read and what it ran belongs in `limitations`.
   1. An approval event that states `evidence.execution_status` with any value other than `executed` is refused, and nothing is appended. The diagnostic says that an actor who cannot affirm the review records a finding or does not approve.
   2. The same rule applies to the operator close of an unsettled security candidate: its evidence stays tool-derived, and a contrary stated status is refused.
   3. An approval or an operator close that omits the field, or states `executed`, is recorded exactly as today.
5. **No gate change.** Whatever needs `executed` evidence today still needs it. The table gives the outcome for a finding of each status.

   | Status | Open and record a finding | Support a blocking synthesis | Clear a required lane, complete a repair, or make an existing finding terminal |
   | --- | --- | --- | --- |
   | `executed` | Yes | Yes | Yes, as today |
   | `inferred` | Yes | Yes | Refused |
   | `unverified` | Yes | Refused, as today | Refused |
   | `not_applicable` | Yes | Refused, as today | Refused |

   1. The refusal is stated by outcome and not by run kind or phase. The builder refuses any finding event with a non-executed status that supersedes an existing head when its synthesis would do one of three things: drop a lane from `blocking_required_lanes`, set `repair_execution_state` to `completed` on a head that would have no blocking lanes left, or make terminal a head that was not terminal. This covers a `reverification`, a `repair_start` and a caller-authored `convergence_checkpoint` alike, and a finding of any origin phase. A lane-less terminal reverification meets the second and third conditions. A caller-authored checkpoint on a lane-less finding meets the second, and that condition is the one that catches it, because a checkpoint is not the builder's `terminal_reverification`. A head that reaches a terminal state through `not_required` and never through `completed` meets the third. Nothing is appended, the prior synthesis stays current, and the diagnostic says that the outcome requires `executed` evidence.
   2. An event that does none of those three things is not a gate. A reviewer can record "read the repair, still wrong" as an `inferred` reverification that keeps its lanes blocking. The builder sets `repair_execution_state` to `completed` on every reverification of an action-required finding, including this one. A `completed` state with lanes still blocking gates nothing: closure needs the finding's blocking lanes to be empty, and the review projection keeps the block open while a lane remains. So that event is recorded.
   3. Every approval gate keeps its current rule. A required approval is `executed` evidence in the delivery phase field, and `_approval_rows`, the closure check and the review-status projection keep reading only `executed` approvals.
   4. The validator rules for lane reassessment evidence, the post-convergence frozen boundary, the census, the safe boundary and probe authorization do not change. Lane reassessment evidence must still be `executed` in both phases.
   5. No rule depends on the finding's phase. The phase label that a caller selects through `run_kind` therefore selects no easier rule.
6. **Validator.** `validate_review_evidence_records` changes in one place, and the change only accepts more.
   1. A review run whose sealed-universe evidence is its own sole finding evidence no longer requires that evidence to be `executed`. Separate `dedup` and `census` evidence still must be `executed`.
   2. No validator rule becomes stricter. Every record that validates today validates after the change.
7. **Reading the status back.** The compact rows of `wf_review_event(event="list")` include `execution_status` for evidence records, so a reader sees it without `verbose=true`.
8. **Existing records.** The change reads and rewrites no stored record. Closed and open ledgers keep their stored `executed` values, including those on read-only evidence. No approval in any open wave lapses, because no approval record changes and the validator only accepts more. Review-policy receipts hash the admitted specs and the project policy, not framework code: the hash is computed in `policy_input_snapshot`, called from `lifecycle_gate_support._prepare_policy_state`. This is `inferred` by the planner, who read it. The reality-checker executed a probe on a copy of the tree during readiness review: the 241lp receipt digest was the same before and after the copy's seed 209, seed 160, carrier block and `review_evidence.py` were mutated.
9. **Guidance.** The field is optional, so the guidance tells callers that it exists and what each value means. Nothing in it forces a caller to pass the field.
   1. Seed 209 gains the status meanings and the boundary in requirement 1 in its field table row for `execution_status`, the per-status integrity rule, the sentence that an approval's `executed` attests the review pass, and the sentence that non-executed evidence clears no lane and completes no repair. It also says that a finding with an open census is `unverified`, which follows from the existing census rule.
   2. The `wf_review_event` docstring and `docs/specs/mcp-tool-surface.md` name `evidence.execution_status` among the observation fields, with its values, its default and the rules in requirements 2 to 5. The tool surface document also says that a server not yet restarted after an upgrade still refuses a non-executed finding with "dedup evidence must be executed".
   3. `review_action_input_schema` describes the field under `evidence.finding` in its own key, as optional, with its allowed values and its default. `REVIEW_FINDING_REQUIRED_EVIDENCE_FIELDS` and `REVIEW_ACTION_CALLER_INPUTS` do not change. `test_lifecycle_golden.py` pins the `caller_input_schema` keys and accepts only declared additions, so the new key is declared there.
   4. A contract test compares the docstring's status values with `EVIDENCE_STATUSES`.
   5. `REVIEW_PROTOCOL_CARRIER_BLOCK` in `render_agent_surfaces.py` gains one sentence. It says that a reviewer tells the coordinator how each finding was verified, and gives the one-line meaning of each status from requirement 1. The surface render carries it into every file that holds the `wave:executable-review-evidence` region: 21 files in this repository on 2026-11-22. They are the reviewer role documents, the specialist documents, `docs/contributing/review-and-evals.md`, the `review-wave`, `create-wave`, `council-review` and `archetype-council` prompts, and the two Guru wrappers. The sentence contains no phrase from `RETIRED_LIFECYCLE_TOKENS`, because the upgrade reconciler fails its preflight on a carrier that contains one.
   6. Seed 160 gains one guardrail bullet for distributions, placed in its Guardrails list outside `UPGRADE_POLICY_BLOCK`. It says that a finding may now state `evidence.execution_status`, that the field is optional so existing prompts and scripts need no change, and that the server must be restarted after the upgrade before a non-executed finding is recorded. No renderer carries seed 160 guardrail prose. The bullet is merged by hand into `docs/prompts/upgrade-wavefoundry.prompt.md`, after the `review-policy-upgrade` end marker and beside the council signoff key paragraph, as that paragraph was. A distribution receives the text because its upgrading agent reads the extracted seed 160.
   7. Seed 178 and `docs/prompts/refresh-techdocs.prompt.md` each tell the coordinator to record a docs-contract fact "as an executed `finding` record". That wording would prescribe a status for a check that may be a reading. Both are reworded to say that the finding states how the fact was verified. The prompt copy is edited by hand, because no renderer carries seed 178 prose.
   8. Carrier census, 2026-11-22. A search of the seeds, the installed lifecycle prompts, `docs/prompts/`, `docs/agents/`, `docs/contributing/` and the native skill folders found these carriers of finding-recording guidance: seed 209, the tool docstring, `docs/specs/mcp-tool-surface.md`, the carrier block, and the seed 178 sentence with its prompt copy. The other mentions route the reader to `wf_review_event`, the guided actions or seed 209 and name no field or status. They include seed 239's instruction to record an untested intent part as a typed finding, and the `prepare-wave` and `review-wave` prompts outside the carrier region.
10. **Platforms.** The change is dictionary and JSON logic with no path, process, encoding or locking behavior. Windows, macOS, Linux and WSL2 behave identically (`inferred`: no platform-specific code is touched; the suite runs on macOS here).

## Scope

**Problem statement:** `wf_review_event` stores `executed` on every finding and approval, refuses honest `false` integrity checks, and refuses every non-executed finding, so a reviewer who only read cannot say so.

**In scope:**

- The finding, approval and operator-close branches of `build_compact_review_event` and `_build_operator_close` in `review_evidence.py`.
- The one validator relaxation in requirement 6.
- The compact list row in `_review_evidence_list_response`.
- The `wf_review_event` docstring, `review_action_input_schema`, seed 209 and `docs/specs/mcp-tool-surface.md`.
- The carrier block in `render_agent_surfaces.py` and its rendered copies.
- The seed 160 guardrail with its hand-merged prompt copy, and the seed 178 sentence with its prompt copy.
- New tests, the test files named under Serialization Points, and the handler-digest pin for `wf_review_event`.
- The Unreleased changelog bullet.

**Out of scope:**

- DECLINE: requiring a finding to state its status. Operator decision 2026-11-22. A required input breaks every carrier and script that records a finding, and gives `repair_start` no honest value.
- DECLINE: letting `inferred` evidence clear a lane or complete a repair, at readiness or at delivery. Operator decision 2026-11-22. The readiness review showed three routes by which a caller could select the easier rule.
- DECLINE: refusing a new `run_kind='readiness'` finding on an open wave, or changing whether a caller may author a `convergence_checkpoint`. Both are existing behaviors. With no rule keyed on phase or run kind, neither is a route past a gate.
- DECLINE: rewriting, re-deriving or annotating any stored record. Closed records are history, and seed 209 makes appended evidence immutable.
- DECLINE: letting an approval store a status other than `executed`. Operator decision 2026-11-22. Seed 209 defines a readiness approval's check as the review pass itself, and every approval gate reads `executed`.
- DECLINE: changing the stored status of `operator-signoff` approvals and operator-close evidence. Their `null` integrity checks and not-applicable method already tell a reader that the operator ran no check, and the gates key on these records.
- DECLINE: a new top-level `execution_status` tool parameter. The field already travels in `evidence`, where the docstring places observation fields, and a new parameter would change the tool's input schema for no added behavior.
- DECLINE: deriving the status in the tool, for `repair_start` or from the integrity booleans. The status is optional, so no event needs a derived value, and seed 209 says the tool never guesses a judgment.
- DECLINE: detecting an overstated status from prose, such as refusing `executed` when `limitations` contains "read-only". A lexical check is easy to evade and refuses honest partial-execution notes. Truth of the stated status stays a reviewer judgment.
- DECLINE: a status column in the `wave.md` Finding Synthesis projection. The projection is checked on closed records, and the list surface in requirement 7 already serves the reader.
- DECLINE: constraining which booleans may be `true` on a non-executed finding. A reading can honestly establish some checks, for example a refuted plan claim as the known-bad control.
- DECLINE: a stricter validator rule for completed repairs. A new refusal in the validator could invalidate a stored ledger; the builder refusal in requirement 5.1 is the gate.

## Acceptance Criteria

Each criterion is checked through `wf_review_event_response` in a temporary root unless it names another surface. AC-1 with AC-3 establishes the intent; AC-5 and AC-6 establish its boundary.

- [x] AC-1: A read-only finding is recorded honestly through the public tool. This fails today with `dedup evidence must be executed`.
  1. A `create` call for a new finding with `evidence.execution_status: inferred` and three integrity checks `false` succeeds, and a `dry_run` of the same input previews the same records.
  2. The stored evidence record carries `execution_status: inferred` and the three `false` values unchanged, and the ledger validates.
  3. The same holds for a non-blocking finding stated as `unverified` and one stated as `not_applicable`.
  4. An `inferred` finding with `safe_boundary: true` and `unexecuted_remainder_prohibited: true` is recorded.
  5. A `repair_start` stated as `inferred` with honest `false` checks, which keeps its lanes blocking, is recorded. This is the call the tool refused during this plan's own readiness repair.
- [x] AC-2: The status is optional, and a stated status is stored as stated.
  1. A finding event with no `evidence.execution_status` produces records equal to those the current code produces for the same input, with `execution_status: executed`. This holds for `readiness`, `initial_delivery`, `repair_start` and `reverification`.
  2. A value outside `EVIDENCE_STATUSES` returns a builder error that lists the allowed values, and appends nothing. Today the same input reaches the validator, whose message lists no values.
  3. A finding that states `executed` produces the same records as one that omits the field, and `review_event_request_digest` gives the same digest for both requests.
- [x] AC-3: Integrity checks follow the stated status. The oracle fails if the status is ignored in either direction.
  1. An `executed` finding with any `false` check is refused, whether the status is stated or omitted, and the diagnostic names `evidence.execution_status` with `inferred` and `unverified` as the remedy.
  2. Each of `inferred`, `unverified` and `not_applicable` accepts `false` checks on a finding that its gates permit.
  3. A `null` check is refused on a finding for all four statuses.
  4. A non-executed finding with an empty `known_bad_detection_method` is refused.
- [x] AC-4: An approval never silently replaces a stated status. Sub-points 1 and 2 fail today because the stated value is dropped and `executed` is stored.
  1. A specialist approval, a council approval and an `operator-signoff` approval that each state `evidence.execution_status: inferred` are refused, and nothing is appended.
  2. An operator close that states a status other than `executed` is refused, and nothing is appended.
  3. The same approvals with the field omitted, or stated as `executed`, produce records equal to those the current code produces for the same input.
  4. An operator close that omits the field produces records equal to those the current code produces for the same input.
- [x] AC-5: Evidence that was not executed clears nothing and completes nothing. Sub-points 3, 4, 9 and 10 fail under an implementation that makes only the validator change: the planning prototype and the security-reviewer's prototype probe each completed such a repair.
  1. For a delivery finding, an `inferred` reverification that would clear a required lane is refused, nothing is appended, and the finding's head and blocking lanes are unchanged.
  2. The relabel probe from the review notes leaves the lane blocking. A finding introduced with `run_kind='readiness'` after an `initial_delivery` run exists, and one introduced with `run_kind='readiness'` on a wave whose Status is `implementing` with no delivery record, each refuse an `inferred` reverification that would clear the lane. A readiness finding on a `planned` wave refuses it too.
  3. For a delivery finding with no blocking lanes, an `inferred` terminal reverification is refused, and `repair_execution_state` stays `pending`.
  4. For the same lane-less delivery finding in cycle 2, an `inferred` caller-authored `convergence_checkpoint` with `evidence.frozen_boundary` is refused, and `repair_execution_state` stays `pending`.
  5. Sub-points 1, 3 and 4 hold for `unverified` and for `not_applicable`.
  6. For a finding with two blocking lanes, one lane's `inferred` reverification that would drop only that lane is refused.
  7. An `inferred` reverification that keeps its required lanes blocking is recorded, for a readiness finding and for a delivery finding.
  8. An `executed` reverification with all checks `true` clears the lane as today, for a readiness finding and for a delivery finding.
  9. For a readiness finding with no blocking lanes, an `inferred` reverification that would make it terminal, or complete its repair, is refused. An implementation that applies the completion and terminal conditions only to delivery findings fails this sub-point.
  10. A reclassifying `inferred` reverification follows the same outcome rule. One that reclassifies a finding to `invalid` is refused: in the current builder that event is either refused by an existing validator rule or yields a head that is terminal through `not_required`, with the lane dropped when the finding had one. One that settles a `security_unsettled` head as not actionable is refused, because the head becomes terminal through `not_required`. One that settles it as actionable, or leaves it unsettled, is recorded, because the head stays `pending` and no lane is dropped. An implementation that tests only lanes and `completed` fails the two refused cases.
- [x] AC-6: The remaining gates keep their outcomes.
  1. A blocking finding stated as `unverified` or `not_applicable` is refused, and the same finding stated as `inferred` is recorded as blocking.
  2. `validate_review_evidence_records` still rejects an approval record whose `execution_status` is `inferred`.
  3. `validate_review_evidence_records` still rejects `inferred` lane reassessment evidence, in the `readiness` phase and in the `delivery` phase.
  4. A review run whose separate `dedup` evidence is `inferred` is still rejected.
- [x] AC-7: Existing records are untouched, stay valid and replay.
  1. A delivery-time, read-only comparison over every `events.jsonl` under `docs/waves/` reports the same validation errors and the same per-signoff approval currency with the change as without it. The baseline is the tree after wave 241lp closed. The comparison names the count of ledgers it read.
  2. Fixture records in the two pre-change shapes validate: a read-only finding stored as `executed`, and a hand-authored `inferred` finding with separate executed `dedup` evidence.
  3. The bytes of every existing ledger are unchanged after the comparison and after the full suite.
  4. A finding bundle already in a ledger replays on an identical retry with no refusal and no append.
  5. An approval bundle whose stored request digest is that of a request stating `evidence.execution_status: inferred`, which the current code accepts, replays on an identical retry with no refusal and no append. This fails under an implementation that places the new approval refusal before the replay lookup.
- [x] AC-8: A reader can tell the statuses apart. The compact rows of `wf_review_event(event="list")` carry `execution_status` on each evidence record, for a ledger that holds both an `executed` and an `inferred` finding. This fails today because the compact row omits the field.
- [x] AC-9: The guidance matches the code.
  1. Seed 209 states the four meanings with the boundary in requirement 1: a test, probe, handler call or checker is `executed`, and reading or a read-only search such as `grep` or `code_read` is `inferred`. It also states the per-status integrity rule, the approval rule, and that non-executed evidence clears no lane and completes no repair.
  2. The `wf_review_event` docstring and `docs/specs/mcp-tool-surface.md` name `evidence.execution_status`, its four values and its default, and a contract test fails when the docstring's values differ from `EVIDENCE_STATUSES`.
  3. `wf_review_wave` returns a `caller_input_schema` whose `evidence.finding` entry names `execution_status` as optional with its allowed values and default, and `test_lifecycle_golden.py` passes with that key as a declared addition.
  4. In `register-surface-handler-digests.json`, the `wf_review_event` hash and one added sentence in `description` are the only differences from the file as it stood when implementation began.
  5. Every file that holds the `wave:executable-review-evidence` region carries the new sentence after the surface render, and a test fails when `REVIEW_PROTOCOL_CARRIER_BLOCK` names a status set that differs from `EVIDENCE_STATUSES`. The same test compares the one-line meaning of each status in the carrier block with the meaning in seed 209's field table row, so the two cannot drift apart.
  6. Seed 160 carries the guardrail bullet, `docs/prompts/upgrade-wavefoundry.prompt.md` carries the same text outside its managed region, and `UPGRADE_POLICY_BLOCK` is unchanged.
  7. Seed 178 and `docs/prompts/refresh-techdocs.prompt.md` no longer prescribe an "executed `finding` record".
  8. The byte-exact seed pins listed in the Tasks census pass unchanged, with no pinned phrase edited.

## Tasks

- [x] Wait for the trigger: `wf_list_waves` shows wave 241lp as closed. Then, before the first edit, record one Progress Log row with these five results.
  1. The diff of the shared files listed under Risks against the 241lp close commit, checked against the symbol anchors this plan cites: `review_action_input_schema`, `_finding_origin_phases`, `build_compact_review_event`, `terminal_reverification`, `_build_operator_close`, `_validate_relationships`, `validate_review_evidence_records`, `_review_evidence_list_response` and `normalize_review_event_request`. The check also confirms the replay order inside `transact()` in `wf_review_event_response`: `_identified_review_event_bundle` runs before `build_identified_review_event`. Requirement 2.6, AC-7.4 and AC-7.5 rest on that order, and 241lp added checks inside `transact()`.
  2. A rerun of `scan_status_census.py`, and of the reality-checker's receipt probe against any wave open at that time.
  3. The count of files that hold the `wave:executable-review-evidence` region.
  4. A census of the test files that author a finding event, including 241lp's `test_small_change_lifecycle.py`.
  5. The seed-pin census described below.
- [x] Open `framework_edit_allowed` for the script, test and fixture edits, and close it when they are done.
- [x] Write the failing tests first, through `wf_review_event_response`: the three observed failures and the approval case from Rationale.
- [x] Finding branch of `build_compact_review_event`: validate a stated `evidence.execution_status`, keep the `executed` default, and extend the `executed`-with-`false` message with the remedy.
- [x] Approval branch and `_build_operator_close`: refuse a stated status other than `executed`.
- [x] Finding branch: refuse, by outcome, a non-executed event that would clear a lane, complete a repair or make a head terminal. Compute the outcome from the synthesis the builder already derives, before any record is returned.
- [x] Validator: relax the sole-finding sealed-universe rule.
- [x] Add `execution_status` to the compact list row.
- [x] Add the optional field to `review_action_input_schema`, and declare the new key in `test_lifecycle_golden.py`.
- [x] Replace the builder-only honest-false test with one that reaches the validator. Add the gate matrix tests for AC-5 and AC-6 and the fixtures for AC-7.
- [x] Seed edit, seed 209: open `seed_edit_allowed`, edit the `execution_status` table row, the integrity-checks paragraph, the re-verification paragraph and the typed-authoring paragraph, then close the gate.
- [x] Seed edit, seed 160: open `seed_edit_allowed`, add the guardrail bullet beside the council signoff key bullet and outside `UPGRADE_POLICY_BLOCK`, then close the gate.
- [x] Seed edit, seed 178: open `seed_edit_allowed`, reword the "executed `finding` record" sentence, then close the gate. `test_render_agent_surfaces.py` pins "never treat a `run` event as evidence", which is in the next sentence of the same paragraph. That sentence stays intact in the seed and in the prompt copy.
- [x] Keep every byte-exact pin on the touched seed paragraphs. The census of 2026-11-22 searched the test tree for phrases from those paragraphs and found these pins on seed 209, all in `test_review_evidence.py`. `test_canonical_seed_states_load_bearing_validator_contract` requires "Lane reassessment evidence must name the original finding phase" and "earlier Executable Evidence Record with `claim_kind: finding`". `test_contract_text_no_longer_demands_operator_affirmation` requires "Do not ask the operator for check values: omit `integrity_checks`", "stores all five booleans as `null` (not applicable)", "Except for the specialist readiness case below", "`operator-signoff` approval has a separate exception", and exactly four table rows that begin "| Yes | Boolean, or `null` (not applicable) on an `operator-signoff` approval;". The same test forbids "may carry `false` integrity checks", "supplied with honest `false` values" and "If any boolean cannot be honestly affirmed, do not approve", so the new seed text must not use those phrases. The census found no test pin on the seed 160 guardrail list or on the seed 178 sentence being reworded; the pin on its neighbor is named in the seed 178 task. Repeat the census at the trigger, because wave 241lp may add pins.
- [x] Add the sentence to `REVIEW_PROTOCOL_CARRIER_BLOCK`, and check it against `RETIRED_LIFECYCLE_TOKENS`. `test_carrier_blocks_carry_chain_aware_independence_contract` requires the block to keep "wf_review_wave(phase='implementation')", "`wf_review_event`", "never hand-edit" and "role without lifecycle mutation authority", and to omit "four-way actionability gate" and "`do_now`".
- [x] Run `wf_sync_surfaces` to render the carrier block, and confirm that only the `wave:executable-review-evidence` regions changed.
- [x] Merge the seed 160 bullet by hand into `docs/prompts/upgrade-wavefoundry.prompt.md` outside the managed region, and edit the seed 178 sentence by hand in `docs/prompts/refresh-techdocs.prompt.md`.
- [x] Update the `wf_review_event` docstring and `docs/specs/mcp-tool-surface.md`, and add the contract test.
- [x] Refresh the handler-digest pin for `wf_review_event` only, and add this change to the fixture's description sentence. The tool-surface golden files store the input schema without prose, and the input schema does not change, so they need no edit.
- [x] Run the read-only ledger comparison for AC-7 and keep its output under `.wavefoundry/work/242k5/`.
- [x] Add an Unreleased `CHANGELOG.md` bullet that ends "Wave 242k5 / 242k4.".
- [x] Run the framework suite last, on the declared profile, and run `wf_validate_docs`.

## Agent Execution Graph

The work is one sequence. Tests come first so that each observed failure is seen failing before its fix.

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| re-census | implementer | - | The Progress Log row at the 241lp trigger |
| failing-tests | implementer | re-census | Public-path tests for the Rationale table |
| builder-and-validator | implementer | failing-tests | Requirements 2 to 7 |
| matrix-and-fixtures | implementer | builder-and-validator | AC-5 to AC-7 |
| guidance | implementer | builder-and-validator | Seeds 209, 160 and 178, carrier block and render, hand merges, docstring, tool surface doc, schema, digest pin |
| verification | qa-reviewer | matrix-and-fixtures, guidance | Ledger comparison, full suite, delivery review |

## Serialization Points

- `.wavefoundry/framework/scripts/review_evidence.py`
- `.wavefoundry/framework/scripts/wf_server/server_impl.py`
- `.wavefoundry/framework/scripts/render_agent_surfaces.py`
- `.wavefoundry/framework/seeds/209-agent-harness-core.prompt.md`
- `.wavefoundry/framework/seeds/160-upgrade-wavefoundry.prompt.md`
- `.wavefoundry/framework/seeds/178-refresh-techdocs.prompt.md`
- `.wavefoundry/framework/scripts/tests/test_review_evidence.py`
- `.wavefoundry/framework/scripts/tests/test_server_tools_lifecycle.py`
- `.wavefoundry/framework/scripts/tests/test_lifecycle_golden.py`
- `.wavefoundry/framework/scripts/tests/test_render_agent_surfaces.py`
- `.wavefoundry/framework/scripts/tests/test_server_tools_retrieval.py`
- `.wavefoundry/framework/scripts/tests/fixtures/register-surface-handler-digests.json`
- `docs/specs/mcp-tool-surface.md`
- `docs/prompts/review-wave.prompt.md`
- `docs/prompts/upgrade-wavefoundry.prompt.md`
- `docs/prompts/refresh-techdocs.prompt.md`
- The root changelog also changes.
- Only the five test files above need edits. About seventeen test files author a finding event. The status is optional and its default is unchanged, so the others need no change.

## Affected Architecture Docs

N/A. The review-evidence contract lives in seed 209 and `docs/specs/mcp-tool-surface.md`, and both are updated here. No module boundary, data path or verification seam moves: the same builder writes the same record types to the same ledger, and the same validator reads them.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | The defect: an honest read-only finding cannot be recorded |
| AC-2 | required | Existing callers see no change, and a stated status is stored as stated |
| AC-3 | required | Stops the refusal that left only the overstated form |
| AC-4 | required | An approval must not replace a stated status silently |
| AC-5 | required | Evidence that was not executed must clear and complete nothing |
| AC-6 | required | The remaining gates keep their outcomes |
| AC-7 | required | Closed and open records stay valid, unchanged and replayable |
| AC-8 | important | Readers can tell executed from read-only evidence without `verbose` |
| AC-9 | required | Callers learn the field only from the guidance and schema |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-11-22 | Reproduced the defect through the real handler in a throwaway root, ran the status census over 396 ledgers, and prototyped the validator relaxations in a scratch copy. | `.wavefoundry/work/242k5/planning/repro_handler.py`, `repro_builder.py`, `scan_status_census.py`, `scan_ledgers.py`, `proto_flow.py` in the same folder |
| 2026-11-22 | Readiness repair, cycle 1, for seven blocking findings: `R1-242k4-status-meaning-boundary`, `R1-242k4-upgrade-guardrail-not-rendered`, `R1-242k4-readiness-relabel-bypass`, `R1-242k4-repair-start-status`, `R1-242k4-old-ledger-replay`, `R1-242k4-relabel-open-wave` and `R1-242k4-checkpoint-completion`. The operator narrowed the fix: the status is optional and no gate changes. Requirements 1, 2, 5, 6, 8 and 9, AC-2, AC-4, AC-5, AC-6, AC-7 and AC-9, the Tasks, the Serialization Points and the Decision Log were rewritten to match. Each `repair_start` was recorded before the edit. The honest form of a repair start, `inferred` with `false` checks, was refused by the tool with "dedup evidence must be executed", so each record states `executed` for the two tool calls it rests on and says so in `limitations`. | The seven `repair_start` records in `events.jsonl`, context `242k5-implementer-repair-1`; the review notes in `.wavefoundry/work/242k5/review/` |
| 2026-11-22 | Readiness repair, cycle 2, for one blocking finding, `R1-242k4-outcome-rule-completed-trigger`, raised by the code-reviewer in the focused round. The operator authorized this second bounded repair on 2026-11-22 and chose option 1. Requirement 5.1 refused every non-executed event that sets `completed`, and the builder sets `completed` on every reverification, so 5.1 refused the event that 5.2 and AC-5.7 require. The repair scopes the `completed` condition to a head with no blocking lanes left and keeps the other two conditions as written. It adds AC-5.9, AC-5.10 and the meaning comparison in AC-9.5, two anchors to the 241lp re-check, and the seed 178 neighbor pin. Wave 241lp is closed and committed as `d8a4dcc6`; the pre-edit re-check row is still owed at implementation. The `repair_start` was recorded before the edit, in cycle 2, because the tool refuses a new repair start in a completed cycle 1. Its honest `inferred` form was refused, as in cycle 1. A probe on the current builder, with `executed` status, gave the reclassification outcomes that AC-5.10 states. | The `repair_start` record in `events.jsonl`, context `242k5-implementer-repair-2`; `.wavefoundry/work/242k5/planning/probe_reclassify.py`; the `*-focused-r2.md` notes in `.wavefoundry/work/242k5/review/` |
| 2026-11-22 | Pre-edit re-check after wave 241lp closed (commit `d8a4dcc6`). Nothing contradicts the plan. (1) Shared files: none carries an uncommitted edit, and every cited anchor exists in `review_evidence.py`: `review_action_input_schema`, `_finding_origin_phases`, `build_compact_review_event`, `terminal_reverification`, `_build_operator_close`, `_validate_relationships`, `validate_review_evidence_records` and `normalize_review_event_request`, which still defaults an omitted finding status to `executed`. `_review_evidence_list_response` exists in `server_impl.py`. Inside `transact()`, both `_identified_review_event_bundle` lookups precede `build_identified_review_event`. (2) Status census: 396 ledgers, 3,908 `finding` rows `executed`, 2 `inferred` (both in `1skt1`), all approvals, dedup and lane reassessment rows `executed`. Receipt probe on a throwaway copy for the only open wave, 242k5: the computed digest equals the stored receipt `review-policy-e764ccac54fd187c865e`, and no append is required. (3) Carrier count: 21 files hold the `wave:executable-review-evidence` region. (4) Finding fixtures: six test files submit a finding event by a strict pattern (`test_memory_records.py`, `test_review_evidence.py`, `test_review_event_promotion_trigger.py`, `test_small_change_lifecycle.py`, `test_server_tools_lifecycle.py`, `test_security_unsettled_disposition.py`); only `test_review_evidence.py` and `test_server_tools_lifecycle.py` hold a non-executed status literal. The earlier figure of about seventeen came from a looser pattern. The status is optional, so none needs a fixture edit. (5) Seed pins: unchanged from the Tasks census. The seed 209 pins are all in `test_review_evidence.py`, the seed 178 neighbor pin is in `test_render_agent_surfaces.py`, and no test pins the seed 160 guardrail list or the sentences to be edited. | `.wavefoundry/work/242k5/impl/receipt_probe_before.txt`; `.wavefoundry/work/242k5/planning/scan_status_census.py`; grep censuses run on the tree of `d8a4dcc6` |
| 2026-11-22 | Implemented. Builder: a stated `evidence.execution_status` is validated and stored as stated, the default stays `executed`, the refusal of a `false` check on an executed finding names the remedy, and a non-executed event that supersedes a head is refused when it would clear a lane, complete a repair on a head with no lanes left, or make the head terminal. Approvals and the operator close refuse a contrary stated status. Validator: the sole-finding sealed-universe rule is relaxed and nothing else changes. The one-line meanings live in one constant, `EXECUTION_STATUS_MEANINGS`; the carrier block and seed 209 state each entry verbatim, and tests compare both with it. Tests cover every AC sub-point through `wf_review_event_response`, with the builder matrix beside them. Carried advisories: the `invalid` reclassification is tested on a non-blocking finding, and one test pins the scoped `completed` condition alone on an already-terminal lane-less head, where the stale approval stays stale. One fixture outside the Serialization Points changed: `tests/fixtures/lifecycle-gate-golden.json` was regenerated, because it stores the `caller_input_schema`; its diff is 60 added lines, the `optional_fields` entry in three fixtures. Requirement 5.2 says the builder sets `completed` on every reverification of an action-required finding. The code keeps `pending` for a reverification from a `security_unsettled` head. The sentence errs on the safe side and was left as written, to avoid lapsing the readiness approvals. The tasks that end with closing a gate stay unchecked: the coordinator closes `framework_edit_allowed` and `seed_edit_allowed`. The edits those tasks name are done. Results: full suite 13,270 tests in 255 files, green, receipt written; second profile 13,248 tests, 255 of 255 files passed. The AC-7.1 comparison read 396 ledgers with the change and without it: same validation errors (none), same approval currency over 4,998 approval rows and 1,217 finding facts. No ledger byte changed after the runs. Records built for requests that omit the status equal those of the earlier code. The 242k5 receipt digest is the same before and after. | `.wavefoundry/work/242k5/impl/`: `full-suite-run-2.log`, `profile-second-run-2.log`, `focused-run-1.log`, `red-builder-tests.log`, `ac-7-1-ledger-comparison.txt`, `ac-7-3-ledger-bytes.txt`, `ac-2-1-omitted-status-comparison.txt`, `receipt_probe_before.txt`, `receipt_probe_after.txt` |
| 2026-11-22 | Gapfill: the implementer did its code retrieval with shell `grep`, `sed` and file reads, not the `code_*` MCP tools: the session record shows 217 shell calls and no `code_*` call. The MCP tools were available, so this was a habit, not a tool limitation. The edits are checked by the full suite, the second profile and the delivery lanes, which were told to use the MCP tools first. | The implementer's session record, counted by the coordinator |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-11-22 | Operator decision 2026-11-22, narrowing the fix. `evidence.execution_status` is an optional, documented input whose default stays `executed`. The tool stores the stated status. No gate changes: non-executed evidence can open and record a finding, and it clears no lane, completes no repair, satisfies no approval and completes no checkpoint. This supersedes the two earlier decisions of the same date in the next two rows. | Operator decision 2026-11-22, citing the readiness findings. The lenient readiness clear created three bypass routes: `R1-242k4-readiness-relabel-bypass`, `R1-242k4-relabel-open-wave` and `R1-242k4-checkpoint-completion`. The required input was a breaking change across every carrier that records a finding, and it left `repair_start` with no honest value (`R1-242k4-repair-start-status`). Mechanism efficacy: replaying the three Rationale rows, the honest finding is recorded and nothing is cleared. The mechanism controls the outcome at write time. It cannot detect a reviewer who states `executed` for a read, and it leaves the pressure to do so at the lane clear, as Product Intent says. Success is measured by the post-release observation in Product Intent. | Keep the lenient readiness clear and guard it with wave status and ledger state: more mechanism, and the ledger alone cannot see that a wave is open |
| 2026-11-22 | Superseded by the first row. An omitted status on a new finding was to be refused. | Operator decision 2026-11-22: refuse a finding that omits its status. Withdrawn the same day by the narrowing decision. | Keep the `executed` default: this is now the decision |
| 2026-11-22 | Superseded by the first row. A readiness finding's lane was to be clearable by `inferred` evidence. | Operator decision 2026-11-22: `inferred` may clear readiness lanes. Withdrawn the same day by the narrowing decision. | Require `executed` in both phases: this is now the decision |
| 2026-11-22 | Approvals and operator records keep `executed` and refuse a contrary stated status. | Operator decision 2026-11-22: approvals and operator records stay `executed`-only. Seed 209 defines a readiness approval's check as the review pass, and all approval gates read `executed`. Refusing a contrary statement removes the silent replacement without changing any gate. The narrowing decision keeps this. | Let readiness approvals store `inferred`: changes `_approval_rows` and the shape rule, and risks approval currency in open waves |
| 2026-11-22 | The gate refusal is stated by outcome: a cleared lane, a completed repair, or a head made terminal. The row below scopes the second outcome. | Planner default, from `R1-242k4-checkpoint-completion`. A rule keyed on `run_kind` left the caller-authored checkpoint open, and a rule keyed on phase left the relabel open. An outcome rule has no label for a caller to choose. | Name `reverification` only: the security-reviewer's probe completed a repair through a checkpoint |
| 2026-11-22 | The `completed` condition of the outcome rule applies only when the head would have no blocking lanes left. The lane-drop and terminal conditions are unchanged. | Planner default under the operator's authorization of 2026-11-22 for a second bounded repair, from `R1-242k4-outcome-rule-completed-trigger`. The builder sets `completed` on every reverification, so the unscoped condition refused the lane-keeping reverification that requirement 5.2 records. A `completed` state with lanes still blocking gates nothing. The scoped condition still refuses the lane-less terminal reverification and the lane-less caller-authored checkpoint. | Drop the `completed` condition: reopens the caller-authored checkpoint, which is not a terminal reverification. Keep it unscoped: AC-5.7 cannot pass |
| 2026-11-22 | `executed` means something ran that exercised the system or evaluated the claim. Retrieving text to read it, even through a tool, is `inferred`. | Planner default, from the operator's definitions and `R1-242k4-status-meaning-boundary`. One act must map to one status, or a reader cannot use the stored value. | Leave the boundary to each reviewer: two honest reviewers record the same act differently |
| 2026-11-22 | The field stays in `evidence`; no top-level parameter. | Planner default. The handler already merges `evidence` into the event and the docstring places observation fields there. The tool's input schema stays unchanged. | A top-level `execution_status` parameter: changes the input schema and its golden files for no added behavior |
| 2026-11-22 | The status is never derived from the integrity booleans. | Planner default. Seed 209 says the tool never guesses a judgment, and booleans cannot separate `inferred` from `unverified`. | Derive `inferred` when any check is `false`: hides the choice from the caller |
| 2026-11-22 | New refusals live in the builder; the validator change only accepts more. | Planner default. The closed wave `1skt1` holds two `inferred` findings, so a stricter validator rule could invalidate a stored ledger. The prototype showed that the validator change alone lets a delivery repair complete on `inferred` evidence, so the builder refusal is required. The builder runs after the replay lookup, so the refusals cannot reach a replay. | Add a validator rule for completed repairs: stronger against hand-edited ledgers, but can break closed records |

## Risks

| Risk | Mitigation |
| --- | --- |
| A lane that verified a repair only by reading cannot clear its block with an honest status. This includes a readiness lane that re-read a repaired plan. | Accepted by operator decision 2026-11-22. Product Intent and seed 209 say so plainly. The lane runs a check whose result bears on the repair, or the finding stays open. |
| With a default of `executed`, a caller who never learns of the field still stores `executed` for a read. | The carrier block, seed 209 and the docstring name the field where reviewers and coordinators read. The refusal of a `false` check names the field at the moment a reviewer tries to be honest. The post-release observation in Product Intent measures use. |
| Wave 241lp is implementing in another session and has uncommitted edits in files this change also edits: `.wavefoundry/framework/scripts/review_evidence.py`, `.wavefoundry/framework/scripts/wf_server/server_impl.py`, `.wavefoundry/framework/scripts/tests/test_review_evidence.py`, `.wavefoundry/framework/scripts/tests/test_render_agent_surfaces.py`, `.wavefoundry/framework/scripts/tests/fixtures/register-surface-handler-digests.json`, `docs/specs/mcp-tool-surface.md`, `docs/prompts/review-wave.prompt.md`, `docs/prompts/agents/review-wave.prompt.md` and `CHANGELOG.md`. | Only one wave can be open, so implementation starts after 241lp closes. The first task names the trigger and the five results to record. This plan depends on none of 241lp's edits. The code-reviewer read 241lp's diff: its hunks touch the approval branch and the shape validator near this plan's edits, and they sit outside the carrier regions of the rendered prompts. |
| A server that was not restarted after an upgrade refuses a non-executed finding with the old "dedup evidence must be executed" message. | The seed 160 guardrail and the tool surface document tell the operator to restart the server first. |
| A ledger that holds a non-executed finding recorded by the new tool fails validation under an older framework version. | State this in the changelog bullet. It affects only a project that downgrades after recording such a finding. |
| The builder is the only enforcement of requirement 5.1; a hand-edited ledger could bypass it for a lane-less finding. | Hand-editing can already forge any value, and typed events are the only supported writer. A lane clear is still refused by the unchanged validator rule for lane reassessment evidence. Recorded as accepted. |
| A reviewer states `executed` for a read. | No mechanism can detect this. Seed 209 now defines the meanings and the boundary. |
| Editing framework files invalidates the framework test receipt for any wave about to close. | Sequence after 241lp, and run the suite last. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.

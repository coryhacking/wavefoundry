# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-09-18
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1yd97 phase-gate-follow-ups`
Title: Phase Gate Follow Ups

## Objective

When this wave closes, the readiness digest that binds declared sensors to approvals is a control on both mutating phases rather than on prepare alone, and the two guards wave `1y0h0` left defeatable are closed. Now, because `1y0h0`'s delivery review proved the close asymmetry by executed probe and deferred a set of carried lane observations behind a production freeze that has since served its purpose.

## Changes

Change ID: `1yd98-enh close-sensor-approval-precondition`
Change Status: `complete`

Change ID: `1yd99-debt phase-gate-guard-and-doc-tidy-ups`
Change Status: `complete`

## Participants

- Coordinator: framework maintainer
- Write-owning roles: implementer, qa
- Requested review lanes: none
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer

Completed At: 2026-09-18

## Wave Summary

Wave `1yd97 phase-gate-follow-ups` (Phase Gate Follow Ups) delivered two changes: Close-sensor approval precondition and Phase-gate guard and documentation tidy-ups. Notable adjustments during implementation: Close-sensor approval precondition: Readiness repair round 5: five lanes reviewed, all blocked, and three of the four repairs the brief flagged as hardest had relocated their defect again. All five lanes found the citation I adopted for the boundary row's policy-entry clauses is wrong: that criterion's own text scopes its scans to a different row, and I took a reviewer's proposed fix without re-deriving it, which is the same error as trusting a plan's prose. The clauses now cite the typed-schema refusal criteria, and the clause no criterion verifies is marked inferred. The citation notation was two levels while the sub-clause model needs three, so the prescribed prepare citation tripped the criterion governing it. The note treatment was scoped to one closed-wave change document where the closed wave has two, both carrying derived statements. Red-team found a code-half defect no earlier round reached: nothing stated where the close orchestrator computes the blocking keyword, so computing it before the loop passes every criterion while failing the invariant for any blocker the loop itself produces; the computation point is now specified and a criterion drives it. The amendment criterion is restructured around two recorded tables with a no-empty-cell condition, because five rounds have shown a prose taxonomy of documents and clauses is the artifact that keeps being subtly wrong; Close-sensor approval precondition: Readiness repair round 3: five lanes reviewed, all blocked, and two of the round-2 repairs had relocated their defect rather than closed it. Three lanes independently found that repointing the layering row's Verified column to criteria covering only the new suppression path would leave the row citing criteria that verify none of the three clauses it asserts, and that AC-7's failure condition compelled that outcome; amendment is now clause-level and the column is repointed clause by clause. Two lanes found the split treatment had assigned the decision record to the notes class while Requirement 6 replaces two of its sentences, which cannot both be done; the record moves to the in-place class with its superseded wording preserved in an appended note, since its consequences paragraph is a current-state claim and a note beside it would leave a false sentence standing. Code review found that repointing prepare's closure deletes the only occurrence of a string wave `1uugg` pins in `server_impl.py`, so the pin is retargeted to the helper. Red-team found Requirement 2's single-implementation outcome had no criterion, so a correct third inline copy passed everything; AC-11 now asserts it structurally. Two lanes found the golden criterion needed the landed comparison repointed rather than a sibling added, since a sibling sorts after a test that regenerates the committed fixture. Three census claims did not re-derive: the shared-file count, the fixture-identity justification and the stale-receipt producer set; Close-sensor approval precondition: Readiness repair round 2: all four lanes blocked again. Three lanes independently found Requirement 5 and AC-7 jointly unsatisfiable: the derivation rule did not yield `1y0bd` AC-9, which AC-8 separately declares untouched, so an implementer would either fail a required criterion or inscribe a supersession note asserting a change this wave does not make. AC-9 and the `wf_prepare_wave` bullet are removed from the set and asserted unchanged by a new Requirement 8 and AC-10 instead. Red-team found that the tasks as written ship a double-spawning close, because the sensor gate remained a member of the iterated tuple while an explicit call was added after the loop, and no criterion counted runner invocations on the clean path; the loop form is now specified and AC-4 counts calls and rows. Architecture found that one amendment treatment applied to living documents would leave superseded text standing beside an annotation, and that the layering row's Verified column would point at criteria that no longer verify it; the treatment is now split by document class and the citation repointed. Architecture also found the Rationale's causal chain still one link wrong, its third round: the blocking diagnostic on an edited sensor command is `missing_wave_council_signoff` from the council gate, not a stale receipt, which is emitted only from policy-state errors. Red-team found AC-8 self-satisfying under the ambient regeneration variable, so the comparison now takes an empty environment. Three lanes found the same stale round-1 prose in the risks row, the wave record's retired count and the sequencing watchpoint's dead premise.

**Changes delivered:**

- **Close-sensor approval precondition** (`1yd98-enh close-sensor-approval-precondition`) — 11 ACs completed. Key decisions: Suppress execution only, leaving the pre-spawn `invalid` classification untouched, by making the precondition a conjunct on the gate's existing `mutating` predicate; Pass the blocking state as a keyword argument with a not-blocked default rather than as a context field
- **Phase-gate guard and documentation tidy-ups** (`1yd99-debt phase-gate-guard-and-doc-tidy-ups`) — 8 ACs completed. Key decisions: Collect the carried observations into one change rather than leaving them as notes; Leave the unreachable bare assertion alone
## Watchpoints

- Watchpoint: `1yd98-enh` reverses behavior specified by `1y0bd` Requirement 5 and pinned by its AC-2 and AC-6, both carrying recorded readiness approvals. Amendment is clause-level, and sub-clause level where a clause spans phases: only AC-2's close clause and the close portion of AC-6's mutating-outcome clause are touched, and the boundary row's Verified column is repointed to the five-row table `1yd98-enh` Requirement 5 specifies in full, rather than to a contract described in prose. Clause two is wholly inferred and clause one's exclusivity is inferred beside its citations. The amendment set is a derivation rule with a stated boundary, re-derived at implementation time with three instruments and recorded under an `## Amendment Record` heading in the change document rather than in the Progress Log, which is normalized out of the review-policy digest; a criterion fails if the derived set is empty or omits a named member. The treatment differs by document class, stated over the class rather than an instance because the closed wave has two change documents that both carry derived statements: a dated supersession note alone on a closed wave's change document, and in-place correction with the superseded wording preserved verbatim in an appended dated note on the decision record and every living document. `1y0bd` AC-9 is deliberately not a member and is asserted unchanged. It is also not cited by the repointed boundary row: citing it was tried and was wrong, because its own text scopes its scans to the row naming the extracted modules.
- Watchpoint: land `1yd98-enh` first. The original reason for this being a hard constraint is void, because `1yd98-enh` now performs no golden regeneration for `1yd99-debt`'s refusal to collide with. The surviving reasons are the shared surface named in the next watchpoint, and `1yd99-debt`'s ninth requirement, which discharges a carried observation by recording that `1yd98-enh`'s clause-by-clause repoint resolves it. Both keep those edits sequential rather than concurrent.
- Watchpoint: the two changes share five paths, re-derived from both Serialization Points lists. `tests/test_lifecycle_gates_structure.py` carries `1yd99-debt`'s scanner criterion and `1yd98-enh`'s gate-order pin. `tests/test_lifecycle_golden.py` carries `1yd98-enh`'s repointed comparison call and `1yd99-debt`'s regeneration refusal and fixture docstring. `docs/specs/mcp-tool-surface.md` and `docs/architecture/cross-cutting-concerns.md` carry sentences both changes edit. Three paragraphs are co-edited at sentence granularity: the `wf_prepare_wave` bullet, where `1yd98-enh` pins two sentences unchanged while `1yd99-debt` rewrites a third; the `wf_close_wave` bullet, where both change different sentences; and the cross-cutting read-only paragraph, where `1yd98-enh` amends the `would_run` binding and `1yd99-debt` rewrites the wrapper-refusal sentence. The `lifecycle_gates.py` and `server_impl.py` edits are disjoint regions.
- Watchpoint: `docs/specs/mcp-tool-surface.md` carries a docs-constants claim naming the configured-gate outcome vocabulary. A lint row pins it, so it must survive both changes verbatim.
- Follow-up, disclosed rather than fixed: on a legacy prose wave or one with no current policy receipt, no digest binds a declared sensor's command bytes at either phase, so such a wave closes clean and executes whatever it declares. `1yd98-enh` re-scopes the decision record's commit-hook sentence to that population instead of deleting it.
- Follow-up, deliberately excluded: the tool-surface golden carries the same self-healing regeneration as the lifecycle golden and has no frozen twin. Hardening it would change a documented workflow and is a separate decision.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| — | — | — | — | — |

*Machine review state — 0 findings; current: do_now 0, maybe_later 0, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| wave-council-readiness | approved | current executed approval by coryhacking follows every affected repair | none |
| code-reviewer | approved | current executed approval by coryhacking follows every affected repair | none |
| qa-reviewer | approved | current executed approval by coryhacking follows every affected repair | none |
| architecture-reviewer | approved | current executed approval by coryhacking follows every affected repair | none |
| docs-contract-reviewer | approved | current executed approval by coryhacking follows every affected repair | none |
| operator-signoff | approved | current executed approval by coryhacking follows every affected repair | none |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Review Checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-09-18: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, security-reviewer; rotating-seat: security-reviewer; strongest-challenge: the amendment criterion judged citation adequacy at implementation time and so rejected the very table its own requirement prescribed, in two consecutive rounds and in two different rows; replaying each already-repaired defect against the current criteria is what surfaced it, and the resolution was to specify the finished table in the requirement, pin its citations, and reduce the criterion to reproduction and locatability; strongest-alternative: keep the adequacy condition and repair the prescribed citation set instead, rejected because the condition had never once caught a bad citation while twice making the prescribed artifact unrecordable, and because pinning the set converts the check into string equality that an implementer cannot evade)

- **security-reviewer (rotating seat) — 2026-09-18: APPROVE, two low observations, neither blocking.** Traced the execution path end to end against the tree rather than the plan's account. The digest binding is genuine: `policy_input_digest` hashes `phase_gates` plus a name, command and dimension projection of every referenced sensor, `_read_project_sensors` normalizes to exactly those fields, and `run_sensor` consumes only `command` with the shell disabled and the working directory fixed, so the digest covers every execution-determining field. `_prepare_policy_state` recomputes it from the current config on every close and a mismatch becomes a non-advisory stale-receipt diagnostic inside `shared_delivery_gate`, which is the first shared gate and therefore accumulates before the hard-gate loop, so an edit to a declared sensor's command bytes after approval now withholds execution at close exactly as it already did at prepare. The precondition cannot become an execution path in the other direction, because the withholding decision and the close's refusal derive from the same monotonically growing diagnostics list. The seat's framing, adopted here: this is an integrity control against unreviewed drift, not an authorization boundary against a hostile caller, since anyone who can write the workflow config can also write the framework scripts. The residual population re-derived from the code predicates to exactly the two the change names, a legacy prose wave and a wave with no current receipt, with no third found. The single-site except clause preserves the fail-fast contention contract; the added clause is pre-write and fail-closed. The pre-spawn invalid classification is structurally unreachable by the precondition, since the misdeclaration branch precedes the conjunct. Observations recorded and not repaired: the keyword's default is fail-open, so a future third call site would execute unless it opts in, which no current caller does; and `subprocess_ops.sensor_timeout_seconds` is read at execution time and is not digest-bound, which can only shorten or lengthen a timeout rather than change which bytes execute.

## Dependencies

- No external wave dependencies.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| plan | 37 | 0 |
| implement | 6 | 31,420 |
| review | 26 | 48,024 |
| **Total** | **69** | **79,444** |

<!-- wave:context-efficiency-state {"generation":58,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":6,"content_source_credit":38656,"derived_artifact_credit":0,"direct_net":31420,"estimated_tokens_saved":31420,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":185,"response_debit":7051,"source_credit_count":7,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":0},"plan":{"calls":37,"content_source_credit":8309,"derived_artifact_credit":2678,"direct_net":-11177,"estimated_tokens_saved":0,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":1844,"response_debit":26252,"source_credit_count":4,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":5932},"review":{"calls":26,"content_source_credit":81226,"derived_artifact_credit":1139,"direct_net":48024,"estimated_tokens_saved":48024,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":7169,"response_debit":29174,"source_credit_count":16,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2002}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":69,"content_source_credit":128191,"derived_artifact_credit":3817,"direct_net":68267,"estimated_tokens_saved":79444,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":9198,"response_debit":62477,"source_credit_count":27,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":7934},"wave_id":"1yd97 phase-gate-follow-ups"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 1 | 0 | 1 | 19,131 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":1,"estimated_exploration_avoided":19131,"surfaced_events":1} -->
<!-- wave:exploration-avoided end -->

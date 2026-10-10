# Waveforge follow-up council readiness synthesis

Owner: Engineering
Status: active
Last verified: 2026-10-08
Wave: `204mp waveforge-follow-up`

Phase: readiness. Verdict: **PASS for C1–C5 admissibility**.
Receipt: `review-policy-5de6f84316a3a4bf9e13`.
Chair context: `204mp-independent-chair-20261008-final`.

## Merit-first synthesis

Seat 1 supplies a coherent, bounded case: the explicit upstream inventory separates ownership from checkout presence; a frozen historical encoder avoids a circular digest oracle; actor recognition preserves canonical authority and repair identity; exact destination-span migration preserves custom content and discovers unfinished work on retry. These are implementable requirements with negative controls, not assertions that new behavior already exists. No findings in my lane: I read the three current admitted plans, their required ACs and dependencies, the retained C6 plan, and current evidence, and found no concrete unresolved implementation choice or contradictory requirement in C1–C5.

Seat 1's strongest caution is retained as implementation guidance: inventory updates must catch omitted zero-hit owned files; runtime collision checks must include configured and wave-declared roles; link repair cannot reuse the existing reporter unchanged. These obligations already follow from the requirements. No specialist blocking finding is softened or waived.

## Attribution and independence

Seat 1 is the configured docs-contract-reviewer Phase 2/rotating alternative seat, supplied by the independent specialist context in [readiness-specialists.md](readiness-specialists.md). The configured council roster is red-team plus docs-contract-reviewer; I do not claim four additional fixed council seats ran. Its code, QA, architecture, security and docs-contract judgments are five dimensions from one context, not five independent confirmations. The separate red-team primer and closing reconciliation are in [readiness-primer.md](readiness-primer.md). The typed ledger lists all five specialist approval records under their disclosed shared context.

The chair authored no plan, implementation or repair. Prior conclusions were visible during mandatory orientation and synthesis; I do not claim a blind pre-primer chair read. Independence rests on my direct inspection of current plans, scope and the executed current-boundary checks below, not on accepting a prior PASS. The specialist's pre-primer read and primer-effect statement are recorded in its report. With only one Phase 2 seat there is no cross-seat phrase comparison or independent consensus count. Shared primer framing and repeated compatibility tests are correlated evidence of the same seam.

Actual primer depth was **full**, with five stances and three questions, appropriate for authority and project-document write boundaries. Generated receipt metadata says **standard** because the current prepare implementation fixes that value; this report discloses the difference and neither edits it nor claims it was corrected. `seat_agreement_aggregate`: `seat_agreement=unanimous`, `max_severity=none`, bounded to the single configured Phase 2 seat. No challenge-round trigger exists.

## Primer reconciliation and alternatives

The strongest original challenge was the unspecified pre-relocation journal-presence predicate. I directly checked that original change 204mo remains admitted to planned 206is with its source-location task, risk and all four required ACs unchecked. The three current plans neither introduce that trigger nor depend on its implementation. C2 uses a controlled source for the existing hook contract. The C6 question remains pending and is not waived.

Question 2 is answered by 204mm requirements 1–4: validate runtime role/operator collisions, maintain one canonical repair identity, keep the digest's built-in historical moderator spelling independent, and prove actual reload and byte-preserved replay at delivery. Question 3 is answered by 204mn's contained current-state retry, explicit syntax/history exclusions and destination-only edit requirements, alongside 204ml's zero-hit ownership inventory and explicit update command. The specialist probes support feasibility; complete new-alias and parser behavior remains unimplemented.

The strongest alternative is to hold all public changes until C6's location is settled. It would be better if the retained three plans depended on that new trigger. Direct plan inspection shows no such dependency, so it adds delay without resolving an in-scope defect. Broad Markdown serialization and dynamic downstream census enumeration are also weaker than the selected narrow edits and upstream inventory because they alter unrelated bytes or conflate ownership. For C6 itself, the primer's smallest explicitly authorized source predicate remains preferable to recursive guessing.

| Recommendation | Disposition | Reason |
| --- | --- | --- |
| Proceed with the three admitted plans after readiness is recorded | Implementation note | No current blocker demonstrated; all product ACs remain delivery obligations. |
| Exercise zero-hit omission, configured-role collision and completed-move retry controls | Implementation note | These are high-value negative controls already required by the selected contracts. |
| Preserve C6 pending location decision in 206is | Retained separate work | Scope split preserves the original change ID and requirements; it does not complete or waive them. |
| Treat repeated judgments as independent votes | Rejected interpretation | One Phase 2 seat and one shared specialist context cannot supply five corroborating reviewers. |

Finding synthesis: empty current C1–C5 candidate set, consistent with the recorded readiness run and red-team closing reconciliation. This table contains implementation notes, not invented typed findings or a second actionability vocabulary.

## Chair-executed evidence

I discovered and successfully invoked MCP code_read and code_keyword, inspected the existing test methods, then ran this command in a fresh process:

```sh
PYTHONPATH=.wavefoundry/framework/scripts:.wavefoundry/framework/scripts/tests python3 -B -m unittest -v test_council_signoff_keys.LifecycleCompatibilityTests.test_old_actor_input_writes_the_new_actor test_council_signoff_keys.LifecycleCompatibilityTests.test_a_legacy_key_approval_replays_after_the_rename test_council_signoff_keys.LifecycleCompatibilityTests.test_a_legacy_key_approval_with_different_evidence_is_a_conflict
```

Observed: **3 tests passed in 4.454 seconds, zero skips**. The faithful boundary is `wf_server.server_impl.wf_review_event_response` through `LifecycleCompatibilityTests`. Existing legacy actor input produced canonical actor records; identical historical requests replayed without changing ledger bytes; deliberately changed evidence under the same identity returned `review_event_identity_conflict` and preserved the ledger. Canonical fresh-context writes and legitimate replay supply adjacent controls. Failure of any canonicalization, byte equality or conflict assertion would falsify this bounded current-seam proposition.

Known-bad method: `readiness-safe-control`, the deliberately conflicting evidence request. The five integrity booleans are true for this chair's readiness evidence: test_ran_without_unintended_skip, public_path_reached (the named faithful boundary), boundary_values_realistic, assertions_non_vacuous and known_bad_detected. The execution was local_safe and authorized; safe_boundary=false, unexecuted_remainder_prohibited=false, universal_claim=false. Test fixtures confine writes to temporary roots and mock garden/docs-validation/publication support. This does not prove the full MCP transport, whole-tree lint, newly declared aliases, real reload or delivered product behavior. No full suite or live-server reload ran.

Specialist E1–E6 and red-team's four-test closing replay are attributed evidence only; I did not execute those groups. Their residual delivery obligations remain exactly as disclosed in those reports. No source or plan edits, activation, closure, commit or push are part of this chair review.

### Falsification Check

Working verdict is PASS for C1–C5 readiness. The strongest counterargument is that splitting C6 could conceal a dependency on its unresolved predicate; the current three plans retain the existing journal contract and independent actor/link/oracle scopes, while 204mo retains the unresolved decision in 206is. That argument does not change the verdict. Readiness approves admissibility only; implementation still owes every unchecked product AC and independent delivery evidence.

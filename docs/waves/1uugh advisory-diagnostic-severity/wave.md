# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-08-10
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1uugh advisory-diagnostic-severity`
Title: Advisory Diagnostic Severity

## Objective

Make a diagnostic able to say something without failing the call. `wf_prepare_wave_response` currently decides failure by `if diagnostics:`, so an informational signal either fails the preview or has to be hand-routed around the gate at every return site.

## Changes

Change ID: `1uugg-debt advisory-diagnostics-need-a-severity`
Change Status: `implementing`

## Participants

- Coordinator: <wave coordinator>
- Write-owning roles: <roles selected during Prepare wave>
- Requested review lanes: none
- Required review lanes: code-reviewer, qa-reviewer, docs-contract-reviewer

Completed At: 2026-08-10

## Wave Summary

Wave `1uugh advisory-diagnostic-severity` (Advisory Diagnostic Severity) delivered one change: Diagnostics Conflate Information With Failure. Notable adjustments during implementation: Diagnostics Conflate Information With Failure: THREE-LANE REVERIFICATION after the coordinator became a co-author. Splice damage independently cleared: an AST diff of all 34,431 lines against HEAD found ZERO methods removed anywhere, and each of the four restored tests is mutation-killed rather than merely present. QA ran 23 mutants; the three operator-found defects are all genuinely fixed, and AC-5c's `>= 3` probe bound was judged TIGHT rather than a proxy — `.get("advisory")` is read at exactly one place with exactly three call sites, the fixture holds one dict so `any()` cannot short-circuit, and the measured count is exactly 3; Diagnostics Conflate Information With Failure: TWO LANES CONVERGED on a fix of this wave breaking a fix of `1upba`: the `policy_state is not None` guard added for Requirement 8 made `1upba`'s `_seen_stale` dedupe UNREACHABLE, because entering the block forces `policy_state_errors == ()` and the two producers become mutually exclusive. Deleting the dedupe survived all 55 tests, and the surrounding comments still asserted the old two-producer mechanism. Dedupe and comments removed; the test survives its mechanism, re-founded on the property that still holds; Diagnostics Conflate Information With Failure: The FIRST splice deletion, previously referenced but never recorded. It happened in wave `1usqm` while folding that wave's delivery findings: a line-index splice removed the AC-6, AC-8 and AC-10 tests from `WaveCouncilPolicyTests`, caught only when the class count fell 34 to 31, and restored by anchored edit. It is recorded there in `1upba`'s Progress Log; noted here because this wave's own row called itself "the second of this session" against an event a reader of this document could not find.

**Changes delivered:**

- **Diagnostics Conflate Information With Failure** (`1uugg-debt advisory-diagnostics-need-a-severity`) — 15 ACs completed. Key decisions: Name the field `advisory: bool`, not `severity`; Omit the key at default rather than always emitting it
## Watchpoints

- **Sequencing watchpoint:** this change deletes `_prepare_stale_advisories`, which wave `1usqm` ships, and both edit overlapping regions of `wf_prepare_wave_response` in an uncommitted `server_impl.py`. The binding constraint is file-level: do not start until `1usqm`'s implementation is settled and its suite is green. Closure is NOT required, and **no edit to `1usqm`'s record is made or needed** — an earlier revision required closure, which would have guaranteed the record was a closed archive at edit time, the one place `AGENTS.md` most clearly forbids deleting historical mentions.
- **The default must be blocking.** The field is `advisory: bool = False`, omitted from the payload at default — an earlier revision called it `severity`, which collides with an entrenched five-level finding scale. Many diagnostics in the tree are unclassified; an advisory default would silently convert unreviewed blocking conditions into non-blocking ones across every gate at once. AC-2 pins this and is written first.
- **Three sites get tagged, not one.** Folding `_ac_advisories` into the shared list means `ac_priority_unpopulated` and the dry-run `prepare_council_verdict_missing` must both carry the tag, or prepare starts failing on conditions that today only decorate a successful envelope.
- **Follow-up, deliberately deferred:** extending the advisory model to the other lifecycle gates. Prepare is the measured case; generalize only once this one is proven.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| — | — | — | — | — |

*Machine review state — 0 findings; current: do_now 0, maybe_later 0, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-08-10: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, security-reviewer; rotating-seat: security-reviewer; strongest-challenge: an advisory field claimed as global would falsely promise payload changes for existing lifecycle-focus and review-evidence conventions, while a truthiness predicate would let malformed internal values bypass a prepare gate; strongest-alternative: migrate every non-blocking diagnostic through a global census, declined as a materially broader change than the measured prepare repair)
- **Seat evidence [red-team/code-reviewer] — 2026-08-10:** APPROVE after fresh independent re-verification. The plan requires literal `diagnostic.get("advisory") is True`, exact three prepare-only tag sites, four unchanged receipt-helper callers, and conversion of all three prepare consumers including the publication write guard. Runtime baseline was intentionally not claimed by this seat because a full-suite probe did not complete. Context: `1uugh-code-reverify-20260810-advisory-literal-three-sites`.
- **Seat evidence [security-reviewer/docs-contract-reviewer] — 2026-08-10:** APPROVE after fresh independent re-verification. Requirement 6, Scope, AC-9, and AC-10c now consistently make the public contract prepare-local, preserve historical non-blocking payload shapes, and fail closed for `False`, `"false"`, and `1`. Docs validation passed. Context: `ctx-1uugh-readiness-reverify-20260810-02`.
- **Seat evidence [qa-reviewer] — 2026-08-10:** APPROVE after fresh independent re-verification. The two public-path lifecycle baseline tests passed (2/2); AC-2 malformed-value, return-helper, three-consumer, and site-isolation tests are feasible in the existing fixtures. Context: `1uugh-qa-readiness-reverify-20260810`.
- **Prepare-phase Wave Council [prepare-council] — 2026-08-09: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, docs-contract-reviewer, security-reviewer; rotating-seat: security-reviewer; strongest-challenge: the plan's central premise was FALSE — it claimed the shared `diagnostics` list reaches every return, and an AST walk found 8 returns of which only 3 forward it, with two of the droppers constructing fresh lists after both gates, so the proposed fix would have reproduced the defect at two new sites; strongest-alternative: amend the claim and simply require the two post-gate returns to forward the shared list — declined because it repairs the instance rather than the class, and the same failure recurs the next time a return is added, which is precisely the defect this change exists to remove)
- **Seat evidence [red-team] — 2026-08-09:** WITHHELD with four P1s and three lower findings, all folded. P1-1 falsified the Rationale's central claim by AST walk, re-derived independently on two byte snapshots because mutation testing was live. P1-2: `if diagnostics:` is three reads, not one, and `if _mutating and policy_state is not None and not diagnostics:` is a WRITE guard for receipt publication — a blocking-only filter decouples skipped-publication from failed-call and would let a `create` run activate a wave with an unpublished receipt while returning `ok`. P1-3: `review_policy_receipt_stale` has 10 emit sites and is emitted inside prepare both as the advisory and as two genuine blockers, so code-scoped tagging fails open; two existing code-keyed registries would also silently contradict a per-diagnostic field. P1-4: AC-6 was unsatisfiable, its zero-hit census matching the plan's own prose. Verified accurate: `LIFECYCLE_ENGAGED_STATUSES` excludes `error`, the 15-key/10-key envelope measurement, and 384 `_diagnostic` call sites unaffected by a defaulted keyword parameter.
- **Seat evidence [docs-contract-reviewer] — 2026-08-09:** WITHHELD with two P1s and seven lower findings, all folded. P1s convergent with red-team on AC-6, on two independent grounds: the zero-hit census counts prose that must survive, and the watchpoint clause directed an edit that `AGENTS.md` *Cleanup and Destructive Operations* prohibits, restated in four seeds, with the wave's own sequencing guaranteeing the record would be a closed archive at edit time. Also: `severity` collides with an entrenched five-level review-finding scale shipping in the same envelope as `data.max_severity`, renamed to `advisory: bool` omitted at default; `_ac_advisories` is a third list the plan never mentioned and the only one the success return emits, so the stated mechanism was unreachable; Requirement 4 named a file but no heading and deferred a decision decidable at plan time; and a coverage trace found the public-contract Requirement pinned by no AC. Verified clean: Serialization Points parses to exactly its three intended targets with no prose leakage, and the plan self-applies today's symbol-anchor rule with zero bare line citations.
- **Seat evidence [security-reviewer] — 2026-08-09:** WITHHELD with one P1 and four lower findings, all folded. P1: Requirement 2 was factually wrong about where the advisory is emitted — the pending-mint dict is constructed in `_review_policy_receipt_diagnostics`, a shared helper with FIVE callers, four of which treat it as blocking. Tagging that construction would stamp `advisory: true` on diagnostics blocking at three other tools and plant a fail-open for the named follow-on wave, and AC-10 pinned the two sites that were not the problem. Also found that Requirements 3 and 4 described two different designs, under which all eleven ACs pass with zero gate conversion; that AC-5 was half-pinned with no negative twin on the publication write; that AC-2's predicate used tokens from the abolished `severity` design; and that nothing enforced site-scoping against drift. Recorded explicit no-issue findings on the two code-keyed registries (correctly left alone, fail closed), on external influence (no diagnostic dict on prepare's path originates outside the process), on AC-5's outcome being the safe one, and on the `1usqm` watchpoint carrying no integrity dependency.
- **Seat rotation note:** the rotating seat moved from `docs-contract-reviewer` to `security-reviewer` when the fold changed the canonical change text, since seat selection binds to it. Both were run; the docs-contract evidence above is from the pre-fold text and its findings are all folded.
- **Fold disclosure:** every P1 and P2 was folded before this verdict. The seats did **not** re-review the folded text. The plan was re-founded rather than patched — the fix moved from "put advisories on the other list" to "no return site constructs a diagnostics list at all" — so the delivery-phase lanes review a materially different design from the one the seats saw.

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| wave-council-readiness | approved | current executed approval follows every affected repair | none |
| wave-council-delivery | approved | current executed approval follows every affected repair | none |
| code-reviewer | approved | current executed approval follows every affected repair | none |
| qa-reviewer | approved | current executed approval follows every affected repair | none |
| docs-contract-reviewer | approved | current executed approval follows every affected repair | none |
| operator-signoff | approved | current executed approval follows every affected repair | none |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Dependencies

- Wave `1usqm citation-durability-and-receipt-integrity` must land first: this change deletes code that wave ships, in a file both edit.

<!-- wave:context-efficiency begin -->
## Context Efficiency

Estimated token savings use phase-unique returned source versions and mapped workflow prompts, minus recorded request and response tokens. Saved model output or avoided tool loops count only through quality-equivalent paired evidence.

| Stage | Tool calls | Estimated token savings |
| --- | ---: | ---: |
| plan | 33 | 854,992 |
| implement | 25 | 1,501,983 |
| review | 70 | 1,447,003 |
| **Total** | **128** | **3,803,978** |

<!-- wave:context-efficiency-state {"generation":123,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":25,"content_source_credit":1626605,"derived_artifact_credit":0,"direct_net":1501983,"estimated_tokens_saved":1501983,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":520,"response_debit":126015,"source_credit_count":11,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1913},"plan":{"calls":33,"content_source_credit":937419,"derived_artifact_credit":1037,"direct_net":854992,"estimated_tokens_saved":854992,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":2060,"response_debit":87100,"source_credit_count":50,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":5696},"review":{"calls":70,"content_source_credit":1695332,"derived_artifact_credit":2147,"direct_net":1447003,"estimated_tokens_saved":1447003,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":4702,"response_debit":247120,"source_credit_count":34,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1346}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":128,"content_source_credit":4259356,"derived_artifact_credit":3184,"direct_net":3803978,"estimated_tokens_saved":3803978,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":7282,"response_debit":460235,"source_credit_count":95,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":8955},"wave_id":"1uugh advisory-diagnostic-severity"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 7 | 0 | 2 | 3,518,666 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":2,"estimated_exploration_avoided":3518666,"surfaced_events":7} -->
<!-- wave:exploration-avoided end -->

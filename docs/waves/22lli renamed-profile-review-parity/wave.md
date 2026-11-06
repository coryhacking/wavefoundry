# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-11-06
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `22lli renamed-profile-review-parity`
Title: Renamed Profile Review Parity

## Objective

Renamed distributions retain meaningful review, authority-path and generated-hook checks without false failures from default vocabulary. Preserve strict default oracles and rejection behavior; repair only the scoped assertions and one diagnostic.

## Changes

Change ID: `22llh-bug renamed-profile-review-and-hook-parity`
Change Status: `implemented`

## Participants

- Coordinator: Primary coordinator
- Write-owning roles: implementer (coordinator; narrow, coupled test and wording repair)
- Requested review lanes: none
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer

Completed At: 2026-11-06

## Wave Summary

Wave `22lli` closed on 2026-11-06 with change `22llh` implemented, all four ACs and all tasks complete, and no deferrals or unresolved findings. The repair preserves strict default instruction and hook checks while testing effective profile vocabulary; production changes only the escaped-record diagnostic. Default, renamed and declared-extension suites and both exact comparisons pass. Current readiness, delivery and operator approvals are recorded. Closure reused the matching green framework receipt and removed the verified owned work area. No duplicate memory was created because maintained tests and architecture guidance retain the lessons. Existing binary and long-line scanner coverage limits remain disclosed.

Intent outcome: achieved for the admitted motivating cases. Nine affected methods pass under default, second and declared profiles; six deliberate regressions are rejected, including hardcoded nouns, altered authority, weakened grounding and an unrelated hook byte. Full qualification passes in all three profiles, with both exact comparisons passing. The repair preserves the historical default digest oracle, tests effective vocabulary separately and changes only the escaped-record diagnostic in production. This establishes scoped renamed-profile parity, not native Windows qualification or a real downstream installation result. Independent QA confirmed this assessment and all four required ACs before the final profile runs; those later runs required no source repair.

**Changes delivered:**

- **Preserve review and hook checks across renamed profiles** (`22llh-bug renamed-profile-review-and-hook-parity`) — 4 ACs completed. Key decisions: Select profile-aware assertions, preserved default oracles and one production wording correction.; Run cheap affected checks first, then normal full qualification once the repair is stable.
## Watchpoints

- Watchpoint: do not weaken checks, rebaseline golden hashes or add profile skips. Preserve unrelated website and local-build edits. No scanner, seed or profile-runner changes.

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
| council-readiness | approved | current executed approval by coryhacking follows every affected repair (local account: coryhacking) | none |
| council-delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| code-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| qa-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| architecture-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| operator-signoff | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Dependencies

- No external wave dependencies. Declare intra-wave dependencies with a `Depends On:` line containing full backticked change ids in each change's block under `## Changes`.

## Review Checkpoints

2026-11-06: Closure reconciliation: the operator explicitly requested close, commit and push. All four required ACs and all tasks are complete, with no intentional deferrals. Readiness and delivery approvals remain current; delivered scope introduces no additional reviewer lane. Docs-contract review ran with architecture, and no specification file changed. The six reviewed paths still match the frozen candidate. Reuse the current green default receipt and the passing profile comparisons; no additional suite or review cycle is needed for closure bookkeeping.

2026-11-06: Retrospective and retention: separate the unchanged default instruction oracle from effective-profile assertions, and restrict hook adaptation to the declared base-to-effective noun. Maintained tests and testing-architecture.md already carry these lessons and their negative controls, so no duplicate memory is warranted. memory_propose returned zero eligible candidates and created nothing. Decisive results, mutation descriptions and limitations are retained here and in the admitted change; typed approvals remain in events.jsonl. All six disposable baseline snapshots equal HEAD, so Git preserves their preimages. Canonical close may remove the owned work area; profile reports remain in the ignored qualification cache. No unique proof depends solely on the disposable files.

2026-11-06: Intent outcome: achieved for the admitted motivating cases. Nine affected methods pass under default, second and declared profiles; six deliberate regressions are rejected, including hardcoded nouns, altered authority, weakened grounding and an unrelated hook byte. Full qualification passes in all three profiles, with both exact comparisons passing. The repair preserves the historical default digest oracle, tests effective vocabulary separately and changes only the escaped-record diagnostic in production. This establishes scoped renamed-profile parity, not native Windows qualification or a real downstream installation result. Independent QA confirmed this assessment and all four required ACs before the final profile runs; those later runs required no source repair.

| Full qualification | Tests | Files | Existing skips | Seconds |
| --- | ---: | ---: | ---: | ---: |
| Default | 12,485 | 221 | 12 | 716.508 |
| Renamed (`second`) | 12,467 | 221 | 30 | 700.315 |
| Declared extension | 12,485 | 221 | 12 | 705.813 |

Commands: `run_tests.py --qualification-report <report>` for default, adding `--profile second` or `--profile declared` for the other rows. Reports are `.wavefoundry/cache/qualification/22lli-{default,second,declared}.json`. `qualification_report.py --compare <default> <candidate> --profile <name>` returns `equal=true` for both profiles: renamed retains 18 existing default-only cases; declared has none. All commands exit zero. The canonical default receipt remains green with inputs `67a67641b3d521a84201c9d318c66ab5d99255154c35956e47d613cd4709cb63`; profile-copy runs do not replace it. No new skip or allowance was introduced.

Readiness PASS on review-policy-08bce7906989f3824f48: code/QA share one independent context, docs-contract/architecture another; isolated red-team primer and closing reconciliation found no blocker. Chair rejected a test-only repair census; code/QA executed the existing authority test (default pass, renamed known-bad assertion failure without errors/skips); architecture rejected a shipped-Change assumption using the actual base/effective overlay. Separate default oracles and effective expectations address the strongest alternative. Actual model identities are unobserved; grouped remits are correlated. Delivery remains to be verified.

Work allocation: coordinator owns the small coupled implementation. Independent readiness and delivery roles use separate contexts under the council protocol. Current inherited model/effort is suitable for this bounded code-and-test review; actual runtime identity is not independently observed. Disposable work: `.wavefoundry/work/22lli/`; no per-seat durable reports.

2026-11-06: Delivery PASS. Fresh code, QA and architecture approvals and `council-delivery` are recorded in the typed ledger; the Council's intent verdict is `establishes`. Standard-depth isolated red-team primer came first. The receipt-selected Council seats were red-team and docs-contract; no rotating fifth seat was required by this targeted roster. Code/QA shared one independent context; architecture/docs-contract shared another. Their pre-primer reads focused on test invariants and base-profile identity respectively; the primer confirmed those concerns. These grouped remits are correlated, not four independent samples. The chair weighed the complementary controls by merit, then reconciled the empty finding set with red-team. No disagreement or required repair remained; actual runtime model identities were not verified.

| Independent check | Candidate result | Known-bad result |
| --- | --- | --- |
| Red-team: actual council-brief method in the existing second-profile fixture | One test passes | Replace typed approval with narrative approval only in typed instructions: four assertion failures |
| Code/QA: actual council-brief and authority-path methods in second profile | Two tests pass | Hardcode the admitted item noun to `change`: three effective-profile assertion failures while the default oracle passes |
| Architecture/docs-contract: actual hook-parity method with active base `Proposal`, then second overlay `Wave` | One test passes | Change copied committed hook `MAX_INPUT_BYTES` from 16384 to 32768: one byte-comparison assertion failure |
| Chair: actual authority-path method with process-local container `Cycle` | One test passes | Restore the pre-repair authority function in memory: one assertion failure |

All targeted positive and mutant runs above had zero errors and zero skips. Reproduce through `LifecycleHintGapTests.test_council_brief_points_at_the_record_that_counts`, `ReviewAuthorityFacadeTests.test_symlinked_and_escaping_authority_keeps_existing_messages` and `HookVenvMismatchTests.test_committed_rendered_hooks_match_the_renderer`, using the existing repository-copy/profile-application helpers; each mutation is specified in the table. The synthetic base fixture changes the active base asset and corresponding committed noun before applying the overlay; it never regenerates the committed hook to conceal drift. Probes used temporary copies or process-local patches, and all six reviewed source blobs matched candidate `e9b746357d882960c29f12e35feeb398ccd5cce8d86a8db16f07f2f9b783726a` before and after review. No whole-file or full-suite review rerun was needed. The initial code/QA probe stopped at an incorrect probe mutation anchor; correcting that anchor after MCP lookup produced the reported result, without changing product source.

Falsification check: the strongest argument against approval was that vocabulary adaptation could hide a broken producer. The hardcoded-item, typed-authority and unrelated-hook mutants were each rejected, while the three historical digest literals remain unchanged. The best alternative—freezing all expectations to default names—would miss effective-name defects; broader normalization would mask drift. The chosen separate checks preserve both obligations. This approval covers the admitted repair; completion of the full profile matrix remains a separate task and carries no native Windows or actual downstream-installation claim.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| plan | 145 | 3,149,792 |
| implement | 30 | 3,366 |
| review | 61 | 837,654 |
| **Total** | **236** | **3,990,812** |

<!-- wave:context-efficiency-state {"generation":135,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":30,"content_source_credit":22192,"derived_artifact_credit":0,"direct_net":3366,"estimated_tokens_saved":3366,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":1242,"response_debit":21108,"source_credit_count":2,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3524},"plan":{"calls":145,"content_source_credit":3596416,"derived_artifact_credit":1923,"direct_net":3149792,"estimated_tokens_saved":3149792,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":10240,"response_debit":443815,"source_credit_count":95,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":5508},"review":{"calls":61,"content_source_credit":955033,"derived_artifact_credit":1040,"direct_net":837654,"estimated_tokens_saved":837654,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":7295,"response_debit":114902,"source_credit_count":31,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3778}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":236,"content_source_credit":4573641,"derived_artifact_credit":2963,"direct_net":3990812,"estimated_tokens_saved":3990812,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":18777,"response_debit":579825,"source_credit_count":128,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":12810},"wave_id":"22lli renamed-profile-review-parity"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 10 | 0 | 10 | 4,596,827 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":10,"estimated_exploration_avoided":4596827,"surfaced_events":10} -->
<!-- wave:exploration-avoided end -->

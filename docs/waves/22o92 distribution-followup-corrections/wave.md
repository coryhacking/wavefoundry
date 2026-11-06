# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-11-05
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `22o92 distribution-followup-corrections`
Title: Distribution Followup Corrections

## Objective

Operators and downstream maintainers receive visible, selected-repository setup recovery in an identified shell, truthful setup planning, and portable verification that respects distribution profiles. A skill-name conflict blocks only that name while unrelated eligible skills continue rendering. Preserve storage/provider safeguards, filesystem ownership and operator authority; scanner changes and release publication are outside this wave.

## Changes

Change ID: `22o8y-bug bootstrap-recovery-and-policy-currency`
Change Status: `implemented`

Change ID: `22o8z-bug distribution-profile-and-diagnostic-followups`
Change Status: `implemented`
Depends On: `22o8y-bug bootstrap-recovery-and-policy-currency`

Change ID: `22o90-bug isolate-declared-skill-name-collisions`
Change Status: `implemented`

## Participants

- Coordinator: root
- Write-owning roles: unassigned until Prepare wave
- Requested review lanes: code-reviewer, qa-reviewer, architecture-reviewer, security-reviewer, performance-reviewer, docs-contract-reviewer
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer, release-reviewer, performance-reviewer, security-reviewer

Completed At: 2026-11-06

## Wave Summary

Delivered three changes: bootstrap-safe setup recovery and policy-aware preparation; distribution-compatible carriers and bounded diagnostics; collision-local skill rendering. All 12 ACs and all tasks are complete, with no deferrals or actionable findings. Required technical lanes and Council approve. The operator explicitly authorized closure, commit and push; canonical closure succeeded on 2026-11-06 using the current combined green 12,411-test receipt. The owned work area was removed after preserving decisive evidence and the final delivery manifest.

## Watchpoints

- Watchpoint: establish the shared bootstrap-safe command/formatting seam in 22o8y before 22o8z adopts it in affected platform tests. Serialize shared setup, renderer, test and changelog edits.
- Keep the policy finding bounded: policy-only planning omitted maintenance in the observed replay; newly eligible files were correctly planned. An unsafe native-preparation bypass remains unproven.
- Collision-local failure must preserve files at the conflicting name and all existing path/ownership safety refusals. Report partial rendering truthfully.
- Record actual platform evidence. Controlled Windows formatting and aliases do not establish native Windows or Git Bash qualification.
- The scanner plan 22o91 and the earlier README/public-documentation edits are not admitted here. Preserve those uncommitted changes and the unrelated :memory:.ses artifact.
- The operator authorized implementation of both waves and pausing this wave after delivery to continue with 22o93. Closure, commit, push, package and release remain outside the current request.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| D92-consumer-test-expectations | do_now | no | completed | qa-reviewer |
| D92-delegate-fixture-dependency | do_now | no | completed | qa-reviewer, code-reviewer, architecture-reviewer |
| D92-helper-registration | do_now | no | completed | code-reviewer, architecture-reviewer, qa-reviewer |
| D92-hook-length-reason | do_now | no | completed | qa-reviewer |
| R92-generated-hook-targets | do_now | no | completed | code-reviewer, architecture-reviewer, qa-reviewer, docs-contract-reviewer, release-reviewer |

*Machine review state — 5 findings; current: do_now 5, maybe_later 0, dont_do_later 0, not_issue 0*
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
| docs-contract-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| release-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| performance-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| security-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| operator-signoff | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Dependencies

- No external wave dependency. 22o8z consumes the command/formatting seam from 22o8y; 22o90 has no hard dependency, but its shared renderer and changelog edits must be serialized.

## Review Checkpoints

2026-11-06: Closure retrospective and memory checkpoint. The operator explicitly authorized closing both waves, then committing and pushing them. The current combined receipt passes 12,411 tests across 218 files, with 12 expected skips. Decisive consumer controls, negative controls, reviewer conclusions and limitations remain in these checkpoints, the admitted plans, typed ledger and maintained tests. The final delivery manifest is retained in evidence/delivery-manifest.json; detailed work-area logs and reviewer notes are disposable.

The MCP memory proposal call refused because its loaded index producer is stale; in-process reload did not clear that boundary. The same public memory_propose_response handler in a fresh process completed read-only for this wave and proposed zero candidates, omitting source records without a current contained source target. No actual wave-linked memory candidate exists. No proposal was forced or promoted: existing canonical contracts and maintained regression tests carry the actionable lessons. No setup, live index rebuild or model operation ran.

Non-obvious lesson: a shared bootstrap helper also needs reload registration, flat-script ownership and delegated-child fixture inclusion. The corresponding regressions now exercise these consumers. Canonical suite qualification must freeze lifecycle accounting as well as source until process exit; the earlier guard-refused run remains distinct from the later green receipt. Native Windows and an actual older-Python host remain unqualified.

2026-11-06: Final delivery Council PASS, unanimous, worst intent_fit establishes across all three changes and Objective. Seven typed technical approvals are current. Final canonical EXIT0 qualifies manifest 5a542918f10139bc9b99224b14e9d20f4589cf49: 12,400 tests / 218 files / 575.668 seconds / 12 expected skips; receipt inputs_hash 2e773a18ef0cde23bd5bf478dcb01125cbf9eab7c5f16df94c63a0640231553a, ran_at 2026-11-06T08:19:29.063440+00:00. All nonignored files stayed frozen through exit. This supersedes the earlier red and guard-refused attempts without erasing them. All ACs/tasks complete, gates closed, no native Windows/Git Bash/actual Python3.9 or field-adoption claim. Operator closure signoff is not inferred.

2026-11-06: Focused delivery verification of the launcher amendment passes on manifest 5a542918f10139bc9b99224b14e9d20f4589cf49 (62 targets). Code/architecture/performance, QA, security and docs/release each independently execute the 11 emitted-launcher tests. Separate omitted-layout, omitted-notice and raw-newline-notice controls are rejected; these tests invoke the public wrapper through PATH and preserve explicit targets, help and exit behavior. Docs/release verify fresh-render parity and actual packaging inclusion. Reality attributes those executions and confirms the operator's intended convenience without trusting arbitrary cwd. No new finding; all prior repair records are terminal. Required technical verdicts are conditional only on final canonical qualification. Gates are closed and every nonignored path, including lifecycle accounting, now freezes for that run. Operator closure signoff remains pending and is not inferred from implementation authority.

2026-11-06: The operator's public-launcher clarification amended only 22o8y R8, required AC-5, its task/priority and decision. Seven focused readiness lane approvals and standard-depth Council PASS establish the amended intent on receipt ec9dafffac39fc15bf44; canonical Prepare succeeds with no pending readiness lanes. Independent emitted POSIX launchers invoked through PATH selected their owner from foreign directories without notice and still invoked an observer interpreter with a missing dispatcher. Explicit spaced targets and caller files stayed intact. These baseline defects justify the bounded guard-and-notice repair. Code/architecture/performance share one nonauthor context, docs/release share one, QA and security are separate, and reality attributes the independent observations. Anonymous merit weighting preceded identity reveal. New launcher delivery remains unqualified; previous unaffected delivery evidence is retained.

2026-11-06: The repaired canonical retry passed all 12,396 worker tests across 218 files in 572.737 seconds, with 12 expected skips. Receipt publication was refused because lifecycle accounting changed wave.md and events.jsonl during execution; refusal 915a9244ca7c4028939fc5d1a7ffc51a is preserved. This is worker evidence, not a green receipt. The launcher amendment requires a new settled-tree run. That run will freeze every nonignored path and suspend MCP accounting and lifecycle writes until completion.

2026-11-06: Independent delivery checks are complete on the final bounded delta, pending canonical qualification. Code and architecture shared one actual reviewer context with the supplemental performance lane: 47 initial tests, 13 registration checks plus retained-wrapper lookup, and five bounded cost checks; bare-launcher, policy-removal, registration-removal and old shared-budget mutants fail. QA ran 39 initial tests, the real delegate/omission pair, and 26 final integration checks; purge/census/length-branch controls detect their defects and preserve precision/no-embedding/publication assertions. Security ran 21 initial tests, then eight final tests plus two declaration controls, rejecting quoting, collision-protection and omitted-registration mutations. Docs-contract and release shared one actual context: 24 initial and seven final tests, shell-label and missing-pack-owner controls; the actual pack collector includes the new helper. The separate reality seat ran seven hook/helper tests and a selected-root counterexample; its initial conditional assessment relies on the affected specialists for the narrow final repairs. These five Council contexts are independent of implementation, not different model-family or human evidence. Native Windows, Git Bash, actual Python 3.9 and field adoption remain unqualified.

2026-11-06: The first canonical suite ran 12,396 tests across 218 files and was red in five modules. Typed cycle-3 findings separate missing helper registration, preserved hook diagnostic cause and existing consumer-test expectations. Repairs followed the frozen review reports; no acceptance criterion or runtime safeguard was weakened. The final 62-source-path manifest is 16274db06378b27b4cd82a1047bd8104925d5403. All five Council seats completed their initial independent assessment without another defect; required affected lanes now perform focused reverification while the settled canonical suite reruns.

2026-11-06: Delivery tree frozen across 65 declared source/contract/generated targets at git-blob manifest fingerprint e2b008ab587a100ac81b3c954bbe8a824aafe560. Final canonical surface sync writes nothing. Chair selected full primer depth for bootstrap, policy observation and filesystem ownership boundaries; isolated adversarial primer precedes fixed seats. Root runs the single settled-tree canonical suite while read-only reviewers inspect the same target set. No native Windows/Git Bash or actual older-Python claim.

2026-11-06: Intent outcome: the controlled consumer checks support the intended recovery, distribution and collision-local outcomes. Setup planning now observes policy currency; generated diagnostics retain the selected root and shell metadata; renamed carriers and default golden checks pass; bounded hints reach Downloads; unrelated skills render while conflicted bytes survive. These establish the specified behavior in temporary fixtures, not field adoption, native Windows/Git Bash execution or actual older-Python qualification. The canonical suite and independent delivery lanes remain pending; QA must confirm or correct this assessment before delivery.

2026-11-05: Implementation allocation: cross-cutting implementer bootstrap owns 22o8y's command/currency/caller integration; implementer skills owns 22o90's typed collision partition and renderer integration. Coordinator owns 22o8z carrier/golden/platform integration and shared documentation; root owns its model-hint and token-wording functions/tests. Shared renderer/server/upgrade writes are serialized by explicit messages. The inherited capable model is suitable for these coupled correctness boundaries; actual child runtime model/effort is unverified. Required independent delivery reviews follow frozen integration and the canonical suite. User explicitly authorized pausing this delivered wave before implementing 22o93, without closure or commit.

2026-11-05: Prepare wave — focused readiness verdict PASS on review-policy-a986f4d156d7838c90da. All seven required lanes approved in fresh focused turns: code and architecture shared readiness_codearch_22o9; QA readiness_qa_22o9; security readiness_security_22o9; docs-contract readiness_docs_22o9; performance and release shared readiness_perfrelease_22o9. Fixed reality readiness_reality_22o9 also approved. The independent readiness_chair_22o9 synthesized unanimous focused agreement, no remaining blocker, worst intent_fit establishes across 22o8y, 22o8z, 22o90 and the Objective. Same actual reviewers performed the focused turns; none authored the repair. This is one bounded repair and one focused verification after the initial full review, not another full panel investigation. Typed readiness approvals and the terminal five-lane repair chain are in events.jsonl.

Readiness evidence retained: actual generated outputs omitted by the original target list were Cursor after-file-edit.py, seed-warn.py, framework-plan-warn.py and docs-lint.py; Copilot pre-tool-use.py and post-tool-use.py; Windsurf seed-protect.py and docs-lint.py. Initial independent code/docs executions and the focused release execution enumerated these eight outputs. The amended Serialization Points and required AC-4 now cover them. Actual bootstrap controls printed the warning with a working diagnostic import and lost it at a simulated missing-tomllib boundary. Actual temporary index execution showed policy-only dry-run current while real generation advanced from 1 to 2; newly eligible files were correctly planned, so an unsafe embedding bypass was not reproduced. Actual renamed-template carriers raised FileNotFoundError, a crowded hint search missed Downloads while its direct control found the bundle, and a mixed declared-skill render globally aborted before creating the unrelated eligible skill. These are baseline defect and plan-efficacy controls; candidate fixes do not exist yet.

The rotating fallback-only alternative was explicitly weighed by fixed seats and chair: it repairs silence but leaves selected-root and shell-dialect obligations unmet. A bounded standard-library command owner with visible fallback and finite carrier parity remains proportionate. No native Windows/Git Bash, actual older-Python interpreter, live setup/index/models, field improvement or new full-suite qualification is claimed. Work snapshots retain detailed disposable notes; this checkpoint and typed records retain their conclusions and decisive observations.

2026-11-05: Initial full-depth readiness review completed. Four distinct fixed seats (architecture/code, QA, security, reality) and rotating docs-contract received the isolated red-team primer; supplemental performance/release shared one actual context. Anonymous merit weighting preceded identity reveal. R92-generated-hook-targets is the sole demonstrated blocker, source/blocking lanes code, architecture, QA, docs-contract and release. The chair records majority written verdicts with one shared medium-severity integration gap, not a disagreement about its blocking status; no challenge round. Typed repair_start preceded the plan-only amendment. The repair adds three existing hook directories and explicit AC-4 parity; all generated/source files remain unchanged. One focused verification follows on the new receipt; no second automatic repair round.

2026-11-05: Operator admitted exactly 22o8y, 22o8z and 22o90. Admission preserves the explicitly selected collision-local skill behavior and excludes scanner work. Operator acknowledgment selects collision-local refusal with preserved conflicting files; independent review must verify that the planned outcomes honor that choice. No independent admission approval is claimed. Other changes repair existing contracts without selecting a new product destination. Required technical lanes and Council authority are determined and recorded by Prepare wave.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| plan | 264 | 1,737,807 |
| implement | 145 | 4,850,303 |
| review | 568 | 7,826,424 |
| **Total** | **977** | **14,414,534** |

<!-- wave:context-efficiency-state {"generation":807,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":145,"content_source_credit":5030511,"derived_artifact_credit":1270,"direct_net":4850303,"estimated_tokens_saved":4850303,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":4803,"response_debit":182063,"source_credit_count":131,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":5388},"plan":{"calls":264,"content_source_credit":2346949,"derived_artifact_credit":6611,"direct_net":1737807,"estimated_tokens_saved":1737807,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":29579,"response_debit":595770,"source_credit_count":132,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":9596},"review":{"calls":568,"content_source_credit":8513747,"derived_artifact_credit":69560,"direct_net":7826424,"estimated_tokens_saved":7826424,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":35954,"response_debit":1191852,"source_credit_count":320,"source_credit_drop_count":0,"structural_source_credit":470923,"workflow_prompt_credit":0}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":977,"content_source_credit":15891207,"derived_artifact_credit":77441,"direct_net":14414534,"estimated_tokens_saved":14414534,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":70336,"response_debit":1969685,"source_credit_count":583,"source_credit_drop_count":0,"structural_source_credit":470923,"workflow_prompt_credit":14984},"wave_id":"22o92 distribution-followup-corrections"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 110 | 0 | 44 | 46,049,808 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":44,"estimated_exploration_avoided":46049808,"surfaced_events":110} -->
<!-- wave:exploration-avoided end -->

# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-10-27
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `21w0b wave-work-device-drift`
Title: Wave Work Device Drift

## Objective

A wave's work area stays usable across a reboot or remount that renumbers the device: open waves still see it, focused re-review snapshots still load, and close still removes it. A different directory or an unreadable ownership record is still refused and preserved.

## Changes

Change ID: `21vug-bug wave-work-ownership-device-drift`
Change Status: `implemented`

## Participants

- Coordinator: main session
- Write-owning roles: implementer (coordinator)
- Requested review lanes: code-reviewer, qa-reviewer, security-reviewer
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, security-reviewer

Completed At: 2026-10-27

## Wave Summary

Wave `21w0b` (Wave Work Device Drift) delivered one change: Wave Work Ownership Survives Device Drift. Notable adjustments during implementation: Wave Work Ownership Survives Device Drift: Observe: fresh independent code/QA/architecture/security and full-depth Council delivery approved; empty finding set, unanimous/max severity none, intent established in controlled macOS execution. Corrected registered old-comparator injection detected an availability assertion failure; initial injection displaced by load_server is excluded. All source hashes unchanged. No scope gap, intentional deferral or implementation blocker remains.; Wave Work Ownership Survives Device Drift: Readiness repair. QA blocked: `compare_identity` accepts a zero inode on path alone, which would turn the existing `[0, 0]` refusal into acceptance; code, architecture and security raised the same point. Requirement 1 now requires an exact two-integer shape, nonzero inodes and `basis: path+inode`; AC-3 lists the malformed cases. Red-team found the deliberately strict retired-graph site the first census missed; recorded with a Decision Log row and kept out of scope. Also: call-site count, Requirement 3 coverage, `test_wave_work.py` in scope, platform list corrected, generation named as the main inode-reuse mitigation.

Intent outcome: achieved in controlled macOS execution. Registered lifecycle tests prove device-only drift preserves open-wave availability and permits owned cleanup, retained reopen rotates generation, and snapshot bytes still load. Fifteen invalid persisted shapes/identities remain refused with scratch preserved; live zero inode is also refused. Four deliberate regression controls fail their targeted assertions. Canonical run passed 12,288 tests across 214 files; current green framework receipt b5ec21c5124b52f65164e966b812519d73e7616198174f12f2644c51800bc6bf. QA is assigned independent intent validation. Physical reboot/remount and Linux/WSL/native Windows execution were not performed; post-release absence of leftover work is not yet observable.

**Changes delivered:**

- **Wave Work Ownership Survives Device Drift** (`21vug-bug wave-work-ownership-device-drift`) — 5 ACs completed. Key decisions: Work-area ownership tolerates device drift while retired-graph deletion stays strict; Use `storage_identity.compare_identity` for the recorded directory identity inside `_read_owner`
## Watchpoints

- Watchpoint: wave `21uny` is OPEN; this wave is readied only and cannot be implemented until `21uny` closes.
- Watchpoint: the change touches deletion authority; within-operation identity checks must stay strict on device and inode.

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
| security-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| operator-signoff | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
<!-- wave:review-status end -->

- Operator authorized closure, commit and push on 2026-10-27; typed operator-signoff recorded.

## Dependencies

- No external wave dependencies. Declare intra-wave dependencies with a `Depends On:` line containing full backticked change ids in each change's block under `## Changes`.

## Review Checkpoints

2026-10-27: Closure retrospective: persisted device numbers are historical evidence, while same-operation device/inode checks protect deletion. The shared comparator's zero-inode path fallback must not authorize wave-work ownership. These lessons are now captured by maintained tests, the bounded identity census and threat-model guidance; memory_propose returned no candidates and no duplicate memory is needed. Unique probe recipes, source fingerprints and qualification outcomes are retained here and in the change record; routine logs and source-copy controls in .wavefoundry/work/21w0b are disposable and eligible for owned close cleanup. All five ACs and tasks are complete with no intentional deferrals. The historical 21uny activation watchpoint was resolved before implementation. Current operator request authorizes closure, commit and push.

2026-10-27: Delivery complete: all five ACs/tasks and required code/QA/architecture/security approvals current; full-depth Council approved intent_fit establishes with unanimous agreement/max severity none and no findings. Isolated red-team primer, fixed architecture/security/QA/reality seats, rotating docs-contract alternative, separate code lane, anonymous-first synthesis and red-team closing completed. Fixed seats all weighed the optional maintained live-device-only substitution regression; no stronger implementation alternative or current defect was found. Architecture/security saw the primer in their initial packets and claim no uncontaminated pre-primer prior; QA/reality recorded artifact-only reads before the primer. Repeated shared-fixture controls are correlated corroboration. Requested gpt-6.1-sol/high, runtime identity unverified. Operator signoff/closure and commit remain unrequested.

2026-10-27: Falsification check: device tolerance could otherwise authorize deletion after substitution, but unchanged live-device checks preserve scratch and deliberately inode-only live mutants remove it. The accepted copied-record plus replacement-volume/inode ambiguity remains; generation guards stale cleanup, not copied-record authenticity. AC scope gap check: no missing required/important scope or intentional AC deferral. Optional future work is a maintained precise live-device substitution test and real reboot/remount/platform execution; no follow-on work was admitted. Canonical qualification remains green: 12,288 tests / 214 files / 12 skips / 547.670s; no source edit since qualification.

2026-10-27: Independent delivery probes retained here for reproduction: create a temporary repository and canonical wave record, call ensure_work, retain its generation and owner bytes, change only the recorded device, then exercise describe_work and cleanup_work with stale/current generations. For the live-device control, intercept descriptor-relative stat at the cleanup entry checkpoint for the owned wave directory only, returning unchanged inode/mode but device+1; the current code must return preserved with work_identity_changed and retain scratch. An isolated runtime _same replacement comparing only inodes makes that same preservation assertion fail by removing scratch. Architecture/security independently executed these probes and 38 maintained work tests each; repeated controls are corroboration, not additional distinct coverage. Durable wave records survive valid cleanup. No shared source mutation or external path deletion occurred.

2026-10-27: Required code lane independently passed seven targeted checks (6.767s) plus the syntax guard (0.210s); source-copy restoration of strict persisted comparison caused two intended assertion failures. QA independently passed six targeted checks including registered lifecycle, 15 malformed initial-close cases, snapshot and syntax guard, then killed registered strict-comparator and source syntax-guard controls. Both confirmed unchanged five-file fingerprints. An initial registered mutation injection was displaced by fixture module loading and excluded; corrected post-setUp or source-copy injection supplied the counted detection. Shared maintained fixtures remain a common-mode limitation; independent transformations and live-device probes supplement them.

2026-10-27: Intent outcome: achieved in controlled macOS execution. Registered lifecycle tests prove device-only drift preserves open-wave availability and permits owned cleanup, retained reopen rotates generation, and snapshot bytes still load. Fifteen invalid persisted shapes/identities remain refused with scratch preserved; live zero inode is also refused. Four deliberate regression controls fail their targeted assertions. Canonical run passed 12,288 tests across 214 files; current green framework receipt b5ec21c5124b52f65164e966b812519d73e7616198174f12f2644c51800bc6bf. QA is assigned independent intent validation. Physical reboot/remount and Linux/WSL/native Windows execution were not performed; post-release absence of leftover work is not yet observable.

2026-10-27: Current-request plan review found no unresolved decision branch. Prior independent readiness approvals remain current on receipt d394fa3c93191afcd614; Prepare ready passed and Implement opened the wave. The historical 21uny watchpoint is resolved: that wave is closed and committed. Operator authorization is review and implementation only.

2026-10-27: Work allocation: one implementer owns the five admitted paths, including tests and the threat-model sentence; coordinator integrates and runs canonical qualification; fresh independent code/QA/architecture/security lanes and delivery Council follow on the frozen tree. Requested gpt-6.1-sol/high for the narrow identity/deletion-authority implementation and review tasks; actual runtime identity unverified. Work area .wavefoundry/work/21w0b is available. No closure, commit or host restart inferred.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| plan | 24 | 67,768 |
| implement | 219 | 545,444 |
| review | 19 | 468,346 |
| **Total** | **262** | **1,081,558** |

<!-- wave:context-efficiency-state {"generation":264,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":219,"content_source_credit":379443,"derived_artifact_credit":501,"direct_net":545444,"estimated_tokens_saved":545444,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":12310,"response_debit":478006,"source_credit_count":49,"source_credit_drop_count":0,"structural_source_credit":652558,"workflow_prompt_credit":3258},"plan":{"calls":24,"content_source_credit":134629,"derived_artifact_credit":3007,"direct_net":67768,"estimated_tokens_saved":67768,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":8801,"response_debit":69753,"source_credit_count":24,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":8686},"review":{"calls":19,"content_source_credit":109860,"derived_artifact_credit":460,"direct_net":468346,"estimated_tokens_saved":468346,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":2749,"response_debit":37265,"source_credit_count":16,"source_credit_drop_count":0,"structural_source_credit":394351,"workflow_prompt_credit":3689}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":262,"content_source_credit":623932,"derived_artifact_credit":3968,"direct_net":1081558,"estimated_tokens_saved":1081558,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":23860,"response_debit":585024,"source_credit_count":89,"source_credit_drop_count":0,"structural_source_credit":1046909,"workflow_prompt_credit":15633},"wave_id":"21w0b wave-work-device-drift"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 4 | 0 | 3 | 2,692,108 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":3,"estimated_exploration_avoided":2692108,"surfaced_events":4} -->
<!-- wave:exploration-avoided end -->

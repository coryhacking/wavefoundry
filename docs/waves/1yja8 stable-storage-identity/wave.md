# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-09-19
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1yja8 stable-storage-identity`
Title: Stable Storage Identity

## Objective

Restore index, setup observation and interrupted-upgrade access after filesystem device renumbering across reboot, while preserving identity refusal for genuinely different paths or available inodes.

## Changes

Change ID: `1yhhs-bug stable-storage-identity-across-reboots`
Change Status: `complete`

## Participants

- Coordinator: wave-coordinator
- Write-owning roles: implementer
- Requested review lanes: code-reviewer, qa-reviewer, architecture-reviewer, security-reviewer, docs-contract-reviewer
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer, security-reviewer

Completed At: 2026-09-19

## Wave Summary

Wave `1yja8` (Stable Storage Identity) delivered one change: Stable Storage Identity Across Reboots And Platforms. Notable adjustments during implementation: Stable Storage Identity Across Reboots And Platforms: Readback: device-only drift accepts unchanged path/available inode without restamping; differing nonzero inode and path still refuse. AC-1–8 cover helper, migration, setup, upgrade and retrieval consumers. Example: historical device 16777231 with live 16777233 becomes readable with bytes preserved. Scope excludes exact persisted bindings and within-run races. Thought: implement helper first, migration and setup/upgrade in disjoint implementer lanes, then retrieval, regression guards and architecture documentation; integrate and verify before delivery review.

**Changes delivered:**

- **Stable Storage Identity Across Reboots And Platforms** (`1yhhs-bug stable-storage-identity-across-reboots`) — 8 ACs completed. Key decisions: Operator selected path plus available inode with replacement-volume ambiguity documented; Operator selected no restamping; preserve pure reads and existing records
## Watchpoints

- Watchpoint: preserve standing recovery receipts and index data; no manual receipt repair or index rebuild.
- Existing unrelated dirty files and other planned waves remain outside this effort.
- Framework edits require the framework gate and recorded readiness.
- Use the shared tool venv for dependency-bearing tests; index health currently reports storage identity mismatch and stale loaded code, so use live source reads rather than indexed claims.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| STORAGE-D1 | do_now | no | completed | security-reviewer, code-reviewer, wave-council-delivery |
| STORAGE-R1 | do_now | no | completed | wave-council-readiness |
| STORAGE-R2 | do_now | no | completed | wave-council-readiness |
| STORAGE-R3 | do_now | no | completed | wave-council-readiness |

*Machine review state — 4 findings; current: do_now 4, maybe_later 0, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| wave-council-readiness | approved | current executed approval by coryhacking follows every affected repair | none |
| wave-council-delivery | approved | current executed approval by coryhacking follows every affected repair | none |
| code-reviewer | approved | current executed approval by coryhacking follows every affected repair | none |
| qa-reviewer | approved | current executed approval by coryhacking follows every affected repair | none |
| architecture-reviewer | approved | current executed approval by coryhacking follows every affected repair | none |
| docs-contract-reviewer | approved | current executed approval by coryhacking follows every affected repair | none |
| security-reviewer | approved | current executed approval by coryhacking follows every affected repair | none |
| operator-signoff | approved | current executed approval by coryhacking follows every affected repair | none |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Dependencies

- No external wave dependencies.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| plan | 57 | 745,475 |
| implement | 7 | 137,399 |
| review | 151 | 3,352,638 |
| **Total** | **215** | **4,235,512** |

<!-- wave:context-efficiency-state {"generation":171,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":7,"content_source_credit":141492,"derived_artifact_credit":0,"direct_net":137399,"estimated_tokens_saved":137399,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":117,"response_debit":5879,"source_credit_count":3,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1903},"plan":{"calls":57,"content_source_credit":891338,"derived_artifact_credit":965,"direct_net":745475,"estimated_tokens_saved":745475,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":26774,"response_debit":123695,"source_credit_count":50,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3641},"review":{"calls":151,"content_source_credit":3624840,"derived_artifact_credit":641,"direct_net":3352638,"estimated_tokens_saved":3352638,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":30088,"response_debit":244757,"source_credit_count":121,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2002}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":215,"content_source_credit":4657670,"derived_artifact_credit":1606,"direct_net":4235512,"estimated_tokens_saved":4235512,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":56979,"response_debit":374331,"source_credit_count":174,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":7546},"wave_id":"1yja8 stable-storage-identity"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 9 | 0 | 6 | 2,449,121 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":6,"estimated_exploration_avoided":2449121,"surfaced_events":9} -->
<!-- wave:exploration-avoided end -->
## Review Checkpoints

- Product-owner: N/A — internal recovery correctness bug; operator explicitly requested admission, preparation, review and implementation.
- Work allocation: coordinator owns wave records and integration; independent red-team primer and implementer/Guru census run read-only before code edits. Readiness specialists run in fresh contexts; implementation work will be serialized where file ownership overlaps. Inherited capable model fits recovery-contract ambiguity.
- Gapfill: index_health reports storage_receipt_identity_mismatch and loaded_code_stale. No rebuild is attempted as a workaround; MCP live reads and fresh-process probes provide evidence.

- Readiness review — 2026-09-19: BLOCKED on explicit identity-contract decisions; typed findings STORAGE-R1–R3 recorded. Independent full-depth red-team and security/architecture assessment recommend path plus available inode with a documented same-path/replacement-volume collision limitation, and pure reads with no restamping. Operator questions are pending; no framework code or standing recovery record changed.
- Strongest challenge: path plus inode cannot distinguish reboot from a different volume exposing the same path/inode; unavailable inode further weakens discrimination. Strongest alternative: pure shared continuity comparison, preserve every independent ownership/schema/package/continuation check, report comparison basis separately. Keeping zero-new-false-accepts requires a larger stable-volume/legacy recovery design.
- Restamp evidence: observer writes contradict setup_readiness's read-only contract; read_restart_action binds receipt/checkpoint/action identity equality; setup_reconciliation also binds a completed parent receipt hash. Preserve both on-disk and returned stored identity shapes unless an explicit owner transaction is designed.
- Census before implementation: sqlite_storage_migration persisted root/published/source/work/artifact comparisons; setup_readiness receipt/action/checkpoint live comparisons; setup_reconciliation.SetupReconciliation._inspect; upgrade_extensions._validate_index_guard_handoff; retrieval_eval._compare_index_identity (a real gate, with distinct same-generation versus cross-generation store identity rules). Exclude within-run snapshots/race checks and strict persisted-to-persisted continuity bindings. Path binding stays with validated root/index locators and artifact roles so staged-to-live rename remains valid.
- Independent evidence: red-team temporary real-receipt probes reproduced device-only refusal with unchanged bytes and old-reader refusal of enriched identity mappings. Replacement-volume ambiguity was simulated, not mounted. Live MCP source reads established observer and continuation contracts; no unimplemented behavior is claimed. Supporting identity semantics: Python os.stat_result documentation (https://docs.python.org/3/library/os.html#os.stat_result) and Linux inode documentation (https://man7.org/linux/man-pages/man7/inode.7.html) scope inode uniqueness to its filesystem/device.
- Next action: receive operator choices on continuity guarantee and restamp scope, record repair starts before amending the plan, then run one focused independent readiness verification and finish Prepare before activation/implementation.

- Operator decision — identity contract: use path plus available inode and document same-path/reused-inode replacement-volume ambiguity. STORAGE-R1 repair started and plan guarantee narrowed accordingly. Restamping decision remains pending; implementation has not started.

- Operator decisions complete: omit restamping and preserve recovery bytes/returned mappings; accept documented path-plus-available-inode ambiguity. STORAGE-R1–R3 plan repairs are applied for focused independent verification. No framework edits yet.

- **Prepare-phase Wave Council [prepare-council] — 2026-09-19: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, security-reviewer; rotating-seat: security-reviewer; strongest-challenge: replacement volumes can reuse inode and restamping breaks bound recovery records; strongest-alternative: persistent volume identification with legacy recovery). Red-team findings STORAGE-R1–R3 independently reverified after explicit operator decisions; security approves scoped continuity with pure reads. Evidence is recorded in the typed ledger. Security and synthesis share one author-independent context; code/architecture/docs/QA share another, disclosed due host thread cap, not isolated votes.

- **Delivery review, 2026-09-19:** Standard primer challenged independent package authority at the new bootstrap load. STORAGE-D1 was confirmed by temporary archive replacement, repaired with validation before loading plus a single digest-checked byte buffer, and independently cleared by code/security. Review roles share one author-independent context under the host thread cap; these are not isolated votes. No unresolved source blocker or scope deferral remains. Final QA/council await the post-repair full-suite receipt.

- **Delivery-phase Wave Council [delivery-council] — 2026-09-19: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer, security-reviewer; rotating-seat: security-reviewer). Shared author-independent context disclosed above. STORAGE-D1 independently terminal; all required ACs verified with no deferrals. Final current-tree framework receipt is green at 9376 tests with 21 aggregate skips; required targeted regressions pass. Operator signoff, commit and closure remain pending operator review.

## Closure Reconciliation

- Operator explicitly requested review and closure; current typed operator approval is recorded. All specialist and council approvals are current and all four findings are terminal.
- All eight required ACs and every task are complete; no deferred changes or `[~]` ACs. Close applies final change status, completed date and wave chronology.
- Docs-contract review passed; no product spec changes. Full docs validation passes and the framework test receipt is current (9376 tests, 21 disclosed aggregate skips).
- Memory checkpoint completed: no pending candidates. Three generated fragile-file claims were rejected because they confused plan repairs with repeated source repairs; no duplicate memory was promoted.
- Retrospective: the non-obvious boundary is identity lifetime. Persisted-versus-live comparison tolerates device drift, while within-run races and exact persisted bindings stay strict. Incoming helper execution must use the exact archive bytes whose digest was verified. Durable identity rationale, accepted volume ambiguity and pure-read policy are in ADR 1yja8 and cross-cutting architecture documentation.
- Handoff will be idle with this last-closed wave and the delivered continuity fix. Open operational note: the restarted MCP now accepts device drift, but index generation 1729 is interrupted with no build lock; recovery is an index-build retry, outside this closure. Retired-JSON graph test skips remain separate test debt.
- No commit requested or created. No unresolved tree-moved finding; framework edit gate is closed.


## Original-plan reconciliation

Reconciled on 2026-09-20: the original `1yhhs-bug` adopt-and-restamp proposal was superseded during readiness by the operator's explicit choices. Wave `1yja8` completed the amended path-plus-available-inode contract with pure reads, historical device values and accepted replacement-volume/reused-inode ambiguity. Restamping was intentionally removed before implementation, not delivered or left as an untracked task. See the change document's Original-plan reconciliation and the accepted storage continuity ADR. Closed status and historical review evidence are unchanged.

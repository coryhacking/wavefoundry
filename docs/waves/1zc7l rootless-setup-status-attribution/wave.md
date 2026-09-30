# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-09-29
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1zc7l rootless-setup-status-attribution`
Title: Rootless Setup Status Attribution

## Objective

Pin the resolution of CR-L1 (1za2y delivery review): a reused background-build pid held by a rootless `wf setup` in another repository reads as completed, through wave `1zc7n`'s start-time guard.

## Changes

Change ID: `1zc7k-bug rootless-setup-pid-attributed-to-any-repository`
Change Status: `complete`

## Participants

- Coordinator: wave-coordinator
- Write-owning roles: implementer
- Requested review lanes: none
- Required review lanes: code-reviewer, qa-reviewer

Completed At: 2026-09-29

## Wave Summary

Wave `1zc7l` (Rootless Setup Status Attribution) delivered one change: A Setup Run Counts Only For The Repository It Was Stamped For. Notable adjustments during implementation: A Setup Run Counts Only For The Repository It Was Stamped For: Rescoped: operator agreed that wave `1zc7n`'s start-time guard resolves CR-L1; the identity stamp is deferred and this change adds a regression test only.

**Changes delivered:**

- **A Setup Run Counts Only For The Repository It Was Stamped For** (`1zc7k-bug rootless-setup-pid-attributed-to-any-repository`) — 2 ACs completed. Key decisions: Defer the identity stamp; pin the `1zc7n` start-time guard with a regression test; Record pid, root and start time when stamping; scrape working directories only for older stamps
## Watchpoints

- Watchpoint: wave `1zc7n process-info-psutil` is closed; this wave relies on its `_pid_started_after` guard.
- Watchpoint: no production code changes; the stamp format is unchanged.

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
| wave-council-delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| code-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| qa-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| operator-signoff | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Review Checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-09-29: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, architecture-reviewer, security-reviewer; rotating-seat: security-reviewer; strongest-challenge: the resolution rests on the pid file's modification time as the stamp time, which moves with clock skew (WSL2 drvfs) or anything touching the file; accepted as status-only, recorded in Risks; strongest-alternative: a minimal identity stamp holding the exact start time of the stamped pid, recorded in the Decision Log as the revisit path)
  - red-team: no writer or reader bypasses `_pid_started_after`; both `setup_index` writers stamp while the process owns the pid (an unreaped POSIX child or an open Windows handle keeps it); `index_build_status_response`, `index_health` and the dashboard go through `_background_build_status`.
  - architecture-reviewer: reuses the 1zc7n seam rather than adding a second identity mechanism; the deferred sibling stamp stays compatible with bare-integer readers.
  - security-reviewer: test-only, no new input, file or privilege surface; an unreadable start time of another user's reusing process fails safe toward `running` (status-only, never a lock or spawn decision); without psutil liveness reads not running and the OS lock decides.

- **Delivery review and Wave Council — 2026-09-29: PASS** (moderator: wave-council; primer-depth: lightweight; fixed seats: code-reviewer, qa-reviewer, architecture-reviewer, security-reviewer; rotating fifth seat: documentation/contract review). Host-native orchestration used three independent-of-implementation reviewer contexts plus the coordinator: code and QA each had a worker; the primer worker subsequently held the architecture and security seats; the coordinator moderated and held the rotating documentation seat. These were not five isolated reviewer contexts. No reviewer implemented or repaired this wave.
  - Frozen reviewed tree: `test_server_tools_retrieval.py` `50bbdba641621a513989216c186d03b89801c3b2`; `server_tools_support.py` `7abc0bb6b30e6659af9bd0b2d965bb85e4e04510`; `wf_server/index_handlers.py` `e6b0aaebe085bf04cfdff72bc9a95a8510d889bc`. Fingerprints matched before and after the bounded review; no code edits landed.
  - Strongest challenge: a mutation installed before `setUpClass/load_server` could patch a discarded module and falsely survive. Strongest alternative: initialize the class first and patch the predicate's actual loaded guard. Each worker independently executed the targeted baseline and this post-initialization mutation; baseline passed and the mutant failed only the final assertion (`running != completed`), with no errors or skips. The primer worker additionally observed the real guard return `False`, then `True` for the current and backdated stamps. Code and QA addressed the primer directly; architecture and security agreed this faithfully exercises the existing advisory status seam.
  - Mutation table: actual `_pid_started_after` replaced by constant `False` after class initialization → the new regression fails; no surviving mutant and no expanded whole-file sweep. Code also observed a real foreign child cwd, unequal to the queried temporary root, with no `--root` argument. QA and coordinator each ran `BackgroundBuildStatusTests`: 11 tests passed, no skips. Both required ACs are verified; no deferred or unverified required AC was introduced.
  - Architecture/security: no producer, stamp-format, lock-ownership, input-trust or privilege change. Temporary process and stamp fixtures are cleaned up. Rotating documentation seat: retain the explicitly deferred exact-identity stamp and the documented two-second/clock-skew/unavailable-start-time limitations; this test pins the guard, not real kernel PID recycling or exact repository identity. No material disagreements or findings remained.
  - Execution limitations: current macOS tree tested; native Windows and WSL2 were inspected, not executed. MCP retrieval reported a stale-loaded-code advisory, so executable conclusions used fresh Python subprocesses and matching disk fingerprints, not indexed semantic results. The canonical runner verified the existing full-suite receipt as current: 10,070 passed at `2026-09-30T00:04:10Z`; this review did not rerun the whole suite. Operator signoff remains pending; no closure or commit is authorized by this review.

## Dependencies

- No external wave dependencies. Declare intra-wave dependencies with a `Depends On:` line containing full backticked change ids in each change's block under `## Changes`.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| plan | 19 | 1,185,197 |
| implement | 41 | 890,122 |
| review | 51 | 453,237 |
| **Total** | **111** | **2,528,556** |

<!-- wave:context-efficiency-state {"generation":120,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":41,"content_source_credit":967665,"derived_artifact_credit":734,"direct_net":890122,"estimated_tokens_saved":890122,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":2212,"response_debit":76065,"source_credit_count":29,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":0},"plan":{"calls":19,"content_source_credit":1201605,"derived_artifact_credit":3101,"direct_net":1185197,"estimated_tokens_saved":1185197,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":1458,"response_debit":21860,"source_credit_count":35,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3809},"review":{"calls":51,"content_source_credit":592496,"derived_artifact_credit":467,"direct_net":453237,"estimated_tokens_saved":453237,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":6180,"response_debit":135862,"source_credit_count":22,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2316}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":111,"content_source_credit":2761766,"derived_artifact_credit":4302,"direct_net":2528556,"estimated_tokens_saved":2528556,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":9850,"response_debit":233787,"source_credit_count":86,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":6125},"wave_id":"1zc7l rootless-setup-status-attribution"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 11 | 0 | 10 | 4,622,043 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":10,"estimated_exploration_avoided":4622043,"surfaced_events":11} -->
<!-- wave:exploration-avoided end -->

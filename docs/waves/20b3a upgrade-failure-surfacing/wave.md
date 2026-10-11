# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-10-10
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `20b3a upgrade-failure-surfacing`
Title: Upgrade Failure Surfacing

## Objective

Make upgrade failures diagnosable: the log opens before the first failure point, MCP output keeps its error tail, child index and graph output is captured, and pause and refusal messages name the CLI resume and accounting-gap clear commands. Driven by a field upgrade where the real error was hidden for hours.

## Changes

Change ID: `20b33-enh upgrade-failure-surfacing-log-and-child-output`
Change Status: `implemented`

Change ID: `20b34-enh upgrade-cli-resume-and-gap-clear-guidance`
Change Status: `implemented`
Depends On: `20b33-enh upgrade-failure-surfacing-log-and-child-output`

## Participants

- Coordinator: wave coordinator (Engineering)
- Write-owning roles: implementer (upgrade runner, MCP handler, setup reconciliation, tests, docs)
- Requested review lanes: qa-reviewer, architecture-reviewer, security-reviewer, docs-contract-reviewer
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer, release-reviewer, security-reviewer

Completed At: 2026-10-10

## Wave Summary

Wave `20b3a` (Upgrade Failure Surfacing) delivered two changes: Upgrade Failure Surfacing: Early Log, Output Tail, and Index Child Output and Upgrade CLI Resume and Accounting-Gap Clear Guidance. Notable adjustments during implementation: Upgrade Failure Surfacing: Early Log, Output Tail, and Index Child Output: Round-2 repair from the confirming readiness reviewers: late `mode="w"` open removed and post-open exits closed, new contained create-or-append helper, tee mechanism decided (`isolated_popen`, drained reader, `PYTHONUNBUFFERED=1`), redaction moved to the tee path, tail-preserving envelope, additive `error_tail` compatibility, retention of 5 runs, census anchors corrected, module registration, CHANGELOG AC. Product Intent: waived (bug-and-diagnostics change with no product scope; no change doc of this kind carries the section and docs-lint does not enforce it).; Upgrade Failure Surfacing: Early Log, Output Tail, and Index Child Output: Readback: a failure that formerly vanished past the output cap will survive in head+marker+tail output and additive error_tail; fresh logging starts after the lifecycle lock, child output is continuously teed to contained, redacted logs retaining five run groups. Scope is diagnostics only; phase ordering, publisher authorization, exit semantics and the old-runner window remain. Expected files: contained_files, new child_tee, upgrade runner/handler, module roster, focused tests, spec and CHANGELOG.; Upgrade Failure Surfacing: Early Log, Output Tail, and Index Child Output: Census: additionally include surface rendering, permissions backstop and pruning because they hide stderr reasons. Generic _run has no live caller and metadata-only _count_committers stays excluded. New child_tee is in extension roster and actual collect_files inventory plus a temporary MANIFEST; no setup-path import was added, so SOURCE_FILES is unchanged. Architecture data/control flow names neither upgrade-log timing nor output bounding; no architecture edit needed.

**Changes delivered:**

- **Upgrade Failure Surfacing: Early Log, Output Tail, and Index Child Output** (`20b33-enh upgrade-failure-surfacing-log-and-child-output`) — 13 ACs completed. Key decisions: Divergent pre-plan: selected approach C below.; Child output is teed to a per-run contained file through `isolated_popen` and a drained reader, not redirected, with `PYTHONUNBUFFERED=1` as the only child environment addition.
- **Upgrade CLI Resume and Accounting-Gap Clear Guidance** (`20b34-enh upgrade-cli-resume-and-gap-clear-guidance`) — 8 ACs completed. Key decisions: Divergent pre-plan: selected approach C below.; Build resume argv from one shared helper placed in `sqlite_storage_migration.py` beside `restart_command`.
## Watchpoints

- Watchpoint: sequence `20b34` after `20b33`. Both edit `upgrade_wavefoundry.py` and `upgrade_extensions.py`; keep the early-log-open hunk (`20b33`) and the `command_argv` and pause-message hunks (`20b34`) separate.
- This wave lands BEFORE wave `20b3b upgrade-resilience`. `20b3b` must rebase on the `20b34` resume helper (`20b36` owns any other `restart_command` change) and on the `20b33` log-open ordering; serialize edits to `upgrade_wavefoundry.py` and `upgrade_extensions.py` across the two waves.
- Log-open ordering is a readiness finding: open the fresh-run log only after the lifecycle lock is held, and prove a lock-busy run leaves the first log byte-identical.
- Security: new log files go through the contained-files helpers (no symlinks, junctions or reparse points, 0600) and captured output is redacted for the publisher token and bounded.
- The old-code window means the first upgrade carrying these changes does not protect itself, including the old MCP handler that still truncates head-only; do not assert otherwise in tests, and do not claim `error_tail` for that first upgrade in docs or the CHANGELOG.
- Watchpoint: `20b33` adds a new contained create-or-append open in `contained_files.py` and a new stdlib tee module (`child_tee.py`); both must be registered (extension module roster, pack/MANIFEST) and are follow-up checks at Prepare of wave `20b3b`, which rebases on them.
- Watchpoint: `20b34` places its resume helper in `sqlite_storage_migration.py` beside `restart_command`; wave `20b3b` change `20b36` also edits that region, so keep the hunks separate and re-derive every cited line anchor after this wave lands.
- Product Intent: waived for both changes (guidance and diagnostics fixes with no product scope; seed 170 lists the section but no change doc of this kind carries it and docs-lint does not enforce it). The waiver is recorded in each change's Progress Log.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| 20b3a-capture-completeness | do_now | no | completed | code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer, release-reviewer, security-reviewer, council-delivery |
| 20b3a-qualification-fixture-alignment | do_now | no | completed | code-reviewer, qa-reviewer, release-reviewer, council-delivery |
| 20b3a-reload-dependency-closure | do_now | no | completed | code-reviewer, qa-reviewer, release-reviewer, council-delivery |
| 20b3a-token-final-sanitization | do_now | no | completed | code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer, release-reviewer, security-reviewer, council-delivery |

*Machine review state — 4 findings; current: do_now 4, maybe_later 0, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| council-readiness | approved | current executed approval by coryhacking follows every affected repair | none |
| council-delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| code-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| qa-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| architecture-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| docs-contract-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| release-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| security-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| operator-signoff | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Review checkpoints

### Implementation handoff — 2026-10-10

Both source changes are implemented; all tasks are complete. Change-local checks passed: upgrade 735 tests (two skips, identities not captured in this focused log), corrected integration 135, setup CLI 50, new tests 36, and context boundaries two. Eight executed mutants were detected; all six default restart-command baselines remain byte-identical. Canonical qualification and full independent delivery review remain pending; AC-13 for 20b33 and AC-8 for 20b34 remain unchecked. The source writer has stopped, and the framework edit gate is closed for the frozen review round. Native Windows remains simulated, and first-upgrade behavior remains limited by the installed old runner/handler. Temporary diagnostics are not permanent evidence artifacts.

The first independent delivery round is frozen at framework hash `4291f0bcc036feab62588a7db3e1c3b5bcc1abe61c51d5dfc95ad4b1cfd18f10`. The canonical run was stopped at 56 of 184 files (exit 143), with its owned descendants terminated and their absence verified, after an executed redaction defect established that a source repair would invalidate that run. This is partial diagnostic evidence, not qualification or a green receipt. Security confirmed that control/ANSI removal can reconstruct a token after redaction; architecture also reproduced surviving capture readers and undisclosed dropped output when a descendant retains pipes. The full delivery round completed with five actual seat contexts and six required specialist judgments; its anonymous merit pass and fact challenge retained two deduplicated blockers, `20b3a-token-final-sanitization` (AC-9) and `20b3a-capture-completeness` (AC-7). Both are recorded as delivery findings. The accepted repair preserves token overlap after canonicalization, completes ordinary capture to EOF, and applies explicit timeouts to process plus capture. It changes no admitted requirement, trust boundary, recovery phase or ownership protocol; affected lanes will independently reverify it. No attacker privilege delta, permanent reader leak, universal custom-sink guarantee or native Windows qualification is claimed. Final canonical qualification will use the repaired source.

### Repair verification — 2026-10-10

Both recorded findings have completed cycle-1 repair and independent lane clearance. Repairs changed only `child_tee.py`, `test_child_tee.py` and `test_upgrade_failure_surfacing.py`: canonical stream assembly retains final-form token overlap; ordinary capture drains to EOF; explicit timeouts cover process plus capture; presentation writes do not hold the log/bookkeeping lock. Implementer checks passed (32 focused tests, five pruning tests, no skips); three reached mutants failed assertions and restored controls passed.

Fresh focused verification covered all six affected specialists and Council through four actual execution contexts: code/architecture shared, security, QA, and docs/release/chair shared. Every actor used its own executed controls and reached/restored mutants. Security additionally checked 84 control/partition cases and bounded unfinished sequences; code/architecture and QA exercised the actual pruning consumer with count 17 and late descendant output. Regression anchors: `ChildTeeTests.test_decorated_token_canonicalization_spans_reads_and_forced_caps`, `ChildTeeTests.test_default_capture_waits_for_finite_descendant_eof`, and `PhaseChildTests.test_split_publisher_token_is_absent_from_all_upgrade_destinations`. Eleven state-derived lane clearances were recorded; no new finding or full-review trigger was established. Initial full delivery coverage remains current for untouched surfaces.

Source remained frozen at framework hash `ee6e7b92e392e3d49a0fc4ba6c9e1e7541b40b517978b9f4fddd0aa9fbe8c80a`; all 24 reviewed SHA/Git identities matched. Canonical qualification and final docs validation remain pending, so delivery approval has not been recorded. Windows pipe ABI is documented and simulated; no native Windows qualification, arbitrary custom-sink cancellation or bounded no-timeout inherited-pipe lifetime is claimed. Reader/fixture cleanup was verified for the executed finite controls. Diagnostics remain temporary; the durable result belongs here and in the regression tests.

### Qualification integration repairs — 2026-10-10

Independent runtime probes confirmed a real successful-MCP-reload defect: stale `child_tee` and migration helpers supplied old sanitization and recovery guidance. Cycle 2 restores the existing reload contract, corrects two new test imports and updates only the intentionally changed `wf_upgrade` digest, preserving its historical provenance. Migration reload uses the existing in-place mechanism with a module-owned ContextVar guard; it preserves active binding, clean scope exit, exception identities, runtime-lock registry and native connections without re-executing eight heavy dependencies. Independent code/QA/release and architecture verification exercised the actual consumers and reached three removed-guard mutants. All five full-review triggers remain false.

The cycle-2 canonical run completed red: 12,196 tests/184 files/12 skips in 1254.763s, with eleven fixture failures in three older test files. Cycle 3 changes only the stale reload-tuple negative fixture, nine child-runner injection seams and one precisely counted foreground-wait classification. All 902 existing assertion ASTs and production bytes are unchanged. Independent code/QA/chair review in one shared fresh context passed 14 focused checks without skips and detected four broken variants; a distinct release reviewer confirmed the call census statically. The original assertions reject false semantic/graph success, an invalid native epoch and an omitted wait classification. Foreground session flags and the inherited direct-child-only explicit-timeout limit remain unchanged; current upgrade callers supply no timeout. All four recorded findings now have terminal repaired heads and no unresolved lanes. No new full-review trigger, upgrade pass or permanent evidence folder was added.

### Final qualification — 2026-10-10

The quiet isolated default run passed 12,196 tests across 184 files in 1205.540s (exit 0). All 12 skip IDs and reasons exactly match the baseline. Framework hash `6eee918e91e8ba7e2ef15f8b5bc88674fced8dffe4726a3a3c31f950a60feed7` and all 31 frozen review identities matched both working tree and snapshot before the runner's genuine receipt was copied byte-for-byte. Receipt timestamp: 2026-10-10T23:47:18.704053+00:00; receipt SHA-256: `63de43e41a7c2cc87b3277599691628f7340cec85e51b1578044be72bccc5354`. Exact execution report is in the ignored qualification cache; routine diagnostics remain temporary. All 21 ACs and all tasks are reconciled; full docs validation passed without errors or warnings. Seven typed delivery approvals are current, with original reviewer contexts and limits preserved; operator signoff remains reserved. The wave is PAUSED for operator closure. No native Windows or release-archive qualification is claimed. Earlier stopped/red runs are diagnostic history and supply no green receipt.

Bounded AC scope-gap check: all admitted important and nice-to-have items are met. Native Windows qualification and testing a future release archive remain follow-ups; the installed old-runner/handler window remains the disclosed boundary of this change. No additional change was admitted.

### Implementation allocation — 2026-10-10

Activated on current typed readiness after fully reviewing and pausing 20b39. One generic implementer owns both changes in dependency order: 20b33 early lock-owned logging, bounded child tee and MCP output tails, then 20b34 checkpoint-specific recovery and accounting-gap commands. Shared runner/extensions edits are serialized. Requested gpt-6.1-sol/high fits the containment, subprocess and response-contract risks; observed runtime identity is unknown. The earlier preflight was reused with affected 20b39 writable-flush/renderer anchors refreshed; no conflict was found. Preserve the writable-flush and newline/BOM repairs. Capture default restart-command bytes before changing its optional API.

Parent pre-implementation memory briefing has no needs_reverification advisory. Apply MCP stdout purity, paired response producer/consumer checks, nonvacuous test obligations, phase/old-code-window rules and current memory authorization for retained staging receipts. The memory-count advisory does not open an unrelated curation task. Child logs retain five generated run groups; routine implementation/reviewer artifacts stay temporary. The parent owns one quiet canonical suite after implementation/bookkeeping freeze, independent full delivery review and pause. No closure, commit, push or local pack rebuild is authorized.

- 2026-10-10: Before activation, complete the project-policy roster for the new contained log handle, child-process integration and behavioral MCP spec: QA, architecture, security and docs-contract review join the existing code and release lanes. The accepted implementation scope is unchanged; Prepare will publish the current receipt and fresh phase-correct approvals. Council fixed-seat review covers the same risks rather than adding duplicate test runs.
- 2026-10-10: Fresh readiness review against receipt `review-policy-2a7c3ca5854f5fb4ed43` approved the admitted plans, with no findings. Full red-team primer preceded four independently contextualized fixed seats (architecture, security, QA, reality), then the rotating docs-contract seat and an independent chair. Code shared architecture's context; release shared docs-contract's context: seven role judgments from five seat contexts, rather than seven independent executions. All seats answered the three primer questions; the chair assessed anonymous randomized judgments before attribution. Requested models were `gpt-6.1-sol` (reality medium, other seats and chair high); observed runtime identity is unknown. Agreement: unanimous; maximum severity: none.
- Architecture and code: no findings; current foreground-child and lexical-containment controls support feasibility, and reject omitted spawn sites and a tail-only initial-slice fix. Security: no findings; scratch contained I/O controls reject a whole-module runtime-lock-alias mutant. QA: no findings; actual command quoting distinguishes an unquoted-join mutant, with a finite delivery matrix for all 21 ACs. Reality: no findings; actual parser/next-step controls reject a mistaken cleanup continuation. Docs-contract and release: no findings; actual parser, pack-selection and default-command controls reject changed default argv and claims of first-upgrade MCP protection. Chair: no findings; a real child through the whole current subprocess helper rejects forced detachment. Source and plan identities remained unchanged during each review; no full suite, future implementation, native Windows or package execution is claimed by these readiness controls.
- Implementation notes: sanitize before every sink, retaining split-token overlap across forced flushes; refuse original linked parents before any log mutation; preserve the error tail through every envelope fallback; retain only five generated run groups; derive operator commands from the fixed checkpoint allowlist and preserve older-helper/default-command behavior. These refine existing ACs and require no extra upgrade pass or permanent evidence folder. Delivery must verify the completed behavior separately.

## Dependencies

- No external wave dependencies. Declare intra-wave dependencies with a `Depends On:` line containing full backticked change ids in each change's block under `## Changes`.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| plan | 50 | 412,883 |
| implement | 219 | 3,303,385 |
| review | 918 | 5,708,844 |
| **Total** | **1,187** | **9,425,112** |

<!-- wave:context-efficiency-state {"generation":1228,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":219,"content_source_credit":3572997,"derived_artifact_credit":0,"direct_net":3303385,"estimated_tokens_saved":3303385,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":10171,"response_debit":267927,"source_credit_count":100,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":8486},"plan":{"calls":50,"content_source_credit":488916,"derived_artifact_credit":2944,"direct_net":412883,"estimated_tokens_saved":412883,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":20550,"response_debit":67628,"source_credit_count":31,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":9201},"review":{"calls":918,"content_source_credit":8129396,"derived_artifact_credit":361,"direct_net":5708844,"estimated_tokens_saved":5708844,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":114008,"response_debit":2309761,"source_credit_count":317,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2856}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":1187,"content_source_credit":12191309,"derived_artifact_credit":3305,"direct_net":9425112,"estimated_tokens_saved":9425112,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":144729,"response_debit":2645316,"source_credit_count":448,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":20543},"wave_id":"20b3a upgrade-failure-surfacing"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 74 | 0 | 36 | 29,886,810 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":36,"estimated_exploration_avoided":29886810,"surfaced_events":74} -->
<!-- wave:exploration-avoided end -->

# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-11-21
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `23zbf upgrade-setup-and-permission-follow-ups`
Title: Upgrade Setup And Permission Follow Ups

## Objective

Operators read a short upgrade dry run and a drift report they can act on, see the recorded setup phase, the next recovery step, and what to do when the same failure recurs, and can let agents run low-risk write tools without prompting while closes, gates and upgrades still ask. Task checkboxes can be marked by a unique prefix. The mark tools protect closed history, explicit required deferrals and visible checklist entries before operators opt in.

## Changes

Change ID: `23xoq-enh upgrade-dry-run-and-drift-report-clarity`
Change Status: `implemented`

Change ID: `23xor-enh setup-checkpoint-recovery-wording`
Change Status: `implemented`

Change ID: `23zbc-enh low-risk-write-permission-tier`
Change Status: `implemented`
Depends On: `23xlm-bug protect-marked-checklist-integrity`

Change ID: `23zbd-enh mark-task-unique-prefix`
Change Status: `implemented`

Change ID: `23xlm-bug protect-marked-checklist-integrity`
Change Status: `implemented`

## Participants

- Coordinator: wave-coordinator (main session)
- Write-owning roles: implementer
- Requested review lanes: security-reviewer
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer, release-reviewer, security-reviewer

Completed At: 2026-11-21

## Wave Summary

Wave `23zbf` (Upgrade Setup And Permission Follow Ups) delivered 5 changes: Upgrade Dry Run Logs the Extension Source and the Baseline Drift Report Says What to Do, A Failed Setup Names One Resume Command and Its Recorded Phase, Low-risk write permission tier for the rendered host allowlist, Mark a task by a unique prefix, and Protect checklist history and deferral reasons.

Intent outcome: The delivered tools give operators a bounded upgrade preview with actionable template comparisons, an immediate setup command when it is safe to retry, and prerequisite guidance when source recovery must happen first. Scratch-target checks exercise served checklist updates, including completed waves, individually completed specs, required deferrals and ambiguous task prefixes. The opt-in host renderer covers the 16 selected write tools and preserves manual rules. Focused tests establish these behaviors on the current host. Native Windows execution, downstream adoption and reduced operator effort remain unobserved. QA independently confirmed all five outcomes at their tested interfaces. The final default suite passed 13,187 tests across 253 files with 12 skips. The declared profile also passed the upgrade and permission checks.

**Changes delivered:**

- **Upgrade Dry Run Logs the Extension Source and the Baseline Drift Report Says What to Do** (`23xoq-enh upgrade-dry-run-and-drift-report-clarity`) — AC-1, AC-2, AC-3, AC-4, AC-5, AC-6, AC-7, AC-8 and AC-9 completed. Key decisions: Dry run: print the module's name, digest and line count, and write the exact source to `.wavefoundry/logs/upgrade-extension-module.preview.log`; Write the log from the zip entry's bytes, not from decoded text.
- **A Failed Setup Names One Resume Command and Its Recorded Phase** (`23xor-enh setup-checkpoint-recovery-wording`) — AC-1, AC-2, AC-3, AC-4, AC-5, AC-6, AC-7, AC-8, AC-9, AC-10 and AC-11 completed. Key decisions: Selected approach: one shared producer in `setup_readiness.py` that yields the resume argv, the recorded setup phase and the cause for both surfaces, with the new readiness path limited to a recorded failure; Mechanism efficacy. Replay: the reported state (cases A and B) gets `recovery_pending`, one command and the step on both surfaces. Control or advice: advice; the refusals remain the control. What makes someone act: the command is the last text of the line the operator is already reading, the hook prints it as `Recommended:`, and the `setup_not_ready` notice now fires. Misses: a killed setup with no recorded failure, and a record that fails an ownership check, stay `recovery_unproven` in the readiness check; the upgrade refusal still prints the command. Wrong flags: none found; a rerun clears `failed_phase` on entry (executed, A'2). Existing mechanisms give the value: no new mechanism, code or action kind. Measure after release: the reporting team sees `recovery_pending` with a command for a failed setup, and its next report of a failed setup quotes the step.
- **Low-risk write permission tier for the rendered host allowlist** (`23zbc-enh low-risk-write-permission-tier`) — AC-1, AC-2, AC-3, AC-4, AC-5, AC-6, AC-7, AC-8 and AC-9 completed. Key decisions: Selected: a named subset of the write tier plus a second operator key; Mechanism efficacy. Replay: the reporter sets the key, the next render adds rules under its served names, and marks, gardening, index builds and new records stop prompting while closes, gates, upgrades and cleanup still prompt; the rename case was replayed in the prototype. The mechanism controls the rendered rules and the host enforces them; it is opt-in, so seed 050 and the CHANGELOG bullet are what make an operator act. It misses frequent tools left out on purpose (`wf_review_wave`, `wf_pause_wave`), so relief is partial. Hand-authored rules give one team most of the value but no self-heal. Measured after release by asking the reporter whether set tools stopped prompting and closes still prompt, and by the absence of reports of a rule naming an unserved tool.
- **Mark a task by a unique prefix** (`23zbd-enh mark-task-unique-prefix`) — AC-1, AC-2, AC-3, AC-4, AC-5, AC-6, AC-7, AC-8 and AC-9 completed. Key decisions: Selected: a second-tier prefix rule that runs only when the existing rule matches nothing; The prefix rule applies to `Tasks` only.
- **Protect checklist history and deferral reasons** (`23xlm-bug protect-marked-checklist-integrity`) — AC-1, AC-2, AC-3 and AC-4 completed. Key decisions: The operator selected shared writer guards and retained the opt-in tier; Close spec affects only its selected member. After closing the only admitted spec, the agent can offer Close wave as a separate action.

## Watchpoints

- Watchpoint: never run an upgrade against this repository; upgrade tests use scratch targets.
- Watchpoint: seed edits (seed 050, seed 160) open `seed_edit_allowed` around each edit and close it after.
- Watchpoint: the admitted specs add a bullet to the existing Unreleased section of the root changelog.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| 23zbf-active-mark-publication-interleaving | do_now | no | completed | code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer, security-reviewer |
| 23zbf-overwrite-rerender-mode | do_now | no | completed | docs-contract-reviewer |
| R1-23xoq-lookalike-region-mask | do_now | no | completed | — |
| R1-23xoq-preserve-hides-stale-copy | do_now | no | completed | — |
| R1-23xor-case-b-untested | do_now | no | completed | — |
| R1-23xor-recovery-claim-overstated | do_now | no | completed | — |
| R1-23xor-step-on-return-code-exit | do_now | no | completed | — |
| R1-23zbc-threat-note-bounds-false | do_now | no | completed | — |
| R2-23xlm-completed-member-history | do_now | no | completed | code-reviewer, architecture-reviewer, docs-contract-reviewer, qa-reviewer, security-reviewer, release-reviewer |
| R2-23xor-preserve-recovery-prerequisite | do_now | no | completed | qa-reviewer, release-reviewer |

*Machine review state — 10 findings; current: do_now 10, maybe_later 0, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | Phase | State | Why | Next action |
| --- | --- | --- | --- | --- |
| council-readiness | readiness | approved | current executed approval by coryhacking follows every affected repair (local account: coryhacking) | none |
| council-delivery | delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| code-reviewer | readiness | approved | current executed approval by coryhacking follows every affected repair (local account: coryhacking) | none |
| code-reviewer | delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| qa-reviewer | readiness | approved | current executed approval by coryhacking follows every affected repair (local account: coryhacking) | none |
| qa-reviewer | delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| architecture-reviewer | readiness | approved | current executed approval by coryhacking follows every affected repair (local account: coryhacking) | none |
| architecture-reviewer | delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| docs-contract-reviewer | readiness | approved | current executed approval by coryhacking follows every affected repair (local account: coryhacking) | none |
| docs-contract-reviewer | delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| release-reviewer | readiness | approved | current executed approval by coryhacking follows every affected repair (local account: coryhacking) | none |
| release-reviewer | delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| security-reviewer | readiness | approved | current executed approval by coryhacking follows every affected repair (local account: coryhacking) | none |
| security-reviewer | delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| operator-signoff | delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Dependencies

- No external wave dependencies. Declare intra-wave dependencies with a `Depends On:` line containing full backticked change ids in each change's block under `## Changes`.

## Review Checkpoints

2026-11-21: Intent outcome: The delivered tools give operators a bounded upgrade preview with actionable template comparisons, an immediate setup command when it is safe to retry, and prerequisite guidance when source recovery must happen first. Scratch-target checks exercise served checklist updates, including completed waves, individually completed specs, required deferrals and ambiguous task prefixes. The opt-in host renderer covers the 16 selected write tools and preserves manual rules. Focused tests establish these behaviors on the current host. Native Windows execution, downstream adoption and reduced operator effort remain unobserved. QA independently confirmed all five outcomes at their tested interfaces. The final default suite passed 13,187 tests across 253 files with 12 skips. The declared profile also passed the upgrade and permission checks.

2026-11-21: All six specialist lanes approved. Code found two simultaneous checklist edits could each report success while only one persisted. Both mark tools now share the lifecycle lock with close. A competing call received a busy response. Retrying after release preserved both edits. Docs-contract found the four overwrite instructions used the default preview. Each corrected instruction restored the incoming text and its generated section on a disposable install. Both reviewers independently reverified their findings.

2026-11-21: The full-depth delivery council rated all five specs and the wave Objective `establishes`. The red-team primer challenged whether a success response proves the file contents. Architecture, security, QA, reality-checker and the rotating docs-contract seat inspected the resulting files. The five seats agreed, with no remaining material disagreement. The rotating seat proposed a lasting regression test that extracts the four published commands and executes each distinct call once. The seats endorsed the proposal as a follow-up. Release review verified the preview bytes and all other files against their pre-run contents on a scratch installation.

2026-11-21: The operator retained the opt-in permission group and added 23xlm as a prerequisite. On receipt `review-policy-d76937227fa810fc98d9`, QA, release and security independently verified the repairs to all six original findings. The amended review included six specialist lanes, an independent red-team primer, the reality-checker and the council chair. The chair withheld readiness on two findings. A completed member of an open wave falls outside the planned writer check, although the permission guidance promises to protect its checklist. The planned setup error excerpt also hides the prerequisite to recover an unreadable migration source before retrying. All six specialists own the checklist recheck. The reality-checker owns the recovery finding, with QA and release responsible for rechecking the public actions and guidance. The reviewers tested plan claims on this receipt. Product verification follows implementation.

2026-11-21: The operator chose to protect individually completed specs in open waves and to recover a compatible duplicate before retrying a legacy storage failure. The six specialist lanes, reality-checker and chair independently verified the two affected cases on receipt `review-policy-1c8e832684356f86b639`. All eight findings reached completed repair. The chair rated each of the five specs and the wave Objective `establishes` at readiness. Its two negative controls removed the editable-sibling assertion and substituted immediate retry when the setup guidance producer was unavailable. Both failed as expected. During implementation correct the outdated 23xor Risks row to match Requirement 5.5 and AC-3.5: when the producer is unavailable, preserve the refusal and point to recovery guidance without printing a retry command. Runtime enforcement, native Windows execution and field outcomes await verification.

2026-11-21: Paused after delivery review. All acceptance criteria and tasks are complete. The full-suite receipt covers the delivered tree. Operator signoff and closure remain outstanding.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| plan | 131 | 2,737,892 |
| implement | 131 | 0 |
| review | 486 | 7,939,867 |
| **Total** | **748** | **10,677,759** |

<!-- wave:context-efficiency-state {"generation":744,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":131,"content_source_credit":0,"derived_artifact_credit":0,"direct_net":-14354,"estimated_tokens_saved":0,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":6105,"response_debit":28915,"source_credit_count":0,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":20666},"plan":{"calls":131,"content_source_credit":3278600,"derived_artifact_credit":8994,"direct_net":2737892,"estimated_tokens_saved":2737892,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":61863,"response_debit":493767,"source_credit_count":142,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":5928},"review":{"calls":486,"content_source_credit":10045713,"derived_artifact_credit":2285,"direct_net":7939867,"estimated_tokens_saved":7939867,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":42122,"response_debit":2072725,"source_credit_count":286,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":6716}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":748,"content_source_credit":13324313,"derived_artifact_credit":11279,"direct_net":10663405,"estimated_tokens_saved":10677759,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":110090,"response_debit":2595407,"source_credit_count":428,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":33310},"wave_id":"23zbf upgrade-setup-and-permission-follow-ups"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 47 | 0 | 26 | 23,149,029 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":26,"estimated_exploration_avoided":23149029,"surfaced_events":47} -->
<!-- wave:exploration-avoided end -->

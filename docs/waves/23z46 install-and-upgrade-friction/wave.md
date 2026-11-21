# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-11-20
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `23z46 install-and-upgrade-friction`
Title: Install And Upgrade Friction

## Objective

Operators know when an install needs their permission, see actionable document errors before an upgrade replaces files, and can tell which review phase an approval covers.

## Changes

Change ID: `23zl2-enh docs-lint-control-characters`
Change Status: `implemented`

Change ID: `23zib-enh install-surface-gate-guidance`
Change Status: `implemented`

Change ID: `23zl1-enh review-evidence-phase-column`
Change Status: `implemented`

Change ID: `23zia-enh upgrade-lint-preflight-and-diff-log`
Change Status: `implemented`
Depends On: `23zl2-enh docs-lint-control-characters`

## Participants

- Coordinator: wave-coordinator (main session)
- Write-owning roles: implementer
- Requested review lanes: none
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer, release-reviewer

Completed At: 2026-11-21

## Wave Summary

Wave `23z46` (Install And Upgrade Friction) delivered 4 changes: Docs Lint Reports Control Characters in Markdown, Install surface gate guidance, independent CLAUDE.md bridge and manifest example, Show the approval phase in the Review Evidence status table, and Upgrade Lints Before Replacing the Tree and Logs Seed Diffs.

Intent outcome: established on the tested workflows. Install guidance tells the installer when to ask permission, who closes the gate and how to resume after an interruption (23zib). Full and changed Markdown lint locate controls in live documents and use the owning record to exclude closed history (23zl2). Fresh upgrade refuses a confirmed live docs error before extraction, prints the retry command and gives the operator the complete seed diff (23zia). During apply and resume, review tables distinguish readiness from delivery while preserving operator text and historical record bytes (23zl1). QA independently checked these outcomes for each spec. The chair confirmed them against the wave Objective. The rehearsals ran on macOS. An actual downstream install transcript and native Windows execution remain unmeasured.

**Changes delivered:**

- **Docs Lint Reports Control Characters in Markdown** (`23zl2-enh docs-lint-control-characters`) — AC-1, AC-2, AC-3, AC-4, AC-5, AC-6, AC-7, AC-8 and AC-9 completed. Key decisions: Selected approach: a registered docs-lint sensor over the decoded text of live scanned markdown, mirroring the `heading_without_blank_line_before` sensor's path sets and history predicate, with one compiled pattern search per document; The sensor ships **blocking**, against the default that new docs-lint sensors ship advisory (`SENSOR_POLARITY_REGISTRY` comment in `constants.py`; plan-spec prompt). This record is the recorded decision that policy asks for.
- **Install surface gate guidance, independent CLAUDE.md bridge and manifest example** (`23zib-enh install-surface-gate-guidance`) — AC-1, AC-2, AC-3, AC-4, AC-5, AC-6 and AC-7 completed. Key decisions: Premise (a) confirmed, hook message. Status: executed; Premise (a) confirmed, install log. Status: verified by reading; the interpretation of "row" is inferred.
- **Show the approval phase in the Review Evidence status table** (`23zl1-enh review-evidence-phase-column`) — AC-1, AC-2, AC-3, AC-4, AC-5, AC-6, AC-7, AC-8, AC-10 and AC-9 completed. Key decisions: Select approach A: a Phase column plus a readiness row for each specialist key that holds a readiness approval in the ledger; Phase goes second, after Signoff.
- **Upgrade Lints Before Replacing the Tree and Logs Seed Diffs** (`23zia-enh upgrade-lint-preflight-and-diff-log`) — AC-1, AC-2, AC-3, AC-4, AC-5, AC-6, AC-7, AC-8, AC-9, AC-10, AC-12, AC-13, AC-14 and AC-11 completed. Key decisions: Block on the installed linter against the unchanged tree; Operator decision: ship the installed-rule pre-flight only; no pre-flight on incoming rules.

## Watchpoints

- Watchpoint: implement 23zl2 before 23zia; the pre-flight calls 23zl2's control-character scan. 23zia reads the incoming copy of `wave_validators.py` from the pack and does not edit that file; only 23zl2 edits it.
- Watchpoint: 23zia and 23zl1 both edit `upgrade_wavefoundry.py`, `upgrade_extensions.py`, `wf_server/upgrade_handlers.py`, seed 160 and `docs/architecture/layering-rules.md`. Implement those two specs one after another and rerun both changes' upgrade tests after the second.
- Watchpoint: 23zib and 23zl1 both edit seed 100.
- Watchpoint: 23zia, 23zl1 and 23zl2 all edit `docs/architecture/data-and-control-flow.md`; 23zia and 23zl1 both edit `docs/specs/mcp-tool-surface.md`.
- Watchpoint: all four specs add a bullet to the Unreleased section of the root changelog, which already exists; add to it rather than opening a second section.
- 23zl1 declares all of `.wavefoundry/framework/scripts/tests/`, which covers `test_docs_lint.py` (23zl2) and `test_upgrade_wavefoundry.py` (23zia).
- 23zib, 23zl1 and 23zia edit seeds: open `seed_edit_allowed` around each seed edit and close it after. Rendered hooks are regenerated, never hand-edited.
- Never run an upgrade against this repository; upgrade tests use scratch targets.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| D1-23zia-colon-prefix-closed-history | do_now | no | completed | release-reviewer, council-delivery |
| D1-23zia-verbatim-legacy-closed-count | do_now | no | completed | docs-contract-reviewer, release-reviewer, council-delivery |
| D1-23zia-visible-live-status-preflight | do_now | no | completed | release-reviewer, council-delivery |
| D1-23zib-bridge-preflight | do_now | no | completed | docs-contract-reviewer, council-delivery |
| D1-23zib-hook-census | do_now | no | completed | qa-reviewer, council-delivery |
| D1-23zib-install-gate-ownership | do_now | no | completed | docs-contract-reviewer, qa-reviewer, council-delivery |
| D1-23zl1-completed-history-refresh | do_now | no | completed | architecture-reviewer, council-delivery |
| D1-23zl1-refresh-removes-human-prose | do_now | no | completed | architecture-reviewer, council-delivery |
| D1-23zl2-comment-status-closed-history | do_now | no | completed | release-reviewer, council-delivery |
| D1-23zl2-git-quoted-paths | do_now | no | completed | code-reviewer, council-delivery |
| D1-23zl2-saved-record-shadows-closed-owner | do_now | no | completed | council-delivery |
| R1-23z46-wave-dependency-record | do_now | no | completed | — |
| R1-23zia-ac-coverage-gaps | do_now | no | completed | — |
| R1-23zia-ac1-3-unsatisfiable | do_now | no | completed | — |
| R1-23zia-layering-doc-missing | do_now | no | completed | — |
| R1-23zia-no-override-premise | do_now | no | completed | — |
| R1-23zia-preflight-on-recovery | do_now | no | completed | — |
| R1-23zia-secrets-exit-mismatch | do_now | no | completed | — |
| R1-23zia-serialization-bullets | do_now | no | completed | — |
| R1-23zl1-rerender-never-runs | do_now | no | completed | — |
| R1-23zl1-resume-after-gate-contract | do_now | no | completed | — |
| R2-23zia-existing-indeterminate-lock | do_now | no | completed | — |

*Machine review state — 22 findings; current: do_now 22, maybe_later 0, dont_do_later 0, not_issue 0*
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
| operator-signoff | delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Dependencies

- No external wave dependencies. Declare intra-wave dependencies with a `Depends On:` line containing full backticked change ids in each change's block under `## Changes`.

## Review Checkpoints

2026-11-21: Intent outcome: established on the tested workflows. Install guidance tells the installer when to ask permission, who closes the gate and how to resume after an interruption (23zib). Full and changed Markdown lint locate controls in live documents and use the owning record to exclude closed history (23zl2). Fresh upgrade refuses a confirmed live docs error before extraction, prints the retry command and gives the operator the complete seed diff (23zia). During apply and resume, review tables distinguish readiness from delivery while preserving operator text and historical record bytes (23zl1). QA independently checked these outcomes for each spec. The chair confirmed them against the wave Objective. The rehearsals ran on macOS. An actual downstream install transcript and native Windows execution remain unmeasured.

2026-11-21: Delivery council used a full adversarial primer. Architecture, QA, security and reality-checker were the four fixed seats. Release held the rotating seat. All five initially withheld approval. Eleven recorded findings received repairs and independent reverification. The security seat also verified that a tab in a filename is escaped in the operator diagnostic while the upgrade still opens the correct file. Matched tests reached tagged installers, real Git filenames, a resumed upgrade and the extracted docs gate. The final 54-path evidence fingerprint was `74027cc3a2416ae529dba5a9dd73147a22991e61`. The release reviewer, independent closing red team and chair separately exercised an active record with a history status inside an example. A real control byte stopped fresh apply before replacement. Removing the byte passed the extracted gate. Restoring the old preflight behavior reproduced the retained lock. All five seats agreed after repairs, and the chair recorded `establishes` for each spec and the wave. The initial triage was `seat_agreement=unanimous` on withholding approval and `max_severity=high` because a supported upgrade deleted operator prose. The final vote was unanimous, with no unresolved finding.

2026-11-21: The rotating release seat proposed staging an incoming runner to cover an older installed planner. The council kept the existing release boundary after comparative runs. A completed record with a genuinely missing declared ledger can still fail in the v1.31 planner even with the new preflight disabled. A stale historical Finding Synthesis can still fail the final integrity gate. An old Review Status table alone passes. The new preflight never refuses a finding attributed to closed history and treats ambiguous ownership as indeterminate. Field effectiveness of a staged-runner alternative remains unverified.

2026-11-21: All 253 test files passed in each release profile. The default run completed 13,160 tests with 12 skips in 718.920 seconds and wrote the framework receipt. The second profile completed 13,138 tests with 38 skips in 675.839 seconds. The declared profile completed 13,160 tests with 12 skips in 661.727 seconds. Both profile comparisons matched expectations, including the second profile’s 26 additional approved skips. Code, QA, architecture, docs-contract, release and council delivery approvals are recorded. The memory preview offered one account of the former hook warning. The new install guidance and tests supersede that warning, so no candidate was created.

2026-11-20: The operator authorized a bounded repair and focused verification of the release reviewer’s AC-10.1 finding. The revised guidance explains that a later docs-gate failure can retain a lock even when its cause existed before extraction. The live-document pre-flight decision stands.

2026-11-20: The operator confirmed the fresh-upgrade pre-flight must never refuse on closed history. The 23zia repair extends that decision to ambiguous and renamed-layout paths. Only independently established live findings may block. Recheck this change against the new readiness receipt.

2026-11-20: Evidence correction. The architecture finding R1-23zia-preflight-on-recovery and its first reverification used source inspection for recovery order. The release reverification of R1-23zia-no-override-premise inspected plan text and relied on the primer’s historical run. Their true execution-integrity values overstate what those reviewers executed. Use their observations only within those limits. Fresh probes, when recorded, stand on their own. The original records remain in the append-only ledger. A read-only `wf_review_event` preview using `execution_status=inferred` and false integrity values for a readiness finding refused the event with “dedup evidence must be executed”. This confirms a writer limitation for this kind of finding. An evidence text that explains a source read cannot make a true execution attestation accurate.

2026-11-20: Fresh coordinator checks replayed the old closed-record case. With the same retired marker in closed wave 1293d, the v1.31.0 and v1.32.0 tagged linters ran with `PROJECT_ROOT` pointing to each scratch tree and `python3 -B .wavefoundry/framework/scripts/docs_lint.py --read-only`. v1.31.0 exited 1 with two findings on the closed record. v1.32.0 exited 0. The production recovery test `test_storage_upgrade_resume.StorageUpgradeProcessResumeTests.test_old_main_pause_then_fresh_installed_main_relocated_pack_and_retry` passed, including refusal of a different archive at the same version and successful continuation with the relocated original. These checks establish the historical lint difference and the retained storage path. Delivery must still exercise the proposed pre-flight itself (AC-12 through AC-14).

The readiness council approved all four plans and the wave Objective on receipt `review-policy-58770d6306aa5cf0fc46`. The chair recorded `intent_fit=establishes`. The red team supplied the standard primer. Code, QA, architecture, docs contract and release approved the final packet. The red team also verified the final repair. The chair independently matched all four final specs to the reviewed text and replayed the v1.31 and v1.32 lint results on identical closed history. Each earlier claim retains the evidence limits above.

The council considered shipping control-character lint as advisory first. It retained the operator’s chosen live-error refusal. It also retained projection repair in the incoming upgrade hook so the installing upgrade and resume can use the new renderer. Delivery should exercise the strongest remaining case end to end. Start with a pre-existing finding whose status cannot be determined, observe preflight continue, make the final docs gate fail, then check the retained lock and printed resume command. After release, an install transcript, an upgrade transcript and its diff log, and a prepared wave’s review table provide direct evidence of the intended operator outcomes.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| plan | 166 | 10,329,428 |
| implement | 149 | 2,954 |
| review | 478 | 6,125,338 |
| **Total** | **793** | **16,457,720** |

<!-- wave:context-efficiency-state {"generation":819,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":149,"content_source_credit":0,"derived_artifact_credit":25899,"direct_net":2954,"estimated_tokens_saved":2954,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":6879,"response_debit":34162,"source_credit_count":0,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":18096},"plan":{"calls":166,"content_source_credit":11021584,"derived_artifact_credit":13200,"direct_net":10329428,"estimated_tokens_saved":10329428,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":72405,"response_debit":638879,"source_credit_count":719,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":5928},"review":{"calls":478,"content_source_credit":7606411,"derived_artifact_credit":2108,"direct_net":6125338,"estimated_tokens_saved":6125338,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":73705,"response_debit":1416038,"source_credit_count":212,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":6562}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":793,"content_source_credit":18627995,"derived_artifact_credit":41207,"direct_net":16457720,"estimated_tokens_saved":16457720,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":152989,"response_debit":2089079,"source_credit_count":931,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":30586},"wave_id":"23z46 install-and-upgrade-friction"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 45 | 0 | 26 | 22,368,935 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":26,"estimated_exploration_avoided":22368935,"surfaced_events":45} -->
<!-- wave:exploration-avoided end -->

# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-09-08
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1x5tr scanner-correctness-and-visibility`
Title: Scanner Correctness And Visibility

## Objective

Make scanner safety-guard omissions visible in close responses and keep non-git scan caches free of Wavefoundry machine authority. These changes share scanner ownership and prevent internally generated files from polluting the new coverage advisory.

## Changes

Change ID: `1x550-debt non-git-secrets-candidate-walk-includes-index-internals`
Change Status: `implemented`

Change ID: `1x4om-bug scanner-guard-skips-invisible-at-close`
Change Status: `implemented`

## Participants

- Coordinator: wave-coordinator
- Write-owning roles: implementer
- Requested review lanes: code-reviewer, qa-reviewer, architecture-reviewer, security-reviewer, performance-reviewer, docs-contract-reviewer
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer, performance-reviewer, security-reviewer

Completed At: 2026-09-05

## Wave Summary

Wave `1x5tr` (Scanner Correctness And Visibility) delivered two changes: The Secrets Scanner's Candidate Walk Includes Index Internals in Non-Git Repositories and A File the Secrets Scanner Skips Is Invisible to the Close Gate. Notable adjustments during implementation: A File the Secrets Scanner Skips Is Invisible to the Close Gate: Delivery review repairs (cycle 4): a removed-only delta now reaches the cache store so a removed file's row is deleted and an identical restore is re-observed rather than cache-hitting with its guard row already pruned; the ledger's duplicate-row dedupe is pinned.

**Changes delivered:**

- **The Secrets Scanner's Candidate Walk Includes Index Internals in Non-Git Repositories** (`1x550-debt non-git-secrets-candidate-walk-includes-index-internals`) — 3 ACs completed. Key decisions: Limit exclusion to existing semantic machine-authority classes.
- **A File the Secrets Scanner Skips Is Invisible to the Close Gate** (`1x4om-bug scanner-guard-skips-invisible-at-close`) — 5 ACs completed. Key decisions: Park rather than fold into `1x4ol`.
No admitted ACs or tasks were deferred. The JSON observation ledger preserves the fixed-root ownership and explicit scan-completion boundary; only the non-git fallback shares machine-authority exclusions. Durable lessons are retained in memories `1x5tw-mem` and `1x6hh-mem`. Operator-requested review artifact guidance is canonical in seed 209; the historical reports are consolidated with relocation anchors in one council archive.

## Watchpoints

- Watchpoint: serialize both changes at `wave_lint_lib/secrets_validators.py`; one implementer owns that file.
- Preserve Git candidates, cache-hit count semantics, raw scan tuple shape, and existing scanner guard thresholds.
- No custom-index exclusion expansion: the shared exclusions are the existing semantic layers 2–4. Skip evidence always has one canonical root-local location.
- Skip data is advisory; missing/unreadable scan state must not be presented as proven complete coverage.

## Review checkpoints

- Product-owner acknowledgment: operator accepted the two-scanner-change recommendation and requested prepare, review, then implementation on 2026-09-05. This authorizes the described advisory behavior and bounded non-git exclusions; no new skip-classification workflow.
- Builder allocation: generic implementer for cross-cutting scanner/MCP work; independent council and specialist readiness lanes before code edits.
- **Prepare-phase Wave Council [prepare-council] — 2026-09-05: PASS** (moderator: wave-council; primer-depth: full; seats: red-team, architecture-reviewer, security-reviewer, qa-reviewer, reality-checker, performance-reviewer, code-reviewer, docs-contract-reviewer; rotating-seat: performance-reviewer). Three plan findings repaired and independently cleared; all six required readiness lanes approved. See [council report](readiness-council.md). Canonical authority is `events.jsonl`.

### Closure reconciliation

- Both admitted changes are fully implemented; every task and AC is checked, with no intentionally unmet ACs or deferred implementation work. The final change state is `implemented`, matching the repository lifecycle convention.
- Delivery review is complete across code, QA, architecture, security, performance and docs-contract lanes, with the red-team seat and council delivery approval recorded. All required repair chains are terminal. Docs-contract review covered the changed MCP specification and architecture ownership/deletion contracts. The operator explicitly authorized closure and commit after reviewing delivery, smoke results and artifact consolidation; the typed operator signoff records that authorization.
- Final framework verification: 8,512 tests across 75 files, 3 intentional skips, OK; the close dry-run verifies the current green receipt. Subsequent smoke verification: 87 tests, no failures/skips. Full docs lint and diff checks passed after report consolidation. Framework and seed edit gates are closed.
- Retrospective: scanner cache rules must cover both producers, and validator stubs must mirror newly imported scanner accessors. These lessons are retained in active memories `1x5tw-mem` and `1x6hh-mem`. The close-time `memory_propose(mode='create')` pass is exhausted with zero new or pending candidates; prior rejected/superseded source dispositions remain preserved. Review artifact discipline is promoted into canonical seed 209 and the coordinator role; historical reports are consolidated with explicit relocation anchors.
- Closure publishes the completion timestamp and final wave summary, then resets the session handoff to idle with the shipped result and previously surfaced scope limitations. No operator decision remains necessary to deliver the admitted scope.

### Consolidated supporting evidence

On 2026-09-05 the operator requested applying Review Artifact Discipline to this wave. Five uncited supporting reports were summarized here and removed. On the subsequent cleanup request, ten individually cited reports were preserved in full in the existing [council evidence archive](readiness-council.md#historical-artifact-locations), with a relocation table for historical filename and fragment citations, and their separate files were removed. Four Markdown files remain: this record, the two admitted changes, and that evidence archive. The archive has the distinct lasting purpose of preserving original reviewer evidence cited by the immutable ledger. This consolidation changes neither recorded judgments nor approval authority.

The readiness briefing covered the two admitted plans and their Serialization Points, with a 180-second substantive-work budget per seat and one focused follow-up for material disagreement. Disposable fixtures only; no credentials, network, embedding builds, or live-root mutation. Its eight risk families were guard reasons/ordinary-line findings; worker/fallback equivalence; skip retention/retirement; malformed/failed/concurrent publication; advisory reader and close responses; exact non-git authority exclusions with positive lookalikes; unchanged Git candidates and two fresh-cache full scans; targeted deletion mutants. The implementation order was shared exclusions, ledger/outcome transport, close advisory/documentation, then regression and full-gate verification. These requirements and completion evidence remain in the admitted change docs.

| Readiness output | Distinct outcome and evidence retained |
| --- | --- |
| Red-team primer, context `1x5tr-primer-independent-20260905` | No new blocker. Source comparison of `scan_file_raw` and `_scan_file_secrets_worker` refuted inferring completion from an empty raw triple. Questions covered explicit worker-safe outcomes, exact candidate/cache census, and missing/malformed/blocked-close semantics. Five stances applied; no runtime execution or delivery approval claimed. |
| Reality seat, context `1x5tr-reality-independent-20260905` | No new material blocker after reader-only purity and fresh-cache scope clarification. A disposable Python `-B` probe called `scan_file_raw` with empty compiled rules on empty text, allowlisted nonempty text, and an absent path: all returned `([], None, [])`, as asserted, exit 0. This disproves the completion shortcut; it does not prove public scanning, workers, persistence, or close behavior. |
| Initial security seat, context `1x5tr-security-independent-20260905` | Approved with notes at readiness. Independently executed the same three-input raw-result control with the same observed triple. No credible lower-trust actor or authority escalation was established; coverage loss is a correctness concern. Interpreted purity as reader-only, preserving existing close validation. Final independent approval remains in the retained security recheck and typed ledger. |

The reality and initial security seats both weighed the rotating existing-SQLite alternative and preferred fixed-root JSON observation history: existing cache reset/custom-directory semantics do not own that history, while separate SQLite or append-only storage adds schema/replay obligations without measured need. Both retained short-lock publication and explicit outcome transport as delivery obligations; neither claimed a performance result.

Implementation verification before delivery review passed 8,506 tests across 75 files with 3 skips (185.072 seconds), full docs validation, and `git diff --check`. Two initial historical skip-reason census expectations were corrected to include the newly reported existing line-length guard. Disposable controls killed the excluded-authority predicate mutant, publication no-op, omitted long-line observation, and omitted worker outcome transport; clean/restored controls passed. Reproducible anchors are `NonGitMachineAuthorityTests.test_two_full_scans_keep_exact_cache_membership_without_index_internals`, `GuardCoverageIntegrationTests.test_all_guards_persist_without_hiding_ordinary_line_findings`, `GuardCoverageIntegrationTests.test_real_workers_publish_all_guards_without_serial_fallback`, and `ScannerSkipLedgerTests.test_guard_publication_survives_fresh_read_and_reskip_then_clears_on_complete_scan`. This is historical implementer evidence, not independent delivery approval; later delivery records in the ledger supersede its next-step wording and test totals.

The subsequent operator-requested smoke pass on the delivery-repaired tree passed **87 tests, no failures or skips**: `test_scanner_skips.py` (12), `test_secret_scan_cache.py` (24), `GuardCoverageIntegrationTests` (11), `WaveCloseSecretsGateTests` (18), and `test_scan_secrets.py` (22), using `/Users/coryhacking/.wavefoundry/venv/bin/python -B -m unittest discover -s .wavefoundry/framework/scripts/tests -p <file>` with `-k <class>` for the two named classes. These exercise real workers/fallback, failed-publication retries in both cache producers, delete/restore rescanning, cache stability and close advisories alongside existing secret gates.

Limits remain unchanged: fresh-cache pollution prevention does not purge historical rows; missing guard history is not proof of complete coverage; deletion loses observations; the advisory reader is read-only while existing close validation still scans. All implementation mutants were restored.

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-09-05 | Thought: ground and refine both accepted plans, admit together, then run readiness review before opening the framework edit gate. | MCP outlines and targeted reads located candidate, worker, cache and close-response owners. |
| 2026-09-05 | Observe: non-git full scans grow real cache membership from 4 to 8 unchanged files; guard skips have no durable authority, worker skip lists stay child-local, and long-line guards emit nothing. | Disposable `/tmp/scanner-scope` probes; admitted plans correct these assumptions. |
| 2026-09-05 | Reflect: readiness found ambiguous scope and omitted documentation carriers. Thought: repair plans before code by limiting purity to the added reader, declaring fresh-cache prevention, and naming guard-history ownership/deletion docs. | ARCH-READY-1, QA-R1, DOCS-READY-1; typed cycle-1 repair starts recorded before edits. |
| 2026-09-05 | Observe: all three plan corrections are applied; scanner-version migration and actual close test owner are explicit. | Both admitted plans and readiness packet; awaiting independent focused rechecks. |
| 2026-09-05 | Observe: all three readiness findings are terminal; six specialist approvals and council approval are current. Prepare ready and Implement create passed; framework edit gate opened. | Canonical events and successful lifecycle responses. |
| 2026-09-05 | Thought: follow packet sequence: extract shared exclusions and add ledger in separate owned files, then wire scanner outcomes and close advisory, verify targeted regressions/mutations, and run full gates. | Root owns secrets_validators.py, scan_secrets.py, server_impl.py and their integration tests; exclusion lane owns machine_authority.py/indexer.py/cache tests; ledger lane owns scanner_skips.py and its tests. Memory briefing checked; close producer/consumer and worker result seams reread. |
| 2026-09-05 | Gapfill: lifecycle test file was absent at guessed test_server_impl.py; scoped test-file listing found test_server_tools_lifecycle.py, followed by MCP outline and targeted fixture reads. Scoped rg checked test-only raw-result mocks because semantic test coverage is incomplete. | WaveCloseSecretsGateTests and TestScanFileRawGuards are the integration fixture owners. |
| 2026-09-05 | Observe: exclusion change implemented, 41 targeted cache/walker tests green, exclusion-deletion mutant detected. Ledger helper has 10 green unit checks; scanner/close wiring is in place and integration tests are next. | Independent builder results; root owns remaining integration. |
| 2026-09-05 | Observe: ledger suite now 11 green; scanner integration 7 green; close suite 18 green. Publication, long-line reporting and worker transport mutants each detected; all source restored. Thought: inspect combined diff, then run full framework suite and full docs gate. | AC-1 through AC-4 and all 1x4om tasks checked; standard AC-5 awaits full gates. |
| 2026-09-05 | Observe: combined diff inspection added the real-Git transient ls-files failure preservation control and retained the wider fallback in that case. Cache/walker checks now 42 green; full docs gate green. | `test_git_ls_files_failure_preserves_tracked_authority_in_fallback`; `wf_validate_docs`: no errors or warnings. Full framework run in progress. |
| 2026-09-05 | Reflect: full run reached 8,506 tests; only two historical skip-reason census assertions failed because they omit the newly surfaced existing line-length guard. Thought: update that owned compatibility expectation, retaining the prohibition on unknown guard reasons, then rerun full verification. Level 1 integration correction; no guard or scope change. | `NothingNewIsSkippedTests` in `test_secrets_prefix_collapse.py`; all other 74 test files passed. |
| 2026-09-05 | Observe: final full suite passes 8,506 tests/75 files, 3 skips, 185.072s. Both changes implemented; every AC/task complete. Framework edit gate closed; MCP matches disk with updated close description. | Green framework receipt; final runner log; `wf_reload_mcp` and `wf_close_gate`. Delivery review remains the next operator workflow; no wave closure or commit performed. |

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| ARCH-DEL-1 | do_now | no | completed | architecture-reviewer |
| ARCH-DEL-2 | do_now | no | completed | architecture-reviewer |
| ARCH-DEL-3 | not_issue | no | not_required | — |
| ARCH-READY-1 | do_now | no | completed | architecture-reviewer, code-reviewer, qa-reviewer, docs-contract-reviewer, security-reviewer, wave-council-readiness |
| CODE-DEL-1 | do_now | no | completed | code-reviewer, qa-reviewer |
| CODE-DEL-2 | not_issue | no | not_required | — |
| CODE-DEL-3 | not_issue | no | not_required | — |
| CODE-DEL-4 | not_issue | no | not_required | — |
| CODE-DEL-5 | maybe_later | no | completed | code-reviewer, qa-reviewer |
| DOCS-DEL-1 | not_issue | no | not_required | — |
| DOCS-DEL-2 | do_now | no | completed | docs-contract-reviewer |
| DOCS-DEL-3 | not_issue | no | not_required | — |
| DOCS-DEL-4 | not_issue | no | not_required | — |
| DOCS-DEL-5 | do_now | no | completed | docs-contract-reviewer |
| DOCS-DEL-6 | not_issue | no | not_required | — |
| DOCS-READY-1 | do_now | no | completed | docs-contract-reviewer, wave-council-readiness |
| PERF-DEL-1 | not_issue | no | not_required | — |
| PERF-DEL-2 | not_issue | no | not_required | — |
| PERF-DEL-3 | do_now | no | completed | performance-reviewer |
| PERF-DEL-4 | not_issue | no | not_required | — |
| QA-DEL-1 | do_now | no | completed | qa-reviewer |
| QA-DEL-2 | not_issue | no | not_required | — |
| QA-DEL-3 | not_issue | no | not_required | — |
| QA-DEL-4 | dont_do_later | no | not_required | — |
| QA-DEL-5 | not_issue | no | not_required | — |
| QA-DEL-6 | do_now | no | completed | qa-reviewer |
| QA-R1 | do_now | no | completed | qa-reviewer, docs-contract-reviewer |
| RED-DEL-1 | do_now | no | completed | code-reviewer, security-reviewer |
| RED-DEL-10 | do_now | no | completed | code-reviewer, qa-reviewer |
| RED-DEL-2 | do_now | no | completed | code-reviewer, qa-reviewer, security-reviewer |
| RED-DEL-3 | do_now | no | completed | code-reviewer, security-reviewer |
| RED-DEL-4 | not_issue | no | not_required | — |
| RED-DEL-5 | not_issue | no | not_required | — |
| RED-DEL-6 | not_issue | no | not_required | — |
| RED-DEL-7 | dont_do_later | no | not_required | — |
| RED-DEL-8 | not_issue | no | not_required | — |
| RED-DEL-9 | do_now | no | completed | code-reviewer, qa-reviewer, security-reviewer |
| SEC-DEL-1 | not_issue | no | not_required | — |
| SEC-DEL-2 | do_now | no | completed | security-reviewer |
| SEC-DEL-3 | do_now | no | completed | security-reviewer |
| SEC-DEL-4 | do_now | no | completed | security-reviewer |

*Machine review state — 41 findings; current: do_now 19, maybe_later 1, dont_do_later 2, not_issue 19*
<!-- wave:finding-synthesis end -->

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| wave-council-readiness | approved | current executed approval follows every affected repair | none |
| wave-council-delivery | approved | current executed approval follows every affected repair | none |
| code-reviewer | approved | current executed approval follows every affected repair | none |
| qa-reviewer | approved | current executed approval follows every affected repair | none |
| architecture-reviewer | approved | current executed approval follows every affected repair | none |
| docs-contract-reviewer | approved | current executed approval follows every affected repair | none |
| performance-reviewer | approved | current executed approval follows every affected repair | none |
| security-reviewer | approved | current executed approval follows every affected repair | none |
| operator-signoff | approved | current executed approval follows every affected repair | none |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Dependencies

- No external wave dependencies.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated token savings use phase-unique returned source versions and mapped workflow prompts, minus recorded request and response tokens. Saved model output or avoided tool loops count only through quality-equivalent paired evidence.

| Stage | Tool calls | Estimated token savings |
| --- | ---: | ---: |
| plan | 347 | 2,685,571 |
| implement | 54 | 81,032 |
| review | 209 | 6,657,983 |
| **Total** | **610** | **9,424,586** |

<!-- wave:context-efficiency-state {"generation":410,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":54,"content_source_credit":100645,"derived_artifact_credit":0,"direct_net":81032,"estimated_tokens_saved":81032,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":1721,"response_debit":20443,"source_credit_count":5,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2551},"plan":{"calls":347,"content_source_credit":3475034,"derived_artifact_credit":1725,"direct_net":2685571,"estimated_tokens_saved":2685571,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":48175,"response_debit":753089,"source_credit_count":138,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":10076},"review":{"calls":209,"content_source_credit":7299350,"derived_artifact_credit":3462,"direct_net":6657983,"estimated_tokens_saved":6657983,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":61503,"response_debit":709000,"source_credit_count":225,"source_credit_drop_count":0,"structural_source_credit":123785,"workflow_prompt_credit":1889}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":610,"content_source_credit":10875029,"derived_artifact_credit":5187,"direct_net":9424586,"estimated_tokens_saved":9424586,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":111399,"response_debit":1482532,"source_credit_count":368,"source_credit_drop_count":0,"structural_source_credit":123785,"workflow_prompt_credit":14516},"wave_id":"1x5tr scanner-correctness-and-visibility"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 17 | 0 | 11 | 12,254,230 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":11,"estimated_exploration_avoided":12254230,"surfaced_events":17} -->
<!-- wave:exploration-avoided end -->

# Wave Record

Owner: Engineering
Status: paused
Last verified: 2026-10-15
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `20qrv windows-review-follow-ups`
Title: Windows Review Follow Ups

## Objective

Prepare bounded repairs for source-grounded Windows portability concerns: owned archive cleanup/publication, consistent reparse classification, complete lock traversal and precise diagnostics. Synthetic oracles establish branch contracts, not native Windows, OneDrive, WSL2 or reboot qualification. Unsupported bytecode warm-up changes are deferred. Preserve ownership, no-clobber publication and permission safety throughout.

## Changes

Change ID: `20qrr-bug embedded-archive-ownership-on-windows`
Change Status: `implemented`

Change ID: `20qrs-bug reparse-tag-and-junction-classification`
Change Status: `implemented`

Change ID: `20qrt-bug lifecycle-lock-scan-windows-identity`
Change Status: `implemented`

Change ID: `20qru-bug windows-path-and-diagnostic-fixes`
Change Status: `implemented`

## Participants

- Coordinator: Coordinator
- Write-owning roles: Implementer after readiness; coordinator owns lifecycle records
- Requested review lanes: code-reviewer, qa-reviewer, architecture-reviewer, security-reviewer, docs-contract-reviewer, release-reviewer, performance-reviewer
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer, release-reviewer, performance-reviewer, security-reviewer

## Wave Summary

Delivered retained/embedded archive ownership portability, name-surrogate reparse classification, complete zero-identity lock scanning, and bounded path/permission/BOM/shim diagnostics. Durable proof tolerates device drift while current-operation identity and hash checks remain strict. Native Windows, WSL2/drvfs and reboot qualification remain unverified; operator probes are in docs/references/native-windows-support.md.

Intentional deferral — `20qru-bug windows-path-and-diagnostic-fixes`: [~] AC-2: Warm-up skip/count remedy intentionally deferred during 2026-10-15 readiness: actual child returns success when compile_dir returns False, so the stated failure premise is unsupported. No timing or cache-warmup changes in this wave.

## Watchpoints

- Watchpoint: Synthetic metadata and real POSIX controls passed; they do not establish native Windows/WSL2/reboot behavior. Canonical native-support guidance retains the field probes and by-path race limits. Shared upgrade/contained-file edits were serialized, independent security review passed, and the unsupported warm-up remedy remains deferred.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| CODE-QRV-APPEND-FIXTURE | do_now | no | completed | code-reviewer, qa-reviewer, docs-contract-reviewer |
| CODE-QRV-IDENTITY-CENSUS | do_now | no | completed | code-reviewer, qa-reviewer, docs-contract-reviewer |
| QA-QRV-LAYOUT | do_now | no | completed | qa-reviewer, code-reviewer, docs-contract-reviewer |
| QRV-RD1 | do_now | no | completed | code-reviewer, qa-reviewer, architecture-reviewer, security-reviewer, council-readiness |
| QRV-RD2 | do_now | no | completed | architecture-reviewer, security-reviewer, qa-reviewer, council-readiness |
| QRV-RD3 | do_now | no | completed | security-reviewer, architecture-reviewer, qa-reviewer, docs-contract-reviewer, council-readiness |
| QRV-RD4 | do_now | no | completed | architecture-reviewer, security-reviewer, qa-reviewer, performance-reviewer, council-readiness |
| QRV-RD5 | do_now | no | completed | security-reviewer, architecture-reviewer, qa-reviewer, code-reviewer, council-readiness |
| QRV-RD6 | do_now | no | completed | code-reviewer, qa-reviewer, performance-reviewer, docs-contract-reviewer, council-readiness |
| QRV-RD7 | do_now | no | completed | qa-reviewer, docs-contract-reviewer, release-reviewer, council-readiness |

*Machine review state — 10 findings; current: do_now 10, maybe_later 0, dont_do_later 0, not_issue 0*
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

- No external wave dependencies. Declare intra-wave dependencies with a `Depends On:` line containing full backticked change ids in each change's block under `## Changes`.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| plan | 184 | 3,502,557 |
| implement | 37 | 222,601 |
| review | 81 | 720,009 |
| **Total** | **302** | **4,445,167** |

<!-- wave:context-efficiency-state {"generation":233,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":37,"content_source_credit":255049,"derived_artifact_credit":0,"direct_net":222601,"estimated_tokens_saved":222601,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":1147,"response_debit":34411,"source_credit_count":12,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3110},"plan":{"calls":184,"content_source_credit":4243697,"derived_artifact_credit":9067,"direct_net":3502557,"estimated_tokens_saved":3502557,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":59064,"response_debit":695411,"source_credit_count":170,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":4268},"review":{"calls":81,"content_source_credit":865018,"derived_artifact_credit":0,"direct_net":720009,"estimated_tokens_saved":720009,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":2418,"response_debit":142591,"source_credit_count":35,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":0}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":302,"content_source_credit":5363764,"derived_artifact_credit":9067,"direct_net":4445167,"estimated_tokens_saved":4445167,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":62629,"response_debit":872413,"source_credit_count":217,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":7378},"wave_id":"20qrv windows-review-follow-ups"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 30 | 0 | 19 | 9,850,781 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":19,"estimated_exploration_avoided":9850781,"surfaced_events":30} -->
<!-- wave:exploration-avoided end -->
## Review checkpoints

2026-10-15 final delivery: Four portability follow-ups are implemented: embedded/retained archive ownership, precise reparse classification, directory identity scanning and bounded path/input/permission diagnostics. Native Windows, WSL2/drvfs and reboot probes remain explicitly unverified; operator probes are in docs/references/native-windows-support.md. The warm-up requirement remains legitimately deferred because its reported exit failure was disproven. Original full isolated red-team primer preceded separate architecture, security, QA and reality seats plus rotating docs. Chair grouped code/release/performance in one disclosed independent context. Six test/doc integration findings were collected, repaired in one bounded pass and independently reverified by fresh QA/code/docs contexts (39, 9 and 7 selected passing tests respectively, each with known-bad controls and zero skips). Original architecture/security source judgments were retained against unchanged production hashes; no second full council is claimed. Council agreed on scoped delivery with no remaining material finding or disagreement. The alternative of extra cleanup hashing/session markers was rejected in favor of existing proof and fresh identity controls. Final 47-path binding: 3090aafeb2c958ac40e3f6997800ba241f9f5f50c32cdbcc847307618ed9524f. These are implementation and review results, not release or native-platform qualification.

2026-10-15: operator requested preparation and review only. Independent council reviews actual source and bounded synthetic controls, with isolated primer before fixed seats and rotating review. Native Windows/WSL execution is not claimed. Inherited capable reviewers address cross-module ownership and platform contracts; runtime model identity is not exposed. Source remains frozen; no implementation, full suite, close, commit or push requested. Wave 20ppj remains separate and readied; shared-file implementation must be serialized and its reviewed contracts preserved.

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-10-15 | One bounded four-plan repair addresses QRV-RD1–RD7. Native qualification remains pending; warm-up AC-2 explicitly deferred after source falsified its premise. No implementation. | Owning Requirements/ACs and typed findings |
| 2026-10-15 | Implementation and independent repair review complete; leave paused for operator closure. Full shared qualification ran 11,816 tests / 200 files / 12 skips in 736.347 seconds. It was red from the repaired test-integration failures and the unrelated deferred checklist scaling ratio (8.47 versus limit 8); no timing waiver, benchmark pass or fresh green full-suite receipt is claimed. After the bounded test/doc repairs, the stable protected focused run passed 420 tests / 11 modules / zero skips, including the repository-state guard, and the exact identity census separately passed with its three existing mutation controls. Unchanged production coverage comes from the full run plus earlier focused and independent guard controls; the entire full suite was not repeated merely for a timing pass. | Typed terminal findings: QA-QRV-LAYOUT; CODE-QRV-APPEND-FIXTURE; CODE-QRV-IDENTITY-CENSUS; shipped test modules and native-support probe notes. No new evidence folder, close, commit, push or package. |
| 2026-10-15 | Closure retrospective and cleanup: reviewed concrete memory proposals without creating candidates. Drafts duplicate canonical contracts/tests or infer source fragility from readiness findings; no distinct durable action was justified. Keep rationale here and current support guidance. Folder contains only wave.md, admitted change docs and immutable events.jsonl; no redundant evidence folder or scratch artifact needs deletion. Operator authorized close, commit and push; a fresh repaired-tree full suite is required for the stale receipt. Timing investigation stays deferred, without a new waiver. | memory_propose dry-runs; existing regression controls; current close dry-runs. |
| 2026-10-15 | Operator authorized close, commit and push. Final repaired-tree canonical run completed 11,816 tests / 200 files / 12 skips in 841.468 seconds; every check except test_indexer.SQLiteDriftDetectionScaleTests.test_100k_rows_contention_safe_budget passed (1.063578 seconds versus 1.000 seconds). Timing investigation remains deferred; no threshold change, waiver, unchanged retry or green receipt was produced. Closure stays paused because the existing close tool requires a current green receipt and has no exception path. Commit/push the reviewed implementation with this explicit limitation. | python .wavefoundry/framework/scripts/run_tests.py; exact result in this record; temporary full log /private/tmp/three-wave-close-qualified-default.log. |


## Readiness outcome

2026-10-15: all seven required lanes and council approve receipt review-policy-ebadb176025c278e7481. Full isolated adversarial primer preceded architecture, security, QA and reality seats; docs-contract was the rotating seat. Chair supplied code, release and performance assessments in one disclosed shared context, not three independent votes. First round unanimously required seven bounded plan corrections. One four-document repair and one focused verification cleared QRV-RD1–RD7. One focused challenge distinguished stale ancillary wording from a material requirement; the precise amended requirements and ACs govern. No remaining blocker.

Corrections: no-clobber publication or controlled refusal; durable root/file proof compatibility separated from fresh deletion identity across all consumers; generic name-surrogate and unknown-metadata refusal; fresh no-follow lock-walk metadata and consistent fallback keys; actual replacement-descriptor mode proof; unsupported warm-up remedy deferred; BOM and shim diagnostics narrowed to existing contracts. The lock entry cap remains phase-2-only, not a bound on the legitimate real-directory walk. Native Windows, WSL2, OneDrive and reboot execution remain unverified despite earlier broad rationale wording.

Evidence includes scratch hard-link collision/replace counterexamples, actual new-fd modes under umask, zero-identity/path-key controls, unknown-surrogate/cloud tag controls, exact warm-up code returning success for a false compile result, BOM checks, and plan-contract assertions with omitted-contract negative controls. Focused chair ran 12 operative artifact checks and seven negatives; other seats executed and disclosed their own bounded checks. This approves plan feasibility and testability, not future runtime behavior. Official source checks: [CPython Windows link implementation](https://github.com/python/cpython/blob/3.13/Modules/posixmodule.c), [Python DirEntry.stat contract](https://docs.python.org/3.13/library/os.html#os.DirEntry.stat), and [Microsoft reparse tags](https://learn.microsoft.com/en-us/windows/win32/fileio/reparse-point-tags).

20qru AC-2 is intentionally deferred: actual source disproved the warm-up failure premise, so no cache-warmup or timing work is admitted. All other acceptance checks remain implementation obligations. No full suite, source implementation, native platform test, closure, commit or push performed. 20ppj remains separately readied; shared source edits must be serialized when implementation is authorized.

## Implementation allocation

2026-10-15: narrow implementer owns archive/guard pack lifecycle; another implementer owns predicate parity then lock scan identity; coordinator owns diagnostics/BOM/shim/permission changes after predicate ownership release. Inherited capable model for platform/ownership reasoning; actual runtime identity unavailable. Disjoint edits serialized at shared files. Final canonical suite and delivery review follow settled source across the batch.

## Implementation checkpoint

2026-10-15: all four changes implemented; declared warm-up deferral retained. Focused predicate/lock/runtime/cache/contained tests: 209 / 3 skips; archive portability 12, index guard 45, protocol 44 and model bundle 29 passed. Root diagnostics and record controls passed; setup fixture permission-only failures passed under their required temp-file access. Named guard mutants detected. Pause for 20tpo; final batch canonical qualification and independent delivery review pending. Native Windows, WSL2, cloud, drvfs and reboot probes remain unverified.

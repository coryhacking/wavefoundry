# Final Install Reliability Review

Owner: Engineering
Status: active
Last verified: 2026-09-22

## Scope and operator decision

The operator requested final review for closure and external Windows testers after the next release. Native AC-3/AC-6 and native portions of broader diagnostics are deferred, not passed. post-release-windows-validation.md retains the branch matrix, standard-user/policy cases and fresh-host checks. Portable correctness, accurate guidance, required python3, source drift protection and no environment mutation remain required.

## Standard-depth adversarial primer

Fresh context `/root/final_install_primer`, read-only source review, no executed/native claim. Strongest challenge: the diagnostic itself has untested native branches, not only repair. Best alternative: retain the explicit operator deferral and a small external branch matrix instead of adding a new launcher. Questions: verify version JSON integer handling and resolution versus actual process identity, or retain them explicitly in external qualification; preserve interpreter/MCP/native-qualification distinctions, opt-in applicability, optional CHANGELOG checks and sync permission boundaries.

## Independent lanes

Final verdict: APPROVE within the operator-amended qualification scope. No confirmed implementation blocker remains. Native Windows execution is unverified, not passed.

| Context | Remits | Independent evidence |
| --- | --- | --- |
| /root/final_install_code | Code and architecture | 29 focused tests pass; server_impl AST unchanged except sync docstring; three valid mutants killed. Architecture approval conditioned on the timing correction, independently reverified below. |
| /root/final_install_qa | QA | 117 tests: 116 pass, one intentional native skip; independently recomputed current 9,550-test receipt; three valid mutants killed. AC-1/2/4/7 supported in adjusted scope; AC-3/6 deferrals legitimate. |
| /root/final_install_security_docs | Security, docs and council synthesis | 44 tests pass without skips; three valid mutants killed; fixed argv, no shell/policy bypass/environment mutation, consumer opt-in and renderer ownership confirmed. |

Each lane had a six-minute budget and targeted-mutant sweep rule; whole-file sweeps only for survivors. All 34 reviewed paths matched at each lane's start and end. These are three fresh specialist contexts with paired remits, not five independent contexts.

## Mutation results

| Lane | Valid mutation | Detecting test / outcome |
| --- | --- | --- |
| Code and QA, independently | Restore strict skip bypass | test_strict_check_cannot_be_skipped: expected SystemExit absent; killed |
| Code and QA, independently | Discard timeout output | test_timeout_retains_bounded_output_even_when_subprocess_returns_bytes: missing stdout; killed |
| Code and QA, independently | Force mandatory source checks on consumers | test_consumer_with_packaged_scripts_and_own_docs_is_exempt: unexpected errors; killed |
| Security/docs | Enable shell=True | test_probe_failures_preserve_observation_without_claiming_old_version; killed |
| Security/docs | Accept Boolean version components | Same failure-observation regression; killed |
| Security/docs | Remove optional CHANGELOG validation | test_optional_changelog_claim_still_runs_for_consumer; killed |

Initial controls patching obsolete/directly imported bindings were invalid experiments. Reviewers corrected bindings to the actual tested producer and reran; only those valid outcomes are counted. No valid survivors. No native PowerShell execution claimed.

## Documentation correction and council

After all frozen reviews finished, coordinator aligned testing-architecture.md, native-windows-support.md, guidance-propagation.md, plan scope/handoff and wave objective with the operator's post-release qualification decision. Only the two architecture/runbook paths changed among the 34 fingerprinted paths; final-review-fingerprint-after-docs.json records the corrected snapshot. The security/docs reviewer independently reread all corrections and verified the new fingerprint, clearing the architecture timing condition and approving docs, security and council readiness/delivery. No runtime source changed.

Standard-depth council roster: earlier independent red-team primer; code/architecture paired context; QA context; security/docs paired context and synthesis. Rotating seat: docs-contract-reviewer. Strongest challenge: diagnostic native semantics remain untested. Strongest alternative: hold release until native testing. Operator selected post-release testing; retain the explicit deferral and branch matrix. No unresolved disagreement or demonstrated defect is excused by that decision.

## Verification and retention

Existing canonical suite: 9,550 tests, 123 files, 13 intentional skips. QA independently matched inputs_hash ba0feb769723f8a149314e339847b8f48bfbe844d794da56f19a97cdbec5c5eb to the current framework tree. No redundant full-suite run; subsequent changes are docs-only. Full docs validation passes.

Retain both fingerprint files to distinguish initial reviewed state from the narrow documentation correction; retain readiness, implementation, propagation, external protocol and typed ledger as unique evidence. No disposable scratch artifact in the wave folder. Memory checkpoint produced zero candidates. Closure and commit remain operator-owned.


## Close dry-run

Prepare passed with receipt review-policy-87cce96d1a31c1090b1e and all current specialist/council readiness and delivery approvals. Close dry-run passed lint, garden and current framework receipt checks. Only operator signoff remains; the wave has not been closed or committed. Scanner advisories list existing binary/compressed/presentation files skipped, without claiming complete scan coverage.

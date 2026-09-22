# Independent code review — 1ymzq

Owner: Engineering
Status: active
Last verified: 2026-09-22

Reviewer: fresh code-reviewer context `/root/split3_code_delivery`; no implementation edits. Baseline: `4a8b8951`. Review budget: 12 minutes; sweep: targeted tests per mutant, whole-file escalation only for survivors. No mutant survived, so no escalation was needed. Repository remained read-only; executable mutations were confined to `/private/tmp/1ymzq-code-review-scratch`.

Verdict: **approve the reviewed implementation and refreshed plan readiness; no blocking implementation finding observed. Do not use this report as approval of R2, completion of index AC-5, or wave closure.** R2 was explicitly pending in the review packet and was not evaluated. Framework 9,508-test receipt was not independently replayed or approved by this lane.

## Fingerprint and retrieval

Initial fingerprint matched all supplied paths. During review the coordinator reported six documentation metadata refreshes, invalidating v1 for those paths. V1 is superseded. Final reviewed fingerprint is `/private/tmp/1ymzq-delivery-fingerprint-v2.json`, SHA256 `7d69750f1514d43c92f20b5b68749688b2776ccb5862b5bacd4c66d249808577`; independently recomputed git hash-object values all match. V1-to-v2 changed only the six architecture/review documentation files; no executable/test path moved. Their current diffs were read. Code results remain bound to identical code bytes; this report makes no assertion that v1 stayed frozen.

Read canonical role/review guidance and five admitted plans. MCP code_outline/code_read inspected index ownership, containment implementation, CE projection call-time binding, handler structural tests and focused test inventories. AST/git-diff probes were necessary gapfill: indexed excerpts do not establish complete relocation equivalence, absent declarations, object parity, or baseline-to-working-tree diffs. No semantic-answer-only conclusion was used.

## Independent reference and observed evidence

Reference: independently loaded committed `4a8b8951:server_impl.py`, combined with the plans' explicit preservation contracts. Parsed every moved definition, normalized only local `import server_impl` and `server_impl.<name>` qualification, and compared ASTs. All **111 functions** matched exactly; **32 moved module-level named objects** matched exact assignment ASTs. No removed definition was unaccounted for. Among remaining top-level definitions, only `resolve_path_under_root` and `_contained_wave_review_paths` changed; registration closures, ImplHandler, middleware and index-monitor policy matched the committed ASTs. This is strong mechanical evidence, with the explicit limitation that stripping root qualification cannot itself prove dynamic rebinding behavior.

That limitation was addressed through scratch execution: 30 tests passed, zero skips, covering ContainedPathTests, WrapperContractTests, ResolvedComparisonTests, ContainmentCensusTests, ContainmentReloadTests, HandlerStructureTests, HandlerResponseTests and HandlerReloadTests. The modified-scratch reload tests invoke registered/public paths and prove replacement code serves after reload across handler families and primitive. The complete partitions/re-export identities, including index mutable state, pass. Public response exercises include docs sync and secrets paths. ResourceWarnings for two subprocess objects appeared in response tests; the run completed successfully and no assertion was skipped.

Two additional selected source-guard tests passed: `test_unknown_acquisition_preserves_pending_work` and `test_publication_contention_releases_source_guard`. The real-monitor test passed baseline and failed its call-time-binding mutant (below). Code inspection preserves source guard before publication lock, `wait=False` for automatic work, and unchanged failed-publication/pending behavior.

Eleven tests passed in `test_index_optimize_contract`, `test_record_layout_census`, and `test_index_handler_identity`, zero skips. Optimize tests create real index state through the canonical producer; assertions and optimize producer remain unchanged, with only the two moved mock owners repointed. Index-handler edit changes production identity independently of membership discovery. R2 cannot therefore be silently compared as an unchanged evaluator identity.

Containment caller diffs preserve original strictness, resolution order, stronger parent/file/symlink restrictions, returned spelling and exception scopes at sub-clause adopters. The pure entry point performs only containment, avoiding newly introduced filesystem uncertainty. The renderer/TechDocs matrices exercise missing write targets, aliases, symlink escapes and exception outcomes; the unchanged indexer helper remains outside adoption. Windows behavior here is portable-path/contract coverage, not native Windows execution.

## Mutation table

All mutants were reverted in scratch immediately after execution. Named baseline tests passed before mutation.

| Mechanism | Mutation | Failing test / observation |
|---|---|---|
| Containment boundary | Always return candidate | `ContainedPathTests.test_parent_escape_with_missing_tail`: outside path returned instead of None |
| Symlink-component policy | Disable S_ISLNK refusal | `ContainedPathTests.test_leave_and_reenter_link`: inside final path accepted despite prohibited component |
| Python 3.13 unresolved-loop uncertainty | Remove non-strict stat probe | `ContainedPathTests.test_loop_refused_on_each_interpreter_branch`: unresolved loop returned |
| Pure comparison | Add candidate.resolve() | `ResolvedComparisonTests.test_pure_helper_performs_no_filesystem_work`: explicit resolve sentinel fails |
| CE call-time patch transparency | Use handler-local config reader | `SourceGuardTests.test_same_process_build_excludes_monitor_and_unlocked_carrier_allows_write`: bounded real monitor never reaches index_source_busy |
| Old-tree upgrade fallback | Re-raise ImportError instead of resolving server fallback | `RuntimeLockCutoverMigrationTests.test_cutover_module_absence_uses_installed_modern_stop`: expected cutover stop fails |

Reproducible mutation runner: `/private/tmp/1ymzq-code-mutations.py`; outcomes `/private/tmp/1ymzq-code-mutations.json`, log `/private/tmp/1ymzq-code-mutations.log`. The pure-comparison extra mutant was executed separately as recorded in the tool transcript. Initial isolated upgrade test launch lacked PYTHONPATH and failed module import; that attempt was invalid evidence, corrected with explicit scratch scripts PYTHONPATH, and both baseline and mutant were rerun successfully. No import-error launch is counted as known-bad detection.

## Refreshed readiness

Approve the actual updated plans under the coordinator's new readiness receipt `94b63f24a5c63152fa15`: index inventory now correctly states 53 definitions/12 objects, with domain-preserving dormant helpers and child PID ownership; overall 111 relocation count is independently corroborated. The two optimize mock-owner changes and two record-census filename updates retain behavior/assertions and are necessary consequences of relocation, not broadened product scope. Current containment plan's pure-already-resolved comparison preserves stronger callers' failure contracts. The executed containment census includes deliberate new-helper polarity and stale allowlist controls; these are readiness-safe known-bad controls, supplemented by delivery mutations. No unresolved implementation decision or unimplementable required AC was identified. Pending R2 remains an explicit unmet required delivery criterion, not a readiness defect or permission to mark it complete.

## Primer response and limits

Addressed the adversarial concerns with both relocation differential and executable boundaries: no extra resolution in pure helper, realistic symlink/missing-target cases, actual modified reload, mutable identity assertions, active CE patch/interlock, old-install fallback control and distinct evaluator production identity. I did not exhaustively mutate every preserved historical constant, test native Windows, run every dashboard process scenario, independently repeat the full framework suite, or evaluate R0/R1/R2 ranking metrics. These are bounded review limitations, not falsely claimed green checks. Full runtime semantic equivalence remains broader than finite tests and AST parity.

Evidence integrity for this lane's bounded readiness and implementation probes:

```json
{"test_ran_without_unintended_skip":true,"public_path_reached":true,"boundary_values_realistic":true,"assertions_non_vacuous":true,"known_bad_detected":true,"known_bad_detection_method":"focused-mutation"}
```

`fresh_context=true`, `independent=true`. No typed lifecycle state was written by this reviewer. Coordinator must preserve the outstanding R2/AC-5 limitation when recording phase-specific evidence.

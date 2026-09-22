# Final handler extraction architecture review

Owner: Engineering
Status: active
Last verified: 2026-09-21

## Verdict

Final closure-readiness currency check: architecture readiness, architecture delivery and Council readiness synthesis approve `review-policy-0bbe4d004de7d941414a`. Final AC/task/status reconciliation changes no reviewed scope. Independently read the completed plans, delivery report and receipts: framework receipt is `ok`, 9,481 tests, inputs hash `58bd9cc3ca90dfa056e3d7c7bd5ecbe01661aa25db1133e37a567e9eb1e020fb`; coordinator reports 12 intentional skips. After receipt SHA-256 `4ae11e8e97e7604eb6aa9479e9c989b896b9e69e6ceb67a088405d190c40f0e0` has verdict pass, no invalidation reasons, comparison violations or operator-review reasons. Supplementary fresh-before comparison has verdict pass and no violations; it remains computed arithmetic, not a separate signed gate receipt. Product hashes match this review. Thus the previously pending suite and after-benchmark obligations have supplied evidence; QA owns independent identity recomputation. Earlier pending statements below are historical checkpoint limits. This same independent worker uses phase-specific recording IDs solely to avoid operation-identity collisions; they do not represent fresh review voices. No wave closure is authorized or performed by this judgment.

Approve architecture delivery for the frozen TechDocs and memory extraction. No blocking architecture findings. Context `1ymzk-architecture-final-20260921` continues this independent reviewer's inventory and TechDocs checkpoint; it is not an additional independent voice. Reviewer did not implement either extraction. Existing host capability was selected for dependency/loader subtleties; actual runtime identity is unknown.

The prior `architecture-techdocs-review.md` checkpoint remains applicable: its module source is unchanged, and final handler tests exercise its reload alongside memory and graph. This verdict does not discharge the coordinator's full-suite or after-benchmark obligations.

## Verified boundaries

Independent comparison against `f7f95d5e` found exact `register_mcp_surface` source equality; all 29 memory definitions match normalized ASTs after removing only authorized composition-root qualifications/function-local imports; all five lifecycle/crediting stayers match exact old source segments; all 14 caps/cache/sentinel/regex object definitions match old ASTs. No storage schema or connection ownership changes were introduced.

Memory's direct imports retain `_diagnostic` and the review-ledger reader at their owning modules. Shared helpers, `WaveIndex`, publication locking and `list_waves` remain invocation-time composition-root lookups. Re-export identity tests cover all 43 moved definitions/objects. `_memory_mod` retains the namespaced loader: an independent fresh-process probe confirmed it returns the same module as `server_impl._load_script('memory_records')`.

A fresh-process real CLI dry-run confirmed importing `memory_cli` does not import `server_impl`, then the first backfill response loads it and exits zero. This supports the docs' narrow lexical inversion claim, not a claim that CLI responses avoid loading the composition root. Lifecycle close, locked mint cost forwarding, upgrade backfill, capped advisories, purge failure and CLI patch seams were exercised. Two-cache assertions and corrected fixture descriptions honestly retain a same-interpreter test; they do not claim separate process/store identities.

The final static measured-tool closure and evaluator attribute-read/golden-anchor tests pass, including non-vacuity anchors. Their result remains bounded static evidence, not a universal dynamic-dispatch proof. Neither new handler belongs in `PRODUCTION_RETRIEVAL_MODULES`; the composition-root edit still requires the wave-level receipt pair. Current-state, domain-map and layering documents match ownership; baseline docs and their literal pins agree on the pending after receipt. Its temporary absence is not an architecture finding.

## Execution

All unittest commands used the canonical `/Users/coryhacking/.wavefoundry/venv/bin/python -B -m unittest` with `PYTHONPATH=.wavefoundry/framework/scripts:.wavefoundry/framework/scripts/tests`. Groups ran in separate interpreters, preserving the repository's isolation convention.

| Arguments after unittest | Observed | Log |
| --- | --- | --- |
| `test_handler_modules.HandlerStructureTests test_handler_modules.HandlerPackagingAndEvaluatorTests test_handler_modules.HandlerReloadTests` | 8 passed, 12.881s | `/private/tmp/1ymzk-arch-final-contract.log` |
| `test_memory_records.MemoryToolTests.test_purge_response_failure_preserves_body_and_gives_retry_route test_memory_records.ActionTimeAdvisoryTests.test_code_read_carries_capped_matching_advisories test_memory_records.SupersessionCostInheritanceTests.test_explicit_cost_wins_over_inheritance test_memory_records.TwoProcessCacheCoherenceTests` | 6 passed, 2.229s | `/private/tmp/1ymzk-arch-final-records.log` |
| `test_memory_backfill.HistoricalMemoryBackfillTests.test_cli_rewrite_forwards_complete_correction_contract test_memory_backfill.HistoricalMemoryBackfillTests.test_response_size_is_bounded_even_when_failure_text_is_huge test_memory_backfill.RootDefaultDiscoveryTests.test_memory_cli_defaults_to_repo_root_from_subdirectory` | 3 passed, 0.026s | `/private/tmp/1ymzk-arch-final-backfill.log` |
| `test_upgrade_wavefoundry.HistoricalMemoryUpgradeExtensionBootstrapTests.test_old_runner_hook_hands_candidate_publication_to_installed_runner` | 1 passed, 0.889s | `/private/tmp/1ymzk-arch-final-upgrade.log` |
| `test_phase_gates.PhaseGateTests.test_close_passes_with_real_delivery_approvals` | 1 passed, 1.908s | `/private/tmp/1ymzk-arch-final-close.log` |
| `test_docs_lint.EvaluatorEditBaselinePolicyPinTests` | 3 passed, 0.001s | `/private/tmp/1ymzk-arch-final-docpins.log` |

Total: 22 tests passed, zero skips. Actual scratch reload executes modified handler responses through the registered graph, TechDocs and memory callables. A separate fresh-process CLI probe performed `memory_cli.main(['backfill', '--root', temporary_root, '--mode', 'dry_run'])`, asserted composition-root import timing, and checked the namespaced memory loader identity; all passed.

## Focused mutation evidence

`PYTHONPATH=.wavefoundry/framework/scripts:.wavefoundry/framework/scripts/tests /Users/coryhacking/.wavefoundry/venv/bin/python -B /private/tmp/1ymzk-arch-final-probe.py` passed its baseline comparisons and detected all four intentionally bad variants. Log: `/private/tmp/1ymzk-arch-final-probe.log`. Mutants changed only text supplied to actual structural tests or a temporary re-export attribute in the probe process; no repository source was edited.

| Mechanism | Mutation | Detection |
| --- | --- | --- |
| Module ownership | Add module-top `import server_impl` to memory source read by test | `HandlerStructureTests.test_locations_import_boundaries_and_name_resolution` assertion |
| Lifecycle ownership | Remove the `_auto_populate_memory_for_wave` declaration from composition-root text | `HandlerStructureTests.test_memory_partition_and_reexport_identities` stayer assertion |
| Re-export identity | Replace root advisory alias with a different object | Same identity test, `_memory_advisories_for_path` assertion |
| Reload | Omit memory module from purge source | `LifecycleGateStructureTests.test_reload_purge_covers_direct_sibling_imports` reports `memory_handlers` |

No errors, unintended skips or survivors; no broad resweep was needed.

## AC coverage and limits

TechDocs AC-1–AC-4 architectural obligations retain prior checkpoint evidence and final reload/manifest checks. Memory AC-1–AC-4 architectural obligations are demonstrated by partition/identity/import/reload checks and targeted real-response seams. Memory AC-5 static closure/anchor portion is demonstrated; benchmark receipts remain coordinator-owned. Whole-suite portions of TechDocs AC-5 and memory AC-6 are pending independently. The reported mixed-process stale-import fixture failures were not reclassified as product defects or silently ignored: this checkpoint used isolated canonical invocations, while the coordinator must finish the full runner.

Integrity: `test_ran_without_unintended_skip=true`, `public_path_reached=true`, `boundary_values_realistic=true`, `assertions_non_vacuous=true`, `known_bad_detected=true`, `known_bad_detection_method=focused-mutation`.

Authorized local-safe temporary fixtures only. No live-index/model/network operations, product-source writes, or lifecycle writes. No claim about complete arbitrary runtime dispatch or benchmark quality. MCP outline/read were available and used; native AST/Git checks complemented them for exhaustive equivalence and fingerprint verification.

## Frozen SHA-256 fingerprints

### Current-packet readiness and focused repair recheck

Architecture readiness: approve against `review-policy-728303bb1c878ce02f91`. The current plans, corrected wave summary and inventory agree on 29 moved definitions, five staying definitions and fourteen objects. The task's 31-to-34 correction counts the already-reviewed partition; it adds no behavior or ownership scope. The Participants line now names only the inverted memory CLI, consistent with the governing objective and the retained evaluator handle.

Council readiness synthesis: approve the current packet. This is a focused currency synthesis of the prior red-team, architecture and docs-contract seat evidence in `readiness-review.md`, not a new independent run of those seats. The strongest challenge remains unclassified module state and source-text tests losing coverage after extraction; the inventory, identity obligations and owner-aware census repairs address it. The strongest alternative remains moving close-gate compositions as well; reject that expansion because their domain is lifecycle composition, while the present partition preserves existing seams. No unreviewed scope or readiness blocker remains. The coordinator confirmed both delivery findings terminal; the current ledger records completed repairs and fresh code/QA readiness approvals. Full-suite and after-benchmark completion remain delivery obligations.

Architecture delivery approval remains current after independent inspection of the two repaired test diffs. The literal census repoints exactly one existing exception to `memory_handlers.py`. The lock-order scanner now covers both owners, recognizes bare and `server_impl`-qualified calls, preserves the `>=8` non-vacuity threshold, and adds both spellings as negative controls. No product code changed. QA independently reports six passing tests and detection of the actual scratch moved-owner nested-lock mutant and old census-owner mutant; these are QA's execution results, not additional executions by this reviewer. No heavy tests were rerun during the coordinator's full-suite run.

Fresh SHA-256 readback matches the three product hashes below. Repaired tests: `test_record_layout_census.py` = `ed6c7e46ed076a0b0bbce8c69b8ceb17033ecca9969862958b13e61fdca3fc76`; `test_server_tools_lifecycle.py` = `77b07bb61745b1e817eade15fd5820c1c11d509c3c563960d903e5796ffefa23`. Commands: targeted `git diff --` for those tests, `shasum -a 256` for those tests and the three product files, and current plan/wave/readiness/ledger reads. MCP code-read access was verified; native Git supplied the exact diff and hash complement.

Context remains `1ymzk-architecture-final-20260921`: independent of implementation, reused across this review and synthesis, not fresh per perspective. The five integrity booleans and `focused-mutation` method above continue to describe the independently executed architecture delivery evidence; the currency recheck adds inspection, not another mutation sweep. No lifecycle records were written by this reviewer.

All 13 reviewed paths remained identical at review start and end:

| Path | SHA-256 |
| --- | --- |
| `.wavefoundry/framework/scripts/server_impl.py` | `f9ba2a24a5b77e77d8ca0d9aa8ce7a76577435721f6359ef01925b298a8f78f8` |
| `.wavefoundry/framework/scripts/techdocs_handlers.py` | `a77d31ec9ece75ced097b5d95425b116e3f5110edf4a1dc5f33767a4acdefed7` |
| `.wavefoundry/framework/scripts/memory_handlers.py` | `e160012ebe7fc7047afeed4c58c5147b2f130bc7b7954451b896d103c3945cd4` |
| `.wavefoundry/framework/scripts/memory_cli.py` | `c8280dd6e4ac1f3ce123182904ac7d1f81056ab4aeb4397bb114a345ae13751f` |
| `.wavefoundry/framework/scripts/tests/test_handler_modules.py` | `a5573b14f2b956f41d2e152c1770ab8b885de5fdbd03bf60f7bb39a246a2413e` |
| `.wavefoundry/framework/scripts/tests/test_memory_records.py` | `54a916bdb44ddd90de59defb5eca9bc99afe7e31f158f909120a0812aaeccaae` |
| `.wavefoundry/framework/scripts/tests/test_memory_backfill.py` | `ea3c49920b88a11a8601d5976d8be0209f21a6f23caf72d8efbc42daccba7c10` |
| `.wavefoundry/framework/scripts/tests/test_docs_lint.py` | `5d808ed2620ce3c806b2473c703d97d5e726f7855abf7002080320308bddfb07` |
| `docs/architecture/current-state.md` | `2f65669c6642049e2c304e3d3c72fbdbcc3953da5af9994afee57dd04d326515` |
| `docs/architecture/domain-map.md` | `77469dd3f68184feef86b09811d77c1820b7a961be14605e0ce642d9a47dafef` |
| `docs/architecture/layering-rules.md` | `9d94ac646a9f3ac720c70dfb671619ac3191c0f7b8ac074402c4d4c015b1b493` |
| `docs/architecture/testing-architecture.md` | `52603042a8bf9d3a3688d01a6186e02e44a76a5031db0787910848cc01f8d79d` |
| `docs/contributing/review-and-evals.md` | `46365d05fe66dc90e501d7d0cda261033a99c9043a7deaebce941d490673135e` |

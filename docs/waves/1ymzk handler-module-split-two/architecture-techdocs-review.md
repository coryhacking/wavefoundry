# TechDocs architecture checkpoint

Owner: Engineering
Status: active
Last verified: 2026-09-21

## Verdict and boundary

Approve the frozen TechDocs extraction checkpoint; no blocking findings. Context `1ymzk-architecture-techdocs-20260921`, independent of implementation. This follows the read-only inventory checkpoint, not a repeated readiness Council. Existing host capability was used for import/reload ownership analysis; runtime model identity is unknown.

`techdocs_handlers` owns three definitions and two caps. `_diagnostic` comes directly from `lifecycle_gate_support`; retained composition helpers use function-local `import server_impl`. No module-top composition-root or handler-sibling import, `_load_script` seam, new connection owner, persistence schema, registration source, or provider-policy change was introduced. The composition root re-exports all five names and purges the new module before re-import. The current-state, domain-map and layering documents accurately describe this boundary. Memory remains outside this checkpoint.

MCP `code_outline` and targeted `code_read` were used and callable. The previous inventory pass also used `code_references`, then `code_keyword` to recover test references not exposed by reference results; no shell code-navigation fallback was necessary. Native Git diff/hash and executable probes were used for verification.

## Executed evidence

Interpreter: `/Users/coryhacking/.wavefoundry/venv/bin/python`; environment: `PYTHONPATH=.wavefoundry/framework/scripts:.wavefoundry/framework/scripts/tests`; all Python commands used `-B`.

1. `-m unittest test_handler_modules.HandlerStructureTests test_handler_modules.HandlerPackagingAndEvaluatorTests.test_generated_manifest_contains_all_handler_modules test_handler_modules.HandlerReloadTests test_server_tools.TechdocsBaselineToolTests.test_dry_run_default_writes_nothing_and_reports_absent_paths` — four tests passed, zero skips, 3.426 seconds. Actual scratch reload serves the modified TechDocs handler through its registered callable; generated manifest includes the module; real baseline dry-run preserves fixture bytes. Log `/private/tmp/1ymzk-arch-techdocs.log`.
2. `-m unittest test_lifecycle_gates_structure.LifecycleGateStructureTests.test_reload_purge_covers_direct_sibling_imports test_server_tools_lifecycle.WaveCouncilPolicyTests.test_advisory_tags_appear_only_at_the_sanctioned_sites test_render_agent_surfaces.TechdocsBaselinePreconditionAndPathTests.test_only_the_two_declared_entries_call_the_command_function` — three tests passed, zero skips, 1.792 seconds. Logs `/private/tmp/1ymzk-arch-techdocs-census.log`.
3. `/private/tmp/1ymzk-arch-techdocs-probe.py` — exact source-segment equality for `register_mcp_surface` against `f7f95d5e`; normalized AST equality for all three moved definitions (only authorized server qualification and local import removed); absence of `_load_script`; two focused mutants killed. Log `/private/tmp/1ymzk-arch-techdocs-probe.log`.

| Mechanism | Mutation | Detecting test / observed failure |
| --- | --- | --- |
| Import ownership | Append module-top `import server_impl` to the text read by the real structural test | `HandlerStructureTests.test_locations_import_boundaries_and_name_resolution` rejects the forbidden import |
| Reload membership | Remove `techdocs_handlers` from the source returned to the real import-derived purge test | `LifecycleGateStructureTests.test_reload_purge_covers_direct_sibling_imports` reports missing `techdocs_handlers` |

Both mutants were in-memory source substitutions, not repository edits. Both failed assertions at the intended boundary, with no errors or skips. No survivors required full-file sweeps.

## Frozen fingerprint

`git hash-object` values were identical at start and end:

| Path | Object hash |
| --- | --- |
| `.wavefoundry/framework/scripts/server_impl.py` | `2a6bf0a22f95ce96f6d1a26016d4de3fabfe1305` |
| `.wavefoundry/framework/scripts/techdocs_handlers.py` | `868d10ac1f78edc925361c23a1a3f25586ef68d8` |
| `.wavefoundry/framework/scripts/tests/test_handler_modules.py` | `559296492d686ada4760fc775fdbdf2afcecdaef` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | `55ae6c31d15474ed188291ba52805c67e19d5ced` |
| `.wavefoundry/framework/scripts/tests/test_server_tools_lifecycle.py` | `3f26a9b82f66760c3a7199e4b159849fc1a0b223` |
| `.wavefoundry/framework/scripts/tests/test_render_agent_surfaces.py` | `128b9591804b3767f78acb0f73486ee9b431643c` |
| `docs/architecture/current-state.md` | `0e66a74ca1ce586073377176ea0295aecc090bf4` |
| `docs/architecture/domain-map.md` | `f73205bd37f9631a4cc88f054d79415a55c3a37b` |
| `docs/architecture/layering-rules.md` | `1850de7aef08168883f78af5a2976cbb717a96da` |

## Integrity and limits

`test_ran_without_unintended_skip=true`, `public_path_reached=true`, `boundary_values_realistic=true`, `assertions_non_vacuous=true`, `known_bad_detected=true`, `known_bad_detection_method=focused-mutation`.

Authorized local-safe fixture/scratch probes only; no live index, model, network, lifecycle mutation or product-source edits. Public paths reached were the actual registered scratch-reload callable and the real baseline response/renderer. The checkpoint does not claim the full suite, the retrieval benchmark pair, memory extraction or terminal wave approval. No test was silently skipped; those broader obligations remain coordinator-owned.

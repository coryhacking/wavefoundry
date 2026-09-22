# Final code and QA review

Owner: Engineering
Status: current
Last verified: 2026-09-21

## Verdict and identity

APPROVE the frozen implementation within this bounded independent code/QA scope. No blocking source or test findings. This is the same `/root/split_currency` worker that reviewed readiness, inventories and the TechDocs checkpoint; code and QA are two perspectives in one shared context, not two independent agents. The reviewer did not implement or repair source. Runtime model identity is unavailable. Context: `1ymzk-final-code-qa-20260921` (a review label, not a newly spawned context).

This report does not certify the coordinator-owned final whole-suite receipt or before/after live retrieval evaluation. Those remain required wave evidence. No live models/index builds or network probes were run by this reviewer.

## Reference and source proof

The independent reference is commit `f7f95d5e`, the approved move/stay inventory, unchanged public tool/handler goldens and existing consumer tests. Independent AST normalization removes only local `import server_impl` and the inventoried composition-root qualifications. All 29 moved memory functions and all 3 TechDocs functions are AST-identical to the baseline. The registration function and all five memory stayers are byte-identical. `git diff --name-only f7f95d5e -- .wavefoundry/framework/scripts/tests/fixtures` returns no files.

MCP `code_outline`/`code_read` worked for memory handlers; native AST and exact source diffs complemented indexed navigation. No inferred indexed completeness claim is made.

The four patch target changes preserve all original assertions and add invocation checks where required. The two-cache fixture now accurately describes its same-interpreter limit and asserts distinct cache identity; actual child-process coverage remains intact and passed. `memory_cli` forwards unchanged arguments through its new owner. The three docs-lint changes only repoint the evaluation filename; assertions remain unchanged. Local callable annotations and per-call dependencies match the inventory. Both caches and the sentinel are identity-reexported. Mint producer/re-entry, fence/finalize and lifecycle compositions remain mechanically identical.

## Executed checks

Interpreter: `/Users/coryhacking/.wavefoundry/venv/bin/python -B`; environment `PYTHONPATH=.wavefoundry/framework/scripts:.wavefoundry/framework/scripts/tests`. Independent shell processes were used for the memory records and backfill suites to avoid their documented module-reload interference.

- `-m unittest test_memory_records`: 217 passed, 15.543s.
- `-m unittest test_memory_backfill`: 46 passed, 7.107s.
- `-m unittest test_handler_modules test_tool_surface_golden test_mcp_tool_registry`: 51 passed, 24.034s. Includes real scratch reload through registry for graph, TechDocs and memory.
- `-m unittest test_memory_eval test_lifecycle_golden test_phase_gates`: 50 passed, 38.861s.

Total this final pass: 364 passed, zero skips. Earlier independent TechDocs checkpoint: 71 passed, zero skips; its dry-run byte preservation and actual producer lint checks remain applicable because TechDocs source is unchanged.

## Mutation table

Finite budget: targeted test for each mutation; only expand for a substantive survivor. All mutations were in-memory or temporary copies; repository source was not changed.

| Mechanism | Mutation | Detection |
| --- | --- | --- |
| Re-export identity | Delete `server_impl._MEMORY_KEY_BYPASS` | `HandlerStructureTests.test_memory_partition_and_reexport_identities` errors at the missing name |
| Action-time advisories | Replace server advisory response with empty list | `ActionTimeAdvisoryTests.test_code_read_carries_capped_matching_advisories` fails: advisory unexpectedly absent |
| Reload | Remove `memory_handlers` from scratch server purge list | Real `_RELOAD` script fails `fresh is not old` before registry success assertion |
| Lifecycle ownership | Remove `_auto_populate_memory_for_wave` definition in scratch source | Partition test fails staying-name subset assertion |
| Patch fidelity | Copy actual batch function globals so its proposal lookup bypasses owner mock | `HistoricalMemoryBackfillTests.test_response_size_is_bounded_even_when_failure_text_is_huge` fails `propose.assert_called()` |
| Writer fence | Return fabricated success token without establishing fence | `SeqlockCoherenceTests.test_fence_refusal_blocks_the_write` fails: `ok` instead of `error` |

Two initial non-discriminating probes are disclosed, not counted as kills: copying outer backfill-response globals leaves the inner batch lookup intact and passes; returning `None` from the fence still correctly refuses, so the refusal test passes. Both were replaced with actual boundary-changing probes above. No substantive surviving mutation remains in this finite set. Prior TechDocs mutants (dry-run write, bypass retained lint helper, omitted purge entry) were all killed at its checkpoint.

## AC assessment and limits

Memory AC-1: 29 AST-equivalent moves, 14 objects, five byte-identical stayers, import/identity/partition tests. AC-2: unchanged registration/goldens and 217 real response tests. AC-3: packaging/import tests and real scratch reload, with omitted-purge negative control. AC-4: unchanged CLI forwarding, four owning-module patch changes, faithful two-cache correction, retained real child process tests. AC-5: closure/not-joined and golden-anchor tests passed; live receipt pair remains coordinator-owned. AC-6: 364 independent focused tests passed; final whole-suite receipt remains coordinator-owned. The other named existing memory/upgrade suites are not independently rerun in this final budget; coordinator evidence covers them.

TechDocs prior checkpoint evidence remains retained, with final AST and public surface rechecked. No assertion weakening found. Static measured-tool closure is bounded by its direct-call traversal and does not claim arbitrary dynamic-dispatch completeness. AST parity alone does not establish binding identity; explicit identity/name-resolution tests, actual public calls and reload probes supply that separate evidence.

Minor documentation correction (`do_now`, nonblocking): the memory plan's inventory task says “thirty-one definitions” while its governing inventory correctly covers 34 total (29 move, 5 stay); make the task agree with that count. Requirement 1 separately explains 31 memory-named plus three other helpers, so scope is not ambiguous.

Integrity: `test_ran_without_unintended_skip=true`, `public_path_reached=true`, `boundary_values_realistic=true`, `assertions_non_vacuous=true`, `known_bad_detected=true`, `known_bad_detection_method=focused-mutation`. These statements apply to the executed checks, not the pending whole-wave evidence.

## Stable frozen SHA-256

All below were computed independently at review start and end and remained identical:

| Path under scripts | SHA-256 |
| --- | --- |
| server_impl.py | f9ba2a24a5b77e77d8ca0d9aa8ce7a76577435721f6359ef01925b298a8f78f8 |
| memory_handlers.py | e160012ebe7fc7047afeed4c58c5147b2f130bc7b7954451b896d103c3945cd4 |
| techdocs_handlers.py | a77d31ec9ece75ced097b5d95425b116e3f5110edf4a1dc5f33767a4acdefed7 |
| memory_cli.py | c8280dd6e4ac1f3ce123182904ac7d1f81056ab4aeb4397bb114a345ae13751f |
| tests/test_handler_modules.py | a5573b14f2b956f41d2e152c1770ab8b885de5fdbd03bf60f7bb39a246a2413e |
| tests/test_memory_records.py | 54a916bdb44ddd90de59defb5eca9bc99afe7e31f158f909120a0812aaeccaae |
| tests/test_memory_backfill.py | ea3c49920b88a11a8601d5976d8be0209f21a6f23caf72d8efbc42daccba7c10 |
| tests/test_docs_lint.py | 5d808ed2620ce3c806b2473c703d97d5e726f7855abf7002080320308bddfb07 |
| tests/test_server_tools.py | 8b5f26e9753822c412916bfb08aee742eec3e15c1fa9ec5afbbb331af375658c |
| tests/test_server_tools_lifecycle.py | 5e5448ee10670a481cef45616058cee757996eb80aecda8ebd65a8636202a705 |
| tests/test_render_agent_surfaces.py | 7ed6668c7cafd52a52a910ff52fdabb55291ba92ce743e0429295a0599737e9b |

## Whole-suite status received after focused review

Coordinator reports the canonical whole-suite run has marked `test_server_tools_lifecycle` failed (542 tests), with tracebacks still buffered. Consequently **whole-wave QA remains needs-more-evidence**, not an unconditional delivery approval. The bounded source approval and focused results above stand; no attribution is made before inspecting the actual failure. Investigate, repair if attributable, and independently reverify before restoring full delivery approval. No source repair was performed by this reviewer.

## Diagnosed delivery blockers

Independent canonical-interpreter reproduction of `test_record_layout_census` plus `PublicTypedEventProcessRaceTests.test_lock_order_is_lifecycle_then_publication_structurally`: six tests, three failures, 0.686s. Two typed initial-delivery findings were recorded through the MCP authoring tool after guided review:

- `CODE-DEL-1`: stale census allowlist owner at `test_record_layout_census.py:148`; the message moved to `memory_handlers.py:1046`. Repoint that exact owner while retaining the message exemption and stale-entry check.
- `QA-DEL-1`: lock-order source scan still reads only server source and recognizes only bare calls. Seven publication blocks remain there; six moved blocks use `server_impl.project_state_publication_lock` in memory handlers. Scan both owners, recognize bare and qualified publication/lifecycle calls, retain meaningful owner coverage and prove a nested lifecycle call in the moved module is detected. Lowering the count would hide the missing coverage.

Both are `do_now`, blocking required-AC verification defects, with focused code-reviewer and qa-reviewer repair/reverification. Product bodies remain baseline-equivalent; neither finding alleges a new lock-order execution defect. The coordinator separately reports dashboard checks pass outside the initial sandbox; that result is not independently certified here. No source repair was performed by this reviewer.

## Independent repair replay

Both findings independently reverified against frozen repaired tests. Six targeted tests now pass, zero skips, 0.766s. In-memory old-owner allowlist restoration reproduces both original census failures. An AST-validated mutation of the actual temporary `memory_handlers.py`, inserting `with server_impl._lifecycle_mutation_lock(root)` within its publication block at line 1078, fails the repaired structural test's violations assertion. The first attempt had invalid indentation and is excluded from evidence; the corrected mutation fails for the intended reason. Publication count remains 13 (7 server, 6 memory), threshold remains at least eight; excluding memory would fail that threshold. No unnecessary per-owner abstraction is required.

Repaired hashes stayed stable: census `ed6c7e46ed076a0b0bbce8c69b8ceb17033ecca9969862958b13e61fdca3fc76`; lifecycle tests `77b07bb61745b1e817eade15fd5820c1c11d509c3c563960d903e5796ffefa23`. Product hashes unchanged. Typed cycle-1 reverifications cleared both code-reviewer and qa-reviewer lanes for each finding, transparently performed by the same independent review worker, distinct from repair implementer. Whole-suite receipt remains coordinator-owned.

Current readiness packet correction from 31 to 34 definitions is editorial: it agrees with the already reviewed 29-move/5-stay partition, existing 14-object inventory, protected public surface and sequential checkpoints. No behavior scope or policy requirement changed. Code and QA readiness judgments remain approved on that corrected packet.

## Final whole-wave evidence verification

The final canonical receipt is green for 9,481 tests across 119 files (12 recorded skips, 283.551s). Independently recomputed `run_tests._hash_inputs()` equals its `58bd9cc3ca90dfa056e3d7c7bd5ecbe01661aa25db1133e37a567e9eb1e020fb`; product and repaired-source hashes remain unchanged. The reviewer’s focused runs had zero skips; the broader suite’s 12 skips are not silently counted as executed cases.

Independently read `docs/reports/retrieval-quality-1ymzk-after.json`: SHA-256 `4ae11e8e97e7604eb6aa9479e9c989b896b9e69e6ceb67a088405d190c40f0e0`, verdict pass, no invalidation reasons, comparison violations or operator-review reasons. The measured start/end token is identical: complete generation 1869, attempt `cdd9fa73f64945caaaaf0a97d6367b51`. Production identity recomputes exactly to `b5db05645898290795151280470532592bf311aca5fc12b660580c659882da0a`; evaluator identity and normalized fixture digest also match current source/corpus. There are 35 fixtures, 140 tool/fixture case rows and 22 resolved symbol anchors. Raw corpus JSON is normalized by `load_fixture_corpus` before digesting; hashing raw JSON directly is not the receipt recipe.

The signed after receipt compares against the standing reference. The valid fresh before receipt has no invalidation reasons but a fail verdict against that older reference. The supplementary fresh-before/after computed comparison binds both actual file hashes and generations 1861→1869, with evaluator/fixture/environment identity equal and production identity different as expected. Independently reran `compare_retrieval_receipts.compare` over those receipt objects: no violations and all seven critical floors pass. It is expressly supplementary computed arithmetic, not a signed gate receipt and not proof of same-generation identity. Code-ask holdout recall changes 0.57291667→0.59375 and nDCG 0.5233558→0.53066709; measured holdout quality does not regress. These observations do not claim broad retrieval improvement caused by the extraction.

Final code and QA verdict: APPROVE after the two terminal repairs, the current green whole-suite receipt and valid after benchmark. All required code/test/evaluation AC facts are supported. Current typed approval events use a delivery suffix solely to avoid phase identity collision; they remain the same independent worker and shared code/QA context, not additional independent voices.

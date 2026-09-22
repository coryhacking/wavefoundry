# Memory Handler Module

Change ID: `1ymzj-ref memory-handler-module`
Change Status: `complete`
Owner: Engineering
Status: completed
Last verified: 2026-09-21
Wave: `1ymzk handler-module-split-two`

## Rationale

The modularity kickoff (`docs/reports/wavefoundry-implementation-kickoff.md`, Slice 7) scheduled memory orchestration as the last and hardest extraction from `server_impl.py`. After `1y0h2` the file is 29,036 lines, and memory is its largest remaining family: thirty-one module-level definitions whose names carry the memory token, 2,124 lines, from `_memory_mod` through `memory_consolidate_response` plus `wf_memory_eval_response`, the two close-gate compositions and the three crediting extractors, together with three family helpers whose names do not carry the token (`_lifecycle_id_tokens`, `_credit_exploration_avoided_surface`, `_draft_view`), registered as ten tools (`memory_add`, `memory_propose`, `memory_backfill`, `memory_validate`, `memory_search`, `memory_brief`, `memory_reconcile`, `memory_purge`, `memory_consolidate`, `wf_memory_eval`), and fourteen module-level objects the family owns: the caps `MEMORY_BRIEF_CAP`, `MEMORY_SEARCH_CAP`, `MEMORY_QUERY_CHECK_CAP`, `MEMORY_QUERY_MIN_LOGIT`, `MEMORY_PROPOSE_CAP`, `MEMORY_CONSOLIDATE_GROUP_CAP`, `MEMORY_CONSOLIDATE_MEMBER_CAP`, `MEMORY_SUMMARY_EXCERPT_CHARS`, `MEMORY_BRIEF_CONTEXTS` and `MEMORY_ADVISORY_CAP`, the caches `_MEMORY_RECORDS_CACHE` and `_MEMORY_BETWEENNESS_CACHE`, the sentinel `_MEMORY_KEY_BYPASS`, and `_LIFECYCLE_ID_TOKEN_RE`. The family already has a home: `memory_records.py`, `memory_backfill.py`, `memory_supply.py` and `memory_eval.py` exist and none imports `server_impl`, but `memory_cli.py` imports `server_impl` at module top for two response functions, and `memory_eval.py` threads a single `srv` handle through its helpers for `_memory_mod`, `_memory_ranked`, `memory_search_response`, `WaveIndex` and `_load_script`. The kickoff asked for those back-references to be inverted.

The move follows the `1y0h2` recipe: the family goes to a new `memory_handlers.py`; the decorated closures in `register_mcp_surface` stay byte-identical; `server_impl.py` rebinds every moved name through one module-top `from memory_handlers import (...)` block, private names and module-level objects included (the two `1y0h2` blocks already import fifty-eight underscore names, and re-exporting a dict shares the object so `server_impl._MEMORY_RECORDS_CACHE.clear()` keeps working); the module reaches helpers that stay behind through a function-level `import server_impl`; the module joins the reload purge list; the golden tool-surface fixture proves the public surface unchanged.

The move criterion is domain ownership, not caller location, which is where the first draft of this plan contradicted itself. Memory-domain services move even when lifecycle or sibling code calls them, and the rebinding block keeps those callers valid: `_memory_advisories_for_path` (called by `code_read_response` in `codenav_handlers` and by three graph responses), `_memory_advisories_for_wave` (called by the audit, prepare and review responses; a structural twin of the path variant), `_memory_backfill_batch_locked` (called by `upgrade_wavefoundry` through `server_impl`, and pinned there by a source-text test), `_credit_exploration_avoided_surface`, `_draft_view` and `_lifecycle_id_tokens` (callers only inside the family; the last one's only dependency, `_LIFECYCLE_ID_TOKEN_RE`, moves with it). Two definitions stay in `server_impl.py` because they are close-gate lifecycle compositions that only call public memory entry points and emit lifecycle diagnostics: `_auto_populate_memory_for_wave` and `_memory_validation_diagnostics`; their eventual home is the lifecycle-gate modules, not this one. Three more stay because they belong to the context-efficiency crediting registry that this change leaves alone: `_state_sources_memory_validate`, `_state_sources_memory_propose` and `_state_sources_memory_views`, bound in the module-level `_STATE_SOURCE_EXTRACTORS` dictionary. So the family reached from outside is six definitions, not three, and the partition is a table the inventory commits, not two prose lists.

Helpers the moved code reaches and that stay behind, read as `server_impl.<name>` per call: `_load_script`, `_response`, `_graph_snapshot_module`, `_trigger_background_index_refresh_for_paths` and `WaveIndex` (used by `_memory_query_records` and `memory_search_response`, not only by `memory_eval`). Names `server_impl` itself imports from siblings are imported directly by `memory_handlers` from their owners (`_diagnostic` from `lifecycle_gate_support`, `read_review_event_ledger` from `review_evidence`, `record_paths`), with one exception: `project_state_publication_lock` is read as `server_impl.project_state_publication_lock` at call time because a test patches it on `server_impl` around `memory_reconcile_response`. `_memory_mod` keeps its `server_impl._load_script("memory_records")` indirection deliberately: `_load_script` registers the sibling under a namespaced key that `importlib.reload` re-executes, tests patch that seam and monkeypatch the objects it returns, and a plain `import memory_records` would create a second module object with split dataclass identity that the purge census would not demand an entry for.

Context-efficiency projection (ten definitions, 652 lines, one tool) is deliberately not in this change. It is interleaved with the middleware chain that `1y0h1` made explicit and with the quiet-period monitor that `1yj14` interlocked against index builds; readiness verified the boundary is clean in both directions (no memory definition calls a projection definition and none calls back; memory reaches context efficiency only through the exploration-avoided telemetry module).

## Requirements

1. The inventory is a committed, reviewed deliverable before any definition moves. It classifies all thirty-one memory-named definitions, the three family helpers without the token, and all fourteen module-level objects as move or stay, with every caller including test patch sites, dynamic patches, source-text anchors in tests and string-built targets; it records the measured-tool reachability closure and the golden-anchor scan. The Rationale's partition is its starting point; the table governs.
2. The decorated closures in `register_mcp_surface` stay byte-identical. `server_impl.py` rebinds every moved name through one module-top `from memory_handlers import (...)` block, so the ten closures, the staying definitions, `WaveIndex`, the sibling handler modules, the upgrade runner and every test that reads or patches `server_impl.<name>` keep resolving. Patch transparency is narrowed to what is true: a patch on `server_impl.<name>` is observed by staying callers and by moved code that reads `server_impl.<name>` at call time; it is not observed by a moved function calling another moved function by bare name. The known sites of that class are repointed to `memory_handlers` and listed: `test_memory_records.py` patching `_memory_mod` around `memory_purge_response`; `test_memory_backfill.py` patching `_memory_propose_response_locked` around `memory_backfill_response`, and its two `memory_cli` sites (`memory_validate_response`, `memory_backfill_response`), which become `memory_cli.memory_handlers.<name>`. The `1y0h2` rule that a patch through `server_impl` on a helper must assert it was called or be marked inert-by-design is extended to memory names.
3. `memory_handlers` never imports `server_impl` at module top and never imports another handler module; it reaches the staying helpers per call. It is appended to the reload purge list and imported by public name at module top, so both reload tests cover it. Names, tiers, parameters, docstrings, annotations and extra-argument validation are unchanged; the golden fixture does not change.
4. Back-references: `memory_cli.py` imports `memory_handlers` for its two responses and drops its module-top `server_impl` import; the first call still executes `server_impl` in full through the function-level import, the same cost as today, so AC-4 says "no longer imports" lexically and "transitively loads at first call" honestly. `memory_eval.py` is not inverted in this change: it threads one `srv` handle through four helper signatures for five attributes, two of which (`WaveIndex`, `_load_script`) do not move and one of which a test patches on `server_impl`; the rebinding block keeps every `srv.<name>` valid, and splitting the handle is a follow-up recorded in the Decision Log.
5. Standing evaluation. `server_impl.py` is a member of `retrieval_eval.PRODUCTION_RETRIEVAL_MODULES` and both changes in this wave edit it, so the wave owes a before-and-after receipt pair per `docs/contributing/review-and-evals.md`: a before-receipt on the pre-change tree with the index brought current and the evaluator run in the foreground, recorded before `1ymzi`'s first edit; an after-receipt on the delivered tree after this change; and the comparison. The before-receipt is written to `docs/reports/retrieval-quality-1ymzk-before.json` and the after-receipt to `docs/reports/retrieval-quality-1ymzk-after.json`, both run with `--baseline docs/reports/retrieval-quality-1y0bf-final.json`; `docs/contributing/review-and-evals.md` (Standing artifact) and `docs/architecture/testing-architecture.md` still name the superseded `post-1wybs` receipt as the reference and are corrected in this change to name `1y0bf-final` and then the after-receipt; `tests/test_docs_lint.py` (`EvaluatorEditBaselinePolicyPinTests`) pins the literal `retrieval-quality-post-1wybs.json` in both documents and the exact `--baseline` argument in the testing-architecture row, so the same change updates those pinned literals to the new receipt name or the docs-lint suite goes red. If the current evaluator identity cannot compare against the standing `1y0bf-final` report (the tree has already moved past it), the deviation is recorded the way `1y0h2` Requirement 11 did and the after-receipt becomes the new baseline. Separately, `memory_handlers.py` does not join `PRODUCTION_RETRIEVAL_MODULES`: three independent reachability closures from the four measured tools reach no memory definition (the only route, `code_read_response` calling `_memory_advisories_for_path`, is not measured). One test pins that: the module is absent from the list and its response names are disjoint from the measured closure and from the evaluator's attribute reads.
6. Golden-corpus anchors naming a moved definition are repointed in the same change; today none names a memory symbol, and the inventory re-derives this over `symbol` and `content` anchors.
7. Tests. The existing modules are the transport-free coverage and are repointed, not duplicated: `test_memory_records.py` (217 tests, building records through the canonical producers and driving every response including the fence and finalize path and the locked variants), `test_memory_backfill.py`, `test_memory_eval.py`, `test_storage_upgrade_resume.py`, `test_upgrade_wavefoundry.py`, `test_graph_snapshot_readers.py` and `test_record_layout_nested.py`; new tests in this change reach memory functions through `server_impl`, not by importing `memory_handlers` directly. This change adds: a `FAMILIES` entry with the ten tool names in `test_handler_modules.py` (yielding the location, no-top-import, name-resolution and manifest tests); an AST assertion that the five staying memory-named definitions remain in `server_impl.py`; one identity assertion per re-exported name reached from outside the module (`assertIs(server_impl.<name>, memory_handlers.<name>)`), covering the responses, the advisory and backfill services, `_memory_mod`, `_memory_ranked`, the caps, the caches and the sentinel; the reload proof generalized from `test_actual_reload_serves_modified_scratch_graph_handler` into a template over (module, response, tool) run for graph, techdocs and memory; and the `PRODUCTION_RETRIEVAL_MODULES` not-joined test. Self-mutants named by test: a duplicate definition left in `server_impl.py` fails the location test; a module-top `server_impl` import fails the boundary test; an omitted purge entry fails the import-derived purge test; a dropped re-export of `_memory_advisories_for_path` fails `test_code_read_carries_capped_matching_advisories`; a dropped re-export of any other reached name fails its identity assertion; a moved close-gate composition fails the staying-names assertion.
8. Two-process coherence. `test_memory_records.py`'s `TwoProcessCacheCoherenceTests` executes `server_impl.py` a second time as an independent instance to model two MCP processes with distinct caches and distinct `index_state_store` instances. After the move the second instance re-runs the purge block and re-imports a fresh `memory_handlers`, so its cache stays distinct, but moved functions' per-call `import server_impl` resolves the first instance, so the second instance's handler path uses the first instance's `_load_script` and store. Two readiness reviewers traced the three tests and expect them to pass on on-disk state, but the class docstring's premise is weakened for moved code. The inventory records this; the class docstring is corrected; and an explicit `assertIsNot(p1._MEMORY_RECORDS_CACHE, p2._MEMORY_RECORDS_CACHE)` is added so the class cannot pass vacuously. Retiring the class in favor of the real child-process coherence tests is the fallback if the traced expectation fails.
9. The lifecycle seam is preserved: `wf_close_wave_response`'s calls into the two staying compositions and the readiness, audit and review paths' calls into `_memory_advisories_for_wave` are exercised by the existing lifecycle tests unchanged (`test_lifecycle_golden.py` and `test_phase_gates.py` patch `_auto_populate_memory_for_wave`, a stayer). The memory playbook in `docs/agents/memory/` for `server_impl.py` is followed: the memory-mint re-entry seam and its paired producer and consumer are verified before and after the move, and the upgrade runner's seam test cluster is run because `upgrade_wavefoundry` reaches `_memory_backfill_batch_locked` through `server_impl`, spelled exactly that way by a source-text test.

## Scope

**Problem statement:** memory orchestration is the largest family still inlined in `server_impl.py`, a sibling module imports the monolith to reach it, and the recipe for moving a family safely is proven and idle.

**In scope:**

- The committed inventory; the new module; the rebinding block re-exporting every reached name and object; the purge entry.
- The `memory_cli.py` inversion and its two repointed test sites; the two other repointed patch sites.
- The wave-level receipt pair and the `PRODUCTION_RETRIEVAL_MODULES` derivation and test.
- The test additions in Requirement 7 and the two-process docstring correction and assertion.
- The architecture doc lines (Affected Architecture Docs) and a CHANGELOG Unreleased bullet.

**Out of scope:**

- Context-efficiency projection and persistence, including the three `_state_sources_memory_*` extractors bound in its registry.
- Moving the two close-gate compositions, the three crediting extractors, the four staying helpers, or `WaveIndex`.
- Inverting `memory_eval.py` (Requirement 4).
- Any behavior change to a memory tool, record shape, fence or lock; any change to `memory_records.py`, `memory_backfill.py` or `memory_supply.py`.
- Replacing `_load_script` indirections with plain imports across the memory siblings (a separate change that must add purge entries and repoint patch seams together).
- A `TOOLS` list or second registration source.

## Acceptance Criteria

- [x] AC-1: Every definition and module-level object the committed inventory classifies as moved lives in `memory_handlers.py` and not in `server_impl.py`; the five staying memory-named definitions remain; the module has no module-top `server_impl` or handler import; the AST tests prove all three.
- [x] AC-2: The ten registered memory tools are byte-identical to the golden fixture; the existing memory test modules drive every response without the transport; every re-exported name passes its identity assertion.
- [x] AC-3: The module is in the purge list and imported at module top; both reload tests and the parameterized reload proof pass; the packaging manifest test lists it.
- [x] AC-4: `memory_cli.py` no longer imports `server_impl` lexically; the four repointed patch sites are listed and the seven existing test modules pass with no other edit; the two-process class carries its non-vacuity assertion and corrected docstring.
- [x] AC-5: The before-and-after receipt pair (or its recorded deviation) exists; `memory_handlers.py` is absent from `PRODUCTION_RETRIEVAL_MODULES` with the derivation pinned by a test; golden-corpus anchors resolve.
- [x] AC-6: The change's own suites and every test it adds pass, and no failure elsewhere is attributable to this change.

## Tasks

- [x] Commit the inventory: thirty-four definitions (twenty-nine moves and five stayers) and fourteen objects with callers, classification, test patch sites, source-text anchors, the measured-tool closure and the golden-anchor scan. Review it before moving anything.
- [x] Create `memory_handlers.py`, move the classified set, add the rebinding block with every reached re-export and the purge entry; run the golden fixture and the seven existing test modules.
- [x] Invert `memory_cli.py`; repoint the four named patch sites; correct the two-process docstring and add its assertion.
- [x] Add the `FAMILIES` entry, the staying-names assertion, the identity assertions, the parameterized reload proof and the not-joined test.
- [x] Record the after-receipt and the comparison or deviation.
- [x] Update the architecture doc lines, add the CHANGELOG bullet, run the framework suite last; required delivery review.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| inventory | implementer | techdocs-move (sibling change, reviewed) | Committed and reviewed before the move starts. |
| memory-move | implementer | inventory | One owner for `server_impl.py`, the new module and `memory_cli.py`. |
| independent-review | required reviewers | memory-move | Fresh contexts; golden fixture, reload proof, identity assertions and the lifecycle seam are the evidence. |

## Serialization Points

- `.wavefoundry/framework/scripts/memory_handlers.py`
- `.wavefoundry/framework/scripts/server_impl.py`
- `.wavefoundry/framework/scripts/memory_cli.py`
- `.wavefoundry/framework/scripts/retrieval_eval.py`
- `.wavefoundry/framework/scripts/tests/test_handler_modules.py`
- `.wavefoundry/framework/scripts/tests/test_memory_records.py`
- `.wavefoundry/framework/scripts/tests/test_memory_backfill.py`
- `docs/architecture/current-state.md`
- `docs/architecture/domain-map.md`
- `docs/architecture/layering-rules.md`
- `docs/reports/`
- `.wavefoundry/framework/scripts/tests/test_docs_lint.py`
- `docs/contributing/review-and-evals.md`
- `docs/architecture/testing-architecture.md`

## Affected Architecture Docs

`docs/architecture/current-state.md` and `docs/architecture/domain-map.md` (Handler ownership) gain `memory_handlers.py`, and their "both siblings" wording about purge-and-reimport becomes "every handler sibling" with the current-state heading reading "(waves 1y0h2, 1ymzk)"; `docs/architecture/layering-rules.md` gains the handler-module boundary row described in `1ymzi`; `docs/architecture/testing-architecture.md` has its standing-baseline row corrected (Requirement 5). `docs/references/project-context-memory.md` names `server_impl.py` only as a `PRODUCTION_RETRIEVAL_MODULES` member, which remains true, so it needs no edit.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | The move is the change, and the stay list is what keeps lifecycle and crediting callers intact. |
| AC-2 | required | Public surface, behavior and every reached name must survive. |
| AC-3 | required | A missed purge entry serves stale code after reload. |
| AC-4 | required | The inversion is the kickoff's stated goal and the existing coverage must survive honestly. |
| AC-5 | required | The evaluator obligation is documented and the production identity must be derived, not guessed. |
| AC-6 | required | Change-local correctness. |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-09-21 | Repair cycle 1: typed repair_start recorded for CODE-DEL-1 and QA-DEL-1 before test-only edits. Migrated exact record-layout message exemption; expanded lock-order source owners and exact qualified-call recognition while retaining >=8 coverage and proving nested violation detection. Six focused tests passed in 0.712s; product unchanged, repaired test hashes frozen. Gapfill: exact compiler-AST census and mechanical test-path migration used native source reads because the checks depend on complete source syntax rather than semantic ranking. | memory-delivery-evidence.md cycle-1 section; memory-inventory.md delivery-discovered consumers; /private/tmp/1ymzk-repair-before.log and /private/tmp/1ymzk-repair-after.log. |
| 2026-09-21 | Observe: all seven named memory modules passed in isolated canonical-interpreter runs (901 tests, one skip); lifecycle golden/phase suites passed 25, shared handler/registry/golden/reload suites passed 61. Source remains frozen at recorded SHA-256 values. AC-1 through AC-4 complete; after evaluation, complete framework receipt and independent delivery remain pending. | [Memory delivery evidence](memory-delivery-evidence.md), per-module counts/timings and retained exploratory-failure disclosure. |
| 2026-09-21 | Observe: 217 memory-record and 46 backfill tests passed in isolated canonical-interpreter runs; 61 handler/registry/golden/reload tests passed. All 29 moved function bodies normalize AST-identically; registration bytes unchanged. Mixed-process exploratory run had three failures and is disclosed, not counted as green. Source frozen for review; remaining modules and final wave receipt pending. | [Memory delivery evidence](memory-delivery-evidence.md), including exact source hashes and reproducible equivalence recipe. |
| 2026-09-21 | Implement: independently approved inventory published before source edits; all 29 domain functions and 14 objects moved, five lifecycle/crediting compositions retained. Added direct CLI owner, four explicit patch migrations, cache non-vacuity and corrected same-interpreter premise; identity, staying, reload and bounded closure tests added. The inventory deliverable is recorded in the tree; Git commit remains operator-owned. | memory-inventory.md; implementation and focused verification in progress. |
| 2026-09-21 | Readback: After TechDocs review, record and independently review the memory move/stay inventory, then relocate only domain-owned definitions/state, invert memory_cli, preserve lifecycle/crediting stayers and memory_eval handle; verify identity, patch targets, real reload and response tests (AC-1 through AC-6). Thought: no memory source edits before inventory review. Inventory will be recorded durably in this wave; a Git commit remains operator-owned and is not authorized by this implementation request. Gapfill: indexed structural navigation currently refuses stale runtime; native AST and targeted caller/patch census are the fallback. | Current plans; scoped source inventory; before-run invalid receipt. |
| 2026-09-21 | Planned as the second change of the second handler-split wave after a census of `server_impl.py`: 31 memory definitions, 2,124 lines, 3 with lifecycle callers, 7 shared helpers stay, 5 cross-module reaches through `server_impl`, 2 back-referencing siblings, 5 test modules referencing memory names, no golden anchor. | AST census; `retrieval_eval.TOOLS`; `docs/evals/retrieval-quality-golden.json`. |
| 2026-09-21 | Readiness round (red-team and architecture seats, code and QA lanes, all fresh). Build-changing corrections folded in: the move criterion is domain ownership and the first draft's caller-location rule contradicted its own re-exports; fourteen module-level objects were unclassified and are reached from `WaveIndex`, a closure, a staying definition and about twenty test sites; the patch-transparency claim was false for moved-to-moved calls and four sites are now named; six definitions have outside callers, not three, because three state-source extractors sit in the context-efficiency registry; the two-process coherence class loses its premise for moved code; the wave owes a before-and-after retrieval receipt pair regardless of module membership. Also folded: `WaveIndex`, `_diagnostic`, `project_state_publication_lock`, `read_review_event_ledger` as reached names; `_draft_view` moves; `_load_script` indirection retained with reasons; `memory_eval` not inverted; existing tests are the transport-free coverage; the module does not join the evaluator list (three closures agree); `domain-map.md` and a `layering-rules.md` row. | Readiness review in this wave directory; context `handler-split-two-readiness-20260921`. |
| 2026-09-21 | Focused verification from wave `1ymzq`: the standing-baseline repoint would break the literal pin in `test_docs_lint.py` (`EvaluatorEditBaselinePolicyPinTests`); the pin is now a named edit and a serialization point. | 1ymzq readiness review, index lane. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-09-21 | Follow the `1y0h2` recipe with a rebinding block that re-exports every reached name and object. | Keeps every external reference valid without editing sibling modules or the upgrade runner in the same change; the upgrade runner's reach is pinned by a source-text test. | Repoint the cross-module reaches to `memory_handlers` now; fails the source-text pin and adds edits for no behavior gain. |
| 2026-09-21 | Move criterion is domain ownership; two close-gate compositions and three crediting extractors stay. | The lifecycle callers live in `server_impl.py`, which already imports the module at module top, so moving memory services changes no edge direction; the stayers are lifecycle and crediting logic, not memory services. | Caller-location rule (first draft); contradicted its own re-exports and misclassified `_draft_view` and `_memory_advisories_for_wave`. |
| 2026-09-21 | Keep `_memory_mod` through `server_impl._load_script`. | Reload re-executes namespaced siblings; tests patch the seam and its returned objects; a plain import would split module identity and evade the purge census. | Plain `import memory_records` now; a separate change that adds purge entries and repoints patch seams for all memory siblings together. |
| 2026-09-21 | Invert `memory_cli.py` only; leave `memory_eval.py` on its single `server_impl` handle. | Two of its five attributes do not move and one is test-patched on `server_impl`; splitting the handle threads two parameters through four helpers for no behavior gain. | Split the handle now; more edits and a false "inverted" claim. |
| 2026-09-21 | Context-efficiency projection is a separate change. | Interleaved with the `1y0h1` middleware chain and the `1yj14` index interlock; boundary verified clean at readiness. | Move it here as the kickoff sketched; doubles the blast radius of one review. |
| 2026-09-21 | Wave-level before-and-after receipt pair, not a conditional rerun. | `server_impl.py` is a production retrieval module and both changes edit it; the obligation is documented and does not depend on the new module's membership. | Rerun only if the module joins (first draft); refuted by the documented obligation. |

## Risks

| Risk | Mitigation |
| --- | --- |
| A helper or object is classified as move but has a caller the AST census missed (dynamic attribute access, string-built patch targets). | The inventory greps for `"_memory` and `"memory_` string literals across scripts and tests as well as AST names; the identity assertions and the name-resolution test catch a miss. |
| A test reads `server_impl.py` source text to find a memory definition. | Inventory item; `1y0h2` found two such sites for its families and repointed them with a per-anchor source map; the upgrade runner's pin is on `upgrade_wavefoundry.py`, not the monolith, and stays valid. |
| The two-process coherence tests pass vacuously after the move. | Requirement 8: explicit distinct-cache assertion and corrected docstring; fallback is retiring the class for the real child-process tests. |
| The upgrade runner's reach into `_memory_backfill_batch_locked` breaks on the installing upgrade's old-code window. | The name stays resolvable through `server_impl`; the upgrade runner playbook is followed and its seam test cluster is run. |
| The before-receipt cannot compare against the standing report because the evaluator identity moved. | Requirement 5 records the deviation explicitly, as `1y0h2` did, and the after-receipt becomes the new baseline. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.

| 2026-09-21 | Repaired whole suite passes 9,481 tests across 119 files, 12 skips, in 283.551 seconds with host process/localhost access. Framework receipt result ok, inputs_hash 58bd9cc3ca90dfa056e3d7c7bd5ecbe01661aa25db1133e37a567e9eb1e020fb. Both cycle-1 findings terminal after independent code/QA verification. | delivery-review.md; /private/tmp/1ymzk-full-suite-repair1.log. |

| 2026-09-21 | Observe: signed after receipt passes against standing 1y0bf-final, stable generation1869, no invalidation, violations or operator-review reasons. Supplementary fresh before/after computed comparison passes0violations; labeled computed rather than a gate receipt. Required pair, closure test and unchanged corpus anchors now proven. | docs/reports/retrieval-quality-1ymzk-after.json; docs/reports/retrieval-quality-1ymzk-before-after-computed.json; final-code-qa-review.md. |

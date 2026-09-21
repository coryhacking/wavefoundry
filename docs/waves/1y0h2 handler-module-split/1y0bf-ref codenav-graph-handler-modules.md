# Move Code Navigation And Graph Handlers Into Domain Modules

Change ID: `1y0bf-ref codenav-graph-handler-modules`
Change Status: `complete`
Owner: Engineering
Status: completed
Completed at: 2026-09-20
Last verified: 2026-09-20
Wave: `1y0h2 handler-module-split`

## Rationale

**Brief.** Goal: begin shrinking `server_impl.py` by moving the two largest self-contained handler families, code navigation and graph query, into sibling response modules, while registration stays in the composition root that the introspection registry from `1y0be-ref tool-registry-and-wrapper-chain` reads, so the registry reports `server_impl` as the source module of all nineteen tools. Audience: framework maintainers and downstream integrators who merge around the server file. Approach: move the `*_response` functions and their private helpers; keep decorated registration closures in the composition root, byte-identical, and rebind the moved names into `server_impl` so every existing caller keeps resolving them there. Constraints: public surface identical; reload safe; no change to retrieval behavior. Success: neither family's response functions are defined in `server_impl.py`, both modules are unit-tested without the transport, and the golden fixture is unchanged.

Verification found these families already delegate through loaders: `_get_chunker_module()` and `_load_graph_query()`, a wrapper over `_load_script("graph_query")`, both in `server_impl.py`. That makes the seam thin. The reload investigation also settled the design question the earlier evaluation raised: `wf_reload_mcp` clears `_script_cache` and purges a named list of sibling modules, so relocated handlers stay fresh after an upgrade as long as their modules are on that list. Techdocs is not used as the exemplar here because its dependency claims in the RFC were found to be inaccurate; it can follow once the pattern is proven.

Re-verified 2026-09-17 against four intervening commits: none touched code-navigation or graph-query tool bodies, the implementation registration and runner survivors together match the roster, and the purge-list mechanism this change relies on is unchanged (see the parallel finding in `1y0be` about two new modules that were *not* added to it — a reminder to add `codenav_handlers`/`graph_handlers` to that list explicitly rather than assume it happens by default).

Re-verified 2026-09-19 at `f4063a85`, after waves `1y0h0 typed-phase-gates` and `1yd97 phase-gate-follow-ups` landed. The nineteen tools, their closures and response functions, and both loader seams are unchanged. The check found one defect in this plan and several constraints the plan now states. The defect: the standing retrieval evaluator, `retrieval_eval.py`, calls `code_outline_response`, `code_constants_response` and `code_lexical_response` as attributes of the loaded `server_impl` module, and fingerprints its production identity from a fixed module list, `PRODUCTION_RETRIEVAL_MODULES`, that names `server_impl.py` but would not name the module the moved code lives in. Moving the functions as first written would have broken the evaluator on a measured path, and every hermetic test and acceptance criterion would have stayed green, because every evaluator test uses a stub server. Rebinding the moved names into `server_impl` keeps the evaluator's calls working and keeps every existing caller and test patch meaningful, including `WaveIndex.search_combined` and `_code_ask_response_body`, which call `code_keyword_response`. The constraints: `1y0h0`'s `test_reload_picks_up_every_added_module` requires both modules to be imported by public name at module top rather than loaded lazily, and `1y0be`'s handler-digest test stays green only if the nineteen closures are not edited. Red-team also found that the code-navigation walker, `_walk_repo_for_navigation`, catches every exception and falls back to a scan that honours no ignore rules, so a missing name after the move would silently expose `.gitignore`d and `.aiignore`d files while every existing navigation test stayed green. Root containment through `_resolve_repo_path` fails visibly and cannot vanish silently.

## Requirements

1. Two new modules, `.wavefoundry/framework/scripts/codenav_handlers.py` and `.wavefoundry/framework/scripts/graph_handlers.py`, receive the `*_response` functions and the private helpers used only by them for these tools: code navigation covers `code_list_files`, `code_read`, `code_keyword`, `code_lexical`, `code_constants`, `code_pattern`, `code_outline`, `code_definition`, `code_references`, `code_dependencies`, `code_hover`, and `code_commit_provenance`; graph covers `code_impact`, `code_callgraph`, `code_callhierarchy`, `code_graph_path`, `code_graph_community`, `code_risk_score`, and `wf_graph_report`.
2. Keep the existing decorated closures in `register_mcp_surface` byte-identical. `server_impl.py` rebinds the moved response functions with one `from codenav_handlers import (...)` block and one `from graph_handlers import (...)` block at module top, the pattern `1y0h0` used for the lifecycle gates, so each closure, every internal caller such as `WaveIndex.search_combined` and `_code_ask_response_body`, every test that patches `server_impl.<name>`, and the retrieval evaluator keep resolving the name through `server_impl`. Reload re-executes those imports after the purge block has evicted both modules, so nothing is captured across reload. The `1y0be` registry continues to introspect FastMCP after registration; modules declare no `TOOLS` list and introduce no second registration source. Names, tiers, parameters, docstrings, annotations and extra-argument validation remain unchanged.
3. Helpers used by any function outside the moved set stay where they are defined today, in `server_impl.py` or in `lifecycle_gate_support.py`, from which `server_impl` imports some of them. A helper used by both new modules, such as `_resolve_repo_path` and `_walk_repo_for_navigation`, also stays in `server_impl.py`, so neither new module imports the other. Only a helper whose callers all sit inside one family moves, and it moves with that family; this is what Requirement 1's "used only by them" means. The new modules reach every helper that stays behind as `server_impl.<name>` through a function-level `import server_impl` resolved per call, the precedent in `project_context_efficiency.py` and `upgrade_extensions.py`, so neither module imports `server_impl` at module top level. A test asserts the absence of a module-top import, and an AST test asserts that every global name referenced in either module resolves to a definition in that module, an import in that module, or an attribute of `server_impl` that exists.
4. Both modules are appended at the end of the purge list at the top of `server_impl.py` and imported by public name at module top, so `1y0h0`'s `test_reload_picks_up_every_added_module` covers their reload freshness. The reload proof for a modified handler module edits a scratch copy of the scripts tree or uses a `sys.modules` stub, never the live file, which parallel test workers read. Preserve the independent direct-import census and native reload identity/callable checks added by wave `1yj14`. Update the registry test's obsolete last-entry assertion to require registry membership and module-top import, since the new modules now follow it; removing any required purge entry must still fail a named test.
5. Unit tests exercise each module's response functions against a fixture repository root with no MCP transport. The code-navigation tests include a fixture containing a `.gitignore`d file and an `.aiignore`d file, and assert that relocated `code_list_files` and `code_keyword` exclude both.
6. An AST test asserts that none of the nineteen response functions is defined in `server_impl.py` after the move, and the registry-based parity test from `1y0be` still covers their registered tools. Retain the existing AST roster census: decorated closures remain in the composition root, so moving response functions does not invalidate it.
7. The golden tool-surface fixture is unchanged, and the retrieval test corpus passes, meaning `tests/test_server_tools_retrieval.py`, `tests/test_retrieval_eval.py`, `tests/test_retrieval_candidate_generation.py`, `tests/test_sqlite_serving.py` and `tests/test_graph_snapshot_readers.py`, with no edit beyond import paths, patch targets and source-file paths. A test that reads source text is repointed at the module that now defines the function. Two such sites are known: `tests/test_server_tools_retrieval.py` locates `def code_lexical_response` in `server_impl.py` text and anchors two further strings whose definitions stay, so it needs a per-anchor source map rather than one path; `tests/test_fts_query_honesty.py` asserts a substring of `inspect.getsource(code_lexical_response)`, which should survive the move unchanged. Implementation derives the full set rather than working from these two. Any new test that patches a helper through `server_impl` asserts the patch was called or carries an `inert-by-design:` justification, as this change requires. The existing `1y0h0` patch census only checks lifecycle-module names; it does not enforce this rule for the new handler test's `index_build_response` patch, whose deliberately unavailable builder is documented inline.
8. `build_pack.py` includes the new modules without a manifest edit, confirmed by a packaging test that lists them in the generated manifest.
9. The standing retrieval evaluator keeps working and keeps covering the moved code. `codenav_handlers.py` is added to `PRODUCTION_RETRIEVAL_MODULES` in `retrieval_eval.py`; `graph_handlers.py` is not. The rule that decides membership is whether a measured tool in `retrieval_eval.TOOLS` reaches a function the module holds, or the evaluator reads one directly. Both clauses matter: `code_lexical` runs `code_lexical_response` and `code_ask` reaches `code_keyword_response`, while `_resolve_declaration` calls `code_outline_response` and `code_constants_response` for anchor resolution outside any measured tool. All four move to `codenav_handlers.py`. No graph response function is reachable from the four measured tools, and a private helper moves only when the moved set is its only caller, so a measured path cannot reach `graph_handlers.py` except through one of those response functions; the inventory re-derives this rather than assuming it. `_production_identity` refuses a listed module that does not exist, so the fingerprint entry is added only once the file exists.
10. The golden corpus, `docs/evals/retrieval-quality-golden.json`, anchors relevance entries to a `path`. Every entry whose resolution depends on the file its `path` names is repointed when this change moves that definition, in the same change as the move. The rule covers `content` anchors as well as `symbol` anchors, because a moved function carrying a distinctive string would otherwise escape it; today no content anchor qualifies, since both sit in functions that stay. The derivation governs, not a fixed list; on the tree this change is planned against exactly one entry qualifies, the `code_lexical_response` anchor of fixture `agentic-calibration-lexical-backfill`. The repoint follows module creation, because `load_fixture_corpus` refuses a relevance path that does not yet exist.
11. No before-and-after standing evaluation is run across this change, and the comparison chain restarts here. Three independent facts each make a comparison unavailable, and the first already holds at `f4063a85`, before this change touches anything: every recorded report in `docs/reports/` carries fixture digest `bda67546` while the current evaluator normalizes the byte-unchanged corpus to `cc98eb0a`, and those reports record fixture schema v1 against the current v2, which `_validate_baseline_compatibility` refuses one check earlier than the digest. The second and third are this change's own corpus edit and its production-identity change. `docs/contributing/review-and-evals.md` and `docs/references/project-context-memory.md` ask for a before-and-after receipt pair on any edit to a `PRODUCTION_RETRIEVAL_MODULES` member; a standalone pre-move run is still possible, since only the comparison is refused, but it could never serve as a baseline for anything after the move, so this change deviates deliberately rather than recording a receipt that no later run can use. Neither document is machine-enforced. The standing evaluation runs once after the move and that report becomes the new baseline; the Progress Log records the deviation and the restart point.

## Scope

**Problem statement:** Every handler lives in one file of more than 34,000 lines, so unrelated work collides in review and every integrator merges around the same file.

**In scope:**

- The two response modules, purge-list entries, and tests.
- Rebinding the moved names into `server_impl` so existing closures, callers and patches keep resolving them there.
- The retrieval evaluator's production fingerprint, the golden-corpus anchors this move invalidates, and the new baseline report.
- Preserving both AST roster and runtime registry parity coverage.

**Out of scope:**

- Search handlers (`docs_search`, `code_search`, `code_ask`), lifecycle handlers, memory, context-efficiency, and techdocs; each follows in its own change once this pattern holds.
- Any change to ranking, chunking, graph building, or response shapes.
- A `server/` package layout.

## Acceptance Criteria

- [x] AC-1: The golden tool-surface fixture is unchanged and the retrieval test files Requirement 7 names pass with no edit beyond import paths, patch targets and source-file paths.
- [x] AC-2: The AST test finds none of the nineteen response functions defined in `server_impl.py`, both modules pass the no-top-level-`server_impl`-import test, and the name-resolution test passes on both modules and fails on a mutated copy that references a name no scope defines.
- [x] AC-3: Unit tests for both modules run without booting the transport and cover every relocated response function with at least one call, and the ignore-rule fixture proves relocated `code_list_files` and `code_keyword` exclude both the `.gitignore`d and the `.aiignore`d file.
- [x] AC-4: After reload a modified `graph_handlers.py` is served, proven in a scratch tree or with a `sys.modules` stub, and `1y0h0`'s `test_reload_picks_up_every_added_module` passes with both modules on the purge list.
- [x] AC-5: The registry parity test covers the relocated tools, the AST roster census remains green, and both initial registration and reload preserve the full public surface.
- [x] AC-6: The packaging test lists both modules in the generated manifest.
- [x] AC-7: The change's own suites and every test it adds pass; the documents this change authors or edits validate; and no failure elsewhere is attributable to this change.
- [x] AC-8: A hermetic test proves every attribute `retrieval_eval` reads from the loaded server module exists on the real post-move `server_impl`, and fails when one of `code_outline_response`, `code_constants_response` or `code_lexical_response` is removed from it. A second hermetic test proves an edit confined to `codenav_handlers.py` changes `_production_identity(...)["digest"]`.
- [x] AC-9: A hermetic test proves every anchor in the golden corpus resolves in the file its `path` names, symbol and content alike, and fails on a corpus copy whose anchor points at a file that no longer carries it. The standing evaluation runs once after the move, completes with a report, and is recorded as the new baseline.
- [x] AC-10: The index the post-move evaluation runs against contains the two new modules, verified before the run rather than assumed, so the recorded baseline reflects the moved code and not its absence.

## Tasks

- [x] Create both modules, append them to the purge list with public-name imports, and add `codenav_handlers.py` to `retrieval_eval.PRODUCTION_RETRIEVAL_MODULES` once the file exists.
- [x] Inventory the private helpers each family uses and classify them as move or stay, and every caller of each moved function, including internal callers, test patch sites and dynamic patches such as `patch.object(server, tool + "_response")`. Commit the inventory as a short table (name, used by, callers, classification) for review before the move starts, so a missed helper or caller is caught at review rather than mid-move. The inventory re-derives the two sets Requirements 9 and 10 depend on: which moved definitions a measured tool reaches, and which golden-corpus anchors name a definition that moves.
- [x] Move the graph response family first and add its rebinding import block; run the golden test and the retrieval test files.
- [x] Move the code-navigation family and add its rebinding import block; run the golden test and the retrieval test files.
- [x] Repoint every golden-corpus anchor the inventory identified, in the same change as the move.
- [x] Add the no-top-level-import test, the name-resolution test, the AST absence test, the ignore-rule fixture tests, the reload proof, the two evaluator tests, and the corpus anchor-resolution test.
- [x] Rebuild the index so it contains both new modules, verify that it does, then run the standing evaluation once and record its report as the new baseline.
- [x] Run the existing AST census and registry parity test against both original and reloaded registration.
- [x] Add the packaging manifest test.
- [x] Run `python3 .wavefoundry/framework/scripts/run_tests.py` last and record the receipt.

## Agent Execution Graph


| Workstream     | Owner       | Depends On   | Notes |
| -------------- | ----------- | ------------ | ----- |
| inventory      | implementer | `1y0h1` registry | helper classification |
| graph          | implementer | inventory    | smaller family first |
| codenav        | implementer | graph        | |
| compose-guards | qa          | codenav      | delegation, tests, census preservation, packaging |


## Serialization Points

- `.wavefoundry/framework/scripts/codenav_handlers.py`
- `.wavefoundry/framework/scripts/graph_handlers.py`
- `.wavefoundry/framework/scripts/server_impl.py`
- `.wavefoundry/framework/scripts/retrieval_eval.py`
- `.wavefoundry/framework/scripts/tests/`
- `docs/evals/retrieval-quality-golden.json`, `docs/reports/`

## Affected Architecture Docs

`docs/architecture/current-state.md` and `docs/architecture/domain-map.md` list the two handler modules and state the rule that a handler family is a reloadable sibling response module with registration retained in the composition root. `docs/architecture/search-architecture.md` updates file references for the graph query entry points. The decision record from `1y0be` gains the exemplar outcome.

## AC Priority


| AC   | Priority  | Rationale |
| ---- | --------- | --------- |
| AC-1 | required  | Unchanged public surface and behavior |
| AC-2 | required  | The move is the deliverable |
| AC-3 | required  | Testability without transport is the maintainer benefit |
| AC-4 | required  | Stale handlers after upgrade would be a silent regression |
| AC-5 | important | Preserves both registration and runtime parity coverage |
| AC-6 | required  | Downstream repositories must receive the modules |
| AC-7 | required  | Standard change-local verification |
| AC-8 | required  | The standing retrieval evaluator must keep working and keep covering the code its measured paths run |
| AC-9 | required  | A corpus anchor left pointing at a file that no longer carries it aborts the whole evaluation at `unresolved_symbol_anchor`, so the standing gate stops producing any result at all |
| AC-10 | required | The post-move run becomes the standing baseline, so an index predating the new modules would bake a depressed reference into every later comparison |


## Progress Log

2026-09-20 Observe: all operator-requested pre-close improvements implemented and independently reviewed. Root escape mutant is killed against an existing sibling file; direct imports remove incidental composition-root coupling. Full suite green (9,418 tests,12 skips); final protected retrieval run produced a valid baseline at stable generation1772 with source hashes and exit production digest verified. Earlier invalid evaluation attempts are retained as failed attempts, not claimed as evidence. Full details and reproducible review fingerprints: delivery-evidence.md and verification-summary.json.

2026-09-20 Thought / Readback: operator authorized bounded pre-close improvements: use the handler modules’ existing direct Any/Optional/Path imports instead of composition-root aliases, strengthen the root-boundary fixture with an existing outside-root file and a caught bypass mutant, correct the patch-census claim, and preserve reproducible digest manifests/recipes. Shared behavioral helpers remain invocation-time server lookups. Refresh code/QA/architecture approvals, full-suite receipt and indexed retrieval baseline before operator-authorized closure. Gapfill: exact mechanical replacement and evidence-manifest reproduction use filesystem tools after MCP source reads.


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-09-20 | Observe: implementation complete; 9,418 tests passed across 114 files (12 skips), full docs validation clean. Pre-run index hashes match both handlers; the single standing evaluation returned baseline at unchanged completed generation 1762 with exit production digest verified and no invalidation or operator-review reasons. Reflect: whole-file source censuses must follow all relocated owners; cycle 3 retained exact expected sets and independent mutation controls killed constructor and advisory regressions. No further source edits; comparison chain restarts at the recorded report | delivery-evidence.md; verification-summary.json; docs/reports/retrieval-quality-1y0bf-post-move.json |
| 2026-09-20 | Full suite ran 9,418 tests with two stale source-census failures: graph constructor locations and advisory diagnostic ownership. Independent review confirmed production unchanged. Typed delivery repair cycle 3 extends both censuses to server plus both handlers, retaining expected constructor and diagnostic sets. Adjacent repair search covers both positive constructor census and negative fresh-parse/advisory guards. Targeted checks pass; independent mutation reverification follows. Index initial attempt rejected concurrent test edit and verified historical rollback; stable retry completed generation 1760 with matching handler source hashes | handler-graph-accessor-source-gate; /tmp/handler-source-gates-repair.log; /tmp/handler-index-presence.json |
| 2026-09-20 | Observe: both families extracted; all 77 definition ASTs match aadab429 after shared-lookup/import normalization. Combined 1,337 regressions had one additional source-location assertion, repaired without changing its expected count; subsequent 37 focused tests pass (registry, new handler guards and repaired assertion). Nine new guards include killed ignore-bypass, captured-walker, omitted-fingerprint, missing-name/alias and stale-anchor controls. Golden fixture and decorated closures unchanged. Thought: freeze source for independent code/QA/architecture delivery review and final full suite; fresh index update underway before the one post-move evaluation | /tmp/handler-combined-tests.log; /tmp/handler-final-focused.log; /tmp/handler-delivery-freeze.json; test_handler_modules.py |
| 2026-09-20 | Observe: graph extraction preserves all 25 moved definition ASTs after allowed shared-lookup/import normalization. 1,312 graph-stage regression tests ran; sole failure was the inventoried whole-server source read for hierarchy edge trust. Repointed it to the relocated response, retaining both-branch count. Thought: proceed to codenav extraction using the same scope-aware transform | /tmp/handler-graph-move-tests2.log; TestCallHierarchyEdgeTrustFields; handler-inventory.md |
| 2026-09-20 | Observe/Readback: reviewed independent inventory: 12 codenav + 7 graph responses, 40 and 18 exclusive private definitions; shared helpers remain late-bound through server_impl. No public behavior change: code_outline retains its existing tool closure and delegates to the rebound response. Graph move first, then codenav, guards/evaluator/corpus, fresh indexed baseline, full suite. Required ACs cover surface, module ownership, ignore/root controls, reload, packaging and evaluator continuity | handler-inventory.md; independent readiness primer/security checks; current typed approval |
| 2026-09-20 | Gapfill: semantic Q&A returned stale/incomplete enumeration; live MCP reads and exact keyword/reference evidence plus source AST census governed the inventory. No index rebuild used to conceal missing exploration evidence | handler-inventory.md |
| 2026-09-20 | Thought: prerequisite registry baseline committed as aadab429 after 27 native registry tests; current readiness authority has no pending action. Re-derive the helper/caller inventory before moving either family, checking the recent source-guard/reload and storage-evaluator changes against the settled design | wf_review_wave prepare; independent implementer/Guru inventory; registry-baseline-check.log |
| 2026-09-14 | Change planned and admitted to `1y0h2 handler-module-split` | this document |
| 2026-09-19 | Readiness drift check at `f4063a85` after `1y0h0` and `1yd97` landed, run as one scoped round under the rule that readiness takes at most one round once the design is settled. Code-reviewer and qa-reviewer each blocked independently on the retrieval evaluator, recorded as typed readiness finding `READY-B1`; red-team approved and found the silent ignore-rule exposure. Repaired in one pass: the moved names are rebound into `server_impl`, the evaluator's fingerprint gains the new module in a fixed order with before and after receipts (Requirement 9, AC-8), and the ignore-rule fixture and name-resolution test are added. Line anchors are replaced with symbols | lane reports 2026-09-19; `events.jsonl` finding `READY-B1` |
| 2026-09-19 | Scoped reverification of the `READY-R1` repair: qa-reviewer and code-reviewer both approved with no blocking finding, each replaying the guard and independently re-deriving the one-anchor corpus census and the graph unreachability closure. Their non-blocking notes are applied here in one pass. Three sentences the repair introduced were false and are corrected: `_compare` is not a symbol (the guard is in `_validate_baseline_compatibility`); the recorded baseline had already stopped being comparable at `f4063a85` on fixture schema v1 against v2 and on a normalization-moved digest, so the two reasons the plan named were not the operative ones; and a stale anchor aborts the run at `unresolved_symbol_anchor` rather than silently degrading it, which also means the rejected alternative does not exist. Requirement 9's membership rule now covers the evaluator's direct reads, Requirement 10 covers content anchors, Requirement 3 resolves the helper-movement ambiguity against Requirement 1, Requirement 7 names both known source-reading tests, the deviation from the before-and-after receipt policy is stated as Requirement 11, and AC-10 pins index freshness for the baseline run | lane reports 2026-09-19; guard replayed at `retrieval_eval.py:1991`; `docs/reports/*.json` fixture digest `bda67546` against current `cc98eb0a` |
| 2026-09-19 | Scoped readiness round on `READY-B1`'s repair found `READY-R1`, a defect that repair introduced: it required a before-and-after standing evaluation that no ordering can satisfy, because the same move must repoint a golden-corpus anchor and `_compare` refuses a baseline whose fixture digest differs from the current corpus. Repaired by deleting the comparison, stating the anchor-repointing rule as Requirement 10 with AC-9, and recording where the comparison chain restarts. The open `graph_handlers.py` fingerprint question is settled as no on an AST reachability closure from the four measured tools | `events.jsonl` finding `READY-R1`, repair cycle 2; reachability closure over `server_impl.py`; corpus census of `docs/evals/retrieval-quality-golden.json` |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-09-14 | Code navigation and graph first, techdocs and memory later | Largest self-contained families with existing loader seams; techdocs' dependency picture was misstated in the RFC and memory has a static import back-reference | Techdocs as exemplar per the RFC: smaller, but not representative |
| 2026-09-14 | Modules never import `server_impl` at top level | Prevents a cycle and keeps each module testable in isolation; matches the existing `techdocs_audit_lib.py` rule | Allow the import: simpler moves, permanent cycle |
| 2026-09-19 | Handler modules reach shared helpers through a function-level `import server_impl`; the any-scope import ban that `1y044-ref extract-lifecycle-gate-units` Requirement 3 set for `lifecycle_gates.py` is not extended to them | An AST reachability census by the code-reviewer lane found that 113 of the 210 definitions reachable from the nineteen response functions have callers outside them, so an any-scope ban would require moving them into a new support module first, a larger change than this exemplar; the silent-failure risk the ban guards against is covered here by the name-resolution test and the ignore-rule fixture | A navigation support module on the `lifecycle_gate_support.py` pattern, with the handler modules never importing `server_impl` at any scope: stricter layering, roughly doubles the move; raised by red-team for operator decision |
| 2026-09-19 | `graph_handlers.py` does not join `PRODUCTION_RETRIEVAL_MODULES` | An AST reachability closure from the four measured tools in `retrieval_eval.TOOLS` reaches none of the seven graph response functions, and a helper moves only when the moved set is its only caller, so no measured path can reach the module | Add it defensively: one more module in the fingerprint, but it would move production identity on every graph edit and force a new baseline for changes the evaluator does not measure |
| 2026-09-19 | No before-and-after standing evaluation across this change; the post-move run becomes the new baseline | `_validate_baseline_compatibility` already refuses every recorded report at `f4063a85`, on fixture schema v1 against the current v2 and on a digest the evaluator's own normalization has moved, so the chain was broken before this change; the corpus edit and the production-identity change each break it again | Keep the anchor pointing at `server_impl.py` to preserve the digest: this alternative does not exist, because the stale anchor aborts the run at `unresolved_symbol_anchor` and produces no report to compare |
| 2026-09-14 | Originally proposed retiring the AST census; superseded 2026-09-17 | The original proposal moved registration, but the accepted introspection design keeps decorated closures in the composition root | Current decision: preserve AST and runtime parity tests |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| A helper is used by both a moved family and a remaining one and gets duplicated | Inventory step classifies helpers first; duplicates are flagged for a follow-up dedupe |
| The inventory itself is wrong or incomplete, discovered mid-move | Archetype Council (Yoda, 2026-09-17): the inventory is now a committed, reviewed deliverable before Task 2 starts, not an internal step with no checkpoint |
| The two modules grow their own import-time cost | They stay on the lazy path the families already use |
| Downstream integrators with local patches to these handlers hit conflicts once | One-time cost, documented in the release notes for the version that ships this |
| Whether Waveforge's real fork has diverged inside these specific 19 tool bodies was not individually verified | `docs/reports/waveforge-fork-audit.md` (2026-09-17) confirms `register_mcp_surface` and its supporting infra are name-identical across both forks, which is what makes this split low-risk to attempt, but the individual code-navigation/graph tool names were not checked one by one against Waveforge's tree — an open detail to confirm before implementing, not a blocking one |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.

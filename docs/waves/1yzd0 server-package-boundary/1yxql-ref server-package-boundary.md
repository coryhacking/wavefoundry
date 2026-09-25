# Server Package Boundary

Change ID: `1yxql-ref server-package-boundary`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-09-24
Wave: 1yzd0 server-package-boundary

## Rationale

The server has grown through flat handler extractions, reaching the range where ADR 1ye5y requires reconsidering a package. Distribution extensions also introduce a sibling dependency. A dedicated server namespace now offers a clearer ownership boundary and avoids accumulating more globally named server implementation modules. The goal is maintainable server organization and a stable downstream integration boundary, not fewer files or a claim that moving paths alone eliminates merge conflicts.

Brief: create a behavior-preserving package for the server composition root, response handlers and tool registry; preserve executable entry points and downstream extension contracts. Consumers are Wavefoundry maintainers and distributions such as Waveforge. Deliver a tested package migration, legacy import compatibility, and documented ownership. Keep shared framework utilities and CLI scripts outside the package. Planning may proceed alongside other work; source migration waits for the overlapping work to settle.

## Requirements

Readiness evidence: `evidence/readiness-inventory.md` (baseline HEAD `902f7edc`), with its census scripts and the alias/reload demonstration under `evidence/demo/` (28 fresh-interpreter runs on CPython 3.11 and 3.13 in a path containing a space).

1. **Bounded package ownership (frozen inventory).** Create `.wavefoundry/framework/scripts/wf_server/` with an import-free `__init__.py`. Move exactly these 12 modules there under the same basenames: `server_impl`, `mcp_tool_registry`, `codenav_handlers`, `graph_handlers`, `techdocs_handlers`, `memory_handlers`, `index_handlers`, `upgrade_handlers`, `edit_gate_handlers`, `dashboard_handlers`, `docs_handlers`, `context_efficiency_handlers`. Every other module stays flat. That includes the borderline modules whose only importers are moved: `lifecycle_gates`, `sensor_runner`, `operator_identity`, `install_log_lib`, `tree_sitter_cache`, `commit_provenance`, `exploration_avoided`, `memory_supply`, `memory_eval` and `score_context_efficiency_pairs`. They are shared substrate, CLIs, or reached through the flat `_load_script`. `server.py` remains the flat executable entry point, and no `server/` import name is created. The `server_impl` legacy `__main__` guard moves unchanged; the flat alias does not run it, and no documented invocation uses it.
2. **Retained flat contracts.** `mcp_tool_extensions.py`, `mcp_tool_roster.py`, `record_paths.py`, CLI entry scripts and shared substrates stay at their current paths. The package initializer imports nothing, and permission rendering and upgrade declaration checks stay importable without MCP or model dependencies.
3. **Flat aliases: one module object per implementation (strategy (a)).** Each moved module keeps a flat file whose exact body is `import importlib`, `import sys`, and `sys.modules[__name__] = importlib.import_module("wf_server.<name>")`. A structure test pins those bytes, so a downstream merge that restores a full flat file fails. Package-internal code imports canonical package names.
   - **Why this strategy:** the demonstration showed it is the only one tried that keeps flat and package names on one module object through import, reload and old-runner reload. It preserves private names (the extension contract lets extensions use `server_impl` underscore helpers), `patch.object` on flat names, and runner attribute writes. Star-import stubs and a meta-path finder were rejected on executed evidence.
   - **The alias table:** it is a constant in `wf_server/server_impl.py`, which is reloaded. It is not in `__init__.py`, which is never evicted. It is defined above the purge block. It is the single source for the flat names and for both purge key sets.
   - **Eager registration:** `server_impl` registers the flat aliases after its last module-top import, and only when `__name__ == "wf_server.server_impl"`. That way a private-name load of the package file never rebinds the aliases, and a failed module-top import never leaves flat keys pointing at half-initialized modules. The extension module-name collision refusal and the reload census see the aliases.
   - **Lifetime:** aliases contain no logic. Removing them needs two things: an upgrade-protocol change that counts package modules, and a minimum supported upgrade-from version at or above it (Requirement 6).
4. **Scripts-root resolution.** A single `SCRIPTS_DIR` in `server_impl` resolves to the scripts root, not the package directory. Every lookup of a retained script goes through it. This covers the inventory's A3 sites that read retained files beside `__file__` or `server_impl.__file__`:
   - `_load_script`, `_read_chunker_version`, both `docs_lint.py` lookups, `_default_template`, `_indexer_module`, `_get_chunker_module`, `SERVER_IMPL_VERSION`;
   - index ×3, upgrade ×3, dashboard ×1, docs ×3.

   **Carve-out:** `_audit_harness_coherence` reads `server.py` from `SCRIPTS_DIR`, but reads the implementation source from the package file itself (`Path(__file__)`). Resolving `server_impl.py` from `SCRIPTS_DIR` would read the one-line alias and drop every tool it defines from `live_tools`.

   No code inserts the package directory on `sys.path`: the demonstration showed that creates duplicate handler instances. `_load_script` keeps loading retained flat scripts from the scripts root. Handlers keep their invocation-time access to the composition root; this is not a decoupling.
5. **Reload boundary.** The purge evicts both flat alias keys and `wf_server.<module>` keys for the moved handlers and registry. Both sets are derived from the alias table, and both exclude `server_impl` in both spellings. It never evicts `wf_server` or `wf_server.server_impl`: the demonstration showed that makes the reload raise `ImportError`. Existing shared-substrate invalidation is kept.
   - **Census rewrite:** the reload-coverage census is rewritten, not extended. Today `_direct_local_imports`, `_purge_run`, `_purge_entries`, `_patch_census` and `test_reload_picks_up_every_added_module` parse a literal flat purge set and assert flat paths, so they would silently stop covering handlers. The rewritten census derives coverage from the package files and imports, independently of the purge list.
   - **Preserved behavior:** handler shutdown, notifications, `runner_stale` reporting and the extension fail-closed contract.
   - **Restart rule:** editing `wf_server/__init__.py` needs a restart, because the parent package is never reloaded.
6. **Old-runner and upgrade compatibility.** Installed 1.25 and 1.26 runners validate the new pack with byte-identical `upgrade_protocol._pack_module_names`/`_validate_imports`. These accept only flat module imports, including function-local ones, in mandatory upgrade modules. Consequences:
   - The flat `server_impl.py` and `dashboard_handlers.py` aliases are mandatory.
   - `upgrade_wavefoundry`, `upgrade_extensions` and every other `MANDATORY_FEATURE_MODULES` member import only flat names, never `wf_server`. More generally, every consumer outside the package keeps flat names: the flat names are the permanent public import surface, and package names are internal.
   - `setup_readiness.SOURCE_FILES` adds only `wf_server/server_impl.py` and keeps the flat alias. This keeps today's scope, in which handler edits are served by `wf_reload_mcp` without a stale-code restart. Widening that scope would need its own decision.
   - `build_pack.collect_files` already includes subdirectories (executed) and is not changed.
   - **Pack verification:** the pack is built from a scratch copy of the tree (`build_pack` stamps VERSION and MANIFEST). Installed 1.25 and 1.26 runners are sourced by `git archive v1.25.0` / `v1.26.0` into scratch roots whose paths contain a space. Each reaches a working server, meaning `server.py --dry-run` plus a stdio `wf_server_info` call. These old-runner fixtures are recorded evidence on this machine, not portable committed tests, because tags and tests are not in consumer checkouts.
   - **Committed test:** the mandatory-import refusal is exercised against the real validation functions.
   - **Dashboard-running case:** it is included. The P1 upgrade process may then hold the installed `dashboard_handlers`/`server_impl`, and the matrix makes no package-identity claim for P1.
7. **Behavior preservation.** These keep their baseline behavior: tool names, input schemas, tiers, response envelopes, wrapper order, locking, publication guards, resources, prompts, `wf_audit` output, and every 1yv9l extension guarantee. Provenance changes are enumerated separately: `__module__` and `source_module` become `wf_server.*`, and source paths move. Goldens are not regenerated to bless unrelated drift.
8. **Evaluator sequencing (E0, E1, M, E2).** The retrieval evaluator cannot run after the move unedited: production identity comes from `Path(server.__file__).parent`, and 14 golden relevance rows in 10 fixtures target moved files.
   - **E0:** make `retrieval_eval` production identity, `_git_binding` paths and golden relevance resolution layout-independent through an explicit moved-path table. Logical keys and the fixture file stay byte-identical. After the move, a logical key matches only the implementing file; results on flat alias paths never count as matches. E0 changes the evaluator identity once, deliberately. Tests that fake `server.__file__` or copy flat files for identity are adapted.
   - **E0 lands as its own committed step:** an independent focused review of the E0 diff comes first, then the coordinator asks the operator to commit it. That gives E1 a reproducible pre-move tree.
   - **E1:** a receipt with the E0 evaluator on that commit, at a stable complete generation. Refresh the index with an ordinary update first. Run the evaluator as a CLI with the tool venv, not through a stale MCP process. "Approved" means verdict `baseline` with no invalidation or operator-review reasons.
   - **E1 recovery:** if a later repair changes `retrieval_eval.py`, E1 is re-recorded on the E0 commit in a scratch checkout with its own index.
   - **M:** the move, then an ordinary incremental index update.
   - **E2:** the after receipt with the same evaluator and fixture digest.
   - **Fail disposition:** a `cross_generation` fail at E2 goes to operator review, with per-fixture attribution to moved paths versus changed bytes, because the move is itself corpus drift for `server_impl`.
   - **No version bumps:** no storage, chunker or embedding versions change.
9. **Test seams, enumerations and silent degradations.**
   - **Hollow loaders:** any `spec_from_file_location` or generic `_load(name)` loader that can resolve a moved flat file, including computed names, gets a hollow module. Each such loader returns `sys.modules[name]` or loads the package file. Known sites:
     - `test_memory_records.load_independent_server` and `load_server`;
     - the child in `test_lifecycle_mutation_lock`;
     - `test_graph_snapshot_readers._load`;
     - `test_graph_indexer` (around 7215).
   - **Framework file enumeration:** one `framework_source_files()` test helper includes `wf_server/*.py` and excludes alias files. Every test that enumerates framework files goes through it, including:
     - the Windows spawn-isolation census (`test_server_tools`);
     - the tool-name census (`test_extension_tool_modules`);
     - the orphan-retirement caller census (`test_indexer`);
     - `test_reconcile_scan`;
     - `test_venv_bootstrap` (×2);
     - the scratch-copy identity tests (`test_index_handler_identity`, `test_path_containment`);
     - the pack builder in `test_upgrade_protocol`.

     A census refuses a flat `glob("*.py")` of the scripts root outside the helper.
   - **Scratch copies:** tests that copy single flat files into scratch trees also copy the package (`test_handler_modules`).
   - **Redirect patches:** patches of `server_impl.__file__` used to redirect handlers (`test_install_resume_integration`) patch `SCRIPTS_DIR` instead.
   - **Source-path reads:** literal and computed reads of a moved file's source (about 148 occurrences) go through a canonical-path helper that separates "reads source" from "names an archive member". A census fails when a test reads a moved flat path as source.
   - **Silent degradations:** each one the inventory found gets a discriminating test:
     - `SERVER_IMPL_VERSION` empty;
     - `_audit_harness_coherence` losing `server.py`, or losing `server_impl` tools by reading the alias;
     - `_default_template`, `_read_chunker_version` and `_upgrade_summary_sentinel` fallbacks;
     - `SOURCE_FILES` staleness.
10. **Reviewable migration and memory continuity.**
    - **Move/body equivalence:** file moves stay distinguishable from edits. A per-definition AST comparison against `git show <base>:<flat path>` normalizes the import rewrites and allowlists only the inventoried sites, the purge and alias block, and the scripts-root adaptations. Git rename detection is not relied on.
    - **No unrelated work:** no unrelated functional work joins.
    - **Follow-up:** the pre-existing `upgrade_handlers` post-upgrade `import server` second-instance finding (A4) becomes a follow-up plan through `wf_new_bug`; it is not fixed here.
    - **Memory records:** active memory records whose `## Targets` name moved flat paths (32 at readiness) are retargeted to the package paths. This keeps target matching, churn and decay attached to the implementation.
    - **Downstream merge procedure:** re-apply fork edits to `wf_server/<name>.py`, never over the flat alias. Include restart expectations.
11. **Canonical documentation.**
    - **ADR 1ye5y:** update it, or supersede it with a successor ADR that references it, because its title describes a flat layout. Record:
      - the package decision;
      - strategy (a), with the rejected (b), (b2) and (c) and their evidence;
      - that canonical package imports, the dual-key purge and eager aliases supersede the 1y0h2 "flat reloadable siblings" wording;
      - that its existing alias-declined rows concern tool-name aliases;
      - the old-runner constraint and the alias-removal precondition;
      - the flat names as the permanent public import surface;
      - the remaining composition-root coupling.
    - **Evaluator workflow doc:** `docs/contributing/review-and-evals.md` names E2 as the reference receipt and describes E0's layout-independent resolution.
    - **Doc census:** every living doc citing a moved module as a file (`<name>.py` or `scripts/<name>.py`) is re-derived at delivery and either moved to the package path or declared a module-name reference. Excluded: `docs/waves`, `docs/reports`, `docs/agents/memory`, `docs/plans`, `docs/evals`. Known hits:
      - `docs/architecture/search-architecture.md`, `graph-index-system.md`;
      - `docs/index.md`, `docs/references/project-overview.md`;
      - role docs `docs/agents/software-engineer.md`, `architecture-reviewer.md`, `specialists/red-team.md`.
    - **Checked and unchanged:** seeds 160 and 211, AGENTS.md, rendered hooks and the dashboard, which use module-name tokens.
    - **Also updated:** the other architecture, spec and build docs, and the code map through its generator.
    - **Downstream guidance names:**
      - the unchanged entry point and declaration paths;
      - the preserved flat imports;
      - that a full restart is recommended after upgrading. `wf_reload_mcp` on 1.25/1.26 serves the package, but `loaded_code_stale` stays until restart.
      - that a distribution shipping a flat module named `wf_server` would be shadowed by the package.
    - **Changelog:** the entry describes organization and compatibility only.

## Scope

**Problem statement:** server-owned modules increasingly occupy the framework's global flat namespace without an explicit package ownership boundary.

**In scope:** server composition implementation, response-handler owners and tool registry; minimal legacy adapters; reload/import/path/upgrade integration; regression coverage; architecture and downstream migration guidance.

**Out of scope:** a framework-wide package conversion; renaming MCP tools; changing extension trust or permissions; moving distribution-edited declarations; redesigning handler dependencies; new async middleware; repairing unrelated server behavior; changing index storage/models or forcing rebuilds; automatic removal of legacy imports; modifying a downstream repository.

## Acceptance Criteria

- [ ] AC-1: The package holds exactly the 12 inventoried modules with an import-free initializer, every other module stays flat, and each flat alias file has the exact pinned body. Declaration and permission consumers import without MCP dependencies. The alias table, the `SOURCE_FILES` entry and the evaluator moved-path table are each checked against a literal expected set.
- [ ] AC-2: Through the runner import and `wf_reload_mcp`, flat and package names are the same module object for every moved module. Private names are reachable, `patch.object` on the flat name takes effect, runner attribute writes are visible, and one live instance exists. The existing handler-first consumer path (`memory_cli`, `project_context_efficiency`) is pinned as documented behavior. Public consumer fixtures (an extension importing `server_impl` helpers, `memory_cli`, upgrade integration) reach the intended functions.
- [ ] AC-3: Stock and extension fixtures through the real server and MCP call path match the baseline tool, schema, tier, envelope and middleware contracts. `wf_audit` harness coherence reports the same live-tool set. The only golden differences are the enumerated, reviewed provenance changes.
- [ ] AC-4: Scratch-install reload probes observe edited behavior in every moved module, with stable module ownership, handler shutdown, notifications and extension failure cleanup. The rewritten reload census derives coverage from the package independently of the purge list. Mutants restoring a flat-only purge, or evicting the parent package, fail it.
- [ ] AC-5: A pack built from a scratch copy contains the package and the flat aliases. Fresh-install and 1.25/1.26 installed-runner upgrade fixtures (from the release tags, paths with spaces, including a dashboard-running case) reach a working server (`--dry-run` plus stdio `wf_server_info`), with mandatory modules accepted by the installed validation. A committed test proves a mandatory module importing `wf_server` is refused. Invalid or interrupted upgrade controls keep their guarantees, and the matrix names tested platforms without claiming native Windows.
- [ ] AC-6: After the move, an incremental index update resolves definitions and graph owners to package files, including handler-to-`server_impl` call edges counted against baseline. It removes obsolete implementation ownership and keeps the alias modules. E1 and E2 are recorded with the same E0 evaluator and fixture digest, alias paths never count as relevance matches, and any E2 fail carries the operator-review attribution.
- [ ] AC-7: Move/body-equivalence evidence separates moves and adaptations from intentional changes. Each changed mechanism has a discriminating failure control: scripts root, the harness-coherence carve-out, purge sets, eager aliases, `SOURCE_FILES`, evaluator resolution, test enumeration helpers and loaders. This change's own suites and new tests pass, and its authored or edited docs validate.
- [ ] AC-8: The ADR, architecture docs, evaluator workflow doc, re-derived doc-citation census and downstream guidance agree with the shipped import, reload, evaluation and upgrade behavior. They name the retained flat paths, the old-runner constraint, the alias-removal precondition and the remaining dependency limits. Retargeted memory records match the package paths.

## Tasks

- [x] Reconcile the landed 1yv9l extension contract and 1yzcz setup-readiness changes; freeze the baseline and module/consumer/path inventory (`evidence/readiness-inventory.md`, baseline `902f7edc`).
- [x] Demonstrate the canonical-module/flat-alias and reload strategy in disposable fixtures; record the old-runner matrix and evaluator-identity sequence (`evidence/demo/`).
- [ ] Prepare and independently review the admitted wave before any repository code edit.
- [ ] E0: make the retrieval evaluator layout-independent; focused independent review; operator commit of E0.
- [ ] E1: refresh the index and record the approved baseline receipt on the E0 commit.
- [ ] Create the package and alias table; move the 12 modules with body-equivalence evidence; apply scripts-root (with the harness-coherence carve-out), purge, eager-alias and `SOURCE_FILES` adaptations.
- [ ] Adapt test seams: hollow loaders, the `framework_source_files()` helper and census, scratch copies, redirect patches, the source-path helper and census, the rewritten reload census; add discriminating tests for each silent degradation.
- [ ] Retarget memory records that name moved flat paths.
- [ ] Verify a scratch-built pack, fresh-install and 1.25/1.26 tag-sourced upgrade fixtures (including dashboard running), public MCP contracts, extension behavior and failure paths.
- [ ] M then E2: incremental index update and the after receipt; graph ownership and call-edge verification.
- [ ] Update ADR 1ye5y (or a successor), architecture/spec/build/evaluation guidance, the doc-citation census and changelog; regenerate maps through their producer; open the `upgrade_handlers` second-instance follow-up plan.
- [ ] Run required delivery lanes and final framework and docs gates; hand off for operator closure.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Inventory and readiness | coordinator | overlapping work landed | Planning only until readiness; independent architecture and compatibility review |
| E0 evaluator and E1 baseline | implementer | readiness | Own reviewed and operator-committed step before any move |
| Package and compatibility migration | implementer | E1 recorded | One write owner for composition, aliases and reload |
| Distribution and evaluation integration | implementer | package boundary | Same write owner; no concurrent edits to shared startup paths |
| Independent delivery review | code, QA, architecture, security, docs-contract | frozen implementation | Read-only lanes; focus on module identity, old-runner behavior and public contracts |

## Serialization Points

- `.wavefoundry/framework/scripts/server.py`
- `.wavefoundry/framework/scripts/server_impl.py`
- `.wavefoundry/framework/scripts/wf_server/`
- `.wavefoundry/framework/scripts/`
- `.wavefoundry/framework/scripts/tests/`
- `docs/specs/mcp-tool-surface.md`
- `docs/architecture/`
- `docs/contributing/build-and-verification.md`
- `docs/contributing/review-and-evals.md`
- `docs/reports/`
- `docs/agents/memory/`
- `docs/agents/software-engineer.md`, `docs/agents/architecture-reviewer.md`, `docs/agents/specialists/red-team.md`
- `docs/index.md`, `docs/references/project-overview.md`
- `docs/references/codebase-map.md`
- `docs/repo-index.md`

The scripts-directory declaration is a conservative review floor, not authorization to refactor every script. The readiness inventory narrows exact edits. CHANGELOG.md receives the release note. Protect AGENTS.md, seeds, MCP host configurations, prompt bodies, distribution declarations and operator pins; any newly necessary behavioral policy edit requires a named plan revision. Architecture/code/QA/security/docs-contract reviewers are read-only; the implementer is the single source-writing owner.

## Affected Architecture Docs

- `docs/architecture/decisions/1ye5y-adr flat-sibling-tool-registry.md`: explicit package decision replacing the deferred flat-layout choice, compatibility and rejected alternatives.
- `docs/architecture/current-state.md`, `domain-map.md`, `layering-rules.md`: ownership and permitted import edges, including retained shared modules and invocation-time root dependencies.
- `docs/architecture/data-and-control-flow.md`, `cross-cutting-concerns.md`: runner/reload/upgrade identity transitions.
- `docs/architecture/testing-architecture.md`: module identity, reload census, package and old-runner verification.
- `docs/ARCHITECTURE.md`: update hub links if the package decision needs them; avoid unrelated rewriting.
- `docs/specs/mcp-tool-surface.md`, `docs/contributing/build-and-verification.md`: extension/legacy contracts and migration verification.
- `docs/contributing/review-and-evals.md`: E0 layout-independent evaluator resolution and E2 as the reference receipt.
- `docs/architecture/search-architecture.md`, `docs/architecture/graph-index-system.md`, `docs/index.md`, `docs/references/project-overview.md` and the listed role docs: file-path citations of moved modules, per the doc census in Requirement 11.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Package must represent an explicit boundary |
| AC-2 | required | Duplicate module state is a correctness hazard |
| AC-3 | required | Organization must preserve the public contract |
| AC-4 | required | Hot reload is load-bearing |
| AC-5 | required | Consumers enter through existing installers/runners |
| AC-6 | required | Path migration must preserve incremental retrieval |
| AC-7 | required | Reviewable mechanical change and honest verification |
| AC-8 | required | Downstream integrators need an accurate contract |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-09-24 | Planned on operator request to address the long-term package boundary now, while unrelated implementation continues. No source edits or wave activation. | ADR 1ye5y; current server runner/reload and _load_script; build_pack.collect_files; upgrade_extensions dashboard import; memory_cli handler import |
| 2026-09-24 | Admitted to wave `1yzd0`. Readiness inventory and alias/reload demonstration complete; the plan is amended to the evidence: 12-module moved set, strategy (a) flat aliases with an eager alias table, about 20 scripts-root sites (`_load_script` does need an edit), dual-key purge, mandatory flat aliases for old-runner pack validation, E0/E1/M/E2 evaluator sequence, hollow-loader and silent-degradation tests | evidence/readiness-inventory.md; evidence/demo/ |
| 2026-09-24 | Readiness round 1 (receipt `review-policy-32c232e62ee9cf27fdb2`): security and release approve; red-team, code, QA, docs-contract and architecture block. One bounded repair: harness-coherence carve-out; framework-file enumeration helper and census plus the full test-seam list; alias table pinned in `server_impl` with guarded eager registration; frozen `SOURCE_FILES` scope; exact alias bytes; evaluator workflow doc, receipts and doc-citation census; E0 as its own reviewed, operator-committed step with an E1 recovery path and exclusive alias matching; memory-record retargeting; AC-2 scoped to the runner path; AC-5 fixture sourcing | readiness-review.md |
| 2026-09-24 | Readiness round 2 (receipt `review-policy-69be0964cfd937179b64`): all lanes and both council seats approve. Implementation notes carried from the round: land each census as a red test against the post-move tree before adapting the seams it guards (red-team challenge); the named glob sites are non-exhaustive, so run the flat-glob census first (also `test_declared_wave_fixtures`, `test_events_only_residue_census`, `test_graph_query`, `test_model_bundle`, `test_marker_namespaces`, `test_render_agent_surfaces`, `test_record_layout_census`, `test_storage_upgrade_resume`, `sqlite_conversion_eval.py`); the flat names are the public import surface until the alias-removal precondition is met; memory retargeting is corpus drift to list in any E2 fail attribution; the doc-citation census also excludes `docs/agents/history/`, `docs/agents/memory-archive.md`, historical ADR sections and `CHANGELOG.md`, and additionally dispositions `docs/references/native-windows-support.md`, `docs/references/project-context-memory.md`, `docs/architecture/embedding-model.md`, `docs/ARCHITECTURE.md`, ADRs `1p4xx`/`1u49j`/`1yb8v` and `mcp-tool-surface.md`; `wf_server/__init__.py` stays empty, pinned by the structure test | readiness-review.md |
| 2026-09-24 | E0 implemented: `retrieval_eval` resolves the 12 moved modules through `SERVER_PACKAGE_MODULES` (package file when present, else flat) for production identity (`module_paths` disclosed), the `_git_binding` blob path, symbol-anchor resolution and result matching; the scripts root steps out of `wf_server/`; the corpus and its digest are never rewritten (`relevance_path_resolution` disclosed in the report). Pre-move equivalence on the real tree: empty resolution, identity module paths, production digest equal to the pre-E0 formula. Eight mutants each killed by an assertion | evidence/e0/mutants.out; evidence/e0/premove_equivalence.out |
| 2026-09-24 | E0 focused independent review: approve, two non-blocking findings repaired at once. E0-REV-1: the logical-name digest is pinned by a pure-move test (same bytes, flat vs package layout, equal digest). E0-REV-2: once `wf_server/` exists, a moved module without its package file raises `incomplete_server_package` instead of measuring the alias. Ten mutants, each killed by an assertion; pre-move equivalence re-confirmed | evidence/e0/mutants.out; evidence/e0/premove_equivalence.out |
| 2026-09-24 | E0 reverification: approve, both repairs hold. Residual E0-REV-3 repaired as well: the package is recognised by `wf_server/__init__.py`, not the directory, so an ignored `__pycache__` left by checking out a pre-move commit does not trigger the refusal. Eleven mutants, each killed by an assertion. E0 is ready for the operator commit | evidence/e0/mutants.out |
| 2026-09-25 | Package renamed `wf_server` by operator decision; independent rename verification approves (completeness, shadowing demo, `find_spec` absence, no framework collision). Implementation note for the move (RENAME-1): add `wf_server` to `mcp_tool_extensions.RESERVED_MODULE_NAMES` so a conflicting extension declaration is refused at validation, not only at load | Decision Log; evidence/e0/mutants.out |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-09-24 | Select a server-owned package with retained flat compatibility/declarations | Introduces a useful namespace while preserving downstream entry and distribution boundaries | Keep all modules flat: least immediate work but no explicit namespace as the subsystem grows. Package all framework scripts: broadens risk to CLI, validators, storage and upgrade machinery without a demonstrated benefit. |
| 2026-09-24 | Proposed package name wavefoundry_server; preserve server.py (renamed `wf_server` on 2026-09-25, below) | Avoids ambiguity between a server package and the established executable/import facade | server/: collides with established import spelling. Renaming all entry points: unnecessary downstream churn. |
| 2026-09-24 | Preserve legacy import paths with a single implementation owner | Existing extension and framework callers use public flat names; duplicated module execution would split state | Star-import forwarding or copied implementations: may preserve stale values/callables and break mutation/reload identity. Exact adapter design must be demonstrated before readiness. |
| 2026-09-24 | Preserve shared flat loader and recursive pack collection where they already work | _load_script assumes flat retained scripts; collect_files uses recursive os.walk, not a flat-only scan | Rewrite packaging wholesale: unsupported by current implementation. |
| 2026-09-24 | Stage separately from active work | Current active wave 1yzcz edits startup/readiness/upgrade seams this migration must consume | Fold into the active wave: expands scope and invalidates its review boundary. |
| 2026-09-24 | Flat aliases by `sys.modules` replacement (strategy (a)) with an eager alias table | Only strategy that keeps one module object through import, reload and old-runner reload, with private names, patching and runner writes intact (executed on 3.11 and 3.13) | Star-import stubs (lose private names, second instances, break reload); meta-path finder (reload no-op, unreachable for old runners and plain CLIs) |
| 2026-09-24 | Evaluator made layout-independent before the move (E0/E1) | The evaluator cannot run after the move unedited, and a signed before/after comparison needs one evaluator identity on both sides | Keep the evaluator unchanged and accept an unsigned computed comparison after the move (weaker; contradicts the approved-baseline requirement) |
| 2026-09-24 | Retarget memory records to package paths | Target matching, churn and decay should follow the implementation, not a never-changing alias | Map targets through the alias table in `memory_records` (code change in a retained substrate); disclose degraded recall |
| 2026-09-24 | `SOURCE_FILES` adds only the package `server_impl` | Keeps today's stale-code scope; handler edits are served by `wf_reload_mcp` | Add all 12 files (behavior change: every handler edit would demand a restart) |
| 2026-09-25 | Name the package `wf_server` (was `wavefoundry_server` in readiness) | Operator decision. `server` is taken: a `server/` package shadows the flat `server.py` entry point for every `import server` (`dashboard_lib`, `upgrade_handlers`, tests), verified by demonstration. The scripts root is on `sys.path`, so the package is a top-level import name and keeps a project prefix (PEP 8 naming; packaging guidance on unique top-level names); `wf_server` is unused in the repository and the tool venv | `wavefoundry_server` (longer), `mcp_server` (generic top-level name, and `mcp_server.mcp_tool_registry` stutters) |

## Risks

| Risk | Mitigation |
| --- | --- |
| Legacy and package imports create two stateful module instances | Single-owner import/reload fixture and independent review before migration |
| Moved __file__ changes path lookup, provenance or identity | Derive and classify each consumer at readiness; test real paths and archive loads |
| Older runner cannot reach the new implementation | Retain flat compatibility paths and exercise supported old-runner upgrade fixtures |
| Package reload leaves stale aliases or parent attributes | Independent module census and behavior-changing scratch reload probes |
| Refactor makes a stable retrieval comparison impossible | Inspect evaluator identity first and approve baseline sequencing before source moves |
| Concurrent startup work changes assumptions | Plan only now; reconcile overlapping landed changes before preparing/implementing |
| Cleaner paths mistaken for decoupled architecture | Document retained root dependencies; defer dependency redesign explicitly |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state. Overlapping waves 1yv9l and 1yzcz are closed and committed; the inventory is frozen at `902f7edc`.

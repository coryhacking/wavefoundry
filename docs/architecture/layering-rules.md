# Layering Rules

Owner: Engineering
Status: active
Last verified: 2026-09-25

## Allowed Dependencies

| Layer | May Import / Read | May Not Import / Read |
|-------|-----------------|----------------------|
| `.wavefoundry/framework/seeds/` | Nothing (text files only) | Any runtime code |
| `.wavefoundry/framework/scripts/` | Python stdlib; `.wavefoundry/framework/scripts/wave_lint_lib/` | `src/wavefoundry/` (future MCP) |
| `src/wavefoundry/` (future) | Python stdlib; third-party libs; `.wavefoundry/framework/seeds/` for seed resolution | `.wavefoundry/framework/scripts/` (use as library only if explicitly extracted) |
| `docs/` | N/A (markdown only; consumed by scripts, not importing scripts) | — |

## Boundary Invariants

| Edge | Invariant | Verified / Inferred |
|------|-----------|----------------------|
| `lifecycle_gates.py`, `lifecycle_gate_support.py`, `sensor_runner.py` → `wf_server/server_impl.py` | Extracted gates and support never import the orchestrator. Evidence is consumed through the `review_evidence` facade; configuration comes through unit inputs or support readers. Gates call support helpers through module attributes, and support imports neither gates nor orchestrator. Context contains only the six shared data fields. | Mechanical import-direction, facade-only, context-reader and reload tests in `test_lifecycle_gates_structure.py` (wave `1y044`); behavioral polarity coverage in `test_lifecycle_gates.py`. The same scans cover `sensor_runner.py`. |
| `wf_server/mcp_tool_registry.py` → `wf_server/server_impl.py` | The registry module never imports the orchestrator at any scope and holds no state; everything it needs arrives as arguments. `MIDDLEWARE` in `wf_server/server_impl.py` is the only place registration-time call wrapping is applied, and the three `_wrap_*` functions remain the only place a tool's callable is rebound. | `1y0be` AC-3 and AC-5; `test_mcp_tool_registry` module-boundary tests (`test_module_never_imports_server_impl_at_any_scope`, `test_module_never_rebinds_a_tool_callable`). |
| Flat aliases → `wf_server` package | Each moved module's flat file is exactly three statements that replace it in `sys.modules` with `wf_server.<name>`; package-internal code imports canonical package names, and a module the reload purge evicts is never imported with the `from wf_server import <module>` form, which would reuse the stale module left on the parent package. `wf_server/__init__.py` imports nothing. | `test_server_package` pins the package contents, alias bytes, alias table, one module object per name and eager registration; `test_mcp_tool_registry` pins the registry import form; `test_lifecycle_gates_structure` derives reload coverage from the package files |
| Upgrade-mandatory modules and outside consumers → `wf_server` | Never spell a package import, not even function-locally: installed 1.25 and 1.26 runners validate new packs with pack validation that counts only flat modules. The flat `server_impl` and `dashboard_handlers` aliases are required for that validation. | `test_server_package` runs the real `upgrade_protocol` validation over the mandatory modules and refuses package imports; old-runner matrix in wave `1yzd0` evidence |
| Handler siblings → `wf_server/server_impl.py` | No module-top import of the composition root or another handler sibling. Shared helpers resolve through function-local public imports; every handler sibling participates in purge-and-reimport reload. Registration remains in the composition root. | `test_handler_modules.py` checks import boundaries, re-export identity, name resolution, packaging and actual scratch reload; import-derived purge coverage is checked by `test_lifecycle_gates_structure.py`. |
| Declared extension modules → `wf_server/server_impl.py` | Registration stays in the composition root except for modules declared in `mcp_tool_extensions`, which register against a staging surface; `server_impl` imports them by declared name during registration (not at module top) and installs their tools before the prefix contract and `MIDDLEWARE`. `mcp_tool_roster` reads `mcp_tool_extensions` (the first import dependency between flat siblings, recorded in `1ye5y-adr`). | `test_extension_tool_modules.py` drives build, reload and refusal through the real server in a scratch scripts tree. |
| MCP server → target repo | Must never write outside configured allowed roots without mutation tool approval | Inferred from AGENTS.md and seed-050 safety rules |
| `build_pack.py` → VERSION | Must stamp VERSION before writing zip; VERSION must match zip basename date+letter | Verified from build_pack.py behavior described in seeds |
| `docs_lint.py` → manifest | Must fail (exit non-zero) when `framework_revision` in manifest does not match `.wavefoundry/framework/VERSION` | Verified from seed-010 lint gate requirement |
| `render_platform_surfaces.py` → `.github/` | Must not create or modify `.github/workflows/` — only `.github/hooks/` | Verified from seed-050 scope boundary |
| `wf techdocs-baseline` / `wf_techdocs_baseline` → `catalog-info.yaml`, `mkdocs.yml`, `docs/index.md` | A stateless materializer invoked explicitly, by the CLI or by `wf_techdocs_baseline(mode='run')` (which serializes its writes under `project_state_publication_lock` and is a registered `fail_fast` publisher; `mode='dry_run'` writes nothing): writes only absent members (`O_EXCL`), only after the navigation-target precondition and the containment classification of all three destinations, and is never called by the render pass, setup Step 1, or the upgrade surface-rendering phase; no upgrade-lock ownership; the AC-5 publication oracle is a stdlib matcher (scripts row 2 above stays stdlib-only) | Verified by `test_render_agent_surfaces.TechdocsBaselinePreconditionAndPathTests` (negative render/setup/upgrade paths, containment, `O_EXCL`), `TechdocsBaselineStateMatrixTests`, `TechdocsExcludeDocsOracleTests`, `test_wf_cli.TechdocsBaselineSubcommandTests`, `test_server_tools.TechdocsBaselineToolTests` (MCP dry_run/run, publication lock, checkpoint refusal, shared function) |
| `wf techdocs-audit` / `wf_techdocs_audit` → `mkdocs.yml`, `catalog-info.yaml`, `docs/**`, git baseline | A read-only reporter that gates nothing: no lock, no publication-writer registration, and no write on any path. It depends on the standard library plus `wave_lint_lib` (metadata and link primitives), `render_agent_surfaces` (trio state and the preserved containment wrapper, delegating its pure comparison to `path_containment`), `index_state_store` for every git read, and `subprocess_util` for the isolated, console-free, UTF-8 worker. Scripts row 2 above stays free of third-party YAML, since the `mkdocs.yml` parser is a recognized-shape stdlib parser that degrades explicitly rather than guessing. Both public entries use one ten-second worker deadline and perform no repository-derived I/O after expiry. `docs_dir` is contained through that wrapper and shared comparison; nav entries are screened lexically, then every survivor and nav candidate is checked by realpath before `is_file()` or content access. Realpath may perform metadata lookup on an external target; the audit then refuses before `is_file()`, open, or content read. Escaping nav symlinks are named logically under `publication.unsafe_nav_targets` and degrade with `nav_target_escapes_root`; escaping survivor candidates are named under `publication.unsafe_survivor_targets`, degrade with `survivor_target_escapes_root`, and remain part of link-boundary scoring for both the normalized directory node and its descendants. The read-tier MCP envelope independently caps findings, survivor pages, and unsafe survivor targets at 200, reporting the true unsafe-target total and the omitted count when that cap fires; the CLI remains uncapped. Timeout degrades with `audit_timeout`, so no incomplete path can report clean. | Verified: `test_techdocs_audit_lib.TechdocsAuditDegradeTests` (docs_dir containment with an instrumented read proof, the escaping-survivor logical-name/degrade/link-finding/no-external-read proof including exact unsafe-directory node, intentionally skipped trailing-slash link, descendant, and in-root polarity, the realpath backstop, the shape degrades, `test_the_walk_never_descends_outside_the_root`, and the escaping/in-root nav-symlink polarity control), `TechdocsAuditBoundaryAgreementTests` (the pinned oracle plus an external `git check-ignore` oracle), the bounded-runner timeout/isolation/error tests including the recorded crossing-pattern reproduction and the no-trio-state-after-expiry assertion, `test_wf_cli.TechdocsAuditSubcommandTests` (timeout envelope plus whole-tree digest unchanged), and `test_server_tools.TechdocsAuditToolTests` (read tier, no publisher, advisory timeout diagnostic, public description, cap-fired unsafe-target arithmetic, and below-cap polarity) |
| `review_policy.py` carrier registry → renderer | Renderer writes only the registered marker-owned region and preserves surrounding bytes | Verified by registry/renderer carrier tests |
| `review_policy.py` carrier registry → lifecycle reconciler | Reconciler writes only exact registered legacy markers or byte-known baseline sections after complete preflight; ambiguity or symlink escape writes nothing | Verified by reconciler mutation and containment tests |
| Fresh agent renderer → lifecycle reconciler | The lifecycle reconciler remains primary owner; after all-path containment preflight, the freshly extracted renderer may replay only the shared `UPGRADE_POLICY_BLOCK` marker in `docs/prompts/upgrade-wavefoundry.prompt.md` to close the installing-upgrade old-code window, preserving every byte outside that marker and adopting no other lifecycle carriers | Verified by transition, preservation, idempotence, and symlink-refusal tests |
| `review_policy.py` carrier registry → direct docs | Direct-doc carriers are validation-only and never target-repository writers | Verified by owner-permission registry tests |
| Upgrade → project publishers | Upgrade acquires lifecycle then publication ownership; registered publishers fail fast from the durable checkpoint, except the two memory-recovery writers at the exact memory pause | Verified by lock-order, checkpoint, and public-wrapper tests |
| FROM-runner → TO-tree summary producer | The pre-extraction parent produces the primary-phase summary only through the pinned `--emit-summary` contract on the freshly extracted tree (argv, sentinel prefix, `summary_schema_version` token, pinned timeout; upgrade lock as the sole state carrier, old-schema tolerant); the surface never changes silently (deliberate versioned evolution bumps the schema token); any contract failure degrades to the parent's marked in-process fallback, never a second sentinel and never unlabeled old-schema output. This boundary governs the PRIMARY-phase producer only; wave 1uf68 additionally has the separate cleanup process carry the same token at its own emit site, which is not a second sentinel in this stream (each subprocess invocation's stdout is parsed on its own) and does not make the token exclusive to this boundary | Verified by the permanent `DelegatedSummaryContractTests` plus the degradation and mutual-exclusion tests |
| `index_state_store` publication → upgrade cleanup | `index.sqlite` is the sole durable semantic AND graph authority. The freshly loaded cleanup process may inspect one stable complete docs-and-code token and bounded layer summary, but it must not create a second receipt or treat the upgrade lock's audit copy as authority | Verified by upgrade stable-token, incomplete-epoch, active-manifest, and cleanup-retry tests |
| `docs/workflow-config.json` → lifecycle gates | Project policy enters through typed configuration only; the server never imports repository Python. Prepare `ready`/`create` may execute list-form sensors named in `phase_gates`; close `create` executes them only when no blocking diagnostic has accumulated at the gate stage; read-only `dry_run` and its `evaluate` alias execute nothing. | Clause by clause. Typed-configuration entry: `1y0bd` AC-2, prepare clause; `1y0bd` AC-3; `1y0bd` AC-4 (the exclusivity "only" is **Inferred**: refusing malformed entries inside the key is not the proposition that no other entry path exists). No repository-Python import: **Inferred** from `1yb53-adr` and the absence of any import site; no criterion asserts it. Prepare execution: `1y0bd` AC-2, prepare clause; `1y0bd` AC-6, mutating-outcome clause, prepare portion; `1y0bd` AC-4; `1y0bd` AC-1. Close execution and its precondition: `1yd98` AC-1; `1yd98` AC-4; `1y0bd` AC-4. Read-only: `1y0bd` AC-6, read-only clause. |

> **Amended 2026-09-18 by wave `1yd97 phase-gate-follow-ups` (`1yd98-enh`).** The `docs/workflow-config.json` → lifecycle gates row gained the close precondition and its clause-by-clause Verified column; the row was corrected in place. Superseded wording, preserved verbatim: "| `docs/workflow-config.json` → lifecycle gates | Project policy enters through typed configuration only; the server never imports repository Python. Prepare `ready`/`create` and close `create` may execute list-form sensors named in `phase_gates`; read-only `dry_run` and its `evaluate` alias execute nothing. | Phase-gate execution, validation and provenance tests (`1y0bd` AC-2 and AC-6). |"

## Violation Detection

- Lifecycle boundaries: AST checks in `test_lifecycle_gates_structure.py` verify import direction, facade-only evidence and data-only context; behavior tests verify gate polarity. Other dependency edges remain code-reviewed rather than covered by a general import linter.
- Boundary invariants: enforced through MCP **`wf_validate_docs`** (agents) or **`wf docs-lint`** (hooks/CI), plus seed protection hook and framework plan gate hook.

## Shared index storage (waves 1xjmm, 1xny6)

`sqlite_runtime` is the sole runtime connection policy for `index.sqlite`, and no module
may open that file with a second SQLite library in one process. `index_paths` is
the one definition of the database's current and legacy filenames; it deliberately
does NOT decide authority when both exist — that is the migration receipt's job.
`sqlite_vector_store` owns canonical chunk/vector schema and bounded retrieval;
`graph_store` owns the graph, community and derived-output DDL, emitted into the
CALLER's transaction and never opening a connection of its own; `index_state_store`
owns bookkeeping, FTS validation and publication fences; `indexer` owns the single
transaction combining every one of their mutations. `graph_snapshot` is the only
runtime generation-bound read path for graph and community rows: it opens read-only, reads
one SQLite snapshot, and returns immutable content rather than a live handle. Query
consumers open read-only connections and cannot repair or migrate persistent data.

## Shared path resolution (waves 1t3gt, 1xjmm, 1y0gz)

Four stdlib-only modules are the single owners of path resolution and no other
module may re-derive what they answer: `repo_root` discovers the repository root,
`path_containment` owns containment comparisons (including a pure already-resolved entry point),
`index_paths` names the index database, and `record_paths` resolves the wave and
plan record roots from its own module constants (`WAVES_ROOT = "docs/waves"`,
`PLANS_ROOT = "docs/plans"`, `NESTED = False`, `MAX_DEPTH = 4`). The constants
are the only definition of the layout: a downstream fork edits them at merge
time, nothing is read from `docs/workflow-config.json` at runtime (a
`record_layout` block or `wave_implement.wave_root` is inert), and the layout of
a process is fixed at import. `record_paths` validates the constants against the
repository fail-closed: an absolute, `..`, or empty root, a root or an ancestor of
an absent root that is a file or a dangling symlink, a root that escapes through
a symlink, a root or ancestor that is a symlink alias or case alias of the
canonical in-repository directory (an in-repository symlink is no longer
accepted), equal or nested roots (by spelling or by inode, judged against the
nearest existing ancestor of an absent root), a non-boolean `NESTED`, or a
`MAX_DEPTH` outside 1 to 8 raises
`RecordLayoutInvalid`; docs-lint reports it as the `record_layout_invalid` error
and every lifecycle tool returns the same `record_layout_invalid` diagnostic and
performs no read or write; nothing falls back silently. `layout_constants()`
returns the four values at call time and every cache keyed on record discovery
(the lint roots cache, `McpRepoCache`) folds it into its key. For the shipped
constants it builds paths exactly as the call sites did before it existed, so
cache fingerprints and rendered paths are byte-identical. A census test forbids
the `docs/waves` and `docs/plans` literals in every other non-test module outside
an explicit allowlist whose reasons are comment, docstring, user-facing message,
or `pinned_evidence` (a shipped report pins the module's SHA-256). Docs-lint
requires `<waves_root>/README.md`, and the lint and gardener walkers union
`docs/` with the resolved roots when a root lies outside `docs/`.

Wave record discovery is one walk (wave 1y043): `record_paths.walk_wave_candidates`
enumerates the waves root's child directories (flat, the shipped `NESTED = False`)
or, when `NESTED` is true, a depth-first walk bounded by `MAX_DEPTH` (1 to 8,
shipped 4; it counts the wave folder's own depth below the waves root, so 1 means
direct children only) that never enters a symlink or a dot-prefixed directory and
never descends into a folder that holds a `wave.md`; `discover_wave_dirs` keeps
the folders that hold one. The server, docs-lint (every `wave_lint_lib`
enumerator, including `_collect_wave_state`, `check_closed_wave_requirements`,
`check_wave_docs`, `check_prepare_council_verdict`, and
`check_prepare_council_roster_evidence`), memory backfill, memory supply,
lifecycle-id minting, commit provenance, and the review-policy upgrade planner all
enumerate through it, and no module discovers wave records by enumerating the
waves root itself with `iterdir`, `rglob`, or a `*/wave.md` glob of its own;
change-doc lookup (`_resolve_change_doc_matches`) and the docs-lint and gardener
corpus walks stay recursive over the roots by design, because they look for
documents, not for wave folders. A wave id at two paths is
`ambiguous_wave_id` from docs-lint and from every lifecycle tool that resolves a
wave (`wf_current_wave`, `wf_list_waves`, `wf_prepare_wave`, `wf_add_change`,
`wf_review_event`, `wf_close_wave`, `wf_pause_wave`, and the rest), and no
lifecycle mutation proceeds on it. A tool invocation walks at most once:
`McpRepoCache.list_waves_cached` performs the walk, keys the cache on the
directory fingerprint, `layout_constants()`, and the discovered paths, and threads
the result as `wave_dirs` to `list_waves` and the record lookups.

The standalone `graph_call_census.py` diagnostic is an explicit exception: in its
own process, it uses stdlib SQLite to inspect relational graph rows in one
read-only transaction without loading the runtime or vector extension. It is
not a serving path and must not open a second SQLite library inside an existing
runtime process. It confines the database and required existing WAL sidecars to
the selected repository, refuses missing sidecars rather than creating them,
and closes its connection explicitly. It does not repair, migrate or publish data.

`setup_readiness.py` is a second diagnostic exception, with a distinct ownership
contract: the parent uses only stdlib metadata and never imports SQLite or the
vector runtime. At most one isolated `-I -S -B` child inspects exact relational
metadata in a read-only, query-only transaction. Normal SQLite WAL/SHM coordination
is allowed; application-data writes, checkpoints, recovery, migration and explicit
sidecar cleanup are not. Failed or inconsistent observations are indeterminate.
The child deadline does not promise a global deadline for parent filesystem reads.
`setup_requirements.py` owns the shared dependency declarations and setup CLI
grammar used by setup and the assessor; metadata inspection must not activate the tool environment or execute
its `.pth` files. Advisory stamps never replace live compatibility and ownership checks.
The same holds for its consumers that run before activation: `wf setup --check`,
MCP startup, and the Claude Code session-start hook, whose body is composed without
the tool-environment bootstrap and writes no framework bytecode.

`sqlite_storage_migration` may load the pinned legacy reader only during supported
setup- or upgrade-owned conversion. Its durable receipt records recovery and cleanup progress;
the existing build epoch remains publication authority. Graph participates in the shared publication transaction. Memory retains
separate persistent ownership.

## Index compatibility ownership (wave 1xxc9)

`index_compatibility.py` owns stdlib-only classification, typed refusals and
producer source identity; it does not own migrations or create connections.
Ordered revisions come from producer declarations. Opaque model/FTS identities
retain their selection/integrity contracts and are never sorted as versions.
Writer owners invoke compatibility under the stable SQLite write snapshot before
mutation, preserving the existing epoch CAS and publication transaction. A
preflight alone is insufficient for a worker prepared before newer publication.
The upgrade owns first-hop host coordination through `index_guard_handoff`,
separate from the storage conversion receipt; incoming code cannot protect
already-loaded unprotected hosts without the confirmed fresh-CLI handoff.

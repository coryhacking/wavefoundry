# Code Navigation Never Walks Unfiltered Files

Change ID: `1z9u7-bug navigation-walker-fallback-leaks-unfiltered-files`
Change Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-09-29
Wave: 1za2y code-tool-and-index-status-fixes

## Rationale

`code_constants` returned raw bytes from `.wavefoundry/index/index.sqlite` beside real matches, and `code_keyword` read the 524 MB index file (11.8 s for one call). Every code-navigation handler gets its files from `server_impl._walk_repo_for_navigation`, which calls the module-level `server_impl._indexer_module()`. That function re-executes `indexer.py` from disk on every call instead of using the process's cached module (`_load_script("indexer")`). Importing `indexer.py` calls `index_compatibility.register_loaded_source()`, which raises `IndexCompatibilityError("index_runtime_stale")` once any index-producer file has changed on disk since the server captured it. `_walk_repo_for_navigation` catches that with a bare `except Exception` and falls back to `root.rglob("*")`, which excludes only `.git`: no ignore rules, no binary or size filter, no dot-directory pruning. A server that outlives a framework edit or upgrade therefore serves index databases, binaries, `node_modules` and virtual environments. A scratch reproduction returned 3489 files instead of 2719.

Operator decision (2026-09-29): when the on-disk indexer is newer than the running server, navigation keeps using the walker the server already loaded, with a stale-runtime warning, rather than failing or duplicating the walker's filter rules.

## Requirements

1. `server_impl._indexer_module()` returns the process's cached indexer module (`_load_script("indexer")`). No code in the server process executes `indexer.py` afresh per call; the set to change is every fresh execution of `indexer.py` in `wf_server/` (derive it from the `spec_from_file_location` loads of `indexer.py`, which today include `_indexer_module` and the lock-owner load in `index_handlers.py`). Change `1z9yb` relies on this shared module instance.
2. The server makes a best-effort load of its indexer module at startup, so the walker the operator chose to keep using exists before any later framework edit. A failed startup load does not stop the server. The last indexer module that loaded successfully stays reachable across `wf_reload_mcp`: a reload clears the script cache but not `index_compatibility`'s capture, so a fresh load after a producer edit fails as stale, and navigation then keeps using that last good module.
3. The unfiltered `rglob` fallback in `_walk_repo_for_navigation` is removed. When the process has no loaded indexer and cannot load one, every public tool whose handler reaches the walker returns a structured error naming the cause and recommending a restart of the MCP server, never a file list and never empty results; helpers between the tool and the walker propagate the error rather than absorbing it.
4. When the installed producer sources differ from the running server's capture (`index_compatibility.ensure_runtime_current`), each such tool's response carries a warning diagnostic naming `index_runtime_stale` and recommending a restart of the MCP server. The freshness check is cached on the producer files' stat signatures (size, mtime, inode and ctime, since a replacement can keep size and mtime) so a navigation call costs stats, not hashes, unless a signature changes.
5. The affected tool set is derived through to the public MCP tools whose handlers reach `_walk_repo_for_navigation` directly or through helpers. At planning time that set is `code_list_files`, `code_keyword`, `code_constants`, `code_pattern`, `code_definition`, `code_references`, `code_impact` (heuristic path) and the graph tools that call it in `graph_handlers.py`; the derivation governs if it differs.
6. With a current runtime and a loaded indexer, file lists and responses are unchanged.
7. `docs/specs/mcp-tool-surface.md` states the navigation contract for a stale runtime (the loaded walker keeps serving, with the warning) beside its `index_runtime_stale` refusal rules, which otherwise read as refusal-only.

## Scope

**Problem statement:** a stale runtime turns code navigation into an unfiltered walk of the repository.

**In scope:**

- `_walk_repo_for_navigation` and `_indexer_module` in `wf_server/server_impl.py`, every fresh execution of `indexer.py` in `wf_server/` (including the lock-owner load in `index_handlers.py`), the best-effort startup load, and the error and warning handling in every public tool that reaches the walker, including the helpers in `codenav_handlers.py` and `graph_handlers.py`.
- The stale-runtime navigation contract in `docs/specs/mcp-tool-surface.md`.
- Tests for the stale-runtime and no-indexer paths.

**Out of scope:**

- The index compatibility guard itself and when it captures sources.
- Glob matching (change `1z9ya`).
- `_load_script` itself and its callers that already use the cached module.

## Acceptance Criteria

- [x] AC-1: with an index-producer file changed after the server loaded its indexer, every tool in the derived set returns results over the same file set as with a current runtime (no `.wavefoundry/index/` path, no gitignored or binary file) and carries the `index_runtime_stale` warning recommending a restart of the MCP server.
- [x] AC-2: when no indexer can be loaded in the process, every tool in the derived set returns a structured error recommending a restart of the MCP server, with no file list and no empty-result success; the `rglob` fallback no longer exists.
- [x] AC-3: `_indexer_module()` returns the same module object as `_load_script("indexer")`, no fresh execution of `indexer.py` remains in `wf_server/`, and a server start loads the indexer.
- [x] AC-4: with a current runtime, navigation responses carry no new diagnostic and their file sets are unchanged, and the freshness check does not re-hash producer files when their stat signatures are unchanged.
- [x] AC-5: the spec states the stale-runtime navigation contract.
- [x] AC-6: the change's own suites and every test it adds pass, and the documents it edits validate.

## Tasks

- [x] Make `_indexer_module()` return `_load_script("indexer")`, remove every fresh execution of `indexer.py` in `wf_server/`, and remove the `rglob` fallback.
- [x] Best-effort indexer load at server start.
- [x] Stale-runtime warning with a stat-signature cache, and the no-indexer error propagated to every tool in the derived set.
- [x] Tests: stale-runtime and no-indexer fixtures across every tool in the derived set; module identity; startup load; no re-hash on unchanged signatures.
- [x] Spec: the stale-runtime navigation contract.
- [x] CHANGELOG Fixed entry.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Walker and callers | implementer | readiness | |
| Review | code, QA reviewers | implementation | |

## Serialization Points

- `.wavefoundry/framework/scripts/wf_server/server_impl.py`, `.wavefoundry/framework/scripts/wf_server/codenav_handlers.py`, `.wavefoundry/framework/scripts/wf_server/graph_handlers.py`, `.wavefoundry/framework/scripts/wf_server/index_handlers.py`
- `.wavefoundry/framework/scripts/tests/`
- `docs/specs/mcp-tool-surface.md`

Root release note: CHANGELOG.md.

## Affected Architecture Docs

N/A: the navigation walker stays the indexer's `walk_repo`; this removes a fallback and adds a diagnostic inside the existing handlers.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | The observed defect |
| AC-2 | required | Fail closed when there is no walker |
| AC-3 | required | One shared indexer module, loaded at start |
| AC-4 | required | No change for a current runtime; bounded cost |
| AC-5 | important | The contract is documented |
| AC-6 | required | Verification |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-09-29 | Delivery repair round 1: QA-1 (startup test was satisfied by setUp's own load) fixed by clearing the loaded indexer and running only `register_mcp_surface`; a scratch mutant removing the startup load now fails it. ARCH-4 (design note): helpers still absorb `NavigationWalkerUnavailable` and the tool wrapper's per-call event turns it into the error; a walker call outside a wrapped tool call (worker thread, internal caller) returns no files rather than an unfiltered list, which is the safe direction | `test_navigation_walker_runtime` OK |
| 2026-09-29 | Implemented. `_indexer_module()` returns `_load_script("indexer")` and keeps the last good module under `sys.modules["_wavefoundry_indexer_last_good"]`; the rglob fallback is removed; `_walk_repo_for_navigation` raises `NavigationWalkerUnavailable` (converted by the tool wrapper to a `navigation_indexer_unavailable` error, including the `code_impact` heuristic path) and records an `index_runtime_stale` warning from a stat-signature cache over the index producer sources; `register_mcp_surface` loads the indexer at start; the lock-owner read in `index_handlers.py` uses the shared module. Scratch mutants: restoring the old rglob fallback fails `MissingIndexerTests` for every tool in `TOOL_CALLS` and the source pin in `SharedModuleTests`; dropping the stale notice fails `StaleRuntimeTests` for every tool and `WrapperMechanismTests`; forcing a rehash on every call fails `FreshnessCacheTests`. Gapfill: call sites were enumerated with grep and AST walks, not `code_references`, because the index runtime these tools depend on is the one being changed and `code_keyword` globs had the `**/` defect fixed by 1z9ya | `tests/test_navigation_walker_runtime.py` 10 OK |
| 2026-09-29 | Implementation correction: the remedy is a server restart, and the last good indexer module survives `wf_reload_mcp` (see Decision Log). | `server.perform_mcp_reload` purge scope; `index_compatibility` module docstring |
| 2026-09-29 | Readiness review folded in: `_indexer_module` returns the cached module (shared with 1z9yb), every fresh indexer execution removed, startup load, stat-cached freshness check, affected tools derived through to the public tools, spec contract. | readiness review (code, security, architecture, docs lanes) |
| 2026-09-29 | Planned. Root cause reproduced by forcing one stored producer hash stale: 3489 files instead of 2719, including `.wavefoundry/index/*` and 351 files under `node_modules` and `.venv`. | investigation of `_walk_repo_for_navigation`, `_indexer_module`, `index_compatibility.register_loaded_source` |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-09-29 | Recommend restarting the MCP server, not `wf_reload_mcp` | Implementation found that `wf_reload_mcp` keeps `index_compatibility` (only the script cache and `wave_lint_lib` are purged), so a reload cannot adopt a new index runtime; the guard's own docstring says restarting is the only way | Recommending `wf_reload_mcp` (a remedy that cannot work) |
| 2026-09-29 | Use the walker the server already loaded, with a stale-runtime warning | Operator choice: navigation keeps working after framework edits, with no duplicated filter rules | Fail closed until restart (tools unusable after every framework edit); a filtered fallback walk (duplicates `.gitignore`, binary, size and dot-directory rules and drifts from them) |

## Risks

| Risk | Mitigation |
| --- | --- |
| The loaded walker's filters lag the on-disk ones until the server restarts | The warning names the cause and the remedy |
| A helper's broad `except` turns the no-indexer error into empty results | Derive the public tools through their helpers; test the no-indexer path per tool |
| The first indexer load happens after a producer edit, so there is no loaded walker | Best-effort load at server start; otherwise the documented error with the restart remedy |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.

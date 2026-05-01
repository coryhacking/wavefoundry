# Framework Script Code Quality

Change ID: `12a0c-debt framework-script-code-quality`
Change Status: `complete`
Owner: implementer
Status: complete
Last verified: 2026-04-30
Wave: 129p8 mcp-docs-search-reliability

## Rationale

A systematic code review of all framework Python scripts identified a set of correctness, performance, and maintainability issues. The most impactful are: `_load_script` re-executes modules on every call (correctness/perf), `run_validate` does not forward `PROJECT_ROOT` to its subprocess (correctness), dead code in `docs_search_response` and `indexer.py` obscures the actual logic, and five independent copies of the repo-root discovery function diverge silently. Additional issues include trivially wrong conditional branches, missing docstrings on non-obvious helpers, and an orphaned `has_markdown_metadata` function. Fixing these reduces maintenance surface, improves correctness under multi-project use, and makes the codebase legible to new contributors.

## Requirements

1. `_load_script` in `server.py` must cache loaded modules so that a module is executed at most once per process, using a namespaced key that does not pollute the public `sys.modules` namespace.
2. `run_validate` in `server.py` must pass `PROJECT_ROOT=str(root)` in the subprocess environment, consistent with `run_garden` and `run_sync_surfaces`.
3. The dead `_build_chunks_for_file` function in `indexer.py` must be removed.
4. The unreachable `else` branch in `docs_search_response` (`if not fallback_reason: ... else: ...`) must be removed; the search fallback logic must be simplified to reflect actual control flow.
5. The trivially-wrong `next_tools` conditional in `wave_list_plans_response` (both branches return `["wave_help"]`) must be corrected: return `["wave_change_create", "wave_current"]` when plans exist.
6. The orphaned `has_markdown_metadata` function in `wave_lint_lib/helpers.py` must be removed.
7. The five duplicated repo-root discovery implementations (`server.py:_discover_root`, `indexer.py:_discover_root`, `lifecycle_id.py:discover_repo_root`, `render_platform_surfaces.py:discover_repo_root`, `docs_gardener.py:project_root`) must each receive a comment pointing to the canonical version and noting the intentional difference (if any), until a full consolidation is planned in a future wave.
8. The `_dir_fingerprint` duplication in `server.py` (`_wave_fingerprint`, `_plans_fingerprint`, `_prompts_fingerprint`) must be extracted into a single shared helper.
9. Public and non-obvious functions across all scripts must have docstrings or inline comments where they currently have none. Priority: `_load_script`, `_lifecycle_module`, `_ensure_no_extra_args`, `_dir_fingerprint` (post-extraction), `_live_docs_chunks`, `_layer_health`, `McpRepoCache`.
10. All changes must leave 293+ tests passing and `docs-lint` clean.

## Scope

**Problem statement:** Framework Python scripts accumulated correctness bugs, dead code, and missing documentation during rapid feature development. No single issue is catastrophic, but together they raise the maintenance cost and create hazards for future contributors.

**In scope:**

- `server.py`: `_load_script` caching, `run_validate` env fix, dead code removal, fingerprint helper extraction, `next_tools` fix, docstrings
- `indexer.py`: remove `_build_chunks_for_file`
- `wave_lint_lib/helpers.py`: remove `has_markdown_metadata`
- All scripts: add docstrings/comments to non-obvious public functions
- Root-discovery functions: add cross-reference comments

**Out of scope:**

- Consolidating the five root-discovery implementations into a shared utility (deferred; requires touching five files with different callers and error semantics)
- Subprocess-to-in-process refactor for `run_validate`/`run_garden`/`run_sync_surfaces` (larger change; deferred)
- `indexer.py` lock-spin timeout (A-13 from review; separate reliability concern)
- `_layer_current_hashes` hash caching (A-2; separate performance concern)
- `render_platform_surfaces.py` generated-hook static analysis (I-7; separate testing concern)

## Acceptance Criteria

- AC-1: `_load_script` executes each module at most once per process; subsequent calls return the cached module object.
- AC-2: `run_validate` subprocess receives `PROJECT_ROOT=str(root)` in its environment.
- AC-3: `_build_chunks_for_file` does not exist in `indexer.py`.
- AC-4: `has_markdown_metadata` does not exist in `wave_lint_lib/helpers.py`.
- AC-5: The unreachable `else` branch is removed from `docs_search_response`; the fallback logic reads cleanly.
- AC-6: `wave_list_plans_response` returns `["wave_change_create", "wave_current"]` in `next_tools` when plans exist and `["wave_help"]` when empty.
- AC-7: `_wave_fingerprint`, `_plans_fingerprint`, `_prompts_fingerprint` are replaced by calls to a shared `_dir_fingerprint` helper.
- AC-8: Root-discovery functions each have a comment identifying the canonical reference and any intentional differences.
- AC-9: All functions listed in Requirement 9 have docstrings or inline comments.
- AC-10: 293+ tests pass; `docs-lint` clean.

## Tasks

- Fix `_load_script` caching (`server.py`)
- Fix `run_validate` env propagation (`server.py`)
- Remove `_build_chunks_for_file` (`indexer.py`)
- Remove `has_markdown_metadata` (`wave_lint_lib/helpers.py`)
- Remove dead `else` branch in `docs_search_response` (`server.py`)
- Fix `next_tools` in `wave_list_plans_response` (`server.py`)
- Extract `_dir_fingerprint` helper, update callers (`server.py`)
- Add root-discovery cross-reference comments (all five files)
- Add docstrings/comments to listed functions (all affected files)
- Run tests and docs-lint; verify AC-10

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
|------------|-------|------------|-------|
| server-fixes | implementer | — | `_load_script`, `run_validate`, dead branch, `next_tools`, fingerprint extraction, docstrings |
| indexer-cleanup | implementer | — | Remove `_build_chunks_for_file` |
| helpers-cleanup | implementer | — | Remove `has_markdown_metadata` |
| root-discovery-comments | implementer | — | Comment all five files |
| verification | implementer | all above | Tests + docs-lint |

## Serialization Points

- `server.py` is the only file with multiple concurrent changes in this debt item; serialize all server edits within a single pass.

## Affected Architecture Docs

N/A — all changes are internal implementation quality improvements within existing module boundaries. No boundary, flow, or verification contract changes.

## AC Priority

(Populated at Prepare wave.)

| AC | Priority | Rationale |
|----|----------|-----------|
| AC-1 | required | Correctness: module re-execution on every call |
| AC-2 | required | Correctness: wrong repo linted when PROJECT_ROOT is set |
| AC-3 | required | Dead code removal |
| AC-4 | required | Dead code removal |
| AC-5 | required | Dead code removal |
| AC-6 | important | Incorrect next_tools guidance for agents |
| AC-7 | important | DRY: three near-identical functions |
| AC-8 | important | Maintenance: five diverging copies of same logic |
| AC-9 | nice-to-have | Readability: docstrings on non-obvious helpers |
| AC-10 | required | Verification gate |

## Progress Log

| Date | Update | Evidence |
|------|--------|----------|
| 2026-04-30 | Change doc created from systematic code review findings | Code review output in session |
| 2026-04-30 | All 10 ACs verified; AC-1–4, 6–9 already addressed by prior work; AC-5 fixed (dead `fallback_reason == "missing_index"` branch) | 309 tests pass; docs-lint clean |

## Decision Log

| Date | Decision | Reason | Alternatives |
|------|----------|--------|--------------|
| 2026-04-30 | Defer root-discovery consolidation to future wave | Five callers with different error semantics; consolidation is a larger change than the current debt scope | Consolidate now (rejected: too broad) |
| 2026-04-30 | Defer subprocess-to-in-process refactor | Requires understanding isolation requirements for each caller | Do it now (rejected: scope creep) |

## Risks

| Risk | Mitigation |
|------|-----------|
| `_load_script` cache prevents hot-reload in dev | Document that the cache is intentional and process-scoped; `_script_cache.clear()` is available if needed |
| Removing `_build_chunks_for_file` breaks an undiscovered caller | Grep for all call sites before deletion |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.

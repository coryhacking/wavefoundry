# Upgrade Guidance Treats an In-Process Reload as Complete When Modules Stay Stale

Change ID: `1zf1x-bug reload-leaves-modules-stale`
Change Status: `complete`
Owner: Engineering
Status: planned
Last verified: 2026-09-30
Wave: 1zf1y reload-restart-guidance

## Rationale

Across three 1.28.0 test builds, the post-upgrade reload reported `loaded_code_stale` and recommended a host restart while `runner_stale` was false. A field investigation, verified here against the code, showed the warning is accurate:

- `perform_mcp_reload` in `server.py` reloads only the implementation module (`importlib.reload(server_impl)`, which the root shim aliases to `wf_server.server_impl`), evicts `wave_lint_lib`, and clears the script cache. Modules the server imports directly (`indexer`, `chunker`, `setup_readiness`, the `index_*`, `sqlite_*` and `graph_*` stores, `model_bundle`) keep the version the host started with.
- `setup_readiness.capture_loaded_identity` fingerprints the 28 `SOURCE_FILES` once at launch (`server.py` module level), and a reload deliberately keeps that fingerprint ("never recapture updated disk rules as though they were the code with which this process started"). `assess_setup` reports `loaded_code_stale` whenever a fingerprinted file on disk differs.
- `runner_stale` compares only `server.py` and `venv_bootstrap.py`, and cleanup's `setup_status` is computed in a fresh subprocess, so neither can see this.

Two defects follow. Seed 160 tells the operator that "ordinary code-only upgrades retain in-process reload" and that `runner_stale` decides whether a restart is needed, so agents reported the warning as cosmetic while indexing and setup code ran from the previous build. And the fingerprint keeps the launch hash for `wf_server/server_impl.py` and its shim even after a reload re-executes them, so a build that changed only those files would raise a false warning.

Goal: the upgrade guidance tells the truth about what a reload loads, and the staleness check is exact for the files a reload does refresh. Consumer: agents and operators after every upgrade. Success: guidance names `loaded_code_stale` as a restart instruction; a reload that re-executed the implementation module no longer counts it as stale.

## Requirements

1. **Guidance.** Seed 160 and its rendered twin `docs/prompts/upgrade-wavefoundry.prompt.md` (edited by hand in both; the new sentences are identical, the surrounding numbering differs) say, in the operator mental model's reload step, in step 12's `runner_stale` paragraph, and in the post-reload catalog check ("a restart when `runner_stale` or cutover requires one"), that an in-process reload refreshes the MCP tool layer (the implementation module and tool registrations) only; indexing, storage, setup and model code stays at the version the host started with, and when the upgrade changed any of it the reload result reports `loaded_code_stale`, which means restart the host. `runner_stale: false` does not mean everything is loaded. The `wf_upgrade` cleanup `next_step` (`upgrade_handlers._upgrade_next_step`) says the same: reload, and restart the host if setup readiness reports `loaded_code_stale`.
2. **Exact staleness for reloaded files.** Right after `perform_mcp_reload` re-executes the implementation module and `_record_runner_identity` runs, and before the new handler is built (the handler snapshots the identity), the runner updates its own launch identity (the `server.py` global, in place, so the copy the implementation module holds is updated too and the next reload does not restore the stale value) for exactly the file that reload re-executed, `wf_server/server_impl.py` (the root `server_impl.py` shim is only aliased, not re-executed, so it keeps its launch value); every other entry and the launch `errors` keep their values, and an entry whose fresh hash fails is left unchanged. `SOURCE_FILES`, `capture_loaded_identity` and the monitor signature are unchanged. A failed reload records nothing new, and a failure to re-record never fails the reload.
3. **Platforms.** Pure Python in the runner and prompt text; the same on Windows, macOS, Linux and WSL2.
4. **Transition.** The runner (`server.py`) is not reloadable, so Requirement 2 takes effect after the first host restart onto a build that contains it. The guidance applies as soon as the upgrade renders it. The CHANGELOG entry goes under `### Fixed` in the open `## [1.28.0]` section.

## Scope

**Problem statement:** after an upgrade, the reload leaves indexing, storage and setup modules on the previous build while the guidance implies a reload is enough, and the staleness check keeps flagging files the reload did refresh.

**In scope:**

- `server.py` `perform_mcp_reload` (re-record the reloaded entry); `upgrade_handlers._upgrade_next_step` cleanup text; tests.
- Seed 160 mental-model step 3 and step 12; the prompt twin; CHANGELOG.

**Out of scope:**

- Reloading more modules in-process (stateful stores and native runtimes are deliberately not reloaded).
- Making every upgrade demand a restart.
- `runner_stale` semantics.

## Acceptance Criteria

- [x] AC-1: after a successful `perform_mcp_reload`, the runner's loaded identity (and so the implementation module's and the new handler's) has the current disk hash for `wf_server/server_impl.py` and the launch hash for every other source; a disk change to only `wf_server/server_impl.py` no longer yields `loaded_code_stale`, including after a second reload, while a change to a non-reloaded source (for example `indexer.py`) still does.
- [x] AC-2: a reload that fails before the implementation module is re-executed leaves the loaded identity untouched, and an error while re-recording (for example the fresh capture raising) leaves the identity unchanged and still returns a successful reload.
- [x] AC-3: seed 160 and the prompt twin state, in the three places named in Requirement 1, that a reload refreshes the tool layer only, that `loaded_code_stale` after an upgrade means restart the host, and that `runner_stale: false` does not rule that out; the new sentences are identical in both files; the cleanup `next_step` names `loaded_code_stale` and the restart.
- [x] AC-4: the change's own suites and every test it adds pass; the documents this change authors or edits validate; and no failure elsewhere is attributable to this change.

## Tasks

- [x] Re-record the reloaded fingerprint entries in `perform_mcp_reload`.
- [x] Tests for AC-1 and AC-2 through a real reload.
- [x] Seed 160 and prompt twin guidance; CHANGELOG `### Fixed` entry under 1.28.0.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Runner re-record and guidance | implementer | readiness | Small |
| Review | code-reviewer, qa-reviewer, docs-contract-reviewer | implementation | |

## Serialization Points

- `.wavefoundry/framework/scripts/server.py`, `.wavefoundry/framework/scripts/tests/test_server_tools.py`
- `.wavefoundry/framework/seeds/160-upgrade-wavefoundry.prompt.md`, `docs/prompts/upgrade-wavefoundry.prompt.md`

## Affected Architecture Docs

N/A: guidance text and one runner bookkeeping step; the reload scope itself is unchanged.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Removes the false warning for reloaded files without hiding real staleness |
| AC-2 | required | The reload must stay never-fail |
| AC-3 | required | The guidance misled agents on every upgrade |
| AC-4 | required | Standard verification |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-09-30 | Reverification of DEL-1ZF1Y-BYTECODE-IDENTITY (independent, Opus, scratch): RESOLVED. The full-implementation reproduction runs the old bytecode and records the new hash with the repair reverted, and runs the new source with a matching hash with it in place; unchecked-hash pycs are covered by the deletion, checked-hash pycs revalidate, a pycache prefix set before import is covered, and an undeletable cache records nothing. Hardening taken for its two residual gaps (another non-`-B` process rewriting a stale pyc between unlink and reload; the pycache prefix changing after import): after the reload, `_bytecode_cache_absent` requires the reloaded module's own `__spec__.cached` to be absent (nothing writes it under `-B`) or nothing is recorded; test added, its mutant fails | 12 identity tests OK |
| 2026-09-30 | Post-approval review (DEL-1ZF1Y-BYTECODE-IDENTITY): a timestamp `.pyc` stays valid when replacement source has the same size and whole-second mtime, and `-B` does not stop Python reading it, so the reload could execute old bytecode while the before/after source digests matched, marking unexecuted source current. Repaired: `_discard_reloaded_bytecode` removes the implementation module's `__spec__.cached` before the reload so the reload compiles the source it reads, and the entry is recorded only when no bytecode cache remains (unlink failure or a lingering cache records nothing). Windows, macOS, Linux and WSL2 identical (a cache file delete). Tests: a real module with a same-size, same-mtime rewrite shows the stale `.pyc` really is executed on this interpreter; discarding makes the reload run the current source; a cache that cannot be removed is reported; a reload whose executed bytes are unknown records nothing and stays stale. Mutants: gate removed, no unlink, discard after the digest; all caught | 11 identity tests OK |
| 2026-09-30 | Delivery review (independent, Opus): all lanes and seats APPROVE, no build-changing defect; 6 mutants all killed; patching `capture_loaded_identity` confirmed a faithful oracle (`assess_setup` calls the same function and compares with `!=`). Advisories taken: A1, digest `wf_server/server_impl.py` before and after the reload and record only on a match (`_reloaded_source_digests`), so a file rewritten while the reload read it is never marked current (test added; the no-match-check mutant fails it); A2, the guidance sentence now says modules the server already imported keep their launch version so the process can run a mix of old and new code (the tool-path `_load_script` copies do refresh lazily), in both files and the CHANGELOG; A3, a test pins the cleanup next step. Full suite 10178 OK before these | 7 identity tests OK |
| 2026-09-30 | Implemented. `server.py`: `_RELOADED_SOURCES = ("wf_server/server_impl.py",)` and `_refresh_reloaded_source_identity`, called right after `importlib.reload(server_impl)` and before `_record_runner_identity` (same dict object, so order relative to it is irrelevant; it hashes immediately after the reload); updates the runner's `_SETUP_LOADED_IDENTITY["sources"]` in place, skips an entry the fresh capture cannot hash, never raises. If `build_handler` then fails, the identity stays updated, which is correct because the module was re-executed. `upgrade_handlers._upgrade_next_step` cleanup text names `loaded_code_stale` and the restart. Seed 160 and the prompt twin carry one identical new sentence at the mental-model reload step and in step 12 (twin: step 3 and step 6), both catalog-check lines add `loaded_code_stale`, and the twin's step 6 no longer says a restart is "only" needed for the listed cases. Tests (`ReloadedSourceIdentityTests`, real `perform_mcp_reload`, real `assess_setup`, disk changes simulated through the fresh capture): only the re-executed module becomes current (shim keeps its launch value; runner, implementation and handler share the object); an implementation-only change is not stale across two reloads; an `indexer.py` change stays stale; a failing capture leaves the identity and a successful reload; a reload that raises before re-execution records nothing. Mutants: no refresh, shim included, all sources, unguarded, refresh before reload, copy instead of in place; all caught. Gapfill: shell reads, targets known from the investigation | 5 new tests OK |
| 2026-09-30 | Readiness review (independent, fresh context): code-reviewer and red-team BLOCK on one plan gap, adopted: the runner's own `_SETUP_LOADED_IDENTITY` global is what must be updated (in place, after `_record_runner_identity`, before `build_handler` snapshots it), or the next reload restores the stale value; test two consecutive reloads. Also adopted: re-record only `wf_server/server_impl.py` (the shim is aliased, not re-executed); keep launch `errors` and skip an entry whose fresh hash fails; seed line "a restart when `runner_stale` or cutover requires one" and the cleanup `next_step` join the guidance scope; the new sentences are identical in seed and twin while numbering differs. qa, docs-contract and the docs-contract seat APPROVE | Readiness report |
| 2026-09-30 | Planned from a field investigation, verified: `perform_mcp_reload` reloads only `server_impl` (the root shim aliases `wf_server.server_impl`), evicts `wave_lint_lib`, clears `_script_cache`; `SOURCE_FILES` (28 files) feeds both `capture_loaded_identity` and `assessment_signature`; `server.py` restores the launch identity into the reloaded module in `_record_runner_identity`; seed 160 step 12 routes the restart decision through `runner_stale` only | Code reads |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-09-30 | Re-record the reloaded entries after a reload instead of dropping them from `SOURCE_FILES` | `SOURCE_FILES` also drives the monitor signature, and dropping the entries would hide real staleness before any reload | Remove `server_impl` from `SOURCE_FILES` (proposed first, rejected on this reading) |
| 2026-09-30 | Keep the in-process reload and correct the guidance | The staleness check already says precisely when a restart is needed | Always require a host restart after an upgrade |

## Risks

| Risk | Mitigation |
| --- | --- |
| Re-recording masks a partial reload | Only after `importlib.reload` returns, and only the one file that reload executes; a file edited between the reload and the hash would be recorded as current (a tiny window, accepted) |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.

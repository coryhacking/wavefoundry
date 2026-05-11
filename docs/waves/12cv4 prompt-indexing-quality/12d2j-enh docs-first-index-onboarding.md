# Docs-First Index Onboarding and Background Code Index

Change ID: `12d2j-enh docs-first-index-onboarding`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-05-04
Wave: 12cv4 prompt-indexing-quality

## Rationale

Full index builds take ~6 minutes (docs ~2.5 min + code ~3.5 min) due to embedding throughput. This is a friction point for new developer onboarding and for post-upgrade rebuilds on teams where a pack upgrade that bumps `CHUNKER_VERSION` forces a full rebuild for everyone.

The docs index alone unlocks all MCP value (`docs_search`, `seed_get`, all wave lifecycle tools). The code index is additive. Building docs first and code in the background lets developers start working immediately while the code index completes in the background.

## Requirements

1. `setup_index.py` must support a `--background-code` flag that: (a) builds the docs index synchronously (docs model prewarm + docs embedding), then (b) spawns a detached background process that runs code model prewarm and code embedding, returning the foreground process immediately with a message indicating where to watch progress. The code model prewarm must not run in the foreground when `--background-code` is set.
2. `wave_index_health` must read `chunker_versions` from the index `meta.json` for both the project and framework layers, compare against the current `CHUNKER_VERSION` constant, and surface an explicit `chunker_version_mismatch` advisory (distinct from the generic `index_stale` code) when a mismatch is detected on either layer. The advisory must indicate a full rebuild is required.
3. `docs/contributing/build-and-verification.md` must document the two-phase onboarding approach: the default `setup_index.py` invocation (no flags) builds docs only and unblocks MCP immediately; `--background-code` or a subsequent `setup_index.py --include-code` builds the code index as phase 2.
4. `docs/contributing/build-and-verification.md` must document the upgrade rebuild requirement: when a pack upgrade bumps `CHUNKER_VERSION`, a full rebuild is required; note the time cost and the `chunker_version_mismatch` advisory so teams can identify and schedule it.
5. The upgrade prompt (`docs/prompts/upgrade-wavefoundry.prompt.md`) and seed-160 verification checklist must note the `CHUNKER_VERSION` check and recommend running `setup_index.py` (docs-first via default, then code via `--background-code`) during upgrade for immediate MCP availability.

## Scope

**In scope:**

- `.wavefoundry/framework/scripts/setup_index.py` — `--background-code` flag; `prewarm_models` split so code model prewarm is deferred to background child
- `.wavefoundry/framework/scripts/server.py` — `WaveIndex._layer_health` and `docs_health`: read `chunker_versions` from `meta.json` and emit `chunker_version_mismatch` advisory per layer (project + framework)
- `docs/contributing/build-and-verification.md` — two-phase onboarding section, upgrade rebuild and `chunker_version_mismatch` callout
- `docs/prompts/upgrade-wavefoundry.prompt.md` — `CHUNKER_VERSION` note and docs-first guidance
- Seed-160 — verification checklist update (requires `seed_edit_allowed` gate)

**Out of scope:**

- CI artifact download / shared index distribution
- Model size changes
- Code index incremental-only mode
- Automated tests for Windows `--background-code` behavior (requires manual testing on Windows)

## Acceptance Criteria

- **AC-1 (required):** `setup_index.py --background-code` builds the docs index synchronously (docs model prewarm + docs embedding) and returns the foreground process before code model prewarm or code embedding begins. Code model prewarm does not run in the foreground when `--background-code` is set.
- **AC-2 (required):** `wave_index_health` returns a `chunker_version_mismatch` advisory (distinct from `index_stale`) when `meta.json` `chunker_versions` for project or framework layer does not match the current `CHUNKER_VERSION` constant. Advisory fires even when file hashes are current (i.e. after a pack upgrade before any files change).
- **AC-3 (required):** `wave_index_health` `chunker_version_mismatch` advisory covers both the project layer and the framework layer independently.
- **AC-4 (required):** `docs/contributing/build-and-verification.md` contains a two-phase onboarding section: default invocation (no flags) is docs-only and unblocks MCP; `--background-code` or `--include-code` is the phase-2 code index path.
- **AC-5 (required):** `docs/contributing/build-and-verification.md` contains an upgrade rebuild callout: `CHUNKER_VERSION` bumps force a full rebuild; `wave_index_health` will emit `chunker_version_mismatch` advisory; note time cost (~6 min) so teams can schedule it.
- **AC-6 (required):** `docs/prompts/upgrade-wavefoundry.prompt.md` and seed-160 note the `CHUNKER_VERSION` check and instruct agents to run `setup_index.py` (default docs-first, then `--background-code`) during upgrade for immediate MCP availability.
- **AC-7 (nice-to-have):** Background code index process writes progress to `.wavefoundry/index/background-build.log`; `wave_index_health` surfaces a note when a background build is in progress.

## Affected Architecture Docs

- `docs/architecture/search-architecture.md` — index build modes and background process behavior

## Tasks

**Preflight:** seed-160 edit requires `seed_edit_allowed` gate — open before that task, close immediately after.

- [ ] `server.py` `WaveIndex._layer_health` and `docs_health`: read `chunker_versions` from `meta.json`; compare against `chunker.CHUNKER_VERSION`; emit `chunker_version_mismatch` advisory per layer for both project and framework. Add `chunker_versions` dict to `_layer_health` return value so `docs_health` aggregates it before the response function — do not reach back into `self._meta` inside the response function.
- [ ] `setup_index.py`: split `prewarm_models` so docs-model prewarm runs in foreground; add `--background-code` flag that runs docs phase synchronously then spawns a detached background process for code model prewarm + code embedding. Background child re-enters `setup_index.py --include-code` so code model prewarm runs naturally in the child. On macOS/Linux use `close_fds=True` + `start_new_session=True`; on Windows use `creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP` — do NOT mix `start_new_session` with Windows flags (raises on Python <3.11). Windows behavior requires manual testing.
- [ ] Update `docs/contributing/build-and-verification.md` — two-phase onboarding section (default = docs-only; `--background-code` / `--include-code` = phase 2)
- [ ] Update `docs/contributing/build-and-verification.md` — upgrade rebuild callout (`CHUNKER_VERSION` bump forces full rebuild; `chunker_version_mismatch` advisory; ~6 min time cost)
- [ ] Update `docs/prompts/upgrade-wavefoundry.prompt.md` — `CHUNKER_VERSION` note and docs-first onboarding guidance
- [ ] Update seed-160 verification checklist — `CHUNKER_VERSION` check and `setup_index.py` docs-first guidance (requires `seed_edit_allowed` gate)
- [ ] Tests: `--background-code` foreground returns before code model prewarm; `wave_index_health` `chunker_version_mismatch` advisory fires for project and framework layers; advisory fires when file hashes are current but version is mismatched

## AC Priority

(Populated at Prepare wave.)

| AC   | Priority     | Rationale |
| ---- | ------------ | --------- |
| AC-1 | required     | Core goal — docs-first unblocks MCP immediately |
| AC-2 | required     | Version mismatch is silent without this advisory |
| AC-3 | required     | Project and framework layers can mismatch independently |
| AC-4 | required     | Teams need documented onboarding path |
| AC-5 | required     | Upgrade rebuild cost must be visible to teams |
| AC-6 | required     | Upgrade prompt and seed-160 are the primary agent entry points |
| AC-7 | nice-to-have | Use PID file alongside log; check `os.kill(pid, 0)` to distinguish live from crashed process — without this, crashed build permanently reports "in progress" |

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| health advisory | implementer | — | `_layer_health`/`docs_health` reads `chunker_versions` from existing meta.json; emits `chunker_version_mismatch` |
| `--background-code` flag | implementer | — | Can run in parallel with health advisory; prewarm split independent of server.py |
| docs updates | implementer | `--background-code` flag | build-and-verification, upgrade prompt, seed-160 |
| tests | qa-reviewer | all workstreams | AC-1 through AC-3 automated; AC-4/5/6 manual |

## Serialization Points

- Seed-160 edit requires `seed_edit_allowed` gate — do not run concurrently with other seed edits
- Health advisory and `--background-code` flag are independent and can be implemented in parallel after planning is complete

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-05-04 | Change doc created | — |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-05-04 | Detached subprocess for background code build | Simplest approach with no new dependencies; cross-platform via `close_fds` on POSIX and `DETACHED_PROCESS` on Windows | asyncio background task, thread |
| 2026-05-04 | Drop `--docs-only` flag | Current default is already docs-only (no `--include-code`); adding a flag that aliases the default creates confusion and a trivially-passing AC | Keep flag with explicit docs-only behavior |
| 2026-05-04 | Defer code model prewarm to background child | `prewarm_models` runs before `build_index`; if code prewarm runs in foreground, `--background-code` still blocks on model download, defeating the goal | N/A |
| 2026-05-04 | Background child re-enters `setup_index.py --include-code` | Simplest path — child naturally re-runs prewarm for code model then builds; no separate prewarm-only entrypoint needed | Separate `--prewarm-code` flag |
| 2026-05-04 | Add `chunker_versions` to `_layer_health` return value | Keeps layer-separation contract clean; response function must not reach back into `self._meta` | Read `self._meta` in response function |
| 2026-05-04 | AC-7 PID file for in-progress detection | `log.exists()` alone cannot distinguish live process from crashed one; PID file + `os.kill(pid, 0)` is the standard pattern | Sentinel file deleted on clean exit only (no crash detection) |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Background process orphaned if terminal closes | Log file persists; `wave_index_health` detects stale code index on next check |
| `--background-code` not available in MCP `wave_index_build` surface | Document shell path as primary for background builds; MCP `wave_index_build` stays synchronous |
| Windows `DETACHED_PROCESS` behavior untested | Requires manual Windows testing before close; flag the AC-1 Windows case as needing a human tester |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.

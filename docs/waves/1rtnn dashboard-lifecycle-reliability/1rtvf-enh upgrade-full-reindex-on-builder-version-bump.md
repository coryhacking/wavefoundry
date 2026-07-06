# Upgrade forces a full graph rebuild on a builder-version bump (+ MCP-reload guidance)

Change ID: `1rtvf-enh upgrade-full-reindex-on-builder-version-bump`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-07-06
Wave: `1rtnn dashboard-lifecycle-reliability`

## Rationale

Today the upgrade flow (`upgrade_wavefoundry.py` Phase 4) rebuilds the DOCS index in full when the chunker/model version changed, but the GRAPH layer is left to rebuild **lazily on first query** when `GRAPH_BUILDER_VERSION` advances (`upgrade_wavefoundry.py:541-542`). That lazy rebuild runs in whatever process issues the first graph query — and a real trap follows: an **already-running MCP server keeps the OLD extractor in memory**, so on the next graph query it rebuilds the graph DOWN to its stale builder version, silently reverting the new extraction the upgrade just installed. This was observed directly this cycle: after bumping `GRAPH_BUILDER_VERSION` 40→43 (SQL loop-body recovery, schema-DDL faithfulness, Oracle/T-SQL dialect support), a smoke test showed a running server auto-rebuilding `43 → 37`.

Two fixes make an upgrade actually deliver the new graph extraction:
1. **Proactively do a full graph rebuild during the upgrade** (a fresh `setup_index` subprocess = new code) when the graph-builder version advanced, instead of deferring to a possibly-stale first-query rebuild.
2. **Tell the operator to reload/restart the MCP session** after the upgrade, since an already-running server keeps the old extractor until reloaded (`wave_mcp_reload`) or the host restarts.

This is the release-vehicle change for the 1.11.0 cut (version bump + changelog live here).

## Requirements

1. **Phase 4 forces a full graph rebuild when `GRAPH_BUILDER_VERSION` advanced.** The upgrade already reads the pre-extract vs pack graph-builder version (`_read_graph_builder_version_from_pack` / `_snapshot_pre_extract_*`, `upgrade_wavefoundry.py:609-645`); wire that comparison to run a proactive full graph rebuild (`setup_index`/`indexer` with `content='graph'`, from-scratch) in Phase 4 when the version advanced, so the new extractor's output is materialized by a fresh subprocess (new code) rather than left to a lazy first-query rebuild that a stale server can downgrade. When the version is UNCHANGED, keep today's incremental behavior (no gratuitous full rebuild).
2. **Install + upgrade instructions surface the MCP-reload requirement.** The canonical seeds (`.wavefoundry/framework/seeds/` install + upgrade prompts) and the rendered `docs/prompts/{install,upgrade}-wavefoundry.prompt.md` must state that after a builder-version bump an already-running MCP session must be reloaded (`wave_mcp_reload`) or the host restarted, else it keeps the old extractor and downgrades the graph on the next query. Seed-first: update the seeds, then re-render.
3. **VERSION → 1.11.0; CHANGELOG entry for the cycle.** Bump `.wavefoundry/framework/VERSION` from `1.10.1+p9pc` to `1.11.0` (minor — new Oracle/T-SQL dialect support + upgrade-reindex behavior + graph accuracy + dashboard reliability). Add a `## [1.11.0]` CHANGELOG section covering the cycle's shipped waves (SQL graph accuracy `1rvdp`; schema-DDL + Oracle/T-SQL `1rvjs`; dashboard lifecycle reliability `1rtnn`; this upgrade-reindex change). Follow the operator changelog stance (commit-message-style bullets; no build numbers) reconciled with the existing file's format.
4. **Package the framework distribution at release.** Build the `wavefoundry-*.zip` via `build_pack.py` (the "Package Wavefoundry" flow) at wave close so the 1.11.0 distribution reflects the new VERSION + graph extractor. (Zips are transport artifacts — never committed; build + hand off.)

## Scope

**In scope:**

- `upgrade_wavefoundry.py` Phase 4 — the proactive full-graph-rebuild-on-builder-version-advance path (R1).
- Canonical install/upgrade seeds + rendered `docs/prompts/*` — the MCP-reload note (R2).
- `.wavefoundry/framework/VERSION` bump + `CHANGELOG.md` entry (R3).
- The `build_pack.py` package build at close (R4).
- Tests: a deterministic upgrade-Phase-4 test asserting the full-graph-rebuild is invoked when the graph-builder version advanced and NOT when unchanged.

**Out of scope:**

- Changing the graph extractor itself (it's already at v43 from the SQL waves).
- The lazy first-query rebuild machinery (kept as the fallback for the unchanged case + non-upgrade paths).
- Auto-reloading the MCP server from the upgrade script (the server is a separate process the host owns; we document the reload, not force it).
- Semantic (docs/code) rebuild policy (already handled by the chunker-version escalation).

## Acceptance Criteria

- [~] AC-1: **Re-scoped — the proactive full-graph-rebuild-on-version-advance is REDUNDANT; the existing upgrade already does exactly this, and it is already regression-locked.** Code-grounded verification (guru trace, 2026-07-06): upgrade Phase 4b (`phase_index_update`, `upgrade_wavefoundry.py:1397-1409`) already runs `setup_index --graph-only` as a FRESH subprocess; opening the per-file graph state store calls `GraphStateStore.ensure_current()` (`graph_indexer.py:1276-1298`), which resets the store and forces a full-corpus re-extraction whenever the pack's `GRAPH_BUILDER_VERSION` differs from the persisted one — **independent of `--full`**. Because it is a fresh process, it always reads the just-upgraded extractor (immune to the stale-in-process-module trap). This is already proven by existing tests: `test_phase_index_update_runs_graph_only_update` (Phase-4b wiring), plus `test_builder_version_mismatch_forces_full_reextract` / `test_version_mismatch_resets_whole_store` / `test_builder_version_bump_reextracts_full_corpus` (the escalation itself). Adding a second proactive rebuild would be duplicate work that does NOT fix the observed `43 → 37` downgrade — that downgrade comes entirely from the SEPARATE lazy in-process path (`graph_query._ensure_graph_builder_current`) firing in a stale, un-reloaded server, which AC-2's reload requirement is the real fix for. **In place of new code:** corrected the two misleading comments that described the mechanism as "graph rebuilds on first query" (`upgrade_wavefoundry.py` version-transition block + the Phase-4 transition log line) so the code accurately states Phase 4b materializes the graph during the upgrade.
- [x] AC-2: The upgrade seed (`160-upgrade-wavefoundry.prompt.md`) AND the rendered `docs/prompts/upgrade-wavefoundry.prompt.md` state the post-upgrade MCP-reload requirement, with the specific stale-server-downgrade warning (a non-reloaded server keeps the old extractor and re-extracts the graph DOWN on the next query). Seed-first, then hand-synced the curated project-local rendered doc (these prompt docs are not mechanically re-rendered by `wf render-surfaces`). **Install narrowed:** the downgrade trap is upgrade-specific — a fresh install builds the graph from scratch with no pre-existing running server holding a stale extractor — so the install seed was assessed and intentionally not edited (adding the warning there would be inaccurate). Docs-lint clean.
- [x] AC-3: `.wavefoundry/framework/VERSION` reads `1.11.0` (valid semver per `check_version.py`'s regex); a `## [1.11.0]` CHANGELOG section documents the cycle's user-facing changes (SQL graph accuracy + Oracle/T-SQL dialects; dashboard stop/restart-on-zombie; dashboard silent-staleness; the upgrade reload-downgrade guidance). Written commit-message-style without build numbers or wave IDs (per operator changelog stance); the internal `1rqh2` tomllib dead-code cleanup is omitted as non-user-facing. (Note flagged for operator: older entries cite wave IDs — say the word to add them for consistency.)
- [x] AC-4: The framework package builds cleanly at close (`build_pack.py`), producing a `wavefoundry-1.11.0*.zip` reflecting the new VERSION; the zip is NOT committed. Evidence: `build_pack.py --version 1.11.0` (no `--release`, no git side effects) produced `~/.wavefoundry/dist/wavefoundry-1.11.0.paev.zip` and stamped VERSION `1.11.0+paev`; the docs gate passed as build preflight. The zip is a transport artifact (gitignored, never committed).
- [x] AC-5: Standing gates — full framework suite green (4701 tests); `wave_validate` clean; the upgrade path exercised in dry-run (`wf upgrade --dry-run` → "No changes were made / End Dry Run", no phase regression).

## Tasks

- [x] Characterize the exact Phase 4 index-update code + the version-snapshot helpers (`_read_graph_builder_version_from_pack`, `_snapshot_pre_extract_*`) and where to insert the proactive graph rebuild. **Outcome: the rebuild already exists (Phase 4b `--graph-only` + `GraphStateStore.ensure_current()`); no insertion needed.**
- [~] Implement the full-graph-rebuild-on-version-advance in Phase 4; gate strictly on advance. **Not implemented — redundant (see AC-1). Instead corrected the misleading mechanism comments in `upgrade_wavefoundry.py`.**
- [x] Update the upgrade seed with the MCP-reload downgrade warning; hand-sync the curated rendered prompt doc; verify parity. (Install narrowed — trap is upgrade-specific.)
- [x] Bump VERSION to 1.11.0; write the `## [1.11.0]` CHANGELOG entry.
- [~] Deterministic Phase-4 test (advance → full rebuild; equal → incremental). **Superseded — the behavior is already covered by `test_phase_index_update_runs_graph_only_update` + the graph-layer version-bump-reset tests; no new test needed.**
- [x] Build the package at close; full suite; upgrade dry-run. (Package `wavefoundry-1.11.0.paev.zip`; 4701 tests green; `wf upgrade --dry-run` clean.)

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| upgrade-reindex | implementer | — | R1 Phase-4 full-graph-rebuild-on-advance + test. |
| install-upgrade-docs | implementer | — | R2 seeds + re-render + parity (disjoint from the code). |
| release-mechanics | implementer | upgrade-reindex | R3/R4 VERSION + CHANGELOG + package (at close). |

## Serialization Points

- Shares nothing with the dashboard changes (`1rswx`/`1rtju`) in the same wave — different files (`upgrade_wavefoundry.py`/seeds vs `server_impl.py`/`dashboard_server.py`). The VERSION/CHANGELOG/package are release-close steps done once for the whole wave.

## Affected Architecture Docs

`docs/architecture/` — the upgrade/index-lifecycle doc gains the proactive-graph-rebuild-on-version-advance note if such a doc exists; otherwise N/A (confined to the upgrade script + install/upgrade prompt surfaces).

## AC Priority

(Populated at Prepare wave.)

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | The core behavior — an upgrade must materialize the new graph extraction. |
| AC-2 | required | The MCP-reload trap silently reverts the upgrade; operators must know. |
| AC-3 | required | Release identity (VERSION + CHANGELOG). |
| AC-4 | important | Distribution package for the release. |
| AC-5 | required | Standing gates. |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-07-06 | Drafted as the release vehicle for 1.11.0. Rationale grounded in the smoke-test finding (running server auto-rebuilt graph `43 → 37`) + the current lazy-first-query graph rebuild (`upgrade_wavefoundry.py:541-542`). | Smoke-test readout; upgrade Phase 4 audit. |
| 2026-07-06 | **Re-scoped after code-grounded verification (guru trace).** The change doc's premise — that Phase 4 leaves the graph to a lazy first-query rebuild — was STALE: Phase 4b already runs `setup_index --graph-only` as a fresh subprocess and `GraphStateStore.ensure_current()` forces a full-corpus re-extraction on any builder-version mismatch independent of `--full`, and this is already regression-locked by existing tests. R1/AC-1 is therefore redundant (marked `[~]`). The real fix for the observed `43 → 37` downgrade is R2 (mandate MCP reload after a builder-version bump), since the downgrade is caused by the separate lazy in-process path in a stale un-reloaded server — which a proactive rebuild would not prevent. Implemented: corrected the misleading mechanism comments; added the stale-server-downgrade warning to the upgrade seed + rendered prompt; bumped VERSION → 1.11.0; wrote the CHANGELOG. Latent issue discovered (flagged, NOT fixed here to avoid scope creep): `_snapshot_pre_extract_versions` reads a dead `framework-graph-state.json` path (retired framework-graph layer), so the upgrade log's "GRAPH_BUILDER_VERSION X → Y" transition line never fires in production — cosmetic only (does not affect the rebuild); candidate for a small follow-up change. | guru trace (`upgrade_wavefoundry.py:1397-1409`, `graph_indexer.py:1254-1298`, `graph_query.py:161-315`, `setup_index.py:1608-1655`); existing tests `test_phase_index_update_runs_graph_only_update`, `test_builder_version_mismatch_forces_full_reextract`, `test_version_mismatch_resets_whole_store`, `test_builder_version_bump_reextracts_full_corpus`. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-07-06 | Proactive full graph rebuild in Phase 4 (fresh subprocess) rather than fixing the lazy first-query path. | The upgrade subprocess runs the NEW code; the lazy path runs whatever process queries first (a stale server downgrades). A fresh-subprocess full rebuild is deterministic + version-correct. | Force the running server to reload from the upgrade script (rejected — the server is host-owned; document the reload instead). Keep lazy-only (rejected — the observed downgrade trap). |
| 2026-07-06 | **Superseded by the re-scope:** do NOT add a proactive Phase-4 rebuild — verification showed Phase 4b already performs it correctly (fresh subprocess + `ensure_current()` full re-extract on version advance). Deliver R2 (mandatory MCP reload) as the real fix, correct the misleading comments, and lock nothing new (existing tests already cover the behavior). | The proactive rebuild the prior decision proposed already exists in the code and is already tested; adding it again is duplicate work that does not address the actual downgrade cause (a stale in-process extractor). Simplest-solution-first + don't-add-redundant-code. | Ship the redundant rebuild anyway (rejected — duplicate, and it wouldn't stop the stale-server downgrade). Also fix the dead-path `_snapshot_pre_extract_versions` graph read now (deferred — cosmetic log-only issue, scope-creep on a release wave; flagged as a follow-up). |
| 2026-07-06 | Bundle the reindex behavior + release mechanics (VERSION/CHANGELOG/package) in one change, in the combined 1.11.0 release wave. | Operator direction (one combined release wave); the reindex change is the natural release vehicle. | Separate release-mechanics change (rejected — operator chose one wave). |

## Risks

| Risk | Mitigation |
| --- | --- |
| The proactive full graph rebuild adds ~17s to every upgrade even when unneeded. | Gate strictly on the graph-builder version ADVANCING (pack > installed); unchanged version keeps today's incremental path — no gratuitous rebuild. |
| Seed↔rendered drift on the MCP-reload note. | Seed-first: edit the canonical seeds, then re-render platform surfaces; `wave_validate` + a render-parity check at review. |
| CHANGELOG style conflict (operator "no wave IDs" vs the existing file citing waves). | Reconcile at implementation: match the existing file's structure but honor the operator's no-build-number stance; flag the wave-ID question for the operator. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.

# Data and Control Flow

Owner: Engineering
Status: active
Last verified: 2026-07-20

## Primary Control Paths

### Path 1: Lifecycle ID Generation

1. Operator mints an ID via the MCP `wf_create_wave` / `wave_new_<kind>` tools (preferred — they dedupe against on-disk IDs), or, when MCP is unavailable, the CLI `python3 .wavefoundry/framework/scripts/lifecycle_id.py --kind wave --slug <slug>`
2. Script reads `docs/workflow-config.json` for the `lifecycle_id_policy` block (`scheme_version`, `epoch_utc`, `offset`, `hour_offset`) once per mint
3. Encodes the base value per scheme — `v2`: `offset + days_since_epoch × 4096 + blake2s-hash entropy(kind, slug)`, min-width-5 base36, no modulo (values past 36^5 widen gracefully to 6 chars); `v1`/absent: `(days_since_epoch × 288 + bucket_5min) mod 36^5`, 5 base36 chars — then linear-probes past on-disk IDs to the final prefix
4. Prints ID to stdout for operator to use in wave or change documents

The `scheme_version: "v2"` policy is provisioned by code, not agents: fresh installs auto-provision via `wf setup` Step 0 (`setup_wavefoundry._provision_lifecycle_policy_if_absent`, repo-root-anchored, absent-block-only); upgrades run `upgrade_wavefoundry.py` Phase 2c (`materialize_lifecycle_policy`) automatically and re-verify at cleanup via the reconciliation backstop; the standalone `wf upgrade --materialize-lifecycle-policy` command is the recovery fallback. All paths are idempotent — a repo already on v2 is never re-provisioned.

**State read:** `docs/workflow-config.json`
**State written:** none (ID is printed only)
**Domain owner of mutation:** operator (manually inserts ID into docs)

### Path 2: Docs Lint Gate

1. **Agents:** MCP **`wf_validate_docs`** / **`wf_garden_docs`** call the same `docs_lint.py` / `docs_gardener.py` backends as the CLI launchers. **Hooks / CI:** **`wf docs-lint`** (canonical cross-OS dispatcher subcommand) calls `python3 .wavefoundry/framework/scripts/docs_lint.py`. This repository does not rely on repo-root `./docs-lint`.
2. Linter reads `docs/prompts/prompt-surface-manifest.json`, checks `framework_revision` against `.wavefoundry/framework/VERSION`
3. Validates required prompt docs exist, metadata fields are present, wave/journal roots exist
4. Exits 0 on pass or non-zero with actionable error on failure

**State read:** `docs/`, `.wavefoundry/framework/VERSION`
**State written:** none
**Triggered by:** Claude Code post-edit hook (after any `docs/` file edit), manual operator run

### Path 3: Platform Surface Rendering

1. Operator or init process runs `python3 .wavefoundry/framework/scripts/render_platform_surfaces.py`
2. Before cleanup or the first write, the orchestration layer resolves every selected platform write root (`.claude`, `.cursor`, `.github`, `.junie`, `.windsurf`, `.agents` as applicable), unconditional launcher/ignore roots, every registered review carrier, and every enabled native/Guru destination against the resolved repository root. Any pre-existing/static final, parent, or common-ancestor symlink escape in the repository state presented to the command returns nonzero with no platform/agent mutation; fresh `wf setup` therefore stops before `setup_index.py`, and upgrade stops before pruning, the docs gate, and index update. Rendering assumes exclusive control of these path namespaces for the duration of the command; concurrent local filesystem substitution after preflight is outside the supported threat model and is not claimed race-safe
3. After the complete preflight passes, the platform renderer generates enabled platform entrypoints and merged configuration, including `.claude/hooks/*`, `.cursor/hooks/*`, `.github/hooks/*`, `.claude/settings.json`, `.mcp.json`, and `.junie/mcp/mcp.json`
4. It then calls `render_agent_surfaces`; before that function's Guru-availability guard, the agent renderer reconciles only the typed registry's framework-owned executable-review marker regions under `docs/agents/`, `docs/prompts/`, `docs/contributing/`, and explicitly enabled native role destinations under `.claude/agents/` and `.codex/skills/`. Missing required canonical carriers are materialized, absent optional/native roles stay disabled, malformed markers fail safe, and project-authored bytes outside the marker pair remain unchanged
5. The renderer finishes the remaining bin-launcher, ignore/attributes, and cleanup work only after agent-surface reconciliation succeeds

**State read:** `.wavefoundry/framework/scripts/` (templates), registered carrier seeds and enabled target files
**State written:** `.claude/`, `.cursor/`, `.github/hooks/`, `.junie/mcp/mcp.json`, `.mcp.json`, and only framework-marked regions in registered review carriers under `docs/` plus explicitly enabled native role carriers under `.claude/agents/` and `.codex/skills/`
**Must not touch:** `.github/workflows/`, `.git/hooks/`

### Path 4: Framework Packaging

1. Operator runs `python3 .wavefoundry/framework/scripts/build_pack.py --version MAJOR.MINOR.PATCH` (from repo root)
2. Script derives the current lifecycle build suffix and validates manifest `framework_revision` against the packaged revision
3. Stamps `.wavefoundry/framework/VERSION` to `MAJOR.MINOR.PATCH+<build>`
4. Zips the canonical framework **source** tree into `wavefoundry-MAJOR.MINOR.PATCH.<build>.zip` under `~/.wavefoundry/dist/` by default — no framework index is built or shipped (wave 1p4ww removed the separate framework index; framework seeds now fold into the project docs index at setup/upgrade)

**State read:** `.wavefoundry/framework/` tree, output directory listing
**State written:** `.wavefoundry/framework/VERSION`, zip archive in the dist directory (or caller-supplied output dir)
**Note:** zip file is gitignored; do not commit it

### Path 5: Semantic Index Build

1. Operator runs `python3 .wavefoundry/framework/scripts/setup_index.py [--root .] [--full]`, the post-edit hook runs `indexer.py --content docs` directly in the background, or a qualifying MCP mutation requests a detached background docs refresh
2. `setup_index.py` verifies required packages are available in the active Python runtime and prints isolated tool-venv setup commands when missing
3. `setup_index.py` prewarms the embedding model cache, then verifies the same model in offline-only mode so later `docs_search` calls do not need network access
4. Default `setup_index.py` invokes a single `indexer.py --content all` subprocess (after dependency checks and model prewarm) so docs and code share one coordinated synchronous build and one merged `--project-include-prefix` policy; `--background-code` builds docs first and detaches code, while `--background-docs` builds code first and detaches docs
5. `walk_repo()` yields all non-excluded files (respects `.gitignore`, `.aiignore`, binary exclusions)
6. `chunker.py` dispatches each file: Python → AST-based; Markdown → header-split; others → line-window
7. Chunks classified as `code`, `doc`, or `seed` based on kind and path
8. `fastembed` embeds docs/seeds by default using `BAAI/bge-base-en-v1.5`; semantic code embeddings use the same model and run in the foreground by default, and the code pass skips framework internal tests plus non-source/test/generated files unless `--include-tests` or `--include-generated` is passed
9. Project code indexing excludes `.wavefoundry/framework/` by default; repos can explicitly opt in additional excluded paths with `docs/workflow-config.json` -> `indexing.project_include_prefixes` (`docs` and `code` lists, consumed by `setup_index.py` and forwarded to `indexer.py --project-include-prefix`)
10. Project index written to `.wavefoundry/index/` (LanceDB `docs`/`code` tables, graph sidecars, and the `index-state.sqlite` state store — no `meta.json`, wave 1sed7) — this is the single semantic index; framework seeds fold into the project `docs` table at setup/upgrade
11. Subsequent runs are incremental: **each semantic layer detects its own changes** (wave 1sc7c) — the walk hash is compared against the hash that layer last embedded per path (`layer_path_state` in the index-state store), scoped to the layer's eligibility set (its include-prefixes, plus the tests/generated source filter for code — applied identically under every `--content` scope, so corpus membership is deterministic). Changed files are re-chunked with per-layer routing (a dual-output file — e.g. Python, whose docstrings feed the docs table — updates only the stale layer; the other stays queued, never erased); existing LanceDB rows are compared by `chunk_hash` so unchanged chunk vectors are reused and only changed/new chunks re-embed. A path whose freshly-chunked `{id: chunk_hash}` map exactly matches the chunk registry skips its Lance read entirely (wave 1rsh9; kill switch `WAVEFOUNDRY_DISABLE_REGISTRY_INCREMENTAL`). Layer hashes commit AFTER the layer's Lance writes; an EMPTY layer state (fresh store, schema bump, pre-1sc7c repo) reads as all-stale and converges in one rechunk pass — which is also the automatic heal for repos whose code index was frozen by the historical broad-meta stamping. The post-edit hook's automatic reindex runs `--content all` so both layers stay current; the store's build bookkeeping is the walk-state snapshot (stat cache, graph/reap/freshness input), no longer the semantic change signal
12. **Build epoch (wave 1sed7):** every mutating pass — normal/scoped builds, zero-change reap/heal, standalone FTS rebuild, optimize/compact — holds the build lock AND the store's build epoch: a FULL-durable `building` fence commits before the first Lance/FTS mutation, and an attempt-ID compare-and-set completion transaction (the only generation advance) publishes readiness after all mandatory residents reconcile. A proven true no-op opens no epoch and leaves the generation unchanged. Readers fail closed between fence and finalize. Legacy convergence: a pre-1sed7 install (Lance + `meta.json`, no store) reads as all-stale and converges in one re-chunk pass with vector reuse — the JSON is never imported as authority and is removed after the first successful finalize.
13. Index-state store passes (wave 1rsh9, all inside the build lock, all derived-only and fail-safe): (a) SQLite FTS5 lexical tables + chunk registry sync in one store transaction ordered **after** the Lance writes, with an end-of-build chunk-id reconciliation repairing any crash window from Lance; (b) per-path build bookkeeping written to the store — the sole state surface (wave 1sed7: a bookkeeping write failure is a structured build failure, never a silent fallback); (c) freshness/attribution refresh from one batched `git log` pass (zero-change builds skip on the git-HEAD + path-set fingerprint); (d) end-of-build store maintenance — `wal_checkpoint(TRUNCATE)` + `incremental_vacuum` — so the WAL stays bounded under the long-lived MCP server. The reconcile's Lance read is **schema-tolerant** (wave 1sbfk): it projects only columns present in the table's actual schema (required: `id`/`path`/`text`; everything else defaults empty), because production Lance tables carry no `tags` column and Lance raises on absent projections. Zero-change builds run a cheap coverage probe (registry count vs Lance `count_rows` per table) and fall through to the reconcile when the store is cold or materially under-covered, so an idle repo still heals. The store's one-time diagnostics (provisioning, crash-window, reconcile skips, legacy-FTS drops) persist to `.wavefoundry/logs/index-state.log` (bounded, best-effort) in addition to stdout/stderr
14. The secrets scan consults the per-file scan cache (content hash + rules fingerprint) on the index-state store: matching files are skipped, scanned files' rows are upserted in one transaction; any cache problem fails toward a full scan (wave 1rsh9 / 1rsha)

**State read:** entire repository tree (excluding index, binaries, ignores); git history (one batched `git log` per build for freshness)
**State written:** `.wavefoundry/index/` (gitignored), including `index-state.sqlite`
**Triggered by:** manual run, post-edit hook (background subprocess after each file edit), or qualifying MCP mutation tools after successful docs writes

### Path 6: MCP Tool Calls

1. MCP client (Claude Code, Cursor, etc.) sends tool request via stdio to `server.py`
2. **Discovery tool** (`wf_help`): returns a structured catalogue of core verbs, compatibility tools, workflows, recommended chains, and exact next-call usage hints
3. **Search tools** (`docs_search`, `code_search`, `seed_get`): load the single project index from `.wavefoundry/index/` (framework seeds fold into the project `docs` table at setup/upgrade); `docs_search` embeds queries in offline-only mode. **Degradation (wave 1seav):** with a PUBLISHED index (captured complete 1sed7 epoch) but an unavailable semantic model, both search tools serve BM25 results from the FTS5 layer with filters preserved (`search_mode: lexical_fallback`); with no published index, `docs_search` serves the live-filesystem walk (`live_fallback` — its only reachable state) and `code_search` refuses (`index_not_ready`). Every response carries `search_mode` + always-present `fallback_reason` (`null` healthy; `query_failed` = infrastructure failure, typed distinctly from zero hits). `code_ask` freshness (wave 1sbxq) is the cached three-state verdict (per-layer hashes + stat-fast-path + chunker check; TTL + build-generation invalidation) — never a per-query corpus walk
4. **Anchor tool** (`wf_map`): resolves `doc:` / `code:` / `seed:` addresses against the repo root (shared containment rules with future file-navigation tools) and returns trust metadata plus excerpts
5. **Inspection tools** (`wf_current_wave`, `wf_list_waves`, `wf_list_plans`, `wf_get_change`, `wf_get_prompt`): read `docs/waves/`, `docs/plans/`, and `docs/prompts/` via regex parsing and return structured data plus recovery hints (with per-process caching for wave/plan lists and prompt resolution keyed by prompt file mtimes); `wf_current_wave` returns all non-closed waves as `data.waves[]` (ordered active → planned → paused, with per-entry `next_action` — `implement_wave` / `prepare_wave` / `resume_wave`) and runs advisory drift detection against the active wave only. Its context-efficiency view distinguishes the durable SQLite authority, the last published checkpoint, current process focus, producer-scoped general attribution, pending projection, and explicit store/accounting-gap health. `wf_get_change(wave_id=...)` supports bulk mode returning all admitted changes for a wave in one call; `docs_search` responses include a `mode` field (`"semantic"` or `"lexical"`) for fallback transparency
5b. **Session handoff tools** (`wf_get_handoff`, `wf_set_handoff`): read and write `docs/agents/session-handoff.md` for cross-session state continuity; `wf_set_handoff` triggers a background docs-index refresh after successful writes
6. **Code navigation tools — exact layer** (`code_list_files`, `code_read`, `code_keyword`): walk repo files using indexer's ignore/exclusion rules, perform substring search or ranged file reads; all paths validated against repo root to prevent traversal; return deterministic path/line/snippet results
6b. **Code navigation tools — symbol layer** (`code_definition`, `code_references`): Python AST definitions plus tree-sitter-backed Java/C#/JS/TS navigation, with structural/text fallback for other supported non-Python languages and broad keyword fallback when unmatched. `code_references` surfaces a constant's readers in a distinct graph-sourced `reads` bucket (wave 1p4ls), not merged into callers
6c. **Cited-answer retrieval** (`code_ask`): default agent mode returns the semantic `docs`/`code` `citations` PLUS a dedicated **`graph_related` section** (wave 1p4hu): the query's resolved symbol(s) → 1-hop graph neighbors **grouped by relationship** (`callers`/`readers`/`importers`/`related`), with **seed + direction by intent** — "what calls/reads/uses X" expands the named symbol's edges INTO it (callers / readers via the 1p4ls `reads` edge / importers), while "how does X work" expands the named symbol + top semantic hits both directions (its mechanism). Citations stay purely semantic; a structural match that is also a citation is flagged `also_cited` (excerpt dropped, never sent twice). Generic-word seeds, test-file, and module nodes are suppressed. Bounded, relationship-labeled; absent when no graph/symbol resolves. Consumes the existing graph (no builder bump)
7. **Creation tools** (`wf_new_*`): import `lifecycle_id.py` directly, generate change ID, scaffold docs in `docs/plans/`, and return repeat-safe diagnostics when the artifact already exists
8. **Lifecycle mutation tools** (`wf_add_change`, `wf_remove_change`, `wf_prepare_wave`): update the wave record and keep admitted change docs in the wave folder; add-change relocates immediately and inserts the new `Change ID:` block inside the wave's `## Changes` section (tail-append, preserving admission order), remove-change moves active docs back to `docs/plans/`, and prepare validates or repairs placement drift; `wf_prepare_wave` decouples readiness from activation (wave 1p45l): `mode='ready'` records full readiness and leaves the wave `planned` (readied) with no guard, while `mode='create'` runs the single-OPEN guard and flips `planned→active`. The single-OPEN invariant (≤1 wave `active`/`implementing`) is enforced at the activation transitions — `wf_implement_wave`, `wf_reopen_wave`, and `wf_prepare_wave(create)` — via the `another_wave_active` diagnostic (recovery: pause the open wave, or ready the target with `mode='ready'`), not at readiness; successful write paths request a detached background docs-index refresh so non-hook clients do not depend on editor hooks for search freshness
9. **Review and closure tools** (`wf_review_wave`, `wf_review_evidence`, `wf_close_wave`, `wf_pause_wave`): prepare/review/close resolve the fixed sibling `docs/waves/<wave>/events.jsonl`, parse its canonical bytes, validate record relationships through `review_evidence.py`, and compare the adopted prefix against the bounded count/hash proof in `docs/waves/review-evidence-adoptions.json`. The typed evidence tool accepts explicit reviewer judgments, derives only mechanical fields, serializes the complete transaction under the project-global review lock, atomically replaces the event ledger as the authority commit point, advances adoption proof, and regenerates the non-authoritative Markdown current-head projection. When cycle-2 reverification completes after cycle 1, that same identified transaction derives and appends the mandatory convergence checkpoint, including a frozen boundary from the post-reverification current synthesis heads; there is no separate caller-authored checkpoint operation. Failures after event commit report adoption-pending or projection-stale state and converge on identical replay without another append. Its lane-scoped chronology invalidates only approvals affected by a synthesis (with full/council and final-operator scopes preserved). `wf_review_wave` runs lint and validates adoption with `persist_adoption=False`; it requests no background index refresh and performs no adoption or project-file write, while its telemetry event follows the same write-through accounting contract as other eligible lifecycle handlers. Close runs its existing garden/lint gates first. With adoption state retained, a missing/downgraded source declaration, missing authority, proof-ahead state, changed prefix, or unadopted suffix fails closed without invoking Git. Write paths index only `wave.md`; an exact declared ledger or a retained-adoption ledger after declaration tamper is excluded from semantic retrieval, while unrelated/unadopted lifecycle-shaped files remain eligible. `wf_pause_wave` transitions the target wave from `active` to `paused` (idempotent on paused, advisory on other states), so the paused wave frees the single-OPEN slot; duplicate refreshes are throttled with repo-local runtime state
10. **Explicit index maintenance tools** (`index_health`, `index_build`): `index_health` reports stale/missing layer status without touching the hot search path; `index_build` runs `setup_index.py` (project `content=all`, docs+code) or `indexer.py` (project `content=docs|code`) synchronously for deterministic index builds (`mode='update'` vs `mode='rebuild'`), returns structured statistics, and invalidates the in-process loaded index state afterward
11. **Operations tools** (`wf_validate_docs`, `wf_garden_docs`, `wf_sync_surfaces`): invoke `docs_lint.py`, `docs_gardener.py`, `render_platform_surfaces.py` as subprocesses and return structured pass/fail

### Path 6a: Context-Efficiency Capture and Projection

1. Exactly 18 retrieval/navigation tools attach `context_avoided` after producing their complete core response: `code_ask`, `code_search`, `code_lexical`, `docs_search`, `code_keyword`, `code_pattern`, `code_constants`, `code_read`, `code_outline`, `code_definition`, `code_references`, `code_callhierarchy`, `code_impact`, `code_dependencies`, `code_callgraph`, `code_graph_path`, `code_graph_community`, and `code_commit_provenance`.
2. Each event canonically estimates the request and complete response as `ceil(UTF-8 bytes / 4)`. Contained content-returning paths and the documented structural path fields provide source-size credit. Paths and versions become opaque IDs before persistence. SQLite credits a source version once per wave phase across content and structural retrieval; a changed version or new phase may be credited again.
3. Five lifecycle tools record request/response debits whenever their handler is reached. A newly completed create, prepare, implement, full review, or close milestone may also credit exactly one contained project-local shortcut prompt. Dry runs, refusals, lifecycle no-ops, and incomplete reviews retain their debits but receive no prompt credit.
4. `ImplHandler` retains a random producer identity, a lazily acquired crash-released OS lease, and current focus in memory. Every eligible event writes through atomically to `.wavefoundry/logs/context-efficiency.sqlite`; event IDs and phase/source/version uniqueness are enforced across processes. Successful create/prepare transfers its own general rows and atomically claims only persisted peer identities whose lease is provably unheld; live or ambiguous peers remain isolated.
5. The per-stage ledger is closed: content source credit + structural source credit + workflow prompt credit − request debit − response debit. Saved output and avoided tool loops enter only as the conservative residual from a pre-registered, quality-equivalent paired evaluation (at least five completed pairs, assisted quality componentwise no worse, minimum residual across qualifying pairs).
6. Lifecycle projection boundaries re-read durable state under the project-global `wave.md` lock and atomically replace only the marker-owned block. MCP reload and framework upgrade first project every pending wave generation. A generation compare-and-set is the exact covered-row cutoff: an older projection cannot mark newer events published. Close additionally seals that generation, then transactionally replaces payload rows with the cumulative checkpoint floor plus compact event-ID replay tombstones. Reads combine the floor with later raw rows after reopen; a failed post-publication compaction stays pending and retries.
7. Runtime parsing and docs lint share one strict validator for marker uniqueness, schema, and canonical rendering. The human table has only stage, tool calls, and estimated token savings; detailed ledger components remain machine-readable. Legacy `wavefoundry:` markers migrate when touched.
8. The store carries a random instance ID. Loss or replacement freezes active history as `credit_history_unavailable`; a closed validator-valid checkpoint may restore its sealed compact floor because no uncovered mutation is possible. This is the first shipped schema and has no versioned pre-release compatibility layer.
9. A failed transaction durably writes `.wavefoundry/logs/context-efficiency.gap`, suppressing all positive publication. Exceptions before the normal event commit route through the same poison barrier. Only failure to persist both event and poison changes the public call, returning `telemetry_persistence_failed`.
10. Fresh install, package install, public render, and upgrade deliver the implementation, scorer/schema, five missing-only lifecycle prompt baselines from packaged install templates, and `.wavefoundry/logs/` ignore rule without eagerly creating telemetry state or bulk-rewriting historical wave artifacts. Existing project prompt prose remains authoritative and is never replaced by a baseline.
11. Exact-match memory-advisory events use a distinct
    `exploration_credit_event` table in the same SQLite authority. The event key
    is phase/context idempotent and all memories from one source wave share a
    receiving-phase budget. Lifecycle/reload/upgrade projection writes a separate
    `## Estimated Exploration Avoided` block; these counterfactual estimates are
    never added to measured Context Efficiency.

**State read:** current request/response, current/captured file-size and same-version metadata, five project-local lifecycle prompts, strict marker-owned checkpoint, and the SQLite authority when present; health is `absent | healthy | accounting_gap | failed`
**State written:** write-through opaque event/source/evaluation accounting, producer lease files, sealed checkpoint floors and compact replay tombstones, plus separately labeled memory-advisory estimates in `.wavefoundry/logs/`; durable gap poison on failed transactions; marker-owned Context Efficiency and Estimated Exploration Avoided `wave.md` projections at lifecycle/reload/upgrade barriers
**Failure semantics:** ordinary measurement uncertainty undercounts; a durable accounting gap suppresses the headline; only the inability to persist both an event and the poison barrier fails the public tool call

### Path 6b: MCP Resource and Resource-Template Reads

1. MCP client requests a **resource** or **resource template** URI via the MCP resources protocol
2. **Stable resources** (`wavefoundry://overview`, `wavefoundry://prompts`, `wavefoundry://architecture/current-state`, `wavefoundry://wave/current`, `wavefoundry://session-handoff`, `wavefoundry://agents`, `wavefoundry://index/status`, `wavefoundry://graph/status`, `wavefoundry://graph/communities`, `wavefoundry://waves`): read the corresponding file(s) or index artifacts and return raw markdown text; missing files return a structured `# Not Found` markdown message
3. **Resource templates** (`wavefoundry://change/{change_id}`, `wavefoundry://wave/{wave_id}`, `wavefoundry://prompt/{slug}`, `wavefoundry://seed/{slug}`, `wavefoundry://architecture/{slug}`): parameterized reads of the matching doc in `docs/` or `.wavefoundry/framework/seeds/`; matched by name prefix; unknown identifiers return `# Not Found`; ambiguous change/wave IDs return markdown candidate lists instead of silently choosing one match or reporting not-found
4. All resource reads are **strictly read-only** — no writes, no side effects, no background refresh requests. Use tools when a structured response envelope (`diagnostics`, `next_tools`, `usage`) is needed.

**State read:** `docs/`, `.wavefoundry/framework/seeds/`
**State written:** none
**Transport:** stdio (FastMCP MCP resources protocol)

**State read (Path 6):** `.wavefoundry/index/`, `.wavefoundry/logs/context-efficiency.sqlite` when present, `docs/waves/`, `docs/plans/`, `docs/prompts/`, `docs/agents/session-handoff.md`
**State written (Path 6):** process-local context-efficiency focus; write-through `.wavefoundry/logs/context-efficiency.sqlite` accounting and optional gap poison; `docs/plans/`, `docs/waves/` (including project-visible `review-evidence-adoptions.json` and marker-owned context-efficiency projection), `docs/agents/session-handoff.md` (handoff tools), `docs/` metadata (garden tool), and ignored host-local `.wavefoundry/locks/review-evidence-adoptions.lock`
**Transport:** stdio (FastMCP)

### Path 7: Local Dashboard

1. Operator or agent runs `python3 .wavefoundry/framework/scripts/dashboard_server.py --root . [--open]`
2. Script reads `docs/workflow-config.json` `dashboard` settings to determine host, preferred port, fallback range, poll interval, and optional `include_dirs` for file-activity metrics
3. Script resolves the runtime port using a preference-then-fallback strategy across a configured range; reuses the recorded port from `.wavefoundry/locks/dashboard-server.lock` when available and free
4. Script holds `.wavefoundry/locks/dashboard-server.lock` for its lifetime and writes endpoint metadata into that same persistent inode (pid, host, port, url, started_at); launchers serialize the check/spawn/readiness handoff through `.wavefoundry/locks/dashboard-start.lock`
5. Browser loads `dashboard.html` (shell), `dashboard.css` (design system tokens + layout), and `dashboard.js` (React application) from the loopback server; pinned React, React DOM, force-graph, and elkjs load from unpkg CDN URLs embedded in the HTML. No build toolchain required in target repos; graph scripts need network (or cache) on first load.
6. Browser React app polls `/api/dashboard` on a graduated backoff schedule (2 → 5 → 8 → 13 → 21 → 30 s); resets to 2 s when the snapshot hash changes; UI state (selected agent, scroll) stays in browser memory
7. On each poll, `dashboard_lib.collect_dashboard_snapshot` assembles the snapshot from:
   - `docs/waves/` and `docs/plans/` — wave and change records (status, tasks, AC counts, progress logs, participants, review evidence)
   - `docs/agents/` tree including `personas/`, `specialists/`, `journals/` subdirectories — agent/persona metadata and section content for the detail dialog
   - `docs/agents/session-handoff.md` — active wave and recent progress context
   - `docs/prompts/prompt-surface-manifest.json` — public prompt count and framework revision
   - `docs/repo-profile.json` — project archetypes
   - `.wavefoundry/framework/VERSION` — framework version string
   - File-system mtime scan for `files_updated_today` and `files_updated_week` activity metrics

**State read:** `docs/workflow-config.json`, `docs/repo-profile.json`, `docs/waves/`, `docs/plans/`, `docs/prompts/prompt-surface-manifest.json`, `docs/agents/` tree, `.wavefoundry/framework/VERSION`, repo file mtimes
**State written:** `.wavefoundry/locks/dashboard-start.lock`, `.wavefoundry/locks/dashboard-server.lock`
**Transport:** localhost HTTP on loopback only; browser never speaks to MCP or git directly

### Path 8: Hook- and MCP-Owned Incremental Index Refresh

1. Post-edit hooks and explicit MCP lifecycle/index tools request incremental refreshes.
2. `indexer.py` serializes each build with the resource-scoped `.wavefoundry/index/index-build.lock`; the lock remains co-located because deleting/rebuilding the index is its lifecycle boundary.
3. The dashboard only reads bounded build summaries and index row counts. It never starts an indexer or owns index freshness policy.
4. Dashboard snapshots observe external build-state changes on later reads and expose the resulting status without becoming an indexing writer.

**State read:** repository inputs, `.wavefoundry/index/index-state.sqlite`, `.wavefoundry/index/*.lance`
**State written:** `.wavefoundry/index/` by hooks/MCP/indexer only; none by the dashboard
**Transport:** local hook or MCP request; indexer subprocesses use the configured project Python

## State Ownership

| State | Owner | Read By | Written By |
|-------|-------|---------|-----------|
| `docs/workflow-config.json` | Engineering | lifecycle_id.py, docs_lint.py | Wave Framework init/upgrade |
| `docs/prompts/prompt-surface-manifest.json` | Engineering | docs_lint.py | seed-100 / upgrade |
| `.wavefoundry/framework/VERSION` | build_pack.py | docs_lint.py | build_pack.py |
| `.claude/settings.json` | Engineering | Claude Code | render_platform_surfaces.py (merge) |
| `.mcp.json` | Engineering | Claude Code and compatible clients | render_platform_surfaces.py |
| `.junie/mcp/mcp.json` | Engineering | JetBrains Junie / AI Assistant MCP | render_platform_surfaces.py |
| `.wavefoundry/index/` | indexer.py | server.py | indexer.py (incremental) |
| `.wavefoundry/index/index-state.sqlite` | index_state_store.py (wave 1rsh9) | server.py (read-only per-operation connections: FTS fusion, freshness primitive, health probe), scan_secrets.py / run_secrets_scan.py (scan cache) | indexer.py build passes, secrets-scan record, `index_optimize` maintenance |
| `.wavefoundry/locks/dashboard-server.lock` | dashboard_server.py | dashboard lifecycle and upgrade tools | dashboard_server.py; persistent lifetime lock plus in-place process metadata |
| Background refresh state `.wavefoundry/index/background-refresh.json` | MCP server runtime | server.py background refresh helper | MCP mutation/review tools that request detached docs-index refresh |
| Context-efficiency focus | One MCP `ImplHandler` process | that process's lifecycle attribution | lifecycle transitions only; no event totals live solely in memory |
| `.wavefoundry/logs/context-efficiency.sqlite` | MCP operational telemetry | eligible retrieval/lifecycle calls, exact-match memory-advisory estimates, paired-evaluation attachment, lifecycle/reload/upgrade projection, `wf_current_wave`, `wf_audit` | write-through opaque accounting plus separate origin-bounded exploration events; ignored and lazy |
| Wave records `docs/waves/<id>/wave.md` | wave-coordinator | wave inspection tools | wave lifecycle commands |
| Wave event ledger `docs/waves/<id>/events.jsonl` | wave-coordinator | prepare/review/close, dashboard/resources | `wf_create_wave` (empty) and locked `wf_review_evidence`; sole canonical review-event authority |
| Review adoption ledger `docs/waves/review-evidence-adoptions.json` | lifecycle evidence validator | prepare/review/close validation | `review_evidence.py`; bounded `record_count` + canonical-prefix SHA-256 per adopted wave |
| Review adoption lock `.wavefoundry/locks/review-evidence-adoptions.lock` | lifecycle evidence validator | `review_evidence.py` | `review_evidence.py`; host-local, ignored, crash-safe coordination only |
| Change docs `docs/plans/<id>.md` | Engineering | wf_get_change | wf_new_* tools, operator, wf_remove_change |
| Change docs `docs/waves/<wave-id>/<id>.md` | Active wave | wf_get_change, wave lifecycle tools | wf_add_change, wf_prepare_wave |
| Session handoff `docs/agents/session-handoff.md` | Active session | wf_get_handoff, MCP resource `wavefoundry://session-handoff` | wf_set_handoff |

## Runtime Lock Convention

Dedicated project-runtime OS-lock carriers live under `.wavefoundry/locks/`:
the dashboard launch mutex and lifetime/metadata carrier, the review-evidence
adoption lock, and context-efficiency producer leases under `locks/producers/`.
`runtime_lock.py` is the mechanical authority for lazy parent creation, binary
open, POSIX/Windows acquire and release, byte ranges, typed busy versus I/O
outcomes, held probing, handle closure, and in-place JSON metadata. Lock files
persist after release; pathname existence never proves a live holder.

Resource wrappers retain policy. Dashboard code owns check → launch-lock →
recheck → spawn → lifetime-lock ordering; review evidence owns same-thread
re-entrancy; context-efficiency owns producer abandonment and reap; the indexer
owns stale-owner, F_GETLK holder-PID, `ended_at`, and interrupted-build
interpretation. `.wavefoundry/index/index-build.lock` therefore remains
co-located with the nuke-and-rebuild index resource, while
`.wavefoundry/upgrade-in-progress.json` remains a root-level transaction/state
marker rather than an OS-lock carrier. SQLite/Lance locks intrinsic to their
resource files and the framework test-run lock are outside this path convention.

Upgrade performs a one-way cutover with no runtime fallback. Before extraction,
the new pack's upgrade extension records dashboard restart intent, stops the
installed dashboard, proves the old dashboard/adoption/producer carriers are
not held, and deletes those old paths. The extracted runtime recognizes only
`.wavefoundry/locks/`. Cleanup restarts a previously running dashboard on its
prior port before removing the upgrade marker; restart failure retains the
marker and intent for recovery. Every creator provisions its own lock parent,
so fresh installs and upgraded projects do not require eager directory setup.

## Temporal Metadata and Agent Memory Flows (wave 1ro44)

### Historical memory adoption

Install, upgrade, and migration inventory closed local waves without Git or a
semantic index. The canonical `docs/waves` root and each inventoried source
must resolve inside the repository. An escaped parent refuses the inventory
with a typed failure; an unsafe child/source is omitted as unsupported rather
than fingerprinted. `memory-state.sqlite` owns the backfill
run (`inventory_pending → awaiting_validation → ready_for_index →
publishing_index → indexed`),
per-wave fingerprints, random short claim tokens, source identities, counts,
and failures. Mechanical extraction creates candidates only; an agent follows
the evidence/current target and records promote/retain/reject/rewrite through
`memory_validate`. While a lifecycle run awaits validation, candidate and
validation writes advance the memory seqlock but suppress background index
refresh. Upgrade resumes through its existing phase API; setup and migration
resume by rerunning ordinary `wf setup`. The owning lifecycle command performs
the single publication pass under a run-scoped receipt protocol. Immediately
before the index epoch compare-and-set, the index-store finalizer holds the
shared review/memory mutation lock, re-inventories historical sources, syncs
changed fingerprints, proves zero pending work, and records the exact index
attempt, expected generation, and inventory digest as `publishing_index`.
Only then may that attempt become the complete index generation. The lifecycle
command reconciles that receipt to `indexed`; if it crashes after the index CAS
but before the final checkpoint, retry observes the completed generation and
finishes the checkpoint without running the index pass again. A changed source
requeues validation and refuses publication. Receipt-authorized publication is
foreground and synchronous: the owning setup/upgrade command converges both
semantic layers itself, and detached index jobs never inherit the receipt.

An indexed setup/upgrade run remains the durable fingerprint baseline.
Unchanged ordinary setup calls reuse it without reopening validation; a later
new or changed eligible wave reopens only the affected inventory work. There is no
setup-memory-specific MCP tool or public resume flag. Upgrade/install state
mirrors only the run id and gate; there is no JSON/Markdown fallback authority.
Active-run lookup and
creation are one SQLite immediate transaction with one non-indexed run allowed
per entry path, so concurrent setup/upgrade processes share a census. A
new-code `update-index`/`rebuild-index`/cleanup backstop first projects review
state and establishes this run when the retained lock came from an older
in-memory upgrade runner; action-required state is returned before any index
publication. A candidate-bearing run remains `ready_for_index` for the newly
installed runner to publish; the old loaded runner never forwards publication
authority into its older index-child choreography. Before the old runner
reaches its docs gate, the newly extracted
`upgrade_extensions.pre_docs_gate` loads the newly installed upgrader by file
path under a unique module name and repairs the review-status projection. The
upgrade lock records that repair, so a resumed current runner does not repeat
it. This bridge deliberately executes new validation code rather than falling
back to the old in-memory implementation. If that projection or the following
docs gate needs repair, `resume_after_gate` accepts either retained failure
phase and always rebuilds/persists current projection before rerunning lint;
the earlier lock marker is never treated as current authority.
Every index-publication and cleanup entry point checks that retained phase
before doing work: resume-after-memory, update/rebuild-index, and cleanup all
refuse until `resume_after_gate` succeeds and clears the marker.

### Review history and current state

For adopted waves, `events.jsonl` is the complete machine history. A serialized
ledger-first write updates the adoption proof, then regenerates two bounded
Markdown views: Finding Synthesis and `wave:review-status`. The latter contains
one row per canonical signoff key with current state, causal reason, and next
action. Lifecycle gates consume the same typed derivation; human prose outside
the owned marker is not approval authority and is preserved.

### Dashboard document presentation

`/api/doc` returns raw Markdown unchanged. The shared `renderMarkdownish`
presentation path hides HTML control comments outside fences, joins soft
physical lines into Markdown paragraphs/list items, and constrains ordinary
prose to the dialog. Fenced code preserves literal marker text; intrinsically
wide code and tables scroll locally. Wave and change documents have no
type-specific preprocessing. The other prose contexts—framework-process
details, wave-change descriptions, activity update/evidence, and agent
details—intentionally use the same renderer; an exact caller-census regression
forces review when a new consumer is added. The checked-in browser regression
loads the real renderer and stylesheet in exact-size desktop and mobile
iframes, then asserts document/dialog/body scroll bounds, prose and inline-code
containment, hidden comments, and table-local overflow.

**Build-time temporal passes** (optional residents at the semantic-build tail, inside the index-build lock,
after the mandatory residents and before epoch finalize — never fail a build):

1. `update_freshness_from_build` — one batched `git log --name-only` → per-file `last_modified`/`churn_score`
   (`file_freshness`) + windowed commit rows (`file_commits`); zero-change skip on a git-HEAD + path-set
   fingerprint; mtime fallback labeled `source='mtime'`.
2. `update_drift_from_build` — a second batched walk with subjects → landing-commit wave→files attribution
   (`wave_landing`/`wave_change_files`, tolerant subject patterns incl. "Close wave"-as-landing) and per-doc
   drift rows (`doc_drift`: content/verification-stamp anchor, explicit path refs validated against the indexed
   path set, historical class for `docs/waves/`). Skip fingerprint = HEAD + docs path set + verification-stamp
   digest, so an uncommitted stamp still recomputes anchors.

**Zero-git query guarantee:** all git subprocesses run on the build path only; the query path (search tools,
degraded FTS serving, freshness annotation, memory tools) reads SQLite/Lance exclusively — pinned by a test that
patches subprocess and asserts zero spawns.

**Query-time annotation:** search responses attach per-citation `freshness` via one batched read-only
state-store query (`freshness_for_paths`); the drift partition (default-off) and the `wf_audit` drift
worklist consume the same rows. See `search-architecture.md` → Temporal Decay.

**Agent memory flows:** `memory_add` validates (forbidden content refused pre-write) → **fences the memory
seqlock** → writes the record markdown under `docs/agents/memory/` → **finalizes the seqlock** → triggers the
background index refresh (docs embedding + graph per-file delta). `memory_search`/`memory_brief` read
the record files directly (source of truth), decay confidence kind-awarely through `freshness_for_path(since_ts)`,
rank with persisted-betweenness tie-breaks, and degrade gracefully without index/graph layers.
`memory_reconcile` transitions status in place (supersession preserves history; nothing deletes), under the
same fence. Hot read tools and lifecycle tools attach capped advisories from the same record store.

Evidence-derived supply adds a semantic checkpoint without adding another event
store: `memory_supply.draft_candidates` assigns each source a stable identity →
`memory_propose(create)` writes a repo-visible `candidate` with
`Validation: pending` → the active agent follows the evidence and current target
→ `memory_validate` records promote/retain/reject/rewrite plus the action
delta and compact judgment. Rewrites create the corrected record and supersede
the generated candidate under the shared cross-process lock; multi-file crash
atomicity is not claimed and partial failures return explicit recovery.
Proposal scans every status by source identity, so rejected and superseded
history suppress regeneration. `wf_close_wave` blocks on missing or pending
eligible sources; a wave with no eligible source passes with no memory.
Deterministic Python owns extraction/linkage/mutation while the agent owns
semantic usefulness. Contradictions remain surfaced, never auto-resolved.

**`memory-state.sqlite` (advisory-cache invalidation seqlock).** A DEDICATED store in `.wavefoundry/index/`,
owned exclusively by the memory layer — never the canonical `index-state.sqlite`, so a memory write can never
`ensure_current`/reset freshness, FTS, or the build epoch. It holds three keys: a random `epoch` (minted once at
creation; a delete/recreate mints a new one, defeating an ABA where a rebuilt store returns to the same
generation), a monotonic `generation`, and a `memory_writers` table of **writer-owned fence tokens**. **Writers:**
the `memory_*` tools (`memory_fence` registers a unique token BEFORE the filesystem write; `memory_finalize`
removes ONLY that token and advances the generation AFTER) and the indexer (`memory_invalidate` runs early — right
after the changed/removed path sets are known, before any Lance/FTS/freshness/drift work — when a memory record
changed on disk via a hook/raw edit). **Readers** (the hot-path advisory cache) key on
`(epoch, generation, dir_mtime)` and BYPASS caching whenever the store is unreadable or any *live* writer token
exists (`read_memory_state` synthesizes a `dirty` flag from the live-token count, so the reader key contract is
unchanged). **Writer-owned tokens (not a shared flag):** a single shared `dirty` flag let one writer's finalize
clear a concurrent writer's fence (A fence, B fence, A finalize → cleared while B still mutating). Each writer owns
its token and finalize deletes only its own, so B's fence survives A's finalize. A crashed writer's token is
bounded by a TTL (`_MEMORY_WRITER_TTL_SECONDS`, 300s): readers stop bypassing on tokens older than the TTL
(self-heal) and the rw paths lazily reap them. **Failure semantics:** if the fence cannot be registered the tool
REFUSES the mutation; if a finalize fails, the token remains so every process keeps bypassing (correctness over
warm-cache performance) until the next successful mutation or the TTL. The indexer's `memory_invalidate` returns
True ONLY when the generation DURABLY advances (the sole durable invalidation for a raw content edit, which leaves
`dir_mtime` unchanged); on failure it sets a best-effort short-lived fence token and returns False, and the
**build then FAILS before recording file metadata** (`_build_failed_result`) so the edited record's old file_meta
is preserved and the recovered retry re-detects the edit and advances the generation — a "clean" build can never
strand a warm reader on the pre-edit advisory. The store is derived/rebuildable — deleting it only forces cache
reloads.

**Git→non-git drift clearing (typed authority).** `update_drift_from_build` probes git authority through the typed
`_git_authority` (not the empty-string-conflating `_git_head`), returning `git` (work tree with a resolvable HEAD),
`confirmed_non_git`, or `probe_failed`. **Every git subprocess in the derivation chain — the authority probe, the
freshness history walk, the drift history walk, `git cat-file` blob reads, and the gardener classification — routes
through ONE sanitized wrapper (`_run_git`)** that forces a C locale and STRIPS every repository-LOCAL git env var.
The strip-set is the AUTHORITATIVE `git rev-parse --local-env-vars` census (git's own list — discovery/location
`GIT_DIR`/`GIT_WORK_TREE`/`GIT_COMMON_DIR`/…, object-graph *interpretation* `GIT_SHALLOW_FILE`/`GIT_GRAFT_FILE`/
`GIT_REPLACE_REF_BASE`/`GIT_NO_REPLACE_OBJECTS`, and config injection `GIT_CONFIG*`) unioned with a hardcoded
fallback superset, so a newer git that adds a local var is covered without a code change. **Protected GLOBAL/SYSTEM
config is passed through unchanged** — it is deliberately NOT neutralized, because git only accepts `safe.directory`
trust from protected scope, and discarding it would break ordinary shared/differently-owned checkouts (containers,
CI mounts, WSL, shared workspaces) with a "dubious ownership" failure. Instead, the one parser-critical setting —
rename detection — is pinned per-command with `--no-renames` on the freshness and history walks (command flags
outrank all config levels), so path attribution is deterministic regardless of the user's `diff.renames` without the
config sledgehammer. This closes three failure modes: an inherited `GIT_DIR=/missing` no longer makes a valid repo
report "not a git repository" (authority mis-read); an ambient `GIT_DIR` pointing at an unrelated DECOY repo can no
longer redirect the downstream history/freshness/blob reads to the decoy; and an ambient `GIT_SHALLOW_FILE`/
`GIT_GRAFT_FILE` can no longer silently truncate or reshape the derived history. A genuinely-untrusted repo (real
"dubious ownership") degrades gracefully — `rev-parse` fails → `probe_failed` → drift preserved / mtime freshness
fallback. A structural AST census test asserts no process-spawn (`subprocess.run`/`Popen`/aliases/variable-built
commands) exists outside `_run_git`. A `confirmed_non_git` result requires BOTH the POSITIVE "`not a git repository`"
fatal (matched under a forced C locale) AND the genuine ABSENCE of any `.git` marker at the root or an ancestor
(`_git_marker_present`): git prints the same message for an empty/corrupt `.git/`, a broken `.git` worktree pointer,
or an unreadable marker, and those are PRESENT-BUT-INVALID repos — not non-git trees — so a present marker forces
`probe_failed`. **Every other completed-but-failing invocation — dubious ownership, permission denied, bad config,
unexpected output — is also `probe_failed`, NOT confirmed non-git**, so none can authorize a destructive clear. A
FRESH non-git project has nothing to clear, but a git-built index copied into — or a repo that dropped its git
metadata under — a now-non-git root would otherwise keep serving stale git-derived `drifted: true` rows. So on a
CONFIRMED non-git transition the git-derived wave attribution + doc-drift rows + drift fingerprint are
transactionally CLEARED (`IndexStateStore.clear_attribution_and_drift`, idempotent). A `probe_failed` result
PRESERVES last-good drift and never clears (a transient timeout, dubious-ownership error, or corrupt `.git` must not
destructively wipe valid drift); an unborn-HEAD git repo is still git and is not cleared. The no-op build path
reconciles the same transition (`reconcile_non_git_drift`, gated on the cheap `has_drift_state` so a normal git repo
pays no git probe on a zero-change build). **A failed clear on a confirmed transition returns a structured FAILED
build (not `up_to_date` / not a finalized epoch) on BOTH paths** — the no-op path fails before the up_to_date
return, and the build-tail path fails on `drift_clear_failed` before finalizing the epoch — so the stale row is
never served behind a successful build, and the retry re-attempts the clear. Ordinary drift *computation* failures
(`drift_detect_failed`, `git_probe_failed`) stay OPTIONAL (the drift table is a ranking-decay resident, not a
readiness gate); only a `drift_clear_failed` on a confirmed transition escalates to a build failure.

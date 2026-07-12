# Content-Scoped Builds Stamp Broad Meta Hashes, Silently Freezing the Code Semantic Index (+ Hook Docs-Default, + all/code Corpus Divergence)

Change ID: `1sek8-bug content-scoped-builds-poison-code-index-freshness`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-07-11
Wave: TBD

## Rationale

Reproduced live on this repo during 1.12.0 release prep (2026-07-11), while verifying `code_lexical` (1seiz): a full day of code edits to `server_impl.py`/`indexer.py`/`index_state_store.py` was **absent from the code semantic index and FTS**, `wave_index_health` read healthy, and — the sharp part — a fresh `wave_index_build(content='code', mode='update')` said **"index is up to date"** while demonstrably missing all of it. The documented recovery for stale code navigation is a no-op on a poisoned repo.

Three interacting defects, all verified in source and live:

1. **Broad meta stamping erases the other content type's change signal (the core defect).** `build_index` intentionally hashes the BROAD walk into `current_file_meta` every run ("meta.json captures every walkable file regardless of which content type this run is building" — `indexer.py` ~3432) and scopes only the Lance writes. A docs-content build after a code edit therefore records the code file's NEW hash without embedding it; the next code-content build compares hashes, sees no change, and skips the file **forever** (no later incremental can recover — only a full rebuild or `--rechunk`). The 1p399 drift detector cannot catch it: it only detects zero-row paths, and stale-content rows exist (the known-deferred "stale-content Lance drift" follow-up from wave 1rsh9 — this is that gap, weaponized).
2. **The post-edit hook always runs the poisoning build.** The rendered hook spawns `indexer.py --root <root>` bare (`post-edit.py` ~279) and `--content` **defaults to `docs`** — so on every hook-enabled repo, every code edit is followed by a docs-only build that stamps the code file's fresh hash. Consequence: **incremental code indexing effectively never works on hook-enabled repos** — the code index stays frozen at the last full build (setup/upgrade), which matches long-standing field "code_search feels stale" reports and the 1rsh9-era observation that stale-content Lance rows exist live.
3. **`content=all` and `content=code` produce different corpora.** `_filter_code_files` (tests/generated exclusion) applies ONLY when `build_code and not build_docs` (`indexer.py` ~3425), so `content=all` (setup's path) chunks test files into the code table while `content=code` excludes them — this repo's code table was 14,683 rows WITH framework-test chunks (contradicting the documented "framework internals under scripts/tests/ are never included") until tonight's first-ever `content=code` build reaped ~10k test-file rows down to 4,982. Corpus membership must not depend on which content flag last ran.

Live evidence trail (this repo, 2026-07-11): `code_lexical_response("code_lexical_response")` → 0 hits with hash-current meta; Lance scan → 0 chunks containing any of today's symbols; `--content code` → "up to date"; `--content code --rechunk` → 1,341 files re-chunked, new symbols searchable, test-file rows reaped.

4. **(Design-critical, verified 2026-07-12) Code files are DUAL-OUTPUT.** `chunk_python` emits `kind="doc"` chunks for module/class docstrings (`chunker.py:509/574/1901`) and `_chunks_for_file` (`indexer.py:3128`) routes them to the **docs** table — so a changed `.py` writes into BOTH tables under `content=all`, a code-only build silently drops its doc chunks, and a docs-only build (whose walk excludes `.py`) processes none of it. Only `content=all` keeps both tables coherent for code files. Consequences: (a) `.py` docstring chunks in the docs table go stale under BOTH scoped build types, not just the code side; (b) a per-file meta-revert fix is coarse for dual-output files (the side that DID process them re-processes redundantly next build); (c) per-layer "last-embedded hash" tracking, or making the automatic path always `content=all`, are the coherent design shapes.

## Requirements

(Shapes below are the starting proposal; the admitted wave must run its own design pass — the eligibility semantics interact.)

1. **Meta stamping is content-scoped:** a changed file that this build did not FULLY process for every table it feeds — but that a `content="all"` build would — must not read as current to the next in-scope build. Design pass picks the mechanism from (at least) three candidates: **(A) per-file meta-revert** (changed-but-not-fully-processed files keep the OLD meta entry; simple, but redundant re-work for dual-output files and coarse per-file granularity); **(B) per-layer last-embedded hashes in the index-state store** (each table tracks the hash it last embedded per path; change detection per content type compares walk hash vs its own layer's hash — architecturally clean on the substrate that now exists, no redundant work, makes scoping coherent; `meta.json` stays the walk-state snapshot for its existing readers); **(C) automatic builds are always `content=all`** (scoping restricted to explicit operator/CI calls, with A or B still needed to de-footgun the explicit scoped path — or scoped incrementals deprecated outright). Files no content type would ever chunk keep the current broad stamping (no perpetual-churn regression for graph/reap consumers).
2. **The hook path stops poisoning:** the rendered post-edit hook spawn covers code content (e.g. `--content all`), so a code edit's own hook build indexes it — incremental code freshness works on hook-enabled repos. Evaluate the hook-latency cost (background, detached, incremental — expected seconds on GPU for changed chunks only).
3. **One corpus definition:** `content=all` and `content=code` agree on code-table membership (tests/generated policy applied identically); a migration note covers repos whose tables currently include test chunks (first post-fix build reaps them — loud, logged).
4. **Recovery guidance corrected:** `AGENTS.md`/`build-and-verification.md` "code navigation feels stale" rows must not recommend the no-op (`content=code` update on a poisoned repo); until the fix ships, the working recovery is `--rechunk` or a full rebuild — and after it ships, the ordinary update works.
5. **(Operator-directed addition, 2026-07-12) From-scratch FTS rebuild surface:** `wave_index_build(content="fts")` rebuilds the derived lexical layer (FTS5 tables + chunk registry) from scratch off the authoritative Lance tables — embedding-free, in-process (seconds), lock-guarded; `mode` ignored. The `chunk_index_undercovered` diagnostics (health + `code_lexical`) point at it as the targeted recovery.
6. **Regression fixtures:** (a) code edit → docs-only build → code build MUST index the change (the poison scenario); (b) hook-spawn argument pin; (c) all-vs-code corpus-membership parity; (d) the health/coverage surfaces stay honest through the transition.

## Scope

**Problem statement:** content-scoped incremental builds destroy the change signal for the other content type, the automatic hook path does this on every edit, and corpus membership varies by content flag — collectively freezing code retrieval freshness fleet-wide while every health surface reads ok.

**In scope:** `indexer.py` meta/change-detection semantics; the rendered hook spawn (platform surfaces + seeds carrying it); corpus-filter unification; docs/decision-table corrections; fixtures.

**Out of scope:** chunker content changes; store schema; retrieval ranking.

## Acceptance Criteria

- [x] AC-1: The poison scenario is fixture-pinned and fixed — a code edit followed by a docs-only build is still indexed by the next code/all build. *(`test_poison_scenario_docs_build_cannot_freeze_code_layer` — the exact field sequence; plus dual-output coherence and scoped-build queueing fixtures.)*
- [x] AC-2: The rendered post-edit hook's spawn covers code content, with the argument pinned by test. *(Template + Stop-flush spawns `--content all`; all rendered hooks re-rendered; pins in `test_hook_spawns_all_content_reindex` + the render-surface test.)*
- [x] AC-3: `content=all` and `content=code` produce the same code-table membership under identical include flags. *(`test_corpus_membership_identical_across_content_scopes` — tests excluded under both, extensionless code names kept, `--include-tests` parity; migration reap fixture proves loud, store-logged cleanup + re-widening.)*
- [x] AC-4: Stale-recovery documentation reflects reality (no recommended no-ops). *(`build-and-verification.md` decision table updated to post-fix behavior; `data-and-control-flow.md` step 11 + `chunking-and-indexing-pipeline.md` Stage 2 document the per-layer scheme, dual-output union, and the heal.)*
- [x] AC-6: `wave_index_build(content="fts")` rebuilds the derived lexical layer from scratch off Lance — lock-guarded, embedding-free, with the under-coverage diagnostics pointing at it. *(`FtsRebuildContentTests` ×3 + store-side `test_force_rebuild_ignores_in_sync_state`; live probe: emptied `fts_code` rebuilt to 4,687 rows + docs 18,215 in seconds, operator-requested messaging store-logged.)*
- [x] AC-5: Full suite bytecode-free + docs validation + a live end-to-end verification on this repo (edit → hook-shaped build sequence → symbol searchable). *(Suite 4,863 OK zero failures; `wave_validate` clean; live: v5 store migration heal in 38s (1,330 files, vector reuse), 1,200 dual-output docstring rows restored, zero-change rerun 1.5s fast exit, brand-new symbols FTS-searchable with no manual rechunk. The live pass caught and fixed two design flaws pre-ship — see Progress Log.)*

## Tasks

- [x] Design pass: census + trigger characterization + heal verification + hook-cost measurement complete; mechanism decided (B+C hybrid, see Decision Log 2026-07-12).
- [x] Implement per-layer change detection (`layer_path_state`, store schema v5) + fixtures.
- [x] Hook spawn change (`--content all`) + surface re-render + pin.
- [x] Corpus-filter unification (incl. extensionless code names) + migration reap with store-log audit.
- [x] Docs corrections (decision table, data-and-control-flow); live verification on this repo; suite (final run pending at doc-update time).
- [x] Operator-directed addition: `content="fts"` from-scratch derived-layer rebuild (`rebuild_derived_chunk_state` + reconcile `force` + server branch + diagnostics repointed + docs + tests).

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| design | planner | — | Eligibility semantics + hook cost |
| meta-fix | implementer | design | The core defect |
| hook-and-corpus | implementer | design | Spawn + filter unification |
| tests-docs | qa-reviewer | all | Fixtures + docs + live proof |


## Serialization Points

- The design pass gates implementation — the three defects interact (fixing the hook alone hides the meta defect; fixing meta alone leaves hook builds docs-only).

## Affected Architecture Docs

- `docs/architecture/data-and-control-flow.md` (build path steps), `docs/architecture/chunking-and-indexing-pipeline.md` (corpus membership), `docs/contributing/build-and-verification.md` (decision table).

## AC Priority

(Populated at Prepare wave.)


| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The core silent-staleness defect. |
| AC-2 | required | The automatic poisoning vector. |
| AC-3 | required | Corpus determinism. |
| AC-4 | required | The documented recovery is currently a no-op. |
| AC-5 | required | Standard gate + live proof. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-07-11 | Drafted from the live reproduction during 1.12.0 release prep: a day of code edits invisible to code retrieval with hash-current meta; `content=code` update a confirmed no-op; recovery via `--rechunk` (which also exposed the all/code corpus divergence by reaping ~10k test-file rows). Root causes verified in source: broad meta stamping (`indexer.py` ~3432 comment + `_detect_changes` on `files_for_meta`), bare hook spawn (`post-edit.py` ~279) with `--content` defaulting to `docs` (`indexer.py` ~4122), `_filter_code_files` gated on `build_code and not build_docs` (~3425). This is the 1rsh9 known-deferred "stale-content Lance drift detection" follow-up, now with mechanism and blast radius established. | Live probes (FTS/Lance token scans, hash comparison, up-to-date no-op, rechunk recovery); source line evidence; 1rsh9 wave learnings. |
| 2026-07-12 | DESIGN PASS COMPLETE (the gate). (1) **Census:** dual-output is UNIVERSAL — every code-language chunker emits `kind="doc"` comment/docstring chunks routed to the docs table (chunk_python, _chunk_java_like, chunk_csharp, chunk_js_ts, chunk_c_cpp, chunk_go, chunk_rust, chunk_shell, SQL, chunk_swift, chunk_objc, chunk_xml, chunk_html, design-JSON, chunk_jupyter — 33 emission sites mapped). Option A (per-file meta-revert) is thereby eliminated: it would double-process essentially every code edit forever. (2) **Poison trigger precisely characterized (bench-repo reproduction):** a docs-content build with NO docs changes takes the zero-change early return and never rewrites meta — no poison; the poison fires when a docs change rides with the code change (docs build runs the full path, broad-stamps the code file's fresh hash, `content=code` then reports "up to date" and the code chunks are lost). Interleaved docs+code edits are the universal agent-session pattern, which also explains inconsistent field perception ("sometimes stale"). The graph phase consumes the code file in the same docs build (extraction ran on it), masking the loss further. (3) **Heal-in-place verified:** the normal upgrade's `phase_index_update` runs `setup_index.py` WITHOUT `--full` — poisoned meta SURVIVES incremental upgrades; only chunker-bump (full-rebuild) upgrades heal today. (4) **Hook-cost measured (bench clone, GPU box):** `content=all` zero-change 1.2s; docs-edit 4.3s; code-edit ~12.4s (embedder load dominated) — vs current docs-only hook 1.2–4.3s; acceptable for a detached, turn-coalesced background build. | Chunker emission map (33 sites); bench-repo builds (steps 1–6 + interleaved-edit reproduction); `upgrade_wavefoundry.py:1444-1462` (no `--full`); timing runs. |
| 2026-07-12 | IMPLEMENTED (mechanism B+C). (B) `layer_path_state (layer, path, hash)` resident table, store schema bump 4→5; `layer_hashes`/`update_layer_hashes`/`replace_layer_hashes`; per-layer change detection in `build_index` (walk hash vs layer's own last-embedded hash, scoped to per-layer eligibility; drifted paths always re-process; rechunk = layer-wide); chunk-loop routes each kind only to its stale layer; per-table writers receive THEIR layer's stale set (+removals) with a completion collector; layer hashes commit AFTER the layer's Lance writes (failed write → layer stays stale → retry); full rebuilds replace layer state wholesale; reap gains per-table eligibility + layer-state cleanup + persisted-log audit. (C) hook + Stop-flush spawns go `--content all` (template + all rendered hooks re-rendered, pin updated). Corpus unification: `_filter_code_files` applies under every scope, extended with `CODE_EXTENSIONLESS_SOURCE_NAMES` (Makefile/Dockerfile/… — chunker-synced by test) so content=all's undocumented extras don't silently vanish; drift candidacy + `chunks_emitted` counts are eligibility-aware (a claimed-but-ineligible contribution would drift-flag forever). 9 new fixtures green first run (poison pin, dual-output coherence, scoped-build queueing, corpus parity, empty-state heal, fast-exit, migration reap + re-widening, hook pin, name-sync). | `indexer.py`, `index_state_store.py`, `render_platform_surfaces.py`, hooks; `ContentScopeFreshnessTests` (9); suite. |
| 2026-07-12 | LIVE VERIFICATION caught two design flaws pre-ship (the reason AC-5 runs on real data): (1) **dual-output eligibility** — docs-table membership must be the UNION of docs prefixes + code corpus; prefix-only eligibility let the first live reap delete 3,126 legitimate `.py` docstring rows (self-healing but wrong; every code chunker emits doc-kind chunks). Fixed: `docs_eligible_rel |= code_eligible_rel`. (2) **v4-store read** — `layer_hashes` on a pre-1sek8 store returned None (missing table) → legacy fallback deferred the heal one build. Fixed: unreadable/absent layer state reads as EMPTY → the migration heal runs on the FIRST post-upgrade build. Post-fix live run on this repo: full heal in 38s (1,330 files, both layers, vector reuse), 1,200 docstring rows restored, zero-change rerun "up to date" in 1.5s, brand-new symbols (`_cleanup_layer_state_for_reaped`) FTS-searchable with no manual rechunk. | Live build transcripts (reap 3,126 → union fix → heal 38s → fast exit 1.5s); store probes (layer counts 1,339/119; FTS hits). |
| 2026-07-12 | Third-order interaction caught by the suite (1rmaf drift-eligibility pins): union docs eligibility made docs-only builds drift-flag code files whose code rows they cannot write (and emitted-count claims for unwritten layers would have churned the detector). Resolution: change detection + reap keep the UNION (dual-output correctness); drift candidacy + emitted-count claims stay PRE-union, scoped to the layers a build actually writes — dual-output docstring drift stays undetectable, exactly as pre-1sek8 (documented limitation, not a regression). Full-rebuild claims likewise zero unwritten layers. test_indexer 216 OK. | `docs_prefix_eligible_rel` split; drift candidacy + count edits; `LanceDriftEligibilityBuildTests` green again. |
| 2026-07-12 | Operator-directed addition: `wave_index_build(content="fts")` — from-scratch rebuild of the derived lexical layer. Store: `reconcile_chunk_index(force=True)` skips the in-sync early-out with calm operator-requested messaging (store-logged, never the crash-window warning). Indexer: `rebuild_derived_chunk_state` (schema-tolerant fetch, sync counts recorded, cold cleared); `_sync_chunk_derived_state` now returns per-table stats. Server: lock-guarded in-process branch (busy → `already_running`), response carries per-table `rows_written`; both `chunk_index_undercovered` diagnostics repointed to `content='fts'` as the targeted recovery. Docs: tool docstring content values, spec row, build-and-verification decision table + accepts-line. Live probe: emptied `fts_code` rebuilt 4,687 rows (docs 18,215) in seconds. 4 new tests green. | `server_impl.py` fts branch; `indexer.py`/`index_state_store.py`; `FtsRebuildContentTests`, `test_force_rebuild_ignores_in_sync_state`; live probe output. |
| 2026-07-12 | Operator exercised the new surface through the live MCP (`wave_mcp_reload` → `wave_index_build(content="fts")`): docs 18,227 + code 4,690 rows rebuilt from scratch; the persisted store log answered the "how long?" question (~3s wall) — which exposed that the response lacked a duration field. Added `duration_ms` to the fts response (live re-verified: 3,417ms); tests green. | MCP call transcripts; `.wavefoundry/logs/index-state.log` timestamps; `FtsRebuildContentTests` 3 OK. |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-07-11 | NOT folded into 1.12.0 (recommended fast-follow instead); operator decides. | The fix requires design decisions (eligibility semantics, hook cost, corpus migration) unsuited to a same-night patch into a twice-field-tested RC; the defect is long-standing (pre-dates 1.12 by many releases), not a 1.12 regression; and 1.12's upgrade path runs full/`all` builds, which are immune. | **Fold the one-line hook fix (`--content all`) into 1.12:** viable and cheap, and it removes the main poisoning vector — but without the meta fix, already-poisoned repos still need a rechunk, and shipping half the fix risks "fixed it" confusion; kept as an operator option. |
| 2026-07-12 | **Mechanism = B+C hybrid.** (B) Per-layer last-embedded hash state moves into the index-state store (new resident table, e.g. `layer_path_state(layer, path, hash)`; `STATE_STORE_SCHEMA_VERSION` bump to "5" — a shape change per the store's rule; the version-gated drop-and-rebuild is safe because everything resident is derived and the 1sbfj reconcile reprovisions FTS/registry from Lance, a now-proven path). Each semantic layer's change detection compares the walk hash against ITS OWN last-embedded hash, so any build scope is correct by construction; `meta.json` remains the exported walk-state snapshot (reader contract untouched). **The migration IS the heal:** absent layer state reads as "everything stale for this layer" → one rechunk pass with chunk-hash vector reuse (the exact shape of the manual `--rechunk` recovery) → every poisoned field repo converges on its first post-upgrade build, incremental upgrades included. (C) The rendered post-edit hook spawns `--content all`, keeping both semantic layers + dual-output files current on the automatic path. | A eliminated by the dual-output census (universal double-processing). B alone leaves the hook docs-only (dual-output docs chunks and code freshness then depend on operator builds). C alone leaves explicit scoped builds latently wrong and heals nothing. | **A (meta-revert):** rejected — census. **C-only:** rejected — latent defect + no heal. **Full deprecation of scoped builds:** rejected — legitimate CI/operator uses; under B they become correct anyway. |
| 2026-07-12 | **Corpus unification direction: tests/generated excluded under ALL content scopes** (apply `_filter_code_files` whenever `build_code`, not only when `build_code and not build_docs`). This matches the documented contract ("code indexing defaults to source files only") and `content=code` behavior; `content=all` loses its undocumented test-inclusion. Field repos whose code tables carry test chunks get a loud, store-logged reap on first post-fix build. `--include-tests`/`--include-generated` keep working identically across scopes. | The documented contract is the target state; determinism requires one membership rule; the reap machinery + persisted log (1sbfj) already exist. | **Unify toward inclusion (tests in both):** rejected — contradicts documented default and bloats field corpora; test retrieval was never the semantic index's contract (graph layer handles test paths separately). |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Hook builds get slower (code embedding per edit) | Detached background, incremental (changed chunks only); measure in the design pass. |
| Corpus unification reaps test chunks on repos that (unknowingly) had them | Loud reap logging + migration note; the documented contract already says tests are excluded. |
| Meta-scoping regression re-processes files every build | The semantic-ineligible carve-out; fixture-pinned. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.

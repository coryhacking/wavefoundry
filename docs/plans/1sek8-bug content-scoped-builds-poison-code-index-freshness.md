# Content-Scoped Builds Stamp Broad Meta Hashes, Silently Freezing the Code Semantic Index (+ Hook Docs-Default, + all/code Corpus Divergence)

Change ID: `1sek8-bug content-scoped-builds-poison-code-index-freshness`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-07-11
Wave: TBD

## Rationale

Reproduced live on this repo during 1.12.0 release prep (2026-07-11), while verifying `code_lexical` (1seiz): a full day of code edits to `server_impl.py`/`indexer.py`/`index_state_store.py` was **absent from the code semantic index and FTS**, `wave_index_health` read healthy, and — the sharp part — a fresh `wave_index_build(content='code', mode='update')` said **"index is up to date"** while demonstrably missing all of it. The documented recovery for stale code navigation is a no-op on a poisoned repo.

Three interacting defects, all verified in source and live:

1. **Broad meta stamping erases the other content type's change signal (the core defect).** `build_index` intentionally hashes the BROAD walk into `current_file_meta` every run ("meta.json captures every walkable file regardless of which content type this run is building" — `indexer.py` ~3432) and scopes only the Lance writes. A docs-content build after a code edit therefore records the code file's NEW hash without embedding it; the next code-content build compares hashes, sees no change, and skips the file **forever** (no later incremental can recover — only a full rebuild or `--rechunk`). The 1p399 drift detector cannot catch it: it only detects zero-row paths, and stale-content rows exist (the known-deferred "stale-content Lance drift" follow-up from wave 1rsh9 — this is that gap, weaponized).
2. **The post-edit hook always runs the poisoning build.** The rendered hook spawns `indexer.py --root <root>` bare (`post-edit.py` ~279) and `--content` **defaults to `docs`** — so on every hook-enabled repo, every code edit is followed by a docs-only build that stamps the code file's fresh hash. Consequence: **incremental code indexing effectively never works on hook-enabled repos** — the code index stays frozen at the last full build (setup/upgrade), which matches long-standing field "code_search feels stale" reports and the 1rsh9-era observation that stale-content Lance rows exist live.
3. **`content=all` and `content=code` produce different corpora.** `_filter_code_files` (tests/generated exclusion) applies ONLY when `build_code and not build_docs` (`indexer.py` ~3425), so `content=all` (setup's path) chunks test files into the code table while `content=code` excludes them — this repo's code table was 14,683 rows WITH framework-test chunks (contradicting the documented "framework internals under scripts/tests/ are never included") until tonight's first-ever `content=code` build reaped ~10k test-file rows down to 4,982. Corpus membership must not depend on which content flag last ran.

Live evidence trail (this repo, 2026-07-11): `code_lexical_response("code_lexical_response")` → 0 hits with hash-current meta; Lance scan → 0 chunks containing any of today's symbols; `--content code` → "up to date"; `--content code --rechunk` → 1,341 files re-chunked, new symbols searchable, test-file rows reaped.

## Requirements

(Shapes below are the starting proposal; the admitted wave must run its own design pass — the eligibility semantics interact.)

1. **Meta stamping is content-scoped:** a changed file that this build did not chunk — but that a `content="all"` build WOULD chunk — keeps its OLD meta entry (or stays absent if new), so the next in-scope build still detects the change. Files no content type would ever chunk (semantic-ineligible) keep the current broad stamping (no perpetual-churn regression for graph/reap consumers).
2. **The hook path stops poisoning:** the rendered post-edit hook spawn covers code content (e.g. `--content all`), so a code edit's own hook build indexes it — incremental code freshness works on hook-enabled repos. Evaluate the hook-latency cost (background, detached, incremental — expected seconds on GPU for changed chunks only).
3. **One corpus definition:** `content=all` and `content=code` agree on code-table membership (tests/generated policy applied identically); a migration note covers repos whose tables currently include test chunks (first post-fix build reaps them — loud, logged).
4. **Recovery guidance corrected:** `AGENTS.md`/`build-and-verification.md` "code navigation feels stale" rows must not recommend the no-op (`content=code` update on a poisoned repo); until the fix ships, the working recovery is `--rechunk` or a full rebuild — and after it ships, the ordinary update works.
5. **Regression fixtures:** (a) code edit → docs-only build → code build MUST index the change (the poison scenario); (b) hook-spawn argument pin; (c) all-vs-code corpus-membership parity; (d) the health/coverage surfaces stay honest through the transition.

## Scope

**Problem statement:** content-scoped incremental builds destroy the change signal for the other content type, the automatic hook path does this on every edit, and corpus membership varies by content flag — collectively freezing code retrieval freshness fleet-wide while every health surface reads ok.

**In scope:** `indexer.py` meta/change-detection semantics; the rendered hook spawn (platform surfaces + seeds carrying it); corpus-filter unification; docs/decision-table corrections; fixtures.

**Out of scope:** chunker content changes; store schema; retrieval ranking.

## Acceptance Criteria

- [ ] AC-1: The poison scenario is fixture-pinned and fixed — a code edit followed by a docs-only build is still indexed by the next code/all build.
- [ ] AC-2: The rendered post-edit hook's spawn covers code content, with the argument pinned by test.
- [ ] AC-3: `content=all` and `content=code` produce the same code-table membership under identical include flags.
- [ ] AC-4: Stale-recovery documentation reflects reality (no recommended no-ops).
- [ ] AC-5: Full suite bytecode-free + docs validation + a live end-to-end verification on this repo (edit → hook-shaped build sequence → symbol searchable).

## Tasks

- [ ] Design pass: eligibility semantics for "would content=all chunk this file" (single source of truth with `_filter_code_files`/prefix filters).
- [ ] Implement content-scoped meta stamping + fixtures.
- [ ] Hook spawn change + surface re-render + pin.
- [ ] Corpus-filter unification + migration note.
- [ ] Docs corrections; suite; live verification.

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


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-07-11 | NOT folded into 1.12.0 (recommended fast-follow instead); operator decides. | The fix requires design decisions (eligibility semantics, hook cost, corpus migration) unsuited to a same-night patch into a twice-field-tested RC; the defect is long-standing (pre-dates 1.12 by many releases), not a 1.12 regression; and 1.12's upgrade path runs full/`all` builds, which are immune. | **Fold the one-line hook fix (`--content all`) into 1.12:** viable and cheap, and it removes the main poisoning vector — but without the meta fix, already-poisoned repos still need a rechunk, and shipping half the fix risks "fixed it" confusion; kept as an operator option. |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Hook builds get slower (code embedding per edit) | Detached background, incremental (changed chunks only); measure in the design pass. |
| Corpus unification reaps test chunks on repos that (unknowingly) had them | Loud reap logging + migration note; the documented contract already says tests are excluded. |
| Meta-scoping regression re-processes files every build | The semantic-ineligible carve-out; fixture-pinned. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.

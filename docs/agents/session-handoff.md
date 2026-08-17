# Session Handoff

Owner: Engineering
Status: active
Last verified: 2026-08-16

## Wave `1uwpf receipt-and-citation-contract-followups` — CLOSED 2026-08-10 (uncommitted)

Three changes delivered: `1uu0f` (receipt-authority docs reconciled to shipped code, five drifts), `1uu9y` (symbol-anchor citation rule at review-evidence authoring surfaces), `1uu9z` (twelve unguarded change-doc read sites fixed; unreadable docs now block close instead of being silently skipped; absolute-path leak class closed via `_read_error_detail`). Full ledger: 6/6 lane and council APPROVE across two review rounds, operator signoff recorded, closed via `wf_close_wave`.

`1us4q` (Decision Log churn) was admitted, implemented, falsified by six lanes, WITHDRAWN, and its implementation fully reverted — it is parked in `docs/plans/` carrying the findings. Do not re-attempt without reading its Progress Log.

**Carried-forward findings (need their own changes):** unguarded `wave.md` reads (same crash class, one file over); missing-admitted-doc silently skipped at close; synthetic single-arg `OSError` in the rollback path defeats `strerror`; the review-status reason string says "invalid actor or independence" when the true cause is receipt supersession; `docs/prompts/council-review.prompt.md` has no renderer sync for its citation paragraph; carrier parity unenforced between `REVIEW_POLICY_SURFACE_BLOCKS` and rendered regions; the p95 perf budget in `test_server_context_efficiency` fails under full-suite parallelism at HEAD.

**Nothing committed.** The tree holds this wave plus `1usqm`, `1uugh`, `1ur6o` — all closed, all uncommitted.

## Wave `1usqm citation-durability-and-receipt-integrity` — CLOSED (uncommitted)

Suite **7032 tests OK across 62 files**; docs-lint ok. Nothing committed since `bf085a21`.

### `1urlb-change plans-anchor-by-symbol-not-line-number` — implemented, 7/7 ACs

Symbol-anchor citation rule in seeds 170, 180, 211, propagated to `docs/agents/guru.md` (seed↔doc parity confirmed by SHA-256 on the `## Citation Format` region). Delivery review also caught a fifth carrier nobody counted: the Claude subagent template in `render_agent_surfaces.py` instructed bare `file:line`, contradicting the doc it delegates to. Repaired at source and re-rendered.

### `1upba-bug failed-prepare-appends-receipt-and-lapses-approvals` — implemented, 12/12 ACs

Readiness approvals now refuse against an already-superseded receipt, inside the publication lock, for every receipt-bound readiness key. Degradation splits by typed cause (`PolicyInputError.cause`); only `read` degrades. Close-branch carve-out gates both exits on `never_prepared_under_policy`.

**Known, named discrepancy that ships:** Requirement 9's "faithfully" claim is withdrawn. `wf_mark_ac(state='~')` is a second receipt writer, so one AC deferral on a never-prepared wave re-arms the readiness key. Recoverable (one prepare + one approval); every other population censused unaffected. **Follow-up: reconcile seed `007-review-system-overview.md`'s wording to the implemented rule.**

## Delivery review — COMPLETE, four lanes, all findings folded

All four lanes returned CHANGES REQUESTED; every finding is folded and re-verified. QA ran 22 mutants and found 9 survivors, three against required ACs (AC-3 non-digest fixture, AC-5 coverage, AC-9 ledger-health conjunct in the fail-open direction). All three now have tests and all three mutants were re-run and killed.

## Remaining before close

- **Delivery lane approvals not yet recorded** in the ledger: `code-reviewer`, `qa-reviewer`, `architecture-reviewer`, `docs-contract-reviewer`, plus the required delivery council and operator signoff.
- Readiness approval is recorded, bound to receipt `review-policy-1d603a3387c1ec91ff7c`.

## Follow-ups not in this wave

1. Reconcile seed 007's carve-out wording (above).
2. Review-evidence citation authoring lives in `209-agent-harness-core.prompt.md` and the lane seeds, outside `1urlb`'s declared surfaces; `237-council-review.prompt.md` should be revisited in the same change.
3. `docs/architecture/data-and-control-flow.md` carries three pre-existing drifts. The sole-writer one is now load-bearing for a gate decision, so it is contract-relevant rather than cosmetic.
4. `1us4q` remains parked behind its own census gate, by design.

## Note

`docs/plans/1upqx-...` was deleted (premise disproved at readiness). Wave `1ur6o`'s record retains the full disproof; its two "parked in `docs/plans/`" pointers were removed so nothing dangles.

## Current Session

**Active wave:** *(none)*

### Wave `1vk4c` (2026-08-16), CLOSED

Last closed wave: `1vk4c field-feedback-1p17p1-seed-scan-gaps` (changes `1vk4a`, `1vk4b`); from the first 1.17.1 field upgrades: seed-050 now specifies the `platform-mapping.md` Skills subsection seed-100 points at (seed-160 re-verifies it against the rendered skill directories on every upgrade), and `reconcile_scan.py` no longer reports table rows under the exact `## Resolved / closed` heading in the canonical `docs/missing-docs.md` (every producer, fence-aware, fail-toward-reporting; seed-230/150/160 reconciled; operators drop stopgap dispositions because the disposition key hashes the matched text and also silences the live tables). Readiness council corrected the plan from executed probes; delivery: three lanes + delivery council APPROVE after one aggregated hardening finding. Suite 7267 tests / 63 files OK. Operator signoff and close recorded 2026-08-16; committed and released with 1.17.1 (see below).

**Open questions / Deferred decisions:** legacy `docs/gaps/missing-docs.md` gets no archive exemption until consolidated per seed-220 (deliberate); rows parked under the archive heading are silenced by construction (accepted, allowlist pinned to one entry by test).

### Wave `1vgep` (2026-08-16), CLOSED

Last closed wave: `1vgep agent-role-canonicalization-audit` (change `1vflu`); shipped the read-only, registry-derived agent-surface integrity audit (duplicate framework review-carrier roles) surfaced through `wf_audit` and the upgrade operator summary. Implemented in another session (no MCP attached there); independently reviewed here. Five delivery findings repaired and reverified, including one this session introduced and then retracted: a zip-loaded `pre_cleanup` hook meant to cover the delivering upgrade DUPLICATED the advisory, because `phase_cleanup` runs in the standalone `--cleanup` process from the freshly extracted runner (memory `1vjt5-mem`). `upgrade_extensions.py` is byte-identical to HEAD; the cleanup-driver test pins exactly one advisory block. Suite 7261 tests / 63 files OK. CHANGELOG bullet under `## [1.17.1]`. Operator signoff and close recorded 2026-08-16.

**Open questions / Deferred decisions:** the `[~]` items in `1vflu` (reference census, wrapper policy, repo-local role classification, seed/prompt reconciliation) are deferred by operator direction; the `agent_surface_integrity_drift` diagnostic omits the structured `advisory=True` flag (info, not planned).

### Wave `1vglb` (2026-08-16), CLOSED

Last closed wave: `1vglb model-set-refs-main-fix` (change `1vgla`); shipped the set-3 offline model asset plus ref normalization at build/install/attest and a pinned online fallback, restoring the one-command release path. Operator signoff and close recorded via `wf_close_wave` 2026-08-16.

The model-set defect is fixed end to end. `refs/*` members are normalized (40-byte, no newline) at build (`_manifest_from_cache`, `build_bundle`), at install (`materialize_bundle`), and in attestation (`_cached_component_file_map`, `_verified_marker`) through one helper pair; the online fallback in `accel_embedder._hf_download_cached_first` is pinned to the canonical revision by (upstream, target) with a stderr miss line, and writes/normalizes `refs/main` after a pinned fetch; `attest_online_cache` and `materialize_bundle`'s already-installed skip normalize legacy refs in place. `MODEL_SET_VERSION` is `3`, the fingerprint is unchanged (ADR `1vglc`, weights byte-identical), and the canonical manifest differs from set 2 by exactly one sha. **`wavefoundry-models-3.zip` is published at the `models` tag** (351,495,236 bytes, sha256 `64154814bc6ecff330695dbac752174c60e29d016027180393192a77618169e5`) next to set 2, round-tripped from the download into a clean cache. **`build_pack.py --with-models` builds on this machine again** (exit 0 on the real tree against the repaired live cache; `--with-models --release-dry-run` exit 0 in a scratch clone with both assets and steps 3 to 7 printed). The live `~/.wavefoundry/cache` was repaired by materializing set 3 (arctic onnx-src now one snapshot, ref 40 bytes).

Delivery review (three fresh lanes) found three real defects, all repaired in-session and independently reverified by fresh contexts with executed known-bads: F-1vglb-01 (broad) the pin resolved by upstream only and the shared arctic upstream pinned the WRONG revision for onnx-src; F-1vglb-02 (medium) a commit-hash download writes no `refs/main`; F-1vglb-03 (medium) a legacy set-2 cache attested without the asset kept its 41-byte ref forever. Ledger: `code-reviewer`, `qa-reviewer`, `release-reviewer` delivery approvals recorded; readiness approvals recorded earlier. Suite **7254 tests OK across 62 files**; docs-lint ok. CHANGELOG `## [1.17.1] - 2026-08-16` staged.

**Next release (1.17.1) can use the one-command path:** commit the tree, then `build_pack.py --version 1.17.1 --with-models --release`. It rebuilds the companion (content-identical to the `models`-tag copy, different sha256 because of zip timestamps; the `models`-tag copy is canonical).

**Open questions / Deferred decisions (info, not planned):** companion zips are not byte-reproducible across builds; `_ensure_ref_main`/`_normalize_refs_in_place` write refs non-atomically (same pattern as the marker restore path); `accel_embedder._CLEAN_ONNX_CACHE` ignores `WAVEFOUNDRY_ONNX_SRC_CACHE` while `model_bundle` honors it (pre-existing). Pre-existing unrelated: `test_reranker_fp16_matches_fp32_when_available` fails on direct CoreML runs and skips under `run_tests.py`'s cpu pin.

### 1.17.0 RELEASED 2026-08-15

Tag `v1.17.0` on stamp commit `62c29ca1` (`1.17.0+pjdj`); assets `wavefoundry-1.17.0.pjdj.zip` (6,259,625 bytes) and the reattached, re-verified `wavefoundry-models-2.zip` (351,495,236 bytes; manifest identical to canonical, 15/15 sha256, zero undeclared); Latest resolves to v1.17.0. Contents: waves `1p6lp`, `1ve3a`, `1ve3e`, `1vbuu` plus the skills documentation. Suite 7244/62 OK. **The automated `--release` path REFUSED at pre-flight (`--release` now requires `--with-models`), and `--with-models` remains broken on this machine by the `refs/main` newline defect; shipped by hand along `build_pack`'s exact five-step ordering, same as 1.16.4.** That defect needs its own wave before releases are one command again. Target repos: drop the zip and run **Upgrade Wavefoundry**; thirteen `wf-` skills render there (all but `wf-package`/`wf-code-cleanup`).


### Wave 1p6lp CLOSED 2026-08-15 (implemented 2026-08-14)

All three changes implemented in one session, full suite **7239 tests across 62 files OK**, docs-lint clean, all ACs and tasks `[x]`:

- **`1p6lo`**: `Skill` registry + `render_skills` emitter in `render_agent_surfaces.py`, called before the Guru gate; `wf-` kebab-case namespace enforced (regex + test); `auto-guru`/`upgrade-wave` migrated to `wf-guru`/`wf-upgrade` with the ad-hoc writers retired; stale paths cleaned with a **containment check** (a full-suite find: the first cut would have unlinked through a symlinked parent; now refuses loudly, regression-tested); maintenance guard covers the `wf-` skill prefix on all three hosts via the rendered hook template; carrier-region graft keeps re-renders byte-convergent (second render writes nothing); seeds 050/160 updated under `seed_edit_allowed`.
- **`1v877`**: seed `177-red-team-review.prompt.md` + rendered `docs/prompts/red-team-review.prompt.md` (shortcuts **Red-team review** / **Red team this**); no-signoff/no-gate boundary; cross-refs in seeds 236/237/225 + rendered docs; catalog + manifest rows; live find: rendered specialist doc lagged seed 225's `improvement-review` mode, drift repaired.
- **`1p6lw`**: twelve skills total render to `.codex`/`.claude`/`.agents` (ten lifecycle + router + two migrated); Claude Code live-discovered them in-session; three descriptions containing `": "` (YAML-unsafe in frontmatter) repaired with a test forbidding the pattern.

Transition note for target repos: the maintenance-guard pin lives in rendered hook bodies, so already-installed repos keep guarding the old flat path until their next upgrade re-render.

**Closed 2026-08-15** after the six-seat delivery council PASS (see below) and explicit operator close via `/wf-close-wave`. CHANGELOG carries an `[Unreleased]` section with the skills and Red-team review bullets. Open questions carried nowhere: none; deferred skill candidates (`wf-config-review`, maintainer extras) are recorded in `1p6lw` Scope and the `1ve3a` plans. **Next:** operator may say Implement wave for `1ve3a` (single-OPEN slot now free). Nothing committed.

### Wave `1vbuu cleanup-review-reachability` CLOSED 2026-08-15

The fourth wave, from the operator's "can we improve this? anything in the graph?" after `1ve3e`. Verdict recorded in the change doc: the graph answered node reachability correctly and the failure was applying a node-reachability rule to a condition-reachability question while trusting a docstring, so path predicates on call edges were evaluated and DEFERRED. Delivered: (1) seed 221 gained a two-class reachability rule (node vs condition; three-step probe: enumerate every sentinel producer, grep the module's tests, treat prose unreachability as a hypothesis), mirrored into the repo-local cleanup prompt; (2) `code_impact` now attaches the advisory `test_callers_not_visible` when `include_tests=true` finds zero test-path callers, naming both invisibility reasons (index-excluded test trees like this repo's `scripts/tests/`, mock-driven coverage with no `calls` edge). Three-state tests on the existing fake-graph fixture; the live accel query that returned a silent empty this morning now emits the advisory with its 3 real callers intact. Live find: the `test_advisory_tags_appear_only_at_the_sanctioned_sites` guard (1uugg AC-10c) correctly rejected the new `advisory=True` site; the sanctioned set was extended deliberately with a stated reason (code_impact gates nothing). Typed ledger complete through delivery (readiness run + 4 approvals; delivery run + code, qa, docs-contract); suite 7244/62 OK; docs-lint clean; `docs/specs/mcp-tool-surface.md` gained one clause. Memory: none proposed, none forced (the lesson lives in the seed rule and `1vcgo-mem`). Closed on the operator's `/wf-close-wave`; CHANGELOG `[Unreleased]` Fixed section gained its bullet.

**End of session state: NO wave open; the four closed waves (`1p6lp`, `1ve3a`, `1ve3e`, `1vbuu`) are COMMITTED locally as `2f2858b5` (102 files, tree clean); NOT pushed, NOT released; suite 7244/62 OK; docs-lint clean.** Next: push and/or package (the CHANGELOG `[Unreleased]` section carries all four waves; `wf-package` reminds that the changelog gets its version header first). Open observation (no wave): the reranker FP16 drift test skips under the suite's cpu pin and fails on direct CoreML runs.

### Wave `1ve3e cleanup-review-followups` CLOSED 2026-08-15

Third wave of the day, born from the first real `/wf-code-cleanup` run. Its headline is a **withdrawn verdict**: the sweep recommended removing `accel_embedder`'s resident-graph fallback as dead-for-shipped-models (corroborating a docstring that said "unreachable"), the operator approved it, and plan-time verification falsified the premise: `_resolve_clean_onnx` degrades to that branch on any failed clean fetch and the offline-fallback tests execute it. `1ve3c` corrected the docstring instead (comment-only, proven by an empty executable-line diff); `1ve3d` fixed seed 160's two dangling `docs/prompts/agents/` references to when-present semantics. Typed ledger complete (readiness run + 3 approvals; delivery run + code-reviewer, docs-contract-reviewer, operator). Suite 7241/62 OK. Active memory `1vcgo-mem` records the sweep lesson (trace the sentinel producers, not just the registry lookup, before calling a fallback dead); operator chose to keep it. CHANGELOG `[Unreleased]` gained a Fixed section.

**Open observation, not in any wave:** `test_reranker_fp16_matches_fp32_when_available` FAILS on direct CoreML runs (one query drifts 0.067 vs the 0.05 bound) but is SKIPPED under `run_tests.py`'s `WAVEFOUNDRY_EMBED_PROVIDER=cpu` pin, so every green suite this week skipped it, not passed it. Pre-existing (identical on HEAD), machine-level, orthogonal to all three waves; a candidate for its own change (either the FP16 export precision or the bound).

**No wave open; nothing committed.** Three closed waves (`1p6lp`, `1ve3a`, `1ve3e`) ready to commit and ride the next release.

### Wave `1ve3a package-skill` CLOSED 2026-08-15

Full typed-ledger lifecycle in one day, each step explicitly operator-commanded through the new skills themselves (interrogate, implement, review, close): `initial_delivery` run record, executed code-reviewer + qa-reviewer approvals, operator signoff on the `/wf-close-wave` invocation. One decision memory promoted after a validation rewrite (the drafter's auto-target said `build_pack.py`; the mechanism lives in `render_agent_surfaces.py`): repo-conditional skills gate on backing-doc presence, never repo identity. CHANGELOG `[Unreleased]` extended with the doc-gated skills bullet. **No wave open; nothing committed.** Ready to commit both skill waves and ride the next release.

### Implementation record (2026-08-15)

Both changes implemented and marked: `Skill.requires_doc` replaces `requires_guru` (wf-guru pinned byte-identical via the shared `GURU_ROLE_REL` predicate); `wf-package` and `wf-code-cleanup` registered on their backing-doc gates; catalogs updated; new tests `test_doc_gate_polarity_both_directions` + `test_doc_gated_entries_declare_their_backing_doc_as_gate`; 14 skills render here, second render writes nothing; full suite **7241 tests across 62 files OK**; docs-lint clean. Remaining: delivery review (typed approvals for code-reviewer, qa-reviewer + `initial_delivery` run record + operator signoff), then operator-owned close.

### Original planning record (READIED 2026-08-15)

Per operator direction: two doc-gated skills over the `1p6lp` registry. `1vbpl` generalizes `requires_guru` into a doc-presence gate (`requires_doc`) and adds **`wf-package`** gated on `docs/prompts/package-wavefoundry.prompt.md` (seed 100 declares it public-only/when-present, so target repos never render it, which is the operator's constraint: this repository only). `1ve3b` adds **`wf-code-cleanup`** (operator-chosen name) gated on `docs/prompts/codebase-cleanup-review.prompt.md`, which no seed provisions to targets. This is a **typed events.jsonl wave**: readiness recorded via `wf_review_event` (readiness run record + three executed approvals: wave-council-readiness, code-reviewer, qa-reviewer, each with an executed known-bad control after the ledger rejected `known_bad_detected: false` on an executed approval). Receipt `review-policy-e1fc9a84f0a0df8dcfde`; delivery lanes code-reviewer + qa-reviewer; no delivery council required. Implementation starts only after `1p6lp` closes; `1vbpl` (gate mechanism) lands before `1ve3b`.

Also learned for future typed waves: hand-editing `Required review lanes` in a fresh wave.md invalidates the scaffolded review-status projection (the projector adds lane rows); regenerate the block to match `render_review_status_projection` output.

### Delivery review complete 2026-08-14

Invoked via the freshly rendered `/wf-review-wave` skill (the wave reviewing itself through its own deliverable). Six-seat delivery council ran inline at standard primer depth (red-team primer, code, qa, security, docs-contract, architecture rotating): **PASS**, one qa finding repaired in-cycle (the rendered-hook maintenance-guard prefix change had no pinning test; assertions added and executed, 94 tests OK). Fresh probes executed: registry-to-catalog parity 12/12, permissions surface zero-diff, five-file script diff census, reach-for sweep clean. `wave-council-delivery` and all five lane signoffs recorded as prose lines (legacy-prose wave). `wf_review_wave` now reports only `missing_operator_signoff` — the operator's own approval at close. Docs-lint clean. **Close remains operator-owned and has not been requested.**

### Wave 1p6lp revived and readied 2026-08-14

The parked 2026-06-19 skills wave was revived per operator direction. Both original change docs refreshed: line refs re-verified against HEAD, tool names corrected to the post-`1t3gt` surface, `wf-` kebab-case skill namespace adopted (operator direction; the two migrated skills rename to `wf-guru` and `wf-upgrade`), and `1p6lw` re-curated from five to **ten** skills (core loop + `wf-interrogate-plan`, `wf-evaluate-decision`, `wf-memory-review`, `wf-pause-wave`, plus the `wf-council` router over Wave Council / Archetype Council / standalone red-team review; full-catalog exclusions with reasons recorded in its Scope).

A third change was authored and admitted the same day: **`1v877-enh red-team-standalone-review-command`**, promoting red-team-in-isolation (seven standalone modes already defined in `docs/agents/specialists/red-team.md`) to the operator command **Red-team review** via a new seed (177 verified free), cross-refs in seeds 236/237/225, catalog rows, and an explicit no-signoff/no-gate boundary. It supplies `wf-council`'s third pointer target; `1p6lw` depends on both `1p6lo` and `1v877`.

Readiness council ran inline twice (initial pass: red-team, security-reviewer, docs-contract-reviewer; delta pass for the scope expansion: red-team, docs-contract-reviewer). The initial pass's one finding, an incomplete rename census, was folded into `1p6lo` Requirement 5 before approval; both `wf_prepare_wave(mode='ready')` calls succeeded (3 changes, lint clean). The wave awaits **Implement wave** (order: `1p6lo` registry, `1v877` command, `1p6lw` skills). All of this is uncommitted docs-only work.

### 1.16.4 released 2026-08-13

Tag `v1.16.4`, stamp commit `55ccb026` (`1.16.4+piwn`), pack `wavefoundry-1.16.4.piwn.zip`. Suite 7230 across 62 files, docs-lint ok, tree clean and pushed. Contents: wave `1v4yf` only, the Python 3.11 f-string repair in `memory_records.py`. Model set stays at v2, so `wavefoundry-models-2.zip` was reattached rather than rebuilt.

**Blocker hit, and worked around rather than fixed:** `build_pack --version 1.16.4 --with-models --release` aborted at `model_bundle.build_bundle` with `warmed model cache does not match the canonical verification manifest`.

The release shipped by reusing the existing `~/.wavefoundry/dist/wavefoundry-models-2.zip`, verified first against the canonical manifest (manifest identical, 15/15 declared files sha256-match, zero undeclared model files), then publishing by hand along `build_pack`'s own ordering: README badge stamp, stamp commit, annotated tag on that commit, push main, push tag, `gh release create` with both assets. Latest resolves to `v1.16.4`.

#### Root cause, diagnosed after the release

One byte in the published model asset. In `wavefoundry-models-2.zip`, the member `models/onnx-src/models--Snowflake--snowflake-arctic-embed-s/refs/main` is **41 bytes: the commit sha plus a trailing newline**. The other two components' `refs/main` members are clean 40-byte shas.

`huggingface_hub` resolves the symbolic revision `main` by reading `refs/main` verbatim and matching it against snapshot directory names, so `d3c1d2d4...798f\n` never matches the directory `d3c1d2d4...798f`. Every cached-first lookup for that one component therefore misses on a cache provisioned from the bundle. `accel_embedder._hf_download_cached_first` swallows the miss and falls through to an unpinned online `hf_hub_download`, which resolves `main` on the Hub to the current head `e596f507...`, pulls roughly 100 MB, writes a second snapshot, and rewrites `refs/main` to point at it. `_manifest_from_cache` enumerates the whole component directory, so that extra snapshot breaks exact equality against the canonical manifest from then on.

Executed evidence: on a scratch extraction of the published zip, `try_to_load_from_cache(revision='main')` returns `None` for all three files while `revision='d3c1d2d4...'` resolves them; stripping the single trailing newline makes `hf_hub_download(local_files_only=True)` resolve all three with no network.

Local timeline: `wf setup` installed the bundle at 18:15:37; the next index build downloaded `main` at 19:49:39; the release build only started at 19:51:51 and merely observed the result. The earlier note in this file blaming the release build was wrong.

**The contradiction that makes this unfixable locally:** the canonical manifest pins the sha256 of the **41-byte** form (`e0da9620...`, verified). Keeping the newline guarantees the re-download that breaks the manifest; stripping it makes `refs/main` itself fail the manifest. No byte state of that file satisfies both, so the published set-2 asset cannot be rebuilt from any cache that has been used once. Fixing it needs its own wave: normalize `refs/main` on install or at bundle build, regenerate the manifest, and republish the asset. Until then `--with-models` stays broken on this machine and on any machine that has provisioned models offline. Field impact short of that: one unnecessary ~100 MB re-download on the first index build after an offline provision; retrieval is unaffected, since the weights are byte-identical across the two commits.

### 1.16.0 released 2026-08-11

Tag `v1.16.0`, stamp commit `0324f9ee` (`1.16.0+pig9`), suite 7181 across 62 files, docs-lint ok. Model set v2 published at the permanent `models` tag as `wavefoundry-models-2.zip`. Set 1 stays unpublished (it carries the components the supplier-lineage policy removed), so 1.15.x and earlier have no distributed offline model set.

### Stage-gate waiver — seed 209 census instrument sentence (2026-08-12)

**Scope:** one paragraph added to `.wavefoundry/framework/seeds/209-agent-harness-core.prompt.md`, in the `census` object contract. No code, no validator semantics, no schema field added or changed.

**Granted by:** operator, in-session, 2026-08-12 ("we can make that one change directly").

**Gate handling:** `seed_edit_allowed` opened immediately before the edit and closed immediately after.

**What it adds and why it is not a restatement:** the seeds already carry the MCP-first exploration order comprehensively (`seed-020` Retrieval Rules, `seed-180:103-121`, and the tool-posture preamble in every reviewer role seed), so no further "prefer the MCP tools" guidance was added. The gap was epistemic rather than preferential: `census.universe_closed` presumes the author can tell when the universe is open, and an identifier search cannot find a consumer that holds the value under a different local name, so a census can report closed in good faith and be wrong. That is the defect wave 1v454 shipped and repaired.

**Asymmetry worth knowing:** `seed-180:130` already teaches the complement, that graph queries miss non-code mentions so impact analysis should also run `code_keyword`. Nothing taught the reverse direction until now.

**REFINED 2026-08-12, same waiver and gate cycle, before the text ever shipped.** The first version ranked the instruments: it told authors to close a value-flow universe with `code_references` and described identifier search as a complement for non-code mentions. Running the very next census, for wave `1v4ms`, produced the opposite failure: `code_references` on `rerank` missed both consumer sites in `server_impl` (calls through an instance attribute, `reranker.rerank(...)`), while `code_keyword` found them in one call. The rule now says no single instrument closes every universe, names both observed blind spots, requires crossing with at least two whose blind spots differ, requires reconciling disagreement rather than unioning, and requires recording which instrument closed which part of the claim. That matches what `seed-180` already teaches about chaining tools; the first draft had drifted from it by trying to name a winner.

### Stage-gate waiver — operator-approved, named scope

**Scope:** comment-only corrections in `.wavefoundry/framework/scripts/accel_embedder.py`. No behavioral change, no contract change, no test change.

**Granted by:** operator, in-session, 2026-08-11 ("Also, let's fix the out of date comment").

**Why a waiver rather than a wave:** the edits touch only docstring prose in a framework script, which affects no shipped or verified behavior. Recorded here per the `AGENTS.md` **Stage Gate** exclusion for operator-approved waivers on a named scope.

**What was corrected:** two comments described arctic as having no `CLEAN_ONNX_SOURCES` entry. Wave 1v0r0 registered it at `accel_embedder.py:72`, so both statements inverted the truth.

**Finding surfaced while correcting, NOT acted on:** `_resolve_model_files` returns the clean export first (`:274-276`), so the resident-graph branch at `:277-283` and its `_ensure_fastembed_model_cached` call are now unreachable for every model this set ships. Both arctic and MiniLM L6 are registered in `CLEAN_ONNX_SOURCES`; the branch only runs for an unregistered model. This is dead-for-shipped-models code, not a stale comment, and removing it needs its own change doc and wave. Note it does **not** make the `embedding-fastembed` bundle component redundant: `indexer._get_embedder` reaches fastembed through a different path (`indexer.py:3574-3586`) for small incremental runs and for accel failure on a GPU host.

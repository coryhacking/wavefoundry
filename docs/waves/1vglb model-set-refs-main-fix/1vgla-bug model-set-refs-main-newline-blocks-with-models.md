# A trailing newline in the model set's `refs/main` makes `--with-models` unbuildable and forces an unpinned re-download

Change ID: `1vgla-bug model-set-refs-main-newline-blocks-with-models`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-08-16
Wave: 1vglb model-set-refs-main-fix

## Rationale

Two consecutive releases (1.16.4 on 2026-08-13, 1.17.0 on 2026-08-15) had to be published by hand because `build_pack.py --release` now requires `--with-models`, and `--with-models` cannot rebuild the model asset on the release machine. The root cause was diagnosed after 1.16.4 and is fully reproducible; it has two layers.

**Layer 1, the defect in the shipped data.** In `wavefoundry-models-2.zip`, the member `models/onnx-src/models--Snowflake--snowflake-arctic-embed-s/refs/main` is 41 bytes: the commit sha plus a trailing newline. The other two components' `refs/main` are clean 40-byte shas. `huggingface_hub` resolves the symbolic revision `main` by reading `refs/main` verbatim and matching it against snapshot directory names, so `d3c1d2d4...798f\n` never matches the directory `d3c1d2d4...798f`, and every `local_files_only=True` lookup for that component misses on a cache provisioned from the bundle. The canonical verification manifest (`.wavefoundry/framework/model-set-verification-manifest.json`) pins the sha256 of the 41-byte form (`e0da9620...`, verified against both encodings), so the manifest itself encodes the defect.

**Layer 2, the amplifier in the code.** `accel_embedder._hf_download_cached_first` swallows the cache miss with a bare `except Exception: pass` and falls through to an **unpinned** online `hf_hub_download(repo, filename)`, which resolves Hub `main` to the current head (`e596f507...` at the time), downloads roughly 100 MB, writes a second snapshot, and repoints `refs/main`. `model_bundle._manifest_from_cache` enumerates the whole component directory, so the extra snapshot breaks exact equality against the canonical manifest, and `build_bundle` refuses with `warmed model cache does not match the canonical verification manifest`. From then on the cache is unrebuildable, and there is no local repair: keeping the newline guarantees the re-download that breaks the manifest, stripping it makes `refs/main` itself fail the manifest. No byte state satisfies both.

**Why the current code is inconsistent with itself.** `materialize_bundle` already *compares* the revision tolerantly (`archive.read(revision_name).decode().strip() == component["revision"].strip()`) but *writes* the bytes verbatim (`output.write_bytes(archive.read(path))`), so the tolerant check passes and the newline still lands on disk where huggingface_hub reads it strictly. Verified 2026-08-16 against `model_bundle.py` `materialize_bundle`.

**Why a set 3 rather than a tolerant-code-only fix.** The identity the indexer keys on is `EMBEDDING_COMPATIBILITY_FINGERPRINT` (`wf-model-set-2-20260811-arctic-s`), consumed by `indexer.py` and `upgrade_wavefoundry.py`; the model **weights are byte-identical** across the two Hub revisions (verified at the 1.16.4 diagnosis), so a corrected set can keep the same fingerprint and force no re-embed. Upgrades select the model asset by `MODEL_SET_VERSION` read from the feature pack, and `materialize_bundle` installs a higher set over a lower one atomically. Making the code tolerant of set 2 alone would leave the shipped asset defective and every fresh install still one index-build away from a 100 MB re-download; publishing set 3 fixes the data at the source while the code changes make the same class impossible to ship again.

## Requirements

1. **Normalize `refs/main` at build.** `_manifest_from_cache` and `build_bundle` read each component's `refs/main`, and the packed member and its manifest sha256 must be the **normalized 40-byte sha** (`.strip()`) regardless of what the local cache holds. Both functions must agree (they share the file enumeration; normalize in one helper used by both).
2. **Normalize `refs/main` at install.** `materialize_bundle` writes `refs/main` normalized (`.strip()` + no trailing newline) so a target cache resolves `main` on the first `local_files_only=True` lookup with no network. This is defensive for any future asset and independent of Requirement 1.
3. **Pin the online fallback.** `_hf_download_cached_first` passes `revision=<the component's canonical revision>` on its online branch, resolved from the canonical manifest by repo (fallback to `main` only when the repo is not a managed component). A cache miss must never be able to drift the cache to a different Hub head. Log the miss (repo, filename, pinned revision) at the existing stderr channel so a persisting miss is operator-visible rather than silently downloading every process.
4. **Publish set 3.** Bump `MODEL_SET_VERSION` to `"3"`; **keep** `EMBEDDING_COMPATIBILITY_FINGERPRINT` unchanged (weights identical, no re-embed); regenerate `model-set-verification-manifest.json` from a clean warmed cache under the normalized rules (Requirement 1) so it pins the 40-byte forms; confirm every non-`refs/main` sha256 is unchanged from set 2. `build_bundle` then succeeds on this machine and produces `wavefoundry-models-3.zip`, published at the permanent `models` release tag per the standing release convention (memory: `project_1p16_0_release`, `project_u8o2_...`).
5. **Executable falsification.** Tests prove: (a) a cache whose `refs/main` carries a trailing newline still builds a bundle whose packed `refs/main` is 40 bytes and whose manifest matches a normalized canonical manifest (build-side normalization); (b) materializing a bundle whose packed `refs/main` has a trailing newline writes a 40-byte file to disk (install-side normalization); (c) `_hf_download_cached_first` passes `revision=<canonical>` on the online branch for a managed repo (mock `hf_hub_download` and assert kwargs) and omits it for an unmanaged repo; (d) the shipped set-2 asset (fixture-sized replica) reproduces the original miss on `try_to_load_from_cache(revision='main')` before install-normalization and resolves after, the executed known-bad pair.
6. **Release path restored.** `build_pack.py --version X --with-models --release-dry-run` completes on the release machine after the cache is re-warmed once from set 3, proving the one-command release path is back.

## Scope

**Problem statement:** The published model asset carries a one-byte defect that its own manifest pins, and the cached-first download amplifies any miss into an unpinned cache drift; together they make `--with-models`, and therefore `--release`, unusable on the release machine.

**In scope:** Requirements 1 through 6, in `model_bundle.py`, `accel_embedder.py`, the canonical verification manifest, `MODEL_SET_VERSION`, tests, and the models-tag publish.

**Out of scope:**

- Changing model choice, weights, or the embedding fingerprint (nothing re-embeds).
- Retiring or republishing set 2 (it stays at the `models` tag for 1.16.x/1.17.0 consumers; the version compare installs set 3 over it on the next upgrade).
- The 1.17.0 release itself (already published by hand).
- The `--release` pre-flight rule that requires `--with-models` (correct as written; this change makes it satisfiable).

## Acceptance Criteria

- [x] AC-1: `build_bundle` on a cache whose `refs/main` has a trailing newline packs a 40-byte `refs/main` and a manifest equal to the normalized canonical manifest; `_manifest_from_cache` and `build_bundle` share one normalization helper.
- [x] AC-2: `materialize_bundle` writes `refs/main` normalized to disk; a subsequent `hf_hub_download(..., local_files_only=True)` (or `try_to_load_from_cache(revision='main')`) resolves with no network on a fixture cache.
- [x] AC-3: `_hf_download_cached_first`'s online branch is pinned to the canonical revision for managed repos and logs the miss; unmanaged repos keep `main`.
- [x] AC-4: `MODEL_SET_VERSION == "3"`, fingerprint unchanged, canonical manifest regenerated with 40-byte `refs/main` shas and every other sha identical to set 2; `wavefoundry-models-3.zip` builds on this machine and is published at the `models` tag with a size/sha record in the wave.
- [x] AC-5: the four falsification tests in Requirement 5 exist and pass; the known-bad pair (d) fails-then-passes across the normalization; full suite green; docs-lint clean.
- [x] AC-6: `--with-models --release-dry-run` completes on the release machine (recorded with its log), restoring the one-command release path.

## Tasks

- [x] `model_bundle.py`: `_normalized_ref_bytes` helper; use in `_manifest_from_cache`, `build_bundle`, and `materialize_bundle`'s write path.
- [x] `accel_embedder.py`: revision pin + miss log in `_hf_download_cached_first` (resolve repo to canonical revision via `model_bundle`).
- [x] Bump `MODEL_SET_VERSION` to `"3"`; regenerate the canonical manifest from a clean re-warmed cache; diff against set 2 (only three `refs/main` shas change).
- [x] Tests (a) through (d); full suite; docs-lint.
- [x] Build `wavefoundry-models-3.zip`, verify (manifest identity, per-file sha, zero undeclared), publish at the `models` tag; record size + sha256.
- [x] `--with-models --release-dry-run` on this machine; record the log. Update `docs/prompts/upgrade-wavefoundry.prompt.md` model-set notes and README "Model downloads" if they name set 2 explicitly (check at implement).

## Agent Execution Graph


| Workstream | Owner       | Depends On | Notes |
| ---------- | ----------- | ---------- | ----- |
| normalize  | implementer | —          | Goal: one helper, three call sites; build/install both normalized; tests (a)(b) |
| pin        | implementer | —          | Goal: online fallback pinned + logged; test (c) |
| set3       | implementer | normalize  | Goal: version bump, manifest regenerated from clean cache, asset built + verified + published |
| prove      | implementer | set3, pin  | Goal: known-bad pair (d), suite, release-dry-run log |


## Serialization Points

- `.wavefoundry/framework/scripts/model_bundle.py`
- `.wavefoundry/framework/scripts/accel_embedder.py`
- `.wavefoundry/framework/model-set-verification-manifest.json`
- `.wavefoundry/framework/scripts/tests/test_model_bundle.py`
- `.wavefoundry/framework/scripts/tests/test_accel_embedder.py`

## Affected Architecture Docs

`docs/architecture/decisions/`: an ADR is warranted for the set-3 identity decision (new `MODEL_SET_VERSION`, same `EMBEDDING_COMPATIBILITY_FINGERPRINT`, because weights are identical and only a reference file changes); the model-set identity contract is a shipped, cross-repo boundary. Also check `docs/prompts/upgrade-wavefoundry.prompt.md` and the README's "Model downloads" section for explicit set-2 mentions.

## AC Priority

(Populate one row per AC at plan time, before the prepare council runs. Filling this table after readiness is recorded supersedes the review-policy receipt and lapses the approvals it just collected. The `ac_priority_unpopulated` advisory at Prepare is the backstop, not the schedule.)


| AC   | Priority  | Rationale |
| ---- | --------- | --------- |
| AC-1 | required  | Build-side normalization is what makes the asset rebuildable. |
| AC-2 | required  | Install-side normalization is what stops the first-lookup miss in every target repo. |
| AC-3 | required  | The pin is what makes a miss harmless forever; without it the class recurs on the next bad byte. |
| AC-4 | required  | Publishing set 3 fixes the data at the source; fingerprint stability protects every existing index. |
| AC-5 | required  | The known-bad pair is the proof; the suite is the regression floor. |
| AC-6 | important | The operator-visible outcome, but it depends on this machine's cache state, so it is evidence, not the contract. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-08-16 | Planned after two by-hand releases (1.16.4, 1.17.0). Every claim re-verified against the tree: `_manifest_from_cache`/`build_bundle` enumerate `refs` + `snapshots` and read `refs/main` with `.strip()` only for the revision field, not the packed bytes; `materialize_bundle` compares tolerantly but writes verbatim; `_hf_download_cached_first` swallows the miss and downloads unpinned; the canonical manifest pins the arctic onnx-src `refs/main` at `e0da9620...` (the 41-byte form) while the other two components are 40 bytes; the fingerprint is consumed by `indexer.py` and `upgrade_wavefoundry.py`; upgrades select the asset by `MODEL_SET_VERSION` from the pack. | `model_bundle.py` (`_manifest_from_cache`, `build_bundle`, `materialize_bundle`), `accel_embedder.py` `_hf_download_cached_first`, canonical manifest read via `load_canonical_verification_manifest` 2026-08-16; memory `project_model_cache_drift_blocks_release` (executed diagnosis 2026-08-13) |
| 2026-08-16 | Implemented normalization at all four sites (`_manifest_from_cache`, `build_bundle`, `materialize_bundle` write path, `_cached_component_file_map`/`_verified_marker` attestation) through one helper pair (`_is_ref_member` + `_normalized_ref_bytes`); pinned `_hf_download_cached_first`'s online branch to the canonical revision for managed repos with a stderr miss log; `MODEL_SET_VERSION` 2 to 3 with the fingerprint held (ADR `1vglc`); canonical manifest regenerated from the PUBLISHED set-2 asset extracted to a scratch cache under the normalized rules: exactly one sha changed (arctic onnx-src `refs/main`), 15 paths, revisions, and fingerprint identical. | `model_bundle.py`, `accel_embedder.py`, `model-set-verification-manifest.json` diff (1 sha), `test_model_bundle.py` 22 OK, `test_accel_embedder.py` cached-first 5 OK |
| 2026-08-16 | Built `wavefoundry-models-3.zip` via `build_pack.py --with-models` (exit 0), verified (packed `refs/main` 40 bytes for all three components; bundle manifest == canonical; 15/15 declared sha256; zero undeclared), published at the permanent `models` release tag alongside set 2, then re-downloaded the published asset and materialized it into a CLEAN cache (`FASTEMBED_CACHE_PATH`/`WAVEFOUNDRY_ONNX_SRC_CACHE` redirected): installed `refs/main` 40 bytes, `huggingface_hub.try_to_load_from_cache(revision='main')` resolves for every shipped file, clean-cache `_manifest_from_cache` == canonical, `local_model_set_status() == current`. Published asset: 351,495,236 bytes, sha256 `64154814bc6ecff330695dbac752174c60e29d016027180393192a77618169e5`. | `gh release view models` (assets `wavefoundry-models-2.zip`, `wavefoundry-models-3.zip`); round-trip script output 2026-08-16 |
| 2026-08-16 | Release path restored: `build_pack.py --version 1.17.1 --with-models --release-dry-run` completed (exit 0) in a scratch clone of this working tree on its own `main` (a worktree cannot satisfy the branch pre-flight because it shares the branch namespace); pre-flight passed, LOCAL build produced `wavefoundry-1.17.1.pjiq.zip` + `wavefoundry-models-3.zip`, and steps 3 to 7 (stamp, commit, tag, push, `gh release create` with both assets) printed. The live `~/.wavefoundry/cache` was repaired by materializing set 3, so `build_bundle`'s exact-manifest gate also passes on the real tree (`build_pack --with-models` exit 0 there too). Two set-2 literal assertions surfaced in the full suite (`test_build_pack`, `test_setup_index`) and now follow `MODEL_SET_VERSION`/`bundle_name()`; suite 7249/62 with the pre-existing CoreML-only `test_reranker_fp16_matches_fp32_when_available` drift as the only non-suite-path failure (skips under `run_tests.py`, unrelated); docs-lint ok. | scratchpad `release-dry-run-1vglb.log`, `wm.log`, `suite-1vglb.log` |
| 2026-08-16 | Gapfill: implement-stage retrieval ran through the plan-stage map rather than fresh `code_*` calls. The five-file footprint (`model_bundle.py`, `accel_embedder.py`, the canonical manifest, two test files) was fully located and read during planning (15 credited retrieval calls); implementation was targeted edits at those known sites plus executed probes that are shell work by definition (bundle build, cache extraction and sha comparison, `gh release upload`, clean-cache materialization, suite runs). Two late test sites (`test_build_pack`, `test_setup_index`) surfaced from the executed full suite, not from a search. | plan-stage telemetry in `wave.md` context-efficiency state; `suite-1vglb.log` |
| 2026-08-16 | Delivery review (code-reviewer, qa-reviewer, release-reviewer lanes, fresh contexts) found two real defects, both independently by two lanes and both repaired in-session: F-1vglb-01 (broad) the revision pin resolved by upstream only, and the arctic upstream is shared by the fastembed component at a different revision, so the onnx-src miss pinned e596f507, the exact drift head; repaired by resolving on (upstream, target) with `_hf_download_cached_first` passing `onnx-src`, plus a real-manifest test and a two-component fake. F-1vglb-02 (medium) a commit-hash-pinned download writes no `refs/main`, so every later process missed `main` again and the cache could not attest; repaired by `_ensure_ref_main` writing the normalized 40-byte ref once after a successful pinned download (never repointing an existing ref), with a tmp-cache test. Also fixed from the lanes' lower findings: `_cache_member_sha256` streams non-ref members again (weights no longer read whole into memory), `_verified_marker` accepts a legacy verbatim ref digest so an installed set 2 reads as older rather than mixed during upgrade (tested both ways plus tamper), the checked-in manifest test now asserts every `refs/main` sha is the 40-byte form, the fixture carries a whitespace-bearing non-ref member so normalization scope is falsifiable (the two mutants that survived, strip-everything and always-ref, now die), test (b) lost its no-op `_sha256` patch, the two leaky miss tests redirect stderr, and the install-side comment was reworded. Executed mutation matrix in scratch: mut5, mut5b, mutF1, mutF2, mutLegacy all fail the intended tests and pass on restore. Targeted files after repair: 866 tests, only the pre-existing CoreML `test_reranker_fp16` drift fails (skips under `run_tests.py`); `test_model_bundle` 23 OK, cached-first 7 OK; docs-lint ok. | typed ledger F-1vglb-01 / F-1vglb-02 (finding, repair_start, reverification); `repair-targeted.log`; scratch `mut-1vglb` |
| 2026-08-16 | Release lane finding F-1vglb-03 (medium), repaired: a legacy set-2 cache (41-byte arctic ref) upgraded WITHOUT the set-3 asset in reach was attested as set 3 with the defect intact (attest hashes refs normalized, so it could not see it), after which an asset drop was a no-op publish and `_ensure_ref_main` returned early, leaving the per-process miss line forever. Repair: one helper `_normalize_refs_in_place` (refs/* only, idempotent, returns originals for rollback) runs in `attest_online_cache`'s write phase before the equal-marker skip, on `materialize_bundle`'s already-installed skip path, and `_ensure_ref_main` rewrites an existing ref that names the pin with a newline (never repoints one that differs). Tests: legacy cache through attest then materialize skip with the REAL `huggingface_hub` resolving `main` at the end; helper scope/idempotence; extended pinned-download test. Executed mutants mutF3a-d (attest no-normalize, skip no-normalize, ensure-ref early return, scope widening to rglob) all die. Also fixed the lane's doc findings: model-selection fingerprint rule now matches ADR `1vglc`; build-and-verification names `wavefoundry-models-<MODEL_SET_VERSION>.zip`; release-flow says builds (never reuses) and the recovery `gh release create` lists both assets. Deferred as info (not planned): companion zips are content-identical but not byte-reproducible across builds (zip timestamps), so v1.17.1 will carry a models-3 with a different sha256 than the `models`-tag copy; the `models`-tag copy is canonical. | typed ledger F-1vglb-03; scratch `mut-1vglb`; docs-lint ok |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-08-16 | Publish a set 3 with the SAME embedding fingerprint, plus normalize at build and install, plus pin the online fallback. | Fixes the data at the source (every fresh install stops missing), keeps every existing index valid (weights identical, fingerprint stable), and removes the amplifier so the class cannot recur; the version compare installs set 3 over set 2 cleanly. | Tolerant code only, keep set 2 (rejected: leaves a defective published asset and a 100 MB re-download on every fresh install's first index build); regenerate the manifest against the drifted local cache (rejected: would pin a two-snapshot cache as canonical, and set 2 is a shipped contract at the `models` tag); pin only, no set 3 (rejected: the first-lookup miss on the newline persists, it just stops drifting). |
| 2026-08-16 | Keep the `--release`-requires-`--with-models` pre-flight. | It is the correct invariant (feature pack and model asset ship together); this change makes it satisfiable rather than working around it. | Add an escape flag (rejected: reintroduces the by-hand class the invariant exists to prevent). |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Regenerating the manifest from a re-warmed cache captures a drifted revision. | Warm from set 3's own normalized bundle in a scratch cache root; assert every non-`refs/main` sha equals set 2 before accepting the manifest; the diff must be exactly three lines. |
| Fingerprint stability claim is wrong and existing indexes need re-embedding. | Executed check at implement: byte-compare the arctic weights across revisions `d3c1d2d4` and `e596f507` (already verified 2026-08-13; re-verify in the wave record). |
| The revision pin breaks a legitimate future model bump. | The pin is resolved from the canonical manifest, so a bump updates it in the same place; unmanaged repos are unaffected. |
| `test_model_bundle` fixtures assume verbatim `refs/main` bytes. | Audit the 18 existing tests at implement; update any that assert the pre-normalization shape, recording each as a deliberate contract change. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.

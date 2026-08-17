# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-08-16
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1vglb model-set-refs-main-fix`
Title: Model Set Refs Main Fix

## Objective

Restore the one-command release path by fixing the model-set defect that forced 1.16.4 and 1.17.0 to ship by hand: normalize `refs/main` at build and install, pin the cached-first online fallback to the canonical revision so a cache miss can never drift the cache, and publish model set 3 with the same embedding fingerprint (weights are byte-identical, so no index re-embeds). When this wave closes, `build_pack.py --with-models --release` works again on the release machine and every fresh install resolves `main` offline on first lookup.

## Changes

Change ID: `1vgla-bug model-set-refs-main-newline-blocks-with-models`
Change Status: `implemented`

## Participants

- Coordinator: agent session coordinator
- Write-owning roles: implementer
- Requested review lanes: release-reviewer
- Required review lanes: code-reviewer, qa-reviewer, release-reviewer

Completed At: 2026-08-16

## Wave Summary

Wave `1vglb` (Model Set Refs Main Fix) delivered one change: A trailing newline in the model set's `refs/main` makes `--with-models` unbuildable and forces an unpinned re-download. Notable adjustments during implementation: A trailing newline in the model set's `refs/main` makes `--with-models` unbuildable and forces an unpinned re-download: Delivery review (code-reviewer, qa-reviewer, release-reviewer lanes, fresh contexts) found two real defects, both independently by two lanes and both repaired in-session: F-1vglb-01 (broad) the revision pin resolved by upstream only, and the arctic upstream is shared by the fastembed component at a different revision, so the onnx-src miss pinned e596f507, the exact drift head; repaired by resolving on (upstream, target) with `_hf_download_cached_first` passing `onnx-src`, plus a real-manifest test and a two-component fake. F-1vglb-02 (medium) a commit-hash-pinned download writes no `refs/main`, so every later process missed `main` again and the cache could not attest; repaired by `_ensure_ref_main` writing the normalized 40-byte ref once after a successful pinned download (never repointing an existing ref), with a tmp-cache test. Also fixed from the lanes' lower findings: `_cache_member_sha256` streams non-ref members again (weights no longer read whole into memory), `_verified_marker` accepts a legacy verbatim ref digest so an installed set 2 reads as older rather than mixed during upgrade (tested both ways plus tamper), the checked-in manifest test now asserts every `refs/main` sha is the 40-byte form, the fixture carries a whitespace-bearing non-ref member so normalization scope is falsifiable (the two mutants that survived, strip-everything and always-ref, now die), test (b) lost its no-op `_sha256` patch, the two leaky miss tests redirect stderr, and the install-side comment was reworded. Executed mutation matrix in scratch: mut5, mut5b, mutF1, mutF2, mutLegacy all fail the intended tests and pass on restore. Targeted files after repair: 866 tests, only the pre-existing CoreML `test_reranker_fp16` drift fails (skips under `run_tests.py`); `test_model_bundle` 23 OK, cached-first 7 OK; docs-lint ok.; A trailing newline in the model set's `refs/main` makes `--with-models` unbuildable and forces an unpinned re-download: Release lane finding F-1vglb-03 (medium), repaired: a legacy set-2 cache (41-byte arctic ref) upgraded WITHOUT the set-3 asset in reach was attested as set 3 with the defect intact (attest hashes refs normalized, so it could not see it), after which an asset drop was a no-op publish and `_ensure_ref_main` returned early, leaving the per-process miss line forever. Repair: one helper `_normalize_refs_in_place` (refs/* only, idempotent, returns originals for rollback) runs in `attest_online_cache`'s write phase before the equal-marker skip, on `materialize_bundle`'s already-installed skip path, and `_ensure_ref_main` rewrites an existing ref that names the pin with a newline (never repoints one that differs). Tests: legacy cache through attest then materialize skip with the REAL `huggingface_hub` resolving `main` at the end; helper scope/idempotence; extended pinned-download test. Executed mutants mutF3a-d (attest no-normalize, skip no-normalize, ensure-ref early return, scope widening to rglob) all die. Also fixed the lane's doc findings: model-selection fingerprint rule now matches ADR `1vglc`; build-and-verification names `wavefoundry-models-<MODEL_SET_VERSION>.zip`; release-flow says builds (never reuses) and the recovery `gh release create` lists both assets. Deferred as info (not planned): companion zips are content-identical but not byte-reproducible across builds (zip timestamps), so v1.17.1 will carry a models-3 with a different sha256 than the `models`-tag copy; the `models`-tag copy is canonical.

**Changes delivered:**

- **A trailing newline in the model set's `refs/main` makes `--with-models` unbuildable and forces an unpinned re-download** (`1vgla-bug model-set-refs-main-newline-blocks-with-models`) — 6 ACs completed. Key decisions: Publish a set 3 with the SAME embedding fingerprint, plus normalize at build and install, plus pin the online fallback.; Keep the `--release`-requires-`--with-models` pre-flight.
## Watchpoints

- **Watchpoint, fingerprint stability is load-bearing:** the same-fingerprint decision rests on byte-identical weights across revisions `d3c1d2d4` and `e596f507`; the readiness council re-executed the byte compare (three files IDENTICAL). Any deviation at implement blocks the fingerprint decision.
- **Watchpoint, the local cache is drifted:** `refs/main` on this machine is already the 40-byte `e596f507` form with two snapshots; the manifest regeneration MUST warm from set 3's own normalized bundle in a scratch cache root, never from `~/.wavefoundry/cache` as-is, and the manifest diff against set 2 must be exactly the three `refs/main` shas.
- **Watchpoint, publishing set 3** to the `models` tag is a remote side effect inside implementation; it is authorized by this wave's scope (AC-4) but the models-tag upload happens only after the asset verifies (manifest identity, per-file sha, zero undeclared).
- **Follow-up (deferred):** none new; the `--release`-requires-`--with-models` invariant is kept deliberately.

## Review Checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-08-16: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: keeping the embedding fingerprint across a model-set bump could silently mask a real weight change in some future bump that copies this precedent, mitigated by making the fingerprint decision rest on an EXECUTED byte compare recorded in the wave (three arctic files identical across revisions `d3c1d2d4` and `e596f507`) and by the ADR the change doc calls for, which states the rule as weights-identical-therefore-fingerprint-stable rather than set-bumps-never-touch-the-fingerprint; strongest-alternative: tolerant code only, keeping set 2 published, rejected because it leaves a defective asset at the `models` tag and every fresh install one index build away from a 100 MB unpinned re-download)

Seat evidence (code-grounded, probes executed 2026-08-16):

- red-team: every load-bearing claim executed against the tree and the published asset: the packed arctic onnx-src `refs/main` is 41 bytes while the other two are 40 (unzip byte counts); the canonical manifest pins the 41-byte sha (raw sha equals pinned, stripped sha does not); `materialize_bundle` writes verbatim (`output.write_bytes(archive.read(path))` present) while comparing with `.strip()`; `_hf_download_cached_first` swallows the miss and downloads unpinned; fingerprint consumers are exactly `indexer.py`, `upgrade_wavefoundry.py`, and `model_bundle.py` itself; the local cache holds both snapshots with `refs/main` now the 40-byte `e596f507` form (the drift the plan describes); the arctic weights are byte-identical across the two snapshots (fp16, int8, tokenizer all IDENTICAL by sha256), which is the executed basis for keeping the fingerprint; `test_model_bundle.py` has 18 tests to audit for verbatim-bytes assumptions. No unrepaired findings.
- docs-contract-reviewer: the ADR obligation is named in Affected Architecture Docs with the precise decision it must record; the release convention (models asset at the permanent `models` tag) is cited to the standing memory rather than restated; the change keeps the `--release`-requires-`--with-models` invariant and says so; AC Priority populated at plan time; serialization points are pure paths; the upgrade prompt and README model-download notes are flagged for a set-2 mention check at implement. No findings.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| F-1vglb-01 | do_now | no | completed | — |
| F-1vglb-02 | do_now | no | completed | — |
| F-1vglb-03 | do_now | no | completed | — |

*Machine review state — 3 findings; current: do_now 3, maybe_later 0, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| wave-council-readiness | approved | current executed approval follows every affected repair | none |
| code-reviewer | approved | current executed approval follows every affected repair | none |
| qa-reviewer | approved | current executed approval follows every affected repair | none |
| release-reviewer | approved | current executed approval follows every affected repair | none |
| operator-signoff | approved | current executed approval follows every affected repair | none |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Dependencies

- No external wave dependencies.

<!-- wave:context-efficiency begin -->
## Context Efficiency

Estimated token savings use phase-unique returned source versions and mapped workflow prompts, minus recorded request and response tokens. Saved model output or avoided tool loops count only through quality-equivalent paired evidence.

| Stage | Tool calls | Estimated token savings |
| --- | ---: | ---: |
| plan | 15 | 7,345 |
| implement | 31 | 0 |
| review | 134 | 2,352,693 |
| **Total** | **180** | **2,360,038** |

<!-- wave:context-efficiency-state {"generation":179,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":31,"content_source_credit":0,"derived_artifact_credit":0,"direct_net":-6735,"estimated_tokens_saved":0,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":1628,"response_debit":6161,"source_credit_count":0,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1054},"plan":{"calls":15,"content_source_credit":18912,"derived_artifact_credit":2039,"direct_net":7345,"estimated_tokens_saved":7345,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":2206,"response_debit":14906,"source_credit_count":10,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3506},"review":{"calls":134,"content_source_credit":2626442,"derived_artifact_credit":1107,"direct_net":2352693,"estimated_tokens_saved":2352693,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":18330,"response_debit":257872,"source_credit_count":101,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1346}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":180,"content_source_credit":2645354,"derived_artifact_credit":3146,"direct_net":2353303,"estimated_tokens_saved":2360038,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":22164,"response_debit":278939,"source_credit_count":111,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":5906},"wave_id":"1vglb model-set-refs-main-fix"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 4 | 0 | 4 | 1,659,027 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":4,"estimated_exploration_avoided":1659027,"surfaced_events":4} -->
<!-- wave:exploration-avoided end -->

# Session Handoff

Owner: Engineering
Status: active
Last verified: 2026-09-17

## Current Session

**Active wave:** *(none — idle)*
**Last closed wave:** `1y0gz record-layout-roots` — project-relative fork-editable record roots and bounded nested wave discovery, consistently used by lifecycle, dashboard, lint, memory and historical attribution.

Closed by explicit operator instruction after independent code/QA/council approvals. Both changes and all 17 ACs complete; no AC deferrals. Full framework receipt current: 9,277 tests, 12 skips. Memory checkpoint respects eight validated dispositions and has zero pending candidates. Framework gate closed; changes remain uncommitted.

MCP restart verified: runner `23e4b4c351ad` matches disk, implementation current, index ready, schema 8 integrity OK, no missing/orphan vectors, graph and semantic generation aligned. The earlier stale-runner warning is resolved. Supplemental evidence: `docs/waves/1y0gz record-layout-roots/supplemental-goal-review.md`.

Remaining Waveforge implementation order: `1y0h0 typed-phase-gates`, `1y0h1 tool-registry-dispatch`, then `1y0h2 handler-module-split`. The OPEN slot is free. Wave `1ycrj task-fit-agent-model-policy` is separately prepared/reviewed; implementation was intentionally held while this wave was open.

## Release

Release target `1.25.0` approved 2026-09-17. Two local projects reported successful upgrades to the test package, clean docs/reconciliation checks and completed prompt editing passes. The follow-up clarifies that Python guidance applies only to Wavefoundry tooling, not the host application language. The official path builds the feature archive and verified model set 3 through `build_pack.py --with-models --release`.

Local test build `1.25.0+pqmt` created 2026-09-17 at `~/.wavefoundry/dist/wavefoundry-1.25.0.pqmt.zip` (7,486,022 bytes). SHA-256: `09defc0419ff5b8c176084161090b1ed27673a6b1aff0ad28c058a2521b70f2a`. Docs gate passed; 9152-test receipt current. Outer archive and inner upgrade payload verified, including exact changelog, version and source bytes. VERSION and prompt manifest match. Feature-only local build; no models bundled, tag, commit or publication. Advisory sensor `ac_asserts_repository_state` (1wur7) remains advisory.

Official 1.24.0+ppq7 published on 2026-09-13; tag v1.24.0 and framework/model asset hashes verified. Source commit 3433fb03; release stamp f8e4732e. Host-neutral orchestration is subsequent source work, not a new packaged release.

## Open questions / Deferred decisions

- Not yet scoped: give the `terminology` workflow-config key real consumers beyond the dashboard (rendered docs and messages). Premise correction recorded in `docs/reports/waveforge-fork-audit.md`: the key is read by `dashboard_lib.py` today, and Waveforge's values are keyed by Waveforge tier names (their `wave` is Wavefoundry's `change`), so a change must fix whose vocabulary the keys use before it can claim zero-edit merges.
- Graph-expansion/reranking quality comparison (evaluation AC-4) remains intentionally deferred; current retrieval ordering unchanged.
- Native Windows/Linux/Intel execution remains release follow-through.
- Investigate MCP's initial `graph_rebuilt=false` notice on an all-content full rebuild.
- The CoreML reranker probe fell back to CPU after `output_features has no value for logits`; no reranker fix included.
- Any other unfinished povc receipt must retain its original archive; qualified revision-2 repair: `/Users/coryhacking/.wavefoundry/dist/povc-storage-rebuild-repair-v2.zip`.
- Follow-ups recorded by the 1xtnr council, not in scope: bind the two `graph-index-system.md` builder-version mirrors to `docs_constants_validators._claims()`; a kind-aware `symbol_lookup` once `reads` binds get their own table; route `_scan_all_call_sites_in_file` through `_resolve_repo_path`.

- Record-layout follow-ups: conventional-root seed prose and an explicit nested-create parent argument remain outside this wave; canonical architecture and regression tests retain the consumer-identity lessons.

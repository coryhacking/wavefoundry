# Session Handoff

Owner: Engineering
Status: active
Last verified: 2026-09-13

## Current Session

**Active wave:** *(none)*
**Status:** wave work idle; operator authorized committing the release changes and publishing official 1.24.0.

**Last closed wave:** `1xxcd staged-graph-memory-publication` — candidate graph builds remain separate from live memory publication; standard upgrades preserve memory and reclaim superseded storage after verification.

All five ACs and tasks completed. Required specialist and targeted Council approvals are current, and closure passed with a proven framework receipt: 9,008 tests, 12 skips, input hash `e93ffd69905569097c61198cf6e040b61800d000d41ac3314814d2b85d191524`. The complete suite ran with two workers outside the sandbox; before/after source inventories match. Memory proposal returned zero candidates. Framework/seed edit gates are closed.

Permanent tests cover fresh conversion and interrupted retries with outer/feature retained archives through live publication and cleanup. Local field upgrades completed and matched package bytes. The one-off ppol repair ZIPs were deleted at operator request; its source/tests remain here but the utility is excluded from future distributions. Detailed evidence is retained in the wave reports.

## Paused waves

- `1xxcb index-restart-envelope`: implemented and reviewed; closure still operator-owned. Its behavior is included in 1.24.0.
- `1xtnr call-edge-target-integrity`: both changes implemented and reviewed; closure still operator-owned. Builder 52 and call-site citations are included in 1.24.0. Original review evidence and follow-ups remain in that wave.

## Release follow-through

Commit the reviewed pending 1.24.0 changes, then run `build_pack.py --version 1.24.0 --with-models --release`. Verify the published feature/model assets and tag. Changelog is dated and emphasizes user benefits; local-testing repair history is omitted. Sensor `ac_asserts_repository_state` (wave `1wur7`) remains advisory.

## Open questions / Deferred decisions

- Graph-expansion/reranking quality comparison (evaluation AC-4) remains intentionally deferred; current retrieval ordering unchanged.
- Native Windows/Linux/Intel execution remains release follow-through.
- Investigate MCP's initial `graph_rebuilt=false` notice on an all-content full rebuild.
- The CoreML reranker probe fell back to CPU after `output_features has no value for logits`; no reranker fix included.
- Any other unfinished povc receipt must retain its original archive; qualified revision-2 repair: `/Users/coryhacking/.wavefoundry/dist/povc-storage-rebuild-repair-v2.zip`.
- Follow-ups recorded by the 1xtnr council, not in scope: bind the two `graph-index-system.md` builder-version mirrors to `docs_constants_validators._claims()`; a kind-aware `symbol_lookup` once `reads` binds get their own table; route `_scan_all_call_sites_in_file` through `_resolve_repo_path`.

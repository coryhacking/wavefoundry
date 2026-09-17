# Session Handoff

Owner: Engineering
Status: active
Last verified: 2026-09-16

## Current Session

**Active wave:** *(none)*
**Status:** idle. Waves 1y6hg and 1y4j8 are closed with current review approvals and a proven 9,104-test framework receipt. The Python advisory wave was committed/pushed as 52158da1; the test-only wave remains uncommitted.

**Last closed wave:** `1y4j8 portable-windows-path-test` — Windows lexical comparison test uses pure paths, retaining positive/negative assertions without requiring a Windows filesystem.

Retrospective validated as memory `1y5tz-mem validate-setup-readiness-against-canonical-producers`: test observers with actual producer output and share parser grammar. No wave AC/task deferrals.

## Release

Official 1.24.0+ppq7 published on 2026-09-13; tag v1.24.0 and framework/model asset hashes verified. Source commit 3433fb03; release stamp f8e4732e. Host-neutral orchestration is subsequent source work, not a new packaged release.

## Open questions / Deferred decisions

- Graph-expansion/reranking quality comparison (evaluation AC-4) remains intentionally deferred; current retrieval ordering unchanged.
- Native Windows/Linux/Intel execution remains release follow-through.
- Investigate MCP's initial `graph_rebuilt=false` notice on an all-content full rebuild.
- The CoreML reranker probe fell back to CPU after `output_features has no value for logits`; no reranker fix included.
- Any other unfinished povc receipt must retain its original archive; qualified revision-2 repair: `/Users/coryhacking/.wavefoundry/dist/povc-storage-rebuild-repair-v2.zip`.
- Follow-ups recorded by the 1xtnr council, not in scope: bind the two `graph-index-system.md` builder-version mirrors to `docs_constants_validators._claims()`; a kind-aware `symbol_lookup` once `reads` binds get their own table; route `_scan_all_call_sites_in_file` through `_resolve_repo_path`.
